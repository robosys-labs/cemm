"""Semantic gold for English relation queries: fronted WH is a missing subject.

This suite inspects the authenticated public runtime's *meaning graph*, not
whether a question happens to produce a fluent or plausible surface.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cemm_authoritative_hybrid.bootstrap import load_runtime
from cemm_authoritative_hybrid.expressions import BoundVariable, GroundedReference

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("utterance,relation,object_ref", [
    ("Who owns a book?", "rel:owns", "entity:book"),
    ("Who likes Bob?", "rel:likes", "entity:bob"),
    ("Who owns Alice?", "rel:owns", "entity:alice"),
])
def test_leading_wh_query_binds_subject_not_object(tmp_path, utterance, relation, object_ref):
    runtime = load_runtime(
        ROOT, profile="development", store_path=tmp_path / "meaning.sqlite3"
    )
    try:
        before = runtime.stores.revision_pin().world_revision
        cycle = runtime.process("session:query-subject", utterance)
        assert cycle.verification.status == "selected", utterance
        meaning = cycle.verification.selected_meaning
        assert meaning is not None
        relations = [
            app for app in meaning.expression.applications
            if app.operator == "op:relation" and app.predicate_ref == relation
        ]
        assert len(relations) == 1, utterance
        roles = {binding.role_ref: binding.filler for binding in relations[0].roles}
        assert isinstance(roles["role:subject"], BoundVariable), (utterance, roles)
        assert roles["role:object"] == GroundedReference(object_ref), (utterance, roles)
        assert runtime.stores.revision_pin().world_revision == before
    finally:
        runtime.stores.close()


def test_statement_role_order_not_reversed_by_query_repair(tmp_path):
    runtime = load_runtime(
        ROOT, profile="development", store_path=tmp_path / "statement.sqlite3"
    )
    try:
        cycle = runtime.process("session:declarative-direction", "Alice owns a book.")
        assert cycle.verification.status == "selected"
        relation = next(
            app for app in cycle.verification.selected_meaning.expression.applications
            if app.operator == "op:relation" and app.predicate_ref == "rel:owns"
        )
        roles = {binding.role_ref: binding.filler for binding in relation.roles}
        assert roles["role:subject"] == GroundedReference("entity:alice")
        assert roles["role:object"] == GroundedReference("entity:book")
    finally:
        runtime.stores.close()
