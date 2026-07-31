# Hybrid MVP Corrective Replay Master Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `subagent-driven-development` to execute each detailed phase plan task-by-task, with test-first implementation, contract review, code-quality review, and controller verification.

**Goal:** Rebuild the isolated Hybrid MVP into an authentic, independently verifiable six-phase proof without adopting the unsafe R1-R5 donor overlay or treating current M4 artifacts as valid training evidence.

**Architecture:** A selective hard-cut replay proceeds from governance and canonical runtime identities through recursive semantic composition, exact decisions/effects/realization, reviewed data, neural proposal/realization, shared surfaces, authentic evaluation, and clean release proof. Each phase has one content-addressed admission receipt and cannot activate while an ancestor is red or stale.

**Tech Stack:** Python 3.11+, PyTorch, pytest, JSON/JSON Schema, SQLite-backed hybrid persistence, canonical SHA-256 identities.

**Scope:** `hybrid_mvp/` only. Root CEMM remains governed by the root contracts and is not modified or adopted by this replay.

**Working branch/worktree:** `codex/hybrid-mvp-g0-r1` at `C:\dev\cemm\.worktrees\hybrid-mvp-g0-r1`.

---

## Governing decision

The approved design is
`hybrid_mvp/docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md`.

It and the detailed replay plans supersede conflicting execution and status
claims in:

- `hybrid_mvp/docs/superpowers/plans/2026-07-29-authoritative-mvp-master-roadmap.md`;
- the July 29 M1-M5 plans;
- `hybrid_mvp/docs/superpowers/plans/2026-07-30-corrective-replay-plan.md`;
- current M1-M4 receipts, checkpoints, calibration and evaluation artifacts.

Those files remain historical evidence until explicitly reclassified. The
R1-R5 donor bundle is an evidence source only; its installer, delete list,
authority bundle, runtime, corpus, checkpoints and receipts must not be
activated or copied wholesale.

## Dependency graph

```text
G0 governance + forensic inventory + executable validation
 |
 v
R1 canonical identities + receipts + one ABI/path
 |
 v
R2 reversible evidence + bounded ProposalContext + recursive composition
 |
 v
R3 exact decision + proof + effect + learning + response + activation
 |
 v
R4 reviewed contracts + authentic episodes + sealed partitions + external review
 |
 v
R5 neural proposer + neural realizer + selection + calibration + reproduction
 |
 v
R6 one composition root + CLI/API/web/evaluation surfaces
 |
 v
R7 authentic evaluation + per-case evidence + baseline comparison
 |
 v
R8 clean rebuild/retrain + complete DAG + release proof
```

A phase may begin design/test preparation while its predecessor is under review,
but no successor implementation or activation may depend on a red predecessor.

## Three validation tiers, not a gate maze

The replay has exactly three execution tiers:

| Tier | When it runs | Contents | Freshness |
|---|---|---|---|
| `owner` | Every red/green implementation loop | The affected owner's focused tests, corruption tests, static import/source checks | Always fresh; target under 60 seconds |
| `phase` | After a task is green and reviewed | Fresh cross-owner integration tests selected from the dependency manifest; owner tests are not repeated | Always fresh |
| `admission` | Once per G0/R1/.../R8 candidate | Complete declared active suite, deterministic regeneration, clean activation/reload; training/corpus work only where that phase owns it | Always fresh; cached results never admit |

These are runner modes, not three independent validators. A test is invoked at
most once in a tier. Later tiers consume the same structured result schema
rather than re-parsing or re-running an earlier tier for ceremony.

The external gate runner records:

- command and exact source/input identities;
- predecessor and authority identities;
- exit status plus structured pytest/JUnit counts;
- wall time, peak working set when available, and slowest cases;
- whether the result was fresh or diagnostic-only.

No gate runner, corpus scan, trace serializer, model training operation, or
performance sampler is called from the normal `HybridRuntime.process()` path.

### Cost and invalidation policy

- Documentation-only edits do not trigger model training or corpus rebuilding.
- Runtime ABI changes invalidate affected integration and downstream artifacts,
  not unrelated owner tests.
- Corpus compilation runs only when reviewed assertions, compiler, coverage
  contract, alignment owner, or relevant ABI changes.
- Training runs only when admitted train data, feature/model code, training
  configuration, or predecessor checkpoint contract changes.
- Reproduction runs only for selected checkpoint candidates and once fresh at
  R5/R8 admission.
- Clean-checkout activation runs once per phase admission candidate.
- G0-R1 does not cache test results. Later R4-R5 plans may reuse content-matched
  expensive artifact diagnostics, but never for admission.
- Performance budgets start as observed baselines. A material unexplained
  regression is investigated; budgets are not relaxed to hide semantic bloat.

## Detailed plan sequence

1. `2026-07-31-hybrid-mvp-g0-r1-implementation-plan.md`
   - G0 document/status authority, artifact quarantine, test inventory and the
     dependency-aware gate runner.
   - R1 canonical revision/program/proposal/verification/phase/cycle identities,
     one public runtime path, one composition root and R1 activation proof.

2. `2026-08-01-hybrid-mvp-r2-composition-verification-plan.md`
   - Written only after G0-R1 admission evidence exists.
   - One source-span coordinate system, bounded immutable ProposalContext,
     recursive action construction and independent exact reconstruction.

3. `2026-08-02-hybrid-mvp-r3-cognition-activation-plan.md`
   - Written only after R2 admission.
   - Closed decisions, proof, explicit no-effect/effect, typed learning,
     response meaning/equivalence and authentic activation canaries.

4. `2026-08-03-hybrid-mvp-r4-data-partition-plan.md`
   - Written only after R3 admission.
   - Reviewed semantic assertions, total expected-contract compiler, structural
     coverage, authentic aligned episodes, verified negatives, sealed axes and
     independent external review.

5. `2026-08-04-hybrid-mvp-r5-neural-reproduction-plan.md`
   - Written only after R4 technical admission and external review.
   - Context/action neural proposal, production neural realization, train-only
     fitting, held-out selection/calibration, frozen test opening and
     deterministic reproduction.

6. `2026-08-05-hybrid-mvp-r6-r8-product-release-plan.md`
   - Written only after R5 admission.
   - Shared product composition, thin surfaces, authentic evaluation, measured
     limitations, clean release proof and explicit root non-adoption.

Dates identify plan ordering, not promised completion dates.

## Phase admission contracts

### G0

Required evidence:

- a Hybrid MVP document authority/supersession map;
- truthful append-only replay status with G0 pending/green and R1-R8 red;
- quarantined prior receipts/checkpoints without deletion;
- every predecessor test classified as retained, rewritten, or historical;
  retained tests also declare their earliest activation phase;
- collection failures, skips, xfails and unexpected deselections represented as
  structured failures;
- the three-tier external gate runner and content dependency manifest;
- baseline collection and known-red M4 threshold evidence.

G0 does not claim a functioning release runtime.

### R1

Required evidence:

- one canonical owner for each active cross-phase type;
- complete `RevisionPin`, program, proposal, verification, phase receipt and
  cycle serialization/identity with corruption rejection;
- `CycleResult` as the only cycle result and no compatibility `.kernel` view;
- `HybridRuntime.process()` as the only public cognitive path;
- no signature inspection, result-shape adaptation, evaluation runtime factory,
  or fixture release owner;
- portable governed-source identity across LF/CRLF checkouts;
- all declared G0-R1 active tests green and all downstream retained tests
  bound to a reviewed later activation phase.

R1 may truthfully end at an R2-owned typed semantic gap; it must not fake a full
cognitive success.

### R2

Required evidence:

- exact character spans from one form resolver;
- bounded context without authority-wide target inventories;
- all five operators, four modes and twelve action types;
- multiple applications, at least three roots and nested proposition depth
  within configured bounds;
- references, scopes, variables, literal pointers and transitions;
- independent verifier reconstruction and adversarial corruption tests;
- multilingual/unseen-synonym tests and no ref-name lexicalization.

### R3

Required evidence:

- typed read-only/denied/pending/failed/committed decisions;
- explicit no-effect/effect receipt every cycle;
- proof-bearing mutations through one effect gateway;
- complete typed learning plans bound to one query and successful commit;
- response meaning followed by exact realization equivalence;
- authentic persisted canaries that cannot be promoted by caller labels.

### R4

Required evidence:

- independently reviewed semantic assertion inputs;
- a total expected-cycle compiler that never invokes PROPOSE;
- every configured coverage minimum and maximum;
- every eligible surface/context/dialogue lineage represented;
- hard negatives with real mutations and authentic earliest-owner rejection;
- independent holdout axes and process-separated dataset access;
- an externally verified exact-set review manifest.

### R5

Required evidence:

- neural proposal over legal context-local actions/pointers;
- explicit abstention examples and model-derived confidence;
- candidate-order randomization and train-only learned preprocessing;
- separate train, selection, calibration and frozen-test access;
- selected checkpoint executing through the public composition root;
- production neural realization from ResponseMeaning and literal pointers;
- zero-weight/ablation evidence and byte-reproducible selected artifacts.

### R6-R8

Required evidence:

- one production composition root for CLI/API/web/evaluation;
- no surface semantic routing or canned normal answers;
- authentic per-case full-cycle evaluation with non-vacuous denominators;
- measured limitations;
- clean rebuild, retrain, regeneration, activation, full suite and bundle check;
- an explicit statement that root adoption remains a separate reviewed change.

## Test lifecycle

Every predecessor test has one approved classification:

- `retained`: its assertion remains valid and declares the earliest replay phase
  whose admitted owners can execute it;
- `rewritten`: a named active successor preserves the assertion under the
  hard-cut ABI;
- `historical`: the assertion depended on a retired semantic path and remains
  evidence with a reviewed reason.

There is no `future` classification. At each admission, all predecessor source
tests are inventory-checked, while the complete retained suite whose activation
phase is at or before the candidate phase is collected and executed. Admission
requires zero unclassified tests, collection errors, skips, xfails or xpasses.
R8 requires every retained test to be active.

## Commit and review discipline

For every implementation task:

1. add the smallest behavioral/corruption test and observe the expected failure;
2. implement the earliest owner only;
3. run the focused owner tier;
4. request contract compliance review;
5. address review findings and rerun;
6. request code-quality/performance review;
7. address findings and rerun;
8. run the applicable coalesced phase tier;
9. commit one coherent task.

Do not combine unrelated phase work, copy donor files wholesale, or weaken a
threshold/gate to make a phrase pass.

## Stop conditions

Stop implementation and record a red or externally blocked receipt when:

- the earliest owner cannot be identified from an exact stage trace;
- a change would require modifying root semantics rather than the isolated MVP;
- semantic review or adoption authority is missing;
- a proposed compatibility path would create a second runtime/ABI;
- a performance optimization would weaken independent verification;
- corpus/test access cannot prove separation;
- a programming exception is being converted into a semantic gap.

A red receipt is useful evidence. It is never promoted by changing a label.
