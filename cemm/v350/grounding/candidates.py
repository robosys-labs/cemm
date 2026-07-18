"""Candidate generation for Phase-8 grounding.

Candidate providers are deliberately plural: canonical referents, discourse,
multimodal tracks, system output, schema topics, and provisional identities all
contribute evidence.  No provider may select a winner on its own.
"""
from __future__ import annotations

from collections import defaultdict
import unicodedata
from typing import Iterable

from ..facets import TypeClosureCompiler
from ..schema.model import PortFillerClass, ReferentTypeSchema, SchemaClass, StorageKind, semantic_fingerprint
from ..storage import SemanticStore, StoreSnapshot
from ..uol.model import Referent
from .model import (
    CandidateOrigin,
    DiscourseAnchor,
    GroundingCandidate,
    GroundingFactor,
    GroundingFactorKind,
    MentionHypothesis,
    MentionTargetClass,
    MultimodalTrack,
    SystemOutputAnchor,
)


class GroundingCandidateProvider:
    def __init__(self, store: SemanticStore):
        self.store = store

    def generate(
        self,
        mentions: Iterable[MentionHypothesis],
        *,
        discourse_anchors: Iterable[DiscourseAnchor] = (),
        multimodal_tracks: Iterable[MultimodalTrack] = (),
        system_outputs: Iterable[SystemOutputAnchor] = (),
        snapshot: StoreSnapshot | None = None,
        allow_provisional: bool = True,
    ) -> tuple[GroundingCandidate, ...]:
        if snapshot is not None:
            self.store.assert_snapshot(snapshot)
        referents = tuple(item.payload for item in self.store.repositories.referents.all(snapshot=snapshot))
        by_ref = {item.referent_ref: item for item in referents}
        identities = defaultdict(list)
        applications = {
            item.record_ref: item.payload
            for item in self.store.repositories.applications.all(snapshot=snapshot)
        }
        for stored in self.store.repositories.identity_facets.all(snapshot=snapshot):
            facet = stored.payload
            identities[_normalize(facet.normalized_value)].append(facet)
        anchor_by_ref = defaultdict(list)
        for anchor in discourse_anchors:
            anchor_by_ref[anchor.referent_ref].append(anchor)
        multimodal = tuple(multimodal_tracks)
        outputs = tuple(system_outputs)
        type_cache: dict[str, tuple[str, ...]] = {}
        schema_registry = self.store.repositories.schemas.registry(snapshot=snapshot)

        def declared_type_closure(type_refs: Iterable[str]) -> tuple[str, ...]:
            closure: set[str] = set()
            for type_ref in type_refs:
                try:
                    schema = schema_registry.authoritative_schema(type_ref)
                    if isinstance(schema, ReferentTypeSchema):
                        closure.update(schema_registry.type_closure(type_ref, schema.revision))
                    else:
                        closure.add(type_ref)
                except Exception:
                    closure.add(type_ref)
            return tuple(sorted(closure))

        def type_closure(ref: str, referent: Referent) -> tuple[str, ...]:
            cached = type_cache.get(ref)
            if cached is not None:
                return cached
            try:
                closure = TypeClosureCompiler(self.store).compile(
                    ref,
                    context_ref=referent.context_refs[0] if referent.context_refs else "actual",
                    snapshot=snapshot,
                )
                value = tuple(sorted(closure.type_refs))
            except Exception:
                # Candidate generation remains partial when a provisional or
                # historical referent has unresolved type evidence.
                value = tuple(sorted(referent.type_refs))
            type_cache[ref] = value
            return value

        candidates: list[GroundingCandidate] = []
        for mention in mentions:
            seen_targets: set[tuple[str, CandidateOrigin]] = set()
            structural_targets = set(map(str, mention.metadata.get("structural_targets", ())))
            grounding_channels = set(map(str, mention.metadata.get("grounding_channels", ())))
            required_discourse_roles = set(map(str, mention.metadata.get("required_discourse_roles", ())))
            deictic_external = bool(grounding_channels.intersection({"multimodal", "system_output"}))
            discourse_only = bool(mention.metadata.get("discourse_required")) or bool(required_discourse_roles)
            schema_target_refs = tuple(map(str, mention.metadata.get("schema_target_refs", ())))
            introduces_occurrence = (
                mention.target_class in {
                    MentionTargetClass.EVENT, MentionTargetClass.CLAIM, MentionTargetClass.STATE
                }
                and bool(schema_target_refs)
                and not structural_targets
                and not mention.description_application_refs
            )

            if not deictic_external and not introduces_occurrence:
                for referent in referents:
                    referent_anchors = tuple(anchor_by_ref.get(referent.referent_ref, ()))
                    if discourse_only and not referent_anchors:
                        continue
                    if required_discourse_roles and not any(
                        required_discourse_roles.intersection(anchor.role_refs)
                        for anchor in referent_anchors
                    ):
                        continue
                    candidate = self._referent_candidate(
                        mention, referent, type_closure(referent.referent_ref, referent),
                        identities=identities, applications=applications,
                        anchors=referent_anchors,
                    )
                    if candidate is None or (candidate.target_ref, candidate.origin) in seen_targets:
                        continue
                    candidates.append(candidate)
                    seen_targets.add((candidate.target_ref, candidate.origin))

            if mention.target_class == MentionTargetClass.SCHEMA_TOPIC:
                candidates.extend(self._schema_candidates(mention, snapshot=snapshot))

            if (mention.target_class == MentionTargetClass.MULTIMODAL_TRACK
                    or "multimodal" in grounding_channels):
                for track in multimodal:
                    if track.referent_ref in by_ref and track.referent_ref not in type_cache:
                        type_closure(track.referent_ref, by_ref[track.referent_ref])
                    elif track.referent_ref is None and track.track_ref not in type_cache:
                        type_cache[track.track_ref] = declared_type_closure(track.type_refs)
                    candidate = self._multimodal_candidate(mention, track, by_ref, type_cache)
                    if candidate is not None and (candidate.target_ref, candidate.origin) not in seen_targets:
                        candidates.append(candidate)
                        seen_targets.add((candidate.target_ref, candidate.origin))

            if (mention.target_class == MentionTargetClass.SYSTEM_OUTPUT
                    or "system_output" in grounding_channels):
                for output in outputs:
                    for ref in (*output.target_refs, *output.content_referent_refs):
                        if ref in by_ref and ref not in type_cache:
                            type_closure(ref, by_ref[ref])
                    for candidate in self._system_output_candidates(mention, output, by_ref, type_cache):
                        if (candidate.target_ref, candidate.origin) not in seen_targets:
                            candidates.append(candidate)
                            seen_targets.add((candidate.target_ref, candidate.origin))

            if allow_provisional and not any(item.mention_ref == mention.mention_ref for item in candidates):
                candidates.append(self._provisional_candidate(mention))
            elif allow_provisional and self._should_keep_frontier(mention, candidates):
                candidates.append(self._provisional_candidate(mention))

        return tuple(sorted(
            candidates,
            key=lambda item: (item.mention_ref, -item.local_score, item.origin.value, item.target_ref),
        ))

    def _referent_candidate(
        self,
        mention: MentionHypothesis,
        referent: Referent,
        type_refs: tuple[str, ...],
        *,
        identities,
        applications,
        anchors: Iterable[DiscourseAnchor],
        forced_identity: bool = False,
    ) -> GroundingCandidate | None:
        if mention.expected_storage_kinds and referent.storage_kind not in mention.expected_storage_kinds:
            return None
        if not _target_accepts_storage(mention.target_class, referent.storage_kind):
            return None
        if mention.context_ref not in referent.context_refs and "global" not in referent.context_refs:
            return None
        if mention.expected_type_refs and not _type_compatible(type_refs, mention.expected_type_refs):
            return None
        if mention.time_ref is not None and referent.valid_time_ref is not None \
                and mention.time_ref != referent.valid_time_ref:
            return None

        evidence = mention.evidence_refs or (f"mention:{mention.mention_ref}",)
        factors: list[GroundingFactor] = []
        if forced_identity:
            factors.append(_factor(mention, referent.referent_ref, GroundingFactorKind.IDENTITY, 8.0,
                                   evidence, "explicit deictic identity", hard=True))
        normalized = _normalize(mention.normalized_surface)
        matched = [
            facet for facet in identities.get(normalized, ())
            if facet.referent_ref == referent.referent_ref
            and facet.context_ref in {"global", mention.context_ref}
        ]
        if matched:
            factors.append(_factor(
                mention, referent.referent_ref, GroundingFactorKind.IDENTITY,
                4.0 + max(item.confidence for item in matched),
                tuple(sorted({ref for item in matched for ref in item.evidence_refs})) or evidence,
                "normalized identity facet match",
                metadata={"normalized_value": normalized},
            ))
        elif bool(mention.metadata.get("unresolved_form")) and not forced_identity:
            # Unknown lexical material should not match every existing referent
            # merely because type/context are broad.
            if not tuple(anchors):
                return None

        if mention.expected_type_refs:
            factors.append(_factor(
                mention, referent.referent_ref, GroundingFactorKind.TYPE, 2.0,
                evidence, "referent type closure satisfies mention constraints", hard=True,
                metadata={"type_refs": type_refs},
            ))
        else:
            factors.append(_factor(
                mention, referent.referent_ref, GroundingFactorKind.TYPE, 0.2,
                evidence, "open referent type constraint",
            ))
        factors.append(_factor(
            mention, referent.referent_ref, GroundingFactorKind.STORAGE, 1.0,
            evidence, "storage kind is compatible", hard=True,
            metadata={"storage_kind": referent.storage_kind.value},
        ))
        factors.append(_factor(
            mention, referent.referent_ref, GroundingFactorKind.CONTEXT, 0.8,
            evidence, "referent is visible in the selected context", hard=True,
        ))
        if mention.time_ref is not None:
            factors.append(_factor(
                mention, referent.referent_ref, GroundingFactorKind.TIME, 0.75,
                evidence, "referent validity is compatible with the selected time", hard=True,
                metadata={"time_ref": mention.time_ref},
            ))
        description_factors = self._description_factors(
            mention, referent.referent_ref, applications, evidence
        )
        if description_factors is None:
            return None
        factors.extend(description_factors)
        anchor_values = tuple(anchors)
        if anchor_values:
            best = max(anchor_values, key=lambda item: (item.salience, item.turn_index))
            factors.append(_factor(
                mention, referent.referent_ref, GroundingFactorKind.DISCOURSE,
                1.0 + best.salience + min(best.turn_index, 20) * 0.01,
                best.evidence_refs or evidence,
                "discourse anchor supports the referent",
                metadata={"anchor_ref": best.anchor_ref},
            ))
        return GroundingCandidate(
            candidate_ref=_candidate_ref(mention, referent.referent_ref, CandidateOrigin.STORE),
            mention_ref=mention.mention_ref,
            target_ref=referent.referent_ref,
            origin=CandidateOrigin.STORE,
            storage_kind=referent.storage_kind,
            type_refs=type_refs,
            context_refs=referent.context_refs,
            factors=tuple(factors),
            valid_time_ref=referent.valid_time_ref,
        )


    @staticmethod
    def _description_factors(mention, referent_ref, applications, fallback_evidence):
        factors = []
        for application_ref in mention.description_application_refs:
            application = applications.get(application_ref)
            if application is None or application.context_ref != mention.context_ref:
                return None
            bound_refs = {
                filler.ref
                for binding in application.bindings
                for filler in binding.fillers
                if getattr(filler, "filler_class", None) == PortFillerClass.REFERENT
            }
            if bound_refs and referent_ref not in bound_refs:
                return None
            evidence = application.evidence_refs or fallback_evidence
            factors.append(_factor(
                mention, referent_ref, GroundingFactorKind.DESCRIPTION, 1.5,
                evidence, "semantic description application supports this referent", hard=bool(bound_refs),
                metadata={"application_ref": application_ref},
            ))
        return tuple(factors)

    def _schema_candidates(
        self, mention: MentionHypothesis, *, snapshot: StoreSnapshot | None
    ) -> tuple[GroundingCandidate, ...]:
        registry = self.store.repositories.schemas.registry(snapshot=snapshot)
        evidence = mention.evidence_refs or (f"mention:{mention.mention_ref}",)
        result = []
        # Exact schema-target lexical senses carry target refs in metadata.
        lexical_targets = set(map(str, mention.metadata.get("schema_target_refs", ())))
        for schema in registry.iter_schemas():
            if schema.lifecycle_status.value not in {"competence_verified", "active"}:
                continue
            exact = schema.schema_ref in lexical_targets
            semantic_key_match = _normalize(schema.semantic_key) == _normalize(mention.normalized_surface)
            if not (exact or semantic_key_match):
                continue
            factors = (
                _factor(mention, schema.schema_ref, GroundingFactorKind.SCHEMA_TOPIC,
                        5.0 if exact else 3.0, evidence,
                        "lexical/schema-topic evidence identifies an exact schema revision", hard=exact,
                        metadata={"schema_revision": schema.revision, "schema_class": schema.schema_class.value}),
            )
            result.append(GroundingCandidate(
                candidate_ref=_candidate_ref(mention, schema.schema_ref, CandidateOrigin.SCHEMA),
                mention_ref=mention.mention_ref,
                target_ref=schema.schema_ref,
                origin=CandidateOrigin.SCHEMA,
                storage_kind=StorageKind.SCHEMA_TOPIC,
                type_refs=mention.expected_type_refs,
                context_refs=(mention.context_ref,),
                factors=factors,
                metadata={"schema_revision": schema.revision, "schema_class": schema.schema_class.value},
            ))
        return tuple(result)

    @staticmethod
    def _multimodal_candidate(
        mention: MentionHypothesis,
        track: MultimodalTrack,
        by_ref: dict[str, Referent],
        type_cache: dict[str, tuple[str, ...]],
    ) -> GroundingCandidate | None:
        if track.context_ref not in {"global", mention.context_ref}:
            return None
        target_ref = track.referent_ref or track.track_ref
        referent = by_ref.get(target_ref)
        storage = referent.storage_kind if referent is not None else _storage_for_target(mention.target_class)
        type_refs = type_cache.get(target_ref, tuple(sorted(track.type_refs)))
        if mention.expected_storage_kinds and storage not in mention.expected_storage_kinds:
            return None
        if mention.expected_type_refs and not _type_compatible(type_refs, mention.expected_type_refs):
            return None
        if mention.time_ref is not None and track.valid_time_ref is not None and mention.time_ref != track.valid_time_ref:
            return None
        evidence = track.evidence_refs or mention.evidence_refs or (f"track:{track.track_ref}",)
        factors = (
            _factor(mention, target_ref, GroundingFactorKind.MULTIMODAL,
                    2.0 + track.salience, evidence,
                    "multimodal track is salient in the selected context",
                    metadata={"track_ref": track.track_ref, "modality": track.modality}),
        )
        return GroundingCandidate(
            candidate_ref=_candidate_ref(mention, target_ref, CandidateOrigin.MULTIMODAL),
            mention_ref=mention.mention_ref,
            target_ref=target_ref,
            origin=CandidateOrigin.MULTIMODAL,
            storage_kind=storage,
            type_refs=type_refs,
            context_refs=(track.context_ref,),
            factors=factors,
            valid_time_ref=track.valid_time_ref,
            provisional=track.referent_ref is None,
            metadata={"track_ref": track.track_ref},
        )

    @staticmethod
    def _system_output_candidates(
        mention: MentionHypothesis,
        output: SystemOutputAnchor,
        by_ref: dict[str, Referent],
        type_cache: dict[str, tuple[str, ...]],
    ) -> tuple[GroundingCandidate, ...]:
        if output.context_ref not in {"global", mention.context_ref}:
            return ()
        evidence = output.evidence_refs or mention.evidence_refs or (f"system-output:{output.output_ref}",)
        refs = tuple(dict.fromkeys((*output.target_refs, *output.content_referent_refs)))
        result = []
        for ref in refs:
            referent = by_ref.get(ref)
            if referent is None:
                continue
            if mention.expected_storage_kinds and referent.storage_kind not in mention.expected_storage_kinds:
                continue
            types = type_cache.get(ref, tuple(sorted(referent.type_refs)))
            if mention.expected_type_refs and not _type_compatible(types, mention.expected_type_refs):
                continue
            if mention.time_ref is not None and referent.valid_time_ref is not None and mention.time_ref != referent.valid_time_ref:
                continue
            result.append(GroundingCandidate(
                candidate_ref=_candidate_ref(mention, ref, CandidateOrigin.SYSTEM_OUTPUT),
                mention_ref=mention.mention_ref,
                target_ref=ref,
                origin=CandidateOrigin.SYSTEM_OUTPUT,
                storage_kind=referent.storage_kind,
                type_refs=types,
                context_refs=referent.context_refs,
                factors=(
                    _factor(mention, ref, GroundingFactorKind.SYSTEM_OUTPUT,
                            (3.0 if ref in output.target_refs else 2.5)
                            + min(output.turn_index, 20) * 0.01,
                            evidence,
                            ("system-output target supports this referent"
                             if ref in output.target_refs
                             else "system-output content mentions this referent"),
                            metadata={
                                "output_ref": output.output_ref,
                                "is_target": ref in output.target_refs,
                            }),
                ),
            ))
        return tuple(result)

    @staticmethod
    def _provisional_candidate(mention: MentionHypothesis) -> GroundingCandidate:
        target_ref = "referent:provisional:" + semantic_fingerprint(
            "provisional-referent", (mention.source_ref, mention.span.start, mention.span.end,
                                      mention.normalized_surface, mention.context_ref), 24
        )
        evidence = mention.evidence_refs or (f"mention:{mention.mention_ref}",)
        return GroundingCandidate(
            candidate_ref=_candidate_ref(mention, target_ref, CandidateOrigin.PROVISIONAL),
            mention_ref=mention.mention_ref,
            target_ref=target_ref,
            origin=CandidateOrigin.PROVISIONAL,
            storage_kind=(mention.expected_storage_kinds[0] if mention.expected_storage_kinds
                          else _storage_for_target(mention.target_class)),
            type_refs=mention.expected_type_refs,
            context_refs=(mention.context_ref,),
            factors=(
                _factor(mention, target_ref, GroundingFactorKind.PROVISIONAL, -0.75,
                        evidence, "no resolved identity is required; retain a provisional frontier"),
            ),
            provisional=True,
            valid_time_ref=mention.time_ref,
            metadata={
                "introduced_by_schema_refs": tuple(
                    map(str, mention.metadata.get("schema_target_refs", ()))
                ),
                "introduced_by_schema_pins": tuple(
                    (str(ref), int(revision))
                    for ref, revision in mention.metadata.get("schema_target_pins", ())
                ),
                "occurrence_introduction": mention.target_class in {
                    MentionTargetClass.EVENT, MentionTargetClass.CLAIM, MentionTargetClass.STATE
                },
            },
        )

    @staticmethod
    def _should_keep_frontier(
        mention: MentionHypothesis, all_candidates: list[GroundingCandidate]
    ) -> bool:
        local = [item for item in all_candidates if item.mention_ref == mention.mention_ref]
        if not local:
            return True
        best = max(item.local_score for item in local)
        return best < 3.0 or bool(mention.metadata.get("unresolved_form"))


def _candidate_ref(mention: MentionHypothesis, target_ref: str, origin: CandidateOrigin) -> str:
    return "grounding-candidate:" + semantic_fingerprint(
        "grounding-candidate-ref", (mention.mention_ref, target_ref, origin.value), 24
    )


def _factor(
    mention: MentionHypothesis,
    target_ref: str,
    kind: GroundingFactorKind,
    score: float,
    evidence_refs: tuple[str, ...],
    reason: str,
    *,
    hard: bool = False,
    metadata=None,
) -> GroundingFactor:
    refs = tuple(sorted(set(evidence_refs))) or (f"mention:{mention.mention_ref}",)
    return GroundingFactor(
        factor_ref="grounding-factor:" + semantic_fingerprint(
            "grounding-factor-ref", (mention.mention_ref, target_ref, kind.value, reason, refs), 24
        ),
        factor_kind=kind,
        score=score,
        evidence_refs=refs,
        reason=reason,
        hard=hard,
        metadata={} if metadata is None else dict(metadata),
    )


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold().strip()


def _target_accepts_storage(target: MentionTargetClass, storage: StorageKind) -> bool:
    allowed = {
        MentionTargetClass.EVENT: {StorageKind.EVENT_OCCURRENCE},
        MentionTargetClass.CLAIM: {StorageKind.EVENT_OCCURRENCE},
        MentionTargetClass.PROPOSITION: {StorageKind.PROPOSITION},
        MentionTargetClass.STATE: {StorageKind.STATE_OCCURRENCE},
        MentionTargetClass.SCHEMA_TOPIC: {StorageKind.SCHEMA_TOPIC},
    }.get(target)
    return True if allowed is None else storage in allowed


def _storage_for_target(target: MentionTargetClass) -> StorageKind:
    return {
        MentionTargetClass.EVENT: StorageKind.EVENT_OCCURRENCE,
        MentionTargetClass.CLAIM: StorageKind.EVENT_OCCURRENCE,
        MentionTargetClass.PROPOSITION: StorageKind.PROPOSITION,
        MentionTargetClass.STATE: StorageKind.STATE_OCCURRENCE,
        MentionTargetClass.SCHEMA_TOPIC: StorageKind.SCHEMA_TOPIC,
    }.get(target, StorageKind.ORDINARY)



def _type_compatible(actual: Iterable[str], expected: Iterable[str]) -> bool:
    actual_set = set(actual)
    return bool(actual_set.intersection(expected))
