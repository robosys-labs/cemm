# CEMM-ARCH: Refer to cemm_architecture_gap_trace.md and AGENTS.md before modifying.
# Fix 2: Model-driven action selection. Operator models loaded from ModelStore
# and scored via Ranker. Hardcoded routing only fires when no model exceeds threshold.

from __future__ import annotations
import os
import sys
import argparse
import time
import uuid
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
from .operators.call_tool import CallToolOperator
from .operators.base import OperatorContext
from .types.action import Action
from .learning.online import OnlineLearner
from .retrieval.structural import StructuralRetriever, RetrievalQuery
from .retrieval.ranker import Ranker
from .types.context_kernel import ContextKernel
from .types.action import ActionKind
from .types.model import ModelKind, ModelStatus
from .types.permission import Permission
from .types.signal import Signal, SignalKind, SourceType
from .types.self_state import SelfState
from .types.semantic_answer_graph import SemanticAnswerGraph
from .causal.inference import CausalInference
from .causal.simulation import SimulationEngine
from .kernel.recursive_loop import RecursiveLoop
from .kernel.mode_controller import ModeController
from .kernel.decision_router import DecisionRouter
from .types.packets import DecisionPacket, InferencePacket
from .learning.inductor import Inductor

_ACTION_CONFIDENCE_THRESHOLD = 0.5


def seed_registry(registry: Registry) -> None:
    predicates = [
        ("favorite_database", "fav_db", "preferred_db"),
        ("likes", "like", "enjoy", "love", "loves"),
        ("is_a", "isa", "is_a_type_of"),
        ("has", "have", "own", "owns"),
        ("belongs_to", "belongs", "owned_by"),
        ("causes", "leads_to", "results_in"),
        ("precedes", "before", "comes_before"),
        ("located_at", "located_in", "at"),
        ("created_by", "authored_by", "made_by"),
        ("used_for", "used_in", "use"),
        ("part_of", "component_of"),
        ("started_at", "started_on", "began_at"),
        ("favorite", "favourite", "fav"),
        ("prefers", "prefer", "preferred"),
        ("noted", "noted_as"),
    ]
    for i, (canonical, *aliases) in enumerate(predicates):
        registry.register(RegistryEntry(
            model_id=f"pred_{i}",
            canonical_key=canonical,
            kind="predicate",
            aliases=list(aliases),
        ))

    uol_semantics = [
        ("greeting", ["hello", "hi", "hey", "greetings", "howdy", "sup", "morning", "afternoon", "evening"]),
        ("session_exit", ["exit", "quit", "bye", "goodbye", "stop", "done"]),
        ("command_remember", ["remember", "save", "store", "note"]),
        ("command_reflect", ["reflect", "think", "ponder", "contemplate"]),
        ("command_retrieve", ["retrieve", "search", "recall", "find", "lookup"]),
        ("assert_evaluation", ["is", "are", "was", "were"]),
        ("request_clarification", ["what", "who", "where", "when", "why", "how",
                                    "huh", "what do you mean", "how do you mean",
                                    "what in the world", "what the", "come again",
                                    "confused", "don't understand", "don't get it",
                                    "lost", "not following"]),
        ("ask_question", ["?", "which"]),
        ("unknown_intent", []),
        ("state_preference", ["prefer", "like", "favorite", "love"]),
        ("low_competence", ["dumb", "stupid", "fool", "idiot", "useless", "broken"]),
        ("high_quality", ["great", "awesome", "excellent", "amazing", "helpful"]),
        ("temporal_before", ["before", "prior_to"]),
        ("temporal_after", ["after", "then", "next", "following"]),
        ("temporal_during", ["during", "while"]),
        ("temporal_overlaps", ["overlaps", "concurrent"]),
        ("temporal_starts", ["starts", "begins"]),
        ("temporal_finishes", ["finishes", "ends", "completes"]),
        ("causal_causes", ["causes", "cause", "caused"]),
        ("causal_caused_by", ["caused_by", "due_to"]),
        ("causal_leads_to", ["leads_to", "leads", "results_in", "results"]),
        ("causal_because", ["because", "since"]),
        ("causal_so", ["so", "therefore"]),
        ("uncertainty_marker", ["might", "may", "could", "possibly", "probably", "likely",
                                 "unclear", "uncertain", "not sure", "based on available information",
                                 "it appears", "it seems", "suggests"]),
        ("acknowledgment", ["ok", "okay", "sure", "right", "yeah", "yes", "yup", "got it",
                            "understood", "makes sense", "i see", "gotcha", "cool", "nice"]),
        ("discourse_marker", ["oh", "well", "so", "hmm", "anyway", "actually", "btw", "honestly"]),
    ]
    for i, (canonical, aliases) in enumerate(uol_semantics):
        registry.register(RegistryEntry(
            model_id=f"uol_{i}",
            canonical_key=canonical,
            kind="uol_semantic",
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
        ("call_tool", CallToolOperator(), ["tool_id"]),
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
    _self_ref_patterns = (
        "who are you", "what are you", "what do you know", "what do you like",
        "what do you think", "what do you prefer", "what do you want", "what do you need",
        "tell me about yourself", "describe yourself", "introduce yourself",
        "who made you", "who created you", "what can you do", "what is your name",
        "your name", "your capabilities", "about yourself",
    )
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
    context_inference = pipeline_result.context_inference

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
        if memory_packet and selected_claim_ids:
            memory_packet.selected_claim_ids = list(selected_claim_ids)
            memory_packet.selected_model_ids = list(selected_model_ids)

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

    inference_packet = pipeline_result.inference_packet or InferencePacket()
    sim_result = None
    graph = pipeline_result.semantic_event_graph
    # Pipeline already ran causal inference; only run simulation if causal edges exist
    if graph and graph.causal_edges:
        sim_engine = SimulationEngine(store)
        sim_result = sim_engine.simulate(text, kernel)
    predictions = inference_packet.predictions

    if text.lower() in ("exit", "quit", "bye"):
        return "Goodbye!"

    # DecisionRouter is the sole, authoritative decision mechanism.
    # No hardcoded fallbacks or confidence threshold bypass.
    kind: ActionKind | None = None
    params: dict = {}
    decision: DecisionPacket | None = pipeline_result.decision_packet
    if decision is None and pipeline_result.semantic_event_graph:
        decision_router = DecisionRouter()
        decision = decision_router.run(
            graph=pipeline_result.semantic_event_graph,
            kernel=kernel,
            grounded_graph=grounded_graph,
            memory_packet=memory_packet,
            inference_packet=inference_packet if inference_packet.predictions else None,
            input_text=text,
            observation_semantics=input_signal.observation_semantics,
            context_inference=context_inference,
        )

    kind: ActionKind | None = None
    params: dict = {}
    ap: ActionPlan | None = None
    if decision:
        _action_kind_map = {
            "answer": ActionKind.ANSWER,
            "ask": ActionKind.ASK,
            "remember": ActionKind.REMEMBER,
            "update": ActionKind.UPDATE_CLAIM,
            "act": ActionKind.CALL_TOOL,
            "abstain": ActionKind.ABSTAIN,
            "reflect": ActionKind.REFLECT,
            "retrieve": ActionKind.RETRIEVE,
            "synthesize": ActionKind.SYNTHESIZE,
            "simulate": ActionKind.SIMULATE,
            "create_model_candidate": ActionKind.CREATE_MODEL_CANDIDATE,
        }
        kind = _action_kind_map.get(decision.action_kind)
        ap = decision.action_plan
        if kind == ActionKind.ASK:
            params = {"question": "Could you elaborate?"}
        elif kind == ActionKind.ANSWER:
            # For conversational intents (greeting/acknowledgment), don't pass claims
            # — the response is a template, not evidence-backed
            reason_lower = decision.reason.lower()
            is_conversational = "greeting" in reason_lower or "acknowledgment" in reason_lower
            answer_claim_ids = [] if is_conversational else (list(ap.selected_claim_ids) if ap else selected_claim_ids)
            params = {
                "answer_text": "",
                "selected_claim_ids": answer_claim_ids,
                "seg_confidence": pipeline_result.semantic_event_graph.confidence if pipeline_result.semantic_event_graph else 0.0,
                "decision_reason": decision.reason,
            }
            if sim_result is not None:
                params["simulation_claims"] = sim_result.predicted_claims
                params["simulation_confidence"] = sim_result.confidence
        elif kind == ActionKind.ABSTAIN:
            params = {"reason": decision.reason}
        elif kind == ActionKind.REMEMBER:
            seg = pipeline_result.semantic_event_graph
            if seg and seg.claim_candidates:
                cand = seg.claim_candidates[0]
                params = {
                    "subject_entity_id": "user",
                    "predicate": cand.get("predicate", "noted"),
                    "object_value": cand.get("object", ""),
                    "domain": "general",
                }
            else:
                stripped = text.strip()
                cmd_entry = registry.get_uol_semantic("command_remember")
                cmd_aliases = [cmd_entry.canonical_key] + cmd_entry.aliases if cmd_entry else ["remember", "save", "store", "note"]
                params = {
                    "subject_entity_id": "user",
                    "predicate": "noted",
                    "object_value": stripped,
                    "domain": "general",
                }
                for alias in cmd_aliases:
                    if stripped.lower().startswith(alias + " "):
                        rest = stripped[len(alias) + 1:]
                        parts = rest.split(maxsplit=1)
                        params = {
                            "subject_entity_id": "user",
                            "predicate": parts[0] if parts else "noted",
                            "object_value": parts[1] if len(parts) > 1 else "",
                            "domain": "general",
                        }
                        break
        elif kind == ActionKind.REFLECT:
            params = {}
            if sim_result is not None:
                params["simulation_claims"] = sim_result.predicted_claims
        elif kind == ActionKind.RETRIEVE:
            params = {}

    # Safety net: if no SEG was produced, abstain
    if kind is None:
        kind = ActionKind.ABSTAIN
        params = {"reason": "No semantic event graph produced"}

    ctx = OperatorContext(
        kernel=kernel,
        input_signal=input_signal,
        store=store,
        registry=registry,
        selected_claim_ids=selected_claim_ids,
        selected_model_ids=selected_model_ids,
        grounded_graph_id=grounded_graph.id if grounded_graph else None,
        memory_packet_id=memory_packet.id if memory_packet else None,
        inference_packet_id=inference_packet.id if inference_packet else None,
        semantic_event_graph_id=pipeline_result.semantic_event_graph.id if pipeline_result.semantic_event_graph else None,
        decision_packet_id=decision.id if decision else None,
        params=params,
    )
    op_result = op_registry.execute(kind, ctx)
    output = op_result.output_text

    # Invariant checks after operator execution
    from .kernel.invariant_guard import InvariantGuard
    guard = InvariantGuard()
    guard.reset()
    if op_result.trace:
        synthetic_action = Action(
            id=op_result.trace.action_id or uuid.uuid4().hex[:16],
            kind=kind,
            operator_model_id=op_result.trace.operator_model_id or "",
            trace=op_result.trace,
        )
        guard.check_action_has_trace(synthetic_action)
        guard.check_memory_mutation_has_trace(synthetic_action)
        guard.check_synthesis_verification(synthetic_action, op_result.trace)
        if inference_packet and inference_packet.predictions:
            guard.check_causal_chain_confidence(inference_packet.predictions)
    guard.check_response_has_input_signal(input_signal)
    if mode_change_action:
        guard.check_self_mutation_has_trace(mode_change_action)
        guard.check_self_mode_change_has_trace(
            kernel.self_view.mode, kernel.self_view.mode, mode_change_action
        )
    for claim_id in ctx.selected_claim_ids:
        claim = store.claims.get(claim_id)
        if claim:
            guard.check_private_claim_used_with_permission(claim, kernel)
            guard.check_disputed_not_presented_certain(claim)
            guard.check_stale_claim_not_used(claim, kernel)
    if guard.errors:
        for err in guard.errors:
            print(f"[INVARIANT] {err}", file=sys.stderr)

    if op_result.success:
        online_learner.record_outcome(
            source_id=ctx.input_signal.source_id,
            domain="operator_execution",
            success=True,
        )
    else:
        online_learner.record_outcome(
            source_id=ctx.input_signal.source_id,
            domain="operator_execution",
            success=False,
        )

    if not output:
        from .synthesis.realizer import RealizationPipeline as _RP
        fallback_sag = SemanticAnswerGraph(
            id=uuid.uuid4().hex[:16],
            intent="abstain",
            source_signal_ids=[input_signal.id],
            context_id=kernel.id,
            confidence=max(0.5, 1.0 - kernel.self_view.uncertainty),
        )
        fallback_pipeline = _RP()
        fallback_result = fallback_pipeline.run(fallback_sag, kernel, store, registry)
        output = fallback_result.output

    # Re-entry: append actionable signal summaries to output
    for sig in actionable_signals:
        if sig.salience >= 0.7 and sig.kind == SignalKind.REFLECTION:
            output += f"\n[{sig.kind.value}] {sig.content}"

    # Export training data if CEMM_EXPORT_PATH is set
    _export_path = os.environ.get("CEMM_EXPORT_PATH")
    if _export_path and op_result.trace:
        from .kernel.training_export import serialize_turn, write_turn_to_jsonl
        sag_for_export = op_result.semantic_answer_graph
        if sag_for_export is None and decision is not None:
            sag_for_export = decision.semantic_answer_graph
        turn_data = serialize_turn(
            input_text=text,
            output_text=output,
            kernel=kernel,
            input_signal=input_signal,
            trace=op_result.trace,
            semantic_event_graph=pipeline_result.semantic_event_graph,
            semantic_answer_graph=sag_for_export,
            grounded_graph=grounded_graph,
            memory_packet=memory_packet,
            inference_packet=inference_packet,
            decision_packet=decision if decision and decision.confidence > 0 else None,
        )
        write_turn_to_jsonl(_export_path, turn_data)

    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="CEMM — Contextual Event Memory Model")
    parser.add_argument("--db", default=":memory:", help="SQLite database path")
    parser.add_argument("--eval", help="Single query to evaluate and exit")
    parser.add_argument("--train", nargs="?", const="cemm_training.sqlite3",
                        help="Run training: path to SQLite DB (default: cemm_training.sqlite3)")
    parser.add_argument("--workers", type=int, default=2, help="Training worker count")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run mode for training")
    parser.add_argument("--once", help="Handle one user turn")
    parser.add_argument("--chat", action="store_true", help="Interactive chat mode")
    args = parser.parse_args()

    store = Store(args.db)
    registry = Registry()
    op_registry = OperatorRegistry()
    pipeline = Pipeline(store, registry)
    online_learner = OnlineLearner(store.source_trust, store.self_store, store.claims, store.models)
    inductor = Inductor(store, registry=registry)
    recursive_loop = RecursiveLoop(pipeline, store, online_learner, inductor)

    seed_registry(registry)
    seed_self_state(store)

    for op_class in [
        AnswerOperator, AskOperator, RememberOperator, UpdateClaimOperator,
        CreateModelOperator, SynthesizeOperator, SimulateOperator,
        RetrieveOperator, ReflectOperator, CallToolOperator, AbstainOperator,
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
