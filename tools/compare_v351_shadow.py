#!/usr/bin/env python3
"""Compare normalized Phase-18 old/new shadow captures."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from cemm.v350.finalization.shadow_v351 import compare_shadow_capture_v351


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("old", type=Path)
    parser.add_argument("new", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-latency-ratio", type=float, default=1.25)
    parser.add_argument("--maximum-storage-ratio", type=float, default=1.20)
    args = parser.parse_args()
    old = json.loads(args.old.read_text(encoding="utf-8"))
    new = json.loads(args.new.read_text(encoding="utf-8"))
    report = compare_shadow_capture_v351(
        old, new,
        maximum_latency_ratio=args.maximum_latency_ratio,
        maximum_storage_ratio=args.maximum_storage_ratio,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
