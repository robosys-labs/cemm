#!/usr/bin/env python3
"""Phase-13 architecture/contract verifier.

This verifier is intentionally structural. Runtime behavioral proof remains in
pytest/competence cases; this tool catches forbidden authority drift and missing
learning lifecycle wiring before those tests run.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
LEARNING = ROOT / "cemm/v350/learning"
CONTRACT = ROOT / "cemm/data/v350/learning_contract.json"
CASES = ROOT / "cemm/data/v350/competence/learning_promotion.jsonl"
MANIFEST = ROOT / "cemm/data/v350/manifest.json"

REQUIRED_RECORD_VALUES = {
    "learning_package", "learning_frontier", "learning_evidence_link",
    "competence_result", "promotion_decision", "learning_invalidation",
}
REQUIRED_COMPONENTS = {
    "FrontierCollector", "EvidenceAggregator", "CandidateStructureInducer",
    "PackageAssembler", "LearningDependencyResolver", "LearningCompetenceRunner",
    "PromotionPolicyEngine", "PromotionCoordinator", "LearningInvalidationManager",
    "LearningRetractionCoordinator", "LearningRehydrationCoordinator",
    "LearningPackageCommitCoordinator", "LearningCoordinator",
}
FORBIDDEN_CALL_NAMES = {
    "startswith", "endswith",  # concept/word name routing must not enter promotion authority
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def defined_symbols(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name for node in ast.walk(tree)
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }


def verify() -> list[str]:
    errors: list[str] = []
    if not CONTRACT.is_file() or not CASES.is_file() or not MANIFEST.is_file():
        return ["missing Phase-13 contract/cases/manifest"]
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    metadata = manifest.get("metadata", {})
    if int(metadata.get("phase", 0)) < 13:
        errors.append("manifest phase is below 13")
    if metadata.get("learning_runtime_cutover") is not False:
        errors.append("Phase 13 must remain shadow/non-public until all exit gates pass")
    if metadata.get("learning_contract_sha256") != sha(CONTRACT):
        errors.append("learning contract hash is not pinned in manifest")
    if metadata.get("learning_competence_sha256") != sha(CASES):
        errors.append("learning competence hash is not pinned in manifest")
    if not REQUIRED_RECORD_VALUES.issubset(set(contract.get("required_record_kinds", ()))):
        errors.append("learning contract omits required durable record family")
    if not REQUIRED_COMPONENTS.issubset(set(contract.get("required_components", ()))):
        errors.append("learning contract omits required runtime component")
    source_symbols: set[str] = set()
    for path in LEARNING.glob("*.py"):
        source_symbols.update(defined_symbols(path))
    missing = REQUIRED_COMPONENTS.difference(source_symbols)
    if missing:
        errors.append("missing Phase-13 components: " + ", ".join(sorted(missing)))
    record_model = (ROOT / "cemm/v350/storage/model.py").read_text(encoding="utf-8")
    for value in sorted(REQUIRED_RECORD_VALUES):
        if f'"{value}"' not in record_model:
            errors.append(f"RecordKind missing {value}")
    schema_registry = (ROOT / "cemm/v350/schema/registry.py").read_text(encoding="utf-8")
    if "schema_authorizes_use" not in schema_registry:
        errors.append("schema registry still lacks lifecycle-aware use authority")
    transition_compiler = (ROOT / "cemm/v350/transitions/compiler.py").read_text(encoding="utf-8")
    if "runtime transition compilation requires an active contract revision" not in transition_compiler:
        errors.append("transition compiler is not active-only for executable runtime use")
    transition_state = (ROOT / "cemm/v350/transitions/state.py").read_text(encoding="utf-8")
    if "delta.from_value_ref, delta.from_value_revision" not in transition_state:
        errors.append("ordered scalar transition direction is not pinned to explicit from_value")
    transition_commit = (ROOT / "cemm/v350/transitions/commit.py").read_text(encoding="utf-8")
    if "dependency_by_ref" not in transition_commit or "conflicting exact transition dependency pins" not in transition_commit:
        errors.append("transition state-delta dependency assembly is not duplicate/conflict safe")
    validation = (ROOT / "cemm/v350/learning/validation.py").read_text(encoding="utf-8")
    if "PromotionDecision dependency" not in validation:
        errors.append("direct GraphPatch learned-authority bypass guard missing")
    case_refs = set()
    for line in CASES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        case_refs.add(json.loads(line)["case_ref"])
    required_cases = set(contract.get("required_competence_case_refs", ()))
    if not required_cases.issubset(case_refs):
        errors.append("competence dataset omits contract-required cases")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    errors = verify()
    payload = {"phase": 13, "ok": not errors, "errors": errors}
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        print("Phase 13 verification:", "PASS" if not errors else "FAIL")
        for error in errors:
            print(" -", error)
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
