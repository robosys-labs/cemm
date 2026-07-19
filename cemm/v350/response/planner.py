"""Generic proof-carrying Response UOL planner for Phase 16."""
from __future__ import annotations
from collections import defaultdict

from ..goals.model import GoalCandidateRecord,GoalDecisionRecord
from ..learning.model import FrontierResolutionStatus,LearningFrontierRecord,PinnedRecord
from ..schema.model import PortFillerClass,UseOperation,schema_authorizes_use,semantic_fingerprint
from ..storage.codec import record_fingerprints
from ..storage.model import RecordKind
from ..uol.model import ApplicationBinding,FillerRef,SemanticApplication,UOLGraph
from .model import (ResponseBindingSelector,ResponseSelectorMode,ResponseTransformationProof,ResponseTransformRuleRecord,ResponseUOLRecord)


def _pin(stored): return PinnedRecord(stored.record_kind,stored.record_ref,stored.revision,stored.record_fingerprint)


class ResponseTransformRegistry:
    def __init__(self,rules):
        by_ref={}
        for rule in rules:
            if rule.executable:by_ref.setdefault(rule.rule_ref,[]).append(rule)
        effective=[]
        for ref in sorted(by_ref):
            revisions=by_ref[ref]
            superseded={r.supersedes_revision for r in revisions if r.supersedes_revision is not None}
            effective.extend(r for r in revisions if r.revision not in superseded)
        self.rules=tuple(sorted(effective,key=lambda r:(r.rule_ref,r.revision)))
    def candidates(self,goal:GoalCandidateRecord,source_kind:RecordKind):
        return tuple(sorted((r for r in self.rules if (goal.goal_schema_ref,goal.goal_schema_revision) in r.goal_schema_pins and source_kind in r.source_record_kinds),key=lambda r:(-r.priority,r.rule_ref,r.revision)))


class ResponseMeaningPlanner:
    """Transforms only selected, exact goal/source lineage; unsupported meaning becomes a frontier."""
    def __init__(self,store,rules): self.store=store; self.registry=ResponseTransformRegistry(rules)

    def plan(self,decision_pin:PinnedRecord,*,audience_refs:tuple[str,...],perspective_ref:str):
        with self.store.snapshot() as source_snapshot:
            pass
        decision_stored=self._exact(decision_pin,RecordKind.GOAL_DECISION); decision=decision_stored.payload
        if not isinstance(decision,GoalDecisionRecord): raise ValueError("response planning requires GoalDecisionRecord")
        # latest decision identity must still be exact; later revisions invalidate old response plans
        latest=self.store.get_record(RecordKind.GOAL_DECISION,decision.decision_ref)
        if latest is None or latest.revision!=decision_pin.revision or latest.record_fingerprint!=decision_pin.record_fingerprint: raise ValueError("stale goal decision")
        selected_pins=[]; source_pins=[]; proofs=[]; applications={}; roots=[]; frontiers=[]
        contexts=set(); permissions=set(); sensitivities=set()
        for goal_ref in decision.selected_goal_refs:
            gp=next((p for p in decision.candidate_pins if p.record_ref==goal_ref),None)
            if gp is None: raise ValueError("selected goal missing exact candidate pin")
            gs=self._exact(gp,RecordKind.GOAL_CANDIDATE); goal=gs.payload
            if not isinstance(goal,GoalCandidateRecord) or not goal.authorized: raise ValueError("selected response goal is not authorized")
            if goal.operation==UseOperation.EXECUTE: continue  # execution handled by the operation authority; result may trigger a new Phase-15 decision
            selected_pins.append(gp); permissions.add(goal.permission_ref); sensitivities.add(goal.sensitivity)
            goal_context=str(goal.metadata.get('context_ref',decision.context_ref)); contexts.add(goal_context)
            for sp in goal.source_pins:
                ss=self._exact(sp); source_pins.append(sp)
                rules=self.registry.candidates(goal,sp.record_kind)
                if not rules:
                    frontiers.append(self._frontier("missing_response_transform",gp,sp,(RecordKind.RESPONSE_TRANSFORM_RULE,),goal_context,goal.permission_ref)); continue
                top=rules[0]
                if len(rules)>1 and rules[1].priority==top.priority:
                    frontiers.append(self._frontier("ambiguous_response_transform",gp,sp,(RecordKind.RESPONSE_TRANSFORM_RULE,),goal_context,goal.permission_ref,metadata={"candidate_rules":tuple((r.rule_ref,r.revision) for r in rules[:2])})); continue
                rule_stored=self.store.get_record(RecordKind.RESPONSE_TRANSFORM_RULE,top.rule_ref,top.revision)
                if rule_stored is None or rule_stored.payload != top: raise ValueError("response transform rule must match exact durable authority")
                rule_pin=_pin(rule_stored)
                out_schema_stored=self.store.get_record(RecordKind.SCHEMA,top.output_schema_ref,top.output_schema_revision)
                if out_schema_stored is None or not schema_authorizes_use(out_schema_stored.payload,UseOperation.COMPOSE):
                    raise ValueError("response transform output schema is not exact COMPOSE authority")
                self._check_required_status(top,ss.payload)
                if top.mandatory_qualification_refs:
                    frontiers.append(self._frontier("mandatory_qualification_required",gp,sp,(RecordKind.SCHEMA,),goal_context,goal.permission_ref,metadata={"qualification_refs":top.mandatory_qualification_refs,"rule_ref":top.rule_ref})); continue
                try:
                    bindings,nested_records=self._bindings(top.selectors,ss.payload,goal,goal_context)
                except ValueError as exc:
                    frontiers.append(self._frontier("response_binding_resolution_gap",gp,sp,(RecordKind.REFERENT,RecordKind.SEMANTIC_APPLICATION),goal_context,goal.permission_ref,metadata={"rule_ref":top.rule_ref,"error":str(exc)})); continue
                required={p.port_ref for p in out_schema_stored.payload.local_ports if p.cardinality.minimum>0}
                if not required.issubset({b.port_ref for b in bindings}):
                    frontiers.append(self._frontier("response_required_port_gap",gp,sp,(RecordKind.SCHEMA,),goal_context,goal.permission_ref,metadata={"rule_ref":top.rule_ref,"required_ports":tuple(sorted(required))})); continue
                nested_pins=[]
                for nested in nested_records:
                    nested_pin=_pin(nested); nested_pins.append(nested_pin); source_pins.append(nested_pin)
                    existing=applications.get(nested.record_ref)
                    if existing is not None and existing != nested.payload:
                        raise ValueError("response nested application identity collision")
                    applications[nested.record_ref]=nested.payload
                app_ref="response-app:"+semantic_fingerprint("response-application",(gp.key,sp.key,rule_pin.key,tuple((b.port_ref,tuple(getattr(f,'ref',None) for f in b.fillers)) for b in bindings)),24)
                app=SemanticApplication(application_ref=app_ref,schema_ref=top.output_schema_ref,schema_revision=top.output_schema_revision,bindings=bindings,context_ref=goal_context,use_operation=UseOperation.COMPOSE,
                                        confidence=min(1.0,float(getattr(ss.payload,'confidence',1.0))),evidence_refs=tuple(getattr(ss.payload,'evidence_refs',())))
                applications[app_ref]=app; roots.append(FillerRef(PortFillerClass.SEMANTIC_APPLICATION,app_ref))
                auth_pins=tuple(getattr(goal,'authorization_pins',()))
                input_pins=tuple(sorted({p.key+(p.record_fingerprint,):p for p in (sp,*nested_pins)}.values(),key=lambda p:p.key))
                proof=ResponseTransformationProof(
                    proof_ref="response-proof:"+semantic_fingerprint("response-transform-proof",(gp.key,sp.key,rule_pin.key,app_ref,tuple(p.key+(p.record_fingerprint,) for p in input_pins)),24),
                    goal_candidate_pin=gp,rule_pin=rule_pin,input_pins=input_pins,output_refs=(app_ref,),authorization_pins=auth_pins,reason_refs=(top.rule_ref,))
                proofs.append(proof)
        if len(contexts)>1 or len(permissions)>1 or len(sensitivities)>1: raise ValueError("one Response UOL cannot silently merge contexts, permission scopes, or sensitivity scopes")
        if not selected_pins:
            raise ValueError("no non-operation selected goals remain for response planning")
        with self.store.snapshot() as snapshot:
            if snapshot.fingerprint != source_snapshot.fingerprint:
                raise ValueError("store changed during Response UOL planning; rebuild from one exact snapshot")
            frontier_refs=tuple(sorted(f.frontier_ref for f in frontiers))
            graph=UOLGraph(graph_ref="response-graph:"+semantic_fingerprint("response-graph",(decision_pin.key,tuple(sorted(applications)),frontier_refs),24),applications=applications,root_refs=tuple(roots),unresolved_refs=frontier_refs)
            record=ResponseUOLRecord(
                response_ref="response-uol:"+semantic_fingerprint("response-uol-ref",(source_snapshot.fingerprint,decision_pin.key,tuple(p.key for p in selected_pins),graph.record_fingerprint),24),
                goal_decision_pin=decision_pin,selected_goal_pins=tuple(selected_pins),source_pins=tuple(sorted(set(source_pins),key=lambda p:p.key)),
                transformation_proof_refs=tuple(sorted(p.proof_ref for p in proofs)),omission_refs=(),graph=graph,unresolved_frontier_refs=frontier_refs,
                audience_refs=tuple(sorted(set(audience_refs))),perspective_ref=perspective_ref,context_ref=next(iter(contexts),decision.context_ref),permission_ref=next(iter(permissions),decision.permission_ref),
                sensitivity=max(sensitivities) if sensitivities else 'normal',snapshot_revision=source_snapshot.store_revision,snapshot_fingerprint=source_snapshot.fingerprint)
        return record,tuple(proofs),tuple(frontiers)

    @staticmethod
    def _frontier(missing_contract,goal_pin,source_pin,expected_kinds,context_ref,permission_ref,metadata=None):
        ref="learning-frontier:response:"+semantic_fingerprint("response-planning-frontier",(missing_contract,goal_pin.key,source_pin.key,tuple(k.value for k in expected_kinds),context_ref,permission_ref,metadata or {}),24)
        return LearningFrontierRecord(
            frontier_ref=ref,target_ref=source_pin.record_ref,missing_contract=missing_contract,
            expected_record_kinds=tuple(expected_kinds),expected_schema_classes=(),accepted_anchor_types=(),
            evidence_refs=(),candidate_refs=(),resolution_status=FrontierResolutionStatus.OPEN,
            context_ref=context_ref,permission_ref=permission_ref,
            metadata={"phase":16,"goal_ref":goal_pin.record_ref,"source_kind":source_pin.record_kind.value,"source_revision":source_pin.revision,**dict(metadata or {})},
        )

    def _bindings(self,selectors:tuple[ResponseBindingSelector,...],source,goal,goal_context):
        result=[]; nested={}
        source_app=self._source_application(source,goal)
        for sel in selectors:
            refs=[]
            if sel.mode==ResponseSelectorMode.SOURCE: refs=[self._primary_ref(source)]
            elif sel.mode==ResponseSelectorMode.SOURCE_FIELD:
                val=getattr(source,sel.source_field,None)
                if isinstance(val,str): refs=[val]
                elif isinstance(val,(tuple,list)): refs=[str(x) for x in val if x]
            elif sel.mode==ResponseSelectorMode.APPLICATION_PORT and source_app is not None:
                b=source_app.binding(sel.source_port_ref); refs=[] if b is None else [f.ref for f in b.fillers if isinstance(f,FillerRef)]
            elif sel.mode==ResponseSelectorMode.TARGET and sel.target_index is not None and sel.target_index<len(goal.target_refs): refs=[goal.target_refs[sel.target_index]]
            elif sel.mode==ResponseSelectorMode.FIXED and sel.fixed_ref: refs=[sel.fixed_ref]
            fillers=[]
            for ref in sorted(set(refs)):
                filler_class,stored=self._resolve_filler(ref,goal)
                fillers.append(FillerRef(filler_class,ref))
                if filler_class==PortFillerClass.SEMANTIC_APPLICATION:
                    self._collect_application_closure(stored,goal,goal_context,nested,set())
            if fillers: result.append(ApplicationBinding(sel.output_port_ref,tuple(fillers)))
        return tuple(result),tuple(nested[key] for key in sorted(nested))

    def _resolve_filler(self,ref,goal):
        app=self.store.get_record(RecordKind.SEMANTIC_APPLICATION,ref)
        if app is not None:
            exact=[p for p in (*goal.source_pins,*getattr(goal,'authorization_pins',())) if p.record_kind==RecordKind.SEMANTIC_APPLICATION and p.record_ref==ref]
            exact={p.key+(p.record_fingerprint,):p for p in exact}
            if len(exact)!=1:
                raise ValueError(f"semantic-application filler requires one exact goal-lineage pin: {ref}")
            pin=next(iter(exact.values())); stored=self._exact(pin,RecordKind.SEMANTIC_APPLICATION)
            return PortFillerClass.SEMANTIC_APPLICATION,stored
        for kind in (RecordKind.REFERENT,RecordKind.PROPOSITION,RecordKind.CLAIM_OCCURRENCE,RecordKind.EVENT_OCCURRENCE):
            stored=self.store.get_record(kind,ref)
            if stored is not None:return PortFillerClass.REFERENT,stored
        raise ValueError(f"response selector resolved a non-UOL/dangling filler reference: {ref}")

    def _collect_application_closure(self,stored,goal,goal_context,nested,visiting):
        if stored.record_ref in nested:return
        if stored.record_ref in visiting:raise ValueError(f"cyclic durable semantic-application closure: {stored.record_ref}")
        app=stored.payload
        if not isinstance(app,SemanticApplication):raise ValueError("nested application pin did not decode SemanticApplication")
        if app.context_ref!=goal_context:raise ValueError("response transform cannot silently merge nested application contexts")
        visiting.add(stored.record_ref);nested[stored.record_ref]=stored
        for binding in app.bindings:
            for filler in binding.fillers:
                if not isinstance(filler,FillerRef):raise ValueError("nested quoted literal requires an explicit response transform")
                if filler.filler_class==PortFillerClass.SEMANTIC_APPLICATION:
                    _cls,child=self._resolve_filler(filler.ref,goal);self._collect_application_closure(child,goal,goal_context,nested,visiting)
                elif filler.filler_class==PortFillerClass.COORDINATION_GROUP:
                    raise ValueError("durable nested coordination requires explicit Response-UOL reconstruction")
        visiting.remove(stored.record_ref)

    def _source_application(self,source,goal):
        if isinstance(source,SemanticApplication): return source
        app_ref=getattr(source,'participant_application_ref',None)
        if app_ref:
            pins=[p for p in goal.source_pins if p.record_kind==RecordKind.SEMANTIC_APPLICATION and p.record_ref==app_ref]
            unique={p.key+(p.record_fingerprint,):p for p in pins}
            if len(unique)!=1:raise ValueError("event response transform requires one exact participant application source pin")
            return self._exact(next(iter(unique.values())),RecordKind.SEMANTIC_APPLICATION).payload
        return None
    @staticmethod
    def _primary_ref(source):
        for name in ('application_ref','proposition_ref','claim_ref','claim_record_ref','event_ref','frontier_ref','assessment_ref','knowledge_ref','assignment_ref','delta_ref','capability_ref','result_ref'):
            v=getattr(source,name,None)
            if v:return str(v)
        raise ValueError(f"source lacks stable semantic ref: {type(source).__name__}")
    @staticmethod
    def _check_required_status(rule,source):
        if not rule.required_source_statuses:return
        status=getattr(source,'status',None) or getattr(source,'truth_status',None) or getattr(source,'occurrence_status',None)
        value=getattr(status,'value',status)
        if value not in set(rule.required_source_statuses): raise ValueError("source status is not licensed by response transform rule")
    def _exact(self,pin,kind=None):
        if kind is not None and pin.record_kind!=kind: raise ValueError(f"expected {kind.value} pin")
        s=self.store.get_record(pin.record_kind,pin.record_ref,pin.revision)
        if s is None or s.record_fingerprint!=pin.record_fingerprint: raise ValueError(f"stale response dependency: {pin.key}")
        return s


class ResponseAuthorizationGate:
    def __init__(self,store): self.store=store
    def require_authorized(self,response:ResponseUOLRecord,proofs:tuple[ResponseTransformationProof,...]):
        decision=self._exact(response.goal_decision_pin)
        latest=self.store.get_record(RecordKind.GOAL_DECISION,response.goal_decision_pin.record_ref)
        if latest is None or latest.revision!=response.goal_decision_pin.revision or latest.record_fingerprint!=response.goal_decision_pin.record_fingerprint: raise ValueError("stale goal decision before Response UOL commit")
        proof_map={p.proof_ref:p for p in proofs}
        if set(response.transformation_proof_refs)!=set(proof_map): raise ValueError("Response UOL proof set mismatch")
        selected={p.record_ref:p for p in response.selected_goal_pins}
        for gp in response.selected_goal_pins:
            gs=self._exact(gp)
            if gp.record_ref not in decision.payload.selected_goal_refs or not getattr(gs.payload,'authorized',False): raise ValueError("Response UOL contains unselected/unauthorized goal")
        for sp in response.source_pins:
            s=self._exact(sp)
            current=self.store.get_record(sp.record_kind,sp.record_ref)
            if current is None or current.revision!=sp.revision or current.record_fingerprint!=sp.record_fingerprint: raise ValueError("Response UOL source is no longer current")
            permission=s.permission_ref or getattr(s.payload,'permission_ref','conversation')
            if permission not in {'public',response.permission_ref}: raise ValueError("Response UOL would widen source permission")
        proof_outputs=set()
        proof_inputs=set()
        for proof in proofs:
            if proof.goal_candidate_pin.record_ref not in selected: raise ValueError("response proof belongs to unselected goal")
            rule_stored=self._exact(proof.rule_pin)
            if not isinstance(rule_stored.payload,ResponseTransformRuleRecord) or not rule_stored.payload.executable: raise ValueError("response proof uses non-executable transform rule")
            for p in (*proof.input_pins,*proof.authorization_pins):
                self._exact(p)
                current=self.store.get_record(p.record_kind,p.record_ref)
                if current is None or current.revision!=p.revision or current.record_fingerprint!=p.record_fingerprint: raise ValueError("response proof dependency is no longer current")
            proof_outputs.update(proof.output_refs);proof_inputs.update(p.key for p in proof.input_pins)
        root_refs={root.ref for root in response.graph.root_refs if root.filler_class==PortFillerClass.SEMANTIC_APPLICATION}
        if proof_outputs != root_refs: raise ValueError("Response UOL roots must equal exact authorized proof outputs")
        reachable=self._reachable_applications(response.graph)
        if reachable != set(response.graph.applications): raise ValueError("Response UOL contains unrooted or missing nested applications")
        if not proof_inputs.issubset({p.key for p in response.source_pins}): raise ValueError("response proof uses undeclared source input")
        if response.graph.unresolved_refs and not response.unresolved_frontier_refs: raise ValueError("unresolved response meaning must remain explicit frontiers")
        if set(response.graph.unresolved_refs) != set(response.unresolved_frontier_refs): raise ValueError("Response UOL unresolved frontier sets differ")
        return True
    @staticmethod
    def _reachable_applications(graph):
        seen=set();visiting=set()
        def visit_app(ref):
            if ref in seen:return
            if ref in visiting:raise ValueError("cyclic Response UOL application closure")
            app=graph.applications.get(ref)
            if app is None:raise ValueError(f"Response UOL references missing nested application: {ref}")
            visiting.add(ref)
            for binding in app.bindings:
                for filler in binding.fillers:
                    if isinstance(filler,FillerRef) and filler.filler_class==PortFillerClass.SEMANTIC_APPLICATION:visit_app(filler.ref)
                    elif isinstance(filler,FillerRef) and filler.filler_class==PortFillerClass.COORDINATION_GROUP:
                        group=graph.coordination_groups.get(filler.ref)
                        if group is None:raise ValueError(f"Response UOL references missing coordination group: {filler.ref}")
                        for member in group.members:
                            if member.filler_class==PortFillerClass.SEMANTIC_APPLICATION:visit_app(member.ref)
                        for rel in graph.scope_relations:
                            if rel.scoped_ref.ref==group.group_ref:visit_app(rel.operator_application_ref)
            scoped_relations=[rel for rel in graph.scope_relations if rel.scoped_ref.ref==ref]
            for rel in scoped_relations:
                visit_app(rel.operator_application_ref)
            visiting.remove(ref);seen.add(ref)
        for root in graph.root_refs:
            if root.filler_class==PortFillerClass.SEMANTIC_APPLICATION:visit_app(root.ref)
            elif root.filler_class==PortFillerClass.COORDINATION_GROUP:
                group=graph.coordination_groups.get(root.ref)
                if group is None:raise ValueError(f"Response UOL root coordination group missing: {root.ref}")
                for member in group.members:
                    if member.filler_class==PortFillerClass.SEMANTIC_APPLICATION:visit_app(member.ref)
                for rel in graph.scope_relations:
                    if rel.scoped_ref.ref==group.group_ref:visit_app(rel.operator_application_ref)
        return seen
    def _exact(self,p):
        s=self.store.get_record(p.record_kind,p.record_ref,p.revision)
        if s is None or s.record_fingerprint!=p.record_fingerprint: raise ValueError(f"stale response authorization pin: {p.key}")
        return s
