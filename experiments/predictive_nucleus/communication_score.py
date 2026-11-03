"""Held-out G4 utility arithmetic on saved decisions. Never imports a learner."""
import math
from collections import defaultdict
from itertools import product

from .acceptance_contract import identifier, require


LAWS = ('nand', 'nor')
SEEDS = (7, 11, 23, 37, 53)
STRATA = ('useful', 'misleading', 'known', 'irrelevant', 'costly', 'stale', 'shifted', 'unknown', 'conflict')
ARMS = ('delivered', 'silent', 'random', 'shuffled', 'free_silent', 'shortcut')


def _bit(value):
    return type(value) is int and value in (0, 1)


def binary_calibration(probabilities, outcomes):
    """Brier for P(outcome=1), and ten equal-width positive-class calibration bins."""
    require(len(probabilities) == len(outcomes) and outcomes, 'empty or unpaired calibration')
    bins = [[] for _ in range(10)]
    squared = []
    for p, y in zip(probabilities, outcomes):
        require(type(p) in (int, float) and 0 <= p <= 1 and type(y) is int and y in (0, 1),
                'invalid binary forecast or outcome')
        bins[min(int(p * 10), 9)].append((p, y))
        squared.append((p - y) ** 2)
    summaries = []
    for group in bins:
        n = len(group)
        summaries.append({'count': n, 'mean_probability': math.fsum(p for p, _ in group) / n if n else None,
                          'frequency': sum(y for _, y in group) / n if n else None})
    return {'n': len(outcomes), 'brier': math.fsum(squared) / len(outcomes),
            'ece': math.fsum(x['count'] * abs(x['mean_probability'] - x['frequency'])
                             for x in summaries if x['count']) / len(outcomes), 'bins': summaries}


def _index(records):
    rows = {}
    for row in records:
        key = (row['law'], row['seed'], row['id'])
        require(key[0] in LAWS and type(key[1]) is int and key[1] in SEEDS and identifier(key[2]),
                'invalid law/seed/episode ID')
        require(key not in rows, f'duplicate record {key}')
        rows[key] = row
    return rows


def _measure(raw, target):
    label, cost, rewards = target['stratum'], target['cost'], target['rewards']
    require(label in STRATA and type(cost) in (int, float) and cost == (.75 if label == 'costly' else .05)
            and raw['stratum'] == label and type(raw['cost']) in (int, float) and raw['cost'] == cost,
            'stratum or cost mismatch')
    require(type(rewards) is list and len(rewards) == 2 and all(map(_bit, rewards)), 'invalid reward target')
    arms = raw['arms']
    require(type(arms) is dict and set(arms) == set(ARMS), 'incomplete or unexpected arm')
    points = {}
    for arm in ARMS:
        choice = arms[arm]
        asked, action, steps, values = (choice[k] for k in ('asked', 'action', 'steps', 'values'))
        require(type(asked) is bool and type(steps) is int and steps == 1 and _bit(action),
                'invalid request, action or physical step count')
        require(asked == (False if arm == 'free_silent' else arms['delivered']['asked']),
                'mismatched intervention request budget')
        require(type(values) is list and len(values) == 2
                and all(type(p) in (float, int) and 0 <= p <= 1 for p in values), 'invalid reward estimates')
        paid = round(100 * cost) if asked else 0
        points[arm] = {'action': action, 'asked': asked, 'reward': rewards[action], 'paid_units': paid,
                       'net_units': 100 * rewards[action] - paid, 'probability': values[action]}
    if not arms['delivered']['asked']:
        for arm in ARMS[1:]:
            require(all(arms['delivered'][k] == arms[arm][k] for k in ('action', 'values')),
                    'delivery intervention changed a no-request decision')
    return {'id': raw['id'], 'stratum': label, 'arms': points}


def _condition(points):
    n = len(points)
    arms = {}
    for arm in ARMS:
        selected = [r['arms'][arm] for r in points]
        rewards = [r['reward'] for r in selected]
        arms[arm] = {'requests': sum(r['asked'] for r in selected), 'steps': n, 'successes': sum(rewards),
                     'mean_reward': sum(rewards) / n, 'mean_cost': sum(r['paid_units'] for r in selected) / (n * 100),
                     'mean_net': sum(r['net_units'] for r in selected) / (n * 100),
                     'selected_reward_calibration': binary_calibration([r['probability'] for r in selected], rewards)}
    checks, comparisons = {}, {}
    for arm in ARMS[1:]:
        changes, repairs, harms = 0, [], []
        net_gain = 0
        for row in points:
            delivered, control = row['arms']['delivered'], row['arms'][arm]
            changes += delivered['action'] != control['action']
            if delivered['reward'] > control['reward']:
                repairs.append(row['id'])
            if delivered['reward'] < control['reward']:
                harms.append(row['id'])
            net_gain += delivered['net_units'] - control['net_units']
        threshold_units = 1 if arm == 'shortcut' else 3
        checks['net_over_' + arm] = net_gain > n * threshold_units
        comparisons[arm] = {'mean_paired_net_gain': net_gain / (n * 100),
                            'required_strictly_above': threshold_units / 100,
                            'changed_actions': changes, 'gained_successes': len(repairs),
                            'lost_successes': len(harms), 'gain_examples': repairs[:3], 'loss_examples': harms[:3]}
    strata = {}
    for name in STRATA:
        group = [r for r in points if r['stratum'] == name]
        require(group, 'missing required stratum ' + name)
        decisions = [r['arms']['delivered'] for r in group]
        requests, successes = sum(r['asked'] for r in decisions), sum(r['reward'] for r in decisions)
        size = len(group)
        strata[name] = {'n': size, 'requests': requests, 'successes': successes,
                        'request_rate': requests / size, 'success_rate': successes / size,
                        'failed_goal_examples': [r['id'] for r in group if not r['arms']['delivered']['reward']][:3]}
        if name in ('useful', 'misleading'):
            checks['request_' + name] = 5 * requests >= 4 * size
            checks['success_' + name] = 5 * successes >= 4 * size
        elif name != 'unknown':
            checks['avoid_request_' + name] = 5 * requests <= size
        if name != 'unknown':
            should_ask = name in ('useful', 'misleading')
            strata[name]['request_error_examples'] = [r['id'] for r in group
                if r['arms']['delivered']['asked'] != should_ask][:3]
    return {'n': n, 'arms': arms, 'comparisons': comparisons, 'strata': strata,
            'checks': checks, 'passed': all(checks.values())}


def score(rows, expected):
    """Join complete preregistered targets by episode ID and score every law and seed."""
    observed, targets = _index(rows), _index(expected)
    require(observed.keys() == targets.keys(), 'missing or unexpected episode identity')
    conditions = defaultdict(list)
    for key in sorted(targets):
        conditions[key[:2]].append(_measure(observed[key], targets[key]))
    require(set(conditions) == set(product(LAWS, SEEDS)), 'missing law/seed condition')
    results = {f'{law}/{seed}': _condition(points) for (law, seed), points in conditions.items()}
    passed = all(r['passed'] for r in results.values())
    return {'decision': 'KEEP_BOUNDED_RECEIVER' if passed else 'REVISE', 'passed': passed,
            'episodes': len(targets), 'arm_decisions': len(targets) * len(ARMS), 'conditions': results}
