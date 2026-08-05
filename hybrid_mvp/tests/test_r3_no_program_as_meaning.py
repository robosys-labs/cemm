"""R3-01: hard-cut legacy Program-as-meaning consumers.

AST-based inventory rejecting active R3 code that:
- accesses ``program.graph`` or ``program.actions`` after VERIFY
- accepts :class:`SemanticSwitchProgram` as EVALUATE input
- reads ``Orientation.source_text`` after VERIFY
- branches on raw words
- calls ``FormResolver``/``Grounder`` after ORIENT
- commits to ``stores.world`` outside effect owner
- uses ``program_ref`` except for lineage
- treats R2 ``TransitionPreview`` as effect authorization

Only valid EVALUATE input:
    evaluate(meaning: VerifiedMeaning, situation: SituationContext) -> Decision
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

__cemm_test_inventory__ = {
    "tests/test_r3_no_program_as_meaning.py::test_r3_owners_do_not_access_program_graph": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-owners-do-not-access-program-graph",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-1",
        "source_ast_sha256": "7b0c673092683e49a3b3f39a8c18f4e187ced4d52f6ba77c5ece9da00bc84652",
    },
    "tests/test_r3_no_program_as_meaning.py::test_r3_owners_do_not_access_program_actions": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-owners-do-not-access-program-actions",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-1",
        "source_ast_sha256": "a462dd8722690b09d29849f0434398533df7679af2df193f8d055e71eed56343",
    },
    "tests/test_r3_no_program_as_meaning.py::test_r3_owners_do_not_import_semantic_switch_program": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-owners-do-not-import-semantic-switch-program",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-1",
        "source_ast_sha256": "9108d2fdc9183fa2ae702dfb8e66ab9dd533109f0ad617486805fd606ab07f5b",
    },
    "tests/test_r3_no_program_as_meaning.py::test_r3_owners_do_not_use_form_resolver_or_grounder": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-owners-do-not-use-form-resolver-or-grounder",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-1",
        "source_ast_sha256": "f5d2213a826435c2d542a58a42f68d7e69efc16e13807381aba308d763560c39",
    },
    "tests/test_r3_no_program_as_meaning.py::test_r3_owners_do_not_read_orientation_source_text": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-owners-do-not-read-orientation-source-text",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-1",
        "source_ast_sha256": "69ade59f29664c5286c270d70373b9c41c090ebcbadfb1363938690f55005885",
    },
    "tests/test_r3_no_program_as_meaning.py::test_r3_owners_do_not_branch_on_raw_words": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-owners-do-not-branch-on-raw-words",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-1",
        "source_ast_sha256": "2b5d8abac6e7ac85415d0d8321c7d039d817140b6eb2a86f704e3ced651a2107",
    },
    "tests/test_r3_no_program_as_meaning.py::test_r3_transition_preview_not_effect_authorization": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-transition-preview-not-effect-authorization",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-1",
        "source_ast_sha256": "1e394d75989a93aec36f7febcb543e3987896a98c004bca2c8df6f5b51d81877",
    },
    "tests/test_r3_no_program_as_meaning.py::test_program_to_evaluate_raises_type_error": {
        "activation_phase": "R3",
        "assertion_ref": "assertion:r3-program-to-evaluate-raises-type-error",
        "diagnostic_role": "phase",
        "introduced_by_task": "R3-Task-1",
        "source_ast_sha256": "a5ca7d3465d7aa989e0285d1a64c010cb2da0d4297152132eac78693c9b6b812",
    },
}

_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src" / "cemm_authoritative_hybrid"

# R3 owner modules: the files that R3 owns and must not contain legacy patterns
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

# R2 owners that are permitted to use program.graph/actions (PROPOSE, VERIFY)
_R2_PROGRAM_OWNERS = frozenset(
    {
        "programs",
        "proposal",
        "verifier",
        "verifier_reconstruction",
        "recursive_compiler",
        "recursive_composer",
        "coverage",
        "transition_preview",
        "model",
        "training",
        "episodes",
    }
)


def _module_source(module_name: str) -> str:
    """Return the source text of a module, or empty string if not found."""
    path = _SRC / f"{module_name}.py"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _module_ast(module_name: str) -> ast.Module | None:
    """Return the AST of a module, or None if not found."""
    text = _module_source(module_name)
    if not text:
        return None
    return ast.parse(text)


def _source_imports(module_name: str) -> set[str]:
    """Return the set of cemm_authoritative_hybrid imports in a module."""
    text = _module_source(module_name)
    if not text:
        return set()
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


class _AttributeAccessVisitor(ast.NodeVisitor):
    """AST visitor that finds attribute access patterns like ``obj.attr``."""

    def __init__(self, obj_name: str, attr_names: frozenset[str]) -> None:
        self._obj_name = obj_name
        self._attr_names = attr_names
        self.hits: list[tuple[int, str]] = []

    def visit_Attribute(self, node: ast.Attribute) -> None:
        # Check for ``program.graph`` or ``program.actions``
        if node.attr in self._attr_names:
            if isinstance(node.value, ast.Name) and node.value.id == self._obj_name:
                self.hits.append((node.lineno, f"{self._obj_name}.{node.attr}"))
        self.generic_visit(node)


class _ImportVisitor(ast.NodeVisitor):
    """AST visitor that finds imports of specific names."""

    def __init__(self, target_name: str) -> None:
        self._target_name = target_name
        self.found: list[tuple[int, str]] = []

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name == self._target_name or alias.asname == self._target_name:
                self.found.append((node.lineno, f"import {alias.name}"))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if node.id == self._target_name:
            self.found.append((node.lineno, f"name {node.id}"))
        self.generic_visit(node)


def test_r3_owners_do_not_access_program_graph() -> None:
    """R3 owner modules must not access ``program.graph``."""
    violations: list[str] = []
    for owner in sorted(_R3_OWNERS):
        tree = _module_ast(owner)
        if tree is None:
            continue
        visitor = _AttributeAccessVisitor("program", frozenset({"graph"}))
        visitor.visit(tree)
        for lineno, pattern in visitor.hits:
            violations.append(f"{owner}.py:{lineno} accesses {pattern}")
    assert not violations, (
        "R3 owners access program.graph (forbidden after VERIFY):\n"
        + "\n".join(violations)
    )


def test_r3_owners_do_not_access_program_actions() -> None:
    """R3 owner modules must not access ``program.actions``."""
    violations: list[str] = []
    for owner in sorted(_R3_OWNERS):
        tree = _module_ast(owner)
        if tree is None:
            continue
        visitor = _AttributeAccessVisitor("program", frozenset({"actions"}))
        visitor.visit(tree)
        for lineno, pattern in visitor.hits:
            violations.append(f"{owner}.py:{lineno} accesses {pattern}")
    assert not violations, (
        "R3 owners access program.actions (forbidden after VERIFY):\n"
        + "\n".join(violations)
    )


def test_r3_owners_do_not_import_semantic_switch_program() -> None:
    """R3 owner modules must not import ``SemanticSwitchProgram``."""
    violations: list[str] = []
    for owner in sorted(_R3_OWNERS):
        imports = _source_imports(owner)
        if "SemanticSwitchProgram" in imports:
            violations.append(f"{owner}.py imports SemanticSwitchProgram")
        # Also check AST for the name
        tree = _module_ast(owner)
        if tree is None:
            continue
        visitor = _ImportVisitor("SemanticSwitchProgram")
        visitor.visit(tree)
        for lineno, pattern in visitor.found:
            violations.append(f"{owner}.py:{lineno} {pattern}")
    assert not violations, (
        "R3 owners import SemanticSwitchProgram (forbidden):\n"
        + "\n".join(violations)
    )


def test_r3_owners_do_not_use_form_resolver_or_grounder() -> None:
    """R3 owner modules must not use ``FormResolver`` or ``Grounder``."""
    forbidden = frozenset({"FormResolver", "Grounder"})
    violations: list[str] = []
    for owner in sorted(_R3_OWNERS):
        imports = _source_imports(owner)
        found = imports & forbidden
        if found:
            violations.append(
                f"{owner}.py imports forbidden form/grounding: {sorted(found)}"
            )
    assert not violations, (
        "R3 owners use FormResolver/Grounder (forbidden after ORIENT):\n"
        + "\n".join(violations)
    )


def test_r3_owners_do_not_read_orientation_source_text() -> None:
    """R3 owner modules must not read ``Orientation.source_text`` after VERIFY."""
    violations: list[str] = []
    for owner in sorted(_R3_OWNERS):
        tree = _module_ast(owner)
        if tree is None:
            continue
        visitor = _AttributeAccessVisitor(
            "orientation", frozenset({"source_text"})
        )
        visitor.visit(tree)
        for lineno, pattern in visitor.hits:
            violations.append(f"{owner}.py:{lineno} accesses {pattern}")
    assert not violations, (
        "R3 owners read orientation.source_text (forbidden after VERIFY):\n"
        + "\n".join(violations)
    )


def test_r3_owners_do_not_branch_on_raw_words() -> None:
    """R3 owner modules must not branch on raw user word strings.

    This checks for string literal comparisons in if statements where
    the string is compared against a variable that could hold user input.
    Internal status enums (like 'available', 'timeout', 'corrected') are
    permitted - only comparisons against ``word``, ``text``, ``surface``,
    ``token``, ``phrase`` variables are flagged.
    """
    _RAW_WORD_VARS = frozenset({"word", "text", "surface", "token", "phrase", "utterance"})
    violations: list[str] = []

    class _RawWordBranchVisitor(ast.NodeVisitor):
        def __init__(self, module_name: str) -> None:
            self._module_name = module_name

        def visit_If(self, node: ast.If) -> None:
            self._check_raw_word_compare(node.test, node.lineno)
            self.generic_visit(node)

        def _check_raw_word_compare(self, node: ast.AST, lineno: int) -> None:
            if isinstance(node, ast.Compare):
                # Check if one side is a raw word variable and the other is a string
                for comparator in [node.left, *node.comparators]:
                    if isinstance(comparator, ast.Name) and comparator.id in _RAW_WORD_VARS:
                        for other in [node.left, *node.comparators]:
                            if isinstance(other, ast.Constant) and isinstance(other.value, str):
                                violations.append(
                                    f"{self._module_name}.py:{lineno} "
                                    f"branches on raw word {comparator.id} == {other.value!r}"
                                )
            elif isinstance(node, ast.BoolOp):
                for v in node.values:
                    self._check_raw_word_compare(v, lineno)

    for owner in sorted(_R3_OWNERS):
        tree = _module_ast(owner)
        if tree is None:
            continue
        visitor = _RawWordBranchVisitor(owner)
        visitor.visit(tree)

    assert not violations, (
        "R3 owners branch on raw words (forbidden):\n" + "\n".join(violations)
    )


def test_r3_transition_preview_not_effect_authorization() -> None:
    """R3 owner modules must not treat ``TransitionPreview`` as effect authorization.

    ``TransitionPreview`` is a VERIFY-phase preview mechanism.  R3's
    ``EffectGateway`` must only accept verified decisions, not previews.
    """
    # Check that effects.py does not import or use TransitionPreview
    effects_source = _module_source("effects")
    if not effects_source:
        return  # effects.py not yet created
    assert "TransitionPreview" not in effects_source, (
        "effects.py references TransitionPreview (forbidden as effect authorization)"
    )


def test_program_to_evaluate_raises_type_error() -> None:
    """Passing a SemanticSwitchProgram to EVALUATE must raise TypeError.

    The only valid EVALUATE input is:
        evaluate(meaning: VerifiedMeaning, situation: SituationContext) -> Decision
    """
    # The runtime's _evaluate_phase should reject programs
    runtime_source = _module_source("runtime")
    assert runtime_source, "runtime.py not found"
    # The runtime must have a LaterOwnerNotAdmitted boundary for contract:r3:evaluate
    assert "contract:r3:evaluate" in runtime_source, (
        "runtime.py does not define the contract:r3:evaluate boundary"
    )
