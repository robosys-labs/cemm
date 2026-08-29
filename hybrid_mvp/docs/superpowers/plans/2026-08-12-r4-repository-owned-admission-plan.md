# R4 Repository-Owned Admission Implementation Plan

> **Superseded execution evidence:** This document is retained for forensic
> history only. It cannot authorize current work or phase status. Current status
> is derived from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).
> The August 29 R4.1 data/supervision amendment supersedes conflicting
> partition, feasibility, gold and realization instructions.

> **Historical completion notice (2026-08-13):** R4 has been admitted; worktree
> paths, cleanup commands, and task state in the body are historical, not current
> routing. Status is derived only from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).
> **Partition-boundary supersession (2026-08-22):** the repository-owned
> admission migration remains historical governing evidence, while its
> Build Receipt ABI 3, per-axis partition, and training-allowlist tasks are
> superseded by the 2026-08-14 partition corrective design and plan.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Retire the R4 external signed-manifest subsystem, replace it with exact repository-owned artifact-integrity admission, regenerate the R4 artifact graph, admit R4 green, and merge the closeout to `main`.

**Architecture:** Make a hard ABI cut from externally approved R4 builds to deterministic admission candidates. A focused `r4_admission.py` owner reconstructs every committed artifact and emits an exact integrity report; the validation control plane binds that report to the clean committed R4 source, linked authority, active tests, and append-only governance receipt. Source migration, generated artifacts, and final admission are separate commits so generator provenance and governance provenance remain exact.

**Tech Stack:** Python 3, pytest, canonical JSON/JSONL, content-addressed receipts, SQLite activation, PowerShell, Git worktrees.

---

## File map

- `src/cemm_authoritative_hybrid/r4_pipeline.py` — own R4 Build Receipt ABI 3 and deterministic admission-candidate construction; remove external approval types.
- `src/cemm_authoritative_hybrid/r4_admission.py` — reconstruct committed R4 artifacts and emit the internal integrity report without verifier inputs.
- `src/cemm_authoritative_hybrid/r4_environment.py` — keep runtime/environment ownership but accept the explicit generator source revision.
- `src/cemm_authoritative_hybrid/__init__.py` — remove the retired `CorpusReviewManifest` package export.
- `scripts/build_r4_artifacts.py` — require `--source-revision` and pass it into the R4 build environment.
- `scripts/diagnose_r4_cases.py` — pass an explicit source revision when loading the R4 environment owner.
- `scripts/validation_gate.py` — replace the R4 review step kind, schema, handler, and evidence policy with artifact integrity.
- `scripts/update_replay_status.py` — remove the nonexistent review manifest from R4 evidence.
- `scripts/check_r3_r4_structure.py` — assert the retired external-review subsystem is absent.
- `scripts/prepare_r4_review_request.py` — delete the retired request generator.
- `scripts/verify_r4_review_manifest.py` — delete the retired verifier CLI.
- `src/cemm_authoritative_hybrid/r4_review.py` — delete the retired signed-manifest ABI and trust-root owner.
- `schemas/corpus_review_manifest.schema.json` — delete the retired manifest schema.
- `data/review/R4_REVIEW_MANIFEST.template.json` — delete the retired template.
- `schemas/r4_build_receipt.schema.json` — align the exact Build Receipt ABI 3 wire fields and admission-candidate state with Python.
- `tests/test_r4_admission.py` — add focused exact-reconstruction and tamper tests.
- `tests/test_r4_expansion_and_review.py` — keep surface-expansion tests only; remove signature tests and rename to `test_r4_expansion.py`.
- `tests/test_r4_structure.py` — replace anti-self-signing assertions with hard-cut absence assertions.
- `tests/test_r4_environment.py` — assert explicit generator source propagation rather than inherited R3 source.
- `tests/test_r4_closeout_regressions.py` — pass explicit source revision to direct environment-factory probes.
- `tests/test_r4_validation_gate.py` — test the exact R4 integrity report, generator-source derivation, and no-environment admission handler.
- `tests/test_lazy_package_imports.py` — remove the retired public export.
- `configs/validation_gates.json` — register the new step kind and exact successor nodes.
- `docs/ABI_REGISTRY.md` — retire the manifest/approval ABIs and register Build Receipt ABI 3.
- `docs/DOCUMENT_AUTHORITY.json` — make the new approved spec and plan governing; move the external-review closeout spec/plan to superseded claims and refresh the inventory pin only if inventory bytes change.
- `docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md` — add a narrow notice that its generic governance remains active but its R4 external-review clauses are superseded.
- `docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md` — add the same narrow R4 supersession notice without rewriting G0-R3 history.
- `docs/superpowers/plans/2026-08-05-hybrid-mvp-r3-r4-implementation-plan.md` — preserve R3 history while superseding its R4 external-review tasks.
- `docs/superpowers/specs/2026-08-12-r4-final-admission-closeout-design.md` — mark superseded by the repository-owned design.
- `docs/superpowers/plans/2026-08-12-r4-final-admission-closeout-plan.md` — mark superseded by this plan.
- `artifacts/r4/**` — regenerate the complete deterministic artifact graph under Build Receipt ABI 3.
- `artifacts/validation/TEST_INVENTORY_RECEIPT.json` — reconstruct the living inventory receipt after selector/test changes.
- `artifacts/validation/runs/<run-ref>.json` — add the passed R4 admission receipt.
- `governance/replay_status.jsonl` — append the effective R4 `green` record.

### Task 1: Create an isolated execution branch and record the legacy boundary

**Files:**
- Read: `docs/superpowers/specs/2026-08-12-r4-repository-owned-admission-design.md`
- Read: `src/cemm_authoritative_hybrid/r4_review.py`
- Read: `src/cemm_authoritative_hybrid/r4_admission.py`
- Read: `configs/validation_gates.json`

- [ ] **Step 1: Create the isolated worktree**

From `C:\dev\cemm`, use the `using-git-worktrees` skill and create:

```powershell
git worktree add C:\dev\cemm\.worktrees\r4-repository-owned-admission -b codex/r4-repository-owned-admission main
```

Expected: a clean worktree at commit `1921d23` or its reviewed descendant. Do
not reuse `C:\dev\cemm\.worktrees\r4-final-admission-closeout`, and do not move
or stage untracked files from the primary workspace.

- [ ] **Step 2: Run the focused pre-change tests**

From the new worktree's `hybrid_mvp/` directory:

```powershell
python -m pytest tests/test_r4_expansion_and_review.py tests/test_r4_structure.py tests/test_lazy_package_imports.py -q -p no:cacheprovider
```

Expected: PASS, proving the legacy external-review contract is currently active.

- [ ] **Step 3: Capture the exact legacy footprint**

```powershell
rg -n "r4_review|CorpusReviewManifest|ApprovedR4Build|R4_REVIEW_MANIFEST|CEMM_R4_REVIEW|r4_artifact_review|external_review_required" src scripts tests configs schemas data docs/ABI_REGISTRY.md docs/DOCUMENT_AUTHORITY.json
```

Expected: matches in the exact files listed in the file map; preserve this output
for the hard-cut absence check in Task 5.

### Task 2: Cut Build Receipt ABI 3 and remove external approval from the pipeline

**Files:**
- Modify: `tests/test_r4_authentic_episodes.py`
- Modify: `src/cemm_authoritative_hybrid/r4_pipeline.py`
- Modify: `schemas/r4_build_receipt.schema.json`
- Modify: `src/cemm_authoritative_hybrid/__init__.py`
- Modify: `tests/test_lazy_package_imports.py`

- [ ] **Step 1: Write failing Build Receipt ABI 3 tests**

Add these assertions to `tests/test_r4_authentic_episodes.py` using a local
exact-value helper rather than the not-yet-regenerated committed artifact:

```python
from cemm_authoritative_hybrid.r4_pipeline import (
    R4_BUILD_RECEIPT_ABI_VERSION,
    R4BuildReceipt,
)


def _candidate_receipt() -> R4BuildReceipt:
    sha = "sha256:" + "0" * 64
    return R4BuildReceipt.create(
        source_revision="1" * 40,
        authority_generation="authority:test",
        abi_registry_ref="abi:test",
        scenario_source_sha256=sha,
        assertion_registry_sha256=sha,
        contract_set_sha256=sha,
        derivation_contract_set_sha256=sha,
        expanded_case_set_sha256=sha,
        episode_set_sha256=sha,
        mutation_set_sha256=sha,
        mutation_observation_set_sha256=sha,
        structural_sufficiency_sha256=sha,
        partition_manifest_sha256s=(sha,) * 7,
        training_allowlist_sha256=sha,
        admission_state="candidate",
    )


def test_r4_build_receipt_is_an_exact_admission_candidate() -> None:
    value = _candidate_receipt().as_dict()
    assert R4_BUILD_RECEIPT_ABI_VERSION == 3
    assert value["abi_version"] == 3
    assert value["admission_state"] == "candidate"
    assert "review_state" not in value
    assert R4BuildReceipt.from_dict(value).as_dict() == value


def test_r4_build_receipt_rejects_retired_review_state() -> None:
    value = _candidate_receipt().as_dict()
    value["review_state"] = value.pop("admission_state")
    with pytest.raises(ValueError, match="R4BuildReceipt"):
        R4BuildReceipt.from_dict(value)
```

Update only this module's literal metadata with two R4 `phase` entries and add
both exact nodes to `steps.r4_phase_tests.exact_nodes` in Task 5. Use a literal
64-zero hash temporarily; Task 6 replaces it mechanically before any governed
gate runs.

- [ ] **Step 2: Run the tests and verify the ABI failure**

```powershell
python -m pytest tests/test_r4_authentic_episodes.py -q -p no:cacheprovider
```

Expected: FAIL because the constant and committed artifact still declare ABI 2
and `review_state="external_review_required"`.

- [ ] **Step 3: Implement the minimal pipeline hard cut**

In `r4_pipeline.py`:

```python
R4_BUILD_RECEIPT_ABI_VERSION = 3

@dataclass(frozen=True, init=False)
class R4BuildReceipt:
    # existing hash and provenance fields remain exact
    admission_state: str

    # _FIELDS contains "admission_state" and not "review_state"

    @classmethod
    def create(cls, **values: Any) -> "R4BuildReceipt":
        # retain exact field/type validation
        if canonical["admission_state"] != "candidate":
            raise ValueError("R4 build receipt must remain an admission candidate")
        # identity namespace changes on the hard ABI cut
        object.__setattr__(obj, "receipt_ref", stable_ref("r4_build_v3", material))
```

Change `R4Pipeline.build()` to pass `admission_state="candidate"`. Remove:

```python
from .r4_review import CorpusReviewManifest, ReviewManifestVerifier
R4_APPROVAL_ABI_VERSION
ApprovedR4Build
```

Delete the complete `ApprovedR4Build` class. Remove `CorpusReviewManifest` from
the lazy package exports and from `PUBLIC_EXPORTS` in
`test_lazy_package_imports.py`.

- [ ] **Step 4: Align the exact JSON schema**

Replace `schemas/r4_build_receipt.schema.json` with a strict Draft 2020-12
schema whose `required` fields exactly equal `R4BuildReceipt._FIELDS`, including
`receipt_ref`, `assertion_registry_sha256`,
`derivation_contract_set_sha256`, `structural_sufficiency_sha256`, and
`admission_state`. Hash fields accept the active `sha256:<64 lowercase hex>`
wire shape, `abi_version` is `3`, `admission_state` is exactly `candidate`, and
`additionalProperties` is `false`.

- [ ] **Step 5: Run focused pipeline and package tests**

```powershell
python -m pytest tests/test_r4_authentic_episodes.py tests/test_lazy_package_imports.py -q -p no:cacheprovider
```

Expected: PASS. The focused tests use a newly constructed ABI 3 candidate and do
not decode the still-ABI-2 committed artifact. Do not add an ABI 2 decoder
fallback.

### Task 3: Replace external review with exact artifact-integrity reconstruction

**Files:**
- Create: `tests/test_r4_admission.py`
- Modify: `src/cemm_authoritative_hybrid/r4_admission.py`

- [ ] **Step 1: Write failing admission-owner tests**

Create `tests/test_r4_admission.py` with helpers that copy the tracked
`artifacts/r4/` tree and scenario source into `tmp_path`. In the copied tree
only, migrate `BUILD_RECEIPT.json` by decoding its existing field values,
replacing `review_state` with `admission_state="candidate"`, and rebuilding it
through `R4BuildReceipt.create`; this makes an ABI 3 fixture without changing or
trusting the committed ABI 2 receipt. Then add:

```python
def test_r4_admission_reconstructs_repository_owned_artifacts(tmp_path: Path) -> None:
    project, receipt = copied_r4_project(tmp_path)
    report = verify_r4_admission(
        project,
        expected_source_revision=receipt.source_revision,
        expected_authority_generation=receipt.authority_generation,
    )
    assert set(report) == {
        "schema", "artifact_count", "artifact_set_ref", "build_receipt_ref",
        "source_revision", "authority_generation", "integrity_ref",
    }
    assert report["schema"] == "cemm-r4-artifact-integrity-step-report-v1"
    assert report["artifact_count"] > 400


@pytest.mark.parametrize(
    ("relative", "mutation"),
    [
        ("episodes.jsonl", lambda raw: raw.replace(b'"passed":true', b'"passed":false', 1)),
        ("partitions/general.json", lambda raw: raw.replace(b'"axis":"general"', b'"axis":"lexical"', 1)),
        ("BUILD_RECEIPT.json", lambda raw: raw.replace(b'"authority_generation":"', b'"authority_generation":"tampered-', 1)),
    ],
)
def test_r4_admission_rejects_tampered_artifact(
    tmp_path: Path, relative: str, mutation,
) -> None:
    project, receipt = copied_r4_project(tmp_path)
    target = project / "artifacts" / "r4" / relative
    target.write_bytes(mutation(target.read_bytes()))
    with pytest.raises(R4AdmissionError):
        verify_r4_admission(
            project,
            expected_source_revision=receipt.source_revision,
            expected_authority_generation=receipt.authority_generation,
        )
```

The helper must preserve canonical LF bytes, load the copied Build Receipt via
`R4BuildReceipt.from_dict`, and copy only explicit R4 inputs. Register each test
as an R4 `owner` node with `owner_ref="artifact-integrity"`.

- [ ] **Step 2: Run the tests and verify the signature-argument failure**

```powershell
python -m pytest tests/test_r4_admission.py -q -p no:cacheprovider
```

Expected: FAIL because `verify_r4_admission()` still requires `verifier_spec`
and `verifier_sha256` and still loads the external manifest.

- [ ] **Step 3: Simplify the admission API and report**

Delete verifier imports, dynamic module loading, signature handling, the review
manifest path, and `ApprovedR4Build` construction from `r4_admission.py`. The
public signature becomes:

```python
def verify_r4_admission(
    root: str | Path,
    *,
    expected_source_revision: str,
    expected_authority_generation: str,
) -> dict[str, object]:
```

Rebuild the Build Receipt with `admission_state="candidate"`. Build
`artifact_refs` only from the receipt, contracts, cases, episodes, mutations,
observations, partitions, allowlist, and sufficiency receipt. Return:

```python
material = {
    "schema": "cemm-r4-artifact-integrity-step-report-v1",
    "artifact_count": len(artifact_refs),
    "artifact_set_ref": _content_ref("r4_admission_artifact_set", list(artifact_refs)),
    "build_receipt_ref": receipt.receipt_ref,
    "source_revision": receipt.source_revision,
    "authority_generation": receipt.authority_generation,
}
material["integrity_ref"] = _content_ref("r4_artifact_integrity", material)
```

Retain all strict JSON/JSONL decoding, non-empty checks, comparison checks,
mutation checks, sufficiency checks, seven-axis ordering, pin validation, and
exact receipt reconstruction.

- [ ] **Step 4: Run the admission-owner tests**

Run against the copied ABI 3 fixture:

```powershell
python -m pytest tests/test_r4_admission.py -q -p no:cacheprovider
```

Expected: all reconstruction and tamper tests pass against ABI 3 bytes. No test
creates a signature, manifest, verifier, or approval object.

### Task 4: Bind artifact generation to an explicit committed source revision

**Files:**
- Modify: `tests/test_r4_environment.py`
- Modify: `tests/test_r4_closeout_regressions.py`
- Modify: `src/cemm_authoritative_hybrid/r4_environment.py`
- Modify: `scripts/build_r4_artifacts.py`
- Modify: `scripts/diagnose_r4_cases.py`
- Modify: `tests/test_r4_case_diagnostics.py`

- [ ] **Step 1: Write the failing explicit-source test**

Replace the existing R3-source assertion with:

```python
def test_environment_factory_binds_explicit_generator_source(tmp_path: Path) -> None:
    environment = build_environment(
        ROOT,
        tmp_path,
        source_revision="1" * 40,
    )
    try:
        assert environment["source_revision"] == "1" * 40
    finally:
        environment["close"]()
```

Add a CLI test that invokes `scripts/build_r4_artifacts.py` without
`--source-revision` and asserts argparse exits nonzero with
`the following arguments are required: --source-revision`.
Register it under the existing `mutation-partition` R4 owner and add its exact
node to `r4_data_owner_tests` in Task 5.

- [ ] **Step 2: Run and verify the signature mismatch**

```powershell
python -m pytest tests/test_r4_environment.py -q -p no:cacheprovider
```

Expected: FAIL because `build_environment()` does not accept
`source_revision` and the CLI does not require it.

- [ ] **Step 3: Implement explicit provenance**

Change the environment signature to:

```python
def build_environment(
    project_root: Path,
    output_root: Path,
    *,
    source_revision: str,
) -> Mapping[str, object]:
```

Validate `source_revision` as exactly 40 lowercase hexadecimal characters and
return that value in the environment mapping. Keep
`admitted_source_for_phase()` because its independent ledger verification still
has tests and may have non-R4 callers; do not use it to label the new build.

In `build_r4_artifacts.py`, add:

```python
parser.add_argument("--source-revision", required=True)
environment = build_environment(
    ROOT,
    args.output.resolve(),
    source_revision=args.source_revision,
)
```

Update the documented plugin signature at the top of the script. The production
generator accepts only a repository-owned environment module and passes the
explicit revision; do not restore an implicit R3 fallback.

In `diagnose_r4_cases.py`, add a `--source-revision` option and wrap the selected
environment factory so its call is:

```python
environment_factory(
    root,
    stores,
    source_revision=args.source_revision,
)
```

Require this option whenever `--environment` is supplied. Add a parser/owner
test proving the diagnostic cannot load the R4 environment without an explicit
40-hex source revision. Register that test under the existing
`expected-contract` R4 owner and add its exact node to
`r4_contract_review_owner_tests` in Task 5.

Keep `diagnose_cases()` backward compatible for its default public-runtime
diagnostic path, but add a keyword-only `source_revision: str | None = None`.
When an environment factory is supplied, require the value and call that factory
with `source_revision=source_revision`; when no environment is supplied, reject
a non-`None` value as unused input. The CLI passes its parsed value into this
keyword.

- [ ] **Step 4: Run environment and generator tests**

```powershell
python -m pytest tests/test_r4_environment.py tests/test_r4_closeout_regressions.py -q -p no:cacheprovider
```

Expected: PASS after updating direct `build_environment()` test calls to supply
one explicit 40-hex revision.

### Task 5: Replace the validation step and delete the external-review subsystem

**Files:**
- Create: `tests/test_r4_validation_gate.py`
- Modify: `tests/test_r4_structure.py`
- Rename: `tests/test_r4_expansion_and_review.py` to `tests/test_r4_expansion.py`
- Modify: `scripts/validation_gate.py`
- Modify: `scripts/update_replay_status.py`
- Modify: `scripts/check_r3_r4_structure.py`
- Modify: `configs/validation_gates.json`
- Delete: `src/cemm_authoritative_hybrid/r4_review.py`
- Delete: `scripts/prepare_r4_review_request.py`
- Delete: `scripts/verify_r4_review_manifest.py`
- Delete: `schemas/corpus_review_manifest.schema.json`
- Delete: `data/review/R4_REVIEW_MANIFEST.template.json`

- [ ] **Step 1: Write failing validation-control tests**

Create `tests/test_r4_validation_gate.py`, load `scripts/validation_gate.py`
through the same reviewed-source pattern used by `test_validation_gate.py`, and
add:

```python
def test_r4_integrity_report_has_exact_internal_shape() -> None:
    material = {
        "schema": "cemm-r4-artifact-integrity-step-report-v1",
        "artifact_count": 401,
        "artifact_set_ref": content_ref("artifact_set", ["x"]),
        "build_receipt_ref": content_ref("build_receipt", {"x": 1}),
        "source_revision": "1" * 40,
        "authority_generation": "authority:test",
    }
    material["integrity_ref"] = content_ref("r4_artifact_integrity", material)
    validation_gate_module._validate_admission_step_report(
        "r4_artifact_integrity", material
    )


def test_r4_integrity_report_rejects_retired_review_fields() -> None:
    report = valid_r4_integrity_report()
    report["reviewer_ref"] = "reviewer:test"
    with pytest.raises(AdmissionValidationError):
        validation_gate_module._validate_admission_step_report(
            "r4_artifact_integrity", report
        )
```

Add a `_RunContext` handler test with a stubbed `verify_r4_admission` that records
its keyword arguments and assert it receives the exact artifact commit parent as
`expected_source_revision` plus `expected_authority_generation`, with no
environment lookup. Add failure cases for a merge commit and for any changed
path outside `artifacts/r4/`.

Register every function in this new module with literal R4 metadata using
`diagnostic_role="owner"` and `owner_ref="artifact-integrity"`; Task 6 refreshes
the temporary AST hashes.

In `test_r4_structure.py`, replace the anti-self-signing test with:

```python
def test_r4_external_review_subsystem_is_absent() -> None:
    forbidden = (
        SRC / "r4_review.py",
        ROOT / "scripts" / "prepare_r4_review_request.py",
        ROOT / "scripts" / "verify_r4_review_manifest.py",
        ROOT / "schemas" / "corpus_review_manifest.schema.json",
        ROOT / "data" / "review" / "R4_REVIEW_MANIFEST.template.json",
    )
    assert all(not path.exists() for path in forbidden)
```

- [ ] **Step 2: Run and verify legacy-step failures**

```powershell
python -m pytest tests/test_r4_validation_gate.py tests/test_r4_structure.py -q -p no:cacheprovider
```

Expected: new tests fail because `r4_artifact_review`, reviewer fields, and
external files still exist.

- [ ] **Step 3: Migrate the validation control plane**

In `validation_gate.py`, replace every step-kind/schema/handler occurrence:

```text
r4_artifact_review -> r4_artifact_integrity
cemm-r4-artifact-review-step-report-v1
  -> cemm-r4-artifact-integrity-step-report-v1
run_r4_artifact_review -> run_r4_artifact_integrity
```

The exact report fields are:

```python
{
    "schema", "artifact_count", "artifact_set_ref", "build_receipt_ref",
    "source_revision", "authority_generation", "integrity_ref",
}
```

The handler requires linked authority, authenticated governance, and an
effective green R3 predecessor. It calls:

```python
verify(
    self.root,
    expected_source_revision=self._r4_generator_source_revision(),
    expected_authority_generation=authority.generation,
)
```

`_r4_generator_source_revision()` resolves exactly one parent for
`self.source_ref`, requires that the current commit's complete changed-path set
is non-empty and contained by `artifacts/r4/`, and returns that 40-hex parent.
Thus the Build Receipt independently binds the source commit that generated it
while the validation receipt independently binds the current artifact commit.
Remove all `os.environ` review lookups and verifier parameters.

Update the admission-only topology and error text to require authority,
activation, and artifact integrity only. Remove
`data/review/R4_REVIEW_MANIFEST.json` from `_required_admission_evidence_paths()`
and from `_PHASE_ADMISSION_EVIDENCE_PATHS` in `update_replay_status.py`.

- [ ] **Step 4: Update config and exact owner selectors**

In `configs/validation_gates.json`:

```json
"R4": {
  "admission": ["governance", "pytest_active", "r4_artifact_integrity", "sqlite_activation"]
}
```

Define `r4_artifact_integrity` with dependencies `governance` and
`sqlite_activation`, inputs `artifacts/r4/`, `data/scenarios/use_cases.jsonl`,
and `src/cemm_authoritative_hybrid/`, and kind
`r4_artifact_integrity`. Rename owner `surface-review` to `surface-expansion`,
retain only the two expansion nodes, add the two Build Receipt ABI nodes to
`r4_phase_tests`, add the new environment/diagnostic CLI nodes to their existing
owners, and add a new `artifact-integrity` owner step selecting every test in
`test_r4_admission.py` and `test_r4_validation_gate.py`.

- [ ] **Step 5: Retire code and legacy tests**

Rename `test_r4_expansion_and_review.py` to `test_r4_expansion.py`, delete its
two signature tests, verifier helper, pytest import if unused, and signature
metadata. Delete the five external-review files listed above. Update
`check_r3_r4_structure.py` to fail if any deleted path exists or if
`r4_pipeline.py`, `r4_admission.py`, or `validation_gate.py` contains any of:

```python
(
    "CorpusReviewManifest", "ApprovedR4Build", "CEMM_R4_REVIEW",
    "R4_REVIEW_MANIFEST", "external_review_required",
)
```

This is an absence test for a retired subsystem, not a compatibility shim.

- [ ] **Step 6: Run focused structural and control-plane tests**

```powershell
python -m pytest tests/test_r4_expansion.py tests/test_r4_structure.py tests/test_r4_validation_gate.py -q -p no:cacheprovider
python scripts/check_r3_r4_structure.py
```

Expected: PASS; no active path imports, reads, or configures the retired review
subsystem.

### Task 6: Update active authority, ABI documentation, and living test metadata

**Files:**
- Modify: `docs/ABI_REGISTRY.md`
- Modify: `docs/DOCUMENT_AUTHORITY.json`
- Modify: `docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md`
- Modify: `docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md`
- Modify: `docs/superpowers/plans/2026-08-05-hybrid-mvp-r3-r4-implementation-plan.md`
- Modify: `docs/superpowers/specs/2026-08-12-r4-final-admission-closeout-design.md`
- Modify: `docs/superpowers/plans/2026-08-12-r4-final-admission-closeout-plan.md`
- Modify: R3/R4 test modules changed in Tasks 2-5
- Modify: `artifacts/validation/TEST_INVENTORY_RECEIPT.json`
- Verify unchanged unless necessary: `governance/test_inventory.json`

- [ ] **Step 1: Update the ABI registry and supersession markers**

Replace the active rows for Corpus Review Manifest ABI 2, Approved R4 Build ABI
1, and Build Receipt ABI 2 with:

```markdown
| R4 Build Receipt ABI | **3** | `src/cemm_authoritative_hybrid/r4_pipeline.py` | Serialized admission-candidate evidence | `R4BuildReceipt.from_dict` + `verify_r4_admission` | Reconstructs every committed R4 artifact hash, binds exact generator source and authority generation, and remains `admission_state=candidate` until the governed admission receipt and replay ledger admit it. |
```

Add a retirement note stating the manifest and approval ABIs have no active
decoder or compatibility path. At the top of the former closeout spec and plan,
add an explicit `Superseded by` link to the new design/plan without rewriting
their historical contents.

Add a scoped notice to the 2026-07-31 admission design, 2026-07-31 master plan,
and 2026-08-05 R3/R4 plan stating that only their R4 external-review and signed-
manifest requirements are superseded. Their non-R4 governance, admission, and
implementation history remains authoritative where it does not conflict with
the new R4 contract.

- [ ] **Step 2: Update document authority**

In `DOCUMENT_AUTHORITY.json`, add the new approved design and this plan to
`governing_documents`. Move only the fully R4-specific 2026-08-12 external-
review design and plan from `governing_documents` to
`superseded_execution_claims`. Keep the three broader documents governing after
their scoped notices. Preserve all other entries and canonical formatting.

- [ ] **Step 3: Refresh literal R3/R4 AST hashes**

```powershell
python scripts/refresh_r3_r4_test_metadata.py
python scripts/verify_r3_r4_test_metadata.py
```

Expected: the placeholder hashes and all changed R4 function hashes are replaced
with their exact canonical AST digests; verification passes.

- [ ] **Step 4: Reconstruct the living inventory receipt**

Use the same canonical reconstruction owner as the prior R1 retirement:

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
    inventory_sha256=inventory_sha,
    inventory=inventory,
    selector=selector,
)
(root / "artifacts" / "validation" / "TEST_INVENTORY_RECEIPT.json").write_bytes(
    gate.canonical_json_bytes(receipt)
)
'@ | python -
```

The immutable predecessor inventory currently contains none of the R4 modules
being renamed or edited, so `governance/test_inventory.json` and its SHA-256 pin
must remain byte-unchanged. If verification contradicts that inspected fact,
stop rather than inventing an inventory migration.

- [ ] **Step 5: Verify every closed-phase inventory**

```powershell
foreach ($phase in 'G0','R1','R2','R3','R4') {
    python scripts/check_test_inventory.py --phase $phase --source-only
    if ($LASTEXITCODE -ne 0) { throw "inventory failed for $phase" }
}
```

Expected: all phases pass; signature-only nodes are absent, and every replacement
artifact-integrity node is active in R4.

- [ ] **Step 6: Commit the source/authority migration**

```powershell
git add -- src scripts tests configs schemas data/review docs artifacts/validation/TEST_INVENTORY_RECEIPT.json governance/test_inventory.json
git diff --cached --check
git diff --cached --stat
git commit -m "refactor(r4): replace external review with artifact admission"
```

Expected: one focused migration commit. Confirm the commit contains no
`artifacts/r4/**`, replay-ledger update, or unrelated workspace file.

### Task 7: Generate and commit the complete ABI 3 artifact graph

**Files:**
- Modify: `artifacts/r4/**`
- Test: `tests/test_r4_admission.py`
- Test: `tests/test_r4_authentic_episodes.py`

- [ ] **Step 1: Record the exact generator source commit**

```powershell
$generatorSource = (git rev-parse --verify HEAD^{commit}).Trim()
if ($generatorSource -notmatch '^[0-9a-f]{40}$') { throw "invalid generator source" }
```

Expected: `$generatorSource` is the Task 6 migration commit. This value is the
Build Receipt's `source_revision`.

- [ ] **Step 2: Generate two independent candidate trees**

```powershell
$buildA = Join-Path $env:TEMP ("cemm-r4-repository-admission-a-" + [guid]::NewGuid().ToString('N'))
$buildB = Join-Path $env:TEMP ("cemm-r4-repository-admission-b-" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $buildA,$buildB | Out-Null
python scripts/build_r4_artifacts.py --environment src/cemm_authoritative_hybrid/r4_environment.py --source-revision $generatorSource --output $buildA
if ($LASTEXITCODE -ne 0) { throw "first R4 build failed" }
python scripts/build_r4_artifacts.py --environment src/cemm_authoritative_hybrid/r4_environment.py --source-revision $generatorSource --output $buildB
if ($LASTEXITCODE -ne 0) { throw "second R4 build failed" }
```

Expected: both commands print the same ABI 3 `receipt_ref` and complete with no
review environment.

- [ ] **Step 3: Prove exact byte identity**

```powershell
$filesA = Get-ChildItem -LiteralPath $buildA -Recurse -File | ForEach-Object {
    [pscustomobject]@{ Path=$_.FullName.Substring($buildA.Length).TrimStart('\'); Length=$_.Length; Hash=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
}
$filesB = Get-ChildItem -LiteralPath $buildB -Recurse -File | ForEach-Object {
    [pscustomobject]@{ Path=$_.FullName.Substring($buildB.Length).TrimStart('\'); Length=$_.Length; Hash=(Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash }
}
if ((Compare-Object ($filesA | Sort-Object Path) ($filesB | Sort-Object Path) -Property Path,Length,Hash)) {
    throw "R4 generation is not byte deterministic"
}
```

Expected: no differences.

- [ ] **Step 4: Copy only verified candidate files into `artifacts/r4`**

Resolve every destination under the explicit worktree
`hybrid_mvp/artifacts/r4` directory. Use `Copy-Item -LiteralPath` per verified
relative path, create missing partition directories with `New-Item`, and reject
any destination that resolves outside `artifacts/r4`. Remove no path unless it
is a tracked obsolete artifact explicitly absent from both candidate trees.

Expected: `git status --short -- artifacts/r4` lists only deterministic ABI 3
artifact changes.

- [ ] **Step 5: Run exact artifact tests and the 400-case diagnostic**

```powershell
python -m pytest tests/test_r4_admission.py tests/test_r4_authentic_episodes.py tests/test_r4_mutations_and_partitions.py tests/test_r4_sufficiency.py -q -p no:cacheprovider
python scripts/diagnose_r4_cases.py --environment cemm_authoritative_hybrid.r4_environment:build_environment --source-revision $generatorSource --store-root "$env:TEMP\cemm-r4-repository-admission-diagnostic" --output "$env:TEMP\cemm-r4-repository-admission-diagnostic.json"
```

Expected: tests pass and the diagnostic reports exactly 400 passed, 0 failed,
0 errors.

- [ ] **Step 6: Commit generated artifacts**

```powershell
git add -- artifacts/r4
git diff --cached --check
git commit -m "data(r4): regenerate repository-admitted corpus"
```

Expected: one generated-data commit whose only changed paths are under
`artifacts/r4/` and whose Build Receipt points to its exact parent generator
source commit. The later admission receipt binds this complete artifact commit.

### Task 8: Run complete pre-admission verification

**Files:**
- No source changes expected

- [ ] **Step 1: Run source, structure, and metadata gates**

```powershell
python -m compileall -q src scripts
python scripts/verify_r3_r4_test_metadata.py
python scripts/check_r3_r4_structure.py
python scripts/audit_r3_r4_legacy_tests.py --strict --output "$env:TEMP\R3_R4_LEGACY_AUDIT.json"
```

Expected: all commands pass and the audit does not require preservation of
retired signature-only tests.

- [ ] **Step 2: Run every R4 owner and phase gate**

```powershell
python scripts/validate_mvp.py --tier owner --phase R4 --owner expected-contract
python scripts/validate_mvp.py --tier owner --phase R4 --owner mutation-partition
python scripts/validate_mvp.py --tier owner --phase R4 --owner structural-sufficiency
python scripts/validate_mvp.py --tier owner --phase R4 --owner surface-expansion
python scripts/validate_mvp.py --tier owner --phase R4 --owner artifact-integrity
python scripts/validate_mvp.py --tier phase --phase R4
```

Expected: all six commands pass.

- [ ] **Step 3: Run the full repository suite**

```powershell
python -m pytest -q -p no:cacheprovider
```

Expected: all active tests pass with no external-review compatibility tests or
fallback behavior.

- [ ] **Step 4: Verify all prerequisite phases and the current chain**

```powershell
foreach ($phase in 'G0','R1','R2','R3','R4') {
    python scripts/validate_mvp.py --tier phase --phase $phase
    if ($LASTEXITCODE -ne 0) { throw "phase gate failed for $phase" }
}
python scripts/update_replay_status.py --verify-chain
```

Expected: all phase gates pass; the effective ledger is still R4 red before
admission.

- [ ] **Step 5: Verify a clean committed source snapshot**

```powershell
git diff --check
git status --short --branch
```

Expected: no tracked or untracked changes in the isolated worktree.

### Task 9: Admit R4 green through ordinary governed admission

**Files:**
- Create: `artifacts/validation/runs/<run-ref>.json`
- Modify: `governance/replay_status.jsonl`

- [ ] **Step 1: Run clean R4 admission without review environment**

```powershell
Remove-Item Env:CEMM_R4_REVIEW_VERIFIER -ErrorAction SilentlyContinue
Remove-Item Env:CEMM_R4_REVIEW_VERIFIER_SHA256 -ErrorAction SilentlyContinue
python scripts/validate_mvp.py --tier admission --phase R4 | Tee-Object -FilePath "$env:TEMP\r4-repository-admission-outcome.json"
```

Expected: `disposition="passed"`, with a fresh `run_ref`, `gate_result_ref`, and
receipt path under `artifacts/validation/runs/`. The R4 step report schema is
`cemm-r4-artifact-integrity-step-report-v1` and contains no review fields.

- [ ] **Step 2: Dry-run the exact green transition**

```powershell
$admission = Get-Content -Raw "$env:TEMP\r4-repository-admission-outcome.json" | ConvertFrom-Json
$ledgerHead = (Get-Content governance/replay_status.jsonl | Select-Object -Last 1 | ConvertFrom-Json).record_ref
python scripts/update_replay_status.py --phase R4 --status green --run-ref $admission.run_ref --expect-record-ref $ledgerHead --dry-run
```

Expected: one canonical proposed R4 green record bound to the passed admission
receipt and effective green R3 predecessor.

- [ ] **Step 3: Append and verify the complete chain**

```powershell
python scripts/update_replay_status.py --phase R4 --status green --run-ref $admission.run_ref --expect-record-ref $ledgerHead --append
python scripts/update_replay_status.py --verify-chain
```

Expected:

```text
G0=green R1=green R2=green R3=green R4=green R5=red R6=red R7=red R8=red
```

- [ ] **Step 4: Commit exact admission evidence**

```powershell
git add -- governance/replay_status.jsonl artifacts/validation/runs
git diff --cached --check
git commit -m "admit(r4): close repository-owned data phase"
```

Expected: the commit includes the one new content-addressed admission receipt
and one append-only ledger record only.

### Task 10: Verify, merge to main, and close R4

**Files:**
- No source changes expected

- [ ] **Step 1: Run final branch verification**

```powershell
python -m pytest -q -p no:cacheprovider
python scripts/validate_mvp.py --tier phase --phase R4
python scripts/update_replay_status.py --verify-chain
git status --short --branch
```

Expected: all tests pass, R4 phase passes, the ledger reports R4 green, and the
worktree is clean.

- [ ] **Step 2: Merge the reviewed branch into primary `main`**

From `C:\dev\cemm`:

```powershell
git switch main
git merge --ff-only codex/r4-repository-owned-admission
```

Expected: fast-forward merge succeeds. Preserve all pre-existing untracked files
in the primary workspace; none is staged or modified.

- [ ] **Step 3: Verify the merged main state**

```powershell
Set-Location C:\dev\cemm\hybrid_mvp
python scripts/validate_mvp.py --tier phase --phase R4
python scripts/update_replay_status.py --verify-chain
git status --short --branch
```

Expected: R4 remains green on `main`; tracked state is clean; only the user's
pre-existing unrelated untracked files remain.

- [ ] **Step 4: Remove the completed worktree and branch**

After resolving and verifying the exact worktree path:

```powershell
git worktree remove C:\dev\cemm\.worktrees\r4-repository-owned-admission
git branch -d codex/r4-repository-owned-admission
```

Expected: only the completed isolated worktree and its merged local branch are
removed. No repository data or user workspace file is deleted.
