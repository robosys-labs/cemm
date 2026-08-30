#!/usr/bin/env python3
"""Bounded local session model for accountable R4.1 review."""
from __future__ import annotations

import copy
from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from cemm_authoritative_hybrid.canonical import stable_ref

from scripts.build_r4_1_review_selection import (
    SelectionContext,
    load_selection_context,
)
from scripts.build_r4_1_review_worksheets import (
    MAX_WORKSHEET_BYTES,
    _read_regular,
)


@dataclass(frozen=True)
class ReviewPaths:
    repository_root: Path
    draft_root: Path
    template_path: Path
    working_path: Path
    journal_path: Path
    export_path: Path


@dataclass(frozen=True)
class ReviewIndexes:
    structural_rows_by_ref: Mapping[str, Mapping[str, object]]
    purpose_rows_by_ref: Mapping[str, Mapping[str, object]]
    source_cases_by_ref: Mapping[str, Mapping[str, object]]
    proposal_families_by_ref: Mapping[str, Mapping[str, object]]
    designation_rows_by_case: Mapping[str, Mapping[str, object]]
    purpose_cohorts: Mapping[str, tuple[str, ...]]
    designation_exception_case_refs: frozenset[str]
    routine_designation_cohorts: Mapping[str, tuple[str, ...]]
    overlap_pair_count: int
    intersecting_case_count: int
    multi_unit_case_count: int
    exact_empty_count: int


def _mapping_proxy(
    value: Mapping[str, Mapping[str, object]],
) -> Mapping[str, Mapping[str, object]]:
    return MappingProxyType(
        {key: _freeze_json(row) for key, row in sorted(value.items())}
    )


def _freeze_json(value: object) -> object:
    if type(value) is dict:
        return MappingProxyType(
            {key: _freeze_json(item) for key, item in value.items()}
        )
    if type(value) is list:
        return tuple(_freeze_json(item) for item in value)
    return value


def _thaw_json(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw_json(item) for key, item in value.items()}
    if type(value) is tuple:
        return [_thaw_json(item) for item in value]
    return value


def _overlaps(left: Mapping[str, object], right: Mapping[str, object]) -> bool:
    return left["start"] < right["end"] and right["start"] < left["end"]


def _designation_risk(
    row: Mapping[str, object],
) -> tuple[bool, int, bool, bool, bool]:
    bindings = row["candidate_bindings"]
    if type(bindings) not in {list, tuple}:
        raise ValueError("designation review row has invalid bindings")
    empty = not bindings
    multi_unit = any(len(binding["unit_refs"]) > 1 for binding in bindings)
    overlap_pairs = sum(
        _overlaps(left, right)
        for index, left in enumerate(bindings)
        for right in bindings[index + 1 :]
    )
    span_targets: dict[tuple[int, int], set[tuple[str, str]]] = {}
    for binding in bindings:
        span = (binding["start"], binding["end"])
        span_targets.setdefault(span, set()).add(
            (
                binding["designation_fact_ref"],
                binding["candidate_target_ref"],
            )
        )
    polysemous = any(len(targets) > 1 for targets in span_targets.values())
    exceptional = empty or multi_unit or overlap_pairs > 0 or polysemous
    return exceptional, overlap_pairs, multi_unit, empty, polysemous


def _routine_signature(row: Mapping[str, object]) -> str:
    material = [
        {
            "surface": binding["surface"],
            "start": binding["start"],
            "end": binding["end"],
            "designation_fact_ref": binding["designation_fact_ref"],
            "candidate_target_ref": binding["candidate_target_ref"],
            "unit_count": len(binding["unit_refs"]),
        }
        for binding in row["candidate_bindings"]
    ]
    return stable_ref("review_ui_designation_cohort", {"signature": material})


def build_review_indexes(context: SelectionContext) -> ReviewIndexes:
    supervision = context.decoded["SUPERVISION_DECISIONS.json"]["rows"]
    designation_rows = {
        row["source_case_ref"]: row
        for row in supervision
        if row["row_kind"] == "designation_supervision"
    }
    proposal_families = {
        row["family_ref"]: row
        for row in context.expected_template["proposal_recipe_selections"]
    }
    purpose_groups: dict[str, list[str]] = {}
    for row in context.purpose_rows.values():
        option_labels = tuple(option["label"] for option in row["options"])
        cohort_ref = stable_ref(
            "review_ui_purpose_cohort",
            {
                "row_kind": row["row_kind"],
                "source_classification": row.get("source_classification"),
                "branch_applicability": row.get("branch_applicability"),
                "option_labels": list(option_labels),
            },
        )
        purpose_groups.setdefault(cohort_ref, []).append(row["row_ref"])

    exceptions: set[str] = set()
    routine: dict[str, list[str]] = {}
    overlap_pair_count = 0
    intersecting_case_count = 0
    multi_unit_case_count = 0
    exact_empty_count = 0
    for case_ref, row in designation_rows.items():
        exceptional, overlap_pairs, multi_unit, empty, _ = _designation_risk(row)
        overlap_pair_count += overlap_pairs
        intersecting_case_count += overlap_pairs > 0
        multi_unit_case_count += multi_unit
        exact_empty_count += empty
        if exceptional:
            exceptions.add(case_ref)
        else:
            routine.setdefault(_routine_signature(row), []).append(case_ref)

    return ReviewIndexes(
        structural_rows_by_ref=_mapping_proxy(context.structural_rows),
        purpose_rows_by_ref=_mapping_proxy(context.purpose_rows),
        source_cases_by_ref=_mapping_proxy(context.source_case_rows),
        proposal_families_by_ref=_mapping_proxy(proposal_families),
        designation_rows_by_case=_mapping_proxy(designation_rows),
        purpose_cohorts=MappingProxyType(
            {
                ref: tuple(sorted(members))
                for ref, members in sorted(purpose_groups.items())
            }
        ),
        designation_exception_case_refs=frozenset(exceptions),
        routine_designation_cohorts=MappingProxyType(
            {
                ref: tuple(sorted(members))
                for ref, members in sorted(routine.items())
            }
        ),
        overlap_pair_count=overlap_pair_count,
        intersecting_case_count=intersecting_case_count,
        multi_unit_case_count=multi_unit_case_count,
        exact_empty_count=exact_empty_count,
    )


class ReviewSession:
    def __init__(
        self,
        *,
        paths: ReviewPaths,
        context: SelectionContext,
        state: Mapping[str, object],
        indexes: ReviewIndexes,
    ) -> None:
        self.paths = paths
        self.context = context
        self._state = copy.deepcopy(dict(state))
        self.indexes = indexes
        self.state_revision = 0

    @classmethod
    def open(cls, paths: ReviewPaths) -> "ReviewSession":
        template_raw = _read_regular(
            paths.template_path,
            maximum=MAX_WORKSHEET_BYTES,
            owner="review UI selection template",
        )
        context = load_selection_context(
            repository_root=paths.repository_root,
            draft_root=paths.draft_root,
            template_raw=template_raw,
        )
        return cls(
            paths=paths,
            context=context,
            state=context.expected_template,
            indexes=build_review_indexes(context),
        )

    def bootstrap(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "inventory": {
                    "structural": len(self.indexes.structural_rows_by_ref),
                    "purpose": len(self.indexes.purpose_rows_by_ref),
                    "recipe_family": len(self.indexes.proposal_families_by_ref),
                    "designation": len(self.indexes.designation_rows_by_case),
                },
                "designation_risk_counts": {
                    "intersecting_case": self.indexes.intersecting_case_count,
                    "overlap_pair": self.indexes.overlap_pair_count,
                    "multi_unit_case": self.indexes.multi_unit_case_count,
                    "exact_empty": self.indexes.exact_empty_count,
                },
                "state_revision": self.state_revision,
                "selection_template_ref": self._state["selection_template_ref"],
                "draft_input_set_ref": self._state["draft_input_set_ref"],
            }
        )

    def _decision_items(self, *, section: str) -> list[dict[str, object]]:
        if section == "structural":
            source_rows = self.indexes.structural_rows_by_ref
            selections = {
                row["row_ref"]: row
                for row in self._state["structural_selections"]
            }
        else:
            source_rows = self.indexes.purpose_rows_by_ref
            selections = {
                row["row_ref"]: row for row in self._state["purpose_selections"]
            }
        result = []
        for row_ref, source in source_rows.items():
            selected = selections[row_ref]["selected_option_ref"]
            display = {
                key: _thaw_json(value)
                for key, value in source.items()
                if key
                not in {
                    "decision_state",
                    "options",
                    "row_kind",
                    "row_ref",
                    "selected_option_ref",
                    "subject_ref",
                }
            }
            result.append(
                {
                    "current_value": selected,
                    "display": display,
                "options": _thaw_json(source["options"]),
                    "row_kind": source["row_kind"],
                    "row_ref": row_ref,
                    "state": "completed" if selected is not None else "unresolved",
                    "subject_ref": source["subject_ref"],
                }
            )
        return result

    def _recipe_items(self) -> list[dict[str, object]]:
        return [
            {
                "current_value": copy.deepcopy(row["purpose_recipes"]),
                "display": {
                    "family_definition": copy.deepcopy(row["family_definition"]),
                    "member_case_refs": list(row["member_case_refs"]),
                    "target_kind": row["target_kind"],
                },
                "options": ["approve", "reject"],
                "row_kind": "proposal_recipe_family",
                "row_ref": row["family_ref"],
                "state": "completed" if row["purpose_recipes"] else "unresolved",
                "subject_ref": row["family_ref"],
            }
            for row in self._state["proposal_recipe_selections"]
        ]

    def _designation_items(self) -> list[dict[str, object]]:
        source_by_case = self.indexes.designation_rows_by_case
        result = []
        for row in self._state["designation_selections"]:
            case_ref = row["source_case_ref"]
            source = source_by_case[case_ref]
            decision = row["decision"]
            risk = _designation_risk(source)
            result.append(
                {
                    "current_value": {
                        "approved_binding_refs": copy.deepcopy(
                            row["approved_binding_refs"]
                        ),
                        "decision": decision,
                    },
                    "display": {
                        "candidate_bindings": _thaw_json(
                            source["candidate_bindings"]
                        ),
                        "candidate_set_ref": source["candidate_set_ref"],
                        "exceptional": risk[0],
                        "language": source["language"],
                        "surface": source["surface"],
                    },
                    "options": [
                        "approve_candidate_bindings",
                        "approve_exact_empty",
                        "reject",
                    ],
                    "row_kind": "designation_supervision",
                    "row_ref": case_ref,
                    "state": (
                        "rejected"
                        if decision == "reject"
                        else "completed"
                        if decision is not None
                        else "unresolved"
                    ),
                    "subject_ref": case_ref,
                }
            )
        return result

    def items(
        self,
        *,
        section: str,
        state_filter: str,
        query: str,
        offset: int,
        limit: int,
    ) -> Mapping[str, object]:
        if section not in {"structural", "purpose", "recipe", "designation"}:
            raise ValueError("review item section is invalid")
        if state_filter not in {
            "all",
            "unresolved",
            "completed",
            "rejected",
            "exception",
        }:
            raise ValueError("review item state filter is invalid")
        if type(query) is not str or len(query) > 256:
            raise ValueError("review item query violates its bound")
        if type(offset) is not int or not 0 <= offset <= 4096:
            raise ValueError("review item offset violates its bound")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("review item limit violates its bound")
        if section in {"structural", "purpose"}:
            rows = self._decision_items(section=section)
        elif section == "recipe":
            rows = self._recipe_items()
        else:
            rows = self._designation_items()
        if state_filter == "exception":
            rows = [row for row in rows if row["display"].get("exceptional") is True]
        elif state_filter != "all":
            rows = [row for row in rows if row["state"] == state_filter]
        normalized_query = query.casefold().strip()
        if normalized_query:
            rows = [
                row
                for row in rows
                if normalized_query
                in json.dumps(row, sort_keys=True, ensure_ascii=False).casefold()
            ]
        rows.sort(key=lambda row: (row["row_kind"], row["row_ref"]))
        total = len(rows)
        return {
            "items": rows[offset : offset + limit],
            "limit": limit,
            "offset": offset,
            "section": section,
            "total": total,
        }
