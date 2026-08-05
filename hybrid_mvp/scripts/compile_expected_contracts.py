#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r4_contracts import ExpectedCycleContractCompiler,ReviewedScenario

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).parents[1]);p.add_argument('--scenarios',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.root.resolve();source=a.scenarios or root/'data/scenarios/use_cases.jsonl'
 authority=AuthorityLinker().link_path(root/'data/authority/manifest.json');abi_hash=hashlib.sha256((root/'docs/ABI_REGISTRY.md').read_bytes()).hexdigest();compiler=ExpectedCycleContractCompiler(authority,abi_registry_ref=f'abi_registry:{abi_hash}')
 pin=RevisionPin(authority.generation,0,0,0,0,None);rows=[]
 for number,raw in enumerate(source.read_text(encoding='utf-8').splitlines()):
  if not raw.strip():continue
  scenario=ReviewedScenario.from_dict(json.loads(raw));surface=scenario.surface_examples[0] if scenario.surface_examples else ''
  contract=compiler.compile(scenario_ref=scenario.scenario_ref,case_ref=stable_ref('reviewed_case',{'scenario':scenario.scenario_ref,'index':number}),surface_ref=stable_ref('reviewed_surface',{'scenario':scenario.scenario_ref,'surface':surface}),context_ref=stable_ref('expected_context',{'scenario':scenario.scenario_ref}),assertions=scenario.assertions,situation_constraints={},revision_pin=pin);rows.append(contract.as_dict())
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text('\n'.join(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False) for row in rows)+'\n',encoding='utf-8',newline='\n');print(json.dumps({'schema':'r4-contract-build-v1','count':len(rows),'sha256':hashlib.sha256(a.output.read_bytes()).hexdigest()},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
