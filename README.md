# CEMM — Contextual Event Memory Model

CEMM is a learning-first grounded semantic kernel.

> **Current repository status:** the public runtime has cut over to the signed CEMM v3.5 Stage-0..22 authority. Runtime cutover is complete; **productive semantic activation is not yet complete**. The active remediation work replaces exact-form/predicate-catalogue behavior with semantic contributions, lexeme/form-family authority, typed information gaps, referent-driven closure, universal query binding, generic Response UOL, and full learning-runtime promotion.

Do not describe v3.5 as fully verified until the semantic productivity release gates pass.

---

## What CEMM is trying to achieve

CEMM should be able to start with a small reviewed semantic/language substrate and grow reusable understanding.

A known word does not need to map directly to a complete intent.

Instead:

```text
observation
→ form/morpheme evidence
→ lexeme/form-family evidence
→ semantic contributions
→ construction constraints
→ referent grounding
→ type/facet/state/capability projection
→ bounded UOL meaning solve
→ claims/queries/events/learning
→ semantic response goals
→ Response UOL
→ multilingual realization
→ semantic verification
```

The target is **compositional meaning**, not phrase coverage.

CEMM is not a chatbot architecture and not an intent classifier with memory. Its standing ordering laws are:

```text
perceive before answering
working graph before memory write
compression before storage
source before belief
time before current claims
permission before learning
safety before realization/emission
commit before claiming a write
meaning before wording
```

The working graph is temporary and ambiguity-preserving; durable memory is compressed semantic authority and history, not a transcript archive.

---

## Core design principles

### Small semantic kernel

Only stable structural machinery belongs in code.

New domain concepts remain data.

### Semantic contributions

A recognized form may contribute:

```text
target candidate
referential requirement
open variable
restriction
answer projection
scope
argument relation
grammatical feature
construction trigger
```

Meaning closes jointly rather than one word becoming one intent.

### Referent-centered cognition

Every grounded referent has a type-derived knowledge envelope containing applicable properties, states, roles, relations, affordances, capabilities, functions and epistemic constraints.

### Claims are not facts

User utterances create attributed discourse/claim evidence first.

Actual-world admission is separate.

### State, process, event and action are distinct

CEMM must distinguish conditions that hold, processes that unfold, events/transitions that occur, and actions with control/intentionality.

### Language is not ontology

Adjective/adverb/pronoun/auxiliary are grammatical categories.

They constrain semantic interpretation but do not define world semantics.

### Learning is reusable

CEMM learns lexemes, semantic contributions, constructions, schemas, transitions, realization competence and other reusable structure—not transcript phrases.

---

## Current remediation boundary

The signed v3.5 runtime currently exposes important semantic gaps that are being fixed in ordered phases.

The first two remediation phases establish:

1. corrected root architecture/governance;
2. Semantic Contribution and Meaning Closure contracts;
3. typed semantic variables;
4. durable lexeme/form-family records;
5. durable semantic-contribution specifications;
6. a migration-safe preference for new language authority with explicit legacy form→sense fallback;
7. productivity tests using synthetic vocabulary rather than demo phrases;
8. removal/replacement of tests that freeze catalogue sizes or require interpretation to be disabled.

Later phases close:

- predication/eventuality/construction algebra;
- ParticipantFrame grounding;
- Stage-4 referent-driven semantic closure;
- typed interrogatives;
- universal Stage-10 query binding;
- runtime-backed self state/capabilities;
- generic response cognition;
- full learning-runtime cutover;
- multilingual seed rebuild.

See [`phased-fixes.md`](phased-fixes.md).

---

## Canonical documentation

Read in this order:

1. [`AGENTS.md`](AGENTS.md)
2. [`ARCHITECTURE.md`](ARCHITECTURE.md)
3. [`docs/architecture/TERMINOLOGY.md`](docs/architecture/TERMINOLOGY.md)
4. [`docs/architecture/FOUNDATIONAL_KNOWLEDGE_ARCHITECTURE.md`](docs/architecture/FOUNDATIONAL_KNOWLEDGE_ARCHITECTURE.md)
5. [`docs/architecture/FOUNDATIONAL_SEMANTIC_ALGEBRA.md`](docs/architecture/FOUNDATIONAL_SEMANTIC_ALGEBRA.md)
6. [`docs/architecture/LEARNING_ARCHITECTURE.md`](docs/architecture/LEARNING_ARCHITECTURE.md)
7. [`docs/architecture/CLAIMS_EVENTS_STATE_AND_IMPACT.md`](docs/architecture/CLAIMS_EVENTS_STATE_AND_IMPACT.md)
8. [`docs/architecture/UOL.md`](docs/architecture/UOL.md)
9. [`CORE_LOOP.md`](CORE_LOOP.md)
10. [`docs/architecture/DATA_ARCHITECTURE.md`](docs/architecture/DATA_ARCHITECTURE.md)
11. [`IMPLEMENTATION_PLAN.md`](IMPLEMENTATION_PLAN.md)
12. [`phased-fixes.md`](phased-fixes.md)
13. [`ACCEPTANCE_CONTRACT.md`](ACCEPTANCE_CONTRACT.md)

Historical documents under `docs/archive/` and old runtime code are not current semantic authority.

---

## Status vocabulary

- **specified** — required by canonical contracts;
- **implemented** — code/data exists;
- **wired** — canonical runtime invokes it;
- **authoritative** — no competing path makes the same semantic decision;
- **verified** — architecture/productivity/end-to-end tests prove it.

Runtime cutover may be authoritative while a particular semantic capability remains unverified.

---

## Development

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"

pytest -q
python -m cemm --chat
```

Before calling a semantic phase complete, run its synthetic productivity, restart/rehydration, no-shortcut and release-verifier gates.

---

## What not to add

Do not fix regressions by adding:

- exact transcript phrases;
- full-sentence constructions for ordinary composition;
- English word checks in kernel code;
- semantic regex routing;
- one response policy per predicate;
- canned capability/state answers;
- event-specific state mutation;
- defaults promoted to facts;
- new Python enums for learned concepts;
- tests that prove only a fixed catalogue count.

The architecture should make unseen combinations work because the underlying meaning is compositional.
