#!/usr/bin/env python3
"""Train the neural switch proposer and save the safetensors artifact.

Usage:
    python scripts/train_proposer.py --config configs/proposal_dev.json \
        --episodes data/bootstrap/proposal_episodes.jsonl \
        --output artifacts/proposal_dev
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
        description="Train the neural switch proposer."
    )
    parser.add_argument(
        "--config",
        default="configs/proposal_dev.json",
        help="Path to the training config JSON.",
    )
    parser.add_argument(
        "--episodes",
        default=None,
        help="Path to the bootstrap episodes JSONL (overrides config).",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output artifact directory (overrides config).",
    )
    parser.add_argument(
        "--release-isolated-root",
        default=None,
        help="Private R4 train-evidence root supplied by the release parent controller.",
    )
    parser.add_argument(
        "--expected-authorization-ref",
        default=None,
        help="Admission-authenticated train authorization ref (release mode only).",
    )
    parser.add_argument(
        "--expected-authorization-sha256",
        default=None,
        help="Admission-authenticated train authorization SHA-256 (release mode only).",
    )
    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    with open(config_path, encoding="utf-8") as fh:
        config = json.load(fh)

    output_dir_value = args.output or config.get("artifact_dir", "artifacts/proposal_dev")
    root = Path(__file__).resolve().parents[1]
    output_dir = root / output_dir_value
    is_release = bool(config.get("release", False)) or "release" in str(output_dir).lower()
    episodes_path = None
    if not is_release:
        episodes_value = args.episodes or config.get("episodes_path", "data/bootstrap/proposal_episodes.jsonl")
        episodes_path = root / episodes_value

    train_batch = None
    if is_release:
        if args.episodes is not None:
            parser.error("--episodes is forbidden in release mode")
        required = {
            "--release-isolated-root": args.release_isolated_root,
            "--expected-authorization-ref": args.expected_authorization_ref,
            "--expected-authorization-sha256": args.expected_authorization_sha256,
        }
        missing = [flag for flag, value in required.items() if not value]
        if missing:
            parser.error("release mode requires " + ", ".join(missing))
        if config.get("train_authorization_trust") != "r4_admission_receipt":
            parser.error("release config must trust only r4_admission_receipt")
        authorization_path = config.get("train_authorization_path")
        capability_path = config.get("train_capability_path")
        if type(authorization_path) is not str or type(capability_path) is not str:
            parser.error("release config requires exact train authorization/capability paths")
        isolated_root = Path(args.release_isolated_root).resolve(strict=True)
        repository_root = root.resolve(strict=True)
        try:
            isolated_root.relative_to(repository_root)
        except ValueError:
            pass
        else:
            parser.error("release isolated root must be outside the repository")
        from cemm_authoritative_hybrid.r4_partition_access import load_r4_train_episodes

        train_batch = load_r4_train_episodes(
            authorization_path,
            capability_path,
            isolated_root,
            expected_authorization_ref=args.expected_authorization_ref,
            expected_authorization_sha256=args.expected_authorization_sha256,
        )

    print("Training neural switch proposer")
    print(f"  Config: {config_path}")
    print(f"  Data mode: {'authenticated-r4-train' if is_release else 'bootstrap'}")
    if episodes_path is not None:
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

    # Build components
    from cemm_authoritative_hybrid.config import RuntimeConfig
    from cemm_authoritative_hybrid.contributions import ContributionExpander
    from cemm_authoritative_hybrid.affordances import SemanticAffordanceIndex
    from cemm_authoritative_hybrid.coverage import CoverageVerifier
    from cemm_authoritative_hybrid.forms import FormResolver
    from cemm_authoritative_hybrid.grounding import Grounder
    from cemm_authoritative_hybrid.verifier import (
        ActionMasker,
        ExactProgramVerifier,
        LegalActionIndex,
    )

    rc = RuntimeConfig.release()

    form_pack_path = root / "data" / "languages" / "en" / "forms.json"
    with open(form_pack_path, encoding="utf-8") as fh:
        form_pack = json.load(fh)

    from cemm_authoritative_hybrid.canonical import canonical_bytes
    import hashlib
    form_pack_hash = f"sha256:{hashlib.sha256(canonical_bytes(form_pack)).hexdigest()}"

    form_resolver = FormResolver(form_pack, rc)
    affordance_index = SemanticAffordanceIndex(linked, rc)
    coverage_verifier = CoverageVerifier(rc)
    verifier = ExactProgramVerifier(linked, rc, coverage_verifier)
    legal_action_index = LegalActionIndex(linked, rc)
    action_masker = ActionMasker(legal_action_index)

    from cemm_authoritative_hybrid.authority import DesignationIndex

    class _StaticDesignationStore:
        def build_index(self) -> DesignationIndex:
            return linked.designations

    grounder = Grounder(
        authority=linked,
        config=rc,
        form_pack=form_pack,
        form_pack_hash=form_pack_hash,
        designation_store=_StaticDesignationStore(),
    )

    # Release mode is train-capability-only; bootstrap paths are never accepted.
    if is_release:
        from cemm_authoritative_hybrid.training import (
            ReleaseProposalTrainer,
            save_proposal_release_artifact,
            _git_revision,
        )

        if train_batch is None:
            raise RuntimeError("release train batch was not authenticated")

        trainer = ReleaseProposalTrainer(
            authority=linked,
            config=rc,
            form_resolver=form_resolver,
            grounder=grounder,
            affordance_index=affordance_index,
            verifier=verifier,
            coverage_verifier=coverage_verifier,
            legal_action_index=legal_action_index,
            hidden=config.get("hidden", 64),
            layers=config.get("layers", 2),
            max_form_tokens=config.get("max_form_tokens", 32),
            max_actions=config.get("max_actions", 24),
            epochs=config.get("epochs", 60),
            learning_rate=config.get("learning_rate", 0.003),
            seed=config.get("seed", 3502),
            device=config.get("device", "cpu"),
            root=root,
        )
        report = trainer.fit(train_batch)
        revision = _git_revision(root)
        manifest_sha256, final_metadata = save_proposal_release_artifact(
            output_dir, trainer, report, revision
        )
        network = trainer._network
        metadata_template = trainer.build_metadata()
    else:
        from cemm_authoritative_hybrid.training import train_proposer, save_proposer_artifact

        network, metadata_template, report = train_proposer(
            episodes_path,
            linked,
            rc,
            form_resolver=form_resolver,
            grounder=grounder,
            affordance_index=affordance_index,
            verifier=verifier,
            coverage_verifier=coverage_verifier,
            legal_action_index=legal_action_index,
            hidden=config.get("hidden", 64),
            layers=config.get("layers", 2),
            max_form_tokens=config.get("max_form_tokens", 32),
            max_actions=config.get("max_actions", 24),
            epochs=config.get("epochs", 60),
            learning_rate=config.get("learning_rate", 0.003),
            seed=config.get("seed", 3502),
            device=config.get("device", "cpu"),
        )
        manifest_sha256, final_metadata = save_proposer_artifact(
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
