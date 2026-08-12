# Hybrid MVP R4 Final Admission Closeout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce an authentic, deterministic, externally reviewed R4 artifact graph, admit R4 green on the preserved corrective-replay lineage, and merge the complete G0–R4 ancestry into `main` without history rewriting.

**Architecture:** Continue from `0a52bd6` and repair the earliest semantic owners exposed by an independent 400-case expected/observed comparison. Keep expected contracts independent, execute every accepted episode and mutation through authentic owners, generate the complete artifact graph twice, require external review, then use the existing validation and append-only governance owners for admission and integration.

**Tech Stack:** Python 3.13, pytest 8, immutable dataclasses, canonical JSON/JSONL, SQLite-backed `HybridRuntime`, Git/GitHub Actions, existing CEMM governance and validation CLIs.

---

## Starting evidence

Run from `hybrid_mvp/`:

```powershell
python scripts/update_replay_status.py --verify-chain
python scripts/validate_mvp.py --tier phase --phase R3
python scripts/validate_mvp.py --tier phase --phase R4
```

Expected starting results:

```text
G0=green R1=green R2=green R3=green R4=red
R3 phase: passed
R4 phase: pytest_test_failure
```

The read-only public-runtime diagnostic at `6ae360a` produced:

```text
TOTAL=400 PASSED=22 FAILED=358 ERRORS=20
comparison:gap        347
comparison:decision   299
comparison:effect     299
comparison:response   299
comparison:expression 271
comparison:situation   10
restart executor errors 20
```

This ordering is the repair order. Downstream decision/effect/response mismatches
are not fixed before the expression/gap owner is correct.

## File map

- `tests/test_episode_generation_hard_cut.py` — diagnostic Episode ABI 2 contract.
- `tests/test_r4_closeout_regressions.py` — authentic reviewed-family runtime canaries.
- `tests/test_r4_authentic_episodes.py` — committed corpus integrity.
- `tests/test_r4_environment.py` — authentic build environment and restart/mutation owner tests.
- `tests/test_r4_admission.py` — deterministic artifact/review/admission reconstruction tests.
- `src/cemm_authoritative_hybrid/grounding.py` — designation/reference grounding.
- `src/cemm_authoritative_hybrid/proposal_context.py` — typed contribution slots.
- `src/cemm_authoritative_hybrid/recursive_composer/_core.py` — graph unit legality.
- `src/cemm_authoritative_hybrid/recursive_composer/_expand.py` — multi-unit graph expansion.
- `src/cemm_authoritative_hybrid/recursive_composer/_search.py` — bounded chart search.
- `src/cemm_authoritative_hybrid/proposal.py` — program candidate construction.
- `src/cemm_authoritative_hybrid/verifier.py` — exact program-to-expression verification.
- `src/cemm_authoritative_hybrid/r3_cognition.py` — expression-only decisions and gaps.
- `src/cemm_authoritative_hybrid/r3_effects.py` — authentic effect/no-effect behavior.
- `src/cemm_authoritative_hybrid/r3_response.py` — response meaning from exact decisions.
- `src/cemm_authoritative_hybrid/r4_environment.py` — committed authentic factory, restart executor, and mutation executor.
- `scripts/diagnose_r4_cases.py` — bounded owner-classified 400-case report.
- `scripts/build_r4_artifacts.py` — deterministic pipeline entrypoint.
- `src/cemm_authoritative_hybrid/r4_admission.py` — exact artifact/review reconstruction.
- `configs/validation_gates.json` — governed nodes and R4 gate topology.
- `governance/test_inventory.json` and `artifacts/validation/TEST_INVENTORY_RECEIPT.json` — refreshed literal test metadata.
- `artifacts/r4/**` — deterministic admitted artifact graph.
- `data/review/R4_REVIEW_MANIFEST.json` — externally produced exact review authorization.
- `governance/replay_status.jsonl` — append-only R4 green transition.

### Task 1: Align the diagnostic Episode ABI 2 assertion

**Files:**
- Modify: `tests/test_episode_generation_hard_cut.py`
- Modify: `governance/test_inventory.json`
- Modify: `artifacts/validation/TEST_INVENTORY_RECEIPT.json`

- [ ] **Step 1: Change the stale test into a failing derivation-lineage separation test**

Replace the empty-proposal assertion with exact checks that proposals remain
diagnostic lineage while no settled or later-owner artifacts are claimed:

```python
def test_episode_abi2_r1_shape_preserves_derivation_lineage_without_later_truth(
    diagnostic_episode,
):
    assert diagnostic_episode.orientation
    assert diagnostic_episode.legal_proposals
    assert all(
        row["artifact_role"] == "derivation_lineage"
        for row in diagnostic_episode.legal_proposals
    )
    assert diagnostic_episode.selected_program == {}
    assert diagnostic_episode.verified_meaning == {}
    assert diagnostic_episode.coverage == {}
    assert diagnostic_episode.evaluation == {}
    assert diagnostic_episode.effect_or_no_effect == {"status": "not_admitted"}
    assert diagnostic_episode.response_meaning == {}
    assert diagnostic_episode.realization_receipt == {}
    assert diagnostic_episode.training_source["independently_reverified"] is False
```

- [ ] **Step 2: Run the renamed test before metadata refresh**

Run:

```powershell
python -m pytest tests/test_episode_generation_hard_cut.py -q -p no:cacheprovider
```

Expected: semantic assertions pass, but inventory verification reports the
renamed node or AST digest as stale.

- [ ] **Step 3: Refresh and verify literal metadata**

Run:

```powershell
python scripts/refresh_r3_r4_test_metadata.py
python scripts/verify_r3_r4_test_metadata.py
python scripts/check_test_inventory.py --phase G0 --source-only
```

Expected: all commands exit 0 and the inventory binds the renamed node and new
AST digest.

- [ ] **Step 4: Run the R4 phase to prove only corpus work remains**

Run:

```powershell
python scripts/validate_mvp.py --tier phase --phase R4
```

Expected: failure is limited to the three missing committed-corpus assertions.

- [ ] **Step 5: Commit the ABI alignment**

```powershell
git add tests/test_episode_generation_hard_cut.py governance/test_inventory.json artifacts/validation/TEST_INVENTORY_RECEIPT.json
git commit -m "test(r4): align diagnostic episode lineage contract"
```

### Task 2: Add the bounded authentic-case diagnostic owner

**Files:**
- Create: `scripts/diagnose_r4_cases.py`
- Create: `tests/test_r4_case_diagnostics.py`
- Modify: `configs/validation_gates.json`
- Modify: `governance/test_inventory.json`
- Modify: `artifacts/validation/TEST_INVENTORY_RECEIPT.json`

- [ ] **Step 1: Write failing tests for exact report shape and deterministic counts**

```python
def test_report_groups_by_earliest_comparison_owner(tmp_path):
    report = diagnose_cases(ROOT, store_root=tmp_path)
    assert report["schema"] == "cemm-r4-case-diagnostic-v1"
    assert report["case_count"] == 400
    assert report["counts"]["passed"] + report["counts"]["failed"] + report["counts"]["errors"] == 400
    assert set(report["mismatch_counts"]) <= {
        "expression", "situation", "decision", "effect", "response", "gap", "environment"
    }


def test_report_is_byte_deterministic(tmp_path):
    first = canonical_report_bytes(diagnose_cases(ROOT, store_root=tmp_path / "a"))
    second = canonical_report_bytes(diagnose_cases(ROOT, store_root=tmp_path / "b"))
    assert first == second
```

- [ ] **Step 2: Run the focused tests and observe the missing module**

```powershell
python -m pytest tests/test_r4_case_diagnostics.py -q -p no:cacheprovider
```

Expected: FAIL because `scripts.diagnose_r4_cases` does not exist.

- [ ] **Step 3: Implement the diagnostic without semantic branching**

Implement public functions with these signatures:

```python
def diagnose_cases(project_root: Path, *, store_root: Path) -> dict[str, object]: ...
def canonical_report_bytes(report: Mapping[str, object]) -> bytes: ...
```

The implementation must:

- load reviewed scenarios and independent expected contracts;
- execute non-restart cases through `load_runtime(...).create_evidence()` and
  `.process_evidence()` via `PublicRuntimeEpisodeOwner`;
- classify only existing `ComparisonReceipt.mismatch_codes` and typed executor
  exceptions;
- close all runtime stores in `finally`;
- cap stored examples at eight per mismatch code; and
- never inspect a surface string to decide meaning or ownership.

- [ ] **Step 4: Run tests and the full diagnostic twice**

```powershell
python -m pytest tests/test_r4_case_diagnostics.py -q -p no:cacheprovider
python scripts/diagnose_r4_cases.py --store-root "$env:TEMP\cemm-r4-diag-a" --output "$env:TEMP\cemm-r4-a.json"
python scripts/diagnose_r4_cases.py --store-root "$env:TEMP\cemm-r4-diag-b" --output "$env:TEMP\cemm-r4-b.json"
Get-FileHash "$env:TEMP\cemm-r4-a.json","$env:TEMP\cemm-r4-b.json"
```

Expected: tests pass, both commands exit 0, hashes match, and starting counts are
400 total / 22 passed / 358 failed / 20 restart-owner errors.

- [ ] **Step 5: Register the diagnostic owner and commit**

Add its tests to the `expected-contract` R4 owner step, refresh metadata, then:

```powershell
git add scripts/diagnose_r4_cases.py tests/test_r4_case_diagnostics.py configs/validation_gates.json governance/test_inventory.json artifacts/validation/TEST_INVENTORY_RECEIPT.json
git commit -m "test(r4): add deterministic authentic-case diagnostics"
```

### Task 3: Close designation, definition, state, and relation composition

**Files:**
- Modify: `tests/test_r4_closeout_regressions.py`
- Modify as proved by the trace: `src/cemm_authoritative_hybrid/grounding.py`
- Modify as proved by the trace: `src/cemm_authoritative_hybrid/proposal_context.py`
- Modify as proved by the trace: `src/cemm_authoritative_hybrid/recursive_composer/_core.py`
- Modify as proved by the trace: `src/cemm_authoritative_hybrid/recursive_composer/_expand.py`
- Modify as proved by the trace: `src/cemm_authoritative_hybrid/recursive_composer/_search.py`
- Modify as proved by the trace: `src/cemm_authoritative_hybrid/proposal.py`
- Modify as proved by the trace: `src/cemm_authoritative_hybrid/verifier.py`
- Modify: `governance/test_inventory.json`
- Modify: `artifacts/validation/TEST_INVENTORY_RECEIPT.json`

- [ ] **Step 1: Add failing public-runtime family canaries**

Add parameterized canaries using reviewed scenario refs rather than inline
expected semantics:

```python
@pytest.mark.parametrize(
    "scenario_ref",
    (
        "scenario:designation_definition-0003",
        "scenario:designation_definition-0004",
        "scenario:designation_definition-0006",
        "scenario:designation_definition-0010",
        "scenario:designation_definition-0012",
        "scenario:designation_definition-0013",
        "scenario:designation_definition-0014",
        "scenario:reordered_constructions-0021",
        "scenario:reordered_constructions-0022",
        "scenario:temporal_state-0089",
        "scenario:temporal_state-0091",
    ),
)
def test_reviewed_nominal_state_relation_families_match_authentic_cycles(
    scenario_ref, tmp_path
):
    episodes = authentic_episodes_for_scenario(scenario_ref, tmp_path)
    assert episodes
    assert all(row.comparison.passed for row in episodes)
```

- [ ] **Step 2: Run the canaries and capture Stage PROPOSE/VERIFY traces**

```powershell
python -m pytest tests/test_r4_closeout_regressions.py -k nominal_state_relation -q -p no:cacheprovider --tb=long
```

Expected: FAIL. For each failure, record the earliest absent or invalid artifact:
designation candidate, contribution, chart graphlet, complete proposal,
verification selection, or typed gap.

- [ ] **Step 3: Implement only the earliest proven owner changes**

Required semantic behavior:

- exact reviewed designation lookup accepts determiner-bearing full spans only
  when their form analysis and explicit target authority cover every source unit;
- concept targets can provide bounded nominal/type predicate contributions;
- state values and dimensions bind one `op:state` graph with explicit subject,
  dimension, and value roles;
- relation predicates bind subject/object contributions in either reviewed word
  order through typed roles, not token position;
- definition queries compose through reviewed query/scope contributions;
- every source unit is consumed exactly once or retained as one typed residual;
- no literal surface, regex, target-ref spelling, or default-to-concept branch is
  introduced.

- [ ] **Step 4: Run focused, owner, predecessor, and diagnostic gates**

```powershell
python -m pytest tests/test_r4_closeout_regressions.py -k nominal_state_relation -q -p no:cacheprovider
python scripts/validate_mvp.py --tier owner --phase R4 --owner expected-contract
python scripts/validate_mvp.py --tier phase --phase R3
python scripts/diagnose_r4_cases.py --store-root "$env:TEMP\cemm-r4-diag-task3" --output "$env:TEMP\cemm-r4-task3.json"
```

Expected: canaries and gates pass; the diagnostic passed count strictly increases
and no previously passing case becomes failed or errored.

- [ ] **Step 5: Refresh metadata and commit**

```powershell
python scripts/refresh_r3_r4_test_metadata.py
python scripts/verify_r3_r4_test_metadata.py
git add tests/test_r4_closeout_regressions.py src/cemm_authoritative_hybrid governance/test_inventory.json artifacts/validation/TEST_INVENTORY_RECEIPT.json
git commit -m "fix(r4): compose reviewed designation state and relation families"
```

### Task 4: Close recursive scope, modality, speech, learning, and inference families

**Files:**
- Modify: `tests/test_r4_closeout_regressions.py`
- Modify as proved by trace: `src/cemm_authoritative_hybrid/recursive_composer/_expand.py`
- Modify as proved by trace: `src/cemm_authoritative_hybrid/recursive_composer/_search.py`
- Modify as proved by trace: `src/cemm_authoritative_hybrid/expression_projection.py`
- Modify as proved by trace: `src/cemm_authoritative_hybrid/r3_cognition.py`
- Modify as proved by trace: `src/cemm_authoritative_hybrid/r3_learning.py`
- Modify as proved by trace: `src/cemm_authoritative_hybrid/r3_response.py`
- Modify: `governance/test_inventory.json`
- Modify: `artifacts/validation/TEST_INVENTORY_RECEIPT.json`

- [ ] **Step 1: Add failing reviewed-family canaries**

```python
@pytest.mark.parametrize(
    "scenario_ref",
    (
        "scenario:negation_scope-0047",
        "scenario:modality-0037",
        "scenario:reported_speech-0085",
        "scenario:learning_security-0119",
        "scenario:recursive_family_proof-0059",
        "scenario:participant_reference-0078",
        "scenario:contradiction-0143",
    ),
)
def test_reviewed_recursive_scope_families_match_authentic_cycles(
    scenario_ref, tmp_path
):
    episodes = authentic_episodes_for_scenario(scenario_ref, tmp_path)
    assert episodes
    assert all(row.comparison.passed for row in episodes)
```

- [ ] **Step 2: Run the canaries and locate the first divergent graph/app ref**

```powershell
python -m pytest tests/test_r4_closeout_regressions.py -k recursive_scope -q -p no:cacheprovider --tb=long
```

Expected: FAIL with exact expression/gap/decision mismatches.

- [ ] **Step 3: Implement the minimal reviewed-frame composition**

The implementation must use:

- candidate-local application refs for proposition-taking frame roles;
- explicit scope nodes for polarity and modality;
- reviewed actor/content/addressee roles for speech and learning events;
- `LearningPlan` ABI 2 only after the exact query/decision owner authorizes it;
- bounded proof/query traversal for recursive definitions and inference; and
- conflict-preserving exact decisions for contradiction cases.

No sentence-family dispatch or surface-string selection is permitted.

- [ ] **Step 4: Run focused, R3 owner, R3 phase, and diagnostic verification**

```powershell
python -m pytest tests/test_r4_closeout_regressions.py -k recursive_scope -q -p no:cacheprovider
python scripts/validate_mvp.py --tier owner --phase R3 --owner decision-query-proof
python scripts/validate_mvp.py --tier owner --phase R3 --owner learning-response
python scripts/validate_mvp.py --tier phase --phase R3
python scripts/diagnose_r4_cases.py --store-root "$env:TEMP\cemm-r4-diag-task4" --output "$env:TEMP\cemm-r4-task4.json"
```

Expected: gates pass and the authentic pass count strictly increases without a
regression in the prior task’s families.

- [ ] **Step 5: Refresh metadata and commit**

```powershell
python scripts/refresh_r3_r4_test_metadata.py
python scripts/verify_r3_r4_test_metadata.py
git add tests/test_r4_closeout_regressions.py src/cemm_authoritative_hybrid governance/test_inventory.json artifacts/validation/TEST_INVENTORY_RECEIPT.json
git commit -m "fix(r4): close recursive scope and cognition families"
```

### Task 5: Implement authentic restart and mutation execution owners

**Files:**
- Create: `src/cemm_authoritative_hybrid/r4_environment.py`
- Create: `tests/test_r4_environment.py`
- Modify: `scripts/build_r4_artifacts.py`
- Modify: `configs/validation_gates.json`
- Modify: `governance/test_inventory.json`
- Modify: `artifacts/validation/TEST_INVENTORY_RECEIPT.json`

- [ ] **Step 1: Write failing owner tests**

```python
def test_environment_factory_returns_exact_committed_owners(tmp_path):
    environment = build_environment(ROOT, tmp_path)
    assert environment["source_revision"] == admitted_source_for_phase(ROOT, "R3")
    assert callable(environment["runtime_factory"])
    assert hasattr(environment["restart_executor"], "execute_restart_case")
    assert hasattr(environment["mutation_owner"], "execute_mutation")


def test_restart_executor_reopens_persistent_state_and_emits_cycle_result(tmp_path):
    case = reviewed_restart_case(ROOT)
    owner = AuthenticRestartExecutor(ROOT, tmp_path)
    result = owner.execute_restart_case(case, session_ref="session:r4-restart")
    assert type(result) is EpisodeExecutionResult
    assert type(result.cycle) is CycleResult
    assert result.cycle.gap_receipt is not None


def test_mutation_owner_reports_observed_boundary_not_expected_labels(tmp_path):
    mutation = reviewed_mutation(ROOT)
    owner = AuthenticMutationOwner(ROOT, tmp_path)
    result = owner.execute_mutation(mutation)
    assert type(result) is MutationBoundaryResult
    assert result.artifact_ref != mutation.mutation_ref
```

- [ ] **Step 2: Run tests and observe the missing environment owner**

```powershell
python -m pytest tests/test_r4_environment.py -q -p no:cacheprovider
```

Expected: FAIL because `r4_environment.py` does not exist.

- [ ] **Step 3: Implement exact owners**

Implement:

```python
def admitted_source_for_phase(project_root: Path, phase: str) -> str: ...
def build_environment(project_root: Path, output_root: Path) -> Mapping[str, object]: ...

class AuthenticRestartExecutor:
    def execute_restart_case(
        self, case: ExpandedCase, *, session_ref: str
    ) -> EpisodeExecutionResult: ...

class AuthenticMutationOwner:
    def execute_mutation(self, mutation: SemanticMutation) -> MutationBoundaryResult: ...
```

`admitted_source_for_phase()` must reconstruct the append-only ledger through
the existing governance verifier and return the `source_base` of the last
effective green record for the exact requested phase; it must reject a missing,
red, invalidated, or malformed phase record.

The restart owner must close the original stores, reopen from the same persistent
path, execute through public runtime methods, and return exact cycle evidence.
The mutation owner must decode the mutated artifact and call the owning compiler,
expression validator, EVALUATE gate, or EFFECT CAS path. It must derive owner,
status, and error code from the observed exception/receipt, never copy
`expected_*` fields.

- [ ] **Step 4: Run tests and a 400-case diagnostic with the restart owner**

```powershell
python -m pytest tests/test_r4_environment.py -q -p no:cacheprovider
python scripts/diagnose_r4_cases.py --environment cemm_authoritative_hybrid.r4_environment:build_environment --store-root "$env:TEMP\cemm-r4-diag-task5" --output "$env:TEMP\cemm-r4-task5.json"
```

Expected: environment tests pass and diagnostic executor errors are zero.

- [ ] **Step 5: Register nodes, refresh metadata, and commit**

```powershell
python scripts/refresh_r3_r4_test_metadata.py
python scripts/verify_r3_r4_test_metadata.py
git add src/cemm_authoritative_hybrid/r4_environment.py tests/test_r4_environment.py scripts/build_r4_artifacts.py configs/validation_gates.json governance/test_inventory.json artifacts/validation/TEST_INVENTORY_RECEIPT.json
git commit -m "feat(r4): add authentic build execution owners"
```

### Task 6: Reach exact 400-case semantic agreement

**Files:**
- Modify only earliest owners identified by `scripts/diagnose_r4_cases.py`
- Modify: `tests/test_r4_closeout_regressions.py`
- Modify: `governance/test_inventory.json`
- Modify: `artifacts/validation/TEST_INVENTORY_RECEIPT.json`

- [ ] **Step 1: Run the diagnostic and select the largest remaining earliest-owner family**

```powershell
python scripts/diagnose_r4_cases.py --environment cemm_authoritative_hybrid.r4_environment:build_environment --store-root "$env:TEMP\cemm-r4-diag-next" --output "$env:TEMP\cemm-r4-next.json"
Get-Content "$env:TEMP\cemm-r4-next.json"
```

Expected: a canonical report with a nonempty ordered mismatch count unless all
400 cases already pass.

- [ ] **Step 2: Add one failing parameterized canary for that semantic family**

Use reviewed scenario refs from the report:

```python
def test_every_reviewed_scenario_matches_authentic_cycles(tmp_path):
    mismatches = []
    for scenario in load_reviewed_scenarios(SCENARIOS):
        episodes = authentic_episodes_for_scenario(scenario.scenario_ref, tmp_path)
        mismatches.extend(
            (episode.expanded_case.case_ref, episode.comparison.mismatch_codes)
            for episode in episodes
            if not episode.comparison.passed
        )
    assert mismatches == []
```

- [ ] **Step 3: Run the canary, fix only the traced owner, and rerun gates**

```powershell
python -m pytest tests/test_r4_closeout_regressions.py -k every_reviewed_scenario -q -p no:cacheprovider --tb=long
python scripts/validate_mvp.py --tier phase --phase R3
python scripts/diagnose_r4_cases.py --environment cemm_authoritative_hybrid.r4_environment:build_environment --store-root "$env:TEMP\cemm-r4-diag-after" --output "$env:TEMP\cemm-r4-after.json"
```

Expected: the focused canary and R3 phase pass, passed-case count increases, and
no earlier passing case regresses.

- [ ] **Step 4: Repeat Steps 1–3 until exact agreement**

The loop terminates only at:

```text
TOTAL=400 PASSED=400 FAILED=0 ERRORS=0
```

Expected contracts or reviewed scenario assertions may change only when the
diagnostic proves the independent compiler is inconsistent with the governing
semantic contract, not merely to match observed runtime output.

- [ ] **Step 5: Refresh metadata and commit each owner-scoped tranche**

For each family:

```powershell
python scripts/refresh_r3_r4_test_metadata.py
python scripts/verify_r3_r4_test_metadata.py
git add src/cemm_authoritative_hybrid/grounding.py src/cemm_authoritative_hybrid/proposal_context.py src/cemm_authoritative_hybrid/recursive_composer/_core.py src/cemm_authoritative_hybrid/recursive_composer/_expand.py src/cemm_authoritative_hybrid/recursive_composer/_search.py src/cemm_authoritative_hybrid/proposal.py src/cemm_authoritative_hybrid/verifier.py src/cemm_authoritative_hybrid/expression_projection.py src/cemm_authoritative_hybrid/r3_cognition.py src/cemm_authoritative_hybrid/r3_learning.py src/cemm_authoritative_hybrid/r3_effects.py src/cemm_authoritative_hybrid/r3_response.py tests/test_r4_closeout_regressions.py governance/test_inventory.json artifacts/validation/TEST_INVENTORY_RECEIPT.json
git commit -m "fix(r4): close remaining authentic semantic cases"
```

### Task 7: Generate the complete R4 artifact graph twice

**Files:**
- Create: `artifacts/r4/expected_contracts.jsonl`
- Create: `artifacts/r4/expected_derivations.jsonl`
- Create: `artifacts/r4/expanded_cases.jsonl`
- Create: `artifacts/r4/episodes.jsonl`
- Create: `artifacts/r4/mutations.jsonl`
- Create: `artifacts/r4/mutation_observations.jsonl`
- Create: `artifacts/r4/structural_sufficiency.json`
- Create: `artifacts/r4/partitions/*.json`
- Create: `artifacts/r4/training_allowlist.json`
- Create: `artifacts/r4/BUILD_RECEIPT.json`
- Modify: `tests/test_r4_authentic_episodes.py`
- Create: `tests/test_r4_admission.py`

- [ ] **Step 1: Add failing deterministic reconstruction tests**

```python
def test_committed_r4_artifacts_rebuild_byte_identically(tmp_path):
    first = build_r4(ROOT, tmp_path / "first")
    second = build_r4(ROOT, tmp_path / "second")
    assert tree_digest(first) == tree_digest(second)
    assert tree_digest(first) == tree_digest(ROOT / "artifacts" / "r4")


def test_build_receipt_reconstructs_every_artifact_hash():
    receipt = load_build_receipt(ROOT)
    assert reconstruct_build_receipt(ROOT).as_dict() == receipt.as_dict()
```

- [ ] **Step 2: Run tests before generation**

```powershell
python -m pytest tests/test_r4_authentic_episodes.py tests/test_r4_admission.py -q -p no:cacheprovider
```

Expected: FAIL because the committed artifact graph is absent.

- [ ] **Step 3: Generate two candidate trees from the same governed R3 source**

```powershell
python scripts/build_r4_artifacts.py --environment src/cemm_authoritative_hybrid/r4_environment.py --output "$env:TEMP\cemm-r4-build-a"
python scripts/build_r4_artifacts.py --environment src/cemm_authoritative_hybrid/r4_environment.py --output "$env:TEMP\cemm-r4-build-b"
```

Expected: both exit 0, report the same `receipt_ref`, and bind the exact source
revision from the final effective green R3 ledger record.

- [ ] **Step 4: Prove exact tree identity and copy candidate bytes**

Run a PowerShell hash inventory over both explicit temporary directories and
require identical relative paths, sizes, and SHA-256 values. Then use
`Copy-Item -LiteralPath` for each verified file into `artifacts/r4/`; do not
delete or replace the repository root or use a recursive wildcard move.

Expected: copied tree equals both candidates byte for byte.

- [ ] **Step 5: Run corpus and deterministic reconstruction tests**

```powershell
python -m pytest tests/test_r4_authentic_episodes.py tests/test_r4_admission.py -q -p no:cacheprovider
python scripts/validate_mvp.py --tier phase --phase R4
```

Expected: tests and the complete R4 phase tier pass.

- [ ] **Step 6: Commit generated artifacts**

```powershell
git add artifacts/r4 tests/test_r4_authentic_episodes.py tests/test_r4_admission.py
git commit -m "data(r4): generate authentic reviewed corpus"
```

### Task 8: Obtain and verify external R4 review

**Files:**
- Create outside the repository first: unsigned review request JSON
- Create from external reviewer: `data/review/R4_REVIEW_MANIFEST.json`
- Create or reference outside semantic/runtime owners: external verifier module and pinned SHA-256

- [ ] **Step 1: Produce the unsigned exact review request**

```powershell
if (-not $env:CEMM_R4_REVIEWER_REF -or -not $env:CEMM_R4_REVIEW_NONCE -or -not $env:CEMM_R4_REVIEW_ISSUED_AT) { throw "external reviewer identity, nonce, and issued time are required" }
python scripts/prepare_r4_review_request.py --scenarios data/scenarios/use_cases.jsonl --artifacts artifacts/r4 --output "$env:TEMP\R4_REVIEW_REQUEST.json" --reviewer-ref $env:CEMM_R4_REVIEWER_REF --reviewer-policy-ref policy:r4-corpus-review-v1 --nonce $env:CEMM_R4_REVIEW_NONCE --issued-at $env:CEMM_R4_REVIEW_ISSUED_AT
```

Expected: request contains exact artifact hashes and the literal placeholders
`REQUIRES_EXTERNAL_SIGNER` / `REQUIRES_EXTERNAL_SIGNATURE`.

- [ ] **Step 2: Hand the request to the approved external reviewer**

The reviewer independently verifies scenario authority, 400 expected/observed
comparisons, mutation observations, structural sufficiency, partitions, and
source revision; then returns Corpus Review Manifest ABI 2 with its external
signature. Repository code and this agent must not fabricate the signature.

- [ ] **Step 3: Verify the returned manifest and verifier source pin**

```powershell
if (-not $env:CEMM_R4_REVIEW_VERIFIER -or -not $env:CEMM_R4_REVIEW_VERIFIER_SOURCE) { throw "external verifier spec and source path are required" }
python scripts/verify_r4_review_manifest.py data/review/R4_REVIEW_MANIFEST.json --verifier $env:CEMM_R4_REVIEW_VERIFIER
$env:CEMM_R4_REVIEW_VERIFIER_SHA256=(Get-FileHash -LiteralPath $env:CEMM_R4_REVIEW_VERIFIER_SOURCE -Algorithm SHA256).Hash.ToLowerInvariant()
```

Expected: manifest verification exits 0 and prints its `manifest_ref`; record the
lowercase verifier source hash for admission.

- [ ] **Step 4: Commit the exact external manifest**

```powershell
git add data/review/R4_REVIEW_MANIFEST.json
git commit -m "review(r4): bind externally approved corpus"
```

### Task 9: Run governed R4 admission and append green status

**Files:**
- Modify: `governance/replay_status.jsonl`
- Create: the content-addressed `artifacts/validation/runs/*.json` path printed by the fresh R4 admission outcome
- Modify as required by governance: `artifacts/validation/TEST_INVENTORY_RECEIPT.json`

- [ ] **Step 1: Run every owner and phase gate on the committed clean source**

```powershell
python scripts/validate_mvp.py --tier owner --phase R4 --owner expected-contract
python scripts/validate_mvp.py --tier owner --phase R4 --owner mutation-partition
python scripts/validate_mvp.py --tier owner --phase R4 --owner structural-sufficiency
python scripts/validate_mvp.py --tier owner --phase R4 --owner surface-review
python scripts/validate_mvp.py --tier phase --phase R3
python scripts/validate_mvp.py --tier phase --phase R4
```

Expected: all six commands pass.

- [ ] **Step 2: Run R4 admission with exact external verifier environment**

Set only the environment variables consumed by the active admission runner for
external verifier spec/hash, source revision, and authority generation; then:

```powershell
python scripts/validate_mvp.py --tier admission --phase R4 | Tee-Object -FilePath "$env:TEMP\r4-admission-outcome.json"
```

Expected: `disposition=passed`, a fresh exact `run_ref`, `gate_result_ref`, and
committed receipt under `artifacts/validation/runs/`.

- [ ] **Step 3: Dry-run the append against the exact current ledger head**

```powershell
$admission=Get-Content -Raw "$env:TEMP\r4-admission-outcome.json" | ConvertFrom-Json
$ledgerHead=(Get-Content governance/replay_status.jsonl | Select-Object -Last 1 | ConvertFrom-Json).record_ref
python scripts/update_replay_status.py --phase R4 --status green --run-ref $admission.run_ref --expect-record-ref $ledgerHead --dry-run
```

Expected: one canonical proposed R4 green record bound to the R3 green
predecessor and current source.

- [ ] **Step 4: Append and reconstruct the entire chain**

```powershell
python scripts/update_replay_status.py --phase R4 --status green --run-ref $admission.run_ref --expect-record-ref $ledgerHead --append
python scripts/update_replay_status.py --verify-chain
```

Expected:

```text
G0=green R1=green R2=green R3=green R4=green R5=red R6=red R7=red R8=red
```

- [ ] **Step 5: Commit admission evidence**

```powershell
git add governance/replay_status.jsonl artifacts/validation/runs artifacts/validation/TEST_INVENTORY_RECEIPT.json
git commit -m "admit(r4): close authentic reviewed data phase"
```

### Task 10: Run complete branch verification and publish the closeout branch

**Files:**
- No source changes expected

- [ ] **Step 1: Run the complete governed and repository suite**

```powershell
python -m compileall -q src scripts
python scripts/verify_r3_r4_test_metadata.py
python scripts/check_r3_r4_structure.py
python scripts/audit_r3_r4_legacy_tests.py --strict --output "$env:TEMP\R3_R4_LEGACY_AUDIT.json"
python -m pytest -q -p no:cacheprovider
python scripts/validate_mvp.py --tier phase --phase R3
python scripts/validate_mvp.py --tier phase --phase R4
python scripts/update_replay_status.py --verify-chain
```

Expected: every command exits 0, the full suite has no failure/error/skip/xfail,
and chain output shows G0–R4 green.

- [ ] **Step 2: Verify branch ancestry and clean status**

```powershell
git merge-base --is-ancestor 0a52bd6 HEAD
git merge-base --is-ancestor 4eb6c27 HEAD
git status --short
```

Expected: both ancestry commands exit 0 and status is empty.

- [ ] **Step 3: Push without rewriting history**

```powershell
git push -u origin codex/r4-final-admission-closeout
```

Expected: remote branch points to the exact verified local tip.

### Task 11: Merge the complete G0–R4 lineage into `main`

**Files:**
- Git integration only

- [ ] **Step 1: Fetch and verify remote identities**

```powershell
git fetch origin --prune
git rev-parse HEAD
git rev-parse origin/codex/r4-final-admission-closeout
git rev-parse origin/main
```

Expected: local closeout tip equals its remote tip and `main` is unchanged from
the reviewed integration base or has only compatible descendants to analyze.

- [ ] **Step 2: Merge the closeout branch into an up-to-date local `main`**

From the main checkout, preserve existing untracked files and run:

```powershell
git switch main
git pull --ff-only origin main
git merge --no-ff codex/r4-final-admission-closeout -m "merge: admit Hybrid MVP through R4"
```

Expected: merge succeeds without squashing or cherry-picking and retains every
G0–R4 commit as an ancestor.

- [ ] **Step 3: Verify the exact merge result before pushing**

From `hybrid_mvp/` on the merge commit:

```powershell
python -m compileall -q src scripts
python scripts/verify_r3_r4_test_metadata.py
python scripts/check_r3_r4_structure.py
python scripts/audit_r3_r4_legacy_tests.py --strict --output "$env:TEMP\R3_R4_LEGACY_AUDIT_MAIN.json"
python -m pytest -q -p no:cacheprovider
python scripts/validate_mvp.py --tier phase --phase R3
python scripts/validate_mvp.py --tier phase --phase R4
python scripts/update_replay_status.py --verify-chain
```

Expected: same results as the closeout branch, with G0–R4 green.

- [ ] **Step 4: Push verified `main`**

```powershell
git push origin main
```

Expected: `origin/main` advances to the exact locally verified merge commit.

- [ ] **Step 5: Preserve root-adoption boundary**

Confirm `hybrid_mvp/docs/DOCUMENT_AUTHORITY.json` still declares
`root_adoption_requires_separate_review=true`. Do not redirect the root runtime,
delete historical branches, or alter unrelated worktrees as part of this merge.

## Plan self-review result

- Spec coverage: all design sections map to Tasks 1–11.
- Placeholder scan: no placeholder tokens remain. External reviewer values and
  content-addressed run refs are read from explicit environment or command output
  and rejected when absent.
- Type consistency: `ExpandedCase`, `EpisodeExecutionResult`, `CycleResult`,
  `SemanticMutation`, `MutationBoundaryResult`, `R4BuildReceipt`, and
  `CorpusReviewManifest` use their active ABI owners and signatures.
- Scope: root runtime adoption and R5+ remain excluded.
