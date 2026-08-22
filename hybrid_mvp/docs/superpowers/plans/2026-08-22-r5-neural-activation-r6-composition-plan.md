# R5 Neural Activation and R6 Composition Implementation Plan

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

- R4 must be current green before Task 2.
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

## Task 0 — Publish authority and exact baseline

**Purpose:** make this design and plan governing before code changes.

1. Add the 2026-08-22 design and plan to `docs/DOCUMENT_AUTHORITY.json`.
2. Update exact governing-document constants in
   `tests/test_replay_governance.py`.
3. Add narrow supersession notices to the R5 foundation documents:
   foundation remains authoritative for hard-cut behavior; this plan governs
   activation and R6.
4. Update `docs/IMPLEMENTATION_PLAN.md` to point here.
5. Run governance tests, metadata verification, source-only inventory G0-R5,
   structural hard cut, legacy audit, and ledger verification.
6. Commit and push one documentation/governance change.

**Stop:** do not modify runtime/model/training source in this task.

## Task 1 — Restore and admit current R4 ABI 4 predecessor

1. Verify the latest effective R4 status.
2. If red, run the repository-owned corrective controller against the exact
   committed source.
3. Rebuild the global four-class artifacts twice and require byte identity.
4. Run R4 owners, phase, and admission from a clean commit.
5. Load the receipt with the authoritative loader and prove ABI 4 evidence.
6. Append one green R4 status row through the governed updater.
7. Verify chain, source ancestry, clean state, and remote branch equality.
8. Commit and push evidence/status in bounded chunks.

**Acceptance:** effective G0-R4 green, R5-R8 red.  
**Stop:** no R5 training before this acceptance passes.

## Task 2 — Freeze R5/R6 ABIs and validation skeleton

Create strict schemas and canonical types for all ABIs defined in the design.
Register them in `ABI_REGISTRY.md` only after tests exist.

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

## Task 3 — Implement purpose-bound class access

Extend R4 class access into exact R5 worker inputs:

- `TrainInputSnapshot`
- `SelectionInputSnapshot`
- `CalibrationInputSnapshot`

Each is minted from its own capability/authorization and contains no sibling
metadata.

Add process-bound tests that prove:

- train cannot open selection/calibration/frozen-test;
- selection cannot open train/calibration/frozen-test;
- calibration cannot open train/selection/frozen-test;
- no class can discover sibling paths, hashes, refs, counts, or manifests;
- frozen-test mint/open is rejected for R5 and R6;
- path traversal, symlink, junction, and reparse escapes fail.

Commit/push access ABI and tests before any trainer changes.

## Task 4 — Hard-cut obsolete bootstrap training authority

Delete or quarantine from release imports:

- `BootstrapEpisode`;
- bootstrap JSONL loaders;
- `train_proposer`;
- `train_realizer`;
- old artifact-saving entry points where superseded;
- arbitrary validation-path calibration;
- compatibility re-exports.

Split modules by responsibility:

```text
neural_features.py
neural_proposer.py
neural_realizer.py
r5_training.py
r5_selection.py
r5_calibration.py
r5_reproduction.py
```

The control plane and runtime package initializer must remain Torch-light until
a selected activation is explicitly loaded.

Add structural tests for one release path and zero bootstrap reachability.

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
- deterministic bytes across processes/platforms where specified.

## Task 6 — Implement the masked neural proposer

Replace the flat placeholder decoder with separate action and pointer heads.

At every step:

1. construct exact legal candidates;
2. apply masks before softmax and loss;
3. decode only licensed pointers;
4. preserve bounded beam/state/time/RSS limits;
5. emit explicit abstention and model confidence;
6. build canonical Program ABI 2 candidates;
7. pass them to the exact verifier.

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

Publish a committed candidate set transactionally. Do not select a checkpoint in
this task.

## Task 8 — Select the proposer checkpoint

Run a fresh selection-only process with a selection capability.

Freeze:

- metric definitions;
- candidate set;
- accuracy/abstention/robustness/latency/capacity metrics;
- deterministic tie-break;
- selected checkpoint identity.

No optimizer or train snapshot may exist in the process. Commit/push selection
evidence and selected proposer artifact.

## Task 9 — Implement the structured neural realizer

Replace sentence-hash classification with a bounded autoregressive decoder over:

- reviewed language-pack surface units;
- discourse/morphology units;
- exact literal-copy pointers;
- end/failure actions;
- legality masks.

Every result must create a candidate surface and undergo public round-trip
semantic verification.

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

Commit/push selected realizer and selection receipt.

## Task 11 — Calibrate selected models

Freeze both selected checkpoints before calibration.

Use a calibration-only snapshot and actual model scores to produce:

- calibrator parameters;
- nonempty confidence bins;
- ECE and threshold evidence;
- abstention threshold;
- exact proposer/realizer identities;
- canonical Calibration Receipt ABI 1.

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
Emit Reproduction and Weight-Use receipts.

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

Publish transactionally with rollback and crash/retry tests on Linux and Windows.

## Task 14 — Activate exact R5 runtime path

Add the realization owner to `HybridRuntime`.

Release construction:

- requires exact activation ref;
- loads no bootstrap proposer;
- uses selected neural proposer;
- retains exact verifier and R3;
- uses selected neural realizer;
- produces exact RealizationReceipt;
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
- owns runtime lifecycle;
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

## Task 19 — Add API and web adapters

Create thin transport adapters with:

- strict request schemas;
- authentication/authorization hook boundary;
- body/output/time bounds;
- idempotency and cancellation;
- streaming policy only if semantically complete chunks are defined;
- no direct model or semantic-owner imports;
- no fallback responses.

Transport errors remain distinct from semantic cycle results.

## Task 20 — Add evaluation adapter boundary without frozen-test access

The R6 evaluation adapter converts injected cases to CompositionRequests and
records CompositionResults. It has no dataset loader and cannot mint/open
frozen-test capability.

Tests prove R7 is the earliest possible frozen-test owner.

## Task 21 — Prove cross-surface parity

For the same canonical request, CLI/API/web/evaluation adapters must bind the
same:

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

Test process-tree termination, transactional rollback, partial writes,
store/model mismatch, adapter disconnect, repeated idempotency keys, and
Linux/Windows path semantics.

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
R4 green (current ABI 4)
R5 green (neural activation)
R6 green (one composition root)
R7 red (frozen-test evaluation not yet run)
R8 red
```

No implementation begins from this plan until Task 0 and Task 1 are green.
