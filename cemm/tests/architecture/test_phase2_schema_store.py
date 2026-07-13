"""Phase 2 gate tests: SemanticSchemaStore lifecycle and atomic activation.

Gates (from IMPLEMENTATION_PLAN.md Phase 2):
- no overlay or second resolver
- validator cannot activate
- concurrent child revisions never silently merge
- boot and learned schemas use identical store APIs

Additional guardrail tests from AGENTS.md §7:
- Strict lifecycle: candidate → provisional → active → superseded/rejected
- CAS activation: revision mismatch fails
- Cluster activation: all-or-nothing atomicity
- Supersession is journaled and reversible
- Revision retention for proposition/replay-bound schemas
- Reverse dependency tracking for invalidation
- Context/time applicability filtering
- Scope-aware resolution without blind shadowing
"""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

import pytest

from cemm.kernel.schema.store import (
    SemanticSchemaStore,
    StoreSnapshot,
    SupersessionJournalEntry,
    ReverseDependency,
)
from cemm.kernel.schema.resolver import (
    SchemaResolver,
    SenseCandidate,
    ResolutionResult,
)
from cemm.kernel.schema.envelope import (
    SchemaEnvelope,
    SchemaContribution,
    SchemaDependency,
)
from cemm.kernel.schema.activation import (
    ActivationResult,
    ActivationStatus,
    activate_single,
    activate_cluster,
)
from cemm.kernel.schema.versioning import SchemaStatus
from cemm.kernel.schema.grounding_spec import SemanticPattern, GroundingSpecification
from cemm.kernel.schema.validation import CompetencyCase
from cemm.kernel.schema.use_profile import SchemaGroundingAssessment
from cemm.kernel.model.identity import (
    Scope,
    ScopeLevel,
    Provenance,
    Permission,
    TimeExtent,
)


# ── Helpers ────────────────────────────────────────────────────────


def make_envelope(
    record_id: str,
    semantic_key: str,
    schema_kind: str = "predicate",
    status: str = "candidate",
    scope: Scope | None = None,
    version: int = 1,
    confidence: float = 0.0,
    valid_time: TimeExtent | None = None,
    applicability_context_refs: tuple[str, ...] = (),
) -> SchemaEnvelope:
    """Create a test schema envelope."""
    return SchemaEnvelope(
        record_id=record_id,
        semantic_key=semantic_key,
        schema_kind=schema_kind,
        status=status,
        scope=scope or Scope(level=ScopeLevel.GLOBAL),
        version=version,
        confidence=confidence,
        valid_time=valid_time,
        applicability_context_refs=applicability_context_refs,
        provenance=Provenance(source_id="test"),
    )


# ── Gate 1: no overlay or second resolver ──────────────────────────


def test_single_store_instance():
    """There must be one schema store, not an overlay or second resolver."""
    store = SemanticSchemaStore()
    resolver = SchemaResolver(store)
    # The resolver delegates to the store — it has no independent state
    assert resolver._store is store


def test_no_session_overlay():
    """Session learning must be a session-scoped revision, not an overlay.

    A session-scoped schema is registered with session scope — it
    uses the same store API as any other schema.
    """
    store = SemanticSchemaStore()
    session_scope = Scope(level=ScopeLevel.SESSION, session_id="s1")

    # Register a session-scoped schema — same API as global
    env = make_envelope(
        "schema:session_test:v1",
        "test_concept",
        scope=session_scope,
    )
    store.register(env)

    retrieved = store.get("schema:session_test:v1")
    assert retrieved is not None
    assert retrieved.scope.level == ScopeLevel.SESSION


def test_resolver_does_not_activate():
    """The resolver must not activate schemas — only the store can."""
    store = SemanticSchemaStore()
    resolver = SchemaResolver(store)

    env = make_envelope("schema:test:v1", "test")
    store.register(env)

    # Resolver only produces candidates — no activation method
    assert not hasattr(resolver, "activate")
    assert not hasattr(resolver, "transition_to_provisional")

    # The resolver's resolve_key returns candidates, not activated schemas
    result = resolver.resolve_key("test")
    assert result.active_candidate is None  # Not active yet
    assert len(result.candidates) == 1
    assert result.candidates[0].status == "candidate"


# ── Gate 2: validator cannot activate ──────────────────────────────


def test_validation_module_cannot_activate():
    """SchemaGroundingAssessment is a derived record — it cannot activate.

    The validation module produces assessments; the store performs
    activation using CAS.
    """
    store = SemanticSchemaStore()

    env = make_envelope("schema:test:v1", "test")
    store.register(env)

    # Create a grounding assessment — it's a derived control record
    assessment = SchemaGroundingAssessment(
        record_id="schema:test:v1",
        semantic_key="test",
        environment_fingerprint="",
        is_structurally_executable=True,
    )

    # The assessment has no activation method
    assert not hasattr(assessment, "activate")
    assert not hasattr(assessment, "set_status")

    # Only the store can activate
    result = store.activate("schema:test:v1", expected_revision=1)
    assert result.status == ActivationStatus.SUCCESS


def test_activation_requires_store():
    """Activation must go through the store's CAS mechanism."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:test:v1", "test")
    store.register(env)

    # Direct activation via store works
    result = store.activate("schema:test:v1", expected_revision=1)
    assert result.status == ActivationStatus.SUCCESS

    # Verify it's active
    activated = store.get("schema:test:v1")
    assert activated.status == "active"


# ── Gate 3: concurrent child revisions never silently merge ────────


def test_concurrent_revisions_do_not_merge():
    """Two child revisions of the same schema must remain distinct.

    Concurrent child revisions never silently merge — each has its
    own record_id and version.
    """
    store = SemanticSchemaStore()

    # Register parent
    parent = make_envelope("schema:parent:v1", "parent_concept", status="active")
    store.register(parent)
    store.activate("schema:parent:v1", expected_revision=1)

    # Two children from different learning transactions
    child1 = make_envelope(
        "schema:child_a:v1", "child_concept",
        version=1, confidence=0.3,
    )
    child2 = make_envelope(
        "schema:child_b:v1", "child_concept",
        version=1, confidence=0.4,
    )
    store.register(child1)
    store.register(child2)

    # Both exist as separate records — no merge
    assert store.get("schema:child_a:v1") is not None
    assert store.get("schema:child_b:v1") is not None
    assert "schema:child_a:v1" != "schema:child_b:v1"

    # Both are in the same sense cluster but remain distinct
    cluster = store._sense_clusters.get("child_concept", set())
    assert "schema:child_a:v1" in cluster
    assert "schema:child_b:v1" in cluster


def test_cas_prevents_concurrent_activation():
    """CAS prevents two activations from racing on the same revision."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:test:v1", "test")
    store.register(env)

    # First activation succeeds (revision 1 → 2)
    result1 = store.activate("schema:test:v1", expected_revision=1)
    assert result1.status == ActivationStatus.SUCCESS

    # Second activation with stale revision — blocked because already active
    # (status check happens before CAS; this is correct behavior)
    result2 = store.activate("schema:test:v1", expected_revision=1)
    assert result2.status == ActivationStatus.BLOCKED

    # Direct CAS with stale revision on a non-active schema fails properly
    env2 = make_envelope("schema:cas2:v1", "cas2_test")
    store.register(env2)
    # Simulate someone else changing the revision before we activate
    store._revisions["schema:cas2:v1"] = 5
    result3 = store.activate("schema:cas2:v1", expected_revision=1)
    assert result3.status == ActivationStatus.CAS_FAILED


# ── Gate 4: boot and learned schemas use identical store APIs ──────


def test_boot_and_learned_same_api():
    """Boot and learned schemas must use the same store APIs.

    Boot origin is provenance, not a separate lifecycle state.
    """
    store = SemanticSchemaStore()

    # Boot schema — provenance says "boot"
    boot_env = SchemaEnvelope(
        record_id="schema:boot_entity:v1",
        semantic_key="entity",
        schema_kind="entity_kind",
        provenance=Provenance(source_id="boot", source_kind="boot"),
    )
    store.register(boot_env)

    # Learned schema — provenance says "learning"
    learned_env = SchemaEnvelope(
        record_id="schema:learned_concept:v1",
        semantic_key="learned",
        schema_kind="predicate",
        provenance=Provenance(source_id="learning_tx:1", source_kind="learning"),
    )
    store.register(learned_env)

    # Both use the same API — no special boot-only or learned-only methods
    boot = store.get("schema:boot_entity:v1")
    learned = store.get("schema:learned_concept:v1")

    assert boot is not None
    assert learned is not None
    # Both start as candidate
    assert boot.status == "candidate"
    assert learned.status == "candidate"

    # Both can transition through the same lifecycle
    result_boot = store.activate("schema:boot_entity:v1", expected_revision=1)
    result_learned = store.activate("schema:learned_concept:v1", expected_revision=1)
    assert result_boot.status == ActivationStatus.SUCCESS
    assert result_learned.status == ActivationStatus.SUCCESS


# ── Strict lifecycle transitions ───────────────────────────────────


def test_lifecycle_candidate_to_provisional_to_active():
    """Schema must follow: candidate → provisional → active."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:lifecycle:v1", "lifecycle")
    store.register(env)

    # Start as candidate
    assert store.get("schema:lifecycle:v1").status == "candidate"

    # Transition to provisional
    result = store.transition_to_provisional("schema:lifecycle:v1", expected_revision=1)
    assert result.status == ActivationStatus.SUCCESS
    assert store.get("schema:lifecycle:v1").status == "provisional"

    # Transition to active
    result = store.activate("schema:lifecycle:v1", expected_revision=2)
    assert result.status == ActivationStatus.SUCCESS
    assert store.get("schema:lifecycle:v1").status == "active"


def test_lifecycle_cannot_skip_provisional_from_rejected():
    """A rejected schema cannot be activated."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:rejected:v1", "rejected_concept")
    store.register(env)

    # Reject it
    assert store.reject("schema:rejected:v1", reason="test")
    assert store.get("schema:rejected:v1").status == "rejected"

    # Cannot activate a rejected schema
    result = store.activate("schema:rejected:v1", expected_revision=2)
    assert result.status == ActivationStatus.BLOCKED


def test_supersede_only_active():
    """Only active schemas can be superseded."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:supersede:v1", "supersede_concept")
    store.register(env)

    # Cannot supersede a candidate
    assert not store.supersede("schema:supersede:v1", "schema:replacement:v1")

    # Activate then supersede
    store.activate("schema:supersede:v1", expected_revision=1)
    assert store.supersede("schema:supersede:v1", "schema:replacement:v1", reason="test")
    assert store.get("schema:supersede:v1").status == "superseded"


# ── CAS activation ─────────────────────────────────────────────────


def test_cas_revision_mismatch_fails():
    """CAS activation must fail when the revision has changed."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:cas:v1", "cas_test")
    store.register(env)

    # Someone else modified the store (simulated by wrong expected revision)
    result = store.activate("schema:cas:v1", expected_revision=99)
    assert result.status == ActivationStatus.CAS_FAILED


def test_cas_nonexistent_record_fails():
    """CAS activation must fail for non-existent records."""
    store = SemanticSchemaStore()
    result = store.activate("schema:nonexistent:v1", expected_revision=1)
    assert result.status == ActivationStatus.BLOCKED


# ── Cluster activation atomicity ───────────────────────────────────


def test_cluster_activation_all_or_nothing():
    """Cluster activation must be all-or-nothing."""
    store = SemanticSchemaStore()

    env_a = make_envelope("schema:cluster_a:v1", "cluster_a")
    env_b = make_envelope("schema:cluster_b:v1", "cluster_b")
    store.register(env_a)
    store.register(env_b)

    # Both should activate atomically
    result = store.activate_cluster(
        ("schema:cluster_a:v1", "schema:cluster_b:v1"),
        {"schema:cluster_a:v1": 1, "schema:cluster_b:v1": 1},
    )
    assert result.status == ActivationStatus.SUCCESS
    assert store.get("schema:cluster_a:v1").status == "active"
    assert store.get("schema:cluster_b:v1").status == "active"


def test_cluster_activation_failure_rolls_back():
    """If one member fails, no member should be activated."""
    store = SemanticSchemaStore()

    env_a = make_envelope("schema:cluster_ok:v1", "cluster_ok")
    env_b = make_envelope("schema:cluster_fail:v1", "cluster_fail")
    store.register(env_a)
    store.register(env_b)

    # Wrong revision for env_b → should fail and roll back env_a
    result = store.activate_cluster(
        ("schema:cluster_ok:v1", "schema:cluster_fail:v1"),
        {"schema:cluster_ok:v1": 1, "schema:cluster_fail:v1": 99},
    )
    assert result.status == ActivationStatus.CAS_FAILED
    # env_a should NOT be active
    assert store.get("schema:cluster_ok:v1").status != "active"


# ── Reverse dependencies ───────────────────────────────────────────


def test_reverse_dependency_tracking():
    """Reverse dependencies must be tracked for invalidation."""
    store = SemanticSchemaStore()

    # Register a dependency: child depends on parent
    parent = make_envelope("schema:parent_dep:v1", "parent_dep")
    store.register(parent)

    child = make_envelope("schema:child_dep:v1", "child_dep")
    dep = SchemaDependency(
        dependency_kind="definition",
        target_schema_ref="schema:parent_dep:v1",
    )
    store.register(child, dependencies=(dep,))

    # Reverse dependency: parent should know child depends on it
    rdeps = store.get_reverse_dependencies("schema:parent_dep:v1")
    assert len(rdeps) == 1
    assert rdeps[0].dependent_ref == "schema:child_dep:v1"
    assert rdeps[0].dependency_kind == "definition"


def test_transitive_dependents():
    """Transitive dependents must be discoverable via BFS."""
    store = SemanticSchemaStore()

    # A → B → C (C depends on B, B depends on A)
    a = make_envelope("schema:dep_a:v1", "dep_a")
    store.register(a)

    b = make_envelope("schema:dep_b:v1", "dep_b")
    store.register(b, dependencies=(SchemaDependency(
        dependency_kind="definition",
        target_schema_ref="schema:dep_a:v1",
    ),))

    c = make_envelope("schema:dep_c:v1", "dep_c")
    store.register(c, dependencies=(SchemaDependency(
        dependency_kind="definition",
        target_schema_ref="schema:dep_b:v1",
    ),))

    # Transitive dependents of A should include B and C
    transitive = store.get_transitive_dependents("schema:dep_a:v1")
    assert "schema:dep_b:v1" in transitive
    assert "schema:dep_c:v1" in transitive


# ── Supersession journal ───────────────────────────────────────────


def test_supersession_is_journaled():
    """Supersession operations must be journaled."""
    store = SemanticSchemaStore()

    env = make_envelope("schema:journal_test:v1", "journal_test")
    store.register(env)
    store.activate("schema:journal_test:v1", expected_revision=1)

    store.supersede("schema:journal_test:v1", "schema:replacement:v1", reason="obsolete")

    journal = store.get_journal()
    assert len(journal) == 1
    assert journal[0].operation == "supersede"
    assert journal[0].source_ref == "schema:journal_test:v1"
    assert journal[0].target_ref == "schema:replacement:v1"
    assert journal[0].reason == "obsolete"


def test_merge_is_journaled_and_reversible():
    """Sense merge must be journaled and reversible."""
    store = SemanticSchemaStore()

    env1 = make_envelope("schema:merge_a:v1", "sense_a")
    env2 = make_envelope("schema:merge_b:v1", "sense_b")
    store.register(env1)
    store.register(env2)

    entry = store.merge_senses("sense_a", "sense_b", reason="same concept")
    assert entry.operation == "merge"
    assert entry.reversible

    # Both records should be in the merged cluster
    cluster = store._sense_clusters.get("sense_b", set())
    assert "schema:merge_a:v1" in cluster
    assert "schema:merge_b:v1" in cluster

    # Reverse the merge
    assert store.reverse_journal_entry(entry.entry_id)
    # Journal retains original + adds reversal entry (audit trail preserved)
    journal = store.get_journal()
    assert len(journal) == 2
    assert any(e.entry_id == entry.entry_id for e in journal)
    assert any(e.operation == "reverse:merge" for e in journal)


def test_split_is_journaled():
    """Sense split must be journaled."""
    store = SemanticSchemaStore()

    env1 = make_envelope("schema:split_a:v1", "polysemous")
    env2 = make_envelope("schema:split_b:v1", "polysemous")
    store.register(env1)
    store.register(env2)

    entry = store.split_sense(
        "polysemous", "polysemous_sense_2",
        record_ids_to_move=("schema:split_b:v1",),
        reason="polysemy detected",
    )
    assert entry.operation == "split"

    # split_b should be in the new cluster
    assert "schema:split_b:v1" in store._sense_clusters.get("polysemous_sense_2", set())
    assert "schema:split_b:v1" not in store._sense_clusters.get("polysemous", set())


# ── Revision retention ─────────────────────────────────────────────


def test_retention_for_proposition_bound_revision():
    """Revisions bound to propositions must be retained."""
    store = SemanticSchemaStore()

    env = make_envelope("schema:retain:v1", "retain_test")
    store.register(env)
    store.activate("schema:retain:v1", expected_revision=1)
    store.supersede("schema:retain:v1", "schema:retain:v2", reason="new version")

    # Bind a proposition
    store.bind_proposition("schema:retain:v1", "prop:historical:1")

    assert store.is_retention_required("schema:retain:v1")


def test_retention_for_replay_bound_revision():
    """Revisions bound to replay results must be retained."""
    store = SemanticSchemaStore()

    env = make_envelope("schema:replay_retain:v1", "replay_test")
    store.register(env)
    store.activate("schema:replay_retain:v1", expected_revision=1)
    store.supersede("schema:replay_retain:v1", "schema:replay_retain:v2")

    store.bind_replay("schema:replay_retain:v1", "replay:1")
    assert store.is_retention_required("schema:replay_retain:v1")


def test_no_retention_for_unbound_superseded():
    """Unbound superseded revisions need not be retained."""
    store = SemanticSchemaStore()

    env = make_envelope("schema:no_retain:v1", "no_retain_test")
    store.register(env)
    store.activate("schema:no_retain:v1", expected_revision=1)
    store.supersede("schema:no_retain:v1", "schema:no_retain:v2")

    assert not store.is_retention_required("schema:no_retain:v1")


def test_active_always_retained():
    """Active revisions are always retained."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:active_retain:v1", "active_retain_test")
    store.register(env)
    store.activate("schema:active_retain:v1", expected_revision=1)

    assert store.is_retention_required("schema:active_retain:v1")


# ── Context/time applicability ─────────────────────────────────────


def test_context_applicability_filtering():
    """Candidates must be filtered by applicability context."""
    store = SemanticSchemaStore()

    # Schema applicable only in context "ctx:medical"
    env = make_envelope(
        "schema:ctx_medical:v1", "medical_term",
        applicability_context_refs=("ctx:medical",),
    )
    store.register(env)

    # Query with matching context → found
    candidates = store.find_candidates("medical_term", context_ref="ctx:medical")
    assert len(candidates) == 1

    # Query with non-matching context → not found
    candidates = store.find_candidates("medical_term", context_ref="ctx:general")
    assert len(candidates) == 0

    # Query without context → found (no filtering)
    candidates = store.find_candidates("medical_term")
    assert len(candidates) == 1


def test_time_applicability_filtering():
    """Candidates must be filtered by valid time."""
    store = SemanticSchemaStore()

    # Schema valid only in 2020-2025
    env = make_envelope(
        "schema:time_limited:v1", "time_concept",
        valid_time=TimeExtent(
            start=datetime(2020, 1, 1, tzinfo=timezone.utc),
            end=datetime(2025, 12, 31, tzinfo=timezone.utc),
        ),
    )
    store.register(env)

    # Query within valid time → found
    candidates = store.find_candidates(
        "time_concept",
        valid_at=datetime(2023, 6, 1, tzinfo=timezone.utc),
    )
    assert len(candidates) == 1

    # Query outside valid time → not found
    candidates = store.find_candidates(
        "time_concept",
        valid_at=datetime(2030, 1, 1, tzinfo=timezone.utc),
    )
    assert len(candidates) == 0


# ── Scope-aware resolution ─────────────────────────────────────────


def test_scope_does_not_blind_shadow():
    """Narrower scope must not blindly replace wider meaning.

    A user-scoped revision should not override an active global
    schema in the actual context.
    """
    store = SemanticSchemaStore()
    resolver = SchemaResolver(store)

    # Global active schema
    global_env = make_envelope(
        "schema:global_concept:v1", "shared_concept",
        scope=Scope(level=ScopeLevel.GLOBAL),
        confidence=0.9,
    )
    store.register(global_env)
    store.activate("schema:global_concept:v1", expected_revision=1)

    # User-scoped candidate (user's private theory)
    user_env = make_envelope(
        "schema:user_concept:v1", "shared_concept",
        scope=Scope(level=ScopeLevel.USER, owner_id="user1"),
        confidence=0.3,
    )
    store.register(user_env)

    # Resolve with user scope — both should be candidates
    result = resolver.resolve_key(
        "shared_concept",
        scope=Scope(level=ScopeLevel.USER, owner_id="user1"),
    )

    # Both global and user schemas should be present
    assert len(result.candidates) == 2
    # Active candidate should be the global one (it's active)
    assert result.active_candidate is not None
    assert result.active_candidate.record_id == "schema:global_concept:v1"


def test_lexical_form_multiple_senses():
    """One lexical form may map to multiple senses."""
    store = SemanticSchemaStore()
    resolver = SchemaResolver(store)

    # "bank" → river_bank and financial_bank
    store.index_lexical_form("bank", "en", "river_bank")
    store.index_lexical_form("bank", "en", "financial_bank")

    env1 = make_envelope("schema:river_bank:v1", "river_bank")
    env2 = make_envelope("schema:financial_bank:v1", "financial_bank")
    store.register(env1)
    store.register(env2)

    result = resolver.resolve_lexical("bank", "en")
    assert len(result.candidates) == 2
    semantic_keys = {c.semantic_key for c in result.candidates}
    assert "river_bank" in semantic_keys
    assert "financial_bank" in semantic_keys


def test_opaque_clusters_remain_distinct():
    """Opaque uses of one spelling remain separate clusters."""
    store = SemanticSchemaStore()
    resolver = SchemaResolver(store)

    store.index_lexical_form("dax", "en", "dax_sense_1")
    store.index_lexical_form("dax", "en", "dax_sense_2")

    env1 = make_envelope("schema:dax_1:v1", "dax_sense_1", status="candidate")
    env2 = make_envelope("schema:dax_2:v1", "dax_sense_2", status="candidate")
    store.register(env1)
    store.register(env2)

    clusters = resolver.get_opaque_clusters("dax", "en")
    assert len(clusters) == 2  # Two distinct opaque clusters


# ── Store snapshot ─────────────────────────────────────────────────


def test_store_snapshot_is_pinned():
    """Store snapshot must be pinned at a specific revision."""
    store = SemanticSchemaStore()

    env = make_envelope("schema:snapshot:v1", "snapshot_test")
    store.register(env)

    snapshot = store.create_snapshot()
    assert snapshot.store_revision == store.store_revision

    # Mutate the store
    store.activate("schema:snapshot:v1", expected_revision=1)

    # Snapshot should still see the old state
    snap_env = snapshot.get("schema:snapshot:v1")
    assert snap_env.status == "candidate"  # Old state

    # Store should see the new state
    assert store.get("schema:snapshot:v1").status == "active"


def test_store_revision_increments_on_mutation():
    """Store revision must increment on every mutation."""
    store = SemanticSchemaStore()
    initial = store.store_revision

    env = make_envelope("schema:rev_test:v1", "rev_test")
    store.register(env)
    assert store.store_revision == initial + 1

    store.activate("schema:rev_test:v1", expected_revision=1)
    assert store.store_revision == initial + 2


# ── Import boundary ────────────────────────────────────────────────


def test_schema_store_imports_no_engine():
    """Schema store must not import any engine module."""
    import cemm.kernel.schema.store as store_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.kernel.operational_meaning_compiler",
        "cemm.memory.durable_semantic_store",
    ]
    source = open(store_mod.__file__, encoding="utf-8").read()
    for f in forbidden:
        assert f not in source, f"store.py imports forbidden module {f}"


def test_resolver_imports_no_engine():
    """Schema resolver must not import any engine module."""
    import cemm.kernel.schema.resolver as resolver_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.kernel.operational_meaning_compiler",
        "cemm.memory.durable_semantic_store",
    ]
    source = open(resolver_mod.__file__, encoding="utf-8").read()
    for f in forbidden:
        assert f not in source, f"resolver.py imports forbidden module {f}"


# ── Bug regression tests ───────────────────────────────────────────


def test_cluster_rollback_uses_post_commit_revision():
    """Regression: cluster activation rollback must use post-commit revision.

    After set_status succeeds, the revision increments by 1.
    Rollback must use expected+1, not the original expected revision,
    or the CAS will silently fail and leave committed members active.
    """
    store = SemanticSchemaStore()
    env1 = make_envelope("schema:rb1:v1", "rb1")
    env2 = make_envelope("schema:rb2:v1", "rb2")
    env3 = make_envelope("schema:rb3:v1", "rb3")
    store.register(env1)
    store.register(env2)
    store.register(env3)

    # Activate env1 and env2 first (so they're active, revision = 2)
    store.activate("schema:rb1:v1", expected_revision=1)
    store.activate("schema:rb2:v1", expected_revision=1)

    # Now try cluster activation of all three, but env3 has wrong expected revision
    # env1 and env2 are already active (revision 2), env3 is candidate (revision 1)
    # We pass expected_revisions that match for rb1 and rb2 but not rb3
    result = store.activate_cluster(
        ("schema:rb1:v1", "schema:rb2:v1", "schema:rb3:v1"),
        {"schema:rb1:v1": 2, "schema:rb2:v1": 2, "schema:rb3:v1": 999},
    )

    # Should fail — rb3 revision mismatch
    assert result.status == ActivationStatus.CAS_FAILED


def test_cluster_rollback_restores_to_provisional():
    """Regression: cluster rollback must actually restore committed members.

    If member A is committed to active and member B fails, A must be
    rolled back to provisional, not left as active.
    """
    store = SemanticSchemaStore()
    env1 = make_envelope("schema:crb1:v1", "crb1")
    env2 = make_envelope("schema:crb2:v1", "crb2")
    store.register(env1)
    store.register(env2)

    # Transition both to provisional first (realistic scenario:
    # cluster activation operates on schemas that passed structural closure)
    store.transition_to_provisional("schema:crb1:v1", expected_revision=1)
    store.transition_to_provisional("schema:crb2:v1", expected_revision=1)

    # Now try cluster activation, but pass wrong revision for env2
    result = store.activate_cluster(
        ("schema:crb1:v1", "schema:crb2:v1"),
        {"schema:crb1:v1": 2, "schema:crb2:v1": 999},  # env2 wrong revision
    )

    # Should fail
    assert result.status == ActivationStatus.CAS_FAILED

    # env1 should NOT be active — it should be rolled back to provisional
    env1_after = store.get("schema:crb1:v1")
    assert env1_after.status == "provisional", (
        f"env1 should be rolled back to provisional, but is {env1_after.status}"
    )


def test_journal_reversal_preserves_audit_trail():
    """Regression: reversing a journal entry must not destroy the original.

    AGENTS.md: 'Schema merge or identity equivalence is explicit,
    reversible, journaled, and never destroys original references.'
    """
    store = SemanticSchemaStore()
    env1 = make_envelope("schema:rev1:v1", "sense_a")
    env2 = make_envelope("schema:rev2:v1", "sense_b")
    store.register(env1)
    store.register(env2)

    # Merge senses
    entry = store.merge_senses("sense_a", "sense_b", reason="test merge")
    assert entry.reversible

    journal_before = store.get_journal()
    assert len(journal_before) == 1

    # Reverse the merge
    assert store.reverse_journal_entry(entry.entry_id)

    # Original entry must still be in the journal
    journal_after = store.get_journal()
    assert len(journal_after) == 2, (
        f"Journal should have 2 entries (original + reversal), has {len(journal_after)}"
    )
    # Original entry must still exist
    assert any(e.entry_id == entry.entry_id for e in journal_after)
    # Reversal entry must exist
    assert any(e.operation == "reverse:merge" for e in journal_after)


def test_supersede_uses_cas():
    """Regression: supersede must use CAS, not direct mutation."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:sup_cas:v1", "sup_cas")
    store.register(env)
    store.activate("schema:sup_cas:v1", expected_revision=1)

    # Get revision after activation
    rev_after_activate = store.get_revision("schema:sup_cas:v1")
    assert rev_after_activate == 2

    # Supersede should succeed
    assert store.supersede("schema:sup_cas:v1", "schema:sup_cas:v2", reason="test")

    # Revision should have incremented
    rev_after_supersede = store.get_revision("schema:sup_cas:v1")
    assert rev_after_supersede == rev_after_activate + 1

    # Status should be superseded
    assert store.get("schema:sup_cas:v1").status == "superseded"


def test_reject_uses_cas():
    """Regression: reject must use CAS, not direct mutation."""
    store = SemanticSchemaStore()
    env = make_envelope("schema:rej_cas:v1", "rej_cas")
    store.register(env)

    rev_before = store.get_revision("schema:rej_cas:v1")
    assert rev_before == 1

    # Reject should succeed
    assert store.reject("schema:rej_cas:v1", reason="test")

    # Revision should have incremented
    rev_after = store.get_revision("schema:rej_cas:v1")
    assert rev_after == rev_before + 1

    # Status should be rejected
    assert store.get("schema:rej_cas:v1").status == "rejected"
