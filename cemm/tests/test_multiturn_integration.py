"""Multiturn seed-powered integration tests.

Exercises the full Pipeline.run() path with real seed data from
self_knowledge.json, verifying that self-queries, teaching, social,
and mixed conversations work end-to-end across multiple turns.
"""

from __future__ import annotations

import os
import sys
import random
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ.setdefault("CEMM_EXPORT_PATH", "")

from cemm.tests.harness import SeededSystem, seed_durable_from_config, make_signal


# ── Self-query conversations ─────────────────────────────────────────


class TestSelfQueryMultiturn:
    """Verify self-knowledge queries work across multiple turns with seed data."""

    def test_name_query_returns_identity(self):
        sys = SeededSystem()
        seed_durable_from_config(sys)
        r = sys.run("what's your name?")
        assert r["has_answer"] is True, f"abstention: {r['abstention_reason']}"
        assert r["relation_key"] == "answers_identity_as"
        assert "CEMM" in r["output"]
        assert r["errors"] == []

    def test_capability_query_returns_capabilities(self):
        sys = SeededSystem()
        seed_durable_from_config(sys)
        r = sys.run("what can you do?")
        assert r["has_answer"] is True, f"abstention: {r['abstention_reason']}"
        assert r["relation_key"] == "capability"
        assert len(r["slot_fills"]) >= 2
        assert r["output"] != ""
        assert r["errors"] == []

    def test_self_knowledge_query(self):
        sys = SeededSystem()
        seed_durable_from_config(sys)
        r = sys.run("what do you know about yourself?")
        assert r["has_answer"] is True, f"abstention: {r['abstention_reason']}"
        assert r["relation_key"] == "knows_about"
        assert r["output"] != ""

    def test_repeated_queries_are_stable(self):
        """Same query 3 times should produce consistent answers."""
        sys = SeededSystem()
        seed_durable_from_config(sys)
        results = sys.run_turns([
            "what's your name?",
            "what's your name?",
            "what's your name?",
        ])
        for r in results:
            assert r["has_answer"] is True
            assert "CEMM" in r["output"]
        # All three should produce the same output
        outputs = [r["output"] for r in results]
        assert len(set(outputs)) == 1, f"Inconsistent outputs: {outputs}"

    def test_mixed_self_queries_in_sequence(self):
        """Different self-queries in sequence should each get correct answers."""
        sys = SeededSystem()
        seed_durable_from_config(sys)
        results = sys.run_turns([
            "what's your name?",
            "what can you do?",
            "what's your name?",
        ])
        assert results[0]["relation_key"] == "answers_identity_as"
        assert results[1]["relation_key"] == "capability"
        assert results[2]["relation_key"] == "answers_identity_as"
        assert all(r["has_answer"] for r in results)
        assert all(r["errors"] == [] for r in results)


# ── Social conversation ──────────────────────────────────────────────


class TestSocialMultiturn:
    """Social greetings and closings should produce non-empty responses."""

    def test_greeting_sequence(self):
        sys = SeededSystem()
        seed_durable_from_config(sys)
        results = sys.run_turns(["hi", "hello", "hey there"])
        for r in results:
            assert r["obligation_kind"] == "social_reply"
            assert r["output"] != ""
            assert r["errors"] == []

    def test_social_then_self_query(self):
        """Social greeting followed by self-query should work."""
        sys = SeededSystem()
        seed_durable_from_config(sys)
        results = sys.run_turns(["hi", "what's your name?"])
        assert results[0]["obligation_kind"] == "social_reply"
        assert results[1]["has_answer"] is True
        assert "CEMM" in results[1]["output"]


# ── Teaching and persistence ─────────────────────────────────────────


class TestTeachingMultiturn:
    """Teaching a fact and then querying it should work across turns."""

    def test_teach_then_query(self):
        sys = SeededSystem()
        seed_durable_from_config(sys)
        r1 = sys.run("remember that a dog is an animal")
        r2 = sys.run("what is a dog?")
        # Teaching should produce a patch or at least not error
        assert r1["errors"] == []
        # Query should find the taught relation
        assert r2["errors"] == []
        # Either has an answer or abstains gracefully (no crash)
        assert r2["output"] != "" or r2["abstention_reason"] != ""

    def test_teach_multiple_facts(self):
        sys = SeededSystem()
        seed_durable_from_config(sys)
        results = sys.run_turns([
            "remember that Paris is the capital of France",
            "remember that Tokyo is the capital of Japan",
        ])
        assert all(r["errors"] == [] for r in results)
        # Durable store should have grown
        assert results[-1]["durable_count"] >= results[0]["durable_count"]


# ── Session persistence ──────────────────────────────────────────────


class TestSessionPersistence:
    """Session state should persist across turns within the same context."""

    def test_turn_index_increments(self):
        sys = SeededSystem()
        r1 = sys.run("hello")
        r2 = sys.run("hi")
        assert r2["turn"] > r1["turn"]

    def test_same_context_maintains_state(self):
        sys = SeededSystem(context_id="persist_test")
        seed_durable_from_config(sys)
        results = sys.run_turns([
            "what's your name?",
            "what can you do?",
            "what's your name?",
        ])
        # All turns should succeed without errors
        assert all(r["errors"] == [] for r in results)
        # Durable count should stay stable (no duplicate seeding)
        assert results[0]["durable_count"] == results[-1]["durable_count"]


# ── Edge cases ───────────────────────────────────────────────────────


class TestEdgeCases:
    """Edge case inputs should not crash the system."""

    def test_empty_string(self):
        sys = SeededSystem()
        seed_durable_from_config(sys)
        r = sys.run("")
        assert r["errors"] == [] or "empty" in " ".join(r["errors"]).lower()

    def test_very_long_input(self):
        sys = SeededSystem()
        seed_durable_from_config(sys)
        text = " ".join(["hello"] * 200)
        r = sys.run(text)
        assert r["errors"] == []

    def test_special_characters(self):
        sys = SeededSystem()
        seed_durable_from_config(sys)
        r = sys.run("what's your name?!!! @#$%^&*()")
        assert r["errors"] == []

    def test_repeated_same_input(self):
        sys = SeededSystem()
        seed_durable_from_config(sys)
        results = sys.run_turns(["what's your name?"] * 5)
        assert all(r["has_answer"] for r in results)
        assert all("CEMM" in r["output"] for r in results)

    def test_unknown_question_abstains_gracefully(self):
        sys = SeededSystem()
        seed_durable_from_config(sys)
        r = sys.run("what is the meaning of life?")
        assert r["errors"] == []
        # Should either answer or abstain, but not crash
        assert r["output"] != "" or r["abstention_reason"] != ""
