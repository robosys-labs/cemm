# CEMM Governing Agent Instructions — Recursive Native Semantic Composition

**Status:** highest-priority implementation contract  
**Target:** one exact, atomic, language-agnostic semantic cognition runtime  
**Semantic Contribution ABI:** 1  
**Form/Coverage ABI:** 6

## 1. Canonical documents

Read and obey these files together:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `RUNTIME_ARCHITECTURE.md`
4. `DATA_ARCHITECTURE.md`
5. `runtime-core-loop.md`
6. `CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md`
7. `NATIVE_SEMANTIC_SPINE_IMPLEMENTATION_PLAN.md`
8. `NATIVE_SEMANTIC_SPINE_IMPLEMENTATION_STATUS.md`
9. `V1_ACCEPTANCE.md`

Historical documents, demo transcripts and archived tests are evidence only. They cannot override these contracts.

## 2. Unchanging thesis

```text
meaning != language
surface evidence != semantic identity
semantic identity != compositional role
compositional candidate != settled meaning
settled meaning != admitted world truth
admitted truth != executable external operation
response meaning precedes surface realization
```

CEMM has one semantic brain. Language, sensors, dialogue and operation output supply evidence. The exact semantic plane owns identities, operators, roles, facts, state, rules, frames and proof. Dynamic computation proposes and ranks candidates but cannot invent semantic authority.

## 3. Fixed kernel

Exactly five semantic application shapes remain irreducible:

```text
op:designation
op:type
op:relation
op:state
op:event
```

Do not add `op:learn`, `op:want`, `op:remember`, `op:name`, phrase intents or domain-specific kernel operators. Learning, desire, memory, naming and communication are represented by semantic refs, frames, capabilities, goals and ordinary five-operator applications.

## 4. Native semantic grounding law

Every seeded or learned **meaning-bearing form** must yield at least one bounded typed semantic contribution candidate or one typed unresolved contribution.

A form contribution belongs to the closed transient ABI:

```text
anchor
predicate
binder
reference
scope
discourse
connector
qualifier
literal
open_variable
```

Not every word maps directly to an operation:

- `learn` may denote `event:learn` and inherit an event-frame affordance;
- `is` supplies a predication binder;
- `you` supplies a participant-relative reference requirement;
- `can` supplies capability modality scope;
- `not` supplies polarity scope;
- `because` links proposition graphs;
- a learned noun may supply an anchor and, when its target is a concept, a type-predicate candidate.

The final operator and role structure is selected only by atomic graph composition and exact settling.

## 5. Designation versus affordance

A designation answers:

> Which semantic identity may this surface denote?

An affordance profile answers:

> How may that semantic identity participate in a candidate graph?

Never encode both concerns as one language-pack dictionary entry.

Required path:

```text
surface span
→ designation candidates
→ target semantic kinds and reviewed frame links
→ bounded affordance profiles
→ semantic contribution candidates
→ atomic graph composition
```

A newly learned synonym must inherit the target's affordances without regenerating the language pack.

## 6. Language-pack boundary

Language packs own reversible form evidence:

- tokenisation and morphology;
- closed-class features;
- reference/deixis requirements;
- polarity, modality, tense, aspect and scope evidence;
- bounded construction annotations;
- discourse-form evidence;
- language-specific realization.

Language packs must not be expanding semantic dictionaries. Open-class meaning normally enters through exact designations and semantic affordances.

Do not place a new learned verb in `function_forms` merely to make it compositionally usable.

Realization grammar tokens are output-only and must never be fed back into pre-core form classification.

## 7. Semantic affordance rules

Default affordances may be derived only from semantic kind, never from surface text or ref-name spelling.

Examples:

- `event_type` → event-predicate and event-type-anchor candidates;
- `relation_type` → relation-predicate and relation-type-anchor candidates;
- `state_dimension` → state-property predicate and dimension anchor;
- `value` → value anchor and bounded state-value predicate candidate;
- `label_type` → designation-property predicate and label anchor;
- `concept` → nominal anchor and type-predicate candidate;
- entity-like kinds → referent anchor;
- `capability` → capability target/predicate candidates.

Sparse reviewed frame atoms may refine or replace defaults. Frame metadata must be generation-pinned, bounded and validated at activation.

## 8. No ref-name lexicalization

Internal refs are not language.

Forbidden:

```text
resource:semantic_store → automatically create “semantic store”
frame:event-learn → automatically create “event learn”
contract:designation_learning → automatically expose “designation learning”
```

User-visible designations must be explicit reviewed facts. Developer display labels, if needed, are separate metadata and never enter the designation index.

## 9. Polysemy law

One surface may produce multiple semantic targets and multiple affordance profiles. Preserve alternatives until exact constraints and bounded settling produce a sufficient margin.

Do not collapse:

```text
mean → one universal learning operation
learn → equal-priority event and capability identities
is → one operator
```

`mean` may contribute definition/designation, implication, correction or significance candidates. `learn` normally denotes a learning event; capability interpretation is composed from modality plus the event-to-capability dependency.

## 10. Typed learning plans

Runtime procedure strings are not semantic authority.

Forbidden:

```text
learning_operation = "resolve_designation"
if query_kind in {...}: execute learning branch
```

Required:

```text
LearningPlan
  contract_ref
  source_query_ref
  goal_ref
  capability_ref
  commit_operator_ref
  surface_literal
  expected target kinds
  answer contract
  provenance
  expiry
```

The designation-learning contract must lower to `op:designation`, require `cap:learn`, remain bound to one exact QueryResult, and be consumed only after a successful Stage-13 commit receipt.

## 11. Learning distinctions

Keep these meanings separate:

- **lookup:** “What does X mean?” executes a query and does not mutate world state;
- **teaching claim:** “X means Y” creates a source-attributed semantic claim;
- **learning directive:** “Learn that X means Y” creates a directive over an embedded proposition;
- **learning event claim:** “I learned X” is an attributed event claim about the speaker;
- **reviewed acquisition:** an explicit reviewer publishes a new identity/designation under acquisition policy.

No lexical token directly authorizes a write.

## 12. Atomic graph requirements

Every observed unit must be:

1. consumed into exactly one semantic role; or
2. retained as exactly one typed residual.

Dynamic contribution ports from grounded semantic targets participate in port validation alongside schema-declared ports. Critical residuals block execution. Noncritical discourse/modifier evidence may survive as background evidence.

A schema may match contribution features and semantic kinds. It must not match literal words, regexes, raw phrases or internal ref spelling.

## 13. Proposition and scope architecture

Embedded content is represented as nested or linked semantic graphs, never opaque text when structure is available.

Required generic competencies include:

- modal scope over an event or relation;
- desire/intention over a proposition;
- knowledge/memory over an entity or proposition;
- speech over content and optional addressee;
- condition, cause, contrast and coordination links;
- quoted/literal content when semantic decomposition is unavailable.

Do not add one intent or schema family per English sentence.

## 14. Authority and data ownership

Authority files form one linked graph. Every atom has one owner. Supplemental files may reference but not redefine it.

Before import:

- link the complete bundle;
- validate all atom refs and kinds;
- validate frame links and frame metadata;
- validate learning contracts;
- validate operator lowering compatibility;
- reject automatic internal lexicalization;
- reject missing capabilities, goals or answer contracts;
- validate pack hashes and ABI versions;
- perform one atomic import.

## 15. Performance bounds

Normal cycles must remain bounded:

- maximum designation candidates per span;
- maximum affordance profiles per target;
- maximum grounding hypotheses;
- maximum atomic matches and search states;
- bounded proposition depth;
- bounded retrieval and inference closure;
- one pending learning obligation;
- bounded operation re-entry.

No normal cycle may scan every atom to derive affordances. Use generation/revision-keyed caches and indexed relation lookup.

## 16. Required anti-bloat tests

A release fails if:

- an unseen learned synonym requires form-pack regeneration;
- a new atom automatically becomes a user-visible word;
- an open-class lexeme is added to `function_forms` without closed-class justification;
- a runtime branch checks a surface string to select meaning;
- one semantic frame is duplicated per inflection or language;
- a capability and event are duplicated lexically when modality can compose them;
- a semantic contribution set exceeds its configured bound;
- a learned unknown defaults to `concept`;
- an invalid frame silently falls back to an opaque predicate.

## 17. Root-cause workflow

For every failure:

1. reproduce with exact activation and stage trace;
2. identify the earliest divergent artifact;
3. determine whether the defect belongs to form evidence, designation, affordance, graph assembly, settling, query, admission, goal, operation or realization;
4. define multilingual and unseen-synonym acceptance tests;
5. modify the earliest owner;
6. regenerate deterministic artifacts;
7. run authority, ABI, anti-bloat and full regression gates.

A passing phrase alone is not acceptance.

## 18. Definition of completion

A change is complete only when code, authority data, deterministic generators, migrations, active docs, activation validation and executable tests agree. Partial implementation must remain explicitly disabled rather than hidden behind permissive fallback behaviour.

<!-- CEMM_SOURCE_REWRITE:AGENTS:v3.1.3 -->

## 19. Recursive release contract

- PropositionGraph ABI 2 and Atomic Composition ABI 1 are transient Stage-5 structures only.
- Coverage/Form ABI 7 is the active form contract.
- Candidate-local app references are legal only through reviewed proposition-taking frame roles.
- Description ABI 1 and Proof Bundle ABI 1 extend Stage 10 without a parallel query engine.
- Verified semantic focus is recorded only after exact Response CSIR realization equivalence.
- The obsolete sentence-shaped embedded proposition family is forbidden.
- Historical tests may be replaced when they require a retired semantic path; exact gates must never be weakened for compatibility.
