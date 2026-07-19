"""Predicate-independent Phase-17 realization compiler."""
from __future__ import annotations
from collections import defaultdict,deque
from dataclasses import dataclass
from typing import Protocol

from ..learning.model import PinnedRecord
from ..response.model import ResponseUOLRecord
from ..schema.model import PortFillerClass,UseOperation,semantic_fingerprint
from ..storage.codec import record_fingerprints
from ..storage.model import RecordKind
from ..uol.model import CoordinationGroup,FillerRef,SemanticApplication
from .authority import LanguageUseAuthority
from ..language.model import ConstructionKind,ConstructionRecord
from .model import (ArgumentFrameRecord,DeepClausePlanRecord,LinearizationRuleRecord,MorphologyOperation,MorphologyRuleRecord,RealizationRequestRecord,ReferencePlanRecord,RoundTripDecision,SemanticRoundTripRecord,SurfaceCandidateRecord)

def _pin(s): return PinnedRecord(s.record_kind,s.record_ref,s.revision,s.record_fingerprint)

class RealizationFrontier(Exception):
 def __init__(self,missing_contract:str,refs:tuple[str,...]=()): self.missing_contract=missing_contract;self.refs=refs;super().__init__(missing_contract)

class ClausePlanner:
 def __init__(self,store):self.store=store
 def plan(self,request_pin:PinnedRecord,response:ResponseUOLRecord,frames:tuple[tuple[PinnedRecord,ArgumentFrameRecord],...]):
  result=[];planned=set();visiting=set()
  def visit(app_ref):
   if app_ref in planned:return
   if app_ref in visiting:raise RealizationFrontier('cyclic_nested_semantic_application',(app_ref,))
   app=response.graph.applications.get(app_ref)
   if app is None:raise RealizationFrontier('missing_nested_semantic_application',(app_ref,))
   visiting.add(app_ref)
   schema=self.store.get_record(RecordKind.SCHEMA,app.schema_ref,app.schema_revision)
   if schema is None:raise RealizationFrontier('missing_predicate_schema',(app.schema_ref,))
   ports={b.port_ref for b in app.bindings}
   candidates=[]
   for pin,frame in frames:
    if not frame.executable:continue
    if frame.predicate_schema_classes and schema.payload.schema_class.value not in frame.predicate_schema_classes:continue
    if not set(frame.required_port_refs).issubset(ports):continue
    if not ports.issubset(set(frame.required_port_refs)|set(frame.optional_port_refs)):continue
    candidates.append((pin,frame))
   if not candidates:raise RealizationFrontier('missing_argument_frame',(app.schema_ref,))
   candidates.sort(key=lambda x:(-len(x[1].required_port_refs),x[1].frame_ref,x[1].revision))
   if len(candidates)>1 and len(candidates[0][1].required_port_refs)==len(candidates[1][1].required_port_refs):raise RealizationFrontier('ambiguous_argument_frame',(app.schema_ref,))
   pin,frame=candidates[0]
   args=[];coord_refs=[]
   for binding in sorted(app.bindings,key=lambda b:b.port_ref):
    fillers=[]
    for filler in binding.fillers:
     if not isinstance(filler,FillerRef):raise RealizationFrontier('quoted_literal_requires_explicit_realization_contract',(app_ref,binding.port_ref))
     fillers.append((filler.filler_class.value,filler.ref))
     if filler.filler_class==PortFillerClass.SEMANTIC_APPLICATION:visit(filler.ref)
     elif filler.filler_class==PortFillerClass.COORDINATION_GROUP:
      group=response.graph.coordination_groups.get(filler.ref)
      if group is None:raise RealizationFrontier('missing_coordination_group',(filler.ref,))
      coord_refs.append(group.group_ref)
      for member in group.members:
       if member.filler_class==PortFillerClass.SEMANTIC_APPLICATION:visit(member.ref)
      group_scopes=tuple(sorted((rel for rel in response.graph.scope_relations if rel.scoped_ref.ref==group.group_ref),key=lambda rel:(rel.order,rel.scope_relation_ref)))
      if len({rel.order for rel in group_scopes})!=len(group_scopes):raise RealizationFrontier('ambiguous_scope_order',tuple(rel.scope_relation_ref for rel in group_scopes))
      for rel in group_scopes:visit(rel.operator_application_ref)
    args.append((binding.port_ref,tuple(fillers)))
   scoped_relations=tuple(sorted((rel for rel in response.graph.scope_relations if rel.scoped_ref.ref==app_ref),key=lambda rel:(rel.order,rel.scope_relation_ref)))
   if len({rel.order for rel in scoped_relations})!=len(scoped_relations):raise RealizationFrontier('ambiguous_scope_order',tuple(rel.scope_relation_ref for rel in scoped_relations))
   for rel in scoped_relations:visit(rel.operator_application_ref)
   scope_refs=tuple(rel.scope_relation_ref for rel in scoped_relations)
   features=tuple(sorted(set(frame.feature_constraints)|{('polarity',app.polarity.value)}))
   result.append(DeepClausePlanRecord(clause_ref='clause:'+semantic_fingerprint('deep-clause',(request_pin.key,app.application_ref,pin.key,tuple(args),features,scope_refs,tuple(sorted(set(coord_refs)))),24),request_pin=request_pin,response_application_ref=app.application_ref,predicate_schema_ref=app.schema_ref,predicate_schema_revision=app.schema_revision,argument_refs=tuple(args),discourse_act_ref=None,feature_values=features,scope_refs=scope_refs,coordination_refs=tuple(sorted(set(coord_refs))),information_structure=(),frame_pin=pin))
   visiting.remove(app_ref);planned.add(app_ref)
  for root in response.graph.root_refs:
   if root.filler_class==PortFillerClass.SEMANTIC_APPLICATION:visit(root.ref)
   elif root.filler_class==PortFillerClass.COORDINATION_GROUP:
    group=response.graph.coordination_groups.get(root.ref)
    if group is None:raise RealizationFrontier('missing_coordination_group',(root.ref,))
    for member in group.members:
     if member.filler_class==PortFillerClass.SEMANTIC_APPLICATION:visit(member.ref)
     else:raise RealizationFrontier('unsupported_coordination_root_member',(member.filler_class.value,member.ref))
    root_scopes=tuple(sorted((rel for rel in response.graph.scope_relations if rel.scoped_ref.ref==group.group_ref),key=lambda rel:(rel.order,rel.scope_relation_ref)))
    if len({rel.order for rel in root_scopes})!=len(root_scopes):raise RealizationFrontier('ambiguous_scope_order',tuple(rel.scope_relation_ref for rel in root_scopes))
    for rel in root_scopes:visit(rel.operator_application_ref)
   else:raise RealizationFrontier('unsupported_response_root',(root.filler_class.value,root.ref))
  if not result and response.graph.root_refs:raise RealizationFrontier('unsupported_response_root',tuple(r.ref for r in response.graph.root_refs))
  return tuple(result)

class FeatureUnifier:
 def unify(self,*structures):
  merged={}
  for structure in structures:
   for key,value in structure:
    if key in merged and merged[key]!=value:raise RealizationFrontier('feature_conflict',(key,merged[key],value))
    merged[key]=value
  return tuple(sorted(merged.items()))

class LexicalSelector:
 def __init__(self,store):self.store=store;self.authority=LanguageUseAuthority(store)
 def predicate_form(self,language_tag,schema_ref,schema_revision,allowed_pack_pins,register_refs=(),script=None,permission_ref='conversation'):
  allowed={(p.record_ref,p.revision) for p in allowed_pack_pins if p.record_kind==RecordKind.LANGUAGE_PACK}
  senses=[s for s in self.authority.records_for_use(RecordKind.LEXICAL_SENSE,UseOperation.REALIZE) if s.payload.target_ref==schema_ref and s.payload.target_revision==schema_revision and (s.payload.pack_ref,s.payload.pack_revision) in allowed and s.permission_ref in {None,'public',permission_ref}]
  candidates=[]
  for ss in senses:
   pack=self.store.get_record(RecordKind.LANGUAGE_PACK,ss.payload.pack_ref,ss.payload.pack_revision)
   if pack is None or (pack.record_ref,pack.revision) not in allowed or pack.payload.language_tag!=language_tag or pack.permission_ref not in {None,'public',permission_ref} or not self.authority.authorized(pack,UseOperation.REALIZE):continue
   for link in self.authority.records_for_use(RecordKind.FORM_SENSE_LINK,UseOperation.REALIZE):
    if link.payload.sense_ref!=ss.record_ref or link.payload.sense_revision!=ss.revision or link.permission_ref not in {None,'public',permission_ref}:continue
    if register_refs and link.payload.register_refs and not set(register_refs).intersection(link.payload.register_refs):continue
    form=self.store.get_record(RecordKind.LANGUAGE_FORM,link.payload.form_ref,link.payload.form_revision)
    if form is not None and form.permission_ref not in {None,'public',permission_ref}:continue
    if form is not None and script and form.payload.script and form.payload.script!=script:continue
    if form is not None and self.authority.authorized(form,UseOperation.REALIZE):candidates.append((ss,link,form))
  candidates.sort(key=lambda x:(-int(bool(set(register_refs).intersection(x[1].payload.register_refs))),-getattr(x[1].payload,'prior_weight',1.0),x[2].record_ref,x[2].revision))
  if not candidates:raise RealizationFrontier('missing_realize_lexicalization',(schema_ref,str(schema_revision),language_tag))
  return candidates[0]

class MorphologyExecutor:
 def apply(self,base:str,features:tuple[tuple[str,str],...],rules:tuple[tuple[PinnedRecord,MorphologyRuleRecord],...],lexical_category:str):
  matches=[];f=dict(features)
  for pin,rule in rules:
   if not rule.executable or rule.lexical_category!=lexical_category:continue
   if all(f.get(k)==v for k,v in rule.required_features):matches.append((rule.priority,pin,rule))
  matches.sort(key=lambda x:(-x[0],x[1].key))
  if not matches:return base,()
  if len(matches)>1 and matches[0][0]==matches[1][0]:raise RealizationFrontier('ambiguous_morphology',(matches[0][1].record_ref,matches[1][1].record_ref))
  _,pin,rule=matches[0]
  if rule.operation==MorphologyOperation.IDENTITY:out=base
  elif rule.operation==MorphologyOperation.PREFIX:out=rule.operand+base
  elif rule.operation==MorphologyOperation.SUFFIX:out=base+rule.operand
  elif rule.operation==MorphologyOperation.REPLACE_FORM:out=rule.operand
  elif rule.operation==MorphologyOperation.ZERO:out=''
  else:raise RealizationFrontier('unsupported_morphology_operation',(rule.rule_ref,))
  return out,(pin,)

class Linearizer:
 def order(self,slot_tokens:dict[str,list[str]],rule:LinearizationRuleRecord):
  nodes=set(slot_tokens);edges=defaultdict(set);ind={n:0 for n in nodes}
  for left,right in rule.precedence_pairs:
   if left in nodes and right in nodes and right not in edges[left]:edges[left].add(right);ind[right]+=1
  q=deque(sorted(n for n,d in ind.items() if d==0));order=[]
  while q:
   if len(q)>1 and not bool(rule.metadata.get('free_order',False)):
    raise RealizationFrontier('underconstrained_linearization',tuple(q))
   n=q.popleft();order.append(n)
   for m in sorted(edges[n]):
    ind[m]-=1
    if ind[m]==0:q.append(m)
   q=deque(sorted(q))
  if len(order)!=len(nodes):raise RealizationFrontier('cyclic_linearization',(rule.rule_ref,))
  tokens=list(rule.prefix_tokens)
  for slot in order:tokens.extend(slot_tokens[slot])
  tokens.extend(rule.suffix_tokens)
  return tuple(t for t in tokens if t),rule.separator.join(t for t in tokens if t)

class ReferenceResolver(Protocol):
 def realize(self,referent_ref:str,request:RealizationRequestRecord,request_pin:PinnedRecord)->tuple[str,ReferencePlanRecord]:...

class PrivacyAwareReferenceResolver:
 """Resolve references only through explicit REALIZE-authorized language records.

 The resolver never exposes raw identity-facet values or transcript text. A language
 package must provide a reviewed LanguageForm whose metadata explicitly binds the
 stable referent (`referent_ref`). Ambiguity remains a frontier.
 """
 def __init__(self,store): self.store=store; self.authority=LanguageUseAuthority(store)
 def realize(self,referent_ref:str,request:RealizationRequestRecord,request_pin:PinnedRecord):
  referent=self._semantic_referent(referent_ref)
  if referent is None:raise RealizationFrontier('missing_reference_referent',(referent_ref,))
  permission=referent.permission_ref or getattr(getattr(referent.payload,'referent',referent.payload),'permission_ref','conversation')
  if permission not in {'public',request.permission_ref}:raise RealizationFrontier('reference_permission_blocked',(referent_ref,))
  allowed={(p.record_ref,p.revision) for p in request.language_pack_pins if p.record_kind==RecordKind.LANGUAGE_PACK}
  forms=[]
  for form in self.authority.records_for_use(RecordKind.LANGUAGE_FORM,UseOperation.REALIZE):
   if str(form.payload.metadata.get('referent_ref',''))!=referent_ref:continue
   if form.permission_ref not in {None,'public',request.permission_ref}:continue
   pack=self.store.get_record(RecordKind.LANGUAGE_PACK,form.payload.pack_ref,form.payload.pack_revision)
   if pack is None or (pack.record_ref,pack.revision) not in allowed or pack.payload.language_tag!=request.language_tag or not self.authority.authorized(pack,UseOperation.REALIZE):continue
   if request.script and form.payload.script and form.payload.script!=request.script:continue
   priority=int(form.payload.metadata.get('reference_priority',0))
   forms.append((priority,form))
  forms.sort(key=lambda x:(-x[0],x[1].record_ref,x[1].revision))
  if not forms:raise RealizationFrontier('missing_reference_realization',(referent_ref,request.language_tag))
  if len(forms)>1 and forms[0][0]==forms[1][0]:raise RealizationFrontier('ambiguous_reference_realization',(referent_ref,request.language_tag))
  _,form=forms[0]
  competitors=[]
  for other_form in self.authority.records_for_use(RecordKind.LANGUAGE_FORM,UseOperation.REALIZE):
   if other_form.record_ref==form.record_ref or other_form.payload.written_form!=form.payload.written_form:continue
   other_ref=str(other_form.payload.metadata.get('referent_ref',''))
   if not other_ref or other_ref==referent_ref:continue
   other_pack=self.store.get_record(RecordKind.LANGUAGE_PACK,other_form.payload.pack_ref,other_form.payload.pack_revision)
   if other_pack is None or (other_pack.record_ref,other_pack.revision) not in allowed or other_pack.payload.language_tag!=request.language_tag:continue
   other=self._semantic_referent(other_ref)
   if other is not None and (other.permission_ref or getattr(getattr(other.payload,'referent',other.payload),'permission_ref','conversation')) in {'public',request.permission_ref}:competitors.append(_pin(other))
  if competitors:raise RealizationFrontier('ambiguous_reference_surface',(referent_ref,form.payload.written_form))
  plan=ReferencePlanRecord(
   reference_ref='reference-plan:'+semantic_fingerprint('reference-plan',(request_pin.key,_pin(referent).key,_pin(form).key,tuple(p.key for p in competitors)),24),
   request_pin=request_pin,referent_pin=_pin(referent),competitor_pins=tuple(sorted(competitors,key=lambda p:p.key)),
   allowed_identity_facet_pins=(),strategy_ref='explicit-language-form-reference',language_rule_pin=_pin(form),feature_values=())
  return form.payload.written_form,plan
 def _semantic_referent(self,ref):
  matches=[]
  for kind in (RecordKind.REFERENT,RecordKind.PROPOSITION,RecordKind.CLAIM_OCCURRENCE,RecordKind.EVENT_OCCURRENCE):
   stored=self.store.get_record(kind,ref)
   if stored is not None:matches.append(stored)
  if not matches:return None
  if len(matches)>1:
   # A specialized referent may coexist with an identical base referent only if
   # the embedded/base referent is structurally identical. Prefer the specialized
   # durable record so its exact revision is preserved in reference lineage.
   specialized=[m for m in matches if m.record_kind!=RecordKind.REFERENT]
   if len(specialized)==1:return specialized[0]
   raise RealizationFrontier('ambiguous_durable_referent_identity',(ref,))
  return matches[0]

class RealizationCompiler:
 def __init__(self,store,reference_resolver:ReferenceResolver):
  self.store=store;self.reference_resolver=reference_resolver;self.authority=LanguageUseAuthority(store);self.lexical=LexicalSelector(store);self.morphology=MorphologyExecutor();self.linearizer=Linearizer();self.clauses=ClausePlanner(store)
 def compile(self,request:RealizationRequestRecord,*,frames:tuple[tuple[PinnedRecord,ArgumentFrameRecord],...],morphology_rules:tuple[tuple[PinnedRecord,MorphologyRuleRecord],...],linearization_rules:tuple[tuple[PinnedRecord,LinearizationRuleRecord],...]):
  with self.store.snapshot() as source_snapshot:
   pass
  response_stored=self._exact(request.response_uol_pin,RecordKind.RESPONSE_UOL);response=response_stored.payload
  response_current=self.store.get_record(RecordKind.RESPONSE_UOL,request.response_uol_pin.record_ref)
  if response_current is None or response_current.revision!=request.response_uol_pin.revision or response_current.record_fingerprint!=request.response_uol_pin.record_fingerprint:raise RealizationFrontier('stale_response_uol',(request.response_uol_pin.record_ref,))
  if response.permission_ref not in {'public',request.permission_ref}:raise RealizationFrontier('realization_permission_broadening',(response.permission_ref,request.permission_ref))
  if not set(request.audience_refs).issubset(set(response.audience_refs)):raise RealizationFrontier('realization_audience_broadening',tuple(sorted(set(request.audience_refs)-set(response.audience_refs))))
  if request.sensitivity!=response.sensitivity:raise RealizationFrontier('realization_sensitivity_scope_mismatch',(response.sensitivity,request.sensitivity))
  allowed_packs={(p.record_ref,p.revision) for p in request.language_pack_pins if p.record_kind==RecordKind.LANGUAGE_PACK}
  if len(allowed_packs)!=len(request.language_pack_pins):raise RealizationFrontier('invalid_language_pack_pin_kind',())
  for p in request.language_pack_pins:
   stored=self._exact(p,RecordKind.LANGUAGE_PACK)
   if stored.permission_ref not in {None,'public',request.permission_ref}:raise RealizationFrontier('language_pack_permission_blocked',(p.record_ref,str(p.revision)))
   if not self.authority.authorized(stored,UseOperation.REALIZE):raise RealizationFrontier('language_pack_not_realize_authorized',(p.record_ref,str(p.revision)))
   if stored.payload.language_tag!=request.language_tag:raise RealizationFrontier('language_pack_tag_mismatch',(p.record_ref,request.language_tag))
   if request.script and stored.payload.scripts and request.script not in stored.payload.scripts:raise RealizationFrontier('language_pack_script_mismatch',(p.record_ref,request.script))
  authorized_frames=[]
  for p,f in frames:
   stored=self._exact(p,RecordKind.ARGUMENT_FRAME)
   if stored.payload!=f or (f.pack_ref,f.pack_revision) not in allowed_packs or stored.permission_ref not in {None,'public',request.permission_ref} or not self.authority.authorized(stored,UseOperation.REALIZE):continue
   authorized_frames.append((p,f))
  authorized_morph=[]
  for p,r in morphology_rules:
   stored=self._exact(p,RecordKind.MORPHOLOGY_RULE)
   if stored.payload==r and (r.pack_ref,r.pack_revision) in allowed_packs and stored.permission_ref in {None,'public',request.permission_ref} and self.authority.authorized(stored,UseOperation.REALIZE):authorized_morph.append((p,r))
  authorized_linear=[]
  for p,r in linearization_rules:
   stored=self._exact(p,RecordKind.LINEARIZATION_RULE)
   if stored.payload==r and (r.pack_ref,r.pack_revision) in allowed_packs and stored.permission_ref in {None,'public',request.permission_ref} and self.authority.authorized(stored,UseOperation.REALIZE):authorized_linear.append((p,r))
  request_pin=PinnedRecord(RecordKind.REALIZATION_REQUEST,request.request_ref,1,record_fingerprints(RecordKind.REALIZATION_REQUEST,request)[1])
  clauses=self.clauses.plan(request_pin,response,tuple(authorized_frames));clause_by_app={c.response_application_ref:c for c in clauses}
  all_tokens=[];clause_surfaces=[];lex_pins=[];morph_pins=[];ref_pins=[];reference_plans=[];lin_pins=[];frame_pins=[];rendered={};rendering=set()
  def realize_filler(filler_class,ref):
   cls=PortFillerClass(filler_class)
   if cls==PortFillerClass.REFERENT:
    surface,reference_plan=self.reference_resolver.realize(ref,request,request_pin);reference_plans.append(reference_plan);ref_pins.append(PinnedRecord(RecordKind.REFERENCE_PLAN,reference_plan.reference_ref,1,record_fingerprints(RecordKind.REFERENCE_PLAN,reference_plan)[1]));return surface
   if cls==PortFillerClass.SEMANTIC_APPLICATION:return realize_clause(ref)
   if cls==PortFillerClass.COORDINATION_GROUP:return realize_coordination(ref)
   if cls==PortFillerClass.SEMANTIC_VARIABLE:raise RealizationFrontier('semantic_variable_requires_reviewed_question_realization',(ref,))
   raise RealizationFrontier('unsupported_filler_class',(filler_class,ref))
  def apply_scope(target_ref,surface):
   relations=tuple(sorted((rel for rel in response.graph.scope_relations if rel.scoped_ref.ref==target_ref),key=lambda rel:(rel.order,rel.scope_relation_ref)))
   if len({rel.order for rel in relations})!=len(relations):raise RealizationFrontier('ambiguous_scope_order',tuple(rel.scope_relation_ref for rel in relations))
   for relation in relations:
    operator_surface=realize_clause(relation.operator_application_ref)
    constructions=[]
    for cs in self.authority.records_for_use(RecordKind.CONSTRUCTION,UseOperation.REALIZE):
     c=cs.payload;meta=c.metadata
     if (c.pack_ref,c.pack_revision) not in allowed_packs or cs.permission_ref not in {None,'public',request.permission_ref}:continue
     if meta.get('realization_role','')!='scope' or str(meta.get('scope_kind',''))!=relation.scope_kind.value:continue
     mode=str(meta.get('scope_realization',''))
     if mode not in {'operator_before','operator_after'}:continue
     constructions.append(cs)
    constructions.sort(key=lambda x:(-int(x.payload.metadata.get('priority',0)),x.record_ref,x.revision))
    if not constructions:raise RealizationFrontier('missing_scope_construction',(relation.scope_kind.value,request.language_tag))
    if len(constructions)>1 and int(constructions[0].payload.metadata.get('priority',0))==int(constructions[1].payload.metadata.get('priority',0)):raise RealizationFrontier('ambiguous_scope_construction',(relation.scope_kind.value,))
    construction=constructions[0];mode=str(construction.payload.metadata.get('scope_realization'));separator=str(construction.payload.metadata.get('separator',' '))
    surface=(operator_surface+separator+surface) if mode=='operator_before' else (surface+separator+operator_surface)
    lin_pins.append(_pin(construction))
   return surface
  def realize_coordination(group_ref):
   group=response.graph.coordination_groups.get(group_ref)
   if group is None:raise RealizationFrontier('missing_coordination_group',(group_ref,))
   members=[realize_filler(m.filler_class.value,m.ref) for m in group.members]
   constructions=[]
   for cs in self.authority.records_for_use(RecordKind.CONSTRUCTION,UseOperation.REALIZE):
    c=cs.payload
    if not isinstance(c,ConstructionRecord) or c.construction_kind!=ConstructionKind.COORDINATION:continue
    if (c.pack_ref,c.pack_revision) not in allowed_packs or cs.permission_ref not in {None,'public',request.permission_ref}:continue
    if str(c.metadata.get('coordination_kind',''))!=group.coordination_kind.value:continue
    constructions.append(cs)
   constructions.sort(key=lambda x:(-int(x.payload.metadata.get('priority',0)),x.record_ref,x.revision))
   if not constructions:raise RealizationFrontier('missing_coordination_construction',(group.coordination_kind.value,request.language_tag))
   if len(constructions)>1 and int(constructions[0].payload.metadata.get('priority',0))==int(constructions[1].payload.metadata.get('priority',0)):raise RealizationFrontier('ambiguous_coordination_construction',(group.coordination_kind.value,))
   construction=constructions[0];meta=construction.payload.metadata
   form_ref=str(meta.get('connector_form_ref',''));form_revision=int(meta.get('connector_form_revision',0) or 0)
   if not form_ref or form_revision<1:raise RealizationFrontier('coordination_connector_not_pinned',(construction.record_ref,))
   form=self.store.get_record(RecordKind.LANGUAGE_FORM,form_ref,form_revision)
   if form is None or (form.payload.pack_ref,form.payload.pack_revision) not in allowed_packs or form.permission_ref not in {None,'public',request.permission_ref} or not self.authority.authorized(form,UseOperation.REALIZE):raise RealizationFrontier('coordination_connector_not_authorized',(form_ref,str(form_revision)))
   member_sep=str(meta.get('member_separator',', '));pre=str(meta.get('pre_connector_separator',' '));post=str(meta.get('post_connector_separator',' '));connector=form.payload.written_form
   if len(members)==2:surface=members[0]+pre+connector+post+members[1]
   else:surface=member_sep.join(members[:-1])+pre+connector+post+members[-1]
   lin_pins.extend((_pin(construction),_pin(form)));return apply_scope(group_ref,surface)
  def realize_clause(app_ref):
   if app_ref in rendered:return rendered[app_ref]
   if app_ref in rendering:raise RealizationFrontier('cyclic_clause_realization',(app_ref,))
   clause=clause_by_app.get(app_ref)
   if clause is None:raise RealizationFrontier('missing_deep_clause_plan',(app_ref,))
   rendering.add(app_ref);app=response.graph.applications[clause.response_application_ref]
   sense,link,form=self.lexical.predicate_form(request.language_tag,app.schema_ref,app.schema_revision,request.language_pack_pins,request.register_refs,request.script,request.permission_ref)
   pred,mps=self.morphology.apply(form.payload.written_form,clause.feature_values,tuple(authorized_morph),getattr(sense.payload,'lexical_category',''))
   lex_pins.extend((_pin(sense),_pin(link),_pin(form)));morph_pins.extend(mps);frame_pins.append(clause.frame_pin)
   frame=next(f for p,f in authorized_frames if p==clause.frame_pin);mapping=dict(frame.port_to_slot);slots=defaultdict(list)
   predicate_slot=str(frame.metadata.get('predicate_slot','predicate'));slots[predicate_slot].append(pred)
   for port,fillers in clause.argument_refs:
    slot=mapping.get(port)
    if slot is None:continue
    for filler_class,ref in fillers:slots[slot].append(realize_filler(filler_class,ref))
   lin_candidates=[(p,r) for p,r in authorized_linear if r.construction_ref==str(frame.metadata.get('construction_ref',frame.frame_ref))]
   if len(lin_candidates)!=1:raise RealizationFrontier('missing_or_ambiguous_linearization',(frame.frame_ref,))
   lp,lr=lin_candidates[0];tokens,surface=self.linearizer.order(dict(slots),lr);lin_pins.append(lp)
   surface=apply_scope(app_ref,surface)
   rendering.remove(app_ref);rendered[app_ref]=surface;return surface
  for root in response.graph.root_refs:
   surface=realize_filler(root.filler_class.value,root.ref);clause_surfaces.append(surface);all_tokens.extend(surface.split())
  if not all_tokens:raise RealizationFrontier('empty_surface_not_authorized',())
  with self.store.snapshot() as final_snapshot:
   if final_snapshot.fingerprint!=source_snapshot.fingerprint:raise RealizationFrontier('store_changed_during_realization_compile',(str(source_snapshot.store_revision),str(final_snapshot.store_revision)))
  candidate=SurfaceCandidateRecord(candidate_ref='surface:'+semantic_fingerprint('surface-candidate',(request.request_ref,tuple(all_tokens),tuple(p.key for p in lex_pins),tuple(p.key for p in lin_pins),source_snapshot.fingerprint),24),request_pin=request_pin,clause_pins=tuple(PinnedRecord(RecordKind.DEEP_CLAUSE_PLAN,c.clause_ref,1,record_fingerprints(RecordKind.DEEP_CLAUSE_PLAN,c)[1]) for c in clauses),frame_pins=tuple(dict.fromkeys(frame_pins)),lexical_pins=tuple(dict.fromkeys(lex_pins)),morphology_pins=tuple(dict.fromkeys(morph_pins)),reference_pins=tuple(dict.fromkeys(ref_pins)),linearization_pins=tuple(dict.fromkeys(lin_pins)),tokens=tuple(all_tokens),surface=' '.join(clause_surfaces),generation_score=1.0,permission_ref=request.permission_ref,snapshot_revision=source_snapshot.store_revision,snapshot_fingerprint=source_snapshot.fingerprint)
  return clauses,tuple(reference_plans),candidate
 def _exact(self,p,kind=None):
  if kind is not None and p.record_kind!=kind:raise ValueError(f'expected {kind.value} pin')
  s=self.store.get_record(p.record_kind,p.record_ref,p.revision)
  if s is None or s.record_fingerprint!=p.record_fingerprint:raise ValueError(f'stale realization pin: {p.key}')
  return s

class SemanticAnalyzer(Protocol):
 analyzer_ref:str;analyzer_revision:str
 def recover_graph_fingerprint(self,surface:str,language_tag:str)->tuple[str,tuple[str,...],tuple[str,...],tuple[str,...],tuple[str,...]]:...

class RoundTripVerifier:
 def verify(self,request_pin:PinnedRecord,candidate_pin:PinnedRecord,expected_graph_fingerprint:str,surface:str,language_tag:str,analyzer:SemanticAnalyzer):
  recovered,additions,losses,drift,proofs=analyzer.recover_graph_fingerprint(surface,language_tag)
  decision=RoundTripDecision.PASS if recovered==expected_graph_fingerprint and not additions and not losses and not drift else RoundTripDecision.FAIL
  return SemanticRoundTripRecord(roundtrip_ref='roundtrip:'+semantic_fingerprint('semantic-roundtrip',(candidate_pin.key,analyzer.analyzer_ref,analyzer.analyzer_revision,recovered,expected_graph_fingerprint),24),request_pin=request_pin,surface_candidate_pin=candidate_pin,analyzer_ref=analyzer.analyzer_ref,analyzer_revision=analyzer.analyzer_revision,recovered_graph_fingerprint=recovered,expected_graph_fingerprint=expected_graph_fingerprint,decision=decision,additions=tuple(additions),losses=tuple(losses),drift_refs=tuple(drift),proof_refs=tuple(proofs))
