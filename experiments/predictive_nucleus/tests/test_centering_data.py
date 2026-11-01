"""Generator invariants only; no learned checkpoint is fitted or evaluated."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import centering_data as data, binding_scoring as scoring
from experiments.predictive_nucleus import continuation_run as io
from experiments.predictive_nucleus.bilingual_contract import validate_inputs


class CenteringDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = data.build_assets()

    def test_preserves_exact_training_bytes_and_prescribed_inventory(self):
        self.assertEqual(self.assets['train'], io._read(data.TRAINING))
        with tempfile.TemporaryDirectory() as folder:
            copied = Path(folder) / 'train.json.xz'; io._write(copied, self.assets['train'])
            self.assertEqual(copied.read_bytes(), data.TRAINING.read_bytes())
        audit = self.assets['audit']
        self.assertEqual(audit['training_file_sha256'], io._hash(data.TRAINING))
        self.assertEqual((audit['train_forecasts'], audit['challenge_episodes_per_law'],
                          audit['challenge_forecasts_per_law']), (1152, 384, 1728))
        self.assertEqual(self.assets, data.build_assets())

    def test_novelty_ignores_names_directions_and_inactive_slots(self):
        original = data.previous.SCHEDULES['diamond4'][1]
        relabeled = tuple((9 - b, 9 - a) for a, b in original)
        self.assertEqual(data.ordered_shape(original), data.ordered_shape(relabeled))
        with self.assertRaisesRegex(ValueError, 'previously opened'):
            data.novelty({'renamed': (6, relabeled)})
        with patch.object(data, 'SCHEDULES', {'renamed': (4, original)}), \
             self.assertRaisesRegex(ValueError, 'previously opened'):
            data.build_assets()
        self.assertEqual(len(data.novelty(data.SCHEDULES)['new_ordered_shapes']), 2)

    def test_training_withheld_cells_are_not_claimed_as_new_lexical_cells(self):
        audit = self.assets['audit']
        self.assertEqual(audit['new_words'], [])
        self.assertEqual(audit['new_lexical_layout_cells'], [])
        self.assertEqual(len(audit['training_withheld_cells']), 8)
        trained = set(map(tuple, audit['training_cells']))
        for law in ('nand', 'nor'):
            for gold in self.assets[law]['oracle']['episodes']:
                for cell in gold['cells']:
                    self.assertEqual(cell['held'], (cell['word'], cell['layout']) not in trained)

    def test_no_identity_or_episode_overlap_with_training_or_opened_banks(self):
        challenge = self.assets['nand']['inputs']['episodes']
        ids = {r['id'] for r in challenge}
        names = {n for r in challenge for n in r['entities']}
        self.assertEqual(len(ids), 384)
        for folder in ('bilingual-v1', 'lexical-v1', 'binding-v1', 'saturation-v1'):
            for name in ('train-inputs.json.xz', 'nand-inputs.json.xz'):
                records = io._read(io.ROOT / 'data' / folder / name)['episodes']
                self.assertFalse(ids & {r['id'] for r in records})
                self.assertFalse(names & {n for r in records for n in r['entities']})

    def test_independent_oracle_checks_every_context_and_role_lexical_pair(self):
        for law in ('nand', 'nor'):
            records, gold, pairs = scoring.oracle(self.assets[law]['inputs'], self.assets[law]['oracle'], law)
            self.assertEqual(len(records), 384)
            self.assertEqual({k: len(v) for k, v in pairs.items()}, {'lexical': 192, 'role': 192})
            for case in gold.values():
                edges = [tuple(action[1:3]) for action in case['actions']]
                expected = data.SCHEDULES[case['family']][1]
                self.assertEqual(data.ordered_shape(edges), data.ordered_shape(expected))

    def test_rejects_changed_training_bytes_and_learner_gold_fields(self):
        with patch.object(io, '_hash', return_value='0' * 64), \
             self.assertRaisesRegex(ValueError, 'training bytes changed'):
            data.build_assets()
        bad = deepcopy(self.assets['train']); bad['episodes'][0]['action_orders'] = [0]
        with self.assertRaises(ValueError): validate_inputs(bad)


if __name__ == '__main__': unittest.main()
