# R5/R6 Plan Readiness Review

**Date:** 2026-08-22  
**Reviewed branch:** `agent/r4-task4-batch-publisher-20260816`  
**Reviewed commit:** `5c704399b417414cf91211d6d9a9a8c8ce84767c`  
**Scope:** `hybrid_mvp/` only  
**Decision:** **PLAN GO after Task 0; SOURCE IMPLEMENTATION NO-GO until current R4 ABI-4 is green**

## 1. Executive finding

The repository has a sound R5 hard-cut foundation, but it does **not** yet have
an executable R5 neural-activation plan or an R6 composition/surface plan.
Starting implementation from the existing foundation plan would leave essential
owners unspecified and would risk promoting placeholder neural paths into the
release runtime.

The current Git and governance state also contains a hard predecessor blocker:
the effective replay ledger has R4 red after invalidating the historical R4
green record. R5 cannot train, select, calibrate, activate, or admit from a red
R4 predecessor. A fresh, current-source, Build Receipt ABI 4 R4 admission is the
first mandatory implementation prerequisite.

This review therefore introduces:

1. an R4-green precondition;
2. a complete R5 neural-activation architecture;
3. a separate R6 one-root composition and surface architecture;
4. exact data-class isolation through train, selection, calibration, and
   frozen-test capabilities;
5. hard removal of obsolete bootstrap training/runtime paths before activation;
6. genuine neural proposal and realization requirements, replacing placeholder
   encodings and sentence-hash classification;
7. deterministic training, selection, calibration, reproduction, ablation,
   activation, and admission receipts;
8. Linux/Windows transactional, timeout, path-safety, and crash-recovery gates;
9. explicit ownership of all 25 deferred R5 assertions; and
10. a task graph that keeps R7 frozen-test evaluation unopened.

## 2. Evidence examined

The review covered the active governance ledger, document authority map, R5
foundation design and plan, R5 disposition source, validation graph, ABI
registry, architecture, runtime, bootstrap composition root, CLI, model and
training implementations, R4 partition access boundary, and current R5
foundation tests.

### 2.1 Current status

The latest replay record invalidates R4 and leaves R4-R8 red. The earlier R4
green admission is historical evidence only. No R5 implementation may use that
historical receipt as current predecessor authority.

### 2.2 Existing R5 authority

The only active R5 design and plan are for the **hard-cut foundation**. They
deliberately state:

- R5 remains red;
- R5 admission is unavailable;
- only five foundation owners exist;
- `R5-Neural-Activation` is future work;
- train, selection, calibration, and frozen-test are future authorization
  vocabulary.

This foundation is a valid predecessor, not an activation roadmap.

### 2.3 Missing R6 authority

There is no active R6 governing design, implementation plan, validation phase,
admission graph, or exact composition-root ABI. The master plan contains only a
high-level R6 outcome. That is insufficient for implementation.

### 2.4 Current neural implementation risks

The current source contains useful components, but it is not an admissible
release implementation without correction:

- `training.py` still exposes bootstrap episode loaders and bootstrap training
  beside authenticated R4 release training;
- the proposal unit-pointer encoder returns an all-zero tensor;
- the proposal vocabulary collapses dynamic pointers and does not prove learned
  pointer selection independently of action-type selection;
- proposal training shown in the legacy path computes ordinary cross-entropy
  without proving the exact legal-action mask was applied before loss;
- the realizer maps an entire surface string to one of a small number of
  SHA-256-derived classes, so it does not generate the surface;
- calibration confidence is currently derived from fixed epistemic labels
  rather than model scores;
- calibration accepts an arbitrary filesystem path instead of a purpose-bound
  authenticated calibration capability;
- reproduction reports tensor reproduction from model-identity equality rather
  than independently comparing canonical tensor identity;
- the public runtime always terminates at
  `contract:r5:realize_surface`;
- the current composition root rejects neural and release profiles and loads
  `BootstrapProposer` for development;
- the CLI emits raw diagnostic cycle JSON and is not a production surface.

These are not small tuning issues. They define the required R5/R6 hard cuts.

## 3. Intended end state

### R5 end state

R5 is green only when an admitted activation bundle provides:

- a genuinely neural proposer over legal context-local action and pointer
  choices;
- model-derived confidence and explicit abstention;
- a genuinely neural, pointer-aware realizer from exact `ResponseMeaning`;
- exact semantic round-trip verification;
- strict four-class data authorization;
- train-only fitting, selection-only checkpoint choice, calibration-only
  confidence calibration, and no frozen-test access;
- reproducible selected proposer and realizer artifacts;
- proof that normal release outputs depend on loaded weights;
- no bootstrap, static, fixture, canned-response, or compatibility fallback;
- one current-source R5 admission receipt and green ledger record.

### R6 end state

R6 is green only when exactly one production composition root serves every
surface:

```text
CLI
API
web
evaluation adapter
    -> one typed CompositionRequest
    -> one admitted R5 runtime
    -> one typed CompositionResult
```

Surface adapters may translate transport concerns only. They cannot classify
meaning, choose owners, call models directly, inspect internal ref spelling,
invent responses, or access frozen-test data. R7 remains the sole frozen-test
evaluation owner.

## 4. Corrections required before implementation

### C1 — Make current R4 green a machine-enforced prerequisite

The first implementation task must load and verify one current R4 admission
receipt whose source is an ancestor of the implementation head and whose
evidence uses the exact ABI 4 global four-class artifact graph. If R4 is red,
missing, historical-only, dirty, or ABI 3, stop.

### C2 — Promote a new design and plan before source changes

The foundation documents remain governing for the hard cut. The new R5/R6
design and plan must be added to `DOCUMENT_AUTHORITY.json` and to the exact
governance-test constants in one reviewed commit before implementation code.

### C3 — Separate R5 and R6 admission

R5 owns models, data capabilities, training, selection, calibration,
reproduction, activation, and semantic realization. R6 owns composition and
transport surfaces. R6 cannot hide unfinished R5 behavior.

### C4 — Replace placeholder model contracts

The proposer must have separate bounded heads for structural action type and
each licensed dynamic pointer. The realizer must decode reviewed surface units
and literal-copy pointers; sentence hashing is forbidden. Both paths must expose
weight-use and zero-weight ablation evidence.

### C5 — Remove duplicate bootstrap authority

Before a release checkpoint can be selected, obsolete bootstrap dataset
loaders, old training entry points, `BootstrapProposer` release reachability,
and compatibility re-exports must be removed or isolated as non-importable
historical tooling. There must be one release training path and one runtime
proposal owner.

### C6 — Make data separation physical and purpose-bound

A worker must receive one class capability only. It must not receive sibling
paths, hashes, refs, counts, manifests, or discovery APIs. Selection and
calibration are not aliases for validation. Frozen test stays unavailable until
R7.

### C7 — Add a real R5 activation graph

The R5 validation graph needs distinct owners for:

- data capability integrity;
- feature schema;
- proposal model;
- realization model;
- training;
- selection;
- calibration;
- reproduction;
- weight-use/ablation;
- runtime activation;
- activation canaries;
- artifact integrity;
- structural hard cut.

The current five foundation owners remain predecessor owners.

### C8 — Add an exact R6 graph

R6 needs owners for:

- composition request/result ABI;
- composition root;
- CLI adapter;
- API adapter;
- web adapter;
- evaluation adapter boundary;
- parity;
- cancellation/deadline/idempotency;
- operational budgets;
- structural hard cut.

### C9 — Keep R7 authority closed

Neither R5 nor R6 may open, enumerate, hash, count, or log the frozen-test class.
R6 evaluation integration is an adapter contract only; authentic frozen-test
evaluation begins at R7.

### C10 — Bind deterministic and operational evidence

All artifacts and receipts must be canonical, content-addressed, size-bounded,
safe-tensor-only, source-pinned, authority-pinned, config-pinned, and published
transactionally. Training and reproduction run outside the request path.
Linux and Windows must prove process-tree timeout, rollback, path traversal,
symlink/reparse/junction rejection, and clean retry.

## 5. Requirement matrix

| Requirement | Current state | Required correction |
|---|---|---|
| Current R4 predecessor | Red | Fresh ABI-4 R4 admission |
| R5 foundation | Implemented, red by design | Preserve as predecessor |
| R5 activation design | Missing | Add governing design |
| R5 activation plan | Missing | Add task-by-task plan |
| R6 design/plan | Missing | Add exact one-root design and plan |
| Train access | Authenticated train batch exists | Preserve one-class isolation |
| Selection access | Vocabulary only | Add exact capability and owner |
| Calibration access | Arbitrary path API exists | Replace with authenticated class snapshot |
| Frozen-test access | Future vocabulary | Keep unopened until R7 |
| Proposer | Neural skeleton exists | Genuine masked action + pointer decoder |
| Realizer | Hash-classification placeholder | Genuine structured pointer-aware decoder |
| Confidence | Fixed semantic-label mapping | Model score + selected calibrator |
| Reproduction | Partial | Independent tensor/receipt byte identity |
| Runtime | Stops at R5 gap | Activate exact realizer owner only from admitted bundle |
| Composition root | R3 development bootstrap | New R6 production root |
| CLI/API/web parity | Missing | Typed adapters over same root |
| R5 admission | Unavailable | Add only after all deferred owners are satisfied |
| R6 admission | No graph | Add after parity and operational gates |

## 6. Final decision

**Do not begin R5 neural implementation from the current foundation plan.**
First adopt the accompanying design and implementation plan, then satisfy the
fresh R4 admission prerequisite. The corrected task graph is implementation
ready only after those two steps are green.

## 7. Final efficiency and anti-bloat refinement

The final review found that correctness alone was insufficient: the draft
still permitted excess schemas, modules, artifact retention, and hot-path
verification. The following corrections are now binding:

1. **Consolidated contracts.** R5 uses one purpose-snapshot ABI and one
   discriminated lifecycle-receipt ABI rather than separate near-duplicate
   snapshot/receipt codecs. R6 uses one discriminated evidence receipt for
   adapter, parity, and operational evidence.
2. **Minimal implementation footprint.** R5 has at most five active owner
   modules; there is no module-per-receipt layout, compatibility re-export,
   wrapper-only layer, or speculative accelerator abstraction.
3. **No artifact-history inflation.** Non-selected checkpoint weights remain
   in bounded scratch/CI storage and are deleted after selection and
   reproduction. Git receives only selected artifacts that fit the reviewed
   repository-size budget plus bounded manifests and receipts.
4. **Hot-path work is single-pass.** Models, manifests, safe tensors, and
   authority pins are verified once when the composition root loads.
   Context features and pointer tables are encoded once per request and
   reused; immutable refs are computed once; phases exchange typed objects,
   not JSON.
5. **Bounded inference.** Proposal uses vectorized pointer heads, cached
   context encodings, bounded beam/top-k, and no materialization of masked
   candidates. Realization batches a bounded set of neural candidates for
   round-trip verification and has no template fallback.
6. **Budgets precede architecture.** Task 2 freezes combined checkpoint
   bytes, parameter count, startup, RSS, p50/p95 stage latency, beam/decode
   bounds, round-trip candidate count, trace/report size, artifact count,
   dependency count, and import-time ceilings before model code begins.
   Implementation may improve but cannot raise those ceilings.
7. **Dependency restraint.** R5 is CPU-only and uses the existing PyTorch,
   safetensors, JSON, and validation stack. A new runtime dependency,
   accelerator backend, cache, streaming protocol, or server framework
   requires separate measured justification.
8. **One HTTP surface.** API and web share one HTTP transport adapter. The
   initial R6 increment does not implement streaming. CLI and evaluation
   remain thin codecs over the same composition root.
9. **Bounded evidence and tests.** Receipts retain refs, aggregates, and
   typed failures rather than duplicated datasets, tensors, traces, or
   per-step logits. Deferred assertions should use literal parameter IDs
   and conjunctive successor reuse rather than one file/class per case.

These corrections reduce the planned ABI count from sixteen to ten and
prevent offline governance rigor from becoming request-time overhead.
