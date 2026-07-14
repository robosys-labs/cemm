"""English language adapter — native v3.4 perception.

Implements the LanguageAdapter protocol from interfaces.py.
Produces SurfaceEvidence directly from raw text — no legacy
MeaningPerceptor dependency.

Per UNDERSTANDING_PIPELINE.md §2:
- Language adapters emit reversible surface evidence only.
- They may NOT select final meaning, authorize writes, declare truth,
  answer queries, mutate memory, claim capabilities, or choose
  response content.
- Unknown content is never converted into a generic entity.

Per completion-plan.md Stage 2:
- This replaces the legacy v3.3 percept path for English.
- Multilingual adapters can target the same SurfaceEvidence interface.
"""
from __future__ import annotations

from .tokenizer import tokenize
from .constructions import detect_constructions
from ..interfaces import SurfaceEvidence


class EnglishLanguageAdapter:
    """Native English language adapter.

    Produces SurfaceEvidence from raw English text.
    Implements the LanguageAdapter protocol.
    """

    adapter_id = "english-native-v34"
    adapter_version = "1.0.0"
    supported_language_tags = ("en", "en-US", "en-GB")

    def perceive(self, raw_text: str, language_tag: str = "en") -> SurfaceEvidence:
        """Perceive raw English text into reversible SurfaceEvidence.

        This is the sole output of language perception. It contains
        candidate lexical senses, constructions, communicative forces,
        and pragmatic cues — all as proposals, not selections.
        """
        # 1. Tokenize
        stream = tokenize(raw_text)

        # 2. Detect constructions
        lexical, constructions, communicative, cues, spans = detect_constructions(stream)

        # 3. Build SurfaceEvidence
        return SurfaceEvidence(
            token_stream=stream,
            lexical_sense_candidates=lexical,
            construction_candidates=constructions,
            communicative_candidates=communicative,
            pragmatic_cues=cues,
            surface_spans=spans,
            language_tag="en",
            overall_confidence=0.85,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
        )
