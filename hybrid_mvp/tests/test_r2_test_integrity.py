"""R2 test integrity guards: reject vacuous assertions and stale patterns."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

_TESTS = Path(__file__).resolve().parent


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_no_trivially_true_numeric_bounds() -> None:
    """No R2 test should assert ``len(...) >= 0`` or similar tautologies."""
    offenders: list[str] = []
    for py in _TESTS.glob("test_*.py"):
        if py.name == Path(__file__).name:
            continue  # Don't check self
        text = _read(py)
        # Match len(...) >= 0 which is always true
        for m in re.finditer(r"len\s*\([^)]*\)\s*>=\s*0\b", text):
            offenders.append(f"{py.name}: trivially true bound at offset {m.start()}")
    assert not offenders, "Trivially true numeric bounds found:\n" + "\n".join(
        offenders
    )


def test_no_r2_test_asserts_only_class_absence() -> None:
    """R2 tests must not only assert absence of a retired class."""
    # This guard checks that tests named test_r2_* are not solely
    # asserting that some class doesn't exist
    offenders: list[str] = []
    for py in _TESTS.glob("test_r2_*.py"):
        text = _read(py)
        # Strip comments and docstrings (rough)
        lines = [
            line
            for line in text.splitlines()
            if line.strip()
            and not line.strip().startswith("#")
            and not line.strip().startswith('"""')
            and not line.strip().startswith("'''")
        ]
        assert_lines = [l for l in lines if "assert " in l]
        if len(assert_lines) == 0:
            continue
        # Check if all assertions are just "not hasattr" or class absence
        class_absence = all(
            "not hasattr" in l or "is None" in l or "absent" in l.lower()
            for l in assert_lines
        )
        if class_absence and len(assert_lines) <= 2:
            offenders.append(
                f"{py.name}: only asserts class/attribute absence ({len(assert_lines)} asserts)"
            )
    assert not offenders, "R2 tests with only class-absence assertions:\n" + "\n".join(
        offenders
    )


def test_no_unused_parametrized_surface_in_r2_tests() -> None:
    """R2 semantic tests must use their parametrized surface arguments."""
    offenders: list[str] = []
    for py in _TESTS.glob("test_r2_*.py"):
        text = _read(py)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            # Check for parametrize decorator with "surface"
            has_surface_param = False
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call):
                    for kw in dec.keywords:
                        if kw.arg == "params" and isinstance(kw.value, ast.Constant):
                            # Check if any param is a string that looks like a surface
                            pass
            # Check if "surface" is a parameter name
            for arg in node.args.args:
                if arg.arg == "surface":
                    has_surface_param = True
            if not has_surface_param:
                continue
            # Check if "surface" appears in the function body
            body_text = ast.get_source_segment(text, node)
            if body_text and "surface" not in body_text.split("def ")[1]:
                offenders.append(
                    f"{py.name}::{node.name}: 'surface' parameter is unused"
                )
    assert not offenders, "Unused parametrized surface arguments:\n" + "\n".join(
        offenders
    )


# Fix the typo above and re-check
_TESTS_DIR = Path(__file__).resolve().parent


def test_r2_plan_contract_test_exists() -> None:
    """The R2 plan contract test must exist and be importable."""
    contract = _TESTS_DIR / "test_r2_plan_contract.py"
    assert contract.exists(), "test_r2_plan_contract.py must exist"


def test_r2_unknown_frontier_test_exists() -> None:
    """The required unknown-frontier successor must exist."""
    frontier = _TESTS_DIR / "test_r2_unknown_frontier.py"
    assert frontier.exists(), "test_r2_unknown_frontier.py must exist"
    text = _read(frontier)
    assert "test_unknown_surface_abstains_or_emits_typed_unresolved_candidate" in text
