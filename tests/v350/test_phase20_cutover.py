from pathlib import Path
import json
import tempfile

def test_phase20_contract_and_competence_exist():
 root=Path(__file__).resolve().parents[2]
 contract=json.loads((root/'cemm/data/v350/phase20_cutover_contract.json').read_text())
 assert contract['phase']==20
 assert contract['required_core_stages']==23
 cases=[json.loads(x) for x in (root/'cemm/data/v350/competence/runtime_cutover.jsonl').read_text().splitlines() if x.strip()]
 assert len({x['case_ref'] for x in cases})==len(cases)>=10

def test_core_stage_topology_is_exact():
 from cemm.v350.orchestration import CoreStage
 assert [int(x) for x in CoreStage]==list(range(23))
 assert CoreStage.DERIVE_OBLIGATIONS_GENERATE_AND_ARBITRATE_GOALS==15
 assert CoreStage.RECONCILE_OPERATION_OUTCOMES_AND_REFRESH_GOALS==17

def test_orchestrator_rejects_incomplete_stage_graph():
 from cemm.v350.orchestration import CanonicalOrchestrator,CanonicalOrchestrationError
 class S:
  def fingerprint(self):return 'snapshot:x'
 class G:pass
 try:CanonicalOrchestrator((),snapshot_provider=S(),authority_guard=G())
 except CanonicalOrchestrationError as e:assert 'missing stages' in str(e)
 else:raise AssertionError('incomplete stage graph must fail closed')

def test_denylist_has_no_runtime_reachable_status():
 root=Path(__file__).resolve().parents[2]
 doc=json.loads((root/'cemm/data/v350/legacy_authority_denylist.json').read_text())
 allowed={'deleted','moved_to_offline_migration','moved_to_test_fixture','mechanical_adapter_only','quarantined_archive'}
 assert all(x['removal_status'] in allowed for x in doc['entries'])

def test_phase20_verifier_normalizes_windows_style_v350_paths():
 import tools.verify_v350_phase20 as verifier
 assert verifier.is_forbidden_runtime_import('cemm\\v350\\storage\\codec.py','migration.codec')
 assert verifier.is_forbidden_runtime_import('cemm/v350/storage/codec.py','migration.codec')

def test_runtime_authority_manifest_loads_full_cutover_fields():
 from cemm.v350.cutover import RuntimeAuthorityManifest
 doc={
  'manifest_version':1,'release_version':'3.5.0','release_commit':'commit:x',
  'source_manifest_sha256':'a','boot_database_sha256':'b','schema_version':8,
  'canonical_orchestrator':'cemm.v350.orchestration:CanonicalOrchestrator',
  'canonical_runtime_factory':'cemm.v350.runtime:build_runtime',
  'public_entrypoints':['cemm:Runtime'],
  'forbidden_runtime_import_prefixes':['cemm.v347','cemm.v350.migration'],
  'stage_adapters':[],
  'legacy_denylist_sha256':'c','verification_report_sha256':'d',
  'activation_ready':False,
  'allowed_runtime_modules':['cemm.v350.runtime'],
  'allowed_record_kinds':['schema'],
  'allowed_boot_data_modules':['schemas:referent_types'],
  'allowed_language_packages':['language-pack:en'],
  'operation_adapter_contracts':['operation-adapter:console@1'],
  'semantic_analyzer_contracts':['semantic-analyzer:en@1'],
  'channel_adapter_contracts':['channel-adapter:text@1'],
  'migration_modules_allowed_at_runtime':[],
  'metadata':{},
 }
 with tempfile.TemporaryDirectory() as td:
  path=Path(td)/'runtime_authority_manifest.json'
  path.write_text(json.dumps(doc),encoding='utf-8')
  loaded=RuntimeAuthorityManifest.load(path)
 assert loaded.allowed_runtime_modules==('cemm.v350.runtime',)
 assert loaded.migration_modules_allowed_at_runtime==()
