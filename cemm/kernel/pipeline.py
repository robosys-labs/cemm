from __future__ import annotations
import copy
import time
import uuid
from dataclasses import dataclass, field
from typing import Any
from ..types.signal import Signal, SignalKind, SourceType
from ..types.action import Action, ActionKind, ActionStatus
from ..types.context_kernel import ContextKernel
from ..types.self_view import SelfView
from ..types.permission import Permission
from ..types.uol_graph import UOLGraph
from ..store.store import Store
from ..registry import Registry
from ..registry.semantic_model_store import SemanticModelStore
from ..learning.lexeme_memory import LexemeMemory
from ..memory.concept_lattice import ConceptLattice
from ..memory.construction_lattice import ConstructionLattice
from ..memory.episodic_trace_store import EpisodicTraceStore
from .context_kernel_builder import ContextKernelBuilder
from .text_normalizer import TextNormalizer
from .promotion_gate import PromotionGate
from .semantic_kernel_runtime import SemanticKernelRuntime


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
    # v4.2: Semantic stack outputs
    semantic_program: Any | None = None
    obligation_frame: Any | None = None
    relation_frames: list[Any] = field(default_factory=list)
    semantic_query: Any | None = None
    answer_binding: Any | None = None
    realization_contract: Any | None = None
    semantic_realized_output: str = ""

    @staticmethod
    def from_cycle(cycle: Any, kernel: Any, signal: Any, turn_index: int = 0) -> "PipelineResult":
        """Derive PipelineResult from RuntimeCycleResult for backward compatibility."""
        result = PipelineResult(
            kernel=kernel,
            output_text=cycle.realized_output,
            uol_graph=cycle.uol_graph,
            semantic_program=cycle.semantic_program,
            obligation_frame=cycle.obligation_frame,
            relation_frames=cycle.relation_frames,
            semantic_query=cycle.semantic_query,
            answer_binding=cycle.answer_binding,
            realization_contract=cycle.realization_contract,
            semantic_realized_output=cycle.realized_output,
            act_resolution_plan=cycle.act_plan,
            meaning_percept=cycle.percept,
            cost_ms=cycle.cost_ms,
        )
        return result


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
        self._lexeme_memory = LexemeMemory()
        self._semantic_model_store = SemanticModelStore(lexeme_memory=self._lexeme_memory)
        self._text_normalizer = TextNormalizer(lexeme_memory=self._lexeme_memory)
        self._promotion_gate = PromotionGate(semantic_model_store=self._semantic_model_store)
        self._turn_counts: dict[str, int] = {}
        self._session_state: dict[str, dict] = {}
        self._concept_lattice = concept_lattice
        self._construction_lattice = construction_lattice
        self._episodic_store = episodic_store or EpisodicTraceStore()
        self._runtime = SemanticKernelRuntime(
            concept_lattice=concept_lattice,
            construction_lattice=construction_lattice,
            episodic_store=self._episodic_store,
            store=store,
            auto_consolidate=auto_consolidate,
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

        # ── Signal creation ──
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

        # ── Kernel building ──
        turn_index = self._turn_counts.get(signal.context_id, 0) + 1
        self._turn_counts[signal.context_id] = turn_index
        kernel = self._builder.from_signal(signal, turn_index=turn_index)
        kernel.latest_signal = signal

        if budget_override:
            for k, v in budget_override.items():
                if hasattr(kernel.budget, k):
                    setattr(kernel.budget, k, v)

        # ── Session restore ──
        prior_session = self._session_state.get(signal.context_id)
        if prior_session:
            self._restore_session_state(kernel, prior_session)

        # ── Self view ──
        self_state = self._store.self_store.latest()
        if self_state:
            kernel.self_view = SelfView.from_self_state(self_state, kernel.memory.working_claim_ids)
        else:
            kernel.self_view = SelfView()

        # ── Delegate to runtime ──
        cycle = self._runtime.run_turn(signal, kernel)

        # ── Session persist ──
        self._session_state[signal.context_id] = self._build_session_state(kernel)

        # ── Wrap result ──
        result = PipelineResult.from_cycle(cycle, kernel, signal, turn_index)
        result.cost_ms = (time.time() - start) * 1000.0
        result.signals.append(signal)
        return result

    def _restore_session_state(self, kernel, prior_session):
        kernel.user.affect = copy.deepcopy(prior_session.get("user_affect", kernel.user.affect))
        kernel.conversation.dynamics = copy.deepcopy(
            prior_session.get("conversation_dynamics", kernel.conversation.dynamics)
        )
        kernel.conversation.active_repetition_group_ids = list(
            prior_session.get("active_repetition_group_ids", kernel.conversation.active_repetition_group_ids)
        )
        previous_recent = list(prior_session.get("recent_signal_ids", []))
        kernel.conversation.recent_signal_ids = previous_recent + [kernel.latest_signal.id]
        kernel.conversation.first_user_signal_id = prior_session.get(
            "first_user_signal_id", kernel.conversation.first_user_signal_id
        )
        last_user_at = prior_session.get("last_user_at")
        if last_user_at is not None:
            kernel.time.time_since_last_user_signal_ms = max(
                0.0, (kernel.latest_signal.observed_at - float(last_user_at)) * 1000.0,
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
        prior_topic = prior_session.get("topic_state")
        if prior_topic:
            kernel.topic.active_topic_entity_id = prior_topic.get("active_topic_entity_id", "")
            kernel.topic.active_topic_surface = prior_topic.get("active_topic_surface", "")
            kernel.topic.active_topic_type = prior_topic.get("active_topic_type", "")
            kernel.topic.last_taught_entity_id = prior_topic.get("last_taught_entity_id", "")
            kernel.topic.last_taught_entity_surface = prior_topic.get("last_taught_entity_surface", "")
            kernel.topic.last_questioned_attribute = prior_topic.get("last_questioned_attribute", "")
        prior_discourse = prior_session.get("discourse_stack")
        if prior_discourse:
            kernel.conversation.discourse_stack = prior_discourse
        kernel.conversation.repair_target_turn_id = prior_session.get("repair_target_turn_id", "")
        kernel.conversation.active_teaching_target = prior_session.get("active_teaching_target", "")
        kernel.conversation.active_unknown_concept = prior_session.get("active_unknown_concept", "")

    def _build_session_state(self, kernel):
        return {
            "user_affect": copy.deepcopy(kernel.user.affect),
            "conversation_dynamics": copy.deepcopy(kernel.conversation.dynamics),
            "active_repetition_group_ids": list(kernel.conversation.active_repetition_group_ids),
            "recent_signal_ids": list(kernel.conversation.recent_signal_ids),
            "first_user_signal_id": kernel.conversation.first_user_signal_id,
            "last_user_at": kernel.latest_signal.observed_at,
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

    def _check_budget(self, kernel: ContextKernel, start: float) -> None:
        elapsed = (time.time() - start) * 1000.0
        if elapsed > kernel.budget.latency_target_ms:
            working_ids = kernel.memory.working_signal_ids
            if len(working_ids) > kernel.budget.max_entities:
                kernel.memory.working_signal_ids = working_ids[:kernel.budget.max_entities]
            if len(kernel.world.active_claim_ids) > kernel.budget.max_claims:
                kernel.world.active_claim_ids = kernel.world.active_claim_ids[:kernel.budget.max_claims]
