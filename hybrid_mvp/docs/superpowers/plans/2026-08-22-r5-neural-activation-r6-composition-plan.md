# R5 Neural Activation and R6 Composition Implementation Plan

> **Conditional target:** The August 29 R4.1 data/supervision amendment has
> precedence. No training, model selection, calibration, frozen evaluation,
> realization publication or activation task in this document is executable
> until fresh R4.1 admission authenticates semantically useful purpose classes,
> independent reviewed derivations and reviewed response surfaces.
> R4.1 is an external prerequisite implemented and admitted outside this
> document. Current status is derived only from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).
> This document cannot implement, rebuild, publish, or admit R4.1.

**Date:** 2026-08-22  
**Status:** reviewed pre-implementation work plan  
**Scope:** `hybrid_mvp/` only  
**Starting branch:** `agent/r4-task4-batch-publisher-20260816`  
**Starting commit reviewed:** `5c704399b417414cf91211d6d9a9a8c8ce84767c`

> Execute task-by-task with test-first owner changes, exact Git publication,
> contract review, code-quality/performance review, and fresh verification.
> Every completed chunk must be committed and pushed. No implementation result
> may exist only in a local worktree.

## Global invariants

- Fresh R4.1 admission must be current before Task 2.
- `governance/test_inventory.json` remains byte-identical.
- R5 foundation behavior remains red/not-admitted until Task 16.
- Frozen test is not opened, enumerated, hashed, counted, or logged.
- Train, selection, and calibration capabilities expose one class only.
- No release bootstrap/static/template fallback.
- No internal semantic-ref spelling reaches model features.
- No arbitrary `latest` artifact discovery.
- Every artifact and receipt is canonical and content-addressed.
- Linux and Windows path/process safety are required.
- R5 and R6 are admitted separately.
- R7 remains red.
- One canonical codec serves each ABI family; no receipt-specific wrappers.
- R5 uses one purpose-snapshot type and at most five active owner modules.
- No non-selected checkpoint weights are committed to Git.
- No new runtime dependency, accelerator backend, cache, or streaming
  protocol is introduced without separate measured review.
- Artifact verification, hashing, and model loading occur at startup, not
  per request.
- Task 2 freezes hard resource ceilings before model implementation.

## Task 0 — Publish authority and exact baseline

**Purpose:** make this design and plan governing before code changes.

1. Add the 2026-08-22 design and plan to `docs/DOCUMENT_AUTHORITY.json`.
2. Update exact governing-document constants in
   `tests/test_replay_governance.py`.
3. Apply the final efficiency and anti-bloat refinement: consolidate
   purpose snapshots and receipt families, freeze hot-path rules, prevent
   non-selected artifact retention, and collapse API/web into one HTTP adapter.
4. Add narrow supersession notices to the R5 foundation documents:
   foundation remains authoritative for hard-cut behavior; this plan governs
   activation and R6.
5. Update `docs/IMPLEMENTATION_PLAN.md` to point here.
6. Run governance tests, metadata verification, source-only inventory G0-R5,
   structural hard cut, legacy audit, and ledger verification.
7. Commit and push one documentation/governance change.

**Stop:** do not modify runtime/model/training source in this task.

## Task 1 — Confirm the external R4.1 admission prerequisite

R4.1 is an external prerequisite. This plan cannot implement, rebuild, publish,
or admit it.

1. Read effective status and exact admission identities only from the replay
   ledger.
2. Require one fresh R4.1 admission produced by the separately governed R4.1
   implementation plan.
3. Verify that admission authenticates meaningful purpose-class semantic
   coverage, independent derivation and abstention supervision, and reviewed
   ResponseMeaning-to-surface supervision.
4. Verify source ancestry, clean state, and remote equality without modifying
   R4 evidence or appending status.
5. Stop this plan if any prerequisite is absent, stale, ambiguous, or red.

**Acceptance:** fresh R4.1 admission is current; this task creates no artifacts or status row.
**Stop:** no R5 implementation or training before this acceptance passes.

## Task 2 — Freeze R5/R6 ABIs, validation skeleton, and resource budget

Create strict schemas and canonical types for the consolidated ABI
families defined in the design. Register them in `ABI_REGISTRY.md` only after
tests exist. Add `configs/r5_r6_resource_budget.json` with measured baseline and
hard ceilings for model bytes/parameters, startup, RSS, p50/p95 stage latency,
beam/decode/state bounds, round-trip candidates, trace/report bytes, artifact
count/bytes, runtime dependencies, and import time. The same task adds a strict
schema and owner tests; later implementation tasks cannot raise a ceiling.

Add validation graph entries for all R5/R6 owners, but keep:

```text
R5 admission unavailable
R6 admission unavailable
```

until their activation tasks.

Tests must reject unknown fields, duplicate keys, nonfinite values, oversized
documents, unsafe refs/paths, wrong source/authority/ABI identities, and
noncanonical bytes.

Commit/push ABI and graph changes separately from model implementation.

## Task 3 — Implement one purpose-bound class snapshot

Extend R4 class access into one canonical `R5PurposeSnapshot` with an
exact `purpose` discriminator: `train`, `selection`, or `calibration`.
Separate mint/open owners enforce the purpose, but all three variants use
one codec, validator, and provenance envelope. The snapshot contains no
sibling metadata.

Add process-bound tests that prove:

- train cannot open selection/calibration/frozen-test;
- selection cannot open train/calibration/frozen-test;
- calibration cannot open train/selection/frozen-test;
- a purpose mismatch fails before data decoding;
- no class can discover sibling paths, hashes, refs, counts, or manifests;
- frozen-test mint/open is rejected for R5 and R6;
- path traversal, symlink, junction, and reparse escapes fail.

Commit/push the single snapshot ABI and tests before trainer changes.

## Task 4 — Hard-cut obsolete bootstrap training authority

Delete or quarantine from release imports:

- `BootstrapEpisode`;
- bootstrap JSONL loaders;
- `train_proposer`;
- `train_realizer`;
- old artifact-saving entry points where superseded;
- arbitrary validation-path calibration;
- compatibility re-exports.

The active R5 implementation is limited to at most five owner modules:

```text
r5_features.py
r5_proposer.py
r5_realizer.py
r5_lifecycle.py
r5_activation.py
```

`r5_lifecycle.py` owns the discriminated offline receipt variants and
shared canonical codec; it is never imported on the request path. Do not
create a module per receipt, wrapper-only layer, compatibility alias, or
speculative accelerator abstraction. Superseded `model.py`/`training.py`
owners are removed in the same lineage once their successors verify.

The control plane and package initializer remain Torch-light until an exact
activation bundle is loaded. Add structural tests for one release path,
zero bootstrap reachability, the five-module ceiling, and an acyclic import
graph.

## Task 5 — Implement Neural Feature Schema ABI 1

Create canonical structural encoders for:

- form-unit features and exact source geometry;
- contribution kinds;
- orientation/session structure;
- action-prefix structure;
- each context-local pointer table;
- ResponseMeaning and literal-copy slots.

Required tests:

- alpha-equivalent refs produce identical encodings;
- structurally different pointers are distinguishable;
- pointer encodings are not all zero;
- feature construction performs no authority-wide scan;
- bounds reject oversize contexts;
- no source/internal ref spelling appears in tensors or vocabulary;
- deterministic bytes across processes/platforms where specified;
- form/context/pointer features are computed once per request and exposed as
  immutable cached tensors within the request lifetime;
- construction stays inside the frozen allocation and latency ceilings.

## Task 6 — Implement the masked neural proposer

Replace the flat placeholder decoder with separate action and pointer heads.

At every step:

1. construct exact legal candidates;
2. apply masks before softmax and loss;
3. decode only licensed pointers;
4. reuse one cached context encoding and vectorized pointer tables;
5. preserve bounded beam/state/time/RSS limits and materialize only top-k legal
   expansions;
6. emit explicit abstention and model confidence;
7. build canonical Program ABI 2 candidates;
8. pass only the bounded final top-k set to the exact verifier.

Tests consume the deferred proposal assertions:

- masked actions never emit;
- internal ref spelling does not change logits;
- dynamic semantic slots are used;
- capacity is bounded;
- release proposal invokes loaded weights;
- zero-weight ablation breaks learned selection;
- compatible new designations keep the model active;
- no bootstrap delegation.

## Task 7 — Train proposer candidates from authenticated train only

Implement deterministic training with:

- exact train snapshot;
- candidate-order randomization;
- accepted, rejected, and abstention examples;
- per-step masked losses;
- fixed optimizer/config/dependency lock;
- deterministic CPU reference;
- bounded workers/threads/memory/time;
- canonical Training Receipt ABI 1.

Publish the candidate manifest and bounded training receipt
transactionally, but keep candidate weight files in bounded scratch/CI storage.
Do not commit non-selected checkpoints and do not select a checkpoint in this
task.

## Task 8 — Select the proposer checkpoint

Run a fresh selection-only process with a selection capability.

Freeze:

- metric definitions;
- candidate set;
- accuracy/abstention/robustness/latency/capacity metrics;
- deterministic tie-break;
- selected checkpoint identity.

No optimizer or train snapshot may exist in the process. Commit/push
selection evidence and only the selected proposer artifact after enforcing the
repository-size budget; delete non-selected candidate weights.

## Task 9 — Implement the structured neural realizer

Replace sentence-hash classification with a bounded autoregressive decoder over:

- reviewed language-pack surface units;
- discourse/morphology units;
- exact literal-copy pointers;
- end/failure actions;
- legality masks.

Decode only a bounded top-k set, batch round-trip parsing where possible,
and accept the first exact equivalent result in model order. Every result must
undergo public round-trip semantic verification; none may use a template or
static fallback.

Tests consume realization and weight-use obligations:

- normal realization invokes selected weights;
- receipt records model identity and decoder invocations;
- no fallback when weights fail;
- zero-weight realizer loses domain accuracy;
- release artifact pins all semantic inputs;
- literals are copied only from licensed pointers;
- multilingual packs do not introduce English regex routing.

## Task 10 — Train and select realizer candidates

Repeat the train/selection separation used for the proposer.

Selection metrics include:

- semantic round-trip success;
- literal-copy correctness;
- unsupported/failure behavior;
- language-pack coverage;
- latency/RSS/capacity;
- robustness to candidate order and ref renaming.

Commit/push only the selected realizer and selection lifecycle receipt
after enforcing the combined selected-artifact budget; delete non-selected
realizer weights.

## Task 11 — Calibrate selected models

Freeze both selected checkpoints before calibration.

Use a calibration-only snapshot and actual model scores to produce:

- calibrator parameters;
- nonempty confidence bins;
- ECE and threshold evidence;
- abstention threshold;
- exact proposer/realizer identities;
- the `calibration` variant of R5 Lifecycle Receipt ABI 1.

Tests consume all three calibration obligations. Zero-support or fixed-label
confidence fails.

## Task 12 — Reproduce and prove weight use

In fresh scratch outside the repository:

1. retrain proposer and realizer;
2. compare every artifact byte;
3. compare tensor names/dtypes/shapes/bytes;
4. compare model and metadata identities;
5. verify scratch cleanup on success/failure.

Run proposer and realizer zero-weight/ablation experiments with frozen thresholds.
Emit the `reproduction` and `weight_use` variants of the shared R5
Lifecycle Receipt ABI 1.

Consume all reproduction and weight-use deferred assertions.

## Task 13 — Build and verify R5 Activation Bundle

Create one exact bundle containing:

- selected proposer;
- selected realizer;
- calibrator;
- feature/action/response ABI refs;
- authority and source refs;
- dependency lock and Python ABI;
- runtime configuration;
- canary manifest.

Verify all files before tensor access. Test tamper, truncation, swapping,
wrong-authority, wrong-source, wrong-ABI, path escape, symlink/reparse, duplicate,
and unsafe tensor cases.

Publish transactionally with rollback and crash/retry tests on Linux and
Windows. Stop rather than commit selected model blobs when the combined size,
artifact count, or startup/RSS ceilings are exceeded.

## Task 14 — Activate exact R5 runtime path

Add the realization owner to `HybridRuntime`.

Release construction:

- requires exact activation ref;
- loads no bootstrap proposer;
- uses selected neural proposer;
- retains exact verifier and R3;
- uses selected neural realizer;
- produces exact RealizationReceipt;
- verifies artifact bytes and manifests once at root load, then reuses immutable
  handles without per-request rehash or filesystem discovery;
- runs models under `eval()` and `torch.inference_mode()` with frozen thread and
  allocation limits;
- passes typed in-memory objects between phases without JSON round-trips;
- has no normal fallback.

Development remains diagnostic and cannot satisfy release/admission selectors.

## Task 15 — Run fresh R5 activation canaries

Canaries must cover:

- selected proposal;
- explicit abstention;
- verifier rejection;
- normal realization;
- literal-copy realization;
- realization failure with no invented surface;
- OBSERVE/QUERY/REQUEST/SIMULATE;
- effect/no-effect;
- restart and model/store identity;
- tampered activation rejection;
- deadline/cancellation cleanup.

All observations come from the public runtime.

## Task 16 — Complete R5 inventory, phase, and admission

1. Replace every one of the 25 deferred R5 dispositions with exact executable
   successor lineage.
2. Regenerate the R5 disposition receipt.
3. Require no deferred R5 activation obligations.
4. Run every R5 owner and phase.
5. Run fresh R5 admission from committed clean inputs.
6. Append R5 green through the governed updater.
7. Verify effective G0-R5 green and R6-R8 red.
8. Push the exact verified commits and receipts.

## Task 17 — Define R6 composition ABIs and root

Implement `CompositionRequest`, `CompositionResult`, and `CompositionRoot`.

The root:

- requires exact R5 activation ref;
- owns and reuses one verified runtime/model/store lifecycle;
- propagates deadline/cancellation;
- binds idempotency;
- enforces output/trace bounds;
- closes resources deterministically;
- exposes no model/training internals.

Add startup, concurrent-use, restart, corruption, cancellation, and cleanup tests.

## Task 18 — Migrate CLI to the composition root

Replace diagnostic/bootstrap CLI construction with the R6 root.

CLI handles transport only:

- input/session commands;
- typed output rendering;
- optional bounded diagnostic trace;
- no semantic routing or canned answers.

Verify the old CLI path cannot load a development/bootstrap owner in release.

## Task 19 — Add one HTTP adapter for API and web

Create one thin HTTP transport owner used by both API and web. Do not
introduce a second web semantic adapter or server framework. The initial R6
increment has no streaming. The shared adapter provides:

- strict request schemas;
- authentication/authorization hook boundary;
- body/output/time bounds;
- idempotency and cancellation;
- no direct model or semantic-owner imports;
- no fallback responses.

Transport errors remain distinct from semantic cycle results.

## Task 20 — Add evaluation adapter boundary without frozen-test access

The R6 evaluation adapter converts injected cases to CompositionRequests and
records CompositionResults. It has no dataset loader and cannot mint/open
frozen-test capability.

Tests prove R7 is the earliest possible frozen-test owner.

## Task 21 — Prove cross-surface parity

For the same canonical request, CLI, shared HTTP, and evaluation
adapters must bind the same:

- input/evidence identity;
- VerifiedMeaning/expression;
- Decision and proof;
- effect/no-effect receipt;
- ResponseMeaning;
- surface and RealizationReceipt;
- final revision pin.

Only transport envelope fields may differ. Emit Surface Parity Receipt ABI 1.

## Task 22 — Prove operational budgets and failure isolation

Measure and freeze reviewed budgets for:

- cold activation;
- warm request latency;
- proposer/realizer latency;
- peak RSS and model size;
- output/trace size;
- concurrent sessions;
- cancellation latency;
- clean shutdown.

Compare every measurement against the Task 2 ceilings; this task may
freeze tighter values but cannot raise them. Test process-tree termination,
transactional rollback, partial writes, store/model mismatch, adapter
disconnect, repeated idempotency keys, and Linux/Windows path semantics.

## Task 23 — R6 structural hard cut

Reject:

- direct surface imports of model/training/proposer/realizer/effect owners;
- multiple composition roots;
- BootstrapProposer in release reachability;
- semantic regex/keyword routing;
- canned normal responses;
- latest-model discovery;
- frozen-test access;
- UI success substitution;
- unbounded traces or background workers.

## Task 24 — Run R6 phase and admission

1. Run all R6 owners and phase selectors.
2. Verify exact surface parity and operational receipts.
3. Run fresh R6 admission from a clean committed checkout.
4. Append R6 green through the governed updater.
5. Verify effective G0-R6 green and R7-R8 red.
6. Push exact source, generated evidence, admission, and status commits.

## Chunking and publication discipline

Use small owner-scoped commits. Recommended publication tranches:

1. authority + predecessor;
2. ABIs + data firewall;
3. legacy hard cut + features;
4. proposer;
5. proposer training/selection;
6. realizer;
7. realizer training/selection;
8. calibration;
9. reproduction/ablation;
10. activation bundle/runtime;
11. R5 canaries/admission;
12. R6 root;
13. adapters;
14. parity/operations;
15. R6 admission.

After each tranche:

- run focused owner tests;
- run metadata and source-only inventory;
- run affected phase only when cross-owner boundaries changed;
- run structural/legacy audit;
- commit and push;
- verify remote SHA equals the tested SHA.

## Final acceptance

```text
G0 green
R1 green
R2 green
R3 green
R4.1 green (fresh data/supervision admission)
R5 green (neural activation)
R6 green (one composition root, one HTTP adapter, all frozen budgets)
R7 red (frozen-test evaluation not yet run)
R8 red
```

No implementation begins from this plan until Task 0 and Task 1 are green.
