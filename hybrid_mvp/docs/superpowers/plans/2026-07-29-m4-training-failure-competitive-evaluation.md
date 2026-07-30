# Milestone 4 Training, Failure Coverage, and Competitive Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for every task and superpowers:verification-before-completion before the milestone commit. Track work with the checkboxes below.

**Goal:** Produce leakage-controlled semantic episodes, trained proposal and realization artifacts, calibrated safe failure behavior, and an honest same-hardware comparison with Qwen2.5-1.5B-Instruct.

**Architecture:** Reviewed scenarios specify semantic expectations; deterministic generators expand controlled surface/structural variation; lineage-aware partitioning seals evaluation; trainers consume train only; calibration consumes validation only; CEMM and Qwen receive the same sealed inputs and exact output contract. Measurement receipts, not aspiration, determine release and competitiveness claims.

**Tech Stack:** Python 3.13, PyTorch, safetensors, SQLite, canonical JSON/JSONL, pytest, Hypothesis, Hugging Face Transformers for the isolated baseline profile.

---

### Task 1: Define and validate complete Semantic Episodes and the 210-scenario source

**Files:**
- Create: `src/cemm_authoritative_hybrid/episodes.py`
- Create: `data/scenarios/use_cases.jsonl`
- Create: `data/scenarios/SCENARIO_COVERAGE.md`
- Create: `schemas/semantic_episode.schema.json`
- Create: `schemas/training_source.schema.json`
- Create: `scripts/build_episodes.py`
- Create: `data/episodes/all.jsonl`
- Create: `tests/test_semantic_episode.py`
- Create: `tests/test_scenario_coverage.py`

- [ ] **Step 1: Write failing completeness and deterministic-identity tests**

```python
def test_episode_contains_every_phase_and_revision(reviewed_episode):
    assert reviewed_episode.orientation
    assert reviewed_episode.legal_proposals
    assert reviewed_episode.rejected_proposals
    assert reviewed_episode.selected_program
    assert reviewed_episode.coverage
    assert reviewed_episode.evaluation
    assert reviewed_episode.effect_or_no_effect
    assert reviewed_episode.response_meaning
    assert reviewed_episode.realization_receipt
    assert reviewed_episode.authority_hash and reviewed_episode.action_encoding_hash

def test_scenario_source_has_210_unique_reviewed_cases(load_scenarios):
    scenarios = load_scenarios()
    assert len(scenarios) == 210
    assert len({case.scenario_ref for case in scenarios}) == 210
    assert all(case.review_status == "reviewed" for case in scenarios)

def test_episode_generation_is_byte_deterministic(tmp_path, builder):
    left, right = tmp_path / "left.jsonl", tmp_path / "right.jsonl"
    builder(left, seed=1701); builder(right, seed=1701)
    assert left.read_bytes() == right.read_bytes()
```

- [ ] **Step 2: Run and confirm current cases are transcript-oriented**

Run: `python -m pytest tests/test_semantic_episode.py tests/test_scenario_coverage.py -v`

Expected: FAIL until exact phase artifacts and scenario coverage exist.

- [ ] **Step 3: Implement the episode contract**

`SemanticEpisode` serializes all six-phase inputs/outputs, legal and rejected alternatives, typed verifier errors, exact proof/placement/effect, response semantics, accepted/rejected realizations, gap receipt, revisions, hashes, generator lineage, and review provenance. Schema validation rejects missing no-effect markers and unknown ABI versions.

Training sources are typed as `reviewed_scenario`, `authority_derived`, `human_paraphrase`, `teacher_paraphrase`, or `verified_correction`. Human/teacher language is untrusted evidence: it may become an episode only when paired with an already reviewed semantic target and independently re-verified. It never creates an atom, rule, frame, policy, or transition. This same import contract supports later large corpora without changing semantic authority ownership.

- [ ] **Step 4: Author the scenario matrix by semantic competency**

The 210 cases cover designation/definition, reordered constructions, polysemy, modality, negation/scope, recursive family proof, participant/reference, reported speech, temporal state, reviewed sensor/operation evidence, transition simulation, learning/security, capability/policy/adapter/effect, contradiction, every gap kind, multilingual aliases, adversarial programs, restart, and realization equivalence. Each case specifies semantic assertions rather than exact prose.

- [ ] **Step 5: Generate, validate, and commit**

```powershell
python scripts\build_episodes.py --scenarios data\scenarios\use_cases.jsonl --output data\episodes\all.jsonl --seed 1701
python -m pytest tests\test_semantic_episode.py tests\test_scenario_coverage.py -v
git add src\cemm_authoritative_hybrid\episodes.py schemas\semantic_episode.schema.json schemas\training_source.schema.json data\scenarios data\episodes\all.jsonl scripts\build_episodes.py tests\test_semantic_episode.py tests\test_scenario_coverage.py
git commit -m "data: define reviewed semantic episodes"
```

### Task 2: Seal lineage-aware partitions, hard negatives, and gap coverage

**Files:**
- Create: `src/cemm_authoritative_hybrid/partitions.py`
- Create: `configs/partitions.json`
- Create: `scripts/partition_episodes.py`
- Create: `data/partitions/manifest.json`
- Create: `data/partitions/train.jsonl`
- Create: `data/partitions/validation.jsonl`
- Create: `data/partitions/test.jsonl`
- Create: `tests/test_partition_leakage.py`
- Create: `tests/test_hard_negatives.py`
- Create: `tests/test_gap_episode_coverage.py`

- [ ] **Step 1: Write failing transitive-leakage tests**

```python
@pytest.mark.parametrize("lineage", [
    "normalized_text", "template", "lexical_value", "entity", "authority_target",
    "graph_topology", "dialogue", "adversarial_mutation",
])
def test_no_lineage_component_crosses_partitions(partitioned, lineage):
    groups = connected_lineage_components(partitioned.all, lineage)
    assert all(len({partitioned.partition_of(ref) for ref in group}) == 1 for group in groups)

def test_sealed_test_hash_is_not_available_to_training(partition_manifest, train_config):
    assert partition_manifest.test_sha256 not in canonical_text(train_config)
    assert partition_manifest.test_path not in canonical_text(train_config)

def test_every_gap_kind_has_positive_and_near_miss(gap_episodes):
    for kind in GapKind:
        assert gap_episodes.count(kind, "positive") >= 5
        assert gap_episodes.count(kind, "near_miss") >= 5
```

- [ ] **Step 2: Run and demonstrate naive random splitting leaks**

Run: `python -m pytest tests/test_partition_leakage.py tests/test_hard_negatives.py tests/test_gap_episode_coverage.py -v`

Expected: FAIL until transitive lineage components are partitioned atomically.

- [ ] **Step 3: Implement deterministic connected-component partitioning**

Build one graph joining episodes that share any protected lineage value. Assign whole connected components to train/validation/test using a seeded, stratified bin-packing algorithm. Emit immutable manifest hashes and counts. The test manifest is readable by evaluation only, never imported by training or calibration modules.

- [ ] **Step 4: Generate hard negatives and counterfactual pairs**

Mutate role, polarity, modality, source, tense, reference, effect permission, target kind, scope attachment, and action order one at a time. Retain the parent lineage. Exact verifier errors are labels; neural scores never determine truth. Add proposer-miss cases where a legal target exists and authority-gap cases where none exists.

- [ ] **Step 5: Partition and commit**

```powershell
python scripts\partition_episodes.py --input data\episodes\all.jsonl --config configs\partitions.json --output data\partitions
python -m pytest tests\test_partition_leakage.py tests\test_hard_negatives.py tests\test_gap_episode_coverage.py -v
git add src\cemm_authoritative_hybrid\partitions.py configs\partitions.json scripts\partition_episodes.py data\partitions tests\test_partition_leakage.py tests\test_hard_negatives.py tests\test_gap_episode_coverage.py
git commit -m "data: seal semantic evaluation partitions"
```

### Task 3: Train, calibrate, and publish reproducible proposal and realization models

**Files:**
- Rewrite: `src/cemm_authoritative_hybrid/training.py`
- Create: `configs/proposal_release.json`
- Create: `configs/realizer_release.json`
- Modify: `scripts/train_proposer.py`
- Modify: `scripts/train_realizer.py`
- Create: `scripts/calibrate_models.py`
- Create: `scripts/reproduce_models.py`
- Create: `artifacts/proposal_release/model_manifest.json`
- Create: `artifacts/proposal_release/model_metadata.json`
- Create: `artifacts/proposal_release/model.safetensors`
- Create: `artifacts/realizer_release/model_manifest.json`
- Create: `artifacts/realizer_release/model_metadata.json`
- Create: `artifacts/realizer_release/model.safetensors`
- Create: `artifacts/calibration.json`
- Create: `artifacts/validation/REPRODUCIBILITY.json`
- Create: `tests/test_training_isolation.py`
- Create: `tests/test_model_reproducibility.py`
- Create: `tests/test_calibration.py`

- [ ] **Step 1: Write failing isolation, pinning, and calibration tests**

```python
def test_trainer_cannot_open_validation_or_test(trainer, sealed_paths):
    with pytest.raises(PartitionAccessError):
        trainer.fit(sealed_paths.test)

def test_release_artifact_pins_all_semantic_inputs(release_metadata, manifests):
    assert release_metadata.authority_compatibility_hash == manifests.authority.compatibility_sha256
    assert release_metadata.action_encoding_hash == manifests.actions.sha256
    assert release_metadata.dataset_hash == manifests.train.sha256
    assert release_metadata.model_dependency_lock_sha256 == manifests.dependencies.model_sha256
    assert release_metadata.python_abi == manifests.environment.python_abi
    assert release_metadata.source_revision
    assert release_metadata.abi_registry == manifests.abis

def test_calibration_uses_validation_only(calibration_receipt, manifests):
    assert calibration_receipt.input_hash == manifests.validation.sha256
    assert calibration_receipt.expected_calibration_error <= 0.08

def test_model_uses_dynamic_semantic_slots_not_ref_spelling(release_metadata):
    assert release_metadata.target_encoding == "dynamic_pointer_slots"
    assert release_metadata.internal_ref_vocabulary == ()

def test_combined_trainable_capacity_is_bounded(release_models):
    assert sum(model.trainable_parameter_count for model in release_models) <= 50_000_000
```

- [ ] **Step 2: Run and confirm development artifacts are insufficient**

Run: `python -m pytest tests/test_training_isolation.py tests/test_model_reproducibility.py tests/test_calibration.py -v`

Expected: FAIL until data access and complete model identity are enforced.

- [ ] **Step 3: Implement deterministic trainers and receipts**

Set Python/PyTorch seeds, deterministic kernels where supported, fixed ordering, explicit device/dtype, gradient/parameter counts, early stopping from validation only, and canonical metric history. Record environment and dependency lock hashes. Proposal loss combines legal action sequence, dynamic pointer selection, and calibrated abstention; realization loss uses response-conditioned tokens, reviewed designation pointers, and semantic-preservation rejection pairs. Train/evaluate 10%, 25%, 50%, and 100% data curves with fixed partitions to measure minimal-data utility rather than infer it from the final score.

- [ ] **Step 4: Train and calibrate release artifacts**

```powershell
python scripts\train_proposer.py --config configs\proposal_release.json --episodes data\partitions\train.jsonl --output artifacts\proposal_release
python scripts\train_realizer.py --config configs\realizer_release.json --episodes data\partitions\train.jsonl --output artifacts\realizer_release
python scripts\calibrate_models.py --proposal artifacts\proposal_release --realizer artifacts\realizer_release --validation data\partitions\validation.jsonl --output artifacts\calibration.json
python scripts\reproduce_models.py --expected artifacts --temporary --receipt artifacts\validation\REPRODUCIBILITY.json
```

Expected: semantic metadata and evaluation outputs reproduce exactly; tensor identity reproduces in the locked same-environment profile. `--temporary` uses an OS temporary directory, verifies it is outside the repository, writes only the canonical receipt, and removes the scratch directory on success/failure. Any allowed device-level numeric variance is measured and must not change predictions or artifact acceptance.

- [ ] **Step 5: Run and commit**

```powershell
python -m pytest tests\test_training_isolation.py tests\test_model_reproducibility.py tests\test_calibration.py -v
git add src\cemm_authoritative_hybrid\training.py configs\proposal_release.json configs\realizer_release.json scripts\train_proposer.py scripts\train_realizer.py scripts\calibrate_models.py scripts\reproduce_models.py tests\test_training_isolation.py tests\test_model_reproducibility.py tests\test_calibration.py artifacts\proposal_release artifacts\realizer_release artifacts\calibration.json artifacts\validation\REPRODUCIBILITY.json
git commit -m "train: publish pinned hybrid models"
```

### Task 4: Evaluate semantic accuracy, gaps, safety, and limitations

**Files:**
- Create: `src/cemm_authoritative_hybrid/evaluation.py`
- Create: `scripts/evaluate_cemm.py`
- Create: `tests/test_evaluation_metrics.py`
- Create: `tests/test_gap_owner_evaluation.py`
- Create: `tests/test_release_thresholds.py`
- Create: `artifacts/evaluation/CEMM_EVALUATION.json`
- Create: `artifacts/evaluation/LIMITATIONS.md`

- [ ] **Step 1: Write failing metric and threshold tests**

```python
def test_release_thresholds(report):
    assert report.illegal_program_rejection == 1.0
    assert report.effect_safety_accuracy == 1.0
    assert report.exact_program_accuracy >= 0.90
    assert report.end_to_end_accuracy >= 0.95
    assert report.abstention_precision >= 0.95
    assert report.abstention_recall >= 0.95
    assert report.expected_calibration_error <= 0.08
    assert report.realization_equivalence == 1.0
    assert report.proposal_zero_weight_accuracy <= 0.50
    assert report.proposal_weight_accuracy_drop >= 0.30
    assert report.realizer_zero_weight_accuracy <= 0.50
    assert report.realizer_weight_accuracy_drop >= 0.30
    assert report.bootstrap_delegate_calls == 0
    assert report.unreviewed_atom_creations == 0
    assert report.raw_surface_dispatches == 0
```

- [ ] **Step 2: Run and ensure no metric is inferred from response-string equality**

Run: `python -m pytest tests/test_evaluation_metrics.py tests/test_gap_owner_evaluation.py tests/test_release_thresholds.py -v`

Expected: FAIL before semantic receipt scoring exists.

- [ ] **Step 3: Implement exact evaluation**

Score legal target recall, exact program/actions/roles/coverage, proof correctness, answer semantics, abstention, calibration, effect safety, learned designation reuse, realization preservation, and gap kind/owner/safe action. Preserve per-case records and bootstrap confidence intervals. A failed gate makes the report status `failed`; no weighted aggregate hides it.

- [ ] **Step 4: Generate limitations from measured failures**

Group failures by earliest phase, gap kind, and recommended owner. Generate `artifacts/evaluation/LIMITATIONS.md` from receipts, explicitly separating architecture/runtime defects, missing authority/data, proposal/realizer training gaps, policy denials, adapter absence, and declared unsupported competencies.

- [ ] **Step 5: Evaluate and commit**

```powershell
python scripts\evaluate_cemm.py --episodes data\partitions\test.jsonl --output artifacts\evaluation\CEMM_EVALUATION.json
python -m pytest tests\test_evaluation_metrics.py tests\test_gap_owner_evaluation.py tests\test_release_thresholds.py -v
git add src\cemm_authoritative_hybrid\evaluation.py scripts\evaluate_cemm.py tests\test_evaluation_metrics.py tests\test_gap_owner_evaluation.py tests\test_release_thresholds.py artifacts\evaluation
git commit -m "test: measure semantic MVP acceptance"
```

### Task 5: Run a fair frozen Qwen2.5-1.5B baseline

**Files:**
- Create: `benchmarks/qwen_baseline.py`
- Create: `benchmarks/fixed_prompt.txt`
- Create: `benchmarks/output_contract.schema.json`
- Create: `requirements-benchmark.lock`
- Create: `scripts/compare_baselines.py`
- Create: `tests/test_baseline_contract.py`
- Create: `tests/test_competitiveness_claim.py`
- Create: `artifacts/evaluation/QWEN_BASELINE.json`
- Create: `artifacts/evaluation/COMPETITIVE_EVALUATION.json`

- [ ] **Step 1: Write failing fairness and claim-policy tests**

```python
def test_baseline_uses_same_sealed_case_ids(cemm_report, qwen_report):
    assert cemm_report.case_refs == qwen_report.case_refs
    assert cemm_report.output_contract_hash == qwen_report.output_contract_hash

def test_competitiveness_claim_requires_all_conditions(comparison_factory):
    report = comparison_factory(cemm_accuracy=.95, qwen_accuracy=.96,
                                cemm_unsafe=0.0, qwen_unsafe=.01,
                                cemm_parameters=8_000_000, qwen_parameters=1_540_000_000)
    assert report.domain_competitiveness_claim == "supported"
    assert comparison_factory(cemm_accuracy=.89, qwen_accuracy=.96).domain_competitiveness_claim == "not_supported"
```

- [ ] **Step 2: Run and confirm no informal baseline can satisfy the contract**

Run: `python -m pytest tests/test_baseline_contract.py tests/test_competitiveness_claim.py -v`

Expected: FAIL until one immutable prompt/schema/model revision and comparison policy exist.

- [ ] **Step 3: Implement two isolated baseline tracks**

Pin `Qwen/Qwen2.5-1.5B-Instruct` revision, tokenizer, Transformers dependencies, generation arguments, fixed prompt, JSON schema, hardware, and seeds. For every case, serialize the same relevant reviewed authority slice, allowed semantic IDs/roles, participant/session facts, policy facts, and operation schema that CEMM can retrieve under its bounds; do not give Qwen hidden gold programs or proofs. Multi-turn cases carry the same admitted state and prior verified semantic content. Qwen emits decisions/programs into the shared schema and never directly invokes an adapter; the exact benchmark evaluator scores legality, proof, abstention, and effect safety. Track 1 is frozen zero/few-shot. Track 2 may use only the same train partition and is reported separately when hardware permits. Prompt/checkpoint selection uses train/validation only, never sealed test content, and the comparison uses the stronger valid baseline track.

- [ ] **Step 4: Run the same-hardware comparison**

```powershell
python benchmarks\qwen_baseline.py --model Qwen/Qwen2.5-1.5B-Instruct --prompt benchmarks\fixed_prompt.txt --episodes data\partitions\test.jsonl --output artifacts\evaluation\QWEN_BASELINE.json
python scripts\compare_baselines.py --cemm artifacts\evaluation\CEMM_EVALUATION.json --qwen artifacts\evaluation\QWEN_BASELINE.json --output artifacts\evaluation\COMPETITIVE_EVALUATION.json
```

If model acquisition or reference hardware is unavailable, emit a signed `baseline_unavailable` diagnostic and stop the milestone. It does not waive any absolute CEMM gate and cannot satisfy Milestone 4 or final release. The authoritative release comparison must contain measured frozen-baseline results.

- [ ] **Step 5: Run and commit**

```powershell
python -m pytest tests\test_baseline_contract.py tests\test_competitiveness_claim.py -v
git add benchmarks requirements-benchmark.lock scripts\compare_baselines.py tests\test_baseline_contract.py tests\test_competitiveness_claim.py artifacts\evaluation\QWEN_BASELINE.json artifacts\evaluation\COMPETITIVE_EVALUATION.json
git commit -m "bench: compare CEMM with frozen Qwen baseline"
```

### Task 6: Enforce performance bounds and close the milestone

**Files:**
- Create: `benchmarks/performance.py`
- Create: `configs/performance_reference.json`
- Create: `tests/test_operation_bounds.py`
- Create: `tests/test_performance_regression.py`
- Create: `artifacts/evaluation/PERFORMANCE.json`
- Modify: `scripts/validate_mvp.py`

- [ ] **Step 1: Write failing operation-count and regression tests**

```python
def test_normal_cycle_respects_declared_bounds(performance_cases, limits):
    for receipt in performance_cases:
        assert receipt.designation_candidates <= limits.max_designations_per_span * receipt.spans
        assert receipt.proposal_states <= limits.max_beam_states
        assert receipt.complete_candidates <= limits.max_complete_candidates
        assert receipt.graph_depth <= limits.max_graph_depth
        assert receipt.full_store_scans == 0

def test_over_ten_percent_regression_blocks_release(current, accepted):
    current.p95_ms = accepted.p95_ms * 1.101
    assert release_performance_status(current, accepted) == "failed"
```

- [ ] **Step 2: Run and expose uninstrumented scans/caches**

Run: `python -m pytest tests/test_operation_bounds.py tests/test_performance_regression.py -v`

Expected: FAIL until index probes, expansions, cache hits, time, memory, and throughput are measured.

- [ ] **Step 3: Benchmark CEMM and Qwen under one measurement policy**

Warm up identically; fix batches/threads; record CPU/GPU model, RAM, dependency versions, p50/p95, throughput, peak resident/device memory, artifact bytes, parameters, and training examples. Trace serialization is disabled and verified not to change semantic results. Claim efficiency only when both latency and peak memory are lower on the shared setup.

- [ ] **Step 4: Run the full milestone gate**

```powershell
python benchmarks\performance.py --cemm artifacts --qwen Qwen/Qwen2.5-1.5B-Instruct --episodes data\partitions\test.jsonl --output artifacts\evaluation\PERFORMANCE.json
python -m pytest -q
python scripts\validate_mvp.py --profile milestone-4 --output artifacts\validation\MILESTONE_RECEIPT.json
git diff --check
```

Expected: all absolute semantic/safety thresholds pass, no >10% unapproved CEMM regression exists, and comparative claims match measured receipts exactly.

- [ ] **Step 5: Commit the milestone**

```powershell
git add benchmarks\performance.py configs\performance_reference.json tests\test_operation_bounds.py tests\test_performance_regression.py scripts\validate_mvp.py artifacts\evaluation artifacts\validation\MILESTONE_RECEIPT.json
git commit -m "feat: train and benchmark the hybrid MVP"
git status --short
```

Expected: clean working tree with immutable CEMM, Qwen, comparison, performance, and milestone receipts.
