"""SemanticKernelRuntime — CPU: single authoritative entrypoint for the semantic cycle.

Wires perception, graph building, attention scheduling, planning, patch
extraction, patch validation, and consolidation into one orchestrator.
Produces a RuntimeCycleResult with the full architectural trace.
"""

from __future__ import annotations
import copy
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
        store: Any | None = None,
        auto_consolidate: bool = False,
    ) -> None:
        self.concept_lattice = concept_lattice
        self.construction_lattice = construction_lattice
        self.episodic_store = episodic_store
        self.auto_consolidate = auto_consolidate

        # Reuse SemanticCPU for core component wiring — avoids duplicating
        # MeaningGraphBuilder, MeaningPerceptor, ActResolutionPlanner,
        # GraphPatchExtractor, ConceptConsolidator setup
        self._cpu = SemanticCPU(
            concept_lattice=concept_lattice,
            construction_lattice=construction_lattice,
            episodic_store=episodic_store,
            auto_consolidate=auto_consolidate,
        )

        # Expose SemanticCPU's public attributes for Pipeline cherry-picking
        self.graph_builder = self._cpu.graph_builder
        self.perceptor = self._cpu.perceptor
        self.planner = self._cpu.planner
        self.patch_extractor = self._cpu.patch_extractor
        self.consolidator = self._cpu.consolidator

        # Phase 3-4 additions
        self._attention = SemanticAttentionController()
        self._patch_validator = PatchValidator(store=store)

        # v4.2: Semantic program compilation, obligation scheduling, teaching frames
        self._program_compiler = SemanticProgramCompiler()
        self._obligation_scheduler = SemanticObligationScheduler()
        self._teaching_frame_manager = TeachingFrameManager()

        # v4.2: Relation frames, predicate schemas, relation algebra
        self._predicate_schema_store = PredicateSchemaStore()
        self._relation_frame_compiler = RelationFrameCompiler()
        self._relation_algebra = RelationAlgebra(self._predicate_schema_store)
        self._query_engine = SemanticQueryEngine(self._relation_algebra, self._predicate_schema_store)
        self._realizer = SemanticRealizer()

        # Durable semantic store + patch committer (Phase 8 breakthrough)
        self._durable_semantic_store = DurableSemanticStore()
        self._patch_committer = PatchCommitter(self._durable_semantic_store)
        self._session_state: dict = {}

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

    def _restore_session(self, kernel, context_id):
        prior = self._session_state.get(context_id)
        if prior is None:
            return
        if hasattr(kernel, 'user') and hasattr(kernel.user, 'affect'):
            kernel.user.affect = copy.deepcopy(prior.get("user_affect", kernel.user.affect))
        if hasattr(kernel, 'conversation'):
            kernel.conversation.dynamics = copy.deepcopy(
                prior.get("conversation_dynamics", kernel.conversation.dynamics)
            )
            kernel.conversation.active_repetition_group_ids = list(
                prior.get("active_repetition_group_ids", kernel.conversation.active_repetition_group_ids)
            )
            previous_recent = list(prior.get("recent_signal_ids", []))
            kernel.conversation.recent_signal_ids = previous_recent
            kernel.conversation.first_user_signal_id = prior.get(
                "first_user_signal_id", kernel.conversation.first_user_signal_id
            )
            kernel.conversation.pending_assistant_question = prior.get(
                "pending_assistant_question", ""
            )
            kernel.conversation.expected_user_answer_type = prior.get(
                "expected_user_answer_type", ""
            )
            kernel.conversation.last_assistant_response_mode = prior.get(
                "last_assistant_response_mode", ""
            )
            prior_discourse = prior.get("discourse_stack")
            if prior_discourse:
                kernel.conversation.discourse_stack = prior_discourse
            kernel.conversation.repair_target_turn_id = prior.get("repair_target_turn_id", "")
            kernel.conversation.active_teaching_target = prior.get("active_teaching_target", "")
            kernel.conversation.active_unknown_concept = prior.get("active_unknown_concept", "")
        if hasattr(kernel, 'topic'):
            prior_topic = prior.get("topic_state")
            if prior_topic:
                kernel.topic.active_topic_entity_id = prior_topic.get("active_topic_entity_id", "")
                kernel.topic.active_topic_surface = prior_topic.get("active_topic_surface", "")
                kernel.topic.active_topic_type = prior_topic.get("active_topic_type", "")
                kernel.topic.last_taught_entity_id = prior_topic.get("last_taught_entity_id", "")
                kernel.topic.last_taught_entity_surface = prior_topic.get("last_taught_entity_surface", "")
                kernel.topic.last_questioned_attribute = prior_topic.get("last_questioned_attribute", "")
        last_user_at = prior.get("last_user_at")
        if last_user_at is not None and hasattr(kernel, 'time'):
            signal_time = getattr(kernel, 'latest_signal', None)
            if signal_time is not None and hasattr(signal_time, 'observed_at'):
                kernel.time.time_since_last_user_signal_ms = max(
                    0.0, (signal_time.observed_at - float(last_user_at)) * 1000.0,
                )

    def _persist_session(self, kernel, context_id):
        self._session_state[context_id] = {
            "user_affect": copy.deepcopy(kernel.user.affect) if hasattr(kernel, 'user') and hasattr(kernel.user, 'affect') else {},
            "conversation_dynamics": copy.deepcopy(kernel.conversation.dynamics) if hasattr(kernel, 'conversation') and hasattr(kernel.conversation, 'dynamics') else {},
            "active_repetition_group_ids": list(kernel.conversation.active_repetition_group_ids) if hasattr(kernel, 'conversation') else [],
            "recent_signal_ids": list(kernel.conversation.recent_signal_ids) if hasattr(kernel, 'conversation') else [],
            "first_user_signal_id": kernel.conversation.first_user_signal_id if hasattr(kernel, 'conversation') else "",
            "last_user_at": time.time(),
            "pending_assistant_question": kernel.conversation.pending_assistant_question if hasattr(kernel, 'conversation') else "",
            "expected_user_answer_type": kernel.conversation.expected_user_answer_type if hasattr(kernel, 'conversation') else "",
            "last_assistant_response_mode": kernel.conversation.last_assistant_response_mode if hasattr(kernel, 'conversation') else "",
            "topic_state": {
                "active_topic_entity_id": kernel.topic.active_topic_entity_id if hasattr(kernel, 'topic') else "",
                "active_topic_surface": kernel.topic.active_topic_surface if hasattr(kernel, 'topic') else "",
                "active_topic_type": kernel.topic.active_topic_type if hasattr(kernel, 'topic') else "",
                "last_taught_entity_id": kernel.topic.last_taught_entity_id if hasattr(kernel, 'topic') else "",
                "last_taught_entity_surface": kernel.topic.last_taught_entity_surface if hasattr(kernel, 'topic') else "",
                "last_questioned_attribute": kernel.topic.last_questioned_attribute if hasattr(kernel, 'topic') else "",
            },
            "discourse_stack": kernel.conversation.discourse_stack if hasattr(kernel, 'conversation') else [],
            "repair_target_turn_id": kernel.conversation.repair_target_turn_id if hasattr(kernel, 'conversation') else "",
            "active_teaching_target": kernel.conversation.active_teaching_target if hasattr(kernel, 'conversation') else "",
            "active_unknown_concept": kernel.conversation.active_unknown_concept if hasattr(kernel, 'conversation') else "",
        }

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
        kernel = builder.from_signal(signal)
        kernel.latest_signal = signal

        self._restore_session(kernel, signal.context_id)

        result = self.run_turn(signal, kernel)

        self._persist_session(kernel, signal.context_id)

        from ..learning.predicate_schema_inductor import PredicateSchemaInductor
        inductor = PredicateSchemaInductor()
        try:
            inductor.induct_from_frames(result.relation_frames, self._predicate_schema_store)
        except Exception:
            pass

        return result

    def run_semantic_stack(
        self,
        signal: Any,
        kernel: Any,
        uol_graph: Any,
        percept: Any | None = None,
        working_set: Any | None = None,
    ) -> RuntimeCycleResult:
        """Run only the v4.2 semantic stack on a pre-built UOLGraph.

        This avoids re-perceiving / re-building / re-consolidating when the
        pipeline has already done those steps.  Produces a RuntimeCycleResult
        populated with semantic_program, obligation_frame, relation_frames,
        semantic_query, answer_binding, realization_contract, and realized_output.
        """
        start = time.monotonic()
        result = RuntimeCycleResult(signal=signal, context_kernel=kernel)
        result.percept = percept
        result.uol_graph = uol_graph
        result.working_set = working_set
        errors: list[str] = []

        # 1. Attend if not provided
        if working_set is None:
            try:
                budget = getattr(kernel, "budget", None) if kernel is not None else None
                working_set = self._attention.attend(uol_graph, kernel, budget)
                result.working_set = working_set
            except Exception as e:
                errors.append(f"attend failed: {e}")

        # 2. Compile semantic program
        semantic_program = None
        try:
            semantic_program = self._program_compiler.compile(uol_graph, percept, kernel)
        except Exception as e:
            errors.append(f"compile program failed: {e}")

        # 3. Schedule obligation
        obligation_frame = None
        try:
            obligation_frame = self._obligation_scheduler.schedule(
                semantic_program, working_set, kernel, uol_graph,
            )
        except Exception as e:
            errors.append(f"schedule obligation failed: {e}")

        # 4. Process teaching frame
        try:
            self._teaching_frame_manager.process_turn(
                semantic_program, uol_graph, kernel, signal.id,
            )
        except Exception as e:
            errors.append(f"teaching frame failed: {e}")

        # 5. Compile relation frames + merge with durable store
        relation_frames: list[Any] = []
        try:
            turn_frames = self._relation_frame_compiler.compile(uol_graph)
            durable_frames = self._durable_semantic_store.query_relations()
            relation_frames = turn_frames + durable_frames
        except Exception as e:
            errors.append(f"compile relations failed: {e}")

        # 6. Execute semantic query → answer binding → realization contract
        semantic_query = None
        answer_binding = None
        realization_contract = None
        if obligation_frame is not None:
            try:
                semantic_query, answer_binding, realization_contract = (
                    self._query_engine.run(
                        obligation_frame, relation_frames, semantic_program,
                    )
                )
            except Exception as e:
                errors.append(f"query engine failed: {e}")

        # 7. Realize contract → response text
        if realization_contract is not None:
            try:
                result.realized_output = self._realizer.realize(
                    realization_contract, answer_binding,
                )
            except Exception as e:
                errors.append(f"realize failed: {e}")

        # 8. Populate first-class fields
        result.semantic_program = semantic_program
        result.obligation_frame = obligation_frame
        result.relation_frames = relation_frames
        result.semantic_query = semantic_query
        result.answer_binding = answer_binding
        result.realization_contract = realization_contract

        result.cost_ms = (time.monotonic() - start) * 1000
        if errors:
            result.diagnostics = {"errors": errors}
        return result

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
            obligation_frame = self._obligation_scheduler.schedule(
                semantic_program, working_set, kernel, uol_graph,
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

        # 3d. Compile relation frames (v4.2) + merge with durable store
        relation_frames: list[Any] = []
        try:
            turn_frames = self._relation_frame_compiler.compile(uol_graph)
            durable_frames = self._durable_semantic_store.query_relations()
            # Durable frames last so current-turn frames take priority
            relation_frames = turn_frames + durable_frames
        except Exception as e:
            errors.append(f"compile relations failed: {e}")

        # 3e. Execute semantic query → answer binding → realization contract (v4.2)
        semantic_query = None
        answer_binding = None
        realization_contract = None
        if obligation_frame is not None:
            try:
                semantic_query, answer_binding, realization_contract = self._query_engine.run(
                    obligation_frame, relation_frames, semantic_program,
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
                validation = self._patch_validator.validate(patch, kernel)
                result.validation.append(validation)
            except Exception as e:
                errors.append(f"validate patch {patch.id}: {e}")

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
                valences=[],
            )
            if safety_frame and result.realized_output:
                result.realized_output = "I cannot help with that request."
                if result.realization_contract:
                    result.realization_contract.abstention_reason = "safety_policy"
        except Exception:
            pass

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
        except Exception:
            pass

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
        except Exception:
            pass

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
        return result
