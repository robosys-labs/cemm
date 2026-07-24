#!/usr/bin/env python3
"""Build a fail-closed Phase-18 closure ledger from gate-bound JSON evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from cemm.v350.finalization.closure_v351 import REQUIRED_PHASE18_GATES


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_binding(doc, *, gate, release_commit, authority_payload, boot_sha, source_root):
    if doc.get("gate") != gate:
        raise ValueError(f"evidence gate mismatch:{gate}")
    if doc.get("status") != "pass" or doc.get("pass") is not True:
        raise ValueError(f"gate evidence is not an explicit pass:{gate}")
    expected = {
        "release_commit": release_commit,
        "authority_payload_sha256": authority_payload,
        "boot_database_sha256": boot_sha,
        "runtime_source_root_sha256": source_root,
    }
    for key, value in expected.items():
        if doc.get(key) != value:
            raise ValueError(f"gate evidence root mismatch:{gate}:{key}")


def _special_validate(gate: str, doc):
    if gate == "shadow_equivalence":
        required = {
            "grounding", "canonical_meaning", "query_bindings", "epistemic_placement",
            "durable_deltas", "frontiers", "response_semantics", "realization",
            "latency", "storage_volume",
        }
        comparisons = set((doc.get("comparisons") or {}).keys())
        if not required.issubset(comparisons):
            raise ValueError("shadow evidence omits required comparison dimensions")
    elif gate == "authority_snapshot_restart_projection":
        required = (
            "semantic_definitions_reloaded", "observation_models_reloaded",
            "calibration_pins_exact", "same_authority_generation", "zero_unsigned_injection",
        )
        if not all(doc.get(key) is True for key in required):
            raise ValueError("authority snapshot does not prove signed restart reconstruction")
        if int(doc.get("semantic_definition_count", 0)) < 1:
            raise ValueError("restart projection evidence contains no semantic definitions")
        if int(doc.get("observation_model_count", 0)) < 1:
            raise ValueError("restart projection evidence contains no active ObservationModel authority")
        first = doc.get("first") or {}
        second = doc.get("second") or {}
        if not first.get("snapshot_fingerprint") or first.get("snapshot_fingerprint") != second.get("snapshot_fingerprint"):
            raise ValueError("restart projection semantic snapshot fingerprint is not deterministic")
    elif gate == "active_knowledge_acquisition":
        if not doc.get("novel_gap_detected") or not doc.get("evidence_acquired") or not doc.get("candidate_reused"):
            raise ValueError("active knowledge acquisition evidence is incomplete")
    elif gate == "deterministic_release_artifacts":
        if doc.get("rebuild_hash_match") is not True:
            raise ValueError("deterministic artifact gate lacks exact rebuild hash match")
    elif gate == "signed_release_authority":
        if not doc.get("signature_verified") or not doc.get("signer_identity"):
            raise ValueError("signed release gate lacks verified detached signature evidence")
    elif gate == "cross_language_equivalence":
        tags = set(doc.get("language_tags", ()))
        if "en" not in tags or "synthetic-renamed" not in tags or len(tags) < 3:
            raise ValueError("cross-language gate requires English, real typologically different language, synthetic renamed language")
        if doc.get("equivalent_canonical_csir") is not True:
            raise ValueError("cross-language gate does not prove canonical CSIR equivalence")
    elif gate == "operation_result_recurrence":
        if int(doc.get("maximum_observed_reentry_hops", 99)) > 2 or doc.get("same_authority_generation") is not True:
            raise ValueError("operation recurrence gate violates bounded same-authority re-entry")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--release-commit", required=True)
    parser.add_argument("--authority-payload-sha256", required=True)
    parser.add_argument("--boot-database-sha256", required=True)
    parser.add_argument("--runtime-source-root-sha256", required=True)
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    gates = []
    for gate in REQUIRED_PHASE18_GATES:
        path = args.evidence_dir / f"{gate}.json"
        if not path.is_file():
            gates.append({"gate": gate, "status": "not_run", "evidence_sha256": "", "evidence_path": str(path), "reason": "missing evidence"})
            continue
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            _require_binding(
                doc, gate=gate, release_commit=args.release_commit,
                authority_payload=args.authority_payload_sha256,
                boot_sha=args.boot_database_sha256, source_root=args.runtime_source_root_sha256,
            )
            _special_validate(gate, doc)
            gates.append({"gate": gate, "status": "pass", "evidence_sha256": sha256(path), "evidence_path": str(path), "reason": ""})
        except Exception as exc:
            gates.append({"gate": gate, "status": "fail", "evidence_sha256": sha256(path), "evidence_path": str(path), "reason": str(exc)})
    complete = all(item["status"] == "pass" for item in gates)
    ledger = {
        "release_commit": args.release_commit,
        "authority_payload_sha256": args.authority_payload_sha256,
        "boot_database_sha256": args.boot_database_sha256,
        "runtime_source_root_sha256": args.runtime_source_root_sha256,
        "complete": complete,
        "gates": gates,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
