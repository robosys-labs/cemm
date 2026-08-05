"""Bounded, stdlib-only test inventory verification for corrective replay.

This module is intentionally outside the runtime package. Source-only
admission loads it by exact file path, scans every test module once, and never
imports pytest, Git helpers, the CEMM runtime, model code, training code, or
Torch.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import tomllib
from types import MappingProxyType
from typing import Callable, Mapping, NoReturn


INVENTORY_SCHEMA = "cemm-hybrid-test-inventory-v1"
PHASES = ("G0", "R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8")
MAX_JSON_BYTES = 64 * 1024 * 1024

PYTEST_COLLECTION_CONTRACT = MappingProxyType(
    {
        "python_files": ("test_*.py", "*_test.py"),
        "python_functions": ("test*",),
        "python_classes": ("Test*",),
    }
)
CLASSIFICATIONS = frozenset({"retained", "rewritten", "historical"})
DIAGNOSTIC_ROLES = frozenset({"owner", "phase", "admission_only"})
REVIEWED_COUNTS = MappingProxyType(
    {
        "file_count": 60,
        "source_test_count": 632,
        "case_count": 743,
        "retained": 609,
        "rewritten": 10,
        "historical": 13,
    }
)

_TOP_FIELDS = frozenset(
    {
        "schema",
        "inventory_ref",
        "baseline_source_ref",
        "source_set_ref",
        "case_set_ref",
        "file_count",
        "source_test_count",
        "case_count",
        "classification_counts",
        "files",
        "source_tests",
    }
)
_FILE_FIELDS = frozenset({"path", "baseline_blob_ref"})
_SOURCE_COMMON_FIELDS = frozenset(
    {
        "source_test_ref",
        "classification",
        "activation_phase",
        "assertion_ref",
        "source_ast_sha256",
        "case_node_ids",
        "successor_node_ids",
    }
)
_HISTORICAL_FIELDS = _SOURCE_COMMON_FIELDS | {"historical_reason"}
_REWRITTEN_FIELDS = _SOURCE_COMMON_FIELDS | {
    "replacement_phase",
    "rewrite_obligations",
}
_OBLIGATION_FIELDS = frozenset(
    {"rewrite_ref", "predecessor_case_node_id", "required_successor_node_ids"}
)
_LATER_REQUIRED_FIELDS = frozenset(
    {
        "assertion_ref",
        "activation_phase",
        "diagnostic_role",
        "introduced_by_task",
        "source_ast_sha256",
    }
)
_LATER_OPTIONAL_FIELDS = frozenset(
    {"owner_ref", "supersedes_node_id", "contributes_to_rewrite_refs"}
)

_COMMIT_RE = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
_SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")
_CONTENT_REF_RE = re.compile(r"[a-z][a-z0-9_-]*:[0-9a-f]{24}\Z")
_ASSERTION_REF_RE = re.compile(r"assertion:[a-z0-9][a-z0-9-]*\Z")
_OWNER_REF_RE = re.compile(r"[a-z][a-z0-9_.:-]*\Z")
_TASK_REF_RE = re.compile(r"[A-Z0-9][A-Za-z0-9._-]*\Z")


class InventoryError(ValueError):
    """Raised when the governed test inventory fails closed."""


@dataclass(frozen=True)
class SourceTestRecord:
    source_test_ref: str
    classification: str
    activation_phase: str | None
    assertion_ref: str
    source_ast_sha256: str
    case_node_ids: tuple[str, ...]
    successor_node_ids: tuple[str, ...]
    replacement_phase: str | None = None
    rewrite_obligations: tuple[Mapping[str, object], ...] = ()
    historical_reason: str | None = None


@dataclass(frozen=True)
class LaterNodeRecord:
    node_id: str
    source_test_ref: str
    assertion_ref: str
    activation_phase: str
    diagnostic_role: str
    introduced_by_task: str
    source_ast_sha256: str
    owner_ref: str | None
    supersedes_node_id: str | None
    contributes_to_rewrite_refs: tuple[str, ...]


@dataclass(frozen=True)
class InventoryResult:
    inventory_ref: str
    baseline_source_ref: str
    active_node_ids: tuple[str, ...]
    collectable_node_ids: tuple[str, ...]
    deferred_rewrite_refs: tuple[str, ...]
    due_rewrite_refs: tuple[str, ...]
    owner_node_ids: Mapping[str, tuple[str, ...]]
    phase_node_ids: tuple[str, ...]
    admission_only_node_ids: tuple[str, ...]
    source_tests: Mapping[str, SourceTestRecord]
    later_nodes: Mapping[str, LaterNodeRecord]
    parsed_module_count: int
    literal_metadata_ref: str
    active_node_set_ref: str
    collectable_node_set_ref: str


@dataclass(frozen=True)
class _ParsedModule:
    relative_path: str
    source_nodes: Mapping[str, ast.FunctionDef | ast.AsyncFunctionDef]
    case_node_ids: Mapping[str, tuple[str, ...]]
    metadata: Mapping[str, Mapping[str, object]]


def _canonical_json_bytes(value: object) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise InventoryError(f"value is not canonical JSON: {exc}") from exc


def content_ref(kind: str, payload: object) -> str:
    """Return a deterministic, human-routable 96-bit content reference."""

    if type(kind) is not str or re.fullmatch(r"[a-z][a-z0-9_-]*", kind) is None:
        raise InventoryError("content-ref kind is invalid")
    digest = hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()
    return f"{kind}:{digest[:24]}"


def _duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise InventoryError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _nonfinite_json(value: str) -> NoReturn:
    raise InventoryError(f"non-finite JSON constant is forbidden: {value}")


def _load_strict_json_bytes(raw: bytes, *, path: Path) -> object:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise InventoryError(f"{path} is not UTF-8 JSON") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_duplicate_keys,
            parse_constant=_nonfinite_json,
        )
    except InventoryError:
        raise
    except (json.JSONDecodeError, ValueError, RecursionError) as exc:
        raise InventoryError(f"invalid JSON in {path}: {exc}") from exc


def load_strict_json(path: Path) -> object:
    try:
        with path.open("rb") as stream:
            raw = stream.read(MAX_JSON_BYTES + 1)
    except OSError as exc:
        raise InventoryError(f"cannot read JSON {path}: {exc}") from exc
    if not raw or len(raw) > MAX_JSON_BYTES:
        raise InventoryError(f"JSON file exceeds its byte bound: {path}")
    return _load_strict_json_bytes(raw, path=path)


def source_ast_sha256(node: ast.AST) -> str:
    """Hash a source test's canonical AST without location attributes."""

    dumped = ast.dump(node, annotate_fields=True, include_attributes=False)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()


def _exact_fields(
    value: object, expected: frozenset[str], *, context: str
) -> Mapping[str, object]:
    if type(value) is not dict:
        raise InventoryError(f"{context} must be an object")
    actual = set(value)
    if actual != expected:
        raise InventoryError(
            f"{context} has non-exact fields; "
            f"missing={sorted(expected - actual)}, extra={sorted(actual - expected)}"
        )
    return value


def _text(value: object, *, context: str) -> str:
    if type(value) is not str or not value.strip() or value != value.strip():
        raise InventoryError(f"{context} must be non-empty canonical text")
    if any(ord(char) < 32 for char in value):
        raise InventoryError(f"{context} contains a control character")
    return value


def _phase(value: object, *, context: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or value not in PHASES:
        raise InventoryError(f"{context} is not a recognized replay phase")
    return value


def _phase_index(value: str) -> int:
    return PHASES.index(value)


def _safe_test_path(value: object, *, context: str) -> str:
    path_text = _text(value, context=context)
    path = PurePosixPath(path_text)
    if (
        path.is_absolute()
        or "\\" in path_text
        or ":" in path_text
        or not path.parts
        or path.parts[0] != "tests"
        or any(part in {"", ".", ".."} for part in path.parts)
        or path.as_posix() != path_text
        or path.suffix != ".py"
    ):
        raise InventoryError(f"{context} is not a safe canonical test path")
    return path_text


def _safe_node_id(value: object, *, context: str, source_only: bool = False) -> str:
    node_id = _text(value, context=context)
    if "::" not in node_id or "\\" in node_id:
        raise InventoryError(f"{context} is not a canonical pytest node ID")
    path_text, *components = node_id.split("::")
    _safe_test_path(path_text, context=f"{context} path")
    if not components or any(not part for part in components):
        raise InventoryError(f"{context} has an empty node component")
    identifier_components = components
    if not source_only and "[" in components[-1]:
        identifier_components = components[:-1] + [components[-1].split("[", 1)[0]]
    if any(re.fullmatch(r"[A-Za-z_]\w*", part) is None for part in identifier_components):
        raise InventoryError(f"{context} has a non-identifier source component")
    if source_only and ("[" in components[-1] or "]" in components[-1]):
        raise InventoryError(f"{context} cannot be a parameter case")
    return node_id



def _string_list(
    value: object,
    *,
    context: str,
    allow_empty: bool,
    item_validator: Callable[[object], str] | None = None,
) -> tuple[str, ...]:
    if type(value) is not list or (not allow_empty and not value):
        qualifier = "" if allow_empty else " non-empty"
        raise InventoryError(f"{context} must be a{qualifier} array")
    result: list[str] = []
    for index, item in enumerate(value):
        if item_validator is None:
            item_text = _text(item, context=f"{context}[{index}]")
        else:
            item_text = item_validator(item)
        result.append(item_text)
    if result != sorted(result) or len(result) != len(set(result)):
        raise InventoryError(f"{context} must be sorted and unique")
    return tuple(result)


def _validate_content_ref(value: object, *, kind: str, context: str) -> str:
    text_value = _text(value, context=context)
    if (
        _CONTENT_REF_RE.fullmatch(text_value) is None
        or not text_value.startswith(kind + ":")
    ):
        raise InventoryError(f"{context} is not a {kind} content ref")
    return text_value


def _exact_int(value: object, expected: int, *, context: str) -> None:
    if type(value) is not int or value != expected:
        raise InventoryError(f"{context} must equal {expected}")


def _case_for_source(value: object, source_ref: str) -> str:
    case = _safe_node_id(value, context=f"case for {source_ref}")
    if case != source_ref and not (
        case.startswith(source_ref + "[") and case.endswith("]")
    ):
        raise InventoryError(f"case {case} is not owned by {source_ref}")
    return case


def _parse_inventory(
    raw: object, *, enforce_reviewed_counts: bool
) -> tuple[
    Mapping[str, object],
    Mapping[str, SourceTestRecord],
    frozenset[str],
    frozenset[str],
]:
    top = _exact_fields(raw, _TOP_FIELDS, context="test inventory")
    if top["schema"] != INVENTORY_SCHEMA:
        raise InventoryError("test inventory has an unknown schema")
    baseline = _text(top["baseline_source_ref"], context="baseline_source_ref")
    if _COMMIT_RE.fullmatch(baseline) is None:
        raise InventoryError("baseline_source_ref is not a full commit ref")

    files_raw = top["files"]
    sources_raw = top["source_tests"]
    if type(files_raw) is not list or type(sources_raw) is not list:
        raise InventoryError("files and source_tests must be arrays")

    file_paths: list[str] = []
    for index, file_raw in enumerate(files_raw):
        record = _exact_fields(file_raw, _FILE_FIELDS, context=f"files[{index}]")
        path = _safe_test_path(record["path"], context=f"files[{index}].path")
        blob_ref = _text(
            record["baseline_blob_ref"], context=f"files[{index}].baseline_blob_ref"
        )
        if _SHA256_RE.fullmatch(blob_ref) is None:
            raise InventoryError(f"files[{index}].baseline_blob_ref is invalid")
        file_paths.append(path)
    if file_paths != sorted(file_paths) or len(file_paths) != len(set(file_paths)):
        raise InventoryError("inventory file paths must be sorted and unique")
    file_path_set = frozenset(file_paths)

    source_records: dict[str, SourceTestRecord] = {}
    all_cases: set[str] = set()
    classifications = {name: 0 for name in sorted(CLASSIFICATIONS)}
    rewrite_refs: set[str] = set()
    for index, source_raw in enumerate(sources_raw):
        if type(source_raw) is not dict:
            raise InventoryError(f"source_tests[{index}] must be an object")
        classification = source_raw.get("classification")
        if type(classification) is not str or classification not in CLASSIFICATIONS:
            raise InventoryError(
                f"source_tests[{index}] has an invalid classification"
            )
        expected_fields = (
            _SOURCE_COMMON_FIELDS
            if classification == "retained"
            else _REWRITTEN_FIELDS
            if classification == "rewritten"
            else _HISTORICAL_FIELDS
        )
        record = _exact_fields(
            source_raw, expected_fields, context=f"source_tests[{index}]"
        )
        source_ref = _safe_node_id(
            record["source_test_ref"],
            context=f"source_tests[{index}].source_test_ref",
            source_only=True,
        )
        source_path = source_ref.split("::", 1)[0]
        if source_path not in file_path_set:
            raise InventoryError(f"{source_ref} is not owned by an inventoried file")
        if source_ref in source_records:
            raise InventoryError(f"duplicate source_test_ref: {source_ref}")

        assertion_ref = _text(
            record["assertion_ref"], context=f"{source_ref}.assertion_ref"
        )
        if _ASSERTION_REF_RE.fullmatch(assertion_ref) is None:
            raise InventoryError(f"{source_ref} has an invalid assertion_ref")
        digest = _text(
            record["source_ast_sha256"], context=f"{source_ref}.source_ast_sha256"
        )
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise InventoryError(f"{source_ref} has an invalid source_ast_sha256")
        cases = _string_list(
            record["case_node_ids"],
            context=f"{source_ref}.case_node_ids",
            allow_empty=False,
            item_validator=lambda value, sr=source_ref: _case_for_source(value, sr),
        )
        duplicate_cases = all_cases.intersection(cases)
        if duplicate_cases:
            raise InventoryError(
                f"duplicate predecessor case ownership: {sorted(duplicate_cases)}"
            )
        all_cases.update(cases)
        successors = _string_list(
            record["successor_node_ids"],
            context=f"{source_ref}.successor_node_ids",
            allow_empty=True,
            item_validator=lambda value: _safe_node_id(
                value, context="successor_node_id"
            ),
        )

        activation = _phase(
            record["activation_phase"],
            context=f"{source_ref}.activation_phase",
            nullable=True,
        )
        replacement_phase: str | None = None
        obligations: tuple[Mapping[str, object], ...] = ()
        historical_reason: str | None = None
        if classification == "retained":
            if activation is None or successors:
                raise InventoryError(
                    f"retained source {source_ref} needs activation and no "
                    "rewrite successors"
                )
        elif classification == "historical":
            if activation is not None or successors:
                raise InventoryError(
                    f"historical source {source_ref} cannot activate or "
                    "declare successors"
                )
            historical_reason = _text(
                record["historical_reason"],
                context=f"{source_ref}.historical_reason",
            )
        else:
            if activation is not None:
                raise InventoryError(f"rewritten source {source_ref} cannot activate")
            replacement_phase = _phase(
                record["replacement_phase"],
                context=f"{source_ref}.replacement_phase",
            )
            if type(record["rewrite_obligations"]) is not list:
                raise InventoryError(
                    f"{source_ref}.rewrite_obligations must be an array"
                )
            parsed_obligations: list[Mapping[str, object]] = []
            mapped_cases: set[str] = set()
            successor_union: set[str] = set()
            for obligation_index, obligation_raw in enumerate(
                record["rewrite_obligations"]
            ):
                obligation = _exact_fields(
                    obligation_raw,
                    _OBLIGATION_FIELDS,
                    context=(
                        f"{source_ref}.rewrite_obligations[{obligation_index}]"
                    ),
                )
                predecessor = _case_for_source(
                    obligation["predecessor_case_node_id"], source_ref
                )
                if predecessor not in cases or predecessor in mapped_cases:
                    raise InventoryError(
                        f"{source_ref} has duplicate or unknown rewrite "
                        f"predecessor {predecessor}"
                    )
                required = _string_list(
                    obligation["required_successor_node_ids"],
                    context=f"rewrite successors for {predecessor}",
                    allow_empty=False,
                    item_validator=lambda value: _safe_node_id(
                        value, context="required_successor_node_id"
                    ),
                )
                expected_ref = content_ref(
                    "rewrite_obligation",
                    {
                        "predecessor_case_node_id": predecessor,
                        "required_successor_node_ids": list(required),
                    },
                )
                actual_ref = _validate_content_ref(
                    obligation["rewrite_ref"],
                    kind="rewrite_obligation",
                    context=f"rewrite ref for {predecessor}",
                )
                if actual_ref != expected_ref:
                    raise InventoryError(
                        f"rewrite obligation identity mismatch for {predecessor}"
                    )
                if actual_ref in rewrite_refs:
                    raise InventoryError(
                        f"duplicate rewrite obligation ref: {actual_ref}"
                    )
                rewrite_refs.add(actual_ref)
                mapped_cases.add(predecessor)
                successor_union.update(required)
                parsed_obligations.append(
                    MappingProxyType(
                        {
                            "rewrite_ref": actual_ref,
                            "predecessor_case_node_id": predecessor,
                            "required_successor_node_ids": required,
                        }
                    )
                )
            if mapped_cases != set(cases):
                raise InventoryError(
                    f"{source_ref} does not map every predecessor case"
                )
            if tuple(sorted(successor_union)) != successors:
                raise InventoryError(
                    f"{source_ref}.successor_node_ids is not the exact union"
                )
            obligations = tuple(parsed_obligations)

        source_records[source_ref] = SourceTestRecord(
            source_test_ref=source_ref,
            classification=classification,
            activation_phase=activation,
            assertion_ref=assertion_ref,
            source_ast_sha256=digest,
            case_node_ids=cases,
            successor_node_ids=successors,
            replacement_phase=replacement_phase,
            rewrite_obligations=obligations,
            historical_reason=historical_reason,
        )
        classifications[classification] += 1



    if list(source_records) != sorted(source_records):
        raise InventoryError("source_tests must be sorted by source_test_ref")

    _exact_int(top["file_count"], len(file_paths), context="file_count")
    _exact_int(
        top["source_test_count"], len(source_records), context="source_test_count"
    )
    _exact_int(top["case_count"], len(all_cases), context="case_count")
    expected_class_counts = _exact_fields(
        top["classification_counts"],
        frozenset(CLASSIFICATIONS),
        context="classification_counts",
    )
    for name, count in classifications.items():
        _exact_int(
            expected_class_counts[name],
            count,
            context=f"classification_counts.{name}",
        )

    if enforce_reviewed_counts:
        for field in ("file_count", "source_test_count", "case_count"):
            _exact_int(top[field], REVIEWED_COUNTS[field], context=field)
        for name in CLASSIFICATIONS:
            _exact_int(
                expected_class_counts[name],
                REVIEWED_COUNTS[name],
                context=f"classification_counts.{name}",
            )

    source_set_ref = _validate_content_ref(
        top["source_set_ref"], kind="source_set", context="source_set_ref"
    )
    if source_set_ref != content_ref("source_set", sources_raw):
        raise InventoryError("source_set_ref does not match source_tests")
    case_set_ref = _validate_content_ref(
        top["case_set_ref"], kind="case_set", context="case_set_ref"
    )
    if case_set_ref != content_ref("case_set", sorted(all_cases)):
        raise InventoryError("case_set_ref does not match exact predecessor cases")
    inventory_ref = _validate_content_ref(
        top["inventory_ref"], kind="test_inventory", context="inventory_ref"
    )
    identity_payload = dict(top)
    identity_payload.pop("inventory_ref")
    if inventory_ref != content_ref("test_inventory", identity_payload):
        raise InventoryError("inventory_ref does not match the complete inventory")

    return (
        top,
        MappingProxyType(source_records),
        frozenset(all_cases),
        frozenset(rewrite_refs),
    )


class _TopLevelBindingVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.names.add(node.id)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if (
            isinstance(node.ctx, (ast.Store, ast.Del))
            and node.attr == "fixture"
            and isinstance(node.value, ast.Name)
        ):
            self.names.add(node.value.id)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.names.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.names.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.names.add(node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.names.add(alias.asname or alias.name.split(".", 1)[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name != "*":
                self.names.add(alias.asname or alias.name)


def _reject_ambiguous_test_bindings(
    body: list[ast.stmt],
    *,
    path: str,
    class_parts: tuple[str, ...] = (),
) -> None:
    for statement in body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(statement, ast.ClassDef):
            if statement.name.startswith("test"):
                location = "::".join((*class_parts, statement.name))
                raise InventoryError(
                    f"{path} has ambiguous test binding {location}"
                )
            if statement.name.startswith("Test"):
                if statement.bases or statement.keywords or statement.decorator_list:
                    location = "::".join((*class_parts, statement.name))
                    raise InventoryError(
                        f"{path} has inherited or dynamic test class {location}"
                    )
                _reject_ambiguous_test_bindings(
                    statement.body,
                    path=path,
                    class_parts=(*class_parts, statement.name),
                )
            continue
        visitor = _TopLevelBindingVisitor()
        visitor.visit(statement)
        ambiguous = sorted(
            name
            for name in visitor.names
            if name.startswith(("test", "Test"))
        )
        if ambiguous:
            scope = "::".join(class_parts) or "module"
            raise InventoryError(
                f"{path} has ambiguous test binding in {scope}: {ambiguous}"
            )

def _fixture_aliases(tree: ast.Module) -> tuple[frozenset[str], frozenset[str]]:
    module_aliases: set[str] = set()
    function_aliases: set[str] = set()
    other_bindings: set[str] = set()
    fixture_modules = {"pytest", "pytest_asyncio"}
    for statement in tree.body:
        if isinstance(statement, ast.Import):
            for alias in statement.names:
                binding = alias.asname or alias.name.split(".", 1)[0]
                if alias.name in fixture_modules:
                    module_aliases.add(binding)
                else:
                    other_bindings.add(binding)
        elif isinstance(statement, ast.ImportFrom):
            for alias in statement.names:
                if alias.name == "*":
                    continue
                binding = alias.asname or alias.name
                if statement.module in fixture_modules and alias.name == "fixture":
                    function_aliases.add(binding)
                else:
                    other_bindings.add(binding)
        else:
            visitor = _TopLevelBindingVisitor()
            visitor.visit(statement)
            other_bindings.update(visitor.names)
    return (
        frozenset(module_aliases - other_bindings),
        frozenset(function_aliases - other_bindings),
    )


def _is_fixture_source(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    fixture_module_aliases: frozenset[str],
    fixture_function_aliases: frozenset[str],
) -> bool:
    for decorator in node.decorator_list:
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        if (
            isinstance(target, ast.Name)
            and target.id in fixture_function_aliases
        ) or (
            isinstance(target, ast.Attribute)
            and target.attr == "fixture"
            and isinstance(target.value, ast.Name)
            and target.value.id in fixture_module_aliases
        ):
            return True
    return False


def _iter_test_functions(
    body: list[ast.stmt],
    *,
    path: str,
    fixture_module_aliases: frozenset[str],
    fixture_function_aliases: frozenset[str],
    class_parts: tuple[str, ...] = (),
) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    found: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []
    for statement in body:
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if statement.name.startswith("test") and not _is_fixture_source(
                statement,
                fixture_module_aliases=fixture_module_aliases,
                fixture_function_aliases=fixture_function_aliases,
            ):
                components = (*class_parts, statement.name)
                found.append((path + "::" + "::".join(components), statement))
        elif isinstance(statement, ast.ClassDef) and statement.name.startswith("Test"):
            found.extend(
                _iter_test_functions(
                    statement.body,
                    path=path,
                    fixture_module_aliases=fixture_module_aliases,
                    fixture_function_aliases=fixture_function_aliases,
                    class_parts=(*class_parts, statement.name),
                )
            )
    return found

def _is_parametrize_decorator(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "parametrize"
    )


def _literal_case_ids(
    source_ref: str, node: ast.FunctionDef | ast.AsyncFunctionDef
) -> tuple[str, ...]:
    decorators = [
        decorator
        for decorator in node.decorator_list
        if _is_parametrize_decorator(decorator)
    ]
    if not decorators:
        return (source_ref,)
    if len(decorators) != 1:
        raise InventoryError(
            f"later source {source_ref} uses unsupported stacked parametrize"
        )
    call = decorators[0]
    assert isinstance(call, ast.Call)
    if any(isinstance(argument, ast.Starred) for argument in call.args):
        raise InventoryError(
            f"later parameterized source {source_ref} needs literal argvalues"
        )
    argvalue_nodes = (
        ([call.args[1]] if len(call.args) >= 2 else [])
        + [
            keyword.value
            for keyword in call.keywords
            if keyword.arg == "argvalues"
        ]
    )
    if len(argvalue_nodes) != 1 or not isinstance(
        argvalue_nodes[0], (ast.List, ast.Tuple)
    ):
        raise InventoryError(
            f"later parameterized source {source_ref} needs literal argvalues"
        )
    argvalue_node = argvalue_nodes[0]
    assert isinstance(argvalue_node, (ast.List, ast.Tuple))
    if not argvalue_node.elts or any(
        isinstance(item, ast.Starred) for item in argvalue_node.elts
    ):
        raise InventoryError(
            f"later parameterized source {source_ref} needs non-empty literal argvalues"
        )

    ids_nodes = [keyword.value for keyword in call.keywords if keyword.arg == "ids"]
    if len(ids_nodes) != 1:
        raise InventoryError(
            f"later parameterized source {source_ref} needs one literal ids="
        )
    try:
        literal_ids = ast.literal_eval(ids_nodes[0])
    except (ValueError, SyntaxError) as exc:
        raise InventoryError(
            f"later parameterized source {source_ref} has non-literal ids"
        ) from exc
    if type(literal_ids) not in {list, tuple} or not literal_ids:
        raise InventoryError(
            f"later parameterized source {source_ref} ids must be non-empty"
        )
    ids: list[str] = []
    for value in literal_ids:
        item = _text(value, context=f"parametrize id for {source_ref}")
        if re.fullmatch(r"[A-Za-z0-9_.-]+", item) is None:
            raise InventoryError(
                f"parametrize id for {source_ref} must use safe ASCII"
            )
        ids.append(item)
    if len(ids) != len(argvalue_node.elts):
        raise InventoryError(
            f"later parameterized source {source_ref} ids count does not match "
            "literal argvalues"
        )
    if len(ids) != len(set(ids)):
        raise InventoryError(f"later parameterized source {source_ref} has duplicate ids")
    return tuple(f"{source_ref}[{item}]" for item in ids)

def _reject_duplicate_literal_metadata_keys(node: ast.AST, *, path: str) -> None:
    for mapping in (
        candidate for candidate in ast.walk(node) if isinstance(candidate, ast.Dict)
    ):
        seen: set[object] = set()
        for key_node in mapping.keys:
            if key_node is None:
                raise InventoryError(f"{path} metadata cannot use dictionary unpacking")
            try:
                key = ast.literal_eval(key_node)
                hash(key)
            except (TypeError, ValueError, SyntaxError) as exc:
                raise InventoryError(
                    f"{path} metadata dictionary keys must be hashable literals"
                ) from exc
            if key in seen:
                raise InventoryError(
                    f"{path} has a duplicate literal metadata key: {key!r}"
                )
            seen.add(key)

def _literal_metadata(
    tree: ast.Module, *, path: str
) -> Mapping[str, Mapping[str, object]]:
    assignments: list[ast.Assign] = []
    for statement in tree.body:
        if (
            isinstance(statement, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "__cemm_test_inventory__"
                for target in statement.targets
            )
        ):
            assignments.append(statement)
        elif (
            isinstance(statement, ast.AnnAssign)
            and isinstance(statement.target, ast.Name)
            and statement.target.id == "__cemm_test_inventory__"
        ):
            raise InventoryError(
                f"{path} metadata must use one unannotated literal assignment"
            )
    if not assignments:
        return MappingProxyType({})
    if len(assignments) != 1 or len(assignments[0].targets) != 1:
        raise InventoryError(f"{path} must contain exactly one metadata assignment")
    _reject_duplicate_literal_metadata_keys(assignments[0].value, path=path)
    try:
        value = ast.literal_eval(assignments[0].value)
    except (ValueError, SyntaxError) as exc:
        raise InventoryError(f"{path} metadata must be entirely AST-literal") from exc
    if type(value) is not dict:
        raise InventoryError(f"{path} metadata must be a literal mapping")
    result: dict[str, Mapping[str, object]] = {}
    for raw_node_id, raw_metadata in value.items():
        node_id = _safe_node_id(raw_node_id, context=f"{path} metadata key")
        if not node_id.startswith(path + "::"):
            raise InventoryError(f"{node_id} metadata is owned by the wrong module")
        if node_id in result:
            raise InventoryError(f"duplicate literal metadata node: {node_id}")
        if type(raw_metadata) is not dict:
            raise InventoryError(f"metadata for {node_id} must be an object")
        result[node_id] = MappingProxyType(dict(raw_metadata))
    return MappingProxyType(result)


def _verify_pytest_collection_contract(
    root: Path,
    *,
    source_reader: Callable[[Path], bytes] | None = None,
) -> None:
    path = root / "pyproject.toml"
    try:
        raw = path.read_bytes() if source_reader is None else source_reader(path)
        if type(raw) is not bytes:
            raise TypeError("source reader returned non-bytes")
        source = raw.decode("utf-8")
    except (OSError, UnicodeDecodeError, TypeError) as exc:
        raise InventoryError(f"cannot read pytest collection contract {path}: {exc}") from exc
    try:
        document = tomllib.loads(source)
    except tomllib.TOMLDecodeError as exc:
        raise InventoryError(f"invalid pytest collection contract {path}: {exc}") from exc
    try:
        options = document["tool"]["pytest"]["ini_options"]
    except (KeyError, TypeError) as exc:
        raise InventoryError("pyproject.toml lacks the pytest collection contract") from exc
    if type(options) is not dict:
        raise InventoryError("pyproject pytest collection contract must be a table")
    for field, expected in PYTEST_COLLECTION_CONTRACT.items():
        actual = options.get(field)
        if (
            type(actual) is not list
            or any(type(item) is not str for item in actual)
            or tuple(actual) != expected
        ):
            raise InventoryError(
                f"pytest collection contract {field} must equal {list(expected)!r}"
            )

def _read_and_parse_modules(
    root: Path,
    *,
    frozen_source_refs: frozenset[str],
    parse_source: Callable[..., ast.AST],
    source_reader: Callable[[Path], bytes] | None = None,
) -> tuple[Mapping[str, _ParsedModule], int]:
    tests_root = root / "tests"
    if not tests_root.is_dir():
        raise InventoryError(f"test root does not exist: {tests_root}")
    paths_by_relative: dict[str, Path] = {}
    for pattern in ("test_*.py", "*_test.py"):
        for path in tests_root.rglob(pattern):
            if path.is_file():
                relative = path.relative_to(root).as_posix()
                paths_by_relative[relative] = path
    paths = [paths_by_relative[relative] for relative in sorted(paths_by_relative)]
    modules: dict[str, _ParsedModule] = {}
    parse_count = 0
    for path in paths:
        relative = path.relative_to(root).as_posix()
        _safe_test_path(relative, context="current test module")
        try:
            raw = path.read_bytes() if source_reader is None else source_reader(path)
            if type(raw) is not bytes:
                raise TypeError("source reader returned non-bytes")
            source = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError, TypeError) as exc:
            raise InventoryError(f"cannot read test module {relative}: {exc}") from exc
        try:
            tree = parse_source(source, filename=relative)
        except (SyntaxError, TypeError) as exc:
            raise InventoryError(f"cannot parse test module {relative}: {exc}") from exc
        parse_count += 1
        if not isinstance(tree, ast.Module):
            raise InventoryError(f"AST parser returned non-module for {relative}")
        source_nodes: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
        case_ids: dict[str, tuple[str, ...]] = {}
        _reject_ambiguous_test_bindings(tree.body, path=relative)
        fixture_module_aliases, fixture_function_aliases = _fixture_aliases(tree)
        for source_ref, node in _iter_test_functions(
            tree.body,
            path=relative,
            fixture_module_aliases=fixture_module_aliases,
            fixture_function_aliases=fixture_function_aliases,
        ):
            if source_ref in source_nodes:
                raise InventoryError(f"duplicate source test in {relative}: {source_ref}")
            source_nodes[source_ref] = node
            case_ids[source_ref] = (
                ()
                if source_ref in frozen_source_refs
                else _literal_case_ids(source_ref, node)
            )
        modules[relative] = _ParsedModule(
            relative_path=relative,
            source_nodes=MappingProxyType(source_nodes),
            case_node_ids=MappingProxyType(case_ids),
            metadata=_literal_metadata(tree, path=relative),
        )
    return MappingProxyType(modules), parse_count



def _current_sources(
    modules: Mapping[str, _ParsedModule],
) -> tuple[
    Mapping[str, ast.FunctionDef | ast.AsyncFunctionDef],
    Mapping[str, tuple[str, ...]],
    Mapping[str, Mapping[str, object]],
]:
    source_nodes: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    case_ids: dict[str, tuple[str, ...]] = {}
    metadata: dict[str, Mapping[str, object]] = {}
    for module in modules.values():
        for source_ref, node in module.source_nodes.items():
            if source_ref in source_nodes:
                raise InventoryError(f"duplicate current source test: {source_ref}")
            source_nodes[source_ref] = node
            case_ids[source_ref] = module.case_node_ids[source_ref]
        for node_id, record in module.metadata.items():
            if node_id in metadata:
                raise InventoryError(f"duplicate metadata ownership: {node_id}")
            metadata[node_id] = record
    return (
        MappingProxyType(source_nodes),
        MappingProxyType(case_ids),
        MappingProxyType(metadata),
    )


def _source_ref_for_later_case(
    node_id: str, case_ids: Mapping[str, tuple[str, ...]]
) -> str:
    matches = [
        source_ref
        for source_ref, nodes in case_ids.items()
        if node_id in nodes and nodes
    ]
    if len(matches) != 1:
        raise InventoryError(f"metadata node {node_id} has no unique source test")
    return matches[0]


def _validate_later_metadata_record(
    node_id: str,
    source_ref: str,
    raw: Mapping[str, object],
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    known_rewrite_refs: frozenset[str],
) -> LaterNodeRecord:
    fields = set(raw)
    missing = _LATER_REQUIRED_FIELDS - fields
    extra = fields - (_LATER_REQUIRED_FIELDS | _LATER_OPTIONAL_FIELDS)
    if missing or extra:
        raise InventoryError(
            f"metadata for {node_id} has non-exact fields; "
            f"missing={sorted(missing)}, extra={sorted(extra)}"
        )
    assertion_ref = _text(raw["assertion_ref"], context=f"{node_id}.assertion_ref")
    if _ASSERTION_REF_RE.fullmatch(assertion_ref) is None:
        raise InventoryError(f"{node_id} has an invalid assertion_ref")
    activation = _phase(
        raw["activation_phase"], context=f"{node_id}.activation_phase"
    )
    assert activation is not None
    role = _text(raw["diagnostic_role"], context=f"{node_id}.diagnostic_role")
    if role not in DIAGNOSTIC_ROLES:
        raise InventoryError(f"{node_id} has an invalid diagnostic_role")
    task = _text(raw["introduced_by_task"], context=f"{node_id}.introduced_by_task")
    if _TASK_REF_RE.fullmatch(task) is None:
        raise InventoryError(f"{node_id} has an invalid introduced_by_task")

    digest = _text(
        raw["source_ast_sha256"], context=f"{node_id}.source_ast_sha256"
    )
    if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
        raise InventoryError(f"{node_id} has an invalid source_ast_sha256")
    expected_digest = source_ast_sha256(node)
    if digest != expected_digest:
        raise InventoryError(f"same-ID source mutation detected for {node_id}")

    owner_value = raw.get("owner_ref")
    if role == "owner":
        owner_ref = _text(owner_value, context=f"{node_id}.owner_ref")
        if _OWNER_REF_RE.fullmatch(owner_ref) is None:
            raise InventoryError(f"{node_id} has an invalid owner_ref")
    else:
        if "owner_ref" in raw:
            raise InventoryError(
                f"{node_id} can declare owner_ref only with diagnostic_role=owner"
            )
        owner_ref = None

    supersedes_value = raw.get("supersedes_node_id")
    supersedes = (
        None
        if supersedes_value is None
        else _safe_node_id(
            supersedes_value, context=f"{node_id}.supersedes_node_id"
        )
    )
    if "supersedes_node_id" in raw and supersedes is None:
        raise InventoryError(f"{node_id}.supersedes_node_id cannot be null")

    contributes_raw = raw.get("contributes_to_rewrite_refs", [])
    contributes = _string_list(
        contributes_raw,
        context=f"{node_id}.contributes_to_rewrite_refs",
        allow_empty=True,
        item_validator=lambda value: _validate_content_ref(
            value,
            kind="rewrite_obligation",
            context=f"{node_id} contribution",
        ),
    )
    unknown_contributions = set(contributes) - set(known_rewrite_refs)
    if unknown_contributions:
        raise InventoryError(
            f"{node_id} declares unknown rewrite contributions: "
            f"{sorted(unknown_contributions)}"
        )

    return LaterNodeRecord(
        node_id=node_id,
        source_test_ref=source_ref,
        assertion_ref=assertion_ref,
        activation_phase=activation,
        diagnostic_role=role,
        introduced_by_task=task,
        source_ast_sha256=digest,
        owner_ref=owner_ref,
        supersedes_node_id=supersedes,
        contributes_to_rewrite_refs=contributes,
    )


def _validate_current_source(
    modules: Mapping[str, _ParsedModule],
    source_records: Mapping[str, SourceTestRecord],
    predecessor_cases: frozenset[str],
    rewrite_refs: frozenset[str],
) -> tuple[
    Mapping[str, LaterNodeRecord],
    frozenset[str],
    frozenset[str],
    frozenset[str],
]:
    current_sources, case_ids, metadata = _current_sources(modules)
    frozen_source_refs = frozenset(source_records)

    for source_ref, frozen in source_records.items():
        node = current_sources.get(source_ref)
        if node is not None and source_ast_sha256(node) != frozen.source_ast_sha256:
            raise InventoryError(f"same-ID source mutation detected for {source_ref}")

    current_later_nodes: set[str] = set()
    later_source_refs = sorted(set(current_sources) - set(frozen_source_refs))
    for source_ref in later_source_refs:
        current_later_nodes.update(case_ids[source_ref])
    metadata_nodes = set(metadata)
    if metadata_nodes & set(predecessor_cases):
        raise InventoryError(
            "literal metadata cannot redefine frozen predecessor nodes: "
            f"{sorted(metadata_nodes & set(predecessor_cases))}"
        )
    missing_metadata = current_later_nodes - metadata_nodes
    nonexistent_metadata = metadata_nodes - current_later_nodes
    if missing_metadata or nonexistent_metadata:
        raise InventoryError(
            "literal metadata does not exactly describe later cases; "
            f"missing={sorted(missing_metadata)}, "
            f"nonexistent={sorted(nonexistent_metadata)}"
        )

    later_records: dict[str, LaterNodeRecord] = {}
    for node_id in sorted(current_later_nodes):
        source_ref = _source_ref_for_later_case(node_id, case_ids)
        record = _validate_later_metadata_record(
            node_id,
            source_ref,
            metadata[node_id],
            current_sources[source_ref],
            known_rewrite_refs=rewrite_refs,
        )
        later_records[node_id] = record

    executable_frozen: set[str] = set()
    collectable_frozen: set[str] = set()
    for source_ref, frozen in source_records.items():
        if source_ref not in current_sources:
            continue
        collectable_frozen.update(frozen.case_node_ids)
        if frozen.classification == "retained":
            executable_frozen.update(frozen.case_node_ids)
    return (
        MappingProxyType(later_records),
        frozenset(executable_frozen),
        frozenset(current_later_nodes),
        frozenset(collectable_frozen | current_later_nodes),
    )


def _build_lineages(
    source_records: Mapping[str, SourceTestRecord],
    later_records: Mapping[str, LaterNodeRecord],
) -> tuple[
    Mapping[str, str],
    Mapping[str, str],
    Mapping[str, str],
    frozenset[str],
]:
    assertion_by_node: dict[str, str] = {}
    activation_by_node: dict[str, str] = {}
    retained_predecessors: set[str] = set()
    for source in source_records.values():
        if source.classification != "retained":
            continue
        assert source.activation_phase is not None
        for node_id in source.case_node_ids:
            assertion_by_node[node_id] = source.assertion_ref
            activation_by_node[node_id] = source.activation_phase
            retained_predecessors.add(node_id)
    for node_id, record in later_records.items():
        if node_id in assertion_by_node:
            raise InventoryError(f"later node collides with retained node: {node_id}")
        assertion_by_node[node_id] = record.assertion_ref
        activation_by_node[node_id] = record.activation_phase

    successor_by_node: dict[str, str] = {}
    for node_id, record in later_records.items():
        predecessor = record.supersedes_node_id
        if predecessor is None:
            continue
        if predecessor not in assertion_by_node:
            raise InventoryError(
                f"{node_id} supersedes unknown or non-retained node {predecessor}"
            )
        if predecessor == node_id:
            raise InventoryError(f"{node_id} cannot supersede itself")
        if predecessor in successor_by_node:
            raise InventoryError(
                f"lineage branches at {predecessor}: "
                f"{successor_by_node[predecessor]} and {node_id}"
            )
        if assertion_by_node[predecessor] != record.assertion_ref:
            raise InventoryError(
                f"{node_id} does not preserve assertion identity from {predecessor}"
            )
        if _phase_index(record.activation_phase) < _phase_index(
            activation_by_node[predecessor]
        ):
            raise InventoryError(
                f"{node_id} regresses activation phase from {predecessor}"
            )
        successor_by_node[predecessor] = node_id

    state: dict[str, int] = {}

    def visit(node_id: str) -> None:
        marker = state.get(node_id, 0)
        if marker == 1:
            raise InventoryError(f"supersession cycle contains {node_id}")
        if marker == 2:
            return
        state[node_id] = 1
        successor = successor_by_node.get(node_id)
        if successor is not None:
            visit(successor)
        state[node_id] = 2

    for node_id in assertion_by_node:
        visit(node_id)
    return (
        MappingProxyType(assertion_by_node),
        MappingProxyType(activation_by_node),
        MappingProxyType(successor_by_node),
        frozenset(retained_predecessors),
    )


def _leaf_at_phase(
    node_id: str,
    *,
    phase: str,
    activation_by_node: Mapping[str, str],
    successor_by_node: Mapping[str, str],
) -> str:
    current = node_id
    while True:
        successor = successor_by_node.get(current)
        if successor is None:
            return current
        if _phase_index(activation_by_node[successor]) > _phase_index(phase):
            return current
        current = successor



def _select_active_nodes(
    phase: str,
    *,
    activation_by_node: Mapping[str, str],
    successor_by_node: Mapping[str, str],
    executable_nodes: frozenset[str],
) -> tuple[str, ...]:
    successor_nodes = frozenset(successor_by_node.values())
    roots = sorted(set(activation_by_node) - set(successor_nodes))
    active: list[str] = []
    for root in roots:
        if _phase_index(activation_by_node[root]) > _phase_index(phase):
            continue
        leaf = _leaf_at_phase(
            root,
            phase=phase,
            activation_by_node=activation_by_node,
            successor_by_node=successor_by_node,
        )
        if leaf not in executable_nodes:
            raise InventoryError(
                f"active lineage leaf {leaf} has no current executable source"
            )
        active.append(leaf)
    if len(active) != len(set(active)):
        raise InventoryError("active lineage selection produced duplicate leaves")
    return tuple(sorted(active))


def _validate_rewrite_lifecycle(
    phase: str,
    *,
    source_records: Mapping[str, SourceTestRecord],
    later_records: Mapping[str, LaterNodeRecord],
    activation_by_node: Mapping[str, str],
    successor_by_node: Mapping[str, str],
    executable_nodes: frozenset[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    deferred: list[str] = []
    due: list[str] = []
    known_nodes = frozenset(activation_by_node)
    for source in source_records.values():
        if source.classification != "rewritten":
            continue
        assert source.replacement_phase is not None
        is_due = _phase_index(phase) >= _phase_index(source.replacement_phase)
        for obligation in source.rewrite_obligations:
            rewrite_ref = str(obligation["rewrite_ref"])
            if not is_due:
                deferred.append(rewrite_ref)
                continue
            due.append(rewrite_ref)
            required = obligation["required_successor_node_ids"]
            assert isinstance(required, tuple)
            for successor in required:
                if successor not in known_nodes:
                    raise InventoryError(
                        f"due rewrite {rewrite_ref} is missing successor {successor}"
                    )
                if _phase_index(activation_by_node[successor]) > _phase_index(phase):
                    raise InventoryError(
                        f"due rewrite {rewrite_ref} successor {successor} "
                        "is not active"
                    )
                later = later_records.get(successor)
                if (
                    later is not None
                    and rewrite_ref not in later.contributes_to_rewrite_refs
                ):
                    raise InventoryError(
                        f"later successor {successor} does not declare "
                        f"contribution to {rewrite_ref}"
                    )
                leaf = _leaf_at_phase(
                    successor,
                    phase=phase,
                    activation_by_node=activation_by_node,
                    successor_by_node=successor_by_node,
                )
                if leaf not in executable_nodes:
                    raise InventoryError(
                        f"due rewrite {rewrite_ref} resolves to non-executable "
                        f"leaf {leaf}"
                    )
    return tuple(sorted(deferred)), tuple(sorted(due))


def _normalized_later_metadata(
    later_records: Mapping[str, LaterNodeRecord],
) -> list[dict[str, object]]:
    normalized: list[dict[str, object]] = []
    for node_id in sorted(later_records):
        record = later_records[node_id]
        item: dict[str, object] = {
            "node_id": record.node_id,
            "source_test_ref": record.source_test_ref,
            "assertion_ref": record.assertion_ref,
            "activation_phase": record.activation_phase,
            "diagnostic_role": record.diagnostic_role,
            "introduced_by_task": record.introduced_by_task,
            "source_ast_sha256": record.source_ast_sha256,
            "contributes_to_rewrite_refs": list(
                record.contributes_to_rewrite_refs
            ),
        }
        if record.owner_ref is not None:
            item["owner_ref"] = record.owner_ref
        if record.supersedes_node_id is not None:
            item["supersedes_node_id"] = record.supersedes_node_id
        normalized.append(item)
    return normalized


def verify_document_authority_pin(
    root: str | Path,
    inventory_path: str | Path,
    *,
    source_reader: Callable[[Path], bytes] | None = None,
) -> str:
    """Verify the exact inventory bytes pinned by DOCUMENT_AUTHORITY.json."""

    root_path = Path(root).resolve()
    target = _resolve_inside_root(root_path, inventory_path)
    authority_path = root_path / "docs" / "DOCUMENT_AUTHORITY.json"
    if source_reader is None:
        authority = load_strict_json(authority_path)
    else:
        try:
            authority_raw = source_reader(authority_path)
        except OSError as exc:
            raise InventoryError("cannot read DOCUMENT_AUTHORITY.json") from exc
        if type(authority_raw) is not bytes:
            raise InventoryError("source reader returned non-bytes")
        authority = _load_strict_json_bytes(authority_raw, path=authority_path)
    if type(authority) is not dict:
        raise InventoryError("DOCUMENT_AUTHORITY.json must be an object")
    pin = authority.get("test_inventory")
    if type(pin) is not dict or set(pin) != {"path", "sha256"}:
        raise InventoryError("DOCUMENT_AUTHORITY.json lacks an exact test_inventory pin")
    expected_path = _text(pin["path"], context="test_inventory.path")
    if expected_path != target.relative_to(root_path).as_posix():
        raise InventoryError("document-authority test inventory path mismatch")
    expected_digest = _text(pin["sha256"], context="test_inventory.sha256")
    if re.fullmatch(r"[0-9a-f]{64}", expected_digest) is None:
        raise InventoryError("document-authority test inventory digest is invalid")
    try:
        target_raw = target.read_bytes() if source_reader is None else source_reader(target)
    except OSError as exc:
        raise InventoryError("cannot read the pinned test inventory") from exc
    if type(target_raw) is not bytes:
        raise InventoryError("source reader returned non-bytes")
    actual_digest = hashlib.sha256(target_raw).hexdigest()
    if actual_digest != expected_digest:
        raise InventoryError("document-authority test inventory digest mismatch")
    return actual_digest


def _resolve_inside_root(root: Path, path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise InventoryError("inventory path escapes the Hybrid MVP root") from exc
    if not resolved.is_file():
        raise InventoryError(f"inventory path is not a file: {resolved}")
    return resolved


def load_and_verify(
    root: str | Path,
    inventory_path: str | Path,
    *,
    phase: str,
    enforce_reviewed_counts: bool = False,
    expected_sha256: str | None = None,
    parse_source: Callable[..., ast.AST] = ast.parse,
    source_reader: Callable[[Path], bytes] | None = None,
) -> InventoryResult:
    """Load the immutable inventory and verify current source in one AST pass."""

    checked_phase = _phase(phase, context="requested phase")
    assert checked_phase is not None
    root_path = Path(root).resolve()
    _verify_pytest_collection_contract(
        root_path, source_reader=source_reader
    )
    target = _resolve_inside_root(root_path, inventory_path)
    try:
        inventory_bytes = (
            target.read_bytes() if source_reader is None else source_reader(target)
        )
        if type(inventory_bytes) is not bytes:
            raise TypeError("source reader returned non-bytes")
    except (OSError, TypeError) as exc:
        raise InventoryError(f"cannot read inventory {target}: {exc}") from exc
    if expected_sha256 is not None:
        if (
            type(expected_sha256) is not str
            or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None
        ):
            raise InventoryError("expected inventory SHA-256 is invalid")
        if hashlib.sha256(inventory_bytes).hexdigest() != expected_sha256:
            raise InventoryError("loaded inventory bytes do not match authority pin")
    raw = _load_strict_json_bytes(inventory_bytes, path=target)
    top, source_records, predecessor_cases, rewrite_refs = _parse_inventory(
        raw, enforce_reviewed_counts=enforce_reviewed_counts
    )
    modules, parse_count = _read_and_parse_modules(
        root_path,
        frozen_source_refs=frozenset(source_records),
        parse_source=parse_source,
        source_reader=source_reader,
    )
    (
        later_records,
        executable_frozen,
        executable_later,
        collectable_nodes,
    ) = _validate_current_source(
        modules,
        source_records,
        predecessor_cases,
        rewrite_refs,
    )
    (
        _assertion_by_node,
        activation_by_node,
        successor_by_node,
        _retained_predecessors,
    ) = _build_lineages(source_records, later_records)
    executable_nodes = executable_frozen | executable_later
    active = _select_active_nodes(
        checked_phase,
        activation_by_node=activation_by_node,
        successor_by_node=successor_by_node,
        executable_nodes=executable_nodes,
    )
    deferred, due = _validate_rewrite_lifecycle(
        checked_phase,
        source_records=source_records,
        later_records=later_records,
        activation_by_node=activation_by_node,
        successor_by_node=successor_by_node,
        executable_nodes=executable_nodes,
    )

    active_set = frozenset(active)
    owner_groups: dict[str, list[str]] = {}
    phase_nodes: list[str] = []
    admission_only_nodes: list[str] = []
    for node_id, record in later_records.items():
        if node_id not in active_set:
            continue
        # Owner and phase tiers diagnose only the work introduced by the
        # requested phase. Prior-phase coverage remains in the active admission
        # suite, so replaying it here would duplicate pytest execution at every
        # later milestone.
        if record.activation_phase != checked_phase:
            continue
        if record.diagnostic_role == "owner":
            assert record.owner_ref is not None
            owner_groups.setdefault(record.owner_ref, []).append(node_id)
        elif record.diagnostic_role == "phase":
            phase_nodes.append(node_id)
        else:
            admission_only_nodes.append(node_id)
    owner_result = MappingProxyType(
        {
            owner: tuple(sorted(nodes))
            for owner, nodes in sorted(owner_groups.items())
        }
    )

    return InventoryResult(
        inventory_ref=str(top["inventory_ref"]),
        baseline_source_ref=str(top["baseline_source_ref"]),
        active_node_ids=active,
        collectable_node_ids=tuple(sorted(collectable_nodes)),
        deferred_rewrite_refs=deferred,
        due_rewrite_refs=due,
        owner_node_ids=owner_result,
        phase_node_ids=tuple(sorted(phase_nodes)),
        admission_only_node_ids=tuple(sorted(admission_only_nodes)),
        source_tests=source_records,
        later_nodes=later_records,
        parsed_module_count=parse_count,
        literal_metadata_ref=content_ref(
            "literal_test_metadata", _normalized_later_metadata(later_records)
        ),
        active_node_set_ref=content_ref("active_test_nodes", list(active)),
        collectable_node_set_ref=content_ref(
            "collectable_test_nodes", list(sorted(collectable_nodes))
        ),
    )


__all__ = [
    "INVENTORY_SCHEMA",
    "InventoryError",
    "InventoryResult",
    "LaterNodeRecord",
    "PHASES",
    "REVIEWED_COUNTS",
    "SourceTestRecord",
    "content_ref",
    "load_and_verify",
    "load_strict_json",
    "source_ast_sha256",
    "verify_document_authority_pin",
]
