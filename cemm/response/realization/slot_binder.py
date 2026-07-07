"""Bind semantic response slots for realization."""

from __future__ import annotations

from typing import Any

from ..types import ResponseSituation
from .types import BoundSlot


class SlotBinder:
    """Bind slots from query/evidence outputs only.

    This component deliberately never reads raw user text or instruction
    surface. If upstream semantics did not bind a slot, realization must not
    invent one.
    """

    def bind(self, situation: ResponseSituation) -> dict[str, BoundSlot]:
        slots: dict[str, BoundSlot] = {}
        evidence = situation.evidence
        for key, slot in getattr(evidence, "selected_slots", {}).items() if evidence is not None else []:
            value = getattr(slot, "value", "")
            if value:
                slots[key] = BoundSlot(
                    key=key,
                    value=self._clean_value(str(value)),
                    relation_key=getattr(slot, "relation_key", "") or "",
                    slot_kind=getattr(slot, "slot_kind", "surface") or "surface",
                    confidence=float(getattr(slot, "confidence", 0.5) or 0.5),
                    source_refs=self._slot_refs(slot),
                    features=dict(getattr(slot, "features", {}) or {}),
                )

        binding = situation.answer_binding or getattr(evidence, "answer_binding", None)
        fills = list(getattr(binding, "slot_fills", []) or [])
        if fills and "answer" not in slots:
            best = max(fills, key=lambda fill: getattr(fill, "confidence", 0.0) or 0.0)
            value = self._fill_value(best)
            if value:
                slots["answer"] = BoundSlot(
                    key="answer",
                    value=self._clean_value(value),
                    relation_key=getattr(best, "relation_key", "") or "",
                    confidence=float(getattr(best, "confidence", 0.5) or 0.5),
                    source_refs=[
                        *getattr(best, "source_frame_ids", []),
                        *getattr(best, "evidence_refs", []),
                    ],
                    features=dict(getattr(best, "features", {}) or {}),
                )
        return slots

    @staticmethod
    def _fill_value(fill: Any) -> str:
        return str(
            getattr(fill, "surface", "")
            or getattr(fill, "concept_id", "")
            or getattr(fill, "entity_id", "")
            or ""
        )

    @staticmethod
    def _slot_refs(slot: Any) -> list[str]:
        refs = [
            getattr(slot, "source_binding_id", ""),
            getattr(slot, "source_atom_id", ""),
            getattr(slot, "source_relation_id", ""),
            getattr(slot, "source_record_id", ""),
        ]
        return [ref for ref in refs if ref]

    @staticmethod
    def _clean_value(value: str) -> str:
        import re
        # Strip script/style blocks entirely (content + tags)
        value = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)
        value = re.sub(r'<style[^>]*>.*?</style>', '', value, flags=re.IGNORECASE | re.DOTALL)
        # Strip remaining HTML tags
        value = re.sub(r'<[^>]+>', '', value)
        # Remove control characters
        allowed: list[str] = []
        for char in value:
            code = ord(char)
            if code in (9, 10, 13) or code >= 32:
                allowed.append(char)
        return " ".join("".join(allowed).split()).strip()
