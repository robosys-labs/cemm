#!/usr/bin/env python3
"""Build one bounded, inert reviewer-selection template from an R4.1 draft."""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import sys
from types import MappingProxyType
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.canonical import stable_ref  # noqa: E402
from cemm_authoritative_hybrid._r4_source_codec import (  # noqa: E402
    exact_reviewer_refs,
)

from scripts.build_r4_1_review_worksheets import (  # noqa: E402
    MAX_WORKSHEET_BYTES,
    _is_link_or_reparse,
    _json_bytes,
    _read_regular,
    _same_identity,
    _strict_json,
    _tree_bytes,
    _trusted_directory,
    _validate_bound_repository_inputs,
    _validate_file_set_bytes,
    _validate_repository_semantics,
)

SELECTION_SCHEMA = "cemm-r4-authoring-review-selection-v1"
MAX_SELECTION_ROWS = 4096
_SCHEMA_PATH = "schemas/r4_authoring_selection.schema.json"


@dataclass(frozen=True)
class SelectionContext:
    expected_template: Mapping[str, object]
    decoded: Mapping[str, Mapping[str, object]]
    structural_rows: Mapping[str, Mapping[str, object]]
    purpose_rows: Mapping[str, Mapping[str, object]]
    source_case_rows: Mapping[str, Mapping[str, object]]


@dataclass(frozen=True)
class SelectionEvaluation:
    complete: bool
    branch: str | None
    applicable_purpose_row_refs: frozenset[str]
    active_case_refs: frozenset[str]
    active_supervised_case_refs: frozenset[str]
    case_purposes: Mapping[str, str | None]
    unresolved_structural_count: int
    unresolved_purpose_count: int
    unresolved_recipe_count: int
    unresolved_realization_recipe_count: int
    unresolved_designation_count: int
    blocking_rejection_refs: tuple[str, ...]
    blocking_errors: tuple[str, ...]
    stale_selection_refs: tuple[str, ...]


def _worksheet_refs(decoded: Mapping[str, Mapping[str, Any]]) -> dict[str, str]:
    return {
        name: decoded[name]["worksheet_ref"]
        for name in (
            "STRUCTURAL_DECISIONS.json",
            "SUPERVISION_DECISIONS.json",
            "PURPOSE_DECISIONS.json",
        )
    }


def _decision_targets(rows: object) -> list[dict[str, object]]:
    if type(rows) is not list or len(rows) > MAX_SELECTION_ROWS:
        raise ValueError("selection source rows violate their bound")
    result: list[dict[str, object]] = []
    for row in rows:
        if type(row) is not dict:
            raise TypeError("selection source row must be an exact object")
        options = row.get("options")
        if type(options) is not list or not options or len(options) > 16:
            raise ValueError("selection source options violate their bound")
        option_refs = [option.get("option_ref") for option in options]
        if any(
            type(ref) is not str or not ref.startswith("review_worksheet_option:")
            for ref in option_refs
        ) or len(option_refs) != len(set(option_refs)):
            raise ValueError("selection source option identities are invalid")
        result.append(
            {
                "row_ref": row["row_ref"],
                "row_kind": row["row_kind"],
                "subject_ref": row["subject_ref"],
                "allowed_option_refs": option_refs,
                "selected_option_ref": None,
            }
        )
    return result


def _proposal_recipe_targets(rows: object) -> list[dict[str, object]]:
    if type(rows) is not list or len(rows) > MAX_SELECTION_ROWS:
        raise ValueError("supervision rows violate their selection bound")
    families: dict[str, dict[str, object]] = {}
    for row in rows:
        if type(row) is not dict or row.get("row_kind") != "proposal_supervision":
            continue
        source_case_ref = row.get("source_case_ref")
        projection = row.get("source_projection")
        if type(source_case_ref) is not str or type(projection) is not dict:
            raise ValueError("proposal selection source join is invalid")
        suggestion = projection.get("recipe_suggestion")
        if type(suggestion) is not dict:
            raise ValueError("proposal selection lacks its recipe suggestion")
        family_ref = suggestion.get("family_ref")
        if type(family_ref) is not str:
            raise ValueError("proposal selection family ref is invalid")
        family = families.setdefault(
            family_ref,
            {
                "family_ref": family_ref,
                "target_kind": suggestion.get("target_kind"),
                "family_definition": None,
                "member_case_refs": [],
                "purpose_recipes": [],
            },
        )
        if family["target_kind"] != suggestion.get("target_kind"):
            raise ValueError("proposal selection family crosses target kinds")
        definition = suggestion.get("family_definition")
        if definition is not None:
            if family["family_definition"] is not None:
                raise ValueError("proposal selection family definition is duplicated")
            family["family_definition"] = definition
        members = family["member_case_refs"]
        if type(members) is not list:
            raise AssertionError("proposal selection member accumulator is invalid")
        members.append(source_case_ref)
    result = []
    for family_ref in sorted(families):
        family = families[family_ref]
        if family["family_definition"] is None:
            raise ValueError("proposal selection family definition is absent")
        family["member_case_refs"] = sorted(family["member_case_refs"])
        result.append(family)
    return result


def _realization_recipe_targets(rows: object) -> list[dict[str, object]]:
    if type(rows) is not list or len(rows) > MAX_SELECTION_ROWS:
        raise ValueError("realization rows violate their selection bound")
    families: dict[str, dict[str, object]] = {}
    for row in rows:
        if type(row) is not dict or row.get("row_kind") != "realization_supervision":
            continue
        source_case_ref = row.get("source_case_ref")
        projection = row.get("source_projection")
        if type(source_case_ref) is not str or type(projection) is not dict:
            raise ValueError("realization selection source join is invalid")
        suggestion = projection.get("recipe_suggestion")
        if type(suggestion) is not dict:
            raise ValueError("realization selection lacks its recipe suggestion")
        family_ref = suggestion.get("family_ref")
        if type(family_ref) is not str:
            raise ValueError("realization selection family ref is invalid")
        family = families.setdefault(
            family_ref,
            {
                "family_ref": family_ref,
                "target_kind": suggestion.get("target_kind"),
                "family_definition": None,
                "member_case_refs": [],
                "purpose_recipes": [],
            },
        )
        if family["target_kind"] != suggestion.get("target_kind"):
            raise ValueError("realization selection family crosses target kinds")
        definition = suggestion.get("family_definition")
        if definition is not None:
            if family["family_definition"] is not None:
                raise ValueError(
                    "realization selection family definition is duplicated"
                )
            family["family_definition"] = definition
        members = family["member_case_refs"]
        if type(members) is not list:
            raise AssertionError("realization selection member accumulator is invalid")
        members.append(source_case_ref)
    result = []
    for family_ref in sorted(families):
        family = families[family_ref]
        if family["family_definition"] is None:
            raise ValueError("realization selection family definition is absent")
        family["member_case_refs"] = sorted(family["member_case_refs"])
        result.append(family)
    return result


def _designation_targets(rows: object) -> list[dict[str, object]]:
    if type(rows) is not list or len(rows) > MAX_SELECTION_ROWS:
        raise ValueError("designation rows violate their selection bound")
    result: list[dict[str, object]] = []
    for row in rows:
        if type(row) is not dict or row.get("row_kind") != "designation_supervision":
            continue
        bindings = row.get("candidate_bindings")
        if type(bindings) is not list:
            raise ValueError("designation selection bindings are invalid")
        binding_refs = [binding.get("binding_ref") for binding in bindings]
        if any(
            type(ref) is not str
            or not ref.startswith("designation_binding_suggestion:")
            for ref in binding_refs
        ) or len(binding_refs) != len(set(binding_refs)):
            raise ValueError("designation selection binding refs are invalid")
        result.append(
            {
                "source_case_ref": row["source_case_ref"],
                "candidate_set_ref": row["candidate_set_ref"],
                "candidate_binding_refs": binding_refs,
                "decision": None,
                "approved_binding_refs": None,
            }
        )
    result.sort(key=lambda row: row["source_case_ref"])
    return result


def _load_selection_source(
    *,
    repository_root: Path,
    draft_root: Path,
) -> tuple[Path, dict[str, Mapping[str, object]]]:
    root = Path(repository_root).resolve(strict=True)
    draft_payloads = _tree_bytes(Path(draft_root), owner="selection-source draft")
    decoded = _validate_file_set_bytes(draft_payloads)
    retained = _validate_bound_repository_inputs(decoded=decoded, repository_root=root)
    _validate_repository_semantics(decoded=decoded, retained=retained)
    return root, decoded


def _selection_template_bytes_from_source(
    *,
    root: Path,
    decoded: Mapping[str, Mapping[str, object]],
) -> bytes:
    input_set_refs = {payload["input_set_ref"] for payload in decoded.values()}
    if len(input_set_refs) != 1:
        raise ValueError("selection-source worksheets do not share one input set")
    schema_raw = _read_regular(
        root / _SCHEMA_PATH,
        maximum=MAX_WORKSHEET_BYTES,
        owner="review selection schema",
    )
    schema = _strict_json(schema_raw, owner="review selection schema")
    if type(schema) is not dict or schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema":
        raise ValueError("review selection schema is not Draft 2020-12")
    material = {
        "schema": SELECTION_SCHEMA,
        "selection_state": "unresolved",
        "draft_input_set_ref": next(iter(input_set_refs)),
        "draft_worksheet_refs": _worksheet_refs(decoded),
        "selection_schema_path": _SCHEMA_PATH,
        "selection_schema_sha256": hashlib.sha256(schema_raw).hexdigest(),
        "reviewer_refs": [],
        "structural_selections": _decision_targets(
            decoded["STRUCTURAL_DECISIONS.json"]["rows"]
        ),
        "purpose_selections": _decision_targets(
            decoded["PURPOSE_DECISIONS.json"]["rows"]
        ),
        "proposal_recipe_selections": _proposal_recipe_targets(
            decoded["SUPERVISION_DECISIONS.json"]["rows"]
        ),
        "realization_recipe_selections": _realization_recipe_targets(
            decoded["SUPERVISION_DECISIONS.json"]["rows"]
        ),
        "designation_selections": _designation_targets(
            decoded["SUPERVISION_DECISIONS.json"]["rows"]
        ),
    }
    total_rows = sum(
        len(material[name])
        for name in (
            "structural_selections",
            "purpose_selections",
            "proposal_recipe_selections",
            "realization_recipe_selections",
            "designation_selections",
        )
    )
    if total_rows > MAX_SELECTION_ROWS:
        raise ValueError("review selection template exceeds its aggregate row bound")
    result = {
        **material,
        "selection_template_ref": stable_ref(
            "r4_authoring_selection_template",
            material,
        ),
    }
    raw = _json_bytes(result)
    if len(raw) > MAX_WORKSHEET_BYTES:
        raise ValueError("review selection template exceeds its byte bound")
    return raw


def build_selection_template_bytes(
    *,
    repository_root: Path,
    draft_root: Path,
) -> bytes:
    root, decoded = _load_selection_source(
        repository_root=repository_root,
        draft_root=draft_root,
    )
    return _selection_template_bytes_from_source(root=root, decoded=decoded)


def _selected_option(
    selection: Mapping[str, object],
    source_row: Mapping[str, object],
) -> Mapping[str, object] | None:
    selected_ref = selection["selected_option_ref"]
    if selected_ref is None:
        return None
    options = source_row["options"]
    if type(options) is not list:
        raise ValueError("selection source options are invalid")
    matches = [option for option in options if option.get("option_ref") == selected_ref]
    if len(matches) != 1 or matches[0].get("selectable") is not True:
        raise ValueError("review selection names an unavailable option")
    return matches[0]


def _validate_selection_projection(
    *,
    actual: object,
    expected: object,
    mutable_fields: frozenset[str],
    owner: str,
) -> tuple[dict[str, object], ...]:
    if type(actual) is not list or type(expected) is not list or len(actual) != len(expected):
        raise ValueError(f"{owner} selection inventory is incomplete")
    rows: list[dict[str, object]] = []
    for row, template in zip(actual, expected, strict=True):
        if type(row) is not dict or type(template) is not dict or set(row) != set(template):
            raise ValueError(f"{owner} selection fields do not match the template")
        if any(row[field] != template[field] for field in set(template) - mutable_fields):
            raise ValueError(f"{owner} immutable selection material changed")
        rows.append(row)
    return tuple(rows)


def load_selection_context(
    *,
    repository_root: Path,
    draft_root: Path,
    template_raw: bytes | None = None,
) -> SelectionContext:
    """Authenticate one exact draft and its generated selection template."""

    if template_raw is not None and not isinstance(template_raw, bytes):
        raise TypeError("selection template must be exact bytes")
    root, decoded = _load_selection_source(
        repository_root=repository_root,
        draft_root=draft_root,
    )
    generated = _selection_template_bytes_from_source(
        root=root,
        decoded=decoded,
    )
    if template_raw is None:
        template_raw = generated
    elif template_raw != generated:
        raise ValueError("selection template differs from authenticated draft")
    expected = _strict_json(template_raw, owner="review selection template")
    structural_rows = {
        row["row_ref"]: row
        for row in decoded["STRUCTURAL_DECISIONS.json"]["rows"]
    }
    purpose_rows = {
        row["row_ref"]: row for row in decoded["PURPOSE_DECISIONS.json"]["rows"]
    }
    source_case_rows = {
        row["case_ref"]: row
        for row in decoded["SOURCE_UNIVERSE.json"]["rows"]
        if row.get("row_kind") == "expanded_case"
    }
    if len(source_case_rows) != 408:
        raise ValueError("review selection source case inventory is invalid")
    return SelectionContext(
        expected_template=MappingProxyType(expected),
        decoded=MappingProxyType(decoded),
        structural_rows=MappingProxyType(structural_rows),
        purpose_rows=MappingProxyType(purpose_rows),
        source_case_rows=MappingProxyType(source_case_rows),
    )


def _selection_projections(
    *,
    context: SelectionContext,
    selection: Mapping[str, object],
) -> tuple[
    tuple[dict[str, object], ...],
    tuple[dict[str, object], ...],
    tuple[dict[str, object], ...],
    tuple[dict[str, object], ...],
    tuple[dict[str, object], ...],
]:
    expected = context.expected_template
    if type(selection) is not dict or set(selection) != set(expected):
        raise ValueError("completed review selection fields do not match")
    immutable_top = set(expected) - {
        "selection_state",
        "reviewer_refs",
        "structural_selections",
        "purpose_selections",
        "proposal_recipe_selections",
        "realization_recipe_selections",
        "designation_selections",
    }
    if any(selection[field] != expected[field] for field in immutable_top):
        raise ValueError("completed review selection is not bound to this template")
    structural = _validate_selection_projection(
        actual=selection["structural_selections"],
        expected=expected["structural_selections"],
        mutable_fields=frozenset({"selected_option_ref"}),
        owner="structural",
    )
    purpose = _validate_selection_projection(
        actual=selection["purpose_selections"],
        expected=expected["purpose_selections"],
        mutable_fields=frozenset({"selected_option_ref"}),
        owner="purpose",
    )
    recipes = _validate_selection_projection(
        actual=selection["proposal_recipe_selections"],
        expected=expected["proposal_recipe_selections"],
        mutable_fields=frozenset({"purpose_recipes"}),
        owner="proposal recipe",
    )
    realization_recipes = _validate_selection_projection(
        actual=selection["realization_recipe_selections"],
        expected=expected["realization_recipe_selections"],
        mutable_fields=frozenset({"purpose_recipes"}),
        owner="realization recipe",
    )
    designations = _validate_selection_projection(
        actual=selection["designation_selections"],
        expected=expected["designation_selections"],
        mutable_fields=frozenset({"decision", "approved_binding_refs"}),
        owner="designation",
    )
    return structural, purpose, recipes, realization_recipes, designations


def _raise_first_complete_error(
    *,
    blocking_errors: Sequence[str],
    stale_selection_refs: Sequence[str],
    unresolved_structural_count: int,
    unresolved_purpose_count: int,
    unresolved_recipe_count: int,
    unresolved_realization_recipe_count: int,
    unresolved_designation_count: int,
) -> None:
    if blocking_errors:
        raise ValueError(blocking_errors[0])
    if stale_selection_refs:
        if any(ref.startswith("review_worksheet_row:") for ref in stale_selection_refs):
            raise ValueError("inapplicable purpose decision must remain unselected")
        raise ValueError("inapplicable downstream selection must remain empty")
    if unresolved_structural_count:
        raise ValueError("every structural decision requires one selection")
    if unresolved_purpose_count:
        raise ValueError("every applicable purpose decision requires one selection")
    if unresolved_recipe_count:
        raise ValueError("proposal purpose recipes do not partition active members")
    if unresolved_realization_recipe_count:
        raise ValueError(
            "realization purpose recipes do not partition active members"
        )
    if unresolved_designation_count:
        raise ValueError("active designation selection is unresolved")


def _evaluate_recipe_partitions(
    *,
    recipe_rows: tuple[dict[str, object], ...],
    active_supervised: frozenset[str],
    case_purposes: Mapping[str, str | None],
    stale_refs: list[str],
    blocking_rejections: set[str],
    owner: str,
) -> int:
    unresolved = 0
    for selection_row in recipe_rows:
        active_members = set(selection_row["member_case_refs"]) & active_supervised
        purpose_recipes = selection_row["purpose_recipes"]
        if type(purpose_recipes) is not list or len(purpose_recipes) > 4:
            raise ValueError(f"{owner} purpose recipes violate their bound")
        if not active_members:
            if purpose_recipes:
                stale_refs.append(selection_row["family_ref"])
            continue
        seen_purposes: set[str] = set()
        assigned_members: set[str] = set()
        for recipe in purpose_recipes:
            if type(recipe) is not dict or set(recipe) != {
                "purpose",
                "member_case_refs",
                "decision",
                "reviewed_parameters",
            }:
                raise ValueError(f"{owner} purpose recipe fields are invalid")
            purpose = recipe["purpose"]
            members = recipe["member_case_refs"]
            if (
                purpose not in {"train", "selection", "calibration", "frozen_test"}
                or purpose in seen_purposes
                or type(members) is not list
                or not members
                or members != sorted(set(members))
                or recipe["decision"] not in {"approve", "reject"}
                or type(recipe["reviewed_parameters"]) is not dict
                or len(recipe["reviewed_parameters"]) > 128
            ):
                raise ValueError(f"{owner} purpose recipe is not canonical")
            member_set = set(members)
            inactive_members = member_set - active_members
            if inactive_members:
                stale_refs.append(selection_row["family_ref"])
                continue
            if (
                member_set & assigned_members
                or any(case_purposes.get(case_ref) != purpose for case_ref in members)
            ):
                raise ValueError(f"{owner} purpose recipe crosses case ownership")
            if recipe["decision"] == "reject":
                blocking_rejections.add(selection_row["family_ref"])
            seen_purposes.add(purpose)
            assigned_members.update(member_set)
        if assigned_members != active_members:
            unresolved += 1
    return unresolved


def evaluate_selection(
    *,
    context: SelectionContext,
    selection: Mapping[str, object],
    require_complete: bool,
) -> SelectionEvaluation:
    """Evaluate exact mutable fields against one authenticated selection context."""

    (
        structural,
        purpose_rows,
        recipe_rows,
        realization_recipe_rows,
        designation_rows,
    ) = _selection_projections(context=context, selection=selection)
    unresolved_structural = sum(
        row["selected_option_ref"] is None for row in structural
    )
    stale_refs: list[str] = []
    blocking_errors: list[str] = []
    blocking_rejections: set[str] = set()

    selected_structural: dict[str, list[Mapping[str, object]]] = {}
    for selection_row in structural:
        source_row = context.structural_rows[selection_row["row_ref"]]
        option = _selected_option(selection_row, source_row)
        if option is None:
            continue
        selected_structural.setdefault(source_row["row_kind"], []).append(option)
        if option["label"] in {
            "reject_exact_proposal",
            "reject_pending_replacement",
        }:
            blocking_rejections.add(source_row["subject_ref"])

    if unresolved_structural:
        stale_refs.extend(
            row["row_ref"]
            for row in purpose_rows
            if row["selected_option_ref"] is not None
        )
        stale_refs.extend(
            row["family_ref"] for row in recipe_rows if row["purpose_recipes"]
        )
        stale_refs.extend(
            row["family_ref"]
            for row in realization_recipe_rows
            if row["purpose_recipes"]
        )
        stale_refs.extend(
            row["source_case_ref"]
            for row in designation_rows
            if row["decision"] is not None or row["approved_binding_refs"] is not None
        )
        if require_complete:
            _raise_first_complete_error(
                blocking_errors=blocking_errors,
                stale_selection_refs=stale_refs,
                unresolved_structural_count=unresolved_structural,
                unresolved_purpose_count=0,
                unresolved_recipe_count=0,
                unresolved_realization_recipe_count=0,
                unresolved_designation_count=0,
            )
        return SelectionEvaluation(
            complete=False,
            branch=None,
            applicable_purpose_row_refs=frozenset(),
            active_case_refs=frozenset(),
            active_supervised_case_refs=frozenset(),
            case_purposes=MappingProxyType({}),
            unresolved_structural_count=unresolved_structural,
            unresolved_purpose_count=0,
            unresolved_recipe_count=0,
            unresolved_realization_recipe_count=0,
            unresolved_designation_count=0,
            blocking_rejection_refs=tuple(sorted(blocking_rejections)),
            blocking_errors=(),
            stale_selection_refs=tuple(sorted(stale_refs)),
        )

    branch_options = selected_structural.get("legacy_conditional", [])
    if len(branch_options) != 1 or branch_options[0]["label"] not in {
        "retain_typed_proposal_gaps",
        "retire_with_reserved_indices",
    }:
        blocking_errors.append("review selection lacks one exact structural branch")
        branch = None
    else:
        branch = branch_options[0]["label"]
    patch_options = selected_structural.get("generator_patch", [])
    if branch is not None and (
        len(patch_options) != 1 or patch_options[0]["label"] != branch
    ):
        blocking_errors.append("selected generator patch differs from structural branch")
    restart_options = selected_structural.get("restart_diagnostic", [])
    if len(restart_options) != 1:
        blocking_errors.append("review selection lacks one restart-diagnostic policy")
        diagnostic_cases_active = False
    else:
        diagnostic_cases_active = (
            restart_options[0]["label"] == "approve_diagnostic_only"
        )
    proposal_options = selected_structural.get("composed_expression_proposal", [])
    if len(proposal_options) != 8:
        blocking_errors.append(
            "review selection lacks the exact structural proposal set"
        )
    approved_candidate_scenarios = {
        option["payload"]["scenario_ref"]
        for option in proposal_options
        if option["label"] == "approve_exact_proposal"
    }

    def case_is_active(case_ref: object) -> bool:
        if type(case_ref) is not str or case_ref not in context.source_case_rows:
            raise ValueError("purpose decision references an unknown source case")
        source = context.source_case_rows[case_ref]
        if source["universe"] == "candidate":
            return source["scenario_ref"] in approved_candidate_scenarios
        if source["universe"] != "current":
            raise ValueError("purpose decision references an unknown source universe")
        if source["source_disposition"] == "restart_diagnostic_candidate":
            return diagnostic_cases_active
        if branch == "retire_with_reserved_indices" and source["scenario_ref"] in {
            "scenario:modality-0040",
            "scenario:modality-0046",
        }:
            return False
        return branch is not None

    active_cases = frozenset(
        case_ref for case_ref in context.source_case_rows if case_is_active(case_ref)
    )
    applicable_purpose: set[str] = set()
    selected_purpose: dict[str, Mapping[str, object]] = {}
    active_purpose_source_rows: dict[str, Mapping[str, object]] = {}
    unresolved_purpose = 0
    for selection_row in purpose_rows:
        source_row = context.purpose_rows[selection_row["row_ref"]]
        applicability = source_row.get("branch_applicability")
        applicable = branch is not None and (
            applicability is None or branch in applicability
        )
        if source_row["row_kind"] == "membership":
            applicable = applicable and case_is_active(source_row["source_case_ref"])
        elif source_row["row_kind"] in {"duplicate_group", "challenge_holdout"}:
            applicable = applicable and all(
                case_is_active(case_ref)
                for case_ref in source_row["member_case_refs"]
            )
        elif source_row["row_kind"] != "denominator":
            raise ValueError("review selection has an unknown purpose decision kind")
        option = _selected_option(selection_row, source_row)
        if applicable:
            applicable_purpose.add(source_row["row_ref"])
            if option is None:
                unresolved_purpose += 1
            else:
                selected_purpose[source_row["row_ref"]] = option
                active_purpose_source_rows[source_row["row_ref"]] = source_row
        elif option is not None:
            stale_refs.append(source_row["row_ref"])

    group_purposes: dict[str, str | None] = {}
    for row_ref, source_row in active_purpose_source_rows.items():
        if source_row["row_kind"] != "duplicate_group":
            continue
        payload = selected_purpose[row_ref]["payload"]
        if type(payload) is not dict:
            raise ValueError("duplicate-group selection payload is invalid")
        group_purposes[source_row["subject_ref"]] = payload.get("purpose")

    case_purposes: dict[str, str | None] = {}
    for row_ref, source_row in active_purpose_source_rows.items():
        if source_row["row_kind"] != "membership":
            continue
        payload = selected_purpose[row_ref]["payload"]
        if type(payload) is not dict:
            raise ValueError("membership selection payload is invalid")
        purpose = payload.get("purpose")
        group_ref = payload.get("group_candidate_ref")
        if group_ref is not None:
            purpose = group_purposes.get(group_ref)
            if purpose is None:
                blocking_errors.append(
                    "membership selects a rejected duplicate group"
                )
        classification = payload.get("classification")
        if classification == "diagnostic_only":
            if purpose is not None:
                blocking_errors.append("diagnostic membership cannot own a purpose")
        elif purpose not in {"train", "selection", "calibration", "frozen_test"}:
            blocking_errors.append("supervised membership lacks one exact purpose")
        case_purposes[source_row["source_case_ref"]] = purpose

    for row_ref, source_row in active_purpose_source_rows.items():
        if source_row["row_kind"] != "challenge_holdout":
            continue
        payload = selected_purpose[row_ref]["payload"]
        purpose = payload.get("purpose") if type(payload) is dict else None
        if purpose is not None and any(
            case_purposes.get(case_ref) != purpose
            for case_ref in source_row["member_case_refs"]
        ):
            blocking_errors.append("challenge holdout crosses selected case purposes")

    purpose_counts = {
        purpose: sum(value == purpose for value in case_purposes.values())
        for purpose in ("train", "selection", "calibration", "frozen_test")
    }
    for row_ref, source_row in active_purpose_source_rows.items():
        if source_row["row_kind"] != "denominator":
            continue
        payload = selected_purpose[row_ref]["payload"]
        if type(payload) is not dict or any(
            type(minimum) is not int
            or minimum < 0
            or purpose_counts[purpose] < minimum
            for purpose, minimum in payload.items()
        ):
            blocking_errors.append(
                "selected purpose denominator minimum is not satisfied"
            )

    active_supervised = frozenset(
        case_ref for case_ref, purpose in case_purposes.items() if purpose is not None
    )
    unresolved_recipes = _evaluate_recipe_partitions(
        recipe_rows=recipe_rows,
        active_supervised=active_supervised,
        case_purposes=case_purposes,
        stale_refs=stale_refs,
        blocking_rejections=blocking_rejections,
        owner="proposal",
    )
    unresolved_realization_recipes = _evaluate_recipe_partitions(
        recipe_rows=realization_recipe_rows,
        active_supervised=active_supervised,
        case_purposes=case_purposes,
        stale_refs=stale_refs,
        blocking_rejections=blocking_rejections,
        owner="realization",
    )

    unresolved_designations = 0
    for selection_row in designation_rows:
        active = selection_row["source_case_ref"] in active_supervised
        candidates = selection_row["candidate_binding_refs"]
        decision = selection_row["decision"]
        approved = selection_row["approved_binding_refs"]
        if not active:
            if decision is not None or approved is not None:
                stale_refs.append(selection_row["source_case_ref"])
            continue
        if decision == "approve_candidate_bindings":
            if not candidates or approved != candidates:
                raise ValueError(
                    "designation approval differs from exact candidate set"
                )
        elif decision == "approve_exact_empty":
            if candidates or approved != []:
                raise ValueError("designation empty approval is not exact")
        elif decision == "reject":
            if approved is not None:
                raise ValueError("rejected designation cannot approve bindings")
            blocking_rejections.add(selection_row["source_case_ref"])
        elif decision is None and approved is None:
            unresolved_designations += 1
        else:
            raise ValueError("active designation selection is unresolved")

    stale = tuple(sorted(set(stale_refs)))
    errors = tuple(dict.fromkeys(blocking_errors))
    complete = not any(
        (
            unresolved_structural,
            unresolved_purpose,
            unresolved_recipes,
            unresolved_realization_recipes,
            unresolved_designations,
            stale,
            errors,
        )
    )
    if require_complete and not complete:
        _raise_first_complete_error(
            blocking_errors=errors,
            stale_selection_refs=stale,
            unresolved_structural_count=unresolved_structural,
            unresolved_purpose_count=unresolved_purpose,
            unresolved_recipe_count=unresolved_recipes,
            unresolved_realization_recipe_count=unresolved_realization_recipes,
            unresolved_designation_count=unresolved_designations,
        )
    return SelectionEvaluation(
        complete=complete,
        branch=branch,
        applicable_purpose_row_refs=frozenset(applicable_purpose),
        active_case_refs=active_cases,
        active_supervised_case_refs=active_supervised,
        case_purposes=MappingProxyType(dict(sorted(case_purposes.items()))),
        unresolved_structural_count=unresolved_structural,
        unresolved_purpose_count=unresolved_purpose,
        unresolved_recipe_count=unresolved_recipes,
        unresolved_realization_recipe_count=unresolved_realization_recipes,
        unresolved_designation_count=unresolved_designations,
        blocking_rejection_refs=tuple(sorted(blocking_rejections)),
        blocking_errors=errors,
        stale_selection_refs=stale,
    )


def validate_reviewed_selection_bytes(
    *,
    repository_root: Path,
    draft_root: Path,
    selection_raw: object,
) -> Mapping[str, object]:
    """Validate one completed selection without minting reviewed-source identity."""

    if not isinstance(selection_raw, bytes):
        raise TypeError("review selection must be exact bytes")
    context = load_selection_context(
        repository_root=repository_root,
        draft_root=draft_root,
    )
    actual = _strict_json(selection_raw, owner="completed review selection")
    reviewers = actual.get("reviewer_refs") if type(actual) is dict else None
    if (
        type(actual) is not dict
        or actual.get("selection_state") != "reviewed"
        or type(reviewers) is not list
    ):
        raise ValueError(
            "completed review selection lacks canonical accountable reviewers"
        )
    try:
        exact_reviewers = exact_reviewer_refs(
            tuple(reviewers),
            maximum=128,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "completed review selection lacks canonical accountable reviewers"
        ) from exc
    if list(exact_reviewers) != reviewers:
        raise ValueError(
            "completed review selection lacks canonical accountable reviewers"
        )
    evaluation = evaluate_selection(
        context=context,
        selection=actual,
        require_complete=True,
    )
    if not evaluation.complete:
        raise ValueError("completed review selection remains unresolved")
    if _json_bytes(actual) != selection_raw:
        raise ValueError("completed review selection bytes are not canonical")
    return actual


def write_exact_output(
    *,
    output_path: Path,
    raw: bytes,
    owner: str,
    allow_identical_existing: bool,
) -> None:
    output = Path(output_path).absolute()
    if type(raw) is not bytes or not raw or len(raw) > MAX_WORKSHEET_BYTES:
        raise ValueError(f"{owner} violates byte bounds")
    if type(owner) is not str or not owner:
        raise TypeError("exact output owner must be an exact string")
    if type(allow_identical_existing) is not bool:
        raise TypeError("exact output existing policy must be exact")
    parent_before = _trusted_directory(
        output.parent,
        owner=f"{owner} parent",
    )
    try:
        existing = os.lstat(output)
    except FileNotFoundError:
        existing = None
    except OSError as exc:
        raise ValueError(f"cannot inspect {owner}") from exc
    if existing is not None:
        if not allow_identical_existing:
            raise ValueError(f"{owner} must not already exist")
        try:
            retained = _read_regular(
                output,
                maximum=MAX_WORKSHEET_BYTES,
                owner=owner,
            )
        except ValueError as exc:
            raise ValueError("different existing export is unsafe") from exc
        if retained != raw:
            raise ValueError("different existing export already exists")
        return
    if not _same_identity(
        parent_before,
        _trusted_directory(output.parent, owner=f"{owner} parent"),
    ):
        raise ValueError(f"{owner} parent identity changed")
    try:
        descriptor = os.open(
            output,
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | getattr(os, "O_BINARY", 0),
            0o600,
        )
    except OSError as exc:
        raise ValueError(f"cannot create {owner} exclusively") from exc
    created_identity = os.fstat(descriptor)
    try:
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                written = stream.write(raw)
                if written != len(raw):
                    raise ValueError(f"{owner} write was incomplete")
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            os.close(descriptor)
        after = os.lstat(output)
        if (
            not stat.S_ISREG(after.st_mode)
            or _is_link_or_reparse(after)
            or after.st_nlink != 1
            or not _same_identity(
                parent_before,
                _trusted_directory(output.parent, owner=f"{owner} parent"),
            )
            or _read_regular(
                output,
                maximum=MAX_WORKSHEET_BYTES,
                owner=f"written {owner}",
            )
            != raw
        ):
            raise ValueError(f"written {owner} does not match retained bytes")
    except Exception as exc:
        try:
            current = os.lstat(output)
        except OSError:
            current = None
        if (
            current is not None
            and _same_identity(created_identity, current)
            and stat.S_ISREG(current.st_mode)
            and not _is_link_or_reparse(current)
        ):
            output.unlink()
        elif current is not None:
            raise ValueError(
                f"{owner} identity changed; refusing cleanup"
            ) from exc
        raise


def write_selection_template(
    *,
    repository_root: Path,
    draft_root: Path,
    output_path: Path,
) -> None:
    raw = build_selection_template_bytes(
        repository_root=repository_root,
        draft_root=draft_root,
    )
    write_exact_output(
        output_path=output_path,
        raw=raw,
        owner="selection output",
        allow_identical_existing=False,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--draft", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--output", type=Path)
    action.add_argument("--validate-selection", type=Path)
    args = parser.parse_args(argv)
    if args.output is not None:
        write_selection_template(
            repository_root=args.root,
            draft_root=args.draft,
            output_path=args.output,
        )
    else:
        selection_raw = _read_regular(
            args.validate_selection,
            maximum=MAX_WORKSHEET_BYTES,
            owner="completed review selection",
        )
        validate_reviewed_selection_bytes(
            repository_root=args.root,
            draft_root=args.draft,
            selection_raw=selection_raw,
        )
        print("review selection validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
