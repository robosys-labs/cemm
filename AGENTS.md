# CEMM v3.5.1 Governing Agent Instructions

**Status:** highest-priority local implementation contract  
**Version target:** CEMM v3.5.1  
**Purpose:** keep every human or AI implementation pass aligned to one architecture, one runtime, one semantic substrate, and one implementation roadmap.

---

## 1. Canonical authority order

Use the following documents in this order:

1. `AGENTS.md` — implementation governance and prohibitions.
2. `ARCHITECTURE.md` — stable target architecture and invariants.
3. `CORE_LOOP.md` — logical Stage 0–22 cognitive contract.
4. `RUNTIME_PLAN.md` — concrete runtime ownership, stage artifacts, persistence/effect boundaries, bootstrap, maintenance, re-entry, and migration behavior.
5. `CEMM_CORE_MATHS.md` — mathematical contract for exact semantics, dynamics, uncertainty, state, causality, learning, and equivalence.
6. `IMPLEMENTATION_PLAN.md` — the **only active implementation roadmap**.
7. `CORE_ISSUES.md` — defect register and remediation trace.
8. `ISSUES_TO_AVOID.md` — mandatory negative/anti-regression contract.
9. `ACCEPTANCE_CONTRACT.md` — executable release and competence gates.
10. implementation code and reviewed data.

If a lower document conflicts with a higher document, fix or quarantine the lower document. Do not invent a second path.

`PRE_3_5_1_STABILIZATION_PLAN.md` and `V3_5_1_IMPLEMENTATION_PLAN.md` are superseded by `IMPLEMENTATION_PLAN.md` after this documentation set is adopted.

---

## 2. One-brain rule

CEMM has one canonical semantic brain:

```text
observations
→ language/multimodal evidence
→ grounded referents and state spaces
→ exact CSIR candidates
→ recurrent semantic dynamics
→ stable/partial semantic attractors
→ discourse/epistemic/world structures
→ query, prediction, causal simulation and learning
→ goals and Response CSIR
→ realization
→ semantic-preservation/effect authorization
→ emission/common-ground update
```

There must never be:

```text
legacy UOL brain
+ CSIR brain
+ neural brain
```

Legacy UOL/schema material may be migration input or a temporary shadow oracle. It may not be a public fallback after CSIR cutover.

---

## 3. Two inseparable computational planes

### 3.1 Exact semantic plane

Defines what meaning **is**:

- content-addressed CSIR;
- exact semantic definitions and closure;
- typed ports, roles, variables, scope, context and time;
- state dimensions and domains;
- causal mechanism structure;
- operational profiles;
- evidence/proof lineage;
- exact authority generations.

### 3.2 Dynamic semantic plane

Defines how meaning becomes active, competes, settles, predicts and learns:

- sparse activation;
- typed relation-specific message passing;
- bottom-up evidence;
- top-down semantic prediction;
- inhibition;
- uncertainty;
- recurrent convergence;
- learned parameter artifacts;
- prediction error.

Continuous representations and activations never define semantic identity.

---

## 4. Meaning laws

1. A recognized form contributes only the smallest semantic constraints licensed by evidence.
2. Grammar is evidence about meaning, not ontology.
3. `subject` is not universally `agent`; `object` is not universally `affected`.
4. Referent identity is distinct from state continuity.
5. Defaults are expectations, not active facts.
6. Claims are not automatically world truth.
7. Event occurrence is not automatically state mutation.
8. Simulation is not commit.
9. Correlation and temporal adjacency are not causal authority.
10. Response meaning exists before wording.
11. Realization may choose wording but may not invent semantic content.
12. Partial understanding is valid cognition and must remain explicit.

---

## 5. Authority and control-plane separation

Keep these predicates distinct:

```text
release-attested
semantically-defined
activated/eligible
epistemically-supported
permitted-to-read
permitted-to-retain
permitted-to-disclose
permitted-to-mutate
permitted-to-execute
competent
realisable
emittable
```

Do not replace them with one `authorized` or `trusted` boolean.

Normal semantic cognition must not repeatedly perform release verification or execute-level authorization.

Fail-closed effect authorization belongs at the narrowest boundary where an irreversible or protected effect can occur.

---

## 6. Runtime and persistence laws

- Stage 0–22 are logical cognitive boundaries, not 23 database transactions.
- Use a cycle-local `CycleWorkspace` for transient cognition.
- A cycle pins one immutable semantic authority generation.
- Mutable world/discourse generations are tracked separately.
- No semantic authority mutation mid-pass.
- No global lock across semantic solving.
- No O(total history) operation for an O(1) write.
- No per-request full learning promotion scan.
- No request-frequency runtime telemetry persistence.
- No `for kind in RecordKind` hot-path resolution.
- Every cache declares generation ownership and invalidation domains.

---

## 7. Learning laws

Separate:

1. episodic/participant knowledge;
2. lexicalization and language learning;
3. semantic-definition learning;
4. state-schema learning;
5. causal/transition structure learning;
6. continuous parameter learning;
7. operational-profile learning;
8. use authorization/promotion.

A learning loop is complete only when it supports:

```text
frontier
→ evidence
→ candidate
→ exact dependencies
→ competence/counterexamples
→ scoped promotion decision
→ immutable new authority generation
→ next-cycle use
→ restart rehydration
→ replay/invalidation
```

Learning candidates do not self-promote merely because they were observed frequently.

---

## 8. Completion vocabulary

A component is complete only when applicable statuses are all true:

```text
specified
implemented
wired
authoritative
verified
calibrated
replayable
```

Do not call a phase complete because files, schemas, or tests merely exist.

---

## 9. Mandatory implementation workflow

For every phase:

1. read the relevant canonical contracts;
2. identify old authority and new authority;
3. state exact invariants preserved;
4. implement the smallest coherent vertical slice;
5. add positive, negative, partial and restart tests;
6. run anti-regression lints;
7. run architecture/competence tests;
8. run performance/concurrency tests where relevant;
9. update `CORE_ISSUES.md`;
10. only then update status to verified.

Never weaken tests, hide blockers, add dummy adapters, or patch signed hashes manually.

---

## 10. Forbidden shortcuts

A patch is invalid if it introduces or preserves as public authority:

- transcript/phrase matching as cognition;
- English word checks in the semantic kernel;
- named concept/action/type branches;
- predicate-specific response sentences;
- event-specific state mutators;
- subject/object-based universal effects;
- universal state fields without entitlement;
- confidence used as authority;
- embeddings used as semantic identity;
- unpinned executable semantic dependencies;
- mutable in-place promoted neural parameters;
- claims/defaults/simulations committed as actual state without policy;
- response text before Response CSIR;
- hidden legacy fallback;
- fake authority records;
- verifier exclusions to force activation.

---

## 11. Required test dimensions

Where applicable, every semantic change includes:

```text
positive case
negative case
partial/ambiguous case
correction/retraction case
synthetic vocabulary rename
paraphrase
active/passive contrast
cross-type contrast
context/hypothetical/counterfactual isolation
restart/rehydration
authority-generation change
prediction-error frontier
no-shortcut lint
performance budget
```

---

## 12. Release law

Correct order:

```text
implementation
→ behavior tests
→ semantic competence tests
→ learning/restart tests
→ performance/concurrency tests
→ migration/shadow evidence
→ boot/release artifacts
→ exact authority roots
→ deterministic verification report
→ signed release manifest
→ cutover
```

Never sign first and then make behavior fit the artifact.
