"""A cognition turn must not materialize the unbounded world fact table.

The reference foundation may temporarily use bounded snapshots until indexed
predicate/role retrieval is admitted; overflow must yield an explicit budget
blocker, not an inaccurate partial search result.
"""
from pathlib import Path

from cemm_authoritative_hybrid.foundation import load_foundation
from cemm_authoritative_hybrid.persistence import Fact
from cemm_authoritative_hybrid.r3_persistence import install_reviewed_world_facts

ROOT = Path(__file__).resolve().parents[1]


def fact(index: int, target: str = "entity:book") -> Fact:
    return Fact(
        fact_ref=f"fact:budget:{index}",
        operator="op:relation",
        args={
            "predicate_ref": "rel:owns",
            "role:subject": "entity:alice",
            "role:object": target,
        },
        proof={"source": f"source:budget:{index}", "placement": "observed"},
    )


def test_public_query_does_not_call_unbounded_world_facts(monkeypatch, tmp_path):
    runtime = load_foundation(ROOT, store_path=tmp_path / "bounded.sqlite3")
    try:
        install_reviewed_world_facts(runtime.stores, facts=(fact(1),))

        def fail_unbounded():
            raise AssertionError("unbounded world materialization is forbidden")

        monkeypatch.setattr(runtime.stores, "r3_world_facts", fail_unbounded)
        result = runtime.process("session:bounded-query", "Who owns the book?")
        assert result.verify()
        assert result.cycle.evaluation.decision.status.value == "supported"
    finally:
        runtime.close()


def test_oversized_world_returns_typed_budget_exhaustion_not_false_answer(tmp_path):
    runtime = load_foundation(ROOT, store_path=tmp_path / "large.sqlite3")
    try:
        install_reviewed_world_facts(
            runtime.stores,
            facts=tuple(fact(i, target=f"entity:other:{i}") for i in range(257)),
        )
        before = runtime.stores.revision_pin().world_revision
        result = runtime.process("session:large-world", "Who owns the book?")
        assert result.verify()
        assert result.cycle.evaluation is not None
        assert result.cycle.evaluation.decision.status.value == "budget_exhausted"
        response = result.cycle.response_meaning
        assert response is not None
        assert response.discourse_action != "answer"
        assert "query:world_fact_budget_exceeded" in response.blocker_refs
        assert runtime.stores.revision_pin().world_revision == before
    finally:
        runtime.close()
