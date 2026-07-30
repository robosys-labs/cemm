#!/usr/bin/env python3
"""Train the neural realizer and save the safetensors artifact.

Usage:
    python scripts/train_realizer.py --config configs/realizer_dev.json \
        --episodes data/bootstrap/realization_episodes.jsonl \
        --output artifacts/realizer_dev
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure the package is importable
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train the neural realizer."
    )
    parser.add_argument(
        "--config",
        default="configs/realizer_dev.json",
        help="Path to the training config JSON.",
    )
    parser.add_argument(
        "--episodes",
        default=None,
        help="Path to the realization episodes JSONL (overrides config).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output artifact directory (overrides config).",
    )
    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    with open(config_path, encoding="utf-8") as fh:
        config = json.load(fh)

    episodes_path = args.episodes or config.get("episodes_path", "data/bootstrap/realization_episodes.jsonl")
    output_dir = args.output or config.get("artifact_dir", "artifacts/realizer_dev")

    root = Path(__file__).resolve().parents[1]
    episodes_path = root / episodes_path
    output_dir = root / output_dir

    print(f"Training neural realizer")
    print(f"  Config: {config_path}")
    print(f"  Episodes: {episodes_path}")
    print(f"  Output: {output_dir}")
    print(f"  Hidden: {config.get('hidden', 64)}, Layers: {config.get('layers', 2)}")
    print(f"  Epochs: {config.get('epochs', 60)}, LR: {config.get('learning_rate', 0.003)}")
    print(f"  Seed: {config.get('seed', 3502)}")
    print()

    # Link authority
    from cemm_authoritative_hybrid.authority import AuthorityLinker

    manifest_path = root / "data" / "authority" / "manifest.json"
    linked = AuthorityLinker().link_path(manifest_path)
    print(f"Authority generation: {linked.generation}")
    print(f"Authority compatibility hash: {linked.model_compatibility_hash}")

    # Build config
    from cemm_authoritative_hybrid.config import RuntimeConfig

    rc = RuntimeConfig.release()

    # Train — use the release trainer when the config targets a release artifact.
    is_release = "release" in str(output_dir).lower() or config.get("release", False)

    if is_release:
        from cemm_authoritative_hybrid.training import (
            ReleaseRealizerTrainer,
            save_realizer_release_artifact,
            _git_revision,
        )

        trainer = ReleaseRealizerTrainer(
            authority=linked,
            config=rc,
            hidden=config.get("hidden", 64),
            layers=config.get("layers", 2),
            feature_dim=config.get("feature_dim", 32),
            vocab_size=config.get("vocab_size", 16),
            epochs=config.get("epochs", 60),
            learning_rate=config.get("learning_rate", 0.003),
            seed=config.get("seed", 3502),
            device=config.get("device", "cpu"),
            root=root,
        )
        report = trainer.fit(episodes_path)
        revision = _git_revision(root)
        manifest_sha256, final_metadata = save_realizer_release_artifact(
            output_dir, trainer, report, revision
        )
    else:
        from cemm_authoritative_hybrid.training import train_realizer, save_realizer_artifact

        network, metadata_template, report = train_realizer(
            episodes_path,
            linked,
            rc,
            hidden=config.get("hidden", 64),
            layers=config.get("layers", 2),
            feature_dim=config.get("feature_dim", 32),
            vocab_size=config.get("vocab_size", 16),
            epochs=config.get("epochs", 60),
            learning_rate=config.get("learning_rate", 0.003),
            seed=config.get("seed", 3502),
            device=config.get("device", "cpu"),
        )
        manifest_sha256, final_metadata = save_realizer_artifact(
            output_dir, network, metadata_template, report
        )

    print(f"Training complete!")
    print(f"  Episodes: {report['episodes']}")
    print(f"  Training episodes: {report['training_episodes']}")
    print(f"  Vocab size: {report['vocab_size']}")
    print(f"  Final loss: {report['final_loss']:.6f}")
    print()

    # Save artifact

    print(f"Artifact saved to {output_dir}")
    print(f"  Model identity: {final_metadata.model_identity}")
    print(f"  Action encoding hash: {final_metadata.action_encoding_hash}")
    print(f"  Dataset hash: {final_metadata.dataset_hash}")
    print(f"  Manifest SHA-256: {manifest_sha256}")
    print()
    print("Training receipt:")
    print(json.dumps({
        "model_identity": final_metadata.model_identity,
        "authority_compatibility_hash": final_metadata.authority_compatibility_hash,
        "action_encoding_hash": final_metadata.action_encoding_hash,
        "dataset_hash": final_metadata.dataset_hash,
        "manifest_sha256": manifest_sha256,
        "training_report": report,
    }, indent=2))


if __name__ == "__main__":
    main()
