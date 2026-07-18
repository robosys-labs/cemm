from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from cemm.v350.composition.contract import CompositionPackageAuditor, load_composition_contract

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cemm" / "data" / "v350"
BASE = "e362bf82da4ee4f6704be2ed522cd7bf9418d6bf"

def _audit(root: Path):
    contract = load_composition_contract(root / "composition_contract.json")
    return CompositionPackageAuditor(contract).audit(root)

def test_phase9_review_contract_is_clean_and_pinned() -> None:
    report = _audit(SOURCE)
    assert report.valid, report.issues
    contract = load_composition_contract(SOURCE / "composition_contract.json")
    assert contract.repository_base_commit == BASE
    assert {"type_entitlement", "context_isolation"}.issubset(set(contract.required_hard_factor_kinds))
    assert contract.invariants["solver_has_no_named_semantic_authority"] is True

def test_phase9_competence_tampering_fails_manifest_hash(tmp_path: Path) -> None:
    copied = tmp_path / "v350"
    shutil.copytree(SOURCE, copied)
    with (copied / "competence" / "meaning_composition.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    report = _audit(copied)
    assert not report.valid
    assert any("meaning_composition_competence_sha256" in item for item in report.issues)

def test_phase9_contract_tampering_fails_manifest_hash(tmp_path: Path) -> None:
    copied = tmp_path / "v350"
    shutil.copytree(SOURCE, copied)
    contract_path = copied / "composition_contract.json"
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    payload["metadata"]["runtime_cutover"] = True
    contract_path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
    report = _audit(copied)
    assert not report.valid
    assert any("composition_contract_sha256" in item for item in report.issues)

def test_phase9_verifier_executes_all_declarative_cases(tmp_path: Path) -> None:
    report_path = tmp_path / "phase9.json"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run([sys.executable, str(ROOT / "tools" / "verify_v350_composition.py"), "--source", str(SOURCE), "--report", str(report_path)], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["valid"] is True
    assert report["competence"]["passed"] == 12
    assert report["compilation"]["byte_deterministic"] is True
