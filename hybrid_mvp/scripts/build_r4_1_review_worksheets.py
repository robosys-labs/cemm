#!/usr/bin/env python3
"""Build deterministic, non-authoritative R4.1 source-review worksheets."""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import difflib
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from cemm_authoritative_hybrid.authority import AuthorityLinker, LinkedAuthority
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.r4_contracts import ReviewedScenario
from cemm_authoritative_hybrid.r4_expansion import (
    SourceUniverse,
    expand_reviewed_source_universe,
)


MAX_INPUT_FILES = 64
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_WORKSHEET_ROWS = 4096
MAX_WORKSHEET_BYTES = 16 * 1024 * 1024
MAX_AGGREGATE_BYTES = 48 * 1024 * 1024
MAX_JSON_DEPTH = 64
MAX_READ_CALLS = 8192

_FILES = (
    "PURPOSE_DECISIONS.json",
    "REVIEW_SUMMARY.md",
    "SOURCE_UNIVERSE.json",
    "STRUCTURAL_DECISIONS.json",
    "SUPERVISION_DECISIONS.json",
)
_JSON_FILES = tuple(name for name in _FILES if name.endswith(".json"))
_ENVELOPE_FIELDS = frozenset(
    {
        "schema",
        "worksheet_ref",
        "draft_non_authoritative",
        "input_set_ref",
        "inputs",
        "current_snapshot",
        "row_count",
        "rows",
    }
)
_SCHEMAS = {
    "SOURCE_UNIVERSE.json": "cemm-r4-1-source-universe-worksheet-v1",
    "STRUCTURAL_DECISIONS.json": "cemm-r4-1-structural-decisions-worksheet-v1",
    "SUPERVISION_DECISIONS.json": "cemm-r4-1-supervision-decisions-worksheet-v1",
    "PURPOSE_DECISIONS.json": "cemm-r4-1-purpose-decisions-worksheet-v1",
}
_WINDOWS_REPARSE_POINT = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
_CONDITIONAL_SCENARIOS = (
    "scenario:modality-0040",
    "scenario:modality-0046",
)
_RESTART_SCENARIOS = tuple(f"scenario:restart-{index:04d}" for index in range(191, 201))
_PURPOSES = ("train", "selection", "calibration", "frozen_test")
_DENOMINATOR_FAMILIES = (
    "semantic_expression",
    "operator",
    "mode",
    "role",
    "state_compatibility",
    "topology",
    "typed_abstention",
    "critical_residual",
    "transition_effect",
    "no_effect",
    "response_meaning",
    "perspective_reference",
    "literal_copy",
)
_COMPILER_MODULES = (
    "__init__.py",
    "affordances.py",
    "authority.py",
    "canonical.py",
    "config.py",
    "contributions.py",
    "coverage.py",
    "cycle.py",
    "decision.py",
    "dialogue.py",
    "epistemic.py",
    "expression_projection.py",
    "expressions.py",
    "forms.py",
    "gaps.py",
    "grounding.py",
    "literal_codec.py",
    "persistence.py",
    "programs.py",
    "proposal.py",
    "proposal_context.py",
    "r3_codec.py",
    "r3_persistence.py",
    "r4_contracts.py",
    "r4_expansion.py",
    "recursive_composer/__init__.py",
    "recursive_composer/_core.py",
    "recursive_composer/_expand.py",
    "recursive_composer/_search.py",
    "recursive_compiler.py",
    "situation.py",
    "transition_preview.py",
    "verifier.py",
    "verifier_reconstruction.py",
)


@dataclass(frozen=True)
class ReproducedScenarioSource:
    scenario_rows: tuple[dict[str, Any], ...]
    source_bytes: bytes
    generator_source: bytes
    generator_source_sha256: str
    unified_diff: str
    patch_variants: Mapping[str, Mapping[str, Any]]
    variant_rows: Mapping[str, tuple[dict[str, Any], ...]]


def _verify_compiler_module_closure(inputs: Mapping[str, bytes]) -> None:
    package = "cemm_authoritative_hybrid"
    expected_paths = {
        f"src/{package}/{name}" for name in _COMPILER_MODULES
    }
    actual_paths = {
        path for path in inputs if path.startswith(f"src/{package}/")
    }
    if actual_paths != expected_paths:
        raise ValueError("source compiler module input set is not exact")
    def module_name(relative: str) -> str:
        parts = list(Path(relative).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        return ".".join((package, *parts))

    by_module = {
        module_name(str(Path(path).relative_to(f"src/{package}"))): raw
        for path, raw in inputs.items()
        if path in expected_paths
    }
    expected_modules = {module_name(name) for name in _COMPILER_MODULES}
    if set(by_module) != expected_modules:
        raise ValueError("source compiler module inventory is not exact")
    package_modules = {
        module_name(name)
        for name in _COMPILER_MODULES
        if Path(name).name == "__init__.py"
    }
    pending = [
        package,
        f"{package}.authority",
        f"{package}.canonical",
        f"{package}.r4_contracts",
        f"{package}.r4_expansion",
    ]
    reached: set[str] = set()

    def require_dependency(dependency: str) -> None:
        if dependency not in by_module:
            raise ValueError(
                f"source compiler dependency {dependency!r} is missing from input set"
            )
        parts = dependency.split(".")
        for length in range(1, len(parts)):
            ancestor = ".".join(parts[:length])
            if ancestor in package_modules and ancestor not in reached:
                pending.append(ancestor)
        if dependency not in reached:
            pending.append(dependency)

    while pending:
        module = pending.pop()
        if module in reached:
            continue
        raw = by_module.get(module)
        if raw is None:
            raise ValueError("source compiler dependency is missing")
        reached.add(module)
        tree = ast.parse(raw.decode("utf-8", errors="strict"), filename=f"{module}.py")
        current_package = (
            module if module in package_modules else module.rpartition(".")[0]
        )
        for node in ast.walk(tree):
            dependencies: tuple[str, ...] = ()
            if isinstance(node, ast.ImportFrom):
                if node.level:
                    base_parts = current_package.split(".")
                    if node.level > len(base_parts):
                        raise ValueError("source compiler dependency leaves the bound package")
                    base = ".".join(base_parts[: len(base_parts) - node.level + 1])
                    imported_module = (
                        f"{base}.{node.module}" if node.module else base
                    )
                else:
                    imported_module = node.module or ""
                if imported_module == package or node.module is None:
                    dependencies = tuple(
                        f"{imported_module}.{alias.name}"
                        for alias in node.names
                        if alias.name != "*"
                    )
                    if any(alias.name == "*" for alias in node.names):
                        dependencies += (imported_module,)
                elif imported_module.startswith(f"{package}."):
                    dependencies = (imported_module,)
                    dependencies += tuple(
                        candidate
                        for alias in node.names
                        if (candidate := f"{imported_module}.{alias.name}") in by_module
                    )
            elif isinstance(node, ast.Import):
                dependencies = tuple(
                    alias.name
                    for alias in node.names
                    if alias.name == package or alias.name.startswith(f"{package}.")
                )
            for dependency in dependencies:
                require_dependency(dependency)
    if reached != set(by_module):
        raise ValueError("source compiler dependency closure changed")


def _grounded(target: str) -> dict[str, Any]:
    return {"kind": "grounded", "target": target}


def _literal(value: object, value_type: str = "string") -> dict[str, Any]:
    return {"kind": "literal", "value_type": value_type, "value": value}


def _application(
    local_ref: str, operator: str, predicate: str, roles: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "local_ref": local_ref,
        "operator": operator,
        "predicate": predicate,
        "roles": dict(roles),
    }


def _state(local_ref: str, subject: str, dimension: str, value: str) -> dict[str, Any]:
    return _application(
        local_ref,
        "op:state",
        dimension,
        {
            "role:subject": _grounded(subject),
            "role:dimension": _grounded(dimension),
            "role:value": _grounded(value),
        },
    )


def _relation(
    local_ref: str, predicate: str, subject: str, object_ref: str
) -> dict[str, Any]:
    return _application(
        local_ref,
        "op:relation",
        predicate,
        {
            "role:subject": _grounded(subject),
            "role:object": _grounded(object_ref),
        },
    )


def _event(local_ref: str, predicate: str) -> dict[str, Any]:
    return _application(
        local_ref,
        "op:event",
        predicate,
        {
            "role:actor": _grounded("participant:user"),
            "role:addressee": _grounded("participant:system"),
        },
    )


def _composed(
    *,
    shape: str,
    mode: str,
    applications: Sequence[Mapping[str, Any]],
    links: Sequence[Mapping[str, Any]],
    roots: Sequence[str],
) -> dict[str, Any]:
    return {
        "kind": "composed_expression",
        "shape": shape,
        "mode": mode,
        "applications": [dict(row) for row in applications],
        "expression_links": [dict(row) for row in links],
        "root_local_refs": list(roots),
    }


def _scenario(index: int, assertion: Mapping[str, Any], surface: str) -> dict[str, Any]:
    return {
        "scenario_ref": f"scenario:structural_composition-{index:04d}",
        "review_status": "reviewed",
        "competency_category": "recursive_family_proof",
        "semantic_assertions": [dict(assertion)],
        "surface_examples": [surface],
        "metadata": {},
    }


def _link(local_ref: str, link_type: str, operands: Sequence[str]) -> dict[str, Any]:
    return {
        "local_ref": local_ref,
        "link_type": link_type,
        "operand_local_refs": list(operands),
    }


_PROPOSALS: tuple[dict[str, Any], ...] = (
    {
        "scenario": _scenario(
            211,
            _composed(
                shape="linked",
                mode="SIMULATE",
                applications=(
                    _state("server_online", "entity:server", "dim:availability", "value:online"),
                    _state("lamp_on", "entity:lamp", "dim:power", "value:on"),
                ),
                links=(_link("condition", "link:condition", ("server_online", "lamp_on")),),
                roots=("condition",),
            ),
            "if the server is online then the lamp is on",
        ),
        "candidate_output": "In the simulation, if the server is online, the lamp is on.",
        "designation_spans": ((7, 13, "entity:server"), (17, 23, "value:online"), (33, 37, "entity:lamp"), (41, 43, "value:on")),
    },
    {
        "scenario": _scenario(
            212,
            _composed(
                shape="linked",
                mode="SIMULATE",
                applications=(
                    _state("lamp_off", "entity:lamp", "dim:power", "value:off"),
                    _state("server_offline", "entity:server", "dim:availability", "value:offline"),
                ),
                links=(_link("cause", "link:cause", ("lamp_off", "server_offline")),),
                roots=("cause",),
            ),
            "suppose the lamp is off because the server is offline",
        ),
        "candidate_output": "In the simulation, the lamp is off since the server is offline.",
        "designation_spans": ((12, 16, "entity:lamp"), (20, 23, "value:off"), (36, 42, "entity:server"), (46, 53, "value:offline")),
    },
    {
        "scenario": _scenario(
            213,
            _composed(
                shape="linked",
                mode="OBSERVE",
                applications=(
                    _state("server_online", "entity:server", "dim:availability", "value:online"),
                    _state("lamp_off", "entity:lamp", "dim:power", "value:off"),
                ),
                links=(_link("contrast", "link:contrast", ("server_online", "lamp_off")),),
                roots=("contrast",),
            ),
            "the server is online but the lamp is off",
        ),
        "candidate_output": "Although the server is online, the lamp is off.",
        "designation_spans": ((4, 10, "entity:server"), (14, 20, "value:online"), (29, 33, "entity:lamp"), (37, 40, "value:off")),
    },
    {
        "scenario": _scenario(
            214,
            _composed(
                shape="linked",
                mode="QUERY",
                applications=(
                    _application(
                        "job_type",
                        "op:type",
                        "concept:job_role",
                        {
                            "role:subject": _grounded("concept:job_role"),
                            "role:type": _literal("concept"),
                        },
                    ),
                    _state("server_online", "entity:server", "dim:availability", "value:online"),
                ),
                links=(_link("conjunction", "link:conjunction", ("job_type", "server_online")),),
                roots=("conjunction",),
            ),
            "what is job and is the server online?",
        ),
        "candidate_output": "Job is a concept, and the server is online.",
        "designation_spans": ((8, 11, "concept:job_role"), (23, 29, "entity:server"), (30, 36, "value:online")),
    },
    {
        "scenario": _scenario(
            215,
            _composed(
                shape="multi_root",
                mode="OBSERVE",
                applications=(
                    _state("server_online", "entity:server", "dim:availability", "value:online"),
                    _state("lamp_on", "entity:lamp", "dim:power", "value:on"),
                ),
                links=(),
                roots=("server_online", "lamp_on"),
            ),
            "the server is online. the lamp is on.",
        ),
        "candidate_output": "The lamp is on. The server is online.",
        "designation_spans": ((4, 10, "entity:server"), (14, 20, "value:online"), (26, 30, "entity:lamp"), (34, 36, "value:on")),
    },
    {
        "scenario": _scenario(
            216,
            _composed(
                shape="multi_root",
                mode="OBSERVE",
                applications=(
                    _relation("alice_likes", "rel:likes", "entity:alice", "entity:book"),
                    _relation("bob_owns", "rel:owns", "entity:bob", "entity:book"),
                ),
                links=(),
                roots=("alice_likes", "bob_owns"),
            ),
            "alice likes the book. bob owns the book.",
        ),
        "candidate_output": "Bob owns the book. Alice likes the book.",
        "designation_spans": ((0, 5, "entity:alice"), (6, 11, "rel:likes"), (16, 20, "entity:book"), (22, 25, "entity:bob"), (26, 30, "rel:owns"), (35, 39, "entity:book")),
    },
    {
        "scenario": _scenario(
            217,
            _composed(
                shape="multi_root",
                mode="OBSERVE",
                applications=(
                    _event("greeting", "event:greeting"),
                    _relation("alice_owns", "rel:owns", "entity:alice", "entity:book"),
                ),
                links=(),
                roots=("greeting", "alice_owns"),
            ),
            "hello. alice owns the book.",
        ),
        "candidate_output": "Alice owns the book. You greeted me.",
        "designation_spans": ((0, 5, "event:greeting"), (7, 12, "entity:alice"), (13, 17, "rel:owns"), (22, 26, "entity:book")),
    },
    {
        "scenario": _scenario(
            218,
            _composed(
                shape="multi_root",
                mode="OBSERVE",
                applications=(
                    _event("farewell", "event:farewell"),
                    _state("server_offline", "entity:server", "dim:availability", "value:offline"),
                ),
                links=(),
                roots=("farewell", "server_offline"),
            ),
            "goodbye. the server is offline.",
        ),
        "candidate_output": "The server is offline. You said goodbye.",
        "designation_spans": ((0, 7, "event:farewell"), (13, 19, "entity:server"), (23, 30, "value:offline")),
    },
)


def _is_link_or_reparse(metadata: os.stat_result) -> bool:
    return stat.S_ISLNK(metadata.st_mode) or bool(
        getattr(metadata, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT
    )


def _same_file(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev,
        left.st_ino,
        stat.S_IFMT(left.st_mode),
        left.st_size,
        left.st_mtime_ns,
        left.st_nlink,
        getattr(left, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT,
    ) == (
        right.st_dev,
        right.st_ino,
        stat.S_IFMT(right.st_mode),
        right.st_size,
        right.st_mtime_ns,
        right.st_nlink,
        getattr(right, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT,
    )


def _same_identity(left: os.stat_result, right: os.stat_result) -> bool:
    return (
        left.st_dev,
        left.st_ino,
        stat.S_IFMT(left.st_mode),
        getattr(left, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT,
    ) == (
        right.st_dev,
        right.st_ino,
        stat.S_IFMT(right.st_mode),
        getattr(right, "st_file_attributes", 0) & _WINDOWS_REPARSE_POINT,
    )


def _read_regular(path: Path, *, maximum: int, owner: str) -> bytes:
    parent_before = _trusted_directory(path.parent, owner=f"{owner} parent")
    try:
        before = os.lstat(path)
    except OSError as exc:
        raise ValueError(f"{owner} file is missing") from exc
    if (
        not stat.S_ISREG(before.st_mode)
        or _is_link_or_reparse(before)
        or before.st_nlink != 1
    ):
        raise ValueError(f"{owner} file must be one regular non-link file")
    if before.st_size <= 0 or before.st_size > maximum:
        raise ValueError(f"{owner} file violates byte bounds")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor: int | None = None
    try:
        descriptor = os.open(path, flags)
        opened = os.fstat(descriptor)
        if not _same_file(before, opened):
            raise ValueError(f"{owner} file changed before open")
        chunks: list[bytes] = []
        remaining = before.st_size + 1
        for _ in range(MAX_READ_CALLS):
            try:
                chunk = os.read(descriptor, remaining)
            except InterruptedError:
                continue
            except OSError as exc:
                if exc.errno == errno.EINTR:
                    continue
                raise ValueError(f"cannot read {owner} file") from exc
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
            if remaining <= 0:
                break
        else:
            raise ValueError(f"{owner} file exceeds bounded read calls")
        after_descriptor = os.fstat(descriptor)
    finally:
        if descriptor is not None:
            os.close(descriptor)
    after = os.lstat(path)
    parent_after = _trusted_directory(path.parent, owner=f"{owner} parent")
    raw = b"".join(chunks)
    if (
        not _same_file(opened, after_descriptor)
        or not _same_file(opened, after)
        or not _same_identity(parent_before, parent_after)
        or len(raw) != opened.st_size
    ):
        raise ValueError(f"{owner} file changed or was read incompletely")
    return raw


def _strict_json(raw: bytes, *, owner: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"{owner} contains duplicate JSON fields")
            result[key] = value
        return result

    def nonfinite(token: str) -> object:
        raise ValueError(f"{owner} contains non-finite JSON: {token}")

    try:
        value = json.loads(
            raw.decode("utf-8", errors="strict"),
            object_pairs_hook=pairs,
            parse_constant=nonfinite,
        )
        _validate_json_shape(value)
        return value
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"{owner} is not strict JSON") from exc


def _bounded_directory_entries(path: Path, *, owner: str) -> tuple[os.DirEntry[str], ...]:
    result: list[os.DirEntry[str]] = []
    with os.scandir(path) as entries:
        for entry in entries:
            if len(result) >= len(_FILES) + 1:
                raise ValueError(f"{owner} candidate file inventory exceeds bound")
            result.append(entry)
    return tuple(result)


def _validate_json_shape(value: object) -> None:
    stack: list[tuple[object, int]] = [(value, 1)]
    while stack:
        item, depth = stack.pop()
        if depth > MAX_JSON_DEPTH:
            raise ValueError("worksheet JSON depth bound violated")
        if isinstance(item, Mapping):
            if any(type(key) is not str for key in item):
                raise TypeError("worksheet JSON keys must be exact strings")
            stack.extend((child, depth + 1) for child in item.values())
        elif type(item) in {list, tuple}:
            stack.extend((child, depth + 1) for child in item)
        elif item is not None and type(item) not in {str, int, float, bool}:
            raise TypeError("worksheet JSON contains unsupported value")
        if type(item) is float and (item != item or item in {float("inf"), float("-inf")}):
            raise ValueError("worksheet JSON contains non-finite value")


def _json_bytes(value: object) -> bytes:
    _validate_json_shape(value)
    try:
        payload = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8", errors="strict") + b"\n"
    except (UnicodeEncodeError, ValueError) as exc:
        raise ValueError("worksheet JSON is not canonical UTF-8") from exc
    if len(payload) > MAX_WORKSHEET_BYTES:
        raise ValueError("worksheet exceeds byte bound")
    return payload


def _row(row: Mapping[str, Any]) -> dict[str, Any]:
    material = dict(row)
    material["row_ref"] = stable_ref("review_worksheet_row", material)
    return material


def _option(
    subject_ref: str, label: str, payload: object, *, selectable: bool = True
) -> dict[str, Any]:
    material = {
        "subject_ref": subject_ref,
        "label": label,
        "payload": payload,
        "selectable": selectable,
    }
    return {
        "option_ref": stable_ref("review_worksheet_option", material),
        "label": label,
        "payload": payload,
        "selectable": selectable,
    }


def _decision(
    *, row_kind: str, subject_ref: str, fields: Mapping[str, Any], options: Sequence[dict[str, Any]]
) -> dict[str, Any]:
    return _row(
        {
            "row_kind": row_kind,
            "subject_ref": subject_ref,
            **dict(fields),
            "options": list(options),
            "decision_state": "unresolved",
            "selected_option_ref": None,
        }
    )


def _canonical_scenario_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return b"".join(_json_bytes(dict(row)) for row in rows)


def _parse_scenarios(raw: bytes) -> tuple[tuple[dict[str, Any], ...], tuple[ReviewedScenario, ...]]:
    if b"\r" in raw or not raw.endswith(b"\n"):
        raise ValueError("scenario source must be canonical LF JSONL")
    lines = raw[:-1].split(b"\n")
    if not 1 <= len(lines) <= 512:
        raise ValueError("scenario source row bound violated")
    source_rows: list[dict[str, Any]] = []
    scenarios: list[ReviewedScenario] = []
    for line in lines:
        value = _strict_json(line, owner="scenario source row")
        if type(value) is not dict or _json_bytes(value)[:-1] != line:
            raise ValueError("scenario source row is not canonical")
        source_rows.append(value)
        scenarios.append(ReviewedScenario.from_dict(value))
    return tuple(source_rows), tuple(scenarios)


def _execute_generator(source: bytes, *, owner: str) -> tuple[dict[str, Any], ...]:
    namespace: dict[str, Any] = {"__name__": f"_{owner}", "__file__": "scripts/generate_scenarios.py"}
    try:
        code = compile(source.decode("utf-8", errors="strict"), "scripts/generate_scenarios.py", "exec")
        exec(code, namespace, namespace)
        rows = namespace["generate_all"]()
    except Exception as exc:
        raise ValueError(f"{owner} generator source is not reproducible") from exc
    if type(rows) is not list or len(rows) > 512 or any(type(row) is not dict for row in rows):
        raise ValueError(f"{owner} generator returned invalid rows")
    return tuple(rows)


_LEGACY_CONDITIONAL_BLOCKS = (
    """    _next(cat, [*_disabled_proposal(\"conditional event scope is not admitted in R4\"),
                _assertion(\"mode\", mode=\"simulate\")],
          [\"if the server is online then proceed\", \"when the server is online proceed\"])
""",
    """    _next(cat, [*_disabled_proposal(\"conditional greeting scope is not admitted in R4\"),
                _assertion(\"mode\", mode=\"simulate\")],
          [\"if alice arrives then greet her\", \"when alice arrives greet her\"])
""",
)


def _candidate_generator_source(
    base: bytes,
    added: Sequence[Mapping[str, Any]],
    *,
    retire_legacy_conditionals: bool,
) -> bytes:
    text = base.decode("utf-8", errors="strict")
    if retire_legacy_conditionals:
        for index, block in zip((40, 46), _LEGACY_CONDITIONAL_BLOCKS, strict=True):
            if text.count(block) != 1:
                raise ValueError("legacy conditional generator block is not exact")
            reservation = (
                "    # R4.1 conditional retirement proposal: reserve the historical "
                f"{index:04d} identity.\n"
                "    counter += 1\n"
            )
            text = text.replace(block, reservation)
    marker = "\n    return cases\n"
    if text.count(marker) != 1:
        raise ValueError("generator return marker is not exact")
    encoded = json.dumps(
        list(added), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    insertion = (
        "\n    # R4.1 STRUCTURAL SOURCE PROPOSAL — pending exact human approval.\n"
        f"    cases.extend(json.loads({encoded!r}))\n"
    )
    candidate = text.replace(marker, insertion + marker)
    expected_count = 216 if retire_legacy_conditionals else 218
    count_assertion = 'assert len(cases) == 210, f"Expected 210 cases, got {len(cases)}"'
    if text.count(count_assertion) != 1:
        raise ValueError("generator count assertion is not exact")
    candidate = candidate.replace(
        count_assertion,
        f'assert len(cases) == {expected_count}, f"Expected {expected_count} cases, got {{len(cases)}}"',
    )
    candidate = candidate.replace(
        "Generate the 210-scenario coverage matrix as JSONL.",
        f"Generate the proposed {expected_count}-scenario coverage matrix as JSONL.",
        1,
    ).replace(
        "The 210 cases cover all semantic",
        f"The proposed {expected_count} cases cover all semantic",
        1,
    )
    return candidate.encode("utf-8")


def reproduce_proposed_scenario_source(
    *,
    repository_root: Path,
    structural_rows: Sequence[Mapping[str, Any]],
    authority: LinkedAuthority | None = None,
    base_generator_source: bytes | None = None,
) -> ReproducedScenarioSource:
    root = Path(repository_root).resolve(strict=True)
    base = (
        _read_regular(
            root / "scripts/generate_scenarios.py",
            maximum=MAX_INPUT_BYTES,
            owner="generator",
        )
        if base_generator_source is None
        else bytes(base_generator_source)
    )
    added = tuple(dict(row["resulting_scenario_row"]) for row in structural_rows)
    linked_authority = authority
    if linked_authority is None:
        linked_authority, _inputs = _authority_snapshot(root)
    patch_variants: dict[str, Mapping[str, Any]] = {}
    variant_rows: dict[str, tuple[dict[str, Any], ...]] = {}
    variant_sources: dict[str, bytes] = {}
    variant_diffs: dict[str, str] = {}
    added_refs = {item["scenario_ref"] for item in added}
    policies = (
        ("retain_typed_proposal_gaps", False),
        ("retire_with_reserved_indices", True),
    )
    for policy, retire in policies:
        candidate = _candidate_generator_source(
            base,
            added,
            retire_legacy_conditionals=retire,
        )
        scenario_rows = _execute_generator(candidate, owner=f"candidate-{policy}")
        actual_added = tuple(row for row in scenario_rows if row.get("scenario_ref") in added_refs)
        if actual_added != added:
            raise ValueError("candidate generator differs from exact proposed rows")
        source_bytes = _canonical_scenario_bytes(scenario_rows)
        diff = "".join(
            difflib.unified_diff(
                base.decode("utf-8").splitlines(keepends=True),
                candidate.decode("utf-8").splitlines(keepends=True),
                fromfile="a/scripts/generate_scenarios.py",
                tofile="b/scripts/generate_scenarios.py",
            )
        )
        universe = expand_reviewed_source_universe(
            tuple(ReviewedScenario.from_dict(row) for row in scenario_rows),
            authority=linked_authority,
        )
        snapshot = _snapshot(universe)
        patch_variants[policy] = {
            "path": "scripts/generate_scenarios.py",
            "base_sha256": hashlib.sha256(base).hexdigest(),
            "result_sha256": hashlib.sha256(candidate).hexdigest(),
            "scenario_source_sha256": hashlib.sha256(source_bytes).hexdigest(),
            "unified_diff": diff,
            "scenario_count": snapshot["reviewed_scenario_count"],
            "case_count": snapshot["expanded_case_count"],
            "disposition_counts": snapshot["disposition_counts"],
            "source_universe_ref": snapshot["source_universe_ref"],
        }
        variant_rows[policy] = scenario_rows
        variant_sources[policy] = candidate
        variant_diffs[policy] = diff
    retained_policy = "retain_typed_proposal_gaps"
    retained_rows = variant_rows[retained_policy]
    retained_source = variant_sources[retained_policy]
    return ReproducedScenarioSource(
        scenario_rows=retained_rows,
        source_bytes=_canonical_scenario_bytes(retained_rows),
        generator_source=retained_source,
        generator_source_sha256=hashlib.sha256(retained_source).hexdigest(),
        unified_diff=variant_diffs[retained_policy],
        patch_variants=patch_variants,
        variant_rows=variant_rows,
    )


def _authority_snapshot(root: Path) -> tuple[LinkedAuthority, tuple[dict[str, Any], ...]]:
    manifest_path = root / "data/authority/manifest.json"
    manifest_raw = _read_regular(manifest_path, maximum=MAX_INPUT_BYTES, owner="authority manifest")
    manifest = _strict_json(manifest_raw, owner="authority manifest")
    if type(manifest) is not dict or type(manifest.get("owners")) is not list:
        raise ValueError("authority manifest shape is invalid")
    if not 1 <= len(manifest["owners"]) <= MAX_INPUT_FILES - 1:
        raise ValueError("authority owner count violates bounds")
    inputs = [_input_row("data/authority/manifest.json", manifest_raw)]
    retained: dict[str, bytes] = {"manifest.json": manifest_raw}
    aggregate_bytes = len(manifest_raw)
    for owner in manifest["owners"]:
        if type(owner) is not dict or set(owner) != {"name", "path", "sha256"}:
            raise ValueError("authority owner row is invalid")
        relative = owner["path"]
        if (
            type(relative) is not str
            or not relative
            or Path(relative).is_absolute()
            or ".." in Path(relative).parts
        ):
            raise ValueError("authority owner path is unsafe")
        raw = _read_regular(
            root / "data/authority" / relative,
            maximum=MAX_INPUT_BYTES,
            owner="authority owner",
        )
        aggregate_bytes += len(raw)
        if aggregate_bytes > MAX_INPUT_BYTES:
            raise ValueError("authority source bytes violate aggregate bound")
        if hashlib.sha256(raw).hexdigest() != owner["sha256"]:
            raise ValueError("authority owner hash mismatch")
        retained[relative] = raw
        inputs.append(_input_row(f"data/authority/{relative}", raw))
    with tempfile.TemporaryDirectory(prefix="cemm-r4-1-authority-") as temp:
        snapshot = Path(temp)
        for relative, raw in retained.items():
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        authority = AuthorityLinker().link_path(snapshot / "manifest.json")
    return authority, tuple(sorted(inputs, key=lambda row: row["path"]))


def _input_row(path: str, raw: bytes) -> dict[str, Any]:
    return {
        "path": path,
        "byte_length": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _snapshot(universe: SourceUniverse) -> dict[str, Any]:
    counts = dict(universe.disposition_counts)
    return {
        "reviewed_scenario_count": universe.scenario_count,
        "expanded_case_count": universe.expanded_count,
        "disposition_counts": {
            "semantic": counts["semantic"],
            "explicit_gap": counts["explicit_gap"],
            "verification_rejection": counts["verification_rejection"],
            "restart_diagnostic": counts["restart_diagnostic_candidate"],
        },
        "source_universe_ref": universe.source_set_ref,
    }


def _case_row(case: Any, *, universe: str) -> dict[str, Any]:
    wire = case.as_dict()
    row = {
        "row_kind": "expanded_case",
        "universe": universe,
        "case_ref": case.case_ref,
        "scenario_ref": case.scenario_ref,
        "surface_ref": case.surface_ref,
        "context_ref": case.context_ref,
        "contract_ref": case.contract_ref,
        "surface": case.surface,
        "surface_index": case.surface_index,
        "environment_index": case.environment_index,
        "environment_sha256": hashlib.sha256(_json_bytes(wire["environment"])).hexdigest(),
        "language": case.language,
        "trajectory_ref": case.trajectory_ref,
        "turn_index": case.turn_index,
        "source_disposition": case.source_disposition.value,
        "outcome_kind": case.contract.outcome_kind.value,
        "expected_expression_relation": case.contract.expression_relation.value,
        "expected_expression_refs": [row.expression_ref for row in case.contract.expected_expressions],
    }
    row["expanded_case_sha256"] = hashlib.sha256(_json_bytes(wire)).hexdigest()
    return _row(row)


def _scenario_row(value: Mapping[str, Any], *, universe: str, change_kind: str) -> dict[str, Any]:
    raw = _json_bytes(dict(value))
    return _row(
        {
            "row_kind": "scenario",
            "universe": universe,
            "change_kind": change_kind,
            "scenario_ref": value["scenario_ref"],
            "scenario_sha256": hashlib.sha256(raw).hexdigest(),
            "scenario": dict(value),
        }
    )


def collect_structural_decision_rows(
    *,
    candidate_universe: SourceUniverse,
    reproduced: ReproducedScenarioSource,
    proposal_rows: Sequence[Mapping[str, Any]],
    current_universe: SourceUniverse,
) -> tuple[dict[str, Any], ...]:
    cases = {case.scenario_ref: case for case in candidate_universe.cases}
    retained_patch = reproduced.patch_variants["retain_typed_proposal_gaps"]
    base_generator_sha256 = retained_patch["base_sha256"]
    result: list[dict[str, Any]] = []
    for proposal in proposal_rows:
        scenario = dict(proposal["scenario"])
        case = cases[scenario["scenario_ref"]]
        expression = case.contract.expected_expressions[0]
        assertion = scenario["semantic_assertions"][0]
        subject_ref = scenario["scenario_ref"]
        row = _decision(
            row_kind="composed_expression_proposal",
            subject_ref=subject_ref,
            fields={
                "proposal_kind": assertion["shape"],
                "semantic_mode": assertion["mode"],
                "contains_type_role": any(
                    app["operator"] == "op:type" and "role:type" in app["roles"]
                    for app in assertion["applications"]
                ),
                "resulting_scenario_row": scenario,
                "designation_spans": [
                    {"start": start, "end": end, "target_ref": target}
                    for start, end, target in proposal["designation_spans"]
                ],
                "candidate_output": proposal["candidate_output"],
                "compiled_candidate": {
                    "case_ref": case.case_ref,
                    "contract_ref": case.contract_ref,
                    "expected_expression_relation": case.contract.expression_relation.value,
                    "expressions": [expression.as_dict()],
                },
                "generator_patch": {
                    "path": "scripts/generate_scenarios.py",
                    "base_sha256": base_generator_sha256,
                    "variant_result_sha256": {
                        label: payload["result_sha256"]
                        for label, payload in reproduced.patch_variants.items()
                    },
                    "variant_scenario_source_sha256": {
                        label: payload["scenario_source_sha256"]
                        for label, payload in reproduced.patch_variants.items()
                    },
                },
            },
            options=(
                _option(subject_ref, "approve_exact_proposal", {"scenario_ref": subject_ref}),
                _option(subject_ref, "reject_exact_proposal", {"scenario_ref": subject_ref}),
            ),
        )
        result.append(row)

    conflicts = tuple(
        sorted(
            case.case_ref
            for case in current_universe.cases
            if case.contract.expression_relation.value == "conflict"
        )
    )
    result.append(
        _decision(
            row_kind="conflict_preservation",
            subject_ref="source_policy:conflict-preservation",
            fields={"case_refs": list(conflicts)},
            options=(
                _option("source_policy:conflict-preservation", "preserve_as_alternatives", {"relation": "conflict"}),
            ),
        )
    )
    result.append(
        _decision(
            row_kind="legacy_conditional",
            subject_ref="source_policy:legacy-conditionals",
            fields={"scenario_refs": list(_CONDITIONAL_SCENARIOS)},
            options=(
                _option(
                    "source_policy:legacy-conditionals",
                    "retain_typed_proposal_gaps",
                    reproduced.patch_variants["retain_typed_proposal_gaps"],
                ),
                _option(
                    "source_policy:legacy-conditionals",
                    "retire_with_reserved_indices",
                    reproduced.patch_variants["retire_with_reserved_indices"],
                ),
            ),
        )
    )
    restart_cases = tuple(
        sorted(case.case_ref for case in current_universe.cases if case.scenario_ref in _RESTART_SCENARIOS)
    )
    result.append(
        _decision(
            row_kind="restart_diagnostic",
            subject_ref="source_policy:restart-diagnostic",
            fields={"scenario_refs": list(_RESTART_SCENARIOS), "case_refs": list(restart_cases)},
            options=(
                _option("source_policy:restart-diagnostic", "approve_diagnostic_only", {"proposal_rows": 0, "realization_rows": 0}),
                _option("source_policy:restart-diagnostic", "reject_pending_replacement", {"fail_closed": True}),
            ),
        )
    )
    result.append(
        _decision(
            row_kind="generator_patch",
            subject_ref="source_patch:r4-1-structural",
            fields={
                "base_path": "scripts/generate_scenarios.py",
                "base_sha256": base_generator_sha256,
                "patch_variants": dict(reproduced.patch_variants),
                "resulting_scenario_refs": [row["scenario"]["scenario_ref"] for row in proposal_rows],
            },
            options=(
                *(
                    _option(
                        "source_patch:r4-1-structural",
                        label,
                        {
                            "conditional_policy": label,
                            "result_sha256": payload["result_sha256"],
                            "scenario_source_sha256": payload["scenario_source_sha256"],
                            "source_universe_ref": payload["source_universe_ref"],
                        },
                    )
                    for label, payload in reproduced.patch_variants.items()
                ),
            ),
        )
    )
    return tuple(result)


def _validate_structural_rows(rows: Sequence[Mapping[str, Any]]) -> None:
    proposals = [row for row in rows if row.get("row_kind") == "composed_expression_proposal"]
    if len(proposals) != 8:
        raise ValueError("structural proposal set must contain exactly eight rows")
    if [row["proposal_kind"] for row in proposals].count("linked") != 4 or [
        row["proposal_kind"] for row in proposals
    ].count("multi_root") != 4:
        raise ValueError("structural proposal set must contain four plus four shapes")
    if sum(row["semantic_mode"] == "SIMULATE" for row in proposals) < 2:
        raise ValueError("structural proposal set lacks semantic simulation coverage")
    if not any(row["contains_type_role"] is True for row in proposals):
        raise ValueError("structural proposal set lacks op:type role:type coverage")
    for row in proposals:
        compiled = row["compiled_candidate"]
        if compiled.get("expected_expression_relation") != "single" or len(compiled.get("expressions", ())) != 1:
            raise ValueError("structural proposal must compile with relation single")
        expression = compiled["expressions"][0]
        roots = expression["root_refs"]
        links = expression["expression_links"]
        if row["proposal_kind"] == "linked":
            link_refs = {link["link_ref"] for link in links}
            if len(roots) != 1 or roots[0] not in link_refs or not links or any(len(link["operand_refs"]) < 2 for link in links):
                raise ValueError("linked structural proposal topology is invalid")
        elif links or not 2 <= len(roots) <= 8:
            raise ValueError("multi_root structural proposal topology is invalid")


def _supervision_rows(
    current_universe: SourceUniverse, candidate_universe: SourceUniverse
) -> tuple[dict[str, Any], ...]:
    proposal_by_scenario = {item["scenario"]["scenario_ref"]: item for item in _PROPOSALS}
    rows: list[dict[str, Any]] = []
    for case in (*current_universe.cases, *candidate_universe.cases):
        if case.source_disposition.value == "restart_diagnostic_candidate":
            continue
        subject_ref = case.case_ref
        proposal = proposal_by_scenario.get(case.scenario_ref)
        expected_response = None if case.contract.expected_response is None else case.contract.expected_response.as_dict()
        branch_applicability = (
            ["retain_typed_proposal_gaps"]
            if case.scenario_ref in _CONDITIONAL_SCENARIOS
            else ["retain_typed_proposal_gaps", "retire_with_reserved_indices"]
        )
        proposal_projection = {
            "target_kind": {
                "semantic": "derive",
                "explicit_gap": "abstain",
                "verification_rejection": "verification_rejection",
            }[case.source_disposition.value],
            "match_policy": "exact",
            "expected_expression_relation": case.contract.expression_relation.value,
            "expected_expression_refs": [row.expression_ref for row in case.contract.expected_expressions],
        }
        realization_projection = {
            "response_contract": expected_response,
            "candidate_surface": None if proposal is None else proposal["candidate_output"],
        }
        designation_candidates = []
        if proposal is not None:
            surface = proposal["scenario"]["surface_examples"][0]
            for start, end, target in proposal["designation_spans"]:
                designation_candidates.append(
                    {
                        "surface": surface[start:end],
                        "start": start,
                        "end": end,
                        "candidate_target_ref": target,
                    }
                )
        rows.append(
            _decision(
                row_kind="proposal_supervision",
                subject_ref=f"proposal_decision:{subject_ref}",
                fields={
                    "source_case_ref": case.case_ref,
                    "scenario_ref": case.scenario_ref,
                    "surface_ref": case.surface_ref,
                    "language": case.language,
                    "source_disposition": case.source_disposition.value,
                    "branch_applicability": branch_applicability,
                    "source_projection": proposal_projection,
                },
                options=(
                    _option(
                        f"proposal_decision:{subject_ref}",
                        "provide_exact_proposal_target",
                        {
                            "required_abi": "Proposal Supervision ABI 1",
                            "proposal_target": None,
                            "reviewed_derivations_and_source_assignments_required": True,
                        },
                        selectable=False,
                    ),
                ),
            )
        )
        designation_subject = f"designation_decision:{subject_ref}"
        designation_options = [
            _option(
                designation_subject,
                "provide_exact_designation_bindings",
                {
                    "bindings": None,
                    "reviewed_empty_binding_set_permitted": True,
                },
                selectable=False,
            )
        ]
        if designation_candidates:
            designation_options.insert(
                0,
                _option(
                    designation_subject,
                    "approve_exact_candidate_bindings",
                    {"bindings": designation_candidates},
                ),
            )
        rows.append(
            _decision(
                row_kind="designation_supervision",
                subject_ref=designation_subject,
                fields={
                    "source_case_ref": case.case_ref,
                    "scenario_ref": case.scenario_ref,
                    "surface_ref": case.surface_ref,
                    "language": case.language,
                    "surface": case.surface,
                    "branch_applicability": branch_applicability,
                    "candidate_bindings": designation_candidates,
                },
                options=tuple(designation_options),
            )
        )
        realization_subject = f"realization_decision:{subject_ref}"
        realization_options = [
            _option(
                realization_subject,
                "provide_exact_realization_row",
                {
                    "required_abi": "Realization Supervision ABI 1",
                    "realization_row": None,
                    "exact_slots_and_alignments_required": True,
                },
                selectable=False,
            )
        ]
        if proposal is not None:
            realization_options.insert(
                0,
                _option(
                    realization_subject,
                    "approve_candidate_surface_for_exact_realization",
                    {"candidate_surface": proposal["candidate_output"]},
                    selectable=False,
                ),
            )
        rows.append(
            _decision(
                row_kind="realization_supervision",
                subject_ref=realization_subject,
                fields={
                    "source_case_ref": case.case_ref,
                    "scenario_ref": case.scenario_ref,
                    "surface_ref": case.surface_ref,
                    "language": case.language,
                    "branch_applicability": branch_applicability,
                    "source_projection": realization_projection,
                },
                options=tuple(realization_options),
            )
        )
        mutation_subject = f"mutation_decision:{subject_ref}"
        rows.append(
            _decision(
                row_kind="mutation_truth",
                subject_ref=mutation_subject,
                fields={
                    "source_case_ref": case.case_ref,
                    "scenario_ref": case.scenario_ref,
                    "surface_ref": case.surface_ref,
                    "branch_applicability": branch_applicability,
                    "source_expected_effect": case.contract.expected_effect.as_dict(),
                },
                options=(
                    _option(
                        mutation_subject,
                        "provide_exact_source_consistent_mutation_contract",
                        {
                            "required_abi": "Mutation Contract ABI 1",
                            "required_effect_kind": case.contract.expected_effect.kind.value,
                            "mutation_contract": None,
                        },
                        selectable=False,
                    ),
                    _option(
                        mutation_subject,
                        "reject_source_mutation_truth_pending_repair",
                        {"fail_closed": True},
                    ),
                ),
            )
        )
    return tuple(rows)


def _purpose_rows(
    current_universe: SourceUniverse, candidate_universe: SourceUniverse
) -> tuple[dict[str, Any], ...]:
    cases = (*current_universe.cases, *candidate_universe.cases)
    by_scenario: dict[str, list[str]] = {}
    for case in cases:
        by_scenario.setdefault(case.scenario_ref, []).append(case.case_ref)
    result: list[dict[str, Any]] = []
    for case in cases:
        classification = {
            "semantic": "semantic_supervision",
            "explicit_gap": "typed_abstention",
            "verification_rejection": "verification_rejection",
            "restart_diagnostic_candidate": "diagnostic_only",
        }[case.source_disposition.value]
        subject_ref = case.case_ref
        branch_applicability = (
            ["retain_typed_proposal_gaps"]
            if case.scenario_ref in _CONDITIONAL_SCENARIOS
            else ["retain_typed_proposal_gaps", "retire_with_reserved_indices"]
        )
        if classification == "diagnostic_only":
            options = (
                _option(
                    subject_ref,
                    "approve_diagnostic_only",
                    {"classification": "diagnostic_only", "purpose": None, "group_ref": None},
                ),
                _option(
                    subject_ref,
                    "reject_pending_replacement",
                    {"classification": None, "purpose": None, "group_ref": None, "fail_closed": True},
                ),
            )
        else:
            group_subject = f"duplicate_candidate:{case.scenario_ref.split(':', 1)[1]}"
            direct_options = tuple(
                _option(
                    subject_ref,
                    f"direct_{purpose}",
                    {"classification": classification, "purpose": purpose, "group_ref": None},
                )
                for purpose in _PURPOSES
            )
            group_options = (
                (
                    _option(
                        subject_ref,
                        "assign_to_reviewed_group",
                        {"classification": classification, "purpose": None, "group_candidate_ref": group_subject},
                    ),
                )
                if len(by_scenario[case.scenario_ref]) > 1
                else ()
            )
            options = (
                *direct_options,
                *group_options,
            )
        result.append(
            _decision(
                row_kind="membership",
                subject_ref=subject_ref,
                fields={
                    "source_case_ref": case.case_ref,
                    "source_classification": (
                        "restart_diagnostic_candidate"
                        if classification == "diagnostic_only"
                        else classification
                    ),
                    "branch_applicability": branch_applicability,
                },
                options=options,
            )
        )
    for scenario_ref, members in sorted(by_scenario.items()):
        if len(members) < 2 or scenario_ref in _RESTART_SCENARIOS:
            continue
        subject_ref = f"duplicate_candidate:{scenario_ref.split(':', 1)[1]}"
        result.append(
            _decision(
                row_kind="duplicate_group",
                subject_ref=subject_ref,
                fields={
                    "scenario_ref": scenario_ref,
                    "member_case_refs": sorted(members),
                    "branch_applicability": _branch_applicability(scenario_ref),
                },
                options=(
                    _option(subject_ref, "reject_group", {"group_ref": None}),
                    *tuple(
                        _option(subject_ref, f"approve_{purpose}", {"namespace": "paraphrase_family", "purpose": purpose})
                        for purpose in _PURPOSES
                    ),
                ),
            )
        )
    topology_cases = {
        "topology:linked": sorted(case.case_ref for case in candidate_universe.cases if case.contract.expected_expressions[0].expression_links),
        "topology:multi_root": sorted(case.case_ref for case in candidate_universe.cases if len(case.contract.expected_expressions[0].root_refs) > 1),
    }
    for identity_ref, members in topology_cases.items():
        result.append(
            _decision(
                row_kind="challenge_holdout",
                subject_ref=f"holdout_candidate:{identity_ref.split(':', 1)[1]}",
                fields={"identity_namespace": "topology", "identity_ref": identity_ref, "member_case_refs": members},
                options=(
                    _option(f"holdout_candidate:{identity_ref.split(':', 1)[1]}", "not_a_holdout", {"purpose": None}),
                    *tuple(
                        _option(
                            f"holdout_candidate:{identity_ref.split(':', 1)[1]}",
                            f"holdout_{purpose}",
                            {"purpose": purpose},
                        )
                        for purpose in _PURPOSES
                    ),
                ),
            )
        )
    for family in _DENOMINATOR_FAMILIES:
        subject_ref = f"denominator:r4_1-{family}"
        result.append(
            _decision(
                row_kind="denominator",
                subject_ref=subject_ref,
                fields={"denominator_family": family},
                options=(
                    _option(subject_ref, "minimum_one_each", {purpose: 1 for purpose in _PURPOSES}),
                ),
            )
        )
    if len(result) > MAX_WORKSHEET_ROWS:
        raise ValueError("purpose worksheet row bound violated")
    return tuple(result)


def _envelope(
    *, schema: str, rows: Sequence[Mapping[str, Any]], inputs: Sequence[Mapping[str, Any]], snapshot: Mapping[str, Any]
) -> dict[str, Any]:
    if not 1 <= len(rows) <= MAX_WORKSHEET_ROWS:
        raise ValueError("worksheet row bound violated")
    input_set_ref = stable_ref("r4_1_review_input_set_v1", list(inputs))
    material = {
        "schema": schema,
        "draft_non_authoritative": True,
        "input_set_ref": input_set_ref,
        "inputs": list(inputs),
        "current_snapshot": dict(snapshot),
        "row_count": len(rows),
        "rows": [dict(row) for row in rows],
    }
    return {
        "schema": schema,
        "worksheet_ref": stable_ref("review_worksheet", material),
        "draft_non_authoritative": True,
        "input_set_ref": input_set_ref,
        "inputs": list(inputs),
        "current_snapshot": dict(snapshot),
        "row_count": len(rows),
        "rows": [dict(row) for row in rows],
    }


def _summary(json_payloads: Mapping[str, bytes], decoded: Mapping[str, Mapping[str, Any]]) -> bytes:
    first = decoded["SOURCE_UNIVERSE.json"]
    legacy_row = next(
        row
        for row in decoded["STRUCTURAL_DECISIONS.json"]["rows"]
        if row["row_kind"] == "legacy_conditional"
    )
    branch_payloads = {
        option["label"]: option["payload"] for option in legacy_row["options"]
    }
    authoring_requirements = sum(
        not option["selectable"]
        for sheet in decoded.values()
        for row in sheet["rows"]
        if row.get("decision_state") == "unresolved"
        for option in row["options"]
    )
    lines = [
        "# R4.1 Source-Readiness Review Worksheets",
        "",
        "> DRAFT — NON-AUTHORITATIVE. No review decision is selected.",
        "",
        f"Input set: `{first['input_set_ref']}`",
        "",
        "| Worksheet | Ref | Bytes | SHA-256 | Rows |",
        "|---|---|---:|---|---:|",
    ]
    for name in sorted(json_payloads):
        raw = json_payloads[name]
        sheet = decoded[name]
        lines.append(
            f"| `{name}` | `{sheet['worksheet_ref']}` | {len(raw)} | `{hashlib.sha256(raw).hexdigest()}` | {sheet['row_count']} |"
        )
    snapshot = first["current_snapshot"]
    lines.extend(
        [
            "",
            f"Current source: {snapshot['reviewed_scenario_count']} scenarios, {snapshot['expanded_case_count']} cases, `{snapshot['source_universe_ref']}`.",
            "",
            "The candidate structural set contains eight unresolved proposals. The legacy conditional and restart decisions remain unresolved.",
            "",
            f"There are {authoring_requirements} explicitly non-selectable authoring requirements. Approval of these draft bytes alone cannot satisfy them; exact ABI records must replace every such placeholder before SR6.",
            "",
            "| Conditional branch | Scenarios | Cases | Source universe | Generator SHA-256 |",
            "|---|---:|---:|---|---|",
            *(
                f"| `{label}` | {payload['scenario_count']} | {payload['case_count']} | `{payload['source_universe_ref']}` | `{payload['result_sha256']}` |"
                for label, payload in sorted(branch_payloads.items())
            ),
            "",
            "`data/review/r4_1/` is intentionally absent. These files do not approve or publish reviewed source.",
            "",
        ]
    )
    raw = "\n".join(lines).encode("utf-8")
    if len(raw) > MAX_WORKSHEET_BYTES:
        raise ValueError("review summary exceeds byte bound")
    return raw


def _build_bytes(repository_root: Path) -> dict[str, bytes]:
    root = Path(repository_root).resolve(strict=True)
    builder_path = (root / "scripts/build_r4_1_review_worksheets.py").resolve(strict=True)
    if builder_path != Path(__file__).resolve(strict=True):
        raise ValueError("worksheet builder does not belong to repository root")
    reviewed = (root / "data/review/r4_1").resolve(strict=False)
    if reviewed.exists():
        raise ValueError("reviewed source output must remain absent during worksheet drafting")
    scenario_raw = _read_regular(
        root / "data/scenarios/use_cases.jsonl", maximum=MAX_INPUT_BYTES, owner="scenario source"
    )
    generator_raw = _read_regular(
        root / "scripts/generate_scenarios.py", maximum=MAX_INPUT_BYTES, owner="generator"
    )
    builder_raw = _read_regular(builder_path, maximum=MAX_INPUT_BYTES, owner="worksheet builder")
    compiler_inputs = tuple(
        (
            relative,
            _read_regular(root / relative, maximum=MAX_INPUT_BYTES, owner="source compiler"),
        )
        for relative in tuple(
            f"src/cemm_authoritative_hybrid/{name}" for name in _COMPILER_MODULES
        )
    )
    _verify_compiler_module_closure(dict(compiler_inputs))
    source_rows, scenarios = _parse_scenarios(scenario_raw)
    if _canonical_scenario_bytes(_execute_generator(generator_raw, owner="current")) != scenario_raw:
        raise ValueError("current generator does not reproduce checked scenario source")
    authority, authority_inputs = _authority_snapshot(root)
    current_universe = expand_reviewed_source_universe(scenarios, authority=authority)
    if _snapshot(current_universe) | {} != {
        "reviewed_scenario_count": 210,
        "expanded_case_count": 400,
        "disposition_counts": {
            "semantic": 248,
            "explicit_gap": 112,
            "verification_rejection": 20,
            "restart_diagnostic": 20,
        },
        "source_universe_ref": current_universe.source_set_ref,
    }:
        raise ValueError("current source universe differs from audited boundary")
    proposal_scenarios = tuple(ReviewedScenario.from_dict(item["scenario"]) for item in _PROPOSALS)
    candidate_universe = expand_reviewed_source_universe(proposal_scenarios, authority=authority)
    provisional = tuple(
        {
            "resulting_scenario_row": item["scenario"],
        }
        for item in _PROPOSALS
    )
    reproduced = reproduce_proposed_scenario_source(
        repository_root=root,
        structural_rows=provisional,
        authority=authority,
        base_generator_source=generator_raw,
    )
    structural_rows = collect_structural_decision_rows(
        candidate_universe=candidate_universe,
        reproduced=reproduced,
        proposal_rows=_PROPOSALS,
        current_universe=current_universe,
    )
    _validate_structural_rows(structural_rows)
    inputs = tuple(
        sorted(
            (
                _input_row("data/scenarios/use_cases.jsonl", scenario_raw),
                _input_row("scripts/generate_scenarios.py", generator_raw),
                _input_row("scripts/build_r4_1_review_worksheets.py", builder_raw),
                *(_input_row(relative, raw) for relative, raw in compiler_inputs),
                *authority_inputs,
            ),
            key=lambda row: row["path"],
        )
    )
    if len(inputs) > MAX_INPUT_FILES or sum(row["byte_length"] for row in inputs) > MAX_INPUT_BYTES:
        raise ValueError("worksheet input set violates bounds")
    snapshot = _snapshot(current_universe)
    source_worksheet_rows = tuple(
        [*(_scenario_row(row, universe="current", change_kind="unchanged") for row in source_rows)]
        + [*(_case_row(case, universe="current") for case in current_universe.cases)]
        + [*(_scenario_row(item["scenario"], universe="candidate", change_kind="added") for item in _PROPOSALS)]
        + [*(_case_row(case, universe="candidate") for case in candidate_universe.cases)]
    )
    worksheets = {
        "SOURCE_UNIVERSE.json": _envelope(schema=_SCHEMAS["SOURCE_UNIVERSE.json"], rows=source_worksheet_rows, inputs=inputs, snapshot=snapshot),
        "STRUCTURAL_DECISIONS.json": _envelope(schema=_SCHEMAS["STRUCTURAL_DECISIONS.json"], rows=structural_rows, inputs=inputs, snapshot=snapshot),
        "SUPERVISION_DECISIONS.json": _envelope(schema=_SCHEMAS["SUPERVISION_DECISIONS.json"], rows=_supervision_rows(current_universe, candidate_universe), inputs=inputs, snapshot=snapshot),
        "PURPOSE_DECISIONS.json": _envelope(schema=_SCHEMAS["PURPOSE_DECISIONS.json"], rows=_purpose_rows(current_universe, candidate_universe), inputs=inputs, snapshot=snapshot),
    }
    json_payloads = {name: _json_bytes(value) for name, value in worksheets.items()}
    result = {**json_payloads, "REVIEW_SUMMARY.md": _summary(json_payloads, worksheets)}
    if sum(map(len, result.values())) > MAX_AGGREGATE_BYTES:
        raise ValueError("worksheet file set exceeds aggregate byte bound")
    return result


def _assert_safe_output(repository_root: Path, output_root: Path) -> Path:
    root = Path(repository_root).resolve(strict=True)
    output = Path(output_root).absolute()
    reviewed = (root / "data/review/r4_1").resolve(strict=False)
    try:
        output.resolve(strict=False).relative_to(reviewed)
    except ValueError:
        pass
    else:
        raise ValueError("worksheet output cannot target reviewed source")
    if output.exists():
        raise ValueError("worksheet output must be absent")
    _trusted_directory(output.parent, owner="worksheet output parent")
    return output


def _trusted_directory(path: Path, *, owner: str) -> os.stat_result:
    directory = Path(path).absolute()
    try:
        metadata = os.lstat(directory)
    except OSError as exc:
        raise ValueError(f"{owner} is missing") from exc
    if not stat.S_ISDIR(metadata.st_mode) or _is_link_or_reparse(metadata):
        raise ValueError(f"{owner} must be a non-link directory")
    for ancestor in directory.parents:
        ancestor_metadata = os.lstat(ancestor)
        if not stat.S_ISDIR(ancestor_metadata.st_mode) or _is_link_or_reparse(ancestor_metadata):
            raise ValueError(f"{owner} has an unsafe ancestor")
    return metadata


def build_review_worksheet_draft(*, repository_root: Path, output_root: Path) -> None:
    output = _assert_safe_output(Path(repository_root), Path(output_root))
    payloads = _build_bytes(Path(repository_root))
    parent_identity = _trusted_directory(output.parent, owner="worksheet output parent")
    output.mkdir(exist_ok=False)
    output_identity = os.lstat(output)
    try:
        for name in _FILES:
            path = output / name
            descriptor = os.open(
                path,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
                0o600,
            )
            try:
                with os.fdopen(descriptor, "wb", closefd=False) as stream:
                    stream.write(payloads[name])
                    stream.flush()
                    os.fsync(stream.fileno())
            finally:
                os.close(descriptor)
    except Exception:
        _cleanup_owned_stage(output, output_identity)
        raise
    if not _same_identity(
        parent_identity,
        _trusted_directory(output.parent, owner="worksheet output parent"),
    ):
        _cleanup_owned_stage(output, output_identity)
        raise ValueError("worksheet output parent identity changed")
    if _tree_bytes(output, owner="written draft") != payloads:
        _cleanup_owned_stage(output, output_identity)
        raise ValueError("written worksheet bytes do not match retained draft")


def _tree_bytes(path: Path, *, owner: str) -> dict[str, bytes]:
    metadata = _trusted_directory(path, owner=f"{owner} candidate")
    entries = _bounded_directory_entries(path, owner=owner)
    names = [entry.name for entry in entries]
    if len(names) != len(set(name.casefold() for name in names)) or set(names) != set(_FILES):
        raise ValueError(f"{owner} candidate file inventory does not match")
    result = {
        name: _read_regular(path / name, maximum=MAX_WORKSHEET_BYTES, owner=f"{owner} candidate")
        for name in _FILES
    }
    if sum(map(len, result.values())) > MAX_AGGREGATE_BYTES:
        raise ValueError(f"{owner} candidate exceeds aggregate byte bound")
    after = _trusted_directory(path, owner=f"{owner} candidate")
    if not _same_identity(metadata, after) or _is_link_or_reparse(after):
        raise ValueError(f"{owner} candidate directory identity changed")
    return result


def _row_fields(schema: str, row_kind: str) -> frozenset[str]:
    common = {"row_ref", "row_kind"}
    if schema == _SCHEMAS["SOURCE_UNIVERSE.json"]:
        if row_kind == "scenario":
            return frozenset(common | {"universe", "change_kind", "scenario_ref", "scenario_sha256", "scenario"})
        if row_kind == "expanded_case":
            return frozenset(common | {"universe", "case_ref", "scenario_ref", "surface_ref", "context_ref", "contract_ref", "surface", "surface_index", "environment_index", "environment_sha256", "language", "trajectory_ref", "turn_index", "source_disposition", "outcome_kind", "expected_expression_relation", "expected_expression_refs", "expanded_case_sha256"})
    decision_common = common | {"subject_ref", "options", "decision_state", "selected_option_ref"}
    structural = {
        "composed_expression_proposal": {"proposal_kind", "semantic_mode", "contains_type_role", "resulting_scenario_row", "designation_spans", "candidate_output", "compiled_candidate", "generator_patch"},
        "conflict_preservation": {"case_refs"},
        "legacy_conditional": {"scenario_refs"},
        "restart_diagnostic": {"scenario_refs", "case_refs"},
        "generator_patch": {"base_path", "base_sha256", "patch_variants", "resulting_scenario_refs"},
    }
    if schema == _SCHEMAS["STRUCTURAL_DECISIONS.json"] and row_kind in structural:
        return frozenset(decision_common | structural[row_kind])
    supervision = {
        "proposal_supervision": {
            "source_case_ref", "scenario_ref", "surface_ref", "language",
            "source_disposition", "branch_applicability", "source_projection",
        },
        "designation_supervision": {
            "source_case_ref", "scenario_ref", "surface_ref", "language",
            "surface", "branch_applicability", "candidate_bindings",
        },
        "realization_supervision": {
            "source_case_ref", "scenario_ref", "surface_ref", "language",
            "branch_applicability", "source_projection",
        },
        "mutation_truth": {
            "source_case_ref", "scenario_ref", "surface_ref", "branch_applicability",
            "source_expected_effect",
        },
    }
    if schema == _SCHEMAS["SUPERVISION_DECISIONS.json"] and row_kind in supervision:
        return frozenset(decision_common | supervision[row_kind])
    purpose = {
        "membership": {"source_case_ref", "source_classification", "branch_applicability"},
        "duplicate_group": {"scenario_ref", "member_case_refs", "branch_applicability"},
        "challenge_holdout": {"identity_namespace", "identity_ref", "member_case_refs"},
        "denominator": {"denominator_family"},
    }
    if schema == _SCHEMAS["PURPOSE_DECISIONS.json"] and row_kind in purpose:
        return frozenset(decision_common | purpose[row_kind])
    raise ValueError("worksheet row kind is unsupported")


def _branch_applicability(scenario_ref: str) -> list[str]:
    if scenario_ref in _CONDITIONAL_SCENARIOS:
        return ["retain_typed_proposal_gaps"]
    return ["retain_typed_proposal_gaps", "retire_with_reserved_indices"]


def _validate_bundle_joins(decoded: Mapping[str, Mapping[str, Any]]) -> None:
    source = decoded["SOURCE_UNIVERSE.json"]
    if source["current_snapshot"].get("reviewed_scenario_count") != 210 or source[
        "current_snapshot"
    ].get("expanded_case_count") != 400:
        raise ValueError("worksheet current source snapshot is not exact")
    if source["current_snapshot"].get("disposition_counts") != {
        "semantic": 248,
        "explicit_gap": 112,
        "verification_rejection": 20,
        "restart_diagnostic": 20,
    }:
        raise ValueError("worksheet current disposition snapshot is not exact")
    if not str(source["current_snapshot"].get("source_universe_ref", "")).startswith(
        "r4_source_set_v1:"
    ):
        raise ValueError("worksheet current source identity is invalid")

    scenarios: dict[tuple[str, str], Mapping[str, Any]] = {}
    cases: dict[str, Mapping[str, Any]] = {}
    cases_by_scenario: dict[str, list[str]] = {}
    source_row_refs: set[str] = set()
    for row in source["rows"]:
        if row["row_ref"] in source_row_refs:
            raise ValueError("source worksheet contains duplicate row identities")
        source_row_refs.add(row["row_ref"])
        if row["row_kind"] == "scenario":
            key = (row["universe"], row["scenario_ref"])
            if key in scenarios or row["universe"] not in {"current", "candidate"}:
                raise ValueError("source worksheet contains duplicate scenario identities")
            if row["change_kind"] != ("unchanged" if row["universe"] == "current" else "added"):
                raise ValueError("source worksheet scenario change kind is invalid")
            if type(row["scenario"]) is not dict or row["scenario"].get("scenario_ref") != row["scenario_ref"]:
                raise ValueError("source worksheet scenario row does not join")
            if row["scenario_sha256"] != hashlib.sha256(_json_bytes(row["scenario"])).hexdigest():
                raise ValueError("source worksheet scenario hash does not match")
            ReviewedScenario.from_dict(row["scenario"])
            scenarios[key] = row
        else:
            if row["case_ref"] in cases or row["universe"] not in {"current", "candidate"}:
                raise ValueError("source worksheet contains duplicate case identities")
            if (row["universe"], row["scenario_ref"]) not in scenarios:
                raise ValueError("source worksheet case does not join its scenario")
            if row["source_disposition"] not in {
                "semantic", "explicit_gap", "verification_rejection", "restart_diagnostic_candidate"
            }:
                raise ValueError("source worksheet case disposition is invalid")
            if (
                not str(row["case_ref"]).startswith("expanded_case_v2:")
                or len(str(row["expanded_case_sha256"])) != 64
                or any(character not in "0123456789abcdef" for character in row["expanded_case_sha256"])
            ):
                raise ValueError("source worksheet case identity is invalid")
            cases[row["case_ref"]] = row
            cases_by_scenario.setdefault(row["scenario_ref"], []).append(row["case_ref"])

    current_scenarios = {ref for universe, ref in scenarios if universe == "current"}
    candidate_scenarios = {ref for universe, ref in scenarios if universe == "candidate"}
    current_cases = [row for row in cases.values() if row["universe"] == "current"]
    candidate_cases = [row for row in cases.values() if row["universe"] == "candidate"]
    expected_proposals = {
        item["scenario"]["scenario_ref"]: item["scenario"] for item in _PROPOSALS
    }
    if len(current_scenarios) != 210 or len(current_cases) != 400:
        raise ValueError("source worksheet current universe is incomplete")
    if candidate_scenarios != set(expected_proposals) or len(candidate_cases) != 8:
        raise ValueError("source worksheet candidate universe is incomplete")
    for scenario_ref, expected in expected_proposals.items():
        if scenarios[("candidate", scenario_ref)]["scenario"] != expected:
            raise ValueError("source worksheet candidate scenario differs from proposal")
    current_counts = {
        kind: sum(row["source_disposition"] == kind for row in current_cases)
        for kind in ("semantic", "explicit_gap", "verification_rejection")
    }
    current_counts["restart_diagnostic"] = sum(
        row["source_disposition"] == "restart_diagnostic_candidate" for row in current_cases
    )
    if current_counts != source["current_snapshot"]["disposition_counts"]:
        raise ValueError("source worksheet case dispositions do not reconstruct snapshot")
    if any(row["source_disposition"] != "semantic" for row in candidate_cases):
        raise ValueError("candidate structural cases must be semantic")

    structural = decoded["STRUCTURAL_DECISIONS.json"]["rows"]
    structural_kinds = [row["row_kind"] for row in structural]
    if len(structural) != 12 or any(
        structural_kinds.count(kind) != count
        for kind, count in {
            "composed_expression_proposal": 8,
            "conflict_preservation": 1,
            "legacy_conditional": 1,
            "restart_diagnostic": 1,
            "generator_patch": 1,
        }.items()
    ):
        raise ValueError("structural worksheet decision inventory is incomplete")
    proposals = {
        row["subject_ref"]: row
        for row in structural
        if row["row_kind"] == "composed_expression_proposal"
    }
    if set(proposals) != set(expected_proposals):
        raise ValueError("structural worksheet proposal identities are incomplete")
    proposal_specs = {item["scenario"]["scenario_ref"]: item for item in _PROPOSALS}
    for scenario_ref, row in proposals.items():
        spec = proposal_specs[scenario_ref]
        if row["resulting_scenario_row"] != spec["scenario"]:
            raise ValueError("structural proposal scenario is not exact")
        surface = spec["scenario"]["surface_examples"][0]
        expected_spans = [
            {"start": start, "end": end, "target_ref": target}
            for start, end, target in spec["designation_spans"]
        ]
        if row["designation_spans"] != expected_spans or row["candidate_output"] != spec["candidate_output"]:
            raise ValueError("structural proposal designation or output differs")
        if not row["candidate_output"].strip() or row["candidate_output"].casefold() == surface.casefold():
            raise ValueError("structural proposal output is empty or an input echo")
        if any(surface[item["start"] : item["end"]] == "" for item in row["designation_spans"]):
            raise ValueError("structural proposal designation span is empty")
    legacy = next(row for row in structural if row["row_kind"] == "legacy_conditional")
    legacy_options = {option["label"]: option["payload"] for option in legacy["options"]}
    if set(legacy_options) != {"retain_typed_proposal_gaps", "retire_with_reserved_indices"}:
        raise ValueError("legacy conditional options are incomplete")
    for label, scenario_count, case_count, counts in (
        ("retain_typed_proposal_gaps", 218, 408, {"semantic": 256, "explicit_gap": 112, "verification_rejection": 20, "restart_diagnostic": 20}),
        ("retire_with_reserved_indices", 216, 404, {"semantic": 256, "explicit_gap": 108, "verification_rejection": 20, "restart_diagnostic": 20}),
    ):
        payload = legacy_options[label]
        if (
            payload.get("path") != "scripts/generate_scenarios.py"
            or payload.get("scenario_count") != scenario_count
            or payload.get("case_count") != case_count
            or payload.get("disposition_counts") != counts
            or not str(payload.get("source_universe_ref", "")).startswith("r4_source_set_v1:")
            or any(len(str(payload.get(field, ""))) != 64 for field in ("base_sha256", "result_sha256", "scenario_source_sha256"))
            or not str(payload.get("unified_diff", "")).startswith("--- a/scripts/generate_scenarios.py\n")
        ):
            raise ValueError("legacy conditional patch variant is incomplete")

    supervised = {
        ref: row
        for ref, row in cases.items()
        if row["source_disposition"] != "restart_diagnostic_candidate"
    }
    supervision = decoded["SUPERVISION_DECISIONS.json"]["rows"]
    by_case_and_kind: dict[tuple[str, str], Mapping[str, Any]] = {}
    for row in supervision:
        key = (row["source_case_ref"], row["row_kind"])
        if key in by_case_and_kind or row["source_case_ref"] not in supervised:
            raise ValueError("supervision worksheet case ownership is invalid")
        source_case = supervised[row["source_case_ref"]]
        if row["scenario_ref"] != source_case["scenario_ref"] or row["surface_ref"] != source_case["surface_ref"]:
            raise ValueError("supervision worksheet source join does not match")
        if row["branch_applicability"] != _branch_applicability(row["scenario_ref"]):
            raise ValueError("supervision worksheet branch applicability is invalid")
        by_case_and_kind[key] = row
    required_supervision_kinds = {
        "proposal_supervision", "designation_supervision", "realization_supervision", "mutation_truth"
    }
    if len(supervision) != len(supervised) * len(required_supervision_kinds) or {
        key for key in by_case_and_kind
    } != {(case_ref, kind) for case_ref in supervised for kind in required_supervision_kinds}:
        raise ValueError("supervision worksheet decision inventory is incomplete")
    for case_ref, source_case in supervised.items():
        designation = by_case_and_kind[(case_ref, "designation_supervision")]
        realization = by_case_and_kind[(case_ref, "realization_supervision")]
        proposal_spec = proposal_specs.get(source_case["scenario_ref"])
        expected_bindings = [] if proposal_spec is None else [
            {
                "surface": proposal_spec["scenario"]["surface_examples"][0][start:end],
                "start": start,
                "end": end,
                "candidate_target_ref": target,
            }
            for start, end, target in proposal_spec["designation_spans"]
        ]
        if designation["candidate_bindings"] != expected_bindings:
            raise ValueError("designation candidate bindings differ from structural proposal")
        candidate_surface = realization["source_projection"]["candidate_surface"]
        expected_surface = None if proposal_spec is None else proposal_spec["candidate_output"]
        if candidate_surface != expected_surface:
            raise ValueError("realization candidate surface differs from structural proposal")

    purpose = decoded["PURPOSE_DECISIONS.json"]["rows"]
    memberships = [row for row in purpose if row["row_kind"] == "membership"]
    if len(memberships) != len(cases) or {row["source_case_ref"] for row in memberships} != set(cases):
        raise ValueError("purpose membership inventory is incomplete")
    for row in memberships:
        case = cases[row["source_case_ref"]]
        if row["branch_applicability"] != _branch_applicability(case["scenario_ref"]):
            raise ValueError("purpose membership branch applicability is invalid")
        expected_classification = {
            "semantic": "semantic_supervision",
            "explicit_gap": "typed_abstention",
            "verification_rejection": "verification_rejection",
            "restart_diagnostic_candidate": "restart_diagnostic_candidate",
        }[case["source_disposition"]]
        if row["source_classification"] != expected_classification:
            raise ValueError("purpose membership source classification is invalid")
    duplicate_rows = [row for row in purpose if row["row_kind"] == "duplicate_group"]
    expected_duplicates = {
        scenario_ref: sorted(member_refs)
        for scenario_ref, member_refs in cases_by_scenario.items()
        if len(member_refs) > 1 and scenario_ref not in _RESTART_SCENARIOS
    }
    if len(duplicate_rows) != len(expected_duplicates) or any(
        row["member_case_refs"] != expected_duplicates.get(row["scenario_ref"])
        or row["branch_applicability"] != _branch_applicability(row["scenario_ref"])
        for row in duplicate_rows
    ):
        raise ValueError("purpose duplicate-group candidates are incomplete")
    denominators = [row for row in purpose if row["row_kind"] == "denominator"]
    if {row["denominator_family"] for row in denominators} != set(_DENOMINATOR_FAMILIES) or len(denominators) != len(_DENOMINATOR_FAMILIES):
        raise ValueError("purpose denominator inventory is incomplete")
    if any(len(row["options"]) != 1 or row["options"][0]["payload"] != {purpose_ref: 1 for purpose_ref in _PURPOSES} for row in denominators):
        raise ValueError("purpose denominator minima are not exact")
    holdouts = [row for row in purpose if row["row_kind"] == "challenge_holdout"]
    if {row["identity_ref"] for row in holdouts} != {"topology:linked", "topology:multi_root"} or len(holdouts) != 2:
        raise ValueError("purpose topology holdouts are incomplete")


def _validate_file_set_bytes(payloads: Mapping[str, bytes]) -> dict[str, Mapping[str, Any]]:
    if set(payloads) != set(_FILES):
        raise ValueError("worksheet file set does not match")
    decoded: dict[str, Mapping[str, Any]] = {}
    snapshot: object | None = None
    input_set_ref: object | None = None
    shared_inputs: object | None = None
    for name in _JSON_FILES:
        raw = payloads[name]
        value = _strict_json(raw, owner=name)
        if type(value) is not dict or set(value) != _ENVELOPE_FIELDS:
            raise ValueError("worksheet envelope fields do not match")
        if value["schema"] != _SCHEMAS[name] or value["draft_non_authoritative"] is not True:
            raise ValueError("worksheet schema or draft marker is invalid")
        if type(value["rows"]) is not list or value["row_count"] != len(value["rows"]):
            raise ValueError("worksheet row count does not match")
        if not 1 <= len(value["rows"]) <= MAX_WORKSHEET_ROWS:
            raise ValueError("worksheet row bound violated")
        for row in value["rows"]:
            if type(row) is not dict or set(row) != _row_fields(value["schema"], row.get("row_kind")):
                raise ValueError("worksheet row fields do not match")
            identity = dict(row)
            row_ref = identity.pop("row_ref")
            if row_ref != stable_ref("review_worksheet_row", identity):
                raise ValueError("worksheet row hash does not match")
            if name != "SOURCE_UNIVERSE.json" and (
                row["decision_state"] != "unresolved" or row["selected_option_ref"] is not None
            ):
                raise ValueError("worksheet decision must remain unresolved")
            if name != "SOURCE_UNIVERSE.json":
                if type(row["options"]) is not list or not row["options"]:
                    raise ValueError("worksheet decision options must be nonempty")
                option_refs: set[str] = set()
                for option in row["options"]:
                    if type(option) is not dict or set(option) != {
                        "option_ref", "label", "payload", "selectable"
                    }:
                        raise ValueError("worksheet option fields do not match")
                    if type(option["selectable"]) is not bool:
                        raise ValueError("worksheet option selectable marker is invalid")
                    material = {
                        "subject_ref": row["subject_ref"],
                        "label": option["label"],
                        "payload": option["payload"],
                        "selectable": option["selectable"],
                    }
                    if option["option_ref"] != stable_ref("review_worksheet_option", material):
                        raise ValueError("worksheet option hash does not match")
                    if option["option_ref"] in option_refs:
                        raise ValueError("worksheet contains duplicate option identities")
                    option_refs.add(option["option_ref"])
        if _json_bytes(value) != raw:
            raise ValueError("worksheet canonical bytes do not match")
        material = dict(value)
        worksheet_ref = material.pop("worksheet_ref")
        if worksheet_ref != stable_ref("review_worksheet", material):
            raise ValueError("worksheet hash does not match")
        expected_input_ref = stable_ref("r4_1_review_input_set_v1", value["inputs"])
        if value["input_set_ref"] != expected_input_ref:
            raise ValueError("worksheet input-set hash does not match")
        if snapshot is None:
            snapshot = value["current_snapshot"]
            input_set_ref = value["input_set_ref"]
            shared_inputs = value["inputs"]
        elif (
            value["current_snapshot"] != snapshot
            or value["input_set_ref"] != input_set_ref
            or value["inputs"] != shared_inputs
        ):
            raise ValueError("worksheet snapshots or inputs do not match")
        decoded[name] = value
    if payloads["REVIEW_SUMMARY.md"] != _summary(
        {name: payloads[name] for name in _JSON_FILES}, decoded
    ):
        raise ValueError("review summary does not match worksheet bytes")
    _validate_structural_rows(decoded["STRUCTURAL_DECISIONS.json"]["rows"])
    _validate_bundle_joins(decoded)
    return decoded


def _validate_bound_repository_inputs(
    *, decoded: Mapping[str, Mapping[str, Any]], repository_root: Path
) -> dict[str, bytes]:
    root = Path(repository_root).resolve(strict=True)
    inputs = decoded["SOURCE_UNIVERSE.json"]["inputs"]
    if type(inputs) is not list or not 1 <= len(inputs) <= MAX_INPUT_FILES:
        raise ValueError("worksheet input list violates bounds")
    retained: dict[str, bytes] = {}
    aggregate = 0
    for row in inputs:
        if type(row) is not dict or set(row) != {"path", "byte_length", "sha256"}:
            raise ValueError("worksheet input fields do not match")
        path = row["path"]
        if type(path) is not str or Path(path).is_absolute() or ".." in Path(path).parts:
            raise ValueError("worksheet input path is unsafe")
        lowered_parts = {part.casefold() for part in Path(path).parts}
        if (
            path in retained
            or "artifacts" in lowered_parts
            or "review" in lowered_parts
            or lowered_parts & {"runtime.py", "bootstrap.py", "episode.py", "model.py", "solver.py"}
        ):
            raise ValueError("worksheet input path is forbidden or duplicated")
        raw = _read_regular(root / path, maximum=MAX_INPUT_BYTES, owner="worksheet input")
        if len(raw) != row["byte_length"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("worksheet input hash does not match")
        retained[path] = raw
        aggregate += len(raw)
        if aggregate > MAX_INPUT_BYTES:
            raise ValueError("worksheet input bytes exceed aggregate bound")
    required_inputs = {
        "data/scenarios/use_cases.jsonl",
        "scripts/generate_scenarios.py",
        "scripts/build_r4_1_review_worksheets.py",
        *(f"src/cemm_authoritative_hybrid/{name}" for name in _COMPILER_MODULES),
        "data/authority/manifest.json",
    }
    manifest = _strict_json(
        retained.get("data/authority/manifest.json", b""),
        owner="worksheet authority manifest input",
    )
    if type(manifest) is not dict or type(manifest.get("owners")) is not list:
        raise ValueError("worksheet authority manifest input is invalid")
    authority_paths = set()
    for owner in manifest["owners"]:
        if type(owner) is not dict or type(owner.get("path")) is not str:
            raise ValueError("worksheet authority owner input is invalid")
        authority_paths.add(f"data/authority/{owner['path']}")
    if set(retained) != required_inputs | authority_paths:
        raise ValueError("worksheet compiler input set is not exact")
    _verify_compiler_module_closure(retained)
    return retained


def _authority_from_retained_inputs(retained: Mapping[str, bytes]) -> LinkedAuthority:
    manifest_path = "data/authority/manifest.json"
    manifest = _strict_json(retained[manifest_path], owner="retained authority manifest")
    if type(manifest) is not dict or type(manifest.get("owners")) is not list:
        raise ValueError("retained authority manifest shape is invalid")
    expected_paths = {manifest_path}
    for owner in manifest["owners"]:
        if type(owner) is not dict or set(owner) != {"name", "path", "sha256"}:
            raise ValueError("retained authority owner row is invalid")
        relative = owner["path"]
        path = f"data/authority/{relative}"
        expected_paths.add(path)
        raw = retained.get(path)
        if raw is None or hashlib.sha256(raw).hexdigest() != owner["sha256"]:
            raise ValueError("retained authority owner bytes do not match manifest")
    actual_paths = {path for path in retained if path.startswith("data/authority/")}
    if actual_paths != expected_paths:
        raise ValueError("retained authority input inventory is not exact")
    with tempfile.TemporaryDirectory(prefix="cemm-r4-1-validate-authority-") as temp:
        snapshot = Path(temp)
        for path in sorted(expected_paths):
            relative = Path(path).relative_to("data/authority")
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(retained[path])
        return AuthorityLinker().link_path(snapshot / "manifest.json")


def _validate_repository_semantics(
    *, decoded: Mapping[str, Mapping[str, Any]], retained: Mapping[str, bytes]
) -> None:
    scenario_raw = retained["data/scenarios/use_cases.jsonl"]
    generator_raw = retained["scripts/generate_scenarios.py"]
    source_rows, scenarios = _parse_scenarios(scenario_raw)
    if _canonical_scenario_bytes(_execute_generator(generator_raw, owner="validated-current")) != scenario_raw:
        raise ValueError("bound generator does not reproduce bound scenario source")
    authority = _authority_from_retained_inputs(retained)
    current_universe = expand_reviewed_source_universe(scenarios, authority=authority)
    if decoded["SOURCE_UNIVERSE.json"]["current_snapshot"] != _snapshot(current_universe):
        raise ValueError("worksheet current snapshot does not reconstruct bound source")
    candidate_scenarios = tuple(
        ReviewedScenario.from_dict(item["scenario"]) for item in _PROPOSALS
    )
    candidate_universe = expand_reviewed_source_universe(
        candidate_scenarios,
        authority=authority,
    )
    structural_proposals = tuple(
        {"resulting_scenario_row": item["scenario"]} for item in _PROPOSALS
    )
    reproduced = reproduce_proposed_scenario_source(
        repository_root=ROOT,
        structural_rows=structural_proposals,
        authority=authority,
        base_generator_source=generator_raw,
    )
    expected_source_rows = tuple(
        [*(_scenario_row(row, universe="current", change_kind="unchanged") for row in source_rows)]
        + [*(_case_row(case, universe="current") for case in current_universe.cases)]
        + [*(_scenario_row(item["scenario"], universe="candidate", change_kind="added") for item in _PROPOSALS)]
        + [*(_case_row(case, universe="candidate") for case in candidate_universe.cases)]
    )
    if decoded["SOURCE_UNIVERSE.json"]["rows"] != list(expected_source_rows):
        raise ValueError("worksheet source rows do not reconstruct bound source")
    expected_structural = collect_structural_decision_rows(
        candidate_universe=candidate_universe,
        reproduced=reproduced,
        proposal_rows=_PROPOSALS,
        current_universe=current_universe,
    )
    if decoded["STRUCTURAL_DECISIONS.json"]["rows"] != list(expected_structural):
        raise ValueError("worksheet structural decisions do not reconstruct bound source")
    expected_supervision = _supervision_rows(current_universe, candidate_universe)
    if decoded["SUPERVISION_DECISIONS.json"]["rows"] != list(expected_supervision):
        raise ValueError("worksheet supervision decisions do not reconstruct bound source")
    expected_purpose = _purpose_rows(current_universe, candidate_universe)
    if decoded["PURPOSE_DECISIONS.json"]["rows"] != list(expected_purpose):
        raise ValueError("worksheet purpose decisions do not reconstruct bound source")
    for item in _PROPOSALS:
        surface = item["scenario"]["surface_examples"][0]
        for start, end, target in item["designation_spans"]:
            sliced = surface[start:end]
            if target not in authority.atoms or target not in authority.designations.for_surface(sliced, "en"):
                raise ValueError("structural designation proposal is not exact authority evidence")


def validate_review_worksheet_draft(*, repository_root: Path, draft_root: Path) -> None:
    payloads = _tree_bytes(Path(draft_root), owner="draft")
    decoded = _validate_file_set_bytes(payloads)
    retained = _validate_bound_repository_inputs(
        decoded=decoded,
        repository_root=Path(repository_root),
    )
    _validate_repository_semantics(decoded=decoded, retained=retained)


def _write_stage(stage: Path, payloads: Mapping[str, bytes]) -> None:
    for name in _FILES:
        descriptor = os.open(
            stage / name,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0),
            0o600,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=False) as stream:
                stream.write(payloads[name])
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            os.close(descriptor)


def _cleanup_owned_stage(stage: Path, identity: os.stat_result) -> None:
    if not stage.exists():
        return
    current = os.lstat(stage)
    if not _same_identity(current, identity) or not stat.S_ISDIR(current.st_mode) or _is_link_or_reparse(current):
        raise ValueError("publication stage identity changed; refusing cleanup")
    for name in _FILES:
        path = stage / name
        if path.exists() or path.is_symlink():
            metadata = os.lstat(path)
            if not stat.S_ISREG(metadata.st_mode) or _is_link_or_reparse(metadata):
                raise ValueError("publication stage contains unsafe file; refusing cleanup")
            path.unlink()
    if _bounded_directory_entries(stage, owner="publication stage"):
        raise ValueError("publication stage contains unexpected files; refusing cleanup")
    stage.rmdir()


def _rename_directory_no_replace(source: Path, target: Path) -> None:
    if os.name == "nt":
        os.rename(source, target)
        return
    if sys.platform == "linux":
        import ctypes

        libc = ctypes.CDLL(None, use_errno=True)
        renameat2 = getattr(libc, "renameat2", None)
        if renameat2 is None:
            raise OSError(errno.ENOSYS, "renameat2 is unavailable")
        renameat2.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        renameat2.restype = ctypes.c_int
        at_fdcwd = -100
        rename_noreplace = 1
        if renameat2(
            at_fdcwd,
            os.fsencode(source),
            at_fdcwd,
            os.fsencode(target),
            rename_noreplace,
        ) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), str(target))
        return
    raise OSError(errno.ENOTSUP, "atomic no-replace directory rename is unsupported")


def publish_verified_review_worksheet_draft(
    *, candidate_a: Path, candidate_b: Path, final_root: Path, repository_root: Path = ROOT
) -> None:
    candidate_a_path = Path(candidate_a).absolute()
    candidate_b_path = Path(candidate_b).absolute()
    candidate_a_identity = _trusted_directory(candidate_a_path, owner="candidate A")
    candidate_b_identity = _trusted_directory(candidate_b_path, owner="candidate B")
    try:
        same_candidate = os.path.samefile(candidate_a_path, candidate_b_path)
    except OSError:
        same_candidate = False
    if same_candidate:
        raise ValueError("candidate A and B must be independent directories")
    final = Path(final_root).absolute()
    final_parent = final.parent
    for candidate in (candidate_a_path, candidate_b_path):
        if candidate == final or candidate in final.parents or final in candidate.parents:
            raise ValueError("candidate and final paths must not overlap")
    parent_identity = _trusted_directory(final_parent, owner="publication parent")
    a = _tree_bytes(candidate_a_path, owner="A")
    b = _tree_bytes(candidate_b_path, owner="B")
    decoded_a = _validate_file_set_bytes(a)
    _validate_file_set_bytes(b)
    if a != b:
        raise ValueError("candidate A and B bytes do not match")
    retained = _validate_bound_repository_inputs(
        decoded=decoded_a,
        repository_root=Path(repository_root),
    )
    _validate_repository_semantics(decoded=decoded_a, retained=retained)
    if final.exists() or final.is_symlink():
        existing = _tree_bytes(final, owner="existing final")
        if existing != a:
            raise ValueError("existing final bytes do not match verified candidate")
        return
    stage = Path(tempfile.mkdtemp(prefix=f".{final.name}.", dir=final.parent))
    identity = os.lstat(stage)
    try:
        _write_stage(stage, a)
        if _tree_bytes(stage, owner="staged") != a:
            raise ValueError("staged bytes do not match candidate A")
        if _tree_bytes(candidate_a_path, owner="A") != a or _tree_bytes(candidate_b_path, owner="B") != a:
            raise ValueError("candidate files changed before publication")
        if not _same_identity(
            candidate_a_identity,
            _trusted_directory(candidate_a_path, owner="candidate A"),
        ) or not _same_identity(
            candidate_b_identity,
            _trusted_directory(candidate_b_path, owner="candidate B"),
        ):
            raise ValueError("candidate directory identity changed before publication")
        if not _same_identity(
            parent_identity,
            _trusted_directory(final_parent, owner="publication parent"),
        ):
            raise ValueError("publication parent identity changed")
        try:
            _rename_directory_no_replace(stage, final)
        except OSError as exc:
            if final.exists() and _tree_bytes(final, owner="raced final") == a:
                _cleanup_owned_stage(stage, identity)
                return
            raise ValueError("cannot publish to an absent final directory") from exc
        if _tree_bytes(final, owner="final") != a:
            raise ValueError("published final bytes do not match candidate A")
    except Exception:
        if stage.exists():
            _cleanup_owned_stage(stage, identity)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--publish-a", type=Path)
    parser.add_argument("--verify-b", type=Path)
    parser.add_argument("--final", type=Path)
    args = parser.parse_args(argv)
    publish_values = (args.publish_a, args.verify_b, args.final)
    if args.output is not None and any(value is not None for value in publish_values):
        parser.error("--output cannot be combined with publication options")
    if args.output is not None:
        build_review_worksheet_draft(repository_root=args.root, output_root=args.output)
        return 0
    if all(value is not None for value in publish_values):
        publish_verified_review_worksheet_draft(
            candidate_a=args.publish_a,
            candidate_b=args.verify_b,
            final_root=args.final,
            repository_root=args.root,
        )
        return 0
    parser.error("provide --output or all publication options")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
