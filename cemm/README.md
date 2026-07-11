# CEMM

**A meaning-first runtime that learns language and operational knowledge online.**

CEMM is a pure-Python research and engineering architecture for multilingual, multimodal agents. It represents language as evidence for executable semantic structure rather than as a direct route to canned responses.

The 3.3 target combines:

- a UOL working graph over fixed semantic atom kinds;
- dynamic entity, relation, operator, state, time, place, source, permission, and modality grounding;
- typed operational ports and state transmutations;
- contract-driven query, write, safety, reaction, action, and response execution;
- recursive acquisition of unknown words, grammar, constructions, schemas, and meanings;
- graph-patch-only durable learning with provenance, confidence, contradiction, scope, and revision.

> **Status:** active 3.3 upgrade. The repository contains working 3.1/3.2 components and transitional paths. `AGENTS.md` and `ARCHITECTURE.md` define the target contract; implementation status must be verified by tests and code, not by old phase labels.

---

## Why CEMM

Most language systems treat unknown language as an error, guess, or embedding-neighbor problem. CEMM treats it as a structured learning opportunity.

```text
unknown form
-> typed semantic gap
-> minimum-information question
-> user/source/multimodal evidence
-> provisional operational grounding
-> immediate scoped reuse
-> reinforcement, correction, sense splitting, or promotion
```

CEMM learns mappings into fundamental substrates:

```text
entities and entity kinds
relations and predicates
actions/operators and typed ports
state families, dimensions, values, and transitions
time and geospatial relations
modality, polarity, source, evidence, and permission
grammar operators and constructions
causal effects and affordances
realization forms
```

It does not need to memorize whole sentences to understand a newly taught word.

---

## Core architecture

```text
EXECUTION SPINE

surface or multimodal signal
-> normalized evidence
-> meaning groups and interpretation branches
-> grounded UOL propositions
-> scoped predicate/operator activation
-> state occupancy, deltas, and authorized transmutations
-> operational meanings and causal effects
-> obligation graph
-> execution contracts and ledger
-> response/action/state results

ACQUISITION SPINE

unknown or uncertain evidence
-> SemanticGap
-> LearningEpisode
-> recursive clarification
-> provisional binding/schema
-> branch resumption and immediate reuse
-> learning evidence and revision

CONSOLIDATION LOOP

evidence ledger + use outcomes + independent support
-> strength projection
-> scope promotion or restriction
-> graph-patch validation
-> durable consolidation, split, supersession, quarantine, or retirement
```

Surface matches propose candidates. They never directly authorize actions, state changes, memory writes, safety decisions, or responses.

---

## Fixed primitives and learned meaning

The kernel uses a small fixed representation vocabulary:

```text
entity, process, state, relation, quality, quantity, time, place,
intent, need, modality, evidence, source, permission, action, self
```

Domain meanings are dynamic:

```text
person, animal, vehicle, president, database, cold, run, near,
instrument, ownership, future, completed, polite, dangerous
```

They may be seeded, learned, revised, scoped, contested, consolidated, or retired.

---

## Learning model

Each learned artifact has:

```text
surface/language context
semantic target or schema
source and evidence references
scope: session, user, domain/dialect, language, or global
support and contradiction events
successful-use and repair-failure outcomes
freshness and stability
promotion ceiling and safety class
```

The evidence ledger is append-only. Confidence and stability are derived views, so later corrections remain explainable.

A newly taught form may be used immediately through a reversible session overlay. Durable or global promotion requires stronger, diverse evidence.

---

## Repository layout

```text
AGENTS.md                 # highest-priority implementation instructions
ARCHITECTURE.md           # canonical 3.3 architecture contract
README.md                 # project introduction and usage

cemm/
├── types/                # UOL, authority, state, contract, learning, response types
├── kernel/               # perception, graph, grounding, activation, state, contracts, runtime
├── data/
│   ├── semantic_schemas/ # authored entity/state/slot/operator/affordance schemas
│   └── languages/        # language-specific lexical and grammatical resources
├── memory/               # provisional overlays, durable semantic and evidence stores
├── learning/             # gaps, episodes, evidence, revision, patches, consolidation
├── query/                # contract-indexed budget-aware retrieval
├── causal/               # effect and causal prediction
├── response/             # language-neutral planning and language-specific realization
├── actions/              # internal/external action proposals and authorization
├── budget/               # per-stage computational budget
├── conformance/          # architecture and drift checks
├── newarch/              # 3.3 design, implementation, and fixes plans
└── tests/                # structural, regression, multilingual, learning, safety, performance
```

Some target directories or modules may be introduced incrementally during the 3.3 migration.

---

## Quick start

```bash
# From the repository root
python -m pytest -q

# Interactive session
python -m cemm

# Single input
python -m cemm --eval "What can you do?"

# Persistent store
python -m cemm --db ./cemm.sqlite
```

Use the repository's supported Python version and environment definition where present.

---

## Development contract

Read these before changing runtime behavior:

1. `AGENTS.md`
2. `ARCHITECTURE.md`
3. `cemm/newarch/3.3-upgrade-core-architecture-design.md`
4. `cemm/newarch/3.3-upgrade-core-architecture-implementation-plan.md`
5. `cemm/newarch/3.3-upgrade-fixes-plan.md`

The core rule is:

```text
repair the earliest wrong semantic substrate;
do not patch the visible response.
```

Examples:

```text
bad action activation -> fix predicate scope and ports
bad memory behavior -> fix frame provenance and write contract
bad state behavior -> fix occupancy/transmutation authority
bad answer -> fix query target/evidence contract
bad learning -> fix gap, episode, evidence, scope, or promotion
bad wording -> fix realization only after upstream traces are correct
```

---

## Testing

CEMM tests should assert internal semantic traces, not only final strings.

Important suites cover:

```text
multilingual normalization and grammar
meaning groups and interpretation branches
entity and reference grounding
predicate activation under negation, quotation, modality, and hypotheticals
typed ports and placeholders
state occupancy/transmutation/application
recursive vocabulary and schema learning
immediate provisional reuse
polysemy, contradiction, scope, and evidence independence
obligation composition and contract execution
frame-scoped graph patches
query freshness and target grounding
safety and permission
response-plan gates and structured output acts
hot-path performance and broad-scan prevention
```

Exact test counts are intentionally omitted because they change frequently.

---

## Architecture status discipline

Do not describe a phase as complete because files or dataclasses exist.

A capability is implemented only when:

```text
the canonical runtime uses it
legacy competing authority is disabled or deleted
structural acceptance tests pass
failure and fallback paths preserve the same invariants
performance and safety gates pass
documentation matches the tested code
```

See `ARCHITECTURE.md` for the complete contract.
