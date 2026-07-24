# CEMM v3.5.1 — Phase 1 Review and Phase 2–3 Implementation

Target baseline: `2cad08fd5bbf2f0a6dd74500a450dad2cdee4883`.

## Phase 1 review: additional bugs fixed

### 1. Concurrent session-participant CAS recovery was not exact enough

The landed Phase-1 implementation correctly introduced canonical fingerprint identity,
but the conflict-recovery branch still accepted a concurrent creator when the expected
refs merely existed. The Phase 2–3 patch tightens that boundary so the deterministic:

- participant referent;
- participant evidence;
- participant type assertion, when created;

must match their exact expected fingerprints.

A race can no longer convert a conflicting durable identity into silent success.

### 2. Attested manifest nested structures remained mutable

`RuntimeAuthorityManifest` is a frozen dataclass, but nested mappings such as
`metadata`, `release_capabilities`, and runtime service binding dictionaries remained
mutable Python objects. The patch seals a deep-frozen copy for runtime consumption
after full verification. The raw guard remains the verification authority; runtime
services cannot mutate their attested configuration in place.

### 3. RuntimeLearningAdvancer candidate packaging was still broken

The current implementation calls `_package(frontier, pins, dependency_pins)` while
`dependency_pins` is undefined at that call site, and `_package` reconstructs
dependencies from an empty iterator. The patch:

- returns candidate pins and exact dependency pins together from `_persist_proposals`;
- passes them explicitly into `_package`;
- stores them in `LearningPackageRecord.dependency_pins`;
- adds targeted `frontier_refs` support for event-driven maintenance.

This is required even though general induction remains a later phase because Phase 3
moves advancement into maintenance and that maintenance path must not crash.

---

## Phase 2 — generation-separated, indexed, concurrent storage

### Authority is no longer the whole mutable store fingerprint

The patch introduces:

```text
AuthoritySnapshot
ReadGeneration
WorldRevision
DiscourseRevision
RuntimeObservationRevision
AuditRevision
EffectJournalRevision
```

`StoreSnapshot.fingerprint` remains as a compatibility read-generation identity until
the Phase-5 Stage ABI migration, but executable semantic authority now has an
independent generation and fingerprint.

A world or discourse write therefore does not redefine semantic definitions.

### Generation ownership

Runtime record families are assigned to the narrowest generation plane:

- definitions, schemas, transition contracts, language/construction authority,
  policies, realization contracts and adapter contracts → `AuthorityGeneration`;
- referents, admitted knowledge, state, capability, events, evidence → `WorldRevision`;
- claims/output/common-ground state → `DiscourseRevision`;
- operation/emission effects → `EffectJournalRevision`;
- transient compatibility records, learning candidates/results, significance/goals
  and realization copies → `AuditRevision`;
- runtime observation patches additionally advance `RuntimeObservationRevision`.

Dependency changes advance the dependent domain as well.

### Indexed lookup

The existing SQLite index:

```text
record_index_ref_idx(record_ref, record_kind, revision DESC)
```

is now used directly.

`resolve_any(ref)` performs indexed `record_ref` discovery rather than:

```python
for kind in RecordKind:
    get_record(kind, ref)
```

Latest exact/effective `get_record` also queries by indexed kind/ref instead of
materializing every record of a kind first.

### O(1) authenticated overlay root update

The old runtime recomputed a fingerprint by scanning the complete overlay record and
tombstone history after every patch.

The new runtime root is append-authenticated:

```text
R_(n+1) = H(R_n, patch_fingerprint, store_revision_(n+1))
```

This preserves deterministic tamper-evident transition identity without making an
O(1) write perform an O(total-history) scan.

### Concurrent read snapshots

The canonical store now uses:

- one serialized writer connection/short writer lock;
- independent per-thread normal readers;
- independent pinned snapshot reader connections;
- immutable boot readers;
- no global Python lock held while a semantic stage computes.

Pinned snapshots remain valid after unrelated commits because they are actual SQLite
read transactions rather than "current store must still equal this fingerprint"
assertions.

### Cache generations

Schema and language registries are keyed by:

```text
authority_generation + authority_fingerprint
```

not by every mutable store write.

Record caches are keyed by only their owning generation domains plus authority.

An audit write no longer flushes definition/language closure caches.

---

## Phase 3 — cycle workspace, maintenance, lifecycle and honest completion

### CycleWorkspace

`CycleWorkspace` is now the live home of cycle artifacts and frontier effects.

The existing `CycleState.artifacts` mapping remains an alias during the v3.5
compatibility ABI period so this stabilization patch does not prematurely perform the
Phase-5 stage rewrite.

Re-entry carries only the explicit artifact whitelist into a fresh workspace.

### Read-generation consistency

Every stage capability now carries separate authority and cognitive generation
identity.

Before Stage 13:

- an authority change invalidates/restarts the pass;
- a world/discourse/runtime-observation change invalidates/restarts the pass;
- an audit-only or effect-journal-only write does **not** restart unrelated cognition.

Restarts are bounded.

After the durable commit boundary, the runtime does not pretend that its own expected
writes are an authority violation.

### Event-driven maintenance

Request-frequency maintenance is removed from `run_text()`:

```text
LearningRuntimeActivator(...).activate_ready()
RuntimeSelfObserver(...).observe(...)
```

The runtime now has an explicit `MaintenanceScheduler` with triggers for:

```text
startup
reload
runtime signal changed
learning evidence changed
competence completed
review decision
explicit consolidation
timer/manual host event
```

No background thread is introduced.

Runtime observation runs at startup/reload/change and persists only when the stable
signal snapshot changed.

Reviewed learning activation runs at startup/reload.

Candidate/competence advancement runs only on explicit learning events, not because a
chat request occurred.

### Session participant lifecycle

`SessionParticipantLifecycle` resolves/persists stable transport-grounded participant
identity once per session key.

`Runtime.prepare_session(...)` is available to hosts that can establish session
identity before the first request. `run_text()` remains backwards compatible and
lazily initializes through the same idempotent lifecycle when necessary.

### Learning frontier lookup

Stage 11 no longer scans every historical learning frontier revision each turn.

The structural frontier key is deterministic, so the runtime derives the exact
frontier ref for each current observation and fetches only those records.

### Honest completion status

The runtime now emits one of:

```text
SUCCESS
PARTIAL
NO_RESPONSE_REQUIRED
RESPONSE_DEFERRED
RESPONSE_BLOCKED
ACTION_UNCERTAIN
RUNTIME_ERROR
```

`errors=[]` is not treated as success.

Frontiers carry effects such as:

```text
informational
learning
blocks_query_answer
blocks_commit
blocks_effect
blocks_realization
blocks_emission
```

Only relevant blocking effects prevent the corresponding outcome.

---

## Compatibility persistence note

The current v3.5 Stage-14–19 coordinators still require exact durable pins between
their legacy downstream steps. Removing every intermediate write in Phase 3 alone
would either break those exact-pin contracts or require prematurely implementing the
Phase-4/5 realization and Stage-ABI changes.

This patch therefore makes `CycleWorkspace` the live cycle authority while classifying
those compatibility copies into `AuditRevision`, not semantic authority or world
truth.

The final removal/selective retention of those copies belongs with Phase 4's
proof-carrying realization/effect-boundary work and the Phase-5 Stage ABI migration.
They must not be treated as semantic authority in the meantime.

---

## Verification gates

Run:

```bash
python -m compileall cemm/v350

pytest -q tests/v350/test_v351_phase0_1_stabilization.py
pytest -q tests/v350/test_v351_phase2_3_runtime_substrate.py

python tools/capture_v351_phase0_baseline.py --strict-hot-path

python tools/benchmark_v351_phase2_store.py \
  --scales 1000,10000,100000

pytest -q tests/v350
```

Do not regenerate signed release artifacts until behavior, architecture,
concurrency/performance and full regression tests pass.
