from __future__ import annotations
import copy
import time
import uuid
from dataclasses import dataclass, field
from ..types.signal import Signal, SignalKind, SourceType
from ..types.action import Action, ActionKind, ActionStatus
from ..types.trace import Trace
from ..types.context_kernel import ContextKernel
from ..types.semantic_event_graph import SemanticEventGraph
from ..types.packets import GroundedGraph, MemoryPacket, RankingTraceEntry, InferencePacket, DecisionPacket
from ..types.context_inference import ContextInference
from ..types.self_view import SelfView
from ..types.permission import Permission
from ..store.store import Store
from ..store.artifact_store import ArtifactStore
from ..registry import Registry
from ..confidence.scoring import score_action
from .context_kernel_builder import ContextKernelBuilder
from .text_normalizer import TextNormalizer
from .entity_resolver import EntityResolver
from .frame_engine import FrameEngine
from .pragmatic_interpreter import interpret_signal, update_user_affect, update_conversation_dynamics
from ..registry.uol_mapper import UOLMapper
from ..kernel.teaching_interpreter import TeachingInterpreter
from ..learning.lexeme_memory import LexemeMemory
from .context_inference import ContextInferenceEngine
from .semantic_interpreter import SemanticInterpreter
from .grounding import GroundingPipeline
from .decision_router import DecisionRouter
from .conversation_act_classifier import ConversationActClassifier
from .meaning_perceptor import MeaningPerceptor
from .situation_frame_builder import SituationFrameBuilder
from .outcome_evaluator import OutcomeEvaluator
from .safety_frame_detector import SafetyFrameDetector
from .retrieval_planner import RetrievalPlanner
from .output_state_updater import OutputStateUpdater
from ..types.conversation_act import ConversationAct, ConversationActPacket
from ..types.meaning_percept import MeaningPerceptPacket, SituationFrame, SafetyFrame, RetrievalPlan
from ..causal.inference import CausalInference
from ..retrieval.structural import StructuralRetriever, RetrievalResult
from ..retrieval.ranker import Ranker


@dataclass
class PipelineResult:
    output_text: str = ""
    actions: list[Action] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    kernel: ContextKernel | None = None
    confidence: float = 0.0
    cost_ms: float = 0.0
    abstained: bool = False
    ranked_claim_ids: list[str] = field(default_factory=list)
    ranked_model_ids: list[str] = field(default_factory=list)
    semantic_event_graph: SemanticEventGraph | None = None
    grounded_graph: GroundedGraph | None = None
    memory_packet: MemoryPacket | None = None
    inference_packet: InferencePacket | None = None
    decision_packet: DecisionPacket | None = None
    context_inference: ContextInference | None = None
    conversation_act: ConversationActPacket | None = None
    meaning_percept: MeaningPerceptPacket | None = None
    situation_frame: SituationFrame | None = None
    safety_frame: SafetyFrame | None = None
    retrieval_plan: RetrievalPlan | None = None


class Pipeline:
    def __init__(
        self,
        store: Store,
        registry: Registry,
    ) -> None:
        self._store = store
        self._registry = registry
        self._builder = ContextKernelBuilder()
        self._resolver = EntityResolver(store.entities)
        self._frames = FrameEngine(store.claims)
        self._lexeme_memory = LexemeMemory()
        self._teaching_interpreter = TeachingInterpreter()
        self._uol_mapper = UOLMapper(
            registry,
            lexeme_memory=self._lexeme_memory,
            teaching_interpreter=self._teaching_interpreter,
        )
        self._artifact_store = ArtifactStore(store)
        self._text_normalizer = TextNormalizer(lexeme_memory=self._lexeme_memory)
        self._semantic_interpreter = SemanticInterpreter(
            self._uol_mapper, artifact_store=self._artifact_store, store=store,
            lexeme_memory=self._lexeme_memory,
            text_normalizer=self._text_normalizer,
        )
        self._grounding_pipeline = GroundingPipeline(self._resolver, self._frames)
        self._context_inference_engine = ContextInferenceEngine(store, registry)
        self._causal_inference = CausalInference(store)
        self._decision_router = DecisionRouter(uol_mapper=self._uol_mapper)
        self._conversation_act_classifier = ConversationActClassifier(registry)
        self._retriever = StructuralRetriever(store)
        self._ranker = Ranker()
        # New v3 components
        self._meaning_perceptor = MeaningPerceptor(
            ner_tagger=self._semantic_interpreter._ner_tagger,
            surface_tagger=self._semantic_interpreter._surface_tagger,
            lexeme_memory=self._lexeme_memory,
        )
        self._situation_frame_builder = SituationFrameBuilder()
        self._outcome_evaluator = OutcomeEvaluator()
        self._safety_frame_detector = SafetyFrameDetector()
        self._retrieval_planner = RetrievalPlanner()
        self._output_state_updater = OutputStateUpdater()
        self._turn_counts: dict[str, int] = {}
        self._session_state: dict[str, dict] = {}

    def run(
        self,
        input_text: str,
        context_id: str | None = None,
        budget_override: dict | None = None,
        source_id: str = "user",
    ) -> PipelineResult:
        start = time.time()
        signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.INPUT,
            source_id=source_id,
            source_type=SourceType.USER,
            content=input_text,
            observed_at=start,
            context_id=context_id or uuid.uuid4().hex[:16],
            salience=0.8,
            trust=0.8,
            permission=Permission.public(),
        )
        self._store.signals.put(signal)
        signal.normalized = self._text_normalizer.normalize(signal.content)

        turn_index = self._turn_counts.get(signal.context_id, 0) + 1
        self._turn_counts[signal.context_id] = turn_index
        kernel = self._builder.from_signal(signal, turn_index=turn_index)
        kernel.latest_signal = signal

        prior_session = self._session_state.get(signal.context_id)
        if prior_session:
            kernel.user.affect = copy.deepcopy(prior_session.get("user_affect", kernel.user.affect))
            kernel.conversation.dynamics = copy.deepcopy(
                prior_session.get("conversation_dynamics", kernel.conversation.dynamics)
            )
            kernel.conversation.active_repetition_group_ids = list(
                prior_session.get("active_repetition_group_ids", kernel.conversation.active_repetition_group_ids)
            )
            previous_recent = list(prior_session.get("recent_signal_ids", []))
            kernel.conversation.recent_signal_ids = previous_recent + [signal.id]
            kernel.conversation.first_user_signal_id = prior_session.get(
                "first_user_signal_id", kernel.conversation.first_user_signal_id
            )
            last_user_at = prior_session.get("last_user_at")
            if last_user_at is not None:
                kernel.time.time_since_last_user_signal_ms = max(
                    0.0, (signal.observed_at - float(last_user_at)) * 1000.0,
                )
            kernel.conversation.pending_assistant_question = prior_session.get(
                "pending_assistant_question", ""
            )
            kernel.conversation.expected_user_answer_type = prior_session.get(
                "expected_user_answer_type", ""
            )
            kernel.conversation.last_assistant_response_mode = prior_session.get(
                "last_assistant_response_mode", ""
            )

        if budget_override:
            for k, v in budget_override.items():
                if hasattr(kernel.budget, k):
                    setattr(kernel.budget, k, v)

        self_state = self._store.self_store.latest()
        if self_state:
            kernel.self_view = SelfView.from_self_state(self_state, kernel.memory.working_claim_ids)
        else:
            kernel.self_view = SelfView()

        # Contextualize: infer context from signal + kernel before interpretation
        context_inference = self._context_inference_engine.infer(signal, kernel)
        self._context_inference_engine.apply_to_kernel(context_inference, kernel)

        # ── Build MeaningPerceptPacket (v3 step 3) ───────────────────
        # NER + unknown lexemes + POS-lite roles + pronouns/deixis + affect
        # Must happen before UOL mapping, before retrieval, before decision.
        meaning_percept = self._meaning_perceptor.perceive(signal, kernel)

        # ── Build SituationFrame (v3 step 4) ──────────────────────────
        # Actor/action/object/place/state/need + event schema candidates
        situation_frame = self._situation_frame_builder.build(meaning_percept, kernel)

        # ── Evaluate outcomes and valences (v3 step 4b) ───────────────
        outcomes, valences = self._outcome_evaluator.evaluate(situation_frame)
        situation_frame.expected_outcomes = outcomes
        situation_frame.valences = valences

        # ── Detect SafetyFrame (v3 step 5) ────────────────────────────
        safety_frame = self._safety_frame_detector.detect(
            situation=situation_frame,
            input_text=signal.content,
            valences=valences,
        )
        if safety_frame:
            situation_frame.safety_frame = safety_frame

        # Interpret: SemanticEventGraph + UOL atoms (single authority)
        # §8.13: SemanticInterpreter now consumes MeaningPerceptPacket + SituationFrame
        # to enrich the graph with pre-bound atoms, skipping redundant NER/SurfaceTagger.
        semantic_event_graph = self._semantic_interpreter.run(
            signal, kernel,
            meaning_percept=meaning_percept,
            situation_frame=situation_frame,
        )
        semantics = interpret_signal(signal, kernel, self._store, main_registry=self._registry)
        uol_atoms: list | None = None
        if semantics is not None:
            # NOTE: SemanticInterpreter.run() already calls UOLMapper internally.
            # This second call is needed to get raw UOL atoms for pragmatic key
            # compilation and observation_semantics. Future refactor: have
            # SemanticInterpreter return atoms directly to eliminate the duplicate.
            uol_atoms = self._uol_mapper.map_signal(signal.content, kernel)
            semantics.uol_atoms = uol_atoms
            quality_keys, process_keys = self._uol_mapper.compile_to_pragmatic_keys(uol_atoms)
            kernel.user.affect.active_quality_atom_keys = quality_keys
            if kernel.conversation.dynamics:
                kernel.conversation.dynamics.active_process_atom_keys = process_keys
            signal.observation_semantics = semantics
            from .invariant_guard import InvariantGuard
            InvariantGuard.check_uol_not_bypassing_registry(uol_atoms, self._registry)
            if semantics.semantic_cluster_key:
                kernel.user.affect = update_user_affect(kernel.user.affect, semantics, kernel, signal.id)
                kernel.conversation.dynamics = update_conversation_dynamics(
                    kernel.conversation.dynamics, semantics, kernel, signal.id
                )
                kernel.conversation.active_repetition_group_ids = list(
                    kernel.conversation.dynamics.active_repetition_group_ids
                )

        # Classify ConversationActPacket — now consumes MeaningPercept + SituationFrame + SafetyFrame
        conversation_act = self._conversation_act_classifier.classify(
            signal, kernel,
            uol_atoms=uol_atoms,
            meaning_percept=meaning_percept,
            situation_frame=situation_frame,
            safety_frame=safety_frame,
        )

        # Clear pending question if the user answered it or the topic shifted
        if kernel.conversation.pending_assistant_question:
            if conversation_act.discourse_relation == "answer_to_pending":
                kernel.conversation.pending_assistant_question = ""
                kernel.conversation.expected_user_answer_type = ""
            elif conversation_act.primary.act_type not in ("unknown", "chat_mode_statement"):
                # Topic shifted — clear stale pending question
                kernel.conversation.pending_assistant_question = ""
                kernel.conversation.expected_user_answer_type = ""

        # Update last response mode for next turn's context
        kernel.conversation.last_assistant_response_mode = conversation_act.response_mode

        # Suppress claim candidates for social/creative/repair/teaching turns.
        # "unknown" turns are permissive — claim candidates may flow through.
        if semantic_event_graph and conversation_act.act_type != "unknown" and not conversation_act.allows_memory_write:
            semantic_event_graph.claim_candidates = []

        # Ground entities, time, frame, permission
        grounded_graph = self._grounding_pipeline.run(semantic_event_graph, kernel, content=signal.content)

        # Seed entity IDs from graph for graph-grounded retrieval
        for ref in semantic_event_graph.entity_refs:
            eid = ref.get("entity_id", "")
            if eid and eid not in kernel.memory.working_entity_ids:
                kernel.memory.working_entity_ids.append(eid)

        # ── Build RetrievalPlan (v3 step 8) ───────────────────────────
        # Explicit retrieval plan replaces implicit requires_evidence gating
        retrieval_plan = self._retrieval_planner.plan(
            conversation_act=conversation_act,
            situation=situation_frame,
            safety_frame=safety_frame,
            has_unknown_lexemes=bool(meaning_percept.unknown_lexemes),
            has_idiom_candidates=bool(meaning_percept.idiom_candidates),
        )

        # Retrieve claims and models — gated by RetrievalPlan
        if retrieval_plan.mode != "none":
            retrieval_result = self._retriever.retrieve_for_kernel(kernel)

            # Graph-grounded retrieval enrichment
            graph_result = self._retriever.retrieve_for_graph(semantic_event_graph, kernel)
        else:
            retrieval_result = RetrievalResult(claims=[], models=[])
            graph_result = RetrievalResult(claims=[], models=[])

        # Merge: deduplicate by claim ID, prefer graph results
        seen_ids = {c.id for c in retrieval_result.claims}
        for c in graph_result.claims:
            if c.id not in seen_ids:
                retrieval_result.claims.append(c)
                seen_ids.add(c.id)

        # Apply frame rules before ranking (architecture requires frame rules before permission/ranking)
        retrieval_result.claims = self._frames.filter_valid(retrieval_result.claims, kernel)

        # Rank claims and models with graph context
        # Skip ranking entirely when retrieval plan says none
        if retrieval_plan.mode != "none":
            ranked_claims = self._ranker.rank_claims(retrieval_result.claims, kernel, graph=semantic_event_graph)
            ranked_models = self._ranker.rank_models(retrieval_result.models, kernel, store=self._store)
            kernel.memory.working_claim_ids = [c.id for c, _ in ranked_claims[:kernel.budget.max_ranked]]
            kernel.world.active_claim_ids = kernel.memory.working_claim_ids
            kernel.memory.candidate_model_ids = [m.id for m, _ in ranked_models[:kernel.budget.max_ranked]]
        else:
            ranked_claims = []
            ranked_models = []
            kernel.memory.working_claim_ids = []
            kernel.world.active_claim_ids = []
            kernel.memory.candidate_model_ids = []

        # Update self-view uncertainty based on available evidence
        n_claims = len(kernel.memory.working_claim_ids)
        n_models = len(kernel.memory.candidate_model_ids)
        kernel.self_view.uncertainty = max(0.2, 1.0 - min(1.0, (n_claims + n_models * 0.5) / 10.0))

        # Invariant: ensure context inference does not override explicit user claims
        if kernel.memory.working_claim_ids:
            from .invariant_guard import InvariantGuard
            from ..types.claim import Claim
            explicit = self._store.claims.get(kernel.memory.working_claim_ids[0])
            if explicit is not None:
                inferred = Claim(
                    id=f"inferred_{explicit.id}",
                    subject_entity_id=explicit.subject_entity_id,
                    predicate=explicit.predicate,
                    object_value=explicit.object_value,
                    source_id="context_inference",
                )
                InvariantGuard.check_context_not_override_explicit(inferred, explicit)

        memory_packet = MemoryPacket(
            selected_signal_ids=[signal.id],
            selected_claim_ids=list(kernel.memory.working_claim_ids),
            selected_model_ids=list(kernel.memory.candidate_model_ids),
    ranking_trace=[
        RankingTraceEntry(
            candidate_id=c.id,
            score=s,
            reason=f"ranked {s:.3f}",
        )
        for c, s in ranked_claims
    ] if ranked_claims else [],
            confidence=sum(s for _, s in ranked_claims[:5]) / len(ranked_claims[:5]) if ranked_claims else 0.5,
        )

        # Infer: causal inference + slot inference
        inference_packet = InferencePacket(
            id=uuid.uuid4().hex[:16],
            inference_graph_input_signal_ids=[signal.id],
        )
        if semantic_event_graph and semantic_event_graph.causal_edges:
            inference_packet = self._causal_inference.predict(
                signal.content,
                semantic_event_graph.claim_refs,
                kernel,
                graph=semantic_event_graph,
            )

        # Decide: choose action based on grounded graph, memory, inference, conversation act
        decision_packet = self._decision_router.run(
            graph=semantic_event_graph,
            kernel=kernel,
            grounded_graph=grounded_graph,
            memory_packet=memory_packet,
            inference_packet=inference_packet,
            input_text=signal.content,
            observation_semantics=signal.observation_semantics,
            context_inference=context_inference,
            conversation_act=conversation_act,
            store=self._store,
        )

        self._check_budget(kernel, start)

        result = PipelineResult(
            kernel=kernel,
            ranked_claim_ids=kernel.memory.working_claim_ids,
            ranked_model_ids=[m.id for m in retrieval_result.models],
            semantic_event_graph=semantic_event_graph,
            grounded_graph=grounded_graph,
            memory_packet=memory_packet,
            context_inference=context_inference,
            conversation_act=conversation_act,
            inference_packet=inference_packet,
            decision_packet=decision_packet,
            meaning_percept=meaning_percept,
            situation_frame=situation_frame,
            safety_frame=safety_frame,
            retrieval_plan=retrieval_plan,
        )
        # Validate runtime packets against schemas
        from ..kernel.packet_validator import validate_packet
        from dataclasses import asdict

        validation_errors: list[str] = []
        if result.semantic_event_graph:
            validation_errors.extend(validate_packet(asdict(result.semantic_event_graph), "semantic_event_graph") or [])
        if result.grounded_graph:
            validation_errors.extend(validate_packet(asdict(result.grounded_graph), "grounded_graph") or [])
        if result.memory_packet:
            validation_errors.extend(validate_packet(asdict(result.memory_packet), "memory_packet") or [])
        if result.inference_packet:
            validation_errors.extend(validate_packet(asdict(result.inference_packet), "inference_packet") or [])
        if result.decision_packet:
            validation_errors.extend(validate_packet(asdict(result.decision_packet), "decision_packet") or [])
        if validation_errors:
            result.abstained = True
            if result.kernel is not None:
                result.kernel.self_view.recent_error_rate = min(
                    1.0, result.kernel.self_view.recent_error_rate + 0.1
                )

        self._session_state[signal.context_id] = {
            "user_affect": copy.deepcopy(kernel.user.affect),
            "conversation_dynamics": copy.deepcopy(kernel.conversation.dynamics),
            "active_repetition_group_ids": list(kernel.conversation.active_repetition_group_ids),
            "recent_signal_ids": list(kernel.conversation.recent_signal_ids),
            "first_user_signal_id": kernel.conversation.first_user_signal_id,
            "last_user_at": signal.observed_at,
            "pending_assistant_question": kernel.conversation.pending_assistant_question,
            "expected_user_answer_type": kernel.conversation.expected_user_answer_type,
            "last_assistant_response_mode": kernel.conversation.last_assistant_response_mode,
        }

        result.signals.append(signal)
        result.cost_ms = (time.time() - start) * 1000.0
        return result

    def _check_budget(self, kernel: ContextKernel, start: float) -> None:
        elapsed = (time.time() - start) * 1000.0
        if elapsed > kernel.budget.latency_target_ms:
            working_ids = kernel.memory.working_signal_ids
            if len(working_ids) > kernel.budget.max_entities:
                kernel.memory.working_signal_ids = working_ids[-kernel.budget.max_entities:]
            if len(kernel.world.active_claim_ids) > kernel.budget.max_claims:
                kernel.world.active_claim_ids = kernel.world.active_claim_ids[-kernel.budget.max_claims:]
