"""Explicit event-driven maintenance and session participant lifecycle."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from threading import RLock
from typing import Any, Callable, Iterable, Mapping

from .schema.model import semantic_fingerprint


class MaintenanceTrigger(str, Enum):
    STARTUP = "startup"
    RELOAD = "reload"
    RUNTIME_SIGNAL_CHANGED = "runtime_signal_changed"
    LEARNING_EVIDENCE_CHANGED = "learning_evidence_changed"
    COMPETENCE_COMPLETED = "competence_completed"
    REVIEW_DECISION = "review_decision"
    EXPLICIT_CONSOLIDATION = "explicit_consolidation"
    TIMER = "timer"
    MANUAL = "manual"


@dataclass(frozen=True, slots=True)
class RuntimeObservationSnapshot:
    snapshot_ref: str
    signal_fingerprint: str
    runtime_epoch_ref: str
    authority_generation: int
    signal_refs: tuple[str, ...]
    provider_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MaintenanceEvent:
    trigger: MaintenanceTrigger
    ref_set: tuple[str, ...] = ()
    context_ref: str = "global"
    permission_ref: str = "internal"


@dataclass(frozen=True, slots=True)
class MaintenanceTaskResult:
    task_ref: str
    trigger: MaintenanceTrigger
    performed: bool
    details: Mapping[str, Any] = field(
        default_factory=dict
    )


class MaintenanceScheduler:
    """Synchronous event queue; no request-count clock or background thread."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._tasks: dict[
            str,
            tuple[
                frozenset[MaintenanceTrigger],
                Callable[[MaintenanceEvent], Any],
            ],
        ] = {}
        self._pending: list[MaintenanceEvent] = []

    def register(
        self,
        task_ref: str,
        *,
        triggers: Iterable[MaintenanceTrigger],
        callback: Callable[[MaintenanceEvent], Any],
    ) -> None:
        resolved = frozenset(triggers)
        if not task_ref or not resolved:
            raise ValueError(
                "maintenance task requires identity and triggers"
            )
        with self._lock:
            if task_ref in self._tasks:
                raise ValueError(
                    f"duplicate maintenance task:{task_ref}"
                )
            self._tasks[task_ref] = (
                resolved,
                callback,
            )

    def notify(
        self,
        trigger: MaintenanceTrigger,
        *,
        refs: Iterable[str] = (),
        context_ref: str = "global",
        permission_ref: str = "internal",
    ) -> None:
        event = MaintenanceEvent(
            trigger,
            tuple(sorted(set(map(str, refs)))),
            context_ref,
            permission_ref,
        )
        with self._lock:
            if event not in self._pending:
                self._pending.append(event)

    def run_event(
        self,
        event: MaintenanceEvent,
    ) -> tuple[MaintenanceTaskResult, ...]:
        with self._lock:
            tasks = tuple(self._tasks.items())
        results = []
        for task_ref, (triggers, callback) in tasks:
            if event.trigger not in triggers:
                continue
            details = callback(event)
            results.append(
                MaintenanceTaskResult(
                    task_ref=task_ref,
                    trigger=event.trigger,
                    performed=True,
                    details=(
                        {}
                        if details is None
                        else {"result": details}
                    ),
                )
            )
        return tuple(results)

    def drain(
        self,
    ) -> tuple[MaintenanceTaskResult, ...]:
        with self._lock:
            pending = tuple(self._pending)
            self._pending.clear()
        return tuple(
            result
            for event in pending
            for result in self.run_event(event)
        )


class SessionParticipantLifecycle:
    """Persist/resolve participant identity once per session key."""

    def __init__(self) -> None:
        self._lock = RLock()
        self._resolved: dict[
            tuple[str, str, str | None],
            tuple[str, str],
        ] = {}

    def resolve(
        self,
        context_ref: str,
        permission_ref: str,
        requested_ref: str | None,
        *,
        initializer: Callable[
            [str, str, str | None],
            tuple[str, str],
        ],
    ) -> tuple[str, str]:
        key = (
            context_ref,
            permission_ref,
            requested_ref,
        )
        with self._lock:
            existing = self._resolved.get(key)
            if existing is not None:
                return existing
            resolved = initializer(
                context_ref,
                permission_ref,
                requested_ref,
            )
            self._resolved[key] = resolved
            return resolved

    def invalidate_context(
        self,
        context_ref: str,
    ) -> None:
        with self._lock:
            self._resolved = {
                key: value
                for key, value in self._resolved.items()
                if key[0] != context_ref
            }


def build_default_maintenance_scheduler(
    store,
    services,
) -> MaintenanceScheduler:
    from .learning.runtime import LearningRuntimeActivator
    from .learning.runtime_advance import RuntimeLearningAdvancer
    from .runtime_state import RuntimeSelfObserver

    scheduler = MaintenanceScheduler()

    def refresh_runtime_observation(
        event: MaintenanceEvent,
    ):
        observer = RuntimeSelfObserver(
            store,
            services,
        )
        signals = observer._signals()
        provider_refs = tuple(
            sorted(
                {
                    str(item.metadata.get("provider_ref"))
                    for item in signals
                    if item.metadata.get("provider_ref")
                }
            )
        )
        signal_fingerprint = semantic_fingerprint(
            "runtime-observation-snapshot",
            tuple(
                (
                    item.signal_ref,
                    item.value,
                    item.confidence,
                    tuple(sorted(item.evidence_refs)),
                    tuple(
                        sorted(
                            (
                                str(key),
                                value,
                            )
                            for key, value in item.metadata.items()
                            if str(key)
                            not in {
                                "observed_at",
                                "observed_time",
                                "timestamp",
                                "collected_at",
                                "request_id",
                                "cycle_ref",
                                "trace_ref",
                            }
                        )
                    ),
                )
                for item in signals
            ),
            64,
        )
        current = getattr(
            services,
            "runtime_observation_snapshot",
            None,
        )
        if (
            isinstance(
                current,
                RuntimeObservationSnapshot,
            )
            and current.signal_fingerprint
            == signal_fingerprint
        ):
            return current

        observer.observe(
            context_ref=(
                event.context_ref
                or "global"
            ),
            permission_ref=(
                event.permission_ref
                or "internal"
            ),
        )
        snapshot = RuntimeObservationSnapshot(
            snapshot_ref=(
                "runtime-observation:"
                + semantic_fingerprint(
                    "runtime-observation-ref",
                    (
                        getattr(
                            services,
                            "runtime_epoch_ref",
                            "",
                        ),
                        signal_fingerprint,
                        getattr(
                            services,
                            "runtime_authority_generation",
                            1,
                        ),
                    ),
                    24,
                )
            ),
            signal_fingerprint=signal_fingerprint,
            runtime_epoch_ref=str(
                getattr(
                    services,
                    "runtime_epoch_ref",
                    "",
                )
                or ""
            ),
            authority_generation=int(
                getattr(
                    services,
                    "runtime_authority_generation",
                    1,
                )
                or 1
            ),
            signal_refs=tuple(
                item.signal_ref
                for item in signals
            ),
            provider_refs=provider_refs,
        )
        services.runtime_observation_snapshot = snapshot
        return snapshot

    def activate_reviewed_learning(
        _event: MaintenanceEvent,
    ):
        return LearningRuntimeActivator(
            store
        ).activate_ready()

    def advance_learning(
        event: MaintenanceEvent,
    ):
        active_passes = int(getattr(store, "active_semantic_passes", 0) or 0)
        if active_passes:
            # Do not lose the event and do not publish a new authority generation
            # into the middle of an active semantic pass.
            scheduler.notify(
                event.trigger,
                refs=event.ref_set,
                context_ref=event.context_ref,
                permission_ref=event.permission_ref,
            )
            return {
                "deferred": "active_semantic_passes",
                "active_semantic_passes": active_passes,
            }

        trace = RuntimeLearningAdvancer(
            store,
            inducers=tuple(
                getattr(
                    services,
                    "learning_inducers",
                    (),
                )
            ),
            competence_executors=dict(
                getattr(
                    services,
                    "learning_competence_executors",
                    {},
                )
            ),
        ).advance(
            context_ref=event.context_ref,
            permission_ref=event.permission_ref,
            frontier_refs=(
                event.ref_set
                or None
            ),
        )
        activation = LearningRuntimeActivator(
            store
        ).activate_ready()
        return {
            "advance": trace,
            "activation": activation,
        }

    scheduler.register(
        "maintenance:runtime-observation",
        triggers={
            MaintenanceTrigger.STARTUP,
            MaintenanceTrigger.RELOAD,
            MaintenanceTrigger.RUNTIME_SIGNAL_CHANGED,
        },
        callback=refresh_runtime_observation,
    )
    scheduler.register(
        "maintenance:reviewed-learning-activation",
        triggers={
            MaintenanceTrigger.STARTUP,
            MaintenanceTrigger.RELOAD,
        },
        callback=activate_reviewed_learning,
    )
    scheduler.register(
        "maintenance:learning-advance",
        triggers={
            MaintenanceTrigger.LEARNING_EVIDENCE_CHANGED,
            MaintenanceTrigger.COMPETENCE_COMPLETED,
            MaintenanceTrigger.REVIEW_DECISION,
            MaintenanceTrigger.EXPLICIT_CONSOLIDATION,
        },
        callback=advance_learning,
    )
    return scheduler


__all__ = [
    "MaintenanceEvent",
    "MaintenanceScheduler",
    "MaintenanceTaskResult",
    "MaintenanceTrigger",
    "RuntimeObservationSnapshot",
    "SessionParticipantLifecycle",
    "build_default_maintenance_scheduler",
]
