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
            assert report["proposer_owner"] == "src/cemm_authoritative_hybrid/recursive_composer.py"
            assert report["runtime_owner"] == "src/cemm_authoritative_hybrid/runtime.py"
            assert report["forbidden_match_count"] == 0
            assert report["scanned_file_count"] > 0
        except GateConfigError as exc:
            pytest.fail(f"R2 structure scan failed: {exc}")
    finally:
        sys.path.pop(0)
        sys.path.pop(0)
