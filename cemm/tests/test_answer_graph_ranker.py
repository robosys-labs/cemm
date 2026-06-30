"""Tests for answer graph ranker."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cemm.kernel.answer_graph_ranker import rank_candidates, best_candidate
from cemm.types.context_kernel import ContextKernel, GoalState, MemoryState
from cemm.types.permission import Permission
from cemm.types.semantic_answer_graph import SemanticAnswerGraph, AnswerVerification
from cemm.types.semantic_event_graph import SemanticEventGraph


def _make_sag(intent: str, confidence: float, claim_ids: list[str] | None = None,
              verified: bool = False, scope: str = "public") -> SemanticAnswerGraph:
    return SemanticAnswerGraph(
        id=f"sag_{intent}",
        intent=intent,
        source_signal_ids=["sig_1"],
        context_id="ctx_1",
        selected_claim_ids=claim_ids or [],
        confidence=confidence,
        permission_scope=scope,
        verification=AnswerVerification(supported=verified, verification_type="hard" if verified else "none"),
    )


def _kernel(permission_scope: str = "public", claim_ids: list[str] | None = None) -> ContextKernel:
    from cemm.types.permission import PermissionScope
    return ContextKernel(
        id="test_kernel",
        goal=GoalState(),
        memory=MemoryState(candidate_claim_ids=claim_ids or []),
        permission=Permission(scope=getattr(PermissionScope, permission_scope.upper(), PermissionScope.PUBLIC)),
    )


def _graph(claim_refs: list[str] | None = None) -> SemanticEventGraph:
    return SemanticEventGraph(id="g1", source_signal_ids=[], context_id="ctx_1",
                               entity_refs=[], processes=[], states=[],
                               claim_refs=claim_refs or [])


def test_rank_prefers_higher_confidence() -> None:
    kernel = _kernel()
    graph = _graph(["c1", "c2"])
    low = _make_sag("answer", 0.4, ["c1"])
    high = _make_sag("answer", 0.9, ["c1", "c2"])
    ranked = rank_candidates([low, high], kernel, graph)
    assert ranked[0][0].id == high.id
    assert ranked[0][1] > ranked[1][1]


def test_rank_prefers_verified() -> None:
    kernel = _kernel()
    graph = _graph(["c1"])
    unverified = _make_sag("answer", 0.7, ["c1"], verified=False)
    verified = _make_sag("answer", 0.7, ["c1"], verified=True)
    ranked = rank_candidates([unverified, verified], kernel, graph)
    assert ranked[0][0].id == verified.id


def test_rank_respects_permission() -> None:
    kernel = _kernel("user_private")
    graph = _graph(["c1"])
    pub = _make_sag("answer", 0.8, ["c1"], scope="public")
    priv = _make_sag("answer", 0.8, ["c1"], scope="user_private")
    ranked = rank_candidates([pub, priv], kernel, graph)
    assert ranked[0][0].id == priv.id


def test_rank_prefers_factual_over_causal() -> None:
    kernel = _kernel()
    graph = _graph(["c1"])
    factual = _make_sag("answer", 0.7, ["c1"])
    causal = _make_sag("answer", 0.7, ["c1"])
    causal.causal_edges = [{"source": "a", "target": "b", "relation": "causes"}]
    ranked = rank_candidates([causal, factual], kernel, graph)
    assert ranked[0][0].id == factual.id
    assert ranked[0][1] > ranked[1][1]


def test_best_candidate_returns_none_below_min() -> None:
    kernel = _kernel()
    graph = _graph([])
    low = _make_sag("answer", 0.1, [])
    result = best_candidate([low], kernel, graph, min_score=0.5)
    assert result is None


def test_rank_orders_mixed_candidates() -> None:
    kernel = _kernel(claim_ids=["c1"])
    graph = _graph(["c1", "c2"])
    ask = _make_sag("ask", 0.9, [])
    answer = _make_sag("answer", 0.7, ["c1"], verified=True)
    abstain = _make_sag("abstain", 0.5, [])
    ranked = rank_candidates([abstain, ask, answer], kernel, graph)
    assert ranked[0][0].id in (answer.id, ask.id)
    assert ranked[-1][0].id == abstain.id
