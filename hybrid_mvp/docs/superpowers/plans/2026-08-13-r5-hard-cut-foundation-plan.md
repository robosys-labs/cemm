# R5 Legacy Hard-Cut Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove retired test/runtime-fixture paths, preserve every active G0-R4 assertion, replace the 43 frozen R5 source-test records with 17 current foundation successors plus 26 explicit deferred neural obligations, update active documentation, and make the R5 source/owner/phase foundation gates pass while R5 admission remains unavailable and replay status remains red.

**Architecture:** Keep `governance/test_inventory.json` immutable and introduce one reviewed R5 test-disposition source plus a deterministic receipt. The inventory verifier accepts a missing frozen R5 source only when an exact successor lineage or exact deferred obligation covers it; it never treats deferral as execution evidence. Current R5 foundation tests own five boundaries—artifact contract, proposal contract, realization contract, data isolation, and legacy hard cut—while neural model quality, calibration, reproducibility, and weight-use evidence remain reserved for `R5-Neural-Activation`. Remove compatibility test support only after active-node and import audits prove no G0-R4 owner depends on it.

**Tech Stack:** Python 3, pytest, canonical JSON/JSONL, literal test metadata, SHA-256 content references, PowerShell, Git worktrees.

---

## Release invariants

- `governance/test_inventory.json` remains byte-identical with SHA-256 `7c27b0ad80998fc1f10876c05d0238a2498d2fd3a116ace77c9505da11d0b4b8`.
- G0, R1, R2, R3, and R4 source-only active assertion identities remain satisfied by executable current leaves.
- The 43 frozen R5 records have exactly one reviewed disposition each: 17 `successor`, 26 `deferred`, 0 `retired`.
- A deferred row cannot satisfy a rewrite obligation, owner selector, phase selector, admission selector, or pytest collection requirement.
- The rewritten `assertion:release-path-excludes-bootstrap-proposer` obligation has all three required executable successors at R5.
- R5 owner and phase tiers may pass the foundation contract; R5 admission must still return a structured error and must not append a green status.
- No current source imports `legacy_propositions` or `legacy_runtime_fixtures`, and neither support module remains in the tree.
- No open-class compatibility test, bootstrap proposer fallback, stale fixture shim, or UI/runtime fallback is added to keep a historical test passing.

## File map

- `governance/r5_test_dispositions.json` — reviewed source classifying all 43 frozen R5 source tests.
- `schemas/r5_test_dispositions.schema.json` — strict reviewed-source schema.
- `artifacts/validation/R5_TEST_DISPOSITIONS.json` — deterministic receipt generated from the reviewed source and literal successor metadata.
- `scripts/r5_test_dispositions.py` — bounded loader, validator, and canonical receipt builder.
- `scripts/generate_r5_test_dispositions.py` — deterministic generator CLI.
- `scripts/test_inventory_core.py` — apply exact R5 successor/deferred coverage without mutating the frozen inventory.
- `scripts/check_test_inventory.py` — report exact R5 disposition counts and receipt ref.
- `tests/test_test_inventory.py` — fail-closed disposition and lineage tests.
- `configs/r5_foundation.json` — reviewed owner/data/status boundary for this increment.
- `schemas/r5_foundation.schema.json` — strict R5 foundation contract schema.
- `tests/test_r5_artifact_contract.py` — 15 current artifact successors.
- `tests/test_r5_public_runtime_selection.py` — two proposal successors plus the missing rewritten successor.
- `tests/test_r5_foundation.py` — exact owner set and red/not-admitted status.
- `tests/test_r5_realization_boundary.py` — current exact R5 realization boundary.
- `tests/test_r5_data_isolation.py` — exact four-class access contract and training-loader boundary.
- `tests/test_r5_legacy_hard_cut.py` — disposition completeness and forbidden legacy footprint.
- `scripts/audit_legacy_test_hard_cut.py` — source-only anti-bloat audit.
- `configs/validation_gates.json` — register R5 foundation steps and five owners.
- `scripts/validation_gate.py` — allow R5 owner/phase execution but deliberately keep R5 admission evidence unsupported.
- `scripts/refresh_r5_test_metadata.py` — deterministic R5 literal AST hash refresher.
- `tests/conftest.py` — remove compatibility support loading and fixtures used only by retired tests.
- `tests/test_canonical.py` — retain R1 canonical identity tests; remove its four frozen R5 tensor tests after succession.
- `tests/test_neural_proposer.py` — retain the active R1 no-legacy-API invariant; remove its four frozen R5 tests after succession/deferral.
- `docs/DOCUMENT_AUTHORITY.json`, `tests/test_replay_governance.py` — make the approved R5 design and this plan governing.
- `docs/ARCHITECTURE.md`, `docs/ABI_REGISTRY.md`, `docs/IMPLEMENTATION_PLAN.md` — state the hard-cut boundary and current R5 status.
- `docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md` — add a narrow R5 supersession notice.
- `../NATIVE_SEMANTIC_SPINE_IMPLEMENTATION_STATUS.md`, `../NATIVE_SEMANTIC_SPINE_IMPLEMENTATION_PLAN.md`, `../V1_ACCEPTANCE.md` — remove stale present-tense claims that conflict with the closed R4/current R5 boundary.

### Task 1: Reconfirm the clean baseline and freeze the removal set

**Files:**
- Read: `governance/test_inventory.json`
- Read: `scripts/test_inventory_core.py`
- Read: `configs/validation_gates.json`
- Read: `tests/conftest.py`
- Create later: `artifacts/validation/R5_TEST_DISPOSITIONS.json`

- [ ] **Step 1: Confirm branch and immutable inventory bytes**

```powershell
git status --short --branch
(Get-FileHash governance/test_inventory.json -Algorithm SHA256).Hash.ToLower()
```

Expected: branch `codex/r5-hard-cut-foundation`, clean worktree, and inventory hash `7c27b0ad80998fc1f10876c05d0238a2498d2fd3a116ace77c9505da11d0b4b8`.

- [ ] **Step 2: Reproduce both R5 foundation failures**

```powershell
python scripts/check_test_inventory.py --phase R5 --source-only
python scripts/validate_mvp.py --tier phase --phase R5
```

Expected: inventory fails on missing `tests/test_r5_public_runtime_selection.py::test_selected_release_runtime_never_invokes_bootstrap_proposer`; validation returns `phase has no validation plan: R5`.

- [ ] **Step 3: Record active G0-R4 node sets and legacy imports**

```powershell
python scripts/check_test_inventory.py --phase G0 --source-only
python scripts/check_test_inventory.py --phase R1 --source-only
python scripts/check_test_inventory.py --phase R2 --source-only
python scripts/check_test_inventory.py --phase R3 --source-only
python scripts/check_test_inventory.py --phase R4 --source-only
rg -n "legacy_propositions|legacy_runtime_fixtures|runtime_factory|verified_observation_program|SIX_PHASES" tests
```

Save the five active-node refs in the implementation log. The expected direct compatibility importers are `test_cognitive_loop_e2e.py`, `test_epistemic_admission.py`, `test_inference_bounds.py`, `test_learning_distinctions.py`, `test_query_engine.py`, `test_recursive_inference.py`, `test_restart_e2e.py`, `test_safety_and_contracts.py`, and `test_synonym_acquisition.py`; all must have current successor leaves before deletion.

### Task 2: Define and validate R5 Test Disposition ABI 1

**Files:**
- Create: `schemas/r5_test_dispositions.schema.json`
- Create: `scripts/r5_test_dispositions.py`
- Create: `governance/r5_test_dispositions.json`
- Modify: `tests/test_test_inventory.py`

- [ ] **Step 1: Write failing parser/schema tests**

Add tests that construct minimal reviewed payloads and require:

```python
{
    "schema": "cemm-r5-test-dispositions-v1",
    "phase": "R5",
    "inventory_ref": "test_inventory:c715e262526c0ea26a6fef90",
    "rows": [
        {
            "predecessor_source_test_ref": "tests/test_x.py::test_x",
            "assertion_ref": "assertion:x",
            "disposition": "successor",
            "successor_node_ids": ["tests/test_r5_x.py::test_x"],
        }
    ],
}
```

Reject unknown fields, duplicate predecessor refs, non-R5 predecessors, assertion mismatches, empty successor lists, successor rows with deferral fields, deferred rows without `future_owner_ref` and `future_task_ref`, a `retired` value, and any row count other than 43 for the real reviewed file.

- [ ] **Step 2: Run the tests to see the missing owner**

```powershell
python -m pytest tests/test_test_inventory.py -q -p no:cacheprovider
```

Expected: FAIL because `r5_test_dispositions.py` and the schema do not exist.

- [ ] **Step 3: Implement the bounded loader**

In `scripts/r5_test_dispositions.py`, use only canonical JSON, exact field sets, a 1 MiB read bound, lowercase SHA-256 values, and immutable dataclasses. Export:

```python
DISPOSITION_SCHEMA = "cemm-r5-test-dispositions-v1"
RECEIPT_SCHEMA = "cemm-r5-test-disposition-receipt-v1"

load_r5_test_dispositions(root: Path, *, expected_inventory_ref: str) -> R5TestDispositions
build_r5_test_disposition_receipt(root: Path, dispositions: R5TestDispositions) -> dict[str, object]
```

The loader validates syntax and predecessor coverage. The receipt builder additionally parses literal test metadata and verifies every `successor_node_ids` entry exists, activates at R5, preserves the predecessor assertion identity, and directly or transitively supersedes the predecessor. It must not import pytest or execute tests.

- [ ] **Step 4: Check in the exact 43-row reviewed source**

Use the classification in Appendix A. Every deferred row uses `future_task_ref: "R5-Neural-Activation"`; owner refs are `proposal-contract`, `realization-contract`, `data-isolation`, `artifact-contract`, or `calibration-contract` as appropriate. The reviewed source has exactly 17 successor rows, 26 deferred rows, and no retired rows.

- [ ] **Step 5: Run focused tests**

```powershell
python -m pytest tests/test_test_inventory.py -q -p no:cacheprovider
```

Expected: parser unit tests pass; real-source successor verification remains red until Tasks 4 and 5 create successor nodes.

- [ ] **Step 6: Commit the ABI source and tests**

```powershell
git add schemas/r5_test_dispositions.schema.json scripts/r5_test_dispositions.py governance/r5_test_dispositions.json tests/test_test_inventory.py
git commit -m "governance(r5): define frozen test dispositions"
```

### Task 3: Teach the immutable inventory verifier about exact R5 deferrals

**Files:**
- Modify: `scripts/test_inventory_core.py`
- Modify: `scripts/check_test_inventory.py`
- Modify: `tests/test_test_inventory.py`

- [ ] **Step 1: Write failing fail-closed overlay tests**

Cover these cases with temporary repositories:

1. a missing frozen R5 leaf with no disposition still fails;
2. a deferred R5 leaf is absent from `active_node_ids` only at R5 and appears in `deferred_r5_assertion_refs`;
3. a deferred row cannot satisfy a due rewrite obligation;
4. a successor row without literal executable metadata fails;
5. a successor row follows normal supersession to an executable current leaf;
6. a missing or extra reviewed row fails exact 43-row coverage in the real repository;
7. G0-R4 results are unchanged by the R5 overlay.

- [ ] **Step 2: Run the focused failures**

```powershell
python -m pytest tests/test_test_inventory.py -q -p no:cacheprovider
```

Expected: FAIL because `InventoryResult` has no R5 disposition state and deferred leaves still require source functions.

- [ ] **Step 3: Implement minimal overlay integration**

Load the reviewed source only when `phase == "R5"`. Validate it after frozen source records and literal later records are known. Add immutable result fields:

```python
r5_disposition_receipt_ref: str | None
deferred_r5_assertion_refs: tuple[str, ...]
```

Successor rows use the existing lineage graph; do not create synthetic executable nodes. Deferred predecessor case-node IDs may be skipped by active selection only after exact coverage validation. Keep them out of collectable, owner, phase, admission-only, and rewrite-satisfaction sets. Preserve the existing G0-R4 code path byte-for-byte where practical.

- [ ] **Step 4: Extend source-only output**

For R5 only, add `r5_disposition_receipt_ref`, `r5_successor_count`, and `r5_deferred_count` to the canonical CLI payload. Keep the existing schema name and existing fields so G0-R4 consumers remain compatible.

- [ ] **Step 5: Run inventory unit and baseline checks**

```powershell
python -m pytest tests/test_test_inventory.py -q -p no:cacheprovider
python scripts/check_test_inventory.py --phase G0 --source-only
python scripts/check_test_inventory.py --phase R1 --source-only
python scripts/check_test_inventory.py --phase R2 --source-only
python scripts/check_test_inventory.py --phase R3 --source-only
python scripts/check_test_inventory.py --phase R4 --source-only
```

Expected: unit and G0-R4 checks pass with the same active-node refs recorded in Task 1. R5 remains red because successor nodes are not present yet.

- [ ] **Step 6: Commit inventory support**

```powershell
git add scripts/test_inventory_core.py scripts/check_test_inventory.py tests/test_test_inventory.py
git commit -m "feat(r5): verify exact deferred test obligations"
```

### Task 4: Replace the valid frozen R5 artifact assertions with current successors

**Files:**
- Create: `tests/test_r5_artifact_contract.py`
- Modify: `tests/test_canonical.py`
- Delete later: `tests/test_artifact_security.py`

- [ ] **Step 1: Create 15 literal successor tests**

Move behavior, not compatibility scaffolding, from the 11 artifact-security tests and four R5 tensor-canonicalization tests into `test_r5_artifact_contract.py`. Use the current `safetensors`/canonical artifact APIs and temporary files. Give every test R5 literal metadata with:

```python
{
    "activation_phase": "R5",
    "assertion_ref": "<exact predecessor assertion_ref>",
    "diagnostic_role": "owner",
    "introduced_by_task": "R5-Hard-Cut-Foundation",
    "owner_ref": "artifact-contract",
    "supersedes_node_id": "<exact frozen predecessor node>",
    "source_ast_sha256": "<refreshed hash>",
}
```

The successors must retain strict safe-deserialization, exact schema, tamper, dtype, shape, finite-value, size-bound, no-pickle, CPU-load, digest, and tensor-identity behavior. Do not add an old `.pt`/pickle decoder.

- [ ] **Step 2: Remove only the four R5 tests from the mixed canonical module**

Keep its eight active R1 canonical identity tests and their literal metadata. Remove `torch` only if no retained R1 test imports it.

- [ ] **Step 3: Run artifact tests**

```powershell
python -m pytest tests/test_r5_artifact_contract.py tests/test_canonical.py -q -p no:cacheprovider
```

Expected: PASS.

### Task 5: Close the rewritten public-runtime selection obligation

**Files:**
- Create: `tests/test_r5_public_runtime_selection.py`
- Modify: `tests/test_neural_proposer.py`

- [ ] **Step 1: Write three current proposal-boundary tests**

Create these exact nodes:

```text
tests/test_r5_public_runtime_selection.py::test_selected_release_runtime_never_invokes_bootstrap_proposer
tests/test_r5_public_runtime_selection.py::test_release_runtime_requires_selected_neural_proposer
tests/test_r5_public_runtime_selection.py::test_release_runtime_does_not_delegate_to_bootstrap
```

The first has assertion ref `assertion:release-path-excludes-bootstrap-proposer` and `contributes_to_rewrite_refs: ["rewrite_obligation:1961f2f12d4a3f36b41db460"]`. The second supersedes `tests/test_neural_proposer.py::test_release_runtime_requires_neural_switch_proposer`; the third supersedes `tests/test_neural_weight_use.py::test_release_path_does_not_delegate_to_bootstrap`. Both preserve their predecessor assertion refs. All three are R5 `owner` nodes for `proposal-contract`.

Monkeypatch `BootstrapProposer` construction/proposal entry points to fail if touched, invoke the public release-runtime selector, and assert the current exact `MissingOwner`/not-admitted boundary. The test passes only because no bootstrap fallback occurs; it does not claim neural weights exist.

- [ ] **Step 2: Remove only the four R5 tests from `test_neural_proposer.py`**

Retain `test_legacy_candidate_api_is_absent`, because its active R1 assertion protects a current absence invariant rather than exercising a retired implementation. Remove now-unused neural imports.

- [ ] **Step 3: Run proposal and inventory checks**

```powershell
python -m pytest tests/test_r5_public_runtime_selection.py tests/test_neural_proposer.py -q -p no:cacheprovider
python scripts/check_test_inventory.py --phase R5 --source-only
```

Expected: the public-runtime rewrite obligation is complete. Inventory may still fail if the artifact successor module metadata has not been refreshed.

### Task 6: Add the five-owner R5 foundation contract without admitting R5

**Files:**
- Create: `configs/r5_foundation.json`
- Create: `schemas/r5_foundation.schema.json`
- Create: `tests/test_r5_foundation.py`
- Create: `tests/test_r5_realization_boundary.py`
- Create: `tests/test_r5_data_isolation.py`
- Modify: `configs/validation_gates.json`
- Modify: `scripts/validation_gate.py`
- Modify: `tests/test_validation_gate.py`

- [ ] **Step 1: Write the strict foundation contract**

Require exact values:

```json
{
  "schema": "cemm-r5-foundation-contract-v1",
  "phase": "R5",
  "increment": "hard-cut-foundation",
  "effective_replay_status": "red",
  "admission_available": false,
  "owners": [
    "artifact-contract",
    "data-isolation",
    "legacy-hard-cut",
    "proposal-contract",
    "realization-contract"
  ],
  "data_access_classes": ["calibration", "frozen_test", "selection", "train"],
  "neural_activation_task_ref": "R5-Neural-Activation"
}
```

The schema has `additionalProperties: false`. Keep `calibration-contract` only as a future owner in deferred dispositions; it is not a current foundation gate owner.

- [ ] **Step 2: Add current realization/data/foundation tests**

- `test_r5_realization_boundary.py` proves the public runtime reaches the exact R5 realization later-owner contract and returns a typed nonempty response meaning without manufacturing a surface.
- `test_r5_data_isolation.py` proves the four access classes are exact/disjoint and the current training loader accepts only the training partition.
- `test_r5_foundation.py` proves the exact five-owner set, `admission_available == false`, effective replay status remains red, and no R5 green governance record exists.

All are literal R5 nodes. Use owner roles for `realization-contract` and `data-isolation`; use a phase role for the aggregate foundation-status test.

- [ ] **Step 3: Register an R5 phase plan and five owner plans**

In `configs/validation_gates.json`, add exact selectors for every current R5 owner/phase node. The R5 `phase` roots execute source compilation plus the aggregate foundation test. The `admission` roots may be structurally present because the graph schema requires them, but `scripts/validation_gate.py::_required_admission_evidence_paths("R5")` must still reject R5 as not admitted before any receipt or status mutation.

- [ ] **Step 4: Test both allowed and forbidden tiers**

```powershell
python scripts/validate_mvp.py --tier owner --phase R5 --owner artifact-contract
python scripts/validate_mvp.py --tier owner --phase R5 --owner proposal-contract
python scripts/validate_mvp.py --tier owner --phase R5 --owner realization-contract
python scripts/validate_mvp.py --tier owner --phase R5 --owner data-isolation
python scripts/validate_mvp.py --tier owner --phase R5 --owner legacy-hard-cut
python scripts/validate_mvp.py --tier phase --phase R5
python scripts/validate_mvp.py --tier admission --phase R5
```

Expected: owner and phase calls pass; admission exits 2 with a canonical structured error and writes no admission run or green ledger record.

### Task 7: Generate and pin the disposition receipt

**Files:**
- Create: `scripts/generate_r5_test_dispositions.py`
- Create: `artifacts/validation/R5_TEST_DISPOSITIONS.json`
- Create: `scripts/refresh_r5_test_metadata.py`
- Modify: `tests/test_r5_legacy_hard_cut.py`

- [ ] **Step 1: Create the deterministic generator CLI**

The CLI reads the immutable inventory, reviewed disposition source, and literal current test metadata; it writes only `artifacts/validation/R5_TEST_DISPOSITIONS.json` when `--output` names that exact path. The receipt contains inventory ref, disposition-source SHA-256, literal metadata ref, 43 ordered rows, counts `17/26/0`, and a content-derived `receipt_ref`.

- [ ] **Step 2: Add determinism and tamper tests**

Generate twice into two temporary paths and require byte identity. Mutate one successor node, one assertion ref, and one deferred owner in memory and require validation failure. Assert the checked-in receipt matches freshly generated bytes.

- [ ] **Step 3: Refresh literal R5 AST hashes**

`scripts/refresh_r5_test_metadata.py` must use the same AST digest algorithm as the R3/R4 refresher, scan only `tests/test_r5_*.py`, and modify only `source_ast_sha256`. Run:

```powershell
python scripts/refresh_r5_test_metadata.py
python scripts/generate_r5_test_dispositions.py --output artifacts/validation/R5_TEST_DISPOSITIONS.json
python scripts/generate_r5_test_dispositions.py --check artifacts/validation/R5_TEST_DISPOSITIONS.json
```

Expected: exact `17` successor, `26` deferred, `0` retired; subsequent refresher and generator runs make no changes.

### Task 8: Remove retired tests and compatibility fixture support

**Files:**
- Create: `scripts/audit_legacy_test_hard_cut.py`
- Create: `tests/test_r5_legacy_hard_cut.py`
- Modify: `tests/conftest.py`
- Delete: `tests/legacy_propositions.py`
- Delete: `tests/legacy_runtime_fixtures.py`
- Delete: `tests/test_artifact_security.py`
- Delete: `tests/test_model_reproducibility.py`
- Delete: `tests/test_neural_realizer_weight_use.py`
- Delete: `tests/test_training_isolation.py`
- Delete: `tests/test_calibration.py`
- Delete: `tests/test_neural_weight_use.py`
- Delete: `tests/test_production_proposer_cutover.py`
- Delete: `tests/test_cognitive_loop_e2e.py`
- Delete: `tests/test_epistemic_admission.py`
- Delete: `tests/test_inference_bounds.py`
- Delete: `tests/test_learning_distinctions.py`
- Delete: `tests/test_query_engine.py`
- Delete: `tests/test_recursive_inference.py`
- Delete: `tests/test_restart_e2e.py`
- Delete: `tests/test_safety_and_contracts.py`
- Delete: `tests/test_synonym_acquisition.py`
- Delete after active-leaf audit: `tests/test_six_phase_runtime.py`
- Delete after active-leaf audit: `tests/test_response_meaning.py`

- [ ] **Step 1: Write the hard-cut audit before deleting files**

The source-only auditor must fail on:

- either forbidden support module existing;
- any Python import/load reference to either support module;
- compatibility fixtures `runtime_factory`, `verified_observation_program`, or `SIX_PHASES` remaining;
- any missing G0-R4 active leaf;
- any missing R5 disposition row;
- any current R5 test whose assertion identity is not in literal metadata;
- any deferred assertion appearing in an owner/phase/admission selector.

Do not fail merely because a historical document names an old test.

- [ ] **Step 2: Prove every direct importer is inactive through R4**

Call `load_and_verify(ROOT, INVENTORY_PATH, phase="R4", enforce_reviewed_counts=True, expected_sha256=INVENTORY_SHA256)` to assert none of the named modules owns an active R4 leaf. For `test_six_phase_runtime.py` and `test_response_meaning.py`, require the same proof before deletion. If either still owns an active G0-R4 assertion, stop and add a current semantic successor; do not delete it and do not add a shim.

- [ ] **Step 3: Delete the retired files and prune `conftest.py`**

Remove the dynamic support loader and only fixtures/constants whose complete consumer set was deleted. Preserve the current orientation/runtime fixtures used by active `test_orientation_projection.py` and `test_temporal_state.py` tests.

- [ ] **Step 4: Run absence, collection, and inventory gates**

```powershell
python scripts/audit_legacy_test_hard_cut.py
rg -n "legacy_propositions|legacy_runtime_fixtures|runtime_factory|verified_observation_program|SIX_PHASES" tests scripts src
python -m pytest --collect-only -q -p no:cacheprovider
python scripts/check_test_inventory.py --phase G0 --source-only
python scripts/check_test_inventory.py --phase R1 --source-only
python scripts/check_test_inventory.py --phase R2 --source-only
python scripts/check_test_inventory.py --phase R3 --source-only
python scripts/check_test_inventory.py --phase R4 --source-only
python scripts/check_test_inventory.py --phase R5 --source-only
```

Expected: audit and all inventory checks pass; `rg` returns no code matches; pytest collection succeeds.

- [ ] **Step 5: Commit the hard cut**

```powershell
git add tests scripts/audit_legacy_test_hard_cut.py artifacts/validation/R5_TEST_DISPOSITIONS.json
git commit -m "test(r5): remove retired compatibility suite"
```

### Task 9: Update active documentation and authority classification

**Files:**
- Modify: `docs/DOCUMENT_AUTHORITY.json`
- Modify: `tests/test_replay_governance.py`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/ABI_REGISTRY.md`
- Modify: `docs/IMPLEMENTATION_PLAN.md`
- Modify: `docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md`
- Modify: `../NATIVE_SEMANTIC_SPINE_IMPLEMENTATION_STATUS.md`
- Modify: `../NATIVE_SEMANTIC_SPINE_IMPLEMENTATION_PLAN.md`
- Modify: `../V1_ACCEPTANCE.md`

- [ ] **Step 1: Make the approved design and plan governing**

Add:

```text
docs/superpowers/specs/2026-08-13-r5-hard-cut-foundation-design.md
docs/superpowers/plans/2026-08-13-r5-hard-cut-foundation-plan.md
```

to `governing_documents` and the exact `GOVERNING_DOCUMENTS` test tuple. Do not make the generated receipt authoritative. Keep `docs/NEURAL_MODEL.md` historical evidence.

- [ ] **Step 2: Register the two new ABIs and status boundary**

In `docs/ABI_REGISTRY.md`, register R5 Test Disposition ABI 1 and R5 Foundation Contract ABI 1 with reviewed owners, schemas, generator, validation command, and the rule that deferral is not admission evidence. In `docs/ARCHITECTURE.md`, state R4 is closed/green, R5 foundation is source/owner/phase-valid but admission-unavailable/red, and neural activation is the next increment.

- [ ] **Step 3: Correct stale execution claims without rewriting history**

- Add a supersession/status banner to `docs/IMPLEMENTATION_PLAN.md`.
- Add a narrow R5 notice to the corrective-replay master plan: its frozen neural assertions are obligations, not a mandate to retain retired source files.
- Update the root native-spine status/plan and V1 acceptance status notes only where they make present-tense claims inconsistent with the closed R4/current R5 boundary.
- Preserve historical transcripts, evaluation reports, and archived neural expectations as evidence.

- [ ] **Step 4: Regenerate governed metadata hashes and verify docs**

Use the existing reviewed metadata refresh/generator commands required by the repository after governing-document bytes change. Then run:

```powershell
python -m pytest tests/test_replay_governance.py tests/test_document_authority.py -q -p no:cacheprovider
```

If `tests/test_document_authority.py` does not exist, run the authority cases in `tests/test_replay_governance.py` only. Never edit `governance/test_inventory.json`; refresh only literal current-source AST hashes and the generated inventory receipt.

- [ ] **Step 5: Commit documentation/governance updates**

```powershell
git add docs tests/test_replay_governance.py ..\NATIVE_SEMANTIC_SPINE_IMPLEMENTATION_STATUS.md ..\NATIVE_SEMANTIC_SPINE_IMPLEMENTATION_PLAN.md ..\V1_ACCEPTANCE.md
git commit -m "docs(r5): publish hard-cut foundation status"
```

### Task 10: Run exact R5 foundation and full regression gates

**Files:**
- Modify only if deterministic regeneration requires it: `artifacts/validation/TEST_INVENTORY_RECEIPT.json`

- [ ] **Step 1: Verify deterministic generated artifacts**

```powershell
python scripts/refresh_r5_test_metadata.py
git diff --exit-code
python scripts/generate_r5_test_dispositions.py --check artifacts/validation/R5_TEST_DISPOSITIONS.json
python scripts/check_test_inventory.py --phase R5 --source-only
```

Expected: no refresh diff, generated receipt exact, R5 source-only passes with 17 successors and 26 deferred obligations.

- [ ] **Step 2: Run all owner and phase tiers**

```powershell
python scripts/validate_mvp.py --tier owner --phase R5 --owner artifact-contract
python scripts/validate_mvp.py --tier owner --phase R5 --owner proposal-contract
python scripts/validate_mvp.py --tier owner --phase R5 --owner realization-contract
python scripts/validate_mvp.py --tier owner --phase R5 --owner data-isolation
python scripts/validate_mvp.py --tier owner --phase R5 --owner legacy-hard-cut
python scripts/validate_mvp.py --tier phase --phase R5
```

Expected: all pass.

- [ ] **Step 3: Prove R5 admission remains closed**

```powershell
python scripts/validate_mvp.py --tier admission --phase R5
python scripts/update_replay_status.py --show-effective
git status --short
```

Expected: admission exits 2 with `R5 admission is not available`; effective R5 remains red; no unexpected receipt or ledger change appears.

- [ ] **Step 4: Run all prior phase and complete regression gates**

```powershell
python scripts/validate_mvp.py --tier phase --phase G0
python scripts/validate_mvp.py --tier phase --phase R1
python scripts/validate_mvp.py --tier phase --phase R2
python scripts/validate_mvp.py --tier phase --phase R3
python scripts/validate_mvp.py --tier phase --phase R4
python -m pytest -q -p no:cacheprovider
python scripts/check_r3_r4_structure.py
python scripts/audit_legacy_test_hard_cut.py
git diff --check
```

Expected: every command passes. Test count may fall because retired source files were deleted; acceptance is exact active-node coverage and the full current suite, not preservation of historical test count.

- [ ] **Step 5: Final review and commit**

```powershell
git status --short
git diff --stat main HEAD
git log --oneline main..HEAD
```

Review that no product/runtime compatibility fallback was added, no frozen inventory bytes changed, R5 is still red, and all changes are within the approved hard-cut foundation. Commit any deterministic receipt-only finalization as:

```powershell
git add artifacts/validation/TEST_INVENTORY_RECEIPT.json
git commit -m "chore(r5): finalize foundation validation receipts"
```

Do not merge or push from this plan unless the user separately authorizes integration after reviewing the verified branch.

---

## Appendix A: Exact frozen R5 disposition

### Successor now — 17

All 11 records in `tests/test_artifact_security.py` become literal successors in `tests/test_r5_artifact_contract.py`:

1. `test_artifact_digest_is_enforced`
2. `test_artifact_loads_on_cpu`
3. `test_artifact_rejects_infinite_values`
4. `test_artifact_rejects_oversized_payload`
5. `test_artifact_rejects_pickle_format`
6. `test_artifact_rejects_shape_mismatch`
7. `test_artifact_rejects_tampered_weights`
8. `test_artifact_rejects_unexpected_dtype`
9. `test_artifact_schema_is_exact`
10. `test_artifact_uses_safe_deserialization`
11. `test_valid_artifact_loads`

All four R5 records in `tests/test_canonical.py` become literal successors in `tests/test_r5_artifact_contract.py`:

12. `test_tensor_canonical_identity_distinguishes_dtype`
13. `test_tensor_canonical_identity_distinguishes_shape`
14. `test_tensor_canonical_identity_uses_full_contents`
15. `test_tensor_canonical_identity_rejects_nonfinite_values`

The two release-selection records become literal successors in `tests/test_r5_public_runtime_selection.py`:

16. `tests/test_neural_proposer.py::test_release_runtime_requires_neural_switch_proposer`
17. `tests/test_neural_weight_use.py::test_release_path_does_not_delegate_to_bootstrap`

The additional public-runtime test required by rewrite obligation `rewrite_obligation:1961f2f12d4a3f36b41db460` is new current evidence, not one of the 43 disposition rows.

### Deferred to R5-Neural-Activation — 26

All six in `tests/test_model_reproducibility.py`:

1. `test_deterministic_inference_for_same_input`
2. `test_dropout_disabled_during_inference`
3. `test_model_architecture_is_pinned`
4. `test_model_config_is_strictly_parsed`
5. `test_model_config_rejects_extra_fields`
6. `test_model_config_rejects_missing_fields`

All six in `tests/test_neural_realizer_weight_use.py`:

7. `test_generation_is_deterministic`
8. `test_neural_realizer_requires_weights`
9. `test_realizer_allows_unseen_expression`
10. `test_realizer_changes_when_weights_change`
11. `test_realizer_does_not_delegate_to_template`
12. `test_realizer_is_semantically_constrained`

Three neural behavior records in `tests/test_neural_proposer.py`:

13. `test_invalid_actions_are_masked`
14. `test_neural_proposer_is_not_bootstrap_capacity`
15. `test_neural_proposer_returns_logits_and_selected_action`

All four R5 records in `tests/test_training_isolation.py`:

16. `test_combined_reranker_capacity_cannot_improve_frozen_test`
17. `test_dynamic_training_slots_scale_with_reviewed_train_partition`
18. `test_realizer_artifact_pins_authentic_episode_source`
19. `test_release_artifact_pins_authentic_episode_source`

Two remaining weight-use records in `tests/test_neural_weight_use.py`:

20. `test_proposal_changes_when_weights_change`
21. `test_release_path_masks_invalid_actions`

All three in `tests/test_calibration.py`:

22. `test_calibration_bins_include_high_confidence_error`
23. `test_calibration_report_is_deterministic`
24. `test_calibration_threshold_is_enforced`

Both R5 records in `tests/test_production_proposer_cutover.py`:

25. `test_release_profile_defaults_to_hard_cutover`
26. `test_template_fallback_requires_explicit_opt_in`

## Appendix B: Forbidden implementation shortcuts

- Do not change or regenerate `governance/test_inventory.json`.
- Do not mark deferred neural tests as passed, skipped, xfailed, historical, or retired.
- Do not retain old test modules merely to satisfy source collection.
- Do not add a generic concept fallback, phrase matcher, template realizer fallback, bootstrap proposer fallback, pickle loader, or legacy fixture shim.
- Do not weaken assertion identity, owner selector, rewrite, AST hash, document authority, admission evidence, or generated-artifact checks.
- Do not claim R5 admission or append R5 green in this increment.
