# CEMM v3.5 Meaning-Substrate Architecture

**Status:** proposed replacement architecture  
**Baseline reviewed:** `robosys-labs/cemm` commit `855e17d57129bb8a7a601bf7077994c1971e736d` (`Make 347 functional`)  
**Version decision:** this is a breaking semantic/data redesign and should be called **v3.5**, not v3.4.8  
**Primary objective:** a bounded multilingual baby CEMM that composes meaning from reusable atoms, learns grounded additions, answers from its actual semantic state, and never relies on whole-sentence routing or one-template-per-predicate generation.

---

## 1. Executive decision

v3.4.7 established several necessary foundations:

- one canonical identity-bearing object family, `Referent`;
- predicate-local ports;
- temporary UOL graphs;
- GraphPatch-only durable mutation;
- bounded inference and lifecycle records;
- response goals and emission proofs.

Those foundations should be retained.

The failure is deeper than a missing vocabulary list. The executable meaning substrate is still effectively:

```text
surface form
→ lexical entry pointing at a predicate
→ predicate activation
→ cartesian port binding
→ per-predicate response template
```

That architecture becomes more convincing as data is added, but it does not become fundamentally more intelligent. It makes “how” a shortcut to `has_state`, “do” a shortcut to `capable_of`, and “can” another surface for the same predicate. It cannot independently represent the interrogative, modal, pro-action, participant, property, aspect, and discourse contributions that combine to form the meaning of “what can you do?”

v3.5 must replace the center of gravity with:

```text
multimodal form evidence
→ candidate meaning atoms and referents
→ referent operational profiles
→ generic semantic composition algebra
→ selected UOL meaning bundle
→ epistemic/action/learning obligations
→ semantic response transforms
→ deep language-neutral clause plan
→ language grammar and morphology
→ surface realization
```

The central law is:

> No language form, template, parser result, or special response label may substitute for a compositional meaning graph.

---

## 2. What was structurally wrong in v3.4.7

### 2.1 A predicate catalogue was mistaken for a meaning substrate

The foundation contains referents, predicate schemas, operations, rules, and assertions, but it has no executable model of what kinds of properties, states, actions, and relations are naturally available to a referent type.

A `software_agent` does not currently inherit a data-defined profile saying that it may:

- possess a name;
- have operational and availability states;
- observe information;
- read, write, retrieve, learn, reason, answer, remember, and communicate;
- conditionally obey a command;
- lack physical movement unless an adapter supplies it.

Without this profile, compatibility is evaluated only from the active predicate’s local port. The system knows what a predicate permits, but not what the candidate referent itself can meaningfully possess, undergo, observe, or do.

### 2.2 Lexemes directly activate completed predicates

A word should normally contribute a lexical sense or operator, not a completed proposition.

Examples:

```text
what  → query operator and typed answer variable
can   → ability modality
you   → discourse participant referent
do    → pro-action/light-action operator
name  → name property atom
is    → copular realization/semantic linking evidence
how   → manner/state-quality interrogative operator
```

They must not be encoded as:

```text
how → predicate:has_state + fixed operational-status dimension
do  → predicate:capable_of
can → predicate:capable_of
```

The latter design cannot preserve the distinct semantic work performed by each word.

### 2.3 Operational ports are only half implemented

Predicate-owned ports are correct, but they are not enough.

The runtime needs two compatible projections:

1. **Atom-local ports**: the participant/value/content positions defined by an action, relation, property, state, or operator.
2. **Referent operational profile**: the properties, state dimensions, roles, acceptable actions, live capabilities, permissions, and multimodal conditions available to a candidate referent.

A binding is valid only when both sides agree.

### 2.4 The current UOL graph is too predication-centric

The current graph can hold referents and predications, but it lacks first-class compositional operators for:

- query variables and answer projections;
- modality and modal scope;
- tense and aspect;
- quantification;
- degree and comparison;
- pro-actions and ellipsis;
- property access and assignment;
- coordination with shared arguments;
- relative clauses and restrictive modifiers;
- discourse acts with bound targets;
- viewpoint and perspective.

These are not language-only details. They are language-independent meaning contributions.

### 2.5 NLG is still sentence-template enumeration

A dictionary such as:

```text
named      → "My name is {name}."
has_state  → "My {dimension} is {value}."
capable_of → "I can perform {operation}."
```

requires a new template for every combination of:

- predicate;
- participant perspective;
- tense/aspect;
- modality;
- polarity;
- question/declarative form;
- information structure;
- coordination;
- tone;
- language.

That growth is multiplicative. It is not a multilingual NLG algebra.

### 2.6 Output meaning is not a full discourse participant

A system response must be committed as semantic discourse content, not only as an emission ledger and surface hash. Otherwise later utterances such as:

- “for what?”
- “understood what?”
- “why?”
- “that is wrong”
- “do the second one”

cannot refer to the system’s prior response meaning.

### 2.7 Generic acknowledgement is epistemically unsafe

“Understood” is not a harmless filler. It asserts an understanding state and requires a target.

The system may emit an understanding acknowledgement only when it has:

- a target proposition or operation;
- a selected meaning bundle for that target;
- a successful understanding assessment;
- an explicit acknowledgement predication bound to the target.

A storage acknowledgement should say what happened semantically, such as:

```text
stored(property:name(user, Chibu))
```

and can be realized as “I’ve stored that your name is Chibu.”

---

## 3. Canonical architecture layers

v3.5 has six non-substitutable layers.

### 3.1 Observation and form evidence

```text
ObservationEnvelope
EvidenceAtom
Token/MorphemeCandidate
LexemeSenseCandidate
MentionCandidate
FormRelationCandidate
FormLattice
MultimodalTrackCandidate
```

This layer records what analyzers proposed. It contains surfaces and source alignment. It does not contain selected meaning.

### 3.2 Meaning-atom schemas

A **MeaningAtomSchema** is the common executable root for foundational semantic primitives.

```text
MeaningAtomSchema
  atom_ref
  atom_class
  semantic_key
  parent_atom_refs
  local_ports
  constraints
  composition_behaviors
  inferential_behaviors
  operational_behaviors
  language_neutral_realization_features
  lifecycle/provenance
```

Required atom classes:

```text
REFERENT_TYPE
PROPERTY
STATE_DIMENSION
STATE_VALUE
ACTION
RELATION
ROLE
UNIT
MODAL_OPERATOR
QUERY_OPERATOR
QUANTIFIER_OPERATOR
POLARITY_OPERATOR
TEMPORAL_OPERATOR
ASPECT_OPERATOR
COMPARISON_OPERATOR
COORDINATION_OPERATOR
REFERENCE_OPERATOR
DISCOURSE_ACT
DISCOURSE_RELATION
CONTROL_OPERATOR
```

Specialized records may expose strongly typed fields, but all participate in one activation, inheritance, port, lifecycle, dependency, and indexing model.

### 3.3 Referents and operational profiles

A `Referent` remains the single identity-bearing semantic object family.

A **ReferentOperationalProfile** is a cycle-pinned projection:

```text
ReferentOperationalProfile
  referent_ref
  active_type_closure
  inherent_property_atoms
  admissible_state_dimensions
  current_state_refs
  role_occupancy_refs
  afforded_action_atoms
  live_capability_refs
  permission_refs
  resource_constraints
  multimodal_state_refs
  context_ref
  valid_time_ref
  dependency_fingerprint
```

The profile is derived from:

- the referent’s type closure;
- inherited type-profile declarations;
- explicit properties and roles;
- live state and multimodal observations;
- capability adapters;
- permissions and resources;
- context and time.

It is not independently persisted as truth. It is a pinned derived view.

### 3.4 UOL v2 semantic records

```text
Referent
AtomApplication
PortBinding
SemanticVariable
ScopeLink
CoordinationGroup
PropositionReferent
DiscourseAct
DiscourseRelation
UOLGraph
MeaningHypothesis
MeaningBundle
```

`AtomApplication` replaces the assumption that all meaning is a flat predicate.

It can instantiate:

- a property: `property:name(holder=user, value=Chibu)`;
- a state: `state:operational_status(holder=self, value=available)`;
- an action: `action:read(actor=self, content=?content)`;
- a relation: `relation:located_at(subject=x, place=y)`;
- an operator: `operator:ability(scope=event-or-action, experiencer=self)`;
- a query: `operator:query(variable=?action, restriction=...)`;
- a discourse act: `discourse:ask(speaker=user, addressee=self, content=...)`.

### 3.5 Knowledge and control

```text
KnowledgeRecord
TruthAssessment
LearningTransaction
SchemaRevision
RuleRevision
GraphPatch
GoalRecord
OperationPlan
AuthorizationRecord
ResponseGoal
EmissionProof
```

These records point to semantic content. They do not recreate it.

### 3.6 Language realization

```text
DeepClausePlan
SyntacticFeatureGraph
LexemeSelection
MorphologicalWord
LinearizationPlan
SurfaceUtterance
RoundTripSemanticAssessment
```

Language realization operates only after response UOL exists.

---

## 4. Referent-type profiles

A data-driven type profile replaces scattered type checks.

### 4.1 Profile structure

```text
ReferentTypeProfile
  type_ref
  parent_type_refs
  identity_facets
  inherent_property_refs
  admissible_state_dimension_refs
  afforded_action_refs
  admissible_role_refs
  observation_channel_refs
  participant_constraints
  defaults
  prohibitions
```

### 4.2 Example: software agent

```text
type:software_agent
parents:
  - type:agent
  - type:digital_object

inherent properties:
  - property:name
  - property:type
  - property:version
  - property:location
  - property:capability_set

state dimensions:
  - state:operational_status
  - state:availability
  - state:connectivity
  - state:memory_status
  - state:conversational_tone

afforded actions:
  - action:observe
  - action:read
  - action:write
  - action:retrieve
  - action:learn
  - action:reason
  - action:remember
  - action:answer
  - action:ask
  - action:communicate
  - action:obey

prohibitions/default absences:
  - action:physical_move unless a physical embodiment capability is active
  - action:see unless a vision adapter is active
  - action:hear unless an audio adapter is active
```

### 4.3 Example: self

`referent:self` is a distinguished referent instance, not a language shortcut.

```text
referent:self
types:
  - type:software_agent
  - type:agent

identity:
  self_anchor = runtime_instance

properties:
  property:name = CEMM
  property:version = current runtime version

live states:
  state:operational_status = running
  state:availability = available

live capabilities:
  derived from built-in operations and registered adapters
```

The word “you” resolves to `referent:self` only because the current discourse participant frame identifies self as the addressee, not because the English lexicon permanently equates “you” with CEMM.

---

## 5. Properties, states, actions, and relations

### 5.1 Property atoms

A property atom is itself predicative.

```text
property:name
ports:
  holder: Referent
  value: Name/Text Referent
constraints:
  usually_single_valued: true
  identity_contribution: true
  alias_generation: value → holder
  queryable_ports: [value]
```

This removes the need for a separate `named` predicate plus special alias metadata.

Other seed properties:

```text
property:type
property:meaning
property:version
property:age
property:location
property:role
property:capability_set
property:owner
property:part_whole
```

A property can declare whether it is:

- identity-contributing;
- single- or multi-valued;
- persistent or transient;
- directly observable;
- inferable;
- sensitive;
- temporally scoped.

### 5.2 State atoms

A state dimension is predicative and time-aware.

```text
state:operational_status
ports:
  holder
  value
  valid_time
value_domain:
  running
  degraded
  unavailable
```

The state value is not duplicated inside a `StatePayload` and a predication. The reified state referent points to the defining atom application.

### 5.3 Action atoms

```text
action:read
ports:
  actor
  content
  source?
  result?
preconditions:
  actor has capability read
effects:
  actor may gain attended/accessible content
```

The action atom is semantic. An `OperationSchema` is the executable implementation contract that may realize the action through code or an adapter.

### 5.4 Relation atoms

Relations include:

```text
relation:same_as
relation:part_of
relation:member_of
relation:located_at
relation:inside
relation:before
relation:after
relation:causes
relation:enables
relation:prevents
relation:refers_to
relation:spouse_of
```

Their symmetry, inverse, transitivity, temporal behavior, and sensitivity are schema data.

---

## 6. Affordance, capability, permission, competence, intention

These terms must not be collapsed.

### 6.1 Affordance

An affordance says an action is structurally meaningful for a type or referent.

```text
affords(type:software_agent, action:read)
```

It does not prove the current runtime can perform it.

### 6.2 Capability

A capability says a specific referent can currently perform an action under declared conditions.

```text
capability(
  holder=self,
  action=read,
  status=available,
  conditions=[content_accessible],
  evidence=[runtime_adapter:reader]
)
```

### 6.3 Permission

Permission says execution is authorized in a context.

```text
permitted(self, write, destination=session_memory)
```

### 6.4 Competence

Competence describes reliability or quality.

```text
competence(self, translate, language=fr, score=0.82)
```

### 6.5 Intention and commitment

“Will” and “intend” concern future commitment, not current ability.

```text
intends(self, action)
committed_to(self, action)
```

### 6.6 Operational availability

An action is executable only when:

```text
afforded
∧ capable now
∧ permitted
∧ resources available
∧ required ports grounded
∧ risk accepted
```

The answer to “what can you do?” should normally query the live `capability` view, while “what kinds of things can software agents do?” may query inherited affordances.

---

## 7. Meaning operators

### 7.1 Query

```text
operator:query
ports:
  variable
  restriction
  projection
  expected_answer_type
```

### 7.2 Ability

```text
operator:ability
ports:
  holder
  action_or_event
  conditions?
```

### 7.3 Pro-action

```text
operator:pro_action
ports:
  action_variable
```

This is the semantic contribution of light/pro verbs such as English “do” when the actual action is open.

### 7.4 Negation

Negation is an operator with explicit scope.

### 7.5 Tense and aspect

Operators include:

```text
temporal:past
temporal:present
temporal:future
aspect:ongoing
aspect:completed
aspect:habitual
aspect:still
```

### 7.6 Coordination

Coordination is represented as a group with:

- member semantic refs;
- coordinator type;
- shared arguments;
- distributive/collective interpretation;
- scope.

### 7.7 Discourse acts

```text
discourse:greet
discourse:ask
discourse:assert
discourse:direct
discourse:acknowledge
discourse:correct
discourse:confirm
discourse:refuse
discourse:clarify
```

Every acknowledgement binds a target.

---

## 8. Correct interpretation of “what can you do?”

The form evidence contributes:

```text
what → QUERY variable ?action, expected type ACTION
can  → ABILITY operator
you  → addressee participant → referent:self
do   → PRO_ACTION with open action variable
?     → interrogative force
```

The selected UOL should be equivalent to:

```text
DiscourseAct(
  atom = discourse:ask,
  speaker = referent:user,
  addressee = referent:self,
  content = Query(
    variable = ?action: ACTION,
    restriction = Ability(
      holder = referent:self,
      action_or_event = ?action
    ),
    projection = ?action
  )
)
```

Candidate meaning is strengthened by:

- `referent:self` has an operational profile containing action affordances;
- the ability operator accepts an agent and action;
- the pro-action contributes an open action variable;
- “what” expects an action-like answer because of the pro-action restriction;
- the utterance is interrogative.

No word directly activates a completed `capable_of` proposition.

Retrieval returns action atom references, such as:

```text
action:read
action:write
action:learn
action:reason
action:remember
action:answer
action:obey
```

Each result is filtered through live capability, permission, resource, and risk state.

---

## 9. Correct interpretation of property assertions and queries

### 9.1 “My name is Chibu”

```text
my    → possessor/holder = referent:user
name  → property:name
is    → property-value linking/copying evidence
Chibu → provisional name/text referent, constrained by property:name.value
```

Selected meaning:

```text
property:name(
  holder = referent:user,
  value = referent:name:Chibu
)
```

The unknown name does not require teaching a new concept. The property port supplies the type constraint needed to create a grounded name referent.

Admission:

- stores the property proposition;
- supersedes any prior single-valued name in the same scope/time;
- creates aliases from `Chibu` to `referent:user`;
- records source and evidence.

### 9.2 “What is my name?”

```text
Query(
  variable = ?name: NAME,
  restriction = property:name(holder=user, value=?name),
  projection = ?name
)
```

Retrieval closes `?name` with the stored referent.

---

## 10. Correct interpretation of “how are you?”

The system should preserve at least two candidates:

### Candidate A: state-summary question

```text
Query(
  variable = ?state_summary,
  restriction = summarize_current_state(holder=self),
  projection = ?state_summary
)
```

### Candidate B: rapport/wellbeing discourse act

```text
discourse:ask_wellbeing(speaker=user, target=self)
```

The candidate ranking can use:

- greeting context;
- conversational convention;
- self type;
- available state dimensions;
- current topic;
- whether the user asked a specific state dimension.

The response must be generated from live self state, for example:

```text
state:operational_status(self, running)
state:availability(self, available)
```

Possible realization:

```text
“I’m operational and available.”
```

The system must not fabricate human emotion.

---

## 11. Output discourse and grounded acknowledgement

The system must commit both user and system semantic turns.

```text
DiscourseTurn
  speaker_ref
  addressee_refs
  discourse_act_ref
  content_proposition_refs
  response_goal_ref
  emitted_uol_ref
  surface_ref
  common_ground_status
```

### 11.1 “Understood”

Allowed only when the response UOL contains:

```text
discourse:acknowledge(
  speaker=self,
  addressee=user,
  target=<specific proposition or operation>,
  acknowledgement_kind=understanding
)
```

and `understands(self, target)` is supported.

### 11.2 “Understood what?”

The query operator opens the acknowledgement target/content port and resolves the prior system acknowledgement from discourse.

### 11.3 “For what?”

This is an elliptical query. Candidate targets include the prior response’s:

- reason;
- purpose;
- content target;
- limitation target;
- requested action.

The output semantic graph, not the surface transcript alone, provides the answer.

---

## 12. Learning architecture

Learning must operate on atom schemas and profiles.

### 12.1 Learnable contributions

```text
new lexical sense
new alias
new referent identity
new referent type
new property
new state dimension/value
new action
new relation
new affordance
new capability condition
new rule
new grammar realization
```

### 12.2 Grounding frontier

Every learned item must connect to known meaning through:

- parent atom refs;
- port type constraints;
- known referent anchors;
- known state/action/property classes;
- evidence and source;
- scope and valid time.

### 12.3 Unknown words in known positions

If the system receives:

```text
“My glorp is blue.”
```

and `glorp` occupies the property position, it may ask:

```text
“Does ‘glorp’ name a property of you?”
```

It should not ask a generic clarification.

### 12.4 Lifecycle

```text
candidate
→ structurally complete
→ provisionally usable in source-attributed context
→ competence-tested
→ active
```

Learned language mappings enter the ordinary analyzer. Learned atoms enter the ordinary atom index. No session shadow interpreter is permitted.

---

## 13. Architectural invariants

1. `Referent` remains the only identity-bearing semantic filler family.
2. `MeaningAtomSchema` is the only root executable meaning-schema family.
3. No surface form points directly to a selected proposition.
4. No language pack may contain per-predicate sentence answers as the primary realization method.
5. Idiom templates are allowed only for genuinely non-compositional forms.
6. Referent operational profiles and atom-local ports must both authorize binding.
7. `can`, `will`, `must`, negation, query, tense, and aspect remain scoped operators.
8. Output UOL is committed to discourse and can be referred to later.
9. Acknowledgements bind explicit targets.
10. Capability answers are derived from live capability state, not marketing text or seeded prose.
11. Unknown words preserve partial meaning and produce typed repair questions.
12. NLG may realize only selected response UOL.
13. Every semantic rewrite and realization rule is proof-carrying.
14. Cross-language equivalence is tested at UOL, not surface-string level.
15. Legacy `predicate_answers` and generic `response_moves` must be physically removed from the canonical path.

---

## 14. Minimum baby-CEMM foundation

The first useful foundation should seed approximately:

| Family | Target |
|---|---:|
| broad referent types | 20–30 |
| properties | 20–30 |
| state dimensions and values | 25–40 |
| actions | 35–50 |
| relations | 25–35 |
| modal/query/temporal/aspect operators | 20–30 |
| discourse acts/relations | 12–20 |
| units and measure dimensions | 20–30 |
| self capabilities | 15–25 |
| generic inference/affordance rules | 50–100 |

The goal is not vocabulary volume. The goal is sufficient compositional closure for:

- identity and naming;
- state and property queries;
- action/capability queries;
- simple directives;
- assertion/correction;
- reference to prior propositions;
- coordination;
- negation/modality;
- grounded learning;
- multilingual generation.

---

## 15. Release definition

v3.5 is complete only when:

- the required conversation regression passes without whole-sentence patterns;
- English, French, and Swahili inputs produce equivalent selected UOL for shared tests;
- responses are generated through grammar and morphology rules rather than per-predicate sentences;
- property learning and retrieval work after restart;
- prior system output can be referenced semantically;
- generic clarification is not selected when a typed repair question can be generated;
- “what can you do?” returns live action capabilities;
- the system never emits “Understood” without a grounded target;
- legacy template and predicate-shortcut paths are unreachable and deleted.
