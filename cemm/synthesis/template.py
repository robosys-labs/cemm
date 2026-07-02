from __future__ import annotations

import json
from pathlib import Path

from ..types.context_kernel import ContextKernel
from ..store.store import Store
from ..registry import Registry
from .result import SynthesisResult


_TEMPLATE_PATH = Path(__file__).parent.parent / "data" / "response_templates.json"


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
        language = params.get("language") or self._detect_language(kernel)
        if template_key and not template:
            template = self._load_template(template_key, language)
        variables = params.get("variables", {})
        rendered = self._apply(template, variables)
        return SynthesisResult(
            success=True,
            output=rendered,
            strategy="template",
            cost_ms=0.5,
        )

    @staticmethod
    def _detect_language(kernel: ContextKernel) -> str:
        if kernel.user.locale and kernel.user.locale.get("language"):
            return kernel.user.locale["language"]
        if kernel.world and kernel.world.assistant_locale and kernel.world.assistant_locale.get("language"):
            return kernel.world.assistant_locale["language"]
        return "en"

    @staticmethod
    def _load_template(key: str, language: str = "en") -> str:
        if _TEMPLATE_PATH.exists():
            data = json.loads(_TEMPLATE_PATH.read_text(encoding="utf-8"))
            lang_map = data.get(language) or data.get("en", {})
            return lang_map.get(key, "")
        return ""

    @staticmethod
    def _apply(template: str, variables: dict) -> str:
        result = template
        for k, v in variables.items():
            result = result.replace(f"{{{k}}}", str(v))
        return result
