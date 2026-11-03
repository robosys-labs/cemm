"""Descriptive request-cue ablations on the opened PR #82 bank and feedback."""
from collections import defaultdict
from itertools import product

from . import communication_run as receiver, continuation_run as io
from .acceptance_contract import require
from .communication_exchange import TOKENS, rounds
from .communication_policy import Policy, Witness
from .sender_policy import _margin

ARMS = ('original', 'removed', 'margin')


def _features(prior, opportunity):
    # The two replacements never read opportunity when determining their feature.
    return opportunity, None, _margin(prior)


def _tables(samples):
    """Repeat the v1 requested-minus-silent residual contrast under each feature set."""
    totals = {arm: defaultdict(lambda: [0., 0]) for arm in ARMS}
    for witness, prior, opportunity, requested, reward in samples:
        for arm, feature in zip(ARMS, _features(prior, opportunity), strict=True):
            row = totals[arm][(*witness.key(), feature), requested]
            row[0] += reward - max(prior)
            row[1] += 1
    tables = {}
    for arm, table in totals.items():
        gains = []
        for (key, asked), (total, n) in table.items():
            if asked and (key, False) in table:
                silent, count = table[key, False]
                gains.append([*key, total / n - silent / count])
        tables[arm] = sorted(gains)
    return tables


def fit_ablation(law, seed):
    old = receiver.RESULT / 'fit' / f'{law}-{seed}'
    feedback = {identity: (asked, action, reward) for identity, asked, action, reward in
                io._read(old.with_name(old.name + '-feedback.json.xz'))}
    samples = []
    for case in receiver.cases(law, seed, 'train'):
        for r in rounds(case, law, 'train'):
            if r['rep'] >= 2:  # The first two replicates belonged to action-head exploration.
                paid, action, reward = feedback[r['id']]
                require(reward == r['rewards'][action], 'archived selected-action reward differs')
                samples.append((r['witness'], r['prior'], r['opportunity'], paid, reward))
    tables = _tables(samples)
    require(len(samples) * 2 == len(feedback) and tables['original'] == io._read(old.with_suffix('.json'))['gains'],
            'original request-head reproduction failed')
    return tables


def collect_ablation(law, seed, checkpoint):
    action_head = Policy.from_dict(io._read(receiver.RESULT / 'fit' / f'{law}-{seed}.json'))
    gains = {a: {tuple(row[:-1]): row[-1] for row in checkpoint[a]} for a in ARMS}
    rows = []
    for path in sorted((receiver.RESULT / 'raw').glob(f'{law}-{seed}-*.json.xz')):
        seed7 = path.with_name(path.name.replace(f'{law}-{seed}-', f'{law}-7-'))
        shared = {r['id']: r for b in io._read(seed7) for r in b['records']}
        for bundle in io._read(path):
            for r in bundle['records']:
                env = shared[r['id']]
                witness = Witness(**env['witness'])
                token = env['potential_deliveries']['delivered']['token']
                bit = TOKENS.index(token) if token in TOKENS else None
                view = None
                if bit in env['support']:
                    view = (1., 1.) if r['stratum'] == 'irrelevant' else bundle['predicted'][bit]
                choices = {}
                for a, feature in zip(ARMS, _features(r['prior'], r['opportunity']), strict=True):
                    paid = gains[a].get((*witness.key(), feature), 0.) > r['cost']
                    action = action_head.act(r['prior'], witness, view if paid else None)
                    choices[a] = [paid, action]
                delivered = r['arms']['delivered']
                require(choices['original'] == [delivered['asked'], delivered['action']],
                        'original receiver deployment differs')
                rows.append(dict(law=law, seed=seed, id=r['id'], choices=choices))
    return rows


def score_ablation(rows):
    targets = {law: {r['id']: r for r in io._read(receiver.DATA / f'{law}-challenge-targets.json.xz')}
               for law in receiver.LAWS}
    groups, seen = defaultdict(list), defaultdict(set)
    for row in rows:
        k = row['law'], row['seed']
        rid = row['id']
        require(rid not in seen[k] and set(row['choices']) == set(ARMS), 'duplicate row or invalid arms')
        seen[k].add(rid)
        t = targets[k[0]][rid]
        answers = {}
        for arm, (paid, action) in row['choices'].items():
            require(type(paid) is bool and type(action) is int and action in (0, 1), 'invalid receiver action')
            reward = t['rewards'][action]
            answers[arm] = (paid, reward, 100 * reward - round(100 * t['cost']) * paid)
        groups[k].append((rid, t['stratum'], answers))
    require(set(groups) == set(product(receiver.LAWS, io.SEEDS)), 'receiver conditions incomplete')
    published = io._read(receiver.RESULT / 'scored/decision.json')['conditions']
    result = {}
    for (law, seed), trials in groups.items():
        require(seen[law, seed] == targets[law].keys(), 'receiver challenge coverage differs')
        summaries = {}
        for arm in ARMS:
            requests = successes = net_units = harms = repairs = 0
            worse = []
            strata = defaultdict(lambda: {'rounds': 0, 'requests': 0, 'successes': 0, 'net_units': 0})
            for rid, label, answers in trials:
                paid, reward, net = answers[arm]
                requests += paid
                successes += reward
                net_units += net
                harms += reward < answers['original'][1]
                repairs += reward > answers['original'][1]
                if net < answers['original'][2] and len(worse) < 3:
                    worse.append(rid)
                s = strata[label]
                s['rounds'] += 1
                s['requests'] += paid
                s['successes'] += reward
                s['net_units'] += net
            summaries[arm] = dict(requests=requests, successes=successes, net_units=net_units,
                mean_net=net_units / (100 * len(trials)), harms=harms, repairs=repairs,
                lower_net_examples=worse, strata=dict(strata))
        name = f'{law}/{seed}'
        ref = published[name]['arms']['delivered']
        require(all(summaries['original'][k] == ref[k] for k in ('requests', 'successes'))
                and summaries['original']['mean_net'] == ref['mean_net'], 'original score differs')
        result[name] = summaries
    return {'scope': 'Descriptive refits on opened PR #82 tasks and recorded phase-two feedback.',
            'rounds': sum(map(len, groups.values())), 'conditions': result}
