"""Proof revisions must reflect other SQLite writers, not stale facade caches."""
from pathlib import Path

from cemm_authoritative_hybrid.foundation import load_foundation
from cemm_authoritative_hybrid.persistence import Fact
from cemm_authoritative_hybrid.r3_persistence import install_reviewed_world_facts

ROOT = Path(__file__).resolve().parents[1]


def owner_fact():
    return Fact(
        fact_ref="fact:live-owner",
        operator="op:relation",
        args={
            "predicate_ref": "rel:owns",
            "role:subject": "entity:alice",
            "role:object": "entity:book",
        },
        proof={"source":"source:reviewed-live-owner","placement":"observed"},
    )


def test_other_sqlite_connection_world_commit_updates_live_revision(tmp_path):
    store=tmp_path/"live-world"
    first=load_foundation(ROOT,store_path=store)
    second=load_foundation(ROOT,store_path=store)
    try:
        initial=second.stores.revision_pin()
        install_reviewed_world_facts(first.stores,facts=(owner_fact(),))
        actual=second.stores.revision_pin()
        assert actual.world_revision == initial.world_revision + 1
        assert second.stores.world.revision == actual.world_revision
        result=second.process("session:live-query", "Who owns the book?")
        assert result.verify()
        assert result.cycle.response_meaning.discourse_action == "answer"
        assert ("?v0","entity:alice") in result.cycle.response_meaning.bindings
    finally:
        first.close()
        second.close()


def test_other_connection_non_world_turn_invalidates_stale_surface(tmp_path):
    store=tmp_path/"live-response"
    first=load_foundation(ROOT,store_path=store)
    second=load_foundation(ROOT,store_path=store)
    try:
        install_reviewed_world_facts(first.stores,facts=(owner_fact(),))
        result=first.process("session:live-answer","Who owns the book?")
        assert result.verify()
        assert first.assess_english_surface(
            result, "Alice owns the book."
        ).equivalent
        before=first.stores.revision_pin()
        extra=second.process("session:separate","hello")
        assert extra.verify()
        after=first.stores.revision_pin()
        assert before.world_revision == after.world_revision
        assert after.session_revision > before.session_revision
        assert after.effect_revision > before.effect_revision
        stale=first.assess_english_surface(result,"Alice owns the book.")
        assert not stale.equivalent
        assert stale.reason == "response_revision_stale"
    finally:
        first.close()
        second.close()
