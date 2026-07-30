"""Six-phase runtime tests: injected owners, trace, revision increment.

These tests verify that an injected program runs through all six phase owners
(ORIENT -> PROPOSE -> VERIFY -> EVALUATE -> EFFECT -> REALIZE), produces a
``resolved`` status, increments the world revision, and emits a trace with the
six named phases in order.
"""

from __future__ import annotations

from conftest import SIX_PHASES


def test_injected_program_runs_through_six_phase_owners(
    runtime_factory, verified_observation_program
):
    runtime = runtime_factory(proposal_fixture=verified_observation_program)
    result = runtime.process_evidence(
        {"source": "test", "units": ("unit:1",)}, trace=True
    )
    assert result.status.value == "resolved"
    assert tuple(r.phase for r in result.trace) == SIX_PHASES
    assert result.final_revision_pin.world_revision == 1


def test_trace_off_still_resolves(runtime_factory, verified_observation_program):
    runtime = runtime_factory(proposal_fixture=verified_observation_program)
    result = runtime.process_evidence(
        {"source": "test", "units": ("unit:1",)}, trace=False
    )
    assert result.status.value == "resolved"
    assert result.trace == ()


def test_second_cycle_increments_world_revision(
    runtime_factory, verified_observation_program
):
    runtime = runtime_factory(proposal_fixture=verified_observation_program)
    first = runtime.process_evidence(
        {"source": "test", "units": ("unit:1",)}, trace=True
    )
    assert first.final_revision_pin.world_revision == 1
    second = runtime.process_evidence(
        {"source": "test", "units": ("unit:2",)}, trace=True
    )
    assert second.final_revision_pin.world_revision == 2


def test_phase_receipts_have_named_phases_not_stage_numbers(
    runtime_factory, verified_observation_program
):
    runtime = runtime_factory(proposal_fixture=verified_observation_program)
    result = runtime.process_evidence(
        {"source": "test", "units": ("unit:1",)}, trace=True
    )
    serialized = str(result.as_dict())
    assert "stage" not in serialized.casefold()


def test_gap_receipt_is_none_on_resolved_cycle(
    runtime_factory, verified_observation_program
):
    runtime = runtime_factory(proposal_fixture=verified_observation_program)
    result = runtime.process_evidence(
        {"source": "test", "units": ("unit:1",)}, trace=True
    )
    assert result.gap_receipt is None
