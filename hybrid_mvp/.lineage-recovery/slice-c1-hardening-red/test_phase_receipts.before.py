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
    LegacyPhaseReceipt as PhaseReceipt,
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


# ---------------------------------------------------------------------------
# R1 Slice C1 superseding ABI-2 literals
# ---------------------------------------------------------------------------

from dataclasses import replace as _c1_replace
from types import MappingProxyType as _C1MappingProxyType

import pytest as _c1_pytest

import cemm_authoritative_hybrid.cycle as _c1_cycle
from cemm_authoritative_hybrid.gaps import (
    GapKind as _C1GapKind,
    GapReceipt as _C1GapReceipt,
    RepairOwner as _C1RepairOwner,
)
from cemm_authoritative_hybrid.proposal import ProposalResult as _C1ProposalResult
from cemm_authoritative_hybrid.verifier import VerificationBatch as _C1VerificationBatch


def _c1_pin(*, world_revision: int = 3, effect_revision: int = 5) -> RevisionPin:
    return RevisionPin(
        "authority:generation-c1", world_revision, 7, 11, effect_revision, "model:c1"
    )


def _c1_artifacts():
    pin = _c1_pin()
    orientation = Orientation.create(
        session_ref="session:c1", turn_ref="turn:c1",
        source_text="unknown later owner", mode=SemanticMode.QUERY,
        participant_frame="participant-frame:c1",
        temporal_frame="temporal-frame:c1",
        participants=("participant:user", "participant:system"),
        active_turn_ref="turn:c1", event_refs=("turn:c1",), focus_refs=(),
        obligation_refs=(), capability_summary=("cap:answer",),
        permission_summary=("permission:answer",),
        budgets={"input_tokens": 3}, scanned_atom_count=0,
        index_probes=("designations:for_surface",), visited_refs=(),
        revision_pin=pin,
    )
    proposal = _C1ProposalResult.create(
        orientation_ref=orientation.orientation_ref,
        proposal_context_ref="proposal_context:c1", candidates=(),
        status="abstained", abstention_code="no_candidates",
        explored_states=0, truncated=False, model_identity="model:c1",
        revision_pin=pin,
    )
    verification = _C1VerificationBatch.create(
        proposal_ref=proposal.proposal_ref,
        proposal_context_ref="proposal_context:c1", candidate_receipts=(),
        ambiguity_margin_q=0, status="abstained",
        selected_candidate_ref=None, selected_meaning=None,
        ambiguity_expression_refs=(),
    )
    gap = _C1GapReceipt.create(
        kind=_C1GapKind.IMPLEMENTATION,
        status="later_owner_not_admitted",
        source_refs=(verification.batch_ref,),
        blockers=("owner:evaluate",),
        missing_contract_refs=("contract:evaluate-abi2",),
        rejected_candidate_refs=(),
        recommended_owner=_C1RepairOwner.RUNTIME,
        safe_response_action="activation_failure",
    )
    material_type = _c1_cycle._PhaseMaterial
    disposition = _c1_cycle.PhaseDisposition
    materials = (
        material_type(
            SemanticPhase.ORIENT, ("evidence:c1",),
            (orientation.orientation_ref,), pin, pin,
            disposition.COMPLETED, (), {"input_tokens": 3},
        ),
        material_type(
            SemanticPhase.PROPOSE, (orientation.orientation_ref,),
            (proposal.proposal_ref,), pin, pin,
            disposition.ABSTAINED, ("no_candidates",), {"search_states": 0},
        ),
        material_type(
            SemanticPhase.VERIFY, (proposal.proposal_ref,),
            (verification.batch_ref,), pin, pin,
            disposition.ABSTAINED, ("no_candidates",), {"candidates": 0},
        ),
    )
    return pin, orientation, proposal, verification, gap, materials


def _c1_finalize(*, capture_trace: bool, durations_ns=(13, 17, 19), **changes):
    pin, orientation, proposal, verification, gap, materials = _c1_artifacts()
    values = {
        "input_ref": "evidence:c1", "status": CycleStatus.UNSUPPORTED,
        "orientation": orientation, "proposal": proposal,
        "verification": verification, "evaluation": None,
        "effect_receipt": None, "response_meaning": None,
        "realization_receipt": None, "gap_receipt": gap,
        "phase_material": materials, "final_revision_pin": pin,
        "capture_trace": capture_trace, "durations_ns": durations_ns,
    }
    values.update(changes)
    return _c1_cycle.CycleFinalizer.finalize(**values)


def test_c1_phase_disposition_and_material_wire_are_closed_strict_and_frozen():
    assert _c1_cycle.PHASE_RECEIPT_ABI_VERSION == 2
    assert tuple(item.value for item in _c1_cycle.PhaseDisposition) == (
        "completed", "abstained", "rejected", "gap", "committed",
        "no_effect", "failed",
    )
    material = _c1_artifacts()[-1][0]
    payload = material.as_dict()
    assert _c1_cycle._PhaseMaterial.from_dict(payload) == material
    assert tuple(payload) == (
        "phase", "input_refs", "output_refs", "input_revision_pin",
        "output_revision_pin", "disposition", "rejection_codes", "budget_use",
    )
    assert type(payload["input_refs"]) is list
    assert type(payload["budget_use"]) is dict
    assert isinstance(material.budget_use, _C1MappingProxyType)


def test_c1_phase_receipt_roundtrip_corruption_sensitivity_and_duration_exclusion():
    material = _c1_artifacts()[-1][0]
    first = _c1_cycle.PhaseReceipt.create(
        cycle_ref="cycle:111111111111111111111111",
        material=material, duration_ns=1,
    )
    second = _c1_cycle.PhaseReceipt.create(
        cycle_ref=first.cycle_ref, material=material, duration_ns=99,
    )
    assert first.receipt_ref == second.receipt_ref
    assert _c1_cycle.PhaseReceipt.from_dict(first.as_dict()) == first
    assert first.receipt_ref != _c1_cycle.PhaseReceipt.create(
        cycle_ref="cycle:222222222222222222222222",
        material=material, duration_ns=1,
    ).receipt_ref
    assert first.receipt_ref != _c1_cycle.PhaseReceipt.create(
        cycle_ref=first.cycle_ref,
        material=_c1_replace(material, budget_use={"input_tokens": 2}),
        duration_ns=1,
    ).receipt_ref
    corrupted = first.as_dict()
    corrupted["receipt_ref"] = "phase_receipt:000000000000000000000000"
    with _c1_pytest.raises(ValueError, match="ref mismatch"):
        _c1_cycle.PhaseReceipt.from_dict(corrupted)
    with _c1_pytest.raises(ValueError, match="ref mismatch"):
        _c1_replace(first, receipt_ref="phase_receipt:000000000000000000000000")


def test_c1_phase_receipt_hostile_content_is_rejected_before_hash(monkeypatch):
    material = _c1_artifacts()[-1][0]

    def forbidden_hash(*_args, **_kwargs):
        raise AssertionError("hostile receipt content reached stable_ref")

    monkeypatch.setattr(_c1_cycle, "stable_ref", forbidden_hash)
    with _c1_pytest.raises(ValueError, match="bound"):
        _c1_cycle.PhaseReceipt.create(
            cycle_ref="cycle:111111111111111111111111",
            material=_c1_replace(
                material,
                input_refs=tuple(f"evidence:{index}" for index in range(65)),
            ),
            duration_ns=None,
        )


def test_c1_cycle_finalizer_trace_toggle_timing_and_final_binding_are_nonrecursive():
    without_trace = _c1_finalize(capture_trace=False, durations_ns=(1, 2, 3))
    with_trace = _c1_finalize(capture_trace=True, durations_ns=(100, 200, 300))
    assert _c1_cycle.CYCLE_RESULT_ABI_VERSION == 2
    assert without_trace.cycle_ref == with_trace.cycle_ref
    assert without_trace.trace == ()
    assert tuple(row.duration_ns for row in with_trace.trace) == (100, 200, 300)
    assert all(row.cycle_ref == with_trace.cycle_ref for row in with_trace.trace)
    assert all(row.receipt_ref.startswith("phase_receipt:") for row in with_trace.trace)


def test_c1_cycle_result_roundtrip_and_constructor_forgery_checks_verify_gap_state():
    result = _c1_finalize(capture_trace=True)
    assert _c1_cycle.CycleResult.from_dict(result.as_dict()) == result
    assert tuple(row.phase for row in result.phase_material) == (
        SemanticPhase.ORIENT, SemanticPhase.PROPOSE, SemanticPhase.VERIFY,
    )
    assert result.evaluation is result.effect_receipt is None
    assert result.response_meaning is result.realization_receipt is None
    assert result.gap_receipt.status == "later_owner_not_admitted"
    with _c1_pytest.raises(ValueError, match="cycle ref mismatch"):
        _c1_replace(result, cycle_ref="cycle:000000000000000000000000")
    with _c1_pytest.raises(ValueError, match="trace|ref mismatch"):
        _c1_replace(
            result,
            trace=(
                _c1_replace(
                    result.trace[0],
                    cycle_ref="cycle:222222222222222222222222",
                ),
            ),
        )


def test_c1_cycle_identity_and_pin_chain_are_exact():
    original = _c1_finalize(capture_trace=False)
    pin, orientation, proposal, verification, gap, materials = _c1_artifacts()
    changed_material = (
        *materials[:-1],
        _c1_replace(materials[-1], budget_use={"candidates": 1}),
    )
    variants = (
        _c1_finalize(capture_trace=False, status=CycleStatus.PARTIAL),
        _c1_finalize(capture_trace=False, phase_material=changed_material),
        _c1_finalize(
            capture_trace=False,
            gap_receipt=_C1GapReceipt.create(
                kind=gap.kind,
                status=gap.status,
                source_refs=gap.source_refs,
                blockers=("owner:evaluate", "owner:effect"),
                missing_contract_refs=gap.missing_contract_refs,
                rejected_candidate_refs=gap.rejected_candidate_refs,
                recommended_owner=gap.recommended_owner,
                safe_response_action=gap.safe_response_action,
            ),
        ),
    )
    assert len({original.cycle_ref, *(row.cycle_ref for row in variants)}) == 4
    with _c1_pytest.raises(ValueError, match="order"):
        _c1_finalize(
            capture_trace=False,
            phase_material=(materials[0], materials[2]),
            durations_ns=(1, 2),
        )
    with _c1_pytest.raises(ValueError, match="pin chain|only EFFECT"):
        _c1_finalize(
            capture_trace=False,
            phase_material=(
                materials[0],
                _c1_replace(
                    materials[1],
                    input_revision_pin=_c1_pin(world_revision=9),
                ),
                materials[2],
            ),
        )
    with _c1_pytest.raises(ValueError, match="only EFFECT"):
        _c1_cycle._PhaseMaterial(
            SemanticPhase.ORIENT, ("evidence:c1",),
            (orientation.orientation_ref,), pin,
            _c1_pin(world_revision=9),
            _c1_cycle.PhaseDisposition.COMPLETED, (), {},
        )
    effect_pin = _c1_pin(world_revision=4, effect_revision=6)
    effect_material = _c1_cycle._PhaseMaterial(
        SemanticPhase.EFFECT, ("decision:c1",), ("effect_receipt:c1",),
        pin, effect_pin, _c1_cycle.PhaseDisposition.COMMITTED, (),
        {"effects": 1},
    )
    assert effect_material.output_revision_pin == effect_pin


def test_c1_cycle_codec_prehash_bounds_and_later_owner_disable(monkeypatch):
    payload = _c1_finalize(capture_trace=False).as_dict()
    hostile = dict(payload)
    hostile["phase_material"] = [payload["phase_material"][0]] * 7

    def forbidden_hash(*_args, **_kwargs):
        raise AssertionError("hostile cycle content reached stable_ref")

    monkeypatch.setattr(_c1_cycle, "stable_ref", forbidden_hash)
    with _c1_pytest.raises(ValueError, match="bound"):
        _c1_cycle.CycleResult.from_dict(hostile)

    monkeypatch.undo()
    for field_name in (
        "evaluation", "effect_receipt", "response_meaning", "realization_receipt",
    ):
        with _c1_pytest.raises(TypeError, match="not admitted"):
            _c1_finalize(capture_trace=False, **{field_name: object()})