# Hybrid MVP Completion Critical Path Implementation Plan

> **Superseded execution evidence:** This document is retained for forensic
> history only. It cannot authorize current work or phase status. Current status
> is derived from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).
> The August 29 R4.1 data/supervision amendment supersedes conflicting
> partition, feasibility, gold and realization instructions.

> **Historical supersession notice (2026-08-13):** This plan's paths, status,
> and execution instructions are retained as historical evidence, not current
> routing. Status is derived only from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).
> Continue with the plan selected by `docs/DOCUMENT_AUTHORITY.json`.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the isolated Hybrid MVP as an authentic, independently verifiable six-phase semantic system, from the current red R1 candidate through clean R8 release proof, without treating construction programs as meaning or reusing invalid M4/R5 descendants.

**Architecture:** Preserve the admitted G0 governance chain, finish and admit the Program ABI 2 / Semantic Expression ABI 1 hard cut, then advance one dependency-ordered replay phase at a time. Each phase changes the earliest semantic owner, uses focused owner tests during development, one cross-owner phase suite only when a boundary changes, and one fresh full admission run against a clean committed candidate.

**Tech Stack:** Python 3.11+, pytest, JSON/JSON Schema Draft 2020-12, SQLite, PyTorch/safetensors, canonical SHA-256 identities, CLI/API/web surfaces.

---

## 1. Authoritative starting point

Work only in:

```text
C:\dev\cemm\.worktrees\hybrid-mvp-g0-r1\hybrid_mvp
branch: codex/hybrid-mvp-g0-r1
```

The governing order is:

1. `AGENTS.md`
2. `docs/DOCUMENT_AUTHORITY.json`
3. `docs/superpowers/specs/2026-08-02-hybrid-semantic-algebra-corrective-replay-amendment.md`
4. `docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md`
5. `docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md`
6. this execution plan and the phase-specific plans it requires

The root CEMM runtime is outside scope. Root adoption remains a separate reviewed decision after R8.

### Current evidence, not aspiration

- G0 is the only green replay phase. Its ledger row consumes `run:2b63b31aba576be0e61bf6bd` and must remain in preserved Git ancestry.
- R1 remains red. The worktree contains a large uncommitted R1 candidate and therefore cannot produce an admission receipt yet.
- Program ABI 2, Proposal Context ABI 1, Semantic Expression ABI 1, Compilation Proof ABI 1, Source Coverage ABI 2, Proposal Result ABI 2, Verification Batch ABI 2, Verified Meaning ABI 1, Phase Receipt ABI 2 and Cycle Result ABI 2 have candidate implementations and focused tests, but are not release authority until R1 admission.
- The production duplicate `propositions.py` owner is deleted; legacy proposition/runtime fixtures are test-only.
- The `program-verifier` and `cycle-result` owner tiers have passed diagnostic runs. The `runtime-path` exact selector passes 93/93 directly, but its authoritative runner is red because `tests/test_episode_generation_hard_cut.py::canonical_runtime` requests `tmp_path_factory` while the governed runner intentionally disables pytest's tempdir plugin.
- The current M4 corpus, checkpoints, calibration, 78-case evaluation and the proposed 100-epoch rerun are quarantined Program ABI 1 descendants. They cannot answer whether the repaired architecture is competitive.
- R2 through R8 have no fresh admission evidence and remain red.

## 2. Non-negotiable decisions

- `SemanticSwitchProgram` is derivation lineage. `SemanticExpression` is canonical semantic content. `VerifiedMeaning` is the only input to EVALUATE.
- Exactly five persistent operators remain: designation, type, relation, state and event.
- No surface string, regex, internal ref spelling or legacy stage number selects semantic behavior.
- No donor installer, donor authority bundle, donor corpus, donor checkpoint, donor receipt or donor deletion list is activated wholesale.
- No new release gate is added for a local test-fixture defect. Repair the fixture at its owner.
- No training, epoch tuning or threshold tuning occurs before R4 reviewed expression gold and partitions are admitted.
- No phase is marked green from focused tests. Admission requires a clean committed candidate and one fresh admission receipt.
- No squash, rebase, force-push or cherry-pick-only integration may orphan a ledger `source_base` commit.

## 3. Validation policy and performance budget

Keep exactly three validation tiers:

| Tier | Purpose | Execution rule |
|---|---|---|
| owner | Red/green loop for one owner | Exact nodes only; target under 60 seconds |
| phase | Changed cross-owner boundary | Integration nodes only; never replay owner nodes |
| admission | Phase authority | One full governed collection and active execution against a clean commit |

Additional rules:

- `HybridRuntime.process()` imports or invokes no governance, corpus, training, evaluation or gate code.
- R4/R5 may cache content-matched expensive diagnostics, but admission always re-executes fresh.
- Corpus compilation runs only when reviewed assertions, compiler, coverage/alignment owner or relevant ABI changes.
- Training runs only when admitted training data, model code, preprocessing, config or predecessor checkpoint changes.
- Reproduction runs only for selected candidates and R5/R8 admission.
- Record wall time, peak RSS and slowest cases; investigate semantic search or activation regressions instead of raising bounds.

## 4. Phase/file ownership map

| Phase | Primary production owners | Generated/reviewed outputs |
|---|---|---|
| R1 | `programs.py`, `proposal_context.py`, `expressions.py`, `coverage.py`, `proposal.py`, `verifier.py`, `cycle.py`, `runtime.py`, `bootstrap.py` | R1 validation receipt and green ledger row |
| R2 | `forms.py`, `grounding.py`, `affordances.py`, `contributions.py`, `proposal_context.py`, `proposal.py`, `programs.py`, `expressions.py`, `verifier.py`, authority/frame data | recursive composition matrices and R2 receipt |
| R3 | `situation.py`, `query.py`, `epistemics.py`, `state.py`, `capabilities.py`, `proof.py`, `effects.py`, `learning.py`, `dialogue.py`, `response.py`, `realization.py`, `runtime.py`, `bootstrap.py`, `persistence.py` | activation canaries and R3 receipt |
| R4 | `episodes.py`, `partitions.py`, corpus schemas, `scripts/build_episodes.py`, partition/review tools | reviewed contracts, authentic episodes, sealed partitions, external review manifest |
| R5 | `model.py`, `training.py`, neural realization owner, train/calibrate/reproduce scripts | selected proposer/realizer, calibration and reproducibility receipts |
| R6 | `bootstrap.py`, `cli.py`, new API/web composition adapters | one shared composition root and thin surfaces |
| R7 | `evaluation.py`, `scripts/evaluate_cemm.py`, baseline adapter | authentic per-case evaluation and limitations report |
| R8 | validation/reproduction/package scripts and release manifest | clean rebuild/retrain/activation/bundle proof |

## 5. Critical path

```text
R1 clean hard-cut admission
  -> R2 authentic recursive composition
  -> R3 cognition/effect/learning/realization
  -> R4 reviewed expression gold and sealed data
  -> R5 neural proposal and realization
  -> R6 shared product surfaces
  -> R7 authentic competitive evaluation
  -> R8 clean release reproduction
```

Documentation and failing-test preparation may overlap review time. Production activation and generated descendants may not cross a red predecessor.

---

### Task 1: Stop the R1 loop and produce one reviewable candidate

**Files:**

- Modify: `tests/test_episode_generation_hard_cut.py`
- Verify: `configs/validation_gates.json`
- Verify: `scripts/pytest_gate_runner.py`
- Verify: all current R1 production/test changes

- [ ] **Step 1: Repair the earliest fixture owner without expanding the runner**

Replace the module-scoped `canonical_runtime(tmp_path_factory)` fixture with a module-scoped standard-library `TemporaryDirectory` fixture. The governed runner already pins `TMP`, `TEMP` and `TMPDIR` inside its run directory, so this remains isolated and avoids adding a second temp-factory contract.

```python
import tempfile


@pytest.fixture(scope="module")
def canonical_runtime():
    with tempfile.TemporaryDirectory(prefix="cemm-episode-hard-cut-") as root:
        runtime = load_runtime(
            ROOT,
            profile="development",
            store_path=Path(root) / "stores",
        )
        try:
            yield runtime
        finally:
            runtime.stores.close()
```

- [ ] **Step 2: Prove the exact runner failure is gone**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'src').Path
python scripts\validate_mvp.py --tier owner --phase R1 --owner runtime-path
```

Expected: `disposition="passed"`, 93 selected nodes, zero skips/errors/failures.

- [ ] **Step 3: Run the single R1 phase boundary suite**

```powershell
python scripts\validate_mvp.py --tier phase --phase R1
```

Expected: only `governance`, `source_compile` and `r1_phase_tests`; no owner node repeats.

- [ ] **Step 4: Review the full R1 diff by ownership**

```powershell
git diff --check
python -m ruff check scripts src tests
python scripts\check_test_inventory.py --phase R1 --source-only
python -m pytest --collect-only -q
```

Confirm:

- one production `SemanticSwitchProgram` owner and one `CycleResult` owner;
- no production `propositions.py`;
- no `process_evidence`, `propose_and_verify`, fixture release owners, result adapters or signature inspection;
- no Program ABI 1 evaluation/training path silently re-enabled;
- every changed frozen assertion uses a new-ID successor rather than same-ID mutation;
- `.lineage-recovery/` remains intact.

- [ ] **Step 5: Commit the deterministic R1 candidate before admission**

Stage by reviewed owner group and commit without squashing G0 ancestry:

```powershell
git add configs docs scripts src tests .lineage-recovery
git commit -m "refactor: complete canonical hybrid replay R1 candidate"
git status --short
```

Expected: clean worktree. Do not include regenerated pytest, Ruff, Hypothesis, bytecode or temporary directories.

### Task 2: Admit R1 and close its governance record

**Files:**

- Generate: `artifacts/validation/runs/<run-ref>.json`
- Append: `governance/replay_status.jsonl`

- [ ] **Step 1: Run one fresh R1 admission**

```powershell
$r1 = python scripts\validate_mvp.py --tier admission --phase R1 | ConvertFrom-Json
if ($r1.disposition -ne 'passed') { throw "R1 admission failed: $($r1.error_code)" }
$r1.run_ref
```

Expected admission DAG: governance, source compile, authority link, one active pytest suite, R1 structure and fresh SQLite activation. No training or corpus build.

- [ ] **Step 2: Inspect the exact receipt**

Verify the source commit, authority generation, active/collectable identities, 777 active tests, zero skips/xfails/xpasses, structural scan, fresh-store activation, wall time, peak RSS and slowest cases.

- [ ] **Step 3: Append R1 green using the exact run**

```powershell
$candidate = python scripts\update_replay_status.py --phase R1 --status green --run-ref $r1.run_ref --dry-run | ConvertFrom-Json
python scripts\update_replay_status.py --phase R1 --status green --run-ref $r1.run_ref --expect-record-ref $candidate.record_ref --append
python scripts\update_replay_status.py --verify-chain
```

- [ ] **Step 4: Commit admission evidence**

```powershell
git add artifacts\validation governance\replay_status.jsonl
git commit -m "chore: admit canonical hybrid replay R1"
```

Exit state: `G0=green`, `R1=green`, `R2-R8=red` with monotonic ancestry.

### Task 3: Specify and implement R2 recursive semantic composition

**Files:**

- Create: `docs/superpowers/plans/2026-08-04-hybrid-mvp-r2-composition-verification-plan.md`
- Modify: `data/authority/` reviewed frame/role/link sources and generator
- Modify: `src/cemm_authoritative_hybrid/forms.py`
- Modify: `src/cemm_authoritative_hybrid/grounding.py`
- Modify: `src/cemm_authoritative_hybrid/affordances.py`
- Modify: `src/cemm_authoritative_hybrid/contributions.py`
- Modify: `src/cemm_authoritative_hybrid/proposal_context.py`
- Modify: `src/cemm_authoritative_hybrid/proposal.py`
- Modify: `src/cemm_authoritative_hybrid/programs.py`
- Modify: `src/cemm_authoritative_hybrid/expressions.py`
- Modify: `src/cemm_authoritative_hybrid/verifier.py`
- Create: focused R2 structural/composition/corruption tests

- [ ] **Step 1: Freeze R2 acceptance matrices before implementation**

The checked-in cases must cover all five operators, all four modes, all twelve Program ABI 2 actions, exact character-span ownership, multiple applications, at least three roots, proposition-valued roles, nested depth, ordered and commutative links, references, scopes, binders/query variables, literal pointers and state-transition proposals.

Add multilingual and unseen-synonym pairs proving that new reviewed designations inherit semantic affordances without form-pack regeneration. Add negative cases for ref-name lexicalization, authority-wide scans, orphan nodes, duplicate parents, cycles, depth overflow, invalid frame fallback and contribution-bound overflow.

- [ ] **Step 2: Make ProposalContext the complete bounded input**

ORIENT resolves evidence once and builds indexed slots for only current-cycle designations, contributions, application frames, references, scopes, links, variables, literals, transitions and residuals. No proposer or verifier retokenizes text or enumerates all atoms.

- [ ] **Step 3: Replace the R1 bootstrap stub with a bounded complete composer**

`BootstrapProposer.propose(context)` must construct legal multi-application Program ABI 2 candidates using context-local pointers and the frozen action schemas. It is a deterministic correctness oracle/data-construction tool, not the product model and not semantic gold authority.

- [ ] **Step 4: Admit the registered R2 compiler actions**

Remove R1-only rejection for nested applications, links, scopes, binders and transitions only after each action has total compilation, exact source accounting and adversarial tests. Compilation never fills an omitted role or repairs a candidate.

- [ ] **Step 5: Make verifier reconstruction independent**

The verifier reconstructs source criticality, action/pointer legality, role ownership, value/dimension compatibility, reachability, root membership, parent cardinality, acyclicity, depth and exact program-to-expression proof. It groups accepted candidates by `expression_ref`, not `program_ref`.

- [ ] **Step 6: Run and admit R2**

```powershell
python scripts\validate_mvp.py --tier owner --phase R2 --owner composition
python scripts\validate_mvp.py --tier owner --phase R2 --owner compiler-verifier
python scripts\validate_mvp.py --tier phase --phase R2
git commit -am "feat: implement authentic recursive semantic composition"
python scripts\validate_mvp.py --tier admission --phase R2
```

Append R2 green only from the exact passed run. Exit state: real unseen-synonym and recursive cases reach `VerifiedMeaning`; no EVALUATE claim yet.

### Task 4: Implement R3 cognition, effects, learning and realization

**Files:**

- Create: `docs/superpowers/plans/2026-08-04-hybrid-mvp-r3-cognition-activation-plan.md`
- Create/modify: `src/cemm_authoritative_hybrid/situation.py`
- Modify: `query.py`, `epistemics.py`, `state.py`, `capabilities.py`, `proof.py`
- Modify: `effects.py`, `learning.py`, `dialogue.py`, `response.py`, `realization.py`
- Modify: `runtime.py`, `cycle.py`, `bootstrap.py`, `persistence.py`
- Create: R3 decision/effect/learning/realization/restart tests

- [ ] **Step 1: Define one closed Decision ABI**

`SemanticEvaluator.evaluate(meaning: VerifiedMeaning, situation: SituationContext) -> Decision` returns one of read-only query, denied, clarification, transition preview, operation, learning, admission or no-op semantics with explicit supported/unknown/partial/ambiguous/conflict state. It never accepts a program.

- [ ] **Step 2: Require an effect or no-effect receipt every cycle**

Only `EffectGateway` mutates stores or invokes adapters. Receipts bind decision, `verified_meaning_ref`, expression, revision and idempotency key. Query, simulation, denial, ambiguity and failure emit authenticated no-effect receipts.

- [ ] **Step 3: Complete Learning Plan ABI 2**

Plans bind exact verified meaning, source query, goal, capability, commit operator, target-kind contract, answer contract, provenance, permission, expiry and revision. Lookup is read-only; teaching, directive, event claim and reviewed acquisition remain distinct. A designation commit occurs only after the successful EFFECT receipt.

- [ ] **Step 4: Build response meaning before wording**

`ResponseBuilder` consumes decision, proof, blockers, effect/no-effect receipt and dialogue obligation. `RealizationVerifier` sends generated surface back through the same evidence/composition/compile/verify path and compares canonical expression plus situated qualifiers. Only then may focus be committed.

- [ ] **Step 5: Extend the one runtime path through all six phases**

Keep `HybridRuntime.process()` as the sole public path. Remove the R1 `contract:r3:evaluate` stop only when EVALUATE, EFFECT and REALIZE owners are all activated together and Cycle Result ABI 2 invariants cover their artifacts.

- [ ] **Step 6: Prove persisted activation**

Use fresh SQLite canaries for query/no-effect, claim admission, state transition, capability denial, reviewed synonym learning, restart, stale-revision rejection, idempotent effect replay and realization equivalence.

- [ ] **Step 7: Admit R3**

Run focused owners, one cross-owner phase suite and one clean R3 admission. Exit state: deterministic development profile completes authentic six-phase cycles; neural release profiles remain fail-closed.

### Task 5: Build R4 reviewed expression gold and sealed partitions

**Files:**

- Create: `docs/superpowers/plans/2026-08-04-hybrid-mvp-r4-data-partition-plan.md`
- Create: strict reviewed semantic-contract and coverage schemas
- Modify: `src/cemm_authoritative_hybrid/episodes.py`
- Modify: `src/cemm_authoritative_hybrid/partitions.py`
- Replace fail-closed owner in `scripts/build_episodes.py`
- Modify: scenario/partition/review generators
- Regenerate: Program ABI 2 / Expression ABI 1 episode and partition artifacts

- [ ] **Step 1: Author semantic assertions independently of PROPOSE**

Reviewed inputs name canonical expressions, situated context, expected decision/effect/response contracts and eligible surfaces. Bootstrap or neural output cannot write or approve these inputs.

- [ ] **Step 2: Implement a total expected-cycle compiler**

Compile reviewed assertions directly to expected canonical expressions and cycle contracts without invoking the proposer. Separately compile canonical derivation targets when needed for model supervision.

- [ ] **Step 3: Generate authentic episodes through the public runtime**

Episodes retain evidence, ProposalContext, legal/rejected programs, compiled expressions, proof, `VerifiedMeaning`, decision, effect/no-effect, response meaning, realization receipt, revisions and provenance. Diagnostic R1 episodes remain quarantined.

- [ ] **Step 4: Enforce structural sufficiency and maxima**

Coverage gates include every operator/mode/action, nesting/root/reference/scope/binder/link/transition axis, eligible language/context/dialogue lineage, verified negatives and configured upper bounds. Empty denominators fail.

- [ ] **Step 5: Seal partitions by independent axes**

Split train, selection, calibration and frozen test by semantic template, designation/synonym, surface form, participant/context and structural composition axes. Dataset access is process-separated; train code cannot open frozen test.

- [ ] **Step 6: Obtain an external exact-set review manifest**

The manifest binds every reviewed input/output hash, reviewer identity/policy and accepted/rejected set. R4 technical admission may be `externally_blocked` until this exact review exists; it may not be self-attested green.

- [ ] **Step 7: Admit R4**

Exit state: content-addressed reviewed Expression ABI 1 gold and sealed partitions exist; all Program ABI 1 corpora are excluded from training and release.

### Task 6: Train and select R5 neural proposal and realization

**Files:**

- Create: `docs/superpowers/plans/2026-08-04-hybrid-mvp-r5-neural-reproduction-plan.md`
- Modify: `src/cemm_authoritative_hybrid/model.py`
- Modify: `src/cemm_authoritative_hybrid/training.py`
- Modify: neural realizer owner in `realization.py`
- Modify: `scripts/train_proposer.py`, `train_realizer.py`, `calibrate_models.py`, `reproduce_models.py`
- Replace: quarantined checkpoints/calibration/evaluation descendants

- [ ] **Step 1: Train only on admitted R4 train partitions**

Proposal targets are context-local Program ABI 2 actions/pointers plus explicit abstention. Realization targets are surfaces conditioned on Response Meaning ABI 2 and licensed literals. Learned preprocessing fits train only.

- [ ] **Step 2: Make confidence genuinely model-derived**

Randomize candidate order during construction, calibrate on the sealed calibration set and preserve ambiguous alternatives until the verified expression margin is sufficient. Do not use surface heuristics or expected operators at inference.

- [ ] **Step 3: Select without opening frozen test**

Use train for fitting, selection for checkpoint choice and calibration only for thresholds. Freeze the selected config/checkpoint identities before the test partition is opened once.

- [ ] **Step 4: Run required ablations**

Compare selected weights against zero-weight/randomized controls and deterministic bootstrap behavior. A model that does not materially affect legal candidate ranking or realization is not a neural success.

- [ ] **Step 5: Reproduce selected artifacts byte-for-byte**

Pin dependencies, seeds, data refs, action ABI, authority generation, configs and device policy. Reproduction must rebuild the selected safetensors, metadata and calibration identities.

- [ ] **Step 6: Admit R5**

The 60-versus-100 epoch choice is made from preregistered selection curves and overfit diagnostics, never from frozen-test or legacy 78-case scores. Exit state: release profile loads the selected proposer and realizer through `load_runtime` and passes model-dependence canaries.

### Task 7: Expose R6 through one production composition root

**Files:**

- Create: `docs/superpowers/plans/2026-08-04-hybrid-mvp-r6-r8-product-release-plan.md`
- Modify: `bootstrap.py`, `cli.py`, `__main__.py`
- Create: thin API server and web adapter modules/tests
- Modify: `scripts/run_demo.py`, evaluation caller

- [ ] **Step 1: Freeze one request/response contract around `CycleResult`**

CLI, API, web and evaluator call the same `load_runtime(...).process(...)` composition. Surfaces serialize semantic status, response surface, gap/proof/effect summary and optional trace; they do not classify intent or choose operators.

- [ ] **Step 2: Keep review authority authenticated and separate**

Review/acquisition controls remain disabled unless the server advertises the reviewed acquisition capability and verifies the same typed authorization used by core learning.

- [ ] **Step 3: Prove parity and restart behavior**

The same inputs/session state produce the same semantic cycle across CLI, API and web. Test network errors, empty authorized surface rejection, accessibility, concurrent sessions and persisted restart.

- [ ] **Step 4: Admit R6**

Exit state: there is one product runtime and no canned normal answers, UI semantic routing or alternate evaluator bootstrap.

### Task 8: Run R7 authentic competitive evaluation

**Files:**

- Modify: `src/cemm_authoritative_hybrid/evaluation.py`
- Modify: `scripts/evaluate_cemm.py`
- Create: baseline adapter and per-case evidence schema
- Generate: new content-addressed evaluation report

- [ ] **Step 1: Preregister metrics and denominators**

Report separately: exact derivation, canonical expression, coverage, operator, decision, effect/no-effect, realization equivalence, abstention precision/recall, end-to-end semantic success, latency and memory. Every case retains earliest divergent owner and exact artifacts.

- [ ] **Step 2: Evaluate the selected frozen R5 artifacts once**

All cases run through the public R6 composition root. No expected label is available to the runtime, no fixture owner participates and no empty required denominator is accepted.

- [ ] **Step 3: Compare against the declared small-LLM baseline**

Use the same reviewed contracts, splits, scoring and resource envelope. Record uncertainty and limitations; do not rewrite gold or tune thresholds after seeing frozen-test results.

- [ ] **Step 4: Diagnose failures by earliest owner**

Classify form, designation, affordance, composition, compile, verify, evaluate, effect or realization failures. Any repair invalidates affected downstream artifacts and requires a new selected model/evaluation identity.

- [ ] **Step 5: Admit R7**

Exit state: the competitive claim is supported by authentic per-case evidence, or the report truthfully records that the MVP did not meet the preregistered target.

### Task 9: Produce R8 clean release proof

**Files:**

- Modify: release validation/reproduction/package scripts
- Create: release manifest and clean-install verification instructions
- Generate: R8 admission receipt and final limitations statement

- [ ] **Step 1: Rebuild from a clean history-preserving checkout**

Install pinned dependencies, link authority, create fresh stores, regenerate R4 data, retrain/reproduce R5 selected artifacts, activate R6 surfaces and rerun R7 evaluation from reviewed sources.

- [ ] **Step 2: Run the complete release DAG once**

Require full governed collection equality, zero skips/xfails/xpasses, all ABI/authority/corpus/model/store hashes, deterministic generator double-run, realization preservation matrix, corruption tests, full suite and package integrity.

- [ ] **Step 3: Verify operational bounds**

Measure normal-cycle latency, peak memory, designation/affordance/search counts, graph depth, retrieval closure and operation re-entry. No normal cycle scans all atoms or invokes validation/training.

- [ ] **Step 4: Admit R8 and preserve evidence ancestry**

Append the exact green R8 run, verify the entire ledger/receipt DAG and create a release commit/tag without rewriting any referenced source commit.

- [ ] **Step 5: State the adoption boundary**

The release manifest must say that the Hybrid MVP proof is complete inside `hybrid_mvp/`; repository-root adoption requires a separate authority-map, ABI migration, ledger-genesis and integration review.

## 6. Completion definition

The Hybrid MVP is fully complete only when all are true:

- effective replay status is G0 and R1-R8 green, with any external-review block resolved by exact evidence;
- one semantic brain and one production composition root serve every surface;
- programs, expressions and situated verified meanings have distinct exact identities;
- all five operators and recursive structures work on reviewed multilingual/unseen-synonym cases;
- deterministic six-phase cognition, proof, effects, learning and realization survive fresh SQLite restart;
- reviewed R4 expression gold and partitions are independent of proposal output;
- selected R5 neural proposer/realizer are model-dependent, calibrated and reproducible;
- R7 evaluation is authentic, non-vacuous and per-case traceable;
- R8 clean rebuild/retrain/regeneration/activation/package proof passes with no compatibility path, skip, xfail, empty surface or unreviewed descendant;
- root adoption remains explicitly unperformed.

## 7. Immediate next action

Execute Task 1 only. Do not start R2 implementation until the R1 admission row is green and committed. After R1 admission, write the detailed R2 plan from the admitted APIs and observed cost profile, then execute it under this critical path.
