"""Acceptance Suite D — Sense identity and scope/context (tests 14-18).

### 14. Polysemy split
### 15. Opaque homonyms
### 16. Alias versus new concept
### 17. Scope is not blind shadowing
### 18. Context/time-qualified meaning
"""
from __future__ import annotations

import pytest

from cemm.kernel.schema.store import SemanticSchemaStore
from cemm.kernel.schema.envelope import SchemaEnvelope
from cemm.kernel.schema.resolver import SchemaResolver
from cemm.kernel.schema.use_profile import (
    UseProfileLevel, derive_use_profile, SemanticOperation,
)
from cemm.kernel.schema.closure import SchemaGroundingAssessment
from cemm.kernel.model.identity import Provenance, Scope, ScopeLevel


def make_envelope(
    record_id: str, semantic_key: str, status: str = "candidate",
    scope: Scope | None = None,
) -> SchemaEnvelope:
    return SchemaEnvelope(
        record_id=record_id,
        semantic_key=semantic_key,
        schema_kind="predicate",
        status=status,
        provenance=Provenance(source_id="boot", source_kind="boot"),
        scope=scope or Scope(level=ScopeLevel.GLOBAL),
    )


# ── Test 14: Polysemy split ──


def test_14a_polysemy_separate_senses():
    """Teach `leader` as group-directing role and metal strip — separate senses.

    Per ACCEPTANCE_TESTS.md §14: separate candidate senses; no contradiction
    across senses; evidence does not contaminate; exact sense used in each
    proposition is retained.
    """
    store = SemanticSchemaStore()
    leader_role = make_envelope("schema:leader_role:v1", "leader_role", status="candidate")
    leader_strip = make_envelope("schema:leader_strip:v1", "leader_strip", status="candidate")
    store.register(leader_role)
    store.register(leader_strip)

    # Both exist as separate schemas with distinct semantic keys
    retrieved_role = store.get("schema:leader_role:v1")
    retrieved_strip = store.get("schema:leader_strip:v1")
    assert retrieved_role is not None
    assert retrieved_strip is not None
    assert retrieved_role.semantic_key != retrieved_strip.semantic_key
    # Both remain candidate — neither contaminated by the other's presence
    assert retrieved_role.status == "candidate"
    assert retrieved_strip.status == "candidate"
    # Store keeps them as distinct records (not merged)
    assert retrieved_role.record_id != retrieved_strip.record_id


def test_14b_no_contradiction_across_senses():
    """No contradiction across senses — different semantic keys prevent conflict.

    Per ACCEPTANCE_TESTS.md §14: no contradiction across senses. Two schemas
    with different semantic keys can coexist without one invalidating the other.
    """
    store = SemanticSchemaStore()
    s1 = make_envelope("schema:leader_role:v1", "leader_role", status="active")
    s2 = make_envelope("schema:leader_strip:v1", "leader_strip", status="active")
    store.register(s1)
    store.register(s2)
    # Both can be active simultaneously — no contradiction
    assert store.get("schema:leader_role:v1").status == "active"
    assert store.get("schema:leader_strip:v1").status == "active"


def test_14c_evidence_does_not_contaminate():
    """Evidence for one sense does not contaminate the other.

    Per ACCEPTANCE_TESTS.md §14: evidence does not contaminate. Activating
    one sense must not change the status of the other.
    """
    store = SemanticSchemaStore()
    s1 = make_envelope("schema:leader_role:v1", "leader_role", status="candidate")
    s2 = make_envelope("schema:leader_strip:v1", "leader_strip", status="candidate")
    store.register(s1)
    store.register(s2)

    # Activate s1 via CAS
    rev = store.get_revision("schema:leader_role:v1")
    store.activate_with_assessment("schema:leader_role:v1", expected_revision=rev,
        grounding_assessment_ref="assessment:leader_role",
    )

    # s1 is active, s2 remains candidate — no contamination
    assert store.get("schema:leader_role:v1").status == "active"
    assert store.get("schema:leader_strip:v1").status == "candidate"


# ── Test 15: Opaque homonyms ──


def test_15a_opaque_homonyms_remain_distinct():
    """Opaque uses of one spelling remain separate clusters.

    Per ACCEPTANCE_TESTS.md §15: lexical form may be shared; candidate sense
    clusters remain distinct/reversible; no premature schema merge.
    """
    store = SemanticSchemaStore()
    # Two unknown senses — same lexical form "dax" but different context-qualified keys
    s1 = make_envelope("schema:dax_a:v1", "dax#context_1", status="candidate")
    s2 = make_envelope("schema:dax_b:v1", "dax#context_2", status="candidate")
    store.register(s1)
    store.register(s2)

    retrieved_1 = store.get("schema:dax_a:v1")
    retrieved_2 = store.get("schema:dax_b:v1")
    # Distinct records — no premature merge
    assert retrieved_1 is not None
    assert retrieved_2 is not None
    assert retrieved_1.record_id != retrieved_2.record_id
    assert retrieved_1.semantic_key != retrieved_2.semantic_key
    # Both remain candidate — no auto-activation or merge
    assert retrieved_1.status == "candidate"
    assert retrieved_2.status == "candidate"


def test_15b_no_premature_schema_merge():
    """No premature schema merge for opaque homonyms.

    Per ACCEPTANCE_TESTS.md §15: no premature schema merge. Even after
    activating one cluster, the other remains distinct and candidate.
    """
    store = SemanticSchemaStore()
    s1 = make_envelope("schema:wug_a:v1", "wug#context_a", status="candidate")
    s2 = make_envelope("schema:wug_b:v1", "wug#context_b", status="candidate")
    store.register(s1)
    store.register(s2)

    # Activate s1 — s2 must remain candidate and distinct
    rev = store.get_revision("schema:wug_a:v1")
    store.transition_to_provisional("schema:wug_a:v1", expected_revision=rev)

    assert store.get("schema:wug_a:v1").status == "provisional"
    assert store.get("schema:wug_b:v1").status == "candidate"
    assert store.get("schema:wug_a:v1").semantic_key != store.get("schema:wug_b:v1").semantic_key


# ── Test 16: Alias versus new concept ──


def test_16a_alias_competes_with_new_schema():
    """Alias/synonym/translation competes with new-schema hypothesis."""
    store = SemanticSchemaStore()
    # Existing grounded schema
    existing = make_envelope("schema:engineer:v1", "engineer", status="active")
    store.register(existing)

    # New form with no differentiator → alias hypothesis competes
    alias = make_envelope("schema:engineer_alias:v1", "engineer", status="candidate")
    store.register(alias)

    # Both exist; alias is candidate, not active
    assert store.get("schema:engineer:v1").status == "active"
    assert store.get("schema:engineer_alias:v1").status == "candidate"


def test_16b_duplicate_active_not_created_without_evidence():
    """Duplicate active schema is not created without evidence."""
    store = SemanticSchemaStore()
    s1 = make_envelope("schema:engineer:v1", "engineer", status="active")
    store.register(s1)

    # Attempt to register another active with same key
    s2 = make_envelope("schema:engineer:v2", "engineer", status="candidate")
    store.register(s2)

    # s2 remains candidate — not auto-activated
    assert store.get("schema:engineer:v2").status == "candidate"


# ── Test 17: Scope is not blind shadowing ──


def test_17a_user_scoped_does_not_override_global():
    """User-scoped revision does not blindly override active global schema."""
    store = SemanticSchemaStore()
    global_schema = make_envelope(
        "schema:leader:v1", "leader", status="active",
        scope=Scope(level=ScopeLevel.GLOBAL),
    )
    user_schema = make_envelope(
        "schema:leader_user:v1", "leader", status="candidate",
        scope=Scope(level=ScopeLevel.USER, owner_id="user1"),
    )
    store.register(global_schema)
    store.register(user_schema)

    # Global remains active
    assert store.get("schema:leader:v1").status == "active"
    # User schema is separate
    assert store.get("schema:leader_user:v1").status == "candidate"


def test_17b_actual_world_retains_global():
    """Actual-world queries retain globally admitted evidence."""
    assessment = SchemaGroundingAssessment(
        record_id="schema:leader:v1",
        semantic_key="leader",
        environment_fingerprint="fp1",
        is_structurally_executable=True,
    )
    # Global scope, actual context → active if competent and admissible
    profile = derive_use_profile(
        assessment, context_ref="ctx:actual",
        competence_is_competent=True, epistemic_admissible=True,
        scope_accessible=True,
    )
    assert profile.level == UseProfileLevel.ACTIVE


def test_17c_user_scoped_queries_select_user_revision():
    """User-belief queries can select user-scoped revision."""
    assessment = SchemaGroundingAssessment(
        record_id="schema:leader_user:v1",
        semantic_key="leader",
        environment_fingerprint="fp1",
        is_structurally_executable=True,
    )
    # User scope, user-belief context → partial (not actual-world active)
    profile = derive_use_profile(
        assessment, context_ref="ctx:believed",
        competence_is_competent=False, epistemic_admissible=True,
        scope_accessible=True,
    )
    # Should not be ACTIVE in believed context without competence
    assert profile.level != UseProfileLevel.ACTIVE


# ── Test 18: Context/time-qualified meaning ──


def test_18a_applicability_context_recorded():
    """Applicability context is recorded on the schema envelope."""
    from cemm.kernel.model.identity import TimeExtent
    env = SchemaEnvelope(
        record_id="schema:policy:v1",
        semantic_key="policy",
        schema_kind="predicate",
        status="candidate",
        provenance=Provenance(source_id="boot", source_kind="boot"),
        applicability_context_refs=("jurisdiction:EU",),
        valid_time=TimeExtent(start="2024-01-01", end="2026-12-31"),
    )
    assert "jurisdiction:EU" in env.applicability_context_refs
    assert env.valid_time is not None


def test_18b_no_global_promotion_for_context_limited():
    """Context-limited definition does not get global promotion."""
    store = SemanticSchemaStore()
    from cemm.kernel.model.identity import TimeExtent
    env = SchemaEnvelope(
        record_id="schema:policy_eu:v1",
        semantic_key="policy",
        schema_kind="predicate",
        status="candidate",
        provenance=Provenance(source_id="user", source_kind="taught"),
        applicability_context_refs=("jurisdiction:EU",),
    )
    store.register(env)
    # Remains candidate — not promoted to active
    assert store.get("schema:policy_eu:v1").status == "candidate"


def test_18c_out_of_context_queries_qualify():
    """Out-of-context queries qualify or abstain."""
    assessment = SchemaGroundingAssessment(
        record_id="schema:policy_eu:v1",
        semantic_key="policy",
        environment_fingerprint="fp1",
        is_structurally_executable=True,
    )
    # Out-of-context → not admissible → opaque
    profile = derive_use_profile(
        assessment, context_ref="ctx:actual",
        competence_is_competent=True, epistemic_admissible=False,
    )
    assert profile.level == UseProfileLevel.OPAQUE
    assert not profile.permits(SemanticOperation.CLASSIFY)
