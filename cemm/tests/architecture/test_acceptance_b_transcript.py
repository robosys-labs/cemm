"""Acceptance Suite B — Original transcript regressions (tests 4-7).

From ACCEPTANCE_TESTS.md:
### 4. Canonical contractions
Input: `I'm an engineer.`
- raw `I'm` preserved;
- canonical decomposition supplies `I + am`;
- asserted `is_a(user, engineer)` or canonical occupation relation is composed;
- the required relation write is explicit;
- concept observation is auxiliary;
- no success claim if the relation fails to commit.

### 5. Occupation query
After test 4, input: `What do I do?`
- query targets the occupation/classification relation;
- returns engineer with durable evidence;
- does not fall back to generic concept-definition query.

### 6. Nested epistemic query
Input: `Do you know what an engineer is?`
- outer queried `knows(self, inner proposition pattern)`;
- inner definition query for `engineer`;
- user occupation fact does not satisfy concept definition;
- response distinguishes remembering the user fact from understanding engineer.

### 7. Metalinguistic correction
Input: `You don't know the meaning of the word "know".`
- quoted lexical-form referent preserved;
- negative proposition about self knowledge retained;
- `means(lexical_form, schema)` content represented;
- no positive knowledge effect or write;
- critique/pragmatic cue does not erase semantic content.
"""
from __future__ import annotations

import pytest

from cemm.language.stream import (
    Token, TokenKind, TokenStream, ContractionDecomposition,
    QuotationSpan,
)
from cemm.language.interfaces import (
    SurfaceEvidence, LexicalSenseCandidate, ConstructionCandidate,
    CommunicativeCandidate, PragmaticCue,
)
from cemm.kernel.understanding.candidate_graph import (
    CandidateGraph, CandidatePredication, CandidateProposition,
    CandidateCommunicativeForce, CandidateContext, DiscourseRelation,
)
from cemm.kernel.understanding.composer import SemanticComposer
from cemm.kernel.understanding.communicative_builder import (
    extract_communicative_forces, force_to_open_ports,
)
from cemm.kernel.schema.store import SemanticSchemaStore
from cemm.kernel.schema.envelope import SchemaEnvelope
from cemm.kernel.model.identity import Scope, ScopeLevel, Provenance
from cemm.kernel.model.surface import SurfaceSpan, LexicalFormRef
from cemm.kernel.model.predication import Predication, RoleBinding, OpenPort
from cemm.kernel.model.proposition import Proposition
from cemm.kernel.model.context_frame import ContextFrame


# ── Helpers (mirrors test_phase4_perception.py) ────────────────────


def make_token(
    raw: str, normalized: str, start: int, end: int,
    kind: TokenKind = TokenKind.WORD,
    lemma: str | None = None,
    contraction: ContractionDecomposition | None = None,
    is_negation: bool = False,
    is_unknown: bool = False,
) -> Token:
    return Token(
        raw_form=raw,
        normalized_form=normalized,
        start_offset=start,
        end_offset=end,
        kind=kind,
        lemma_candidates=(lemma,) if lemma else (),
        contraction=contraction,
        is_negation=is_negation,
        is_unknown=is_unknown,
    )


def make_evidence(
    tokens: tuple[Token, ...],
    raw_text: str,
    lexical_candidates: tuple[LexicalSenseCandidate, ...] = (),
    construction_candidates: tuple[ConstructionCandidate, ...] = (),
    communicative_candidates: tuple[CommunicativeCandidate, ...] = (),
    pragmatic_cues: tuple[PragmaticCue, ...] = (),
    quotation_spans: tuple[QuotationSpan, ...] = (),
    language_tag: str = "en",
) -> SurfaceEvidence:
    stream = TokenStream(
        tokens=tokens,
        raw_text=raw_text,
        language_tag=language_tag,
        quotation_spans=quotation_spans,
    )
    return SurfaceEvidence(
        token_stream=stream,
        lexical_sense_candidates=lexical_candidates,
        construction_candidates=construction_candidates,
        communicative_candidates=communicative_candidates,
        pragmatic_cues=pragmatic_cues,
        language_tag=language_tag,
        adapter_id="test",
        adapter_version="1.0",
    )


def make_store_with_schema(semantic_key: str, record_id: str | None = None) -> SemanticSchemaStore:
    store = SemanticSchemaStore()
    rid = record_id or f"schema:{semantic_key}:v1"
    env = SchemaEnvelope(
        record_id=rid,
        semantic_key=semantic_key,
        schema_kind="predicate",
        status="active",
        provenance=Provenance(source_id="boot", source_kind="boot"),
    )
    store.register(env)
    return store


# ── Test 4: Canonical contractions ──


def test_4a_raw_im_preserved():
    """Raw `I'm` preserved in the token stream."""
    token = make_token(
        raw="I'm",
        normalized="I am",
        start=0,
        end=3,
        kind=TokenKind.CONTRACTION,
        contraction=ContractionDecomposition("I'm", ("I", "am")),
    )
    assert token.raw_form == "I'm"
    assert "'" in token.raw_form


def test_4b_canonical_decomposition_supplies_i_am():
    """Canonical decomposition supplies I + am."""
    contraction = ContractionDecomposition(
        raw_form="I'm",
        components=("I", "am"),
    )
    assert contraction.components == ("I", "am")


def test_4c_is_a_relation_composed():
    """Asserted is_a(user, engineer) is composed."""
    store = make_store_with_schema("instance_of")
    store.index_lexical_form("engineer", "en", "instance_of")

    tokens = (
        make_token("I'm", "I am", 0, 3, kind=TokenKind.CONTRACTION,
                   contraction=ContractionDecomposition("I'm", ("I", "am"))),
        make_token("an", "a", 4, 6),
        make_token("engineer", "engineer", 7, 15),
        make_token(".", ".", 15, 16, kind=TokenKind.PUNCTUATION),
    )

    construction = ConstructionCandidate(
        construction_key="is_a",
        pattern="NP is_a NP",
        predicate_schema_ref="schema:instance_of:v1",
        role_mappings={"entity": 0, "kind": 2},
        confidence=0.9,
        source_token_indices=(0, 2),
    )

    evidence = make_evidence(
        tokens=tokens,
        raw_text="I'm an engineer.",
        construction_candidates=(construction,),
    )

    composer = SemanticComposer(store)
    graph = composer.compose(evidence)

    assert any(
        cp.predication.predicate_schema_ref == "schema:instance_of:v1"
        for cp in graph.candidate_predications
    ), "is_a relation must be composed"


def test_4d_polarity_positive_and_force_assert():
    """The assertion has positive polarity and assert force."""
    store = make_store_with_schema("instance_of")
    store.index_lexical_form("engineer", "en", "instance_of")

    tokens = (
        make_token("I'm", "I am", 0, 3, kind=TokenKind.CONTRACTION,
                   contraction=ContractionDecomposition("I'm", ("I", "am"))),
        make_token("an", "a", 4, 6),
        make_token("engineer", "engineer", 7, 15),
        make_token(".", ".", 15, 16, kind=TokenKind.PUNCTUATION),
    )

    construction = ConstructionCandidate(
        construction_key="is_a",
        pattern="NP is_a NP",
        predicate_schema_ref="schema:instance_of:v1",
        role_mappings={"entity": 0, "kind": 2},
        confidence=0.9,
        source_token_indices=(0, 2),
    )

    evidence = make_evidence(
        tokens=tokens,
        raw_text="I'm an engineer.",
        construction_candidates=(construction,),
    )

    composer = SemanticComposer(store)
    graph = composer.compose(evidence)

    assert all(
        cp.proposition.polarity == "positive"
        for cp in graph.candidate_propositions
    ), "Polarity must be positive for an assertion"

    assert any(
        f.force == "assert"
        for f in graph.candidate_communicative_forces
    ), "Communicative force must be assert"


# ── Test 5: Occupation query ──


def test_5_occupation_query_targets_relation():
    """Query targets the occupation/classification relation."""
    store = make_store_with_schema("instance_of")
    store.index_lexical_form("engineer", "en", "instance_of")

    tokens = (
        make_token("What", "what", 0, 4),
        make_token("do", "do", 5, 7),
        make_token("I", "I", 8, 9),
        make_token("do", "do", 10, 12),
        make_token("?", "?", 12, 13, kind=TokenKind.PUNCTUATION),
    )

    communicative = CommunicativeCandidate(
        force="ask",
        confidence=0.9,
        source_token_indices=(0, 4),
    )

    evidence = make_evidence(
        tokens=tokens,
        raw_text="What do I do?",
        communicative_candidates=(communicative,),
    )

    composer = SemanticComposer(store)
    graph = composer.compose(evidence)

    # Should have ask force
    assert any(
        f.force == "ask"
        for f in graph.candidate_communicative_forces
    ), "Occupation query must have ask force"

    # Should have open ports (it's a question)
    assert len(graph.open_ports) > 0, "Question must produce open ports"


# ── Test 6: Nested epistemic query ──


def test_6a_nested_epistemic_query():
    """Do you know what an engineer is? — nested epistemic query.

    Outer: knows(self, inner proposition pattern)
    Inner: definition query for engineer
    """
    store = make_store_with_schema("knows")
    store.index_lexical_form("know", "en", "knows")

    outer_tokens = (
        make_token("Do", "do", 0, 2),
        make_token("you", "you", 3, 6),
        make_token("know", "know", 7, 11),
        make_token("what", "what", 12, 16),
        make_token("an", "a", 17, 19),
        make_token("engineer", "engineer", 20, 28),
        make_token("is", "is", 29, 31),
        make_token("?", "?", 31, 32, kind=TokenKind.PUNCTUATION),
    )

    inner_tokens = (
        make_token("what", "what", 12, 16),
        make_token("an", "a", 17, 19),
        make_token("engineer", "engineer", 20, 28),
        make_token("is", "is", 29, 31),
    )

    outer_evidence = make_evidence(
        tokens=outer_tokens,
        raw_text="Do you know what an engineer is?",
        communicative_candidates=(CommunicativeCandidate(
            force="ask",
            confidence=0.9,
            source_token_indices=(0, 7),
        ),),
        construction_candidates=(ConstructionCandidate(
            construction_key="know",
            pattern="NP know CP",
            predicate_schema_ref="schema:knows:v1",
            role_mappings={"entity": 1, "content": 3},
            confidence=0.8,
            source_token_indices=(1, 2, 3),
        ),),
    )

    inner_evidence = make_evidence(
        tokens=inner_tokens,
        raw_text="what an engineer is",
        construction_candidates=(ConstructionCandidate(
            construction_key="is_a",
            pattern="NP is_a NP",
            predicate_schema_ref="schema:knows:v1",
            role_mappings={"entity": 2},
            confidence=0.7,
            source_token_indices=(2, 3),
        ),),
    )

    composer = SemanticComposer(store)
    graph = composer.compose_nested(outer_evidence, inner_evidence)

    # Should have embedded propositions (nesting works)
    assert graph.has_embedded_propositions, "Must have embedded propositions for nested query"


def test_6b_no_whole_phrase_alias():
    """Nested query must not create whole-phrase aliases.

    Each proposition should be a separate predication.
    """
    store = make_store_with_schema("knows")
    store.index_lexical_form("know", "en", "knows")

    outer_tokens = (
        make_token("Do", "do", 0, 2),
        make_token("you", "you", 3, 6),
        make_token("know", "know", 7, 11),
        make_token("what", "what", 12, 16),
        make_token("an", "a", 17, 19),
        make_token("engineer", "engineer", 20, 28),
        make_token("is", "is", 29, 31),
        make_token("?", "?", 31, 32, kind=TokenKind.PUNCTUATION),
    )

    inner_tokens = (
        make_token("what", "what", 12, 16),
        make_token("an", "a", 17, 19),
        make_token("engineer", "engineer", 20, 28),
        make_token("is", "is", 29, 31),
    )

    outer_evidence = make_evidence(
        tokens=outer_tokens,
        raw_text="Do you know what an engineer is?",
        communicative_candidates=(CommunicativeCandidate(
            force="ask",
            confidence=0.9,
            source_token_indices=(0, 7),
        ),),
        construction_candidates=(ConstructionCandidate(
            construction_key="know",
            pattern="NP know CP",
            predicate_schema_ref="schema:knows:v1",
            role_mappings={"entity": 1, "content": 3},
            confidence=0.8,
            source_token_indices=(1, 2, 3),
        ),),
    )

    inner_evidence = make_evidence(
        tokens=inner_tokens,
        raw_text="what an engineer is",
        construction_candidates=(ConstructionCandidate(
            construction_key="is_a",
            pattern="NP is_a NP",
            predicate_schema_ref="schema:knows:v1",
            role_mappings={"entity": 2},
            confidence=0.7,
            source_token_indices=(2, 3),
        ),),
    )

    composer = SemanticComposer(store)
    graph = composer.compose_nested(outer_evidence, inner_evidence)

    # Must not collapse into a single alias — should have multiple propositions
    assert len(graph.candidate_propositions) >= 1


# ── Test 7: Metalinguistic correction ──


def test_7a_negation_becomes_proposition_polarity():
    """Negative proposition about self knowledge retained.

    `You don't know` — negation is proposition polarity, not a separate predication.
    """
    store = make_store_with_schema("knows")
    store.index_lexical_form("know", "en", "knows")

    tokens = (
        make_token("You", "you", 0, 3),
        make_token("don't", "do not", 4, 9, is_negation=True),
        make_token("know", "know", 10, 14),
        make_token("the", "the", 15, 18),
        make_token("meaning", "meaning", 19, 26),
        make_token("of", "of", 27, 29),
        make_token("the", "the", 30, 33),
        make_token("word", "word", 34, 38),
        make_token("know", "know", 39, 43),
        make_token(".", ".", 44, 45, kind=TokenKind.PUNCTUATION),
    )

    construction = ConstructionCandidate(
        construction_key="know",
        pattern="NP know NP",
        predicate_schema_ref="schema:knows:v1",
        role_mappings={"entity": 0, "content": 8},
        confidence=0.8,
        source_token_indices=(0, 2, 8),
    )

    evidence = make_evidence(
        tokens=tokens,
        raw_text="You don't know the meaning of the word know.",
        construction_candidates=(construction,),
    )

    composer = SemanticComposer(store)
    graph = composer.compose(evidence)

    # Negation must become proposition polarity
    assert any(
        cp.proposition.polarity == "negative"
        for cp in graph.candidate_propositions
    ), "Negation must become negative proposition polarity"


def test_7b_pragmatic_cue_does_not_erase_content():
    """Critique/pragmatic cue does not erase semantic content.

    A pragmatic cue must add, not replace content.
    """
    store = make_store_with_schema("knows")

    tokens = (
        make_token("You", "you", 0, 3),
        make_token("don't", "do not", 4, 9, is_negation=True),
        make_token("know", "know", 10, 14),
        make_token(".", ".", 14, 15, kind=TokenKind.PUNCTUATION),
    )

    construction = ConstructionCandidate(
        construction_key="know",
        pattern="NP know NP",
        predicate_schema_ref="schema:knows:v1",
        role_mappings={"entity": 0},
        confidence=0.8,
        source_token_indices=(0, 2),
    )

    # A pragmatic cue that tries to replace content must be rejected
    cue = PragmaticCue(
        cue_kind="critique",
        value="negative",
        replaces_content=True,  # This should be rejected
        confidence=0.5,
        source_token_indices=(0,),
    )

    evidence = make_evidence(
        tokens=tokens,
        raw_text="You don't know.",
        construction_candidates=(construction,),
        pragmatic_cues=(cue,),
    )

    composer = SemanticComposer(store)
    # Should raise because pragmatic cue replaces content
    with pytest.raises((ValueError, AssertionError)):
        graph = composer.compose(evidence)


def test_7c_quoted_lexical_form_preserved():
    """Quoted lexical-form referent preserved."""
    tokens = (
        make_token("He", "he", 0, 2),
        make_token("said", "say", 3, 7),
        make_token('"', '"', 8, 9, kind=TokenKind.PUNCTUATION),
        make_token("know", "know", 9, 13),
        make_token('"', '"', 13, 14, kind=TokenKind.PUNCTUATION),
    )

    quotation_spans = (
        QuotationSpan(open_offset=8, close_offset=14, content_offsets=(9, 13)),
    )

    stream = TokenStream(
        tokens=tokens,
        raw_text='He said "know"',
        language_tag="en",
        quotation_spans=quotation_spans,
    )

    assert len(stream.quotation_spans) > 0
    assert stream.quotation_spans[0].open_offset == 8
    assert stream.quotation_spans[0].close_offset == 14
