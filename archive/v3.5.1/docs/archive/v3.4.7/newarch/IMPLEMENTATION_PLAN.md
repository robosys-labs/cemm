# CEMM v3.5 Foundational Redesign Implementation Plan

**Status:** canonical proposed execution plan  
**Objective:** implement the learning-first referent/facet/event/claim architecture without retaining v3.4.7 semantic authority.

---

## 1. Program gates

The release cannot be called complete until it is:

```text
specified
implemented
wired
authoritative
verified
```

No phase is complete merely because classes or JSON files exist.

---

## 2. Phase 0 — Baseline and authority audit

- pin current main commit;
- capture failing transcripts and traces;
- inventory all semantic shortcuts;
- map all per-predicate templates;
- inventory mutable state blobs;
- inventory claims admitted as actual facts;
- identify every Python enum that blocks learned types;
- record performance and database shape.

Deliverable: `v347-authority-audit.md`.

---

## 3. Phase 1 — Replace governing documents

Install this package's:

- `ARCHITECTURE.md`;
- `FOUNDATIONAL_KNOWLEDGE_ARCHITECTURE.md`;
- `UOL.md`;
- `CORE_LOOP.md`;
- `DATA_ARCHITECTURE.md`;
- `IMPLEMENTATION_PLAN.md`;
- `ACCEPTANCE_CONTRACT.md`;
- `AGENTS.md`.

Archive conflicting v3.4.7 documents.

Add CI lints for prohibited authority patterns.

---

## 4. Phase 2 — Semantic schema metamodel

Implement:

```text
MeaningSchema
ReferentTypeSchema
FacetSchema
FacetEntitlement
PropertySchema
StateDimensionSchema
StateValueSchema
RelationSchema
RoleSchema
FunctionSchema
ActionSchema
EventSchema
OperatorSchema
DiscourseActSchema
ResponsePolicySchema
```

Requirements:

- data-driven schema classes;
- multiple inheritance;
- revision/lifecycle;
- typed local ports;
- use profiles;
- provenance/dependencies;
- competence hooks.

Remove executable dependency on the broad `ReferentKind` ontology enum.

---

## 5. Phase 3 — UOL v3 records

Implement:

```text
SemanticApplication
SemanticVariable
ScopeRelation
CoordinationGroup
PropositionReferent
ClaimOccurrence
EventOccurrence
StateDelta
CapabilityDelta
ImpactAssessment
ImportanceAssessment
```

Add canonical fingerprints and equivalence comparison.

---

## 6. Phase 4 — Data compiler and normalized store

- establish modular source tree;
- implement validators;
- compile deterministic SQLite;
- implement read-only boot DB;
- implement writable overlays;
- implement typed repositories;
- implement CAS snapshots and GraphPatch commit;
- implement dependency fingerprints/materialized views.

---

## 7. Phase 5 — Universal facet and entitlement engine

Implement:

```text
TypeClosureCompiler
FacetEntitlementProjector
ReferentKnowledgeProjector
StateApplicabilityAssessor
DefaultExpectationProjector
```

Tests:

- active/latent/default/unknown/inapplicable;
- multiple inheritance;
- blocked entitlement;
- context/time;
- contradiction.

---

## 8. Phase 6 — Foundational seed package

Seed and competence-test:

- root semantic types;
- universal facets;
- native semantic axes;
- core properties;
- core state dimensions;
- core change/event schemas;
- claim/proposition/discourse schemas;
- capability/function distinctions;
- self identity and live capability contracts.

Do not seed domain prose as capability descriptions.

---

## 9. Phase 7 — Form lattice and lexical-sense redesign

- separate forms from senses;
- add operator/scope candidates;
- add dependency/constituency adapters;
- add code switching;
- add coordination, complement, relative clause, and ellipsis;
- keep full-sentence patterns only for genuine idioms;
- convert colloquial normalization to evidence.

---

## 10. Phase 8 — Referent and claim grounding

Implement joint resolution for:

- participants;
- names/descriptions;
- events/states/propositions;
- multimodal tracks;
- system output;
- schema topics;
- claim source/audience;
- provisional typed mentions.

Add identity merge/split proposals.

---

## 11. Phase 9 — UOL factor-graph composer

- variables for senses, schemas, referents, ports, scope, time, context;
- hard entitlement constraints;
- soft discourse/world factors;
- nested operator composition;
- queries;
- claims/events;
- multi-clause bundles;
- partial understanding;
- bounded beam and trace.

Delete v3.4.7 `JointMeaningAssembler` authority from v3.5.

---

## 12. Phase 10 — Epistemic and claim architecture

- claim occurrence compiler;
- attributed contexts;
- source/evidence model;
- four-state truth;
- corrections/retractions;
- independent actual-world admission;
- claim history and contradiction.

Acceptance: a grammatical claim must not automatically update actual state.

---

## 13. Phase 11 — Event transition engine

Implement:

```text
TransitionContractCompiler
TransitionPreviewEngine
StateDeltaValidator
StateTimelineProjector
CapabilityDependencyEngine
EffectCommitCoordinator
```

First generic events:

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
```

Then implement biological death through the same data path.

No event-specific mutation branch is allowed.

---

## 14. Phase 12 — Death/loss vertical slice

Required cases:

```text
The fox died.
The fox did not die.
The fox may die.
The fox almost died.
The fox died in the story.
The battery died.
The company died.
The dead fox moved downhill.
```

Verify:

- sense selection;
- context isolation;
- life-state transition;
- capability dependency;
- externally caused movement;
- no health/emotion category error;
- impact proof.

---

## 15. Phase 13 — Learning-first coordinator

Implement packages for:

- referent;
- type;
- facet entitlement;
- property;
- state;
- action/event;
- relation/role;
- rule;
- lexeme sense;
- realization;
- response policy.

Features:

- exact grounding frontier;
- recursive limits;
- counterexamples;
- independent competence;
- per-use activation;
- rehydration;
- retraction and invalidation.

---

## 16. Phase 14 — Impact and importance engine

Implement:

```text
ImpactRuleEngine
ImportanceEvidenceCollector
SignificanceCoordinator
StakeholderResolver
```

Inputs:

- state/capability/relation deltas;
- explicit importance;
- user goals;
- relation/ownership;
- mention history;
- affective evidence;
- magnitude/irreversibility;
- privacy scope.

Output is assessment, not fact.

---

## 17. Phase 15 — Goals and response policies

- generate response goals from semantic obligations;
- add console/warn/congratulate/silence candidates;
- prohibit targetless acknowledgement;
- support semantic response policies;
- preserve literal policy overrides with explicit provenance;
- add repetition and social-harm penalties.

---

## 18. Phase 16 — Response UOL planner

Implement proof-carrying transforms:

- query closure;
- perspective;
- state/property reporting;
- capability expansion;
- event acknowledgement;
- impact-sensitive console/warn;
- qualification;
- exact repair questions;
- aggregation and ordering.

---

## 19. Phase 17 — Multilingual NLG algebra

Implement:

- deep clause plans;
- argument frames;
- feature unification;
- reference generation;
- modality;
- negation;
- tense/aspect;
- coordination;
- morphology;
- linearization;
- semantic round-trip.

Initial languages:

- English;
- French;
- Swahili.

No per-predicate answer templates.

---

## 20. Phase 18 — Output discourse and common ground

Store system output UOL, targets, reasons, commitments, and response policy refs.

Acceptance:

```text
Why?
For what?
Understood what?
What did you mean by that?
```

---

## 21. Phase 19 — Migration

Migrate:

- v3.4.7 foundation;
- learned schemas/rules;
- referents;
- knowledge;
- states;
- aliases;
- operations;
- language data.

Generate:

- ref map;
- rejected records;
- semantic equivalence report;
- rollback DB.

---

## 22. Phase 20 — Authority removal

Physically remove from canonical runtime:

- direct modal/query word-to-predicate shortcuts;
- per-predicate response sentences;
- generic targetless response moves;
- monolithic mutable state blobs;
- input-only discourse commit;
- event-specific state mutation helpers;
- semantic type enum expansion requirements.

---

## 23. Phase 21 — Verification

Run:

- architecture lints;
- unit tests;
- semantic competence;
- transition tests;
- learning/restart tests;
- claim/epistemic tests;
- multimodal tests;
- cross-language UOL equivalence;
- NLG round-trip;
- long-session significance;
- performance budgets;
- migration tests.

---

## 24. Vertical delivery order

### Slice A — identity/property learning

```text
My name is Chibu.
What is my name?
Correct it to Chibueze.
```

### Slice B — capability/function distinction

```text
What can you do?
What are you designed to do?
What are you allowed to do?
What will you do?
```

### Slice C — state and entitlement

```text
What is your status?
Are you connected?
Can a proposition be sad?
```

The last query should distinguish inapplicable affective state from unknown.

### Slice D — claims

```text
John says the fox died.
Did the fox die?
```

Answer must preserve attribution/uncertainty.

### Slice E — death transition

Use the cases in Phase 12.

### Slice F — significance response

```text
A fox died.
My fox died.
My beloved fox died.
The fox in the story died.
```

Response candidates must differ for semantic reasons.

### Slice G — learned event

Teach a new event with state effects, verify inference, restart, and cross-language lexicalization.

---

## 25. Performance targets

Initial median targets without external tools:

```text
form analysis             25 ms
candidate/profile lookup  20 ms
UOL composition           60 ms
epistemic/retrieval       25 ms
transition/impact         25 ms
response planning         15 ms
NLG + verification        60 ms
total                     <250 ms
```

Timeouts preserve partial proof and learning frontier.

---

## 26. Definition of completion

v3.5 is complete only when a new learned type or event can:

1. inherit facets;
2. constrain reference and composition;
3. participate in claims;
4. update state through generic transition contracts;
5. affect capabilities through dependencies;
6. produce contextual impact;
7. influence response goals;
8. be queried and explained;
9. be realized in multiple languages;
10. survive restart;
11. be corrected and invalidate dependents;
12. do all of this without a new kernel branch or full-sentence template.
