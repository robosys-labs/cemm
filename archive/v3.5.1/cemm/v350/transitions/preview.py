"""Proof-bearing preview of admitted event effects without durable mutation."""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Protocol

from ..schema.model import SchemaLifecycleStatus
from ..schema.registry import SchemaRegistry
from ..storage.model import RecordKind
from ..uol.model import (
    EventOccurrence,
    FillerRef,
    OccurrenceStatus,
    PortFillerClass,
    SemanticApplication,
    StateDelta,
)
from .admission import EventAdmissionGate
from .compiler import TransitionContractCompiler, TransitionContractError
from .model import (
    TransitionContractRecord,
    TransitionFrontier,
    TransitionPreview,
    TransitionProofRecord,
    UnknownConditionPolicy,
)
from .state import StateConditionEvaluator, StateTransitionError, require_concrete_timeline_timestamp


class Resolver(Protocol):
    def resolve(self, record_kind: RecordKind, record_ref: str, revision: int | None = None) -> Any | None: ...
    def records(self, record_kind: RecordKind) -> tuple[Any, ...]: ...


_NON_TRANSITIONING = frozenset({
    OccurrenceStatus.MENTIONED,
    OccurrenceStatus.CLAIMED,
    OccurrenceStatus.REPORTED,
    OccurrenceStatus.PLANNED,
    OccurrenceStatus.ATTEMPTED,
    OccurrenceStatus.HYPOTHETICAL,
    OccurrenceStatus.COUNTERFACTUAL,
    OccurrenceStatus.FICTIONAL,
    OccurrenceStatus.NON_OCCURRING,
    OccurrenceStatus.PREVENTED,
    OccurrenceStatus.FAILED,
})


class TransitionPreviewEngine:
    def __init__(self, schemas: SchemaRegistry, resolver: Resolver) -> None:
        self._schemas = schemas
        self._resolver = resolver
        self._compiler = TransitionContractCompiler(schemas)
        self._admission = EventAdmissionGate(resolver)
        self._conditions = StateConditionEvaluator(resolver)

    def preview(
        self,
        event: EventOccurrence,
        contract: TransitionContractRecord,
        *,
        effective_time_ref: str,
    ) -> TransitionPreview:
        blocked: list[str] = []
        frontiers: list[TransitionFrontier] = []
        try:
            require_concrete_timeline_timestamp(effective_time_ref)
        except StateTransitionError:
            frontiers.append(TransitionFrontier(
                frontier_ref=_ref("transition-frontier", event.event_ref, contract.contract_ref, "effective-time"),
                reason="transition_effective_time_unresolved",
                dependency_refs=(effective_time_ref,),
            ))
            blocked.append("transition_frontier_unresolved")
            return TransitionPreview(
                event.event_ref, contract.contract_ref, contract.revision, (), None,
                tuple(frontiers), tuple(sorted(set(blocked))),
            )

        event_stored = self._resolver.resolve(RecordKind.EVENT_OCCURRENCE, event.event_ref)
        if event_stored is None or event_stored.payload != event:
            blocked.append("event_occurrence_not_exactly_stored")
            return TransitionPreview(
                event.event_ref, contract.contract_ref, contract.revision, (), None,
                tuple(frontiers), tuple(sorted(set(blocked))),
            )
        event_revision = event_stored.revision

        for stored_proof in self._resolver.records(RecordKind.TRANSITION_PROOF):
            existing = stored_proof.payload
            if (
                isinstance(existing, TransitionProofRecord)
                and existing.event_ref == event.event_ref
                and existing.event_revision == event_revision
                and existing.transition_contract_ref == contract.contract_ref
                and existing.transition_contract_revision == contract.revision
                and existing.context_ref == event.context_ref
            ):
                blocked.append("transition_already_committed_for_event_contract")
                break

        if event.occurrence_status in _NON_TRANSITIONING:
            blocked.append(f"event_status_not_transitioning:{event.occurrence_status.value}")
        if contract.lifecycle_status != SchemaLifecycleStatus.ACTIVE:
            blocked.append("transition_contract_not_active")
        try:
            compiled = self._compiler.compile(contract)
        except TransitionContractError as exc:
            blocked.append(f"transition_contract_invalid:{exc}")
            return TransitionPreview(event.event_ref, contract.contract_ref, contract.revision, (), None, (), tuple(blocked))
        if event.event_schema_ref != contract.trigger_schema_ref or event.event_schema_revision != contract.trigger_schema_revision:
            blocked.append("transition_contract_trigger_mismatch")

        application_stored = self._resolver.resolve(RecordKind.SEMANTIC_APPLICATION, event.participant_application_ref)
        if application_stored is None or not isinstance(application_stored.payload, SemanticApplication):
            blocked.append("event_participant_application_unresolved")
            return TransitionPreview(event.event_ref, contract.contract_ref, contract.revision, (), None, (), tuple(sorted(set(blocked))))
        application = application_stored.payload
        application_revision = application_stored.revision
        admission = self._admission.assess(
            event, participant_application_revision=application_revision
        )
        if not admission.admitted:
            blocked.extend(admission.reasons or ("event_not_epistemically_admitted",))
        if application.application_ref != event.participant_application_ref:
            blocked.append("event_participant_application_ref_mismatch")
        if application.schema_ref != event.event_schema_ref or application.schema_revision != event.event_schema_revision:
            blocked.append("event_participant_application_schema_mismatch")
        if application.context_ref != event.context_ref:
            blocked.append("event_participant_application_context_mismatch")

        bound_referents: dict[str, str] = {}
        bound_refs: dict[str, str] = {}
        for port_ref in compiled.trigger_port_refs:
            binding = application.binding(port_ref)
            if binding is None or not binding.fillers:
                frontiers.append(TransitionFrontier(
                    frontier_ref=_ref("transition-frontier", event.event_ref, contract.contract_ref, port_ref),
                    reason="required_transition_binding_unresolved",
                    dependency_refs=(port_ref,),
                ))
                continue
            if len(binding.fillers) != 1 or not isinstance(binding.fillers[0], FillerRef):
                frontiers.append(TransitionFrontier(
                    frontier_ref=_ref("transition-frontier", event.event_ref, contract.contract_ref, port_ref),
                    reason="transition_binding_not_single_reference",
                    dependency_refs=(port_ref,),
                ))
                continue
            filler = binding.fillers[0]
            bound_refs[port_ref] = filler.ref
            if filler.filler_class == PortFillerClass.REFERENT:
                bound_referents[port_ref] = filler.ref

        condition_assignment_pins: set[tuple[str, int]] = set()
        condition_evidence_refs: set[str] = set()
        for condition in contract.state_conditions:
            holder = bound_referents.get(condition.holder_port_ref)
            if holder is None:
                frontiers.append(TransitionFrontier(
                    frontier_ref=_ref("transition-frontier", event.event_ref, condition.condition_ref),
                    reason="condition_holder_unresolved",
                    dependency_refs=(condition.holder_port_ref,),
                ))
                continue
            result, assignment_pins, evidence_refs = self._conditions.evaluate(condition, holder, event.context_ref, effective_time_ref)
            condition_assignment_pins.update(assignment_pins)
            condition_evidence_refs.update(evidence_refs)
            if result is False:
                blocked.append(f"transition_condition_unsatisfied:{condition.condition_ref}")
            elif result is None:
                if condition.unknown_policy == UnknownConditionPolicy.BLOCK:
                    blocked.append(f"transition_condition_unknown:{condition.condition_ref}")
                else:
                    frontiers.append(TransitionFrontier(
                        frontier_ref=_ref("transition-frontier", event.event_ref, condition.condition_ref),
                        reason="transition_condition_unknown",
                        dependency_refs=(condition.condition_ref,),
                    ))

        if frontiers:
            blocked.append("transition_frontier_unresolved")
        if blocked:
            return TransitionPreview(
                event.event_ref, contract.contract_ref, contract.revision, (), None,
                tuple(sorted(frontiers, key=lambda item: item.frontier_ref)),
                tuple(sorted(set(blocked))),
            )

        runtime_targets: set[tuple[str, str, int, str]] = set()
        for effect in contract.state_effects:
            holder = bound_referents.get(effect.holder_port_ref)
            if holder is None:
                continue
            target = (holder, effect.dimension_ref, effect.dimension_revision, event.context_ref)
            if target in runtime_targets:
                frontiers.append(TransitionFrontier(
                    frontier_ref=_ref("transition-frontier", event.event_ref, contract.contract_ref, "duplicate-runtime-target", *target),
                    reason="multiple_transition_effects_resolve_to_same_runtime_state_target",
                    dependency_refs=(effect.effect_ref, holder, effect.dimension_ref),
                ))
            runtime_targets.add(target)
        if frontiers:
            return TransitionPreview(
                event.event_ref, contract.contract_ref, contract.revision, (), None,
                tuple(sorted(frontiers, key=lambda item: item.frontier_ref)),
                tuple(sorted(set((*blocked, "transition_frontier_unresolved")))),
            )

        proof_material = repr((
            event.event_ref, event_revision, application.application_ref, application_revision,
            contract.contract_ref, contract.revision, tuple(sorted(admission.admission_pins)),
            tuple(sorted(condition_assignment_pins)), effective_time_ref,
            tuple((
                item.effect_ref, bound_referents.get(item.holder_port_ref), item.dimension_ref,
                item.dimension_revision, item.operation.value, item.from_value_ref, item.from_value_revision,
                item.to_value_ref, item.to_value_revision,
                bound_refs.get(item.magnitude_port_ref) if item.magnitude_port_ref else None,
            ) for item in contract.state_effects),
        ))
        proof_ref = _ref("transition-proof", proof_material)
        deltas: list[StateDelta] = []
        for effect in contract.state_effects:
            holder = bound_referents.get(effect.holder_port_ref)
            if holder is None:
                raise AssertionError("compiled transition effect holder became unresolved after frontier gate")
            magnitude_ref = bound_refs.get(effect.magnitude_port_ref) if effect.magnitude_port_ref else None
            delta_ref = _ref("state-delta", proof_ref, effect.effect_ref, holder)
            deltas.append(StateDelta(
                delta_ref=delta_ref,
                trigger_ref=event.event_ref,
                holder_ref=holder,
                dimension_ref=effect.dimension_ref,
                dimension_revision=effect.dimension_revision,
                operation=effect.operation,
                context_ref=event.context_ref,
                effective_time_ref=effective_time_ref,
                from_value_ref=effect.from_value_ref,
                from_value_revision=effect.from_value_revision,
                to_value_ref=effect.to_value_ref,
                to_value_revision=effect.to_value_revision,
                magnitude_ref=magnitude_ref,
                confidence=min(effect.confidence, application.confidence, admission.confidence),
                proof_refs=(proof_ref,),
            ))
        proof = TransitionProofRecord(
            proof_ref=proof_ref,
            event_ref=event.event_ref,
            event_revision=event_revision,
            participant_application_ref=application.application_ref,
            participant_application_revision=application_revision,
            transition_contract_ref=contract.contract_ref,
            transition_contract_revision=contract.revision,
            admission_pins=admission.admission_pins,
            condition_evidence_refs=tuple(sorted(condition_evidence_refs)),
            input_assignment_pins=tuple(sorted(condition_assignment_pins)),
            derived_state_delta_refs=tuple(item.delta_ref for item in deltas),
            context_ref=event.context_ref,
            effective_time_ref=effective_time_ref,
            confidence=min([1.0, *[item.confidence for item in deltas]]),
            evidence_refs=tuple(sorted(set(admission.evidence_refs) | set(contract.evidence_refs))),
        )

        return TransitionPreview(
            event_ref=event.event_ref,
            contract_ref=contract.contract_ref,
            contract_revision=contract.revision,
            state_deltas=tuple(deltas),
            proof=proof,
            frontiers=(),
            blocked_reasons=(),
        )


def _ref(prefix: str, *parts: str) -> str:
    payload = "\x1f".join(parts).encode("utf-8")
    return f"{prefix}:{sha256(payload).hexdigest()[:24]}"
