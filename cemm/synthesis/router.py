from __future__ import annotations
from ..types.context_kernel import ContextKernel
from ..store.store import Store
from ..registry import Registry
from .template import TemplateStrategy
from .extractive import ExtractiveStrategy
from .result import SynthesisResult


class SynthesisRouter:
    def __init__(self) -> None:
        self._strategies = {
            "template": TemplateStrategy(),
            "extractive": ExtractiveStrategy(),
        }

    def route(
        self,
        strategy_name: str,
        kernel: ContextKernel,
        store: Store,
        registry: Registry,
        params: dict,
    ) -> SynthesisResult:
        strategy = self._strategies.get(strategy_name)
        if strategy is None:
            return SynthesisResult(
                success=False,
                output=f"Unknown strategy: {strategy_name}",
            )
        return strategy.render(kernel, store, registry, params)

    def select_strategy(
        self,
        kernel: ContextKernel,
        store: Store,
        registry: Registry,
        params: dict,
    ) -> str:
        template = self._strategies["template"]
        if template.can_handle(params):
            return "template"
        extractive = self._strategies["extractive"]
        if extractive.can_handle(params):
            return "extractive"
        return "template"
