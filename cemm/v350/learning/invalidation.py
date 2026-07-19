"""Explicit lineage-aware invalidation, retraction, and recomputation frontiers."""
from __future__ import annotations

from dataclasses import replace

from ..schema.model import SchemaClass, semantic_fingerprint
from ..storage.codec import encode_record, record_fingerprints, record_ref, record_revision
from ..storage.model import (
    DependencyEdge,
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordDependency,
    RecordKind,
)
from .model import (
    FrontierResolutionStatus,
    InvalidationStatus,
    LearningFrontierRecord,
    LearningInvalidationRecord,
    LearningPackageRecord,
    LearningPackageStatus,
    PinnedRecord,
    PromotionDecisionRecord,
)


_AUTO_DERIVED = {
    RecordKind.KNOWLEDGE,
    RecordKind.STATE_ASSIGNMENT,
    RecordKind.STATE_DELTA,
    RecordKind.CAPABILITY_INSTANCE,
    RecordKind.CAPABILITY_DELTA,
    RecordKind.TRANSITION_PROOF,
    RecordKind.COMPETENCE_RESULT,
    RecordKind.PROMOTION_DECISION,
    RecordKind.IMPACT_PROOF,
    RecordKind.SIGNIFICANCE_ASSESSMENT,
    RecordKind.SEMANTIC_OBLIGATION,
    RecordKind.GOAL_CANDIDATE,
    RecordKind.GOAL_CONFLICT,
    RecordKind.GOAL_DECISION,
}


class LearningInvalidationManager:
    def __init__(self, store) -> None:
        self.store = store

    def plan(
        self,
        trigger_pins: tuple[PinnedRecord, ...],
        *,
        reason: str,
        evidence_refs: tuple[str, ...],
        context_ref: str = "actual",
        permission_ref: str = "internal",
    ) -> tuple[LearningInvalidationRecord, tuple[LearningFrontierRecord, ...], tuple[PinnedRecord, ...]]:
        dependent_affected, replay = self._dependent_closure(trigger_pins)
        explicit_revocations = tuple(
            pin for pin in trigger_pins
            if pin.record_kind in {RecordKind.LEARNING_PACKAGE, RecordKind.PROMOTION_DECISION, RecordKind.COMPETENCE_RESULT}
        )
        affected_by_key = {pin.key: pin for pin in (*explicit_revocations, *dependent_affected)}
        affected = tuple(affected_by_key[key] for key in sorted(affected_by_key))
        packages: set[str] = set()
        decisions: set[str] = set()
        for pin in affected:
            if pin.record_kind == RecordKind.LEARNING_PACKAGE:
                packages.add(pin.record_ref)
            elif pin.record_kind == RecordKind.PROMOTION_DECISION:
                decisions.add(pin.record_ref)
        frontiers = []
        for pin in affected:
            if pin.record_kind in {RecordKind.COMPETENCE_RESULT, RecordKind.PROMOTION_DECISION, RecordKind.LEARNING_PACKAGE}:
                frontier_ref = "learning-frontier:recompute:" + semantic_fingerprint(
                    "learning-recompute-frontier", (pin.key, reason, context_ref), 24
                )
                frontiers.append(LearningFrontierRecord(
                    frontier_ref=frontier_ref,
                    target_ref=pin.record_ref,
                    missing_contract="dependency_revalidation",
                    expected_record_kinds=(pin.record_kind,),
                    expected_schema_classes=(),
                    accepted_anchor_types=(),
                    evidence_refs=evidence_refs,
                    candidate_refs=(),
                    resolution_status=FrontierResolutionStatus.OPEN,
                    context_ref=context_ref,
                    permission_ref=permission_ref,
                    metadata={"affected_revision": pin.revision, "affected_fingerprint": pin.record_fingerprint},
                ))
        invalidation_ref = "learning-invalidation:" + semantic_fingerprint(
            "learning-invalidation-ref",
            (
                tuple(pin.key + (pin.record_fingerprint,) for pin in trigger_pins),
                tuple(pin.key + (pin.record_fingerprint,) for pin in affected),
                reason,
            ),
            24,
        )
        record = LearningInvalidationRecord(
            invalidation_ref=invalidation_ref,
            trigger_pins=trigger_pins,
            affected_pins=affected,
            package_refs=tuple(sorted(packages)),
            invalidated_decision_refs=tuple(sorted(decisions)),
            recomputation_frontier_refs=tuple(sorted(item.frontier_ref for item in frontiers)),
            replay_required_refs=tuple(sorted(replay)),
            reason=reason,
            status=(InvalidationStatus.RECOMPUTATION_REQUIRED if frontiers or replay else InvalidationStatus.APPLIED),
            evidence_refs=tuple(sorted(set(evidence_refs))),
            proof_refs=(),
            context_ref=context_ref,
            permission_ref=permission_ref,
        )
        return record, tuple(frontiers), affected

    def apply(self, invalidation: LearningInvalidationRecord, frontiers: tuple[LearningFrontierRecord, ...]):
        with self.store.snapshot() as snapshot:
            operations: list[PatchOperation] = []
            trigger_dependencies = [
                RecordDependency(
                    pin.record_kind, pin.record_ref, pin.revision, pin.record_fingerprint,
                    "invalidation_trigger",
                )
                for pin in invalidation.trigger_pins
            ]
            for evidence_ref in invalidation.evidence_refs:
                stored_evidence = self.store.get_record(RecordKind.EVIDENCE, evidence_ref)
                if stored_evidence is not None:
                    trigger_dependencies.append(RecordDependency(
                        RecordKind.EVIDENCE, evidence_ref, stored_evidence.revision,
                        stored_evidence.record_fingerprint, "invalidation_evidence",
                    ))
            invalidation_fp = record_fingerprints(RecordKind.LEARNING_INVALIDATION, invalidation)[1]
            operations.append(self._upsert(
                RecordKind.LEARNING_INVALIDATION,
                invalidation,
                "persist exact invalidation lineage",
                dependencies=tuple(trigger_dependencies),
            ))
            for frontier in frontiers:
                operations.append(self._upsert(
                    RecordKind.LEARNING_FRONTIER,
                    frontier,
                    "preserve recomputation frontier",
                    dependencies=(RecordDependency(
                        RecordKind.LEARNING_INVALIDATION, invalidation.invalidation_ref, invalidation.revision,
                        invalidation_fp, "invalidation_frontier",
                    ),),
                ))

            handled_packages: set[str] = set()
            handled_targets: set[tuple[RecordKind, str]] = set()
            for pin in invalidation.affected_pins:
                if pin.record_kind == RecordKind.LEARNING_PACKAGE:
                    if pin.record_ref in handled_packages:
                        continue
                    handled_packages.add(pin.record_ref)
                    latest = self.store.get_record(RecordKind.LEARNING_PACKAGE, pin.record_ref)
                    if latest is None or not isinstance(latest.payload, LearningPackageRecord):
                        continue
                    package = latest.payload
                    if package.lifecycle_status in {
                        LearningPackageStatus.RETRACTED, LearningPackageStatus.SUPERSEDED,
                        LearningPackageStatus.INVALIDATED, LearningPackageStatus.REJECTED,
                    }:
                        continue
                    invalidated = replace(
                        package,
                        revision=package.revision + 1,
                        supersedes_revision=package.revision,
                        lifecycle_status=LearningPackageStatus.INVALIDATED,
                        metadata={**dict(package.metadata), "invalidation_ref": invalidation.invalidation_ref},
                    )
                    operations.append(self._upsert(
                        RecordKind.LEARNING_PACKAGE, invalidated,
                        "invalidate package authority after dependency change",
                        expected_revision=package.revision,
                        expected_fingerprint=latest.record_fingerprint,
                        dependencies=(RecordDependency(
                            RecordKind.LEARNING_INVALIDATION, invalidation.invalidation_ref, invalidation.revision,
                            invalidation_fp, "learning_invalidation",
                        ),),
                    ))
                    continue

                target_key = (pin.record_kind, pin.record_ref)
                if target_key in handled_targets:
                    continue
                handled_targets.add(target_key)
                latest = self.store.get_record(pin.record_kind, pin.record_ref)
                # Historical revisions remain immutable audit history. Only the
                # exact currently effective/latest derived revision is revoked.
                if (
                    latest is None
                    or latest.revision != pin.revision
                    or latest.record_fingerprint != pin.record_fingerprint
                ):
                    continue
                if pin.record_kind == RecordKind.MATERIALIZED_VIEW:
                    operations.append(PatchOperation(
                        operation_ref="patch-operation:learning-invalidate-view:" + semantic_fingerprint("invalidate-view", pin.key, 20),
                        operation_kind=PatchOperationKind.INVALIDATE,
                        record_kind=pin.record_kind,
                        target_ref=pin.record_ref,
                        record_revision=pin.revision,
                        expected_record_revision=pin.revision,
                        expected_record_fingerprint=pin.record_fingerprint,
                        dependencies=(RecordDependency(
                            RecordKind.LEARNING_INVALIDATION, invalidation.invalidation_ref, invalidation.revision,
                            invalidation_fp, "learning_invalidation",
                        ),),
                        reason="dependency changed; materialized view must recompute",
                    ))
                elif pin.record_kind in _AUTO_DERIVED or self._is_promoted_authority(pin):
                    operations.append(PatchOperation(
                        operation_ref="patch-operation:learning-tombstone:" + semantic_fingerprint("learning-tombstone", pin.key, 20),
                        operation_kind=PatchOperationKind.TOMBSTONE,
                        record_kind=pin.record_kind,
                        target_ref=pin.record_ref,
                        record_revision=pin.revision,
                        expected_record_revision=pin.revision,
                        expected_record_fingerprint=pin.record_fingerprint,
                        dependencies=(RecordDependency(
                            RecordKind.LEARNING_INVALIDATION, invalidation.invalidation_ref, invalidation.revision,
                            invalidation_fp, "learning_invalidation",
                        ),),
                        reason="explicit dependency invalidation; preserve historical row behind tombstone",
                    ))
            patch = GraphPatch(
                patch_ref="graph-patch:learning-invalidation:" + semantic_fingerprint(
                    "learning-invalidation-patch", (invalidation.invalidation_ref, snapshot.fingerprint), 24
                ),
                context_ref=invalidation.context_ref,
                scope_ref="learning:invalidation",
                source_ref="source:phase13:invalidation-manager",
                permission_ref=invalidation.permission_ref,
                operations=tuple(operations),
                expected_store_revision=snapshot.store_revision,
                evidence_refs=invalidation.evidence_refs,
                validation_requirements=("phase13_explicit_invalidation", "preserve_history"),
                metadata={"phase": 13, "invalidation_ref": invalidation.invalidation_ref},
            )
        return self.store.apply_patch(patch)

    def _dependent_closure(self, triggers: tuple[PinnedRecord, ...]) -> tuple[tuple[PinnedRecord, ...], tuple[str, ...]]:
        edges = tuple(
            stored.payload for stored in self.store.records(RecordKind.DEPENDENCY, all_revisions=True)
            if isinstance(stored.payload, DependencyEdge) and stored.payload.active
        )
        frontier = list(triggers)
        seen = {pin.key for pin in triggers}
        affected: dict[tuple[str, str, int], PinnedRecord] = {}
        replay_required: set[str] = set()
        while frontier:
            prerequisite = frontier.pop(0)
            for edge in edges:
                if edge.prerequisite_ref != prerequisite.record_ref:
                    continue
                if edge.prerequisite_kind is not None and edge.prerequisite_kind != prerequisite.record_kind:
                    continue
                if edge.prerequisite_revision is not None and edge.prerequisite_revision != prerequisite.revision:
                    continue
                if edge.prerequisite_fingerprint is not None and edge.prerequisite_fingerprint != prerequisite.record_fingerprint:
                    continue
                stored = self.store.get_record(edge.dependent_kind, edge.dependent_ref, edge.dependent_revision)
                if stored is None:
                    continue
                pin = PinnedRecord(edge.dependent_kind, edge.dependent_ref, edge.dependent_revision, stored.record_fingerprint)
                if pin.key in seen:
                    continue
                seen.add(pin.key)
                affected[pin.key] = pin
                frontier.append(pin)
                if pin.record_kind in {
                    RecordKind.TRANSITION_PROOF, RecordKind.STATE_DELTA, RecordKind.STATE_ASSIGNMENT,
                    RecordKind.CAPABILITY_DELTA, RecordKind.CAPABILITY_INSTANCE,
                }:
                    replay_required.add(pin.record_ref)
        return tuple(affected[key] for key in sorted(affected)), tuple(sorted(replay_required))

    def _is_promoted_authority(self, pin: PinnedRecord) -> bool:
        # Only records whose dependency lineage explicitly includes a promotion
        # decision are automatically revoked. Reviewed boot authority is never
        # deleted merely because it shares a reference with learned material.
        for stored in self.store.records(RecordKind.DEPENDENCY, all_revisions=True):
            edge = stored.payload
            if not isinstance(edge, DependencyEdge) or not edge.active:
                continue
            if edge.dependent_kind != pin.record_kind or edge.dependent_ref != pin.record_ref or edge.dependent_revision != pin.revision:
                continue
            if edge.prerequisite_kind == RecordKind.PROMOTION_DECISION or edge.dependency_kind.startswith("promotion"):
                return True
        return False

    @staticmethod
    def _upsert(
        kind: RecordKind, record, reason: str, *, expected_revision=None,
        expected_fingerprint=None, dependencies: tuple[RecordDependency, ...] = (),
    ) -> PatchOperation:
        return PatchOperation(
            operation_ref="patch-operation:learning-invalidation-upsert:" + semantic_fingerprint(
                "learning-invalidation-upsert", (kind.value, record_ref(kind, record), record_revision(kind, record)), 20
            ),
            operation_kind=PatchOperationKind.UPSERT,
            record_kind=kind,
            target_ref=record_ref(kind, record),
            record_revision=record_revision(kind, record),
            payload=encode_record(kind, record),
            expected_record_revision=expected_revision,
            expected_record_fingerprint=expected_fingerprint,
            dependencies=dependencies,
            reason=reason,
        )


class LearningRetractionCoordinator:
    def __init__(self, store) -> None:
        self.store = store
        self.invalidations = LearningInvalidationManager(store)

    def retract_package(self, package_ref: str, *, evidence_refs: tuple[str, ...], reason: str):
        stored = self.store.get_record(RecordKind.LEARNING_PACKAGE, package_ref)
        if stored is None or not isinstance(stored.payload, LearningPackageRecord):
            raise KeyError(package_ref)
        package = stored.payload
        triggers = [PinnedRecord(RecordKind.LEARNING_PACKAGE, package_ref, stored.revision, stored.record_fingerprint)]
        for decision_stored in self.store.records(RecordKind.PROMOTION_DECISION, all_revisions=True):
            decision = decision_stored.payload
            if isinstance(decision, PromotionDecisionRecord) and decision.package_ref == package_ref:
                triggers.append(PinnedRecord(
                    RecordKind.PROMOTION_DECISION, decision.decision_ref, decision_stored.revision,
                    decision_stored.record_fingerprint,
                ))
        invalidation, frontiers, _ = self.invalidations.plan(
            tuple(triggers), reason=reason, evidence_refs=evidence_refs, permission_ref=package.permission_ref
        )
        return self.invalidations.apply(invalidation, frontiers)
