#!/usr/bin/env python3
"""Build the exact RuntimeAuthorityManifest used to authorize v3.5 service."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, subprocess
from pathlib import Path

STAGES = [
"ORIENT_AND_PIN","OBSERVE","ANALYZE_AND_FUSE_FORM","GENERATE_REFERENT_AND_SCHEMA_CANDIDATES",
"PROJECT_REFERENT_KNOWLEDGE_AND_ENTITLEMENTS","BUILD_UOL_FACTOR_GRAPH","SOLVE_MEANING_HYPOTHESES",
"SELECT_MEANING_BUNDLE","CLASSIFY_DISCOURSE_CLAIMS_EVENTS_AND_GAPS","EPISTEMICALLY_ASSESS_AND_PLACE_CONTEXT",
"RETRIEVE_AND_ANSWER_BIND","BUILD_OR_ADVANCE_LEARNING_FRONTIERS","INFER_AND_PREVIEW_TRANSITIONS",
"COMMIT_AUTHORIZED_KNOWLEDGE_AND_STATE","ASSESS_IMPACT_AND_IMPORTANCE",
"DERIVE_OBLIGATIONS_GENERATE_AND_ARBITRATE_GOALS","PLAN_AUTHORIZE_EXECUTE_AND_RECONCILE",
"RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS","BUILD_RESPONSE_UOL","REALIZE_TARGET_LANGUAGE",
"VERIFY_AND_AUTHORIZE_EMISSION","COMMIT_OUTPUT_DISCOURSE_AND_COMMON_GROUND","INVALIDATE_RECOMPUTE_AND_FINALIZE"]

def sha(path: Path)->str:
 h=hashlib.sha256();
 with path.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''): h.update(c)
 return h.hexdigest()

def git_head(root:Path)->str:
 try:return subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
 except Exception:return ''

def main():
 p=argparse.ArgumentParser();p.add_argument('--repo',default='.');p.add_argument('--verification-report',default='');p.add_argument('--boot-db',default='');p.add_argument('--runtime-factory',required=True);p.add_argument('--adapter',action='append',default=[],help='STAGE=adapter_ref@revision,module:factory,source_file');p.add_argument('--output',default='cemm/data/v350/runtime_authority_manifest.json');a=p.parse_args()
 root=Path(a.repo).resolve();report=Path(a.verification_report).resolve() if a.verification_report else None
 if report is not None:
  doc=json.loads(report.read_text())
  if doc.get('status') not in {'PASS','PREACTIVATION_PASS'}:raise SystemExit('verification report is not PASS/PREACTIVATION_PASS')
 by={}
 for raw in a.adapter:
  stage,rest=raw.split('=',1);identity,factory,source=rest.split(',',2);ref,rev=identity.rsplit('@',1)
  if stage not in STAGES:raise SystemExit(f'unknown stage {stage}')
  if stage in by:raise SystemExit(f'duplicate stage {stage}')
  source_path=(root/source).resolve();
  if not source_path.is_file():raise SystemExit(f'missing adapter source {source}')
  by[stage]={"stage":STAGES.index(stage),"stage_name":stage,"adapter_ref":ref,"adapter_revision":int(rev),"factory_path":factory,"source_sha256":sha(source_path)}
 missing=[s for s in STAGES if s not in by]
 if missing:raise SystemExit('missing stage adapters: '+','.join(missing))
 source_manifest=root/'cemm/data/v350/manifest.json';deny=root/'cemm/data/v350/legacy_authority_denylist.json'
 boot=Path(a.boot_db).resolve() if a.boot_db else None
 out={"manifest_version":1,"release_version":"3.5.0","release_commit":git_head(root),"source_manifest_sha256":sha(source_manifest),"boot_database_sha256":sha(boot) if boot and boot.is_file() else '',"schema_version":8,"canonical_orchestrator":"cemm.v350.orchestration:CanonicalOrchestrator","canonical_runtime_factory":a.runtime_factory,"public_entrypoints":["cemm:Runtime","cemm.app.runtime:Runtime","cemm.__main__:main"],"forbidden_runtime_import_prefixes":["cemm.v347","cemm.v350.migration"],"stage_adapters":[by[s] for s in STAGES],"legacy_denylist_sha256":sha(deny),"verification_report_sha256":sha(report) if report is not None else "","activation_ready":False,"metadata":{"stage15_sole_goal_authority":True,"legacy_fallback":False,"migration_runtime_reachable":False}}
 path=root/a.output;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(out,sort_keys=True,separators=(',',':'))+'\n');print(path)
if __name__=='__main__':main()
