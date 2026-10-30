"""Mixed challenge design and oracle invariants; no learned weights or fitting."""
from collections import Counter, defaultdict
from copy import deepcopy
import unittest

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import mixed_composition_data as data
from experiments.predictive_nucleus.tests.test_prospective_oracle import reference


def config():
    return {'version': 'mixed-composition-data-tests-v1',
            'data': {'entity_counts': [3, 4, 5, 6], 'split_seed': 20261039999}}


class MixedCompositionDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = data.build_assets(config())
        cls.inputs = {row['episode']: row for row in cls.assets['inputs']['episodes']}
        cls.information = {row['episode']: row['forecasts'] for row in cls.assets['information']['episodes']}

    def test_exact_inventory_reproducibility_and_new_templates(self):
        settings = config(); before = deepcopy(settings)
        self.assertEqual(data.build_assets(settings), self.assets)
        self.assertEqual(settings, before)
        audit = self.assets['audit']
        self.assertEqual([audit[k] for k in ('physical_lineages', 'episode_views', 'role_pairs',
                         'planned_forecasts', 'contact_events', 'max_cumulative_missing_bits')],
                         [48, 192, 96, 800, 768, 2])
        self.assertEqual(audit['family_views'], dict.fromkeys(data.FAMILIES, 32))
        self.assertEqual(audit['identifiable_points'] + audit['ambiguous_points'], 800)
        for history in audit['historical_overlap'].values():
            self.assertTrue(contract.is_sha(history['sha256']))
            for partition in history['partitions'].values():
                self.assertEqual((partition['blueprint_overlap'], partition['template_overlap']), (0, 0))

    def test_independent_whole_history_oracle_and_observed_boundary(self):
        gold = {row['episode']: row for row in self.assets['oracle']['episodes']}
        for meta in self.assets['cases']:
            case = self.inputs[meta['episode']]
            self.assertEqual(set(case), {'episode', 'ids', 'observations', 'actions', 'coverage'})
            self.assertEqual(self.information[meta['episode']], reference(case))
            self.assertEqual(meta['query_steps'], list(range(len(case['actions']))))
            self.assertEqual(meta['contact_count'], sum(a['kind'] == 'contact' for a in case['actions']))
            self.assertIn(meta['contact_count'], (3, 4, 5))
            active = {name for action in case['actions'] for name in action['participants']}
            for name in set(case['ids']) - active:
                self.assertTrue(all(row[name] == case['observations'][0][name] for row in gold[meta['episode']]['truth']))
            missing = sum(value is None for row in case['observations'] for value in row.values())
            self.assertLessEqual(2 ** (missing + len(case['ids'])), 512)

    def test_mode_twins_share_design_and_role_pairs_are_complete(self):
        lineages, pairs = defaultdict(list), defaultdict(list)
        for meta in self.assets['cases']:
            lineages[meta['lineage']].append(meta); pairs[meta['pair_id']].append(meta)
        for rows in lineages.values():
            self.assertEqual(Counter((row['hidden_source_slot'], row['direction']) for row in rows),
                             Counter({(m, d): 1 for m in (0, 1) for d in (0, 1)}))
            self.assertEqual(len({data.blueprint_digest(self.inputs[row['episode']]) for row in rows}), 1)
            self.assertEqual(len({tuple(row['query_steps']) for row in rows}), 1)
        for rows in pairs.values():
            a, b = sorted(rows, key=lambda row: row['direction'])
            left, right = self.inputs[a['episode']], self.inputs[b['episode']]
            actions = deepcopy(left['actions'])
            for action in actions:
                if action['kind'] == 'contact': action['participants'].reverse()
            self.assertEqual(actions, right['actions'])
            self.assertEqual(left['observations'][0], right['observations'][0])
            self.assertEqual(a['hidden_source_slot'], b['hidden_source_slot'])

    def test_aliases_do_not_identify_mode_and_coalescence_does_not_erase_it(self):
        for meta in self.assets['cases']:
            rows, family = self.information[meta['episode']], meta['family']
            if family in ('alias_before_acquisition', 'repeated_alias'):
                count = 1 if family == 'alias_before_acquisition' else 2
                self.assertTrue(all(row['surviving_modes'] == [0, 1] for row in rows[:count + 1]))
                self.assertTrue(all(len(row['possible_worlds']) == 1 for row in rows[:count]))
                self.assertEqual(rows[count]['probabilities'], [.5, .5])
            elif family == 'withheld_alias':
                self.assertTrue(all(row['surviving_modes'] == [0, 1] for row in rows[:3]))
                self.assertTrue(all(row['probabilities'] == [.5, .5] for row in rows[:3]))
                self.assertTrue(all(row['surviving_modes'] == [meta['hidden_source_slot']] for row in rows[3:]))
            elif family == 'mode_coalescence':
                self.assertEqual([len(row['possible_worlds']) for row in rows[:4]], [2, 1, 1, 2])
                self.assertTrue(all(row['surviving_modes'] == [0, 1] for row in rows[:4]))
                self.assertEqual(rows[3]['probabilities'], [.5, .5])

    def test_invalid_design_rejected_without_silent_reduction(self):
        for key, value in [('entity_counts', []), ('entity_counts', [3, 3]),
                           ('entity_counts', [2]), ('split_seed', True), ('split_seed', 20261030040)]:
            settings = config(); settings['data'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError): data.build_assets(settings)


if __name__ == '__main__': unittest.main()
