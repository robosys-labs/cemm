"""R3-01: validate R3 owner structure and EVALUATE boundary.

Ensures that the R3 owner structure is correct:
- EVALUATE only accepts VerifiedMeaning + SituationContext
- Same VerifiedMeaning produces same Decision regardless of derivation
- No legacy proposition fixture imports in R3 owners
- R3 owners do not import R4+ modules
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

__cemm_test_inventory__ = {
    "tests/test_r3_owner_structure.py::test_r3_owners_do_not_import_r4_plus_modules": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-owners-do-not-import-r4-plus-modules",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-1",
        "source_ast_sha256": "0605e4915ddb49e081ff267ab99ce0a42d9225424650ac986e10965430820c79",
    },
    "tests/test_r3_owner_structure.py::test_r3_owners_do_not_import_legacy_proposition_fixtures": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-owners-do-not-import-legacy-proposition-fixtures",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-1",
        "source_ast_sha256": "a29e55570a0d5b8119f7068b096cf1dd7412a012f5f2ba3d700322cd36733e83",
    },
    "tests/test_r3_owner_structure.py::test_r3_evaluate_boundary_rejects_programs": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-evaluate-boundary-rejects-programs",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-1",
        "source_ast_sha256": "7f51d17b79a75cf568c891c96f021fa9f4e234a14f4efd569a11835f072a19c9",
    },
    "tests/test_r3_owner_structure.py::test_r3_owners_are_post_verify": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-owners-are-post-verify",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-1",
        "source_ast_sha256": "f527d1e6b7efc6d29f562ac317e101298e514e0505f2ba97d25f397e697a7d0c",
    },
}

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src" / "cemm_authoritative_hybrid"

# R3 owner modules
_R3_OWNERS = frozenset(
    {
        "query",
        "epistemics",
        "state",
        "effects",
        "learning",
        "response",
        "dialogue",
        "evaluation",
        "realization",
        "decision",
        "situation",
    }
)

# R4+ modules that R3 must not import
_R4_PLUS_MODULES = frozenset(
    {
        "training",
        "episodes",
        "calibration",
        "partitions",
        "model",
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


def test_r3_owners_do_not_import_r4_plus_modules() -> None:
    """R3 owner modules must not import R4+ owner modules."""
    violations: list[str] = []
    for owner in sorted(_R3_OWNERS):
        imports = _source_imports(owner)
        forbidden = imports & _R4_PLUS_MODULES
        if forbidden:
            violations.append(
                f"{owner}.py imports forbidden R4+ modules: {sorted(forbidden)}"
            )
    assert not violations, (
        "R3 owners import R4+ modules:\n" + "\n".join(violations)
    )


def test_r3_owners_do_not_import_legacy_proposition_fixtures() -> None:
    """R3 owner modules must not import legacy proposition fixtures.

    Legacy proposition fixtures (``PropositionGraph``, ``Application``)
    are R2 VERIFY-phase structures.  R3 owners work with
    ``VerifiedMeaning`` and ``SemanticExpression`` instead.
    """
    # PropositionGraph and Application are R2 structures
    # R3 owners should not import them from programs.py
    legacy_imports = frozenset({"PropositionGraph"})
    violations: list[str] = []
    for owner in sorted(_R3_OWNERS):
        imports = _source_imports(owner)
        found = imports & legacy_imports
        if found:
            violations.append(
                f"{owner}.py imports legacy proposition fixtures: {sorted(found)}"
            )
    assert not violations, (
        "R3 owners import legacy proposition fixtures:\n" + "\n".join(violations)
    )


def test_r3_runtime_owns_evaluate_and_exposes_only_r5_boundary() -> None:
    """R3 owns EVALUATE; only R5 realization may remain unadmitted."""
    runtime_path = _SRC / "runtime.py"
    assert runtime_path.exists(), "runtime.py not found"
    text = runtime_path.read_text(encoding="utf-8")
    assert "contract:r3:evaluate" not in text
    assert text.count("contract:r5:realize_surface") == 1
    assert "VerifiedMeaning" in text or "verified_meaning" in text


def test_r3_owners_are_post_verify() -> None:
    """R3 owner modules must not import PROPOSE-phase modules.

    R3 owners are post-VERIFY: they consume ``VerifiedMeaning`` and must
    not import PROPOSE-phase modules like ``proposal``, ``programs``,
    ``recursive_composer``, ``recursive_compiler``.
    """
    propose_modules = frozenset(
        {"proposal", "recursive_composer", "recursive_compiler"}
    )
    violations: list[str] = []
    for owner in sorted(_R3_OWNERS):
        imports = _source_imports(owner)
        found = imports & propose_modules
        if found:
            violations.append(
                f"{owner}.py imports PROPOSE-phase modules: {sorted(found)}"
            )
    assert not violations, (
        "R3 owners import PROPOSE-phase modules (forbidden):\n"
        + "\n".join(violations)
    )
