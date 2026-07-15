"""Executable goal/requirement semantics.

The module gives semantic content to "requires" without assuming any language
word.  A current requirement exists only when a live goal depends on an
unsatisfied specification in a particular context and valid-time interval.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable


class GoalStatus(str, Enum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    SATISFIED = "satisfied"
    ABANDONED = "abandoned"
    BLOCKED = "blocked"


class RequirementStatus(str, Enum):
    UNSATISFIED = "unsatisfied"
    PARTIALLY_SATISFIED = "partially_satisfied"
    SATISFIED = "satisfied"
    INVALID = "invalid"


@dataclass(frozen=True, slots=True)
class EvidenceField:
    field_key: str
    value_type: str
    required: bool = True
    semantic_constraint_refs: tuple[str, ...] = ()
    minimum_count: int = 1


@dataclass(frozen=True, slots=True)
class EvidenceSpecification:
    specification_id: str
    target_ref: str
    fields: tuple[EvidenceField, ...]
    context_ref: str
    valid_time_ref: str = ""
    source_independence_required: bool = False
    admissibility_policy_ref: str = ""
    provenance_refs: tuple[str, ...] = ()

    def required_field_keys(self) -> frozenset[str]:
        return frozenset(field.field_key for field in self.fields if field.required)


@dataclass(frozen=True, slots=True)
class GoalRecord:
    goal_id: str
    holder_ref: str
    desired_proposition_ref: str
    context_ref: str
    status: GoalStatus = GoalStatus.PROPOSED
    priority: float = 0.5
    valid_time_ref: str = ""
    provenance_refs: tuple[str, ...] = ()

    @property
    def is_live(self) -> bool:
        return self.status in {GoalStatus.ACTIVE, GoalStatus.BLOCKED}


@dataclass(frozen=True, slots=True)
class GoalDependency:
    dependency_id: str
    goal_ref: str
    requirement_ref: str
    dependency_kind: str = "necessary"
    context_ref: str = ""
    valid_time_ref: str = ""
    provenance_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RequirementEvidence:
    evidence_id: str
    specification_ref: str
    supplied_field_keys: frozenset[str]
    context_ref: str
    valid_time_ref: str = ""
    source_ref: str = ""
    confidence: float = 1.0
    admissible: bool = True
    independent_lineage_ref: str = ""
    provenance_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RequirementAssessment:
    assessment_id: str
    requirer_ref: str
    goal_ref: str
    requirement_ref: str
    context_ref: str
    status: RequirementStatus
    missing_field_keys: tuple[str, ...] = ()
    supporting_evidence_refs: tuple[str, ...] = ()
    blocker_refs: tuple[str, ...] = ()
    dependency_ref: str = ""
    valid_time_ref: str = ""
    revision_fingerprint: str = ""

    @property
    def licenses_requirement_claim(self) -> bool:
        return self.status in {
            RequirementStatus.UNSATISFIED,
            RequirementStatus.PARTIALLY_SATISFIED,
        } and bool(self.dependency_ref)


class RequirementEngine:
    """Derive current requirements from live goals and admissible evidence."""

    def assess(
        self,
        *,
        goals: Iterable[GoalRecord],
        dependencies: Iterable[GoalDependency],
        specifications: Iterable[EvidenceSpecification],
        evidence: Iterable[RequirementEvidence],
        revision_fingerprint: str,
    ) -> tuple[RequirementAssessment, ...]:
        goal_by_id = {goal.goal_id: goal for goal in goals}
        spec_by_id = {spec.specification_id: spec for spec in specifications}
        evidence_by_spec: dict[str, list[RequirementEvidence]] = {}
        for item in evidence:
            evidence_by_spec.setdefault(item.specification_ref, []).append(item)

        result: list[RequirementAssessment] = []
        for dependency in dependencies:
            goal = goal_by_id.get(dependency.goal_ref)
            spec = spec_by_id.get(dependency.requirement_ref)
            if goal is None or spec is None or not goal.is_live:
                continue
            context_ref = dependency.context_ref or goal.context_ref
            if spec.context_ref != context_ref:
                continue

            admissible = tuple(
                item
                for item in evidence_by_spec.get(spec.specification_id, ())
                if item.admissible and item.context_ref == context_ref
            )
            supplied = frozenset(
                field_key
                for item in admissible
                for field_key in item.supplied_field_keys
            )
            missing = tuple(sorted(spec.required_field_keys() - supplied))
            if not missing:
                status = RequirementStatus.SATISFIED
            elif supplied:
                status = RequirementStatus.PARTIALLY_SATISFIED
            else:
                status = RequirementStatus.UNSATISFIED
            result.append(
                RequirementAssessment(
                    assessment_id=(
                        f"requirement_assessment:{dependency.dependency_id}:"
                        f"{revision_fingerprint}"
                    ),
                    requirer_ref=goal.holder_ref,
                    goal_ref=goal.goal_id,
                    requirement_ref=spec.specification_id,
                    context_ref=context_ref,
                    status=status,
                    missing_field_keys=missing,
                    supporting_evidence_refs=tuple(item.evidence_id for item in admissible),
                    dependency_ref=dependency.dependency_id,
                    valid_time_ref=dependency.valid_time_ref or goal.valid_time_ref,
                    revision_fingerprint=revision_fingerprint,
                )
            )
        return tuple(result)
