"""Advisory R4.1 assistant pre-review ledger."""
from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.build_r4_1_review_selection import build_selection_template_bytes
from scripts.build_r4_1_review_worksheets import build_review_worksheet_draft
from scripts.r4_1_pre_review import (
    RecommendationClass,
    build_pre_review_records,
    preflight_designation_source,
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
