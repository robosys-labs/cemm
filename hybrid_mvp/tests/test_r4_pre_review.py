"""Advisory R4.1 assistant pre-review ledger."""
from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import subprocess
import sys

from scripts.build_r4_1_review_selection import build_selection_template_bytes
from scripts.build_r4_1_review_worksheets import build_review_worksheet_draft
from scripts.r4_1_pre_review import (
    RecommendationClass,
    build_pre_review_cohorts,
    build_pre_review_records,
    preflight_designation_source,
    write_pre_review_outputs,
)
from scripts.r4_1_review_session import ReviewPaths, ReviewSession

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

    assert (
        result.recommendation_class
        == RecommendationClass.BLOCKED_EVIDENCE_MISMATCH
    )
    assert result.action is None
    assert any(
        issue.issue_kind == "span_text_mismatch"
        for issue in result.issues
    )
    assert any(
        issue.issue_kind == "surface_example_order_mismatch"
        for issue in result.issues
    )


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


def _review_paths(tmp_path: Path) -> ReviewPaths:
    draft = tmp_path / "draft"
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    build_review_worksheet_draft(repository_root=ROOT, output_root=draft)
    template_path = inputs / "SELECTION_TEMPLATE.json"
    template_path.write_bytes(
        build_selection_template_bytes(
            repository_root=ROOT,
            draft_root=draft,
        )
    )
    return ReviewPaths(
        repository_root=ROOT,
        draft_root=draft,
        template_path=template_path,
        working_path=inputs / "SELECTION_WORKING.json",
        journal_path=inputs / "REVIEW_ACTIONS.jsonl",
        export_path=inputs / "SELECTION.json",
    )


def test_pre_review_records_are_deterministic_and_inert(
    tmp_path: Path,
) -> None:
    paths = _review_paths(tmp_path)
    session = ReviewSession.open(paths)
    before = paths.working_path.exists(), paths.export_path.exists()

    first = build_pre_review_records(session)
    second = build_pre_review_records(ReviewSession.open(paths))

    assert [record.record_ref for record in first] == [
        record.record_ref for record in second
    ]
    assert [record.to_json() for record in first] == [
        record.to_json() for record in second
    ]
    assert len(first) == 1056
    assert before == (paths.working_path.exists(), paths.export_path.exists())
    assert not paths.working_path.exists()
    assert not paths.export_path.exists()
    assert hashlib.sha256(
        repr(first[0].to_json()).encode("utf-8")
    ).hexdigest()


def test_pre_review_cli_writes_default_draft_outputs(
    tmp_path: Path,
) -> None:
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


def test_pre_review_cli_default_output_does_not_pollute_draft_root(
    tmp_path: Path,
) -> None:
    paths = _review_paths(tmp_path)
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
        ],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    output_root = paths.draft_root.parent / "draft_pre_review"

    assert "record_count" in completed.stdout
    assert (output_root / "PRE_REVIEW_RECOMMENDATIONS.jsonl").exists()
    assert (output_root / "PRE_REVIEW_SUMMARY.md").exists()
    assert not (paths.draft_root / "PRE_REVIEW_RECOMMENDATIONS.jsonl").exists()
    assert not (paths.draft_root / "PRE_REVIEW_SUMMARY.md").exists()
    assert build_pre_review_records(ReviewSession.open(paths))


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


def test_pre_review_cohorts_exclude_human_required_records(
    tmp_path: Path,
) -> None:
    paths = _review_paths(tmp_path)
    records = build_pre_review_records(ReviewSession.open(paths))

    cohorts = build_pre_review_cohorts(records)

    assert all(
        cohort["recommendation_class"] == "approve_candidate"
        for cohort in cohorts
    )
    assert all(
        1 <= len(cohort["member_record_refs"]) <= 512
        for cohort in cohorts
    )
    human_required = {
        record.record_ref
        for record in records
        if record.recommendation_class
        == RecommendationClass.NEEDS_INDIVIDUAL_REVIEW
    }
    assert not any(
        human_required.intersection(cohort["member_record_refs"])
        for cohort in cohorts
    )


def test_write_pre_review_outputs_is_deterministic_and_does_not_touch_selection(
    tmp_path: Path,
) -> None:
    paths = _review_paths(tmp_path)
    output_root = tmp_path / "draft" / "pre_review"
    session = ReviewSession.open(paths)
    records = build_pre_review_records(session)

    first = write_pre_review_outputs(
        records=records,
        output_root=output_root,
    )
    first_bytes = {
        path.name: path.read_bytes()
        for path in sorted(output_root.iterdir())
    }
    second = write_pre_review_outputs(
        records=records,
        output_root=output_root,
    )
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
    ledger_lines = first_bytes[
        "PRE_REVIEW_RECOMMENDATIONS.jsonl"
    ].splitlines()
    assert len(ledger_lines) == len(records)
    assert all(line.strip() for line in ledger_lines)
    assert not paths.working_path.exists()
    assert not paths.export_path.exists()
