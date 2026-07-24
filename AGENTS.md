# CEMM v1 — Governing Agent Instructions

**Status:** highest-priority local implementation contract
**Version target:** CEMM v1
**Purpose:** keep every human or AI implementation pass aligned to one
architecture, one semantic substrate, and honest public claims.

For architectural detail, operator catalogues, runtime contracts, and
acceptance gates, see `ARCHITECTURE.md`. This document governs principles and
prohibitions only.

---

## 1. Core thesis

CEMM is a modular semantic cognition kernel. Its engineering thesis:

```text
meaning ≠ language
```

Language is a symbolic/compositional interface for expressing, communicating,
and manipulating meaning. It is **not** the ontology and must not become the
kernel's primary semantic authority.

**One-brain rule.** There is one canonical semantic brain. Deterministic
solvers, recurrent dynamics, neural models, language adapters, and migration
compilers may perform distinct computational roles, but they must converge on
one canonical semantic authority. There must never be competing brains
(legacy + neural + multimodal) as parallel authorities.

**Two inseparable computational planes:**

- **Exact semantic plane** — defines what meaning *is*: content-addressed
  semantic graphs, exact definitions, typed roles/bindings, state dimensions,
  causal structure, evidence lineage, immutable authority generations.
  Semantic identity is deterministic, versioned, replayable, content-addressed.
- **Dynamic semantic plane** — defines how meaning becomes active, competes,
  settles, predicts, and learns: sparse activation, recurrent message passing,
  bottom-up evidence, top-down expectation, uncertainty, learned parameters.
  Continuous representations may assist cognition; they never define semantic
  identity by themselves.

---

## 2. Meaning laws

1. **Exact semantics are authority.** Exact semantic truth lives in the
   meaning database / semantic graph. Neural models propose and rank; they do
   not decide semantic truth.
2. **Neural computation proposes, ranks, composes, realizes.** The neural
   plane generates candidates, scores them, composes structures, and realizes
   language. It never becomes the semantic authority.
3. **Neural latent state never becomes a second semantic ontology.**
   Embeddings, activations, and learned labels are not semantic identity.
4. **New domain ≠ new Python class, ≠ new SQL schema, ≠ new semantic program
   class.** New domains are expressed as atoms, designations, operator
   applications, state dimensions, graph rules, and learned parameters — not
   as new code branches or schemas.
5. **Derived closure is not materialized by default.** Inferred facts are
   computed on demand. Persisting closure merely because it was queried is
   forbidden.
6. **Five universal operator shapes remain fixed.** The kernel operator ABI
   is frozen. New competence extends what operators are applied to, not how
   many operator shapes exist.

Additional standing laws (condensed):

- Grammar is evidence about meaning, not ontology.
- `subject` is not universally `agent`; `object` is not universally `affected`.
- Referent identity is distinct from state continuity.
- Defaults are expectations, not active facts.
- Claims are not automatically world truth.
- Prediction is not observation; simulation is not commit.
- Correlation and co-occurrence are not causal authority.
- Response meaning exists before wording; realization may choose wording but
  may not invent semantic content.
- Partial understanding is valid cognition and must remain explicit.
- Unknown material must not erase already-grounded meaning.

---

## 3. Authority separation principle

Keep **authority** and **world** distinct.

- **Authority** is the immutable semantic substrate: kernel operators, roles,
  definitions, promoted rules, language/model artifacts, operational profiles,
  causal mechanisms, authorizations. Authority changes only through explicit
  generation-based promotion.
- **World** is the mutable grounded layer: referents, claims, state timelines,
  events, evidence, discourse, observations. World revision never silently
  mutates authority.

Authority is **generation-based**: each promotion creates a new immutable
generation. A cycle pins one authority generation and never sees mid-cycle
promotion. Newly promoted authority becomes visible only through **explicit
reload** — it must not silently appear to pinned cycles.

World occurrences must never contaminate authority hashes. Authority
attestation is pinned to the authority cutoff so later world learning cannot
alter it.

---

## 4. Anti-bloat / forbidden shortcuts

Before adding any new schema, code branch, or runtime path, ask:

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

Only if the answer is demonstrably no should the kernel ABI be reconsidered.

A patch is invalid if it introduces or preserves as public authority any of:

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

Additional standing prohibitions:

- Exact transcript/phrase matching as cognition.
- Named concept/action/type branches in kernel cognition.
- Confidence used as authority; embeddings used as semantic identity.
- Defaults promoted directly to facts.
- Observation frequency treated as truth.
- Learning candidates self-promoting from frequency alone.
- Response text constructed before response semantics.
- Irreversible/external effects without the narrow authorization boundary.
- Hidden legacy fallback; duplicate semantic brains.
- Durable persistence for every transient cognitive intermediate.

The system must generalize because semantic structure and computational laws
generalize.

---

## 5. Public claims discipline

Do not publicly claim a capability merely because its code, schema, or data
exists. Until the applicable acceptance gates pass, do not describe CEMM as:

- a completed general intelligence system;
- a verified replacement for LLMs;
- a literal or validated biological brain simulation;
- a production-grade multimodal cognition engine;
- broadly multilingual merely because multiple language packs are present;
- a fully proven autonomous self-learning system.

Preferred language while under verification:

```text
"architecture/code exists"
"implemented foundation"
"under active verification"
"target capability"
```

Use stronger status language only when canonical acceptance evidence supports
it.

The architectural thesis may be stated strongly:

> language is a symbolic/compositional interface for representing and
> communicating meaning grounded in entities, states, relations, events,
> transitions, causality, and possible operations.

Do not turn that thesis into unsupported claims about neuroscience, biological
brain equivalence, or proven evolutionary mechanisms.

---

## 6. Reference

For architecture detail, operator catalogues, runtime contracts, persistence
boundaries, learning loops, and acceptance gates, see `ARCHITECTURE.md`.

If a lower-authority document, test, bootstrap script, generated artifact, or
implementation path conflicts with the principles above, fix or quarantine the
lower authority. Do not invent a second runtime or semantic authority to
preserve compatibility.
