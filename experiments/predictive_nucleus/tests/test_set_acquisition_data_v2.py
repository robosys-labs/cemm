"""V2 data lineage/schema invariants; no model, fitting or research forecasts."""
from collections import Counter
from copy import deepcopy
import subprocess
import sys
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import set_acquisition_data_v2 as d
from experiments.predictive_nucleus.set_acquisition_scoring import _inventory


class SetAcquisitionDataV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.assets = d.build_assets()

    def test_training_is_exact_reused_observation_tape(self):
        train = self.assets['train']
        self.assertEqual(train, d.io._read(d.ROOT / d.TRAIN))
        self.assertEqual(d.io._hash(d.ROOT / d.TRAIN), d.TRAIN_SHA256)
        counts = Counter((e['observations'][0][e['actions'][0]['participants'][0]], e['actions'][0]['value'])
                         for e in train['episodes'])
        self.assertEqual(counts, Counter({(0, 0): 12, (0, 1): 12, (1, 0): 12, (1, 1): 12}))
        with patch.object(d.io, '_hash', return_value='changed'):
            with self.assertRaisesRegex(ValueError, 'training tape differs'): d.build_assets()

    def test_native_matrix_and_unchanged_information_schema(self):
        for law, bundle in self.assets['laws'].items():
            self.assertEqual(bundle['information']['version'], 'set-acquisition-v1-information')
            planned, pairs = _inventory(bundle)
            self.assertEqual((len(planned), len(pairs)), (1920, 128))
            self.assertEqual(self.assets['audit'][law]['families'],
                {'interleaved_set': 64, 'rotating_set': 64, 'contact_set_feedback': 256})
            self.assertEqual(self.assets['audit'][law]['identifiable_points'], 1664)
            self.assertEqual(self.assets['audit'][law]['ambiguous_points'], 256)
            self.assertTrue(all(len(e['actions']) == 5 for e in bundle['inputs']['episodes']))
            self.assertEqual(bundle['oracle']['source_sha256'], d.source_digest())
            self.assertEqual(bundle['information']['information_law_sha256'], d.law_digest(law))

    def test_actual_prefix_support_matches_independent_boolean_step(self):
        for law, bundle in self.assets['laws'].items():
            for case, meta, info in zip(bundle['inputs']['episodes'], bundle['cases'],
                                       bundle['information']['episodes'], strict=True):
                state = dict(case['observations'][0]); ids = sorted(case['ids'])
                for t, (action, expected) in enumerate(zip(case['actions'], info['forecasts'], strict=True)):
                    members = action['participants']
                    if action['kind'] == 'set': state[members[0]] = action['value']
                    else:
                        mode = meta['hidden_source_slot']; source, target = members[mode], members[1 - mode]
                        state[target] = int(not (state[source] and state[target])) if law == 'nand' else int(
                            not (state[source] or state[target]))
                    self.assertEqual(case['observations'][t + 1], state)
                    world = sum(state[name] << (len(ids) - i - 1) for i, name in enumerate(ids))
                    self.assertIn(world, expected['possible_worlds'])
                    self.assertEqual(sum(expected['probabilities']), 1.)

    def test_new_templates_are_disjoint_from_training_and_listed_opened_native_banks(self):
        audit = self.assets['audit']
        self.assertEqual(audit['split_overlap'], {'blueprint': 0, 'template': 0, 'identity': 0})
        self.assertEqual(set(audit['historical_overlap']), set(d.HISTORY))
        for name, row in audit['historical_overlap'].items():
            self.assertEqual(row['sha256'], d.io._hash(d.ROOT / name))
            self.assertTrue(all(row[k] == 0 for k in ('blueprint', 'template', 'identity')))
        self.assertEqual(audit['atomic_set_tuples']['train'], audit['atomic_set_tuples']['evaluation'])
        self.assertEqual(audit['atomic_set_tuples']['novel_atomic_tuples'], [])

    def test_identity_renaming_and_global_reversal_cannot_fake_template_freshness(self):
        bank = self.assets['laws']['nand']
        case = deepcopy(next(e for e, m in zip(bank['inputs']['episodes'], bank['cases'], strict=True)
                             if m['family'] == 'contact_set_feedback'))
        renamed = deepcopy(case); names = {name: 'renamed_' + str(i) for i, name in enumerate(case['ids'])}
        renamed['ids'] = [names[i] for i in case['ids']]
        renamed['observations'] = [{names[i]: v for i, v in row.items()} for row in case['observations']]
        renamed['coverage'] = [[names[i] for i in row] for row in case['coverage']]
        for action in renamed['actions']:
            action['participants'] = [names[i] for i in action['participants']]
            if action['kind'] == 'contact': action['participants'].reverse()
        self.assertEqual(d._overlap([case], [renamed]), {'blueprint': 1, 'template': 1, 'identity': 0})

    def test_law_twins_share_design_but_not_outcome_authority(self):
        a, b = [self.assets['laws'][law] for law in d.LAWS]
        self.assertNotEqual(a['oracle']['information_law_sha256'], b['oracle']['information_law_sha256'])
        self.assertTrue(any(x['observations'] != y['observations'] for x, y in
                            zip(a['inputs']['episodes'], b['inputs']['episodes'], strict=True)))
        for x, y in zip(a['inputs']['episodes'], b['inputs']['episodes'], strict=True):
            self.assertTrue(all(x[k] == y[k] for k in ('episode', 'ids', 'actions', 'coverage')))
            self.assertEqual(x['observations'][0], y['observations'][0])

    def test_repeat_preparation_is_deterministic_without_model_import(self):
        self.assertEqual(d.c.digest(self.assets), d.c.digest(d.build_assets()))
        subprocess.run([sys.executable, '-c', 'import sys; '
            'import experiments.predictive_nucleus.set_acquisition_data_v2; '
            'assert "torch" not in sys.modules; '
            'assert "experiments.predictive_nucleus.set_acquisition_fit" not in sys.modules'], check=True)


if __name__ == '__main__': unittest.main()
