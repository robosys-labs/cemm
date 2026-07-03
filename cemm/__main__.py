# CEMM-ARCH: Refer to cemm_architecture_gap_trace.md and AGENTS.md before modifying.
# Fix 2: Model-driven action selection. Operator models loaded from ModelStore
# and scored via Ranker. Hardcoded routing only fires when no model exceeds threshold.

from __future__ import annotations
import os
import sys
import argparse
import json
import time
import uuid
from pathlib import Path
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
from .operators.learn import LearnOperator
from .operators.base import OperatorContext
from .types.action import Action, ActionStatus
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


def _load_seed_data(name: str) -> list[dict[str, Any]]:
    """Load seed entries (predicates, UOL semantics, etc.) from cemm/data/*.json."""
    data_dir = Path(__file__).parent / "data"
    path = data_dir / f"{name}.json"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(name, [])


def seed_registry(registry: Registry) -> None:
    predicates = _load_seed_data("predicates")
    for i, entry in enumerate(predicates):
        canonical = entry["canonical_key"]
        aliases = entry.get("aliases", [])
        registry.register(RegistryEntry(
            model_id=f"pred_{i}",
            canonical_key=canonical,
            kind="predicate",
            aliases=list(aliases),
        ))

    uol_semantics = _load_seed_data("uol_semantics")
    for i, entry in enumerate(uol_semantics):
        canonical = entry["canonical_key"]
        aliases = entry.get("aliases", [])
        registry.register(RegistryEntry(
            model_id=f"uol_{i}",
            canonical_key=canonical,
            kind="uol_semantic",
            aliases=list(aliases),
        ))

    # Operator registration is canonical (not language-specific). The metadata
    # is loaded from cemm/data/operators.json; the implementing classes are
    # imported here so import paths remain in code while the canonical list is
    # data-driven.
    for entry in _load_seed_data("operators"):
        key = entry["canonical_key"]
        registry.register(RegistryEntry(
            model_id=f"op_{key}",
            canonical_key=key,
            kind="operator",
            description=f"{key} operator",
        ))


def seed_causal_models(store: Store) -> None:
    """Seed a small library of causal rule models so CausalInference can produce predictions."""
    from .types.model import Model, ModelKind, ModelStatus
    from .types.permission import Permission
    from .types.signal import Signal, SignalKind, SourceType

    rules = [
        ("causal_rain_flooding", "rain causes flooding", "causal_causes", ["rain"], ["flooding"]),
        ("causal_heat_melt", "heat causes melting", "causal_causes", ["heat"], ["melting"]),
        ("causal_study_pass", "studying causes passing the exam", "causal_causes", ["studying"], ["passing the exam"]),
        ("causal_exercise_energy", "exercise causes more energy", "causal_causes", ["exercise"], ["more energy"]),
    ]

    existing = store.models.find_by_kind(
        ModelKind.CAUSAL_RULE.value, ModelStatus.ACTIVE.value,
    )
    if existing:
        return

    for model_id, name, registry_key, preconditions, effects in rules:
        seed_signal = Signal(
            id=f"seed_{model_id}",
            kind=SignalKind.SYSTEM,
            source_id="seed",
            source_type=SourceType.SYSTEM,
            content=f"seed causal model: {name}",
            observed_at=time.time(),
            context_id="seed",
            salience=0.5,
            trust=1.0,
            permission=Permission.public(),
        )
        store.signals.put(seed_signal)
        model = Model(
            id=model_id,
            name=name,
            registry_key=registry_key,
            kind=ModelKind.CAUSAL_RULE,
            status=ModelStatus.ACTIVE,
            preconditions=preconditions,
            effects=effects,
            confidence=0.8,
            trust=0.9,
            risk=0.1,
            evidence_signal_ids=[seed_signal.id],
            permission=Permission.public(),
            created_at=time.time(),
            updated_at=time.time(),
        )
        store.models.put(model)


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

    if store.signals.get("seed") is None:
        store.signals.put(Signal(
            id="seed",
            kind=SignalKind.SYSTEM,
            source_id="seed",
            source_type=SourceType.SYSTEM,
            content="seed self knowledge",
            observed_at=time.time(),
            context_id="seed",
            salience=0.5,
            trust=1.0,
            permission=Permission.public(),
        ))

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
                evidence_signal_ids=["seed"],
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

    # Self-referential queries are handled by the UOL mapper and grounding pipeline,
    # which produce entity refs for self and seed them into kernel memory/world.

    # Use pipeline-provided ranked claims if available
    selected_claim_ids = pipeline_result.ranked_claim_ids
    selected_model_ids = pipeline_result.ranked_model_ids
    grounded_graph = pipeline_result.grounded_graph
    memory_packet = pipeline_result.memory_packet
    context_inference = pipeline_result.context_inference
    conversation_act = pipeline_result.conversation_act

    # Fallback: manual retrieval if pipeline didn't populate AND the turn requires evidence
    # Social/creative/repair turns should not trigger fallback retrieval.
    if not selected_claim_ids and (conversation_act is None or conversation_act.requires_evidence or conversation_act.act_type == "unknown"):
        fallback_retriever = StructuralRetriever(store)
        fallback_ranker = Ranker()
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
            conversation_act=conversation_act,
            store=store,
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
            "learn_lexeme": ActionKind.LEARN_LEXEME,
            "learn_command_alias": ActionKind.LEARN_COMMAND_ALIAS,
            "learn_correction": ActionKind.LEARN_CORRECTION,
        }
        kind = _action_kind_map.get(decision.action_kind)
        ap = decision.action_plan
        if kind == ActionKind.ASK:
            params = dict(ap.params) if ap and ap.params else {}
            params.setdefault("question", "Could you elaborate?")
        elif kind == ActionKind.ANSWER:
            # Use action_plan.params as the authoritative contract.
            # Do not recompile or infer intent from reason strings.
            answer_claim_ids = list(ap.selected_claim_ids) if ap else selected_claim_ids
            # For non-evidence response modes, don't pass claims
            response_mode = ap.params.get("response_mode", "") if ap and ap.params else ""
            if response_mode in ("social_response", "creative_response", "repair_response", "capability_summary", "teaching_prompt", "unknown_entity_response"):
                answer_claim_ids = []
            params = {
                "answer_text": "",
                "selected_claim_ids": answer_claim_ids,
                "seg_confidence": pipeline_result.semantic_event_graph.confidence if pipeline_result.semantic_event_graph else 0.0,
                "decision_reason": decision.reason,
            }
            if ap and ap.params:
                params["intent"] = ap.params.get("intent", "")
                params["response_mode"] = ap.params.get("response_mode", "")
            if sim_result is not None:
                params["simulation_claims"] = sim_result.predicted_claims
                params["simulation_confidence"] = sim_result.confidence
        elif kind == ActionKind.ABSTAIN:
            params = {"reason": decision.reason}
        elif kind == ActionKind.REMEMBER:
            # Use action_plan.params as authoritative. Only use claim_candidates
            # from the SEG — no fallback raw text storage.
            seg = pipeline_result.semantic_event_graph
            if seg and seg.claim_candidates:
                cand = seg.claim_candidates[0]
                params = {
                    "subject_entity_id": cand.get("subject", "user") or "user",
                    "predicate": cand.get("predicate", "noted"),
                    "object_value": cand.get("object", ""),
                    "domain": "general",
                }
            elif ap and ap.params:
                params = dict(ap.params)
            else:
                # No claim candidates and no action_plan params: redirect to abstain.
                # Do NOT fall back to storing raw text as a claim.
                kind = ActionKind.ABSTAIN
                params = {"reason": "No structured claim candidate available for storage"}
        elif kind == ActionKind.REFLECT:
            params = {}
            if sim_result is not None:
                params["simulation_claims"] = sim_result.predicted_claims
        elif kind == ActionKind.RETRIEVE:
            params = {}
        elif kind in (
            ActionKind.LEARN_LEXEME,
            ActionKind.LEARN_COMMAND_ALIAS,
            ActionKind.LEARN_CORRECTION,
        ):
            params = dict(ap.params) if ap and ap.params else {}
            params["action_kind"] = kind

    # Safety net: if no SEG was produced, abstain
    if kind is None:
        kind = ActionKind.ABSTAIN
        params = {"reason": "No semantic event graph produced"}

    ctx = OperatorContext(
        kernel=kernel,
        input_signal=input_signal,
        store=store,
        registry=registry,
        lexeme_memory=pipeline._lexeme_memory,
        selected_claim_ids=selected_claim_ids,
        selected_model_ids=selected_model_ids,
        grounded_graph_id=grounded_graph.id if grounded_graph else None,
        memory_packet_id=memory_packet.id if memory_packet else None,
        inference_packet_id=inference_packet.id if inference_packet else None,
        semantic_event_graph_id=pipeline_result.semantic_event_graph.id if pipeline_result.semantic_event_graph else None,
        decision_packet_id=decision.id if decision else None,
        params=params,
    )
    op_start = time.time()
    op_result = op_registry.execute(kind, ctx)
    op_cost_ms = (time.time() - op_start) * 1000.0
    output = op_result.output_text

    # Fix trace metadata for the operator result.
    if op_result.trace:
        spec = op_registry.get_spec(kind)
        op_result.trace.operator_model_id = spec.model_id if spec else kind.value
        op_result.trace.action_id = uuid.uuid4().hex[:16]
        op_result.trace.cost_ms = op_cost_ms
        op_result.trace.frame_rules_applied = grounded_graph is not None
        op_result.trace.causal_inference_used = bool(
            inference_packet
            and (inference_packet.predictions or inference_packet.implications or inference_packet.contradictions)
        )
        if not op_result.trace.semantic_event_graph_id:
            op_result.trace.semantic_event_graph_id = ctx.semantic_event_graph_id
        if op_result.semantic_answer_graph and not op_result.trace.semantic_answer_graph_id:
            op_result.trace.semantic_answer_graph_id = op_result.semantic_answer_graph.id

    # Populate full typed latent snapshot in the trace for CEMM-SLC integration.
    if op_result.trace:
        from .latent.encoder import LatentEncoder
        latent_encoder = LatentEncoder(dim=64)
        sag_for_export = op_result.semantic_answer_graph
        seg_for_export = pipeline_result.semantic_event_graph
        selected_claims = [store.claims.get(cid) for cid in ctx.selected_claim_ids]
        selected_claims = [c for c in selected_claims if c is not None]
        selected_models = [store.models.get(mid) for mid in ctx.selected_model_ids]
        selected_models = [m for m in selected_models if m is not None]
        claim_tuples = [(c.predicate, c.object_value) for c in selected_claims]
        op_result.trace.typed_latents = latent_encoder.encode_typed(
            entity_ids=kernel.memory.working_entity_ids + kernel.world.active_entity_ids,
            process_keys=[p.get("frame_key", "") for p in (seg_for_export.processes if seg_for_export else [])],
            state_keys=[s.get("state_key", "") for s in (seg_for_export.states if seg_for_export else [])],
            claim_tuples=claim_tuples,
            model_keys=[m.id for m in selected_models],
            context_id=kernel.id,
            self_mode=kernel.self_view.mode,
            self_uncertainty=kernel.self_view.uncertainty,
            memory_claim_ids=kernel.memory.working_claim_ids,
            action_kind=kind.value,
            answer_intent=sag_for_export.intent if sag_for_export else "",
            answer_claim_ids=sag_for_export.selected_claim_ids if sag_for_export else [],
            answer_model_ids=sag_for_export.selected_model_ids if sag_for_export else [],
        )

    # Persist action audit record (after latents are attached for complete trace).
    if op_result.trace:
        action = Action(
            id=op_result.trace.action_id,
            kind=kind,
            operator_model_id=op_result.trace.operator_model_id,
            input_signal_ids=[input_signal.id],
            selected_claim_ids=list(ctx.selected_claim_ids),
            selected_model_ids=list(ctx.selected_model_ids),
            confidence=decision.confidence if decision else op_result.trace.confidence,
            risk=ap.risk if ap else 0.0,
            cost_ms=op_cost_ms,
            status=ActionStatus.EXECUTED if op_result.success else ActionStatus.FAILED,
            result_signal_id=op_result.result_signal.id if op_result.result_signal else None,
            trace=op_result.trace,
            created_at=time.time(),
        )
        store.actions.put(action)

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
            old_mode, kernel.self_view.mode, mode_change_action
        )
    for claim_id in ctx.selected_claim_ids:
        claim = store.claims.get(claim_id)
        if claim:
            guard.check_private_claim_used_with_permission(claim, kernel)
            guard.check_disputed_not_presented_certain(claim)
            guard.check_stale_claim_not_used(claim, kernel)
            guard.check_claim_has_evidence(claim)
    for model_id in ctx.selected_model_ids:
        model = store.models.get(model_id)
        if model:
            guard.check_model_has_evidence(model)
            guard.check_model_promoted_with_validation(model)
    if op_result.new_claim_ids:
        for claim_id in op_result.new_claim_ids:
            claim = store.claims.get(claim_id)
            if claim:
                guard.check_prediction_not_presented_as_fact(claim)
                if kernel.self_view.self_id:
                    guard.check_insults_are_not_factual_claims(claim, kernel.self_view.self_id)
                guard.check_temporary_frustration_not_persisted(claim)
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

    # ── OutputStateUpdater (v3 step 14) ──────────────────────────────
    # Update conversation state from ACTUAL realized output, not predicted mode.
    # This fixes the bug where pending_assistant_question was set from
    # decision metadata rather than the actual question text the assistant asked.
    assistant_intent = ap.params.get("intent", "") if ap and ap.params else ""
    assistant_response_mode = ap.params.get("response_mode", "") if ap and ap.params else ""
    output_update = pipeline._output_state_updater.update(
        kernel=kernel,
        output_text=output,
        output_signal_id=op_result.result_signal.id if op_result.result_signal else "",
        assistant_intent=assistant_intent,
        response_mode=assistant_response_mode,
    )
    pipeline._output_state_updater.apply(kernel, output_update)

    # Persist the post-output conversation state. Pipeline.run() persists a
    # pre-output snapshot before the final assistant text exists, so the output
    # updater must write its state transition back into the session store here.
    pipeline._session_state[input_signal.context_id] = {
        "user_affect": kernel.user.affect,
        "conversation_dynamics": kernel.conversation.dynamics,
        "active_repetition_group_ids": list(kernel.conversation.active_repetition_group_ids),
        "recent_signal_ids": list(kernel.conversation.recent_signal_ids),
        "first_user_signal_id": kernel.conversation.first_user_signal_id,
        "last_user_at": input_signal.observed_at,
        "pending_assistant_question": kernel.conversation.pending_assistant_question,
        "expected_user_answer_type": kernel.conversation.expected_user_answer_type,
        "last_assistant_response_mode": kernel.conversation.last_assistant_response_mode,
        "topic_state": {
            "active_topic_entity_id": kernel.topic.active_topic_entity_id,
            "active_topic_surface": kernel.topic.active_topic_surface,
            "active_topic_type": kernel.topic.active_topic_type,
            "last_taught_entity_id": kernel.topic.last_taught_entity_id,
            "last_taught_entity_surface": kernel.topic.last_taught_entity_surface,
            "last_questioned_attribute": kernel.topic.last_questioned_attribute,
        },
    }

    # Export training data if CEMM_EXPORT_PATH is set
    _export_path = os.environ.get("CEMM_EXPORT_PATH")
    if _export_path and op_result.trace:
        from .kernel.training_export import serialize_turn, write_turn_to_jsonl
        sag_for_export = op_result.semantic_answer_graph
        if sag_for_export is None and decision is not None:
            sag_for_export = decision.semantic_answer_graph
        records = serialize_turn(
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
            observation_semantics=input_signal.observation_semantics,
            context_inference=pipeline_result.context_inference if pipeline_result else None,
            conversation_act=pipeline_result.conversation_act if pipeline_result else None,
            meaning_percept=pipeline_result.meaning_percept if pipeline_result else None,
            situation_frame=pipeline_result.situation_frame if pipeline_result else None,
            safety_frame=pipeline_result.safety_frame if pipeline_result else None,
            retrieval_plan=pipeline_result.retrieval_plan if pipeline_result else None,
        )
        for record in records:
            write_turn_to_jsonl(_export_path, record)

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
    seed_causal_models(store)

    for op_class in [
        AnswerOperator, AskOperator, RememberOperator, UpdateClaimOperator,
        CreateModelOperator, SynthesizeOperator, SimulateOperator,
        RetrieveOperator, ReflectOperator, CallToolOperator, AbstainOperator,
    ]:
        op_registry.register(op_class())

    # Learning operators share the pipeline's lexeme memory.
    learn_lexeme_memory = pipeline._lexeme_memory
    op_registry.register(LearnOperator(lexeme_memory=learn_lexeme_memory, action_kind=ActionKind.LEARN_LEXEME))
    op_registry.register(LearnOperator(lexeme_memory=learn_lexeme_memory, action_kind=ActionKind.LEARN_COMMAND_ALIAS))
    op_registry.register(LearnOperator(lexeme_memory=learn_lexeme_memory, action_kind=ActionKind.LEARN_CORRECTION))

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
