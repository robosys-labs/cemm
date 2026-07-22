#!/usr/bin/env python3
"""Execute Phase-15/16 core mechanics without requiring the full CEMM checkout.

This verifier installs only tiny baseline type stubs (ExactAuthorityPin, UseOperation,
semantic_fingerprint, StateDimensionSchema), then imports the real bundle modules directly.
It is intentionally narrower than repository pytest and must not be reported as a full-suite run.
"""
from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import json
import sys
import types
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _pkg(name: str, path: Path | None = None):
    mod = types.ModuleType(name)
    mod.__path__ = [] if path is None else [str(path)]
    sys.modules[name] = mod
    return mod


def _load(name: str, rel: str):
    path = ROOT / rel
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec and spec.loader
    spec.loader.exec_module(mod)
    return mod


def _canonical(value):
    if dataclasses.is_dataclass(value):
        return {f.name: _canonical(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda x: repr(x[0]))}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_canonical(v) for v in value]
    return value


def _fingerprint(namespace, value, length=64):
    raw = json.dumps([namespace, _canonical(value)], sort_keys=True, default=repr, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()[:length]


def install_stubs():
    _pkg("cemm", ROOT / "cemm")
    _pkg("cemm.v350", ROOT / "cemm/v350")
    _pkg("cemm.v350.csir")
    csir = types.ModuleType("cemm.v350.csir.model")

    @dataclass(frozen=True, slots=True)
    class ExactAuthorityPin:
        kind: str
        namespace: str
        ref: str
        revision: int
        content_hash: str
        scope_ref: str = "global"
        @property
        def key(self):
            return (self.kind, self.namespace, self.ref, self.revision, self.content_hash, self.scope_ref)

    @dataclass(frozen=True, slots=True)
    class CSIRGraph:
        root_refs: tuple = ()

    csir.ExactAuthorityPin = ExactAuthorityPin
    csir.CSIRGraph = CSIRGraph
    sys.modules[csir.__name__] = csir

    _pkg("cemm.v350.schema")
    schema = types.ModuleType("cemm.v350.schema.model")
    class UseOperation(str, Enum):
        QUERY="query"; INFER="infer"; TRANSITION="transition"; IMPACT="impact"; PLAN="plan"; EXECUTE="execute"; REALIZE="realize"; RESPONSE_POLICY="response_policy"
    @dataclass(frozen=True)
    class StateDimensionSchema:
        schema_ref: str
        revision: int = 1
        scalar: bool = False
        ordered: bool = False
        metadata: dict = dataclasses.field(default_factory=dict)
    schema.UseOperation = UseOperation
    schema.StateDimensionSchema = StateDimensionSchema
    schema.semantic_fingerprint = _fingerprint
    sys.modules[schema.__name__] = schema

    _pkg("cemm.v350.state", ROOT / "cemm/v350/state")
    _pkg("cemm.v350.causal", ROOT / "cemm/v350/causal")
    return ExactAuthorityPin, UseOperation


def main():
    Pin, UseOperation = install_stubs()
    sm = _load("cemm.v350.state.model_v351", "cemm/v350/state/model_v351.py")
    algm = _load("cemm.v350.state.algebra_v351", "cemm/v350/state/algebra_v351.py")
    trm = _load("cemm.v350.state.transition_v351", "cemm/v350/state/transition_v351.py")
    cm = _load("cemm.v350.causal.model_v351", "cemm/v350/causal/model_v351.py")
    engm = _load("cemm.v350.causal.engine_v351", "cemm/v350/causal/engine_v351.py")
    exm = _load("cemm.v350.causal.explanation_v351", "cemm/v350/causal/explanation_v351.py")

    def pin(kind, ref):
        return Pin(kind, "isolated-test", ref, 1, _fingerprint(kind, ref), "global")

    checks = {}

    # 1) Eight domain families + role-explicit relation + typed probability support.
    low, mid, high = [pin("state_value", x) for x in ("low", "mid", "high")]
    rel = pin("relation", "located-in"); located=pin("role","located"); container=pin("role","container")
    process = pin("process", "transfer")
    domains = (
        sm.StateDomainContractV351("cat",1,sm.StateDomainKind.CATEGORICAL,value_pins=(low,mid,high)),
        sm.StateDomainContractV351("ord",1,sm.StateDomainKind.ORDERED,value_pins=(low,mid,high)),
        sm.StateDomainContractV351("cont",1,sm.StateDomainKind.CONTINUOUS),
        sm.StateDomainContractV351("vec",1,sm.StateDomainKind.VECTOR,vector_size=2),
        sm.StateDomainContractV351("rel",1,sm.StateDomainKind.RELATIONAL,relation_pins=(rel,),relation_role_pins=(located,container),relation_signatures=(sm.RelationStateSignatureV351(rel,(located,container)),)),
        sm.StateDomainContractV351("set",1,sm.StateDomainKind.SET),
        sm.StateDomainContractV351("proc",1,sm.StateDomainKind.PROCESS,process_pins=(process,)),
        sm.StateDomainContractV351("prob",1,sm.StateDomainKind.PROBABILISTIC,support_domain_kind=sm.StateDomainKind.CATEGORICAL,value_pins=(low,high)),
    )
    assert {d.kind for d in domains} == set(sm.StateDomainKind)
    relation_value = sm.StateValueV351(sm.StateDomainKind.RELATIONAL, relation_pin=rel, relation_bindings=(sm.RelationStateRoleBindingV351(located,"r:1"),sm.RelationStateRoleBindingV351(container,"r:1")))
    algm.StateAlgebraV351().validate_value(domains[4], relation_value)
    prob = sm.StateValueV351(sm.StateDomainKind.PROBABILISTIC, probability_mass=(sm.ProbabilityPointV351(sm.StateValueV351(sm.StateDomainKind.CATEGORICAL,categorical_pin=low),0.25),sm.ProbabilityPointV351(sm.StateValueV351(sm.StateDomainKind.CATEGORICAL,categorical_pin=high),0.75)))
    algm.StateAlgebraV351().validate_value(domains[7], prob)
    checks["eight_typed_domains"] = True

    # 2) State identity ignores evidence; unit-bearing additive offsets cannot be bare numbers.
    unit=pin("unit","temperature")
    v1=sm.StateValueV351(sm.StateDomainKind.CONTINUOUS,scalar_value=10,unit_pin=unit,evidence_refs=("e:1",))
    v2=sm.StateValueV351(sm.StateDomainKind.CONTINUOUS,scalar_value=10,unit_pin=unit,evidence_refs=("e:2",))
    assert v1.value_ref == v2.value_ref
    unit_domain=sm.StateDomainContractV351("temp",1,sm.StateDomainKind.CONTINUOUS,unit_pin=unit)
    try:
        algm.StateAlgebraV351().apply(unit_domain,v1,sm.StateTransformExpression(sm.StateTransformOperator.ADD,(sm.StateOperandV351(sm.OperandKind.CONSTANT,constant=2.0),)),resolve_operand=lambda o:o.constant)
        raise AssertionError("bare unit-bearing addition was accepted")
    except sm.StateModelError:
        pass
    checks["state_identity_and_units"] = True

    # 3) Semantic role bindings, not derivation/voice identity, determine effects.
    role=pin("semantic_port","affected"); dim=pin("state_dimension","level"); eventpin=pin("semantic_definition","event"); case=pin("competence_case","transition")
    mechanism=sm.TransitionMechanismV351("m:role",1,sm.MechanismTriggerKind.EVENT,eventpin,(role,),deterministic_transforms=(sm.RoleStateTransformV351("t:add",role,dim,sm.StateTransformExpression(sm.StateTransformOperator.ADD,(sm.StateOperandV351(sm.OperandKind.CONSTANT,constant=2.0),))),),competence_case_pins=(case,),evidence_refs=("e:review",),lifecycle_status="active",authorized_use_operations=(UseOperation.TRANSITION,),use_authority_explicit=True)
    domain=sm.StateDomainContractV351("level",1,sm.StateDomainKind.CONTINUOUS)
    snap=trm.StateSnapshotV351(((trm.StateKeyV351("r:1",dim,"actual"),sm.StateValueV351(sm.StateDomainKind.CONTINUOUS,scalar_value=3)),),((dim.key,domain),))
    events=[trm.CausalEventV351(f"e:{x}",eventpin,(sm.ParticipantRoleBinding(role,"r:1",x),),"actual","t:0") for x in ("active-derivation","passive-derivation")]
    previews=[trm.TransitionPreviewEngineV351().preview_event(e,(mechanism,),snap) for e in events]
    vals=[p.distributions[0].branches[0][2][0].new_value.scalar_value for p in previews]
    assert vals == [5.0,5.0]
    checks["role_addressed_transition"] = True

    # 4) Unknown possible defeater with BLOCK cannot be assumed absent.
    cond=sm.MechanismPrecondition("c:def",role,dim,sm.ConditionOperatorV351.EQUALS,expected_value=sm.StateValueV351(sm.StateDomainKind.CONTINUOUS,scalar_value=1),unknown_policy=sm.UnknownConditionPolicyV351.BLOCK)
    blocked=sm.TransitionMechanismV351("m:def",1,sm.MechanismTriggerKind.EVENT,eventpin,(role,),defeaters=(sm.MechanismDefeater("d:1",cond,hard=True),),deterministic_transforms=(sm.RoleStateTransformV351("t:set",role,dim,sm.StateTransformExpression(sm.StateTransformOperator.ASSIGN,(sm.StateOperandV351(sm.OperandKind.CONSTANT,constant=sm.StateValueV351(sm.StateDomainKind.CONTINUOUS,scalar_value=1)),))),),competence_case_pins=(case,),evidence_refs=("e:review",),lifecycle_status="active",authorized_use_operations=(UseOperation.TRANSITION,),use_authority_explicit=True)
    empty=trm.StateSnapshotV351((),((dim.key,domain),))
    assert not trm.TransitionPreviewEngineV351().preview_event(events[0],(blocked,),empty).distributions
    checks["unknown_defeater_fails_closed"] = True

    # 5) Operational context/use changes do not mutate causal mechanism identity.
    same_semantics = dataclasses.replace(mechanism, context_scopes=("ctx:a",), metadata={"review_note":"a"})
    other_scope = dataclasses.replace(mechanism, context_scopes=("ctx:b",), metadata={"review_note":"b"})
    assert same_semantics.authority_pin.key == other_scope.authority_pin.key
    checks["mechanism_identity_separates_operational_scope"] = True

    # 6) Isolated worlds copy only declared parent/factual context, never an unrelated context.
    alt=sm.StateValueV351(sm.StateDomainKind.CONTINUOUS,scalar_value=99)
    multi=trm.StateSnapshotV351(((trm.StateKeyV351("r:1",dim,"actual"),sm.StateValueV351(sm.StateDomainKind.CONTINUOUS,scalar_value=3)),(trm.StateKeyV351("r:1",dim,"other"),alt)),((dim.key,domain),))
    isolated=engm.CausalPropagationEngine._isolate_context(multi,"cf:1",source_context_ref="actual")
    assert isolated.value("r:1",dim,"cf:1").scalar_value == 3
    checks["context_isolation_no_cross_world_leak"] = True

    # 7) Stochastic branch budget preserves unresolved mass rather than renormalizing.
    branches=tuple(sm.MechanismBranchV351(f"b:{i}",0.25,(sm.RoleStateTransformV351(f"t:{i}",role,dim,sm.StateTransformExpression(sm.StateTransformOperator.ASSIGN,(sm.StateOperandV351(sm.OperandKind.CONSTANT,constant=sm.StateValueV351(sm.StateDomainKind.CONTINUOUS,scalar_value=float(i))),))),)) for i in range(4))
    stochastic=sm.TransitionMechanismV351("m:stoch",1,sm.MechanismTriggerKind.EVENT,eventpin,(role,),branches=branches,competence_case_pins=(case,),evidence_refs=("e:review",),lifecycle_status="active",authorized_use_operations=(UseOperation.TRANSITION,),use_authority_explicit=True)
    result=engm.CausalPropagationEngine(mechanisms=(stochastic,),budget=cm.SimulationBudgetV351(maximum_branches=2)).simulate(initial_state=snap,root_events=(events[0],),context_semantics=cm.ContextSemantics.ACTUAL)
    assert len(result.branches)<=2 and result.unresolved_probability_mass >= 0.5-1e-9
    checks["bounded_probability_mass"] = True

    # 8) Query-result partiality invariant and branch→proof identity are enforced.
    assert all(b.proof_ref in {p.proof_ref for p in result.causal_proofs} for b in result.branches)
    try:
        cm.CausalQueryResultV351("qr:bad","q:1",False,cm.CausalExplanationV351("x","q:1","v",(),(),(),"p",(),True,1.0))
        raise AssertionError("unanswered result carried definitive explanation")
    except cm.CausalModelError:
        pass
    checks["proof_and_partial_query_invariants"] = True

    print(json.dumps({"ok": all(checks.values()), "checks": checks}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
