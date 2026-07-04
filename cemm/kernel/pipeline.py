from __future__ import annotations
import copy
import time
import uuid
from dataclasses import dataclass, field
from ..types.signal import Signal, SignalKind, SourceType
from ..types.action import Action, ActionKind, ActionStatus
from ..types.trace import Trace
from ..types.context_kernel import ContextKernel
from ..types.packets import GroundedGraph, MemoryPacket, RankingTraceEntry, InferencePacket, DecisionPacket
from ..types.context_inference import ContextInference
from ..types.self_view import SelfView
from ..types.permission import Permission
from ..store.store import Store
from ..store.artifact_store import ArtifactStore
from ..registry import Registry
from .context_kernel_builder import ContextKernelBuilder
from .text_normalizer import TextNormalizer
from .entity_resolver import EntityResolver
from .frame_engine import FrameEngine
from .pragmatic_interpreter import interpret_signal, update_user_affect, update_conversation_dynamics
from ..registry.uol_mapper import UOLMapper
from .teaching_interpreter import TeachingInterpreter
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
from .entity_fact_extractor import EntityFactExtractor
from .act_resolution_planner import ActResolutionPlanner, ActResolutionPlan
from .reaction_detector import ReactionDetector, ReactionSignal
from .response_planner import ResponsePlanner, ResponsePlan
from .error_attribution_engine import ErrorAttributionEngine, ErrorAttributionResult
from ..registry.semantic_model_store import SemanticModelStore
from .language_detection import detect_and_get_adapter
from .promotion_gate import PromotionGate
from ..types.conversation_act import ConversationActPacket
from ..types.meaning_percept import MeaningPerceptPacket, SituationFrame, SafetyFrame, RetrievalPlan
from ..types.uol_graph import UOLGraph
from ..causal.inference import CausalInference
from ..retrieval.ranker import Ranker
from ..retrieval.retrieval_executor import RetrievalExecutor, RetrievalExecutionResult
from .semantic_kernel_runtime import SemanticKernelRuntime
from .meaning_graph_builder import MeaningGraphBuilder
from .port_resolver import LatticePortResolver
from .affordance_predictor import AffordancePredictor
from ..memory.concept_lattice import ConceptLattice
from ..memory.construction_lattice import ConstructionLattice
from ..memory.episodic_trace_store import EpisodicTraceStore


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
    act_resolution_plan: ActResolutionPlan | None = None
    retrieval_execution: RetrievalExecutionResult | None = None
    reaction_signal: ReactionSignal | None = None
    response_plan: ResponsePlan | None = None
    error_attribution: ErrorAttributionResult | None = None
    uol_graph: UOLGraph | None = None


class Pipeline:
    def __init__(
        self,
        store: Store,
        registry: Registry,
        concept_lattice: ConceptLattice | None = None,
        construction_lattice: ConstructionLattice | None = None,
        episodic_store: EpisodicTraceStore | None = None,
        auto_consolidate: bool = False,
    ) -> None:
        self._store = store
        self._registry = registry
        self._builder = ContextKernelBuilder()
        self._resolver = EntityResolver(store.entities)
        self._frames = FrameEngine(store.claims)
        self._lexeme_memory = LexemeMemory()
        self._semantic_model_store = SemanticModelStore(lexeme_memory=self._lexeme_memory)
        self._teaching_interpreter = TeachingInterpreter()
        self._uol_mapper = UOLMapper(
            registry,
            lexeme_memory=self._lexeme_memory,
            teaching_interpreter=self._teaching_interpreter,
            semantic_model_store=self._semantic_model_store,
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
        self._conversation_act_classifier = ConversationActClassifier(
            registry, semantic_model_store=self._semantic_model_store,
        )
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
        self._entity_fact_extractor = EntityFactExtractor()
        self._act_resolution_planner = ActResolutionPlanner()
        self._reaction_detector = ReactionDetector()
        self._response_planner = ResponsePlanner()
        self._error_attribution_engine = ErrorAttributionEngine()
        self._promotion_gate = PromotionGate(semantic_model_store=self._semantic_model_store)
        self._retrieval_executor = RetrievalExecutor(store)
        self._turn_counts: dict[str, int] = {}
        self._session_state: dict[str, dict] = {}
        # v4.2: SemanticKernelRuntime — single authoritative entrypoint
        self._runtime: SemanticKernelRuntime | None = None
        self._concept_lattice = concept_lattice
        self._construction_lattice = construction_lattice
        self._episodic_store = episodic_store or EpisodicTraceStore()
        if concept_lattice is not None:
            self._runtime = SemanticKernelRuntime(
                concept_lattice=concept_lattice,
                construction_lattice=construction_lattice,
                episodic_store=self._episodic_store,
                store=store,
                auto_consolidate=auto_consolidate,
            )
        # Always create a fallback graph builder so the pipeline never produces
        # an empty graph, even when the runtime is not configured.
        self._fallback_graph_builder = MeaningGraphBuilder(
            concept_lattice=concept_lattice,
            construction_lattice=construction_lattice,
            port_resolver=LatticePortResolver(concept_lattice) if concept_lattice else None,
            affordance_lattice=AffordancePredictor() if concept_lattice else None,
        )

    @property
    def semantic_model_store(self) -> SemanticModelStore:
        return self._semantic_model_store

    @property
    def promotion_gate(self) -> PromotionGate:
        return self._promotion_gate

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
            # Restore topic state for pronoun coreference and multi-turn learning
            prior_topic = prior_session.get("topic_state")
            if prior_topic:
                kernel.topic.active_topic_entity_id = prior_topic.get("active_topic_entity_id", "")
                kernel.topic.active_topic_surface = prior_topic.get("active_topic_surface", "")
                kernel.topic.active_topic_type = prior_topic.get("active_topic_type", "")
                kernel.topic.last_taught_entity_id = prior_topic.get("last_taught_entity_id", "")
                kernel.topic.last_taught_entity_surface = prior_topic.get("last_taught_entity_surface", "")
                kernel.topic.last_questioned_attribute = prior_topic.get("last_questioned_attribute", "")
            # v3.3: Restore discourse stack for repair targeting
            prior_discourse = prior_session.get("discourse_stack")
            if prior_discourse:
                kernel.conversation.discourse_stack = prior_discourse
            kernel.conversation.repair_target_turn_id = prior_session.get("repair_target_turn_id", "")
            kernel.conversation.active_teaching_target = prior_session.get("active_teaching_target", "")
            kernel.conversation.active_unknown_concept = prior_session.get("active_unknown_concept", "")

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
        # v3.3 Phase 4: Detect language and select appropriate adapter
        detected_lang, lang_adapter = detect_and_get_adapter(signal.content)
        self._meaning_perceptor._language = lang_adapter
        meaning_percept = self._meaning_perceptor.perceive(signal, kernel)

        # v4.2: Build UOLGraph — the single working graph.
        # Always initialize so downstream consumers never see None.
        # Use runtime builder when available; fall back to the pipeline's own
        # builder so the graph is NEVER empty across any code path.
        uol_graph = UOLGraph(
            id=uuid.uuid4().hex[:16],
            signal_id=signal.id,
            context_id=signal.context_id,
            raw_text=signal.content,
        )
        graph_builder = None
        if self._runtime is not None and self._runtime.graph_builder is not None:
            graph_builder = self._runtime.graph_builder
        elif self._fallback_graph_builder is not None:
            graph_builder = self._fallback_graph_builder
        if graph_builder is not None:
            try:
                built = graph_builder.build(meaning_percept)
                if built is not None:
                    uol_graph = built
                    meaning_percept.uol_graph = uol_graph
            except Exception:
                pass

        # Make sure graph has at least the self atom
        # If builder failed or produced empty graph, route to abstain
        graph_is_empty = len(uol_graph.atoms) <= 1  # only self_atom, or empty
        uol_graph.trace["graph_empty"] = graph_is_empty

        # ── SituationFrameBuilder (v3.1 step 3b) ─────────────────────
        # Delegates to FrameBinder for atom-based role binding with scored
        # role assignments and schema outcomes.
        situation_frame = self._situation_frame_builder.build(meaning_percept, kernel)

        # ── EntityFactExtractor (v3.1 step 3c) ────────────────────────
        # Atom-first fact extraction with surface pattern fallback.
        # Returns EntityFactExtractionResult with typed EntityFactCandidate list.
        fact_result = self._entity_fact_extractor.extract(
            meaning_percept,
            situation=situation_frame,
            kernel=kernel,
        )
        fact_candidates = fact_result.candidates
        self._entity_fact_extractor.update_topic_state(
            kernel, meaning_percept, fact_candidates,
            signal.id, signal.observed_at,
        )

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

        # v4.2: UOLGraph is the single working graph.
        # Entity fact candidates are merged into UOLGraph as claim_candidates
        # and as GraphPatch candidates for consolidation.
        if fact_candidates:
            existing = uol_graph.claim_candidates
            existing_keys = {(c.get("subject", ""), c.get("predicate", "")) for c in existing}
            for fc in fact_candidates:
                key = (fc.subject_entity_id, fc.predicate)
                if key not in existing_keys:
                    uol_graph.claim_candidates.append(fc.to_claim_dict())
                    existing_keys.add(key)

            from ..types.graph_patch import GraphPatch, PatchOperation
            fact_ops = []
            for fc in fact_candidates:
                fact_ops.append(PatchOperation(
                    operation="upsert_relation_candidate",
                    target_id=f"entity:{fc.subject_entity_id}",
                    fields={
                        "subject": fc.subject_entity_id,
                        "predicate": fc.predicate,
                        "object_value": fc.object_value,
                        "object_entity_id": fc.object_entity_id,
                        "domain": fc.domain,
                        "source": fc.source,
                        "evidence_span": fc.evidence_span,
                    },
                    confidence=fc.confidence,
                    reason=fc.reason,
                ))
            if fact_ops:
                uol_graph.add_patch_candidate(GraphPatch(
                    source_graph_id=uol_graph.id,
                    target="concept_lattice",
                    operations=fact_ops,
                    confidence=max(op.confidence for op in fact_ops),
                    reason="entity_fact_candidates",
                ))
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

        # ── ReactionDetector (v3.3: pre-classification) ──────────────
        # Lightweight detection of whether the current input is a reaction
        # to the previous assistant output. Runs before classification using
        # only MeaningPerceptPacket + DiscourseStateStack.
        reaction_signal = self._reaction_detector.detect(
            percept=meaning_percept,
            discourse_stack=kernel.conversation.discourse_stack,
        )
        if reaction_signal.is_reaction:
            kernel.conversation.repair_target_turn_id = reaction_signal.target_turn_id

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

        # ── ActResolutionPlanner (v3.3: moved BEFORE retrieval) ─────────
        # Resolve multi-act ConversationActPacket into typed runtime tasks
        # BEFORE retrieval so the retrieval plan can use obligations instead
        # of re-deriving from conversation_act.act_type.
        act_resolution_plan = self._act_resolution_planner.plan(
            conversation_act=conversation_act,
            situation=situation_frame,
            safety_frame=safety_frame,
            fact_candidates=fact_candidates,
            meaning_percept=meaning_percept,
        )

        # Suppress claim candidates for social/creative/repair/teaching turns.
        # "unknown" turns are permissive — claim candidates may flow through.
        # Check all acts in the packet, not just the primary — a secondary
        # claim_assertion should preserve candidates even if primary is social.
        # v3.3: Also consult act_resolution_plan.memory_updates — if the plan
        # has memory tasks, preserve candidates even if the primary act is social.
        if uol_graph is not None and "unknown" not in conversation_act.act_types:
            has_memory_plan = bool(act_resolution_plan and act_resolution_plan.memory_updates)
            if not any(act.allows_memory_write for act in conversation_act.all_acts) and not has_memory_plan:
                uol_graph.claim_candidates = []

        # Ground entities, time, frame, permission
        grounded_graph = self._grounding_pipeline.run(uol_graph, kernel, content=signal.content) if uol_graph is not None else GroundedGraph(
            semantic_event_graph_id="", entity_ids=[], resolved_time_refs=[], resolved_location_ids=[],
            active_frame_ids=[], permission="public", missing_slots=[], confidence=0.5,
        )

        # Seed entity IDs from graph for graph-grounded retrieval
        if uol_graph is not None:
            for atom in (a for a in uol_graph.atoms.values() if a.kind in ("entity", "self")):
                eid = atom.key.replace("entity:", "").replace("self:", "")
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
            act_resolution_plan=act_resolution_plan,
        )

        # Retrieve claims and models — gated by RetrievalPlan via RetrievalExecutor
        retrieval_execution = self._retrieval_executor.execute(
            retrieval_plan, kernel,
            graph=uol_graph,
            lexeme_memory=self._lexeme_memory,
        )
        retrieval_result = retrieval_execution.result

        # Apply frame rules before ranking (architecture requires frame rules before permission/ranking)
        retrieval_result.claims = self._frames.filter_valid(retrieval_result.claims, kernel)

        # Rank claims and models with graph context
        # Skip ranking entirely when retrieval plan says none
        if retrieval_plan.mode != "none":
            ranked_claims = self._ranker.rank_claims(retrieval_result.claims, kernel, graph=uol_graph)
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
        if uol_graph is not None and uol_graph.edges_by_type("causes"):
            inference_packet = self._causal_inference.predict(
                signal.content,
                kernel.memory.working_claim_ids,
                kernel,
                graph=uol_graph,
            )

        # v3.3: Plan response specification from act resolution and capability model
        has_evidence = bool(memory_packet and memory_packet.selected_claim_ids)
        response_plan = self._response_planner.plan(
            conversation_act=conversation_act,
            act_resolution_plan=act_resolution_plan,
            safety_frame=safety_frame,
            has_evidence=has_evidence,
        )

        # v3.3 Phase 9: Error attribution — evaluate reaction signal against
        # previous discourse state. Runs before decision routing so that
        # safety_missed errors can influence the current turn's routing.
        error_attribution = self._error_attribution_engine.evaluate(
            reaction_signal=reaction_signal,
            conversation_act=conversation_act,
            discourse_stack=kernel.conversation.discourse_stack,
            decision_packet=None,
            sag=None,
            realization_metadata=None,
        )
        if error_attribution:
            self._error_attribution_engine.apply(
                error_attribution,
                kernel.conversation.discourse_stack,
                kernel.self_view,
                semantic_model_store=self._semantic_model_store,
            )

        # v4.2: Build working set for cycle-aware decision routing
        working_set = None
        if self._runtime is not None:
            try:
                working_set = self._runtime.attention.attend(
                    uol_graph or UOLGraph(), kernel, kernel.budget,
                )
            except Exception:
                working_set = None

        # Decide: choose action based on grounded graph, memory, inference, conversation act
        # v3.3: DecisionRouter now receives act_resolution_plan as primary routing signal
        decision_packet = self._decision_router.run(
            graph=uol_graph or UOLGraph(),
            kernel=kernel,
            grounded_graph=grounded_graph,
            memory_packet=memory_packet,
            inference_packet=inference_packet,
            input_text=signal.content,
            observation_semantics=signal.observation_semantics,
            context_inference=context_inference,
            conversation_act=conversation_act,
            store=self._store,
            act_resolution_plan=act_resolution_plan,
            # v4.2: Cycle-aware routing
            working_set=working_set,
        )

        self._check_budget(kernel, start)

        result = PipelineResult(
            kernel=kernel,
            ranked_claim_ids=kernel.memory.working_claim_ids,
            ranked_model_ids=[m.id for m, _ in ranked_models] if ranked_models else [],
            uol_graph=uol_graph,
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
            act_resolution_plan=act_resolution_plan,
            retrieval_execution=retrieval_execution,
            reaction_signal=reaction_signal,
            response_plan=response_plan,
            error_attribution=error_attribution,
        )
        # Validate runtime packets against schemas
        from ..kernel.packet_validator import validate_packet
        from dataclasses import asdict

        validation_errors: list[str] = []
        if result.uol_graph:
            validation_errors.extend(validate_packet(asdict(result.uol_graph), "uol_graph") or [])
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

        # v4.2: SemanticKernelRuntime consolidation at end of turn
        if uol_graph is not None and self._runtime is not None:
            patches = self._runtime.patch_extractor.extract(uol_graph)
            if self._runtime.auto_consolidate:
                self._runtime.consolidator.consolidate(
                    patches,
                    source_graph=uol_graph,
                )

            # v4.2 PatchPipeline flush: write dirty lattice state to store
            if hasattr(self._runtime, 'patch_router') and self._runtime.patch_router is not None:
                self._runtime.patch_router.flush_all()

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
            "topic_state": {
                "active_topic_entity_id": kernel.topic.active_topic_entity_id,
                "active_topic_surface": kernel.topic.active_topic_surface,
                "active_topic_type": kernel.topic.active_topic_type,
                "last_taught_entity_id": kernel.topic.last_taught_entity_id,
                "last_taught_entity_surface": kernel.topic.last_taught_entity_surface,
                "last_questioned_attribute": kernel.topic.last_questioned_attribute,
            },
            "discourse_stack": kernel.conversation.discourse_stack,
            "repair_target_turn_id": kernel.conversation.repair_target_turn_id,
            "active_teaching_target": kernel.conversation.active_teaching_target,
            "active_unknown_concept": kernel.conversation.active_unknown_concept,
        }

        result.signals.append(signal)
        result.cost_ms = (time.time() - start) * 1000.0

        # v3.3 Phase 3: Promote ready bindings at end of turn
        promoted = self._semantic_model_store.promote_ready()
        # Route promotion patches through PatchPipeline
        promotion_patches = []
        if hasattr(self._semantic_model_store, 'get_promotion_patches'):
            promotion_patches = self._semantic_model_store.get_promotion_patches()
        if promotion_patches and self._runtime is not None and hasattr(self._runtime, 'patch_router') and self._runtime.patch_router is not None:
            self._runtime.patch_router.route_batch(promotion_patches)

        return result

    def _check_budget(self, kernel: ContextKernel, start: float) -> None:
        elapsed = (time.time() - start) * 1000.0
        if elapsed > kernel.budget.latency_target_ms:
            working_ids = kernel.memory.working_signal_ids
            if len(working_ids) > kernel.budget.max_entities:
                kernel.memory.working_signal_ids = working_ids[:kernel.budget.max_entities]
            if len(kernel.world.active_claim_ids) > kernel.budget.max_claims:
                kernel.world.active_claim_ids = kernel.world.active_claim_ids[:kernel.budget.max_claims]
