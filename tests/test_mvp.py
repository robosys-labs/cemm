from __future__ import annotations
import json,tempfile,sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cemm.store import Store
from cemm.runtime import Runtime, BoundedModelCache
from cemm.inference import Inference
from cemm.model import AmbiguousReferent
from cemm.compiler import ExactStructuredCompiler
from cemm.trainer import compile_corpus
from cemm.acquisition import acquire
import cemm.codec as _codec
import cemm.interpreter as _interp
BASE=ROOT/'cemm/data/base.json';FAMILY=ROOT/'cemm/data/family_knowledge.json';EN=ROOT/'cemm/language_packs/en.json';ES=ROOT/'cemm/language_packs/es.json'
TRAIN=ROOT/'reference/mvp_v4/training/en_seed.json';ACQ=ROOT/'reference/mvp_v4/acquisition_examples/friction.json'

def make(lang='en',family=True):
    td=tempfile.TemporaryDirectory();s=Store(Path(td.name)/'mvp.sqlite');s.import_data(BASE)
    if family:s.import_data(FAMILY)
    rt=Runtime(s,EN if lang=='en' else ES);return td,s,rt

def teach_family(rt):
    a=rt.process('A mother in-law is the mother of a partner.',teach=True)
    b=rt.process('A mother-in-law is the mother of a partner.',teach=True)
    return a,b

def rules(node):
    if not node:return set()
    out={node['rule_ref']} if node.get('rule_ref') else set()
    for p in node.get('parents',[]):out|=rules(p)
    return out

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Clear both the structured-codec cache and the surface-codec model cache.
        _codec.CACHE.clear();_interp.MODEL_CACHE.clear()
        td,s,rt=make();rt.process('What is evidence?');s.db.close();td.cleanup()

    def test_pack_has_structured_supervision_not_closed_program_classes(self):
        d=json.loads(EN.read_text());self.assertEqual(d['version'],4);self.assertTrue(d['structured_examples']);self.assertNotIn('interpretation_examples',d)
        blob=json.dumps(d['structured_examples']);self.assertNotIn('"program"',blob);self.assertTrue(all('intent' in x['target'] and 'apps' in x['target'] for x in d['structured_examples']))

    def test_trainer_deterministic_and_language_generic(self):
        ks=[BASE,FAMILY];a=compile_corpus(TRAIN,ks);b=compile_corpus(TRAIN,ks);self.assertEqual(a['pack_hash'],b['pack_hash']);self.assertTrue(a['structured_examples']);self.assertTrue(a['rule_examples'])

    def test_kernel_has_no_family_or_literal_response_hardcoding(self):
        # Read all modular cemm source files (ported from v4 cemm_mvp.py + structured_codec.py).
        cemm_dir=ROOT/'cemm'
        src=''
        for p in sorted(cemm_dir.glob('*.py')):
            src+=p.read_text().lower()
        for x in ('mother_in_law','mother-in-law','spouse','wife','husband','married','president','i have conflicting evidence','evidence is insufficient'):
            self.assertNotIn(x,src)

    def test_open_prediction_is_compositional_not_document_class(self):
        d=json.loads(EN.read_text());self.assertFalse(any(ex['input'].count('.')>1 for ex in d['structured_examples']))
        td,s,rt=make()
        try:
            r=rt.process('Ada is a doctor. She arrived today.');self.assertEqual(r['status'],'learned');self.assertEqual(len(r['packet']['apps']),2);self.assertEqual(r['packet']['apps'][0]['args']['role:instance'],r['packet']['apps'][1]['args']['role:actor'])
        finally:s.db.close();td.cleanup()

    def test_nbest_structured_prediction_and_settling(self):
        td,s,rt=make()
        try:
            r=rt.process('Ada is a doctor.');tr=r['trace']['clauses'][0];self.assertTrue(r['trace']['n_best']);self.assertEqual(tr['status'],'settled');self.assertGreaterEqual(len(tr['candidates']),2);self.assertIn('operator',tr['candidates'][0]['packet']['apps'][0])
        finally:s.db.close();td.cleanup()

    def test_exact_compiler_rejects_semantic_kind_mismatch(self):
        td,s,rt=make()
        try:
            c=ExactStructuredCompiler(s)
            with self.assertRaises(ValueError):c.compile({'apps':[{'operator':'op:type','args':{'role:instance':'entity:ada','role:class':'rel:spouse'}}]})
        finally:s.db.close();td.cleanup()

    def test_greeting_grounded_semantics_and_pointer_nlg(self):
        td,s,rt=make()
        try:
            r=rt.process('Hi.');self.assertEqual(r['response'],'Hello.');self.assertEqual(r['response_plan']['goal'],'goal:greet');self.assertTrue(r['realization_proof']['verified']);self.assertFalse(r['realization_proof']['roundtrip_used'])
        finally:s.db.close();td.cleanup()

    def test_operational_response_words_are_meaning(self):
        td,s,rt=make()
        try:
            self.assertEqual(rt.process('What is evidence?')['response'],'Evidence is information.');self.assertEqual(rt.process('What is conflict?')['response'],'Conflict is a state.');self.assertEqual(rt.process('What is meaning?')['response'],'Meaning is structured semantic content.')
        finally:s.db.close();td.cleanup()

    def test_unknown_and_conflict_are_grounded_response_plans(self):
        td,s,rt=make()
        try:
            u=rt.process('Am I married?');self.assertEqual(u['result'],'unknown');self.assertEqual(u['response'],'Evidence is insufficient.')
            with s.db:
                g=s.begin('conflict');o=s.add_observation('support',{},'und','test',g);s.insert_app('op:state',{'role:subject':'participant:user','role:dimension':'dim:marital_status','role:value':'value:married'},g,o,'support');o2=s.add_observation('deny',{},'und','test',g);s.insert_app('op:state',{'role:subject':'participant:user','role:dimension':'dim:marital_status','role:value':'value:married'},g,o2,'deny');s.finish(g)
            c=rt.process('Am I married?');self.assertEqual(c['result'],'conflict');self.assertEqual(c['response'],'Evidence is conflicting.')
        finally:s.db.close();td.cleanup()

    def test_family_specific_rule_is_not_hardseeded(self):
        d=json.loads(FAMILY.read_text());self.assertFalse(any(r['rule_ref']=='rule:mil-decompose' for r in d.get('rules',[])))

    def test_rule_induction_is_structured_and_provisional_first(self):
        td,s,rt=make()
        try:
            a=rt.process('A mother in-law is the mother of a partner.',teach=True);self.assertEqual(a['status'],'provisional_rule');rule=a['rule'];self.assertEqual(rule['if'][0]['operator'],'op:relation');self.assertEqual(len(rule['then']),2);self.assertEqual(s.db.execute('select status from rule_candidates').fetchone()[0],'provisional')
        finally:s.db.close();td.cleanup()

    def test_provisional_rule_does_not_execute(self):
        td,s,rt=make()
        try:
            rt.process('A mother in-law is the mother of a partner.',teach=True);rt.process('My mother in-law arrived today.');self.assertEqual(rt.process('Am I married?')['result'],'unknown')
        finally:s.db.close();td.cleanup()

    def test_promotion_requires_evidence_and_activation_reload(self):
        td,s,rt=make()
        try:
            a,b=teach_family(rt);self.assertEqual(a['status'],'provisional_rule');self.assertEqual(b['status'],'promoted_rule');rt.process('My mother in-law arrived today.');self.assertEqual(rt.process('Am I married?')['result'],'unknown');rt.reload_authority();self.assertEqual(rt.process('Am I married?')['response'],'Yes.')
        finally:s.db.close();td.cleanup()

    def test_family_reasoning_after_promoted_rule_has_proof_chain(self):
        td,s,rt=make()
        try:
            teach_family(rt);rt.reload_authority();rt.process('My mother in-law arrived today.');a=rt.process('Am I married?');self.assertEqual(a['response'],'Yes.');rs=rules(a['query_result']['proofs'][0]);self.assertIn('rule:subrelation-inheritance',rs);self.assertIn('rule:relation-object-state',rs);self.assertTrue(any(x.startswith('rule:') for x in rs))
        finally:s.db.close();td.cleanup()

    def test_rule_semantic_dedup_across_paraphrases(self):
        td,s,rt=make()
        try:
            teach_family(rt);row=s.db.execute('select count(*),max(evidence_count),max(status) from rule_candidates').fetchone();self.assertEqual(row[0],1);self.assertEqual(row[1],2);self.assertEqual(row[2],'promoted')
        finally:s.db.close();td.cleanup()

    def test_promoted_authority_does_not_mutate_existing_pin(self):
        td,s,rt=make()
        try:
            g=rt.runtime_attestation['authority_generation'];h=rt.runtime_attestation['authority_generation_hash'];teach_family(rt);self.assertEqual(rt.runtime_attestation['authority_generation'],g);self.assertEqual(rt.runtime_attestation['authority_generation_hash'],h);rt.reload_authority();self.assertGreater(rt.runtime_attestation['authority_generation'],g)
        finally:s.db.close();td.cleanup()

    def test_reviewed_new_concept_acquisition_uses_same_codec(self):
        td,s,rt=make()
        try:
            doc=json.loads(ACQ.read_text());r=acquire(s,rt,doc);self.assertEqual(r['result']['status'],'learned');self.assertEqual(rt.process('What is Friction?')['response'],'Friction is resistance.');self.assertTrue(all(x.startswith('atom:') for x in r['created_or_resolved'].values()))
        finally:s.db.close();td.cleanup()


    def test_reviewed_designation_acquisition_changes_authority_but_user_fact_does_not(self):
        td,s,rt=make()
        try:
            h0=rt.runtime_attestation['authority_generation_hash'];rt.process('Ada is a doctor.');rt.reload_authority();self.assertEqual(h0,rt.runtime_attestation['authority_generation_hash']);acquire(s,rt,json.loads(ACQ.read_text()));self.assertNotEqual(h0,rt.runtime_attestation['authority_generation_hash'])
        finally:s.db.close();td.cleanup()

    def test_acquisition_does_not_add_operator_schema(self):
        td,s,rt=make()
        try:
            before=(s.db.execute("select count(*) from atoms where kind='operator'").fetchone()[0],s.db.execute('select count(*) from operator_roles').fetchone()[0]);acquire(s,rt,json.loads(ACQ.read_text()));after=(s.db.execute("select count(*) from atoms where kind='operator'").fetchone()[0],s.db.execute('select count(*) from operator_roles').fetchone()[0]);self.assertEqual(before,after)
        finally:s.db.close();td.cleanup()

    def test_workspace_bounded_and_self_state_present(self):
        td,s,rt=make()
        try:
            teach_family(rt);rt.reload_authority();rt.process('My mother in-law arrived today.');a=rt.process('Am I married?');self.assertLessEqual(len(a['workspace']['selected']),24);self.assertEqual(a['self_state'],{})
        finally:s.db.close();td.cleanup()

    def test_inference_ephemeral_no_query_bloat(self):
        td,s,rt=make()
        try:
            teach_family(rt);rt.reload_authority();rt.process('My mother in-law arrived today.');before=tuple(s.db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ('applications','bindings','claims','proof_links'));[rt.process('Am I married?') for _ in range(4)];after=tuple(s.db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ('applications','bindings','claims','proof_links'));self.assertEqual(before,after)
        finally:s.db.close();td.cleanup()

    def test_inferred_type_supports_pronoun_resolution(self):
        td,s,rt=make()
        try:
            teach_family(rt);rt.reload_authority();rt.process('My mother in-law arrived today.');self.assertEqual(rt.process('Is she a human?')['response'],'Yes.')
        finally:s.db.close();td.cleanup()

    def test_multilingual_interface_reuses_promoted_semantic_rule(self):
        td=tempfile.TemporaryDirectory();s=Store(Path(td.name)/'x.sqlite');s.import_data(BASE);s.import_data(FAMILY);en=Runtime(s,EN);teach_family(en);en.reload_authority();es=Runtime(s,ES)
        try:
            self.assertEqual(es.process('Mi suegra llegó hoy.')['status'],'learned');self.assertEqual(es.process('¿Estoy casado?')['response'],'Sí.')
        finally:s.db.close();td.cleanup()

    def test_same_name_entities_not_merged(self):
        td,s,rt=make()
        try:
            with self.assertRaises(AmbiguousReferent):s.resolve_label('Alex Kim','en');self.assertEqual(s.resolve_label('Alex J. Kim','en'),'entity:alex_a')
        finally:s.db.close();td.cleanup()

    def test_unicode_casefold_resolution(self):
        td,s,rt=make('es')
        try:self.assertEqual(s.resolve_label('CÓNYUGE','es'),s.resolve_label('cónyuge','es'))
        finally:s.db.close();td.cleanup()

    def test_pointer_nlg_no_mandatory_roundtrip(self):
        td,s,rt=make()
        try:
            p=rt.process('Am I married?')['realization_proof'];self.assertTrue(p['verified']);self.assertEqual(p['verification_mode'],'semantic_pointer_provenance');self.assertFalse(p['roundtrip_used'])
        finally:s.db.close();td.cleanup()

    def test_internal_ids_never_emit(self):
        td,s,rt=make()
        try:
            teach_family(rt);rt.reload_authority();rt.process('My mother in-law arrived today.');r=rt.process('Who is she?');self.assertNotRegex(r.get('response',''),r'(?:atom|existential|app|fact):[0-9a-fA-F]+')
        finally:s.db.close();td.cleanup()

    def test_repeated_observations_distinct_apps_dedup(self):
        td,s,rt=make()
        try:
            a=rt.process('My mother in-law arrived today.');b=rt.process('My mother in-law arrived today.');self.assertEqual(a['new_atoms'],b['new_atoms']);self.assertEqual(s.db.execute('select count(*) from observations where surface=?',('My mother in-law arrived today.',)).fetchone()[0],2);self.assertEqual(s.db.execute("select count(*) from applications where operator_ref='op:event'").fetchone()[0],1)
        finally:s.db.close();td.cleanup()

    def test_causal_rule_not_asserted_as_actual(self):
        td,s,rt=make()
        try:
            learned=rt.process('My mother in-law arrived today.');mil=learned['packet']['apps'][0]['args']['role:subject'];facts,_=Inference(s,authority_generation=rt.runtime_attestation['authority_generation']).closure();self.assertFalse(any(f.operator=='op:state' and f.args.get('role:subject')==mil and f.args.get('role:dimension')=='dim:location_status' for f in facts))
        finally:s.db.close();td.cleanup()

    def test_exclusive_state_denial_does_not_supersede_support(self):
        td,s,rt=make()
        try:
            with s.db:
                g=s.begin('state');o=s.add_observation('ready',{},'und','test',g);a=s.insert_app('op:state',{'role:subject':'participant:system','role:dimension':'dim:response_state','role:value':'value:ready'},g,o,'support');o2=s.add_observation('not processing',{},'und','test',g);s.insert_app('op:state',{'role:subject':'participant:system','role:dimension':'dim:response_state','role:value':'value:processing'},g,o2,'deny');s.finish(g)
            self.assertIsNone(s.db.execute("select valid_to from claims where app_ref=? and stance='support'",(a,)).fetchone()[0])
        finally:s.db.close();td.cleanup()

    def test_inference_budget_exhaustion_frontier(self):
        td,s,rt=make()
        try:
            rt.inf=Inference(s,max_rounds=0,max_facts=1,authority_generation=rt.runtime_attestation['authority_generation']);r=rt.process('Am I married?');self.assertIn(r['status'],('frontier','partial'));self.assertEqual(r['frontier']['kind'],'inference_incomplete')
        finally:s.db.close();td.cleanup()

    def test_epistemics_are_target_scoped_across_unknown_and_supported_answers(self):
        td,s,rt=make()
        try:
            u=rt.process('Am I married?')
            self.assertEqual(u['epistemic_assessment']['status'],'unknown')
            self.assertEqual(u['self_state'],{})
            teach_family(rt);rt.reload_authority();rt.process('My mother in-law arrived today.')
            a=rt.process('Am I married?')
            self.assertEqual(a['response'],'Yes.')
            self.assertEqual(a['epistemic_assessment']['status'],'answered')
            self.assertEqual(a['self_state'],{})
        finally:s.db.close();td.cleanup()

    def test_rule_candidate_not_in_authority_hash_until_promotion_activation(self):
        td,s,rt=make()
        try:
            pin=rt.runtime_attestation['authority_generation_hash'];rt.process('A mother in-law is the mother of a partner.',teach=True);self.assertEqual(pin,rt.runtime_attestation['authority_generation_hash']);self.assertEqual(s.db.execute("select count(*) from rules where authority_status='promoted'").fetchone()[0],0)
        finally:s.db.close();td.cleanup()

    def test_family_import_does_not_expand_operator_schema(self):
        td=tempfile.TemporaryDirectory();s=Store(Path(td.name)/'x.sqlite');s.import_data(BASE);before=(s.db.execute("select count(*) from atoms where kind='operator'").fetchone()[0],s.db.execute('select count(*) from operator_roles').fetchone()[0]);s.import_data(FAMILY);after=(s.db.execute("select count(*) from atoms where kind='operator'").fetchone()[0],s.db.execute('select count(*) from operator_roles').fetchone()[0]);self.assertEqual(before,after);self.assertEqual(before,(5,20));s.db.close();td.cleanup()


    def test_world_occurrence_atoms_never_enter_authority_hash(self):
        td,s,rt=make()
        try:
            before=s.authority_hash(s.generation);rt.process('My mother in-law arrived today.');world=s.db.execute("select count(*) from atoms where authority_scope='world'").fetchone()[0];self.assertGreater(world,0);rt.reload_authority();self.assertEqual(before,rt.runtime_attestation['authority_generation_hash'])
        finally:s.db.close();td.cleanup()

    def test_reimport_semantic_replay_stable(self):
        td,s,rt=make()
        try:before=s.snapshot_hash();s.import_data(FAMILY);self.assertEqual(before,s.snapshot_hash())
        finally:s.db.close();td.cleanup()

    def test_unsupported_multivalue_role_fails(self):
        td=tempfile.TemporaryDirectory();s=Store(Path(td.name)/'m.sqlite')
        try:
            bad=Path(td.name)/'bad.json';bad.write_text(json.dumps({'atoms':[{'ref':'op:x','kind':'operator'}],'operator_roles':[{'operator_ref':'op:x','role_ref':'role:x','cardinality':'many'}]}))
            with self.assertRaises(ValueError):s.import_data(bad)
        finally:s.db.close();td.cleanup()

if __name__=='__main__':unittest.main(verbosity=2)
