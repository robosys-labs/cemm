"""TypedInvalidationEvent — typed invalidation events for dependency changes.

Import boundary: model + schema submodules only. No engine imports.

Architectural guardrails (AGENTS.md §7.5, LEARNING_PIPELINE.md §13,
CORE_LOOP.md §9, ADR-21):
- Typed schema/environment changes publish invalidation events.
- Schema, policy, foundation, competence-suite, adapter-contract, or
  type-registry changes invalidate dependent assessments.
- The truth-maintenance/dependency infrastructure retracts or marks stale:
    inherited constraints, classifications, inferred propositions,
    cached answers, plans, effect proposals, undispatched messages,
    capability/understanding conclusions, learning-success claims.
- Original evidence remains. Historical output remains an event and may
  generate a repair obligation.
- Effects and irreversible operations revalidate at authorization and
  critical commit.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class InvalidationSource(str, Enum):
    """What kind of dependency change triggered the invalidation."""
    SCHEMA_DOWNGRADE = "schema_downgrade"
    SCHEMA_SUPERSESSION = "schema_supersession"
    SCHEMA_REJECTION = "schema_rejection"
    POLICY_CHANGE = "policy_change"
    FOUNDATION_CHANGE = "foundation_change"
    COMPETENCE_SUITE_CHANGE = "competence_suite_change"
    ADAPTER_CONTRACT_CHANGE = "adapter_contract_change"
    TYPE_REGISTRY_CHANGE = "type_registry_change"
    ENVIRONMENT_FINGERPRINT_CHANGE = "environment_fingerprint_change"
    EVIDENCE_RETRACTION = "evidence_retraction"
    PERMISSION_CHANGE = "permission_change"


class InvalidationAction(str, Enum):
    """What action to take on dependent artifacts."""
    RETRACT = "retract"    # Remove from active use
    MARK_STALE = "mark_stale"  # Keep but flag as needing revalidation
    REAUTHORIZE = "reauthorize"  # Must revalidate against current state


@dataclass(frozen=True, slots=True)
class TypedInvalidationEvent:
    """A typed invalidation event published when a dependency changes.

    Typed schema/environment changes publish invalidation events.
    The event specifies what changed, what artifacts are affected,
    and what action to take.
    """
    event_id: str
    source: InvalidationSource
    action: InvalidationAction
    changed_schema_revision_refs: tuple[str, ...] = ()
    changed_assessment_refs: tuple[str, ...] = ()
    changed_evidence_refs: tuple[str, ...] = ()
    old_fingerprint: str = ""
    new_fingerprint: str = ""
    affected_artifact_ids: tuple[str, ...] = ()
    published_at: str = ""

    @staticmethod
    def create(
        source: InvalidationSource,
        action: InvalidationAction = InvalidationAction.RETRACT,
        changed_schema_revision_refs: tuple[str, ...] = (),
        changed_assessment_refs: tuple[str, ...] = (),
        changed_evidence_refs: tuple[str, ...] = (),
        old_fingerprint: str = "",
        new_fingerprint: str = "",
        affected_artifact_ids: tuple[str, ...] = (),
    ) -> TypedInvalidationEvent:
        """Create a new typed invalidation event."""
        return TypedInvalidationEvent(
            event_id=f"inv:{source.value}:{datetime.now(timezone.utc).isoformat()}",
            source=source,
            action=action,
            changed_schema_revision_refs=changed_schema_revision_refs,
            changed_assessment_refs=changed_assessment_refs,
            changed_evidence_refs=changed_evidence_refs,
            old_fingerprint=old_fingerprint,
            new_fingerprint=new_fingerprint,
            affected_artifact_ids=affected_artifact_ids,
            published_at=datetime.now(timezone.utc).isoformat(),
        )


class InvalidationEventBus:
    """Bus for publishing and consuming typed invalidation events.

    Typed schema/environment changes publish invalidation events.
    Truth maintenance and other subscribers consume them to retract
    or mark stale dependent derived artifacts.
    """

    def __init__(self) -> None:
        self._events: list[TypedInvalidationEvent] = []
        self._subscribers: list[Any] = []

    def publish(self, event: TypedInvalidationEvent) -> None:
        """Publish a typed invalidation event."""
        self._events.append(event)
        for subscriber in self._subscribers:
            if hasattr(subscriber, "on_invalidation"):
                subscriber.on_invalidation(event)

    def subscribe(self, subscriber: Any) -> None:
        """Subscribe to invalidation events.

        Subscriber must have an `on_invalidation(event)` method.
        """
        self._subscribers.append(subscriber)

    def get_events(self) -> tuple[TypedInvalidationEvent, ...]:
        """Get all published events."""
        return tuple(self._events)

    def get_events_for_schema(self, schema_ref: str) -> tuple[TypedInvalidationEvent, ...]:
        """Get events that affect a specific schema revision."""
        return tuple(
            e for e in self._events
            if schema_ref in e.changed_schema_revision_refs
        )

    def get_events_for_fingerprint(self, fingerprint: str) -> tuple[TypedInvalidationEvent, ...]:
        """Get events that affect a specific environment fingerprint."""
        return tuple(
            e for e in self._events
            if e.old_fingerprint == fingerprint or e.new_fingerprint == fingerprint
        )

    def clear(self) -> None:
        """Clear all events."""
        self._events.clear()
