# CEMM-ARCH: Refer to cemm_architecture_gap_trace.md and AGENTS.md before modifying.
# Abstain synthesis strategy - used when confidence/permission/evidence is insufficient.

from __future__ import annotations
from ..types.context_kernel import ContextKernel
from ..store.store import Store
from ..registry import Registry
from .result import SynthesisResult


class AbstainStrategy:
    def can_handle(self, params: dict) -> bool:
        return True

    def render(
        self,
        kernel: ContextKernel,
        store: Store,
        registry: Registry,
        params: dict,
    ) -> SynthesisResult:
        reason = params.get("abstain_reason", "")
        if not reason:
            answer_graph = params.get("answer_graph")
            if answer_graph and answer_graph.uncertainty_reasons:
                reason = answer_graph.uncertainty_reasons[0]
        if not reason:
            reason = "I don't have enough information to answer."
        return SynthesisResult(
            success=True,
            output=reason,
            strategy="abstain",
            cost_ms=0.1,
            verified=False,
        )
