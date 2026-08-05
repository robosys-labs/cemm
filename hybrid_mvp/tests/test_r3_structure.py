"""R3 anti-bypass structural admission checks."""
from __future__ import annotations

import ast
from pathlib import Path

__cemm_test_inventory__ = {
    "tests/test_r3_structure.py::test_cycle_extension_preserves_canonical_cycle_class_owner": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-cycle-extension-preserves-canonical-cycle-class-owner",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Complete",
        "source_ast_sha256": "d22ddfbd6b1861691ab7afa7c87aa2a799f26ed9eb2edcaaf4f873ae79240a43"
    },
    "tests/test_r3_structure.py::test_only_atomic_effect_persistence_commits_world_state": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-only-atomic-effect-persistence-commits-world-state",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Complete",
        "source_ast_sha256": "e63fd3932f6922170b5e2c08de0927415eb0e3d57376faa3a8e0bc8622df1a94"
    },
    "tests/test_r3_structure.py::test_post_verify_owners_do_not_consume_program_graph_or_raw_text": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-post-verify-owners-do-not-consume-program-graph-or-raw-text",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Complete",
        "source_ast_sha256": "7b610a1f4d5570433694baa64d97aec6d5b603086fcb42e7622dd13a1e07511e"
    },
    "tests/test_r3_structure.py::test_r3_runtime_has_exact_r5_boundary": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-r3-runtime-has-exact-r5-boundary",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Complete",
        "source_ast_sha256": "503f91cec4b6a807ac62217a87532f3e402ac25d5ab10e7094936426f50bc7dc"
    }
}


ROOT = Path(__file__).parents[1]
SRC = ROOT / "src" / "cemm_authoritative_hybrid"


def test_post_verify_owners_do_not_consume_program_graph_or_raw_text() -> None:
    owners = [
        "decision.py", "r3_cognition.py", "r3_effects.py", "r3_learning.py",
        "r3_response.py", "r3_kernel.py", "situation.py",
    ]
    source = "\n".join((SRC / name).read_text(encoding="utf-8") for name in owners)
    assert "program.graph" not in source
    assert "getattr(program, \"graph\"" not in source
    assert "source_text" not in source


def test_only_atomic_effect_persistence_commits_world_state() -> None:
    offenders = []
    for path in SRC.glob("*.py"):
        if path.name in ("r3_persistence.py", "query.py", "state.py"):
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "commit" and isinstance(node.func.value, ast.Attribute):
                    if node.func.value.attr == "world":
                        offenders.append(path.name)
    assert not offenders


def test_r3_runtime_has_exact_r5_boundary() -> None:
    source = (SRC / "runtime.py").read_text(encoding="utf-8")
    assert "contract:r5:realize_surface" in source
    assert "contract:r3:evaluate" not in source


def test_cycle_extension_preserves_canonical_cycle_class_owner() -> None:
    extension = (SRC / "r3_cycle.py").read_text(encoding="utf-8")
    cycle = (SRC / "cycle.py").read_text(encoding="utf-8")
    assert "class CycleResult" in extension
    assert "class CycleFinalizer" in extension
    assert "CYCLE_RESULT_ABI_VERSION = 3" in extension
    assert "class CycleResult" in cycle
    assert "class CycleFinalizer" in cycle
    assert "CYCLE_RESULT_ABI_VERSION = 2" in cycle
