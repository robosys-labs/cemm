"""Acceptance Suite F — Recursive definition closure (tests 25-28).

### 25. Inverse relation cluster
### 26. Non-monotone blocked
### 27. Activation race
### 28. Joint atomicity
"""
from __future__ import annotations

import pytest

from cemm.kernel.schema.closure import RecursiveComponent
from cemm.kernel.schema.store import SemanticSchemaStore
from cemm.kernel.schema.envelope import SchemaEnvelope
from cemm.kernel.model.identity import Provenance


def make_envelope(
    record_id: str, semantic_key: str, status: str = "candidate",
) -> SchemaEnvelope:
    return SchemaEnvelope(
        record_id=record_id,
        semantic_key=semantic_key,
        schema_kind="predicate",
        status=status,
        provenance=Provenance(source_id="boot", source_kind="boot"),
    )


# ── Test 25: Inverse relation cluster ──


def test_25a_inverse_cluster_can_activate():
    """Inverse relation cluster with all requirements can activate jointly."""
    component = RecursiveComponent(
        component_id="rc_inverse",
        member_refs=("schema:parent:v1", "schema:child:v1"),
        classification="inverse_relation",
        has_external_anchor=True,
        has_non_redundant_contribution=True,
        has_type_consistent_mapping=True,
        has_declared_semantics=True,
        has_forbidden_dependency=False,
    )
    assert component.can_activate_jointly


def test_25b_positive_monotone_can_activate():
    """Positive monotone recursive cluster can activate jointly."""
    component = RecursiveComponent(
        component_id="rc_mono",
        member_refs=("schema:ancestor:v1", "schema:descendant:v1"),
        classification="positive_monotone",
        has_external_anchor=True,
        has_non_redundant_contribution=True,
        has_type_consistent_mapping=True,
        has_declared_semantics=True,
        has_forbidden_dependency=False,
    )
    assert component.can_activate_jointly


def test_25c_missing_anchor_blocks():
    """Missing external anchor blocks joint activation."""
    component = RecursiveComponent(
        component_id="rc_no_anchor",
        member_refs=("schema:parent:v1", "schema:child:v1"),
        classification="inverse_relation",
        has_external_anchor=False,
        has_non_redundant_contribution=True,
        has_type_consistent_mapping=True,
        has_declared_semantics=True,
    )
    assert not component.can_activate_jointly


# ── Test 26: Non-monotone blocked ──


def test_26a_non_monotone_blocked():
    """Non-monotone recursive cluster cannot activate jointly."""
    component = RecursiveComponent(
        component_id="rc_neg",
        member_refs=("schema:a:v1", "schema:b:v1"),
        classification="unsupported_non_monotone",
        has_external_anchor=True,
        has_non_redundant_contribution=True,
        has_type_consistent_mapping=True,
        has_declared_semantics=True,
    )
    assert not component.can_activate_jointly


def test_26b_forbidden_dependency_blocks():
    """Forbidden dependency blocks joint activation even for inverse."""
    component = RecursiveComponent(
        component_id="rc_forbidden",
        member_refs=("schema:a:v1", "schema:b:v1"),
        classification="inverse_relation",
        has_external_anchor=True,
        has_non_redundant_contribution=True,
        has_type_consistent_mapping=True,
        has_declared_semantics=True,
        has_forbidden_dependency=True,
    )
    assert not component.can_activate_jointly


def test_26c_stratified_defeasible_blocked():
    """Stratified defeasible cluster cannot activate jointly."""
    component = RecursiveComponent(
        component_id="rc_stratified",
        member_refs=("schema:a:v1", "schema:b:v1"),
        classification="stratified_defeasible",
        has_external_anchor=True,
        has_non_redundant_contribution=True,
        has_type_consistent_mapping=True,
        has_declared_semantics=True,
    )
    assert not component.can_activate_jointly


# ── Test 27: Activation race ──


def test_27a_compare_and_swap_prevents_race():
    """Compare-and-swap prevents activation race conditions."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:test:v1", "test", status="candidate")
    store.register(env)

    # First activation with correct revision succeeds
    rev = store.get_revision("schema:test:v1")
    result1 = store.transition_to_provisional("schema:test:v1", expected_revision=rev)
    assert result1.status.value == "success"

    # Second activation with stale revision fails
    result2 = store.transition_to_provisional("schema:test:v1", expected_revision=rev)
    assert result2.status.value != "success"


def test_27b_concurrent_activation_rejected():
    """Concurrent activation with wrong revision is rejected."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:test:v1", "test", status="candidate")
    store.register(env)

    # Wrong revision → blocked
    result = store.transition_to_provisional("schema:test:v1", expected_revision=999)
    assert result.status.value == "cas_failed"


# ── Test 28: Joint atomicity ──


def test_28a_joint_activation_atomic():
    """Joint activation is atomic — all or nothing."""
    store = SemanticSchemaStore()
    s1 = make_envelope("schema:parent:v1", "parent", status="candidate")
    s2 = make_envelope("schema:child:v1", "child", status="candidate")
    store.register(s1)
    store.register(s2)

    # Stamp assessment refs before cluster activation
    store.stamp_assessment_refs("schema:parent:v1", "assessment:parent")
    store.stamp_assessment_refs("schema:child:v1", "assessment:child")

    rev1 = store.get_revision("schema:parent:v1")
    rev2 = store.get_revision("schema:child:v1")

    # Joint activation with correct revisions
    result = store.activate_cluster(
        ("schema:parent:v1", "schema:child:v1"),
        {"schema:parent:v1": rev1, "schema:child:v1": rev2},
    )
    assert result.status.value == "success"
    assert store.get("schema:parent:v1").status == "active"
    assert store.get("schema:child:v1").status == "active"


def test_28b_joint_activation_fails_if_one_stale():
    """Joint activation fails if one member has stale revision."""
    store = SemanticSchemaStore()
    s1 = make_envelope("schema:parent:v1", "parent", status="candidate")
    s2 = make_envelope("schema:child:v1", "child", status="candidate")
    store.register(s1)
    store.register(s2)

    rev1 = store.get_revision("schema:parent:v1")

    # Stale revision for s2
    store.stamp_assessment_refs("schema:parent:v1", "assessment:parent2")
    store.stamp_assessment_refs("schema:child:v1", "assessment:child2")

    result = store.activate_cluster(
        ("schema:parent:v1", "schema:child:v1"),
        {"schema:parent:v1": rev1, "schema:child:v1": 999},
    )
    # Should fail — atomic
    assert result.status.value != "success"
    # Neither should be activated
    assert store.get("schema:parent:v1").status != "active"
    assert store.get("schema:child:v1").status != "active"
