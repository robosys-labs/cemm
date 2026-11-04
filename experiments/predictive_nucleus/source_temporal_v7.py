"""G5 v7: source-conditioned physical likelihood, one extra scalar over v6.

Pure likelihood transformation exactly reuses the frozen two-state temporal
Bayes recursion. Each event's source ID is public; no gold interpretation,
actual sensor error, or hidden epoch truth is an input.
"""
from dataclasses import replace
from .temporal_belief_v5 import (probability as _v6_probability,
                                 causal_nll as _v6_nll,
                                 _likelihoods)
from .temporal_audit_v5 import payoff_forecasts as _v6_forecasts

H_GRID=(.05,.15,.35,.5)
EA_GRID=(.01,.03,.05,.1)
EB_GRID=(.05,.1,.2,.3)

def _check(h,ea,eb):
    if not (0<=h<=.5 and 0<=ea<.5 and 0<=eb<.5):
        raise ValueError('invalid temporal/source reliability')

def _condition(record,ea,eb):
    if _likelihoods(record) is None:
        return record  # unverified claims never supply physical evidence
    if record.source not in ('sensor-A','sensor-B'):
        raise ValueError('unrecognized physical source')
    e = ea if record.source == 'sensor-A' else eb
    a,b = record.probabilities
    # Sensor flips the OBSERVED BINARY REWARD, not the hidden meaning.
    # Mixing meaning columns would be wrong if a+b != 1.
    return replace(record, probabilities=(e+(1-2*e)*a,e+(1-2*e)*b))

def probability(records,term,scope,h,ea,eb):
    _check(h,ea,eb)
    return _v6_probability(
        tuple(_condition(r,ea,eb) for r in records),term,scope,h,0.)

def payoff_forecasts(records,h,ea,eb):
    _check(h,ea,eb)
    return _v6_forecasts(
        (_condition(r,ea,eb) for r in records),h,0.)

def causal_nll(tapes,h,ea,eb):
    _check(h,ea,eb)
    return _v6_nll(
        (( _condition(r,ea,eb) for r in tape) for tape in tapes),h,0.)

def fit(tapes):
    """Select exactly 3 parameters using public outcome likelihood only."""
    tapes=tuple(tuple(r for r in tape) for tape in tapes)
    if not tapes:
        raise ValueError('empty training data')
    grid={}
    n=None
    for ea in EA_GRID:
        for eb in EB_GRID:
            # Reuse the same prepared evidence for all transition rates.
            conditioned=tuple(tuple(_condition(r,ea,eb) for r in t)
                              for t in tapes)
            for h in H_GRID:
                loss,count=_v6_nll(conditioned,h,0.)
                if n is not None and count!=n:
                    raise ValueError('training evidence changed across grid')
                n=count
                grid[f'{h}:{ea}:{eb}']=loss
    h,ea,eb=min(((h,ea,eb) for h in H_GRID for ea in EA_GRID
                 for eb in EB_GRID),
                key=lambda z:(grid[f'{z[0]}:{z[1]}:{z[2]}'],*z))
    return {'h':h,'e_A':ea,'e_B':eb,'nll':grid[f'{h}:{ea}:{eb}'],
            'outcomes':n,'grid':grid}
