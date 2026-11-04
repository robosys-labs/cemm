"""Evaluator-only G5 v6: proper meaning scores and goal-aware priced actions.

Scoring consumes a previously committed raw forecast bank and independently
regenerates oracle truths; no optimizer, fitting or new forecast is invoked.
"""
from collections import Counter
from math import log, isfinite
from .revision_study import scoped_latest
from .independent_task_v6 import inventory
from .temporal_audit_v5 import record_digest
from .goal_policy_v6 import GOALS, public_task, choose, after_answer

ARMS=('temporal','historical_temporal','scoped_rule','latest','no_memory')
VIEWS=('mid_local','final_local','final_sibling','final_root','final_sentinel')


def _p_of(cell,arm):
    if arm=='temporal': return cell[0]
    if arm=='historical_temporal': return cell[1]
    if arm=='scoped_rule': return .5 if cell[2] is None else cell[2]
    if arm=='latest': return .5 if cell[3] is None else cell[3]
    if arm=='no_memory':return .5
    raise ValueError('unknown policy')


def score(raw,law,seed,bank,trainfit):
    if (raw.get('version'),raw.get('law'),raw.get('seed'),raw.get('split'))!=(
        'g5-v6-raw',law,seed,'challenge'):
        raise ValueError('incorrect sealed raw condition')
    if tuple(raw['parameters'])!=(trainfit['h'],trainfit['e']):
        raise ValueError('refit or different parent parameters')
    source=inventory(law,seed,'challenge',bank)
    if len(raw['rows'])!=len(source):
        raise ValueError('incomplete frozen challenge rows')
    metrics={arm:Counter() for arm in ARMS}
    byview={view:{arm:Counter() for arm in ARMS} for view in VIEWS}
    bysource={source:Counter() for source in ('A','B')}
    bychange={str(v):Counter() for v in (False,True)}
    bins=[[0,0.,0.] for _ in range(10)]
    overall=Counter()
    seen=set()
    for ep, saved in zip(source,raw['rows'],strict=True):
        if saved['id']!=ep.uid or ep.uid in seen or saved['record_hash']!=record_digest(ep.records):
            raise ValueError('source hash/identity mismatch in frozen challenge')
        seen.add(ep.uid)
        if (saved['lineage']!=ep.lineage or list(saved['source_ids'])!=list(ep.observed_sources)
            or len(saved['beliefs'])!=5 or len(saved['payoff_p'])!=15):
            raise ValueError('incomplete or mismatched source/probability inventory')
        expected_goal=public_task(ep.uid)
        if (saved['fee']!=expected_goal[2] or
            saved['goals']!=[[list(x) for x in g] for g in expected_goal[:2]]):
            raise ValueError('goal or fee changed after collection')
        meanings=(ep.truth[3],ep.truth[3],ep.truth[1],ep.truth[0],ep.truth[4])
        changed=ep.truth[2]!=ep.truth[3]
        bychange[str(changed)]['episodes']+=1
        for view,cell,y in zip(VIEWS,saved['beliefs'],meanings,strict=True):
            if len(cell)!=4 or any(type(p) not in (float,int) or
                not isfinite(p) or not 0<=p<=1 for p in cell[:2]) or any(
                p is not None and (type(p) is not int or p not in (0,1))
                for p in cell[2:]):
                raise ValueError('bad saved belief')
            for arm in ARMS:
                p=_p_of(cell,arm)
                data=metrics[arm];v=byview[view][arm]
                b=(p-y)**2
                data['brier_sum']+=b
                v['brier_sum']+=b
                data['belief_cases']+=1
                v['belief_cases']+=1
                is_wrong_conf=(p>=.95 and y==0) or (p<=.05 and y==1)
                data['wrong_confident']+=is_wrong_conf
                v['wrong_confident']+=is_wrong_conf
                data['abstained_95']+=.05<p<.95
                if arm=='temporal':
                    loss=-log(max(p if y else 1-p,1e-12))
                    data['nll_sum']+=loss
                    v['nll_sum']+=loss
                    bin_i=min(9,int(p*10))
                    bins[bin_i][0]+=1
                    bins[bin_i][1]+=p
                    bins[bin_i][2]+=y
                    bychange[str(changed)]['belief_brier_sum']+=b
                    bychange[str(changed)]['belief_cases']+=1
        for p,r in zip(saved['payoff_p'],(r for r in ep.records if r.physical),strict=True):
            if type(p) not in (float,int) or not isfinite(p) or not 0<=p<=1:
                raise ValueError('invalid frozen causal payoff probability')
            loss=-log(max(p if r.outcome else 1-p,1e-12))
            b=(p-r.outcome)**2
            overall['payoff_nll_sum']+=loss
            overall['payoff_brier_sum']+=b
            overall['payoffs']+=1
            group=bysource[r.source.removeprefix('sensor-')]
            group['nll_sum']+=loss
            group['brier_sum']+=b
            group['observations']+=1
            group['realized_one']+=r.outcome
            if r.epoch:
                overall['epoch_payoffs']+=1
                overall['epoch_nll_sum']+=loss
        goals=expected_goal[:2]
        fee=expected_goal[2]
        truth=ep.truth[3]
        for arm in ARMS:
            data=metrics[arm]
            mid_p=_p_of(saved['beliefs'][0],arm)
            post_p=_p_of(saved['beliefs'][1],arm)
            first=choose(mid_p,goals[0],fee)
            if first['ask']:
                if fee is None:
                    raise ValueError('asked unavailable question')
                mid=after_answer(goals[0],truth)
                post=after_answer(goals[1],truth)  # scoped answer survives reset
                data['queries']+=1
                data['question_cost_sum']+=fee
                if fee>=.75 or first['voi']<=fee:
                    raise ValueError('purchased nonbeneficial question')
                data['query_after_beneficial_goal']+=1
            else:
                mid=first['action']
                post=choose(post_p,goals[1],None)['action']
            best=(max(goals[0][truth]),max(goals[1][truth]))
            earned=(goals[0][truth][mid],goals[1][truth][post])
            data['utility_sum']+=sum(earned)-(fee if first['ask'] else 0)
            data['gross_regret_sum']+=sum(best)-sum(earned)
            data['optimal_actions']+=sum(abs(earned[i]-best[i])<=1e-12 for i in (0,1))
            data['episodes']+=1
            data['action_count']+=2
        overall['episodes']+=1

    if overall['episodes']!=192 or overall['payoffs']!=2880 or len(seen)!=192:
        raise ValueError('incomplete scored denominator')
    report={}
    for arm,counts in metrics.items():
        d=dict(counts)
        # Empty counts are valid observations, not absent report fields.
        for field in ('queries','question_cost_sum','query_after_beneficial_goal',
                      'wrong_confident','abstained_95','gross_regret_sum'):
            d.setdefault(field,0)
        d['mean_brier']=d['brier_sum']/d['belief_cases']
        d['mean_net_per_action']=d['utility_sum']/d['action_count']
        d['mean_gross_regret_per_action']=d['gross_regret_sum']/d['action_count']
        d['optimal_action_rate']=d['optimal_actions']/d['action_count']
        if arm=='temporal':d['mean_belief_nll']=d['nll_sum']/d['belief_cases']
        report[arm]=d
    for v,byarm in byview.items():
        for arm,count in byarm.items():
            count.setdefault('wrong_confident',0)
            count.setdefault('abstained_95',0)
            count['mean_brier']=count['brier_sum']/count['belief_cases']
    for src,count in bysource.items():
        count['mean_nll']=count['nll_sum']/count['observations']
        count['mean_brier']=count['brier_sum']/count['observations']
    for key,count in bychange.items():
        count['mean_brier']=count['belief_brier_sum']/count['belief_cases']
    return dict(law=law,seed=seed,arms=report,
        view_scores={k:{a:dict(c) for a,c in v.items()} for k,v in byview.items()},
        sources={k:dict(c) for k,c in bysource.items()},
        epoch_change={k:dict(c) for k,c in bychange.items()},
        payoff=dict(n=overall['payoffs'],
            mean_nll=overall['payoff_nll_sum']/overall['payoffs'],
            mean_brier=overall['payoff_brier_sum']/overall['payoffs'],
            epoch_n=overall['epoch_payoffs'],
            epoch_mean_nll=overall['epoch_nll_sum']/overall['epoch_payoffs']),
        calibration=dict(bins=bins,ece=sum(n/960*abs(s/n-y/n)
                          for n,s,y in bins if n),
                         description='descriptive 10-bin ECE across 5 correlated meaning views'),
        limitations='opened inherited G3 physical banks; no external blind challenge')
