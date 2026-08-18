#!/usr/bin/env python3
"""Strict equal-only publisher for the frozen R4 feasibility basis."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

from cemm_authoritative_hybrid.r4_partition_config import R4PartitionConfig
from cemm_authoritative_hybrid.r4_partition_contracts import MAX_PARTITION_ARTIFACT_BYTES

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path) -> tuple[bytes, dict[str, object]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"unsafe feasibility path: {path}")
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_PARTITION_ARTIFACT_BYTES:
        raise ValueError(f"feasibility artifact violates byte bound: {path}")
    value = json.loads(raw.decode("utf-8"))
    if type(value) is not dict:
        raise TypeError("feasibility artifact must be an exact object")
    return raw, value


def _atomic_replace(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--current", type=Path, required=True)
    args = parser.parse_args()
    candidate_path = args.candidate if args.candidate.is_absolute() else ROOT / args.candidate
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    current_path = args.current if args.current.is_absolute() else ROOT / args.current
    candidate_raw, candidate = _load(candidate_path)
    current_raw, current = _load(current_path)
    config = R4PartitionConfig.from_json_bytes(config_path.read_bytes())
    identity_keys = ("feasibility_basis_ref", "minima_witness_ref")
    if any(candidate.get(key) != getattr(config, key) for key in identity_keys):
        return 3
    if any(current.get(key) != getattr(config, key) for key in identity_keys):
        raise ValueError("current basis does not match frozen config authority")
    # Equal identities are publishable. Byte equality is a no-op; otherwise the
    # candidate atomically replaces the current evidence while preserving the
    # reviewed basis/witness identity.
    if candidate_raw != current_raw:
        backup = current_raw
        try:
            _atomic_replace(current_path, candidate_raw)
        except Exception:
            _atomic_replace(current_path, backup)
            raise
    print(candidate["feasibility_basis_ref"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
