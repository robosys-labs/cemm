"""New study wiring only: no fitted model or scientific forecast is executed."""
from pathlib import Path
import tempfile
import unittest

from experiments.predictive_nucleus import coordinate_data as data, binding_scoring as scoring
from experiments.predictive_nucleus import continuation_run as io


class CoordinateDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = data.build_assets()

    def test_preserves_training_bytes_and_frozen_denominators(self):
        with tempfile.TemporaryDirectory() as folder:
            copied = Path(folder) / 'train.json.xz'; io._write(copied, self.assets['train'])
            self.assertEqual(copied.read_bytes(), data.TRAINING.read_bytes())
        audit = self.assets['audit']
        self.assertEqual((audit['train_forecasts'], audit['challenge_episodes_per_law'],
                          audit['challenge_forecasts_per_law']), (1152, 384, 1728))
        self.assertEqual(self.assets, data.build_assets())

    def test_rejects_opened_centering_shapes_even_after_role_and_entity_reversal(self):
        for name, (n, edges) in data.previous.SCHEDULES.items():
            renamed = tuple((n - 1 - b, n - 1 - a) for a, b in edges)
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'previously opened centering'):
                data.novelty({'changed-label': (n, renamed)})
        self.assertTrue({'centering-relay4', 'centering-fork_return5'} <=
                        set(self.assets['audit']['compared_opened_families']))

    def test_new_identity_inventory_excludes_every_opened_bank(self):
        fresh = self.assets['nand']['inputs']['episodes']
        ids = {r['id'] for r in fresh}; names = {n for r in fresh for n in r['entities']}
        for folder in ('bilingual-v1', 'lexical-v1', 'binding-v1', 'saturation-v1', 'centering-v1'):
            for filename in ('train-inputs.json.xz', 'nand-inputs.json.xz'):
                previous = io._read(io.ROOT / 'data' / folder / filename)['episodes']
                self.assertFalse(ids & {r['id'] for r in previous})
                self.assertFalse(names & {n for r in previous for n in r['entities']})

    def test_new_shapes_preserve_complete_oracles_and_pair_coverage(self):
        for law in ('nand', 'nor'):
            records, gold, pairs = scoring.oracle(self.assets[law]['inputs'], self.assets[law]['oracle'], law)
            self.assertEqual(len(records), 384)
            self.assertEqual({k: len(v) for k, v in pairs.items()}, {'lexical': 192, 'role': 192})
            for case in gold.values():
                edges = [tuple(action[1:3]) for action in case['actions']]
                self.assertEqual(data.previous.ordered_shape(edges),
                                 data.previous.ordered_shape(data.SCHEDULES[case['family']][1]))
        self.assertEqual(self.assets['audit']['new_words'], [])
        self.assertEqual(self.assets['audit']['new_lexical_layout_cells'], [])
        self.assertEqual(len(self.assets['audit']['training_withheld_cells']), 8)


if __name__ == '__main__': unittest.main()
