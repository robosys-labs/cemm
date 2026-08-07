#!/usr/bin/env python3
"""Build R4 artifacts with an explicitly supplied authentic environment owner.

The factory module must expose:

``build_environment(project_root, output_root) -> mapping``

Required mapping entries:
- ``authority``
- ``revision_pin``
- ``abi_registry_ref``
- ``runtime_factory(expanded_case)``
- ``mutation_owner`` implementing ``execute_mutation(semantic_mutation)``
- ``source_revision``

Optional authentic execution entry:
- ``restart_executor`` implementing ``execute_restart_case(...)``

Optional reviewed derivation entries must be supplied together:
- ``derivation_contracts``
- ``derivation_validator`` implementing ``validate_derivation(...)``

This script deliberately has no fixture/default environment.  R4 must not label
mutations or environmental outcomes by assumption.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.r4_episodes import PublicRuntimeEpisodeOwner
from cemm_authoritative_hybrid.r4_pipeline import R4Pipeline


def _load_factory(path: Path):
    spec = importlib.util.spec_from_file_location("cemm_r4_environment", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load R4 environment module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    owner = getattr(module, "build_environment", None)
    if not callable(owner):
        raise TypeError("environment module must define build_environment")
    return owner


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", type=Path, required=True)
    parser.add_argument(
        "--scenarios", type=Path,
        default=ROOT / "data" / "scenarios" / "use_cases.jsonl",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument(
        "--sufficiency-config", type=Path,
        default=ROOT / "configs" / "r4_structural_sufficiency.json",
    )
    parser.add_argument(
        "--partition-config", type=Path,
        default=ROOT / "configs" / "r4_partitions.json",
    )
    args = parser.parse_args()

    build_environment = _load_factory(args.environment.resolve())
    environment = build_environment(ROOT, args.output.resolve())
    if not isinstance(environment, Mapping):
        raise TypeError("build_environment must return a mapping")
    required = {
        "authority", "revision_pin", "abi_registry_ref", "runtime_factory",
        "mutation_owner", "source_revision",
    }
    missing = sorted(required - set(environment))
    if missing:
        raise ValueError(f"environment mapping is missing: {missing}")
    config = json.loads(args.sufficiency_config.read_text(encoding="utf-8"))
    partition_config = json.loads(
        args.partition_config.read_text(encoding="utf-8")
    )
    ratios_value = partition_config.get("ratios", [60, 20, 20])
    if (
        type(ratios_value) is not list
        or len(ratios_value) != 3
        or any(type(value) is not int or value <= 0 for value in ratios_value)
    ):
        raise ValueError("partition ratios must be three positive integers")
    episode_owner = PublicRuntimeEpisodeOwner(
        environment["runtime_factory"],
        restart_executor=environment.get("restart_executor"),
    )
    pipeline = R4Pipeline(
        authority=environment["authority"],
        revision_pin=environment["revision_pin"],
        abi_registry_ref=environment["abi_registry_ref"],
        episode_owner=episode_owner,
        mutation_owner=environment["mutation_owner"],
        source_revision=environment["source_revision"],
        seed=args.seed,
        minimums=config.get("minimums"),
        maximums=config.get("maximums"),
        partition_ratios=tuple(ratios_value),
    )
    derivations = environment.get("derivation_contracts", ())
    derivation_validator = environment.get("derivation_validator")
    if bool(derivations) != callable(derivation_validator):
        raise ValueError(
            "derivation_contracts and derivation_validator must be supplied together"
        )
    result = pipeline.build(
        args.scenarios.resolve(),
        derivation_contracts=derivations,
        derivation_validator=derivation_validator,
    )
    pipeline.write(result, args.output.resolve())
    print(json.dumps(result.receipt.as_dict(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
