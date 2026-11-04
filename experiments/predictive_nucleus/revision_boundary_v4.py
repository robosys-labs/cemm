"""G5 v4: post-hoc TRAIN-only feasibility below v3's minimum switch rate."""
from itertools import product
from .revision_memory import Memory, Receipt
from .revision_objective_v3 import STRATA, train_rows, nll
from .revision_outcome import posterior, decision

RATES = (.00001,.000025,.00005,.0001,.0002,.0004,.0006,.0008,
         .001,.00125,.0015,.00175,.002,.00225,.0025)

def score_at(rows,gold,s):
    result={}
    for band in STRATA:
        correct=confident=wrong=0
        loss=0.
        for row,target in zip(rows[band],gold[band],strict=True):
            p=posterior(row.memory,row.term,row.scope,s)
            guess=decision(p)
            confident+=guess is not None
            correct+=guess is not None and guess==target
            wrong+=guess is not None and guess!=target
            loss+=nll(row,p)
        result[band]={'observations':len(rows[band]),'confident':confident,
                      'correct_confident':correct,'wrong_confident':wrong,
                      'abstained':len(rows[band])-confident,
                      'mean_nll':loss/len(rows[band])}
    pre=result['pre'];post=result['post'];ret=result['retain']
    if pre['confident']%2:
        raise ValueError('broken counterfactual twin pairing')
    result['pre_confident_pairs']=pre['confident']//2
    result['balanced_mean_nll']=sum(result[k]['mean_nll'] for k in STRATA)/3
    result['joint_pass']=(
        pre['confident']==0 and post['correct_confident']==192 and
        post['wrong_confident']==0 and ret['correct_confident']==576 and
        ret['wrong_confident']==0)
    return result

def temporal_no_info(rows,s):
    changed=0;max_abs_delta=0.;trials=0
    for row in rows['pre']:
        before=posterior(row.memory,row.term,row.scope,s)
        copy=Memory(row.memory.snapshot())
        copy.add(Receipt('noninformative-physical-check','qor',
                         row.scope,5,'verified-sensor',(.5,.5),1))
        after=posterior(copy,row.term,row.scope,s)
        changed+=decision(before)!=decision(after)
        max_abs_delta=max(max_abs_delta,abs(after-before))
        trials+=1
    return {'trials':trials,'changed_confident_decisions':changed,
            'maximum_abs_posterior_drift':max_abs_delta}

def analyze(law,seed,bank):
    rows,gold,pairs=train_rows(bank,seed)
    grid={}
    for s in RATES:
        cell=score_at(rows,gold,s)
        cell['no_info']=temporal_no_info(rows,s)
        grid[str(s)]=cell
    possible=[s for s in RATES if grid[str(s)]['joint_pass']]
    return {'law':law,'seed':seed,'train_only':True,
            'matched_prefix_pairs':pairs,
            'previous_v3_boundary':grid[str(.0025)],
            'feasible_rates':possible,
            'decision':('BOUNDED_REPRESENTATION_FEASIBLE_ON_TRAIN' if possible
                        else 'NO_FEASIBLE_RATE_IN_REGISTERED_SUBGRID'),
            'grid':grid}

def run():
    from .transfer_task import catalogue
    return {f'{law}-{seed}':analyze(law,seed,catalogue(law,'train'))
            for law,seed in product(('nand','nor'),(7,11,23,37,53))}

if __name__=='__main__':
    import json
    print('G5_V4_BOUNDARY_TRAIN '+json.dumps(run(),sort_keys=True),flush=True)
