from __future__ import annotations
import time
import uuid
from dataclasses import dataclass, field
from ..types.signal import Signal, SignalKind, SourceType
from ..types.action import Action, ActionKind, ActionStatus
from ..types.trace import Trace
from ..types.context_kernel import ContextKernel
from ..types.permission import Permission
from ..store.store import Store
from ..registry import Registry
from ..confidence.scoring import score_action
from .context_kernel_builder import ContextKernelBuilder
from .normalizer import Normalizer
from .entity_resolver import EntityResolver
from .frame_engine import FrameEngine
from .pragmatic_interpreter import interpret_signal, update_pragmatic_state
from ..registry.uol_mapper import UOLMapper


@dataclass
class PipelineResult:
    output_text: str = ""
    actions: list[Action] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    kernel: ContextKernel | None = None
    confidence: float = 0.0
    cost_ms: float = 0.0
    abstained: bool = False


class Pipeline:
    def __init__(
        self,
        store: Store,
        registry: Registry,
    ) -> None:
        self._store = store
        self._registry = registry
        self._builder = ContextKernelBuilder()
        self._normalizer = Normalizer(registry)
        self._resolver = EntityResolver(store.entities)
        self._frames = FrameEngine(store.claims)
        self._uol_mapper = UOLMapper(registry)

    def run(
        self,
        input_text: str,
        context_id: str | None = None,
        budget_override: dict | None = None,
    ) -> PipelineResult:
        start = time.time()
        signal = Signal(
            id=uuid.uuid4().hex[:16],
            kind=SignalKind.INPUT,
            source_id="user",
            source_type=SourceType.USER,
            content=input_text,
            observed_at=start,
            context_id=context_id or uuid.uuid4().hex[:16],
            salience=0.8,
            trust=0.8,
            permission=Permission.public(),
        )
        self._store.signals.put(signal)

        kernel = self._builder.from_signal(signal)

        if budget_override:
            for k, v in budget_override.items():
                if hasattr(kernel.budget, k):
                    setattr(kernel.budget, k, v)

        self_state = self._store.self_store.latest()
        if self_state:
            kernel.self_state = self_state

        self._resolver.resolve_self(kernel)
        self._frames.apply_frame_rules(kernel)

        semantics = interpret_signal(signal, kernel, self._store)
        if semantics is not None:
            uol_atoms = self._uol_mapper.map_signal(signal.content, kernel)
            semantics.uol_atoms = uol_atoms
            quality_keys, process_keys = self._uol_mapper.compile_to_pragmatic_keys(uol_atoms)
            if kernel.conversation.pragmatic_state:
                kernel.conversation.pragmatic_state.active_quality_atom_keys = quality_keys
                kernel.conversation.pragmatic_state.active_process_atom_keys = process_keys
            signal.observation_semantics = semantics
            if semantics.semantic_cluster_key:
                conv = kernel.conversation
                if conv.pragmatic_state is None:
                    from ..types.context_kernel import PragmaticState
                    conv.pragmatic_state = PragmaticState(last_updated_at=start)
                conv.pragmatic_state = update_pragmatic_state(conv.pragmatic_state, semantics, kernel, signal.id)
                if kernel.user.session_affect is None:
                    kernel.user.session_affect = PragmaticState(last_updated_at=start)
                kernel.user.session_affect = update_pragmatic_state(kernel.user.session_affect, semantics, kernel, signal.id)

        self._check_budget(kernel, start)

        result = PipelineResult(kernel=kernel)
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
