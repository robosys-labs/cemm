from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "diagnose_r4_cases.py"
SPEC = importlib.util.spec_from_file_location("cemm_r4_case_diagnostics", SCRIPT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load R4 case diagnostic owner")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
canonical_report_bytes = MODULE.canonical_report_bytes
diagnose_cases = MODULE.diagnose_cases


def test_report_groups_by_earliest_comparison_owner(tmp_path: Path) -> None:
    report = diagnose_cases(ROOT, store_root=tmp_path / "stores")

    assert report["schema"] == "cemm-r4-case-diagnostic-v1"
    assert report["case_count"] == 400
    assert (
        report["counts"]["passed"]
        + report["counts"]["failed"]
        + report["counts"]["errors"]
        == 400
    )
    assert set(report["mismatch_counts"]) <= {
        "expression",
        "situation",
        "decision",
        "effect",
        "response",
        "gap",
        "environment",
    }
    assert sum(report["earliest_owner_counts"].values()) == (
        report["counts"]["failed"] + report["counts"]["errors"]
    )
    assert all(len(rows) <= 8 for rows in report["examples"].values())


def test_report_is_byte_deterministic(tmp_path: Path) -> None:
    first = canonical_report_bytes(
        diagnose_cases(ROOT, store_root=tmp_path / "a")
    )
    second = canonical_report_bytes(
        diagnose_cases(ROOT, store_root=tmp_path / "b")
    )

    assert first == second


def test_environment_diagnostic_requires_explicit_source_revision(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--environment",
            "cemm_authoritative_hybrid.r4_environment:build_environment",
            "--store-root",
            str(tmp_path / "stores"),
            "--output",
            str(tmp_path / "report.json"),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode != 0
    assert "--source-revision is required with --environment" in completed.stderr


__cemm_test_inventory__ = {'tests/test_r4_case_diagnostics.py::test_report_groups_by_earliest_comparison_owner': {'activation_phase': 'R4',
                                                                                        'assertion_ref': 'assertion:r4-case-diagnostic-groups-earliest-owner',
                                                                                        'diagnostic_role': 'owner',
                                                                                        'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                                        'owner_ref': 'expected-contract',
                                                                                        'source_ast_sha256': '77389aff3e73624b0d9be8a61f5fd52c368d0fdafc6ec1cdb2b4bf155594ca26'},
 'tests/test_r4_case_diagnostics.py::test_report_is_byte_deterministic': {'activation_phase': 'R4',
                                                                          'assertion_ref': 'assertion:r4-case-diagnostic-is-byte-deterministic',
                                                                          'diagnostic_role': 'owner',
                                                                          'introduced_by_task': 'R4-Final-Admission-Closeout',
                                                                          'owner_ref': 'expected-contract',
                                                                          'source_ast_sha256': 'a82b4be5e8d1f6cfea5fae59985f43fc34bcbac7ce82708f9c0cf2479934f22b'},
 'tests/test_r4_case_diagnostics.py::test_environment_diagnostic_requires_explicit_source_revision': {'activation_phase': 'R4',
                                                                                                      'assertion_ref': 'assertion:r4-diagnostic-requires-source-revision',
                                                                                                      'diagnostic_role': 'owner',
                                                                                                      'introduced_by_task': 'R4-Repository-Owned-Admission',
                                                                                                      'owner_ref': 'expected-contract',
                                                                                                      'source_ast_sha256': 'd38c6552be5c0b80ac4e6ebde0717631e88b330119b0d62dfd3061c27e941270'}}
