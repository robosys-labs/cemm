#!/usr/bin/env python3
"""Build inert advisory pre-review records for R4.1 accountable review."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


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


def _nonempty_text(value: object) -> str | None:
    return value if type(value) is str and value.strip() else None


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
