# CEMM v3.5 Governing Agent Instructions

This file is the highest-priority local implementation contract for CEMM v3.5.

## 0. Current status

The public runtime has cut over to the signed v3.5 Stage-0..22 authority. That cutover does **not** mean semantic activation is complete.

Use the following status vocabulary precisely:

```text
specified
implemented
wired
authoritative
verified
```

A component is complete only when every applicable status is true.

The current remediation target is **productive semantic competence**: a small grounded vocabulary and reviewed grammar must compose into unseen meaning without transcript phrases, predicate catalogues, language-specific kernel branches, or canned answers.

v3.4.7 and older code are migration/history only. They must never regain public runtime authority.

---

## 1. Authority order

Use these sources in this order:

1. root `AGENTS.md`
2. root `ARCHITECTURE.md`
3. `docs/architecture/TERMINOLOGY.md`
4. `docs/architecture/FOUNDATIONAL_KNOWLEDGE_ARCHITECTURE.md`
5. `docs/architecture/FOUNDATIONAL_SEMANTIC_ALGEBRA.md`
6. `docs/architecture/LEARNING_ARCHITECTURE.md`
7. `docs/architecture/CLAIMS_EVENTS_STATE_AND_IMPACT.md`
8. `docs/architecture/UOL.md`
9. root `CORE_LOOP.md`
10. `docs/architecture/DATA_ARCHITECTURE.md`
11. root `IMPLEMENTATION_PLAN.md`
12. root `phased-fixes.md`
13. root `ACCEPTANCE_CONTRACT.md`
14. executable architecture/productivity tests
15. implementation code and reviewed data

If lower authority conflicts with higher authority, fix or quarantine the lower authority. Do not create a second competing path.

---

## 2. Four authority layers

Never collapse these layers.

### 2.1 Kernel structural primitives

The kernel may hard-code only stable machinery required to execute semantics:

- referent identity;
- schema/type machinery;
- semantic applications;
- ports, fillers, variables, bindings;
- properties, state dimensions/values, relations, roles;
- eventuality/action/event representation;
- time, place, quantity, measure;
- operators and scope;
- propositions, claims, evidence, epistemics;
- query/information-gap mechanics;
- capability/affordance/function distinction;
- transitions/deltas/dependencies;
- context, permissions, provenance, lifecycle;
- goals, operations, Response UOL;
- learning frontiers, competence, promotion, invalidation.

Do not add a Python enum or branch merely because a new learned concept appears.

### 2.2 Foundational semantic axes

Cross-domain semantic axes are reviewed, revisioned **data**, not surface-word branches.

Examples:

- identity/sameness/difference;
- classification;
- existence;
- applicability/activation;
- persistence/change;
- polarity/modality;
- occurrence/aspect;
- time/localization;
- quantity/order/degree;
- cause/enable/prevent;
- agency/control/affectedness;
- containment/mereology/possession;
- capability status;
- epistemic status/source;
- query answer projections;
- uncertainty/default expectation;
- valence/significance.

### 2.3 Learned semantic world

Domain concepts remain data:

```text
fox
server
battery
pregnancy
bank
fraud
marriage
charging
specific emotions
specific procedures
specific social conventions
```

A new concept must not require kernel code.

### 2.4 Language and grammar

Language packages may encode:

- forms, morphemes, lexemes and allomorphs;
- lexical categories;
- agreement, tense, aspect and case features;
- constructions and word order;
- semantic contribution specifications;
- realization morphology and linearization.

Language data may provide evidence and constraints. It may not become world truth or kernel ontology.

---

## 3. Semantic Contribution Law

Every recognized linguistic or multimodal unit contributes only the **smallest semantic constraints justified by evidence**.

Valid contribution mechanics include:

```text
TARGET
REFERENTIAL
VARIABLE
RESTRICTION
PROJECTION
SCOPE
ARGUMENT
GRAMMATICAL_FEATURE
CONSTRUCTION
```

These are mechanics, not vocabulary.

A unit must not be promoted directly into a completed proposition, discourse act, response obligation, referent binding, event occurrence, or world fact unless that complete meaning is intrinsic to the unit itself.

Every selected contribution must retain evidence and lineage.

Unknown material may remain unresolved without erasing known contributions around it.

---

## 4. Meaning Closure Law

Partial understanding is valid cognition.

A partial meaning must explicitly preserve:

- what has been grounded;
- what schema classes remain possible;
- what filler classes are allowed;
- what referent types are compatible;
- what restrictions apply;
- what answer projection is requested;
- what scope/time/context applies;
- why a variable remains open.

Meaning closes only through compatible composition of:

```text
form/morphology evidence
+ lexical/semantic contributions
+ constructions
+ participant/discourse anchors
+ referent grounding
+ type/facet entitlement
+ state/capability knowledge
+ time/context
+ epistemic authority
```

No stage may invent a filler merely to make realization possible.

---

## 5. Query Separation Law

Keep these separate:

1. **information gap** — something is unknown;
2. **semantic variable** — the missing binding;
3. **restriction graph** — what can satisfy it;
4. **answer projection** — what part of a match should be returned;
5. **discourse act** — ask, embedded question, wonder, request, etc.;
6. **response obligation** — whether/how CEMM should respond.

Words such as `who`, `what`, `where`, `when`, `why`, and `how` must not directly map to a completed response intent.

Example:

```text
I know how it works.
Tell me how it works.
How does it work?
I wonder how it works.
```

The `how` contribution may be related across all four. Only the matrix/discourse structure determines whether an `ask` act and response obligation exist.

---

## 6. Qualitative-description law

Do not equate grammatical categories with semantic categories.

```text
adjective != state
adverb != process
```

An adjective may realize a property, state value, classification, scalar value, or event result.

An adverb may realize manner, degree, time, frequency, modality, evidentiality, or discourse stance.

Grammar constrains semantic candidates. It does not define ontology.

### 6.1 Manner

`manner` is an eventuality/process-characterization projection, not a universal state value.

### 6.2 Degree

`degree` is grounded in ordered/scalar dimensions, comparison, quantity and measure.

### 6.3 Method

`method` is structured means/procedure knowledge built from goals/results, processes/actions, resources/instruments, ordering, and causal/enabling relations.

### 6.4 Availability and connectivity

`availability` and `connectivity` are state dimensions whose applicability comes from type/facet entitlement. They are not universal kernel primitives.

---

## 7. Eventuality law

CEMM must be able to distinguish:

```text
STATE
  condition holding over an interval

PROCESS / ACTIVITY
  dynamic unfolding over an interval without requiring a terminal boundary

EVENT / TRANSITION
  occurrence/change boundary/result structure

ACTION
  eventuality with control/intentionality semantics
```

Do not add a `PROCESS` Python enum merely because English grammar needs it. First determine whether the distinction can be expressed by event/aspect profiles and reviewed schemas.

A copular/auxiliary form such as English BE must not directly mean `state`, `becoming`, or one domain predicate.

---

## 8. Referent law

`Referent` is the only identity-bearing semantic filler family.

Semantic type is data-driven and supports multiple inheritance.

Properties, states, roles, capabilities, functions, claims, events and significance are applications/records around referents, not casual mutable fields.

Identity continuity is separate from state continuity.

---

## 9. Entitlement law

Every property/state/capability interpretation must be licensed by:

- type-derived facet entitlement; or
- explicit schema extension with exact authority.

Distinguish:

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

A default is never an active fact.

Stage-4 referent knowledge must constrain and, where structurally licensed, generate candidate closures for Stage 5. It must not merely act as a same-token filter.

---

## 10. Participant/deixis law

Speaker/addressee identity comes from the cycle `ParticipantFrame` and evidence.

A pronoun or deictic contributes a discourse-role requirement. It does not hard-code:

```text
I   -> user
you -> self
```

The same mechanism must work for arbitrary languages and renamed synthetic forms.

---

## 11. Claim and epistemic law

An utterance is evidence that a discourse/claim act occurred.

It is not automatically actual-world truth.

Keep separate:

```text
proposition
claim occurrence
source
evidence
epistemic admission
knowledge status
```

Reported, hypothetical, planned, desired, counterfactual and fictional contexts remain isolated.

---

## 12. Transition law

Events affect state only through typed transition contracts and proof-bearing deltas.

No event-specific state mutation code.

No transition from an unadmitted or wrong-context event.

Timeout/incompleteness never becomes success.

---

## 13. Capability law

Keep separate:

```text
affordance
disposition
capability
permission
competence
intention
function
```

Capabilities are current and evidence/dependency based.

Self capability claims must reflect active runtime authority, not merely the existence of an action schema.

---

## 14. Language authority law

The canonical language path is:

```text
observation
→ form/morpheme candidates
→ lexeme/form-family candidates
→ lexical meaning/sense candidates
→ semantic contributions
→ construction constraints
→ UOL factor graph
```

New language knowledge must prefer durable lexeme/contribution authority.

Legacy direct `form -> sense` links may remain readable only as an explicit compatibility path until seed migration. They are not the target architecture.

`metadata.interpretation_enabled` must not be a hidden semantic authority switch.

External parsers are optional evidence providers only.

---

## 15. Learning-first law

CEMM learns reusable semantic structure, not transcript phrases.

The following ordering laws are non-negotiable:

```text
perceive before answering
working graph before memory write
compression before durable storage
source before belief
time before current-state claims
permission before learning
safety/policy before realization and emission
committed write before claiming that memory/state changed
meaning before wording
```

The temporary working graph may preserve ambiguity, branches, gaps and evidence. Durable memory stores compressed reusable semantic authority—not a transcript archive.

A fix is invalid if it requires:

- an exact transcript phrase;
- a full-sentence construction for ordinary compositional meaning;
- regex/keyword semantic routing in the kernel;
- a Python concept-name branch;
- a per-predicate output sentence;
- an event-specific mutator;
- an ungrounded default;
- a targetless acknowledgement;
- catalogue-size assertions as evidence of cognition.

Learning is a co-equal acquisition/consolidation spine, not a terminal bookkeeping step. Observation, unresolved frontiers, candidate induction, competence, promotion, consolidation, invalidation and rehydration must remain connected to the canonical cycle.

Learned authority is promoted independently by use:

```text
ground
compose
query
infer
transition
impact
plan
execute
realize
response_policy
```

---

## 16. Response law

The system first builds Response UOL.

Response cognition must be structurally generic, e.g.:

```text
answer_bound_query
report_value
report_state
report_set
report_event
report_capability
qualify_epistemic_status
clarify_missing_binding
```

Adding a new state/action/capability must not require a new predicate-specific response rule.

Literal programmed responses are allowed only as explicit scoped semantic policy.

---

## 17. Test law

Semantic tests must prove mechanisms, not examples.

Every major semantic change should include, where applicable:

- positive case;
- paraphrase/variant;
- synthetic vocabulary rename;
- cross-type contrast;
- negation/modality contrast;
- context isolation;
- counterexample;
- restart/rehydration;
- trace/contribution assertion;
- no-shortcut lint.

Tests must not freeze exact counts of policies, transforms, frames, lexical senses, constructions or morphology rules as evidence of competence.

Tests may assert deterministic fingerprints/counts only when explicitly testing source-package tamper detection.

---

## 18. Runtime authority law

The signed Stage-0..22 graph is the sole public runtime authority.

Do not:

- reintroduce v3.4.7 imports into public surfaces;
- add fallback runtimes;
- bypass the authority manifest;
- weaken round-trip/emission gates to make demos pass;
- hide unresolved frontiers from verification.

A failing semantic case must be fixed upstream.

---

## 19. Repository hygiene

- archive conflicting historical guidance;
- never duplicate semantic authority across JSON and Python;
- preserve exact revisions/provenance;
- preserve migrations and rollback;
- report skipped tests;
- remove stale tests rather than satisfy known-wrong contracts;
- prefer deleting competing authority over wrapping it;
- do not rebuild signed boot artifacts without deterministic verification.

---

## 20. Definition of completion

A phase is complete only when:

1. architecture and data model agree;
2. codecs and persistence round-trip exactly;
3. canonical runtime consumes the new authority;
4. legacy compatibility is explicit and bounded;
5. synthetic productivity tests pass;
6. no prohibited shortcut was introduced;
7. restart/rehydration behavior is verified where durable authority changed;
8. release evidence states what remains incomplete.
