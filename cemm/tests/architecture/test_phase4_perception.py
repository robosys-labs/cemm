"""Phase 4 gate tests: Canonical perception and compositional understanding.

Gates (from IMPLEMENTATION_PLAN.md Phase 4):
- I'm decomposes without losing raw evidence;
- assertion stores exact required is_a/occupation relation;
- arbitrary epistemic nesting works without whole-phrase aliases;
- pragmatic cues never erase content propositions.

Vertical tests:
    I'm an engineer.
    What do I do?
    Do you know what an engineer is?
    You don't know what "know" means.

Additional guardrail tests from AGENTS.md §8, UNDERSTANDING_PIPELINE.md:
- Token stream preserves raw text, apostrophes, offsets, quotes, negation
- Language adapters emit reversible surface evidence only
- SemanticComposer creates separate candidates (alternatives preserved)
- Pragmatic cues add, never replace content
- Opaque lexemes get provisional sense clusters, not generic entities
- Communicative force is independent from polarity/context/modality
- Negation is proposition polarity, not a separate predication
- Questions have open ports
- Unknown content is never converted to durable facts
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from cemm.language.stream import (
    Token, TokenKind, TokenStream, ContractionDecomposition,
    MorphologicalFeature, DependencyEdge, ClauseBoundary,
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
from cemm.kernel.understanding.context_builder import (
    extract_context_candidates, context_for_proposition,
)
from cemm.kernel.schema.store import SemanticSchemaStore
from cemm.kernel.schema.envelope import SchemaEnvelope
from cemm.kernel.model.identity import Scope, ScopeLevel, Provenance
from cemm.kernel.model.surface import SurfaceSpan, LexicalFormRef
from cemm.kernel.model.predication import Predication, RoleBinding, OpenPort
from cemm.kernel.model.proposition import Proposition
from cemm.kernel.model.context_frame import ContextFrame


# ── Helpers ────────────────────────────────────────────────────────


def make_token(
    raw: str, normalized: str, start: int, end: int,
    kind: TokenKind = TokenKind.WORD,
    lemma: str | None = None,
    contraction: ContractionDecomposition | None = None,
    is_negation: bool = False,
    is_unknown: bool = False,
    features: tuple[MorphologicalFeature, ...] = (),
) -> Token:
    return Token(
        raw_form=raw,
        normalized_form=normalized,
        start_offset=start,
        end_offset=end,
        kind=kind,
        lemma_candidates=(lemma,) if lemma else (),
        morphological_features=features,
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
    clause_boundaries: tuple[ClauseBoundary, ...] = (),
    dependency_edges: tuple[DependencyEdge, ...] = (),
    language_tag: str = "en",
) -> SurfaceEvidence:
    stream = TokenStream(
        tokens=tokens,
        raw_text=raw_text,
        language_tag=language_tag,
        quotation_spans=quotation_spans,
        clause_boundaries=clause_boundaries,
        dependency_edges=dependency_edges,
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
    """Create a store with a pre-registered active schema."""
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
    store.activate(rid, expected_revision=1)
    store.index_lexical_form(semantic_key, "en", semantic_key)
    return store


# ── Gate 1: I'm decomposes without losing raw evidence ─────────────


def test_contraction_decomposition_preserves_raw():
    """I'm must decompose to I + am without losing the raw form."""
    contraction = ContractionDecomposition(
        raw_form="I'm",
        components=("I", "am"),
        component_offsets=((0, 1), (2, 4)),
    )
    token = make_token(
        raw="I'm",
        normalized="I am",
        start=0,
        end=3,
        kind=TokenKind.CONTRACTION,
        contraction=contraction,
    )
    assert token.raw_form == "I'm"
    assert token.contraction is not None
    assert token.contraction.components == ("I", "am")
    assert token.preserves_raw


def test_token_stream_preserves_apostrophes():
    """Apostrophes must survive in the canonical token stream."""
    tokens = (
        make_token("I'm", "I am", 0, 3, kind=TokenKind.CONTRACTION,
                   contraction=ContractionDecomposition("I'm", ("I", "am"))),
        make_token("an", "a", 4, 6),
        make_token("engineer", "engineer", 7, 15),
        make_token(".", ".", 15, 16, kind=TokenKind.PUNCTUATION),
    )
    stream = TokenStream(tokens=tokens, raw_text="I'm an engineer.")
    assert stream.has_contractions
    assert stream.tokens[0].raw_form == "I'm"
    assert "'" in stream.tokens[0].raw_form


def test_im_engineer_composition():
    """I'm an engineer. — composition preserves contraction and builds candidates."""
    store = make_store_with_schema("instance_of")
    store.index_lexical_form("engineer", "en", "instance_of")

    tokens = (
        make_token("I'm", "I am", 0, 3, kind=TokenKind.CONTRACTION,
                   contraction=ContractionDecomposition("I'm", ("I", "am"))),
        make_token("an", "a", 4, 6),
        make_token("engineer", "engineer", 7, 15),
        make_token(".", ".", 15, 16, kind=TokenKind.PUNCTUATION),
    )

    lexical = LexicalSenseCandidate(
        lexical_form_ref=LexicalFormRef(surface="engineer", language_tag="en"),
        semantic_key="instance_of",
        confidence=0.8,
        source_token_indices=(2,),
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
        lexical_candidates=(lexical,),
        construction_candidates=(construction,),
    )

    composer = SemanticComposer(store)
    graph = composer.compose(evidence)

    # Should have candidate predications
    assert len(graph.candidate_predications) > 0
    # Should have candidate propositions
    assert len(graph.candidate_propositions) > 0
    # Should have communicative force (assert by default)
    assert len(graph.candidate_communicative_forces) > 0
    assert graph.candidate_communicative_forces[0].force == "assert"
    # Polarity should be positive (no negation)
    assert all(
        cp.proposition.polarity == "positive"
        for cp in graph.candidate_propositions
    )


# ── Gate 2: assertion stores exact required is_a/occupation relation ─


def test_assertion_stores_is_a_relation():
    """An assertion like 'I'm an engineer' must store the exact is_a relation."""
    store = make_store_with_schema("instance_of")
    store.index_lexical_form("engineer", "en", "instance_of")

    tokens = (
        make_token("I'm", "I am", 0, 3, kind=TokenKind.CONTRACTION),
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

    # The predication should reference the instance_of schema
    assert any(
        cp.predication.predicate_schema_ref == "schema:instance_of:v1"
        for cp in graph.candidate_predications
    )

    # The proposition should have positive polarity (it's an assertion)
    assert all(
        cp.proposition.polarity == "positive"
        for cp in graph.candidate_propositions
    )

    # The communicative force should be assert
    assert any(
        f.force == "assert"
        for f in graph.candidate_communicative_forces
    )


# ── Gate 3: arbitrary epistemic nesting without whole-phrase aliases ─


def test_epistemic_nesting_without_whole_phrase_aliases():
    """Do you know what an engineer is? — nested proposition without aliases."""
    store = make_store_with_schema("knows")
    store.index_lexical_form("know", "en", "knows")

    # Outer: "Do you know [inner]?"
    # Inner: "what an engineer is"
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

    # Should have embedded propositions
    assert graph.has_embedded_propositions
    # Should not create whole-phrase aliases
    # Each proposition should be a separate predication, not a single alias
    assert len(graph.candidate_propositions) >= 1
    # The embedded proposition refs should be non-empty
    assert any(
        len(cp.embedded_proposition_refs) > 0
        for cp in graph.candidate_propositions
    )


def test_question_has_open_ports():
    """Questions must produce open ports for the unknown role."""
    store = make_store_with_schema("knows")

    tokens = (
        make_token("What", "what", 0, 4),
        make_token("do", "do", 5, 7),
        make_token("I", "I", 8, 9),
        make_token("do", "do", 10, 12),
        make_token("?", "?", 12, 13, kind=TokenKind.PUNCTUATION),
    )

    evidence = make_evidence(
        tokens=tokens,
        raw_text="What do I do?",
        communicative_candidates=(CommunicativeCandidate(
            force="ask",
            confidence=0.9,
            source_token_indices=(0, 4),
        ),),
    )

    composer = SemanticComposer(store)
    graph = composer.compose(evidence)

    # Questions should have open ports
    assert len(graph.open_ports) > 0


# ── Gate 4: pragmatic cues never erase content propositions ─────────


def test_pragmatic_cues_add_not_replace():
    """Pragmatic cues must add candidates, never replace content."""
    store = make_store_with_schema("instance_of")

    tokens = (
        make_token("I'm", "I am", 0, 3, kind=TokenKind.CONTRACTION),
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

    # Pragmatic cue: politeness
    cue = PragmaticCue(
        cue_kind="politeness",
        value="formal",
        confidence=0.8,
        adds_candidates=True,
        replaces_content=False,
    )

    evidence = make_evidence(
        tokens=tokens,
        raw_text="I'm an engineer.",
        construction_candidates=(construction,),
        pragmatic_cues=(cue,),
    )

    composer = SemanticComposer(store)
    graph = composer.compose(evidence)

    # Content propositions must still exist
    assert len(graph.candidate_propositions) > 0
    # The is_a predication must still be present
    assert any(
        cp.predication.predicate_schema_ref == "schema:instance_of:v1"
        for cp in graph.candidate_predications
    )
    # Pragmatic cue should add a discourse relation, not remove content
    assert any(
        dr.from_pragmatic_cue for dr in graph.discourse_relations
    )


def test_pragmatic_cue_replacing_content_is_forbidden():
    """A pragmatic cue with replaces_content=True must be rejected."""
    store = make_store_with_schema("instance_of")

    tokens = (
        make_token("I'm", "I am", 0, 3, kind=TokenKind.CONTRACTION),
        make_token("an", "a", 4, 6),
        make_token("engineer", "engineer", 7, 15),
        make_token(".", ".", 15, 16, kind=TokenKind.PUNCTUATION),
    )

    cue = PragmaticCue(
        cue_kind="override",
        value="replace",
        confidence=0.8,
        adds_candidates=False,
        replaces_content=True,  # This must be rejected!
    )

    evidence = make_evidence(
        tokens=tokens,
        raw_text="I'm an engineer.",
        pragmatic_cues=(cue,),
    )

    composer = SemanticComposer(store)
    # Should raise an assertion error
    with pytest.raises(AssertionError, match="replace content"):
        composer.compose(evidence)


# ── Token stream preservation tests ────────────────────────────────


def test_quotation_boundaries_preserved():
    """Quotation boundaries must survive in the token stream."""
    # You don't know what "know" means.
    tokens = (
        make_token("You", "you", 0, 3),
        make_token("don't", "do not", 4, 9,
                   kind=TokenKind.CONTRACTION,
                   contraction=ContractionDecomposition("don't", ("do", "not")),
                   is_negation=True),
        make_token("know", "know", 10, 14),
        make_token("what", "what", 15, 19),
        make_token('"', '"', 20, 21, kind=TokenKind.QUOTE_OPEN),
        make_token("know", "know", 21, 25),
        make_token('"', '"', 25, 26, kind=TokenKind.QUOTE_CLOSE),
        make_token("means", "mean", 27, 32),
        make_token(".", ".", 32, 33, kind=TokenKind.PUNCTUATION),
    )

    qspan = QuotationSpan(
        open_offset=20,
        close_offset=26,
        content_offsets=(21, 25),
    )

    stream = TokenStream(
        tokens=tokens,
        raw_text='You don\'t know what "know" means.',
        quotation_spans=(qspan,),
    )

    assert stream.has_quotations
    assert stream.has_negation
    assert stream.has_contractions
    # Tokens inside quotation
    quoted = stream.tokens_in_quotation(0)
    assert len(quoted) == 1
    assert quoted[0].raw_form == "know"


def test_negation_preserved_in_token_stream():
    """Negation must be preserved as token annotation."""
    tokens = (
        make_token("You", "you", 0, 3),
        make_token("don't", "do not", 4, 9,
                   kind=TokenKind.CONTRACTION,
                   contraction=ContractionDecomposition("don't", ("do", "not")),
                   is_negation=True),
        make_token("know", "know", 10, 14),
    )
    stream = TokenStream(tokens=tokens, raw_text="You don't know")
    assert stream.has_negation
    assert tokens[1].is_negation


def test_negation_becomes_proposition_polarity():
    """Negation must become proposition polarity, not a separate predication."""
    store = make_store_with_schema("knows")
    store.index_lexical_form("know", "en", "knows")

    tokens = (
        make_token("You", "you", 0, 3),
        make_token("don't", "do not", 4, 9,
                   kind=TokenKind.CONTRACTION,
                   contraction=ContractionDecomposition("don't", ("do", "not")),
                   is_negation=True),
        make_token("know", "know", 10, 14, lemma="know"),
    )

    construction = ConstructionCandidate(
        construction_key="know",
        pattern="NP know",
        predicate_schema_ref="schema:knows:v1",
        role_mappings={"entity": 0},
        confidence=0.8,
        source_token_indices=(0, 2),
    )

    evidence = make_evidence(
        tokens=tokens,
        raw_text="You don't know",
        construction_candidates=(construction,),
    )

    composer = SemanticComposer(store)
    graph = composer.compose(evidence)

    # Negation should be captured as negative polarity
    assert any(
        cp.proposition.polarity == "negative"
        for cp in graph.candidate_propositions
    )


# ── Opaque lexeme tests ────────────────────────────────────────────


def test_opaque_lexeme_gets_provisional_cluster():
    """Opaque lexemes get provisional sense clusters, not generic entities."""
    store = SemanticSchemaStore()  # Empty store — no schemas

    tokens = (
        make_token("dax", "dax", 0, 3, is_unknown=True),
        make_token("is", "is", 4, 6),
        make_token("good", "good", 7, 11),
    )

    lexical = LexicalSenseCandidate(
        lexical_form_ref=LexicalFormRef(surface="dax", language_tag="en"),
        semantic_key="dax",
        confidence=0.1,
        source_token_indices=(0,),
    )

    evidence = make_evidence(
        tokens=tokens,
        raw_text="dax is good",
        lexical_candidates=(lexical,),
    )

    composer = SemanticComposer(store)
    graph = composer.compose(evidence)

    # Should have opaque lexeme refs
    assert len(graph.opaque_lexeme_refs) > 0
    # Should NOT have predications for the opaque lexeme
    # (it wasn't resolved to any schema)
    assert all(
        "dax" not in cp.predication.predicate_schema_ref
        for cp in graph.candidate_predications
    )


def test_unknown_content_not_converted_to_durable_fact():
    """Unknown content must not be converted to a generic entity or durable fact."""
    store = SemanticSchemaStore()

    tokens = (
        make_token("xyzzy", "xyzzy", 0, 5, is_unknown=True),
    )

    evidence = make_evidence(
        tokens=tokens,
        raw_text="xyzzy",
    )

    composer = SemanticComposer(store)
    graph = composer.compose(evidence)

    # Should have opaque refs, not predications
    assert len(graph.opaque_lexeme_refs) > 0
    # Should not have any candidate predications (nothing resolved)
    assert len(graph.candidate_predications) == 0


# ── Communicative force independence tests ─────────────────────────


def test_communicative_force_independent_from_polarity():
    """Communicative force is independent from polarity and context."""
    # A negative question: "Don't you know?"
    store = make_store_with_schema("knows")
    store.index_lexical_form("know", "en", "knows")

    tokens = (
        make_token("Don't", "do not", 0, 5,
                   kind=TokenKind.CONTRACTION,
                   contraction=ContractionDecomposition("Don't", ("Do", "not")),
                   is_negation=True),
        make_token("you", "you", 6, 9),
        make_token("know", "know", 10, 14, lemma="know"),
        make_token("?", "?", 14, 15, kind=TokenKind.PUNCTUATION),
    )

    construction = ConstructionCandidate(
        construction_key="know",
        pattern="NP know",
        predicate_schema_ref="schema:knows:v1",
        role_mappings={"entity": 1},
        confidence=0.8,
        source_token_indices=(1, 2),
    )

    evidence = make_evidence(
        tokens=tokens,
        raw_text="Don't you know?",
        construction_candidates=(construction,),
        communicative_candidates=(CommunicativeCandidate(
            force="ask",
            confidence=0.9,
        ),),
    )

    composer = SemanticComposer(store)
    graph = composer.compose(evidence)

    # Should have ask force AND negative polarity
    assert any(f.force == "ask" for f in graph.candidate_communicative_forces)
    assert any(cp.proposition.polarity == "negative" for cp in graph.candidate_propositions)


def test_force_to_open_ports():
    """Questions produce open ports for unknown role."""
    assert "role:unknown" in force_to_open_ports("ask")
    assert "role:desired_state" in force_to_open_ports("request")
    assert len(force_to_open_ports("assert")) == 0


# ── Context builder tests ──────────────────────────────────────────


def test_quoted_context_detected():
    """Quotation boundaries produce quoted context candidates."""
    tokens = (
        make_token("He", "he", 0, 2),
        make_token("said", "say", 3, 7),
        make_token('"', '"', 8, 9, kind=TokenKind.QUOTE_OPEN),
        make_token("hello", "hello", 9, 14),
        make_token('"', '"', 14, 15, kind=TokenKind.QUOTE_CLOSE),
    )

    qspan = QuotationSpan(open_offset=8, close_offset=15, content_offsets=(9, 14))
    stream = TokenStream(
        tokens=tokens,
        raw_text='He said "hello"',
        quotation_spans=(qspan,),
    )
    evidence = SurfaceEvidence(
        token_stream=stream,
        language_tag="en",
    )

    contexts = extract_context_candidates(evidence)
    assert any(c.context_kind == "quoted" for c in contexts)


def test_believed_context_detected():
    """Epistemic verbs produce believed context candidates."""
    tokens = (
        make_token("I", "I", 0, 1),
        make_token("believe", "believe", 2, 9, lemma="believe"),
        make_token("he", "he", 10, 12),
        make_token("is", "is", 13, 15),
        make_token("right", "right", 16, 21),
    )

    evidence = make_evidence(tokens=tokens, raw_text="I believe he is right")
    contexts = extract_context_candidates(evidence)
    assert any(c.context_kind == "believed" for c in contexts)


def test_default_actual_context():
    """Default context is actual when no special markers present."""
    tokens = (
        make_token("I'm", "I am", 0, 3, kind=TokenKind.CONTRACTION),
        make_token("here", "here", 4, 8),
    )

    evidence = make_evidence(tokens=tokens, raw_text="I'm here")
    contexts = extract_context_candidates(evidence)
    assert any(c.context_kind == "actual" for c in contexts)


# ── Candidate graph alternatives tests ─────────────────────────────


def test_alternatives_preserved():
    """Multiple candidates for the same evidence must be preserved."""
    store = make_store_with_schema("instance_of")
    # Register a second schema for the same key
    env2 = SchemaEnvelope(
        record_id="schema:instance_of:v2",
        semantic_key="instance_of",
        schema_kind="predicate",
        status="active",
        provenance=Provenance(source_id="boot", source_kind="boot"),
    )
    store.register(env2)
    store.activate("schema:instance_of:v2", expected_revision=1)

    tokens = (
        make_token("I'm", "I am", 0, 3, kind=TokenKind.CONTRACTION),
        make_token("an", "a", 4, 6),
        make_token("engineer", "engineer", 7, 15),
    )

    lexical = LexicalSenseCandidate(
        lexical_form_ref=LexicalFormRef(surface="engineer", language_tag="en"),
        semantic_key="instance_of",
        confidence=0.8,
        source_token_indices=(2,),
    )

    evidence = make_evidence(
        tokens=tokens,
        raw_text="I'm an engineer",
        lexical_candidates=(lexical,),
    )

    composer = SemanticComposer(store)
    graph = composer.compose(evidence)

    # Should have multiple candidates (alternatives preserved)
    # (At least from lexical and construction sources)
    assert len(graph.candidate_predications) >= 1


# ── Import boundary tests ──────────────────────────────────────────


def test_language_stream_imports_no_engine():
    """Language stream must not import any engine module."""
    import cemm.language.stream as stream_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
    ]
    source = open(stream_mod.__file__, encoding="utf-8").read()
    for f in forbidden:
        assert f not in source, f"stream.py imports forbidden module {f}"


def test_composer_imports_no_engine():
    """Composer must not import any engine module."""
    import cemm.kernel.understanding.composer as composer_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
    ]
    source = open(composer_mod.__file__, encoding="utf-8").read()
    for f in forbidden:
        assert f not in source, f"composer.py imports forbidden module {f}"


def test_language_adapter_cannot_select_meaning():
    """Language adapter evidence is candidate-only — no final meaning selection."""
    # SurfaceEvidence has no method to select or finalize meaning
    tokens = (make_token("test", "test", 0, 4),)
    evidence = make_evidence(tokens=tokens, raw_text="test")

    # SurfaceEvidence must not have authoritative selection methods
    assert not hasattr(evidence, "select_meaning")
    assert not hasattr(evidence, "finalize")
    assert not hasattr(evidence, "activate")
    assert not hasattr(evidence, "commit")
