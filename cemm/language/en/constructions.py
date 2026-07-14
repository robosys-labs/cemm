"""English construction detection — maps surface patterns to candidate predications.

Detects:
- Copular constructions ("I'm an engineer" → is_a(user, engineer))
- Wh-questions ("What do I do?" → ask with open port)
- Complement clauses ("Do you know what an engineer is?" → knows(self, embedded))
- Pronoun/deictic candidates
- Negation scope

Per UNDERSTANDING_PIPELINE.md §3:
- Constructions map surface patterns to predications — as candidate evidence.
- Unknown content is never converted into a generic entity or durable fact.
"""
from __future__ import annotations

from typing import Any

from ..stream import Token, TokenStream, TokenKind
from ..interfaces import (
    LexicalSenseCandidate,
    ConstructionCandidate,
    CommunicativeCandidate,
    PragmaticCue,
)
from ...kernel.model.surface import SurfaceSpan, LexicalFormRef


# ── Construction detection ──

def detect_constructions(
    stream: TokenStream,
) -> tuple[
    tuple[LexicalSenseCandidate, ...],
    tuple[ConstructionCandidate, ...],
    tuple[CommunicativeCandidate, ...],
    tuple[PragmaticCue, ...],
    tuple[SurfaceSpan, ...],
]:
    """Detect constructions from a token stream.

    Returns lexical sense candidates, construction candidates,
    communicative candidates, pragmatic cues, and surface spans.
    """
    lexical: list[LexicalSenseCandidate] = []
    constructions: list[ConstructionCandidate] = []
    communicative: list[CommunicativeCandidate] = []
    cues: list[PragmaticCue] = []
    spans: list[SurfaceSpan] = []

    word_tokens = [
        (i, t) for i, t in enumerate(stream.tokens)
        if t.kind in (TokenKind.WORD, TokenKind.CONTRACTION, TokenKind.NEGATION)
    ]

    if not word_tokens:
        return (), (), (), (), ()

    # ── Lexical sense candidates ──
    for idx, (i, token) in enumerate(word_tokens):
        lower = token.normalized_form
        lemma = token.lemma_candidates[0] if token.lemma_candidates else lower

        # Determine semantic key
        if lemma in ("i", "my", "me", "mine", "myself"):
            semantic_key = "pronoun:first_person"
        elif lemma in ("you", "your", "yours", "yourself"):
            semantic_key = "pronoun:second_person"
        elif lemma in ("he", "him", "his", "himself"):
            semantic_key = "pronoun:third_person_masc"
        elif lemma in ("she", "her", "hers", "herself"):
            semantic_key = "pronoun:third_person_fem"
        elif lemma in ("it", "its", "itself"):
            semantic_key = "pronoun:third_person_neut"
        elif lemma in ("we", "us", "our", "ours", "ourselves"):
            semantic_key = "pronoun:first_person_plural"
        elif lemma in ("they", "them", "their", "theirs", "themselves"):
            semantic_key = "pronoun:third_person_plural"
        elif lemma in ("what", "who", "whom", "whose", "which", "where", "when", "why", "how"):
            semantic_key = f"wh:{lemma}"
        elif lemma in ("is", "are", "am", "was", "were", "be", "been", "being"):
            semantic_key = "copula:be"
        elif lemma in ("know", "knows", "knew"):
            semantic_key = "verb:know"
        elif lemma in ("mean", "means", "meant"):
            semantic_key = "verb:mean"
        elif lemma in ("do", "does", "did"):
            semantic_key = "aux:do"
        elif lemma in ("a", "an", "the"):
            semantic_key = "det"
        elif lemma == "not":
            semantic_key = "negation"
        elif lemma == "engineer":
            semantic_key = "noun:engineer"
        else:
            # Unknown — mark as opaque
            semantic_key = f"opaque:{lemma}"

        form_ref = LexicalFormRef(
            surface=token.raw_form,
            language_tag="en",
        )
        lexical.append(LexicalSenseCandidate(
            lexical_form_ref=form_ref,
            semantic_key=semantic_key,
            sense_rank=1.0 if not token.is_unknown else 0.0,
            evidence_kind="lexical",
            confidence=0.0 if token.is_unknown else 0.8,
            source_token_indices=(i,),
        ))

        # Surface span for this token
        spans.append(SurfaceSpan(
            signal_ref="",
            start=token.start_offset,
            end=token.end_offset,
            raw_text=token.raw_form,
            token_start=i,
            token_end=i + 1,
        ))

    # ── Construction candidates ──

    # Detect copular: [subj] [copula] [det] [noun]
    _detect_copular(word_tokens, stream, constructions)

    # Detect wh-questions: [wh] [aux] [subj] [verb]
    _detect_wh_question(word_tokens, stream, constructions, communicative)

    # Detect yes/no question: [aux] [subj] [verb] ...
    _detect_yn_question(word_tokens, stream, constructions, communicative)

    # Detect complement clause: [verb] [wh/noun] ... [copula/verb]
    _detect_complement(word_tokens, stream, constructions)

    # ── Communicative force ──
    if not communicative:
        # Default: assert for declarative, ask for interrogative
        first_word = word_tokens[0][1].normalized_form if word_tokens else ""
        if first_word in ("what", "who", "where", "when", "why", "how", "which"):
            communicative.append(CommunicativeCandidate(
                force="ask",
                confidence=0.9,
                source_token_indices=(word_tokens[0][0],),
            ))
        elif first_word in ("do", "does", "did", "is", "are", "was", "were", "can", "could", "will", "would", "should", "have", "has"):
            communicative.append(CommunicativeCandidate(
                force="ask",
                confidence=0.7,
                source_token_indices=(word_tokens[0][0],),
            ))
        else:
            communicative.append(CommunicativeCandidate(
                force="assert",
                confidence=0.6,
                source_token_indices=(word_tokens[0][0],),
            ))

    # ── Negation scope ──
    for i, token in enumerate(stream.tokens):
        if token.is_negation:
            cues.append(PragmaticCue(
                cue_kind="negation_scope",
                value="negative",
                confidence=1.0,
                source_token_indices=(i,),
            ))

    return (
        tuple(lexical),
        tuple(constructions),
        tuple(communicative),
        tuple(cues),
        tuple(spans),
    )


def _get_lemma(token: Token) -> str:
    return token.lemma_candidates[0] if token.lemma_candidates else token.normalized_form


def _detect_copular(
    word_tokens: list[tuple[int, Token]],
    stream: TokenStream,
    constructions: list[ConstructionCandidate],
) -> None:
    """Detect copular constructions: [subj] [copula] [det] [noun].

    Handles both separated copula ("I am an engineer") and contracted
    forms ("I'm an engineer") where the copula is embedded in the
    contraction.
    """
    for idx, (i, token) in enumerate(word_tokens):
        lemma = _get_lemma(token)
        # Check if this token IS a copula
        is_copular = lemma in ("is", "are", "am", "was", "were")
        # Check if this token is a contraction containing a copula
        copular_in_contraction = False
        if token.contraction and not is_copular:
            components = token.contraction.components
            for comp in components:
                if comp.lower() in ("is", "are", "am", "was", "were"):
                    copular_in_contraction = True
                    break

        if not is_copular and not copular_in_contraction:
            continue

        # For contractions like "I'm", the subject is embedded in the
        # same token. For separate copula, look before.
        subj_idx = None
        if copular_in_contraction:
            # Subject is embedded in the contraction — use this token
            subj_idx = i
        elif idx > 0:
            prev_token = word_tokens[idx - 1][1]
            prev_lemma = _get_lemma(prev_token)
            if prev_lemma in ("i", "you", "he", "she", "it", "we", "they") or \
               prev_token.morphological_features and any(
                   f.feature == "case" and f.value == "proper" for f in prev_token.morphological_features
               ):
                subj_idx = word_tokens[idx - 1][0]

        # Look for predicate after copula
        pred_idx = None
        pred_role = "complement"
        search_start = idx + 1
        if copular_in_contraction:
            search_start = idx + 1

        if search_start < len(word_tokens):
            next_token = word_tokens[search_start][1]
            next_lemma = _get_lemma(next_token)
            if next_lemma in ("a", "an", "the"):
                # Skip determiner, look for noun
                if search_start + 1 < len(word_tokens):
                    noun_token = word_tokens[search_start + 1][1]
                    noun_lemma = _get_lemma(noun_token)
                    pred_idx = word_tokens[search_start + 1][0]
                    pred_role = "category"
            elif next_lemma not in ("not", "n't"):
                pred_idx = word_tokens[search_start][0]
                pred_role = "complement"

        if subj_idx is not None and pred_idx is not None:
            role_map = {"subject": subj_idx, pred_role: pred_idx}

            constructions.append(ConstructionCandidate(
                construction_key="copular",
                pattern="[subj] [copula] [complement]",
                predicate_schema_ref="pred:is_a" if pred_role == "category" else "pred:copular",
                role_mappings=role_map,
                confidence=0.85,
                source_token_indices=(i,),
            ))


def _detect_wh_question(
    word_tokens: list[tuple[int, Token]],
    stream: TokenStream,
    constructions: list[ConstructionCandidate],
    communicative: list[CommunicativeCandidate],
) -> None:
    """Detect wh-questions: [wh] [aux] [subj] [verb]."""
    if not word_tokens:
        return
    first_lemma = _get_lemma(word_tokens[0][1])
    wh_words = {"what", "who", "whom", "whose", "which", "where", "when", "why", "how"}

    if first_lemma not in wh_words:
        return

    wh_idx = word_tokens[0][0]

    # Find aux after wh
    aux_idx = None
    subj_idx = None
    verb_idx = None

    for idx in range(1, len(word_tokens)):
        lemma = _get_lemma(word_tokens[idx][1])
        if aux_idx is None and lemma in ("do", "does", "did", "can", "could", "will", "would", "should", "have", "has", "is", "are", "was", "were"):
            aux_idx = word_tokens[idx][0]
        elif aux_idx is not None and subj_idx is None:
            subj_idx = word_tokens[idx][0]
        elif subj_idx is not None and verb_idx is None:
            verb_idx = word_tokens[idx][0]
            break

    role_map = {"wh": wh_idx}
    if aux_idx is not None:
        role_map["aux"] = aux_idx
    if subj_idx is not None:
        role_map["subject"] = subj_idx
    if verb_idx is not None:
        role_map["verb"] = verb_idx

    constructions.append(ConstructionCandidate(
        construction_key="wh_question",
        pattern="[wh] [aux] [subj] [verb]",
        predicate_schema_ref="pred:wh_question",
        role_mappings=role_map,
        confidence=0.8,
        source_token_indices=(wh_idx,),
    ))

    communicative.append(CommunicativeCandidate(
        force="ask",
        confidence=0.95,
        source_token_indices=(wh_idx,),
    ))


def _detect_yn_question(
    word_tokens: list[tuple[int, Token]],
    stream: TokenStream,
    constructions: list[ConstructionCandidate],
    communicative: list[CommunicativeCandidate],
) -> None:
    """Detect yes/no questions: [aux] [subj] [verb] ..."""
    if not word_tokens:
        return
    first_lemma = _get_lemma(word_tokens[0][1])
    aux_words = {"do", "does", "did", "can", "could", "will", "would", "should",
                 "have", "has", "had", "is", "are", "was", "were", "might", "must"}

    if first_lemma not in aux_words:
        return

    # Check if already detected as wh-question
    if any(c.construction_key == "wh_question" for c in constructions):
        return

    aux_idx = word_tokens[0][0]

    subj_idx = None
    verb_idx = None
    for idx in range(1, len(word_tokens)):
        lemma = _get_lemma(word_tokens[idx][1])
        if subj_idx is None:
            subj_idx = word_tokens[idx][0]
        elif verb_idx is None:
            verb_idx = word_tokens[idx][0]
            break

    role_map = {"aux": aux_idx}
    if subj_idx is not None:
        role_map["subject"] = subj_idx
    if verb_idx is not None:
        role_map["verb"] = verb_idx

    constructions.append(ConstructionCandidate(
        construction_key="yn_question",
        pattern="[aux] [subj] [verb]",
        predicate_schema_ref="pred:yn_question",
        role_mappings=role_map,
        confidence=0.75,
        source_token_indices=(aux_idx,),
    ))

    communicative.append(CommunicativeCandidate(
        force="ask",
        confidence=0.85,
        source_token_indices=(aux_idx,),
    ))


def _detect_complement(
    word_tokens: list[tuple[int, Token]],
    stream: TokenStream,
    constructions: list[ConstructionCandidate],
) -> None:
    """Detect complement clauses: [verb] [wh/noun] ... [copula/verb]."""
    complement_verbs = {"know", "knows", "knew", "think", "thinks", "believe", "believes", "mean", "means"}

    for idx, (i, token) in enumerate(word_tokens):
        lemma = _get_lemma(token)
        if lemma not in complement_verbs:
            continue

        # Look for embedded clause after the verb
        if idx + 1 >= len(word_tokens):
            continue

        next_lemma = _get_lemma(word_tokens[idx + 1][1])
        wh_words = {"what", "who", "whom", "whose", "which", "where", "when", "why", "how"}

        if next_lemma in wh_words or next_lemma in ("that", "if", "whether"):
            # Embedded wh-clause or that-clause
            embedded_start = word_tokens[idx + 1][0]
            role_map = {"subject": i, "embedded": embedded_start}

            # Find the embedded verb/copula
            for jdx in range(idx + 2, len(word_tokens)):
                emb_lemma = _get_lemma(word_tokens[jdx][1])
                if emb_lemma in ("is", "are", "am", "was", "were", "do", "does", "did"):
                    role_map["embedded_verb"] = word_tokens[jdx][0]
                    break

            constructions.append(ConstructionCandidate(
                construction_key="complement_clause",
                pattern="[verb] [wh/that] [embedded clause]",
                predicate_schema_ref=f"pred:{lemma}",
                role_mappings=role_map,
                confidence=0.8,
                source_token_indices=(i,),
            ))
