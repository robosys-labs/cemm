"""Six-phase runtime tests: injected owners, trace, revision increment.

These tests verify that an injected program runs through all six phase owners
(ORIENT -> PROPOSE -> VERIFY -> EVALUATE -> EFFECT -> REALIZE), produces a
``resolved`` status, increments the world revision, and emits a trace with the
six named phases in order.
"""

from __future__ import annotations

from conftest import SIX_PHASES

from cemm_authoritative_hybrid.cycle import SemanticPhase


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


def test_runtime_receipts_bind_exact_orientation_content_ref(
    runtime_factory, verified_observation_program, monkeypatch
):
    runtime = runtime_factory(proposal_fixture=verified_observation_program)
    first_orientation = runtime.orient("session:same", "first content")
    second_orientation = runtime.orient("session:same", "second content")
    assert first_orientation.session_ref == second_orientation.session_ref
    assert first_orientation.orientation_ref != second_orientation.orientation_ref

    projected = iter((first_orientation, second_orientation))
    monkeypatch.setattr(runtime, "_orient", lambda *_args, **_kwargs: next(projected))

    first = runtime.process_evidence({"text": "first content"}, trace=True)
    second = runtime.process_evidence({"text": "second content"}, trace=True)
    for expected, result in (
        (first_orientation, first),
        (second_orientation, second),
    ):
        assert result.phase_output_refs[SemanticPhase.ORIENT] == (
            expected.orientation_ref,
        )
        assert result.trace[0].output_refs == (expected.orientation_ref,)
        assert result.trace[1].input_refs == (expected.orientation_ref,)

__cemm_test_inventory__ = {
    "tests/test_six_phase_runtime.py::test_runtime_receipts_bind_exact_orientation_content_ref": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-slice-b-runtime-receipts-bind-orientation-content",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Slice-B",
        "owner_ref": "orientation-lineage",
        "source_ast_sha256": "88b2ba4d9827f7595b82f0b4a420973d66530156d9cec3daff962f626239685c",
    },
}