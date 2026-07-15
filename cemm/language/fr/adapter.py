"""French adapter using the shared declarative matcher."""
from __future__ import annotations
from dataclasses import replace
from typing import Any
from ..en.tokenizer import tokenize
from ..interfaces import (
    CommunicativeCandidate,
    ConstructionCandidate,
    LexicalSenseCandidate,
    PragmaticCue,
    RuleCandidate,
    SurfaceEvidence,
)
from ..matcher import DeclarativeConstructionMatcher, TokenEvidence
from ..pack import LanguagePackRegistry
from cemm.kernel.model.surface import LexicalFormRef
from ...kernel.model.surface import SurfaceSpan

class FrenchLanguageAdapter:
    adapter_id = "data-language-adapter:fr"
    adapter_version = "3.0.0"
    supported_language_tags = ("fr", "fr-FR")

    def __init__(self, schema_store: Any, language_registry: LanguagePackRegistry):
        self._store = schema_store
        self._registry = language_registry
        self._matcher = DeclarativeConstructionMatcher()

    def perceive(self, raw_text: str, language_tag: str = "fr") -> SurfaceEvidence:
        pack = self._registry.require(language_tag)
        stream = replace(tokenize(raw_text), language_tag=language_tag)
        tokens = self._build_token_evidence(stream)
        construction_matches = self._matcher.match(
            tokens, pack.constructions,
            passed_competence_case_refs=frozenset(),
        )

        lexical = self._build_lexical(tokens, language_tag)
        constructions = tuple(
            ConstructionCandidate(
                construction_key=m.construction_ref,
                pattern=m.predicate_key,
                predicate_schema_ref=m.predicate_key,
                role_mappings={
                    role: indices[0]
                    for role, indices in m.role_token_indices.items()
                },
                open_role_refs=m.open_role_keys,
                communicative_force=m.communicative_force,
                confidence=m.confidence,
                source_token_indices=m.source_token_indices,
                output_kind=m.output_kind,
                metadata=m.output_metadata,
            )
            for m in construction_matches
        )

        cues = self._detect_pragmatic_cues(tokens, constructions, lexical)
        spans = self._build_spans(stream)

        return SurfaceEvidence(
            token_stream=stream,
            lexical_sense_candidates=lexical,
            construction_candidates=constructions,
            rule_candidates=(),
            communicative_candidates=(),
            pragmatic_cues=cues,
            surface_spans=spans,
            language_tag=language_tag,
            overall_confidence=0.75,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
        )

    def _build_token_evidence(self, stream):
        result = []
        for index, token in enumerate(stream.tokens if hasattr(stream, 'tokens') else stream):
            keys = frozenset(
                self._store.lookup_lexical_form(
                    token.normalized_form.casefold(), "fr"
                )
            )
            result.append(TokenEvidence(
                token_index=index,
                raw_form=token.raw_form,
                normalized_form=token.normalized_form,
                lemma_candidates=token.lemma_candidates or (token.normalized_form,),
                semantic_keys=keys,
                token_kind=token.kind.value if hasattr(token.kind, 'value') else str(token.kind),
            ))
        return tuple(result)

    def _build_lexical(self, tokens, language_tag):
        result = []
        seen = set()
        for token in tokens:
            for semantic_key in token.semantic_keys:
                if semantic_key not in seen:
                    seen.add(semantic_key)
                    result.append(LexicalSenseCandidate(
                        lexical_form_ref=LexicalFormRef(
                            surface=token.normalized_form,
                            language_tag=language_tag,
                            normalised=token.normalized_form,
                        ),
                        semantic_key=semantic_key,
                        confidence=0.9,
                        source_token_indices=(token.token_index,),
                    ))
        return tuple(result)

    def _detect_pragmatic_cues(self, tokens, constructions, lexical):
        return ()

    def _build_spans(self, stream):
        return tuple(
            SurfaceSpan(
                signal_ref="",
                start=token.start_offset,
                end=token.end_offset,
                raw_text=token.raw_form,
                token_start=index,
                token_end=index,
            )
            for index, token in enumerate(stream.tokens if hasattr(stream, 'tokens') else stream)
        )
