# CEMM — Contextual Event Memory Model

CEMM is a **learning-first grounded semantic computational architecture** intended to grow reusable understanding from a small reviewed semantic and language substrate.

It is not a chatbot architecture, an intent classifier with memory, or a catalogue of phrases mapped to responses.

The long-term target is a **grounded semantic brain**: a system that represents exact meaning structurally, resolves meaning through recurrent compositional dynamics, maintains multimodal state, performs causal and counterfactual inference, learns recursively from prediction error and unresolved frontiers, and generates responses from semantic goals before language realization.

> **Current repository status:** the public runtime has cut over to the signed CEMM v3.5 Stage-0..22 runtime. Runtime cutover is complete, but the current v3.5 substrate still contains important architectural, correctness, performance, authority, identity, persistence, learning, realization, and semantic-productivity defects.
>
> **v3.5.1 must not be implemented directly on top of those defects.** The unified `IMPLEMENTATION_PLAN.md` integrates stabilization (Phases 0–4, Milestone M0) and semantic-brain migration (Phases 5–18) into one roadmap. It preserves exactness, provenance, permissions, effect authorization, and release integrity while removing authority overreach, whole-store coupling, hot-path verification, false identity collisions, unnecessary persistence, and concurrency bottlenecks.
>
> Do not describe v3.5 as fully semantically verified or v3.5.1 as implementation-ready until the acceptance gates pass.

---

## What CEMM is trying to achieve

CEMM should be able to start with a small reviewed substrate and progressively acquire reusable semantic competence.

A recognized form does not need to map directly to a complete intent or canned response.

The target computation is approximately:

```text
multimodal observation
→ form / signal analysis
→ lexical and structural evidence
→ referent grounding
→ semantic contribution activation
→ exact semantic-definition expansion
→ CSIR construction
→ recurrent compositional meaning dynamics
→ grounded state estimation
→ claims / queries / events / causal mechanisms
→ prediction and recursive inference
→ learning frontiers and prediction error
→ impact / significance / goals
→ semantic response construction
→ target-language realization
→ semantic-preservation verification
→ authorized external effect / emission
→ common-ground update
```

The target is **compositional, grounded, causal meaning**, not phrase coverage.

---

## Core architectural direction

CEMM v3.5.1 is being designed around two inseparable computational planes.

### 1. Exact semantic plane

This plane defines **what a meaning is**.

It contains:

```text
content-addressed CSIR graphs
exact semantic definitions
typed roles and bindings
scope, context, time and modality
semantic state dimensions
causal mechanism structure
operational profiles
proof and evidence lineage
exact authority closure
```

Meaning identity must be deterministic, replayable, versioned and content-addressed.

### 2. Recurrent semantic-dynamics plane

This plane defines **how meaning becomes active, competes, settles, predicts and learns**.

It contains:

```text
bottom-up multimodal evidence
top-down semantic prediction
typed recurrent message passing
activation and inhibition
uncertainty distributions
state estimation
causal propagation
attention and salience
prediction error
recursive learning
```

Continuous/neural-like dynamics may activate, rank and settle semantic structures.

They must never silently redefine exact semantic identity.

---

## Grounded meaning, not linguistic ontology

Language provides evidence for meaning.

Language is not the ontology.

Categories such as:

```text
noun
verb
adjective
adverb
pronoun
subject
object
auxiliary
```

are grammatical evidence and realization structures.

They must not become universal semantic laws.

For example:

```text
sentence subject ≠ universal actor
sentence object  ≠ universal affected entity
```

Action effects operate over **semantic roles bound to grounded referents**, independent of language-specific syntax.

The same semantic structure should survive:

* active/passive alternation;
* pro-drop;
* topic-prominent syntax;
* accusative/ergative alignment;
* different word orders;
* different morphological strategies.

---

## Multimodal state and causal meaning

Every grounded referent may participate in type-entitled state spaces such as:

```text
geospatial
temporal
physical
thermal
structural
biological
homeostatic
affective
social
epistemic
resource
capability
permission
goal
```

A state in one dimension does not become another dimension merely by renaming it.

Instead, cross-dimensional effects are represented through causal mechanisms.

Example:

```text
temperature change
→ thermal state
→ homeostatic consequence
→ comfort / stress consequence
→ affective / behavioural consequence
```

for an appropriate living entity.

For a server, the same thermal state may instead affect:

```text
cooling dependency
→ processing reliability
→ capability degradation
→ service failures
```

CEMM must infer these consequences from typed causal knowledge, not hardcoded English phrases or entity-specific `if` statements.

---

## Standing ordering laws

CEMM preserves these laws:

```text
perceive before answering
ground before committing identity
working cognition before durable memory
source before belief
claims before world admission
event occurrence before state mutation
time before current-state claims
permission before protected use/disclosure
safety before irreversible effect
authorization before execution/emission
commit before claiming a write
meaning before wording
prediction before learning update
```

The working cognitive graph is temporary and ambiguity-preserving.

Durable memory is structured semantic/world/history state—not a transcript archive and not a dump of every intermediate computation.

---

# Current implementation sequence

The unified roadmap in [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md) integrates stabilization and semantic-brain migration into five sequential milestones:

```text
M0 STABILIZED RUNTIME SUBSTRATE   (Phases 0–4)
M1 EXACT CSIR SEMANTIC SPINE       (Phases 5–8)
M2 ENGLISH CONVERSATIONAL KERNEL   (Phases 9–12)
M3 WORKING LEARNING + RECURRENT SEMANTIC BRAIN  (Phases 13–14)
M4 FULL STATE/CAUSAL/MULTIMODAL CUTOVER         (Phases 15–18)
```

The key correction is to build a usable vertical slice early (M2) rather than implementing every advanced subsystem before proving basic cognition.

The current v3.5 runtime solved important problems:

* one Stage-0..22 runtime path;
* explicit provenance;
* exact revisioned records;
* claims separated from world truth;
* events separated from state mutation;
* controlled side effects;
* response meaning before wording;
* release/cutover verification.

But several safeguards have become too deeply coupled to ordinary cognition. The defects are catalogued in [`CORE_ISSUES.md`](CORE_ISSUES.md) and addressed by the unified plan.

The correction is **not** to remove rigor. The correction is to place each invariant at the narrowest correct boundary.

---

## Five control planes

The architecture must distinguish at least five independent control planes.

### Release attestation

Answers:

> Is this process an approved runtime generation?

Validated at startup or explicit reload.

It must not require rehashing the release on every request.

### Semantic authority

Answers:

> What exactly does this semantic structure mean under this exact definition closure?

Pinned by immutable, content-addressed authority generation.

### Epistemic and world-state validity

Answers:

> What is currently supported, opposed, unknown, estimated or contradicted?

Mutable and context/time sensitive.

### Access and privacy permission

Answers:

> May this principal read, retain or disclose this information?

Evaluated at access and disclosure boundaries.

### Effect authorization

Answers:

> May this proposed mutation, external operation, privileged disclosure or emission happen now?

This is where fail-closed authorization belongs.

The system must not spend more computation proving it is allowed to think than actually performing semantic cognition.

---

# Canonical documentation

## Read these first — in order of importance

### 1. [`AGENTS.md`](AGENTS.md)

Highest-priority implementation governance.

Defines:

* canonical authority order;
* prohibited shortcuts;
* versioning rules;
* exact semantic closure requirements;
* implementation status vocabulary;
* architectural invariants AI agents must obey.

If another implementation note conflicts with `AGENTS.md`, follow `AGENTS.md` and the canonical architecture documents it names.

### 2. [`CORE_ISSUES.md`](CORE_ISSUES.md)

Mandatory pre-v3.5.1 defect register.

Read this before modifying the current runtime.

It identifies the deeper v3.5 problems that must not be inherited, including:

* authority overreach;
* hot-path release verification;
* identity/idempotency failures;
* snapshot conflation;
* persistence asymptotics;
* concurrency bottlenecks;
* learning hot-path coupling;
* semantic over-gating;
* realization/emission costs;
* partial-cognition failure modes.

### 3. [`ISSUES_TO_AVOID.md`](ISSUES_TO_AVOID.md)

Mandatory anti-regression contract.

This is the implementation "do not recreate these mistakes" document.

Every code review and AI implementation pass should use it as a negative architectural checklist.

### 4. [`ARCHITECTURE.md`](ARCHITECTURE.md)

The target CEMM computational architecture.

Defines:

* grounded semantic-brain architecture;
* exact semantic plane;
* recurrent semantic-dynamics plane;
* CSIR;
* multimodal state;
* causal mechanisms;
* state/action/event/claim separation;
* semantic authority;
* learning;
* response generation;
* versioning;
* effect boundaries.

### 5. [`CEMM_CORE_MATHS.md`](CEMM_CORE_MATHS.md)

The mathematical contract behind the architecture.

Defines the formal machinery for:

* exact authority snapshots;
* canonical semantic graphs;
* recurrent activation/message passing;
* constrained semantic solving;
* uncertainty and calibrated interpretation;
* grounded state estimation;
* temporal/state transitions;
* causal propagation;
* prediction and counterfactual reasoning;
* impact and goal arbitration;
* learning and expected information gain;
* semantic equivalence;
* invalidation and computational budgets.

### 6. [`CORE_LOOP.md`](CORE_LOOP.md)

The canonical Stage-0..22 cognitive loop.

Defines how the architecture executes over time, including:

* orientation and pinning;
* observation;
* grounding;
* semantic compilation;
* recurrent meaning solve;
* epistemic placement;
* retrieval/query binding;
* learning frontiers;
* causal transition inference;
* impact and goals;
* operation planning;
* response semantics;
* realization;
* verification;
* emission;
* common-ground update;
* invalidation and finalization.

Stages are **logical computational boundaries**, not mandatory database transaction boundaries.

### 7. [`RUNTIME_PLAN.md`](RUNTIME_PLAN.md)

The canonical concrete runtime implementation contract.

Bridges `ARCHITECTURE.md` + `CORE_LOOP.md` to actual runtime code. Defines:

* process-lifetime, session-lifetime, and cycle-lifetime objects;
* authority and mutable-state generation model;
* stage capability tokens;
* `CycleWorkspace`;
* stage persistence/effect matrix;
* concrete stage artifact contracts;
* pre-cycle/post-cycle maintenance;
* participant/session lifecycle;
* epistemic admission policy;
* learning runtime;
* re-entry protocol;
* realization verification;
* storage architecture;
* v3.5 → v3.5.1 migration runtime rule.

### 8. [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)

The **sole active implementation roadmap** for v3.5.1.

Integrates stabilization and semantic-brain migration into one unified plan with five milestones:

* M0 — Stabilized runtime substrate (Phases 0–4);
* M1 — Exact CSIR semantic spine (Phases 5–8);
* M2 — English conversational kernel (Phases 9–12);
* M3 — Working learning + recurrent semantic brain (Phases 13–14);
* M4 — Full state/causal/multimodal cutover (Phases 15–18).

Supersedes `PRE_3_5_1_STABILIZATION_PLAN.md` and `V3_5_1_IMPLEMENTATION_PLAN.md` (both archived under `docs/archive/`).

### 9. [`ACCEPTANCE_CONTRACT.md`](ACCEPTANCE_CONTRACT.md)

Defines what must be proven before a capability or release is called complete.

Acceptance must include:

```text
architectural conformance
semantic productivity
synthetic unseen combinations
restart / rehydration
no-shortcut verification
multilingual competence
causal/state correctness
learning competence
performance budgets
concurrency
release verification
```

### 10. [`ISSUES_TO_AVOID.md`](ISSUES_TO_AVOID.md)

Mandatory anti-regression contract.

This is the implementation "do not recreate these mistakes" document.

Every code review and AI implementation pass should use it as a negative architectural checklist.

### 11. [`docs/architecture/TERMINOLOGY.md`](docs/architecture/TERMINOLOGY.md)

Canonical terminology.

Use it to prevent vocabulary drift between code, schemas, docs and tests.

---

## Foundational supporting architecture

Read these after the documents above when implementing the relevant subsystem.

1. [`docs/architecture/FOUNDATIONAL_KNOWLEDGE_ARCHITECTURE.md`](docs/architecture/FOUNDATIONAL_KNOWLEDGE_ARCHITECTURE.md)
2. [`docs/architecture/FOUNDATIONAL_SEMANTIC_ALGEBRA.md`](docs/architecture/FOUNDATIONAL_SEMANTIC_ALGEBRA.md)
3. [`docs/architecture/LEARNING_ARCHITECTURE.md`](docs/architecture/LEARNING_ARCHITECTURE.md)
4. [`docs/architecture/CLAIMS_EVENTS_STATE_AND_IMPACT.md`](docs/architecture/CLAIMS_EVENTS_STATE_AND_IMPACT.md)
5. [`docs/architecture/UOL.md`](docs/architecture/UOL.md)
6. [`docs/architecture/DATA_ARCHITECTURE.md`](docs/architecture/DATA_ARCHITECTURE.md)

These documents remain useful foundational references, but where older terminology or v3.5 assumptions conflict with the newer canonical architecture, follow:

```text
AGENTS.md
→ CORE_ISSUES.md / ISSUES_TO_AVOID.md
→ ARCHITECTURE.md
→ CEMM_CORE_MATHS.md
→ CORE_LOOP.md
→ RUNTIME_PLAN.md
→ IMPLEMENTATION_PLAN.md
→ ACCEPTANCE_CONTRACT.md
```

---

## Historical and audit documents

These are useful for reasoning about migration history and architectural changes but are not higher authority than the canonical documents above.

* [`ARCHITECTURE_AUDIT.md`](ARCHITECTURE_AUDIT.md)
* [`phased-fixes.md`](phased-fixes.md)
* [`PRE_3_5_1_STABILIZATION_PLAN.md`](PRE_3_5_1_STABILIZATION_PLAN.md) — **SUPERSEDED**, archived at `docs/archive/`
* [`V3_5_1_IMPLEMENTATION_PLAN.md`](V3_5_1_IMPLEMENTATION_PLAN.md) — **SUPERSEDED**, archived at `docs/archive/`
* historical documents under `docs/archive/`

Old runtime code, archived plans, deprecated bootstrap scripts and historical acceptance assumptions are not current semantic authority.

Do not resurrect old paths merely because they already exist.

---

# Status vocabulary

Use these terms precisely.

* **specified** — required by canonical contracts;
* **implemented** — code/data exists;
* **persisted** — required durable representation exists;
* **wired** — canonical runtime invokes it;
* **authoritative** — no competing path makes the same semantic decision;
* **verified** — correctness/architecture/productivity tests prove it;
* **cut over** — public runtime and release authority use the new path exclusively.

A runtime may be cut over while individual semantic capabilities remain unverified.

Do not use "implemented" as a synonym for "correct."

Do not use "tests pass" as a synonym for "architecturally complete."

---

# Development

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

pytest -q
python -m cemm --chat
```

Before calling any stabilization or semantic phase complete, run the relevant:

```text
unit tests
synthetic productivity tests
restart / rehydration tests
identity / idempotency tests
no-shortcut tests
multilingual tests
causal/state tests
learning tests
performance tests
concurrency tests
release-verifier gates
```

For Phase 0 baseline and stabilization gates (M0), additionally measure:

```text
files hashed per normal cycle
boot hashes per normal cycle
SQLite queries per stage
rows scanned
records decoded
snapshot count
write transaction count
lock wait
cache hit ratio
p50 / p95 / p99 latency
concurrent throughput
write cost vs overlay size
```

A semantic system that becomes slower as audit history grows, serializes normal requests, or spends most of its cycle revalidating immutable release facts is not architecturally complete.

---

# What not to add

Do not fix regressions by adding:

* exact transcript phrases;
* full-sentence constructions for ordinary composition;
* English word checks in kernel code;
* language-specific semantic regex routing;
* predicate catalogues as cognition;
* one response policy per predicate;
* canned capability/state answers;
* subject=actor or object=affected universal rules;
* event-specific state mutation branches;
* hardcoded concept-specific causal effects;
* defaults promoted to facts;
* observation frequency treated as truth;
* new Python enums for learned concepts;
* floating executable semantic dependencies;
* `max(revision)` as semantic authority;
* `RecordKind` as ontology;
* raw Python object equality as persistence identity;
* full release revalidation on every request;
* full-store hashing on every small write;
* global locks held across semantic computation;
* learning-promotion scans on every user request;
* durable persistence for every transient cognitive intermediate;
* verifier exclusions;
* dummy adapters;
* fake authority records;
* tests that prove only a fixed catalogue count.

The architecture must make **unseen combinations work because the underlying semantic structure and computational laws generalize**.

---

# Non-negotiable invariants

CEMM must preserve:

```text
claims ≠ truth
event occurrence ≠ state mutation
prediction ≠ observation
counterfactual world ≠ actual world
language form ≠ semantic identity
confidence ≠ authority
semantic eligibility ≠ effect authorization
storage record kind ≠ ontology
activation score ≠ calibrated probability
response wording ≠ response meaning
```

And:

```text
no hidden legacy semantic authority
no phrase-specific semantic brain
no verifier bypass
no silent reinterpretation of historical records
no unpinned executable semantic closure
no external effect without authorization
no protected disclosure without permission
no claim of success when a critical frontier blocks the requested outcome
```

---

# Repository direction

The next successful CEMM release is not achieved by adding more gates or more catalogue coverage.

It requires a substrate that is simultaneously:

```text
exact
grounded
compositional
causal
multimodal
learning-first
recurrent
version-safe
permission-aware
effect-safe
efficient
concurrent
replayable
```

The goal of M0 (Phases 0–4) is to make the runtime lean enough to support cognition without weakening its guarantees.

The goal of v3.5.1 (Phases 5–18) is to build the grounded semantic brain on that stabilized foundation.
