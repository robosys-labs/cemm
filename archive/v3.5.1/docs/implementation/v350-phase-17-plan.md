# CEMM v3.5 Phase 17 — Multilingual Realization Algebra

## 1. Objective

Realize authorized Phase-16 Response UOL into target-language surface text using **reviewed/revisioned language packages**, not predicate-specific sentence templates or English-centric regex/control flow.

The realization layer is a compiler:

```text
Response UOL
-> discourse/clause planning
-> semantic argument frames
-> syntactic feature structures
-> reference plans
-> morphology/agreement
-> linearization
-> surface candidate(s)
-> semantic round-trip verification
```

It is not a second reasoning engine and may not invent facts, goals, impacts, certainty, relationships or emotional stance.

---

## 2. Governing laws

1. Meaning schemas contain no target-language surface strings.
2. Adding a domain schema must not require adding a full-sentence template.
3. Lexicalization and construction records are evidence/grammar data, independently revisioned and promoted per use.
4. `REALIZE` authority is independent from `GROUND`/`COMPOSE` authority.
5. A language package active for grounding must not automatically become realization-authorized.
6. Grammar selection operates on structural features/ports/types, never concept-name switches.
7. Morphology is feature-unification/inflection, not post-hoc regex replacement.
8. Negation, modality, tense, aspect, scope and coordination remain explicit until linearization; scope composition is driven by exact `ScopeRelation` order plus reviewed REALIZE-authorized language constructions, never predicate-name branches.
9. Reference generation is referent/discourse-state based, not transcript-string substitution.
10. Surface candidates must round-trip to the authorized Response UOL within declared equivalence tolerances.
11. Failure to realize safely yields a realization frontier/silence decision path; it never licenses semantic simplification that changes meaning.
12. Literal surface policy is an explicit exception, pinned to an external policy record and still semantically verified.

---

## 3. Durable contracts

### 3.1 `RealizationRequestRecord`
Pins:
- Response UOL revision/fingerprint;
- target language/script/locale;
- audience/register constraints;
- language-package revisions;
- realization budget;
- permission/sensitivity.

### 3.2 `DeepClausePlanRecord`
Language-neutral or minimally language-conditioned plan containing:
- discourse act;
- predicate/application refs;
- semantic arguments;
- information structure/topic/focus;
- polarity/modality/time/aspect/scope;
- coordination relations;
- reference requirements.

No final tokens.

### 3.3 `ArgumentFrameRecord`
Data-driven mapping between semantic port configuration and syntactic slots/features.

Conditions can reference:
- schema class;
- port role/filler class;
- voice/valency;
- discourse act;
- morphosyntactic feature constraints;
- construction compatibility.

Do not key behavior on English predicate names.

### 3.4 `FeatureStructure`
Unifiable features such as:
- person;
- number;
- gender/class where grammatically required;
- case;
- definiteness;
- animacy if grammatical;
- tense/aspect/mood;
- polarity;
- evidentiality;
- honorific/register;
- agreement class.

Unknown features remain variables/frontiers; do not guess semantically meaningful features.

### 3.5 `ReferencePlanRecord`
Pins:
- target referent;
- discourse salience/common ground;
- ambiguity competitors;
- permitted identity facets;
- chosen reference strategy;
- language package rule revision.

Reference resolution operates over durable ordinary and specialized referents (including proposition/claim/event referents), preserves exact permission lineage, and never reads raw identity-facet values as surface authority.

### 3.6 `MorphologyRuleRecord`
Declarative rule/transducer contract with:
- lemma/form class;
- feature constraints;
- output morpheme sequence or finite-state transition;
- exceptions with provenance;
- competence cases;
- `REALIZE` promotion status.

### 3.7 `LinearizationRuleRecord`
Orders syntactic constituents from feature/dependency structure.
No semantic facts may be introduced by linearization. If the precedence graph admits multiple orders, realization fails closed unless reviewed language data explicitly declares a free-order construction; kernel lexical sorting is not grammar authority.

### 3.8 `SurfaceCandidateRecord`
Contains:
- token/morpheme sequence;
- source clause/frame/reference/morphology pins;
- exact compilation snapshot revision/fingerprint;
- generation score;
- no authorization status yet.

Compilation is single-snapshot: any semantic-store mutation during or after compilation invalidates the candidate before persistence.

### 3.9 `SemanticRoundTripRecord`
Pins:
- surface candidate;
- analyzer/language package versions;
- recovered UOL;
- semantic equivalence result;
- losses/additions/drift;
- proof trace.

The expected graph fingerprint is derived only from the exact pinned `ResponseUOLRecord`; callers cannot choose a weaker expected meaning. `PASS` remains necessary but is not emission authorization.

---

## 4. Language package architecture

Each package should be independently replaceable/reviewable and contain:

```text
language metadata
script/orthography
lexeme forms
lexical senses
construction schemas
argument frames
morphology paradigms/rules
agreement rules
reference paradigms
word-order/linearization rules
discourse markers
punctuation/orthographic rules
genuine idioms
round-trip competence cases
```

Semantic kernel code must not change when adding a new reviewed language package.

---

## 5. Components

### 5.1 `RealizationCoordinator`
Pins request/snapshot and orchestrates stages only.

### 5.2 `ClausePlanner`
Transforms Response UOL roots into deep clauses.

Responsibilities:
- clause boundaries;
- main/subordinate relations;
- discourse act realization needs;
- coordination;
- semantic scope preservation;
- information structure hints.

No words yet.

### 5.3 `ArgumentFrameSelector`
Selects compatible frames from structural schema/port/features.

Hard constraints:
- all required semantic arguments accounted for or intentionally omitted by a licensed construction;
- no extra semantic role introduced;
- exact frame revision/promotion pin;
- target language compatibility.

### 5.4 `ReferenceGenerator`
Chooses:
- pronoun;
- name/title;
- definite/indefinite NP;
- demonstrative/deictic form;
- repeated description;
- omission/pro-drop where licensed.

Based on semantic/discourse ambiguity and language rules.

Never expose private identity facets merely to make a fluent reference.

### 5.5 `FeatureUnifier`
Constraint propagation across:
- subject/verb agreement;
- determiner/noun/adjective agreement;
- case assignment;
- tense/aspect/mood;
- negation;
- question features;
- relative/complement clause dependencies.

Must detect contradictions rather than pick arbitrary values.

### 5.6 `MorphologyExecutor`
Applies reviewed morphology algebra/transducers.

Forbidden:
- English suffix heuristics in generic kernel;
- regex chains that infer semantic tense/polarity;
- silent fallback to lemma when required morphology carries meaning.

### 5.7 `Linearizer`
Orders constituents using dependency/feature/construction rules.

Must preserve:
- scope;
- coordination grouping;
- clitic/auxiliary ordering;
- question/negation placement;
- language-specific flexible-order constraints.

### 5.8 `OrthographyRenderer`
Applies script, spacing, punctuation and capitalization *after* semantic/syntactic structure is fixed.

Orthography must not decide meaning.

### 5.9 `RoundTripVerifier`
Re-analyzes the generated surface through the reviewed target-language understanding path.

Compare recovered meaning against Response UOL:
- schemas/applications;
- referents;
- bindings;
- polarity;
- modality;
- time/aspect;
- scope;
- discourse act;
- uncertainty/attribution;
- stakeholder/impact qualification.

No unsupported additions permitted.

### 5.10 `RealizationFrontierCoordinator`
When realization cannot safely complete:
- record missing lexicalization/frame/morphology/reference contract;
- preserve exact Response UOL;
- produce learnable package/frontier;
- never mutate Response UOL to fit available grammar.

---

## 6. Per-use authority / Phase-13 integration

This phase must close a known architectural hazard:

A lifecycle-only language record becoming `ACTIVE` after competence on one use axis must not become implicitly executable for every other supported language use.

Required runtime rule:

```text
usable for REALIZE
=
structurally compatible
AND active/reviewed base authority
OR exact PromotionDecision grant for REALIZE
```

Runtime registries should expose operation-aware views:

```text
registry.for_use(UseOperation.GROUND)
registry.for_use(UseOperation.COMPOSE)
registry.for_use(UseOperation.REALIZE)
```

A learned construction that passed grounding competence only must be invisible to realization.

---

## 7. Core realization algebra

### 7.1 Predicate-independent clause formation

Input:
- semantic application + ports;
- discourse act;
- information structure;
- target language.

Output:
- syntactic predicate frame with role mappings.

No `if schema_ref == "event:foo": sentence = ...`.

### 7.2 Negation

Negation is an operator/scope feature and may realize through:
- particle;
- auxiliary;
- morphology;
- negative concord;
- construction.

Selection is language-package data.

### 7.3 Modality

Preserve exact modality source and scope. Ability, permission, obligation, possibility, evidentiality and epistemic uncertainty must not collapse into one generic modal.

### 7.4 Tense/aspect/time

Distinguish semantic time from grammatical tense/aspect. Language packages map semantic temporal relations to available grammatical systems without inventing precision.

### 7.5 Questions

Question type derives from Response UOL variable/discourse act, not punctuation.
Support:
- polar;
- constituent/wh;
- alternative;
- clarification/repair;
- embedded questions.

### 7.6 Coordination

Preserve coordinated member identity and shared arguments. Do not flatten coordinated propositions into strings before realization.

### 7.7 Ellipsis/pro-drop

Allowed only when:
- language construction licenses it;
- recovered meaning remains unambiguous enough;
- round-trip equivalence passes.

### 7.8 Idioms

Only genuine reviewed idioms may map a semantic construction to a non-compositional form. Phrase templates are not a shortcut for ordinary predicates.

---

## 8. Round-trip equivalence policy

Define equivalence tiers:

### Exact-required axes
- referent identity;
- predicate/schema meaning;
- argument bindings;
- polarity;
- modality;
- scope-critical relations;
- numerical quantity/unit;
- permission-sensitive content.

### Controlled-loss axes
Only when Response UOL explicitly permits underspecification:
- grammatical gender absent in source meaning;
- article choice without semantic distinction;
- optional discourse particles;
- language-required evidential/default grammatical marking, provided it does not falsely assert source certainty.

Any semantic addition -> candidate rejected.

---

## 9. Multilingual acceptance matrix

At minimum test reviewed packages across typological contrasts:

1. relatively fixed word order language;
2. richer morphology/agreement language;
3. pro-drop language;
4. language with grammatical gender/class;
5. language with different question strategy;
6. language with flexible word order/case marking where available.

Cases:
- statement;
- negation;
- polar question;
- constituent question;
- modality;
- past/current/future relation;
- progressive/perfective distinction where supported;
- coordination;
- relative/complement clause;
- pronoun/reference ambiguity;
- named referent + privacy scope;
- state/capability report;
- qualification/uncertainty;
- clarification question;
- impact-sensitive acknowledgement/support;
- operation-result report.

Each case must compare semantic graph equivalence, not string translation similarity.

---

## 10. Adversarial tests

- malicious schema name attempts to trigger hardcoded phrase -> no effect;
- unseen new domain schema with valid ports realizes through generic frame;
- learned grounding-only construction appears in realization registry -> rejected;
- realization rule attempts to add certainty -> round-trip rejects;
- morphology fallback drops negation -> reject;
- pronoun creates referent ambiguity -> regenerate stronger reference;
- private identity facet chosen for fluency -> authorization rejects;
- literal response policy outside scope -> rejected;
- cyclic grammar/construction dependency -> bounded frontier;
- language package removal/revision invalidates cached surface plans;
- renaming semantic fixtures leaves realization mechanics unchanged.

---

## 11. Performance gates

Measure:
- frame candidate lookup;
- feature unification iterations;
- morphology application count;
- reference candidate count;
- linearization branching;
- N-best surface generation;
- round-trip analysis cost;
- cache hit/miss keyed by exact language-package + Response-UOL fingerprints.

Use bounded beams/budgets but never prune mandatory semantic distinctions.

---

## 12. Implementation sequence

### 17A — operation-aware language authority views
Close per-use promotion leakage before realization cutover.

### 17B — durable realization contracts/indexes

### 17C — deep clause planner

### 17D — argument frame algebra

### 17E — feature structures/unification

### 17F — reference generation

### 17G — morphology engine

### 17H — coordination/scope/negation/modality/time handling

Implement a generic scope constructor over UOL `ScopeRelation`: recursively realize the exact operator application, apply relations in explicit non-tied order, and select a reviewed REALIZE-authorized `ConstructionRecord` from the pinned pack closure by structural `scope_kind` and `scope_realization` mode. Missing/ambiguous scope construction is a typed frontier. Polarity remains an explicit feature for morphology/frames; time/aspect mappings require reviewed feature/rule data and must never be guessed from English conventions.


### 17I — linearization + orthography

### 17J — realization frontiers/learning integration

### 17K — semantic round-trip verifier

### 17L — multilingual reviewed competence suite

### 17M — adversarial/no-template tests

### 17N — caching/performance/query-plan proof

### 17O — shadow compare with legacy NLG, then authority cutover

---

## 13. Exit gate

Phase 17 passes only when:

- multiple reviewed languages realize equivalent Response UOL without semantic drift;
- adding an ordinary domain schema requires no full-sentence template or kernel branch;
- morphology/syntax/reference are data-driven and independently reviewable;
- per-use learning authority prevents grounding competence from leaking into realization;
- generated surfaces round-trip to authorized meaning;
- realization failure preserves semantic truth and creates explicit frontiers rather than inventing/omitting meaning.
