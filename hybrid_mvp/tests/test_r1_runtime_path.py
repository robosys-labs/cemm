"""R1 hard-cut runtime-path contracts."""

from __future__ import annotations

import ast
import importlib.util
import inspect
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.config import RuntimeConfig
from cemm_authoritative_hybrid.cycle import (
    CycleResult,
    CycleStatus,
    Orientation,
    SemanticMode,
    SemanticPhase,
)
from cemm_authoritative_hybrid.r3_cycle import CycleResult as R3CycleResult
from cemm_authoritative_hybrid.persistence import RevisionPin, memory_stores
from cemm_authoritative_hybrid.runtime import HybridRuntime


def _selected_artifacts():
    pin = RevisionPin("authority:r1-runtime", 0, 0, 0, 0, "model:r1-runtime")
    orientation = Orientation.create(
        session_ref="session:r1-runtime",
        turn_ref="turn:r1-runtime",
        source_text="alice likes bob",
        mode=SemanticMode.OBSERVE,
        participant_frame="participant:user",
        temporal_frame="now",
        participants=("participant:user", "participant:system"),
        active_turn_ref="turn:r1-runtime",
        event_refs=("turn:r1-runtime",),
        focus_refs=(),
        obligation_refs=(),
        capability_summary=(),
        permission_summary=(),
        budgets={"input_tokens": 3},
        scanned_atom_count=0,
        index_probes=("designations:for_surface",),
        visited_refs=(),
        revision_pin=pin,
    )
    helper_path = Path(__file__).with_name("test_r1_verification_batch.py")
    spec = importlib.util.spec_from_file_location("_r1_runtime_helpers", helper_path)
    helpers = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(helpers)
    context = helpers._context(
        orientation_ref=orientation.orientation_ref,
        revision_pin=pin,
    )
    proposal = helpers._proposal(context, (helpers._program(context, 1),), (100,))
    verification = helpers._verifier().verify_candidates(proposal, context)
    assert verification.status == "selected"
    return pin, orientation, context, proposal, verification


class _RecordingProposalOwner:
    def __init__(self, proposal):
        self.proposal = proposal
        self.model_identity = proposal.model_identity
        self.contexts = []

    def propose(self, context):
        self.contexts.append(context)
        return self.proposal


class _RecordingVerificationOwner:
    def __init__(self, verification):
        self.verification = verification
        self.calls = []

    def verify_candidates(self, proposal, context):
        self.calls.append((proposal, context))
        return self.verification


class _RecordingOrientationOwner:
    def __init__(self, orientation, context):
        self.orientation = orientation
        self.context = context

    def orient(self, session_ref, text):
        return self.orientation, self.context


def _runtime(*, proposal_owner=None):
    pin, orientation, context, proposal, verification = _selected_artifacts()
    proposer = proposal_owner or _RecordingProposalOwner(proposal)
    verifier = _RecordingVerificationOwner(verification)
    runtime = HybridRuntime(
        RuntimeConfig.release(),
        object(),
        memory_stores(
            authority_generation=pin.authority_generation,
            model_identity=pin.model_identity,
        ),
        {
            "orientation": _RecordingOrientationOwner(orientation, context),
            "proposal": proposer,
            "verification": verifier,
        },
        profile="development",
    )
    return runtime, proposer, verifier, context, proposal


def test_r1_runtime_has_one_exact_public_process_path():
    signature = inspect.signature(HybridRuntime.process)
    assert tuple(signature.parameters) == ("self", "session_ref", "text", "trace")
    assert signature.parameters["trace"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["trace"].default is True
    assert not hasattr(HybridRuntime, "propose_and_verify")

    source_path = Path(inspect.getsourcefile(HybridRuntime))
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    class_names = {
        node.name for node in tree.body if isinstance(node, ast.ClassDef)
    }
    assert not {
        "ProposalResult",
        "VerificationResult",
        "EvaluationResult",
        "EffectResult",
        "RealizationResult",
        "ProcessResult",
    } & class_names
    assert "inspect.signature" not in source
    assert "getattr(owner" not in source
    assert "except Exception" not in source


def test_r1_selected_meaning_stops_at_exact_later_owner_gap():
    runtime, proposer, verifier, context, proposal = _runtime()
    result = runtime.process("session:r1-runtime", "alice likes bob", trace=True)

    assert type(result) is CycleResult
    assert proposer.contexts == [context]
    assert proposer.contexts[0] is context
    assert verifier.calls == [(proposal, context)]
    assert verifier.calls[0][1] is context
    assert result.status is CycleStatus.PARTIAL
    assert tuple(row.phase for row in result.phase_material) == (
        SemanticPhase.ORIENT,
        SemanticPhase.PROPOSE,
        SemanticPhase.VERIFY,
    )
    assert tuple(row.phase for row in result.trace) == (
        SemanticPhase.ORIENT,
        SemanticPhase.PROPOSE,
        SemanticPhase.VERIFY,
    )
    assert result.evaluation is None
    assert result.effect_receipt is None
    assert result.response_meaning is None
    assert result.realization_receipt is None
    meaning = result.verification.selected_meaning
    assert meaning is not None
    assert result.gap_receipt.source_refs == (meaning.verified_meaning_ref,)
    assert result.gap_receipt.missing_contract_refs == ("contract:r3:evaluate",)
    assert result.gap_receipt.safe_response_action == "stop_without_surface"


def test_r1_trace_is_observational_and_cycle_identity_is_stable():
    runtime, _, _, _, _ = _runtime()
    traced = runtime.process("session:r1-runtime", "alice likes bob", trace=True)
    untraced = runtime.process("session:r1-runtime", "alice likes bob", trace=False)
    assert traced.cycle_ref == untraced.cycle_ref
    assert traced.trace
    assert untraced.trace == ()
    assert traced.phase_material == untraced.phase_material


def test_r1_programming_exceptions_propagate_without_shape_adaptation():
    class BrokenProposalOwner:
        model_identity = "model:r1-runtime"

        def propose(self, context):
            raise RuntimeError("programming defect")

    runtime, _, _, _, _ = _runtime(proposal_owner=BrokenProposalOwner())
    with pytest.raises(RuntimeError, match="programming defect"):
        runtime.process("session:r1-runtime", "alice likes bob")


def test_r1_legacy_m4_evaluator_is_explicitly_disabled():
    from cemm_authoritative_hybrid.evaluation import Evaluator

    evaluator = object.__new__(Evaluator)
    with pytest.raises(RuntimeError, match="R4.*expression.*R5"):
        evaluator.evaluate()

def test_r1_injected_program_reaches_every_admitted_owner_then_stops():
    runtime, _, _, _, _ = _runtime()
    result = runtime.process("session:r1-six-phase", "alice likes bob")
    assert result.status is CycleStatus.PARTIAL
    assert tuple(row.phase for row in result.phase_material) == (
        SemanticPhase.ORIENT,
        SemanticPhase.PROPOSE,
        SemanticPhase.VERIFY,
    )
    assert result.gap_receipt.missing_contract_refs == ("contract:r3:evaluate",)


def test_r1_trace_off_preserves_selected_cycle_material():
    runtime, _, _, _, _ = _runtime()
    result = runtime.process(
        "session:r1-trace-off-successor", "alice likes bob", trace=False
    )
    assert result.status is CycleStatus.PARTIAL
    assert result.verification.status == "selected"
    assert result.trace == ()
    assert len(result.phase_material) == 3


def test_r1_disabled_effect_owner_does_not_advance_world_revision():
    runtime, _, _, _, _ = _runtime()
    first = runtime.process("session:r1-two-cycles", "alice likes bob")
    second = runtime.process("session:r1-two-cycles", "alice likes bob")
    assert first.final_revision_pin.world_revision == 0
    assert second.final_revision_pin.world_revision == 0
    assert first.effect_receipt is second.effect_receipt is None


def test_r1_phase_receipts_use_semantic_names_not_stage_numbers():
    runtime, _, _, _, _ = _runtime()
    result = runtime.process("session:r1-named-phases", "alice likes bob")
    assert "stage" not in str(result.as_dict()).casefold()
    assert tuple(row.phase for row in result.phase_material) == (
        SemanticPhase.ORIENT,
        SemanticPhase.PROPOSE,
        SemanticPhase.VERIFY,
    )


def test_r1_selected_cycle_has_exact_later_owner_gap_until_r3():
    runtime, _, _, _, _ = _runtime()
    result = runtime.process("session:r1-gap-successor", "alice likes bob")
    assert result.gap_receipt is not None
    assert result.gap_receipt.status == "later_owner_not_admitted"
    assert result.gap_receipt.missing_contract_refs == ("contract:r3:evaluate",)


def test_r1_development_profile_uses_canonical_process(monkeypatch):
    import cemm_authoritative_hybrid.bootstrap as bootstrap_module
    from cemm_authoritative_hybrid.bootstrap import load_runtime

    root = Path(__file__).parents[1]
    monkeypatch.setattr(
        bootstrap_module,
        "open_stores",
        lambda _path, *, authority_generation, model_identity: memory_stores(
            authority_generation=authority_generation,
            model_identity=model_identity,
        ),
    )
    runtime = load_runtime(root, profile="development")
    try:
        result = runtime.process("session:r1-development", "hello")
    finally:
        runtime.stores.close()
    assert runtime.profile == "development"
    assert type(result) in (CycleResult, R3CycleResult)
    assert result.proposal is not None


def test_r1_receipts_bind_exact_orientation_and_context_refs():
    runtime, _, _, context, _ = _runtime()
    orientation, oriented_context = runtime.orient(
        "session:r1-receipts", "alice likes bob"
    )
    result = runtime.process("session:r1-receipts", "alice likes bob")

    assert oriented_context is context
    assert result.orientation is orientation
    orient_material, propose_material, verify_material = result.phase_material
    assert orient_material.output_refs == (
        orientation.orientation_ref,
        context.context_ref,
    )
    assert propose_material.input_refs == orient_material.output_refs
    assert verify_material.input_refs == (
        result.proposal.proposal_ref,
        context.context_ref,
    )


__cemm_test_inventory__ = {
    "tests/test_r1_runtime_path.py::test_r1_runtime_has_one_exact_public_process_path": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-one-runtime-path",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "093e77a0632483638379e7211cd852bd58e42018b06f8a0971be8dfde1c47798",
    },
    "tests/test_r1_runtime_path.py::test_r1_selected_meaning_stops_at_exact_later_owner_gap": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-selected-stops-at-r3",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "9e4ca9a582dbeab55dbd00c562af0a42359c7e4421098726ee155e5105e6352c",
    },
    "tests/test_r1_runtime_path.py::test_r1_trace_is_observational_and_cycle_identity_is_stable": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-runtime-trace-observational",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "da6b96e21fbe5f6d01008f2c92cdf05faef929af48069b6bf41ae540306a0b0d",
    },
    "tests/test_r1_runtime_path.py::test_r1_programming_exceptions_propagate_without_shape_adaptation": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-runtime-exceptions-propagate",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "3bd9b6cb064b539953747fa801c423ad83bec554a6e3d6b67d94195c694d9139",
    },
    "tests/test_r1_runtime_path.py::test_r1_legacy_m4_evaluator_is_explicitly_disabled": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-legacy-m4-evaluation-disabled",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "d7642b1030ad984633662842bca0110e1dff922e1ea9f554bd0cec6cfae83808",
    },
    "tests/test_r1_runtime_path.py::test_r1_injected_program_reaches_every_admitted_owner_then_stops": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:six-phase-runtime-injected-program-runs-through-six-phase-owners",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "fe5aa3933bde32e280d544ebd86893dacaf8fccb4ad8d48da76a2c0abb47b7fe",
        "supersedes_node_id": "tests/test_six_phase_runtime.py::test_injected_program_runs_through_six_phase_owners",
    },
    "tests/test_r1_runtime_path.py::test_r1_trace_off_preserves_selected_cycle_material": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:six-phase-runtime-trace-off-still-resolves",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "1529092c649f49718009894470e60bdcef95d16183ac1469acfc76b7db3cb23c",
        "supersedes_node_id": "tests/test_six_phase_runtime.py::test_trace_off_still_resolves",
    },
    "tests/test_r1_runtime_path.py::test_r1_disabled_effect_owner_does_not_advance_world_revision": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:six-phase-runtime-second-cycle-increments-world-revision",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "100d914fc6b8429b36264ff94091a2a42f02426ad1ef5f932d9908f09ca61fd5",
        "supersedes_node_id": "tests/test_six_phase_runtime.py::test_second_cycle_increments_world_revision",
    },
    "tests/test_r1_runtime_path.py::test_r1_phase_receipts_use_semantic_names_not_stage_numbers": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:six-phase-runtime-phase-receipts-have-named-phases-not-stage-numbers",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "b584d84aac7adff66a492bd13fcd60f5616429cc59ee7523cbde9ed89634930e",
        "supersedes_node_id": "tests/test_six_phase_runtime.py::test_phase_receipts_have_named_phases_not_stage_numbers",
    },
    "tests/test_r1_runtime_path.py::test_r1_selected_cycle_has_exact_later_owner_gap_until_r3": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:six-phase-runtime-gap-receipt-is-none-on-resolved-cycle",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "c697406b6f5d9295a0dace4deecfd6b599ea5ae1f042bf5b4769228b6b507d38",
        "supersedes_node_id": "tests/test_six_phase_runtime.py::test_gap_receipt_is_none_on_resolved_cycle",
    },
    "tests/test_r1_runtime_path.py::test_r1_development_profile_uses_canonical_process": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:production-proposer-cutover-development-profile-still-works",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "f97074023bfcbf1a616f5c5a1d8a808817b7826fe4cb4458d8ac640be3ae0708",
        "supersedes_node_id": "tests/test_production_proposer_cutover.py::test_development_profile_still_works",
    },
    "tests/test_r1_runtime_path.py::test_r1_receipts_bind_exact_orientation_and_context_refs": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-slice-b-runtime-receipts-bind-orientation-content",
        "diagnostic_role": "owner",
        "introduced_by_task": "R1-Task-9",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "b8b3e082a888035ac961d7d096414f379e221b84f2f8bf847011bd34b834d1d5",
        "supersedes_node_id": "tests/test_six_phase_runtime.py::test_runtime_receipts_bind_exact_orientation_content_ref",
    },
}
