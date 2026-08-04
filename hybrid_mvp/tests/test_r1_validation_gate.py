"""R1 admission-only authority, activation, and structure gates."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from cemm_authoritative_hybrid import process_control as process_control_module  # noqa: E402

sys.modules["process_control"] = process_control_module
import validation_gate as gate  # noqa: E402


def _limits() -> dict[str, int]:
    return {
        "max_output_bytes": 1_048_576,
        "max_pytest_processes_per_tier": 1,
        "max_report_bytes": 1_048_576,
        "max_slowest_rows": 10,
        "max_steps_per_tier": 8,
        "pytest_timeout_seconds": 300,
        "rss_poll_interval_ms": 25,
    }


def _r1_graph() -> dict[str, object]:
    exact = "tests/test_r1_validation_gate.py::test_r1_steps_are_admission_only"
    steps: dict[str, object] = {
        "governance": {
            "depends_on": [],
            "inputs": ["governance/test_inventory.json"],
            "invalidation_ledger": "governance/receipt_invalidations.jsonl",
            "kind": "governance",
            "metadata_symbol": "__cemm_test_inventory__",
            "status_ledger": "governance/replay_status.jsonl",
            "test_inventory": "governance/test_inventory.json",
        },
        "source_compile": {
            "depends_on": ["governance"],
            "inputs": ["src/"],
            "kind": "compile",
            "roots": ["src/"],
        },
        "owner_tests": {
            "depends_on": ["source_compile"],
            "exact_nodes": [exact],
            "inputs": ["tests/test_r1_validation_gate.py"],
            "kind": "pytest",
        },
        "phase_tests": {
            "depends_on": ["source_compile"],
            "exact_nodes": [
                "tests/test_r1_validation_gate.py::test_r1_evidence_policy_has_no_external_artifact"
            ],
            "inputs": ["tests/test_r1_validation_gate.py"],
            "kind": "pytest",
        },
        "authority_link": {
            "depends_on": ["source_compile"],
            "inputs": ["data/authority/", "src/cemm_authoritative_hybrid/authority.py"],
            "kind": "authority_link",
        },
        "sqlite_activation": {
            "depends_on": ["authority_link"],
            "inputs": ["src/cemm_authoritative_hybrid/persistence.py"],
            "kind": "sqlite_activation",
        },
        "r1_structure": {
            "depends_on": ["source_compile"],
            "inputs": ["src/cemm_authoritative_hybrid/"],
            "kind": "r1_structure",
        },
        "pytest_active": {
            "depends_on": ["source_compile"],
            "inputs": ["governance/test_inventory.json", "tests/"],
            "kind": "pytest_inventory",
            "metadata_symbol": "__cemm_test_inventory__",
            "test_inventory": "governance/test_inventory.json",
            "test_root": "tests",
        },
    }
    return {
        "limits": _limits(),
        "phases": {
            "R1": {
                "admission": ["pytest_active", "r1_structure", "sqlite_activation"],
                "owners": {"runtime-path": ["owner_tests"]},
                "phase": ["phase_tests"],
            }
        },
        "schema": "cemm-hybrid-validation-gates-v1",
        "steps": steps,
    }


def _context(tmp_path: Path) -> gate._RunContext:
    return gate._RunContext(
        ROOT,
        gate.GateGraph.from_dict(_r1_graph()),
        phase="R1",
        tier="admission",
        owner=None,
        source_ref="a" * 40,
        run_root=tmp_path,
    )


def test_r1_steps_are_admission_only() -> None:
    graph = gate.GateGraph.from_dict(_r1_graph())
    assert graph.resolve_phase("R1", "admission") == (
        "governance",
        "source_compile",
        "authority_link",
        "pytest_active",
        "r1_structure",
        "sqlite_activation",
    )

    for tier, replacement in (("owner", "authority_link"), ("phase", "r1_structure")):
        payload = _r1_graph()
        if tier == "owner":
            payload["phases"]["R1"]["owners"] = {"runtime-path": [replacement]}
        else:
            payload["phases"]["R1"]["phase"] = [replacement]
        with pytest.raises(gate.GateConfigError, match="admission-only"):
            gate.GateGraph.from_dict(payload)


def test_r1_evidence_policy_has_no_external_artifact() -> None:
    assert gate._required_admission_evidence_paths("R1") == ()


def test_authority_link_is_content_addressed_and_fail_closed(tmp_path: Path) -> None:
    context = _context(tmp_path)
    result = context.run_authority_link()
    assert result.disposition == "passed"
    assert result.report is not None
    assert result.report["schema"] == "cemm-authority-link-step-report-v1"
    assert result.report["generation"] == "authority-v1-2026-07-29"
    assert result.report["authority_ref"].startswith("linked_authority:")

    manifest = ROOT / "data" / "authority" / "manifest.json"
    original = context._read_bytes
    context._read_bytes = lambda path: b"{}" if path == manifest else original(path)
    with pytest.raises(gate.GateConfigError, match="authority link failed"):
        context.run_authority_link()


def test_sqlite_activation_uses_fresh_store_and_reopens(tmp_path: Path) -> None:
    context = _context(tmp_path)
    context.run_authority_link()
    result = context.run_sqlite_activation()
    assert result.disposition == "passed"
    assert result.report is not None
    assert result.report["schema"] == "cemm-sqlite-activation-step-report-v1"
    assert result.report["fresh_revisions"] == {
        "effect": 0,
        "episode": 0,
        "session": 0,
        "world": 0,
    }
    assert result.report["reopened"] is True
    assert result.report["activation_ref"].startswith("sqlite_activation:")


def test_r1_structure_proves_canonical_production_seam(tmp_path: Path) -> None:
    result = _context(tmp_path).run_r1_structure()
    assert result.disposition == "passed"
    assert result.report is not None
    assert result.report["program_owner"] == "src/cemm_authoritative_hybrid/programs.py"
    assert result.report["cycle_result_owner"] == "src/cemm_authoritative_hybrid/cycle.py"
    assert result.report["runtime_owner"] == "src/cemm_authoritative_hybrid/runtime.py"
    assert result.report["forbidden_match_count"] == 0


def test_r1_structure_rejects_legacy_or_duplicate_paths(tmp_path: Path) -> None:
    source = tmp_path / "src" / "cemm_authoritative_hybrid"
    source.mkdir(parents=True)
    (source / "programs.py").write_text("class SemanticSwitchProgram:\n    pass\n", encoding="utf-8")
    (source / "other.py").write_text("class SemanticSwitchProgram:\n    pass\n", encoding="utf-8")
    (source / "cycle.py").write_text("class CycleResult:\n    pass\n", encoding="utf-8")
    (source / "runtime.py").write_text(
        "class HybridRuntime:\n"
        "    def process(self, session_ref, text, *, trace=True):\n"
        "        return self.propose_and_verify(text)\n",
        encoding="utf-8",
    )
    (source / "propositions.py").write_text("legacy = True\n", encoding="utf-8")
    with pytest.raises(gate.GateConfigError, match="R1 structure validation failed"):
        gate._scan_r1_structure(tmp_path)
__cemm_test_inventory__ = {
    "tests/test_r1_validation_gate.py::test_authority_link_is_content_addressed_and_fail_closed": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-admission-authority-link",
        "diagnostic_role": "admission_only",
        "introduced_by_task": "R1-Task-9-Admission",
        "source_ast_sha256": "12bbf808cd2b35bdcb916e9d7e72a37dd8bb28584d626a23bf3ae77adc41320a",
    },
    "tests/test_r1_validation_gate.py::test_r1_evidence_policy_has_no_external_artifact": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-admission-evidence-policy",
        "diagnostic_role": "admission_only",
        "introduced_by_task": "R1-Task-9-Admission",
        "source_ast_sha256": "60a748f54ab76e6299fedb6e1e960dcdc312a7a230b1ab7cf85c3975bea11fc8",
    },
    "tests/test_r1_validation_gate.py::test_r1_steps_are_admission_only": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-admission-only-steps",
        "diagnostic_role": "admission_only",
        "introduced_by_task": "R1-Task-9-Admission",
        "source_ast_sha256": "22664f73cb4c6e688dc8ec9742778eac58d0c4a8385962b72fdf20915230bab6",
    },
    "tests/test_r1_validation_gate.py::test_r1_structure_proves_canonical_production_seam": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-admission-structure-seam",
        "diagnostic_role": "admission_only",
        "introduced_by_task": "R1-Task-9-Admission",
        "source_ast_sha256": "5b532ce39dba93f8448f2a44018ddf425cd08fc1c95491788a9a9f275928556f",
    },
    "tests/test_r1_validation_gate.py::test_r1_structure_rejects_legacy_or_duplicate_paths": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-admission-structure-rejects-duplicates",
        "diagnostic_role": "admission_only",
        "introduced_by_task": "R1-Task-9-Admission",
        "source_ast_sha256": "08684c7300c9477c8ef17eb2c40a615481e14696f3e3429dca4ab9256cf833c4",
    },
    "tests/test_r1_validation_gate.py::test_sqlite_activation_uses_fresh_store_and_reopens": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:r1-admission-sqlite-activation",
        "diagnostic_role": "admission_only",
        "introduced_by_task": "R1-Task-9-Admission",
        "source_ast_sha256": "040156eb8bf3b54a877106594d5ceace5e81c69635e1eba3d2fb58363baa20f3",
    },
}