"""Budget-aware relation-frame selection for semantic query execution."""

from __future__ import annotations

from typing import Any

from .types import QueryBudgetPolicy

_STRUCTURAL_RELATIONS = frozenset({
    "has_role", "causes", "enables", "prevents", "before", "after",
    "refers_to", "modifies", "teaches", "asks_about", "is_a", "same_as",
    "part_of", "used_for",
})


class QueryFrameSelector:
    def select(self, *, query: Any, relation_frames: list[Any], policy: QueryBudgetPolicy) -> list[Any]:
        relation_key = getattr(query, "relation_key", "") or ""
        subject_entity = getattr(getattr(query, "subject_constraint", None), "entity_id", "") or ""
        subject_concept = getattr(getattr(query, "subject_constraint", None), "concept_id", "") or ""
        object_entity = getattr(getattr(query, "object_constraint", None), "entity_id", "") or ""
        object_concept = getattr(getattr(query, "object_constraint", None), "concept_id", "") or ""

        scored: list[tuple[tuple[int, float, int], Any]] = []
        for idx, frame in enumerate(relation_frames or []):
            if getattr(frame, "structural", False):
                continue
            if not getattr(frame, "answerable", True):
                continue
            fkey = getattr(frame, "relation_key", "") or ""
            key_score = 1 if not relation_key or fkey == relation_key else 0
            if relation_key and key_score == 0 and not policy.allow_inverse:
                continue
            if fkey in _STRUCTURAL_RELATIONS and fkey != relation_key:
                continue
            arg_score = self._arg_score(
                frame,
                subject_entity=subject_entity,
                subject_concept=subject_concept,
                object_entity=object_entity,
                object_concept=object_concept,
            )
            confidence = float(getattr(frame, "confidence", 0.5) or 0.5)
            # Higher tuple is better; idx is inverted so original order wins ties.
            scored.append(((key_score + arg_score, confidence, -idx), frame))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [frame for _, frame in scored[: max(1, policy.max_frame_scan)]]

    @staticmethod
    def _arg_score(frame: Any, *, subject_entity: str, subject_concept: str, object_entity: str, object_concept: str) -> int:
        score = 0
        subj = getattr(frame, "subject", None)
        obj = getattr(frame, "object", None)
        if subject_entity and getattr(subj, "entity_id", "") == subject_entity:
            score += 2
        if subject_concept and getattr(subj, "concept_id", "") == subject_concept:
            score += 2
        if object_entity and getattr(obj, "entity_id", "") == object_entity:
            score += 1
        if object_concept and getattr(obj, "concept_id", "") == object_concept:
            score += 1
        return score
