#!/usr/bin/env python3
"""Generate a reviewed, language-neutral conversational foundation extension.

The seed expands reusable semantic primitives and reviewed designations; it does
not add phrase routers, transcript checks, or new operator shapes.
"""
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def atom(ref,kind,**metadata):
 return {'ref':ref,'kind':kind,'metadata':{'foundational':True,**metadata}}
def lit(v,t='text'): return {'literal':{'type':t,'value':v}}
def fact(op,args,ref=None,source='seed'):
 d={'operator':op,'args':args,'stance':'support','confidence':1.0,'authority_status':'reviewed','source_ref':source}
 if ref: d['fact_ref']=ref
 return d

def rel(s,r,o,ref=None): return fact('op:relation',{'role:subject':s,'role:relation':r,'role:object':o},ref)
def designation(target,surface,label='label:lexical',lang='en',preferred=True,prior=1.0):
 return fact('op:designation',{
  'role:target':target,'role:label_type':label,'role:surface':lit(surface),
  'role:language':lit(lang),'role:script':lit('Latn'),
  'role:prior':lit(float(prior),'float'),'role:preferred':lit(bool(preferred),'bool')
 })

atoms=[]; facts=[]
# General semantic families required for conversation, learning and repair.
concepts=[
 'concept:agent','concept:participant','concept:person','concept:entity','concept:object','concept:place','concept:time','concept:quantity',
 'concept:language','concept:language_form','concept:lexical_form','concept:construction','concept:designation','concept:identity','concept:definition',
 'concept:learning','concept:teaching','concept:memory','concept:knowledge','concept:question','concept:answer','concept:clarification','concept:correction',
 'concept:reference','concept:context','concept:conversation','concept:communication','concept:preference','concept:emotion','concept:location',
 'concept:operation','concept:resource','concept:process','concept:result','concept:property','concept:identifier','concept:abbreviation','concept:acronym',
 'concept:laughing_out_loud','concept:gratitude','concept:apology','concept:agreement','concept:disagreement','concept:possibility','concept:necessity'
]
for ref in concepts: atoms.append(atom(ref,'concept',conversation_foundation=True))
relations=[
 'rel:equivalent_to','rel:refers_to','rel:synonym_of','rel:antonym_of','rel:part_of','rel:located_in','rel:owns','rel:prefers',
 'rel:knows','rel:about','rel:before','rel:after','rel:caused_by','rel:enables','rel:requires','rel:source_of','rel:evidence_for',
 'rel:has_property','rel:has_identifier','rel:has_definition','rel:communicates_with','rel:answers','rel:asks','rel:corrects','rel:clarifies'
]
for ref in relations: atoms.append(atom(ref,'relation_type',conversation_foundation=True,user_visible=True))
events=[
 'event:ask','event:answer','event:learn','event:teach','event:remember','event:forget','event:clarify','event:correct','event:retract',
 'event:thank','event:apologize','event:communicate','event:define','event:identify','event:name','event:confirm','event:deny','event:explain'
]
for ref in events: atoms.append(atom(ref,'event_type',conversation_foundation=True))
labels=['label:title','label:identifier','label:username','label:abbreviation','label:acronym','label:nickname','label:expansion','label:translation']
for ref in labels: atoms.append(atom(ref,'label_type',conversation_foundation=True))
capabilities=['cap:learn','cap:query','cap:clarify','cap:remember','cap:designate','cap:explain']
for ref in capabilities: atoms.append(atom(ref,'capability',conversation_foundation=True))
resources=['resource:semantic_store','resource:designation_index','resource:form_processor','resource:inference_engine','resource:common_ground']
for ref in resources: atoms.append(atom(ref,'resource',conversation_foundation=True))
dimensions=[
 'dim:availability','dim:confidence','dim:location','dim:quantity','dim:preference','dim:emotional_state','dim:memory_status','dim:learning_status','dim:communication_status'
]
for ref in dimensions: atoms.append(atom(ref,'state_dimension',conversation_foundation=True,exclusive=True,cardinality='one',domain_type='categorical'))
values=[
 'value:available','value:unavailable','value:known','value:remembered','value:forgotten','value:learning','value:learned_confirmed',
 'value:communicating','value:idle','value:positive','value:neutral','value:possible','value:necessary'
]
for ref in values: atoms.append(atom(ref,'value',conversation_foundation=True))
# Label hierarchy: generic designation queries can constrain a family through normal graph inference.
for child,parent in [
 ('label:title','label:lexical'),('label:identifier','label:lexical'),('label:username','label:identifier'),
 ('label:abbreviation','label:lexical'),('label:acronym','label:abbreviation'),('label:nickname','label:name_alias'),
 ('label:expansion','label:lexical'),('label:translation','label:lexical')
]: facts.append(rel(child,'rel:subtype_of',parent))
# Concept hierarchy and generic definitions.
for child,parent in [
 ('concept:agent','concept:entity'),('concept:participant','concept:entity'),('concept:person','concept:participant'),
 ('concept:object','concept:entity'),('concept:place','concept:entity'),('concept:language_form','concept:information'),
 ('concept:lexical_form','concept:language_form'),('concept:construction','concept:language_form'),
 ('concept:designation','concept:information'),('concept:definition','concept:information'),('concept:question','concept:query'),
 ('concept:answer','concept:response'),('concept:clarification','concept:response'),('concept:correction','concept:response'),
 ('concept:conversation','concept:communication'),('concept:operation','concept:process'),('concept:learning','concept:process'),
 ('concept:teaching','concept:process'),('concept:memory','concept:resource'),('concept:knowledge','concept:information'),
 ('concept:identifier','concept:designation'),('concept:abbreviation','concept:designation'),('concept:acronym','concept:abbreviation')
]: facts.append(rel(child,'rel:subtype_of',parent))
# Operational profile additions.
for cap in capabilities: facts.append(rel('concept:digital_agent','rel:entitles_capability',cap))
for resource in resources: facts.append(rel('concept:digital_agent','rel:entitles_resource',resource))
for cap,dependency in [
 ('cap:learn','cap:interpret'),('cap:learn','resource:semantic_store'),('cap:learn','resource:designation_index'),
 ('cap:query','cap:interpret'),('cap:query','resource:inference_engine'),('cap:clarify','cap:query'),('cap:clarify','cap:realize'),
 ('cap:remember','resource:semantic_store'),('cap:remember','resource:common_ground'),('cap:designate','resource:designation_index'),
 ('cap:explain','cap:query'),('cap:explain','cap:realize')
]: facts.append(rel(cap,'rel:depends_on',dependency))
# Dimension domains and exact value-to-dimension links.
value_dims={
 'dim:availability':['value:available','value:unavailable'],
 'dim:confidence':['value:uncertain','value:supported','value:contradicted'],
 'dim:memory_status':['value:remembered','value:forgotten','value:unknown'],
 'dim:learning_status':['value:learning','value:learned','value:learned_confirmed','value:unknown'],
 'dim:communication_status':['value:communicating','value:idle'],
 'dim:emotional_state':['value:positive','value:neutral','value:negative'],
}
for dim,vals in value_dims.items():
 facts.append(rel(dim,'rel:dimension_domain','domain:categorical'))
 for value in vals: facts.append(rel(value,'rel:value_of_dimension',dim))
# System identity and acronym expansion.
facts += [
 designation('participant:system','CEMM','label:name','en',True,2.0),
 designation('participant:system','Contextual Event Memory Model','label:name_full','en',True,1.8),
 designation('participant:system','CEMM','label:acronym','en',True,1.6),
 designation('participant:user','you','label:lexical','en',True,1.1),
 designation('participant:user','user','label:title','en',False,0.8),
]
# Reviewed common lexical designations. A form can resolve to existing meaning before any user probe.
lexemes={
 'concept:laughing_out_loud':[('laughing out loud','label:name_full',True,1.8),('LOL','label:acronym',True,1.7),('lol','label:lexical',True,1.6)],
 'concept:meaning':[('meaning','label:lexical',True,1.3),('sense','label:lexical',False,0.8)],
 'concept:definition':[('definition','label:lexical',True,1.3)],
 'concept:designation':[('designation','label:lexical',True,1.2),('label','label:lexical',False,0.9)],
 'concept:learning':[('learning','label:lexical',True,1.2)],
 'concept:memory':[('memory','label:lexical',True,1.2)],
 'concept:knowledge':[('knowledge','label:lexical',True,1.2)],
 'concept:question':[('question','label:lexical',True,1.2)],
 'concept:answer':[('answer','label:lexical',True,1.2)],
 'concept:clarification':[('clarification','label:lexical',True,1.2)],
 'concept:correction':[('correction','label:lexical',True,1.2)],
 'concept:conversation':[('conversation','label:lexical',True,1.2)],
 'concept:context':[('context','label:lexical',True,1.2)],
 'concept:identity':[('identity','label:lexical',True,1.2)],
 'concept:property':[('property','label:lexical',True,1.2)],
 'concept:preference':[('preference','label:lexical',True,1.2)],
 'concept:location':[('location','label:lexical',True,1.2)],
 'concept:quantity':[('quantity','label:lexical',True,1.2)],
}
for target,entries in lexemes.items():
 for surface,label,preferred,prior in entries: facts.append(designation(target,surface,label,'en',preferred,prior))
for ref in concepts:
 if ref not in lexemes:
  facts.append(designation(ref,ref.split(':',1)[1].replace('_',' '),'label:lexical','en',True,1.0))
# Designations for reusable operator fillers and response properties.
for ref in relations+events+capabilities+resources+dimensions+values+labels:
 surface=ref.split(':',1)[1].replace('_',' ')
 facts.append(designation(ref,surface,'label:lexical','en',True,1.0))
# Basic multilingual designations demonstrate shared meaning / separate surfaces.
for target,en,es in [
 ('concept:question','question','pregunta'),('concept:answer','answer','respuesta'),('concept:meaning','meaning','significado'),
 ('concept:learning','learning','aprendizaje'),('concept:memory','memory','memoria'),('concept:knowledge','knowledge','conocimiento'),
 ('concept:clarification','clarification','aclaración'),('concept:conversation','conversation','conversación')
]:
 facts.append(designation(target,es,'label:translation','es',True,1.1))

# De-duplicate atoms/facts deterministically.
atom_map={a['ref']:a for a in atoms}
def fkey(f): return json.dumps([f['operator'],f.get('stance','support'),f['args']],sort_keys=True,ensure_ascii=False,separators=(',',':'))
fact_map={fkey(f):f for f in facts}
data={
 'atoms':[atom_map[k] for k in sorted(atom_map)],
 'operator_roles':[], 'control_symbols':{}, 'reference_forms':[],
 'facts':[fact_map[k] for k in sorted(fact_map)], 'rules':[]
}
out=ROOT/'cemm/data/conversation_foundation.json'; out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(out),'atoms':len(data['atoms']),'facts':len(data['facts'])},indent=2))
