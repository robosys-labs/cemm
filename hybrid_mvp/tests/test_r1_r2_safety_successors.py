"""Current-ABI successors for the three frozen safety assertion lineages."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from cemm_authoritative_hybrid.expressions import (
    ApplicationFiller,
    GroundedReference,
    RoleBinding,
    SemanticApplication,
    SemanticExpression,
)


ROOT = Path(__file__).parents[1]


def _source_tree(relative_path: str) -> ast.Module:
    path = ROOT / relative_path
    size = path.stat().st_size
    assert size <= 2 * 1024 * 1024
    raw = path.read_bytes()
    assert len(raw) == size
    return ast.parse(raw.decode("utf-8"), filename=str(path))


def test_r1_runtime_has_no_raw_phrase_equality_dispatch() -> None:
    tree = _source_tree("src/cemm_authoritative_hybrid/runtime.py")
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and any(
            isinstance(value, ast.Constant)
            and isinstance(value.value, str)
            and " " in value.value
            for value in (node.left, *node.comparators)
        ):
            violations.append(ast.unparse(node))

    assert violations == []


def test_r1_safe_artifact_contract_has_no_legacy_checkpoint_api() -> None:
    tree = _source_tree("src/cemm_authoritative_hybrid/training.py")
    names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }

    assert names.isdisjoint({"load_checkpoint", "save_checkpoint"})


def test_r2_semantic_expression_rejects_application_cycle() -> None:
    a = SemanticApplication(
        "app:a",
        "op:event",
        "event:say",
        (
            RoleBinding("role:actor", GroundedReference("entity:mary")),
            RoleBinding("role:content", ApplicationFiller("app:b")),
        ),
    )
    b = SemanticApplication(
        "app:b",
        "op:event",
        "event:say",
        (
            RoleBinding("role:actor", GroundedReference("entity:bob")),
            RoleBinding("role:content", ApplicationFiller("app:a")),
        ),
    )

    with pytest.raises(ValueError, match="root has a parent|expression cycle"):
        SemanticExpression.create(applications=(a, b), root_refs=("app:a",))


__cemm_test_inventory__ = {
    "tests/test_r1_r2_safety_successors.py::test_r1_runtime_has_no_raw_phrase_equality_dispatch": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:safety-and-contracts-no-raw-phrase-equality-dispatch-in-runtime-source",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "9e5a007d2dc108ac5cf94b981f7d622ec609f9c5f63f60b1917226e19b7ccb0c",
        "supersedes_node_id": "tests/test_safety_and_contracts.py::test_no_raw_phrase_equality_dispatch_in_runtime_source",
    },
    "tests/test_r1_r2_safety_successors.py::test_r1_safe_artifact_contract_has_no_legacy_checkpoint_api": {
        "activation_phase": "R1",
        "assertion_ref": "assertion:safety-and-contracts-safe-artifact-contract-replaces-legacy-checkpoint",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "runtime-path",
        "source_ast_sha256": "fde1ce11494bda017351f0a8c4797014d7f0f73a5e643f08aafb6e2ba53bdb16",
        "supersedes_node_id": "tests/test_safety_and_contracts.py::test_safe_artifact_contract_replaces_legacy_checkpoint",
    },
    "tests/test_r1_r2_safety_successors.py::test_r2_semantic_expression_rejects_application_cycle": {
        "activation_phase": "R2",
        "assertion_ref": "assertion:safety-and-contracts-recursive-graph-cycle-rejected",
        "diagnostic_role": "owner",
        "introduced_by_task": "R5-Hard-Cut-Foundation",
        "owner_ref": "expression-compiler",
        "source_ast_sha256": "0f75ec2896414bfde10c59203a05b521d58257607fcd06c10a37f9466bd988cf",
        "supersedes_node_id": "tests/test_safety_and_contracts.py::test_recursive_graph_cycle_rejected",
    },
}
