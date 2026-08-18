#!/usr/bin/env python3
"""Build a new deterministic R4 ABI 4 candidate tree.

The environment module must expose
``build_environment(project_root, execution_state_root, *, source_revision)``
and return authentic authority/runtime/mutation owners.  This command never
modifies an existing artifact tree: ``--output`` must name a new path.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.r4_episodes import PublicRuntimeEpisodeOwner
from cemm_authoritative_hybrid.r4_partition_config import R4PartitionConfig
from cemm_authoritative_hybrid.r4_pipeline import R4Pipeline


def _load_factory(path: Path):
    source_root = (ROOT / "src").resolve()
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(source_root)
    except ValueError:
        relative = None
    if relative is not None and relative.suffix == ".py":
        module_name = ".".join(relative.with_suffix("").parts)
        module = importlib.import_module(module_name)
    else:
        spec = importlib.util.spec_from_file_location("cemm_r4_environment", resolved)
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
    parser.add_argument("--source-revision", required=True)
    parser.add_argument(
        "--scenarios",
        type=Path,
        default=ROOT / "data" / "scenarios" / "use_cases.jsonl",
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--sufficiency-config",
        type=Path,
        default=ROOT / "configs" / "r4_structural_sufficiency.json",
    )
    parser.add_argument(
        "--partition-config",
        type=Path,
        default=ROOT / "configs" / "r4_partitions.json",
    )
    args = parser.parse_args()

    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(f"candidate output already exists: {output}")
    partition_config = R4PartitionConfig.from_json_bytes(
        args.partition_config.resolve().read_bytes()
    )
    structural_config = json.loads(
        args.sufficiency_config.resolve().read_text(encoding="utf-8")
    )
    if type(structural_config) is not dict:
        raise TypeError("structural sufficiency config must be an object")

    build_environment = _load_factory(args.environment.resolve())
    execution_state = TemporaryDirectory(prefix="cemm-r4-build-state-")
    environment = None
    try:
        environment = build_environment(
            ROOT,
            Path(execution_state.name),
            source_revision=args.source_revision,
        )
        if not isinstance(environment, Mapping):
            raise TypeError("build_environment must return a mapping")
        required = {
            "authority",
            "revision_pin",
            "abi_registry_ref",
            "runtime_factory",
            "mutation_owner",
            "source_revision",
        }
        missing = sorted(required - set(environment))
        if missing:
            raise ValueError(f"environment mapping is missing: {missing}")
        if environment["source_revision"] != args.source_revision:
            raise ValueError("environment source revision differs from requested source revision")

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
            partition_config=partition_config,
            minimums=structural_config.get("minimums"),
            maximums=structural_config.get("maximums"),
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
        inventory = pipeline.write_candidate_tree(result, output)
    finally:
        if environment is not None:
            close_environment = environment.get("close")
            if close_environment is not None:
                if not callable(close_environment):
                    raise TypeError("environment close owner must be callable")
                close_environment()
        execution_state.cleanup()

    print(
        json.dumps(
            {
                "receipt": result.receipt.as_dict(),
                "paths": [path.as_posix() for path in inventory],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
