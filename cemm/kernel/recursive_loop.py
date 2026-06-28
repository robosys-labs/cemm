from __future__ import annotations
import time
from ..types.signal import Signal, SignalKind, SourceType
from ..types.context_kernel import ContextKernel
from ..types.self_state import SelfState
from ..store.store import Store
from ..learning.online import OnlineLearner
from ..learning.inductor import Inductor
from ..retrieval.structural import StructuralRetriever
from ..retrieval.ranker import Ranker
from .pipeline import Pipeline, PipelineResult
from ..types.action import Action


class RecursiveLoop:
    def __init__(
        self,
        pipeline: Pipeline,
        store: Store,
        online_learner: OnlineLearner,
        inductor: Inductor,
    ) -> None:
        self._pipeline = pipeline
        self._store = store
        self._learner = online_learner
        self._inductor = inductor
        self._retriever = StructuralRetriever(store)
        self._ranker = Ranker()
        self._induction_turn_count: int = 0

    _INTERNAL_SIGNAL_KINDS = (
        SignalKind.TRACE,
        SignalKind.ACTION_RESULT,
        SignalKind.MEMORY_UPDATE,
        SignalKind.SIMULATION_RESULT,
        SignalKind.REFLECTION,
    )

    def run_once(
        self,
        input_text: str,
        context_id: str,
    ) -> tuple[ContextKernel | None, list[Signal]]:
        result = self._pipeline.run(input_text, context_id=context_id)
        kernel = result.kernel
        if kernel is None:
            return None, []

        internal_signals = [s for s in result.signals if s.kind in self._INTERNAL_SIGNAL_KINDS]

        from .invariant_guard import InvariantGuard
        guard = InvariantGuard()
        guard.reset()
        for action in result.actions:
            guard.check_action_has_trace(action)
            guard.check_memory_mutation_has_trace(action)
        guard.check_recursive_budget(kernel, 0)

        self._run_online_learning(kernel, result)

        if kernel.budget.max_recursive_steps > 0:
            recursion_depth = 0
            while recursion_depth < kernel.budget.max_recursive_steps:
                triggers = self._find_recursion_triggers(kernel, result.actions)
                if not triggers:
                    break
                new_signals = []
                for trigger in triggers:
                    if trigger.salience < 0.3:
                        continue
                    sub_result = self._pipeline.run(
                        trigger.content,
                        context_id=context_id,
                    )
                    if sub_result.kernel:
                        new_signals.extend(sub_result.signals)
                        internal_signals.extend(
                            s for s in sub_result.signals
                            if s.kind in self._INTERNAL_SIGNAL_KINDS
                        )
                recursion_depth += 1

        if self._induction_turn_count % 10 == 0:
            self._run_induction(kernel)
        self._induction_turn_count += 1

        if kernel.memory.candidate_model_ids:
            self._run_induction(kernel)

        return kernel, internal_signals

    def _find_recursion_triggers(self, kernel: ContextKernel, actions: list[Action] | None = None) -> list[Signal]:
        triggers: list[Signal] = []
        for action in (actions or []):
            if action.status.value == "failed":
                triggers.append(Signal(
                    id=f"recurse_{action.id}",
                    kind=SignalKind.ACTION_RESULT,
                    source_id="recursive_loop",
                    source_type=SourceType.SYSTEM,
                    content=f"Action {action.id} failed",
                    observed_at=time.time(),
                    context_id=kernel.id,
                    salience=0.8,
                    trust=1.0,
                    permission=kernel.permission,
                ))
        if kernel.self_view.uncertainty > 0.7:
            triggers.append(Signal(
                id="recurse_uncertainty",
                kind=SignalKind.REFLECTION,
                source_id="recursive_loop",
                source_type=SourceType.SYSTEM,
                content=f"High uncertainty ({kernel.self_view.uncertainty:.2f})",
                observed_at=time.time(),
                context_id=kernel.id,
                salience=0.6,
                trust=1.0,
                permission=kernel.permission,
            ))
        if kernel.self_view.recent_error_rate > 0.3:
            triggers.append(Signal(
                id="recurse_error_rate",
                kind=SignalKind.REFLECTION,
                source_id="recursive_loop",
                source_type=SourceType.SYSTEM,
                content=f"High error rate ({kernel.self_view.recent_error_rate:.2f})",
                observed_at=time.time(),
                context_id=kernel.id,
                salience=0.7,
                trust=1.0,
                permission=kernel.permission,
            ))
        if kernel.self_view.coherence < 0.5:
            triggers.append(Signal(
                id="recurse_coherence",
                kind=SignalKind.REFLECTION,
                source_id="recursive_loop",
                source_type=SourceType.SYSTEM,
                content=f"Low coherence ({kernel.self_view.coherence:.2f})",
                observed_at=time.time(),
                context_id=kernel.id,
                salience=0.7,
                trust=1.0,
                permission=kernel.permission,
            ))
        return triggers

    def _run_online_learning(self, kernel: ContextKernel, result) -> None:
        if kernel.self_state:
            self._learner.update_self_state(kernel.self_state)

    def _run_induction(self, kernel: ContextKernel) -> None:
        candidates = self._inductor.maybe_induct()
        for model in candidates:
            self._store.models.put(model)
