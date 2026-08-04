"""Phase receipt tests: six-phase trace, closed modes, closed outcomes.

These tests assert the Phase Receipt ABI and the closed semantic-mode and
cycle-outcome enums. They verify that the six-phase trace uses named phases
(not legacy stage numbers) and that ``KernelCycleResult.as_dict()`` never
contains the forbidden ``stage`` substring.
"""

from __future__ import annotations

from cemm_authoritative_hybrid.cycle import (
    CycleResult,
    CycleStatus,
    KernelCycleResult,
    Orientation,
    PhaseReceipt,
    SemanticMode,
    SemanticPhase,
)
from cemm_authoritative_hybrid.persistence import RevisionPin


# ---------------------------------------------------------------------------
# Six-phase trace
# ---------------------------------------------------------------------------


def test_trace_contains_six_named_phases_not_stage_numbers(cycle_fixture):
    result = cycle_fixture.run(trace=True)
    assert tuple(r.phase for r in result.trace) == (
        "ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "REALIZE"
    )
    assert "stage" not in str(result.as_dict()).casefold()


def test_semantic_phase_enum_is_closed_and_ordered():
    assert tuple(phase.value for phase in SemanticPhase) == (
        "ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "REALIZE"
    )


# ---------------------------------------------------------------------------
# Closed semantic modes
# ---------------------------------------------------------------------------


def test_semantic_modes_are_closed_and_not_phrase_intents():
    assert tuple(mode.value for mode in SemanticMode) == (
        "OBSERVE", "QUERY", "REQUEST", "SIMULATE"
    )


# ---------------------------------------------------------------------------
# Closed external cycle outcomes
# ---------------------------------------------------------------------------


def test_external_cycle_outcomes_are_closed():
    assert tuple(status.value for status in CycleStatus) == (
        "resolved", "partial", "ambiguous", "unknown", "conflict", "unsupported",
        "denied", "resource_unavailable", "budget_exhausted", "operation_failed",
        "realization_failed",
    )


# ---------------------------------------------------------------------------
# Phase receipt structure
# ---------------------------------------------------------------------------


def test_phase_receipt_is_frozen_dataclass():
    receipt = PhaseReceipt(
        cycle_ref="cycle:test",
        phase="ORIENT",
        input_refs=("evidence:1",),
        output_refs=("orientation:1",),
        revision_pin=RevisionPin(
            authority_generation="authority:generation-1",
            world_revision=0,
            session_revision=0,
            episode_revision=0,
            effect_revision=0,
            model_identity=None,
        ),
        budget_use={"tokens": 4},
        status="ok",
    )
    assert receipt.phase == "ORIENT"
    assert receipt.rejection_codes == ()
    assert receipt.duration_ns is None
    # frozen
    import dataclasses

    assert dataclasses.is_dataclass(receipt)
    try:
        receipt.phase = "PROPOSE"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("PhaseReceipt must be frozen")


def test_kernel_cycle_result_as_dict_has_no_stage(cycle_fixture):
    result = cycle_fixture.run(trace=True)
    serialized = result.as_dict()
    assert "stage" not in str(serialized).casefold()
    assert isinstance(serialized, dict)


def test_kernel_cycle_result_trace_off_still_has_status(cycle_fixture):
    result = cycle_fixture.run(trace=False)
    assert result.status is CycleStatus.RESOLVED
    assert result.trace == ()


def test_kernel_cycle_result_resolved_status(cycle_fixture):
    result = cycle_fixture.run(trace=True)
    assert result.status is CycleStatus.RESOLVED
    assert result.gap_receipt is None
    assert isinstance(result.final_revision_pin, RevisionPin)


def test_orientation_is_frozen_dataclass():
    import dataclasses

    orientation = Orientation.create(
        session_ref="session:test",
        turn_ref="turn:test",
        source_text="",
        mode=SemanticMode.OBSERVE,
        participant_frame="participant:user",
        temporal_frame="now",
        participants=(),
        active_turn_ref="turn:test",
        event_refs=(),
        focus_refs=(),
        obligation_refs=(),
        capability_summary=(),
        permission_summary=(),
        budgets={},
        scanned_atom_count=0,
        index_probes=(),
        visited_refs=(),
        revision_pin=RevisionPin(
            "authority:generation-1", 0, 0, 0, 0, None
        ),
    )
    assert dataclasses.is_dataclass(orientation)
    try:
        orientation.mode = SemanticMode.QUERY  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:
        raise AssertionError("Orientation must be frozen")


def test_cycle_result_is_kernel_cycle_result_or_wraps_it(cycle_fixture):
    result = cycle_fixture.run(trace=False)
    # CycleResult should be usable as the user-facing result.
    assert isinstance(result, (KernelCycleResult, CycleResult))
