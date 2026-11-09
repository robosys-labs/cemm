"""Synthetic objective and inference checks; never loads the real TRAIN bank."""
from hashlib import sha256
import unittest

import numpy as np
import torch

from experiments.predictive_nucleus import prefix_protection_train_v1 as candidate
from experiments.predictive_nucleus import temporal_native_models_v1 as original
from experiments.predictive_nucleus.tests.test_temporal_native_models_v1 import examples


class PrefixProtectionTrain(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_final_only_matches_original_fingerprints_exposure_and_every_loss_exactly(self):
        for arm in ('native', 'flat'):
            with self.subTest(arm=arm):
                first, second = original.Model(arm, 7), original.Model(arm, 7)
                baseline = original.fit(first, examples(5), 7, steps=4)
                result = candidate.fit(second, examples(5), 7, steps=4, final_only=True)
                for name in ('initial_sha256', 'final_sha256', 'minibatch_sha256', 'losses',
                             'parameters', 'updates', 'sampled_episodes', 'forecast_terms'):
                    self.assertEqual(result[name], baseline[name], name)

    def test_horizon_inventory_matches_flat_global_sequence(self):
        observed = torch.cat([candidate.horizons(step) for step in range(256)])
        self.assertEqual(observed.tolist(), [i % 3 for i in range(32768)])
        self.assertEqual(torch.bincount(observed).tolist(), [10923, 10923, 10922])
        self.assertTrue(torch.equal(candidate.horizons(3, final_only=True), torch.full((128,), 2)))

    def test_both_arms_receive_same_tensors_minibatches_and_horizons_without_input_mutation(self):
        data = examples(5)
        saved = {name: value.copy() for name, value in data.items()}
        reports = [candidate.fit(original.Model(arm, 23), data, 23, steps=3) for arm in ('native', 'flat')]
        for name in ('input_tensors_sha256', 'minibatch_sha256', 'horizon_sha256', 'horizon_counts'):
            self.assertEqual(reports[0][name], reports[1][name])
        expected = sha256()
        for step in range(3):
            expected.update(candidate.encoded([(step * 128 + i) % 3 for i in range(128)]))
        self.assertEqual(reports[0]['horizon_sha256'], expected.hexdigest())
        self.assertEqual(reports[0]['horizon_counts'], [128, 128, 128])
        for name in data:
            self.assertTrue(np.array_equal(data[name], saved[name]), name)
        for result in reports:
            self.assertEqual(result['forecast_terms'], 3 * 128 * 6)
            for step in result['losses']:
                self.assertEqual(len(step['forecast_nll']), 6)
                self.assertAlmostEqual(step['mean_nll'], sum(step['forecast_nll'].values()) / 6)

    def test_distributed_loss_changes_training_relative_to_final_only(self):
        a, b = original.Model('native', 11), original.Model('native', 11)
        distributed = candidate.fit(a, examples(5), 11, steps=2)
        fixed = candidate.fit(b, examples(5), 11, steps=2, final_only=True)
        self.assertEqual(distributed['minibatch_sha256'], fixed['minibatch_sha256'])
        for name in original.FORECASTS[:5]:
            self.assertEqual(distributed['losses'][0]['forecast_nll'][name], fixed['losses'][0]['forecast_nll'][name])
        self.assertNotEqual(distributed['losses'][0]['forecast_nll']['protected'], fixed['losses'][0]['forecast_nll']['protected'])
        self.assertNotEqual(distributed['final_sha256'], fixed['final_sha256'])

    def test_inference_ignores_target_labels_and_future_answers_until_delivered(self):
        for arm in ('native', 'flat'):
            data, modified = examples(), examples()
            modified['target_y'] = (modified['target_y'] + 3) % 8
            modified['protected_y'] = (modified['protected_y'] + 4) % 8
            model = original.Model(arm, 37)
            initial = original.fingerprint(model)
            first = candidate.predictions(model, data)
            self.assertEqual(first, candidate.predictions(model, modified))
            modified['second_y'] = (modified['second_y'] + 1) % 8
            changed = candidate.predictions(model, modified)
            for stage in ('teaching', 'claim', 'first'):
                self.assertEqual(first[stage], changed[stage])
            self.assertNotEqual(first['second'], changed['second'])
            self.assertEqual(original.fingerprint(model), initial)
            self.assertTrue(all(p.grad is None for p in model.parameters()))


if __name__ == '__main__':
    unittest.main()
