"""Canonical Phase-15 state-domain and role-addressed transition contracts.

The module contains only structural mechanics.  Domain/event/concept identities remain
exact authority/data refs; no named event, English token, or grammatical role is special.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from math import isfinite
from typing import Any, Iterable, Mapping

from ..csir.model import ExactAuthorityPin
from ..schema.model import UseOperation, semantic_fingerprint


class StateModelError(ValueError):
    pass


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class StateDomainKind(StrEnum):
    CATEGORICAL = "categorical"
    ORDERED = "ordered"
    CONTINUOUS = "continuous"
    VECTOR = "vector"
    RELATIONAL = "relational"
    SET = "set"
    PROCESS = "process"
    PROBABILISTIC = "probabilistic"


class StateTransformOperator(StrEnum):
    ASSIGN = "assign"
    CLEAR = "clear"
    ADD = "add"
    SCALE = "scale"
    AFFINE = "affine"
    CLAMP = "clamp"
    ORDER_SHIFT = "order_shift"
    VECTOR_ADD = "vector_add"
    VECTOR_SCALE = "vector_scale"
    VECTOR_AFFINE = "vector_affine"
    MANIFOLD_MAP = "manifold_map"
    RELATION_ADD = "relation_add"
    RELATION_REMOVE = "relation_remove"
    SET_ADD = "set_add"
    SET_REMOVE = "set_remove"
    SET_UNION = "set_union"
    SET_DIFFERENCE = "set_difference"
    PROCESS_START = "process_start"
    PROCESS_STOP = "process_stop"
    PROCESS_ADVANCE = "process_advance"
    DISTRIBUTION_REPLACE = "distribution_replace"
    DISTRIBUTION_MIX = "distribution_mix"


class OperandKind(StrEnum):
    CONSTANT = "constant"
    CURRENT = "current"
    ROLE_STATE = "role_state"
    EVENT_PORT = "event_port"
    PARAMETER = "parameter"


class ConditionOperatorV351(StrEnum):
    KNOWN = "known"
    UNKNOWN = "unknown"
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    LESS_THAN = "less_than"
    LESS_EQUAL = "less_equal"
    GREATER_THAN = "greater_than"
    GREATER_EQUAL = "greater_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    PROBABILITY_AT_LEAST = "probability_at_least"


class UnknownConditionPolicyV351(StrEnum):
    BLOCK = "block"
    PRESERVE_FRONTIER = "preserve_frontier"
    BRANCH = "branch"


class MechanismTriggerKind(StrEnum):
    EVENT = "event"
    STATE_CHANGE = "state_change"
    EXOGENOUS = "exogenous"


class ProcessStatus(StrEnum):
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    TERMINATED = "terminated"


def _require_ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise StateModelError(f"{label} must be a non-empty reference")


def _unique(values: Iterable[Any], label: str) -> None:
    values = tuple(values)
    if len(values) != len(set(values)):
        raise StateModelError(f"{label} must be unique")


def _finite(value: float, label: str) -> None:
    if not isfinite(value):
        raise StateModelError(f"{label} must be finite")


@dataclass(frozen=True, slots=True)
class RelationStateSignatureV351:
    """Exact argument signature for one relation-valued state predicate."""

    relation_pin: ExactAuthorityPin
    role_pins: tuple[ExactAuthorityPin, ...]

    def __post_init__(self) -> None:
        if not self.role_pins:
            raise StateModelError("relational state signature requires exact semantic roles")
        _unique((pin.key for pin in self.role_pins), "relational state signature roles")


@dataclass(frozen=True, slots=True)
class StateDomainContractV351:
    """Typed interpretation of one exact StateDimensionSchema revision.

    The authority may be encoded directly in reviewed schema metadata for backwards
    compatibility.  This compiled object is the only runtime algebra contract.
    """

    dimension_ref: str
    dimension_revision: int
    kind: StateDomainKind
    unit_pin: ExactAuthorityPin | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    vector_size: int | None = None
    coordinate_frame_pin: ExactAuthorityPin | None = None
    manifold_pin: ExactAuthorityPin | None = None
    value_pins: tuple[ExactAuthorityPin, ...] = ()
    relation_pins: tuple[ExactAuthorityPin, ...] = ()
    relation_role_pins: tuple[ExactAuthorityPin, ...] = ()
    relation_signatures: tuple[RelationStateSignatureV351, ...] = ()
    element_type_pins: tuple[ExactAuthorityPin, ...] = ()
    process_pins: tuple[ExactAuthorityPin, ...] = ()
    support_domain_kind: StateDomainKind | None = None
    maximum_set_size: int | None = None
    probability_tolerance: float = 1e-9
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_ref(self.dimension_ref, "state domain dimension_ref")
        if self.dimension_revision < 1:
            raise StateModelError("state domain dimension revision must be positive")
        if self.lower_bound is not None:
            _finite(float(self.lower_bound), "state lower bound")
        if self.upper_bound is not None:
            _finite(float(self.upper_bound), "state upper bound")
        if self.lower_bound is not None and self.upper_bound is not None and self.lower_bound > self.upper_bound:
            raise StateModelError("state domain lower bound cannot exceed upper bound")
        if self.vector_size is not None and self.vector_size < 1:
            raise StateModelError("vector_size must be positive")
        if self.maximum_set_size is not None and self.maximum_set_size < 0:
            raise StateModelError("maximum_set_size cannot be negative")
        if not isfinite(self.probability_tolerance) or self.probability_tolerance <= 0:
            raise StateModelError("probability_tolerance must be finite and positive")
        _unique((pin.key for pin in self.value_pins), "state-domain value pins")
        _unique((pin.key for pin in self.relation_pins), "state-domain relation pins")
        _unique((pin.key for pin in self.relation_role_pins), "state-domain relation role pins")
        _unique((item.relation_pin.key for item in self.relation_signatures), "state-domain relation signatures")
        _unique((pin.key for pin in self.element_type_pins), "state-domain element type pins")
        _unique((pin.key for pin in self.process_pins), "state-domain process pins")
        if self.kind == StateDomainKind.CONTINUOUS and self.vector_size is not None:
            raise StateModelError("continuous scalar domain cannot declare vector_size")
        if self.kind == StateDomainKind.VECTOR and self.vector_size is None:
            raise StateModelError("vector domain requires vector_size")
        if self.kind == StateDomainKind.RELATIONAL and not (self.relation_signatures or self.relation_pins):
            raise StateModelError("relational domain requires exact relation authority")
        if self.kind == StateDomainKind.RELATIONAL and not (self.relation_signatures or self.relation_role_pins):
            raise StateModelError("relational domain requires exact semantic role authority")
        if self.kind == StateDomainKind.PROCESS and not self.process_pins:
            raise StateModelError("process domain requires exact process pins")
        if self.kind == StateDomainKind.PROBABILISTIC and self.support_domain_kind is None:
            raise StateModelError("probabilistic domain requires support_domain_kind")
        if self.kind != StateDomainKind.PROBABILISTIC and self.support_domain_kind is not None:
            raise StateModelError("support_domain_kind is only valid for probabilistic domains")
        effective_kind = self.support_domain_kind if self.kind is StateDomainKind.PROBABILISTIC else self.kind
        if self.kind is StateDomainKind.PROBABILISTIC and effective_kind is StateDomainKind.PROBABILISTIC:
            raise StateModelError("probabilistic support domain cannot recursively be probabilistic")
        if effective_kind is StateDomainKind.VECTOR and self.vector_size is None:
            raise StateModelError("vector state/support domain requires vector_size")
        if effective_kind is StateDomainKind.RELATIONAL and not (self.relation_signatures or self.relation_pins):
            raise StateModelError("relational state/support domain requires exact relation authority")
        if effective_kind is StateDomainKind.RELATIONAL and not (self.relation_signatures or self.relation_role_pins):
            raise StateModelError("relational state/support domain requires exact semantic role authority")
        if self.relation_signatures:
            signature_relations = {item.relation_pin.key for item in self.relation_signatures}
            if self.relation_pins and signature_relations != {pin.key for pin in self.relation_pins}:
                raise StateModelError("relation_signatures and relation_pins must describe the same exact predicates")
            signature_roles = {pin.key for item in self.relation_signatures for pin in item.role_pins}
            if self.relation_role_pins and not signature_roles.issubset({pin.key for pin in self.relation_role_pins}):
                raise StateModelError("relation signature role lies outside declared relational role authority")
        if effective_kind is StateDomainKind.PROCESS and not self.process_pins:
            raise StateModelError("process state/support domain requires exact process pins")
        if self.unit_pin is not None and effective_kind not in {StateDomainKind.CONTINUOUS, StateDomainKind.VECTOR}:
            raise StateModelError("unit authority is only valid for scalar/vector state domains")
        if self.coordinate_frame_pin is not None and effective_kind is not StateDomainKind.VECTOR:
            raise StateModelError("coordinate-frame authority is only valid for vector state domains")
        if self.manifold_pin is not None and effective_kind is not StateDomainKind.VECTOR:
            raise StateModelError("manifold authority requires vector support")
        if (self.lower_bound is not None or self.upper_bound is not None) and effective_kind not in {StateDomainKind.CONTINUOUS, StateDomainKind.VECTOR}:
            raise StateModelError("numeric bounds require scalar/vector state domain")
        if self.vector_size is not None and effective_kind is not StateDomainKind.VECTOR:
            raise StateModelError("vector_size is only valid for vector state domain")
        if self.value_pins and effective_kind not in {StateDomainKind.CATEGORICAL, StateDomainKind.ORDERED}:
            raise StateModelError("value_pins are only valid for categorical/ordered state domains")
        if (self.relation_pins or self.relation_role_pins or self.relation_signatures) and effective_kind is not StateDomainKind.RELATIONAL:
            raise StateModelError("relation authority is only valid for relational state domains")
        if (self.element_type_pins or self.maximum_set_size is not None) and effective_kind is not StateDomainKind.SET:
            raise StateModelError("set constraints are only valid for set-valued state domains")
        if self.process_pins and effective_kind is not StateDomainKind.PROCESS:
            raise StateModelError("process_pins are only valid for process-valued state domains")

    @property
    def contract_ref(self) -> str:
        return "state-domain-contract:" + semantic_fingerprint("state-domain-v351", self, 32)


@dataclass(frozen=True, slots=True)
class ProbabilityPointV351:
    """One probability mass point over a typed non-probabilistic state value."""

    support_value: "StateValueV351"
    probability: float

    def __post_init__(self) -> None:
        if not isinstance(self.support_value, StateValueV351):
            raise StateModelError("probability support requires typed StateValueV351")
        if self.support_value.domain_kind == StateDomainKind.PROBABILISTIC:
            raise StateModelError("probability support cannot recursively be probabilistic")
        if not isfinite(self.probability) or self.probability < 0.0 or self.probability > 1.0:
            raise StateModelError("probability mass must be finite in [0,1]")

    @property
    def value_key(self) -> str:
        return self.support_value.value_ref


@dataclass(frozen=True, slots=True)
class RelationStateRoleBindingV351:
    """Exact semantic role binding inside one relational state value.

    Participant tuple position never carries meaning. Reflexive relations are legal because
    role identity, not participant uniqueness, distinguishes the relation arguments.
    """

    role_pin: ExactAuthorityPin
    participant_ref: str

    def __post_init__(self) -> None:
        _require_ref(self.participant_ref, "relation-state participant_ref")


@dataclass(frozen=True, slots=True)
class StateValueV351:
    """Canonical value occurrence for every Phase-15 domain family.

    Exactly one domain-specific payload is meaningful.  `value_ref` is derived from the
    normalized value document, so measured/vector/set/process values have stable identity
    without pretending to be ontology/schema records.
    """

    domain_kind: StateDomainKind
    categorical_pin: ExactAuthorityPin | None = None
    scalar_value: float | None = None
    vector_value: tuple[float, ...] = ()
    relation_pin: ExactAuthorityPin | None = None
    relation_bindings: tuple[RelationStateRoleBindingV351, ...] = ()
    set_members: tuple[str, ...] = ()
    process_pin: ExactAuthorityPin | None = None
    process_status: ProcessStatus | None = None
    process_progress: float | None = None
    probability_mass: tuple[ProbabilityPointV351, ...] = ()
    unit_pin: ExactAuthorityPin | None = None
    coordinate_frame_pin: ExactAuthorityPin | None = None
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _unique((item.role_pin.key for item in self.relation_bindings), "relation role bindings")
        _unique(self.set_members, "set members")
        _unique((item.value_key for item in self.probability_mass), "probability support keys")
        _unique(self.evidence_refs, "state value evidence")
        if self.scalar_value is not None:
            _finite(float(self.scalar_value), "scalar state value")
        for value in self.vector_value:
            _finite(float(value), "vector state component")
        if self.process_progress is not None:
            _finite(float(self.process_progress), "process progress")
            if not 0.0 <= float(self.process_progress) <= 1.0:
                raise StateModelError("process progress must be normalized to [0,1]")

        kind = self.domain_kind
        if kind in {StateDomainKind.CATEGORICAL, StateDomainKind.ORDERED}:
            if self.categorical_pin is None:
                raise StateModelError(f"{kind.value} value requires categorical_pin")
            self._forbid("categorical", self.scalar_value, self.vector_value, self.relation_pin,
                         self.relation_bindings, self.set_members, self.process_pin, self.process_status,
                         self.process_progress, self.probability_mass)
        elif kind == StateDomainKind.CONTINUOUS:
            if self.scalar_value is None:
                raise StateModelError("continuous value requires scalar_value")
            self._forbid("continuous", self.categorical_pin, self.vector_value, self.relation_pin,
                         self.relation_bindings, self.set_members, self.process_pin, self.process_status,
                         self.process_progress, self.probability_mass)
        elif kind == StateDomainKind.VECTOR:
            if not self.vector_value:
                raise StateModelError("vector value requires vector_value")
            self._forbid("vector", self.categorical_pin, self.scalar_value, self.relation_pin,
                         self.relation_bindings, self.set_members, self.process_pin, self.process_status,
                         self.process_progress, self.probability_mass)
        elif kind == StateDomainKind.RELATIONAL:
            if self.relation_pin is None or not self.relation_bindings:
                raise StateModelError("relational value requires relation_pin and exact role bindings")
            self._forbid("relational", self.categorical_pin, self.scalar_value, self.vector_value,
                         self.set_members, self.process_pin, self.process_status, self.process_progress,
                         self.probability_mass)
        elif kind == StateDomainKind.SET:
            self._forbid("set", self.categorical_pin, self.scalar_value, self.vector_value,
                         self.relation_pin, self.relation_bindings, self.process_pin, self.process_status,
                         self.process_progress, self.probability_mass)
        elif kind == StateDomainKind.PROCESS:
            if self.process_pin is None or self.process_status is None:
                raise StateModelError("process value requires process_pin and status")
            self._forbid("process", self.categorical_pin, self.scalar_value, self.vector_value,
                         self.relation_pin, self.relation_bindings, self.set_members, self.probability_mass)
        elif kind == StateDomainKind.PROBABILISTIC:
            if not self.probability_mass:
                raise StateModelError("probabilistic value requires probability_mass")
            total = sum(item.probability for item in self.probability_mass)
            if abs(total - 1.0) > 1e-8:
                raise StateModelError("probability mass must sum to 1")
            self._forbid("probabilistic", self.categorical_pin, self.scalar_value, self.vector_value,
                         self.relation_pin, self.relation_bindings, self.set_members, self.process_pin,
                         self.process_status, self.process_progress, self.unit_pin, self.coordinate_frame_pin)
        else:  # pragma: no cover - enum exhaustiveness
            raise StateModelError(f"unsupported state domain kind:{kind}")

    @staticmethod
    def _forbid(label: str, *values: object) -> None:
        def present(value: object) -> bool:
            return value is not None and value != () and value != [] and value != {}
        if any(present(value) for value in values):
            raise StateModelError(f"{label} state value contains payload for another domain kind")

    @property
    def value_ref(self) -> str:
        # Semantic state identity is independent of which observation/proof happened to
        # support this occurrence.  Evidence lineage belongs to the occurrence document, not
        # to equality/transition identity; otherwise identical values from two observations
        # would compare unequal and causal preconditions would become evidence-sensitive.
        return "state-value-occurrence:" + semantic_fingerprint(
            "state-value-v351", self.semantic_document(), 40
        )

    def semantic_document(self) -> Mapping[str, Any]:
        return {
            "model": "state-value-v351",
            "domain_kind": self.domain_kind.value,
            "categorical_pin": None if self.categorical_pin is None else self.categorical_pin.key,
            "scalar_value": self.scalar_value,
            "vector_value": self.vector_value,
            "relation_pin": None if self.relation_pin is None else self.relation_pin.key,
            "relation_bindings": tuple(
                (item.role_pin.key, item.participant_ref) for item in self.relation_bindings
            ),
            "set_members": self.set_members,
            "process_pin": None if self.process_pin is None else self.process_pin.key,
            "process_status": None if self.process_status is None else self.process_status.value,
            "process_progress": self.process_progress,
            "probability_mass": tuple(
                (item.support_value.semantic_document(), item.probability)
                for item in self.probability_mass
            ),
            "unit_pin": None if self.unit_pin is None else self.unit_pin.key,
            "coordinate_frame_pin": None if self.coordinate_frame_pin is None else self.coordinate_frame_pin.key,
        }

    def document(self) -> Mapping[str, Any]:
        return {**self.semantic_document(), "evidence_refs": self.evidence_refs}


@dataclass(frozen=True, slots=True)
class StateOperandV351:
    kind: OperandKind
    constant: StateValueV351 | float | tuple[float, ...] | tuple[str, ...] | None = None
    role_pin: ExactAuthorityPin | None = None
    dimension_pin: ExactAuthorityPin | None = None
    event_port_pin: ExactAuthorityPin | None = None
    parameter_pin: ExactAuthorityPin | None = None
    parameter_name: str = ""

    def __post_init__(self) -> None:
        if self.kind == OperandKind.CONSTANT and self.constant is None:
            raise StateModelError("constant operand requires a value")
        if self.kind == OperandKind.ROLE_STATE and (self.role_pin is None or self.dimension_pin is None):
            raise StateModelError("role-state operand requires exact role and dimension pins")
        if self.kind == OperandKind.EVENT_PORT and self.event_port_pin is None:
            raise StateModelError("event-port operand requires exact port pin")
        if self.kind == OperandKind.PARAMETER:
            if self.parameter_pin is None or not self.parameter_name.strip():
                raise StateModelError("parameter operand requires exact artifact pin and parameter name")


@dataclass(frozen=True, slots=True)
class StateTransformExpression:
    operator: StateTransformOperator
    operands: tuple[StateOperandV351, ...] = ()
    external_operator_pin: ExactAuthorityPin | None = None
    clamp_lower: float | None = None
    clamp_upper: float | None = None

    def __post_init__(self) -> None:
        if self.operator == StateTransformOperator.MANIFOLD_MAP and self.external_operator_pin is None:
            raise StateModelError("MANIFOLD_MAP requires exact external_operator_pin")
        if self.operator != StateTransformOperator.MANIFOLD_MAP and self.external_operator_pin is not None:
            raise StateModelError("external_operator_pin is only valid for MANIFOLD_MAP")
        if self.clamp_lower is not None:
            _finite(float(self.clamp_lower), "transform clamp lower")
        if self.clamp_upper is not None:
            _finite(float(self.clamp_upper), "transform clamp upper")
        if self.clamp_lower is not None and self.clamp_upper is not None and self.clamp_lower > self.clamp_upper:
            raise StateModelError("transform clamp lower cannot exceed upper")
        no_operand = {StateTransformOperator.CLEAR, StateTransformOperator.CLAMP, StateTransformOperator.PROCESS_STOP}
        if self.operator in no_operand and self.operands:
            raise StateModelError(f"{self.operator.value} transform has no operands")
        if self.operator not in no_operand and not self.operands:
            raise StateModelError(f"{self.operator.value} transform requires operands")

    @property
    def expression_ref(self) -> str:
        return "state-transform:" + semantic_fingerprint("state-transform-v351", self, 32)


@dataclass(frozen=True, slots=True)
class ParticipantRoleBinding:
    role_pin: ExactAuthorityPin
    participant_ref: str
    source_application_ref: str
    participant_type_pins: tuple[ExactAuthorityPin, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_ref(self.participant_ref, "participant role participant_ref")
        _require_ref(self.source_application_ref, "participant role source_application_ref")
        _unique((pin.key for pin in self.participant_type_pins), "participant type pins")
        _unique(self.evidence_refs, "participant role evidence")
        _unique(self.proof_refs, "participant role proofs")


@dataclass(frozen=True, slots=True)
class MechanismPrecondition:
    condition_ref: str
    holder_role_pin: ExactAuthorityPin
    dimension_pin: ExactAuthorityPin
    operator: ConditionOperatorV351
    expected_value: StateValueV351 | None = None
    expected_member_key: str = ""
    numeric_threshold: float | None = None
    unknown_policy: UnknownConditionPolicyV351 = UnknownConditionPolicyV351.PRESERVE_FRONTIER

    def __post_init__(self) -> None:
        _require_ref(self.condition_ref, "mechanism condition_ref")
        if self.numeric_threshold is not None:
            _finite(float(self.numeric_threshold), "mechanism numeric threshold")
        needs_value = self.operator in {
            ConditionOperatorV351.EQUALS, ConditionOperatorV351.NOT_EQUALS,
            ConditionOperatorV351.LESS_THAN, ConditionOperatorV351.LESS_EQUAL,
            ConditionOperatorV351.GREATER_THAN, ConditionOperatorV351.GREATER_EQUAL,
        }
        if needs_value and self.expected_value is None:
            raise StateModelError(f"{self.operator.value} precondition requires expected_value")
        if self.operator in {ConditionOperatorV351.CONTAINS, ConditionOperatorV351.NOT_CONTAINS}:
            if not self.expected_member_key:
                raise StateModelError("set-membership precondition requires expected_member_key")
        if self.operator == ConditionOperatorV351.PROBABILITY_AT_LEAST:
            if self.expected_value is None or self.numeric_threshold is None:
                raise StateModelError("probability threshold requires typed support value and threshold")
            if self.expected_value.domain_kind is StateDomainKind.PROBABILISTIC:
                raise StateModelError("probability threshold support value cannot itself be probabilistic")
            if not 0.0 <= self.numeric_threshold <= 1.0:
                raise StateModelError("probability threshold must be in [0,1]")


@dataclass(frozen=True, slots=True)
class MechanismDefeater:
    defeater_ref: str
    condition: MechanismPrecondition
    hard: bool = True
    attenuation: float = 0.0

    def __post_init__(self) -> None:
        _require_ref(self.defeater_ref, "mechanism defeater_ref")
        if not isfinite(self.attenuation) or not 0.0 <= self.attenuation <= 1.0:
            raise StateModelError("defeater attenuation must be finite in [0,1]")
        if self.hard and self.attenuation not in {0.0, 1.0}:
            raise StateModelError("hard defeater attenuation must be 0 or 1")


@dataclass(frozen=True, slots=True)
class RoleStateTransformV351:
    transform_ref: str
    target_role_pin: ExactAuthorityPin
    dimension_pin: ExactAuthorityPin
    expression: StateTransformExpression
    confidence: float = 1.0
    condition_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_ref(self.transform_ref, "role-state transform_ref")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise StateModelError("transform confidence must be finite in [0,1]")
        _unique(self.condition_refs, "transform condition refs")


@dataclass(frozen=True, slots=True)
class SecondaryEventTemplateV351:
    template_ref: str
    event_definition_pin: ExactAuthorityPin
    role_map: tuple[tuple[ExactAuthorityPin, ExactAuthorityPin], ...]
    delay_steps: int = 0

    def __post_init__(self) -> None:
        _require_ref(self.template_ref, "secondary event template_ref")
        if self.delay_steps < 0:
            raise StateModelError("secondary event delay_steps cannot be negative")
        _unique((source.key for source, _ in self.role_map), "secondary event source roles")
        _unique((target.key for _, target in self.role_map), "secondary event target roles")


@dataclass(frozen=True, slots=True)
class MechanismBranchV351:
    branch_ref: str
    probability: float
    transforms: tuple[RoleStateTransformV351, ...] = ()
    secondary_events: tuple[SecondaryEventTemplateV351, ...] = ()

    def __post_init__(self) -> None:
        _require_ref(self.branch_ref, "mechanism branch_ref")
        if not isfinite(self.probability) or not 0.0 <= self.probability <= 1.0:
            raise StateModelError("mechanism branch probability must be in [0,1]")
        _unique((item.transform_ref for item in self.transforms), "mechanism branch transforms")
        _unique(
            ((item.target_role_pin.key, item.dimension_pin.key) for item in self.transforms),
            "mechanism branch transform targets",
        )
        _unique((item.template_ref for item in self.secondary_events), "mechanism branch secondary events")


@dataclass(frozen=True, slots=True)
class TransitionMechanismV351:
    mechanism_ref: str
    revision: int
    trigger_kind: MechanismTriggerKind
    trigger_definition_pin: ExactAuthorityPin | None
    participant_role_pins: tuple[ExactAuthorityPin, ...]
    participant_type_requirements: tuple[tuple[ExactAuthorityPin, tuple[ExactAuthorityPin, ...]], ...] = ()
    source_dimension_pins: tuple[ExactAuthorityPin, ...] = ()
    preconditions: tuple[MechanismPrecondition, ...] = ()
    defeaters: tuple[MechanismDefeater, ...] = ()
    deterministic_transforms: tuple[RoleStateTransformV351, ...] = ()
    deterministic_secondary_events: tuple[SecondaryEventTemplateV351, ...] = ()
    branches: tuple[MechanismBranchV351, ...] = ()
    parameter_pins: tuple[ExactAuthorityPin, ...] = ()
    competence_case_pins: tuple[ExactAuthorityPin, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    lifecycle_status: str = "candidate"
    # Per-use authority is distinct from lifecycle. Candidate records declare the intended
    # structural use axis; promotion writes the exact authorized set and marks it explicit.
    use_operation: UseOperation = UseOperation.TRANSITION
    authorized_use_operations: tuple[UseOperation, ...] = ()
    use_authority_explicit: bool = False
    permission_ref: str = "public"
    context_scopes: tuple[str, ...] = ()
    aggregation_contract_pin: ExactAuthorityPin | None = None
    stochastic_independence_pin: ExactAuthorityPin | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_ref(self.mechanism_ref, "transition mechanism_ref")
        _require_ref(self.permission_ref, "transition mechanism permission_ref")
        if self.revision < 1:
            raise StateModelError("transition mechanism revision must be positive")
        if self.trigger_kind in {MechanismTriggerKind.EVENT, MechanismTriggerKind.EXOGENOUS} and self.trigger_definition_pin is None:
            raise StateModelError(f"{self.trigger_kind.value}-triggered mechanism requires exact trigger definition pin")
        if self.trigger_kind == MechanismTriggerKind.STATE_CHANGE and not self.source_dimension_pins:
            raise StateModelError("state-change mechanism requires source dimension pins")
        _unique((pin.key for pin in self.participant_role_pins), "mechanism participant roles")
        _unique((pin.key for pin in self.source_dimension_pins), "mechanism source dimensions")
        _unique((item.condition_ref for item in self.preconditions), "mechanism preconditions")
        _unique((item.defeater_ref for item in self.defeaters), "mechanism defeaters")
        _unique((item.transform_ref for item in self.deterministic_transforms), "mechanism transforms")
        _unique(
            ((item.target_role_pin.key, item.dimension_pin.key) for item in self.deterministic_transforms),
            "mechanism deterministic transform targets",
        )
        _unique((item.template_ref for item in self.deterministic_secondary_events), "mechanism secondary events")
        _unique((item.branch_ref for item in self.branches), "mechanism branches")
        _unique((pin.key for pin in self.parameter_pins), "mechanism parameters")
        _unique((pin.key for pin in self.competence_case_pins), "mechanism competence cases")
        _unique(self.authorized_use_operations, "mechanism authorized use operations")
        if self.use_operation is not UseOperation.TRANSITION:
            raise StateModelError("transition mechanisms must declare TRANSITION as their structural use axis")
        allowed_lifecycle = {"candidate", "structurally_closed", "provisional", "competence_verified", "active", "superseded", "rejected"}
        if self.lifecycle_status not in allowed_lifecycle:
            raise StateModelError("transition mechanism lifecycle status is not recognized")
        if self.authorized_use_operations and not self.use_authority_explicit:
            raise StateModelError("transition mechanism granted uses require explicit use authority")
        if self.use_authority_explicit and UseOperation.TRANSITION not in self.authorized_use_operations:
            raise StateModelError("explicit transition authority must include TRANSITION use")
        _unique(self.evidence_refs, "mechanism evidence")
        if self.lifecycle_status == "active" and not self.evidence_refs:
            raise StateModelError("active transition mechanism requires reviewed evidence")
        _unique(self.context_scopes, "mechanism context scopes")
        role_keys = {pin.key for pin in self.participant_role_pins}
        _unique((role.key for role, _ in self.participant_type_requirements), "participant type requirement roles")
        for role, type_pins in self.participant_type_requirements:
            if role.key not in role_keys:
                raise StateModelError("type requirement targets undeclared participant role")
            _unique((pin.key for pin in type_pins), "participant type requirements")
        condition_refs = {item.condition_ref for item in self.preconditions}
        for condition in (*self.preconditions, *(item.condition for item in self.defeaters)):
            if condition.holder_role_pin.key not in role_keys:
                raise StateModelError("mechanism condition targets undeclared participant role")
        transforms = (*self.deterministic_transforms, *(t for branch in self.branches for t in branch.transforms))
        for transform in transforms:
            if transform.target_role_pin.key not in role_keys:
                raise StateModelError("mechanism transform targets undeclared participant role")
            if set(transform.condition_refs).difference(condition_refs):
                raise StateModelError("mechanism transform references an undeclared precondition")
            for operand in transform.expression.operands:
                if operand.kind is OperandKind.ROLE_STATE and (
                    operand.role_pin is None or operand.role_pin.key not in role_keys
                ):
                    raise StateModelError("role-state operand references undeclared participant role")
        secondary_templates = (*self.deterministic_secondary_events, *(e for branch in self.branches for e in branch.secondary_events))
        for template in secondary_templates:
            if any(source.key not in role_keys for source, _target in template.role_map):
                raise StateModelError("secondary event mapping references undeclared source participant role")
        if self.branches:
            total = sum(item.probability for item in self.branches)
            if abs(total - 1.0) > 1e-8:
                raise StateModelError("stochastic mechanism branch probabilities must sum to 1")
            if self.deterministic_transforms or self.deterministic_secondary_events:
                raise StateModelError("mechanism cannot mix deterministic payload and stochastic branches")
        if not (self.deterministic_transforms or self.deterministic_secondary_events or self.branches):
            raise StateModelError("transition mechanism requires an effect or secondary event")

    @property
    def contract_ref(self) -> str:
        return self.mechanism_ref

    @property
    def authority_pin(self) -> ExactAuthorityPin:
        payload = {
            "mechanism_ref": self.mechanism_ref,
            "revision": self.revision,
            "trigger_kind": self.trigger_kind.value,
            "trigger_definition_pin": None if self.trigger_definition_pin is None else self.trigger_definition_pin.key,
            "roles": tuple(pin.key for pin in self.participant_role_pins),
            "type_requirements": tuple((role.key, tuple(pin.key for pin in pins)) for role, pins in self.participant_type_requirements),
            "source_dimensions": tuple(pin.key for pin in self.source_dimension_pins),
            "preconditions": self.preconditions,
            "defeaters": self.defeaters,
            "deterministic_transforms": self.deterministic_transforms,
            "deterministic_secondary_events": self.deterministic_secondary_events,
            "branches": self.branches,
            "parameters": tuple(pin.key for pin in self.parameter_pins),
            # Context/permission/lifecycle/competence/use grants are operational authority,
            # not causal mechanism identity. They are enforced by separate exact use authority.
            "aggregation_contract_pin": (
                None if self.aggregation_contract_pin is None else self.aggregation_contract_pin.key
            ),
            "stochastic_independence_pin": (
                None if self.stochastic_independence_pin is None else self.stochastic_independence_pin.key
            ),
        }
        return ExactAuthorityPin(
            "causal_mechanism", "cemm:v351:causal", self.mechanism_ref, self.revision,
            semantic_fingerprint("transition-mechanism-authority-v351", payload, 64), "global",
        )

    @property
    def executable(self) -> bool:
        return (
            self.lifecycle_status == "active"
            and bool(self.competence_case_pins)
            and self.use_authority_explicit
            and UseOperation.TRANSITION in self.authorized_use_operations
        )


@dataclass(frozen=True, slots=True)
class StateDeltaV351:
    delta_ref: str
    holder_ref: str
    dimension_pin: ExactAuthorityPin
    prior_value: StateValueV351 | None
    new_value: StateValueV351 | None
    transform_ref: str
    mechanism_pin: ExactAuthorityPin
    context_ref: str
    effective_time_ref: str
    confidence: float
    time_step: int = 0
    branch_probability: float = 1.0
    proof_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.delta_ref, "state delta_ref"), (self.holder_ref, "state delta holder_ref"),
            (self.transform_ref, "state delta transform_ref"), (self.context_ref, "state delta context_ref"),
            (self.effective_time_ref, "state delta effective_time_ref"),
        ):
            _require_ref(value, label)
        if self.prior_value is None and self.new_value is None:
            raise StateModelError("state delta cannot have both prior and new value absent")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise StateModelError("state delta confidence must be in [0,1]")
        if self.time_step < 0:
            raise StateModelError("state delta time_step cannot be negative")
        if not isfinite(self.branch_probability) or not 0.0 <= self.branch_probability <= 1.0:
            raise StateModelError("state delta branch_probability must be in [0,1]")
        _unique(self.proof_refs, "state delta proofs")
        _unique(self.evidence_refs, "state delta evidence")


@dataclass(frozen=True, slots=True)
class SecondaryEventCandidateV351:
    event_ref: str
    event_definition_pin: ExactAuthorityPin
    role_bindings: tuple[ParticipantRoleBinding, ...]
    context_ref: str
    time_step: int
    source_mechanism_pin: ExactAuthorityPin
    branch_probability: float
    proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_ref(self.event_ref, "secondary event_ref")
        _require_ref(self.context_ref, "secondary event context_ref")
        if self.time_step < 0:
            raise StateModelError("secondary event time_step cannot be negative")
        if not isfinite(self.branch_probability) or not 0.0 <= self.branch_probability <= 1.0:
            raise StateModelError("secondary event probability must be in [0,1]")
        _unique((item.role_pin.key for item in self.role_bindings), "secondary event role bindings")
        _unique(self.proof_refs, "secondary event proofs")


@dataclass(frozen=True, slots=True)
class TransitionPreviewProof:
    proof_ref: str
    mechanism_pin: ExactAuthorityPin
    trigger_ref: str
    role_bindings: tuple[ParticipantRoleBinding, ...]
    prestate_refs: tuple[str, ...]
    precondition_results: tuple[tuple[str, str], ...]
    defeater_results: tuple[tuple[str, str], ...]
    derived_delta_refs: tuple[str, ...]
    secondary_event_refs: tuple[str, ...]
    context_ref: str
    branch_ref: str
    branch_probability: float
    evidence_refs: tuple[str, ...] = ()
    parent_proof_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for value, label in (
            (self.proof_ref, "transition proof_ref"), (self.trigger_ref, "transition trigger_ref"),
            (self.context_ref, "transition proof context_ref"), (self.branch_ref, "transition proof branch_ref"),
        ):
            _require_ref(value, label)
        if not isfinite(self.branch_probability) or not 0.0 <= self.branch_probability <= 1.0:
            raise StateModelError("transition proof branch probability must be in [0,1]")
        _unique((item.role_pin.key for item in self.role_bindings), "transition proof roles")
        for values, label in (
            (self.prestate_refs, "transition prestate refs"),
            (self.derived_delta_refs, "transition derived delta refs"),
            (self.secondary_event_refs, "transition secondary event refs"),
            (self.evidence_refs, "transition evidence refs"),
            (self.parent_proof_refs, "transition parent proof refs"),
        ):
            _unique(values, label)


@dataclass(frozen=True, slots=True)
class TransitionDistribution:
    distribution_ref: str
    mechanism_pin: ExactAuthorityPin
    trigger_ref: str
    branches: tuple[tuple[str, float, tuple[StateDeltaV351, ...], tuple[SecondaryEventCandidateV351, ...], TransitionPreviewProof], ...]
    frontier_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_ref(self.distribution_ref, "transition distribution_ref")
        _require_ref(self.trigger_ref, "transition distribution trigger_ref")
        _unique((item[0] for item in self.branches), "transition distribution branch refs")
        total = sum(item[1] for item in self.branches)
        if self.branches and abs(total - 1.0) > 1e-8:
            raise StateModelError("transition distribution branch probability must sum to 1")
        _unique(self.frontier_refs, "transition distribution frontiers")


@dataclass(frozen=True, slots=True)
class EntitledStateVariableV351:
    state_variable_ref: str
    holder_ref: str
    dimension_pin: ExactAuthorityPin
    domain: StateDomainContractV351
    value: StateValueV351 | None
    context_ref: str
    valid_time_ref: str | None
    entitlement_proof_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_ref(self.state_variable_ref, "entitled state variable_ref")
        _require_ref(self.holder_ref, "entitled state holder_ref")
        _require_ref(self.context_ref, "entitled state context_ref")
        if self.dimension_pin.ref != self.domain.dimension_ref or self.dimension_pin.revision != self.domain.dimension_revision:
            raise StateModelError("entitled state variable domain does not match exact dimension pin")
        _unique(self.entitlement_proof_refs, "state entitlement proofs")
        _unique(self.evidence_refs, "state variable evidence")


__all__ = [
    "ConditionOperatorV351", "EntitledStateVariableV351", "MechanismBranchV351",
    "MechanismDefeater", "MechanismPrecondition", "MechanismTriggerKind", "OperandKind",
    "ParticipantRoleBinding", "ProbabilityPointV351", "ProcessStatus", "RelationStateRoleBindingV351",
    "RelationStateSignatureV351", "RoleStateTransformV351",
    "SecondaryEventCandidateV351", "SecondaryEventTemplateV351", "StateDeltaV351",
    "StateDomainContractV351", "StateDomainKind", "StateModelError", "StateOperandV351",
    "StateTransformExpression", "StateTransformOperator", "StateValueV351",
    "TransitionDistribution", "TransitionMechanismV351", "TransitionPreviewProof",
    "UnknownConditionPolicyV351",
]
