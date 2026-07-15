"""Canonical language-neutral response-intent planner.

The planner consumes already-decided semantic intents. It never inspects words
or transcript phrases. Missing intent evidence produces an empty message plan,
not a guessed response.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from ..model.emission import (
    PlannedClause,
    SemanticMessagePlan,
    SemanticRoleValue,
    UseMode,
)
from ..model.requirements import RequirementAssessment


@dataclass(frozen=True, slots=True)
class ResponseIntentRole:
    role_key: str
    value_ref: str
    value_kind: str
    semantic_key: str = ""
    surface_hint: str = ""
    use_mode: str = "assert"
    provenance_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResponseIntent:
    intent_id: str
    predicate_key: str
    roles: tuple[ResponseIntentRole, ...]
    communicative_force: str
    context_ref: str
    polarity: str = "positive"
    modality: str = "actual"
    valid_time_ref: str = ""
    qualification_key: str = ""
    goal_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ContentSelectionInput:
    response_intents: tuple[ResponseIntent, ...] = ()
    requirement_assessments: tuple[RequirementAssessment, ...] = ()
    language: str = "und"
    channel: str = "text"
    addressee_ref: str = "user"

    # Transitional fields are accepted but never used as phrase-routing
    # authorities. DECIDE must convert them into ResponseIntent records.
    selected_interpretations: tuple[Any, ...] = ()
    gaps: tuple[Any, ...] = ()
    retrieval_results: tuple[Any, ...] = ()
    capability_assessments: tuple[Any, ...] = ()
    learning_transactions: tuple[Any, ...] = ()
    commit_outcome: Any | None = None


class ResponsePlanner:
    def plan_response(
        self,
        selection: ContentSelectionInput,
    ) -> SemanticMessagePlan:
        clauses: list[PlannedClause] = []
        goals: list[str] = []
        provenance: list[str] = []

        for intent in selection.response_intents:
            if not intent.provenance_refs:
                continue
            if (
                intent.predicate_key == "requires_for_goal"
                and not self._requirement_intent_authorized(
                    intent,
                    selection.requirement_assessments,
                )
            ):
                continue

            roles = tuple(
                SemanticRoleValue(
                    role_key=role.role_key,
                    value_ref=role.value_ref,
                    value_kind=role.value_kind,
                    semantic_key=role.semantic_key,
                    surface_hint=role.surface_hint,
                    use_mode=UseMode(role.use_mode),
                    provenance_refs=role.provenance_refs,
                )
                for role in intent.roles
            )
            clauses.append(
                PlannedClause(
                    clause_id=f"clause:{intent.intent_id}",
                    predicate_key=intent.predicate_key,
                    roles=roles,
                    communicative_force=intent.communicative_force,
                    polarity=intent.polarity,
                    modality=intent.modality,
                    context_ref=intent.context_ref,
                    valid_time_ref=intent.valid_time_ref,
                    qualification_key=intent.qualification_key,
                    provenance_refs=intent.provenance_refs,
                )
            )
            goals.extend(intent.goal_refs)
            provenance.extend(intent.provenance_refs)

        return SemanticMessagePlan(
            plan_id=f"message_plan:{uuid4().hex[:12]}",
            clauses=tuple(clauses),
            language_tag=selection.language,
            channel=selection.channel,
            addressee_refs=(selection.addressee_ref,),
            goal_refs=tuple(dict.fromkeys(goals)),
            provenance_refs=tuple(dict.fromkeys(provenance)),
        )

    @staticmethod
    def _requirement_intent_authorized(
        intent: ResponseIntent,
        assessments: tuple[RequirementAssessment, ...],
    ) -> bool:
        role_map = {role.role_key: role.value_ref for role in intent.roles}
        return any(
            assessment.licenses_requirement_claim
            and assessment.requirer_ref == role_map.get("requirer")
            and assessment.requirement_ref == role_map.get("requirement")
            and assessment.goal_ref == role_map.get("goal")
            and assessment.context_ref == intent.context_ref
            for assessment in assessments
        )
