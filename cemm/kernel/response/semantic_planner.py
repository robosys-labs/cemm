"""Language-neutral semantic response planning.

The planner creates only semantic clauses.  It does not choose words.  In
particular, it can plan a self requirement clause only from a live
RequirementAssessment that licenses that claim.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable
from uuid import uuid4

from ..model.emission import (
    PlannedClause,
    SemanticMessagePlan,
    SemanticRoleValue,
    UseMode,
)
from ..model.requirements import RequirementAssessment, RequirementStatus


@dataclass(frozen=True, slots=True)
class InformationRequestIntent:
    intent_id: str
    requester_ref: str
    addressee_ref: str
    requirement_assessment_ref: str
    requirement_ref: str
    goal_ref: str
    target_ref: str
    target_surface: str
    context_ref: str
    valid_time_ref: str = ""
    provenance_refs: tuple[str, ...] = ()


class SemanticResponsePlanner:
    def plan_requirement_request(
        self,
        intent: InformationRequestIntent,
        assessments: Iterable[RequirementAssessment],
        *,
        language_tag: str,
    ) -> SemanticMessagePlan:
        assessment = next(
            (
                item
                for item in assessments
                if item.assessment_id == intent.requirement_assessment_ref
                and item.requirer_ref == intent.requester_ref
                and item.requirement_ref == intent.requirement_ref
                and item.goal_ref == intent.goal_ref
                and item.context_ref == intent.context_ref
                and item.licenses_requirement_claim
            ),
            None,
        )
        if assessment is None:
            return SemanticMessagePlan(
                plan_id=f"message_plan:{uuid4().hex[:12]}",
                clauses=(),
                language_tag=language_tag,
                addressee_refs=(intent.addressee_ref,),
                goal_refs=(intent.goal_ref,),
                provenance_refs=intent.provenance_refs,
            )

        provenance = tuple(
            dict.fromkeys(
                (
                    *intent.provenance_refs,
                    assessment.assessment_id,
                    assessment.dependency_ref,
                    *assessment.supporting_evidence_refs,
                )
            )
        )
        clause = PlannedClause(
            clause_id=f"clause:requirement:{uuid4().hex[:12]}",
            predicate_key="requires_for_goal",
            roles=(
                SemanticRoleValue(
                    role_key="requirer",
                    value_ref=intent.requester_ref,
                    value_kind="referent",
                    provenance_refs=(assessment.assessment_id,),
                ),
                SemanticRoleValue(
                    role_key="requirement",
                    value_ref=intent.requirement_ref,
                    value_kind="referent",
                    semantic_key="evidence_specification",
                    provenance_refs=(assessment.assessment_id,),
                ),
                SemanticRoleValue(
                    role_key="goal",
                    value_ref=intent.goal_ref,
                    value_kind="referent",
                    semantic_key="goal",
                    provenance_refs=(assessment.assessment_id,),
                ),
                SemanticRoleValue(
                    role_key="target",
                    value_ref=intent.target_ref,
                    value_kind="referent",
                    surface_hint=intent.target_surface,
                    use_mode=UseMode.MENTION,
                    provenance_refs=intent.provenance_refs,
                ),
                SemanticRoleValue(
                    role_key="context",
                    value_ref=intent.context_ref,
                    value_kind="context",
                    provenance_refs=(assessment.assessment_id,),
                ),
            ),
            communicative_force="request",
            polarity="positive",
            context_ref=intent.context_ref,
            valid_time_ref=intent.valid_time_ref,
            provenance_refs=provenance,
        )
        return SemanticMessagePlan(
            plan_id=f"message_plan:{uuid4().hex[:12]}",
            clauses=(clause,),
            language_tag=language_tag,
            addressee_refs=(intent.addressee_ref,),
            goal_refs=(intent.goal_ref,),
            provenance_refs=provenance,
        )
