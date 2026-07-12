# CEMM v3.4 — Final Integrated Semantic and Cognitive Data Model

This document defines the minimum immutable records used across the kernel. Exact implementation syntax may differ, but field meaning and separation of concerns are normative.

## 1. Typed references

All cross-record references are typed and opaque internally.

```python
@dataclass(frozen=True)
class Ref(Generic[T]):
    id: str
```

Internal IDs never substitute for public lexical surfaces.

## 2. Semantic graph records

### 2.1 Referent

```python
@dataclass(frozen=True)
class Referent:
    id: str
    referent_kind: str              # entity, concept, place, source, schema, self, etc.
    canonical_key: str | None
    aliases: tuple[LexicalFormRef, ...]
    kind_hypotheses: tuple[KindHypothesis, ...]
    scope: Scope
    provenance: Provenance
    confidence: float
```

A provisional discourse referent may exist without a durable canonical identity.

### 2.2 Value

```python
@dataclass(frozen=True)
class Value:
    id: str
    value_type: str                 # boolean, enum, text, quantity, set, coordinate, etc.
    data: object
    unit: str | None = None
    normalization: str | None = None
    public_surface_hint: str | None = None
```

### 2.3 RoleBinding and OpenPort

```python
SemanticFillerRef = Ref[Referent | Value | Predication | Proposition | ContextFrame]

@dataclass(frozen=True)
class RoleBinding:
    role_schema_ref: Ref[RoleSchema]
    filler_ref: SemanticFillerRef
    confidence: float
    evidence_refs: tuple[Ref[EvidenceRecord], ...]

@dataclass(frozen=True)
class OpenPort:
    role_schema_ref: Ref[RoleSchema]
    required: bool
    cardinality: str
    constraints: tuple[Constraint, ...]
    source_span_refs: tuple[Ref[SurfaceSpan], ...]
```

### 2.4 Predication

```python
@dataclass(frozen=True)
class Predication:
    id: str
    predicate_schema_ref: Ref[PredicateSchema]
    bindings: tuple[RoleBinding, ...]
    open_ports: tuple[OpenPort, ...]
    occurrence_kind: str            # relation, state, event
    aspect: AspectProfile | None
    source_span_refs: tuple[Ref[SurfaceSpan], ...]
    evidence_refs: tuple[Ref[EvidenceRecord], ...]
    confidence: float
```

### 2.5 ModalQualifier

```python
@dataclass(frozen=True)
class ModalQualifier:
    modal_kind: str                 # possible, necessary, permitted, prohibited, obligated, capable
    holder_ref: Ref[Referent] | None
    degree: float | None
    source_refs: tuple[str, ...]
```

### 2.6 Proposition

```python
@dataclass(frozen=True)
class Proposition:
    id: str
    predication_ref: Ref[Predication]
    context_ref: Ref[ContextFrame]
    polarity: str                   # positive | negative
    modal_qualifiers: tuple[ModalQualifier, ...]
    attribution_ref: Ref[Referent | EvidenceRecord] | None
    valid_time: TimeExtent | None
    evidence_refs: tuple[Ref[EvidenceRecord], ...]
    derivation_kind: str            # observed, attributed, inferred, replayed
    derivation_parent_refs: tuple[Ref[Proposition | EvidenceRecord], ...]
    interpreted_under: tuple[Ref[SchemaEnvelope], ...]
    assessment_environment_fingerprint: str
```

### 2.7 ContextFrame

```python
@dataclass(frozen=True)
class ContextFrame:
    id: str
    context_kind: str               # actual, reported, belief, hypothetical, etc.
    owner_ref: Ref[Referent] | None
    parent_ref: Ref[ContextFrame] | None
    assumptions: tuple[Ref[Proposition], ...]
    accessibility_policy_ref: Ref[ContextSchema]
    valid_time: TimeExtent | None
    provenance: Provenance
```

### 2.8 EvidenceRecord

```python
@dataclass(frozen=True)
class EvidenceRecord:
    id: str
    evidence_kind: str
    target_refs: tuple[str, ...]
    stance: str                     # supports, opposes, observes, defines, corrects, retracts
    source_ref: Ref[Referent] | None
    signal_ref: Ref[SignalEnvelope] | None
    derivation_parent_refs: tuple[Ref[EvidenceRecord], ...]
    lineage_root_refs: tuple[Ref[EvidenceRecord], ...]
    transformation_kind: str | None # translation, paraphrase, summary, generation, retrieval-copy
    independence_cluster: str
    provenance_kind: str            # asserted, observed, entailed, inherited, hypothesized, etc.
    observed_at: datetime
    valid_time: TimeExtent | None
    confidence: float
    permission: Permission
    scope: Scope
    context_refs: tuple[Ref[ContextFrame], ...]
    support_status: str             # active, retracted, archived, privacy_deleted
```

### 2.9 StructuralLink

```python
@dataclass(frozen=True)
class StructuralLink:
    id: str
    link_type: str                  # fixed structural vocabulary only
    source_ref: str
    target_ref: str
    features: FrozenMap
```

## 3. Schema records

### 3.1 SchemaEnvelope

```python
@dataclass(frozen=True)
class SchemaContribution:
    field_path: str
    value_or_pattern_ref: str
    provenance_kind: str            # asserted, observed, entailed, inherited,
                                    # hypothesized, defaulted, induced,
                                    # adapter_supplied, boot_supplied
    evidence_refs: tuple[Ref[EvidenceRecord], ...]
    derivation_refs: tuple[str, ...]
    scope: Scope
    context_refs: tuple[Ref[ContextFrame], ...]
    confidence: float

@dataclass(frozen=True)
class SchemaDependency:
    dependency_kind: str            # definition, inheritance, selectional,
                                    # competence, evidence, adapter, policy,
                                    # realization, effect
    target_schema_ref: Ref[SchemaEnvelope]
    polarity: str                   # positive | negative
    monotonicity: str               # monotone | defeasible | non_monotone
    required_for_operations: frozenset[str]
    invalidation_policy: str

@dataclass(frozen=True)
class SchemaEnvelope(Generic[S]):
    record_id: str
    semantic_key: str
    schema_kind: str
    status: str                     # candidate, provisional, active, rejected, superseded
    scope: Scope                    # access/ownership, not truth context
    applicability_context_refs: tuple[Ref[ContextFrame], ...]
    valid_time: TimeExtent | None
    version: int
    payload: S
    grounding_spec_ref: str
    contribution_refs: tuple[Ref[SchemaContribution], ...]
    dependency_refs: tuple[Ref[SchemaDependency], ...]
    support_refs: tuple[Ref[EvidenceRecord], ...]
    counterevidence_refs: tuple[Ref[EvidenceRecord], ...]
    confidence: float
    permission: Permission
    provenance: Provenance
    supersedes_refs: tuple[Ref[SchemaEnvelope], ...]
```

### 3.2 GroundingSpecification and SemanticPattern

```python
@dataclass(frozen=True)
class SemanticPattern:
    pattern_kind: str
    function: str                   # constitutive, identity, selectional,
                                    # diagnostic, default, typical, incidental,
                                    # causal, normative
    strength: str                   # strict, defeasible, probabilistic
    expression: object              # typed pattern AST; never copied executable code
    context_refs: tuple[Ref[ContextFrame], ...]
    valid_time: TimeExtent | None
    exception_refs: tuple[str, ...]
    priority: int
    provenance_refs: tuple[str, ...]

@dataclass(frozen=True)
class GroundingSpecification:
    semantic_family: str
    required_definition_fields: tuple[str, ...]
    constitutive_pattern_refs: tuple[Ref[SemanticPattern], ...]
    differentiating_pattern_refs: tuple[Ref[SemanticPattern], ...]
    dependency_refs: tuple[Ref[SchemaDependency], ...]
    competency_case_refs: tuple[Ref[CompetencyCase], ...]
    allowed_cycle_classes: frozenset[str]
    minimum_independent_oracle_classes: frozenset[str]
```

Only patterns with an allowed function/strength combination satisfy a required definition field. A typical feature never satisfies a constitutive requirement by itself.

### 3.3 CompetencyCase

```python
@dataclass(frozen=True)
class CompetencyCase:
    id: str
    competency_kind: str            # compose, query, discriminate, infer, realize, etc.
    input_ref: str
    expected_pattern_ref: str
    oracle_kind: str                # invariant, audited_expected, independent_observation,
                                    # sibling_contrast, teaching_derived
    generation_lineage_refs: tuple[str, ...]
    oracle_lineage_refs: tuple[str, ...]
    independence_cluster: str
    counts_for_structure: bool
    counts_for_discrimination: bool
    counts_for_epistemic_support: bool
    context_refs: tuple[Ref[ContextFrame], ...]
    budget_cost: int
```

A teaching-derived case may count for structure but not independent discrimination or epistemic support.

### 3.4 RoleSchema

```python
@dataclass(frozen=True)
class RoleSchema:
    role_key: str
    required: bool
    cardinality: str                # one, optional_one, many, ordered_many
    accepted_object_families: frozenset[str]
    accepted_entity_kinds: frozenset[str]
    accepted_value_types: frozenset[str]
    allows_open_port: bool
    allows_embedded_predication: bool
    allows_embedded_proposition: bool
    co_reference_constraints: tuple[Constraint, ...]
    selectional_preferences: tuple[Preference, ...]
```

### 3.5 PredicateSchema

```python
@dataclass(frozen=True)
class PredicateSchema:
    semantic_key: str
    predication_kind: str           # relation, state, event
    agentive: bool
    aspect_profile: AspectProfile
    role_refs: tuple[Ref[RoleSchema], ...]
    context_behavior: ContextBehavior
    polarity_behavior: PolarityBehavior
    modality_behavior: ModalityBehavior
    preconditions: tuple[SemanticPattern, ...]
    predicted_effects: tuple[MutationTemplate, ...]
    query_projections: tuple[QueryProjection, ...]
    identity_policy: IdentityPolicy
    cardinality_policy: CardinalityPolicy
    evidence_policy: EvidencePolicy
    persistence_policy: PersistencePolicy
    lexicalization_refs: tuple[Ref[LexemeSenseSchema], ...]
    realization_refs: tuple[Ref[RealizationSchema], ...]
```

### 3.6 StateDimensionSchema

```python
@dataclass(frozen=True)
class StateDimensionSchema:
    semantic_key: str
    holder_kinds: frozenset[str]
    value_type: str
    unit: str | None
    cardinality: str
    temporal_policy: str            # instantaneous, interval, persistent_until_changed, event_derived
    contradiction_policy: str
    transition_predicate_refs: tuple[Ref[PredicateSchema], ...]
```

### 3.7 OperationSchema

```python
@dataclass(frozen=True)
class OperationSchema:
    semantic_key: str
    operation_class: str            # cognitive, communicative, external
    input_roles: tuple[Ref[RoleSchema], ...]
    output_roles: tuple[Ref[RoleSchema], ...]
    semantic_preconditions: tuple[SemanticPattern, ...]
    capability_schema_refs: tuple[Ref[CapabilitySchema], ...]
    policy_refs: tuple[Ref[PolicySchema], ...]
    cost_model: CostModel
    predicted_effects: tuple[MutationTemplate, ...]
    failure_modes: tuple[str, ...]
    idempotency_policy: str
    adapter_binding: str | None
```

### 3.8 CapabilitySchema

```python
@dataclass(frozen=True)
class CapabilitySchema:
    semantic_key: str
    operation_schema_refs: tuple[Ref[OperationSchema], ...]
    required_component_types: tuple[str, ...]
    required_input_channels: tuple[str, ...]
    required_output_channels: tuple[str, ...]
    required_resources: tuple[ResourceRequirement, ...]
    contextual_preconditions: tuple[SemanticPattern, ...]
    competency_tests: tuple[CompetencyTest, ...]
```

### 3.9 Derived schema assessments

```python
@dataclass(frozen=True)
class AssessmentEnvironmentFingerprint:
    schema_store_revision: int
    dependency_revision_hash: str
    grounding_policy_version: str
    competency_suite_hash: str
    kernel_foundation_version: str
    type_registry_version: str
    inference_policy_version: str
    truth_maintenance_version: str
    adapter_contract_hash: str
    context_scope_policy_version: str

@dataclass(frozen=True)
class SchemaGroundingAssessment:
    schema_record_ref: Ref[SchemaEnvelope]
    schema_revision: int
    structural_status: str          # opaque, partial, structurally_executable
    semantic_family_resolved: bool
    required_fields_complete: bool
    dependencies_grounded: bool
    constitutive_patterns_executable: bool
    differentiator_satisfied: bool
    cycle_class: str | None
    fixed_point_status: str | None
    competence_status: str          # untested, self_checked, limited,
                                    # independently_validated, failed
    demonstrated_competencies: frozenset[str]
    blocker_codes: tuple[str, ...]
    dependency_refs: tuple[Ref[SchemaDependency], ...]
    evidence_refs: tuple[Ref[EvidenceRecord], ...]
    environment_fingerprint: AssessmentEnvironmentFingerprint

@dataclass(frozen=True)
class SchemaUseProfile:
    schema_record_ref: Ref[SchemaEnvelope]
    context_ref: Ref[ContextFrame]
    requested_operation: str
    structural_status: str
    competence_status: str
    epistemic_admissibility: str    # admitted, attributed_only, contested, blocked
    permitted_semantic_operations: frozenset[str]
    limitations: tuple[str, ...]
    grounding_assessment_ref: Ref[SchemaGroundingAssessment]
    epistemic_assessment_refs: tuple[Ref[EpistemicAssessment], ...]
    environment_fingerprint: AssessmentEnvironmentFingerprint
```

These are derived control records. They do not create another schema store or ontology.

## 4. Cognitive-control records

### 4.1 WorkspaceEntry

```python
@dataclass(frozen=True)
class WorkspaceEntry:
    item_ref: str
    item_kind: str
    relevance: float
    novelty: float
    uncertainty: float
    urgency: float
    goal_impact: float
    causal_consequence: float
    activation_time: datetime
    decay_policy: str
    protected_by_goal_refs: tuple[str, ...]
```

### 4.2 EpistemicAssessment

```python
@dataclass(frozen=True)
class EpistemicAssessment:
    proposition_ref: Ref[Proposition]
    context_ref: Ref[ContextFrame]
    support_state: str              # supported, refuted, both, neither
    support_score: float
    opposition_score: float
    confidence: float
    accessible: bool
    fresh_enough: bool
    permission_allowed: bool
    schema_use_valid: bool
    admissibility: str              # admitted, attributed_only, contested, blocked
    causal_warrant_grade: str | None
    lineage_independence_count: int
    explanation_refs: tuple[str, ...]
    environment_fingerprint: AssessmentEnvironmentFingerprint
```

### 4.3 CapabilityAssessment

```python
@dataclass(frozen=True)
class CapabilityAssessment:
    subject_ref: Ref[Referent]
    operation_schema_ref: Ref[OperationSchema]
    status: str
    competence: float | None
    component_refs: tuple[str, ...]
    health: str
    resource_status: str
    permission_status: str
    condition_results: tuple[ConditionResult, ...]
    limitations: tuple[str, ...]
    observed_reliability: float | None
    valid_time: TimeExtent
    evidence_refs: tuple[str, ...]
```

### 4.4 GapRecord

```python
@dataclass(frozen=True)
class GapRecord:
    id: str
    gap_kind: str
    target_artifact_ref: str
    missing_fields: tuple[str, ...]
    conflicting_fields: tuple[str, ...]
    blocked_stage: str
    blocked_goal_refs: tuple[str, ...]
    preserved_artifact_refs: tuple[str, ...]
    hypothesis_refs: tuple[str, ...]
    probe_options: tuple[ProbePlan, ...]
    expected_evidence_schema_ref: str | None
    resume_checkpoint_ref: str
    learnable: bool
    budget: LearningBudget
```

### 4.5 GoalRecord

```python
@dataclass(frozen=True)
class GoalRecord:
    id: str
    owner_ref: Ref[Referent]
    desired_pattern: SemanticPattern
    goal_kind: str                  # world_state, information_state, discourse, maintenance
    priority: float
    urgency: float
    policy_priority: int
    success_conditions: tuple[SemanticPattern, ...]
    failure_conditions: tuple[SemanticPattern, ...]
    dependencies: tuple[Ref[GoalRecord], ...]
    conflicts: tuple[Ref[GoalRecord], ...]
    status: str
    expires_at: datetime | None
```

### 4.6 OperationInstance and PlanRecord

```python
@dataclass(frozen=True)
class OperationInstance:
    id: str
    schema_ref: Ref[OperationSchema]
    bindings: tuple[RoleBinding, ...]
    predicted_effects: tuple[MutationTemplate, ...]
    status: str
    idempotency_key: str

@dataclass(frozen=True)
class PlanRecord:
    id: str
    goal_refs: tuple[Ref[GoalRecord], ...]
    operations: tuple[OperationInstance, ...]
    dependencies: tuple[OperationDependency, ...]
    predicted_outcomes: tuple[SemanticPattern, ...]
    cost: CostEstimate
    risk: RiskEstimate
    score: float
    rejected_reasons: tuple[str, ...]
```

### 4.7 ExecutionLedger

```python
@dataclass(frozen=True)
class OperationOutcome:
    operation_ref: Ref[OperationInstance]
    started_at: datetime | None
    finished_at: datetime | None
    status: str
    output_refs: tuple[str, ...]
    observed_effect_refs: tuple[str, ...]
    failure: TypedFailure | None
    adapter_receipt: str | None

@dataclass(frozen=True)
class ExecutionLedger:
    plan_ref: Ref[PlanRecord]
    outcomes: tuple[OperationOutcome, ...]
    prediction_errors: tuple[PredictionError, ...]
```

### 4.8 LearningTransaction

```python
@dataclass(frozen=True)
class LearningTransaction:
    id: str
    gap_ref: Ref[GapRecord]
    target_sense_ref: str
    target_schema_ref: str
    base_schema_revision: int
    base_store_revision: int
    child_schema_revision: int | None
    child_snapshot_fingerprint: AssessmentEnvironmentFingerprint
    hypotheses: tuple[SchemaHypothesis, ...]
    expected_evidence_schema_ref: str
    acquired_evidence_refs: tuple[str, ...]
    grounding_frontier: tuple[str, ...]
    asked_probe_keys: frozenset[str]
    replay_checkpoint_ref: str
    replay_work_refs: tuple[str, ...]
    replay_results: tuple[ReplayResult, ...]
    competency_results: tuple[CompetencyResult, ...]
    structural_status: str
    competence_status: str
    admissibility_status: str
    status: str                     # open, probing, staged, provisional,
                                    # validated, committed, rolled_back
    scope: Scope
    context_refs: tuple[Ref[ContextFrame], ...]
    budget: LearningBudget
    provenance: Provenance
```

### 4.9 ReplayWorkItem and derived-artifact provenance

```python
@dataclass(frozen=True)
class ReplayWorkItem:
    id: str
    source_evidence_ref: Ref[EvidenceRecord]
    target_sense_ref: str
    target_schema_revision_ref: Ref[SchemaEnvelope]
    checkpoint_ref: str
    context_refs: tuple[Ref[ContextFrame], ...]
    dependency_fingerprint: str
    idempotency_key: str
    priority: float
    status: str                     # queued, running, succeeded, redeferred,
                                    # cancelled, stale
    attempt_count: int

@dataclass(frozen=True)
class DerivedArtifactProvenance:
    supporting_schema_revision_refs: tuple[Ref[SchemaEnvelope], ...]
    supporting_assessment_refs: tuple[Ref[SchemaGroundingAssessment], ...]
    evidence_refs: tuple[Ref[EvidenceRecord], ...]
    environment_fingerprint: AssessmentEnvironmentFingerprint
```

Every materialized inference, classification, cached answer, plan, message item, capability conclusion, and understanding claim carries equivalent dependency provenance so downgrade can retract it.

### 4.10 SemanticMessagePlan

```python
@dataclass(frozen=True)
class MessageContentItem:
    semantic_ref: str
    discourse_function: str
    stance: str
    focus: str
    required: bool
    provenance_refs: tuple[str, ...]

@dataclass(frozen=True)
class SemanticMessagePlan:
    id: str
    communicative_goal_refs: tuple[Ref[GoalRecord], ...]
    content_items: tuple[MessageContentItem, ...]
    rhetorical_relations: tuple[RhetoricalRelation, ...]
    addressee_refs: tuple[Ref[Referent], ...]
    language: str
    channel: str
    style_constraints: FrozenMap
```

### 4.11 MutationSet and CommitOutcome

```python
@dataclass(frozen=True)
class MutationOperation:
    id: str
    operation_kind: str
    semantic_identity: SemanticIdentity
    action: str                     # create, update, supersede, append, reject
    payload_ref: str
    required: bool
    expected_revision: int | None
    evidence_refs: tuple[str, ...]
    permission: Permission
    reason: str

@dataclass(frozen=True)
class MutationSet:
    id: str
    phase: str                      # critical | output | consolidation
    operations: tuple[MutationOperation, ...]

@dataclass(frozen=True)
class CommitOperationResult:
    mutation_ref: Ref[MutationOperation]
    status: str
    record_refs: tuple[str, ...]
    failure: TypedFailure | None

@dataclass(frozen=True)
class CommitOutcome:
    mutation_set_ref: Ref[MutationSet]
    results: tuple[CommitOperationResult, ...]
    required_satisfied: bool
    committed_revision: int | None
```

## 5. Identity rules

### 5.1 Proposition semantic identity

Proposition identity includes:

```text
predicate schema
normalized role-filler identities
context identity
polarity
modal qualifiers
valid-time policy bucket
qualifiers required by predicate identity policy
```

Evidence and confidence are not part of semantic identity.

### 5.2 State-slot identity

State identity includes:

```text
holder identity
state-dimension schema
context
scope/reference frame
qualifiers
```

The value distinguishes occupancy records under that slot. Cardinality/temporal policy determines reinforcement, coexistence, or supersession.

### 5.3 Schema identity

Schema revision identity is:

```text
stable schema/sense identity + schema kind + version
```

Scope and applicability are properties of a revision, not substitutes for sense identity. A lexical form can map to several candidate senses. Evidence assignments to opaque sense clusters remain reversible.

Schema identity merge uses an explicit reversible same-identity assessment or alias binding. Original references are retained for historical proposition integrity.

Learned evidence creates new revisions; it does not silently mutate boot or prior records.



### 5.4 Assessment and replay identity

Grounding assessment identity includes:

```text
exact schema revision
+ dependency/environment fingerprint
+ grounding/competence policy versions
```

Replay identity includes:

```text
source evidence
+ target sense/schema revision
+ checkpoint
+ context/scope
+ dependency/environment fingerprint
```

### 5.5 Revision retention

A proposition bound to a schema revision keeps that revision reachable. Garbage collection may compact indexes but may not remove revision content needed to interpret historical propositions or replay results.

## 6. Public-surface safety

Every public value must preserve or derive:

```text
public lexical form
language
semantic reference
source/provenance
features needed for morphology/reference
```

Opaque IDs, internal enum keys, role names, and open ports are never public fallbacks.
