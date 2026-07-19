#!/usr/bin/env python3
"""Audit and execute the CEMM v3.5 Phase-12 cross-domain vertical slices."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import tempfile

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from cemm.v350.data import DeterministicSQLiteCompiler
from cemm.v350.verification import (
    TransitionSliceHarness, TransitionSliceResult, VerticalSlicePackageAuditor,
    load_vertical_slice_contract,
)

ROOT = REPOSITORY_ROOT
SOURCE = ROOT / "cemm" / "data" / "v350"
RUNTIME = ROOT / "cemm" / "v350"


def _cases(path: Path):
    return tuple(
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    contract = load_vertical_slice_contract(args.source / "vertical_slice_contract.json")
    audit = VerticalSlicePackageAuditor(contract).audit(args.source, runtime_root=RUNTIME)
    if not audit.valid:
        raise SystemExit("Phase 12 source audit failed:\n" + "\n".join(audit.issues))

    compiler = DeterministicSQLiteCompiler()
    with tempfile.TemporaryDirectory(prefix="cemm-v350-phase12-") as directory:
        directory = Path(directory)
        first = compiler.compile(args.source, directory / "a.sqlite", make_read_only=False)
        second = compiler.compile(args.source, directory / "b.sqlite", make_read_only=False)
        if first.output_path.read_bytes() != second.output_path.read_bytes():
            raise SystemExit("Phase 12 deterministic compilation failed")
        harness = TransitionSliceHarness(first.output_path)
        results = []
        full_path_packages = set()
        for case in _cases(args.source / "competence" / "transition_vertical_slices.jsonl"):
            result = harness.run(case)
            if isinstance(result, TransitionSliceResult):
                if case["operation"] in {"full_slice", "context_isolation"}:
                    full_path_packages.add(result.package_ref)
                if result.committed:
                    if not result.restart_verified:
                        raise AssertionError(f"{case['case_ref']}: restart verification missing")
                    if result.proof_event_revision is None or result.proof_application_revision is None:
                        raise AssertionError(f"{case['case_ref']}: exact event/application proof pins missing")
                results.append(asdict(result))
            else:
                if case["operation"] == "rename_equivalence" and not result.get("equivalent"):
                    raise AssertionError("mechanical semantic renaming changed structural transition behavior")
                if case["operation"] == "polysemy_type_selection" and int(result.get("sense_candidate_count", 0)) < 2:
                    raise AssertionError("polysemy proof did not preserve competing lexical senses before selection")
                results.append(dict(result))
        if len(full_path_packages) < contract.minimum_full_path_packages:
            raise AssertionError("insufficient independent full-path Phase-12 packages")

    timing_samples = []
    for item in results:
        timings = item.get("timings_ms")
        if isinstance(timings, dict):
            timing_samples.append({"case_ref": item["case_ref"], **timings})
    report = {
        "valid": True,
        "contract_ref": contract.contract_ref,
        "repository_base_commit": contract.repository_base_commit,
        "audit": asdict(audit),
        "compilation": {
            "record_count": first.record_count,
            "manifest_fingerprint": first.manifest_fingerprint,
            "record_set_fingerprint": first.record_set_fingerprint,
            "boot_fingerprint": first.boot_fingerprint,
            "byte_deterministic": True,
            "byte_size": first.byte_size,
        },
        "competence": {
            "passed": len(results),
            "full_path_packages": len(full_path_packages),
            "cases": results,
        },
        "performance_evidence_ms": timing_samples,
        "authority": {
            "canonical_phase12_domain_seed_records": 0,
            "synthetic_packages_are_overlay_only": True,
            "runtime_cutover": False,
        },
    }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.report:
        args.report.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
