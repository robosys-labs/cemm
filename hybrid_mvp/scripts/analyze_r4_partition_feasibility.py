#!/usr/bin/env python3
"""Reconstruct the read-only R4 global partition feasibility authority."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Callable

from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.r4_episodes import AuthenticEpisode
from cemm_authoritative_hybrid.r4_mutations import SemanticMutation
from cemm_authoritative_hybrid.r4_partition_config import R4PartitionConfig
from cemm_authoritative_hybrid.r4_partition_contracts import (
    MAX_EPISODE_INPUT_BYTES,
    MAX_PARTITION_ARTIFACT_BYTES,
    canonical_json_bytes,
)
from cemm_authoritative_hybrid.r4_partitions import GlobalLeakagePartitioner

ROOT = Path(__file__).resolve().parents[1]
EPISODES = ROOT / "artifacts/r4/episodes.jsonl"
MUTATIONS = ROOT / "artifacts/r4/mutations.jsonl"
CONFIG = ROOT / "configs/r4_partitions.json"
BASIS = ROOT / "artifacts/validation/R4_PARTITION_FEASIBILITY_BASIS.json"
FINAL = ROOT / "artifacts/validation/R4_PARTITION_FEASIBILITY.json"


def _load_jsonl(path: Path, decoder: Callable[[dict[str, Any]], Any]) -> tuple[Any, ...]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"unsafe source path: {path}")
    raw = path.read_bytes()
    if not raw or len(raw) > MAX_EPISODE_INPUT_BYTES:
        raise ValueError(f"source byte bound violated: {path}")
    rows = []
    for line_no, line in enumerate(raw.splitlines(), 1):
        if not line:
            continue
        try:
            value = json.loads(line.decode("utf-8"))
        except Exception as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_no}") from exc
        if type(value) is not dict:
            raise TypeError("JSONL rows must be exact objects")
        rows.append(decoder(value))
    return tuple(rows)


def _source_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _basis_payload() -> dict[str, Any]:
    episodes = _load_jsonl(EPISODES, AuthenticEpisode.from_dict)
    mutations = _load_jsonl(MUTATIONS, SemanticMutation.from_dict)
    graph, feasibility = GlobalLeakagePartitioner().analyze_feasibility(
        episodes, mutations=mutations
    )
    if not feasibility.four_nonempty_possible:
        raise ValueError(
            "four-class feasibility failed: "
            + ",".join(feasibility.infeasibility_reasons)
        )
    witness_rows = [row.as_dict() for row in feasibility.assignment_witness]
    minima_rows = [row.as_dict() for row in feasibility.candidate_minima]
    maxima_rows = [row.as_dict() for row in feasibility.candidate_maxima]
    dimension_rows = [row.as_dict() for row in feasibility.dimension_support]
    minima_witness_ref = stable_ref(
        "r4_partition_minima_witness_v1",
        {
            "graph_ref": graph.graph_ref,
            "minima": minima_rows,
            "maxima": maxima_rows,
            "assignment_witness": witness_rows,
            "witness_objective_ref": feasibility.witness_objective_ref,
        },
    )
    material = {
        "abi_version": 1,
        "source_set_ref": graph.source_set_ref,
        "graph_ref": graph.graph_ref,
        "episodes_sha256": _source_sha256(EPISODES),
        "mutations_sha256": _source_sha256(MUTATIONS),
        "source_count": feasibility.source_count,
        "hyperedge_count": len(graph.hyperedges),
        "label_count": len(graph.labels),
        "component_count": feasibility.component_count,
        "largest_component_count": feasibility.largest_component_count,
        "component_size_histogram": [
            {"component_size": size, "component_count": count}
            for size, count in feasibility.component_size_histogram
        ],
        "dimension_support": dimension_rows,
        "candidate_minima": minima_rows,
        "candidate_maxima": maxima_rows,
        "assignment_witness": witness_rows,
        "witness_objective_ref": feasibility.witness_objective_ref,
        "minima_witness_ref": minima_witness_ref,
        "four_nonempty_possible": feasibility.four_nonempty_possible,
        "infeasibility_reasons": list(feasibility.infeasibility_reasons),
        "solver": {
            key: value
            for key, value in feasibility.solver_stats.as_dict().items()
            if key != "wall_seconds_millis"
        },
    }
    return {
        **material,
        "feasibility_basis_ref": stable_ref(
            "r4_partition_feasibility_basis_v1", material
        ),
    }


def _final_payload() -> dict[str, Any]:
    basis = _basis_payload()
    config = R4PartitionConfig.from_json_bytes(CONFIG.read_bytes())
    if config.feasibility_basis_ref != basis["feasibility_basis_ref"]:
        raise ValueError("config feasibility_basis_ref does not bind current basis")
    if config.minima_witness_ref != basis["minima_witness_ref"]:
        raise ValueError("config minima_witness_ref does not bind current witness")
    if [row.as_dict() for row in config.minima] != basis["candidate_minima"]:
        raise ValueError("config minima differ from reviewed feasibility basis")
    if [row.as_dict() for row in config.maxima] != basis["candidate_maxima"]:
        raise ValueError("config maxima differ from reviewed feasibility basis")
    material = {
        "abi_version": 1,
        "config_ref": config.config_ref,
        "feasibility_basis_ref": basis["feasibility_basis_ref"],
        "minima_witness_ref": basis["minima_witness_ref"],
        "graph_ref": basis["graph_ref"],
        "source_set_ref": basis["source_set_ref"],
        "source_count": basis["source_count"],
        "component_count": basis["component_count"],
        "witness_objective_ref": basis["witness_objective_ref"],
        "assignment_witness": basis["assignment_witness"],
        "solver": basis["solver"],
        "passed": True,
    }
    return {
        **material,
        "receipt_ref": stable_ref("r4_partition_feasibility_v1", material),
    }


def _canonical(value: dict[str, Any]) -> bytes:
    raw = canonical_json_bytes(value)
    if len(raw) > MAX_PARTITION_ARTIFACT_BYTES:
        raise ValueError("feasibility artifact exceeds hard byte bound")
    return raw


def _atomic_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("refusing to replace symlink output")
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
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--basis", action="store_true")
    mode.add_argument("--final", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check", type=Path)
    args = parser.parse_args()
    if (args.output is None) == (args.check is None):
        parser.error("exactly one of --output or --check is required")
    payload = _basis_payload() if args.basis else _final_payload()
    raw = _canonical(payload)
    path = args.output if args.output is not None else args.check
    assert path is not None
    path = path if path.is_absolute() else ROOT / path
    if args.check is not None:
        if not path.is_file() or path.is_symlink() or path.read_bytes() != raw:
            raise SystemExit(f"feasibility artifact drift: {path}")
        print(payload.get("feasibility_basis_ref") or payload.get("receipt_ref"))
        return 0
    _atomic_write(path, raw)
    print(payload.get("feasibility_basis_ref") or payload.get("receipt_ref"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
