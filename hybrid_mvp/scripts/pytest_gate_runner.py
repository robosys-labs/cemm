from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Mapping, Sequence


def _load_pytest():
    import_root_text = os.environ.pop("CEMM_PYTEST_IMPORT_ROOT", None)
    if import_root_text is not None:
        if (
            not import_root_text
            or import_root_text != import_root_text.strip()
            or any(ord(character) < 32 for character in import_root_text)
        ):
            raise RuntimeError("pytest import root is invalid")
        import_root = Path(import_root_text)
        if not import_root.is_absolute():
            raise RuntimeError("pytest import root must be absolute")
        try:
            resolved = import_root.resolve(strict=True)
        except OSError as exc:
            raise RuntimeError("pytest import root is unavailable") from exc
        if not resolved.is_dir():
            raise RuntimeError("pytest import root is not a directory")
        resolved_text = str(resolved)
        if resolved_text not in sys.path:
            sys.path.append(resolved_text)
    try:
        import pytest as loaded_pytest
    except ModuleNotFoundError as exc:
        if exc.name != "pytest":
            raise
        raise RuntimeError("pytest is unavailable in the isolated interpreter") from exc
    return loaded_pytest


pytest = _load_pytest()


SELECTOR_SCHEMA = "cemm-pytest-selector-v1"
REPORT_SCHEMA = "cemm-pytest-report-v1"
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
MAX_REPORT_BYTES = 32 * 1024 * 1024
MAX_NODE_COUNT = 5_000
MAX_NODE_ID_CHARS = 1_024
MAX_ERROR_ROWS = 100
MAX_ERROR_CHARS = 4_096
DEFAULT_SLOWEST_LIMIT = 10
MAX_SLOWEST_LIMIT = 100

_SELECTOR_REF_RE = re.compile(r"^pytest_selector:[0-9a-f]{24}$")
_REPORT_PHASES = {"setup", "call", "teardown"}
_REPORT_OUTCOMES = {"passed", "failed", "skipped"}
_PHASE_ORDER = {"setup": 0, "call": 1, "teardown": 2}
_COUNT_KEYS = ("error", "failure", "passed", "skip", "xfail", "xpass")


class ManifestError(ValueError):
    """The selector manifest is malformed, unsafe, or has the wrong identity."""


class ReportError(RuntimeError):
    """The structured report cannot be represented within its fixed bounds."""


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _content_ref(kind: str, value: object) -> str:
    digest = hashlib.sha256(_canonical_bytes(value)).hexdigest()
    return f"{kind}:{digest[:24]}"


def _reject_json_constant(value: str) -> None:
    raise ManifestError(f"non-finite JSON constant is forbidden: {value}")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ManifestError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _validate_json_structure(value: object) -> None:
    stack: list[tuple[object, int]] = [(value, 0)]
    nodes = 0
    while stack:
        item, depth = stack.pop()
        nodes += 1
        if nodes > 100_000:
            raise ManifestError("selector manifest exceeds its JSON node bound")
        if depth > 32:
            raise ManifestError("selector manifest exceeds its JSON depth bound")
        if isinstance(item, dict):
            stack.extend((child, depth + 1) for child in item.values())
        elif isinstance(item, list):
            stack.extend((child, depth + 1) for child in item)
        elif item is None or type(item) in {str, int, bool}:
            continue
        elif type(item) is float and math.isfinite(item):
            continue
        else:
            raise ManifestError("selector manifest contains a non-canonical scalar")

def _load_canonical_json(path: Path) -> Mapping[str, object]:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_MANIFEST_BYTES + 1)
    except OSError as exc:
        raise ManifestError(f"cannot read selector manifest: {exc}") from exc
    if not raw:
        raise ManifestError("selector manifest is empty")
    if len(raw) > MAX_MANIFEST_BYTES:
        raise ManifestError("selector manifest exceeds its byte bound")
    try:
        text = raw.decode("utf-8")
        value = json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_json_constant,
        )
        _validate_json_structure(value)
    except ManifestError:
        raise
    except (
        UnicodeDecodeError, json.JSONDecodeError, ValueError, RecursionError,
    ) as exc:
        raise ManifestError(f"selector manifest is not strict JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ManifestError("selector manifest must be a JSON object")
    try:
        canonical = _canonical_bytes(value)
    except (TypeError, ValueError) as exc:
        raise ManifestError(f"selector manifest is not canonical JSON: {exc}") from exc
    if raw != canonical:
        raise ManifestError("selector manifest bytes are not canonical")
    return value


def _validate_node_id(node_id: object, *, field: str) -> str:
    if not isinstance(node_id, str):
        raise ManifestError(f"{field} entries must be strings")
    if not node_id or node_id.strip() != node_id:
        raise ManifestError(f"{field} contains an empty or padded node ID")
    if len(node_id) > MAX_NODE_ID_CHARS:
        raise ManifestError(f"{field} contains an overlong node ID")
    if any(ord(character) < 32 for character in node_id):
        raise ManifestError(f"{field} contains a control character")
    if "::" not in node_id:
        raise ManifestError(f"{field} entries must be exact pytest node IDs")
    file_part, object_part = node_id.split("::", 1)
    if not object_part:
        raise ManifestError(f"{field} entries must name an exact test")
    if "\\" in file_part or file_part.startswith("/") or ":" in file_part:
        raise ManifestError(f"{field} contains an unsafe node path")
    path_parts = file_part.split("/")
    if (
        not file_part.endswith(".py")
        or not path_parts
        or path_parts[0] != "tests"
        or any(part in {"", ".", ".."} for part in path_parts)
    ):
        raise ManifestError(f"{field} contains an unsafe node path")
    return node_id


def _validate_node_ids(value: object, *, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) and not isinstance(value, tuple):
        raise ManifestError(f"{field} must be an array")
    if not value:
        raise ManifestError(f"{field} must not be empty")
    if len(value) > MAX_NODE_COUNT:
        raise ManifestError(f"{field} exceeds its node-count bound")
    nodes = tuple(_validate_node_id(node, field=field) for node in value)
    if list(nodes) != sorted(set(nodes)):
        raise ManifestError(f"{field} must be sorted and duplicate-free")
    return nodes


@dataclass(frozen=True)
class SelectorManifest:
    schema: str
    selector_ref: str
    mode: str
    exact_node_ids: tuple[str, ...] = ()
    test_root: str | None = None
    collectable_node_ids: tuple[str, ...] = ()
    active_node_ids: tuple[str, ...] = ()

    @classmethod
    def for_exact(
        cls,
        selector_ref: str,
        node_ids: Sequence[str],
    ) -> "SelectorManifest":
        nodes = _validate_node_ids(tuple(node_ids), field="exact_node_ids")
        return cls(
            schema=SELECTOR_SCHEMA,
            selector_ref=selector_ref,
            mode="exact",
            exact_node_ids=nodes,
            active_node_ids=nodes,
        )

    @classmethod
    def for_admission(
        cls,
        selector_ref: str,
        *,
        test_root: str,
        collectable_node_ids: Sequence[str],
        active_node_ids: Sequence[str],
    ) -> "SelectorManifest":
        if test_root != "tests":
            raise ManifestError("test_root must be the pinned root 'tests'")
        collectable = _validate_node_ids(
            tuple(collectable_node_ids),
            field="collectable_node_ids",
        )
        active = _validate_node_ids(tuple(active_node_ids), field="active_node_ids")
        if not set(active).issubset(collectable):
            raise ManifestError("active_node_ids must be a subset of collectable_node_ids")
        return cls(
            schema=SELECTOR_SCHEMA,
            selector_ref=selector_ref,
            mode="admission",
            test_root=test_root,
            collectable_node_ids=collectable,
            active_node_ids=active,
        )

    @property
    def expected_collected_node_ids(self) -> tuple[str, ...]:
        if self.mode == "exact":
            return self.exact_node_ids
        return self.collectable_node_ids

    @property
    def pytest_targets(self) -> tuple[str, ...]:
        if self.mode == "exact":
            return self.exact_node_ids
        if self.test_root is None:
            raise ManifestError("admission manifest has no test_root")
        return (self.test_root,)


def load_selector_manifest(path: Path | str) -> SelectorManifest:
    source = Path(path)
    value = _load_canonical_json(source)
    mode = value.get("mode")
    if mode == "exact":
        allowed = {"schema", "selector_ref", "mode", "exact_node_ids"}
    elif mode == "admission":
        allowed = {
            "schema",
            "selector_ref",
            "mode",
            "test_root",
            "collectable_node_ids",
            "active_node_ids",
        }
    else:
        raise ManifestError("selector mode must be 'exact' or 'admission'")
    if set(value) != allowed:
        missing = sorted(allowed - set(value))
        extra = sorted(set(value) - allowed)
        raise ManifestError(
            f"selector fields do not match its mode; missing={missing}, extra={extra}"
        )
    if value["schema"] != SELECTOR_SCHEMA:
        raise ManifestError(f"selector schema must be {SELECTOR_SCHEMA}")
    selector_ref = value["selector_ref"]
    if not isinstance(selector_ref, str) or not _SELECTOR_REF_RE.fullmatch(selector_ref):
        raise ManifestError("selector_ref has an invalid form")
    identity_payload = dict(value)
    identity_payload.pop("selector_ref")
    expected_ref = _content_ref("pytest_selector", identity_payload)
    if selector_ref != expected_ref:
        raise ManifestError("selector manifest identity does not match its content")
    if mode == "exact":
        return SelectorManifest.for_exact(selector_ref, value["exact_node_ids"])
    test_root = value["test_root"]
    if not isinstance(test_root, str):
        raise ManifestError("test_root must be a string")
    return SelectorManifest.for_admission(
        selector_ref,
        test_root=test_root,
        collectable_node_ids=value["collectable_node_ids"],
        active_node_ids=value["active_node_ids"],
    )


def _bounded_text(value: object) -> str:
    if isinstance(value, str):
        text = value
    else:
        try:
            text = str(value)
        except Exception as exc:
            text = f"<unprintable {type(value).__name__}: {type(exc).__name__}>"
    if len(text) <= MAX_ERROR_CHARS:
        return text
    return text[: MAX_ERROR_CHARS - 1] + "…"


def _duplicate_node_ids(node_ids: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for node_id in node_ids:
        if node_id in seen:
            duplicates.add(node_id)
        seen.add(node_id)
    return sorted(duplicates)


class StructuredReportPlugin:
    def __init__(
        self,
        manifest: SelectorManifest,
        *,
        report_path: Path | str | None = None,
        slowest_limit: int = DEFAULT_SLOWEST_LIMIT,
    ) -> None:
        if isinstance(slowest_limit, bool) or not isinstance(slowest_limit, int):
            raise ValueError("slowest_limit must be an integer")
        if not 0 <= slowest_limit <= MAX_SLOWEST_LIMIT:
            raise ValueError("slowest_limit is outside its bound")
        self.manifest = manifest
        self.report_path = Path(report_path) if report_path is not None else None
        self.slowest_limit = slowest_limit
        self.collected_node_ids: tuple[str, ...] = ()
        self.selected_node_ids: tuple[str, ...] = ()
        self._selected_node_id_set: set[str] = set()
        self.deselected_node_ids: tuple[str, ...] = ()
        self.collection_mismatch: dict[str, list[str]] | None = None
        self.collection_errors: list[dict[str, str]] = []
        self._collection_error_count = 0
        self._collection_seen = False
        self._collection_finished = False
        self._reports: dict[str, list[dict[str, object]]] = {}
        self._malformed_nodes: set[str] = set()
        self._error_codes: set[str] = set()
        self._errors: list[dict[str, str]] = []
        self._errors_truncated = False
        self._written_payload: dict[str, object] | None = None

    @classmethod
    def for_unit_test(
        cls,
        manifest: SelectorManifest,
        *,
        slowest_limit: int = DEFAULT_SLOWEST_LIMIT,
    ) -> "StructuredReportPlugin":
        return cls(manifest, slowest_limit=slowest_limit)

    @property
    def written_payload(self) -> dict[str, object] | None:
        return self._written_payload

    @pytest.fixture
    def tmp_path(self, request: Any) -> Path:
        """Provide an isolated path without pytest's Windows 0o700 ACL trap."""
        if self.report_path is None:
            raise RuntimeError("runner-owned tmp_path requires a report path")
        base = self.report_path.parent / ".pytest-runtime" / "fixture-tmp"
        base.mkdir(parents=True, exist_ok=True)
        node_id = str(request.node.nodeid)
        digest = hashlib.sha256(node_id.encode("utf-8")).hexdigest()[:24]
        target = base / digest
        target.mkdir(exist_ok=False)
        return target
    def _append_error(
        self,
        code: str,
        message: object,
        *,
        node_id: str | None = None,
        fatal: bool,
    ) -> None:
        if fatal:
            self._error_codes.add(code)
        if len(self._errors) >= MAX_ERROR_ROWS:
            self._errors_truncated = True
            return
        row = {"code": code, "message": _bounded_text(message)}
        if node_id is not None:
            row["node_id"] = _bounded_text(node_id)
        self._errors.append(row)

    def record_infrastructure_error(self, code: str, message: object) -> None:
        self._append_error(code, message, fatal=True)

    def pytest_collection_modifyitems(
        self,
        session: Any,
        config: Any,
        items: list[Any],
    ) -> None:
        actual = tuple(str(item.nodeid) for item in items)
        self._collection_seen = True
        self.collected_node_ids = tuple(sorted(actual))
        expected = self.manifest.expected_collected_node_ids
        duplicates = _duplicate_node_ids(actual)
        actual_set = set(actual)
        expected_set = set(expected)
        extra = sorted(actual_set - expected_set)
        missing = sorted(expected_set - actual_set)
        if duplicates or extra or missing or len(actual) != len(expected):
            self.collection_mismatch = {
                "duplicate_node_ids": duplicates,
                "extra_node_ids": extra,
                "missing_node_ids": missing,
            }
            self._error_codes.add("collection_mismatch")
            self._append_error(
                "collection_mismatch",
                "collected node IDs do not equal the selector manifest",
                fatal=False,
            )
            rejected = list(items)
            self.deselected_node_ids = tuple(sorted(actual))
            if rejected:
                config.hook.pytest_deselected(items=rejected)
            items[:] = []
            self.selected_node_ids = ()
            self._selected_node_id_set = set()
            session.shouldfail = "selector manifest collection mismatch"
            return

        if self.manifest.mode == "admission":
            active = set(self.manifest.active_node_ids)
            selected = [item for item in items if str(item.nodeid) in active]
            deselected = [item for item in items if str(item.nodeid) not in active]
            if deselected:
                config.hook.pytest_deselected(items=deselected)
            items[:] = selected
            self.selected_node_ids = tuple(sorted(str(item.nodeid) for item in selected))
            self.deselected_node_ids = tuple(
                sorted(str(item.nodeid) for item in deselected)
            )
        else:
            self.selected_node_ids = tuple(sorted(actual))
            self.deselected_node_ids = ()
        self._selected_node_id_set = set(self.selected_node_ids)

    def pytest_collection_finish(self, session: Any) -> None:
        del session
        self._collection_finished = True

    def pytest_collectreport(self, report: Any) -> None:
        if getattr(report, "outcome", None) != "failed":
            return
        self._collection_error_count += 1
        self._error_codes.add("collection_error")
        node_id = _bounded_text(getattr(report, "nodeid", "<unknown>"))
        message = _bounded_text(getattr(report, "longrepr", "collection failed"))
        if len(self.collection_errors) < MAX_ERROR_ROWS:
            self.collection_errors.append({"message": message, "node_id": node_id})
        else:
            self._errors_truncated = True

    def pytest_runtest_logreport(self, report: Any) -> None:
        node_id = getattr(report, "nodeid", None)
        when = getattr(report, "when", None)
        outcome = getattr(report, "outcome", None)
        duration = getattr(report, "duration", None)
        valid_duration = (
            not isinstance(duration, bool)
            and isinstance(duration, (int, float))
            and math.isfinite(float(duration))
            and float(duration) >= 0
        )
        if (
            not isinstance(node_id, str)
            or when not in _REPORT_PHASES
            or outcome not in _REPORT_OUTCOMES
            or not valid_duration
        ):
            malformed_node = node_id if isinstance(node_id, str) else "<unknown>"
            self._malformed_nodes.add(malformed_node)
            self._append_error(
                "malformed_report",
                "pytest supplied a malformed runtest report",
                node_id=malformed_node,
                fatal=True,
            )
            return
        if node_id not in self._selected_node_id_set:
            self._append_error(
                "unexpected_report",
                "pytest supplied a report for an unselected node",
                node_id=node_id,
                fatal=True,
            )
            return
        reports = self._reports.setdefault(node_id, [])
        if any(existing["when"] == when for existing in reports):
            self._malformed_nodes.add(node_id)
            self._append_error(
                "duplicate_report_phase",
                f"pytest supplied more than one {when} report",
                node_id=node_id,
                fatal=True,
            )
            return
        wasxfail = getattr(report, "wasxfail", None) is not None
        reports.append(
            {
                "duration": float(duration),
                "outcome": outcome,
                "wasxfail": wasxfail,
                "when": when,
            }
        )
        if outcome == "failed":
            code = "test_failure" if when == "call" else "test_error"
            self._append_error(
                code,
                getattr(report, "longrepr", f"{when} phase failed"),
                node_id=node_id,
                fatal=False,
            )

    def _classify(self, reports: Sequence[Mapping[str, object]]) -> str | None:
        if any(
            report["outcome"] == "failed" and report["when"] in {"setup", "teardown"}
            for report in reports
        ):
            return "error"
        if any(
            report["outcome"] == "failed" and report["when"] == "call"
            for report in reports
        ):
            return "failure"
        if any(
            report["outcome"] == "skipped" and bool(report["wasxfail"])
            for report in reports
        ):
            return "xfail"
        if any(
            report["outcome"] == "passed" and bool(report["wasxfail"])
            for report in reports
        ):
            return "xpass"
        if any(report["outcome"] == "skipped" for report in reports):
            return "skip"
        if (
            tuple(report["when"] for report in reports)
            == ("setup", "call", "teardown")
            and all(
                report["outcome"] == "passed" and not bool(report["wasxfail"])
                for report in reports
            )
        ):
            return "passed"
        return None

    def finalize(self, *, exitstatus: int) -> dict[str, object]:
        if type(exitstatus) is not int:
            raise ReportError("pytest exit status is not an integer")
        normalized_exitstatus = exitstatus

        error_codes = set(self._error_codes)
        errors = [dict(row) for row in self._errors]
        errors_truncated = self._errors_truncated

        def append_derived_error(code: str, message: str, node_id: str) -> None:
            nonlocal errors_truncated
            error_codes.add(code)
            if len(errors) >= MAX_ERROR_ROWS:
                errors_truncated = True
                return
            errors.append(
                {
                    "code": code,
                    "message": _bounded_text(message),
                    "node_id": _bounded_text(node_id),
                }
            )

        if (
            not self._collection_seen
            and not self.collection_errors
            and "pytest_exception" not in error_codes
        ):
            error_codes.add("collection_not_observed")
            if len(errors) < MAX_ERROR_ROWS:
                errors.append(
                    {
                        "code": "collection_not_observed",
                        "message": "pytest did not expose a collection to the runner",
                    }
                )
            else:
                errors_truncated = True
        elif self._collection_seen and not self._collection_finished:
            error_codes.add("collection_not_finished")
            if len(errors) < MAX_ERROR_ROWS:
                errors.append(
                    {
                        "code": "collection_not_finished",
                        "message": _bounded_text(
                            "pytest collection did not reach its finish hook"
                        ),
                    }
                )
            else:
                errors_truncated = True

        facts: list[dict[str, object]] = []
        counts = {key: 0 for key in _COUNT_KEYS}
        for node_id in self.selected_node_ids:
            reports = self._reports.get(node_id, [])
            classification: str | None
            if node_id in self._malformed_nodes:
                classification = "error"
            else:
                classification = self._classify(reports)
            if classification is None:
                classification = "error"
                append_derived_error(
                    "missing_report",
                    "selected node has no classifiable pytest report",
                    node_id,
                )
            ordered_reports = sorted(
                reports,
                key=lambda report: _PHASE_ORDER[str(report["when"])],
            )
            try:
                duration_ns = int(
                    round(
                        sum(float(report["duration"]) for report in ordered_reports)
                        * 1_000_000_000
                    )
                )
            except (ArithmeticError, ValueError) as exc:
                classification = "error"
                duration_ns = 0
                append_derived_error(
                    "duration_aggregation_error",
                    "pytest duration could not be represented as integer nanoseconds "
                    f"({type(exc).__name__})",
                    node_id,
                )
            facts.append(
                {
                    "classification": classification,
                    "duration_ns": duration_ns,
                    "node_id": node_id,
                    "reports": [
                        {
                            "outcome": report["outcome"],
                            "wasxfail": report["wasxfail"],
                            "when": report["when"],
                        }
                        for report in ordered_reports
                    ],
                }
            )
            counts[classification] += 1
        counts["error"] += self._collection_error_count

        if error_codes or counts["error"]:
            disposition = "error"
        elif any(counts[key] for key in ("failure", "skip", "xfail", "xpass")):
            disposition = "failed"
        elif normalized_exitstatus != 0:
            disposition = "error"
            error_codes.add("pytest_exit_status")
            if len(errors) < MAX_ERROR_ROWS:
                errors.append(
                    {
                        "code": "pytest_exit_status",
                        "message": f"pytest exited with status {normalized_exitstatus}",
                    }
                )
            else:
                errors_truncated = True
        else:
            disposition = "passed"

        slowest_source = sorted(
            (
                (int(fact["duration_ns"]), str(fact["node_id"]))
                for fact in facts
            ),
            key=lambda row: (-row[0], row[1]),
        )
        slowest = [
            {"duration_ns": duration_ns, "node_id": node_id}
            for duration_ns, node_id in slowest_source[: self.slowest_limit]
        ]
        payload: dict[str, object] = {
            "active_node_ids": list(self.manifest.active_node_ids),
            "collected_node_ids": list(self.collected_node_ids),
            "collection_errors": [dict(row) for row in self.collection_errors],
            "collection_mismatch": self.collection_mismatch,
            "counts": counts,
            "deselected_node_ids": list(self.deselected_node_ids),
            "disposition": disposition,
            "error_codes": sorted(error_codes),
            "errors": errors,
            "errors_truncated": errors_truncated,
            "exit_status": normalized_exitstatus,
            "expected_collected_node_ids": list(
                self.manifest.expected_collected_node_ids
            ),
            "facts": facts,
            "mode": self.manifest.mode,
            "schema": REPORT_SCHEMA,
            "selected_node_ids": list(self.selected_node_ids),
            "selector_ref": self.manifest.selector_ref,
            "slowest": slowest,
            "test_root": self.manifest.test_root,
        }
        payload["report_ref"] = _content_ref("pytest_report", payload)
        if len(_canonical_bytes(payload)) > MAX_REPORT_BYTES:
            raise ReportError("structured pytest report exceeds its byte bound")
        return payload

    def write_report(self, *, exitstatus: int) -> dict[str, object]:
        if self.report_path is None:
            raise ReportError("no report path was configured")
        payload = self.finalize(exitstatus=exitstatus)
        raw = _canonical_bytes(payload)
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        with self.report_path.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        self._written_payload = payload
        return payload

    def pytest_sessionfinish(self, session: Any, exitstatus: int) -> None:
        del session
        if self.report_path is not None:
            self.write_report(exitstatus=int(exitstatus))


def _bootstrap_error_payload(code: str, message: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "active_node_ids": [],
        "collected_node_ids": [],
        "collection_errors": [],
        "collection_mismatch": None,
        "counts": {key: 0 for key in _COUNT_KEYS},
        "deselected_node_ids": [],
        "disposition": "error",
        "error_codes": [code],
        "errors": [{"code": code, "message": _bounded_text(message)}],
        "errors_truncated": False,
        "exit_status": 2,
        "expected_collected_node_ids": [],
        "facts": [],
        "mode": None,
        "schema": REPORT_SCHEMA,
        "selected_node_ids": [],
        "selector_ref": None,
        "slowest": [],
        "test_root": None,
    }
    payload["report_ref"] = _content_ref("pytest_report", payload)
    return payload


def _write_payload_exclusive(path: Path, payload: Mapping[str, object]) -> None:
    raw = _canonical_bytes(payload)
    if len(raw) > MAX_REPORT_BYTES:
        raise ReportError("structured pytest report exceeds its byte bound")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one manifest-pinned pytest gate and emit structured JSON.",
    )
    parser.add_argument("--selector-manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    return parser


def _restore_environment(previous: Mapping[str, str | None]) -> None:
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    report_path = args.report.resolve()
    if report_path.exists():
        print(f"structured report already exists: {report_path}", file=sys.stderr)
        return 2
    try:
        manifest = load_selector_manifest(args.selector_manifest)
    except ManifestError as exc:
        try:
            _write_payload_exclusive(
                report_path,
                _bootstrap_error_payload("selector_manifest_invalid", exc),
            )
        except (OSError, ReportError, ArithmeticError) as write_exc:
            print(f"cannot write structured report: {write_exc}", file=sys.stderr)
        return 2

    project_root = Path(__file__).resolve().parents[1]

    run_root = report_path.parent
    runtime_root = run_root / ".pytest-runtime"
    temp_dir = runtime_root / "temp"
    pycache_dir = runtime_root / "pycache"
    hypothesis_dir = runtime_root / "hypothesis"
    for directory in (temp_dir, pycache_dir, hypothesis_dir):
        directory.mkdir(parents=True, exist_ok=True)

    environment_keys = (
        "HYPOTHESIS_STORAGE_DIRECTORY", "TMP", "TEMP", "TMPDIR",
        "PYTHONPYCACHEPREFIX",
    )
    previous_environment = {key: os.environ.get(key) for key in environment_keys}
    os.environ["TMP"] = str(temp_dir)
    os.environ["TEMP"] = str(temp_dir)
    os.environ["TMPDIR"] = str(temp_dir)
    os.environ["PYTHONPYCACHEPREFIX"] = str(pycache_dir)
    os.environ["HYPOTHESIS_STORAGE_DIRECTORY"] = str(hypothesis_dir)

    plugin = StructuredReportPlugin(manifest, report_path=report_path)
    pytest_args = [
        *manifest.pytest_targets,
        "-c",
        str(project_root / "pyproject.toml"),
        "--confcutdir",
        str(project_root / "tests"),
        "-p",
        "no:tmpdir",
        "-p",
        "no:cacheprovider",
        "--capture=no",
    ]
    try:
        try:
            pytest_exitstatus = int(pytest.main(pytest_args, plugins=[plugin]))
        except Exception as exc:
            plugin.record_infrastructure_error(
                "pytest_exception",
                f"{type(exc).__name__}: {exc}",
            )
            if plugin.written_payload is None:
                try:
                    plugin.write_report(exitstatus=2)
                except (OSError, ReportError, ArithmeticError) as write_exc:
                    print(f"cannot write structured report: {write_exc}", file=sys.stderr)
            return 2
    finally:
        _restore_environment(previous_environment)

    payload = plugin.written_payload
    if payload is None:
        try:
            payload = plugin.write_report(exitstatus=pytest_exitstatus)
        except (OSError, ReportError, ArithmeticError) as exc:
            print(f"cannot write structured report: {exc}", file=sys.stderr)
            return 2
    disposition = payload.get("disposition")
    if disposition == "passed":
        return 0
    if disposition == "failed":
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
