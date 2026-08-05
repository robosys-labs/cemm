#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from cemm_authoritative_hybrid.authority import AuthorityLinker
from cemm_authoritative_hybrid.canonical import stable_ref
from cemm_authoritative_hybrid.persistence import RevisionPin
from cemm_authoritative_hybrid.r4_contracts import ExpectedCycleContractCompiler,ReviewedScenario
from cemm_authoritative_hybrid.r4_expansion import CaseExpander

def main()->int:
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).parents[1]);p.add_argument('--output',type=Path,required=True);a=p.parse_args();root=a.root.resolve();authority=AuthorityLinker().link_path(root/'data/authority/manifest.json');compiler=ExpectedCycleContractCompiler(authority,abi_registry_ref='abi_registry:active');pin=RevisionPin(authority.generation,0,0,0,0,None);out=[]
 for number,raw in enumerate((root/'data/scenarios/use_cases.jsonl').read_text(encoding='utf-8').splitlines()):
  if not raw.strip():continue
  scenario=ReviewedScenario.from_dict(json.loads(raw));contract=compiler.compile(scenario_ref=scenario.scenario_ref,case_ref=stable_ref('case_seed',{'scenario':scenario.scenario_ref}),surface_ref=stable_ref('surface_seed',{'scenario':scenario.scenario_ref}),context_ref=stable_ref('context_seed',{'scenario':scenario.scenario_ref}),assertions=scenario.assertions,situation_constraints={},revision_pin=pin);out.extend(row.as_dict() for row in CaseExpander().expand(scenario,contract))
 a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text('\n'.join(json.dumps(row,sort_keys=True,separators=(',',':'),ensure_ascii=False) for row in out)+'\n',encoding='utf-8',newline='\n');print(len(out));return 0
if __name__=='__main__':raise SystemExit(main())
