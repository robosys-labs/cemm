"""Architecture contract tests — verify CEMM v4.2 invariants."""

from __future__ import annotations

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
os.environ["CEMM_EXPORT_PATH"] = ""

from cemm.types.uol_atom import CANONICAL_ATOM_KINDS, CANONICAL_EDGE_TYPES


def test_canonical_atom_kinds() -> None:
    assert len(CANONICAL_ATOM_KINDS) == 16, (
        f"Expected 16 canonical atom kinds, got {len(CANONICAL_ATOM_KINDS)}"
    )


def test_canonical_edge_types() -> None:
    assert len(CANONICAL_EDGE_TYPES) == 16, (
        f"Expected 16 canonical edge types, got {len(CANONICAL_EDGE_TYPES)}"
    )


def test_agents_md_references_architecture() -> None:
    agents_path = os.path.join(os.path.dirname(__file__), "..", "AGENTS.md")
    assert os.path.exists(agents_path), "AGENTS.md must exist"
    with open(agents_path, encoding="utf-8") as f:
        content = f.read()
    assert "consolidated_architecture" in content, (
        "AGENTS.md must reference the consolidated architecture doc"
    )
