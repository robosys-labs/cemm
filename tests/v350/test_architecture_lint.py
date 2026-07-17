from __future__ import annotations

import json
from pathlib import Path

from cemm.v350.architecture_lint import scan_file, scan_legacy_debt, scan_tree


def test_v350_tree_has_no_prohibited_authority_patterns() -> None:
    root = Path(__file__).resolve().parents[2] / "cemm" / "v350"
    assert scan_tree(root) == ()


def test_lint_rejects_v347_import(tmp_path: Path) -> None:
    path = tmp_path / "bad.py"
    path.write_text("from cemm.v347.model import ReferentKind\n", encoding="utf-8")
    assert any(item.code == "v347_dependency" for item in scan_file(path))


def test_lint_rejects_learned_type_enum(tmp_path: Path) -> None:
    path = tmp_path / "bad.py"
    path.write_text("from enum import Enum\nclass ReferentKind(Enum):\n    FOX='fox'\n", encoding="utf-8")
    assert any(item.code == "learned_type_enum" for item in scan_file(path))


def test_lint_rejects_generic_negative_axis(tmp_path: Path) -> None:
    path = tmp_path / "bad.py"
    path.write_text("from dataclasses import dataclass\n@dataclass\nclass X:\n    negative: bool\n", encoding="utf-8")
    assert any(item.code == "generic_negative_axis" for item in scan_file(path))


def test_lint_rejects_event_specific_mutation(tmp_path: Path) -> None:
    path = tmp_path / "bad.py"
    path.write_text("def apply_death_state():\n    pass\n", encoding="utf-8")
    assert any(item.code == "event_specific_mutation" for item in scan_file(path))


def test_lint_rejects_kernel_surface_word_branch(tmp_path: Path) -> None:
    path = tmp_path / "bad.py"
    path.write_text("def f(token):\n    return token == 'how'\n", encoding="utf-8")
    assert any(item.code == "kernel_surface_word_branch" for item in scan_file(path))


def test_legacy_debt_manifest_is_a_ratchet(tmp_path: Path) -> None:
    (tmp_path / "legacy.py").write_text("legacy()\n", encoding="utf-8")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "budgets": [{
            "debt_id": "legacy-call",
            "path": "legacy.py",
            "pattern": "legacy\\(",
            "maximum_count": 1,
        }]
    }), encoding="utf-8")
    assert scan_legacy_debt(tmp_path, manifest) == ()
    (tmp_path / "legacy.py").write_text("legacy()\nlegacy()\n", encoding="utf-8")
    findings = scan_legacy_debt(tmp_path, manifest)
    assert findings and findings[0].observed_count == 2


def test_removing_legacy_file_is_allowed(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({
        "budgets": [{
            "debt_id": "removed",
            "path": "missing.py",
            "pattern": "x",
            "maximum_count": 1,
        }]
    }), encoding="utf-8")
    assert scan_legacy_debt(tmp_path, manifest) == ()


def test_lint_rejects_v347_import_alias_and_attribute_access(tmp_path: Path) -> None:
    imported = tmp_path / "imported.py"
    imported.write_text("from cemm import v347\n", encoding="utf-8")
    assert any(item.code == "v347_dependency" for item in scan_file(imported))

    accessed = tmp_path / "accessed.py"
    accessed.write_text("import cemm\nx = cemm.v347.model\n", encoding="utf-8")
    assert any(item.code == "v347_dependency" for item in scan_file(accessed))


def test_lint_rejects_surface_membership_and_prefix_branches(tmp_path: Path) -> None:
    membership = tmp_path / "membership.py"
    membership.write_text("def f(token):\n    return token in {'how', 'what'}\n", encoding="utf-8")
    assert any(item.code == "kernel_surface_word_branch" for item in scan_file(membership))

    prefix = tmp_path / "prefix.py"
    prefix.write_text("def f(surface):\n    return surface.startswith('how')\n", encoding="utf-8")
    assert any(item.code == "kernel_surface_word_branch" for item in scan_file(prefix))


def test_lint_rejects_named_event_behavior_branch(tmp_path: Path) -> None:
    path = tmp_path / "transition.py"
    path.write_text(
        "def transition(event):\n    return event.event_schema_ref == 'event:die'\n",
        encoding="utf-8",
    )
    assert any(item.code == "event_specific_semantic_branch" for item in scan_file(path))


def test_lint_rejects_targetless_response_goal(tmp_path: Path) -> None:
    path = tmp_path / "response_goals.py"
    path.write_text(
        "def f(Candidate):\n    return Candidate(target_proposition_refs=())\n",
        encoding="utf-8",
    )
    assert any(item.code == "targetless_response_goal" for item in scan_file(path))
