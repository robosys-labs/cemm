"""Synthetic data/oracle invariants, never scientific model scores."""
from collections import Counter
from copy import deepcopy
import unittest

from experiments.predictive_nucleus import acceptance_contract as c
from experiments.predictive_nucleus import set_acquisition_data as d


class SetAcquisitionDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = d.build_assets()

    def test_balanced_training_observations_and_untouched_coordinates(self):
        counts = Counter()
        for e in self.assets['train']['episodes']:
            self.assertEqual(set(e), {'episode', 'ids', 'observations', 'actions', 'coverage'})
            a = e['actions'][0]; target = a['participants'][0]; pre, post = e['observations']
            counts[pre[target], a['value']] += 1
            self.assertEqual(post[target], a['value'])
            self.assertTrue(all(pre[i] == post[i] for i in e['ids'] if i != target))
        self.assertEqual(counts, Counter({(0, 0): 12, (0, 1): 12, (1, 0): 12, (1, 1): 12}))

    def test_inventory_no_useless_views_and_disjoint_sequences(self):
        audit = self.assets['audit']
        self.assertEqual(audit['split_overlap'], {'blueprint': 0, 'template': 0, 'identity': 0})
        self.assertEqual(audit['atomic_set_tuples']['train'], audit['atomic_set_tuples']['evaluation'])
        for law, bundle in self.assets['laws'].items():
            self.assertEqual(len(bundle['inputs']['episodes']), 384)
            self.assertEqual(audit[law]['families'], {'repeated_set': 64, 'alternating_set': 64, 'set_contact_bridge': 256})
            pairs = Counter(m['pair_id'] for m in bundle['cases'] if m['pair_id'] is not None)
            self.assertEqual(len(pairs), 128); self.assertEqual(set(pairs.values()), {2})
            self.assertEqual(audit[law]['identifiable_points'] + audit[law]['ambiguous_points'], 1920)

    def test_law_twins_and_reversed_pairs_share_exogenous_design(self):
        left, right = (self.assets['laws'][law]['inputs']['episodes'] for law in d.LAWS)
        for a, b in zip(left, right, strict=True):
            self.assertTrue(all(a[k] == b[k] for k in ('episode', 'ids', 'actions', 'coverage')))
            self.assertEqual(a['observations'][0], b['observations'][0])
        bundle = self.assets['laws']['nand']; episodes = {e['episode']: e for e in left}; pairs = {}
        for m in bundle['cases']:
            if m['pair_id'] is not None: pairs.setdefault(m['pair_id'], []).append(episodes[m['episode']])
        for a, b in pairs.values():
            self.assertEqual(a['observations'][0], b['observations'][0])
            for x, y in zip(a['actions'], b['actions'], strict=True):
                self.assertEqual(x, y if x['kind'] == 'set' else {**y, 'participants': y['participants'][::-1]})

    def test_table_oracle_handles_set_then_ambiguous_contact_then_feedback(self):
        case = {'episode': 'synthetic', 'ids': ['c', 'a', 'b'],
            'observations': [{'a': 0, 'b': 0, 'c': 1}, {'a': 1, 'b': 0, 'c': 1},
                             {'a': 1, 'b': 1, 'c': 1}, {'a': 1, 'b': 1, 'c': 0}],
            'actions': [d._set('a', 1), {'kind': 'contact', 'participants': ['a', 'b']}, d._set('c', 0)],
            'coverage': [['a', 'b', 'c']] * 3}
        rows = d.forecast_episode(case, 'nand')
        self.assertEqual([r['possible_worlds'] for r in rows], [[5], [5, 7], [6]])
        self.assertEqual(rows[1]['probabilities'], [.5, .5]); self.assertEqual(rows[2]['surviving_modes'], [0])
        altered = deepcopy(case); altered['observations'][2] = {'a': 1, 'b': 0, 'c': 1}
        altered['observations'][3] = {'a': 1, 'b': 0, 'c': 0}
        other = d.forecast_episode(altered, 'nand')
        self.assertEqual(rows[:2], other[:2]); self.assertEqual(other[2]['possible_worlds'], [4])

    def test_strict_inputs_and_oracle_contradictions_fail(self):
        case = deepcopy(self.assets['train']['episodes'][0]); case['truth'] = []
        with self.assertRaises(ValueError): d.forecast_episode(case, 'nand')
        case.pop('truth'); a = case['actions'][0]
        case['observations'][1][a['participants'][0]] = 1 - a['value']
        with self.assertRaises(ValueError): d.forecast_episode(case, 'nand')
        with self.assertRaises(ValueError): d.forecast_episode(case, 'xor')

    def test_byte_reproducibility_without_any_model_execution(self):
        self.assertEqual(c.digest(self.assets), c.digest(d.build_assets()))


if __name__ == '__main__': unittest.main()
