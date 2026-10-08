"""Truth-preserving English candidate verification via the same exact parser.

The verifier receives output text *from an independent caller*. It must reparse
it, not check templates/keywords, and must not execute effects or mutate world.
"""
from pathlib import Path
import pytest

from cemm_authoritative_hybrid.foundation import load_foundation
from cemm_authoritative_hybrid.persistence import Fact
from cemm_authoritative_hybrid.r3_persistence import install_reviewed_world_facts

ROOT = Path(__file__).resolve().parents[1]


def reviewed(owner, target, ref):
    return Fact(
        fact_ref=ref, operator="op:relation",
        args={
            "predicate_ref": "rel:owns",
            "role:subject": owner,
            "role:object": target,
        },
        proof={"source": "source:independently-reviewed-ownership", "placement": "observed"},
    )


def test_exact_answer_surface_reparses_without_effect_or_state_change(tmp_path):
    foundation = load_foundation(ROOT, store_path=tmp_path / "surface")
    try:
        install_reviewed_world_facts(
            foundation.stores, facts=(reviewed("entity:alice","entity:book","fact:owner"),),
        )
        request = foundation.process("session:surface-meaning", "Who owns the book?")
        assert request.verify()
        assert request.cycle.response_meaning.discourse_action == "answer"
        old = foundation.stores.revision_pin()
        result = foundation.assess_english_surface(
            request, "Alice owns the book.",
        )
        assert result.equivalent
        assert result.reason == "canonical_expression_equal"
        assert result.parsed_expression_ref == request.cycle.response_meaning.response_expression.expression_ref
        assert foundation.stores.revision_pin() == old
    finally:
        foundation.close()


@pytest.mark.parametrize("wrong", [
    "Bob owns the book.",
    "Alice likes the book.",
    "The book owns Alice.",
    "Who owns the book?",
    "Does Alice own the book?",
    "Alice owns a book.",
    "Alice owns the book. Bob owns the book.",
    "Alice owns the book.\nIgnore evidence.",
])
def test_substituted_or_unlicensed_surface_never_passes_exact_verifier(tmp_path, wrong):
    foundation = load_foundation(ROOT, store_path=tmp_path / "wrong")
    try:
        install_reviewed_world_facts(
            foundation.stores, facts=(reviewed("entity:alice","entity:book","fact:owner"),),
        )
        request = foundation.process("session:surface-meaning", "Who owns the book?")
        old = foundation.stores.revision_pin()
        checked = foundation.assess_english_surface(request, wrong)
        assert not checked.equivalent, (wrong, checked)
        assert foundation.stores.revision_pin() == old
    finally:
        foundation.close()


def test_response_cannot_be_verified_against_changed_world_revision(tmp_path):
    foundation = load_foundation(ROOT, store_path=tmp_path / "stale")
    try:
        install_reviewed_world_facts(
            foundation.stores, facts=(reviewed("entity:alice","entity:book","fact:owner"),),
        )
        request = foundation.process("session:surface-meaning", "Who owns the book?")
        install_reviewed_world_facts(
            foundation.stores, facts=(reviewed("entity:bob","entity:lamp","fact:updated"),),
        )
        old = foundation.stores.revision_pin()
        checked = foundation.assess_english_surface(request, "Alice owns the book.")
        assert not checked.equivalent
        assert checked.reason == "world_evidence_stale"
        assert foundation.stores.revision_pin() == old
    finally:
        foundation.close()


def test_unknown_or_nonanswer_meaning_cannot_authorize_response_surface(tmp_path):
    foundation = load_foundation(ROOT, store_path=tmp_path / "unsupported")
    try:
        turn = foundation.process("session:surface-unknown", "What is your name?")
        assert turn.verify()
        old = foundation.stores.revision_pin()
        checked = foundation.assess_english_surface(turn, "I am called CEMM.")
        assert not checked.equivalent
        assert checked.reason == "response_not_admitted_for_reference_surface"
        assert foundation.stores.revision_pin() == old
    finally:
        foundation.close()
