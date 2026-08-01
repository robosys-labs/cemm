# Hybrid MVP Corrective Replay Admission Design

**Status:** approved for implementation
**Date:** 2026-07-31
**Scope:** `hybrid_mvp/` only
**Reviewed base:** `5f8688b8bf4591563692a8d133097a14feeff8ff`
**Donor evidence:** `cemm_hybrid_mvp_r1_r5_consolidated_replay_patch`

## 1. Decision

Repair the Hybrid MVP through a selective, evidence-gated hard-cut replay on the
landed checkout. Do not apply the R1–R5 donor overlay, preserve its claimed
implementation status, or train further from the current M4 artifacts.

The donor is an evidence and algorithm source. Every adopted behavior must be
re-expressed under one admitted Hybrid MVP contract, introduced by a failing
test, and independently verified in the landed repository.

The replay is decomposed into separately admissible units:

```text
G0 governance, forensic inventory and executable validation
→ R1 canonical identities, phase/cycle receipts and one runtime path
→ R2 reversible evidence, bounded context, recursive composition and verification
→ R3 exact decision, proof, effect, learning, response and activation
→ R4 reviewed semantic contracts, authentic episodes and sealed partitions
→ R5 neural proposal/realization, selection, calibration and reproduction
→ R6 shared product composition and surfaces
→ R7 authentic evaluation and baseline comparison
→ R8 clean release proof
```

No successor is implemented against a red predecessor. A red gate is an
investigation result, not permission to weaken or skip the gate.

## 2. Product proof and non-claims

The Hybrid MVP must prove, inside its isolated subtree, that:

1. reversible evidence and bounded context can support recursive five-operator
   candidate programs;
2. exact owners can independently verify meaning, proof, epistemic placement,
   effects and response equivalence;
3. learned proposal and realization materially depend on current evidence,
   context and trained parameters;
4. supported-domain performance can be measured without proposer-owned gold,
   lineage leakage, fixture owners, alternate runtimes or vacuous denominators.

The Hybrid MVP is not the root runtime, an open-domain assistant, or authority to
replace root Stage 0–22, root ABIs, root authority, or root realization
contracts. A successful Hybrid MVP release and root adoption are separate
decisions. Root adoption requires a later reviewed migration design and every
root authority, ABI, anti-bloat, deterministic-generation, regression and
realization-preservation gate.

## 3. Why neither existing implementation can be the baseline

### 3.1 Landed checkout

The landed checkout has duplicate public types and paths, including separate
program, proposal, verification and cycle result classes. Its public runtime
uses signature inspection and result-shape adaptation. Episode generation
selects the first bootstrap candidate as gold, hard negatives can be metadata
clones, calibration reads episode labels, and evaluation has a separate release
factory.

Existing milestone receipts therefore remain historical evidence. Their
`verified` labels do not admit R1–R5.

### 3.2 R1–R5 donor

The donor contains useful contracts and development algorithms, but its core
R1–R3 files retain the known structural defects. Its installer validates only a
curated subset, its CLI composition is incomplete after overlay, its R4 corpus
violates its own coverage minimums and leakage rules, and its R5 models do not
implement the required public-runtime proposer and production realizer.

The following donor operations are forbidden:

- applying `apply_overlay.py` to the authoritative checkout;
- honoring `DELETE_PATHS.txt` before all callers have migrated;
- using skip-validation, force-base, force-branch or dirty-tree overrides;
- activating donor-generated corpus, checkpoints or receipts;
- copying donor authority, forms, runtime or ABI files unchanged.

## 4. Authority and status model

G0 creates a Hybrid MVP document authority and supersession map. It states:

- hybrid contracts govern only `hybrid_mvp/`;
- root contracts continue to govern the root runtime;
- this design and its reviewed implementation plans supersede conflicting
  execution/status claims in the July 29 plans and the draft July 30 plan;
- earlier plans remain historical intent and acceptance evidence;
- the truthful initial replay state is G0 pending and R1–R8 red;
- generated artifacts never become governing documents or semantic authority.

Status is append-only and dependency-pinned. A phase receipt names its direct
source, authority, ABI, configuration, store, test and predecessor identities.
Changing an ancestor invalidates every descendant without deleting historical
evidence. Green and `externally_blocked` updater transitions both require a
verified passed admission and bind `admission_gate_result_ref` plus the exact
`admission_run_ref`; red and initial pending records bind neither.

Each admission executes against an exact committed, clean candidate source.
Deterministic admission inputs are committed first; the unique run, phase
pointer and consuming status row are committed afterward. A receipt never
describes an older HEAD plus an open-ended dirty source set.

Every post-anchor ledger `source_base` is durable release evidence. Once such a
record exists, its commit must remain a monotonic ancestor of the next
`source_base` and of the final release commit. Integration therefore uses a
fast-forward or history-preserving merge commit. Rebase, squash merge,
cherry-pick-only integration, history filtering and force-push are forbidden
when they would detach or remove a referenced commit. The production
`read_hash_chain(path)` path requires Git to authenticate every post-anchor
suffix and accepts no caller-supplied prior bytes or receipt bypass. A future
Git-less release verifier may be designed as a separate, manifest-pinned,
verify-only path; it is not accepted by `read_hash_chain`, is not current
admission authority and cannot authorize source-history rewriting.

## 5. Runtime architecture

### 5.1 One type, owner and path

Each cross-phase artifact has one canonical owner. `HybridRuntime.process()` is
the only public cognitive path. CLI, API, web, corpus replay and evaluation use
the same composition root. No compatibility result view, signature inspection,
`propose_and_verify` shortcut, evaluation-only runtime or fixture release owner
survives admission.

### 5.2 Six exact ownership boundaries

```text
ORIENT → PROPOSE → VERIFY → EVALUATE → EFFECT → REALIZE
```

- ORIENT consumes one exact evidence packet and performs bounded indexed
  retrieval.
- PROPOSE consumes one immutable proposal context and emits a content-addressed
  candidate batch or abstention.
- VERIFY requires that exact context and independently recomputes legality,
  source coverage, graph structure and revisions. It never repairs.
- EVALUATE consumes one selected verified program and emits one closed typed
  decision.
- EFFECT always emits a content-addressed effect or no-effect receipt and is the
  only mutation/adapter owner.
- REALIZE builds exact response meaning and accepts a surface only after
  independent semantic equivalence.

Unexpected programming exceptions propagate through development and activation
boundaries. Expected semantic limitations produce typed gap receipts at the
earliest owner.

### 5.3 Complete content identity

Evidence, orientation, proposal context, actions, candidates, candidate batch,
program, verification, decision, effect/no-effect, response, realization,
phase receipts and cycle results derive identity from their complete semantic
content. Constructors and deserializers reject mismatched identities.

Cycle identity is finalized from the completed result rather than allocated
from the input alone. Every phase receipt binds exact input/output refs,
revision pins, disposition, rejection codes and budget use.

## 6. R1–R3 corrective boundaries

### 6.1 R1 admission

R1 removes duplicate public ABI classes and alternate paths only after a caller
inventory and migration tests exist. It adds complete `RevisionPin`
serialization, content-addressed phase/cycle identity, deterministic standard
validation and a full active-test inventory. No deletion may create an import or
collection failure.

### 6.2 R2 admission

R2 uses one coordinate system: exact source character spans. `FormResolver` is
the only segmentation owner. The immutable context exposes current grounded
designations, contributions, frames, references, scopes, variables,
transitions, residuals and revision pin; it exposes no authority-wide target
inventory.

Composition is bounded but genuinely recursive. It must positively construct:

- all five operators and four modes;
- all twelve switch actions;
- multiple applications and at least three roots within configured bounds;
- proposition-valued nesting through configured maximum depth;
- reference, polarity, modality, tense/aspect, attribution, projected variable
  and transition structures.

Literal values and exact source pointers survive every transformation. Legal
action identities include their dynamic pointer/root identity. VERIFY requires
the exact context and reconstructs residual criticality, assignments, state
dimension/value compatibility, roots, reachability, parent cardinality,
acyclicity and depth independently.

### 6.3 R3 admission

R3 implements typed decisions without lexical dispatch. Read-only, denied,
pending, failed and committed outcomes remain distinct. Every cycle has an
explicit no-effect/effect receipt.

The learning plan contains the exact contract, source query, goal, capability,
commit operator, literal, expected target kinds, answer contract, provenance,
revision and expiry. Conversation cannot authorize publication.

Activation canaries are persisted products of actual runtime cycles. A canary
binds the exact evidence, context, proposal, verification, decision, effect,
response, realization and source/owner identities. A caller cannot activate a
profile by supplying `passed: true` and arbitrary artifact refs.

## 7. R4 data architecture

R4 has independent owners in this order:

```text
reviewed semantic assertions
→ total ExpectedCycleContract compiler
→ structural sufficiency matrix
→ real R2 surface alignment
→ authentic six-phase episodes
→ verified semantic/environment negatives
→ independent sealed partition axes
→ externally verified review manifest
```

The compiler never invokes PROPOSE and has no default-to-designation rule.
Unsupported assertion kinds fail. Expected contracts and observed runtime
outputs remain separate fields.

The coverage gate enforces every configured minimum and maximum, including
operator share, modes, actions, scopes, topology/depth/root counts,
transitions, ambiguity, conflict, unknowns, dialogues and construction-family
diversity. It emits the governed coverage matrix; nonzero marginals are not a
substitute.

Every eligible surface/context produces an episode, not only the first surface
per contract. Dialogue turns point to their actual dialogue lineage. Hard
negatives alter semantic or environmental content and retain only rejection
codes returned by the authentic earliest owner.

General, lexical, semantic-target, topology, dialogue, mutation and realization
axes are sealed independently. Exact strings, normalized templates, programs,
targets, mutations, dialogue descendants and response families obey the
declared holdout boundary. Training occurs in a separate process with a read
allowlist and access manifest.

Machine generation cannot self-approve semantic review. R4 release remains red
until an independently verified review manifest binds the exact corpus and
approved descendants.

## 8. R5 neural architecture

The proposal model consumes immutable ProposalContext candidate/action sets,
reversible surface/form evidence and opaque semantic IDs. It emits distributions
over legal switch actions and dynamic pointers. It does not select from a
hard-coded table of completed programs.

Training includes explicit abstention examples and authentic rejected
mutations. Candidate order is deterministically randomized. Vocabulary and all
learned preprocessing are fit from train only.

Dataset access is process-separated:

1. train is readable during fitting;
2. checkpoint validation is readable only for selection;
3. calibration is a distinct held-out prediction split;
4. frozen test opens only after a content-addressed selection and calibration
   receipt exists;
5. access logs and ancestor hashes are part of the run receipt.

Evaluation reports every holdout axis and required slice. Runtime integration is
mandatory: the selected proposer checkpoint must execute through the public
composition root.

The production realizer decodes from exact ResponseMeaning under reviewed
language constraints and typed literal pointers. A development response-surface
selector may be retained as a clearly named test instrument, but it cannot
satisfy R5, M4 or release activation.

## 9. R6–R8 and M5 relationship

R6 creates one production composition root and makes CLI, API, web and
evaluation thin consumers. Surfaces contain no semantic routing or canned normal
answers.

R7 evaluates one authentic public-runtime cycle per declared case after
anti-bypass self-tests. Accepted illegal programs, swallowed exceptions,
fixture owners, missing artifacts, stale identities, unverified effects,
semantic realization mismatches and empty required denominators are failures.
Per-case records remain in every denominator.

R8 rebuilds and retrains from clean inputs, validates the complete artifact DAG,
runs the full active suite and reproducible bundle verification, and records
limitations. Only then may the isolated Hybrid MVP satisfy its M5 release goal.
Application or adoption into the root repository is not automatic.

## 10. Validation and installer contract

The standard validation command must work without private environment state,
extra `PYTHONPATH`, skip flags or parser assumptions about quiet pytest output.
It establishes a writable isolated temp/cache directory and reports structured
test results rather than parsing human progress text.

Each phase requires four evidence categories:

1. focused red/green behavioral tests;
2. corruption and anti-bypass tests;
3. complete active-suite collection and execution;
4. clean-checkout activation/reload with deterministic artifact regeneration.

These are evidence categories inside exactly three runner modes, never four
gate invocations. One external runner coalesces them into owner, phase and
admission tiers and deduplicates shared prerequisites. After selector expansion,
each pytest node and artifact step runs at most once within a tier. Owner mode
runs only affected-owner and corruption nodes. Phase mode runs only declared
cross-owner integration nodes, and its pytest node set is disjoint from the
owner node set. A task with no changed cross-owner boundary and no integration
nodes does not run an empty ceremonial phase tier.

Admission is one independent fresh execution of the complete active node set.
Its deliberate re-execution of earlier diagnostic nodes is the only intended
cross-tier repeat: admission never nests or invokes owner or phase test steps as
separate prerequisites, and it never treats their receipts as admission
authority. One admission invocation performs active-suite collection and
execution once. Status and receipt verification validate existing bytes and
identities only; they never launch pytest, artifact generation or another gate.

The categories are dependency-aware rather than redundantly serial. Local
red/green work runs only the affected owner tests and static checks. Applicable
phase integration runs once after its owners are green and reviewed. Corpus
rebuild, model training, reproduction and full clean-checkout gates run only
when one of their content-addressed ancestors changes, and always run fresh for
phase admission and release. An unchanged cached receipt can accelerate
development diagnostics, but cannot satisfy a fresh admission or release gate.

Admission receipts have one strict external verification seam:
`load_verified_admission_receipt(root, *, phase, expected_status, run_ref=None) -> tuple[GateReceipt, tuple[str, ...]]`. It deserializes and recomputes every
step, gate and run identity; verifies the phase, admission tier, freshness,
derived status and the applicable source/environment/input identities; and
performs no gate work. The loader is deliberately ledger-agnostic: it never
reads replay_status.jsonl, invokes Git history authentication or recursively
loads another receipt. It verifies the receipt's canonical bytes, nested refs,
stored source/environment/input identities and external evidence only.

The lifecycle coordinator performs consumption checks over the one status chain
it has already authenticated. Before append, the updater requires a clean
current HEAD equal to source_ref, a current status head equal to
pre_admission_status_head_ref and no prior consumer. After append and during
historical verification, one pass over the authenticated records requires
exactly one consuming row whose predecessor/source_base/gate/run fields equal
the receipt. The coalesced governance handler uses the same one-pass relation.

The returned path tuple is every sorted canonical repository-relative external
evidence path authenticated by the receipt's path/hash material. The loader
never queries Git status or substitutes a directory, glob, working-tree scan or
unauthenticated path. Dry-run and governance verification take one dirty-path snapshot.
Append takes
one pre-append snapshot under the exclusive lock and one post-write snapshot
before success, rolling back on mismatch. These bounded counts are independent
of receipt count. Each check intersects dirty paths with the authenticated set
and rejects every dirty governed path outside it. An explicit `run_ref` selects exactly that run.
Without one, verification succeeds only when exactly one eligible current run
exists; clocks, modification times and a "latest" pointer never select
authority. Receipt-validation failures are typed, while unexpected programming
exceptions propagate. The status updater passes `expected_status="passed"` for
both green and `externally_blocked` transitions.

Gate execution records wall time, peak memory and the slowest test/artifact
steps. A gate whose cost grows without a declared semantic-data increase is a
performance regression to investigate. Validation instrumentation uses bounded
counters and optional receipts; it does not add authority scans, serialized
traces or synchronous training work to the normal `HybridRuntime.process()`
path. Governance, status and receipt-loader control paths remain lightweight
and do not import runtime, model, training or Torch libraries. They load the
stdlib-only inventory owner by its reviewed exact file path rather than through
the runtime package initializer. Within one runner
invocation, canonical paths are hashed once, manifests and ledgers are parsed
once, and resolved dependencies are memoized in memory. Owner and phase tiers
collect only their exact selected nodes. Admission performs one fresh active-set
collection and execution in the same pytest invocation; it does not pre-run a
second full collection gate.

Test governance has two governed evidence sources, validated inside the
existing coalesced governance step rather than by another gate.
`governance/test_inventory.json` freezes the reviewed predecessor sets: exactly
59 test files, 634 source-test refs and 743 exact collected-case node IDs,
together with classifications, activation phases, semantic assertion refs and
its recomputable inventory ref. `DOCUMENT_AUTHORITY.json` pins its exact path
and SHA-256. It is reviewed once and never mutated by later replay tasks.
The reviewed classification is 611 retained, 10 rewritten and 13 historical;
those counts are audit results, not targets obtained by relabelling cases.

Every frozen source test also binds a canonical digest of its own decorators,
literal parameter IDs, signature and body. A whole-file blob ref is provenance,
not the edit boundary. Unrelated imports, helpers, metadata and new tests may
change without mutating a frozen node. A frozen assertion that remains valid
may move only to a new exact node ID with literal, assertion-preserving,
phase-monotonic supersession metadata. Same-ID body mutation, ambiguous or
cyclic supersession and incomplete parameter-case coverage fail closed.

A rewritten predecessor is evidence-only and is never executable. Its typed
replacement obligation is deferred before its reviewed replacement phase and
must be completely satisfied by exact successor cases at or after that phase,
before pytest starts. `historical` predecessors are never executable. Deferred
is a computed lifecycle state, not a fourth classification.

Every test introduced after that frozen set carries a module-level literal
`__cemm_test_inventory__` mapping with one metadata record per exact pytest node
ID, including every parameterized case. Later parameterized tests declare
literal case IDs; dynamic/generated parameter IDs are forbidden. Each record
states its assertion ref, activation phase, diagnostic role, owner when
applicable, and introducing replay task. The AST checker parses each current
test module once, without importing
it, and rejects computed metadata, filename/default inference, duplicate or
missing nodes and overlap with the frozen case set. Routine and bundle
verification load the immutable inventory and literal AST metadata directly;
they do not query live Git or maintain a secondary mutable registry.

All executing tiers pass exact node selectors to one pytest process. Owner and
phase sets are disjoint; admission independently executes the complete eligible
union of frozen cases and later literal-metadata cases once. Mixed-phase files
may be import-checked, but are never selected or classified as whole files.
There are zero active skips, xfails or xpasses at an admission or release gate.

## 11. Execution and review discipline

Implementation occurs in an isolated `codex/` branch/worktree after user review
of this design and its detailed plan. Each implementation task follows test-first
red/green/refactor and receives two independent reviews:

1. contract/spec compliance;
2. code quality, failure behavior and regression risk.

No two implementation agents edit the same owner concurrently. Read-only
audits and independent review may run in parallel. The controller reruns each
task's focused proof and, only when the task changes a declared cross-owner
boundary, the applicable phase gate instead of trusting an agent report.

## 12. Admission outcomes

A phase ends in exactly one state:

- **green:** every declared artifact and gate is present and independently
  verified;
- **red:** one or more gates failed, with the earliest owner and evidence
  recorded;
- **externally blocked:** technical gates are green but an external review,
  baseline artifact, reference hardware or adoption approval is absent.

There is no partial-green profile, profile-label promotion, inherited pass
count, or release claim based on a future installer run.
