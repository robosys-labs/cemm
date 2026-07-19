#!/usr/bin/env python3
"""Fail-closed Phase-20 release verifier.

This verifier intentionally distinguishes source implementation from release
activation.  It produces PASS only when the public runtime topology is v3.5-only,
all Stage-0..22 adapters are explicitly declared, packaging contains v3.5 data,
and no known competing runtime authority remains reachable by static imports.
"""
from __future__ import annotations
import argparse, ast, hashlib, json, re, subprocess, sys, tempfile, zipfile
from pathlib import Path

FORBIDDEN_IMPORTS=('cemm.v347','cemm.v350.migration')
PUBLIC_FILES=('cemm/__init__.py','cemm/app/runtime.py','cemm/__main__.py')
SEMANTIC_FLAGS=('USE_V350','FALLBACK_LEGACY','USE_OLD_NLG','LEGACY_MEMORY_ON_FAILURE')
STAGE_COUNT=23

def sha(p:Path)->str:
 h=hashlib.sha256();
 with p.open('rb') as f:
  for c in iter(lambda:f.read(1024*1024),b''):h.update(c)
 return h.hexdigest()

def imports(path:Path):
 try:tree=ast.parse(path.read_text(encoding='utf-8'))
 except Exception:return ()
 out=[]
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):out.extend(a.name for a in node.names)
  elif isinstance(node,ast.ImportFrom):
   if node.module:out.append(node.module)
 return tuple(out)

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--repo',default='.');ap.add_argument('--boot-db',default='');ap.add_argument('--runtime-manifest',default='cemm/data/v350/runtime_authority_manifest.json');ap.add_argument('--run-pytest',action='store_true');ap.add_argument('--check-wheel',action='store_true');ap.add_argument('--output',default='phase20-release-verification.json');ap.add_argument('--preactivate',action='store_true');a=ap.parse_args();root=Path(a.repo).resolve();errors=[];warnings=[];checks={}
 def check(name,ok,msg):checks[name]=bool(ok);errors.append(msg) if not ok else None
 source=root/'cemm/data/v350/manifest.json'
 try:meta=json.loads(source.read_text()).get('metadata',{});check('phase19_predecessor',int(meta.get('phase',0))>=19,'source manifest is below Phase19')
 except Exception as e:check('phase19_predecessor',False,f'manifest unreadable: {e}')
 core=(root/'CORE_LOOP.md').read_text(encoding='utf-8') if (root/'CORE_LOOP.md').is_file() else ''
 check('stage17_topology','17 RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS' in core,'CORE_LOOP macro Stage17 still duplicates goal generation')
 if not a.preactivate:
  for rel in PUBLIC_FILES:
   p=root/rel
   text=p.read_text(encoding='utf-8') if p.is_file() else ''
   check('public_no_v347:'+rel,'v347' not in text,f'{rel} still references v347')
 else:
  warnings.append('preactivation mode: public v3.4.7 entrypoints are allowed until atomic cutover')
 runtime_files=[p for p in (root/'cemm').rglob('*.py') if '/v347/' not in p.as_posix() and '/v350/migration/' not in p.as_posix() and not (a.preactivate and p.relative_to(root).as_posix() in PUBLIC_FILES)]
 bad=[]
 for p in runtime_files:
  for imp in imports(p):
   if any(imp==x or imp.startswith(x+'.') for x in FORBIDDEN_IMPORTS) or imp=='v347' or imp.startswith('v347.') or imp=='v350.migration' or imp.startswith('v350.migration.') or (str(p.relative_to(root)).startswith('cemm/v350/') and (imp=='migration' or imp.startswith('migration.'))):bad.append((str(p.relative_to(root)),imp))
 check('runtime_import_isolation',not bad,'forbidden runtime imports: '+repr(bad[:20]))
 flag_hits=[]
 for p in runtime_files:
  text=p.read_text(encoding='utf-8',errors='ignore')
  for flag in SEMANTIC_FLAGS:
   if flag in text:flag_hits.append((str(p.relative_to(root)),flag))
 check('no_semantic_fallback_flags',not flag_hits,'semantic fallback flags found: '+repr(flag_hits))
 deny=root/'cemm/data/v350/legacy_authority_denylist.json'
 try:d=json.loads(deny.read_text());unresolved=[x for x in d.get('entries',[]) if x.get('removal_status') not in {'deleted','moved_to_offline_migration','moved_to_test_fixture','mechanical_adapter_only','quarantined_archive'}];check('denylist_closed',not unresolved,'legacy denylist has unresolved entries')
 except Exception as e:check('denylist_closed',False,f'denylist unreadable: {e}')
 rmp=root/a.runtime_manifest
 try:
  m=json.loads(rmp.read_text());ad=m.get('stage_adapters',[]);stages={int(x['stage']) for x in ad};check('runtime_manifest_activation',True if a.preactivate else bool(m.get('activation_ready')),'runtime manifest is not activation_ready');check('all_23_stages',len(ad)==STAGE_COUNT and stages==set(range(STAGE_COUNT)),'runtime manifest does not declare exactly one adapter for stages 0..22');check('runtime_factory',bool(m.get('canonical_runtime_factory')) and not any(str(m.get('canonical_runtime_factory')).startswith(x) for x in FORBIDDEN_IMPORTS),'runtime factory missing or forbidden');check('source_manifest_fingerprint',m.get('source_manifest_sha256')==sha(source),'runtime manifest source manifest fingerprint mismatch');check('denylist_fingerprint',m.get('legacy_denylist_sha256')==sha(deny),'runtime manifest denylist fingerprint mismatch');
  if not a.preactivate:check('verification_lineage',bool(m.get('verification_report_sha256')),'runtime manifest lacks activation verification lineage')
 except Exception as e:check('runtime_manifest_activation',False,f'runtime authority manifest unreadable: {e}');check('all_23_stages',False,'no valid runtime authority manifest')
 pyproject=(root/'pyproject.toml').read_text(encoding='utf-8') if (root/'pyproject.toml').is_file() else ''
 if not a.preactivate:check('package_version','version = "3.5.0"' in pyproject,'pyproject version is not 3.5.0')
 check('package_v350_data','data/v350/' in pyproject or (root/'MANIFEST.in').is_file(),'packaging does not declare v350 data')
 if a.boot_db:
  boot=Path(a.boot_db).resolve();check('boot_db_exists',boot.is_file(),'boot DB missing')
 if a.check_wheel:
  try:
   with tempfile.TemporaryDirectory() as td:
    subprocess.check_call([sys.executable,'-m','build','--wheel','--outdir',td],cwd=root,stdout=subprocess.DEVNULL)
    wheels=list(Path(td).glob('*.whl'));assert len(wheels)==1
    with zipfile.ZipFile(wheels[0]) as z:names=z.namelist()
    required=('cemm/data/v350/manifest.json','cemm/data/v350/phase20_cutover_contract.json','cemm/data/v350/competence/runtime_cutover.jsonl')
    check('wheel_contains_v350',all(any(n.endswith(x) for n in names) for x in required),'built wheel omits required v350 data')
  except Exception as e:check('wheel_contains_v350',False,f'wheel verification failed: {e}')
 else:warnings.append('wheel build not executed; use --check-wheel for release verification')
 if a.run_pytest:
  rc=subprocess.call([sys.executable,'-m','pytest','-q'],cwd=root);check('pytest',rc==0,f'pytest failed with exit {rc}')
 else:warnings.append('full pytest not executed; use --run-pytest for release verification')
 status=('PREACTIVATION_PASS' if a.preactivate else 'PASS') if not errors and a.run_pytest and a.check_wheel else 'INCOMPLETE' if not errors else 'FAIL'
 report={'status':status,'checks':checks,'errors':errors,'warnings':warnings,'source_manifest_sha256':sha(source) if source.is_file() else '', 'legacy_denylist_sha256':sha(deny) if deny.is_file() else ''}
 out=root/a.output;out.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,indent=2,sort_keys=True));raise SystemExit(0 if status in {'PASS','PREACTIVATION_PASS'} else 2)
if __name__=='__main__':main()
