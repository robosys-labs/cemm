from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from cemm.__main__ import seed_registry, seed_self_state
from cemm.kernel.pipeline import Pipeline
from cemm.kernel.recursive_loop import RecursiveLoop
from cemm.learning.inductor import Inductor
from cemm.learning.online import OnlineLearner
from cemm.operators.registry import OperatorRegistry
from cemm.operators.abstain import AbstainOperator
from cemm.operators.answer import AnswerOperator
from cemm.operators.ask import AskOperator
from cemm.operators.remember import RememberOperator
from cemm.operators.retrieve_op import RetrieveOperator
from cemm.registry import Registry
from cemm.retrieval.structural import StructuralRetriever
from cemm.retrieval.ranker import Ranker
from cemm.store.store import Store
from cemm.types.action import ActionKind


def test_self_capability_query_selects_self_claims() -> None:
    store = Store(":memory:")
    registry = Registry()
    seed_registry(registry)
    seed_self_state(store)

    op_registry = OperatorRegistry()
    for op in [AnswerOperator(), AskOperator(), RememberOperator(), RetrieveOperator(), AbstainOperator()]:
        op_registry.register(op)

    pipeline = Pipeline(store, registry)
    learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    loop = RecursiveLoop(pipeline, store, learner, Inductor(store, registry=registry))

    result_tuple = loop.run_once("what can you do?", context_id="ctx_self")
    kernel = result_tuple[0]
    assert kernel is not None

    # Ensure self entity is in working memory
    retriever = StructuralRetriever(store)
    retrieved = retriever.retrieve_for_kernel(kernel)
    ranked = Ranker().rank_claims(retrieved.claims, kernel)
    selected_ids = [c.id for c, _ in ranked if c.subject_entity_id == "self_main"]
    assert selected_ids, "expected self claims to be selected for a self query"

    # Build a minimal context and invoke AnswerOperator
    pipeline_result = loop._last_result
    result_signal = [s for s in pipeline_result.signals if s.kind == "input"][0]
    ctx = __import__("cemm.operators.base", fromlist=["OperatorContext"]).OperatorContext(
        kernel=kernel,
        input_signal=result_signal,
        store=store,
        registry=registry,
        selected_claim_ids=selected_ids,
        params={"answer_text": "", "selected_claim_ids": selected_ids, "seg_confidence": pipeline_result.semantic_event_graph.confidence if pipeline_result.semantic_event_graph else 0.5},
    )
    answer = AnswerOperator().execute(ctx)
    assert answer.success
    assert answer.semantic_answer_graph is not None
    assert answer.semantic_answer_graph.selected_claim_ids
    assert "self_main" in answer.output_text.lower() or "cemm" in answer.output_text.lower()
