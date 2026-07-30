# Evidence-Gated Corrective Replay Plan

> **Status:** Draft for review
> **Branch:** `hybrid-mvp/integration` in `C:\dev\cemm`
> **Working directory:** `hybrid_mvp/` subdirectory
> **Date:** 2026-07-30

## Executive Summary

The hybrid MVP completed M1–M3 and M4 Tasks 1–4, but investigation found the work
is not trustworthy. The root causes are upstream in M1–M3, not in M4 training:

1. **M1's validation receipt is too weak** — `--profile` mostly changes the
   receipt label without verifying the advertised owner graph or neural
   runtime. Six-phase tests use fixture owners.
2. **M2 introduced two incompatible proposal ABIs** — the release proposer
   returns `ProposalResult` (with `.candidates`), but `HybridRuntime.process()`
   expects the old fixture ABI (`.program`, `.output_refs`,
   `.rejection_codes`). The bootstrap proposer computes grounding/contributions
   but discards them, enumerating every global designation target and operator.
3. **M3's cognition modules are isolated** — end-to-end tests inject fixture
   proposal, verification, evaluation, effect, and realization owners. The real
   runtime stops after ORIENT because of the proposal/runtime ABI mismatch.
4. **M4 trained on corrupt labels** — `episodes.py:689` ignores
   `case.semantic_assertions`, runs `BootstrapProposer`, and selects its first
   accepted candidate as gold. Hard negatives are mostly unchanged clones.
   Calibration is disconnected from model inference. Evaluation bypasses the
   authentic six-phase loop.

The 100-epoch retrain confirmed more training cannot fix this: exact accuracy
dropped from 61/78 to 59/78.

## Strategy: Evidence-Gated Corrective Replay

Preserve Git history. Mark current M2–M4 acceptance receipts and model
artifacts as **superseded**. Revalidate M1, repair M2's single ABI/composer/model
path, integrate M3 through the real runtime, then regenerate and retrain M4
before proceeding to M5.

Each phase has a hard gate: no phase begins until the previous phase's
acceptance tests pass against the **real runtime** (no fixture owners).

---

## Phase 0: Supersede and Scaffold

**Goal:** Mark current artifacts as superseded, create the corrective replay
workspace, and establish the evidence-gated acceptance protocol.

### 0.1 Mark superseded artifacts
- [ ] Move `artifacts/validation/MILESTONE_RECEIPT.json`,
      `M2_PROPOSAL_RECEIPT.json`, `M3_MILESTONE_RECEIPT.json` to
      `artifacts/validation/superseded/`
- [ ] Move `artifacts/proposal_release/`, `artifacts/realizer_release/`,
      `artifacts/proposal_dev/`, `artifacts/realizer_dev/` to
      `artifacts/superseded/`
- [ ] Move `artifacts/calibration.json` to `artifacts/superseded/`
- [ ] Move `artifacts/evaluation/CEMM_EVALUATION.json` to
      `artifacts/superseded/`
- [ ] Add `SUPERSEDED.md` to `artifacts/superseded/` explaining why these
      artifacts are not trustworthy and are preserved only as evidence

### 0.2 Define the real-runtime acceptance protocol
- [ ] Create `tests/acceptance/REAL_RUNTIME_ACCEPTANCE.py` — a shared fixture
      that builds `HybridRuntime` with **real** owners only (neural proposer,
      exact verifier, real evaluation/effect/realization owners). No fixture
      owners, no stubs, no bypass paths.
- [ ] Add a test `test_real_runtime_smoke` that processes "hello",
      "what is your name?", and "open the door" through the full six-phase
      `process()` path and asserts each produces a typed `CycleResult` (not
      `operation_failed` / `implementation_gap` / stopping after ORIENT).
- [ ] This test is the **gate** for all subsequent phases: it must pass before
      any phase is marked complete.

### 0.3 Commit
- [ ] `git commit -m "scaffold: mark superseded artifacts and define real-runtime acceptance gate"`

---

## Phase 1: Revalidate M1 (Six-Phase Kernel Integrity)

**Goal:** Verify the six-phase kernel's structural integrity against the real
runtime, not fixture owners.

### 1.1 Audit the ProposalOwner ABI mismatch
- [ ] Document the exact mismatch: `ProposalOwner.propose()` returns
      `ProposalResult` (has `.candidates`, `.explored_states`, `.truncated`,
      `.model_identity`) but `HybridRuntime.process()` accesses
      `proposal.program`, `proposal.output_refs`, `proposal.rejection_codes`
      (lines 685–691, 727).
- [ ] Document that `propose_and_verify()` (line 334) uses a different
      `_ProposeAndVerifyResult` type (line 170) with `.accepted`, `.proposal`,
      `.program` — a third ABI.
- [ ] Write `tests/acceptance/test_proposal_abi_consistency.py` that asserts
      the runtime's `process()` and `propose_and_verify()` both consume the
      same `ProposalResult` type returned by `ProposalOwner.propose()`.

### 1.2 Audit M1 six-phase tests for fixture-owner dependency
- [ ] List every M1 test that injects fixture/stub owners into `HybridRuntime`.
- [ ] For each, classify: (a) the test is genuinely unit-scoped and may keep
      fixtures, or (b) the test claims to verify the six-phase kernel but
      bypasses real owners and must be rewritten.
- [ ] Write `tests/acceptance/test_six_phase_no_fixture_owners.py` that asserts
      no acceptance-level test uses fixture proposal/verification/evaluation/
      effect/realization owners.

### 1.3 Gate
- [ ] `test_proposal_abi_consistency` passes
- [ ] `test_six_phase_no_fixture_owners` passes
- [ ] `test_real_runtime_smoke` passes (may fail here — that's expected; it
      becomes the driving test for Phase 2)
- [ ] `git commit -m "revalidate: audit M1 six-phase kernel integrity and proposal ABI"`

---

## Phase 2: Repair M2 (Single Proposal ABI and Grounded Composer)

**Goal:** Unify the proposal ABI so the runtime, bootstrap proposer, and neural
proposer all use one `ProposalResult` type. Make the proposer consume grounded
designation candidates, semantic kinds, contributions, ports, and orientation
to constrain decoding.

### 2.1 Unify ProposalResult as the single proposal ABI
- [ ] Extend `ProposalResult` to carry the fields the runtime needs:
      `program` (the selected/primary candidate), `output_refs`,
      `rejection_codes`, plus the existing `candidates`, `explored_states`,
      `truncated`, `model_identity`.
- [ ] Update `HybridRuntime.process()` to consume `ProposalResult` consistently:
      use `proposal.program` for VERIFY, `proposal.output_refs` for receipts,
      `proposal.rejection_codes` for gap classification.
- [ ] Update `propose_and_verify()` to return the same `ProposalResult` (or a
      thin wrapper that exposes the same fields).
- [ ] Delete `_ProposeAndVerifyResult` if it's redundant.
- [ ] All existing tests that construct `ProposalResult` must still compile.

### 2.2 Make the bootstrap proposer use grounded candidates
- [ ] In `BootstrapProposer._enumerate_actions()` (proposal.py:459), replace
      the enumeration of **all** `legal._designation_targets` with only the
      candidates returned by `self._grounder.ground_text(text)`.
- [ ] Replace the enumeration of **all** `legal._operators` with only the
      operators compatible with the grounded candidates' semantic kinds and
      affordance profiles.
- [ ] The grounding result computed at proposal.py:140 must flow into the
      action enumeration. Currently it's computed and discarded.
- [ ] Add a test `test_bootstrap_proposer_uses_grounded_candidates` that
      verifies the proposer does not enumerate designation targets that are
      not grounded from the input text.

### 2.3 Make the neural proposer use grounded candidates
- [ ] In `NeuralSwitchProposer.propose()` (model.py:735), replace the
      all-targets legal action generation with grounded-candidate-constrained
      generation.
- [ ] The neural input encoder (`_encode_form_units`, model.py:128) must
      include open-class unit identity (e.g., a hash-based or index-based
      embedding of grounded designation candidates), not just 11 closed-class
      feature categories. Otherwise "mary teaches bob" and "john knows alice"
      produce identical encodings.
- [ ] Dynamic pointers must reference only grounded designation candidates,
      not all 25 authority targets.
- [ ] Add a test `test_neural_proposer_uses_grounded_candidates` that verifies
      the neural proposer's legal action set is bounded by grounding output.

### 2.4 Implement validation-calibrated abstention
- [ ] The neural proposer must produce a confidence score from the model
      (not from the gold label's epistemic status).
- [ ] Add a validation-set-calibrated threshold: the proposer abstains when
      model confidence is below the threshold.
- [ ] The threshold is tuned on the validation partition to maximize
      abstention precision at ≥0.95 recall.
- [ ] Add a test `test_neural_proposer_abstains_on_low_confidence` that
      verifies the proposer produces an abstention action when confidence is
      below threshold.

### 2.5 Gate
- [ ] `test_proposal_abi_consistency` passes
- [ ] `test_bootstrap_proposer_uses_grounded_candidates` passes
- [ ] `test_neural_proposer_uses_grounded_candidates` passes
- [ ] `test_neural_proposer_abstains_on_low_confidence` passes
- [ ] `test_real_runtime_smoke` passes (the runtime can now complete all six
      phases for "hello", "what is your name?", "open the door")
- [ ] All existing M2 tests still pass (or are rewritten under the new ABI)
- [ ] `git commit -m "repair: unify proposal ABI and ground the composer in real candidates"`

---

## Phase 3: Integrate M3 (Real Runtime Cognition)

**Goal:** Wire M3's cognition modules (evaluation, effect, realization,
epistemics, state, dialogue, learning) into the real runtime. No fixture
owners in acceptance tests.

### 3.1 Implement real EvaluationOwner
- [ ] Replace the fixture `_FixtureEvaluationOwner` (evaluation.py:314) with a
      real evaluation owner that:
  - Consumes the verified `SemanticSwitchProgram` and `VerificationResult`.
  - Produces a typed `EvaluationResult` based on the program's operator,
    role assignments, and epistemic admission.
  - Returns `status="resolved"` only when the program is verified and the
    epistemic placement admits the claim.
- [ ] Add a test `test_real_evaluation_owner` that verifies the evaluation
      owner produces correct decisions for designation, type, relation, state,
      and event programs.

### 3.2 Implement real EffectOwner
- [ ] Replace the fixture `_FixtureEffectOwner` (evaluation.py:321) with a
      real effect owner that:
  - Routes through `EffectGateway` (the only owner of world mutation).
  - Returns idempotent `EffectResult` receipts.
  - Rejects unverified decisions.
- [ ] Add a test `test_real_effect_owner` that verifies the effect owner
      executes only verified decisions and produces receipts.

### 3.3 Implement real RealizationOwner
- [ ] Replace the fixture `_NeuralRealizationOwner` wrapper with direct
      integration of `NeuralConstrainedRealizer` + `RealizationVerifier`.
  - The realizer must produce a `ResponseMeaning` from the exact decision,
    proof, blockers, effects, and obligation.
  - The verifier must check realization equivalence before recording focus.
- [ ] Add a test `test_real_realization_owner` that verifies the realizer
      produces equivalent surfaces for resolved cycles.

### 3.4 Wire cognition modules into the runtime
- [ ] `HybridRuntime` must use real `EpistemicAdmission`, `TransitionEngine`,
      `GoalArbiter`, `LearningCoordinator` — not fixtures.
- [ ] The runtime's `process()` must produce a `CycleResult` with real gap
      receipts from `GapClassifier` (not manufactured exceptions).
- [ ] Add a test `test_real_cognitive_loop` that processes a multi-turn
      conversation and verifies epistemic state, obligations, and learning
      obligations are tracked correctly.

### 3.5 Gate
- [ ] `test_real_evaluation_owner` passes
- [ ] `test_real_effect_owner` passes
- [ ] `test_real_realization_owner` passes
- [ ] `test_real_cognitive_loop` passes
- [ ] `test_real_runtime_smoke` still passes
- [ ] No acceptance test uses fixture owners
- [ ] `git commit -m "integrate: wire M3 cognition into the real runtime"`

---

## Phase 4: Regenerate M4 Data and Retrain

**Goal:** Regenerate episodes from reviewed semantic assertions (not bootstrap
selection), create genuine hard negatives, retrain with validation-based model
selection, and calibrate from model inference.

### 4.1 Repair episode generation
- [ ] In `episodes.py:689` (`build_episode`), replace the "pick first bootstrap
      candidate" logic with:
  1. Run the bootstrap proposer to get candidates.
  2. Validate each candidate against `case.semantic_assertions` (the reviewed
     assertions that already exist on `ScenarioCase`).
  3. Select the candidate that matches the reviewed assertions. If none
     match, mark the episode as `unresolved` with a typed gap.
  4. Never select the first candidate blindly.
- [ ] Add a test `test_episode_gold_matches_semantic_assertions` that verifies
      every generated episode's `selected_program` is consistent with its
      `case.semantic_assertions`.
- [ ] Regenerate `data/episodes/all.jsonl` and verify no episode has
      `op:designation` for "konnichiwa means hello" or `op:type` for "greet
      carol".

### 4.2 Repair hard negatives
- [ ] In `partitions.py:526` (`_make_hard_negative`), ensure exactly one
      field is genuinely mutated:
  - Surface text, program, scope, role, permission, or action order — not
    just metadata.
  - The mutation must produce a real verifier failure (run the verifier, not
    fabricate error strings).
- [ ] Author multiple independent lineages per gap kind so validation and test
      cover all 18 gap kinds and 6 repair owners.
- [ ] Add a test `test_hard_negatives_genuinely_mutate` that verifies each
      hard negative differs from its parent in at least one semantic field
      (not just metadata) and that the verifier produces the expected
      rejection.
- [ ] Regenerate `data/partitions/` and verify all 18 gap kinds appear in
      validation and test.

### 4.3 Repair calibration
- [ ] In `training.py:1523` (`_episode_confidence`, `_episode_correct`),
      replace the gold-label-based confidence with model inference:
  - Run the proposal model on each validation episode.
  - Compute model confidence from the model's output (logit/probability).
  - Compute correctness by comparing the model's predicted program to the
    gold program (semantic equivalence, not string equality).
  - Compute ECE from these model-derived confidences and correctness labels.
- [ ] The calibrated threshold must be consumed by the neural proposer for
      abstention.
- [ ] Add a test `test_calibration_uses_model_inference` that verifies the
      calibration JSON is derived from model predictions, not gold labels.

### 4.4 Retrain with validation-based model selection
- [ ] Train the proposal model with validation-based early stopping (not
      fixed epoch count).
- [ ] Train the realizer model with the same protocol.
- [ ] Select the checkpoint with best validation accuracy.
- [ ] Publish to `artifacts/proposal_release/` and `artifacts/realizer_release/`.
- [ ] Add a test `test_release_models_match_best_validation_checkpoint`.

### 4.5 Gate
- [ ] `test_episode_gold_matches_semantic_assertions` passes
- [ ] `test_hard_negatives_genuinely_mutate` passes
- [ ] `test_calibration_uses_model_inference` passes
- [ ] `test_release_models_match_best_validation_checkpoint` passes
- [ ] `test_real_runtime_smoke` still passes
- [ ] `git commit -m "regenerate: repair episodes, hard negatives, calibration, and retrain"`

---

## Phase 5: Rewrite M4 Task 4 Evaluation

**Goal:** Rewrite the evaluator around actual six-phase receipts, strict
semantic identity/program equivalence, per-case records, confidence intervals,
and measured limitation generation.

### 5.1 Rewrite EvaluationReport and Evaluator
- [ ] Replace the fixture EVALUATE/EFFECT owners (evaluation.py:314) with the
      real runtime's `process()` output.
- [ ] Measure every metric from runtime receipts, not gold labels:
  - `illegal_program_rejection`: run the verifier on illegal programs and
    count actual rejections.
  - `effect_safety_accuracy`: run the effect owner and check actual receipts.
  - `exact_program_accuracy`: compare the proposer's predicted program to the
    gold program using semantic structural equivalence (not anonymized
    target identity).
  - `end_to_end_accuracy`: the full `process()` produces the correct
    `CycleResult` status and response meaning.
  - `abstention_precision/recall`: the proposer abstains on unknown inputs and
    accepts on known inputs, measured from model confidence vs. threshold.
  - `expected_calibration_error`: from model-derived confidences, not gold
    labels.
  - `realization_equivalence`: the realizer produces equivalent surfaces,
    verified by `RealizationVerifier`.
  - Zero-weight ablation: run the runtime with `with_zeroed_proposal_weights()`
    and `with_zeroed_realizer_weights()` and measure accuracy drop.
  - `bootstrap_delegate_calls`: instrument the runtime to count bootstrap
    delegate calls (must be 0 in release).
  - `unreviewed_atom_creations`: instrument the runtime to count implicit atom
    creations (must be 0).
  - `raw_surface_dispatches`: instrument the runtime to count raw surface
    dispatches (must be 0).
- [ ] Add per-case records: each test episode gets a record with the predicted
      program, gold program, match status, gap receipt, and all measured
      sub-metrics.
- [ ] Add bootstrap confidence intervals for each aggregate metric.

### 5.2 Generate LIMITATIONS.md from measured failures
- [ ] The evaluator must produce `artifacts/evaluation/LIMITATIONS.md` from
      the actual failure cases, not from a static template.
- [ ] For each failing case, document: the input, the expected program, the
      predicted program, the gap kind, and the root cause classification.

### 5.3 Gate
- [ ] All release thresholds from `test_release_thresholds` are met:
  - `illegal_program_rejection == 1.0`
  - `effect_safety_accuracy == 1.0`
  - `exact_program_accuracy >= 0.90`
  - `end_to_end_accuracy >= 0.95`
  - `abstention_precision >= 0.95`
  - `abstention_recall >= 0.95`
  - `expected_calibration_error <= 0.08`
  - `realization_equivalence == 1.0`
  - `proposal_zero_weight_accuracy <= 0.50`
  - `proposal_weight_accuracy_drop >= 0.30`
  - `realizer_zero_weight_accuracy <= 0.50`
  - `realizer_weight_accuracy_drop >= 0.30`
  - `bootstrap_delegate_calls == 0`
  - `unreviewed_atom_creations == 0`
  - `raw_surface_dispatches == 0`
- [ ] `LIMITATIONS.md` is generated from measured failures
- [ ] `git commit -m "evaluate: rewrite evaluator around real six-phase receipts"`

---

## Phase 6: Full Regression and Milestone Close

**Goal:** Run the complete test suite, verify no regressions, and close M4.

### 6.1 Full regression
- [ ] `python -m pytest -q` — zero failures, zero skips, zero xfails
- [ ] `python scripts/evaluate_cemm.py` produces a passing evaluation report
- [ ] `python scripts/reproduce_models.py` produces byte-identical artifacts

### 6.2 Update acceptance receipts
- [ ] Generate new `MILESTONE_RECEIPT.json` with real-runtime verification
- [ ] Generate new `M2_PROPOSAL_RECEIPT.json` and `M3_MILESTONE_RECEIPT.json`
- [ ] All receipts must show `profile: "release"` and verify the real owner
      graph

### 6.3 Commit and close
- [ ] `git commit -m "close: M4 corrective replay complete with real-runtime acceptance"`
- [ ] Update `hybrid_mvp/INTEGRATION.md` with the new status

---

## Risk Register

| Risk | Mitigation |
|------|------------|
| Repairing the proposer changes the legal action space, breaking existing tests | Rewrite tests under the new ABI; do not weaken gates |
| Neural input encoding changes require retraining | Phase 4 retrains after Phase 2 changes are stable |
| Real runtime integration reveals more M3 issues | Phase 3 is iterative; fix issues as they surface |
| Evaluation thresholds may not be met after repair | If thresholds fail, investigate root cause; do not lower thresholds |

## Ordering Constraints

```
Phase 0 → Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6
```

No phase begins until the previous phase's gate passes. The
`test_real_runtime_smoke` test is the canary: it should fail after Phase 0,
start passing after Phase 2, and remain passing through Phase 6.
