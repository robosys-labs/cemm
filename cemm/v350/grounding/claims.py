"""Claim-source and audience grounding without epistemic admission."""
from __future__ import annotations

from typing import Iterable

from ..schema.model import StorageKind, semantic_fingerprint
from .model import ClaimGrounding, GroundingAssignment, GroundingResult


class ClaimGroundingError(ValueError):
    pass


class ClaimGroundingCompiler:
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
    ) -> ClaimGrounding:
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
        if claim_mention.target_class.value not in {"event", "claim"}:
            raise ClaimGroundingError("claim mention must be typed as an event or claim")
        claim_candidate = selected_by_mention.get(claim_mention_ref)
        if claim_candidate is None:
            raise ClaimGroundingError(f"claim event is unresolved: {claim_mention_ref}")
        if claim_candidate.storage_kind != StorageKind.EVENT_OCCURRENCE:
            raise ClaimGroundingError("claim event must resolve to an event occurrence")
        if not {"type:event_occurrence", "type:claim_information"}.intersection(
            claim_candidate.type_refs
        ):
            raise ClaimGroundingError("claim event candidate lacks claim/event type evidence")

        source_mention = mention_by_ref.get(source_mention_ref)
        if source_mention is None:
            raise ClaimGroundingError(f"unknown claim source mention: {source_mention_ref}")
        if source_mention.target_class.value not in {"claim_source", "referent"}:
            raise ClaimGroundingError("claim source mention is not referential")
        source_candidate = selected_by_mention.get(source_mention_ref)
        if source_candidate is None:
            raise ClaimGroundingError(f"claim source is unresolved: {source_mention_ref}")
        self._require_agent_candidate(source_candidate, "claim source")
        source_ref = mapping[source_mention_ref]

        audience_mentions = tuple(audience_mention_refs)
        audiences = []
        relevant_candidates = [claim_candidate, source_candidate]
        for mention_ref in audience_mentions:
            audience_mention = mention_by_ref.get(mention_ref)
            if audience_mention is None:
                raise ClaimGroundingError(f"unknown claim audience mention: {mention_ref}")
            if audience_mention.target_class.value not in {"audience", "referent"}:
                raise ClaimGroundingError("claim audience mention is not referential")
            audience_candidate = selected_by_mention.get(mention_ref)
            if audience_candidate is None:
                raise ClaimGroundingError(f"claim audience is unresolved: {mention_ref}")
            self._require_agent_candidate(audience_candidate, "claim audience")
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
            # An explicitly selected provisional identity is usable for attributed
            # claim structure, but must never masquerade as settled identity.
            confidence = min(confidence, 0.49)
        refs = tuple(sorted(set(evidence_refs) | set(grounding.evidence_refs)))
        return ClaimGrounding(
            claim_grounding_ref="claim-grounding:" + semantic_fingerprint(
                "claim-grounding-ref",
                (claim_mention_ref, proposition_ref, source_ref, tuple(sorted(audiences)),
                 source_context_ref, reported_context_ref, assignment.assignment_ref),
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

    @staticmethod
    def _require_agent_candidate(candidate, label: str) -> None:
        agent_types = {
            "type:agent",
            "type:natural_agent",
            "type:software_agent",
            "type:collective_agent",
            "type:institutional_agent",
        }
        if not agent_types.intersection(candidate.type_refs):
            raise ClaimGroundingError(f"{label} must resolve to an agent-compatible referent")

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
