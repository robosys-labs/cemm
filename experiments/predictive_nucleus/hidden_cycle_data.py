"""Frozen-weight cycle probes with structurally selected missing feedback.

Physics and stale-state witnesses stay evaluator-side. Full/hidden twins share
all actions and outcomes; only one delivered reading differs. No fitted model
is imported, and no case is retained or rejected using a model prediction.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from itertools import product
import json
import lzma
import random

from . import acceptance_contract as contract, multisource_law_oracle as oracle
from .multisource_law_data import LAWS, ROOT, _overlap, _realize
from .prospective_data import blueprint_digest, template_digest

FAMILIES = {'cycle_forward': ((0, 1), (1, 2), (2, 0)),
            'cycle_reverse': ((2, 0), (1, 2), (0, 1))}
CONDITIONS = ('full', 'hidden')


def _world(state):
    return sum(state[name] << (len(state) - i - 1) for i, name in enumerate(sorted(state)))


def _history(cases):
    """Audit actual law training as well as all retained earlier challenge banks."""
    records = _overlap(cases)
    blueprints = set(map(blueprint_digest, cases)); templates = set(map(template_digest, cases))
    name = 'multisource-law-v1/assets.json.xz'
    raw = (ROOT / 'data' / name).read_bytes(); previous = json.loads(lzma.decompress(raw))
    record = {'sha256': sha256(raw).hexdigest(), 'partitions': {}}
    for law, bank in previous['banks'].items():
        for split, bundle in bank['splits'].items():
            old = bundle['inputs']['episodes']; old_blueprints = set(map(blueprint_digest, old))
            record['partitions'][law + '/' + split] = {'episode_views': len(old),
                'unique_blueprints': len(old_blueprints), 'blueprint_overlap': len(blueprints & old_blueprints),
                'template_overlap': len(templates & set(map(template_digest, old)))}
    records[name] = record
    return records


def build_assets(config):
    contract.require(contract.identifier(config.get('version')), 'study version required')
    settings = config['data']; contract.fields(settings, ('entity_counts', 'split_seed'))
    counts, seed = settings['entity_counts'], settings['split_seed']
    contract.require(type(counts) is list and counts and counts == sorted(set(counts)) and
        all(type(n) is int and 3 <= n <= 6 for n in counts), 'invalid entity inventory')
    contract.require(type(seed) is int and seed >= 20261030063, 'fresh split seed required')
    banks = {law: {'inputs': {'version': 'active-acceptance-input-v1', 'episodes': []},
                   'cases': [], 'gold': [], 'forecasts': []} for law in LAWS}
    for family, edges in FAMILIES.items():
        shared = set(edges[1]) & set(edges[2])
        contract.require(len(shared) == 1, 'second and final contacts must share one entity')
        for n in counts:
            for core in product((0, 1), repeat=3):
                root = [config['version'], seed, family, n, core]
                rng = random.Random(int(contract.digest(root), 16))
                handles = [contract.digest(['hidden-cycle-id-v1', *root, i])[:20] for i in range(n)]
                initial = dict(zip(handles, [*core, *[rng.randrange(2) for _ in range(n - 3)]], strict=True))
                ids = handles.copy(); rng.shuffle(ids)
                lineage = contract.digest(['hidden-cycle-lineage-v1', *root])
                hidden = handles[next(iter(shared))]
                for mode, direction in product((0, 1), repeat=2):
                    twin = contract.digest(['hidden-cycle-twin-v1', lineage, mode, direction])
                    blueprint = {'episode': 'blueprint', 'ids': ids, 'observations': [initial] +
                        [dict.fromkeys(ids, 0) for _ in edges], 'coverage': [ids.copy() for _ in edges],
                        'actions': [{'kind': 'contact', 'participants': [handles[i] for i in
                            (edge[::-1] if direction else edge)]} for edge in edges]}
                    for law, bundle in banks.items():
                        realized = deepcopy(blueprint); truth = _realize(realized, law, mode)
                        stale = dict(truth[2]); stale[hidden] = truth[1][hidden]
                        source, target = (realized['actions'][2]['participants'][i] for i in (mode, 1 - mode))
                        a, b = stale[source], stale[target]
                        stale[target] = 1 - (a & b) if law == 'nand' else 1 - (a | b)
                        for condition in CONDITIONS:
                            case = deepcopy(realized)
                            case['episode'] = contract.digest(['hidden-cycle-episode-v1', twin, condition])[:32]
                            if condition == 'hidden': case['observations'][2][hidden] = None
                            rows = oracle.forecast_episode(case, law)
                            meta = {'episode': case['episode'], 'family': family, 'partition': 'held_out',
                                'lineage': lineage, 'pair_id': contract.digest(['hidden-cycle-role-pair-v1',
                                    lineage, mode, condition]), 'direction': direction, 'hidden_source_slot': mode,
                                'entities': n, 'core_bits': list(core), 'contact_count': 3, 'query_steps': [2],
                                'condition': condition, 'twin_id': twin, 'hidden_handle': hidden,
                                'hidden_changed': truth[2][hidden] != truth[1][hidden],
                                'critical': stale[target] != truth[3][target], 'final_target': target,
                                'stale_final_world': _world(stale), 'stale_target_bit': stale[target],
                                'true_target_bit': truth[3][target],
                                'blueprint_sha256': blueprint_digest(case), 'template_sha256': template_digest(case)}
                            bundle['inputs']['episodes'].append(case); bundle['cases'].append(meta)
                            bundle['gold'].append({'episode': case['episode'], 'truth': deepcopy(truth),
                                'possible_worlds': [r['possible_worlds'] for r in rows],
                                'information_keys': [r['information_key'] for r in rows]})
                            bundle['forecasts'].append({'episode': case['episode'], 'forecasts': rows})
    audit = {'by_law': {}, 'dependency': 'Law, feedback, persistent-mode, role-reversal and order views are paired dependent records.',
        'order_scope': 'The two cycle orders are identity/global-reversal-isomorphic, not independent topology families.',
        'selection': 'One structural overlap entity is masked after the second contact, independently of law, mode and bit values. No outcome rejection.',
        'critical_definition': 'Reset the hidden entity to its last visible value before the final action; the final physical target must differ.',
        'scope': 'One hidden intermediate consequence under separately learned laws; no simultaneous timing or independent custody.'}
    for law, bundle in banks.items():
        inputs = contract.validate_inputs(bundle['inputs'])
        identity = {'input_sha256': contract.digest(inputs), 'source_sha256': oracle.source_digest(),
                    'information_law_sha256': oracle.law_digest(law)}
        target = {'version': 'active-acceptance-oracle-v1', **identity, 'episodes': bundle.pop('gold')}
        contract.validate_oracle(target, inputs, {**identity, 'oracle_source_sha256': identity['source_sha256'],
                                                 'oracle_sha256': contract.digest(target)})
        bundle['oracle'] = target
        bundle['information'] = {'version': 'hidden-cycle-information-v1', **identity, 'episodes': bundle.pop('forecasts')}
        rows = [r for entry in bundle['information']['episodes'] for r in entry['forecasts']]
        cases, episodes = bundle['cases'], inputs['episodes']
        twins = {}
        for meta, case, info in zip(cases, episodes, bundle['information']['episodes'], strict=True):
            twins.setdefault(meta['twin_id'], {})[meta['condition']] = (meta, case, info['forecasts'])
        for pair in twins.values():
            full, hidden = (pair[c] for c in CONDITIONS)
            contract.require(full[0]['critical'] == hidden[0]['critical'] and
                all(full[1][k] == hidden[1][k] for k in ('ids', 'actions', 'coverage')) and
                full[1]['observations'][:2] == hidden[1]['observations'][:2] and
                full[2][:2] == hidden[2][:2] and all(full[2][2][k] == hidden[2][2][k]
                    for k in ('possible_worlds', 'probabilities', 'surviving_modes')), 'feedback twin alignment differs')
        audit['by_law'][law] = {'episode_views': len(cases), 'physical_lineages': len({c['lineage'] for c in cases}),
            'unique_blueprints': len(set(map(blueprint_digest, episodes))), 'unique_templates': len(set(map(template_digest, episodes))),
            'role_pairs': len({c['pair_id'] for c in cases}), 'twin_pairs': len(twins),
            'critical_twin_pairs': sum(pair['hidden'][0]['critical'] for pair in twins.values()),
            'changed_hidden_twin_pairs': sum(pair['hidden'][0]['hidden_changed'] for pair in twins.values()),
            'planned_forecasts': len(rows), 'primary_composition_points': len(cases),
            'identifiable_points': sum(len(r['possible_worlds']) == 1 for r in rows),
            'ambiguous_points': sum(len(r['possible_worlds']) > 1 for r in rows),
            'expected_best_all_action_accuracy': sum(max(r['probabilities']) for r in rows) / len(rows),
            'family_views': dict(Counter(c['family'] for c in cases)),
            'condition_views': dict(Counter(c['condition'] for c in cases)),
            'visible_bits': sum(v is not None for c in episodes for obs in c['observations'][1:] for v in obs.values()),
            'max_cumulative_missing_bits': max(sum(v is None for obs in c['observations'] for v in obs.values()) for c in episodes),
            'combinatorial_live_path_bound': 2, 'combinatorial_candidate_expansion_bound': 2 * 2 ** max(counts)}
    left, right = (banks[law]['inputs']['episodes'] for law in LAWS)
    contract.require(all(all(a[k] == b[k] for k in ('episode', 'ids', 'actions', 'coverage')) and
        a['observations'][0] == b['observations'][0] and [[v is None for v in obs.values()] for obs in a['observations']] ==
        [[v is None for v in obs.values()] for obs in b['observations']] for a, b in zip(left, right, strict=True)),
        'law-matched design differs')
    audit['historical_overlap'] = _history(left)
    return {'banks': banks, 'audit': audit}
