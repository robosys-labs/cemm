# Hybrid MVP R1 Legacy-Test Retirement Implementation Plan

> **Completed historical evidence:** This document records an earlier tranche;
> it is not an executable current plan and owns no phase status. Current status
> is derived from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire three obsolete R1 predecessor tests already replaced by reviewed R3 successors, without adding runtime compatibility behavior, then prove G0 through R4 pass from the merged Hybrid MVP branch.

**Architecture:** Remove the obsolete executable predecessor nodes and their literal metadata, promote the existing reviewed R3 successor nodes to independent lineage roots by removing only their `supersedes_node_id` fields, and remove the predecessors from the exact R1 phase selector. Preserve the immutable predecessor inventory, regenerate the living G0 receipt from the existing validation reconstruction owner, and replay all phase gates.

**Tech Stack:** Python 3, pytest, literal AST test metadata, canonical JSON, PowerShell, Git.

---

## File map

- `tests/test_r1_episode_runtime_path.py` — remove two obsolete R1 episode tests, their metadata, and imports/helper code used only by them.
- `tests/test_r1_phase_integration.py` — remove the obsolete R1 composition expectation, its metadata, and imports used only by it.
- `tests/test_r3_closeout_successors.py` — preserve the two reviewed episode successor tests while promoting them from successor leaves to current lineage roots.
- `tests/test_r3_lineage_successors.py` — preserve the reviewed composition successor while promoting it to a current lineage root.
- `configs/validation_gates.json` — remove the three retired nodes from the exact `r1_phase_tests` selector.
- `artifacts/validation/TEST_INVENTORY_RECEIPT.json` — regenerate the living canonical receipt from current source metadata.
- `governance/test_inventory.json` — verify unchanged; it remains immutable predecessor evidence.

### Task 1: Record the failing legacy boundary

**Files:**
- Read: `tests/test_r1_episode_runtime_path.py`
- Read: `tests/test_r1_phase_integration.py`
- Read: `tests/test_r3_closeout_successors.py`
- Read: `tests/test_r3_lineage_successors.py`

- [ ] **Step 1: Run the R1 phase gate before deletion**

Run from `hybrid_mvp/`:

```powershell
python scripts/validate_mvp.py --tier phase --phase R1
```

Expected: FAIL with exactly three legacy failures: the two R1 episode tests fail because `HybridRuntime` requires `r3_owner`, and the R1 composition test receives `CycleStatus.PARTIAL` instead of its retired `CycleStatus.UNSUPPORTED` expectation.

- [ ] **Step 2: Prove every failed predecessor has one reviewed R3 successor**

Run:

```powershell
rg -n "supersedes_node_id.*(test_r1_episode_builder_uses_process_and_separates_derivation_from_meaning|test_r1_episode_codec_is_strict_bounded_and_authority_bound|test_r1_composition_root_runs_each_orient_transform_once)" tests/test_r3_closeout_successors.py tests/test_r3_lineage_successors.py
```

Expected: exactly three metadata matches, one for each failed predecessor.

### Task 2: Retire the obsolete R1 predecessor nodes

**Files:**
- Modify: `tests/test_r1_episode_runtime_path.py`
- Modify: `tests/test_r1_phase_integration.py`
- Modify: `tests/test_r3_closeout_successors.py`
- Modify: `tests/test_r3_lineage_successors.py`
- Modify: `configs/validation_gates.json`

- [ ] **Step 1: Delete the two obsolete episode tests and their metadata**

In `tests/test_r1_episode_runtime_path.py`, delete:

```python
def _runtime_fixture():
    ...

def test_r1_episode_builder_uses_process_and_separates_derivation_from_meaning():
    ...

def test_r1_episode_codec_is_strict_bounded_and_authority_bound(monkeypatch):
    ...
```

Delete the two matching entries from `__cemm_test_inventory__`. Retain `test_r1_episode_source_has_no_fixture_proposal_or_duplicate_result_path` and its metadata unchanged. Remove imports that become unused; the resulting module needs only `inspect`, `Path`, `EpisodeBuilder`, and `HybridRuntime`.

- [ ] **Step 2: Delete the obsolete composition test and its metadata**

In `tests/test_r1_phase_integration.py`, delete:

```python
def test_r1_composition_root_runs_each_orient_transform_once(monkeypatch):
    ...
```

Delete its matching metadata entry. Retain `test_r1_bootstrap_requires_profile_and_fails_later_profiles_closed` unchanged. Remove imports that become unused; the resulting module needs only `inspect`, `Path`, `pytest`, `load_runtime`, and `MissingOwner`.

- [ ] **Step 3: Promote the reviewed R3 successors to lineage roots**

Remove only the `supersedes_node_id` field from these three metadata records:

```text
tests/test_r3_closeout_successors.py::test_r3_successor_fdc717e6c26ffcec5598
tests/test_r3_closeout_successors.py::test_r3_successor_3e9b731d0d9a6f6936bc
tests/test_r3_lineage_successors.py::test_r3_composition_root_runs_each_orient_transform_once_and_continues_past_verify
```

Do not change their function bodies, assertion refs, activation phases, roles, or AST hashes.

- [ ] **Step 4: Remove retired nodes from the exact R1 selector**

In `configs/validation_gates.json`, remove the same three node IDs from `steps.r1_phase_tests.exact_nodes`. Keep the remaining five R1 phase nodes sorted and unchanged.

- [ ] **Step 5: Verify the source deletion is exact**

Run:

```powershell
rg -n "test_r1_episode_builder_uses_process_and_separates_derivation_from_meaning|test_r1_episode_codec_is_strict_bounded_and_authority_bound|test_r1_composition_root_runs_each_orient_transform_once" tests/test_r1_episode_runtime_path.py tests/test_r1_phase_integration.py configs/validation_gates.json
```

Expected: no matches.

### Task 3: Reconstruct governed metadata and the living receipt

**Files:**
- Verify unchanged: `governance/test_inventory.json`
- Modify: `artifacts/validation/TEST_INVENTORY_RECEIPT.json`

- [ ] **Step 1: Verify R3/R4 literal AST metadata**

Run:

```powershell
python scripts/verify_r3_r4_test_metadata.py
```

Expected: PASS. Metadata-only lineage promotion does not change successor function AST hashes.

- [ ] **Step 2: Reconstruct and write the canonical G0 receipt**

Run this exact reconstruction from `hybrid_mvp/`:

```powershell
@'
from pathlib import Path
import sys

root = Path.cwd()
sys.path.insert(0, str(root / "scripts"))
import validate_mvp
import test_inventory_core

gate = validate_mvp._validation_gate
inventory_path = root / "governance" / "test_inventory.json"
inventory_sha = test_inventory_core.verify_document_authority_pin(root, inventory_path)
inventory = test_inventory_core.load_and_verify(
    root,
    inventory_path,
    phase="G0",
    enforce_reviewed_counts=True,
    expected_sha256=inventory_sha,
)
graph, _ = gate._load_gate_graph_with_source(root / "configs" / "validation_gates.json")
selector = gate.validate_inventory_contract(graph, inventory, phase="G0")
authority_raw = (root / "docs" / "DOCUMENT_AUTHORITY.json").read_bytes()
receipt = gate._expected_g0_inventory_receipt(
    authority_sha256=gate.hashlib.sha256(authority_raw).hexdigest(),
    inventory_sha256=inventory_sha,
    inventory=inventory,
    selector=selector,
)
(root / "artifacts" / "validation" / "TEST_INVENTORY_RECEIPT.json").write_bytes(
    gate.canonical_json_bytes(receipt)
)
'@ | python -
```

Expected: exit 0 and canonical receipt bytes with no unreviewed fields.

- [ ] **Step 3: Verify deterministic receipt generation**

Run the complete reconstruction twice and compare exact bytes:

```powershell
$receipt = 'artifacts/validation/TEST_INVENTORY_RECEIPT.json'
$first = [IO.File]::ReadAllBytes((Resolve-Path $receipt))
@'
from pathlib import Path
import sys

root = Path.cwd()
sys.path.insert(0, str(root / "scripts"))
import validate_mvp
import test_inventory_core

gate = validate_mvp._validation_gate
inventory_path = root / "governance" / "test_inventory.json"
inventory_sha = test_inventory_core.verify_document_authority_pin(root, inventory_path)
inventory = test_inventory_core.load_and_verify(
    root, inventory_path, phase="G0", enforce_reviewed_counts=True,
    expected_sha256=inventory_sha,
)
graph, _ = gate._load_gate_graph_with_source(root / "configs" / "validation_gates.json")
selector = gate.validate_inventory_contract(graph, inventory, phase="G0")
authority_raw = (root / "docs" / "DOCUMENT_AUTHORITY.json").read_bytes()
receipt = gate._expected_g0_inventory_receipt(
    authority_sha256=gate.hashlib.sha256(authority_raw).hexdigest(),
    inventory_sha256=inventory_sha,
    inventory=inventory,
    selector=selector,
)
(root / "artifacts" / "validation" / "TEST_INVENTORY_RECEIPT.json").write_bytes(
    gate.canonical_json_bytes(receipt)
)
'@ | python -
$second = [IO.File]::ReadAllBytes((Resolve-Path $receipt))
if (-not [Linq.Enumerable]::SequenceEqual($first, $second)) {
    throw "G0 receipt generation is nondeterministic"
}
```

Expected: hashes are identical.

- [ ] **Step 4: Verify source-only inventory for every closed phase**

Run:

```powershell
foreach ($phase in 'G0','R1','R2','R3','R4') {
    python scripts/check_test_inventory.py --phase $phase --source-only
    if ($LASTEXITCODE -ne 0) { throw "inventory failed for $phase" }
}
```

Expected: all five commands exit 0; the retired nodes are absent, and the three R3 assertion identities each have one active root.

- [ ] **Step 5: Prove the immutable predecessor inventory did not change**

Run:

```powershell
git diff --exit-code -- governance/test_inventory.json
```

Expected: exit 0 with no diff.

### Task 4: Verify G0 through R4 and preserve R4 behavior

**Files:**
- Test: `tests/test_r3_closeout_successors.py`
- Test: `tests/test_r3_lineage_successors.py`
- Test: governed phase suites G0 through R4
- Test: authentic R4 corpus diagnostics

- [ ] **Step 1: Run the three preserved successor tests directly**

Run:

```powershell
python -m pytest `
  tests/test_r3_closeout_successors.py::test_r3_successor_fdc717e6c26ffcec5598 `
  tests/test_r3_closeout_successors.py::test_r3_successor_3e9b731d0d9a6f6936bc `
  tests/test_r3_lineage_successors.py::test_r3_composition_root_runs_each_orient_transform_once_and_continues_past_verify `
  -q -p no:cacheprovider
```

Expected: 3 passed.

- [ ] **Step 2: Run every phase gate in dependency order**

Run:

```powershell
foreach ($phase in 'G0','R1','R2','R3','R4') {
    python scripts/validate_mvp.py --tier phase --phase $phase
    if ($LASTEXITCODE -ne 0) { throw "phase gate failed for $phase" }
}
```

Expected: every phase returns `"disposition":"passed"`. R1 selects five current tests and reports no compatibility fallback.

- [ ] **Step 3: Recheck the authentic R4 corpus**

Run:

```powershell
python scripts/diagnose_r4_cases.py `
  --environment cemm_authoritative_hybrid.r4_environment:build_environment `
  --store-root "$env:TEMP\cemm-r1-retirement-r4-diagnostic" `
  --output "$env:TEMP\cemm-r1-retirement-r4-diagnostic.json"
```

Expected: 400 cases, 400 passed, 0 failed, 0 errors.

- [ ] **Step 4: Check release diff and workspace preservation**

Run:

```powershell
git diff --check
git status --short
```

Expected: only the two R1 test modules, two R3 successor metadata modules, validation config, living receipt, and this plan are modified or new; pre-existing unrelated untracked files remain untouched.

### Task 5: Commit the retirement

**Files:**
- Modify: `tests/test_r1_episode_runtime_path.py`
- Modify: `tests/test_r1_phase_integration.py`
- Modify: `tests/test_r3_closeout_successors.py`
- Modify: `tests/test_r3_lineage_successors.py`
- Modify: `configs/validation_gates.json`
- Modify: `artifacts/validation/TEST_INVENTORY_RECEIPT.json`
- Create: `docs/superpowers/plans/2026-08-12-r1-legacy-test-retirement-plan.md`

- [ ] **Step 1: Stage only the reviewed scope**

Run:

```powershell
git add -- `
  hybrid_mvp/tests/test_r1_episode_runtime_path.py `
  hybrid_mvp/tests/test_r1_phase_integration.py `
  hybrid_mvp/tests/test_r3_closeout_successors.py `
  hybrid_mvp/tests/test_r3_lineage_successors.py `
  hybrid_mvp/configs/validation_gates.json `
  hybrid_mvp/artifacts/validation/TEST_INVENTORY_RECEIPT.json `
  hybrid_mvp/docs/superpowers/plans/2026-08-12-r1-legacy-test-retirement-plan.md
```

Expected: unrelated untracked diagnostics are not staged.

- [ ] **Step 2: Inspect and commit**

Run:

```powershell
git diff --cached --check
git diff --cached --stat
git commit -m "test(r1): retire superseded phase assertions"
```

Expected: one focused commit with no runtime implementation change.

- [ ] **Step 3: Verify committed state**

Run:

```powershell
git show --stat --oneline HEAD
git status --short --branch
```

Expected: the retirement commit is at HEAD; only pre-existing unrelated untracked files remain.
