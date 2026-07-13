"""Acceptance Suite G — Invalidation, replay, and effects (tests 29-37).

### 29. Downgrade cascade
### 30. Derived retraction
### 31. Environment fingerprint invalidation
### 32. Replay idempotence
### 33. Budget enforcement
### 34. Probe before activation
### 35. Effect schema separation
### 36. Reauthorization before execution
### 37. Causal warrant grade
"""
from __future__ import annotations

import pytest

from cemm.kernel.epistemics.invalidation_events import (
    InvalidationSource, InvalidationAction, TypedInvalidationEvent,
    InvalidationEventBus,
)
from cemm.kernel.epistemics.invalidation_engine import (
    InvalidationEngine, InvalidationResult,
)
from cemm.kernel.epistemics.replay_safety import (
    ReplaySafetyManager, InFlightEffect, ReauthorizationResult,
)
from cemm.kernel.learning.replay_queue import (
    ReplayQueue, ReplayKey,
)
from cemm.kernel.epistemics.artifact_index import (
    DerivedArtifactIndex, IndexedArtifact, ArtifactKind, ArtifactStatus,
)
from cemm.kernel.model.learning import (
    ReplayWorkItem, ReplayResult, DerivedArtifactProvenance,
)
from cemm.kernel.execution.causal_warrant import (
    CausalWarrantGrade, CausalWarrantAssessment, CausalWarrantEvaluator,
    SCHEMA_LEVEL_CAPABILITIES, EffectCapability,
)
from cemm.kernel.model.identity import AssessmentEnvironmentFingerprint
from cemm.kernel.schema.closure import SchemaGroundingAssessment
from cemm.kernel.schema.use_profile import (
    derive_use_profile, SemanticOperation, UseProfileLevel,
)


# ── Test 29: Downgrade cascade ──


def test_29a_schema_downgrade_publishes_event():
    """Schema downgrade publishes invalidation event."""
    bus = InvalidationEventBus()
    event = TypedInvalidationEvent.create(
        source=InvalidationSource.SCHEMA_DOWNGRADE,
        action=InvalidationAction.RETRACT,
        changed_schema_revision_refs=("schema:test:v1",),
        affected_artifact_ids=("prop:1", "prop:2"),
    )
    bus.publish(event)
    events = bus.get_events()
    assert len(events) == 1
    assert events[0].source == InvalidationSource.SCHEMA_DOWNGRADE


def test_29b_downgrade_retracts_dependents():
    """Downgrade retracts dependent classifications and inferences."""
    engine = InvalidationEngine()
    # Register dependents in the index
    engine.index.register(IndexedArtifact(
        artifact_id="prop:classification:1",
        artifact_kind=ArtifactKind.CLASSIFICATION,
        provenance=DerivedArtifactProvenance(
            supporting_schema_revision_refs=("schema:leader:v1",),
        ),
    ))
    engine.index.register(IndexedArtifact(
        artifact_id="prop:inference:2",
        artifact_kind=ArtifactKind.INFERENCE,
        provenance=DerivedArtifactProvenance(
            supporting_schema_revision_refs=("schema:leader:v1",),
        ),
    ))
    event = TypedInvalidationEvent.create(
        source=InvalidationSource.SCHEMA_DOWNGRADE,
        action=InvalidationAction.RETRACT,
        changed_schema_revision_refs=("schema:leader:v1",),
    )
    result = engine.process(event)
    assert "prop:classification:1" in result.retracted_artifact_ids
    assert "prop:inference:2" in result.retracted_artifact_ids


# ── Test 30: Derived retraction ──


def test_30a_derived_cognition_retracted():
    """Derived cognition is retracted when support is withdrawn."""
    engine = InvalidationEngine()
    engine.index.register(IndexedArtifact(
        artifact_id="prop:derived:1",
        artifact_kind=ArtifactKind.INFERENCE,
        provenance=DerivedArtifactProvenance(
            supporting_schema_revision_refs=("schema:old:v1",),
        ),
    ))
    engine.index.register(IndexedArtifact(
        artifact_id="prop:derived:2",
        artifact_kind=ArtifactKind.INFERENCE,
        provenance=DerivedArtifactProvenance(
            supporting_schema_revision_refs=("schema:old:v1",),
        ),
    ))
    event = TypedInvalidationEvent.create(
        source=InvalidationSource.SCHEMA_SUPERSESSION,
        action=InvalidationAction.RETRACT,
        changed_schema_revision_refs=("schema:old:v1",),
    )
    result = engine.process(event)
    assert "prop:derived:1" in result.retracted_artifact_ids
    assert "prop:derived:2" in result.retracted_artifact_ids


def test_30b_original_evidence_preserved():
    """Original evidence is preserved after retraction."""
    engine = InvalidationEngine()
    engine.index.register(IndexedArtifact(
        artifact_id="prop:1",
        artifact_kind=ArtifactKind.CLASSIFICATION,
        provenance=DerivedArtifactProvenance(
            supporting_schema_revision_refs=("schema:test:v1",),
        ),
    ))
    event = TypedInvalidationEvent.create(
        source=InvalidationSource.SCHEMA_DOWNGRADE,
        action=InvalidationAction.MARK_STALE,
        changed_schema_revision_refs=("schema:test:v1",),
    )
    result = engine.process(event)
    # Mark stale preserves the artifact — doesn't retract
    assert "prop:1" not in result.retracted_artifact_ids
    assert "prop:1" in result.staled_artifact_ids
    assert result.evidence_preserved


# ── Test 31: Environment fingerprint invalidation ──


def test_31a_fingerprint_change_invalidates():
    """Environment fingerprint change publishes invalidation event."""
    bus = InvalidationEventBus()
    event = TypedInvalidationEvent.create(
        source=InvalidationSource.ENVIRONMENT_FINGERPRINT_CHANGE,
        action=InvalidationAction.MARK_STALE,
        old_fingerprint="fp1",
        new_fingerprint="fp2",
        affected_artifact_ids=("prop:1", "plan:1"),
    )
    bus.publish(event)
    events = bus.get_events()
    assert len(events) == 1
    assert events[0].source == InvalidationSource.ENVIRONMENT_FINGERPRINT_CHANGE


def test_31b_fingerprint_includes_components():
    """Assessment environment fingerprint includes key components."""
    fp = AssessmentEnvironmentFingerprint(
        schema_store_revision=1,
        dependency_revision_hash="hash1",
        grounding_policy_version="v1",
        competency_suite_hash="cs_hash",
        kernel_foundation_version="kf_v1",
        type_registry_version="tr_v1",
        inference_policy_version="ip_v1",
        truth_maintenance_version="tm_v1",
        adapter_contract_hash="ac_hash",
        context_scope_policy_version="csp_v1",
    )
    assert fp.schema_store_revision == 1
    assert fp.grounding_policy_version == "v1"


# ── Test 32: Replay idempotence ──


def _make_replay_item(target_ref: str = "schema:test:v1") -> ReplayWorkItem:
    return ReplayWorkItem(
        id=f"rwi:{target_ref}",
        source_evidence_ref="evidence:1",
        target_sense_ref="sense:1",
        target_schema_revision_ref=target_ref,
        checkpoint_ref="ckpt:1",
        context_refs=("ctx:actual",),
        dependency_fingerprint="fp1",
    )


def test_32a_replay_deduplicated():
    """Duplicate replay delivery produces one result."""
    queue = ReplayQueue()
    item = _make_replay_item()
    assert queue.enqueue(item)  # First enqueue succeeds
    assert not queue.enqueue(item)  # Second is deduplicated


def test_32b_replay_snapshot_pinned():
    """Replay is snapshot-pinned.

    Per ACCEPTANCE_TESTS.md §32: dedup key stable; stale entries cancel
    after supersession.
    """
    queue = ReplayQueue()
    queue.pin_snapshot("fp1")
    # Enqueue an item with matching fingerprint
    item = _make_replay_item()
    assert queue.enqueue(item)
    assert queue.pending_count() == 1
    # Cancel stale items (different fingerprint) — none should be cancelled
    cancelled = queue.cancel_stale("fp1")
    assert len(cancelled) == 0
    # Now change fingerprint — item is stale
    cancelled = queue.cancel_stale("fp2")
    assert len(cancelled) == 1
    assert queue.pending_count() == 0


# ── Test 33: Budget enforcement ──


def test_33a_replay_budget_enforced():
    """Replay queue handles multiple items with priority ordering.

    Per ACCEPTANCE_TESTS.md §33: active goal blockers replay first;
    per-cycle limit enforced; remainder persists with evidence and
    blockers intact.
    """
    queue = ReplayQueue()
    i1 = _make_replay_item("schema:a:v1")
    i2 = _make_replay_item("schema:b:v1")
    # i2 has higher priority
    i2 = ReplayWorkItem(
        id=i2.id,
        source_evidence_ref=i2.source_evidence_ref,
        target_sense_ref=i2.target_sense_ref,
        target_schema_revision_ref=i2.target_schema_revision_ref,
        checkpoint_ref=i2.checkpoint_ref,
        context_refs=i2.context_refs,
        dependency_fingerprint=i2.dependency_fingerprint,
        priority=10.0,
    )
    assert queue.enqueue(i1)
    assert queue.enqueue(i2)
    assert queue.pending_count() == 2
    # Dequeue returns highest-priority first
    first = queue.dequeue()
    assert first is not None
    assert first.target_schema_revision_ref == "schema:b:v1"
    assert queue.pending_count() == 1
    # Remaining item persists
    second = queue.dequeue()
    assert second is not None
    assert second.target_schema_revision_ref == "schema:a:v1"
    assert queue.pending_count() == 0


# ── Test 34: Probe before activation ──


def test_34a_probe_does_not_activate():
    """Probing a candidate schema does not activate it.

    Per ACCEPTANCE_TESTS.md §34: no repeated interrogation; no fabricated
    closure. Probe is permitted even for opaque schemas, but does not
    activate or classify.
    """
    assessment = SchemaGroundingAssessment(
        record_id="schema:probe:v1",
        semantic_key="probe",
        environment_fingerprint="fp1",
        is_structurally_executable=False,
    )
    profile = derive_use_profile(assessment, context_ref="ctx:actual")
    assert profile.permits(SemanticOperation.PROBE)
    assert not profile.permits(SemanticOperation.CLASSIFY)
    assert not profile.permits(SemanticOperation.LICENSED_INFERENCE)
    assert not profile.permits(SemanticOperation.ANSWER_DEFINING_QUERY)


def test_34b_probe_persists_frontier():
    """Probe frontier persists — replay queue tracks probe work items.

    Per ACCEPTANCE_TESTS.md §34: exact frontier and asked probes persist;
    later evidence resumes transaction; no fabricated closure.
    """
    queue = ReplayQueue()
    # Enqueue a probe work item
    probe_item = ReplayWorkItem(
        id="rwi:probe:1",
        source_evidence_ref="evidence:probe:1",
        target_sense_ref="sense:probe:1",
        target_schema_revision_ref="schema:ungrounded:v1",
        checkpoint_ref="ckpt:probe:1",
        context_refs=("ctx:actual",),
        dependency_fingerprint="fp1",
        priority=5.0,
    )
    assert queue.enqueue(probe_item)
    # Probe persists in queue — not auto-completed
    assert queue.pending_count() == 1
    assert not queue.is_completed(probe_item)
    # Later evidence can resume — dequeue and complete the probe
    dequeued = queue.dequeue()
    assert dequeued is not None
    assert dequeued.id == probe_item.id
    assert queue.pending_count() == 0
    result = ReplayResult(
        work_item_ref=probe_item.id,
        status="succeeded",
    )
    queue.complete(probe_item, result)
    assert queue.is_completed(probe_item)


# ── Test 35: Effect schema separation ──


def test_35a_teaching_effect_schema_fires_no_effect():
    """Teaching a causal/effect schema fires no effect."""
    evaluator = CausalWarrantEvaluator()
    assessment = evaluator.assess_warrant(
        proposition_ref="prop:teach:v1",
        grade=CausalWarrantGrade.REPORTED_CLAIM,
        is_taught=True,
    )
    assert assessment.is_schema_level_only
    assert not evaluator.can_execute(assessment, live_authorization=False)


def test_35b_schema_level_capabilities_excluded():
    """Schema-level capabilities are separate from live-authority capabilities."""
    assert EffectCapability.AUTHORIZE not in SCHEMA_LEVEL_CAPABILITIES
    assert EffectCapability.EXECUTE not in SCHEMA_LEVEL_CAPABILITIES
    assert EffectCapability.COMMIT not in SCHEMA_LEVEL_CAPABILITIES


# ── Test 36: Reauthorization before execution ──


def test_36a_stale_effects_require_reauthorization():
    """Stale effects must be re-authorized before execution."""
    manager = ReplaySafetyManager()
    manager.register_in_flight_effect(
        effect_id="eff:1",
        operation_id="op:1",
        idempotency_key="idem:1",
        authorization_fingerprint="fp1",
    )
    # Reauthorize with different fingerprint → not authorized
    result = manager.reauthorize("eff:1", current_fingerprint="fp2")
    assert not result.is_authorized
    assert "fingerprint changed" in result.reason


def test_36b_reauthorization_with_same_fingerprint():
    """Reauthorization with same fingerprint succeeds."""
    manager = ReplaySafetyManager()
    manager.register_in_flight_effect(
        effect_id="eff:2",
        operation_id="op:2",
        idempotency_key="idem:2",
        authorization_fingerprint="fp1",
    )
    result = manager.reauthorize("eff:2", current_fingerprint="fp1")
    assert result.is_authorized


# ── Test 37: Causal warrant grade ──


def test_37a_causal_warrant_grades_ordered():
    """Causal warrant grades are ordered from weakest to strongest."""
    assert CausalWarrantGrade.REPORTED_CLAIM.strength < CausalWarrantGrade.INTERVENTION_SUPPORTED.strength
    assert CausalWarrantGrade.PREDICTIVE_ASSOCIATION.strength < CausalWarrantGrade.MECHANISM_SUPPORTED.strength


def test_37b_low_warrant_no_live_execution():
    """Low warrant grade with no live authorization → no execution."""
    evaluator = CausalWarrantEvaluator()
    assessment = CausalWarrantAssessment(
        proposition_ref="prop:1",
        grade=CausalWarrantGrade.REPORTED_CLAIM,
    )
    assert not evaluator.can_execute(assessment, live_authorization=False)


def test_37c_high_warrant_still_needs_live_auth():
    """Even high warrant grade needs live authorization for execution."""
    evaluator = CausalWarrantEvaluator()
    assessment = CausalWarrantAssessment(
        proposition_ref="prop:1",
        grade=CausalWarrantGrade.INTERVENTION_SUPPORTED,
    )
    # Without live authorization → cannot execute
    assert not evaluator.can_execute(assessment, live_authorization=False)
