# CEMM-ARCH: Refer to cemm_architecture_gap_trace.md and AGENTS.md before modifying.
# Fix 2: Model-driven action selection. Operator models loaded from ModelStore
# and scored via Ranker. Hardcoded routing only fires when no model exceeds threshold.

from __future__ import annotations
import os
import sys
import argparse
import time
from .store.store import Store
from .store.artifact_store import ArtifactStore
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
from .types.model import ModelKind, ModelStatus
from .types.permission import Permission
from .types.signal import Signal, SignalKind, SourceType
from .types.self_state import SelfState
from .causal.inference import CausalInference
from .causal.simulation import SimulationEngine
from .synthesis.router import SynthesisRouter
from .kernel.recursive_loop import RecursiveLoop
from .kernel.mode_controller import ModeController
from .kernel.decision_router import DecisionRouter
from .types.packets import DecisionPacket, InferencePacket
from .learning.inductor import Inductor

_ACTION_CONFIDENCE_THRESHOLD = 0.5


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


def seed_self_state(store: Store, knowledge_path: str | None = None) -> None:
    existing_state = store.self_store.latest()
    if existing_state is None:
        state = SelfState(
            id="self_main",
            name="cemm",
            created_at=time.time(),
            updated_at=time.time(),
        )
        store.self_store.put(state)

    # Seed self-knowledge entity + claims from JSON config
    import json, uuid
    path = knowledge_path or os.path.join(os.path.dirname(__file__), "self_knowledge.json")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        config = json.load(f)

    ent_cfg = config.get("entity", {})
    existing_entity = store.entities.get(ent_cfg["id"]) if ent_cfg.get("id") else None
    if existing_entity is None and ent_cfg:
        from .types.entity import Entity as _Entity, EntityType as _ET
        entity = _Entity(
            id=ent_cfg["id"],
            type=_ET(ent_cfg.get("type", "system")),
            name=ent_cfg.get("name", "CEMM"),
            aliases=ent_cfg.get("aliases", []),
            confidence=ent_cfg.get("confidence", 0.9),
            created_from_signal_id="seed",
            created_at=time.time(),
            updated_at=time.time(),
        )
        store.entities.put(entity)

    for claim_cfg in config.get("claims", []):
        from .types.claim import Claim as _Claim, ClaimStatus as _CS
        from .types.permission import Permission as _Perm
        existing = store.claims.find_by_subject(
            claim_cfg["subject"], claim_cfg["predicate"], limit=10,
        )
        already = any(
            c.object_value == claim_cfg.get("object_value")
            for c in existing
        )
        if not already:
            claim = _Claim(
                id=uuid.uuid4().hex[:16],
                subject_entity_id=claim_cfg["subject"],
                predicate=claim_cfg["predicate"],
                object_value=claim_cfg.get("object_value"),
                object_entity_id=claim_cfg.get("object_entity_id"),
                domain=claim_cfg.get("domain", "self_knowledge"),
                source_id="seed",
                confidence=claim_cfg.get("confidence", 0.95),
                trust=claim_cfg.get("trust", 0.95),
                salience=0.8,
                status=_CS.ACTIVE,
                observed_at=time.time(),
                updated_at=time.time(),
                permission=_Perm.public(),
            )
            store.claims.put(claim)


def process_input(
    text: str,
    store: Store,
    registry: Registry,
    op_registry: OperatorRegistry,
    pipeline: Pipeline,
    online_learner: OnlineLearner,
    recursive_loop: RecursiveLoop,
    context_id: str,
    turn_count: list[int],
) -> str:
    turn_count[0] += 1
    # Use RecursiveLoop for model-driven pipeline + online learning + induction
    result_tuple = recursive_loop.run_once(text, context_id=context_id)
    if len(result_tuple) == 3:
        kernel, internal_signals, actionable_signals = result_tuple
    else:
        kernel, internal_signals = result_tuple
        actionable_signals = []
    if kernel is None:
        return "Error: no kernel built"

    pipeline_result = recursive_loop._last_result
    input_signal = pipeline_result.signals[0] if pipeline_result and pipeline_result.signals else Signal(
        id=f"input_{context_id}_{turn_count[0]}",
        kind=SignalKind.INPUT,
        source_id="user",
        source_type=SourceType.USER,
        content=text,
        observed_at=time.time(),
        context_id=context_id,
        salience=1.0,
        trust=1.0,
        permission=kernel.permission,
    )

    # Self-referential detection: if input refers to the system, inject
    # self entity into kernel entity lists so self-knowledge claims are retrieved.
    _self_ref_patterns = ("who are you", "what are you", "your name", "tell me about yourself",
                          "who are", "what is your", "describe yourself", "introduce yourself",
                          "who made you", "who created you", "what can you do",
                          "you", "yourself", "ceMM", "cemm")
    text_lower = text.strip().lower()
    if any(pattern in text_lower for pattern in _self_ref_patterns):
        self_entity = store.entities.get("self_main")
        if self_entity:
            if self_entity.id not in kernel.memory.working_entity_ids:
                kernel.memory.working_entity_ids.append(self_entity.id)
            if self_entity.id not in kernel.world.active_entity_ids:
                kernel.world.active_entity_ids.append(self_entity.id)

    # Use pipeline-provided ranked claims if available
    selected_claim_ids = pipeline_result.ranked_claim_ids
    selected_model_ids = pipeline_result.ranked_model_ids
    grounded_graph = pipeline_result.grounded_graph
    memory_packet = pipeline_result.memory_packet

    # Fallback: manual retrieval if pipeline didn't populate
    fallback_retriever = StructuralRetriever(store)
    fallback_ranker = Ranker()
    if not selected_claim_ids:
        graph = pipeline_result.semantic_event_graph
        retrieval_result = fallback_retriever.retrieve_for_kernel(kernel)
        if graph:
            graph_result = fallback_retriever.retrieve_for_graph(graph, kernel)
            seen_ids = {c.id for c in retrieval_result.claims}
            for c in graph_result.claims:
                if c.id not in seen_ids:
                    retrieval_result.claims.append(c)
                    seen_ids.add(c.id)
        ranked_claims = fallback_ranker.rank_claims(retrieval_result.claims, kernel, graph=graph)
        selected_claim_ids = [c.id for c, _ in ranked_claims[:kernel.budget.max_ranked]]
        selected_model_ids = [m.id for m in retrieval_result.models]

    # Mode Controller: evaluate self state and transition if needed
    mode_controller = ModeController()
    new_mode = mode_controller.evaluate(kernel.self_view)
    mode_change_action = None
    if new_mode is not None:
        old_mode = kernel.self_view.mode
        kernel.self_view.mode = new_mode
        mode_change_action = ModeController.create_reflect_action(old_mode, new_mode, kernel.id)
        if mode_change_action:
            mode_signal = Signal(
                id=f"mode_{old_mode}_to_{new_mode}_{int(time.time())}",
                kind=SignalKind.REFLECTION,
                source_id="mode_controller",
                source_type=SourceType.SYSTEM,
                content=f"Mode changed: {old_mode} -> {new_mode}",
                observed_at=time.time(),
                context_id=kernel.id,
                salience=0.4,
                trust=1.0,
                permission=kernel.permission,
            )
            actionable_signals.append(mode_signal)

    inference_packet = InferencePacket()
    sim_result = None
    graph = pipeline_result.semantic_event_graph
    if graph and (graph.causal_edges or kernel.goal.required_slots):
        causal = CausalInference(store)
        inference_packet = causal.predict(text, selected_claim_ids, kernel)
        if graph.causal_edges:
            sim_engine = SimulationEngine(store)
            sim_result = sim_engine.simulate(text, kernel)
    predictions = inference_packet.predictions

    if text.lower() in ("exit", "quit", "bye"):
        return "Goodbye!"

    # Phase 0: Graph-grounded DecisionRouter (primary decision mechanism)
    kind: ActionKind | None = None
    params: dict = {}
    if pipeline_result.semantic_event_graph:
        decision_router = DecisionRouter(artifact_store=ArtifactStore(store))
        decision = decision_router.run(
            graph=pipeline_result.semantic_event_graph,
            kernel=kernel,
            grounded_graph=grounded_graph,
            memory_packet=memory_packet,
            inference_packet=inference_packet if inference_packet.predictions else None,
        )
        _action_kind_map = {
            "answer": ActionKind.ANSWER,
            "ask": ActionKind.ASK,
            "remember": ActionKind.REMEMBER,
            "update": ActionKind.UPDATE_CLAIM,
            "act": ActionKind.CALL_TOOL,
            "abstain": ActionKind.ABSTAIN,
        }
        if decision.confidence >= _ACTION_CONFIDENCE_THRESHOLD and decision.action_kind != "abstain":
            kind = _action_kind_map.get(decision.action_kind)
            ap = decision.action_plan
            if kind == ActionKind.ASK:
                params = {"question": "Could you elaborate?"}
            elif kind == ActionKind.ANSWER:
                params = {
                    "answer_text": "",
                    "selected_claim_ids": list(ap.selected_claim_ids) if ap else selected_claim_ids,
                }

    # Phase 1: Induction-driven routing (fallback when Phase 0 abstains)
    # Uses candidate CAUSAL_RULE models from structural learning to inform decisions
    if kind is None:
        causal_candidates = store.models.find_by_kind(
            ModelKind.CAUSAL_RULE.value, ModelStatus.CANDIDATE.value,
        )
        if causal_candidates:
            scored = fallback_ranker.rank_models(causal_candidates, kernel)
            for model, score in scored:
                if score >= _ACTION_CONFIDENCE_THRESHOLD / 2:
                    kind = ActionKind.ASK
                    params = {
                        "question": "I need more information based on observed patterns.",
                        "causal_model_id": model.id,
                        "causal_confidence": score,
                    }
                    break

    # Phase 2: Hardcoded routing for explicit commands (fallback when Phase 0/1 abstains)
    if kind is None:
        if text.lower().startswith("remember ") or text.lower().startswith("save "):
            kind = ActionKind.REMEMBER
            parts = text.split(maxsplit=2)
            params = {
                "subject_entity_id": "user",
                "predicate": parts[1] if len(parts) > 1 else "noted",
                "object_value": parts[2] if len(parts) > 2 else "",
                "domain": "general",
            }
        elif text.lower().startswith("reflect") or text.lower().startswith("think"):
            kind = ActionKind.REFLECT
            params = {}
            if sim_result is not None:
                params["simulation_claims"] = sim_result.predicted_claims
        elif len(text.strip()) <= 3:
            kind = ActionKind.ASK
            params = {"question": "Could you elaborate?"}
        elif "?" in text or text.lower().startswith("what") or text.lower().startswith("who"):
            kind = ActionKind.ANSWER
            params = {"answer_text": "", "selected_claim_ids": selected_claim_ids}
            if sim_result is not None:
                params["simulation_claims"] = sim_result.predicted_claims
                params["simulation_confidence"] = sim_result.confidence

    # Phase 2: Model-driven routing for everything else
    # If a trained operator model has sufficient confidence, use it.
    # Otherwise fall through to the hardcoded default.
    if kind is None:
        operator_models = store.models.find_by_kind(
            ModelKind.OPERATOR.value, ModelStatus.ACTIVE.value,
        )
        scored_operators = fallback_ranker.rank_models(operator_models, kernel)
        for model, score in scored_operators:
            if score < _ACTION_CONFIDENCE_THRESHOLD:
                break
            if model.registry_key:
                action_kind_map = {
                    "answer": ActionKind.ANSWER,
                    "ask": ActionKind.ASK,
                    "remember": ActionKind.REMEMBER,
                    "abstain": ActionKind.ABSTAIN,
                    "reflect": ActionKind.REFLECT,
                    "synthesize": ActionKind.SYNTHESIZE,
                    "retrieve": ActionKind.RETRIEVE,
                }
                mapped = action_kind_map.get(model.registry_key)
                if mapped:
                    kind = mapped
                    params = {
                        "answer_text": "",
                        "selected_claim_ids": selected_claim_ids,
                        "operator_model_id": model.id,
                        "operator_confidence": score,
                    }
                    if sim_result is not None:
                        params["simulation_claims"] = sim_result.predicted_claims
                        params["simulation_confidence"] = sim_result.confidence
                    break

    # Phase 3: Hardcoded default if nothing matched
    if kind is None:
        kind = ActionKind.ANSWER
        params = {"answer_text": "", "selected_claim_ids": selected_claim_ids}
        if sim_result is not None:
            params["simulation_claims"] = sim_result.predicted_claims
            params["simulation_confidence"] = sim_result.confidence

    ctx = OperatorContext(
        kernel=kernel,
        input_signal=input_signal,
        store=store,
        registry=registry,
        selected_claim_ids=selected_claim_ids,
        selected_model_ids=selected_model_ids,
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

    if not output:
        synthesis_router = SynthesisRouter()
        syn = synthesis_router.realize(kernel, store, registry, {
            "template_key": "greeting",
        })
        output = syn.output

    # Re-entry: append actionable signal summaries to output
    for sig in actionable_signals:
        if sig.salience >= 0.7 and sig.kind == SignalKind.REFLECTION:
            output += f"\n[{sig.kind.value}] {sig.content}"

    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="CEMM — Contextual Event Memory Model")
    parser.add_argument("--db", default=":memory:", help="SQLite database path")
    parser.add_argument("--eval", help="Single query to evaluate and exit")
    parser.add_argument("--train", nargs="?", const="cemm_training.sqlite3",
                        help="Run training: path to SQLite DB (default: cemm_training.sqlite3)")
    parser.add_argument("--workers", type=int, default=2, help="Training worker count")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run mode for training")
    parser.add_argument("--once", help="Handle one user turn via runtime router")
    parser.add_argument("--chat", action="store_true", help="Interactive chat via runtime router")
    parser.add_argument("--legacy", action="store_true",
                        help="Use legacy cemm_runtime_router instead of full architecture")
    args = parser.parse_args()

    # Legacy path: delegate to simplified router (deprecated, kept for backwards compat)
    if args.legacy:
        if args.once:
            from .cemm_runtime_router import main as router_main
            router_main(["once", args.once])
            return
        if args.chat:
            from .cemm_runtime_router import main as router_main
            router_main(["chat"])
            return

    store = Store(args.db)
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)

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

    # --once: single turn through full architecture
    if args.once:
        output = process_input(args.once, store, registry, op_registry, pipeline,
                               online_learner, recursive_loop, context_id, turn_count)
        print(output)
        return

    # --chat: interactive loop through full architecture
    if args.chat:
        print("CEMM — Contextual Event Memory Model (full architecture)")
        print("Type 'exit' to quit.\n")
        while True:
            try:
                text_in = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not text_in:
                continue
            output = process_input(text_in, store, registry, op_registry, pipeline,
                                   online_learner, recursive_loop, context_id, turn_count)
            print(output)
        return

    if args.train:
        if not os.path.exists(args.train):
            print(f"No training DB at {args.train}. Create one via:")
            print(f"  python -m cemm.cemm_trainer ingest examples.jsonl")
            print(f"  python -m cemm.cemm_trainer run --workers 4")
            return
        from . import cemm_trainer as _ct
        _cargs = ["run", "--db", args.train, "--workers",
                  str(args.workers), "--poll-s", "2.0"]
        if args.dry_run:
            _cargs.append("--dry-run")
        raise SystemExit(_ct.main(_cargs))

    if args.eval:
        output = process_input(args.eval, store, registry, op_registry, pipeline,
                               online_learner, recursive_loop, context_id, turn_count)
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
        output = process_input(text, store, registry, op_registry, pipeline,
                               online_learner, recursive_loop, context_id, turn_count)
        print(output)


if __name__ == "__main__":
    main()
