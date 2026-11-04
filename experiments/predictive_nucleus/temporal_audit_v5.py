"""G5 v5 collection/scoring boundary: forecasts precede evaluator-only truth.

This scorer consumes saved probabilities, not a candidate fit or oracle at
collection time. The challenge's physical bank is previously opened; this
only gives bounded development evidence, not independent scientific custody.
"""
from collections import Counter
from hashlib import sha256
import json
import time

from .revision_memory import Memory
from .revision_study import scoped_latest
from .revision_outcome import posterior as old_scalar_posterior, decision as old_scalar_decision
from .temporal_belief_v5 import (probability, decision, causal_nll,
                                 predictive_payoff, TimedReceipt, _update, _likelihoods)
from .temporal_task_v5 import episodes, inventory


VIEWS=('pre_unit','post_unit','post_sibling','post_outside','post_nav')
FEES=(.05,.75,None)
ARMS=('temporal','scoped_rule','latest','v4_scalar','no_memory')


def case_id(law,seed,i):
    return sha256(f'g5-v5:{law}:{seed}:{i}'.encode()).hexdigest()[:20]


def record_digest(records):
    rows=[(r.evidence_id,r.term,r.scope,r.event_time,r.source,r.probabilities,
           r.outcome,r.physical,getattr(r,'epoch',False)) for r in records]
    return sha256(json.dumps(rows,separators=(',',':')).encode()).hexdigest()


def payoff_forecasts(records,h,e):
    """Freeze every one-step action-payoff probability before its observation."""
    states={}
    timed=set()
    saved=[]
    for rec in records:
        if _likelihoods(rec) is None:
            continue
        key=(rec.term,rec.scope)
        p=states.get(key,.5)
        stamp=(key,rec.event_time)
        boundary=getattr(rec,'epoch',False) and stamp not in timed
        saved.append(predictive_payoff(p,rec.probabilities,e,boundary,h))
        if boundary:
            timed.add(stamp)
        current=TimedReceipt(rec.evidence_id,rec.term,rec.scope,rec.event_time,
                             rec.source,rec.probabilities,rec.outcome,True,boundary)
        states[key]=_update(p,current,h,e)
    return tuple(saved)


def collect(law,seed,bank,fit):
    """No reference to Episode.truth or Episode.variant in collection."""
    h,e=fit['h'],fit['e']
    t0=time.process_time()
    saved=[]
    for i,ep in enumerate(episodes(law,seed,'challenge',bank)):
        pre=Memory(ep.records[:13])
        post=Memory(ep.records[:15])
        post.add(ep.records[15])   # unverified false assertion
        views=(
            ('qor',ep.unit,pre),('qor',ep.unit,post),
            ('qor',ep.sibling,post),('qor',ep.outside,post),
            ('nav',ep.unit,post))
        cell=[]
        for term,scope,memory in views:
            p=probability(memory.snapshot(),term,scope,h,e)
            cell.append((p,memory.belief(term,scope),
                         scoped_latest(memory,term,scope),
                         old_scalar_posterior(memory,term,scope,.0025)))
        saved.append((case_id(law,seed,i),record_digest(ep.records),cell,
                      payoff_forecasts(ep.records,h,e)))
    if len(saved)!=192:
        raise ValueError('incomplete recorded TEST decision bank')
    return {'law':law,'seed':seed,'source':'challenge',
            'fit':(h,e),'rows':saved,'cpu_seconds':time.process_time()-t0}


def _price(state,truth,fee):
    ask=state is None and fee is not None and fee < .5
    chosen=truth if ask else (state if state is not None else 0)
    return int(chosen==truth),int(ask),int(state is None),int(state is not None and state!=truth)


def _nll(rows):
    from math import log
    total=0.;n=0
    for ep in rows:
        for r in ep.records:
            if not r.physical or r.probabilities is None:continue
            a,b=r.probabilities
            p=.5*(a+b)
            total-=log(max(p if r.outcome else 1-p,1e-12))
            n+=1
    return total/n


def score(raw,law,seed,bank,fit):
    """All truth access and policy utility joins occur after raw publication."""
    if (raw['law'],raw['seed'],raw['source'])!=(law,seed,'challenge'):
        raise ValueError('wrong saved challenge condition')
    if tuple(raw['fit'])!=(fit['h'],fit['e']):
        raise ValueError('published TRAIN fit differs from collected policy')
    source=inventory(law,seed,'challenge',bank)
    if len(raw['rows'])!=len(source):
        raise ValueError('missing planned physical decisions')
    totals=Counter()
    view_totals={v:Counter() for v in VIEWS}
    pre_twins=[]
    proper_nll=proper_brier=0.
    bins=[[0,0.,0.] for _ in range(10)]
    from math import log
    for i,(ep,entry) in enumerate(zip(source,raw['rows'],strict=True)):
        ident,sha,cells,payoff_preds=entry
        if (ident!=case_id(law,seed,i) or sha!=record_digest(ep.records)
                or len(cells)!=5 or len(payoff_preds)!=15):
            raise ValueError('challenge source / row identity mismatch')
        actual=[r.outcome for r in ep.records if _likelihoods(r) is not None]
        if len(actual)!=15 or any(type(v) is not int or v not in (0,1)
                                  for v in actual):
            raise ValueError('invalid complete payoff record')
        for p,y in zip(payoff_preds,actual,strict=True):
            if type(p) not in (int,float) or not 0<=p<=1:
                raise ValueError('invalid saved causal probability')
            proper_nll-=log(max(p if y else 1-p,1e-12))
            proper_brier+=(p-y)**2
            bucket=min(9,int(p*10))
            bins[bucket][0]+=1
            bins[bucket][1]+=p
            bins[bucket][2]+=y
        outcomes=(ep.truth[2],ep.truth[2],ep.truth[1],ep.truth[0],ep.truth[3])
        for j,(cell,target) in enumerate(zip(cells,outcomes,strict=True)):
            if len(cell)!=4 or not 0<=cell[0]<=1 or not 0<=cell[3]<=1 or any(v is not None and
               (type(v) is not int or v not in (0,1)) for v in cell[1:3]):
                raise ValueError('invalid collected probability/rule')
            p,rule,latest,older=cell
            states=(decision(p),rule,latest,old_scalar_decision(older),None)
            v=VIEWS[j]
            # An epistemic twin has two equally likely hidden worlds and
            # the same public prefix; retain both in all denominators.
            if j==0:
                pre_twins.append((p,states[0],target))
            for arm,state in zip(ARMS,states,strict=True):
                for index,fee in enumerate(FEES):
                    ok,ask,abstain,wrong=_price(state,target,fee)
                    prefix=f'{arm}_{index}'
                    view_totals[v][f'{prefix}_correct']+=ok
                    view_totals[v][f'{prefix}_ask']+=ask
                    view_totals[v][f'{prefix}_abstain']+=abstain
                    view_totals[v][f'{prefix}_wrong_confident']+=wrong
                    view_totals[v][f'{prefix}_net100']+=100*ok-int((fee or 0)*100)*ask
            totals['contexts']+=1
        totals['episodes']+=1
    if len(pre_twins)!=192 or totals['contexts']!=960:
        raise ValueError('wrong test denominator')
    # Consecutive same-source public twins with opposing oracle meanings.
    for left,right in zip(pre_twins[::2],pre_twins[1::2],strict=True):
        if (left[:2]!=right[:2] or left[2]==right[2]):
            raise ValueError('prefeedback indistinguishability broken')
        totals['pre_twin_pairs']+=1
        totals['pre_confident_pairs']+=left[2] is not None
    h,e=fit['h'],fit['e']
    observed=[ep.records for ep in source]
    n=totals['episodes']*15
    model_nll=proper_nll/n
    model_brier=proper_brier/n
    model_ece=sum(count/n*abs(p_sum/count-y_sum/count)
        for count,p_sum,y_sum in bins if count)
    plain_nll=_nll(source)
    no_exception_nll,_=causal_nll(observed,h,0)
    no_transition_nll,_=causal_nll(observed,0,e)
    baseline=totals['contexts']
    for arm in ARMS:
        for i in range(3):
            label=f'{arm}_{i}'
            correct=sum(z[f'{label}_correct'] for z in view_totals.values())
            questions=sum(z[f'{label}_ask'] for z in view_totals.values())
            net=sum(z[f'{label}_net100'] for z in view_totals.values())/100/baseline
            totals[f'{label}_correct']=correct
            totals[f'{label}_questions']=questions
            totals[f'{label}_mean_net']=net
    totals.update({'candidate_causal_nll':model_nll,'uniform_causal_nll':plain_nll,
                   'no_exception_causal_nll':no_exception_nll,
                   'no_transition_causal_nll':no_transition_nll,
                   'causal_payoffs':n,'candidate_brier':model_brier,
                   'candidate_ece_10bin_descriptive':model_ece})
    return {'law':law,'seed':seed,'totals':dict(totals),
            'views':{k:dict(v) for k,v in view_totals.items()}}
