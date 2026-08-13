#!/usr/bin/env python3
"""Generate or check the authenticated R5 test-disposition receipt."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.r5_test_dispositions import (  # noqa: E402
    R5TestDispositionError,
    build_r5_test_disposition_receipt,
    load_r5_test_dispositions,
)
from scripts.test_inventory_core import content_ref, load_strict_json  # noqa: E402


RECEIPT_RELATIVE_PATH = Path("artifacts/validation/R5_TEST_DISPOSITIONS.json")
MAX_RECEIPT_BYTES = 1024 * 1024
_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "inventory_ref",
        "disposition_source_sha256",
        "literal_metadata_ref",
        "counts",
        "rows",
        "receipt_ref",
    }
)


class R5DispositionReceiptError(ValueError):
    """Raised when receipt generation or checking fails closed."""


def _is_reparse_point(path: Path) -> bool:
    if path.is_symlink():
        return True
    is_junction = getattr(path, "is_junction", None)
    if callable(is_junction) and is_junction():
        return True
    try:
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
    except OSError:
        return False
    marker = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & marker)


def _atomic_write(path: Path, data: bytes) -> None:
    """Durably stage bytes beside ``path`` and replace it atomically."""

    if type(data) is not bytes:
        raise R5DispositionReceiptError("atomic receipt payload must be bytes")
    parent = path.parent
    if _is_reparse_point(parent) or _is_reparse_point(path):
        raise R5DispositionReceiptError("receipt path cannot cross a reparse point")
    try:
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.",
            suffix=".tmp",
            dir=parent,
        )
    except OSError as exc:
        raise R5DispositionReceiptError("cannot stage atomic receipt write") from exc
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if path.exists():
            os.chmod(temporary, path.stat().st_mode)
        os.replace(temporary, path)
    except BaseException as exc:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass
        if isinstance(exc, OSError):
            raise R5DispositionReceiptError("atomic replace failed for receipt") from exc
        raise


def _canonical_bytes(value: object) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            + b"\n"
        )
    except (TypeError, ValueError) as exc:
        raise R5DispositionReceiptError("receipt is not canonical JSON") from exc


def build_receipt(root: Path = ROOT) -> dict[str, object]:
    """Reconstruct the receipt from all three authenticated source owners."""

    root_path = Path(root).resolve()
    try:
        inventory = load_strict_json(root_path / "governance" / "test_inventory.json")
        if type(inventory) is not dict:
            raise R5DispositionReceiptError("test inventory must be an object")
        inventory_ref = inventory.get("inventory_ref")
        if type(inventory_ref) is not str:
            raise R5DispositionReceiptError("test inventory ref is missing")
        dispositions = load_r5_test_dispositions(
            root_path,
            expected_inventory_ref=inventory_ref,
        )
        receipt = build_r5_test_disposition_receipt(root_path, dispositions)
    except R5TestDispositionError as exc:
        raise R5DispositionReceiptError(str(exc)) from exc
    _validate_receipt_structure(receipt)
    return receipt


def canonical_receipt_bytes(root: Path = ROOT) -> bytes:
    """Return deterministic checked receipt bytes without writing a path."""

    return _canonical_bytes(build_receipt(root))


def _validate_receipt_structure(candidate: object) -> None:
    if type(candidate) is not dict or set(candidate) != _RECEIPT_FIELDS:
        raise R5DispositionReceiptError("receipt must have exact authenticated fields")
    if candidate.get("schema") != "cemm-r5-test-disposition-receipt-v1":
        raise R5DispositionReceiptError("receipt schema does not match")
    counts = candidate.get("counts")
    if counts != {"successor": 17, "deferred": 25, "retired": 1}:
        raise R5DispositionReceiptError("receipt counts do not match")
    rows = candidate.get("rows")
    if type(rows) is not list or len(rows) != 43:
        raise R5DispositionReceiptError("receipt rows do not match the exact partition")
    without_ref = {key: value for key, value in candidate.items() if key != "receipt_ref"}
    if candidate.get("receipt_ref") != content_ref(
        "r5_test_disposition_receipt",
        without_ref,
    ):
        raise R5DispositionReceiptError("receipt_ref does not match receipt content")


def validate_receipt(root: Path, candidate: object) -> None:
    """Require exact equality with a fresh authenticated reconstruction."""

    _validate_receipt_structure(candidate)
    expected = build_receipt(root)
    if candidate != expected:
        raise R5DispositionReceiptError(
            "receipt does not match authenticated inventory, disposition, and metadata"
        )


def _exact_artifact_path(root: Path, supplied: Path) -> Path:
    root_input = Path(os.path.abspath(root))
    if _is_reparse_point(root_input):
        raise R5DispositionReceiptError("receipt root cannot be a reparse point")
    root_path = root_input.resolve()
    expected = root_path / RECEIPT_RELATIVE_PATH
    if supplied.is_absolute():
        exact_name = supplied == expected
    else:
        exact_name = supplied.as_posix() == RECEIPT_RELATIVE_PATH.as_posix()
    if not exact_name:
        raise R5DispositionReceiptError(
            f"receipt path must be exactly {RECEIPT_RELATIVE_PATH.as_posix()}"
        )
    current = root_input
    for part in RECEIPT_RELATIVE_PATH.parts:
        current = current / part
        if _is_reparse_point(current):
            raise R5DispositionReceiptError(
                "receipt artifact path must be contained without reparse points"
            )
    try:
        expected.resolve().relative_to(root_path)
    except ValueError as exc:
        raise R5DispositionReceiptError(
            "receipt artifact path must remain contained"
        ) from exc
    return expected


def _read_checked_artifact(path: Path) -> object:
    if path.is_symlink() or not path.is_file():
        raise R5DispositionReceiptError("receipt artifact must be a regular file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_RECEIPT_BYTES + 1)
    if len(raw) > MAX_RECEIPT_BYTES:
        raise R5DispositionReceiptError("receipt artifact exceeds its byte bound")
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise R5DispositionReceiptError("receipt artifact is not UTF-8 JSON") from exc
    if raw != _canonical_bytes(value):
        raise R5DispositionReceiptError("receipt artifact is not canonical JSON bytes")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--output", type=Path)
    mode.add_argument("--check", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        supplied = args.output if args.output is not None else args.check
        assert supplied is not None
        target = _exact_artifact_path(ROOT, supplied)
        if args.output is not None:
            _atomic_write(target, canonical_receipt_bytes(ROOT))
        else:
            validate_receipt(ROOT, _read_checked_artifact(target))
    except R5DispositionReceiptError as exc:
        print(f"R5 test disposition receipt failed: {exc}", file=sys.stderr)
        return 1
    print(RECEIPT_RELATIVE_PATH.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
