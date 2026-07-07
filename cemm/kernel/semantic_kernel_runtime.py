"""SemanticKernelRuntime — CPU: single authoritative entrypoint for the semantic cycle.

Wires perception, graph building, attention scheduling, planning, patch
extraction, patch validation, and consolidation into one orchestrator.
Produces a RuntimeCycleResult with the full architectural trace.
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
from .semantic_realizer import SemanticRealizer
from .session_store import SessionStore
from ..causal.causal_bridge import CausalBridge
from ..learning.patch_validator import PatchValidator
from ..learning.patch_committer import PatchCommitter
from ..memory.predicate_schema_store import PredicateSchemaStore
from ..memory.durable_semantic_store import DurableSemanticStore
from ..types.runtime_cycle import RuntimeCycleResult


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

        # v4.2: Relation frames, predicate schemas, relation algebra
        self._relation_frame_compiler = RelationFrameCompiler(
            predicate_schema_store=self._predicate_schema_store,
        )
        self._relation_algebra = RelationAlgebra(self._predicate_schema_store)
        self._query_engine = SemanticQueryEngine(self._relation_algebra, self._predicate_schema_store)
        self._realizer = SemanticRealizer()

        # Patch committer (Phase 8 breakthrough)
        self._patch_committer = PatchCommitter(self._durable_semantic_store)

        # Single-authority session state
        self._session_store = SessionStore()

        # Causal bridge — queries DurableSemanticStore directly
        self._causal_bridge = CausalBridge(self._durable_semantic_store)

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
    def realizer(self) -> SemanticRealizer:
        return self._realizer

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
        except Exception as e:
            errors.append(f"session restore failed: {e}")

        # 1. Perceive
        try:
            if percept is None:
                percept = self._cpu.perceptor.perceive(signal, kernel)
            result.percept = percept
        except Exception as e:
            errors.append(f"perceive failed: {e}")
            result.cost_ms = (time.monotonic() - start) * 1000
            result.diagnostics = {"errors": errors}
            return result

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

        # 2a. Causal inference predictions via bridge
        try:
            causal_preds = self._causal_bridge.predict(
                graph=uol_graph, kernel=kernel,
            )
            for pred in causal_preds:
                uol_graph.add_affordance_prediction(pred)
        except Exception as e:
            errors.append(f"causal bridge failed: {e}")

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

        # 3b. Schedule obligation (v4.2)
        obligation_frame = None
        try:
            affordance_predictions = getattr(uol_graph, "affordance_predictions", []) or []
            obligation_frame = self._obligation_scheduler.schedule(
                semantic_program, working_set, kernel, uol_graph,
                affordance_predictions=affordance_predictions,
            )
        except Exception as e:
            errors.append(f"schedule obligation failed: {e}")

        # 3c. Process teaching frame (v4.2)
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
        realization_contract = None
        try:
            turn_frames = self._relation_frame_compiler.compile(uol_graph)

            # 3d-i. Build query from turn frames + obligation + program
            # Include durable frames so the query engine can find relation_key
            # for concept queries where the answer is in the durable store.
            if obligation_frame is not None:
                # Retrieve durable frames with broad filter for query building
                pre_durable_frames = self._durable_semantic_store.query_relations(
                    relation_key="",
                ) if self._durable_semantic_store.relation_count() > 0 else []
                all_frames_for_query = turn_frames + pre_durable_frames
                semantic_query = self._query_engine.build_query(
                    obligation_frame, all_frames_for_query, semantic_program, uol_graph,
                )

            # 3d-ii. Retrieve durable frames filtered by query constraints
            durable_relation_key = semantic_query.relation_key if semantic_query else ""
            if not durable_relation_key and obligation_frame is not None:
                durable_relation_key = self._query_engine.preferred_relation_key(
                    obligation_frame.obligation_kind
                )

            if semantic_query is not None:
                durable_frames = self._durable_semantic_store.query_relations(
                    relation_key=durable_relation_key,
                    subject_concept_id=semantic_query.subject_constraint.concept_id,
                    subject_entity_id=semantic_query.subject_constraint.entity_id,
                    object_concept_id=semantic_query.object_constraint.concept_id,
                    object_entity_id=semantic_query.object_constraint.entity_id,
                    allow_inverse=semantic_query.allow_inverse,
                )
            elif durable_relation_key:
                durable_frames = self._durable_semantic_store.query_relations(
                    relation_key=durable_relation_key,
                )
            else:
                durable_frames = []

            # Durable frames last so current-turn frames take priority
            relation_frames = turn_frames + durable_frames
        except Exception as e:
            errors.append(f"compile relations failed: {e}")

        # 3d-iii. Induce predicate schemas from observed relation frames
        try:
            from ..learning.predicate_schema_inductor import PredicateSchemaInductor
            inductor = PredicateSchemaInductor()
            inductor.induct_from_frames(relation_frames, self._predicate_schema_store)
        except Exception as e:
            errors.append(f"induce predicate schemas failed: {e}")

        # 3e. Execute semantic query → answer binding → realization contract (v4.2)
        if semantic_query is not None and obligation_frame is not None:
            try:
                answer_binding = self._query_engine.execute(
                    semantic_query, relation_frames,
                )
                realization_contract = self._query_engine.build_contract(
                    obligation_frame, answer_binding, semantic_program,
                )
            except Exception as e:
                errors.append(f"query engine failed: {e}")

        # 3f. Realize contract → response text (v4.2)
        if realization_contract is not None:
            try:
                result.realized_output = self._realizer.realize(
                    realization_contract, answer_binding,
                )
            except Exception as e:
                errors.append(f"realize failed: {e}")

        # Promote v4.2 outputs to first-class fields
        result.semantic_program = semantic_program
        result.obligation_frame = obligation_frame
        result.relation_frames = relation_frames
        result.semantic_query = semantic_query
        result.answer_binding = answer_binding
        result.realization_contract = realization_contract

        # 4. Plan
        try:
            act_plan = self._cpu.planner.plan(
                conversation_act=None,
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
            patches = list(self._cpu.patch_extractor.extract(uol_graph))
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

        # 8. Lightweight safety check on realized output
        from .safety_frame_detector import SafetyFrameDetector
        safety_detector = SafetyFrameDetector()
        try:
            safety_frame = safety_detector.detect(
                situation=getattr(result, 'situation_frame', None),
                input_text=getattr(signal, 'content', ''),
                valences=getattr(percept, 'valences', []) if percept else [],
            )
            if safety_frame and result.realized_output:
                current_output = result.realized_output.lower()
                safety_phrases = ("cannot help", "can't help", "safety", "refuse", "inappropriate")
                if not any(phrase in current_output for phrase in safety_phrases):
                    result.realized_output = "I cannot help with that request."
                if result.realization_contract:
                    import dataclasses
                    if dataclasses.is_dataclass(result.realization_contract):
                        result.realization_contract = dataclasses.replace(
                            result.realization_contract,
                            abstention_reason="safety_policy",
                        )
                    else:
                        result.realization_contract.abstention_reason = "safety_policy"
        except Exception as e:
            errors.append(f"safety check failed: {e}")

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
        if realization_contract is not None:
            diag["realization_contract"] = {
                "response_mode": realization_contract.response_mode,
                "template_key": realization_contract.template_key,
                "evidence_policy": realization_contract.evidence_policy,
                "unfilled_slots": realization_contract.unfilled_slots,
                "abstention_reason": realization_contract.abstention_reason,
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
        except Exception as e:
            errors.append(f"session persist failed: {e}")
            if result.diagnostics is None:
                result.diagnostics = {"errors": errors}
            elif isinstance(result.diagnostics, dict):
                result.diagnostics.setdefault("errors", []).append(f"session persist failed: {e}")

        return result
