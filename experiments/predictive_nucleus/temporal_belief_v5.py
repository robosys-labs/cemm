"""G5 v5: two-scalar temporal belief from observed selected-action payoffs.

The persistent meaning and event-local inversion are competing latent causes.
No latent meaning, gold role, corrective label or response is an input.
"""
from dataclasses import dataclass
from math import log

from .revision_memory import Memory, Receipt


@dataclass(frozen=True)
class TimedReceipt(Receipt):
    epoch: bool = False


def _likelihoods(record):
    if not record.physical or record.probabilities is None or record.outcome is None:
        return None
    a, b = record.probabilities
    if (type(record.outcome) is not int or record.outcome not in (0, 1)
            or not 0 <= a <= 1 or not 0 <= b <= 1):
        raise ValueError('invalid observed physical payoff')
    return (a,b) if record.outcome else (1-a,1-b)


def _update(p, rec, h, e):
    """Apply a real epoch transition, then marginalize a transient observation."""
    if rec.epoch:
        p = h + (1-2*h)*p
    likelihood = _likelihoods(rec)
    if likelihood is None:
        return p
    a,b = likelihood
    l0 = (1-e)*a + e*b
    l1 = (1-e)*b + e*a
    z = (1-p)*l0+p*l1
    # If this evidence is impossible under both allowed hypotheses, do not
    # invent an interpretation. The caller can preserve uncertainty instead.
    return p if z == 0 else p*l1/z


def _validate(h, e):
    if not (0 <= h <= .5 and 0 <= e < .5):
        raise ValueError('invalid temporal/exception probabilities')


def probability(records, term, scope, h, e):
    """P(persistent meaning=1) after source-attributed evidence at exact scopes.

    The supplied hierarchy controls fallback when a child has no observations.
    With new child evidence, both child meanings start equally possible.
    """
    _validate(h,e)
    if not scope:
        raise ValueError('empty scope')
    belief = .5
    for depth in range(1,len(scope)+1):
        direct = [r for r in records if r.term == term and r.scope == scope[:depth]
                  and _likelihoods(r) is not None]
        if not direct:
            continue
        p = .5
        # Each distinct evidence-ID contributes once (Memory performs dedup).
        by_time = {}
        for r in direct:
            by_time.setdefault(r.event_time,[]).append(r)
        for _,group in sorted(by_time.items()):
            group.sort(key=lambda r:r.evidence_id)
            # One transition per independently supplied epoch, never per
            # receipt on the same timestamp.
            boundary = any(getattr(r,'epoch',False) for r in group)
            if boundary:
                p = h+(1-2*h)*p
            for rec in group:
                # Already processed the single epoch for this timestamp.
                if getattr(rec,'epoch',False):
                    rec = TimedReceipt(rec.evidence_id,rec.term,rec.scope,
                        rec.event_time,rec.source,rec.probabilities,
                        rec.outcome,rec.physical,False)
                p = _update(p,rec,h,e)
        belief = p
    return belief


def decision(p, threshold=.95):
    if not 0 <= p <= 1 or not .5 < threshold <= 1:
        raise ValueError('invalid probability/decision threshold')
    return 1 if p >= threshold else (0 if p <= 1-threshold else None)


def predictive_payoff(p, row, e, epoch=False, h=0):
    """P(next selected payoff=1) before seeing its outcome."""
    _validate(h,e)
    a,b = row
    if not 0 <= a <= 1 or not 0 <= b <= 1:
        raise ValueError('invalid physical conditional forecasts')
    if epoch:
        p = h+(1-2*h)*p
    effective = e + (1-2*e)*p
    return (1-effective)*a+effective*b


def causal_nll(episodes,h,e):
    """Only observed selected payoffs fit h/e; no interpretation labels used."""
    _validate(h,e)
    loss = 0.
    n = 0
    for records in episodes:
        states = {}
        transitions = set()
        for rec in records:
            likelihood = _likelihoods(rec)
            if likelihood is None:
                continue
            key = (rec.term,rec.scope)
            p = states.get(key,.5)
            time_key = (key,rec.event_time)
            first_epoch = getattr(rec,'epoch',False) and time_key not in transitions
            pred = predictive_payoff(p,rec.probabilities,e,first_epoch,h)
            loss -= log(max(pred if rec.outcome else 1-pred,1e-12))
            n += 1
            if first_epoch:
                transitions.add(time_key)
            # Calculate posterior without double-counting any transition.
            rr = TimedReceipt(rec.evidence_id,rec.term,rec.scope,rec.event_time,
                              rec.source,rec.probabilities,rec.outcome,True,first_epoch)
            states[key] = _update(p,rr,h,e)
    if not n:
        raise ValueError('empty physical training tape')
    return loss/n,n


GRID_H = (.05,.15,.35,.5)
GRID_E = (.01,.05,.1,.2)


def fit(episodes):
    """Fixed-grid maximization of causally scored observed outcome likelihood."""
    grid = {}
    for h in GRID_H:
        for e in GRID_E:
            loss,n = causal_nll(episodes,h,e)
            grid[f'{h}:{e}'] = loss
    h,e = min(((h,e) for h in GRID_H for e in GRID_E),
              key=lambda v:(grid[f'{v[0]}:{v[1]}'],*v))
    return {'h':h,'e':e,'nll':grid[f'{h}:{e}'],
            'outcomes':n,'grid':grid}
