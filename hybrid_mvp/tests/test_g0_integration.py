"""Cross-owner invariants for the bounded G0 validation control plane."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for reviewed_path in (SRC, SCRIPTS):
    if str(reviewed_path) not in sys.path:
        sys.path.insert(0, str(reviewed_path))

from cemm_authoritative_hybrid import process_control as process_control_module  # noqa: E402
sys.modules["process_control"] = process_control_module
from validation_gate import load_gate_graph, validate_inventory_contract  # noqa: E402


def _inventory_result():
    path = SCRIPTS / "test_inventory_core.py"
    name = "_cemm_g0_integration_inventory_core"
    sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    inventory_path = ROOT / "governance" / "test_inventory.json"
    digest = module.verify_document_authority_pin(ROOT, inventory_path)
    return module.load_and_verify(
        ROOT,
        inventory_path,
        phase="G0",
        enforce_reviewed_counts=True,
        expected_sha256=digest,
    )


def test_g0_admission_plan_is_coalesced_and_bounded() -> None:
    graph = load_gate_graph(ROOT / "configs" / "validation_gates.json")
    assert graph.resolve_phase("G0", "admission") == (
        "governance",
        "source_compile",
        "pytest_active",
    )
    assert not {"corpus", "training", "reproduction"} & set(
        graph.resolve_phase("G0", "admission")
    )


def test_g0_admission_excludes_expensive_or_runtime_activation_steps() -> None:
    graph = load_gate_graph(ROOT / "configs" / "validation_gates.json")
    selected = set(graph.resolve_phase("G0", "admission"))
    assert "authority_link" not in selected
    assert "sqlite_activation" not in selected
    assert all(
        not any(token in step_id for token in ("corpus", "training", "reproduction"))
        for step_id in selected
    )


def test_runtime_has_no_validation_import() -> None:
    runtime = (ROOT / "src" / "cemm_authoritative_hybrid" / "runtime.py").read_text(
        encoding="utf-8"
    )
    assert "validation_gate" not in runtime
    assert "pytest_gate_runner" not in runtime


def test_owner_and_phase_nodes_are_disjoint() -> None:
    graph = load_gate_graph(ROOT / "configs" / "validation_gates.json")
    owner: set[str] = set()
    for owner_ref in graph.phases["G0"].owners:
        owner.update(graph.resolve_pytest_nodes("G0", "owner", owner_ref))
    phase = set(graph.resolve_pytest_nodes("G0", "phase"))
    assert owner.isdisjoint(phase)


def test_configured_selectors_equal_literal_inventory_roles() -> None:
    graph = load_gate_graph(ROOT / "configs" / "validation_gates.json")
    inventory = _inventory_result()
    selector = validate_inventory_contract(graph, inventory, phase="G0")
    assert selector.active_node_ids == inventory.active_node_ids
    assert selector.collectable_node_ids == inventory.collectable_node_ids

    marker = ROOT / "tests" / "__init__.py"
    assert marker.is_file()
    for module_name in (
        "tests.test_query_engine",
        "tests.test_inference_bounds",
        "tests.test_recursive_inference",
    ):
        spec = importlib.util.find_spec(module_name)
        assert spec is not None and spec.origin is not None
        assert Path(spec.origin).resolve().is_relative_to(ROOT / "tests")


def test_each_executing_tier_has_one_pytest_process() -> None:
    graph = load_gate_graph(ROOT / "configs" / "validation_gates.json")
    for owner_ref in graph.phases["G0"].owners:
        assert graph.pytest_process_count("G0", "owner", owner=owner_ref) == 1
    assert graph.pytest_process_count("G0", "phase") == 1
    assert graph.pytest_process_count("G0", "admission") == 1


def test_source_compile_avoids_duplicate_test_tree_parse() -> None:
    graph = load_gate_graph(ROOT / "configs" / "validation_gates.json")
    compile_step = graph.steps["source_compile"]
    assert tuple(compile_step.material["roots"]) == ("scripts/", "src/")
    assert "tests/" not in compile_step.inputs


def test_validation_control_plane_import_leaves_runtime_and_torch_unloaded() -> None:
    for module_name in (
        "validation_gate",
        "test_inventory_core",
        "update_replay_status",
    ):
        code = (
            "import importlib,json,sys; "
            f"sys.path.insert(0,{str(ROOT / 'src')!r}); "
            "pc=importlib.import_module('cemm_authoritative_hybrid.process_control'); "
            "sys.modules['process_control']=pc; "
            f"sys.path.insert(0,{str(SCRIPTS)!r}); "
            f"importlib.import_module({module_name!r}); "
            "blocked=sorted(name for name in sys.modules if "
            "name=='torch' or name.startswith('torch.') or "
            "name in {'cemm_authoritative_hybrid.model',"
            "'cemm_authoritative_hybrid.runtime',"
            "'cemm_authoritative_hybrid.training'}); "
            "print(json.dumps(blocked))"
        )
        completed = subprocess.run(
            [sys.executable, "-I", "-c", code],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
            timeout=30,
        )
        assert completed.returncode == 0, (
            module_name,
            completed.stderr,
        )
        assert json.loads(completed.stdout) == [], module_name


__cemm_test_inventory__ = {
    "tests/test_g0_integration.py::test_configured_selectors_equal_literal_inventory_roles": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:g0-config-selectors-equal-literal-inventory-roles",
        "diagnostic_role": "phase",
        "introduced_by_task": "G0-Task-4",
        "source_ast_sha256": "9c9a328b03d0eb30f2b9c4b9e96eb083b55511366ff24958dbd39ba0882da2e1",
    },
    "tests/test_g0_integration.py::test_each_executing_tier_has_one_pytest_process": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:g0-each-tier-has-one-pytest-process",
        "diagnostic_role": "phase",
        "introduced_by_task": "G0-Task-4",
        "source_ast_sha256": "5e7feb962250855d5df6d8ecf0e3c72685f5fb7bfdf8b28853afc610411bb24e",
    },
    "tests/test_g0_integration.py::test_g0_admission_excludes_expensive_or_runtime_activation_steps": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:g0-admission-excludes-expensive-runtime-activation",
        "diagnostic_role": "phase",
        "introduced_by_task": "G0-Task-4",
        "source_ast_sha256": "48f8fb890b538a7b7992782ad998cd24e74b9dc78da73ad5e638ce6ce7b4950a",
    },
    "tests/test_g0_integration.py::test_g0_admission_plan_is_coalesced_and_bounded": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:g0-admission-plan-coalesced-and-bounded",
        "diagnostic_role": "phase",
        "introduced_by_task": "G0-Task-4",
        "source_ast_sha256": "a7299a73b3ef6841edc18a04d2b5cdf8b89e95bdfbe0c8e9363c30d3471ec3ef",
    },
    "tests/test_g0_integration.py::test_owner_and_phase_nodes_are_disjoint": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:g0-owner-and-phase-nodes-disjoint",
        "diagnostic_role": "phase",
        "introduced_by_task": "G0-Task-4",
        "source_ast_sha256": "4eb5177954bc07186809aa0095221fda34f391ff272176e31b6f963f0d2472e6",
    },
    "tests/test_g0_integration.py::test_runtime_has_no_validation_import": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:g0-runtime-has-no-validation-import",
        "diagnostic_role": "phase",
        "introduced_by_task": "G0-Task-4",
        "source_ast_sha256": "f1344ae54e0b6776c22da020e9d0941c20e5a197a9dd48eb8ca5225f757013b2",
    },
    "tests/test_g0_integration.py::test_source_compile_avoids_duplicate_test_tree_parse": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:g0-source-compile-avoids-duplicate-test-parse",
        "diagnostic_role": "phase",
        "introduced_by_task": "G0-Task-4",
        "source_ast_sha256": "1861008cae13cb44c3710033b3a12dc52421d3500f2e92b0851d600f4d5532e0",
    },
    "tests/test_g0_integration.py::test_validation_control_plane_import_leaves_runtime_and_torch_unloaded": {
        "activation_phase": "G0",
        "assertion_ref": "assertion:g0-control-plane-import-leaves-runtime-torch-unloaded",
        "diagnostic_role": "phase",
        "introduced_by_task": "G0-Task-4",
        "source_ast_sha256": "a19a9f418b10138f7a54f19f807c02a29158ebc258d22a735838a65bf22ed0f1",
    },
}
