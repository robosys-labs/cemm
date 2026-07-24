"""State-condition evaluation, delta validation, and immutable timeline projection."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from hashlib import sha256
from typing import Any, Iterable, Protocol

from ..schema.model import StateDimensionSchema, StateValueSchema, UseOperation, schema_authorizes_use
from ..schema.registry import SchemaRegistry
from ..storage.model import AssignmentStatus, RecordKind, StateAssignment, StoredRecord
from ..semantic_records.model import ChangeOperation, StateDelta
from .model import (
    AssignmentMutation,
    ConditionOperator,
    StateConditionSpec,
    StateTimelineProjection,
    UnknownConditionPolicy,
)


class Resolver(Protocol):
    def resolve(self, record_kind: RecordKind, record_ref: str, revision: int | None = None) -> Any | None: ...
    def records(self, record_kind: RecordKind) -> tuple[Any, ...]: ...


class StateTransitionError(ValueError):
    pass


class StateConditionEvaluator:
    def __init__(self, resolver: Resolver) -> None:
        self._resolver = resolver

    def active_assignments(
        self,
        holder_ref: str,
        dimension_ref: str,
        dimension_revision: int,
        context_ref: str,
        effective_time_ref: str,
    ) -> tuple[StoredRecord[StateAssignment], ...]:
        """Return exact-revision assignments that hold at the requested timeline instant.

        The latest record revision for each assignment identity is authoritative. A
        terminated assignment still counts historically inside its closed interval;
        future-dated assignments never satisfy an earlier transition.
        """
        at_time = parse_timeline_timestamp(effective_time_ref)
        latest: dict[str, StoredRecord[StateAssignment]] = {}
        for stored in self._resolver.records(RecordKind.STATE_ASSIGNMENT):
            item = stored.payload
            if not isinstance(item, StateAssignment):
                continue
            if (
                item.holder_ref != holder_ref
                or item.dimension_ref != dimension_ref
                or item.dimension_revision != dimension_revision
            ):
                continue
            if item.context_ref not in {"global", context_ref}:
                continue
            prior = latest.get(item.assignment_ref)
            if prior is None or stored.revision > prior.revision:
                latest[item.assignment_ref] = stored

        result: list[StoredRecord[StateAssignment]] = []
        for stored in latest.values():
            item = stored.payload
            if item.status in {AssignmentStatus.RETRACTED, AssignmentStatus.SUPERSEDED, AssignmentStatus.OPPOSED, AssignmentStatus.CONTRADICTED}:
                continue
            start = parse_optional_timeline_timestamp(item.valid_from)
            end = parse_optional_timeline_timestamp(item.valid_to)
            if start is not None and at_time < start:
                continue
            if end is not None and at_time >= end:
                continue
            if item.status == AssignmentStatus.TERMINATED and end is None:
                continue
            if item.status not in {AssignmentStatus.ACTIVE, AssignmentStatus.TERMINATED}:
                continue
            result.append(stored)
        return tuple(sorted(result, key=lambda stored: (stored.payload.value_ref, stored.payload.value_revision, stored.record_ref)))

    def evaluate(
        self,
        condition: StateConditionSpec,
        holder_ref: str,
        context_ref: str,
        effective_time_ref: str,
    ) -> tuple[bool | None, tuple[tuple[str, int], ...], tuple[str, ...]]:
        active = self.active_assignments(
            holder_ref, condition.dimension_ref, condition.dimension_revision, context_ref, effective_time_ref
        )
        assignment_pins = tuple((item.record_ref, item.revision) for item in active)
        evidence_refs = tuple(sorted({ref for item in active for ref in item.payload.evidence_refs}))
        if condition.operator == ConditionOperator.KNOWN:
            return bool(active), assignment_pins, evidence_refs
        if condition.operator == ConditionOperator.UNKNOWN:
            return (not active), assignment_pins, evidence_refs
        if not active:
            return None, assignment_pins, evidence_refs
        matches = any(
            item.payload.value_ref == condition.value_ref
            and item.payload.value_revision == condition.value_revision
            for item in active
        )
        if condition.operator == ConditionOperator.EQUALS:
            return matches, assignment_pins, evidence_refs
        if condition.operator == ConditionOperator.NOT_EQUALS:
            return (not matches), assignment_pins, evidence_refs
        raise StateTransitionError(f"unsupported condition operator: {condition.operator}")



class StateDeltaValidator:
    def __init__(self, schemas: SchemaRegistry, resolver: Resolver) -> None:
        self._schemas = schemas
        self._resolver = resolver
        self._conditions = StateConditionEvaluator(resolver)

    def validate(self, delta: StateDelta) -> None:
        dimension = self._schemas.maybe_schema(delta.dimension_ref, delta.dimension_revision)
        if not isinstance(dimension, StateDimensionSchema):
            raise StateTransitionError("state delta must pin an exact state dimension")
        if not schema_authorizes_use(dimension, UseOperation.TRANSITION):
            raise StateTransitionError("state dimension does not authorize active transition use")
        self._require_holder_compatible(delta.holder_ref, dimension.holder_type_refs)
        for value_ref, revision in (
            (delta.from_value_ref, delta.from_value_revision),
            (delta.to_value_ref, delta.to_value_revision),
        ):
            if value_ref is None:
                continue
            value = self._schemas.maybe_schema(value_ref, revision)
            if not isinstance(value, StateValueSchema) or value.dimension_ref != dimension.schema_ref:
                raise StateTransitionError("state delta value is outside the exact dimension domain")
        active = self._conditions.active_assignments(delta.holder_ref, delta.dimension_ref, delta.dimension_revision, delta.context_ref, delta.effective_time_ref)
        if delta.from_value_ref is not None:
            if not any(
                item.payload.value_ref == delta.from_value_ref
                and item.payload.value_revision == delta.from_value_revision
                for item in active
            ):
                raise StateTransitionError("state delta from_value does not match active state")
        if delta.operation in {ChangeOperation.INCREASE, ChangeOperation.DECREASE}:
            if delta.to_value_ref is None:
                raise StateTransitionError(
                    "Phase-11 scalar transition requires an explicit target value; arithmetic magnitude interpretation is not inferred"
                )
            if not dimension.ordered:
                raise StateTransitionError("increase/decrease requires an ordered state dimension")
            if delta.from_value_ref is not None:
                # Direction is defined from the explicitly pinned semantic source value,
                # never from arbitrary list order when multiple assignments are active.
                current = self._schemas.maybe_schema(
                    delta.from_value_ref, delta.from_value_revision
                )
            elif len(active) == 1:
                current = self._schemas.maybe_schema(
                    active[0].payload.value_ref, active[0].payload.value_revision
                )
            elif active:
                raise StateTransitionError(
                    "ordered increase/decrease without from_value requires exactly one active current value"
                )
            else:
                current = None
            target = self._schemas.maybe_schema(delta.to_value_ref, delta.to_value_revision)
            if isinstance(current, StateValueSchema) and isinstance(target, StateValueSchema):
                self._validate_direction(current, target, delta.operation)

    def _require_holder_compatible(self, holder_ref: str, accepted_type_refs: Iterable[str]) -> None:
        accepted = frozenset(accepted_type_refs)
        if not accepted:
            return
        stored = self._resolver.resolve(RecordKind.REFERENT, holder_ref)
        if stored is None:
            raise StateTransitionError(f"state delta holder is unresolved: {holder_ref}")
        referent = stored.payload
        direct = set(getattr(referent, "type_refs", ()))
        for assertion in self._resolver.records(RecordKind.TYPE_ASSERTION):
            item = assertion.payload
            if getattr(item, "referent_ref", None) == holder_ref and getattr(getattr(item, "status", None), "value", None) == "supported":
                direct.add(item.type_schema_ref)
        closure: set[str] = set()
        for type_ref in direct:
            try:
                closure.update(self._schemas.type_closure(type_ref))
            except (KeyError, TypeError):
                continue
        if not closure.intersection(accepted):
            raise StateTransitionError(
                f"state delta holder does not satisfy dimension holder constraints: {sorted(accepted)}"
            )

    @staticmethod
    def _validate_direction(current: StateValueSchema, target: StateValueSchema, operation: ChangeOperation) -> None:
        a, b = current.ordering_key, target.ordering_key
        if a is None or b is None:
            raise StateTransitionError("ordered transition requires ordering keys on current and target values")
        try:
            valid = b > a if operation == ChangeOperation.INCREASE else b < a
        except TypeError as exc:
            raise StateTransitionError("state ordering keys are not mutually comparable") from exc
        if not valid:
            raise StateTransitionError(f"{operation.value} target violates state value ordering")


class StateTimelineProjector:
    """Project immutable assignment revisions from validated state deltas."""

    def __init__(self, schemas: SchemaRegistry, resolver: Resolver) -> None:
        self._schemas = schemas
        self._resolver = resolver
        self._validator = StateDeltaValidator(schemas, resolver)
        self._conditions = StateConditionEvaluator(resolver)

    def project(self, delta: StateDelta) -> StateTimelineProjection:
        require_concrete_timeline_timestamp(delta.effective_time_ref)
        self._validator.validate(delta)
        dimension = self._schemas.schema(delta.dimension_ref, delta.dimension_revision)
        assert isinstance(dimension, StateDimensionSchema)
        self._require_append_only_timeline(delta)
        active = list(self._conditions.active_assignments(delta.holder_ref, delta.dimension_ref, delta.dimension_revision, delta.context_ref, delta.effective_time_ref))
        mutations: list[AssignmentMutation] = []
        projected_active = [stored.payload for stored in active]

        terminate_targets: list[StoredRecord[StateAssignment]] = []
        if delta.operation in {
            ChangeOperation.SET,
            ChangeOperation.ACTIVATE,
            ChangeOperation.RESTORE,
            ChangeOperation.INCREASE,
            ChangeOperation.DECREASE,
        }:
            if dimension.exclusive:
                terminate_targets = [stored for stored in active if stored.payload.value_ref != delta.to_value_ref]
            elif delta.from_value_ref is not None:
                terminate_targets = [stored for stored in active if stored.payload.value_ref == delta.from_value_ref]
        elif delta.operation in {ChangeOperation.TERMINATE, ChangeOperation.DEACTIVATE}:
            terminate_targets = [
                stored for stored in active
                if delta.from_value_ref is None or stored.payload.value_ref == delta.from_value_ref
            ]

        for stored in terminate_targets:
            terminated = replace(
                stored.payload,
                status=AssignmentStatus.TERMINATED,
                valid_to=delta.effective_time_ref,
                proof_refs=tuple(sorted(set(stored.payload.proof_refs) | set(delta.proof_refs))),
            )
            mutations.append(AssignmentMutation(
                assignment_ref=stored.record_ref,
                record_revision=stored.revision + 1,
                expected_record_revision=stored.revision,
                projected=terminated,
            ))
            projected_active = [item for item in projected_active if item.assignment_ref != stored.record_ref]

        if delta.operation in {
            ChangeOperation.SET,
            ChangeOperation.ACTIVATE,
            ChangeOperation.RESTORE,
            ChangeOperation.INCREASE,
            ChangeOperation.DECREASE,
        }:
            assert delta.to_value_ref is not None and delta.to_value_revision is not None
            existing = next((item for item in projected_active if item.value_ref == delta.to_value_ref), None)
            if existing is None:
                assignment_ref = _derived_ref("assignment:transition", delta.delta_ref, delta.to_value_ref)
                created = StateAssignment(
                    assignment_ref=assignment_ref,
                    holder_ref=delta.holder_ref,
                    dimension_ref=delta.dimension_ref,
                    dimension_revision=delta.dimension_revision,
                    value_ref=delta.to_value_ref,
                    value_revision=delta.to_value_revision,
                    status=AssignmentStatus.ACTIVE,
                    context_ref=delta.context_ref,
                    confidence=delta.confidence,
                    valid_from=delta.effective_time_ref,
                    valid_to=None,
                    evidence_refs=(),
                    proof_refs=delta.proof_refs,
                    source_refs=(delta.trigger_ref,),
                )
                mutations.append(AssignmentMutation(
                    assignment_ref=assignment_ref,
                    record_revision=1,
                    expected_record_revision=None,
                    projected=created,
                ))
                projected_active.append(created)

        return StateTimelineProjection(
            holder_ref=delta.holder_ref,
            dimension_ref=delta.dimension_ref,
            context_ref=delta.context_ref,
            mutations=tuple(mutations),
            active_assignments=tuple(sorted(projected_active, key=lambda item: (item.value_ref, item.assignment_ref))),
        )


    def _require_append_only_timeline(self, delta: StateDelta) -> None:
        effective = parse_timeline_timestamp(delta.effective_time_ref)
        latest: dict[str, StoredRecord[StateAssignment]] = {}
        for stored in self._resolver.records(RecordKind.STATE_ASSIGNMENT):
            item = stored.payload
            if not isinstance(item, StateAssignment):
                continue
            if (
                item.holder_ref != delta.holder_ref
                or item.dimension_ref != delta.dimension_ref
                or item.dimension_revision != delta.dimension_revision
                or item.context_ref not in {"global", delta.context_ref}
            ):
                continue
            prior = latest.get(item.assignment_ref)
            if prior is None or stored.revision > prior.revision:
                latest[item.assignment_ref] = stored
        boundaries = []
        for stored in latest.values():
            item = stored.payload
            for value in (item.valid_from, item.valid_to):
                parsed = parse_optional_timeline_timestamp(value)
                if parsed is not None:
                    boundaries.append(parsed)
        if boundaries and effective < max(boundaries):
            raise StateTransitionError(
                "retroactive/out-of-order transition requires replay/invalidation; "
                "Phase 12 will not rewrite an already advanced timeline in place"
            )


def _derived_ref(prefix: str, *parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}:{sha256(payload).hexdigest()[:24]}"


def parse_timeline_timestamp(value: str) -> datetime:
    """Parse a concrete, timezone-aware ISO-8601 timestamp for semantic timelines."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise StateTransitionError(
            "state timeline projection requires an explicit ISO-8601 effective timestamp; "
            "unresolved time referents must remain a transition frontier"
        ) from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise StateTransitionError(
            "state timeline timestamps require an explicit timezone/UTC offset for deterministic ordering"
        )
    return parsed


def parse_optional_timeline_timestamp(value: str | None) -> datetime | None:
    return None if value is None else parse_timeline_timestamp(value)


def require_concrete_timeline_timestamp(value: str) -> None:
    parse_timeline_timestamp(value)
