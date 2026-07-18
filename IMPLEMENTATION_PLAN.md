# CEMM v3.5 Canonical Implementation Plan

**Status:** canonical replacement execution plan
**Purpose:** implement and cut over a learning-first, grounded, multilingual semantic runtime without allowing implementation examples, test fixtures, language forms, or domain concepts to become hidden kernel authority.

---

## 1. Governing laws

### 1.1 Completion is a five-gate state

A phase is not complete because classes, JSON, tests, or documentation exist. Every phase is tracked independently as:

```text
specified -> implemented -> wired -> authoritative -> verified
```

A phase may be implemented and phase-verified while remaining intentionally non-authoritative until runtime cutover.

### 1.2 Plans do not define ontology

This document specifies **machinery, authority boundaries, proof obligations, and coverage classes**. It does not define a vocabulary of world concepts.

Therefore:

- a noun, verb, state, event, language form, or example mentioned in documentation or a test is never automatically a boot concept;
- lists of semantic phenomena are coverage requirements, not privileged schema enumerations;
- test fixtures and demonstration packages are non-authoritative unless separately promoted through the reviewed data path;
- no phase may introduce a Python branch merely because an example needs a new type, event, property, relation, state, response, or lexicalization;
- no later phase may silently reinterpret an earlier record family through metadata flags or naming conventions.

### 1.3 Data authority must be explicit

Executable semantic behavior must come from revisioned, validated, evidence-bearing records with explicit use authorization. Kernel code may implement generic record families and algorithms, but must not know named domain semantics.

Forbidden kernel authority includes:

- language-specific semantic word tests;
- predicate/action keyword catalogues used as cognition;
- named event-to-effect branches;
- named type-to-capability branches;
- full-sentence response templates used as semantic authority;
- metadata booleans that bypass first-class semantic records;
- implicit actual-world context defaults;
- defaults copied into active state;
- claims treated as facts because they are grammatical or confidently grounded.

### 1.4 Every stage owns only its artifact

No core-loop stage may manufacture a downstream artifact. In particular:

- form analysis does not choose referent identity;
- grounding does not admit truth;
- composition does not commit state;
- epistemic admission does not derive event effects;
- transition preview does not mutate durable state;
- impact assessment does not invent state change;
- response planning does not invent facts;
- realization does not choose meaning.

### 1.5 Exact revision and snapshot pinning

Every executable decision that depends on mutable authority must pin the exact relevant revisions or snapshot fingerprints. A later correction must not retroactively change why an earlier decision was authorized.

### 1.6 Partial understanding is a valid result

Budget exhaustion, ambiguity, missing schema structure, missing evidence, unresolved time/context, or unknown state produces a proof-bearing frontier. It must not be replaced by guessed meaning or generic clarification unless policy later selects that response.

---

## 2. Cross-phase release gates

The release remains incomplete until all of the following are true:

1. **Specification gate** — governing documents and executable contracts agree.
2. **Implementation gate** — canonical v3.5 components exist without delegating semantic authority to legacy code.
3. **Wiring gate** — core-loop stage outputs feed the intended next stage through typed contracts.
4. **Authority gate** — public runtime decisions come from v3.5 authorities rather than retained legacy shortcuts.
5. **Verification gate** — unit, integration, competence, restart, migration, adversarial, performance, and semantic-equivalence evidence passes.

A missing measurement is recorded as pending, never inferred as passing.

---

## 3. Phase 0 — Baseline, authority, and measurement audit

### Objective

Create a reproducible baseline and map every active authority before replacement.

### Required coverage

- exact repository/runtime version and executable composition root;
- core-loop stage order and all durable commit boundaries;
- schema, referent, UOL, epistemic, inference, transition, operation, response, and realization authorities;
- semantic shortcuts, language-specific branches, templates, mutable opaque state, and claim-to-fact paths;
- legacy enums/control flow that constrain learnable semantic structure;
- representative transcripts/traces;
- database schema, row/size measurements, principal query plans;
- stage latency/memory budgets and available performance evidence;
- preserve/replace/migrate/remove disposition for every active component.

### Exit gates

- machine-ratcheted authority-debt inventory exists;
- baseline measurements are captured or explicitly marked pending;
- no later cutover may claim parity without comparing against this baseline.

---

## 4. Phase 1 — Governing contracts and architectural enforcement

### Objective

Install one mutually consistent architecture contract and make major prohibitions executable in CI.

### Required work

- canonical architecture, foundational knowledge, UOL, core-loop, data, implementation, acceptance, and agent-governance documents;
- archive conflicting governing material;
- AST/data lints for semantic hardcoding, language-specific authority, implicit context, templates, event-specific mutation, and legacy semantic delegation;
- legacy-debt ratchet with explicit allowed migration-only exclusions;
- CI entrypoint that runs architecture checks on the complete repository.

### Exit gate

Documents, lints, debt inventory, and CI describe and enforce the same authority boundaries.

---

## 5. Phase 2 — Revisioned semantic schema metamodel

### Objective

Provide one data-driven authority for semantic schema families without requiring source-code ontology edits for learned concepts.

### Required capabilities

- typed schema families with shared lifecycle/provenance/dependency infrastructure;
- multiple inheritance and cycle/family validation;
- exact/minimum/authoritative revision links;
- independent per-use authorization;
- typed local ports for referents, applications, variables, coordination, and explicit quoted literals;
- storage-kind, semantic-type, schema-class, cardinality, ordering, context/time, and open-binding constraints;
- semantic-content and full-record fingerprints;
- competence hooks and invalidation dependencies;
- unresolved candidate frontiers but hard failure for broken active authority.

### Exit gate

Every schema family round-trips through reviewed data and can be selected/authorized deterministically by exact revision.

---

## 6. Phase 3 — UOL records and semantic graph equivalence

### Objective

Provide the language-neutral runtime graph records used by all later cognition.

### Required capabilities

- referent-backed identity for ordinary entities, propositions, claims, events, states, quantities, time, contexts, and schema topics;
- semantic applications and typed bindings;
- open variables with explicit purpose/restrictions;
- scope and coordination;
- proposition/claim/event separation;
- state and capability deltas separated from event occurrence;
- impact/importance separated from truth polarity and state change;
- context/time/proof/revision qualification;
- semantic equivalence invariant to generated local IDs while sensitive to all meaning-bearing axes.

### Exit gate

Graph identity/order noise does not change semantic equivalence; any meaning-bearing change does.

---

## 7. Phase 4 — Deterministic data compiler and normalized semantic store

### Objective

Make reviewed semantic authority durable, deterministic, revisioned, and safely mutable through overlays.

### Required capabilities

- modular source manifest and validators;
- deterministic SQLite compilation;
- immutable read-only boot database;
- writable overlay database;
- typed repositories;
- snapshot/CAS semantics;
- GraphPatch commit boundary;
- normalized persistence for canonical record families;
- dependency fingerprints, invalidation, and derived-view recomputation.

### Exit gate

Double compilation is byte-identical and concurrent/stale writes cannot bypass revision or dependency checks.

---

## 8. Phase 5 — Universal facet, entitlement, and referent projection engine

### Objective

Derive what knowledge families are meaningful for any referent from its data-driven type closure.

### Required capabilities

- type closure;
- facet entitlement inheritance/blocking/narrowing;
- applicable/latent/default-expected/unknown/blocked/terminated/inapplicable/contradicted distinctions;
- state applicability;
- default expectations without materialization;
- referent knowledge views;
- affordance/function/capability separation;
- context/time/access restrictions.

### Exit gate

Projection is deterministic, revision-pinned, contradiction-safe, and does not create facts from defaults.

---

## 9. Phase 6 — Minimal structural foundation

### Objective

Seed only the smallest structural semantic substrate required to learn and operate.

### Required coverage

- broad structural referent-type anchors;
- universal facets and entitlement machinery;
- orthogonal native semantic axes;
- minimal generic property/state/relation/role/action/event/discourse structure;
- claim/proposition/context structure;
- function/capability distinction;
- truthful self identity and runtime-backed capability contracts;
- independent competence/audit contract.

### Prohibitions

- no convenience domain taxonomy;
- no domain event effects;
- no sentence templates;
- no language-specific lexical forms as foundation ontology;
- no capability prose treated as executable semantics.

### Exit gate

The foundation is small, domain-light, language-neutral, audited, and cryptographically pinned.

---

## 10. Phase 7 — Form lattice and lexical-sense evidence

### Objective

Represent multilingual form evidence without making surface forms semantic authority.

### Required capabilities

- language packs as reviewed data;
- exact source spans and reversible normalization evidence;
- forms separated from senses;
- many-to-many form/sense links with exact semantic target revisions;
- span-local language/script evidence and code switching;
- dependency/constituency adapters as evidence only;
- compositional constructions for reusable grammatical relations;
- coordination, complementation, modification/relative structure, ellipsis, scope cues, and unresolved spans;
- full-sentence patterns permitted only for independently reviewed genuine idioms, never ordinary semantic routing.

### Exit gate

Equivalent semantic targets can be reached across reviewed language packages without language-specific kernel semantic branches.

---

## 11. Phase 8 — Joint referent and claim grounding

### Objective

Resolve identity/reference jointly while preserving ambiguity and provisional frontiers.

### Required capabilities

- participants and discourse anchors supplied explicitly by the cycle;
- names, identifiers, descriptions, aliases, discourse chains, multimodal tracks, prior system output, event/proposition history, schema topics, and provisional typed mentions;
- joint coreference/distinctness constraints;
- type/storage/context/time compatibility;
- source/audience/role grounding through reviewed semantic/construction ports;
- bounded deterministic solving with ranked alternatives;
- review-only provisional creation and identity merge/split proposals.

### Prohibitions

- no named ontology refs in grounding control flow;
- no sole-provisional candidate reported as resolved;
- no lexical event predicate automatically equated with an arbitrary historical event;
- no implicit actual-context or implicit self/user anchor;
- grounding does not admit truth or mutate identity.

### Exit gate

Grounding outputs candidates/assignments/frontiers/proposals with traceable evidence and no downstream epistemic side effects.

---

## 12. Phase 9 — UOL factor-graph composition

### Objective

Compose selected meaning hypotheses from reviewed form, grounding, schema, and context evidence without predicate-specific assembly code.

### Required capabilities

- variables for sense, schema, referent, port filler, scope, time, context, and construction;
- exact schema/use/port/type/entitlement/context hard factors;
- traceable discourse/world/default/complexity soft factors;
- nested operators and explicit scope;
- queries and typed open variables;
- proposition/claim/event composition;
- shared arguments and multi-clause bundles;
- partial understanding/frontiers;
- deterministic bounded best-first/beam solving and pruning trace;
- close-alternative preservation and selection assessment.

### Prohibitions

- solver has no named semantic vocabulary;
- no realization score influences meaning selection;
- no claim admission or state/capability effect occurs here.

### Exit gate

Composition is language-neutral, bounded, deterministic under pinned inputs, and partial-safe.

---

## 13. Phase 10 — Epistemic and attributed-claim architecture

### Objective

Keep what was said, who said it, what CEMM admits, and what is actually projected as knowledge as separate durable authorities.

### Required capabilities

- structural claim occurrence compilation;
- source and attributed-context separation;
- append-only claim history;
- source-local corrections/retractions;
- durable multidimensional source assessment;
- explicit proof/policy/authorization gate for cross-context admission;
- exact source-assessment revision pins;
- independent support and opposition admissions;
- derived four-state truth projection;
- knowledge projection with exact admission lineage;
- contradiction without destructive overwrite.

### Prohibitions

- grammar or grounding confidence cannot authorize fact admission;
- metadata flags cannot authorize context crossing;
- one record cannot directly assert the derived BOTH state;
- this phase cannot create state/capability effects.

### Exit gate

A well-formed claim can remain attributed evidence indefinitely without becoming actual-world knowledge unless independently admitted.

---

## 14. Phase 11 — Generic event transition and dependent-capability engine

### Objective

Convert independently admitted event occurrences into **previewed, proof-bearing, generic state effects** and dependent capability reevaluations without placing any event-specific mutation knowledge in Python.

### 14.1 Authority records

Implement revisioned, evidence-bearing records for:

```text
TransitionContract
CapabilityDependency
TransitionProof
```

A transition contract must refer only to exact schema revisions, typed event ports, explicit preconditions, and explicit effects. It must not be inferred from semantic-key strings or event names.

### 14.2 Generic runtime components

Implement:

```text
TransitionContractCompiler
EventAdmissionGate
TransitionPreviewEngine
StateDeltaValidator
StateTimelineProjector
CapabilityDependencyEngine
EffectCommitCoordinator
TransitionCoordinator
```

Names above describe generic responsibilities, not domain semantics.

### 14.3 Admission gate

A transition requires:

- a durable event occurrence;
- an exact transition-authorized EventSchema revision;
- an active exact TransitionContract revision linked by reviewed authority;
- independent active epistemic admission into the target context;
- structural equivalence between admitted proposition content and the target-context event application;
- non-negated, transitioning occurrence status;
- resolvable required participant bindings;
- satisfied or explicitly handled preconditions.

Attributed content may cross into another context only through explicit epistemic admission. Matching record IDs or metadata are not sufficient.

### 14.4 Preview and proof

Preview must be non-mutating and produce either:

```text
TransitionPreview
  -> StateDelta candidates
  -> TransitionProof
```

or explicit blocked reasons/frontiers.

Each proof must pin:

- exact event occurrence;
- exact transition-contract revision;
- exact epistemic-admission revisions;
- exact pre-transition state-assignment revisions used by conditions;
- condition evidence;
- exact derived delta refs;
- target context;
- resolved effective time;
- evidence/provenance.

Unresolved semantic time references must remain frontiers until a concrete timeline timestamp is explicitly resolved; they must never be parsed by naming convention.

### 14.5 State timeline rules

- state assignments are revisioned/interval-based, never destructively overwritten;
- exclusivity/order/domain/holder applicability comes from StateDimension/StateValue schemas;
- scalar direction requires an ordered domain and explicit target semantics; the kernel does not infer arithmetic from labels;
- defaults are never transition effects;
- every committed delta must be reproducible from its exact reviewed contract effect and pre-state proof.

### 14.6 Capability dependency rules

Capabilities are reevaluated through separate generic dependency records after projected state changes.

- an event contract must not directly encode named capability mutations;
- a capability dependency targets exact action/type/state schema revisions;
- unavailable/blocked/conditional/available changes remain distinguishable;
- function semantics remain independent of current capability.

### 14.7 Atomic commit

The effect commit must use one snapshot-pinned/CAS GraphPatch containing all authorized records required for the transition, including proof, deltas, immutable timeline revisions, and capability reevaluation.

A stale snapshot, changed boot/overlay fingerprint, missing revision, retracted admission, altered pre-state, forged delta, or dependency mismatch must reject the commit rather than recompute silently.

### 14.8 Deliberate Phase-11 boundary

Phase 11 does **not** fabricate genericity that the data model cannot yet express.

- relation/role lifecycle effects require first-class generic lifecycle/delta records before activation;
- causal chaining is not inferred from sequence;
- impact/importance remains a later assessment stage;
- no domain transition contracts are seeded into the structural foundation merely for demonstrations;
- runtime cutover remains separate from phase implementation.

### 14.9 Exit gate

Phase 11 passes only when synthetic/adversarial reviewed contracts prove that:

- the same kernel executes multiple structurally different transitions without named branches;
- non-occurring/negated/unadmitted/context-isolated events cannot mutate state;
- preview is non-mutating;
- proofs pin exact authority/pre-state revisions;
- forged effects fail commit validation;
- stale plans fail CAS;
- state history remains immutable/queryable;
- capability effects arise only through separate dependencies;
- restart reproduces committed records;
- canonical foundation contains zero convenience domain transition seed.

---

## 15. Phase 12 — Cross-domain transition vertical-slice proof

### Objective

Prove that Phases 2–11 form a reusable learning-first transition architecture by running several independently reviewed **domain packages** through the same kernel with zero new semantic control-flow branches.

Phase 12 is a proof program, not a new kernel ontology.

### 15.1 Package selection

Select multiple unrelated promoted/test-only packages whose transition structures exercise different generic phenomena, such as:

- irreversible terminal state change;
- reversible activation/deactivation or restoration;
- ordered/scalar/resource state change;
- externally caused localization/movement;
- capability changes that depend on resulting state;
- polysemous surface forms that resolve to different schemas by type/context.

The package names and lexical forms are deliberately **not specified here**. They must be replaceable without kernel changes.

### 15.2 Required contrast matrix

For every applicable package, test contrasts covering:

- admitted positive actual occurrence;
- truth negation;
- possibility/modality;
- prevented/failed/non-occurring event;
- hypothetical/counterfactual content;
- attributed report not admitted to target context;
- fictional/simulated context isolation;
- ambiguous/polysemous lexicalization;
- stale/retracted admission;
- conflicting pre-state;
- restart after commit;
- correction/retraction and invalidation.

### 15.3 Cross-domain invariants

The slice must prove:

- no new kernel branch or enum was added for any package;
- no package relies on semantic-key/name inspection;
- all effects originate from reviewed contracts;
- all context crossing is epistemically explicit;
- the same transition compiler/preview/validator/projector/commit coordinator executes every package;
- capabilities change only through dependency records;
- historical identity and state remain queryable after terminal/irreversible transitions;
- external movement is not conflated with self-initiated capability;
- truth polarity, occurrence, change direction, capability status, valence, and importance remain orthogonal;
- impact is assessed later from committed/proposed consequences and stakeholder context, never baked into transition semantics;
- equivalent UOL across language packages yields equivalent transition semantics.

### 15.4 Relation/role effects gate

A vertical slice that requires ending/creating a relation or role may only activate after a generic relation/role lifecycle/delta representation is specified, implemented, validated, persisted, and proof-bound. Until then, the slice must expose an explicit frontier rather than use a custom helper.

### 15.5 Exit gate

Phase 12 passes only when at least three structurally distinct packages satisfy the full path:

```text
form evidence
-> grounding
-> UOL composition
-> claim/epistemic placement where applicable
-> independently admitted event
-> generic transition preview
-> proof-bearing atomic commit
-> state/capability projection
-> restart/re-query
```

with zero package-specific kernel edits.

A detailed executable test matrix is maintained in `docs/implementation/v350-phase-12-plan.md` rather than encoding domain concepts in this root plan.

---

## 16. Phase 13 — Learning-first promotion coordinator

### Objective

Turn unresolved frontiers and repeated evidence into reviewable/promotable semantic packages without making examples into definitions automatically.

### Required capabilities

- package families for referent/type/facet/property/state/action-event/relation-role/rule/lexical/realization/response-policy knowledge;
- exact dependencies and frontier nodes;
- examples and counterexamples;
- recursive learning limits;
- independent competence tests;
- per-use activation;
- promotion/retraction/supersession;
- restart rehydration and invalidation.

### Exit gate

A newly promoted semantic structure survives restart and participates only in uses independently authorized by its competence evidence.

---

## 17. Phase 14 — Impact, importance, and stakeholder assessment

### Objective

Assess consequences without conflating them with event truth or transition semantics.

### Required capabilities

- stakeholder resolution;
- proof-bearing impact rules/assessments;
- importance/significance evidence collection;
- goal/relation/history/affective/risk/irreversibility evidence with privacy scope;
- contradiction and uncertainty;
- durable versus transient significance separated.

### Exit gate

Assessments remain stakeholder/context relative and cannot create or rewrite state facts.

---

## 18. Phase 15 — Goals, obligations, and semantic response policy

### Objective

Generate and arbitrate goals from semantic obligations rather than surface intent labels.

### Required capabilities

- answer/act/learn/clarify/qualify/acknowledge/warn/support/silence classes represented through semantic policy data;
- target-bearing obligations;
- provenance and literal-policy overrides;
- conflict arbitration, repetition cost, social/risk constraints;
- no generic targetless acknowledgement.

### Exit gate

Every selected response/action goal has a semantic target, reason, policy basis, and authorization trace.

---

## 19. Phase 16 — Response UOL planner

### Objective

Build proof-carrying response meaning graphs before any target-language realization.

### Required capabilities

- query closure;
- perspective transformation;
- state/property/event/capability reporting;
- qualification and uncertainty;
- impact-sensitive discourse acts;
- exact repair/learning questions;
- aggregation, ordering, and omission under authorization constraints.

### Exit gate

Response UOL contains all and only authorized meaning, with no target-language wording embedded as semantic authority.

---

## 20. Phase 17 — Multilingual realization algebra

### Objective

Realize Response UOL through language-package grammar/morphology rather than predicate-specific sentences.

### Required capabilities

- deep clause plans;
- data-driven argument frames;
- feature unification;
- reference generation;
- modality/negation/tense/aspect/scope;
- coordination;
- morphology and linearization;
- semantic round-trip verification;
- language packages independently reviewable and replaceable.

### Prohibition

Adding a new domain schema must not require adding a full sentence template.

### Exit gate

Shared semantic competence cases round-trip across multiple reviewed language packages without semantic drift.

---

## 21. Phase 18 — Output discourse and common-ground authority

### Objective

Make system output semantically referable and auditable.

### Required capabilities

- persist emitted output UOL, targets, reasons, commitments, policy refs, realization evidence, and permissions;
- update common ground only after emission authorization;
- allow later reference to prior system propositions/events/targets;
- corrections invalidate dependent common-ground projections.

### Exit gate

Follow-up references can resolve against semantic output history without transcript-string hacks.

---

## 22. Phase 19 — Migration and semantic equivalence

### Objective

Migrate retained useful legacy data without migrating legacy authority or semantic shortcuts.

### Required capabilities

- explicit source→target ref map;
- rejected/quarantined records with reasons;
- semantic-equivalence report;
- rollback database;
- learned schemas/rules/referents/knowledge/states/aliases/operations/language data migrated only when representable under v3.5 contracts;
- no migration adapter remains a permanent competing authority.

### Exit gate

Migrated state is explainable, reversible, and behaviorally equivalent where equivalence is claimed.

---

## 23. Phase 20 — Runtime cutover and legacy authority removal

### Objective

Make the v3.5 core loop the sole public semantic authority and physically remove or isolate superseded legacy paths.

### Required removals

- direct word/pattern-to-semantic shortcuts;
- per-predicate response sentences;
- generic targetless response moves;
- event-specific mutation helpers;
- mutable monolithic semantic state blobs;
- input-only discourse commit shortcuts;
- source-code semantic type expansion requirements;
- legacy assemblers/routers that can bypass v3.5 grounding/composition/epistemics/transitions.

### Exit gate

No public runtime request can reach a removed legacy semantic authority path.

---

## 24. Final verification program

Run on a complete repository/runtime environment:

- architecture/data lints and legacy-debt ratchet;
- all unit and integration tests;
- declarative semantic competence;
- Stage-0 through output end-to-end traces;
- multilingual semantic equivalence and NLG round-trip;
- epistemic contradiction/correction/retraction;
- transition and restart/history tests;
- learning/promotion/restart tests;
- multimodal grounding;
- long-session/common-ground/significance tests;
- migration and rollback;
- permission/privacy/security boundaries;
- adversarial stale-revision/context-leakage/forged-proof tests;
- performance/memory/database/query-plan budgets.

---

## 25. Definition of v3.5 completion

v3.5 is complete only when a newly learned/promoted semantic structure can, without new kernel semantic branches:

1. be grounded from one or more evidence modalities;
2. inherit/project applicable facets;
3. constrain composition by exact schema contracts;
4. participate in attributed claims without automatic fact admission;
5. be independently admitted or opposed with proof;
6. drive generic event/state transitions when separately transition-authorized;
7. alter dependent capabilities through generic dependency records;
8. support inference and contextual assessment;
9. influence semantic goals/responses;
10. be queried and explained with lineage;
11. be realized through multiple language packages;
12. survive restart and migration;
13. be corrected/retracted/superseded with dependent invalidation;
14. preserve uncertainty/frontiers when knowledge is insufficient;
15. do all of the above without a source-code ontology edit, named event-effect branch, semantic word regex, or ordinary full-sentence template.
