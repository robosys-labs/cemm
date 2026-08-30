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
    evaluate_selection,
    load_selection_context,
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
    designation_rows_by_case: Mapping[str, Mapping[str, object]]
    purpose_cohorts: Mapping[str, tuple[str, ...]]
    designation_exception_case_refs: frozenset[str]
    routine_designation_cohorts: Mapping[str, tuple[str, ...]]
    overlap_pair_count: int
    intersecting_case_count: int
    multi_unit_case_count: int
    exact_empty_count: int


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
