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
        )

    @staticmethod
    def _load_template(key: str) -> str:
        templates = {
            "greeting": "Hello! How can I help you today?",
            "confirmation": "I've noted that: {subject} {predicate} {object}.",
            "clarification": "Could you clarify what you mean by {term}?",
            "capability": "I can help with questions about {domain}.",
            "acknowledgment": "Got it! What else would you like to know or share?",
            "remember_confirm": "I've stored that in this session.",
            "retrieve_empty": "I did not find matching stored evidence.",
            "permission_denied": "I cannot do that because the required permission is not available.",
        }
        return templates.get(key, "")

    @staticmethod
    def _apply(template: str, variables: dict) -> str:
        result = template
        for k, v in variables.items():
            result = result.replace(f"{{{k}}}", str(v))
        return result
