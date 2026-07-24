# CEMM v3.5 — Comprehensive Productive Semantic Activation Remediation Plan

**Baseline reviewed:** `e762d04e867532c3ecc9dc9efb17ad8222810295` (`Final full activation patch`)  
**Scope:** repair semantic foundations after runtime cutover without phrase shortcuts, hidden verifier exemptions, predicate catalogues, or source-code ontology growth.

---

# 0. Executive diagnosis

The v3.5 public runtime cutover is structurally real, but semantic activation remains incomplete.

The current implementation still contains a residual architecture shaped roughly like:

```text
surface form
→ one lexical sense target
→ one fixed construction output
→ application-oriented retrieval
→ predicate-specific response policy/transform
```

The required architecture is:

```text
observation
→ form/morpheme
→ lexeme/form family
→ one or more semantic contributions
→ open variables/restrictions/projections/features
→ construction graph constraints
→ participant/referent grounding
→ referent knowledge/entitlement closure
→ bounded joint meaning solve
→ semantic query/claim/event/state classification
→ universal semantic binding/inference/transition
→ generic goals/Response UOL
→ multilingual realization
```

The repair must therefore proceed from the substrate outward.

---

# 1. Gap register

## G1 — contradictory root governance

`AGENTS.md` and `README.md` still describe v3.5 as not authoritative / v3.4.7 as the executable baseline although public runtime authority has cut over.

**Risk:** future agents reintroduce migration authority or optimize against stale contracts.

## G2 — lexical sense forced toward one target

`LexicalSenseRecord` is target-centric.

Function words, auxiliaries, interrogatives and grammatical morphemes often contribute constraints rather than one completed schema.

## G3 — exact form→sense authority

The registry indexes direct form-sense links.

`variant_of_ref` does not create true semantic inheritance.

**Effect:** inflection/allomorphy duplicates semantic authority.

## G4 — no durable lexeme/form-family layer

There is no authoritative entity grouping `be/am/is/are/was/were/...` or equivalent morphological families while preserving distinct grammatical features.

## G5 — no durable semantic-contribution specification

The runtime has no reviewed data record saying that one sense contributes a variable, restriction, projection, referential role, scope and/or target.

## G6 — WH/interrogative collapse

Activation language data tends to map `how/when/where/which/who/why` toward one generic query/ask sense.

Distinct answer projections are lost.

## G7 — information-gap/discourse/response conflation

`query`, `ask`, and response obligation are insufficiently separated.

Embedded interrogatives expose the defect.

## G8 — generic partial gaps are under-typed

`SemanticVariable` has some restriction/projection fields but runtime materialization mostly emits bare `PARTIAL_COMPOSITION` gaps.

Expected filler classes and explicit purpose are not preserved strongly enough.

## G9 — operator materialization assumes unary scope

Current lexical operator materialization handles one local operand port cleanly.

Documented UOL requires multi-port structures such as:

```text
ability(holder, action)
query(variable, restriction)
```

## G10 — constructions map too directly to one output schema

The current `ConstructionRecord` cannot express a general graph-building semantic program required for predication, auxiliaries, interrogatives and modifiers.

## G11 — `interpretation_enabled` metadata is hidden authority

The matcher skips constructions through untyped metadata.

Phase-20 tests encode interpretation disablement as success.

## G12 — grammar/semantics categories are conflated

Adjective/adverb-like intuitions risk becoming semantic atoms.

The architecture needs explicit qualitative projection rules.

## G13 — state/process/event/action distinction is incomplete

State/action/event exist structurally but process/activity semantics are not explicitly closed.

This encourages BE/auxiliary mis-modeling.

## G14 — ParticipantFrame not fully authoritative for ordinary text deixis

The hardened runtime constructs the participant frame, but text grounding must consume it generically for speaker/addressee lexical roles.

## G15 — Stage-4→5 knowledge binding is too weak

The hardened binder exists, but compatibility remains too span-centric and primarily filtering.

Referent knowledge must generate compatible closures through semantic ports.

## G16 — Stage 10 is storage-shape oriented

`SemanticRetriever` primarily searches semantic applications.

Queries must bind over state, capability, identity, type, events, time/place, quantities and epistemic knowledge.

## G17 — self runtime state is under-grounded

Boot defaults correctly remain non-factual, but current self operational/capability/language/memory/channel state needs evidence-backed runtime projection.

## G18 — capability query closure incomplete

Self capabilities may exist but generic queries cannot reliably bind them and generate generic response meaning.

## G19 — response cognition remains predicate-catalogue shaped

Many response policy/transform records are enumerated per schema.

New learned predicates do not automatically become answerable.

## G20 — learning frontiers too generic

Unresolved lexical, construction, query, state, transition, realization and response gaps need distinct typed frontier contracts.

## G21 — learning runtime cutover incomplete

Induction/promotion/rehydration are not fully closed through the canonical runtime.

## G22 — activation/conversation seeds contain migration drift

Phrase-like aliases, direct query mappings and catalogue closure were added to make activation structurally complete.

These must be rebuilt only after the substrate is productive.

## G23 — regression tests freeze catalogue shapes

Exact counts of policies/transforms/frames/senses and interpretation-disablement assertions reward the wrong implementation.

## G24 — release tests insufficiently synthetic

Real demo examples can accidentally become implementation authority.

Synthetic renamed vocabulary and data-only extensions are needed.

## G25 — acquisition/consolidation can regress into a terminal stage

Learning must remain a co-equal acquisition spine. Frontiers can originate anywhere in analysis/grounding/query/transition/realization/response; induction, competence, promotion, compression, invalidation and rehydration must remain connected and bounded.

## G26 — working graph and durable memory can collapse

Temporary ambiguity-rich UOL/meaning graphs must not be written as transcript memory. Durable writes require compression into reusable concepts, lexemes/aliases, schemas, ports, constructions, transition/causal knowledge, source/permission policies, state/history and compact competence evidence.

## G27 — ordering/safety invariants can be lost in semantic refactors

Every phase must preserve: perceive before answer; source before belief; time before current state; permission before learning; safety before realization/emission; and commit before self-claim of write/state change.

## G28 — input morphology is not productively closed

Current morphology authority is realization-oriented. Known surface variants can be linked to lexemes, but unseen inflection/affix/clitic/zero-morpheme analysis is not yet a reviewed productive semantic input path. Input morphology must become reversible language evidence with feature unification; it must not be implemented as English regex semantics in the kernel.

---

# 2. Foundational atom decision

## 2.1 Kernel-native structural primitives

Hard-code only execution categories:

```text
referent/identity
type/inheritance
application
variable
port/binding/filler
property
state dimension/value
relation
role
eventuality representation
action/control
event occurrence
quantity/measure/unit
time
place/localization
operator/scope
proposition/claim/evidence/knowledge
query/information gap
coordination
capability/affordance/function
transition/delta/dependency
context/permission/provenance
goal/operation/response
learning/frontier/promotion/invalidation
```

## 2.2 Data-native foundational axes

Seed reviewed data for:

```text
identity/sameness/difference
classification
existence
applicability/activation
persistence/change
polarity/modality
occurrence/aspect
temporal/localization relations
quantity/order/degree
cause/enable/prevent
agency/control/affectedness
containment/mereology/possession
capability status
epistemic status/source
query answer projection
uncertainty/default expectation
valence/significance
```

## 2.3 Derived meanings

### Manner

Eventuality/process characterization projection.

### Degree

Ordered/scalar/measure projection.

### Method

Means/procedure/causal-enabling structure.

### Availability/connectivity

Type-entitled state dimensions.

### Adjective/adverb

Language categories only.

---

# 3. Phase 0 — Root authority replacement

## Goal

Make future implementation agents converge on one semantic architecture before code changes.

## Replace

- `AGENTS.md`
- `ARCHITECTURE.md`
- `CORE_LOOP.md`
- `README.md`

## Add/align

- `docs/architecture/FOUNDATIONAL_SEMANTIC_ALGEBRA.md`
- this `phased-fixes.md`
- `ACCEPTANCE_CONTRACT.md` productivity sections

## Exit

No active root document:

- calls v3.4.7 runtime authority;
- calls v3.5 “not implemented” globally;
- omits semantic contributions/lexemes/query separation;
- permits phrase-based regression fixes.

---

# 4. Phase 1 — Semantic contribution substrate and test reset

## Goal

Make “understanding a known unit” mean preserving its smallest justified semantic contribution.

## P1.1 Cycle-local contribution model

Add structural contribution kinds:

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

Add immutable `SemanticContribution`.

## P1.2 Rich semantic variables

Extend `SemanticVariable` with:

```text
expected_filler_classes
open_binding_purpose
```

Preserve existing:

```text
expected_schema_classes
expected_type_refs
restriction_refs
projection_ref
scope/evidence
```

Update codec round-trip.

## P1.3 Contribution lineage

Carry contribution refs through:

- SenseCandidate;
- factor graph meaning values;
- materialized applications/variables;
- trace/debug artifacts.

Known evidence may not silently disappear.

## P1.4 Legacy contribution compiler

Until durable contribution specs are present, compile the existing typed lexical sense fields into explicit cycle contributions.

No surface-string checks.

Mark the path:

```text
authority_path=legacy_lexical_sense
```

## P1.5 Regression-test quarantine

Delete/replace tests that assert:

- exact response-policy count;
- exact transform count;
- exact argument-frame count;
- exact realization-sense count;
- blanket `interpretation_enabled=false`;
- final verifier must fail after activation.

Keep:

- duplicate IDs;
- boot integrity;
- foreign keys;
- authority graph;
- deterministic compilation;
- revision/CAS;
- proof lineage.

## P1.6 Synthetic productivity tests

Use arbitrary language tag/forms.

Assert:

- recognized form emits contribution(s);
- surface rename preserves semantic target authority;
- grammar features remain separate;
- typed variables round-trip;
- no contribution silently vanishes.

## Exit

A recognized unit is auditable as semantic contributions even if final meaning remains partial. The working graph remains temporary/ambiguity-preserving, and no Phase-1 tracing structure becomes durable transcript memory.

---

# 5. Phase 2 — Durable lexeme/form-family and contribution authority

## Goal

Remove direct exact-form semantics as the target language architecture while preserving signed-boot compatibility.

## P2.1 New durable record kinds

Add:

```text
LEXEME
FORM_LEXEME_LINK
LEXEME_SENSE_LINK
SEMANTIC_CONTRIBUTION_SPEC
```

### LexemeRecord

```text
lexeme_ref
pack_ref/revision
lemma_form_ref/revision
lexical_category
inflection_class_ref
feature_defaults
lifecycle/provenance/competence
```

### FormLexemeLinkRecord

```text
form_ref/revision
lexeme_ref/revision
relation_kind:
  lemma
  inflected
  suppletive
  clitic
  derived
  zero
feature_values
conditions
prior_weight
```

### LexemeSenseLinkRecord

Many-to-many lexeme/sense relation with priors/conditions.

### SemanticContributionSpecRecord

Durable reviewed specification for one contribution:

```text
sense_ref/revision
kind
target kind/ref/revision/class
expected filler/schema/type constraints
open binding purpose
restriction refs
projection ref
role ref
scope behavior
feature constraints
use operation/decision
lifecycle/provenance/competence
```

## P2.2 Targetless lexical senses

Permit a lexical sense whose meaning is entirely expressed by contribution specs.

Registry validation requires an active allowed contribution path before such a sense is usable.

This avoids placeholder semantic targets for pure grammatical/query contributions.

## P2.3 Registry authority

Index:

```text
form -> lexeme links
lexeme -> sense links
sense -> contribution specs
```

New authority precedence:

```text
if active lexeme path exists:
    use it
else:
    use legacy direct form-sense path and mark compatibility
```

Never merge the two silently.

## P2.4 Analyzer

Lattice becomes:

```text
OBSERVATION
→ FORM
→ LEXEME
→ SENSE
→ CONTRIBUTION
→ CONSTRUCTION
```

Add lexeme candidates and lineage edges.

Form-specific grammatical features from `FormLexemeLink` are preserved separately from semantic contribution specs.

## P2.5 Persistence

Add:

- RecordKind values;
- codecs;
- record-ref/revision/lifecycle support;
- typed repositories;
- registry snapshot/caching;
- GraphPatch compatibility;
- learning package eligibility.

Existing boot records remain decodable without fingerprint changes.

## P2.6 Form-family competence test

Synthetic forms:

```text
za
zi
```

share one lexeme and one sense without direct form-sense links.

Each form supplies different grammatical features.

Assert:

- same lexical semantic authority;
- different grammatical feature contribution;
- exact evidence/record pins;
- no direct-form semantic branch.

## P2.7 Explicit contribution competence

A targetless synthetic lexical sense with:

- VARIABLE;
- PROJECTION;
- RESTRICTION

must be usable through active contribution specs.

No dummy target.

## P2.8 Legacy compatibility test

Existing direct form-sense data remains readable and trace-marked `legacy_form_sense`.

New lexeme authority takes precedence when both are present.

## P2.9 Scope boundary

Phase 2 closes durable lexeme identity, known inflection/allomorph/suppletion relationships, reversible form variants, and semantic-contribution authority. It does **not** claim productive analysis of unseen morphological forms. That separate gap is closed with the grammar/morphology analysis machinery in Phase 3.

## Exit

Known inflected/suppletive forms can share one lexical semantic authority while retaining grammatical differences, and lexical meaning can consist of multiple durable contribution specs.

---

# 6. Phase 3 — Predication, eventuality and semantic construction programs

## Goal

Make grammar compose graph fragments rather than fixed predicates.

### P3.1 Eventuality contract

Specify/test:

```text
state
process/activity
event/transition
action/control
```

Decide whether process requires a schema class only after proving event/aspect representation limits.

### P3.2 Predication

Reusable predication supports:

- state;
- property;
- classification;
- identity/equative;
- localization;
- relation.

### P3.3 Auxiliaries

BE-like lexical families contribute structural/grammatical evidence for:

- copula;
- progressive;
- passive;
- existential.

No direct `becoming` mapping.

### P3.4 Productive input morphology

Add reviewed, reversible morphology-analysis authority for:

- affixation;
- clitics;
- zero morphemes;
- inflection classes;
- feature unification;
- irregular/suppletive overrides;
- morphologically encoded tense/aspect/modality/case/agreement.

The kernel executes generic morphology operations. Language packages supply rules/data. No surface-word or English-regex semantic routing.

### P3.5 Construction program algebra

Implement bounded operations:

```text
INTRODUCE_VARIABLE
INSTANTIATE_SCHEMA
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

### P3.6 Remove hidden interpretation switch

Replace `metadata.interpretation_enabled` with first-class per-use authority.

## Exit

Synthetic renamed copular/process constructions compose without phrase records or external parser authority.

---

# 7. Phase 4 — Participant grounding and referent-driven closure

## Goal

Make referent identity and entitlement materially constrain meaning.

### P4.1 ParticipantFrame bridge

Create grounding anchors from authoritative participant roles.

### P4.2 Deictic contribution grounding

Map semantic roles, not words:

```text
speaker
addressee
demonstrative
prior-output
```

### P4.3 Replace span coupling

Redesign Stage-4→5 binding through semantic ports/application structure.

### P4.4 Candidate generation from referent knowledge

Open state/property/capability variables can receive candidate schemas/values from the grounded referent's knowledge view.

## Exit

Changing only referent type changes possible semantic closure.

---

# 8. Phase 5 — Typed interrogatives and universal query binder

## Goal

Make information gaps compositional.

### P5.1 Answer projection schemas/data

Support projection families such as:

- identity/referent;
- localization;
- temporal;
- cause/reason;
- qualitative condition;
- manner;
- degree;
- means/procedure;
- quantity;
- truth/status.

### P5.2 Matrix vs embedded query

Same WH contribution works in embedded and matrix structures.

Only discourse structure adds `ask`.

### P5.3 Universal Stage-10 binder

Bind restriction graphs over:

- referent projection;
- properties/states;
- capabilities;
- identity/types;
- relations/roles;
- events;
- propositions/knowledge;
- time/place/quantity/proof.

## Exit

Synthetic `how`-like and `what`-like constructions query multiple semantic families without word-specific code.

---

# 9. Phase 6 — Runtime-backed self state/capability truth

## Goal

Make CEMM's self-description evidence-backed and dynamic.

Observe/project:

- operational status;
- language competence;
- semantic store access;
- learning capability;
- channel/response capability;
- connectivity where actually evidenced/applicable;
- resource/dependency state.

Do not turn defaults into facts.

Audit overbroad foundation state applicability, especially `availability`.

## Exit

Changing runtime evidence changes semantic self-query results without transcript/template changes.

---

# 10. Phase 7 — Generic response cognition

## Goal

Remove predicate-catalogue answer behavior.

Introduce structural policies/transforms:

```text
answer_bound_query
report_value
report_state
report_set
report_event
report_capability
describe_projection
qualify_status
clarify_missing_binding
```

Migrate per-predicate rules where generic semantics cover them.

## Exit

Add a new state/action/capability as data and answer it without new Python or predicate-specific response transform.

---

# 11. Phase 8 — Typed learning frontier and runtime cutover

## Goal

Make missing competence learnable end-to-end.

Typed frontiers feed:

```text
observation
→ candidate induction
→ package assembly
→ structural validation
→ competence cases
→ promotion decision
→ durable commit
→ registry rehydration
→ dependency invalidation/replay
```

Promotion remains use-axis specific.

Set learning runtime cutover only after restart tests.

## Exit

Teach a nonce concept/language structure, restart, and reuse it without code changes.

---

# 12. Phase 9 — Seed migration and multilingual nucleus rebuild

## Goal

Replace activation-era phrase/catalogue drift with minimal productive EN/FR/SW authority.

Migrate:

- forms → lexemes;
- direct form-sense links → lexeme/sense authority;
- query words → contribution specs;
- morphology/allomorph features;
- reusable constructions;
- generic realization frames.

Remove ordinary phrase aliases.

Rebuild boot and signed manifest deterministically.

## Exit

English/French/Swahili equivalent UOL cases work from reusable components.

---

# 13. Phase 10 — Final semantic activation verification

Release matrix:

### Atomic contribution

Every recognized form has traceable contribution or explicit compatibility path.

### Morphology/form family

Multiple forms share lexeme semantics with correct features.

### Predication

State/property/classification/localization/process contrasts.

### Interrogatives

Matrix vs embedded; who/where/when/why/how/what projection differences.

### Referent closure

Same grammar, different referent types -> different compatible semantics.

### Universal queries

State/capability/identity/time/place/event/quantity.

### Self

Runtime state/capability changes reflected truthfully.

### Learning

Nonce teach/promote/restart/invalidate.

### Response productivity

New predicate/state/action requires no predicate-specific response code.

### Multilingual

Equivalent UOL across EN/FR/SW shared cases.

### Original demo

Must improve for architectural reasons only.

---

# 14. Phase 1+2 patch acceptance checklist

The combined Phase 1+2 patch is acceptable only if:

- [ ] root docs are replaced first;
- [ ] new durable language records do not change existing boot record fingerprints;
- [ ] codecs round-trip new records;
- [ ] GraphPatch/store accepts new record kinds;
- [ ] registry validates exact cross-record revisions;
- [ ] analyzer prefers new lexeme authority;
- [ ] legacy fallback is explicit in trace metadata;
- [ ] targetless lexical sense is allowed only with active contribution authority;
- [ ] contribution specs support multiple contributions per sense;
- [ ] form-specific grammar features remain separate from semantics;
- [ ] SemanticVariable preserves filler/purpose/restriction/projection;
- [ ] synthetic lexeme tests do not use English words;
- [ ] catalogue-count/interpretation-disablement regression tests are removed/replaced;
- [ ] no phrase-specific fix is introduced;
- [ ] no external parser becomes semantic authority;
- [ ] skipped end-to-end tests are reported honestly.

---

# 15. Files expected to change in Phase 1+2

Core:

```text
cemm/v350/language/model.py
cemm/v350/language/codec.py
cemm/v350/language/registry.py
cemm/v350/language/analyzer.py
cemm/v350/composition/builder.py
cemm/v350/composition/materializer.py
cemm/v350/uol/model.py
cemm/v350/uol/codec.py
cemm/v350/storage/model.py
cemm/v350/storage/codec.py
cemm/v350/storage/repositories.py
```

Tests:

```text
tests/v350/test_phase1_2_semantic_substrate.py
tests/v350/test_conversation_seed_boot.py
tests/v350/test_phase20_final_activation.py
tests/v350/test_phase7_language.py
```

Docs:

```text
AGENTS.md
ARCHITECTURE.md
CORE_LOOP.md
README.md
docs/architecture/FOUNDATIONAL_SEMANTIC_ALGEBRA.md
phased-fixes.md
ACCEPTANCE_CONTRACT.md
```

No Phase 1+2 patch should add English phrase-specific semantic seed data.
