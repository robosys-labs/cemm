"""Atomic multilingual realization executor."""

from __future__ import annotations

from ..types import RealizedCandidate, ResponseMove, ResponseSituation
from .languages import EnglishRenderer, FrenchRenderer
from .languages.base import LanguageRenderer
from .planner import RealizationPlanner
from .slot_binder import SlotBinder


class RealizationExecutor:
    """Render response moves through language-neutral units.

    The executor itself is language-agnostic. It binds semantic slots, builds a
    neutral realization plan, and delegates surface text to a language renderer.
    """

    def __init__(self, renderers: list[LanguageRenderer] | None = None) -> None:
        builtins: list[LanguageRenderer] = [EnglishRenderer(), FrenchRenderer()]
        self._renderers = {renderer.language_code: renderer for renderer in (renderers or builtins)}
        self._slot_binder = SlotBinder()
        self._planner = RealizationPlanner()

    def realize(self, moves: list[ResponseMove], situation: ResponseSituation) -> str:
        return self.realize_candidate(moves, situation).text

    def realize_candidate(self, moves: list[ResponseMove], situation: ResponseSituation) -> RealizedCandidate:
        language = self._normalize_language(situation.language)
        renderer = self._renderer_for(language)
        slots = self._slot_binder.bind(situation)
        plan = self._planner.build_plan(moves, situation, slots, language=renderer.language_code)
        text = renderer.render_plan(plan)
        trace = {
            "language": renderer.language_code,
            "requested_language": language,
            "available_languages": sorted(self._renderers),
            "surface_source": "semantic_slots_only",
            "slot_keys": plan.slot_keys,
            **plan.diagnostics,
        }
        return RealizedCandidate(
            plan=plan.plan,
            text=text,
            language=renderer.language_code,
            grammar_trace=trace,
        )

    def _renderer_for(self, language: str) -> LanguageRenderer:
        if language in self._renderers:
            return self._renderers[language]
        base = language.split("-", 1)[0]
        if base in self._renderers:
            return self._renderers[base]
        return self._renderers["en"]

    @staticmethod
    def _normalize_language(language: str) -> str:
        language = (language or "en").strip().replace("_", "-")
        return language or "en"
