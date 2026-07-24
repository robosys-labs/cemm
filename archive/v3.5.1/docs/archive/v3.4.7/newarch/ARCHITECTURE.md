# CEMM v3.5 Canonical Learning-First Architecture

**Status:** proposed replacement architecture contract  
**Target:** a grounded, multilingual, learning-first baby cognitive meaning system  
**Primary law:** CEMM may use, learn, infer, act on, or express only meaning that is represented in its active semantic substrate and authorized for the requested use.  
**Breaking boundary:** v3.5 replaces predicate-catalogue cognition, monolithic foundation data, targetless response moves, and per-predicate sentence realization.

---

## 1. System identity

CEMM is a **learning-first grounded meaning system**.

It is not:

- a phrase matcher;
- a sentence-intent router;
- a response-template catalogue;
- a generic knowledge graph whose edges have no executable semantics;
- a rule engine detached from referent state;
- an LLM wrapper;
- a transcript memory;
- an ontology that requires source-code changes for every new type;
- a simulator that silently treats defaults as actual facts.

CEMM's defining capability is not the number of phrases it recognizes. It is the ability to:

1. preserve uncertain multimodal evidence;
2. ground references to known or provisional referents;
3. compose reusable meaning atoms;
4. project what kinds of knowledge and actions are applicable to each referent;
5. form claims, events, states, queries, and goals;
6. learn missing semantic structure through grounded frontiers;
7. derive state transitions and consequences with proof;
8. assess impact and relevance;
9. create a response meaning graph;
10. realize that meaning in a target language;
11. remain silent or ask a precise question when authorization is absent.

---

## 2. Foundational ontology versus learned world knowledge

CEMM has a small *structural foundation* and an open-ended *learned semantic world*.

### 2.1 Structural foundation

The foundation defines only the machinery required to learn and operate:

- referents and identity;
- semantic types and inheritance;
- knowledge facets and entitlements;
- properties, state dimensions, actions, relations, roles, and functions;
- events, claims, propositions, and contexts;
- UOL operators and semantic axes;
- ports, variables, scope, time, and modality;
- evidence, epistemics, lifecycle, learning, inference, and patches;
- goals, operations, impacts, responses, and realization.

### 2.2 Learned semantic world

Domain concepts are data:

- fox;
- bank;
- president;
- battery;
- pregnancy;
- server;
- marriage;
- death;
- charging;
- fraud;
- greeting conventions;
- language lexicalizations.

A new type, action, property, event, or relationship must not require a Python enum, a new control-flow branch, or a sentence template.

---

## 3. Canonical semantic object: Referent

A **Referent** is anything with identity that CEMM can point to, bind, track, compare, mention, remember, query, or reason about.

Examples include:

- self and other agents;
- living organisms;
- physical and digital objects;
- places;
- event occurrences;
- state occurrences;
- propositions;
- claims as information objects;
- quantities and units;
- time instants and intervals;
- collections;
- contexts and possible worlds;
- schemas when schemas are discussed.

### 3.1 Minimal referent record

```text
Referent
  referent_ref
  storage_kind
  identity_status
  identity_facets
  semantic_type_assertion_refs
  scope_ref
  context_refs
  valid_time
  provenance_refs
  permission_ref
  lifecycle_status
  revision
```

The referent record does **not** contain a giant mutable object profile. Properties, states, capabilities, roles, relations, event participation, importance, and knowledge are represented as semantic applications and epistemic records.

### 3.2 Storage kind is not semantic type

`storage_kind` exists to serialize specialized identity payloads, such as:

```text
ordinary
event_occurrence
state_occurrence
proposition
quantity
unit
time
context
schema_topic
```

It is deliberately small and stable.

Executable typing uses data-driven `ReferentTypeSchema` records. A fox may simultaneously inherit:

```text
physical_entity
living_entity
organism
animal
mammal
agentive_organism
fox
```

No exclusive enum must choose only one.

### 3.3 Identity continuity

Identity is separate from state.

If a fox dies:

- the fox referent remains the same historical referent;
- its living-state interval ends;
- life-dependent capabilities become unavailable;
- the body can still participate in externally caused movement;
- prior states and events remain historically queryable.

Identity merge, split, replacement, and embodiment changes require explicit policies and provenance.

---

## 4. The universal referent knowledge envelope

All referents share one underlying knowledge architecture. Types decide which facets apply.

### 4.1 Foundational knowledge facets

```text
identity
existence
semantic_type
temporal
localization
composition/mereology
descriptive_property
state
relation
role
event_participation
action_affordance
capability/disposition
function/purpose
resource
epistemic
social/normative
affective
significance/importance
provenance/access
```

A facet is a family of knowledge that may apply to a referent. It is not necessarily a current value.

### 4.2 Facet entitlement

A `FacetEntitlement` is inherited from semantic types.

```text
FacetEntitlement
  owner_type_ref
  facet_ref
  applicability: required | optional | conditional | prohibited
  activation_policy
  value_domain_refs
  default_rule_refs
  dependency_refs
  inheritance_policy
  context_constraints
  temporal_constraints
```

Examples:

- every referent requires identity, type, context, provenance, and temporal validity metadata;
- a physical entity may have geospatial location, mass, shape, and containment;
- a living entity may have life status and biological process states;
- an animal may have affective and self-initiated motion capabilities;
- a digital entity may have connectivity, storage, execution, and data-access states;
- a proposition may have truth and epistemic status but not biological health;
- an event may have occurrence status, participants, time, place, causal links, and impacts;
- a place may have geospatial extent and occupancy but not an actor capability unless typed as an institution/agent too.

### 4.3 Facet projection status

At runtime, a facet projection has one of these statuses:

```text
active
latent
default_expected
unknown
blocked
terminated
inapplicable
contradicted
```

Definitions:

- **active** — a current value or capability is supported in the selected context/time;
- **latent** — applicable and structurally available, but not currently activated or instantiated;
- **default_expected** — inherited defeasible expectation, not admitted fact;
- **unknown** — applicable but no sufficient value is known;
- **blocked** — normally available but a condition currently prevents activation;
- **terminated** — a previously active interval has ended;
- **inapplicable** — the type/profile does not license this facet;
- **contradicted** — supported incompatible assignments remain unresolved.

A default must never be silently copied into active state.

### 4.4 Referent knowledge view

A `ReferentKnowledgeView` is a cycle-pinned derived projection:

```text
ReferentKnowledgeView
  referent_ref
  active_type_closure
  identity_assessments
  facet_entitlements
  property_assignments
  state_timelines
  active_relations
  active_roles
  event_history
  afforded_actions
  live_capabilities
  functions
  resources
  significance_assessments
  epistemic/access constraints
  unresolved conflicts
  dependency_fingerprint
```

It is computed from canonical records and is not a competing truth store.

---

## 5. Meaning schema families

All executable meaning schemas share lifecycle, inheritance, ports, constraints, provenance, and competence infrastructure.

```text
MeaningSchema
  schema_ref
  schema_class
  parent_schema_refs
  local_ports
  facet_contracts
  composition_contracts
  transition_contracts
  inference_contracts
  impact_contracts
  operation_contract_refs
  status/revision/provenance
```

Typed schema classes include:

```text
ReferentTypeSchema
PropertySchema
StateDimensionSchema
StateValueSchema
RelationSchema
RoleSchema
FunctionSchema
ActionSchema
EventSchema
UnitSchema
MeasureDimensionSchema
OperatorSchema
DiscourseActSchema
DiscourseRelationSchema
ResponsePolicySchema
```

Typed classes are necessary because a property and an event have different validation rules. They still share one authority and dependency model.

---

## 6. Properties, states, capabilities, functions, and roles

These concepts must remain distinct.

### 6.1 Property

A property is a relatively stable or identity-descriptive relation.

```text
property:name(holder, value)
property:version(holder, value)
property:material(holder, value)
property:owner(item, owner)
```

Properties can be time-qualified and corrected. “Stable” does not mean eternal.

### 6.2 State

A state is a time- and context-indexed condition along a state dimension.

```text
state:life_status(holder, alive)
state:connectivity(holder, connected)
state:emotion(holder, afraid)
state:operational_status(holder, degraded)
```

State values belong to explicit domains and may be mutually exclusive, overlapping, scalar, or composite.

### 6.3 Affordance

An affordance means an action is structurally meaningful for a type or referent.

```text
affords(type:software_agent, action:read)
affords(type:animal, action:self_initiated_move)
```

It does not prove current ability.

### 6.4 Disposition

A disposition is a latent capability activated under conditions.

```text
disposition(battery, supply_power)
requires(charge_level > 0)
```

### 6.5 Capability

A capability means a particular referent can currently instantiate an action under known conditions.

```text
capability(
  holder = self,
  action = read,
  status = available,
  conditions = content_accessible,
  evidence = runtime_reader_adapter
)
```

Capability status is one of:

```text
available
conditional
degraded
blocked
unavailable
terminated
unknown
```

### 6.6 Function

A function describes the intended, selected, institutional, or system contribution of a referent or component.

```text
function(heart, circulate_blood)
function(router, route_packets)
function(president_role, preside_over_jurisdiction)
```

Function is not identical to capability. A broken router retains its designed function while lacking current capability.

### 6.7 Role

A role is context- and time-bound occupancy.

```text
occupies_role(person, president_role, country, interval)
```

A role is not a predicate port and is not necessarily a referent type.

---

## 7. Native UOL semantic axes and gates

CEMM must not hide foundational semantic distinctions in ad hoc scores or strings.

### 7.1 Truth polarity

```text
positive proposition: P
negative proposition: NOT P
```

Truth negation says nothing about whether P is good or bad.

### 7.2 Existence and occurrence

```text
actual
reported
hypothetical
desired
planned
possible
counterfactual
fictional/simulated
non_occurring
```

### 7.3 Applicability and activation

```text
applicable | inapplicable
active | latent | blocked | terminated
```

### 7.4 Change direction

```text
set
activate
deactivate
gain
lose
increase
decrease
maintain
start
stop
create
destroy
enable
disable
```

### 7.5 Evaluative valence

Valence is stakeholder- and goal-relative:

```text
beneficial
harmful
mixed
neutral
unknown
```

A negative truth proposition is not harmful valence. A decrease is not always harmful. A loss event is not always unwanted by every stakeholder.

### 7.6 Importance and significance

Importance is a contextual assessment:

```text
ImportanceAssessment
  subject_ref
  stakeholder_ref
  context_ref
  score
  class: negligible | low | moderate | high | critical
  evidence_refs
  reasons
  valid_time
```

Evidence may include:

- explicit user statements;
- ownership, kinship, responsibility, or goal relations;
- mention frequency and recency;
- emotional language;
- event magnitude;
- uniqueness or irreversibility;
- active plans;
- prior corrections and focus;
- user-configured priorities.

Frequency alone cannot establish importance.

### 7.7 Certainty and epistemic status

```text
supported
opposed
both
undetermined
observed
reported
inferred
default_expected
assumed
```

### 7.8 Modality

```text
possible
capable
permitted
obligated
intended
desired
predicted
necessary
```

### 7.9 Normativity

```text
permitted
required
prohibited
recommended
discouraged
```

### 7.10 Persistence and reversibility

```text
instantaneous
durative
persistent_until_changed
terminal
reversible
partially_reversible
irreversible
unknown
```

These axes are first-class UOL values/operators. They can be learned, queried, compared, and realized.

---

## 8. Events and state transitions

### 8.1 Event occurrence

An event occurrence is a referent.

```text
EventOccurrence
  event_ref
  event_schema_ref
  participant_application_refs
  context_ref
  occurrence_status
  time_ref
  place_ref
  cause_refs
  result_refs
  provenance_refs
```

### 8.2 Action versus event

An action is an event schema with an intentional or controlling participant and possible operation implementation. Not every event is an action.

Examples:

```text
action:write
action:move
event:die
event:rain
event:collapse
```

### 8.3 Transition contract

An event schema can declare generic effects:

```text
TransitionContract
  trigger_event_schema_ref
  condition_pattern
  affected_port
  state_delta_templates
  capability_delta_templates
  relation_delta_templates
  created/terminated_referent_templates
  persistence
  defeaters
  warrant_class
```

These are semantic rules over ports and state dimensions, not sentence templates and not custom event code.

### 8.4 State delta

```text
StateDelta
  holder_ref
  dimension_ref
  operation: set | activate | deactivate | increase | decrease | terminate
  from_value_ref?
  to_value_ref?
  magnitude_ref?
  context_ref
  effective_time_ref
  duration_ref?
  confidence
  proof_refs
```

### 8.5 Capability dependency

Capabilities declare grounded requirements:

```text
CapabilityDependency
  capability/action_ref
  required_state_pattern
  required_resource_pattern
  required_component_pattern
  dependency_kind
```

When a state transition invalidates a requirement, capability status is recomputed.

---

## 9. Death as a foundational transition example

`die` must not be hard-coded as a response phrase or a collection of manual assignments.

### 9.1 Semantic event

```text
event:die
ports:
  affected: living_entity
  time: time
  cause: event_or_state? 
```

### 9.2 Transition meaning

A supported occurrence normally implies:

```text
life_status(affected, alive) ends at t
life_status(affected, dead) starts at t
biological_life_process(affected) terminates at t
```

### 9.3 Capability consequences

Capabilities tagged with living-state dependencies are recomputed.

Potential consequences for a fox include:

```text
self_initiated_locomotion → unavailable
voluntary_action → unavailable
affective_experience → unavailable
homeostatic_regulation → terminated
biological_growth → terminated
```

Important constraints:

- “health” is a state dimension, not a capability;
- the system should not merely set health to “bad”; health may become terminal or inapplicable after death;
- externally caused body movement remains possible;
- historical capabilities and prior events remain true in their earlier intervals;
- plants, animals, software, batteries, and organizations require different senses or event schemas for surface forms such as “died.”

### 9.4 Sense disambiguation

```text
“The fox died.”      → biological death candidate
“The battery died.”  → power depletion/operational failure candidate
“The company died.”  → organizational cessation candidate
“The joke died.”     → discourse/activity cessation candidate
```

The language analyzer proposes senses. Type compatibility and event contracts rank them.

### 9.5 Impact

Biological death has a high-priority default harmful impact for the affected living referent, but stakeholder valence is contextual.

```text
ImpactAssessment
  event_ref
  affected_ref
  stakeholder_ref
  affected_facet_refs
  direction
  magnitude
  valence
  reversibility
  duration
  certainty
  importance
  proof_refs
```

A fox's death may be:

- highly harmful and important to a user who owns and frequently discusses the fox;
- low-personal-importance but still negative in a wildlife report;
- mixed or positively valued by a stakeholder if the fox threatened livestock;
- fictional if it occurred in a story.

CEMM must preserve these distinctions.

---

## 10. Claims, propositions, evidence, and knowledge

### 10.1 Proposition

A proposition is truth-evaluable semantic content.

```text
PropositionReferent
  content_application_refs
  context_ref
  polarity
  modality
  valid_time_ref
```

### 10.2 Claim occurrence

A claim is an event in which a claimant presents a proposition with some commitment.

```text
ClaimOccurrence
  claimant_ref
  audience_refs
  proposition_ref
  claim_force
  certainty_expression
  evidence_offered_refs
  context_ref
  time_ref
```

The statement “the fox died” provides evidence for:

1. a claim occurrence by the speaker;
2. proposition content about a death event.

It does not directly prove actual death.

### 10.3 Claim record

A `ClaimRecord` preserves:

```text
claim_ref
claim_occurrence_ref
proposition_ref
source_ref
source_context_ref
reported_context_ref
commitment_strength
evidence_refs
scope
permission
revision
```

### 10.4 CEMM epistemic stance

CEMM separately stores:

```text
KnowledgeRecord
  proposition_ref
  status: supported | opposed | both | undetermined
  evidence_refs
  source_refs
  confidence
  context_ref
  valid_time
  sensitivity
  permission
```

Claim, evidence, proposition, and knowledge are never interchangeable.

### 10.5 Corrections

A correction may:

- oppose a prior proposition;
- supersede one source's earlier support;
- preserve both claims historically;
- update active state projection;
- invalidate dependent conclusions;
- keep unrelated source support intact.

---

## 11. Multimodal state architecture

### 11.1 Modality-neutral observation

Text, audio, vision, sensors, tools, and databases all produce evidence.

### 11.2 State channels

Types may entitle dimensions across channels:

```text
temporal
geospatial
physical
biological
affective
cognitive
social
digital
operational
epistemic
discourse
normative
```

### 11.3 Examples

A living animal may have:

```text
life status
location
health
energy
fear/arousal
attention
locomotion capability
social relation
```

A server may have:

```text
operational status
CPU load
storage
connectivity
temperature
service capability
location
```

A proposition may have:

```text
truth status
source attribution
confidence
common-ground status
sensitivity
```

An event may have:

```text
planned/ongoing/completed status
time
place
participants
impact
causal relations
```

### 11.4 Fusion

Conflicting modality evidence remains separate until an epistemic/state assessment resolves or preserves the contradiction. A visual tracker, user report, and sensor value are not automatically equal sources.

---

## 12. Learning-first semantic architecture

### 12.1 Learning is a primary operating mode

Every cycle can produce:

- selected meaning;
- unresolved typed dependencies;
- candidate learning contributions;
- evidence for existing schema revision;
- counterevidence;
- competence cases;
- promotion or invalidation proposals.

Learning is not a fallback triggered only by unknown words.

### 12.2 Learnable package

A `ConceptLearningPackage` can contain:

```text
target schema/referent
parent type assertions
identity criteria
facet entitlements
property schemas
state dimensions and domains
actions and participant ports
affordances and dispositions
capability dependencies
functions and roles
event transition contracts
impact/default rules
lexeme senses
realization frames
examples
counterexamples
exceptions/defeaters
competence cases
scope/permission
```

A package may be incomplete. Its exact unresolved requirements form a grounding frontier.

### 12.3 Grounding frontier

```text
GroundingFrontierItem
  target_ref
  missing_contract
  expected_schema_class
  accepted_anchor_types
  dependency_depth
  sensitivity
  best_question
  resolution_status
```

CEMM asks the smallest, safest question that unlocks the most reusable structure.

### 12.4 Learning a new referent type

To learn a type, CEMM seeks:

1. parent types;
2. identity criteria;
3. applicable facets;
4. characteristic but non-definitional defaults;
5. actions/relations/roles;
6. event and state constraints;
7. examples and counterexamples;
8. lexicalizations.

Not every field is required for mention-level use. Schema use profiles define what is permitted:

```text
mention
resolve
classify
query
infer
realize
plan
execute
```

### 12.5 Learning an event

To learn `event:X`, CEMM seeks:

- event parent class;
- participants and accepted types;
- occurrence conditions;
- before/after state transitions;
- persistence and reversibility;
- causal versus constitutive implications;
- capability/resource effects;
- exceptions;
- impact defaults;
- lexical senses.

### 12.6 Negative evidence

Counterexamples and corrections are first-class. A learned rule cannot become universal merely because positive examples were repeated.

### 12.7 Promotion

```text
candidate
→ structurally_closed
→ provisional
→ competence_verified
→ active
→ superseded/rejected
```

Promotion is operation-relative. A schema may be active for interpretation but not inference or execution.

---

## 13. UOL semantic workbench

UOL contains:

```text
Referent
SemanticApplication
SemanticVariable
ScopeRelation
CoordinationGroup
PropositionReferent
ClaimOccurrence
EventOccurrence
DiscourseActOccurrence
MeaningHypothesis
MeaningBundle
```

A `SemanticApplication` applies a meaning schema to local ports.

Examples:

```text
property:name(holder=user, value=Chibu)
state:life_status(holder=fox, value=dead)
event:die(affected=fox, time=t1)
operator:negation(scope=event:die(...))
operator:ability(holder=self, action=?action)
operator:query(variable=?action, restriction=ability(...))
```

UOL is cycle-local cognition. Durable knowledge and learned schemas require GraphPatches.

---

## 14. Inference, transition propagation, and simulation

### 14.1 Rule classes

```text
identity
constitutive
strict
state_transition
causal
enabling
preventing
default
statistical
pragmatic
normative
impact
response_policy
```

### 14.2 Context isolation

Rules fire inside an explicit context:

- actual;
- reported;
- believed;
- hypothetical;
- desired;
- planned;
- counterfactual;
- fictional;
- simulated.

“The fox may die” must not transition actual fox state.

### 14.3 Transition preview

Before admission or action, the engine can compute a proof-bearing preview:

```text
event candidate
→ state deltas
→ capability/resource deltas
→ secondary consequences
→ impact candidates
```

Preview does not mutate stores.

### 14.4 Commit

Only epistemically admitted or observed events produce durable state transitions in the relevant context.

### 14.5 Invalidation

When a premise, type, state, or event is corrected, dependent projections and conclusions are invalidated and recomputed.

---

## 15. Impact, importance, and response cognition

### 15.1 Event impact is semantic

Response-goal selection considers what selected meaning changes for relevant stakeholders.

### 15.2 Significance coordinator

The `SignificanceCoordinator` produces contextual assessments from:

- direct impact;
- irreversibility;
- affected facet centrality;
- relation to user/self/active goals;
- explicit importance;
- recurrence and magnitude;
- mention history;
- emotional evidence;
- topic continuity;
- cultural/social policy;
- uncertainty and sensitivity.

### 15.3 Response goal families

```text
answer
acknowledge_specific_claim
acknowledge_state_change
console
congratulate
warn
clarify
learn
qualify
challenge
confirm_action
report_result
remain_silent
follow_explicit_response_policy
```

Console is not triggered by the word “died.” It is a candidate when:

- the death meaning is selected;
- the event is epistemically usable;
- harmful impact is likely;
- the user has a meaningful relation or emotional stance;
- the channel and conversation support it.

### 15.4 Silence

Silence/no-output is a valid selected response goal when:

- no authorized useful content exists;
- another response would be repetitive or socially harmful;
- an explicit policy requests silence;
- the system cannot realize meaning safely.

### 15.5 Explicit programmed response

A user or application may install a scoped `ResponsePolicySchema`:

```text
when semantic pattern P
and context constraints C
select response goal G
optionally require literal surface L
```

A literal phrase is an explicit external policy, not proof that CEMM understood it. The emission trace must mark the policy source and semantic trigger.

---

## 16. Goals, operations, and self

### 16.1 Goal generation

Goals derive from:

- discourse acts;
- queries;
- claims;
- state transitions;
- learning frontiers;
- impact and importance;
- obligations;
- self/user goals;
- operation outcomes;
- response policies.

### 16.2 Operations

An operation implements an action schema under capability, permission, resource, and risk constraints.

### 16.3 Self model

Self is a referent whose knowledge view is constructed from:

- configured identity;
- active semantic types;
- built-in functions;
- runtime adapters;
- live capabilities;
- permissions;
- operational states;
- memory state;
- language competence;
- current goals;
- limitations.

Self claims are generated from this view, never from marketing prose.

---

## 17. Multilingual understanding and realization

Meaning schemas contain no language surfaces.

A language package contains:

- lexeme forms and senses;
- morphology;
- syntactic evidence;
- argument realization frames;
- reference paradigms;
- linearization;
- discourse markers;
- genuine idioms;
- semantic round-trip tests.

A surface form activates possible schemas/operators. It never creates selected meaning.

Response generation proceeds:

```text
Response UOL
→ semantic aggregation
→ deep clause plan
→ language argument frames
→ syntax
→ reference realization
→ agreement/morphology
→ linearization
→ semantic verification
```

Adding a new action must not require a full sentence template.

---

## 18. Authority boundaries

| Decision | Sole authority |
|---|---|
| language hypotheses | LanguageDetectionCoordinator |
| form alternatives | LanguageAnalysis/Fusion |
| referent candidates | ReferentResolver |
| type/facet closure | ReferentKnowledgeProjector |
| schema lifecycle | SemanticSchemaStore |
| UOL composition | MeaningComposer |
| selected meaning | MeaningBundleSelector |
| discourse/claim classification | DiscourseActCoordinator |
| epistemic status | EpistemicCoordinator |
| learning frontier | LearningCoordinator |
| state/effect preview | TransitionCoordinator |
| impact/importance | SignificanceCoordinator |
| active goals | GoalArbiter |
| executable plan | OperationPlanner/Authorizer |
| response goals | ResponseGoalCoordinator |
| response UOL | ResponseMeaningPlanner |
| target-language surface | NLGCoordinator |
| emission authorization | EmissionGate |
| durable mutation | GraphPatchCommitCoordinator |

No component may create a downstream authority's artifact as a convenience fallback.

---

## 19. Non-regression laws

1. New semantic types are data, not enum additions.
2. No word directly selects a proposition.
3. No event uses custom state mutation code when a transition contract can express it.
4. No “negative” flag conflates polarity, loss, deactivation, valence, or prohibition.
5. Default state is never active fact without admission.
6. Claims are never stored as facts merely because they are grammatical.
7. Event effects are context- and time-qualified.
8. Capabilities are recomputed from dependencies; they are not deleted.
9. Importance is stakeholder-relative and evidence-bearing.
10. Response policy operates on semantics, not transcript strings.
11. Learning data enters ordinary indexes and survives restart.
12. Output meaning is stored and referable.
13. Acknowledgements bind explicit targets.
14. NLG cannot invent semantic content.
15. Every release claim distinguishes specified, implemented, wired, authoritative, and verified.
