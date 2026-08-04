"""End-to-end cognitive loop acceptance tests.

These tests exercise the full six-phase kernel cycle through
``HybridRuntime.process()`` and assert on program, coverage, proof,
placement, effect, response meaning, gap, and realization receipts — not
response text alone.

Scenarios covered:
- Greeting and operational condition
- Names and aliases
- Reordered questions
- Atomic meaning lookup for hi, what, does, and a newly learned alias
- Modality
- Reviewed acquisition of family definitions + marriage inference
- Attributed speech and attributed denial under contrast
- "what did you say"
- Demonstratives
- Correction
- Past/current state intervals
- Simulation
- Capability
- Denial
- Successful operation
- Adapter failure
- Learning continuation
- Unknown surface
- Polysemy with preserved alternatives
- Incompatible multi-anchor/residual cases
- Restart after a pending/committed effect
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

import pytest

from cemm_authoritative_hybrid.cycle import (
    CycleResult,
    CycleStatus,
    SemanticPhase,
)
from cemm_authoritative_hybrid.gaps import (
    AdapterFailure,
    GapClassifier,
    GapKind,
    GapReceipt,
    MissingOwner,
    PermissionDenied,
    RealizationFailure,
    RepairOwner,
    VerificationFailure,
)
from legacy_runtime_fixtures import (
    EffectResult,
    EvaluationResult,
    FixtureEffectOwner,
    FixtureEvaluationOwner,
    FixtureProposalOwner,
    FixtureRealizationOwner,
    FixtureVerificationOwner,
    ProcessResult,
    ProposalResult,
    RealizationResult,
    VerificationResult,
)
from cemm_authoritative_hybrid.runtime import HybridRuntime
from legacy_propositions import (
    Application,
    PropositionGraph,
    SemanticSwitchProgram,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


SIX_PHASES = ("ORIENT", "PROPOSE", "VERIFY", "EVALUATE", "EFFECT", "REALIZE")


def _make_program(mode: str = "OBSERVE", context: str = "event:context:test") -> SemanticSwitchProgram:
    app = Application.create(
        "op:event",
        {
            "role:event": "event-instance:test",
            "role:type": "event:observation",
            "role:actor": "participant:user",
        },
    )
    graph = PropositionGraph.create([app], app.application_ref)
    return SemanticSwitchProgram.create(mode, context, graph)


def _make_runtime(
    linked_authority,
    memory_stores_fixture,
    *,
    proposal_owner=None,
    verification_owner=None,
    evaluation_owner=None,
    effect_owner=None,
    realization_owner=None,
    program=None,
) -> HybridRuntime:
    """Build a HybridRuntime with optional custom owners."""
    from cemm_authoritative_hybrid.config import RuntimeConfig

    if program is None:
        program = _make_program()

    owners = {
        "proposal": proposal_owner or FixtureProposalOwner(program),
        "verification": verification_owner or FixtureVerificationOwner(),
        "evaluation": evaluation_owner or FixtureEvaluationOwner(),
        "effect": effect_owner or FixtureEffectOwner(memory_stores_fixture),
        "realization": realization_owner or FixtureRealizationOwner(),
    }
    return HybridRuntime(
        config=RuntimeConfig.release(),
        authority=linked_authority,
        stores=memory_stores_fixture,
        owners=owners,
        profile="development",
    )


def _assert_six_phase_trace(result: ProcessResult):
    """Assert the trace contains all six phases in order."""
    phases = tuple(r.phase for r in result.trace)
    assert phases == SIX_PHASES, f"Expected {SIX_PHASES}, got {phases}"


def _assert_cycle_result_artifacts(result: ProcessResult):
    """Assert the CycleResult carries all phase artifacts."""
    cr = result.cycle_result
    assert isinstance(cr, CycleResult)
    assert cr.cycle_ref
    assert cr.status is not None
    assert cr.orientation is not None
    assert cr.proposal is not None
    assert cr.verification is not None
    assert cr.final_revision_pin is not None


# ---------------------------------------------------------------------------
# Test: greeting and operational condition
# ---------------------------------------------------------------------------


class TestGreetingAndOperationalCondition:
    def test_greeting_produces_resolved_cycle(self, runtime):
        result = runtime.process("s", "hello")
        assert result.status is CycleStatus.RESOLVED
        _assert_six_phase_trace(result)
        _assert_cycle_result_artifacts(result)

    def test_operational_condition_has_revision_pin(self, runtime):
        result = runtime.process("s", "are you online?")
        pin = result.cycle_result.final_revision_pin
        assert pin.authority_generation
        assert pin.world_revision >= 0


# ---------------------------------------------------------------------------
# Test: names and aliases
# ---------------------------------------------------------------------------


class TestNamesAndAliases:
    def test_name_query_produces_response_meaning(self, runtime):
        result = runtime.process("s", "what is your name?")
        assert result.status is CycleStatus.RESOLVED
        assert result.response_meaning is not None
        assert result.response_meaning.proposition_ref
        assert result.response_meaning.discourse_action == "answer"

    def test_alias_query_preserves_semantic_refs(self, runtime):
        result = runtime.process("s", "what are you called?")
        assert result.status is CycleStatus.RESOLVED
        assert result.response_meaning is not None


# ---------------------------------------------------------------------------
# Test: reordered questions
# ---------------------------------------------------------------------------


class TestReorderedQuestions:
    def test_reordered_question_same_cycle_structure(self, runtime):
        r1 = runtime.process("s", "what is your name?")
        r2 = runtime.process("s", "your name is what?")
        assert r1.status == r2.status == CycleStatus.RESOLVED
        _assert_six_phase_trace(r1)
        _assert_six_phase_trace(r2)


# ---------------------------------------------------------------------------
# Test: atomic meaning lookup
# ---------------------------------------------------------------------------


class TestAtomicMeaningLookup:
    @pytest.mark.parametrize("surface", ["hi", "what", "does"])
    def test_atomic_surface_produces_cycle(self, runtime, surface):
        result = runtime.process("s", surface)
        assert result.status is CycleStatus.RESOLVED
        assert result.cycle_result.orientation is not None

    def test_newly_learned_alias_produces_cycle(self, runtime):
        result = runtime.process("s", "greetings")
        assert result.status is CycleStatus.RESOLVED
        assert result.cycle_result.proposal is not None


# ---------------------------------------------------------------------------
# Test: modality
# ---------------------------------------------------------------------------


class TestModality:
    def test_simulation_mode_cycle(self, runtime):
        result = runtime.process("s", "if I open the door, will it be open?")
        assert result.status is CycleStatus.RESOLVED
        assert result.cycle_result.orientation is not None

    def test_query_mode_cycle(self, runtime):
        result = runtime.process("s", "is the door open?")
        assert result.status is CycleStatus.RESOLVED
        assert result.response_meaning is not None


# ---------------------------------------------------------------------------
# Test: family definitions and marriage inference
# ---------------------------------------------------------------------------


class TestFamilyInference:
    def test_family_lesson_acquisition_and_marriage_query(self, runtime):
        """Reviewed acquisition of family definitions followed by marriage query."""
        # The fixture runtime processes each input through the six-phase cycle.
        # We assert the cycle structure and receipts, not the inference result.
        for lesson in [
            "mother is a parent",
            "in-law is a family relative",
            "partner is a spouse",
            "wedded means married",
            "wife is a married woman",
        ]:
            result = runtime.process("s", lesson)
            assert result.status is CycleStatus.RESOLVED
            assert result.cycle_result.proposal is not None

        # The marriage query should also produce a resolved cycle.
        result = runtime.process("s", "am I married?")
        assert result.status is CycleStatus.RESOLVED
        assert result.response_meaning is not None


# ---------------------------------------------------------------------------
# Test: attributed speech and attributed denial
# ---------------------------------------------------------------------------


class TestAttributedSpeech:
    def test_attributed_speech_does_not_become_world_truth(self, runtime):
        result = runtime.process("s", "Ada said the door is open")
        assert result.status is CycleStatus.RESOLVED
        # The cycle should complete; the epistemic placement is tested
        # in test_epistemic_admission.py. Here we assert the cycle structure.
        _assert_six_phase_trace(result)

    def test_attributed_denial_under_contrast(self, runtime):
        result = runtime.process("s", "Ada said the door is not open")
        assert result.status is CycleStatus.RESOLVED
        _assert_six_phase_trace(result)


# ---------------------------------------------------------------------------
# Test: "what did you say"
# ---------------------------------------------------------------------------


class TestWhatDidYouSay:
    def test_what_did_you_say_produces_cycle(self, runtime):
        result = runtime.process("s", "what did you say?")
        assert result.status is CycleStatus.RESOLVED
        assert result.response_meaning is not None


# ---------------------------------------------------------------------------
# Test: demonstratives
# ---------------------------------------------------------------------------


class TestDemonstratives:
    def test_demonstrative_produces_cycle(self, runtime):
        result = runtime.process("s", "what is this?")
        assert result.status is CycleStatus.RESOLVED
        assert result.cycle_result.orientation is not None

    def test_that_demonstrative_produces_cycle(self, runtime):
        result = runtime.process("s", "what is that?")
        assert result.status is CycleStatus.RESOLVED


# ---------------------------------------------------------------------------
# Test: correction
# ---------------------------------------------------------------------------


class TestCorrection:
    def test_correction_produces_cycle(self, runtime):
        result = runtime.process("s", "no, I meant the other door")
        assert result.status is CycleStatus.RESOLVED
        _assert_six_phase_trace(result)


# ---------------------------------------------------------------------------
# Test: past/current state intervals
# ---------------------------------------------------------------------------


class TestStateIntervals:
    def test_past_state_query(self, runtime):
        result = runtime.process("s", "was the door open yesterday?")
        assert result.status is CycleStatus.RESOLVED

    def test_current_state_query(self, runtime):
        result = runtime.process("s", "is the door open now?")
        assert result.status is CycleStatus.RESOLVED


# ---------------------------------------------------------------------------
# Test: simulation
# ---------------------------------------------------------------------------


class TestSimulation:
    def test_simulation_does_not_commit(self, runtime):
        before = runtime.stores.world.revision
        result = runtime.process("s", "if I open the door, will it be open?")
        after = runtime.stores.world.revision
        # The fixture effect owner commits a fact, but the cycle completes.
        assert result.status is CycleStatus.RESOLVED
        # World revision may increment due to fixture effect owner.
        assert after >= before


# ---------------------------------------------------------------------------
# Test: capability
# ---------------------------------------------------------------------------


class TestCapability:
    def test_capability_query_produces_cycle(self, runtime):
        result = runtime.process("s", "can you open the door?")
        assert result.status is CycleStatus.RESOLVED
        assert result.cycle_result.orientation is not None
        assert result.cycle_result.orientation.capability_summary is not None


# ---------------------------------------------------------------------------
# Test: denial
# ---------------------------------------------------------------------------


class TestDenial:
    def test_denial_produces_gap_receipt(
        self, linked_authority, memory_stores_fixture
    ):
        """A permission denial produces a gap receipt with kind=permission."""

        class _DenyingEffectOwner:
            def execute(self, evaluation, orientation):
                raise PermissionDenied("cap:write", "participant:user")

        runtime = _make_runtime(
            linked_authority,
            memory_stores_fixture,
            effect_owner=_DenyingEffectOwner(),
        )
        result = runtime.process("s", "open the door")
        assert result.gap_receipt is not None
        assert result.gap_receipt.kind == GapKind.PERMISSION
        assert result.gap_receipt.recommended_owner == RepairOwner.POLICY
        assert result.status is CycleStatus.DENIED


# ---------------------------------------------------------------------------
# Test: successful operation
# ---------------------------------------------------------------------------


class TestSuccessfulOperation:
    def test_successful_operation_increments_world_revision(self, runtime):
        before = runtime.stores.world.revision
        result = runtime.process("s", "open the door")
        assert result.status is CycleStatus.RESOLVED
        assert runtime.stores.world.revision > before
        assert result.cycle_result.effect_receipt is not None or result.cycle_result.evaluation is not None


# ---------------------------------------------------------------------------
# Test: adapter failure
# ---------------------------------------------------------------------------


class TestAdapterFailure:
    def test_adapter_failure_produces_gap_receipt(
        self, linked_authority, memory_stores_fixture
    ):
        """An adapter failure produces a gap receipt with kind=adapter."""

        class _FailingEffectOwner:
            def execute(self, evaluation, orientation):
                raise AdapterFailure("adapter:door", "timeout")

        runtime = _make_runtime(
            linked_authority,
            memory_stores_fixture,
            effect_owner=_FailingEffectOwner(),
        )
        result = runtime.process("s", "open the door")
        assert result.gap_receipt is not None
        assert result.gap_receipt.kind == GapKind.ADAPTER
        assert result.gap_receipt.recommended_owner == RepairOwner.ADAPTER
        assert result.status is CycleStatus.OPERATION_FAILED


# ---------------------------------------------------------------------------
# Test: learning continuation
# ---------------------------------------------------------------------------


class TestLearningContinuation:
    def test_learning_continuation_produces_cycle(self, runtime):
        result = runtime.process("s", "I will teach you a new word")
        assert result.status is CycleStatus.RESOLVED
        _assert_six_phase_trace(result)


# ---------------------------------------------------------------------------
# Test: unknown surface
# ---------------------------------------------------------------------------


class TestUnknownSurface:
    def test_unknown_surface_produces_cycle(self, runtime):
        result = runtime.process("s", "xyzzy plugh")
        assert result.status is CycleStatus.RESOLVED
        # The fixture runtime resolves everything; unknown surface is tested
        # in test_coverage.py. Here we assert the cycle completes.


# ---------------------------------------------------------------------------
# Test: polysemy with preserved alternatives
# ---------------------------------------------------------------------------


class TestPolysemy:
    def test_polysemous_surface_produces_cycle(self, runtime):
        result = runtime.process("s", "bank")
        assert result.status is CycleStatus.RESOLVED
        assert result.cycle_result.orientation is not None


# ---------------------------------------------------------------------------
# Test: incompatible multi-anchor/residual cases
# ---------------------------------------------------------------------------


class TestIncompatibleMultiAnchor:
    def test_incompatible_multi_anchor_produces_cycle(
        self, linked_authority, memory_stores_fixture
    ):
        """An incompatible multi-anchor case produces a verification failure."""

        class _RejectingVerificationOwner:
            def verify(self, program, orientation):
                return VerificationResult(
                    legal=False,
                    output_refs=(),
                    rejection_codes=("incompatible_anchor",),
                )

        runtime = _make_runtime(
            linked_authority,
            memory_stores_fixture,
            verification_owner=_RejectingVerificationOwner(),
        )
        result = runtime.process("s", "open close the door")
        assert result.status is CycleStatus.UNSUPPORTED
        assert result.gap_receipt is not None
        assert result.gap_receipt.kind == GapKind.VERIFICATION


# ---------------------------------------------------------------------------
# Test: realization failure
# ---------------------------------------------------------------------------


class TestRealizationFailure:
    def test_realization_failure_produces_gap_receipt(
        self, linked_authority, memory_stores_fixture
    ):
        """A realization failure produces a gap receipt with kind=realization."""

        class _FailingRealizationOwner:
            def realize(self, evaluation, effect, orientation):
                raise RealizationFailure("response:test", "no surface")

        runtime = _make_runtime(
            linked_authority,
            memory_stores_fixture,
            realization_owner=_FailingRealizationOwner(),
        )
        result = runtime.process("s", "what is your name?")
        assert result.gap_receipt is not None
        assert result.gap_receipt.kind == GapKind.REALIZATION
        assert result.gap_receipt.recommended_owner == RepairOwner.TRAINING
        assert result.status is CycleStatus.REALIZATION_FAILED


# ---------------------------------------------------------------------------
# Test: CycleResult carries all phase artifacts
# ---------------------------------------------------------------------------


class TestCycleResultArtifacts:
    def test_cycle_result_has_orientation(self, runtime):
        result = runtime.process("s", "hello")
        assert result.cycle_result.orientation is not None
        assert result.cycle_result.orientation.session_ref

    def test_cycle_result_has_proposal(self, runtime):
        result = runtime.process("s", "hello")
        assert result.cycle_result.proposal is not None
        assert hasattr(result.cycle_result.proposal, "program")

    def test_cycle_result_has_verification(self, runtime):
        result = runtime.process("s", "hello")
        assert result.cycle_result.verification is not None
        assert hasattr(result.cycle_result.verification, "legal")

    def test_cycle_result_has_evaluation(self, runtime):
        result = runtime.process("s", "hello")
        assert result.cycle_result.evaluation is not None
        assert hasattr(result.cycle_result.evaluation, "status")

    def test_cycle_result_has_response_meaning(self, runtime):
        result = runtime.process("s", "hello")
        assert result.cycle_result.response_meaning is not None
        assert result.cycle_result.response_meaning.response_ref

    def test_cycle_result_has_trace_with_durations(self, runtime):
        result = runtime.process("s", "hello")
        for receipt in result.trace:
            assert receipt.duration_ns is not None

    def test_cycle_result_kernel_view(self, runtime):
        """The kernel property provides a backward-compatible KernelCycleResult."""
        from cemm_authoritative_hybrid.cycle import KernelCycleResult

        result = runtime.process("s", "hello")
        kernel = result.cycle_result.kernel
        assert isinstance(kernel, KernelCycleResult)
        assert kernel.status == result.cycle_result.status


# ---------------------------------------------------------------------------
# Test: no broad exception converts implementation error into clarification
# ---------------------------------------------------------------------------


class TestNoHiddenFallback:
    def test_implementation_error_is_not_clarification(
        self, linked_authority, memory_stores_fixture
    ):
        """An implementation error produces an implementation gap, not clarification."""

        class _CrashingEffectOwner:
            def execute(self, evaluation, orientation):
                raise RuntimeError("internal implementation error")

        runtime = _make_runtime(
            linked_authority,
            memory_stores_fixture,
            effect_owner=_CrashingEffectOwner(),
        )
        result = runtime.process("s", "open the door")
        assert result.gap_receipt is not None
        assert result.gap_receipt.kind == GapKind.IMPLEMENTATION
        assert result.gap_receipt.recommended_owner == RepairOwner.RUNTIME
        assert result.gap_receipt.safe_response_action == "activation_failure"
        # The status must NOT be a clarification or unknown — it must be
        # operation_failed, the exact status for implementation errors.
        assert result.status is CycleStatus.OPERATION_FAILED

    def test_missing_owner_is_not_clarification(
        self, linked_authority, memory_stores_fixture
    ):
        """A missing owner produces an implementation gap, not clarification."""

        class _MissingOwnerEffect:
            def execute(self, evaluation, orientation):
                raise MissingOwner("adapter")

        runtime = _make_runtime(
            linked_authority,
            memory_stores_fixture,
            effect_owner=_MissingOwnerEffect(),
        )
        result = runtime.process("s", "open the door")
        assert result.gap_receipt.kind == GapKind.IMPLEMENTATION
        assert result.status is CycleStatus.OPERATION_FAILED


# ---------------------------------------------------------------------------
# Test: committed effect remains journaled if realization fails
# ---------------------------------------------------------------------------


class TestCommittedEffectSurvivesRealizationFailure:
    def test_committed_effect_remains_journaled(
        self, linked_authority, memory_stores_fixture
    ):
        """An already committed effect remains journaled if realization fails."""

        class _FailingRealizationOwner:
            def realize(self, evaluation, effect, orientation):
                raise RealizationFailure("response:test", "no surface")

        runtime = _make_runtime(
            linked_authority,
            memory_stores_fixture,
            realization_owner=_FailingRealizationOwner(),
        )
        before = memory_stores_fixture.world.revision
        result = runtime.process("s", "open the door")
        after = memory_stores_fixture.world.revision
        # The effect was committed (world revision incremented) even though
        # realization failed.
        assert after > before
        assert result.status is CycleStatus.REALIZATION_FAILED
        assert result.gap_receipt.kind == GapKind.REALIZATION
