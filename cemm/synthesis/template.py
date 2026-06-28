from __future__ import annotations
from dataclasses import dataclass, field
from ..types.context_kernel import ContextKernel
from ..store.store import Store
from ..registry import Registry
from .result import SynthesisResult


class TemplateStrategy:
    def can_handle(self, params: dict) -> bool:
        return bool(params.get("template") or params.get("template_key"))

    def render(
        self,
        kernel: ContextKernel,
        store: Store,
        registry: Registry,
        params: dict,
    ) -> SynthesisResult:
        template = params.get("template", "")
        template_key = params.get("template_key", "")
        if template_key and not template:
            template = self._load_template(template_key)
        variables = params.get("variables", {})
        rendered = self._apply(template, variables)
        return SynthesisResult(
            success=True,
            output=rendered,
            strategy="template",
            cost_ms=0.5,
            verified=True,
        )

    @staticmethod
    def _load_template(key: str) -> str:
        templates = {
            "greeting": "Hello! How can I help you today?",
            "confirmation": "I've noted that: {subject} {predicate} {object}.",
            "clarification": "Could you clarify what you mean by {term}?",
            "capability": "I can help with questions about {domain}.",
        }
        return templates.get(key, "I'm not sure how to respond to that.")

    @staticmethod
    def _apply(template: str, variables: dict) -> str:
        result = template
        for k, v in variables.items():
            result = result.replace(f"{{{k}}}", str(v))
        return result
