"""Guided accountable R4.1 review projections."""
from __future__ import annotations

from pathlib import Path
from typing import Mapping

import pytest

from scripts.build_r4_1_review_selection import build_selection_template_bytes
from scripts.build_r4_1_review_worksheets import build_review_worksheet_draft
from scripts.r4_1_guided_review import (
    GUIDANCE,
    MAX_GUIDED_TARGET_REFS,
    PHASE_ORDER,
    GuidedReviewService,
    active_choice_labels,
)
from scripts.r4_1_review_session import ReviewAction, ReviewPaths, ReviewSession

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


def test_guided_review_starts_with_identity_then_earliest_structural(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    service = GuidedReviewService(session)

    first = service.next_item(after_item_ref=None)
    assert first["phase"] == "identity"
    assert first["primary_action"] == "save_reviewer_identity"

    session.set_reviewers(("reviewer:test",))
    structural = service.next_item(after_item_ref=None)
    assert structural["phase"] == "structural"
    assert structural["source_summary"].strip()
    assert structural["reviewer_question"].endswith("?")
    assert structural["selected_choice_ref"] is None
    assert "row_ref" not in structural
    assert "technical_evidence" in structural


def test_skip_advances_without_mutation_and_wraps_once(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:test",))
    service = GuidedReviewService(session)
    revision = session.state_revision

    first = service.next_item(after_item_ref=None)
    second = service.next_item(after_item_ref=first["item_ref"])

    assert second["item_ref"] != first["item_ref"]
    assert session.state_revision == revision
    wrapped = service.next_item(after_item_ref=service.ordered_item_refs[-1])
    assert wrapped["wrapped"] is True
    assert session.state_revision == revision


def test_512_guided_reads_reuse_one_state_projection(
    review_paths: ReviewPaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:test",))
    real_getter = ReviewSession.state.fget
    assert real_getter is not None
    reads = 0

    def counted_state(current: ReviewSession):
        nonlocal reads
        reads += 1
        return real_getter(current)

    monkeypatch.setattr(ReviewSession, "state", property(counted_state))
    service = GuidedReviewService(session)
    item = service.next_item(after_item_ref=None)
    for _ in range(512):
        service.next_item(after_item_ref=item["item_ref"])

    assert service.projection_builds == 1
    assert reads == 1


def test_every_current_guided_choice_resolves_to_existing_allowed_action(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:test",))
    service = GuidedReviewService(session)

    for item in service.iter_current_items():
        assert item["choices"]
        for choice in item["choices"]:
            action = service.resolve_choice(
                item_ref=item["item_ref"],
                choice_ref=choice["choice_ref"],
            )
            assert session.preview(action).action == action
            assert "action" not in choice
            assert "selected" not in choice


def test_routine_designation_cohorts_exclude_every_exception(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    service = GuidedReviewService(session)
    exceptions = session.indexes.designation_exception_case_refs

    for item in service.designation_cohort_items():
        cohort = item["cohort"]
        members = set(cohort["target_refs"])
        assert members
        assert not members & exceptions
        assert len(members) <= MAX_GUIDED_TARGET_REFS


def test_guided_preview_is_readable_and_hides_action_wire(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:test",))
    service = GuidedReviewService(session)
    item = service.next_item(after_item_ref=None)

    preview = service.preview_choice(
        item_ref=item["item_ref"],
        choice_ref=item["choices"][0]["choice_ref"],
    )

    assert preview["decision_summary"].strip()
    assert preview["affected_count"] == len(preview["affected_refs"])
    assert preview["cleared_count"] == len(preview["cleared_refs"])
    assert "preview_hash" in preview
    assert "action" not in preview


def _option_ref(row: Mapping[str, object], label: str) -> str:
    return next(
        option["option_ref"]
        for option in row["options"]
        if option["label"] == label
    )


def _apply(session: ReviewSession, action: ReviewAction) -> None:
    preview = session.preview(action)
    session.apply(
        preview_hash=preview.preview_hash,
        expected_revision=preview.state_revision,
    )


def _complete_structural_and_purpose(session: ReviewSession) -> None:
    structural_labels = {
        "composed_expression_proposal": "approve_exact_proposal",
        "conflict_preservation": "preserve_as_alternatives",
        "legacy_conditional": "retain_typed_proposal_gaps",
        "restart_diagnostic": "approve_diagnostic_only",
        "generator_patch": "retain_typed_proposal_gaps",
    }
    for row in session.indexes.structural_rows_by_ref.values():
        _apply(
            session,
            ReviewAction.structural(
                row_ref=row["row_ref"],
                selected_option_ref=_option_ref(
                    row,
                    structural_labels[row["row_kind"]],
                ),
            ),
        )
    supervised = [
        row
        for row in session.indexes.purpose_rows_by_ref.values()
        if row["row_kind"] == "membership"
        and row["source_classification"] != "restart_diagnostic_candidate"
    ]
    purposes = ("train", "selection", "calibration", "frozen_test")
    for index, purpose in enumerate(purposes):
        refs = tuple(
            sorted(
                row["row_ref"]
                for row_index, row in enumerate(supervised)
                if row_index % len(purposes) == index
            )
        )
        _apply(
            session,
            ReviewAction.purpose(
                row_refs=refs,
                option_label=f"direct_{purpose}",
            ),
        )
    for row_kind, option_label in (
        ("membership", "approve_diagnostic_only"),
        ("duplicate_group", "reject_group"),
        ("challenge_holdout", "not_a_holdout"),
        ("denominator", "minimum_one_each"),
    ):
        refs = tuple(
            sorted(
                row["row_ref"]
                for row in session.indexes.purpose_rows_by_ref.values()
                if row["row_kind"] == row_kind
                and any(
                    option["label"] == option_label
                    and option["selectable"] is True
                    for option in row["options"]
                )
            )
        )
        _apply(
            session,
            ReviewAction.purpose(
                row_refs=refs,
                option_label=option_label,
            ),
        )


def test_guided_recipe_choice_uses_exact_purpose_local_action(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:test",))
    _complete_structural_and_purpose(session)
    service = GuidedReviewService(session)

    item = service.next_item(after_item_ref=None)

    assert item["phase"] == "recipe"
    assert {choice["label"] for choice in item["choices"]} == {
        "Approve this purpose-local recipe",
        "Reject and repair this recipe",
    }
    for choice in item["choices"]:
        action = service.resolve_choice(
            item_ref=item["item_ref"],
            choice_ref=choice["choice_ref"],
        )
        assert action.action_kind == "recipe"
        assert session.preview(action).action == action


def _complete_recipes(session: ReviewSession) -> None:
    evaluation = session.evaluation()
    for family_ref, family in session.indexes.proposal_families_by_ref.items():
        purposes = sorted(
            {
                evaluation.case_purposes[case_ref]
                for case_ref in family["member_case_refs"]
                if case_ref in evaluation.case_purposes
            }
        )
        for purpose in purposes:
            _apply(
                session,
                ReviewAction.recipe(
                    family_ref=family_ref,
                    purpose=purpose,
                    decision="approve",
                    reviewed_parameters={
                        "review_basis": "accountable_ui_exact_family"
                    },
                ),
            )


def test_guided_designation_choice_preserves_exception_ownership(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:test",))
    _complete_structural_and_purpose(session)
    _complete_recipes(session)
    service = GuidedReviewService(session)

    item = service.next_item(after_item_ref=None)

    assert item["phase"] == "designation"
    for choice in item["choices"]:
        action = service.resolve_choice(
            item_ref=item["item_ref"],
            choice_ref=choice["choice_ref"],
        )
        if item["cohort"] is None:
            assert action.action_kind == "designation_cases"
            assert action.selected_value["individual"] is True
        else:
            assert action.action_kind == "designation_cohort"
        assert session.preview(action).action == action
