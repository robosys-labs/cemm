> **SUPERSEDED — historical planning context only.**
> **Canonical roadmap: [`/IMPLEMENTATION_PLAN.md`](../../IMPLEMENTATION_PLAN.md)**
>
> This document's useful reasoning has been integrated into the unified
> `IMPLEMENTATION_PLAN.md` (Phases 0–4 + Milestone M0).
> Do not follow this as an active implementation plan.

---

# CEMM v3.5 — Pre-v3.5.1 Stabilization Plan

**Goal:** repair the v3.5 substrate before introducing CSIR semantic-brain dynamics.  
**Strategy:** minimal, measured, reversible changes; preserve behavioral invariants while separating authority planes and removing pathological hot-path work.

---

# 1. Why stabilize before v3.5.1

v3.5.1 introduces substantial new machinery:

- exact CSIR;
- exact definition closure;
- semantic authority generations;
- grounded multidimensional state;
- recurrent semantic activation;
- causal mechanism propagation;
- prediction/error learning;
- proof-carrying response generation.

Adding these onto the current v3.5 authority/storage coupling would magnify:

- latency;
- cache churn;
- record volume;
- lock contention;
- false blocking;
- identity collisions;
- replay complexity.

Therefore v3.5.1 begins only after the substrate has stable contracts.

---

# 2. Safety rule: optimize by relocating invariants, not deleting them

Every stabilization patch must identify:

```text
old invariant
old enforcement location
new enforcement location
proof of equivalence
performance effect
failure-mode effect
rollback path
```

No patch may simply remove a gate because it is slow.

---

# 3. Phase S0 — Instrument the current runtime before modifying it

Add structured timings/counters around:

```text
RuntimeAuthorityGuard
RuntimeSelfObserver
LearningRuntimeActivator
Stage 0–22
snapshot open/close
records(kind)
get_record
resolve_any
apply_patch
overlay fingerprint rebuild
dependency invalidation
round-trip analyzer
realization compiler
emission gate
```

Capture:

```text
wall time
CPU time
SQLite query count
rows read
records decoded
cache hits/misses
lock wait
files hashed
bytes hashed
write transaction count
records written
```

Baseline cases:

1. hello/no durable knowledge mutation;
2. simple factual assertion;
3. state query;
4. known response;
5. unknown/partial input;
6. realization frontier;
7. learning frontier;
8. concurrent 1/4/16/64 requests;
9. long-lived overlay with 1k/10k/100k records.

Do not optimize blind.

---

# 4. Phase S1 — Fix deterministic identity and runtime-self crash

## S1.1 Canonical identity comparison

Create:

```text
canonical_record_identity(record_kind, payload)
canonical_content_fingerprint(record_kind, payload)
```

Replace raw persisted-object equality checks.

## S1.2 Runtime epoch

Create one `RuntimeEpoch` at runtime construction.

`RuntimeSelfObserver` receives it.

## S1.3 Stable observation semantics

Do not create a new durable observation for unchanged mechanical runtime state every request.

## S1.4 Idempotency result handling

Return typed status:

```text
NO_CHANGE
IDEMPOTENT
UPDATED
CONFLICT
CORRUPT
```

Only `CORRUPT` required authority hard-fails runtime.

## S1.5 Regression tests

- encode/decode canonical equivalence;
- nested tuple/list metadata;
- repeated same runtime signal;
- restart creates fresh epoch;
- concurrent same-signal requests;
- changed signal creates new observation;
- telemetry conflict does not corrupt semantic authority.

---

# 5. Phase S2 — Introduce one-time RuntimeAttestation

Refactor `RuntimeAuthorityGuard`.

## S2.1 Startup API

```python
attestation = guard.verify_release_once()
runtime = build_runtime(..., attestation=attestation)
```

## S2.2 Hot-path API

```python
attestation.require_current_generation()
```

O(1).

## S2.3 Remove duplicate full calls

No full `require_service_authority()` from:

- `public Runtime.run_text`;
- `CanonicalOrchestrator.run`.

`build_runtime` consumes a verified attestation.

## S2.4 Integrity reload

Explicit:

```text
reload_release()
-> verify new generation
-> construct new immutable authority context
-> atomic generation switch between cycles
```

Never mutate one active pass.

## S2.5 Tests

Count file hashing calls.

Normal request must hash zero release files.

---

# 6. Phase S3 — Split authority and mutable snapshots

Introduce:

```text
AuthorityGeneration
AuthoritySnapshot
WorldRevision
DiscourseRevision
AuditRevision
RuntimeObservationRevision
```

## S3.1 AuthoritySnapshot

Pinned at Stage 0 and immutable for pass.

It excludes ordinary:

- claims;
- state observations;
- response artifacts;
- journals;
- common-ground writes.

## S3.2 World/discourse read generation

Pin based on consistency requirement.

Allow explicit refresh/re-entry after commits.

## S3.3 StageCapability

Replace ambiguous:

```text
snapshot_fingerprint
```

with:

```text
authority_generation
read_generation
pass_ref
stage
nonce
```

## S3.4 Trace

Trace both authority and state changes explicitly.

---

# 7. Phase S4 — Fix storage asymptotics

## S4.1 Incremental overlay root

Replace full row scan fingerprint on every patch.

## S4.2 Indexed direct lookup

Implement indexed exact/effective APIs.

## S4.3 Ref-kind index

Stop `for kind in RecordKind` resolution.

## S4.4 Domain generations

Patch declares domains changed.

Only dependent caches invalidate.

## S4.5 Query plans

Add `EXPLAIN QUERY PLAN` assertions for hot queries.

---

# 8. Phase S5 — Remove global snapshot serialization

## S5.1 Read connection model

Use:

- immutable boot read connection/pool;
- overlay read connections suitable for concurrent snapshots;
- dedicated short write transaction connection.

## S5.2 Lock scope

Python lock covers:

- generation swap;
- write coordination where required.

It does not cover semantic analysis.

## S5.3 Eliminate double snapshot

Orchestrator passes read token.

Stage consumes it.

## S5.4 Concurrency tests

Prove multiple read-only cycles overlap.

---

# 9. Phase S6 — Event-driven pre-cycle maintenance

## S6.1 Learning promotion

Move from every-request scan to:

```text
on package/evidence/competence/review event
startup reconciliation
explicit consolidation
```

## S6.2 Runtime observation

Observe by provider schedule/change/freshness, not chat request count.

## S6.3 Session participant

Create once per context/principal identity.

Use canonical idempotent initialization.

---

# 10. Phase S7 — Compile semantic eligibility

Current per-use governance is replaced by activation-time compilation.

Produce:

```text
CompiledSemanticCapability {
  definition_pin
  denotation
  bindable
  queryable
  inferable
  transition_profile_pin?
  causal_profile_pin?
  realization_projection_pins
  scope
}
```

Dangerous privileges remain separate:

```text
MutationPermission
OperationAuthorization
DisclosureAuthorization
EmissionAuthorization
```

This phase must be tested carefully to avoid accidentally broadening learned authority.

---

# 11. Phase S8 — Reduce mid-cycle durable writes

Create `CycleWorkspace`.

Stage 0–22 artifacts live there by default.

Commit boundaries:

```text
semantic admission/state commit
external operation journal/result
required learning evidence
external emission journal/result
output/common-ground state
```

Make transient compiler artifact persistence optional/audit-configured.

---

# 12. Phase S9 — Proof-carrying realization verification

## S9.1 Realizer proof

Every transform records:

```text
input semantic fragment
rule pin
output semantic preservation claim
lexical pin
morphology pin
linearization pin
coverage
qualification preservation
```

## S9.2 Cheap mandatory verifier

Verify proof graph and source pins.

## S9.3 Full round-trip policy

Run independent full re-analysis when:

- new language authority generation;
- novel realization path;
- non-deterministic generator;
- high-risk disclosure;
- proof verifier uncertainty;
- configured audit sample.

## S9.4 Release competence

Every supported construction family still passes independent round-trip in release verification.

---

# 13. Phase S10 — Final outcome and partial-cognition semantics

Introduce:

```text
CycleCompletionStatus
```

At minimum:

```text
SUCCESS
PARTIAL
NO_RESPONSE_REQUIRED
RESPONSE_DEFERRED
RESPONSE_BLOCKED
ACTION_UNCERTAIN
RUNTIME_ERROR
```

Frontiers carry severity/effect:

```text
informational
learning
blocks_query_answer
blocks_realization
blocks_effect
blocks_emission
```

Stage 22 computes honest completion.

---

# 14. Phase S11 — Performance acceptance gate

Set budgets from measured baseline after S0.

Required shape:

```text
steady-state request:
  O(semantic work + bounded indexed reads)
not:
  O(release size + boot size + overlay history + all record kinds)
```

Acceptance checks:

- zero release rehash per normal cycle;
- zero full overlay scan per patch;
- no all-kind probe lookup;
- no per-request full learning package scan;
- targeted cache invalidation;
- concurrent reads overlap;
- stable runtime observations do not write every request;
- stage trace preserves exact authority generation;
- effect authorization remains fail closed.

---

# 15. Phase S12 — Freeze stable substrate interfaces for v3.5.1

v3.5.1 must build only on these stable contracts:

```text
RuntimeAttestation
AuthoritySnapshot
SemanticAuthorityResolver
WorldStateView
DiscourseStateView
RuntimeObservationSnapshot
CycleWorkspace
EffectAuthorizationBoundary
CanonicalPersistenceIdentity
GenerationAwareCache
```

The semantic-brain architecture then plugs in:

```text
CSIR compiler
recurrent semantic dynamics
grounded state estimator
causal mechanism engine
prediction-error learner
response utility/goal system
```

without knowing about release file hashes, boot SQL enumeration or global store locks.

---

# 16. Minimal first patch set

The first stabilization patch should remain deliberately narrow.

Modify:

```text
cemm/v350/runtime_state.py
cemm/v350/storage/codec.py or canonical identity helpers
cemm/v350/storage/store.py
cemm/v350/public_runtime.py
cemm/v350/cutover.py
cemm/v350/orchestration.py
cemm/v350/runtime.py
tests/v350/
```

Deliver only:

1. canonical deterministic identity comparison;
2. runtime-instance epoch;
3. one-time attestation object;
4. no full authority recheck in normal request;
5. instrumentation proving removed hot-path work;
6. unchanged semantic/effect authorization behavior.

Do **not** combine the first patch with CSIR migration.

This keeps rollback and regression isolation manageable.

---

# 17. Second patch set

After first patch passes:

1. split AuthoritySnapshot from mutable store revision;
2. generation-aware cache domains;
3. incremental overlay root;
4. direct indexed record lookup;
5. ref-kind index;
6. concurrent read snapshot model.

---

# 18. Third patch set

Then:

1. event-driven learning promotion;
2. live runtime observation plane;
3. CycleWorkspace;
4. reduced transient persistence;
5. final-cycle status.

---

# 19. Fourth patch set

Then:

1. compile semantic eligibility;
2. separate effect authorization;
3. proof-carrying realization;
4. selective full roundtrip;
5. performance acceptance.

Only then begin the v3.5.1 semantic-brain implementation phases.

---

# 20. Must-preserve invariants during stabilization

The following may not regress:

1. exact Stage-0..22 logical order;
2. no legacy semantic authority path;
3. no phrase-specific semantic routing;
4. claims are not automatically world truth;
5. event occurrence does not automatically mutate state;
6. external operations require explicit authorization;
7. response meaning precedes wording;
8. output disclosure respects permission;
9. external emission is journaled/idempotent;
10. common ground is evidence-relative;
11. learned candidates do not self-promote without required competence/review policy;
12. historical records retain exact interpretation lineage;
13. side effects remain outside semantic DB transactions;
14. unresolved meaning remains visible;
15. no verifier bypass or fake authority.

---

# 21. New invariants added by stabilization

1. release attestation is immutable-generation based;
2. normal requests do not rehash release artifacts;
3. authority snapshot excludes ordinary mutable cognition;
4. canonical fingerprints define persisted identity equality;
5. stable runtime state is not request-frequency persisted;
6. one small write does not scan all historical rows;
7. semantic definition caches survive unrelated audit writes;
8. read-only semantic stages can execute concurrently;
9. semantic interpretation is not treated as an external effect;
10. every hard block identifies the exact plane that denied it.

---

# 22. Go/no-go for v3.5.1

Proceed only if:

```text
correctness gates pass
+
behavioral v3.5 regression suite passes
+
authority invariants pass
+
performance budgets pass
+
concurrency tests pass
+
crash reproducer is eliminated
+
no safeguard was hidden or bypassed
```

The stabilization work is complete when v3.5 becomes a lean, exact substrate rather than an authority-heavy runtime that v3.5.1 would have to fight against.
