"""G5 v3: balanced, selected-payoff TRAIN diagnosis of the frozen v2 filter."""
from dataclasses import dataclass
from itertools import product
from math import log
from .revision_memory import Memory
from .revision_outcome import GRID, decision, history, posterior
from .revision_study import select_triples

STRATA = ('pre','post','retain')

@dataclass(frozen=True)
class Example:
    memory: Memory
    term: str
    scope: tuple
    probs: tuple
    observed: int

def sample(m, term, scope, matrix, action, outcome):
    a,b = matrix[action]
    if not (0 <= a <= 1 and 0 <= b <= 1 and type(outcome) is int and outcome in (0,1)):
        raise ValueError('invalid observed selected-action payoff')
    return Example(Memory(m.snapshot()),term,scope,(a,b),outcome)

def train_rows(bank, seed):
    rows = {band:[] for band in STRATA}
    gold = {band:[] for band in STRATA}  # audit-only; never used by fit()
    pair_count = 0
    for k,(earlier,probe,later) in enumerate(select_triples(bank,seed)):
        for old,regional,sentinel,action in product((0,1),repeat=4):
            key = f'balanced-{k}-{old}-{regional}-{sentinel}-{action}'
            pair = []
            for reversal in (0,1):
                full,scopes,truth = history(earlier,probe,key,old,regional,
                                            sentinel,action,0,reversal)
                prefix = Memory(r for r in full.snapshot() if r.event_time < 4)
                local,sibling,outside = scopes
                pre = sample(prefix,'qor',local,later[1],action,
                             later[0]['rewards'][action][truth[0]])
                post = sample(full,'qor',local,later[1],action,
                              later[0]['rewards'][action][truth[0]])
                for band,row,target in (('pre',pre,truth[0]),('post',post,truth[0])):
                    rows[band].append(row)
                    gold[band].append(target)
                for term,scope,target in (('qor',sibling,regional),
                                          ('qor',outside,old),('nav',local,sentinel)):
                    row = sample(full,term,scope,later[1],action,
                                 later[0]['rewards'][action][target])
                    rows['retain'].append(row)
                    gold['retain'].append(target)
                pair.append((pre,post))
            a,b = pair
            if (a[0].memory.snapshot()!=b[0].memory.snapshot()
                or a[0].scope!=b[0].scope or a[0].probs!=b[0].probs
                or a[0].observed==b[0].observed
                or a[1].memory.snapshot()==b[1].memory.snapshot()):
                raise ValueError('broken pre-payoff counterfactual twins')
            pair_count += 1
    counts = {band:len(items) for band,items in rows.items()}
    if pair_count!=96 or counts!={'pre':192,'post':192,'retain':576}:
        raise ValueError(f'incomplete TRAIN inventory: {pair_count}, {counts}')
    return rows,gold,pair_count

def nll(row, p):
    a,b = row.probs
    q = (1-p)*a+p*b
    return -log(max(q if row.observed else 1-q,1e-12))

def fit(rows):
    """One shared scalar chosen only from selected physical payoffs."""
    losses = {}
    for s in GRID:
        by_band={band:sum(nll(r,posterior(r.memory,r.term,r.scope,s))
                for r in rows[band])/len(rows[band]) for band in STRATA}
        losses[s] = {'strata_nll':by_band,'balanced_nll':sum(by_band.values())/3}
    chosen=min(GRID,key=lambda s:(losses[s]['balanced_nll'],s))
    return chosen,losses

def audit(rows,gold,s):
    counts={}
    for band in STRATA:
        confident=wrong=0
        max_confidence=.5
        for row,target in zip(rows[band],gold[band],strict=True):
            p=posterior(row.memory,row.term,row.scope,s)
            guess=decision(p)
            confident+=guess is not None
            wrong+=guess is not None and guess!=target
            max_confidence=max(max_confidence,p,1-p)
        counts[band]={'confident':confident,'wrong_confident':wrong,
                      'max_confidence':max_confidence}
    if counts['pre']['confident']%2: raise ValueError('broken twin symmetry')
    counts['pre']['confident_pairs']=counts['pre']['confident']//2
    return counts

def audit_rule(rows,gold):
    """Previously retained rule; decisions only, without invented probabilities."""
    out={}
    for band in STRATA:
        valid=wrong=0
        for row,target in zip(rows[band],gold[band],strict=True):
            pred=row.memory.belief(row.term,row.scope)
            valid+=pred is not None
            wrong+=pred is not None and pred!=target
        out[band]={'confident':valid,'wrong_confident':wrong}
    out['pre']['confident_pairs']=out['pre']['confident']//2
    return out

def diagnose(law,seed,bank,previous):
    rows,gold,pairs=train_rows(bank,seed)
    selected,losses=fit(rows)
    grid={}
    for s in GRID:
        checks=audit(rows,gold,s)
        joint=(checks['pre']['confident']==0
               and checks['post']['confident']==192
               and checks['post']['wrong_confident']==0
               and checks['retain']['confident']==576
               and checks['retain']['wrong_confident']==0)
        grid[str(s)]={**losses[s],'audit':checks,'joint_pass':joint}
    possible=[s for s in GRID if grid[str(s)]['joint_pass']]
    verdict=('REVISE_REPRESENTATION' if not possible else
             'REVISE_OBJECTIVE' if selected not in possible else
             'KEEP_BALANCED_OBJECTIVE_TRAIN_DIAGNOSTIC')
    return {'law':law,'seed':seed,'train_only':True,'matched_prefix_pairs':pairs,
            'v1_rule_audit':audit_rule(rows,gold),
            'rows':{x:len(rows[x]) for x in STRATA},'v2_switch':previous,
            'balanced_switch':selected,'feasible_switches':possible,
            'decision':verdict,'grid':grid}

def run():
    import json
    from pathlib import Path
    from .transfer_task import catalogue
    frozen=json.loads((Path(__file__).parent/
         'results/revision-v2/train-fitted.json').read_text())
    if frozen['stage']!='train_only' or len(frozen['condition_fits'])!=10:
        raise ValueError('incorrect frozen v2 fits')
    return {f'{law}-{seed}':diagnose(law,seed,catalogue(law,'train'),
             frozen['condition_fits'][f'{law}-{seed}']['switch'])
             for law in ('nand','nor') for seed in (7,11,23,37,53)}

if __name__ == '__main__':
    import json
    print('G5_V3_TRAIN_OBJECTIVE '+json.dumps(run(),sort_keys=True),flush=True)
