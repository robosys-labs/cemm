"""Persistence tests: revision, commit, and effect-journal semantics.

These tests run against both the SQLite reference backend and the test-only
in-memory backend (via ``any_stores`` parametrization) so that the two
implementations share the same behavioural contract.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.persistence import (
    CommitReceipt,
    StaleRevisionError,
)


# ---------------------------------------------------------------------------
# World store — revision & commit
# ---------------------------------------------------------------------------


class TestWorldCommit:
    def test_initial_revision_is_zero(self, any_stores):
        assert any_stores.world.revision == 0

    def test_commit_advances_revision(self, any_stores, fact_factory):
        receipt = any_stores.world.commit((fact_factory("one"),), expected_revision=0)
        assert isinstance(receipt, CommitReceipt)
        assert receipt.parent_revision == 0
        assert receipt.new_revision == 1
        assert any_stores.world.revision == 1

    def test_commit_persists_fact(self, any_stores, fact_factory):
        any_stores.world.commit((fact_factory("alpha"),), expected_revision=0)
        fact = any_stores.world.get("fact:alpha")
        assert fact is not None
        assert fact.fact_ref == "fact:alpha"

    def test_get_missing_fact_returns_none(self, any_stores):
        assert any_stores.world.get("fact:nonexistent") is None

    def test_commit_multiple_facts(self, any_stores, fact_factory):
        receipt = any_stores.world.commit(
            (fact_factory("a"), fact_factory("b")),
            expected_revision=0,
        )
        assert receipt.new_revision == 1
        assert any_stores.world.get("fact:a") is not None
        assert any_stores.world.get("fact:b") is not None

    def test_stale_writer_cannot_overwrite_newer_world(self, any_stores, fact_factory):
        revision = any_stores.world.revision
        any_stores.world.commit((fact_factory("one"),), expected_revision=revision)
        with pytest.raises(StaleRevisionError):
            any_stores.world.commit(
                (fact_factory("stale"),),
                expected_revision=revision,
            )

    def test_commit_with_correct_expected_revision_succeeds(self, any_stores, fact_factory):
        rev0 = any_stores.world.revision
        r1 = any_stores.world.commit((fact_factory("one"),), expected_revision=rev0)
        rev1 = any_stores.world.revision
        assert rev1 == r1.new_revision
        r2 = any_stores.world.commit((fact_factory("two"),), expected_revision=rev1)
        assert r2.parent_revision == rev1
        assert r2.new_revision == rev1 + 1

    def test_commit_receipt_has_delta_hash(self, any_stores, fact_factory):
        receipt = any_stores.world.commit((fact_factory("x"),), expected_revision=0)
        assert receipt.delta_hash
        assert isinstance(receipt.delta_hash, str)

    def test_commit_receipt_has_transaction_ref(self, any_stores, fact_factory):
        receipt = any_stores.world.commit((fact_factory("x"),), expected_revision=0)
        assert receipt.transaction_ref
        assert isinstance(receipt.transaction_ref, str)


# ---------------------------------------------------------------------------
# Effect journal — idempotency
# ---------------------------------------------------------------------------


class TestEffectJournal:
    def test_effect_commit_returns_receipt(self, any_stores, effect_factory):
        receipt = any_stores.effects.commit(effect_factory("key"))
        assert isinstance(receipt, CommitReceipt)
        assert receipt.store == "effects"

    def test_duplicate_effect_key_returns_original_receipt(self, any_stores, effect_factory):
        first = any_stores.effects.commit(effect_factory("effect:key"))
        second = any_stores.effects.commit(effect_factory("effect:key"))
        assert second == first

    def test_different_effect_keys_get_different_receipts(self, any_stores, effect_factory):
        first = any_stores.effects.commit(effect_factory("a"))
        second = any_stores.effects.commit(effect_factory("b"))
        assert first != second

    def test_effect_revision_advances(self, any_stores, effect_factory):
        assert any_stores.effects.revision == 0
        any_stores.effects.commit(effect_factory("a"))
        assert any_stores.effects.revision == 1
        # duplicate does not advance revision
        any_stores.effects.commit(effect_factory("a"))
        assert any_stores.effects.revision == 1


# ---------------------------------------------------------------------------
# Session store
# ---------------------------------------------------------------------------


class TestSessionStore:
    def test_create_session_advances_revision(self, any_stores):
        assert any_stores.sessions.revision == 0
        session = any_stores.sessions.create()
        assert session.session_ref
        assert any_stores.sessions.revision == 1

    def test_get_session(self, any_stores):
        session = any_stores.sessions.create()
        fetched = any_stores.sessions.get(session.session_ref)
        assert fetched is not None
        assert fetched.session_ref == session.session_ref

    def test_get_missing_session_returns_none(self, any_stores):
        assert any_stores.sessions.get("session:nonexistent") is None


# ---------------------------------------------------------------------------
# Episode store
# ---------------------------------------------------------------------------


class TestEpisodeStore:
    def test_append_episode_advances_revision(self, any_stores):
        assert any_stores.episodes.revision == 0
        any_stores.episodes.append({"event": "test"})
        assert any_stores.episodes.revision == 1

    def test_episode_rows_are_immutable_append_only(self, any_stores):
        any_stores.episodes.append({"event": "first"})
        any_stores.episodes.append({"event": "second"})
        rows = any_stores.episodes.rows()
        assert len(rows) == 2
        assert rows[0]["event"] == "first"
        assert rows[1]["event"] == "second"


# ---------------------------------------------------------------------------
# Revision pin
# ---------------------------------------------------------------------------


class TestRevisionPin:
    def test_revision_pin_captures_all_revisions(self, any_stores, fact_factory, effect_factory):
        any_stores.world.commit((fact_factory("w"),), expected_revision=0)
        any_stores.sessions.create()
        any_stores.episodes.append({"event": "e"})
        any_stores.effects.commit(effect_factory("ef"))
        pin = any_stores.revision_pin()
        assert pin.authority_generation
        assert pin.world_revision == any_stores.world.revision
        assert pin.session_revision == any_stores.sessions.revision
        assert pin.episode_revision == any_stores.episodes.revision
        assert pin.effect_revision == any_stores.effects.revision


# ---------------------------------------------------------------------------
# SemanticStores facade
# ---------------------------------------------------------------------------


class TestSemanticStores:
    def test_stores_expose_all_backends(self, any_stores):
        assert any_stores.world is not None
        assert any_stores.sessions is not None
        assert any_stores.episodes is not None
        assert any_stores.effects is not None
        assert any_stores.models is not None
        assert any_stores.focus is not None
        assert any_stores.obligations is not None

    def test_close_is_idempotent(self, any_stores):
        any_stores.close()
        any_stores.close()  # should not raise


# ---------------------------------------------------------------------------
# Model registry
# ---------------------------------------------------------------------------


class TestModelRegistry:
    def test_register_model_advances_revision(self, any_stores):
        assert any_stores.models.revision == 0
        any_stores.models.register("model:identity-1", {"kind": "proposal"})
        assert any_stores.models.revision == 1

    def test_get_model(self, any_stores):
        any_stores.models.register("model:identity-1", {"kind": "proposal"})
        model = any_stores.models.get("model:identity-1")
        assert model is not None
        assert model["model_identity"] == "model:identity-1"

    def test_get_missing_model_returns_none(self, any_stores):
        assert any_stores.models.get("model:nonexistent") is None
