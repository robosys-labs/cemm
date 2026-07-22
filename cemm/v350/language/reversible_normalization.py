"""Reversible, evidence-preserving text normalization for v3.5.1 language packages.

Normalization is form evidence, never semantic identity.  Whole-string Unicode NFKC
plus casefold produces the canonical analysis form.  A deterministic alignment ledger
preserves exact source evidence and source/normalized span projection without relying on
character-by-character normalization (which is wrong across combining/Jamo boundaries)
or heuristic diff matching.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import unicodedata


_NORMALIZATION_PROFILE = "unicode:nfkc-casefold:v3-deterministic-alignment"
_MAX_LOCAL_ALIGNMENT_LOOKAHEAD = 64


@dataclass(frozen=True, slots=True)
class NormalizationSegment:
    source_start: int
    source_end: int
    normalized_start: int
    normalized_end: int
    original: str
    normalized: str
    operations: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.source_start < 0 or self.source_end < self.source_start:
            raise ValueError("invalid normalization source span")
        if self.normalized_start < 0 or self.normalized_end < self.normalized_start:
            raise ValueError("invalid normalization target span")


@dataclass(frozen=True, slots=True)
class ReversibleNormalization:
    normalization_ref: str
    original_text: str
    normalized_text: str
    segments: tuple[NormalizationSegment, ...]
    profile_ref: str = _NORMALIZATION_PROFILE

    def reverse(self) -> str:
        # NFKC/casefold is many-to-one. Exact source evidence, never an invented inverse
        # transform, is the reversal authority.
        return self.original_text

    def normalized_span_for(self, source_start: int, source_end: int) -> tuple[int, int]:
        if source_start < 0 or source_end < source_start or source_end > len(self.original_text):
            raise ValueError("invalid source span")
        touched = [
            item for item in self.segments
            if (item.source_end > source_start and item.source_start < source_end)
            or (source_start == source_end and item.source_start <= source_start <= item.source_end)
        ]
        if not touched:
            return (0, 0)
        return min(x.normalized_start for x in touched), max(x.normalized_end for x in touched)

    def original_span_for(self, normalized_start: int, normalized_end: int) -> tuple[int, int]:
        if normalized_start < 0 or normalized_end < normalized_start or normalized_end > len(self.normalized_text):
            raise ValueError("invalid normalized span")
        touched = [
            item for item in self.segments
            if (item.normalized_end > normalized_start and item.normalized_start < normalized_end)
            or (normalized_start == normalized_end and item.normalized_start <= normalized_start <= item.normalized_end)
        ]
        if not touched:
            return (0, 0)
        return min(x.source_start for x in touched), max(x.source_end for x in touched)


def _normalize(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def _operations(original: str, normalized: str) -> tuple[str, ...]:
    nfkc = unicodedata.normalize("NFKC", original)
    operations: list[str] = []
    if nfkc != original:
        operations.append("NFKC")
    if nfkc.casefold() != nfkc:
        operations.append("CASEFOLD")
    if normalized != _normalize(original):
        operations.append("ALIGNMENT_GROUP")
    return tuple(operations) or ("IDENTITY",)


def _segments(text: str, normalized_text: str) -> tuple[NormalizationSegment, ...]:
    if not text:
        return (NormalizationSegment(0, 0, 0, 0, "", "", ("IDENTITY",)),)

    result: list[NormalizationSegment] = []
    source = 0
    normalized = 0
    while source < len(text):
        selected_end: int | None = None
        selected_value: str | None = None
        local_limit = min(len(text), source + _MAX_LOCAL_ALIGNMENT_LOOKAHEAD)
        for end in range(source + 1, local_limit + 1):
            candidate = _normalize(text[source:end])
            if not normalized_text.startswith(candidate, normalized):
                continue
            # Commit only when adding the next code point cannot rewrite this candidate's
            # normalized prefix. This catches canonical composition and Hangul Jamo.
            if end < len(text):
                widened = _normalize(text[source : end + 1])
                if not widened.startswith(candidate):
                    continue
            selected_end = end
            selected_value = candidate
            break

        if selected_end is None:
            # Pathological normalization clusters can exceed local lookahead. Consume the
            # remaining source as one conservative evidence segment rather than enter an
            # unbounded quadratic search. The canonical normalized string remains exact;
            # only span attribution becomes deliberately coarser for the tail.
            selected_end = len(text)
            selected_value = _normalize(text[source:selected_end])
            if not normalized_text.startswith(selected_value, normalized):
                raise ValueError("Unicode normalization alignment could not be reconstructed")

        assert selected_value is not None
        end_normalized = normalized + len(selected_value)
        original = text[source:selected_end]
        result.append(
            NormalizationSegment(
                source,
                selected_end,
                normalized,
                end_normalized,
                original,
                selected_value,
                _operations(original, selected_value),
            )
        )
        source = selected_end
        normalized = end_normalized

    if normalized != len(normalized_text):
        raise ValueError("Unicode normalization alignment did not cover canonical output")
    return tuple(result)


def normalize_with_provenance(text: str) -> ReversibleNormalization:
    if not isinstance(text, str):
        raise TypeError("text must be str")
    normalized_text = _normalize(text)
    segments = _segments(text, normalized_text)
    payload = json.dumps(
        {
            "profile": _NORMALIZATION_PROFILE,
            "original": text,
            "normalized": normalized_text,
            "segments": [
                (
                    x.source_start, x.source_end, x.normalized_start, x.normalized_end,
                    x.original, x.normalized, x.operations,
                )
                for x in segments
            ],
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    ref = "normalization:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return ReversibleNormalization(ref, text, normalized_text, segments)


__all__ = ["NormalizationSegment", "ReversibleNormalization", "normalize_with_provenance"]
