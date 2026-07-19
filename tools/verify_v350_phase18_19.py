#!/usr/bin/env python3
"""Fail-closed structural verifier for CEMM v3.5 Phases 18/19.

This verifier complements, but does not replace, the full predecessor/unit/
integration/performance suite required by the implementation plan.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import sys


def fail(message: str) -> None:
    raise SystemExit(f"PHASE18_19_VERIFY_FAIL: {message}")


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))

    from cemm.v350.storage.model import RecordKind
    from cemm.v350.storage.sqlite_schema import SCHEMA_VERSION, initialize_schema
    from cemm.v350.operations.model import OperationReconciliationRecord
    from cemm.v350.realization.model import SemanticAnalyzerContractRecord, SemanticRoundTripRecord
    from cemm.v350.output.gate import EmissionGate
    from cemm.v350.output.model import ChannelAdapterContractRecord, EmissionAnomalyRecord
    from cemm.v350.migration.model import MigrationTargetMapRecord

    required_kinds = {
        "semantic_analyzer_contract", "channel_adapter_contract", "literal_emission_policy",
        "emission_gate_assessment", "emission_authorization", "emission_journal", "emission",
        "emission_anomaly", "silence_outcome", "output_discourse_act", "output_commitment",
        "common_ground", "output_reference_anchor", "output_correction", "migration_source",
        "migration_rule", "migration_target_map", "migration_decision", "migration_batch",
        "migration_quarantine", "migration_intentional_change", "semantic_equivalence",
        "migration_rollback",
    }
    actual = {item.value for item in RecordKind}
    require(required_kinds <= actual, f"missing RecordKinds: {sorted(required_kinds - actual)}")
    require(SCHEMA_VERSION == 8, f"expected SQLite schema 8, found {SCHEMA_VERSION}")

    con = sqlite3.connect(":memory:")
    initialize_schema(con)
    names = {str(row[0]) for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    require({"phase18_records", "migration_records", "migration_record_sources"} <= names, "Phase18/19 normalized SQLite tables missing")

    op_fields = set(OperationReconciliationRecord.__dataclass_fields__)
    require("observed_journal_pin" in op_fields, "Phase16 reconciliation lacks exact observed journal pin")
    rt_fields = set(SemanticRoundTripRecord.__dataclass_fields__)
    require("analyzer_contract_pin" in rt_fields, "Phase17 round-trip lacks analyzer contract pin")
    require("competence_case_refs" in SemanticAnalyzerContractRecord.__dataclass_fields__, "analyzer contract lacks competence lineage")
    require("source_pins" in MigrationTargetMapRecord.__dataclass_fields__, "migration target map cannot represent merge source sets")
    require("policy_safety" in EmissionGate.REQUIRED_GATES and "qualification_preserved" in EmissionGate.REQUIRED_GATES, "emission hard-gate set incomplete")
    require(EmissionAnomalyRecord.__dataclass_fields__["no_output_discourse_authority"].default is True, "emission anomalies are not fail-closed non-discourse records")
    require("delivery_ack_proves_recipient_receipt" in ChannelAdapterContractRecord.__dataclass_fields__, "channel receipt semantics lack structural contract field")
    require("supports_recovery_query" in ChannelAdapterContractRecord.__dataclass_fields__, "channel recovery capability is not structurally reviewed")

    data = root / "cemm" / "data" / "v350"
    contracts = {
        18: data / "phase18_output_contract.json",
        19: data / "phase19_migration_contract.json",
    }
    competence = {
        18: data / "competence" / "output_discourse.jsonl",
        19: data / "competence" / "migration_equivalence.jsonl",
    }
    seen: set[str] = set()
    for phase, path in contracts.items():
        doc = json.loads(path.read_text(encoding="utf-8"))
        require(doc.get("phase") == phase, f"contract phase mismatch: {path}")
        require(doc.get("contract_ref"), f"contract_ref missing: {path}")
        require(doc.get("laws"), f"contract laws missing: {path}")
    for phase, path in competence.items():
        count = 0
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            ref = row.get("case_ref")
            require(ref and ref not in seen, f"missing/duplicate competence case_ref: {ref}")
            seen.add(ref)
            require(row.get("assertion"), f"competence assertion missing: {ref}")
            count += 1
        require(count >= 15, f"phase {phase} competence coverage unexpectedly small: {count}")

    manifest_path = data / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    meta = manifest.get("metadata", {})
    require(int(meta.get("phase", 0)) >= 19, "manifest does not declare Phase19 verification lineage")
    for phase in (18, 19):
        require(meta.get(f"phase{phase}_contract_sha256") == sha256(contracts[phase]), f"phase{phase} contract hash mismatch")
        require(meta.get(f"phase{phase}_competence_sha256") == sha256(competence[phase]), f"phase{phase} competence hash mismatch")

    core = (root / "CORE_LOOP.md").read_text(encoding="utf-8")
    require("17 RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS" in core, "core-loop macro retains duplicate response-goal authority")
    require("17 GENERATE_RESPONSE_GOALS" not in core, "legacy Stage17 goal-generation label still present")
    require("Semantic round-trip PASS is necessary but does **not** authorize emission" in core, "Stage20 emission authority law missing")

    impl = (root / "IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")
    require("docs/implementation/v350-phase-20-plan.md" in impl, "Phase20 comprehensive plan link missing")

    scan_paths = [
        root / "cemm" / "v350" / "output",
        root / "cemm" / "v350" / "migration",
        root / "cemm" / "v350" / "operations",
        root / "cemm" / "v350" / "realization",
    ]
    for directory in scan_paths:
        for path in directory.glob("*.py"):
            text = path.read_text(encoding="utf-8")
            require("NotImplementedError" not in text, f"unfinished runtime stub in {path}")
            require("TODO: semantic" not in text, f"semantic TODO in {path}")

    authority = (root / "cemm" / "v350" / "realization" / "authority.py").read_text(encoding="utf-8")
    require('stored.layer == "boot"' in authority or "stored.layer == 'boot'" in authority, "overlay language ACTIVE records can self-authorize realization")
    migration_coordinator = (root / "cemm" / "v350" / "migration" / "coordinator.py").read_text(encoding="utf-8")
    require("logical batch" in migration_coordinator.lower() and "existing_batch" in migration_coordinator, "migration logical-batch idempotence guard missing")
    require("lineage_sources=map_record.source_pins" in migration_coordinator.replace(" ", ""), "merged target writes do not depend on every exact map source")
    output_coordinator = (root / "cemm" / "v350" / "output" / "coordinator.py").read_text(encoding="utf-8")
    require("output_addressee" in output_coordinator and "delivery_ack_proves_recipient_receipt" in output_coordinator, "output audience/receipt hardening missing")
    output_reference = (root / "cemm" / "v350" / "output" / "reference.py").read_text(encoding="utf-8")
    require("candidate_refs=tuple(refs)" in output_reference.replace(" ", ""), "output-reference frontier still misuses evidence refs")
    language_authority = (root / "cemm" / "v350" / "realization" / "authority.py").read_text(encoding="utf-8")
    require("len(effective)!=1" in language_authority.replace(" ", "") and "prerequisite_fingerprint" in language_authority, "REALIZE singular-effective/exact-promotion hardening missing")

    print(f"PHASE18_19_VERIFY_OK cases={len(seen)} schema_version={SCHEMA_VERSION}")


if __name__ == "__main__":
    main()
