"""PerceptToSurfaceEvidence — bridge from legacy MeaningPerceptPacket to v3.4 SurfaceEvidence.

Import boundary: model + language + understanding submodules only. No engine imports.

Architectural purpose (IMPLEMENTATION_PLAN.md Phase 4, UNDERSTANDING_PIPELINE.md §2-3):
- Converts the legacy MeaningPerceptPacket output of MeaningPerceptor into
  the canonical SurfaceEvidence required by SemanticComposer.
- Preserves raw text, token offsets, contraction structure, negation flags,
  clause boundaries, and quotation spans.
- Maps legacy referent atoms to LexicalSenseCandidate entries.
- Maps legacy predicate phrases / action atoms to ConstructionCandidate entries.
- Maps legacy intent atoms to CommunicativeCandidate entries.
- Maps legacy affect markers to PragmaticCue entries.
- Unknown content stays unknown — not converted to generic entities or durable facts.

This is a transitional bridge. Once a native v3.4 LanguageAdapter exists,
this bridge will be retired (Phase 12 — legacy retirement).
"""
from __future__ import annotations

from typing import Any

from ...language.interfaces import (
    SurfaceEvidence,
    LexicalSenseCandidate,
    ConstructionCandidate,
    CommunicativeCandidate,
    PragmaticCue,
)
from ...language.stream import (
    TokenStream,
    Token,
    TokenKind,
    MorphologicalFeature,
    ContractionDecomposition,
    ClauseBoundary,
    QuotationSpan,
    DependencyEdge,
)
from ..model.surface import SurfaceSpan as ModelSurfaceSpan, LexicalFormRef


# Common English contractions and their decompositions
_CONTRACTION_MAP: dict[str, tuple[str, ...]] = {
    "i'm": ("I", "am"),
    "don't": ("do", "not"),
    "doesn't": ("does", "not"),
    "didn't": ("did", "not"),
    "won't": ("will", "not"),
    "can't": ("can", "not"),
    "couldn't": ("could", "not"),
    "shouldn't": ("should", "not"),
    "wouldn't": ("would", "not"),
    "isn't": ("is", "not"),
    "aren't": ("are", "not"),
    "wasn't": ("was", "not"),
    "weren't": ("were", "not"),
    "haven't": ("have", "not"),
    "hasn't": ("has", "not"),
    "hadn't": ("had", "not"),
    "it's": ("it", "is"),
    "he's": ("he", "is"),
    "she's": ("she", "is"),
    "they're": ("they", "are"),
    "we're": ("we", "are"),
    "you're": ("you", "are"),
    "we've": ("we", "have"),
    "they've": ("they", "have"),
    "i've": ("I", "have"),
    "i'll": ("I", "will"),
    "he'll": ("he", "will"),
    "she'll": ("she", "will"),
    "we'll": ("we", "will"),
    "they'll": ("they", "will"),
    "you'll": ("you", "will"),
    "it'll": ("it", "will"),
    "that's": ("that", "is"),
    "what's": ("what", "is"),
    "who's": ("who", "is"),
    "where's": ("where", "is"),
    "how's": ("how", "is"),
}

# Negation words
_NEGATION_WORDS = frozenset({
    "not", "no", "never", "none", "nobody", "nothing",
    "nowhere", "neither", "nor", "cannot", "n't",
})


class PerceptToSurfaceEvidence:
    """Bridge from legacy MeaningPerceptPacket to v3.4 SurfaceEvidence.

    Converts the legacy percept's tokens, referents, predicate phrases,
    intents, and affect markers into the canonical SurfaceEvidence format
    required by SemanticComposer.

    Preserves raw forms, offsets, and structural annotations. Unknown
    content remains unknown — not converted to generic entities.
    """

    def convert(self, percept: Any) -> SurfaceEvidence:
        """Convert a MeaningPerceptPacket into SurfaceEvidence.

        Maps:
        - percept.tokens / normalized_tokens → TokenStream
        - percept.referents → LexicalSenseCandidate entries
        - percept.predicate_phrases / actions → ConstructionCandidate entries
        - percept.intents → CommunicativeCandidate entries
        - percept.affect_markers → PragmaticCue entries
        - percept.spans → SurfaceSpan entries
        """
        raw_text = getattr(percept, "raw_text", "") or ""
        language_tag = getattr(percept, "language", "und") or "und"
        tokens_list = getattr(percept, "tokens", []) or []
        normalized_tokens = getattr(percept, "normalized_tokens", []) or []
        cased_tokens = getattr(percept, "cased_tokens", []) or []
        normalized_forms = getattr(percept, "normalized_forms", []) or []
        punctuation_features = getattr(percept, "punctuation_features", {}) or {}

        # Build canonical Token stream
        token_stream = self._build_token_stream(
            raw_text=raw_text,
            tokens_list=tokens_list,
            normalized_tokens=normalized_tokens,
            cased_tokens=cased_tokens,
            normalized_forms=normalized_forms,
            language_tag=language_tag,
            punctuation_features=punctuation_features,
        )

        # Build lexical sense candidates from referents
        lexical_candidates = self._build_lexical_candidates(percept, token_stream)

        # Build construction candidates from predicate phrases and actions
        construction_candidates = self._build_construction_candidates(percept, token_stream)

        # Build communicative candidates from intents
        communicative_candidates = self._build_communicative_candidates(percept, token_stream)

        # Build pragmatic cues from affect markers
        pragmatic_cues = self._build_pragmatic_cues(percept, token_stream)

        # Build surface spans from percept spans
        surface_spans = self._build_surface_spans(percept, raw_text)

        return SurfaceEvidence(
            token_stream=token_stream,
            lexical_sense_candidates=tuple(lexical_candidates),
            construction_candidates=tuple(construction_candidates),
            communicative_candidates=tuple(communicative_candidates),
            pragmatic_cues=tuple(pragmatic_cues),
            surface_spans=tuple(surface_spans),
            language_tag=language_tag,
            overall_confidence=getattr(percept, "confidence", 0.5),
            adapter_id="percept_bridge",
            adapter_version="1.0",
        )

    def _build_token_stream(
        self,
        raw_text: str,
        tokens_list: list[str],
        normalized_tokens: list[str],
        cased_tokens: list[str],
        normalized_forms: list[str],
        language_tag: str,
        punctuation_features: dict[str, Any],
    ) -> TokenStream:
        """Build a canonical TokenStream from legacy percept token lists."""
        tokens: list[Token] = []
        offset = 0

        for i, tok_str in enumerate(tokens_list):
            raw_form = cased_tokens[i] if i < len(cased_tokens) else tok_str
            norm_form = (
                normalized_tokens[i] if i < len(normalized_tokens)
                else normalized_forms[i] if i < len(normalized_forms)
                else tok_str.lower()
            )

            # Find offset in raw text
            start_offset = raw_text.find(raw_form, offset)
            if start_offset == -1:
                start_offset = offset
            end_offset = start_offset + len(raw_form)
            offset = end_offset

            # Determine token kind
            kind = TokenKind.WORD
            is_negation = False
            contraction = None

            lower_raw = raw_form.lower()
            if lower_raw in _NEGATION_WORDS:
                kind = TokenKind.NEGATION
                is_negation = True
            elif "'" in raw_form and lower_raw in _CONTRACTION_MAP:
                kind = TokenKind.CONTRACTION
                components = _CONTRACTION_MAP[lower_raw]
                # Compute component offsets within the raw form
                comp_offsets: list[tuple[int, int]] = []
                search_start = 0
                for comp in components:
                    idx = raw_form.lower().find(comp.lower(), search_start)
                    if idx >= 0:
                        comp_offsets.append((idx, idx + len(comp)))
                        search_start = idx + len(comp)
                contraction = ContractionDecomposition(
                    raw_form=raw_form,
                    components=tuple(components),
                    component_offsets=tuple(comp_offsets),
                )
            elif raw_form in {",", ".", "!", "?", ";", ":", "-", "—"}:
                kind = TokenKind.PUNCTUATION
            elif raw_form in {'"', "'", "``", "''", "“", "”"}:
                kind = TokenKind.QUOTE_OPEN
            elif raw_form in {"'s", "'re", "'ve", "'ll", "'d", "'m"}:
                kind = TokenKind.CONTRACTION

            # Check if unknown lexeme
            is_unknown = False
            unknown_lexemes = punctuation_features.get("unknown_tokens", [])
            if raw_form.lower() in {ul.lower() if isinstance(ul, str) else ul.get("surface", "").lower()
                                     for ul in unknown_lexemes}:
                is_unknown = True
                kind = TokenKind.UNKNOWN

            tokens.append(Token(
                raw_form=raw_form,
                normalized_form=norm_form,
                start_offset=start_offset,
                end_offset=end_offset,
                kind=kind,
                language_tag=language_tag,
                is_negation=is_negation,
                is_unknown=is_unknown,
                contraction=contraction,
            ))

        # Build clause boundaries from meaning groups if available
        clause_boundaries: list[ClauseBoundary] = []

        # Build quotation spans from punctuation features
        quotation_spans: list[QuotationSpan] = []
        quote_spans_data = punctuation_features.get("quotation_spans", [])
        for qs in quote_spans_data:
            if isinstance(qs, dict):
                quotation_spans.append(QuotationSpan(
                    open_offset=qs.get("open_offset", 0),
                    close_offset=qs.get("close_offset", 0),
                    content_offsets=(qs.get("content_start", 0), qs.get("content_end", 0)),
                    quote_level=qs.get("level", 0),
                ))

        return TokenStream(
            tokens=tuple(tokens),
            clause_boundaries=tuple(clause_boundaries),
            quotation_spans=tuple(quotation_spans),
            language_tag=language_tag,
            overall_confidence=1.0,
            raw_text=raw_text,
        )

    def _build_lexical_candidates(
        self,
        percept: Any,
        stream: TokenStream,
    ) -> list[LexicalSenseCandidate]:
        """Build LexicalSenseCandidate entries from percept referents."""
        candidates: list[LexicalSenseCandidate] = []

        for ref in getattr(percept, "referents", []) or []:
            surface = getattr(ref, "surface", "")
            if not surface:
                continue

            # Find token indices for this referent
            token_indices = self._find_token_indices(stream, surface)

            # Build lexical form ref
            lex_ref = LexicalFormRef(
                surface=surface,
                language_tag=getattr(percept, "language", "und"),
                normalised=surface.lower(),
            )

            # Determine semantic key from entity type or surface
            entity_type = getattr(ref, "entity_type", "unknown")
            semantic_key = f"entity:{entity_type}:{surface.lower()}" if entity_type != "unknown" else surface.lower()

            candidates.append(LexicalSenseCandidate(
                lexical_form_ref=lex_ref,
                semantic_key=semantic_key,
                sense_rank=getattr(ref, "confidence", 0.5),
                evidence_kind="lexical",
                confidence=getattr(ref, "confidence", 0.5),
                source_token_indices=tuple(token_indices),
            ))

        return candidates

    def _build_construction_candidates(
        self,
        percept: Any,
        stream: TokenStream,
    ) -> list[ConstructionCandidate]:
        """Build ConstructionCandidate entries from predicate phrases and actions."""
        candidates: list[ConstructionCandidate] = []

        # From predicate phrases
        for pp in getattr(percept, "predicate_phrases", []) or []:
            surface = getattr(pp, "surface", "") or getattr(pp, "predicate_surface", "")
            if not surface:
                continue

            token_indices = self._find_token_indices(stream, surface)
            predicate_key = getattr(pp, "predicate_key", "")
            if not predicate_key:
                continue

            # Build role mappings from the predicate phrase
            role_mappings: dict[str, int] = {}
            for role_attr in ("actor_role", "object_role", "target_role", "place_role"):
                role_val = getattr(pp, role_attr, None)
                if role_val and isinstance(role_val, str):
                    idx = self._find_token_index(stream, role_val)
                    if idx >= 0:
                        role_mappings[role_attr.replace("_role", "")] = idx

            candidates.append(ConstructionCandidate(
                construction_key=f"pred:{predicate_key}",
                pattern=surface,
                predicate_schema_ref=f"schema:{predicate_key}",
                role_mappings=role_mappings,
                confidence=getattr(pp, "confidence", 0.5),
                source_token_indices=tuple(token_indices),
            ))

        # From action atoms
        for action in getattr(percept, "actions", []) or []:
            surface = getattr(action, "surface", "")
            if not surface:
                continue

            token_indices = self._find_token_indices(stream, surface)
            action_key = getattr(action, "action_key", "")
            if not action_key:
                continue

            role_mappings: dict[str, int] = {}
            for role_attr in ("actor_role", "object_role", "target_role", "place_role"):
                role_val = getattr(action, role_attr, None)
                if role_val and isinstance(role_val, str):
                    idx = self._find_token_index(stream, role_val)
                    if idx >= 0:
                        role_mappings[role_attr.replace("_role", "")] = idx

            candidates.append(ConstructionCandidate(
                construction_key=f"action:{action_key}",
                pattern=surface,
                predicate_schema_ref=f"schema:{action_key}",
                role_mappings=role_mappings,
                confidence=getattr(action, "confidence", 0.5),
                source_token_indices=tuple(token_indices),
            ))

        # From relation atoms
        for rel in getattr(percept, "relations", []) or []:
            surface = getattr(rel, "surface", "")
            relation_key = getattr(rel, "relation_key", "")
            if not relation_key:
                continue

            token_indices = self._find_token_indices(stream, surface) if surface else ()

            role_mappings: dict[str, int] = {}
            source_role = getattr(rel, "source_role", "")
            target_role = getattr(rel, "target_role", "")
            if source_role:
                idx = self._find_token_index(stream, source_role)
                if idx >= 0:
                    role_mappings["source"] = idx
            if target_role:
                idx = self._find_token_index(stream, target_role)
                if idx >= 0:
                    role_mappings["target"] = idx

            candidates.append(ConstructionCandidate(
                construction_key=f"relation:{relation_key}",
                pattern=surface or relation_key,
                predicate_schema_ref=f"schema:{relation_key}",
                role_mappings=role_mappings,
                confidence=getattr(rel, "confidence", 0.5),
                source_token_indices=tuple(token_indices),
            ))

        return candidates

    def _build_communicative_candidates(
        self,
        percept: Any,
        stream: TokenStream,
    ) -> list[CommunicativeCandidate]:
        """Build CommunicativeCandidate entries from percept intents."""
        candidates: list[CommunicativeCandidate] = []

        for intent in getattr(percept, "intents", []) or []:
            intent_key = getattr(intent, "intent_key", "statement")
            surface = getattr(intent, "surface", "")

            # Map legacy intent keys to v3.4 communicative forces
            force = self._map_intent_to_force(intent_key, intent)

            token_indices = self._find_token_indices(stream, surface) if surface else ()

            candidates.append(CommunicativeCandidate(
                force=force,
                confidence=getattr(intent, "confidence", 0.5),
                evidence_kind="syntactic",
                source_token_indices=tuple(token_indices),
            ))

        # If no intents detected, try to infer from punctuation
        if not candidates and stream.tokens:
            last_token = stream.tokens[-1]
            if last_token.kind == TokenKind.PUNCTUATION:
                if last_token.raw_form == "?":
                    candidates.append(CommunicativeCandidate(
                        force="ask",
                        confidence=0.7,
                        evidence_kind="syntactic",
                        source_token_indices=(len(stream.tokens) - 1,),
                    ))
                elif last_token.raw_form == "!":
                    candidates.append(CommunicativeCandidate(
                        force="direct",
                        confidence=0.6,
                        evidence_kind="syntactic",
                        source_token_indices=(len(stream.tokens) - 1,),
                    ))
                else:
                    candidates.append(CommunicativeCandidate(
                        force="assert",
                        confidence=0.5,
                        evidence_kind="syntactic",
                        source_token_indices=(len(stream.tokens) - 1,),
                    ))
            else:
                candidates.append(CommunicativeCandidate(
                    force="assert",
                    confidence=0.4,
                    evidence_kind="syntactic",
                ))

        return candidates

    def _build_pragmatic_cues(
        self,
        percept: Any,
        stream: TokenStream,
    ) -> list[PragmaticCue]:
        """Build PragmaticCue entries from affect markers."""
        cues: list[PragmaticCue] = []

        for marker in getattr(percept, "affect_markers", []) or []:
            if isinstance(marker, dict):
                cue_kind = marker.get("kind", "affect")
                value = marker.get("value", marker.get("emotion", ""))
                confidence = marker.get("confidence", 0.5)
            else:
                cue_kind = "affect"
                value = getattr(marker, "emotion", str(marker))
                confidence = getattr(marker, "confidence", 0.5)

            cues.append(PragmaticCue(
                cue_kind=cue_kind,
                value=value,
                confidence=confidence,
                adds_candidates=True,
                replaces_content=False,
            ))

        return cues

    def _build_surface_spans(
        self,
        percept: Any,
        raw_text: str,
    ) -> list[ModelSurfaceSpan]:
        """Build SurfaceSpan entries from percept spans."""
        from ..model.refs import FrozenMap

        spans: list[ModelSurfaceSpan] = []

        for span in getattr(percept, "spans", []) or []:
            signal_ref = getattr(percept, "signal_id", "")
            start = getattr(span, "start_token", 0)
            end = getattr(span, "end_token", 0)
            surface = getattr(span, "surface", "")

            # Compute character offsets from token positions
            char_start = raw_text.find(surface) if surface else 0
            char_end = char_start + len(surface) if surface else 0

            spans.append(ModelSurfaceSpan(
                signal_ref=signal_ref,
                start=char_start,
                end=char_end,
                raw_text=surface,
                token_start=start,
                token_end=end,
                features=FrozenMap(),
            ))

        return spans

    def _find_token_indices(self, stream: TokenStream, surface: str) -> tuple[int, ...]:
        """Find all token indices whose raw or normalized form matches the surface."""
        if not surface:
            return ()
        lower = surface.lower()
        indices: list[int] = []
        for i, token in enumerate(stream.tokens):
            if token.raw_form.lower() == lower or token.normalized_form == lower:
                indices.append(i)
        if not indices:
            # Try substring match for multi-word surfaces
            for i, token in enumerate(stream.tokens):
                if lower in token.raw_form.lower() or token.raw_form.lower() in lower:
                    indices.append(i)
        return tuple(indices)

    def _find_token_index(self, stream: TokenStream, surface: str) -> int:
        """Find the first token index matching the surface. Returns -1 if not found."""
        indices = self._find_token_indices(stream, surface)
        return indices[0] if indices else -1

    def _map_intent_to_force(self, intent_key: str, intent: Any) -> str:
        """Map legacy intent keys to v3.4 communicative forces.

        v3.4 forces: assert, ask, request, direct, acknowledge, correct, promise, refuse
        """
        is_question = getattr(intent, "is_question", False)
        is_command = getattr(intent, "is_command", False)
        is_teaching = getattr(intent, "is_teaching", False)
        is_repair = getattr(intent, "is_repair", False)

        if is_question or intent_key == "question":
            return "ask"
        if is_command or intent_key == "command":
            return "direct"
        if is_teaching:
            return "assert"
        if is_repair:
            return "correct"
        if intent_key == "refuse":
            return "refuse"
        if intent_key == "acknowledge":
            return "acknowledge"
        if intent_key == "promise":
            return "promise"
        if intent_key == "request":
            return "request"
        return "assert"
