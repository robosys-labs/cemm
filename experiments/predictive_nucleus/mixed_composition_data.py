"""Fresh mixed-contact challenge assets; no fitting or learned predictor imports.

Blueprints precede both mode realizations. Mode and role-direction views share
one physical lineage; four views do not constitute four independent samples.
"""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import lzma
from pathlib import Path
import random

from . import acceptance_contract as contract, prospective_oracle as oracle
from .prospective_data import _realize, blueprint_digest, template_digest

ROOT = Path(__file__).resolve().parent
FAMILIES = {
    'acquired_alias_reverse': ((0, 1), (2, 2), (1, 0)),
    'alias_before_acquisition': ((2, 2), (0, 1), (1, 0)),
    'repeated_alias': ((2, 2), (2, 2), (0, 1), (1, 0)),
    'withheld_alias': ((0, 1), (2, 2), None, (1, 0), (0, 1)),
    'mode_coalescence': ((0, 1), (0, 1), (2, 2), (0, 1), (1, 0)),
    'interleaved_chain': ((0, 1), (2, 2), (1, 2), (0, 1), (1, 0)),
}
HISTORY = ('prospective-assets-v1.json.xz', 'continuation-assets-v1.json.xz',
           'alias-evidence-assets-v1.json.xz', 'alias-evidence-assets-v2.json.xz')


def _historical_overlap(blueprints, templates):
    records = {}
    for name in HISTORY:
        raw = (ROOT / 'data' / name).read_bytes()
        asset = json.loads(lzma.decompress(raw))
        asset = asset.get('bundle', asset)
        groups = dict(asset['splits'])
        if 'alias_training' in asset: groups['alias_training'] = asset['alias_training']
        records[name] = {'sha256': sha256(raw).hexdigest(), 'partitions': {}}
        for split, group in groups.items():
            cases = group['inputs']['episodes']
            old = {blueprint_digest(case) for case in cases}
            shapes = {template_digest(case) for case in cases}
            records[name]['partitions'][split] = {
                'episode_views': len(cases), 'unique_blueprints': len(old),
                'blueprint_overlap': len(blueprints & old), 'template_overlap': len(templates & shapes)}
    return records


def build_assets(config):
    """Build the frozen matrix using version, data.entity_counts and data.split_seed.

    Additional protocol sections belong to the runner. ``information`` is an
    evaluator-only companion retaining exact probabilities and surviving modes;
    the standard observed-input and oracle schemas remain unchanged.
    """
    contract.require(contract.identifier(config.get('version')), 'study version required')
    settings = config['data']
    contract.fields(settings, ('entity_counts', 'split_seed'))
    counts, seed = settings['entity_counts'], settings['split_seed']
    contract.require(type(counts) is list and counts and counts == sorted(set(counts)) and
        all(type(n) is int and 3 <= n <= 6 for n in counts), 'invalid entity inventory')
    contract.require(type(seed) is int and seed >= 20261030041, 'fresh split seed required')
    inputs = {'version': 'active-acceptance-input-v1', 'episodes': []}
    gold, cases, information, blueprints, templates = [], [], [], set(), set()
    for family, edges in FAMILIES.items():
        for n in counts:
            for prebit in (0, 1):
                root = [config['version'], seed, family, n, prebit]
                rng = random.Random(int(contract.digest(root), 16))
                handles = [contract.digest(['mixed-id-v1', *root, i])[:20] for i in range(n)]
                initial = dict(zip(handles, [1, 0, prebit] + [rng.randrange(2) for _ in range(n - 3)], strict=True))
                actions = [{'kind': 'observe', 'participants': []} if edge is None else
                           {'kind': 'contact', 'participants': [handles[i] for i in edge]} for edge in edges]
                missing = {0, 1} if family == 'withheld_alias' else {0} if family == 'mode_coalescence' else set()
                ids = handles.copy(); rng.shuffle(ids)
                readings = [initial] + [{name: None if t in missing and name == handles[1] else 0
                                        for name in ids} for t in range(len(actions))]
                blueprint = {'episode': 'blueprint', 'ids': ids, 'observations': readings,
                             'actions': actions, 'coverage': [ids.copy() for _ in actions]}
                fingerprint = blueprint_digest(blueprint)
                contract.require(fingerprint not in blueprints, 'duplicate mixed blueprint')
                blueprints.add(fingerprint); templates.add(template_digest(blueprint))
                lineage = contract.digest(['mixed-lineage-v1', *root, fingerprint])
                for mode in (0, 1):
                    pair = contract.digest(['mixed-pair-v1', lineage, mode])
                    for direction in (0, 1):
                        case = deepcopy(blueprint)
                        case['episode'] = contract.digest(['mixed-episode-v1', pair, direction])[:32]
                        if direction:
                            for action in case['actions']:
                                if action['kind'] == 'contact': action['participants'].reverse()
                        truth = _realize(case, mode)
                        forecasts = oracle.forecast_episode(case)
                        inputs['episodes'].append(case)
                        gold.append({'episode': case['episode'], 'truth': truth,
                            'possible_worlds': [row['possible_worlds'] for row in forecasts],
                            'information_keys': [row['information_key'] for row in forecasts]})
                        information.append({'episode': case['episode'], 'forecasts': forecasts})
                        cases.append({'episode': case['episode'], 'family': family, 'partition': 'held_out',
                            'lineage': lineage, 'pair_id': pair, 'direction': direction,
                            'entities': n, 'contact_count': sum(edge is not None for edge in edges),
                            'query_steps': list(range(len(edges))), 'prebit': prebit,
                            'hidden_source_slot': mode, 'blueprint_sha256': fingerprint,
                            'template_sha256': template_digest(case)})
    contract.validate_inputs(inputs)
    identity = {'input_sha256': contract.digest(inputs), 'source_sha256': oracle.source_digest(),
                'information_law_sha256': oracle.law_digest()}
    target = {'version': 'active-acceptance-oracle-v1', **identity, 'episodes': gold}
    contract.validate_oracle(target, inputs, {**identity, 'oracle_source_sha256': identity['source_sha256'],
                                             'oracle_sha256': contract.digest(target)})
    forecasts = [row for episode in information for row in episode['forecasts']]
    audit = {'physical_lineages': len(blueprints), 'episode_views': len(cases),
        'role_pairs': len({case['pair_id'] for case in cases}), 'planned_forecasts': len(forecasts),
        'contact_events': sum(case['contact_count'] for case in cases),
        'family_views': dict(Counter(case['family'] for case in cases)),
        'identifiable_points': sum(len(row['possible_worlds']) == 1 for row in forecasts),
        'ambiguous_points': sum(len(row['possible_worlds']) > 1 for row in forecasts),
        'expected_best_all_action_accuracy': sum(max(row['probabilities']) for row in forecasts) / len(forecasts),
        'max_cumulative_missing_bits': max(sum(v is None for reading in case['observations'] for v in reading.values())
                                         for case in inputs['episodes']),
        'historical_overlap': _historical_overlap(blueprints, templates),
        'dependency': 'Both fixed modes and role directions share a blueprint lineage; views and seeds are dependent.',
        'selection': 'Fixed actions, anchor, masks and all query indices precede both mode realizations; no outcome rejection.',
        'scope': 'Fresh public fixed-law mixed templates; no independent custody or new-law claim.'}
    return {'inputs': inputs, 'oracle': target, 'cases': cases, 'audit': audit,
            'information': {'version': 'mixed-composition-information-v1', **identity, 'episodes': information}}
