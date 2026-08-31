#!/usr/bin/env python3
"""Expand the authenticated reviewed scenario source without runtime state."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Iterable, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.r4_contracts import ReviewedScenario
from cemm_authoritative_hybrid.r4_expansion import expand_reviewed_source_universe

_MAX_SCENARIO_BYTES = 8 * 1024 * 1024


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> object:
    raise ValueError(f"non-finite JSON value: {token}")


def _read_source(path: Path) -> tuple[bytes, Iterable[ReviewedScenario]]:
    with path.open("rb") as stream:
        payload = stream.read(_MAX_SCENARIO_BYTES + 1)
    if len(payload) > _MAX_SCENARIO_BYTES:
        raise ValueError("scenario source exceeds byte bound")
    if not payload:
        raise ValueError("scenario source cannot be empty")
    if b"\r" in payload or not payload.endswith(b"\n"):
        raise ValueError("scenario source must use canonical LF JSONL")
    try:
        text = payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ValueError("scenario source must be strict UTF-8") from exc

    def rows() -> Iterable[ReviewedScenario]:
        for line_number, raw_line in enumerate(io.StringIO(text), start=1):
            line = raw_line.removesuffix("\n")
            if not line:
                raise ValueError(f"scenario source contains blank row {line_number}")
            value = json.loads(
                line,
                object_pairs_hook=_reject_duplicate_pairs,
                parse_constant=_reject_nonfinite,
            )
            canonical = json.dumps(
                value,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
            if canonical != line:
                raise ValueError(f"scenario row {line_number} is not canonical JSON")
            yield ReviewedScenario.from_dict(value)

    return payload, rows()


def _atomic_write(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            Path(temporary).unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    source_path = root / "data/scenarios/use_cases.jsonl"
    source_bytes, scenarios = _read_source(source_path)
    authority = AuthorityLinker().link_path(root / "data/authority/manifest.json")
    universe = expand_reviewed_source_universe(scenarios, authority=authority)
    output = (
        "\n".join(
            json.dumps(
                row.as_dict(),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            for row in universe.cases
        )
        + "\n"
    ).encode("utf-8")
    _atomic_write(args.output.resolve(), output)
    summary = {
        "case_set_digest": universe.case_set_digest,
        "expanded_count": universe.expanded_count,
        "output_sha256": hashlib.sha256(output).hexdigest(),
        "scenario_count": universe.scenario_count,
        "scenario_sha256": hashlib.sha256(source_bytes).hexdigest(),
    }
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
