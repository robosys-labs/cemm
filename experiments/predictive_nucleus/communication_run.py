"""Prepare, fit, collect and score the frozen one-request receiver study."""
import argparse
from dataclasses import asdict
from itertools import chain
from time import perf_counter_ns

from . import acceptance_contract as c, communication_world as world, continuation_run as io
from .communication_exchange import rounds
from .communication_freeze import published_stage, write_json
from .communication_policy import ActionSample, Policy, RequestSample
from .communication_score import score

DATA = io.ROOT / 'data/communication-v1'
RESULT = io.ROOT / 'results/communication-v1'
LAWS = ('nand', 'nor')
FAMILY = {'train': 'path_return4', 'challenge': 'branch_return5'}


def cases(law, seed, split):
    return world.load_cases(law, seed, family=FAMILY[split])


def prepare():
    """Publish independent identities/payoffs and their G3 lineage before any fit."""
    DATA.mkdir(exist_ok=False)
    for law in LAWS:
        banks = {}
        for split in FAMILY:
            bank = cases(law, 7, split)
            banks[split] = {x['id']: {k: x[k] for k in ('lineage', 'family', 'episodes', 'goal', 'texts',
                        'entities', 'participants', 'actions', 'witness')} for x in bank}
            targets = [{'id': r['id'], 'case_id': x['id'], 'stratum': r['stratum'],
                        'cost': r['cost'], 'rewards': list(r['rewards'])}
                       for x in bank for r in rounds(x, law, split)]
            c.require(len({r['id'] for r in targets}) == len(targets), 'duplicate prepared round')
            write_json(DATA / f'{law}-{split}-targets.json.xz', targets)
        c.require(not {i for x in banks['train'].values() for i in x['entities']} &
                  {i for x in banks['challenge'].values() for i in x['entities']}, 'roster leakage')
        write_json(DATA / f'{law}-lineage.json.xz', banks)


def fit(law, seed):
    bank = cases(law, seed, 'train')
    action_rows, request_rows, feedback = [], [], []
    for case in bank:
        for r in rounds(case, law, 'train'):
            if r['rep'] >= 2:
                continue
            # For each context×stratum both physical actions are explored once.
            a = (r['rep'] + int(case['id'][:8], 16)) % 2
            view = r['views']['delivered']
            reward = r['rewards'][a]
            if view is not None:
                action_rows.append(ActionSample(r['witness'], r['prior'], view, a, reward))
            feedback.append([r['id'], True, a, reward])
    policy = Policy.fit_actions(action_rows)
    for case in bank:
        for r in rounds(case, law, 'train'):
            if r['rep'] < 2:
                continue
            requested = (r['rep'] + int(case['id'][8:16], 16)) % 2 == 0
            view = r['views']['delivered'] if requested else None
            a = policy.act(r['prior'], r['witness'], view)
            reward = r['rewards'][a]
            request_rows.append(RequestSample(r['witness'], r['prior'], r['opportunity'], reward, requested))
            feedback.append([r['id'], requested, a, reward])
    expected = io._read(DATA / f'{law}-train-targets.json.xz')
    c.require(len(feedback) == len(expected) and {f[0] for f in feedback} == {t['id'] for t in expected},
              'incomplete TRAIN budget')
    return policy.fit_requests(request_rows), feedback


def decision(policy, r):
    prior, witness = r['prior'], r['witness']
    asked = policy.ask(prior, witness, r['opportunity'], r['cost'])
    arms = {}
    for arm in ('delivered', 'silent', 'random', 'shuffled', 'free_silent', 'shortcut'):
        paid = asked and arm != 'free_silent'
        channel = 'delivered' if arm == 'shortcut' else arm
        view = r['views'].get(channel) if paid else None
        values = view if arm == 'shortcut' and view is not None else policy.values(prior, witness, view)
        arms[arm] = dict(asked=paid, action=int(values[1] > values[0]), values=list(values), steps=1)
    return arms


def collect(law, seed, out):
    policy = Policy.from_dict(io._read(RESULT / 'fit' / f'{law}-{seed}.json'))
    bank = cases(law, seed, 'challenge')
    # Group raw records by physical task to preserve every receipt and bound file sizes.
    for start in range(0, len(bank), 10):
        bundle = []
        for case in bank[start:start + 10]:
            records = []
            for r in rounds(case, law, 'challenge'):
                begin = perf_counter_ns()
                arms = decision(policy, r)
                elapsed = perf_counter_ns() - begin
                # Environment receipts are seed-invariant. Store them once per law,
                # keyed by the same episode ID in every seed's raw decision bank.
                shared = {}
                if seed == io.SEEDS[0]:
                    shared = dict(sensor_observations=r['sensor']['observations'],
                                  support=r['sensor']['support'], claims_on_file=r['sensor']['claims_on_file'],
                                  on_file_source_sensors=r['on_file_source_sensors'],
                                  potential_source_sensor=r['source_sensor'], potential_source_claim=r['source_claim'],
                                  potential_deliveries=r['claims'], witness=asdict(r['witness']), h=r['h'], rep=r['rep'])
                records.append(dict(law=law, seed=seed, id=r['id'], stratum=r['stratum'], cost=r['cost'],
                                    prior=r['prior'], opportunity=r['opportunity'], arms=arms,
                                    decision_ns=elapsed, **shared))
            bundle.append({'case_id': case['id'], 'predicted': case['predicted'], 'records': records})
        write_json(out / f'{law}-{seed}-{start:03d}.json.xz', bundle)


def saved_rows(law, seed):
    for path in sorted((RESULT / 'raw').glob(f'{law}-{seed}-*.json.xz')):
        for row in chain.from_iterable(b['records'] for b in io._read(path)):
            yield {k: row[k] for k in ('law', 'seed', 'id', 'stratum', 'cost', 'arms')}


def main(stage):
    if stage == 'prepare':
        prepare()
        return
    with published_stage(stage) as out:
        if stage == 'score':
            expected = (dict(row, law=law, seed=seed) for law in LAWS for seed in io.SEEDS
                        for row in io._read(DATA / f'{law}-challenge-targets.json.xz'))
            rows = (r for law in LAWS for seed in io.SEEDS for r in saved_rows(law, seed))
            result = score(rows, expected)
            write_json(out / 'decision.json', result)
            return
        for law in LAWS:
            for seed in io.SEEDS:
                if stage == 'fit':
                    policy, feedback = fit(law, seed)
                    write_json(out / f'{law}-{seed}.json', policy.to_dict())
                    write_json(out / f'{law}-{seed}-feedback.json.xz', feedback)
                else:
                    collect(law, seed, out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'fit', 'collect', 'score'))
    main(parser.parse_args().stage)
