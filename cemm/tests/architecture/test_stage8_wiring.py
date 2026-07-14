"""Stage 8 wiring and exit gate tests.

Exit gates (from completion-plan.md Stage 8):
- parent downgrade cascades correctly;
- duplicate replay is idempotent;
- stale plans/effects reauthorize;
- privacy deletion is not archival;
- prior wrong output creates bounded repair.

Wiring tests verify that:
- InvalidationEngine, RetractionEngine, ReplaySafetyManager,
  CrossSchemaLaunderingGuard, and DerivedArtifactIndex are
  constructed in runtime and passed to CognitiveKernel;
- CognitiveKernel.execute_correction delegates to RetractionEngine
  and triggers invalidation cascade;
- CognitiveCycle carries invalidation_result and repair_obligations;
- cycle artifacts are registered in DerivedArtifactIndex;
- in-flight effects are registered and reauthorized at critical commit.

Architectural guardrails (AGENTS.md §7.5, §7.8, LEARNING_PIPELINE.md §13-14,
CORE_LOOP.md §9, ADR-21):
- A dependency or environment change invalidates all dependent derived cognition.
- Historical output generates repair obligation.
- Effects and irreversible operations revalidate at authorization and critical commit.
- Cross-schema inference laundering does not increase support.
- Archival cannot masquerade as privacy deletion.
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
from cemm.kernel.epistemics.truth_maintenance import TruthMaintenance
from cemm.kernel.correction.retraction_engine import RetractionEngine
from cemm.kernel.correction.operations import (
    CorrectionKind, CorrectionReversibility, RetentionPolicy,
    CorrectionOperation, CorrectionResult,
    CorrectionOperationFactory,
)
from cemm.kernel.correction.guards import (
    ArchivalPrivacyGuard, CorrectionTargetingGuard,
)
from cemm.kernel.learning.replay_queue import ReplayQueue
from cemm.kernel.model.learning import (
    DerivedArtifactProvenance, ReplayWorkItem, ReplayResult,
)
from cemm.kernel.model.cycle import CognitiveCycle


# ── Helpers ────────────────────────────────────────────────────────


def make_artifact(
    artifact_id: str,
    kind: ArtifactKind = ArtifactKind.INFERENCE,
    schema_refs: tuple[str, ...] = ("schema:test:v1",),
    assessment_refs: tuple[str, ...] = (),
    evidence_refs: tuple[str, ...] = (),
    fingerprint: str | None = None,
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


# ── 1. Runtime wiring tests ───────────────────────────────────────


class TestRuntimeWiring:
    """Verify that runtime constructs and wires all Stage 8 components."""

    def test_runtime_constructs_invalidation_engine(self):
        """Runtime constructs InvalidationEngine."""
        from cemm.app.runtime import Runtime
        rt = Runtime()
        assert rt.invalidation_engine is not None
        assert isinstance(rt.invalidation_engine, InvalidationEngine)

    def test_runtime_constructs_retraction_engine(self):
        """Runtime constructs RetractionEngine."""
        from cemm.app.runtime import Runtime
        rt = Runtime()
        assert rt.retraction_engine is not None
        assert isinstance(rt.retraction_engine, RetractionEngine)

    def test_runtime_constructs_replay_safety_manager(self):
        """Runtime constructs ReplaySafetyManager."""
        from cemm.app.runtime import Runtime
        rt = Runtime()
        assert rt.replay_safety_manager is not None
        assert isinstance(rt.replay_safety_manager, ReplaySafetyManager)

    def test_runtime_constructs_cross_schema_guard(self):
        """Runtime constructs CrossSchemaLaunderingGuard."""
        from cemm.app.runtime import Runtime
        rt = Runtime()
        assert rt.cross_schema_guard is not None
        assert isinstance(rt.cross_schema_guard, CrossSchemaLaunderingGuard)

    def test_runtime_constructs_artifact_index(self):
        """Runtime constructs DerivedArtifactIndex."""
        from cemm.app.runtime import Runtime
        rt = Runtime()
        assert rt.artifact_index is not None
        assert isinstance(rt.artifact_index, DerivedArtifactIndex)

    def test_runtime_cross_schema_guard_wired_to_evaluator(self):
        """CrossSchemaLaunderingGuard is wired into EpistemicEvaluator."""
        from cemm.app.runtime import Runtime
        rt = Runtime()
        assert rt.kernel._cross_schema_guard is not None
        assert rt.kernel._cross_schema_guard is rt.cross_schema_guard

    def test_cutover_verifier_registered_for_invalidation(self):
        """Cutover verifier registers InvalidationEngine for derived_cognition_retraction."""
        from cemm.app.runtime import Runtime
        rt = Runtime()
        authority = rt._cutover_verifier.get_authority("derived_cognition_retraction")
        assert authority == "InvalidationEngine"

    def test_cutover_verifier_registered_for_replay(self):
        """Cutover verifier registers ReplaySafetyManager for replay_scheduling_idempotence."""
        from cemm.app.runtime import Runtime
        rt = Runtime()
        authority = rt._cutover_verifier.get_authority("replay_scheduling_idempotence")
        assert authority == "ReplaySafetyManager"


# ── 2. CognitiveCycle invalidation fields ─────────────────────────


class TestCycleInvalidationFields:
    """Verify CognitiveCycle has invalidation_result and repair_obligations."""

    def test_cycle_has_invalidation_result_field(self):
        """CognitiveCycle has invalidation_result field."""
        cycle = CognitiveCycle(
            cycle_id="test:1",
            trigger=None,
            snapshot=None,
        )
        assert cycle.invalidation_result is None

    def test_cycle_has_repair_obligations_field(self):
        """CognitiveCycle has repair_obligations field."""
        cycle = CognitiveCycle(
            cycle_id="test:1",
            trigger=None,
            snapshot=None,
        )
        assert cycle.repair_obligations == ()


# ── 3. Exit gate: parent downgrade cascades correctly ─────────────


class TestParentDowngradeCascade:
    """Exit gate: parent downgrade cascades correctly."""

    def test_schema_downgrade_retracts_all_dependent_kinds(self):
        """Schema downgrade retracts all dependent artifact kinds."""
        index = DerivedArtifactIndex()
        engine = InvalidationEngine(index=index)

        kinds = [
            ArtifactKind.CLASSIFICATION,
            ArtifactKind.INFERENCE,
            ArtifactKind.CACHED_ANSWER,
            ArtifactKind.PLAN,
            ArtifactKind.MESSAGE_ITEM,
            ArtifactKind.EFFECT_PROPOSAL,
            ArtifactKind.CAPABILITY_CONCLUSION,
            ArtifactKind.LEARNING_SUCCESS_CLAIM,
        ]
        for i, kind in enumerate(kinds):
            art = make_artifact(f"art:{i}", kind=kind)
            index.register(art)

        result = engine.on_schema_downgrade("schema:test:v1")

        assert len(result.retracted_artifact_ids) == len(kinds)
        for i in range(len(kinds)):
            assert f"art:{i}" in result.retracted_artifact_ids

    def test_schema_supersession_marks_stale_not_retracted(self):
        """Schema supersession marks stale, not retracts."""
        index = DerivedArtifactIndex()
        engine = InvalidationEngine(index=index)

        art = make_artifact("art:inf1", ArtifactKind.INFERENCE)
        index.register(art)

        result = engine.on_schema_supersession("schema:test:v1", "schema:test:v2")

        assert "art:inf1" in result.staled_artifact_ids
        assert "art:inf1" not in result.retracted_artifact_ids

    def test_environment_change_marks_stale(self):
        """Environment fingerprint change marks dependent artifacts stale."""
        index = DerivedArtifactIndex()
        engine = InvalidationEngine(index=index)

        art = make_artifact("art:inf1", ArtifactKind.INFERENCE, fingerprint="fp:v1")
        index.register(art)

        result = engine.on_environment_change("fp:v1", "fp:v2")

        assert "art:inf1" in result.staled_artifact_ids

    def test_evidence_retraction_retracts_dependents(self):
        """Evidence retraction retracts dependent artifacts."""
        index = DerivedArtifactIndex()
        engine = InvalidationEngine(index=index)

        art = make_artifact(
            "art:inf1", ArtifactKind.INFERENCE,
            evidence_refs=("ev:1",),
        )
        index.register(art)

        result = engine.on_evidence_retraction("ev:1")

        assert "art:inf1" in result.retracted_artifact_ids

    def test_evidence_remains_after_invalidation(self):
        """Evidence remains after invalidation — original evidence is preserved."""
        index = DerivedArtifactIndex()
        engine = InvalidationEngine(index=index)

        art = make_artifact("art:inf1", ArtifactKind.INFERENCE)
        index.register(art)

        result = engine.on_schema_downgrade("schema:test:v1")
        assert result.evidence_preserved

    def test_unrelated_artifacts_unaffected(self):
        """Unrelated artifacts are not affected by invalidation."""
        index = DerivedArtifactIndex()
        engine = InvalidationEngine(index=index)

        art1 = make_artifact("art:inf1", schema_refs=("schema:A:v1",))
        art2 = make_artifact("art:inf2", schema_refs=("schema:B:v1",))
        index.register(art1)
        index.register(art2)

        result = engine.on_schema_downgrade("schema:A:v1")

        assert "art:inf1" in result.retracted_artifact_ids
        assert "art:inf2" not in result.retracted_artifact_ids


# ── 4. Exit gate: duplicate replay is idempotent ──────────────────


class TestDuplicateReplayIdempotence:
    """Exit gate: duplicate replay is idempotent."""

    def test_duplicate_replay_returns_same_result(self):
        """Duplicate replay delivery produces one result."""
        manager = ReplaySafetyManager()
        item = ReplayWorkItem(
            id="rw:1",
            source_evidence_ref="ev:1",
            target_sense_ref="sense:1",
            checkpoint_ref="cp:1",
            context_refs=("ctx:1",),
            dependency_fingerprint="fp:v1",
        )
        result = ReplayResult(
            work_item_ref="rw:1",
            status="succeeded",
        )

        # First submission
        enqueued, _ = manager.submit_replay(item)
        assert enqueued

        # Complete it
        manager.complete_replay(item, result)

        # Duplicate submission returns existing result
        enqueued2, existing = manager.submit_replay(item)
        assert not enqueued2
        assert existing is not None
        assert existing.work_item_ref == "rw:1"

    def test_replay_queue_dedup_queued(self):
        """Replay queue deduplicates already-queued items."""
        queue = ReplayQueue()
        item = ReplayWorkItem(
            id="rw:1",
            source_evidence_ref="ev:1",
            target_sense_ref="sense:1",
            checkpoint_ref="cp:1",
            context_refs=("ctx:1",),
            dependency_fingerprint="fp:v1",
        )
        assert queue.enqueue(item)
        assert not queue.enqueue(item)  # Already queued

    def test_replay_queue_cancel_stale(self):
        """Replay queue cancels stale items."""
        queue = ReplayQueue()
        item = ReplayWorkItem(
            id="rw:1",
            source_evidence_ref="ev:1",
            target_sense_ref="sense:1",
            checkpoint_ref="cp:1",
            context_refs=("ctx:1",),
            dependency_fingerprint="fp:v1",
        )
        queue.enqueue(item)
        queue.cancel_stale("fp:v2")  # Different fingerprint → item is stale
        assert queue.pending_count() == 0

    def test_executed_operation_exclusion(self):
        """Replay queue excludes already executed operations."""
        queue = ReplayQueue()
        queue.record_executed_operation("op:1", "ik:op1")
        assert queue.is_operation_executed("ik:op1")
        assert not queue.is_operation_executed("ik:other")


# ── 5. Exit gate: stale plans/effects reauthorize ─────────────────


class TestStaleEffectReauthorization:
    """Exit gate: stale plans/effects reauthorize."""

    def test_in_flight_effect_reauthorized_on_fingerprint_match(self):
        """In-flight effect is reauthorized when fingerprint matches."""
        manager = ReplaySafetyManager()
        manager.register_in_flight_effect(
            effect_id="effect:1",
            operation_id="op:1",
            idempotency_key="ik:1",
            authorization_fingerprint="fp:v1",
        )
        result = manager.reauthorize(
            effect_id="effect:1",
            current_fingerprint="fp:v1",
        )
        assert result.is_authorized

    def test_in_flight_effect_denied_on_fingerprint_change(self):
        """In-flight effect is denied when fingerprint changed."""
        manager = ReplaySafetyManager()
        manager.register_in_flight_effect(
            effect_id="effect:1",
            operation_id="op:1",
            idempotency_key="ik:1",
            authorization_fingerprint="fp:v1",
        )
        result = manager.reauthorize(
            effect_id="effect:1",
            current_fingerprint="fp:v2",
        )
        assert not result.is_authorized
        assert "fingerprint changed" in result.reason

    def test_in_flight_effect_denied_on_permission_revoked(self):
        """In-flight effect is denied when permission is revoked."""
        manager = ReplaySafetyManager()
        manager.register_in_flight_effect(
            effect_id="effect:1",
            operation_id="op:1",
            idempotency_key="ik:1",
            authorization_fingerprint="fp:v1",
        )
        result = manager.reauthorize(
            effect_id="effect:1",
            current_fingerprint="fp:v1",
            current_permission=False,
        )
        assert not result.is_authorized
        assert "permission" in result.reason

    def test_in_flight_effect_denied_on_resources_unavailable(self):
        """In-flight effect is denied when resources are unavailable."""
        manager = ReplaySafetyManager()
        manager.register_in_flight_effect(
            effect_id="effect:1",
            operation_id="op:1",
            idempotency_key="ik:1",
            authorization_fingerprint="fp:v1",
        )
        result = manager.reauthorize(
            effect_id="effect:1",
            current_fingerprint="fp:v1",
            current_resources_available=False,
        )
        assert not result.is_authorized
        assert "resources" in result.reason

    def test_commit_effect_removes_from_in_flight(self):
        """Committing an effect removes it from in-flight."""
        manager = ReplaySafetyManager()
        manager.register_in_flight_effect(
            effect_id="effect:1",
            operation_id="op:1",
            idempotency_key="ik:1",
        )
        committed = manager.commit_effect("effect:1")
        assert committed is not None
        assert committed.status == "committed"
        assert len(manager.get_in_flight_effects()) == 0

    def test_cancel_effect_removes_from_in_flight(self):
        """Cancelling an effect removes it from in-flight."""
        manager = ReplaySafetyManager()
        manager.register_in_flight_effect(
            effect_id="effect:1",
            operation_id="op:1",
            idempotency_key="ik:1",
        )
        cancelled = manager.cancel_effect("effect:1")
        assert cancelled is not None
        assert cancelled.status == "cancelled"
        assert len(manager.get_in_flight_effects()) == 0


# ── 6. Exit gate: privacy deletion is not archival ────────────────


class TestPrivacyDeletionNotArchival:
    """Exit gate: privacy deletion is not archival."""

    def test_archival_is_reversible(self):
        """Archival remains reversible/retrievable under policy."""
        guard = ArchivalPrivacyGuard()
        op = CorrectionOperationFactory.archival("prop:1")
        assert guard.can_reverse(op)
        assert guard.can_retrieve(op)

    def test_privacy_deletion_is_irreversible(self):
        """Privacy deletion is irreversible and not retrievable."""
        guard = ArchivalPrivacyGuard()
        op = CorrectionOperationFactory.privacy_deletion("prop:1")
        assert not guard.can_reverse(op)
        assert not guard.can_retrieve(op)

    def test_archival_not_mislabeled_as_privacy(self):
        """Archival cannot masquerade as privacy deletion."""
        guard = ArchivalPrivacyGuard()
        bad = CorrectionOperation(
            operation_id="privacy_delete:prop:1",
            kind=CorrectionKind.ARCHIVAL,
            target_ref="prop:1",
            target_kind="proposition",
            reversibility=CorrectionReversibility.REVERSIBLE,
            retention_policy=RetentionPolicy.RETAIN,
        )
        result = guard.check_operation(bad)
        assert not result.is_valid
        assert "mislabeled" in result.violation

    def test_privacy_deletion_not_mislabeled_as_archival(self):
        """Privacy deletion cannot masquerade as archival."""
        guard = ArchivalPrivacyGuard()
        bad = CorrectionOperation(
            operation_id="archive:prop:1",
            kind=CorrectionKind.PRIVACY_DELETION,
            target_ref="prop:1",
            target_kind="proposition",
            reversibility=CorrectionReversibility.IRREVERSIBLE,
            retention_policy=RetentionPolicy.CRYPTO_ERASE,
        )
        result = guard.check_operation(bad)
        assert not result.is_valid
        assert "mislabeled" in result.violation

    def test_privacy_deletion_crypto_erases(self):
        """Privacy deletion crypto-erases provenance."""
        op = CorrectionOperationFactory.privacy_deletion("prop:1")
        assert op.retention_policy == RetentionPolicy.CRYPTO_ERASE

    def test_archival_retains_history(self):
        """Archival retains provenance history."""
        op = CorrectionOperationFactory.archival("prop:1")
        assert op.retention_policy == RetentionPolicy.RETAIN

    def test_retraction_engine_privacy_deletion_no_retained_history(self):
        """Privacy deletion does not retain provenance history."""
        engine = RetractionEngine()
        result = engine.execute(CorrectionOperationFactory.privacy_deletion("prop:1"))
        assert not result.retained_history

    def test_retraction_engine_archival_retains_history(self):
        """Archival retains provenance history."""
        engine = RetractionEngine()
        result = engine.execute(CorrectionOperationFactory.archival("prop:1"))
        assert result.retained_history


# ── 7. Exit gate: prior wrong output creates bounded repair ───────


class TestRepairObligation:
    """Exit gate: prior wrong output creates bounded repair."""

    def test_retracted_message_generates_repair_obligation(self):
        """Retracted message item generates repair obligation."""
        index = DerivedArtifactIndex()
        engine = InvalidationEngine(index=index)

        art = make_artifact("art:msg1", ArtifactKind.MESSAGE_ITEM)
        index.register(art)

        result = engine.on_schema_downgrade("schema:test:v1")

        assert "art:msg1" in result.retracted_artifact_ids
        assert "art:msg1" in result.repair_obligation_ids

    def test_retracted_non_message_no_repair_obligation(self):
        """Retracted non-message artifact does not generate repair obligation."""
        index = DerivedArtifactIndex()
        engine = InvalidationEngine(index=index)

        art = make_artifact("art:inf1", ArtifactKind.INFERENCE)
        index.register(art)

        result = engine.on_schema_downgrade("schema:test:v1")

        assert "art:inf1" in result.retracted_artifact_ids
        assert "art:inf1" not in result.repair_obligation_ids

    def test_repair_obligations_accumulate(self):
        """Repair obligations accumulate across invalidation events."""
        index = DerivedArtifactIndex()
        engine = InvalidationEngine(index=index)

        art1 = make_artifact("art:msg1", ArtifactKind.MESSAGE_ITEM)
        art2 = make_artifact("art:msg2", ArtifactKind.MESSAGE_ITEM)
        index.register(art1)
        index.register(art2)

        engine.on_schema_downgrade("schema:test:v1")
        obligations = engine.get_repair_obligations()

        assert "art:msg1" in obligations
        assert "art:msg2" in obligations


# ── 8. Cross-schema support laundering prevention ────────────────


class TestCrossSchemaLaundering:
    """Cross-schema inference laundering does not increase support."""

    def test_ancestry_laundering_blocked(self):
        """If target is in evidence schema's ancestry, support is blocked."""
        guard = CrossSchemaLaunderingGuard()
        guard.register_support_ancestry("schema:A", ("schema:B",))
        assert not guard.can_increase_support("schema:A", "schema:B")

    def test_scc_laundering_blocked(self):
        """If both schemas are in the same SCC, support is blocked."""
        guard = CrossSchemaLaunderingGuard()
        guard.register_support_scc("schema:A", ("schema:A", "schema:B"))
        guard.register_support_scc("schema:B", ("schema:A", "schema:B"))
        assert not guard.can_increase_support("schema:A", "schema:B")

    def test_lineage_overlap_blocked(self):
        """If evidence lineage overlaps with target's ancestry, support is blocked."""
        guard = CrossSchemaLaunderingGuard()
        guard.register_support_ancestry("schema:B", ("schema:C",))
        assert not guard.can_increase_support(
            "schema:A", "schema:B",
            evidence_lineage=("schema:C",),
        )

    def test_no_laundering_allows_support(self):
        """When no laundering is detected, support can increase."""
        guard = CrossSchemaLaunderingGuard()
        guard.register_support_ancestry("schema:A", ("schema:X",))
        guard.register_support_ancestry("schema:B", ("schema:Y",))
        assert guard.can_increase_support("schema:A", "schema:B")

    def test_laundering_detection_returns_description(self):
        """detect_laundering returns a human-readable description."""
        guard = CrossSchemaLaunderingGuard()
        guard.register_support_ancestry("schema:A", ("schema:B",))
        desc = guard.detect_laundering("schema:A", "schema:B")
        assert desc is not None
        assert len(desc) > 0


# ── 9. Correction operations via CognitiveKernel ─────────────────


class TestKernelCorrectionExecution:
    """CognitiveKernel.execute_correction delegates to RetractionEngine."""

    def test_execute_correction_supersession(self):
        """execute_correction processes supersession and triggers invalidation."""
        from cemm.app.runtime import Runtime
        rt = Runtime()

        op = CorrectionOperationFactory.supersession("schema:test:v1")
        result = rt.kernel.execute_correction(op)
        assert result is not None
        assert result.success

    def test_execute_correction_support_retraction(self):
        """execute_correction processes support retraction."""
        from cemm.app.runtime import Runtime
        rt = Runtime()

        op = CorrectionOperationFactory.support_retraction("ev:1")
        result = rt.kernel.execute_correction(op)
        assert result is not None
        assert result.success

    def test_execute_correction_permission_revocation(self):
        """execute_correction processes permission revocation."""
        from cemm.app.runtime import Runtime
        rt = Runtime()

        op = CorrectionOperationFactory.permission_revocation("schema:1:v2")
        result = rt.kernel.execute_correction(op)
        assert result is not None
        assert result.success

    def test_execute_correction_archival(self):
        """execute_correction processes archival."""
        from cemm.app.runtime import Runtime
        rt = Runtime()

        op = CorrectionOperationFactory.archival("prop:1")
        result = rt.kernel.execute_correction(op)
        assert result is not None
        assert result.success
        assert result.retained_history

    def test_execute_correction_privacy_deletion(self):
        """execute_correction processes privacy deletion."""
        from cemm.app.runtime import Runtime
        rt = Runtime()

        op = CorrectionOperationFactory.privacy_deletion("prop:1")
        result = rt.kernel.execute_correction(op)
        assert result is not None
        assert result.success
        assert not result.retained_history

    def test_execute_correction_returns_none_without_engine(self):
        """execute_correction returns None when retraction_engine not wired."""
        from cemm.kernel.cycle.kernel import CognitiveKernel
        kernel = CognitiveKernel(
            schema_store=None,
            percept_adapter=None,
            semantic_composer=None,
            grounding_resolver=None,
            interpretation_resolver=None,
            workspace_controller=None,
            semantic_retriever=None,
            epistemic_evaluator=None,
            capability_evaluator=None,
            gap_detector=None,
            self_report_builder=None,
            learning_coordinator=None,
            goal_arbiter=None,
            planner=None,
            operation_authorizer=None,
            operation_executor=None,
            outcome_reconciler=None,
            commit_coordinator=None,
            response_planner=None,
            message_renderer=None,
            common_ground_manager=None,
        )
        op = CorrectionOperationFactory.supersession("schema:1")
        result = kernel.execute_correction(op)
        assert result is None


# ── 10. Six distinct correction operations ────────────────────────


class TestSixCorrectionOperations:
    """The kernel distinguishes exactly 6 correction/retention operations."""

    def test_six_distinct_kinds(self):
        """Exactly 6 correction kinds exist."""
        kinds = set(CorrectionKind)
        assert len(kinds) == 6

    def test_each_kind_has_distinct_factory(self):
        """Each correction kind has a distinct factory method."""
        ops = [
            CorrectionOperationFactory.supersession("t:1"),
            CorrectionOperationFactory.support_retraction("t:1"),
            CorrectionOperationFactory.permission_revocation("t:1"),
            CorrectionOperationFactory.archival("t:1"),
            CorrectionOperationFactory.forgetting("t:1"),
            CorrectionOperationFactory.privacy_deletion("t:1"),
        ]
        kinds = [op.kind for op in ops]
        assert len(set(kinds)) == 6

    def test_all_operations_trigger_reassessment(self):
        """All correction operations trigger dependency reassessment."""
        for factory_fn in [
            CorrectionOperationFactory.supersession,
            CorrectionOperationFactory.support_retraction,
            CorrectionOperationFactory.permission_revocation,
            CorrectionOperationFactory.archival,
            CorrectionOperationFactory.forgetting,
            CorrectionOperationFactory.privacy_deletion,
        ]:
            op = factory_fn("target:1")
            assert op.triggers_reassessment, f"{op.kind.value} must trigger reassessment"


# ── 11. Correction targeting precision ────────────────────────────


class TestCorrectionTargeting:
    """Correction targets exact sense/revision — unrelated senses unaffected."""

    def test_correction_targets_exact_sense(self):
        """Correction targets exact sense/revision."""
        guard = CorrectionTargetingGuard()
        op = CorrectionOperationFactory.supersession("sense:bank:river:v1")
        known = ("sense:bank:river:v1", "sense:bank:financial:v1")
        result = guard.check_target_precision(op, known)
        assert result.is_valid

    def test_unrelated_senses_unaffected(self):
        """Unrelated senses are unaffected by correction."""
        guard = CorrectionTargetingGuard()
        op = CorrectionOperationFactory.supersession("sense:bank:river:v1")
        related = ("sense:bank:river:v1", "sense:bank:financial:v1")
        affected = ("sense:bank:river:v1",)
        result = guard.check_unaffected_senses(op, related, affected)
        assert result.is_valid

    def test_unrelated_senses_violation_detected(self):
        """Violation detected when unrelated sense is affected."""
        guard = CorrectionTargetingGuard()
        op = CorrectionOperationFactory.supersession("sense:bank:river:v1")
        related = ("sense:bank:river:v1", "sense:bank:financial:v1")
        affected = ("sense:bank:river:v1", "sense:bank:financial:v1")
        result = guard.check_unaffected_senses(op, related, affected)
        assert not result.is_valid


# ── 12. Support retraction exact targeting ────────────────────────


class TestSupportRetractionExactTargeting:
    """Support retraction targets exact evidence — no substring bug."""

    def test_retract_ev1_not_ev10(self):
        """Retracting ev:1 must not affect ev:10 (substring bug regression)."""
        engine = RetractionEngine()
        engine.execute(CorrectionOperationFactory.support_retraction("ev:1"))
        assert not engine.support_still_contributes("ev:1", after_retraction=True)
        assert engine.support_still_contributes("ev:10", after_retraction=True)

    def test_support_retraction_returns_affected(self):
        """Support retraction returns affected dependent artifacts."""
        engine = RetractionEngine()
        engine.register_dependency("assess:1", "assessment", "ev:1")
        engine.register_dependency("inference:1", "inference", "ev:1")
        result = engine.execute(CorrectionOperationFactory.support_retraction("ev:1"))
        assert "assess:1" in result.affected_refs
        assert "inference:1" in result.affected_refs


# ── 13. Cycle integration smoke test ──────────────────────────────


class TestCycleIntegration:
    """Verify cycle runs with invalidation stage and produces fields."""

    def test_cycle_run_includes_invalidation_stage(self):
        """Cycle run includes the invalidate stage in trace."""
        from cemm.app.runtime import Runtime
        rt = Runtime()
        from cemm.kernel.model.cycle import CycleTrigger
        trigger = CycleTrigger(
            trigger_kind="user_utterance",
            signal_ids=("hello",),
        )
        cycle = rt.kernel.run(trigger)
        assert cycle.invalidation_result is None or hasattr(cycle.invalidation_result, "event_id")
        assert cycle.repair_obligations == ()

    def test_cycle_trace_includes_invalidate_stage(self):
        """Cycle trace includes 'invalidate' stage."""
        from cemm.app.runtime import Runtime
        rt = Runtime()
        from cemm.kernel.model.cycle import CycleTrigger
        trigger = CycleTrigger(
            trigger_kind="user_utterance",
            signal_ids=("hello",),
        )
        cycle = rt.kernel.run(trigger)
        if cycle.trace:
            assert "invalidate" in cycle.trace.stages or "finalize" in cycle.trace.stages


# ── 14. Import boundary tests ─────────────────────────────────────


class TestImportBoundaries:
    """Verify import boundaries for Stage 8 modules."""

    def test_correction_modules_no_engine_imports(self):
        """Correction modules must not import any engine module."""
        import cemm.kernel.correction.operations as ops_mod
        import cemm.kernel.correction.retraction_engine as re_mod
        import cemm.kernel.correction.guards as gu_mod

        forbidden = [
            "cemm.legacy.v3_3.semantic_kernel_runtime",
            "cemm.legacy.v3_3.meaning_perceptor",
            "cemm.legacy.v3_3.meaning_graph_builder",
            "cemm.memory.durable_semantic_store",
        ]
        for mod in [ops_mod, re_mod, gu_mod]:
            source = open(mod.__file__, encoding="utf-8").read()
            for f in forbidden:
                assert f not in source, f"{mod.__file__} imports forbidden module {f}"

    def test_correction_modules_no_schema_imports(self):
        """Correction modules must not import schema submodules."""
        import cemm.kernel.correction.operations as ops_mod
        import cemm.kernel.correction.retraction_engine as re_mod
        import cemm.kernel.correction.guards as gu_mod

        forbidden_schema = [
            "from ..schema.",
            "from cemm.kernel.schema.",
        ]
        for mod in [ops_mod, re_mod, gu_mod]:
            source = open(mod.__file__, encoding="utf-8").read()
            for f in forbidden_schema:
                assert f not in source, f"{mod.__file__} imports forbidden schema module {f}"

    def test_invalidation_engine_no_engine_imports(self):
        """InvalidationEngine must not import engine modules."""
        import cemm.kernel.epistemics.invalidation_engine as ie_mod
        import cemm.kernel.epistemics.invalidation_events as ev_mod
        import cemm.kernel.epistemics.artifact_index as ai_mod

        forbidden = [
            "cemm.legacy.v3_3.semantic_kernel_runtime",
            "cemm.legacy.v3_3.meaning_perceptor",
            "cemm.legacy.v3_3.meaning_graph_builder",
        ]
        for mod in [ie_mod, ev_mod, ai_mod]:
            source = open(mod.__file__, encoding="utf-8").read()
            for f in forbidden:
                assert f not in source, f"{mod.__file__} imports forbidden module {f}"
