"""R2 validation gate tests.

Per R2 plan Task 10:
- R2 validation DAG exists and is bounded
- R2 phase has 5 owner groups: form-context, recursive-composer,
  expression-compiler, exact-verifier, runtime-boundary
- R2 phase tests cover cross-owner integration
- R2 admission graph: governance -> source_compile -> authority_link ->
  pytest_active -> r2_structure -> sqlite_activation
- Owner nodes are disjoint (no overlap)
- Phase nodes are disjoint from owner nodes
- r2_structure step kind is admitted
- R2 structure scan verifies recursive composer and compiler ownership
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

__cemm_test_inventory__ = {
    "tests/test_r2_validation_gate.py::test_r2_admission_graph_is_bounded": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-r2-admission-graph-is-bounded",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "4b43b5f6ecb28eb6d7a00d325c8815e1eed7fc93a072069d73cd6ea9c65c39d8"
    },
    "tests/test_r2_validation_gate.py::test_r2_has_five_owner_groups": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-r2-has-five-owner-groups",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "c6d1e226dda136e739a873c9aebcef7a52b197c8b072e81e2ae599ca42c37bc5"
    },
    "tests/test_r2_validation_gate.py::test_r2_owner_nodes_are_disjoint": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-r2-owner-nodes-are-disjoint",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "d8ddff9c0dbb0d1583a54863bdd4222b297ff040c015f72a37fb73f202b2fad8"
    },
    "tests/test_r2_validation_gate.py::test_r2_owner_steps_depend_on_source_compile": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-r2-owner-steps-depend-on-source-compile",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "0bdfe628eecabd06fd9aa253fcd4bc50af49e028b4d47105064274973537886e"
    },
    "tests/test_r2_validation_gate.py::test_r2_phase_exists": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-r2-phase-exists",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "eab877f2ccfb949d9fe5ac0f812ac7835a45ec3f210f32d182eee9aa0179d773"
    },
    "tests/test_r2_validation_gate.py::test_r2_phase_nodes_disjoint_from_owners": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-r2-phase-nodes-disjoint-from-owners",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "ca213819fbe58a9d13e7eb6f518b2ae9c92c97315c8fd0f82eef446f127c43c4"
    },
    "tests/test_r2_validation_gate.py::test_r2_phase_step_depends_on_source_compile": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-r2-phase-step-depends-on-source-compile",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "4be24a129f52c50930c80a02d25753d5fbe9deb61ddf62088fb1db9521dd8341"
    },
    "tests/test_r2_validation_gate.py::test_r2_step_count_within_bounds": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-r2-step-count-within-bounds",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "91862e5ebbd356ce2ff3a3268ae1c0ca053910db8dbe0eb81b7b27bef5ce5a1f"
    },
    "tests/test_r2_validation_gate.py::test_r2_structure_scan_finds_owners": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-r2-structure-scan-finds-owners",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "d3944c136f6c9f0067c085e3720b001818d4b7b0474415d02b20796c22f86a5b"
    },
    "tests/test_r2_validation_gate.py::test_r2_structure_step_exists": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-r2-structure-step-exists",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "6851d606cf77148e1d79c8fca8b82c2bb269743eba8c85c0861393bcc25661fe"
    },
    "tests/test_r2_validation_gate.py::test_r2_structure_step_kind_is_admitted": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:r2-r2-structure-step-kind-is-admitted",
        "diagnostic_role": "phase",
        "introduced_by_task": "R2-Implementation",
        "source_ast_sha256": "6ab89e3d6976318bf61a02db0f36215d0a1ba897253b629948bab19d3f871c5c"
    },
}


ROOT = Path(__file__).parents[1]
CONFIG_PATH = ROOT / "configs" / "validation_gates.json"


@pytest.fixture
def gate_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def test_r2_phase_exists(gate_config):
    """R2 phase exists in the validation gates config."""
    assert "R2" in gate_config["phases"]
    r2 = gate_config["phases"]["R2"]
    assert "owners" in r2
    assert "phase" in r2
    assert "admission" in r2


def test_r2_has_five_owner_groups(gate_config):
    """R2 phase has exactly 5 owner groups."""
    owners = gate_config["phases"]["R2"]["owners"]
    expected = {"form-context", "recursive-composer", "expression-compiler", "exact-verifier", "runtime-boundary"}
    assert set(owners.keys()) == expected


def test_r2_owner_nodes_are_disjoint(gate_config):
    """R2 owner test nodes are disjoint (no overlap)."""
    owners = gate_config["phases"]["R2"]["owners"]
    all_nodes: list[str] = []
    for owner, step_ids in owners.items():
        for step_id in step_ids:
            step = gate_config["steps"][step_id]
            all_nodes.extend(step["exact_nodes"])
    assert len(all_nodes) == len(set(all_nodes)), "R2 owner nodes overlap"


def test_r2_phase_nodes_disjoint_from_owners(gate_config):
    """R2 phase test nodes are disjoint from owner nodes."""
    r2 = gate_config["phases"]["R2"]
    owner_nodes: set[str] = set()
    for step_ids in r2["owners"].values():
        for step_id in step_ids:
            owner_nodes.update(gate_config["steps"][step_id]["exact_nodes"])
    phase_nodes: set[str] = set()
    for step_id in r2["phase"]:
        phase_nodes.update(gate_config["steps"][step_id]["exact_nodes"])
    assert not owner_nodes & phase_nodes, "R2 phase nodes overlap with owner nodes"


def test_r2_admission_graph_is_bounded(gate_config):
    """R2 admission graph has the required structure."""
    r2 = gate_config["phases"]["R2"]
    admission = r2["admission"]
    assert "pytest_active" in admission
    assert "r2_structure" in admission
    assert "sqlite_activation" in admission


def test_r2_structure_step_exists(gate_config):
    """r2_structure step exists in the config."""
    assert "r2_structure" in gate_config["steps"]
    step = gate_config["steps"]["r2_structure"]
    assert step["kind"] == "r2_structure"
    assert "source_compile" in step["depends_on"]


def test_r2_owner_steps_depend_on_source_compile(gate_config):
    """All R2 owner steps depend on source_compile."""
    owners = gate_config["phases"]["R2"]["owners"]
    for step_ids in owners.values():
        for step_id in step_ids:
            step = gate_config["steps"][step_id]
            assert "source_compile" in step["depends_on"], f"{step_id} missing source_compile dependency"


def test_r2_phase_step_depends_on_source_compile(gate_config):
    """R2 phase test step depends on source_compile."""
    phase_steps = gate_config["phases"]["R2"]["phase"]
    for step_id in phase_steps:
        step = gate_config["steps"][step_id]
        assert "source_compile" in step["depends_on"], f"{step_id} missing source_compile dependency"


def test_r2_step_count_within_bounds(gate_config):
    """R2 step count is within the configured limit."""
    max_steps = gate_config["limits"]["max_steps_per_tier"]
    r2 = gate_config["phases"]["R2"]
    all_steps: set[str] = set()
    for step_ids in r2["owners"].values():
        all_steps.update(step_ids)
    all_steps.update(r2["phase"])
    all_steps.update(r2["admission"])
    # Add dependencies
    to_check = list(all_steps)
    while to_check:
        step_id = to_check.pop()
        step = gate_config["steps"].get(step_id)
        if step:
            for dep in step["depends_on"]:
                if dep not in all_steps:
                    all_steps.add(dep)
                    to_check.append(dep)
    assert len(all_steps) <= max_steps * 3, f"R2 has {len(all_steps)} steps, limit is {max_steps * 3}"


def test_r2_structure_step_kind_is_admitted():
    """r2_structure step kind is admitted by the validation gate module."""
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "src" / "cemm_authoritative_hybrid"))
    try:
        from validation_gate import STEP_KINDS, ADMISSION_ONLY_KINDS
        assert "r2_structure" in STEP_KINDS
        assert "r2_structure" in ADMISSION_ONLY_KINDS
    finally:
        sys.path.pop(0)
        sys.path.pop(0)


def test_r2_structure_scan_finds_owners():
    """R2 structure scan finds the recursive composer and compiler."""
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    sys.path.insert(0, str(ROOT / "src" / "cemm_authoritative_hybrid"))
    try:
        from validation_gate import _scan_r2_structure, GateConfigError
        try:
            report = _scan_r2_structure(ROOT)
            assert report["compiler_owner"] == "src/cemm_authoritative_hybrid/recursive_compiler.py"
            assert report["proposer_owner"] == "src/cemm_authoritative_hybrid/recursive_composer"
            assert report["runtime_owner"] == "src/cemm_authoritative_hybrid/runtime.py"
            assert report["forbidden_match_count"] == 0
            assert report["scanned_file_count"] > 0
        except GateConfigError as exc:
            pytest.fail(f"R2 structure scan failed: {exc}")
    finally:
        sys.path.pop(0)
        sys.path.pop(0)
