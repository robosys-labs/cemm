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
    ) -> tuple[ContextKernel | None, list[Signal], list[Signal]]:
        result = self._pipeline.run(input_text, context_id=context_id)
        self._last_result = result
        kernel = result.kernel
        if kernel is None:
            return None, [], []

        internal_signals = [s for s in result.signals if s.kind in self._INTERNAL_SIGNAL_KINDS]
        actionable_signals: list[Signal] = []

        from .invariant_guard import InvariantGuard
        guard = InvariantGuard()
        guard.reset()
        for action in result.actions:
            guard.check_action_has_trace(action)
            guard.check_memory_mutation_has_trace(action)
        guard.check_recursive_budget(kernel, 0)

        self._run_online_learning(kernel, result)

        if kernel.budget.max_recursive_steps > 0:
            remaining_steps = kernel.budget.max_recursive_steps
            remaining_latency = kernel.budget.latency_target_ms
            while remaining_steps > 0 and remaining_latency > 0:
                triggers = self._find_recursion_triggers(kernel, result.actions)
                if not triggers:
                    break
                new_signals = []
                for trigger in triggers:
                    if trigger.salience < 0.3:
                        continue
                    remaining_steps -= 1
                    child_budget = kernel.budget.clone()
                    child_budget.latency_target_ms = remaining_latency
                    child_budget.max_recursive_steps = remaining_steps
                    sub_result = self._pipeline.run(
                        trigger.content,
                        context_id=context_id,
                        budget_override={
                            "latency_target_ms": remaining_latency,
                            "max_recursive_steps": remaining_steps,
                            "max_entities": child_budget.max_entities,
                            "max_claims": child_budget.max_claims,
                            "max_models": child_budget.max_models,
                            "max_ranked": child_budget.max_ranked,
                            "max_actions": child_budget.max_actions,
                            "allow_dense_fallback": child_budget.allow_dense_fallback,
                            "allow_simulation": child_budget.allow_simulation,
                        },
                    )
                    remaining_latency -= sub_result.cost_ms
                    if remaining_steps <= 0 or remaining_latency <= 0:
                        abort_signal = Signal(
                            id=f"abort_{context_id}_{remaining_steps}",
                            kind=SignalKind.SYSTEM,
                            source_id="recursive_loop",
                            source_type=SourceType.SYSTEM,
                            content=f"Recursion aborted: budget exhausted (steps={remaining_steps}, latency={remaining_latency:.1f}ms)",
                            observed_at=time.time(),
                            context_id=context_id,
                            salience=0.9,
                            trust=1.0,
                            permission=kernel.permission,
                        )
                        self._store.signals.put(abort_signal)
                        break
                    budget_signal = Signal(
                        id=f"budget_{trigger.id}_{remaining_steps}",
                        kind=SignalKind.TRACE,
                        source_id="recursive_loop",
                        source_type=SourceType.SYSTEM,
                        content=f"Budget after child: remaining_steps={remaining_steps}, remaining_latency={remaining_latency:.1f}ms, child_cost={sub_result.cost_ms:.1f}ms",
                        observed_at=time.time(),
                        context_id=context_id,
                        salience=0.3,
                        trust=1.0,
                        permission=kernel.permission,
                    )
                    self._store.signals.put(budget_signal)
                    if sub_result.kernel:
                        new_signals.extend(sub_result.signals)
                        internal_signals.extend(
                            s for s in sub_result.signals
                            if s.kind in self._INTERNAL_SIGNAL_KINDS
                        )
                    if sub_result.signals:
                        for sig in sub_result.signals:
                            if sig.salience >= 0.6:
                                actionable_signals.append(sig)
                if remaining_steps <= 0:
                    break

        if self._induction_turn_count % 10 == 0:
            self._run_induction(kernel)
        self._induction_turn_count += 1

        if kernel.memory.candidate_model_ids:
            self._run_induction(kernel)

        return kernel, internal_signals, actionable_signals

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
        self_state = self._store.self_store.latest()
        if self_state:
            self._learner.update_self_state(self_state)
        if hasattr(self._learner, "update_source_trust"):
            self._learner.update_source_trust(kernel)
        if hasattr(self._learner, "update_operator_reliability"):
            self._learner.update_operator_reliability(kernel)
        if hasattr(self._learner, "update_ranking_weights"):
            self._learner.update_ranking_weights(kernel)

    def _run_induction(self, kernel: ContextKernel) -> None:
        from ..training.promoter import Promoter
        from ..training.evaluator import Evaluator
        from ..types.model import ModelKind
        candidates = self._inductor.maybe_induct()
        promoter = Promoter(self._store)
        evaluator = Evaluator(self._store)
        for model in candidates:
            existing = self._store.conn.execute(
                "SELECT id FROM eval_results WHERE model_id = ? LIMIT 1",
                (model.id,),
            ).fetchone()
            if existing:
                continue
            eval_set = evaluator.create_eval_set(
                f"induction_{model.kind.value}",
                f"Auto-eval for inducted {model.kind.value}",
            )
            evaluator.record_result(
                eval_set_id=eval_set.id,
                job_id=model.id,
                score=model.confidence,
                model_id=model.id,
                metrics={"kind": model.kind.value, "support_estimate": model.confidence},
            )
            candidate = promoter.create_candidate(
                model.id,
                reason=f"induction: {model.description}",
                score=model.confidence,
            )
            # Auto-promote high-confidence, low-risk causal rules so the system can
            # learn from repeated observations without manual gatekeeping.
            if model.kind == ModelKind.CAUSAL_RULE and candidate.score >= 0.8:
                promoter.approve(candidate.id)
