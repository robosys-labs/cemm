"""Gap policy: dialogue repair is default; learning requires semantic intent."""
from __future__ import annotations

from dataclasses import replace

from .gap_detector import GapDetectionResult, GapDetector


_EXPLICIT_LEARNING_PREDICATES = frozenset({"means", "defines", "learns"})


class CanonicalGapDetector(GapDetector):
    """Prevent ordinary opaque dialogue from silently opening schema lessons.

    A gap remains observable for diagnostics, but it becomes learnable only when
    the selected semantic structure is explicitly definitional/metalinguistic.
    """

    def detect(self, *args, **kwargs):
        selected = tuple(kwargs.get("selected_interpretations") or ())
        permits_learning = any(
            getattr(item, "predicate_semantic_key", "")
            in _EXPLICIT_LEARNING_PREDICATES
            for item in selected
        )
        if not permits_learning:
            kwargs["suppress_fresh_lexical_gaps"] = True
        result = super().detect(*args, **kwargs)
        if permits_learning:
            return result
        gaps = tuple(
            replace(gap, learnable=False, probe_options=())
            if gap.learnable else gap
            for gap in result.gaps
        )
        blocking_ids = {gap.id for gap in result.blocking_gaps}
        blocking = tuple(gap for gap in gaps if gap.id in blocking_ids)
        return GapDetectionResult(
            gaps=gaps,
            blocking_gaps=blocking,
            has_blocking=bool(blocking),
        )
