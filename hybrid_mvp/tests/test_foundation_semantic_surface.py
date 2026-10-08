"""End-to-end public-path tests for the lossless semantic foundation.

These intentionally run the real ORIENT/PROPOSE/VERIFY/EVALUATE/EFFECT path,
rather than injecting fixture owner results.  The final surface is canonical
structured semantics; normal-language realization remains separately gated.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.foundation import (
    FoundationTurn,
    load_foundation,
    SCHEMA,
)
from cemm_authoritative_hybrid.expressions import (
    GroundedReference, RoleBinding, ScopeOperator,
    SemanticApplication, SemanticExpression,
)

ROOT = Path(__file__).parents[1]


def _runtime(tmp_path):
    return load_foundation(ROOT, store_path=tmp_path / "foundation.sqlite3")


def test_complete_public_greeting_has_verified_semantic_response(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        result = runtime.process("session:foundation-greeting", "hello")
        assert result.verify()
        document = json.loads(result.semantic_surface)
        assert document["schema"] == SCHEMA
        assert document["kind"] == "response_meaning"
        assert document["response_meaning"]["response_meaning_ref"]
        assert document["response_meaning"]["response_expression"]["applications"]
        assert document["response_meaning"]["proof_refs"] is not None
        assert document["effect_receipt_ref"] == result.cycle.effect_receipt.receipt_ref
        assert result.cycle.response_meaning.revision_pin == result.cycle.final_revision_pin
        assert result.cycle.realization_receipt is None  # linguistic R5 remains red
    finally:
        runtime.close()


def test_unknown_public_input_cannot_become_a_fabricated_answer(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        before = runtime.stores.revision_pin().world_revision
        turn = runtime.process("session:foundation-unknown", "zorbulate")
        assert turn.verify()
        document = json.loads(turn.semantic_surface)
        assert document["kind"] == "unresolved_frontier"
        assert document["gap_receipt"] is not None
        assert runtime.stores.revision_pin().world_revision == before
    finally:
        runtime.close()


def test_semantic_surface_tampering_is_not_verified(tmp_path):
    runtime = _runtime(tmp_path)
    try:
        result = runtime.process("session:foundation-tamper", "hello")
        document = json.loads(result.semantic_surface)
        document["status"] = "fabricated"
        altered = FoundationTurn(
            result.cycle, json.dumps(document, sort_keys=True), result.surface_ref
        )
        with pytest.raises(ValueError, match="surface differs"):
            altered.verify()
    finally:
        runtime.close()


def _relation(subject: str, obj: str) -> SemanticExpression:
    app = SemanticApplication(
        "application:fixture", "op:relation", "rel:owns",
        (
            RoleBinding("role:subject", GroundedReference(subject)),
            RoleBinding("role:object", GroundedReference(obj)),
        ),
    )
    return SemanticExpression.create(
        applications=(app,), root_refs=(app.application_ref,),
    )


def test_semantic_identity_preserves_role_direction():
    assert (
        _relation("entity:ada", "entity:car").expression_ref
        != _relation("entity:car", "entity:ada").expression_ref
    )


def test_semantic_identity_preserves_negation_and_attribution():
    positive = _relation("entity:ada", "entity:car")
    root = positive.applications[0].application_ref

    def scoped(kind: str, value: str):
        return SemanticExpression.create(
            applications=positive.applications,
            root_refs=("scope:one",),
            scope_operators=(ScopeOperator("scope:one", kind, value, root),),
        )

    negative = scoped("scope:polarity", "scope_value:polarity:negative")
    reported_by_mary = scoped("scope:attribution", "participant:mary")
    reported_by_john = scoped("scope:attribution", "participant:john")
    assert len({
        positive.expression_ref,
        negative.expression_ref,
        reported_by_mary.expression_ref,
        reported_by_john.expression_ref,
    }) == 4
