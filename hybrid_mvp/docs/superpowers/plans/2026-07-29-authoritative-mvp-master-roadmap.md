# Authoritative Hybrid MVP Master Roadmap Implementation Plan

> **Superseded execution evidence:** This document is retained for forensic
> history only. It cannot authorize current work or phase status. Current status
> is derived from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).
> The August 29 R4.1 data/supervision amendment supersedes conflicting
> partition, feasibility, gold and realization instructions.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a reliable, trainable, six-phase authoritative hybrid CEMM MVP that hard-cuts from the legacy runtime and empirically tests domain competitiveness with a small LLM.

**Architecture:** One runtime executes `ORIENT → PROPOSE → VERIFY → EVALUATE → EFFECT → REALIZE`. Neural models propose recursive `SemanticSwitchProgram` structure and constrained language; exact components own identity, legality, epistemics, proof, persistence, effects, and output equivalence.

**Tech Stack:** Python 3.13, PyTorch, safetensors, SQLite, canonical JSON/JSONL, pytest, Hypothesis, FastAPI, vanilla browser assets, HTTPX, reproducible benchmark scripts.

---

## Governing source

Read before implementation:

1. `docs/superpowers/specs/2026-07-29-authoritative-mvp-completion-design.md`
2. this master roadmap;
3. the active milestone plan;
4. current repository code and tests as evidence only.

The confirmed completion design overrides historical documents and tests. No old runtime behavior survives solely for compatibility.

## Non-negotiable execution rules

- Exactly five persistent operators exist: designation, type, relation, state, event.
- Stage 0–22, stage-number assertions, and `disabled_by_milestone` are forbidden in active code and release artifacts.
- `BootstrapProposer` is permitted only in isolation tests, corpus construction, and debugging. The delivered CLI/API/web runtime uses `NeuralSwitchProposer`.
- No raw text, regex, phrase, language ID, or internal-ref spelling may choose a semantic operator, role, program, effect, or response meaning.
- Every source unit is consumed once or retained as one typed residual.
- Every failed/unresolved cycle emits a typed `GapReceipt`; no failure becomes generic clarification when a more exact status exists.
- Every world/external effect passes through `EffectGateway`; verified output alone may enter semantic focus.
- No normal cycle scans an entire authority, world, episode, or training store.
- Model artifacts are safetensors plus verified canonical metadata and manifests. Legacy `.pt` loading is deleted, not wrapped.
- SQLite is the reference persistent backend; the in-memory backend is test-only.
- No milestone retains a legacy test just to preserve obsolete architecture. Rewrite the semantic assertion under the new contract or delete it.
- A milestone that changes authority, action encoding, model input/output, or corpus partitions retrains the development artifact before neural integration tests.
- Final release gates contain zero skips, xfails, xpasses, fallback paths, compatibility adapters, or unverified surfaces.

## Stable interface map

| Ownership | File | Stable public types/services |
|---|---|---|
| ABI/configuration | `src/cemm_authoritative_hybrid/config.py` | `ABIRegistry`, `RuntimeConfig` |
| Canonical identity | `src/cemm_authoritative_hybrid/canonical.py` | canonical bytes, SHA-256, stable refs |
| Artifact identity | `src/cemm_authoritative_hybrid/artifacts.py` | `ModelMetadata`, manifests, safetensors loading and fingerprinting |
| Six-phase artifacts | `src/cemm_authoritative_hybrid/cycle.py` | `SemanticMode`, `CycleStatus`, `Orientation`, `PhaseReceipt`, `KernelCycleResult`, final `CycleResult` |
| Runtime orchestration | `src/cemm_authoritative_hybrid/runtime.py` | `HybridRuntime` and six phase owner protocols |
| Gaps | `src/cemm_authoritative_hybrid/gaps.py` | `GapReceipt`, `GapClassifier` |
| Authority | `src/cemm_authoritative_hybrid/authority.py` | `AuthorityBundle`, `LinkedAuthority`, `AuthorityLinker` |
| Form evidence | `src/cemm_authoritative_hybrid/forms.py` | `EvidenceItem`, `EvidencePacket`, `FormUnit`, `FormHypothesis`, `FormLattice`, `FormResolver` |
| Grounding | `src/cemm_authoritative_hybrid/grounding.py` | `DesignationCandidate`, `ReferenceRequirement`, `Grounder` |
| Affordances | `src/cemm_authoritative_hybrid/affordances.py` | `AffordanceProfile`, `SemanticAffordanceIndex` |
| Contributions | `src/cemm_authoritative_hybrid/contributions.py` | `SemanticContribution`, `ContributionExpander` |
| Program ABI | `src/cemm_authoritative_hybrid/programs.py` | `ProgramAction`, `SourceAssignment`, `SemanticSwitchProgram`, graph/scope/transition types |
| Proposal | `src/cemm_authoritative_hybrid/proposal.py` | `ProposalModel`, `BootstrapProposer`, `ProposalResult` |
| Neural proposal | `src/cemm_authoritative_hybrid/model.py` | `NeuralSwitchProposer`, encoders, constrained decoder |
| Verification | `src/cemm_authoritative_hybrid/verifier.py` | `ExactProgramVerifier`, `VerificationResult`, typed errors |
| Coverage | `src/cemm_authoritative_hybrid/coverage.py` | `CoverageReceipt`, `CoverageVerifier`, residual/assignment types |
| Persistence | `src/cemm_authoritative_hybrid/persistence.py` | `SemanticStores`, `SQLiteSemanticStore`, test-only memory backend |
| Query/proof | `src/cemm_authoritative_hybrid/query.py` | `QueryStructure`, `QueryResult`, `SemanticDescription`, `SelectiveQueryEngine` |
| Epistemics | `src/cemm_authoritative_hybrid/epistemics.py` | `ClaimOccurrence`, `EpistemicPlacement`, `AdmissionDecision` |
| State/transitions | `src/cemm_authoritative_hybrid/state.py` | `StateAssertion`, `TransitionPreview`, `TransitionEngine` |
| Effects | `src/cemm_authoritative_hybrid/effects.py` | `EffectGateway`, operation/effect plans and receipts |
| Learning | `src/cemm_authoritative_hybrid/learning.py` | `LearningPlan`, `ReviewedAcquisitionPlan`, `ReviewerAuthorization`, `LearningCoordinator`, acquisition policy |
| Dialogue | `src/cemm_authoritative_hybrid/dialogue.py` | `Obligation`, `VerifiedSemanticFocus`, `GoalArbiter` |
| Response meaning | `src/cemm_authoritative_hybrid/response.py` | `ResponseMeaning`, `ResponseBuilder` |
| Realization | `src/cemm_authoritative_hybrid/realization.py` | `NeuralConstrainedRealizer`, `SafeRealizer`, `RealizationVerifier` |
| Episodes/data | `src/cemm_authoritative_hybrid/episodes.py` | `SemanticEpisode`, validation and serialization |
| Training | `src/cemm_authoritative_hybrid/training.py` | proposal/realization trainers and receipts |
| Evaluation | `src/cemm_authoritative_hybrid/evaluation.py` | semantic, gap, safety, performance, and comparison reports |
| Reviewer authentication | `src/cemm_authoritative_hybrid/auth.py` | `ReviewerAssertion`, `ReviewerAuthenticator`, replay-protected authorization |
| API | `src/cemm_authoritative_hybrid/api.py` | four typed HTTP endpoints over `HybridRuntime` |

Later plans use these names exactly. Renaming requires updating this map and every downstream plan before implementation continues.

## Requirement coverage

| Confirmed design requirement | Owning milestone tasks |
|---|---|
| Hard cutover, five operators, no Stage 0–22 | M1 Tasks 1 and 6; M5 Task 5 |
| Safe model/data/authority identity | M1 Tasks 2–4; M4 Task 3 |
| Six phases, phase receipts, gap receipts | M1 Tasks 5–6 |
| Linked authority and structural grounding/self projection | M1 Task 4; M2 Tasks 1–2 |
| Universal switch programs and typed coverage | M2 Tasks 3–4 |
| Neural proposal with exact masks | M2 Tasks 5–6 |
| Query, proof, epistemics, state, transition, effects | M3 Tasks 1–3 |
| Learning, focus, obligations | M3 Tasks 4–5 |
| Reviewed acquisition and authenticated review surfaces | M3 Task 4; M5 Tasks 1–3 |
| Neural realization and equivalence verification | M3 Task 6 |
| Real-world gap/failure behavior | M1 Task 5; M3 Task 7; M4 Task 4 |
| Crash-consistent persistence | M1 Task 3; M3 Task 7 |
| Corpus, leakage control, proposal/realization training | M4 Tasks 1–3 |
| Qwen comparison and performance | M4 Tasks 5–6 |
| CLI/API/web/cross-language proof | M5 Tasks 1–3 |
| Clean verification, deletion, hard cutover | M5 Tasks 4–6 |

## Milestone index and dependency order

```text
M1 Constitutional six-phase kernel
  → M2 Universal hybrid proposal and verifier
    → M3 Cognition, learning, persistence, realization
      → M4 Training, failure coverage, competitive evaluation
        → M5 Surfaces, reliable bundle, hard cutover
```

Plans:

1. `docs/superpowers/plans/2026-07-29-m1-six-phase-kernel.md`
2. `docs/superpowers/plans/2026-07-29-m2-hybrid-proposal-verifier.md`
3. `docs/superpowers/plans/2026-07-29-m3-cognition-learning-realization.md`
4. `docs/superpowers/plans/2026-07-29-m4-training-failure-competitive-evaluation.md`
5. `docs/superpowers/plans/2026-07-29-m5-surfaces-reliable-cutover.md`

Each milestone ends in a clean acceptance commit. Do not begin the next milestone while a current gate is red or a future owner is hidden behind permissive behavior.

## Master Task 1: Create the isolated implementation worktree

**Files:**
- Verify: `docs/superpowers/specs/2026-07-29-authoritative-mvp-completion-design.md`
- Verify: all five milestone plans listed above

- [ ] **Step 1: Resolve the confirmed planning commit**

```powershell
$planningCommit = git rev-parse codex/authoritative-mvp-completion
git show --no-patch --oneline $planningCommit
```

Expected: the printed commit contains this five-milestone roadmap.

- [ ] **Step 2: Create the implementation worktree**

Invoke the `using-git-worktrees` skill, then run:

```powershell
git worktree add C:\Users\Son\Downloads\cemm_authoritative_hybrid_mvp_implementation -b codex/authoritative-mvp-implementation $planningCommit
Set-Location C:\Users\Son\Downloads\cemm_authoritative_hybrid_mvp_implementation
git status --short
```

Expected: a clean new worktree. Do not restore `artifacts/graph_action_ranker.pt`; the unsafe legacy loader is removed in Milestone 1.

- [ ] **Step 3: Record the historical test baseline as evidence only**

```powershell
git show 60ffedf:README.md | Select-String '52'
git show --stat --oneline 60ffedf
```

Expected: historical evidence is readable without restoring or loading the unsafe checkpoint. It is not an acceptance requirement or runtime input.

## Master Task 2: Execute milestones in order

**Files:**
- Follow: the five plans in the milestone index

- [ ] **Step 1: Execute Milestone 1**

Expected acceptance commit: `feat: establish six-phase authoritative kernel`.

- [ ] **Step 2: Execute Milestone 2**

Expected acceptance commit: `feat: propose verified semantic switch programs`.

- [ ] **Step 3: Execute Milestone 3**

Expected acceptance commit: `feat: complete persistent semantic cognition`.

- [ ] **Step 4: Execute Milestone 4**

Expected acceptance commit: `feat: train and benchmark the hybrid MVP`.

- [ ] **Step 5: Execute Milestone 5**

Expected acceptance commit: `release: certify six-phase authoritative hybrid MVP`.

## Master Task 3: Enforce every milestone checkpoint

**Files:**
- Update: `artifacts/validation/MILESTONE_RECEIPT.json`

- [ ] **Step 1: Run the focused tests from the active plan**

Expected: new tests fail before implementation and pass afterward; no test is weakened to obtain green status.

- [ ] **Step 2: Run the complete active suite**

```powershell
python -m pytest -q
```

Expected: zero failures, errors, skips, xfails, or xpasses among active tests.

- [ ] **Step 3: Run source and artifact validation**

```powershell
python scripts\validate_mvp.py --profile development --output artifacts\validation\MILESTONE_RECEIPT.json
```

Expected: every owner implemented through the current milestone is `verified`; future capabilities are absent from the advertised runtime contract rather than marked as silently passing.

- [ ] **Step 4: Inspect and commit only declared work**

```powershell
git diff --check
git status --short
git diff --name-only
```

Expected: no legacy checkpoint, cache, temporary database, model training scratch directory, or undeclared file enters the commit.

## Master Task 4: Verify the single Milestone-5 release and application

**Files:**
- Verify: `dist/cemm_authoritative_hybrid_mvp.zip`
- Verify: `dist/BUILD_RECEIPT.json`
- Verify: `dist/CLEAN_BUNDLE_RECEIPT.json`
- Verify: `dist/APPLICATION_RECEIPT.json`
- Verify: `artifacts/validation/FINAL_VALIDATION_RECEIPT.json`
- Verify: `artifacts/evaluation/COMPETITIVE_EVALUATION.json`

- [ ] **Step 1: Verify the release commit and build receipts**

```powershell
Set-Location C:\Users\Son\Downloads\cemm_authoritative_hybrid_mvp_implementation
python scripts\provision_browser.py --manifest release\browser_runtime.json --cache C:\Users\Son\Downloads\cemm_browser_cache --receipt dist\BROWSER_TOOLCHAIN.json
$env:CEMM_BROWSER_BIN = (Get-Content -Raw dist\BROWSER_TOOLCHAIN.json | ConvertFrom-Json).binary_path
git show --no-patch --oneline HEAD
Get-FileHash -Algorithm SHA256 dist\cemm_authoritative_hybrid_mvp.zip
python scripts\verify_clean_bundle.py dist\cemm_authoritative_hybrid_mvp.zip --browser-binary $env:CEMM_BROWSER_BIN --output dist\MASTER_VERIFICATION_RECEIPT.json
```

Expected: the commit equals `dist/BUILD_RECEIPT.json.source_commit`, the archive hash matches, and clean verification reproduces the accepted receipt.

- [ ] **Step 2: Verify committed evaluation and the one application receipt**

```powershell
python scripts\compare_baselines.py --verify-only --cemm artifacts\evaluation\CEMM_EVALUATION.json --qwen artifacts\evaluation\QWEN_BASELINE.json --comparison artifacts\evaluation\COMPETITIVE_EVALUATION.json
Get-Content dist\APPLICATION_RECEIPT.json
```

Expected: every absolute CEMM gate and the measured Qwen comparison are internally consistent; `baseline_unavailable` is absent; the application receipt names this archive hash, the exact target, the recoverable backup, and successful applied verification. This master task performs no second build or application.
