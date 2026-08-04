"""R1 selectors execute only the owners introduced by the current phase."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from test_inventory_core import load_and_verify, verify_document_authority_pin  # noqa: E402
from cemm_authoritative_hybrid import process_control as process_control_module  # noqa: E402


sys.modules["process_control"] = process_control_module
from validation_gate import load_gate_graph, validate_inventory_contract  # noqa: E402


def test_r1_owner_selectors_exclude_prior_phase_owner_runs() -> None:
    inventory_path = ROOT / "governance" / "test_inventory.json"
    inventory = load_and_verify(
        ROOT,
        inventory_path,
        phase="R1",
        enforce_reviewed_counts=True,
        expected_sha256=verify_document_authority_pin(ROOT, inventory_path),
    )
    assert set(inventory.owner_node_ids) == {
        "cycle-result",
        "program-verifier",
        "runtime-path",
    }
    assert all(
        inventory.later_nodes[node_id].activation_phase == "R1"
        for nodes in inventory.owner_node_ids.values()
        for node_id in nodes
    )


def test_r1_configured_selectors_equal_phase_local_inventory() -> None:
    inventory_path = ROOT / "governance" / "test_inventory.json"
    inventory = load_and_verify(
        ROOT,
        inventory_path,
        phase="R1",
        enforce_reviewed_counts=True,
        expected_sha256=verify_document_authority_pin(ROOT, inventory_path),
    )
    graph = load_gate_graph(ROOT / "configs" / "validation_gates.json")
    validate_inventory_contract(graph, inventory, phase="R1")
    assert graph.resolve_phase("R1", "phase") == (
        "governance",
        "source_compile",
        "r1_phase_tests",
    )
    owner_nodes = set(graph.resolve_all_owner_pytest_nodes("R1"))
    phase_nodes = set(graph.resolve_pytest_nodes("R1", "phase"))
    assert owner_nodes.isdisjoint(phase_nodes)


def test_r1_admission_runs_one_active_suite_without_owner_replay() -> None:
    graph = load_gate_graph(ROOT / "configs" / "validation_gates.json")
    resolved = graph.resolve_phase("R1", "admission")
    assert {"r1_structure", "sqlite_activation", "pytest_active"}.issubset(resolved)
    assert not {
        "r1_program_verifier_owner_tests",
        "r1_cycle_owner_tests",
        "r1_runtime_owner_tests",
        "r1_phase_tests",
    } & set(resolved)
    assert sum(graph.steps[step_id].kind == "pytest_inventory" for step_id in resolved) == 1
    assert all(graph.steps[step_id].kind != "pytest" for step_id in resolved)


__cemm_test_inventory__ = {'tests/test_r1_inventory_phase_scoping.py::test_r1_admission_runs_one_active_suite_without_owner_replay': {'activation_phase': 'R1',
                                                                                                            'assertion_ref': 'assertion:r1-admission-one-active-suite',
                                                                                                            'diagnostic_role': 'phase',
                                                                                                            'introduced_by_task': 'R1-Task-9-Performance',
                                                                                                            'source_ast_sha256': 'f8fffb4dc3a39858e5821e680b4407e63e807166955fa0ee3368cf39f114c83b'},
 'tests/test_r1_inventory_phase_scoping.py::test_r1_configured_selectors_equal_phase_local_inventory': {'activation_phase': 'R1',
                                                                                                        'assertion_ref': 'assertion:r1-config-selectors-match-inventory',
                                                                                                        'diagnostic_role': 'phase',
                                                                                                        'introduced_by_task': 'R1-Task-9-Performance',
                                                                                                        'source_ast_sha256': 'e920c1161427ee3b436ff4e88c4b31bbe560d9984d1660455c070861f10f9efb'},
 'tests/test_r1_inventory_phase_scoping.py::test_r1_owner_selectors_exclude_prior_phase_owner_runs': {'activation_phase': 'R1',
                                                                                                      'assertion_ref': 'assertion:r1-owner-selectors-phase-local',
                                                                                                      'diagnostic_role': 'phase',
                                                                                                      'introduced_by_task': 'R1-Task-9-Performance',
                                                                                                      'source_ast_sha256': '8920ff59e410d2cb32fd909deb5338dbd0d440296de1b21c97570540ddccd5c7'}}
