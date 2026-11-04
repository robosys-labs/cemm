"""G5 v8: 32 exact joint states, no new TRAIN or TEST fitted scalars.

One shared reliability-mode variable correlates all scope beliefs. Model
updates use ONLY time, typed provenance and selected physical payoffs.
The public epoch may independently change local meaning and trust mode.
"""
from math import isclose
from .temporal_belief_v5 import _likelihoods

H=.15
EA=.03
EB=.20
STATES=32
LOCAL=4
TRUST=16

def _transition(weights,h=H):
    out=[0.]*STATES
    for i,mass in enumerate(weights):
        for change_local in (0,1):
            local_prob=h if change_local else 1-h
            for change_trust in (0,1):
                p=local_prob*(h if change_trust else 1-h)
                out[i ^ (LOCAL if change_local else 0) ^
                    (TRUST if change_trust else 0)]+=mass*p
    return out

def _slot(record):
    if record.term=='nav':
        if len(record.scope)!=1:
            raise ValueError('sentinel outside root')
        return 3
    if record.term!='qor':
        raise ValueError('unknown public physical term')
    depth=len(record.scope)
    if depth not in (1,2,3):
        raise ValueError('unregistered scope depth')
    return depth-1

def _predict(weights,record):
    if _likelihoods(record) is None:
        raise ValueError('selected physical prediction missing')
    source=record.source
    if source not in ('sensor-A','sensor-B'):
        raise ValueError('unrecognized physical source')
    bit=1<<_slot(record)
    a,b=record.probabilities
    p=0.
    for state,w in enumerate(weights):
        reversed_mode=bool(state&TRUST)
        e=(EB if source=='sensor-A' else EA) if reversed_mode else (
            EA if source=='sensor-A' else EB)
        native=b if state&bit else a
        p+=w*(e+(1-2*e)*native)
    return p

def _update(weights,record):
    if _likelihoods(record) is None:
        return weights
    bit=1<<_slot(record)
    a,b=record.probabilities
    posterior=[]
    for state,mass in enumerate(weights):
        rev=bool(state&TRUST)
        e=(EB if record.source=='sensor-A' else EA) if rev else (
            EA if record.source=='sensor-A' else EB)
        p=e+(1-2*e)*(b if state&bit else a)
        posterior.append(mass*(p if record.outcome else 1-p))
    z=sum(posterior)
    return [v/z for v in posterior] if z>0 else weights

def state_after(records,after_epoch=False,forecasts=False):
    weights=[1/STATES]*STATES
    predictions=[]
    boundary_at=set()
    seen={}
    ordered=sorted(records,key=lambda r:(r.event_time,r.evidence_id))
    for r in ordered:
        prior=seen.get(r.evidence_id)
        if prior is not None:
            if prior!=r:
                raise ValueError('conflicting physical evidence identity')
            continue
        seen[r.evidence_id]=r
        if not r.physical:
            continue
        # One transition per public epoch timestamp, never per receipt.
        if r.epoch and r.event_time not in boundary_at:
            weights=_transition(weights)
            boundary_at.add(r.event_time)
        if _likelihoods(r) is None:
            raise ValueError('partial physical payoff')
        predictions.append(_predict(weights,r))
        weights=_update(weights,r)
    if after_epoch:
        # Counterfactual *public* epoch transition before any new payoff:
        # no knowledge of whether either hidden state actually changed.
        if boundary_at:
            raise ValueError('public epoch already observed')
        weights=_transition(weights)
    z=sum(weights)
    if not isclose(z,1.,abs_tol=1e-10):
        raise ValueError('joint weights unnormalized')
    return (weights,tuple(predictions)) if forecasts else weights

def _marginal(weights,bit):
    return sum(p for i,p in enumerate(weights) if i&bit)

def belief(weights,term,scope,records):
    if not scope:
        raise ValueError('empty query scope')
    if term=='nav':
        return _marginal(weights,8)
    if term!='qor':
        raise ValueError('unknown query term')
    # Exactly the supplied hierarchy; sibling/outside have no direct
    # evidence and inherit the most-specific observed parent.
    observed={r.scope for r in records if r.term=='qor' and r.physical}
    match=next((depth for depth in range(len(scope),0,-1)
                if scope[:depth] in observed),0)
    bit={0:1,1:1,2:2,3:4}[match]
    return _marginal(weights,bit)

def trust_probability(weights):
    return _marginal(weights,TRUST)

def views(ep):
    pre=ep.records[:12]
    mid=ep.records[:13]
    final=ep.records
    before=state_after(pre,after_epoch=True)
    midw=state_after(mid)
    finalw=state_after(final)
    return dict(
        pre_after_epoch_local=belief(before,'qor',ep.unit,pre),
        mid_local=belief(midw,'qor',ep.unit,mid),
        final_local=belief(finalw,'qor',ep.unit,final),
        final_sibling=belief(finalw,'qor',ep.sibling,final),
        final_root=belief(finalw,'qor',ep.outside,final),
        final_sentinel=belief(finalw,'nav',ep.unit,final),
        trust_pre=trust_probability(before),
        trust_mid=trust_probability(midw),
        trust_final=trust_probability(finalw))

def payoff_forecasts(records):
    return state_after(records,forecasts=True)[1]
