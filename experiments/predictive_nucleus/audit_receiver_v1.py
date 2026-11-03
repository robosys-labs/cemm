"""Post-score reconstruction of PR #82 using only published records and checkpoints."""
from collections import Counter
import json
import math

from . import continuation_run as io
from .acceptance_contract import require

DATA = io.ROOT / 'data/communication-v1'
RESULT = io.ROOT / 'results/communication-v1'
G3 = io.ROOT / 'data/effect-role-v3'
STUDY = 'f654226c11d22accfa4c161aa5997053f0e5011f'
RECEIPTS = {
    'fit': '7d5d939131ebfd0402ddac37bff629acb542199e06d176921290cfab4d8a1ccc',
    'raw': 'be3687a2d26e8cc950d6f7f0f7fde59303d6ba644759bea587c8a396a20c6ba7',
    'scored': '49ec2ff0e123e2b4d1bf1a03353e9139e5fdabbea1d7c752c1a330916385d81f',
}


def bound_outputs():
    freeze = io.ROOT / 'communication_freeze_v1.json'
    require(io._hash(freeze) == '5b2ea93caa7949a4a484fc4066ebdf7ccb7919ea092445409c3eb07dc251182e',
            'receiver freeze differs')
    for name, expected in io._read(freeze)['prepared'].items():
        require(io._hash(DATA / name) == expected, 'prepared input differs')
    for stage, expected in RECEIPTS.items():
        path = RESULT / stage / 'receipt.json'
        require(io._hash(path) == expected, 'stage receipt differs')
        for name, sha in io._read(path)['outputs'].items():
            require(io._hash(path.parent / name) == sha, 'sealed output differs')


def physical_menu(case, tapes, forecasts):
    """Derive exact target indices/payoffs from actual G3 tape readings."""
    matrix, payoffs = [], []
    for hypotheses in case['episodes']:
        values, rewards = [], []
        for identity in hypotheses:
            utterances = tapes[identity]['utterances']
            target = list(utterances[-2]['reading'])
            for slot, bit in zip(case['participants'], case['goal'], strict=True):
                target[slot] = bit
            index = int(''.join(map(str, target)), 2)
            values.append(math.exp(forecasts[identity][index]))
            rewards.append(int(utterances[-1]['reading'] == target))
        matrix.append(values)
        payoffs.append(rewards)
    return matrix, payoffs


ARMS = {'delivered', 'silent', 'random', 'shuffled', 'free_silent', 'shortcut'}


def verify_decision(raw, shared, matrix, weights, gains):
    """Enforce requested treatment, delivered message view, action values and argmax."""
    require(set(raw['arms']) == ARMS, 'incomplete arm inventory')
    physical = shared['sensor_observations']
    require(len(physical) in (1, 2), 'receiver observation inventory differs')
    support = [physical[1]['reading']] if len(physical) == 2 else [0, 1]
    require(shared['support'] == support, 'physical support differs')
    prior = [sum(matrix[h][a] for h in support) / len(support) for a in (0, 1)]
    opportunity = len({int(matrix[h][1] > matrix[h][0]) for h in support}) > 1
    require(raw['prior'] == prior and raw['opportunity'] is opportunity, 'decision inputs differ')
    witness = shared['witness']
    key = witness['source'], witness['age'] > 0, witness['focus_matches']
    asked = gains.get((*key, opportunity), 0.) > raw['cost']
    deliveries = shared['potential_deliveries']
    for arm, actual in raw['arms'].items():
        paid = asked and arm != 'free_silent'
        values = prior
        if paid and arm not in ('silent', 'free_silent'):
            channel = 'delivered' if arm == 'shortcut' else arm
            token = deliveries[channel]['token']
            bit = {'lo': 0, 'hi': 1}.get(token)
            if bit in support:
                proposed = matrix[bit]
                values = proposed if arm == 'shortcut' else [
                    max(0., min(1., p + weights.get(key, 0.) * (q - p)))
                    for p, q in zip(prior, proposed, strict=True)]
        require(actual['asked'] is paid and type(actual['action']) is int and type(actual['steps']) is int
                and actual == {'asked': paid, 'steps': 1, 'values': values,
                           'action': int(values[1] > values[0])}, 'decision differs from signed checkpoint')

    # Descriptive comparator with explicitly supplied polarity and a hand-supplied
    # price threshold. It receives no hidden bit, outcome, case ID or stratum label.
    rule_ask = opportunity and not key[1] and key[2] and raw['cost'] < .5
    rule_values = prior
    if rule_ask:
        token = deliveries['delivered']['token']
        if token in ('lo', 'hi'):
            reported = int(token == 'hi') ^ int(key[0] == 'B')
            if reported in support:
                rule_values = matrix[reported]
    rule_action = int(rule_values[1] > rule_values[0])
    return rule_ask == asked, rule_action == raw['arms']['delivered']['action']


def audit():
    bound_outputs()
    counts, by_law, unknown_tokens = Counter(), {}, Counter()
    freeze_path = G3 / 'freeze.json'
    trace_root = io.ROOT / 'results/effect-role-v3/traces'
    manifest_path = trace_root / 'manifest.json'
    require(io._hash(freeze_path) == '5380210e7957c8b170c8e8ee39d8b4be130e32eb81dad52e9cff7d9f392b5922'
            and io._hash(manifest_path) == '71f92c8fa36e8fc346d7e24d1a14a1abb1e74ed820c96dbfe688f158e52761b0',
            'upstream G3 freeze differs')
    g3_hashes, trace_hashes = (io._read(p)['artifacts'] for p in (freeze_path, manifest_path))
    for law in ('nand', 'nor'):
        lineage = io._read(DATA / f'{law}-lineage.json.xz')['challenge']
        train = {x['id']: x for x in io._read(DATA / f'{law}-train-targets.json.xz')}
        test = {x['id']: x for x in io._read(DATA / f'{law}-challenge-targets.json.xz')}
        by_law[law] = {
            'menu_goal_cases': len(lineage),
            'physical_menus': len({tuple(map(tuple, c['episodes'])) for c in lineage.values()}),
            'parent_lineages': len({c['lineage'] for c in lineage.values()})}
        tape_path = G3 / f'{law}-inputs.json.xz'
        require(io._hash(tape_path) == g3_hashes[tape_path.name]['sha256'], 'G3 tape differs')
        tapes = {x['id']: x for x in io._read(tape_path)['episodes']}
        shared = {}
        for seed in io.SEEDS:
            point_path = trace_root / f'trace-{law}-{seed}-grounded-fresh.json.xz'
            require(io._hash(point_path) == trace_hashes[point_path.name]['sha256'], 'G3 forecast differs')
            forecasts = {p['id']: p['logp'] for p in io._read(point_path)['points'] if p['view'] == 'canonical'
                         and p['step'] == len(tapes[p['id']]['utterances']) - 1}
            fit = io._read(RESULT / 'fit' / f'{law}-{seed}.json')
            weights, gains = ({tuple(row[:-1]): row[-1] for row in fit[name]} for name in ('weights', 'gains'))
            log = io._read(RESULT / 'fit' / f'{law}-{seed}-feedback.json.xz')
            require(len(log) == len(train) and {r[0] for r in log} == train.keys(), 'TRAIN coverage differs')
            for identity, _, action, reward in log:
                require(reward == train[identity]['rewards'][action], 'TRAIN selected-action payoff differs')
            counts['selected_training_payoffs'] += len(log)
            seen = set()
            for path in sorted((RESULT / 'raw').glob(f'{law}-{seed}-*.json.xz')):
                for group in io._read(path):
                    case = lineage[group['case_id']]
                    matrix, payoffs = physical_menu(case, tapes, forecasts)
                    require(matrix == group['predicted'], 'native physical forecast differs')
                    for row in group['records']:
                        identity = row['id']
                        require(identity not in seen and row['seed'] == seed and row['law'] == law,
                                'duplicate or mismatched condition')
                        seen.add(identity)
                        if seed == io.SEEDS[0]:
                            shared[identity] = row
                        env = shared[identity]
                        irrelevant = row['stratum'] == 'irrelevant'
                        expected = [1, 1] if irrelevant else payoffs[env['h']]
                        require(test[identity]['case_id'] == group['case_id'] and
                                expected == test[identity]['rewards'], 'physical held-out payoff differs')
                        same_query, same_action = verify_decision(
                            row, env, [[1., 1.], [1., 1.]] if irrelevant else matrix, weights, gains)
                        counts['rounds'] += 1
                        counts['checkpoint_arm_decisions'] += len(row['arms'])
                        counts['handcoded_query_matches'] += same_query
                        counts['handcoded_physical_action_matches'] += same_action
                        if seed == io.SEEDS[0] and row['stratum'] == 'unknown':
                            token = env['potential_source_claim']['token']
                            unknown_tokens[token, env['h']] += 1
            require(seen == test.keys(), 'challenge coverage differs')
    return {'reviewed_commit': STUDY, 'by_law': by_law, 'checks': dict(counts),
            'distinct_unknown_token_counts_by_true_bit': {s: [unknown_tokens[s, i] for i in (0, 1)]
                    for s in sorted({s for s, _ in unknown_tokens})},
            'comparator_scope': 'Post hoc, privileged source polarity and fixed price threshold. No training.',
            'result': 'Frozen decisions reproduced. Narrow to menu-goal cases and decoder-unresolved replies.'}


if __name__ == '__main__':
    print(json.dumps(audit(), indent=2, sort_keys=True))
