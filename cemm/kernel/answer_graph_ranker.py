"""Rank candidate SemanticAnswerGraphs by relevance, evidence, confidence, cost.

Implements build-order step 9 (answer graph ranker).
Scoring formula prioritizes determinism before learned components.
"""

from __future__ import annotations

from typing import Any

from ..types.context_kernel import ContextKernel
from ..types.packets import MemoryPacket
from ..types.semantic_answer_graph import SemanticAnswerGraph


def _claim_overlap(selected: list[str], context_claims: list[str]) -> float:
    """Jaccard overlap between selected claims and context claims."""
    if not selected or not context_claims:
        return 0.0
    s = set(selected)
    c = set(context_claims)
    return len(s & c) / len(s | c)


def _permission_match(sag_scope: str | None, kernel_scope: str | None) -> float:
    """1.0 if permission scope is compatible, 0.0 otherwise."""
    sag_scope = sag_scope or "public"
    kernel_scope = kernel_scope or "public"
    if sag_scope == kernel_scope:
        return 1.0
    if sag_scope == "public":
        return 1.0 if kernel_scope == "public" else 0.7
    return 0.0 if kernel_scope == "public" else 0.5


def _cost_factor(confidence: float, has_temporal: bool, has_causal: bool) -> float:
    """Cheapest-first cost: lower is better for equivalent confidence.

    Template/extractive paths cost less than neural paths.
    Temporal edges imply ordering (higher cost). Causal edges imply
    reasoning (highest cost).
    """
    base = 1.0
    if has_temporal:
        base += 0.3
    if has_causal:
        base += 0.5
    return base / (confidence + 0.1)


def rank_candidates(
    candidates: list[SemanticAnswerGraph],
    kernel: ContextKernel,
    graph: SemanticEventGraph,
    memory: MemoryPacket | None = None,
) -> list[tuple[SemanticAnswerGraph, float]]:
    """Rank candidate answer graphs by combined score.

    Returns (candidate, score) sorted descending.
    Score combines:
      - relevance: claim overlap + entity overlap
      - evidence: confidence + verification
      - permission: scope match
      - cost: cheapest-first penalty
    """
    scored: list[tuple[SemanticAnswerGraph, float]] = []
    kernel_claims = kernel.memory.candidate_claim_ids if kernel.memory else []
    claim_ids = list(graph.claim_refs) if graph.claim_refs else []

    for cand in candidates:
        relevance = (
            _claim_overlap(cand.selected_claim_ids, claim_ids) * 0.4
            + _claim_overlap(cand.selected_claim_ids, kernel_claims) * 0.3
        )

        evidence = cand.confidence * 0.5
        if cand.verification.supported:
            evidence += 0.2
        evidence *= cand.verification.confidence if cand.verification.confidence > 0 else 1.0

        permission = _permission_match(cand.permission_scope, kernel.permission.scope.value if kernel.permission else "public")

        cost = _cost_factor(cand.confidence, bool(cand.temporal_edges), bool(cand.causal_edges))
        cost_norm = 1.0 / (cost + 0.1)

        score = relevance * 0.3 + evidence * 0.3 + permission * 0.2 + cost_norm * 0.2
        scored.append((cand, round(score, 4)))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored


def best_candidate(
    candidates: list[SemanticAnswerGraph],
    kernel: ContextKernel,
    graph: SemanticEventGraph,
    memory: MemoryPacket | None = None,
    min_score: float = 0.3,
) -> SemanticAnswerGraph | None:
    """Return the highest-scoring candidate above min_score, or None."""
    ranked = rank_candidates(candidates, kernel, graph, memory)
    for cand, score in ranked:
        if score >= min_score:
            return cand
    return None
