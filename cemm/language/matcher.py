"""Generic reversible matcher for declarative input constructions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..kernel.schema.construction import InputConstructionSchema, MatchKind


@dataclass(frozen=True, slots=True)
class TokenEvidence:
    token_index: int
    raw_form: str
    normalized_form: str
    lemma_candidates: tuple[str, ...]
    semantic_keys: frozenset[str]
    token_kind: str = ""
    features: frozenset[str] = frozenset()
    boundary_keys: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class ConstructionMatch:
    construction_ref: str
    predicate_key: str
    role_token_indices: dict[str, tuple[int, ...]]
    open_role_keys: tuple[str, ...]
    communicative_force: str
    polarity: str
    modality: str
    output_kind: str
    output_metadata: dict[str, Any]
    source_token_indices: tuple[int, ...]
    confidence: float
    evidence_refs: tuple[str, ...]


class DeclarativeConstructionMatcher:
    def match(
        self,
        tokens: tuple[TokenEvidence, ...],
        constructions: Iterable[InputConstructionSchema],
        *,
        passed_competence_case_refs: frozenset[str],
    ) -> tuple[ConstructionMatch, ...]:
        result: list[ConstructionMatch] = []
        for construction in sorted(
            constructions,
            key=lambda item: (item.priority, len(item.terms)),
            reverse=True,
        ):
            if not set(construction.competence_case_refs) <= passed_competence_case_refs:
                continue
            result.extend(self._match_construction(tokens, construction))
        return tuple(result)

    def _match_construction(self, tokens, construction):
        result = []
        for start in range(len(tokens)):
            cursor = start
            captures: dict[str, tuple[int, ...]] = {}
            consumed: list[int] = []
            failed = False
            for term in construction.terms:
                matched: list[int] = []
                while (
                    cursor < len(tokens)
                    and len(matched) < term.maximum_occurs
                    and self._term_matches(term, tokens[cursor])
                ):
                    matched.append(tokens[cursor].token_index)
                    consumed.append(tokens[cursor].token_index)
                    cursor += 1
                if len(matched) < term.minimum_occurs:
                    failed = True
                    break
                if term.capture_key and matched:
                    captures[term.capture_key] = tuple(dict.fromkeys(matched))
            if failed or not consumed:
                continue
            if not self._post_constraints_hold(construction, captures, tokens):
                continue
            role_map = {
                role_key: captures[capture_key]
                for role_key, capture_key in construction.role_capture_map.items()
                if capture_key in captures
            }
            source_indices = tuple(dict.fromkeys(consumed))
            result.append(ConstructionMatch(
                construction_ref=construction.schema_id,
                predicate_key=construction.predicate_key,
                role_token_indices=role_map,
                open_role_keys=construction.open_role_keys,
                communicative_force=construction.communicative_force,
                polarity=construction.polarity,
                modality=construction.modality,
                output_kind=construction.output_kind,
                output_metadata=construction.output_metadata,
                source_token_indices=source_indices,
                confidence=0.9,
                evidence_refs=tuple(f"token:{index}" for index in source_indices),
            ))
        return tuple(result)

    def _term_matches(self, term, token):
        if not term.constraints:
            return True
        return all(
            self._constraint_matches(constraint, token)
            for constraint in term.constraints
        )

    @staticmethod
    def _constraint_matches(constraint, token):
        values = set(constraint.values)
        if constraint.kind is MatchKind.ANY:
            matched = True
        elif constraint.kind is MatchKind.SURFACE:
            matched = token.normalized_form.casefold() in {
                value.casefold() for value in values
            }
        elif constraint.kind is MatchKind.LEMMA:
            matched = bool(
                {value.casefold() for value in values}
                & {lemma.casefold() for lemma in token.lemma_candidates}
            )
        elif constraint.kind is MatchKind.SEMANTIC_KEY:
            matched = bool(token.semantic_keys & values)
        elif constraint.kind is MatchKind.SEMANTIC_PREFIX:
            matched = any(
                key.startswith(prefix)
                for key in token.semantic_keys
                for prefix in values
            )
        elif constraint.kind is MatchKind.TOKEN_KIND:
            matched = token.token_kind in values
        elif constraint.kind is MatchKind.FEATURE:
            matched = bool(token.features & values)
        elif constraint.kind is MatchKind.BOUNDARY:
            matched = bool(token.boundary_keys & values)
        else:
            matched = False
        return not matched if constraint.negate else matched

    @staticmethod
    def _post_constraints_hold(construction, captures, tokens):
        # Token expansions may create several matcher tokens that point to the
        # same preserved source token.  Aggregate their semantic evidence rather
        # than allowing the last virtual component to overwrite earlier ones.
        keys_by_index: dict[int, set[str]] = {}
        for token in tokens:
            keys_by_index.setdefault(token.token_index, set()).update(
                token.semantic_keys
            )
        for constraint in construction.post_constraints:
            indices = captures.get(constraint.capture_key, ())
            keys = {
                key
                for index in indices
                for key in keys_by_index.get(index, ())
            }
            if constraint.constraint_kind == "semantic_in":
                passed = bool(keys & set(constraint.values))
            elif constraint.constraint_kind == "semantic_not_in":
                passed = not bool(keys & set(constraint.values))
            elif constraint.constraint_kind == "capture_present":
                passed = bool(indices)
            elif constraint.constraint_kind == "captures_distinct":
                other = captures.get(constraint.other_capture_key, ())
                passed = set(indices).isdisjoint(other)
            else:
                return False
            if constraint.negate:
                passed = not passed
            if not passed:
                return False
        return True
