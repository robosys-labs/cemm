#!/usr/bin/env python3
"""Build the CEMM v3.5 runtime-authority manifest from canonical code/data.

The stage graph is never accepted from CLI input. It is derived exclusively from
``cemm.v350.runtime_graph.canonical_stage_descriptors`` and fingerprinted from
resolved production adapter source.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import inspect
import json
from pathlib import Path
import re
import sqlite3
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from cemm.v350.runtime_graph import canonical_stage_descriptors, resolve_adapter_type
from cemm.v350.cutover import REQUIRED_RUNTIME_BOOT_AUTHORITIES
from cemm.v350.runtime_services import canonical_service_descriptors
from cemm.v350.storage import RecordKind
from cemm.v350.storage.sqlite_schema import SCHEMA_VERSION


def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()



def boot_pins(path: Path, kind: RecordKind) -> list[str]:
    connection=sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows=connection.execute(
            "SELECT record_ref, revision, record_fingerprint FROM record_index "
            "WHERE record_kind=? ORDER BY record_ref, revision",
            (kind.value,),
        ).fetchall()
    finally:
        connection.close()
    return [f"{ref}@{int(revision)}#{fingerprint}" for ref,revision,fingerprint in rows]


def boot_language_tags(path: Path) -> list[str]:
    connection=sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows=connection.execute(
            "SELECT payload_json FROM record_index WHERE record_kind=? ORDER BY record_ref, revision",
            (RecordKind.LANGUAGE_PACK.value,),
        ).fetchall()
    finally:
        connection.close()
    result=[]
    for (payload_json,) in rows:
        payload=json.loads(str(payload_json))
        tag=payload.get("language_tag")
        if tag:
            result.append(str(tag))
    return sorted(set(result))

def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument('--repo-root',type=Path,default=Path('.'))
    parser.add_argument('--boot-db',type=Path,required=True)
    parser.add_argument('--verification-report',type=Path,required=True)
    parser.add_argument('--release-commit',required=True)
    parser.add_argument('--output',type=Path,default=Path('cemm/data/v350/runtime_authority_manifest.json'))
    parser.add_argument('--activate',action='store_true',help='emit activation_ready=true only after all release artifacts validate')
    args=parser.parse_args()
    root=args.repo_root.resolve(); boot=args.boot_db.resolve(); report_path=args.verification_report.resolve()
    if not re.fullmatch(r'[0-9a-f]{40}',args.release_commit): raise SystemExit('release commit must be exact 40-hex SHA')
    for path in (boot,report_path,root/'cemm/data/v350/manifest.json',root/'cemm/data/v350/legacy_authority_denylist.json'):
        if not path.is_file(): raise SystemExit(f'missing required artifact: {path}')
    report=json.loads(report_path.read_text(encoding='utf-8'))
    boot_sha=sha256(boot)
    if report.get('status')!='pass': raise SystemExit('verification report is not passing')
    if report.get('release_commit')!=args.release_commit: raise SystemExit('verification report commit mismatch')
    if report.get('boot_database_sha256')!=boot_sha: raise SystemExit('verification report boot database mismatch')

    stages=[]
    for d in canonical_stage_descriptors():
        cls=resolve_adapter_type(d); source=inspect.getsourcefile(cls)
        if not source or not Path(source).is_file(): raise SystemExit(f'cannot fingerprint {d.adapter_class_path}')
        stages.append({
            'stage':int(d.stage),'stage_name':d.stage.name,'adapter_ref':d.adapter_ref,
            'adapter_revision':d.adapter_revision,'factory_path':d.adapter_class_path,
            'handler_name':d.handler_name,'source_sha256':sha256(Path(source)),
            'mutates_semantic_store':d.mutates_semantic_store,
            'permits_external_side_effect':d.permits_external_side_effect,
        })

    source_manifest=root/'cemm/data/v350/manifest.json'; denylist=root/'cemm/data/v350/legacy_authority_denylist.json'
    source_doc=json.loads(source_manifest.read_text(encoding='utf-8'))
    source_metadata=dict(source_doc.get('metadata',{}))
    if args.activate and source_metadata.get('phase20_prepared') is not True:
        raise SystemExit('activation requires source manifest metadata.phase20_prepared=true')
    capabilities=dict(source_metadata.get('release_capabilities',{}))
    if args.activate:
        required=list(REQUIRED_RUNTIME_BOOT_AUTHORITIES)
        if capabilities.get("external_operations"):
            required.append(("operation_adapter_contracts",RecordKind.OPERATION_ADAPTER_CONTRACT))
        missing=[label for label,kind in required if not boot_pins(boot,kind)]
        if missing:
            raise SystemExit('activation requires non-empty boot authorities: '+','.join(missing))
    services=[asdict(item) for item in canonical_service_descriptors()]
    doc={
        'manifest_version':2,'release_version':'3.5.0','release_commit':args.release_commit,
        'source_manifest_sha256':sha256(source_manifest),
        'boot_database_sha256':boot_sha,
        'schema_version':SCHEMA_VERSION,
        'canonical_orchestrator':'cemm.v350.orchestration:CanonicalOrchestrator',
        'canonical_runtime_factory':'cemm.v350.runtime:build_runtime',
        'public_entrypoints':['cemm:Runtime','cemm.app.runtime:Runtime','python -m cemm','cemm.web_demo:serve'],
        'forbidden_runtime_import_prefixes':['cemm.v347','cemm.migration','cemm.v350.migration'],
        'stage_adapters':stages,
        'allowed_runtime_modules':['cemm.v350'],
        'allowed_record_kinds':[item.value for item in RecordKind],
        'allowed_boot_data_modules':['cemm.data.v350'],
        'allowed_language_packages':boot_pins(boot,RecordKind.LANGUAGE_PACK),
        'operation_adapter_contracts':boot_pins(boot,RecordKind.OPERATION_ADAPTER_CONTRACT),
        'semantic_analyzer_contracts':boot_pins(boot,RecordKind.SEMANTIC_ANALYZER_CONTRACT),
        'channel_adapter_contracts':boot_pins(boot,RecordKind.CHANNEL_ADAPTER_CONTRACT),
        'response_policy_rules':boot_pins(boot,RecordKind.RESPONSE_POLICY_RULE),
        'response_transform_rules':boot_pins(boot,RecordKind.RESPONSE_TRANSFORM_RULE),
        'argument_frames':boot_pins(boot,RecordKind.ARGUMENT_FRAME),
        'morphology_rules':boot_pins(boot,RecordKind.MORPHOLOGY_RULE),
        'linearization_rules':boot_pins(boot,RecordKind.LINEARIZATION_RULE),
        'runtime_service_bindings':services,
        'release_capabilities':capabilities,
        'realization_language_tags':boot_language_tags(boot),
        'output_speaker_ref':source_metadata.get('output_speaker_ref'),
        'output_commitment_kind_ref':source_metadata.get('output_commitment_kind_ref'),
        'migration_modules_allowed_at_runtime':[],
        'legacy_denylist_sha256':sha256(denylist),'verification_report_sha256':sha256(report_path),
        'activation_ready':bool(args.activate),
        'metadata':{
            'boot_database_relpath':boot.relative_to(root).as_posix() if boot.is_relative_to(root) else str(boot),
            'verification_report_relpath':report_path.relative_to(root).as_posix() if report_path.is_relative_to(root) else str(report_path),
            'generated_from_canonical_stage_graph':True,'stage_count':len(stages),
            'preactivation':not args.activate,
            'source_runtime_cutover':bool(source_metadata.get('runtime_cutover',False)),
        },
    }
    if args.activate and len(stages)!=23: raise SystemExit('activation requires exact 23-stage graph')
    out=(root/args.output).resolve() if not args.output.is_absolute() else args.output
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(doc,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(out); return 0

if __name__=='__main__': raise SystemExit(main())
