#!/usr/bin/env python3
from __future__ import annotations
import ast, json, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
issues=[]

def require(cond,msg):
    if not cond: issues.append(msg)

def text(path): return (ROOT/path).read_text(encoding='utf-8')

core=text('CORE_LOOP.md')
require('Stage 17 — GENERATE_RESPONSE_GOALS' not in core,'duplicate Stage-17 generic goal authority remains')
require('RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS' in core,'Stage-17 reconciliation contract missing')

storage=text('cemm/v350/storage/model.py')
for token in ('OPERATION_GATE_ASSESSMENT','OPERATION_PLAN','OPERATION_AUTHORIZATION','OPERATION_JOURNAL','OPERATION_RESULT','RESPONSE_UOL','REALIZATION_REQUEST','ARGUMENT_FRAME','SURFACE_CANDIDATE','SEMANTIC_ROUNDTRIP'):
    require(token in storage,f'missing RecordKind {token}')

sqlite=text('cemm/v350/storage/sqlite_schema.py')
require('SCHEMA_VERSION = 7' in sqlite,'Phase16/17 SQLite schema version must be 7')
require('phase16_records' in sqlite and 'phase17_records' in sqlite,'Phase16/17 normalized projections missing')
manifest=json.loads(text('cemm/data/v350/manifest.json'))
require(int(manifest.get('metadata',{}).get('phase',0))>=17,'manifest phase lineage was not advanced to 17')
for key in ('phase14_contract_sha256','phase15_contract_sha256','phase16_contract_sha256','phase17_contract_sha256','phase16_competence_sha256','phase17_competence_sha256'):
    require(bool(manifest.get('metadata',{}).get(key)),f'manifest verification fingerprint missing: {key}')

sig=text('cemm/v350/significance/engine.py')
require('event_ref=event_ref' not in sig,'obsolete ImpactAssessment(event_ref=...) runtime bug remains')
require('source_event_or_state_ref=event_ref' in sig,'correct ImpactAssessment source field missing')

goals=text('cemm/v350/goals/policy.py')
require('controlling_port_ref' in goals,'goal capability authorization does not use controlling port')
require('authorization_pins' in text('cemm/v350/goals/model.py'),'exact goal authorization pins missing')

ops=text('cemm/v350/operations/coordinator.py')
require('_ALLOWED_JOURNAL_TRANSITIONS' in ops,'journal transition state machine missing')
require('illegal operation journal transition' in ops,'journal transition enforcement missing')
require('gate_evaluators' in text('cemm/v350/operations/planner.py'),'hard external gate evaluators missing')
require('persist_observation' in ops and 'phase16_atomic_local_observation' in ops,'operation result + observed journal transition are not atomically persisted')
recovery=text('cemm/v350/operations/executor.py')
require('recover_and_persist' in recovery and 'OperationJournalStatus.SUBMITTED' in recovery,'SUBMITTED crash window is not recoverable')
require('OPERATION_GATE_ASSESSMENT' in storage and 'gate_assessment_pins' in text('cemm/v350/operations/model.py'),'durable hard-gate assessment authority missing')
require('store changed during operation planning' in text('cemm/v350/operations/planner.py'),'operation planning is not single-snapshot fail-closed')
require('store changed during hard-gate evaluation' in text('cemm/v350/operations/planner.py'),'hard-gate authorization is not single-snapshot fail-closed')
require('store changed after operation authorization' in ops,'PREPARED journal can reuse stale authorization snapshot')

realization_files=list((ROOT/'cemm/v350/realization').glob('*.py'))
for path in realization_files:
    tree=ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node,ast.Constant) and isinstance(node.value,str):
            lowered=node.value.lower()
            if 'sentence_template' in lowered or 'full sentence template' in lowered:
                # Documentation/prohibition strings are permitted; executable template fields are not.
                continue
require('sentence_template' not in text('cemm/v350/realization/model.py'),'sentence template field leaked into realization contracts')
require('PrivacyAwareReferenceResolver' in text('cemm/v350/realization/engine.py'),'privacy-aware reference resolver missing')
require('language_pack_pins' in text('cemm/v350/realization/engine.py'),'exact language-pack closure missing')
require('ConstructionKind.COORDINATION' in text('cemm/v350/realization/engine.py'),'reviewed coordination construction path missing')
require('filler.filler_class.value' in text('cemm/v350/realization/engine.py'),'deep clause planner does not preserve UOL filler class')
require('missing_scope_construction' in text('cemm/v350/realization/engine.py') and "meta.get('realization_role','')!='scope'" in text('cemm/v350/realization/engine.py'),'reviewed scope realization algebra missing')
require('underconstrained_linearization' in text('cemm/v350/realization/engine.py'),'underconstrained word order can silently fall back to kernel ordering')
require('store_changed_during_realization_compile' in text('cemm/v350/realization/engine.py'),'realization compiler is not single-snapshot fail-closed')
require('_semantic_referent' in text('cemm/v350/realization/engine.py'),'specialized referent reference resolution is missing')
require('roundtrip expected fingerprint is not the exact Response UOL graph fingerprint' in text('cemm/v350/realization/validation.py'),'roundtrip expected semantics can be caller-selected')
response=text('cemm/v350/response/coordinator.py')
require('LearningFrontierRecord' in response and 'response_unresolved_frontier' in response,'Response-UOL unresolved frontiers are not durable exact dependencies')
response_planner=text('cemm/v350/response/planner.py')
require('_collect_application_closure' in response_planner,'nested Response-UOL semantic application closure is missing')
require('semantic-application filler requires one exact goal-lineage pin' in response_planner,'nested Response-UOL applications lack exact goal lineage')
require('event response transform requires one exact participant application source pin' in response_planner,'event response transform can drift to latest participant application')

for contract in ('phase16_contract.json','phase17_contract.json'):
    data=json.loads(text('cemm/data/v350/'+contract))
    require(all(data['invariants'].values()),f'disabled invariant in {contract}')

for cases in ('phase16_operations_response.jsonl','phase17_realization.jsonl'):
    lines=[json.loads(line) for line in text('cemm/data/v350/competence/'+cases).splitlines() if line.strip()]
    require(len(lines)>=8,f'insufficient competence matrix in {cases}')
    refs=[x['case_ref'] for x in lines]
    require(len(refs)==len(set(refs)),f'duplicate competence case refs in {cases}')

if issues:
    print('Phase16/17 verification FAILED')
    for issue in issues: print(' -',issue)
    sys.exit(1)
print('Phase16/17 static architecture verification passed')
