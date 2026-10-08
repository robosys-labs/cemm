"""Real text -> canonical query -> fact binding -> proof -> semantic response.

Trusted facts are installed by the existing persistence owner, *not* by
unreviewed utterances. This is a complete supported-domain query cycle.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cemm_authoritative_hybrid.foundation import load_foundation
from cemm_authoritative_hybrid.persistence import Fact
from cemm_authoritative_hybrid.r3_persistence import install_reviewed_world_facts

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("text,predicate,object_ref", [
    ("Who owns the book?", "rel:owns", "entity:book"),
    ("Who likes Bob?", "rel:likes", "entity:bob"),
])
def test_text_query_returns_exact_matching_subject_and_source_proof(
    tmp_path, text, predicate, object_ref
):
    runtime = load_foundation(
        ROOT, store_path=tmp_path / "evidence-query.sqlite3"
    )
    try:
        reviewed = Fact(
            fact_ref=f"fact:reviewed:{predicate}",
            operator="op:relation",
            args={
                "predicate_ref": predicate,
                "role:subject": "entity:alice",
                "role:object": object_ref,
            },
            proof={
                "source": "source:reviewed-observation",
                "placement": "observed",
            },
        )
        install_reviewed_world_facts(runtime.stores, facts=(reviewed,))
        before = runtime.stores.revision_pin()
        turn = runtime.process("session:evidence-query", text)
        assert turn.verify()
        cycle = turn.cycle
        assert cycle.verification.status == "selected"
        assert cycle.evaluation.decision.status.value == "supported"
        response = cycle.response_meaning
        assert response is not None
        assert response.discourse_action == "answer"
        assert ("?v0", "entity:alice") in response.bindings
        assert "source:reviewed-observation" in response.source_refs
        assert response.proof_refs
        assert runtime.stores.revision_pin().world_revision == before.world_revision
    finally:
        runtime.close()


def test_unrelated_fact_is_not_a_query_answer(tmp_path):
    runtime = load_foundation(
        ROOT, store_path=tmp_path / "unrelated-query.sqlite3"
    )
    try:
        reviewed = Fact(
            fact_ref="fact:unrelated",
            operator="op:relation",
            args={
                "predicate_ref": "rel:owns",
                "role:subject": "entity:alice",
                "role:object": "entity:lamp",
            },
            proof={"source": "source:unrelated", "placement": "observed"},
        )
        install_reviewed_world_facts(runtime.stores, facts=(reviewed,))
        before = runtime.stores.revision_pin().world_revision
        result = runtime.process("session:unrelated-query", "Who owns the book?")
        assert result.verify()
        assert result.cycle.response_meaning is None or (
            result.cycle.response_meaning.discourse_action != "answer"
        )
        assert runtime.stores.revision_pin().world_revision == before
    finally:
        runtime.close()
