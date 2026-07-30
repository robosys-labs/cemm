#!/usr/bin/env python
"""Partition semantic episodes into sealed lineage-aware splits.

Reads all episodes from a JSONL file, generates hard negatives, builds
connected components of episodes sharing protected lineage values, and assigns
whole components to train/validation/test using a seeded stratified bin-packing
algorithm.  Emits immutable manifest hashes and counts.

Usage::

    python scripts/partition_episodes.py --input data/episodes/all.jsonl --config configs/partitions.json --output data/partitions
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the src directory is on the path.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.partitions import (
    HardNegativeGenerator,
    Partitioner,
    load_partition_episodes,
    write_partition_episodes,
    write_partition_manifest,
)


def load_config(config_path: Path) -> dict:
    """Load the partition configuration."""
    return json.loads(config_path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Partition semantic episodes into sealed lineage-aware splits."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=ROOT / "data" / "episodes" / "all.jsonl",
        help="Input episodes JSONL file path.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "configs" / "partitions.json",
        help="Partition configuration JSON file path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "data" / "partitions",
        help="Output directory for partition files.",
    )
    args = parser.parse_args()

    config = load_config(args.config)

    # Load all episodes.
    episodes = load_partition_episodes(args.input)
    print(f"Loaded {len(episodes)} episodes from {args.input}")

    # Load scenarios to determine expected gap kinds.
    scenarios_path = ROOT / "data" / "scenarios" / "use_cases.jsonl"
    scenarios: list[dict] = []
    if scenarios_path.exists():
        for line in scenarios_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                scenarios.append(json.loads(line))

    # Generate hard negatives.
    hard_neg_gen = HardNegativeGenerator(seed=config["seed"])
    hard_negatives = hard_neg_gen.generate(episodes, scenarios=scenarios)
    print(f"Generated {len(hard_negatives)} hard negatives")

    # Combine original episodes with hard negatives.
    all_episodes = episodes + hard_negatives

    # Partition.
    partitioner = Partitioner(
        lineage_keys=config["lineage_keys"],
        seed=config["seed"],
        train_ratio=config["train_ratio"],
        validation_ratio=config["validation_ratio"],
        test_ratio=config["test_ratio"],
    )
    train_eps, val_eps, test_eps, manifest = partitioner.partition(all_episodes)

    # Write partition files.
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    train_path = output_dir / "train.jsonl"
    val_path = output_dir / "validation.jsonl"
    test_path = output_dir / "test.jsonl"

    write_partition_episodes(train_eps, train_path)
    write_partition_episodes(val_eps, val_path)
    write_partition_episodes(test_eps, test_path)

    # Write manifest with computed hashes.
    final_manifest = write_partition_manifest(
        manifest,
        output_dir,
        train_file=train_path,
        validation_file=val_path,
        test_file=test_path,
    )

    print(
        f"Partitioned {len(all_episodes)} episodes -> "
        f"train={final_manifest.train_count}, "
        f"validation={final_manifest.validation_count}, "
        f"test={final_manifest.test_count}"
    )
    print(f"  train_sha256: {final_manifest.train_sha256[:16]}...")
    print(f"  validation_sha256: {final_manifest.validation_sha256[:16]}...")
    print(f"  test_sha256: {final_manifest.test_sha256[:16]}...")
    print(f"Manifest written to {output_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
