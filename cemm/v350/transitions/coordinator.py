"""Phase-11 transition orchestration over pinned store/schema snapshots."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from ..schema.model import EventSchema, SchemaLifecycleStatus
from ..storage.model import RecordKind, StoreSnapshot
from ..storage.store import SemanticStore
from ..uol.model import EventOccurrence
from .capabilities import CapabilityDependencyEngine
from .commit import EffectCommitCoordinator
from .model import CapabilityProjection, StateTimelineProjection, TransitionContractRecord, TransitionPreview
from .preview import TransitionPreviewEngine
from .state import StateTimelineProjector


@dataclass(frozen=True, slots=True)
class TransitionExecutionPlan:
    preview: TransitionPreview
    state_projections: tuple[StateTimelineProjection, ...]
    capability_projections: tuple[CapabilityProjection, ...]
    store_revision: int
    boot_fingerprint: str
    overlay_fingerprint: str


class _PinnedResolver:
    def __init__(self, store: SemanticStore, snapshot: StoreSnapshot) -> None:
        self._store = store
        self._snapshot = snapshot

    def resolve(self, record_kind: RecordKind, record_ref: str, revision: int | None = None):
        return self._store.get_record(record_kind, record_ref, revision, snapshot=self._snapshot)

    def records(self, record_kind: RecordKind):
        return self._store.records(record_kind, all_revisions=True, snapshot=self._snapshot)

    def resolve_any(self, record_ref: str):
        result = []
        for kind in RecordKind:
            item = self.resolve(kind, record_ref)
            if item is not None:
                result.append(item)
        return tuple(result)


class TransitionCoordinator:
    def __init__(self, store: SemanticStore) -> None:
        self._store = store

    def plans_for_event(
        self,
        event: EventOccurrence,
        *,
        effective_time_ref: str,
    ) -> tuple[TransitionExecutionPlan, ...]:
        with self._store.snapshot() as snapshot:
            schemas = self._store.repositories.schemas.registry(snapshot=snapshot)
            resolver = _PinnedResolver(self._store, snapshot)
            stored_event = resolver.resolve(RecordKind.EVENT_OCCURRENCE, event.event_ref)
            if stored_event is None or stored_event.payload != event:
                return ()
            event_schema = schemas.maybe_schema(event.event_schema_ref, event.event_schema_revision)
            if not isinstance(event_schema, EventSchema):
                return ()
            previewer = TransitionPreviewEngine(schemas, resolver)
            projector = StateTimelineProjector(schemas, resolver)
            capability_engine = CapabilityDependencyEngine(schemas, resolver)
            result: list[TransitionExecutionPlan] = []

            for contract_ref in event_schema.transition_contract_refs:
                stored = resolver.resolve(RecordKind.TRANSITION_CONTRACT, contract_ref)
                if stored is None or not isinstance(stored.payload, TransitionContractRecord):
                    continue
                contract = stored.payload
                if contract.lifecycle_status != SchemaLifecycleStatus.ACTIVE:
                    continue
                preview = previewer.preview(event, contract, effective_time_ref=effective_time_ref)
                if not preview.authorized:
                    result.append(TransitionExecutionPlan(
                        preview, (), (), snapshot.store_revision,
                        snapshot.boot_fingerprint, snapshot.overlay_fingerprint,
                    ))
                    continue
                state_projections = tuple(projector.project(delta) for delta in preview.state_deltas)
                holders = tuple(sorted({projection.holder_ref for projection in state_projections}))
                cap_candidates: list[CapabilityProjection] = []
                for holder_ref in holders:
                    for dependency in capability_engine.applicable_dependencies(holder_ref):
                        projected = capability_engine.evaluate(
                            dependency,
                            holder_ref=holder_ref,
                            context_ref=event.context_ref,
                            effective_time_ref=effective_time_ref,
                            trigger_ref=event.event_ref,
                            proof_refs=(preview.proof.proof_ref,) if preview.proof else (),
                            state_projections=state_projections,
                        )
                        if projected is not None:
                            cap_candidates.append(projected)
                self._require_capability_consistency(cap_candidates)
                result.append(TransitionExecutionPlan(
                    preview,
                    state_projections,
                    tuple(sorted(cap_candidates, key=lambda item: (item.delta.holder_ref, item.delta.action_schema_ref))),
                    snapshot.store_revision,
                    snapshot.boot_fingerprint,
                    snapshot.overlay_fingerprint,
                ))
            return tuple(result)

    def build_patch(
        self,
        event: EventOccurrence,
        plan: TransitionExecutionPlan,
        *,
        source_ref: str,
        permission_ref: str,
    ):
        return EffectCommitCoordinator(self._store).build_patch(
            event,
            plan.preview,
            plan.state_projections,
            plan.capability_projections,
            source_ref=source_ref,
            permission_ref=permission_ref,
            expected_store_revision=plan.store_revision,
            expected_boot_fingerprint=plan.boot_fingerprint,
            expected_overlay_fingerprint=plan.overlay_fingerprint,
        )

    @staticmethod
    def _require_capability_consistency(items: Iterable[CapabilityProjection]) -> None:
        by_key: dict[tuple[str, str, str], set[str]] = {}
        for item in items:
            key = (item.delta.holder_ref, item.delta.action_schema_ref, item.delta.context_ref)
            by_key.setdefault(key, set()).add(item.delta.new_status.value)
        conflicts = {key: values for key, values in by_key.items() if len(values) > 1}
        if conflicts:
            raise ValueError(f"conflicting capability dependency projections: {conflicts}")
