"""Verify and score the published decisions for transfer to unseen sender bindings."""
from collections import Counter, defaultdict
from itertools import product
from math import isfinite

from .acceptance_contract import digest, require
from .communication_score import LAWS, SEEDS
from .sender_scoring import _argmax, _bit, _index, _pair, _prob

BITS = tuple(product(range(2), repeat=2))


def _code_envelope(cells):
    """Highest net attainable by any fixed two-bit Boolean code per public context."""
    total = 0
    for alternatives in cells.values():
        require(set(alternatives) == set(BITS), 'incomplete private-reading factorial')
        total += max(sum(alternatives[bits][bit] for bits, bit in zip(BITS, code, strict=True))
                     for code in product(range(2), repeat=4))
    return total


def _counterfactuals(messages):
    counts = Counter()
    for (context, bits, focus), token in messages.items():
        if focus == 0:
            counts['goal_pairs'] += 1
            switched = token != messages[context, bits, 1]
            counts['goal_flips'] += switched
            if bits[0] != bits[1]:
                counts['opposing_goal_pairs'] += 1
                counts['opposing_goal_flips'] += switched
        for axis, before in enumerate(bits):
            if before == 0:
                changed = list(bits)
                changed[axis] = 1
                name = 'relevant' if axis == focus else 'irrelevant'
                counts[name + '_pairs'] += 1
                if messages[context, tuple(changed), focus] != token:
                    counts[name + '_flips'] += 1
    require(counts['goal_pairs'] and counts['relevant_pairs'] and counts['irrelevant_pairs'],
            'no paired counterfactuals')
    return counts

PARTS = ('recombined', 'fresh')
STRATA = ('hidden', 'known', 'costly', 'indifferent')
ARMS = ('delivered', 'silent', 'random', 'shuffled', 'lookup', 'legacy',
        'raw_dot', 'free_silent', 'public_router', 'margin')


def _badge(identity):
    require(type(identity) is int and 0 <= identity < 16, 'invalid badge identity')
    return tuple(2 * ((identity >> i) & 1) - 1 for i in range(4))


def _round_id(law, pair, part, badges, goal, bits, stratum, rep):
    return digest(['g4-transfer-round-v1', law, 'challenge', pair, part, badges, goal, bits, stratum, rep])


def _raw_dot(sites, goal, bits):
    delta = sum((x - y) * z for x, y, z in zip(*sites, goal, strict=True))
    return bits[int(delta < 0)] if delta else min(bits)


def _gain_table(rows, width):
    table = {}
    for *key, gain in rows:
        require(len(key) == width and all(type(v) is int and 0 <= v < 4 for v in key)
                and type(gain) in (float, int) and isfinite(gain) and -1 <= gain <= 1
                and tuple(key) not in table, 'invalid request checkpoint')
        table[tuple(key)] = gain
    return table


def _score_partition(episodes, raw, bank, law, seed, models):
    from .transfer_sender import legacy_send

    shared, lookup, legacy, request, margin = models
    totals = defaultdict(Counter)
    budgets = defaultdict(Counter)
    examples = defaultdict(list)
    messages = {}
    books = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    seen_goals = defaultdict(set)
    physics, forecasts = {}, {}
    seen = set()
    for identity in sorted(episodes):
        t, row = bank[identity], raw[identity]
        pair, part, stratum, rep = t['pair_id'], t['partition'], t['stratum'], t['rep']
        require(stratum in STRATA and type(rep) is int and 0 <= rep < 4 and t['source'] == 'W0',
                'unregistered episode condition')
        bits, badges, goal = tuple(t['bits']), tuple(t['badge_ids']), t['goal_id']
        require(_pair(bits, _bit) and len(badges) == 2 and badges[0] != badges[1]
                and type(goal) is int and goal in badges,
                'invalid private bits or goal binding')
        focus = badges.index(goal)
        sites, g = tuple(map(_badge, badges)), _badge(goal)
        require(t['law'] == law and t['seed'] == seed and t['split'] == 'challenge',
                'target physical condition mismatch')
        goal_vector = (-g[1], g[0], -g[3], g[2])
        require(sites == tuple(map(tuple, t['sites'])) and tuple(t['goal']) == goal_vector
                and _round_id(law, pair, part, badges, goal, bits, stratum, rep) == identity,
                'target identity or encoded input differs')
        seen_goals[pair].add(badges)
        cell = (pair, badges, focus, bits, stratum, rep)
        require(cell not in seen, 'repeated factorial cell')
        seen.add(cell)
        known, indifferent = stratum == 'known', stratum == 'indifferent'
        local, cost = bits[focus] if known else None, 75 if stratum == 'costly' else 5
        require((t['local'] is None if local is None else _bit(t['local']) and t['local'] == local)
                and type(t['cost']) in (float, int) and t['cost'] == cost / 100
                and t['menu_reversed'] is bool(rep % 2), 'bad sensor support, cost or action order')
        rewards, matrix = tuple(t['rewards']), tuple(map(tuple, t['matrix']))
        require(_pair(rewards, _bit) and sum(rewards) == (2 if indifferent else 1)
                and _pair(matrix, lambda r: _pair(r, _prob)), 'invalid physical rewards/forecasts')
        if indifferent:
            require(matrix == ((1., 1.), (1., 1.)), 'indifferent objective depends on its reply')
        else:
            orientation = rep % 2
            canonical = tuple(r[::-1] if orientation else r for r in matrix)
            pkey = (pair, focus)
            require(forecasts.setdefault(pkey, canonical) == canonical
                    and physics.setdefault(pkey, _argmax(rewards) ^ orientation ^ bits[focus])
                    == _argmax(rewards) ^ orientation ^ bits[focus], 'inconsistent physical forecast/payoff')
        prior = matrix[local] if known else tuple((x + y) / 2 for x, y in zip(*matrix))
        require(_pair(t['prior'], _prob) and prior == tuple(t['prior']), 'prior differs from sensor support')
        witness = t['witness_ids']
        require(_pair(witness, lambda x: isinstance(x, str) and bool(x)) and len(set(witness)) == 2,
                'missing private evidence provenance')
        # Replay the published sender and request checkpoints before checking any scored intervention.
        emitted = shared.send(sites, goal_vector, bits)
        gap = min(3, int(4 * abs(prior[1] - prior[0])))
        ceiling = min(3, int(4 * max(prior)))
        ask = request.get((gap, ceiling), 0.) > t['cost']
        margin_ask = margin.get((gap,), 0.) > t['cost']
        require(_bit(row['emitted']) and row['emitted'] == emitted and row['asked'] is ask
                and row['margin_asked'] is margin_ask, 'raw sender or requests disagree with checkpoints')
        require((sites[0], sites[1], goal_vector, bits) not in lookup.entries,
                'held-out raw symbol pattern exists in TRAIN lookup')
        claim = digest(['g4-transfer-claim-v1', law, seed, identity, 'W0', 1, witness, emitted])
        require(row['claim_id'] == claim, 'claim has lost its source evidence')
        donor_bits = tuple(b ^ int(i != focus or rep >= 2 and not known) for i, b in enumerate(bits))
        donor = _round_id(law, pair, part, badges, goal, donor_bits, stratum, rep)
        noise = int(digest(['g4-transfer-random-v1', identity])[:16], 16) % 2
        require(t['donor'] == donor and _bit(t['random_bit']) and t['random_bit'] == noise,
                'unregistered shuffled or random intervention')
        tokens = (emitted, None, noise, raw[donor]['emitted'], lookup.send(sites, goal_vector, bits),
                  legacy_send(legacy, sites, goal_vector, bits), _raw_dot(sites, goal_vector, bits),
                  None, bits[focus], emitted)
        require(set(row['arms']) == set(ARMS), 'missing or foreign intervention')
        gross = {}
        for arm, wire in zip(ARMS, tokens, strict=True):
            paid = margin_ask if arm == 'margin' else ask and arm != 'free_silent'
            wire = wire if paid else None
            action_row = row['arms'][arm]
            origin = None
            if wire is not None:
                origin = (claim if arm in ('delivered', 'margin') else raw[donor]['claim_id'] if arm == 'shuffled'
                          else digest(['g4-transfer-control-v1', arm, identity, wire]))
            values = prior if wire is None or known else matrix[wire]
            a = _argmax(values)
            require((action_row['token'] is None if wire is None else
                     _bit(action_row['token']) and action_row['token'] == wire)
                    and action_row['origin'] == origin and _bit(action_row['action']) and action_row['action'] == a,
                    'wire payload, origin or chosen physical action differs')
            y = gross[arm] = rewards[a]
            s = totals[arm]
            s['requests'] += paid
            s['successes'] += y
            s['net_units'] += 100 * y - cost * int(paid)
            s['brier_sum'] += (values[a] - y) ** 2
        for arm in ARMS[1:]:
            totals[arm]['repairs'] += gross['delivered'] > gross[arm]
            if gross['delivered'] < gross[arm]:
                totals[arm]['harms'] += 1
                if len(examples[arm]) < 3:
                    examples[arm].append(identity)
        s = budgets[stratum]
        s['n'] += 1
        s['requests'] += ask
        s['successes'] += gross['delivered']
        if bits[0] != bits[1] and stratum == 'hidden':
            s['opposing_readings'] += 1
            s['correct_opposing_symbol'] += emitted == bits[focus]
        if stratum == 'hidden':
            messages[(pair, badges, rep), bits, focus] = emitted
        cells = books[pair, badges][bits]
        for symbol in range(2):
            values = prior if known or not ask else matrix[symbol]
            cells[symbol] += 100 * rewards[_argmax(values)] - cost * int(ask)
    n = len(episodes)
    require(n == 3072 and len(seen_goals) == 12 and all(len(b) == 2 and next(iter(b))[::-1] in b
            for b in seen_goals.values()), 'incomplete physical-pair or badge-order factorial')
    # Verify physical pair assignment independently, including the eight distinct
    # badges and the directed placements used in each transfer population.
    masks = (10, 12, 10) if part == 'recombined' else (3, 12, 3)
    edges = [(i, i ^ mask) for mask in masks for i in range(16)
             if i.bit_count() % 2 == int(part == 'fresh') and i < i ^ mask]
    require(all(seen_goals[p] == {e, e[::-1]} for p, e in zip(sorted(seen_goals), edges, strict=True)),
            'badge binding outside its registered partition')
    # Cardinality and the verified domains force complete 2×2×4×4×4 cells per pair.
    causal = _counterfactuals(messages)
    envelope = _code_envelope(books)
    main = totals['delivered']['net_units']
    checks = {'goal_blind_code': main - envelope > 3 * n,
              'relevant_flip': 5 * causal['relevant_flips'] >= 4 * causal['relevant_pairs'],
              'irrelevant_flip': 5 * causal['irrelevant_flips'] <= causal['irrelevant_pairs'],
              'goal_switch': 5 * causal['goal_flips'] >= 2 * causal['goal_pairs'],
              'opposing_goal_switch': 5 * causal['opposing_goal_flips'] >= 4 * causal['opposing_goal_pairs']}
    hidden = budgets['hidden']
    checks['opposing_readings'] = 5 * hidden['correct_opposing_symbol'] >= 4 * hidden['opposing_readings']
    checks['request_hidden'] = 5 * hidden['requests'] >= 4 * hidden['n']
    checks['success_hidden'] = 5 * hidden['successes'] >= 4 * hidden['n']
    for name in ('known', 'costly', 'indifferent'):
        checks['avoid_' + name] = 5 * budgets[name]['requests'] <= budgets[name]['n']
    for arm, counts in totals.items():
        delta = main - counts['net_units']
        if arm == 'public_router':
            checks['net_vs_' + arm] = 2 * delta >= -n
        elif arm == 'margin':
            checks['net_vs_' + arm] = 2 * delta > n and counts['harms'] == 0
        elif arm != 'delivered':
            checks['net_vs_' + arm] = delta > 3 * n
        counts['mean_net'] = counts['net_units'] / (100 * n)
        counts['brier'] = counts.pop('brier_sum') / n
    return dict(n=n, arms=dict(totals), strata=dict(budgets), checks=checks, passed=all(checks.values()),
                causal=dict(causal), goal_blind_net=envelope / (100 * n), harm_examples=dict(examples))


def score_condition(rows, targets, law, seed, checkpoint):
    from .sender_policy import Sender
    from .transfer_sender import ExactLookup, SharedSender

    require(law in LAWS and type(seed) is int and seed in SEEDS, 'invalid physical model condition')
    raw, bank = _index(rows), _index(targets)
    require(raw.keys() == bank.keys() and len(raw) == 6144, 'incomplete challenge bank')
    models = (SharedSender.from_dict(checkpoint['shared']), ExactLookup.from_dict(checkpoint['lookup']),
              Sender.from_dict(checkpoint['legacy']), _gain_table(checkpoint['request']['gains'], 2),
              _gain_table(checkpoint['margin']['gains'], 1))
    reports = {part: _score_partition([k for k, t in bank.items() if t['partition'] == part],
                                     raw, bank, law, seed, models) for part in PARTS}
    return dict(law=law, seed=seed, partitions=reports, passed=all(p['passed'] for p in reports.values()))


def decision(reports):
    table = {(r['law'], r['seed']): r for r in reports}
    require(len(reports) == len(table) == 10 and set(table) == set(product(LAWS, SEEDS)), 'incomplete conditions')
    passed = all(r['passed'] for r in reports)
    n = sum(p['n'] for r in reports for p in r['partitions'].values())
    return dict(decision='KEEP_UNSEEN_BINDING' if passed else 'REVISE', passed=passed, episodes=n,
                arm_decisions=n * len(ARMS),
                conditions={f'{law}/{seed}': r for (law, seed), r in sorted(table.items())})
