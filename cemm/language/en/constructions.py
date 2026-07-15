"""English construction evidence over a canonical token stream.

This module proposes compositional structures. It does not declare truth,
select a sense, or turn an unknown word into an entity.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..interfaces import (
    CommunicativeCandidate,
    ConstructionCandidate,
    LexicalSenseCandidate,
    PragmaticCue,
)
from ..stream import Token, TokenKind, TokenStream
from ...kernel.model.surface import LexicalFormRef, SurfaceSpan

LexicalLookup = Callable[[str, str, str], tuple[str, ...]]

_GRAMMATICAL_SENSES: dict[str, str] = {
    "i": "pronoun:first_person", "me": "pronoun:first_person",
    "my": "pronoun:first_person_possessive",
    "you": "pronoun:second_person", "your": "pronoun:second_person_possessive",
    "he": "pronoun:third_person", "she": "pronoun:third_person",
    "it": "pronoun:third_person", "we": "pronoun:first_person_plural",
    "they": "pronoun:third_person_plural",
    "what": "wh:what", "which": "wh:which", "who": "wh:who",
    "where": "wh:where", "when": "wh:when", "why": "wh:why", "how": "wh:how",
    "something": "pronoun:indefinite",
    "is": "copula:be", "are": "copula:be", "am": "copula:be",
    "was": "copula:be", "were": "copula:be", "be": "copula:be",
    "do": "aux:do", "does": "aux:do", "did": "aux:do",
    "dont": "aux:do",
    "a": "determiner:indefinite", "an": "determiner:indefinite",
    "the": "determiner:definite", "not": "polarity:negative",
}
_WH = frozenset({"what", "which", "who", "where", "when", "why", "how"})
_AUX = frozenset({
    "do", "does", "did", "dont", "can", "could", "will", "would", "should", "have",
    "has", "had", "is", "are", "was", "were", "might", "must", "may",
})
_COPULA = frozenset({"is", "are", "am", "was", "were", "be"})
_DET = frozenset({"a", "an", "the"})
_GENERIC_COMPLEMENT_FILLERS = frozenset({"something"})


def detect_constructions(
    stream: TokenStream,
    lexical_lookup: LexicalLookup | None = None,
    construction_schemas: tuple[Any, ...] = (),
) -> tuple[
    tuple[LexicalSenseCandidate, ...],
    tuple[ConstructionCandidate, ...],
    tuple[CommunicativeCandidate, ...],
    tuple[PragmaticCue, ...],
    tuple[SurfaceSpan, ...],
]:
    lexical: list[LexicalSenseCandidate] = []
    constructions: list[ConstructionCandidate] = []
    communicative: list[CommunicativeCandidate] = []
    cues: list[PragmaticCue] = []
    spans: list[SurfaceSpan] = []

    words = [
        (i, token) for i, token in enumerate(stream.tokens)
        if token.kind in {TokenKind.WORD, TokenKind.CONTRACTION, TokenKind.NEGATION}
    ]
    for index, token in words:
        lemma = _lemma(token)
        keys = []
        grammatical = _GRAMMATICAL_SENSES.get(lemma)
        if grammatical:
            keys.append(grammatical)
        if lexical_lookup is not None:
            keys.extend(lexical_lookup(token.normalized_form, lemma, stream.language_tag))
        if not keys:
            keys.append(f"opaque:{stream.language_tag}:{lemma}")
        for rank, key in enumerate(dict.fromkeys(keys)):
            opaque = key.startswith("opaque:")
            lexical.append(
                LexicalSenseCandidate(
                    lexical_form_ref=LexicalFormRef(
                        surface=token.raw_form,
                        language_tag=stream.language_tag,
                        normalised=token.normalized_form,
                    ),
                    semantic_key=key,
                    sense_rank=1.0 / (rank + 1),
                    evidence_kind="lexical",
                    confidence=0.0 if opaque else 0.85 / (rank + 1),
                    source_token_indices=(index,),
                )
            )
        spans.append(
            SurfaceSpan(
                signal_ref="",
                start=token.start_offset,
                end=token.end_offset,
                raw_text=token.raw_form,
                token_start=index,
                token_end=index + 1,
            )
        )

    schemas = _SchemaIndex(construction_schemas)
    _copular(words, constructions, schemas)
    _question(words, constructions, communicative, schemas)
    _complement(words, constructions, schemas)

    if not communicative:
        communicative.append(
            CommunicativeCandidate(
                force="ask" if stream.raw_text.rstrip().endswith("?") else "assert",
                confidence=0.85 if stream.raw_text.rstrip().endswith("?") else 0.6,
                source_token_indices=(words[0][0],) if words else (),
            )
        )

    semantic_keys = {candidate.semantic_key for candidate in lexical}
    if "greet" in semantic_keys and len(words) <= 3:
        cues.append(PragmaticCue("greeting", "present", 0.95))
    if words and _lemma(words[0][1]) in _WH and len(words) <= 4:
        finite = any(_lemma(token) in _AUX | _COPULA for _, token in words[1:])
        if not finite:
            cues.append(PragmaticCue("elliptical_clarification_query", "pending_context", 0.8))
    for index, token in enumerate(stream.tokens):
        if token.is_negation:
            cues.append(PragmaticCue("negation_scope", "negative", 1.0, (index,)))

    return tuple(lexical), tuple(constructions), tuple(communicative), tuple(cues), tuple(spans)


def _copular(
    words: list[tuple[int, Token]],
    constructions: list[ConstructionCandidate],
    schemas: "_SchemaIndex",
) -> None:
    for position, (index, token) in enumerate(words):
        components = tuple(part.lower() for part in token.contraction.components) if token.contraction else ()
        lemma = _lemma(token)
        embedded = next((part for part in components if part in _COPULA), "")
        if lemma not in _COPULA and not embedded:
            continue

        if embedded:
            subject_index = index
            subject_lemma = components[0] if components else lemma
        elif position > 0:
            subject_index = words[position - 1][0]
            subject_lemma = _lemma(words[position - 1][1])
        else:
            continue
        if subject_lemma in _WH:
            continue

        cursor = position + 1
        if cursor < len(words) and _lemma(words[cursor][1]) in _DET:
            cursor += 1
        if cursor < len(words) and _lemma(words[cursor][1]) in _GENERIC_COMPLEMENT_FILLERS:
            cursor += 1
        if cursor >= len(words):
            continue
        complement_index = words[cursor][0]

        captures = {"subject": subject_index, "complement": complement_index}
        if subject_lemma in {"i", "you", "he", "she", "it", "we", "they"}:
            schema = schemas.first(
                "[subject] [copula] [category]",
                "subject_is_deictic_or_referential",
            )
        else:
            schema = schemas.first(
                "[subject] [copula] [category]",
                "subject_is_not_deictic_pronoun",
            )
        candidate = _candidate_from_schema(schema, captures, 0.88, (index,))
        if candidate is not None:
            constructions.append(candidate)


def _question(
    words: list[tuple[int, Token]],
    constructions: list[ConstructionCandidate],
    communicative: list[CommunicativeCandidate],
    schemas: "_SchemaIndex",
) -> None:
    if not words:
        return
    first = _lemma(words[0][1])
    desire = _desire_knowledge_question(words, schemas)
    if desire is not None:
        constructions.append(desire)
        _append_force(communicative, desire, 0.9, desire.source_token_indices)
        return
    if first in _WH:
        if (
            first == "how"
            and len(words) >= 3
            and _lemma(words[1][1]) in _COPULA
            and _lemma(words[2][1]) in {
                "i", "you", "he", "she", "it", "we", "they"
            }
        ):
            schema = schemas.first("[wh:how] [copula] [holder]")
            indices = (words[0][0], words[1][0], words[2][0])
            candidate = _candidate_from_schema(schema, {"holder": words[2][0]}, 0.94, indices)
            if candidate is not None:
                constructions.append(candidate)
                _append_force(communicative, candidate, 0.97, indices)
            return

        # Direct definitional question: "what is [a] president?"
        if first == "what" and len(words) >= 3 and _lemma(words[1][1]) in _COPULA:
            cursor = 2
            if cursor < len(words) and _lemma(words[cursor][1]) in _DET:
                cursor += 1
            if cursor < len(words):
                schema = schemas.first("[wh:what] [copula] [kind]")
                indices = (words[0][0], words[1][0])
                candidate = _candidate_from_schema(schema, {"kind": words[cursor][0]}, 0.94, indices)
                if candidate is not None:
                    constructions.append(candidate)
                    _append_force(communicative, candidate, 0.97, indices)
                return

        # Lexical meaning question: "what does X mean?"
        if (
            len(words) >= 4
            and _lemma(words[1][1]) in {"do", "does", "did"}
            and _lemma(words[-1][1]) == "mean"
        ):
            schema = schemas.first("[wh:what] [aux:do] [lexical_form] [lemma:mean]")
            indices = (words[0][0], words[-1][0])
            candidate = _candidate_from_schema(schema, {"lexical_form": words[2][0]}, 0.94, indices)
            if candidate is not None:
                constructions.append(candidate)
                _append_force(communicative, candidate, 0.97, indices)
            return

        schema = schemas.first("[wh] [clause]")
        indices = (words[0][0],)
        candidate = _candidate_from_schema(schema, {"wh": words[0][0]}, 0.9, indices)
        if candidate is not None:
            constructions.append(candidate)
            _append_force(communicative, candidate, 0.96, indices)
    elif first in _AUX:
        captures = {"auxiliary": words[0][0]}
        if len(words) > 1:
            captures["subject"] = words[1][0]
        if len(words) > 2:
            captures["predicate"] = words[2][0]
        schema = schemas.first("[aux] [subject] [predicate]")
        indices = (words[0][0],)
        candidate = _candidate_from_schema(schema, captures, 0.88, indices)
        if candidate is not None:
            constructions.append(candidate)
            _append_force(communicative, candidate, 0.92, indices)


def _desire_knowledge_question(
    words: list[tuple[int, Token]],
    schemas: "_SchemaIndex",
) -> ConstructionCandidate | None:
    for offset, (_, token) in enumerate(words):
        if _lemma(token) not in {"do", "does", "did", "dont"}:
            continue
        if len(words) <= offset + 4:
            continue
        holder = words[offset + 1]
        want = words[offset + 2]
        cursor = offset + 3
        if _lemma(want[1]) != "want":
            continue
        if cursor < len(words) and _lemma(words[cursor][1]) == "to":
            cursor += 1
        if cursor >= len(words) or _lemma(words[cursor][1]) != "know":
            continue
        content_index = next(
            (
                item_index for item_index in range(cursor + 1, len(words))
                if _lemma(words[item_index][1]) not in _DET
                and _lemma(words[item_index][1]) not in {"my", "your", "his", "her", "our", "their"}
            ),
            None,
        )
        if content_index is None:
            continue
        schema = schemas.first(
            "[aux:do] [holder] [lemma:want] [lemma:know] [content]",
            "content_lexicalized_as_information",
        )
        return _candidate_from_schema(
            schema,
            {"holder": holder[0], "content": words[content_index][0]},
            0.86,
            (words[offset][0], want[0], words[cursor][0]),
        )
    return None


def _complement(
    words: list[tuple[int, Token]],
    constructions: list[ConstructionCandidate],
    schemas: "_SchemaIndex",
) -> None:
    for position, (index, token) in enumerate(words):
        lemma = _lemma(token)
        if position + 1 >= len(words):
            continue
        next_lemma = _lemma(words[position + 1][1])
        if next_lemma not in _WH | {"that", "if", "whether"}:
            continue
        schema = schemas.first(
            "[predicate] [embedded_clause]",
            f"predicate_lemma:{lemma}",
        )
        captures = {"content": words[position + 1][0]}
        if position > 0:
            captures["subject"] = words[position - 1][0]
        candidate = _candidate_from_schema(schema, captures, 0.84, (index,))
        if candidate is not None:
            constructions.append(candidate)
        embedded = _embedded_definition_question(words[position + 1:], schemas)
        if embedded is not None:
            constructions.append(embedded)


def _embedded_definition_question(
    embedded_words: list[tuple[int, Token]],
    schemas: "_SchemaIndex",
) -> ConstructionCandidate | None:
    if not embedded_words or _lemma(embedded_words[0][1]) != "what":
        return None
    copula_position = next(
        (
            position for position, (_, token) in enumerate(embedded_words[1:], start=1)
            if _lemma(token) in _COPULA
        ),
        None,
    )
    if copula_position is None:
        return None
    cursor = 1
    if cursor < copula_position and _lemma(embedded_words[cursor][1]) in _DET:
        cursor += 1
    if cursor >= copula_position:
        return None
    schema = schemas.first("[wh:what] [copula] [kind]")
    indices = (embedded_words[0][0], embedded_words[copula_position][0])
    return _candidate_from_schema(
        schema,
        {"kind": embedded_words[cursor][0]},
        0.88,
        indices,
    )


class _SchemaIndex:
    def __init__(self, schemas: tuple[Any, ...]) -> None:
        self._schemas = schemas

    def first(self, pattern: str, constraint: str = "") -> Any | None:
        for schema in self._schemas:
            if getattr(schema, "pattern", "") != pattern:
                continue
            constraints = tuple(getattr(schema, "constraints", ()) or ())
            if constraint and constraint not in constraints:
                continue
            return schema
        return None


def _candidate_from_schema(
    schema: Any | None,
    captures: dict[str, int],
    confidence: float,
    source_indices: tuple[int, ...],
) -> ConstructionCandidate | None:
    if schema is None:
        return None
    role_mappings = {}
    for role_key, capture_key in getattr(schema, "role_mappings", {}).items():
        if capture_key in captures:
            role_mappings[role_key] = captures[capture_key]
    return ConstructionCandidate(
        construction_key=getattr(schema, "semantic_key", ""),
        pattern=getattr(schema, "pattern", ""),
        predicate_schema_ref=getattr(schema, "predicate_schema_ref", ""),
        role_mappings=role_mappings,
        open_role_refs=tuple(getattr(schema, "open_role_refs", ()) or ()),
        communicative_force=getattr(schema, "communicative_force", ""),
        confidence=confidence,
        source_token_indices=source_indices,
    )


def _append_force(
    communicative: list[CommunicativeCandidate],
    candidate: ConstructionCandidate,
    confidence: float,
    source_indices: tuple[int, ...],
) -> None:
    force = getattr(candidate, "communicative_force", "")
    if force:
        communicative.append(
            CommunicativeCandidate(
                force,
                confidence,
                evidence_kind="construction",
                source_token_indices=source_indices,
            )
        )


def _lemma(token: Token) -> str:
    if token.normalized_form in _GRAMMATICAL_SENSES:
        return token.normalized_form
    if token.lemma_candidates:
        return token.lemma_candidates[0]
    return token.normalized_form
