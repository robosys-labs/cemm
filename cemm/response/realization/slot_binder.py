"""Bind public semantic response slots from evidence only."""

from __future__ import annotations

from html import escape
from typing import Any

from ..types import ResponseSituation
from .public_values import public_value
from .types import BoundSlot


class SlotBinder:
    def bind(self, situation: ResponseSituation) -> dict[str, BoundSlot]:
        slots: dict[str, BoundSlot] = {}
        evidence = situation.evidence
        selected = getattr(evidence, "selected_slots", {}) if evidence is not None else {}
        for key, carrier in selected.items():
            features = self._slot_features(carrier)
            raw = self._get(carrier, "value", "")
            value = public_value(raw, features=features, slot_kind=str(self._get(carrier, "slot_kind", "surface") or "surface"))
            if value:
                slots[key] = BoundSlot(
                    key=key,
                    value=self._clean_value(value),
                    relation_key=self._slot_relation_key(carrier),
                    slot_kind=str(self._get(carrier, "slot_kind", "surface") or "surface"),
                    confidence=float(self._get(carrier, "confidence", 0.5) or 0.5),
                    source_refs=self._slot_refs(carrier),
                    features=features,
                )

        binding = situation.answer_binding or getattr(evidence, "answer_binding", None)
        fills = list(getattr(binding, "slot_fills", []) or [])
        if fills and "answer" not in slots:
            fills.sort(key=lambda fill: float(getattr(fill, "confidence", 0.0) or 0.0), reverse=True)
            values: list[str] = []
            accepted: list[Any] = []
            for fill in fills:
                features = dict(getattr(fill, "features", {}) or {})
                value = public_value(
                    self._fill_value(fill),
                    features=features,
                    slot_kind="surface",
                )
                if not value:
                    continue
                cleaned = self._clean_value(value)
                if cleaned and cleaned not in values:
                    values.append(cleaned)
                    accepted.append(fill)
            if values:
                primary = accepted[0]
                slots["answer"] = BoundSlot(
                    key="answer",
                    value=values[0],
                    values=values,
                    relation_key=str(getattr(primary, "relation_key", "") or ""),
                    confidence=float(getattr(primary, "confidence", 0.5) or 0.5),
                    source_refs=list(dict.fromkeys([
                        ref
                        for fill in accepted
                        for ref in [
                            *getattr(fill, "source_frame_ids", []),
                            *getattr(fill, "evidence_refs", []),
                        ]
                        if ref
                    ])),
                    features={
                        **dict(getattr(primary, "features", {}) or {}),
                        "result_count": len(values),
                    },
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
        return carrier.get(key, default) if isinstance(carrier, dict) else getattr(carrier, key, default)

    @classmethod
    def _slot_refs(cls, carrier: Any) -> list[str]:
        refs = [
            cls._get(carrier, "source_binding_id", ""),
            cls._get(carrier, "source_atom_id", ""),
            cls._get(carrier, "source_relation_id", ""),
            cls._get(carrier, "source_record_id", ""),
        ]
        extra = cls._get(carrier, "source_refs", []) or cls._get(carrier, "evidence_refs", []) or []
        refs.extend([extra] if isinstance(extra, str) else extra)
        return list(dict.fromkeys(str(ref) for ref in refs if ref))

    @classmethod
    def _slot_relation_key(cls, carrier: Any) -> str:
        relation_key = cls._get(carrier, "relation_key", "") or ""
        if relation_key:
            return str(relation_key)
        features = cls._slot_features(carrier)
        return str(features.get("relation_key", "") or features.get("predicate", "") or "")

    @classmethod
    def _slot_features(cls, carrier: Any) -> dict[str, Any]:
        features = cls._get(carrier, "features", {}) or {}
        return dict(features) if isinstance(features, dict) else {}

    @staticmethod
    def _clean_value(value: str) -> str:
        allowed = [char for char in value if ord(char) in (9, 10, 13) or ord(char) >= 32]
        normalized = " ".join("".join(allowed).split()).strip()
        return escape(normalized, quote=True)
