from cemm.confidence.scoring import score_claim
from cemm.types.context_kernel import ContextKernel
from cemm.types.permission import Permission


def test_permission_invalid_zeroes_claim_score():
    score = score_claim(
        relevance=1.0,
        trust=1.0,
        confidence=1.0,
        salience=1.0,
        recency=1.0,
        permission_valid=False,
    )
    assert score == 0.0


def test_context_kernel_has_self_state_or_reference():
    kernel = ContextKernel(id="ctx")
    assert hasattr(kernel, "self_state") or hasattr(kernel, "self_state_id")
