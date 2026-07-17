"""Discourse, reference-candidate and session-world context services."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from math import exp
from typing import Any, Iterable, Mapping

from .language import primary_language
from .model import (
    FormLattice,
    FormSpanCandidate,
    GraphPatch,
    GroundingCandidate,
    MeaningBundle,
    PatchOperation,
    PatchOperationKind,
    QuantityPayload,
    Referent,
    ReferentKind,
    semantic_hash,
)
from .schema import LanguagePack
from .storage import SemanticStore


@dataclass(frozen=True, slots=True)
class ContextSnapshot:
    context_ref: str
    store_revision: int
    recent_turns: tuple[Mapping[str, Any], ...]
    recent_mentions: tuple[tuple[Referent, float, str], ...]
    open_questions: tuple[Mapping[str, Any], ...]
    world_tracks: tuple[Mapping[str, Any], ...]
    self_ref: str = "referent:self"
    user_ref: str = "referent:user"


class ContextCoordinator:
    def __init__(self, store: SemanticStore):
        self._store = store

    def snapshot(self, context_ref: str) -> ContextSnapshot:
        return ContextSnapshot(
            context_ref=context_ref,
            store_revision=self._store.revision,
            recent_turns=self._store.recent_turns(context_ref),
            recent_mentions=self._store.recent_mentions(context_ref),
            open_questions=self._store.open_questions(context_ref),
            world_tracks=self._store.world_tracks(context_ref),
        )


class ReferentCandidateGenerator:
    """Generate N-best referent candidates without deciding identity."""

    def __init__(self, store: SemanticStore, language_packs: Mapping[str, LanguagePack]):
        self._store = store
        self._packs = dict(language_packs)

    def generate(
        self,
        lattice: FormLattice,
        context: ContextSnapshot,
        *,
        max_per_span: int = 8,
    ) -> dict[str, tuple[GroundingCandidate, ...]]:
        language_tag = primary_language(lattice)
        pack = self._packs.get(language_tag)
        result: dict[str, list[GroundingCandidate]] = {}
        for span in lattice.spans:
            if span.candidate_kind in {"clause", "construction_evidence"}:
                continue
            candidates: list[GroundingCandidate] = []
            if span.candidate_kind == "pronoun":
                candidates.extend(self._pronoun_candidates(span, context, pack))
            if span.candidate_kind == "quantity":
                candidates.append(self._quantity_candidate(span, context))
            candidates.extend(self._semantic_ref_candidates(span, context))
            if span.candidate_kind not in {"pronoun", "question_operator", "conjunction", "copula"}:
                candidates.extend(self._alias_candidates(span, language_tag))
            if span.candidate_kind in {"unresolved", "name_candidate", "text"}:
                candidates.append(self._text_candidate(span, context))
                candidates.extend(self._projected_mention_candidates(span, context))
            if candidates:
                candidates = sorted(candidates, key=lambda item: item.score, reverse=True)
                result[span.span_id] = _dedupe_candidates(candidates)[:max_per_span]
        return {key: tuple(value) for key, value in result.items()}

    def _pronoun_candidates(
        self,
        span: FormSpanCandidate,
        context: ContextSnapshot,
        pack: LanguagePack | None,
    ) -> list[GroundingCandidate]:
        results: list[GroundingCandidate] = []
        explicit = tuple(span.semantic_refs)
        for rank, referent_ref in enumerate(explicit):
            referent = self._store.get_referent(referent_ref)
            if referent is None:
                continue
            results.append(GroundingCandidate(
                candidate_id=semantic_hash("ground", (span.span_id, referent_ref, "participant")),
                mention_span_ref=span.span_id,
                referent=referent,
                score=max(0.5, span.confidence - rank * 0.05),
                score_parts={"grammar": span.confidence, "participant": 0.2},
                evidence_refs=span.evidence_refs,
            ))
        person = str(span.features.get("person", ""))
        deixis = str(span.features.get("deixis", ""))
        anaphoric = bool(span.features.get("anaphoric", False))
        if person == "first":
            referent = self._store.get_referent(context.user_ref)
            if referent is not None:
                results.append(self._candidate(span, referent, 0.98, "speaker"))
        elif person == "second":
            referent = self._store.get_referent(context.self_ref)
            if referent is not None:
                results.append(self._candidate(span, referent, 0.98, "addressee"))
        if anaphoric or deixis:
            for index, (referent, salience, role) in enumerate(context.recent_mentions[:8]):
                kind_bonus = 0.0
                accepted = set(map(str, span.features.get("accepted_kinds", ())))
                if accepted and referent.kind.value in accepted:
                    kind_bonus = 0.12
                results.append(GroundingCandidate(
                    candidate_id=semantic_hash("ground", (span.span_id, referent.referent_id, "discourse")),
                    mention_span_ref=span.span_id,
                    referent=referent,
                    score=min(0.95, 0.45 + salience * 0.35 + kind_bonus - index * 0.02),
                    score_parts={"salience": salience, "kind_fit": kind_bonus, "recency_rank": -index * 0.02},
                    evidence_refs=span.evidence_refs + (f"discourse:mention:{referent.referent_id}",),
                ))
            for index, turn in enumerate(context.recent_turns[:5]):
                for proposition_ref in turn.get("proposition_refs", ()):
                    referent = self._store.get_referent(str(proposition_ref))
                    if referent is None:
                        continue
                    results.append(GroundingCandidate(
                        candidate_id=semantic_hash("ground", (span.span_id, proposition_ref, "proposition")),
                        mention_span_ref=span.span_id,
                        referent=referent,
                        score=0.7 - index * 0.06,
                        score_parts={"proposition_recency": 0.7 - index * 0.06},
                        evidence_refs=span.evidence_refs + (f"discourse:turn:{turn['turn_id']}",),
                    ))
            now = datetime.now(timezone.utc)
            for track in context.world_tracks[:8]:
                recency = _world_track_recency(str(track.get("observed_at", "")), now=now)
                if recency <= 0.01:
                    continue
                referent = self._store.get_referent(str(track["referent_ref"]))
                if referent is None:
                    continue
                confidence = float(track["confidence"])
                score = 0.30 + confidence * 0.38 + recency * 0.20
                results.append(GroundingCandidate(
                    candidate_id=semantic_hash("ground", (span.span_id, referent.referent_id, "world")),
                    mention_span_ref=span.span_id,
                    referent=referent,
                    score=min(0.92, score),
                    score_parts={
                        "world_track": confidence,
                        "world_recency": recency,
                    },
                    evidence_refs=span.evidence_refs + (f"world_track:{track['track_id']}",),
                    provisional=recency < 0.25,
                ))
        return results

    def _semantic_ref_candidates(
        self, span: FormSpanCandidate, context: ContextSnapshot
    ) -> list[GroundingCandidate]:
        result = []
        for semantic_ref in span.semantic_refs:
            if semantic_ref.startswith(("predicate:", "operation:", "force:", "structure:")):
                continue
            referent = self._store.get_referent(semantic_ref)
            if referent is not None:
                result.append(self._candidate(span, referent, span.confidence, "semantic_ref"))
        return result

    def _alias_candidates(self, span: FormSpanCandidate, language_tag: str) -> list[GroundingCandidate]:
        result = []
        for referent, confidence in self._store.resolve_alias(span.normalized, language_tag):
            result.append(GroundingCandidate(
                candidate_id=semantic_hash("ground", (span.span_id, referent.referent_id, "alias")),
                mention_span_ref=span.span_id,
                referent=referent,
                score=min(0.99, confidence * span.confidence),
                score_parts={"alias": confidence, "span": span.confidence},
                evidence_refs=span.evidence_refs + (f"alias:{language_tag}:{span.normalized}",),
            ))
        return result

    @staticmethod
    def _quantity_candidate(span: FormSpanCandidate, context: ContextSnapshot) -> GroundingCandidate:
        magnitude = str(span.features.get("magnitude", span.normalized))
        referent = Referent(
            referent_id=semantic_hash("referent:quantity", (magnitude, context.context_ref)),
            kind=ReferentKind.QUANTITY,
            type_refs=("kind:quantity",),
            payload=QuantityPayload(magnitude=magnitude),
            scope_ref=context.context_ref,
            context_ref=context.context_ref,
            metadata={"surface": span.surface},
        )
        return GroundingCandidate(
            candidate_id=semantic_hash("ground", (span.span_id, referent.referent_id)),
            mention_span_ref=span.span_id,
            referent=referent,
            score=0.98,
            score_parts={"numeric_parse": 0.98},
            evidence_refs=span.evidence_refs,
            provisional=True,
        )

    @staticmethod
    def _projected_mention_candidates(
        span: FormSpanCandidate, context: ContextSnapshot
    ) -> list[GroundingCandidate]:
        """Emit N-best entity-kind hypotheses without selecting identity.

        These are deliberately low-confidence provisional Referents.  Local
        operational ports later remove incompatible kinds, so the analyzer does
        not decide that an unknown capitalized or unlisted token *is* a person,
        place, event, or object.  The same mechanism works for scripts without
        capitalization because it is driven by unresolved mention spans, not an
        English regex.
        """
        configured = tuple(map(str, span.features.get("candidate_kinds", ())))
        kind_values = configured or (
            ReferentKind.PERSON.value,
            ReferentKind.PLACE.value,
            ReferentKind.ORGANIZATION.value,
            ReferentKind.EVENT.value,
            ReferentKind.PHYSICAL_OBJECT.value,
            ReferentKind.INFORMATION_OBJECT.value,
        )
        result: list[GroundingCandidate] = []
        for rank, value in enumerate(kind_values):
            try:
                kind = ReferentKind(value)
            except ValueError:
                continue
            referent = Referent(
                referent_id=semantic_hash("referent:mention", (
                    span.normalized, kind.value, context.context_ref
                )),
                kind=kind,
                type_refs=(f"kind:{kind.value}",),
                payload={"mention": span.surface},
                scope_ref=context.context_ref,
                context_ref=context.context_ref,
                metadata={
                    "source_span_ref": span.span_id,
                    "identity_status": "candidate",
                },
            )
            score = max(0.24, 0.44 - rank * 0.025)
            result.append(GroundingCandidate(
                candidate_id=semantic_hash("ground:typed_mention", (
                    span.span_id, referent.referent_id
                )),
                mention_span_ref=span.span_id,
                referent=referent,
                score=score,
                score_parts={
                    "mention_evidence": 0.25,
                    "kind_hypothesis": score - 0.25,
                },
                evidence_refs=span.evidence_refs + (
                    f"ner:type_hypothesis:{kind.value}:{span.span_id}",
                ),
                provisional=True,
            ))
        return result

    @staticmethod
    def _text_candidate(span: FormSpanCandidate, context: ContextSnapshot) -> GroundingCandidate:
        referent = Referent(
            referent_id=semantic_hash("referent:text", (span.surface, context.context_ref)),
            kind=ReferentKind.TEXT,
            type_refs=("kind:text",),
            payload={"text": span.surface},
            scope_ref=context.context_ref,
            context_ref=context.context_ref,
            metadata={"normalized": span.normalized, "span_ref": span.span_id},
        )
        return GroundingCandidate(
            candidate_id=semantic_hash("ground", (span.span_id, referent.referent_id, "text")),
            mention_span_ref=span.span_id,
            referent=referent,
            score=0.35,
            score_parts={"mentioned_text": 0.35},
            evidence_refs=span.evidence_refs,
            provisional=True,
        )

    @staticmethod
    def _candidate(span: FormSpanCandidate, referent: Referent, score: float, reason: str) -> GroundingCandidate:
        return GroundingCandidate(
            candidate_id=semantic_hash("ground", (span.span_id, referent.referent_id, reason)),
            mention_span_ref=span.span_id,
            referent=referent,
            score=score,
            score_parts={reason: score},
            evidence_refs=span.evidence_refs,
        )


class DiscoursePatchCompiler:
    def compile(
        self,
        *,
        cycle_id: str,
        context: ContextSnapshot,
        bundle: MeaningBundle | None,
        language_tag: str,
        speaker_ref: str,
        raw_observation_ref: str,
        tone_constraints: Mapping[str, Any] | None = None,
        expected_store_revision: int,
    ) -> GraphPatch | None:
        if bundle is None:
            return None
        operations: list[PatchOperation] = []
        # Preserve selected discourse semantics without admitting them as world
        # knowledge. This makes proposition/event/state antecedents restart-safe.
        for referent in bundle.graph.referents.values():
            kind = (
                PatchOperationKind.UPSERT_PROPOSITION
                if referent.kind == ReferentKind.PROPOSITION
                else PatchOperationKind.UPSERT_REFERENT
            )
            operations.append(PatchOperation(
                operation_id=f"op:discourse:{referent.referent_id}",
                kind=kind,
                target_ref=referent.referent_id,
                payload={
                    "referent_id": referent.referent_id,
                    "kind": referent.kind.value,
                    "type_refs": referent.type_refs,
                    "payload": referent.payload,
                    "scope_ref": referent.scope_ref,
                    "context_ref": referent.context_ref,
                    "provenance": (),
                    "revision": referent.revision,
                    "metadata": dict(referent.metadata),
                },
            ))
        for predication in bundle.graph.predications.values():
            operations.append(PatchOperation(
                operation_id=f"op:discourse:{predication.predication_id}",
                kind=PatchOperationKind.UPSERT_PREDICATION,
                target_ref=predication.predication_id,
                payload={
                    "predication_id": predication.predication_id,
                    "predicate_schema_ref": predication.predicate_schema_ref,
                    "bindings": tuple({
                        "port_id": binding.port_id,
                        "referent_refs": binding.referent_refs,
                        "open_variable_ref": binding.open_variable_ref,
                        "confidence": binding.confidence,
                        "evidence_refs": binding.evidence_refs,
                        "assumptions": binding.assumptions,
                    } for binding in predication.bindings),
                    "context_ref": predication.context_ref,
                    "source_evidence_refs": predication.source_evidence_refs,
                    "assumptions": predication.assumptions,
                    "confidence": predication.confidence,
                    "revision": predication.revision,
                },
            ))
        # Propositions depend on predications, so ensure proposition operations
        # follow the predication operations inside the same atomic patch.
        proposition_operations = [
            operation for operation in operations
            if operation.kind == PatchOperationKind.UPSERT_PROPOSITION
        ]
        operations = [
            operation for operation in operations
            if operation.kind != PatchOperationKind.UPSERT_PROPOSITION
        ] + proposition_operations
        turn_ref = f"turn:{cycle_id}:{speaker_ref}"
        operations.append(PatchOperation(
            operation_id=f"op:{turn_ref}",
            kind=PatchOperationKind.UPSERT_DISCOURSE_TURN,
            target_ref=turn_ref,
            payload={
                "context_ref": context.context_ref,
                "speaker_ref": speaker_ref,
                "proposition_refs": bundle.proposition_refs,
                "language_tag": language_tag,
                "raw_observation_ref": raw_observation_ref,
                "metadata": {
                    "bundle_ref": bundle.bundle_id,
                    "conversational_tone": str((tone_constraints or {}).get("tone", "neutral")),
                    "tone_source": str((tone_constraints or {}).get("tone_source", "default")),
                },
            },
        ))
        mentioned: set[str] = set()
        for proposition_ref in bundle.proposition_refs:
            proposition = bundle.graph.referents.get(proposition_ref)
            if proposition is not None:
                mentioned.add(proposition_ref)
            predication_refs = tuple((proposition.payload or {}).get("predication_refs", ())) if proposition else ()
            for predication_ref in predication_refs:
                predication = bundle.graph.predications.get(str(predication_ref))
                if predication is None:
                    continue
                for binding in predication.bindings:
                    mentioned.update(binding.referent_refs)
                    if binding.open_variable_ref:
                        question_ref = semantic_hash("question", (cycle_id, proposition_ref, binding.open_variable_ref))
                        operations.append(PatchOperation(
                            operation_id=f"op:{question_ref}",
                            kind=PatchOperationKind.UPSERT_OPEN_QUESTION,
                            target_ref=question_ref,
                            payload={
                                "context_ref": context.context_ref,
                                "proposition_ref": proposition_ref,
                                "variable_refs": (binding.open_variable_ref,),
                                "status": "open",
                                "metadata": {"port_id": binding.port_id},
                            },
                        ))
        for index, referent_ref in enumerate(sorted(mentioned)):
            operations.append(PatchOperation(
                operation_id=f"op:mention:{cycle_id}:{index}",
                kind=PatchOperationKind.UPSERT_MENTION,
                target_ref=f"mention:{cycle_id}:{index}",
                payload={
                    "context_ref": context.context_ref,
                    "turn_ref": turn_ref,
                    "referent_ref": referent_ref,
                    "salience": max(0.2, 1.0 - index * 0.05),
                    "grammatical_role": "selected_meaning",
                    "metadata": {"bundle_ref": bundle.bundle_id},
                },
            ))
        return GraphPatch(
            patch_id=semantic_hash("patch:discourse", (cycle_id, bundle.bundle_id)),
            context_ref=context.context_ref,
            scope_ref=context.context_ref,
            source_ref="runtime:discourse",
            evidence_refs=bundle.graph.evidence_refs,
            operations=tuple(operations),
            expected_store_revision=expected_store_revision,
            permission_ref="conversation",
        )


class WorldObservationCompiler:
    def compile(
        self,
        *,
        context_ref: str,
        observations: Iterable[Mapping[str, Any]],
        expected_store_revision: int,
    ) -> GraphPatch | None:
        operations = []
        for index, item in enumerate(observations):
            referent_ref = str(item.get("referent_ref", ""))
            if not referent_ref:
                continue
            track_ref = str(item.get("track_id") or semantic_hash("track", (context_ref, referent_ref, index)))
            operations.append(PatchOperation(
                operation_id=f"op:{track_ref}",
                kind=PatchOperationKind.UPSERT_WORLD_TRACK,
                target_ref=track_ref,
                payload={
                    "context_ref": context_ref,
                    "referent_ref": referent_ref,
                    "modality": str(item.get("modality", "structured")),
                    "state": dict(item.get("state", {})),
                    "confidence": float(item.get("confidence", 0.5)),
                    "observed_at": str(item.get("observed_at") or datetime.now(timezone.utc).isoformat()),
                },
            ))
        if not operations:
            return None
        return GraphPatch(
            patch_id=semantic_hash("patch:world", (context_ref, [op.target_ref for op in operations])),
            context_ref=context_ref,
            scope_ref=context_ref,
            source_ref="runtime:world_observation",
            evidence_refs=tuple(f"world:{op.target_ref}" for op in operations),
            operations=tuple(operations),
            expected_store_revision=expected_store_revision,
        )


def _world_track_recency(observed_at: str, *, now: datetime | None = None) -> float:
    """Return bounded temporal salience for a tracked multimodal observation.

    Tracks decay with a five-minute half-life and are ignored after thirty
    minutes.  The underlying evidence remains durable; only its current
    reference-resolution salience decays.
    """
    if not observed_at:
        return 0.0
    try:
        observed = datetime.fromisoformat(observed_at.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if observed.tzinfo is None:
        observed = observed.replace(tzinfo=timezone.utc)
    now = now or datetime.now(timezone.utc)
    age_seconds = max(0.0, (now - observed).total_seconds())
    if age_seconds >= 1800.0:
        return 0.0
    return float(exp(-age_seconds / 432.808512266689))


def _dedupe_candidates(items: Iterable[GroundingCandidate]) -> list[GroundingCandidate]:
    result: dict[str, GroundingCandidate] = {}
    for item in items:
        key = item.referent.referent_id
        existing = result.get(key)
        if existing is None or item.score > existing.score:
            result[key] = item
    return sorted(result.values(), key=lambda item: item.score, reverse=True)
