"""Matched correlation witnesses from real action/observation histories.

Equal and opposite correlations have identical anchors, delivered prefixes,
state marginals and query actions. Only their observed action histories differ.
All labels, conditional distributions and controls are evaluator-only.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
from itertools import product
import json
import lzma
import math
import random

from . import acceptance_contract as contract, prospective_oracle as oracle
from .mixed_composition_data import ROOT, _historical_overlap
from .prospective_data import _realize, blueprint_digest, template_digest
from .world import Action, World, step

MOTIFS = {
    'chain': {'equal': ((0, 2), (1, 0), (1, 0)), 'opposite': ((0, 2), (2, 1), (1, 0))},
    'fork': {'equal': ((2, 0), (2, 1), (0, 1)), 'opposite': ((2, 0), (1, 2), (0, 1))},
}


def factorized_target_probability(case, forecasts, query_step, target_id):
    """Analytic information-loss control, not a fitted baseline or learner input."""
    ids, reading = sorted(case['ids']), case['observations'][query_step]
    prior = forecasts[query_step - 1]
    worlds = [(tuple((w >> (len(ids) - i - 1)) & 1 for i in range(len(ids))), p)
              for w, p in zip(prior['possible_worlds'], prior['probabilities'], strict=True)]
    worlds = [(bits, p) for bits, p in worlds if all(reading[name] in (None, bits[i]) for i, name in enumerate(ids))]
    mass = sum(p for _, p in worlds)
    contract.require(mass > 0, 'factorized control has no delivered-history support')
    marginals = [sum(p * bits[i] for bits, p in worlds) / mass for i in range(len(ids))]
    modes, action = forecasts[query_step]['surviving_modes'], case['actions'][query_step]
    total = 0.
    for bits in product((0, 1), repeat=len(ids)):
        probability = math.prod(p if bit else 1 - p for p, bit in zip(marginals, bits, strict=True))
        if not probability: continue
        for mode in modes:
            post = step(World(tuple(ids), bits, mode), Action(action['kind'], tuple(action['participants']), action.get('value')))
            total += probability * post.bits[ids.index(target_id)] / len(modes)
    return total


def build_assets(config):
    contract.require(contract.identifier(config.get('version')), 'study version required')
    settings = config['data']; contract.fields(settings, ('entity_counts', 'split_seed'))
    counts, seed = settings['entity_counts'], settings['split_seed']
    contract.require(type(counts) is list and counts and counts == sorted(set(counts)) and
        all(type(n) is int and 3 <= n <= 6 for n in counts), 'invalid entity inventory')
    contract.require(type(seed) is int and seed >= 20261030051, 'fresh split seed required')
    inputs = {'version': 'active-acceptance-input-v1', 'episodes': []}
    gold, cases, information, controls = [], [], [], defaultdict(dict)
    groups, templates = defaultdict(list), set()
    for family, conditions in MOTIFS.items():
        for n in counts:
            root = [config['version'], seed, family, n]
            rng = random.Random(int(contract.digest(root), 16))
            handles = [contract.digest(['correlation-id-v1', *root, i])[:20] for i in range(n)]
            initial = dict(zip(handles, [0, 0, 1] + [rng.randrange(2) for _ in range(n - 3)], strict=True))
            ids = handles.copy(); rng.shuffle(ids)
            lineage = contract.digest(['correlation-lineage-v1', *root])
            for condition, edges in conditions.items():
                blueprint = {'episode': 'blueprint', 'ids': ids, 'coverage': [ids.copy() for _ in edges],
                    'actions': [{'kind': 'contact', 'participants': [handles[i] for i in edge]} for edge in edges],
                    'observations': [initial] + [{name: None if (t == 0 and name == handles[0]) or
                        (t == 1 and name in handles[:2]) else 0 for name in ids} for t in range(3)]}
                fingerprint, template = blueprint_digest(blueprint), template_digest(blueprint)
                groups[fingerprint].append({'family': family, 'entities': n, 'condition': condition, 'lineage': lineage})
                templates.add(template)
                for mode in (0, 1):
                    pair = contract.digest(['correlation-role-pair-v1', lineage, condition, mode])
                    for direction in (0, 1):
                        case = deepcopy(blueprint)
                        case['episode'] = contract.digest(['correlation-episode-v1', pair, direction])[:32]
                        if direction:
                            for action in case['actions']: action['participants'].reverse()
                        truth = _realize(case, mode); forecasts = oracle.forecast_episode(case)
                        contrast = contract.digest(['correlation-contrast-v1', lineage, mode, direction])
                        inputs['episodes'].append(case)
                        gold.append({'episode': case['episode'], 'truth': truth,
                            'possible_worlds': [row['possible_worlds'] for row in forecasts],
                            'information_keys': [row['information_key'] for row in forecasts]})
                        information.append({'episode': case['episode'], 'forecasts': forecasts})
                        cases.append({'episode': case['episode'], 'family': family, 'partition': 'held_out',
                            'lineage': lineage, 'pair_id': pair, 'direction': direction, 'entities': n,
                            'contact_count': 3, 'query_steps': [0, 1, 2], 'query_step': 2,
                            'hidden_source_slot': mode, 'blueprint_sha256': fingerprint, 'template_sha256': template,
                            'contrast_id': contrast, 'condition': condition, 'target_id': handles[1],
                            'expected_target_bit': int(condition == 'opposite')})
                        controls[contrast][condition] = factorized_target_probability(case, forecasts, 2, handles[1])
    contract.validate_inputs(inputs)
    identity = {'input_sha256': contract.digest(inputs), 'source_sha256': oracle.source_digest(),
                'information_law_sha256': oracle.law_digest()}
    target = {'version': 'active-acceptance-oracle-v1', **identity, 'episodes': gold}
    contract.validate_oracle(target, inputs, {**identity, 'oracle_source_sha256': identity['source_sha256'],
                                             'oracle_sha256': contract.digest(target)})
    historical = _historical_overlap(set(groups), templates)
    name = 'mixed-composition-v1/assets.json.xz'; raw = (ROOT / 'data' / name).read_bytes()
    old = json.loads(lzma.decompress(raw))['inputs']['episodes']
    old_blueprints = {blueprint_digest(case) for case in old}
    historical[name] = {'sha256': sha256(raw).hexdigest(), 'partitions': {'evaluation': {
        'episode_views': len(old), 'unique_blueprints': len(old_blueprints),
        'blueprint_overlap': len(set(groups) & old_blueprints),
        'template_overlap': len(templates & {template_digest(case) for case in old})}}}
    forecasts = [row for episode in information for row in episode['forecasts']]
    control_rows = [{'contrast_id': key, 'equal_target_one': row['equal'], 'opposite_target_one': row['opposite'],
                     'gap': row['opposite'] - row['equal']} for key, row in sorted(controls.items())]
    audit = {'physical_lineages': len({case['lineage'] for case in cases}), 'episode_views': len(cases),
        'lineage_interpretation': 'Physical contrast-context lineages labelled by motif/N; not independent physical samples.',
        'role_pairs': len({case['pair_id'] for case in cases}), 'contrast_pairs': len(controls),
        'planned_forecasts': len(forecasts), 'contact_events': len(forecasts),
        'family_views': dict(Counter(case['family'] for case in cases)), 'unique_blueprints': len(groups),
        'canonical_duplicate_groups': {key: rows for key, rows in groups.items() if len(rows) > 1},
        'identifiable_points': sum(len(row['possible_worlds']) == 1 for row in forecasts),
        'ambiguous_points': sum(len(row['possible_worlds']) > 1 for row in forecasts),
        'expected_best_all_action_accuracy': sum(max(row['probabilities']) for row in forecasts) / len(forecasts),
        'max_cumulative_missing_bits': max(sum(v is None for obs in case['observations'] for v in obs.values())
                                         for case in inputs['episodes']),
        'historical_overlap': historical, 'factorized_control': {'scope': 'Analytic oracle-marginal information-loss control; not trained.',
            'contrast_pairs': len(control_rows), 'records': control_rows,
            'target_one_range': [min(v for row in controls.values() for v in row.values()),
                                 max(v for row in controls.values() for v in row.values())],
            'max_abs_gap': max(abs(row['gap']) for row in control_rows)},
        'selection': 'Fixed blueprints before either hidden mode; all conditions and reversals retained without overlap or outcome rejection.',
        'dependency': 'Conditions, modes, reversals, canonical duplicates and model seeds are dependent.',
        'scope': 'Public fixed-law correlation witnesses; no independent custody or new-law claim.'}
    return {'inputs': inputs, 'oracle': target, 'cases': cases, 'audit': audit,
            'information': {'version': 'joint-correlation-information-v1', **identity, 'episodes': information}}
