"""Standalone saved-record checker for matched-conflict-v1. No study module imports."""
from collections import Counter, defaultdict
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace
import argparse
import json
import lzma
import math
import subprocess

import numpy as np


LAWS = ('nand', 'nor')
SEEDS = (7, 11, 23, 37, 53)
ARMS = ('learned', 'empirical', 'crossed', 'fixed0', 'fixed1', 'blind', 'free_silent', 'suppressed', 'shuffled')
FEES = (5, 75, None)


def digest(v):
    return sha256(json.dumps(v, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def read(p):
    return json.loads(lzma.decompress(p.read_bytes()) if p.suffix == '.xz' else p.read_bytes())


def argmax(u):
    return int(u[1] > u[0])


def enumerate_cases(bank, matrices, law, split):
    result = []
    for i, p in enumerate(sorted(bank['sites'])):
        source = [digest(['g4-conflict-source-v1', split, p, s]) for s in (0, 1)]
        for ordinal in range(512):
            site, probe, c0, c1, t0, t1, reg, sr, tr = [int(x) for x in f'{ordinal:09b}']
            start, end = bank['sites'][p][::1 if site == 0 else -1]
            a, b = matrices[p][::1 if site == 0 else -1]
            ca, cb = [c0,c1], [t0,t1]
            outcome = start['rewards'][ca[reg]][probe]
            claims = list(zip(source,ca))[::1 if sr == 0 else -1]
            later = list(zip(source,cb))[::1 if tr == 0 else -1]
            public = digest([start['texts'],end['texts'],[a,claims,probe,outcome,b,later]])
            key = digest(['g4-conflict-v1',law,split,p,site,probe,ca,cb,reg,sr,tr])
            bits = (cb[reg], cb[1-reg])
            payoff = [end['rewards'][k] for k in bits]
            for goal, paid in zip(bits,payoff):
                assert sorted(paid)==[0,1] and argmax(paid) == argmax(b[goal])
            # Calculate calibration evidence via source0's and source1's payoff likelihoods.
            likelihood = [a[bit][probe] if outcome else 1 - a[bit][probe] for bit in ca]
            distance = likelihood[1] - likelihood[0]
            target = (b[t0][tr], b[t1][tr])
            donor_index = 512*i + int(''.join(map(str,[site,probe,c0,c1,t0^sr,t1^sr,reg,sr,1-tr])),2)
            result.append(SimpleNamespace(key=key, pub=public, probe=probe, y=outcome, sel=tr,
                m=b, distance=distance, target=target, bits=bits, rewards=payoff, cb=cb, ca=ca,
                supports=tuple(int(argmax(a[v]) == probe) == outcome for v in ca),
                informative=c0!=c1, conflict=t0!=t1, donor_index=donor_index))
    assert len(result)==len({r.key for r in result})==6144
    return result


def refit(records, observed, cp):
    for r, owner in zip(records,observed,strict=True):
        assert owner == [r.key,r.pub,r.probe,r.y,r.sel,*[v[r.sel] for v in r.rewards]]
    x=np.array([r.distance for r in records])
    lo,hi=np.array([r.target for r in records]).T
    error=0.
    for env, state in enumerate(cp):
        y=np.array([v[5+env] for v in observed])
        # Dense unaggregated float64 batches and alternate algebra; native fit compresses identical rows.
        w=0.
        for _ in range(128):
            g=1/(1+np.exp(-w*x))
            score=hi*g+lo*(1-g)
            safe=np.clip(score,1e-12,1-1e-12)
            update=(y-score)/(safe*(1-safe))*(hi-lo)*x*g*(1-g)
            w=min(16.,max(-16.,w+4*np.mean(update)))
        hard=(np.sign(x)+1)/2
        predictions=[a*hi+(1-a)*lo for a in (hard,1-hard)]
        sse=[np.square(v-y).sum() for v in predictions]
        sign=1 if sse[0]<=sse[1] else -1
        error=max(error,abs(state['neural']-w))
        assert error<1e-10 and sign == state['empirical']
    return error


def expected_probabilities(r, cp, env):
    def reading(w, hard=False):
        z=w*r.distance
        q=(.5 if z==0 else int(z>0)) if hard else 1/(1+math.exp(-z))
        return (1-q)*r.cb[0]+q*r.cb[1]
    weak=[]
    for j in (0,1):
        q=(2/3 if r.supports[j] else 0.)
        q=q if cp[env]['empirical']>0 else 1-q
        weak.append(q*r.cb[j]+(1-q)/2)
    p=reading(cp[env]['neural'])
    return [p, reading(cp[env]['empirical'],True), reading(cp[1-env]['neural']),
            *weak,sum(r.cb)/2,.5,p,p]


def replay(rows, archive, cp, decisions=None):
    agg=defaultdict(Counter)
    gate=Counter()
    equal=0
    seen={}
    for idx,(r,row) in enumerate(zip(rows,archive,strict=True)):
        assert len(row)==4 and row[:2]==[r.key,r.pub]
        donor=rows[r.donor_index]
        assert donor.donor_index==idx and donor.key!=r.key
        for env in (0,1):
            truth=r.bits[env]
            physical=r.rewards[env]
            expected=expected_probabilities(r,cp,env)
            cells=row[2+env]
            assert len(cells)==len(ARMS)
            signature=[]
            for k,(name,cell,p) in enumerate(zip(ARMS,cells,expected,strict=True)):
                assert len(cell)==5 and math.isfinite(cell[0]) and abs(p-cell[0])<1e-10
                # Unlike policy/scorer, expected p uses physical creation order. Use saved p for
                # arithmetic when comparing exact ties so source-order rounding cannot alter a tie.
                p=cell[0]
                v=[(1-p)*a+p*b for a,b in zip(*r.m,strict=True)]
                pre=argmax(v)
                assert type(cell[1]) is int and pre==cell[1]
                vo=((1-p)*max(r.m[0])+p*max(r.m[1]))-max(v)
                a=agg[env,name]
                a['pre']+=physical[pre]
                a['brier']+=(p-truth)**2
                decision_bits=[pre]
                for j,fee in enumerate(FEES):
                    ask=fee is not None and name!='free_silent' and vo>fee/100
                    selection=pre
                    if ask and name!='suppressed':
                        bit=donor.bits[env] if name=='shuffled' else truth
                        selection=argmax(r.m[bit])
                    code=cell[2+j]
                    assert type(code) is int and code==2*ask+selection
                    a['request',j]+=int(ask)
                    a['success',j]+=physical[selection]
                    a['net',j]+=100*physical[selection]-(fee or 0)*int(ask)
                    decision_bits.append(int(ask))
                signature.extend(decision_bits)
            # Different latent regimes may have identical visible evidence. No queried value may
            # change ask/pre-action decisions when that evidence and fee are fixed.
            key=r.pub,env
            if key in seen:
                assert seen[key]==signature
                equal+=1
            seen[key]=signature
            if r.informative and r.conflict:
                gate['critical']+=1
                gate['critical_correct']+=physical[cells[0][1]]
                gate['critical_crossed']+=physical[cells[2][1]]
            elif r.conflict:
                gate['ambiguous']+=1
                gate['ambiguous_correct']+=physical[cells[0][1]]
                assert cells[0][0]==.5
        if r.informative and r.conflict:
            gate['twins']+=1
            gate['twin_hits']+=all(r.rewards[c][row[c+2][0][1]] for c in (0,1))
    if decisions is not None:
        assert gate['twins']==decisions['twin_count'] and gate['twin_hits']==decisions['twin_hits']
        for e,c in enumerate(decisions['conventions']):
            for arm,metrics in c['arms'].items():
                got=agg[e,arm]
                assert got['pre']==metrics['pre_successes']
                assert math.isclose(got['brier']/len(rows),metrics['bit_brier'],abs_tol=1e-12)
                for j,m in enumerate(metrics['fees']):
                    assert [got['request',j],got['success',j],got['net',j]]==[
                        m['requests'],m['successes'],m['net_hundredths']]
    return agg,gate,equal


def main(repo,stage):
    base=repo/'experiments/predictive_nucleus'
    result=base/'results/matched-conflict-v1'
    excluded={'attempt.json','receipt.json'}
    stages=['fit','raw','scored'][:{'fit':1,'raw':2,'scored':3}[stage]]
    receipt_count=0
    for s in stages:
        folder=result/s
        sealed=read(folder/'receipt.json')
        assert sealed['status']=='complete'
        hashes={p.name:sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.name not in excluded}
        assert hashes==sealed['outputs']
        receipt_count+=len(hashes)
    decision=read(result/'scored/decision.json') if stage=='scored' else None
    totals=Counter(verified_outputs=receipt_count)
    frozen=read(base/'matched_conflict_v1.json')
    assert all(sha256((base/k).read_bytes()).hexdigest()==v for k,v in frozen['sources'].items())
    # Compare prior-stage bytes to the exact Git tree the next stage declared as input.
    previous=read(result/'fit/attempt.json')['parent']
    assert subprocess.check_output(['git','-C',repo,'rev-parse',previous+'^'],text=True).strip()==frozen['base']
    for prev,current in zip(stages,stages[1:]):
        head=read(result/current/'attempt.json')['parent']
        assert subprocess.check_output(['git','-C',repo,'rev-parse',head+'^'],text=True).strip()==previous
        for file in sorted((result/prev).iterdir()):
            payload=subprocess.check_output(['git','-C',repo,'show',f'{head}:{file.relative_to(repo)}'])
            assert payload==file.read_bytes()
            totals['git_stage_files']+=1
        previous=head
    maximum_fit_error=0.
    t=defaultdict(Counter)
    distinct=set()
    for law in LAWS:
        native={}
        for split in (['train','challenge'] if stage!='fit' else ['train']):
            f=base/f'data/sender-v1/{law}-{split}-pairs.json.xz'
            assert sha256(f.read_bytes()).hexdigest()==read(base/'sender_freeze_v1.json')['hashes'][str(f.relative_to(repo))]
            native[split]=read(f)
        if stage!='fit':
            # Direct verification against physical endpoint tapes, including IDs of the earlier witness.
            g3=base/'data/effect-role-v3'
            inputs=g3/f'{law}-inputs.json.xz'
            assert sha256(inputs.read_bytes()).hexdigest()==read(g3/'freeze.json')['artifacts'][inputs.name]['sha256']
            tapes={r['id']:r for r in read(inputs)['episodes']}
            for bank in native.values():
                for pair in bank['sites'].values():
                    for site in pair:
                        for bit,actions in enumerate(site['episodes']):
                            for action,key in enumerate(actions):
                                ep=tapes[key]; events=ep['utterances']
                                before=list(events[-2]['reading'] if len(events)>1 else ep['context'][-1]['reading'])
                                for i,want in zip(site['participants'],site['goal'],strict=True): before[i]=want
                                assert ep['entities']==site['entities'] and ep['context'][0]['reading'][0]==bit
                                assert events[-1]['text']==site['texts'][action]
                                assert int(events[-1]['reading']==before)==site['rewards'][bit][action]
                                totals['physical_tape_site_action_checks']+=1
        train_live=read(result/f'fit/{law}-matrices.json')
        assert digest(train_live)==read(result/f'fit/{law}-live.json')['forecast_sha256']
        raw_live={}
        for seed in SEEDS:
            name=f'{law}-{seed}'
            cp=read(result/f'fit/{name}.json')
            train=enumerate_cases(native['train'],train_live[str(seed)],law,'train')
            maximum_fit_error=max(maximum_fit_error,refit(train,read(result/f'fit/{name}-feedback.json.xz'),cp))
            totals['fits_each_kind']+=2
            totals['chosen_train_target_rewards']+=len(train)*2
            totals['probe_outcomes_train']+=len(train)
            if stage=='fit':continue
            saved=read(result/f'raw/{name}.json.xz')
            raw_live[str(seed)]=saved['live_matrices']
            held=enumerate_cases(native['challenge'],saved['live_matrices'],law,'challenge')
            distinct.update(r.key for r in held)
            agg,gate,equal=replay(held,saved['rows'],cp,decision['conditions'][name] if decision else None)
            for (_,arm),counts in agg.items():
                t[arm]+=counts
            totals.update(gate)
            totals['raw_scenarios']+=len(held)
            totals['unassisted_arm_choices']+=len(held)*2*len(ARMS)
            totals['fee_specific_arm_actions']+=len(held)*2*len(ARMS)*len(FEES)
            totals['identical_visible_rechecks']+=equal
        if stage!='fit':
            assert digest(raw_live)==read(result/f'raw/{law}-live.json')['forecast_sha256']
    arms={n:{'pre_correct':c['pre'],'fees':[{'q':c['request',j],'gross':c['success',j],
         'net_hundredths':c['net',j]} for j in range(3)]} for n,c in t.items()}
    return dict(stage=stage,counts=totals,arms=arms,unique_held_case_ids=len(distinct),
                max_abs_fit_error=maximum_fit_error,checker_sha256=sha256(Path(__file__).read_bytes()).hexdigest())


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo',type=Path)
    parser.add_argument('--stage',choices=('fit','raw','scored'),default='scored')
    args=parser.parse_args()
    print(json.dumps(main(args.repo.resolve(),args.stage),indent=2,sort_keys=True))
