# CEMM v3.4 Cognitive Kernel — Governing Implementation Contract

Status: active governing contract upon merge  
Audit baseline: `8e0da751edbd86460049ef14f56fda66cc05de84`  
Architecture revision: `v3.4-foundation-final`  
Scope: repository-wide  
Compatibility: intentionally breaking at the semantic-authority boundary

This file is the highest-priority implementation contract for CEMM v3.4. It governs coding agents, maintainers, reviewers, tests, migration work, and architectural status claims.

The purpose of v3.4 is not to preserve v3.3 names or layers. The purpose is to establish one coherent runtime that can interpret, ground, know, doubt, learn, plan, act, introspect, and communicate through the same native semantic substrate.

## 1. Core identity

CEMM is a **cognitive semantic kernel**.

It maintains an evidence-aware model of:

- referents, identities, concepts, states, events, places, time, sequences, and causes;
- propositions in actual, reported, believed, hypothetical, desired, quoted, counterfactual, and simulated contexts;
- what is stored, accessible, attended, remembered, understood, believed, or known;
- what the system is currently capable of, permitted to do, resourced to do, and reliable at doing;
- active uncertainty, contradiction, gaps, needs, goals, plans, operations, and outcomes;
- language-independent meaning and language-specific expression.

The target is functional cognitive continuity and operational self-awareness. This is a software architecture for simulating cognitive access, self-modeling, agency, and learning. It is not a scientific claim of subjective consciousness.

## 2. Canonical source order

Use active guidance in this order:

1. root `AGENTS.md`
2. `cemm/ARCHITECTURE.md`
3. `cemm/newarch/CORE_LOOP.md`
4. `cemm/newarch/SEMANTIC_DATA_MODEL.md`
5. `cemm/newarch/UNDERSTANDING_PIPELINE.md`
6. `cemm/newarch/LEARNING_PIPELINE.md`
7. `cemm/newarch/SEMANTIC_FOUNDATIONS.md`
8. `cemm/newarch/AUTHORITY_MATRIX.md`
9. `cemm/newarch/IMPLEMENTATION_PLAN.md`
10. `cemm/newarch/ARCHITECTURE_DECISIONS.md`
11. executable architecture and acceptance tests
12. implementation code and traces

Historical documents and code under `legacy/` are non-authoritative.

Every status claim must distinguish:

- **specified** — required by an active contract;
- **implemented** — code exists;
- **wired** — the canonical runtime invokes it;
- **authoritative** — no competing component can make the same decision;
- **verified** — end-to-end structural tests prove it.

Never call a phase complete unless all five states hold.

## 3. Three-layer law

CEMM has exactly three architectural layers of meaning-related records.

### 3.1 Canonical semantic graph

The only canonical semantic object families are:

```text
Referent
Value
Predication
Proposition
ContextFrame
EvidenceRecord
StructuralLink
```

These represent what an input, memory, simulation, plan, tool result, or response means.

### 3.2 Semantic schemas

Executable definitions are versioned `SchemaRecord`s:

```text
LexemeSenseSchema
ConstructionSchema
PredicateSchema
RoleSchema
EntityKindSchema
StateDimensionSchema
ContextSchema
OperationSchema
CapabilitySchema
RealizationSchema
PolicySchema
```

Schemas define how meaning can be recognized, composed, grounded, queried, learned, executed, or expressed.

### 3.3 Cognitive-control records

Control records reference semantic graph objects and schemas; they do not constitute a second ontology:

```text
WorkspaceEntry
EpistemicAssessment
CapabilityAssessment
GapRecord
GoalRecord
PlanRecord
OperationInstance
ExecutionLedger
LearningTransaction
SemanticMessagePlan
MutationSet
CommitOutcome
```

A goal, plan, gap, learning transaction, or capability assessment may never replace the proposition or schema it concerns.

## 4. Structural-edge law

`StructuralLink` expresses graph structure only:

```text
has_role
instantiates
refers_to
grounded_by
scoped_by
supported_by
opposed_by
derived_from
depends_on
co_refers_with
```

Semantic relations such as the following are always `Predication` instances:

```text
is_a
same_as
part_of
located_at
inside
before
after
causes
enables
prevents
knows
means
capable_of
```

No semantic relation may also be encoded as an authoritative typed graph edge. Compatibility importers may read old representations, but the canonical kernel emits only predications plus structural links.

## 5. Predication and proposition law

A `Predication` is semantic content:

```text
predicate_schema_ref + typed role bindings + open ports
```

A `Proposition` makes that content truth-bearing by adding:

```text
context_ref
polarity
modal qualifiers
attribution
valid time
```

The following are independent axes and must never be collapsed into one `proposition_mode` enum:

- communicative force: assert, ask, request, direct, acknowledge, correct, promise, refuse;
- polarity: positive or negative;
- context: actual, reported, believed, hypothetical, desired, counterfactual, simulated, quoted;
- modality: possible, necessary, permitted, prohibited, obligated, capable;
- temporal scope and aspect.

A question is a communicative predication over a proposition pattern with open ports. A command is a directive predication whose content denotes a desired operation or state. Negation is proposition polarity. Reported and hypothetical meanings are contexts.

## 6. Role and open-port law

Roles belong to `PredicateSchema`.

A role binding points from a predication to a real filler:

```text
Referent | Value | Predication | Proposition | ContextFrame
```

A proposition or predication may fill content, cause, condition, purpose, reason, answer, question, belief, desire, or plan roles.

An open port is an unfilled typed role requirement. It is metadata on a candidate predication or query pattern. It is never:

- a placeholder entity;
- a concept named `topic`, `object`, or `target`;
- a public response value;
- a durable memory candidate.

Role resolution is schema-generic. No engine may hard-code a universal role list such as actor/object/target/place.

## 7. One schema authority

`SemanticSchemaStore` is the only authority for executable meaning schemas.

Every schema record carries:

```text
record_id
semantic_key
schema_kind
status: candidate | provisional | active | rejected | superseded
scope: global | tenant | user | session
applicability contexts and valid time
version
field-level contributions and provenance
support and counterevidence
confidence
permission
```

Boot and learned schemas use the same model and resolver. Boot origin is provenance, not a separate lifecycle state. Session learning is a session-scoped schema revision, not a `SessionLearningOverlay`, shadow lexicon, or second resolver.

Lifecycle meaning is strict:

- `candidate` — identity or hypothesis exists but is not structurally usable;
- `provisional` — some or all structure is executable in a declared attributed/hypothetical/private context, but independent competence or epistemic admission is incomplete;
- `active` — the exact revision passed structural closure, required independent competence, context/scope policy, and atomic activation;
- `superseded`/`rejected` — not selected for new interpretation, while historical proposition bindings remain resolvable.

A structurally executable revision is not automatically actual-world knowledge. `EpistemicEvaluator` decides admissibility in a context, and `GroundingResolver` derives a snapshot-specific use profile from structural assessment plus epistemic admissibility. Neither may activate a revision.

`ActionOperatorSchema` and `PredicateSchema` may not remain competing authorities. Actions and processes are event-oriented predicate schemas; executable operations use `OperationSchema` and reference semantic predicates for preconditions and effects.


### 7.1 Grounded-definition and use-profile law

Schema lookup, structural executability, independent competence, epistemic admissibility, and current usability are different decisions.

The existing schema path must derive:

```text
recognized surface
→ candidate sense/schema reference
→ schema-family definition closure
→ competence profile
→ epistemic admissibility by context
→ operation-specific SchemaUseProfile
```

`SchemaGroundingAssessment` is a derived control record for an exact revision and environment fingerprint. It is not a semantic object, store, certificate database, or activation authority.

A revision may support quotation, preservation, or attributed reasoning while remaining opaque or provisional. It may support actual-world classification or inference only when the current `SchemaUseProfile` permits those operations.

### 7.2 Sense, scope, and context law

Lexical form, sense, schema revision, access scope, and epistemic context are distinct.

One lexical form may map to multiple senses. One schema may have multiple lexicalizations. Opaque uses of one spelling may remain separate candidate sense clusters until evidence supports merge.

Narrower access scope does not blindly replace wider meaning. A user-scoped revision may represent a user theory or private convention without overriding an active global schema in the actual context. Resolution considers:

```text
sense
context/world
applicability domain and valid time
scope/access
structural usability
epistemic admissibility
requested semantic operation
```

Schema merge or identity equivalence is explicit, reversible, journaled, and never destroys original references.

### 7.3 Evidence-lineage and field-provenance law

Evidence independence follows derivation lineage, not record count or source labels.

Translations, paraphrases, summaries, generated examples, and retrieved copies inherit their root lineage unless an independent observation or oracle exists.

Every learned schema field or pattern records whether it was:

```text
asserted
observed
entailed
inherited
hypothesized
defaulted
induced
adapter-supplied
boot-supplied
```

Hypothesized/defaulted content may guide candidate ranking and probing. It may not be presented as user-taught or observed truth.

Competence cases derived from the definition may test well-formedness only. They cannot independently certify discrimination, truth, or promotion.

### 7.4 Recursive-definition law

Schema dependencies are typed. Cyclic dependency components are classified as:

```text
inverse relation cluster
positive monotone recursive cluster
stratified defeasible cluster
unsupported non-monotone cluster
```

Joint activation is allowed only for a declared inverse or positive-monotone cluster with external anchors, non-redundant member contributions, a defined fixed-point/inverse contract, and independent joint competence.

Cycles through negation, exception priority, permission, effect authorization, destructive mutation, identity collapse, or single-valued replacement are not directly jointly activated.

A recursive cluster activates atomically or not at all.

### 7.5 Atomic activation and invalidation law

Assessment and activation use one pinned store/environment snapshot and compare-and-swap commit.

The assessment fingerprint includes:

```text
schema dependency revisions
grounding-policy version
competence-suite versions
kernel foundation/type versions
inference/truth-maintenance version
adapter observation-contract versions
context/scope policy version
```

A dependency or environment change invalidates all dependent derived cognition, including assessments, inherited constraints, classifications, inferred propositions, cached answers, plans, undispatched messages, effect proposals, capability/understanding conclusions, and learning-success claims.

Original evidence and already dispatched historical output remain preserved. Stale effects must be re-authorized before execution or critical commit.

### 7.6 Pattern-semantics law

Pattern function and pattern strength are independent.

```text
function:
  constitutive | identity | selectional | diagnostic |
  default | typical | incidental | causal | normative

strength:
  strict | defeasible | probabilistic
```

Typical/default/incidental patterns may support recognition or prediction but may not by themselves close a constitutive definition or reject an instance.

Default reasoning respects specificity, exceptions, context, provenance, and four-state open-world truth.

### 7.7 Live-effect-authority law

Schema grounding may permit interpretation, prediction, simulation, or proposal of effects. It never grants persistent authority to execute or commit an effect.

Every operation instance is authorized from live capability, permission, risk, context, resources, and current schema-use evidence. Authorization is revalidated before irreversible execution and critical commit.

### 7.8 Correction, revocation, and forgetting law

The kernel distinguishes:

```text
schema/proposition supersession
source support retraction
permission revocation
archival
user-requested forgetting
privacy deletion
```

Each targets exact evidence, proposition, sense, or schema revisions and triggers appropriate dependency reassessment. Archival is not privacy deletion. Provenance history may be retained only where policy permits.

## 8. Language-boundary law

Language adapters emit reversible surface evidence only:

```text
raw span
normalized surface
lemma candidates
morphological features
syntax/dependency evidence
construction candidates
quotation and clause boundaries
language and confidence
```

They may propose lexeme senses, constructions, predications, and communicative structures. They may not:

- select final meaning;
- authorize a write;
- declare truth;
- directly answer a query;
- directly mutate memory;
- claim a capability;
- choose final response content.

The canonical token stream preserves raw text, apostrophes, offsets, punctuation, quotation boundaries, negation, contractions, and morphology.

## 9. Working-space and memory law

`GlobalSemanticWorkspace` is the bounded active set available to reasoning, planning, introspection, and response formation.

The following are distinct:

```text
stored(p)       — a persistent record exists
accessible(p)   — current retrieval, permission, and resources allow access
attended(p)     — p is in the active workspace
remembered(p)   — a relevant stored trace was successfully retrieved
understood(x)   — executable schemas can operate over x
known(p)        — epistemic criteria are satisfied
```

Memory classes are lifecycle/indexing policies over shared canonical records:

```text
working
common-ground/conversation
episodic
semantic
procedural
schema/learning
```

They are not competing semantic stores. Indexes and projections may be rebuilt from authoritative journals and stores.

Only `CommitCoordinator` mutates persistent canonical stores.

## 10. Epistemic law

Absence is not falsity.

Truth maintenance uses four support states:

```text
supported
refuted
both
neither
```

Confidence, freshness, accessibility, source trust, and schema executability are separate dimensions.

`EpistemicEvaluator` is the sole truth and knowledge authority.

`knows(self, p)` may be derived only when:

- `p` is grounded;
- supporting evidence satisfies policy;
- relevant counterevidence is considered;
- the record is accessible;
- temporal validity is sufficient;
- the schemas needed to use or explain `p` are executable;
- permission allows the current use.

The following are never interchangeable:

```text
stored(p)
remembers(self, p)
has_access_to(self, p)
knows(self, p)
knows_about(self, topic)
understands(self, schema_or_structure)
believes(self, p)
```

“What do you not know?” may return only bounded active gaps, unresolved requested content, contradictions, inaccessible records, unsupported propositions, and known limitations. CEMM may not claim to enumerate all unknown facts.

## 11. Self and capability law

`self` is a stable `Referent` with deictic identity, not a special atom kind and not a separate truth system.

Self identity, operational state, resources, capabilities, permissions, goals, knowledge assessments, limitations, commitments, and history use the same semantic/query substrate as every other referent.

`CapabilityEvaluator` is the only capability authority. A current capability assessment requires:

```text
semantic competence
∧ registered implementation
∧ component health
∧ required input channel
∧ required output/effect channel
∧ sufficient resources
∧ permission and policy authorization
∧ contextual preconditions
```

Observed reliability and current degradation qualify the result.

A static entity schema, phrase template, or capability list cannot override live evidence.

Self-description must query current assessments and ordinary semantic records, then pass through the normal response planner and NLG pipeline.

## 12. State, event, place, time, and cause law

States are typed predications governed by `StateDimensionSchema`. State values support:

```text
boolean
enum
text
quantity + unit
entity reference
place reference
time reference
set
distribution
structured coordinate
```

Every state assertion distinguishes:

```text
valid time
observation/assertion time
context
source/evidence
current versus historical occupancy
```

Events are event-kind predications with identity, participants, aspect, time, and context.

Spatial, temporal, and causal meanings are predications, not structural links.

Temporal order does not imply causation. Causal hypotheses preserve:

```text
cause and effect propositions/events
context
mechanism or schema basis
support and counterevidence
causal warrant grade:
  reported_claim | contextual_rule | predictive_association |
  mechanism_supported | intervention_supported
intervention/counterfactual status
confidence
```

Predicted effects do not mutate actual state. Actual effects require execution or observation plus reconciliation and commit.

## 13. Context and common-ground law

Every proposition is evaluated in an explicit `ContextFrame`.

Minimum contexts:

```text
actual
reported
belief
hypothetical
conditional
counterfactual
desired
simulation
quoted
```

Contexts may be nested and have explicit accessibility/inheritance policies. Content in reported, belief, hypothetical, conditional, counterfactual, simulated, or quoted contexts may not enter actual-world truth without an explicit inference/evidence rule.

`CommonGroundManager` tracks who asserted, asked, accepted, rejected, corrected, promised, answered, or left unresolved which proposition. It records actual dispatched communication, not intended text.

## 14. Attention, appraisal, needs, values, and goals

Attention changes accessibility to cognition, not truth.

Workspace selection may use:

```text
relevance
novelty
uncertainty
contradiction
urgency
goal impact
causal consequence
social/discourse obligation
resource cost
```

Appraisal variables are functional control signals, not claims of subjective feeling.

Needs generate goals from state constraints, commitments, and gaps. Stable values and policies constrain planning. Minimum policy goals include:

```text
truthfulness
safety
permission integrity
privacy
commitment integrity
semantic coherence
resource boundedness
```

A `GoalRecord` denotes a desired proposition or information state. It may not be a free-form response label such as `answer_concept` or `store_patch`.

## 15. Planning, operation, and execution law

Every action—internal, communicative, or external—is an `OperationInstance` instantiated from `OperationSchema`.

Minimum cognitive operations:

```text
attend
retrieve
query
compare
infer
simulate
probe
assimilate
validate
store
explain
plan
```

Minimum communicative operations:

```text
assert
ask
answer
acknowledge
clarify
correct
qualify
refuse
promise
```

External operations are adapter-backed and capability/permission gated.

Operation lifecycle:

```text
proposed
planned
authorized | blocked
started
succeeded | failed | partial | timed_out
reconciled
committed
```

`Planner` is the sole plan authority. `OperationAuthorizer` is the sole permission/safety/capability gate. `OperationExecutor` executes authorized operations only. `ExecutionLedger` records actual outcomes.

No graph-building, interpretation, or response-planning stage may execute state effects.

## 16. Commit-before-claim law

All persistent mutations are typed `MutationOperation`s in a `MutationSet`.

Every mutation is classified as required or auxiliary and has an exact semantic identity.

Two commit moments use the same `CommitCoordinator`:

1. **critical pre-response commit** — facts, requested writes, state transitions, operation outcomes, and learned schemas that the response may claim;
2. **output/discourse commit** — actual output event, common-ground effects, promises, pending questions, and transport outcome after dispatch.

A response may say “I stored it,” “I learned it,” “I changed it,” or “I completed it” only when every required mutation for that claim committed.

Auxiliary concept or schema observations cannot satisfy an unrelated required write.

## 17. Learning law

Learning is an ordinary kernel operation over the same schema store and semantic model.

A learning transaction is created only for a concrete gap that blocks an interpretation, query, plan, operation, or realization goal.

Lifecycle:

```text
gap
→ exact target artifact and missing fields
→ typed hypothesis
→ minimal semantic probe
→ ordinary interpretation of returned evidence
→ provisional child schema snapshot
→ replay from earliest affected checkpoint
→ structural closure and competency tests
→ commit or rollback
→ resume original goal
```

A learning transaction cannot be successful merely because fields were filled or a status changed. Success requires:

- an executable artifact changed;
- the ordinary resolver uses the new schema version;
- the blocked case replays successfully;
- competency and contradiction tests pass;
- intended scope and provenance are preserved.

Replay may never repeat already dispatched external actions.

## 18. Semantic metalanguage law

CEMM must natively understand enough semantic metalanguage to learn new meanings without phrase-specific code.

Minimum boot predicates include:

```text
means
lexicalizes
defines
is_a
same_as
subtype_of
has_semantic_kind
has_role
role_requires
role_accepts
has_precondition
has_effect
has_state_dimension
has_value_type
applies_to
before
after
causes
enables
prevents
capable_of
requires_operation
realized_as
```

Metalanguage assertions are ordinary predications and propositions about schema referents. They pass through grounding, epistemics, authorization, learning validation, and commit.

## 19. NLG law

`ResponsePlanner` is the only response-content authority.

It consumes selected semantic propositions, epistemic/capability assessments, execution outcomes, commit outcomes, goals, and discourse state. It produces a language-neutral `SemanticMessagePlan`.

NLG stages:

```text
content selection
rhetorical/discourse organization
information structure and focus
referring-expression generation
aggregation
stance and epistemic qualification
lexicalization
syntax planning
morphology
orthography/channel rendering
dispatch
```

Language renderers choose wording, not truth or response content.

Every generated clause must trace to a selected semantic item and evidence/ledger/commit provenance. Opaque IDs, open ports, role labels, or internal placeholders cannot become public text.

Generated content should round-trip into compatible semantic candidates under the same language pack.

## 20. Core-loop law

The canonical event-driven cognitive cycle is:

```text
ORIENT
→ UNDERSTAND
→ KNOW
→ DECIDE
→ ACT AND RECONCILE
→ CRITICAL COMMIT
→ COMMUNICATE
→ OUTPUT COMMIT AND CONSOLIDATE
```

The detailed ordering in `CORE_LOOP.md` is mandatory.

A `KernelSnapshot` pins schema, memory, common-ground, self-health, policy, resource, goal, learning-transaction, competence-suite, type-registry, inference-policy, and adapter-contract revisions for one cycle. Stages return immutable artifacts. Hidden global mutation is forbidden.

Learning replay uses a child schema snapshot and a typed checkpoint. It is not a second top-level loop.

## 21. Authority law

Exactly one component is authoritative for each decision. The binding table is `AUTHORITY_MATRIX.md`.

Compatibility helpers may translate representations but may not:

- independently select meaning;
- independently declare truth;
- independently derive capability;
- independently authorize operations;
- independently write memory;
- independently choose response content.

## 22. Folder and import law

The canonical tree is defined in `KERNEL_FOLDER_STRUCTURE.md`.

Hard import boundaries:

```text
kernel/model       → standard library only
kernel/schema      → model
kernel engines     → model + schema + read interfaces
kernel/commit      → model + schema + writable persistence interfaces
language           → public semantic interfaces only
adapters           → public operation/signal interfaces only
app                → dependency assembly
legacy             → isolated; canonical kernel never imports it
```

Persistence is forbidden in perception, composition, grounding, NLG, and language adapters.

## 23. Forbidden implementation patterns

Do not:

- add transcript phrases to query, write, capability, or response executors;
- learn into an overlay the ordinary schema resolver does not use;
- retain action and predicate schema stores as separate semantic authorities;
- represent semantic relations both as predications and typed graph edges;
- use free-form instruction kinds as semantic content;
- equate structural executability with actual-world truth;
- call a provisional/self-certified schema fully understood;
- count transformed copies from one evidence lineage as independent support;
- activate recursive clusters without declared fixed-point or inverse semantics;
- let a narrow access scope blindly shadow wider actual-world meaning;
- store inferred or hypothesized schema fields as if the user asserted them;
- persist effect authorization as a schema property;
- treat typical/default features as constitutive identity;
- invalidate only an assessment while dependent answers/plans/inferences remain live;
- treat goals as strings such as `answer_relation` or `store_patch`;
- hard-code universal role names in a graph builder;
- create role-placeholder entities or concepts;
- execute predicted effects while building or interpreting a graph;
- infer actual-world truth from reported, belief, hypothetical, quoted, or simulated contexts without a rule;
- confirm a write because any patch committed;
- advertise a capability because a JSON slot says it exists;
- parse generated text to recover operational meaning;
- let language templates choose factual content;
- use missing public wording as a reason to expose internal IDs;
- run the old and new pipelines in parallel and call the new path authoritative;
- call shadow code complete.

## 24. Completion gate

A change is complete only when:

- it corrects the earliest wrong authority;
- no later phrase or output workaround is required;
- one authority owns every changed decision;
- semantic, schema, and control layers remain distinct;
- snapshot and mutation invariants pass;
- query/write/action behavior is exact and contract-driven;
- self/capability claims are live-evidence backed;
- learning changes the ordinary resolver and passes lineage-aware replay/competence;
- activation is snapshot-atomic and context-admissible;
- dependency downgrade retracts all derived cognition;
- response clauses are semantically selected and provenance-bound;
- multilingual graph-equivalence tests pass where applicable;
- legacy imports are absent from the canonical kernel;
- documentation status is updated honestly.
