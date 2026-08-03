# Hybrid MVP G0-R1 Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use `subagent-driven-development` task-by-task. Every implementation task uses `test-driven-development`, then contract review, code-quality/performance review, and controller verification.

**Goal:** Admit G0 and R1: truthful executable governance, inherited-claim quarantine, one dependency-aware validator, and a hard cut from duplicate runtime ABIs/paths to canonical content-addressed R1 boundaries.

**Architecture:** Governance is append-only evidence outside semantic authority. Validation is one external DAG runner with three coalesced tiers. Under the 2026-08-02 amendment, R1 owns Program ABI 2, Semantic Expression ABI 1, the total compiler, Verified Meaning ABI 1, immutable identities in their earliest modules, one candidate-batch/verifier boundary, one final `CycleResult`, and `HybridRuntime.process()` as the only public path. Later-owner R2/R3 behavior remains an explicit typed gap rather than evaluating a raw program.

**Tech Stack:** Python 3.11+, pytest, PyTorch, JSON/JSONL, SHA-256 refs, SQLite activation checks.

**Worktree:** `C:\dev\cemm\.worktrees\hybrid-mvp-g0-r1` on `codex/hybrid-mvp-g0-r1`.

**Design:** `hybrid_mvp/docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md`.

**Command roots:** Run Python/pytest/script commands from `hybrid_mvp/`. Run `git add` and `git commit` commands from the worktree root so their `hybrid_mvp/` paths resolve exactly.

---

## Execution rules

- Never run/copy either donor installer or overlay.
- Do not modify root-runtime code/authority or relabel/move/delete inherited artifacts.
- Do not weaken release expectations, convert programming errors into gaps, or retain adapters, signature inspection, fixture release owners, or alternate composition roots.
- Red/green loops run only the focused owner tier. Run one coalesced phase tier only when reviewed work changes a declared cross-owner boundary and has integration nodes. Run one fresh admission tier per phase candidate.
- Owner and phase selectors are disjoint after expansion to exact collected node IDs. Admission performs one full governed collection, deselects inactive nodes, executes the active set once fresh and never nests owner or phase test steps.
- Test governance uses immutable `governance/test_inventory.json` for the frozen 59-file/632-source/743-case predecessor set. Every later test carries literal per-node `__cemm_test_inventory__` metadata in its own module. The AST checker parses each module once. No secondary mutable registry exists; test-inventory routine/bundle verification neither infers metadata from filenames/defaults nor queries live Git.
- G0/R1 never run corpus generation, training, or reproduction.
- Validation/performance code is not imported by the normal runtime path. Governance, status and receipt-loader tools remain lightweight and do not import runtime/model/training libraries.
- Once a post-anchor status row is appended, preserve every referenced `source_base` through fast-forward or a merge commit; do not rebase, squash, cherry-pick-only integrate or force-push away that history.
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
    effective_replay_status, load_ledger_anchor, read_hash_chain,
    verify_file_invalidation,
)


def test_initial_replay_status_is_truthful() -> None:
    path = ROOT / "governance/replay_status.jsonl"
    records = read_hash_chain(path)
    anchor = load_ledger_anchor(path)
    assert effective_replay_status(records[:anchor.initial_count]) == {
        "G0": "pending", "R1": "red", "R2": "red", "R3": "red",
        "R4": "red", "R5": "red", "R6": "red", "R7": "red", "R8": "red",
    }


def test_invalidations_bind_unchanged_historical_files() -> None:
    path = ROOT / "governance/receipt_invalidations.jsonl"
    all_records = read_hash_chain(path)
    anchor = load_ledger_anchor(path)
    records = all_records[:anchor.initial_count]
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


def read_hash_chain(path: Path) -> tuple[dict[str, object], ...]:
    raw = path.read_bytes()
    anchor = load_ledger_anchor(path)  # verifies the DOCUMENT_AUTHORITY pin
    records = _verify_anchored_bytes(raw, anchor)
    root = _find_git_root(path.resolve().parent)
    prefixes = _prefix_witnesses(raw, records, anchor)
    _head_ref, committed_blobs = _load_git_witnesses(
        root, path, anchor.source_base, prefixes
    )
    for witness in prefixes:
        committed = committed_blobs.get(witness.revision)
        if (
            committed is None
            or len(committed) != witness.expected_size
            or committed != raw[:witness.expected_size]
        ):
            raise GovernanceError(
                "source_base does not bind its exact committed prefix"
            )
    return records
```

`parse_and_validate_records` performs the exact sequence, predecessor, schema,
type and content-ref checks shown by Task 2's RED tests. Status records bind both
`admission_gate_result_ref` and the exact fresh `admission_run_ref`; both are
null for initial red/pending records. Green and `externally_blocked` transitions
both reconstruct one passed admission with `expected_status="passed"` before
binding those refs. The updater never forwards the ledger values `green` or
`externally_blocked` as a receipt-status expectation. `ledger_anchors.json`
pins each ledger's genesis, initial head, initial byte length/hash and initial
count; DOCUMENT_AUTHORITY pins
that anchor file by exact SHA-256. Tests of the truthful initial state inspect
only the governed anchored prefix so later appends do not invalidate them.

For every later append, load the ledger bytes from the record's `source_base`
Git commit and require them to equal the bytes before that record, not merely be
a prefix of the current file. Each source base must be a commit, a monotonic
ancestor of the next source base and an ancestor of current HEAD.
`_prefix_witnesses` derives each revision and exact expected prefix size in
memory from the already bounded ledger. For any nonempty post-anchor suffix,
`_load_git_witnesses` uses exactly three Git subprocesses, independent of row
count:

1. one bounded combined `cat-file --batch-check` over HEAD, every source
   revision and every `<revision>:<ledger-path>` expression, validating commit
   types plus each blob OID, type and exact expected size before loading bytes;
2. one bounded `rev-list --parents --topo-order --ancestry-path` commit DAG,
   followed by local monotonic-ancestry verification; and
3. one bounded `cat-file --batch` that receives only the already checked blob
   OIDs and loads exactly their checked sizes.

There is no per-record Git subprocess. Ledger bytes and records are capped by
`MAX_LEDGER_BYTES` and `MAX_LEDGER_RECORDS`; metadata, commit-graph bytes and
commit-graph records are capped by `MAX_GIT_METADATA_BYTES`,
`MAX_COMMIT_GRAPH_BYTES` and `MAX_COMMIT_GRAPH_RECORDS`; and the aggregate blob
load is bounded from the checked sizes. Extra, oversized or truncated Git output
fails closed.
`read_hash_chain(path)` always discovers and verifies that Git witness itself;
it has no public prior-bytes, prior-head-receipt or callback bypass. If Git is
unavailable for a post-anchor suffix, verification fails closed. A future
Git-less release bundle may define a separately reviewed, manifest-pinned,
verify-only path, but that path is not accepted by `read_hash_chain` and is not
current admission authority.

Populate `G0=pending` and `R1-R8=red` plus the six exact invalidations. Preserve
historical files byte-for-byte. Add tests for changed fields, broken predecessor,
missing/extra fields, truncation, ancestor changes invalidating descendants,
`externally_blocked`, passed-receipt enforcement for both green and
`externally_blocked`, Git-unavailable suffix verification, and a fully rehashed
rewrite that does not preserve the prior committed prefix. A status update
validates existing receipts only and never launches a validation tier.

### Step 3: Verify, review, commit

```powershell
python -m pytest tests\test_replay_governance.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-g0-ledgers
git add hybrid_mvp/src/cemm_authoritative_hybrid/governance.py hybrid_mvp/governance hybrid_mvp/scripts/update_replay_status.py hybrid_mvp/docs/DOCUMENT_AUTHORITY.json hybrid_mvp/tests/test_replay_governance.py
git commit -m "governance: invalidate inherited claims append-only"
```


## Task 3: Freeze predecessor cases and require literal metadata for later tests

**Files:**

- Create: `hybrid_mvp/governance/test_inventory.json`
- Create: `hybrid_mvp/scripts/test_inventory_core.py`
- Create: `hybrid_mvp/scripts/check_test_inventory.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/governance.py`
- Modify: `hybrid_mvp/docs/DOCUMENT_AUTHORITY.json`
- Create: `hybrid_mvp/tests/test_test_inventory.py`
- Modify: `hybrid_mvp/tests/test_replay_governance.py`
- Modify: `hybrid_mvp/pyproject.toml` to pin pytest collection
- Generate in Task 5: `hybrid_mvp/artifacts/validation/TEST_INVENTORY_RECEIPT.json`

### Step 1: Add failing immutable-inventory tests

`governance/test_inventory.json` is the only predecessor inventory. Build it
from the reviewed baseline audit and then make it immutable. It freezes exactly
59 test files, 632 source-test refs and 743 exact collected-case node IDs,
including every parameterized case. The completed manual contract audit yields
609 retained, 10 rewritten and 13 historical source tests. Those are reviewed
results, not quotas to satisfy by relabelling. The artifact binds each file's
reviewed baseline blob ref and every source test's canonical AST digest,
assertion, classification, activation and recomputable inventory identity.

The AST audit also finds two functions named `test_authority_factory`; both
are `@pytest.fixture` providers and collect no cases, so they are not source
tests. The checker excludes only statically resolved `pytest`/`pytest_asyncio`
fixture providers, rejects fixture-identity rebinding and callable test aliases,
and requires the remaining 632 source refs to own all 743 exact cases without
importing pytest. `pyproject.toml` pins collection to `test_*.py|*_test.py`,
`test*` functions and `Test*` classes; the checker verifies that contract.
The frozen artifact has this structural shape:

```json
{
  "schema": "cemm-hybrid-test-inventory-v1",
  "inventory_ref": "test_inventory:<content-ref>",
  "baseline_source_ref": "58345240e67bf003e6ac7d5c68752e2e5eee4a7d",
  "file_count": 59,
  "source_test_count": 632,
  "case_count": 743,
  "classification_counts": {
    "retained": 609,
    "rewritten": 10,
    "historical": 13
  },
  "files": [
    {
      "path": "tests/test_program_abi.py",
      "baseline_blob_ref": "sha256:<digest>"
    }
  ],
  "source_tests": [
    {
      "source_test_ref": "tests/test_program_abi.py::test_program_uses_only_five_persistent_operators",
      "classification": "retained",
      "activation_phase": "R1",
      "assertion_ref": "assertion:program-abi",
      "source_ast_sha256": "<digest>",
      "case_node_ids": [
        "tests/test_program_abi.py::test_program_uses_only_five_persistent_operators"
      ],
      "successor_node_ids": []
    }
  ]
}
```

The full artifact, not this abbreviated example, contains all 59/632/743
records. `DOCUMENT_AUTHORITY.json` pins its exact path and SHA-256. Verify that
authority pin first, then recompute `inventory_ref` over every field except
itself; require exact counts, unique normalized repository-relative
file/source/case refs, every case owned by exactly one source test, a non-empty
assertion ref and exact classification totals. A retained test declares its
earliest activation phase. A rewritten test declares a content-addressed
rewrite obligation, replacement phase and complete predecessor-case mapping to
exact existing or reserved successor node IDs. A historical record declares a
reviewed reason and no activation. There is no `future` classification.

The full-file baseline hash is provenance only. The canonical digest of each
source test's decorators, literal parameter IDs, signature and body is the
mutation boundary. Adding unrelated imports/helpers/metadata/tests is legal;
changing a frozen body under the same node ID fails. A retained assertion may
move only to a new exact node ID through unique, acyclic,
assertion-preserving, phase-monotonic literal supersession metadata.

Every test node introduced after the frozen set is self-describing. Its module
contains one literal mapping named `__cemm_test_inventory__`:

```python
__cemm_test_inventory__ = {
    "tests/test_replay_governance.py::test_initial_replay_status_is_truthful": {
        "assertion_ref": "assertion:truthful-replay-status",
        "activation_phase": "G0",
        "diagnostic_role": "owner",
        "owner_ref": "governance",
        "introduced_by_task": "G0-Task-2",
    },
}
```

Keys are exact pytest node IDs. A parameterized later test has one literal entry
for every exact case node ID, one literal argvalue sequence and a
same-cardinality list of unique safe-ASCII `ids=` values so the AST checker can
derive those IDs without pytest collection. Dynamic/generated parameter IDs
are forbidden. `diagnostic_role` is exactly
`owner|phase|admission_only`; `owner_ref` is required only for `owner`.
A retained replacement record uses literal supersedes_node_id and exactly the
same assertion ref. A node participating in a conjunctive rewrite set uses a
literal contributes_to_rewrite_refs field; the reviewed obligation set, not any
one partial member, is the assertion-preservation authority.
Every predecessor parameter case occurs in exactly one obligation mapping. That
mapping contains a non-empty conjunctive required_successor_node_ids set: once
due, every member must exist, be active and resolve through any retained
supersession chain to one executable leaf. Multiple predecessors may share a
successor. A later successor's literal contribution refs must name each reviewed
obligation; for a frozen retained successor, membership in each immutable reviewed obligation is itself the
contribution declaration because frozen nodes cannot carry later metadata.
Metadata values and keys must be AST literals. Computed dictionaries, decorators
that infer governance, file-level defaults, filename conventions and imported
metadata are forbidden.

`scripts/test_inventory_core.py` is stdlib-only and is loaded by reviewed exact
file path; importing it must not execute `cemm_authoritative_hybrid.__init__`
or load runtime, model, training or Torch. `check_test_inventory.py` is a thin
CLI over that owner. Source-only verification requires an explicit phase,
parses `test_inventory.json` and every current test module exactly once with
`ast`, and invokes neither Git nor pytest. It returns the phase-active union and
the complete currently collectable governed set; the latter includes present
rewritten/historical originals for Task 4's collect-but-never-execute check. It
rejects a bad inventory identity/count, a later test lacking literal per-node
metadata, metadata for a frozen or nonexistent node, duplicate node ownership,
unsafe paths and an unrecognized field/value. The one-time Task 3 review
compares the frozen file to the supplied baseline audit before commit. Routine
and release-bundle verification thereafter recompute the immutable file and AST
metadata directly and never require a live Git checkout.

A rewritten original is evidence-only and never executable. Its replacement
obligation is computed as deferred before `replacement_phase`; at or after that
phase every exact predecessor case must have a valid successor or verification
fails before pytest. Historical nodes never execute. Deferred is not a fourth
classification. Owner and phase execution each use exactly one pytest process
for their exact selected leaf nodes. Admission uses one process to collect the
complete governed current set, deselect inactive nodes and execute the eligible
leaf union.

Mandatory focused tests prove: exact 59/632/743 and 609/10/13 totals; G0
succeeds with all ten rewrite obligations deferred; a due missing successor
fails before pytest; rewritten and historical originals never enter a selector;
duplicate/unknown/wrong-assertion/phase-regressing/cyclic/incomplete mappings
fail; same-ID mutation fails while unrelated additions pass; a valid new-ID
supersession leaves exactly one executable lineage leaf; and source-only
instrumentation observes one AST parse per module, zero Git/pytest calls and no
runtime/model/training/Torch imports.

Run and observe RED:

```powershell
python -m pytest tests\test_test_inventory.py tests\test_replay_governance.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-g0-inventory
```

### Step 2: Curate the complete frozen set and annotate current later tests

Curate all and only the frozen 59 files, 632 source tests and 743 exact cases by
earliest truthful activation:

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
- `rewritten` only when exact successor obligations preserve every quantified
  part of the assertion.
- `historical` only when the assertion itself depended on a retired path.

The reviewed classification is 609 retained / 10 rewritten / 13 historical.
Each rewritten predecessor case owns one conjunctive required successor set.
All listed members are required once the obligation is due; an existing retained
successor is followed to its current supersession leaf.

1. tests/test_bootstrap_episode_generation.py::test_episodes_file_exists
   (R4) requires
   tests/test_semantic_episode.py::test_generated_episodes_match_committed_file.
2. tests/test_bootstrap_episode_generation.py::test_each_episode_has_required_fields
   (R4) requires
   tests/test_semantic_episode.py::test_episode_contains_every_phase_and_revision,
   tests/test_semantic_episode.py::test_generated_episodes_match_committed_file,
   and tests/test_r4_authentic_episodes.py::test_every_emitted_episode_contains_complete_six_phase_artifacts.
3. tests/test_bootstrap_episode_generation.py::test_accepted_episodes_have_coverage_receipt
   (R4) requires
   tests/test_semantic_episode.py::test_episode_contains_every_phase_and_revision,
   tests/test_semantic_episode.py::test_generated_episodes_match_committed_file,
   and tests/test_r4_authentic_episodes.py::test_every_accepted_episode_binds_coverage_program_and_action_identity.
4. tests/test_bootstrap_episode_generation.py::test_episodes_have_authority_hash
   (R4) requires
   tests/test_semantic_episode.py::test_episode_contains_every_phase_and_revision,
   tests/test_semantic_episode.py::test_generated_episodes_match_committed_file,
   and tests/test_r4_authentic_episodes.py::test_every_episode_binds_exact_authority_and_revision_identity.
5. tests/test_bootstrap_episode_generation.py::test_two_runs_produce_identical_output
   (R4) requires
   tests/test_semantic_episode.py::test_episode_generation_is_byte_deterministic.
6. tests/test_bootstrap_episode_generation.py::test_generated_output_matches_committed_file
   (R4) requires
   tests/test_semantic_episode.py::test_generated_episodes_match_committed_file.
7. tests/test_bootstrap_proposer.py::test_release_only_raises
   (R5) requires
   tests/test_neural_proposer.py::test_release_runtime_requires_neural_switch_proposer,
   tests/test_neural_weight_use.py::test_release_path_does_not_delegate_to_bootstrap,
   and tests/test_r5_public_runtime_selection.py::test_selected_release_runtime_never_invokes_bootstrap_proposer.
8. tests/test_bootstrap_proposer.py::test_typed_gap_surface_produces_candidates
   (R2) requires
   tests/test_grounding.py::test_unknown_surface_is_typed_not_manufactured,
   tests/test_grounding.py::test_unknown_surface_produces_reference_requirement,
   and tests/test_r2_unknown_frontier.py::test_unknown_surface_abstains_or_emits_typed_unresolved_candidate.
9. tests/test_cognitive_loop_e2e.py::TestSimulation::test_simulation_does_not_commit
   (R3) requires
   tests/test_transition_simulation.py::TestSimulatedTransitionDoesNotCommit::test_preview_does_not_mutate_revision,
   tests/test_transition_simulation.py::TestSimulatedTransitionDoesNotCommit::test_preview_sequence_does_not_mutate_revision,
   and tests/test_r3_public_cycle.py::test_simulate_cycle_emits_no_effect_and_preserves_world_revision.
10. tests/test_cognitive_loop_e2e.py::TestUnknownSurface::test_unknown_surface_produces_cycle
    (R3) requires
    tests/test_grounding.py::test_unknown_surface_is_typed_not_manufactured,
    tests/test_coverage.py::test_critical_residual_rejects_execution,
    and tests/test_r3_public_cycle.py::test_unknown_surface_returns_typed_frontier_without_acceptance_or_mutation.

These exact sets replace the earlier incomplete one-successor mappings.
Rewrite obligations are deferred before
their listed phase and hard-fail before pytest once due.

The thirteen historical source tests are exactly:

- `tests/test_bootstrap_episode_generation.py::{test_episodes_file_is_valid_jsonl,test_episodes_cover_all_seed_categories}`;
- `tests/test_cognitive_loop_e2e.py::TestCycleResultArtifacts::test_cycle_result_kernel_view`;
- `tests/test_phase_receipts.py::test_cycle_result_is_kernel_cycle_result_or_wraps_it`;
- `tests/test_scenario_coverage.py::{test_scenarios_file_is_valid_jsonl,test_210_unique_reviewed_cases}`;
- `tests/test_semantic_episode.py::{test_scenario_source_has_210_unique_reviewed_cases,test_generated_episodes_count_matches_scenarios}`;
- `tests/test_calibration.py::test_calibration_uses_validation_only`;
- `tests/test_evaluation_metrics.py::test_evaluator_loads_test_episodes`;
- `tests/test_cognitive_loop_e2e.py::TestNoHiddenFallback::test_implementation_error_is_not_clarification`;
- `tests/test_gap_receipts.py::test_unknown_exception_is_implementation_gap`;
- `tests/test_neural_realizer_weight_use.py::TestNeuralRealizerWeightUse::test_with_zeroed_weights_preserves_model_identity`.

These retire, respectively, compatibility result views, fixed 210/78 corpus
counts, one-scenario/one-episode generation, calibration-on-selection data,
swallowed programming errors and same identity for changed weights. Valid JSONL,
manifest-bound set size, exception propagation and derived ablation identity
receive new assertions; they do not inherit the retired assertions.

`tests/test_release_thresholds.py` remains retained with
`activation_phase=R7` and its known-red result is preserved. Do not edit
`test_inventory.json` after this review. Add literal metadata for every test
introduced by Tasks 1-3 to the module that owns it. Every later implementation
task adds literal metadata in the same source change as each new node.

The checker emits an in-memory exact-node index from the immutable inventory and
literal AST metadata. Owner and phase selectors use exact node IDs from that
index and are disjoint. Admission sends the pinned test root plus exact
collectable-node and active-node manifests to one fresh pytest process. The
plugin compares the full collection, deselects governed inactive nodes and then
executes the active union in the same invocation.

`TEST_INVENTORY_RECEIPT.json` binds the document-authority pin, immutable
`inventory_ref`, aggregate content ref of all literal
`__cemm_test_inventory__` mappings, exact collectable-node-set ref and exact
active-node-set ref. This proof is part of the existing coalesced
governance/admission DAG, not a fourth tier or another pytest process.

### Step 3: Verify, review, commit

```powershell
python scripts\check_test_inventory.py --phase G0 --source-only
python -m pytest tests\test_test_inventory.py tests\test_replay_governance.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-g0-inventory
git add hybrid_mvp/governance/test_inventory.json hybrid_mvp/scripts/test_inventory_core.py hybrid_mvp/scripts/check_test_inventory.py hybrid_mvp/src/cemm_authoritative_hybrid/governance.py hybrid_mvp/docs/DOCUMENT_AUTHORITY.json hybrid_mvp/tests/test_test_inventory.py hybrid_mvp/tests/test_replay_governance.py
git commit -m "governance: freeze predecessor tests and require literal metadata"
```


## Task 4: Replace the profile-label validator with one structured DAG runner

**Files:**

- Create: `hybrid_mvp/scripts/validation_gate.py`
- Create: `hybrid_mvp/scripts/pytest_gate_runner.py`
- Rewrite: `hybrid_mvp/scripts/validate_mvp.py`
- Modify: `hybrid_mvp/scripts/update_replay_status.py`
- Create: `hybrid_mvp/configs/validation_gates.json`
- Create: `hybrid_mvp/tests/test_validation_gate.py`
- Create: `hybrid_mvp/tests/test_g0_integration.py`
- Modify: `hybrid_mvp/tests/test_replay_governance.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/__init__.py` to preserve
  public exports through lazy loading
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


def test_collection_error_is_structured_without_nested_pytest() -> None:
    plugin = StructuredReportPlugin.for_unit_test()
    plugin.pytest_collectreport(
        FakeCollectReport(nodeid="tests/test_broken.py", outcome="failed")
    )
    payload = plugin.finalize(exitstatus=2)
    assert payload["counts"]["error"] == 1
    assert payload["disposition"] == "error"
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


def test_owner_and_phase_nodes_are_disjoint(project_root: Path) -> None:
    graph = load_gate_graph(project_root / "configs/validation_gates.json")
    owner = set(graph.resolve_pytest_nodes("G0", "owner"))
    phase = set(graph.resolve_pytest_nodes("G0", "phase"))
    assert owner.isdisjoint(phase)


def test_every_raw_file_selector_is_rejected(raw_file_graph) -> None:
    with pytest.raises(GateConfigError, match="exact node selectors required"):
        raw_file_graph.validate()


def test_each_executing_tier_has_one_pytest_process(project_root: Path) -> None:
    graph = load_gate_graph(project_root / "configs/validation_gates.json")
    assert graph.pytest_process_count("G0", "owner", owner="governance") == 1
    assert graph.pytest_process_count("G0", "phase") == 1
    assert graph.pytest_process_count("G0", "admission") == 1
```

The collection-error unit test drives plugin hooks directly; it must not launch
`pytest_gate_runner.py` from inside a pytest tier, which would create a hidden
second pytest process. The real owner/phase/admission invocation is the single
end-to-end child-runner test.

Add a literal `__cemm_test_inventory__` entry for every new Task 4 exact node in
the module that owns it, including its assertion, G0 activation, diagnostic role
and owner. Config validation accepts exact pytest node selectors only, rejects
filename/file-default inference and duplicate nodes inside a tier, and requires
admission to contain exactly one active-suite pytest process rather than nested
owner/phase pytest steps. Governance, anchor, invalidation, status, immutable
inventory and AST-metadata checks are one coalesced prerequisite, not separate
gate processes.

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
class EvidenceFile:
    path: str  # normalized repository-relative path
    sha256: str


@dataclass(frozen=True)
class GateReceipt:
    gate_result_ref: str
    run_ref: str
    tier: str
    phase: str
    fresh: bool
    source_ref: str
    environment_ref: str
    evidence_files: tuple[EvidenceFile, ...]
    started_at_utc: str
    run_nonce: str
    pre_admission_status_head_ref: str
    step_results: tuple[StepResult, ...]
```

`pre_admission_status_head_ref` binds the exact authenticated status prefix at
execution time; the mutable whole ledger is not a fixed receipt input.
`StepResult.step_ref` excludes `wall_ns` and `peak_rss_bytes`. `gate_result_ref`
covers semantic inputs/dispositions/report/error refs and ordered evidence-file
path/hash material but excludes all clocks, nonces and performance observations.
`run_ref` covers the complete serialized receipt, including start time, nonce,
wall time and peak RSS, permitting multiple fresh observations. Overall gate
status is derived from the immutable step
results rather than trusted as a mutable label. Deserializers recompute both
identity layers and reject mismatch.

Implement the only public receipt seam with this exact signature:

```python
def load_verified_admission_receipt(
    root: Path,
    *,
    phase: str,
    expected_status: str,
    run_ref: str | None = None,
) -> tuple[GateReceipt, tuple[str, ...]]:
    ...
```

It reads only existing run artifacts and never invokes the runner. It strictly
recomputes every step, `gate_result_ref` and `run_ref`; requires the filename and
serialized run identity to agree; and requires the requested phase,
`tier="admission"`, `fresh=True`, derived `expected_status` and exact declared
step set. The loader is ledger-agnostic. It validates canonical receipt
bytes, every
nested ref, stored source/environment/input identities and authenticated
external evidence, but never reads replay_status.jsonl, invokes Git history
authentication or loads another receipt.

Task 2's updater owns consumption semantics over the records it already loaded
and authenticated. Before append it requires a clean current HEAD equal to
source_ref, records[-1].record_ref equal to pre_admission_status_head_ref and no
prior row naming the run. Post-write and historical verification perform one
linear pass requiring exactly one row whose predecessor_ref equals the
pre-admission head, whose source_base equals source_ref and whose phase/gate/run
fields consume this receipt. The Task 4 governance handler applies the same
relation to its one cached ledger parse. Neither path rereads the chain per
receipt.

The loader returns the receipt plus a sorted tuple of every canonical
repository-relative external evidence path whose path/hash material the receipt
authenticated. It rejects directories, globs, inferred working-tree paths,
unauthenticated substitutions and every path/hash mismatch, but never queries
Git status. Dry-run and governance verification take one dirty-path snapshot.
Append takes
one pre-append snapshot under the exclusive lock and one post-write snapshot
before success, rolling back on mismatch. Counts are independent of receipt
count. Each check intersects dirty paths with the returned authenticated set and
rejects every dirty governed path outside it. With an explicit `run_ref` it loads exactly that run.
With `None` it succeeds only when exactly one eligible current run exists; it
never chooses by mtime, timestamp or a "latest" pointer. Raise a typed
receipt-validation error for invalid evidence and let unexpected programming
exceptions propagate.

Add RED tests for exact-run loading, ambiguous `run_ref=None`, wrong
phase/status/tier, stale/non-fresh receipts, mismatched file/run/gate/step refs,
tampered stored input identities, path traversal and
reordered/extra/missing/unauthenticated evidence paths. Prove loading
a receipt invokes no pytest/gate step, does not read the status ledger or Git
history and never recursively loads another receipt. Add updater/governance
tests for pre-consumption exact-head/source validation, post-consumption
acceptance of one exact consuming row, rejection of zero/duplicate/mismatched
consumers, historical reconstruction after later phase changes and one ledger parse independent of receipt count; one dirty snapshot
for
dry-run/governance verification; and exactly two for append (pre-append under
the lock and post-write before success/rollback). Add updater
tests proving that both green and
`externally_blocked` call the loader with `expected_status="passed"`. The
validation CLI emits the completed receipt identity,
including `run_ref`, in a stable JSON result so Tasks 5 and 10 can select it
without scanning for a latest file.

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

Missing/malformed reports fail closed. Launch argv with `shell=False`. Write a
content-addressed selector manifest inside the run root; do not place hundreds
of node IDs on the Windows command line. Owner/phase manifests contain exact
requested IDs, and the child requires collection equality. An admission manifest
contains the pinned test root, the complete governed `collectable_node_ids` and
the phase-active IDs. The child calls `pytest.main()` exactly once on the test
root, compares the full collected set before calls, deselects governed inactive
nodes in `pytest_collection_modifyitems`, and executes the active union. An
extra, missing or duplicate collected node is a structured error and no test
call may run. Redirect stdout/stderr to bounded files rather than unread pipes
while sampling,
so large output cannot deadlock on Windows. Put `TMP`, `TEMP`, `TMPDIR`,
`PYTHONPYCACHEPREFIX`, `--basetemp` and `cache_dir` inside one run root. Do
not require external `PYTHONPATH`. Measure child peak RSS via a platform sampler
and permit sampler injection in unit tests.

### Step 4: Implement only three coalesced tiers

`validation_gates.json` owns `owner`, `phase` and `admission`. Use this
structural shape; the displayed owner/phase node arrays are representative,
while the real file enumerates every selected exact diagnostic node ID.
`pytest_active` derives both the complete currently collectable set and the
eligible active union from immutable `test_inventory.json` plus literal
`__cemm_test_inventory__` metadata. Owner/phase pytest steps accept
`exact_nodes` only. The admission inventory step accepts only the reviewed test
root and those two content-addressed derived sets. Other raw file selectors,
filename/default inference and implicit parameterized expansion are forbidden:

```json
{
  "schema": "cemm-hybrid-validation-gates-v1",
  "steps": {
    "governance": {
      "kind": "governance",
      "depends_on": [],
      "test_inventory": "governance/test_inventory.json",
      "metadata_symbol": "__cemm_test_inventory__",
      "status_ledger": "governance/replay_status.jsonl",
      "invalidation_ledger": "governance/receipt_invalidations.jsonl",
      "inputs": ["docs/DOCUMENT_AUTHORITY.json", "governance/ledger_anchors.json", "governance/replay_status.jsonl", "governance/receipt_invalidations.jsonl", "governance/test_inventory.json", "pyproject.toml", "tests/"]
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
      "exact_nodes": [
        "tests/test_replay_governance.py::test_initial_replay_status_is_truthful",
        "tests/test_validation_gate.py::test_dag_deduplicates_shared_dependencies"
      ],
      "inputs": ["tests/test_replay_governance.py", "tests/test_validation_gate.py", "docs/", "governance/"]
    },
    "g0_phase_tests": {
      "kind": "pytest",
      "depends_on": ["source_compile"],
      "exact_nodes": [
        "tests/test_g0_integration.py::test_g0_admission_plan_is_coalesced_and_bounded",
        "tests/test_g0_integration.py::test_owner_and_phase_nodes_are_disjoint"
      ],
      "inputs": ["tests/test_g0_integration.py", "scripts/", "configs/validation_gates.json"]
    },
    "pytest_active": {
      "kind": "pytest_inventory",
      "depends_on": ["source_compile"],
      "test_inventory": "governance/test_inventory.json",
      "metadata_symbol": "__cemm_test_inventory__",
      "inputs": ["tests/", "src/", "governance/test_inventory.json", "pyproject.toml"]
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

The config validator rejects unknown step kinds/paths, cycles, duplicate
resolved steps or node IDs, owner/phase node overlap, every raw file selector
and an admission plan containing training/corpus/reproduction or nested
owner/phase pytest steps. The coalesced `governance` handler loads Task 3's stdlib-only inventory core
from its reviewed exact file path; it never imports it through the eager runtime
package. It validates document/anchor pins, both ledgers, every invalidated
historical file, every green or `externally_blocked` admission receipt through
`load_verified_admission_receipt` with `expected_status="passed"`, and immutable
inventory plus literal AST
metadata in one process. Each test module is parsed once, each canonical path is
hashed once, each governance artifact is loaded once, and resolved
dependencies are memoized for that invocation. Input refs hash the listed paths
and environment identity.

G0-R1 never caches test results: owner runs focused exact nodes, an applicable
phase runs only fresh disjoint cross-owner exact nodes, and admission performs
one full governed collection, inactive-node deselection and active execution in
the same invocation. Every executing tier launches exactly one pytest process;
owner and phase do not collect the complete tree. Admission's full collection is
its authoritative anti-bypass check, not a separate prerequisite or process.
Task 7 may reuse that admitted collection evidence for its ABI import-safety
claim rather than launching another complete-tree collection. Later
R4-R5 plans may reuse
content-matched diagnostics for expensive artifact steps, never tests or
admission. Governance, status, receipt loading and the pytest hook control plane remain
lightweight and must not import runtime, model, training or Torch libraries.
Make `cemm_authoritative_hybrid.__init__` lazy while preserving its public
exports, and add subprocess import tests for `validation_gate.py`,
`test_inventory_core.py` and `update_replay_status.py`.

### Step 5: Verify, review, commit

```powershell
python -m pytest tests\test_validation_gate.py -q -p no:cacheprovider --basetemp C:\tmp\cemm-g0-validator
python scripts\validate_mvp.py --tier phase --phase G0
python scripts\validate_mvp.py --help
git add hybrid_mvp/scripts/validation_gate.py hybrid_mvp/scripts/pytest_gate_runner.py hybrid_mvp/scripts/validate_mvp.py hybrid_mvp/scripts/update_replay_status.py hybrid_mvp/configs/validation_gates.json hybrid_mvp/src/cemm_authoritative_hybrid/__init__.py hybrid_mvp/tests/test_validation_gate.py hybrid_mvp/tests/test_g0_integration.py hybrid_mvp/tests/test_replay_governance.py hybrid_mvp/pyproject.toml
git commit -m "build: add structured dependency-aware replay validation"
```

## Task 5: Admit G0 without pretending runtime/model success

**Files:**

- Create: `hybrid_mvp/artifacts/validation/BASELINE_REPLAY_FINDINGS.json`
- Generate: `hybrid_mvp/artifacts/validation/TEST_INVENTORY_RECEIPT.json`
- Generate: `hybrid_mvp/artifacts/validation/runs/<run_ref>.json`
- Append: `hybrid_mvp/governance/replay_status.jsonl`


### Step 1: Capture exact baseline findings

Bind commands, environment/source ref, the reviewed 743-node predecessor
collection, the current collectable/active set refs, both threshold failures,
proposal/runtime divergence, and authority EOL failure. State
The findings also record that Program ABI 1 derivations are incorrectly used as settled meaning, bootstrap-influenced programs author current gold, entity/source anonymization can collapse pointer-distinct meanings, and marker checks substitute for round-trip expression equivalence. Every Program ABI 1 corpus, episode, checkpoint, calibration and evaluation descendant remains quarantined historical evidence.

`runtime_admitted: false` and `model_artifacts_admitted: false`. G0 validates
that forensic evidence; it does not require downstream R1/R7 behavior to pass.
Generate `TEST_INVENTORY_RECEIPT.json` from the verified immutable inventory
and literal metadata without launching pytest.

Commit these deterministic G0 inputs before admission and require a clean
worktree. The admission receipt's `source_ref` is this exact candidate commit;
it must never point at a prior commit plus an open-ended dirty source set.

```powershell
git add hybrid_mvp/artifacts/validation/BASELINE_REPLAY_FINDINGS.json hybrid_mvp/artifacts/validation/TEST_INVENTORY_RECEIPT.json
git commit -m "chore: stage deterministic G0 admission inputs"
git status --short
```

### Step 2: Run exactly one fresh G0 admission

Task 1-4 red/green work already ran owner and phase tiers. Do not rerun them
ceremonially before admission. Refuse to start unless the candidate source
worktree is clean.

```powershell
$g0Admission = (python scripts\validate_mvp.py --tier admission --phase G0 | ConvertFrom-Json)
$g0RunRef = $g0Admission.run_ref
```

The fresh admission has zero G0-active skip/xfail/xpass, binds every downstream
frozen predecessor case or later literal-metadata case to one exact node, and
runs no corpus/model work. Inspect and
cryptographically verify the exact run file named by `$g0RunRef` before any
status transition. Do not discover a receipt through a latest pointer or file
mtime.

### Step 3: Validate, then append G0 green

`update_replay_status.py --dry-run` loads the exact run through
`load_verified_admission_receipt(root, phase="G0", expected_status="passed",
run_ref=$g0RunRef)` and receives (receipt, authenticated_evidence_paths). The
loader returns every exact authenticated external path without querying Git
status. Dry-run takes one dirty-path snapshot. Locked append takes one
pre-append and
one post-write snapshot, each independent of receipt count; every check permits
only the intersection with that set and rejects every other dirty governed
path. Dry-run emits the
complete candidate without
writing. Preserve that candidate's `record_ref`. Append must name the same run
and expected record; it reloads the receipt and recomputes the row while holding
the ledger write lock. Any input, evidence path/bytes, receipt, ledger-head or
record-ref change writes nothing. Effective state becomes
`G0=green, R1-R8=red`.

```powershell
$g0Candidate = (python scripts\update_replay_status.py --phase G0 --status green --run-ref $g0RunRef --dry-run | ConvertFrom-Json)
python scripts\update_replay_status.py --phase G0 --status green --run-ref $g0RunRef --expect-record-ref $g0Candidate.record_ref --append
python scripts\update_replay_status.py --verify-chain
git add hybrid_mvp/artifacts/validation/runs hybrid_mvp/governance/replay_status.jsonl
git commit -m "chore: admit corrective replay governance"
```

Receipt loading, candidate dry-run and final chain verification inspect the one
fresh admission; they are not additional gate executions. Before the status
append, the updater requires the current status head to equal
pre_admission_status_head_ref and current clean HEAD to equal source_ref. After
append, updater/governance verification accepts only the unique authenticated
consuming row in the already-loaded chain; it does not ask the receipt loader to
reread history or compare an old receipt to newer R1 working-tree bytes. This status/receipt commit and every referenced
`source_base` must be integrated by fast-forward or
history-preserving merge commit, never squash/cherry-pick-only history rewriting.


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
tampering. Add literal per-node `__cemm_test_inventory__` metadata with R1
activation and the content-identity owner before running each new test. Run and
observe RED.

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

## Task 7: Hard-cut Program ABI 2 and compile canonical Semantic Expression ABI 1

**Files:**

- Create: `hybrid_mvp/src/cemm_authoritative_hybrid/proposal_context.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/programs.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/proposal.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/model.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/verifier.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/coverage.py`
- Modify: `hybrid_mvp/src/cemm_authoritative_hybrid/gaps.py`
- Create: `hybrid_mvp/src/cemm_authoritative_hybrid/expressions.py`
- Create: `hybrid_mvp/src/cemm_authoritative_hybrid/situation.py`
- Delete after caller migration: `hybrid_mvp/src/cemm_authoritative_hybrid/propositions.py`
- Modify active callers in `runtime.py`, `bootstrap.py`, `coverage.py`, `query.py`,
  `epistemics.py`, `episodes.py`, `training.py` and `evaluation.py`
- Modify affected R1 fixtures/tests
- Modify: `hybrid_mvp/configs/validation_gates.json`
- Create: `hybrid_mvp/tests/test_r1_verification_batch.py`
- Create: `hybrid_mvp/tests/test_r1_no_alternate_public_paths.py`

### Step 0: Freeze the implementable R1 seam before coding

The 2026-08-02 semantic-algebra package makes the program-to-expression
separation authoritative, but its abbreviated replacement snippets do not fully
specify an executable R1 seam. The following clarification is normative for
Tasks 7-9 and supersedes narrower dataclass snippets below.

#### Proposal Context ABI 1

Create one immutable, content-addressed `ProposalContext` in ORIENT and pass that
same object through PROPOSE and VERIFY. It contains only bounded, current-cycle
slots for designations, contributions, modes, application frames, references,
scopes, expression links, variables, transitions, residual evidence, source
spans and the exact revision pin. It owns a `context_ref`; both
`SemanticSwitchProgram` and `ProposalResult` bind that ref.

Scores stored in exact artifacts are fixed-point integers (`score_q`), never
unrestricted floats. Build immutable lookup maps once in `ProposalContext`
construction and exclude those derived caches from serialization/identity.
Normal cycles may not linearly rescan slot tuples for every action and may not
open an authority-wide target inventory after ORIENT.

The useful typed slot records in the G0-R6 selective package may be ported, but
its Context ABI 2 number, float identities, repeated `next(...)` lookups and
Program ABI 4 `resolved_applications` field are rejected. Resolved semantic
structure belongs only to `SemanticExpression`.

#### Program ABI 2 action-slot grammar

`ProgramAction.arguments` is not an untyped convention. Program ABI 2 freezes
these exact schemas; R2 may activate additional legal combinations but may not
redefine their slots:

```text
select_context(context_slot_ref)
select_mode(mode_slot_ref)
select_designation(designation_slot_ref)
instantiate_operator(application_local_ref, application_frame_ref)
bind_role(application_local_ref, role_ref, contribution_slot_ref)
bind_reference(application_local_ref, role_ref, reference_slot_ref)
bind_nested_application("role", parent_application_ref, role_ref, child_node_ref)
bind_nested_application("link", link_local_ref, expression_link_slot_ref,
                        operand_node_ref, operand_node_ref, ...)
attach_scope(scope_local_ref, scope_slot_ref, operand_node_ref)
project_variable(binder_local_ref, variable_slot_ref, body_node_ref)
propose_transition(transition_slot_ref, source_application_ref)
complete_program()
abstain()
```

The `link` variant is the reviewed way to construct coordination, condition,
cause, contrast and sequence without a thirteenth switch action. Its context
slot fixes link type, ordered-versus-commutative behavior, arity and source
origin. `propose_transition` is a verified decision hint: it maps exactly once
to the compilation proof and is validated against the source event application,
but it does not manufacture an extra semantic application or alter expression
identity. EVALUATE later derives any authorized effect from the verified
expression, situation and reviewed transition contract.

Every action carries a non-negative contiguous `action_index`; `action_ref`
covers ABI, index, type, complete arguments and source refs. Every cross-action
reference targets a declared local node or exact context slot. Direct
construction, deserialization with defaults, unknown fields, boolean-for-int
coercion and forged refs are rejected.

`ACTION_ABI_SCHEMAS` is one frozen vocabulary/schema value.
`action_abi_hash` hashes only that complete closed vocabulary and never changes
with candidate pointers or action order. `program_ref` hashes ABI version,
orientation ref, proposal-context ref, the complete ordered action sequence,
roots, mode, goals, exact assignments and revision pin. It contains no resolved
application/expression graph.

#### Ranked Proposal Result ABI 2

```python
@dataclass(frozen=True)
class RankedProgramCandidate:
    candidate_ref: str
    rank: int
    score_q: int
    program: SemanticSwitchProgram
    provenance_refs: tuple[str, ...]


@dataclass(frozen=True)
class ProposalResult:
    proposal_ref: str
    orientation_ref: str
    proposal_context_ref: str
    candidates: tuple[RankedProgramCandidate, ...]
    status: Literal["candidates", "abstained"]
    abstention_code: str | None
    explored_states: int
    truncated: bool
    model_identity: str
    revision_pin: RevisionPin
```

Ranks are contiguous in preserved proposer order. Candidate, program, context,
orientation, model and revision identities must agree. Sorting by `program_ref`
is forbidden. A truncated proposal cannot yield a unique selected meaning; it
fails closed to the existing typed budget/frontier route. PROPOSE never calls
the exact verifier.

#### Coverage ABI 2 and compilation proof

Coverage validation receives the exact context. It rejects missing or extra
source units, unknown contribution slots, assignments whose source geometry or
target action/role is incompatible, duplicate consumption and a program's false
criticality claim. Criticality is independently reconstructed from context
contribution kind and reviewed construction metadata. The coverage receipt hash
includes every source, contribution, assignment target, disposition and error.

```python
@dataclass(frozen=True)
class TranslationRow:
    source_ref: str
    disposition: str
    target_refs: tuple[str, ...]


@dataclass(frozen=True)
class CompilationProof:
    proof_ref: str
    program_ref: str
    proposal_context_ref: str
    expression_ref: str
    action_translations: tuple[TranslationRow, ...]
    assignment_translations: tuple[TranslationRow, ...]
    root_translations: tuple[TranslationRow, ...]
    grounding_refs: tuple[str, ...]
    revision_pin: RevisionPin
```

Every program action, source assignment and declared root occurs exactly once in
its proof domain. A candidate receipt retains the actual `CompilationProof` and
Coverage ABI 2 receipt, not only their refs, so it can be reconstructed and
audited without hidden compiler state.

`SemanticExpressionCompiler.compile(program, context)` is total and returns a
typed success or typed compilation failure. Programming exceptions propagate.
`ExactProgramVerifier.verify_candidates(proposal, context)` checks exact
proposal/context binding, replays legal action transitions independently,
validates coverage, invokes compilation and independently checks proof and
expression topology. It never repairs.

Accepted candidates are grouped in O(candidate-count) by `expression_ref`.
Each group's score/rank is its best derivation; duplicate derivation scores are
never summed. The selected lineage is the best candidate in the winning
expression group. Distinct expression groups inside the constructor-pinned
integer margin remain ambiguous.

#### R1/R2 boundary and atomic hard cut

R1 freezes the complete action grammar, Proposal Context ABI 1, Program ABI 2,
Proposal Result ABI 2, Coverage ABI 2, full expression representation,
compilation proof, Verification Batch ABI 2 and the one public runtime path.
The R1 compiler must support a bounded single-application subset sufficient to
prove derivation-independent expression identity, pointer-direction
sensitivity, complete translation and typed failure. A syntactically registered
but R2-only action shape returns `action_shape_not_admitted`; it never falls back
or invents structure.

Direct R1 expression tests cover multi-root, nested, scope, link and binder
canonical topology. Authentic generation/compilation canaries for all twelve
actions, multiple applications, three roots, every scope/link family, variables
and transitions remain R2 admission work. This preserves the replay allocation
without leaving an ambiguous ABI for R2 to redefine.

Tasks 7-9 are one atomic hard cut. Do not claim an intermediate green Task 7
while duplicate runtime results, `propositions.py`, `propose_and_verify`, shape
adapters or raw-program EVALUATE remain. New owner tests receive literal
inventory metadata as they land, but the R1 phase/owner selectors are activated
only once the complete Tasks 7-9 supersession set is present. The final R1 DAG
still uses the already planned owner groups and one phase integration tier; this
clarification adds no validation tier, no seventh runtime phase and no normal
cycle gate.

### Step 1: Add RED owner/content tests

```python
def test_cross_phase_types_have_one_owner() -> None:
    assert class_owners("SemanticSwitchProgram") == {"programs.py"}
    assert class_owners("SemanticExpression") == {"expressions.py"}
    assert class_owners("VerifiedMeaning") == {"expressions.py"}
    assert class_owners("ProposalResult") == {"proposal.py"}
    assert class_owners("VerificationBatch") == {"verifier.py"}


def test_proposal_phase_output_binds_the_complete_batch(proposal_result) -> None:
    assert proposal_result.candidates
    assert not hasattr(proposal_result, "program")
    assert proposal_result.output_refs == (proposal_result.proposal_ref,)
    first = proposal_result.candidates[0]
    assert proposal_result.candidate_by_ref(first.candidate_ref) is first
```

Add tests that every semantic field affects its ref and every deserializer
rejects a stored/nested ref mismatch.

### Step 2: Make leaf/container refs strict

`ProgramAction`, `SourceAssignment` and `SemanticSwitchProgram` expose only strict
content-addressed constructors. `from_dict` rejects unknown/missing fields, wrong
scalar types, nested ref mismatches and non-canonical tuple/order encodings.
`SemanticSwitchProgram.create` derives `program_ref` from ABI version,
orientation, proposal context, ordered indexed actions, roots, mode, goals,
source assignments and revision pin.

Legacy `ScopeFrame` and `TransitionProposal` program-side semantic wrappers are removed.
Their bounded selectable evidence is owned by Proposal Context ABI 1; expression
scope is owned by Semantic Expression ABI 1 and transition hints remain proof/envelope data.

Do not put observational scores/clocks in program identity. Do include literal
and dynamic-pointer values and order; `action_abi_hash` is vocabulary/schema
identity and is never a program or meaning identity.

### Step 3: Define the exact proposal batch

```python
@dataclass(frozen=True)
class RankedProgramCandidate:
    candidate_ref: str
    rank: int
    score_q: int
    program: SemanticSwitchProgram
    provenance_refs: tuple[str, ...]


@dataclass(frozen=True)
class ProposalResult:
    proposal_ref: str
    orientation_ref: str
    proposal_context_ref: str
    candidates: tuple[RankedProgramCandidate, ...]
    status: Literal["candidates", "abstained"]
    abstention_code: str | None
    explored_states: int
    truncated: bool
    model_identity: str
    revision_pin: RevisionPin

    @property
    def output_refs(self) -> tuple[str, ...]:
        return (self.proposal_ref,)

    def candidate_by_ref(self, candidate_ref: str) -> RankedProgramCandidate:
        matches = tuple(c for c in self.candidates if c.candidate_ref == candidate_ref)
        if len(matches) != 1:
            raise KeyError(candidate_ref)
        return matches[0]
```

Create/deserialization derives/checks every nested ref. Candidate refs are unique;
ranks are contiguous in preserved proposer order; scores are exact integers; and
each candidate program matches proposal orientation, context and revision.
`status="abstained"` requires zero candidates and a non-empty typed code;
`status="candidates"` requires candidates and no abstention code.
`candidate_by_ref` requires exactly one envelope match. There is no `program`
compatibility property and no program-ref sort.

Critically, PROPOSE must not invoke `ExactProgramVerifier`. Remove current
verifier calls in `proposal.py` and `model.py`. Proposal may enforce decoder
action masks, but exact independent acceptance occurs only in VERIFY.

### Step 4: Compile and verify canonical meaning

Create Program ABI 2 with a complete order-sensitive `program_ref`; retain
`action_abi_hash` only as the closed model-vocabulary identity. Implement
`SemanticExpressionCompiler` as a total exact compiler from one complete
program plus its exact proposal context into either one canonical multi-root
expression forest and compilation proof or one typed failure. The compiler may
never invent omitted roles, fillers, roots, scopes or links.

`SemanticExpression` owns applications, explicit root refs, typed role/filler
bindings, scope operators, ordered or reviewed-commutative expression links,
variable binders and typed unresolved fillers. Canonicalization alpha-renames
only local IDs through a proven bijection. Grounded identity, role, polarity,
modality, attribution, temporal qualifiers and persistent operators survive.
Source geometry stays in coverage unless attribution/source is meaning.

`ExactProgramVerifier` independently validates ordered program identity,
dynamic-pointer origin, coverage and legality, invokes the compiler, and proves
that every action/source assignment translated exactly once. It then validates
roots, reachability, parent rules, acyclicity and depth on the expression.
VERIFY never repairs.

```python
@dataclass(frozen=True)
class CandidateVerificationReceipt:
    receipt_ref: str
    candidate_ref: str
    candidate_index: int
    program_ref: str
    expression: SemanticExpression | None
    compilation_proof: CompilationProof | None
    coverage_receipt: CoverageReceipt
    verification_errors: tuple[VerificationError, ...]


@dataclass(frozen=True)
class VerificationBatch:
    batch_ref: str
    proposal_ref: str
    proposal_context_ref: str
    candidate_receipts: tuple[CandidateVerificationReceipt, ...]
    status: Literal["selected", "rejected", "abstained", "ambiguous"]
    selected_candidate_ref: str | None
    selected_meaning: VerifiedMeaning | None
    ambiguity_expression_refs: tuple[str, ...]
```

There is exactly one receipt per proposal candidate. Accepted derivations with
the same `expression_ref` form one semantic alternative before margin/ambiguity
selection. Distinct accepted expressions inside the margin remain ambiguous.
`VerifiedMeaning` binds selected expression, grounding, coverage, compilation
proof, verification receipt, revision and program lineage. Its ref may include
lineage; expression plus situated qualifiers is the semantic comparison key.
Constructors/deserializers enforce every cross-field identity and verifier
programming exceptions propagate.

R1 compiler canaries cover two derivations compiling to one expression, swapped
dynamic pointers compiling differently, complete single-application translation,
and rejection when any supported action/assignment/root is omitted, duplicated or
mistranslated. Direct expression tests cover multiple roots, nested fillers,
ordered/commutative links, scope, attribution and binders. Authentic generated
program canaries across every structural family remain R2 admission work.

### Step 5: Remove legacy wrappers and stop at the R1 boundary

Delete `propositions.py` only after every caller imports the canonical Program
ABI 2 / Expression ABI 1 owners. Move any still-valid graph structures into
`expressions.py`; do not retain a legacy program or graph wrapper. Refactor
`query.py` and `epistemics.py` toward `VerifiedMeaning.expression` plus explicit
`SituationContext`. Until R3 owners are implemented, `HybridRuntime.process()`
returns a typed later-owner gap after VERIFY and never passes a raw program to
EVALUATE.

Migrate production imports in runtime, bootstrap, episodes, corpus and
evaluation paths. Remove signature inspection, result-shape adaptation,
`propose_and_verify()` and all program-as-meaning compatibility properties.
Update import-bearing predecessor tests and shared fixtures before deletion,
including `test_epistemic_admission.py`, `test_inference_bounds.py`,
`test_learning_distinctions.py`, `test_query_engine.py`,
`test_recursive_inference.py`, `test_restart_e2e.py`,
`test_synonym_acquisition.py` and `tests/conftest.py`.
Frozen source-test bodies are immutable. Imports, fixtures and non-test helpers
may change, but changing a frozen test requires a new exact node ID with literal
metadata that supersedes the predecessor, preserves its assertion ref and does
not regress activation phase. Task 7 must supersede these nine R1 nodes rather
than edit them in place: the six test_program_abi.py nodes covering unknown
action type, all confirmed action types, empty/extracted persistent operators,
action-encoding structural sensitivity and frozen ProgramAction; plus the three
test_adversarial_programs.py nodes covering fabricated bind references, unknown
action type and unknown operator. Their successors must construct valid
content-addressed actions/programs so a test cannot pass early for an unrelated
ref mismatch.

Run structured collection across the entire predecessor tree and require no
collection errors and no loss of the 743 baseline cases before deleting the
duplicate class. Collection retention is provenance; the R1 selector resolves
only the transitive supersession leaf.

### Step 6: Verify, review, commit

Add literal `__cemm_test_inventory__` metadata for every new Task 7 exact node.
Add one `r1_program_verifier_owner_tests` step whose `exact_nodes` enumerate only
those eligible R1 nodes plus exact retained frozen predecessor cases affected by
this owner. Parameterized cases are listed individually. The runner rejects any
historical or R2+ node. Do not select
`test_program_abi.py`, `test_bootstrap_proposer.py`, `test_neural_proposer.py`,
`test_exact_verifier.py`, `test_adversarial_programs.py` or another mixed-phase
file as a whole.

Run that owner step once. This program/proposal/verifier ABI is one declared R1
owner group; it has no separate phase tier before the public composition exists
in Task 9. Separately collect the complete current tree once through the
structured hook before deleting the legacy class; collection proves
importability, preserves the frozen 743-case set and accounts for every later
literal-metadata node without executing a later-phase test. This explicit
migration-only collection is not part of the owner tier and does not cause that
tier to launch a second pytest process.

```powershell
python scripts\validate_mvp.py --tier owner --phase R1 --owner program-verifier
python scripts\pytest_gate_runner.py --report C:\tmp\cemm-r1-all-collect.json -- --collect-only -q
git add hybrid_mvp/src/cemm_authoritative_hybrid hybrid_mvp/configs/validation_gates.json hybrid_mvp/tests
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
- Modify: `hybrid_mvp/configs/validation_gates.json`
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

Do not edit frozen test bodies under their old IDs. Task 8 adds literal
superseding nodes for the PhaseReceipt frozen-dataclass test; the five retained
CycleResult artifact tests for orientation, proposal, verification, evaluation
and response meaning; and the four retained restart tests for pin fields,
consecutive-cycle pins, stale-orient restart and complete post-restart
artifacts. The new proposal/verification assertions use candidate/batch
semantics and direct CycleResult fields, never compatibility properties.

### Step 4: Verify, review, commit

Add literal `__cemm_test_inventory__` metadata for every new Task 8 exact node.
Add one `r1_cycle_owner_tests` step whose `exact_nodes` enumerate those new
identity cases plus only eligible retained frozen R1 cycle/receipt cases.
Parameterized cases are listed individually. Do not execute `test_phase_receipts.py`,
`test_cognitive_loop_e2e.py`, `test_restart_e2e.py` or another mixed-phase file
as a whole. The config validator must prove that this owner node set is disjoint
from Task 7 and from the later R1 phase-integration set. This result-identity
owner has no separate phase tier until Task 9 creates the one public composition
integration boundary.

```powershell
python scripts\validate_mvp.py --tier owner --phase R1 --owner cycle-result
git add hybrid_mvp/src/cemm_authoritative_hybrid/cycle.py hybrid_mvp/src/cemm_authoritative_hybrid/runtime.py hybrid_mvp/src/cemm_authoritative_hybrid/__init__.py hybrid_mvp/configs/validation_gates.json hybrid_mvp/tests
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
    def propose(self, context: ProposalContext) -> ProposalResult: raise NotImplementedError


class VerificationOwner(Protocol):
    def verify_candidates(
        self, proposal: ProposalResult, context: ProposalContext
    ) -> VerificationBatch: raise NotImplementedError


def process(self, session_ref: str, text: str, *, trace: bool = True) -> CycleResult:
    orientation, context = self.orient(session_ref, text)
    proposal = self._proposal_owner.propose(context)
    verification = self._verification_owner.verify_candidates(proposal, context)
    if verification.status in {"rejected", "abstained"}:
        return self._finalize_verification_gap(
            orientation, context, proposal, verification, trace=trace
        )
    if verification.status == "ambiguous":
        return self._finalize_ambiguity(
            orientation, context, proposal, verification, trace=trace
        )
    verified_meaning = verification.selected_meaning
    if verified_meaning is None:
        raise AssertionError("selected verification has no VerifiedMeaning")
    return self._continue_or_report_disabled_owner(
        orientation, context, proposal, verification, verified_meaning, trace=trace
    )
```

ORIENT builds `ProposalContext` once. PROPOSE and VERIFY receive that exact bounded
object; neither retokenizes surface text nor rescans authority. The continuation
boundary accepts `VerifiedMeaning` only. A caller may resolve
`verified_meaning.program_ref` against the proposal batch for derivation-lineage
diagnostics, but the resolved program is never the semantic phase input.

At the R1 boundary `_continue_or_report_disabled_owner` emits the exact
`LaterOwnerNotAdmitted` implementation gap bound to the verified-meaning ref and
`contract:r3:evaluate`. It does not invoke or fabricate EVALUATE, EFFECT or
REALIZE and emits no surface. The admitted-through-VERIFY branch is fixed once
at activation, so normal execution pays one constant branch and no extra gate.

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

Task 9 must add new-ID, assertion-preserving successors for all five retained
test_six_phase_runtime.py nodes and
test_production_proposer_cutover.py::test_development_profile_still_works.
Those successors use canonical process(); they never edit the frozen body or
retain the shortcut. R1 admission resolves each supersession chain to exactly
one leaf and fails before pytest if any of these 25 Task 7-9 obligations remains
unsatisfied.

### Step 5: Add the now-existing R1 gate selectors

Retain the exact-node Task 7 `r1_program_verifier_owner_tests` and Task 8
`r1_cycle_owner_tests` steps. Add literal per-node
`__cemm_test_inventory__` metadata for every new Task 9 case, then add:

- `r1_runtime_owner_tests`, whose `exact_nodes` enumerate the new runtime-path
  cases and eligible retained frozen R1 predecessor cases;
- `r1_phase_tests`, whose `exact_nodes` enumerate only cross-owner integration
  cases that did not run in an owner tier;
- `r1_structure`, a source-scan step that proves one surviving canonical class
  owner and rejects signature inspection, compatibility result views, alternate
  public paths and fixture release owners.

Do not use a whole-file selector for `test_program_abi.py`,
`test_exact_verifier.py`, `test_phase_receipts.py`, `test_six_phase_runtime.py`
or any other mixed-phase file. The `R1` phase configuration has three named
owners (`program-verifier`, `cycle-result`, `runtime-path`), one
`r1_phase_tests` integration step and admission roots
`["r1_structure", "sqlite_activation", "pytest_active"]`. `r1_structure` runs
inside the one admission DAG; it is not a standalone pre-admission gate.

Config validation requires every explicit node ID to resolve exactly once from
the immutable frozen inventory or literal AST metadata, rejects nodes activated
after R1, rejects duplicate nodes and proves the union of all R1 owner nodes is
disjoint from R1 phase nodes. No filename, file-default or live-Git inference is
allowed. Add these integration assertions:

```python
def test_r1_phase_does_not_repeat_owner_tests(project_root: Path) -> None:
    graph = load_gate_graph(project_root / "configs/validation_gates.json")
    resolved = graph.resolve_phase("R1", "phase")
    assert resolved == ("governance", "source_compile", "r1_phase_tests")
    owner_nodes = set(graph.resolve_all_owner_pytest_nodes("R1"))
    phase_nodes = set(graph.resolve_pytest_nodes("R1", "phase"))
    assert owner_nodes.isdisjoint(phase_nodes)
    assert all(graph.is_active_by(node, "R1") for node in phase_nodes)
    assert len(phase_nodes) == len(set(phase_nodes))


def test_r1_admission_has_one_active_suite_execution(project_root: Path) -> None:
    graph = load_gate_graph(project_root / "configs/validation_gates.json")
    resolved = graph.resolve_phase("R1", "admission")
    assert "r1_structure" in resolved
    assert "pytest_active" in resolved
    assert not {"r1_program_verifier_owner_tests", "r1_cycle_owner_tests",
                "r1_runtime_owner_tests", "r1_phase_tests"} & set(resolved)
```

### Step 6: Verify, review, commit

```powershell
python scripts\validate_mvp.py --tier owner --phase R1 --owner runtime-path
python scripts\validate_mvp.py --tier phase --phase R1
git add hybrid_mvp/src/cemm_authoritative_hybrid hybrid_mvp/scripts hybrid_mvp/configs/validation_gates.json hybrid_mvp/tests
git commit -m "refactor: leave one canonical hybrid runtime path"
```

This is the one applicable R1 phase integration run and launches one pytest
process. It executes no Task 7, Task 8 or Task 9 owner node and does not pre-run
the later admission active suite.

## Task 10: Fresh R1 admission and truthful status

**Files:**

- Generate: `hybrid_mvp/artifacts/validation/runs/<run_ref>.json`
- Append: `hybrid_mvp/governance/replay_status.jsonl`

### Step 1: Keep structural proof inside admission

Do not run standalone pre-admission `rg` gates. Task 9's `r1_structure` step owns
the canonical-owner and forbidden-path scans and is already a dependency of the
single R1 admission DAG. The controller inspects that step's structured result
from the admission receipt.

### Step 2: Run exactly one fresh R1 admission

Task 6-9 red/green work already ran owner and phase tiers. Do not rerun them
immediately before admission. Task 9's commit is the exact clean R1 candidate
source; refuse admission if the worktree has any uncommitted governed source.

```powershell
git status --short
$r1Admission = (python scripts\validate_mvp.py --tier admission --phase R1 | ConvertFrom-Json)
$r1RunRef = $r1Admission.run_ref
```

That one run performs the coalesced structural proof, portable authority
linking, fresh SQLite activation, complete G0-R1 active tests, source compile and
corruption checks. Its test step launches one pytest process with the complete
eligible exact-node union from the immutable inventory and literal metadata. It
excludes corpus/training/reproduction and accounts for every later governed
node. `$r1RunRef` identifies the exact run; do not discover
one through a latest pointer or file mtime.

### Step 3: Inspect, validate, then append R1 green

Controller inspects the exact `$r1RunRef` receipt's structural result, counts,
wall time, peak RSS and slowest cases and verifies every nested identity. Dry-run
loads it through
`load_verified_admission_receipt(root, phase="R1", expected_status="passed",
run_ref=$r1RunRef)` and receives (receipt, authenticated_evidence_paths). The
loader returns every exact authenticated external path without querying Git
status. Dry-run takes one dirty-path snapshot. Locked append takes one
pre-append and
one post-write snapshot, each independent of receipt count; every check permits
only the intersection with that set and rejects every other dirty governed
path.
It then emits the candidate row. Preserve that row's `record_ref`; append must
reload the same run and match that exact record while holding the ledger write
lock:

```powershell
$r1Candidate = (python scripts\update_replay_status.py --phase R1 --status green --run-ref $r1RunRef --dry-run | ConvertFrom-Json)
python scripts\update_replay_status.py --phase R1 --status green --run-ref $r1RunRef --expect-record-ref $r1Candidate.record_ref --append
python scripts\update_replay_status.py --verify-chain
```

Receipt loading, dry-run and chain verification inspect the one admission and do
not execute additional validation tiers. Any changed governed input invalidates
that receipt and requires one new admission rather than a relabel or partial
rerun.

Leave R2-R8 red. ABI_REGISTRY and INTEGRATION already point to the status ledger; do not change governing inputs after admission.
Investigate unexplained cost growth; never weaken semantic bounds/coverage.

```powershell
git add hybrid_mvp/artifacts/validation hybrid_mvp/governance/replay_status.jsonl
git commit -m "chore: admit canonical hybrid replay R1"
```

This admission commit and all prior ledger `source_base` commits are durable
release evidence. Integrate the branch only by fast-forward or
history-preserving merge commit; do not squash, rebase, cherry-pick-only
integrate, filter or force-push away the referenced ancestry.

Request full-plan contract review then code-quality/performance review.

## R1 handoff

R1 is complete only with a verified fresh receipt, effective status
`G0=green, R1=green, R2-R8=red` and an intact monotonic `source_base` ancestry
through current HEAD. Then write the detailed R2 plan from observed R1
APIs/receipts. Do not begin R2 from donor assumptions, retain a temporary R1
adapter or rewrite the admitted history.
