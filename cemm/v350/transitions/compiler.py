"""Compile reviewed transition contracts into exact runtime plans.

Compilation is structural only: no event/schema/type name is special-cased.
"""
from __future__ import annotations

from dataclasses import replace

from ..schema.model import (
    EventSchema,
    PortFillerClass,
    SchemaLifecycleStatus,
    StateDimensionSchema,
    StateValueSchema,
    UseOperation,
)
from ..schema.registry import SchemaRegistry
from .model import (
    CapabilityDependencyRecord,
    CompiledTransitionContract,
    StateConditionSpec,
    StateEffectSpec,
    TransitionContractRecord,
)


class TransitionContractError(ValueError):
    pass


_TERMINAL = {SchemaLifecycleStatus.SUPERSEDED, SchemaLifecycleStatus.REJECTED}


class TransitionContractCompiler:
    def __init__(self, schemas: SchemaRegistry) -> None:
        self._schemas = schemas

    def compile(self, contract: TransitionContractRecord) -> CompiledTransitionContract:
        if contract.lifecycle_status in _TERMINAL:
            raise TransitionContractError("transition contract is terminal")
        trigger = self._schemas.maybe_schema(contract.trigger_schema_ref, contract.trigger_schema_revision)
        if not isinstance(trigger, EventSchema):
            raise TransitionContractError("transition contract trigger must pin an exact EventSchema")
        if not trigger.use_profile.permits(UseOperation.TRANSITION):
            raise TransitionContractError("trigger EventSchema does not authorize transition use")
        if contract.contract_ref not in trigger.transition_contract_refs:
            raise TransitionContractError("trigger EventSchema does not link the transition contract")

        referenced_ports: set[str] = set()
        for condition in contract.state_conditions:
            self._validate_condition(trigger, contract, condition)
            referenced_ports.add(condition.holder_port_ref)
        targets: set[tuple[str, str, int]] = set()
        for effect in contract.state_effects:
            self._validate_effect(trigger, contract, effect)
            target = (effect.holder_port_ref, effect.dimension_ref, effect.dimension_revision)
            if target in targets:
                raise TransitionContractError(
                    "one transition contract may not emit multiple state effects for the same holder-port/dimension"
                )
            targets.add(target)
            referenced_ports.add(effect.holder_port_ref)
            if effect.magnitude_port_ref:
                referenced_ports.add(effect.magnitude_port_ref)
        return CompiledTransitionContract(contract=contract, trigger_port_refs=frozenset(referenced_ports))

    def validate_capability_dependency(self, dependency: CapabilityDependencyRecord) -> None:
        if dependency.lifecycle_status in _TERMINAL:
            raise TransitionContractError("capability dependency is terminal")
        action = self._schemas.maybe_schema(dependency.action_schema_ref, dependency.action_schema_revision)
        from ..schema.model import ActionSchema, ReferentTypeSchema
        if not isinstance(action, ActionSchema):
            raise TransitionContractError("capability dependency must pin an exact ActionSchema")
        for type_ref in dependency.holder_type_refs:
            schema = self._schemas.maybe_authoritative_schema(type_ref)
            if not isinstance(schema, ReferentTypeSchema):
                raise TransitionContractError(f"capability dependency holder type is unresolved: {type_ref}")
        for condition in dependency.state_conditions:
            self._validate_state_target(None, condition.dimension_ref, condition.dimension_revision,
                                        condition.value_ref, condition.value_revision, contract_ref=None)

    def _validate_condition(
        self,
        trigger: EventSchema,
        contract: TransitionContractRecord,
        condition: StateConditionSpec,
    ) -> None:
        self._validate_holder_port(trigger, condition.holder_port_ref)
        self._validate_state_target(
            trigger,
            condition.dimension_ref,
            condition.dimension_revision,
            condition.value_ref,
            condition.value_revision,
            contract_ref=contract.contract_ref,
        )

    def _validate_effect(
        self,
        trigger: EventSchema,
        contract: TransitionContractRecord,
        effect: StateEffectSpec,
    ) -> None:
        self._validate_holder_port(trigger, effect.holder_port_ref)
        if effect.magnitude_port_ref is not None:
            trigger.port(effect.magnitude_port_ref)
        self._validate_state_target(
            trigger,
            effect.dimension_ref,
            effect.dimension_revision,
            effect.from_value_ref,
            effect.from_value_revision,
            contract_ref=contract.contract_ref,
        )
        self._validate_state_target(
            trigger,
            effect.dimension_ref,
            effect.dimension_revision,
            effect.to_value_ref,
            effect.to_value_revision,
            contract_ref=contract.contract_ref,
        )

    @staticmethod
    def _validate_holder_port(trigger: EventSchema, port_ref: str) -> None:
        port = trigger.port(port_ref)
        if PortFillerClass.REFERENT not in port.filler_classes:
            raise TransitionContractError(f"transition holder port must accept referents: {port_ref}")
        if port.cardinality.maximum is not None and port.cardinality.maximum < 1:
            raise TransitionContractError(f"transition holder port cannot bind a referent: {port_ref}")

    def _validate_state_target(
        self,
        trigger: EventSchema | None,
        dimension_ref: str,
        dimension_revision: int,
        value_ref: str | None,
        value_revision: int | None,
        *,
        contract_ref: str | None,
    ) -> None:
        del trigger
        dimension = self._schemas.maybe_schema(dimension_ref, dimension_revision)
        if not isinstance(dimension, StateDimensionSchema):
            raise TransitionContractError(f"transition target is not an exact state dimension: {dimension_ref}@{dimension_revision}")
        if not dimension.use_profile.permits(UseOperation.TRANSITION):
            raise TransitionContractError(f"state dimension does not authorize transition use: {dimension_ref}@{dimension_revision}")
        if contract_ref is not None and contract_ref not in dimension.transition_contract_refs:
            raise TransitionContractError(f"state dimension does not link transition contract: {dimension_ref}@{dimension_revision}")
        if value_ref is None:
            return
        value = self._schemas.maybe_schema(value_ref, value_revision)
        if not isinstance(value, StateValueSchema):
            raise TransitionContractError(f"transition state value is unresolved: {value_ref}@{value_revision}")
        if value.dimension_ref != dimension_ref:
            raise TransitionContractError("transition state value belongs to another dimension")
        if value_ref not in dimension.value_schema_refs:
            raise TransitionContractError("transition state value is outside the dimension value domain")


def activate_contract_for_competence(contract: TransitionContractRecord) -> TransitionContractRecord:
    """Test/helper promotion without embedding semantic authority in the engine."""
    return replace(contract, lifecycle_status=SchemaLifecycleStatus.ACTIVE)
