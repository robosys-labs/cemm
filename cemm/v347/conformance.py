"""Executable architecture-conformance gate for CEMM v3.4.7."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
import re
from typing import Iterable

VERSION = "3.4.7"
LEGACY_AUTHORITIES = {
    "SemanticForestComposer",
    "CanonicalSemanticComposer",
    "CanonicalInterpretationResolver",
    "ContextualInterpretationResolver",
    "DeclarativeConstructionMatcher",
    "SemanticMessagePlan",
}
CANONICAL_UOL_NAMES = {
    "Referent", "Predication", "PortBinding", "UOLGraph", "MeaningHypothesis",
    "MeaningBundle", "GraphPatch", "UOLResponsePlan", "EmissionProof",
}


def check(root: Path) -> dict[str, object]:
    root = root.resolve()
    findings: list[str] = []
    checks: list[str] = []

    _check_version(root, findings); checks.append("single-version-manifest")
    _check_authority_imports(root, findings); checks.append("legacy-authority-import-ban")
    _check_foundation(root, findings); checks.append("language-neutral-foundation")
    _check_language_ownership(root, findings); checks.append("language-pack-only-surfaces")
    _check_uol_authority(root, findings); checks.append("single-uol-model-authority")
    _check_store_writes(root, findings); checks.append("graphpatch-only-durable-write")
    _check_docs(root, findings); checks.append("governing-document-supersession")
    _check_runtime(root, findings); checks.append("canonical-runtime-cutover")

    return {"root": str(root), "ok": not findings, "checks": checks, "findings": findings}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _check_version(root: Path, findings: list[str]) -> None:
    required = [root / "pyproject.toml", root / "AGENTS.md", root / "architecture.md", root / "coreloop.md"]
    for path in required:
        if not path.is_file():
            findings.append(f"missing_governing_file:{path.relative_to(root)}")
            continue
        if VERSION not in _text(path):
            findings.append(f"version_missing:{path.relative_to(root)}")
    pyproject = _text(root / "pyproject.toml")
    if 'version = "3.4.7"' not in pyproject:
        findings.append("pyproject_version_not_3.4.7")
    if "setuptools.build_meta" not in pyproject:
        findings.append("unsupported_build_backend")


def _python_files(root: Path) -> Iterable[Path]:
    for base in (root / "cemm" / "v347", root / "cemm" / "app"):
        if base.is_dir():
            yield from sorted(base.rglob("*.py"))


def _check_authority_imports(root: Path, findings: list[str]) -> None:
    for path in _python_files(root):
        if path.name == "conformance.py":
            continue
        text = _text(path)
        for name in LEGACY_AUTHORITIES:
            if name in text:
                findings.append(f"legacy_authority_reference:{path.relative_to(root)}:{name}")
        if re.search(r"from\s+\.\.?kernel\.(understanding|response)", text):
            findings.append(f"legacy_kernel_import:{path.relative_to(root)}")


def _check_foundation(root: Path, findings: list[str]) -> None:
    path = root / "cemm" / "data" / "v347" / "foundation.json"
    if not path.is_file():
        findings.append("missing_foundation_package")
        return
    data = json.loads(_text(path))
    forbidden = {"surface", "surfaces", "template", "templates", "words", "phrases"}
    stack = [("$", data)]
    while stack:
        where, value = stack.pop()
        if isinstance(value, dict):
            for key, child in value.items():
                if key in forbidden:
                    findings.append(f"foundation_surface_field:{where}.{key}")
                stack.append((f"{where}.{key}", child))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                stack.append((f"{where}[{index}]", child))
    if data.get("version") != VERSION:
        findings.append("foundation_version_mismatch")


def _check_language_ownership(root: Path, findings: list[str]) -> None:
    lang_root = root / "cemm" / "data" / "v347" / "languages"
    tags = set()
    for path in sorted(lang_root.glob("*.json")):
        data = json.loads(_text(path))
        tag = data.get("language_tag")
        tags.add(tag)
        if not data.get("lexical_entries"):
            findings.append(f"empty_lexical_package:{path.name}")
        realization = data.get("realization") or {}
        if not realization.get("predicate_answers") or not realization.get("response_moves"):
            findings.append(f"incomplete_realization_package:{path.name}")
    if not {"en", "fr", "sw"}.issubset(tags):
        findings.append("required_language_packages_missing")


def _check_uol_authority(root: Path, findings: list[str]) -> None:
    model_path = root / "cemm" / "v347" / "model.py"
    model_text = _text(model_path)
    for name in CANONICAL_UOL_NAMES:
        if not re.search(rf"class\s+{re.escape(name)}\b", model_text):
            findings.append(f"canonical_uol_definition_missing:{name}")
    uol_root = root / "cemm" / "uol"
    for path in sorted(uol_root.glob("*.py")):
        if path.name == "__init__.py":
            continue
        tree = ast.parse(_text(path), filename=str(path))
        for node in tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                findings.append(f"duplicate_uol_authority:{path.relative_to(root)}:{node.name}")


def _check_store_writes(root: Path, findings: list[str]) -> None:
    for path in _python_files(root):
        if path.name == "storage.py":
            continue
        text = _text(path)
        if re.search(r"\b(?:INSERT|UPDATE|DELETE)\s+(?:INTO|FROM|[A-Za-z_])", text, re.I):
            findings.append(f"direct_sql_outside_store:{path.relative_to(root)}")
        if ".commit()" in text and "semantic_store.apply_patch" not in text and path.name != "runtime.py":
            findings.append(f"direct_commit_outside_patch_boundary:{path.relative_to(root)}")


def _check_docs(root: Path, findings: list[str]) -> None:
    for name in ("SEMANTIC_DATA_MODEL.md", "UNDERSTANDING_PIPELINE.md", "LEARNING_PIPELINE.md", "SEMANTIC_FOUNDATIONS.md", "AUTHORITY_MATRIX.md", "ARCHITECTURE_DECISIONS.md"):
        text = _text(root / "cemm" / "newarch" / name)
        if "non-authoritative compatibility pointer" not in text:
            findings.append(f"old_architecture_not_superseded:{name}")


def _check_runtime(root: Path, findings: list[str]) -> None:
    app_runtime = _text(root / "cemm" / "app" / "runtime.py")
    if "cemm.v347.runtime" not in app_runtime and "..v347.runtime" not in app_runtime:
        findings.append("public_runtime_not_cut_over")
    runtime = _text(root / "cemm" / "v347" / "runtime.py")
    required = ("LanguageAnalysisCoordinator", "UnderstandingCoordinator", "EpistemicCoordinator", "ResponseGoalGenerator", "UOLResponsePlanner", "RealizationCoordinator")
    for name in required:
        if name not in runtime:
            findings.append(f"canonical_runtime_component_missing:{name}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args(argv)
    result = check(Path(args.root))
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
