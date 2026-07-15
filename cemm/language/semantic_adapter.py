"""Generic v3.4.3 semantic-language adapter.

All word and construction knowledge is supplied by the loaded semantic pack.
The adapter contains no English/French routing or transcript-specific regexes.
"""
from __future__ import annotations

from dataclasses import replace
import re

from .en.tokenizer import tokenize
from .interfaces import (
    CommunicativeCandidate,
    ConstructionCandidate,
    LexicalSenseCandidate,
    SurfaceEvidence,
)
from .matcher import DeclarativeConstructionMatcher, TokenEvidence
from .semantic_pack import SemanticLanguagePack
from ..kernel.model.surface import LexicalFormRef, SurfaceSpan


_EXPRESSIVE_RUN = re.compile(r"([^\W\d_])\1{2,}", flags=re.UNICODE)


class SemanticLanguageAdapter:
    adapter_version = "3.4.3"

    def __init__(self, pack: SemanticLanguagePack) -> None:
        self._pack = pack
        self.adapter_id = f"semantic-language-adapter:{pack.language_tag}"
        self.supported_language_tags = (pack.language_tag,)
        self._matcher = DeclarativeConstructionMatcher()
        self._surface_index: dict[str, tuple[object, ...]] = {}
        for mapping in pack.input_lexicon:
            for surface in mapping.surface_forms:
                key = surface.casefold()
                current = self._surface_index.get(key, ())
                self._surface_index[key] = (*current, mapping)
        self._competence_refs = frozenset(
            ref
            for construction in pack.input_constructions
            for ref in construction.competence_case_refs
        )

    def perceive(
        self,
        raw_text: str,
        language_tag: str | None = None,
    ) -> SurfaceEvidence:
        tag = language_tag or self._pack.language_tag
        stream = replace(tokenize(raw_text), language_tag=tag)
        tokens, mappings_by_index = self._token_evidence(stream)
        matches = self._matcher.match(
            tokens,
            self._pack.input_constructions,
            passed_competence_case_refs=self._competence_refs,
        )
        content_indices = frozenset(
            index
            for index, token in enumerate(stream.tokens)
            if (
                token.kind.value
                if hasattr(token.kind, "value")
                else str(token.kind)
            ) not in {"punctuation", "whitespace", "quote_open", "quote_close"}
        )
        matches = tuple(
            match
            for match in matches
            if not match.output_metadata.get("requires_full_span")
            or frozenset(match.source_token_indices) == content_indices
        )
        constructed_predicates = frozenset(
            (match.predicate_key, index)
            for match in matches
            for index in match.source_token_indices
        )

        lexical = tuple(
            LexicalSenseCandidate(
                lexical_form_ref=LexicalFormRef(
                    surface=stream.tokens[index].raw_form,
                    language_tag=tag,
                    normalised=stream.tokens[index].normalized_form,
                ),
                semantic_key=mapping.semantic_key,
                sense_rank=float(rank),
                confidence=0.95,
                source_token_indices=(index,),
            )
            for index, mappings in mappings_by_index.items()
            for rank, mapping in enumerate(mappings)
            if (mapping.semantic_key, index) not in constructed_predicates
        )
        constructions = tuple(
            ConstructionCandidate(
                construction_key=match.construction_ref,
                pattern=match.predicate_key,
                predicate_schema_ref=match.predicate_key,
                role_mappings={
                    role: indices[0]
                    for role, indices in match.role_token_indices.items()
                    if indices
                },
                open_role_refs=match.open_role_keys,
                communicative_force=match.communicative_force,
                confidence=match.confidence,
                source_token_indices=match.source_token_indices,
                output_kind=match.output_kind,
                metadata=dict(match.output_metadata),
            )
            for match in matches
        )
        communicative = tuple(
            CommunicativeCandidate(
                force=match.communicative_force,
                confidence=match.confidence,
                source_token_indices=match.source_token_indices,
            )
            for match in matches
            if match.communicative_force
        )
        spans = tuple(
            SurfaceSpan(
                signal_ref="",
                start=token.start_offset,
                end=token.end_offset,
                raw_text=token.raw_form,
                token_start=index,
                token_end=index,
            )
            for index, token in enumerate(stream.tokens)
        )
        return SurfaceEvidence(
            token_stream=stream,
            lexical_sense_candidates=lexical,
            construction_candidates=constructions,
            communicative_candidates=communicative,
            surface_spans=spans,
            language_tag=tag,
            overall_confidence=0.95 if constructions else 0.45,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
        )

    def _token_evidence(self, stream):
        tokens: list[TokenEvidence] = []
        mappings_by_index: dict[int, tuple[object, ...]] = {}
        for index, token in enumerate(stream.tokens):
            mappings: list[object] = []
            seen: set[str] = set()
            for variant in self._surface_variants(token.normalized_form):
                for mapping in self._surface_index.get(variant, ()):
                    marker = getattr(mapping, "mapping_id", "")
                    if marker and marker not in seen:
                        mappings.append(mapping)
                        seen.add(marker)
            mappings_by_index[index] = tuple(mappings)
            lemma_candidates = tuple(dict.fromkeys(
                lemma
                for mapping in mappings
                for lemma in getattr(mapping, "lemma_forms", ())
            )) or token.lemma_candidates or (token.normalized_form,)
            tokens.append(TokenEvidence(
                token_index=index,
                raw_form=token.raw_form,
                normalized_form=token.normalized_form,
                lemma_candidates=lemma_candidates,
                semantic_keys=frozenset(
                    getattr(mapping, "semantic_key", "")
                    for mapping in mappings
                    if getattr(mapping, "semantic_key", "")
                ),
                token_kind=(
                    token.kind.value
                    if hasattr(token.kind, "value")
                    else str(token.kind)
                ),
            ))
        return tuple(tokens), mappings_by_index

    @staticmethod
    def _surface_variants(surface: str) -> tuple[str, ...]:
        normalized = surface.casefold()
        collapsed = _EXPRESSIVE_RUN.sub(r"\1", normalized)
        return tuple(dict.fromkeys((normalized, collapsed)))
