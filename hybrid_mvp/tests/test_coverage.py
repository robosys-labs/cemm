"""Tests for the exact coverage ABI.

``CoverageVerifier`` proves the program already contains exactly one
assignment per source unit, valid contribution-to-port binding, explicit typed
residuals, and correct criticality.  It never repairs or synthesizes an
assignment.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from cemm_authoritative_hybrid.coverage import (
    CoverageReceipt,
    CriticalResidual,
    CoverageVerifier,
)
from cemm_authoritative_hybrid.programs import (
    ProgramAction,
    SourceAssignment,
    SemanticSwitchProgram,
)


# ---------------------------------------------------------------------------
# Complete coverage
# ---------------------------------------------------------------------------


def test_every_source_unit_is_consumed_once_or_one_residual(coverage_verifier, case):
    receipt = coverage_verifier.verify(case.lattice, case.program)
    assert receipt.duplicate_unit_refs == ()
    assert receipt.missing_unit_refs == ()
    assert set(receipt.assigned_unit_refs).isdisjoint(receipt.residual_unit_refs)


def test_complete_coverage_is_executable(coverage_verifier, case):
    receipt = coverage_verifier.verify(case.lattice, case.program)
    assert receipt.executable
    assert receipt.critical_residuals == ()


def test_coverage_receipt_has_stable_hash(coverage_verifier, case):
    a = coverage_verifier.verify(case.lattice, case.program)
    b = coverage_verifier.verify(case.lattice, case.program)
    assert a.coverage_hash == b.coverage_hash


# ---------------------------------------------------------------------------
# Missing / duplicate program assignments are rejected
# ---------------------------------------------------------------------------


def test_missing_or_duplicate_program_assignment_is_rejected(coverage_verifier, valid_program):
    assert (
        coverage_verifier.verify(with_assignment_removed(valid_program)).errors[0].code
        == "missing_source_assignment"
    )
    assert (
        coverage_verifier.verify(with_assignment_duplicated(valid_program)).errors[0].code
        == "duplicate_source_assignment"
    )


def test_missing_assignment_populates_missing_unit_refs(coverage_verifier, valid_program):
    receipt = coverage_verifier.verify(with_assignment_removed(valid_program))
    assert len(receipt.missing_unit_refs) == 1
    assert not receipt.executable


def test_duplicate_assignment_populates_duplicate_unit_refs(coverage_verifier, valid_program):
    receipt = coverage_verifier.verify(with_assignment_duplicated(valid_program))
    assert len(receipt.duplicate_unit_refs) == 1
    assert not receipt.executable


def test_valid_program_has_no_assignment_errors(coverage_verifier, valid_program):
    receipt = coverage_verifier.verify(valid_program)
    assert receipt.errors == ()
    assert receipt.missing_unit_refs == ()
    assert receipt.duplicate_unit_refs == ()


# ---------------------------------------------------------------------------
# Critical residuals reject execution
# ---------------------------------------------------------------------------


def test_critical_residual_rejects_execution(coverage_verifier, negated_effect_case):
    receipt = coverage_verifier.verify(*negated_effect_case)
    assert not receipt.executable
    assert receipt.critical_residuals[0].contribution_kind == "scope"


def test_critical_residual_records_source_unit(coverage_verifier, negated_effect_case):
    receipt = coverage_verifier.verify(*negated_effect_case)
    assert receipt.critical_residuals[0].source_unit_ref in {
        u.unit_ref for u in negated_effect_case[0].units
    }


def test_noncritical_residual_does_not_reject_execution(coverage_verifier, case):
    receipt = coverage_verifier.verify(case.lattice, case.program)
    # Any residuals present must be noncritical for an executable program.
    for residual in receipt.residual_unit_refs:
        assert residual not in {cr.source_unit_ref for cr in receipt.critical_residuals}
    assert receipt.executable


# ---------------------------------------------------------------------------
# CoverageVerifier never repairs or synthesizes
# ---------------------------------------------------------------------------


def test_verifier_does_not_synthesize_assignments(coverage_verifier, valid_program):
    """The verifier must not add assignments; it only validates the program."""
    from cemm_authoritative_hybrid.forms import FormLattice

    empty_lattice = FormLattice(units=(), hypotheses=(), source_text="")
    receipt = coverage_verifier.verify(empty_lattice, valid_program)
    # The program's own assignments are unchanged; the verifier reports gaps.
    assert receipt.missing_unit_refs == ()
    # Lattice has no units, so program units are extra but assignments remain.
    assert set(receipt.assigned_unit_refs) == {
        row.source_unit_ref
        for row in valid_program.source_assignments
        if row.assignment_kind != "residual"
    }


def test_verify_program_checks_internal_consistency(coverage_verifier, valid_program):
    receipt = coverage_verifier.verify_program(valid_program)
    assert isinstance(receipt, CoverageReceipt)
    assert receipt.errors == ()


# ---------------------------------------------------------------------------
# Helpers — return modified copies of a program
# ---------------------------------------------------------------------------


def with_assignment_removed(program: SemanticSwitchProgram) -> SemanticSwitchProgram:
    """Return a copy of ``program`` with one source assignment removed."""
    if not program.source_assignments:
        return program
    return replace(program, source_assignments=program.source_assignments[:-1])


def with_assignment_duplicated(
    program: SemanticSwitchProgram,
) -> SemanticSwitchProgram:
    """Return a copy of ``program`` with the first assignment duplicated."""
    if not program.source_assignments:
        return program
    first = program.source_assignments[0]
    return replace(program, source_assignments=(first, *program.source_assignments))
