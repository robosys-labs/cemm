#!/usr/bin/env python3
"""Build inert advisory pre-review records for R4.1 accountable review."""
from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping

from cemm_authoritative_hybrid.canonical import stable_ref
from scripts.r4_1_review_session import (
    ReviewAction,
    ReviewSession,
    _designation_risk,
)


MAX_PRE_REVIEW_RECORDS = 2048


class RecommendationClass(StrEnum):
    APPROVE_CANDIDATE = "approve_candidate"
    REJECT_AND_REPAIR = "reject_and_repair"
    NEEDS_INDIVIDUAL_REVIEW = "needs_individual_review"
    BLOCKED_EVIDENCE_MISMATCH = "blocked_evidence_mismatch"
    BLOCKED_INAPPLICABLE = "blocked_inapplicable"
    DEFER_UNTIL_PREREQUISITE = "defer_until_prerequisite"


@dataclass(frozen=True, slots=True)
class EvidenceIssue:
    issue_kind: str
    message: str
    ref: str | None = None


@dataclass(frozen=True, slots=True)
class PreflightResult:
    recommendation_class: RecommendationClass | None
    issues: tuple[EvidenceIssue, ...]
    action: object | None = None


@dataclass(frozen=True, slots=True)
class PreReviewRecord:
    record_ref: str
    item_ref: str
    phase: str
    row_kind: str
    source_ref: str
    recommendation_class: RecommendationClass
    rationale: str
    confidence: str
    action: Mapping[str, object] | None
    issues: tuple[EvidenceIssue, ...]
    cohort_eligible: bool

    def to_json(self) -> dict[str, object]:
        return {
            "record_ref": self.record_ref,
            "item_ref": self.item_ref,
            "phase": self.phase,
            "row_kind": self.row_kind,
            "source_ref": self.source_ref,
            "recommendation_class": self.recommendation_class.value,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "action": _wire(self.action),
            "issues": [
                {
                    "issue_kind": issue.issue_kind,
                    "message": issue.message,
                    "ref": issue.ref,
                }
                for issue in self.issues
            ],
            "cohort_eligible": self.cohort_eligible,
        }


def _nonempty_text(value: object) -> str | None:
    return value if type(value) is str and value.strip() else None


def _wire(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _wire(item) for key, item in value.items()}
    if type(value) in {list, tuple}:
        return [_wire(item) for item in value]
    if isinstance(value, StrEnum):
        return value.value
    return copy.deepcopy(value)


def _first_surface_example(row: Mapping[str, object]) -> str | None:
    scenario = row.get("resulting_scenario_row")
    if not isinstance(scenario, Mapping):
        return None
    examples = scenario.get("surface_examples")
    if type(examples) is not list or not examples:
        return None
    return _nonempty_text(examples[0])


def _binding_ref(binding: Mapping[str, object]) -> str | None:
    for key in ("binding_ref", "candidate_ref", "designation_fact_ref"):
        ref = binding.get(key)
        if type(ref) is str and ref:
            return ref
    return None


def preflight_designation_source(
    row: Mapping[str, object],
) -> PreflightResult:
    issues: list[EvidenceIssue] = []
    surface = _nonempty_text(row.get("surface"))
    candidate = _nonempty_text(row.get("candidate_output"))
    example = _first_surface_example(row)

    if surface is None:
        issues.append(
            EvidenceIssue(
                "missing_surface",
                "designation row lacks exact surface",
            )
        )
    if surface is not None and candidate is not None and candidate != surface:
        issues.append(
            EvidenceIssue(
                "candidate_output_mismatch",
                "candidate output differs from designation surface",
            )
        )
    if surface is not None and example is not None and example != surface:
        issues.append(
            EvidenceIssue(
                "surface_example_order_mismatch",
                "surface example differs from designation surface",
            )
        )

    bindings = row.get("candidate_bindings")
    if type(bindings) not in {list, tuple}:
        issues.append(
            EvidenceIssue(
                "invalid_candidate_bindings",
                "candidate bindings are not a bounded sequence",
            )
        )
    elif surface is not None:
        for binding in bindings:
            if not isinstance(binding, Mapping):
                issues.append(
                    EvidenceIssue(
                        "invalid_binding",
                        "candidate binding is not an object",
                    )
                )
                continue
            start = binding.get("start")
            end = binding.get("end")
            expected = binding.get("surface")
            ref = _binding_ref(binding)
            if (
                type(start) is not int
                or type(end) is not int
                or type(expected) is not str
                or start < 0
                or end < start
                or end > len(surface)
            ):
                issues.append(
                    EvidenceIssue(
                        "invalid_span",
                        "candidate binding span is outside the surface",
                        ref,
                    )
                )
                continue
            if surface[start:end] != expected:
                issues.append(
                    EvidenceIssue(
                        "span_text_mismatch",
                        (
                            "candidate binding span text differs from "
                            "exact surface"
                        ),
                        ref,
                    )
                )

    if issues:
        return PreflightResult(
            recommendation_class=(
                RecommendationClass.BLOCKED_EVIDENCE_MISMATCH
            ),
            issues=tuple(issues),
        )
    return PreflightResult(recommendation_class=None, issues=())


def _item_ref(
    *,
    phase: str,
    row_kind: str,
    source_ref: str,
) -> str:
    return stable_ref(
        "r4_1_pre_review_item",
        {
            "phase": phase,
            "row_kind": row_kind,
            "source_ref": source_ref,
        },
    )


def _action_to_wire(action: ReviewAction) -> dict[str, object]:
    return {
        "action_kind": action.action_kind,
        "target_refs": list(action.target_refs),
        "selected_value": _wire(action.selected_value),
    }


def _record(
    *,
    phase: str,
    row_kind: str,
    source_ref: str,
    recommendation_class: RecommendationClass,
    rationale: str,
    confidence: str,
    action: Mapping[str, object] | None = None,
    issues: tuple[EvidenceIssue, ...] = (),
    cohort_eligible: bool = False,
) -> PreReviewRecord:
    item_ref = _item_ref(
        phase=phase,
        row_kind=row_kind,
        source_ref=source_ref,
    )
    material = {
        "item_ref": item_ref,
        "phase": phase,
        "row_kind": row_kind,
        "source_ref": source_ref,
        "recommendation_class": recommendation_class.value,
        "action": _wire(action),
        "issues": [
            {
                "issue_kind": issue.issue_kind,
                "message": issue.message,
                "ref": issue.ref,
            }
            for issue in issues
        ],
    }
    return PreReviewRecord(
        record_ref=stable_ref("r4_1_pre_review_record", material),
        item_ref=item_ref,
        phase=phase,
        row_kind=row_kind,
        source_ref=source_ref,
        recommendation_class=recommendation_class,
        rationale=rationale,
        confidence=confidence,
        action=copy.deepcopy(action),
        issues=issues,
        cohort_eligible=cohort_eligible,
    )


def _structural_record(row: Mapping[str, object]) -> PreReviewRecord:
    return _record(
        phase="structural",
        row_kind=str(row["row_kind"]),
        source_ref=str(row["row_ref"]),
        recommendation_class=RecommendationClass.NEEDS_INDIVIDUAL_REVIEW,
        rationale=(
            "Structural choices define proposal eligibility and branch "
            "ownership, so the accountable reviewer must curate them directly."
        ),
        confidence="human_required",
    )


def _purpose_record(row: Mapping[str, object]) -> PreReviewRecord:
    return _record(
        phase="purpose",
        row_kind=str(row["row_kind"]),
        source_ref=str(row["row_ref"]),
        recommendation_class=RecommendationClass.NEEDS_INDIVIDUAL_REVIEW,
        rationale=(
            "Purpose assignment controls train, selection, calibration and "
            "frozen-test leakage, so it remains individually curated."
        ),
        confidence="human_required",
    )


def _recipe_record(row: Mapping[str, object]) -> PreReviewRecord:
    return _record(
        phase="recipe",
        row_kind="proposal_recipe_family",
        source_ref=str(row["family_ref"]),
        recommendation_class=RecommendationClass.NEEDS_INDIVIDUAL_REVIEW,
        rationale=(
            "Recipe-family approval affects R4 proposal expansion and R5 "
            "training provenance, so it requires direct reviewer judgment."
        ),
        confidence="human_required",
    )


def _designation_record(
    *,
    session: ReviewSession,
    row: Mapping[str, object],
) -> PreReviewRecord:
    case_ref = str(row["source_case_ref"])
    preflight = preflight_designation_source(row)
    if preflight.recommendation_class is not None:
        return _record(
            phase="designation",
            row_kind="designation_supervision",
            source_ref=case_ref,
            recommendation_class=preflight.recommendation_class,
            rationale=(
                "Exact designation source geometry is not internally "
                "reviewable; repair the earliest source/display owner first."
            ),
            confidence="blocked",
            issues=preflight.issues,
        )

    exceptional, _, _, empty, _ = _designation_risk(row)
    if exceptional:
        return _record(
            phase="designation",
            row_kind="designation_supervision",
            source_ref=case_ref,
            recommendation_class=RecommendationClass.NEEDS_INDIVIDUAL_REVIEW,
            rationale=(
                "Exceptional designation cases require careful individual "
                "curation before they can become review selections."
            ),
            confidence="human_required",
        )

    if case_ref not in session.indexes.designation_cohort_by_case:
        return _record(
            phase="designation",
            row_kind="designation_supervision",
            source_ref=case_ref,
            recommendation_class=RecommendationClass.NEEDS_INDIVIDUAL_REVIEW,
            rationale=(
                "The designation case is not owned by a routine cohort and "
                "must be inspected individually."
            ),
            confidence="human_required",
        )

    decision = "approve_exact_empty" if empty else "approve_candidate_bindings"
    action = ReviewAction.designation_cases(
        case_refs=(case_ref,),
        decision=decision,
        individual=True,
    )
    return _record(
        phase="designation",
        row_kind="designation_supervision",
        source_ref=case_ref,
        recommendation_class=RecommendationClass.APPROVE_CANDIDATE,
        rationale=(
            "Routine non-exceptional designation geometry is internally "
            "consistent and names exact candidate bindings."
        ),
        confidence="mechanical_high",
        action=_action_to_wire(action),
        cohort_eligible=True,
    )


def build_pre_review_records(
    session: ReviewSession,
) -> tuple[PreReviewRecord, ...]:
    records: list[PreReviewRecord] = []
    records.extend(
        _structural_record(row)
        for _, row in sorted(session.indexes.structural_rows_by_ref.items())
    )
    records.extend(
        _purpose_record(row)
        for _, row in sorted(session.indexes.purpose_rows_by_ref.items())
    )
    records.extend(
        _recipe_record(row)
        for _, row in sorted(session.indexes.proposal_families_by_ref.items())
    )
    records.extend(
        _designation_record(session=session, row=row)
        for _, row in sorted(session.indexes.designation_rows_by_case.items())
    )
    if len(records) > MAX_PRE_REVIEW_RECORDS:
        raise ValueError("pre-review record count exceeds bound")
    return tuple(records)
