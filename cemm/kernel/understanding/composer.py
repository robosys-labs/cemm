"""SemanticComposer — compositional candidate graph construction."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from .candidate_graph import (
    CandidateCommunicativeForce,
    CandidateContext,
    CandidateGraph,
    CandidatePredication,
    CandidateProposition,
    DiscourseRelation,
)
from ..model.context_frame import ContextFrame
from ..model.predication import Predication
from ..model.proposition import Proposition
from ..model.role_binding import OpenPort, RoleBinding
from ..schema.store import SemanticSchemaStore
from ..schema.resolver import SchemaResolver
from ...language.interfaces import SurfaceEvidence
from ...language.stream import TokenKind, TokenStream


class SemanticComposer:
    """Build candidate predications/propositions without selecting truth."""

    def __init__(
        self,
        store: SemanticSchemaStore,
        resolver: SchemaResolver | None = None,
    ) -> None:
        self._store = store
        self._resolver = resolver or SchemaResolver(store)

    def compose(
        self, evidence: SurfaceEvidence, *, context_snapshot=None
    ) -> CandidateGraph:
        stream = evidence.token_stream
        predications: list[CandidatePredication] = []
        propositions: list[CandidateProposition] = []
        contexts: list[CandidateContext] = []
        forces: list[CandidateCommunicativeForce] = []
        discourse: list[DiscourseRelation] = []
        open_ports: list[OpenPort] = []
        opaque_refs: list[str] = []

        # Lexical candidates establish stable opaque sense identities or point
        # to schema-backed senses. Bare nouns do not become entity facts.
        for lexical in evidence.lexical_sense_candidates:
            key = lexical.semantic_key
            resolution = self._resolver.resolve_key(key)
            if key.startswith("opaque:") and not resolution.candidates:
                opaque_refs.append(key)
                continue
            for sense in resolution.candidates:
                candidate = self._lexical_predication(sense, lexical)
                if candidate is not None:
                    predications.append(candidate)
                    open_ports.extend(candidate.predication.open_ports)
            if not resolution.candidates and not self._is_grammatical_key(key):
                opaque_refs.append(
                    self._stable_opaque(
                        lexical.lexical_form_ref.normalised
                        or lexical.lexical_form_ref.surface,
                        lexical.lexical_form_ref.language_tag,
                    )
                )

        # Construction candidates add compositional predications.
        construction_predications: dict[int, CandidatePredication] = {}
        for construction in evidence.construction_candidates:
            candidate = self._construction_predication(construction)
            if candidate is not None:
                predications.append(candidate)
                construction_predications[id(construction)] = candidate
            port = self._open_port_for(construction)
            if port is not None:
                open_ports.append(port)

        # Create contexts and propositions. User assertions are preserved in a
        # reported context until epistemic admission; questions inspect the
        # requested context without turning the question itself into evidence.
        turn_force = max(
            evidence.communicative_candidates,
            key=lambda item: item.confidence,
            default=None,
        )
        force_key = getattr(turn_force, "force", "assert")
        context_kind = "reported" if force_key in {"assert", "correct"} else "actual"
        attribution_ref = "referent:user" if context_kind == "reported" else None
        prop_by_predication: dict[str, str] = {}
        for candidate in predications:
            context = ContextFrame(id=f"ctx:{uuid4().hex[:12]}", context_kind=context_kind)
            contexts.append(CandidateContext(context, 0.9))
            proposition = Proposition(
                id=f"prop:{uuid4().hex[:12]}",
                predication_ref=candidate.predication.id,
                context_ref=context.id,
                polarity=self._polarity_for(candidate, stream),
                attribution_ref=attribution_ref,
                derivation_kind="attributed" if attribution_ref else "observed",
            )
            prop_by_predication[candidate.predication.id] = proposition.id
            propositions.append(
                CandidateProposition(
                    proposition=proposition,
                    candidate_source=candidate.candidate_source,
                    confidence=candidate.confidence,
                    source_evidence_refs=candidate.source_evidence_refs,
                )
            )

        # Build embedded definitional proposition patterns for complement
        # questions, then bind them to the outer content role.
        predications, propositions, contexts, open_ports = self._embed_complements(
            evidence,
            predications,
            propositions,
            contexts,
            open_ports,
            stream,
        )

        for communicative in evidence.communicative_candidates:
            target = ""
            if propositions:
                candidates = propositions
                if communicative.force == "ask":
                    embedded = [
                        item for item in propositions
                        if item.embedded_proposition_refs
                    ]
                    if embedded:
                        candidates = embedded
                target = max(candidates, key=lambda item: item.confidence).proposition.id
            forces.append(
                CandidateCommunicativeForce(
                    force=communicative.force,
                    target_proposition_ref=target,
                    confidence=communicative.confidence,
                    source_evidence_refs=(),
                    source_token_indices=communicative.source_token_indices,
                )
            )
        if not forces and propositions:
            forces.append(
                CandidateCommunicativeForce(
                    force="assert",
                    target_proposition_ref=propositions[0].proposition.id,
                    confidence=0.5,
                )
            )

        for cue in evidence.pragmatic_cues:
            if cue.replaces_content:
                raise ValueError("pragmatic cue may not replace semantic content")
            if propositions:
                discourse.append(
                    DiscourseRelation(
                        source_ref=propositions[0].proposition.id,
                        target_ref=propositions[-1].proposition.id,
                        relation_kind=cue.cue_kind,
                        confidence=cue.confidence,
                        from_pragmatic_cue=True,
                    )
                )

        return CandidateGraph(
            candidate_predications=tuple(predications),
            candidate_propositions=tuple(propositions),
            candidate_communicative_forces=tuple(forces),
            candidate_contexts=tuple(contexts),
            discourse_relations=tuple(discourse),
            open_ports=tuple(self._dedupe_ports(open_ports)),
            opaque_lexeme_refs=tuple(dict.fromkeys(opaque_refs)),
            source_evidence_refs=(),
        )

    def _lexical_predication(self, sense: Any, lexical: Any) -> CandidatePredication | None:
        envelope = self._store.get(sense.record_id)
        payload = getattr(envelope, "payload", None)
        predicate_ref = getattr(payload, "semantic_schema_ref", "")
        if not predicate_ref:
            predicate_ref = getattr(payload, "predicate_schema_ref", "")
        predicate_roles = ()
        if not predicate_ref and getattr(envelope, "schema_kind", "") == "predicate":
            predicate_ref = envelope.record_id
            predicate_roles = tuple(
                str(role) for role in tuple(
                    getattr(payload, "role_refs", ()) or ()
                )
            )
        if not predicate_ref:
            return None
        predication = Predication(
            id=f"pred:{uuid4().hex[:12]}",
            predicate_schema_ref=predicate_ref,
            open_ports=tuple(
                OpenPort(
                    role if role.startswith("role:") else f"role:{role}",
                    True, "one"
                )
                for role in predicate_roles
            ),
            source_span_refs=tuple(f"span:{index}" for index in lexical.source_token_indices),
            confidence=sense.confidence * lexical.confidence,
        )
        return CandidatePredication(
            predication=predication,
            candidate_source="lexical",
            confidence=predication.confidence,
            source_token_indices=lexical.source_token_indices,
        )

    def _construction_predication(self, construction: Any) -> CandidatePredication | None:
        predicate_ref = self._resolve_predicate_ref(construction.predicate_schema_ref)
        bindings = tuple(
            RoleBinding(
                role_schema_ref=f"role:{role_key}",
                filler_ref=f"ref:token:{token_index}",
                confidence=construction.confidence,
            )
            for role_key, token_index in construction.role_mappings.items()
            if isinstance(token_index, int) and token_index >= 0
        )
        port = self._open_port_for(construction)
        predication = Predication(
            id=f"pred:{uuid4().hex[:12]}",
            predicate_schema_ref=predicate_ref,
            bindings=bindings,
            open_ports=(port,) if port is not None else (),
            source_span_refs=tuple(
                f"span:{index}" for index in construction.source_token_indices
            ),
            confidence=construction.confidence,
        )
        return CandidatePredication(
            predication=predication,
            candidate_source="construction",
            confidence=construction.confidence,
            source_token_indices=construction.source_token_indices,
        )

    def _embed_complements(
        self,
        evidence: SurfaceEvidence,
        predications: list[CandidatePredication],
        propositions: list[CandidateProposition],
        contexts: list[CandidateContext],
        ports: list[OpenPort],
        stream: TokenStream,
    ) -> tuple[
        list[CandidatePredication], list[CandidateProposition],
        list[CandidateContext], list[OpenPort],
    ]:
        complement_constructions = [
            construction for construction in evidence.construction_candidates
            if getattr(construction, "pattern", "") == "[predicate] [embedded_clause]"
        ]
        if not complement_constructions:
            return predications, propositions, contexts, ports

        for construction in complement_constructions:
            metadata = dict(getattr(construction, "metadata", {}) or {})
            embedded_role = str(metadata.get("embedded_role", "content"))
            capture_role = str(
                metadata.get("embedded_capture_role", embedded_role)
            )
            content_indices = construction.role_mappings.get(capture_role)
            if content_indices is None:
                continue
            if isinstance(content_indices, int):
                content_index = content_indices
            else:
                content_index = next(iter(content_indices), None)
            if content_index is None:
                continue
            inner_prop = self._embedded_proposition_ref(
                predications, propositions, content_index, construction
            )
            if not inner_prop:
                continue

            for index, candidate in enumerate(predications):
                if tuple(candidate.source_token_indices) != tuple(
                    construction.source_token_indices
                ):
                    continue
                bindings = tuple(
                    binding
                    for binding in candidate.predication.bindings
                    if binding.role_schema_ref != (
                        embedded_role if embedded_role.startswith("role:")
                        else f"role:{embedded_role}"
                    )
                ) + (
                    RoleBinding(
                        embedded_role if embedded_role.startswith("role:")
                        else f"role:{embedded_role}",
                        inner_prop, 0.85
                    ),
                )
                outer = Predication(
                    id=candidate.predication.id,
                    predicate_schema_ref=candidate.predication.predicate_schema_ref,
                    bindings=bindings,
                    open_ports=candidate.predication.open_ports,
                    occurrence_kind=candidate.predication.occurrence_kind,
                    aspect=candidate.predication.aspect,
                    source_span_refs=candidate.predication.source_span_refs,
                    evidence_refs=candidate.predication.evidence_refs,
                    confidence=candidate.predication.confidence,
                )
                predications[index] = CandidatePredication(
                    predication=outer,
                    candidate_source=candidate.candidate_source,
                    confidence=candidate.confidence,
                    source_evidence_refs=candidate.source_evidence_refs,
                    source_token_indices=candidate.source_token_indices,
                )
                # Mark the outer proposition as embedding the inner one.
                for p_index, proposition in enumerate(propositions):
                    if proposition.proposition.predication_ref == outer.id:
                        propositions[p_index] = CandidateProposition(
                            proposition=proposition.proposition,
                            candidate_source=proposition.candidate_source,
                            confidence=proposition.confidence,
                            embedded_proposition_refs=(inner_prop,),
                            source_evidence_refs=proposition.source_evidence_refs,
                        )
        return predications, propositions, contexts, ports

    def _resolve_predicate_ref(self, semantic_key: str) -> str:
        active = self._store.find_active(semantic_key)
        if active is not None:
            return active.record_id
        candidates = self._store.find_candidates(semantic_key)
        if candidates:
            return max(candidates, key=lambda item: item.version).record_id
        return semantic_key

    @staticmethod
    def _open_port_for(construction: Any) -> OpenPort | None:
        refs = tuple(getattr(construction, "open_role_refs", ()) or ())
        if not refs:
            return None
        return OpenPort(refs[0], True, "one")

    @staticmethod
    def _embedded_proposition_ref(
        predications: list[CandidatePredication],
        propositions: list[CandidateProposition],
        content_index: int,
        outer_construction: Any,
    ) -> str:
        outer_indices = tuple(getattr(outer_construction, "source_token_indices", ()) or ())
        predication_by_ref = {
            candidate.predication.id: candidate
            for candidate in predications
        }
        for proposition in propositions:
            candidate = predication_by_ref.get(proposition.proposition.predication_ref)
            if candidate is None:
                continue
            indices = tuple(candidate.source_token_indices)
            if indices == outer_indices:
                continue
            if indices and indices[0] == content_index:
                return proposition.proposition.id
        return ""

    @staticmethod
    def _polarity_for(candidate: CandidatePredication, stream: TokenStream) -> str:
        if not stream.has_negation:
            return "positive"
        indices = candidate.source_token_indices
        if not indices:
            return "positive"
        anchor = min(indices)
        for index, token in enumerate(stream.tokens):
            if token.is_negation and abs(index - anchor) <= 3:
                return "negative"
        return "positive"

    @staticmethod
    def _stable_opaque(surface: str, language: str) -> str:
        normalized = "_".join(surface.casefold().split())
        return f"opaque:{language}:{normalized}"

    @staticmethod
    def _is_grammatical_key(key: str) -> bool:
        return key.startswith((
            "pronoun:", "wh:", "copula:", "aux:", "determiner:", "polarity:",
        ))

    @staticmethod
    def _dedupe_ports(ports: list[OpenPort]) -> list[OpenPort]:
        seen: set[tuple[str, str]] = set()
        result: list[OpenPort] = []
        for port in ports:
            key = (port.role_schema_ref, port.cardinality)
            if key not in seen:
                seen.add(key)
                result.append(port)
        return result
