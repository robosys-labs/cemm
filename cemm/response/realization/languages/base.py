"""Language renderer protocol and shared helpers."""

from __future__ import annotations

from typing import Protocol

from ..types import RealizationPlan, RealizationUnit


class LanguageRenderer(Protocol):
    language_code: str

    def render_plan(self, plan: RealizationPlan) -> str:
        ...


class SentenceHelpers:
    @staticmethod
    def sentence(text: str) -> str:
        text = " ".join((text or "").split()).strip()
        if not text:
            return ""
        text = text[0].upper() + text[1:]
        if text[-1] not in ".!?":
            text += "."
        return text

    @staticmethod
    def clean_label(value: str) -> str:
        if value.startswith("has_"):
            value = value[4:]
        if ":" in value:
            value = value.split(":", 1)[1]
        return " ".join(part for part in value.split("_") if part) or "value"

    @staticmethod
    def join_units(rendered: list[str]) -> str:
        return " ".join(part for part in rendered if part).strip()


class BaseRenderer(SentenceHelpers):
    language_code = "und"

    def render_plan(self, plan: RealizationPlan) -> str:
        return self.join_units([self.render_unit(unit) for unit in plan.units])

    def render_unit(self, unit: RealizationUnit) -> str:
        return ""
