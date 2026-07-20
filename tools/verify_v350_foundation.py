#!/usr/bin/env python3
"""Compile, audit, and competence-test the reviewed CEMM v3.5 foundation."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cemm.v350.data import DeterministicSQLiteCompiler
from cemm.v350.foundation import (
    FoundationCompetenceRunner,
    FoundationPackageAuditor,
    load_foundation_competence,
    load_foundation_contract,
)
from cemm.v350.storage import SemanticStore


def _phase_scoped_source(source: Path, target: Path, *, max_phase: int) -> Path:
    manifest_data = json.loads((source / "manifest.json").read_text(encoding="utf-8"))
    manifest_data["modules"] = [
        item for item in manifest_data["modules"]
        if int(item.get("phase", 6)) <= max_phase
    ]
    target.mkdir(parents=True, exist_ok=True)
    (target / "manifest.json").write_text(
        json.dumps(manifest_data, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    for relative in ("foundation_contract.json", "competence/foundation.jsonl"):
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)
    for module in manifest_data["modules"]:
        relative = Path(module["path"])
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, destination)
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=Path("cemm/data/v350"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-determinism", action="store_true")
    args = parser.parse_args(argv)

    source = args.source.resolve()
    contract = load_foundation_contract(source / "foundation_contract.json")
    audit = FoundationPackageAuditor(contract).audit(source)

    with tempfile.TemporaryDirectory(prefix="cemm-v350-foundation-") as directory:
        temporary = Path(directory)
        scoped_source = _phase_scoped_source(source, temporary / "source", max_phase=6)
        first_path = temporary / "foundation-a.sqlite"
        second_path = temporary / "foundation-b.sqlite"
        first = DeterministicSQLiteCompiler().compile(scoped_source, first_path, make_read_only=False)
        deterministic = True
        second = None
        if not args.skip_determinism:
            second = DeterministicSQLiteCompiler().compile(scoped_source, second_path, make_read_only=False)
            deterministic = (
                first.boot_fingerprint == second.boot_fingerprint
                and first.record_set_fingerprint == second.record_set_fingerprint
                and first_path.read_bytes() == second_path.read_bytes()
            )

        store = SemanticStore(":memory:", boot_path=first_path)
        try:
            cases = load_foundation_competence(source / "competence" / "foundation.jsonl")
            competence = FoundationCompetenceRunner(store).run(cases)
        finally:
            store.close()

        output_result = None
        if args.output is not None:
            output_result = DeterministicSQLiteCompiler().compile(
                scoped_source, args.output, make_read_only=True
            )

    required_cases = set(contract.required_competence_case_refs)
    executed_cases = {item.case_ref for item in competence.results}
    missing_cases = sorted(required_cases - executed_cases)
    ok = audit.valid and competence.passed and deterministic and not missing_cases
    contract_path = source / "foundation_contract.json"
    competence_path = source / "competence" / "foundation.jsonl"
    payload = {
        "ok": ok,
        "source": str(source),
        "contract": {
            "contract_ref": contract.contract_ref,
            "expected_record_counts": dict(contract.expected_record_counts),
            "expected_source_record_fingerprint": contract.expected_source_record_fingerprint,
            "contract_sha256": hashlib.sha256(contract_path.read_bytes()).hexdigest(),
            "competence_sha256": hashlib.sha256(competence_path.read_bytes()).hexdigest(),
            "required_competence_case_count": len(contract.required_competence_case_refs),
        },
        "audit": {
            "valid": audit.valid,
            "record_count": audit.record_count,
            "counts_by_kind": dict(audit.counts_by_kind),
            "manifest_fingerprint": audit.manifest_fingerprint,
            "source_record_fingerprint": audit.source_record_fingerprint,
            "issues": [asdict(item) for item in audit.issues],
        },
        "compilation": {
            "record_count": first.record_count,
            "boot_fingerprint": first.boot_fingerprint,
            "record_set_fingerprint": first.record_set_fingerprint,
            "byte_size": first.byte_size,
            "deterministic": deterministic,
        },
        "competence": {
            "passed": competence.passed,
            "missing_required_cases": missing_cases,
            "results": [asdict(item) for item in competence.results],
        },
        "output": None if output_result is None else {
            "path": str(output_result.output_path),
            "boot_fingerprint": output_result.boot_fingerprint,
            "byte_size": output_result.byte_size,
        },
    }
    print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
