"""Reference language output from reviewed role semantics, not canned cases.

The S–V–O English form is deliberately restricted. A result is user-visible
ONLY after the existing read-only parser proves identical canonical meaning.
The R5 generative release gate remains entirely separate.
"""
from pathlib import Path
import pytest

from cemm_authoritative_hybrid.foundation import load_foundation
from cemm_authoritative_hybrid.persistence import Fact
from cemm_authoritative_hybrid.r3_persistence import install_reviewed_world_facts

ROOT = Path(__file__).resolve().parents[1]


def _reviewed_fact(rel: str, subj: str, obj: str) -> Fact:
    return Fact(
        fact_ref=f"fact:output:{rel}:{subj}:{obj}",
        operator="op:relation",
        args={
            "predicate_ref": rel,
            "role:subject": subj,
            "role:object": obj,
        },
        proof={
            "source": "source:independently-reviewed-reference-answer",
            "placement": "observed",
        },
    )


@pytest.mark.parametrize("question,relation,subject,obj,expected", [
    ("Who owns the book?", "rel:owns", "entity:alice", "entity:book",
     "Alice owns the book."),
    ("Who likes Bob?", "rel:likes", "entity:alice", "entity:bob",
     "Alice likes Bob."),
    ("Who owns Alice?", "rel:owns", "entity:bob", "entity:alice",
     "Bob owns Alice."),
])
def test_new_relation_and_entity_combinations_produce_verified_english(
    tmp_path, question, relation, subject, obj, expected,
):
    runtime = load_foundation(ROOT, store_path=tmp_path / "reference")
    try:
        install_reviewed_world_facts(
            runtime.stores,
            facts=(_reviewed_fact(relation, subject, obj),),
        )
        turn = runtime.process("session:reference", question)
        assert turn.verify()
        before = runtime.stores.revision_pin()
        output = runtime.generate_reference_english(turn)
        assert output.status == "verified"
        assert output.reason == "canonical_expression_equal"
        assert output.surface == expected
        assert output.response_meaning_ref == turn.cycle.response_meaning.response_meaning_ref
        assert output.assessment is not None and output.assessment.equivalent
        assert output.assessment.parsed_expression_ref == (
            turn.cycle.response_meaning.response_expression.expression_ref
        )
        assert "source:independently-reviewed-reference-answer" in (
            turn.cycle.response_meaning.source_refs
        )
        assert output.proof_refs == turn.cycle.response_meaning.proof_refs
        assert runtime.stores.revision_pin() == before
    finally:
        runtime.close()


def test_missing_world_proof_cannot_create_english_answer(tmp_path):
    runtime = load_foundation(ROOT, store_path=tmp_path / "unknown")
    try:
        turn = runtime.process("session:unknown", "Who owns the book?")
        assert turn.verify()
        result = runtime.generate_reference_english(turn)
        assert result.status == "unadmitted"
        assert result.surface is None
    finally:
        runtime.close()


def test_stale_response_never_emits_english_sentence(tmp_path):
    runtime = load_foundation(ROOT, store_path=tmp_path / "stale")
    try:
        install_reviewed_world_facts(
            runtime.stores,
            facts=(_reviewed_fact("rel:owns", "entity:alice", "entity:book"),),
        )
        turn = runtime.process("session:old", "Who owns the book?")
        valid = runtime.generate_reference_english(turn)
        assert valid.surface == "Alice owns the book."
        runtime.process("session:new", "hello")
        invalid = runtime.generate_reference_english(turn)
        assert invalid.status == "unadmitted"
        assert invalid.surface is None
        assert invalid.assessment is not None
        assert invalid.assessment.reason == "response_revision_stale"
    finally:
        runtime.close()


def test_unsupported_disjunction_or_multianswer_does_not_escape(tmp_path):
    runtime = load_foundation(ROOT, store_path=tmp_path / "multi")
    try:
        install_reviewed_world_facts(
            runtime.stores,
            facts=(
                _reviewed_fact("rel:owns", "entity:alice", "entity:book"),
                _reviewed_fact("rel:owns", "entity:bob", "entity:book"),
            ),
        )
        turn = runtime.process("session:multi", "Who owns the book?")
        output = runtime.generate_reference_english(turn)
        assert output.status == "unadmitted"
        assert output.surface is None
    finally:
        runtime.close()
