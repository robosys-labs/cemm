"""Canonical CEMM v3.4.7 semantic records.

The only identity-bearing semantic object family is :class:`Referent`.
Predications bind predicate-owned local ports to referent IDs.  UOL graphs are
cycle-local; durable mutations are represented only as GraphPatch operations.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum
import hashlib
import json
from typing import Any, Iterable, Mapping


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ReferentKind(StrEnum):
    SELF = "self"
    AGENT = "agent"
    PERSON = "person"
    ANIMAL = "animal"
    ORGANIZATION = "organization"
    SOFTWARE_AGENT = "software_agent"
    PHYSICAL_OBJECT = "physical_object"
    DIGITAL_OBJECT = "digital_object"
    PLACE = "place"
    EVENT = "event"
    PROCESS = "process"
    STATE = "state"
    PROPOSITION = "proposition"
    QUANTITY = "quantity"
    UNIT = "unit"
    TIME = "time"
    COLLECTION = "collection"
    INFORMATION_OBJECT = "information_object"
    CONTEXT = "context"
    SCHEMA = "schema"
    TEXT = "text"
    UNKNOWN = "unknown"


class SchemaStatus(StrEnum):
    CANDIDATE = "candidate"
    PROVISIONAL = "provisional"
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"


class TruthStatus(StrEnum):
    SUPPORTED = "supported"
    OPPOSED = "opposed"
    BOTH = "both"
    UNDETERMINED = "undetermined"


class CommunicativeForce(StrEnum):
    ASSERT = "assert"
    ASK = "ask"
    REQUEST = "request"
    DIRECT = "direct"
    ACKNOWLEDGE = "acknowledge"
    CORRECT = "correct"
    PROMISE = "promise"
    REFUSE = "refuse"
    MENTION = "mention"


class Polarity(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"


class ContextMode(StrEnum):
    ACTUAL = "actual"
    REPORTED = "reported"
    BELIEVED = "believed"
    HYPOTHETICAL = "hypothetical"
    DESIRED = "desired"
    COUNTERFACTUAL = "counterfactual"
    SIMULATED = "simulated"
    QUOTED = "quoted"


class RuleFunction(StrEnum):
    IDENTITY = "identity"
    CONSTITUTIVE = "constitutive"
    STRICT = "strict"
    PREREQUISITE = "prerequisite"
    CAUSAL = "causal"
    ENABLING = "enabling"
    PREVENTING = "preventing"
    DEFAULT = "default"
    STATISTICAL = "statistical"
    PRAGMATIC = "pragmatic"
    NORMATIVE = "normative"


class RuleStrength(StrEnum):
    STRICT = "strict"
    DEFEASIBLE = "defeasible"
    PROBABILISTIC = "probabilistic"


class ConsequenceStatus(StrEnum):
    ENTAILED = "entailed"
    EXPECTED = "expected"
    PREDICTED = "predicted"
    POSSIBLE = "possible"
    BLOCKED = "blocked"


class GapKind(StrEnum):
    ANALYSIS = "analysis_gap"
    LEXICAL = "lexical_gap"
    REFERENCE = "reference_gap"
    IDENTITY = "identity_gap"
    PORT = "port_gap"
    SCHEMA = "schema_gap"
    CONTEXT = "context_gap"
    KNOWLEDGE = "knowledge_gap"
    EPISTEMIC = "epistemic_gap"
    CAPABILITY = "capability_gap"
    PERMISSION = "permission_gap"
    REALIZATION = "realization_gap"
    AMBIGUITY = "ambiguity_gap"


class ObservationKind(StrEnum):
    TEXT = "text"
    STRUCTURED = "structured"
    VISION = "vision"
    AUDIO = "audio"
    SENSOR = "sensor"
    TOOL = "tool"


class SchemaUseOperation(StrEnum):
    RECOGNIZE = "recognize"
    COMPOSE = "compose"
    QUERY = "query"
    INFER = "infer"
    LEARN = "learn"
    PLAN = "plan"
    EXECUTE = "execute"
    REALIZE = "realize"


class SchemaUseDecision(StrEnum):
    DENY = "deny"
    PRESERVE_ONLY = "preserve_only"
    PROVISIONAL = "provisional"
    ALLOW = "allow"


class ValidityRelation(StrEnum):
    BEFORE = "before"
    OVERLAPS = "overlaps"
    CONTAINS = "contains"
    DURING = "during"
    AFTER = "after"
    UNKNOWN = "unknown"


class PatchOperationKind(StrEnum):
    UPSERT_REFERENT = "upsert_referent"
    ADD_ALIAS = "add_alias"
    UPSERT_PREDICATION = "upsert_predication"
    UPSERT_PROPOSITION = "upsert_proposition"
    UPSERT_KNOWLEDGE = "upsert_knowledge"
    SUPERSEDE_KNOWLEDGE = "supersede_knowledge"
    RETRACT_SUPPORT = "retract_support"
    UPSERT_DISCOURSE_TURN = "upsert_discourse_turn"
    UPSERT_MENTION = "upsert_mention"
    UPSERT_OPEN_QUESTION = "upsert_open_question"
    CLOSE_OPEN_QUESTION = "close_open_question"
    UPSERT_WORLD_TRACK = "upsert_world_track"
    UPSERT_SCHEMA_CANDIDATE = "upsert_schema_candidate"
    UPSERT_RULE_CANDIDATE = "upsert_rule_candidate"
    UPSERT_EVIDENCE = "upsert_evidence"
    UPSERT_SCHEMA_REVISION = "upsert_schema_revision"
    UPSERT_RULE_REVISION = "upsert_rule_revision"
    ADD_DEPENDENCY = "add_dependency"
    RECORD_INVALIDATION = "record_invalidation"
    UPSERT_CAPABILITY_OBSERVATION = "upsert_capability_observation"
    UPSERT_OPERATION_LEDGER = "upsert_operation_ledger"
    UPSERT_EMISSION_LEDGER = "upsert_emission_ledger"
    UPSERT_TRUTH_ASSESSMENT = "upsert_truth_assessment"


@dataclass(frozen=True, slots=True)
class EvidenceRef:
    evidence_id: str
    source_ref: str
    confidence: float = 1.0
    lineage_ref: str = ""
    span_start: int | None = None
    span_end: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AnalyzerObservation:
    observation_id: str
    observation_kind: ObservationKind
    source_ref: str
    context_ref: str
    confidence: float
    payload: Mapping[str, Any]
    evidence_refs: tuple[str, ...] = ()
    observed_at: str = ""
    analyzer_ref: str = ""
    analyzer_version: str = ""


@dataclass(frozen=True, slots=True)
class CapabilityObservation:
    observation_id: str
    capability_ref: str
    available: bool
    confidence: float
    source_ref: str
    context_ref: str
    resource_state: Mapping[str, float] = field(default_factory=dict)
    valid_until: str | None = None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ValidityInterval:
    valid_from: str | None = None
    valid_to: str | None = None
    time_ref: str | None = None


@dataclass(frozen=True, slots=True)
class QuantityPayload:
    magnitude: str
    unit_ref: str | None = None
    comparator: str = "equal"
    tolerance: str | None = None


@dataclass(frozen=True, slots=True)
class TimePayload:
    start_iso: str | None = None
    end_iso: str | None = None
    granularity: str = "unknown"
    relative_anchor_ref: str | None = None


@dataclass(frozen=True, slots=True)
class PlacePayload:
    latitude: float | None = None
    longitude: float | None = None
    region_ref: str | None = None


@dataclass(frozen=True, slots=True)
class StatePayload:
    dimension_ref: str
    value_ref: str
    holder_ref: str | None = None
    valid_time_ref: str | None = None


@dataclass(frozen=True, slots=True)
class EventPayload:
    defining_predication_refs: tuple[str, ...] = ()
    valid_time_ref: str | None = None
    context_ref: str | None = None


@dataclass(frozen=True, slots=True)
class PropositionPayload:
    predication_refs: tuple[str, ...]
    context_ref: str
    polarity: Polarity = Polarity.POSITIVE
    modality_refs: tuple[str, ...] = ()
    attribution_ref: str | None = None
    valid_time_ref: str | None = None
    communicative_force: CommunicativeForce = CommunicativeForce.ASSERT


@dataclass(frozen=True, slots=True)
class SchemaTopicPayload:
    schema_ref: str
    schema_revision: int


Payload = (
    QuantityPayload
    | TimePayload
    | PlacePayload
    | StatePayload
    | EventPayload
    | PropositionPayload
    | SchemaTopicPayload
    | Mapping[str, Any]
    | None
)


@dataclass(frozen=True, slots=True)
class Referent:
    referent_id: str
    kind: ReferentKind
    type_refs: tuple[str, ...] = ()
    payload: Payload = None
    scope_ref: str = "global"
    context_ref: str = "actual"
    provenance: tuple[EvidenceRef, ...] = ()
    revision: int = 1
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.referent_id:
            raise ValueError("referent_id is required")
        if self.revision < 1:
            raise ValueError("referent revision must be positive")


@dataclass(frozen=True, slots=True)
class PortSchema:
    port_id: str
    accepted_kinds: frozenset[ReferentKind]
    required: bool = False
    query_open: bool = False
    multiple: bool = False
    role_family: str = ""
    accepted_type_refs: frozenset[str] = frozenset()
    identity_contribution: bool = False
    context_propagation: str = "inherit"
    time_propagation: str = "inherit"
    coercion_policy: str = "none"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def accepts(self, referent: Referent) -> bool:
        if self.accepted_kinds and referent.kind not in self.accepted_kinds:
            return False
        if self.accepted_type_refs and not self.accepted_type_refs.intersection(referent.type_refs):
            return False
        return True


@dataclass(frozen=True, slots=True)
class OperationalPort:
    operational_port_id: str
    predicate_schema_ref: str
    predicate_revision: int
    port_schema: PortSchema
    context_ref: str
    use_operation: SchemaUseOperation
    decision: SchemaUseDecision
    accepted_type_closure: frozenset[str] = frozenset()
    evidence_refs: tuple[str, ...] = ()
    assessment_fingerprint: str = ""
    reasons: tuple[str, ...] = ()

    def accepts(self, referent: "Referent") -> bool:
        return self.decision in {SchemaUseDecision.ALLOW, SchemaUseDecision.PROVISIONAL} and self.port_schema.accepts(referent)


@dataclass(frozen=True, slots=True)
class SchemaUseProfile:
    profile_id: str
    schema_ref: str
    schema_revision: int
    context_ref: str
    scope_ref: str
    operation_decisions: Mapping[str, SchemaUseDecision]
    structural_complete: bool
    epistemically_admissible: bool
    competence_passed: bool
    dependency_fingerprint: str
    evidence_refs: tuple[str, ...] = ()
    reasons: tuple[str, ...] = ()

    def permits(self, operation: SchemaUseOperation | str) -> bool:
        key = operation.value if isinstance(operation, SchemaUseOperation) else str(operation)
        return self.operation_decisions.get(key, SchemaUseDecision.DENY) in {
            SchemaUseDecision.ALLOW, SchemaUseDecision.PROVISIONAL
        }


@dataclass(frozen=True, slots=True)
class PredicateSchema:
    schema_ref: str
    semantic_key: str
    ports: tuple[PortSchema, ...]
    status: SchemaStatus = SchemaStatus.ACTIVE
    scope_ref: str = "global"
    revision: int = 1
    eventive: bool = False
    stateful: bool = False
    symmetric: bool = False
    inverse_predicate_ref: str | None = None
    supersedes_same_ports: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def port(self, port_id: str) -> PortSchema:
        for port in self.ports:
            if port.port_id == port_id:
                return port
        raise KeyError(f"unknown port {port_id!r} for {self.schema_ref}")


@dataclass(frozen=True, slots=True)
class PortBinding:
    port_id: str
    referent_refs: tuple[str, ...] = ()
    open_variable_ref: str | None = None
    confidence: float = 1.0
    evidence_refs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if bool(self.referent_refs) == bool(self.open_variable_ref):
            raise ValueError("binding must have either referent refs or one open variable")


@dataclass(frozen=True, slots=True)
class Predication:
    predication_id: str
    predicate_schema_ref: str
    bindings: tuple[PortBinding, ...]
    context_ref: str = "actual"
    source_evidence_refs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    confidence: float = 1.0
    revision: int = 1

    def binding(self, port_id: str) -> PortBinding | None:
        return next((binding for binding in self.bindings if binding.port_id == port_id), None)


@dataclass(frozen=True, slots=True)
class DiscourseRelation:
    relation_id: str
    relation_kind: str
    source_ref: str
    target_ref: str
    confidence: float = 1.0
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class UOLGraph:
    graph_id: str
    referents: Mapping[str, Referent]
    predications: Mapping[str, Predication]
    proposition_refs: tuple[str, ...]
    discourse_relations: tuple[DiscourseRelation, ...] = ()
    unresolved_refs: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MeaningHypothesis:
    hypothesis_id: str
    graph: UOLGraph
    proposition_refs: tuple[str, ...]
    communicative_force: CommunicativeForce
    score: float
    score_parts: Mapping[str, float]
    coverage: float
    unresolved_refs: tuple[str, ...] = ()
    incompatibility_keys: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SelectionAssessment:
    selected_hypothesis_refs: tuple[str, ...]
    rejected_hypothesis_refs: tuple[str, ...]
    total_score: float
    compatibility_score: float
    coverage: float
    incomplete: bool = False
    reason: str = ""


@dataclass(frozen=True, slots=True)
class MeaningBundle:
    bundle_id: str
    graph: UOLGraph
    hypothesis_refs: tuple[str, ...]
    proposition_refs: tuple[str, ...]
    assessment: SelectionAssessment
    alternatives: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LanguageHypothesis:
    language_tag: str
    confidence: float
    span_start: int = 0
    span_end: int | None = None
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class FormSpanCandidate:
    span_id: str
    start: int
    end: int
    surface: str
    normalized: str
    candidate_kind: str
    semantic_refs: tuple[str, ...] = ()
    language_tag: str = "und"
    confidence: float = 0.5
    evidence_refs: tuple[str, ...] = ()
    features: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class StructureRelationCandidate:
    relation_id: str
    relation_kind: str
    source_span_ref: str
    target_span_ref: str
    confidence: float
    evidence_refs: tuple[str, ...] = ()
    features: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class FormLattice:
    lattice_id: str
    raw_text: str
    language_hypotheses: tuple[LanguageHypothesis, ...]
    spans: tuple[FormSpanCandidate, ...]
    structural_relations: tuple[StructureRelationCandidate, ...]
    clause_span_refs: tuple[str, ...]
    evidence: tuple[EvidenceRef, ...]
    unresolved_span_refs: tuple[str, ...] = ()
    analyzer_versions: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ObservationLattice:
    lattice_id: str
    context_ref: str
    form_lattices: tuple[FormLattice, ...]
    observations: tuple[AnalyzerObservation, ...]
    fused_evidence: tuple[EvidenceRef, ...]
    modality_refs: tuple[str, ...]
    analyzer_fingerprint: str
    unresolved_observation_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GroundingCandidate:
    candidate_id: str
    mention_span_ref: str
    referent: Referent
    score: float
    score_parts: Mapping[str, float]
    evidence_refs: tuple[str, ...]
    provisional: bool = False


@dataclass(frozen=True, slots=True)
class GapRecord:
    gap_id: str
    kind: GapKind
    target_ref: str
    reason: str
    expected_type_refs: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()
    learnable: bool = False
    repair_options: tuple[str, ...] = ()
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class KnowledgeRecord:
    knowledge_id: str
    proposition_ref: str
    truth_status: TruthStatus
    context_ref: str
    source_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    confidence: float
    scope_ref: str
    sensitivity: str = "normal"
    permission_ref: str = "conversation"
    valid_time_ref: str | None = None
    revision: int = 1
    superseded_by: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    root_lineage_refs: tuple[str, ...] = ()
    derivation_refs: tuple[str, ...] = ()
    valid_from: str | None = None
    valid_to: str | None = None


@dataclass(frozen=True, slots=True)
class SchemaRevisionRecord:
    schema_ref: str
    schema_kind: str
    revision: int
    status: SchemaStatus
    scope_ref: str
    payload: Mapping[str, Any]
    field_provenance: Mapping[str, str]
    evidence_refs: tuple[str, ...]
    support_lineage_refs: tuple[str, ...]
    counterevidence_refs: tuple[str, ...] = ()
    confidence: float = 0.5
    permission_ref: str = "private_learning"
    dependency_refs: tuple[str, ...] = ()
    competence_case_refs: tuple[str, ...] = ()
    environment_fingerprint: str = ""


@dataclass(frozen=True, slots=True)
class DependencyRecord:
    dependency_id: str
    dependent_ref: str
    dependency_ref: str
    dependency_kind: str
    dependent_revision: int
    dependency_revision: int
    active: bool = True
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class InvalidationRecord:
    invalidation_id: str
    target_ref: str
    reason: str
    cause_ref: str
    prior_fingerprint: str
    invalidated_at_revision: int
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TruthAssessment:
    assessment_id: str
    proposition_signature: str
    context_ref: str
    truth_status: TruthStatus
    support_knowledge_refs: tuple[str, ...]
    opposition_knowledge_refs: tuple[str, ...]
    confidence: float
    valid_time_ref: str | None = None
    evidence_refs: tuple[str, ...] = ()
    store_revision: int = 0


@dataclass(frozen=True, slots=True)
class CompetenceCase:
    case_ref: str
    schema_ref: str
    operation: SchemaUseOperation
    input_payload: Mapping[str, Any]
    expected_payload: Mapping[str, Any]
    independent_lineage_ref: str
    required: bool = True


@dataclass(frozen=True, slots=True)
class CompetenceResult:
    result_ref: str
    case_ref: str
    passed: bool
    observed_payload: Mapping[str, Any]
    evidence_refs: tuple[str, ...]
    environment_fingerprint: str
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PatchOperation:
    operation_id: str
    kind: PatchOperationKind
    target_ref: str
    payload: Mapping[str, Any]
    expected_revision: int | None = None
    reversible: bool = True


@dataclass(frozen=True, slots=True)
class GraphPatch:
    patch_id: str
    context_ref: str
    scope_ref: str
    source_ref: str
    evidence_refs: tuple[str, ...]
    operations: tuple[PatchOperation, ...]
    expected_store_revision: int | None = None
    permission_ref: str = "conversation"
    validation_requirements: tuple[str, ...] = ()
    rollback_hint: str = ""
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PatchCommitResult:
    patch_id: str
    committed: bool
    store_revision_before: int
    store_revision_after: int
    applied_operation_refs: tuple[str, ...] = ()
    blocked_operation_refs: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RulePattern:
    predicate_schema_ref: str
    port_variables: Mapping[str, str]
    fixed_referent_refs: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuleSchema:
    rule_ref: str
    antecedents: tuple[RulePattern, ...]
    consequent: RulePattern
    function: RuleFunction
    strength: RuleStrength
    status: SchemaStatus = SchemaStatus.ACTIVE
    confidence: float = 1.0
    exceptions: tuple[RulePattern, ...] = ()
    sensitivity: str = "normal"
    scope_ref: str = "global"
    revision: int = 1
    priority: int = 0
    context_refs: tuple[str, ...] = ()
    valid_time_ref: str | None = None
    support_lineage_refs: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class InferenceProofStep:
    step_id: str
    rule_ref: str
    premise_knowledge_refs: tuple[str, ...]
    variable_bindings: Mapping[str, str]
    conclusion_proposition_ref: str
    consequence_status: ConsequenceStatus
    depth: int
    premise_proposition_refs: tuple[str, ...] = ()
    dependency_fingerprint: str = ""
    root_lineage_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class InferenceOutcome:
    proposition_refs: tuple[str, ...]
    proof_steps: tuple[InferenceProofStep, ...]
    incomplete: bool
    blocked_rule_refs: tuple[str, ...] = ()
    fired_rule_refs: tuple[str, ...] = ()
    elapsed_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class GoalRecord:
    goal_id: str
    goal_kind: str
    content_proposition_refs: tuple[str, ...]
    desired_state_ref: str | None
    priority: float
    success_conditions: tuple[RulePattern, ...] = ()
    source_ref: str = ""
    status: str = "active"


@dataclass(frozen=True, slots=True)
class OperationSchema:
    operation_ref: str
    semantic_predicate_ref: str
    input_ports: tuple[PortSchema, ...]
    output_ports: tuple[PortSchema, ...] = ()
    capability_ref: str = ""
    permission_ref: str = "conversation"
    risk: float = 0.0
    reversible: bool = True
    idempotent: bool = True
    status: SchemaStatus = SchemaStatus.ACTIVE
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class OperationPlan:
    plan_id: str
    operation_ref: str
    goal_ref: str
    bindings: tuple[PortBinding, ...]
    precondition_refs: tuple[str, ...]
    expected_effect_patch: GraphPatch | None
    risk: float
    authorized: bool = False
    authorization_reason: str = ""
    schema_revision: int = 1
    authorization_fingerprint: str = ""
    resource_requirements: Mapping[str, float] = field(default_factory=dict)
    live_capability_evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationOutcome:
    outcome_id: str
    plan_ref: str
    status: str
    observed_proposition_refs: tuple[str, ...] = ()
    effect_patch: GraphPatch | None = None
    errors: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResponseGoalCandidate:
    response_goal_id: str
    goal_kind: str
    target_proposition_refs: tuple[str, ...]
    score: float
    required: bool = False
    constraints: Mapping[str, Any] = field(default_factory=dict)
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ReferencePlan:
    referent_ref: str
    strategy: str
    preferred_alias: str = ""
    grammatical_features: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ResponseClausePlan:
    clause_id: str
    communicative_force: CommunicativeForce
    proposition_ref: str | None
    semantic_key: str
    port_bindings: Mapping[str, str]
    certainty: float
    attribution_ref: str | None = None
    optional: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class UOLResponsePlan:
    plan_id: str
    response_goal_refs: tuple[str, ...]
    target_language: str
    clauses: tuple[ResponseClausePlan, ...]
    discourse_order: tuple[str, ...]
    reference_plans: tuple[ReferencePlan, ...]
    tone_constraints: Mapping[str, Any]
    coverage_requirements: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    information_structure: Mapping[str, str] = field(default_factory=dict)
    coherence_relations: tuple[DiscourseRelation, ...] = ()
    response_context_ref: str = "actual"


@dataclass(frozen=True, slots=True)
class EmissionProof:
    proof_id: str
    plan_ref: str
    realized_clause_refs: tuple[str, ...]
    covered_semantic_refs: tuple[str, ...]
    blocked_semantic_refs: tuple[str, ...]
    active_schema_revisions: Mapping[str, int]
    evidence_refs: tuple[str, ...]
    authorized: bool
    reasons: tuple[str, ...] = ()
    round_trip_checked: bool = False
    round_trip_score: float = 0.0
    plan_fingerprint: str = ""
    store_revision: int = 0


@dataclass(frozen=True, slots=True)
class RoundTripAssessment:
    assessment_id: str
    plan_ref: str
    realized_text: str
    source_semantic_refs: tuple[str, ...]
    recovered_semantic_refs: tuple[str, ...]
    semantic_score: float
    authorized: bool
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class OperationLedgerRecord:
    ledger_ref: str
    plan_ref: str
    operation_ref: str
    status: str
    authorization_fingerprint: str
    capability_evidence_refs: tuple[str, ...]
    observed_proposition_refs: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class EmissionLedgerRecord:
    ledger_ref: str
    plan_ref: str
    proof_ref: str
    language_tag: str
    surface_hash: str
    authorized: bool
    covered_semantic_refs: tuple[str, ...]
    schema_revisions: Mapping[str, int]
    reasons: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RealizedMessage:
    text: str
    language_tag: str
    clause_texts: Mapping[str, str]
    proof: EmissionProof


@dataclass(slots=True)
class CycleTrace:
    cycle_id: str
    context_id: str
    stages: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def stage(self, name: str, detail: Any = None) -> None:
        self.stages.append(name)
        if detail is not None:
            self.details[name] = detail


@dataclass(frozen=True, slots=True)
class CycleResult:
    cycle_id: str
    context_id: str
    output_text: str
    target_language: str
    selected_bundle: MeaningBundle | None
    response_plan: UOLResponsePlan | None
    emission_proof: EmissionProof | None
    gaps: tuple[GapRecord, ...]
    committed_patch_refs: tuple[str, ...]
    trace: CycleTrace
    observation_lattice: ObservationLattice | None = None
    truth_assessments: tuple[TruthAssessment, ...] = ()


def canonical_data(value: Any) -> Any:
    """Return deterministic JSON-compatible data for semantic identity hashing."""
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: canonical_data(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): canonical_data(value[key]) for key in sorted(value, key=str)}
    if isinstance(value, (tuple, list)):
        return [canonical_data(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted(canonical_data(item) for item in value)
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(canonical_data(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def semantic_hash(prefix: str, value: Any, length: int = 24) -> str:
    digest = hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()[:length]
    return f"{prefix}:{digest}"


def bindings_map(bindings: Iterable[PortBinding]) -> dict[str, tuple[str, ...]]:
    return {binding.port_id: binding.referent_refs for binding in bindings if binding.referent_refs}
