#!/usr/bin/env python3
"""Generate the self-contained English runtime pack from reviewed structures."""
from __future__ import annotations
import hashlib, json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
FORM=json.loads((ROOT/'cemm/form_packs/en.json').read_text(encoding='utf-8'))
def canonical(v): return json.dumps(v,sort_keys=True,ensure_ascii=False,separators=(',',':'))
def h(v): return hashlib.sha256(canonical(v).encode()).hexdigest()

def ex(ref,input_,force,apps=(),projection=(),describe='NONE'):
 return {'example_ref':ref,'input':input_,'target':{'force':force,'intent':'describe' if force=='description_request' else 'query' if force=='query' else 'assert','describe_source':describe,'apps':list(apps),'projection':list(projection)},'weight':1.0}
def app(op,**bindings): return {'operator':op,'bindings':bindings}

structured=[
 ex('en:greet:hi','Hi','claim',[app('op:event',**{'role:event':'NEW_EVENT_0','role:type':'A0','role:actor':'FRAME_SPEAKER'})]),
 ex('en:greet:hello','Hello.','claim',[app('op:event',**{'role:event':'NEW_EVENT_0','role:type':'A0','role:actor':'FRAME_SPEAKER'})]),
 ex('en:type:claim','@A0<entity> is a @A1<concept>.','claim',[app('op:type',**{'role:instance':'A0','role:class':'A1'})]),
 ex('en:type:query','Is @A0<entity> a @A1<concept>?','query',[app('op:type',**{'role:instance':'A0','role:class':'A1'})]),
 ex('en:state:claim','@A0<entity> is @A1<value>.','claim',[app('op:state',**{'role:subject':'A0','role:dimension':'DIM_OF_A1','role:value':'A1'})]),
 ex('en:state:boolean-query','Is @A0<entity> @A1<value>?','query',[app('op:state',**{'role:subject':'A0','role:dimension':'DIM_OF_A1','role:value':'A1'})]),
 ex('en:state:open-query','How is @A0<participant>?','query',[app('op:state',**{'role:subject':'A0','role:dimension':'Q0','role:value':'Q1'})],['Q0','Q1']),
 ex('en:state:property-query','What is the @A0<state_dimension> of @A1<entity>?','query',[app('op:state',**{'role:subject':'A1','role:dimension':'A0','role:value':'Q0'})],['Q0']),
 ex('en:relation:claim','@A0<entity> is a @A1<relation_type> of @A2<entity>.','claim',[app('op:relation',**{'role:subject':'A0','role:relation':'A1','role:object':'A2'})]),
 ex('en:relation:query','Is @A0<entity> a @A1<relation_type> of @A2<entity>?','query',[app('op:relation',**{'role:subject':'A0','role:relation':'A1','role:object':'A2'})]),
 ex('en:event:claim','@A0<entity> @A1<event_type> @A2<time>.','claim',[app('op:event',**{'role:event':'NEW_EVENT_0','role:type':'A1','role:actor':'A0','role:time':'A2'})]),
 ex('en:describe:who','Who is @A0<entity>?','description_request',[],[], 'A0'),
 ex('en:describe:what','What is @A0<concept>?','description_request',[],[], 'A0'),
 ex('en:concept:subtype','@A0<concept> is a @A1<concept>.','claim',[app('op:relation',**{'role:subject':'A0','role:relation':'CONST0','role:object':'A1'})]),
]

response_examples=[
 ('confirm','RESPONSE confirm','Yes.'),
 ('deny','RESPONSE deny','No.'),
 ('conflict','RESPONSE report_conflict','The evidence conflicts.'),
 ('uncertain','RESPONSE report_target_uncertainty','I do not have enough evidence.'),
 ('clarify','RESPONSE request_targeted_clarification EVIDENCE @E0','Could you clarify @E0?'),
 ('capability','RESPONSE report_capability TARGET @A0 SCORE @N0','My @A0 is at @N0 percent.'),
 ('ack','RESPONSE acknowledge_claim','I recorded that claim.'),
 ('decline','RESPONSE decline_directive','I cannot perform that action.'),
 ('operation','RESPONSE report_operation_result','The operation is complete.'),
 ('greet','RESPONSE greet','Hello.'),
 ('property','RESPONSE answer_bindings QUERY_KIND designation_property PROPERTY @A0 BINDING ?q0 @E0','The @A0 is @E0.'),
 ('learned-binding','RESPONSE answer_bindings QUERY_KIND designation_learning PROPERTY @A0 BINDING ?q0 @A1 ?q1 @A0 EVIDENCE @E0','In this context, @E0 refers to @A1.'),
 ('state-answer','RESPONSE answer_bindings QUERY_KIND state_query PROPERTY @A0 BINDING ?q0 @A0 BINDING ?q1 @A1','The @A0 is @A1.'),
 ('state-answer-numeric','RESPONSE answer_bindings QUERY_KIND state_query PROPERTY @A0 BINDING ?q0 @A0 BINDING ?q1 @N0','The @A0 is @N0.'),
 ('type-answer','RESPONSE answer_bindings QUERY_KIND type_query BINDING ?q0 @A0','The kind is a @A0.'),
 ('capability-answer','RESPONSE answer_bindings QUERY_KIND capability_inventory_query BINDING ?capability @A0','I can use @A0.'),
]
response=[{'example_ref':f'en:response:{r}','semantic':s,'surface_plan':p,'weight':1.0} for r,s,p in response_examples]
response_grammar=[
 {'ref':'en:response:learning','when':{'action':'request_learning_evidence'},'template':'What does {evidence} refer to here?','required_slots':['evidence'],'semantic_slots':['evidence','learning_plan_ref','query_kind','query_ref']},
 {'ref':'en:response:attributed-claim','when':{'action':'acknowledge_attributed_claim'},'template':'I understand that you think {subject} {copula} {predicate_surface}.','required_slots':['subject','copula','predicate_surface'],'semantic_slots':['subject_ref','predicate_surface','claim_kind']},
 {'ref':'en:response:designation','when':{'action':'answer_bindings','query_kind':'designation_property','has_bindings':True},'template':'{subject_possessive} {property} is {value}.','required_slots':['subject_possessive','property','value'],'semantic_slots':['binding_values','property_ref','query_kind','query_ref','subject_ref']},
 {'ref':'en:response:operational-degraded','when':{'action':'report_operational_condition','qualifiers':{'assessment_status':'degraded'}},'template':'I am operating, but some runtime resources are degraded.','required_slots':[],'semantic_slots':['assessment_status','query_kind','query_ref','snapshot_ref','target_ref']},
 {'ref':'en:response:operational-normal','when':{'action':'report_operational_condition','qualifiers':{'assessment_status':'operating_normally'}},'template':'I am operating normally and able to respond.','required_slots':[],'semantic_slots':['assessment_status','query_kind','query_ref','snapshot_ref','target_ref']},
 {'ref':'en:response:operational-unavailable','when':{'action':'report_operational_condition','qualifiers':{'assessment_status':'unavailable'}},'template':'I have runtime blockers that limit what I can do right now.','required_slots':[],'semantic_slots':['assessment_status','query_kind','query_ref','snapshot_ref','target_ref']},
 {'ref':'en:response:operational-unknown','when':{'action':'report_operational_condition','qualifiers':{'assessment_status':'unknown'}},'template':'I cannot verify my full runtime condition right now.','required_slots':[],'semantic_slots':['assessment_status','query_kind','query_ref','snapshot_ref','target_ref']},
 {'ref':'en:response:relation-unknown','when':{'action':'report_target_uncertainty','query_kind':'relation_query'},'template':'I do not have evidence that {subject} {relation} {object_surface}.','required_slots':['subject','relation','object_surface'],'semantic_slots':['object_surface','query_kind','query_ref','relation_ref','subject_ref']},
 {'ref':'en:response:surface-choice','when':{'action':'explain_surface_choice'},'template':'{surface_choice_b} would have been more natural than {surface_choice_a} because I was referring to myself.','required_slots':['surface_choice_a','surface_choice_b'],'semantic_slots':['surface_decision_ref','surface_choice_a','surface_choice_b','prior_response_ref','prior_surface']},
 {'ref':'en:response:type','when':{'action':'answer_bindings','query_kind':'type_query','has_bindings':True},'template':'{subject} {copula} a {value}.','required_slots':['subject','copula','value'],'semantic_slots':['binding_values','query_kind','query_ref','subject_ref']},
]
realization=[
 {'example_ref':'en:realize:type','semantic':'FACT support op:type role:class @A0 role:instance @A1','surface_plan':'@A1 is a @A0.','weight':1.0},
 {'example_ref':'en:realize:state','semantic':'FACT support op:state role:dimension @A0 role:subject @A1 role:value @A2','surface_plan':'The @A0 of @A1 is @A2.','weight':1.0},
 {'example_ref':'en:realize:relation','semantic':'FACT support op:relation role:object @A0 role:relation @A1 role:subject @A2','surface_plan':'@A2 is a @A1 of @A0.','weight':1.0},
 {'example_ref':'en:realize:event','semantic':'FACT support op:event role:actor @A0 role:event @A1 role:time @A2 role:type @A3','surface_plan':'@A0 @A3 @A2.','weight':1.0},
 {'example_ref':'en:realize:designation','semantic':'FACT support op:designation role:label_type @A0 role:language @E0 role:preferred @E1 role:prior @N0 role:script @E2 role:surface @E3 role:target @A1','surface_plan':'@E3 is a @A0 for @A1.','weight':1.0},
]
grammar=set()
import re
for item in response+realization:
 for token in re.findall(r"@[A-Z]\d+|[\wÀ-ÿ'’-]+|[^\w\s]",item['surface_plan'],re.UNICODE):
  if not token.startswith(('@A','@E','@N')): grammar.add(token.casefold())
grammar.update(FORM['function_forms'])
grammar.update(['.',',','?','!','context','refers','value','percent','recorded','claim','evidence','conflicts','operation','complete','cannot','perform','action','hello','clarify'])

data={
 'version':7,'language':'en','form_pack':'../form_packs/en.json','form_pack_hash':FORM['pack_hash'],
 'forces':['acknowledgment','claim','correction','description_request','directive','query','retraction'],
 'source_classes':['NONE','FRAME_SPEAKER','FRAME_ADDRESSEE']+[f'A{i}' for i in range(8)]+[f'Q{i}' for i in range(3)]+['NEW_ENTITY_0','NEW_ENTITY_1','NEW_EVENT_0','NEW_EVENT_1']+[f'DIM_OF_A{i}' for i in range(8)]+['CONST0'],
 'constant_sources':{'CONST0':'rel:subtype_of'},
 'rule_sources':['NONE']+[f'A{i}' for i in range(8)]+['V0','V1','V2','E0','E1'],
 'operators':['op:designation','op:event','op:relation','op:state','op:type'],
 'roles':['role:actor','role:class','role:context','role:dimension','role:event','role:instance','role:label_type','role:language','role:object','role:preferred','role:prior','role:relation','role:script','role:subject','role:surface','role:target','role:time','role:type','role:value'],
 'structured_examples':structured,'rule_examples':[],'realization_examples':realization,'response_examples':response,
 'response_grammar':response_grammar,
 'semantic_operational_contract':{
  'contract':'CEMM_RUNTIME_IMPLEMENTATION_CONTRACT.md',
  'response_fallback':'same_response_csir_only',
  'perspective':'output_participant_frame',
  'form_schema_algebra':'atomic-feature-v7',
  'operational_status':'cycle_local_structured_assessment',
  'authority_atom_additions':0,
 },
 'grammar_tokens':sorted(grammar),'function_forms':FORM['function_forms'],
}
data['pack_hash']=h(data)
out=ROOT/'cemm/language_packs/en.json'; out.parent.mkdir(parents=True,exist_ok=True); out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'path':str(out),'hash':data['pack_hash'],'structured':len(structured),'responses':len(response),'grammar':len(grammar)},indent=2))
