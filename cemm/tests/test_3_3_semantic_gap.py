"""Tests for 3.3 SemanticGap detection and classification."""

from __future__ import annotations

from cemm.learning.semantic_gap_detector import SemanticGapDetector
from cemm.types.semantic_gap import SemanticGap, GapKind
from cemm.types.semantic_ref import SemanticRef, SemanticRefKind
from cemm.types.meaning_percept import MeaningPerceptPacket, MeaningGroup


def test_gap_detector_creates_gap_for_unknown_word():
    """Unknown word should produce a LEXEME_SENSE gap."""
    detector = SemanticGapDetector()
    percept = MeaningPerceptPacket(
        id="test",
        raw_text="zibble",
        unknown_lexemes=["zibble"],
        language="en",
    )
    gaps = detector.detect(percept)
    lexeme_gaps = [g for g in gaps if g.gap_kind == GapKind.LEXEME_SENSE]
    assert len(lexeme_gaps) > 0, "Unknown word should create lexeme sense gap"
    assert lexeme_gaps[0].surface_form == "zibble"
    assert lexeme_gaps[0].confidence == 0.0


def test_known_word_produces_no_gap():
    """Known word should not produce a gap."""
    detector = SemanticGapDetector()
    percept = MeaningPerceptPacket(
        id="test",
        raw_text="hello",
        unknown_lexemes=[],
        language="en",
    )
    gaps = detector.detect(percept, known_forms={"hello"})
    lexeme_gaps = [g for g in gaps if g.gap_kind == GapKind.LEXEME_SENSE]
    assert len(lexeme_gaps) == 0, "Known word should not create lexeme sense gap"


def test_gap_classification_blocking():
    """Gaps in selected branches should be classified as blocking."""
    detector = SemanticGapDetector()
    gap = SemanticGap(
        gap_id="test_gap",
        branch_id="branch_1",
        group_id="group_1",
        span_ref=SemanticRef(kind=SemanticRefKind.SPAN, id="span_1"),
        language_tag="en",
        gap_kind=GapKind.LEXEME_SENSE,
        blocking_artifact_ids=["obligation_1"],
    )
    
    blocking = detector.classify_blocking([gap], {"branch_1"})
    assert len(blocking) == 1
    assert blocking[0].gap_id == "test_gap"


def test_gap_classification_nonblocking():
    """Gaps not in selected branches should not be blocking."""
    detector = SemanticGapDetector()
    gap = SemanticGap(
        gap_id="test_gap_2",
        branch_id="branch_2",
        group_id="group_1",
        span_ref=SemanticRef(kind=SemanticRefKind.SPAN, id="span_1"),
        language_tag="en",
        gap_kind=GapKind.TEMPORAL_ANCHOR,
    )
    
    blocking = detector.classify_blocking([gap], {"branch_1"})
    assert len(blocking) == 0


def test_unknown_lexeme_from_dict():
    """Unknown lexeme as dict should produce a gap."""
    detector = SemanticGapDetector()
    percept = MeaningPerceptPacket(
        id="test",
        raw_text="RUNNING",
        unknown_lexemes=[{"surface": "running", "token": "RUNNING"}],
        language="en",
    )
    gaps = detector.detect(percept)
    lexeme_gaps = [g for g in gaps if g.gap_kind == GapKind.LEXEME_SENSE]
    assert len(lexeme_gaps) > 0


def test_gap_deduplication():
    """Duplicate gaps should be deduplicated by surface_form and gap_kind."""
    detector = SemanticGapDetector()
    percept = MeaningPerceptPacket(
        id="test",
        raw_text="zibble zibble",
        unknown_lexemes=["zibble", "zibble"],
        language="en",
    )
    gaps = detector.detect(percept)
    lexeme_gaps = [g for g in gaps if g.gap_kind == GapKind.LEXEME_SENSE]
    surfaces = [g.surface_form for g in lexeme_gaps]
    assert len(surfaces) == len(set(surfaces)), "Duplicate gaps were not deduplicated"


def test_empty_percept_produces_no_gaps():
    """A percept with no unknown lexemes produces no gaps."""
    detector = SemanticGapDetector()
    percept = MeaningPerceptPacket(
        id="test",
        raw_text="hello world",
        unknown_lexemes=[],
        language="en",
    )
    gaps = detector.detect(percept)
    assert len(gaps) == 0


def test_gap_on_group_without_predicate():
    """A meaning group with referent but no predicate should produce a CONSTRUCTION gap."""
    from cemm.types.uol_graph import UOLGraph

    detector = SemanticGapDetector()
    percept = MeaningPerceptPacket(
        id="test",
        raw_text="something",
        unknown_lexemes=[],
        language="en",
        meaning_groups=[
            MeaningGroup(id="group_1", surface="something"),
        ],
    )
    graph = UOLGraph(id="test_graph")
    graph.add_atom("entity", "entity:something", group_id="group_1")

    gaps = detector.detect(percept, graph)
    construction_gaps = [g for g in gaps if g.gap_kind == GapKind.CONSTRUCTION]
    assert len(construction_gaps) > 0


def test_gap_on_group_with_predicate_no_gap():
    """A meaning group with a predicate and referent should NOT produce a CONSTRUCTION gap."""
    from cemm.types.uol_graph import UOLGraph

    detector = SemanticGapDetector()
    percept = MeaningPerceptPacket(
        id="test",
        raw_text="hello world",
        unknown_lexemes=[],
        language="en",
        meaning_groups=[
            MeaningGroup(id="group_1", surface="hello world"),
        ],
    )
    graph = UOLGraph(id="test_graph")
    graph.add_atom("action", "action:greet", group_id="group_1")
    graph.add_atom("entity", "entity:world", group_id="group_1")

    gaps = detector.detect(percept, graph)
    construction_gaps = [g for g in gaps if g.gap_kind == GapKind.CONSTRUCTION]
    assert len(construction_gaps) == 0


def test_existing_semantic_gaps_preserved():
    """Pre-existing semantic_gaps on the percept should be carried through."""
    detector = SemanticGapDetector()
    existing = SemanticGap(
        gap_id="pre_existing",
        branch_id="",
        group_id="",
        span_ref=SemanticRef(kind=SemanticRefKind.SPAN, id="span_x"),
        language_tag="en",
        gap_kind=GapKind.TEMPORAL_ANCHOR,
        surface_form="yesterday",
    )
    percept = MeaningPerceptPacket(
        id="test",
        raw_text="yesterday",
        unknown_lexemes=[],
        language="en",
        semantic_gaps=[existing],
    )
    gaps = detector.detect(percept)
    ids = [g.gap_id for g in gaps]
    assert "pre_existing" in ids
