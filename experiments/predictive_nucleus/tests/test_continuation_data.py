"""Acquisition/query design invariants; no fitting or model performance scores."""
from collections import Counter, defaultdict
from copy import deepcopy
from unittest.mock import patch
import unittest

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import continuation_data as data
from experiments.predictive_nucleus.world import Action, World, step


def config():
    return {'version': 'continuation-data-tests-v1', 'data': {
        'entity_counts': [3, 4, 5, 6],
        'split_seeds': dict(zip(data.SPLITS, range(20261030011, 20261030015))),
        'draws_per_cell': {'train': 8, 'selection': 4, 'calibration': 4, 'evaluation': 4},
        'max_blueprint_attempts': 10000}}


class ContinuationDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = data.build_assets(config())

    def test_exact_inventory_and_reproducibility(self):
        settings = config(); before = deepcopy(settings)
        self.assertEqual(data.build_assets(settings), self.assets)
        self.assertEqual(settings, before)
        expected = {'train': (64, 128, 64), 'selection': (32, 64, 32),
                    'calibration': (32, 64, 32), 'evaluation': (168, 320, 704)}
        for split, (draws, views, queries) in expected.items():
            report = self.assets['audit'][split]
            self.assertEqual((report['physical_draws'], report['episode_views'],
                              report['continuation_queries']), (draws, views, queries))
        evaluation = self.assets['splits']['evaluation']['cases']
        self.assertEqual(sum(len(r['query_steps']) for r in evaluation if r['partition'] == 'in_family'), 32)
        self.assertEqual(sum(len(r['query_steps']) for r in evaluation if r['query_scope'] == 'self_contact'), 16)
        cells = Counter((r['family'], r['entities'], r['contact_count']) for r in evaluation)
        self.assertEqual(len(cells), 42)
        self.assertTrue(all(v == (4 if family == 'self_contact' else 8) for (family, _, _), v in cells.items()))

    def test_strict_observed_boundary_and_gold_physics(self):
        for assets in self.assets['splits'].values():
            inputs, oracle = assets['inputs'], assets['oracle']
            contract.validate_inputs(inputs)
            gold = contract.validate_oracle(oracle, inputs, {'oracle_sha256': contract.digest(oracle),
                'oracle_source_sha256': oracle['source_sha256'],
                'information_law_sha256': oracle['information_law_sha256']})
            rows = {r['episode']: r for r in assets['cases']}
            for case in inputs['episodes']:
                self.assertEqual(set(case), {'episode', 'ids', 'observations', 'actions', 'coverage'})
                ids = case['ids']
                world = World(tuple(ids), tuple(case['observations'][0][i] for i in ids),
                              rows[case['episode']]['hidden_source_slot'])
                for t, action in enumerate(case['actions']):
                    world = step(world, Action(action['kind'], tuple(action['participants']), action.get('value')))
                    self.assertEqual(gold[case['episode']]['truth'][t + 1], dict(zip(ids, world.bits)))

    def test_acquisition_query_timing_and_actual_identifiability(self):
        for split, assets in self.assets['splits'].items():
            gold = {r['episode']: r for r in assets['oracle']['episodes']}
            rows = {r['episode']: r for r in assets['cases']}
            for case in assets['inputs']['episodes']:
                meta, oracle = rows[case['episode']], gold[case['episode']]
                contacts = [t for t, a in enumerate(case['actions']) if a['kind'] == 'contact']
                self.assertEqual(meta['contact_count'], len(contacts))
                before = dict(case['observations'][0])
                for action in case['actions'][:contacts[0]]:
                    self.assertEqual(action['kind'], 'set')
                    before[action['participants'][0]] = action['value']
                if meta['family'] == 'self_contact':
                    self.assertIsNone(meta['acquisition_step'])
                    self.assertEqual(meta['query_scope'], 'self_contact')
                    self.assertEqual(meta['query_steps'], contacts)
                else:
                    self.assertTrue(any(before[i] for i in case['actions'][contacts[0]]['participants']))
                    self.assertEqual(meta['acquisition_step'], contacts[0])
                    self.assertEqual(meta['query_steps'], contacts[1:])
                    self.assertEqual(len(oracle['possible_worlds'][contacts[0]]), 2)
                self.assertTrue(all(len(oracle['possible_worlds'][t]) == 1 for t in meta['query_steps']))
                if meta['family'] == 'single_contact':
                    self.assertEqual(meta['query_steps'], [])
                    self.assertEqual(meta['query_scope'], 'acquisition_only')
                if split != 'evaluation': self.assertLessEqual(len(contacts), 2)

    def test_masks_are_complete_through_acquisition_and_bounded_after(self):
        missing_cases = 0
        for split, assets in self.assets['splits'].items():
            for case in assets['inputs']['episodes']:
                first = next(t for t, a in enumerate(case['actions']) if a['kind'] == 'contact')
                masks = [[value is None for value in row.values()] for row in case['observations']]
                self.assertFalse(any(any(mask) for mask in masks[:first + 2]))
                missing = sum(sum(mask) for mask in masks)
                self.assertLessEqual(missing, 3)
                self.assertLessEqual(2 ** (missing + len(case['ids'])), 512)
                if split != 'evaluation': self.assertEqual(missing, 0)
                missing_cases += missing > 0
                kinds = [a['kind'] for a in case['actions']]
                if 'set' in kinds: self.assertEqual(kinds.index('set'), 0)
                self.assertLessEqual(kinds.count('set'), 1)
                if 'observe' in kinds: self.assertEqual(kinds.index('observe'), len(kinds) - 1)
                self.assertLessEqual(kinds.count('observe'), 1)
                self.assertTrue(all(set(row) == set(case['ids']) for row in case['coverage']))
        self.assertGreater(missing_cases, 0)

    def test_actual_graphs_include_depth_not_just_family_labels(self):
        assets = self.assets['splits']['evaluation']
        observed = {c['episode']: c for c in assets['inputs']['episodes']}
        for meta in assets['cases']:
            if meta['direction'] == 1: continue
            case = observed[meta['episode']]
            edges = [tuple(a['participants']) for a in case['actions'] if a['kind'] == 'contact']
            k, family = meta['contact_count'], meta['family']
            nodes = {i for e in edges for i in e}
            if family == 'three_contact_chain':
                self.assertEqual(len(nodes), k + 1)
                self.assertTrue(all(a[1] == b[0] for a, b in zip(edges, edges[1:])))
            elif family == 'fork':
                self.assertEqual(len(nodes), k + 1)
                self.assertEqual(len({e[0] for e in edges}), 1)
            elif family == 'cycle':
                self.assertEqual(len(nodes), k)
                self.assertTrue(all(a[1] == b[0] for a, b in zip(edges, edges[1:] + edges[:1])))
            elif family == 'disjoint':
                self.assertIn(k, (3, 4, 5))
                self.assertEqual(len(nodes), 4)
                self.assertTrue(set(edges[0]).isdisjoint(edges[1]))
                self.assertEqual(edges, [edges[i % 2] for i in range(k)])
            elif family == 'self_contact':
                self.assertEqual(k, 1)
                self.assertEqual(edges[0][0], edges[0][1])

    def test_paired_coupling_and_split_disjointness(self):
        known = {}
        for split, assets in self.assets['splits'].items():
            observed = {c['episode']: c for c in assets['inputs']['episodes']}
            pairs = defaultdict(list)
            for meta in assets['cases']:
                self.assertEqual(known.setdefault(meta['blueprint_sha256'], split), split)
                self.assertEqual(meta['blueprint_sha256'], data.blueprint_digest(observed[meta['episode']]))
                pairs[meta['lineage']].append(meta)
            for rows in pairs.values():
                if rows[0]['family'] == 'self_contact':
                    self.assertEqual(len(rows), 1); self.assertIsNone(rows[0]['pair_id'])
                    continue
                self.assertEqual(len(rows), 2)
                a, b = sorted(rows, key=lambda r: r['direction'])
                for key in ('hidden_source_slot', 'pair_id', 'blueprint_sha256', 'query_steps', 'acquisition_step'):
                    self.assertEqual(a[key], b[key])
                x, y = observed[a['episode']], observed[b['episode']]
                self.assertEqual(x['observations'][0], y['observations'][0])
                self.assertEqual(x['ids'], y['ids']); self.assertEqual(x['coverage'], y['coverage'])
                self.assertEqual([[r[i] is None for i in x['ids']] for r in x['observations']],
                                 [[r[i] is None for i in y['ids']] for r in y['observations']])
                actions = deepcopy(x['actions'])
                for action in actions:
                    if action['kind'] == 'contact': action['participants'].reverse()
                self.assertEqual(actions, y['actions'])

    def test_actual_hidden_mode_cannot_change_design_or_query_selection(self):
        settings = config(); settings['data']['entity_counts'] = [3]
        settings['data']['draws_per_cell'] = dict.fromkeys(data.SPLITS, 1)
        rng = data._rng
        class FixedMode:
            def __init__(self, mode): self.mode = mode
            def randrange(self, bound): return self.mode
        results = []
        for mode in (0, 1):
            with patch.object(data, '_rng', side_effect=lambda label, material, m=mode:
                FixedMode(m) if label == 'continuation-hidden-mode-v1' else rng(label, material)):
                results.append(data.build_assets(settings))
        for split in data.SPLITS:
            left, right = [r['splits'][split] for r in results]
            self.assertEqual([{k: v for k, v in r.items() if k != 'hidden_source_slot'} for r in left['cases']],
                             [{k: v for k, v in r.items() if k != 'hidden_source_slot'} for r in right['cases']])
            self.assertEqual([data.blueprint_digest(c) for c in left['inputs']['episodes']],
                             [data.blueprint_digest(c) for c in right['inputs']['episodes']])

    def test_invalid_or_exhausted_design_fails_without_silent_reduction(self):
        for mutate in (lambda d: d.update(entity_counts=[3, 3]),
                       lambda d: d['draws_per_cell'].update(evaluation=5),
                       lambda d: d['split_seeds'].update(train=d['split_seeds']['evaluation']),
                       lambda d: d.update(max_blueprint_attempts=True)):
            settings = config(); mutate(settings['data'])
            with self.assertRaises(ValueError): data.build_assets(settings)
        settings = config(); settings['data']['max_blueprint_attempts'] = 5
        with patch.object(data, 'blueprint_digest', return_value='0' * 64):
            with self.assertRaisesRegex(ValueError, 'blueprint budget exhausted'):
                data.build_assets(settings)


if __name__ == '__main__':
    unittest.main()
