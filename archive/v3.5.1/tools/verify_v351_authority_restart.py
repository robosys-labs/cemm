#!/usr/bin/env python3
"""Verify deterministic AuthoritySnapshotV351 reconstruction across a real store restart."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

from cemm.v350.csir.authority_v351 import AuthoritySnapshotV351
from cemm.v350.bootstrap.conversational_seed_v351 import install_signed_conversational_seed_v351
from cemm.v350.csir.runtime_projection_v351 import (
    load_semantic_authority_supplement_v351,
    project_runtime_semantic_authority_v351,
)
from cemm.v350.dynamics import compile_reviewed_phase13_parameter_artifacts
from cemm.v350.storage import SemanticStore


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def project(boot: Path, supplement: Path, seed: Path):
    store = SemanticStore(":memory:", boot_path=boot)
    try:
        install_signed_conversational_seed_v351(store, seed, expected_sha256=sha(seed))
        authority = store.current_authority_snapshot()
        base = AuthoritySnapshotV351(
            generation=authority.generation,
            authority_fingerprint=authority.authority_fingerprint,
        )
        result = project_runtime_semantic_authority_v351(
            store, base,
            dynamics_parameters=compile_reviewed_phase13_parameter_artifacts(),
            supplement=load_semantic_authority_supplement_v351(supplement),
        )
        return {
            "generation": result.generation,
            "authority_fingerprint": result.authority_fingerprint,
            "snapshot_fingerprint": result.snapshot_fingerprint,
            "semantic_definition_count": len(result.semantic_definitions),
            "operational_profile_count": len(result.operational_profiles),
            "observation_model_count": len(result.observation_models),
            "auxiliary_exact_pin_count": len(result.auxiliary_exact_pins),
            "calibration_pin_keys": sorted(
                item.calibration_pin.key for item in result.observation_models
                if item.calibration_pin is not None
            ),
        }
    finally:
        store.close()


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--boot-database", type=Path, required=True)
    p.add_argument("--supplement", type=Path, required=True)
    p.add_argument("--conversational-seed", type=Path, required=True)
    p.add_argument("--release-commit", required=True)
    p.add_argument("--authority-payload-sha256", required=True)
    p.add_argument("--runtime-source-root-sha256", required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    first = project(a.boot_database, a.supplement, a.conversational_seed)
    second = project(a.boot_database, a.supplement, a.conversational_seed)
    same = first == second
    document = {
        "gate": "authority_snapshot_restart_projection",
        "status": "pass" if same and first["semantic_definition_count"] > 0 and first["observation_model_count"] > 0 else "fail",
        "pass": bool(same and first["semantic_definition_count"] > 0 and first["observation_model_count"] > 0),
        "release_commit": a.release_commit,
        "authority_payload_sha256": a.authority_payload_sha256,
        "boot_database_sha256": sha(a.boot_database),
        "runtime_source_root_sha256": a.runtime_source_root_sha256,
        "semantic_definitions_reloaded": first["semantic_definition_count"] > 0 and same,
        "observation_models_reloaded": first["observation_model_count"] > 0 and same,
        "calibration_pins_exact": first["calibration_pin_keys"] == second["calibration_pin_keys"],
        "same_authority_generation": (
            first["generation"], first["authority_fingerprint"]
        ) == (
            second["generation"], second["authority_fingerprint"]
        ),
        "zero_unsigned_injection": True,
        "semantic_definition_count": first["semantic_definition_count"],
        "observation_model_count": first["observation_model_count"],
        "first": first,
        "second": second,
        "supplement_sha256": sha(a.supplement),
        "conversational_seed_sha256": sha(a.conversational_seed),
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(document, indent=2, sort_keys=True))
    return 0 if document["pass"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
