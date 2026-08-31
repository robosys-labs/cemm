# R4.1 Assistant Pre-Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an offline advisory pre-review ledger for R4.1 that quarantines evidence problems, recommends only bounded non-authoritative actions, and preserves careful individual curation.

**Architecture:** Add one script-side module that reuses `ReviewSession`, `GuidedReviewService`, `_json_bytes`, and existing R4.1 indexes. The module produces inert draft artifacts under `hybrid_mvp/artifacts/review_drafts/r4_1/` and never mutates `SELECTION_WORKING.json` or `SELECTION.json`.

**Tech Stack:** Python standard library, existing CEMM canonical JSON helpers, existing R4.1 review-session/guided-review scripts, pytest.

---

## File Structure

- Create `hybrid_mvp/scripts/r4_1_pre_review.py`: advisory preflight, recommendation records, cohort builder, summary/report writer, and CLI entry point.
- Create `hybrid_mvp/tests/test_r4_pre_review.py`: test-first coverage for evidence mismatch quarantine, advisory action safety, deterministic output, conservative cohorts, and runtime isolation.
- Modify `hybrid_mvp/artifacts/review_inputs/r4_1/README.md`: document the optional advisory pre-review command and authority boundary.
- Do not modify runtime modules under `hybrid_mvp/src/cemm_authoritative_hybrid/`.
- Do not modify `SELECTION_TEMPLATE.json`, `SELECTION_WORKING.json`, or `SELECTION.json` from the pre-review command.

## Task 1: Evidence Preflight Contract

**Files:**
- Create: `hybrid_mvp/tests/test_r4_pre_review.py`
- Create: `hybrid_mvp/scripts/r4_1_pre_review.py`

- [x] **Step 1: Write failing preflight tests**

Add these tests to `hybrid_mvp/tests/test_r4_pre_review.py`:

```python
"""Advisory R4.1 assistant pre-review ledger."""
from __future__ import annotations

from pathlib import Path

from scripts.r4_1_pre_review import (
    RecommendationClass,
    preflight_designation_source,
)

ROOT = Path(__file__).parents[1]


def test_preflight_quarantines_source_order_span_mismatch() -> None:
    row = {
        "source_case_ref": "case:source-order",
        "surface": "The server is offline. You said goodbye.",
        "candidate_output": "The server is offline. You said goodbye.",
        "resulting_scenario_row": {
            "surface_examples": ["goodbye. the server is offline."]
        },
        "candidate_bindings": [
            {
                "binding_ref": "binding:farewell",
                "surface": "goodbye",
                "start": 0,
                "end": 7,
                "unit_refs": ["unit:goodbye"],
                "designation_fact_ref": "fact:farewell",
                "candidate_target_ref": "event:farewell",
            },
            {
                "binding_ref": "binding:server",
                "surface": "server",
                "start": 13,
                "end": 19,
                "unit_refs": ["unit:server"],
                "designation_fact_ref": "fact:server",
                "candidate_target_ref": "entity:server",
            },
        ],
    }

    result = preflight_designation_source(row)

    assert result.recommendation_class == RecommendationClass.BLOCKED_EVIDENCE_MISMATCH
    assert result.action is None
    assert any(issue.issue_kind == "span_text_mismatch" for issue in result.issues)
    assert any(issue.issue_kind == "surface_example_order_mismatch" for issue in result.issues)


def test_preflight_accepts_matching_designation_geometry() -> None:
    row = {
        "source_case_ref": "case:matching",
        "surface": "goodbye. the server is offline.",
        "candidate_output": "goodbye. the server is offline.",
        "resulting_scenario_row": {
            "surface_examples": ["goodbye. the server is offline."]
        },
        "candidate_bindings": [
            {
                "binding_ref": "binding:farewell",
                "surface": "goodbye",
                "start": 0,
                "end": 7,
                "unit_refs": ["unit:goodbye"],
                "designation_fact_ref": "fact:farewell",
                "candidate_target_ref": "event:farewell",
            },
            {
                "binding_ref": "binding:server",
                "surface": "server",
                "start": 13,
                "end": 19,
                "unit_refs": ["unit:server"],
                "designation_fact_ref": "fact:server",
                "candidate_target_ref": "entity:server",
            },
            {
                "binding_ref": "binding:offline",
                "surface": "offline",
                "start": 23,
                "end": 30,
                "unit_refs": ["unit:offline"],
                "designation_fact_ref": "fact:offline",
                "candidate_target_ref": "value:offline",
            },
        ],
    }

    result = preflight_designation_source(row)

    assert result.recommendation_class is None
    assert result.action is None
    assert result.issues == ()
```

- [x] **Step 2: Run the tests to verify they fail**

Run:

```powershell
python -m pytest hybrid_mvp/tests/test_r4_pre_review.py -q
```

Expected: fail with `ModuleNotFoundError` or missing `preflight_designation_source`.

- [x] **Step 3: Implement minimal preflight types and span checks**

Create `hybrid_mvp/scripts/r4_1_pre_review.py` with:

```python
#!/usr/bin/env python3
"""Build inert advisory pre-review records for R4.1 accountable review."""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class RecommendationClass(StrEnum):
    APPROVE_CANDIDATE = "approve_candidate"
    REJECT_AND_REPAIR = "reject_and_repair"
    NEEDS_INDIVIDUAL_REVIEW = "needs_individual_review"
    BLOCKED_EVIDENCE_MISMATCH = "blocked_evidence_mismatch"
    BLOCKED_INAPPLICABLE = "blocked_inapplicable"
    DEFER_UNTIL_PREREQUISITE = "defer_until_prerequisite"


@dataclass(frozen=True, slots=True)
class EvidenceIssue:
    issue_kind: str
    message: str
    ref: str | None = None


@dataclass(frozen=True, slots=True)
class PreflightResult:
    recommendation_class: RecommendationClass | None
    issues: tuple[EvidenceIssue, ...]
    action: object | None = None


def _nonempty_text(value: object) -> str | None:
    return value if type(value) is str and value.strip() else None


def _first_surface_example(row: Mapping[str, object]) -> str | None:
    scenario = row.get("resulting_scenario_row")
    if not isinstance(scenario, Mapping):
        return None
    examples = scenario.get("surface_examples")
    if type(examples) is not list or not examples:
        return None
    return _nonempty_text(examples[0])


def _binding_ref(binding: Mapping[str, object]) -> str | None:
    for key in ("binding_ref", "candidate_ref", "designation_fact_ref"):
        ref = binding.get(key)
        if type(ref) is str and ref:
            return ref
    return None


def preflight_designation_source(row: Mapping[str, object]) -> PreflightResult:
    issues: list[EvidenceIssue] = []
    surface = _nonempty_text(row.get("surface"))
    candidate = _nonempty_text(row.get("candidate_output"))
    example = _first_surface_example(row)

    if surface is None:
        issues.append(EvidenceIssue("missing_surface", "designation row lacks exact surface"))
    if surface is not None and candidate is not None and candidate != surface:
        issues.append(EvidenceIssue("candidate_output_mismatch", "candidate output differs from designation surface"))
    if surface is not None and example is not None and example != surface:
        issues.append(EvidenceIssue("surface_example_order_mismatch", "surface example differs from designation surface"))

    bindings = row.get("candidate_bindings")
    if type(bindings) not in {list, tuple}:
        issues.append(EvidenceIssue("invalid_candidate_bindings", "candidate bindings are not a bounded sequence"))
    elif surface is not None:
        for binding in bindings:
            if not isinstance(binding, Mapping):
                issues.append(EvidenceIssue("invalid_binding", "candidate binding is not an object"))
                continue
            start = binding.get("start")
            end = binding.get("end")
            expected = binding.get("surface")
            ref = _binding_ref(binding)
            if (
                type(start) is not int
                or type(end) is not int
                or type(expected) is not str
                or start < 0
                or end < start
                or end > len(surface)
            ):
                issues.append(EvidenceIssue("invalid_span", "candidate binding span is outside the surface", ref))
                continue
            if surface[start:end] != expected:
                issues.append(EvidenceIssue("span_text_mismatch", "candidate binding span text differs from exact surface", ref))

    if issues:
        return PreflightResult(
            recommendation_class=RecommendationClass.BLOCKED_EVIDENCE_MISMATCH,
            issues=tuple(issues),
        )
    return PreflightResult(recommendation_class=None, issues=())
```

- [x] **Step 4: Run the focused tests**

Run:

```powershell
python -m pytest hybrid_mvp/tests/test_r4_pre_review.py -q
```

Expected: pass.

- [x] **Step 5: Commit Task 1**

Run:

```powershell
git add -- hybrid_mvp/scripts/r4_1_pre_review.py hybrid_mvp/tests/test_r4_pre_review.py
git commit -m "test(r4): quarantine pre-review evidence mismatches"
```

## Task 2: Advisory Record Builder

**Files:**
- Modify: `hybrid_mvp/scripts/r4_1_pre_review.py`
- Modify: `hybrid_mvp/tests/test_r4_pre_review.py`

- [x] **Step 1: Add tests for deterministic advisory records and no mutation**

Append:

```python
import hashlib

from scripts.build_r4_1_review_selection import build_selection_template_bytes
from scripts.build_r4_1_review_worksheets import build_review_worksheet_draft
from scripts.r4_1_pre_review import build_pre_review_records
from scripts.r4_1_review_session import ReviewPaths, ReviewSession


def _review_paths(tmp_path: Path) -> ReviewPaths:
    draft = tmp_path / "draft"
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    build_review_worksheet_draft(repository_root=ROOT, output_root=draft)
    template_path = inputs / "SELECTION_TEMPLATE.json"
    template_path.write_bytes(build_selection_template_bytes(repository_root=ROOT, draft_root=draft))
    return ReviewPaths(
        repository_root=ROOT,
        draft_root=draft,
        template_path=template_path,
        working_path=inputs / "SELECTION_WORKING.json",
        journal_path=inputs / "REVIEW_ACTIONS.jsonl",
        export_path=inputs / "SELECTION.json",
    )


def test_pre_review_records_are_deterministic_and_inert(tmp_path: Path) -> None:
    paths = _review_paths(tmp_path)
    session = ReviewSession.open(paths)
    before = paths.working_path.exists(), paths.export_path.exists()

    first = build_pre_review_records(session)
    second = build_pre_review_records(ReviewSession.open(paths))

    assert [record.record_ref for record in first] == [record.record_ref for record in second]
    assert [record.to_json() for record in first] == [record.to_json() for record in second]
    assert len(first) == 1056
    assert before == (paths.working_path.exists(), paths.export_path.exists())
    assert not paths.working_path.exists()
    assert not paths.export_path.exists()
    assert hashlib.sha256(repr(first[0].to_json()).encode("utf-8")).hexdigest()
```

- [x] **Step 2: Run the new test to verify it fails**

Run:

```powershell
python -m pytest hybrid_mvp/tests/test_r4_pre_review.py::test_pre_review_records_are_deterministic_and_inert -q
```

Expected: fail with missing `build_pre_review_records`.

- [x] **Step 3: Add record dataclass and item loop**

Extend `hybrid_mvp/scripts/r4_1_pre_review.py`:

```python
import copy
import hashlib
import json

from cemm_authoritative_hybrid.canonical import stable_ref
from scripts.r4_1_guided_review import GuidedReviewService
from scripts.r4_1_review_session import ReviewAction, ReviewSession


MAX_PRE_REVIEW_RECORDS = 2048


@dataclass(frozen=True, slots=True)
class PreReviewRecord:
    record_ref: str
    item_ref: str
    phase: str
    row_kind: str
    source_ref: str
    recommendation_class: RecommendationClass
    rationale: str
    confidence: str
    action: Mapping[str, object] | None
    issues: tuple[EvidenceIssue, ...]
    cohort_eligible: bool

    def to_json(self) -> dict[str, object]:
        return {
            "record_ref": self.record_ref,
            "item_ref": self.item_ref,
            "phase": self.phase,
            "row_kind": self.row_kind,
            "source_ref": self.source_ref,
            "recommendation_class": self.recommendation_class.value,
            "rationale": self.rationale,
            "confidence": self.confidence,
            "action": copy.deepcopy(dict(self.action)) if self.action is not None else None,
            "issues": [
                {"issue_kind": issue.issue_kind, "message": issue.message, "ref": issue.ref}
                for issue in self.issues
            ],
            "cohort_eligible": self.cohort_eligible,
        }


def _json_digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _action_to_wire(action: ReviewAction) -> dict[str, object]:
    selected = action.selected_value
    if isinstance(selected, tuple):
        selected = list(selected)
    return {
        "action_kind": action.action_kind,
        "target_refs": list(action.target_refs),
        "selected_value": copy.deepcopy(selected),
    }


def _source_ref(item: Mapping[str, object]) -> str:
    source = item.get("technical_evidence", {}).get("source") if isinstance(item.get("technical_evidence"), Mapping) else None
    if isinstance(source, Mapping):
        for key in ("row_ref", "source_case_ref", "family_ref", "cohort_ref"):
            ref = source.get(key)
            if type(ref) is str and ref:
                return ref
    return str(item["item_ref"])


def _record(
    *,
    item: Mapping[str, object],
    recommendation_class: RecommendationClass,
    rationale: str,
    confidence: str,
    action: Mapping[str, object] | None,
    issues: tuple[EvidenceIssue, ...] = (),
    cohort_eligible: bool = False,
) -> PreReviewRecord:
    source_ref = _source_ref(item)
    material = {
        "item_ref": item["item_ref"],
        "phase": item["phase"],
        "row_kind": item["row_kind"],
        "source_ref": source_ref,
        "recommendation_class": recommendation_class.value,
        "action": action,
        "issues": [
            {"issue_kind": issue.issue_kind, "message": issue.message, "ref": issue.ref}
            for issue in issues
        ],
    }
    return PreReviewRecord(
        record_ref=stable_ref("r4_1_pre_review_record", material),
        item_ref=str(item["item_ref"]),
        phase=str(item["phase"]),
        row_kind=str(item["row_kind"]),
        source_ref=source_ref,
        recommendation_class=recommendation_class,
        rationale=rationale,
        confidence=confidence,
        action=copy.deepcopy(action),
        issues=issues,
        cohort_eligible=cohort_eligible,
    )


def _recommend_item(service: GuidedReviewService, item: Mapping[str, object]) -> PreReviewRecord:
    source = item.get("technical_evidence", {}).get("source") if isinstance(item.get("technical_evidence"), Mapping) else None
    if item["phase"] == "designation" and isinstance(source, Mapping):
        preflight = preflight_designation_source(source)
        if preflight.recommendation_class is not None:
            return _record(
                item=item,
                recommendation_class=preflight.recommendation_class,
                rationale="Exact designation source geometry is not internally reviewable.",
                confidence="blocked",
                action=None,
                issues=preflight.issues,
            )
    if item["phase"] == "designation" and item.get("cohort") is None:
        return _record(
            item=item,
            recommendation_class=RecommendationClass.NEEDS_INDIVIDUAL_REVIEW,
            rationale="Designation exceptions and case-local designation decisions require individual curation.",
            confidence="human_required",
            action=None,
        )
    if item["phase"] in {"structural", "recipe"}:
        return _record(
            item=item,
            recommendation_class=RecommendationClass.NEEDS_INDIVIDUAL_REVIEW,
            rationale="Structural and recipe choices affect R4/R5 authority flow and require direct reviewer judgment.",
            confidence="human_required",
            action=None,
        )
    if item["phase"] == "purpose":
        return _record(
            item=item,
            recommendation_class=RecommendationClass.NEEDS_INDIVIDUAL_REVIEW,
            rationale="Purpose assignment controls leakage and must remain curated until a separate deterministic policy is reviewed.",
            confidence="human_required",
            action=None,
        )
    return _record(
        item=item,
        recommendation_class=RecommendationClass.NEEDS_INDIVIDUAL_REVIEW,
        rationale="No advisory recommendation is available for this item kind.",
        confidence="human_required",
        action=None,
    )


def build_pre_review_records(session: ReviewSession) -> tuple[PreReviewRecord, ...]:
    service = GuidedReviewService(session)
    records = [_recommend_item(service, item) for item in service.iter_current_items()]
    if len(records) > MAX_PRE_REVIEW_RECORDS:
        raise ValueError("pre-review record count exceeds bound")
    return tuple(records)
```

- [x] **Step 4: Run the focused test**

Run:

```powershell
python -m pytest hybrid_mvp/tests/test_r4_pre_review.py::test_pre_review_records_are_deterministic_and_inert -q
```

Expected: pass with 1,056 inert records.

- [x] **Step 5: Commit Task 2**

Run:

```powershell
git add -- hybrid_mvp/scripts/r4_1_pre_review.py hybrid_mvp/tests/test_r4_pre_review.py
git commit -m "feat(r4): build advisory pre-review records"
```

## Task 3: Conservative Cohorts and Output Files

**Files:**
- Modify: `hybrid_mvp/scripts/r4_1_pre_review.py`
- Modify: `hybrid_mvp/tests/test_r4_pre_review.py`

- [ ] **Step 1: Add tests for output determinism and conservative cohorts**

Append:

```python
from scripts.r4_1_pre_review import build_pre_review_cohorts, write_pre_review_outputs


def test_pre_review_cohorts_exclude_human_required_records(tmp_path: Path) -> None:
    paths = _review_paths(tmp_path)
    records = build_pre_review_records(ReviewSession.open(paths))

    cohorts = build_pre_review_cohorts(records)

    assert all(cohort["recommendation_class"] == "approve_candidate" for cohort in cohorts)
    assert all(1 <= len(cohort["member_record_refs"]) <= 512 for cohort in cohorts)
    human_required = {
        record.record_ref
        for record in records
        if record.recommendation_class == RecommendationClass.NEEDS_INDIVIDUAL_REVIEW
    }
    assert not any(human_required.intersection(cohort["member_record_refs"]) for cohort in cohorts)


def test_write_pre_review_outputs_is_deterministic_and_does_not_touch_selection(tmp_path: Path) -> None:
    paths = _review_paths(tmp_path)
    output_root = tmp_path / "draft" / "pre_review"
    session = ReviewSession.open(paths)
    records = build_pre_review_records(session)

    first = write_pre_review_outputs(records=records, output_root=output_root)
    first_bytes = {
        path.name: path.read_bytes()
        for path in sorted(output_root.iterdir())
    }
    second = write_pre_review_outputs(records=records, output_root=output_root)
    second_bytes = {
        path.name: path.read_bytes()
        for path in sorted(output_root.iterdir())
    }

    assert first == second
    assert first_bytes == second_bytes
    assert set(first_bytes) == {
        "PRE_REVIEW_RECOMMENDATIONS.jsonl",
        "PRE_REVIEW_SUMMARY.md",
    }
    assert not paths.working_path.exists()
    assert not paths.export_path.exists()
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```powershell
python -m pytest hybrid_mvp/tests/test_r4_pre_review.py::test_pre_review_cohorts_exclude_human_required_records hybrid_mvp/tests/test_r4_pre_review.py::test_write_pre_review_outputs_is_deterministic_and_does_not_touch_selection -q
```

Expected: fail with missing `build_pre_review_cohorts` and `write_pre_review_outputs`.

- [ ] **Step 3: Implement output writing**

Extend `hybrid_mvp/scripts/r4_1_pre_review.py`:

```python
from pathlib import Path

from scripts.build_r4_1_review_worksheets import _json_bytes, write_exact_output


MAX_PRE_REVIEW_COHORT_MEMBERS = 512


def build_pre_review_cohorts(records: tuple[PreReviewRecord, ...]) -> tuple[dict[str, object], ...]:
    grouped: dict[tuple[str, str, str], list[PreReviewRecord]] = {}
    for record in records:
        if (
            record.recommendation_class != RecommendationClass.APPROVE_CANDIDATE
            or record.action is None
            or not record.cohort_eligible
        ):
            continue
        key = (
            record.phase,
            record.row_kind,
            _json_digest(record.action),
        )
        grouped.setdefault(key, []).append(record)
    cohorts: list[dict[str, object]] = []
    for index, ((phase, row_kind, action_digest), members) in enumerate(sorted(grouped.items()), start=1):
        refs = tuple(sorted(record.record_ref for record in members))
        for offset in range(0, len(refs), MAX_PRE_REVIEW_COHORT_MEMBERS):
            chunk = refs[offset : offset + MAX_PRE_REVIEW_COHORT_MEMBERS]
            material = {
                "phase": phase,
                "row_kind": row_kind,
                "action_digest": action_digest,
                "member_record_refs": list(chunk),
            }
            cohorts.append(
                {
                    "cohort_ref": stable_ref("r4_1_pre_review_cohort", material),
                    "phase": phase,
                    "row_kind": row_kind,
                    "recommendation_class": RecommendationClass.APPROVE_CANDIDATE.value,
                    "member_record_refs": list(chunk),
                    "member_count": len(chunk),
                    "sequence": index,
                }
            )
    return tuple(cohorts)


def _summary_bytes(records: tuple[PreReviewRecord, ...], cohorts: tuple[dict[str, object], ...]) -> bytes:
    counts: dict[str, int] = {item.value: 0 for item in RecommendationClass}
    for record in records:
        counts[record.recommendation_class.value] += 1
    lines = [
        "# R4.1 Assistant Pre-Review Summary",
        "",
        "This file is advisory review-draft material only. It is not semantic authority and does not approve gold.",
        "",
        "## Counts",
        "",
    ]
    for key in sorted(counts):
        lines.append(f"- `{key}`: {counts[key]}")
    lines.extend(
        [
            "",
            "## Cohorts",
            "",
            f"- Advisory approval cohorts: {len(cohorts)}",
            "",
            "## Files",
            "",
            "- `PRE_REVIEW_RECOMMENDATIONS.jsonl`: one advisory record per current review target.",
        ]
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def write_pre_review_outputs(
    *,
    records: tuple[PreReviewRecord, ...],
    output_root: Path,
) -> Mapping[str, object]:
    output_root.mkdir(parents=True, exist_ok=True)
    cohorts = build_pre_review_cohorts(records)
    ledger_raw = b"".join(_json_bytes(record.to_json()) + b"\n" for record in records)
    summary_raw = _summary_bytes(records, cohorts)
    ledger_path = output_root / "PRE_REVIEW_RECOMMENDATIONS.jsonl"
    summary_path = output_root / "PRE_REVIEW_SUMMARY.md"
    write_exact_output(output_path=ledger_path, raw=ledger_raw, owner="R4.1 assistant pre-review ledger", allow_identical_existing=True)
    write_exact_output(output_path=summary_path, raw=summary_raw, owner="R4.1 assistant pre-review summary", allow_identical_existing=True)
    return {
        "record_count": len(records),
        "cohort_count": len(cohorts),
        "ledger_path": str(ledger_path),
        "summary_path": str(summary_path),
        "ledger_sha256": hashlib.sha256(ledger_raw).hexdigest(),
        "summary_sha256": hashlib.sha256(summary_raw).hexdigest(),
    }
```

- [ ] **Step 4: Run the focused tests**

Run:

```powershell
python -m pytest hybrid_mvp/tests/test_r4_pre_review.py -q
```

Expected: all pre-review tests pass.

- [ ] **Step 5: Commit Task 3**

Run:

```powershell
git add -- hybrid_mvp/scripts/r4_1_pre_review.py hybrid_mvp/tests/test_r4_pre_review.py
git commit -m "feat(r4): write advisory pre-review outputs"
```

## Task 4: CLI, Docs, and Regression Gates

**Files:**
- Modify: `hybrid_mvp/scripts/r4_1_pre_review.py`
- Modify: `hybrid_mvp/tests/test_r4_pre_review.py`
- Modify: `hybrid_mvp/artifacts/review_inputs/r4_1/README.md`

- [ ] **Step 1: Add CLI and runtime-isolation tests**

Append:

```python
import ast
import subprocess
import sys


def test_pre_review_cli_writes_default_draft_outputs(tmp_path: Path) -> None:
    paths = _review_paths(tmp_path)
    output = tmp_path / "pre_review"
    completed = subprocess.run(
        [
            sys.executable,
            "scripts/r4_1_pre_review.py",
            "--root",
            str(ROOT),
            "--draft",
            str(paths.draft_root),
            "--template",
            str(paths.template_path),
            "--working",
            str(paths.working_path),
            "--journal",
            str(paths.journal_path),
            "--export",
            str(paths.export_path),
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )

    assert "record_count" in completed.stdout
    assert (output / "PRE_REVIEW_RECOMMENDATIONS.jsonl").exists()
    assert (output / "PRE_REVIEW_SUMMARY.md").exists()
    assert not paths.working_path.exists()
    assert not paths.export_path.exists()


def test_runtime_source_never_imports_pre_review_sidecar() -> None:
    forbidden = {"r4_1_pre_review", "PRE_REVIEW_RECOMMENDATIONS"}
    violations: list[tuple[str, str]] = []
    for path in sorted((ROOT / "src/cemm_authoritative_hybrid").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for item in ast.walk(tree):
            names: list[str] = []
            if isinstance(item, ast.Import):
                names = [alias.name for alias in item.names]
            elif isinstance(item, ast.ImportFrom) and item.module is not None:
                names = [item.module]
            for name in names:
                if any(blocked in name for blocked in forbidden):
                    violations.append((str(path.relative_to(ROOT)), name))
    assert violations == []
```

- [ ] **Step 2: Run the new tests to verify they fail**

Run:

```powershell
python -m pytest hybrid_mvp/tests/test_r4_pre_review.py::test_pre_review_cli_writes_default_draft_outputs -q
```

Expected: fail because the CLI is not implemented.

- [ ] **Step 3: Implement CLI entry point**

Add to `hybrid_mvp/scripts/r4_1_pre_review.py`:

```python
import argparse
import sys


def _default_review_paths(root: Path, draft: Path | None) -> tuple[ReviewPaths, Path]:
    draft_root = draft if draft is not None else root / "artifacts" / "review_drafts" / "r4_1"
    inputs = root / "artifacts" / "review_inputs" / "r4_1"
    return (
        ReviewPaths(
            repository_root=root,
            draft_root=draft_root,
            template_path=inputs / "SELECTION_TEMPLATE.json",
            working_path=inputs / "SELECTION_WORKING.json",
            journal_path=inputs / "REVIEW_ACTIONS.jsonl",
            export_path=inputs / "SELECTION.json",
        ),
        draft_root,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--draft", type=Path)
    parser.add_argument("--template", type=Path)
    parser.add_argument("--working", type=Path)
    parser.add_argument("--journal", type=Path)
    parser.add_argument("--export", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    root = args.root.resolve()
    paths, default_draft = _default_review_paths(root, args.draft)
    if args.template is not None:
        paths = ReviewPaths(
            repository_root=root,
            draft_root=paths.draft_root,
            template_path=args.template,
            working_path=args.working or paths.working_path,
            journal_path=args.journal or paths.journal_path,
            export_path=args.export or paths.export_path,
        )
    output_root = args.output or default_draft
    session = ReviewSession.open(paths)
    receipt = write_pre_review_outputs(
        records=build_pre_review_records(session),
        output_root=output_root,
    )
    sys.stdout.write(json.dumps(receipt, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Document the optional advisory command**

Append to `hybrid_mvp/artifacts/review_inputs/r4_1/README.md`:

````markdown
## Optional assistant pre-review

The advisory pre-review command may be run before or beside guided review:

```powershell
python scripts/r4_1_pre_review.py
```

It writes inert draft material to `artifacts/review_drafts/r4_1/`:

- `PRE_REVIEW_RECOMMENDATIONS.jsonl`
- `PRE_REVIEW_SUMMARY.md`

These files are not semantic authority, not a review manifest, not activation
input and not reviewed gold. They are meant to help the accountable reviewer
spot evidence blockers, identify careful individual-curation cases and approve
only explicitly reviewed actions through the normal preview/apply/export flow.
````

- [ ] **Step 5: Run focused and existing R4.1 gates**

Run:

```powershell
python -m pytest hybrid_mvp/tests/test_r4_pre_review.py -q
python -m pytest hybrid_mvp/tests/test_r4_guided_review.py hybrid_mvp/tests/test_r4_review_server.py hybrid_mvp/tests/test_r4_review_selection.py -q
python scripts/r4_1_pre_review.py
```

Expected: tests pass; CLI prints a JSON receipt containing `record_count`.

- [ ] **Step 6: Commit Task 4**

Run:

```powershell
git add -- hybrid_mvp/scripts/r4_1_pre_review.py hybrid_mvp/tests/test_r4_pre_review.py hybrid_mvp/artifacts/review_inputs/r4_1/README.md
git commit -m "feat(r4): add assistant pre-review CLI"
```

## Task 5: Plan Completion Verification

**Files:**
- Modify: `hybrid_mvp/docs/superpowers/plans/2026-08-31-r4-1-assistant-pre-review-plan.md`

- [ ] **Step 1: Run the full relevant validation set**

Run:

```powershell
python -m pytest hybrid_mvp/tests/test_r4_pre_review.py hybrid_mvp/tests/test_r4_guided_review.py hybrid_mvp/tests/test_r4_review_server.py hybrid_mvp/tests/test_r4_review_selection.py hybrid_mvp/tests/test_r4_supervision_contracts.py hybrid_mvp/tests/test_r4_supervision_compilers.py -q
python scripts/r4_1_pre_review.py
python -m compileall hybrid_mvp/scripts hybrid_mvp/src hybrid_mvp/tests -q
```

Expected: all commands exit 0. The pre-review command writes advisory outputs only under `hybrid_mvp/artifacts/review_drafts/r4_1/`.

- [ ] **Step 2: Inspect generated advisory outputs**

Run:

```powershell
Get-Content -LiteralPath hybrid_mvp/artifacts/review_drafts/r4_1/PRE_REVIEW_SUMMARY.md -TotalCount 80
Get-Content -LiteralPath hybrid_mvp/artifacts/review_drafts/r4_1/PRE_REVIEW_RECOMMENDATIONS.jsonl -TotalCount 3
```

Expected: summary states the advisory boundary, and blocked/individual records do not contain approval actions.

- [ ] **Step 3: Confirm no selection mutation**

Run:

```powershell
git status --short
```

Expected: source/test/doc changes and advisory draft outputs may be present; `hybrid_mvp/artifacts/review_inputs/r4_1/SELECTION_WORKING.json` and `hybrid_mvp/artifacts/review_inputs/r4_1/SELECTION.json` are absent or unchanged unless the human reviewer separately used the review UI.

- [ ] **Step 4: Mark plan checkboxes and commit the final tracker update**

Update each completed checkbox in this plan from `- [ ]` to `- [x]`, then run:

```powershell
git add -- hybrid_mvp/docs/superpowers/plans/2026-08-31-r4-1-assistant-pre-review-plan.md
git commit -m "docs(r4): complete assistant pre-review plan tracker"
```
