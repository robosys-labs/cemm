# Hybrid MVP G0-R1 Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `subagent-driven-development` task-by-task. Every implementation task uses `test-driven-development`, then contract review, code-quality/performance review, and controller verification.

**Goal:** Admit G0 and R1: truthful executable governance, inherited-claim quarantine, one dependency-aware validator, and a hard cut from duplicate runtime ABIs/paths to canonical content-addressed R1 boundaries.

**Architecture:** Governance is append-only evidence outside semantic authority. Validation is one external DAG runner with three coalesced tiers. R1 owns immutable identities in their earliest modules, one candidate-batch/verifier boundary, one final `CycleResult`, and `HybridRuntime.process()` as the only public path. R2/R3 functionality remains explicitly unavailable rather than simulated.

**Tech Stack:** Python 3.11+, pytest, PyTorch, JSON/JSONL, SHA-256 refs, SQLite activation checks.

**Worktree:** `C:\dev\cemm\.worktrees\hybrid-mvp-g0-r1` on `codex/hybrid-mvp-g0-r1`.

**Design:** `hybrid_mvp/docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md`.

**Command roots:** Run Python/pytest/script commands from `hybrid_mvp/`. Run `git add` and `git commit` commands from the worktree root so their `hybrid_mvp/` paths resolve exactly.

---

## Execution rules

- Never run/copy the donor installer or overlay.
- Do not modify root-runtime code/authority or relabel/move/delete inherited artifacts.
- Do not weaken release expectations, convert programming errors into gaps, or retain adapters, signature inspection, fixture release owners, or alternate composition roots.
- Red/green loops run only the focused owner tier. Run the coalesced phase tier after review and one fresh admission tier per phase candidate.
- G0/R1 never run corpus generation, training, or reproduction.
- Validation/performance code is not imported by the normal runtime path.
- Preserve unrelated user changes.

## Baseline evidence at `58345240e67bf003e6ac7d5c68752e2e5eee4a7d`

- Python 3.13.4; current pytest 9.0.2 versus inherited 8.4.0 lock expectation.
- 743 collected tests in 59 files.
- `tests/test_release_thresholds.py`: exact accuracy `0.75641 < 0.9` and report status `failed`.
- Runtime diverges after ORIENT: proposal owner returns `candidates` while runtime reads `program/output_refs/rejection_codes`.
- Governed authority hashes differ between Git-archive LF and Windows working-tree bytes.

## Task 1: Establish approved document authority

**Files:**

- Modify: `hybrid_mvp/docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md`
- Modify: `hybrid_mvp/AGENTS.md`
- Modify: `hybrid_mvp/README.md`
- Modify: `hybrid_mvp/INTEGRATION.md`
- Modify: `hybrid_mvp/docs/IMPLEMENTATION_PLAN.md`
- Modify: `hybrid_mvp/docs/ABI_REGISTRY.md`
- Create: `hybrid_mvp/docs/DOCUMENT_AUTHORITY.json`
- Create: `hybrid_mvp/docs/REPLAY_GOVERNANCE.md`
- Test: `hybrid_mvp/tests/test_replay_governance.py`

### Step 1: Add the failing authority tests

```python
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _authority() -> dict[str, object]:
    return json.loads((ROOT / "docs/DOCUMENT_AUTHORITY.json").read_text(encoding="utf-8"))


def test_document_authority_is_scoped_and_supersedes_old_claims() -> None:
    authority = _authority()
    assert authority["scope"] == "hybrid_mvp/"
    assert authority["root_runtime_authority"] == "../AGENTS.md"
    assert authority["governing_documents"][:3] == [
        "AGENTS.md",
        "docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md",
        "docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md",
    ]
    superseded = set(authority["superseded_execution_claims"])
    assert "docs/superpowers/plans/2026-07-30-corrective-replay-plan.md" in superseded
    assert authority["generated_artifacts_are_authority"] is False


def test_governing_pointers_make_no_old_admission_claim() -> None:
    for relative in ("AGENTS.md", "README.md", "INTEGRATION.md",
                     "docs/IMPLEMENTATION_PLAN.md", "docs/ABI_REGISTRY.md"):
        text = (ROOT / relative).read_text(encoding="utf-8")
        assert "M1-M3 are complete" not in text
        assert "M4 Task 4 is complete" not in text
```

Run:

```powershell
cd C:\dev\cemm\.worktrees\hybrid-mvp-g0-r1\hybrid_mvp
python -m pytest tests\test_replay_governance.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-g0-docs
```

Expected RED: missing authority map and obsolete pointers.

### Step 2: Implement one authority owner

Create `DOCUMENT_AUTHORITY.json`:

```json
{
  "schema": "cemm-hybrid-document-authority-v1",
  "scope": "hybrid_mvp/",
  "root_runtime_authority": "../AGENTS.md",
  "governing_documents": [
    "AGENTS.md",
    "docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md",
    "docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md",
    "docs/superpowers/plans/2026-07-31-hybrid-mvp-g0-r1-implementation-plan.md",
    "docs/ARCHITECTURE.md",
    "docs/ABI_REGISTRY.md"
  ],
  "superseded_execution_claims": [
    "docs/superpowers/specs/2026-07-29-authoritative-mvp-completion-design.md",
    "docs/superpowers/plans/2026-07-29-authoritative-mvp-master-roadmap.md",
    "docs/superpowers/plans/2026-07-29-m1-six-phase-kernel.md",
    "docs/superpowers/plans/2026-07-29-m2-hybrid-proposal-verifier.md",
    "docs/superpowers/plans/2026-07-29-m3-cognition-learning-realization.md",
    "docs/superpowers/plans/2026-07-29-m4-training-failure-competitive-evaluation.md",
    "docs/superpowers/plans/2026-07-29-m5-surfaces-reliable-cutover.md",
    "docs/superpowers/plans/2026-07-30-corrective-replay-plan.md"
  ],
  "historical_evidence": [
    "docs/EVALUATION_REPORT.md", "docs/NEURAL_MODEL.md", "docs/COMPARISON.md",
    "docs/RUNTIME_TRACES.md", "docs/WORKTREE_INTEGRATION.md", "artifacts/"
  ],
  "generated_artifacts_are_authority": false,
  "root_adoption_requires_separate_review": true
}
```

Set design status to `approved for implementation`. Add short precedence/scope
pointers to the other governing docs without duplicating a status table.
`REPLAY_GOVERNANCE.md` explains the map and points to Task 2's status ledger.

### Step 3: Verify, review, commit

```powershell
python -m pytest tests\test_replay_governance.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-g0-docs
rg -n "M1.M3 are complete|M4 Task 4 is complete|proposed for user review" AGENTS.md README.md INTEGRATION.md docs\IMPLEMENTATION_PLAN.md docs\ABI_REGISTRY.md docs\superpowers\specs\2026-07-31-hybrid-mvp-corrective-replay-admission-design.md
git add hybrid_mvp/AGENTS.md hybrid_mvp/README.md hybrid_mvp/INTEGRATION.md hybrid_mvp/docs hybrid_mvp/tests/test_replay_governance.py
git commit -m "docs: establish hybrid corrective replay authority"
```

Request contract review and document-consistency review before commit.

## Task 2: Add append-only status and invalidation ledgers

**Files:**

- Create: `hybrid_mvp/src/cemm_authoritative_hybrid/governance.py`
- Create: `hybrid_mvp/governance/replay_status.jsonl`
- Create: `hybrid_mvp/governance/receipt_invalidations.jsonl`
- Create: `hybrid_mvp/governance/ledger_anchors.json`
- Create: `hybrid_mvp/scripts/update_replay_status.py`
- Modify: `hybrid_mvp/docs/DOCUMENT_AUTHORITY.json`
- Modify: `hybrid_mvp/tests/test_replay_governance.py`

### Step 1: Add failing chain/status tests

```python
from cemm_authoritative_hybrid.governance import (
    effective_replay_status, read_hash_chain, verify_file_invalidation,
)


def test_initial_replay_status_is_truthful() -> None:
    records = read_hash_chain(ROOT / "governance/replay_status.jsonl")
    assert effective_replay_status(records) == {
        "G0": "pending", "R1": "red", "R2": "red", "R3": "red",
        "R4": "red", "R5": "red", "R6": "red", "R7": "red", "R8": "red",
    }


def test_invalidations_bind_unchanged_historical_files() -> None:
    records = read_hash_chain(ROOT / "governance/receipt_invalidations.jsonl")
    expected = {
        "artifacts/validation/MILESTONE_RECEIPT.json":
            "f6df34c05b9cbbdd5b5864ad5fb11bfc7c530105753117e05e80a2da642b6aa7",
        "artifacts/validation/M2_PROPOSAL_RECEIPT.json":
            "c01945cfb2d482f9a43cbf4837284d65a6659914718b2d3c4e5629db4160f5ae",
        "artifacts/validation/M3_MILESTONE_RECEIPT.json":
            "6ab45fa606f7ce9ff99e7d779aacc84a7734abde858e2cff1a96225f91005c5e",
        "artifacts/validation/REPRODUCIBILITY.json":
            "330e214f5fa2cf301dd5d0831645eed0e7c61e4e9eadb1917a16c760b84f9768",
        "artifacts/training_receipt.json":
            "7d03f5151f1750b077f44c975095e9db99510d9b4220e1ae00e010e074066517",
        "artifacts/evaluation/CEMM_EVALUATION.json":
            "4caf7f65fd9d30ddeedf455e81b10194132808d75a274dea49229878ca09dc61",
    }
    assert {r["subject"]: r["subject_sha256"] for r in records} == expected
    for record in records:
        verify_file_invalidation(ROOT, record)
```

### Step 2: Implement strict chain validation

```python
def expected_record_ref(record: Mapping[str, object]) -> str:
    material = dict(record)
    material.pop("record_ref", None)
    return stable_ref("governance_record", material)


def read_hash_chain(
    path: Path,
    anchor: LedgerAnchor,
    *,
    prior_committed_bytes: bytes | None,
) -> tuple[dict[str, object], ...]:
    raw = path.read_bytes()
    if prior_committed_bytes is not None and not raw.startswith(prior_committed_bytes):
        raise GovernanceError("ledger is not an append-only extension")
    records = parse_and_validate_records(raw)
    if len(records) < anchor.initial_count:
        raise GovernanceError("ledger truncated below governed anchor")
    if records[0]["record_ref"] != anchor.genesis_ref:
        raise GovernanceError("governance genesis mismatch")
    if records[anchor.initial_count - 1]["record_ref"] != anchor.initial_head_ref:
        raise GovernanceError("governed initial prefix changed")
    return records
```

`parse_and_validate_records` performs the exact sequence, predecessor, schema,
type and content-ref checks shown by Task 2's RED tests. `ledger_anchors.json`
pins each ledger's genesis, initial head and initial count; DOCUMENT_AUTHORITY
pins that anchor file. For every later append, load the ledger bytes from the
record's `source_base` Git object and require the current bytes to have that
exact prefix. A clean bundle without Git must carry the prior-head receipt.

Populate `G0=pending` and `R1-R8=red` plus the six exact invalidations. Preserve
historical files byte-for-byte. Add tests for changed fields, broken predecessor,
missing/extra fields, truncation and a fully rehashed rewrite that does not
preserve the prior committed prefix.

### Step 3: Verify, review, commit

```powershell
python -m pytest tests\test_replay_governance.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-g0-ledgers
git add hybrid_mvp/src/cemm_authoritative_hybrid/governance.py hybrid_mvp/governance hybrid_mvp/scripts/update_replay_status.py hybrid_mvp/docs/DOCUMENT_AUTHORITY.json hybrid_mvp/tests/test_replay_governance.py
git commit -m "governance: invalidate inherited claims append-only"
```


## Task 3: Review and bind the predecessor test inventory

**Files:**

- Create: `hybrid_mvp/governance/predecessor_test_inventory.json`
- Create: `hybrid_mvp/scripts/check_test_inventory.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/governance.py`
- Modify: `hybrid_mvp/tests/test_replay_governance.py`
- Generate in Task 5: `hybrid_mvp/artifacts/validation/TEST_INVENTORY_RECEIPT.json`

### Step 1: Add failing inventory tests

The reviewed inventory has one explicit record per predecessor source test.
Assertions may be shared through a reviewed registry, but classification and
activation are per test:

```json
{
  "assertions": {
    "assertion:program-abi": "The switch vocabulary, five operators, source assignments and program identity remain exact."
  },
  "tests": [
    {
      "test_ref": "tests/test_program_abi.py::test_program_uses_only_five_persistent_operators",
      "classification": "retained",
      "activation_phase": "R1",
      "assertion_ref": "assertion:program-abi",
      "successor_refs": []
    }
  ]
}
```

Parse every tracked `tests/test_*.py` with `ast` and require exactly one reviewed
record for each function or class method whose name starts `test_`. Require a
non-empty referenced assertion, allowed `retained|rewritten|historical`
classification, activation phase for retained tests, successor refs for
rewritten tests, and no duplicate/orphan record. Parameterized collected node
IDs map to their exact source `test_ref`. A file-level default is forbidden.
Do not derive assertions or classifications from test names.

Run and observe RED:

```powershell
python -m pytest tests\test_replay_governance.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-g0-inventory
```

### Step 2: Curate all 59 predecessor files

Curate all 634 predecessor source-test records by earliest truthful owner:

- G0: governance/validator.
- R1: canonical serialization, persistence/recovery, ABI, receipts, runtime-path
  and restart structure.
- R2: forms, grounding, contributions, affordances, coverage, action masks,
  recursive graph, reference/scope/transition and exact reconstruction.
- R3: epistemics, dialogue, query, state/effects, learning, proof, response and
  realization equivalence.
- R4: scenarios/episodes, negatives, leakage and training isolation.
- R5: neural proposer/realizer, calibration, weight use and reproduction.
- R6-R7: production cutover, end-to-end evaluation and release thresholds.
- Rewritten only when a concrete active successor preserves the assertion.
- Historical only when the assertion itself depended on a retired semantic path.

`tests/test_release_thresholds.py` stays retained with `activation_phase=R7`; preserve its current red
result. The structured collector in Task 4 expands parameterized node IDs and
binds every collected node to exactly one reviewed source rule.

### Step 3: Verify, review, commit

```powershell
python scripts\check_test_inventory.py --source-only
python -m pytest tests\test_replay_governance.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-g0-inventory
git add hybrid_mvp/governance/predecessor_test_inventory.json hybrid_mvp/scripts/check_test_inventory.py hybrid_mvp/src/cemm_authoritative_hybrid/governance.py hybrid_mvp/tests/test_replay_governance.py
git commit -m "governance: inventory predecessor semantic tests"
```

## Task 4: Replace the profile-label validator with one structured DAG runner

**Files:**

- Create: `hybrid_mvp/scripts/validation_gate.py`
- Create: `hybrid_mvp/scripts/pytest_gate_runner.py`
- Rewrite: `hybrid_mvp/scripts/validate_mvp.py`
- Create: `hybrid_mvp/configs/validation_gates.json`
- Create: `hybrid_mvp/tests/test_validation_gate.py`
- Create: `hybrid_mvp/tests/test_g0_integration.py`
- Modify: `hybrid_mvp/pyproject.toml` only for strict declared markers, if used

### Step 1: Specify behavior with RED tests

```python
def test_dag_deduplicates_shared_dependencies() -> None:
    graph = GateGraph.from_dict({
        "steps": {
            "governance": {"depends_on": []},
            "compile": {"depends_on": ["governance"]},
            "tests": {"depends_on": ["governance"]},
            "phase": {"depends_on": ["compile", "tests"]},
        },
        "tiers": {"phase": ["phase"]},
    })
    assert graph.resolve("phase") == ("governance", "compile", "tests", "phase")


def test_every_test_tier_is_fresh() -> None:
    for tier in ("owner", "phase", "admission"):
        assert GatePolicy.for_tier(tier).test_results_must_be_fresh


def test_missing_structured_report_fails_closed(tmp_path: Path) -> None:
    result = parse_pytest_report(tmp_path / "missing.json")
    assert result.disposition == "error"
    assert result.error_code == "structured_report_missing"
```

Add these concrete tests as well:

```python
def test_report_classification_is_structural() -> None:
    summary = summarize_reports((
        ReportFact("a", "call", "failed", False),
        ReportFact("b", "setup", "failed", False),
        ReportFact("c", "call", "skipped", False),
        ReportFact("d", "call", "skipped", True),
        ReportFact("e", "call", "passed", True),
    ))
    assert summary.counts == {
        "passed": 0, "failure": 1, "error": 1,
        "skip": 1, "xfail": 1, "xpass": 1,
    }


def test_receipt_write_is_exclusive(tmp_path: Path, gate_receipt: GateReceipt) -> None:
    target = tmp_path / "receipt.json"
    write_receipt_exclusive(target, gate_receipt)
    with pytest.raises(FileExistsError):
        write_receipt_exclusive(target, gate_receipt)


def test_isolated_environment_owns_all_writable_paths(tmp_path: Path) -> None:
    env, pytest_args = isolated_test_environment(tmp_path)
    for key in ("TMP", "TEMP", "TMPDIR", "PYTHONPYCACHEPREFIX"):
        assert Path(env[key]).is_relative_to(tmp_path)
    assert str(tmp_path) in " ".join(pytest_args)


def test_slowest_rows_are_bounded_and_sorted() -> None:
    rows = bounded_slowest((("a", 1), ("b", 9), ("c", 4)), limit=2)
    assert rows == (("b", 9), ("c", 4))


def test_cli_rejects_legacy_profile(project_root: Path) -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/validate_mvp.py", "--profile", "development"],
        cwd=project_root, text=True, capture_output=True, check=False,
    )
    assert completed.returncode != 0
    assert "unrecognized arguments" in completed.stderr
```

Add the remaining mandatory tests explicitly:

```python
def test_runner_records_injected_peak_rss() -> None:
    process = FakeProcess(poll_results=(None, None, 0), returncode=0)
    observation = observe_process(
        process,
        rss_reader=iter((100, 12345, 900)).__next__,
    )
    assert observation.exit_code == 0
    assert observation.peak_rss_bytes == 12345


def test_collection_error_still_writes_structured_report(
    tmp_path: Path, project_root: Path
) -> None:
    broken = tmp_path / "test_broken.py"
    report = tmp_path / "report.json"
    broken.write_text("import module_that_does_not_exist\n", encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "scripts/pytest_gate_runner.py", "--report", str(report),
         "--", str(broken), "-q"],
        cwd=project_root, text=True, capture_output=True, check=False,
    )
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert completed.returncode != 0
    assert payload["counts"]["error"] == 1
```

In `test_g0_integration.py` add:

```python
def test_g0_admission_plan_is_coalesced_and_bounded(project_root: Path) -> None:
    graph = load_gate_graph(project_root / "configs/validation_gates.json")
    assert graph.resolve_phase("G0", "admission") == (
        "governance", "source_compile", "pytest_active"
    )
    assert not {
        "corpus", "training", "reproduction"
    } & set(graph.resolve_phase("G0", "admission"))


def test_runtime_has_no_validation_import(project_root: Path) -> None:
    runtime = (project_root / "src/cemm_authoritative_hybrid/runtime.py").read_text(
        encoding="utf-8"
    )
    assert "validation_gate" not in runtime
    assert "pytest_gate_runner" not in runtime
```

### Step 2: Implement immutable results

```python
@dataclass(frozen=True)
class StepResult:
    step_ref: str
    step_id: str
    disposition: str
    input_ref: str
    report_ref: str | None
    exit_code: int
    wall_ns: int
    peak_rss_bytes: int | None
    error_code: str | None


@dataclass(frozen=True)
class GateReceipt:
    gate_result_ref: str
    run_ref: str
    tier: str
    phase: str
    fresh: bool
    source_ref: str
    environment_ref: str
    started_at_utc: str
    run_nonce: str
    step_results: tuple[StepResult, ...]
```

`StepResult.step_ref` excludes `wall_ns` and `peak_rss_bytes`. `gate_result_ref`
covers semantic inputs/dispositions/report/error refs but excludes all clocks,
nonces and performance observations. `run_ref` covers the complete serialized
receipt, including start time, nonce, wall time and peak RSS, permitting multiple
fresh observations. Deserializers recompute both identity layers and reject
mismatch.

### Step 3: Implement direct pytest JSON hooks

`scripts/pytest_gate_runner.py` imports only stdlib and pytest, constructs the
structured plugin object, and passes it to `pytest.main(..., plugins=[plugin])`
before test collection. This avoids importing the production package before
hooks exist. The plugin writes JSON directly from `pytest_collection_finish`,
`pytest_collectreport`, `pytest_runtest_logreport` and `pytest_sessionfinish`.
Never parse human output. Classify structurally:

- skipped + `wasxfail` -> xfail;
- passed + `wasxfail` -> xpass;
- skipped alone -> skip;
- setup/teardown failure -> error;
- call failure -> failure.

Missing/malformed reports fail closed. Launch argv with `shell=False`. Put `TMP`,
`TEMP`, `TMPDIR`, `PYTHONPYCACHEPREFIX`, `--basetemp` and `cache_dir` inside one
run root. Do not require external `PYTHONPATH`. Measure child peak RSS via a
platform sampler and permit sampler injection in unit tests.

### Step 4: Implement only three coalesced tiers

`validation_gates.json` owns `owner`, `phase` and `admission`. Use this concrete
shape; `pytest_active` derives exact selectors from retained inventory entries
whose `activation_phase` is no later than the candidate phase:

```json
{
  "schema": "cemm-hybrid-validation-gates-v1",
  "steps": {
    "governance": {
      "kind": "command",
      "depends_on": [],
      "argv": ["scripts/check_test_inventory.py", "--source-only"],
      "inputs": ["docs/DOCUMENT_AUTHORITY.json", "governance/"]
    },
    "source_compile": {
      "kind": "compile",
      "depends_on": ["governance"],
      "roots": ["src/", "scripts/", "tests/"],
      "inputs": ["src/", "scripts/", "tests/"]
    },
    "g0_owner_tests": {
      "kind": "pytest",
      "depends_on": ["source_compile"],
      "selectors": ["tests/test_replay_governance.py"],
      "inputs": ["tests/test_replay_governance.py", "docs/", "governance/"]
    },
    "g0_phase_tests": {
      "kind": "pytest",
      "depends_on": ["source_compile"],
      "selectors": ["tests/test_g0_integration.py"],
      "inputs": ["tests/test_g0_integration.py", "scripts/", "configs/validation_gates.json"]
    },
    "pytest_active": {
      "kind": "pytest_inventory",
      "depends_on": ["source_compile"],
      "inventory": "governance/predecessor_test_inventory.json",
      "inputs": ["tests/", "src/", "governance/predecessor_test_inventory.json"]
    },
    "authority_link": {
      "kind": "authority_link",
      "depends_on": ["source_compile"],
      "inputs": ["data/authority/", "src/cemm_authoritative_hybrid/authority.py"]
    },
    "sqlite_activation": {
      "kind": "sqlite_activation",
      "depends_on": ["authority_link"],
      "inputs": ["src/cemm_authoritative_hybrid/persistence.py", "data/authority/"]
    }
  },
  "phases": {
    "G0": {
      "owners": {"governance": ["g0_owner_tests"]},
      "phase": ["g0_phase_tests"],
      "admission": ["pytest_active"]
    }
  }
}
```

The config validator rejects unknown step
kinds/paths, cycles, duplicate resolved steps and an admission plan containing
training/corpus/reproduction. Input refs hash the listed paths and environment
identity; the runner resolves dependencies once.

G0-R1 never caches test results: owner runs focused tests, phase runs only fresh
cross-owner integration tests, and admission runs the complete currently active
suite once. Later R4-R5 plans may reuse content-matched diagnostics for expensive
artifact steps, never tests or admission.

### Step 5: Verify, review, commit

```powershell
python -m pytest tests\test_validation_gate.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-g0-validator
python scripts\validate_mvp.py --tier phase --phase G0
python scripts\validate_mvp.py --help
git add hybrid_mvp/scripts/validation_gate.py hybrid_mvp/scripts/pytest_gate_runner.py hybrid_mvp/scripts/validate_mvp.py hybrid_mvp/configs/validation_gates.json hybrid_mvp/tests/test_validation_gate.py hybrid_mvp/tests/test_g0_integration.py hybrid_mvp/pyproject.toml
git commit -m "build: add structured dependency-aware replay validation"
```

## Task 5: Admit G0 without pretending runtime/model success

**Files:**

- Create: `hybrid_mvp/artifacts/validation/BASELINE_REPLAY_FINDINGS.json`
- Generate: `hybrid_mvp/artifacts/validation/TEST_INVENTORY_RECEIPT.json`
- Generate: `hybrid_mvp/artifacts/validation/runs/<run_ref>.json`
- Append: `hybrid_mvp/governance/replay_status.jsonl`


### Step 1: Capture exact baseline findings

Bind commands, environment/source ref, 743-node collection, both threshold
failures, proposal/runtime divergence, and authority EOL failure. State
`runtime_admitted: false` and `model_artifacts_admitted: false`. G0 validates
that forensic evidence; it does not require downstream R1/R7 behavior to pass.

### Step 2: Run exactly one fresh G0 admission

Task 1-4 red/green work already ran owner and phase tiers. Do not rerun them
ceremonially before admission.

```powershell
python scripts\validate_mvp.py --tier admission --phase G0
```

The fresh admission has zero G0-active skip/xfail/xpass, binds every downstream
retained node to the inventory, and runs no corpus/model work. Inspect and
cryptographically verify that one receipt before any status transition.

### Step 3: Validate, then append G0 green

`update_replay_status.py --dry-run` builds the exact candidate transition against
the verified, unique, unconsumed G0 admission receipt without writing. Only if
that validates, append it once. Effective state becomes `G0=green, R1-R8=red`.

```powershell
python scripts\update_replay_status.py --phase G0 --status green --admit-latest --dry-run
python scripts\update_replay_status.py --phase G0 --status green --admit-latest --append
python scripts\update_replay_status.py --verify-chain
git add hybrid_mvp/artifacts/validation/BASELINE_REPLAY_FINDINGS.json hybrid_mvp/artifacts/validation/TEST_INVENTORY_RECEIPT.json hybrid_mvp/artifacts/validation/runs hybrid_mvp/governance/replay_status.jsonl hybrid_mvp/tests/test_replay_governance.py
git commit -m "chore: admit corrective replay governance"
```


## Task 6: Make revision and governed-source identity portable

**Files:**

- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/persistence.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/canonical.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/authority.py`
- Modify: `.gitattributes`
- Create: `hybrid_mvp/tests/test_r1_content_identity.py`
- Modify callers of private revision serializers

### Step 1: Add RED identity/portability tests

```python
def test_revision_pin_round_trip_preserves_every_field() -> None:
    pin = RevisionPin(
        authority_generation="authority:g1", world_revision=1,
        session_revision=2, episode_revision=3, effect_revision=4,
        model_identity="model:m1",
    )
    restored = RevisionPin.from_dict(pin.as_dict())
    assert restored == pin
    assert restored.revision_ref == pin.revision_ref


def test_governed_text_hash_is_eol_portable(tmp_path: Path) -> None:
    lf, crlf = tmp_path / "lf.json", tmp_path / "crlf.json"
    lf.write_bytes(b'{"a":1}\n')
    crlf.write_bytes(b'{"a":1}\r\n')
    assert sha256_governed_text(lf) == sha256_governed_text(crlf)
```

Also reject unknown/missing fields, wrong scalar types and any nested ref
tampering. Run and observe RED.

### Step 2: Implement canonical owners

`RevisionPin.as_dict()` is the only serializer; `from_dict()` requires the exact
six-field set/types. Identity is:

```python
@property
def revision_ref(self) -> str:
    return stable_ref("revision_pin", self.as_dict())
```

`sha256_governed_text` strips UTF-8 BOM, normalizes CRLF/CR to LF and hashes the
result. Use it only for governed text/JSON, never model/binary artifacts.
Authority linking uses this owner. Add explicit LF attributes for hybrid
authority/config JSON.

### Step 3: Verify, review, commit

```powershell
python -m pytest tests\test_r1_content_identity.py tests\test_authority_linker.py tests\test_persistence.py tests\test_persistence_recovery.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-r1-identity
git add .gitattributes hybrid_mvp/src/cemm_authoritative_hybrid/canonical.py hybrid_mvp/src/cemm_authoritative_hybrid/persistence.py hybrid_mvp/src/cemm_authoritative_hybrid/authority.py hybrid_mvp/tests/test_r1_content_identity.py
git commit -m "refactor: make R1 revision and authority identity exact"
```

## Task 7: Hard-cut one program/proposal/verifier ABI

**Files:**

- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/programs.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/proposal.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/model.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/verifier.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/propositions.py`
- Modify active callers in `bootstrap.py`, `coverage.py`, `training.py` and `evaluation.py`
- Modify affected R1 fixtures/tests
- Create: `hybrid_mvp/tests/test_r1_verification_batch.py`
- Create: `hybrid_mvp/tests/test_r1_no_alternate_public_paths.py`

### Step 1: Add RED owner/content tests

```python
def test_cross_phase_types_have_one_owner() -> None:
    assert class_owners("SemanticSwitchProgram") == {"programs.py"}
    assert class_owners("ProposalResult") == {"proposal.py"}
    assert class_owners("VerificationResult") == {"verifier.py"}


def test_proposal_phase_output_binds_the_complete_batch(proposal_result) -> None:
    assert proposal_result.candidates
    assert not hasattr(proposal_result, "program")
    assert proposal_result.output_refs == (proposal_result.proposal_ref,)
    first = proposal_result.candidates[0]
    assert proposal_result.candidate_by_ref(first.program_ref) is first
```

Add tests that every semantic field affects its ref and every deserializer
rejects a stored/nested ref mismatch.

### Step 2: Make leaf/container refs strict

`ProgramAction` and `SourceAssignment` get
`create(...)` constructors deriving refs from all semantic fields. `from_dict`
reconstructs then compares the serialized ref. `SemanticSwitchProgram.create`
derives `program_ref` from orientation, ordered actions, roots, mode, goals,
source set, assignments and revision pin.

`ScopeFrame` and `TransitionProposal` remain R2-owned and are not hardened or activated in R1.

Do not put observational scores/clocks in program identity. Do include literal
and dynamic-pointer values and order; `action_encoding_hash` is not complete
identity.

### Step 3: Define the exact proposal batch

```python
@dataclass(frozen=True)
class ProposalResult:
    proposal_ref: str
    orientation_ref: str
    candidates: tuple[SemanticSwitchProgram, ...]
    status: Literal["candidates", "abstained"]
    abstention_code: str | None
    explored_states: int
    truncated: bool
    model_identity: str
    revision_pin: RevisionPin

    @property
    def output_refs(self) -> tuple[str, ...]:
        return (self.proposal_ref,)

    def candidate_by_ref(self, program_ref: str) -> SemanticSwitchProgram:
        matches = tuple(c for c in self.candidates if c.program_ref == program_ref)
        if len(matches) != 1:
            raise KeyError(program_ref)
        return matches[0]
```

Create/deserialization derives/checks `proposal_ref` from every field. Candidate
refs are unique and ordered; each candidate must match the proposal orientation
and revision pin. `status="abstained"` requires zero candidates and a non-empty
typed code; `status="candidates"` requires candidates and no abstention code.
`candidate_by_ref` requires exactly one match. There is no `program` compatibility
property.

Critically, PROPOSE must not invoke `ExactProgramVerifier`. Remove current
verifier calls in `proposal.py` and `model.py`. Proposal may enforce decoder
action masks, but exact independent acceptance occurs only in VERIFY.

### Step 4: Add independent batch verification

Keep canonical `VerificationResult` semantics, but complete serialization/hash
coverage includes error code/detail/action and full coverage receipt. Add:

```python
@dataclass(frozen=True)
class CandidateVerificationReceipt:
    receipt_ref: str
    candidate_index: int
    program: SemanticSwitchProgram
    result: VerificationResult


@dataclass(frozen=True)
class VerificationBatchResult:
    batch_ref: str
    proposal_ref: str
    candidate_receipts: tuple[CandidateVerificationReceipt, ...]
    status: Literal["selected", "rejected", "abstained", "ambiguous"]
    selected_program_ref: str | None
    ambiguity_program_refs: tuple[str, ...]
```

`verify_candidates(proposal)` emits exactly one receipt per candidate. Receipt
indices are contiguous and preserve proposal order; each embedded program ref,
result program ref and proposal candidate ref must agree. Selected and ambiguous
refs must identify accepted receipts. Rejected/abstained/ambiguous batches carry
no selected ref; selected batches carry exactly one. Exactly one accepted
candidate is selected, zero is rejected, explicit abstention stays abstained,
and multiple accepted alternatives are ambiguous until R2 settling. Constructors
and deserializers enforce every cross-field rule. Verifier programming
exceptions propagate.

### Step 5: Remove the legacy program wrapper safely

Keep `Application`/`PropositionGraph` as graph structures for later owner work,
but remove `propositions.SemanticSwitchProgram` only after every import-bearing
module can collect without it. Migrate production imports in `runtime.py`,
`bootstrap.py` and `episodes.py` to the canonical program. Refactor `query.py`
to accept `PropositionGraph` directly and `epistemics.py` to accept its graph and
evidence inputs explicitly; never add `.graph/.mode/.evidence` compatibility
properties.

Update import-bearing predecessor tests and shared fixtures before deletion,
including `test_epistemic_admission.py`, `test_inference_bounds.py`,
`test_learning_distinctions.py`, `test_query_engine.py`,
`test_recursive_inference.py`, `test_restart_e2e.py`,
`test_synonym_acquisition.py` and `tests/conftest.py`. Retained tests activated
after R1 may still require later behavioral rewrites, but their modules must
import and collect now. Run structured collection across the entire predecessor
tree and require no collection errors and no loss of the 743 baseline nodes
before deleting the duplicate class.

### Step 6: Verify, review, commit

```powershell
python -m pytest tests\test_r1_content_identity.py tests\test_r1_verification_batch.py tests\test_program_abi.py tests\test_bootstrap_proposer.py tests\test_neural_proposer.py tests\test_exact_verifier.py tests\test_adversarial_programs.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-r1-abi
python scripts\pytest_gate_runner.py --report C:\tmp\cemm-r1-all-collect.json -- --collect-only -q
git add hybrid_mvp/src/cemm_authoritative_hybrid hybrid_mvp/tests
git commit -m "refactor: hard-cut canonical R1 proposal and verification ABIs"
```


## Task 8: Finalize one content-addressed phase/cycle result

**Files:**

- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/cycle.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/runtime.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/__init__.py`
- Modify: `hybrid_mvp/tests/test_phase_receipts.py`
- Modify: `hybrid_mvp/tests/test_cognitive_loop_e2e.py`
- Modify: `hybrid_mvp/tests/conftest.py`
- Extend: `hybrid_mvp/tests/test_r1_content_identity.py`

### Step 1: Add RED result identity tests

Require one `CycleResult` class, no `KernelCycleResult`, no `ProcessResult`, no
`.kernel` view, checked phase `receipt_ref` values, and sensitivity to every
deterministic phase/status/gap/effect/final-pin field. Changing `duration_ns`
must not change semantic receipt/cycle identity.

### Step 2: Implement non-circular finalization

Accumulate deterministic phase facts first. Compute final `cycle_ref` from
input/orientation, status, ordered phase semantic material (excluding parent
cycle ref and duration), gap/effect/response/realization refs and final pin.
Then instantiate `PhaseReceipt` rows with the final cycle ref. A receipt ref
includes that cycle ref plus deterministic phase material, excluding duration.
`CycleResult` recomputation uses receipt semantic material rather than receipt
refs, so there is no circular hash.

### Step 3: Remove compatibility results

Delete `KernelCycleResult`, `CycleResult.kernel`, `ProcessResult` and the
production `_FixtureCycleRunner`. Test fixtures live under `tests/` and return
the same canonical `CycleResult`. Use typed artifact fields; later fields can be
`None` only when status/gap proves the phase was not reached.

### Step 4: Verify, review, commit

```powershell
python -m pytest tests\test_r1_content_identity.py tests\test_phase_receipts.py tests\test_cognitive_loop_e2e.py tests\test_restart_e2e.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-r1-cycle
git add hybrid_mvp/src/cemm_authoritative_hybrid/cycle.py hybrid_mvp/src/cemm_authoritative_hybrid/runtime.py hybrid_mvp/src/cemm_authoritative_hybrid/__init__.py hybrid_mvp/tests
git commit -m "refactor: finalize canonical R1 phase and cycle receipts"
```

## Task 9: Leave one public process path and composition root

**Files:**

- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/runtime.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/bootstrap.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/evaluation.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/episodes.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/cli.py`
- Modify: `hybrid_mvp/scripts/evaluate_cemm.py`
- Modify: `hybrid_mvp/scripts/run_demo.py`
- Modify: `hybrid_mvp/configs/validation_gates.json`
- Modify affected tests/fixtures
- Create: `hybrid_mvp/tests/test_r1_runtime_path.py`
- Create: `hybrid_mvp/tests/test_r1_phase_integration.py`

### Step 1: Add RED path tests

Require:

- one public `HybridRuntime.process(session_ref, text, *, trace=True) -> CycleResult`;
- no `process_evidence`, `propose_and_verify`, shape probing or signature inspection;
- no duplicate phase-result classes in `runtime.py`;
- no `evaluation.build_release_runtime`;
- evaluator/CLI use `bootstrap.load_runtime` and `process`;
- programming exceptions propagate;
- zero/one/multiple accepted batches yield deterministic typed outcomes.

### Step 2: Use exact owner signatures

```python
class ProposalOwner(Protocol):
    def propose(self, orientation: Orientation) -> ProposalResult: raise NotImplementedError


class VerificationOwner(Protocol):
    def verify_candidates(self, proposal: ProposalResult) -> VerificationBatchResult: raise NotImplementedError


def process(self, session_ref: str, text: str, *, trace: bool = True) -> CycleResult:
    orientation = self.orient(session_ref, text)
    proposal = self._proposal_owner.propose(orientation)
    verification = self._verification_owner.verify_candidates(proposal)
    if verification.status in {"rejected", "abstained"}:
        return self._finalize_verification_gap(orientation, proposal, verification)
    if verification.status == "ambiguous":
        return self._finalize_ambiguity(orientation, proposal, verification)
    program = proposal.candidate_by_ref(verification.selected_program_ref)
    return self._continue_or_report_disabled_owner(
        orientation, proposal, verification, program, trace=trace
    )
```

No broad exception catch is allowed. Expected semantic failures become typed
results at their owner; implementation errors propagate.

### Step 3: Make one composition root

```python
def load_runtime(
    root: str | Path,
    *,
    profile: Literal["development", "neural", "release"],
    device: str = "cpu",
    store_path: str | Path | None = None,
    proposal_artifact_dir: str | Path | None = None,
    realizer_artifact_dir: str | Path | None = None,
) -> HybridRuntime:
```

`profile` is required; remove `proposal_fixture`. Release fails closed until
R3/R5 owners/artifacts are admitted. Production bootstrap contains no
`_Fixture*` owner. An explicitly disabled later owner may return only an
implementation-gap artifact; it cannot resolve, mutate or realize a normal
surface.

### Step 4: Migrate callers, then delete alternates

Migrate evaluation, episodes, CLI, demo and tests to `load_runtime/process`.
Evaluator reads `CycleResult.proposal/verification`, not a shortcut. CLI may
serialize a typed R1 diagnostic cycle but must not invent a surface. Align R4/R7
caller paths without claiming authentic corpus/evaluation.

Only after `rg` shows zero callers, delete `process_evidence`,
`propose_and_verify`, `_ProposeAndVerifyResult` and
`build_release_runtime`. Future R3/R5 tests remain inventoried, not made green
with adapters.

### Step 5: Add the now-existing R1 gate selectors

After the R1 test files exist, extend `validation_gates.json` with:

```json
{
  "r1_owner_tests": {
    "kind": "pytest",
    "depends_on": ["source_compile"],
    "selectors": ["tests/test_r1_content_identity.py", "tests/test_r1_verification_batch.py", "tests/test_r1_runtime_path.py", "tests/test_r1_no_alternate_public_paths.py"],
    "inputs": ["tests/test_r1_content_identity.py", "tests/test_r1_verification_batch.py", "tests/test_r1_runtime_path.py", "tests/test_r1_no_alternate_public_paths.py", "src/cemm_authoritative_hybrid/"]
  },
  "r1_phase_tests": {
    "kind": "pytest",
    "depends_on": ["source_compile"],
    "selectors": ["tests/test_r1_phase_integration.py", "tests/test_program_abi.py", "tests/test_exact_verifier.py", "tests/test_phase_receipts.py", "tests/test_six_phase_runtime.py"],
    "inputs": ["tests/test_r1_phase_integration.py", "tests/test_program_abi.py", "tests/test_exact_verifier.py", "tests/test_phase_receipts.py", "tests/test_six_phase_runtime.py", "src/cemm_authoritative_hybrid/"]
  },
  "R1": {
    "owners": {"runtime-abi": ["r1_owner_tests"]},
    "phase": ["r1_phase_tests"],
    "admission": ["sqlite_activation", "pytest_active"]
  }
}
```

The first two objects are merged into `steps` and `R1` into `phases`. Config
validation now requires every selector to exist. Add this phase-integration test:

```python
def test_r1_phase_does_not_repeat_owner_tests(project_root: Path) -> None:
    graph = load_gate_graph(project_root / "configs/validation_gates.json")
    resolved = graph.resolve_phase("R1", "phase")
    assert resolved == ("governance", "source_compile", "r1_phase_tests")
    assert "r1_owner_tests" not in resolved
    assert len(resolved) == len(set(resolved))
```

### Step 6: Verify, review, commit

```powershell
python -m pytest tests\test_r1_runtime_path.py tests\test_r1_no_alternate_public_paths.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-r1-runtime
python scripts\validate_mvp.py --tier phase --phase R1
git add hybrid_mvp/src/cemm_authoritative_hybrid hybrid_mvp/scripts hybrid_mvp/configs/validation_gates.json hybrid_mvp/tests
git commit -m "refactor: leave one canonical hybrid runtime path"
```

## Task 10: Fresh R1 admission and truthful status

**Files:**

- Generate: `hybrid_mvp/artifacts/validation/runs/<run_ref>.json`
- Generate: `hybrid_mvp/artifacts/validation/R1_ADMISSION_RECEIPT.json`
- Append: `hybrid_mvp/governance/replay_status.jsonl`

### Step 1: Run structural owner proof

```powershell
rg -n "class (SemanticSwitchProgram|ProposalResult|VerificationResult|CycleResult|KernelCycleResult|ProcessResult)" src\cemm_authoritative_hybrid
rg -n "inspect\.signature|def process_evidence|def propose_and_verify|def build_release_runtime|proposal\.program|\.kernel\b" src\cemm_authoritative_hybrid
```

First scan must show one canonical owner per surviving type; second is empty.

### Step 2: Run exactly one fresh R1 admission

Task 6-9 red/green work already ran owner and phase tiers. Do not rerun them
immediately before admission.

```powershell
python scripts\validate_mvp.py --tier admission --phase R1
```

That one run performs portable authority linking, fresh SQLite activation,
complete G0-R1 active tests, source compile and corruption checks. It excludes
corpus/training/reproduction and accounts for every later retained node.

### Step 3: Inspect, validate, then append R1 green

Controller inspects the same receipt's structured counts, wall time, peak RSS
and slowest cases and verifies its content refs. Then validate the status
transition without writing, append once, and verify the chain:

```powershell
python scripts\update_replay_status.py --phase R1 --status green --admit-latest --dry-run
python scripts\update_replay_status.py --phase R1 --status green --admit-latest --append
python scripts\update_replay_status.py --verify-chain
```

Leave R2-R8 red. ABI_REGISTRY and INTEGRATION already point to the status ledger; do not change governing inputs after admission.
Investigate unexplained cost growth; never weaken semantic bounds/coverage.

```powershell
git add hybrid_mvp/artifacts/validation hybrid_mvp/governance/replay_status.jsonl
git commit -m "chore: admit canonical hybrid replay R1"
```

Request full-plan contract review then code-quality/performance review.

## R1 handoff

R1 is complete only with a verified fresh receipt and effective status
`G0=green, R1=green, R2-R8=red`. Then write the detailed R2 plan from observed
R1 APIs/receipts. Do not begin R2 from donor assumptions or retain a temporary
R1 adapter.
