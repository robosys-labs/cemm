#!/usr/bin/env python3
"""Compile reviewed CEMM v3.5 source modules into a deterministic boot DB."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cemm.v350.data import DeterministicSQLiteCompiler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("cemm/data/v350"),
        help="reviewed source-package directory containing manifest.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="destination SQLite boot database",
    )
    parser.add_argument(
        "--writable",
        action="store_true",
        help="leave the compiled artifact writable (tests/development only)",
    )
    args = parser.parse_args(argv)

    result = DeterministicSQLiteCompiler().compile(
        args.source,
        args.output,
        make_read_only=not args.writable,
    )
    print(json.dumps({
        "output_path": str(result.output_path),
        "manifest_fingerprint": result.manifest_fingerprint,
        "record_set_fingerprint": result.record_set_fingerprint,
        "boot_fingerprint": result.boot_fingerprint,
        "record_count": result.record_count,
        "module_counts": dict(result.module_counts),
        "byte_size": result.byte_size,
    }, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
