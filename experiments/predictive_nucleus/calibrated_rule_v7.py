"""One-scalar, outcome-calibrated display of the unchanged G5 rule.

Calibration predicts the next *observed selected payoff* from historical
public evidence; it never receives hidden meanings or oracle correctness.
"""
from math import log
from .revision_memory import Memory
from .temporal_belief_v5 import _likelihoods

DELTA_GRID=(.01,.05,.1,.15,.2,.3,.4)

def rule_probability(value,delta):
    if not (0 < delta < .5):
        raise ValueError('invalid smoothing')
    if value is None:
        return .5
    if type(value) is not int or value not in (0,1):
        raise ValueError('invalid rule state')
    return (1-delta) if value else delta

def probability(memory,term,scope,delta):
    return rule_probability(memory.belief(term,scope),delta)

def causal_nll(tapes,delta):
    total=0.
    count=0
    for tape in tapes:
        m=Memory()
        for rec in tape:
            if _likelihoods(rec) is None:
                if not rec.physical:
                    m.add(rec)
                continue
            p=probability(m,rec.term,rec.scope,delta)
            a,b=rec.probabilities
            pred=(1-p)*a+p*b
            total-=log(max(pred if rec.outcome else 1-pred,1e-12))
            count+=1
            m.add(rec)
    if not count:
        raise ValueError('empty selected-payoff training data')
    return total/count,count

def fit(tapes):
    tapes=tuple(tuple(t) for t in tapes)
    grid={}
    for d in DELTA_GRID:
        value,n=causal_nll(tapes,d)
        grid[str(d)]=value
    delta=min(DELTA_GRID,key=lambda d:(grid[str(d)],d))
    return {'delta':delta,'nll':grid[str(delta)],
            'outcomes':n,'grid':grid}
