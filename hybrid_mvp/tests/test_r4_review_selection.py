"""Task 10B reviewer-selection handoff remains bounded and non-authoritative."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

import scripts.build_r4_1_review_selection as selection_module
from scripts.build_r4_1_review_selection import (
    build_selection_template_bytes,
    evaluate_selection,
    load_selection_context,
    validate_reviewed_selection_bytes,
    write_exact_output,
    write_selection_template,
)
from scripts.build_r4_1_review_worksheets import build_review_worksheet_draft

ROOT = Path(__file__).parents[1]


def test_exact_output_allows_only_identical_existing_bytes(
    tmp_path: Path,
) -> None:
    output = tmp_path / "exact.json"
    raw = b'{"exact":true}\n'

    write_exact_output(
        output_path=output,
        raw=raw,
        owner="test exact export",
        allow_identical_existing=True,
    )
    write_exact_output(
        output_path=output,
        raw=raw,
        owner="test exact export",
        allow_identical_existing=True,
    )

    assert output.read_bytes() == raw
    with pytest.raises(ValueError, match="different existing"):
        write_exact_output(
            output_path=output,
            raw=b'{"exact":false}\n',
            owner="test exact export",
            allow_identical_existing=True,
        )


def test_exact_output_rejects_link_and_cleans_interrupted_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(b'{"target":true}\n')
    link = tmp_path / "linked.json"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symbolic links are unavailable: {exc}")
    with pytest.raises(ValueError, match="different existing"):
        write_exact_output(
            output_path=link,
            raw=target.read_bytes(),
            owner="test exact export",
            allow_identical_existing=True,
        )
    assert link.is_symlink()

    output = tmp_path / "interrupted.json"

    def interrupt_fsync(descriptor: int) -> None:
        raise OSError("simulated interruption")

    monkeypatch.setattr(selection_module.os, "fsync", interrupt_fsync)
    with pytest.raises(OSError, match="simulated interruption"):
        write_exact_output(
            output_path=output,
            raw=b'{"exact":true}\n',
            owner="test exact export",
            allow_identical_existing=True,
        )
    assert not output.exists()


def test_selection_evaluator_supports_partial_state(tmp_path: Path) -> None:
    draft = tmp_path / "draft"
    build_review_worksheet_draft(repository_root=ROOT, output_root=draft)
    template_raw = build_selection_template_bytes(
        repository_root=ROOT,
        draft_root=draft,
    )
    context = load_selection_context(
        repository_root=ROOT,
        draft_root=draft,
        template_raw=template_raw,
    )

    partial = evaluate_selection(
        context=context,
        selection=json.loads(template_raw),
        require_complete=False,
    )

    assert partial.complete is False
    assert partial.branch is None
    assert partial.active_case_refs == frozenset()
    assert partial.active_supervised_case_refs == frozenset()
    assert partial.unresolved_structural_count == 12
    assert partial.blocking_errors == ()
    assert partial.stale_selection_refs == ()


def test_review_selection_template_is_exact_bounded_inert_and_deterministic(
    tmp_path: Path,
) -> None:
    draft = tmp_path / "draft"
    build_review_worksheet_draft(repository_root=ROOT, output_root=draft)
    left = build_selection_template_bytes(repository_root=ROOT, draft_root=draft)
    right = build_selection_template_bytes(repository_root=ROOT, draft_root=draft)
    assert left == right
    selection = json.loads(left)
    schema = json.loads(
        (ROOT / "schemas/r4_authoring_selection.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(selection)

    assert selection["selection_state"] == "unresolved"
    assert selection["reviewer_refs"] == []
    assert len(selection["structural_selections"]) == 12
    assert len(selection["purpose_selections"]) == 600
    assert len(selection["proposal_recipe_selections"]) == 56
    assert len(selection["realization_recipe_selections"]) == 12
    assert len(selection["designation_selections"]) == 388
    assert all(
        row["selected_option_ref"] is None
        for name in ("structural_selections", "purpose_selections")
        for row in selection[name]
    )
    assert all(
        row["purpose_recipes"] == []
        for row in selection["proposal_recipe_selections"]
    )
    assert all(
        row["purpose_recipes"] == []
        for row in selection["realization_recipe_selections"]
    )
    assert all(
        row["decision"] is None and row["approved_binding_refs"] is None
        for row in selection["designation_selections"]
    )
    rendered = left.decode("utf-8")
    for forbidden in (
        "source_review:",
        "manifest_ref",
        "source_bundle_ref",
        "purpose_contract_ref",
        "proposal_target_ref",
    ):
        assert forbidden not in rendered

    structural = json.loads((draft / "STRUCTURAL_DECISIONS.json").read_bytes())
    purpose = json.loads((draft / "PURPOSE_DECISIONS.json").read_bytes())
    expected = {
        row["row_ref"]: {option["option_ref"] for option in row["options"]}
        for sheet in (structural, purpose)
        for row in sheet["rows"]
    }
    actual = {
        row["row_ref"]: set(row["allowed_option_refs"])
        for name in ("structural_selections", "purpose_selections")
        for row in selection[name]
    }
    assert actual == expected

    reviewed = deepcopy(selection)
    reviewed["selection_state"] = "reviewed"
    reviewed["reviewer_refs"] = ["reviewer:test"]
    structural_by_ref = {row["row_ref"]: row for row in structural["rows"]}
    for target in reviewed["structural_selections"]:
        source = structural_by_ref[target["row_ref"]]
        target["selected_option_ref"] = source["options"][0]["option_ref"]

    purpose_by_ref = {row["row_ref"]: row for row in purpose["rows"]}
    purposes = ("train", "selection", "calibration", "frozen_test")
    case_purposes = {}
    supervised_index = 0
    for target in reviewed["purpose_selections"]:
        source = purpose_by_ref[target["row_ref"]]
        options = {option["label"]: option for option in source["options"]}
        if source["row_kind"] == "membership":
            if source["source_classification"] == "restart_diagnostic_candidate":
                chosen = options["approve_diagnostic_only"]
            else:
                assigned = purposes[supervised_index % len(purposes)]
                supervised_index += 1
                case_purposes[source["source_case_ref"]] = assigned
                chosen = options[f"direct_{assigned}"]
        elif source["row_kind"] == "duplicate_group":
            chosen = options["reject_group"]
        elif source["row_kind"] == "challenge_holdout":
            chosen = options["not_a_holdout"]
        else:
            chosen = source["options"][0]
        target["selected_option_ref"] = chosen["option_ref"]

    for family in reviewed["proposal_recipe_selections"]:
        family["purpose_recipes"] = [
            {
                "purpose": purpose_name,
                "member_case_refs": sorted(
                    case_ref
                    for case_ref in family["member_case_refs"]
                    if case_purposes[case_ref] == purpose_name
                ),
                "decision": "approve",
                "reviewed_parameters": {"fixture_review": True},
            }
            for purpose_name in purposes
            if any(
                case_purposes[case_ref] == purpose_name
                for case_ref in family["member_case_refs"]
            )
        ]

    missing_realization_review = deepcopy(reviewed)
    missing_realization_review_raw = (
        json.dumps(
            missing_realization_review,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    Draft202012Validator(schema).validate(missing_realization_review)
    with pytest.raises(ValueError, match="realization purpose recipes"):
        validate_reviewed_selection_bytes(
            repository_root=ROOT,
            draft_root=draft,
            selection_raw=missing_realization_review_raw,
        )

    for family in reviewed["realization_recipe_selections"]:
        family["purpose_recipes"] = [
            {
                "purpose": purpose_name,
                "member_case_refs": sorted(
                    case_ref
                    for case_ref in family["member_case_refs"]
                    if case_purposes[case_ref] == purpose_name
                ),
                "decision": "approve",
                "reviewed_parameters": {
                    "review_basis": "accountable_exact_realization_family"
                },
            }
            for purpose_name in purposes
            if any(
                case_purposes[case_ref] == purpose_name
                for case_ref in family["member_case_refs"]
            )
        ]
    for designation in reviewed["designation_selections"]:
        if designation["candidate_binding_refs"]:
            designation["decision"] = "approve_candidate_bindings"
            designation["approved_binding_refs"] = list(
                designation["candidate_binding_refs"]
            )
        else:
            designation["decision"] = "approve_exact_empty"
            designation["approved_binding_refs"] = []
    reviewed_raw = (
        json.dumps(
            reviewed,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    Draft202012Validator(schema).validate(reviewed)
    assert validate_reviewed_selection_bytes(
        repository_root=ROOT,
        draft_root=draft,
        selection_raw=reviewed_raw,
    ) == reviewed

    mismatched_patch = deepcopy(reviewed)
    generator_target = next(
        target
        for target in mismatched_patch["structural_selections"]
        if structural_by_ref[target["row_ref"]]["row_kind"] == "generator_patch"
    )
    generator_source = structural_by_ref[generator_target["row_ref"]]
    generator_target["selected_option_ref"] = generator_source["options"][1][
        "option_ref"
    ]
    mismatched_patch_raw = (
        json.dumps(
            mismatched_patch,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    with pytest.raises(ValueError, match="generator patch differs"):
        validate_reviewed_selection_bytes(
            repository_root=ROOT,
            draft_root=draft,
            selection_raw=mismatched_patch_raw,
        )

    rejected_proposal = deepcopy(reviewed)
    proposal_target = next(
        target
        for target in rejected_proposal["structural_selections"]
        if structural_by_ref[target["row_ref"]]["row_kind"]
        == "composed_expression_proposal"
    )
    proposal_source = structural_by_ref[proposal_target["row_ref"]]
    proposal_target["selected_option_ref"] = next(
        option["option_ref"]
        for option in proposal_source["options"]
        if option["label"] == "reject_exact_proposal"
    )
    rejected_stale_raw = (
        json.dumps(
            rejected_proposal,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    with pytest.raises(ValueError, match="inapplicable purpose decision"):
        validate_reviewed_selection_bytes(
            repository_root=ROOT,
            draft_root=draft,
            selection_raw=rejected_stale_raw,
        )

    source_universe = json.loads((draft / "SOURCE_UNIVERSE.json").read_bytes())
    rejected_case_ref = next(
        row["case_ref"]
        for row in source_universe["rows"]
        if row.get("row_kind") == "expanded_case"
        and row.get("scenario_ref") == proposal_source["subject_ref"]
    )
    for target in rejected_proposal["purpose_selections"]:
        source = purpose_by_ref[target["row_ref"]]
        if (
            source["row_kind"] == "membership"
            and source["source_case_ref"] == rejected_case_ref
        ) or rejected_case_ref in source.get("member_case_refs", []):
            target["selected_option_ref"] = None
    for family in rejected_proposal["proposal_recipe_selections"]:
        retained = []
        for recipe in family["purpose_recipes"]:
            recipe["member_case_refs"] = [
                case_ref
                for case_ref in recipe["member_case_refs"]
                if case_ref != rejected_case_ref
            ]
            if recipe["member_case_refs"]:
                retained.append(recipe)
        family["purpose_recipes"] = retained
    for family in rejected_proposal["realization_recipe_selections"]:
        retained = []
        for recipe in family["purpose_recipes"]:
            recipe["member_case_refs"] = [
                case_ref
                for case_ref in recipe["member_case_refs"]
                if case_ref != rejected_case_ref
            ]
            if recipe["member_case_refs"]:
                retained.append(recipe)
        family["purpose_recipes"] = retained
    designation = next(
        target
        for target in rejected_proposal["designation_selections"]
        if target["source_case_ref"] == rejected_case_ref
    )
    designation["decision"] = None
    designation["approved_binding_refs"] = None
    rejected_valid_raw = (
        json.dumps(
            rejected_proposal,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    assert validate_reviewed_selection_bytes(
        repository_root=ROOT,
        draft_root=draft,
        selection_raw=rejected_valid_raw,
    ) == rejected_proposal

    invalid_reviewer = deepcopy(reviewed)
    invalid_reviewer["reviewer_refs"] = ["reviewer:contains whitespace"]
    invalid_reviewer_raw = (
        json.dumps(
            invalid_reviewer,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    with pytest.raises(ValueError, match="canonical accountable reviewers"):
        validate_reviewed_selection_bytes(
            repository_root=ROOT,
            draft_root=draft,
            selection_raw=invalid_reviewer_raw,
        )

    hostile = deepcopy(reviewed)
    hostile["structural_selections"][0]["selected_option_ref"] = (
        "review_worksheet_option:" + "0" * 24
    )
    hostile_raw = (
        json.dumps(hostile, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()
    with pytest.raises(ValueError, match="unavailable option"):
        validate_reviewed_selection_bytes(
            repository_root=ROOT,
            draft_root=draft,
            selection_raw=hostile_raw,
        )

    output = tmp_path / "SELECTION_TEMPLATE.json"
    write_selection_template(
        repository_root=ROOT,
        draft_root=draft,
        output_path=output,
    )
    assert output.read_bytes() == left
    with pytest.raises(ValueError, match="must not already exist"):
        write_selection_template(
            repository_root=ROOT,
            draft_root=draft,
            output_path=output,
        )
