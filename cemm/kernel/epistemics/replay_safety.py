"""ReplaySafety — duplicate replay delivery produces one result,
in-flight effects reauthorize against current state.

Import boundary: model + schema + epistemics submodules only. No engine imports.

Architectural guardrails (CORE_LOOP.md §9, LEARNING_PIPELINE.md §11):
- Replay is deduplicated, snapshot-pinned, retry-safe, and stale-cancellable.
- It never repeats external actions or already dispatched communication.
- Replay excludes operations already started or dispatched.
- Replay identity includes evidence, target sense/revision, checkpoint,
  context/scope, and dependency fingerprint.
- Replay work is deduplicated, retry-safe, and stale-cancellable.
- Duplicate replay delivery produces one result.
- In-flight effects reauthorize against current state.
- Effects and irreversible operations revalidate at authorization and
  critical commit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..model.learning import ReplayWorkItem, ReplayResult
from ..learning.replay_queue import ReplayQueue, ReplayKey


@dataclass(frozen=True, slots=True)
class InFlightEffect:
    """An in-flight effect that must be reauthorized against current state.

    Effects and irreversible operations revalidate at authorization and
    critical commit.
    """
    effect_id: str
    operation_id: str
    idempotency_key: str
    started_at: str = ""
    predicted_effects: tuple[str, ...] = ()
    authorization_fingerprint: str = ""  # Fingerprint at authorization time
    status: str = "in_flight"  # in_flight, reauthorized, cancelled, committed


@dataclass(frozen=True, slots=True)
class ReauthorizationResult:
    """Result of reauthorizing an in-flight effect."""
    effect_id: str
    is_authorized: bool
    reason: str = ""
    new_fingerprint: str = ""


class ReplaySafetyManager:
    """Manages replay safety and in-flight effect reauthorization.

    Duplicate replay delivery produces one result.
    In-flight effects reauthorize against current state.
    """

    def __init__(self, replay_queue: ReplayQueue | None = None) -> None:
        self._replay_queue = replay_queue or ReplayQueue()
        self._in_flight_effects: dict[str, InFlightEffect] = {}
        self._completed_effects: dict[str, InFlightEffect] = {}

    @property
    def replay_queue(self) -> ReplayQueue:
        return self._replay_queue

    def submit_replay(self, item: ReplayWorkItem) -> tuple[bool, ReplayResult | None]:
        """Submit a replay work item.

        Duplicate replay delivery produces one result.
        Returns (was_enqueued, existing_result).
        """
        # Check if already completed
        if self._replay_queue.is_completed(item):
            existing = self._replay_queue.get_result(item)
            return (False, existing)  # Duplicate — return existing result

        # Try to enqueue
        enqueued = self._replay_queue.enqueue(item)
        return (enqueued, None)

    def complete_replay(self, item: ReplayWorkItem, result: ReplayResult) -> None:
        """Complete a replay work item.

        The result is stored so duplicate submissions return the same result.
        """
        self._replay_queue.complete(item, result)

    def register_in_flight_effect(
        self,
        effect_id: str,
        operation_id: str,
        idempotency_key: str,
        authorization_fingerprint: str = "",
        predicted_effects: tuple[str, ...] = (),
    ) -> InFlightEffect:
        """Register an in-flight effect for reauthorization tracking.

        Effects and irreversible operations revalidate at authorization
        and critical commit.
        """
        effect = InFlightEffect(
            effect_id=effect_id,
            operation_id=operation_id,
            idempotency_key=idempotency_key,
            started_at=datetime.now(timezone.utc).isoformat(),
            predicted_effects=predicted_effects,
            authorization_fingerprint=authorization_fingerprint,
        )
        self._in_flight_effects[effect_id] = effect
        return effect

    def reauthorize(
        self,
        effect_id: str,
        current_fingerprint: str,
        current_permission: bool = True,
        current_resources_available: bool = True,
    ) -> ReauthorizationResult:
        """Reauthorize an in-flight effect against current state.

        Effects and irreversible operations revalidate at authorization
        and critical commit.
        """
        effect = self._in_flight_effects.get(effect_id)
        if effect is None:
            return ReauthorizationResult(
                effect_id=effect_id,
                is_authorized=False,
                reason="effect not found",
            )

        # Check fingerprint match
        if effect.authorization_fingerprint != current_fingerprint:
            return ReauthorizationResult(
                effect_id=effect_id,
                is_authorized=False,
                reason=f"fingerprint changed: was {effect.authorization_fingerprint}, now {current_fingerprint}",
                new_fingerprint=current_fingerprint,
            )

        # Check permission
        if not current_permission:
            return ReauthorizationResult(
                effect_id=effect_id,
                is_authorized=False,
                reason="permission no longer allowed",
                new_fingerprint=current_fingerprint,
            )

        # Check resources
        if not current_resources_available:
            return ReauthorizationResult(
                effect_id=effect_id,
                is_authorized=False,
                reason="resources no longer available",
                new_fingerprint=current_fingerprint,
            )

        return ReauthorizationResult(
            effect_id=effect_id,
            is_authorized=True,
            new_fingerprint=current_fingerprint,
        )

    def commit_effect(self, effect_id: str) -> InFlightEffect | None:
        """Mark an in-flight effect as committed."""
        from dataclasses import replace
        effect = self._in_flight_effects.pop(effect_id, None)
        if effect is None:
            return None
        committed = replace(effect, status="committed")
        self._completed_effects[effect_id] = committed
        return committed

    def cancel_effect(self, effect_id: str) -> InFlightEffect | None:
        """Cancel an in-flight effect."""
        from dataclasses import replace
        effect = self._in_flight_effects.pop(effect_id, None)
        if effect is None:
            return None
        cancelled = replace(effect, status="cancelled")
        self._completed_effects[effect_id] = cancelled
        return cancelled

    def get_in_flight_effects(self) -> tuple[InFlightEffect, ...]:
        """Get all in-flight effects."""
        return tuple(self._in_flight_effects.values())

    def get_completed_effects(self) -> tuple[InFlightEffect, ...]:
        """Get all completed/cancelled effects."""
        return tuple(self._completed_effects.values())
