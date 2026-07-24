# CEMM v1 Architecture

**Status:** executable architecture aligned to the current CEMM v3.5.1 target architecture and runtime contracts.  
**Purpose:** prove that CEMM can keep one exact semantic substrate while using neural models for open compositional interpretation, semantic workspace dynamics, learnable definitions, and grounded language realization without domain-schema or phrase-program explosion.

Canonical repository documents reviewed for this architecture:

- `ARCHITECTURE.md` — canonical grounded semantic brain architecture (reviewed blob `a9f3b6712f7253422cd5b5f183db29860dd16232`).
- `RUNTIME_PLAN.md` — canonical concrete runtime implementation contract (reviewed blob `197360cf0d7ba8b47303b2bf69570d07a592e2c8`).
- `CORE_LOOP.md` — canonical logical Stage 0–22 contract (reviewed blob `118332e54d84d6ee98f7780c2fb6ab7fc98b0bd9`).

v1 is intentionally smaller than production CEMM. Where it compresses or omits a canonical subsystem, that gap is stated explicitly below.

---

## 1. v1 thesis

The core v1 invariant is:

```text
Exact semantics are authority.
Neural computation proposes, ranks, composes and realizes semantics.
Neural latent state never becomes a second semantic ontology.
```

v1 fixes the remaining v3 ceiling:

```text
v3
surface
→ choose one learned whole semantic-program class
→ fill slots
→ exact validation

v1
surface + grounded mention evidence
→ shared Transformer
→ intent
→ application-slot presence
→ operator per slot
→ role → grounded-source pointers
→ N-best graph candidates
→ exact compile / clamp
→ recurrent candidate settling
→ stable or unresolved CSIR-like graph
```

There is no `TYPE_ASSERTION_001`, `MOTHER_IN_LAW_ARRIVAL_PROGRAM`, or equivalent closed semantic program catalogue.

---

## 2. Unified CEMM architecture

```text
┌──────────────────────────────────────────────────────────────────────┐
│ IMMUTABLE SEMANTIC AUTHORITY                                         │
│                                                                      │
│ Kernel Semantic ABI · CSIR constructors · exact operators/roles      │
│ semantic definitions · promoted rules · language/model artifacts     │
│ operational profiles · causal mechanisms · authorizations            │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ exact pins
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ MUTABLE GROUNDED WORLD / DISCOURSE                                   │
│                                                                      │
│ referents · claims · state timelines · events · evidence · discourse │
│ world revision · discourse revision · observation revision           │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ bounded indexed retrieval
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ CYCLE WORKSPACE / ACTIVE SEMANTIC WORKSPACE                          │
│                                                                      │
│ evidence lattice · referent candidates · CSIR candidates             │
│ relevant exact/derived facts · self state · recent transitions       │
│ query restrictions · proof dependencies · frontiers · goals          │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ NEURAL SEMANTIC DYNAMICS                                              │
│                                                                      │
│ structured graph prediction · relevance ranking · attention          │
│ N-best candidate scoring · language realization-plan selection       │
└─────────────────────────────────┬────────────────────────────────────┘
                                  │ exact compiler / hard constraints
                                  ▼
┌──────────────────────────────────────────────────────────────────────┐
│ EXACT SEMANTIC COGNITION                                              │
│                                                                      │
│ settle · query · infer · learn candidate · simulate · choose goal     │
│ commit only at explicit boundaries                                   │
└───────────────┬──────────────────────────────┬───────────────────────┘
                │                              │
                ▼                              ▼
       RESPONSE SEMANTICS               LEARNING FRONTIERS
                │                              │
                ▼                              ▼
       semantic-pointer NLG         provisional candidate authority
                │                              │
                ▼                              ▼
       cheap proof verification       competence / evidence / review
                │                              │
                ▼                              ▼
       authorized emission             new authority generation
                │                              │
                └───────────────► next-cycle activation ◄─────────────┘
```

This is a compact realization of the canonical repository split between one `CognitiveState_t`, exact CSIR authority, recurrent semantic dynamics, explicit durable-effect boundaries, Response CSIR, realization and semantic-preservation verification.

---

## 3. Exact semantic plane vs dynamic semantic plane

### Exact plane

The exact plane owns:

```text
opaque semantic identity
operator/role typing
CSIR-compatible graph structure
world claims and provenance
promoted definitions/rules
state dimensions and values
identity/designation facts
exact proof lineage
authority generation pins
```

### Dynamic plane

The dynamic plane owns:

```text
activation
neural likelihood
workspace relevance
salience / recency
uncertainty
N-best alternatives
candidate competition
settling energy/posterior
learning frontiers
```

Dynamic scores can choose among **valid** semantic candidates. They cannot make an invalid role binding, unknown ontology class, unsupported causal fact, or unpromoted rule authoritative.

---

## 4. Semantic algebra and production CSIR mapping

The executable implementation intentionally uses five compact projection operators:

```text
op:designation
op:type
op:relation
op:state
op:event
```

These are **not proposed replacements for production CSIR**.

They compile conceptually to the canonical CSIR kernel:

```text
atom/filler           → TERM / VARIABLE
application           → APPLICATION
role=value            → BINDING
state/time/context    → QUALIFIER where appropriate
cross-app reference   → APPLICATION/BINDING or scoped graph reference
rule proof            → PROOF_LINK DAG
multi-clause graph    → normalized connected CSIR graph
```

Production CEMM retains:

```text
TERM
VARIABLE
APPLICATION
BINDING
QUALIFIER
SCOPE_EMBEDDING
COORDINATION
PROOF_LINK
```

No domain concept should require a new kernel constructor.

---

## 5. Anti-bloat architecture

The schema growth rule is:

```text
new word/name
    → designation data

new entity/event occurrence
    → world atom / occurrence data

new concept/relation/state value
    → semantic atom + definition evidence

new observation
    → existing operator composition

new reusable implication/definition
    → graph rule over existing operators

new inference result
    → ephemeral closure by default

new domain
    ≠ new Python class
    ≠ new SQL schema
    ≠ new semantic program class
```

### Five universal operator shapes remain fixed

Importing family knowledge, friction knowledge, new people, or new events does not expand the operator schema.

### Derived closure is not materialized by default

```text
Durable:
  observed/admitted facts
  reviewed/promoted definitions
  evidence/provenance

Transient:
  derived type closure
  inferred family relations
  inferred marital state
  existential witnesses
  query-specific proof paths
```

Repeated queries therefore do not grow permanent memory merely because the system reasons repeatedly.

---

## 6. Open compositional structured semantic prediction

### Input representation

Natural language is first grounded into evidence placeholders:

```text
Ada is a doctor.

→ @A0<entity> is a @A1<concept>.
```

The semantic-kind tags are language-independent evidence from the meaning DB, not English grammar categories.

### Neural outputs

The Transformer predicts independent structured fields:

```text
intent:
  assert | query | describe

for each application slot:
  present?
  operator
  role:subject    → grounded source
  role:object     → grounded source
  role:class      → grounded source
  role:value      → grounded source
  ...
```

Grounded source classes are structural pointers:

```text
A0..A7
participant:user
participant:system
new entity occurrence
new event occurrence
none
```

The model does **not** predict arbitrary domain IDs from a global vocabulary.

### Exact compile barrier

Candidate application fragments are checked against exact operator-role contracts:

```text
op:type.role:class        requires concept
op:relation.role:relation requires relation_type
op:state.role:value       requires value
op:event.role:type        requires event_type
```

Impossible predictions are clamped/rejected.

State dimensions may be restored from exact meaning data when a value has one unique licensed dimension.

---

## 7. N-best candidate generation and recurrent settling

The system no longer relies on one greedy whole-program prediction.

```text
Transformer distributions
        │
        ├─ intent alternatives
        ├─ topology alternatives
        ├─ operator alternatives
        └─ role-pointer alternatives
        ▼
N-best structured candidates
        ▼
exact compilation
        ▼
invalid candidates removed
        ▼
canonical-equivalent candidates merged
        ▼
recurrent inhibition / posterior sharpening
        ▼
settled graph OR ambiguity frontier
```

The recurrent loop is deliberately small, but it proves the correct boundary:

- neural score initializes activation;
- exact semantics clamp impossibility;
- incompatible exact alternatives inhibit one another;
- close alternatives can remain unresolved.

Production Stage 6–7 should replace this small settler with the full typed activation/factor graph and semantic-attractor machinery.

---

## 8. Clause-compositional document architecture

The model is not trained to memorize one whole multi-sentence program.

```text
raw document
    ↓
mention/coreference grounding
    ↓
clause split
    ↓
clause-local placeholder canonicalization
    ↓
open structured prediction per clause
    ↓
exact compile + N-best settle
    ↓
map to document-global referents
    ↓
compose connected graph
```

Example held out from any combined document training class:

```text
Ada is a doctor.
She arrived today.
```

becomes:

```text
type(Ada, doctor)

event(E)
type(E, arrive)
actor(E, Ada)
time(E, today)
```

The same `Ada` referent is preserved across clauses.

---

## 9. Grounded identity and designation architecture

Identity remains independent from names/labels:

```text
OPAQUE REFERENT IDENTITY
        │
        ├─ full name
        ├─ given name
        ├─ surname
        ├─ alias
        ├─ localized name
        ├─ language-invariant designation
        └─ context-specific realization label
```

Ranking evidence may include:

```text
reviewed prior
preferred flag
language match
usage frequency
discourse salience
semantic type compatibility
```

Two different entities may share exactly the same surface name. A close candidate margin produces clarification rather than silent identity merge.

### Authority vs world identity

The storage-level distinction (`cemm/store.py`):

```text
authority_scope = authority
    semantic concepts, relations, dimensions, reviewed lexical authority

authority_scope = world
    conversation-created people/events/occurrences
```

World-occurrence atoms are excluded from authority hashing.

---

## 10. Self identity and session-state architecture

`participant:system` / self is represented as an ordinary resolved semantic participant with operational state dimensions (`cemm/selfstate.py`).

Current dimensions include:

```text
response_state
interpretation_state
epistemic_state
```

Typical transitions:

```text
ready → processing → ready
resolved ↔ unresolved
sufficient ↔ insufficient/uncertain
```

Self state enters the active semantic workspace and may condition response selection and neural attention.

Production should expand this into typed self capability/resource/attention/goal state without creating a chatbot-specific parallel ontology.

---

## 11. Semantic workspace architecture

Long-term exact storage is not fed wholesale into a Transformer.

```text
exact world + discourse + proof graph
        ↓ indexed/bounded retrieval
candidate slots
        ↓ neural relevance scorer
TOP-K semantic workspace
        ↓ shared neural dynamics / exact reasoning
```

A slot may represent:

```text
exact fact
derived fact
self state
query restriction
recent transition
proof dependency
salient referent
```

Slot features include:

```text
semantic overlap
self relevance
confidence
derived/exact status
salience
recency
activation score
```

The current implementation caps the workspace at 24 selected slots (`cemm/config.py`).

---

## 12. Learnable semantic definitions and rules

This is the main learning capability.

### No closed rule class

The rule Transformer predicts graph pieces:

```text
rule kind
antecedent application slots
consequent application slots
operator per slot
role → variable / existential / grounded-anchor pointers
```

Variable source classes are structural:

```text
V0 V1 V2
E0 E1
A0..A7
```

### Example

Teaching:

```text
A mother in-law is the mother of a partner.
```

is induced as:

```text
IF
  relation(?v0, mother_in_law, ?v1)

THEN
  relation(?v0, mother_of, !e0)
  relation(!e0, partner, ?v1)
```

No family-specific parser or rule template exists in Python.

### Learning lifecycle

```text
teaching evidence
    ↓
structured rule candidate
    ↓
exact rule validation
    ↓
rule_candidates: provisional
    ↓ additional independent evidence / competence
semantic deduplication
    ↓
promoted rule artifact
    ↓
new authority material
    ↓
explicit authority reload/activation
    ↓
usable in later inference
```

A provisional rule never executes as authority.

A promoted rule does not become visible to an already pinned runtime until explicit authority activation/reload.

---

## 13. Family inference without schema growth

After the mother-in-law definition is promoted and activated:

```text
OBSERVED
mother_in_law_of(M, self)

        ↓ learned compositional definition
exists P:
mother_of(M, P)
partner_of(P, self)

        ↓ generic subrelation rule
spouse_of(P, self)

        ↓ generic relation→state rule
self.marital_status = married
```

Then:

```text
Am I married?
→ Yes.
```

The derived facts remain ephemeral and proof-bearing.

No `MotherInLawSchema`, `MarriageSchema`, or dedicated response rule is introduced.

---

## 14. Reviewed open-vocabulary acquisition

The bridge between unknown forms and structured semantic training is in `cemm/acquisition.py`.

Example reviewed training document:

```text
Friction is resistance.
```

Reviewer/trainer supplies mention anchors only:

```text
Friction     kind=concept
resistance  kind=concept
```

Pipeline:

```text
unknown reviewed mention
    ↓
create opaque semantic atom
    ↓
create exact designation fact
    ↓
publish/reload lexical authority
    ↓
ordinary open structured interpreter
    ↓
op:type(instance=friction, class=resistance)
    ↓
commit scoped learned meaning
```

Afterward:

```text
What is Friction?
→ Friction is resistance.
```

No new schema or code path is required.

### Autonomous unknown-form discovery

v1 adds `AutonomousAcquirer` in `cemm/acquisition.py` for autonomous unknown-span discovery without requiring reviewed mention-kind anchors for every unknown word. This addresses a gap that remained in v4.

---

## 15. Multilingual architecture

Language packs are projection artifacts over the same semantics:

```text
English surface ─┐
Spanish surface ─┼─→ shared referents / atoms / rules / world graph
future language ─┘
```

Promoted semantic rules are language-independent.

A rule learned through an English teaching interface can be reused by a Spanish query path after the same authority generation is active.

No duplicate Spanish family ontology is created.

---

## 16. Response construction and NLG

Response words with semantic content must be grounded meaning.

Examples in the meaning DB:

```text
evidence
information
conflict
meaning
sufficiency
consistency
stored
unresolved
```

Response planning produces ordinary semantic facts/plans (`cemm/response.py`).

```text
query result / self state / frontier
        ↓
communication goal
        ↓
response semantic facts
        ↓
pointerized semantic serialization
        ↓
trained language surface-plan selector
        ↓
exact designations fill semantic pointers
        ↓
cheap proof verification
        ↓
emission
```

A generated content span must trace to an exact semantic reference.

Internal opaque IDs are forbidden from surfacing when no authorized referring expression exists.

Independent full round-trip is policy-driven for novelty/risk/audit; it is not a normal per-message tax.

---

## 17. Authority generations vs mutable revisions

The canonical separation is preserved:

```text
RuntimeAttestation
AuthorityGeneration
AuthoritySnapshot

≠

WorldRevision
DiscourseRevision
ObservationRevision
AuditRevision
EffectJournalRevision
```

### Implementation behavior

- base/promoted semantic atoms and rules are authority material;
- conversation-created entity/event atoms are `authority_scope=world`;
- world occurrences never enter authority hashes;
- rule promotion creates new authority material;
- an already pinned runtime does not execute newly promoted rules;
- `reload_authority()` explicitly activates the newer generation.

This models the production rule that active passes never switch semantic authority mid-cycle.

---

## 18. Persistence and anti-bloat boundaries

```text
Workspace by default:
  candidate interpretations
  N-best graphs
  derived closure
  solver traces
  semantic attractors
  query matches
  response candidates
  provisional reasoning

Durable only at explicit commit:
  admitted observations/claims
  scoped participant/world facts
  promoted language/semantic authority
  state transitions
  emitted common ground
  effect journals where applicable
```

Stage numbers are logical boundaries, not database transaction boundaries.

---

## 19. Canonical Stage 0–22 mapping

| Canonical stage | v1 equivalent | Coverage |
|---|---|---|
| 0 Orient/pin semantic brain | runtime attestation + authority/read generation + self/session state | Partial but explicit |
| 1 Observe multimodal evidence | language observation envelopes/observations table | Text only |
| 2 Encode form/sensor evidence | designation/reference grounding + delex semantic-kind evidence | Language subset |
| 3 Ground referents | ranked labels, participant frame, pronoun/discourse resolution | Implemented subset |
| 4 Project entitled state spaces | exact type/value/dimension checks + semantic workspace retrieval | Partial |
| 5 Compile candidates to CSIR | open structured predictor + exact operator/role compiler | Strong proof; compressed CSIR |
| 6 Recurrent meaning dynamics | N-best energies + inhibition + workspace ranking | Minimal proof |
| 7 Stabilize attractors | posterior/margin settle or explicit frontier | Minimal proof |
| 8 Build proposition/event/query/discourse | assertions, events, queries, describe structures | Partial |
| 9 Epistemic placement/world belief | support/deny, provisional/reviewed/promoted, scoped state | Partial |
| 10 Query/explain | exact graph matching + proof DAG | Implemented subset |
| 11 Learning/frontiers | unknown/frontier + structured rule candidates + acquisition | Implemented subset |
| 12 Causal simulation | causal rules kept separate from actual closure | Representation only |
| 13 Commit authorized knowledge | generation commits; scoped world learning | Implemented subset |
| 14 Capability/impact/affect/significance | self/workspace hooks only | Not implemented |
| 15 Goals | data-backed response goal selection | Narrow response-goal subset |
| 16 Plan/execute/observe | none beyond response action | Not implemented |
| 17 Reconcile/re-enter | authority reload only; no operation re-entry loop | Minimal |
| 18 Construct Response CSIR | response semantic plan/facts | Compressed implementation |
| 19 Realize language/modality | semantic-pointer learned surface plans | Implemented language subset |
| 20 Verify/authorize emission | cheap pointer/grammar/internal-ID proof | Implemented subset |
| 21 Commit output/common ground | limited discourse salience; no full common-ground journal | Partial |
| 22 Consolidate/invalidate/replay/finalize | rule promotion + authority activation demonstration | Partial |

---

## 20. Runtime performance architecture

The intended scalable path is sparse/hybrid:

```text
exact indexed semantic store
        ↓
ANN / typed lookup / discourse retrieval
        ↓
32–256 candidate semantic slots
        ↓
shared Transformer attention
        ↓
structured semantic heads
        ↓
exact compiler + bounded solver
```

Do not:

```text
scan entire graph every turn
run whole-store hashes every request
feed millions of facts into attention
materialize all inference closure
retrain language models for ordinary world facts
```

v1 separates model cache invalidation from ordinary world learning and adds a bounded model cache (`cemm/runtime.py`) to prevent unbounded memory growth.

---

## 21. Training architecture

The main bottleneck is now **training/data quality and coverage**, not another domain-schema redesign.

### Training targets should emphasize

```text
surface evidence → referent candidates
surface evidence → operator/application slots
role → semantic-source pointers
qualifiers/scope/time/modality
cross-clause referent links
N-best ambiguity calibration
semantic definition/rule induction
Response semantics → faithful language plans
```

### Recommended curriculum

1. foundational identity/type/relation/state/event composition;
2. paraphrase/voice/word-order convergence;
3. discourse/coreference;
4. temporal state transitions;
5. definitional and rule-learning corpora;
6. query/proof/reasoning supervision;
7. multilingual projection;
8. Response CSIR/NLG fidelity;
9. causal/state/capability structures;
10. multimodal grounding.

A pretrained multilingual encoder/decoder with CEMM-specific semantic heads is likely more efficient than learning general language morphology/syntax from scratch.

---

## 22. What v1 demonstrably fixes

### Inherited from v4

- no closed whole-semantic-program classification;
- structured prediction of operators and role pointers;
- N-best exact candidate compilation and settling;
- clause-compositional unseen document topology;
- learnable relation-definition graph rules;
- provisional rules cannot execute;
- semantic deduplication of learned rules;
- evidence threshold before promotion;
- promoted authority requires explicit activation/reload;
- world occurrence atoms excluded from authority hashes;
- reviewed acquisition of genuinely new concept vocabulary;
- identity/designation separation;
- same-name ambiguity handling;
- multilingual reuse of semantic authority;
- semantic self state and workspace;
- bounded ephemeral inference;
- no query-driven persistent bloat;
- grounded operational response concepts;
- semantic-pointer NLG without mandatory full reparse;
- internal IDs blocked from surface output;
- deterministic language-pack training artifacts;
- exact kind constraints remain authority.

### New in v1

- **configurable thresholds** — all magic numbers (workspace cap, settle margin, evidence threshold, etc.) centralized in `cemm/config.py` and tunable without code changes;
- **full CLI coverage** — `cemm/cli.py` exposes all runtime operations (chat, teach, query, acquire, train, rules, export, reload) as first-class commands;
- **inference timeout** — `cemm/inference.py` enforces a bounded timeout on inference passes, preventing runaway reasoning on pathological inputs;
- **bounded model cache** — `cemm/runtime.py` caps the model cache size with LRU eviction, preventing unbounded memory growth across long sessions;
- **autonomous unknown-form discovery** — `AutonomousAcquirer` in `cemm/acquisition.py` can discover unknown spans without requiring reviewed mention-kind anchors for every word;
- **modular structure** — the monolithic implementation is split into focused modules (see Section 26), improving maintainability and testability without changing the architecture.

---

## 23. Explicit remaining gaps

These are not claimed solved by v1.

### Full production CSIR expressiveness

Missing or compressed:

```text
scope embeddings
coordination
true multi-valued bindings
quantification
modal/negation scope
ordered/set-valued structures
rich qualifiers
```

### Full recurrent semantic dynamics

The current N-best settler is a small proof. Production needs typed factor/message families, calibrated energy/posterior semantics, convergence certification, partial attractors and richer inhibition.

### General open-domain semantic rule induction

v1 demonstrates relational compositional definition induction. It does not yet robustly induce arbitrary:

```text
state schemas
transition functions
causal mechanisms
quantified defaults
counterfactual mechanisms
capability dependencies
```

### Spanish rule induction (training data gap)

While the architecture supports multilingual reuse of semantic authority, Spanish-specific rule induction remains limited by a training data gap. Spanish language packs can realize English-learned rules, but inducing rules directly from Spanish teaching text requires more training corpora.

### Basic tokenizer

The current tokenizer (`cemm/interpreter.py`) is a simple delexer. Production needs a proper tokenizer with subword handling, morphological awareness, and language-specific segmentation.

### No thread safety

The runtime is single-threaded. Concurrent access to the store, workspace, or model cache is not safe. Production needs locking or actor-model isolation.

### No schema migration

There is no schema migration system. If the store format changes, existing serialized stores must be rebuilt. Production needs versioned snapshots with forward/backward migration.

### Synthetic workspace training

Workspace relevance scoring is trained on synthetic data. Production needs real discourse-derived training signal for workspace slot selection.

### Tiny proof models

The bundled Transformers are tiny train-at-startup proof models. They are not performance/quality benchmarks.

### Rule competence system

The implementation uses repeated semantic evidence as a minimal competence gate. Production needs held-out counterexamples, requested-use competence, review policy, dependency closure, invalidation/replay and signed publication.

### Full temporal/state algebra

The implementation handles exclusive state supersession and inferred state effects but not the complete typed categorical/continuous/vector/distribution algebra in canonical architecture.

### Causality/counterfactuals

Causal rules remain isolated from factual entailment, but full mechanism matching, `do()` interventions, abduction and counterfactual proof DAGs are not implemented.

### Capability/goal/action stack

Stages 14–17 are largely outside the implementation.

### Full discourse/common ground

Salience/coreference are present; commitments, correction/retraction, open-question structure and common-ground commit semantics remain partial.

### Generative referring expressions

The system blocks internal IDs but does not yet robustly construct novel descriptions like "the woman who arrived today."

### Production model scale

The bundled Transformers are tiny train-at-startup proof models. They are not performance/quality benchmarks.

---

## 24. Architecture freeze rules for post-v1 development

Before adding any new schema or runtime branch, ask:

```text
Can this be represented as:
  an atom?
  a designation?
  an existing operator application?
  a state dimension/value?
  a graph rule over existing operators?
  a causal mechanism over typed roles/state?
  an operational profile?
  a learned parameter artifact?
```

Only if the answer is demonstrably no should the Kernel Semantic ABI be reconsidered.

Forbidden shortcuts:

```text
one regex per phrase
one Python class per concept
one SQL table per domain
one semantic program class per utterance topology
response strings whose content is not grounded meaning
neural latent labels treated as semantic truth
inferred closure persisted merely because it was queried
newly promoted authority silently visible to pinned cycles
world occurrences contaminating authority hashes
```

---

## 25. Final v1 architecture

```text
OBSERVATION
   │
   ▼
LANGUAGE / MULTIMODAL EVIDENCE
   │
   ▼
GROUNDED REFERENT + SEMANTIC-KIND CANDIDATES
   │
   ▼
OPEN STRUCTURED TRANSFORMER
   │
   ├─ intent
   ├─ application slots
   ├─ operators
   └─ role → semantic pointers
   │
   ▼
N-BEST GRAPH CANDIDATES
   │
   ▼
EXACT CSIR COMPILER / HARD CLAMPS
   │
   ▼
RECURRENT SEMANTIC SETTLING
   │
   ├─ stable graph
   ├─ alternatives
   └─ frontier
   │
   ▼
GROUNDED WORLD / QUERY / LEARNING
   │
   ├──────────── query proof ──────────────┐
   │                                      │
   ├──────── provisional rule ──► competence/promotion ─► new authority
   │                                      │
   ▼                                      │
ACTIVE SEMANTIC WORKSPACE                  │
   │                                      │
   ▼                                      │
RESPONSE SEMANTICS                        │
   │                                      │
   ▼                                      │
SEMANTIC-POINTER NLG                      │
   │                                      │
   ▼                                      │
CHEAP PROOF / SELECTIVE ROUNDTRIP         │
   │                                      │
   ▼                                      │
AUTHORIZED EMISSION                       │
   │                                      │
   └──────── world/discourse delta ───────┘
```

The intended post-v1 engineering direction is now clear:

> **Scale training, structured semantic coverage, recurrent settling, rule competence and multimodal grounding without reopening the kernel or reintroducing domain/program-class bloat.**

---

## 26. Module structure

v1 reorganizes the monolithic implementation into focused modules under the `cemm/` package. Each module has a single responsibility and clear boundaries. The architecture is unchanged — only the implementation structure is modular.

```
cemm/
  config.py       — configurable thresholds (workspace cap, settle margin,
                     evidence threshold, inference timeout, cache sizes)
  constants.py    — operator/role enums, authority scopes, fixed constants
  model.py        — Fact, helpers, AmbiguousReferent
  store.py        — Store with authority/world separation, indexed retrieval,
                     authority hashing, reload/activation
  codec.py        — StructuredNet, RuleNet, StructuredSemanticCodec
                     (neural structured prediction + encoding)
  compiler.py     — ExactStructuredCompiler
                     (operator-role contract validation, clamps)
  settler.py      — SemanticSettler
                     (N-best inhibition, posterior sharpening, frontier)
  interpreter.py  — Interpreter, SurfaceCodec, Delexer
                     (surface → grounded evidence → structured candidates)
  inference.py    — Inference with timeout
                     (rule application, existential witnesses, proof DAG,
                     bounded by configurable timeout)
  rules.py        — RuleLearner
                     (structured rule candidate induction, validation,
                     semantic deduplication, promotion gating)
  workspace.py    — Workspace, WorkspaceNet
                     (TOP-K slot selection, relevance scoring, slot features)
  selfstate.py    — SessionSelf, StateTransition
                     (self identity, operational state dimensions, transitions)
  response.py     — ResponsePlanner, pointerize_fact
                     (communication goal → response semantic facts →
                     pointerized serialization)
  realizer.py     — PointerRealizer, LanguagePack
                     (semantic pointers → surface language, designation fill,
                     language-pack artifacts)
  runtime.py      — Runtime with bounded model cache
                     (attestation, authority generation/snapshot, cycle
                     orchestration, LRU-bounded model cache)
  acquisition.py  — acquire() + AutonomousAcquirer
                     (unknown-form → opaque atom → designation fact →
                     lexical authority; autonomous span discovery)
  trainer.py      — language pack trainer
                     (deterministic language-pack artifact generation from
                     reviewed training documents)
  cli.py          — CLI with all commands
                     (chat, teach, query, acquire, train, rules, export,
                     reload, status)
```

### Module dependency flow

```text
config.py ──────► (all modules read thresholds)
constants.py ───► (all modules reference enums)

model.py ──────► store.py ──────► runtime.py
                  ↑                  ↑
codec.py ──────► interpreter.py ────► runtime.py
compiler.py ───► interpreter.py
settler.py ────► interpreter.py
inference.py ──► runtime.py
rules.py ──────► runtime.py
workspace.py ──► runtime.py
selfstate.py ──► runtime.py
response.py ───► runtime.py
realizer.py ───► runtime.py
acquisition.py ► runtime.py
trainer.py ────► realizer.py
cli.py ────────► runtime.py + all subsystems
```

### Design principles for the modular split

1. **No circular imports** — dependencies flow downward; `runtime.py` is the composition root.
2. **Config is read-only** — `config.py` holds thresholds; no module mutates them at runtime.
3. **Store is the single semantic authority** — no other module maintains a parallel semantic store.
4. **Neural models are ephemeral** — `codec.py`, `workspace.py`, and `realizer.py` own model lifecycles; `runtime.py` caches them with bounded LRU.
5. **CLI is a thin shell** — `cli.py` parses arguments and delegates to `runtime.py`; no business logic in the CLI.
