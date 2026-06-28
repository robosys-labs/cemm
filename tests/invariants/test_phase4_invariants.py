import pytest
from cemm.kernel.invariant_guard import InvariantGuard
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.action import Action, ActionKind, ActionStatus
from cemm.types.trace import Trace
from cemm.types.permission import Permission, RetentionPolicy


class TestNewInvariants:
    def test_context_kernel_before_interpretation(self):
        guard = InvariantGuard()
        guard.reset()
        assert guard.check_context_kernel_before_interpretation(object()) is True
        assert guard.check_context_kernel_before_interpretation(None) is False
        assert len(guard.assert_no_errors()) >= 1

    def test_response_has_input_signal(self):
        guard = InvariantGuard()
        guard.reset()
        assert guard.check_response_has_input_signal(object()) is True
        assert guard.check_response_has_input_signal(None) is False

    def test_self_mutation_has_trace(self):
        guard = InvariantGuard()
        guard.reset()
        action = Action(id="a1", kind=ActionKind.REFLECT, operator_model_id="reflect_op",
                        status=ActionStatus.EXECUTED)
        assert guard.check_self_mutation_has_trace(action) is False
        action.trace = Trace(context_id="ctx")
        guard.reset()
        assert guard.check_self_mutation_has_trace(action) is True

    def test_prediction_not_presented_as_fact(self):
        guard = InvariantGuard()
        guard.reset()
        claim = Claim(id="c1", subject_entity_id="s1", predicate="p1",
                      confidence=0.99, status=ClaimStatus.ACTIVE)
        assert guard.check_prediction_not_presented_as_fact(claim) is True
        claim.confidence = 1.0
        assert guard.check_causal_chain_confidence([{"confidence": 1.0}]) is False

    def test_insults_not_factual_claims(self):
        guard = InvariantGuard()
        guard.reset()
        claim = Claim(id="c1", subject_entity_id="self_main", predicate="is_dumb",
                      status=ClaimStatus.ACTIVE)
        assert guard.check_insults_are_not_factual_claims(claim, "self_main") is False

    def test_temporary_frustration_not_persisted(self):
        guard = InvariantGuard()
        guard.reset()
        claim = Claim(id="c1", subject_entity_id="u1", predicate="is_frustrated",
                      status=ClaimStatus.ACTIVE,
                      permission=Permission(retention=RetentionPolicy.LONG_TERM))
        assert guard.check_temporary_frustration_not_persisted(claim) is False
