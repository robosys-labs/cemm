# CEMM v3.5.1 Acceptance Contract — Canonical CSIR Runtime

**Status:** active canonical acceptance contract  
**Roadmap authority:** `IMPLEMENTATION_PLAN.md`  
**Runtime authority:** `RUNTIME_PLAN.md` + `CORE_LOOP.md` + `CEMM_CORE_MATHS.md`

This contract replaces UOL-era public-runtime acceptance criteria. Historical UOL/v347
behavior may be tested only under explicit migration/offline suites and may never be a
fallback authority for a public request.

## A. Architecture and legacy quarantine

1. Public/runtime modules import no `cemm.v347` code.
2. `cemm.v347` exports no `Runtime` and no wildcard semantic API.
3. Canonical runtime imports no legacy UOL/composition request brain.
4. Old Stage names (`BUILD_UOL_FACTOR_GRAPH`, `SOLVE_MEANING_HYPOTHESES`,
   `SELECT_MEANING_BUNDLE`, `BUILD_RESPONSE_UOL`) do not occur in canonical runtime,
   runtime graph or canonical tests.
5. v3.5 UOL may exist only in explicit offline/shadow migration code. CSIR failure never
   routes a public request back to UOL.

## B. Stage ABI

The machine-readable `CoreStage` and `StageContract` sequence must match
`CORE_LOOP.md` Stage 0–22 exactly.

Stages 5–7 are semantic operations, not renamed wrappers:

```text
5 COMPILE_CANDIDATES_TO_CSIR
6 RUN_RECURRENT_MEANING_DYNAMICS
7 STABILIZE_SEMANTIC_ATTRACTORS
```

A missing CSIR compiler/recurrent solver/attractor stabilizer produces a typed runtime
capability frontier. It must never invoke the old UOL factor-graph solver.

Every stage contract declares:
- required inputs;
- produced outputs;
- allowed mutable generations;
- persistence class;
- effect classes;
- frontier classes;
- budgets;
- proof requirements.

A stage that changes an undeclared generation fails the cycle as a contract violation.

## C. Authority and semantic eligibility

1. Executable semantic authority is pinned to exact `AuthorityGeneration` and content
   fingerprint.
2. Candidate/provisional records do not become executable by frequency or persistence.
3. `CompiledSemanticCapability` is compiled from exact lifecycle, use profile,
   dependencies and promotion lineage.
4. Semantic eligibility never grants durable mutation, external operation, protected
   disclosure or emission authority.
5. Learned overlay authority requires exact promotion/use-grant lineage.

## D. Effect authorization

`EffectAuthorizationBoundary` is fail-closed at the actual effect boundary.

- Durable semantic/world/learning commit: Stage 13, with exact GraphPatch identity,
  pre-effect CAS revision, target set and policy prerequisites through the guarded store; Stage 22 may consolidate/invalidate and schedule promotion, but a
  new executable AuthorityGeneration is published only after the current semantic-pass
  lease is released through an explicit maintenance/promotion boundary.
- External operation: Stage 16 only. The kernel requires `prepare()` first (including
  guarded prepared-journal persistence), then issues an exact external-operation receipt,
  and only then calls `execute()`; every observation must map to an authorized operation.
- Protected disclosure/external emission: Stage 20 only, after exact audience/scope,
  semantic-preservation proof and emission gate authorization.

No broad cognition gate may substitute for these narrow checks.

## E. Cycle-local cognition and persistence

Default behavior:

| Stage | Persistence |
|---|---|
| 0–12 | workspace only |
| 13 | semantic/world/learning CAS commit |
| 14 | workspace; optional audit |
| 15 | workspace; optional decision audit |
| 16 | effect journal only when an operation is attempted |
| 17 | reconciliation/evidence only |
| 18 | workspace; optional audit |
| 19 | workspace; optional audit |
| 20 | emission/effect journal only when attempted |
| 21 | output discourse/common-ground commit |
| 22 | consolidation/invalidation/replay; promotion publication scheduled post-pass |

A simple read-only conversation must not persist significance, goals, response
compiler graphs or realization intermediates merely because stages executed.

## F. Proof-carrying realization

Every deterministic realization candidate carries a `RealizationProof` with:
- exact semantic input fingerprint;
- exact authority generation;
- exact rule/lexical/morphology/linearization pins;
- semantic coverage;
- qualification fingerprint;
- permission/audience scope;
- surface hash.

Cheap proof verification is mandatory for every emission.

Independent semantic re-analysis is policy-driven:
- mandatory for release competence;
- mandatory for declared high-risk/novel/audit/unreviewed/channel-transform cases;
- not mandatory for an ordinary reviewed deterministic path whose proof verifies.

A failed cheap proof cannot be rescued by a successful independent round-trip.

## G. Learning maintenance

Learning advancement occurs because a typed event exists, not because a chat request
occurred. Targeted post-cycle learning events may run only after the semantic-pass
AuthorityGeneration lease is released.

An empty inducer/learning service set must report learning capability as unavailable;
it must not claim successful general learning.

## H. Completion semantics

The runtime distinguishes at least:

```text
SUCCESS
PARTIAL
NO_RESPONSE_REQUIRED
RESPONSE_DEFERRED
RESPONSE_BLOCKED
ACTION_UNCERTAIN
RUNTIME_ERROR
```

`errors=[]` is not success. Optional enrichment/frontiers may not block an otherwise
fully grounded requested answer.

## I. Required gates for Phase 4–5

```bash
python tools/check_v351_legacy_boundaries.py
pytest -q tests/v350/test_v351_phase4_capabilities_effects.py
pytest -q tests/v350/test_v351_phase4_realization_proof.py
pytest -q tests/v350/test_v351_phase5_stage_abi.py
pytest -q tests/v350/test_v351_phase5_cutover_contract.py
pytest -q tests/v350/test_v351_legacy_boundaries.py
python tools/capture_v351_phase0_baseline.py --strict-hot-path
python tools/benchmark_v351_phase2_store.py --scales 1000,10000,100000
pytest -q tests/v350
```

Signed release artifacts are regenerated only after behavior, architecture,
concurrency, performance and competence gates pass. Hashes/verifiers must never be
patched to manufacture success.
