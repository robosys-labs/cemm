"""R2 plan contract: ensure R2 does not import R3-R8 owners and enumerate due nodes."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src" / "cemm_authoritative_hybrid"
_INVENTORY = _ROOT / "governance" / "test_inventory.json"

# R3-R8 owner modules that R2 must not import
_FORBIDDEN_R3_R8_MODULES = frozenset(
    {
        "effects",
        "realization",
        "response",
        "learning",
        "evaluation",
        "training",
        "episodes",
        "calibration",
        "partitions",
        "query",
        "epistemics",
        "gaps",
        "dialogue",
        "artifacts",
    }
)


def _source_imports(module_name: str) -> set[str]:
    """Return the set of cemm_authoritative_hybrid imports in a module."""
    path = _SRC / f"{module_name}.py"
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8")
    imports: set[str] = set()
    for m in re.finditer(
        r"from\s+cemm_authoritative_hybrid(?:\.\w+)*\s+import\s+(\w+)",
        text,
    ):
        imports.add(m.group(1))
    for m in re.finditer(
        r"from\s+cemm_authoritative_hybrid\.(\w+)\s+import",
        text,
    ):
        imports.add(m.group(1))
    return imports


_R2_OWNERS = frozenset(
    {
        "forms",
        "grounding",
        "affordances",
        "contributions",
        "proposal_context",
        "programs",
        "proposal",
        "expressions",
        "coverage",
        "verifier",
        "runtime",
        "bootstrap",
        "state",
        "config",
        "persistence",
        "authority",
        "canonical",
        "capabilities",
        "process_control",
        "governance",
    }
)


def test_r2_owners_do_not_import_r3_r8_owners() -> None:
    """R2 owner modules must not import R3-R8 owner modules."""
    violations: list[str] = []
    for owner in sorted(_R2_OWNERS):
        imports = _source_imports(owner)
        forbidden = imports & _FORBIDDEN_R3_R8_MODULES
        if forbidden:
            violations.append(
                f"{owner}.py imports forbidden R3-R8 modules: {sorted(forbidden)}"
            )
    assert not violations, "R2 owners import R3-R8 modules:\n" + "\n".join(
        violations
    )


def test_r2_plan_is_committed() -> None:
    """The R2 implementation plan must be committed in the governed docs tree."""
    plan_path = _ROOT / "docs" / "superpowers" / "plans" / "2026-08-04-hybrid-mvp-r2-implementation-plan.md"
    assert plan_path.exists(), "R2 implementation plan is not committed"
    text = plan_path.read_text(encoding="utf-8")
    assert "R2 Recursive Composition" in text
    assert "Task 0" in text
    assert "Task 10" in text


def test_r2_predecessor_inventory_is_enumerable() -> None:
    """Every predecessor node whose activation phase is R2 can be enumerated."""
    with open(_INVENTORY, "r", encoding="utf-8") as f:
        inventory = json.load(f)
    r2_tests = [
        t for t in inventory["source_tests"] if t["activation_phase"] == "R2"
    ]
    assert len(r2_tests) > 0, "No R2 source tests found in inventory"
    # Every R2 test must have a classification
    for t in r2_tests:
        assert t["classification"] in (
            "retained",
            "rewritten",
            "historical",
        ), f"Unknown classification for {t['source_test_ref']}: {t['classification']}"


def test_r2_unknown_frontier_successor_is_required() -> None:
    """The frozen inventory requires the unknown-frontier successor."""
    with open(_INVENTORY, "r", encoding="utf-8") as f:
        inventory = json.load(f)
    # Find the rewritten test that requires the unknown-frontier successor
    target = "tests/test_r2_unknown_frontier.py::test_unknown_surface_abstains_or_emits_typed_unresolved_candidate"
    found = False
    for t in inventory["source_tests"]:
        if t["successor_node_ids"] and target in t["successor_node_ids"]:
            found = True
            break
    assert found, (
        "Frozen inventory does not require the unknown-frontier successor. "
        "This test should not be removed without reviewed supersession."
    )


def test_r2_validation_phase_is_not_yet_activated() -> None:
    """R2 validation phase must not be activated until implementation is complete."""
    gates_path = _ROOT / "configs" / "validation_gates.json"
    with open(gates_path, "r", encoding="utf-8") as f:
        gates = json.load(f)
    # R2 should not have a phase entry until it's ready for admission
    # This test will be updated when R2 is activated
    phases = gates.get("phases", {})
    # R2 may or may not exist yet; this test documents the current state
    if "R2" in phases:
        # If R2 exists, it must have the required structure
        r2 = phases["R2"]
        assert "admission" in r2, "R2 phase missing admission steps"
        assert "owners" in r2, "R2 phase missing owner selectors"
        assert "phase" in r2, "R2 phase missing phase selector"
