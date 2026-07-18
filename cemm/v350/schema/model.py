"""CEMM v3.5 data-driven semantic schema metamodel.

Only stable structural discriminators are represented as Python enums. Learned
referent types, facets, states, actions, events, relations, policies, and values
remain versioned data records.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from enum import Enum
import hashlib
import json
from math import isfinite
from typing import Any, ClassVar, Iterable, Mapping, TypeAlias


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class SchemaClass(StrEnum):
    MEANING = "meaning_schema"
    REFERENT_TYPE = "referent_type"
    FACET = "facet"
    PROPERTY = "property"
    STATE_DIMENSION = "state_dimension"
    STATE_VALUE = "state_value"
    RELATION = "relation"
    ROLE = "role"
    FUNCTION = "function"
    ACTION = "action"
    EVENT = "event"
    UNIT = "unit"
    MEASURE_DIMENSION = "measure_dimension"
    OPERATOR = "operator"
    DISCOURSE_ACT = "discourse_act"
    DISCOURSE_RELATION = "discourse_relation"
    RESPONSE_POLICY = "response_policy"


class SchemaLifecycleStatus(StrEnum):
    CANDIDATE = "candidate"
    STRUCTURALLY_CLOSED = "structurally_closed"
    PROVISIONAL = "provisional"
    COMPETENCE_VERIFIED = "competence_verified"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class UseOperation(StrEnum):
    MENTION = "mention"
    GROUND = "ground"
    COMPOSE = "compose"
    QUERY = "query"
    INFER = "infer"
    TRANSITION = "transition"
    IMPACT = "impact"
    PLAN = "plan"
    EXECUTE = "execute"
    REALIZE = "realize"
    RESPONSE_POLICY = "response_policy"


class UseDecision(StrEnum):
    DENY = "deny"
    PRESERVE_ONLY = "preserve_only"
    PROVISIONAL = "provisional"
    ALLOW = "allow"


class StorageKind(StrEnum):
    """Stable serialization shape; never an executable semantic ontology."""

    ORDINARY = "ordinary"
    EVENT_OCCURRENCE = "event_occurrence"
    STATE_OCCURRENCE = "state_occurrence"
    PROPOSITION = "proposition"
    QUANTITY = "quantity"
    UNIT = "unit"
    TIME = "time"
    CONTEXT = "context"
    SCHEMA_TOPIC = "schema_topic"


class PortFillerClass(StrEnum):
    """Graph-node class accepted by a local semantic port.

    Proposition and event identity are still referents. They are constrained by
    storage kind and referent type, not introduced as parallel filler families.
    """

    REFERENT = "referent"
    SEMANTIC_APPLICATION = "semantic_application"
    SEMANTIC_VARIABLE = "semantic_variable"
    COORDINATION_GROUP = "coordination_group"
    QUOTED_LITERAL = "quoted_literal"


class OpenBindingPurpose(StrEnum):
    QUERY = "query"
    LEARNING = "learning"
    RULE = "rule"
    PARTIAL_COMPOSITION = "partial_composition"
    RESPONSE_PLANNING = "response_planning"


class ParentRevisionPolicy(StrEnum):
    AUTHORITATIVE = "authoritative"
    MINIMUM = "minimum"
    EXACT = "exact"


class EntitlementApplicability(StrEnum):
    REQUIRED = "required"
    OPTIONAL = "optional"
    CONDITIONAL = "conditional"
    PROHIBITED = "prohibited"
    INHERITED_ONLY = "inherited_only"


class EntitlementInheritancePolicy(StrEnum):
    INHERIT = "inherit"
    OVERRIDE = "override"
    NARROW_DOMAIN = "narrow_domain"
    EXTEND_DOMAIN = "extend_domain"
    BLOCK = "block"
    COMPOSE = "compose"


class ValidationSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True)
class Cardinality:
    minimum: int = 0
    maximum: int | None = 1

    def __post_init__(self) -> None:
        if self.minimum < 0:
            raise ValueError("cardinality minimum cannot be negative")
        if self.maximum is not None and self.maximum < self.minimum:
            raise ValueError("cardinality maximum cannot be below minimum")

    def accepts(self, count: int) -> bool:
        return count >= self.minimum and (self.maximum is None or count <= self.maximum)


@dataclass(frozen=True, slots=True)
class SchemaRevisionRef:
    schema_ref: str
    revision: int

    def __post_init__(self) -> None:
        _require_ref(self.schema_ref, "schema_ref")
        if self.revision < 1:
            raise ValueError("schema revision must be positive")


@dataclass(frozen=True, slots=True)
class SchemaParentLink:
    parent_ref: str
    revision_policy: ParentRevisionPolicy = ParentRevisionPolicy.AUTHORITATIVE
    revision: int | None = None
    inheritance_kind: str = "inherit"
    priority: int = 0

    def __post_init__(self) -> None:
        _require_ref(self.parent_ref, "parent_ref")
        _require_ref(self.inheritance_kind, "inheritance_kind")
        if self.revision_policy == ParentRevisionPolicy.AUTHORITATIVE and self.revision is not None:
            raise ValueError("authoritative parent selection cannot pin a revision")
        if self.revision_policy != ParentRevisionPolicy.AUTHORITATIVE:
            if self.revision is None or self.revision < 1:
                raise ValueError("minimum/exact parent selection requires a positive revision")


@dataclass(frozen=True, slots=True)
class SchemaProvenance:
    evidence_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()
    lineage_refs: tuple[str, ...] = ()
    created_by: str = ""
    created_at: str = ""
    field_sources: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _require_unique(self.evidence_refs, "provenance evidence refs")
        _require_unique(self.source_refs, "provenance source refs")
        _require_unique(self.lineage_refs, "provenance lineage refs")
        _require_unique(tuple(name for name, _ in self.field_sources), "provenance field names")


@dataclass(frozen=True, slots=True)
class SchemaDependency:
    dependency_ref: str
    dependency_kind: str
    minimum_revision: int | None = None
    exact_revision: int | None = None
    required: bool = True
    required_for: frozenset[UseOperation] = frozenset()
    reason: str = ""

    def __post_init__(self) -> None:
        _require_ref(self.dependency_ref, "dependency_ref")
        _require_ref(self.dependency_kind, "dependency_kind")
        if self.minimum_revision is not None and self.minimum_revision < 1:
            raise ValueError("minimum_revision must be positive")
        if self.exact_revision is not None and self.exact_revision < 1:
            raise ValueError("exact_revision must be positive")
        if self.minimum_revision is not None and self.exact_revision is not None:
            raise ValueError("dependency cannot set both exact_revision and minimum_revision")


@dataclass(frozen=True, slots=True)
class CompetenceHook:
    case_ref: str
    operation: UseOperation
    required: bool = True
    independent_lineage_ref: str = ""
    environment_ref: str = ""

    def __post_init__(self) -> None:
        _require_ref(self.case_ref, "case_ref")


@dataclass(frozen=True, slots=True)
class UseAuthorization:
    operation: UseOperation
    decision: UseDecision
    evidence_refs: tuple[str, ...] = ()
    reason: str = ""


@dataclass(frozen=True, slots=True)
class UseProfile:
    authorizations: tuple[UseAuthorization, ...] = ()

    def __post_init__(self) -> None:
        _require_unique(tuple(item.operation for item in self.authorizations), "use-profile operations")

    def decision_for(self, operation: UseOperation | str) -> UseDecision:
        resolved = operation if isinstance(operation, UseOperation) else UseOperation(operation)
        for item in self.authorizations:
            if item.operation == resolved:
                return item.decision
        return UseDecision.DENY

    def permits(self, operation: UseOperation | str, *, provisional: bool = False) -> bool:
        decision = self.decision_for(operation)
        return decision == UseDecision.ALLOW or (provisional and decision == UseDecision.PROVISIONAL)

    @classmethod
    def from_mapping(
        cls,
        decisions: Mapping[UseOperation | str, UseDecision | str],
    ) -> "UseProfile":
        items = [
            UseAuthorization(
                operation if isinstance(operation, UseOperation) else UseOperation(operation),
                decision if isinstance(decision, UseDecision) else UseDecision(decision),
            )
            for operation, decision in decisions.items()
        ]
        return cls(tuple(sorted(items, key=lambda item: item.operation.value)))


def schema_authorizes_use(
    schema: "MeaningSchema",
    operation: UseOperation | str,
    *,
    provisional: bool = False,
) -> bool:
    """Lifecycle-aware executable use gate.

    Candidate/structurally-closed records are proposals even if their proposed
    UseProfile contains ALLOW. ALLOW requires ACTIVE lifecycle; competence
    verification alone is not promotion. PROVISIONAL is visible only to explicitly
    provisional callers.
    """
    resolved = operation if isinstance(operation, UseOperation) else UseOperation(operation)
    decision = schema.use_profile.decision_for(resolved)
    if decision == UseDecision.ALLOW:
        return schema.lifecycle_status == SchemaLifecycleStatus.ACTIVE
    if decision == UseDecision.PROVISIONAL and provisional:
        return schema.lifecycle_status in {
            SchemaLifecycleStatus.PROVISIONAL,
            SchemaLifecycleStatus.COMPETENCE_VERIFIED,
            SchemaLifecycleStatus.ACTIVE,
        }
    return False


@dataclass(frozen=True, slots=True)
class LocalPortSchema:
    port_ref: str
    filler_classes: frozenset[PortFillerClass] = frozenset({PortFillerClass.REFERENT})
    accepted_type_refs: tuple[str, ...] = ()
    accepted_storage_kinds: frozenset[StorageKind] = frozenset()
    accepted_schema_classes: frozenset[SchemaClass] = frozenset()
    cardinality: Cardinality = field(default_factory=Cardinality)
    queryable: bool = False
    open_binding_purposes: frozenset[OpenBindingPurpose] = frozenset()
    role_family: str = ""
    context_policy: str = "inherit"
    time_policy: str = "inherit"
    identity_contribution: bool = False
    ordered_fillers: bool = False
    constraint_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_ref(self.port_ref, "port_ref")
        if not self.filler_classes:
            raise ValueError("a local port must accept at least one filler class")
        _require_unique(self.accepted_type_refs, f"accepted type refs for {self.port_ref}")
        _require_unique(self.constraint_refs, f"constraint refs for {self.port_ref}")
        if (
            self.accepted_type_refs or self.accepted_storage_kinds
        ) and PortFillerClass.REFERENT not in self.filler_classes:
            raise ValueError("referent constraints require the referent filler class")
        if self.accepted_schema_classes and PortFillerClass.SEMANTIC_APPLICATION not in self.filler_classes:
            raise ValueError("accepted_schema_classes require semantic_application fillers")
        if OpenBindingPurpose.QUERY in self.open_binding_purposes and not self.queryable:
            raise ValueError("query-open ports must be queryable")

    @property
    def allows_open(self) -> bool:
        return bool(self.open_binding_purposes)


@dataclass(frozen=True, slots=True)
class MeaningSchema:
    """Shared revisioned authority record for all executable schema families."""

    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.MEANING

    schema_ref: str
    semantic_key: str
    parent_links: tuple[SchemaParentLink, ...] = ()
    local_ports: tuple[LocalPortSchema, ...] = ()
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    revision: int = 1
    supersedes_revision: int | None = None
    scope_ref: str = "global"
    confidence: float = 1.0
    permission_ref: str = "public"
    provenance: SchemaProvenance = field(default_factory=SchemaProvenance)
    dependencies: tuple[SchemaDependency, ...] = ()
    use_profile: UseProfile = field(default_factory=UseProfile)
    competence_hooks: tuple[CompetenceHook, ...] = ()
    valid_from: str | None = None
    valid_to: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_ref(self.schema_ref, "schema_ref")
        _require_ref(self.semantic_key, "semantic_key")
        _require_ref(self.scope_ref, "scope_ref")
        _require_ref(self.permission_ref, "permission_ref")
        if self.revision < 1:
            raise ValueError("schema revision must be positive")
        if self.supersedes_revision is not None:
            if self.supersedes_revision < 1 or self.supersedes_revision >= self.revision:
                raise ValueError("supersedes_revision must identify an earlier positive revision")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("schema confidence must be within [0, 1]")
        parent_refs = tuple(link.parent_ref for link in self.parent_links)
        if self.schema_ref in parent_refs:
            raise ValueError(f"schema {self.schema_ref} cannot inherit from itself")
        _require_unique(parent_refs, f"parents of {self.schema_ref}")
        _require_unique(tuple(port.port_ref for port in self.local_ports), f"local ports of {self.schema_ref}")
        _require_unique(
            tuple((item.dependency_ref, item.dependency_kind) for item in self.dependencies),
            f"dependencies of {self.schema_ref}",
        )
        _require_unique(
            tuple((item.case_ref, item.operation) for item in self.competence_hooks),
            f"competence hooks of {self.schema_ref}",
        )

    @property
    def schema_class(self) -> SchemaClass:
        return self.SCHEMA_CLASS

    @property
    def parent_schema_refs(self) -> tuple[str, ...]:
        return tuple(link.parent_ref for link in self.parent_links)

    def port(self, port_ref: str) -> LocalPortSchema:
        for port in self.local_ports:
            if port.port_ref == port_ref:
                return port
        raise KeyError(f"unknown local port {port_ref!r} for {self.schema_ref}")

    @property
    def content_fingerprint(self) -> str:
        return semantic_fingerprint("schema-content", schema_content_document(self))

    @property
    def record_fingerprint(self) -> str:
        return semantic_fingerprint("schema-record", schema_to_document(self))

    @property
    def fingerprint(self) -> str:
        return self.record_fingerprint


@dataclass(frozen=True, slots=True)
class ReferentTypeSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.REFERENT_TYPE
    storage_kinds: frozenset[StorageKind] = frozenset({StorageKind.ORDINARY})
    facet_entitlement_refs: tuple[str, ...] = ()
    identity_criterion_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        super(ReferentTypeSchema, self).__post_init__()
        if not self.storage_kinds:
            raise ValueError("a referent type must permit at least one storage kind")
        _require_unique(self.facet_entitlement_refs, f"facet entitlements of {self.schema_ref}")
        _require_unique(self.identity_criterion_refs, f"identity criteria of {self.schema_ref}")


@dataclass(frozen=True, slots=True)
class FacetSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.FACET
    facet_family: str = ""
    permitted_storage_kinds: frozenset[StorageKind] = frozenset()

    def __post_init__(self) -> None:
        super(FacetSchema, self).__post_init__()
        _require_ref(self.facet_family, "facet_family")


@dataclass(frozen=True, slots=True)
class PropertySchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.PROPERTY
    holder_type_refs: tuple[str, ...] = ()
    value_type_refs: tuple[str, ...] = ()
    value_schema_refs: tuple[str, ...] = ()
    value_cardinality: Cardinality = field(default_factory=Cardinality)
    correction_policy: str = "supersede_same_holder"
    context_policy: str = "qualified"
    time_policy: str = "qualified"

    def __post_init__(self) -> None:
        super(PropertySchema, self).__post_init__()
        _require_unique(self.holder_type_refs, f"holder types of {self.schema_ref}")
        _require_unique(self.value_type_refs, f"value types of {self.schema_ref}")
        _require_unique(self.value_schema_refs, f"value schemas of {self.schema_ref}")


@dataclass(frozen=True, slots=True)
class StateDimensionSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.STATE_DIMENSION
    holder_type_refs: tuple[str, ...] = ()
    value_schema_refs: tuple[str, ...] = ()
    value_cardinality: Cardinality = field(default_factory=Cardinality)
    exclusive: bool = True
    ordered: bool = False
    scalar: bool = False
    persistence: str = "persistent_until_changed"
    observation_channel_refs: tuple[str, ...] = ()
    transition_contract_refs: tuple[str, ...] = ()
    default_rule_refs: tuple[str, ...] = ()
    applicability_rule_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        super(StateDimensionSchema, self).__post_init__()
        for label, values in (
            ("holder types", self.holder_type_refs),
            ("state values", self.value_schema_refs),
            ("observation channels", self.observation_channel_refs),
            ("transition contracts", self.transition_contract_refs),
            ("default rules", self.default_rule_refs),
            ("applicability rules", self.applicability_rule_refs),
        ):
            _require_unique(values, f"{label} of {self.schema_ref}")
        if self.scalar and not self.ordered:
            raise ValueError("a scalar state dimension must be ordered")


@dataclass(frozen=True, slots=True)
class StateValueSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.STATE_VALUE
    dimension_ref: str = ""
    ordering_key: str | float | int | None = None
    mutually_exclusive_with: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        super(StateValueSchema, self).__post_init__()
        _require_ref(self.dimension_ref, "dimension_ref")
        if isinstance(self.ordering_key, float) and not isfinite(self.ordering_key):
            raise ValueError("state-value ordering key must be finite")
        _require_unique(self.mutually_exclusive_with, f"exclusive values of {self.schema_ref}")


@dataclass(frozen=True, slots=True)
class RelationSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.RELATION
    symmetric: bool = False
    transitive: bool = False
    irreflexive: bool = False
    inverse_relation_ref: str | None = None
    persistence: str = "qualified"


@dataclass(frozen=True, slots=True)
class RoleSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.ROLE
    holder_type_refs: tuple[str, ...] = ()
    context_type_refs: tuple[str, ...] = ()
    occupancy_cardinality: Cardinality = field(default_factory=Cardinality)
    occupancy_policy: str = "time_context_qualified"

    def __post_init__(self) -> None:
        super(RoleSchema, self).__post_init__()
        _require_unique(self.holder_type_refs, f"holder types of {self.schema_ref}")
        _require_unique(self.context_type_refs, f"context types of {self.schema_ref}")


@dataclass(frozen=True, slots=True)
class FunctionSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.FUNCTION
    holder_type_refs: tuple[str, ...] = ()
    contribution_schema_refs: tuple[str, ...] = ()
    realization_action_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        super(FunctionSchema, self).__post_init__()
        _require_unique(self.holder_type_refs, f"holder types of {self.schema_ref}")
        _require_unique(self.contribution_schema_refs, f"contributions of {self.schema_ref}")
        _require_unique(self.realization_action_refs, f"actions of {self.schema_ref}")


@dataclass(frozen=True, slots=True)
class ActionSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.ACTION
    controlling_port_ref: str | None = None
    intentional_required: bool = True
    affordance_rule_refs: tuple[str, ...] = ()
    operation_contract_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        super(ActionSchema, self).__post_init__()
        if self.controlling_port_ref is not None:
            self.port(self.controlling_port_ref)
        _require_unique(self.affordance_rule_refs, f"affordance rules of {self.schema_ref}")
        _require_unique(self.operation_contract_refs, f"operation contracts of {self.schema_ref}")


@dataclass(frozen=True, slots=True)
class EventSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.EVENT
    temporal_profile: str = "occurrence"
    occurrence_constraint_refs: tuple[str, ...] = ()
    transition_contract_refs: tuple[str, ...] = ()
    result_contract_refs: tuple[str, ...] = ()
    causal_contract_refs: tuple[str, ...] = ()
    impact_rule_refs: tuple[str, ...] = ()
    persistence: str = "instantaneous"
    reversibility: str = "unknown"

    def __post_init__(self) -> None:
        super(EventSchema, self).__post_init__()
        for label, values in (
            ("occurrence constraints", self.occurrence_constraint_refs),
            ("transition contracts", self.transition_contract_refs),
            ("result contracts", self.result_contract_refs),
            ("causal contracts", self.causal_contract_refs),
            ("impact rules", self.impact_rule_refs),
        ):
            _require_unique(values, f"{label} of {self.schema_ref}")


@dataclass(frozen=True, slots=True)
class UnitSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.UNIT
    measure_dimension_ref: str = ""
    symbol_refs: tuple[str, ...] = ()
    conversion_rule_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        super(UnitSchema, self).__post_init__()
        _require_ref(self.measure_dimension_ref, "measure_dimension_ref")
        _require_unique(self.symbol_refs, f"symbols of {self.schema_ref}")
        _require_unique(self.conversion_rule_refs, f"conversion rules of {self.schema_ref}")


@dataclass(frozen=True, slots=True)
class MeasureDimensionSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.MEASURE_DIMENSION
    quantity_type_refs: tuple[str, ...] = ()
    canonical_unit_ref: str | None = None
    ordered: bool = True

    def __post_init__(self) -> None:
        super(MeasureDimensionSchema, self).__post_init__()
        _require_unique(self.quantity_type_refs, f"quantity types of {self.schema_ref}")


@dataclass(frozen=True, slots=True)
class OperatorSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.OPERATOR
    operator_family: str = ""
    minimum_arity: int = 1
    maximum_arity: int | None = 1
    scope_policy: str = "explicit"

    def __post_init__(self) -> None:
        super(OperatorSchema, self).__post_init__()
        _require_ref(self.operator_family, "operator_family")
        Cardinality(self.minimum_arity, self.maximum_arity)


@dataclass(frozen=True, slots=True)
class DiscourseActSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.DISCOURSE_ACT
    speaker_port_ref: str | None = None
    addressee_port_ref: str | None = None
    content_port_ref: str | None = None
    obligation_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        super(DiscourseActSchema, self).__post_init__()
        for port_ref in (self.speaker_port_ref, self.addressee_port_ref, self.content_port_ref):
            if port_ref is not None:
                self.port(port_ref)
        _require_unique(self.obligation_refs, f"obligations of {self.schema_ref}")


@dataclass(frozen=True, slots=True)
class DiscourseRelationSchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.DISCOURSE_RELATION
    source_class_refs: tuple[str, ...] = ()
    target_class_refs: tuple[str, ...] = ()
    structural: bool = True

    def __post_init__(self) -> None:
        super(DiscourseRelationSchema, self).__post_init__()
        _require_unique(self.source_class_refs, f"source classes of {self.schema_ref}")
        _require_unique(self.target_class_refs, f"target classes of {self.schema_ref}")


@dataclass(frozen=True, slots=True)
class ResponsePolicySchema(MeaningSchema):
    SCHEMA_CLASS: ClassVar[SchemaClass] = SchemaClass.RESPONSE_POLICY
    trigger_schema_refs: tuple[str, ...] = ()
    preferred_goal_refs: tuple[str, ...] = ()
    literal_realization_refs: tuple[str, ...] = ()
    safety_override_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        super(ResponsePolicySchema, self).__post_init__()
        for label, values in (
            ("triggers", self.trigger_schema_refs),
            ("preferred goals", self.preferred_goal_refs),
            ("literal realizations", self.literal_realization_refs),
            ("safety overrides", self.safety_override_refs),
        ):
            _require_unique(values, f"{label} of {self.schema_ref}")


@dataclass(frozen=True, slots=True)
class FacetEntitlement:
    entitlement_ref: str
    owner_type_ref: str
    facet_ref: str
    applicability: EntitlementApplicability
    activation_policy: str = "on_evidence"
    value_domain_refs: tuple[str, ...] = ()
    default_rule_refs: tuple[str, ...] = ()
    dependencies: tuple[SchemaDependency, ...] = ()
    inheritance_policy: EntitlementInheritancePolicy = EntitlementInheritancePolicy.INHERIT
    context_constraints: tuple[str, ...] = ()
    temporal_constraints: tuple[str, ...] = ()
    lifecycle_status: SchemaLifecycleStatus = SchemaLifecycleStatus.CANDIDATE
    revision: int = 1
    supersedes_revision: int | None = None
    scope_ref: str = "global"
    confidence: float = 1.0
    permission_ref: str = "public"
    provenance: SchemaProvenance = field(default_factory=SchemaProvenance)
    use_profile: UseProfile = field(default_factory=UseProfile)
    competence_hooks: tuple[CompetenceHook, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        for value, label in (
            (self.entitlement_ref, "entitlement_ref"),
            (self.owner_type_ref, "owner_type_ref"),
            (self.facet_ref, "facet_ref"),
            (self.activation_policy, "activation_policy"),
            (self.scope_ref, "scope_ref"),
            (self.permission_ref, "permission_ref"),
        ):
            _require_ref(value, label)
        if self.revision < 1:
            raise ValueError("entitlement revision must be positive")
        if self.supersedes_revision is not None:
            if self.supersedes_revision < 1 or self.supersedes_revision >= self.revision:
                raise ValueError("supersedes_revision must identify an earlier positive revision")
        if not isfinite(self.confidence) or not 0.0 <= self.confidence <= 1.0:
            raise ValueError("entitlement confidence must be within [0, 1]")
        for label, values in (
            ("value domains", self.value_domain_refs),
            ("default rules", self.default_rule_refs),
            ("context constraints", self.context_constraints),
            ("temporal constraints", self.temporal_constraints),
        ):
            _require_unique(values, f"{label} of {self.entitlement_ref}")
        _require_unique(
            tuple((item.dependency_ref, item.dependency_kind) for item in self.dependencies),
            f"dependencies of {self.entitlement_ref}",
        )

    @property
    def content_fingerprint(self) -> str:
        return semantic_fingerprint("entitlement-content", entitlement_content_document(self))

    @property
    def record_fingerprint(self) -> str:
        return semantic_fingerprint("entitlement-record", entitlement_to_document(self))

    @property
    def fingerprint(self) -> str:
        return self.record_fingerprint


SchemaRecord: TypeAlias = (
    MeaningSchema
    | ReferentTypeSchema
    | FacetSchema
    | PropertySchema
    | StateDimensionSchema
    | StateValueSchema
    | RelationSchema
    | RoleSchema
    | FunctionSchema
    | ActionSchema
    | EventSchema
    | UnitSchema
    | MeasureDimensionSchema
    | OperatorSchema
    | DiscourseActSchema
    | DiscourseRelationSchema
    | ResponsePolicySchema
)
MetamodelRecord: TypeAlias = SchemaRecord | FacetEntitlement


SCHEMA_CLASS_TO_TYPE: Mapping[SchemaClass, type[MeaningSchema]] = {
    SchemaClass.MEANING: MeaningSchema,
    SchemaClass.REFERENT_TYPE: ReferentTypeSchema,
    SchemaClass.FACET: FacetSchema,
    SchemaClass.PROPERTY: PropertySchema,
    SchemaClass.STATE_DIMENSION: StateDimensionSchema,
    SchemaClass.STATE_VALUE: StateValueSchema,
    SchemaClass.RELATION: RelationSchema,
    SchemaClass.ROLE: RoleSchema,
    SchemaClass.FUNCTION: FunctionSchema,
    SchemaClass.ACTION: ActionSchema,
    SchemaClass.EVENT: EventSchema,
    SchemaClass.UNIT: UnitSchema,
    SchemaClass.MEASURE_DIMENSION: MeasureDimensionSchema,
    SchemaClass.OPERATOR: OperatorSchema,
    SchemaClass.DISCOURSE_ACT: DiscourseActSchema,
    SchemaClass.DISCOURSE_RELATION: DiscourseRelationSchema,
    SchemaClass.RESPONSE_POLICY: ResponsePolicySchema,
}


_LIFECYCLE_TRANSITIONS: Mapping[SchemaLifecycleStatus, frozenset[SchemaLifecycleStatus]] = {
    SchemaLifecycleStatus.CANDIDATE: frozenset({SchemaLifecycleStatus.STRUCTURALLY_CLOSED, SchemaLifecycleStatus.REJECTED}),
    SchemaLifecycleStatus.STRUCTURALLY_CLOSED: frozenset({SchemaLifecycleStatus.PROVISIONAL, SchemaLifecycleStatus.REJECTED}),
    SchemaLifecycleStatus.PROVISIONAL: frozenset({SchemaLifecycleStatus.COMPETENCE_VERIFIED, SchemaLifecycleStatus.SUPERSEDED, SchemaLifecycleStatus.REJECTED}),
    SchemaLifecycleStatus.COMPETENCE_VERIFIED: frozenset({SchemaLifecycleStatus.ACTIVE, SchemaLifecycleStatus.SUPERSEDED, SchemaLifecycleStatus.REJECTED}),
    SchemaLifecycleStatus.ACTIVE: frozenset({SchemaLifecycleStatus.SUPERSEDED}),
    SchemaLifecycleStatus.SUPERSEDED: frozenset(),
    SchemaLifecycleStatus.REJECTED: frozenset(),
}


def lifecycle_transition_allowed(source: SchemaLifecycleStatus, target: SchemaLifecycleStatus) -> bool:
    return target in _LIFECYCLE_TRANSITIONS[source]


def require_lifecycle_transition(source: SchemaLifecycleStatus, target: SchemaLifecycleStatus) -> None:
    if not lifecycle_transition_allowed(source, target):
        raise ValueError(f"invalid schema lifecycle transition: {source.value} -> {target.value}")


def canonical_data(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {item.name: canonical_data(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {
            str(key.value if isinstance(key, Enum) else key): canonical_data(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (tuple, list)):
        return [canonical_data(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((canonical_data(item) for item in value), key=_canonical_sort_key)
    return value


def schema_to_document(schema: MeaningSchema) -> dict[str, Any]:
    document = canonical_data(schema)
    document["schema_class"] = schema.schema_class.value
    return document


def schema_content_document(schema: MeaningSchema) -> dict[str, Any]:
    document = schema_to_document(schema)
    for key in (
        "schema_ref", "revision", "supersedes_revision", "lifecycle_status", "scope_ref",
        "confidence", "permission_ref", "provenance", "use_profile", "competence_hooks",
        "valid_from", "valid_to",
    ):
        document.pop(key, None)
    return document


def entitlement_to_document(entitlement: FacetEntitlement) -> dict[str, Any]:
    document = canonical_data(entitlement)
    document["record_class"] = "facet_entitlement"
    return document


def entitlement_content_document(entitlement: FacetEntitlement) -> dict[str, Any]:
    document = entitlement_to_document(entitlement)
    for key in (
        "entitlement_ref", "revision", "supersedes_revision", "lifecycle_status", "scope_ref",
        "confidence", "permission_ref", "provenance", "use_profile", "competence_hooks",
    ):
        document.pop(key, None)
    return document


def semantic_fingerprint(prefix: str, value: Any, length: int = 32) -> str:
    payload = json.dumps(canonical_data(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return f"{prefix}:{hashlib.sha256(payload).hexdigest()[:length]}"


def all_schema_classes() -> tuple[SchemaClass, ...]:
    return tuple(SchemaClass)


def _canonical_sort_key(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _require_ref(value: str, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} is required")


def _require_unique(values: Iterable[Any], label: str) -> None:
    materialized = tuple(values)
    try:
        unique_count = len(set(materialized))
    except TypeError:
        unique_count = len({_canonical_sort_key(canonical_data(item)) for item in materialized})
    if unique_count != len(materialized):
        raise ValueError(f"duplicate {label}")
