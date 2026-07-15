"""Native English surface-evidence adapter backed by schema lexical indices."""
from __future__ import annotations

from typing import Any
import re

from .tokenizer import tokenize
from .constructions import detect_constructions
from ..interfaces import SurfaceEvidence


class EnglishLanguageAdapter:
    adapter_id = "english-native-v34.1"
    adapter_version = "1.1.0"
    supported_language_tags = ("en", "en-US", "en-GB")

    def __init__(self, schema_store: Any | None = None) -> None:
        self._store = schema_store

    def perceive(self, raw_text: str, language_tag: str = "en") -> SurfaceEvidence:
        stream = tokenize(raw_text)
        lexical, constructions, communicative, cues, spans = detect_constructions(
            stream,
            lexical_lookup=self._lookup,
            construction_schemas=self._construction_schemas(language_tag),
        )
        return SurfaceEvidence(
            token_stream=stream,
            lexical_sense_candidates=lexical,
            construction_candidates=constructions,
            communicative_candidates=communicative,
            pragmatic_cues=cues,
            surface_spans=spans,
            language_tag=language_tag,
            overall_confidence=0.85,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
        )

    def _lookup(self, surface: str, lemma: str, language: str) -> tuple[str, ...]:
        if self._store is None:
            return ()
        keys: list[str] = []
        normalized_candidates = tuple(dict.fromkeys((surface.casefold(), lemma.casefold())))
        for candidate in normalized_candidates:
            keys.extend(self._store.lookup_lexical_form(candidate, language))
        if not keys:
            # Orthographic accommodation is candidate evidence, not semantic
            # authority.  Only reduce an elongated final character and only
            # when the reduced form already has indexed senses.
            for candidate in normalized_candidates:
                reduced = re.sub(r"(.)\1+$", r"\1", candidate)
                if reduced != candidate:
                    keys.extend(self._store.lookup_lexical_form(reduced, language))
        return tuple(dict.fromkeys(keys))

    def _construction_schemas(self, language: str) -> tuple[Any, ...]:
        if self._store is None:
            return ()
        schemas = []
        for envelope in self._store.records_by_kind("construction"):
            payload = getattr(envelope, "payload", None)
            if getattr(payload, "language_tag", "") == language:
                schemas.append(payload)
        return tuple(schemas)
