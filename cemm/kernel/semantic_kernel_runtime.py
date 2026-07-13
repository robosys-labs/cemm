"""SemanticKernelRuntime — CPU: single authoritative entrypoint for the semantic cycle.

Wires perception, graph building, attention scheduling, planning, patch
extraction, patch validation, consolidation, and v3.1 response formation
into one orchestrator. Produces a RuntimeCycleResult with the full
architectural trace including ResponseBundle.
"""

from __future__ import annotations
import time
from typing import Any

from .semantic_cpu import SemanticCPU
from .semantic_attention_controller import SemanticAttentionController
from .semantic_program_compiler import SemanticProgramCompiler
from .semantic_obligation_scheduler import SemanticObligationScheduler
from .teaching_frame_manager import TeachingFrameManager
from .relation_frame_compiler import RelationFrameCompiler
from .relation_algebra import RelationAlgebra
from .semantic_query_engine import SemanticQueryEngine
from .operational_meaning_compiler import OperationalMeaningCompiler
from .state_transmutation_compiler import StateTransmutationCompiler
from .operational_causal_router import OperationalCausalRouter
from .obligation_contract_builder import ObligationContractBuilder
from .query_contract_builder import QueryContractBuilder
from .write_contract_builder import WriteContractBuilder
from .reaction_contract_builder import ReactionContractBuilder
from .operational_contract_compiler import OperationalContractCompiler
from .situation_frame_builder import SituationFrameBuilder
from .state_occupancy_compiler import StateOccupancyCompiler
from .state_delta_compiler import StateDeltaCompiler
from ..response.response_formation_engine import ResponseFormationEngine
from ..response.types import ResponseSituation, ResponseBundle, WriteOutcome, BudgetFrame, StyleVector, TemperatureState, ResponseEvidencePacket
from .session_store import SessionStore
from ..causal.causal_bridge import CausalBridge
from ..learning.patch_validator import PatchValidator
from ..learning.patch_committer import PatchCommitter
from ..memory.predicate_schema_store import PredicateSchemaStore
from ..memory.durable_semantic_store import DurableSemanticStore
from ..types.runtime_cycle import RuntimeCycleResult
from ..types.obligation_contract import QueryContract, WriteContract, ReactionContract
from ..types.obligation_frame import ObligationFrame


class SemanticKernelRuntime:
    """CPU — single authoritative entrypoint for the semantic runtime cycle.

    Wires all core components into one orchestrator. Use run_turn() to
    process a signal through the full cycle.
    """

    def __init__(
        self,
        concept_lattice: Any | None = None,
        construction_lattice: Any | None = None,
        episodic_store: Any | None = None,
        auto_consolidate: bool = False,
        lexeme_memory: Any | None = None,
        registry: Any | None = None,
        semantic_model_store: Any | None = None,
    ) -> None:
        self.concept_lattice = concept_lattice
        self.construction_lattice = construction_lattice
        self.episodic_store = episodic_store
        self.auto_consolidate = auto_consolidate

        # Reuse SemanticCPU for core component wiring — avoids duplicating
        # MeaningGraphBuilder, MeaningPerceptor, ActResolutionPlanner,
        # GraphPatchExtractor, ConceptConsolidator setup
        from .semantic_schema_kernel import get_kernel
        self._predicate_schema_store = PredicateSchemaStore()
        self._cpu = SemanticCPU(
            concept_lattice=concept_lattice,
            construction_lattice=construction_lattice,
            episodic_store=episodic_store,
            auto_consolidate=auto_consolidate,
            schema_kernel=get_kernel(),
            predicate_schema_store=self._predicate_schema_store,
        )

        # Expose SemanticCPU's public attributes for Pipeline cherry-picking
        self.graph_builder = self._cpu.graph_builder
        self.perceptor = self._cpu.perceptor
        self.planner = self._cpu.planner
        self.patch_extractor = self._cpu.patch_extractor
        self.consolidator = self._cpu.consolidator

        # Durable semantic store — created early so PatchValidator can reference it
        self._durable_semantic_store = DurableSemanticStore()
        self._durable_semantic_store.set_schema_store(self._predicate_schema_store)

        # Phase 3-4 additions
        self._attention = SemanticAttentionController()
        self._patch_validator = PatchValidator(
            store=self._durable_semantic_store,
            schema_store=self._predicate_schema_store,
        )

        # v4.2: Semantic program compilation, obligation scheduling, teaching frames
        self._program_compiler = SemanticProgramCompiler()
        self._obligation_scheduler = SemanticObligationScheduler()
        self._teaching_frame_manager = TeachingFrameManager()
        self._operational_meaning_compiler = OperationalMeaningCompiler()
        self._state_transmutation_compiler = StateTransmutationCompiler()
        self._operational_causal_router = OperationalCausalRouter()
        self._obligation_contract_builder = ObligationContractBuilder()
        self._query_contract_builder = QueryContractBuilder()
        self._write_contract_builder = WriteContractBuilder()
        self._reaction_contract_builder = ReactionContractBuilder()
        self._contract_compiler = OperationalContractCompiler()
        self._situation_frame_builder = SituationFrameBuilder()
        self._state_occupancy_compiler = StateOccupancyCompiler()
        self._state_delta_compiler = StateDeltaCompiler()

        # v4.2: Relation frames, predicate schemas, relation algebra
        self._relation_frame_compiler = RelationFrameCompiler(
            predicate_schema_store=self._predicate_schema_store,
        )
        self._relation_algebra = RelationAlgebra(self._predicate_schema_store)
        self._query_engine = SemanticQueryEngine(self._relation_algebra, self._predicate_schema_store)
        self._response_engine = ResponseFormationEngine()

        # Patch committer (Phase 8 breakthrough)
        self._patch_committer = PatchCommitter(self._durable_semantic_store)

        # Single-authority session state
        self._session_store = SessionStore()

        # Causal bridge — queries DurableSemanticStore directly
        self._causal_bridge = CausalBridge(self._durable_semantic_store)

        # 3.3 shadow components — trace-only; do not affect behavior
        self._lexeme_memory = lexeme_memory
        from ..learning.semantic_gap_detector import SemanticGapDetector
        from ..learning.learning_episode_manager import LearningEpisodeManager
        from ..learning.lexeme_candidate_index import LexemeCandidateIndex
        from ..learning.learning_question_planner import LearningQuestionPlanner
        from ..learning.learning_answer_assimilator import LearningAnswerAssimilator
        from .predicate_activation_resolver import PredicateActivationResolver
        from .entity_grounding_resolver import EntityGroundingResolver
        from .interpretation_lattice import InterpretationLattice
        from .interpretation_resolver import InterpretationResolver
        from .obligation_graph_builder import ObligationGraphBuilder

        self._semantic_gap_detector = SemanticGapDetector()
        self._predicate_activation_resolver = PredicateActivationResolver()
        self._entity_grounding_resolver = EntityGroundingResolver()
        self._interpretation_lattice = InterpretationLattice()
        self._interpretation_resolver = InterpretationResolver()
        self._obligation_graph_builder = ObligationGraphBuilder()
        self._learning_episode_manager = LearningEpisodeManager()
        self._lexeme_candidate_index = LexemeCandidateIndex()
        self._learning_question_planner = LearningQuestionPlanner()
        self._learning_answer_assimilator = LearningAnswerAssimilator()

        # Conversation act classifier — wired when registry is available
        self._act_classifier = None
        if registry is not None:
            from .conversation_act_classifier import ConversationActClassifier
            self._act_classifier = ConversationActClassifier(
                registry=registry,
                semantic_model_store=semantic_model_store,
            )

    @property
    def attention(self):
        """Expose the SemanticAttentionController for Pipeline use."""
        return self._attention

    @property
    def program_compiler(self) -> SemanticProgramCompiler:
        return self._program_compiler

    @property
    def obligation_scheduler(self) -> SemanticObligationScheduler:
        return self._obligation_scheduler

    @property
    def teaching_frame_manager(self) -> TeachingFrameManager:
        return self._teaching_frame_manager

    @property
    def relation_frame_compiler(self) -> RelationFrameCompiler:
        return self._relation_frame_compiler

    @property
    def relation_algebra(self) -> RelationAlgebra:
        return self._relation_algebra

    @property
    def predicate_schema_store(self) -> PredicateSchemaStore:
        return self._predicate_schema_store

    @property
    def query_engine(self) -> SemanticQueryEngine:
        return self._query_engine

    @property
    def response_engine(self) -> ResponseFormationEngine:
        return self._response_engine

    @property
    def durable_semantic_store(self) -> DurableSemanticStore:
        return self._durable_semantic_store

    @property
    def patch_committer(self) -> PatchCommitter:
        return self._patch_committer

    @property
    def session_store(self) -> SessionStore:
        return self._session_store

    def run_text(
        self,
        text: str,
        context_id: str | None = None,
        source_id: str = "user",
    ) -> RuntimeCycleResult:
        import uuid
        from ..types.signal import Signal, SignalKind, SourceType
        from ..types.permission import Permission
        from .context_kernel_builder import ContextKernelBuilder
        from .text_normalizer import TextNormalizer

        now = time.time()
        signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.INPUT,
            source_id=source_id,
            source_type=SourceType.USER,
            content=text,
            observed_at=now,
            context_id=context_id or uuid.uuid4().hex[:16],
            salience=0.8,
            trust=0.8,
            permission=Permission.public(),
        )
        signal.normalized = TextNormalizer().normalize(signal.content)

        builder = ContextKernelBuilder()
        turn_index = self._session_store.next_turn_index(signal.context_id)
        kernel = builder.from_signal(signal, turn_index=turn_index)
        kernel.latest_signal = signal

        return self.run_turn(signal, kernel)

    def run_turn(
        self,
        signal: Any,
        kernel: Any,
        *,
        percept: Any | None = None,
        retrieval_plan: Any | None = None,
        safety_frame: Any | None = None,
        situation: Any | None = None,
    ) -> RuntimeCycleResult:
        start = time.monotonic()
        result = RuntimeCycleResult(signal=signal, context_kernel=kernel)
        errors: list[str] = []

        # 0. Session restore — hydrate kernel from prior turn state
        try:
            self._session_store.restore(kernel, signal)
            # Restore teaching frame for this context
            frame_data = self._session_store.load_teaching_frame(signal.context_id)
            if frame_data is not None:
                self._teaching_frame_manager.from_session_dict(signal.context_id, frame_data)
            learning_data = self._session_store.load_learning_state(signal.context_id)
            if learning_data:
                manager_data = learning_data.get("episode_manager", learning_data)
                self._learning_episode_manager.restore_context(signal.context_id, manager_data)
        except Exception as e:
            errors.append(f"session restore failed: {e}")

        # 1. Perceive
        try:
            if percept is None:
                percept = self._cpu.perceptor.perceive(signal, kernel)
            result.percept = percept
            # Consume answers to obligations that were actually asked on a
            # prior turn before detecting or creating new gaps.
            for episode, obligation in self._learning_episode_manager.pending_obligations(signal.context_id):
                if obligation.created_turn_signal_id == getattr(signal, "id", ""):
                    continue
                fields = self._learning_answer_assimilator.assimilate(
                    episode, obligation, getattr(signal, "content", "") or "", percept,
                )
                if fields and self._learning_episode_manager.apply_answer_fields(
                    episode.episode_id, obligation.obligation_id, fields,
                    evidence_signal_id=getattr(signal, "id", ""),
                ):
                    result.learning_answer_fields.extend(fields)
        except Exception as e:
            errors.append(f"perceive failed: {e}")
            result.cost_ms = (time.monotonic() - start) * 1000
            result.diagnostics = {"errors": errors}
            return result

        # 1a-pre. Classify conversation acts (before planning)
        conversation_act = None
        if self._act_classifier is not None:
            try:
                pre_graph = getattr(percept, "uol_graph", None)
                uol_atoms_for_classify = list(pre_graph.atoms.values()) if pre_graph else None
                conversation_act = self._act_classifier.classify(
                    signal=signal,
                    kernel=kernel,
                    uol_atoms=uol_atoms_for_classify,
                    meaning_percept=percept,
                    situation_frame=situation,
                    safety_frame=safety_frame,
                )
            except Exception as e:
                errors.append(f"conversation act classify failed: {e}")

        # 1a. Update user affect from detected affect markers
        try:
            from .pragmatic_interpreter import update_user_affect, affect_markers_to_semantics
            affect_markers = getattr(percept, "affect_markers", None)
            if affect_markers:
                semantics = affect_markers_to_semantics(affect_markers, signal.id)
                kernel.user.affect = update_user_affect(
                    kernel.user.affect, semantics, kernel, signal.id,
                )
        except Exception as e:
            errors.append(f"affect update failed: {e}")

        # 1b. Update entity salience from perception trace
        try:
            salience_map = percept.perception_trace.get("salience_map", {})
            if salience_map and hasattr(kernel, "conversation"):
                kernel.conversation.entity_salience = dict(salience_map)
        except Exception as e:
            errors.append(f"salience update failed: {e}")

        # 2. Build working graph
        try:
            uol_graph = getattr(percept, "uol_graph", None)
            if uol_graph is None:
                uol_graph = self._cpu.graph_builder.build(percept)
                if hasattr(percept, "uol_graph"):
                    percept.uol_graph = uol_graph
            result.uol_graph = uol_graph
        except Exception as e:
            errors.append(f"build failed: {e}")
            result.cost_ms = (time.monotonic() - start) * 1000
            result.diagnostics = {"errors": errors}
            return result

        # 2c. 3.3: semantic gap detection, lexeme candidates
        try:
            known = set()
            if self._lexeme_memory is not None:
                known = {m.surface.lower() for m in self._lexeme_memory.all()}
            gaps = self._semantic_gap_detector.detect(
                percept, uol_graph, known_forms=known,
            )
            result.semantic_gaps = gaps

            tokens = getattr(percept, "tokens", []) or []
            for t in tokens:
                surface = t if isinstance(t, str) else getattr(t, "surface", str(t))
                lang = getattr(percept, "language", "en")
                self._lexeme_candidate_index.index_candidate(
                    lang, surface,
                    {"surface": surface, "lemma": surface.lower(), "form": surface},
                )
        except Exception as e:
            errors.append(f"3.3 gap detection failed: {e}")

        # 2a. Causal inference predictions via bridge
        try:
            causal_preds = self._causal_bridge.predict(
                graph=uol_graph, kernel=kernel,
            )
            for pred in causal_preds:
                uol_graph.add_affordance_prediction(pred)
        except Exception as e:
            errors.append(f"causal bridge failed: {e}")

        # 2b. Build situation frame from percept + kernel
        try:
            situation_frame = self._situation_frame_builder.build(percept, kernel)
            result.situation_frame = situation_frame
        except Exception as e:
            errors.append(f"situation frame build failed: {e}")
            situation_frame = None

        # 2d. 3.3 Shadow: entity grounding + interpretation lattice
        try:
            active_ids = set(
                getattr(kernel.world, "active_entity_ids", [])
                if kernel is not None and hasattr(kernel, "world") else []
            )
            salience = (
                getattr(kernel.conversation, "entity_salience", {})
                if kernel is not None and hasattr(kernel, "conversation") else {}
            )
            known_entities: dict[str, Any] = {
                eid: {"surface": eid.split(":")[-1] if ":" in eid else eid, "name": eid}
                for eid in active_ids
            }
            groundings = []
            for ref in getattr(percept, "referents", []) or []:
                surface = getattr(ref, "surface", str(ref))
                eid, status = self._entity_grounding_resolver.resolve(
                    surface, getattr(ref, "entity_type", "entity"), known_entities, salience,
                )
                groundings.append({"surface": surface, "entity_id": eid, "status": status.value})
            result.entity_groundings = groundings
        except Exception as e:
            errors.append(f"3.3 entity grounding shadow failed: {e}")

        try:
            self._interpretation_lattice.clear()
            from .interpretation_lattice import InterpretationBranch
            groups = getattr(percept, "meaning_groups", []) or []
            for group in groups:
                gid = getattr(group, "id", "") or getattr(group, "group_id", "")
                if not gid:
                    continue
                candidate_types = getattr(group, "candidate_act_types", []) or []
                frame_type = candidate_types[0] if candidate_types else ""
                intents = getattr(group, "intents", []) or []
                modality = getattr(intents[0], "modality", "observed") if intents else "observed"
                polarity = getattr(intents[0], "polarity", "affirmed") if intents else "affirmed"
                from .predicate_activation_resolver import PredicateActivationResolver
                scope = PredicateActivationResolver.extract_scope(
                    [getattr(g, "group_type", "") for g in groups],
                    modality, polarity,
                )
                branch = InterpretationBranch(
                    branch_id=f"br_{gid}",
                    group_id=gid,
                    language_tag=getattr(percept, "language", "und"),
                    frame_type=frame_type,
                    scope=scope,
                )
                self._interpretation_lattice.add_branch(branch)
            result.interpretation_lattice = self._interpretation_lattice
            result.interpretation_resolution = self._interpretation_resolver.resolve(
                self._interpretation_lattice,
            )
        except Exception as e:
            errors.append(f"3.3 interpretation lattice failed: {e}")

        # 2d-i. Branch-aware blocking gap classification (3.3 S2)
        try:
            selected_branch_ids = set(result.interpretation_resolution.get("selected_branches", []))
            selected_group_ids = {
                b.group_id for b in self._interpretation_lattice.all_branches()
                if b.branch_id in selected_branch_ids
            }
            blocking_search = selected_branch_ids | selected_group_ids
            blocking = self._semantic_gap_detector.classify_blocking(
                result.semantic_gaps, blocking_search,
            )
            if blocking and hasattr(signal, "context_id"):
                episode = self._learning_episode_manager.create_episode(
                    signal.context_id, blocking,
                )
                result.active_learning_episodes = [episode]
                asked: set[str] = set()
                for ep in self._learning_episode_manager.get_active_episodes(signal.context_id):
                    asked.update(ep.asked_fields)
                blocking_ids = {g.gap_id for g in blocking}
                question = self._learning_question_planner.plan(
                    result.semantic_gaps, [], asked, blocking_ids,
                )
                if question is not None:
                    result.learning_questions = [question]
        except Exception as e:
            errors.append(f"3.3 blocking gap classification failed: {e}")

        # Learning answers were consumed immediately after perception from
        # prior-turn pending obligations. Never assimilate a newly planned
        # question against the same percept.

        # 2e. Predicate activation — pre-operational gate (3.3 S1, S3)
        activated_group_ids: set[str] = set()
        try:
            from .predicate_activation_resolver import PredicateActivationFrame, PredicateStatus
            selected_branch_ids = set(result.interpretation_resolution.get("selected_branches", []))
            activation_candidates: list[PredicateActivationFrame] = []
            for branch in self._interpretation_lattice.all_branches():
                if branch.branch_id not in selected_branch_ids:
                    continue
                pf = PredicateActivationFrame(
                    predicate_id=f"pred_{branch.group_id}",
                    group_id=branch.group_id,
                    predicate_key=branch.frame_type,
                    predicate_surface=getattr(branch, "lexical_sense_ids", "") and branch.lexical_sense_ids[0] or "",
                    language_tag=branch.language_tag,
                    scope=branch.scope,
                    status=PredicateStatus.CANDIDATE,
                    branch_id=branch.branch_id,
                )
                activation_candidates.append(pf)
            activated = self._predicate_activation_resolver.resolve(activation_candidates, set())
            result.predicate_activations = activated
            activated_group_ids = {pf.group_id for pf in activated}
            result.activated_frame_ids = [pf.predicate_id for pf in activated]
        except Exception as e:
            errors.append(f"predicate activation gate failed: {e}")

        # 3. Attend — select focus (Phase 3)
        try:
            budget = getattr(kernel, "budget", None) if kernel is not None else None
            working_set = self._attention.attend(uol_graph, kernel, budget)
            result.working_set = working_set
        except Exception as e:
            errors.append(f"attend failed: {e}")

        # 3a. Compile semantic program (v4.2)
        semantic_program = None
        try:
            semantic_program = self._program_compiler.compile(uol_graph, percept, kernel)
        except Exception as e:
            errors.append(f"compile program failed: {e}")

        # 3b. Preliminary safety detection from graph (for arbitration preemption)
        from .safety_frame_detector import SafetyFrameDetector
        safety_detector = SafetyFrameDetector()
        try:
            safety_frame = safety_detector.detect(
                situation=result.situation_frame,
                valences=getattr(percept, 'valences', []) if percept else [],
                uol_graph=uol_graph,
            )
        except Exception as e:
            errors.append(f"safety detection failed: {e}")
            safety_frame = None

        # 3c. Compile operational meaning/state/effect/obligation contracts
        obligation_frame = None
        obligation_contract = None
        operational_frames: list[Any] = []
        meaning_arbitration = None
        state_transmutations: list[Any] = []
        operational_effects: list[Any] = []
        try:
            affordance_predictions = getattr(uol_graph, "affordance_predictions", []) or []
            if semantic_program is not None:
                operational_frames = self._operational_meaning_compiler.compile(
                    uol_graph, semantic_program, affordance_predictions=affordance_predictions,
                )
                meaning_arbitration = self._operational_meaning_compiler.arbitrate(
                    operational_frames, safety_frame=safety_frame,
                )
                selected_frames = [
                    frame for frame in operational_frames
                    if frame.frame_id in set(meaning_arbitration.selected_frame_ids)
                ] or operational_frames[:1]

                # 3c-0. Filter by activated groups (3.3 S1 — predicate activation gate)
                if activated_group_ids:
                    selected_frames = [
                        frame for frame in selected_frames
                        if getattr(frame, "group_id", "") in activated_group_ids
                    ]

                # 3c-i. Compile state occupancy frames (entity current states)
                occupancy_frames = self._state_occupancy_compiler.compile(
                    uol_graph, kernel,
                )

                # 3c-ii. Compile state delta frames (proposed changes from graph)
                delta_frames = self._state_delta_compiler.compile(
                    uol_graph, selected_frames,
                )

                # 3c-iii. Compile state transmutations (from frames + deltas + occupancy)
                state_transmutations = self._state_transmutation_compiler.compile(
                    uol_graph, selected_frames,
                    delta_frames=delta_frames,
                    occupancy_frames=occupancy_frames,
                )

                # 3c-iv. Authoritative safety detection from transmutations
                try:
                    authoritative_safety = safety_detector.detect(
                        transmutations=state_transmutations,
                        occupancy_frames=occupancy_frames,
                        situation=result.situation_frame,
                        uol_graph=uol_graph,
                    )
                    if authoritative_safety is not None:
                        safety_frame = authoritative_safety
                except Exception as e:
                    errors.append(f"authoritative safety detection failed: {e}")

                operational_effects = self._operational_causal_router.route(
                    selected_frames,
                    state_transmutations,
                    affordance_predictions=affordance_predictions,
                    safety_frame=safety_frame,
                )

                # 3c-vii. Build obligation graph BEFORE contract compilation (3.3)
                try:
                    gaps = result.semantic_gaps
                    blocking_ids: set[str] = set()
                    for ep in result.active_learning_episodes:
                        blocking_ids.update(ep.target_gap_ids)
                    ob_graph = self._obligation_graph_builder.build(
                        operational_frames, gaps, blocking_ids,
                    )
                    result.obligation_graph = ob_graph
                except Exception as e:
                    errors.append(f"obligation graph build failed: {e}")

                obligation_contract = self._contract_compiler.compile(
                    frames=operational_frames,
                    arbitration=meaning_arbitration,
                    effects=operational_effects,
                    safety_frame=safety_frame,
                    state_transmutations=state_transmutations,
                    obligation_graph=result.obligation_graph,
                    gaps=result.semantic_gaps,
                    episodes=result.active_learning_episodes,
                    durable_store=self._durable_semantic_store,
                    graph=uol_graph,
                    percept=percept,
                )
                obligation_frame = self._obligation_frame_from_contract(
                    obligation_contract,
                    semantic_program,
                    operational_frames,
                )

                # 3c-viii. Authorize transmutations AFTER contract compilation (3.3 S4)
                try:
                    from .transmutation_authorizer import TransmutationAuthorizer
                    authorizer = TransmutationAuthorizer()
                    contract_prov = {
                        "frame_id": getattr(obligation_contract, "contract_id", ""),
                        "obligation_graph": getattr(result.obligation_graph, "graph_id", ""),
                    }
                    auth_results = [
                        authorizer.authorize(stm, contract_prov)
                        for stm in state_transmutations
                    ]
                    result.transmutation_authorizations = auth_results
                    # Filter: only authorized transmutations proceed downstream
                    authorized_ids = {
                        ar.transmutation_id for ar in auth_results if ar.authorized
                    }
                    state_transmutations = [
                        stm for stm in state_transmutations
                        if stm.transmutation_id in authorized_ids
                    ]
                except Exception as e:
                    errors.append(f"transmutation authorization failed: {e}")
        except Exception as e:
            errors.append(f"compile operational contract failed: {e}")

        result.operational_meaning_frames = operational_frames
        result.meaning_arbitration = meaning_arbitration
        result.state_transmutations = state_transmutations
        result.operational_effects = operational_effects
        result.obligation_contract = obligation_contract

        # 3.3 Phase 11 shadow: execution ledger + learning use observer
        try:
            from .turn_execution_planner import TurnExecutionPlanner
            from .contract_executor import ContractExecutor
            from ..learning.learning_use_observer import LearningUseObserver

            planner = TurnExecutionPlanner()
            ob_graph = result.obligation_graph
            plan_steps = planner.plan(ob_graph, obligation_contract)

            executor = ContractExecutor()
            turn_id = getattr(signal, "id", "")
            session_id = getattr(kernel, "session_id", "")
            result.execution_ledger = executor.execute(
                plan_steps, obligation_contract,
                turn_id=turn_id, session_id=session_id,
            )

            observer = LearningUseObserver()
            episode_ids = [ep.episode_id for ep in result.active_learning_episodes]
            use_outcomes: list[Any] = []
            for entry in result.execution_ledger.entries:
                if entry.status == "succeeded" and entry.operation_type in ("query", "write"):
                    for eid in episode_ids:
                        outcomes = observer.observe_use_success(
                            hypothesis_id=eid,
                            use_type=entry.operation_type,
                            confidence=0.7,
                        )
                        use_outcomes.extend(outcomes)
            result.learning_use_outcomes = use_outcomes
        except Exception as e:
            errors.append(f"3.3 execution ledger shadow failed: {e}")

        # 3d. Process teaching frame (v4.2)
        try:
            self._teaching_frame_manager.process_turn(
                semantic_program, uol_graph, kernel, signal.id,
            )
        except Exception as e:
            errors.append(f"teaching frame failed: {e}")

        # 3c-i. Update topic state from active teaching frame
        active_teaching = self._teaching_frame_manager.active_frame
        if active_teaching is not None and hasattr(kernel, 'topic'):
            kernel.topic.active_topic_surface = active_teaching.target_concept_key
            kernel.topic.active_topic_entity_id = active_teaching.target_concept_id or active_teaching.target_concept_key
            kernel.topic.last_taught_entity_surface = active_teaching.target_concept_key
            kernel.topic.last_taught_entity_id = active_teaching.target_concept_id or active_teaching.target_concept_key
            kernel.topic.last_updated_signal_id = signal.id
            kernel.topic.last_updated_at = signal.observed_at

        # 3d. Compile relation frames (v4.2) + query-driven durable retrieval
        relation_frames: list[Any] = []
        semantic_query = None
        answer_binding = None
        try:
            turn_frames = self._relation_frame_compiler.compile(uol_graph)

            query_contract = getattr(obligation_contract, "query_contract", None) if obligation_contract is not None else None
            if query_contract is not None:
                semantic_query, relation_frames, answer_binding = self._query_engine.execute_contract(
                    query_contract, obligation_frame,
                    turn_frames=turn_frames,
                    durable_store=self._durable_semantic_store,
                )
            else:
                relation_frames = turn_frames
        except Exception as e:
            errors.append(f"compile relations failed: {e}")

        # 3d-iii. Induce predicate schemas from observed relation frames
        try:
            from ..learning.predicate_schema_inductor import PredicateSchemaInductor
            inductor = PredicateSchemaInductor()
            inductor.induct_from_frames(relation_frames, self._predicate_schema_store)
        except Exception as e:
            errors.append(f"induce predicate schemas failed: {e}")

        # 3e. Execute semantic query → answer binding (v4.2)
        # Query execution occurs above through the v3.2 QueryContract.

        # Promote v4.2 outputs to first-class fields
        result.semantic_program = semantic_program
        result.obligation_frame = obligation_frame
        result.relation_frames = relation_frames
        result.semantic_query = semantic_query
        result.answer_binding = answer_binding

        # 4. Plan
        try:
            act_plan = self._cpu.planner.plan(
                conversation_act=conversation_act,
                situation=situation,
                safety_frame=safety_frame,
                meaning_percept=percept,
                retrieval_plan=retrieval_plan,
            )
            result.act_plan = act_plan
        except Exception as e:
            errors.append(f"plan failed: {e}")

        # 5. Extract patches
        try:
            patches = list(self._cpu.patch_extractor.extract(
                uol_graph,
                operational_frames,
                obligation_contract,
            ))
            result.patch_candidates = patches
        except Exception as e:
            errors.append(f"extract failed: {e}")
            patches = []

        # 6. Validate patches (Phase 4)
        for patch in patches:
            try:
                validation = self._patch_validator.validate(patch, kernel, current_signal=signal)
                result.validation.append(validation)
            except Exception as e:
                errors.append(f"validate patch {patch.id}: {e}")
                from ..learning.patch_validator import PatchValidationResult, ValidationCheck
                result.validation.append(PatchValidationResult(
                    patch_id=patch.id,
                    status="rejected",
                    reasons=[str(e)],
                    failed_checks=["validate_exception"],
                    check_results=[ValidationCheck("validate_exception", False, 0.0, str(e))],
                ))

        # 6a. Commit validated patches to durable store (Phase 8 breakthrough)
        commit_results: list[Any] = []
        if result.validation:
            try:
                commit_results = self._patch_committer.commit_batch(patches, result.validation)
            except Exception as e:
                errors.append(f"commit patches failed: {e}")

        # 7. Consolidate (Phase 4 — only if auto)
        if self.auto_consolidate and patches:
            try:
                consolidation = self._cpu.consolidator.consolidate(patches, source_graph=uol_graph)
                result.consolidation = [consolidation]
            except Exception as e:
                errors.append(f"consolidate failed: {e}")

        # 8. Safety is now integrated into the obligation contract at step 3c
        # via arbitration preemption + safety_frame parameter to the contract
        # builder. No post-hoc override needed. (v3.1 invariant #2 — safety is a gate)

        # 8a. Build WriteOutcome from commit results (v3.1 invariant #3)
        write_outcome = self._build_write_outcome(commit_results, patches, obligation_contract)

        # 8b. Build ResponseSituation from all prior pipeline outputs
        turn_index = kernel.conversation.turn_index
        is_first_turn = turn_index <= 1
        evidence_packet = ResponseEvidencePacket.from_runtime(
            semantic_query=semantic_query,
            answer_binding=answer_binding,
            relation_frames=relation_frames,
        )
        style_state, temperature_state = self._state_from_reaction_contract(
            getattr(obligation_contract, "reaction_contract", None) if obligation_contract is not None else None,
        )
        response_situation = ResponseSituation(
            obligation_frame=obligation_frame,
            answer_binding=answer_binding,
            evidence=evidence_packet,
            semantic_program=semantic_program,
            relation_frames=relation_frames,
            semantic_query=semantic_query,
            uol_graph=uol_graph,
            safety_frame=safety_frame,
            write_outcome=write_outcome,
            budget_frame=BudgetFrame(),
            style=style_state,
            temperature=temperature_state,
            signal=signal,
            kernel=kernel,
            percept=percept,
            is_first_turn=is_first_turn,
            conversation_turn_index=turn_index,
        )

        # 8c. Form response via ResponseFormationEngine (canonical v3.1 path)
        try:
            bundle = self._response_engine.form(response_situation)
            result.realized_output = bundle.text
            result.response_bundle = bundle
            # Register only a learning question that was actually realized as
            # a clarification. Planned-but-unasked questions do not own the
            # next user turn.
            if result.learning_questions and any(
                getattr(move, "move_type", "") == "clarify" for move in bundle.moves
            ):
                question = result.learning_questions[0]
                active_episodes = self._learning_episode_manager.get_active_episodes(signal.context_id)
                if active_episodes:
                    from ..types.learning_episode import LearningObligation
                    episode = active_episodes[0]
                    obligation = LearningObligation(
                        obligation_id=question.obligation_id,
                        episode_id=episode.episode_id,
                        gap_ids=tuple(question.gap_ids),
                        question_act=question.question_act,
                        expected_answer_schema=dict(question.expected_answer_schema),
                        resumes_obligation_ids=tuple(question.resumes_obligation_ids),
                        utility=question.utility,
                        created_turn_signal_id=getattr(signal, "id", ""),
                    )
                    self._learning_episode_manager.register_obligation(episode.episode_id, obligation)
        except Exception as e:
            errors.append(f"response formation failed: {e}")

        # 8a. Update conversation state from realized output
        from .output_state_updater import OutputStateUpdater
        output_updater = OutputStateUpdater()
        try:
            output_update = output_updater.update(
                kernel=kernel,
                output_text=result.realized_output or "",
                output_signal_id=signal.id if hasattr(signal, 'id') else "",
                assistant_intent=getattr(result.obligation_frame, 'obligation_kind', '') if result.obligation_frame else '',
                response_mode=getattr(result.obligation_frame, 'response_mode', '') if result.obligation_frame else '',
                obligation_contract=result.obligation_contract,
                response_bundle=result.response_bundle,
            )
            output_updater.apply(kernel, output_update)
        except Exception as e:
            errors.append(f"output state update failed: {e}")

        # 8b. Error attribution — lightweight pass
        from .error_attribution_engine import ErrorAttributionEngine
        ea_engine = ErrorAttributionEngine()
        try:
            discourse_stack = getattr(kernel, 'conversation', None)
            ea_result = ea_engine.evaluate(
                reaction_signal=None,
                conversation_act=None,
                discourse_stack=discourse_stack.discourse_stack if discourse_stack else None,
                decision_packet=None,
                realization_metadata={"realized_output": result.realized_output} if result.realized_output else None,
            )
            if ea_result is not None and result.diagnostics:
                if isinstance(result.diagnostics, dict):
                    result.diagnostics["error_attribution"] = {
                        "error_type": ea_result.error_type,
                        "confidence": ea_result.confidence,
                    }
            # Decay error rate on non-error turns so EMA doesn't monotonically increase
            if ea_result is None and kernel.self_view:
                ea_engine.record_success(kernel.self_view)
        except Exception as e:
            errors.append(f"error attribution failed: {e}")

        result.cost_ms = (time.monotonic() - start) * 1000
        diag: dict[str, Any] = {}
        if errors:
            diag["errors"] = errors
        if semantic_program is not None:
            diag["semantic_program"] = {
                "entry_kind": semantic_program.diagnostics.get("entry_kind"),
                "instruction_count": len(semantic_program.instructions),
                "entry_instruction_id": semantic_program.entry_instruction_id,
            }
        if obligation_frame is not None:
            diag["obligation_frame"] = {
                "obligation_kind": obligation_frame.obligation_kind,
                "response_mode": obligation_frame.response_mode,
                "evidence_policy": obligation_frame.evidence_policy,
                "write_policy": obligation_frame.write_policy,
                "suppressed_count": len(obligation_frame.suppressed_obligations),
                "blocked_by": obligation_frame.blocked_by,
            }
        active_teaching = self._teaching_frame_manager.active_frame
        if active_teaching is not None:
            diag["teaching_frame"] = {
                "frame_id": active_teaching.frame_id,
                "target_concept_key": active_teaching.target_concept_key,
                "open_slots": active_teaching.open_slots,
            }
        if relation_frames:
            diag["relation_frames"] = {
                "count": len(relation_frames),
                "keys": [f.relation_key for f in relation_frames],
            }
        if semantic_query is not None:
            diag["semantic_query"] = {
                "query_id": semantic_query.query_id,
                "query_kind": semantic_query.query_kind,
                "relation_key": semantic_query.relation_key,
            }
        if answer_binding is not None:
            diag["answer_binding"] = {
                "has_answer": answer_binding.has_answer,
                "slot_count": len(answer_binding.slot_fills),
                "confidence": answer_binding.confidence,
                "abstention_reason": answer_binding.abstention_reason,
            }
        if commit_results:
            diag["patch_commit"] = {
                "count": len(commit_results),
                "committed": sum(1 for c in commit_results if c.status == "committed"),
                "durable_relations": self._durable_semantic_store.relation_count(),
            }
        if diag:
            result.diagnostics = diag

        # 9. Session persist — snapshot kernel state for next turn
        try:
            self._session_store.persist(kernel, signal)
            frame_data = self._teaching_frame_manager.to_session_dict(signal.context_id)
            self._session_store.save_teaching_frame(signal.context_id, frame_data)
            self._session_store.save_learning_state(
                signal.context_id,
                {
                    "episode_manager": self._learning_episode_manager.context_to_dict(signal.context_id),
                },
            )
        except Exception as e:
            errors.append(f"session persist failed: {e}")
            if result.diagnostics is None:
                result.diagnostics = {"errors": errors}
            elif isinstance(result.diagnostics, dict):
                result.diagnostics.setdefault("errors", []).append(f"session persist failed: {e}")

        return result

    def _obligation_frame_from_contract(
        self,
        contract: Any,
        program: Any | None,
        frames: list[Any],
    ) -> ObligationFrame:
        entry = getattr(program, "entry_instruction", None) if program is not None else None
        primary_id = getattr(entry, "instruction_id", "") or getattr(contract, "primary_meaning_frame_id", "")
        kind_map = {
            "store_profile": "store_patch",
            "store_teaching": "store_patch",
            "store_correction": "store_patch",
            "memory_command": "store_patch",
            "answer_concept_definition": "answer_concept",
            "answer_user_profile": "answer_user_profile",
            "answer_self_identity": "answer_self_identity",
            "answer_self_capability": "answer_self_capability",
            "answer_self_knowledge": "answer_self_knowledge",
            "apply_style_feedback": "acknowledge_emotional_context",
            "apply_response_feedback": "repair",
            "acknowledge_emotional_context": "acknowledge_emotional_context",
            "social_reply": "social_reply",
            "exit": "exit",
            "safety_refusal": "safety_refusal",
            "ask_clarification": "ask_clarification",
            "abstain": "abstain_policy",
            "repair": "repair",
        }
        mode_map = {
            "confirm_write": "store_confirmation",
            "answer": "evidence_answer",
            "acknowledge": "emotional_response",
            "exit": "session_exit",
            "refuse": "safety_refusal",
            "social": "social_response",
            "clarify": "clarification",
            "abstain": "general_conversation",
            "repair": "repair",
        }
        query_contract = getattr(contract, "query_contract", None)
        context = {
            "obligation_contract": contract,
            "operational_meaning_frames": frames,
        }
        return ObligationFrame(
            primary_instruction_id=primary_id,
            obligation_kind=kind_map.get(contract.obligation_kind, "social_reply"),
            response_mode=mode_map.get(contract.response_mode, "general_conversation"),
            evidence_policy=getattr(query_contract, "evidence_policy", "none") if query_contract is not None else "none",
            write_policy=contract.write_policy,
            required_slots=[],
            blocked_by=list(contract.blocked_by),
            child_obligations=list(contract.child_meaning_frame_ids),
            suppressed_obligations=[
                {"meaning_frame_id": frame.frame_id, "frame_type": frame.frame_type, "reason": "not_primary"}
                for frame in frames
                if frame.frame_id != contract.primary_meaning_frame_id
            ],
            confidence=contract.confidence,
            context=context,
        )

    @staticmethod
    def _state_from_reaction_contract(reaction_contract: Any | None) -> tuple[StyleVector, TemperatureState]:
        style = StyleVector()
        temperature = TemperatureState()
        if reaction_contract is None:
            return style, temperature
        for key, delta in getattr(reaction_contract, "style_delta", {}).items():
            if hasattr(style, key):
                current = float(getattr(style, key))
                setattr(style, key, max(0.0, min(1.0, current + float(delta))))
        temperature.conversation_repair_debt = max(
            0.0,
            temperature.conversation_repair_debt + float(getattr(reaction_contract, "repair_debt_delta", 0.0) or 0.0),
        )
        return style, temperature

    def _build_write_outcome(
        self,
        commit_results: list[Any],
        patches: list[Any] | None = None,
        obligation_contract: Any | None = None,
    ) -> WriteOutcome:
        patches = list(patches or [])
        required = list(getattr(obligation_contract, "required_write_target_ids", []) or [])
        if not required:
            for patch in patches:
                required.extend(getattr(patch, "required_operation_target_ids", []) or [])
        if not required and getattr(obligation_contract, "write_contract", None) is not None:
            required.extend(
                operation.target_id
                for patch in patches
                for operation in getattr(patch, "operations", []) or []
                if operation.target_id
            )
        required = list(dict.fromkeys(required))

        committed_targets = list(dict.fromkeys(
            target
            for result in commit_results
            if getattr(result, "status", "") == "committed"
            for target in getattr(result, "operation_target_ids", []) or []
            if target
        ))
        rejected_targets = list(dict.fromkeys(
            target
            for result in commit_results
            for target in getattr(result, "rejected_operation_target_ids", []) or []
            if target
        ))
        committed_records = list(dict.fromkeys(
            record_id
            for result in commit_results
            if getattr(result, "status", "") == "committed"
            for record_id in [
                *getattr(result, "created_records", []),
                *getattr(result, "updated_records", []),
            ]
            if record_id
        ))
        satisfied = bool(required) and set(required) <= set(committed_targets)
        if satisfied:
            status = "committed"
        elif committed_targets:
            status = "conflict"
        elif any(getattr(result, "status", "") == "quarantined" for result in commit_results):
            status = "quarantined"
        elif commit_results:
            status = "rejected"
        else:
            status = "none"
        operation_results = {
            target: "committed" if target in committed_targets else "rejected"
            for target in dict.fromkeys([*required, *committed_targets, *rejected_targets])
        }
        return WriteOutcome(
            patch_count=len(commit_results),
            committed_count=sum(1 for result in commit_results if getattr(result, "status", "") == "committed"),
            rejected_count=sum(1 for result in commit_results if getattr(result, "status", "") == "rejected"),
            quarantined_count=sum(1 for result in commit_results if getattr(result, "status", "") == "quarantined"),
            commit_status=status,
            committed_record_ids=committed_records,
            rejected_patch_ids=rejected_targets,
            rejected_reasons=[
                error for result in commit_results for error in getattr(result, "errors", []) or []
            ],
            required_target_ids=required,
            committed_target_ids=committed_targets,
            operation_results=operation_results,
        )
