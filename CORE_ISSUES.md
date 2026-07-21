# CEMM v3.5 / v3.5.1 Core Issues Register

**Status:** mandatory active defect register  
**Purpose:** prevent known substrate/runtime defects from being hidden by new semantic-brain work.

Update each issue with:

```text
status
owner/phase
reproducer
fix
regression test
performance impact
migration impact
```

Statuses:

```text
OPEN
IN_PROGRESS
FIXED_UNVERIFIED
VERIFIED
QUARANTINED_MIGRATION_ONLY
```

---

## CI-001 — Runtime plan/documentation conflict

**Severity:** critical  
**Status:** OPEN

### Problem
The repository contains multiple plans/contracts with different ordering and authority assumptions.

### Required fix
Adopt:
- `IMPLEMENTATION_PLAN.md` as the sole roadmap;
- `RUNTIME_PLAN.md` as concrete runtime contract;
- archive/supersede old stabilization and v3.5.1 plans.

### Exit test
Documentation-lint verifies no active root document points implementers to superseded plans as authoritative.

---

## CI-002 — Proposed v3.5.1 Core Loop does not match current runtime Stage ABI

**Severity:** critical  
**Status:** OPEN

### Problem
Current runtime still uses UOL-oriented stages such as:

```text
BUILD_UOL_FACTOR_GRAPH
SOLVE_MEANING_HYPOTHESES
SELECT_MEANING_BUNDLE
BUILD_RESPONSE_UOL
```

while v3.5.1 requires:

```text
COMPILE_CANDIDATES_TO_CSIR
RUN_RECURRENT_MEANING_DYNAMICS
STABILIZE_SEMANTIC_ATTRACTORS
CONSTRUCT_RESPONSE_CSIR
```

### Required fix
Phase 5 Stage ABI migration.

### Exit test
Machine-readable stage contract matches `CORE_LOOP.md` exactly.

---

## CI-003 — Pre-Stage-0 request-frequency cognition/maintenance

**Severity:** critical  
**Status:** OPEN

### Problem
`run_text()` currently performs learning activation, runtime-self observation, and participant setup before Stage 0.

### Risk
- hidden semantic state changes before authority pin;
- request frequency becomes a maintenance clock;
- harder replay and performance.

### Required fix
Move:
- release/learning activation to startup/event maintenance;
- telemetry to provider schedule/change;
- participant lifecycle to session setup;
- Stage 0 only pins/exposes current snapshots.

### Exit test
Normal request performs no unrelated durable maintenance before Stage 0.

---

## CI-004 — Per-request release/service authority overwork

**Severity:** critical  
**Status:** OPEN

### Problem
Full/duplicated authority checks are coupled to ordinary cognition.

### Required fix
One-time `RuntimeAttestation` plus O(1) generation checks.

### Exit test

```text
0 release hashes/request
0 boot hashes/request
```

---

## CI-005 — One mutable snapshot fingerprint conflates authority and world state

**Severity:** critical  
**Status:** OPEN

### Problem
Stage capability/read consistency relies on one snapshot fingerprint spanning mutable store state.

### Risk
Unrelated writes can invalidate semantic authority assumptions/caches and force serialization/restarts.

### Required fix

```text
AuthorityGeneration
ReadGeneration
WorldRevision
DiscourseRevision
AuditRevision
```

### Exit test
Audit/emission write does not invalidate definition closure cache.

---

## CI-006 — RecordKind-wide lookup scans

**Severity:** high  
**Status:** OPEN

### Problem
Runtime resolves refs by iterating all `RecordKind`.

### Required fix
Typed pins + ref→kind index + indexed exact lookup.

### Exit test
Hot lookup query plan contains no all-kind probe.

---

## CI-007 — Whole-store/overlay asymptotic coupling

**Severity:** high  
**Status:** OPEN

### Problem
O(1) writes may trigger O(total history) fingerprint/cache behavior.

### Required fix
Incremental authenticated roots + domain generations + targeted invalidation.

### Exit test
1k/10k/100k overlays show bounded per-write behavior.

---

## CI-008 — Global snapshot/SQLite serialization and double-snapshot ceremony

**Severity:** high  
**Status:** OPEN

### Required fix
- concurrent read connections/snapshots;
- short write transaction connection;
- pass explicit read generation;
- no global Python lock around semantic stages.

### Exit test
Concurrent read-only cycles overlap.

---

## CI-009 — Transient cognition persisted across too many stages

**Severity:** high  
**Status:** OPEN

### Problem
Current runtime persists significance, goals, response UOL, realization artifacts and other intermediate structures as routine stage behavior.

### Required fix
`CycleWorkspace` + explicit persistence/effect matrix.

### Exit test
Simple read-only conversation does not persist transient compiler/goal/realization graphs unless configured for audit.

---

## CI-010 — Learning promotion/activation coupled to every request

**Severity:** critical  
**Status:** OPEN

### Required fix
Event/schedule/startup/consolidation-driven promotion and activation.

### Exit test
Unrelated chat request performs no full learning package/promotion scan.

---

## CI-011 — Broken `RuntimeLearningAdvancer` candidate packaging call

**Severity:** critical  
**Status:** OPEN

### Problem
Current learning advancement calls `_package(frontier, pins, dependency_pins)` while the method accepts `(frontier, pins)` and the call-site variable is undefined.

### Risk
Learning can crash exactly when a frontier reaches candidate packaging.

### Required fix
- correct call/signature;
- explicitly propagate dependency pins;
- unit + end-to-end candidate packaging tests.

### Exit test
A real frontier can create candidate package without exception and with complete dependency lineage.

---

## CI-012 — Candidate dependency pins are discarded

**Severity:** critical  
**Status:** OPEN

### Problem
Package dependency assembly currently derives from an empty iterator in the runtime learning path.

### Required fix
Persist exact dependency pins from candidate proposals.

### Exit test
Promoted candidate closure reconstructs exact upstream dependencies after restart.

---

## CI-013 — Default runtime can claim learning while no general candidate inducers are installed

**Severity:** critical  
**Status:** OPEN

### Problem
Runtime defaults to an empty inducer set.

### Required fix
Install canonical inducer registry for supported learning classes, or report learning capability honestly as unavailable.

### Exit test
Unknown/teaching case advances from frontier to concrete candidate through reviewed general mechanism.

---

## CI-014 — Epistemic admission is safe but too unspecified for usable conversation

**Severity:** critical  
**Status:** OPEN

### Problem
Ordinary assertions may remain attributed-only with no practical policy for conversation-local participant facts.

### Required fix
Explicit admission classes and policy.

### Exit test
`My name is Chibu` → scoped participant fact → `What's my name?` returns `Chibu`, while high-risk claims remain appropriately unadmitted.

---

## CI-015 — Participant/session initialization is mixed with request execution

**Severity:** high  
**Status:** OPEN

### Required fix
Session/context lifecycle with idempotent initialization independent of message count.

---

## CI-016 — No early end-to-end English conversational kernel gate

**Severity:** critical  
**Status:** OPEN

### Problem
Existing plan builds broad substrates without forcing usable conversation early.

### Required fix
Phase 12 conversational alpha milestone.

### Exit test
Multi-turn memory/query/correction/partial-understanding suite passes semantically.

---

## CI-017 — Minimum reviewed English substrate is undefined

**Severity:** critical  
**Status:** OPEN

### Required fix
Define minimum forms/lexemes/morphology/construction families in implementation and acceptance contracts.

### Exit test
Core English suite passes without phrase handlers.

---

## CI-018 — UOL and CSIR risk becoming two competing semantic brains

**Severity:** critical  
**Status:** OPEN

### Required fix
One-way UOL→CSIR compiler; UOL shadow/migration only.

### Exit test
No public request fallback to UOL when CSIR fails.

---

## CI-019 — UOL migration deferred too late

**Severity:** high  
**Status:** OPEN

### Required fix
Start Stage-5 shadow compilation immediately after CSIR/closure foundation.

---

## CI-020 — Recurrent dynamics lack bootstrap/calibration contract

**Severity:** high  
**Status:** OPEN

### Required fix
Define:
- initial deterministic immutable parameter artifact;
- message families;
- iteration/convergence budgets;
- inhibition;
- calibration;
- non-convergence semantics;
- promotion/drift rules.

### Exit test
Deterministic baseline and recurrent solver agree on reference competence cases within declared tolerance.

---

## CI-021 — Discourse/common-ground ownership under-specified

**Severity:** high  
**Status:** OPEN

### Required fix
Dedicated participant/coreference/open-question/clarification/common-ground implementation.

### Exit test
`Why?`, `For what?`, `What did you mean?`, `What happened to it?` bind to correct semantic targets.

---

## CI-022 — Acceptance contract terminology/version drift

**Severity:** critical  
**Status:** OPEN

### Problem
Old acceptance tests still describe v3.5/UOL as canonical.

### Required fix
Replace with v3.5.1 CSIR acceptance contract.

---

## CI-023 — Missing canonical `CORE_ISSUES.md`

**Severity:** critical  
**Status:** OPEN until this file is adopted

### Problem
README/governance references a mandatory file that was absent at the expected path.

### Required fix
Adopt this register and maintain it continuously.

---

## CI-024 — Full semantic round-trip on every emission is too expensive

**Severity:** high  
**Status:** OPEN

### Required fix
Proof-carrying deterministic realization + selective independent re-analysis policy.

### Exit test
Release competence still uses full round trip; ordinary reviewed deterministic path uses cheap verified proof unless novelty/risk/audit triggers full re-analysis.

---

## CI-025 — Final status can hide blocked requested behavior

**Severity:** critical  
**Status:** OPEN

### Required fix
`CycleCompletionStatus` + frontier effects.

### Exit test
No-response due to blocking frontier cannot be reported as success.

---

## CI-026 — Response/realization can be blocked by unrelated frontiers

**Severity:** high  
**Status:** OPEN

### Required fix
Typed frontier effects and requested-outcome relevance.

### Exit test
Missing optional affect enrichment does not block a grounded identity answer.

---

## CI-027 — Release artifacts may be treated as implementation targets

**Severity:** high  
**Status:** OPEN

### Required fix
Behavior/competence/performance first; deterministic artifact regeneration last.

### Exit test
No manual hash patching or verifier weakening.

---

# Required closure report

Before v3.5.1 cutover, every critical/high issue above must be:

```text
VERIFIED
or
QUARANTINED_MIGRATION_ONLY with zero public authority
```
