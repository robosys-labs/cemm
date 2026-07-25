#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sqlite3, sys
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cemm.forms import FormPack, FormProcessor, ConstructionCandidateGenerator, generic_designation_learning_packet
from cemm.model import Fact
from cemm.response import ResponseCSIR, pointerize_response

FORM=ROOT/'cemm/form_packs/en.json'
LANG=ROOT/'cemm/language_packs/en.json'
SEED=ROOT/'cemm/data/conversation_foundation.json'

class Frame:
    self_ref='participant:system'; speaker_ref='participant:user'; addressee_ref='participant:system'; conversation_ref='conversation:test'
    def resolve_requirement(self,features):
        role=features.get('participant_role'); person=features.get('person')
        if role=='speaker' or (not role and person=='first'): return self.speaker_ref
        if role=='addressee' or (not role and person=='second'): return self.addressee_ref
        if role=='self': return self.self_ref
        return None

class Store:
    def __init__(self):
        self.db=sqlite3.connect(':memory:'); self.db.row_factory=sqlite3.Row
        self.db.executescript('''
        CREATE TABLE reference_forms(language TEXT,surface TEXT,features TEXT,bound_ref TEXT,weight REAL);
        CREATE TABLE designation_index(label_ref TEXT,target_ref TEXT,label_type_ref TEXT,surface TEXT,language TEXT,script TEXT,prior REAL,preferred INTEGER,context_ref TEXT);
        CREATE TABLE discourse_entities(atom_ref TEXT,salience REAL,last_turn INTEGER);
        ''')
        self.atoms={
          'participant:user':{'kind':'participant','metadata':'{}'},'participant:system':{'kind':'participant','metadata':'{}'},
          'label:name':{'kind':'label_type','metadata':'{}'},'label:lexical':{'kind':'label_type','metadata':'{}'},
          'concept:laughing_out_loud':{'kind':'concept','metadata':'{}'},
        }
        refs=[
          ('en','my',{'person':'first','possessive':True},None,1.3),
          ('en','your',{'person':'second','possessive':True},None,1.3),
          ('en','i',{'person':'first'},None,1.3),('en','you',{'person':'second'},None,1.3),
        ]
        self.db.executemany('INSERT INTO reference_forms VALUES(?,?,?,?,?)',[(a,b,json.dumps(c),d,e) for a,b,c,d,e in refs])
        rows=[
          ('d:name','label:name','label:lexical','name','en','Latn',1.5,1,None),
          ('d:lol','concept:laughing_out_loud','label:lexical','lol','en','Latn',1.5,1,None),
        ]
        self.db.executemany('INSERT INTO designation_index VALUES(?,?,?,?,?,?,?,?,?)',rows)
    def revisions(self): return {'world_revision':1}
    def atom(self,ref):
        x=self.atoms.get(ref)
        return None if x is None else {'ref':ref,**x}
    def matching_facts(self,*args,**kwargs): return []

def canonical_hash(data):
    return hashlib.sha256(json.dumps({k:v for k,v in data.items() if k!='pack_hash'},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def main():
    fp=json.loads(FORM.read_text()); lp=json.loads(LANG.read_text()); seed=json.loads(SEED.read_text())
    assert canonical_hash(fp)==fp['pack_hash']
    assert canonical_hash(lp)==lp['pack_hash']
    assert lp['form_pack_hash']==fp['pack_hash']
    assert set(lp['operators'])=={'op:designation','op:event','op:relation','op:state','op:type'}

    atoms={x['ref'] for x in seed['atoms']}
    assert len(atoms)==len(seed['atoms']) and len(seed['atoms'])>=100 and len(seed['facts'])>=150
    external_allowed={
      'cap:interpret','cap:realize','concept:digital_agent','concept:information','concept:meaning','concept:query','concept:response',
      'domain:categorical','label:lexical','label:name','label:name_alias','label:name_full','op:designation','op:relation',
      'participant:system','participant:user','rel:depends_on','rel:dimension_domain','rel:entitles_capability','rel:entitles_resource',
      'rel:subtype_of','rel:value_of_dimension','value:contradicted','value:learned','value:negative','value:supported','value:uncertain','value:unknown'
    }
    allowed_ops={'op:designation','op:type','op:relation','op:state','op:event'}
    seen=set()
    for fact in seed['facts']:
        assert fact['operator'] in allowed_ops
        sig=json.dumps((fact['operator'],fact.get('stance','support'),fact.get('args',{})),sort_keys=True,separators=(',',':'))
        assert sig not in seen; seen.add(sig)
        for value in fact.get('args',{}).values():
            if isinstance(value,str) and value not in atoms:
                assert value in external_allowed, value

    store=Store(); pack=FormPack(FORM); proc=FormProcessor(store,'en',1,pack,semantic_function_forms=lp['function_forms'])
    frame=Frame(); gen=ConstructionCandidateGenerator(pack,max_matches=64)
    lat=proc.resolve("What's your name?",frame)
    variants={x.text.casefold() for x in lat.normalization_candidates}
    assert "what's your name?" in variants and 'what is your name?' in variants
    ev=gen.evidence(lat,frame)
    packets=[gen.instantiate(x,frame,'en') for x in ev]
    assert any((p.get('query') or {}).get('qualifiers',{}).get('query_kind')=='designation_property' for p in packets)

    lat=proc.resolve('Well my name is Opata',frame)
    ev=gen.evidence(lat,frame); packets=[gen.instantiate(x,frame,'en') for x in ev]
    claims=[p for p in packets if p.get('apps') and p['apps'][0]['operator']=='op:designation']
    assert claims
    assert any(p['apps'][0]['args']['role:target']=='participant:user' and p['apps'][0]['args']['role:surface']['literal']['value']=='Opata' for p in claims)

    lat=proc.resolve('lol, what does that mean?',frame)
    ev=gen.evidence(lat,frame); packets=[gen.instantiate(x,frame,'en') for x in ev]
    assert any(p.get('qualifiers',{}).get('learning_operation')=='resolve_designation' for p in packets)
    unknown=generic_designation_learning_packet('quux','en')
    assert unknown['query']['restrictions'][0]['operator']=='op:designation'
    assert unknown['query']['restrictions'][0]['args']['role:surface']['literal']['value']=='quux'

    learning=ResponseCSIR('r','answer_bindings','participant:user',facts=(Fact('f','op:designation',{
      'role:target':'concept:laughing_out_loud','role:label_type':'label:lexical','role:surface':{'literal':{'type':'text','value':'lol'}},'role:language':{'literal':{'type':'text','value':'en'}}}),),bindings=({'?q0':'concept:laughing_out_loud','?q1':'label:lexical'},),qualifiers={'query_kind':'designation_learning','property_ref':'label:lexical','learning_operation':'resolve_designation'},evidence_literals=('lol',))
    semantic,_=pointerize_response(learning)
    allowed={e['semantic']:e['surface_plan'] for e in lp['response_examples']}
    assert semantic in allowed, semantic
    assert allowed[semantic]=='In this context, @E0 refers to @A1.'

    name=ResponseCSIR('n','answer_bindings','participant:user',facts=(Fact('nf','op:designation',{
      'role:target':'participant:system','role:label_type':'label:name','role:surface':{'literal':{'type':'text','value':'CEMM'}}}),),bindings=({'?q0':{'literal':{'type':'text','value':'CEMM'}}},),qualifiers={'query_kind':'designation_property','property_ref':'label:name'})
    name_semantic,_=pointerize_response(name)
    assert name_semantic in allowed, name_semantic

    print(json.dumps({'status':'passed','form_pack_hash':fp['pack_hash'],'language_pack_hash':lp['pack_hash'],'seed_atoms':len(seed['atoms']),'seed_facts':len(seed['facts']),'constructions':len(fp['constructions'])},indent=2))
if __name__=='__main__': main()
