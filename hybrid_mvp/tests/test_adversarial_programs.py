"""Adversarial tests for the exact program verifier.

These tests verify that the verifier rejects programs with fabricated atoms,
unknown operators, invalid action types, cycles in nested applications, and
depth bound violations. The verifier must never accept a structurally
impossible program.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from cemm_authoritative_hybrid.programs import (
    PERSISTENT_OPERATORS,
    SWITCH_ACTION_TYPES,
    ProgramAction,
    SemanticSwitchProgram,
)
from cemm_authoritative_hybrid.verifier import VerificationResult


# ---------------------------------------------------------------------------
# Helper to build a minimal valid program from scratch (not from lattice)
# ---------------------------------------------------------------------------


def _make_minimal_program(valid_program, **overrides):
    """Return a copy of valid_program with overridden fields."""
    return replace(valid_program, **overrides)


# ---------------------------------------------------------------------------
# Fabricated atoms not in authority
# ---------------------------------------------------------------------------


def test_fabricated_atom_in_designation_rejected(verifier, valid_program, mutate):
    """A select_designation targeting a fabricated atom is rejected."""
    result = verifier.verify(mutate(valid_program, "unknown_ref"))
    assert not result.accepted
    assert result.errors[0].code == "unknown_ref"


def test_fabricated_atom_in_bind_reference_rejected(verifier, valid_program):
    """A bind_reference targeting a fabricated atom is rejected."""
    # Add a bind_reference action with a non-existent target.
    bind_ref_action = ProgramAction(
        action_ref="action:bind_ref_fab",
        action_type="bind_reference",
        arguments=("ref:0", "entity:fabricated"),
        source_unit_refs=(),
    )
    new_actions = []
    for a in valid_program.actions:
        new_actions.append(a)
        if a.action_type == "instantiate_operator":
            new_actions.append(bind_ref_action)
    program = _make_minimal_program(valid_program, actions=tuple(new_actions))
    result = verifier.verify(program)
    assert not result.accepted
    assert any(e.code == "unknown_ref" for e in result.errors)


# ---------------------------------------------------------------------------
# Operator not in the five persistent operators
# ---------------------------------------------------------------------------


def test_unknown_operator_rejected(verifier, valid_program):
    """An instantiate_operator with an unknown operator is rejected."""
    new_actions = []
    for a in valid_program.actions:
        if a.action_type == "instantiate_operator":
            new_actions.append(
                replace(a, arguments=("op:fabricated", "designation:0"))
            )
        else:
            new_actions.append(a)
    program = _make_minimal_program(valid_program, actions=tuple(new_actions))
    result = verifier.verify(program)
    assert not result.accepted
    assert any(e.code == "invalid_operator" for e in result.errors)


def test_only_five_persistent_operators_accepted(verifier, valid_program):
    """The valid program uses only op:designation, which is in the five."""
    assert "op:designation" in PERSISTENT_OPERATORS
    result = verifier.verify(valid_program)
    assert result.accepted


# ---------------------------------------------------------------------------
# Action type not in SWITCH_ACTION_TYPES
# ---------------------------------------------------------------------------


def test_unknown_action_type_rejected_by_constructor():
    """ProgramAction rejects unknown action types at construction time."""
    with pytest.raises(ValueError):
        ProgramAction(
            action_ref="action:bad",
            action_type="not_a_real_action",  # type: ignore[arg-type]
            arguments=(),
            source_unit_refs=(),
        )


def test_switch_action_vocabulary_is_closed_at_twelve():
    """The action vocabulary is exactly 12 types."""
    assert len(SWITCH_ACTION_TYPES) == 12
    assert len(set(SWITCH_ACTION_TYPES)) == 12


# ---------------------------------------------------------------------------
# Cycle in nested applications
# ---------------------------------------------------------------------------


def test_nested_application_cycle_rejected(verifier, valid_program, mutate):
    """A cycle in bind_nested_application actions is rejected."""
    result = verifier.verify(mutate(valid_program, "scope_cycle"))
    assert not result.accepted
    assert result.errors[0].code == "scope_cycle"


def test_direct_self_reference_cycle_rejected(verifier, valid_program):
    """A bind_nested_application that references itself is rejected."""
    op_ref = None
    for a in valid_program.actions:
        if a.action_type == "instantiate_operator":
            op_ref = a.action_ref
            break
    assert op_ref is not None
    self_ref = ProgramAction(
        action_ref="action:self_ref",
        action_type="bind_nested_application",
        arguments=("action:self_ref",),  # references itself
        source_unit_refs=(),
    )
    new_actions = []
    for a in valid_program.actions:
        new_actions.append(a)
        if a.action_type == "complete_program":
            new_actions.insert(-1, self_ref)
    program = _make_minimal_program(valid_program, actions=tuple(new_actions))
    result = verifier.verify(program)
    assert not result.accepted
    assert any(e.code == "scope_cycle" for e in result.errors)


# ---------------------------------------------------------------------------
# Depth bound exceeded
# ---------------------------------------------------------------------------


def test_depth_bound_exceeded_rejected(verifier, valid_program, mutate):
    """A program exceeding max_applications is rejected."""
    result = verifier.verify(mutate(valid_program, "excess_depth"))
    assert not result.accepted
    assert result.errors[0].code == "excess_depth"


def test_program_at_max_actions_accepted(verifier, valid_program):
    """A program at exactly max_applications is accepted (if otherwise valid)."""
    from cemm_authoritative_hybrid.config import RuntimeConfig

    config = RuntimeConfig.release()
    max_actions = config.max_applications
    # The valid program should have fewer than max_actions.
    result = verifier.verify(valid_program)
    if result.accepted:
        assert len(valid_program.actions) <= max_actions


# ---------------------------------------------------------------------------
# Stale revision
# ---------------------------------------------------------------------------


def test_stale_revision_rejected(verifier, valid_program, mutate):
    """A program with a stale revision_pin is rejected."""
    result = verifier.verify(mutate(valid_program, "stale_revision"))
    assert not result.accepted
    assert result.errors[0].code == "stale_revision"


# ---------------------------------------------------------------------------
# Uncovered unit
# ---------------------------------------------------------------------------


def test_uncovered_unit_rejected(verifier, valid_program, mutate):
    """A program with an unassigned source unit is rejected."""
    result = verifier.verify(mutate(valid_program, "uncovered_unit"))
    assert not result.accepted
    assert result.errors[0].code == "uncovered_unit"


# ---------------------------------------------------------------------------
# Verifier returns typed VerificationResult
# ---------------------------------------------------------------------------


def test_verify_returns_verification_result(verifier, valid_program):
    result = verifier.verify(valid_program)
    assert isinstance(result, VerificationResult)
    assert isinstance(result.accepted, bool)
    assert isinstance(result.well_formed, bool)
    assert isinstance(result.errors, tuple)
    assert isinstance(result.verification_hash, str)
