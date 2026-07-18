from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from cemm.v350.transitions.contract import TransitionPackageAuditor, load_transition_contract

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cemm" / "data" / "v350"
BASE = "60b2fe7026fe1e6204b1dc682977de93c13e515e"


def _audit(root: Path):
    contract = load_transition_contract(root / "transition_contract.json")
    return TransitionPackageAuditor(contract).audit(root, runtime_root=ROOT / "cemm" / "v350")


def test_phase11_review_contract_is_clean_pinned_and_domain_empty() -> None:
    report = _audit(SOURCE)
    assert report.valid, report.issues
    contract = load_transition_contract(SOURCE / "transition_contract.json")
    assert contract.repository_base_commit == BASE
    assert contract.invariants["event_specific_mutation_branches_forbidden"] is True
    assert contract.invariants["proof_pins_exact_admission_revisions"] is True
    assert contract.invariants["proof_pins_exact_pre_state_revisions"] is True
    assert contract.invariants["foundation_contains_no_domain_transition_contracts"] is True


def test_phase11_competence_tampering_fails_manifest_hash(tmp_path: Path) -> None:
    copied = tmp_path / "v350"
    shutil.copytree(SOURCE, copied)
    with (copied / "competence" / "transitions.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    report = _audit(copied)
    assert not report.valid
    assert any("transition_competence_sha256" in item for item in report.issues)


def test_phase11_unreviewed_transition_seed_is_rejected_even_if_file_is_manifested(tmp_path: Path) -> None:
    copied = tmp_path / "v350"
    shutil.copytree(SOURCE, copied)
    path = copied / "dynamics" / "transition_contracts.jsonl"
    path.write_text('{"contract_ref":"transition-contract:unreviewed"}\n', encoding="utf-8")
    report = _audit(copied)
    assert not report.valid
    assert any("domain_transition_seed" in item for item in report.issues) or any("source" in item for item in report.issues)


def test_phase11_contract_tampering_fails_manifest_hash(tmp_path: Path) -> None:
    copied = tmp_path / "v350"
    shutil.copytree(SOURCE, copied)
    path = copied / "transition_contract.json"
    payload = json.loads(path.read_text())
    payload["invariants"]["event_specific_mutation_branches_forbidden"] = False
    path.write_text(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
    report = _audit(copied)
    assert not report.valid
    assert any("transition_contract_sha256" in item or "invariant_disabled" in item for item in report.issues)


def test_phase11_verifier_executes_all_declarative_cases(tmp_path: Path) -> None:
    report_path = tmp_path / "phase11.json"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "verify_v350_transitions.py"), "--source", str(SOURCE), "--report", str(report_path)],
        cwd=ROOT, env=env, capture_output=True, text=True, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(report_path.read_text())
    assert report["valid"] is True
    assert report["competence"]["passed"] == 12
    assert report["compilation"]["byte_deterministic"] is True
