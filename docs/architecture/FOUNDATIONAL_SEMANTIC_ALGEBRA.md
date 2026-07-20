# CEMM v3.5 Foundational Semantic Algebra

This document defines the irreducible semantic substrate beneath UOL, language learning, query binding, referent knowledge, transition reasoning, and response generation. `ARCHITECTURE.md` remains the governing system contract.

# 1. Irreducibility criterion

A concept belongs in the stable kernel only when removing it would make a whole class of meanings structurally inexpressible or would require incompatible validation/execution semantics.

A concept does **not** become a kernel primitive merely because it is common, linguistically basic, or useful in early conversation.

Use four authority layers:

```text
A. kernel structural machinery
B. reviewed foundational semantic axes
C. learned/domain semantic concepts
D. language/grammar authority
```

Examples:

```text
SemanticVariable       -> kernel structural machinery
degree/order           -> foundational semantic axis
connectivity            -> entitlement-scoped state dimension
manner                  -> eventuality characterization projection
method                  -> composed means/procedure/causal structure
adjective/adverb        -> language/grammar category
```

This prevents the foundation from becoming either too weak or a hard-coded dictionary of human vocabulary.

# 2. Native semantic basis

## 2.1 Kernel structural primitives

The kernel must natively execute these structural families:

```text
Referent / identity
semantic type / inheritance
SemanticApplication
SemanticVariable
port / filler / binding
property
state dimension / state value
relation
role
eventuality representation
action/control
event occurrence
quantity / measure / unit
time
place / localization
operator / scope
proposition / claim / evidence / knowledge
query / information-gap mechanics
coordination
capability / affordance / disposition / function
transition / delta / dependency
context / permission / provenance / lifecycle
goal / operation / Response UOL
learning frontier / competence / promotion / invalidation
```

Only stable structural discriminators may become Python enums/classes.

## 2.2 Reviewed foundational semantic axes

The boot semantic substrate should contain a small, revisioned, language-neutral set of cross-domain axes such as:

```text
identity / sameness / difference
classification / membership
existence
applicability / activation
persistence / change
polarity
modality
occurrence / aspect
temporal relation
localization
quantity / measure / ordering / degree
cause / enable / prevent
agency / control / affectedness
containment / mereology / possession
capability status
epistemic status / source
query answer projections
uncertainty / default expectation
reversibility
valence / significance
```

These are data authority. Kernel code must not inspect their English names to decide semantics.

## 2.3 Learned semantic concepts

Open-ended concepts remain data and may be introduced without source changes: specific object types, emotions, diseases, procedures, institutions, social conventions, domain actions, state dimensions, state values, and relations.

## 2.4 Language/grammar authority

Forms, morphemes, lexemes, allomorphs, lexical categories, agreement, tense/aspect/case, constructions, semantic-contribution specs, morphology, and linearization belong to language packages.

Grammar constrains semantics. It does not define world truth.

# 3. Semantic Contribution and Meaning Closure

A recognized unit need not independently denote a complete semantic application.

The smallest cognitive unit is a **SemanticContribution**: an evidence-backed constraint on a candidate meaning graph.

Contribution mechanics are structural:

```text
TARGET
  proposes a semantic schema/structural target

REFERENTIAL
  requires or constrains a discourse/referent role

VARIABLE
  introduces an open semantic binding

RESTRICTION
  narrows what can satisfy an open binding

PROJECTION
  specifies what aspect of a matched structure is sought

SCOPE
  constrains logical/modal/temporal/discourse scope

ARGUMENT
  connects grammatical roles/slots to semantic ports

GRAMMATICAL_FEATURE
  preserves tense/aspect/agreement/case/number/etc. as language evidence

CONSTRUCTION
  activates reusable composition structure
```

A token may emit multiple contributions. A contribution is not automatically a proposition, discourse act, response obligation, event occurrence, or fact.

## 3.1 Meaning Closure Law

Partial meaning is valid cognition.

A partial meaning must preserve what is known and what remains open through:

```text
expected filler classes
expected schema classes
expected referent types
restriction refs
answer projection
open-binding purpose
scope/time/context
evidence/lineage
```

Meaning closes only through compatible composition of lexical contributions, construction constraints, participant/discourse anchors, referent grounding, type/facet entitlements, state/capability knowledge, time/context, and epistemic authority.

## 3.2 Query Separation Law

Keep separate:

```text
information gap
semantic variable
restriction graph
answer projection
discourse act
response obligation
```

A WH-like lexical item may contribute an information gap/projection without creating a matrix `ask` act. Embedded interrogatives are the decisive counterexample.

# 4. Lexeme and form-family architecture

Direct `form -> sense` links are insufficient for a multilingual learning system.

The target architecture is:

```text
observed surface
→ LanguageForm candidate
→ Lexeme/form-family candidate
→ LexicalSense/meaning candidate
→ SemanticContributionSpec records
→ cycle-local SemanticContribution instances
```

## 4.1 LanguageForm

A form is an observed or realizable surface/morpheme identity.

It may carry surface features but does not own semantic meaning.

## 4.2 Lexeme

A lexeme groups forms that share lexical semantic authority.

Examples conceptually:

```text
BE:
  be
  am
  is
  are
  was
  were
  been
  being
```

The relation may be regular inflection, suppletion, cliticization or another reviewed form relation.

## 4.3 FormLexemeLink

A form→lexeme link carries grammatical evidence such as:

```text
tense=present
finite=true
person=2
number=plural-compatible
aspect=participle
```

The link is language data, not semantic truth.

## 4.4 LexemeSenseLink

A lexeme may have multiple senses.

Sense choice remains probabilistic/constraint-based and context-sensitive.

## 4.5 SemanticContributionSpec

A lexical sense may have zero, one or multiple contribution specifications.

A sense therefore need not be forced to one complete `target_ref`.

Legacy `form -> sense -> target` authority remains a bounded compatibility path until seed migration.

---

# 5. Qualitative meaning: property, state, process, degree, manner and method

These concepts are frequently confused and must remain orthogonal.

## 5.1 Property

A relatively stable or identity-descriptive semantic relation.

Examples:

```text
name
material
version
owner
color
```

Properties may still be time-qualified and corrected.

## 5.2 State

A time/context-indexed condition along a dimension.

```text
state_dimension(holder, value, interval, context)
```

Examples:

```text
operational_status
connectivity
availability
life_status
charge_status
```

Applicability is entitlement-based.

A state dimension is not universal merely because it is foundational.

## 5.3 Process/activity

A dynamic eventuality unfolding over an interval without requiring a terminal boundary.

Examples conceptually:

```text
running
thinking
charging
learning-in-progress
```

The architecture must represent this distinction even if the stable Python schema class remains `EventSchema` plus aspect/temporal profile.

## 5.4 Event/transition

An occurrence/change structure that may have boundaries/results and trigger transitions.

## 5.5 Action

An eventuality with control/intentionality semantics.

Action is not identical to event occurrence.

## 5.6 Manner

Manner is not a universal state.

It is a projection/modification relation over an eventuality:

```text
characterize_how(eventuality, ?description)
```

Possible answers can derive from many semantic families: speed, style, trajectory, care, instrument use, physical configuration, etc.

## 5.7 Degree

Degree is based on ordered/scalar structure.

```text
dimension(holder, ?value)
ordered_scale(dimension)
project(?value or range)
```

It supports comparison, intensity and measurement.

## 5.8 Method

Method is structured means/procedure knowledge:

```text
goal/result
+ action/process sequence
+ means/instruments/resources
+ enabling/causal relations
```

It is not a single irreducible enum.

---

# 6. Interrogatives and information gaps

Interrogative lexicalizations contribute typed information-gap constraints.

The semantic architecture must separate:

```text
information gap
semantic variable
restriction graph
answer projection
discourse act
response obligation
```

Examples of projection families, represented as data:

```text
WHO
  referent/identity projection

WHERE
  localization projection

WHEN
  temporal projection

WHY
  cause/reason/explanation projection

HOW
  candidate projections such as:
    qualitative condition
    manner
    scalar degree
    means/procedure

WHAT
  broad value/referent/schema/action projection constrained by construction
```

These are not direct word→intent mappings.

## 6.1 Example: `how are you`

A correct decomposition is approximately:

```text
HOW
  introduce/query ?answer
  candidate projection = qualitative/manner/degree/means
  target restriction still open

ARE / BE-family
  finite present grammatical evidence
  candidate structural uses:
    copular predication
    progressive auxiliary
    passive auxiliary
    existential structure

YOU
  referential requirement = discourse addressee
```

Grounding closes:

```text
addressee -> ParticipantFrame.input_addressee -> referent:self
```

Predicative structure plus `HOW` ranks a qualitative condition/state/property projection.

Stage-4 self knowledge exposes applicable facets/dimensions.

Stage 5 forms candidates such as supported current self-state descriptions.

Stage 10 binds current values.

Only matrix interrogative/discourse structure establishes `ask` and a response obligation.

No `"how are you"` phrase record is required.

## 6.2 Example: `what can you do`

Conceptually:

```text
WHAT
  ?answer projection constrained by construction

CAN
  modality/capability contribution

YOU
  addressee -> self

DO
  open action/eventuality slot
```

Composition should converge on:

```text
QUERY ?action
WHERE capability(holder=self, action=?action) is available/conditional
PROJECT ?action
```

Stage 10 binds live `CapabilityInstance`/affordance knowledge.

No capability list is hard-coded in a response rule.

---

# 7. BE/copular architecture

English BE is a language-specific lexeme family.

It must not directly mean:

```text
state
becoming
operational
identity
```

Depending on construction, BE may participate in:

- copular predication;
- classification;
- equative/identity structure;
- localization;
- progressive auxiliary;
- passive auxiliary;
- existential constructions.

“Becoming” is a change/eventuality meaning and must be independently represented.

This rule generalizes to other languages, including languages with zero copula or different copular systems.

---

# 8. Referent and knowledge envelope

A `Referent` is anything with trackable semantic identity.

Examples:

- agents;
- organisms;
- physical/digital objects;
- places;
- event/state occurrences;
- propositions;
- quantities/units;
- times;
- collections;
- contexts;
- schemas when discussed.

Storage kind is serialization shape, not semantic type.

All referents share one derived knowledge envelope:

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
significance
provenance/access
```

Types and entitlements determine applicability.

A `ReferentKnowledgeView` is derived and cycle-pinned, not a competing truth store.

---

# 9. Entitlements and candidate closure

Facet entitlements decide what kinds of predicates/states/capabilities may meaningfully apply.

Runtime projection statuses:

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

Stage 4 must do more than filter same-span lexical candidates.

It must provide semantic closure candidates through graph relationships.

Correct direction:

```text
open predication/query variable
→ holder/actor/affected semantic port
→ grounded referent candidate
→ ReferentKnowledgeView
→ applicable property/state/capability schemas
→ candidate closure values
```

No span equality is semantic authority.

---

# 10. Participant grounding

Stage 0 constructs an evidence-backed `ParticipantFrame`:

```text
system_ref
input_speaker_ref
input_addressee_refs
response_audience_refs
context_ref
permission_ref
identity_evidence_refs
```

Language deixis uses this frame generically.

A lexical sense may contribute:

```text
speaker_role
addressee_role
demonstrative role
prior-output role
```

Grounding resolves the role.

No kernel code checks English pronoun strings.

---

# 11. UOL variable contract

A semantic variable must be capable of preserving:

```text
variable_ref
expected_filler_classes
expected_schema_classes
expected_type_refs
restriction_refs
projection_ref
open_binding_purpose
scope_ref
evidence_refs
```

Open-binding purposes include at least:

```text
query
learning
rule
partial_composition
response_planning
```

A generic “gap” without these constraints is insufficient for learning-first cognition.

---

# 12. Composition and semantic construction algebra

Constructions must eventually build graph fragments, not merely map a surface pattern to one output predicate.

Required bounded operations include:

```text
INTRODUCE_VARIABLE
INSTANTIATE_EXACT_SCHEMA
ACTIVATE_SCHEMA_CLASS_CANDIDATES
BIND_PORT_FROM_SLOT
UNIFY
ADD_RESTRICTION
SET_PROJECTION
ADD_SCOPE
ADD_TIME_FEATURE
ADD_ASPECT_FEATURE
ADD_MODALITY
WRAP_DISCOURSE_ACT
PRESERVE_GAP
```

The executor is generic.

The program/data is language-specific and reviewed.

No arbitrary code in data.

No full-sentence construction except genuine idiom/literal-policy cases.

---

# 13. Factor graph and joint meaning solve

Stage 5 builds one bounded factor graph containing:

```text
sense/lexeme choices
semantic contribution choices
referent identity
schema activation
port fillers
query variables
projection/restriction compatibility
scope
time/aspect/modality
context
discourse act
construction choices
```

Hard factors:

- type/facet entitlement;
- port/filler compatibility;
- participant grounding constraints;
- context isolation;
- query variable typing;
- state applicability;
- exact revision/use authorization.

Soft factors:

- form/morphology evidence;
- lexical priors;
- discourse salience;
- temporal coherence;
- referent knowledge plausibility;
- defaults as ranking only;
- complexity/assumptions.

The solver preserves close alternatives and partial meaning.

---

# 14. Claims, contexts and truth

Input discourse content is first attributed.

A grammatical assertion does not automatically become actual-world knowledge.

Keep:

```text
proposition
claim occurrence
source evidence
epistemic assessment
admission decision
knowledge status
```

separate.

Contexts include actual, reported, belief, hypothetical, planned, desired, counterfactual, fictional/simulated and quoted.

---

# 15. Universal semantic query binding

Stage 10 must bind restriction graphs against **semantic knowledge**, not one storage record kind.

Queryable sources include:

- semantic applications;
- referent/type/identity projections;
- properties;
- state assignments/timelines/default expectations;
- relations/roles;
- capabilities/affordances/functions;
- events;
- propositions/claims/knowledge;
- quantities/measures;
- time/place;
- proofs/explanations.

Storage representation is an implementation detail.

Query output is semantic bindings, never final text.

---

# 16. Self model

`referent:self` is a real referent.

Its knowledge is derived from:

- software-agent type closure;
- runtime adapters;
- active language competence;
- semantic-store access;
- memory/learning authority;
- channel availability;
- operation capability;
- current runtime state.

Self states must be evidence-backed.

Examples of potentially applicable dimensions:

```text
operational_status
availability
connectivity
capability_status
resource state
```

Applicability must be entitlement-correct.

Do not fabricate human affective states for a software agent unless explicitly modeled and evidenced.

---

# 17. Capabilities and actions

Distinguish:

```text
affordance
  action is structurally meaningful

disposition
  latent ability under conditions

capability
  current ability under known dependencies

competence
  verified execution/semantic skill

permission
  authorization to perform

function
  intended/system contribution

intention/goal
  selected desired action/result
```

A query such as “what can you do?” must bind live capability/affordance semantics, not a canned list.

---

# 18. Events and transitions

An event occurrence is context/time qualified.

Only admitted events can mutate the corresponding world context.

Transitions are:

```text
event occurrence
→ transition contract match
→ proof
→ state/relation/capability delta candidates
→ authorization
→ atomic commit
```

No event-specific Python mutator.

State history remains queryable.

---

# 19. Learning architecture boundary

Every unresolved dependency should produce a typed frontier such as:

```text
unknown form
unknown lexeme/form family
unknown lexical sense
unknown semantic contribution
unknown construction
unknown referent/type
missing state dimension/value
missing port/filler
missing query projection
missing transition/dependency
missing realization competence
missing response competence
```

Learning lifecycle:

```text
candidate
→ structurally_closed
→ provisional
→ competence_verified
→ active
→ superseded/rejected
```

Promotion is independent by use operation.

Learning must survive restart and invalidate dependent projections when revised.

---

# 20. Response cognition

Stage 15 derives semantic obligations/goals.

Stage 18 builds Response UOL with generic transforms such as:

```text
answer_bound_query
report_value
report_state
report_set
report_event
report_capability
describe_referent_projection
qualify_epistemic_status
clarify_missing_binding
```

Ordinary predicates do not own response sentences.

A new learned state or action should become answerable without a new predicate-specific response policy.

---

# 21. Realization

Target-language realization:

```text
Response UOL
→ clause plan
→ argument frame
→ reference plan
→ morphology/agreement
→ linearization
→ surface
```

The realizer may choose wording but may not invent:

- facts;
- relationships;
- certainty;
- emotional stance;
- impact;
- unsupported referents.

Round-trip semantic equivalence is mandatory before emission.

---

# 22. Compatibility and migration

The current signed boot contains legacy direct language authority.

During remediation:

1. old records remain readable;
2. new learned/reviewed language authority uses lexemes and semantic-contribution specs;
3. runtime prefers new authority when present;
4. legacy fallback is explicit and traceable;
5. later seed-rebuild phase migrates canonical language data;
6. only then may the compatibility path be removed.

No silent reinterpretation of signed source fingerprints.

---

# 23. Non-negotiable productivity invariant

A newly learned/promoted semantic structure must be able to:

- ground;
- compose;
- project referent facets;
- participate in queries;
- remain attributed/epistemically qualified;
- participate in transitions/capability recomputation when contracts exist;
- influence goals/responses;
- realize in authorized languages;
- survive restart;
- invalidate dependents when revised;

without adding:

- concept-name Python branches;
- regex/keyword semantic routing;
- event-specific mutators;
- predicate-specific answer sentences;
- transcript phrase constructions.

---

# 24. Acceptance examples are consequences, not authorities

Examples such as:

```text
how are you?
what can you do?
my name is X
what is my name?
```

are release regressions.

They must pass for architectural reasons.

Exact phrase mappings, full-sequence constructions or canned answers are prohibited.

The decisive tests use synthetic renamed vocabulary, changed referent types, new states/actions/capabilities, multilingual lexicalizations and restart/rehydration.
