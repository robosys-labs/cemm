"""Execute the prospective transfer study from a published source, fit and raw chain."""
import argparse
from collections import defaultdict
from itertools import product

from . import continuation_run as io, transfer_task as bank
from .acceptance_contract import digest, require
from .sender_policy import Requester, Sender, values
from .transfer_protocol import BASE, FREEZE, RESULT, STAGES, implementation, runtime, signature, stage
from .transfer_sender import ExactLookup, SharedSender, legacy_send, raw_dot

LAWS = ('nand','nor')
ARMS = ('delivered','silent','random','shuffled','lookup','legacy','raw_dot','free_silent','public_router','margin')


def prepare():
    require(io._git('rev-parse','HEAD') == BASE and not RESULT.exists(), 'wrong parent or outputs exist')
    spec = dict(base=BASE, runtime=runtime(), implementation=implementation(),
                audit={law:bank.split_audit(law) for law in LAWS}, banks={})
    for law, seed, split in product(LAWS, io.SEEDS, ('train','challenge')):
        spec['banks'][f'{law}/{seed}/{split}'] = signature(bank.rounds(law, seed, split))
    io._write(FREEZE, spec)


def inputs(law, seed, split):
    rows = list(bank.rounds(law, seed, split))
    expected = io._read(FREEZE)['banks'][f'{law}/{seed}/{split}']
    require(signature(rows) == expected and len(rows) == len({r['id'] for r in rows}) == 6144,
            'registered input sequence differs')
    return rows


def request_key(prior):
    return min(3,int(4*abs(prior[0]-prior[1]))), min(3,int(4*max(prior)))


def execute(r, token):
    q = values(r['prior'],r['matrix'],r['local'],token)
    return int(q[1] > q[0])


def fit(rows, law, seed):
    samples, feedback = [], []
    for r in rows:
        if r['rep'] < 2:
            bit = r['rep'] ^ (int(r['pair_id'][:8],16) % 2)
            a = execute(r,bit)
            reward = r['rewards'][a]
            samples.append((r['sites'],r['goal'],r['bits'],bit,reward))
            feedback.append([r['id'],True,bit,a,reward])
    shared, lookup = SharedSender.fit(samples), ExactLookup.fit(samples)
    means, margin_samples = defaultdict(lambda:[0,0]), []
    for r in rows:
        if r['rep'] >= 2:
            asked = (r['rep'] + int(r['pair_id'][8:16],16)) % 2 == 0
            bit = shared.send(r['sites'],r['goal'],r['bits']) if asked else None
            a = execute(r,bit)
            reward = r['rewards'][a]
            feedback.append([r['id'],asked,bit,a,reward])
            margin_samples.append((r['prior'],asked,reward))
            stat = means[request_key(r['prior']),asked]
            stat[0] += reward
            stat[1] += 1
    gains = []
    for key in sorted({k for k,_ in means}):
        (paid,pn),(silent,sn) = means[key,True],means[key,False]
        require(pn == sn and pn, 'unbalanced request exploration')
        gains.append([*key,paid/pn - silent/sn])
    legacy = io._read(io.ROOT / 'results/sender-v1/fit' / f'{law}-{seed}.json')['sender']
    return dict(shared=shared.to_dict(),lookup=lookup.to_dict(),request={'gains':gains},
                margin=Requester.fit(margin_samples).to_dict(),legacy=legacy), feedback


def collect(rows, law, seed, cp):
    shared = SharedSender.from_dict(cp['shared'])
    lookup, legacy = ExactLookup.from_dict(cp['lookup']), Sender.from_dict(cp['legacy'])
    request = {tuple(r[:2]):r[2] for r in cp['request']['gains']}
    margin = Requester.from_dict(cp['margin'])
    claims = {}
    for r in rows:
        emitted = shared.send(r['sites'],r['goal'],r['bits'])
        claim = digest(['g4-transfer-claim-v1',law,seed,r['id'],r['source'],1,r['witness_ids'],emitted])
        claims[r['id']] = emitted,claim
    for r in rows:
        asked = request.get(request_key(r['prior']),0.) > r['cost']
        other = margin.ask(r['prior'],r['cost'])
        emitted, claim = claims[r['id']]
        donor_bit, donor_claim = claims[r['donor']]
        visible = r['sites'],r['goal'],r['bits']
        tokens = (emitted,None,r['random_bit'],donor_bit,lookup.send(*visible),legacy_send(legacy,*visible),
                  raw_dot(*visible),None,r['bits'][r['badge_ids'].index(r['goal_id'])],emitted)
        arms = {}
        for arm,bit in zip(ARMS,tokens,strict=True):
            paid = other if arm == 'margin' else asked and arm != 'free_silent'
            wire = bit if paid else None
            origin = None
            if wire is not None:
                if arm in ('delivered','margin'):
                    origin = claim
                elif arm == 'shuffled':
                    origin = donor_claim
                else:
                    origin = digest(['g4-transfer-control-v1',arm,r['id'],wire])
            arms[arm] = dict(token=wire,origin=origin,action=execute(r,wire))
        yield dict(id=r['id'],emitted=emitted,claim_id=claim,asked=asked,margin_asked=other,arms=arms)


def run(name):
    if name == 'prepare':
        prepare()
        return
    from . import transfer_score as scorer
    with stage(name) as out:
        reports = []
        for law,seed in product(LAWS,io.SEEDS):
            key = f'{law}-{seed}'
            rows = inputs(law,seed,'train' if name == 'fit' else 'challenge')
            if name == 'fit':
                checkpoint,feedback = fit(rows,law,seed)
                io._write(out/(key+'.json'),checkpoint)
                io._write(out/(key+'-feedback.json.xz'),feedback)
            else:
                checkpoint = io._read(RESULT/'fit'/(key+'.json'))
                if name == 'raw':
                    io._write(out/(key+'.json.xz'),list(collect(rows,law,seed,checkpoint)))
                else:
                    raw = io._read(RESULT/'raw'/(key+'.json.xz'))
                    reports.append(scorer.score_condition(raw,rows,law,seed,checkpoint))
        if name == 'scored':
            io._write(out/'decision.json',scorer.decision(reports))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare',*STAGES))
    run(parser.parse_args().stage)
