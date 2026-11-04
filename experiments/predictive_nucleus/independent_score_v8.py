"""Evaluator-only G5 v8 scorer: read sealed forecasts, never fit or replay policy.

All 1,920 paired episodes and ten predetermined environments count.
Actual meanings/modes are used ONLY after raw forecast sealing.
"""
from collections import Counter,defaultdict
from math import log,isfinite
import json
from .independent_task_v8 import inventory,REGIME
from .independent_collection_v8 import ARMS,VIEWS
from .temporal_audit_v5 import record_digest
from .goal_policy_v6 import choose,after_answer,public_task

def _valid(p):
    if type(p) not in (int,float) or not isfinite(p) or not 0<=p<=1:
        raise ValueError('invalid sealed belief or payoff probability')
    return p

def _wrong(p,y):
    return (p>=.95 and y==0) or (p<=.05 and y==1)

def _proper(p,y):
    return (p-y)**2,-log(max(p if y else 1-p,1e-12))

def _new_count(candidate,control,y):
    return int(_wrong(candidate,y) and not _wrong(control,y))

def score(raw,law,seed,bank):
    if (raw.get('version'),raw.get('split'),raw.get('law'),raw.get('seed'),
            tuple(raw.get('parameters',())))!=(
            'g5-v8-raw','challenge',law,seed,(.15,.03,.2,32)):
        raise ValueError('wrong sealed v8 bank or modified candidate')
    source=inventory(law,seed,'challenge',bank)
    rows=raw['rows']
    if len(rows)!=len(source) or len(rows)!=192:
        raise ValueError('missing raw/evaluator worlds')
    metric={arm:Counter() for arm in ARMS}
    byview={v:{arm:Counter() for arm in ARMS} for v in VIEWS}
    strata=defaultdict(lambda:{arm:Counter() for arm in ARMS})
    questions={arm:Counter() for arm in ARMS}
    payoff={arm:{src:Counter() for src in ('A','B')} for arm in ('joint','frozen_v7','neutral')}
    pair_count=0
    pre_confident=0
    mode=Counter()
    overlap=Counter()
    adverse=[]
    id_set=set()
    for ep,row in zip(source,rows,strict=True):
        if (ep.uid!=row['id'] or ep.uid in id_set or
            row['record_hash']!=record_digest(ep.records)
            or row['pre_record_hash']!=record_digest(ep.records[:12])
            or ep.lineage!=row['lineage']
            or list(ep.observed_sources)!=list(row['source_ids'])):
            raise ValueError('mutated or incomplete raw evidence')
        id_set.add(ep.uid)
        expected=public_task(ep.uid)
        if (row['goals']!=json.loads(json.dumps(expected[:2])) or
            row['fee']!=expected[2] or len(row['beliefs'])!=5):
            raise ValueError('goal or belief changed after collection')
        for p in (row['pre_post_meaning_p'],row['trust_pre_p'],
                  row['trust_mid_p'],row['trust_final_p']):
            _valid(p)
        mode['n']+=1
        b,n=_proper(row['trust_final_p'],ep.source_modes[1])
        mode['final_brier_sum']+=b
        mode['final_nll_sum']+=n
        mode['correct_mode_map']+=int(row['trust_final_p']>=.5)==ep.source_modes[1]
        mode['true_switch']+=ep.source_modes[0]!=ep.source_modes[1]
        yvalues=(ep.truth[3],ep.truth[3],ep.truth[1],ep.truth[0],ep.truth[4])
        group=('flip' if ep.flip else 'stable')+'_'+ep.observed_sources[12]
        for vi,(v,cell,y) in enumerate(zip(VIEWS,row['beliefs'],yvalues,strict=True)):
            if len(cell)!=4:
                raise ValueError('missing model forecasts')
            for index,arm in enumerate(ARMS):
                p=_valid(cell[index])
                b,n=_proper(p,y)
                z=metric[arm];z['belief_cases']+=1
                z['brier_sum']+=b;z['meaning_nll_sum']+=n
                z['wrong_confident']+=_wrong(p,y)
                vstats=byview[v][arm]
                vstats['n']+=1;vstats['brier_sum']+=b
                vstats['wrong_confident']+=_wrong(p,y)
                part=strata[group][arm]
                if vi in (0,1):
                    part[v+'_n']+=1;part[v+'_brier_sum']+=b
                if vi in (3,4) and arm=='joint':
                    z['new_retained_confident_wrong']+=_new_count(
                        p,cell[2],y)
        physical=(r for r in ep.records if r.physical)
        for r,j,v,n in zip(physical,row['payoff_p'],row['v7_payoff_p'],
                           row['neutral_payoff_p'],strict=True):
            if r.source not in ('sensor-A','sensor-B'):
                raise ValueError('invalid source label')
            for arm,p in (('joint',j),('frozen_v7',v),('neutral',n)):
                b,loss=_proper(_valid(p),r.outcome)
                cell=payoff[arm][r.source[-1]]
                cell['n']+=1;cell['brier_sum']+=b;cell['nll_sum']+=loss
        go0,go1,fee=expected
        truth=ep.truth[3]
        choices={}
        for i,arm in enumerate(ARMS):
            mid,final=(_valid(row['beliefs'][j][i]) for j in (0,1))
            first=choose(mid,go0,fee)
            second=choose(final,go1,None)
            ask=first['ask']
            if ask and (fee is None or fee>=.75):
                raise ValueError('invalid purchased question')
            if ask:
                actions=(after_answer(go0,truth),after_answer(go1,truth))
            else:
                actions=(first['action'],second['action'])
            earned=sum(expected[j][truth][actions[j]] for j in (0,1))
            optimal=sum(max(expected[j][truth]) for j in (0,1))
            correct=sum(abs(expected[j][truth][actions[j]]-
                            max(expected[j][truth]))<1e-12 for j in (0,1))
            net=earned-(fee if ask else 0.)
            z=metric[arm];z['episodes']+=1;z['action_count']+=2
            z['utility_sum']+=net;z['gross_regret_sum']+=optimal-earned
            z['optimal_actions']+=correct;z['queries']+=int(ask)
            z['question_cost_sum']+=(fee if ask else 0.)
            x=strata[group][arm];x['n']+=1;x['net_sum']+=net
            if ask:
                # Evaluator-only factual counterfactual, not online VOI.
                no=go0[truth][first['action']]+go1[truth][second['action']]
                q=questions[arm];q['n']+=1
                q['gross_gain_sum']+=earned-no
                q['net_gain_sum']+=earned-no-fee
                q['beneficial']+=earned-no-fee>1e-12
                q['harmful']+=earned-no-fee< -1e-12
            choices[arm]=(ask,net)
        ja,na=choices['joint'][0],choices['neutral'][0]
        overlap['both' if ja and na else 'joint_only' if ja else
                'neutral_only' if na else 'neither']+=1
        delta=choices['joint'][1]-choices['neutral'][1]
        if delta< -1e-9:
            adverse.append({'id':ep.uid,'regime':REGIME[seed],
                'flip':bool(ep.flip),'epoch_source':ep.observed_sources[12],
                'net_delta':delta,'candidate_mid_p':row['beliefs'][0][0],
                'neutral_mid_p':row['beliefs'][0][2]})
    for left,right in zip(rows[::2],rows[1::2],strict=True):
        if (left['pre_record_hash']!=right['pre_record_hash'] or
            left['pre_post_meaning_p']!=right['pre_post_meaning_p'] or
            left['trust_pre_p']!=right['trust_pre_p'] or
            left['id']==right['id']):
            raise ValueError('matched latent twins disclosed before epoch')
        pair_count+=1
        pre_confident+=left['pre_post_meaning_p']>=.95 or left['pre_post_meaning_p']<=.05
    if len(id_set)!=192 or pair_count!=96 or sum(
        x['n'] for x in payoff['joint'].values())!=2880:
        raise ValueError('incomplete paired source/mode bank')
    for arm,z in metric.items():
        z.setdefault('new_retained_confident_wrong',0)
        z.setdefault('queries',0)
        z.setdefault('wrong_confident',0)
        z['mean_brier']=z['brier_sum']/z['belief_cases']
        z['mean_meaning_nll']=z['meaning_nll_sum']/z['belief_cases']
        z['net_per_action']=z['utility_sum']/z['action_count']
        z['optimal_rate']=z['optimal_actions']/z['action_count']
    for byarm in byview.values():
        for z in byarm.values():
            z.setdefault('wrong_confident',0)
            z['mean_brier']=z['brier_sum']/z['n']
    for arm,groups in payoff.items():
        total=Counter()
        for z in groups.values():total.update(z)
        total['mean_nll']=total['nll_sum']/total['n']
        total['mean_brier']=total['brier_sum']/total['n']
        groups['total']=total
    return {'law':law,'seed':seed,'regime':REGIME[seed],
        'arms':{a:dict(z) for a,z in metric.items()},
        'views':{v:{a:dict(z) for a,z in groups.items()}
                 for v,groups in byview.items()},
        'source_epoch_subgroups':{k:{a:dict(z) for a,z in groups.items()}
                                 for k,groups in strata.items()},
        'mode':dict(mode),'twin_pairs':pair_count,
        'premature_confident_twin_pairs':pre_confident,
        'question_overlap':dict(overlap),
        'question_value':{a:dict(z) for a,z in questions.items()},
        'payoff':{a:{k:dict(z) for k,z in groups.items()}
                  for a,groups in payoff.items()},
        'adverse_net_cases':adverse}

def assess(reports):
    if len(reports)!=10 or {(r['law'],r['seed']) for r in reports}!={
        (law,s) for law in ('nand','nor') for s in (7,11,23,37,53)}:
        raise ValueError('missing registered conditions')
    totals={arm:Counter() for arm in ARMS}
    seeds={s:{arm:Counter() for arm in ARMS} for s in (7,11,23,37,53)}
    regimes={reg:{arm:Counter() for arm in ARMS} for reg in set(REGIME.values())}
    regime_first={reg:{arm:Counter() for arm in ARMS} for reg in set(REGIME.values())}
    local_flips={arm:Counter() for arm in ARMS}
    pairs=0;premature=0
    mode=Counter()
    for r in reports:
        pairs+=r['twin_pairs'];premature+=r['premature_confident_twin_pairs']
        mode.update({k:r['mode'][k] for k in ('n','final_brier_sum','final_nll_sum','correct_mode_map','true_switch')})
        for arm in ARMS:
            data=r['arms'][arm]
            for dest in (totals[arm],seeds[r['seed']][arm],
                         regimes[r['regime']][arm]):
                dest.update({key:data.get(key,0) for key in (
                    'belief_cases','brier_sum','meaning_nll_sum','episodes',
                    'action_count','optimal_actions','utility_sum','queries',
                    'wrong_confident','new_retained_confident_wrong')})
            first=r['views']['mid_local'][arm]
            regime_first[r['regime']][arm]['brier_sum']+=first['brier_sum']
            regime_first[r['regime']][arm]['n']+=first['n']
            part=r['source_epoch_subgroups']
            for key,groups in part.items():
                if key.startswith('flip_'):
                    z=groups[arm]
                    local_flips[arm]['mid_n']+=z.get('mid_local_n',0)
                    local_flips[arm]['mid_brier_sum']+=z.get('mid_local_brier_sum',0.)
    a=totals['joint'];v=totals['frozen_v7'];n=totals['neutral'];rule=totals['scoped_rule']
    def good(reg,arm,metric):
        z=regimes[reg][arm]
        return z[metric]
    def first_brier(reg,arm):
        z=regime_first[reg][arm]
        return z['brier_sum']/z['n']
    def seed_ok(s):
        x=seeds[s]
        return x['joint']['utility_sum']+1e-12>=max(
            x['neutral']['utility_sum'],x['scoped_rule']['utility_sum'])
    reversed_reg='reversed'
    shifted_reg='within-epoch-source-switch'
    gates={
        'meaning_brier_better_than_temporals':
            a['brier_sum']/a['belief_cases'] <
            min(v['brier_sum']/v['belief_cases'],
                n['brier_sum']/n['belief_cases']),
        'true_flip_first_brier_nonworse':
            local_flips['joint']['mid_brier_sum']<=
            min(local_flips['frozen_v7']['mid_brier_sum'],
                local_flips['neutral']['mid_brier_sum'])+1e-12,
        'reversed_mid_brier_improves':
            first_brier(reversed_reg,'joint')<
            first_brier(reversed_reg,'frozen_v7'),
        'shifted_mid_brier_improves':
            first_brier(shifted_reg,'joint')<
            first_brier(shifted_reg,'frozen_v7'),
        'reversed_utility_improves':
            good(reversed_reg,'joint','utility_sum')>
            good(reversed_reg,'frozen_v7','utility_sum')+1e-12,
        'shifted_utility_improves':
            good(shifted_reg,'joint','utility_sum')>
            good(shifted_reg,'frozen_v7','utility_sum')+1e-12,
        'reversed_shifted_retention_safe':
            all(regimes[reg]['joint']['new_retained_confident_wrong']==0
                for reg in (reversed_reg,shifted_reg)),
        'overall_goal_utility_nonworse':
            a['utility_sum']+1e-12>=max(
                v['utility_sum'],n['utility_sum'],rule['utility_sum']),
        'optimal_actions_nonworse':
            a['optimal_actions']>=n['optimal_actions'],
        'query_budget_nonworse':
            a['queries']<=n['queries'],
        'worst_seed_nonregression':
            all(seed_ok(s) for s in seeds),
        'zero_new_parent_sentinel_errors':
            a['new_retained_confident_wrong']==0,
        'matched_twin_premature_confidence_zero':
            pairs==960 and premature==0
    }
    return {
        'version':'g5-v8-prospective-decision','worlds':1920,
        'matched_twin_pairs':pairs,
        'premature_confident_pairs':premature,
        'correlated_meaning_views':9600,
        'gates':gates,
        'decision':'KEEP_JOINT_V8_DEVELOPMENT' if all(gates.values())
                   else 'REVISE_JOINT_V8',
        'g5_scientific_admission':False,
        'mean':{arm:{
            'meaning_brier':data['brier_sum']/data['belief_cases'],
            'goal_net_per_action':data['utility_sum']/data['action_count'],
            'optimal_action_rate':data['optimal_actions']/data['action_count'],
            'queries':data['queries'],
            'wrong_confident':data['wrong_confident'],
            'new_retained_confident_wrong':
                data['new_retained_confident_wrong']}
            for arm,data in totals.items()},
        'per_seed_goal_net_action':{
            str(s):{arm:val['utility_sum']/val['action_count']
                    for arm,val in group.items()}
            for s,group in seeds.items()},
        'per_regime':{reg:{
            arm:{'meaning_brier':z['brier_sum']/z['belief_cases'],
                 'net_per_action':z['utility_sum']/z['action_count'],
                 'queries':z['queries'],
                 'new_retained_confident_wrong':
                     z['new_retained_confident_wrong']}
            for arm,z in group.items()} for reg,group in regimes.items()},
        'per_regime_first_local_brier':{
            reg:{arm:z['brier_sum']/z['n'] for arm,z in armdata.items()}
            for reg,armdata in regime_first.items()},
        'true_flip_first_brier':{
            arm:z['mid_brier_sum']/z['mid_n']
            for arm,z in local_flips.items()},
        'source_mode_post':{
            'correct_map_rate':mode['correct_mode_map']/mode['n'],
            'mean_brier':mode['final_brier_sum']/mode['n'],
            'mean_nll':mode['final_nll_sum']/mode['n'],
            'true_switch_episodes':mode['true_switch']},
        'limitation':'same-team world and inherited opened physical menus; formal G5 admission false'}
