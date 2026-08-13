"""Strict R5 Test Disposition ABI 1 loading and receipt construction."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Callable


DISPOSITION_SCHEMA = "cemm-r5-test-dispositions-v1"
RECEIPT_SCHEMA = "cemm-r5-test-disposition-receipt-v1"
MAX_JSON_BYTES = 1024 * 1024

_DISPOSITION_PATH = Path("governance/r5_test_dispositions.json")
_INVENTORY_PATH = Path("governance/test_inventory.json")
_TOP_FIELDS = frozenset({"schema", "phase", "inventory_ref", "rows"})
_COMMON_ROW_FIELDS = frozenset(
    {"predecessor_source_test_ref", "assertion_ref", "disposition"}
)
_ROW_FIELDS = {
    "successor": _COMMON_ROW_FIELDS | {"successor_node_ids"},
    "deferred": _COMMON_ROW_FIELDS | {"future_task_ref", "future_owner_ref"},
    "retired": _COMMON_ROW_FIELDS | {"retirement_reason"},
}
_NODE_RE = re.compile(
    r"tests/[A-Za-z0-9_./-]+\.py::[A-Za-z_][A-Za-z0-9_]*"
    r"(?:::[A-Za-z_][A-Za-z0-9_]*)?(?:\[[A-Za-z0-9_.-]+\])?"
)
_ASSERTION_RE = re.compile(r"assertion:[a-z0-9][a-z0-9-]*")
_OWNER_RE = re.compile(r"[a-z][a-z0-9-]*")
_INVENTORY_REF_RE = re.compile(r"test_inventory:[0-9a-f]{24}")
_SAFE_FALLBACK_PREDECESSOR = (
    "tests/test_neural_realizer_weight_use.py::TestNeuralRealizerWeightUse::"
    "test_failure_meaning_uses_safe_fallback"
)
_SAFE_FALLBACK_ASSERTION = (
    "assertion:neural-realizer-weight-use-test-neural-realizer-weight-use-"
    "failure-meaning-uses-safe-fallback"
)
_SAFE_FALLBACK_REASON = (
    "hybrid_mvp/AGENTS.md section 7 requires zero fallback paths in final "
    "release gates; preserving this requirement would reintroduce forbidden "
    "fallback behavior."
)


class R5TestDispositionError(ValueError):
    """Raised when reviewed R5 disposition evidence fails closed."""


@dataclass(frozen=True)
class R5TestDisposition:
    predecessor_source_test_ref: str
    assertion_ref: str
    disposition: str
    successor_node_ids: tuple[str, ...] = ()
    future_task_ref: str | None = None
    future_owner_ref: str | None = None
    retirement_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        row: dict[str, object] = {
            "predecessor_source_test_ref": self.predecessor_source_test_ref,
            "assertion_ref": self.assertion_ref,
            "disposition": self.disposition,
        }
        if self.disposition == "successor":
            row["successor_node_ids"] = list(self.successor_node_ids)
        elif self.disposition == "deferred":
            row["future_task_ref"] = self.future_task_ref
            row["future_owner_ref"] = self.future_owner_ref
        else:
            row["retirement_reason"] = self.retirement_reason
        return row


@dataclass(frozen=True)
class R5TestDispositions:
    schema: str
    phase: str
    inventory_ref: str
    rows: tuple[R5TestDisposition, ...]
    source_sha256: str

    @property
    def counts(self) -> dict[str, int]:
        return {
            disposition: sum(
                row.disposition == disposition for row in self.rows
            )
            for disposition in ("successor", "deferred", "retired")
        }


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise R5TestDispositionError("value is not canonical JSON") from exc


def _reject_constant(value: str) -> object:
    raise R5TestDispositionError(f"non-finite JSON value is forbidden: {value}")


def _strict_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise R5TestDispositionError(f"duplicate JSON object key: {key}")
        result[key] = value
    return result


def _read_json(
    path: Path,
    *,
    maximum: int,
    source_reader: Callable[[Path], bytes] | None = None,
) -> tuple[object, bytes]:
    try:
        if source_reader is None:
            with path.open("rb") as stream:
                raw = stream.read(maximum + 1)
        else:
            raw = source_reader(path)
            if type(raw) is not bytes:
                raise TypeError("source reader returned non-bytes")
    except (OSError, TypeError, ValueError) as exc:
        raise R5TestDispositionError(f"cannot read {path}") from exc
    if not raw:
        raise R5TestDispositionError(f"{path} is empty")
    if len(raw) > maximum:
        raise R5TestDispositionError(f"{path} exceeds the 1 MiB JSON bound")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_pairs,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R5TestDispositionError(f"{path} is not strict UTF-8 JSON") from exc
    return value, raw


def _resolve_contained_regular_file(root: Path, relative_path: Path) -> Path:
    candidate = root / relative_path
    if candidate.is_symlink():
        raise R5TestDispositionError(
            f"reviewed source path cannot be a symlink: {relative_path.as_posix()}"
        )
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise R5TestDispositionError(
            f"reviewed source path escapes the Hybrid MVP root: "
            f"{relative_path.as_posix()}"
        ) from exc
    if not resolved.is_file():
        raise R5TestDispositionError(
            f"reviewed source path is not a regular file: "
            f"{relative_path.as_posix()}"
        )
    return resolved


def _exact_object(
    value: object,
    fields: frozenset[str],
    *,
    context: str,
) -> dict[str, object]:
    if type(value) is not dict:
        raise R5TestDispositionError(f"{context} must be an object")
    actual = set(value)
    if actual != fields:
        raise R5TestDispositionError(
            f"{context} must have exact fields; "
            f"missing={sorted(fields - actual)}, extra={sorted(actual - fields)}"
        )
    return value


def _text(value: object, *, context: str, maximum: int = 1024) -> str:
    if type(value) is not str or not value or len(value) > maximum:
        raise R5TestDispositionError(f"{context} must be bounded non-empty text")
    return value


def _node_id(value: object, *, context: str) -> str:
    node_id = _text(value, context=context, maximum=512)
    if _NODE_RE.fullmatch(node_id) is None or ".." in node_id:
        raise R5TestDispositionError(f"{context} is not a safe test node ID")
    return node_id


def _assertion_ref(value: object, *, context: str) -> str:
    assertion_ref = _text(value, context=context, maximum=256)
    if _ASSERTION_RE.fullmatch(assertion_ref) is None:
        raise R5TestDispositionError(f"{context} is not an assertion ref")
    return assertion_ref


def _parse_row(raw: object, *, index: int) -> R5TestDisposition:
    if type(raw) is not dict:
        raise R5TestDispositionError(f"rows[{index}] must be an object")
    disposition = raw.get("disposition")
    if type(disposition) is not str or disposition not in _ROW_FIELDS:
        raise R5TestDispositionError(f"rows[{index}] has invalid disposition")
    row = _exact_object(raw, _ROW_FIELDS[disposition], context=f"rows[{index}]")
    predecessor = _node_id(
        row["predecessor_source_test_ref"],
        context=f"rows[{index}].predecessor_source_test_ref",
    )
    assertion = _assertion_ref(
        row["assertion_ref"], context=f"rows[{index}].assertion_ref"
    )
    if disposition == "successor":
        raw_successors = row["successor_node_ids"]
        if type(raw_successors) is not list or not raw_successors:
            raise R5TestDispositionError(
                f"rows[{index}].successor_node_ids must be non-empty"
            )
        if len(raw_successors) > 8:
            raise R5TestDispositionError(
                f"rows[{index}].successor_node_ids exceeds its bound"
            )
        successors = tuple(
            _node_id(value, context=f"rows[{index}].successor_node_ids")
            for value in raw_successors
        )
        if len(successors) != len(set(successors)):
            raise R5TestDispositionError(
                f"rows[{index}].successor_node_ids contains duplicates"
            )
        return R5TestDisposition(
            predecessor_source_test_ref=predecessor,
            assertion_ref=assertion,
            disposition=disposition,
            successor_node_ids=successors,
        )
    if disposition == "deferred":
        task = _text(row["future_task_ref"], context=f"rows[{index}].future_task_ref")
        if task != "R5-Neural-Activation":
            raise R5TestDispositionError(
                f"rows[{index}].future_task_ref must equal R5-Neural-Activation"
            )
        owner = _text(
            row["future_owner_ref"],
            context=f"rows[{index}].future_owner_ref",
            maximum=128,
        )
        if _OWNER_RE.fullmatch(owner) is None:
            raise R5TestDispositionError(
                f"rows[{index}].future_owner_ref is invalid"
            )
        return R5TestDisposition(
            predecessor_source_test_ref=predecessor,
            assertion_ref=assertion,
            disposition=disposition,
            future_task_ref=task,
            future_owner_ref=owner,
        )
    reason = _text(
        row["retirement_reason"],
        context=f"rows[{index}].retirement_reason",
    )
    if reason != _SAFE_FALLBACK_REASON:
        raise R5TestDispositionError(
            f"rows[{index}].retirement_reason must cite the zero fallback paths "
            "contract in hybrid_mvp/AGENTS.md section 7"
        )
    if predecessor != _SAFE_FALLBACK_PREDECESSOR or assertion != _SAFE_FALLBACK_ASSERTION:
        raise R5TestDispositionError("only the exact safe-fallback predecessor may retire")
    return R5TestDisposition(
        predecessor_source_test_ref=predecessor,
        assertion_ref=assertion,
        disposition=disposition,
        retirement_reason=reason,
    )


def _r5_inventory_assertions(
    root: Path,
    *,
    expected_inventory_ref: str,
    source_reader: Callable[[Path], bytes] | None = None,
) -> tuple[dict[str, str], frozenset[str]]:
    inventory_path = root / _INVENTORY_PATH
    if source_reader is None:
        inventory_path = _resolve_contained_regular_file(root, _INVENTORY_PATH)
    inventory, _raw = _read_json(
        inventory_path,
        maximum=MAX_JSON_BYTES,
        source_reader=source_reader,
    )
    if type(inventory) is not dict:
        raise R5TestDispositionError("test inventory must be an object")
    if inventory.get("inventory_ref") != expected_inventory_ref:
        raise R5TestDispositionError("test inventory ref does not match expectation")
    records = inventory.get("source_tests")
    if type(records) is not list:
        raise R5TestDispositionError("test inventory source_tests must be an array")
    all_predecessors: set[str] = set()
    r5: dict[str, str] = {}
    for index, raw in enumerate(records):
        if type(raw) is not dict:
            raise R5TestDispositionError(
                f"test inventory source_tests[{index}] must be an object"
            )
        source_ref = _node_id(
            raw.get("source_test_ref"),
            context=f"test inventory source_tests[{index}].source_test_ref",
        )
        if source_ref in all_predecessors:
            raise R5TestDispositionError(
                f"duplicate inventory predecessor: {source_ref}"
            )
        all_predecessors.add(source_ref)
        if raw.get("classification") != "retained" or raw.get("activation_phase") != "R5":
            continue
        assertion = _assertion_ref(
            raw.get("assertion_ref"),
            context=f"test inventory assertion for {source_ref}",
        )
        cases = raw.get("case_node_ids")
        if cases != [source_ref]:
            raise R5TestDispositionError(
                f"R5 predecessor {source_ref} must own exactly its source node"
            )
        r5[source_ref] = assertion
    return r5, frozenset(all_predecessors)


def load_r5_test_dispositions(
    root: Path,
    *,
    expected_inventory_ref: str,
    source_reader: Callable[[Path], bytes] | None = None,
) -> R5TestDispositions:
    """Load reviewed dispositions and prove exact frozen-R5 predecessor coverage."""

    root_path = Path(root).resolve()
    expected = _text(expected_inventory_ref, context="expected_inventory_ref")
    if _INVENTORY_REF_RE.fullmatch(expected) is None:
        raise R5TestDispositionError("expected_inventory_ref is invalid")
    disposition_path = root_path / _DISPOSITION_PATH
    if source_reader is None:
        disposition_path = _resolve_contained_regular_file(root_path, _DISPOSITION_PATH)
    value, raw = _read_json(
        disposition_path,
        maximum=MAX_JSON_BYTES,
        source_reader=source_reader,
    )
    top = _exact_object(value, _TOP_FIELDS, context="R5 test dispositions")
    if top["schema"] != DISPOSITION_SCHEMA:
        raise R5TestDispositionError("R5 test dispositions schema is not exact")
    if top["phase"] != "R5":
        raise R5TestDispositionError("R5 test dispositions phase must equal R5")
    if top["inventory_ref"] != expected:
        raise R5TestDispositionError("R5 test dispositions inventory_ref mismatch")
    rows_raw = top["rows"]
    if type(rows_raw) is not list or not rows_raw or len(rows_raw) > 43:
        raise R5TestDispositionError("R5 disposition row count is out of bounds")
    rows = tuple(_parse_row(row, index=index) for index, row in enumerate(rows_raw))
    predecessors = [row.predecessor_source_test_ref for row in rows]
    if len(predecessors) != len(set(predecessors)):
        raise R5TestDispositionError("duplicate R5 disposition predecessor")

    inventory_assertions, all_predecessors = _r5_inventory_assertions(
        root_path,
        expected_inventory_ref=expected,
        source_reader=source_reader,
    )
    for row in rows:
        predecessor = row.predecessor_source_test_ref
        if predecessor not in inventory_assertions:
            qualifier = "non-R5" if predecessor in all_predecessors else "unknown"
            raise R5TestDispositionError(
                f"{qualifier} disposition predecessor: {predecessor}"
            )
        if inventory_assertions[predecessor] != row.assertion_ref:
            raise R5TestDispositionError(
                f"assertion mismatch for disposition predecessor {predecessor}"
            )
    actual = frozenset(predecessors)
    expected_predecessors = frozenset(inventory_assertions)
    if actual != expected_predecessors or len(rows) != len(inventory_assertions):
        raise R5TestDispositionError(
            "R5 disposition predecessor coverage and row count must be exact; "
            f"missing={sorted(expected_predecessors - actual)}, "
            f"extra={sorted(actual - expected_predecessors)}"
        )
    return R5TestDispositions(
        schema=DISPOSITION_SCHEMA,
        phase="R5",
        inventory_ref=expected,
        rows=rows,
        source_sha256=hashlib.sha256(raw).hexdigest(),
    )


def build_r5_test_disposition_receipt(
    root: Path,
    dispositions: R5TestDispositions,
) -> dict[str, object]:
    """Build a canonical content-derived receipt after literal successor proof."""

    if type(dispositions) is not R5TestDispositions:
        raise R5TestDispositionError("dispositions must be an R5TestDispositions value")
    from scripts.test_inventory_core import InventoryError, content_ref, load_and_verify

    root_path = Path(root).resolve()
    try:
        reviewed = load_r5_test_dispositions(
            root_path,
            expected_inventory_ref=dispositions.inventory_ref,
        )
    except R5TestDispositionError as exc:
        raise R5TestDispositionError(
            f"dispositions do not match reviewed source: {exc}"
        ) from exc
    if dispositions != reviewed:
        raise R5TestDispositionError("dispositions do not match reviewed source")
    dispositions = reviewed
    try:
        inventory = load_and_verify(
            root_path,
            root_path / _INVENTORY_PATH,
            phase="R5",
            enforce_reviewed_counts=True,
        )
    except InventoryError as exc:
        raise R5TestDispositionError(
            f"cannot verify literal successor metadata: {exc}"
        ) from exc
    if inventory.inventory_ref != dispositions.inventory_ref:
        raise R5TestDispositionError("verified inventory ref does not match dispositions")
    for row in dispositions.rows:
        for successor in row.successor_node_ids:
            current = successor
            seen: set[str] = set()
            while current != row.predecessor_source_test_ref:
                if current in seen:
                    raise R5TestDispositionError(
                        f"successor lineage cycle contains {current}"
                    )
                seen.add(current)
                record = inventory.later_nodes.get(current)
                if record is None:
                    raise R5TestDispositionError(
                        f"successor literal node does not exist: {current}"
                    )
                if record.activation_phase != "R5":
                    raise R5TestDispositionError(
                        f"successor does not activate at R5: {current}"
                    )
                if record.assertion_ref != row.assertion_ref:
                    raise R5TestDispositionError(
                        f"successor does not preserve assertion identity: {current}"
                    )
                if record.supersedes_node_id is None:
                    raise R5TestDispositionError(
                        f"successor does not supersede its predecessor: {current}"
                    )
                current = record.supersedes_node_id
    payload: dict[str, object] = {
        "schema": RECEIPT_SCHEMA,
        "inventory_ref": dispositions.inventory_ref,
        "disposition_source_sha256": f"sha256:{dispositions.source_sha256}",
        "literal_metadata_ref": inventory.literal_metadata_ref,
        "counts": dispositions.counts,
        "rows": [row.to_dict() for row in dispositions.rows],
    }
    payload["receipt_ref"] = content_ref("r5_test_disposition_receipt", payload)
    return payload


def _content_ref(kind: str, value: object) -> str:
    digest = hashlib.sha256(_canonical_json_bytes(value)).hexdigest()
    return f"{kind}:{digest[:24]}"


__all__ = [
    "DISPOSITION_SCHEMA",
    "MAX_JSON_BYTES",
    "RECEIPT_SCHEMA",
    "R5TestDisposition",
    "R5TestDispositionError",
    "R5TestDispositions",
    "build_r5_test_disposition_receipt",
    "load_r5_test_dispositions",
]
