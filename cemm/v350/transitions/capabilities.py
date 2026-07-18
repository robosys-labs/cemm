"""Generic capability dependency reevaluation after projected state changes."""
from __future__ import annotations

from dataclasses import replace
from hashlib import sha256
from typing import Any, Iterable, Protocol

from ..schema.model import SchemaLifecycleStatus
from ..schema.registry import SchemaRegistry
from ..storage.model import CapabilityInstance, RecordKind, StoredRecord
from ..uol.model import CapabilityDelta, CapabilityStatus
from .compiler import TransitionContractCompiler
from .model import (
    CapabilityDependencyRecord,
    CapabilityProjection,
    ConditionOperator,
    StateTimelineProjection,
)
from .state import StateConditionEvaluator


class Resolver(Protocol):
    def resolve(self, record_kind: RecordKind, record_ref: str, revision: int | None = None) -> Any | None: ...
    def records(self, record_kind: RecordKind) -> tuple[Any, ...]: ...


class CapabilityDependencyEngine:
    def __init__(self, schemas: SchemaRegistry, resolver: Resolver) -> None:
        self._schemas = schemas
        self._resolver = resolver
        self._compiler = TransitionContractCompiler(schemas)
        self._conditions = StateConditionEvaluator(resolver)

    def evaluate(
        self,
        dependency: CapabilityDependencyRecord,
        *,
        holder_ref: str,
        context_ref: str,
        effective_time_ref: str,
        trigger_ref: str,
        proof_refs: tuple[str, ...],
        state_projections: tuple[StateTimelineProjection, ...] = (),
    ) -> CapabilityProjection | None:
        if dependency.lifecycle_status != SchemaLifecycleStatus.ACTIVE:
            return None
        self._compiler.validate_capability_dependency(dependency)
        if not self._holder_compatible(holder_ref, dependency.holder_type_refs):
            return None

        outcomes: list[bool | None] = []
        for condition in dependency.state_conditions:
            projected = next((
                projection for projection in state_projections
                if projection.holder_ref == holder_ref
                and projection.dimension_ref == condition.dimension_ref
                and projection.context_ref == context_ref
            ), None)
            if projected is None:
                result, _, _ = self._conditions.evaluate(condition, holder_ref, context_ref, effective_time_ref)
            else:
                values = tuple((item.value_ref, item.value_revision) for item in projected.active_assignments)
                target = (condition.value_ref, condition.value_revision)
                if condition.operator == ConditionOperator.KNOWN:
                    result = bool(values)
                elif condition.operator == ConditionOperator.UNKNOWN:
                    result = not values
                elif not values:
                    result = None
                elif condition.operator == ConditionOperator.EQUALS:
                    result = target in values
                elif condition.operator == ConditionOperator.NOT_EQUALS:
                    result = target not in values
                else:
                    result = None
            outcomes.append(result)

        if any(item is False for item in outcomes):
            new_status = dependency.status_if_unsatisfied
        elif any(item is None for item in outcomes):
            new_status = dependency.status_if_unknown
        else:
            new_status = dependency.status_if_satisfied

        current = self._current_capability(holder_ref, dependency.action_schema_ref, context_ref)
        prior_status = current.payload.status if current is not None else CapabilityStatus.UNKNOWN
        if prior_status == new_status:
            return None

        derivation_confidence = self._derivation_confidence(
            dependency, holder_ref=holder_ref, context_ref=context_ref,
            effective_time_ref=effective_time_ref, proof_refs=proof_refs,
            state_projections=state_projections,
        )
        delta_ref = _ref(
            "capability-delta", trigger_ref, dependency.dependency_ref,
            holder_ref, dependency.action_schema_ref, effective_time_ref,
        )
        delta = CapabilityDelta(
            delta_ref=delta_ref,
            trigger_ref=trigger_ref,
            holder_ref=holder_ref,
            action_schema_ref=dependency.action_schema_ref,
            action_schema_revision=dependency.action_schema_revision,
            prior_status=prior_status,
            new_status=new_status,
            context_ref=context_ref,
            effective_time_ref=effective_time_ref,
            dependency_ref=dependency.dependency_ref,
            confidence=derivation_confidence,
            proof_refs=proof_refs,
        )
        if current is None:
            capability_ref = _ref("capability:derived", holder_ref, dependency.action_schema_ref, context_ref)
            projected_instance = CapabilityInstance(
                capability_ref=capability_ref,
                holder_ref=holder_ref,
                action_schema_ref=dependency.action_schema_ref,
                action_schema_revision=dependency.action_schema_revision,
                status=new_status,
                confidence=derivation_confidence,
                context_ref=context_ref,
                valid_from=effective_time_ref,
                dependency_refs=(dependency.dependency_ref,),
                evidence_refs=dependency.evidence_refs,
                proof_refs=proof_refs,
            )
            return CapabilityProjection(delta, projected_instance, 1, None)

        merged_dependencies = tuple(sorted(set(current.payload.dependency_refs) | {dependency.dependency_ref}))
        projected_instance = replace(
            current.payload,
            status=new_status,
            confidence=derivation_confidence,
            valid_from=effective_time_ref,
            valid_to=None,
            dependency_refs=merged_dependencies,
            evidence_refs=tuple(sorted(set(current.payload.evidence_refs) | set(dependency.evidence_refs))),
            proof_refs=tuple(sorted(set(current.payload.proof_refs) | set(proof_refs))),
        )
        return CapabilityProjection(delta, projected_instance, current.revision + 1, current.revision)

    def _derivation_confidence(
        self,
        dependency: CapabilityDependencyRecord,
        *,
        holder_ref: str,
        context_ref: str,
        effective_time_ref: str,
        proof_refs: tuple[str, ...],
        state_projections: tuple[StateTimelineProjection, ...],
    ) -> float:
        confidences: list[float] = []
        for proof_ref in proof_refs:
            stored = self._resolver.resolve(RecordKind.TRANSITION_PROOF, proof_ref)
            if stored is not None:
                confidence = getattr(stored.payload, "confidence", None)
                if isinstance(confidence, (int, float)):
                    confidences.append(float(confidence))
        for condition in dependency.state_conditions:
            projected = next((
                projection for projection in state_projections
                if projection.holder_ref == holder_ref
                and projection.dimension_ref == condition.dimension_ref
                and projection.context_ref == context_ref
            ), None)
            if projected is not None:
                confidences.extend(item.confidence for item in projected.active_assignments)
            else:
                assignments = self._conditions.active_assignments(
                    holder_ref, condition.dimension_ref, condition.dimension_revision,
                    context_ref, effective_time_ref,
                )
                confidences.extend(item.payload.confidence for item in assignments)
        return min(confidences) if confidences else 1.0

    def applicable_dependencies(self, holder_ref: str) -> tuple[CapabilityDependencyRecord, ...]:
        result: list[CapabilityDependencyRecord] = []
        latest: dict[str, tuple[int, CapabilityDependencyRecord]] = {}
        for stored in self._resolver.records(RecordKind.CAPABILITY_DEPENDENCY):
            item = stored.payload
            if not isinstance(item, CapabilityDependencyRecord):
                continue
            prior = latest.get(item.dependency_ref)
            if prior is None or stored.revision > prior[0]:
                latest[item.dependency_ref] = (stored.revision, item)
        for _, item in latest.values():
            if item.lifecycle_status == SchemaLifecycleStatus.ACTIVE and self._holder_compatible(holder_ref, item.holder_type_refs):
                result.append(item)
        return tuple(sorted(result, key=lambda item: (item.action_schema_ref, item.dependency_ref)))

    def _current_capability(
        self, holder_ref: str, action_schema_ref: str, context_ref: str
    ) -> StoredRecord[CapabilityInstance] | None:
        candidates: dict[str, StoredRecord[CapabilityInstance]] = {}
        for stored in self._resolver.records(RecordKind.CAPABILITY_INSTANCE):
            item = stored.payload
            if not isinstance(item, CapabilityInstance):
                continue
            if item.holder_ref != holder_ref or item.action_schema_ref != action_schema_ref:
                continue
            if item.context_ref not in {"global", context_ref}:
                continue
            prior = candidates.get(item.capability_ref)
            if prior is None or stored.revision > prior.revision:
                candidates[item.capability_ref] = stored
        if not candidates:
            return None
        exact_context = [item for item in candidates.values() if item.payload.context_ref == context_ref]
        pool = exact_context or [item for item in candidates.values() if item.payload.context_ref == "global"]
        return max(pool, key=lambda item: (item.revision, item.record_ref)) if pool else None

    def _holder_compatible(self, holder_ref: str, accepted_type_refs: Iterable[str]) -> bool:
        accepted = frozenset(accepted_type_refs)
        if not accepted:
            return True
        stored = self._resolver.resolve(RecordKind.REFERENT, holder_ref)
        if stored is None:
            return False
        direct = set(getattr(stored.payload, "type_refs", ()))
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
        return bool(closure.intersection(accepted))


def _ref(prefix: str, *parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}:{sha256(payload).hexdigest()[:24]}"
