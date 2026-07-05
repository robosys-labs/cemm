"""v4.2 no-bypass contract tests.

Enforces: no operator bypasses the GraphPatch pipeline by writing
directly to the claim store. This is a non-drift test suite — no
domain-specific strings, no hardcoded domain primitives.
"""

from __future__ import annotations

import ast
import os
import pathlib
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parent
OPERATORS_DIR = PROJECT / "operators"

HARDCODED_PRIMITIVES = frozenset({
    "PresidentAtom",
    "WeatherAtom",
    "CountryAtom",
    "LeaderAtom",
    "PersonAtom",
    "CityAtom",
    "AnimalAtom",
})

TYPED_PATCH_OPERATIONS = frozenset({
    "upsert_relation_candidate",
    "upsert_concept_candidate",
    "observe_port_binding",
    "observe_construction_match",
    "observe_predicate_schema",
    "observe_causal_affordance",
    "update_source_policy",
    "retain_exemplar",
    "discard_trace",
    "merge_concepts",
    "mark_counterexample",
})


# ── Helpers ─────────────────────────────────────────────────────


def _operator_files() -> list[pathlib.Path]:
    return sorted(OPERATORS_DIR.rglob("*.py"))


def _test_files() -> list[pathlib.Path]:
    return sorted(HERE.rglob("*.py"))


def _has_claims_in_chain(node: ast.AST, depth: int = 0) -> bool:
    if depth > 5:
        return False
    if isinstance(node, ast.Attribute):
        if node.attr == "claims":
            return True
        return _has_claims_in_chain(node.value, depth + 1)
    return False


def _check_file_forbidden_put(file_path: pathlib.Path) -> list[str]:
    violations: list[str] = []
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
                call = node.value
                if isinstance(call.func, ast.Attribute) and call.func.attr == "put":
                    if _has_claims_in_chain(call.func.value):
                        violations.append(f"{file_path.name}:{node.lineno}")
    except SyntaxError:
        pass
    return violations


# ── Tests ───────────────────────────────────────────────────────


def test_no_operator_writes_directly_to_claims_store() -> None:
    violations: list[str] = []
    for fpath in _operator_files():
        text = fpath.read_text(encoding="utf-8")
        if "store.claims.put" in text or "claims_store.put" in text:
            violations.append(fpath.name)
    assert violations == [], (
        f"Operators bypassing GraphPatch via direct claims store write: {violations}"
    )


def test_invariant_guard_catches_custom_upsert_claim() -> None:
    from cemm.kernel.invariant_guard import InvariantGuard
    InvariantGuard.reset()
    assert InvariantGuard.check_no_custom_upsert_claim_outside_adapter("upsert_relation_candidate") is True
    assert InvariantGuard.check_no_custom_upsert_claim_outside_adapter("custom:upsert_claim") is False
    assert len(InvariantGuard.errors) == 1


def test_graph_patch_operations_are_typed_not_custom() -> None:
    violations: list[str] = []
    for fpath in _operator_files():
        text = fpath.read_text(encoding="utf-8")
        if "PatchOperation" not in text:
            continue
        try:
            tree = ast.parse(text, filename=str(fpath))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                if node.func.id == "PatchOperation" and node.args:
                    arg = node.args[0]
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        op = arg.value
                        if op.startswith("custom:"):
                            violations.append(f"{fpath.name}:{node.lineno}:{op}")
                        elif op not in TYPED_PATCH_OPERATIONS and "upsert_claim" in op:
                            violations.append(f"{fpath.name}:{node.lineno}:{op}")
    assert violations == [], (
        f"Operators using custom/untyped GraphPatch operations: {violations}"
    )


def test_no_domain_primitives() -> None:
    violations: list[str] = []
    for fpath in _test_files():
        if fpath.name == os.path.basename(__file__):
            continue
        text = fpath.read_text(encoding="utf-8")
        for primitive in HARDCODED_PRIMITIVES:
            if primitive in text:
                violations.append(f"{fpath.name}:{primitive}")
    assert violations == [], (
        f"Test files contain hardcoded domain primitives: {violations}"
    )


def test_no_store_put_in_operator_files() -> None:
    all_violations: list[str] = []
    for fpath in _operator_files():
        all_violations.extend(_check_file_forbidden_put(fpath))
    assert all_violations == [], (
        f"Operators using store.claims.put bypassing GraphPatch: {all_violations}"
    )
