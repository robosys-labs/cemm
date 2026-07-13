"""Sandboxed competence harness — non-mutating competence tests.

Import boundary: model + schema submodules only. No engine imports.

Architectural guardrails (UNDERSTANDING_PIPELINE.md §10, AGENTS.md §7.3):
- Competence checks are non-mutating and sandboxed.
- Minimum generic checks:
    compose a positive case
    preserve required role/context/polarity structure
    answer a defining query
    distinguish a real contrast or alternative
    perform a licensed inference
    realize/reparse where language resources exist
- Competence cases derived from the definition may test well-formedness
  only. They cannot independently certify discrimination, truth, or
  promotion.
- The same implementation path cannot generate input meaning, expected
  graph, and pass judgment without an independent invariant.
- Lineage rules:
    a case derived from the teaching utterance tests structure only;
    translations/paraphrases/generated examples inherit the same lineage;
    negative cases cannot pass from missing evidence alone;
    independent discrimination uses an audited invariant, independently
    grounded sibling/contrast, adapter observation, or independently
    authored expected pattern.
- Open-world negative cases: 'neither' is not rejection. A negative case
  passes only when the candidate schema derives an incompatibility or
  a better alternative.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Protocol

from .closure import CompetenceProfile
from .provenance import (
    ContributionRecord, ProvenanceKind, FieldProvenanceMap,
    INDEPENDENT_PROVENANCE, WEAK_PROVENANCE,
)


class CompetenceCheckKind(str, Enum):
    POSITIVE_CASE = "positive_case"
    ROLE_STRUCTURE = "role_structure"
    DEFINING_QUERY = "defining_query"
    CONTRAST = "contrast"
    LICENSED_INFERENCE = "licensed_inference"
    REALIZE_REPARSE = "realize_reparse"


class ContrastResult(str, Enum):
    SUPPORTED = "supported"
    REFUTED = "refuted"
    BOTH = "both"
    NEITHER = "neither"


@dataclass(frozen=True, slots=True)
class CompetenceCase:
    """A single competence test case.

    Records input generation lineage and oracle lineage.
    """
    case_id: str
    check_kind: CompetenceCheckKind
    input_lineage: str = ""  # source of the input
    oracle_lineage: str = ""  # source of the expected result
    is_independent: bool = False  # whether input and oracle are independent
    passed: bool = False
    detail: str = ""
    contrast_result: ContrastResult | None = None


@dataclass(frozen=True, slots=True)
class CompetenceAssessment:
    """Complete competence assessment for a schema revision.

    Records all competence cases, their lineage, and whether the
    assessment is self-certified.
    """
    cases: tuple[CompetenceCase, ...] = ()
    is_self_certified: bool = False
    independent_oracle_count: int = 0
    profile: CompetenceProfile | None = None

    @property
    def is_competent(self) -> bool:
        """Check if the competence assessment meets minimum requirements."""
        if self.is_self_certified:
            return False
        if self.profile is None:
            return False
        return self.profile.is_competent


class CompetenceHarness:
    """Sandboxed, non-mutating competence test runner.

    Runs competence checks against a schema revision without mutating
    any state. Checks that the same implementation path is not both
    generating inputs and judging results (self-certification).
    """

    def assess(
        self,
        cases: tuple[CompetenceCase, ...],
        implementation_path: str = "",
    ) -> CompetenceAssessment:
        """Assess competence from a set of test cases.

        Checks:
        1. Self-certification: same path generating input and oracle
        2. Minimum checks: positive case, role structure, defining query,
           contrast, licensed inference
        3. Independent oracle count
        4. Open-world negative cases: 'neither' is not rejection
        """
        # Check for self-certification
        self_certified = False
        for case in cases:
            if (case.input_lineage == implementation_path
                    and case.oracle_lineage == implementation_path
                    and not case.is_independent):
                self_certified = True

        # Count independent oracles
        independent_oracles = sum(
            1 for c in cases
            if c.is_independent and c.oracle_lineage != implementation_path
        )

        # Build competence profile from cases
        positive_passed = any(
            c.check_kind == CompetenceCheckKind.POSITIVE_CASE and c.passed
            for c in cases
        )
        role_structure = any(
            c.check_kind == CompetenceCheckKind.ROLE_STRUCTURE and c.passed
            for c in cases
        )
        defining_query = any(
            c.check_kind == CompetenceCheckKind.DEFINING_QUERY and c.passed
            for c in cases
        )
        contrast = any(
            c.check_kind == CompetenceCheckKind.CONTRAST
            and c.passed
            and c.contrast_result in (ContrastResult.SUPPORTED, ContrastResult.REFUTED)
            for c in cases
        )
        licensed_inference = any(
            c.check_kind == CompetenceCheckKind.LICENSED_INFERENCE and c.passed
            for c in cases
        )

        profile = CompetenceProfile(
            positive_case_passed=positive_passed,
            role_structure_preserved=role_structure,
            defining_query_answered=defining_query,
            contrast_distinguished=contrast,
            licensed_inference_performed=licensed_inference,
            independent_oracle_count=independent_oracles,
            self_certified=self_certified,
        )

        return CompetenceAssessment(
            cases=cases,
            is_self_certified=self_certified,
            independent_oracle_count=independent_oracles,
            profile=profile,
        )
