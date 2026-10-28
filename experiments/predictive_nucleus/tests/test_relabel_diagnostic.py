"""Synthetic-only tests: these never fit a model or score the public fixture."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from experiments.predictive_nucleus.causal_replay import DevelopmentHistory
from experiments.predictive_nucleus.development_run import MODEL_NAMES, score_forecast
from experiments.predictive_nucleus.relabel_diagnostic import _evaluate_case, compare_forecasts, rename_history, to_original


class RelabelDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.ids = ('a', 'b', 'c')
        self.mapping = {'a': 'c', 'b': 'a', 'c': 'b'}
        self.history = DevelopmentHistory(
            ((('b', 0), ('c', 1), ('a', 0)), (('b', 1), ('a', 0)), (('c', 1),)),
            (('contact', ('a', 'b'), None), ('observe', (), None)))

    def test_history_bijection_preserves_measurement_and_role_order(self):
        renamed = rename_history(self.history, self.mapping)
        self.assertEqual(renamed._observations[0], (('a', 0), ('b', 1), ('c', 0)))
        self.assertEqual(renamed._action_records[0], ('contact', ('c', 'a'), None))
        self.assertEqual(rename_history(renamed, {v: k for k, v in self.mapping.items()}), self.history)
        for bad in ({'a': 'a', 'b': 'a', 'c': 'c'}, {'a': 'b', 'b': 'a'},
                    {'a': 'd', 'b': 'a', 'c': 'b'}):
            with self.assertRaises(ValueError):
                rename_history(self.history, bad)

    def test_permuted_world_coordinates_and_tv(self):
        # Original world (1,0,0) becomes sorted-renamed order (0,0,1).
        self.assertEqual(to_original({(0, 0, 1): 1.0}, self.ids, self.mapping), {(1, 0, 0): 1.0})
        original = ('PREDICTED', None, {(1, 0, 0): .7, (0, 1, 0): .3})
        equivariant = ('PREDICTED', None, {(0, 0, 1): .7, (1, 0, 0): .3})
        result = compare_forecasts(original, equivariant, self.ids, self.mapping, (1, 0, 0))
        self.assertEqual(result['tv'], 0.0)
        self.assertFalse(result['map_changed'])
        self.assertTrue(result['correct_renamed'])
        changed = ('PREDICTED', None, {(0, 0, 1): .4, (1, 0, 0): .6})
        result = compare_forecasts(original, changed, self.ids, self.mapping, (1, 0, 0))
        self.assertAlmostEqual(result['tv'], .3)
        self.assertTrue(result['map_changed'])
        self.assertFalse(result['correct_renamed'])

    def test_equal_distribution_can_change_lexical_map_on_tie(self):
        original = ('PREDICTED', None, {(1, 0, 0): .5, (0, 1, 0): .5})
        renamed = ('PREDICTED', None, {(0, 0, 1): .5, (1, 0, 0): .5})
        result = compare_forecasts(original, renamed, self.ids, self.mapping, (0, 1, 0))
        self.assertEqual(result['tv'], 0.0)
        self.assertTrue(result['original_map_tied'])
        self.assertTrue(result['renamed_map_tied'])
        self.assertTrue(result['map_changed'])
        self.assertTrue(result['correct_original'])
        self.assertFalse(result['correct_renamed'])

    def test_all_replays_finish_before_any_truth_read(self):
        calls = []
        forecast = ('PREDICTED', None, {(0, 0, 0): 1.0})
        score = score_forecast(*forecast, (0, 0, 0))
        archived = {'public_history': [], 'steps': [{'truth': [0, 0, 0],
                      'models': {name: score for name in MODEL_NAMES}} for _ in range(5)]}

        class Episode:
            def gold_after(self, step):
                self_test.assertEqual(calls, ['replay'] * 7)
                return {'a': 0, 'b': 0, 'c': 0}

        self_test = self
        def replay(*args):
            calls.append('replay')
            return tuple(SimpleNamespace(history=[], forecasts=[forecast] * 5) for _ in MODEL_NAMES)

        with patch('experiments.predictive_nucleus.relabel_diagnostic.sensor_view'), \
             patch.object(DevelopmentHistory, 'from_sensor_view', return_value=self.history), \
             patch('experiments.predictive_nucleus.relabel_diagnostic._replay', side_effect=replay):
            rows, matched, history_matched = _evaluate_case(Episode(), archived, None, None, None)
        self.assertEqual(len(rows), 30)
        self.assertEqual(matched, 20)
        self.assertEqual(history_matched, 1)

    def test_abstentions_and_asymmetric_status_are_not_zero_probabilities(self):
        abstain = ('ABSTAIN', 'NO_MEMORY', None)
        predict = ('PREDICTED', None, {(0, 0, 0): 1.0})
        result = compare_forecasts(abstain, predict, self.ids, self.mapping, (0, 0, 0))
        self.assertIsNone(result['tv'])
        self.assertIsNone(result['original_world_probabilities'])
        self.assertEqual(sum(p['probability'] for p in result['renamed_world_probabilities_mapped_back']), 1.0)
        result = compare_forecasts(predict, abstain, self.ids, self.mapping, (0, 0, 0))
        self.assertIsNone(result['renamed_world_probabilities_mapped_back'])
        self.assertIsNone(result['correct_renamed'])


if __name__ == '__main__':
    unittest.main()
