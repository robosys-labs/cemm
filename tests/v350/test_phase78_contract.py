from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from cemm.v350.language.contract import (
    LanguageGroundingPackageAuditor,
    load_language_grounding_contract,
)

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "cemm" / "data" / "v350"


def _audit(root: Path):
    contract = load_language_grounding_contract(root / "language_grounding_contract.json")
    return LanguageGroundingPackageAuditor(contract).audit(root)


def test_phase7_8_review_contract_is_clean_and_pinned_to_latest_base() -> None:
    report = _audit(SOURCE)
    assert report.valid, report.issues
    assert report.counts_by_kind == {
        "construction": 21,
        "evidence": 1,
        "form_sense_link": 85,
        "language_form": 75,
        "language_pack": 3,
        "lexical_sense": 51,
    }
    contract = load_language_grounding_contract(SOURCE / "language_grounding_contract.json")
    assert contract.base_commit == "e362bf82da4ee4f6704be2ed522cd7bf9418d6bf"
    assert report.source_record_fingerprint == contract.expected_source_record_fingerprint


def test_unreviewed_language_record_fails_count_and_source_fingerprint(tmp_path: Path) -> None:
    copied = tmp_path / "v350"
    shutil.copytree(SOURCE, copied)
    forms = copied / "languages" / "forms.jsonl"
    record = json.loads(forms.read_text(encoding="utf-8").splitlines()[0])
    record["form_ref"] = "form:test:unreviewed"
    record["written_form"] = "unreviewed"
    record["normalized_form"] = "unreviewed"
    with forms.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
    report = _audit(copied)
    assert not report.valid
    assert any(item.startswith("record_count:language_form:") for item in report.issues)
    assert any(item.startswith("source_fingerprint:") for item in report.issues)


def test_competence_tampering_fails_manifest_hash(tmp_path: Path) -> None:
    copied = tmp_path / "v350"
    shutil.copytree(SOURCE, copied)
    with (copied / "competence" / "grounding.jsonl").open("a", encoding="utf-8") as handle:
        handle.write("\n")
    report = _audit(copied)
    assert not report.valid
    assert any("grounding_competence_sha256" in item for item in report.issues)


def test_phase7_8_verifier_executes_all_declarative_cases(tmp_path: Path) -> None:
    report_path = tmp_path / "phase78.json"
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(ROOT)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "verify_v350_language_grounding.py"),
            "--source",
            str(SOURCE),
            "--report",
            str(report_path),
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["valid"] is True
    assert report["base_commit"] == "e362bf82da4ee4f6704be2ed522cd7bf9418d6bf"
    assert report["competence"]["passed"] == 24
    assert report["compilation"]["byte_deterministic"] is True
