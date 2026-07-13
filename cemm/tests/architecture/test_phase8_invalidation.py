"""Phase 8 gate tests: Invalidation, truth maintenance, and replay safety.

Gates (from IMPLEMENTATION_PLAN.md Phase 8):
- parent downgrade retracts classifications, inferences, answers, plans,
  messages, and effect proposals;
- evidence remains;
- cross-schema inference laundering does not increase support;
- duplicate replay delivery produces one result;
- in-flight effects reauthorize against current state.

Additional guardrail tests from AGENTS.md §7.5, LEARNING_PIPELINE.md §13,
CORE_LOOP.md §9, ADR-21:
- Every derived artifact carries dependency provenance
- Historical output generates repair obligation
- Effects and irreversible operations revalidate at authorization
- Schema supersession marks stale (not retracts)
- Environment fingerprint change marks stale
- Import boundaries: epistemics → model + schema + learning
"""
from __future__ import annotations

import pytest

from cemm.kernel.epistemics.artifact_index import (
    DerivedArtifactIndex, IndexedArtifact, ArtifactKind, ArtifactStatus,
)
from cemm.kernel.epistemics.invalidation_events import (
    TypedInvalidationEvent, InvalidationSource, InvalidationAction,
    InvalidationEventBus,
)
from cemm.kernel.epistemics.invalidation_engine import (
    InvalidationEngine, InvalidationResult, CrossSchemaLaunderingGuard,
)
from cemm.kernel.epistemics.replay_safety import (
    ReplaySafetyManager, InFlightEffect, ReauthorizationResult,
)
from cemm.kernel.model.learning import DerivedArtifactProvenance
from cemm.kernel.model.learning import ReplayWorkItem, ReplayResult
from cemm.kernel.learning.replay_queue import ReplayQueue


# ── Helpers ────────────────────────────────────────────────────────


def make_artifact(
    artifact_id: str,
    kind: ArtifactKind = ArtifactKind.INFERENCE,
    schema_refs: tuple[str, ...] = ("schema:test:v1",),
    assessment_refs: tuple[str, ...] = (),
    evidence_refs: tuple[str, ...] = (),
    fingerprint: str = "fp:v1",
) -> IndexedArtifact:
    return IndexedArtifact(
        artifact_id=artifact_id,
        artifact_kind=kind,
        provenance=DerivedArtifactProvenance(
            supporting_schema_revision_refs=schema_refs,
            supporting_assessment_refs=assessment_refs,
            evidence_refs=evidence_refs,
            environment_fingerprint=fingerprint,
        ),
    )


# ── Gate 1: parent downgrade retracts dependent artifacts ──


def test_parent_downgrade_retracts_classifications():
    """Parent downgrade retracts classifications."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    # Register a classification dependent on schema:test:v1
    artifact = make_artifact("art:cls1", ArtifactKind.CLASSIFICATION)
    index.register(artifact)

    # Downgrade the schema
    result = engine.on_schema_downgrade("schema:test:v1")

    assert "art:cls1" in result.retracted_artifact_ids
    assert index.get("art:cls1").status == ArtifactStatus.RETRACTED


def test_parent_downgrade_retracts_inferences():
    """Parent downgrade retracts inferences."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    artifact = make_artifact("art:inf1", ArtifactKind.INFERENCE)
    index.register(artifact)

    result = engine.on_schema_downgrade("schema:test:v1")
    assert "art:inf1" in result.retracted_artifact_ids


def test_parent_downgrade_retracts_cached_answers():
    """Parent downgrade retracts cached answers."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    artifact = make_artifact("art:ans1", ArtifactKind.CACHED_ANSWER)
    index.register(artifact)

    result = engine.on_schema_downgrade("schema:test:v1")
    assert "art:ans1" in result.retracted_artifact_ids


def test_parent_downgrade_retracts_plans():
    """Parent downgrade retracts plans."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    artifact = make_artifact("art:plan1", ArtifactKind.PLAN)
    index.register(artifact)

    result = engine.on_schema_downgrade("schema:test:v1")
    assert "art:plan1" in result.retracted_artifact_ids


def test_parent_downgrade_retracts_messages():
    """Parent downgrade retracts undispatched messages."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    artifact = make_artifact("art:msg1", ArtifactKind.MESSAGE_ITEM)
    index.register(artifact)

    result = engine.on_schema_downgrade("schema:test:v1")
    assert "art:msg1" in result.retracted_artifact_ids


def test_parent_downgrade_retracts_effect_proposals():
    """Parent downgrade retracts effect proposals."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    artifact = make_artifact("art:eff1", ArtifactKind.EFFECT_PROPOSAL)
    index.register(artifact)

    result = engine.on_schema_downgrade("schema:test:v1")
    assert "art:eff1" in result.retracted_artifact_ids


def test_parent_downgrade_retracts_capability_conclusions():
    """Parent downgrade retracts capability/understanding conclusions."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    artifact = make_artifact("art:cap1", ArtifactKind.CAPABILITY_CONCLUSION)
    index.register(artifact)

    result = engine.on_schema_downgrade("schema:test:v1")
    assert "art:cap1" in result.retracted_artifact_ids


def test_parent_downgrade_retracts_learning_success_claims():
    """Parent downgrade retracts learning-success claims."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    artifact = make_artifact("art:learn1", ArtifactKind.LEARNING_SUCCESS_CLAIM)
    index.register(artifact)

    result = engine.on_schema_downgrade("schema:test:v1")
    assert "art:learn1" in result.retracted_artifact_ids


# ── Gate 2: evidence remains ──


def test_evidence_remains_after_invalidation():
    """Evidence remains after invalidation — original evidence is preserved."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    # Register an artifact with evidence dependency
    artifact = make_artifact(
        "art:inf1", ArtifactKind.INFERENCE,
        evidence_refs=("ev:test:1",),
    )
    index.register(artifact)

    # Retract evidence
    result = engine.on_evidence_retraction("ev:test:1")

    # Artifact is retracted
    assert "art:inf1" in result.retracted_artifact_ids

    # But evidence_preserved is True
    assert result.evidence_preserved


def test_historical_output_generates_repair_obligation():
    """Historical output remains an event and may generate a repair obligation."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    # Register a message item (historical output)
    artifact = make_artifact("art:msg1", ArtifactKind.MESSAGE_ITEM)
    index.register(artifact)

    # Downgrade the schema
    result = engine.on_schema_downgrade("schema:test:v1")

    # Repair obligation should be generated
    assert "art:msg1" in result.repair_obligation_ids


# ── Gate 3: cross-schema inference laundering does not increase support ──


def test_cross_schema_laundering_blocked_by_ancestry():
    """Cross-schema inference laundering does not increase support.

    If target is in evidence schema's ancestry, the evidence cannot
    increase support (circular support).
    """
    guard = CrossSchemaLaunderingGuard()
    guard.register_support_ancestry("schema:A", ("schema:B",))
    guard.register_support_ancestry("schema:B", ("schema:C",))

    # A's ancestry includes B → evidence from A cannot support B
    can_increase = guard.can_increase_support(
        evidence_schema_ref="schema:A",
        target_schema_ref="schema:B",
    )
    assert not can_increase


def test_cross_schema_laundering_blocked_by_scc():
    """Cross-schema inference laundering does not increase support.

    If both schemas are in the same SCC, evidence cannot increase support.
    """
    guard = CrossSchemaLaunderingGuard()
    guard.register_support_scc("schema:A", ("schema:A", "schema:B"))
    guard.register_support_scc("schema:B", ("schema:A", "schema:B"))

    can_increase = guard.can_increase_support(
        evidence_schema_ref="schema:A",
        target_schema_ref="schema:B",
    )
    assert not can_increase


def test_cross_schema_laundering_blocked_by_lineage():
    """Cross-schema inference laundering does not increase support.

    If evidence lineage overlaps with target's ancestry, support is blocked.
    """
    guard = CrossSchemaLaunderingGuard()
    guard.register_support_ancestry("schema:B", ("schema:C",))

    can_increase = guard.can_increase_support(
        evidence_schema_ref="schema:A",
        target_schema_ref="schema:B",
        evidence_lineage=("schema:C",),  # Lineage overlaps with B's ancestry
    )
    assert not can_increase


def test_no_laundering_allows_support():
    """When no laundering is detected, support can increase."""
    guard = CrossSchemaLaunderingGuard()
    guard.register_support_ancestry("schema:A", ("schema:X",))
    guard.register_support_ancestry("schema:B", ("schema:Y",))

    can_increase = guard.can_increase_support(
        evidence_schema_ref="schema:A",
        target_schema_ref="schema:B",
        evidence_lineage=("schema:Z",),
    )
    assert can_increase


def test_laundering_detection_returns_description():
    """detect_laundering returns a human-readable description."""
    guard = CrossSchemaLaunderingGuard()
    guard.register_support_ancestry("schema:A", ("schema:B",))

    desc = guard.detect_laundering("schema:A", "schema:B")
    assert desc is not None
    assert "circular support" in desc


# ── Gate 4: duplicate replay delivery produces one result ──


def test_duplicate_replay_produces_one_result():
    """Duplicate replay delivery produces one result."""
    manager = ReplaySafetyManager()

    item = ReplayWorkItem(
        id="rw1", source_evidence_ref="ev1", target_sense_ref="sense1",
        target_schema_revision_ref="schema:v1", checkpoint_ref="ckpt1",
        context_refs=("ctx1",), dependency_fingerprint="fp1",
        idempotency_key="key1", priority=1.0,
    )

    # First submission → enqueued
    enqueued, existing = manager.submit_replay(item)
    assert enqueued
    assert existing is None

    # Complete the replay
    result = ReplayResult(work_item_ref="rw1", status="succeeded")
    manager.complete_replay(item, result)

    # Second submission (duplicate) → not enqueued, returns existing result
    enqueued, existing = manager.submit_replay(item)
    assert not enqueued
    assert existing is not None
    assert existing.status == "succeeded"


def test_replay_no_external_action_repeats():
    """Replay never repeats external actions or already dispatched communication."""
    manager = ReplaySafetyManager()

    # Record an executed operation
    manager.replay_queue.record_executed_operation("op1", "idem_key1")

    # Check that it's marked as executed
    assert manager.replay_queue.is_operation_executed("idem_key1")


# ── Gate 5: in-flight effects reauthorize against current state ──


def test_in_flight_effect_reauthorization_success():
    """In-flight effects reauthorize against current state — success when
    fingerprint matches and permission/resources available."""
    manager = ReplaySafetyManager()

    effect = manager.register_in_flight_effect(
        effect_id="eff1",
        operation_id="op1",
        idempotency_key="key1",
        authorization_fingerprint="fp:v1",
    )

    # Reauthorize with same fingerprint
    result = manager.reauthorize(
        effect_id="eff1",
        current_fingerprint="fp:v1",
        current_permission=True,
        current_resources_available=True,
    )
    assert result.is_authorized


def test_in_flight_effect_reauthorization_fingerprint_change():
    """In-flight effects reauthorize — fails when fingerprint changed."""
    manager = ReplaySafetyManager()

    manager.register_in_flight_effect(
        effect_id="eff1",
        operation_id="op1",
        idempotency_key="key1",
        authorization_fingerprint="fp:v1",
    )

    result = manager.reauthorize(
        effect_id="eff1",
        current_fingerprint="fp:v2",  # Changed!
    )
    assert not result.is_authorized
    assert "fingerprint changed" in result.reason


def test_in_flight_effect_reauthorization_permission_revoked():
    """In-flight effects reauthorize — fails when permission revoked."""
    manager = ReplaySafetyManager()

    manager.register_in_flight_effect(
        effect_id="eff1",
        operation_id="op1",
        idempotency_key="key1",
        authorization_fingerprint="fp:v1",
    )

    result = manager.reauthorize(
        effect_id="eff1",
        current_fingerprint="fp:v1",
        current_permission=False,  # Revoked!
    )
    assert not result.is_authorized
    assert "permission" in result.reason


def test_in_flight_effect_reauthorization_resources_exhausted():
    """In-flight effects reauthorize — fails when resources exhausted."""
    manager = ReplaySafetyManager()

    manager.register_in_flight_effect(
        effect_id="eff1",
        operation_id="op1",
        idempotency_key="key1",
        authorization_fingerprint="fp:v1",
    )

    result = manager.reauthorize(
        effect_id="eff1",
        current_fingerprint="fp:v1",
        current_resources_available=False,  # Exhausted!
    )
    assert not result.is_authorized
    assert "resources" in result.reason


def test_in_flight_effect_commit():
    """In-flight effects can be committed after reauthorization."""
    manager = ReplaySafetyManager()

    manager.register_in_flight_effect(
        effect_id="eff1",
        operation_id="op1",
        idempotency_key="key1",
        authorization_fingerprint="fp:v1",
    )

    committed = manager.commit_effect("eff1")
    assert committed is not None
    assert committed.status == "committed"

    # No longer in-flight
    assert len(manager.get_in_flight_effects()) == 0


def test_in_flight_effect_cancel():
    """In-flight effects can be cancelled."""
    manager = ReplaySafetyManager()

    manager.register_in_flight_effect(
        effect_id="eff1",
        operation_id="op1",
        idempotency_key="key1",
        authorization_fingerprint="fp:v1",
    )

    cancelled = manager.cancel_effect("eff1")
    assert cancelled is not None
    assert cancelled.status == "cancelled"


# ── Additional guardrail tests ──


def test_schema_supersession_marks_stale():
    """Schema supersession marks dependent artifacts as stale, not retracted."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    artifact = make_artifact("art:inf1", ArtifactKind.INFERENCE)
    index.register(artifact)

    result = engine.on_schema_supersession("schema:test:v1", "schema:test:v2")

    assert "art:inf1" in result.staled_artifact_ids
    assert "art:inf1" not in result.retracted_artifact_ids
    assert index.get("art:inf1").status == ArtifactStatus.STALE


def test_environment_change_marks_stale():
    """Environment fingerprint change marks dependent artifacts as stale."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    artifact = make_artifact("art:inf1", ArtifactKind.INFERENCE, fingerprint="fp:v1")
    index.register(artifact)

    result = engine.on_environment_change("fp:v1", "fp:v2")

    assert "art:inf1" in result.staled_artifact_ids
    assert index.get("art:inf1").status == ArtifactStatus.STALE


def test_in_flight_effect_reauthorization_action():
    """In-flight effects get REAUTHORIZE action, not RETRACT."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    # Register an effect proposal
    artifact = make_artifact("art:eff1", ArtifactKind.EFFECT_PROPOSAL)
    index.register(artifact)

    # Use on_in_flight_effect which uses REAUTHORIZE action
    result = engine.on_in_flight_effect("schema:test:v1")

    assert "art:eff1" in result.reauthorized_artifact_ids
    assert "art:eff1" not in result.retracted_artifact_ids


def test_artifact_index_find_by_schema():
    """Artifact index finds artifacts by schema revision."""
    index = DerivedArtifactIndex()

    a1 = make_artifact("art:1", schema_refs=("schema:A",))
    a2 = make_artifact("art:2", schema_refs=("schema:B",))
    a3 = make_artifact("art:3", schema_refs=("schema:A", "schema:B"))
    index.register(a1)
    index.register(a2)
    index.register(a3)

    found = index.find_by_schema("schema:A")
    assert len(found) == 2  # art:1 and art:3

    found = index.find_by_schema("schema:B")
    assert len(found) == 2  # art:2 and art:3


def test_artifact_index_find_all_dependents():
    """Artifact index finds all dependents across multiple inputs."""
    index = DerivedArtifactIndex()

    a1 = make_artifact("art:1", schema_refs=("schema:A",))
    a2 = make_artifact("art:2", assessment_refs=("assess:1",))
    a3 = make_artifact("art:3", evidence_refs=("ev:1",))
    index.register(a1)
    index.register(a2)
    index.register(a3)

    found = index.find_all_dependents(
        schema_revision_refs=("schema:A",),
        assessment_refs=("assess:1",),
        evidence_refs=("ev:1",),
    )
    assert len(found) == 3


def test_invalidation_event_bus_publish_and_subscribe():
    """Invalidation event bus publishes and delivers to subscribers."""
    bus = InvalidationEventBus()

    received = []
    class Subscriber:
        def on_invalidation(self, event):
            received.append(event)

    bus.subscribe(Subscriber())
    event = TypedInvalidationEvent.create(
        source=InvalidationSource.SCHEMA_DOWNGRADE,
        changed_schema_revision_refs=("schema:test:v1",),
    )
    bus.publish(event)

    assert len(received) == 1
    assert received[0].source == InvalidationSource.SCHEMA_DOWNGRADE


def test_already_retracted_artifact_not_processed_again():
    """Already retracted artifacts are not processed again."""
    index = DerivedArtifactIndex()
    engine = InvalidationEngine(index=index)

    artifact = make_artifact("art:inf1", ArtifactKind.INFERENCE)
    index.register(artifact)

    # First invalidation retracts it
    result1 = engine.on_schema_downgrade("schema:test:v1")
    assert len(result1.retracted_artifact_ids) == 1

    # Second invalidation should not re-retract
    result2 = engine.on_schema_downgrade("schema:test:v1")
    assert len(result2.retracted_artifact_ids) == 0


# ── Import boundary tests ──


def test_phase8_imports_no_engine():
    """Phase 8 epistemics modules must not import any engine module."""
    import cemm.kernel.epistemics.artifact_index as ai_mod
    import cemm.kernel.epistemics.invalidation_events as ie_mod
    import cemm.kernel.epistemics.invalidation_engine as ing_mod
    import cemm.kernel.epistemics.replay_safety as rs_mod

    forbidden = [
        "cemm.kernel.semantic_kernel_runtime",
        "cemm.kernel.meaning_perceptor",
        "cemm.kernel.meaning_graph_builder",
        "cemm.memory.durable_semantic_store",
        "cemm.kernel.commit",
    ]
    for mod in [ai_mod, ie_mod, ing_mod, rs_mod]:
        source = open(mod.__file__, encoding="utf-8").read()
        for f in forbidden:
            assert f not in source, f"{mod.__file__} imports forbidden module {f}"


def test_invalidation_engine_does_not_mutate_canonical_stores():
    """InvalidationEngine must not mutate canonical stores."""
    engine = InvalidationEngine()

    assert not hasattr(engine, "activate")
    assert not hasattr(engine, "register")
    assert not hasattr(engine, "commit")
    assert not hasattr(engine, "set_status")
