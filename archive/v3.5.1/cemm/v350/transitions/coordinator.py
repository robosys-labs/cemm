"""Phase-11 transition orchestration over pinned store/schema snapshots."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable

from ..schema.model import EventSchema, SchemaLifecycleStatus
from ..storage.model import RecordKind, StoreSnapshot
from ..storage.store import SemanticStore
from ..uol.model import EventOccurrence
from .capabilities import CapabilityDependencyEngine
from .commit import EffectCommitCoordinator, EffectCommitError
from .model import (
    CapabilityProjection,
    StateTimelineProjection,
    TransitionContractRecord,
    TransitionFrontier,
    TransitionPreview,
)
from .preview import TransitionPreviewEngine
from .staging import StagedResolver
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

    def resolve(
        self, record_kind: RecordKind, record_ref: str, revision: int | None = None
    ):
        return self._store.get_record(
            record_kind, record_ref, revision, snapshot=self._snapshot
        )

    def records(self, record_kind: RecordKind):
        return self._store.records(
            record_kind, all_revisions=True, snapshot=self._snapshot
        )

    def resolve_any(self, record_ref: str):
        result = []
        for kind in RecordKind:
            item = self.resolve(kind, record_ref)
            if item is not None:
                result.append(item)
        return tuple(result)


class TransitionCoordinator:
    """Preview then commit generic transition contracts without early mutation.

    ``plans_for_staged_event`` is the Core Loop Stage-12 boundary.  It overlays
    exact cycle-local event/application/proposition/admission records over a pinned
    snapshot so the preview engine can build proof-bearing effects before Stage 13
    persists anything.  Stage 13 must commit the staged epistemic/event records,
    then recompute with ``plans_for_event`` before building the effect patch.  This
    prevents both illegal early writes and stale staged-proof commits.
    """

    def __init__(self, store: SemanticStore) -> None:
        self._store = store

    def plans_for_event(
        self,
        event: EventOccurrence,
        *,
        effective_time_ref: str,
    ) -> tuple[TransitionExecutionPlan, ...]:
        with self._store.snapshot() as snapshot:
            resolver = _PinnedResolver(self._store, snapshot)
            return self._plans(
                event,
                effective_time_ref=effective_time_ref,
                snapshot=snapshot,
                resolver=resolver,
            )

    def plans_for_staged_event(
        self,
        event: EventOccurrence,
        *,
        staged_records: Iterable[tuple[RecordKind, object]],
        effective_time_ref: str,
        snapshot: StoreSnapshot | None = None,
    ) -> tuple[TransitionExecutionPlan, ...]:
        """Preview a prospective admitted event against an exact pinned snapshot.

        The supplied staged records are read-only cycle-local authority.  They must
        contain the exact event/application/proposition/admission lineage required
        by the normal ``TransitionPreviewEngine`` gates.  Nothing here is durable.
        """

        if snapshot is None:
            with self._store.snapshot() as pinned:
                return self.plans_for_staged_event(
                    event,
                    staged_records=staged_records,
                    effective_time_ref=effective_time_ref,
                    snapshot=pinned,
                )
        self._store.assert_snapshot(snapshot)
        resolver = StagedResolver(self._store, snapshot, staged_records)
        return self._plans(
            event,
            effective_time_ref=effective_time_ref,
            snapshot=snapshot,
            resolver=resolver,
        )

    def _plans(
        self,
        event: EventOccurrence,
        *,
        effective_time_ref: str,
        snapshot: StoreSnapshot,
        resolver,
    ) -> tuple[TransitionExecutionPlan, ...]:
        schemas = self._store.repositories.schemas.registry(snapshot=snapshot)
        stored_event = resolver.resolve(
            RecordKind.EVENT_OCCURRENCE, event.event_ref
        )
        if stored_event is None or stored_event.payload != event:
            return ()
        event_schema = schemas.maybe_schema(
            event.event_schema_ref, event.event_schema_revision
        )
        if not isinstance(event_schema, EventSchema):
            return ()
        previewer = TransitionPreviewEngine(schemas, resolver)
        projector = StateTimelineProjector(schemas, resolver)
        capability_engine = CapabilityDependencyEngine(schemas, resolver)
        result: list[TransitionExecutionPlan] = []

        for contract_ref in event_schema.transition_contract_refs:
            stored = resolver.resolve(RecordKind.TRANSITION_CONTRACT, contract_ref)
            if stored is None or not isinstance(
                stored.payload, TransitionContractRecord
            ):
                continue
            contract = stored.payload
            if contract.lifecycle_status != SchemaLifecycleStatus.ACTIVE:
                continue
            preview = previewer.preview(
                event, contract, effective_time_ref=effective_time_ref
            )
            if not preview.authorized:
                result.append(
                    TransitionExecutionPlan(
                        preview,
                        (),
                        (),
                        snapshot.store_revision,
                        snapshot.boot_fingerprint,
                        snapshot.overlay_fingerprint,
                    )
                )
                continue
            state_projections = tuple(
                projector.project(delta) for delta in preview.state_deltas
            )
            holders = tuple(
                sorted({projection.holder_ref for projection in state_projections})
            )
            cap_candidates: list[CapabilityProjection] = []
            for holder_ref in holders:
                for dependency in capability_engine.applicable_dependencies(
                    holder_ref
                ):
                    projected = capability_engine.evaluate(
                        dependency,
                        holder_ref=holder_ref,
                        context_ref=event.context_ref,
                        effective_time_ref=effective_time_ref,
                        trigger_ref=event.event_ref,
                        proof_refs=(
                            (preview.proof.proof_ref,) if preview.proof else ()
                        ),
                        state_projections=state_projections,
                    )
                    if projected is not None:
                        cap_candidates.append(projected)
            capability_frontiers = self._capability_ambiguity_frontiers(
                cap_candidates
            )
            if capability_frontiers:
                preview = replace(
                    preview,
                    frontiers=tuple(
                        sorted(
                            (*preview.frontiers, *capability_frontiers),
                            key=lambda item: item.frontier_ref,
                        )
                    ),
                    blocked_reasons=tuple(
                        sorted(
                            set(
                                (
                                    *preview.blocked_reasons,
                                    "capability_dependency_frontier_unresolved",
                                )
                            )
                        )
                    ),
                )
            result.append(
                TransitionExecutionPlan(
                    preview,
                    state_projections,
                    tuple(
                        sorted(
                            cap_candidates,
                            key=lambda item: (
                                item.delta.holder_ref,
                                item.delta.action_schema_ref,
                                item.delta.dependency_ref,
                            ),
                        )
                    ),
                    snapshot.store_revision,
                    snapshot.boot_fingerprint,
                    snapshot.overlay_fingerprint,
                )
            )

        authorized = [item for item in result if item.preview.authorized]
        if len(authorized) > 1:
            competing = tuple(
                sorted(item.preview.contract_ref for item in authorized)
            )
            rewritten: list[TransitionExecutionPlan] = []
            for item in result:
                if not item.preview.authorized:
                    rewritten.append(item)
                    continue
                frontier = TransitionFrontier(
                    frontier_ref=self._frontier_ref(
                        event.event_ref,
                        "multiple-authorized-contracts",
                        *competing,
                    ),
                    reason=(
                        "multiple_transition_contracts_authorized_without_"
                        "explicit_composition_semantics"
                    ),
                    dependency_refs=competing,
                )
                rewritten.append(
                    replace(
                        item,
                        preview=replace(
                            item.preview,
                            frontiers=tuple(
                                sorted(
                                    (*item.preview.frontiers, frontier),
                                    key=lambda entry: entry.frontier_ref,
                                )
                            ),
                            blocked_reasons=tuple(
                                sorted(
                                    set(
                                        (
                                            *item.preview.blocked_reasons,
                                            "transition_contract_ambiguity_unresolved",
                                        )
                                    )
                                )
                            ),
                        ),
                    )
                )
            result = rewritten
        return tuple(result)

    def build_patch(
        self,
        event: EventOccurrence,
        plan: TransitionExecutionPlan,
        *,
        source_ref: str,
        permission_ref: str,
    ):
        if not plan.preview.authorized or plan.preview.proof is None:
            raise EffectCommitError(
                "transition plan is blocked or unresolved and cannot be committed"
            )
        with self._store.snapshot() as current_snapshot:
            if (
                current_snapshot.store_revision != plan.store_revision
                or current_snapshot.boot_fingerprint != plan.boot_fingerprint
                or current_snapshot.overlay_fingerprint != plan.overlay_fingerprint
            ):
                raise EffectCommitError(
                    "stale transition execution plan: pinned store snapshot "
                    "no longer matches current store"
                )
        canonical = next(
            (
                item
                for item in self.plans_for_event(
                    event,
                    effective_time_ref=plan.preview.proof.effective_time_ref,
                )
                if item.preview.contract_ref == plan.preview.contract_ref
                and item.preview.contract_revision
                == plan.preview.contract_revision
                and item.preview.proof is not None
                and item.preview.proof.proof_ref == plan.preview.proof.proof_ref
            ),
            None,
        )
        if canonical is None or canonical != plan:
            raise EffectCommitError(
                "transition execution plan does not match canonical recomputation "
                "at the pinned store state"
            )
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
    def _capability_ambiguity_frontiers(
        items: Iterable[CapabilityProjection],
    ) -> tuple[TransitionFrontier, ...]:
        by_key: dict[tuple[str, str, str], list[CapabilityProjection]] = {}
        for item in items:
            key = (
                item.delta.holder_ref,
                item.delta.action_schema_ref,
                item.delta.context_ref,
            )
            by_key.setdefault(key, []).append(item)
        frontiers: list[TransitionFrontier] = []
        for key, projections in sorted(by_key.items()):
            if len(projections) <= 1:
                continue
            dependencies = tuple(
                sorted(item.delta.dependency_ref for item in projections)
            )
            frontiers.append(
                TransitionFrontier(
                    frontier_ref=TransitionCoordinator._frontier_ref(
                        *key,
                        "capability-dependency-ambiguity",
                        *dependencies,
                    ),
                    reason=(
                        "multiple_capability_dependencies_target_same_holder_action_"
                        "without_composition_semantics"
                    ),
                    dependency_refs=dependencies,
                )
            )
        return tuple(frontiers)

    @staticmethod
    def _frontier_ref(*parts: str) -> str:
        from hashlib import sha256

        payload = "\x1f".join(parts).encode("utf-8")
        return f"transition-frontier:{sha256(payload).hexdigest()[:24]}"
