"""Freeze, fit, collect, then independently score a one-bit two-agent channel."""
import argparse
from itertools import product
from time import perf_counter_ns

from . import continuation_run as io, sender_task as task
from .acceptance_contract import digest, require
from .sender_policy import Requester, Sender, values
from .sender_stage import DATA, RESULTS, freeze, stage

LAWS = ('nand', 'nor')
ARMS = ('delivered', 'silent', 'random', 'shuffled', 'fixed0', 'fixed1', 'action_code',
        'free_silent', 'public_router')


def donor_bits(r):
    site = r['tags'].index(r['goal'])
    return tuple(b ^ int(i != site or (r['rep'] >= 2 and r['stratum'] != 'known'))
                 for i, b in enumerate(r['bits']))


def target(r):
    held = {k: r[k] for k in ('id', 'pair_id', 'goal_pair', 'bits', 'tags', 'goal', 'source',
                               'source_group', 'stratum', 'rep', 'cost', 'rewards', 'local',
                               'witness_ids', 'menu_reversed')}
    held['donor'] = task.round_id(r['pair_id'], donor_bits(r), r['tags'], r['goal'], r['source'],
                                 r['stratum'], r['rep'])
    held['random_bit'] = int(digest(['g4-sender-random-v1', r['id']])[:16], 16) % 2
    return held


def prepare():
    DATA.mkdir(exist_ok=False)
    for law, split in product(LAWS, ('train', 'challenge')):
        bank = task.pairs(law, io.SEEDS[0], split)
        entries = {task.pair_id(pair, law, split): [{k: site[k] for k in
                   ('id', 'lineage', 'family', 'entities', 'goal', 'episodes', 'texts', 'actions',
                    'participants', 'witness', 'rewards')} for site in pair] for pair in bank}
        forecasts = {}
        for seed in io.SEEDS:
            pairs = bank if seed == io.SEEDS[0] else task.pairs(law, seed, split)
            forecasts[str(seed)] = {task.pair_id(pair, law, split): [s['predicted'] for s in pair] for pair in pairs}
            require(forecasts[str(seed)].keys() == entries.keys(), 'pair membership depends on model seed')
        io._write(DATA / f'{law}-{split}-pairs.json.xz', dict(sites=entries, forecasts=forecasts))
        targets = [target(r) for pair in bank for r in task.rounds(pair, law, split)]
        require(len(targets) == len({r['id'] for r in targets}) == 4608, 'incomplete designed schedule')
        io._write(DATA / f'{law}-{split}-targets.json.xz', targets)


def fit(law, seed):
    episodes = [r for pair in task.pairs(law, seed, 'train') for r in task.rounds(pair, law, 'train')]
    sender_samples, requester_samples, feedback = [], [], []
    for r in episodes:
        if r['rep'] >= 2:
            continue
        bit = r['rep'] ^ (int(r['pair_id'][:8], 16) % 2) ^ int(r['source_group'] == 'crossed')
        q = values(r['prior'], r['matrix'], r['local'], bit)
        a = int(q[1] > q[0])
        reward = r['rewards'][a]
        sender_samples.append((r['tags'], r['goal'], r['bits'], bit, reward))
        feedback.append([r['id'], True, bit, a, reward])
    sender = Sender.fit(sender_samples)
    for r in episodes:
        if r['rep'] < 2:
            continue
        asked = (r['rep'] + int(r['pair_id'][8:16], 16) + int(r['source_group'] == 'crossed')) % 2 == 0
        bit = sender.send(r['tags'], r['goal'], r['bits']) if asked else None
        q = values(r['prior'], r['matrix'], r['local'], bit)
        a = int(q[1] > q[0])
        reward = r['rewards'][a]
        requester_samples.append((r['prior'], asked, reward))
        feedback.append([r['id'], asked, bit, a, reward])
    targets = io._read(DATA / f'{law}-train-targets.json.xz')
    require(len(feedback) == len(targets) and {f[0] for f in feedback} == {r['id'] for r in targets},
            'training budget differs')
    return dict(sender=sender.to_dict(), requester=Requester.fit(requester_samples).to_dict()), feedback


def claim(law, seed, r, token):
    return digest(['g4-sender-claim-v1', law, seed, r['pair_id'], r['id'], r['source'], 1,
                   list(r['witness_ids']), token])


def decisions(law, seed, r, sender, requester, scheduled, donor):
    p = r['prior']
    asked = requester.ask(p, r['cost'])
    emitted = sender.send(r['tags'], r['goal'], r['bits'])
    source_claim = claim(law, seed, r, emitted)
    choices = {}
    for arm in ARMS:
        paid = asked and arm != 'free_silent'
        bit = None
        if paid:
            if arm in ('delivered', 'action_code'):
                bit = emitted
            elif arm == 'shuffled':
                bit = sender.send(donor['tags'], donor['goal'], donor['bits'])
            elif arm == 'random':
                bit = scheduled['random_bit']
            elif arm in ('fixed0', 'fixed1'):
                bit = r['bits'][int(arm[-1])]
            elif arm == 'public_router':
                bit = r['bits'][r['tags'].index(r['goal'])]
        q = ((1 - bit, bit) if arm == 'action_code' and bit is not None and r['local'] is None
             else values(p, r['matrix'], r['local'], bit))
        origin = None
        if bit is not None:
            if arm in ('delivered', 'action_code'):
                origin = source_claim
            elif arm == 'shuffled':
                origin = claim(law, seed, donor, bit)
            else:
                origin = digest(['g4-sender-intervention-v1', arm, r['id'], bit])
        choices[arm] = dict(asked=paid, origin=origin, token=bit, action=int(q[1] > q[0]), values=list(q), steps=1)
    return dict(id=r['id'], pair_id=r['pair_id'], emitted=emitted, claim_id=source_claim, prior=list(p),
                matrix=r['matrix'], local=r['local'], arms=choices)


def collect(law, seed, out, checkpoint):
    sender = Sender.from_dict(checkpoint['sender'])
    requester = Requester.from_dict(checkpoint['requester'])
    targets = {t['id']: t for t in io._read(DATA / f'{law}-challenge-targets.json.xz')}
    records = []
    for pair in task.pairs(law, seed, 'challenge'):
        group = {r['id']: r for r in task.rounds(pair, law, 'challenge')}
        for r in group.values():
            scheduled = targets[r['id']]
            begin = perf_counter_ns()
            row = decisions(law, seed, r, sender, requester, scheduled, group[scheduled['donor']])
            records.append(dict(row, law=law, seed=seed, decision_ns=perf_counter_ns()-begin))
    io._write(out / f'{law}-{seed}.json.xz', records)


def targets_for(law, seed):
    catalogue = io._read(DATA / f'{law}-challenge-pairs.json.xz')
    for t in io._read(DATA / f'{law}-challenge-targets.json.xz'):
        site = t['tags'].index(t['goal'])
        pair = t['pair_id']
        source = catalogue['sites'][pair]
        matrix = catalogue['forecasts'][str(seed)][pair][site]
        order = (1, 0) if t['menu_reversed'] else (0, 1)
        require(t['witness_ids'] == [s['witness'][b]['id'] for s,b in zip(source, t['bits'], strict=True)]
                and t['rewards'] == [source[site]['rewards'][t['bits'][site]][a] for a in order],
                'published target and physical receipt disagree')
        yield dict(t, matrix=[[row[a] for a in order] for row in matrix])


def run(name):
    if name == 'prepare':
        prepare()
        freeze()
        return
    from . import sender_receiver_ablation as ablation, sender_scoring as scoring
    with stage(name) as out:
        reports, ablated = [], []
        for law, seed in product(LAWS, io.SEEDS):
            key = f'{law}-{seed}'
            if name == 'fit':
                cp, feedback = fit(law, seed)
                cp['receiver_ablation'] = ablation.fit_ablation(law, seed)
                io._write(out / (key + '.json'), cp)
                io._write(out / (key + '-feedback.json.xz'), feedback)
            elif name == 'raw':
                cp = io._read(RESULTS / 'fit' / (key + '.json'))
                collect(law, seed, out, cp)
                rows = ablation.collect_ablation(law, seed, cp['receiver_ablation'])
                io._write(out / (key + '-ablation.json.xz'), rows)
            else:
                rows = io._read(RESULTS / 'raw' / (key + '.json.xz'))
                reports.append(scoring.score_condition(rows, targets_for(law, seed), law, seed))
                ablated.extend(io._read(RESULTS / 'raw' / (key + '-ablation.json.xz')))
        if name == 'scored':
            io._write(out / 'decision.json', scoring.decision(reports))
            io._write(out / 'receiver-ablation.json', ablation.score_ablation(ablated))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'fit', 'raw', 'scored'))
    run(parser.parse_args().stage)
