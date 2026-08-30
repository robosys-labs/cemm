"""Accountable R4.1 review-session behavior."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.build_r4_1_review_selection import build_selection_template_bytes
from scripts.build_r4_1_review_worksheets import build_review_worksheet_draft
from scripts.r4_1_review_session import ReviewPaths, ReviewSession

ROOT = Path(__file__).parents[1]


@pytest.fixture
def review_paths(tmp_path: Path) -> ReviewPaths:
    draft = tmp_path / "draft"
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    build_review_worksheet_draft(repository_root=ROOT, output_root=draft)
    template_path = inputs / "SELECTION_TEMPLATE.json"
    template_path.write_bytes(
        build_selection_template_bytes(repository_root=ROOT, draft_root=draft)
    )
    return ReviewPaths(
        repository_root=ROOT,
        draft_root=draft,
        template_path=template_path,
        working_path=inputs / "SELECTION_WORKING.json",
        journal_path=inputs / "REVIEW_ACTIONS.jsonl",
        export_path=inputs / "SELECTION.json",
    )


def test_session_bootstrap_indexes_exact_current_review_inventory(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    bootstrap = session.bootstrap()

    assert bootstrap["inventory"] == {
        "structural": 12,
        "purpose": 600,
        "recipe_family": 56,
        "designation": 388,
    }
    assert bootstrap["designation_risk_counts"]["intersecting_case"] == 12
    assert bootstrap["designation_risk_counts"]["overlap_pair"] == 13
    assert bootstrap["designation_risk_counts"]["multi_unit_case"] == 21
    assert bootstrap["designation_risk_counts"]["exact_empty"] == 61
    assert bootstrap["state_revision"] == 0
    assert bootstrap["selection_template_ref"].startswith(
        "r4_authoring_selection_template:"
    )


def test_routine_designation_cohorts_exclude_every_high_risk_case(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    exception_refs = session.indexes.designation_exception_case_refs
    cohort_members = {
        case_ref
        for cohort in session.indexes.routine_designation_cohorts.values()
        for case_ref in cohort
    }
    assert exception_refs.isdisjoint(cohort_members)
    assert exception_refs | cohort_members == set(
        session.indexes.designation_rows_by_case
    )


def test_review_indexes_are_recursively_immutable(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    structural = next(iter(session.indexes.structural_rows_by_ref.values()))
    designation = next(
        row
        for row in session.indexes.designation_rows_by_case.values()
        if row["candidate_bindings"]
    )

    with pytest.raises(TypeError):
        structural["options"][0]["label"] = "tampered"
    with pytest.raises(TypeError):
        designation["candidate_bindings"][0]["surface"] = "tampered"


def test_session_items_are_bounded_server_created_projections(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)

    page = session.items(
        section="structural",
        state_filter="all",
        query="composition",
        offset=0,
        limit=5,
    )

    assert set(page) == {"items", "limit", "offset", "section", "total"}
    assert page["section"] == "structural"
    assert page["limit"] == 5
    assert len(page["items"]) <= 5
    assert all(
        set(item)
        == {
            "current_value",
            "display",
            "options",
            "row_kind",
            "row_ref",
            "state",
            "subject_ref",
        }
        for item in page["items"]
    )
    with pytest.raises(ValueError, match="limit"):
        session.items(
            section="structural",
            state_filter="all",
            query="",
            offset=0,
            limit=101,
        )
