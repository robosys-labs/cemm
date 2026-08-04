"""Tests for the reversible form lattice (FormResolver).

These tests verify that the FormResolver preserves every source unit, keeps
monotonic span offsets, generates bounded construction hypotheses, and assigns
closed-class features from the language pack without choosing operators or
inspecting internal ref spelling.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck

from cemm_authoritative_hybrid.forms import (
    EvidenceItem,
    EvidencePacket,
    FormHypothesis,
    FormLattice,
    FormResolver,
    FormUnit,
)
from cemm_authoritative_hybrid.config import RuntimeConfig

ROOT = Path(__file__).parents[1]
FORMS_PATH = ROOT / "data" / "languages" / "en" / "forms.json"


# ---------------------------------------------------------------------------
# Reversibility: every source unit is preserved
# ---------------------------------------------------------------------------


def test_form_lattice_preserves_every_source_unit(form_resolver):
    lattice = form_resolver.resolve("And you are called what?")
    assert (
        "".join(unit.source_text for unit in lattice.units)
        == "And you are called what?"
    )
    assert all(unit.source_start < unit.source_end for unit in lattice.units)
    assert len(lattice.hypotheses) <= 16


def test_empty_text_produces_empty_lattice(form_resolver):
    lattice = form_resolver.resolve("")
    assert lattice.units == ()
    assert lattice.hypotheses == ()
    assert lattice.source_text == ""


def test_single_word_preserved(form_resolver):
    lattice = form_resolver.resolve("hello")
    assert "".join(u.source_text for u in lattice.units) == "hello"
    assert len(lattice.units) == 1


def test_whitespace_preserved_between_units(form_resolver):
    text = "hello   world"
    lattice = form_resolver.resolve(text)
    assert "".join(u.source_text for u in lattice.units) == text


def test_punctuation_preserved(form_resolver):
    text = "hello, world!"
    lattice = form_resolver.resolve(text)
    assert "".join(u.source_text for u in lattice.units) == text


def test_trailing_punctuation_preserved(form_resolver):
    text = "what?"
    lattice = form_resolver.resolve(text)
    assert "".join(u.source_text for u in lattice.units) == text


def test_leading_and_trailing_whitespace_preserved(form_resolver):
    text = "  hi  "
    lattice = form_resolver.resolve(text)
    assert "".join(u.source_text for u in lattice.units) == text


# ---------------------------------------------------------------------------
# Closed-class feature assignment
# ---------------------------------------------------------------------------


def test_query_marker_assigned(form_resolver):
    lattice = form_resolver.resolve("what is your name")
    features = {k: v for u in lattice.units for k, v in u.features}
    assert features.get("query") == "query"


def test_participant_deixis_assigned(form_resolver):
    lattice = form_resolver.resolve("you are here")
    you_unit = next(u for u in lattice.units if u.source_text == "you")
    features = dict(you_unit.features)
    assert "participant" in features


def test_binder_assigned(form_resolver):
    lattice = form_resolver.resolve("you are here")
    are_unit = next(u for u in lattice.units if u.source_text == "are")
    features = dict(are_unit.features)
    assert features.get("binder") == "copula"


def test_polarity_assigned(form_resolver):
    lattice = form_resolver.resolve("not here")
    not_unit = next(u for u in lattice.units if u.source_text == "not")
    features = dict(not_unit.features)
    assert features.get("polarity") == "negation"


def test_modality_assigned(form_resolver):
    lattice = form_resolver.resolve("you can go")
    can_unit = next(u for u in lattice.units if u.source_text == "can")
    features = dict(can_unit.features)
    assert features.get("modality") == "capability"


def test_connector_assigned(form_resolver):
    lattice = form_resolver.resolve("alice and bob")
    and_unit = next(u for u in lattice.units if u.source_text == "and")
    features = dict(and_unit.features)
    assert features.get("connector") == "coordination"


def test_unknown_word_has_no_closed_class_features(form_resolver):
    lattice = form_resolver.resolve("zorbulate now")
    zorb = next(u for u in lattice.units if u.source_text == "zorbulate")
    assert zorb.features == ()


# ---------------------------------------------------------------------------
# Bounded construction hypotheses
# ---------------------------------------------------------------------------


def test_hypotheses_bounded_by_16(form_resolver):
    lattice = form_resolver.resolve("you are called what and is not can because said")
    assert len(lattice.hypotheses) <= 16


def test_hypotheses_reference_valid_units(form_resolver):
    lattice = form_resolver.resolve("you are here")
    unit_refs = {u.unit_ref for u in lattice.units}
    for hyp in lattice.hypotheses:
        for ref in hyp.unit_refs:
            assert ref in unit_refs


def test_form_lattice_source_text_matches_input(form_resolver):
    text = "And you are called what?"
    lattice = form_resolver.resolve(text)
    assert lattice.source_text == text


# ---------------------------------------------------------------------------
# Hypothesis property tests
# ---------------------------------------------------------------------------


_TEXT_ALPHABET = st.characters(
    whitelist_categories=("Ll", "Lu", "Lm", "Lo", "Nd", "Pc", "Pd", "Po", "Sc", "Sm"),
    whitelist_characters=" '",
)


@st.composite
def _bounded_text(draw):
    words = draw(
        st.lists(
            st.text(alphabet=_TEXT_ALPHABET, min_size=1, max_size=8),
            min_size=0,
            max_size=10,
        )
    )
    return " ".join(words)


@given(text=_bounded_text())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_no_unit_lost_hypothesis(form_resolver, text):
    lattice = form_resolver.resolve(text)
    assert "".join(u.source_text for u in lattice.units) == text


@given(text=_bounded_text())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_span_offsets_monotonic_hypothesis(form_resolver, text):
    lattice = form_resolver.resolve(text)
    for u in lattice.units:
        assert u.source_start < u.source_end
    # Units should not overlap: sorted by start, end <= next start
    starts = [u.source_start for u in lattice.units]
    ends = [u.source_end for u in lattice.units]
    assert starts == sorted(starts)
    for i in range(len(ends) - 1):
        assert ends[i] <= starts[i + 1]


@given(text=_bounded_text())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_hypotheses_bounded_hypothesis(form_resolver, text):
    lattice = form_resolver.resolve(text)
    assert len(lattice.hypotheses) <= 16


@given(text=_bounded_text())
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_unit_refs_unique_hypothesis(form_resolver, text):
    lattice = form_resolver.resolve(text)
    refs = [u.unit_ref for u in lattice.units]
    assert len(refs) == len(set(refs))


# ---------------------------------------------------------------------------
# EvidencePacket construction
# ---------------------------------------------------------------------------


def test_evidence_packet_from_text(form_resolver):
    lattice = form_resolver.resolve("hello world")
    item = EvidenceItem(
        source="text",
        content="hello world",
        source_ref="text:0",
        provenance_refs=(),
        adapter_receipt_ref=None,
    )
    packet = EvidencePacket(
        items=(item,),
        source_text="hello world",
        form_pack_hash="sha256:abc",
    )
    assert packet.source_text == "hello world"
    assert len(packet.items) == 1


def test_evidence_item_is_frozen():
    item = EvidenceItem(
        source="text",
        content="hi",
        source_ref="text:0",
        provenance_refs=(),
        adapter_receipt_ref=None,
    )
    with pytest.raises(Exception):
        item.source = "sensor"  # type: ignore[misc]


def test_form_unit_is_frozen():
    unit = FormUnit(
        unit_ref="unit:0",
        source_text="hi",
        normalized_forms=("hi",),
        source_start=0,
        source_end=2,
        features=(("participant", "reference_system"),),
    )
    with pytest.raises(Exception):
        unit.source_text = "bye"  # type: ignore[misc]


def test_form_lattice_is_frozen(form_resolver):
    lattice = form_resolver.resolve("hi")
    with pytest.raises(Exception):
        lattice.units = ()  # type: ignore[misc]


def test_form_hypothesis_is_frozen():
    hyp = FormHypothesis(
        hypothesis_ref="hyp:0",
        unit_refs=("unit:0",),
        construction="query",
        features=(("query", "query"),),
    )
    with pytest.raises(Exception):
        hyp.construction = None  # type: ignore[misc]
