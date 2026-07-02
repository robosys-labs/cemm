from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.retrieval.ranker import Ranker
from cemm.types.claim import Claim, ClaimStatus
from cemm.types.context_kernel import ContextKernel
from cemm.types.permission import Permission
from cemm.types.semantic_event_graph import SemanticEventGraph


def test_graph_claim_ref_boosts_relevance() -> None:
    kernel = ContextKernel(id="ctx", permission=Permission.public())
    kernel.time.now = time.time()
    claim = Claim(
        id="c1",
        subject_entity_id="user",
        predicate="likes",
        object_value="coffee",
        status=ClaimStatus.ACTIVE,
        confidence=0.8,
        trust=0.8,
        salience=0.8,
        observed_at=time.time(),
        permission=Permission.public(),
    )
    graph = SemanticEventGraph(
        id="seg",
        source_signal_ids=["s"],
        context_id="ctx",
        entity_refs=[],
        processes=[],
        states=[],
        claim_refs=["c1"],
        confidence=0.9,
    )
    score_with_graph = Ranker().rank_claims([claim], kernel, graph=graph)[0][1]
    score_without_graph = Ranker().rank_claims([claim], kernel, graph=None)[0][1]
    assert score_with_graph > score_without_graph
