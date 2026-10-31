"""Fresh paired timing views from frozen-law observations, never model outputs.

All core anchors are covered. Spectator bits use a deterministic pattern, not
all 2**N anchors. The timing rule and grouping are supplied; law and mode stay
evaluator-only. Common-snapshot event permutations are actual extra episodes.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
from itertools import product
import json
import lzma
from pathlib import Path
import random

from . import acceptance_contract as common, timing_contract as contract, timing_oracle as oracle

ROOT = Path(__file__).parent
LAWS = ('nand', 'nor')
CONDITIONS = ('ordered', 'common_snapshot', 'common_snapshot_permuted')
FAMILIES = {'chain': (((0, 1), (1, 2)), ((2, 0),), 3),
            'repeated': (((0, 1), (0, 1)), (), 3),
            'fan_in': (((0, 2), (1, 2)), ((0, 1), (2, 0)), 3),
            'disjoint': (((0, 1), (2, 3)), (), 4)}


def _contact(state, pair, law, mode):
    result = dict(state)
    source, target = (pair[i] for i in (mode, 1 - mode))
    a, b = state[source], state[target]
    result[target] = 1 - (a & b) if law == 'nand' else 1 - (a | b)
    return result


def _realize(case, law, mode):
    state, truth = dict(case['observations'][0]), [dict(case['observations'][0])]
    for action in case['actions']:
        if action['kind'] == 'contact':
            state = _contact(state, action['participants'], law, mode)
        elif action['timing'] == 'ordered':
            for pair in action['contacts']:
                state = _contact(state, pair, law, mode)
        else:
            anchor, state = state, dict(state)
            for pair in action['contacts']:
                event = _contact(anchor, pair, law, mode)
                for name, value in event.items():
                    if value != anchor[name]:
                        state[name] = value
        truth.append(dict(state))
    case['observations'] = deepcopy(truth)
    return truth


def build_assets(config):
    common.require(common.identifier(config.get('version')), 'study version required')
    settings = config['data']; common.fields(settings, ('entity_counts', 'split_seed'))
    counts, seed = settings['entity_counts'], settings['split_seed']
    common.require(type(counts) is list and counts and counts == sorted(set(counts)) and
        all(type(n) is int and 3 <= n <= 6 for n in counts), 'invalid timing entity inventory')
    common.require(type(seed) is int and seed >= 20261031067, 'fresh timing split seed required')
    banks = {law: {'inputs': {'version': 'timing-input-v1', 'episodes': []}, 'cases': [],
                   'oracle_episodes': [], 'information_episodes': [], 'timing_contrasts': [], 'permutation_pairs': []}
             for law in LAWS}
    for family, (edges, suffix, core_count) in FAMILIES.items():
        for n in counts:
            if n < core_count: continue
            for core in product((0, 1), repeat=core_count):
                root = [config['version'], seed, family, n, core]
                rng = random.Random(int(common.digest(root), 16))
                handles = [common.digest(['timing-id-v1', *root, i])[:20] for i in range(n)]
                anchor = dict(zip(handles, [*core, *[rng.randrange(2) for _ in range(n - core_count)]], strict=True))
                ids = handles.copy(); rng.shuffle(ids)
                lineage = common.digest(['timing-lineage-v1', *root])
                for mode, direction in product((0, 1), repeat=2):
                    def pair(edge): return [handles[i] for i in (edge[::-1] if direction else edge)]
                    timing_pair = common.digest(['timing-pair-v1', lineage, mode, direction])
                    permutation_pair = common.digest(['timing-permutation-v1', lineage, mode, direction])
                    for law, bundle in banks.items():
                        triple = {}
                        for condition in CONDITIONS:
                            contacts = [pair(edge) for edge in edges]
                            if condition == 'common_snapshot_permuted': contacts.reverse()
                            actions = [{'kind': 'contact', 'participants': pair((0, 1))},
                                {'kind': 'contact_group', 'timing': 'ordered' if condition == 'ordered' else 'common_snapshot',
                                 'contacts': contacts}, *[{'kind': 'contact', 'participants': pair(edge)} for edge in suffix]]
                            case = {'episode': common.digest(['timing-episode-v1', timing_pair, condition])[:32],
                                'ids': ids.copy(), 'observations': [dict(anchor)], 'actions': actions,
                                'coverage': [ids.copy() for _ in actions]}
                            truth = _realize(case, law, mode)
                            rows = oracle.forecast_episode(case, law)
                            meta = {'episode': case['episode'], 'family': family, 'partition': 'held_out',
                                'lineage': lineage, 'pair_id': common.digest(['timing-role-pair-v1', lineage, mode, condition]),
                                'direction': direction, 'hidden_source_slot': mode, 'entities': n, 'core_bits': list(core),
                                'contact_count': 3 + len(suffix), 'query_steps': list(range(1, len(actions))),
                                'condition': condition, 'timing_pair_id': timing_pair, 'permutation_pair_id': permutation_pair,
                                'group_step': 1, 'pre_group_key': rows[1]['history_key'],
                                'group_entry_core_bits': [truth[1][name] for name in handles[:core_count]]}
                            bundle['inputs']['episodes'].append(case); bundle['cases'].append(meta)
                            bundle['oracle_episodes'].append({'episode': case['episode'], 'truth': truth,
                                'possible_worlds': [row['possible_worlds'] for row in rows],
                                'information_keys': [row['information_key'] for row in rows]})
                            bundle['information_episodes'].append({'episode': case['episode'], 'forecasts': rows})
                            triple[condition] = (case, meta, truth, rows)
                        ordered, snapshot, permuted = (triple[c] for c in CONDITIONS)
                        critical = ordered[3][1]['possible_worlds'] != snapshot[3][1]['possible_worlds']
                        for _, meta, _, _ in triple.values(): meta['critical'] = critical
                        common.require(all(ordered[0]['observations'][:2] == row[0]['observations'][:2] and
                            ordered[1]['pre_group_key'] == row[1]['pre_group_key'] and ordered[3][0] == row[3][0]
                            for row in triple.values()), 'timing prefix mismatch')
                        common.require(ordered[0]['actions'][1]['contacts'] == snapshot[0]['actions'][1]['contacts'] and
                            ordered[3][1]['information_key'] != snapshot[3][1]['information_key'], 'timing action binding mismatch')
                        common.require(snapshot[2] == permuted[2] and all(a['probabilities'] == b['probabilities'] and
                            a['possible_worlds'] == b['possible_worlds'] for a, b in zip(snapshot[3], permuted[3], strict=True)),
                            'common snapshot depends on event list order')
                        context = {key: ordered[1][key] for key in ('family', 'entities', 'lineage', 'direction', 'hidden_source_slot')}
                        context.update(step=1, history_key=ordered[1]['pre_group_key'])
                        bundle['timing_contrasts'].append({**context, 'timing_pair_id': timing_pair,
                            'ordered_episode': ordered[0]['episode'], 'snapshot_episode': snapshot[0]['episode'],
                            'ordered_world': ordered[3][1]['possible_worlds'][0],
                            'snapshot_world': snapshot[3][1]['possible_worlds'][0], 'critical': critical})
                        bundle['permutation_pairs'].append({**context, 'permutation_pair_id': permutation_pair,
                            'snapshot_episode': snapshot[0]['episode'], 'permuted_episode': permuted[0]['episode'],
                            'expected_world': snapshot[3][1]['possible_worlds'][0],
                            'nontrivial_event_permutation': snapshot[0]['actions'][1]['contacts'] != permuted[0]['actions'][1]['contacts']})
    audit = {'by_law': {}, 'dependency': 'Laws, timing/permutation views, modes, directions and model seeds are paired dependent records.',
        'anchor_scope': 'All 2**3 core anchors for chain/repeated/fan_in and 2**4 for disjoint. Spectator bits follow one deterministic pattern per core/size/family; not every 2**N full anchor.',
        'supplied_timing': 'ordered uses sequential state updates without intermediate feedback; common_snapshot unions binary deltas from the common anchor and shared mode.',
        'selection': 'Every generated view is retained. Critical iff the two oracle singleton group-end worlds differ; no model-dependent filtering.',
        'counts_scope': 'Each group is one forecast and feedback, containing two physical contacts. Permutation controls are additional real episodes.'}
    for law, bundle in banks.items():
        inputs = contract.validate_inputs(bundle['inputs'])
        identity = {'input_sha256': common.digest(inputs), 'source_sha256': oracle.source_digest(),
                    'information_law_sha256': oracle.law_digest(law)}
        bundle['oracle'] = {'version': 'timing-oracle-v1', **identity, 'episodes': bundle.pop('oracle_episodes')}
        bundle['information'] = {'version': 'timing-information-v1', **identity, 'episodes': bundle.pop('information_episodes')}
        rows = [row for case in bundle['information']['episodes'] for row in case['forecasts']]
        common.require(all(len(entry['forecasts'][0]['possible_worlds']) == 2 and
            all(len(row['possible_worlds']) == len(row['surviving_modes']) == 1 for row in entry['forecasts'][1:])
            for entry in bundle['information']['episodes']), 'acquisition did not identify mode')
        metas = bundle['cases']; coverage = defaultdict(Counter)
        for meta in metas:
            if meta['condition'] == 'ordered':
                coverage[f"{meta['family']}/mode-{meta['hidden_source_slot']}/direction-{meta['direction']}"][
                    ''.join(map(str, meta['group_entry_core_bits']))] += 1
        audit['by_law'][law] = {'episode_views': len(metas), 'physical_lineages': len({c['lineage'] for c in metas}),
            'role_pairs': len({c['pair_id'] for c in metas}), 'timing_pairs': len(bundle['timing_contrasts']),
            'permutation_pairs': len(bundle['permutation_pairs']),
            'nontrivial_permutation_pairs': sum(c['nontrivial_event_permutation'] for c in bundle['permutation_pairs']),
            'critical_timing_pairs': sum(c['critical'] for c in bundle['timing_contrasts']),
            'critical_by_family': dict(Counter(c['family'] for c in bundle['timing_contrasts'] if c['critical'])),
            'planned_forecasts': len(rows), 'physical_contacts': sum(c['contact_count'] for c in metas),
            'group_events': len(metas), 'singleton_events': len(rows) - len(metas),
            'identifiable_points': sum(len(row['possible_worlds']) == 1 for row in rows),
            'ambiguous_points': sum(len(row['possible_worlds']) > 1 for row in rows),
            'expected_best_all_action_accuracy': sum(max(row['probabilities']) for row in rows) / len(rows),
            'family_views': dict(Counter(c['family'] for c in metas)), 'condition_views': dict(Counter(c['condition'] for c in metas)),
            'group_entry_core_coverage': {key: dict(sorted(value.items())) for key, value in sorted(coverage.items())},
            'coverage_counting': 'One ordered view per timing triple; repeated entity sizes remain counted.'}
    for left, right in zip(banks['nand']['inputs']['episodes'], banks['nor']['inputs']['episodes'], strict=True):
        common.require(all(left[k] == right[k] for k in ('episode', 'ids', 'actions', 'coverage')) and
            left['observations'][0] == right['observations'][0], 'law bank design mismatch')
    old_path = ROOT / 'data/multisource-law-v1/assets.json.xz'
    previous = json.loads(lzma.decompress(old_path.read_bytes()))
    audit['actual_training'] = {'artifact_sha256': sha256(old_path.read_bytes()).hexdigest(),
        'per_law': {law: {'episodes': len(previous['banks'][law]['splits']['train']['inputs']['episodes']),
            'max_contacts': max(len(c['actions']) for c in previous['banks'][law]['splits']['train']['inputs']['episodes']),
            'group_events': sum(a['kind'] == 'contact_group' for c in previous['banks'][law]['splits']['train']['inputs']['episodes']
                                for a in c['actions'])} for law in LAWS}}
    return {'banks': banks, 'audit': audit}
