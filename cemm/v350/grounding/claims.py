"""Claim-source and audience grounding without epistemic admission.

The compiler validates participants against the exact schema revision introduced
by the selected claim-event candidate.  It deliberately contains no ontology
shortcut such as a hard-coded list of agent type refs.
"""
from __future__ import annotations

from typing import Iterable

from ..schema.model import EventSchema, LocalPortSchema, PortFillerClass, StorageKind, UseOperation, semantic_fingerprint
from ..storage import SemanticStore, StoreSnapshot
from .model import ClaimGrounding, GroundingAssignment, GroundingCandidate, GroundingResult


class ClaimGroundingError(ValueError):
    pass


class ClaimGroundingCompiler:
    def __init__(self, store: SemanticStore) -> None:
        self.store = store

    def compile(
        self,
        grounding: GroundingResult,
        *,
        claim_mention_ref: str,
        proposition_ref: str,
        source_mention_ref: str,
        audience_mention_refs: Iterable[str] = (),
        source_context_ref: str,
        reported_context_ref: str,
        assignment_ref: str | None = None,
        evidence_refs: tuple[str, ...] = (),
        snapshot: StoreSnapshot | None = None,
    ) -> ClaimGrounding:
        if snapshot is not None:
            self.store.assert_snapshot(snapshot)
        assignment = self._assignment(grounding, assignment_ref)
        mapping = dict(assignment.mention_to_target)
        mention_by_ref = {item.mention_ref: item for item in grounding.mentions}
        candidate_by_ref = {item.candidate_ref: item for item in grounding.candidates}
        selected_by_mention = {
            candidate_by_ref[candidate_ref].mention_ref: candidate_by_ref[candidate_ref]
            for candidate_ref in assignment.candidate_refs
        }

        claim_mention = mention_by_ref.get(claim_mention_ref)
        if claim_mention is None:
            raise ClaimGroundingError(f"unknown claim mention: {claim_mention_ref}")
        claim_candidate = selected_by_mention.get(claim_mention_ref)
        if claim_candidate is None:
            raise ClaimGroundingError(f"claim event is unresolved: {claim_mention_ref}")
        if claim_candidate.storage_kind != StorageKind.EVENT_OCCURRENCE:
            raise ClaimGroundingError("claim occurrence must resolve to event-occurrence storage")

        schema, source_port, content_port, audience_ports = self._claim_contract(
            claim_candidate, snapshot=snapshot
        )

        source_mention = mention_by_ref.get(source_mention_ref)
        if source_mention is None:
            raise ClaimGroundingError(f"unknown claim source mention: {source_mention_ref}")
        source_candidate = selected_by_mention.get(source_mention_ref)
        if source_candidate is None:
            raise ClaimGroundingError(f"claim source is unresolved: {source_mention_ref}")
        self._require_port_candidate(source_candidate, source_port, "claim source")
        source_ref = mapping[source_mention_ref]

        audience_mentions = tuple(audience_mention_refs)
        audiences: list[str] = []
        relevant_candidates = [claim_candidate, source_candidate]
        for mention_ref in audience_mentions:
            audience_mention = mention_by_ref.get(mention_ref)
            if audience_mention is None:
                raise ClaimGroundingError(f"unknown claim audience mention: {mention_ref}")
            audience_candidate = selected_by_mention.get(mention_ref)
            if audience_candidate is None:
                raise ClaimGroundingError(f"claim audience is unresolved: {mention_ref}")
            compatible_audience_ports = tuple(
                port for port in audience_ports
                if self._port_accepts_candidate(audience_candidate, port)
            )
            if not compatible_audience_ports:
                raise ClaimGroundingError(
                    f"schema {schema.schema_ref}@{schema.revision} does not license this claim audience candidate"
                )
            relevant_candidates.append(audience_candidate)
            audiences.append(mapping[mention_ref])

        if source_context_ref == reported_context_ref:
            raise ClaimGroundingError("reported proposition must remain in an attributed context")
        factors = [factor for candidate in relevant_candidates for factor in candidate.factors]
        confidence = 1.0
        if factors:
            confidence = max(
                0.0,
                min(1.0, 0.5 + sum(item.score for item in factors) / (10 * len(factors))),
            )
        if any(item.provisional for item in relevant_candidates):
            confidence = min(confidence, 0.49)
        refs = tuple(sorted(set(evidence_refs) | set(grounding.evidence_refs)))
        return ClaimGrounding(
            claim_grounding_ref="claim-grounding:" + semantic_fingerprint(
                "claim-grounding-ref",
                (
                    claim_mention_ref,
                    proposition_ref,
                    source_ref,
                    tuple(sorted(audiences)),
                    source_context_ref,
                    reported_context_ref,
                    schema.schema_ref,
                    schema.revision,
                    assignment.assignment_ref,
                ),
                24,
            ),
            claim_mention_ref=claim_mention_ref,
            proposition_ref=proposition_ref,
            source_ref=source_ref,
            audience_refs=tuple(sorted(set(audiences))),
            source_context_ref=source_context_ref,
            reported_context_ref=reported_context_ref,
            evidence_refs=refs or (f"grounding:{grounding.grounding_ref}",),
            confidence=confidence,
            admission_refs=(),
        )

    def _claim_contract(
        self, candidate: GroundingCandidate, *, snapshot: StoreSnapshot | None
    ):
        """Resolve claim structure from the exact schema contract, never names.

        A claim-like schema declares that its content is not itself admission.
        The content port is the unique proposition-storage port.  The source is
        the unique required identity-contributing referent port.  Remaining
        referent ports are possible audiences/participants and are validated
        by their own type/storage contracts when actually used.
        """
        pins = tuple(candidate.metadata.get("introduced_by_schema_pins", ()))
        if not pins:
            raise ClaimGroundingError(
                "claim event candidate must preserve an exact introducing schema revision"
            )
        registry = self.store.repositories.schemas.registry(snapshot=snapshot)
        matches = []
        for schema_ref, revision in pins:
            schema = registry.schema(str(schema_ref), int(revision))
            if not isinstance(schema, EventSchema) or not schema.use_profile.permits(UseOperation.GROUND):
                continue
            content_ports = tuple(
                port for port in schema.local_ports
                if StorageKind.PROPOSITION in port.accepted_storage_kinds
            )
            source_ports = tuple(
                port for port in schema.local_ports
                if port.identity_contribution
                and port.cardinality.minimum > 0
                and PortFillerClass.REFERENT in port.filler_classes
                and port not in content_ports
            )
            if len(content_ports) != 1 or len(source_ports) != 1:
                continue
            audience_ports = tuple(
                port for port in schema.local_ports
                if port not in content_ports and port not in source_ports
                and PortFillerClass.REFERENT in port.filler_classes
            )
            matches.append((schema, source_ports[0], content_ports[0], audience_ports))
        if len(matches) != 1:
            raise ClaimGroundingError(
                "claim occurrence requires exactly one exact structurally declared claim contract"
            )
        return matches[0]

    @staticmethod
    def _port_accepts_candidate(candidate: GroundingCandidate, port: LocalPortSchema) -> bool:
        if port.accepted_storage_kinds and candidate.storage_kind not in port.accepted_storage_kinds:
            return False
        if port.accepted_type_refs and not set(port.accepted_type_refs).intersection(candidate.type_refs):
            return False
        return True

    @staticmethod
    def _require_port_candidate(
        candidate: GroundingCandidate, port: LocalPortSchema, label: str
    ) -> None:
        if port.accepted_storage_kinds and candidate.storage_kind not in port.accepted_storage_kinds:
            raise ClaimGroundingError(f"{label} violates schema storage constraints")
        if port.accepted_type_refs and not set(port.accepted_type_refs).intersection(candidate.type_refs):
            raise ClaimGroundingError(f"{label} violates schema type constraints")

    @staticmethod
    def _assignment(
        grounding: GroundingResult, assignment_ref: str | None
    ) -> GroundingAssignment:
        if assignment_ref is None:
            selected = grounding.selected
            if selected is None:
                raise ClaimGroundingError(
                    "claim grounding requires an explicit assignment while identity is ambiguous"
                )
            return selected
        assignment = next(
            (item for item in grounding.assignments if item.assignment_ref == assignment_ref), None
        )
        if assignment is None:
            raise ClaimGroundingError(f"unknown grounding assignment: {assignment_ref}")
        return assignment
