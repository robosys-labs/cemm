# R4 Partition Corrective Replay Implementation Plan

> **Superseded execution evidence:** This document is retained for forensic
> history only. It cannot authorize current work or phase status. Current status
> is derived from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).
> The August 29 R4.1 data/supervision amendment supersedes conflicting
> partition, feasibility, gold and realization instructions.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Invalidate the vacuous admitted R4 partition boundary, replace it with one globally coherent seven-axis leakage graph and four authenticated data classes, migrate the active R5 train-only foundation to the new R4 train capability, regenerate deterministic R4 artifacts, and re-admit R4 while R5 remains red.

**Architecture:** Preserve every exact protected identity from the seven R4 axes as a namespaced leakage hyperedge, build one deterministic connected-component graph, and assign whole components once to `train`, `selection`, `calibration`, or `frozen_test` with an exact integer stratification objective. R4 integrity owners see the complete split graph; consumers receive class-scoped capabilities that reveal one payload only. Hard-cut the old per-axis assignment/intersection ABI and legacy three-way partition authority rather than adapting them.

**Tech Stack:** Python 3, pytest, strict canonical JSON/JSONL, SHA-256 content references, deterministic union/find and integer bin packing, append-only replay governance, Git worktrees, PowerShell.

---

## Release invariants

- The corrective branch remains scoped to `hybrid_mvp/`; root adoption and root runtime files do not change.
- G0-R3 remain green. R4 is appended red before source/artifact replacement and returns green only through a new clean repository-owned admission. R5-R8 remain red.
- `governance/test_inventory.json` remains byte-identical unless a separately reviewed immutable-inventory migration is proven necessary. Later tests use literal metadata and exact succession.
- Every exact protected identity from general, lexical, semantic-target, topology, dialogue, mutation, and realization axes participates in the global leakage graph.
- Standalone coarse values such as `language=en`, `obligation=none`, and `outcome=supported` never create leakage edges.
- No connected component is split. If four-class feasibility fails, implementation stops for reviewed corpus expansion.
- All four payloads are nonempty, disjoint, exhaustive, canonical, and content-addressed.
- Training receives only the authenticated train capability. Selection, calibration, and frozen-test consumers remain unavailable in this increment.
- The legacy `data/partitions` authority, `PartitionManifest`, `Partitioner`, and three-way loader do not survive as compatibility paths.
- R4 generation and verification compute no model metric and perform no neural training.
- Every validation tier remains within eight steps and starts at most one pytest process.
- Across closeout, run one complete G0-R5 phase sweep, let R4 admission own the one full active-suite process, and do not repeat either after the ledger-only commit; aggregate broad pytest is at most seven processes and 1,800 seconds on the reviewed Windows host.
- The progress tracker is operational evidence only; `governance/replay_status.jsonl` remains the sole effective replay-status owner.

## Command convention

Run Python, pytest, and script commands from the linked worktree's
`hybrid_mvp/` directory. Run `git` commands from the linked worktree root, or
prefix their paths with `hybrid_mvp/` exactly as shown. Every task must record
the actual linked worktree root rather than copy the historical folder name
from an older plan.

## File map

### Governance and documentation

- `docs/DOCUMENT_AUTHORITY.json` — govern the approved corrective spec/plan and classify displaced R4 partition claims.
- `docs/ABI_REGISTRY.md` — retire Partition Axis Manifest ABI 2 and Training Allowlist ABI 2; register the new partition/capability/build ABIs.
- `docs/ARCHITECTURE.md` — describe the corrected R4→R5 data boundary without copying mutable phase status.
- `docs/superpowers/specs/2026-08-14-r4-partition-corrective-replay-design.md` — approved governing architecture and exact defect binding.
- `docs/superpowers/plans/2026-08-14-r4-partition-corrective-replay-plan.md` — this implementation authority.
- `docs/superpowers/progress/2026-08-14-r4-partition-corrective-replay-progress.md` — non-authoritative evidence tracker, updated at reviewed checkpoints.
- `governance/replay_status.jsonl` — append red invalidation, then later green re-admission; never rewrite prior rows.
- `tests/test_replay_governance.py` — authority, exact defect binding, tracker non-authority, and transition-order guards.

### Partition contracts and implementation

- `src/cemm_authoritative_hybrid/r4_partition_contracts.py` — strict immutable wire ABIs for hyperedges, labels, components, partition evidence, split manifest, sufficiency receipt, and class capability.
- `src/cemm_authoritative_hybrid/r4_partition_config.py` — strict reviewed Partition Config ABI 1 parser and content identity.
- `src/cemm_authoritative_hybrid/r4_partitions.py` — exact seven-axis extraction, union/find, globally coherent allocator, and artifact construction.
- `src/cemm_authoritative_hybrid/r4_partition_verify.py` — independent reconstruction, sufficiency validation, and purpose-bound capability authentication.
- `configs/r4_partitions.json` — reviewed Partition Config ABI 1 seed, four ratios, bounds, integer objective, and approved sufficiency minima/maxima.
- `schemas/r4_partition_evidence.schema.json` — Partition Evidence ABI 3.
- `schemas/r4_split_manifest.schema.json` — R4 Split Manifest ABI 1.
- `schemas/r4_partition_sufficiency.schema.json` — R4 Partition Sufficiency ABI 1.
- `schemas/r4_class_capability.schema.json` — R4 Class Capability ABI 1.
- `schemas/r4_class_authorization.schema.json` — admitted class-scoped trust projection without sibling disclosure.
- `schemas/r4_partition_config.schema.json` — reviewed seed, ratios, bounds, integer objective, minima/maxima, and feasibility binding.
- `tests/test_r4_partition_contracts.py` — exact schemas/decoders and corruption tests.
- `tests/test_r4_partition_global_assignment.py` — hyperedge extraction, component construction, feasibility, deterministic allocation, and independent verification.
- `scripts/analyze_r4_partition_feasibility.py` — read-only source-derived feasibility report and candidate minima generator.
- `scripts/publish_r4_feasibility_basis.py` — strict candidate/config comparison; unchanged atomic publication or explicit reviewed config migration.
- `artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json` — source/component/solver basis, candidate minima, and satisfying witness material; independent of final config.
- `artifacts/validation/R4_PARTITION_FEASIBILITY.json` — final receipt binding the reviewed config back to that basis; never model-derived.

### R4 pipeline and artifacts

- `src/cemm_authoritative_hybrid/r4_pipeline.py` — consume global partition result and emit Build Receipt ABI 4.
- `src/cemm_authoritative_hybrid/r4_admission.py` — independently reconstruct every new artifact and Build Receipt ABI 4.
- `scripts/build_r4_artifacts.py` — strict config load and four-payload generation.
- `schemas/r4_build_receipt.schema.json` — exact Build Receipt ABI 4.
- `tests/test_r4_mutations_and_partitions.py` — current mutation owner plus successor partition assertions.
- `tests/test_r4_admission.py` — exact ABI 4 reconstruction and tamper cases.
- `tests/test_r4_authentic_episodes.py` — build receipt and payload lineage.
- `artifacts/r4/partition_evidence.json` — complete global leakage/label/component assignment evidence.
- `artifacts/r4/split_manifest.json` — global integrity-owner view of all four payloads.
- `artifacts/r4/partition_sufficiency.json` — non-vacuous feasibility/coverage receipt.
- `artifacts/r4/splits/*.jsonl` — canonical train, selection, calibration, and frozen-test episode payloads.
- `artifacts/r4/capabilities/train.json` — active class-scoped train capability.
- `artifacts/r4/capabilities/train_authorization.json` — class-scoped projection containing the expected train capability identity and exact artifact-graph ancestry; its ref/SHA is authenticated by the repository admission receipt.
- `artifacts/r4/BUILD_RECEIPT.json` — ABI 4 complete artifact graph.
- `artifacts/r4/partitions/*.json`, `artifacts/r4/training_allowlist.json` — delete after ABI 4 generation.

### R5 train-only boundary hard cut

- `src/cemm_authoritative_hybrid/r4_partition_access.py` — bounded class-capability loader and train snapshot owner.
- `src/cemm_authoritative_hybrid/training.py` — consume authenticated R4 train capability/snapshot; remove three-way manifest constants and loader.
- `src/cemm_authoritative_hybrid/partitions.py` — delete after every valid current consumer moves.
- `scripts/partition_episodes.py` — delete retired three-way generator.
- `scripts/train_proposer.py`, `scripts/train_realizer.py` — release mode consumes the authenticated train capability and rejects `--episodes` bypass.
- `configs/proposal_release.json`, `configs/realizer_release.json` — replace legacy episode paths with the exact train-capability path/ref contract.
- `tests/test_r5_data_isolation.py` — successor tests for the active train-only boundary and sibling non-disclosure.
- `tests/test_r4_training_partition_boundary.py` — current R4→R5 train capability boundary.
- `tests/test_partition_leakage.py`, `tests/test_hard_negatives.py`, `tests/test_gap_episode_coverage.py` — lineage-audit, migrate valid assertions to current successors, then delete stale modules where authorized.
- `scripts/calibrate_models.py`, `scripts/evaluate_cemm.py` — remove or structurally quarantine legacy split entry points; current replacements belong to R5/R7 and are not implemented here.
- `_test_eval.py`, `_test_eval2.py`, `_test_eval3.py`, `_test_train.py` — tracked diagnostic consumers at the Hybrid root; migrate `_test_train.py` to the train capability or retire it, and retire the evaluation scripts until the R7 capability owner exists.
- `tests/test_release_thresholds.py`, `tests/test_gap_owner_evaluation.py` — preserve future R7 assertion lineage while rejecting executable legacy evaluation entry points in R4/R5.
- `data/partitions/**` — delete as active authority after all current consumers and tests move.

### Validation and generated evidence

- `configs/validation_gates.json` — exact R4/R5 selectors and input paths; no new owner or pytest process.
- `scripts/check_r3_r4_structure.py` — reject legacy partition authority and incomplete four-class artifacts.
- `scripts/audit_legacy_test_hard_cut.py` — reject reintroduced legacy split loaders/config paths where within its R5 scope.
- `artifacts/validation/TEST_INVENTORY_RECEIPT.json` — mechanically reconstruct after literal test metadata changes.
- `artifacts/validation/R5_TEST_DISPOSITIONS.json` — mechanically regenerate when R5 literal metadata changes; disposition counts remain 17/25/1.
- `artifacts/validation/runs/<run-ref>.json` — new R4 admission receipt only after a clean committed ABI 4 graph passes.
- `scripts/validation_gate.py`, `scripts/update_replay_status.py` — version/source-aware R4 evidence policies preserve historical ABI 3 reconstruction while current candidates require ABI 4 paths.
- `scripts/run_r4_corrective_validation.py` — bounded controller with `phase-sweep` and `admission` modes for the sole six-phase sweep and sole admission active run.
- `scripts/publish_r4_candidate.py` — dry-run/commit transactional checked-in artifact-tree publisher with rollback.
- `scripts/run_r4_release_training.py` — parent trust resolver and isolated train-only child launcher; it is not a neural activation command.
- `tests/test_r4_validation_gate.py`, `tests/test_replay_governance.py` — historical/current evidence-policy separation and artifact-only provenance.

### Historical/current evidence policy constants

The implementation defines these exact, sorted semantic sets in
`validation_gate.py`. Because `update_replay_status.py` must reject dirty paths
before it can securely import governed source, it keeps an independently pinned
syntactic projection of their bounded union. Governance tests require exact
projection equality; the updater never imports mutable source before preflight:

```python
R4_SHARED_EVIDENCE_PATHS = (
    "artifacts/r4/BUILD_RECEIPT.json",
    "artifacts/r4/episodes.jsonl",
    "artifacts/r4/expanded_cases.jsonl",
    "artifacts/r4/expected_contracts.jsonl",
    "artifacts/r4/expected_derivations.jsonl",
    "artifacts/r4/mutation_observations.jsonl",
    "artifacts/r4/mutations.jsonl",
    "artifacts/r4/structural_sufficiency.json",
)
R4_ABI3_ONLY_EVIDENCE_PATHS = (
    "artifacts/r4/partitions/dialogue.json",
    "artifacts/r4/partitions/general.json",
    "artifacts/r4/partitions/lexical.json",
    "artifacts/r4/partitions/mutation.json",
    "artifacts/r4/partitions/realization.json",
    "artifacts/r4/partitions/semantic_target.json",
    "artifacts/r4/partitions/topology.json",
    "artifacts/r4/training_allowlist.json",
)
R4_ABI4_ONLY_EVIDENCE_PATHS = (
    "artifacts/r4/capabilities/train.json",
    "artifacts/r4/capabilities/train_authorization.json",
    "artifacts/r4/partition_evidence.json",
    "artifacts/r4/partition_sufficiency.json",
    "artifacts/r4/split_manifest.json",
    "artifacts/r4/splits/calibration.jsonl",
    "artifacts/r4/splits/frozen_test.jsonl",
    "artifacts/r4/splits/selection.jsonl",
    "artifacts/r4/splits/train.jsonl",
)
```

Historical run reconstruction selects `shared + ABI3-only` from the stored
receipt/source-base. Current candidate admission selects `shared + ABI4-only`.
Only dirty-path containment uses their bounded union.

---

### Task 1: Govern the approved corrective replay and exact defect binding

**Files:**
- Modify: `docs/DOCUMENT_AUTHORITY.json`
- Modify: `tests/test_replay_governance.py`
- Modify: `configs/validation_gates.json`
- Modify: `docs/superpowers/progress/2026-08-14-r4-partition-corrective-replay-progress.md`
- Read: `docs/superpowers/specs/2026-08-14-r4-partition-corrective-replay-design.md`
- Read: `docs/superpowers/plans/2026-08-14-r4-partition-corrective-replay-plan.md`

- [ ] **Step 1: Write the authority and tracker regressions**

Add literal R4 phase metadata for tests that require:

```python
def test_r4_partition_corrective_authority_is_exact() -> None:
    authority = _strict_document_authority()
    governing = set(authority["governing_documents"])
    assert "docs/superpowers/specs/2026-08-14-r4-partition-corrective-replay-design.md" in governing
    assert "docs/superpowers/plans/2026-08-14-r4-partition-corrective-replay-plan.md" in governing


def test_r4_partition_defect_binding_matches_current_pre_invalidation_artifacts() -> None:
    allowlist = ROOT / "artifacts/r4/training_allowlist.json"
    receipt = ROOT / "artifacts/r4/BUILD_RECEIPT.json"
    design = (ROOT / "docs/superpowers/specs/2026-08-14-r4-partition-corrective-replay-design.md").read_text("utf-8")
    assert _sha256(allowlist) == "3c47c3e66771add72a541342a5669ef5c93286356eb1ae0c0de9eb86d9b3d2db"
    assert _sha256(receipt) == "0069ae2c8a301700498aba4801df96205f9166938e1b21d3336aa1768d75dec6"
    assert "training_allowlist_v2:51c0cc234805cdda54f8e2c7" in design
    assert "r4_build_v3:5d5eee0ee8c0e7bb1bcba522" in design


def test_corrective_tracker_is_operational_not_status_authority() -> None:
    text = (ROOT / "docs/superpowers/progress/2026-08-14-r4-partition-corrective-replay-progress.md").read_text("utf-8")
    assert "governance/replay_status.jsonl" in text
    assert "never replay-status authority" in text
    assert not re.search(r"run:[0-9a-f]{24}", text)
```

Do not hard-code a mutable live phase matrix in these tests.
Add the exact new phase nodes, in lexical order, to `r4_phase_tests` in the same
task. Keep them out of every owner selector because document authority is a
phase boundary, not a sixth R4 owner.

- [ ] **Step 2: Run RED**

Run:

```powershell
python -m pytest tests/test_replay_governance.py -q -p no:cacheprovider -k "r4_partition_corrective or partition_defect_binding or corrective_tracker"
```

Expected: authority test fails because the approved spec/plan are not yet governing.

- [ ] **Step 3: Promote exact authority**

Add the spec and plan to `governing_documents`. Keep the tracker outside authority. Do not alter the replay ledger or generated artifacts in this task. Add a narrow notice to the prior R4 repository-owned design/plan only if the authority test identifies a live conflicting partition claim; preserve their admission history.

- [ ] **Step 4: Refresh literal metadata and dependent receipts**

Run the exact Task 8 metadata/receipt command block now: R3/R4 refresh + verify,
R5 refresh, inline canonical `TEST_INVENTORY_RECEIPT.json` reconstruction, R5
disposition output/check, then a second zero-change refresh/idempotence pass.
Regenerate no R4 data artifact in this authority-only task.

- [ ] **Step 5: Run GREEN and commit**

Run:

```powershell
python -m pytest tests/test_replay_governance.py tests/test_test_inventory.py -q -p no:cacheprovider
python scripts/update_replay_status.py --verify-chain
python scripts/generate_r5_test_dispositions.py --check artifacts/validation/R5_TEST_DISPOSITIONS.json
git diff --check
```

Expected: tests and chain pass; the ledger remains unchanged. Update tracker P3 to `complete`, P4 to `in_progress`, record the governing commit after commit creation in a follow-up tracker-only commit.

Commit from the linked worktree root:

```powershell
git add -- hybrid_mvp/docs hybrid_mvp/tests/test_replay_governance.py hybrid_mvp/configs/validation_gates.json hybrid_mvp/artifacts/validation
git commit -m "docs(r4): govern partition corrective replay"
```

This current-file assertion is intentionally temporary and exists only before
the red append. Task 2 replaces it with a successor that authenticates the red
row's historical `source_base` before any old artifact is deleted.

### Task 2: Append and commit the truthful R4 red invalidation

**Files:**
- Modify: `governance/replay_status.jsonl`
- Modify: `docs/superpowers/progress/2026-08-14-r4-partition-corrective-replay-progress.md`

- [ ] **Step 1: Verify the exact clean source base**

Run:

```powershell
git status --short --branch
python scripts/update_replay_status.py --verify-chain
$sourceBase = (git rev-parse HEAD).Trim()
$ledgerHead = (Get-Content governance/replay_status.jsonl | Select-Object -Last 1 | ConvertFrom-Json).record_ref
```

Expected: clean branch; `$sourceBase` is the committed governing-document commit and contains the exact defect refs/hashes.

- [ ] **Step 2: Generate and review the red candidate**

Run:

```powershell
python scripts/update_replay_status.py --phase R4 --status red --dry-run | Tee-Object "$env:TEMP\r4-partition-red-candidate.json"
```

Expected: one canonical R4 red record with no admission run/gate refs, generic invalidation rationale, exact predecessor record ref, and `source_base=$sourceBase`. Independently verify that `git show "$sourceBase:hybrid_mvp/docs/superpowers/specs/2026-08-14-r4-partition-corrective-replay-design.md"` contains the four exact defect identities.

- [ ] **Step 3: Append only the reviewed candidate**

Extract the candidate `record_ref`, then run:

```powershell
$candidate = Get-Content -Raw "$env:TEMP\r4-partition-red-candidate.json" | ConvertFrom-Json
python scripts/update_replay_status.py --phase R4 --status red --expect-record-ref $candidate.record_ref --append
python scripts/update_replay_status.py --verify-chain
```

Expected effective state: G0-R3 green and R4-R8 red. No artifact or run receipt is created.

- [ ] **Step 4: Commit the append and tracker checkpoint**

Update tracker P4 to `complete`, P5 to `in_progress`, and record the invalidation commit event without copying a mutable effective-status matrix or admission run ref.

Commit:

```powershell
git add -- hybrid_mvp/governance/replay_status.jsonl hybrid_mvp/docs/superpowers/progress/2026-08-14-r4-partition-corrective-replay-progress.md
git diff --cached --check
git commit -m "governance(r4): invalidate vacuous partition evidence"
```

- [ ] **Step 5: Replace the temporary defect test with historical reconstruction**

Write the assertion-preserving successor before any artifact replacement. It
locates the exact new R4-red row, uses the existing bounded Git source reader to
load from that row's committed `source_base`, and verifies the four reviewed
old refs/hashes. It must not depend on current old-artifact paths. Refresh
literal succession metadata, the exact R4 phase selector, and generated test
receipts.

Run:

```powershell
python -m pytest tests/test_replay_governance.py -q -p no:cacheprovider -k "partition_defect_binding"
```

Expected: committed historical bytes authenticate even when a mutation fixture
removes or replaces the current old artifacts.

Commit:

```powershell
git add -- hybrid_mvp/tests/test_replay_governance.py hybrid_mvp/configs/validation_gates.json hybrid_mvp/artifacts/validation
git commit -m "test(r4): bind partition defect to invalidated source"
```

### Task 3: Define the hard-cut partition and class-capability ABIs

**Files:**
- Create: `src/cemm_authoritative_hybrid/r4_partition_contracts.py`
- Create: `src/cemm_authoritative_hybrid/r4_partition_config.py`
- Create: `schemas/r4_partition_evidence.schema.json`
- Create: `schemas/r4_split_manifest.schema.json`
- Create: `schemas/r4_partition_sufficiency.schema.json`
- Create: `schemas/r4_class_capability.schema.json`
- Create: `schemas/r4_class_authorization.schema.json`
- Create: `schemas/r4_partition_config.schema.json`
- Create: `tests/test_r4_partition_contracts.py`
- Modify: `docs/ABI_REGISTRY.md`

- [ ] **Step 1: Write strict ABI tests first**

Create tests for these exact frozen types and factory-only construction:

```python
@dataclass(frozen=True)
class LeakageHyperedge:
    axis: str
    key_namespace: str
    key_ref: str
    member_refs: tuple[str, ...]
    hyperedge_ref: str

@dataclass(frozen=True)
class StratificationLabel:
    namespace: str
    label_ref: str
    member_refs: tuple[str, ...]

@dataclass(frozen=True)
class GlobalPartitionComponent:
    component_ref: str
    source_set_ref: str
    partition_abi_version: Literal[3]
    member_refs: tuple[str, ...]
    hyperedge_refs: tuple[str, ...]
    split: Literal["train", "selection", "calibration", "frozen_test"]

@dataclass(frozen=True)
class PartitionEvidence:
    abi_version: Literal[3]
    evidence_ref: str
    source_set_ref: str
    config_ref: str
    hyperedges: tuple[LeakageHyperedge, ...]
    labels: tuple[StratificationLabel, ...]
    components: tuple[GlobalPartitionComponent, ...]

@dataclass(frozen=True)
class R4SplitManifest:
    abi_version: Literal[1]
    manifest_ref: str
    source_set_ref: str
    generator_source_revision: str
    authority_generation: str
    config_ref: str
    partition_evidence_ref: str
    partition_sufficiency_ref: str
    classes: tuple[SplitClassRecord, ...]

@dataclass(frozen=True)
class R4PartitionSufficiencyReceipt:
    abi_version: Literal[1]
    receipt_ref: str
    passed: bool
    class_counts: tuple[ClassCount, ...]
    dimension_rows: tuple[DimensionSufficiency, ...]

@dataclass(frozen=True)
class R4ClassCapability:
    abi_version: Literal[1]
    capability_ref: str
    purpose: Literal["training", "selection", "calibration", "evaluation"]
    split: Literal["train", "selection", "calibration", "frozen_test"]
    payload_path: str
    payload_ref: str
    payload_sha256: str
    payload_count: int
    source_set_ref: str
    split_manifest_ref: str

@dataclass(frozen=True)
class R4ClassAuthorization:
    abi_version: Literal[1]
    authorization_ref: str
    purpose: Literal["training", "selection", "calibration", "evaluation"]
    expected_capability_ref: str
    expected_capability_sha256: str
    artifact_graph_ref: str
    generator_source_revision: str
    authority_generation: str

@dataclass(frozen=True)
class R4PartitionConfig:
    abi_version: Literal[1]
    config_ref: str
    seed: int
    target_weights: tuple[SplitWeight, ...]
    bounds: PartitionBounds
    objective: PartitionObjective
    minima: tuple[DimensionMinimum, ...]
    maxima: tuple[DimensionMaximum, ...]
    feasibility_basis_ref: str
    minima_witness_ref: str
```

The content-address graph is acyclic and tested exactly:

```text
authenticated source/component/solver material
-> feasibility_basis_ref + minima_witness_ref
-> Partition Config ABI 1 config_ref
-> final feasibility receipt ref
-> split manifest / Build Receipt ABI 4
-> repository admission receipt
```

The config never names the final feasibility receipt. The basis never names the
config. Mutation tests change each edge independently and require downstream
reconstruction failure.

`artifact_graph_ref` is computed from source/config/evidence/sufficiency/manifest
and the one class capability, excluding both authorization and Build Receipt.
This avoids a content-address cycle: Build Receipt ABI 4 later binds the
authorization SHA, and the repository admission receipt becomes the external
trust root for that authorization identity.

Tests must reject unknown/missing fields, duplicate refs, unsorted tuples, noncanonical bytes, nonfinite values, path traversal, Windows absolute/device paths, sibling-class fields, invalid purpose/split pairing, unsupported ABI versions, empty hyperedges/components/classes, and any content-ref mismatch. Component ref material must bind `source_set_ref` and `partition_abi_version`. The class authorization has no sibling paths, refs, counts, hashes, or Build Receipt self-reference. A class capability cannot authenticate itself: a loader must receive an independently trusted expected authorization ref/SHA projected from an admitted R4 run receipt.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/test_r4_partition_contracts.py -q -p no:cacheprovider
```

Expected: import failure because the ABI owner does not exist.

- [ ] **Step 3: Implement minimal immutable contracts and Draft 2020-12 schemas**

Use existing `exact_fields`, `exact_int`, `exact_refs`, `exact_text`, and `stable_ref`. Do not import torch, pytest, training, or runtime owners. Set hard bounds:

```python
MAX_SOURCE_EPISODES = 4_096
MAX_HYPEREDGES = 32_768
MAX_LABELS = 32_768
MAX_MEMBERS_PER_RECORD = 4_096
MAX_HYPEREDGES_PER_EPISODE = 128
MAX_LABELS_PER_EPISODE = 128
MAX_TOTAL_HYPEREDGE_MEMBERSHIPS = 131_072
MAX_TOTAL_LABEL_MEMBERSHIPS = 131_072
MAX_COMPONENTS = 4_096
MAX_SOLVER_STATES = 250_000
MAX_SOLVER_KEY_INTS = 128
MAX_SOLVER_MEMORY_BYTES = 192 * 1024 * 1024
MAX_SOLVER_SECONDS = 120
MAX_EPISODE_INPUT_BYTES = 64 * 1024 * 1024
MAX_PARTITION_ARTIFACT_BYTES = 128 * 1024 * 1024
SPLITS = ("train", "selection", "calibration", "frozen_test")
```

Schemas must set `additionalProperties: false` at every object, exact ABI constants, bounded arrays/strings, and canonical split/purpose enums. Split Manifest ABI 1 directly binds `generator_source_revision`, `authority_generation`, and `config_ref`; corruption tests mutate each one. Partition Config ABI 1 owns the exact integer formulas, weights, scaling denominators, minima/maxima semantics, tie-break material, and all input/output/membership/component bounds.

- [ ] **Step 4: Run GREEN and independent schema validation**

```powershell
python -m pytest tests/test_r4_partition_contracts.py -q -p no:cacheprovider
@'
from pathlib import Path
import json
from jsonschema import Draft202012Validator
for path in Path("schemas").glob("r4_*partition*.schema.json"):
    Draft202012Validator.check_schema(json.loads(path.read_text("utf-8")))
for path in (
    Path("schemas/r4_class_capability.schema.json"),
    Path("schemas/r4_class_authorization.schema.json"),
    Path("schemas/r4_partition_config.schema.json"),
):
    Draft202012Validator.check_schema(json.loads(path.read_text("utf-8")))
'@ | python -
```

- [ ] **Step 5: Register ABI hard cuts and commit**

Mark Partition Axis Manifest ABI 2 and Training Allowlist ABI 2 retired. Register Partition Evidence ABI 3, Split Manifest ABI 1, Partition Sufficiency ABI 1, Class Capability ABI 1, Class Authorization ABI 1, Partition Config ABI 1, and Build Receipt ABI 4 without claiming generated artifacts or activation.

Commit:

```powershell
git add -- hybrid_mvp/src/cemm_authoritative_hybrid/r4_partition_contracts.py hybrid_mvp/src/cemm_authoritative_hybrid/r4_partition_config.py hybrid_mvp/schemas hybrid_mvp/tests/test_r4_partition_contracts.py hybrid_mvp/docs/ABI_REGISTRY.md
git commit -m "feat(r4): define global partition contracts"
```

### Task 4: Build the read-only seven-axis feasibility owner

**Files:**
- Modify: `src/cemm_authoritative_hybrid/r4_partitions.py`
- Create: `scripts/analyze_r4_partition_feasibility.py`
- Create: `scripts/publish_r4_feasibility_basis.py`
- Create: `tests/test_r4_partition_global_assignment.py`
- Create: `tests/test_publish_r4_feasibility_basis.py`
- Create: `artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json`
- Create: `artifacts/validation/R4_PARTITION_FEASIBILITY.json`
- Modify: `configs/r4_partitions.json`
- Modify: `docs/superpowers/progress/2026-08-14-r4-partition-corrective-replay-progress.md`

- [ ] **Step 1: Write RED extraction and anti-collapse tests**

Tests must construct small authentic episode fixtures and require:

```python
assert exact_axes(evidence.hyperedges) == (
    "general", "lexical", "semantic_target", "topology",
    "dialogue", "mutation", "realization",
)
assert no_hyperedge_for("language", "en")
assert normalized_surface_key("Hello", "en") == normalized_surface_key(" hello ", "en")
assert normalized_surface_key("hello", "en") != normalized_surface_key("hello", "fr")
assert same_exact_predicate_rows_share_component
assert same_exact_topology_rows_share_component
assert same_exact_obligation_descendants_share_component
assert same_exact_response_semantics_share_component
```

Add corruption cases where a missing/sentinel/coarse label attempts to become a hyperedge, a required exact axis identity is omitted, a label cannot reconstruct from its episode, and pairwise edge expansion exceeds the bounded hyperedge representation.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/test_r4_partition_global_assignment.py -q -p no:cacheprovider -k "hyperedge or label or component"
```

- [ ] **Step 3: Implement exact extraction and one global union/find**

Refactor `IndependentAxisPartitioner` into `GlobalLeakagePartitioner`. Remove `_bucket` and every per-axis split field. Each extractor returns `LeakageHyperedge` rows and `StratificationLabel` rows separately. Build a hyperedge membership map and union the first member with each later member once; do not serialize pairwise edges.

The source-derived feasibility operation returns exact class-independent evidence:

```python
@dataclass(frozen=True)
class PartitionFeasibility:
    source_count: int
    component_count: int
    largest_component_count: int
    component_size_histogram: tuple[tuple[int, int], ...]
    dimension_support: tuple[DimensionSupport, ...]
    four_nonempty_possible: bool
    infeasibility_reasons: tuple[str, ...]
    candidate_minima: tuple[DimensionMinimum, ...]
    assignment_witness: tuple[ComponentAssignment, ...]
    witness_objective_ref: str
```

Candidate minima are derived only from component support and reviewed target ratios. They must be positive, not exceed feasible component support, and contain no model/evaluation fields. The feasibility owner runs the exact bounded four-class solver and serializes a deterministic whole-component assignment witness satisfying every candidate minimum jointly. `four_nonempty_possible=true` is invalid without that witness.

- [ ] **Step 4: Add bounded strict feasibility CLI**

The analyzer reads only committed `artifacts/r4/episodes.jsonl`, `mutations.jsonl`, and reviewed config; it writes canonical evidence to the exact checked-in path or `--check`s it. It rejects symlink/reparse/path escape, reads with explicit byte/row bounds, and writes atomically. It has two explicit modes: `--basis` emits source/component/solver evidence, candidate minima, a deterministic satisfying witness, `feasibility_basis_ref`, and `minima_witness_ref` without reading or naming final config identity; `--final` requires the frozen config to bind those two basis identities and emits the final receipt bound to `config_ref`.

Write publisher RED tests before implementation: equal refs publish atomically;
different basis or witness ref returns exact exit 3 and preserves current/config
bytes; malformed/oversized/symlink/reparse candidates fail before write; injected
replace failure restores exact originals. Then implement the strict equal-only
publisher used by Task 5 and Task 9.

- [ ] **Step 5: Run the real feasibility checkpoint**

```powershell
python scripts/analyze_r4_partition_feasibility.py --basis --output artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json
python scripts/analyze_r4_partition_feasibility.py --basis --check artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json
python -m pytest tests/test_r4_partition_global_assignment.py tests/test_publish_r4_feasibility_basis.py -q -p no:cacheprovider
```

Expected: exact seven-axis reconstruction and `four_nonempty_possible=true`.

**STOP CONDITION:** if false, commit only the truthful feasibility evidence/tracker blocker, push it, and obtain approval for R4 corpus expansion. Do not implement the allocator, weaken an exact key, or change target ratios.

- [ ] **Step 6: Review and freeze exact minima**

Copy the basis's exact `candidate_minima` into `configs/r4_partitions.json` only after contract review confirms they derive solely from source/component support and the serialized witness satisfies them jointly. The config binds the checked-in basis ref and exact `minima_witness_ref`, but never the later final receipt. Freeze the config, then run `--final` so `R4_PARTITION_FEASIBILITY.json` binds `config_ref`, basis ref, minima/witness relation, solver ABI, and independently reconstructed satisfying assignment. Admission reconstructs every DAG edge. Record the reviewed basis/final/config refs in the tracker; do not record model results.

- [ ] **Step 7: Run GREEN and commit**

```powershell
python scripts/analyze_r4_partition_feasibility.py --final --output artifacts/validation/R4_PARTITION_FEASIBILITY.json
python scripts/analyze_r4_partition_feasibility.py --final --check artifacts/validation/R4_PARTITION_FEASIBILITY.json
python -m pytest tests/test_r4_partition_contracts.py tests/test_r4_partition_global_assignment.py -q -p no:cacheprovider
git diff --check
```

Commit:

```powershell
git add -- hybrid_mvp/src/cemm_authoritative_hybrid/r4_partitions.py hybrid_mvp/scripts/analyze_r4_partition_feasibility.py hybrid_mvp/scripts/publish_r4_feasibility_basis.py hybrid_mvp/tests/test_r4_partition_global_assignment.py hybrid_mvp/tests/test_publish_r4_feasibility_basis.py hybrid_mvp/configs/r4_partitions.json hybrid_mvp/artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json hybrid_mvp/artifacts/validation/R4_PARTITION_FEASIBILITY.json hybrid_mvp/docs/superpowers/progress
git commit -m "feat(r4): reconstruct leakage feasibility"
```

### Task 5: Implement deterministic four-class assignment and independent verification

**Files:**
- Modify: `src/cemm_authoritative_hybrid/r4_partitions.py`
- Create: `src/cemm_authoritative_hybrid/r4_partition_verify.py`
- Modify: `tests/test_r4_partition_global_assignment.py`
- Modify: `tests/test_r4_mutations_and_partitions.py`

- [ ] **Step 1: Write allocator RED tests**

Require exactly:

```python
SPLITS = ("train", "selection", "calibration", "frozen_test")
TARGET_WEIGHTS = {"train": 60, "selection": 15, "calibration": 15, "frozen_test": 10}
```

Tests assert whole-component assignment, four nonempty sets, exact 400-source coverage on the real corpus, deterministic result under input permutation, deterministic stable-ref tie breaking, integer-only score material, label balance within reviewed minima, and failure when a synthetic giant component makes four nonempty classes impossible.

Mutation tests alter one seed, ratio, objective weight, component member, hyperedge member, label member, split, or tie-break value and require independent verification failure.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/test_r4_partition_global_assignment.py tests/test_r4_mutations_and_partitions.py -q -p no:cacheprovider -k "assignment or verifier or partition"
```

- [ ] **Step 3: Implement canonical integer allocator**

The config owns these exact integer definitions:

```python
RATIO_DENOMINATOR = 100
RARITY_SCALE = 1_000_000

rare_label_score = sum(
    label_weight[label_ref] * (RARITY_SCALE // global_label_member_count[label_ref])
    for label_ref in component_label_refs
)

component_order = (-member_count, -rare_label_score, component_ref)

size_deviation = sum(
    abs(RATIO_DENOMINATOR * class_count[split] - source_count * target_weight[split])
    for split in SPLITS
)

label_deviation = sum(
    label_weight[label_ref]
    * abs(
        RATIO_DENOMINATOR * class_label_count[split, label_ref]
        - global_label_member_count[label_ref] * target_weight[split]
    )
    for split in SPLITS
    for label_ref in configured_label_refs
)

bound_violation = sum(
    max(0, minimum[split, dimension] - observed[split, dimension])
    + max(0, observed[split, dimension] - maximum[split, dimension])
    for split in SPLITS
    for dimension in configured_dimensions
)
```

For specification, `full_objective(state)` is the dense formula above. The
production allocator maintains its current tuple and computes a candidate by
subtracting the old terms and adding new terms only for the chosen class,
component-member count, component dimension rows, and component label refs:

```python
candidate_objective = (
    current_size_deviation - old_size_term[split] + new_size_term[split],
    current_label_deviation
    + sum(new_label_term[split, label] - old_label_term[split, label]
          for label in component_label_refs),
    current_bound_violation
    + sum(new_bound_term[split, dimension] - old_bound_term[split, dimension]
          for dimension in component_dimension_refs),
    stable_ref("r4_partition_tie", {
        "component": component_ref, "split": split, "seed": seed,
    }),
)
```

Choose the lexicographic minimum only among candidate placements for which the bounded joint-feasibility solver proves a completion satisfying all four nonempty classes and every exact minimum/maximum. There is no four-component preassignment or hidden bootstrap rule. The solver consumes the same canonical component order, memoizes exact remaining class/dimension capacities, emits the witness checked in by Task 4, and fails closed at `MAX_SOLVER_STATES` instead of weakening a bound. Do not use floats, random module state, or iteration-order ties.

Every delta is tested equal to a slow `full_objective` recomputation after each
placement. Sparse counters are updated from the component's membership/label
rows, so the scoring pass is bounded by
`O(total_memberships * len(SPLITS))`, not `components * all_labels`. Tests
instrument counter updates and require them to stay below
`4 * (MAX_TOTAL_HYPEREDGE_MEMBERSHIPS + MAX_TOTAL_LABEL_MEMBERSHIPS)` for the
real corpus.

`MAX_SOLVER_STATES` is one aggregate build-wide budget, not per branch. A memo
key contains only component index, four class counts, and configured-dimension
remaining integer capacities; config also sets `MAX_SOLVER_KEY_INTS = 128`,
`MAX_SOLVER_MEMORY_BYTES = 192 * 1024 * 1024`, and
`MAX_SOLVER_SECONDS = 120`. The analyzer samples RSS with the existing process
observer and reports state count/key width/peak RSS/wall duration. Exceeding a
resource bound returns typed `FeasibilityIndeterminate(reason="resource_bound")`
and triggers the plan stop condition; it is not semantic infeasibility.

- [ ] **Step 4: Implement an independent verifier**

`r4_partition_verify.py` must re-extract hyperedges/labels from authenticated episodes and mutations, rebuild union/find and component refs independently, recompute assignment objective/config refs, verify source coverage/disjointness/non-vacuity/minima, and compare exact evidence/manifest bytes. It must not call the allocator's component or assignment helper.

- [ ] **Step 5: Run GREEN, performance bound, and review**

```powershell
python -m pytest tests/test_r4_partition_contracts.py tests/test_r4_partition_global_assignment.py tests/test_r4_mutations_and_partitions.py -q -p no:cacheprovider
python -m pytest tests/test_r4_partition_global_assignment.py -q -p no:cacheprovider --durations=10
```

Expected: focused suite passes; real 400-row construction remains within the configured membership, solver-state, component, input-byte, output-byte, and sparse-counter-operation bounds and has no torch/runtime import.

- [ ] **Step 6: Refresh final feasibility after allocator source changes**

Task 5 changes the solver/allocator that owns the checked-in basis and final
receipt. Generate the candidate basis to a temporary path, then use the strict
publisher. Its default mode bounded-strict-loads candidate/config, compares
`feasibility_basis_ref` and `minima_witness_ref`, returns exit 3 without writes
when either differs, and atomically publishes only an equal candidate. Exit 3
is a hard stop before mutation: update the tracker, push the candidate evidence
hash, and obtain a separately amended reviewed minima/config plan before this
corrective replay may resume. The present plan contains no implicit acceptance
path for changed feasibility authority:

```powershell
python scripts/analyze_r4_partition_feasibility.py --basis --output "$env:TEMP\R4_PARTITION_FEASIBILITY_BASIS_CANDIDATE.json"
python scripts/publish_r4_feasibility_basis.py --candidate "$env:TEMP\R4_PARTITION_FEASIBILITY_BASIS_CANDIDATE.json" --config configs/r4_partitions.json --current artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json
python scripts/analyze_r4_partition_feasibility.py --final --output artifacts/validation/R4_PARTITION_FEASIBILITY.json
python scripts/analyze_r4_partition_feasibility.py --basis --check artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json
python scripts/analyze_r4_partition_feasibility.py --final --check artifacts/validation/R4_PARTITION_FEASIBILITY.json
```

- [ ] **Step 7: Commit**

```powershell
git add -- hybrid_mvp/src/cemm_authoritative_hybrid/r4_partitions.py hybrid_mvp/src/cemm_authoritative_hybrid/r4_partition_verify.py hybrid_mvp/tests/test_r4_partition_global_assignment.py hybrid_mvp/tests/test_r4_mutations_and_partitions.py hybrid_mvp/configs/r4_partitions.json hybrid_mvp/artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json hybrid_mvp/artifacts/validation/R4_PARTITION_FEASIBILITY.json
git commit -m "feat(r4): assign globally sealed data classes"
```

### Task 6: Cut Build Receipt ABI 4 and prepare temporary generated fixtures

**Files:**
- Modify: `src/cemm_authoritative_hybrid/r4_pipeline.py`
- Modify: `src/cemm_authoritative_hybrid/r4_admission.py`
- Modify: `scripts/build_r4_artifacts.py`
- Modify: `schemas/r4_build_receipt.schema.json`
- Modify: `tests/test_r4_admission.py`
- Modify: `tests/test_r4_authentic_episodes.py`
- Modify: `scripts/validation_gate.py`
- Modify: `tests/test_r4_validation_gate.py`
- Modify later: `artifacts/r4/**`

- [ ] **Step 1: Write Build Receipt ABI 4 RED tests**

Require exact replacement fields:

```python
R4_BUILD_RECEIPT_ABI_VERSION = 4

partition_evidence_sha256: str
split_manifest_sha256: str
partition_sufficiency_sha256: str
split_payload_sha256s: tuple[str, str, str, str]
train_capability_sha256: str
train_authorization_sha256: str
```

Reject `partition_manifest_sha256s`, `training_allowlist_sha256`, ABI 3, missing/extra payload hashes, noncanonical split order, or a train capability/authorization whose ancestry differs from the global manifest and Build Receipt.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tests/test_r4_admission.py tests/test_r4_authentic_episodes.py -q -p no:cacheprovider
```

- [ ] **Step 3: Implement pipeline generation in memory**

The pipeline builds partition evidence, sufficiency receipt, four canonical payload byte strings, global manifest, train capability, and class-scoped train authorization projection from one authenticated episode snapshot. Payload rows are sorted by `episode_ref`, strict canonical JSONL, and each source episode occurs exactly once.

The authorization projection is produced by the integrity owner from the full
candidate graph but contains only training purpose, expected train capability
ref/SHA, `artifact_graph_ref`, generator source revision, and authority
generation. It contains no sibling split identity and cannot self-reference the
Build Receipt. Build Receipt ABI 4 binds the authorization SHA; the final R4
admission receipt binds the Build Receipt and exact authorization ref/SHA.

Define `R4Pipeline.write_candidate_tree(result: R4BuildResult, output_root: Path) -> tuple[Path, ...]`. It first resolves a new sibling staging directory, writes every exact expected relative path there with bounded same-directory temp files plus flush/fsync/replace, rereads and independently verifies the complete staged tree, then renames the completed staging directory to the requested *new* output root. It rejects an existing output root. On any failure it removes only the verified staging directory and leaves checked-in artifacts untouched. The returned tuple is the sorted exact path inventory. There is no multi-file in-place writer.

- [ ] **Step 4: Replace admission reconstruction**

`verify_r4_admission()` strictly loads all new artifacts with bounds, independently reconstructs the graph/assignment/sufficiency/payloads/capability/authorization, checks exact source revision and authority generation, and rebuilds the ABI 4 receipt. It rejects old `partitions/` or `training_allowlist.json` as current evidence.

Add artifact-only provenance RED tests at this point, but do not replace the
historical ABI 3 evidence paths yet. The current candidate path verifies that
admission HEAD has one parent, changes only `artifacts/r4/**`, and the Build
Receipt `source_revision` equals that parent. The historical ABI 3 receipt path
continues to reconstruct from its stored source base. Task 8 switches the
current evidence path set only after all consumers and policies are ready.

- [ ] **Step 5: Commit source and generate temporary candidate trees for TDD**

First commit the complete source/schema/test implementation, with no generated
`artifacts/r4` changes:

```powershell
git add -- hybrid_mvp/src hybrid_mvp/scripts/build_r4_artifacts.py hybrid_mvp/schemas/r4_build_receipt.schema.json hybrid_mvp/tests
git diff --cached --check
git commit -m "feat(r4): generate four-class partition evidence"
$generatorSource = (git rev-parse HEAD).Trim()
```

Then generate against that exact committed source into temporary roots for
focused tests. Do not copy or commit `artifacts/r4` yet, because Tasks 7-8 still
change governed source/config/tests/docs and would make this source revision
stale:

```powershell
$buildA = Join-Path $env:TEMP ("cemm-r4-partition-a-" + [guid]::NewGuid().ToString('N'))
$buildB = Join-Path $env:TEMP ("cemm-r4-partition-b-" + [guid]::NewGuid().ToString('N'))
python scripts/build_r4_artifacts.py --source-revision $generatorSource --environment src/cemm_authoritative_hybrid/r4_environment.py --output $buildA
python scripts/build_r4_artifacts.py --source-revision $generatorSource --environment src/cemm_authoritative_hybrid/r4_environment.py --output $buildB
```

Compare sorted relative path, length, and SHA-256 for every file. Expected: exact equality, four nonempty payloads, 400 total rows, and no old ABI 2 files.

- [ ] **Step 6: Verify temporary candidates without changing checked-in artifacts**

Compare both temporary trees byte-for-byte and run the new ABI/independent
verification against those explicit temporary roots. Tests that require new
artifacts accept an injected candidate root; current checked-in artifacts
remain historical invalidated evidence until Task 9.

- [ ] **Step 7: Run focused verification; do not commit generated data**

```powershell
python -m pytest tests/test_r4_admission.py tests/test_r4_authentic_episodes.py tests/test_r4_partition_global_assignment.py -q -p no:cacheprovider
python scripts/check_r3_r4_structure.py
git diff --check
```

Expected: source implementation is committed and temporary generation is
deterministic. `git status --short -- artifacts/r4` remains unchanged.

### Task 7: Migrate the active R5 train-only capability and hard-cut legacy partitions

**Files:**
- Create: `src/cemm_authoritative_hybrid/r4_partition_access.py`
- Modify: `src/cemm_authoritative_hybrid/training.py`
- Delete: `src/cemm_authoritative_hybrid/partitions.py`
- Delete: `scripts/partition_episodes.py`
- Modify: `scripts/train_proposer.py`
- Modify: `scripts/train_realizer.py`
- Create: `scripts/run_r4_release_training.py`
- Modify: `configs/proposal_release.json`
- Modify: `configs/realizer_release.json`
- Modify: `tests/test_r5_data_isolation.py`
- Modify: `tests/test_r4_training_partition_boundary.py`
- Audit/migrate/delete: `tests/test_partition_leakage.py`, `tests/test_hard_negatives.py`, `tests/test_gap_episode_coverage.py`
- Delete or quarantine after lineage audit: `scripts/calibrate_models.py`, `scripts/evaluate_cemm.py`
- Audit/retire: `_test_eval.py`, `_test_eval2.py`, `_test_eval3.py`, `_test_train.py`
- Modify for future-owner lineage only: `tests/test_release_thresholds.py`, `tests/test_gap_owner_evaluation.py`
- Delete after consumer audit: `data/partitions/**`

- [ ] **Step 1: Run the exact inventory/consumer lineage audit before deletion**

```powershell
foreach ($phase in 'G0','R1','R2','R3','R4','R5') {
    python scripts/check_test_inventory.py --phase $phase --source-only
    if ($LASTEXITCODE -ne 0) { throw "inventory failed for $phase" }
}
rg -n "cemm_authoritative_hybrid\.partitions|PartitionManifest|Partitioner|data[/\\]partitions|episodes_path|--episodes" src scripts tests configs _test_eval.py _test_eval2.py _test_eval3.py _test_train.py
```

For every matching test node, record frozen/literal classification, active phase, assertion ref, and current successors. `test_partition_leakage.py`, `test_hard_negatives.py`, and `test_gap_episode_coverage.py` contain retained R4 assertions: land exact current successor nodes before deleting or stripping their legacy owners. `test_release_thresholds.py` and `test_gap_owner_evaluation.py` remain future R7 evidence, but their R4/R5 structural assertions must prove the legacy evaluation entry points are unavailable rather than importing a compatibility stub. Do not delete a module that owns an active leaf or required literal predecessor until a current successor preserves its exact assertion and phase.

Use this reviewed successor map. Every successor remains activation phase R4,
preserves the exact listed `assertion_ref`, and declares the exact predecessor
in the live literal field `supersedes_node_id`. Allocator/mutation successors
use owner-role `mutation-partition`; the train non-disclosure successor uses
the existing R4 `artifact-integrity` owner. Separate R5 isolation assertions
remain under R5 `data-isolation`. Delete each old module only after all rows
reconstruct:

| Predecessor node/family | Exact assertion ref | Successor node / owner |
|---|---|---|
| `test_gap_episode_coverage.py::test_all_18_gap_kinds_are_covered` | `assertion:gap-episode-coverage-all-18-gap-kinds-are-covered` | `test_r4_mutations_and_partitions.py::test_r4_gap_episodes_cover_all_18_kinds` / `mutation-partition` |
| `test_gap_episode_coverage.py::test_every_gap_kind_has_positive_and_near_miss` | `assertion:gap-episode-coverage-every-gap-kind-has-positive-and-near-miss` | `test_r4_mutations_and_partitions.py::test_r4_gap_kinds_have_positive_and_near_miss` / `mutation-partition` |
| `test_hard_negatives.py::test_hard_negatives_exist` | `assertion:hard-negatives-hard-negatives-exist` | `test_r4_mutations_and_partitions.py::test_r4_hard_negatives_exist` / `mutation-partition` |
| `test_hard_negatives.py::test_hard_negatives_mutate_one_dimension` | `assertion:hard-negatives-hard-negatives-mutate-one-dimension` | `test_r4_mutations_and_partitions.py::test_r4_hard_negatives_mutate_one_dimension` / `mutation-partition` |
| `test_hard_negatives.py::test_hard_negatives_retain_parent_lineage` | `assertion:hard-negatives-hard-negatives-retain-parent-lineage` | `test_r4_mutations_and_partitions.py::test_r4_hard_negatives_retain_parent_lineage` / `mutation-partition` |
| `test_hard_negatives.py::test_hard_negatives_have_verifier_error_labels` | `assertion:hard-negatives-hard-negatives-have-verifier-error-labels` | `test_r4_mutations_and_partitions.py::test_r4_hard_negatives_have_verifier_error_labels` / `mutation-partition` |
| `test_hard_negatives.py::test_hard_negatives_have_valid_labels` | `assertion:hard-negatives-hard-negatives-have-valid-labels` | `test_r4_mutations_and_partitions.py::test_r4_hard_negatives_have_valid_labels` / `mutation-partition` |
| `test_hard_negatives.py::test_hard_negatives_have_gap_kind` | `assertion:hard-negatives-hard-negatives-have-gap-kind` | `test_r4_mutations_and_partitions.py::test_r4_hard_negatives_have_gap_kind` / `mutation-partition` |
| `test_hard_negatives.py::test_proposer_miss_and_authority_gap_cases_exist` | `assertion:hard-negatives-proposer-miss-and-authority-gap-cases-exist` | `test_r4_mutations_and_partitions.py::test_r4_proposer_miss_and_authority_gap_cases_exist` / `mutation-partition` |
| `test_hard_negatives.py::test_hard_negatives_have_unique_refs` | `assertion:hard-negatives-hard-negatives-have-unique-refs` | `test_r4_mutations_and_partitions.py::test_r4_hard_negatives_have_unique_refs` / `mutation-partition` |
| `test_hard_negatives.py::test_hard_negatives_have_valid_abi_version` | `assertion:hard-negatives-hard-negatives-have-valid-abi-version` | `test_r4_mutations_and_partitions.py::test_r4_hard_negatives_use_active_abi` / `mutation-partition` |
| `test_partition_leakage.py::test_no_lineage_component_crosses_partitions[<8 ids>]` | `assertion:partition-leakage-no-lineage-component-crosses-partitions` | `test_r4_partition_global_assignment.py::test_no_leakage_hyperedge_crosses_classes[<same 8 ids>]` / `mutation-partition` |
| `test_partition_leakage.py::test_sealed_test_hash_is_not_available_to_training` | `assertion:partition-leakage-sealed-test-hash-is-not-available-to-training` | `test_r4_training_partition_boundary.py::test_train_capability_discloses_no_sibling_identity` / `artifact-integrity` |
| `test_partition_leakage.py::test_partition_manifest_has_correct_counts` | `assertion:partition-leakage-partition-manifest-has-correct-counts` | `test_r4_partition_global_assignment.py::test_split_manifest_counts_match_assignment` / `mutation-partition` |
| `test_partition_leakage.py::test_partition_counts_match_files` | `assertion:partition-leakage-partition-counts-match-files` | `test_r4_partition_global_assignment.py::test_split_payload_counts_match_manifest` / `mutation-partition` |
| `test_partition_leakage.py::test_partition_manifest_hashes_match_files` | `assertion:partition-leakage-partition-manifest-hashes-match-files` | `test_r4_partition_global_assignment.py::test_split_payload_hashes_match_manifest` / `mutation-partition` |
| `test_partition_leakage.py::test_every_episode_apars_in_exactly_one_partition` | `assertion:partition-leakage-every-episode-apars-in-exactly-one-partition` | `test_r4_partition_global_assignment.py::test_every_episode_appears_in_exactly_one_class` / `mutation-partition` |
| `test_partition_leakage.py::test_partition_ratios_are_approximately_balanced` | `assertion:partition-leakage-partition-ratios-are-approximately-balanced` | `test_r4_partition_global_assignment.py::test_class_sizes_satisfy_reviewed_integer_objective` / `mutation-partition` |

The eight parameter IDs stay exactly `adversarial_mutation`,
`authority_target`, `dialogue`, `entity`, `graph_topology`, `lexical_value`,
`normalized_text`, and `template`. Preserve the historical misspelled
`assertion:partition-leakage-every-episode-apars-in-exactly-one-partition`;
assertion identity is not spelling cleanup.

- [ ] **Step 2: Write train-capability RED tests**

Require `load_r4_train_episodes(authorization_path, capability_path, root, *, expected_authorization_ref, expected_authorization_sha256)` to:

- accept only the exact checked-in train capability path and purpose/split;
- authenticate authorization bytes against the separately supplied reviewed
  expected ref/SHA before reading capability or payload;
- require exact authorization-to-capability ref/SHA, artifact-graph ref, generator source revision, and authority generation;
- require `expected_authorization_ref` and `expected_authorization_sha256` to come from the admitted R4 run projection loaded by release configuration, not from the capability or authorization file;
- authenticate bounded strict capability bytes and one bounded payload snapshot;
- hash and parse the same snapshot without reopen;
- return episodes plus the authenticated payload digest/ref;
- reject selection/calibration/frozen capabilities before payload access;
- reject a capability containing sibling fields or pointing at a sibling payload;
- reject copied, renamed, symlinked, reparse, path-escaped, mutated, oversized, malformed, duplicate-key, nonfinite, or invalid-UTF-8 inputs;
- reject all `data/partitions` paths even if their hashes match; and
- seed/build/train only after successful capability authentication.

- [ ] **Step 3: Run RED**

```powershell
python -m pytest tests/test_r5_data_isolation.py tests/test_r4_training_partition_boundary.py -q -p no:cacheprovider
```

- [ ] **Step 4: Implement the minimal class-scoped loader**

Move `PartitionAccessError` to `r4_partition_access.py`. Return an immutable authenticated snapshot object:

```python
@dataclass(frozen=True)
class AuthenticatedClassSnapshot:
    capability_ref: str
    payload_ref: str
    payload_sha256: str
    payload_bytes: bytes
    episode_count: int
```

Training parses this exact byte object, records its capability/payload/artifact-graph identities in metadata, and never opens the path again. Both proposal and realizer `fit()` authenticate once, then seed once. `train_proposal_release()` and `train_realizer_release()` accept the authenticated snapshot/config trust pin and no longer substitute `_TRAIN_PARTITION`.

The release CLIs load the strict release config and call the same capability API. In release mode, `--episodes` is a hard error; no missing config key falls back to bootstrap JSONL. Development/bootstrap mode remains a separately named non-release command path and cannot emit a release artifact.

`scripts/run_r4_release_training.py` is the repository-owned parent controller.
It verifies the effective R4-green row and SHA-authenticated admission receipt,
extracts only expected authorization ref/SHA, creates a private isolated
snapshot containing exactly authorization, train capability, and train payload,
and invokes `train_proposer.py` or `train_realizer.py` as one bounded child with:

```text
--release-isolated-root <snapshot>
--expected-authorization-ref <ref>
--expected-authorization-sha256 <sha>
```

The child CLI rejects ordinary repository roots in release mode and has no
ledger/run/global-manifest/Build-Receipt path. Instrumented tests poison every
such open in the child and require zero calls. The parent never imports torch
or trainer code; the child never reads governance. Parent output binds the
admission run ref and child artifact/report refs without exposing sibling
evidence identities to the child.

The training process receives only the authorization projection, train
capability, and train payload snapshot. It cannot read the global split
manifest, Build Receipt, or sibling artifacts. Release config pins the expected
authorization ref/SHA separately from both file paths; changing authorization,
capability and payload consistently still fails that external trust check.

- [ ] **Step 5: Migrate configs and current tests**

Replace `episodes_path` with exact class-scoped values:

```json
"train_capability_path": "artifacts/r4/capabilities/train.json",
"train_authorization_path": "artifacts/r4/capabilities/train_authorization.json",
"train_authorization_trust": "r4_admission_receipt"
```

The release launcher validates the effective R4-green ledger row and its exact run receipt, extracts the admission-authenticated train authorization ref/SHA, and passes only those two expected values plus the isolated train authorization/capability/payload snapshot to the training process. Before R4 is green, this trust resolution fails closed. Config does not trust values declared by `train_authorization.json` and no source/config commit needs a future generated hash. No config contains selection/calibration/frozen-test path or hash. Update current R5 tests with exact successors where node IDs must change; preserve assertion refs and succession metadata.

- [ ] **Step 6: Delete the legacy authority after the audit passes**

Remove the legacy module/generator/data and stale future entry points only after all current consumers move. Add structural tests that fail on:

```text
src/cemm_authoritative_hybrid/partitions.py
scripts/partition_episodes.py
data/partitions/manifest.json
data/partitions/train.jsonl
data/partitions/validation.jsonl
data/partitions/test.jsonl
"data/partitions" in active src/config/scripts
```

Future calibration/evaluation scripts may be deleted now and reintroduced under R5/R7; do not add a stub or compatibility error wrapper.

Retire or migrate the four tracked Hybrid-root diagnostic scripts in the same commit. A repository-wide `git grep` over tracked files, not only `src/scripts/tests/configs`, must show no active legacy partition consumer. Evaluation diagnostics cannot be pointed at `frozen_test` in this increment because the R7 evaluation capability is not minted.

- [ ] **Step 7: Run focused and inventory GREEN**

```powershell
python -m pytest tests/test_r5_data_isolation.py tests/test_r4_training_partition_boundary.py tests/test_r4_partition_contracts.py -q -p no:cacheprovider
python scripts/audit_legacy_test_hard_cut.py
foreach ($phase in 'G0','R1','R2','R3','R4','R5') {
    python scripts/check_test_inventory.py --phase $phase --source-only
    if ($LASTEXITCODE -ne 0) { throw "inventory failed for $phase" }
}
```

Expected: no legacy partition authority; R5 disposition remains exactly 17/25/1.

- [ ] **Step 8: Commit**

```powershell
git add -A -- hybrid_mvp/src hybrid_mvp/scripts hybrid_mvp/configs hybrid_mvp/tests hybrid_mvp/data/partitions hybrid_mvp/_test_eval.py hybrid_mvp/_test_eval2.py hybrid_mvp/_test_eval3.py hybrid_mvp/_test_train.py
git diff --cached --check
git commit -m "refactor(r5): consume authenticated R4 train capability"
```

### Task 8: Reconcile validation, documentation, selectors, and deterministic receipts

**Files:**
- Modify: `configs/validation_gates.json`
- Modify: `scripts/validation_gate.py`
- Modify: `scripts/update_replay_status.py`
- Modify: `scripts/check_r3_r4_structure.py`
- Modify: `scripts/audit_legacy_test_hard_cut.py`
- Create: `scripts/publish_r4_candidate.py`
- Create: `scripts/run_r4_corrective_validation.py`
- Create: `tests/test_r4_corrective_validation.py`
- Create: `tests/test_publish_r4_candidate.py`
- Modify: `tests/test_r4_validation_gate.py`
- Modify: `tests/test_replay_governance.py`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `docs/ABI_REGISTRY.md`
- Modify: prior R4 documents only with narrow supersession notices
- Modify: `artifacts/validation/TEST_INVENTORY_RECEIPT.json`
- Modify: `artifacts/validation/R5_TEST_DISPOSITIONS.json`
- Modify: progress tracker

- [ ] **Step 1: Add exact gate-contract RED tests**

Require current authenticated inventory equality for every configured R4/R5 owner and phase selector. Assert:

- `mutation-partition` owns the partition contracts/allocator tests;
- `artifact-integrity` owns ABI 4 reconstruction;
- existing `data-isolation` owns the train-capability tests;
- no sixth R5 foundation owner is created;
- owner/phase node sets remain disjoint;
- every tier resolves to governance, source compile, and one pytest step where applicable;
- R4 artifact generation is not repeated per owner tier; and
- active gate inputs contain no legacy partition paths.

Also write source-aware evidence-policy regressions before changing the policy:

```python
def test_historical_r4_abi3_receipt_reconstructs_from_its_source_base() -> None:
    receipt = load_existing_admitted_r4_run()
    assert receipt.build_receipt_abi_version == 3
    assert reconstruct_evidence_paths(receipt) == HISTORICAL_R4_ABI3_PATHS


def test_current_r4_candidate_requires_only_abi4_evidence() -> None:
    candidate = current_r4_candidate_policy()
    assert candidate == CURRENT_R4_ABI4_PATHS
    assert not candidate & HISTORICAL_R4_PARTITION_PATHS
```

`validation_gate.py` owns two immutable policies: historical ABI 3 by exact
stored receipt/source-base identity, and current ABI 4 by candidate Build
Receipt version. `update_replay_status.py` uses the bounded union only when
validating dirty-path containment/history; it selects ABI 3 or ABI 4 exactly
for reconstruction. Current admission never accepts the union as its evidence
set. Tests mutate an ABI/version/source-base tuple and require fail-closed
rejection.

- [ ] **Step 2: Run RED, then update exact selectors/inputs**

```powershell
python -m pytest tests/test_validation_gate.py tests/test_r4_validation_gate.py tests/test_replay_governance.py tests/test_g0_integration.py tests/test_r5_foundation.py -q -p no:cacheprovider -k "selector or partition or evidence_policy or process"
```

- [ ] **Step 3: Update active docs without copying mutable status**

Document the corrected R4 data boundary and R5 train-only capability. Retire old ABI rows. Add narrow publication-scoped supersession notices to documents whose active partition language conflicts. Keep effective status routed to the ledger and root adoption explicitly unperformed.

- [ ] **Step 4: Refresh metadata and canonical receipts**

Run these exact metadata owners from `hybrid_mvp/`:

```powershell
python scripts/refresh_r3_r4_test_metadata.py
python scripts/verify_r3_r4_test_metadata.py
python scripts/refresh_r5_test_metadata.py
```

Rebuild `TEST_INVENTORY_RECEIPT.json` with the existing canonical owner:

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
    root, inventory_path, phase="G0", enforce_reviewed_counts=True,
    expected_sha256=inventory_sha,
)
graph, _ = gate._load_gate_graph_with_source(root / "configs" / "validation_gates.json")
selector = gate.validate_inventory_contract(graph, inventory, phase="G0")
authority_raw = (root / "docs" / "DOCUMENT_AUTHORITY.json").read_bytes()
receipt = gate._expected_g0_inventory_receipt(
    authority_sha256=gate.hashlib.sha256(authority_raw).hexdigest(),
    inventory_sha256=inventory_sha, inventory=inventory, selector=selector,
)
(root / "artifacts/validation/TEST_INVENTORY_RECEIPT.json").write_bytes(
    gate.canonical_json_bytes(receipt)
)
'@ | python -
python scripts/generate_r5_test_dispositions.py --output artifacts/validation/R5_TEST_DISPOSITIONS.json
python scripts/generate_r5_test_dispositions.py --check artifacts/validation/R5_TEST_DISPOSITIONS.json
python scripts/refresh_r3_r4_test_metadata.py
python scripts/verify_r3_r4_test_metadata.py
python scripts/refresh_r5_test_metadata.py
```

Expected: the second refreshers report zero changed hashes, the disposition
generator check passes, and repeating the inline receipt owner produces
byte-identical `TEST_INVENTORY_RECEIPT.json`.

- [ ] **Step 5: Run focused direct owner tests only**

```powershell
python -m pytest tests/test_r4_partition_contracts.py tests/test_r4_partition_global_assignment.py tests/test_r4_admission.py tests/test_r4_validation_gate.py tests/test_r4_training_partition_boundary.py tests/test_r5_data_isolation.py tests/test_validation_gate.py tests/test_r4_corrective_validation.py tests/test_publish_r4_candidate.py -q -p no:cacheprovider
```

Expected: focused changed-owner behavior passes while ledger-effective R4 and
R5 remain red. Do not invoke `validate_mvp` owner or phase tiers here; Task 9 is
the sole phase sweep and Task 10 is the sole full active run.

In the same TDD task, implement:

```text
publish_r4_candidate.py --candidate <new-root> --current artifacts/r4 --dry-run
publish_r4_candidate.py --candidate <new-root> --current artifacts/r4 --commit
run_r4_corrective_validation.py phase-sweep --max-seconds 900
run_r4_corrective_validation.py admission --phase R4 --max-seconds 900
```

Publisher tests use real temporary Git trees on Windows and inject failure at
candidate validation, current-to-backup rename, candidate-to-current rename,
post-swap verification, backup cleanup, and rollback cleanup. They require
exact original restoration, no unresolved/reparse path, and no leftover temp
on success. The phase controller invokes phases G0-R5 once each, enforces one
aggregate 900-second controller budget (leaving Task 10 up to 900 seconds),
kills descendants on timeout, and emits a bounded canonical summary. It does
not add a validation owner or pytest process.

- [ ] **Step 6: Commit**

```powershell
git add -- hybrid_mvp/configs hybrid_mvp/scripts hybrid_mvp/docs hybrid_mvp/tests hybrid_mvp/artifacts/validation
git commit -m "docs(r4): publish corrected partition boundary"
```

### Task 9: Finalize source, then create the final artifact-only commit

**Files:**
- Modify: `artifacts/r4/**`
- No source/docs/config/test change is permitted after the artifact commit

- [ ] **Step 1: Commit every final non-artifact reconciliation first**

Run focused gates and inspect status. If any source, script, schema, config,
test, doc, validation receipt, or tracker change remains, commit it now. Then
require a clean worktree and record:

```powershell
$generatorSource = (git rev-parse HEAD).Trim()
```

This commit is the exact single parent required by
`_r4_generator_source_revision`. No non-`artifacts/r4/**` commit may occur after
the artifact commit and before admission.

Before recording `$generatorSource`, run the exact metadata/receipt idempotence
commands from Task 8 and require a clean worktree. This is the last opportunity
to update docs, configs, tests, selectors, progress tracker, living validation
receipts, historical/current evidence policies, or consumer lineage.

Also require both feasibility artifacts to check against the final committed
solver/config. If either check fails or regeneration changes bytes, commit the
repaired source/config/basis/final set before recording `$generatorSource` and
repeat all idempotence checks. Use the same strict publisher; exit 3 follows the
renewed review/config update command from Task 5 rather than overwriting
evidence alone:

```powershell
python scripts/analyze_r4_partition_feasibility.py --basis --output "$env:TEMP\R4_PARTITION_FEASIBILITY_BASIS_FINAL_CANDIDATE.json"
python scripts/publish_r4_feasibility_basis.py --candidate "$env:TEMP\R4_PARTITION_FEASIBILITY_BASIS_FINAL_CANDIDATE.json" --config configs/r4_partitions.json --current artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json
python scripts/analyze_r4_partition_feasibility.py --basis --check artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json
python scripts/analyze_r4_partition_feasibility.py --final --check artifacts/validation/R4_PARTITION_FEASIBILITY.json
```

- [ ] **Step 2: Prove generated artifact idempotence**

Generate two fresh temporary roots at `$generatorSource`, passing
`--environment src/cemm_authoritative_hybrid/r4_environment.py`, and compare
every relative path, length, and SHA-256. Expected: byte-identical.

- [ ] **Step 3: Transactionally publish the verified tree and make one artifact-only commit**

Use the exact repository-owned publisher from Task 8:

```powershell
python scripts/publish_r4_candidate.py --candidate $buildA --current artifacts/r4 --dry-run
python scripts/publish_r4_candidate.py --candidate $buildA --current artifacts/r4 --commit
```

It consumes the same exact path inventory emitted by `write_candidate_tree`.
Under `artifacts/`, it constructs a sibling `r4.candidate.<nonce>` from verified
bytes, verifies its complete relative-path/length/SHA map again, moves current
`r4` to a verified sibling backup, replaces it with the complete candidate
directory, and immediately verifies the checked-in destination. On failure it
restores the backup before returning an error; cleanup continues even if one
cleanup step fails. It rejects symlink/junction/reparse components and any
unexpected file in candidate/current/backup. It deletes only the verified
backup after success.

The candidate path inventory omits only the retired
`partitions/*.json` and `training_allowlist.json`; it must include every other
preexisting admitted R4 artifact plus the new evidence/manifest/sufficiency,
four payloads, capability, authorization, and ABI 4 Build Receipt.

```powershell
git add -A -- hybrid_mvp/artifacts/r4
git diff --cached --name-only | ForEach-Object {
    if ($_ -notlike 'hybrid_mvp/artifacts/r4/*') { throw "non-artifact path in R4 artifact commit" }
}
git commit -m "data(r4): regenerate globally sealed partitions"
$artifactCommit = (git rev-parse HEAD).Trim()
```

Verify `$artifactCommit` has exactly one parent `$generatorSource` and changes
only `hybrid_mvp/artifacts/r4/**` using the existing validation-gate function
and tests.

- [ ] **Step 4: Run the single pre-admission source/phase sweep**

```powershell
python scripts/run_r4_corrective_validation.py phase-sweep --max-seconds 900
```

Each phase gate already authenticates the phase inventory; do not run a second
standalone inventory process inside this loop. This is the only complete G0-R5
phase sweep in the corrective replay.

- [ ] **Step 5: Run structural, hard-cut, and governed regression gates**

```powershell
python scripts/check_r3_r4_structure.py
python scripts/audit_legacy_test_hard_cut.py
python scripts/update_replay_status.py --verify-chain
git diff --check
git status --short --branch
```

Expected: structural and hard-cut checks pass; effective R4/R5 remain red before admission; worktree clean. Do not run `run_active_test_suite.py` here: the ordinary R4 admission in Task 10 owns the required full active pytest process against this exact artifact-only HEAD.

- [ ] **Step 6: Review and publish the pre-admission checkpoint**

Request spec then quality/performance/security review. Push the clean reviewed
branch so the exact admission candidate is remotely recoverable. Do not append
green yet. A review finding that requires source/docs/config/test changes
invalidates the artifact commit: fix the parent source, regenerate twice, and
make a new final artifact-only commit before admission.

### Task 10: Admit R4 through the ordinary repository-owned gate

**Files:**
- Create: `artifacts/validation/runs/<run-ref>.json`
- Modify: `governance/replay_status.jsonl`
- Modify: progress tracker

- [ ] **Step 1: Run clean R4 admission**

```powershell
python scripts/run_r4_corrective_validation.py admission --phase R4 --max-seconds 900 --output "$env:TEMP\r4-partition-admission.json"
```

Expected: the outer controller terminates the complete descendant tree at the
900-second aggregate deadline, caps combined output, removes only a
controller-created partial run receipt on infrastructure failure, and returns a
canonical result. On success it reports passed disposition, fresh exact
`run_ref`, `gate_result_ref`, and one receipt path. The admission tier runs the
single required full governed active pytest process. The integrity report binds
Build Receipt ABI 4, partition evidence, split manifest, four payloads,
sufficiency, train capability, and train authorization. It contains no review
or model fields.

- [ ] **Step 2: Verify admission did not mutate the ledger**

Hash the ledger before/after admission. Expected: unchanged. Verify the run receipt source ref equals current committed HEAD and every governed input is clean.

- [ ] **Step 3: Dry-run and append exact R4 green**

```powershell
$admission = Get-Content -Raw "$env:TEMP\r4-partition-admission.json" | ConvertFrom-Json
python scripts/update_replay_status.py --phase R4 --status green --run-ref $admission.run_ref --dry-run | Tee-Object "$env:TEMP\r4-partition-green.json"
$candidate = Get-Content -Raw "$env:TEMP\r4-partition-green.json" | ConvertFrom-Json
python scripts/update_replay_status.py --phase R4 --status green --run-ref $admission.run_ref --expect-record-ref $candidate.record_ref --append
python scripts/update_replay_status.py --verify-chain
```

Expected ledger-derived state after re-admission: G0-R4 green and R5-R8 red.

- [ ] **Step 4: Commit exact admission evidence**

Update tracker P8/P9 with evidence locations and the commit after creation, without making the tracker an admission source.

```powershell
git add -- hybrid_mvp/artifacts/validation/runs hybrid_mvp/governance/replay_status.jsonl hybrid_mvp/docs/superpowers/progress
git diff --cached --check
git commit -m "admit(r4): restore non-vacuous data boundary"
```

This post-admission commit is permitted after the gate has authenticated the
final artifact-only HEAD. Its only paths are the exact run receipt, append-only
ledger, and tracker. If admission itself requires a source change, discard the
run and return to Task 9.

### Task 11: Complete closeout, remote publication, and R5 entry handoff

**Files:**
- Modify: progress tracker only if verification evidence advances

- [ ] **Step 1: Run post-admission governance and artifact checks**

```powershell
python scripts/analyze_r4_partition_feasibility.py --final --check artifacts/validation/R4_PARTITION_FEASIBILITY.json
python scripts/generate_r5_test_dispositions.py --check artifacts/validation/R5_TEST_DISPOSITIONS.json
python scripts/check_r3_r4_structure.py
python scripts/audit_legacy_test_hard_cut.py
python scripts/update_replay_status.py --verify-chain
git diff --check
git status --short --branch
```

Do not repeat the six phase processes or the full active suite after the
ledger-only admission commit. The admission receipt already authenticates the
artifact-only HEAD and its full active result; the post-admission commit may
change only the run receipt, append-only ledger, and tracker. If that path
allowlist is violated, return to Task 9 and rerun admission instead of adding
another broad gate.

The aggregate broad-test budget for the whole replay is:

```text
pre-admission phase sweep   6 pytest processes maximum
R4 admission               1 full active pytest process
post-admission              0 pytest processes (governance/artifact CLIs only)
total broad pytest          <= 7 processes
enforced phase budget       <= 900 seconds aggregate
admission process budget    <= 900 seconds
target wall budget          <= 1,800 seconds aggregate
```

Focused TDD pytest processes are scoped to changed owners and are not repeated
as complete phase/full-suite sweeps.

- [ ] **Step 2: Independently review the complete branch delta**

Review Critical/Important issues only: all seven leakage axes, four-class feasibility, independent verification, class capability non-disclosure, legacy authority absence, Build Receipt ABI 4, ledger sequence, gate/process cost, R5 still red, and root non-adoption.

- [ ] **Step 3: Finalize the tracker and commit**

Record exact final commit ancestry, artifact refs, class counts, feasibility/sufficiency refs, admission evidence path, governed active result ref, review result, and remote publication. Keep the live phase matrix absent; link the ledger verifier output instead.

```powershell
git add -- hybrid_mvp/docs/superpowers/progress/2026-08-14-r4-partition-corrective-replay-progress.md
git commit -m "docs(r4): close partition corrective replay"
```

- [ ] **Step 4: Push the reviewed branch**

```powershell
git push origin codex/r4-partition-corrective-replay
git status --short --branch
```

Expected: local HEAD equals `origin/codex/r4-partition-corrective-replay`; clean worktree. Do not merge to main or begin R5 neural training without separate user authorization.

- [ ] **Step 5: Prepare the R5 Neural Activation handoff**

The next design consumes only the authenticated train/selection/calibration/frozen-test capability ABIs. It must replace Program ABI 1 neural code, calibrate actual predictions, prove weight use/ablation, reproduce selected bytes, and convert the disposition partition from 17/25/1 to 42/0/1 before R5 admission.

---

## Stop conditions

Stop, update the tracker truthfully, and push the evidence checkpoint when:

- the seven-axis exact leakage graph cannot support four nonempty components;
- any reviewed minimum lacks positive source and feasible-component support;
- a proposed fix would reclassify an exact protected identity as a coarse label;
- any current active/frozen test lineage cannot be migrated without immutable-inventory authority;
- any R5 consumer needs sibling class identity or frozen-test bytes before its owner exists;
- deterministic generation differs between two clean output roots;
- Build Receipt ABI 4 cannot reconstruct from committed inputs;
- a G0-R3 phase regresses;
- R4 green would require weakening admission or bypassing the red/green ledger sequence;
- a compatibility loader or second partition authority is proposed; or
- root semantic/runtime adoption would be required.

No stop condition may be converted into success by changing a label, ratio, minimum, or test selector.
