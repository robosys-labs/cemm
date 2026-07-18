"""Static architecture prohibitions for the canonical v3.5 implementation.

The scanner intentionally targets ``cemm/v350`` only.  The retained v3.4.7
migration baseline and archived contracts are evidence to migrate, not v3.5
code, and therefore are not linted as if they were already authoritative.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable


@dataclass(frozen=True, slots=True)
class ArchitectureViolation:
    path: Path
    line: int
    code: str
    message: str

    def render(self, root: Path | None = None) -> str:
        shown = self.path
        if root is not None:
            try:
                shown = self.path.relative_to(root)
            except ValueError:
                pass
        return f"{shown}:{self.line}: {self.code}: {self.message}"


_FORBIDDEN_ONTOLOGY_ENUM_NAMES = frozenset(
    {"ReferentKind", "ReferentType", "EntityType", "SemanticEntityKind"}
)
_SURFACE_NAMES = frozenset(
    {"token", "tokens", "word", "words", "text", "surface", "utterance", "normalized"}
)
_TARGETLESS_ACKNOWLEDGEMENTS = frozenset({"understood"})
_NAMED_SEMANTIC_REF = re.compile(
    r"^(?:type|facet|event|action|property|state|relation|role|function|operator|"
    r"discourse-act|discourse-relation|response-policy):[^:]+(?:[:][^:]+)*$"
)
_SEMANTIC_AUTHORITY_PACKAGES = frozenset({"grounding", "composition", "epistemics"})
_EVENT_MUTATION_NAME = re.compile(
    r"(?:mutate|apply|commit|update|set|handle|on).*(?:death|die|died)|"
    r"(?:death|die|died).*(?:mutate|apply|commit|update|set|handle)",
    re.IGNORECASE,
)


def scan_tree(root: Path) -> tuple[ArchitectureViolation, ...]:
    root = root.resolve()
    violations: list[ArchitectureViolation] = []
    for path in sorted(root.rglob("*.py")):
        if _excluded(path, root):
            continue
        violations.extend(scan_file(path))
    violations.sort(key=lambda item: (str(item.path), item.line, item.code))
    return tuple(violations)


def scan_file(path: Path) -> tuple[ArchitectureViolation, ...]:
    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return (
            ArchitectureViolation(
                path,
                exc.lineno or 1,
                "syntax_error",
                exc.msg,
            ),
        )
    visitor = _Visitor(path, source)
    visitor.visit(tree)
    return tuple(visitor.violations)


def require_clean(root: Path) -> None:
    violations = scan_tree(root)
    if violations:
        detail = "\n".join(item.render(root) for item in violations)
        raise RuntimeError(f"v3.5 architecture lint failed:\n{detail}")


def _excluded(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if path.name == "architecture_lint.py":
        return True
    if "__pycache__" in relative.parts:
        return True
    # Language packages may contain language-specific surface and grammar data.
    return any(part.casefold().startswith("language") for part in relative.parts)


class _Visitor(ast.NodeVisitor):
    def __init__(self, path: Path, source: str) -> None:
        self.path = path
        self.source = source
        self.violations: list[ArchitectureViolation] = []
        self._docstring_nodes = _docstring_nodes(ast.parse(source))

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name == "cemm.v347" or alias.name.startswith("cemm.v347."):
                self._add(node, "v347_dependency", "v3.5 code imports the v3.4.7 authority")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        if module == "cemm.v347" or module.startswith("cemm.v347."):
            self._add(node, "v347_dependency", "v3.5 code imports the v3.4.7 authority")
        if module == "cemm" and any(alias.name == "v347" for alias in node.names):
            self._add(node, "v347_dependency", "v3.5 code imports the v3.4.7 authority")
        if node.level and module.startswith("v347"):
            self._add(node, "v347_dependency", "v3.5 code imports the v3.4.7 authority")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        dotted = _dotted_name(node)
        if dotted == "cemm.v347" or dotted.startswith("cemm.v347."):
            self._add(node, "v347_dependency", "v3.5 code references the v3.4.7 authority")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if node.name in _FORBIDDEN_ONTOLOGY_ENUM_NAMES and _is_enum_class(node):
            self._add(
                node,
                "learned_type_enum",
                f"{node.name} would make learned semantic types source-code-bound",
            )
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        if node.arg == "negative":
            self._add(
                node,
                "generic_negative_axis",
                "use polarity, decrease, loss, deactivation, prohibition, valence, or importance",
            )
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.target, ast.Name) and node.target.id == "negative":
            self._add(
                node,
                "generic_negative_axis",
                "a generic negative field collapses orthogonal semantic axes",
            )
        if (
            _response_path(self.path)
            and isinstance(node.target, ast.Name)
            and _template_name(node.target.id)
            and _long_string(node.value)
        ):
            self._add(
                node,
                "full_sentence_response_template",
                "ordinary response realization must be grammar-driven, not a sentence template",
            )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "negative":
                self._add(
                    node,
                    "generic_negative_axis",
                    "a generic negative field collapses orthogonal semantic axes",
                )
            if (
                _response_path(self.path)
                and isinstance(target, ast.Name)
                and _template_name(target.id)
                and _long_string(node.value)
            ):
                self._add(
                    node,
                    "full_sentence_response_template",
                    "ordinary response realization must be grammar-driven, not a sentence template",
                )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if _EVENT_MUTATION_NAME.search(node.name):
            self._add(
                node,
                "event_specific_mutation",
                "event effects must use generic transition contracts and proof-bearing deltas",
            )
        if _semantic_authority_path(self.path):
            positional = (*node.args.posonlyargs, *node.args.args)
            if node.args.defaults:
                for arg, default in zip(positional[-len(node.args.defaults):], node.args.defaults):
                    if (
                        arg.arg == "context_ref"
                        and isinstance(default, ast.Constant)
                        and default.value == "actual"
                    ):
                        self._add(
                            default,
                            "implicit_actual_context_default",
                            "grounding/composition/epistemic context must be cycle-pinned explicitly, not defaulted to the actual world",
                        )
            for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
                if (
                    arg.arg == "context_ref"
                    and isinstance(default, ast.Constant)
                    and default.value == "actual"
                ):
                    self._add(
                        default,
                        "implicit_actual_context_default",
                        "grounding/composition/epistemic context must be cycle-pinned explicitly, not defaulted to the actual world",
                    )
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Compare(self, node: ast.Compare) -> None:
        operands = (node.left, *node.comparators)
        has_surface_operand = any(_surface_expression(item) for item in operands)
        literal_values = tuple(
            value for operand in operands for value in _string_literals(operand)
        )
        if has_surface_operand and literal_values:
            self._add(
                node,
                "kernel_surface_word_branch",
                "kernel semantics branch on a language surface string; move form knowledge to a language module",
            )
        if (
            any(_semantic_schema_ref_expression(item) for item in operands)
            and any(value.startswith(("event:", "action:")) for value in literal_values)
        ):
            self._add(
                node,
                "event_specific_semantic_branch",
                "event/action behavior must be selected by schema contracts, not a named schema branch",
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"startswith", "endswith"}
            and _surface_expression(node.func.value)
            and any(_string_literals(arg) for arg in node.args)
        ):
            self._add(
                node,
                "kernel_surface_word_branch",
                "kernel semantics branch on a language surface prefix/suffix",
            )
        for keyword in node.keywords:
            if (
                keyword.arg in {"target_ref", "target_refs", "target_proposition_refs"}
                and _empty_semantic_target(keyword.value)
                and _response_or_goal_path(self.path)
            ):
                self._add(
                    keyword.value,
                    "targetless_response_goal",
                    "response goals and acknowledgements require an explicit semantic target",
                )
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        if _response_path(self.path) and _long_string(node.value):
            self._add(
                node,
                "full_sentence_response_template",
                "ordinary response realization must be grammar-driven, not a sentence template",
            )
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        if _response_path(self.path):
            for key, value in zip(node.keys, node.values):
                if (
                    isinstance(key, ast.Constant)
                    and isinstance(key.value, str)
                    and _template_name(key.value)
                    and _long_string(value)
                ):
                    self._add(
                        value,
                        "full_sentence_response_template",
                        "ordinary response realization must be grammar-driven, not a sentence template",
                    )
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:
        if not isinstance(node.value, str) or id(node) in self._docstring_nodes:
            return
        if _semantic_authority_path(self.path) and _NAMED_SEMANTIC_REF.match(node.value):
            self._add(
                node,
                "named_semantic_authority_literal",
                "composition/grounding/epistemic kernel code must resolve semantic refs from data, evidence, or exact schema contracts",
            )
        normalized = " ".join(node.value.casefold().split()).strip(".!? ")
        if normalized in _TARGETLESS_ACKNOWLEDGEMENTS:
            self._add(
                node,
                "targetless_acknowledgement",
                "generic acknowledgement text has no semantic target",
            )

    def _add(self, node: ast.AST, code: str, message: str) -> None:
        self.violations.append(
            ArchitectureViolation(self.path, getattr(node, "lineno", 1), code, message)
        )



def _dotted_name(node: ast.AST) -> str:
    parts: list[str] = []
    current: ast.AST | None = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def _string_literals(node: ast.AST) -> tuple[str, ...]:
    return tuple(
        child.value
        for child in ast.walk(node)
        if isinstance(child, ast.Constant) and isinstance(child.value, str)
    )


def _semantic_schema_ref_expression(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id.casefold() in {"event_ref", "event_schema_ref", "action_ref", "action_schema_ref", "schema_ref"}
    if isinstance(node, ast.Attribute):
        return node.attr.casefold() in {"event_ref", "event_schema_ref", "action_ref", "action_schema_ref", "schema_ref"}
    return False


def _empty_semantic_target(node: ast.AST) -> bool:
    return (
        isinstance(node, (ast.Tuple, ast.List, ast.Set)) and not node.elts
    ) or (isinstance(node, ast.Constant) and node.value in {None, ""})

def _is_enum_class(node: ast.ClassDef) -> bool:
    for base in node.bases:
        if isinstance(base, ast.Name) and base.id.endswith("Enum"):
            return True
        if isinstance(base, ast.Attribute) and base.attr.endswith("Enum"):
            return True
    return False


def _surface_expression(node: ast.AST) -> bool:
    if isinstance(node, ast.Name):
        return node.id.casefold() in _SURFACE_NAMES
    if isinstance(node, ast.Attribute):
        return node.attr.casefold() in _SURFACE_NAMES
    if isinstance(node, ast.Call):
        return _surface_expression(node.func) or any(_surface_expression(arg) for arg in node.args)
    return False



def _semantic_authority_path(path: Path) -> bool:
    return any(part.casefold() in _SEMANTIC_AUTHORITY_PACKAGES for part in path.parts)

def _response_path(path: Path) -> bool:
    stem = path.stem.casefold()
    return any(part in stem for part in ("response", "realiz", "nlg"))


def _response_or_goal_path(path: Path) -> bool:
    stem = path.stem.casefold()
    return _response_path(path) or "goal" in stem


def _template_name(value: str) -> bool:
    normalized = value.casefold()
    return any(
        marker in normalized
        for marker in ("template", "fallback", "response", "utterance", "surface")
    )


def _long_string(node: ast.AST | None) -> bool:
    if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
        return False
    return len(" ".join(node.value.split()).split()) >= 5


def _docstring_nodes(tree: ast.AST) -> set[int]:
    result: set[int] = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (
            isinstance(first, ast.Expr)
            and isinstance(first.value, ast.Constant)
            and isinstance(first.value.value, str)
        ):
            result.add(id(first.value))
    return result


def render_violations(
    violations: Iterable[ArchitectureViolation],
    *,
    root: Path | None = None,
) -> str:
    return "\n".join(item.render(root) for item in violations)


@dataclass(frozen=True, slots=True)
class LegacyDebtBudget:
    debt_id: str
    path: str
    pattern: str
    maximum_count: int
    rationale: str = ""


@dataclass(frozen=True, slots=True)
class LegacyDebtFinding:
    debt_id: str
    path: Path
    observed_count: int
    maximum_count: int
    message: str


def load_legacy_debt_budgets(path: Path) -> tuple[LegacyDebtBudget, ...]:
    import json

    payload = json.loads(path.read_text(encoding="utf-8"))
    result = []
    for item in payload.get("budgets", ()):
        result.append(LegacyDebtBudget(
            debt_id=str(item["debt_id"]),
            path=str(item["path"]),
            pattern=str(item["pattern"]),
            maximum_count=int(item["maximum_count"]),
            rationale=str(item.get("rationale", "")),
        ))
    ids = [item.debt_id for item in result]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate legacy debt budget id")
    return tuple(result)


def scan_legacy_debt(
    repository_root: Path,
    manifest_path: Path | None = None,
) -> tuple[LegacyDebtFinding, ...]:
    """Fail only when known v3.4.7 authority debt increases.

    Deleting or reducing a legacy pattern is always allowed. The manifest is a
    ratchet, not an assertion that retained debt is acceptable in v3.5.
    """
    repository_root = repository_root.resolve()
    manifest_path = manifest_path or repository_root / "docs" / "audits" / "v347-authority-debt.json"
    budgets = load_legacy_debt_budgets(manifest_path)
    findings = []
    for budget in budgets:
        path = repository_root / budget.path
        if not path.is_file():
            # Removal is architectural progress and must not fail the ratchet.
            continue
        count = len(re.findall(budget.pattern, path.read_text(encoding="utf-8"), flags=re.MULTILINE | re.DOTALL))
        if count > budget.maximum_count:
            findings.append(LegacyDebtFinding(
                debt_id=budget.debt_id,
                path=path,
                observed_count=count,
                maximum_count=budget.maximum_count,
                message=f"legacy authority debt increased: {count} > {budget.maximum_count}",
            ))
    return tuple(findings)


def require_legacy_debt_not_increased(repository_root: Path) -> None:
    findings = scan_legacy_debt(repository_root)
    if findings:
        detail = "\n".join(
            f"{item.path.relative_to(repository_root)}: {item.debt_id}: {item.message}"
            for item in findings
        )
        raise RuntimeError(f"v3.4.7 authority-debt ratchet failed:\n{detail}")
