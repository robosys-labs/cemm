"""R3 predecessor regressions exposed by authentic R4 surface replay."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.cycle import (
    PhaseDisposition,
    SemanticMode,
    SemanticPhase,
)
from cemm_authoritative_hybrid.expressions import LiteralValue
from cemm_authoritative_hybrid.proposal import (
    ProposalResult,
    RankedProgramCandidate,
)
from cemm_authoritative_hybrid.r3_effects import NoEffectReceipt
from cemm_authoritative_hybrid.verifier import VerificationError

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
                                                                                                                                  'source_ast_sha256': '5572e796cf5c6aa065133a02dc56af299bf9819eb34540d7eecff6918580f05a'},
 'tests/test_r3_r4_predecessor_regressions.py::test_closure_invalid_program_receives_typed_verification_rejection': {'activation_phase': 'R4',
                                                                                                                     'assertion_ref': 'assertion:r4-closure-invalid-program-verification-rejected',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'R4-Closure-Slice-Task-1',
                                                                                                                     'owner_ref': 'exact-program-verifier',
                                                                                                                     'source_ast_sha256': 'ebf806b4788c94f803d1bae97b7793986afb594d2dbeeb90646b60758deff445'}}


@dataclass(frozen=True)
class _ClosureCase:
    case_ref: str
    surface: str | None
    context_setup: str
    expected_mode: SemanticMode | None
    expected_action: str


_CLOSURE_CASES = (
    _ClosureCase("known_definition", "What is CEMM?", "fresh", SemanticMode.QUERY, "answer"),
    _ClosureCase("unknown_designation", "What is zorbulate?", "fresh", SemanticMode.QUERY, "unknown"),
    _ClosureCase("capability_query", "Can you learn aliases?", "fresh", SemanticMode.QUERY, "answer"),
    _ClosureCase("history_query", "You said what?", "record_system_goodbye", SemanticMode.QUERY, "answer"),
    _ClosureCase("fragment_resolved", "That you learn.", "open_meaning_question", SemanticMode.OBSERVE, "answer"),
    _ClosureCase("fragment_unresolved", "That you learn.", "fresh", SemanticMode.OBSERVE, "clarify"),
    _ClosureCase("negated_relation", "Alice does not like the book.", "fresh", SemanticMode.OBSERVE, "acknowledge_observation"),
    _ClosureCase("state_conflict", "The server is online and offline.", "fresh", SemanticMode.OBSERVE, "clarify"),
    _ClosureCase("linked_simulation", "If the server is online, then the lamp is on.", "fresh", SemanticMode.SIMULATE, "answer_simulation"),
    _ClosureCase("multiple_roots", "The server is offline. You said goodbye.", "fresh", SemanticMode.OBSERVE, "acknowledge_observation"),
    _ClosureCase("permission_denial", "Set the state without permission.", "remove_set_state_permission", SemanticMode.REQUEST, "deny"),
    _ClosureCase("invalid_program", None, "mutate_valid_program", None, "verification_rejected"),
)


def _runtime(tmp_path: Path):
    return load_runtime(ROOT, profile="development", store_path=tmp_path / "stores.db")


def _assert_selected_semantic_path(result) -> None:
    assert result.proposal.status == "candidates", result.proposal.abstention_code
    assert result.verification.status == "selected"
    assert result.verification.selected_candidate_ref
    meaning = result.verification.selected_meaning
    assert meaning is not None
    assert meaning.verified_meaning_ref
    assert meaning.expression.expression_ref
    assert result.evaluation is not None
    assert result.effect_receipt is not None
    assert result.response_meaning is not None
    assert result.response_meaning.response_expression.expression_ref






def test_closure_invalid_program_receives_typed_verification_rejection(
    exact_verifier,
    valid_program,
    proposal_context,
    mutate,
) -> None:
    case = _CLOSURE_CASES[-1]
    assert case.surface is None
    assert case.context_setup == "mutate_valid_program"
    mutated_program = mutate(valid_program, "unknown_ref")
    candidate = RankedProgramCandidate.create(
        rank=0,
        score_q=900_000,
        program=mutated_program,
        provenance_refs=("derivation:closure-invalid-program",),
    )
    proposal = ProposalResult.create(
        orientation_ref=proposal_context.orientation_ref,
        proposal_context_ref=proposal_context.context_ref,
        candidates=(candidate,),
        status="candidates",
        abstention_code=None,
        explored_states=1,
        truncated=False,
        model_identity=proposal_context.revision_pin.model_identity,
        revision_pin=proposal_context.revision_pin,
    )

    batch = exact_verifier.verify_candidates(proposal, proposal_context)

    assert batch.status == "rejected"
    assert batch.selected_candidate_ref is None
    assert batch.selected_meaning is None
    assert len(batch.candidate_receipts) == 1
    receipt = batch.candidate_receipts[0]
    assert not receipt.accepted
    assert receipt.verification_errors
    assert all(type(error) is VerificationError for error in receipt.verification_errors)
    assert "unknown_designation_slot" in {
        error.code for error in receipt.verification_errors
    }
    assert f"verification_{batch.status}" == case.expected_action


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
