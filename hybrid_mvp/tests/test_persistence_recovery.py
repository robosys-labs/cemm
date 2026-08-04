"""Recovery tests: restart preserves exact revisions and hashes.

These tests use the SQLite backend exclusively because the in-memory backend
is process-local and cannot survive restart.
"""

from __future__ import annotations

import pytest

from cemm_authoritative_hybrid.persistence import (
    CommitReceipt,
    StoreActivationError,
    StaleRevisionError,
)


# ---------------------------------------------------------------------------
# Restart recovery
# ---------------------------------------------------------------------------


class TestRestartRecovery:
    def test_restart_recovers_last_verified_revisions(
        self, store_path, stores_factory, fact_factory
    ):
        first = stores_factory(store_path)
        receipt = first.world.commit((fact_factory("persisted"),), expected_revision=0)
        first.close()

        second = stores_factory(store_path)
        assert second.world.revision == receipt.new_revision
        assert second.world.get("fact:persisted") is not None
        second.close()

    def test_restart_preserves_fact_hash(self, store_path, stores_factory, fact_factory):
        first = stores_factory(store_path)
        fact = fact_factory("hashed")
        receipt = first.world.commit((fact,), expected_revision=0)
        first.close()

        second = stores_factory(store_path)
        recovered = second.world.get("fact:hashed")
        assert recovered is not None
        assert recovered.fact_ref == fact.fact_ref
        assert recovered.operator == fact.operator
        assert dict(recovered.args) == dict(fact.args)
        assert recovered.stance == fact.stance
        assert recovered.confidence == fact.confidence
        assert recovered.derived == fact.derived
        assert dict(recovered.proof) == dict(fact.proof)
        second.close()

    def test_restart_preserves_effect_journal(self, store_path, stores_factory, effect_factory):
        first = stores_factory(store_path)
        receipt = first.effects.commit(effect_factory("persisted-effect"))
        first.close()

        second = stores_factory(store_path)
        assert second.effects.revision == receipt.new_revision
        # duplicate after restart still returns original receipt
        dup = second.effects.commit(effect_factory("persisted-effect"))
        assert dup == receipt
        second.close()

    def test_restart_preserves_sessions(self, store_path, stores_factory):
        first = stores_factory(store_path)
        session = first.sessions.create()
        first.close()

        second = stores_factory(store_path)
        assert second.sessions.revision == 1
        fetched = second.sessions.get(session.session_ref)
        assert fetched is not None
        assert fetched.session_ref == session.session_ref
        second.close()

    def test_restart_preserves_episodes(self, store_path, stores_factory):
        first = stores_factory(store_path)
        first.episodes.append({"event": "persisted"})
        first.close()

        second = stores_factory(store_path)
        assert second.episodes.revision == 1
        rows = second.episodes.rows()
        assert len(rows) == 1
        assert rows[0]["event"] == "persisted"
        second.close()

    def test_restart_preserves_models(self, store_path, stores_factory):
        first = stores_factory(store_path)
        first.models.register("model:identity-1", {"kind": "proposal"})
        first.close()

        second = stores_factory(store_path)
        assert second.models.revision == 1
        model = second.models.get("model:identity-1")
        assert model is not None
        second.close()

    def test_restart_preserves_revision_pin(self, store_path, stores_factory, fact_factory, effect_factory):
        first = stores_factory(store_path)
        first.world.commit((fact_factory("w"),), expected_revision=0)
        first.sessions.create()
        first.episodes.append({"event": "e"})
        first.effects.commit(effect_factory("ef"))
        pin_before = first.revision_pin()
        first.close()

        second = stores_factory(store_path)
        pin_after = second.revision_pin()
        assert pin_after.world_revision == pin_before.world_revision
        assert pin_after.session_revision == pin_before.session_revision
        assert pin_after.episode_revision == pin_before.episode_revision
        assert pin_after.effect_revision == pin_before.effect_revision
        second.close()

    def test_restart_with_multiple_commits(self, store_path, stores_factory, fact_factory):
        first = stores_factory(store_path)
        r1 = first.world.commit((fact_factory("a"),), expected_revision=0)
        r2 = first.world.commit((fact_factory("b"),), expected_revision=r1.new_revision)
        r3 = first.world.commit((fact_factory("c"),), expected_revision=r2.new_revision)
        first.close()

        second = stores_factory(store_path)
        assert second.world.revision == 3
        assert second.world.get("fact:a") is not None
        assert second.world.get("fact:b") is not None
        assert second.world.get("fact:c") is not None
        second.close()


# ---------------------------------------------------------------------------
# Activation integrity
# ---------------------------------------------------------------------------


class TestActivationIntegrity:
    def test_activation_error_on_corrupted_row(self, store_path, stores_factory, fact_factory):
        first = stores_factory(store_path)
        first.world.commit((fact_factory("corrupt"),), expected_revision=0)
        first.close()

        # Corrupt the payload hash directly in the database
        import sqlite3
        db_path = store_path / "semantic.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "UPDATE world_facts SET payload_hash = 'tampered' WHERE fact_ref = ?",
            ("fact:corrupt",),
        )
        conn.commit()
        conn.close()

        with pytest.raises(StoreActivationError) as exc_info:
            stores_factory(store_path)

        recovery = exc_info.value.recovery_receipt
        assert recovery.last_verified_revision is not None
        assert "fact:corrupt" in recovery.corrupt_refs
        assert recovery.recommended_action

    def test_activation_error_never_resets_database(self, store_path, stores_factory, fact_factory):
        first = stores_factory(store_path)
        first.world.commit((fact_factory("safe"),), expected_revision=0)
        first.close()

        # Corrupt
        import sqlite3
        db_path = store_path / "semantic.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "UPDATE world_facts SET payload_hash = 'bad' WHERE fact_ref = ?",
            ("fact:safe",),
        )
        conn.commit()
        conn.close()

        with pytest.raises(StoreActivationError):
            stores_factory(store_path)

        # Database still contains the row — it was not reset
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT fact_ref FROM world_facts WHERE fact_ref = ?", ("fact:safe",)
        ).fetchone()
        conn.close()
        assert row is not None

    def test_clean_database_activates_without_error(self, store_path, stores_factory, fact_factory):
        first = stores_factory(store_path)
        first.world.commit((fact_factory("clean"),), expected_revision=0)
        first.close()

        # Should not raise
        second = stores_factory(store_path)
        assert second.world.get("fact:clean") is not None
        second.close()


# ---------------------------------------------------------------------------
# Stale revision across restart
# ---------------------------------------------------------------------------


class TestStaleRevisionAcrossRestart:
    def test_stale_revision_after_restart(self, store_path, stores_factory, fact_factory):
        first = stores_factory(store_path)
        first.world.commit((fact_factory("one"),), expected_revision=0)
        first.close()

        second = stores_factory(store_path)
        # revision is now 1, using stale expected_revision=0 should fail
        with pytest.raises(StaleRevisionError):
            second.world.commit((fact_factory("stale"),), expected_revision=0)
        second.close()
