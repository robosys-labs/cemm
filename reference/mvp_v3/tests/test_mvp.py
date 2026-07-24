from __future__ import annotations
import json, tempfile, sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from cemm_mvp import Store,Runtime,Inference,AmbiguousReferent,MODEL_CACHE  # noqa
from trainer import compile_corpus
BASE=ROOT/'knowledge/base.json';FAMILY=ROOT/'knowledge/family_knowledge.json';EN=ROOT/'language_packs/en.json';ES=ROOT/'language_packs/es.json'

def make(lang='en',family=True):
    td=tempfile.TemporaryDirectory();s=Store(Path(td.name)/'mvp.sqlite');s.import_data(BASE)
    if family:s.import_data(FAMILY)
    rt=Runtime(s,EN if lang=='en' else ES);return td,s,rt

def rules(node):
    if not node:return set()
    out={node['rule_ref']} if node.get('rule_ref') else set()
    for p in node.get('parents',[]):out|=rules(p)
    return out

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        td,s,rt=make();rt.process('What is evidence?');s.db.close();td.cleanup()

    def test_base_has_no_language_or_realization_examples(self):
        d=json.loads(BASE.read_text());self.assertNotIn('language_examples',d);self.assertNotIn('realization_examples',d)

    def test_trainer_is_deterministic_and_language_generic(self):
        a=compile_corpus(ROOT/'training/en_seed.json');b=compile_corpus(ROOT/'training/en_seed.json');self.assertEqual(a['pack_hash'],b['pack_hash']);self.assertTrue(a['interpretation_examples']);self.assertTrue(a['realization_examples'])

    def test_kernel_has_no_domain_or_literal_response_hardcoding(self):
        src=(ROOT/'cemm_mvp.py').read_text().lower()
        for x in ('mother_in_law','mother-in-law','spouse','wife','husband','married','president','doctor','i have conflicting evidence','i have stored that meaning','meaning is unresolved','evidence is insufficient'):
            self.assertNotIn(x,src)

    def test_no_opaque_response_atoms(self):
        d=json.loads(BASE.read_text());self.assertFalse(any(a['ref'].startswith('resp:') for a in d['atoms']))

    def test_greeting_is_grounded_semantics_with_pointer_nlg(self):
        td,s,rt=make()
        try:
            r=rt.process('Hi.');self.assertEqual(r['response'],'Hello.');self.assertEqual(r['response_plan']['goal'],'goal:greet');p=r['realization_proof'];self.assertTrue(p['verified']);self.assertFalse(p['roundtrip_used']);self.assertEqual(p['pointers'][0]['semantic_ref'],'value:greeting_ack')
        finally:s.db.close();td.cleanup()

    def test_operational_words_are_meaning_db_concepts(self):
        td,s,rt=make()
        try:
            self.assertEqual(rt.process('What is evidence?')['response'],'Evidence is information.')
            self.assertEqual(rt.process('What is conflict?')['response'],'Conflict is a state.')
            self.assertEqual(rt.process('What is meaning?')['response'],'Meaning is structured semantic content.')
        finally:s.db.close();td.cleanup()

    def test_unknown_and_conflict_responses_are_grounded_plans(self):
        td,s,rt=make()
        try:
            u=rt.process('Am I married?');self.assertEqual(u['result'],'unknown');self.assertEqual(u['response'],'Evidence is insufficient.');self.assertEqual(u['response_plan']['goal'],'goal:report_uncertainty')
            with s.db:
                g=s.begin('conflict');o=s.add_observation('support',{},'und','test',g);s.insert_app('op:state',{'role:subject':'participant:user','role:dimension':'dim:marital_status','role:value':'value:married'},g,o,'support');o2=s.add_observation('deny',{},'und','test',g);s.insert_app('op:state',{'role:subject':'participant:user','role:dimension':'dim:marital_status','role:value':'value:married'},g,o2,'deny');s.finish(g)
            c=rt.process('Am I married?');self.assertEqual(c['result'],'conflict');self.assertEqual(c['response'],'Evidence is conflicting.');self.assertEqual(c['response_plan']['goal'],'goal:report_conflict')
        finally:s.db.close();td.cleanup()

    def test_family_reasoning_still_answers_marriage(self):
        td,s,rt=make()
        try:
            rt.process('My mother in-law arrived today.');a=rt.process('Am I married?');self.assertEqual(a['response'],'Yes.');self.assertTrue({'rule:mil-decompose','rule:subrelation-inheritance','rule:relation-object-state'}.issubset(rules(a['proof'])))
        finally:s.db.close();td.cleanup()

    def test_workspace_is_bounded_and_contains_self_state(self):
        td,s,rt=make()
        try:
            rt.process('My mother in-law arrived today.');a=rt.process('Am I married?');self.assertLessEqual(len(a['workspace']['selected']),24);self.assertTrue(any(x['features']['self']>0 for x in a['workspace']['selected']))
        finally:s.db.close();td.cleanup()

    def test_self_state_transitions_are_semantic_session_state(self):
        td,s,rt=make()
        try:
            r=rt.process('totally unknown flibbertigibbet');self.assertEqual(r['status'],'frontier');self.assertEqual(r['self_state']['dim:response_state'],'value:confused');self.assertEqual(r['self_state']['dim:interpretation_state'],'value:unresolved')
        finally:s.db.close();td.cleanup()

    def test_pointer_verification_replaces_mandatory_roundtrip(self):
        td,s,rt=make()
        try:
            p=rt.process('Am I married?')['realization_proof'];self.assertEqual(p['verification_mode'],'semantic_pointer_provenance');self.assertFalse(p['roundtrip_used']);self.assertTrue(p['verified']);self.assertTrue(p['language_pack_hash'])
        finally:s.db.close();td.cleanup()

    def test_language_pack_is_pinned_separately_from_meaning_hash(self):
        td,s,rt=make()
        try:
            self.assertEqual(rt.runtime_attestation['authority_generation_hash'],s.authority_hash(rt.runtime_attestation['authority_generation']));self.assertEqual(rt.runtime_attestation['language_pack_hash'],json.loads(EN.read_text())['pack_hash'])
        finally:s.db.close();td.cleanup()

    def test_inference_is_ephemeral_and_queries_do_not_bloat(self):
        td,s,rt=make()
        try:
            rt.process('My mother in-law arrived today.');before=tuple(s.db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ('applications','bindings','claims','proof_links'));[rt.process('Am I married?') for _ in range(4)];after=tuple(s.db.execute(f'SELECT count(*) FROM {t}').fetchone()[0] for t in ('applications','bindings','claims','proof_links'));self.assertEqual(before,after)
        finally:s.db.close();td.cleanup()

    def test_same_name_identity_conflict_is_not_merged(self):
        td,s,rt=make()
        try:
            with self.assertRaises(AmbiguousReferent):s.resolve_label('Alex Kim','en')
            self.assertEqual(s.resolve_label('Alex J. Kim','en'),'entity:alex_a');s.touch(['entity:alex_a']);self.assertEqual(s.resolve_label('Alex Kim','en'),'entity:alex_a')
        finally:s.db.close();td.cleanup()

    def test_contextual_realization_labels_do_not_corrupt_input_resolution(self):
        td,s,rt=make()
        try:
            rt.process('My mother in-law arrived today.');self.assertEqual(rt.process('Is she a human?')['response'],'Yes.');self.assertEqual(rt.process('Who is Ada?')['response'].split()[0],'Ada')
        finally:s.db.close();td.cleanup()

    def test_multilingual_pack_reuses_same_meaning_and_rules(self):
        td,s,rt=make('es')
        try:
            self.assertEqual(rt.process('Mi suegra llegó hoy.')['status'],'learned');a=rt.process('¿Estoy casado?');self.assertEqual(a['response'],'Sí.');self.assertIn('rule:mil-decompose',rules(a['proof']))
        finally:s.db.close();td.cleanup()

    def test_description_hides_operational_policy_edges(self):
        td,s,rt=make()
        try:
            r=rt.process('What is evidence?')['response'];self.assertNotIn('goal:',r);self.assertNotIn('response_state_subject',r)
        finally:s.db.close();td.cleanup()

    def test_family_import_does_not_expand_operator_schema(self):
        td=tempfile.TemporaryDirectory();s=Store(Path(td.name)/'x.sqlite');s.import_data(BASE);before=(s.db.execute("select count(*) from atoms where kind='operator'").fetchone()[0],s.db.execute('select count(*) from operator_roles').fetchone()[0]);s.import_data(FAMILY);after=(s.db.execute("select count(*) from atoms where kind='operator'").fetchone()[0],s.db.execute('select count(*) from operator_roles').fetchone()[0]);self.assertEqual(before,after);self.assertEqual(before,(5,20));s.db.close();td.cleanup()

    def test_provisional_rules_do_not_execute(self):
        td,s,rt=make()
        try:
            with s.db:
                g=s.begin('p');o=s.add_observation('Ada human',{},'und','test',g);s.insert_app('op:type',{'role:instance':'entity:ada','role:class':'concept:human'},g,o);rule={'rule_ref':'r:p','rule_kind':'entailment','authority_status':'provisional','if':[{'operator':'op:type','args':{'role:instance':'?x','role:class':'concept:human'}}],'then':[{'operator':'op:type','args':{'role:instance':'?x','role:class':'concept:doctor'}}]};s.validate_rule(rule);s.exact('rules',['rule_ref','rule_kind','antecedent','consequent','confidence','authority_status','generation'],[rule['rule_ref'],rule['rule_kind'],json.dumps(rule['if'],sort_keys=True,separators=(',',':')),json.dumps(rule['then'],sort_keys=True,separators=(',',':')),1.0,'provisional',g],['rule_ref'],{'generation'});s.finish(g)
            facts,_=Inference(s).closure();self.assertFalse(any(f.operator=='op:type' and f.args.get('role:instance')=='entity:ada' and f.args.get('role:class')=='concept:doctor' for f in facts))
        finally:s.db.close();td.cleanup()

    def test_training_corpus_contains_structured_semantics_not_compiled_program_strings(self):
        d=json.loads((ROOT/'training/en_seed.json').read_text());self.assertTrue(all('semantic' in x and 'program' not in x for x in d['interpretation_examples']))

    def test_authority_attestation_is_stable_across_mutable_learning(self):
        td,s,rt=make()
        try:
            g=rt.runtime_attestation['authority_generation'];before=s.authority_hash(g);rt.process('My mother in-law arrived today.');self.assertEqual(before,s.authority_hash(g));self.assertNotEqual(rt.runtime_attestation['read_generation'],s.generation)
        finally:s.db.close();td.cleanup()

    def test_nlg_requires_authorized_learned_transform_class(self):
        td,s,rt=make()
        try:
            p=rt.process('Am I married?')['realization_proof'];self.assertTrue(p['authorized_transform']);self.assertTrue(p['verified'])
        finally:s.db.close();td.cleanup()

    def test_internal_ids_never_emit_when_no_referring_expression(self):
        td,s,rt=make()
        try:
            rt.process('My mother in-law arrived today.');r=rt.process('Who is she?');self.assertNotRegex(r.get('response',''),r'(?:atom|existential|app|fact):[0-9a-fA-F]+')
        finally:s.db.close();td.cleanup()

    def test_repeated_observations_are_distinct_but_semantic_apps_deduplicate(self):
        td,s,rt=make()
        try:
            a=rt.process('My mother in-law arrived today.');b=rt.process('My mother in-law arrived today.');self.assertEqual(a['new_atoms'],b['new_atoms']);self.assertEqual(s.db.execute('select count(*) from observations where surface=?',('My mother in-law arrived today.',)).fetchone()[0],2);self.assertEqual(s.db.execute("select count(*) from applications where operator_ref='op:event'").fetchone()[0],1)
        finally:s.db.close();td.cleanup()

    def test_causal_rules_are_not_asserted_as_actual_world_truth(self):
        td,s,rt=make()
        try:
            learned=rt.process('My mother in-law arrived today.');mil=learned['packet']['apps'][0]['args']['role:subject'];facts,_=Inference(s).closure();self.assertFalse(any(f.operator=='op:state' and f.args.get('role:subject')==mil and f.args.get('role:dimension')=='dim:location_status' and f.args.get('role:value')=='value:present' for f in facts))
        finally:s.db.close();td.cleanup()

    def test_reimport_is_semantically_replay_stable(self):
        td,s,rt=make()
        try:
            before=s.snapshot_hash();s.import_data(FAMILY);self.assertEqual(before,s.snapshot_hash())
        finally:s.db.close();td.cleanup()

    def test_unicode_casefold_label_resolution(self):
        td,s,rt=make('es')
        try:
            self.assertEqual(s.resolve_label('CÓNYUGE','es'),s.resolve_label('cónyuge','es'))
        finally:s.db.close();td.cleanup()

    def test_unsupported_multivalued_role_fails_explicitly(self):
        td=tempfile.TemporaryDirectory();s=Store(Path(td.name)/'m.sqlite')
        try:
            bad=Path(td.name)/'bad.json';bad.write_text(json.dumps({'atoms':[{'ref':'op:x','kind':'operator'}], 'operator_roles':[{'operator_ref':'op:x','role_ref':'role:x','cardinality':'many'}]}))
            with self.assertRaises(ValueError):s.import_data(bad)
        finally:s.db.close();td.cleanup()

    def test_denied_new_state_does_not_supersede_supported_current_state(self):
        td,s,rt=make()
        try:
            with s.db:
                g=s.begin('state');o=s.add_observation('ready',{},'und','test',g);a=s.insert_app('op:state',{'role:subject':'participant:system','role:dimension':'dim:response_state','role:value':'value:ready'},g,o,'support');o2=s.add_observation('not processing',{},'und','test',g);s.insert_app('op:state',{'role:subject':'participant:system','role:dimension':'dim:response_state','role:value':'value:processing'},g,o2,'deny');s.finish(g)
            self.assertIsNone(s.db.execute("select valid_to from claims where app_ref=? and stance='support'",(a,)).fetchone()[0])
        finally:s.db.close();td.cleanup()

    def test_inference_budget_exhaustion_is_not_reported_as_unknown(self):
        td,s,rt=make()
        try:
            rt.inf=Inference(s,max_rounds=0,max_facts=1);r=rt.process('Am I married?');self.assertEqual(r['status'],'frontier');self.assertEqual(r['frontier']['reason'],'inference_incomplete')
        finally:s.db.close();td.cleanup()

    def test_multisentence_clause_composition_and_coreference(self):
        td,s,rt=make()
        try:
            r=rt.process('Ada is a doctor. She arrived today.');self.assertEqual(r['status'],'learned');apps=r['packet']['apps'];self.assertEqual(len(apps),2);self.assertEqual(apps[0]['args']['role:instance'],apps[1]['args']['role:actor'])
        finally:s.db.close();td.cleanup()

    def test_self_epistemic_state_recovers_after_supported_answer(self):
        td,s,rt=make()
        try:
            u=rt.process('Am I married?');self.assertEqual(u['self_state']['dim:epistemic_state'],'value:insufficient');rt.process('My mother in-law arrived today.');a=rt.process('Am I married?');self.assertEqual(a['response'],'Yes.');self.assertEqual(a['self_state']['dim:epistemic_state'],'value:sufficient')
        finally:s.db.close();td.cleanup()

if __name__=='__main__':unittest.main(verbosity=2)
