"""R1 successors for legacy cognitive-loop and restart contracts.

R1 admits only ORIENT, PROPOSE, and VERIFY.  These tests preserve the useful
artifact and persistence assertions from the frozen six-phase predecessors
without reintroducing their retired result wrappers or later-owner fixtures.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import (
    CycleResult,
    CycleStatus,
    Orientation,
    SemanticPhase,
)
from cemm_authoritative_hybrid.persistence import (
    RevisionPin,
    SemanticStores,
    open_stores,
)
from cemm_authoritative_hybrid.proposal import ProposalResult
from cemm_authoritative_hybrid.runtime import HybridRuntime
from cemm_authoritative_hybrid.verifier import VerificationBatch


_ADMITTED_PHASES = (
    SemanticPhase.ORIENT,
    SemanticPhase.PROPOSE,
    SemanticPhase.VERIFY,
)
_EVALUATE_CONTRACT = ("contract:r3:evaluate",)


def _runtime_helpers():
    helper_path = Path(__file__).with_name("test_r1_runtime_path.py")
    spec = importlib.util.spec_from_file_location(
        "_r1_cognitive_restart_helpers", helper_path
    )
    assert spec is not None and spec.loader is not None
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    return helpers


def _runtime(stores: SemanticStores | None = None) -> HybridRuntime:
    helpers = _runtime_helpers()
    pin, orientation, context, proposal, verification = helpers._selected_artifacts()
    active_stores = stores or helpers.memory_stores(
        authority_generation=pin.authority_generation,
        model_identity=pin.model_identity,
    )
    return HybridRuntime(
        RuntimeConfig.release(),
        object(),
        active_stores,
        {
            "orientation": helpers._RecordingOrientationOwner(orientation, context),
            "proposal": helpers._RecordingProposalOwner(proposal),
            "verification": helpers._RecordingVerificationOwner(verification),
        },
        profile="development",
    )


def _process(runtime: HybridRuntime, *, trace: bool = True) -> CycleResult:
    return runtime.process(
        "session:r1-cognitive-restart",
        "alice likes bob",
        trace=trace,
    )


def _assert_r1_cut(result: CycleResult) -> None:
    assert type(result) is CycleResult
    assert result.status is CycleStatus.PARTIAL
    assert tuple(row.phase for row in result.phase_material) == _ADMITTED_PHASES
    assert result.evaluation is None
    assert result.effect_receipt is None
    assert result.response_meaning is None
    assert result.realization_receipt is None
    assert result.gap_receipt is not None
    assert result.gap_receipt.status == "later_owner_not_admitted"
    assert result.gap_receipt.missing_contract_refs == _EVALUATE_CONTRACT
    assert result.gap_receipt.safe_response_action == "stop_without_surface"


def _open_runtime(path: Path) -> tuple[HybridRuntime, SemanticStores]:
    stores = open_stores(
        path,
        authority_generation="authority:r1-runtime",
        model_identity="model:r1-runtime",
    )
    return _runtime(stores), stores


def test_r1_cycle_result_retains_canonical_orientation():
    result = _process(_runtime())
    _assert_r1_cut(result)
    assert type(result.orientation) is Orientation
    assert result.phase_material[0].output_refs == (
        result.orientation.orientation_ref,
        result.proposal.proposal_context_ref,
    )


def test_r1_cycle_result_retains_canonical_proposal():
    result = _process(_runtime())
    _assert_r1_cut(result)
    assert type(result.proposal) is ProposalResult
    assert result.phase_material[1].output_refs == (result.proposal.proposal_ref,)


def test_r1_cycle_result_retains_canonical_verification():
    result = _process(_runtime())
    _assert_r1_cut(result)
    assert type(result.verification) is VerificationBatch
    assert result.verification.status == "selected"
    assert result.verification.selected_meaning is not None


def test_r1_cycle_result_defers_evaluation_to_exact_later_owner():
    result = _process(_runtime())
    _assert_r1_cut(result)
    meaning = result.verification.selected_meaning
    assert meaning is not None
    assert result.gap_receipt.source_refs == (meaning.verified_meaning_ref,)


def test_r1_cycle_result_has_no_response_before_evaluation():
    result = _process(_runtime())
    _assert_r1_cut(result)
    assert result.response_meaning is None
    assert result.realization_receipt is None


def test_r1_cycle_trace_is_observational_with_bounded_durations():
    runtime = _runtime()
    traced = _process(runtime, trace=True)
    untraced = _process(runtime, trace=False)
    _assert_r1_cut(traced)
    _assert_r1_cut(untraced)
    assert tuple(row.phase for row in traced.trace) == _ADMITTED_PHASES
    assert all(type(row.duration_ns) is int for row in traced.trace)
    assert untraced.trace == ()
    assert traced.cycle_ref == untraced.cycle_ref
    assert traced.phase_material == untraced.phase_material


def test_r1_restart_preserves_world_revision_without_admitted_effect(tmp_path):
    path = tmp_path / "world-revision"
    runtime, stores = _open_runtime(path)
    result = _process(runtime)
    _assert_r1_cut(result)
    before_close = stores.world.revision
    assert before_close == result.final_revision_pin.world_revision == 0
    stores.close()

    _, reopened = _open_runtime(path)
    try:
        assert reopened.world.revision == before_close
    finally:
        reopened.close()


def test_r1_restart_preserves_effect_revision_without_admitted_effect(tmp_path):
    path = tmp_path / "effect-revision"
    runtime, stores = _open_runtime(path)
    result = _process(runtime)
    _assert_r1_cut(result)
    before_close = stores.effects.revision
    assert before_close == result.final_revision_pin.effect_revision == 0
    stores.close()

    _, reopened = _open_runtime(path)
    try:
        assert reopened.effects.revision == before_close
    finally:
        reopened.close()


def test_r1_restart_preserves_every_revision_pin_dimension(tmp_path):
    path = tmp_path / "revision-pin"
    runtime, stores = _open_runtime(path)
    result = _process(runtime)
    _assert_r1_cut(result)
    pin = result.final_revision_pin
    stores.close()

    _, reopened = _open_runtime(path)
    try:
        reopened_pin = reopened.revision_pin()
        assert type(reopened_pin) is RevisionPin
        assert reopened_pin == pin
    finally:
        reopened.close()


def test_r1_restart_preserves_stable_revisions_across_multiple_cycles(tmp_path):
    path = tmp_path / "multiple-cycles"
    runtime, stores = _open_runtime(path)
    results = tuple(_process(runtime) for _ in range(3))
    for result in results:
        _assert_r1_cut(result)
        assert result.final_revision_pin == results[0].final_revision_pin
    before_close = stores.revision_pin()
    stores.close()

    _, reopened = _open_runtime(path)
    try:
        assert reopened.revision_pin() == before_close
    finally:
        reopened.close()


def test_r1_consecutive_cycles_preserve_revision_pins_without_effect():
    runtime = _runtime()
    first = _process(runtime)
    second = _process(runtime)
    third = _process(runtime)
    for result in (first, second, third):
        _assert_r1_cut(result)
    assert first.final_revision_pin == second.final_revision_pin
    assert second.final_revision_pin == third.final_revision_pin


def test_r1_no_stale_revision_reentry_precedes_unadmitted_effect():
    runtime = _runtime()
    first = _process(runtime)
    second = _process(runtime)
    _assert_r1_cut(first)
    _assert_r1_cut(second)
    assert first.final_revision_pin == second.final_revision_pin
    assert tuple(row.phase for row in second.phase_material) == _ADMITTED_PHASES


def test_r1_cycle_result_after_reopen_contains_only_admitted_artifacts(tmp_path):
    path = tmp_path / "cycle-result"
    runtime, stores = _open_runtime(path)
    first = _process(runtime)
    _assert_r1_cut(first)
    stores.close()

    reopened_runtime, reopened = _open_runtime(path)
    try:
        result = _process(reopened_runtime)
        _assert_r1_cut(result)
        assert result.cycle_ref
        assert type(result.orientation) is Orientation
        assert type(result.proposal) is ProposalResult
        assert type(result.verification) is VerificationBatch
        assert tuple(row.phase for row in result.trace) == _ADMITTED_PHASES
    finally:
        reopened.close()


__cemm_test_inventory__ = {'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_result_retains_canonical_orientation': {'activation_phase': 'R1',
                                                                                                       'assertion_ref': 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-orientation',
                                                                                                       'diagnostic_role': 'owner',
                                                                                                       'introduced_by_task': 'R1-Task-9',
                                                                                                       'owner_ref': 'runtime-path',
                                                                                                       'source_ast_sha256': '0326445177a7cb2af3e2916618c16045d3c462f8fa2ff4bb95203503a57a3e74',
                                                                                                       'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestCycleResultArtifacts::test_cycle_result_has_orientation'},
 'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_result_retains_canonical_proposal': {'activation_phase': 'R1',
                                                                                                    'assertion_ref': 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-proposal',
                                                                                                    'diagnostic_role': 'owner',
                                                                                                    'introduced_by_task': 'R1-Task-9',
                                                                                                    'owner_ref': 'runtime-path',
                                                                                                    'source_ast_sha256': '447879f649e340f026f8790d8c868499815dbf2a85cfaf974b18c154d70770ab',
                                                                                                    'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestCycleResultArtifacts::test_cycle_result_has_proposal'},
 'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_result_retains_canonical_verification': {'activation_phase': 'R1',
                                                                                                        'assertion_ref': 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-verification',
                                                                                                        'diagnostic_role': 'owner',
                                                                                                        'introduced_by_task': 'R1-Task-9',
                                                                                                        'owner_ref': 'runtime-path',
                                                                                                        'source_ast_sha256': '74d59046a313399cc256d0dd48675f0a6b97ce61830cf4625bc9e94507666441',
                                                                                                        'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestCycleResultArtifacts::test_cycle_result_has_verification'},
 'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_result_defers_evaluation_to_exact_later_owner': {'activation_phase': 'R1',
                                                                                                                'assertion_ref': 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-evaluation',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'R1-Task-9',
                                                                                                                'owner_ref': 'runtime-path',
                                                                                                                'source_ast_sha256': '5610c4b3afec4d7ee140c5b1dc224ed833ce7230fc6f54296c4ea84f990cc00e',
                                                                                                                'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestCycleResultArtifacts::test_cycle_result_has_evaluation'},
 'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_result_has_no_response_before_evaluation': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-response-meaning',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-9',
                                                                                                           'owner_ref': 'runtime-path',
                                                                                                           'source_ast_sha256': '4e45a984eb00ab43bbd69528943dc6d50d307640f2e623915daec48083928d92',
                                                                                                           'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestCycleResultArtifacts::test_cycle_result_has_response_meaning'},
 'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_trace_is_observational_with_bounded_durations': {'activation_phase': 'R1',
                                                                                                                'assertion_ref': 'assertion:cognitive-loop-e2e-test-cycle-result-artifacts-cycle-result-has-trace-with-durations',
                                                                                                                'diagnostic_role': 'owner',
                                                                                                                'introduced_by_task': 'R1-Task-9',
                                                                                                                'owner_ref': 'runtime-path',
                                                                                                                'source_ast_sha256': 'b1b98f11092f5450e2d893a9b929dfa0a4874eabf0d1f47a9c2a1ab9169ef83b',
                                                                                                                'supersedes_node_id': 'tests/test_cognitive_loop_e2e.py::TestCycleResultArtifacts::test_cycle_result_has_trace_with_durations'},
 'tests/test_r1_cognitive_restart_successors.py::test_r1_restart_preserves_world_revision_without_admitted_effect': {'activation_phase': 'R1',
                                                                                                                     'assertion_ref': 'assertion:restart-e2e-test-restart-preserves-revisions-restart-preserves-world-revision',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'R1-Task-9',
                                                                                                                     'owner_ref': 'cycle-result',
                                                                                                                     'source_ast_sha256': '28be6d860ce4d06932397324182d7393ff2e1d02527a1aadaf8acd46d4466664',
                                                                                                                     'supersedes_node_id': 'tests/test_restart_e2e.py::TestRestartPreservesRevisions::test_restart_preserves_world_revision'},
 'tests/test_r1_cognitive_restart_successors.py::test_r1_restart_preserves_effect_revision_without_admitted_effect': {'activation_phase': 'R1',
                                                                                                                      'assertion_ref': 'assertion:restart-e2e-test-restart-preserves-revisions-restart-preserves-effect-revision',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'R1-Task-9',
                                                                                                                      'owner_ref': 'cycle-result',
                                                                                                                      'source_ast_sha256': '844d1ff4352f265fab21502c6730852de5ee47f060b997e4b0c4fee9502757b2',
                                                                                                                      'supersedes_node_id': 'tests/test_restart_e2e.py::TestRestartPreservesRevisions::test_restart_preserves_effect_revision'},
 'tests/test_r1_cognitive_restart_successors.py::test_r1_restart_preserves_every_revision_pin_dimension': {'activation_phase': 'R1',
                                                                                                           'assertion_ref': 'assertion:restart-e2e-test-restart-preserves-revisions-restart-preserves-revision-pin-fields',
                                                                                                           'diagnostic_role': 'owner',
                                                                                                           'introduced_by_task': 'R1-Task-9',
                                                                                                           'owner_ref': 'cycle-result',
                                                                                                           'source_ast_sha256': 'c8664c85ab24fe1856197ca814c712641d5ad69b7b061f416eaa3d49186ff612',
                                                                                                           'supersedes_node_id': 'tests/test_restart_e2e.py::TestRestartPreservesRevisions::test_restart_preserves_revision_pin_fields'},
 'tests/test_r1_cognitive_restart_successors.py::test_r1_restart_preserves_stable_revisions_across_multiple_cycles': {'activation_phase': 'R1',
                                                                                                                      'assertion_ref': 'assertion:restart-e2e-test-restart-multiple-cycles-restart-preserves-revisions-across-multiple-cycles',
                                                                                                                      'diagnostic_role': 'owner',
                                                                                                                      'introduced_by_task': 'R1-Task-9',
                                                                                                                      'owner_ref': 'cycle-result',
                                                                                                                      'source_ast_sha256': 'd7e312eb9df0212e60c2a05285aaf7277e41b7f491c0c30ed47950161031213e',
                                                                                                                      'supersedes_node_id': 'tests/test_restart_e2e.py::TestRestartMultipleCycles::test_restart_preserves_revisions_across_multiple_cycles'},
 'tests/test_r1_cognitive_restart_successors.py::test_r1_consecutive_cycles_preserve_revision_pins_without_effect': {'activation_phase': 'R1',
                                                                                                                     'assertion_ref': 'assertion:restart-e2e-test-restart-memory-consistency-consecutive-cycles-preserve-revision-pins',
                                                                                                                     'diagnostic_role': 'owner',
                                                                                                                     'introduced_by_task': 'R1-Task-9',
                                                                                                                     'owner_ref': 'cycle-result',
                                                                                                                     'source_ast_sha256': 'e5da0e6482b401210e93f28633d0555c59ddf44883d9956032d3b93e38d970af',
                                                                                                                     'supersedes_node_id': 'tests/test_restart_e2e.py::TestRestartMemoryConsistency::test_consecutive_cycles_preserve_revision_pins'},
 'tests/test_r1_cognitive_restart_successors.py::test_r1_no_stale_revision_reentry_precedes_unadmitted_effect': {'activation_phase': 'R1',
                                                                                                                 'assertion_ref': 'assertion:restart-e2e-test-stale-revision-restart-stale-revision-restart-at-orient',
                                                                                                                 'diagnostic_role': 'owner',
                                                                                                                 'introduced_by_task': 'R1-Task-9',
                                                                                                                 'owner_ref': 'cycle-result',
                                                                                                                 'source_ast_sha256': 'b8aaa2f2d110f2660a607edc943fe2e9b015eb56e61fd5ded3449c646b6673d0',
                                                                                                                 'supersedes_node_id': 'tests/test_restart_e2e.py::TestStaleRevisionRestart::test_stale_revision_restart_at_orient'},
 'tests/test_r1_cognitive_restart_successors.py::test_r1_cycle_result_after_reopen_contains_only_admitted_artifacts': {'activation_phase': 'R1',
                                                                                                                       'assertion_ref': 'assertion:restart-e2e-test-restart-cycle-result-structure-cycle-result-after-restart-has-all-artifacts',
                                                                                                                       'diagnostic_role': 'owner',
                                                                                                                       'introduced_by_task': 'R1-Task-9',
                                                                                                                       'owner_ref': 'cycle-result',
                                                                                                                       'source_ast_sha256': '4a0fff28a7d8b21bb19e646b1c0505be2851a0f611a7d4ab84d6352ebe13aead',
                                                                                                                       'supersedes_node_id': 'tests/test_restart_e2e.py::TestRestartCycleResultStructure::test_cycle_result_after_restart_has_all_artifacts'}}
