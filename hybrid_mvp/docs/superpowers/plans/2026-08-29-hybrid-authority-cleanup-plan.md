# Hybrid MVP Authority and Regression-Surface Cleanup Implementation Plan

> **Completed historical evidence:** This document records an earlier tranche;
> it is not an executable current plan and owns no phase status. Current status
> is derived from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Hybrid MVP expose one fail-closed authority path that rejects both defective R4 partition generations, blocks R5 until authentic supervision exists, describes placeholders truthfully, and prevents CI from rewriting governed source.

**Architecture:** Work from the source-only `0e5cc801` corrective snapshot. First strengthen the existing governance tests, then introduce one R4.1/R5 corrective amendment, reclassify and banner every authority-like document, correct misleading docstrings without changing behavior, and remove obsolete self-mutating workflows. The replay ledger, generated R4 artifacts, root runtime, and semantic implementation remain byte-unchanged.

**Tech Stack:** Markdown, JSON, Python 3.11+, pytest, Python `ast`, PowerShell, GitHub Actions YAML, existing CEMM governance and test-inventory tooling.

---

Run Python, pytest, inventory, and Hybrid-relative Git commands from the
worktree's `hybrid_mvp/` directory. Steps that inspect or stage `.github/` or
repository-root files explicitly say to run from the worktree root.

## File structure and ownership

### New files

- `docs/superpowers/specs/2026-08-29-r4-1-data-supervision-corrective-amendment.md` — highest-precedence Hybrid data/supervision law after `AGENTS.md`.
- `docs/superpowers/plans/2026-08-29-hybrid-authority-cleanup-plan.md` — this completed execution record; historical after implementation.

### Modified authority and routing files

- `docs/DOCUMENT_AUTHORITY.json` — exact classification and precedence owner.
- `AGENTS.md` — points to the corrective amendment without copying phase status.
- `README.md`, `INTEGRATION.md`, `docs/IMPLEMENTATION_PLAN.md` — current routing surfaces; ledger links only.
- `docs/ARCHITECTURE.md` — removes the rejected global-union partition prescription.
- `docs/ABI_REGISTRY.md` — distinguishes target, implemented, and admitted contracts.
- `docs/REPLAY_GOVERNANCE.md` — explains final document classes and status ownership.
- `docs/superpowers/specs/2026-08-22-r5-neural-activation-r6-composition-design.md` — adds the R4.1 supervision prerequisite.
- `docs/superpowers/plans/2026-08-22-r5-neural-activation-r6-composition-plan.md` — makes implementation tasks conditional on the prerequisite.

### Historical/superseded banner targets

- `docs/superpowers/specs/2026-08-14-r4-partition-corrective-replay-design.md`
- `docs/superpowers/plans/2026-08-14-r4-partition-corrective-replay-plan.md`
- `docs/superpowers/specs/2026-08-12-r4-repository-owned-admission-design.md`
- `docs/superpowers/plans/2026-08-12-r4-repository-owned-admission-plan.md`
- `docs/superpowers/plans/2026-08-05-hybrid-mvp-r3-r4-implementation-plan.md`
- `docs/superpowers/plans/2026-08-04-hybrid-mvp-completion-critical-path.md`
- completed G0/R1, R2, R3, R5-foundation plans and progress/readiness reports listed in Task 2.

### Comment-only source files

- `src/cemm_authoritative_hybrid/realization.py` — describe marker checks and the pre-admission scaffold truthfully.
- `src/cemm_authoritative_hybrid/training.py` — describe hash-bucket and bootstrap-derived targets truthfully.

### Test owner

- `tests/test_replay_governance.py` — extend the existing G0 governance owner rather than create a parallel validator.

### Workflow removals

- `.github/workflows/hybrid-mvp-r3-r4-audit.yml`
- `.github/workflows/r3-lineage-closeout.yml`
- `.github/workflows/r3-migration-snapshot.yml`
- `.github/workflows/r3-postverify-close-v2.yml`
- `.github/workflows/r3-postverify-close.yml`
- `.github/workflows/r3-self-close-literal-fix.yml`
- `.github/workflows/r3-self-close.yml`
- `.github/workflows/r3-simulate-probe.yml`
- `.github/workflows/r3-structural-migration.yml`
- `.github/workflows/r4-phase-episodes-diagnostic.yml`

Git history preserves these obsolete branch-specific workflows. Do not copy them to a disabled-workflow directory.

---

### Task 1: Establish exact document classification and R4.1/R5 authority

**Files:**

- Modify: `tests/test_replay_governance.py:30-130,890-980`
- Create: `docs/superpowers/specs/2026-08-29-r4-1-data-supervision-corrective-amendment.md`
- Modify: `docs/DOCUMENT_AUTHORITY.json`
- Modify: `AGENTS.md:14-25,140-150`

- [ ] **Step 1: Write the failing authority-classification tests**

Add these constants beside the existing document constants in `tests/test_replay_governance.py`:

```python
R4_1_AMENDMENT = (
    "docs/superpowers/specs/"
    "2026-08-29-r4-1-data-supervision-corrective-amendment.md"
)

AUTHORITY_LIKE_ROOT_FILES = frozenset({
    "AGENTS.md",
    "README.md",
    "INTEGRATION.md",
})

REQUIRED_R5_PREREQUISITE_MARKERS = (
    "reviewed derivation supervision is independent of bootstrap output",
    "every purpose class contains semantic evaluation denominators",
    "reviewed ResponseMeaning-to-surface supervision",
    "unsupported reviewed minima fail without trimming",
)
```

Add these tests after `test_document_authority_is_scoped_and_classifications_are_exact`:

```python
def test_authority_cleanup_classifies_every_authority_like_document_once() -> None:
    authority = _authority()
    classes = (
        tuple(authority["governing_documents"]),
        tuple(authority["superseded_execution_claims"]),
        tuple(authority["historical_evidence"]),
    )
    classified = set().union(*(set(rows) for rows in classes))
    markdown = {
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "docs").rglob("*.md")
    }
    assert markdown | AUTHORITY_LIKE_ROOT_FILES <= classified
    for index, left in enumerate(classes):
        for right in classes[index + 1 :]:
            assert set(left).isdisjoint(right)
    assert authority["governing_documents"][0] == "AGENTS.md"
    assert authority["governing_documents"][1] == R4_1_AMENDMENT


def test_r4_1_amendment_owns_authentic_r5_prerequisites() -> None:
    authority = _authority()
    assert R4_1_AMENDMENT in authority["governing_documents"]
    text = (ROOT / R4_1_AMENDMENT).read_text(encoding="utf-8")
    for marker in REQUIRED_R5_PREREQUISITE_MARKERS:
        assert marker in text
    assert "governance/replay_status.jsonl" in text
    assert "root adoption" in text.casefold()
```

Add literal `__cemm_test_inventory__` rows for both tests with:

```python
{
    "activation_phase": "G0",
    "assertion_ref": "assertion:authority-cleanup-classifies-documents-exactly",
    "diagnostic_role": "owner",
    "introduced_by_task": "Authority-Cleanup-Task-1",
    "owner_ref": "governance",
    "source_ast_sha256": "e9f7a6b008392d5d88b6ce4915dc51a3026079ed77bb8e6d03b42e6e0f26e716"
}
```

and:

```python
{
    "activation_phase": "G0",
    "assertion_ref": "assertion:r4-1-amendment-owns-r5-prerequisites",
    "diagnostic_role": "owner",
    "introduced_by_task": "Authority-Cleanup-Task-1",
    "owner_ref": "governance",
    "source_ast_sha256": "be6df0f7f7bb1d9df2d1312888e2ed90f4db25a664d7b0033d3de5fe4727c11c"
}
```

Compute the two content identities from the exact written functions; do not invent them:

```powershell
python -c "import ast,hashlib,pathlib; p=pathlib.Path('tests/test_replay_governance.py'); t=ast.parse(p.read_text(encoding='utf-8')); wanted={'test_authority_cleanup_classifies_every_authority_like_document_once','test_r4_1_amendment_owns_authentic_r5_prerequisites'}; print(*[f'{n.name}={hashlib.sha256(ast.dump(n,annotate_fields=True,include_attributes=False).encode()).hexdigest()}' for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in wanted],sep='\n')"
```

Verify that the printed digests equal the two literal metadata values above before running inventory verification.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
python -m pytest tests/test_replay_governance.py::test_authority_cleanup_classifies_every_authority_like_document_once tests/test_replay_governance.py::test_r4_1_amendment_owns_authentic_r5_prerequisites -q
```

Expected: both fail because the amendment is absent and the current authority map leaves documents unclassified.

- [ ] **Step 3: Create the corrective amendment**

Create `docs/superpowers/specs/2026-08-29-r4-1-data-supervision-corrective-amendment.md` with this exact contract:

```markdown
# R4.1 Data and Supervision Corrective Amendment

**Status:** approved target contract; activation requires fresh admission

This amendment is subordinate only to `hybrid_mvp/AGENTS.md`. Replay status and
admission identities are derived only from
[`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).
It contains no phase promotion. Root adoption remains a separate reviewed act.

## Rejected predecessor strategies

Neither independent per-axis train-set intersection nor one transitive union of
common semantic-target and realization identities is an admissible R4 data
boundary. The first can produce no training rows. The second can place all
semantic rows in training and leave held-out purpose classes semantically empty.

## Partition ownership

Hard grouping is limited to reviewed duplicate-risk lineage such as source-case
lineage, paraphrase/normalization family, mutation lineage, and environment
provenance. Operators, roles, modes, common participants, response actions,
semantic targets, and realization actions are reviewed stratification labels
unless a separately reviewed challenge-holdout contract makes one of them a
holdout identity.

Every purpose class contains semantic evaluation denominators declared by a
reviewed contract. Selection, calibration, and frozen evaluation each contain
semantic expressions and the operator, mode, recursive-topology, abstention,
transition, and realization coverage required for that purpose. Aggregate
corpus coverage cannot substitute for class-local coverage.

Reviewed minima are configuration authority. Unsupported reviewed minima fail
without trimming. A feasibility solver may report infeasibility; it may not
select easier requirements, silently weaken them, or convert nonempty files
into evidence of semantic sufficiency.

## Proposal supervision

Canonical `SemanticExpression` gold and reviewed derivation targets are separate
artifacts. Reviewed derivation supervision is independent of bootstrap output.
Bootstrap proposal or verifier selection may be diagnostic lineage, but it
cannot author semantic-expression gold, derivation gold, abstention gold, model
selection truth, or calibration truth.

An eligible semantic case carries one or more reviewed derivations that compile
independently to its expected expression. A gap case carries a typed abstention
or unresolved target. Multiple derivations may express one canonical meaning;
program identity never becomes meaning identity.

## Realization supervision

R5 requires reviewed ResponseMeaning-to-surface supervision with exact semantic
slots, reference perspective, and literal-copy alignment. The user input
utterance is not a response target. Sentence hashes and collision-prone surface
buckets are diagnostic placeholders and are ineligible for activation.

Round-trip equivalence reconstructs canonical semantic expression plus required
situated qualifiers. Marker, keyword, substring, template-family, or internal-
ref checks cannot establish equivalence.

## R5 prerequisite

R5 source scaffolding may remain fail-closed, but training, selection,
calibration, frozen evaluation, model publication, and runtime activation remain
unavailable until fresh R4 admission authenticates this amendment's partition,
derivation, abstention, and realization contracts.
```

- [ ] **Step 4: Replace the document classification atomically**

Update `docs/DOCUMENT_AUTHORITY.json` so the three classes are disjoint and contain every Markdown file under `docs/` plus `AGENTS.md`, `README.md`, and `INTEGRATION.md`.

The governing list, in precedence order, must be:

```json
[
  "AGENTS.md",
  "docs/superpowers/specs/2026-08-29-r4-1-data-supervision-corrective-amendment.md",
  "docs/superpowers/specs/2026-08-02-hybrid-semantic-algebra-corrective-replay-amendment.md",
  "README.md",
  "INTEGRATION.md",
  "docs/ARCHITECTURE.md",
  "docs/ABI_REGISTRY.md",
  "docs/REPLAY_GOVERNANCE.md",
  "docs/IMPLEMENTATION_PLAN.md",
  "docs/superpowers/specs/2026-07-31-hybrid-mvp-corrective-replay-admission-design.md",
  "docs/superpowers/plans/2026-07-31-hybrid-mvp-corrective-replay-master-plan.md",
  "docs/superpowers/specs/2026-08-13-r5-hard-cut-foundation-design.md",
  "docs/superpowers/specs/2026-08-22-r5-neural-activation-r6-composition-design.md",
  "docs/superpowers/plans/2026-08-22-r5-neural-activation-r6-composition-plan.md"
]
```

Move these files to `superseded_execution_claims` in addition to the already superseded July 29/30 and August 12 final-closeout documents:

```text
docs/superpowers/plans/2026-08-04-hybrid-mvp-completion-critical-path.md
docs/superpowers/plans/2026-08-05-hybrid-mvp-r3-r4-implementation-plan.md
docs/superpowers/specs/2026-08-12-r4-repository-owned-admission-design.md
docs/superpowers/plans/2026-08-12-r4-repository-owned-admission-plan.md
docs/superpowers/specs/2026-08-14-r4-partition-corrective-replay-design.md
docs/superpowers/plans/2026-08-14-r4-partition-corrective-replay-plan.md
```

Set `historical_evidence` to this exact list:

```json
[
  "docs/AUTHORITY_GOVERNANCE.md",
  "docs/COMPARISON.md",
  "docs/EVALUATION_PROTOCOL.md",
  "docs/EVALUATION_REPORT.md",
  "docs/GRAPH_PROGRAM_ABI.md",
  "docs/KNOWN_LIMITATIONS.md",
  "docs/NEURAL_MODEL.md",
  "docs/RUNTIME_AND_EFFECTS.md",
  "docs/RUNTIME_TRACES.md",
  "docs/WORKTREE_INTEGRATION.md",
  "docs/superpowers/plans/2026-07-31-hybrid-mvp-g0-r1-implementation-plan.md",
  "docs/superpowers/plans/2026-08-04-hybrid-mvp-r2-implementation-plan.md",
  "docs/superpowers/plans/2026-08-05-hybrid-mvp-r3-cognition-activation-plan.md",
  "docs/superpowers/plans/2026-08-12-r1-legacy-test-retirement-plan.md",
  "docs/superpowers/plans/2026-08-13-r5-hard-cut-foundation-plan.md",
  "docs/superpowers/plans/2026-08-29-hybrid-authority-cleanup-plan.md",
  "docs/superpowers/progress/2026-08-14-r4-partition-corrective-replay-progress.md",
  "docs/superpowers/progress/2026-08-22-r5-r6-plan-readiness-review.md",
  "docs/superpowers/specs/2026-08-12-r1-legacy-test-retirement-design.md",
  "docs/superpowers/specs/2026-08-29-hybrid-authority-cleanup-design.md",
  "artifacts/"
]
```

Do not move a path into more than one class.

- [ ] **Step 5: Add the amendment pointer to `AGENTS.md`**

In the authority section, state:

```markdown
The approved 2026-08-29 R4.1 data/supervision amendment has precedence over
conflicting partition, feasibility, proposal-gold, realization-target, and
calibration instructions in earlier Hybrid documents. It does not promote a
phase or reactivate a superseded plan.
```

In the forbidden-behavior section, add:

```markdown
- **self-satisfying corpus gates:** required semantic minima are reviewed input;
  a solver cannot derive, trim, or weaken them to make a partition pass;
- **input-as-output supervision:** user input surfaces cannot become response
  realization targets;
- **integrity-only admission:** artifact reconstruction without class-local
  semantic usability and independent gold is insufficient for R5.
```

- [ ] **Step 6: Run the authority tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_replay_governance.py::test_authority_cleanup_classifies_every_authority_like_document_once tests/test_replay_governance.py::test_r4_1_amendment_owns_authentic_r5_prerequisites -q
```

Expected: both pass.

- [ ] **Step 7: Verify the inventory metadata and commit**

Run:

```powershell
python scripts/check_test_inventory.py --phase G0 --source-only
git diff --check
git add AGENTS.md docs/DOCUMENT_AUTHORITY.json docs/superpowers/specs/2026-08-29-r4-1-data-supervision-corrective-amendment.md tests/test_replay_governance.py
git commit -m "docs(hybrid): establish R4.1 supervision authority"
```

Expected: inventory verification exits 0; the commit contains no artifacts, ledger rows, root files, or semantic source.

---

### Task 2: Correct living routing documents and banner historical execution records

**Files:**

- Modify: `tests/test_replay_governance.py:83-125,930-980`
- Modify: `README.md`
- Modify: `INTEGRATION.md`
- Modify: `docs/ARCHITECTURE.md:97-140`
- Modify: `docs/ABI_REGISTRY.md:187-230`
- Modify: `docs/REPLAY_GOVERNANCE.md`
- Modify: `docs/IMPLEMENTATION_PLAN.md`
- Modify: `docs/superpowers/specs/2026-08-22-r5-neural-activation-r6-composition-design.md:1-50,430-470`
- Modify: `docs/superpowers/plans/2026-08-22-r5-neural-activation-r6-composition-plan.md:1-55`
- Modify: superseded and historical banner targets classified in Task 1

- [ ] **Step 1: Write the failing active-instruction and banner tests**

Add:

```python
REJECTED_ACTIVE_INSTRUCTIONS = (
    "builds one global connected-component graph",
    "preserve every exact protected identity from the seven r4 axes as a namespaced leakage hyperedge",
    "candidate minima are derived only from component support",
    "the input surface is the realization target",
)


def test_governing_documents_do_not_prescribe_rejected_r4_r5_paths() -> None:
    authority = _authority()
    for relative in authority["governing_documents"]:
        text = (ROOT / relative).read_text(encoding="utf-8").casefold()
        for rejected in REJECTED_ACTIVE_INSTRUCTIONS:
            assert rejected not in text, (relative, rejected)


def test_superseded_execution_documents_have_prominent_successor_banners() -> None:
    authority = _authority()
    for relative in authority["superseded_execution_claims"]:
        banner = "\n".join((ROOT / relative).read_text(encoding="utf-8").splitlines()[:14])
        assert "superseded" in banner.casefold(), relative
        assert "governance/replay_status.jsonl" in banner, relative
```

Add exact G0 owner metadata rows using these identities:

```python
{
    "tests/test_replay_governance.py::test_governing_documents_do_not_prescribe_rejected_r4_r5_paths": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:governing-documents-reject-r4-r5-regression-paths",
        "diagnostic_role": "owner",
        "introduced_by_task": "Authority-Cleanup-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "f9898c646a8e55425e99b64e9e7db3682897a4f69a4c06290ae32790cc1fdf7a"
    },
    "tests/test_replay_governance.py::test_superseded_execution_documents_have_prominent_successor_banners": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:superseded-documents-have-successor-banners",
        "diagnostic_role": "owner",
        "introduced_by_task": "Authority-Cleanup-Task-2",
        "owner_ref": "governance",
        "source_ast_sha256": "5ed3abe50f1d59971eb16ad611af1ca8a7b3c30bd88ac11d89f8f2c1bde9c14c"
    }
}
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
python -m pytest tests/test_replay_governance.py::test_governing_documents_do_not_prescribe_rejected_r4_r5_paths tests/test_replay_governance.py::test_superseded_execution_documents_have_prominent_successor_banners -q
```

Expected: the architecture/global-union wording and missing historical banners fail.

- [ ] **Step 3: Correct the living R4 architecture and ABI wording**

Replace `docs/ARCHITECTURE.md`'s global connected-component paragraph with:

```markdown
R4.1 separates duplicate-risk grouping from semantic stratification. Reviewed
lineage groups prevent source, paraphrase, normalization, mutation and
environment duplicates from crossing a protected boundary. Operators, roles,
modes, common participants, response actions, semantic targets and realization
actions remain class-local coverage labels unless an explicit challenge-holdout
contract promotes one identity into a holdout key. Every purpose class proves
its own semantic denominators. Unsupported reviewed minima fail rather than
being trimmed.

Expected semantic expressions, reviewed derivations, typed abstentions and
reviewed response surfaces are independently authored contracts. Runtime or
bootstrap proposal output remains diagnostic lineage and cannot become gold.
```

In `docs/ABI_REGISTRY.md`, replace “R3–R4 active target ABI allocation” with “R3 implemented and R4.1 target ABI allocation”. Add an `Admission` column whose values are derived descriptions, not copied ledger status:

```text
implemented predecessor
target; requires fresh R4.1 admission
future owner; unavailable before R4.1
```

Register target contracts for reviewed derivation supervision, purpose-class membership, class-local semantic sufficiency, and reviewed response-realization supervision. Do not assign an ABI version unless a Python owner, strict decoder, and validator already exist; describe those missing contracts as required pre-ABI owners.

- [ ] **Step 4: Correct current routing pages**

Make `README.md`, `INTEGRATION.md`, `docs/REPLAY_GOVERNANCE.md`, and `docs/IMPLEMENTATION_PLAN.md` all contain:

```markdown
Current replay status and exact admission identities are derived only from
[`governance/replay_status.jsonl`](governance/replay_status.jsonl). This page
does not copy or promote phase status.
```

Adjust relative links where the file is under `docs/`.

Each page must route the next work to the August 29 amendment and state that:

```markdown
R5 training, selection, calibration, frozen evaluation and realization
activation are unavailable until a fresh R4.1 admission proves meaningful
purpose-class semantic coverage and independent derivation/realization gold.
```

Remove copied status ranges, admission run refs, worktree paths, and statements that repository-owned artifact integrity alone closes R4.

- [ ] **Step 5: Make the R5/R6 package explicitly conditional**

Add this banner within the first 14 lines of both August 22 files:

```markdown
> **Conditional target:** The August 29 R4.1 data/supervision amendment has
> precedence. No training, model selection, calibration, frozen evaluation,
> realization publication or activation task in this document is executable
> until fresh R4.1 admission authenticates semantically useful purpose classes,
> independent reviewed derivations and reviewed response surfaces.
```

Preserve the five-owner, CPU-reference, purpose-capability, single-stack and dependency-budget constraints.

- [ ] **Step 6: Banner superseded documents**

Insert this banner immediately after each superseded document's title, adjusting the named reason where appropriate:

```markdown
> **Superseded execution evidence:** This document is retained for forensic
> history only. It cannot authorize current work or phase status. Current status
> is derived from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).
> The August 29 R4.1 data/supervision amendment supersedes conflicting
> partition, feasibility, gold and realization instructions.
```

For completed historical plans and progress reports, use:

```markdown
> **Completed historical evidence:** This document records an earlier tranche;
> it is not an executable current plan and owns no phase status. Current status
> is derived from
> [`governance/replay_status.jsonl`](../../../governance/replay_status.jsonl).
```

Apply the completed banner to:

```text
docs/superpowers/plans/2026-07-31-hybrid-mvp-g0-r1-implementation-plan.md
docs/superpowers/plans/2026-08-04-hybrid-mvp-r2-implementation-plan.md
docs/superpowers/plans/2026-08-05-hybrid-mvp-r3-cognition-activation-plan.md
docs/superpowers/plans/2026-08-13-r5-hard-cut-foundation-plan.md
docs/superpowers/plans/2026-08-12-r1-legacy-test-retirement-plan.md
docs/superpowers/specs/2026-08-12-r1-legacy-test-retirement-design.md
docs/superpowers/progress/2026-08-14-r4-partition-corrective-replay-progress.md
docs/superpowers/progress/2026-08-22-r5-r6-plan-readiness-review.md
docs/superpowers/specs/2026-08-29-hybrid-authority-cleanup-design.md
docs/superpowers/plans/2026-08-29-hybrid-authority-cleanup-plan.md
```

Do not alter historical checkboxes or rewrite their task bodies as if execution happened differently.

- [ ] **Step 7: Run the focused routing tests and verify GREEN**

Run:

```powershell
python -m pytest tests/test_replay_governance.py::test_document_authority_is_scoped_and_classifications_are_exact tests/test_replay_governance.py::test_governing_documents_do_not_prescribe_rejected_r4_r5_paths tests/test_replay_governance.py::test_superseded_execution_documents_have_prominent_successor_banners -q
```

Expected: all pass.

- [ ] **Step 8: Verify metadata and commit**

Run:

```powershell
python scripts/check_test_inventory.py --phase G0 --source-only
git diff --check
git add README.md INTEGRATION.md AGENTS.md docs tests/test_replay_governance.py
git commit -m "docs(hybrid): route execution through R4.1 authority"
```

Expected: only documentation, authority JSON and the governance test owner are committed.

---

### Task 3: Make placeholder comments and docstrings truthful

**Files:**

- Modify: `tests/test_replay_governance.py`
- Modify: `src/cemm_authoritative_hybrid/realization.py:1-16,148-170,370-384`
- Modify: `src/cemm_authoritative_hybrid/training.py:528-536,757-770,1025-1047`

- [ ] **Step 1: Write the failing comment-truth test**

Add:

```python
def test_r5_placeholder_docstrings_do_not_claim_admitted_semantics() -> None:
    realization = (
        ROOT / "src/cemm_authoritative_hybrid/realization.py"
    ).read_text(encoding="utf-8")
    training = (
        ROOT / "src/cemm_authoritative_hybrid/training.py"
    ).read_text(encoding="utf-8")
    assert "marker-based diagnostic" in realization
    assert "does not establish canonical-expression equivalence" in realization
    assert "collision-prone diagnostic bucket" in training
    assert "not reviewed derivation supervision" in training
    assert "input utterance is not an authorized response target" in training
```

Add its exact G0 owner metadata:

```python
{
    "activation_phase": "G0",
    "assertion_ref": "assertion:r5-placeholder-docstrings-are-truthful",
    "diagnostic_role": "owner",
    "introduced_by_task": "Authority-Cleanup-Task-3",
    "owner_ref": "governance",
    "source_ast_sha256": "f0c5dddedb7c072319c0e0be7a494b523ce0cd4a829756d9552c23f9969bca39"
}
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -m pytest tests/test_replay_governance.py::test_r5_placeholder_docstrings_do_not_claim_admitted_semantics -q
```

Expected: fail because the source currently calls marker checks independent equivalence and does not identify the hash bucket as a placeholder.

- [ ] **Step 3: Correct `realization.py` docstrings without changing executable statements**

Replace the module docstring with:

```python
"""Pre-R5 constrained-realization scaffold with marker-based diagnostic checks.

The module contains historical neural and safe-realizer experiments. Its
current verifier checks bounded surface markers and leakage conditions; it does
not reconstruct Program ABI 2 through VERIFY and does not establish canonical-
expression equivalence. The R5 realization owner remains unadmitted.
"""
```

Replace the `RealizationVerifier` docstring with:

```python
"""Run the bounded pre-R5 marker-based diagnostic.

This check can reject empty, leaking, polarity-, modality-, status- or
perspective-inconsistent surfaces. It does not establish canonical-expression
equivalence and cannot authorize normal release realization.
"""
```

Replace the `NeuralConstrainedRealizer` opening docstring with:

```python
"""Historical constrained-realizer scaffold, unavailable for R5 activation.

The decoder and marker-based diagnostic provide weight-use and failure-path
evidence only. They do not preserve the complete Response Meaning ABI 2 or
prove a semantic round trip.
"""
```

Do not rename classes or change branches, constants, return values, or imports in this tranche.

- [ ] **Step 4: Correct `training.py` docstrings without changing training behavior**

Replace `_surface_to_target`'s docstring with:

```python
"""Map a surface to a collision-prone diagnostic bucket.

This pre-R5 helper is neither reversible token supervision nor a dynamic
pointer target. It is ineligible for model publication and remains visible so
the R5 repair cannot mistake the scaffold for reviewed realization gold.
"""
```

Expand `_selected_program_actions`'s docstring to:

```python
"""Return verifier-selected actions for diagnostic replay.

The sequence is runtime/bootstrap lineage, not reviewed derivation supervision,
and cannot become release proposal gold without an independent reviewed
derivation contract.
"""
```

Change `ReleaseRealizerTrainer.fit`'s docstring to:

```python
"""Exercise the pre-admission trainer on an authenticated R4 snapshot.

Snapshot authentication does not authorize the current labels: the input
utterance is not an authorized response target. R5 activation remains blocked
until reviewed ResponseMeaning-to-surface supervision replaces this scaffold.
"""
```

- [ ] **Step 5: Prove the diff is comment/docstring-only**

Run:

```powershell
python -c "import ast,pathlib; files=['src/cemm_authoritative_hybrid/realization.py','src/cemm_authoritative_hybrid/training.py']; [ast.parse(pathlib.Path(f).read_text(encoding='utf-8')) for f in files]; print('parsed',len(files))"
git diff --word-diff=porcelain -- src/cemm_authoritative_hybrid/realization.py src/cemm_authoritative_hybrid/training.py
```

Inspect the diff. Expected: only string literals used as docstrings change; no executable statement changes.

- [ ] **Step 6: Run the test and relevant import tests**

Run:

```powershell
python -m pytest tests/test_replay_governance.py::test_r5_placeholder_docstrings_do_not_claim_admitted_semantics tests/test_lazy_package_imports.py -q
```

Expected: pass.

- [ ] **Step 7: Verify metadata and commit**

Run:

```powershell
python scripts/check_test_inventory.py --phase G0 --source-only
git diff --check
git add src/cemm_authoritative_hybrid/realization.py src/cemm_authoritative_hybrid/training.py tests/test_replay_governance.py
git commit -m "docs(r5): mark neural scaffolds unadmitted"
```

---

### Task 4: Quarantine obsolete self-mutating CI workflows

**Files:**

- Modify: `tests/test_replay_governance.py`
- Delete: the ten workflow files listed in “Workflow removals”

- [ ] **Step 1: Write the failing workflow-safety test**

Add:

```python
def test_active_hybrid_workflows_cannot_rewrite_governed_source() -> None:
    workflows = ROOT.parent / ".github/workflows"
    forbidden = (
        "contents: write",
        "git push",
        ".github/r3_close_apply.py",
        "base64 --decode",
        "frombase64string",
    )
    offenders: list[tuple[str, str]] = []
    for path in sorted((*workflows.glob("*.yml"), *workflows.glob("*.yaml"))):
        text = path.read_text(encoding="utf-8").casefold()
        for marker in forbidden:
            if marker in text:
                offenders.append((path.name, marker))
    assert not offenders, offenders
```

Add exact G0 owner metadata:

```python
{
    "activation_phase": "G0",
    "assertion_ref": "assertion:active-hybrid-workflows-cannot-rewrite-source",
    "diagnostic_role": "owner",
    "introduced_by_task": "Authority-Cleanup-Task-4",
    "owner_ref": "governance",
    "source_ast_sha256": "0c03ae5af33f1797613c3120bb16e31a647afb5855dbbb9bf885c03784b1cea3"
}
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
python -m pytest tests/test_replay_governance.py::test_active_hybrid_workflows_cannot_rewrite_governed_source -q
```

Expected: fail with write-enabled R3 closeout workflows.

- [ ] **Step 3: Verify the deletion targets exactly**

Run from the worktree root:

```powershell
$targets = @(
  '.github/workflows/hybrid-mvp-r3-r4-audit.yml',
  '.github/workflows/r3-lineage-closeout.yml',
  '.github/workflows/r3-migration-snapshot.yml',
  '.github/workflows/r3-postverify-close-v2.yml',
  '.github/workflows/r3-postverify-close.yml',
  '.github/workflows/r3-self-close-literal-fix.yml',
  '.github/workflows/r3-self-close.yml',
  '.github/workflows/r3-simulate-probe.yml',
  '.github/workflows/r3-structural-migration.yml',
  '.github/workflows/r4-phase-episodes-diagnostic.yml'
)
$missing = @($targets | Where-Object { -not (Test-Path -LiteralPath $_) })
if ($missing.Count) { throw "missing workflow target(s): $($missing -join ', ')" }
git status --short
```

Expected: all ten exact tracked targets exist before deletion and the worktree has no unrelated changes.

- [ ] **Step 4: Delete only the verified workflow targets**

Use `apply_patch` to delete the ten files. Do not recursively remove `.github/workflows` and do not delete helpers or artifacts outside the exact list.

- [ ] **Step 5: Run the workflow test and verify GREEN**

Run from `hybrid_mvp/`:

```powershell
python -m pytest tests/test_replay_governance.py::test_active_hybrid_workflows_cannot_rewrite_governed_source -q
```

Expected: pass.

- [ ] **Step 6: Verify deletion scope and commit**

Run the deletion-scope checks from the worktree root:

```powershell
$deleted = @(git diff --name-only --diff-filter=D)
if ($deleted.Count -ne 10) { throw "unexpected deletion count: $($deleted.Count)" }
if (@($deleted | Where-Object { $_ -notlike '.github/workflows/*' }).Count) { throw 'deletion escaped workflow directory' }
git diff --check
```

Expected: exactly ten workflow deletions and no deletion outside `.github/workflows/`.

Run this inventory check from `hybrid_mvp/`:

```powershell
python scripts/check_test_inventory.py --phase G0 --source-only
```

Then commit from the worktree root:

```powershell
git add .github/workflows hybrid_mvp/tests/test_replay_governance.py
git commit -m "ci: remove obsolete self-mutating replay workflows"
```

Expected: exactly ten workflow deletions plus the governance test change.

---

### Task 5: Refresh deterministic metadata and verify the complete cleanup boundary

**Files:**

- Modify only if required by existing deterministic owner: `governance/test_inventory.json`
- Modify only if inventory bytes changed: `docs/DOCUMENT_AUTHORITY.json`
- Modify if the focused suite exposes its stale authority assertion: `tests/test_r3_plan_contract.py`
- Verify: all files changed since `0e5cc801`

- [ ] **Step 1: Verify no computed metadata token remains**

Run from `hybrid_mvp/`:

```powershell
rg -n "UNRESOLVED_METADATA_TOKEN|UNRESOLVED_REQUIREMENT_MARKER" tests/test_replay_governance.py docs/superpowers/specs/2026-08-29-r4-1-data-supervision-corrective-amendment.md
```

Expected: no matches, exit code 1 from `rg` because nothing matched.

- [ ] **Step 2: Run source-only inventory checks twice**

Run:

```powershell
$before = (Get-FileHash governance/test_inventory.json -Algorithm SHA256).Hash
python scripts/check_test_inventory.py --phase G0 --source-only
python scripts/check_test_inventory.py --phase R4 --source-only
python scripts/check_test_inventory.py --phase R5 --source-only
$middle = (Get-FileHash governance/test_inventory.json -Algorithm SHA256).Hash
python scripts/check_test_inventory.py --phase G0 --source-only
$after = (Get-FileHash governance/test_inventory.json -Algorithm SHA256).Hash
if ($before -ne $middle -or $middle -ne $after) { throw 'inventory verifier mutated immutable inventory' }
```

Expected: all checks exit 0 and the inventory hash remains identical.

- [ ] **Step 3: Run the focused governance and structure suite**

Run:

```powershell
python -m pytest tests/test_replay_governance.py tests/test_r3_plan_contract.py tests/test_r4_structure.py tests/test_lazy_package_imports.py -q
```

Expected: zero failures, errors, skips, xfails, or xpasses.

- [ ] **Step 4: Verify immutable scopes are byte-unchanged**

Run from the repository worktree root:

```powershell
$forbidden = @(git diff --name-only 0e5cc801..HEAD -- AGENTS.md ARCHITECTURE.md RUNTIME_ARCHITECTURE.md DATA_ARCHITECTURE.md runtime-core-loop.md CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md NATIVE_SEMANTIC_SPINE_IMPLEMENTATION_PLAN.md NATIVE_SEMANTIC_SPINE_IMPLEMENTATION_STATUS.md V1_ACCEPTANCE.md hybrid_mvp/artifacts hybrid_mvp/governance/replay_status.jsonl)
if ($forbidden.Count) { throw "immutable scope changed: $($forbidden -join ', ')" }
```

Expected: no paths.

- [ ] **Step 5: Verify the complete changed-path allowlist**

Run:

```powershell
$changed = @(git diff --name-only 0e5cc801..HEAD)
$bad = @($changed | Where-Object {
  $_ -notlike 'hybrid_mvp/AGENTS.md' -and
  $_ -notlike 'hybrid_mvp/README.md' -and
  $_ -notlike 'hybrid_mvp/INTEGRATION.md' -and
  $_ -notlike 'hybrid_mvp/docs/*' -and
  $_ -notlike 'hybrid_mvp/src/cemm_authoritative_hybrid/realization.py' -and
  $_ -notlike 'hybrid_mvp/src/cemm_authoritative_hybrid/training.py' -and
  $_ -notlike 'hybrid_mvp/tests/test_replay_governance.py' -and
  $_ -notlike 'hybrid_mvp/tests/test_r3_plan_contract.py' -and
  $_ -notlike '.github/workflows/*'
})
if ($bad.Count) { throw "path outside cleanup boundary: $($bad -join ', ')" }
```

Expected: no out-of-bound paths.

- [ ] **Step 6: Run whitespace, JSON and Python syntax checks**

Run:

```powershell
git diff --check 0e5cc801..HEAD
python -m json.tool docs/DOCUMENT_AUTHORITY.json > $null
python -m py_compile tests/test_replay_governance.py src/cemm_authoritative_hybrid/realization.py src/cemm_authoritative_hybrid/training.py
```

Expected: all commands exit 0.

- [ ] **Step 7: Commit deterministic metadata only if an owner changed it**

Run:

```powershell
git status --short
```

If the status is clean, create no empty commit. If an existing deterministic owner legitimately updated `governance/test_inventory.json` and its matching `docs/DOCUMENT_AUTHORITY.json` pin, verify the second run was byte-stable and commit exactly those two files:

```powershell
git add governance/test_inventory.json docs/DOCUMENT_AUTHORITY.json
git commit -m "chore(governance): refresh cleanup inventory pin"
```

- [ ] **Step 8: Record final evidence without promoting replay status**

Run:

```powershell
git status --short
git log --oneline 0e5cc801..HEAD
git diff --stat 0e5cc801..HEAD
```

Expected: clean worktree; one design commit plus the implementation commits above; no generated R4 artifact, replay-ledger, root-runtime, model, schema, corpus, or semantic behavior change.

The final evidence must state explicitly that the replay ledger and generated
R4 artifacts are byte-unchanged and that root runtime documents and source are
byte-unchanged.

Do not append a replay-status row, publish an R4 artifact, train a model, merge to `main`, or delete remote refs in this plan.
