# CEMM v3.4.7 Governing Implementation Contract

**Status:** highest-priority repository implementation contract  
**Scope:** all code, data, tests, documentation, demos, migration work, and architectural claims  
**Target:** a multilingual grounded semantic kernel that learns through UOL and says only what it can justify  
**Compatibility:** intentionally breaking at the semantic-authority boundary.

---

## 1. Binding source order

Use active guidance in this order:

1. root `AGENTS.md`;
2. root `architecture.md`;
3. root `coreloop.md`;
4. root `3.4.7-upgrade-fixes-plan.md`;
5. executable architecture/acceptance tests;
6. active data manifests and version manifest;
7. implementation code and traces.

`README.md` explains the project but does not override the contracts above.

Any older architecture, plan, patch README, generated overlay, archived document, bootstrap script, comment, or test fixture that conflicts with these files is non-authoritative. Move obsolete guidance under `docs/archive/` and mark it clearly.

---

## 2. Status language is mandatory

Every progress or completion claim must distinguish:

- **specified** — required by an active contract;
- **implemented** — code/data exists;
- **wired** — the canonical runtime invokes it;
- **authoritative** — no competing component can make the same decision;
- **verified** — end-to-end and metamorphic tests prove it.

Do not call a phase, module, or release complete unless all applicable states are true.

Do not say tests pass unless they were actually run against the stated revision. Report skipped, unavailable, or failing suites explicitly.

---

## 3. Core identity

CEMM is a grounded meaning system and cognitive semantic kernel. It is not:

- a sentence-intent classifier;
- a chatbot routing table;
- an LLM wrapper;
- a vector store presented as understanding;
- a giant persistent sentence graph;
- a rule engine with no grounded learning;
- an English regex pipeline;
- a collection of demo-specific patches.

Its canonical path is:

```text
Observation
→ FormLattice evidence
→ Referent candidates
→ active schemas and local operational ports
→ UOL MeaningHypotheses
→ compatible MeaningBundle
→ epistemics / learning / inference / goals / operations
→ response-goal candidates
→ UOLResponsePlan
→ target-language realization and emission proof
```

---

## 4. Referent law

`Referent` is the single canonical term and record family for every identity-bearing semantic object that may fill a predicate or operation port.

Referent kinds include:

```text
self
agent/person/animal/organization/software agent
physical or digital object
place
event/action/process
state
proposition
quantity
unit
time instant/interval
collection
information object
context
schema-as-topic
```

Rules:

1. Do not introduce a competing top-level `Value`, `Entity`, `TemporalObject`, `EventObject`, or `PropositionObject` filler family.
2. Distinguish kinds through `ReferentKind`, type schemas, identity criteria, and specialized canonical payloads.
3. Raw strings, numbers, role IDs, parser nodes, and opaque labels do not fill semantic ports directly.
4. Quantity and unit are separate linked referents.
5. A proposition is a referent whose content references predications and carries context, polarity, modality, attribution, and time.
6. A schema is not replaced by a referent. A `SCHEMA` referent can point to a schema revision when the schema itself is discussed.
7. Referent identity merge/split is explicit, reversible, provenance-bearing, and patch-controlled.

---

## 5. UOL law

UOL is the Universal Operational Language of the kernel.

### 5.1 UOL is temporary cognition

`UOLGraph` is a cycle-local multi-hypothesis workbench containing referents, predications, propositions, discourse relations, alternatives, open ports, assumptions, and provenance.

Do not persist the entire working graph as long-term memory.

### 5.2 Selected meaning

Only `MeaningBundleSelector` may authorize the selected compatible UOL subgraph. Selecting one top proposition is insufficient for coordinated or multi-clause input.

### 5.3 Durable change

`GraphPatch` is the only route from selected UOL cognition to durable changes in referents, knowledge, schemas, rules, aliases, state, common ground, or operation effects.

No operator, analyzer, learner, or response component may write directly to a canonical store.

### 5.4 Output

`UOLResponsePlan` contains semantic propositions, discourse structure, reference plans, certainty/attribution, target language, and tone constraints. It contains no final response strings.

---

## 6. Predication and local-port law

A `Predication` is an instance of an active `PredicateSchema` with bindings to predicate-owned local ports.

A local port schema defines:

```text
port_id
optional role_family
accepted ReferentKinds and type schemas
cardinality and requiredness
query/open behavior
context/time propagation
identity contribution
binding constraints
coercion policy
```

Rules:

1. Exact port semantics belong to the owning predicate or operation.
2. Engines may not assume a universal actor/object/target/place role list.
3. Reusable role families are alignment hints, not binding authority.
4. An open port is a typed unresolved requirement, not a placeholder referent and not a durable concept.
5. Query ports are deliberately open; missing required assertion ports are gaps.
6. Operations use local input/output ports and explicit semantic success conditions.

---

## 7. Semantic-authority law

Only the following authorities may make their named decisions:

| Decision | Authority |
|---|---|
| language hypotheses | LanguageDetectionCoordinator |
| form-analysis alternatives | LanguageAnalysisCoordinator/FusionCoordinator |
| referent candidates | ReferentCandidateGenerator/Resolver |
| schema lifecycle | SemanticSchemaStore |
| predicate/operation activation | SchemaActivator |
| UOL hypothesis composition | MeaningAssembler |
| selected compatible meaning | MeaningBundleSelector |
| gap class | GapClassifier |
| learning eligibility | LearningEligibilityAssessor |
| epistemic use/admission | EpistemicCoordinator |
| durable semantic commit | GraphPatchCommitCoordinator |
| active goals | GoalArbiter |
| executable operation plan | OperationPlanner + Authorizer |
| response candidate generation | ResponseGoalGenerator |
| selected response goals | ResponseRanker/Selector |
| UOL response content | UOLResponsePlanner |
| surface realization | RealizationCoordinator |
| emission permission | EmissionGate |

A component must not construct the artifact of a downstream authority as a fallback.

---

## 8. Language and analyzer boundary

Language-specific code and data are allowed and necessary inside language adapters and packs. The semantic kernel must remain language-independent.

Language analyzers may emit:

- tokens/morphemes and raw spans;
- lexical-sense candidates;
- morphology and agreement evidence;
- clause and sentence boundary candidates;
- dependency/constituency evidence;
- conjunction, coordination, subordination, and relative-clause evidence;
- negation/modality/tense/aspect scope cues;
- NER/mention candidates;
- quantity, unit, time, and place candidates;
- construction/form-pattern evidence;
- communicative/discourse cues;
- unresolved spans.

They may not:

- select final referents;
- instantiate authoritative predications;
- choose a MeaningBundle;
- write knowledge or schemas;
- open learning solely because a word is unknown;
- choose response goals;
- emit final response content.

### 8.1 Prohibited kernel patterns

Kernel and control modules must not contain:

- English or other language-specific word tests;
- exact transcript phrases;
- language-specific word order assumptions;
- response phrase routing;
- domain-vocabulary blacklists;
- regular expressions whose semantic purpose is recognizing a particular language construction.

Unicode-safe transport normalization is allowed. Language-specific morphology or surface regex belongs in a language module and must emit evidence only.

### 8.2 Construction matcher

The declarative construction matcher is a `FormPatternEvidenceProvider` only.

A construction may be retained for:

- closed grammar;
- idioms/non-compositional expressions;
- argument-realization evidence;
- morphology or discourse patterns;
- realization.

An ordinary full-sentence construction added because a demo failed is architectural drift unless it is proven to be a genuine idiom and accompanied by broader semantic tests.

---

## 9. NER and reference law

NER output is a mention proposal, not an identity decision.

Reference resolution must support all ReferentKinds, including prior propositions, events, states, quantities, units, times, places, schema topics, and multimodal tracks.

Pronoun/anaphora resolution and predicate-port binding are joint. Do not greedily resolve a pronoun before candidate predicates reveal accepted port kinds.

Database, knowledge-base, geospatial, event, or vector matches are candidate anchors only. Final grounding requires identity/type/port/context compatibility and traceable selection.

---

## 10. Context and multimodal law

`DiscourseModel` and `SessionWorldModel` are bounded projections, not truth stores.

They may provide:

- mention chains;
- topic/focus and recency;
- open questions and ports;
- learning and operation obligations;
- common-ground status;
- multimodal tracks;
- current location/time/state;
- capability and affordance evidence;
- language/tone preferences.

They may rank meaning but may not fabricate a fact. Durable admission uses EpistemicAssessment and GraphPatch.

---

## 11. Meaning assembly and selection law

`MeaningAssembler` must compose from evidence, active schemas, referent candidates, and local ports.

Required behavior:

- preserve multiple clause boundaries and structures;
- support multiple predicates per utterance;
- support coordination/shared arguments;
- support relative clauses and complements;
- support propositions as role fillers;
- support questions through typed open ports;
- support directives through desired operation/state content;
- preserve partial meaning and unresolved evidence;
- expose all assumptions/coercions;
- use bounded search and trace pruning.

`MeaningBundleSelector` selects compatible sets using hard constraints and named score factors. It must preserve coordinated propositions and N-best ambiguity alternatives.

Do not use parser confidence, construction priority, lexical frequency, or world plausibility as a final authority.

---

## 12. Gap and repair law

Canonical gaps distinguish analysis, language, lexical, reference, identity, port, schema, knowledge, epistemic, capability, permission, learning-frontier, and realization failures.

Rules:

1. `learnable` defaults to false.
2. Reference or port failures are not schema lessons.
3. Knowledge absence is not missing meaning.
4. Capability/permission failures are not knowledge failures.
5. Learning eligibility requires a known target, grounding anchor/frontier, representable contribution type, scope, and permission.
6. Run error attribution before deciding how to repair.
7. Ask the narrowest useful question.
8. Generic “rephrase” is last resort.
9. Every repair question is a UOL response goal with an exact target gap.

---

## 13. Knowledge and epistemic law

Canonical durable knowledge is a `KnowledgeRecord` pointing to a proposition referent.

Do not create a second predicate/role fact representation for new writes.

Knowledge must preserve:

- four-state truth: supported, opposed, both, undetermined;
- source and evidence lineage;
- context and attribution;
- valid time;
- confidence;
- sensitivity;
- permission and scope;
- retention and revision.

An assertion that is structurally understood is not automatically actual-world knowledge. The EpistemicCoordinator decides permitted use.

Absence of evidence is not negation. Contradictions remain visible unless exact correction/supersession policy applies.

---

## 14. Learning law

Learning is a first-class core-loop activity, not a fallback string handler.

### 14.1 Grounding requirement

Every learned contribution must connect to:

- known referents;
- active/provisional schemas;
- self or discourse participants;
- place/event/state/proposition/quantity/unit/time referents;
- or exact typed unresolved frontier items.

Raw prose, opaque labels, generated examples, and response text are not executable definitions.

### 14.2 Contribution classes

Learning must distinguish lexical alias, identity, kind, role/relationship, predicate/ports, state dimension, unit/conversion, event/place pattern, operation affordance, strict/constitutive/causal/enabling/default/statistical rule, exception, realization, correction, and retraction.

### 14.3 Recursive frontier

Recursive learning must have hard limits for depth, wall clock, new records, rule firings, interaction count, and sensitive content. Detect cycles and classify dependency components.

Unresolved frontier items remain unresolved. Do not guess them.

### 14.4 Scope and activation

New user-taught structures default to session/private scope. A single example cannot self-certify global competence.

Lifecycle is:

```text
candidate → provisional → active → superseded/rejected
```

Activation requires grounding, structural closure, competence, rule classification, cycle/contradiction analysis, permission, scope, and atomic CAS commit.

### 14.5 Examples are not facts about every instance

- `president` should normally be learned as a role/relationship structure, not merely a person kind.
- “president usually in the capital” is a default.
- mother-in-law/spouse/co-residence relations are not automatically strict.
- relationship status must not imply sensitive personal activity by default.

Preserve user-taught theories in attributed/private contexts when appropriate; do not launder them into universal truth.

---

## 15. Inference and relationship-algebra law

Rule function and strength are independent.

Functions include identity, constitutive, strict implication, prerequisite, causal, enabling, preventing, default, statistical, pragmatic, and normative.

Strength includes strict, defeasible, and probabilistic.

Every derived proposition must carry:

- rule and supporting proposition refs;
- variable bindings;
- context/time propagation;
- derivation depth;
- consequence status;
- dependency fingerprint;
- sensitivity result;
- completeness/timeout status.

Defaults and associations may guide ranking or qualified responses. They do not become unqualified actual facts by default.

Inference must obey depth, step, firing, signature, existential, memory, wall-clock, and sensitivity budgets. Partial timeout results are explicit.

---

## 16. Goal, operation, and capability law

Goals are desired propositions, information states, or operation outcomes. They are not response labels.

Operation plans must:

- instantiate active OperationSchemas;
- bind all required local ports to referents;
- have explicit semantic success conditions;
- verify preconditions;
- simulate effects as GraphPatches;
- assess capability, permission, resources, risk, cost, reversibility, and idempotency;
- reauthorize immediately before irreversible effects;
- reconcile observed outcomes.

Do not map generic goal kinds to fixed operation keys without semantic bindings.

Self capability claims come from live component/capability observations and admitted configuration, not from hard-coded conversational text.

---

## 17. Response and realization law

### 17.1 Candidate generation

ResponseGoalGenerator must generate plausible semantic alternatives before ranking, including answer, qualified answer, acknowledgement, correction, clarification, learning probe, operation result, limitation, uncertainty, rapport, and no-output.

A ranker cannot compensate for candidates that were never generated.

### 17.2 Response selection

Each response candidate references exact semantic records. Do not use `content_kind`, phrase labels, or templates as response meaning.

### 17.3 UOL response

UOLResponsePlanner selects semantic propositions, discourse order, reference plans, target language, attribution/certainty, and bounded tone constraints.

### 17.4 Realization

The realizer chooses morphology, word order, referring expressions, and style. It may not add or strengthen claims.

Every semantic contribution must have coverage. Uncovered required content blocks emission.

### 17.5 “Says only what it understands”

A clause is emit-able only when:

- it satisfies a selected response goal;
- predicate and realization schemas are active;
- required ports are filled;
- referents are grounded or explicitly mentioned/quoted;
- epistemic use is authorized;
- inference proof is allowed where applicable;
- full realization coverage exists;
- revisions are fresh.

Fluency is never evidence of understanding.

---

## 18. Foundation-data law

Foundation data must be small, operationally complete, language-neutral, and teachable.

It must include:

- ReferentKinds and identity;
- local-port predicate families;
- relation algebra;
- state and transition;
- quantities, units, conversions, and time;
- place/event participation;
- epistemic and discourse relations;
- learning/definition structures;
- goals, operations, capability, permission;
- self referent, CEMM name, and `Contextual Event Memory Model` expansion;
- response-goal schemas;
- competence tests.

Reviewed foundations and language packs may use JSON/YAML. Runtime and learned records use durable indexed stores.

Do not put language surface forms in language-neutral foundation files.

Do not enforce foundation neutrality through domain-word blacklists in Python. Validate schema families and dependency structure.

---

## 19. Testing contract

Every semantic change requires tests at the correct level.

### 19.1 Required categories

- unit tests for new records and constraints;
- end-to-end canonical-runtime tests;
- metamorphic paraphrase/structure tests;
- cross-language UOL equivalence tests;
- minimal-pair distinction tests;
- discourse/reference tests;
- learning and rollback tests;
- inference proof/rule-class tests;
- operation authorization/reconciliation tests;
- realization round-trip/coverage tests;
- performance/timeout/determinism tests;
- architecture import/lint tests.

### 19.2 Test anti-patterns

Do not prove architecture with only the exact phrase that caused a bug.

For every accepted utterance case, include nearby variants. For every semantic distinction, include a minimal negative case.

Do not mock away the authority being tested in an end-to-end acceptance test.

Do not assert only final surface output. Assert selected referents, predicates, ports, proposition contexts, gaps, goals, response candidates, UOL plan, and proof.

### 19.3 Required baby-CEMM suite

The release suite must cover:

- self name and CEMM expansion;
- user full name and age;
- conjunction and multi-answer query;
- correction/supersession;
- entity/place/event/proposition/state/time reference;
- unknown word versus reference gap;
- recursive grounded teaching;
- strict/default/causal/sensitive rule discipline;
- second-language semantic equivalence;
- multimodal reference;
- bound safe operation;
- multiple response candidates;
- blocked unsupported emission.

---

## 20. Performance and boundedness law

Every candidate-generating or recursive component must expose configurable budgets and trace them.

Required limits include:

- candidates per span/mention/port;
- predicate activations per clause;
- clause and bundle beam width;
- embedding depth;
- repair re-entry count;
- learning frontier depth and questions;
- inference depth, steps, firings, signatures, existentials;
- operation planning alternatives;
- wall-clock and memory budgets.

A budget hit returns the best proof-bearing partial result plus explicit incompleteness. It must not trigger a hidden canned fallback.

Fixed snapshots must produce deterministic selections except where explicitly configured stochastic evidence providers are recorded with seeds/versions.

---

## 21. Repository and import boundaries

1. `language/` may depend on evidence models and schema lookup interfaces, not UOL selection, knowledge commit, goals, response selection, or realization authority outside its own language realization data.
2. `understanding/` may read schemas/referents/context but may not commit knowledge or schemas.
3. `learning/` creates GraphPatches but does not activate or commit directly.
4. `inference/` creates proof-bearing candidates/patches but does not bypass consequence policy.
5. `goals/` and `operations/` do not generate response text.
6. `response/` does not execute operations or admit knowledge.
7. `realization/` does not retrieve facts or decide response content.
8. `storage/` does not interpret semantics.
9. compatibility/legacy packages may not be imported by the canonical composition root after cutover.

Enforce these boundaries with import tests where practical.

---

## 22. Implementation workflow for agents and maintainers

Before changing code:

1. Read the governing documents.
2. Identify the decision authority affected.
3. Trace the current canonical runtime call path.
4. Identify whether the bug is evidence, grounding, activation, composition, selection, gap, knowledge, learning, inference, goal, operation, response, or realization.
5. Reproduce with a semantic trace and neighboring variants.
6. Design the fix at the owning authority.

During implementation:

1. Add/modify typed records first.
2. Preserve source/provenance and alternatives.
3. Add named score factors and budgets.
4. Avoid compatibility branches inside canonical authorities.
5. Keep language-specific logic in language modules/data.
6. Route durable changes through GraphPatch.
7. Add positive, negative, metamorphic, and end-to-end tests.

Before claiming completion:

1. Run architecture lint/import tests.
2. Run focused and full suites.
3. Inspect semantic traces, not only output strings.
4. Verify the canonical runtime invokes the new path.
5. Verify old competing authority is unreachable or removed.
6. Report actual status using specified/implemented/wired/authoritative/verified.

---

## 23. Code-review rejection checklist

Reject a change when any answer is yes:

- Does it add an exact demo/transcript phrase?
- Does kernel code inspect language-specific words or word order?
- Does a parser/construction/NER result become selected meaning directly?
- Does it introduce another semantic object family instead of Referent?
- Does it bind raw values rather than referents?
- Does it hard-code universal role names?
- Does it choose one proposition and drop compatible coordinated content?
- Does it make a generic gap learnable?
- Does it write directly to a semantic store?
- Does it treat a user assertion as unqualified truth?
- Does it materialize a default/association/sensitive inference as fact?
- Does it map a generic goal to an unbound operation?
- Does it rank only one preselected response route?
- Does the renderer decide what to say?
- Does tone change certainty or factual content?
- Does the test assert only a final string?
- Does it claim completion without canonical wiring and verification?

---

## 24. Architectural change procedure

A change to any of the following requires updating the governing documents and architecture tests in the same change:

- canonical record families;
- ReferentKinds;
- authority matrix;
- core-loop stage ownership;
- GraphPatch commit boundary;
- learning lifecycle;
- rule classes/consequence policy;
- UOL response contract;
- foundation admissibility;
- release acceptance floor.

Do not silently evolve architecture through code.

---

## 25. Final governing principle

The implementation must optimize for semantic truthfulness, compositional reuse, teachability, and explicit uncertainty—not for making one conversation look fluent.

The correct fix is the smallest change that repairs the owning foundational authority and generalizes across languages, paraphrases, contexts, and modalities. A larger sentence database, a new fallback phrase, or another wrapper around the old composer is not progress toward CEMM.
