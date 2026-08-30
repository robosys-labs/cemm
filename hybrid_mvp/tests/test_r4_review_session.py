"""Accountable R4.1 review-session behavior."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import pytest

import scripts.r4_1_review_session as review_session_module
from scripts.build_r4_1_review_selection import build_selection_template_bytes
from scripts.build_r4_1_review_worksheets import (
    _json_bytes,
    build_review_worksheet_draft,
)
from scripts.r4_1_review_session import ReviewAction, ReviewPaths, ReviewSession

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
    assert bootstrap["review_complete"] is False
    assert bootstrap["authoring_ready"] is False
    assert bootstrap["blocking_rejection_refs"] == []
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


def test_working_state_round_trips_and_binds_exact_template(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:son",))

    resumed = ReviewSession.open(review_paths)

    assert resumed.state["reviewer_refs"] == ["reviewer:son"]
    assert resumed.state["selection_state"] == "unresolved"
    assert resumed.state_revision == 0


def test_state_projection_cannot_mutate_session(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    projection = session.state
    projection["reviewer_refs"].append("reviewer:tamper")
    projection["structural_selections"][0]["selected_option_ref"] = "tamper"

    assert session.state["reviewer_refs"] == []
    assert session.state["structural_selections"][0]["selected_option_ref"] is None
    with pytest.raises(TypeError):
        projection["selection_state"] = "reviewed"


def test_stale_working_state_is_retained_and_rejected(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:son",))
    original = review_paths.working_path.read_bytes()
    value = json.loads(original)
    value["selection_template_ref"] = (
        "r4_authoring_selection_template:" + "0" * 24
    )
    review_paths.working_path.write_bytes(_json_bytes(value))

    with pytest.raises(ValueError, match="stale working selection"):
        ReviewSession.open(review_paths)
    assert review_paths.working_path.exists()


def test_existing_working_directory_is_rejected_and_retained(
    review_paths: ReviewPaths,
) -> None:
    review_paths.working_path.mkdir()

    with pytest.raises(ValueError, match="regular non-link file"):
        ReviewSession.open(review_paths)
    assert review_paths.working_path.is_dir()


def test_working_state_link_is_rejected_and_retained(
    review_paths: ReviewPaths,
) -> None:
    try:
        review_paths.working_path.symlink_to(review_paths.template_path)
    except OSError as exc:
        pytest.skip(f"symbolic links are unavailable: {exc}")

    with pytest.raises(ValueError, match="regular non-link file"):
        ReviewSession.open(review_paths)
    assert review_paths.working_path.is_symlink()


def test_interrupted_working_replace_preserves_in_memory_state_and_cleans_temp(
    review_paths: ReviewPaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = ReviewSession.open(review_paths)

    def interrupted_replace(source: object, destination: object) -> None:
        raise OSError("simulated interruption")

    monkeypatch.setattr(review_session_module.os, "replace", interrupted_replace)
    with pytest.raises(ValueError, match="replace"):
        session.set_reviewers(("reviewer:son",))

    assert session.state["reviewer_refs"] == []
    assert session.state_revision == 0
    assert not review_paths.working_path.exists()
    assert {path.name for path in review_paths.working_path.parent.iterdir()} == {
        "SELECTION_TEMPLATE.json"
    }


def test_malformed_journal_is_preserved_and_working_state_remains_authoritative(
    review_paths: ReviewPaths,
) -> None:
    malformed = b"{not-json}\n"
    review_paths.journal_path.write_bytes(malformed)

    session = ReviewSession.open(review_paths)
    assert session.audit_warning == "action journal unavailable: ValueError"
    session.set_reviewers(("reviewer:son",))

    assert session.state["reviewer_refs"] == ["reviewer:son"]
    assert session.state_revision == 1
    assert review_paths.working_path.exists()
    assert review_paths.journal_path.read_bytes() == malformed
    assert session.audit_warning == "action journal unavailable: ValueError"


def test_concurrent_journal_change_is_not_overwritten(
    review_paths: ReviewPaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:son",))
    original = review_paths.journal_path.read_bytes()
    concurrent = original + original
    real_atomic_replace = review_session_module._atomic_replace_regular

    def change_before_replace(**kwargs: object) -> None:
        if kwargs["owner"] == "review UI action journal":
            review_paths.journal_path.write_bytes(concurrent)
        real_atomic_replace(**kwargs)

    monkeypatch.setattr(
        review_session_module,
        "_atomic_replace_regular",
        change_before_replace,
    )
    session.set_reviewers(("reviewer:son", "reviewer:two"))

    assert session.state["reviewer_refs"] == ["reviewer:son", "reviewer:two"]
    assert session.audit_warning == "action journal unavailable: ValueError"
    assert review_paths.journal_path.read_bytes() == concurrent


def test_journal_entry_cap_never_blocks_valid_working_state(
    review_paths: ReviewPaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(review_session_module, "MAX_JOURNAL_ENTRIES", 1)
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:son",))
    first_entry = review_paths.journal_path.read_bytes()

    session.set_reviewers(("reviewer:son", "reviewer:two"))

    assert session.state["reviewer_refs"] == ["reviewer:son", "reviewer:two"]
    assert session.audit_warning == "action journal unavailable: ValueError"
    assert review_paths.journal_path.read_bytes() == first_entry


def _option_ref(row: Mapping[str, object], label: str) -> str:
    return next(
        option["option_ref"]
        for option in row["options"]
        if option["label"] == label
    )


@pytest.fixture
def started_session(review_paths: ReviewPaths) -> ReviewSession:
    session = ReviewSession.open(review_paths)
    session.set_reviewers(("reviewer:son",))
    return session


def _select_all_structural_approvals(session: ReviewSession) -> None:
    labels = {
        "composed_expression_proposal": "approve_exact_proposal",
        "conflict_preservation": "preserve_as_alternatives",
        "legacy_conditional": "retain_typed_proposal_gaps",
        "restart_diagnostic": "approve_diagnostic_only",
        "generator_patch": "retain_typed_proposal_gaps",
    }
    for row in session.indexes.structural_rows_by_ref.values():
        preview = session.preview(
            ReviewAction.structural(
                row_ref=row["row_ref"],
                selected_option_ref=_option_ref(
                    row,
                    labels[row["row_kind"]],
                ),
            )
        )
        session.apply(
            preview_hash=preview.preview_hash,
            expected_revision=preview.state_revision,
        )


def test_structural_change_previews_and_clears_exact_dependent_rows(
    started_session: ReviewSession,
) -> None:
    _select_all_structural_approvals(started_session)
    candidate_case = next(
        row
        for row in started_session.indexes.source_cases_by_ref.values()
        if row["universe"] == "candidate"
    )
    membership = next(
        row
        for row in started_session.indexes.purpose_rows_by_ref.values()
        if row["row_kind"] == "membership"
        and row["source_case_ref"] == candidate_case["case_ref"]
    )
    membership_preview = started_session.preview(
        ReviewAction.purpose(
            row_refs=(membership["row_ref"],),
            option_label="direct_train",
        )
    )
    started_session.apply(
        preview_hash=membership_preview.preview_hash,
        expected_revision=membership_preview.state_revision,
    )
    proposal = next(
        row
        for row in started_session.indexes.structural_rows_by_ref.values()
        if row["row_kind"] == "composed_expression_proposal"
        and row["subject_ref"] == candidate_case["scenario_ref"]
    )

    preview = started_session.preview(
        ReviewAction.structural(
            row_ref=proposal["row_ref"],
            selected_option_ref=_option_ref(proposal, "reject_exact_proposal"),
        )
    )
    assert preview.requires_clear_confirmation is True
    assert membership["row_ref"] in preview.cleared_refs

    result = started_session.apply(
        preview_hash=preview.preview_hash,
        expected_revision=preview.state_revision,
    )
    assert set(result["cleared_refs"]) == set(preview.cleared_refs)
    assert started_session.evaluation().blocking_errors == ()


def test_branch_change_previews_incompatible_generator_patch_clear(
    started_session: ReviewSession,
) -> None:
    _select_all_structural_approvals(started_session)
    branch = next(
        row
        for row in started_session.indexes.structural_rows_by_ref.values()
        if row["row_kind"] == "legacy_conditional"
    )
    generator = next(
        row
        for row in started_session.indexes.structural_rows_by_ref.values()
        if row["row_kind"] == "generator_patch"
    )

    preview = started_session.preview(
        ReviewAction.structural(
            row_ref=branch["row_ref"],
            selected_option_ref=_option_ref(
                branch,
                "retire_with_reserved_indices",
            ),
        )
    )

    assert generator["row_ref"] in preview.cleared_refs
    assert preview.requires_clear_confirmation is True


def test_stale_preview_cannot_apply(started_session: ReviewSession) -> None:
    row = next(iter(started_session.indexes.structural_rows_by_ref.values()))
    preview = started_session.preview(
        ReviewAction.structural(
            row_ref=row["row_ref"],
            selected_option_ref=row["options"][0]["option_ref"],
        )
    )
    started_session.set_reviewers(("reviewer:second", "reviewer:son"))
    with pytest.raises(ValueError, match="stale preview"):
        started_session.apply(
            preview_hash=preview.preview_hash,
            expected_revision=preview.state_revision,
        )


def test_anonymous_session_cannot_preview_mutation(
    review_paths: ReviewPaths,
) -> None:
    session = ReviewSession.open(review_paths)
    row = next(iter(session.indexes.structural_rows_by_ref.values()))

    with pytest.raises(ValueError, match="reviewer"):
        session.preview(
            ReviewAction.structural(
                row_ref=row["row_ref"],
                selected_option_ref=row["options"][0]["option_ref"],
            )
        )


def test_review_action_rejects_non_tuple_target_refs(
    started_session: ReviewSession,
) -> None:
    row = next(iter(started_session.indexes.structural_rows_by_ref.values()))

    with pytest.raises(TypeError, match="target refs"):
        started_session.preview(
            ReviewAction(
                action_kind="structural",
                target_refs=[row["row_ref"]],
                selected_value=row["options"][0]["option_ref"],
            )
        )


def test_purpose_cohort_preview_resolves_every_row_local_option(
    started_session: ReviewSession,
) -> None:
    _select_all_structural_approvals(started_session)
    rows = [
        row
        for row in started_session.indexes.purpose_rows_by_ref.values()
        if row["row_kind"] == "membership"
        and any(
            option["label"] == "direct_train" and option["selectable"] is True
            for option in row["options"]
        )
    ][:2]
    refs = tuple(sorted(row["row_ref"] for row in rows))

    preview = started_session.preview(
        ReviewAction.purpose(row_refs=refs, option_label="direct_train")
    )

    assert preview.affected_refs == refs
    result = started_session.apply(
        preview_hash=preview.preview_hash,
        expected_revision=preview.state_revision,
    )
    assert result["affected_refs"] == list(refs)
    selected_by_ref = {
        row["row_ref"]: row["selected_option_ref"]
        for row in started_session.state["purpose_selections"]
    }
    assert all(selected_by_ref[row["row_ref"]] == _option_ref(row, "direct_train") for row in rows)

    denominator = next(
        row
        for row in started_session.indexes.purpose_rows_by_ref.values()
        if row["row_kind"] == "denominator"
    )
    with pytest.raises(ValueError, match="one row kind"):
        started_session.preview(
            ReviewAction.purpose(
                row_refs=tuple(sorted((refs[0], denominator["row_ref"]))),
                option_label="direct_train",
            )
        )


def _apply_preview(session: ReviewSession, action: ReviewAction) -> None:
    preview = session.preview(action)
    session.apply(
        preview_hash=preview.preview_hash,
        expected_revision=preview.state_revision,
    )


def _complete_purpose_selections(session: ReviewSession) -> None:
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
        _apply_preview(
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
        _apply_preview(
            session,
            ReviewAction.purpose(
                row_refs=refs,
                option_label=option_label,
            ),
        )


@pytest.fixture
def purpose_complete_session(started_session: ReviewSession) -> ReviewSession:
    _select_all_structural_approvals(started_session)
    _complete_purpose_selections(started_session)
    return started_session


def _family_members(session: ReviewSession, family_ref: str) -> tuple[str, ...]:
    return tuple(
        session.indexes.proposal_families_by_ref[family_ref]["member_case_refs"]
    )


def _recipe_for(
    state: Mapping[str, object],
    *,
    family_ref: str,
    purpose: str,
) -> Mapping[str, object]:
    family = next(
        row
        for row in state["proposal_recipe_selections"]
        if row["family_ref"] == family_ref
    )
    return next(
        row for row in family["purpose_recipes"] if row["purpose"] == purpose
    )


def _designation_selection(
    state: Mapping[str, object],
    case_ref: str,
) -> Mapping[str, object]:
    return next(
        row
        for row in state["designation_selections"]
        if row["source_case_ref"] == case_ref
    )


def test_recipe_action_uses_exact_selected_purpose_partition(
    purpose_complete_session: ReviewSession,
) -> None:
    evaluation = purpose_complete_session.evaluation()
    family_ref = next(
        ref
        for ref in purpose_complete_session.indexes.proposal_families_by_ref
        if any(
            evaluation.case_purposes[case_ref] == "train"
            for case_ref in _family_members(purpose_complete_session, ref)
        )
    )
    preview = purpose_complete_session.preview(
        ReviewAction.recipe(
            family_ref=family_ref,
            purpose="train",
            decision="approve",
            reviewed_parameters={"review_basis": "exact_source_family"},
        )
    )
    purpose_complete_session.apply(
        preview_hash=preview.preview_hash,
        expected_revision=preview.state_revision,
    )
    recipe = _recipe_for(
        purpose_complete_session.state,
        family_ref=family_ref,
        purpose="train",
    )
    assert recipe["member_case_refs"] == sorted(
        case_ref
        for case_ref in _family_members(purpose_complete_session, family_ref)
        if purpose_complete_session.evaluation().case_purposes[case_ref]
        == "train"
    )
    replacement = purpose_complete_session.preview(
        ReviewAction.recipe(
            family_ref=family_ref,
            purpose="train",
            decision="approve",
            reviewed_parameters={"review_basis": "second_exact_review"},
        )
    )
    purpose_complete_session.apply(
        preview_hash=replacement.preview_hash,
        expected_revision=replacement.state_revision,
    )
    family = next(
        row
        for row in purpose_complete_session.state["proposal_recipe_selections"]
        if row["family_ref"] == family_ref
    )
    assert sum(
        row["purpose"] == "train" for row in family["purpose_recipes"]
    ) == 1


def test_recipe_rejection_is_reported_as_blocking_status(
    purpose_complete_session: ReviewSession,
) -> None:
    evaluation = purpose_complete_session.evaluation()
    family_ref = next(iter(purpose_complete_session.indexes.proposal_families_by_ref))
    purpose = next(
        evaluation.case_purposes[case_ref]
        for case_ref in _family_members(purpose_complete_session, family_ref)
        if evaluation.case_purposes[case_ref] is not None
    )

    preview = purpose_complete_session.preview(
        ReviewAction.recipe(
            family_ref=family_ref,
            purpose=purpose,
            decision="reject",
            reviewed_parameters={"review_basis": "exact_rejection"},
        )
    )
    result = purpose_complete_session.apply(
        preview_hash=preview.preview_hash,
        expected_revision=preview.state_revision,
    )

    assert family_ref in result["blocking_rejection_refs"]
    assert result["authoring_ready"] is False


def test_recipe_action_rejects_absent_partition_and_oversized_parameters(
    purpose_complete_session: ReviewSession,
) -> None:
    evaluation = purpose_complete_session.evaluation()
    family_ref = next(iter(purpose_complete_session.indexes.proposal_families_by_ref))
    absent = next(
        purpose
        for purpose in ("train", "selection", "calibration", "frozen_test")
        if all(
            evaluation.case_purposes[case_ref] != purpose
            for case_ref in _family_members(purpose_complete_session, family_ref)
        )
    )
    with pytest.raises(ValueError, match="absent purpose partition"):
        purpose_complete_session.preview(
            ReviewAction.recipe(
                family_ref=family_ref,
                purpose=absent,
                decision="approve",
                reviewed_parameters={},
            )
        )
    with pytest.raises(ValueError, match="parameter bound"):
        ReviewAction.recipe(
            family_ref=family_ref,
            purpose="train",
            decision="approve",
            reviewed_parameters={f"key_{index}": index for index in range(129)},
        )


def test_routine_designation_cohort_expands_to_exact_case_local_bindings(
    purpose_complete_session: ReviewSession,
) -> None:
    cohort_ref, case_refs = next(
        iter(purpose_complete_session.indexes.routine_designation_cohorts.items())
    )
    preview = purpose_complete_session.preview(
        ReviewAction.designation_cohort(
            cohort_ref=cohort_ref,
            decision="approve_candidate_bindings",
        )
    )
    result = purpose_complete_session.apply(
        preview_hash=preview.preview_hash,
        expected_revision=preview.state_revision,
    )
    assert set(result["affected_refs"]) == set(case_refs)
    for case_ref in case_refs:
        row = _designation_selection(purpose_complete_session.state, case_ref)
        assert row["approved_binding_refs"] == row["candidate_binding_refs"]


def test_exception_designation_rejects_cohort_action(
    purpose_complete_session: ReviewSession,
) -> None:
    case_ref = next(
        iter(purpose_complete_session.indexes.designation_exception_case_refs)
    )
    with pytest.raises(ValueError, match="individual review"):
        purpose_complete_session.preview(
            ReviewAction.designation_cases(
                case_refs=(case_ref,),
                decision="approve_candidate_bindings",
                individual=False,
            )
        )


def test_designation_decision_must_match_exact_candidate_shape(
    purpose_complete_session: ReviewSession,
) -> None:
    nonempty = next(
        case_ref
        for case_ref in purpose_complete_session.evaluation().active_supervised_case_refs
        if _designation_selection(
            purpose_complete_session.state,
            case_ref,
        )["candidate_binding_refs"]
    )
    with pytest.raises(ValueError, match="incompatible"):
        purpose_complete_session.preview(
            ReviewAction.designation_cases(
                case_refs=(nonempty,),
                decision="approve_exact_empty",
                individual=True,
            )
        )
