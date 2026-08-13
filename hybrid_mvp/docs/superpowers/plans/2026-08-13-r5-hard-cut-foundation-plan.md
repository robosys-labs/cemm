# R5 Legacy Hard-Cut Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove retired test/runtime-fixture paths, preserve every active G0-R4 assertion, and give the 43 frozen R5 source-test records exactly 17 current foundation successors, 25 explicit deferred neural obligations, and 1 explicit fallback retirement; then update active documentation and make the R5 source/owner/phase foundation gates pass while R5 admission remains unavailable and replay status remains red.

**Architecture:** Keep `governance/test_inventory.json` immutable and introduce one reviewed R5 test-disposition source plus a deterministic receipt. The inventory verifier accepts a missing frozen R5 source only when an exact successor lineage, exact deferred obligation, or reviewed retirement covers it; neither deferral nor retirement is execution evidence. Current R5 foundation tests own five boundaries—artifact contract, proposal contract, realization contract, data isolation, and legacy hard cut—while neural model quality, calibration, reproducibility, and weight-use evidence remain reserved for `R5-Neural-Activation`. Remove compatibility test support only after active-node and import audits prove no G0-R4 owner depends on it.

**Tech Stack:** Python 3, pytest, canonical JSON/JSONL, literal test metadata, SHA-256 content references, PowerShell, Git worktrees.

---

## Release invariants

- `governance/test_inventory.json` remains byte-identical with SHA-256 `7c27b0ad80998fc1f10876c05d0238a2498d2fd3a116ace77c9505da11d0b4b8`.
- G0, R1, R2, R3, and R4 source-only active assertion identities remain satisfied by executable current leaves.
- The 43 frozen R5 records have exactly one reviewed disposition each: 17 `successor`, 25 `deferred`, 1 `retired`.
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
- `scripts/test_inventory_core.py` — apply exact R5 successor/deferred/retired coverage without mutating the frozen inventory.
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

### Task 0: Promote the corrected R5 authority and freeze the exact partition

**Files:**
- Modify: `tests/test_replay_governance.py`
- Modify: `docs/DOCUMENT_AUTHORITY.json`
- Modify: `docs/superpowers/specs/2026-08-13-r5-hard-cut-foundation-design.md`
- Modify: `docs/superpowers/plans/2026-08-13-r5-hard-cut-foundation-plan.md`

- [ ] **Step 1: Add the focused governance regression first**

Require the R5 design and plan to be governing, classify
`docs/superpowers/plans/2026-08-04-hybrid-mvp-completion-critical-path.md` as a
superseded execution claim, derive all R5 rows from the pinned inventory, and
require the exact 17/25/1 partition plus one literal Appendix A occurrence for
every predecessor source-test ref.

- [ ] **Step 2: Observe RED**

Run the two focused governance tests. Both must fail: one because R5 authority
is missing, and one because the plan still states the old zero-retirement
partition and contains fictional
Appendix A names.

- [ ] **Step 3: Repair authority and the governing documents**

Promote the corrected R5 design and plan before disposition-ABI implementation.
Do not edit `governance/test_inventory.json`, implement the disposition ABI, or
touch remote refs in this task.

- [ ] **Step 4: Observe GREEN and commit one governance/docs change**

Run the focused tests, strict JSON parsing, the exact 43-row/count check, and
verify the pinned inventory SHA-256 before committing.

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

Reject unknown fields, duplicate predecessor refs, non-R5 predecessors, assertion mismatches, empty successor lists, successor rows with deferral or retirement fields, deferred rows without `future_owner_ref` and `future_task_ref`, retired rows without an exact predecessor and concrete `retirement_reason`, and any row count other than 43 for the real reviewed file.

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

Use the classification in Appendix A. Every deferred row uses `future_task_ref: "R5-Neural-Activation"` and the exact concrete owner shown there. The reviewed source has exactly 17 successor rows, 25 deferred rows, and 1 retired row. The retirement reason must cite the Hybrid MVP definition of completion and must not create a future activation obligation.

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

### Task 3: Teach the immutable inventory verifier about exact R5 dispositions

**Files:**
- Modify: `scripts/test_inventory_core.py`
- Modify: `scripts/check_test_inventory.py`
- Modify: `tests/test_test_inventory.py`

- [ ] **Step 1: Write failing fail-closed overlay tests**

Cover these cases with temporary repositories:

1. a missing frozen R5 leaf with no disposition still fails;
2. a deferred R5 leaf is absent from `active_node_ids` only at R5 and appears in `deferred_r5_assertion_refs`;
3. a retired R5 leaf is absent from `active_node_ids` only at R5 and appears in `retired_r5_assertion_refs`;
4. neither a deferred nor retired row can satisfy a due rewrite obligation;
5. a successor row without literal executable metadata fails;
6. a successor row follows normal supersession to an executable current leaf;
7. a missing or extra reviewed row fails exact 43-row coverage in the real repository;
8. G0-R4 results are unchanged by the R5 overlay.

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
retired_r5_assertion_refs: tuple[str, ...]
```

Successor rows use the existing lineage graph; do not create synthetic executable nodes. Deferred and retired predecessor case-node IDs may be skipped by active selection only after exact coverage validation. Keep them out of collectable, owner, phase, admission-only, and rewrite-satisfaction sets. Preserve the existing G0-R4 code path byte-for-byte where practical.

- [ ] **Step 4: Extend source-only output**

For R5 only, add `r5_disposition_receipt_ref`, `r5_successor_count`, `r5_deferred_count`, and `r5_retired_count` to the canonical CLI payload. Keep the existing schema name and existing fields so G0-R4 consumers remain compatible.

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
git commit -m "feat(r5): verify exact test dispositions"
```

### Task 4: Replace the valid frozen R5 artifact assertions with current successors

**Files:**
- Create: `tests/test_r5_artifact_contract.py`
- Modify: `tests/test_canonical.py`
- Delete later: `tests/test_artifact_security.py`

- [ ] **Step 1: Create 15 literal successor tests**

Move behavior, not compatibility scaffolding, from the exact 11 artifact-security tests and four R5 tensor-canonicalization tests listed in Appendix A into `test_r5_artifact_contract.py`. Use the current `safetensors`/canonical artifact APIs and temporary files. Give every test R5 literal metadata with:

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

The successors must retain the inventory-owned requirements exactly: current
model-lock stability; current and mismatched Python ABI handling; identity,
manifest, metadata, dependency-lock, and tail tamper rejection before tensor
use; source-scan rejection of unsafe `torch.load` while allowing the safe
`safetensors` loader; valid artifact loading; and byte-, dtype-, and
shape-sensitive deterministic tensor identity. Do not add an old `.pt`/pickle
decoder or invent a replacement assertion absent from the frozen rows.

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

The schema has `additionalProperties: false`. Keep `calibration-contract`,
`reproduction-contract`, `selection-contract`, and `weight-use-contract` only
as future owners in deferred dispositions; they are not current foundation gate
owners.

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

The CLI reads the immutable inventory, reviewed disposition source, and literal current test metadata; it writes only `artifacts/validation/R5_TEST_DISPOSITIONS.json` when `--output` names that exact path. The receipt contains inventory ref, disposition-source SHA-256, literal metadata ref, 43 ordered rows, counts `17/25/1`, and a content-derived `receipt_ref`.

- [ ] **Step 2: Add determinism and tamper tests**

Generate twice into two temporary paths and require byte identity. Mutate one successor node, one assertion ref, and one deferred owner in memory and require validation failure. Assert the checked-in receipt matches freshly generated bytes.

- [ ] **Step 3: Refresh literal R5 AST hashes**

`scripts/refresh_r5_test_metadata.py` must use the same AST digest algorithm as the R3/R4 refresher, scan only `tests/test_r5_*.py`, and modify only `source_ast_sha256`. Run:

```powershell
python scripts/refresh_r5_test_metadata.py
python scripts/generate_r5_test_dispositions.py --output artifacts/validation/R5_TEST_DISPOSITIONS.json
python scripts/generate_r5_test_dispositions.py --check artifacts/validation/R5_TEST_DISPOSITIONS.json
```

Expected: exact `17` successor, `25` deferred, `1` retired; subsequent refresher and generator runs make no changes.

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
- any deferred or retired assertion appearing in an owner/phase/admission selector.

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

Expected: no refresh diff, generated receipt exact, R5 source-only passes with 17 successors, 25 deferred obligations, and 1 explicit retirement.

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

This table is derived row-for-row from the immutable
`governance/test_inventory.json` R5 records. The predecessor source-test and
assertion refs are copied exactly. No filename stem or proposed successor name
is treated as inventory evidence.

### Successor now — 17

| # | Exact predecessor source-test ref | Exact assertion ref | Current successor node / owner |
|---:|---|---|---|
| 1 | `tests/test_artifact_security.py::test_current_model_lock_hash_is_stable` | `assertion:artifact-security-current-model-lock-hash-is-stable` | `tests/test_r5_artifact_contract.py::test_current_model_lock_hash_is_stable` / `artifact-contract` |
| 2 | `tests/test_artifact_security.py::test_current_python_abi_matches_runtime` | `assertion:artifact-security-current-python-abi-matches-runtime` | `tests/test_r5_artifact_contract.py::test_current_python_abi_matches_runtime` / `artifact-contract` |
| 3 | `tests/test_artifact_security.py::test_identity_mismatch_fails_before_tensor_use` | `assertion:artifact-security-identity-mismatch-fails-before-tensor-use` | `tests/test_r5_artifact_contract.py::test_identity_mismatch_fails_before_tensor_use` / `artifact-contract` |
| 4 | `tests/test_artifact_security.py::test_manifest_tamper_fails_before_tensor_use` | `assertion:artifact-security-manifest-tamper-fails-before-tensor-use` | `tests/test_r5_artifact_contract.py::test_manifest_tamper_fails_before_tensor_use` / `artifact-contract` |
| 5 | `tests/test_artifact_security.py::test_metadata_tamper_fails_before_tensor_use` | `assertion:artifact-security-metadata-tamper-fails-before-tensor-use` | `tests/test_r5_artifact_contract.py::test_metadata_tamper_fails_before_tensor_use` / `artifact-contract` |
| 6 | `tests/test_artifact_security.py::test_model_dependency_lock_mismatch_fails_before_tensor_use` | `assertion:artifact-security-model-dependency-lock-mismatch-fails-before-tensor-use` | `tests/test_r5_artifact_contract.py::test_model_dependency_lock_mismatch_fails_before_tensor_use` / `artifact-contract` |
| 7 | `tests/test_artifact_security.py::test_no_production_module_calls_unsafe_torch_load` | `assertion:artifact-security-no-production-module-calls-unsafe-torch-load` | `tests/test_r5_artifact_contract.py::test_no_production_module_calls_unsafe_torch_load` / `artifact-contract` |
| 8 | `tests/test_artifact_security.py::test_python_abi_mismatch_fails_before_tensor_use` | `assertion:artifact-security-python-abi-mismatch-fails-before-tensor-use` | `tests/test_r5_artifact_contract.py::test_python_abi_mismatch_fails_before_tensor_use` / `artifact-contract` |
| 9 | `tests/test_artifact_security.py::test_safe_safetensors_load_file_is_allowed_in_source_scan` | `assertion:artifact-security-safe-safetensors-load-file-is-allowed-in-source-scan` | `tests/test_r5_artifact_contract.py::test_safe_safetensors_load_file_is_allowed_in_source_scan` / `artifact-contract` |
| 10 | `tests/test_artifact_security.py::test_tail_tamper_fails_before_tensor_use` | `assertion:artifact-security-tail-tamper-fails-before-tensor-use` | `tests/test_r5_artifact_contract.py::test_tail_tamper_fails_before_tensor_use` / `artifact-contract` |
| 11 | `tests/test_artifact_security.py::test_valid_artifact_loads` | `assertion:artifact-security-valid-artifact-loads` | `tests/test_r5_artifact_contract.py::test_valid_artifact_loads` / `artifact-contract` |
| 12 | `tests/test_canonical.py::test_tensor_identity_changes_on_byte_tamper` | `assertion:canonical-tensor-identity-changes-on-byte-tamper` | `tests/test_r5_artifact_contract.py::test_tensor_identity_changes_on_byte_tamper` / `artifact-contract` |
| 13 | `tests/test_canonical.py::test_tensor_identity_changes_on_dtype` | `assertion:canonical-tensor-identity-changes-on-dtype` | `tests/test_r5_artifact_contract.py::test_tensor_identity_changes_on_dtype` / `artifact-contract` |
| 14 | `tests/test_canonical.py::test_tensor_identity_changes_on_shape` | `assertion:canonical-tensor-identity-changes-on-shape` | `tests/test_r5_artifact_contract.py::test_tensor_identity_changes_on_shape` / `artifact-contract` |
| 15 | `tests/test_canonical.py::test_tensor_identity_is_byte_and_shape_deterministic` | `assertion:canonical-tensor-identity-is-byte-and-shape-deterministic` | `tests/test_r5_artifact_contract.py::test_tensor_identity_is_byte_and_shape_deterministic` / `artifact-contract` |
| 16 | `tests/test_neural_proposer.py::test_release_runtime_requires_neural_switch_proposer` | `assertion:neural-proposer-release-runtime-requires-neural-switch-proposer` | `tests/test_r5_public_runtime_selection.py::test_release_runtime_requires_selected_neural_proposer` / `proposal-contract` |
| 17 | `tests/test_neural_weight_use.py::test_release_path_does_not_delegate_to_bootstrap` | `assertion:neural-weight-use-release-path-does-not-delegate-to-bootstrap` | `tests/test_r5_public_runtime_selection.py::test_release_runtime_does_not_delegate_to_bootstrap` / `proposal-contract` |

The additional public-runtime test required by rewrite obligation
`rewrite_obligation:1961f2f12d4a3f36b41db460` is new current evidence, not one
of the 43 disposition rows.

### Explicit retirement — 1

| # | Exact predecessor source-test ref | Exact assertion ref | Concrete reason |
|---:|---|---|---|
| 18 | `tests/test_neural_realizer_weight_use.py::TestNeuralRealizerWeightUse::test_failure_meaning_uses_safe_fallback` | `assertion:neural-realizer-weight-use-test-neural-realizer-weight-use-failure-meaning-uses-safe-fallback` | `hybrid_mvp/AGENTS.md` section 7 requires zero fallback paths in final release gates; preserving this requirement would reintroduce forbidden fallback behavior. |

### Deferred to R5-Neural-Activation — 25

Every row below has `future_task_ref: "R5-Neural-Activation"` and the concrete
`future_owner_ref` shown in the final column.

| # | Exact predecessor source-test ref | Exact assertion ref | Future owner ref |
|---:|---|---|---|
| 19 | `tests/test_calibration.py::test_calibration_error_within_threshold` | `assertion:calibration-calibration-error-within-threshold` | `calibration-contract` |
| 20 | `tests/test_calibration.py::test_calibration_pins_model_identities` | `assertion:calibration-calibration-pins-model-identities` | `calibration-contract` |
| 21 | `tests/test_calibration.py::test_calibration_records_confidence_bins` | `assertion:calibration-calibration-records-confidence-bins` | `calibration-contract` |
| 22 | `tests/test_model_reproducibility.py::test_reproducibility_receipt_exists` | `assertion:model-reproducibility-reproducibility-receipt-exists` | `reproduction-contract` |
| 23 | `tests/test_model_reproducibility.py::test_reproducibility_receipt_records_proposal_identity` | `assertion:model-reproducibility-reproducibility-receipt-records-proposal-identity` | `reproduction-contract` |
| 24 | `tests/test_model_reproducibility.py::test_reproducibility_receipt_records_realizer_identity` | `assertion:model-reproducibility-reproducibility-receipt-records-realizer-identity` | `reproduction-contract` |
| 25 | `tests/test_model_reproducibility.py::test_reproducibility_receipt_records_scratch_outside_repo` | `assertion:model-reproducibility-reproducibility-receipt-records-scratch-outside-repo` | `reproduction-contract` |
| 26 | `tests/test_model_reproducibility.py::test_retraining_produces_same_proposal_identity` | `assertion:model-reproducibility-retraining-produces-same-proposal-identity` | `reproduction-contract` |
| 27 | `tests/test_model_reproducibility.py::test_retraining_produces_same_realizer_identity` | `assertion:model-reproducibility-retraining-produces-same-realizer-identity` | `reproduction-contract` |
| 28 | `tests/test_neural_proposer.py::test_internal_ref_spelling_does_not_affect_model_logits` | `assertion:neural-proposer-internal-ref-spelling-does-not-affect-model-logits` | `proposal-contract` |
| 29 | `tests/test_neural_proposer.py::test_neural_decoder_never_emits_masked_action` | `assertion:neural-proposer-neural-decoder-never-emits-masked-action` | `proposal-contract` |
| 30 | `tests/test_neural_proposer.py::test_proposal_model_capacity_is_bounded` | `assertion:neural-proposer-proposal-model-capacity-is-bounded` | `proposal-contract` |
| 31 | `tests/test_neural_realizer_weight_use.py::TestNeuralRealizerWeightUse::test_normal_answer_cannot_fall_back_when_network_fails` | `assertion:neural-realizer-weight-use-test-neural-realizer-weight-use-normal-answer-cannot-fall-back-when-network-fails` | `weight-use-contract` |
| 32 | `tests/test_neural_realizer_weight_use.py::TestNeuralRealizerWeightUse::test_normal_realization_invokes_loaded_weights` | `assertion:neural-realizer-weight-use-test-neural-realizer-weight-use-normal-realization-invokes-loaded-weights` | `weight-use-contract` |
| 33 | `tests/test_neural_realizer_weight_use.py::TestNeuralRealizerWeightUse::test_normal_realization_records_decoder_invocations` | `assertion:neural-realizer-weight-use-test-neural-realizer-weight-use-normal-realization-records-decoder-invocations` | `weight-use-contract` |
| 34 | `tests/test_neural_realizer_weight_use.py::TestNeuralRealizerWeightUse::test_normal_realization_records_model_identity` | `assertion:neural-realizer-weight-use-test-neural-realizer-weight-use-normal-realization-records-model-identity` | `weight-use-contract` |
| 35 | `tests/test_neural_realizer_weight_use.py::TestNeuralRealizerWeightUse::test_zero_weight_realizer_loses_domain_generation_accuracy` | `assertion:neural-realizer-weight-use-test-neural-realizer-weight-use-zero-weight-realizer-loses-domain-generation-accuracy` | `weight-use-contract` |
| 36 | `tests/test_neural_weight_use.py::test_release_proposal_invokes_loaded_weights` | `assertion:neural-weight-use-release-proposal-invokes-loaded-weights` | `weight-use-contract` |
| 37 | `tests/test_neural_weight_use.py::test_weight_ablation_breaks_learned_selection` | `assertion:neural-weight-use-weight-ablation-breaks-learned-selection` | `weight-use-contract` |
| 38 | `tests/test_production_proposer_cutover.py::test_compatible_new_designation_keeps_model_active` | `assertion:production-proposer-cutover-compatible-new-designation-keeps-model-active` | `selection-contract` |
| 39 | `tests/test_production_proposer_cutover.py::test_neural_profile_loads_from_artifact` | `assertion:production-proposer-cutover-neural-profile-loads-from-artifact` | `selection-contract` |
| 40 | `tests/test_training_isolation.py::test_combined_trainable_capacity_is_bounded` | `assertion:training-isolation-combined-trainable-capacity-is-bounded` | `selection-contract` |
| 41 | `tests/test_training_isolation.py::test_model_uses_dynamic_semantic_slots_not_ref_spelling` | `assertion:training-isolation-model-uses-dynamic-semantic-slots-not-ref-spelling` | `proposal-contract` |
| 42 | `tests/test_training_isolation.py::test_realizer_release_artifact_pins_all_semantic_inputs` | `assertion:training-isolation-realizer-release-artifact-pins-all-semantic-inputs` | `realization-contract` |
| 43 | `tests/test_training_isolation.py::test_release_artifact_pins_all_semantic_inputs` | `assertion:training-isolation-release-artifact-pins-all-semantic-inputs` | `proposal-contract` |

## Appendix B: Forbidden implementation shortcuts

- Do not change or regenerate `governance/test_inventory.json`.
- Do not mark deferred neural tests as passed, skipped, xfailed, historical, or retired.
- Do not retain old test modules merely to satisfy source collection.
- Do not add a generic concept fallback, phrase matcher, template realizer fallback, bootstrap proposer fallback, pickle loader, or legacy fixture shim.
- Do not weaken assertion identity, owner selector, rewrite, AST hash, document authority, admission evidence, or generated-artifact checks.
- Do not claim R5 admission or append R5 green in this increment.
