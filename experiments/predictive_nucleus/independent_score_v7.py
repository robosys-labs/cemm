"""Evaluator-only v7 scoring; never fits or recollects a candidate."""
from collections import Counter,defaultdict
from math import isfinite,log
import json
from .independent_task_v7 import inventory,REGIME
from .temporal_audit_v5 import record_digest
from .goal_policy_v6 import choose,after_answer,public_task
from .independent_collection_v7 import VIEWS,ARMS

def _p(cell,arm):
    i=ARMS.index(arm)
    if i in (4,5): return .5 if cell[i] is None else float(cell[i])
    if i==6: return .5
    return cell[i]

def _wrong(p,y):
    return (p>=.95 and y==0) or (p<=.05 and y==1)

def _check_p(p):
    if type(p) not in (int,float) or not isfinite(p) or not 0<=p<=1:
        raise ValueError('invalid sealed probability')

def _add_payoff(out,p,y):
    _check_p(p)
    out['n']+=1
    out['brier_sum']+=(p-y)**2
    out['nll_sum']-=log(max(p if y else 1-p,1e-12))

def score(raw,law,seed,bank,freeze):
    m=freeze['fit'];d=freeze['rule']['delta']
    neutral=freeze['neutral']
    if ((raw.get('version'),raw.get('law'),raw.get('seed'),raw.get('split'))
            !=('g5-v7-raw',law,seed,'challenge')):
        raise ValueError('incorrect sealed v7 condition')
    if tuple(raw['parameters'])!=(m['h'],m['e_A'],m['e_B'],d,neutral['h'],neutral['e']):
        raise ValueError('changed fit after raw seal')
    episodes=inventory(law,seed,'challenge',bank)
    if len(episodes)!=len(raw['rows']) or len(episodes)!=192:
        raise ValueError('missing sealed episodes')
    arms={a:Counter() for a in ARMS}
    views={v:{a:Counter() for a in ARMS} for v in VIEWS}
    subgroups=defaultdict(lambda:{a:Counter() for a in ARMS})
    questions={a:Counter() for a in ARMS}
    payoffs={name:{s:Counter() for s in ('A','B')} for name in ('source_temporal','sensor_neutral','v6_frozen')}
    seen=set()
    for ep,saved in zip(episodes,raw['rows'],strict=True):
        if (ep.uid in seen or ep.uid!=saved['id']
            or record_digest(ep.records)!=saved['record_hash']
            or ep.lineage!=saved['lineage']
            or list(ep.observed_sources)!=list(saved['source_ids'])):
            raise ValueError('evidence identity/source/lineage mismatched')
        seen.add(ep.uid)
        if (len(saved['beliefs'])!=5 or len(saved['payoff_p'])!=15
            or len(saved['sensor_payoff_p'])!=15 or len(saved['v6_payoff_p'])!=15):
            raise ValueError('incomplete public forecast')
        goals=public_task(ep.uid)
        if (saved['fee']!=goals[2] or
            saved['goals']!=json.loads(json.dumps(goals[:2]))):
            raise ValueError('public goal was changed')
        targets=(ep.truth[3],ep.truth[3],ep.truth[1],ep.truth[0],ep.truth[4])
        changed=ep.truth[2]!=ep.truth[3]
        subgroup=('flip' if changed else 'stable')+'_'+ep.observed_sources[12]
        for vi,(view,cell,y) in enumerate(zip(VIEWS,saved['beliefs'],targets,strict=True)):
            if len(cell)!=6 or any(
                type(p) is not int or p not in (0,1)
                for p in cell[4:] if p is not None):
                raise ValueError('invalid raw meaning cell')
            for arm in ARMS:
                p=_p(cell,arm)
                _check_p(p)
                b=(p-y)**2
                data=arms[arm];detail=views[view][arm]
                data['brier_sum']+=b
                data['nll_sum']-=log(max(p if y else 1-p,1e-12))
                data['belief_cases']+=1
                data['wrong_confident']+=_wrong(p,y)
                detail['brier_sum']+=b
                detail['wrong_confident']+=_wrong(p,y)
                detail['n']+=1
                if vi in (0,1):
                    group=subgroups[subgroup][arm]
                    group[view+'_brier_sum']+=b
                    group[view+'_n']+=1
                if vi in (3,4) and arm=='source_temporal':
                    if _wrong(p,y) and not _wrong(_p(cell,'v6_frozen'),y):
                        data['new_parent_sentinel_confident_wrong']+=1
        physical=[r for r in ep.records if r.physical]
        if len(physical)!=15:
            raise ValueError('changed physical observation inventory')
        for rec,p,n,q in zip(physical,saved['payoff_p'],saved['sensor_payoff_p'],saved['v6_payoff_p'],strict=True):
            source=rec.source.removeprefix('sensor-')
            if source not in ('A','B'):
                raise ValueError('unrecognized raw sensor ID')
            _add_payoff(payoffs['source_temporal'][source],p,rec.outcome)
            _add_payoff(payoffs['sensor_neutral'][source],n,rec.outcome)
            _add_payoff(payoffs['v6_frozen'][source],q,rec.outcome)
        truth=ep.truth[3]
        for arm in ARMS:
            first=choose(_p(saved['beliefs'][0],arm),goals[0],goals[2])
            second=choose(_p(saved['beliefs'][1],arm),goals[1],None)
            ask=first['ask']
            if ask:
                if goals[2] is None or goals[2]>=.75:
                    raise ValueError('bad paid question')
                actions=(after_answer(goals[0],truth),
                         after_answer(goals[1],truth))
            else:
                actions=(first['action'],second['action'])
            gained=sum(goals[i][truth][actions[i]] for i in (0,1))
            best=sum(max(goals[i][truth]) for i in (0,1))
            total=gained-(goals[2] if ask else 0)
            z=arms[arm]
            z['utility_sum']+=total
            z['optimal_actions']+=sum(
                abs(goals[i][truth][actions[i]]-max(goals[i][truth]))<1e-12
                for i in (0,1))
            z['gross_regret_sum']+=best-gained
            z['action_count']+=2
            z['episodes']+=1
            z['queries']+=int(ask)
            z['query_fees_sum']+=(goals[2] if ask else 0.)
            if ask:
                refused=(first['action'],second['action'])
                without=sum(goals[i][truth][refused[i]] for i in (0,1))
                roi=gained-without-goals[2]
                q=questions[arm]
                q['n']+=1
                q['gross_gain_sum']+=gained-without
                q['realized_net_gain_sum']+=roi
                q['beneficial']+=roi>1e-12
                q['harmful']+=roi< -1e-12
                q['neutral']+=abs(roi)<=1e-12
            subgroups[subgroup][arm]['net_sum']+=total
            subgroups[subgroup][arm]['episodes']+=1
    if len(seen)!=192 or sum(x['n'] for x in payoffs['source_temporal'].values())!=2880:
        raise ValueError('incomplete world/payoff denominator')
    for arm,z in arms.items():
        z.setdefault('queries',0)
        z.setdefault('new_parent_sentinel_confident_wrong',0)
        z['mean_brier']=z['brier_sum']/z['belief_cases']
        z['mean_nll']=z['nll_sum']/z['belief_cases']
        z['net_per_action']=z['utility_sum']/z['action_count']
        z['optimal_rate']=z['optimal_actions']/z['action_count']
    for byarm in views.values():
        for z in byarm.values():
            z.setdefault('wrong_confident',0)
            z['mean_brier']=z['brier_sum']/z['n']
    for which,by in payoffs.items():
        total=Counter()
        for z in by.values():total.update(z)
        total['mean_nll']=total['nll_sum']/total['n']
        total['mean_brier']=total['brier_sum']/total['n']
        by['total']=total
    return {'law':law,'seed':seed,'regime':REGIME[seed],
            'arms':{k:dict(v) for k,v in arms.items()},
            'views':{k:{a:dict(c) for a,c in by.items()} for k,by in views.items()},
            'subgroups':{k:{a:dict(c) for a,c in v.items()}
                         for k,v in sorted(subgroups.items())},
            'question_value':{k:dict(v) for k,v in questions.items()},
            'payoff':{k:{s:dict(z) for s,z in v.items()} for k,v in payoffs.items()}}

def assess(reports):
    """Frozen pre-scoring scientific gates (development, not admission)."""
    if len(reports)!=10 or {(r['law'],r['seed']) for r in reports}!={
        (law,seed) for law in ('nand','nor') for seed in (7,11,23,37,53)}:
        raise ValueError('missing ten registered conditions')
    totals={a:Counter() for a in ARMS}
    byseed={s:{a:Counter() for a in ARMS} for s in (7,11,23,37,53)}
    first_stable_b={a:Counter() for a in ARMS}
    stationary_payoffs={a:Counter() for a in ('source_temporal','sensor_neutral','v6_frozen')}
    for r in reports:
        for arm in ARMS:
            totals[arm].update({k:r['arms'][arm].get(k,0) for k in (
                'brier_sum','belief_cases','utility_sum','action_count',
                'optimal_actions','queries','wrong_confident','new_parent_sentinel_confident_wrong')})
            byseed[r['seed']][arm].update({k:r['arms'][arm][k]
                for k in ('utility_sum','action_count')})
        if r['seed'] in (7,11):
            for arm in stationary_payoffs:
                stationary_payoffs[arm]['nll_sum']+=r['payoff'][arm]['total']['nll_sum']
                stationary_payoffs[arm]['n']+=r['payoff'][arm]['total']['n']
                stratum=r['subgroups']['stable_B'][arm]
                first_stable_b[arm]['brier_sum']+=stratum['mid_local_brier_sum']
                first_stable_b[arm]['n']+=stratum['mid_local_n']
    c=totals['source_temporal'];v=totals['v6_frozen'];r=totals['rule_smoothed'];s=totals['sensor_neutral']
    gates={
        'stationary_payoff_nll_improved':
            stationary_payoffs['source_temporal']['nll_sum'] <
            stationary_payoffs['v6_frozen']['nll_sum'],
        'stationary_nll_vs_physics_matched_two_scalar':
            stationary_payoffs['source_temporal']['nll_sum'] <
            stationary_payoffs['sensor_neutral']['nll_sum'],
        'stationary_stable_B_first_brier_improved':
            first_stable_b['source_temporal']['n']>0 and
            first_stable_b['source_temporal']['brier_sum'] <
            first_stable_b['v6_frozen']['brier_sum'],
        'stable_B_brier_vs_physics_matched_two_scalar':
            first_stable_b['source_temporal']['brier_sum'] <
            first_stable_b['sensor_neutral']['brier_sum'],
        'overall_brier_vs_calibrated_rule':
            c['brier_sum']/c['belief_cases'] <=
            r['brier_sum']/r['belief_cases']+1e-12,
        'net_vs_all_controls':c['utility_sum']+1e-12>=
            max(v['utility_sum'],r['utility_sum'],s['utility_sum']),
        'query_budget_vs_frozen_v6':c['queries']<=v['queries'],
        'optimal_actions_vs_frozen_v6':
            c['optimal_actions']>=v['optimal_actions'],
        'zero_new_parent_sentinel_confident_errors':
            c['new_parent_sentinel_confident_wrong']==0,
        'worst_seed_nonregression':
            all(byseed[s]['source_temporal']['utility_sum']+1e-12>=
                max(byseed[s]['v6_frozen']['utility_sum'],
                    byseed[s]['rule_smoothed']['utility_sum'],
                    byseed[s]['sensor_neutral']['utility_sum'])
                for s in byseed)
    }
    return {'version':'g5-v7-prespecified-decision','worlds':1920,
        'measurements_correlated_five_views':9600,
        'gates':gates,
        'decision':('KEEP_SOURCE_V7_DEVELOPMENT' if all(gates.values())
                    else 'REVISE_SOURCE_V7'),
        'g5_scientific_admission':False,
        'means':{a:{'brier':d['brier_sum']/d['belief_cases'],
                    'net_per_action':d['utility_sum']/d['action_count'],
                    'queries':d['queries'],
                    'optimal_action_rate':d['optimal_actions']/d['action_count'],
                    'new_retention_confident_wrong':
                        d['new_parent_sentinel_confident_wrong']}
                 for a,d in totals.items()},
        'per_seed_net_action':{str(s):{a:d['utility_sum']/d['action_count']
                                for a,d in byarm.items()}
                               for s,byarm in byseed.items()},
        'stationary_nll':{a:d['nll_sum']/d['n']
                          for a,d in stationary_payoffs.items()},
        'stationary_stable_B_mid_brier':{a:d['brier_sum']/d['n']
                                       for a,d in first_stable_b.items() if d['n']},
        'limitations':'same-team challenge over previously opened G3 physical menus'}
