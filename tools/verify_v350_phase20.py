#!/usr/bin/env python3
"""Verify that v3.5 final cutover is a concrete executable authority graph.

This verifier intentionally checks production symbols and package contents rather
than accepting a manifest-shaped proof.  It supports preactivation validation
before the signed manifest is generated and final activation validation after it.
"""
from __future__ import annotations

import argparse
import ast
import inspect
import json
from pathlib import Path
import sys
import tomllib
import zipfile

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cemm.v350.cutover import REQUIRED_RUNTIME_BOOT_AUTHORITIES, RuntimeAuthorityGuard, RuntimeAuthorityManifest
from cemm.v350.orchestration import CoreStage
from cemm.v350.runtime_hardening import HardenedRuntimeCoordinator
from cemm.v350.runtime_graph import canonical_stage_descriptors, resolve_adapter_type
from cemm.v350.storage import RecordKind

FORBIDDEN_PREFIXES=("cemm.v347","cemm.migration","cemm.v350.migration")
PUBLIC_FILES=(
    "cemm/__init__.py","cemm/app/runtime.py","cemm/__main__.py",
    "cemm/uol/__init__.py","cemm/web_demo.py","cemm/v350/public_runtime.py",
)


def fail(errors: list[str]) -> int:
    for item in errors:
        print(f"ERROR: {item}", file=sys.stderr)
    return 1


def import_targets(path: Path) -> tuple[str,...]:
    tree=ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result=[]
    for node in ast.walk(tree):
        if isinstance(node,ast.Import): result.extend(alias.name for alias in node.names)
        elif isinstance(node,ast.ImportFrom) and node.module: result.append(node.module)
    return tuple(result)


def is_forbidden_runtime_import(source_path: str, target: str) -> bool:
    normalized=source_path.replace("\\","/")
    candidates={target}
    if normalized.startswith("cemm/v350/") and target.startswith("migration"):
        candidates.add(f"cemm.v350.{target}")
    if normalized.startswith("cemm/") and target.startswith("migration"):
        candidates.add(f"cemm.{target}")
    return any(
        candidate==prefix or candidate.startswith(prefix+".")
        for candidate in candidates
        for prefix in FORBIDDEN_PREFIXES
    )


def verify_wheel(path: Path, errors: list[str]) -> None:
    with zipfile.ZipFile(path) as archive:
        names=tuple(archive.namelist())
        forbidden=("cemm/v347/","cemm/migration/","cemm/v350/migration/")
        leaked=sorted(name for name in names if any(name.startswith(prefix) for prefix in forbidden))
        if leaked: errors.append("runtime wheel contains quarantined legacy/migration modules:"+",".join(leaked[:20]))
        required=("cemm/__init__.py","cemm/v350/runtime.py","cemm/v350/runtime_graph.py","cemm/v350/stage_adapters.py")
        for item in required:
            if item not in names: errors.append(f"runtime wheel missing required production file:{item}")


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo-root",type=Path,default=Path("."))
    parser.add_argument("--manifest",type=Path,default=Path("cemm/data/v350/runtime_authority_manifest.json"))
    parser.add_argument("--preactivation",action="store_true")
    parser.add_argument("--boot-db",type=Path)
    parser.add_argument("--verification-report",type=Path)
    parser.add_argument("--wheel",type=Path)
    args=parser.parse_args()
    root=args.repo_root.resolve(); errors=[]

    descriptors=canonical_stage_descriptors()
    if tuple(d.stage for d in descriptors)!=tuple(CoreStage) or len(descriptors)!=23:
        errors.append("canonical graph is not exact Stage 0..22")
    if len({d.adapter_class_path for d in descriptors})!=23:
        errors.append("each core stage must have a distinct concrete adapter class")
    if {int(d.stage) for d in descriptors if d.permits_external_side_effect}!={16,20}:
        errors.append("external side effects must be owned only by Stage 16 and Stage 20")
    for descriptor in descriptors:
        try:
            cls=resolve_adapter_type(descriptor)
            if inspect.isabstract(cls): errors.append(f"abstract stage adapter:{descriptor.stage.name}")
            if getattr(cls,"HANDLER",None)!=descriptor.handler_name:
                errors.append(f"adapter handler mismatch:{descriptor.stage.name}")
            handler=getattr(HardenedRuntimeCoordinator,descriptor.handler_name,None)
            if handler is None or not callable(handler): errors.append(f"missing concrete runtime handler:{descriptor.stage.name}")
            source=inspect.getsource(cls).lower()
            if any(token in source for token in ("notimplementederror","todo: dummy","placeholder adapter","pass-through adapter")):
                errors.append(f"placeholder marker in production adapter:{descriptor.stage.name}")
        except Exception as exc:
            errors.append(f"cannot resolve concrete adapter {descriptor.stage.name}:{exc}")

    manifest_path=(root/args.manifest).resolve() if not args.manifest.is_absolute() else args.manifest
    if not manifest_path.is_file(): errors.append(f"missing runtime authority manifest:{manifest_path}")
    else:
        try:
            doc=json.loads(manifest_path.read_text(encoding="utf-8"))
            stage_docs=doc.get("stage_adapters",[])
            if [int(x.get("stage",-1)) for x in stage_docs]!=list(range(23)):
                errors.append("manifest does not encode exact ordered Stage 0..22 graph")
            by_stage={int(x["stage"]):x for x in stage_docs}
            for d in descriptors:
                item=by_stage.get(int(d.stage),{})
                expected=(d.adapter_ref,d.adapter_revision,d.adapter_class_path,d.handler_name,d.mutates_semantic_store,d.permits_external_side_effect)
                observed=(item.get("adapter_ref"),item.get("adapter_revision"),item.get("factory_path"),item.get("handler_name"),bool(item.get("mutates_semantic_store",False)),bool(item.get("permits_external_side_effect",False)))
                if observed!=expected: errors.append(f"manifest/code topology mismatch:{d.stage.name}")
            if doc.get("migration_modules_allowed_at_runtime"): errors.append("manifest permits migration modules at runtime")
            source_manifest=root/"cemm/data/v350/manifest.json"
            if not source_manifest.is_file():
                errors.append("missing v3.5 source manifest")
            else:
                try:
                    source_doc=json.loads(source_manifest.read_text(encoding="utf-8"))
                    if doc.get("activation_ready") and source_doc.get("metadata",{}).get("runtime_cutover") is not True:
                        errors.append("activated runtime manifest requires source metadata.runtime_cutover=true")
                except (OSError, ValueError, TypeError) as exc:
                    errors.append(f"invalid v3.5 source manifest:{exc}")
            if args.preactivation:
                if doc.get("activation_ready"): errors.append("preactivation source manifest must remain fail-closed")
            else:
                if args.boot_db is None or args.verification_report is None:
                    errors.append("final activation verification requires --boot-db and --verification-report")
                else:
                    for label, kind in REQUIRED_RUNTIME_BOOT_AUTHORITIES:
                        pins=doc.get(label, ())
                        if not pins:
                            errors.append(f"activated runtime manifest has no {label}")
                    capabilities=dict(doc.get("release_capabilities", {}))
                    required_true=(
                        "epistemic_admission","generic_inference","transitions",
                        "significance","response_policy","text_emission","output_discourse",
                    )
                    for key in required_true:
                        if capabilities.get(key) is not True:
                            errors.append(f"activated runtime lacks release capability:{key}")
                    service_kinds={
                        str(item.get("service_kind",""))
                        for item in doc.get("runtime_service_bindings",())
                        if isinstance(item,dict)
                    }
                    required_services={"clock","semantic_analyzer","channel_adapter","emission_gate_evaluator"}
                    if capabilities.get("epistemic_admission") is True:
                        required_services.add("epistemic_policy_provider")
                    if capabilities.get("generic_inference") is True:
                        required_services.add("inference_engine")
                    for item in sorted(required_services):
                        if item not in service_kinds:
                            errors.append(f"activated runtime lacks signed service:{item}")
                    manifest=RuntimeAuthorityManifest.load(manifest_path)
                    guard=RuntimeAuthorityGuard(manifest,repo_root=root,boot_database_path=args.boot_db.resolve(),verification_report_path=args.verification_report.resolve())
                    guard.require_service_authority()
        except Exception as exc:
            errors.append(f"runtime manifest validation failed:{exc}")

    for rel in PUBLIC_FILES:
        path=root/rel
        if not path.is_file(): errors.append(f"missing public runtime file:{rel}"); continue
        text=path.read_text(encoding="utf-8")
        if "v347" in text: errors.append(f"legacy v347 token remains in public runtime:{rel}")
        try:
            for target in import_targets(path):
                if is_forbidden_runtime_import(rel,target):
                    errors.append(f"forbidden public runtime import:{rel}:{target}")
        except SyntaxError as exc: errors.append(f"public runtime syntax error:{rel}:{exc}")

    pyproject=root/"pyproject.toml"
    if not pyproject.is_file(): errors.append("missing pyproject.toml")
    else:
        try:
            config=tomllib.loads(pyproject.read_text(encoding="utf-8"))
            excludes=set(config.get("tool",{}).get("setuptools",{}).get("packages",{}).get("find",{}).get("exclude",[]))
            required={"cemm.v347","cemm.v347.*","cemm.migration","cemm.migration.*","cemm.v350.migration","cemm.v350.migration.*"}
            if not required.issubset(excludes): errors.append("runtime package discovery does not quarantine all legacy/migration namespaces")
        except Exception as exc: errors.append(f"invalid pyproject packaging config:{exc}")

    for rel in ("cemm/migration/__init__.py","cemm/migration/v347.py"):
        if (root/rel).exists(): errors.append(f"legacy public migration shim still exists:{rel}")

    hardened_source=inspect.getsource(HardenedRuntimeCoordinator)
    if "request_goal_refresh=True" in hardened_source:
        errors.append("hardened runtime contains forbidden direct Stage-17 -> Stage-15 refresh")
    if "SemanticReentryRequest" not in hardened_source:
        errors.append("hardened runtime lacks bounded semantic re-entry")
    if "StructuredObservationAnalysis" not in hardened_source:
        errors.append("operation/tool observations cannot re-enter through reviewed semantic analysis")
    planner_source=(root/"cemm/v350/response/planner.py").read_text(encoding="utf-8")
    if planner_source.count("class ResponseAuthorizationGate")!=1:
        errors.append("response layer must have exactly one ResponseAuthorizationGate")

    if set(RuntimeAuthorityManifest.__dataclass_fields__) and not {item.value for item in RecordKind}:
        errors.append("RecordKind contract unexpectedly empty")
    if args.wheel:
        if not args.wheel.is_file(): errors.append(f"wheel not found:{args.wheel}")
        else: verify_wheel(args.wheel,errors)
    if errors: return fail(errors)
    print("v3.5 Phase-20/final-activation verification: PASS")
    return 0

if __name__=="__main__": raise SystemExit(main())
