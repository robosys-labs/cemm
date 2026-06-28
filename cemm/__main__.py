from __future__ import annotations
import sys
import argparse
import time
from .store.store import Store
from .registry import Registry, RegistryEntry
from .kernel.pipeline import Pipeline, PipelineResult
from .operators.registry import OperatorRegistry
from .operators.answer import AnswerOperator
from .operators.ask import AskOperator
from .operators.remember import RememberOperator
from .operators.update_claim import UpdateClaimOperator
from .operators.create_model import CreateModelOperator
from .operators.synthesize import SynthesizeOperator
from .operators.simulate import SimulateOperator
from .operators.retrieve_op import RetrieveOperator
from .operators.reflect import ReflectOperator
from .operators.abstain import AbstainOperator
from .operators.base import OperatorContext
from .learning.online import OnlineLearner
from .retrieval.structural import StructuralRetriever, RetrievalQuery
from .retrieval.ranker import Ranker
from .types.context_kernel import ContextKernel
from .types.action import ActionKind
from .types.permission import Permission
from .types.signal import Signal, SignalKind, SourceType
from .types.self_state import SelfState
from .causal.inference import CausalInference
from .causal.simulation import SimulationEngine
from .synthesis.router import SynthesisRouter


def seed_registry(registry: Registry) -> None:
    predicates = [
        ("favorite_database", "fav_db", "preferred_db", "likes"),
        ("is_a", "isa", "is_a_type_of"),
        ("belongs_to", "belongs", "owned_by"),
        ("causes", "leads_to", "results_in"),
        ("precedes", "before", "comes_before"),
        ("located_at", "located_in", "at"),
        ("created_by", "authored_by", "made_by"),
        ("used_for", "used_in"),
        ("part_of", "component_of"),
        ("started_at", "started_on", "began_at"),
    ]
    for i, (canonical, *aliases) in enumerate(predicates):
        registry.register(RegistryEntry(
            model_id=f"pred_{i}",
            canonical_key=canonical,
            kind="predicate",
            aliases=list(aliases),
        ))

    operators = [
        ("answer", AnswerOperator(), ["answer_text"]),
        ("ask", AskOperator(), ["question"]),
        ("remember", RememberOperator(), ["subject_entity_id", "predicate"]),
        ("update_claim", UpdateClaimOperator(), ["claim_id", "status"]),
        ("create_model", CreateModelOperator(), ["name", "kind"]),
        ("synthesize", SynthesizeOperator(), ["strategy"]),
        ("simulate", SimulateOperator(), ["action_or_event"]),
        ("retrieve", RetrieveOperator(), []),
        ("reflect", ReflectOperator(), []),
        ("abstain", AbstainOperator(), ["reason"]),
    ]
    for key, op, _ in operators:
        registry.register(RegistryEntry(
            model_id=f"op_{key}",
            canonical_key=key,
            kind="operator",
            description=f"{key} operator",
        ))


def seed_self_state(store: Store) -> None:
    existing = store.self_store.latest()
    if existing is None:
        state = SelfState(
            id="self_main",
            name="cemm",
            created_at=time.time(),
            updated_at=time.time(),
        )
        store.self_store.put(state)


def process_input(
    text: str,
    store: Store,
    registry: Registry,
    op_registry: OperatorRegistry,
    pipeline: Pipeline,
    online_learner: OnlineLearner,
    context_id: str,
    turn_count: list[int],
) -> str:
    turn_count[0] += 1
    result = pipeline.run(text, context_id=context_id)
    kernel = result.kernel
    if kernel is None:
        return "Error: no kernel built"

    retriever = StructuralRetriever(store)
    ranker = Ranker()
    retrieval_result = retriever.retrieve_for_kernel(kernel)
    ranked_claims = ranker.rank_claims(retrieval_result.claims, kernel)
    max_ranked = kernel.budget.max_ranked
    selected_claim_ids = [c.id for c, _ in ranked_claims[:max_ranked]]

    causal = CausalInference(store)
    predictions = causal.predict(text, selected_claim_ids, kernel)

    sim_engine = SimulationEngine(store)
    sim_result = sim_engine.simulate(text, kernel)

    if text.lower() in ("exit", "quit", "bye"):
        return "Goodbye!"

    if text.lower().startswith("remember ") or text.lower().startswith("save "):
        kind = ActionKind.REMEMBER
        parts = text.split(maxsplit=2)
        params = {
            "subject_entity_id": "user",
            "predicate": parts[1] if len(parts) > 1 else "noted",
            "object_value": parts[2] if len(parts) > 2 else "",
            "domain": "general",
        }
    elif "?" in text or text.lower().startswith("what") or text.lower().startswith("who"):
        kind = ActionKind.ANSWER
        params = {"answer_text": "", "selected_claim_ids": selected_claim_ids}
    elif len(text.strip()) <= 3:
        kind = ActionKind.ASK
        params = {"question": "Could you elaborate?"}
    else:
        kind = ActionKind.ANSWER
        params = {"answer_text": text}

    ctx = OperatorContext(
        kernel=kernel,
        input_signal=result.signals[0],
        store=store,
        registry=registry,
        selected_claim_ids=selected_claim_ids,
        selected_model_ids=[m.id for m in retrieval_result.models],
        params=params,
    )
    op_result = op_registry.execute(kind, ctx)
    output = op_result.output_text

    if op_result.success:
        online_learner.record_outcome(
            source_id=ctx.input_signal.source_id,
            domain="operator_execution",
            success=True,
        )

    if kind == ActionKind.ANSWER and ctx.selected_claim_ids:
        for claim_id in ctx.selected_claim_ids:
            online_learner.update_claim_confidence(claim_id, feedback_correct=True)

    if not output or op_result.success is False:
        synthesis_router = SynthesisRouter()
        syn = synthesis_router.route("template", kernel, store, registry, {
            "template_key": "greeting",
        })
        output = syn.output

    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="CEMM — Contextual Event Memory Model")
    parser.add_argument("--db", default=":memory:", help="SQLite database path")
    parser.add_argument("--eval", help="Single query to evaluate and exit")
    args = parser.parse_args()

    store = Store(args.db)
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims)

    seed_registry(registry)
    seed_self_state(store)

    for op_class in [
        AnswerOperator, AskOperator, RememberOperator, UpdateClaimOperator,
        CreateModelOperator, SynthesizeOperator, SimulateOperator,
        RetrieveOperator, ReflectOperator, AbstainOperator,
    ]:
        op_registry.register(op_class())

    context_id = f"session_{int(time.time())}"
    turn_count = [0]

    if args.eval:
        output = process_input(args.eval, store, registry, op_registry, pipeline, online_learner, context_id, turn_count)
        print(output)
        return

    print("CEMM — Contextual Event Memory Model")
    print("Type 'exit' to quit.\n")
    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not text:
            continue
        output = process_input(text, store, registry, op_registry, pipeline, online_learner, context_id, turn_count)
        print(output)


if __name__ == "__main__":
    main()
