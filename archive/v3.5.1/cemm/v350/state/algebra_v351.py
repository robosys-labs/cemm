"""Typed state-domain algebra for CEMM v3.5.1 Phase 15."""
from __future__ import annotations

from dataclasses import replace
from math import isfinite
from typing import Any, Callable, Mapping

from ..csir.model import ExactAuthorityPin
from ..schema.model import StateDimensionSchema
from .model_v351 import (
    OperandKind, ProbabilityPointV351, ProcessStatus, RelationStateSignatureV351, StateDomainContractV351,
    StateDomainKind, StateModelError, StateOperandV351, StateTransformExpression,
    StateTransformOperator, StateValueV351,
)


class StateDomainCompilerV351:
    """Compile exact StateDimensionSchema authority into one typed algebra contract.

    Legacy categorical/ordered/scalar fields remain accepted. Rich domains require the
    reviewed `metadata.state_domain_v351` document, which is included in the schema's exact
    content fingerprint and therefore cannot float beneath an active revision.
    """

    @staticmethod
    def compile(dimension: StateDimensionSchema) -> StateDomainContractV351:
        raw = dict(dimension.metadata.get("state_domain_v351", {}) or {})
        if raw:
            kind = StateDomainKind(str(raw["kind"]))
        elif dimension.scalar:
            kind = StateDomainKind.CONTINUOUS
        elif dimension.ordered:
            kind = StateDomainKind.ORDERED
        else:
            kind = StateDomainKind.CATEGORICAL
        return StateDomainContractV351(
            dimension_ref=dimension.schema_ref,
            dimension_revision=dimension.revision,
            kind=kind,
            unit_pin=_pin_from_doc(raw.get("unit_pin")),
            lower_bound=_optional_float(raw.get("lower_bound")),
            upper_bound=_optional_float(raw.get("upper_bound")),
            vector_size=None if raw.get("vector_size") is None else int(raw["vector_size"]),
            coordinate_frame_pin=_pin_from_doc(raw.get("coordinate_frame_pin")),
            manifold_pin=_pin_from_doc(raw.get("manifold_pin")),
            value_pins=tuple(_pin_from_doc(item, required=True) for item in raw.get("value_pins", ())),
            relation_pins=tuple(_pin_from_doc(item, required=True) for item in raw.get("relation_pins", ())),
            relation_role_pins=tuple(_pin_from_doc(item, required=True) for item in raw.get("relation_role_pins", ())),
            relation_signatures=tuple(
                RelationStateSignatureV351(
                    _pin_from_doc(item["relation_pin"], required=True),
                    tuple(_pin_from_doc(pin, required=True) for pin in item.get("role_pins", ())),
                )
                for item in raw.get("relation_signatures", ())
            ),
            element_type_pins=tuple(_pin_from_doc(item, required=True) for item in raw.get("element_type_pins", ())),
            process_pins=tuple(_pin_from_doc(item, required=True) for item in raw.get("process_pins", ())),
            support_domain_kind=(None if raw.get("support_domain_kind") is None else StateDomainKind(str(raw["support_domain_kind"]))),
            maximum_set_size=None if raw.get("maximum_set_size") is None else int(raw["maximum_set_size"]),
            probability_tolerance=float(raw.get("probability_tolerance", 1e-9)),
            metadata={k: v for k, v in raw.items() if k not in {
                "kind", "unit_pin", "lower_bound", "upper_bound", "vector_size",
                "coordinate_frame_pin", "manifold_pin", "value_pins", "relation_pins",
                "relation_role_pins", "relation_signatures", "element_type_pins", "process_pins",
                "support_domain_kind", "maximum_set_size", "probability_tolerance",
            }},
        )


def _optional_float(value):
    return None if value is None else float(value)


def _pin_from_doc(value: Any, required: bool = False) -> ExactAuthorityPin | None:
    if value is None:
        if required:
            raise StateModelError("missing exact authority pin in state-domain contract")
        return None
    if isinstance(value, ExactAuthorityPin):
        return value
    if isinstance(value, Mapping):
        return ExactAuthorityPin(
            str(value["kind"]), str(value["namespace"]), str(value["ref"]),
            int(value["revision"]), str(value["content_hash"]), str(value.get("scope_ref", "global")),
        )
    if not isinstance(value, (list, tuple)) or len(value) != 6:
        raise StateModelError("exact authority pin document must contain six key fields")
    return ExactAuthorityPin(str(value[0]), str(value[1]), str(value[2]), int(value[3]), str(value[4]), str(value[5]))


class StateAlgebraV351:
    def __init__(self, *, manifold_transform_resolver=None, set_member_type_resolver=None) -> None:
        self.manifold_transform_resolver = manifold_transform_resolver
        self.set_member_type_resolver = set_member_type_resolver

    def validate_value(self, domain: StateDomainContractV351, value: StateValueV351) -> None:
        if domain.kind != value.domain_kind:
            raise StateModelError(f"state value domain mismatch:{value.domain_kind.value}!={domain.kind.value}")
        # For a probabilistic state, unit/frame/type constraints belong to each support
        # value rather than to the distribution container itself.
        if domain.kind != StateDomainKind.PROBABILISTIC:
            if domain.unit_pin is not None:
                if value.unit_pin is None or value.unit_pin.key != domain.unit_pin.key:
                    raise StateModelError("state value unit differs from exact domain unit authority")
            elif value.unit_pin is not None:
                raise StateModelError("unit-bearing value supplied to unitless state domain")
            if domain.coordinate_frame_pin is not None:
                if value.coordinate_frame_pin is None or value.coordinate_frame_pin.key != domain.coordinate_frame_pin.key:
                    raise StateModelError("vector coordinate frame differs from exact domain frame")
            elif value.coordinate_frame_pin is not None:
                raise StateModelError("coordinate frame supplied to domain without frame authority")

        if domain.kind in {StateDomainKind.CATEGORICAL, StateDomainKind.ORDERED}:
            if domain.value_pins and (
                value.categorical_pin is None
                or value.categorical_pin.key not in {pin.key for pin in domain.value_pins}
            ):
                raise StateModelError("categorical/ordered value is outside exact domain value authority")
        if domain.kind == StateDomainKind.CONTINUOUS:
            assert value.scalar_value is not None
            self._bounds(domain, value.scalar_value)
        elif domain.kind == StateDomainKind.VECTOR:
            if len(value.vector_value) != domain.vector_size:
                raise StateModelError("vector value dimension differs from domain vector_size")
            for component in value.vector_value:
                self._bounds(domain, component)
        elif domain.kind == StateDomainKind.RELATIONAL:
            if value.relation_pin is None:
                raise StateModelError("relational state lacks exact relation predicate")
            signatures = {item.relation_pin.key: item for item in domain.relation_signatures}
            if signatures:
                signature = signatures.get(value.relation_pin.key)
                if signature is None:
                    raise StateModelError("relation value is outside exact relational domain")
                required_roles = {pin.key for pin in signature.role_pins}
            else:
                allowed = {pin.key for pin in domain.relation_pins}
                if value.relation_pin.key not in allowed:
                    raise StateModelError("relation value is outside exact relational domain")
                required_roles = {pin.key for pin in domain.relation_role_pins}
            observed_roles = {item.role_pin.key for item in value.relation_bindings}
            if observed_roles != required_roles:
                raise StateModelError("relation value must bind exactly the authorized semantic role signature")
        elif domain.kind == StateDomainKind.SET:
            if domain.maximum_set_size is not None and len(value.set_members) > domain.maximum_set_size:
                raise StateModelError("set-valued state exceeds exact maximum cardinality")
            if domain.element_type_pins:
                if self.set_member_type_resolver is None:
                    raise StateModelError("typed set domain requires exact member-type resolver")
                allowed = {pin.key for pin in domain.element_type_pins}
                for member in value.set_members:
                    observed = tuple(self.set_member_type_resolver(member) or ())
                    if not any(pin.key in allowed for pin in observed):
                        raise StateModelError("set member lacks an entitled exact element type")
        elif domain.kind == StateDomainKind.PROCESS:
            allowed = {pin.key for pin in domain.process_pins}
            if value.process_pin is None or value.process_pin.key not in allowed:
                raise StateModelError("process value is outside exact process domain")
        elif domain.kind == StateDomainKind.PROBABILISTIC:
            total = sum(item.probability for item in value.probability_mass)
            if abs(total - 1.0) > domain.probability_tolerance:
                raise StateModelError("probability distribution violates domain tolerance")
            support = self._support_domain(domain)
            for point in value.probability_mass:
                self.validate_value(support, point.support_value)

    @staticmethod
    def _support_domain(domain: StateDomainContractV351) -> StateDomainContractV351:
        if domain.support_domain_kind is None:
            raise StateModelError("probabilistic domain lacks support-domain authority")
        return StateDomainContractV351(
            dimension_ref=domain.dimension_ref + ":support",
            dimension_revision=domain.dimension_revision,
            kind=domain.support_domain_kind,
            unit_pin=domain.unit_pin, lower_bound=domain.lower_bound, upper_bound=domain.upper_bound,
            vector_size=domain.vector_size, coordinate_frame_pin=domain.coordinate_frame_pin,
            manifold_pin=domain.manifold_pin, value_pins=domain.value_pins,
            relation_pins=domain.relation_pins, relation_role_pins=domain.relation_role_pins,
            relation_signatures=domain.relation_signatures,
            element_type_pins=domain.element_type_pins,
            process_pins=domain.process_pins, maximum_set_size=domain.maximum_set_size,
            probability_tolerance=domain.probability_tolerance, metadata=domain.metadata,
        )

    @staticmethod
    def _bounds(domain: StateDomainContractV351, value: float) -> None:
        if domain.lower_bound is not None and value < domain.lower_bound:
            raise StateModelError("state value below domain lower bound")
        if domain.upper_bound is not None and value > domain.upper_bound:
            raise StateModelError("state value above domain upper bound")

    def compare(
        self, domain: StateDomainContractV351, left: StateValueV351, right: StateValueV351
    ) -> int:
        """Return -1/0/1 under the exact domain order; undefined domains fail closed."""
        self.validate_value(domain, left)
        self.validate_value(domain, right)
        if domain.kind is StateDomainKind.ORDERED:
            if not domain.value_pins or left.categorical_pin is None or right.categorical_pin is None:
                raise StateModelError("ordered comparison requires exact reviewed value order")
            positions = {pin.key: index for index, pin in enumerate(domain.value_pins)}
            a, b = positions[left.categorical_pin.key], positions[right.categorical_pin.key]
        elif domain.kind is StateDomainKind.CONTINUOUS:
            if left.scalar_value is None or right.scalar_value is None:
                raise StateModelError("continuous comparison requires scalar values")
            a, b = float(left.scalar_value), float(right.scalar_value)
        else:
            raise StateModelError(f"domain {domain.kind.value} has no total comparison order")
        return -1 if a < b else 1 if a > b else 0

    def apply(
        self,
        domain: StateDomainContractV351,
        current: StateValueV351 | None,
        expression: StateTransformExpression,
        *,
        resolve_operand: Callable[[StateOperandV351], Any],
    ) -> StateValueV351 | None:
        if current is not None:
            self.validate_value(domain, current)
        op = expression.operator
        if op == StateTransformOperator.CLEAR:
            return None
        values = [resolve_operand(item) for item in expression.operands]
        result: StateValueV351

        if op == StateTransformOperator.ASSIGN:
            if len(values) != 1 or not isinstance(values[0], StateValueV351):
                raise StateModelError("ASSIGN requires one typed StateValueV351 operand")
            if domain.kind in {StateDomainKind.CATEGORICAL, StateDomainKind.ORDERED} and not domain.value_pins:
                raise StateModelError(
                    "categorical/ordered transition assignment requires exact reviewed value_pins authority"
                )
            result = values[0]
        elif op in {StateTransformOperator.ADD, StateTransformOperator.SCALE, StateTransformOperator.AFFINE, StateTransformOperator.CLAMP}:
            result = self._scalar(domain, current, op, values, expression)
        elif op == StateTransformOperator.ORDER_SHIFT:
            result = self._ordered(domain, current, values)
        elif op in {StateTransformOperator.VECTOR_ADD, StateTransformOperator.VECTOR_SCALE, StateTransformOperator.VECTOR_AFFINE}:
            if domain.manifold_pin is not None:
                raise StateModelError(
                    "linear vector transform is not authorized on a manifold domain"
                )
            result = self._vector(domain, current, op, values, expression)
        elif op == StateTransformOperator.MANIFOLD_MAP:
            if domain.kind != StateDomainKind.VECTOR or domain.manifold_pin is None:
                raise StateModelError("MANIFOLD_MAP requires vector domain with exact manifold authority")
            if self.manifold_transform_resolver is None:
                raise StateModelError("manifold transform requires installed exact evaluator")
            result = self.manifold_transform_resolver(
                expression.external_operator_pin, domain, current, tuple(values)
            )
            if not isinstance(result, StateValueV351):
                raise StateModelError("manifold evaluator must return typed StateValueV351")
        elif op in {StateTransformOperator.SET_ADD, StateTransformOperator.SET_REMOVE, StateTransformOperator.SET_UNION, StateTransformOperator.SET_DIFFERENCE}:
            result = self._set(domain, current, op, values)
        elif op in {StateTransformOperator.RELATION_ADD, StateTransformOperator.RELATION_REMOVE}:
            if domain.kind != StateDomainKind.RELATIONAL:
                raise StateModelError("relational transform applied to non-relational domain")
            if op == StateTransformOperator.RELATION_REMOVE:
                return None
            if len(values) != 1 or not isinstance(values[0], StateValueV351):
                raise StateModelError("RELATION_ADD requires one typed relational value")
            result = values[0]
        elif op in {StateTransformOperator.PROCESS_START, StateTransformOperator.PROCESS_STOP, StateTransformOperator.PROCESS_ADVANCE}:
            result = self._process(domain, current, op, values)
        elif op in {StateTransformOperator.DISTRIBUTION_REPLACE, StateTransformOperator.DISTRIBUTION_MIX}:
            result = self._probability(domain, current, op, values)
        else:  # pragma: no cover
            raise StateModelError(f"unsupported transform operator:{op.value}")

        self.validate_value(domain, result)
        return result

    def _scalar(self, domain, current, op, values, expression):
        if domain.kind != StateDomainKind.CONTINUOUS:
            raise StateModelError("numeric scalar transform requires continuous domain")
        if current is None or current.scalar_value is None:
            raise StateModelError("numeric scalar transform requires known current state")
        x = float(current.scalar_value)
        if op == StateTransformOperator.ADD:
            if len(values) != 1: raise StateModelError("ADD requires one numeric operand")
            y = x + self._scalar_additive_operand(domain, values[0])
        elif op == StateTransformOperator.SCALE:
            if len(values) != 1: raise StateModelError("SCALE requires one dimensionless numeric operand")
            y = x * self._number(values[0])
        elif op == StateTransformOperator.AFFINE:
            if len(values) != 2: raise StateModelError("AFFINE requires dimensionless scale and compatible offset")
            y = x * self._number(values[0]) + self._scalar_additive_operand(domain, values[1])
        else:
            if values: raise StateModelError("CLAMP uses expression clamp bounds, not operands")
            y = x
        lower = expression.clamp_lower if expression.clamp_lower is not None else domain.lower_bound
        upper = expression.clamp_upper if expression.clamp_upper is not None else domain.upper_bound
        if lower is not None: y = max(float(lower), y)
        if upper is not None: y = min(float(upper), y)
        return replace(current, scalar_value=y)

    def _ordered(self, domain, current, values):
        if domain.kind != StateDomainKind.ORDERED:
            raise StateModelError("ORDER_SHIFT requires ordered domain")
        if current is None or current.categorical_pin is None:
            raise StateModelError("ORDER_SHIFT requires known current ordered value")
        if len(values) != 1:
            raise StateModelError("ORDER_SHIFT requires one signed integer step operand")
        raw = self._number(values[0])
        if int(raw) != raw:
            raise StateModelError("ORDER_SHIFT step must be an integer")
        ordered = list(domain.value_pins)
        if not ordered:
            raise StateModelError(
                "ORDER_SHIFT requires reviewed exact value_pins order in state_domain_v351"
            )
        try:
            index = next(i for i, pin in enumerate(ordered) if pin.key == current.categorical_pin.key)
        except StopIteration as exc:
            raise StateModelError("current ordered value is outside exact order") from exc
        target = index + int(raw)
        if target < 0 or target >= len(ordered):
            raise StateModelError("ORDER_SHIFT exceeds exact ordered domain boundary")
        return replace(current, categorical_pin=ordered[target])

    def _vector(self, domain, current, op, values, expression):
        del expression
        if domain.kind != StateDomainKind.VECTOR:
            raise StateModelError("vector transform requires vector domain")
        if current is None or not current.vector_value:
            raise StateModelError("vector transform requires known current vector")
        x = tuple(float(v) for v in current.vector_value)
        if op == StateTransformOperator.VECTOR_ADD:
            if len(values) != 1: raise StateModelError("VECTOR_ADD requires one vector operand")
            v = self._vector_additive_operand(domain, values[0], len(x)); y = tuple(a + b for a, b in zip(x, v))
        elif op == StateTransformOperator.VECTOR_SCALE:
            if len(values) != 1: raise StateModelError("VECTOR_SCALE requires one dimensionless scalar operand")
            s = self._number(values[0]); y = tuple(a * s for a in x)
        else:
            if len(values) != 2: raise StateModelError("VECTOR_AFFINE requires dimensionless scalar and compatible vector offset")
            s = self._number(values[0]); v = self._vector_additive_operand(domain, values[1], len(x)); y = tuple(a * s + b for a, b in zip(x, v))
        return replace(current, vector_value=y)

    def _set(self, domain, current, op, values):
        if domain.kind != StateDomainKind.SET:
            raise StateModelError("set transform requires set-valued domain")
        members = set(() if current is None else current.set_members)
        if op in {StateTransformOperator.SET_ADD, StateTransformOperator.SET_REMOVE}:
            if len(values) != 1: raise StateModelError(f"{op.value} requires one member operand")
            if not isinstance(values[0], str) or not values[0].strip():
                raise StateModelError(f"{op.value} member operand must be an explicit non-empty member ref")
            incoming = {values[0]}
        else:
            if len(values) != 1: raise StateModelError(f"{op.value} requires one set operand")
            incoming = set(self._string_set(values[0]))
        if op in {StateTransformOperator.SET_ADD, StateTransformOperator.SET_UNION}: members |= incoming
        else: members -= incoming
        result = StateValueV351(StateDomainKind.SET, set_members=tuple(sorted(members)))
        return result

    def _process(self, domain, current, op, values):
        if domain.kind != StateDomainKind.PROCESS:
            raise StateModelError("process transform requires process domain")
        if op == StateTransformOperator.PROCESS_START:
            if len(values) != 1 or not isinstance(values[0], StateValueV351):
                raise StateModelError("PROCESS_START requires one process value")
            incoming = values[0]
            return replace(incoming, process_status=ProcessStatus.ACTIVE)
        if current is None or current.process_pin is None or current.process_status is None:
            raise StateModelError("process update requires known current process")
        if op == StateTransformOperator.PROCESS_STOP:
            if values: raise StateModelError("PROCESS_STOP takes no value operand beyond structural declaration")
            return replace(current, process_status=ProcessStatus.TERMINATED)
        if len(values) != 1: raise StateModelError("PROCESS_ADVANCE requires numeric progress delta")
        progress = float(current.process_progress or 0.0) + self._number(values[0])
        return replace(current, process_progress=progress)

    def _probability(self, domain, current, op, values):
        if domain.kind != StateDomainKind.PROBABILISTIC:
            raise StateModelError("distribution transform requires probabilistic domain")
        expected_arity = {StateTransformOperator.DISTRIBUTION_REPLACE: (1,), StateTransformOperator.DISTRIBUTION_MIX: (1, 2)}[op]
        if len(values) not in expected_arity or not isinstance(values[0], StateValueV351):
            raise StateModelError("distribution transform has invalid operand arity or untyped distribution")
        incoming = values[0]
        if incoming.domain_kind != StateDomainKind.PROBABILISTIC:
            raise StateModelError("distribution operand is not probabilistic")
        if op == StateTransformOperator.DISTRIBUTION_REPLACE:
            return incoming
        if current is None or current.domain_kind != StateDomainKind.PROBABILISTIC:
            raise StateModelError("DISTRIBUTION_MIX requires current probability state")
        weight = self._number(values[1]) if len(values) > 1 else 0.5
        if not 0.0 <= weight <= 1.0:
            raise StateModelError("distribution mixture weight must be in [0,1]")
        masses = {}
        for point in current.probability_mass:
            masses.setdefault(point.value_key, [point.support_value, 0.0])[1] += (1.0 - weight) * point.probability
        for point in incoming.probability_mass:
            masses.setdefault(point.value_key, [point.support_value, 0.0])[1] += weight * point.probability
        return StateValueV351(
            StateDomainKind.PROBABILISTIC,
            probability_mass=tuple(
                ProbabilityPointV351(masses[key][0], masses[key][1]) for key in sorted(masses)
            ),
        )


    def _scalar_additive_operand(self, domain: StateDomainContractV351, value: Any) -> float:
        if isinstance(value, StateValueV351):
            self.validate_value(domain, value)
            if value.scalar_value is None:
                raise StateModelError("additive scalar operand lacks scalar value")
            return float(value.scalar_value)
        if domain.unit_pin is not None:
            raise StateModelError("unit-bearing additive transform requires typed state-value operand with exact unit authority")
        return self._number(value)

    def _vector_additive_operand(
        self, domain: StateDomainContractV351, value: Any, size: int
    ) -> tuple[float, ...]:
        if isinstance(value, StateValueV351):
            self.validate_value(domain, value)
            return self._vector_operand(value, size)
        if domain.unit_pin is not None or domain.coordinate_frame_pin is not None:
            raise StateModelError(
                "unit/frame-bearing vector addition requires typed state-value operand with exact authority"
            )
        return self._vector_operand(value, size)

    @staticmethod
    def _number(value: Any) -> float:
        if isinstance(value, StateValueV351) and value.scalar_value is not None:
            value = value.scalar_value
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(float(value)):
            raise StateModelError("numeric transform operand must be finite")
        return float(value)

    @staticmethod
    def _vector_operand(value: Any, size: int) -> tuple[float, ...]:
        if isinstance(value, StateValueV351): value = value.vector_value
        if not isinstance(value, (tuple, list)) or len(value) != size:
            raise StateModelError("vector operand has incompatible dimension")
        result = tuple(float(item) for item in value)
        if any(not isfinite(item) for item in result):
            raise StateModelError("vector operand contains non-finite component")
        return result

    @staticmethod
    def _string_set(value: Any) -> tuple[str, ...]:
        if isinstance(value, StateValueV351): value = value.set_members
        if not isinstance(value, (tuple, list, set, frozenset)):
            raise StateModelError("set operand must be a collection")
        return tuple(sorted(set(map(str, value))))


__all__ = ["StateAlgebraV351", "StateDomainCompilerV351"]
