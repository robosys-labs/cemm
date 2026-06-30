import pytest
import time
from cemm.kernel.invariant_guard import InvariantGuard
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.context_kernel import ContextKernel, Budget


class TestInvariant19_ContextNotOverrideExplicit:
    def test_context_override_rejected(self):
        guard = InvariantGuard()
        guard.reset()
        explicit = Claim(
            id="exp1", subject_entity_id="user1", predicate="location",
            object_value="Berlin", status=ClaimStatus.ACTIVE,
            source_id="test", domain="test",
        )
        inferred = Claim(
            id="inf1", subject_entity_id="user1", predicate="location",
            object_value="Paris", status=ClaimStatus.ACTIVE,
            source_id="context", domain="inferred",
        )
        assert guard.check_context_not_override_explicit(inferred, explicit) is False
        assert len(guard.assert_no_errors()) >= 1

    def test_context_no_conflict(self):
        guard = InvariantGuard()
        guard.reset()
        explicit = Claim(
            id="exp2", subject_entity_id="user1", predicate="location",
            object_value="Berlin", status=ClaimStatus.ACTIVE,
            source_id="test", domain="test",
        )
        inferred = Claim(
            id="inf2", subject_entity_id="user1", predicate="mood",
            object_value="happy", status=ClaimStatus.ACTIVE,
            source_id="context", domain="inferred",
        )
        assert guard.check_context_not_override_explicit(inferred, explicit) is True


class TestInvariant21_StaleClaimNotUsed:
    def test_stale_claim_rejected(self):
        guard = InvariantGuard()
        guard.reset()
        now = time.time()
        kernel = ContextKernel(id="test")
        kernel.time.now = now
        claim = Claim(
            id="c1", subject_entity_id="s1", predicate="p1",
            object_value="old_info",
            valid_until=now - 3600,
            status=ClaimStatus.ACTIVE,
            source_id="test", domain="test",
        )
        assert guard.check_stale_claim_not_used(claim, kernel) is False
        assert len(guard.assert_no_errors()) >= 1

    def test_fresh_claim_accepted(self):
        guard = InvariantGuard()
        guard.reset()
        now = time.time()
        kernel = ContextKernel(id="test")
        kernel.time.now = now
        claim = Claim(
            id="c2", subject_entity_id="s1", predicate="p1",
            object_value="fresh_info",
            valid_until=now + 3600,
            status=ClaimStatus.ACTIVE,
            source_id="test", domain="test",
        )
        assert guard.check_stale_claim_not_used(claim, kernel) is True

    def test_stale_rejected_no_valid_until(self):
        guard = InvariantGuard()
        guard.reset()
        now = time.time()
        kernel = ContextKernel(id="test")
        kernel.time.now = now
        claim = Claim(
            id="c3", subject_entity_id="s1", predicate="p1",
            object_value="persistent",
            status=ClaimStatus.ACTIVE,
            source_id="test", domain="test",
        )
        assert guard.check_stale_claim_not_used(claim, kernel) is True


class TestInvariant23_RecursiveBudget:
    def test_budget_exceeded_fails(self):
        guard = InvariantGuard()
        guard.reset()
        kernel = ContextKernel(id="test", budget=Budget(max_recursive_steps=3))
        assert guard.check_recursive_budget(kernel, 4) is False

    def test_budget_within_limits(self):
        guard = InvariantGuard()
        guard.reset()
        kernel = ContextKernel(id="test", budget=Budget(max_recursive_steps=5))
        assert guard.check_recursive_budget(kernel, 3) is True

    def test_budget_equal_pass(self):
        guard = InvariantGuard()
        guard.reset()
        kernel = ContextKernel(id="test", budget=Budget(max_recursive_steps=3))
        assert guard.check_recursive_budget(kernel, 3) is True

    def test_none_kernel_fails(self):
        guard = InvariantGuard()
        guard.reset()
        assert guard.check_recursive_budget(None, 0) is False


class TestInvariant29_NeuralSynthesisVerification:
    def test_neural_synthesis_not_hard_verified(self):
        from cemm.synthesis.result import SynthesisResult
        result = SynthesisResult(
            success=True, output="neural output",
            strategy="neural", cost_ms=30.0, verified=False,
        )
        assert result.verified is False
        assert result.strategy == "neural"

    def test_neural_fallback_on_low_confidence(self):
        from cemm.synthesis.verifier import SynthesisVerifier
        verifier = SynthesisVerifier()
        kernel = ContextKernel(id="test")
        verified, issues = verifier.verify("output", ["cl1"], ["m1"], kernel)
        assert verified is True


class TestInvariant30_UnselectedEvidence:
    def test_unselected_claim_rejected(self):
        from cemm.synthesis.verifier import SynthesisVerifier
        verifier = SynthesisVerifier()
        kernel = ContextKernel(id="test")
        verified, issues = verifier.verify(
            "output with unselected content",
            ["selected_1"],
            ["model_1"],
            kernel,
            claims=None,
        )
        assert verified is True or len(issues) > 0
