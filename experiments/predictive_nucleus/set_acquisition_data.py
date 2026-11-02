"""Evaluator-only SET acquisition tapes; no learned model or inference imports.

Atomic prior/request combinations are deliberately shared. Novelty is confined
to identities and five-action compositions; laws/modes remain evaluator metadata.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from itertools import product
from pathlib import Path
import random

from . import acceptance_contract as c, multisource_law_oracle as old
from .prospective_data import blueprint_digest, template_digest

VERSION = 'set-acquisition-v1'
SEEDS = {'train': 20261102071, 'evaluation': 20261102072}
FAMILIES = ('repeated_set', 'alternating_set', 'set_contact_bridge')
LAWS = ('nand', 'nor')


def source_digest():
    return sha256(Path(__file__).read_bytes() + old.source_digest().encode()).hexdigest()


def law_digest(law):
    c.require(law in LAWS, 'unknown contact law')
    return c.digest({'version': VERSION, 'contact_table': old.TABLES[law],
        'set': 'addressed bit becomes requested bit; all other bits persist',
        'source_mode': 'equiprobable 0/1, persistent through whole episode',
        'evidence': 'complete initial anchor and full noiseless observations',
        'scope': '3-6 entities; actions selected before outcomes; no self contacts'})


def forecast_episode(case, law):
    """Table-based prefix oracle; neither actual hidden mode nor truth is an input."""
    law_digest(law)
    case = c.validate_inputs({'version': 'active-acceptance-input-v1', 'episodes': [case]})['episodes'][0]
    ids = sorted(case['ids'])
    modes = {m: dict(case['observations'][0]) for m in (0, 1)}
    result = []
    for t, action in enumerate(case['actions']):
        members = action['participants']
        c.require(action['kind'] in ('set', 'contact') and len(set(members)) == len(members),
                  'SET acquisition oracle requires sets or distinct contacts')
        for mode, state in modes.items():
            if action['kind'] == 'set':
                state[members[0]] = action['value']
            else:
                source, target = members[mode], members[1 - mode]
                state[target] = old.TABLES[law][state[source]][state[target]]
        counts = Counter(sum(state[name] << (len(ids) - i - 1) for i, name in enumerate(ids))
                         for state in modes.values())
        support = sorted(counts)
        result.append({'information_key': c.information_key(case, t), 'possible_worlds': support,
            'probabilities': [counts[w] / len(modes) for w in support], 'surviving_modes': sorted(modes)})
        reading = case['observations'][t + 1]
        modes = {mode: state for mode, state in modes.items()
                 if all(value is None or state[name] == value for name, value in reading.items())}
        c.require(bool(modes), 'delivered evidence contradicts the declared action law')
    return result


def _realize(blueprint, law, mode):
    """Boolean simulator separated from the table-based forecast oracle."""
    case = deepcopy(blueprint); state = dict(case['observations'][0]); truth = [dict(state)]
    for action in case['actions']:
        members = action['participants']
        if action['kind'] == 'set':
            state[members[0]] = action['value']
        else:
            source, target = members[mode], members[1 - mode]
            a, b = state[source], state[target]
            state[target] = 1 - (a & b) if law == 'nand' else 1 - (a | b)
        truth.append(dict(state))
    case['observations'] = truth
    return case


def _design(split, family, n, core, requested, slot=None):
    root = [VERSION, SEEDS[split], split, family, n, core, requested, slot]
    rng = random.Random(int(c.digest(root), 16))
    handles = [c.digest(['identity', root, i])[:20] for i in range(n)]
    anchor = dict(zip(handles, [*core, *[rng.randrange(2) for _ in range(n - 3)]], strict=True))
    ids = handles.copy(); rng.shuffle(ids)
    return root, handles, ids, anchor


def _set(name, value):
    return {'kind': 'set', 'participants': [name], 'value': value}


def _actions(family, handles, value, direction):
    a, b, d = handles[:3]
    if family == 'repeated_set':
        return [_set(a, value), _set(a, value), _set(b, 1 - value), _set(a, 1 - value), _set(b, value)]
    if family == 'alternating_set':
        return [_set(a, value ^ (t % 2)) for t in range(5)]
    contact = lambda x, y: {'kind': 'contact', 'participants': [y, x] if direction else [x, y]}
    return [_set(a, value), contact(a, b), _set(d, 1 - value), contact(b, d), contact(a, d)]


def build_assets():
    train = {'version': 'active-acceptance-input-v1', 'episodes': []}; train_lineages = []
    for core, slot, value in product(product((0, 1), repeat=3), range(3), (0, 1)):
        root, handles, ids, anchor = _design('train', 'single_set', 3, core, value, slot)
        train_lineages.append(c.digest(['lineage', root]))
        blueprint = {'episode': c.digest(['episode', root])[:32], 'ids': ids,
            'observations': [anchor], 'coverage': [ids.copy()], 'actions': [_set(handles[slot], value)]}
        train['episodes'].append(_realize(blueprint, 'nand', 0))
    c.validate_inputs(train)
    laws = {law: {'inputs': {'version': 'active-acceptance-input-v1', 'episodes': []},
                  'cases': [], 'gold': [], 'information': []} for law in LAWS}
    for family, n, core, value in product(FAMILIES, range(3, 7), product((0, 1), repeat=3), (0, 1)):
        root, handles, ids, anchor = _design('evaluation', family, n, core, value)
        lineage = c.digest(['lineage', root]); bridge = family == 'set_contact_bridge'
        for mode, direction in product((0, 1), repeat=2) if bridge else ((0, 0),):
            pair = c.digest(['pair', lineage, mode]) if bridge else None
            episode = c.digest(['episode', root, mode, direction])[:32]
            blueprint = {'episode': episode, 'ids': ids, 'observations': [anchor],
                'coverage': [ids.copy() for _ in range(5)], 'actions': _actions(family, handles, value, direction)}
            for law, bundle in laws.items():
                case = _realize(blueprint, law, mode); forecasts = forecast_episode(case, law)
                bundle['inputs']['episodes'].append(case)
                bundle['cases'].append({'episode': episode, 'family': family, 'partition': 'held_out',
                    'lineage': lineage, 'pair_id': pair, 'direction': direction if bridge else None,
                    'entities': n, 'hidden_source_slot': mode if bridge else None, 'requested': value,
                    'set_points': [{'step': t, 'prior': case['observations'][t][a['participants'][0]],
                        'requested': a['value'], 'changed': case['observations'][t][a['participants'][0]] != a['value']}
                        for t, a in enumerate(case['actions']) if a['kind'] == 'set']})
                bundle['gold'].append({'episode': episode, 'truth': deepcopy(case['observations']),
                    'possible_worlds': [f['possible_worlds'] for f in forecasts],
                    'information_keys': [f['information_key'] for f in forecasts]})
                bundle['information'].append({'episode': episode, 'forecasts': forecasts})
    audit = {'train_lineages': train_lineages, 'train_episodes': 48, 'train_forecasts': 48,
        'evaluation_episodes_per_law': 384, 'evaluation_forecasts_per_law': 1920,
        'role_pairs_per_law': 128, 'split_seeds': dict(SEEDS),
        'scope': 'Fresh identities and five-action compositions; atomic set tuples intentionally shared. '
                 'Law/mode/reversal views are dependent; set-only mode/reversal duplicates omitted.'}
    for law, bundle in laws.items():
        inputs = c.validate_inputs(bundle['inputs'])
        identity = {'input_sha256': c.digest(inputs), 'source_sha256': source_digest(),
                    'information_law_sha256': law_digest(law)}
        oracle = {'version': 'active-acceptance-oracle-v1', **identity, 'episodes': bundle.pop('gold')}
        c.validate_oracle(oracle, inputs, {**identity, 'oracle_source_sha256': identity['source_sha256'],
                                          'oracle_sha256': c.digest(oracle)})
        bundle['oracle'] = oracle
        bundle['information'] = {'version': VERSION + '-information', **identity, 'episodes': bundle['information']}
        rows = [f for e in bundle['information']['episodes'] for f in e['forecasts']]
        audit[law] = {'families': dict(Counter(m['family'] for m in bundle['cases'])),
            'identifiable_points': sum(len(f['possible_worlds']) == 1 for f in rows),
            'ambiguous_points': sum(len(f['possible_worlds']) > 1 for f in rows),
            'expected_best_all_action_accuracy': sum(max(f['probabilities']) for f in rows) / len(rows)}
        c.require(len(inputs['episodes']) == 384 and len(rows) == 1920, 'planned evaluation inventory differs')
    evaluation = laws['nand']['inputs']['episodes']
    audit['split_overlap'] = {label: len({fn(e) for e in train['episodes']} & {fn(e) for e in evaluation})
                             for label, fn in (('blueprint', blueprint_digest), ('template', template_digest))}
    audit['split_overlap']['identity'] = len({i for e in train['episodes'] for i in e['ids']} &
                                            {i for e in evaluation for i in e['ids']})
    atomic = lambda episodes: sorted({(e['observations'][t][a['participants'][0]], a['value'])
        for e in episodes for t, a in enumerate(e['actions']) if a['kind'] == 'set'})
    audit['atomic_set_tuples'] = {'train': atomic(train['episodes']), 'evaluation': atomic(evaluation),
                                 'novel_atomic_tuples': []}
    c.require(len(train['episodes']) == 48 and not any(audit['split_overlap'].values()) and
              audit['atomic_set_tuples']['train'] == audit['atomic_set_tuples']['evaluation'] ==
              [(0, 0), (0, 1), (1, 0), (1, 1)], 'split or atomic inventory differs')
    return {'train': train, 'laws': laws, 'audit': audit}
