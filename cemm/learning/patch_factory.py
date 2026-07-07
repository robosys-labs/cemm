"""Learning patch construction with strict payload sanitization."""

from __future__ import annotations

import hashlib
from typing import Any

from .learning_types import LearningPatchCandidate

_DENIED_PAYLOAD_KEYS = frozenset({
    "text", "raw_text", "surface", "user_text", "assistant_text", "content", "transcript", "message",
})


class LearningPatchFactory:
    def make(
        self,
        *,
        target: str,
        key: tuple[str, ...],
        delta: dict[str, float],
        confidence: float,
        source_refs: list[str],
        payload: dict[str, Any] | None = None,
        operation: str = "increment_stat",
    ) -> LearningPatchCandidate:
        sanitized_payload = self._sanitize_payload(payload or {})
        patch = LearningPatchCandidate(
            patch_id=self._patch_id(target, key, delta, source_refs),
            target=target,
            operation=operation,
            key=tuple(str(part) for part in key if part is not None),
            delta={str(k): float(v) for k, v in delta.items()},
            confidence=max(0.0, min(1.0, float(confidence or 0.0))),
            reversible=True,
            source_refs=_dedupe([str(ref) for ref in source_refs if ref]),
            payload=sanitized_payload,
        )
        return patch

    def _sanitize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        clean: dict[str, Any] = {}
        for key, value in payload.items():
            if str(key) in _DENIED_PAYLOAD_KEYS:
                continue
            if isinstance(value, str):
                clean[str(key)] = value if self._looks_like_identifier(value) else "<redacted_surface>"
            elif isinstance(value, (int, float, bool)) or value is None:
                clean[str(key)] = value
            elif isinstance(value, (list, tuple)):
                clean[str(key)] = [item for item in value if not isinstance(item, str) or self._looks_like_identifier(item)]
            elif isinstance(value, dict):
                clean[str(key)] = self._sanitize_payload(value)
        return clean

    @staticmethod
    def _looks_like_identifier(value: str) -> bool:
        if not value:
            return True
        allowed_prefixes = ("atom:", "concept:", "entity:", "frame:", "patch:", "turn:", "signal:")
        if value.startswith(allowed_prefixes):
            return True
        if len(value) <= 64 and all(ch.isalnum() or ch in "_:-./" for ch in value):
            return True
        return False

    @staticmethod
    def _patch_id(target: str, key: tuple[str, ...], delta: dict[str, float], source_refs: list[str]) -> str:
        material = repr((target, key, sorted(delta.items()), sorted(source_refs))).encode("utf-8")
        return "learn_" + hashlib.sha256(material).hexdigest()[:16]


def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        if value and value not in out:
            out.append(value)
    return out
