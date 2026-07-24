# CEMM v3.4.7 Authority Audit for the v3.5 Cutover

**Baseline commit:** `bcc77fdf1af7a735e173e873c9fd0585c5bbb80f`
**Executable package version:** `3.4.7`
**Audit role:** Phase 0 prerequisite for v3.5 implementation
**Status:** static authority audit completed; runtime performance measurement remains a repository-CI task because the review environment cannot clone or execute the full repository.

---

## 1. Audit conclusion

v3.4.7 contains several foundations worth preserving:

- one `Referent` record family;
- cycle-local UOL-like structures;
- a central SQLite `SemanticStore`;
- GraphPatch-only public mutation;
- compare-and-swap store revisions;
- source/evidence lineage;
- schema and rule revision tables;
- correction, retraction, invalidation, and restart hydration;
- operation and emission ledgers;
- multilingual language packages.

It is not an incremental implementation base for v3.5 semantic authority. Its executable meaning remains organized around:

- a broad source-code `ReferentKind` ontology;
- predicate-centred schemas and learned-predicate promotion;
- kind-based local-port compatibility;
- a monolithic foundation package;
- assertion-to-supported-knowledge admission;
- `Predication` rather than general `SemanticApplication`;
- mutable/opaque world-track state blobs;
- sentence-level predicate answer templates;
- incomplete system-output discourse persistence;
- no generic event-transition/state/capability/impact substrate.

The correct migration strategy is **parallel v3.5 authorities followed by deliberate cutover**, not continued patching of v3.4.7 classes.

---

## 2. Pinned executable composition root

The public package exports `cemm.v347.version.VERSION`, and `Runtime` is the v3.4.7 composition root.

Static runtime order:

```text
PackageLoader
→ FoundationPackage + LanguagePack[]
→ SemanticSchemaStore
→ SemanticStore
→ foundation GraphPatch bootstrap
→ learned-candidate/revision hydration
→ LanguageAnalysisCoordinator
→ ObservationFusionCoordinator
→ ContextCoordinator
→ ReferentCandidateGenerator
→ SchemaLifecycleCoordinator
→ UnderstandingCoordinator
→ EpistemicCoordinator
→ TruthMaintenanceCoordinator
→ LearningCoordinator
→ BoundedInferenceEngine
→ goal / operation pipeline
→ response-goal generation and ranking
→ UOLResponsePlanner
→ RealizationCoordinator
→ emission ledger
→ DiscoursePatchCompiler
```

Cycle write order:

```text
world observations
→ evidence
→ admitted input propositions/knowledge
→ learning candidates
→ truth assessments
→ inferred knowledge
→ operation effects
→ operation ledger
→ emission ledger
→ input discourse turn
```

This differs materially from the v3.5 core loop. In particular, claim compilation, context placement, event admission, transition preview, state/capability commit, impact, importance, and output common-ground commit are not separate authorities.

---

## 3. Durable write authority

### 3.1 Preservable foundation

`SemanticStore.apply_patch()` is the central public mutation authority.

It provides:

- SQLite transaction boundary;
- monotonically increasing store revision;
- expected-revision compare-and-swap;
- idempotent patch identity;
- operation validation;
- patch ledger;
- immutable record reconstruction on reads.

This should inform the Phase 4 v3.5 store and GraphPatch coordinator.

### 3.2 Write producers

The runtime compiles or applies patches for:

| Producer | Durable output |
|---|---|
| foundation bootstrap | referents, aliases, predicates/propositions/knowledge |
| observation fusion | evidence records |
| world observation compiler | world tracks |
| epistemic coordinator | referents, predications, propositions, supported knowledge, aliases, supersession/invalidation |
| learning coordinator | schema/rule candidates |
| truth maintenance | truth assessments |
| inference engine | inferred propositions/knowledge and dependencies |
| outcome reconciler | operation effect patches |
| operation ledger compiler | operation ledger |
| emission ledger compiler | emission ledger |
| discourse compiler | user turn, mentions, open questions |
| candidate promotion | schema/rule revisions and dependencies |

No direct SQL outside `SemanticStore` was found in the active compact v3.4.7 package. This is a migration asset.

### 3.3 Authority mismatch

GraphPatch is generic at the operation envelope, but its operation taxonomy is still v3.4.7-shaped. It has no normalized v3.5 operations for:

- semantic applications;
- referent-type assertions;
- facet entitlements;
- claim occurrences;
- event occurrences;
- state assignments/timelines;
- proof-bearing state deltas;
- capability instances/deltas;
- impact/importance assessments;
- response UOL/common-ground records.

Phase 4 must extend or replace the operation taxonomy without allowing direct store writes.

---

## 4. Semantic object and type authority

### 4.1 Referent

`Referent` is already the only ordinary identity-bearing filler record. Preserve this law.

Current fields:

```text
referent_id
kind: ReferentKind
type_refs
payload
scope_ref
context_ref
provenance
revision
metadata
```

### 4.2 Broad `ReferentKind` ontology

The enum includes semantic categories such as:

```text
self
agent
person
animal
organization
software_agent
physical_object
digital_object
place
event
process
state
proposition
quantity
unit
time
collection
information_object
context
schema
text
unknown
```

This is not merely a storage discriminator. It is executable authority because:

- `PortSchema.accepted_kinds` constrains compatibility;
- referent candidate generation creates multiple kind-specific provisional referents;
- language/reference logic branches on kinds;
- tests assert kind-level semantic behavior;
- package data must use an enum member for each supported category.

A learned type still requires either approximation to an existing kind or a source-code enum addition.

### 4.3 Required v3.5 replacement

v3.5 must retain a small `StorageKind` only for serialization shapes and move executable type authority to revisioned `ReferentTypeSchema` data with multiple inheritance.

The v3.5 metamodel must not import `ReferentKind` or translate learned types into it.

---

## 5. Schema authority

### 5.1 Active schema model

`PredicateSchema` is the primary executable schema:

```text
schema_ref
semantic_key
ports
status
scope/revision
eventive/stateful/symmetric
inverse/supersession metadata
```

`SemanticSchemaStore` owns:

- predicates;
- predicate lookup by semantic key;
- operations;
- rules;
- candidate payloads;
- schema/rule revision payloads;
- learned predicates and rules.

### 5.2 Learned-schema limitation

`register_schema_revision()` only makes a learned revision executable when:

- its `schema_kind` is `predicate`/`predicate_schema`; and
- the payload can be decoded as a `PredicateSchema` with ports.

Therefore v3.4.7 cannot independently activate learned:

- referent types;
- facets/entitlements;
- properties versus state dimensions;
- state values;
- relations versus roles;
- functions;
- actions versus events;
- operators;
- discourse schemas;
- response policies.

They collapse into predicate records or remain inert payloads.

### 5.3 Lifecycle authority

Useful existing concepts:

- operation-specific `SchemaUseProfile`;
- structural checks;
- environment fingerprints;
- competence evidence;
- candidate/provisional/active/superseded/rejected states;
- dependency invalidation.

Gaps against v3.5:

- no `structurally_closed` or `competence_verified` lifecycle stage;
- use operations omit `mention`, `ground`, `transition`, and `impact` while adding v3.4.7-specific `recognize`/`learn`;
- profiles are derived mainly for predicate schemas;
- structural validation still requires `accepted_kinds` or direct type refs;
- parent inheritance/revision policy is absent;
- semantic content fingerprint and record/provenance fingerprint are not separated.

Phase 2 should preserve operation-specific authorization as a concept, but replace its predicate-only authority.

---

## 6. UOL authority and record migration

v3.4.7 places most UOL records in one `model.py`.

### 6.1 Directly reusable concepts

| v3.4.7 | v3.5 disposition |
|---|---|
| `Referent` | retain law; replace kind/payload authority |
| `PortBinding` | generalize to `ApplicationBinding` |
| `Predication` | replace with `SemanticApplication` |
| `UOLGraph` | replace with typed v3 graph containing variables, scopes, coordination, claims/events/deltas/assessments |
| `MeaningHypothesis` | preserve in later composition phase |
| `MeaningBundle` | preserve in later selection phase |
| `GraphPatch` | preserve mutation law; extend in Phase 4 |
| `EvidenceRef` | preserve provenance concept |
| `KnowledgeRecord` | preserve epistemic record concept, not Phase 3 cognition |
| `TruthAssessment` | preserve four-state truth concept |
| `UOLResponsePlan` | replace in Phase 16 after v3 response UOL exists |

### 6.2 Missing Phase 3 records

The active model lacks first-class:

- general semantic applications that can bind applications/variables/coordination;
- semantic variables with typed restrictions/projection;
- explicit scope relations;
- coordination group nodes;
- proposition specialization separate from generic payload maps;
- claim occurrence;
- event occurrence with occurrence status;
- state delta;
- capability delta;
- impact assessment;
- importance assessment.

### 6.3 Current filler limitation

`PortBinding` supports either:

- referent references; or
- one open variable string.

It cannot safely bind:

- a semantic application;
- a coordination group;
- typed variable records;
- explicitly quoted literal records.

Embedded proposition/event identity is possible only by representing it as a referent with an opaque payload.

---

## 7. Understanding authority and shortcuts

### 7.1 Current composition

`SchemaActivator` activates only predicate references. `JointMeaningAssembler` then:

- derives one communicative force and polarity from form evidence;
- generates candidate pools;
- binds predicate ports through `ReferentKind` and direct type refs;
- creates `Predication` records;
- wraps them in proposition referent payloads;
- ranks hypotheses and selects a bundle.

The assembler is a useful behavioral baseline, but it cannot become v3.5 authority because it has no variables for:

- schema family;
- type closure/facet entitlement;
- operator scope;
- claim/proposition relation;
- event occurrence;
- multiple contexts;
- explicit coordination nodes.

### 7.2 Fixed semantic anchors

When a fixed binding is absent from the store, the assembler creates a provisional `SCHEMA` referent. This can hide an unresolved dependency rather than proving a data-driven semantic type/application.

### 7.3 Provisional mention projection

Unknown mentions are projected as several hard-coded `ReferentKind` candidates: person, place, organization, event, physical object, and information object. v3.5 should instead use provisional type-schema candidates and storage-neutral ordinary referents.

### 7.4 Recent direct surface shortcuts

The final v3.4.7 functional patch added migration shortcuts including:

- English `how` → `predicate:has_state` with fixed operational-status dimension;
- English `do` → `predicate:capable_of`;
- greeting forms → a greeting predicate plus acknowledgement force;
- exact response moves such as `Hello.`;
- self-specific capability sentence variants.

These are useful regression evidence but prohibited as v3.5 semantic authority.

---

## 8. Claim, proposition, evidence, and actual-world admission

### 8.1 Current behavior

`EpistemicCoordinator.compile_admission_patch()` iterates selected proposition referents and admits a proposition when communicative force is `ASSERT` or `CORRECT` and all ports are closed.

It writes:

- referents;
- predications;
- proposition;
- `KnowledgeRecord(truth_status=supported)` in the supplied runtime context;
- aliases;
- supersession and dependent invalidation.

### 8.2 Strengths

- source attribution is retained;
- correction can supersede prior knowledge;
- support retraction is source-specific;
- dependent records are invalidated rather than silently deleted;
- negative propositions remain distinguishable in retrieval.

### 8.3 Critical v3.5 gap

There is no first-class claim occurrence or reported-content context between utterance and supported knowledge. A grammatical assertion is the principal admission gate.

As a result, the architecture cannot cleanly represent:

```text
John says the fox died.
```

as all of:

- John's claim occurrence;
- a proposition in John's reported context;
- evidence for—but not automatic admission of—actual-world death.

Phase 3 must make claim occurrence and proposition content separate records. Phase 10 must own actual-world admission.

---

## 9. State, event, capability, and impact authority

### 9.1 Current state representation

State is represented through ordinary predicates such as `has_state` and opaque `world_tracks.state_json` blobs. There is no normalized state-assignment/timeline authority.

### 9.2 Current event representation

Events are predicates marked `eventive` plus proposition payloads. There is no generic `EventOccurrence` record with occurrence status, participants, context, time, causes, and results.

### 9.3 Current transition behavior

There is no generic transition-contract engine and no state/capability delta records. Operation effects may produce GraphPatches, but linguistic/observed events do not flow through generic semantic transition contracts.

### 9.4 Current capabilities

Capabilities are primarily self/runtime operation observations and `capable_of` knowledge. They are not universally projected for arbitrary referents from type entitlements and state dependencies.

### 9.5 Impact and importance

There is no stakeholder-relative `ImpactAssessment` or `ImportanceAssessment` authority. Response ranking therefore cannot derive console/warn/congratulate/silence from proved effects and user-relative significance.

---

## 10. Response and realization authority

### 10.1 Current response goals

`ResponseGoalGenerator` creates answer, contradiction, acknowledgement, learning, operation-result, knowledge-limitation, admission-failure, and clarification candidates.

Several candidates carry empty `target_proposition_refs`, including contradiction disclosure, learning probes, and fallback clarification. Constraints may carry a reason or target string, but no uniform semantic target is required.

### 10.2 Sentence authority

Language packs contain:

- `predicate_answers`;
- `response_moves`;
- predicate-specific variants;
- full sentence strings.

This contradicts the v3.5 requirement that new actions/states be realizable by reusable grammar and argument frames without adding per-predicate answer sentences.

### 10.3 Output discourse deficit

The runtime commits:

- an emission ledger; then
- a discourse patch compiled from `understood.bundle`, with speaker set to the user.

The realized system response UOL is not passed to `DiscoursePatchCompiler`. Therefore system output is not stored as equivalent semantic discourse content that later turns can target with:

```text
Why?
For what?
What did you mean?
Understood what?
```

This must be corrected in Phases 16–18, and Phase 3 records must support output propositions/acts as ordinary UOL.

---

## 11. Learning authority

### 11.1 Preservable behavior

- explicit teaching is distinguished from ordinary failure;
- learning contributions remain candidates;
- unresolved grounding frontiers block activation;
- candidates survive restart;
- promotion can require competence results;
- dependencies and invalidations are durable.

### 11.2 Current limitations

- contributions are classified by a small set of seeded predicates;
- new semantic types/facets/states/events cannot enter independent typed authorities;
- schema promotion compiles only predicates;
- frontier classification depends on `ReferentKind.TEXT` versus non-text anchors;
- learning transactions are not persisted as first-class resumable transaction records;
- use activation is not independent for all v3.5 operations;
- cross-language lexicalization and semantic schema lifecycles remain coupled through package-specific paths.

---

## 12. Database shape

The active SQLite schema contains approximately these logical groups:

```text
meta / patches
referents / aliases
predications / proposition_contents / port_fillers
knowledge / truth_assessments
discourse_turns / mentions / open_questions
world_tracks
evidence_records
schema_candidates / schema_revisions
rule_candidates / rule_revisions
dependencies / invalidations
capability_observations
operation_ledger / emission_ledger
```

Important gaps relative to the v3.5 data contract:

```text
semantic_schemas + normalized typed schema-family records
schema_parents with revision policy/priority
facet entitlements
referent type assertions
semantic applications with non-referent fillers
claims and attributed contexts
event occurrences
state assignments/timelines/deltas
capability instances/dependencies/deltas
impact/importance assessments
learning transactions/contributions/frontiers
system-output discourse UOL
```

`world_tracks.state_json`, schema candidate payloads, and several metadata JSON columns are broad mutable/opaque blobs that must not become v3.5 semantic authority.

---

## 13. Tests and behavioral baseline

v3.4.7 tests prove useful infrastructure and regression behavior:

- runtime/version cutover;
- referent-only port filler assumption;
- quantity/unit distinction;
- multilingual name queries;
- coordination;
- GraphPatch CAS;
- restart persistence;
- learning candidate blocking;
- correction/supersession;
- operation authorization;
- emission proof.

They also encode v3.5-prohibited behavior:

- exact target-language output sentences;
- generic `Understood.` acknowledgement;
- broad kind-level port compatibility;
- predicate-specific answer templates.

These tests should remain migration regression evidence, not v3.5 acceptance authority.

---

## 14. Performance baseline

The source defines bounded mechanisms such as:

- maximum hypotheses;
- maximum candidates per span;
- inference wall-clock budget;
- limited recent turns/mentions/world tracks;
- SQLite indexes and WAL mode.

No trustworthy runtime latency or database-size measurement was possible in the review environment because the repository could not be cloned or executed. Phase 0 is therefore **static-complete but measurement-pending** for:

```text
cold boot time
foundation row counts
SQLite file size
single-turn stage timings
peak candidate/hypothesis counts
restart hydration time
query plans for principal retrieval paths
```

CI must capture these before v3.5 runtime cutover. The absence of measurements must not be misreported as a passing performance baseline.

---

## 15. Additional authority findings from the final code pass

### 15.1 Language evidence boundary is partly sound

`cemm/v347/language.py` largely obeys an evidence-only boundary: it emits token, lexical, structural, construction, quantity, and unresolved-span candidates without creating predications or writing memory. This machinery should inform Phase 7.

The semantic shortcut debt is primarily in language-package data and downstream activation/composition:

- English `how` is both a question operator and a direct `has_state` predicate cue;
- English `do` is both an auxiliary/copula cue and a direct `capable_of` predicate cue;
- package realization owns `predicate_answers` and response moves;
- `SchemaActivator` only activates `predicate:*` references;
- `JointMeaningAssembler` completes predications from those cues.

Therefore Phase 7 should preserve reversible form evidence while replacing direct form-to-completed-meaning mappings and predicate-only activation.

### 15.2 Proposition equivalence is incomplete

`TruthMaintenanceCoordinator.proposition_signature()` hashes predicate schemas and bound referents, but not proposition polarity directly, modality, context/world, scope, attribution, or validity time. Polarity is compared later, but the underlying signature is still insufficient for v3.5 semantic identity and cross-context comparison.

Phase 3 equivalence must include:

```text
schema revision
referents/bindings
polarity
modality and scope
context/world
time/aspect
coordination
discourse/claim structure
change and assessment axes
```

Generated local IDs and proof/evidence IDs must not define semantic equivalence.

### 15.3 Operation authorization should be preserved, effect authority should change

The v3.4.7 operation path usefully rechecks:

- live capability observations;
- permission;
- risk;
- grounded ports;
- resources;
- authorization fingerprint;
- adapter result reconciliation.

However, a completed adapter may return a raw `GraphPatch`, and the reconciler authorizes a set of patch operation kinds. In v3.5, adapters should instead return typed observed event/application/proposition records. Generic transition and epistemic authorities should derive state, capability, relation, and knowledge patches from those observations. Raw adapter-authored semantic effects must not bypass event admission and transition proof.

### 15.4 Assertion goal generation deepens admission coupling

`GoalGenerator` maps ordinary assertions to `admit_and_acknowledge_assertion`, while `EpistemicCoordinator` separately turns assertion/correction force into supported knowledge. This duplicates the assumption that grammatical assertion implies an admission obligation.

In v3.5:

- claim occurrence compilation is mandatory;
- actual-world admission is independent;
- acknowledgement is a later targeted response-goal candidate;
- no response goal may authorize epistemic admission.

---

## 16. Authority-debt ratchet

`docs/audits/v347-authority-debt.json` records maximum counts for known v3.4.7 shortcuts.

The Phase 1 lint policy is:

- v3.5 code is held to full prohibitions immediately;
- archived/v3.4.7 code is not falsely treated as already migrated;
- known legacy authority debt may decrease;
- any increase fails CI;
- no debt entry authorizes copying the shortcut into v3.5.

---

## 17. Phase implications

### Phase 1

Must add both:

1. strict v3.5 architecture lints; and
2. a ratchet preventing new v3.4.7 authority debt during migration.

### Phase 2

Must implement one typed metamodel authority with:

- revision-aware parent links;
- multiple inheritance;
- typed local ports;
- open variables for query, learning, rules, partial composition, and response planning;
- independent use profiles;
- provenance/dependencies/competence;
- semantic-content and full-record fingerprints;
- no `ReferentKind` dependency;
- no generic executable `MeaningSchema` bypass.

### Phase 3

Must implement referent-backed UOL v3 records and graph equivalence without importing v3.4.7 records.

### Phase 4+

Must preserve GraphPatch/CAS strengths while replacing the current tables and payload authorities with normalized v3.5 stores.

---

## 18. Phase 0 completion status

| Requirement | Status |
|---|---|
| pin main commit | completed |
| map executable composition root | completed |
| inventory semantic shortcuts | completed statically |
| map sentence-template authority | completed statically |
| inventory state blobs | completed statically |
| inspect claim admission | completed statically |
| identify blocking enums | completed |
| map write authority and database shape | completed statically |
| capture existing regression tests | completed statically |
| execute transcript/trace baseline | unavailable in review environment |
| record measured performance/database size | pending repository CI |

Phase 0 is sufficient to design Phases 1–3 accurately, but the release must retain the two pending measurements as explicit gates.
