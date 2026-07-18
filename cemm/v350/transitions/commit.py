"""Atomic Phase-11 effect patch construction and commit coordination."""
from __future__ import annotations

from hashlib import sha256
from typing import Iterable

from ..storage.codec import encode_record
from ..storage.model import (
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordDependency,
    RecordKind,
)
from ..storage.store import SemanticStore
from ..uol.model import EventOccurrence
from .model import CapabilityProjection, StateTimelineProjection, TransitionPreview


class EffectCommitError(ValueError):
    pass


class EffectCommitCoordinator:
    def __init__(self, store: SemanticStore) -> None:
        self._store = store

    def build_patch(
        self,
        event: EventOccurrence,
        preview: TransitionPreview,
        state_projections: tuple[StateTimelineProjection, ...],
        capability_projections: tuple[CapabilityProjection, ...],
        *,
        source_ref: str,
        permission_ref: str,
        expected_store_revision: int,
        expected_boot_fingerprint: str,
        expected_overlay_fingerprint: str,
    ) -> GraphPatch:
        if not preview.authorized or preview.proof is None:
            raise EffectCommitError("only an authorized proof-bearing transition preview can be committed")
        if self._store.revision != expected_store_revision:
            raise EffectCommitError("transition plan is stale: store revision changed")
        if self._store.boot_fingerprint != expected_boot_fingerprint:
            raise EffectCommitError("transition plan is stale: boot fingerprint changed")
        if self._store.overlay_fingerprint != expected_overlay_fingerprint:
            raise EffectCommitError("transition plan is stale: overlay fingerprint changed")
        operations: list[PatchOperation] = []

        event_stored = self._store.get_record(
            RecordKind.EVENT_OCCURRENCE, event.event_ref, preview.proof.event_revision
        )
        if event_stored is None or event_stored.payload != event:
            raise EffectCommitError("transition event must match the exact proof-pinned durable event revision")
        application_stored = self._store.get_record(
            RecordKind.SEMANTIC_APPLICATION,
            preview.proof.participant_application_ref,
            preview.proof.participant_application_revision,
        )
        if application_stored is None:
            raise EffectCommitError("transition participant application revision disappeared before commit")
        if event.participant_application_ref != preview.proof.participant_application_ref:
            raise EffectCommitError("transition proof pins a different participant application")
        contract_stored = self._store.get_record(
            RecordKind.TRANSITION_CONTRACT,
            preview.contract_ref,
            preview.contract_revision
        )
        if contract_stored is None:
            raise EffectCommitError("transition contract revision is unresolved at commit boundary")

        proof_dependencies = [
            RecordDependency(RecordKind.EVENT_OCCURRENCE, event.event_ref, preview.proof.event_revision, event_stored.record_fingerprint),
            RecordDependency(RecordKind.TRANSITION_CONTRACT, preview.contract_ref, contract_stored.revision, contract_stored.record_fingerprint),
            RecordDependency(
                RecordKind.SEMANTIC_APPLICATION, preview.proof.participant_application_ref,
                preview.proof.participant_application_revision, application_stored.record_fingerprint,
            ),
        ]
        for admission_ref, admission_revision in preview.proof.admission_pins:
            admission = self._store.get_record(RecordKind.EPISTEMIC_ADMISSION, admission_ref, admission_revision)
            if admission is None:
                raise EffectCommitError(f"transition admission disappeared before commit: {admission_ref}")
            proof_dependencies.append(RecordDependency(
                RecordKind.EPISTEMIC_ADMISSION,
                admission_ref,
                admission_revision,
                admission.record_fingerprint,
            ))
        for assignment_ref, assignment_revision in preview.proof.input_assignment_pins:
            assignment = self._store.get_record(RecordKind.STATE_ASSIGNMENT, assignment_ref, assignment_revision)
            if assignment is None:
                raise EffectCommitError(f"transition input state disappeared before commit: {assignment_ref}")
            proof_dependencies.append(RecordDependency(
                RecordKind.STATE_ASSIGNMENT,
                assignment_ref,
                assignment_revision,
                assignment.record_fingerprint,
            ))

        operations.append(PatchOperation(
            operation_ref=_ref("patch-op:transition-proof", preview.proof.proof_ref),
            operation_kind=PatchOperationKind.UPSERT,
            record_kind=RecordKind.TRANSITION_PROOF,
            target_ref=preview.proof.proof_ref,
            record_revision=1,
            payload=encode_record(RecordKind.TRANSITION_PROOF, preview.proof),
            dependencies=tuple(proof_dependencies),
            reason="proof-bearing admitted event transition",
        ))

        for delta in preview.state_deltas:
            deps = [
                RecordDependency(RecordKind.TRANSITION_PROOF, preview.proof.proof_ref, 1),
                RecordDependency(RecordKind.SCHEMA, delta.dimension_ref, delta.dimension_revision),
            ]
            for value_ref, revision in (
                (delta.from_value_ref, delta.from_value_revision),
                (delta.to_value_ref, delta.to_value_revision),
            ):
                if value_ref is not None and revision is not None:
                    deps.append(RecordDependency(RecordKind.SCHEMA, value_ref, revision))
            operations.append(PatchOperation(
                operation_ref=_ref("patch-op:state-delta", delta.delta_ref),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.STATE_DELTA,
                target_ref=delta.delta_ref,
                record_revision=1,
                payload=encode_record(RecordKind.STATE_DELTA, delta),
                dependencies=tuple(deps),
                reason="validated state effect from transition contract",
            ))

        for projection in state_projections:
            for mutation in projection.mutations:
                source_delta = next((item for item in preview.state_deltas if (
                    item.holder_ref == projection.holder_ref
                    and item.dimension_ref == projection.dimension_ref
                    and item.context_ref == projection.context_ref
                )), None)
                if source_delta is None:
                    raise EffectCommitError("state projection has no corresponding transition delta")
                operations.append(PatchOperation(
                    operation_ref=_ref("patch-op:state-assignment", mutation.assignment_ref, str(mutation.record_revision)),
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=RecordKind.STATE_ASSIGNMENT,
                    target_ref=mutation.assignment_ref,
                    record_revision=mutation.record_revision,
                    expected_record_revision=mutation.expected_record_revision,
                    payload=encode_record(RecordKind.STATE_ASSIGNMENT, mutation.projected),
                    dependencies=(RecordDependency(RecordKind.STATE_DELTA, source_delta.delta_ref, 1),),
                    reason="projected immutable state timeline update",
                ))

        seen_capability_targets: set[tuple[str, str, str]] = set()
        for projection in capability_projections:
            delta = projection.delta
            key = (delta.holder_ref, delta.action_schema_ref, delta.context_ref)
            if key in seen_capability_targets:
                raise EffectCommitError("multiple capability projections target the same holder/action in one atomic patch")
            seen_capability_targets.add(key)
            dependency = self._store.get_record(RecordKind.CAPABILITY_DEPENDENCY, delta.dependency_ref)
            if dependency is None:
                raise EffectCommitError("capability dependency disappeared before commit")
            operations.append(PatchOperation(
                operation_ref=_ref("patch-op:capability-delta", delta.delta_ref),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.CAPABILITY_DELTA,
                target_ref=delta.delta_ref,
                record_revision=1,
                payload=encode_record(RecordKind.CAPABILITY_DELTA, delta),
                dependencies=(
                    RecordDependency(RecordKind.TRANSITION_PROOF, preview.proof.proof_ref, 1),
                    RecordDependency(RecordKind.CAPABILITY_DEPENDENCY, delta.dependency_ref, dependency.revision, dependency.record_fingerprint),
                ),
                reason="capability dependency reevaluation from projected state",
            ))
            operations.append(PatchOperation(
                operation_ref=_ref("patch-op:capability-instance", projection.projected_instance.capability_ref, str(projection.record_revision)),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.CAPABILITY_INSTANCE,
                target_ref=projection.projected_instance.capability_ref,
                record_revision=projection.record_revision,
                expected_record_revision=projection.expected_record_revision,
                payload=encode_record(RecordKind.CAPABILITY_INSTANCE, projection.projected_instance),
                dependencies=(RecordDependency(RecordKind.CAPABILITY_DELTA, delta.delta_ref, 1),),
                reason="projected capability instance update",
            ))

        return GraphPatch(
            patch_ref=_ref("patch:transition-effects", event.event_ref, preview.proof.proof_ref),
            context_ref=event.context_ref,
            scope_ref="transition-effects",
            source_ref=source_ref,
            permission_ref=permission_ref,
            operations=tuple(operations),
            expected_store_revision=expected_store_revision,
            evidence_refs=preview.proof.evidence_refs,
            validation_requirements=(
                "exact_transition_contract_revision",
                "independent_active_epistemic_admission",
                "state_entitlement_and_value_domain",
                "capability_dependency_revalidation",
                "atomic_compare_and_swap",
            ),
            rollback_hint="append/revise compensating semantic records; never erase transition proof lineage",
            metadata={
                "event_ref": event.event_ref,
                "transition_contract_ref": preview.contract_ref,
                "transition_contract_revision": preview.contract_revision,
            },
        )

    def commit(self, patch: GraphPatch):
        return self._store.apply_patch(patch)


def _ref(prefix: str, *parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}:{sha256(payload).hexdigest()[:24]}"
