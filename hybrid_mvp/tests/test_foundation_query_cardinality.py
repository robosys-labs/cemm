"""No arbitrary single-answer selection from multi-binding query evidence.

The current ResponseMeaning ABI supports one scalar binding solution, not an
exhaustive solution set. Until a set-valued answer contract is admitted,
multiple distinct solutions must produce a typed partial result, never a
plausible but incomplete 'answer'.
"""
from __future__ import annotations

from pathlib import Path

from cemm_authoritative_hybrid.foundation import load_foundation
from cemm_authoritative_hybrid.persistence import Fact
from cemm_authoritative_hybrid.r3_persistence import install_reviewed_world_facts

ROOT = Path(__file__).resolve().parents[1]


def _ownership(owner: str, evidence: str) -> Fact:
    return Fact(
        fact_ref=f"fact:ownership:{owner}:{evidence}",
        operator="op:relation",
        args={
            "predicate_ref": "rel:owns",
            "role:subject": owner,
            "role:object": "entity:book",
        },
        proof={"source": evidence, "placement": "observed"},
    )


def test_distinct_verified_answers_cannot_collapse_into_first_match(tmp_path):
    runtime = load_foundation(ROOT, store_path=tmp_path / "several.sqlite3")
    try:
        install_reviewed_world_facts(
            runtime.stores,
            facts=(
                _ownership("entity:alice", "source:alice"),
                _ownership("entity:bob", "source:bob"),
            ),
        )
        before = runtime.stores.revision_pin().world_revision
        result = runtime.process("session:two-owners", "Who owns the book?")
        assert result.verify()
        response = result.cycle.response_meaning
        assert response is not None
        assert response.discourse_action == "clarify"
        assert response.bindings == (), "scalar ABI cannot emit arbitrary one of two answers"
        assert "query:multiple_bindings" in response.blocker_refs
        assert runtime.stores.revision_pin().world_revision == before
    finally:
        runtime.close()


def test_duplicate_evidence_for_one_binding_does_not_invent_ambiguity(tmp_path):
    runtime = load_foundation(ROOT, store_path=tmp_path / "same-owner.sqlite3")
    try:
        install_reviewed_world_facts(
            runtime.stores,
            facts=(
                _ownership("entity:alice", "source:first"),
                _ownership("entity:alice", "source:second"),
            ),
        )
        result = runtime.process("session:single-owner", "Who owns the book?")
        assert result.verify()
        response = result.cycle.response_meaning
        assert response is not None
        assert response.discourse_action == "answer"
        assert ("?v0", "entity:alice") in response.bindings
    finally:
        runtime.close()
