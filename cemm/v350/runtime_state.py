"""Phase-6 runtime-backed self state and capability observation.

Only mechanical runtime signals are admitted. Reviewed schema metadata maps those
signals into semantic state/capability records. The observer never infers health,
connectivity, availability, emotion, or other conversationally convenient state.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .identity import IdempotencyOutcome, classify_persisted_identity
from .schema.model import ActionSchema, StateDimensionSchema, semantic_fingerprint
from .storage import (
    EvidenceRecord,
    GraphPatch,
    PatchOperation,
    PatchOperationKind,
    RecordKind,
    SemanticStore,
    encode_record,
)
from .storage.model import AssignmentStatus, CapabilityInstance, CapabilityStatus, StateAssignment


@dataclass(frozen=True, slots=True)
class RuntimeSignal:
    signal_ref: str
    value: str
    confidence: float = 1.0
    evidence_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.signal_ref.strip() or not self.value.strip():
            raise ValueError("runtime signal requires signal_ref and value")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("runtime signal confidence must be within [0,1]")


_VOLATILE_RUNTIME_METADATA = frozenset({
    "observed_at",
    "observed_time",
    "timestamp",
    "collected_at",
    "request_id",
    "cycle_ref",
    "trace_ref",
})


def _stable_runtime_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Exclude request-frequency occurrence fields from durable snapshot identity."""
    return {
        str(key): value
        for key, value in metadata.items()
        if str(key) not in _VOLATILE_RUNTIME_METADATA
    }


class RuntimeSelfObserver:
    """Persist mechanically observed self state/capabilities before Stage 0.

    State assignments are immutable observations. When a reviewed exclusive
    dimension changes, the prior current assignment is tombstoned in the writable
    overlay before the new observation is written, preventing contradictory
    simultaneous current values while preserving patch/audit history.
    """

    def __init__(self, store: SemanticStore, services) -> None:
        self.store = store
        self.services = services

    def observe(self, *, context_ref: str, permission_ref: str = "conversation"):
        signals = self._signals()
        if not signals:
            return None
        signal_map = {item.signal_ref: item for item in signals}
        registry = self.store.repositories.schemas.registry()
        operations: list[PatchOperation] = []
        source_ref = "source:runtime-self-observer"
        evidence_by_signal: dict[str, str] = {}

        for signal in signals:
            stable_metadata = _stable_runtime_metadata(signal.metadata)
            evidence_ref = "evidence:runtime-signal:" + semantic_fingerprint(
                "runtime-signal-evidence",
                (signal.signal_ref, signal.value, context_ref, stable_metadata),
                24,
            )
            evidence = EvidenceRecord(
                evidence_ref=evidence_ref,
                source_ref=source_ref,
                confidence=signal.confidence,
                lineage_ref=source_ref,
                context_ref=context_ref,
                permission_ref=permission_ref,
                metadata={
                    "runtime_signal_ref": signal.signal_ref,
                    "value": signal.value,
                    "source_evidence_refs": tuple(signal.evidence_refs),
                    **stable_metadata,
                },
            )
            evidence_by_signal[signal.signal_ref] = evidence_ref
            existing = self.store.get_record(RecordKind.EVIDENCE, evidence_ref)
            if existing is None:
                operations.append(PatchOperation(
                    operation_ref="patch-operation:runtime-signal:" + semantic_fingerprint(
                        "runtime-signal-op", evidence_ref, 20
                    ),
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=RecordKind.EVIDENCE,
                    target_ref=evidence_ref,
                    record_revision=1,
                    payload=encode_record(RecordKind.EVIDENCE, evidence),
                    reason="persist mechanical runtime signal before Stage 0",
                ))
            elif classify_persisted_identity(
                existing, RecordKind.EVIDENCE, evidence, revision=1
            ).outcome is IdempotencyOutcome.CONFLICT:
                raise RuntimeError(
                    f"deterministic runtime evidence identity collision:{evidence_ref}"
                )

        # State dimensions opt in explicitly. A signal-to-value mapping is reviewed
        # semantic authority; the observer itself knows no state vocabulary.
        for schema in registry.iter_schemas():
            if not isinstance(schema, StateDimensionSchema):
                continue
            matches = []
            for binding in tuple(schema.metadata.get("runtime_state_bindings", ())):
                signal = signal_map.get(str(binding.get("signal_ref", "")))
                if signal is None or str(binding.get("signal_value", "")) != signal.value:
                    continue
                value_ref = str(binding.get("state_value_ref", ""))
                value_revision = int(binding.get("state_value_revision", 0) or 0)
                if not value_ref or value_revision < 1:
                    raise ValueError(
                        f"invalid runtime state binding:{schema.schema_ref}@{schema.revision}"
                    )
                # Exact value pin must exist and belong to this dimension.
                value_schema = registry.schema(value_ref, value_revision)
                if getattr(value_schema, "dimension_ref", None) != schema.schema_ref:
                    raise ValueError(
                        f"runtime state binding value outside dimension:{value_ref}"
                    )
                semantic_context_ref = str(binding.get("context_ref", context_ref) or context_ref)
                matches.append((signal, value_ref, value_revision, semantic_context_ref))
            if len(matches) > 1:
                raise ValueError(
                    f"ambiguous runtime state bindings:{schema.schema_ref}@{schema.revision}"
                )
            if not matches:
                continue
            signal, value_ref, value_revision, semantic_context_ref = matches[0]
            evidence_ref = evidence_by_signal[signal.signal_ref]
            current = [
                stored
                for stored in self.store.repositories.state_assignments.all(all_revisions=True)
                if stored.payload.holder_ref == "referent:self"
                and stored.payload.dimension_ref == schema.schema_ref
                and stored.payload.dimension_revision == schema.revision
                and stored.payload.context_ref == semantic_context_ref
                and stored.payload.status == AssignmentStatus.ACTIVE
            ]
            same = [item for item in current if item.payload.value_ref == value_ref and item.payload.value_revision == value_revision]
            if same:
                continue
            if schema.exclusive:
                for stored in current:
                    operations.append(PatchOperation(
                        operation_ref="patch-operation:runtime-state-retire:" + semantic_fingerprint(
                            "runtime-state-retire",
                            (stored.record_ref, stored.revision, evidence_ref),
                            20,
                        ),
                        operation_kind=PatchOperationKind.TOMBSTONE,
                        record_kind=RecordKind.STATE_ASSIGNMENT,
                        target_ref=stored.record_ref,
                        record_revision=stored.revision,
                        reason="replace prior exclusive runtime state with newer mechanical observation",
                    ))
            assignment_ref = "state-assignment:runtime:self:" + semantic_fingerprint(
                "runtime-self-state-observation",
                (schema.schema_ref, schema.revision, value_ref, value_revision, semantic_context_ref, evidence_ref),
                24,
            )
            assignment = StateAssignment(
                assignment_ref=assignment_ref,
                holder_ref="referent:self",
                dimension_ref=schema.schema_ref,
                dimension_revision=schema.revision,
                value_ref=value_ref,
                value_revision=value_revision,
                status=AssignmentStatus.ACTIVE,
                context_ref=semantic_context_ref,
                confidence=signal.confidence,
                evidence_refs=(evidence_ref,),
                source_refs=(source_ref,),
            )
            existing = self.store.get_record(RecordKind.STATE_ASSIGNMENT, assignment_ref)
            if existing is None:
                operations.append(PatchOperation(
                    operation_ref="patch-operation:runtime-state:" + semantic_fingerprint(
                        "runtime-state-op", assignment_ref, 20
                    ),
                    operation_kind=PatchOperationKind.UPSERT,
                    record_kind=RecordKind.STATE_ASSIGNMENT,
                    target_ref=assignment_ref,
                    record_revision=1,
                    payload=encode_record(RecordKind.STATE_ASSIGNMENT, assignment),
                    reason="map mechanical runtime signal through reviewed state binding",
                ))
            elif classify_persisted_identity(
                existing, RecordKind.STATE_ASSIGNMENT, assignment, revision=1
            ).outcome is IdempotencyOutcome.CONFLICT:
                raise RuntimeError(
                    f"deterministic runtime state identity collision:{assignment_ref}"
                )

        # Capabilities also require explicit reviewed signal/status mappings. We do
        # not infer an action is executable merely because a Python class exists.
        for schema in registry.iter_schemas():
            if not isinstance(schema, ActionSchema):
                continue
            bindings = tuple(schema.metadata.get("runtime_capability_bindings", ()))
            matches = []
            for binding in bindings:
                signal = signal_map.get(str(binding.get("signal_ref", "")))
                if signal is None or str(binding.get("signal_value", "")) != signal.value:
                    continue
                try:
                    status = CapabilityStatus(str(binding.get("capability_status", "unknown")))
                except ValueError as exc:
                    raise ValueError(
                        f"invalid capability status binding:{schema.schema_ref}"
                    ) from exc
                semantic_context_ref = str(binding.get("context_ref", context_ref) or context_ref)
                matches.append((signal, status, semantic_context_ref))
            if len(matches) > 1:
                raise ValueError(
                    f"ambiguous runtime capability bindings:{schema.schema_ref}@{schema.revision}"
                )
            if not matches:
                continue
            signal, status, semantic_context_ref = matches[0]
            evidence_ref = evidence_by_signal[signal.signal_ref]
            capability_ref = "capability:runtime:self:" + semantic_fingerprint(
                "runtime-self-capability", (schema.schema_ref, schema.revision, semantic_context_ref), 24
            )
            existing = self.store.get_record(RecordKind.CAPABILITY_INSTANCE, capability_ref)
            if (
                existing is not None
                and existing.payload.status == status
                and existing.payload.action_schema_ref == schema.schema_ref
                and existing.payload.action_schema_revision == schema.revision
                and existing.payload.context_ref == semantic_context_ref
            ):
                continue
            revision = 1 if existing is None else existing.revision + 1
            capability = CapabilityInstance(
                capability_ref=capability_ref,
                holder_ref="referent:self",
                action_schema_ref=schema.schema_ref,
                action_schema_revision=schema.revision,
                status=status,
                confidence=signal.confidence,
                context_ref=semantic_context_ref,
                revision=revision,
                supersedes_revision=None if revision == 1 else revision - 1,
                evidence_refs=(evidence_ref,),
            )
            operations.append(PatchOperation(
                operation_ref="patch-operation:runtime-capability:" + semantic_fingerprint(
                    "runtime-capability-op", (capability_ref, revision, status.value), 20
                ),
                operation_kind=PatchOperationKind.UPSERT,
                record_kind=RecordKind.CAPABILITY_INSTANCE,
                target_ref=capability_ref,
                record_revision=revision,
                payload=encode_record(RecordKind.CAPABILITY_INSTANCE, capability),
                reason="map mechanical runtime signal through reviewed capability binding",
            ))

        if not operations:
            return None
        with self.store.snapshot() as snapshot:
            patch = GraphPatch(
                patch_ref="graph-patch:runtime-self:" + semantic_fingerprint(
                    "runtime-self-patch",
                    (
                        snapshot.fingerprint,
                        tuple((s.signal_ref, s.value) for s in signals),
                        tuple(op.operation_ref for op in operations),
                    ),
                    24,
                ),
                context_ref=context_ref,
                scope_ref="runtime:self-observation",
                source_ref=source_ref,
                permission_ref=permission_ref,
                operations=tuple(operations),
                expected_store_revision=snapshot.store_revision,
                validation_requirements=(
                    "mechanical_runtime_evidence_only",
                    "defaults_not_facts",
                    "exclusive_current_state_not_duplicated",
                ),
            )
        result = self.store.apply_patch(patch)
        if not result.committed:
            raise RuntimeError(
                "runtime self observation commit failed: " + "; ".join(result.errors)
            )
        return result

    def _signals(self) -> tuple[RuntimeSignal, ...]:
        # Reaching Runtime.run_text with an initialized canonical orchestrator is
        # mechanically sufficient only for this narrow signal. It says nothing
        # about network, emotional state, health, or external service availability.
        runtime_metadata = {}
        epoch_ref = getattr(self.services, "runtime_epoch_ref", None)
        attestation_ref = getattr(self.services, "runtime_attestation_ref", None)
        authority_generation = getattr(
            self.services, "runtime_authority_generation", None
        )
        if epoch_ref:
            runtime_metadata["runtime_epoch_ref"] = epoch_ref
        if attestation_ref:
            runtime_metadata["runtime_attestation_ref"] = attestation_ref
        if authority_generation is not None:
            runtime_metadata["runtime_authority_generation"] = int(
                authority_generation
            )
        result = [
            RuntimeSignal(
                "runtime:core-loop",
                "operational",
                metadata=runtime_metadata,
            )
        ]
        provider = getattr(self.services, "runtime_signal_provider", None)
        if provider is not None:
            provider_ref = str(getattr(provider, "provider_ref", "") or "")
            provider_revision = str(getattr(provider, "provider_revision", "") or "")
            if not provider_ref or not provider_revision:
                raise ValueError("runtime signal provider requires explicit provider_ref/provider_revision authority")
            supplied = provider.observe() if hasattr(provider, "observe") else provider()
            for item in supplied or ():
                if isinstance(item, RuntimeSignal):
                    signal = item
                elif isinstance(item, Mapping):
                    signal = RuntimeSignal(
                        signal_ref=str(item["signal_ref"]),
                        value=str(item["value"]),
                        confidence=float(item.get("confidence", 1.0)),
                        evidence_refs=tuple(item.get("evidence_refs", ())),
                        metadata=dict(item.get("metadata", {})),
                    )
                else:
                    raise TypeError("runtime signal provider returned unsupported item")
                if not signal.evidence_refs:
                    raise ValueError("external runtime signal requires explicit evidence_refs")
                signal = RuntimeSignal(
                    signal_ref=signal.signal_ref, value=signal.value,
                    confidence=signal.confidence, evidence_refs=signal.evidence_refs,
                    metadata={
                        **dict(signal.metadata),
                        "provider_ref": provider_ref,
                        "provider_revision": provider_revision,
                    },
                )
                result.append(signal)
        # Conflicting values for one signal in one observation cycle are evidence
        # conflict, not a tie to resolve by ordering.
        by_ref: dict[str, RuntimeSignal] = {}
        for signal in result:
            previous = by_ref.get(signal.signal_ref)
            if previous is not None and previous.value != signal.value:
                raise ValueError(f"conflicting runtime signal values:{signal.signal_ref}")
            if previous is None or signal.confidence > previous.confidence:
                by_ref[signal.signal_ref] = signal
        return tuple(by_ref[key] for key in sorted(by_ref))
