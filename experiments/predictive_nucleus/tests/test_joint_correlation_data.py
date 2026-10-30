"""Real-history correlation witnesses; no checkpoints, fitting or learner runs."""
from collections import Counter, defaultdict
from copy import deepcopy
import unittest

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import joint_correlation_data as data
from experiments.predictive_nucleus.tests.test_prospective_oracle import reference


def config():
    return {'version': 'joint-correlation-data-tests-v1',
            'data': {'entity_counts': [3, 4, 5, 6], 'split_seed': 20261039998}}


def marginals(row, n):
    return [sum(p * ((w >> (n - i - 1)) & 1) for w, p in
                zip(row['possible_worlds'], row['probabilities'], strict=True)) for i in range(n)]


class JointCorrelationDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = data.build_assets(config())
        cls.inputs = {row['episode']: row for row in cls.assets['inputs']['episodes']}
        cls.information = {row['episode']: row['forecasts'] for row in cls.assets['information']['episodes']}

    def test_inventory_reproducibility_and_truthful_overlap(self):
        settings = config(); before = deepcopy(settings)
        self.assertEqual(data.build_assets(settings), self.assets)
        self.assertEqual(settings, before)
        audit = self.assets['audit']
        self.assertEqual([audit[k] for k in ('physical_lineages', 'episode_views', 'role_pairs',
                         'contrast_pairs', 'planned_forecasts', 'identifiable_points', 'ambiguous_points',
                         'max_cumulative_missing_bits')], [8, 64, 32, 32, 192, 32, 160, 3])
        self.assertEqual(audit['family_views'], {'chain': 32, 'fork': 32})
        self.assertTrue(audit['canonical_duplicate_groups'])
        self.assertLess(audit['unique_blueprints'], 16)
        self.assertIn('mixed-composition-v1/assets.json.xz', audit['historical_overlap'])
        self.assertTrue(all(contract.is_sha(row['sha256']) for row in audit['historical_overlap'].values()))
        self.assertTrue(all(row['blueprint_overlap'] == 0 for h in audit['historical_overlap'].values()
                            for row in h['partitions'].values()))

    def test_independent_oracle_boundary_and_resource_budget(self):
        for meta in self.assets['cases']:
            case, rows = self.inputs[meta['episode']], self.information[meta['episode']]
            self.assertEqual(set(case), {'episode', 'ids', 'observations', 'actions', 'coverage'})
            self.assertEqual(rows, reference(case))
            self.assertTrue(all(row['surviving_modes'] == [0, 1] for row in rows))
            self.assertEqual(meta['query_steps'], [0, 1, 2])
            self.assertEqual([a['kind'] for a in case['actions']], ['contact'] * 3)
            missing = [sum(v is None for v in obs.values()) for obs in case['observations']]
            self.assertEqual(missing, [0, 1, 2, 0])
            self.assertLessEqual(2 ** sum(missing) * 2 ** len(case['ids']), 512)
            active = {name for action in case['actions'] for name in action['participants']}
            for i, name in enumerate(sorted(case['ids'])):
                if name not in active:
                    self.assertTrue(all(marginals(row, len(case['ids']))[i] == case['observations'][0][name] for row in rows))

    def test_matched_histories_have_equal_marginals_and_opposite_certain_query_bits(self):
        pairs = defaultdict(dict)
        for meta in self.assets['cases']: pairs[meta['contrast_id']][meta['condition']] = meta
        for members in pairs.values():
            a, b = members['equal'], members['opposite']
            left, right = self.inputs[a['episode']], self.inputs[b['episode']]
            x, y = self.information[a['episode']], self.information[b['episode']]
            self.assertEqual(left['ids'], right['ids'])
            self.assertEqual(left['observations'][:3], right['observations'][:3])
            self.assertEqual(left['coverage'], right['coverage'])
            self.assertEqual(left['actions'][0], right['actions'][0])
            self.assertEqual(left['actions'][2], right['actions'][2])
            self.assertNotEqual(left['actions'][1], right['actions'][1])
            self.assertEqual(marginals(x[1], a['entities']), marginals(y[1], b['entities']))
            self.assertFalse(set(x[1]['possible_worlds']) & set(y[1]['possible_worlds']))
            for meta, case, rows, bit in ((a, left, x, 0), (b, right, y, 1)):
                index = sorted(case['ids']).index(meta['target_id'])
                self.assertEqual(marginals(rows[2], meta['entities'])[index], bit)
                self.assertEqual(meta['expected_target_bit'], bit)
                self.assertEqual(data.factorized_target_probability(case, rows, 2, meta['target_id']), .5)
        control = self.assets['audit']['factorized_control']
        self.assertEqual((control['contrast_pairs'], control['target_one_range'], control['max_abs_gap']), (32, [.5, .5], 0.))

    def test_role_pairs_and_all_dependent_views_are_retained(self):
        pairs, lineages = defaultdict(list), defaultdict(list)
        for meta in self.assets['cases']:
            pairs[meta['pair_id']].append(meta); lineages[meta['lineage']].append(meta)
        for rows in lineages.values():
            self.assertEqual(Counter((r['condition'], r['hidden_source_slot'], r['direction']) for r in rows),
                             Counter({(c, m, d): 1 for c in ('equal', 'opposite') for m in (0, 1) for d in (0, 1)}))
        for rows in pairs.values():
            a, b = sorted(rows, key=lambda row: row['direction'])
            left, right = self.inputs[a['episode']], self.inputs[b['episode']]
            self.assertEqual([{**action, 'participants': list(reversed(action['participants']))}
                              for action in left['actions']], right['actions'])
            self.assertEqual(left['observations'][:3], right['observations'][:3])
            self.assertEqual(data.blueprint_digest(left), data.blueprint_digest(right))

    def test_invalid_config_rejected(self):
        for key, value in [('entity_counts', []), ('entity_counts', [3, 3]), ('entity_counts', [7]),
                           ('split_seed', True), ('split_seed', 20261030050)]:
            settings = config(); settings['data'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): data.build_assets(settings)


if __name__ == '__main__': unittest.main()
