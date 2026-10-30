"""Matched observed NAND/NOR evidence and held three-to-five-contact compositions.

Both laws share blueprints, IDs, anchors, modes, reversals and full sensor masks.
Only realized consequences differ. Physics, laws and query labels stay evaluator-side.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
from itertools import product
import json
import lzma
import random

from . import acceptance_contract as contract, multisource_law_oracle as oracle
from .mixed_composition_data import ROOT, _historical_overlap
from .prospective_data import blueprint_digest, template_digest

FAMILIES = {'train': {'two_contact_chain': ((0, 2), (2, 1))},
    'evaluation': {'aab': ((0, 2), (0, 2), (1, 2)),
                   'abba': ((0, 2), (1, 2), (1, 2), (0, 2)),
                   'abaab': ((0, 2), (1, 2), (0, 2), (0, 2), (1, 2))}}
LAWS = ('nand', 'nor')


def _realize(case, law, mode):
    state = dict(case['observations'][0]); truth = [dict(state)]
    for t, action in enumerate(case['actions']):
        source, target = action['participants'][mode], action['participants'][1 - mode]
        a, b = state[source], state[target]
        state[target] = 1 - (a & b) if law == 'nand' else 1 - (a | b)
        truth.append(dict(state)); case['observations'][t + 1] = dict(state)
    return truth


def _overlap(cases):
    blueprints = {blueprint_digest(case) for case in cases}
    templates = {template_digest(case) for case in cases}
    records = _historical_overlap(blueprints, templates)
    for name in ('mixed-composition-v1/assets.json.xz', 'joint-correlation-v1/assets.json.xz'):
        raw = (ROOT / 'data' / name).read_bytes()
        old = json.loads(lzma.decompress(raw))['inputs']['episodes']
        previous = {blueprint_digest(case) for case in old}
        records[name] = {'sha256': sha256(raw).hexdigest(), 'partitions': {'evaluation': {
            'episode_views': len(old), 'unique_blueprints': len(previous),
            'blueprint_overlap': len(blueprints & previous),
            'template_overlap': len(templates & {template_digest(case) for case in old})}}}
    return records


def build_assets(config):
    contract.require(contract.identifier(config.get('version')), 'study version required')
    settings = config['data']; contract.fields(settings, ('entity_counts', 'split_seeds'))
    counts, seeds = settings['entity_counts'], settings['split_seeds']
    contract.require(type(counts) is list and counts and counts == sorted(set(counts)) and
        all(type(n) is int and 3 <= n <= 6 for n in counts), 'invalid entity inventory')
    contract.fields(seeds, ('train', 'evaluation'))
    contract.require(all(type(s) is int and s >= 20261030061 for s in seeds.values()) and
                     len(set(seeds.values())) == 2, 'fresh disjoint split seeds required')
    banks = {law: {'splits': {}} for law in LAWS}
    audit = {'matched_design': True, 'exposure_scope': 'Same initial states, actions, masks and counts; observed values differ by law.',
        'dependency': 'Law banks, physical-mode and role-reversal views are matched dependent records; not independent replications.'}
    for split, families in FAMILIES.items():
        bundles = {law: {'inputs': {'version': 'active-acceptance-input-v1', 'episodes': []},
                        'cases': [], 'gold': [], 'forecasts': []} for law in LAWS}
        for family, edges in families.items():
            for n in counts:
                for core in product((0, 1), repeat=3):
                    root = [config['version'], split, seeds[split], family, n, core]
                    rng = random.Random(int(contract.digest(root), 16))
                    handles = [contract.digest(['multisource-id-v1', *root, i])[:20] for i in range(n)]
                    initial = dict(zip(handles, [*core, *[rng.randrange(2) for _ in range(n - 3)]], strict=True))
                    ids = handles.copy(); rng.shuffle(ids)
                    lineage = contract.digest(['multisource-lineage-v1', *root])
                    for mode, direction in product((0, 1), repeat=2):
                        pair = contract.digest(['multisource-role-pair-v1', lineage, mode])
                        blueprint = {'episode': contract.digest(['multisource-episode-v1', pair, direction])[:32],
                            'ids': ids, 'observations': [initial] + [dict.fromkeys(ids, 0) for _ in edges],
                            'coverage': [ids.copy() for _ in edges], 'actions': [
                                {'kind': 'contact', 'participants': [handles[i] for i in (edge[::-1] if direction else edge)]}
                                for edge in edges]}
                        meta = {'episode': blueprint['episode'], 'family': family,
                            'partition': 'in_family' if split == 'train' else 'held_out', 'lineage': lineage,
                            'pair_id': pair, 'direction': direction, 'hidden_source_slot': mode, 'entities': n,
                            'core_bits': list(core), 'contact_count': len(edges), 'query_steps': list(range(2, len(edges))),
                            'flow': 'chain' if split == 'train' else 'fan_in' if mode == direction else 'fan_out',
                            'blueprint_sha256': blueprint_digest(blueprint), 'template_sha256': template_digest(blueprint)}
                        for law, bundle in bundles.items():
                            case = deepcopy(blueprint); truth = _realize(case, law, mode)
                            forecasts = oracle.forecast_episode(case, law)
                            bundle['inputs']['episodes'].append(case); bundle['cases'].append(deepcopy(meta))
                            bundle['gold'].append({'episode': case['episode'], 'truth': truth,
                                'possible_worlds': [row['possible_worlds'] for row in forecasts],
                                'information_keys': [row['information_key'] for row in forecasts]})
                            bundle['forecasts'].append({'episode': case['episode'], 'forecasts': forecasts})
        for law, bundle in bundles.items():
            inputs = contract.validate_inputs(bundle['inputs'])
            identity = {'input_sha256': contract.digest(inputs), 'source_sha256': oracle.source_digest(),
                        'information_law_sha256': oracle.law_digest(law)}
            target = {'version': 'active-acceptance-oracle-v1', **identity, 'episodes': bundle.pop('gold')}
            contract.validate_oracle(target, inputs, {**identity, 'oracle_source_sha256': identity['source_sha256'],
                                                     'oracle_sha256': contract.digest(target)})
            bundle['oracle'] = target
            bundle['information'] = {'version': 'multisource-law-information-v1', **identity, 'episodes': bundle.pop('forecasts')}
            banks[law]['splits'][split] = bundle
        left, right = [bundles[law]['inputs']['episodes'] for law in LAWS]
        for a, b in zip(left, right, strict=True):
            contract.require(all(a[k] == b[k] for k in ('episode', 'ids', 'actions', 'coverage')) and
                             a['observations'][0] == b['observations'][0], 'law design differs')
        rows = [f for case in bundles['nand']['information']['episodes'] for f in case['forecasts']]
        cases = bundles['nand']['cases']
        audit[split] = {'episode_views': len(cases), 'physical_lineages': len({r['lineage'] for r in cases}),
            'role_pairs': len({r['pair_id'] for r in cases}), 'planned_forecasts': len(rows),
            'primary_composition_points': sum(len(r['query_steps']) for r in cases),
            'visible_bits': sum(len(c['ids']) * len(c['actions']) for c in left),
            'identifiable_points': sum(len(f['possible_worlds']) == 1 for f in rows),
            'ambiguous_points': sum(len(f['possible_worlds']) > 1 for f in rows),
            'expected_best_all_action_accuracy': sum(max(f['probabilities']) for f in rows) / len(rows),
            'family_views': dict(Counter(r['family'] for r in cases)), 'flow_views': dict(Counter(r['flow'] for r in cases)),
            'historical_overlap': _overlap(left)}
    evaluation = {law: banks[law]['splits']['evaluation'] for law in LAWS}
    lookups = {law: {row['episode']: (case, info['forecasts']) for row, case, info in zip(
        bundle['cases'], bundle['inputs']['episodes'], bundle['information']['episodes'], strict=True)}
        for law, bundle in evaluation.items()}
    contrasts = []
    for meta in evaluation['nand']['cases']:
        if meta['family'] != 'aab' or meta['core_bits'][0] != meta['core_bits'][2]: continue
        a, x = lookups['nand'][meta['episode']]; b, y = lookups['nor'][meta['episode']]
        contract.require(a['observations'][:2] == b['observations'][:2] and a['actions'][:2] == b['actions'][:2] and
            x[1]['information_key'] == y[1]['information_key'] and len(x[1]['possible_worlds']) == len(y[1]['possible_worlds']) == 1 and
            x[1]['possible_worlds'] != y[1]['possible_worlds'], 'critical law contrast is not identified from a matched prefix')
        contrasts.append({'episode': meta['episode'], 'step': 1, 'nand_world': x[1]['possible_worlds'][0],
                          'nor_world': y[1]['possible_worlds'][0], 'information_key': x[1]['information_key']})
    split_cases = [banks['nand']['splits'][split]['inputs']['episodes'] for split in ('train', 'evaluation')]
    audit['current_split_overlap'] = {'blueprint': len(set(map(blueprint_digest, split_cases[0])) & set(map(blueprint_digest, split_cases[1]))),
                                     'template': len(set(map(template_digest, split_cases[0])) & set(map(template_digest, split_cases[1])))}
    audit['law_contrasts'] = len(contrasts)
    return {'banks': banks, 'law_contrasts': contrasts, 'audit': audit}
