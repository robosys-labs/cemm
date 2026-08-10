"""R3 predecessor regressions exposed by authentic R4 surface replay."""
from __future__ import annotations

from pathlib import Path

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.cycle import PhaseDisposition, SemanticPhase
from cemm_authoritative_hybrid.r3_effects import NoEffectReceipt

ROOT = Path(__file__).parents[1]

__cemm_test_inventory__ = {'tests/test_r3_r4_predecessor_regressions.py::test_designation_reference_slots_bind_exact_reference_contributions': {'activation_phase': 'R3',
                                                                                                                      'assertion_ref': 'assertion:r3-designation-reference-contribution-provenance',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'R4-Predecessor-Repair',
                                                                                                                      'owner_ref': 'situation-context',
                                                                                                                      'source_ast_sha256': '09d245d7563ee15cb971fcec8467a37b8f637693011e20ae7e46a0f82525b2b5'},
 'tests/test_r3_r4_predecessor_regressions.py::test_event_frames_receive_only_missing_situated_participant_roles': {'activation_phase': 'R3',
                                                                                                                    'assertion_ref': 'assertion:r3-situated-event-participant-reference',
                                                                                                                    'diagnostic_role': 'owner',
                                                                                                                    'introduced_by_task': 'R4-Predecessor-Repair',
                                                                                                                    'owner_ref': 'situation-context',
                                                                                                                    'source_ast_sha256': 'bb06c2a2f01f2d17179ecaf1a191447f45b2ee4509f0a457577ac85d38a7d317'},
 'tests/test_r3_r4_predecessor_regressions.py::test_orientation_permission_snapshot_is_set_like': {'activation_phase': 'R3',
                                                                                                   'assertion_ref': 'assertion:r3-orientation-permission-snapshot-unique',
                                                                                                   'diagnostic_role': 'owner',
                                                                                                   'introduced_by_task': 'R4-Predecessor-Repair',
                                                                                                   'owner_ref': 'situation-context',
                                                                                                   'source_ast_sha256': '4eaecd9fd223c304f224ffbc14e18f5a0a8bc6fde62515f0e48385586c398508'},
 'tests/test_r3_r4_predecessor_regressions.py::test_public_greeting_completes_r3_and_persists_no_effect_without_world_mutation': {'activation_phase': 'R3',
                                                                                                                                  'assertion_ref': 'assertion:r3-public-greeting-six-phase-no-effect',
                                                                                                                                  'diagnostic_role': 'phase',
                                                                                                                                  'introduced_by_task': 'R4-Predecessor-Repair',
                                                                                                                                  'source_ast_sha256': '5572e796cf5c6aa065133a02dc56af299bf9819eb34540d7eecff6918580f05a'}}


def _runtime(tmp_path: Path):
    return load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")


def test_designation_reference_slots_bind_exact_reference_contributions(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    try:
        _, context = runtime.orient("session:reference-provenance", "alice likes bob")
    finally:
        runtime.stores.close()
    designation_refs = tuple(
        row for row in context.reference_slots
        if row.resolution_kind == "designation" and row.source_unit_refs
    )
    assert designation_refs
    for reference in designation_refs:
        supporting = tuple(
            row for row in context.contribution_slots
            if row.kind == "reference"
            and row.target_ref == reference.target_ref
            and row.source_unit_refs == reference.source_unit_refs
            and row.slot_ref in reference.provenance_refs
        )
        assert supporting
        assert set(reference.compatible_roles) <= set().union(*(set(row.output_ports) for row in supporting))


def test_event_frames_receive_only_missing_situated_participant_roles(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    try:
        orientation, context = runtime.orient("session:situated-greeting", "hello")
    finally:
        runtime.stores.close()
    situated = tuple(row for row in context.reference_slots if row.resolution_kind == "situated_participant")
    assert situated
    assert all(row.source_unit_refs == () for row in situated)
    assert all(row.target_ref in orientation.participants for row in situated)
    assert all(orientation.orientation_ref in row.provenance_refs for row in situated)
    assert len({role for row in situated for role in row.compatible_roles}) == sum(
        len(row.compatible_roles) for row in situated
    )


def test_orientation_permission_snapshot_is_set_like(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    try:
        orientation, _ = runtime.orient("session:permission-snapshot", "hello")
    finally:
        runtime.stores.close()
    assert orientation.permission_summary
    assert len(orientation.permission_summary) == len(set(orientation.permission_summary))


def test_public_greeting_completes_r3_and_persists_no_effect_without_world_mutation(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path)
    try:
        result = runtime.process("session:public-greeting", "hello")
    finally:
        runtime.stores.close()
    assert result.proposal.status == "candidates"
    assert result.verification.status == "selected"
    assert result.evaluation is not None
    assert type(result.effect_receipt) is NoEffectReceipt
    assert result.response_meaning is not None
    assert result.realization_receipt is None
    assert result.gap_receipt is not None
    assert result.gap_receipt.missing_contract_refs == ("contract:r5:realize_surface",)
    assert tuple(row.phase for row in result.phase_material) == (
        SemanticPhase.ORIENT,
        SemanticPhase.PROPOSE,
        SemanticPhase.VERIFY,
        SemanticPhase.EVALUATE,
        SemanticPhase.EFFECT,
        SemanticPhase.REALIZE,
    )
    effect_phase = next(row for row in result.phase_material if row.phase is SemanticPhase.EFFECT)
    assert effect_phase.disposition is PhaseDisposition.NO_EFFECT
    assert effect_phase.output_revision_pin.world_revision == effect_phase.input_revision_pin.world_revision
    assert effect_phase.output_revision_pin.effect_revision > effect_phase.input_revision_pin.effect_revision
    assert effect_phase.output_revision_pin.session_revision >= effect_phase.input_revision_pin.session_revision
