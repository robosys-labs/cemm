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
`hybrid_mvp/docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md`,
as amended by the higher-priority
`hybrid_mvp/docs/superpowers/specs/2026-08-02-hybrid-semantic-algebra-corrective-replay-amendment.md`.

The amendment, design and detailed replay plans supersede conflicting execution
and status claims in:

- `hybrid_mvp/docs/superpowers/plans/2026-07-29-authoritative-mvp-master-roadmap.md`;
- the July 29 M1-M5 plans;
- `hybrid_mvp/docs/superpowers/plans/2026-07-30-corrective-replay-plan.md`;
- current M1-M4 receipts, checkpoints, calibration and evaluation artifacts.

Those files remain historical evidence until explicitly reclassified. The
R1-R5 donor bundle and the later G0-R6 selective-admission package are evidence
sources only; their installers, delete lists, governing documents, inventories,
authority bundles, runtimes, corpora, checkpoints and receipts must not be
activated or copied wholesale. The later package's internally consistent
archive and algorithms may inform owner work, but its 18-test selector, invalid
coverage matrix, leaky partitions and self-attested phase claims do not satisfy
this plan.

## Dependency graph

```text
G0 governance + forensic inventory + executable validation
 |
 v
R1 Program ABI 2 + Semantic Expression ABI 1 + compiler + one path
 |
 v
R2 reversible evidence + bounded ProposalContext + authentic recursive composition
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
| `phase` | Once after reviewed work changes a declared cross-owner boundary and has integration nodes | Fresh cross-owner integration nodes selected from the dependency manifest; owner nodes are excluded | Always fresh |
| `admission` | Once per G0/R1/.../R8 candidate | One full governed collection, exact active-set execution, deterministic regeneration and clean activation/reload; training/corpus work only where that phase owns it | Always fresh; cached results never admit |

These are runner modes, not three independent validators. The runner resolves
the immutable inventory and literal metadata before execution. DAG prerequisites
and pytest nodes execute at most once within a tier, and owner and phase
diagnostic node sets are disjoint. A task with no changed cross-owner boundary
and no integration nodes runs no empty phase tier. Admission does not nest owner
or phase steps or trust their receipts: one pytest invocation collects the
pinned test root, requires exact equality with the governed collectable set,
deselects inactive nodes and executes the complete active set once fresh. That
single admission re-execution is the only intended cross-tier repeat. Status and
receipt verification never launches a runner.

The external gate runner records:

- command and exact source/input identities;
- predecessor and authority identities;
- exit status plus direct structured pytest counts;
- wall time, peak working set when available, and slowest cases;
- whether the result was fresh or diagnostic-only.

The only public admission loader is
`load_verified_admission_receipt(root, *, phase, expected_status, run_ref=None) -> tuple[GateReceipt, tuple[str, ...]]`. It strictly reconstructs one existing
receipt and every nested identity without executing a gate. The second value is
the sorted canonical repository-relative paths of every exact external evidence
file authenticated by that receipt's path/hash material; directory, glob,
working-tree and unauthenticated-path inference is forbidden. Dry-run and governance verification take one dirty-path snapshot.
Append takes
one pre-append snapshot under the exclusive lock and one post-write snapshot
before success, rolling back on mismatch. These bounded counts are independent
of receipt count. Each check intersects dirty paths with the authenticated set
and rejects every dirty governed path outside it. The loader never queries Git
status. An explicit
`run_ref` selects that run; omitting it is legal only when exactly one eligible
current run exists. Time, mtime and a "latest" pointer never choose authority.
Both green and `externally_blocked` updater transitions call this loader with
`expected_status="passed"` and bind `admission_gate_result_ref` plus the exact
`admission_run_ref`.

Each admission binds the exact clean candidate commit and a
`pre_admission_status_head_ref`. The receipt loader is ledger-agnostic and
validates only canonical receipt
bytes, nested identities and authenticated external evidence; it never rereads
the status chain, invokes Git history authentication or recursively loads a
receipt. The status updater and coalesced governance handler instead perform
consumption checks in one pass over the chain they already authenticated.
Before append they require clean current HEAD/source and current
head/pre-admission-head equality with no prior consumer. After append and during
historical verification they require exactly one row whose
predecessor/source_base/gate/run fields consume the receipt.

No gate runner, corpus scan, trace serializer, model training operation, or
performance sampler is called from the normal `HybridRuntime.process()` path.
Governance, status and receipt-loader control paths remain lightweight and do
not import runtime, model, training or Torch libraries. The stdlib-only test
inventory owner is loaded from its reviewed exact file path, not through the
runtime package initializer.

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
- One runner invocation hashes each canonical input and parses each governance
  artifact once. Owner/phase modes collect only exact selected nodes; admission
  performs one full governed collection, equality check, inactive deselection
  and active execution in one pytest process.
- Performance budgets start as observed baselines. A material unexplained
  regression is investigated; budgets are not relaxed to hide semantic bloat.

### History-preserving admission evidence

Every admission executes against an exact committed, clean candidate source.
Deterministic admission inputs are committed first; the unique run artifact,
phase pointer and consuming status row are committed afterward as evidence.
Receipts never describe an older HEAD plus an open-ended dirty source set.

Every post-anchor status `source_base` is part of the release proof. Referenced
commits must form a monotonic ancestry chain and remain ancestors of the release
HEAD. Once a status row is appended, integration uses only fast-forward or a
history-preserving merge commit. Squash merge, rebase, cherry-pick-only
integration, history filtering and force-push are forbidden when they would
orphan a referenced commit. Production `read_hash_chain(path)` authenticates
post-anchor history from Git and exposes no prior-bytes or prior-receipt bypass.
A future Git-less release verifier may be separately reviewed as a
manifest-pinned verify-only path, but `read_hash_chain` does not accept it and
it is not current admission authority. Root adoption that cannot preserve this
history requires a separately reviewed ledger-closing and new-genesis
migration.

## Detailed plan sequence

1. `2026-07-31-hybrid-mvp-g0-r1-implementation-plan.md`
   - G0 document/status authority, artifact quarantine, test inventory and the
     dependency-aware gate runner.
   - R1 canonical revision/program/proposal/verification/phase/cycle identities,
     Program ABI 2, Semantic Expression ABI 1, total compiler, Verified Meaning
     ABI 1, one public runtime path and R1 activation proof. Later-owner behavior
     remains a typed gap rather than evaluating a raw program.

2. `2026-08-01-hybrid-mvp-r2-composition-verification-plan.md`
   - Written only after G0-R1 admission evidence exists.
   - One source-span coordinate system, bounded immutable ProposalContext,
     recursive multi-root action construction, independent program-to-expression
     proof and expression-grouped ambiguity.

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
- immutable `governance/test_inventory.json`, freezing exactly 59 predecessor
  test files, 632 source-test refs and 743 exact case node IDs with reviewed
  classification/assertion/activation metadata;
- literal per-node `__cemm_test_inventory__` metadata in every later test,
  parsed once by AST without filename/default or live-Git inference;
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

`governance/test_inventory.json` is the single immutable predecessor
inventory. It freezes exactly 59 reviewed test files, 632 source-test refs and
743 exact collected-case node IDs, plus the classification, assertion,
activation and content refs needed to select them without consulting live Git.
`DOCUMENT_AUTHORITY.json` pins its exact path and SHA-256. Its identity and
counts are recomputed directly from the file in routine and bundle verification;
later replay tasks never mutate it.

The 632 count excludes two `test_authority_factory` functions that are
`@pytest.fixture` providers and therefore own no collected case IDs. This
distinction is checked structurally without importing pytest; every included
source ref owns at least one of the 743 exact cases.

Every test introduced after the frozen inventory carries a module-level literal
`__cemm_test_inventory__` mapping with one record per exact pytest node ID,
including parameterized cases. Later parameterized tests declare literal case
IDs; dynamic/generated parameter IDs are forbidden. Each literal record
declares its assertion ref, earliest activation phase, diagnostic role, owner
when applicable, and introducing task. The checker parses every current test
module once with `ast`
and rejects computed metadata, a missing or duplicate node, overlap with the
frozen inventory, and every filename or file-level default inference. No
secondary mutable registry or live-Git lookup participates in routine or bundle
verification.

Every frozen predecessor source test has one approved classification:

- `retained`: its assertion remains valid and declares the earliest replay phase
  whose admitted owners can execute it;
- `rewritten`: one reviewed obligation maps each predecessor case to a non-empty
  conjunctive set of exact successor nodes that together preserve the assertion
  under the hard-cut ABI;
- `historical`: the assertion depended on a retired semantic path and remains
  evidence with a reviewed reason.

The completed baseline audit yields exactly 609 retained, 10 rewritten and 13
historical source tests. A frozen per-source-test AST digest, not the whole-file
blob hash, is the edit boundary. A valid retained assertion may move to a new
exact node ID only through unique, acyclic, assertion-preserving and
phase-monotonic literal supersession metadata; a same-ID body edit fails.
Rewritten originals never execute. Their typed replacement obligations are
deferred before the reviewed replacement phase and must have complete exact-case
successors before pytest starts once due. Deferred is not a fourth
classification.

There is no `future` classification. Owner and phase tiers receive disjoint
exact node selectors and each executing tier starts exactly one pytest process.
Admission supplies the pinned test root plus governed collectable and active
manifests to one fresh pytest process. The plugin rejects any extra, missing or
duplicate collected node before deselecting inactive nodes and executing the
complete eligible union. Admission requires zero collection errors, active
skips, xfails or xpasses. R8 requires every retained frozen case and every
active later case to be active.

## Commit and review discipline

For every implementation task:

1. add the smallest behavioral/corruption test and observe the expected failure;
2. implement the earliest owner only;
3. run the focused owner tier;
4. request contract compliance review;
5. address review findings and rerun;
6. request code-quality/performance review;
7. address findings and rerun;
8. if the task changed a declared cross-owner boundary, run its coalesced phase
   tier exactly once; otherwise record that no phase tier applies;
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
- a programming exception is being converted into a semantic gap;
- integration would detach, rewrite or discard a ledger-referenced commit.

A red receipt is useful evidence. It is never promoted by changing a label.
