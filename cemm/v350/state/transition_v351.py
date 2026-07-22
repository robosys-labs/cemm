"""Role-addressed, domain-generic transition preview for CEMM v3.5.1 Phase 15."""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Any, Callable, Iterable, Mapping

from ..csir.model import ExactAuthorityPin
from ..schema.model import semantic_fingerprint
from .algebra_v351 import StateAlgebraV351
from .model_v351 import (
    ConditionOperatorV351, MechanismPrecondition, MechanismTriggerKind, OperandKind,
    ParticipantRoleBinding, RoleStateTransformV351, SecondaryEventCandidateV351,
    StateDeltaV351, StateDomainContractV351, StateModelError, StateOperandV351,
    StateTransformExpression, StateValueV351, TransitionDistribution, TransitionMechanismV351,
    TransitionPreviewProof, UnknownConditionPolicyV351,
)


@dataclass(frozen=True, slots=True)
class StateKeyV351:
    holder_ref: str
    dimension_pin: ExactAuthorityPin
    context_ref: str

    def __post_init__(self) -> None:
        if not self.holder_ref or not self.context_ref:
            raise StateModelError("state key requires holder and context refs")

    @property
    def key(self):
        return (self.holder_ref, self.dimension_pin.key, self.context_ref)


@dataclass(frozen=True, slots=True)
class StateSnapshotV351:
    values: tuple[tuple[StateKeyV351, StateValueV351], ...]
    domains: tuple[tuple[tuple, StateDomainContractV351], ...]
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        keys = tuple(item.key for item, _ in self.values)
        if len(keys) != len(set(keys)):
            raise StateModelError("state snapshot has duplicate holder/dimension/context keys")
        domain_keys = tuple(key for key, _ in self.domains)
        if len(domain_keys) != len(set(domain_keys)):
            raise StateModelError("state snapshot has duplicate dimension-domain contracts")
        domain_map = dict(self.domains)
        for exact_key, domain in self.domains:
            if len(exact_key) != 6 or exact_key[2] != domain.dimension_ref or int(exact_key[3]) != domain.dimension_revision:
                raise StateModelError("state snapshot domain key differs from exact dimension contract")
        for key, value in self.values:
            domain = domain_map.get(key.dimension_pin.key)
            if domain is None:
                raise StateModelError("state snapshot value lacks exact dimension-domain contract")
            if value.domain_kind is not domain.kind:
                raise StateModelError("state snapshot value domain kind differs from exact dimension contract")
        if len(self.proof_refs) != len(set(self.proof_refs)):
            raise StateModelError("state snapshot proof refs must be unique")

    def value(self, holder_ref: str, dimension_pin: ExactAuthorityPin, context_ref: str) -> StateValueV351 | None:
        exact = [value for key, value in self.values if key.holder_ref == holder_ref and key.dimension_pin.key == dimension_pin.key and key.context_ref == context_ref]
        if exact:
            return exact[0]
        global_values = [value for key, value in self.values if key.holder_ref == holder_ref and key.dimension_pin.key == dimension_pin.key and key.context_ref == "global"]
        return global_values[0] if global_values else None

    def domain(self, dimension_pin: ExactAuthorityPin) -> StateDomainContractV351:
        for key, domain in self.domains:
            if key == dimension_pin.key:
                return domain
        raise StateModelError(f"missing exact state-domain contract:{dimension_pin.key}")

    def with_value(self, holder_ref: str, dimension_pin: ExactAuthorityPin, context_ref: str, value: StateValueV351 | None):
        key = StateKeyV351(holder_ref, dimension_pin, context_ref)
        kept = [(k, v) for k, v in self.values if k.key != key.key]
        if value is not None:
            kept.append((key, value))
        return StateSnapshotV351(tuple(sorted(kept, key=lambda item: str(item[0].key))), self.domains, self.proof_refs)


@dataclass(frozen=True, slots=True)
class CausalEventV351:
    event_ref: str
    predicate_pin: ExactAuthorityPin
    role_bindings: tuple[ParticipantRoleBinding, ...]
    context_ref: str
    effective_time_ref: str
    time_step: int = 0
    causal_depth: int = 0
    evidence_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()
    occurrence_kind: str = "actual"
    source_delta: StateDeltaV351 | None = None
    causal_parent_step_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in ((self.event_ref, "event_ref"), (self.context_ref, "event context_ref"), (self.effective_time_ref, "event time")):
            if not value: raise StateModelError(f"{label} is required")
        if self.time_step < 0: raise StateModelError("event time_step cannot be negative")
        if self.causal_depth < 0: raise StateModelError("event causal_depth cannot be negative")
        keys = tuple(item.role_pin.key for item in self.role_bindings)
        if len(keys) != len(set(keys)): raise StateModelError("event role bindings must be unique")
        if len(self.causal_parent_step_refs) != len(set(self.causal_parent_step_refs)):
            raise StateModelError("event causal parent steps must be unique")
        if len(self.evidence_refs) != len(set(self.evidence_refs)) or len(self.proof_refs) != len(set(self.proof_refs)):
            raise StateModelError("causal event evidence/proof refs must be unique")
        if not self.occurrence_kind:
            raise StateModelError("causal event occurrence kind is required")

    def participant(self, role_pin: ExactAuthorityPin) -> str | None:
        for item in self.role_bindings:
            if item.role_pin.key == role_pin.key:
                return item.participant_ref
        return None


@dataclass(frozen=True, slots=True)
class TransitionPreviewResultV351:
    distributions: tuple[TransitionDistribution, ...]
    frontier_refs: tuple[str, ...] = ()


class TransitionPreviewEngineV351:
    """Evaluate exact mechanisms without mutating durable state.

    The engine never branches on event names, lexical forms, grammatical voice, or subject/
    object positions. Consequences are addressed exclusively through exact semantic role pins.
    """

    def __init__(
        self, *,
        parameter_lookup: Callable[[ExactAuthorityPin, str], float] | None = None,
        algebra: StateAlgebraV351 | None = None,
    ) -> None:
        self.algebra = algebra or StateAlgebraV351()
        self.parameter_lookup = parameter_lookup or (
            lambda pin, name: (_raise(StateModelError(f"missing parameter:{pin.key}:{name}")))
        )

    def preview_event(
        self,
        event: CausalEventV351,
        mechanisms: Iterable[TransitionMechanismV351],
        snapshot: StateSnapshotV351,
        *,
        event_port_values: Mapping[tuple, Any] | None = None,
    ) -> TransitionPreviewResultV351:
        event_port_values = dict(event_port_values or {})
        distributions = []
        frontiers = []
        for mechanism in sorted(mechanisms, key=lambda item: item.mechanism_pin_sort_key if hasattr(item, "mechanism_pin_sort_key") else item.authority_pin.key):
            if not mechanism.executable:
                continue
            if mechanism.trigger_kind not in {MechanismTriggerKind.EVENT, MechanismTriggerKind.EXOGENOUS}:
                continue
            if mechanism.trigger_kind is MechanismTriggerKind.EXOGENOUS and event.occurrence_kind != "exogenous":
                continue
            if mechanism.trigger_kind is MechanismTriggerKind.EVENT and event.occurrence_kind == "exogenous":
                continue
            if mechanism.trigger_definition_pin is None or mechanism.trigger_definition_pin.key != event.predicate_pin.key:
                continue
            result = self._preview(mechanism, event, snapshot, event_port_values=event_port_values)
            if isinstance(result, TransitionDistribution):
                distributions.append(result)
            else:
                frontiers.extend(result)
        return TransitionPreviewResultV351(tuple(distributions), tuple(sorted(set(frontiers))))

    def preview_state_change(
        self,
        *,
        source_delta: StateDeltaV351,
        role_bindings: tuple[ParticipantRoleBinding, ...],
        mechanisms: Iterable[TransitionMechanismV351],
        snapshot: StateSnapshotV351,
        time_step: int,
    ) -> TransitionPreviewResultV351:
        distributions = []
        frontiers = []
        event = CausalEventV351(
            event_ref="state-change-trigger:" + semantic_fingerprint("state-change-trigger-v351", source_delta.delta_ref, 24),
            predicate_pin=source_delta.mechanism_pin,
            role_bindings=role_bindings,
            context_ref=source_delta.context_ref,
            effective_time_ref=source_delta.effective_time_ref,
            time_step=time_step,
            proof_refs=source_delta.proof_refs,
            occurrence_kind="derived_state_change",
        )
        for mechanism in sorted(mechanisms, key=lambda item: item.authority_pin.key):
            if not mechanism.executable or mechanism.trigger_kind != MechanismTriggerKind.STATE_CHANGE:
                continue
            if source_delta.dimension_pin.key not in {pin.key for pin in mechanism.source_dimension_pins}:
                continue
            result = self._preview(mechanism, event, snapshot, event_port_values={})
            if isinstance(result, TransitionDistribution): distributions.append(result)
            else: frontiers.extend(result)
        return TransitionPreviewResultV351(tuple(distributions), tuple(sorted(set(frontiers))))

    def _preview(self, mechanism, event, snapshot, *, event_port_values):
        if (
            mechanism.context_scopes
            and event.context_ref not in mechanism.context_scopes
            and "global" not in mechanism.context_scopes
        ):
            return ()
        role_map = {item.role_pin.key: item for item in event.role_bindings}
        missing_roles = [pin for pin in mechanism.participant_role_pins if pin.key not in role_map]
        if missing_roles:
            return tuple(f"frontier:transition:missing-role:{pin.ref}" for pin in missing_roles)
        if mechanism.participant_type_requirements:
            for role_pin, required_types in mechanism.participant_type_requirements:
                binding = role_map.get(role_pin.key)
                if binding is None:
                    return (f"frontier:transition:missing-role:{role_pin.ref}",)
                actual = {pin.key for pin in binding.participant_type_pins}
                if required_types and not actual.intersection(pin.key for pin in required_types):
                    return ()  # mechanism simply does not apply to this participant type

        precondition_results = []
        prestate_refs = []
        evidence_refs = list((
            *mechanism.evidence_refs, *event.evidence_refs,
            *(ref for binding in event.role_bindings for ref in binding.evidence_refs),
        ))
        for condition in mechanism.preconditions:
            try:
                outcome, state_ref = self._condition(condition, role_map, snapshot, event.context_ref)
            except StateModelError as exc:
                return (f"frontier:transition:precondition-domain-invalid:{condition.condition_ref}:{type(exc).__name__}",)
            precondition_results.append((condition.condition_ref, outcome))
            if state_ref: prestate_refs.append(state_ref)
            if outcome == "false": return ()
            if outcome == "unknown":
                if condition.unknown_policy == UnknownConditionPolicyV351.BLOCK: return ()
                if condition.unknown_policy == UnknownConditionPolicyV351.PRESERVE_FRONTIER:
                    return (f"frontier:transition:precondition-unknown:{condition.condition_ref}",)
                return (f"frontier:transition:precondition-branch-required:{condition.condition_ref}",)

        defeater_results = []
        attenuation = 1.0
        for defeater in mechanism.defeaters:
            try:
                outcome, state_ref = self._condition(defeater.condition, role_map, snapshot, event.context_ref)
            except StateModelError as exc:
                return (f"frontier:transition:defeater-domain-invalid:{defeater.defeater_ref}:{type(exc).__name__}",)
            defeater_results.append((defeater.defeater_ref, outcome))
            if state_ref: prestate_refs.append(state_ref)
            if outcome == "true":
                if defeater.hard: return ()
                attenuation *= defeater.attenuation
            elif outcome == "unknown":
                if defeater.condition.unknown_policy == UnknownConditionPolicyV351.BLOCK:
                    # Unknown possible defeater under BLOCK may not be treated as absent.
                    return ()
                if defeater.condition.unknown_policy == UnknownConditionPolicyV351.PRESERVE_FRONTIER:
                    return (f"frontier:transition:defeater-unknown:{defeater.defeater_ref}",)
                # BRANCH requires an exact uncertainty/prior contract; never invent 50/50 mass.
                return (f"frontier:transition:defeater-branch-required:{defeater.defeater_ref}",)

        materialized = []
        if mechanism.branches:
            branch_payloads = [(branch.branch_ref, branch.probability, branch.transforms, branch.secondary_events) for branch in mechanism.branches]
        else:
            branch_payloads = [("deterministic", 1.0, mechanism.deterministic_transforms, mechanism.deterministic_secondary_events)]

        for branch_ref, probability, transforms, secondary in branch_payloads:
            deltas = []
            secondary_events = []
            for transform in transforms:
                binding = role_map.get(transform.target_role_pin.key)
                if binding is None:
                    return (f"frontier:transition:target-role-unbound:{transform.target_role_pin.ref}",)
                domain = snapshot.domain(transform.dimension_pin)
                current = snapshot.value(binding.participant_ref, transform.dimension_pin, event.context_ref)
                def resolve_operand(operand):
                    return self._operand(
                        operand, current=current, role_map=role_map, snapshot=snapshot,
                        context_ref=event.context_ref, event_port_values=event_port_values,
                    )
                try:
                    new_value = self.algebra.apply(
                        domain, current, transform.expression, resolve_operand=resolve_operand
                    )
                except StateModelError as exc:
                    # Missing operands/evaluators/domain mismatch are semantic frontiers, not
                    # reasons to crash the entire cognitive pass or guess a transition.
                    return (
                        "frontier:transition:transform-unresolved:"
                        + transform.transform_ref + ":" + type(exc).__name__,
                    )
                delta_ref = "state-delta-v351:" + semantic_fingerprint(
                    "state-delta-v351",
                    (event.event_ref, mechanism.authority_pin.key, branch_ref, transform.transform_ref,
                     binding.participant_ref, transform.dimension_pin.key,
                     None if current is None else current.value_ref,
                     None if new_value is None else new_value.value_ref), 32,
                )
                deltas.append(StateDeltaV351(
                    delta_ref=delta_ref,
                    holder_ref=binding.participant_ref,
                    dimension_pin=transform.dimension_pin,
                    prior_value=current,
                    new_value=new_value,
                    transform_ref=transform.transform_ref,
                    mechanism_pin=mechanism.authority_pin,
                    context_ref=event.context_ref,
                    effective_time_ref=event.effective_time_ref,
                    confidence=transform.confidence * attenuation,
                    time_step=event.time_step + 1,
                    branch_probability=probability,
                    proof_refs=event.proof_refs,
                    evidence_refs=tuple(sorted(set((*event.evidence_refs, *mechanism.evidence_refs)))),
                ))
            for template in secondary:
                mapped = []
                for source_role, target_role in template.role_map:
                    source = role_map.get(source_role.key)
                    if source is None:
                        return (f"frontier:transition:secondary-source-role-unbound:{source_role.ref}",)
                    mapped.append(ParticipantRoleBinding(
                        role_pin=target_role,
                        participant_ref=source.participant_ref,
                        source_application_ref=event.event_ref,
                        participant_type_pins=source.participant_type_pins,
                        evidence_refs=source.evidence_refs,
                        proof_refs=source.proof_refs,
                    ))
                secondary_events.append(SecondaryEventCandidateV351(
                    event_ref="secondary-event:" + semantic_fingerprint(
                        "secondary-event-v351", (event.event_ref, mechanism.authority_pin.key, branch_ref, template.template_ref), 32,
                    ),
                    event_definition_pin=template.event_definition_pin,
                    role_bindings=tuple(mapped),
                    context_ref=event.context_ref,
                    time_step=event.time_step + template.delay_steps + 1,
                    source_mechanism_pin=mechanism.authority_pin,
                    branch_probability=probability,
                    proof_refs=event.proof_refs,
                ))
            proof_ref = "transition-preview-proof:" + semantic_fingerprint(
                "transition-preview-proof-v351",
                (event.event_ref, mechanism.authority_pin.key, branch_ref,
                 tuple(item.delta_ref for item in deltas), tuple(item.event_ref for item in secondary_events),
                 tuple(precondition_results), tuple(defeater_results), event.context_ref), 40,
            )
            proof = TransitionPreviewProof(
                proof_ref=proof_ref,
                mechanism_pin=mechanism.authority_pin,
                trigger_ref=event.event_ref,
                role_bindings=event.role_bindings,
                prestate_refs=tuple(sorted(set(prestate_refs))),
                precondition_results=tuple(precondition_results),
                defeater_results=tuple(defeater_results),
                derived_delta_refs=tuple(item.delta_ref for item in deltas),
                secondary_event_refs=tuple(item.event_ref for item in secondary_events),
                context_ref=event.context_ref,
                branch_ref=branch_ref,
                branch_probability=probability,
                evidence_refs=tuple(sorted(set(evidence_refs))),
                parent_proof_refs=event.proof_refs,
            )
            deltas = tuple(_attach_proof(delta, proof_ref) for delta in deltas)
            secondary_events = tuple(_attach_event_proof(item, proof_ref) for item in secondary_events)
            materialized.append((branch_ref, probability, deltas, secondary_events, proof))

        return TransitionDistribution(
            distribution_ref="transition-distribution:" + semantic_fingerprint(
                "transition-distribution-v351", (event.event_ref, mechanism.authority_pin.key, tuple((x[0], x[1]) for x in materialized)), 32,
            ),
            mechanism_pin=mechanism.authority_pin,
            trigger_ref=event.event_ref,
            branches=tuple(materialized),
        )

    def _condition(self, condition: MechanismPrecondition, role_map, snapshot, context_ref):
        binding = role_map.get(condition.holder_role_pin.key)
        if binding is None: return "unknown", ""
        current = snapshot.value(binding.participant_ref, condition.dimension_pin, context_ref)
        domain = snapshot.domain(condition.dimension_pin)
        if current is not None:
            self.algebra.validate_value(domain, current)
        if condition.expected_value is not None:
            expected_domain = (
                self.algebra._support_domain(domain)
                if condition.operator is ConditionOperatorV351.PROBABILITY_AT_LEAST
                else domain
            )
            self.algebra.validate_value(expected_domain, condition.expected_value)
        state_ref = "" if current is None else current.value_ref
        op = condition.operator
        if op == ConditionOperatorV351.KNOWN: return ("true" if current is not None else "unknown"), state_ref
        if op == ConditionOperatorV351.UNKNOWN: return ("true" if current is None else "false"), state_ref
        if current is None: return "unknown", state_ref
        expected = condition.expected_value
        if op in {ConditionOperatorV351.EQUALS, ConditionOperatorV351.NOT_EQUALS}:
            equal = expected is not None and current.value_ref == expected.value_ref
            return ("true" if (equal if op == ConditionOperatorV351.EQUALS else not equal) else "false"), state_ref
        if op in {ConditionOperatorV351.LESS_THAN, ConditionOperatorV351.LESS_EQUAL, ConditionOperatorV351.GREATER_THAN, ConditionOperatorV351.GREATER_EQUAL}:
            if expected is None:
                return "unknown", state_ref
            try:
                comparison = self.algebra.compare(domain, current, expected)
            except StateModelError:
                return "unknown", state_ref
            checks = {
                ConditionOperatorV351.LESS_THAN: comparison < 0,
                ConditionOperatorV351.LESS_EQUAL: comparison <= 0,
                ConditionOperatorV351.GREATER_THAN: comparison > 0,
                ConditionOperatorV351.GREATER_EQUAL: comparison >= 0,
            }
            return ("true" if checks[op] else "false"), state_ref
        if op in {ConditionOperatorV351.CONTAINS, ConditionOperatorV351.NOT_CONTAINS}:
            if not condition.expected_member_key: return "unknown", state_ref
            contained = condition.expected_member_key in current.set_members
            return ("true" if (contained if op == ConditionOperatorV351.CONTAINS else not contained) else "false"), state_ref
        if op == ConditionOperatorV351.PROBABILITY_AT_LEAST:
            if expected is None or condition.numeric_threshold is None or not current.probability_mass:
                return "unknown", state_ref
            mass = sum(
                item.probability for item in current.probability_mass
                if item.support_value.value_ref == expected.value_ref
            )
            return ("true" if mass >= condition.numeric_threshold else "false"), state_ref
        return "unknown", state_ref

    def _operand(self, operand: StateOperandV351, *, current, role_map, snapshot, context_ref, event_port_values):
        if operand.kind == OperandKind.CONSTANT: return operand.constant
        if operand.kind == OperandKind.CURRENT: return current
        if operand.kind == OperandKind.ROLE_STATE:
            binding = role_map.get(operand.role_pin.key)
            if binding is None: raise StateModelError("role-state operand role is unbound")
            return snapshot.value(binding.participant_ref, operand.dimension_pin, context_ref)
        if operand.kind == OperandKind.EVENT_PORT:
            if operand.event_port_pin.key not in event_port_values:
                raise StateModelError("event-port transform operand is unbound")
            return event_port_values[operand.event_port_pin.key]
        if operand.kind == OperandKind.PARAMETER:
            return self.parameter_lookup(operand.parameter_pin, operand.parameter_name)
        raise StateModelError(f"unknown operand kind:{operand.kind}")


def _attach_proof(delta: StateDeltaV351, proof_ref: str) -> StateDeltaV351:
    from dataclasses import replace
    return replace(delta, proof_refs=tuple(sorted(set((*delta.proof_refs, proof_ref)))))


def _attach_event_proof(event: SecondaryEventCandidateV351, proof_ref: str) -> SecondaryEventCandidateV351:
    from dataclasses import replace
    return replace(event, proof_refs=tuple(sorted(set((*event.proof_refs, proof_ref)))))


def _raise(exc):
    raise exc


__all__ = [
    "CausalEventV351", "StateKeyV351", "StateSnapshotV351", "TransitionPreviewEngineV351",
    "TransitionPreviewResultV351",
]
