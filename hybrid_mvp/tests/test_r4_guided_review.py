"""Guided accountable R4.1 review projections."""
from __future__ import annotations

from pathlib import Path

import pytest

from scripts.build_r4_1_review_selection import build_selection_template_bytes
from scripts.build_r4_1_review_worksheets import build_review_worksheet_draft
from scripts.r4_1_guided_review import (
    GUIDANCE,
    PHASE_ORDER,
    active_choice_labels,
)
from scripts.r4_1_review_session import ReviewPaths, ReviewSession

ROOT = Path(__file__).parents[1]


EXPECTED_CHOICES = {
    "composed_expression_proposal": {
        "approve_exact_proposal",
        "reject_exact_proposal",
    },
    "conflict_preservation": {"preserve_as_alternatives"},
    "legacy_conditional": {
        "retain_typed_proposal_gaps",
        "retire_with_reserved_indices",
    },
    "generator_patch": {
        "retain_typed_proposal_gaps",
        "retire_with_reserved_indices",
    },
    "restart_diagnostic": {
        "approve_diagnostic_only",
        "reject_pending_replacement",
    },
    "membership": {
        "direct_train",
        "direct_selection",
        "direct_calibration",
        "direct_frozen_test",
        "assign_to_reviewed_group",
        "approve_diagnostic_only",
        "reject_pending_replacement",
    },
    "duplicate_group": {
        "approve_train",
        "approve_selection",
        "approve_calibration",
        "approve_frozen_test",
        "reject_group",
    },
    "challenge_holdout": {
        "not_a_holdout",
        "holdout_train",
        "holdout_selection",
        "holdout_calibration",
        "holdout_frozen_test",
    },
    "denominator": {"minimum_one_each"},
    "proposal_recipe_family": {"approve", "reject"},
    "designation_nonempty": {"approve_candidate_bindings", "reject"},
    "designation_empty": {"approve_exact_empty", "reject"},
}


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


def test_guidance_covers_every_active_choice_without_recommendation() -> None:
    assert PHASE_ORDER == (
        "identity",
        "structural",
        "purpose",
        "recipe",
        "designation",
        "export",
    )
    assert set(GUIDANCE) == set(EXPECTED_CHOICES)
    for row_kind, labels in EXPECTED_CHOICES.items():
        entry = GUIDANCE[row_kind]
        assert set(entry.choices) == labels
        assert entry.question.strip()
        for label, choice in entry.choices.items():
            wire = repr(choice).casefold()
            assert choice.label.strip()
            assert choice.explanation.strip()
            assert choice.consequence.strip()
            assert "recommended" not in wire
            assert "best choice" not in wire
            assert label not in {"default", "selected"}


def test_guidance_matches_authenticated_active_options(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)

    assert active_choice_labels(session) == EXPECTED_CHOICES
