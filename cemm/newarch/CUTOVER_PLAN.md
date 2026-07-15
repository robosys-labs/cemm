# CEMM v3.4 — Migration Completion Plan (Phase 12: Legacy Retirement and Authoritative Cutover)

Status: **NOT complete — parallel legacy/v3.4 pipeline confirmed active in `run_turn`**
Audit date: this document supersedes all prior "cutover complete" claims in this file, which were false.
Scope: make v3.4 canonical components the sole authority for every stage in `cemm/kernel/semantic_kernel_runtime.py::run_turn`, then delete the demoted legacy implementation.
Anchored to: AGENTS.md, `CORE_LOOP.md`, `UNDERSTANDING_PIPELINE.md`, `AUTHORITY_MATRIX.md`, `IMPLEMENTATION_PLAN.md` Phase 12.

## 0. Why the prior "complete" status was false

This file previously claimed "full cutover complete, 1089 tests pass, 28 authorities registered." That claim conflated three different things that AGENTS.md requires to be kept distinct: **implemented**, **wired**, and **authoritative**. Direct code inspection of `cemm/kernel/semantic_kernel_runtime.py` (1569 lines) as of this audit shows:

- All 20 v3.4 components listed in the old "Completed work" section do exist and are instantiated (`kernel/understanding/*`, `kernel/execution/*`, `kernel/response/*`, `kernel/epistemics/*`, `kernel/self_model/*`, `kernel/learning/coordinator.py`, `kernel/schema/store.py`). **implemented: true.**
- All 20 are called inside `run_turn`. **wired: true.**
- None of them are **authoritative**. The legacy pipeline (`SemanticCPU`/`ActResolutionPlanner` planning, `GraphPatchExtractor`, `PatchValidator`, `PatchCommitter`, `ResponseFormationEngine`, `OutputStateUpdater`, `ErrorAttributionEngine`) runs in full, unmodified, in the same `run_turn` call, and its outputs — not the v3.4 outputs — are what get committed to the durable store and rendered to the user (`result.realized_output = bundle.text` comes from `self._response_engine.form(...)`, a legacy component; see §2 below). This is the exact "no parallel old/new pipelines" / "no shadow code claiming authority" violation AGENTS.md §24 and `kernel/retirement/cutover.py`'s own docstring forbid.
- `AuthoritativeCutoverVerifier.register()` only records a self-reported string pair (`authority_key`, `implementation_name`). It never checks that the named implementation actually produced the response/commit the user received. `is_valid=True` therefore only proves "someone called `.register(...)` once per key," not authoritative behavior.
- `LegacyImportGuard.scan_directory()` (`kernel/retirement/legacy_guard.py`) only walks `kernel/<canonical_subpackage>/` directories (`model`, `schema`, `epistemics`, `learning`, `understanding`, `self_model`, `execution`, `response`, `correction`, `retirement`, `foundations`, `boot`). It never scans `kernel/*.py` at the package root — which is exactly where `semantic_kernel_runtime.py`, `semantic_cpu.py`, `meaning_perceptor.py`, `meaning_graph_builder.py`, and all 60+ other legacy modules live. `tests/architecture/test_phase12_retirement.py` explicitly comments "legacy kernel root files may still have them — that's expected" (line ~247) — i.e. the completion gate was deliberately scoped to exclude the one file where the violation lives, so "1089 tests pass" does not and cannot detect this.

Conclusion: the 1089 passing tests and 28 registered authorities are real, but they certify the existence of v3.4 components, not their authority. The actual cutover (Phase 12 of `IMPLEMENTATION_PLAN.md`) has not started for the orchestration layer.

## 1. Verified end-to-end trace of `run_turn` (current code, `cemm/kernel/semantic_kernel_runtime.py`, 1569 lines)

Both a legacy branch and a v3.4 branch execute for nearly every stage. The table marks which branch's *output* actually reaches the durable store / the user, per direct read of the code (not per comment or variable name).

| Lines | Stage | Legacy call (still present) | v3.4 call (present, parallel) | Whose output is used downstream |
|---|---|---|---|---|
| 419-431 | A Orient | `session_store.restore`, `teaching_frame_manager`, `learning_episode_manager` | — (no `KernelSnapshot` pinning exists) | legacy (only path) |
| 433-455 | B1/B2 Perceive | `self._cpu.perceptor.perceive(signal, kernel)` → `percept` | — | legacy `percept` feeds every later stage, including v3.4 adapters |
| 474-492 | — | affect update, entity salience update | — | legacy |
| 494-500 | B2 Perceive (v3.4) | — | `PerceptToSurfaceEvidence.convert(percept)` → `surface_evidence` | v3.4 output stored in `result.surface_evidence` for trace only; nothing downstream reads it except the v3.4 branch itself |
| 502-508 | B3 Compose | — | `SemanticComposer.compose(surface_evidence)` → `candidate_graph` | v3.4-only, trace field; legacy graph (below) is what the operational compiler actually uses |
| 510-522 | B4 Ground | — | `GroundingResolver.ground_referent(...)` → `grounding_assessments` | v3.4-only, trace field |
| 524-559 | C2-C3 Know | — | `EpistemicEvaluator.evaluate`, `CapabilityEvaluator.evaluate` | v3.4-only, trace fields |
| 561-570 | B7 Resolve | — | `V34InterpretationResolver.resolve(candidate_graph, ...)` → `interp_result` | feeds only the v3.4 goal arbiter/response-planner branch, not the legacy plan/response branch |
| 572-583 | C4 Gaps | — | `V34GapDetector.detect(...)` → `v34_gaps` | v3.4-only; **legacy** `SemanticGapDetector` (line 629-648) is the one whose gaps drive `obligation_graph_builder` and the actually-asked clarification question |
| 585-594 | C5 Focus | — | `WorkspaceController.focus(...)` | overwritten seconds later — `result.working_set` is reassigned by the **legacy** `SemanticAttentionController.attend(...)` at line 788 |
| 596-604 | B5-B6 Learn | — | `LearningCoordinator.open_transaction(gap)` | v3.4-only trace field; **legacy** `LearningEpisodeManager`/`LearningQuestionPlanner`/`LearningAnswerAssimilator` (lines 440-450, 738-750) own the actual learning-obligation lifecycle that is persisted and re-asked next turn |
| 606-613 | C1 Retrieve | — | `SemanticRetriever.retrieve(...)` | v3.4-only; result (`retrieval_batch`) is not even assigned to `result` and is unused after this line |
| 615-627 | B3 Compose (legacy) | `MeaningGraphBuilder.build(percept)` → `uol_graph` | — | legacy — `uol_graph` is the object every operational/response stage below actually consumes |
| 629-648 | Gap detection (legacy) | `SemanticGapDetector.detect(...)` → `result.semantic_gaps` | — | legacy — authoritative gaps |
| 650-658 | Causal | `CausalBridge.predict(...)` | — | legacy |
| 660-666 | Situation frame | `SituationFrameBuilder.build(...)` | — | legacy |
| 668-691 | Entity grounding (legacy shadow) | `EntityGroundingResolver.resolve(...)` | — | legacy |
| 693-724 | Interpretation lattice (legacy) | `InterpretationLattice` + `InterpretationResolver` (legacy, not v3.4) | — | legacy — `result.interpretation_resolution` drives blocking-gap classification and predicate activation below |
| 726-752 | Blocking gap classification | `SemanticGapDetector.classify_blocking`, `LearningEpisodeManager.create_episode`, `LearningQuestionPlanner.plan` | — | legacy — this is what actually creates the next learning question |
| 758-783 | Predicate activation gate | `PredicateActivationResolver.resolve(...)` | — | legacy |
| 785-791 | C5 Focus (legacy) | `SemanticAttentionController.attend(...)` → **overwrites** `result.working_set` | — | legacy wins over v3.4 `WorkspaceController` output from line 587-592 |
| 793-798 | Program compile | `SemanticProgramCompiler.compile(...)` | — | legacy |
| 800-811 | Safety (preliminary) | `SafetyFrameDetector.detect(...)` | — | legacy |
| 813-934 | 3c Operational contracts | `OperationalMeaningCompiler`, `StateOccupancyCompiler`, `StateDeltaCompiler`, `StateTransmutationCompiler`, `OperationalCausalRouter`, `ObligationGraphBuilder`, `OperationalContractCompiler`, `TransmutationAuthorizer` | — | legacy — produces `obligation_contract`, the object `ResponseFormationEngine` and `write_outcome` are built from |
| 942-974 | 3.3 execution ledger | `TurnExecutionPlanner`, `ContractExecutor`, `LearningUseObserver` | — | legacy |
| 976-1019 | 3d Teaching/relations | `TeachingFrameManager`, `RelationFrameCompiler`, `SemanticQueryEngine.execute_contract`, `PredicateSchemaInductor` | — | legacy — `answer_binding`/`relation_frames` used in the response |
| 1031-1042 | D3 Plan (legacy) | `self._cpu.planner.plan(...)` (`ActResolutionPlanner`) → `act_plan` | — | legacy; unused by v3.4 branch, but nothing downstream reads `act_plan` either (dead value) |
| 1044-1065 | D1-D3 Decide (v3.4) | — | `GoalArbiter.derive_and_arbitrate`, `V34Planner.plan` | v3.4-only trace branch |
| 1067-1105 | D4/E1/E3 (v3.4) | — | `OperationAuthorizer`, `OperationExecutor`, `OutcomeReconciler` | v3.4-only; `exec_result` feeds only the v3.4 commit block (1151-1175) and message-plan metadata, never the durable-store commit that matters (next row) |
| 1107-1149 | 5-7 Patches (legacy) | `GraphPatchExtractor.extract`, `PatchValidator.validate`, `PatchCommitter.commit_batch`, `SemanticConsolidator` | — | legacy — **this is the actual persistent-mutation authority**: `commit_results` here, not `CommitCoordinator`, is what `_build_write_outcome` and the durable store reflect |
| 1151-1175 | F Commit (v3.4) | — | `CommitCoordinator.commit(mutation_set)` built from `exec_result` | v3.4-only parallel commit path — a **second, independent mutation authority** running against the same durable state; classic AGENTS.md "no parallel old/new pipelines" violation |
| 1177-1198 | G1-G2 Response content (v3.4) | — | `ResponsePlanner.plan_response(...)` → `message_plan` | v3.4-only; not used to build `result.realized_output` |
| 1204-1236 | 8a-8b Write outcome / situation | `_build_write_outcome(commit_results, ...)`, `ResponseSituation(...)` | — | legacy — built from legacy `commit_results`, not `commit_outcome` |
| 1238-1266 | G3 Realize (legacy, actually authoritative) | `ResponseFormationEngine.form(response_situation)` → **`result.realized_output = bundle.text`** | — | **legacy — this is the text the user actually receives** |
| 1268-1307 | 8a/8b Output state / error attribution | `OutputStateUpdater`, `ErrorAttributionEngine` | — | legacy |
| 1309-1343 | H Common ground (v3.4) | — | `CommonGroundManager.record_dispatch(...)` keyed off `message_plan` (v3.4, mostly empty) | v3.4-only; discourse commitments recorded here do not correspond to what was actually said in `bundle.text` |
| 1399-1411 | Session persist | `session_store.persist`, teaching frame, learning state | — | legacy |

**Bottom line:** the response text, the committed facts, the asked clarification question, and the learning obligation lifecycle are all still produced by the legacy pipeline. The v3.4 components run, populate `RuntimeCycleResult` trace fields (`surface_evidence`, `candidate_graph`, `grounding_assessments`, `epistemic_assessments`, `commit_outcome`, `message_plan`, `common_ground_entries`), and are visible in the web-demo debug panel — but they do not decide anything the user experiences. This matches AGENTS.md's definition of forbidden "shadow code."

### Additional legacy leftovers outside `run_turn`

- `cemm/kernel/pipeline.py` (`Pipeline.run()`) and `cemm/__main__.py`/`cemm/web_demo.py` call into `SemanticKernelRuntime.run_turn`/`run_text` directly — no separate legacy code path there, but they inherit the same non-authoritative v3.4 state.
- `cemm/kernel/retirement/legacy_guard.py` — `LegacyImportGuard.scan_directory` only scans the 12 canonical subpackages, never `kernel/*.py` root files. This must be fixed as part of, not after, the cutover, or the completion gate remains structurally unable to detect this class of violation.
- `cemm/kernel/retirement/cutover.py` — `AuthoritativeCutoverVerifier.register()`/`verify_cutover()` only checks that a string was registered once per key; it has no way to verify the registered implementation is actually authoritative at runtime. This needs a runtime-assertion mechanism (e.g. each stage asserts it is the only writer of its `CognitiveCycle` field) rather than a static string ledger, or it will keep passing "cutover complete" checks vacuously.

## 2. Cutover strategy

**Approach: incremental stage-by-stage replacement, following CORE_LOOP ordering.**

Each sub-task:
1. Implements missing v3.4 component if needed
2. Replaces legacy stage with v3.4 authoritative path in `run_turn`
3. Removes the legacy stage code
4. Runs full test suite to verify zero regressions
5. Registers authority in cutover verifier

**Guardrails (from AGENTS.md):**
- No parallel old/new pipelines — each stage is either legacy OR v3.4, never both
- No shadow code claiming authority
- One authority owns every changed decision
- Semantic, schema, and control layers remain distinct
- Snapshot and mutation invariants pass
- Activation is snapshot-atomic
- Documentation status is updated honestly

## 3. Sub-tasks

All v3.4 components referenced below already exist under `kernel/understanding`, `kernel/execution`, `kernel/response`, `kernel/epistemics`, `kernel/self_model`, `kernel/learning`, `kernel/schema` — no new component files are needed. Every sub-task is purely: (a) make the v3.4 call's output the only value downstream code reads, (b) delete the legacy call and its imports, (c) delete the now-dead legacy module if nothing else in the codebase still imports it.

### Sub-task 0: Fix the completion-gate blind spot (do this first)
**Stage:** verification infrastructure
**What:** `LegacyImportGuard.scan_directory` (`kernel/retirement/legacy_guard.py`) must scan `kernel/*.py` root files, not only the 12 canonical subpackages, or none of the sub-tasks below can be verified as complete. `AuthoritativeCutoverVerifier` must gain a runtime check (e.g. each `CognitiveCycle` field has exactly one writer per turn, asserted in `run_turn` itself or via a field-write interceptor) instead of accepting a static self-reported string per authority key.
**Files:**
- `cemm/kernel/retirement/legacy_guard.py` — add root-file scanning, excluding files explicitly staged for deletion in a given sub-task
- `cemm/kernel/retirement/cutover.py` — add `assert_single_writer(field_name, writer)` or equivalent runtime proof
- `cemm/tests/architecture/test_phase12_retirement.py` — remove the root-file exclusion at the `canonical_pkg_violations` filter
**Tests:** guard fails loudly against current `semantic_kernel_runtime.py` (expected — this is the correct starting state)

### Sub-task 1: Orient — KernelSnapshot pinner
**Stage:** A. ORIENT
**Authority:** cycle_scheduling
**What:** Add `KernelSnapshot` pinning (schema/memory/episodic/common-ground/self/resource/permission/goal/learning/competence/grounding-policy/foundation/inference/adapter/context revisions + clock) as specified in `CORE_LOOP.md` §3. Currently only `session_store.restore` exists; there is no snapshot object at all.
**Files:**
- `cemm/kernel/model/cycle.py` — add `pin_snapshot()` factory (file exists, factory does not)
- `cemm/kernel/semantic_kernel_runtime.py` — lines 419-431
**Tests:** verify snapshot pins all 15 revision fields

### Sub-task 2: Perceive — SurfaceEvidence authoritative (UNDERSTAND B2)
**Stage:** B2. Perceive
**Authority:** surface_analysis
**What:** `PerceptToSurfaceEvidence.convert` output (lines 494-500) becomes the only percept representation later stages read; `MeaningPerceptor` stays only as the adapter called inside `PerceptToSurfaceEvidence`, not called directly by `run_turn` (lines 433-455).
**Files:** `cemm/kernel/semantic_kernel_runtime.py`
**Delete:** the direct `self._cpu.perceptor.perceive(...)` call at line 436 once every downstream consumer (graph builder, entity grounding, teaching frame manager, etc.) is repointed at `surface_evidence`-derived data; affect/salience updates (474-492) move to read from `surface_evidence`.
**Tests:** verify `surface_evidence` is the sole percept input to Compose

### Sub-task 3: Compose — SemanticComposer authoritative (UNDERSTAND B3)
**Stage:** B3. Compose
**Authority:** semantic_composition
**What:** `candidate_graph` (lines 502-508) becomes the input to grounding/operational compilation instead of `uol_graph` (currently built separately at lines 615-627 by legacy `MeaningGraphBuilder`).
**Files:** `cemm/kernel/semantic_kernel_runtime.py`
**Delete:** `MeaningGraphBuilder.build` call (615-627) once `OperationalMeaningCompiler` et al. are re-pointed at candidate-graph-derived structures, or kept only as a compatibility view built *from* `candidate_graph` (never independently from `percept`).
**Tests:** verify `candidate_graph` is authoritative; operational compiler consumes it

### Sub-task 4: Ground — GroundingResolver authoritative (UNDERSTAND B4)
**Stage:** B4. Ground
**Authority:** referent_sense_role_grounding, current_schema_use
**What:** `grounding_assessments` (510-522) becomes the sole grounding source.
**Files:** `cemm/kernel/semantic_kernel_runtime.py`
**Delete:** `CausalBridge.predict` (650-658), `SituationFrameBuilder.build` (660-666), `EntityGroundingResolver.resolve` (668-691) — reimplement any still-needed causal/situation signal as a `GroundingResolver`/`EpistemicEvaluator` input instead of a parallel resolver.
**Tests:** verify grounding_assessments are authoritative

### Sub-task 5: Resolve — v3.4 InterpretationResolver authoritative (UNDERSTAND B7)
**Stage:** B7. Resolve
**Authority:** interpretation_selection
**What:** `interp_result` from `V34InterpretationResolver.resolve` (561-570) becomes the sole selected-interpretation source for goal arbitration, gap detection, and response planning.
**Files:** `cemm/kernel/semantic_kernel_runtime.py`
**Delete:** `InterpretationLattice`/legacy `InterpretationResolver` block (693-724) and everything keyed off `result.interpretation_resolution` (726-752 blocking-gap classification, 758-783 predicate activation) — reimplement blocking-gap classification and predicate activation as consumers of `interp_result`/`v34_gaps`, not the legacy lattice.
**Tests:** verify selected interpretations from candidate graph drive gap/goal/response stages

### Sub-task 6: Learn — LearningCoordinator authoritative (UNDERSTAND B5-B6)
**Stage:** B5-B6
**Authority:** learning_lifecycle, replay_scheduling_idempotence
**What:** `LearningCoordinator` (596-604) becomes the sole owner of pending-evidence consumption and transaction lifecycle, replacing `LearningEpisodeManager`/`LearningQuestionPlanner`/`LearningAnswerAssimilator`.
**Files:** `cemm/kernel/semantic_kernel_runtime.py`, `cemm/kernel/learning/coordinator.py` (extend to cover question planning + answer assimilation if not already present)
**Delete:** answer assimilation at perceive time (438-450), blocking-gap-triggered episode/question creation (737-750) — migrate their responsibilities into `LearningCoordinator`
**Tests:** verify learning transaction lifecycle owns obligations previously owned by `LearningEpisodeManager`

### Sub-task 7: Know — Retrieve + Gaps + Focus authoritative (KNOW C1, C4, C5)
**Stage:** C1, C4, C5
**Authority:** semantic_retrieval, gap_creation
**What:** `SemanticRetriever.retrieve` (606-613) result must actually be consumed (currently discarded); `v34_gaps` (572-583) must drive obligation-graph building and clarification-question creation instead of legacy `SemanticGapDetector` (629-648); `WorkspaceController.focus` (585-594) output must not be overwritten by `SemanticAttentionController.attend` (785-791).
**Files:** `cemm/kernel/semantic_kernel_runtime.py`
**Delete:** `SemanticGapDetector.detect`/`classify_blocking` (629-648, 726-752 — superseded by sub-task 5/6), `SemanticAttentionController.attend` (785-791), `PredicateActivationResolver` block (758-783, superseded by sub-task 5)
**Tests:** verify epistemic/capability assessments, gaps, and workspace snapshot are unique and authoritative

### Sub-task 8: Decide — GoalArbiter + Planner + OperationAuthorizer authoritative (DECIDE D1-D4)
**Stage:** D1-D4
**Authority:** active_goals, plan_selection, operation_authorization
**What:** `goal_result`/`plan_batch`/`authorization` (1044-1084) become the only plan/authorization objects consumed by execution.
**Files:** `cemm/kernel/semantic_kernel_runtime.py`
**Delete:** `self._cpu.planner.plan(...)` (`ActResolutionPlanner`, 1031-1042) — already dead-value downstream, safe to remove once nothing reads `act_plan`
**Tests:** verify goals, plans, authorization drive execution exclusively

### Sub-task 9: Act and reconcile — OperationExecutor authoritative (ACT E1-E3)
**Stage:** E1-E3
**Authority:** execution, outcome_reconciliation
**What:** `exec_result`/`OutcomeReconciler` output (1086-1105) become the sole execution-outcome source feeding commit.
**Files:** `cemm/kernel/semantic_kernel_runtime.py`
**Delete:** `OperationalMeaningCompiler`, `StateOccupancyCompiler`, `StateDeltaCompiler`, `StateTransmutationCompiler`, `OperationalCausalRouter`, `ObligationGraphBuilder`, `OperationalContractCompiler`, `TransmutationAuthorizer` (813-934), `TurnExecutionPlanner`/`ContractExecutor`/`LearningUseObserver` (942-974) — port any still-required safety-gate and obligation-tracking logic into `OperationAuthorizer`/`OperationExecutor`/`GapDetector` first
**Tests:** verify execution outcomes and reconciliation are the exclusive execution record

### Sub-task 10: Critical commit — CommitCoordinator sole mutation authority (CRITICAL_COMMIT F)
**Stage:** F. CRITICAL_COMMIT
**Authority:** persistent_mutation
**What:** Collapse the two parallel commit paths into one. `CommitCoordinator.commit` (1151-1175) must become the only code that writes to the durable store; `PatchValidator`/`PatchCommitter` (1107-1149) must be deleted, not run alongside it. Any patch-extraction logic still needed must be reimplemented as `MutationSet` construction feeding `CommitCoordinator`.
**Files:** `cemm/kernel/semantic_kernel_runtime.py`
**Delete:** `GraphPatchExtractor.extract`, `PatchValidator.validate`, `PatchCommitter.commit_batch`, `SemanticConsolidator.consolidate` (1107-1149); `_build_write_outcome` (1497-1569) rewritten to read from `commit_outcome`, not `commit_results`
**Tests:** verify a single commit path produces `WriteOutcome`; no dual-commit race is possible

### Sub-task 11: Communicate — ResponsePlanner + renderer authoritative (COMMUNICATE G1-G4)
**Stage:** G1-G4
**Authority:** response_content, surface_realization
**What:** `message_plan` (1177-1198) becomes the sole input to text realization; `result.realized_output` must come from rendering `message_plan`, not from `ResponseFormationEngine.form(response_situation)` (1238-1266) fed by legacy `obligation_contract`/`answer_binding`/`relation_frames`.
**Files:** `cemm/kernel/semantic_kernel_runtime.py`, `cemm/response/response_formation_engine.py` (repurpose as the G3 "language renderer" that consumes a `SemanticMessagePlan`, or replace with a new renderer under `kernel/response/`)
**Delete:** `ResponseSituation` construction from `obligation_contract`/`semantic_program`/`relation_frames`/`answer_binding` (1207-1236); `RelationFrameCompiler`/`SemanticQueryEngine.execute_contract`/`PredicateSchemaInductor` (994-1019) once `ResponsePlanner`/`SemanticRetriever` cover query-answer content selection
**Tests:** verify response provenance is bound to `message_plan` content items; no internal IDs leak; reparse validator passes

### Sub-task 12: Output commit and consolidate — CommonGroundManager authoritative (OUTPUT_COMMIT H)
**Stage:** H
**Authority:** common_ground, cycle_scheduling
**What:** `CommonGroundManager.record_dispatch` (1309-1343) must be keyed off what was *actually rendered* in sub-task 11, not a mostly-empty `message_plan`. `OutputStateUpdater`/`ErrorAttributionEngine` (1268-1307) responsibilities move into common-ground/capability-competence updates.
**Files:** `cemm/kernel/semantic_kernel_runtime.py`
**Delete:** `OutputStateUpdater.update/apply`, `ErrorAttributionEngine.evaluate/record_success` (1268-1307) once discourse-state and error-rate tracking are ported into `CommonGroundManager`/`CapabilityEvaluator`
**Tests:** verify common ground reflects only actually-dispatched content; learning finalization and wake scheduling run

### Sub-task 13: Fix and re-run the completion gate
**Stage:** verification
**What:** With sub-tasks 1-12 done, `LegacyImportGuard.scan_directory` (fixed in sub-task 0) must return `is_clean=True` against the full `kernel/` tree, and `AuthoritativeCutoverVerifier`'s runtime single-writer check must pass for a real turn, not just registration calls.
**Files:** `cemm/kernel/semantic_kernel_runtime.py`, `cemm/tests/architecture/test_phase12_retirement.py`
**Tests:** full completion gate (14 criteria in `CompletionGateChecker`), all criteria backed by the actual scan/runtime check, not a default-`True` keyword argument

### Sub-task 14: Delete dead legacy modules
**Stage:** cleanup
**What:** Once no canonical code path imports them (verified by sub-task 13's guard), delete the module files entirely (send to recycle bin per workspace convention, not `git rm -f` silently, unless the user confirms permanent removal is fine for a version-controlled repo).
**Files to delete:** `meaning_perceptor.py`, `meaning_graph_builder.py`, `semantic_cpu.py`, `interpretation_lattice.py`, `interpretation_resolver.py` (legacy), `branch_arbitrator.py`, `entity_grounding_resolver.py`, `predicate_activation_resolver.py`, `../learning/semantic_gap_detector.py`, `operational_meaning_compiler.py`, `state_occupancy_compiler.py`, `state_delta_compiler.py`, `state_transmutation_compiler.py`, `operational_causal_router.py`, `obligation_graph_builder.py`, `obligation_contract_builder.py`, `query_contract_builder.py`, `write_contract_builder.py`, `reaction_contract_builder.py`, `operational_contract_compiler.py`, `turn_execution_planner.py`, `contract_executor.py`, `semantic_program_compiler.py`, `semantic_obligation_scheduler.py`, `relation_frame_compiler.py`, `relation_algebra.py`, `semantic_query_engine.py`, `transmutation_authorizer.py`, `../learning/patch_validator.py`, `../learning/patch_committer.py`, `../response/response_formation_engine.py` (unless repurposed per sub-task 11), `output_state_updater.py`, `error_attribution_engine.py`, `conversation_act_classifier.py` (already unused — `self._act_classifier = None`), `safety_frame_detector.py` (unless ported into `OperationAuthorizer`), `situation_frame_builder.py`, `causal/causal_bridge.py`, `teaching_frame_manager.py`, `teaching_interpreter.py`, plus the now-orphaned `../learning/learning_episode_manager.py`, `../learning/lexeme_candidate_index.py`, `../learning/learning_question_planner.py`, `../learning/learning_answer_assimilator.py` if sub-task 6 fully absorbed their behavior.
**Also delete:** the now-unused constructor wiring for all of the above in `SemanticKernelRuntime.__init__` (lines 52-233), and any properties exposing them.
**Tests:** `LegacyImportGuard` clean scan of full `kernel/` tree; `ForbiddenPatternScanner` clean; full test suite green; web demo manually re-verified end-to-end with the debug panel showing only v3.4 fields being non-empty

## 4. Risk mitigation

- Each sub-task runs the full test suite (current count: 1089 tests); a sub-task is not merged until it passes with zero regressions.
- Because sub-task 0 correctly makes `LegacyImportGuard` fail against the current codebase, `test_canonical_kernel_no_legacy_imports` and similar gate tests must be expected to go red at sub-task 0 and only return green once sub-task 14 completes — this is a known, intended state, not a regression to work around.
- `uol_graph` and `obligation_contract` compatibility shims may be kept temporarily as *derived views* built from `candidate_graph`/`interp_result`, never as an independently-computed parallel value, through sub-tasks 3-11.
- Do not delete any file until sub-task 13's guard confirms zero remaining canonical imports of it — deleting out of order will break the currently-passing test suite for no architectural benefit.
- Per workspace convention, file deletions in sub-task 14 go to the recycle bin / are done via `git rm` in a reviewable commit, not irreversible disk deletion.

## 5. Ordering constraint

Sub-tasks MUST be executed in order. Each depends on the prior:
0 → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14

No sub-task may skip a prior sub-task. The pipeline is sequential.

## 6. Definition of done (per AGENTS.md five-state model)

The cutover is complete only when, for every stage in `CORE_LOOP.md` §5-6:

| State | Required evidence |
|---|---|
| specified | already true — `CORE_LOOP.md`, `AUTHORITY_MATRIX.md` |
| implemented | already true — all v3.4 components exist under the canonical subpackages |
| wired | already true — all are called from `run_turn` |
| authoritative | **not yet true** — becomes true only after sub-tasks 1-12 remove every parallel legacy computation of the same decision |
| verified | **not yet true** — becomes true only after sub-task 13's fixed guard/verifier pass against the *entire* `kernel/` tree, and sub-task 14 deletes the dead legacy modules so there is nothing left to accidentally re-wire |

Until all five hold, this document's status line must read "NOT complete," per AGENTS.md's documentation-honesty requirement. Do not restore a "cutover complete" status line without re-running the trace in §1 against the then-current `semantic_kernel_runtime.py` and confirming every row's "whose output is used downstream" column says the v3.4 component, with zero remaining legacy calls in the file.
