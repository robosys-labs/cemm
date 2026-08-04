"""Safety and contract tests that survive the six-phase cutover.

Legacy tests that depended on the retired ``stores``/``training`` modules or
the stage-bound checkpoint architecture have been removed. The assertions
below are still valid under the new six-phase contract.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from legacy_propositions import Application, PropositionGraph

ROOT = Path(__file__).parents[1]


def test_no_raw_phrase_equality_dispatch_in_runtime_source():
    """The runtime must not branch on raw phrase-string equality."""
    tree = ast.parse((ROOT / "src/cemm_authoritative_hybrid/runtime.py").read_text())
    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and any(
            isinstance(x, ast.Constant)
            and isinstance(x.value, str)
            and " " in x.value
            for x in [node.left, *node.comparators]
        ):
            violations.append(ast.unparse(node))
    assert not violations


def test_recursive_graph_cycle_rejected():
    a = Application.create(
        "op:event",
        {
            "role:event": "event-instance:a",
            "role:type": "event:say",
            "role:actor": "entity:mary",
            "role:content": {"app": "app:b"},
        },
        application_ref="app:a",
    )
    b = Application.create(
        "op:event",
        {
            "role:event": "event-instance:b",
            "role:type": "event:say",
            "role:actor": "entity:bob",
            "role:content": {"app": "app:a"},
        },
        application_ref="app:b",
    )
    with pytest.raises(ValueError, match="cycle"):
        PropositionGraph.create([a, b], "app:a", depth=2)


def test_safe_artifact_contract_replaces_legacy_checkpoint():
    """The legacy torch.load checkpoint loader is removed from training.py."""
    tree = ast.parse((ROOT / "src/cemm_authoritative_hybrid/training.py").read_text())
    names = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    assert "load_checkpoint" not in names
    assert "save_checkpoint" not in names
