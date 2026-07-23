#!/usr/bin/env python3
"""Structural Phase-17/18 verifier. Release evidence gates remain separate and fail closed."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys


LEGACY_PREFIXES = (
    "cemm.v347", "cemm.migration", "cemm.v350.migration", "cemm.v350.uol",
    "cemm.v350.runtime_hardening", "cemm.v350.runtime_services", "cemm.v350.activation_services",
)
PUBLIC_ROOTS = ("cemm/__init__.py", "cemm/__main__.py", "cemm/app/runtime.py", "cemm/web_demo.py")


def _module_for_path(root: Path, path: Path) -> str | None:
    try:
        rel = path.relative_to(root).with_suffix("")
    except ValueError:
        return None
    parts = list(rel.parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else None


def _resolve_from(package_name: str, level: int, imported: str | None) -> str | None:
    if level == 0:
        return imported
    parts = package_name.split(".") if package_name else []
    up = level - 1
    if up > len(parts):
        return None
    base = parts[: len(parts) - up]
    if imported:
        base.extend(imported.split("."))
    return ".".join(part for part in base if part)


def imported_modules(root: Path, path: Path):
    module_name = _module_for_path(root, path) or ""
    package_name = module_name if path.name == "__init__.py" else module_name.rpartition(".")[0]
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            resolved = _resolve_from(package_name, int(node.level or 0), node.module)
            if resolved:
                result.append(resolved)
                # Imported names may themselves be submodules (``from .pkg import child``).
                # Queueing these candidates is harmless for symbols because _module_path filters them.
                result.extend(
                    f"{resolved}.{alias.name}" for alias in node.names if alias.name != "*"
                )
    return tuple(dict.fromkeys(result))


def _module_path(root: Path, module: str) -> Path | None:
    if not module.startswith("cemm"):
        return None
    base = root.joinpath(*module.split("."))
    file_path = base.with_suffix(".py")
    if file_path.is_file():
        return file_path
    init_path = base / "__init__.py"
    return init_path if init_path.is_file() else None


def legacy_import_scan(root: Path):
    """Scan only the transitive public/canonical runtime import graph.

    Historical/quarantined files are allowed to exist. They become a release blocker only when
    a public entrypoint or canonical runtime module can actually reach them through imports.
    """
    seed_paths = [root / rel for rel in PUBLIC_ROOTS]
    seed_paths.extend([
        root / "cemm/v350/runtime_v351.py",
        root / "cemm/v350/orchestration.py",
        root / "cemm/v350/cutover.py",
        root / "cemm/v350/service_loader.py",
    ])
    queue = [path for path in seed_paths if path.is_file()]
    visited: set[Path] = set()
    findings = []
    while queue:
        path = queue.pop(0).resolve()
        if path in visited:
            continue
        visited.add(path)
        rel = path.relative_to(root).as_posix()
        for name in imported_modules(root, path):
            if any(name == prefix or name.startswith(prefix + ".") for prefix in LEGACY_PREFIXES):
                findings.append({"path": rel, "module": name})
                continue
            dependency = _module_path(root, name)
            if dependency is not None and dependency.resolve() not in visited:
                queue.append(dependency)
    return sorted(findings, key=lambda item: (item["path"], item["module"]))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check(condition, label, failures):
    if not condition:
        failures.append(label)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, default=Path("."))
    parser.add_argument("--boot-database", type=Path, help="exact boot.sqlite used by this verification run")
    parser.add_argument("--run-tests", action="store_true")
    parser.add_argument("--full-tests", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    sys.path.insert(0, str(root))
    failures = []

    from cemm.v350.stage_contracts import CoreStage, canonical_stage_contracts
    from cemm.v350.finalization.service_authority_v351 import canonical_service_authorities_v351
    from cemm.v350.finalization.source_attestation_v351 import runtime_source_root_v351
    from cemm.v350.storage import RecordKind

    check(len(tuple(CoreStage)) == 23, "CoreStage is not exact Stage 0..22", failures)
    check(len(canonical_stage_contracts()) == 23, "stage contract graph is not 23 stages", failures)
    authorities = canonical_service_authorities_v351()
    slots = {item.service_kind for item in authorities}
    for required in {
        "csir_compiler", "recurrent_semantic_solver", "semantic_attractor_stabilizer",
        "operation_engine", "operation_outcome_assimilator", "response_csir_builder",
        "realization_engine", "emission_engine", "output_discourse_engine", "consolidation_engine",
    }:
        check(required in slots, f"missing canonical service authority:{required}", failures)
    for item in authorities:
        check(item.runtime_abi == "v351", f"non-final runtime ABI:{item.service_kind}", failures)

    runtime_text = (root / "cemm/v350/runtime_v351.py").read_text(encoding="utf-8")
    check("observations=" in runtime_text or "envelope.observations" in runtime_text, "typed RuntimeInput observations not wired", failures)
    check("prepare_nonlexical_multimodal_grounding_v351" in runtime_text, "multimodal-only grounding not wired", failures)
    check("CanonicalOperationOutcomeAssimilatorV351" in runtime_text, "canonical operation result recurrence not wired", failures)
    check("CanonicalCycleFinalizerV351" in runtime_text, "canonical Stage22 finalizer not wired", failures)
    check("self._resolved_service(\"operation_engine\")" in runtime_text, "Stage16 bypasses canonical service resolver", failures)

    compiler_text = (root / "cemm/v350/dynamics/compiler_v351.py").read_text(encoding="utf-8")
    check("dependence" in compiler_text.casefold() and "MessageFamily.MULTIMODAL" in compiler_text, "dependence-aware multimodal recurrent bridge missing", failures)
    sw_text = (root / "cemm/v350/language/minimum_swahili_v351.py").read_text(encoding="utf-8")
    check("ConstructionProgramOperation" in sw_text and "shared_semantic_slots" in sw_text.casefold(), "Swahili package bypasses shared generic semantics", failures)

    findings = legacy_import_scan(root)
    check(not findings, "legacy imports remain in canonical/public Python graph:" + repr(findings[:20]), failures)

    manifest_path = root / "cemm/data/v350/runtime_authority_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("activation_ready"):
        check(int(manifest.get("manifest_version", 0)) >= 5, "activation-ready manifest is pre-v5", failures)
        check(bool(manifest.get("closure_ledger_sha256")), "activation-ready manifest lacks closure ledger", failures)
        check(bool((manifest.get("detached_signature") or {}).get("sha256")), "activation-ready manifest lacks detached signature", failures)
    allowed = set(manifest.get("allowed_record_kinds", ()))
    legacy_record = {item.value for item in RecordKind if item.value.startswith("migration_")} | {"response_uol"}
    check(not allowed.intersection(legacy_record), "runtime manifest authorizes legacy/migration record families", failures)
    check("cemm.v350.composition" not in set(manifest.get("forbidden_runtime_import_prefixes", ())), "manifest forbids canonical composition namespace", failures)

    if args.run_tests or args.full_tests:
        command = [sys.executable, "-m", "pytest", "-q"]
        if not args.full_tests:
            command += ["tests/v351/test_phase17_multimodal_final.py", "tests/v351/test_phase18_final_closure.py", "tests/v351/test_phase18_authority_attestation.py"]
        completed = subprocess.run(command, cwd=root)
        check(completed.returncode == 0, f"pytest failed:{completed.returncode}", failures)

    boot_sha = ""
    if args.boot_database is not None:
        boot_path = args.boot_database.resolve()
        check(boot_path.is_file(), f"boot database missing:{boot_path}", failures)
        if boot_path.is_file():
            boot_sha = sha256_file(boot_path)

    source_root, _source_inventory = runtime_source_root_v351(root)
    report = {
        "status": "pass" if not failures else "fail",
        "release_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip(),
        "boot_database_sha256": boot_sha,
        "runtime_source_root_sha256": source_root,
        "failures": failures,
        "checks": {
            "stage_count": 23,
            "canonical_service_count": len(authorities),
            "legacy_import_findings": findings,
        },
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
