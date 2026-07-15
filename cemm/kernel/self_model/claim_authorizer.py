"""Authorize semantic predicates about self from live cognitive records."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable

from ..model.emission import PlannedClause, SelfClaimProof
from ..model.requirements import RequirementAssessment


@dataclass(frozen=True, slots=True)
class ClaimEvidence:
    evidence_id: str
    evidence_kind: str
    subject_ref: str
    semantic_target_ref: str = ""
    context_ref: str = ""
    valid_time_ref: str = ""
    successful: bool = True
    revision_fingerprint: str = ""
    provenance_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SelfClaimPolicy:
    policy_id: str
    predicate_key: str
    self_role_key: str
    evidence_kind: str
    target_role_key: str = ""
    requires_success: bool = True
    same_context_required: bool = True
    same_valid_time_required: bool = False


class SelfClaimAuthorizer:
    def __init__(self, policies: Iterable[SelfClaimPolicy]) -> None:
        self._policies = {policy.predicate_key: policy for policy in policies}

    @classmethod
    def load(cls, path: Path) -> "SelfClaimAuthorizer":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            SelfClaimPolicy(
                policy_id=item["policy_id"],
                predicate_key=item["predicate_key"],
                self_role_key=item["self_role_key"],
                evidence_kind=item["evidence_kind"],
                target_role_key=item.get("target_role_key", ""),
                requires_success=bool(item.get("requires_success", True)),
                same_context_required=bool(
                    item.get("same_context_required", True)
                ),
                same_valid_time_required=bool(
                    item.get("same_valid_time_required", False)
                ),
            )
            for item in raw
        )

    def authorize(
        self,
        clause: PlannedClause,
        *,
        evidence: Iterable[ClaimEvidence],
        requirement_assessments: Iterable[RequirementAssessment] = (),
    ) -> SelfClaimProof | None:
        policy = self._policies.get(clause.predicate_key)
        if policy is None:
            return None

        subject = clause.role(policy.self_role_key)
        if subject is None or subject.value_ref != "self":
            return None

        target = clause.role(policy.target_role_key) if policy.target_role_key else None
        target_ref = target.value_ref if target else ""

        if policy.evidence_kind == "goal_requirement":
            matches = tuple(
                assessment
                for assessment in requirement_assessments
                if assessment.requirer_ref == "self"
                and assessment.licenses_requirement_claim
                and (
                    not target_ref
                    or assessment.requirement_ref == target_ref
                    or assessment.goal_ref == target_ref
                )
                and (
                    not policy.same_context_required
                    or assessment.context_ref == clause.context_ref
                )
            )
            return SelfClaimProof(
                clause_ref=clause.clause_id,
                policy_ref=policy.policy_id,
                evidence_refs=tuple(item.assessment_id for item in matches),
                authorized=bool(matches),
                blocker_refs=()
                if matches
                else ("missing_live_goal_requirement_assessment",),
            )

        expected_success = clause.polarity != "negative"
        matches = tuple(
            item
            for item in evidence
            if item.evidence_kind == policy.evidence_kind
            and item.subject_ref == "self"
            and (
                not target_ref
                or item.semantic_target_ref == target_ref
            )
            and (
                not policy.requires_success
                or item.successful is expected_success
            )
            and (
                not policy.same_context_required
                or item.context_ref == clause.context_ref
            )
            and (
                not policy.same_valid_time_required
                or item.valid_time_ref == clause.valid_time_ref
            )
        )
        return SelfClaimProof(
            clause_ref=clause.clause_id,
            policy_ref=policy.policy_id,
            evidence_refs=tuple(item.evidence_id for item in matches),
            authorized=bool(matches),
            blocker_refs=()
            if matches
            else (f"missing_{policy.evidence_kind}_evidence",),
        )
