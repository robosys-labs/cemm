"""Bind semantic response slots for realization."""

from __future__ import annotations

from html import escape
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
            value = self._get(slot, "value", "")
            if value:
                slots[key] = BoundSlot(
                    key=key,
                    value=self._clean_value(str(value)),
                    relation_key=self._slot_relation_key(slot),
                    slot_kind=str(self._get(slot, "slot_kind", "surface") or "surface"),
                    confidence=float(self._get(slot, "confidence", 0.5) or 0.5),
                    source_refs=self._slot_refs(slot),
                    features=self._slot_features(slot),
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
    def _get(carrier: Any, key: str, default: Any = "") -> Any:
        if isinstance(carrier, dict):
            return carrier.get(key, default)
        return getattr(carrier, key, default)

    @classmethod
    def _slot_refs(cls, slot: Any) -> list[str]:
        refs = [
            cls._get(slot, "source_binding_id", ""),
            cls._get(slot, "source_atom_id", ""),
            cls._get(slot, "source_relation_id", ""),
            cls._get(slot, "source_record_id", ""),
        ]
        source_refs = cls._get(slot, "source_refs", []) or cls._get(slot, "evidence_refs", []) or []
        if isinstance(source_refs, str):
            refs.append(source_refs)
        else:
            refs.extend(source_refs)
        return [str(ref) for ref in refs if ref]

    @classmethod
    def _slot_relation_key(cls, slot: Any) -> str:
        relation_key = cls._get(slot, "relation_key", "") or ""
        if relation_key:
            return str(relation_key)
        features = cls._slot_features(slot)
        return str(features.get("relation_key", "") or features.get("predicate", "") or "")

    @classmethod
    def _slot_features(cls, slot: Any) -> dict[str, Any]:
        features = cls._get(slot, "features", {}) or {}
        return dict(features) if isinstance(features, dict) else {}

    @staticmethod
    def _clean_value(value: str) -> str:
        allowed: list[str] = []
        for char in value:
            code = ord(char)
            if code in (9, 10, 13) or code >= 32:
                allowed.append(char)
        normalized = " ".join("".join(allowed).split()).strip()
        # Realization surfaces are plain text, but downstream UIs may render HTML.
        # Escape markup at the boundary instead of trying to parse or whitelist tags.
        return escape(normalized, quote=True)
