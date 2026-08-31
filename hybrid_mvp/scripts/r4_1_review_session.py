#!/usr/bin/env python3
"""Bounded local session model for accountable R4.1 review."""
from __future__ import annotations

import copy
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import time
from types import MappingProxyType
from typing import Mapping

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid._r4_source_codec import exact_reviewer_refs

from scripts.build_r4_1_review_selection import (
    SelectionContext,
    SelectionEvaluation,
    evaluate_selection,
    load_selection_context,
    validate_reviewed_selection_bytes,
    write_exact_output,
)
from scripts.build_r4_1_review_worksheets import (
    MAX_WORKSHEET_BYTES,
    _is_link_or_reparse,
    _json_bytes,
    _read_regular,
    _same_identity,
    _strict_json,
    _trusted_directory,
)

MAX_JOURNAL_ENTRY_BYTES = 128 * 1024
MAX_JOURNAL_BYTES = 64 * 1024 * 1024
MAX_JOURNAL_ENTRIES = 8192


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
    realization_families_by_ref: Mapping[str, Mapping[str, object]]
    designation_rows_by_case: Mapping[str, Mapping[str, object]]
    purpose_cohorts: Mapping[str, tuple[str, ...]]
    designation_exception_case_refs: frozenset[str]
    routine_designation_cohorts: Mapping[str, tuple[str, ...]]
    designation_cohort_by_case: Mapping[str, str]
    overlap_pair_count: int
    intersecting_case_count: int
    multi_unit_case_count: int
    exact_empty_count: int


@dataclass(frozen=True)
class ReviewAction:
    action_kind: str
    target_refs: tuple[str, ...]
    selected_value: object

    def __post_init__(self) -> None:
        if type(self.action_kind) is not str or not self.action_kind:
            raise TypeError("review action kind must be an exact string")
        if type(self.target_refs) is not tuple:
            raise TypeError("review action target refs must be an exact tuple")
        if (
            not self.target_refs
            or len(self.target_refs) > 512
            or any(type(ref) is not str or not ref for ref in self.target_refs)
            or self.target_refs != tuple(sorted(set(self.target_refs)))
        ):
            raise ValueError("review action target refs are not canonical")
        object.__setattr__(
            self,
            "selected_value",
            _freeze_json(copy.deepcopy(self.selected_value)),
        )

    @classmethod
    def structural(
        cls,
        *,
        row_ref: str,
        selected_option_ref: str,
    ) -> "ReviewAction":
        return cls("structural", (row_ref,), selected_option_ref)

    @classmethod
    def purpose(
        cls,
        *,
        row_refs: tuple[str, ...],
        option_label: str,
    ) -> "ReviewAction":
        return cls("purpose", row_refs, option_label)

    @classmethod
    def recipe(
        cls,
        *,
        family_ref: str,
        purpose: str,
        decision: str,
        reviewed_parameters: Mapping[str, object],
    ) -> "ReviewAction":
        if purpose not in {"train", "selection", "calibration", "frozen_test"}:
            raise ValueError("recipe purpose is invalid")
        if decision not in {"approve", "reject"}:
            raise ValueError("recipe decision is invalid")
        if type(reviewed_parameters) is not dict or len(reviewed_parameters) > 128:
            raise ValueError("recipe reviewed parameter bound is violated")
        _json_bytes(reviewed_parameters)
        return cls(
            "recipe",
            (family_ref,),
            {
                "decision": decision,
                "purpose": purpose,
                "reviewed_parameters": copy.deepcopy(reviewed_parameters),
            },
        )

    @classmethod
    def designation_cohort(
        cls,
        *,
        cohort_ref: str,
        decision: str,
    ) -> "ReviewAction":
        if decision not in {
            "approve_candidate_bindings",
            "approve_exact_empty",
            "reject",
        }:
            raise ValueError("designation decision is invalid")
        return cls("designation_cohort", (cohort_ref,), decision)

    @classmethod
    def designation_cases(
        cls,
        *,
        case_refs: tuple[str, ...],
        decision: str,
        individual: bool,
    ) -> "ReviewAction":
        if decision not in {
            "approve_candidate_bindings",
            "approve_exact_empty",
            "reject",
        }:
            raise ValueError("designation decision is invalid")
        if type(individual) is not bool:
            raise TypeError("designation individual flag must be exact")
        return cls(
            "designation_cases",
            case_refs,
            {"decision": decision, "individual": individual},
        )

    @classmethod
    def from_wire(cls, value: object) -> "ReviewAction":
        if type(value) is not dict or set(value) != {
            "action_kind",
            "target_refs",
            "selected_value",
        }:
            raise ValueError("review action wire fields are invalid")
        kind = value["action_kind"]
        refs = value["target_refs"]
        selected = value["selected_value"]
        if type(kind) is not str or type(refs) is not list:
            raise TypeError("review action wire types are invalid")
        exact_refs = tuple(refs)
        if kind == "structural":
            if len(exact_refs) != 1 or type(selected) is not str:
                raise ValueError("structural action wire value is invalid")
            return cls.structural(
                row_ref=exact_refs[0],
                selected_option_ref=selected,
            )
        if kind == "purpose":
            if type(selected) is not str:
                raise ValueError("purpose action wire value is invalid")
            return cls.purpose(
                row_refs=exact_refs,
                option_label=selected,
            )
        if kind == "recipe":
            if len(exact_refs) != 1 or type(selected) is not dict:
                raise ValueError("recipe action wire value is invalid")
            if set(selected) != {
                "decision",
                "purpose",
                "reviewed_parameters",
            }:
                raise ValueError("recipe action wire fields are invalid")
            return cls.recipe(
                family_ref=exact_refs[0],
                purpose=selected["purpose"],
                decision=selected["decision"],
                reviewed_parameters=selected["reviewed_parameters"],
            )
        if kind == "designation_cohort":
            if len(exact_refs) != 1 or type(selected) is not str:
                raise ValueError("designation cohort wire value is invalid")
            return cls.designation_cohort(
                cohort_ref=exact_refs[0],
                decision=selected,
            )
        if kind == "designation_cases":
            if type(selected) is not dict or set(selected) != {
                "decision",
                "individual",
            }:
                raise ValueError("designation case action wire value is invalid")
            return cls.designation_cases(
                case_refs=exact_refs,
                decision=selected["decision"],
                individual=selected["individual"],
            )
        raise ValueError("review action wire kind is unavailable")


@dataclass(frozen=True)
class ActionPreview:
    preview_hash: str
    state_revision: int
    action: ReviewAction
    affected_refs: tuple[str, ...]
    cleared_refs: tuple[str, ...]
    requires_clear_confirmation: bool
    resulting_counts: Mapping[str, int]


def _optional_metadata(path: Path) -> os.stat_result | None:
    try:
        return os.lstat(path)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise ValueError(f"cannot inspect {path.name}") from exc


def _require_regular_metadata(
    metadata: os.stat_result,
    *,
    owner: str,
) -> None:
    if (
        not stat.S_ISREG(metadata.st_mode)
        or _is_link_or_reparse(metadata)
        or metadata.st_nlink != 1
    ):
        raise ValueError(f"{owner} must be one regular non-link file")


def _atomic_replace_regular(
    *,
    path: Path,
    raw: bytes,
    maximum: int,
    owner: str,
    expected_existing_raw: bytes | None,
) -> None:
    if type(raw) is not bytes or not raw or len(raw) > maximum:
        raise ValueError(f"{owner} violates byte bounds")
    path = Path(path).absolute()
    parent_before = _trusted_directory(path.parent, owner=f"{owner} parent")
    before = _optional_metadata(path)
    if expected_existing_raw is None:
        if before is not None:
            _require_regular_metadata(before, owner=owner)
            raise ValueError(f"{owner} changed before replace")
    else:
        if before is None:
            raise ValueError(f"{owner} changed before replace")
        _require_regular_metadata(before, owner=owner)
        if (
            _read_regular(path, maximum=maximum, owner=owner)
            != expected_existing_raw
        ):
            raise ValueError(f"{owner} changed before replace")

    descriptor: int | None = None
    temporary_name: str | None = None
    temporary_identity: os.stat_result | None = None
    replaced = False
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=path.parent,
        )
        temporary = Path(temporary_name)
        temporary_identity = os.fstat(descriptor)
        with os.fdopen(descriptor, "wb", closefd=False) as stream:
            written = stream.write(raw)
            if written != len(raw):
                raise ValueError(f"{owner} temporary write was incomplete")
            stream.flush()
            os.fsync(stream.fileno())
        os.close(descriptor)
        descriptor = None
        retained = os.lstat(temporary)
        _require_regular_metadata(retained, owner=f"{owner} temporary")
        if (
            not _same_identity(temporary_identity, retained)
            or _read_regular(
                temporary,
                maximum=maximum,
                owner=f"{owner} temporary",
            )
            != raw
            or not _same_identity(
                parent_before,
                _trusted_directory(path.parent, owner=f"{owner} parent"),
            )
        ):
            raise ValueError(f"{owner} temporary file changed")

        current = _optional_metadata(path)
        if expected_existing_raw is None:
            if current is not None:
                raise ValueError(f"{owner} changed before replace")
        else:
            if current is None or before is None:
                raise ValueError(f"{owner} changed before replace")
            _require_regular_metadata(current, owner=owner)
            if (
                not _same_identity(before, current)
                or _read_regular(path, maximum=maximum, owner=owner)
                != expected_existing_raw
            ):
                raise ValueError(f"{owner} changed before replace")
        try:
            os.replace(temporary, path)
        except OSError as exc:
            raise ValueError(f"cannot replace {owner}") from exc
        replaced = True
        after = os.lstat(path)
        _require_regular_metadata(after, owner=owner)
        if (
            not _same_identity(temporary_identity, after)
            or not _same_identity(
                parent_before,
                _trusted_directory(path.parent, owner=f"{owner} parent"),
            )
            or _read_regular(path, maximum=maximum, owner=owner) != raw
        ):
            raise ValueError(f"replaced {owner} does not match retained bytes")
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if not replaced and temporary_name is not None:
            temporary = Path(temporary_name)
            current = _optional_metadata(temporary)
            if (
                current is not None
                and temporary_identity is not None
                and _same_identity(temporary_identity, current)
                and stat.S_ISREG(current.st_mode)
                and not _is_link_or_reparse(current)
            ):
                temporary.unlink()


def _validate_journal_raw(raw: bytes) -> int:
    if not raw or len(raw) > MAX_JOURNAL_BYTES or not raw.endswith(b"\n"):
        raise ValueError("action journal violates byte bounds")
    lines = raw.splitlines(keepends=True)
    if len(lines) > MAX_JOURNAL_ENTRIES:
        raise ValueError("action journal exceeds entry bound")
    for line in lines:
        if len(line) > MAX_JOURNAL_ENTRY_BYTES:
            raise ValueError("action journal entry exceeds byte bound")
        value = _strict_json(line, owner="review UI action journal entry")
        if (
            type(value) is not dict
            or value.get("schema") != "cemm-r4-review-ui-action-v1"
            or _json_bytes(value) != line
        ):
            raise ValueError("action journal entry is not canonical")
    return len(lines)


def _append_journal_entry(
    *,
    path: Path,
    entry: Mapping[str, object],
) -> None:
    entry_raw = _json_bytes(dict(entry))
    if len(entry_raw) > MAX_JOURNAL_ENTRY_BYTES:
        raise ValueError("action journal entry exceeds byte bound")
    metadata = _optional_metadata(path)
    if metadata is None:
        existing = None
        entry_count = 0
    else:
        _require_regular_metadata(metadata, owner="review UI action journal")
        existing = _read_regular(
            path,
            maximum=MAX_JOURNAL_BYTES,
            owner="review UI action journal",
        )
        entry_count = _validate_journal_raw(existing)
    if entry_count >= MAX_JOURNAL_ENTRIES:
        raise ValueError("action journal exceeds entry bound")
    combined = (existing or b"") + entry_raw
    if len(combined) > MAX_JOURNAL_BYTES:
        raise ValueError("action journal exceeds byte bound")
    _atomic_replace_regular(
        path=path,
        raw=combined,
        maximum=MAX_JOURNAL_BYTES,
        owner="review UI action journal",
        expected_existing_raw=existing,
    )


def _journal_warning(path: Path) -> str | None:
    try:
        metadata = _optional_metadata(path)
        if metadata is None:
            return None
        _require_regular_metadata(metadata, owner="review UI action journal")
        raw = _read_regular(
            path,
            maximum=MAX_JOURNAL_BYTES,
            owner="review UI action journal",
        )
        _validate_journal_raw(raw)
    except (OSError, TypeError, ValueError) as exc:
        return f"action journal unavailable: {type(exc).__name__}"
    return None


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
    realization_families = {
        row["family_ref"]: row
        for row in context.expected_template["realization_recipe_selections"]
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
        realization_families_by_ref=_mapping_proxy(realization_families),
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
        designation_cohort_by_case=MappingProxyType(
            {
                case_ref: cohort_ref
                for cohort_ref, members in sorted(routine.items())
                for case_ref in sorted(members)
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
        template_sha256: str,
        working_raw: bytes | None,
        audit_warning: str | None,
    ) -> None:
        self.paths = paths
        self.context = context
        self._state = copy.deepcopy(dict(state))
        self._working_raw = working_raw
        self.indexes = indexes
        self.template_sha256 = template_sha256
        self.state_revision = 0
        self.audit_warning = audit_warning
        self._pending_preview: ActionPreview | None = None
        self._pending_preview_state: dict[str, object] | None = None

    @property
    def state(self) -> Mapping[str, object]:
        return MappingProxyType(copy.deepcopy(self._state))

    @staticmethod
    def _validate_working_state(
        *,
        context: SelectionContext,
        state: object,
    ) -> Mapping[str, object]:
        if type(state) is not dict:
            raise ValueError("working selection must be one object")
        expected = context.expected_template
        if (
            state.get("selection_template_ref")
            != expected["selection_template_ref"]
            or state.get("draft_input_set_ref")
            != expected["draft_input_set_ref"]
        ):
            raise ValueError("stale working selection is not bound to this template")
        if state.get("selection_state") != "unresolved":
            raise ValueError("working selection must remain unresolved")
        reviewers = state.get("reviewer_refs")
        if type(reviewers) is not list:
            raise ValueError("working selection reviewers are invalid")
        if reviewers:
            exact = exact_reviewer_refs(tuple(reviewers), maximum=128)
            if list(exact) != reviewers:
                raise ValueError("working selection reviewers are not canonical")
        evaluate_selection(
            context=context,
            selection=state,
            require_complete=False,
        )
        return state

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
        working_metadata = _optional_metadata(paths.working_path)
        if working_metadata is None:
            working_raw = None
            state = context.expected_template
        else:
            working_raw = _read_regular(
                paths.working_path,
                maximum=MAX_WORKSHEET_BYTES,
                owner="review UI working selection",
            )
            decoded = _strict_json(
                working_raw,
                owner="review UI working selection",
            )
            try:
                state = cls._validate_working_state(
                    context=context,
                    state=decoded,
                )
            except (TypeError, ValueError) as exc:
                if (
                    type(decoded) is dict
                    and (
                        decoded.get("selection_template_ref")
                        != context.expected_template["selection_template_ref"]
                        or decoded.get("draft_input_set_ref")
                        != context.expected_template["draft_input_set_ref"]
                    )
                ):
                    raise ValueError(
                        "stale working selection is not bound to this template"
                    ) from exc
                raise
            if _json_bytes(state) != working_raw:
                raise ValueError("working selection is not canonical")
        return cls(
            paths=paths,
            context=context,
            state=state,
            indexes=build_review_indexes(context),
            template_sha256=hashlib.sha256(template_raw).hexdigest(),
            working_raw=working_raw,
            audit_warning=_journal_warning(paths.journal_path),
        )

    def _commit_working_state(
        self,
        *,
        candidate_state: Mapping[str, object],
        action: Mapping[str, object],
    ) -> None:
        candidate = copy.deepcopy(dict(candidate_state))
        self._validate_working_state(context=self.context, state=candidate)
        raw = _json_bytes(candidate)
        _atomic_replace_regular(
            path=self.paths.working_path,
            raw=raw,
            maximum=MAX_WORKSHEET_BYTES,
            owner="review UI working selection",
            expected_existing_raw=self._working_raw,
        )
        self._state = candidate
        self._working_raw = raw
        self.state_revision += 1
        self._pending_preview = None
        self._pending_preview_state = None
        try:
            _append_journal_entry(
                path=self.paths.journal_path,
                entry={
                    "schema": "cemm-r4-review-ui-action-v1",
                    "selection_template_ref": self._state[
                        "selection_template_ref"
                    ],
                    "selection_template_sha256": self.template_sha256,
                    "action_sequence": self.state_revision,
                    "reviewer_refs": list(self._reviewers()),
                    "action": dict(action),
                    "state_sha256": hashlib.sha256(raw).hexdigest(),
                    "recorded_at_ns": time.time_ns(),
                },
            )
        except (OSError, TypeError, ValueError) as exc:
            self.audit_warning = (
                f"action journal unavailable: {type(exc).__name__}"
            )
        else:
            self.audit_warning = None

    def _reviewers(self) -> tuple[str, ...]:
        reviewers = self._state["reviewer_refs"]
        if not reviewers:
            return ()
        return exact_reviewer_refs(tuple(reviewers), maximum=128)

    def set_reviewers(self, refs: tuple[str, ...]) -> None:
        exact = exact_reviewer_refs(refs, maximum=128)
        candidate = copy.deepcopy(self._state)
        candidate["reviewer_refs"] = list(exact)
        self._commit_working_state(
            candidate_state=candidate,
            action={
                "kind": "set_reviewers",
                "reviewer_refs": list(exact),
            },
        )

    def evaluation(self) -> SelectionEvaluation:
        return evaluate_selection(
            context=self.context,
            selection=self._state,
            require_complete=False,
        )

    @staticmethod
    def _review_status(
        evaluation: SelectionEvaluation,
    ) -> dict[str, object]:
        return {
            "review_complete": evaluation.complete,
            "authoring_ready": (
                evaluation.complete
                and not evaluation.blocking_rejection_refs
            ),
            "blocking_rejection_refs": list(
                evaluation.blocking_rejection_refs
            ),
        }

    @staticmethod
    def _selection_by_ref(
        state: Mapping[str, object],
        *,
        field: str,
        ref_field: str,
    ) -> dict[str, dict[str, object]]:
        rows = state[field]
        if type(rows) is not list:
            raise ValueError(f"working selection {field} is invalid")
        return {row[ref_field]: row for row in rows}

    @staticmethod
    def _selected_source_option(
        source: Mapping[str, object],
        option_ref: str,
    ) -> Mapping[str, object]:
        if type(option_ref) is not str:
            raise TypeError("selected option ref must be an exact string")
        matches = [
            option
            for option in source["options"]
            if option["option_ref"] == option_ref
            and option["selectable"] is True
        ]
        if len(matches) != 1:
            raise ValueError("review action names an unavailable option")
        return matches[0]

    def _apply_structural_action(
        self,
        *,
        candidate: dict[str, object],
        action: ReviewAction,
    ) -> tuple[tuple[str, ...], set[str]]:
        if len(action.target_refs) != 1:
            raise ValueError("structural action requires one exact row")
        row_ref = action.target_refs[0]
        if type(row_ref) is not str or row_ref not in self.indexes.structural_rows_by_ref:
            raise ValueError("structural action references an unknown row")
        source = self.indexes.structural_rows_by_ref[row_ref]
        option = self._selected_source_option(source, action.selected_value)
        selections = self._selection_by_ref(
            candidate,
            field="structural_selections",
            ref_field="row_ref",
        )
        selections[row_ref]["selected_option_ref"] = option["option_ref"]
        cleared: set[str] = set()
        if source["row_kind"] == "legacy_conditional":
            generator = next(
                row
                for row in self.indexes.structural_rows_by_ref.values()
                if row["row_kind"] == "generator_patch"
            )
            generator_ref = generator["row_ref"]
            selected_ref = selections[generator_ref]["selected_option_ref"]
            if selected_ref is not None:
                selected_generator = self._selected_source_option(
                    generator,
                    selected_ref,
                )
                if selected_generator["label"] != option["label"]:
                    selections[generator_ref]["selected_option_ref"] = None
                    cleared.add(generator_ref)
        return (row_ref,), cleared

    def _apply_purpose_action(
        self,
        *,
        candidate: dict[str, object],
        action: ReviewAction,
        before: SelectionEvaluation,
    ) -> tuple[tuple[str, ...], set[str]]:
        refs = action.target_refs
        if (
            type(refs) is not tuple
            or not refs
            or len(refs) > 512
            or refs != tuple(sorted(set(refs)))
            or any(type(ref) is not str for ref in refs)
        ):
            raise ValueError("purpose action requires sorted unique row refs")
        if type(action.selected_value) is not str:
            raise TypeError("purpose option label must be an exact string")
        try:
            sources = [self.indexes.purpose_rows_by_ref[ref] for ref in refs]
        except KeyError as exc:
            raise ValueError("purpose action references an unknown row") from exc
        row_kinds = {source["row_kind"] for source in sources}
        if len(row_kinds) != 1:
            raise ValueError("purpose action must target one row kind")
        if not set(refs) <= before.applicable_purpose_row_refs:
            raise ValueError("purpose action targets a branch-inapplicable row")
        options = []
        for source in sources:
            matches = [
                option
                for option in source["options"]
                if option["label"] == action.selected_value
                and option["selectable"] is True
            ]
            if len(matches) != 1:
                raise ValueError(
                    "purpose action label is unavailable for an exact member"
                )
            options.append(matches[0])
        selections = self._selection_by_ref(
            candidate,
            field="purpose_selections",
            ref_field="row_ref",
        )
        changed_case_refs: set[str] = set()
        for ref, source, option in zip(refs, sources, options, strict=True):
            if selections[ref]["selected_option_ref"] == option["option_ref"]:
                continue
            selections[ref]["selected_option_ref"] = option["option_ref"]
            if source["row_kind"] == "membership":
                changed_case_refs.add(source["source_case_ref"])
            elif source["row_kind"] == "duplicate_group":
                changed_case_refs.update(source["member_case_refs"])

        cleared: set[str] = set()
        if changed_case_refs:
            proposal_recipes = self._selection_by_ref(
                candidate,
                field="proposal_recipe_selections",
                ref_field="family_ref",
            )
            for family_ref, recipe in proposal_recipes.items():
                if (
                    recipe["purpose_recipes"]
                    and changed_case_refs.intersection(recipe["member_case_refs"])
                ):
                    recipe["purpose_recipes"] = []
                    cleared.add(family_ref)
            realization_recipes = self._selection_by_ref(
                candidate,
                field="realization_recipe_selections",
                ref_field="family_ref",
            )
            for family_ref, recipe in realization_recipes.items():
                if (
                    recipe["purpose_recipes"]
                    and changed_case_refs.intersection(recipe["member_case_refs"])
                ):
                    recipe["purpose_recipes"] = []
                    cleared.add(family_ref)
        return refs, cleared

    def _apply_recipe_action(
        self,
        *,
        candidate: dict[str, object],
        action: ReviewAction,
        before: SelectionEvaluation,
    ) -> tuple[tuple[str, ...], set[str]]:
        if len(action.target_refs) != 1:
            raise ValueError("recipe action requires one exact family")
        family_ref = action.target_refs[0]
        field: str
        if family_ref in self.indexes.proposal_families_by_ref:
            family = self.indexes.proposal_families_by_ref[family_ref]
            field = "proposal_recipe_selections"
        elif family_ref in self.indexes.realization_families_by_ref:
            family = self.indexes.realization_families_by_ref[family_ref]
            field = "realization_recipe_selections"
        else:
            raise ValueError("recipe action references an unknown family")
        value = _thaw_json(action.selected_value)
        if type(value) is not dict or set(value) != {
            "decision",
            "purpose",
            "reviewed_parameters",
        }:
            raise ValueError("recipe action value is invalid")
        purpose = value["purpose"]
        members = sorted(
            case_ref
            for case_ref in family["member_case_refs"]
            if before.case_purposes.get(case_ref) == purpose
        )
        if not members:
            raise ValueError("recipe action names an absent purpose partition")
        selections = self._selection_by_ref(
            candidate,
            field=field,
            ref_field="family_ref",
        )
        existing = selections[family_ref]["purpose_recipes"]
        if type(existing) is not list:
            raise ValueError("recipe selection is invalid")
        retained = [row for row in existing if row["purpose"] != purpose]
        retained.append(
            {
                "purpose": purpose,
                "member_case_refs": members,
                "decision": value["decision"],
                "reviewed_parameters": value["reviewed_parameters"],
            }
        )
        retained.sort(key=lambda row: row["purpose"])
        selections[family_ref]["purpose_recipes"] = retained
        return (family_ref,), set()

    @staticmethod
    def _designation_value(
        selection: Mapping[str, object],
        decision: str,
    ) -> tuple[str, list[str] | None]:
        candidates = selection["candidate_binding_refs"]
        if type(candidates) is not list:
            raise ValueError("designation candidate refs are invalid")
        if decision == "approve_candidate_bindings" and candidates:
            return decision, list(candidates)
        if decision == "approve_exact_empty" and not candidates:
            return decision, []
        if decision == "reject":
            return decision, None
        raise ValueError(
            "designation decision is incompatible with its exact candidate set"
        )

    def _apply_designation_action(
        self,
        *,
        candidate: dict[str, object],
        action: ReviewAction,
        before: SelectionEvaluation,
    ) -> tuple[tuple[str, ...], set[str]]:
        if action.action_kind == "designation_cohort":
            cohort_ref = action.target_refs[0]
            try:
                refs = self.indexes.routine_designation_cohorts[cohort_ref]
            except KeyError as exc:
                raise ValueError(
                    "designation action references an unknown routine cohort"
                ) from exc
            decision = action.selected_value
            individual = False
        else:
            refs = action.target_refs
            value = _thaw_json(action.selected_value)
            if type(value) is not dict or set(value) != {
                "decision",
                "individual",
            }:
                raise ValueError("designation action value is invalid")
            decision = value["decision"]
            individual = value["individual"]
        if type(decision) is not str:
            raise TypeError("designation decision must be an exact string")
        exceptions = set(refs) & self.indexes.designation_exception_case_refs
        if exceptions and (individual is not True or len(refs) != 1):
            raise ValueError(
                "exception designation case requires individual review"
            )
        if not set(refs) <= before.active_supervised_case_refs:
            raise ValueError("designation action targets an inactive case")
        selections = self._selection_by_ref(
            candidate,
            field="designation_selections",
            ref_field="source_case_ref",
        )
        for case_ref in refs:
            try:
                selection = selections[case_ref]
            except KeyError as exc:
                raise ValueError(
                    "designation action references an unknown case"
                ) from exc
            selected_decision, approved = self._designation_value(
                selection,
                decision,
            )
            selection["decision"] = selected_decision
            selection["approved_binding_refs"] = approved
        return tuple(refs), set()

    @staticmethod
    def _clear_stale_refs(
        candidate: dict[str, object],
        stale_refs: tuple[str, ...],
    ) -> set[str]:
        stale = set(stale_refs)
        cleared: set[str] = set()
        for row in candidate["purpose_selections"]:
            if row["row_ref"] in stale and row["selected_option_ref"] is not None:
                row["selected_option_ref"] = None
                cleared.add(row["row_ref"])
        for row in candidate["proposal_recipe_selections"]:
            if row["family_ref"] in stale and row["purpose_recipes"]:
                row["purpose_recipes"] = []
                cleared.add(row["family_ref"])
        for row in candidate["realization_recipe_selections"]:
            if row["family_ref"] in stale and row["purpose_recipes"]:
                row["purpose_recipes"] = []
                cleared.add(row["family_ref"])
        for row in candidate["designation_selections"]:
            if row["source_case_ref"] in stale and (
                row["decision"] is not None
                or row["approved_binding_refs"] is not None
            ):
                row["decision"] = None
                row["approved_binding_refs"] = None
                cleared.add(row["source_case_ref"])
        return cleared

    @staticmethod
    def _resulting_counts(
        evaluation: SelectionEvaluation,
    ) -> Mapping[str, int]:
        purpose_counts = {
            purpose: sum(
                selected == purpose
                for selected in evaluation.case_purposes.values()
            )
            for purpose in ("train", "selection", "calibration", "frozen_test")
        }
        return MappingProxyType(
            {
                "active_case": len(evaluation.active_case_refs),
                "active_supervised_case": len(
                    evaluation.active_supervised_case_refs
                ),
                "blocking_error": len(evaluation.blocking_errors),
                "blocking_rejection": len(
                    evaluation.blocking_rejection_refs
                ),
                "calibration": purpose_counts["calibration"],
                "denominator_shortfall": int(
                    "selected purpose denominator minimum is not satisfied"
                    in evaluation.blocking_errors
                ),
                "frozen_test": purpose_counts["frozen_test"],
                "holdout_conflict": int(
                    "challenge holdout crosses selected case purposes"
                    in evaluation.blocking_errors
                ),
                "selection": purpose_counts["selection"],
                "stale_selection": len(evaluation.stale_selection_refs),
                "train": purpose_counts["train"],
                "unresolved_designation": (
                    evaluation.unresolved_designation_count
                ),
                "unresolved_purpose": evaluation.unresolved_purpose_count,
                "unresolved_recipe": evaluation.unresolved_recipe_count,
                "unresolved_realization_recipe": (
                    evaluation.unresolved_realization_recipe_count
                ),
                "unresolved_structural": (
                    evaluation.unresolved_structural_count
                ),
            }
        )

    def preview(self, action: ReviewAction) -> ActionPreview:
        if not self._reviewers():
            raise ValueError("review action requires an accountable reviewer")
        if type(action) is not ReviewAction:
            raise TypeError("review action must be exact")
        before = self.evaluation()
        candidate = copy.deepcopy(self._state)
        if action.action_kind == "structural":
            affected, cleared = self._apply_structural_action(
                candidate=candidate,
                action=action,
            )
        elif action.action_kind == "purpose":
            affected, cleared = self._apply_purpose_action(
                candidate=candidate,
                action=action,
                before=before,
            )
        elif action.action_kind == "recipe":
            affected, cleared = self._apply_recipe_action(
                candidate=candidate,
                action=action,
                before=before,
            )
        elif action.action_kind in {
            "designation_cohort",
            "designation_cases",
        }:
            affected, cleared = self._apply_designation_action(
                candidate=candidate,
                action=action,
                before=before,
            )
        else:
            raise ValueError("review action kind is unavailable")
        intermediate = evaluate_selection(
            context=self.context,
            selection=candidate,
            require_complete=False,
        )
        cleared.update(
            self._clear_stale_refs(candidate, intermediate.stale_selection_refs)
        )
        resulting = evaluate_selection(
            context=self.context,
            selection=candidate,
            require_complete=False,
        )
        cleared_refs = tuple(sorted(cleared))
        state_sha256 = hashlib.sha256(_json_bytes(candidate)).hexdigest()
        preview_hash = stable_ref(
            "r4_review_action_preview",
            {
                "action": {
                    "action_kind": action.action_kind,
                    "selected_value": _thaw_json(action.selected_value),
                    "target_refs": list(action.target_refs),
                },
                "affected_refs": list(affected),
                "cleared_refs": list(cleared_refs),
                "resulting_state_sha256": state_sha256,
                "state_revision": self.state_revision,
            },
        )
        preview = ActionPreview(
            preview_hash=preview_hash,
            state_revision=self.state_revision,
            action=action,
            affected_refs=affected,
            cleared_refs=cleared_refs,
            requires_clear_confirmation=bool(cleared_refs),
            resulting_counts=self._resulting_counts(resulting),
        )
        self._pending_preview = preview
        self._pending_preview_state = candidate
        return preview

    def apply(
        self,
        *,
        preview_hash: str,
        expected_revision: int,
    ) -> Mapping[str, object]:
        pending = self._pending_preview
        candidate = self._pending_preview_state
        if (
            pending is None
            or candidate is None
            or type(preview_hash) is not str
            or type(expected_revision) is not int
            or preview_hash != pending.preview_hash
            or expected_revision != pending.state_revision
            or expected_revision != self.state_revision
        ):
            raise ValueError("stale preview cannot be applied")
        self._commit_working_state(
            candidate_state=candidate,
            action={
                "kind": "apply_review_action",
                "preview_hash": pending.preview_hash,
                "action_kind": pending.action.action_kind,
                "target_refs": list(pending.action.target_refs),
                "selected_value": _thaw_json(pending.action.selected_value),
                "affected_refs": list(pending.affected_refs),
                "cleared_refs": list(pending.cleared_refs),
            },
        )
        result = {
            "affected_refs": list(pending.affected_refs),
            "audit_warning": self.audit_warning,
            "cleared_refs": list(pending.cleared_refs),
            "state_revision": self.state_revision,
        }
        result.update(self._review_status(self.evaluation()))
        return MappingProxyType(result)

    def export(self) -> Mapping[str, object]:
        evaluation = self.evaluation()
        if not evaluation.complete:
            raise ValueError("incomplete review session cannot be exported")
        if self._working_raw is None:
            raise ValueError("complete review session lacks working state")
        retained_working = _read_regular(
            self.paths.working_path,
            maximum=MAX_WORKSHEET_BYTES,
            owner="review UI working selection",
        )
        if retained_working != self._working_raw:
            raise ValueError("working selection changed before export")
        template_raw = _read_regular(
            self.paths.template_path,
            maximum=MAX_WORKSHEET_BYTES,
            owner="review UI selection template",
        )
        current_context = load_selection_context(
            repository_root=self.paths.repository_root,
            draft_root=self.paths.draft_root,
            template_raw=template_raw,
        )
        try:
            current_evaluation = evaluate_selection(
                context=current_context,
                selection=self._state,
                require_complete=True,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("stale review session cannot be exported") from exc
        if not current_evaluation.complete:
            raise ValueError("incomplete review session cannot be exported")
        candidate = copy.deepcopy(self._state)
        candidate["selection_state"] = "reviewed"
        reviewers = self._reviewers()
        if not reviewers or list(reviewers) != candidate["reviewer_refs"]:
            raise ValueError("review export lacks canonical accountable reviewers")
        raw = _json_bytes(candidate)
        validate_reviewed_selection_bytes(
            repository_root=self.paths.repository_root,
            draft_root=self.paths.draft_root,
            selection_raw=raw,
        )
        write_exact_output(
            output_path=self.paths.export_path,
            raw=raw,
            owner="reviewed selection export",
            allow_identical_existing=True,
        )
        status = self._review_status(current_evaluation)
        return MappingProxyType(
            {
                "path": str(self.paths.export_path.absolute()),
                "byte_length": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
                **status,
            }
        )

    def bootstrap(self) -> Mapping[str, object]:
        evaluation = self.evaluation()
        result = {
            "inventory": {
                "structural": len(self.indexes.structural_rows_by_ref),
                "purpose": len(self.indexes.purpose_rows_by_ref),
                "recipe_family": len(self.indexes.proposal_families_by_ref),
                "realization_recipe_family": len(
                    self.indexes.realization_families_by_ref
                ),
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
            "reviewer_refs": list(self._state["reviewer_refs"]),
            "audit_warning": self.audit_warning,
            "review_counts": dict(self._resulting_counts(evaluation)),
        }
        result.update(self._review_status(evaluation))
        return MappingProxyType(result)

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
        evaluation = self.evaluation()
        result = []
        recipe_sections = (
            ("proposal_recipe_family", "proposal_recipe_selections"),
            ("realization_recipe_family", "realization_recipe_selections"),
        )
        for row_kind, state_field in recipe_sections:
            for row in self._state[state_field]:
                eligible = [
                    purpose
                    for purpose in (
                        "train",
                        "selection",
                        "calibration",
                        "frozen_test",
                    )
                    if any(
                        evaluation.case_purposes.get(case_ref) == purpose
                        for case_ref in row["member_case_refs"]
                    )
                ]
                selected = row["purpose_recipes"]
                selected_purposes = {recipe["purpose"] for recipe in selected}
                state = (
                    "rejected"
                    if any(recipe["decision"] == "reject" for recipe in selected)
                    else "completed"
                    if selected_purposes == set(eligible)
                    else "unresolved"
                )
                result.append({
                    "current_value": copy.deepcopy(row["purpose_recipes"]),
                    "display": {
                        "family_definition": copy.deepcopy(row["family_definition"]),
                        "member_case_refs": list(row["member_case_refs"]),
                        "target_kind": row["target_kind"],
                        "eligible_purposes": eligible,
                    },
                    "options": ["approve", "reject"],
                    "row_kind": row_kind,
                    "row_ref": row["family_ref"],
                    "state": state,
                    "subject_ref": row["family_ref"],
                })
        return result

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
                        "routine_cohort_ref": (
                            self.indexes.designation_cohort_by_case.get(case_ref)
                        ),
                        "surface": source["surface"],
                    },
                    "options": (
                        ["approve_candidate_bindings", "reject"]
                        if source["candidate_bindings"]
                        else ["approve_exact_empty", "reject"]
                    ),
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
