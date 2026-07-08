from __future__ import annotations
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
    response_bundle: Any | None = None

    @staticmethod
    def from_cycle(cycle: Any, kernel: Any, signal: Any, turn_index: int = 0) -> "PipelineResult":
        """Derive PipelineResult from RuntimeCycleResult."""
        result = PipelineResult(
            kernel=kernel,
            output_text=cycle.realized_output,
            uol_graph=cycle.uol_graph,
            semantic_program=cycle.semantic_program,
            obligation_frame=cycle.obligation_frame,
            relation_frames=cycle.relation_frames,
            semantic_query=cycle.semantic_query,
            answer_binding=cycle.answer_binding,
            response_bundle=cycle.response_bundle,
            act_resolution_plan=cycle.act_plan,
            meaning_percept=cycle.percept,
            cost_ms=cycle.cost_ms,
        )
        return result


class Pipeline:
    def __init__(
        self,
        registry: Registry,
        concept_lattice: ConceptLattice | None = None,
        construction_lattice: ConstructionLattice | None = None,
        episodic_store: EpisodicTraceStore | None = None,
        auto_consolidate: bool = False,
    ) -> None:
        self._registry = registry
        self._builder = ContextKernelBuilder()
        self._lexeme_memory = LexemeMemory()
        self._semantic_model_store = SemanticModelStore(lexeme_memory=self._lexeme_memory)
        self._text_normalizer = TextNormalizer(lexeme_memory=self._lexeme_memory)
        self._promotion_gate = PromotionGate(semantic_model_store=self._semantic_model_store)
        self._concept_lattice = concept_lattice
        self._construction_lattice = construction_lattice
        self._episodic_store = episodic_store or EpisodicTraceStore()
        self._runtime = SemanticKernelRuntime(
            concept_lattice=concept_lattice,
            construction_lattice=construction_lattice,
            episodic_store=self._episodic_store,
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
        signal.normalized = self._text_normalizer.normalize(signal.content)

        # ── Kernel building ──
        turn_index = self._runtime.session_store.next_turn_index(signal.context_id)
        kernel = self._builder.from_signal(signal, turn_index=turn_index)
        kernel.latest_signal = signal

        if budget_override:
            for k, v in budget_override.items():
                if hasattr(kernel.budget, k):
                    setattr(kernel.budget, k, v)

        # ── Self view (inline — no legacy Store needed) ──
        kernel.self_view = SelfView()

        # ── Delegate to runtime (session restore/persist happens inside) ──
        cycle = self._runtime.run_turn(signal, kernel)

        # ── Budget enforcement ──
        self._check_budget(kernel, start)

        # ── Wrap result ──
        result = PipelineResult.from_cycle(cycle, kernel, signal, turn_index)
        result.cost_ms = (time.time() - start) * 1000.0
        result.signals.append(signal)
        return result

    def _check_budget(self, kernel: ContextKernel, start: float) -> None:
        elapsed = (time.time() - start) * 1000.0
        if elapsed > kernel.budget.latency_target_ms:
            working_ids = kernel.memory.working_signal_ids
            if len(working_ids) > kernel.budget.max_signals:
                kernel.memory.working_signal_ids = working_ids[:kernel.budget.max_signals]
            if len(kernel.world.active_claim_ids) > kernel.budget.max_claims:
                kernel.world.active_claim_ids = kernel.world.active_claim_ids[:kernel.budget.max_claims]
