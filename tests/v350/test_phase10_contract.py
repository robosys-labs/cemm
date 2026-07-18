from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from cemm.v350.epistemics.contract import EpistemicPackageAuditor, load_epistemic_contract

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cemm" / "data" / "v350"
BASE = "390610c0f17f83d309d8d7e83bd63ce5b68c03a7"


def _audit(root: Path):
    contract = load_epistemic_contract(root / "epistemic_contract.json")
    return EpistemicPackageAuditor(contract).audit(root)


def test_phase10_review_contract_is_clean_and_pinned() -> None:
    report = _audit(SOURCE)
    assert report.valid, report.issues
    contract = load_epistemic_contract(SOURCE / "epistemic_contract.json")
    assert contract.repository_base_commit == BASE
    assert {
        "claim_occurrence", "claim_record", "claim_history", "source_assessment",
        "epistemic_admission", "knowledge", "evidence",
    }.issubset(set(contract.required_record_kinds))
    assert contract.invariants["claim_occurrence_is_not_truth_admission"] is True
    assert contract.invariants["admission_authorization_is_first_class_durable_data"] is True
    assert contract.invariants["actual_world_retraction_requires_authorization_and_proof"] is True


def test_phase10_competence_tampering_fails_manifest_hash(tmp_path: Path) -> None:
    copied = tmp_path / "v350"
    shutil.copytree(SOURCE, copied)
    with (copied / "competence" / "epistemics.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    report = _audit(copied)
    assert not report.valid
    assert any("epistemic_competence_sha256" in item for item in report.issues)


def test_phase10_contract_tampering_fails_manifest_hash(tmp_path: Path) -> None:
    copied = tmp_path / "v350"
    shutil.copytree(SOURCE, copied)
    contract_path = copied / "epistemic_contract.json"
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    payload["metadata"]["runtime_cutover"] = True
    contract_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    report = _audit(copied)
    assert not report.valid
    assert any("epistemic_contract_sha256" in item for item in report.issues)


def test_phase10_missing_record_kind_contract_is_rejected(tmp_path: Path) -> None:
    copied = tmp_path / "v350"
    shutil.copytree(SOURCE, copied)
    contract_path = copied / "epistemic_contract.json"
    payload = json.loads(contract_path.read_text(encoding="utf-8"))
    payload["required_record_kinds"].append("nonexistent_epistemic_authority")
    contract_path.write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    # Pin the tampered contract so the semantic contract check, not only the hash,
    # proves that an unavailable authority cannot be declared complete.
    import hashlib
    manifest_path = copied / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["metadata"]["epistemic_contract_sha256"] = hashlib.sha256(
        contract_path.read_bytes()
    ).hexdigest()
    manifest_path.write_text(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    report = _audit(copied)
    assert not report.valid
    assert any("record_kinds:missing" in item for item in report.issues)


def test_phase10_verifier_executes_all_declarative_cases(tmp_path: Path) -> None:
    report_path = tmp_path / "phase10.json"
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "verify_v350_epistemics.py"),
            "--source",
            str(SOURCE),
            "--report",
            str(report_path),
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["valid"] is True
    assert report["competence"]["passed"] == 17
    assert report["compilation"]["byte_deterministic"] is True
