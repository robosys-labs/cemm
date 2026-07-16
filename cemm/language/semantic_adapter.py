"""Generic v3.4.3 semantic-language adapter.

All lexical, token-expansion, construction, and discourse knowledge is supplied
by the selected semantic pack.  The adapter preserves source tokens while
matching virtual expansion components, so contractions and clitics do not
require language-specific kernel branches.
"""
from __future__ import annotations

from dataclasses import replace
import re

from .interfaces import (
    CommunicativeCandidate,
    ConstructionCandidate,
    LexicalSenseCandidate,
    PragmaticCue,
    RuleCandidate,
    SurfaceEvidence,
)
from .matcher import DeclarativeConstructionMatcher, TokenEvidence
from .semantic_pack import SemanticLanguagePack
from .stream import ContractionDecomposition, TokenKind
from .tokenizer import tokenize
from ..kernel.model.surface import LexicalFormRef, SurfaceSpan


_EXPRESSIVE_RUN = re.compile(r"([^\W\d_])\1+", flags=re.UNICODE)
_SUPPORT_OUTPUT_KINDS = frozenset({
    "pragmatic_cue",
    "discourse_cue",
    "politeness_cue",
})


class SemanticLanguageAdapter:
    adapter_version = "3.4.4"

    def __init__(
        self,
        pack: SemanticLanguagePack,
        *,
        passed_competence_case_refs: frozenset[str] | None = None,
    ) -> None:
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
        self._expansion_index: dict[str, object] = {}
        self._competence_refs = (
            passed_competence_case_refs
            if passed_competence_case_refs is not None
            else frozenset()
        )
        for expansion in pack.token_expansions:
            if not set(expansion.competence_case_refs) <= self._competence_refs:
                continue
            for surface in expansion.surface_forms:
                self._expansion_index[surface.casefold()] = expansion

    def perceive(
        self,
        raw_text: str,
        language_tag: str | None = None,
    ) -> SurfaceEvidence:
        tag = (language_tag or self._pack.language_tag).split("-", 1)[0]
        stream = tokenize(raw_text, language_tag=tag)
        stream, matcher_tokens, mappings_by_index = self._token_evidence(stream)
        all_matches = self._matcher.match(
            matcher_tokens,
            self._pack.input_constructions,
            passed_competence_case_refs=self._competence_refs,
        )

        content_by_clause = self._content_indices_by_clause(stream)
        support_matches = self._maximal_support_matches(tuple(
            match
            for match in all_matches
            if match.output_kind in _SUPPORT_OUTPUT_KINDS
        ))
        rule_matches = tuple(
            match for match in all_matches if match.output_kind == "rule"
        )
        ordinary_matches = tuple(
            match
            for match in all_matches
            if match.output_kind not in _SUPPORT_OUTPUT_KINDS
            and match.output_kind != "rule"
        )
        semantic_matches = self._select_clause_cover(
            ordinary_matches,
            support_matches,
            content_by_clause,
        )
        embedded_matches = self._embedded_rule_matches(
            ordinary_matches,
            rule_matches,
        )
        semantic_matches = self._dedupe_matches((
            *semantic_matches,
            *embedded_matches,
        ))
        rule_candidates = self._rule_candidates(rule_matches)

        support_indices = frozenset(
            index
            for match in support_matches
            for index in match.source_token_indices
        )
        constructed_predicates = frozenset(
            (match.predicate_key, index)
            for match in semantic_matches
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
            if index not in support_indices
            and (mapping.semantic_key, index) not in constructed_predicates
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
            for match in semantic_matches
        )
        communicative = tuple(
            CommunicativeCandidate(
                force=match.communicative_force,
                confidence=match.confidence,
                source_token_indices=match.source_token_indices,
            )
            for match in semantic_matches
            if match.communicative_force
            and not match.output_metadata.get("embedded_rule_ref")
        )
        pragmatic = tuple(
            PragmaticCue(
                cue_kind=str(
                    match.output_metadata.get("cue_kind", match.output_kind)
                ),
                value=str(match.output_metadata.get("cue_value", "present")),
                confidence=match.confidence,
                source_token_indices=match.source_token_indices,
                adds_candidates=False,
                replaces_content=False,
            )
            for match in support_matches
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
            rule_candidates=rule_candidates,
            communicative_candidates=communicative,
            pragmatic_cues=pragmatic,
            surface_spans=spans,
            language_tag=tag,
            overall_confidence=0.95 if constructions else 0.45,
            adapter_id=self.adapter_id,
            adapter_version=self.adapter_version,
        )


    @staticmethod
    def _maximal_support_matches(matches):
        """Drop nested cue matches when a more specific cue covers the span."""
        result = []
        for match in matches:
            source = frozenset(match.source_token_indices)
            if any(
                source < frozenset(other.source_token_indices)
                for other in matches
            ):
                continue
            key = (
                tuple(match.source_token_indices),
                match.output_metadata.get("cue_kind", match.output_kind),
            )
            if not any(
                (tuple(item.source_token_indices),
                 item.output_metadata.get("cue_kind", item.output_kind)) == key
                for item in result
            ):
                result.append(match)
        return tuple(result)

    @staticmethod
    def _content_indices_by_clause(stream) -> tuple[frozenset[int], ...]:
        result = []
        for clause in stream.clause_boundaries:
            result.append(frozenset(
                index
                for index, token in enumerate(stream.tokens)
                if token.start_offset >= clause.start_offset
                and token.end_offset <= clause.end_offset
                and token.kind not in {
                    TokenKind.PUNCTUATION,
                    TokenKind.WHITESPACE,
                    TokenKind.QUOTE_OPEN,
                    TokenKind.QUOTE_CLOSE,
                }
            ))
        return tuple(result) or (frozenset(),)

    @classmethod
    def _select_clause_cover(
        cls,
        matches,
        support_matches,
        content_by_clause,
    ):
        """Select a non-overlapping semantic cover for each clause.

        A clause may be composed from several independently licensed semantic
        constructions (for example acknowledgement + identity assertion).
        Unknown residue is never silently discarded.
        """
        selected = []
        for clause_content in content_by_clause:
            if not clause_content:
                continue
            support = frozenset(
                index
                for cue in support_matches
                if frozenset(cue.source_token_indices) <= clause_content
                for index in cue.source_token_indices
            )
            candidates = [
                match for match in matches
                if frozenset(match.source_token_indices)
                and frozenset(match.source_token_indices) <= clause_content
            ]
            covered = set(support)
            chosen = []
            while covered != set(clause_content):
                ranked = sorted(
                    (
                        match for match in candidates
                        if set(match.source_token_indices) - covered
                        and not (
                            set(match.source_token_indices) & covered
                            - set(support)
                        )
                    ),
                    key=lambda match: (
                        len(set(match.source_token_indices) - covered),
                        len(set(match.source_token_indices)),
                        match.confidence,
                    ),
                    reverse=True,
                )
                if not ranked:
                    break
                best = ranked[0]
                chosen.append(best)
                covered.update(best.source_token_indices)
            if covered == set(clause_content):
                selected.extend(chosen)
                continue
            # Preserve non-communicative local candidates, but do not authorize
            # a partial speech act as if the residue had been understood.
            selected.extend(
                match for match in candidates
                if not match.communicative_force
                and not match.output_metadata.get("requires_full_span")
            )
        return cls._dedupe_matches(tuple(selected))

    @staticmethod
    def _embedded_rule_matches(matches, rule_matches):
        result = []
        for rule in rule_matches:
            premise_key = str(rule.output_metadata.get("premise_capture", "premise"))
            conclusion_key = str(
                rule.output_metadata.get("conclusion_capture", "conclusion")
            )
            for side, capture_key in (
                ("premise", premise_key),
                ("conclusion", conclusion_key),
            ):
                capture = frozenset(rule.capture_token_indices.get(capture_key, ()))
                if not capture:
                    continue
                for match in matches:
                    source = frozenset(match.source_token_indices)
                    if source and source <= capture:
                        result.append(replace(
                            match,
                            output_metadata={
                                **dict(match.output_metadata),
                                "embedded_rule_ref": rule.construction_ref,
                                "rule_component_side": side,
                            },
                        ))
        return tuple(result)

    @staticmethod
    def _rule_candidates(rule_matches):
        return tuple(
            RuleCandidate(
                construction_key=match.construction_ref,
                rule_kind=str(match.output_metadata.get("rule_kind", "relational")),
                strength=str(match.output_metadata.get("strength", "defeasible")),
                causal_warrant=str(
                    match.output_metadata.get("causal_warrant", "reported_claim")
                ),
                premise_capture=str(
                    match.output_metadata.get("premise_capture", "premise")
                ),
                conclusion_capture=str(
                    match.output_metadata.get("conclusion_capture", "conclusion")
                ),
                premise_token_indices=tuple(match.capture_token_indices.get(
                    str(match.output_metadata.get("premise_capture", "premise")),
                    (),
                )),
                conclusion_token_indices=tuple(match.capture_token_indices.get(
                    str(match.output_metadata.get("conclusion_capture", "conclusion")),
                    (),
                )),
                confidence=match.confidence,
                source_token_indices=match.source_token_indices,
            )
            for match in rule_matches
        )

    @staticmethod
    def _dedupe_matches(matches):
        result = []
        seen = set()
        for match in matches:
            key = (
                match.construction_ref,
                tuple(match.source_token_indices),
                match.output_metadata.get("embedded_rule_ref", ""),
                match.output_metadata.get("rule_component_side", ""),
            )
            if key not in seen:
                seen.add(key)
                result.append(match)
        return tuple(result)

    def _token_evidence(self, stream):
        matcher_tokens: list[TokenEvidence] = []
        mappings_by_index: dict[int, tuple[object, ...]] = {}
        preserved_tokens = []

        for source_index, token in enumerate(stream.tokens):
            expansion = self._expansion_index.get(token.normalized_form.casefold())
            components = (
                tuple(str(value).casefold() for value in expansion.components)
                if expansion is not None
                else (token.normalized_form.casefold(),)
            )
            source_mappings: list[object] = []
            source_seen: set[str] = set()
            source_is_negation = False

            for component_index, component in enumerate(components):
                mappings: list[object] = []
                seen: set[str] = set()
                for variant in self._surface_variants(component):
                    for mapping in self._surface_index.get(variant, ()):
                        marker = getattr(mapping, "mapping_id", "")
                        if marker and marker not in seen:
                            mappings.append(mapping)
                            seen.add(marker)
                        if marker and marker not in source_seen:
                            source_mappings.append(mapping)
                            source_seen.add(marker)
                semantic_keys = frozenset(
                    getattr(mapping, "semantic_key", "")
                    for mapping in mappings
                    if getattr(mapping, "semantic_key", "")
                )
                source_is_negation = source_is_negation or any(
                    key.startswith("polarity:negative")
                    or key == "grammar:negation"
                    for key in semantic_keys
                )
                features = frozenset(
                    f"{key}:{value}"
                    for mapping in mappings
                    for key, value in getattr(
                        mapping, "morphological_features", {}
                    ).items()
                )
                lemma_candidates = tuple(dict.fromkeys(
                    lemma
                    for mapping in mappings
                    for lemma in getattr(mapping, "lemma_forms", ())
                )) or (component,)
                matcher_tokens.append(TokenEvidence(
                    token_index=source_index,
                    raw_form=token.raw_form,
                    normalized_form=component,
                    lemma_candidates=lemma_candidates,
                    semantic_keys=semantic_keys,
                    token_kind=(
                        token.kind.value
                        if hasattr(token.kind, "value")
                        else str(token.kind)
                    ),
                    features=features,
                    boundary_keys=frozenset({
                        "expansion:first" if component_index == 0 else "",
                        (
                            "expansion:last"
                            if component_index == len(components) - 1
                            else ""
                        ),
                    } - {""}),
                ))

            mappings_by_index[source_index] = tuple(source_mappings)
            preserved_tokens.append(replace(
                token,
                contraction=(
                    ContractionDecomposition(token.raw_form, components)
                    if expansion is not None
                    else token.contraction
                ),
                lemma_candidates=tuple(dict.fromkeys(
                    lemma
                    for mapping in source_mappings
                    for lemma in getattr(mapping, "lemma_forms", ())
                )) or token.lemma_candidates,
                is_negation=source_is_negation,
            ))

        return (
            replace(stream, tokens=tuple(preserved_tokens)),
            tuple(matcher_tokens),
            mappings_by_index,
        )

    @staticmethod
    def _surface_variants(surface: str) -> tuple[str, ...]:
        normalized = surface.casefold()
        collapsed = _EXPRESSIVE_RUN.sub(r"\1", normalized)
        return tuple(dict.fromkeys((normalized, collapsed)))
