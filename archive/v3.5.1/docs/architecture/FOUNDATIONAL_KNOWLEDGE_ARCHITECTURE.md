# CEMM v3.5 Foundational Knowledge and Referent Architecture

**Status:** canonical supporting contract  
**Purpose:** define the minimum knowledge substrate that makes CEMM learnable from the ground up.

---

## 1. Foundational principle

CEMM does not begin with a large catalogue of world facts. It begins with a small set of structural concepts that let it learn what kinds of things exist, what may be known about them, how they change, and how claims about them are evaluated.

The foundation must be:

- language-neutral;
- domain-light;
- recursively teachable;
- capable of representing incomplete definitions;
- executable through typed ports and rules;
- safe under contradiction and uncertainty;
- suitable for multimodal state;
- extensible without source-code ontology edits.

---

## 2. The three layers of referent knowledge

### 2.1 Identity layer

Answers:

```text
What referent is this?
Is it the same as another referent?
What anchors its identity?
When and where does this identity apply?
```

Records include:

```text
Referent
IdentityFacet
IdentityAssessment
Alias
Anchor
MergeProposal
SplitProposal
```

### 2.2 Type and entitlement layer

Answers:

```text
What semantic types apply?
What facets are meaningful for this referent?
What properties, states, actions, roles, or capabilities are allowed?
```

Records include:

```text
ReferentTypeAssertion
ReferentTypeSchema
FacetSchema
FacetEntitlement
AffordanceRule
FunctionSchema
CapabilityDependency
```

### 2.3 Instance knowledge layer

Answers:

```text
What is currently or historically true of this referent?
What events affected it?
What claims exist?
What is known, disputed, defaulted, or unknown?
```

Records include:

```text
PropertyAssignment
StateAssignment
StateTimeline
RelationOccurrence
RoleOccupancy
EventOccurrence
ClaimRecord
KnowledgeRecord
CapabilityInstance
ImpactAssessment
ImportanceAssessment
```

---

## 3. Foundational type graph

Boot types should be broad and composable.

```text
referent
├── concrete
│   ├── physical_entity
│   │   ├── living_entity
│   │   │   ├── organism
│   │   │   └── biological_agent
│   │   └── artifact
│   ├── digital_entity
│   └── hybrid_entity
├── agent
│   ├── natural_agent
│   ├── software_agent
│   ├── collective_agent
│   └── institutional_agent
├── place
├── information_object
├── event_occurrence
├── state_occurrence
├── proposition
├── claim_information
├── quantity
├── unit
├── time
├── collection
├── context
└── schema_topic
```

This is a starting graph, not an exhaustive taxonomy. Multiple inheritance is expected.

`person`, `animal`, `server`, `bank`, `president`, `fox`, and `battery` are learned or separately seeded domain types under these anchors.

---

## 4. Universal facets

### 4.1 Identity facet

Applicable to every referent.

Possible knowledge:

```text
name
alias
identifier
same_as/different_from
origin anchor
identity confidence
```

### 4.2 Existence facet

Applicable to every referent, but interpreted by type/context.

```text
exists_in_context
created
destroyed
active identity interval
fictional/simulated status
```

A proposition “exists” as information without its content being true.

### 4.3 Temporal facet

Every referent can have a validity or reference interval.

- physical entities persist through time;
- events occur in time;
- states hold over intervals;
- propositions have validity time and claim time;
- schemas have revision intervals;
- places may have historical boundaries.

### 4.4 Localization facet

Localization is reference-frame specific.

```text
geospatial
physical containment
digital address/storage
network location
discourse position
conceptual/ontology location
temporal position
```

Not every referent is geospatially located.

### 4.5 Composition facet

```text
part_of
contains
member_of
component_of
material_of
body_of
representation_of
```

Composition rules define whether loss of a part affects identity, function, capability, or state.

### 4.6 Descriptive-property facet

Holds relatively stable values such as name, version, material, owner, or classification.

### 4.7 State facet

Holds time-indexed conditions.

### 4.8 Relation and role facets

Represent world relations and context/time-bound positions.

### 4.9 Event-participation facet

Records participation as actor, affected, experiencer, instrument, source, destination, beneficiary, cause, or result according to event-local ports.

### 4.10 Action/capability facet

Available where type profiles license actions or dispositions.

### 4.11 Function/purpose facet

Represents intended or selected contribution.

### 4.12 Epistemic facet

Applicable to information-bearing referents and agents:

```text
known_by
believed_by
reported_by
supported_by
opposed_by
sensitive_to
```

### 4.13 Significance facet

Contextual assessments of value, importance, urgency, risk, or impact.

---

## 5. Entitlement inheritance

### 5.1 Entitlement modes

```text
required
optional
conditional
prohibited
inherited_only
```

### 5.2 Inheritance policies

```text
inherit
override
narrow_domain
extend_domain
block
compose
```

### 5.3 Example

```text
physical_entity
  entails optional geospatial_location
  entails optional mass
  affords externally_caused_move

living_entity
  requires life_status
  entails biological_process facet
  conditionally affords growth

animal
  conditionally affords self_initiated_locomotion
  conditionally entails affective_state

software_agent
  entails operational_status
  entails digital_location
  conditionally affords read/write/reason
```

A specific type can narrow or block inherited entitlements.

---

## 6. State model

### 6.1 State dimension schema

```text
StateDimensionSchema
  dimension_ref
  holder_type_constraints
  value_domain
  cardinality
  exclusivity
  scale/order
  persistence
  observation_channels
  transition_rules
  default_rules
  applicability_rules
```

### 6.2 State assignment

```text
StateAssignment
  holder_ref
  dimension_ref
  value_ref
  context_ref
  valid_from
  valid_to
  status
  confidence
  evidence_refs
  proof_refs
```

### 6.3 State timeline

A timeline is a derived ordered set of assignments and deltas. It must tolerate:

- unknown gaps;
- overlapping claims;
- contradiction;
- retrospective correction;
- future/planned state;
- context-specific state.

### 6.4 Default state

A default is represented as a rule:

```text
if type/conditions
then expected state
unless defeater
```

It is not inserted as an active assignment.

### 6.5 Latent state

A latent state means the dimension or disposition applies but has no active current value or activation condition.

---

## 7. Capability and function graph

### 7.1 Action affordance

Type-level possibility.

### 7.2 Capability instance

Referent-level current availability.

### 7.3 Dependencies

Capabilities may depend on:

- life status;
- operational status;
- resources;
- components;
- connectivity;
- permission;
- location;
- knowledge;
- other capabilities.

### 7.4 Capability propagation

A state delta causes dependency reevaluation:

```text
state_delta
→ affected dependency index
→ recompute capability instances
→ emit capability deltas
→ invalidate operation plans
```

### 7.5 Function and failure

Function persists as design or role semantics even when capability is blocked.

---

## 8. Event knowledge architecture

### 8.1 Event schema

```text
EventSchema
  parent_event_refs
  participant_ports
  temporal profile
  occurrence constraints
  transition contracts
  result contracts
  causal contracts
  impact contracts
  persistence/reversibility
  lexical sense refs
```

### 8.2 Event occurrence status

```text
mentioned
claimed
reported
observed
planned
attempted
ongoing
completed
failed
prevented
hypothetical
counterfactual
```

### 8.3 Event causality

A cause is not inferred from sequence alone. Causal warrants include:

```text
constitutive mechanism
observed intervention
learned causal rule
reported cause
statistical evidence
assumption
```

### 8.4 Event result versus effect

- **result** is an event-local semantic output;
- **effect** is a state/relation/capability change derived through a transition contract;
- **impact** is a stakeholder-relative evaluation of those changes.

---

## 9. Claim knowledge architecture

### 9.1 Claim layers

```text
surface observation
discourse claim act
proposition content
claim record
evidence record
CEMM epistemic stance
```

### 9.2 Claim commitment

```text
asserted
suggested
speculated
quoted
denied
corrected
retracted
```

### 9.3 Source model

Source identity, authority, reliability, access, and possible bias are separate from proposition content.

### 9.4 Claim conflict

CEMM can hold multiple claims about the same proposition signature without deleting them. Truth assessment aggregates admissible support and opposition.

---

## 10. Native gain/loss architecture

### 10.1 Possession/status change

`gain` and `loss` are transition operators over a facet or relation.

```text
Loss
  holder/affected
  lost_content
  facet_or_relation
  prior_status
  resulting_status
  time
```

### 10.2 Scalar decrease

A decrease is not necessarily a loss of possession.

```text
temperature decreased
battery charge decreased
importance decreased
```

### 10.3 Capability deactivation

A capability can become unavailable without being erased.

### 10.4 Evaluative consequence

A loss can be beneficial, harmful, mixed, or unknown to different stakeholders.

### 10.5 Example: tail loss

```text
event:lose_body_part(fox, tail)
→ relation part_of(tail, fox) ends
→ body_integrity state changes
→ balance/mobility capability may degrade through learned dependency
→ impact assessment depends on severity and stakeholder
```

No custom fox-tail code is permitted.

---

## 11. Importance and value architecture

### 11.1 Two meanings of value

CEMM distinguishes:

1. **semantic value** — a filler such as a quantity, state value, name, or symbol;
2. **evaluative value** — worth or desirability relative to a stakeholder or goal.

### 11.2 Importance sources

```text
explicit importance claim
active goal dependency
ownership/kinship/responsibility
high impact
irreversibility
rarity/uniqueness
mention/focus history
emotional evidence
risk
normative priority
```

### 11.3 Importance decay and persistence

Some importance is momentary discourse salience; some is durable user preference. They must not share one score or retention policy.

---

## 12. Learning package architecture

### 12.1 Package types

```text
ReferentLearningPackage
TypeLearningPackage
PropertyLearningPackage
StateLearningPackage
Action/EventLearningPackage
Relation/RoleLearningPackage
RuleLearningPackage
LexicalLearningPackage
RealizationLearningPackage
ResponsePolicyLearningPackage
```

### 12.2 Package dependencies

Every package declares exact dependencies and unresolved frontier nodes.

### 12.3 Example and counterexample store

Examples are evidence for competence and induction. They do not become definitions automatically.

### 12.4 Schema use profiles

```text
mention_use
grounding_use
composition_use
query_use
inference_use
transition_use
impact_use
operation_use
realization_use
```

A partially learned schema can support some uses and be denied others.

---

## 13. Minimal seed knowledge

### 13.1 Semantic axes

Seed the native axes from the architecture.

### 13.2 Core type anchors

Seed only broad types needed for entitlement inheritance.

### 13.3 Core facets

Seed universal facets and validation contracts.

### 13.4 Core state dimensions

```text
existence_status
life_status
operational_status
availability
location
time_status
resource_level
capability_status
truth_status
common_ground_status
importance
valence
```

`emotion`, `health`, `connectivity`, and similar dimensions are seeded where needed for initial competence, but applicability remains type-driven.

### 13.5 Core event/change schemas

```text
start
stop
gain
lose
increase
decrease
activate
deactivate
create
destroy
move
communicate
observe
claim
correct
learn
```

Biological death may be a carefully seeded event schema or an early learned competence package. It must use the generic transition architecture either way.

---

## 14. Foundational competence tests

The foundation is acceptable only if it can represent and reason about:

- a referent with unknown but applicable state;
- a prohibited facet;
- a default state without materializing it;
- a state transition;
- a capability disabled by a state change;
- a function retained during failure;
- a claim not accepted as fact;
- an event reported in a fictional context;
- a loss with mixed stakeholder valence;
- a learned type with inherited facets;
- a learned event with transition effects;
- correction and dependent invalidation.
