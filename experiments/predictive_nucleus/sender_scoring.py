"""Independent audit and decision from published sender-v1 targets and raw decisions."""
from collections import Counter, defaultdict
from itertools import product

from .acceptance_contract import digest, require
from .communication_score import LAWS, SEEDS, binary_calibration

ARMS = ('delivered', 'silent', 'random', 'shuffled', 'fixed0', 'fixed1',
        'action_code', 'free_silent', 'public_router')
STRATA = ('hidden', 'known', 'costly')
BITS = tuple(product(range(2), repeat=2))
TAGS = ((0, 1), (1, 0))


def _bit(x):
    return type(x) is int and x in (0, 1)


def _pair(x, predicate):
    return isinstance(x, (tuple, list)) and len(x) == 2 and all(map(predicate, x))


def _prob(x):
    return type(x) in (int, float) and 0 <= x <= 1


def _argmax(values):
    return int(values[1] > values[0])


def _identity(pair, bits, tags, goal, source, stratum, rep):
    return digest(['g4-sender-round-v1', pair, bits, tags, goal, source, stratum, rep])


def _index(rows):
    records = {}
    for row in rows:
        identity = row['id']
        require(isinstance(identity, str) and identity not in records, 'duplicate/invalid episode ID')
        records[identity] = row
    return records


def _schedule(pair_ids):
    require(len(pair_ids) == 12, 'challenge must have twelve distinct task pairs')
    for pair, bits, tags, goal, group, stratum, rep in product(
            sorted(pair_ids), BITS, TAGS, range(2), ('shared', 'crossed'), STRATA, range(4)):
        source = 'W0' if group == 'shared' else ('W1' if goal == 1 else 'W2')
        yield pair, bits, tags, goal, source, stratum, rep


def _same(mapping, key, value, reason):
    require(mapping.setdefault(key, value) == value, reason)


def score_condition(rows, targets, law, seed):
    require(law in LAWS and type(seed) is int and seed in SEEDS, 'unregistered G3 condition')
    raw, bank = _index(rows), _index(targets)
    require(raw.keys() == bank.keys() and len(bank) == 4608, 'incomplete raw/target bank')
    pairs = {t['pair_id'] for t in bank.values()}
    physics, forecasts, public_asks, source_blind = {}, {}, {}, {}
    books = defaultdict(lambda: [[0, 0] for _ in BITS])
    totals, strata, examples = defaultdict(Counter), defaultdict(Counter), defaultdict(list)
    probabilities, outcomes = defaultdict(list), defaultdict(list)
    sent = {}
    for key in _schedule(pairs):
        pair, bits, tags, goal, source, stratum, rep = key
        episode = _identity(*key)
        require(episode in bank, 'registered factorial cell missing')
        t, row = bank[episode], raw[episode]
        require(_bit(t['goal']) and type(t['rep']) is int and _pair(t['bits'], _bit)
                and _pair(t['tags'], _bit) and (t['pair_id'], tuple(t['bits']), tuple(t['tags']),
                t['goal'], t['source'], t['stratum'], t['rep']) == key, 'target identity/content mismatch')
        require(row['law'] == law and type(row['seed']) is int and row['seed'] == seed and
                row['pair_id'] == pair and _bit(row['emitted']), 'raw identity/condition mismatch')
        group = 'shared' if source == 'W0' else 'crossed'
        require(t['source_group'] == group and t['goal_pair'] ==
                digest(['g4-sender-goal-pair-v1', pair, bits, tags, group, stratum, rep])
                and type(t['menu_reversed']) is bool and t['menu_reversed'] == bool(rep % 2), 'goal-pair/source/orientation mismatch')
        focus = tags.index(goal)
        known = stratum == 'known'
        local = bits[focus] if known else None
        cost = 75 if stratum == 'costly' else 5
        require(type(t['cost']) in (int, float) and t['cost'] == cost / 100 and
                (row['local'] is None if local is None else _bit(row['local']) and row['local'] == local),
                'invalid public cost or local observation')
        rewards = t['rewards']
        require(_pair(rewards, _bit) and sum(rewards) == 1, 'invalid physical payoff vector')
        require(_pair(t['witness_ids'], lambda x: isinstance(x, str) and bool(x))
                and len(set(t['witness_ids'])) == 2, 'missing distinct physical provenance')
        matrix, prior = row['matrix'], row['prior']
        require(_pair(matrix, lambda p: _pair(p, _prob)) and _pair(prior, _prob)
                and _pair(t['matrix'], lambda p: _pair(p, _prob))
                and tuple(map(tuple, t['matrix'])) == tuple(map(tuple, matrix)),
                'invalid native values or mismatch with published forecast catalogue')
        matrix = tuple(map(tuple, matrix))
        prior = tuple(prior)
        observed_prior = matrix[local] if known else tuple((lo + hi) / 2 for lo, hi in zip(*matrix))
        require(prior == observed_prior, 'sensor prior disagrees with its available evidence')
        # Reversing physical menu slots on odd replicates must reverse payoffs and predictions together.
        orientation = rep % 2
        canonical = tuple(p[::-1] if orientation else p for p in matrix)
        _same(forecasts, (pair, focus), canonical, 'native forecast depends on hidden/private metadata')
        _same(physics, (pair, focus), _argmax(rewards) ^ orientation ^ bits[focus],
              'payoff is not controlled by the selected physical bit')
        emitted = row['emitted']
        claim = digest(['g4-sender-claim-v1', law, seed, pair, episode, source, 1,
                        list(t['witness_ids']), emitted])
        require(row['claim_id'] == claim, 'emitted claim is not bound to the source evidence')
        _same(source_blind, (bits, tags, goal), emitted, 'sender depends on unavailable source/menu information')
        sent[key] = emitted
        donor_bits = list(bits)
        donor_bits[1 - focus] ^= 1
        donor_bits[focus] ^= int(rep >= 2 and not known)
        donor = _identity(pair, donor_bits, tags, goal, source, stratum, rep)
        random_bit = int(digest(['g4-sender-random-v1', episode])[:16], 16) % 2
        require(t['donor'] == donor and donor in raw and _bit(t['random_bit'])
                and t['random_bit'] == random_bit, 'invalid shuffled donor or independent random bit')
        tokens = (emitted, None, random_bit, raw[donor]['emitted'], bits[0], bits[1], emitted, None, bits[focus])
        decisions = row['arms']
        require(set(decisions) == set(ARMS), 'intervention inventory differs')
        ask = decisions['delivered']['asked']
        require(type(ask) is bool, 'invalid receiver request')
        _same(public_asks, (prior, cost), ask, 'request depends on information other than public prior/cost')
        cells = ('all', stratum, group, f'{group}/goal{goal}/{stratum}')
        gross, net = {}, {}
        for arm, token in zip(ARMS, tokens, strict=True):
            a = decisions[arm]
            paid = ask and arm != 'free_silent'
            token = token if paid else None
            require(type(a['asked']) is bool and a['asked'] == paid and type(a['steps']) is int and a['steps'] == 1
                    and (a['token'] is None if token is None else _bit(a['token']) and a['token'] == token),
                    'request, wire token or action budget differs from registered intervention')
            origin = None
            if token is not None:
                if arm == 'shuffled':
                    origin = raw[donor]['claim_id']
                elif arm in ('delivered', 'action_code'):
                    origin = claim
                else:
                    origin = digest(['g4-sender-intervention-v1', arm, episode, token])
            require(a['origin'] == origin, 'wire delivery origin differs from its source or intervention')
            values = prior if known or token is None else matrix[token]
            if arm == 'action_code' and not known and token is not None:
                values = (1 - token, token)
            require(_pair(a['values'], _prob) and tuple(a['values']) == values and _bit(a['action'])
                    and a['action'] == _argmax(values), 'action or value differs from audited physical decoder')
            action = a['action']
            gross[arm] = rewards[action]
            net[arm] = 100 * rewards[action] - cost * int(paid)
            count = totals[arm]
            count['n'] += 1
            count['requests'] += paid
            count['successes'] += rewards[action]
            count['net_units'] += net[arm]
            probabilities[arm].append(values[action])
            outcomes[arm].append(rewards[action])
        for arm in ARMS[1:]:
            delta = gross['delivered'] - gross[arm]
            totals[arm]['gained'] += delta > 0
            totals[arm]['lost'] += delta < 0
            if delta < 0 and len(examples[arm]) < 3:
                examples[arm].append(episode)
        for cell in cells:
            s = strata[cell]
            s['n'] += 1
            s['asks'] += ask
            s['successes'] += gross['delivered']
            for arm in ('delivered', 'fixed0', 'fixed1'):
                s[arm] += net[arm]
        for scope in ('all', group):
            values_by_symbol = books[scope, tags][2 * bits[0] + bits[1]]
            for token in range(2):
                v = prior if known or not ask else matrix[token]
                values_by_symbol[token] += 100 * rewards[_argmax(v)] - cost * int(ask)

    n = len(raw)
    checks, comparisons, reports = {}, {}, {}
    main = totals['delivered']['net_units']
    for arm, s in totals.items():
        reports[arm] = {**s, 'mean_net': s['net_units'] / (100 * n),
                        'selected_reward': binary_calibration(probabilities[arm], outcomes[arm])}
        if arm != 'delivered':
            delta = main - s['net_units']
            checks[f'net_vs_{arm}'] = 2 * delta >= -n if arm == 'public_router' else delta > 3 * n
            comparisons[arm] = {'gain': delta / (100 * n), 'gained_successes': s['gained'],
                                'lost_successes': s['lost'], 'loss_examples': examples[arm]}
    checks['request_hidden'] = 5 * strata['hidden']['asks'] >= 4 * strata['hidden']['n']
    checks['success_hidden'] = 5 * strata['hidden']['successes'] >= 4 * strata['hidden']['n']
    for k in ('known', 'costly'):
        checks[f'avoid_{k}'] = 5 * strata[k]['asks'] <= strata[k]['n']
    for goal in (0, 1):
        s = strata[f'crossed/goal{goal}/hidden']
        checks[f'held_goal{goal}_asks'] = 5 * s['asks'] >= 4 * s['n']
        checks[f'held_goal{goal}_success'] = 5 * s['successes'] >= 4 * s['n']
        checks[f'held_goal{goal}_over_fixed'] = s['delivered'] - max(s['fixed0'], s['fixed1']) > 3 * s['n']
    envelope = {}
    for scope in ('all', 'crossed'):
        total, tables = 0, []
        for tags in TAGS:
            cells = books[scope, tags]
            score, code = max((sum(cell[v] for cell, v in zip(cells, code)), code)
                              for code in product(range(2), repeat=4))
            total += score
            tables.append(list(code))
        s = strata[scope]
        checks[f'net_over_goal_blind_{scope}'] = s['delivered'] - total > 3 * s['n']
        envelope[scope] = {'net': total / (100 * s['n']), 'codebooks_by_placement': tables,
                           'gain': (s['delivered'] - total) / (100 * s['n'])}
    causal = Counter()
    for key, token in sent.items():
        pair, bits, tags, goal, source, stratum, rep = key
        if stratum == 'hidden':
            for i in (0, 1):
                if bits[i] != 0:
                    continue
                flipped = list(bits)
                flipped[i] = 1
                other = sent[pair, tuple(flipped), tags, goal, source, stratum, rep]
                label = 'relevant' if tags[i] == goal else 'irrelevant'
                causal[label + '_pairs'] += 1
                causal[label + '_flips'] += other != token
        if source == 'W0' and goal == 0:
            causal['goal_pairs'] += 1
            causal['goal_flips'] += sent[pair, bits, tags, 1, source, stratum, rep] != token
    checks['relevant_signal'] = 5 * causal['relevant_flips'] >= 4 * causal['relevant_pairs']
    checks['irrelevant_signal'] = 5 * causal['irrelevant_flips'] <= causal['irrelevant_pairs']
    checks['goal_only_switch'] = 5 * causal['goal_flips'] >= 2 * causal['goal_pairs']
    return {'law': law, 'seed': seed, 'n': n, 'arms': reports, 'comparisons': comparisons,
            'strata': dict(strata), 'causal': dict(causal), 'goal_blind_envelope': envelope,
            'checks': checks, 'passed': all(checks.values())}


def decision(reports):
    bank = {(r['law'], r['seed']): r for r in reports}
    require(len(reports) == len(bank) == 10 and set(bank) == set(product(LAWS, SEEDS)),
            'incomplete or duplicate sender condition')
    passed = all(r['passed'] for r in reports)
    return {'decision': 'KEEP_BOUNDED_SENDER' if passed else 'REVISE',
            'passed': passed, 'episodes': sum(r['n'] for r in reports),
            'arm_decisions': len(ARMS) * sum(r['n'] for r in reports),
            'conditions': {f'{law}/{seed}': r for (law, seed), r in sorted(bank.items())}}
