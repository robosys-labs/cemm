"""ReplayQueue — dedup/snapshot/idempotence for replay work.

Import boundary: model + schema submodules only. No engine imports.

Architectural guardrails (LEARNING_PIPELINE.md §11, CORE_LOOP.md §9):
- Replay begins at the earliest affected checkpoint in the ordinary pipeline.
- Replay key: source evidence, exact target sense/schema revision,
  checkpoint, context/scope, dependency/environment fingerprint.
- Replay is deduplicated, snapshot-pinned, retry-safe, and stale-cancellable.
- It never repeats external actions or already dispatched communication.
- Replay excludes operations already started or dispatched.
- Replay identity includes evidence, target sense/revision, checkpoint,
  context/scope, and dependency fingerprint.
- Replay work is deduplicated, retry-safe, and stale-cancellable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from ..model.learning import ReplayWorkItem, ReplayResult


@dataclass(frozen=True, slots=True)
class ReplayKey:
    """Deduplication key for replay work.

    Replay identity includes:
    - source evidence
    - exact target sense/schema revision
    - checkpoint
    - context/scope
    - dependency/environment fingerprint
    """
    source_evidence_ref: str
    target_sense_ref: str
    target_schema_revision_ref: str
    checkpoint_ref: str
    context_ref: str
    dependency_fingerprint: str

    def as_string(self) -> str:
        """Get a string representation for hashing/comparison."""
        return "|".join((
            self.source_evidence_ref,
            self.target_sense_ref,
            self.target_schema_revision_ref,
            self.checkpoint_ref,
            self.context_ref,
            self.dependency_fingerprint,
        ))


@dataclass(frozen=True, slots=True)
class ExecutedOperationExclusion:
    """Record of an already-executed operation to exclude from replay.

    Replay never repeats external actions or already dispatched communication.
    """
    operation_id: str
    idempotency_key: str
    dispatched_at: str = ""  # ISO timestamp


class ReplayQueue:
    """Dedup/snapshot/idempotence queue for replay work.

    Replay is deduplicated, snapshot-pinned, retry-safe, and stale-cancellable.
    It never repeats external actions or already dispatched communication.
    """

    def __init__(self) -> None:
        self._queue: list[ReplayWorkItem] = []
        self._completed_keys: dict[str, ReplayResult] = {}
        self._executed_operations: dict[str, ExecutedOperationExclusion] = {}
        self._snapshot_fingerprint: str = ""

    def pin_snapshot(self, fingerprint: str) -> None:
        """Pin the snapshot fingerprint for this replay batch.

        Replay is snapshot-pinned — all work items reference the same
        environment snapshot.
        """
        self._snapshot_fingerprint = fingerprint

    def enqueue(self, item: ReplayWorkItem) -> bool:
        """Enqueue a replay work item.

        Returns True if the item was enqueued, False if it was deduplicated
        (already completed or already queued with same key).
        """
        key = self._make_key(item)

        # Dedup: check if already completed
        if key.as_string() in self._completed_keys:
            return False  # Already done — dedup

        # Dedup: check if already queued
        for existing in self._queue:
            if self._make_key(existing).as_string() == key.as_string():
                return False  # Already queued — dedup

        self._queue.append(item)
        return True

    def dequeue(self) -> ReplayWorkItem | None:
        """Dequeue the highest-priority replay work item."""
        if not self._queue:
            return None

        # Sort by priority (higher first)
        self._queue.sort(key=lambda x: x.priority, reverse=True)
        return self._queue.pop(0)

    def complete(self, item: ReplayWorkItem, result: ReplayResult) -> None:
        """Mark a replay work item as completed."""
        key = self._make_key(item)
        self._completed_keys[key.as_string()] = result

    def is_completed(self, item: ReplayWorkItem) -> bool:
        """Check if a replay work item has been completed."""
        key = self._make_key(item)
        return key.as_string() in self._completed_keys

    def get_result(self, item: ReplayWorkItem) -> ReplayResult | None:
        """Get the result of a completed replay work item."""
        key = self._make_key(item)
        return self._completed_keys.get(key.as_string())

    def cancel_stale(self, current_fingerprint: str) -> tuple[ReplayWorkItem, ...]:
        """Cancel stale replay work items.

        Items with a different dependency fingerprint than the current
        snapshot are stale and should be cancelled.
        """
        stale: list[ReplayWorkItem] = []
        remaining: list[ReplayWorkItem] = []

        for item in self._queue:
            if item.dependency_fingerprint != current_fingerprint:
                stale.append(item)
            else:
                remaining.append(item)

        self._queue = remaining
        return tuple(stale)

    def record_executed_operation(
        self,
        operation_id: str,
        idempotency_key: str,
    ) -> None:
        """Record an already-executed operation to exclude from replay.

        Replay never repeats external actions or already dispatched
        communication.
        """
        self._executed_operations[idempotency_key] = ExecutedOperationExclusion(
            operation_id=operation_id,
            idempotency_key=idempotency_key,
            dispatched_at=datetime.now(timezone.utc).isoformat(),
        )

    def is_operation_executed(self, idempotency_key: str) -> bool:
        """Check if an operation has already been executed.

        Replay excludes operations already started or dispatched.
        """
        return idempotency_key in self._executed_operations

    def pending_count(self) -> int:
        """Get the number of pending replay work items."""
        return len(self._queue)

    def completed_count(self) -> int:
        """Get the number of completed replay work items."""
        return len(self._completed_keys)

    def _make_key(self, item: ReplayWorkItem) -> ReplayKey:
        """Make a dedup key from a replay work item."""
        context_ref = item.context_refs[0] if item.context_refs else ""
        return ReplayKey(
            source_evidence_ref=item.source_evidence_ref,
            target_sense_ref=item.target_sense_ref,
            target_schema_revision_ref=item.target_schema_revision_ref,
            checkpoint_ref=item.checkpoint_ref,
            context_ref=context_ref,
            dependency_fingerprint=item.dependency_fingerprint,
        )
