"""Model-boundary and prequential checks without a physical simulator or TEST data."""
import unittest

import numpy as np
import torch

from experiments.predictive_nucleus.temporal_native_models_v1 import Model, collect, fit, fingerprint, receipt


def examples(size=3):
    query = torch.zeros(size, 41, dtype=torch.float64)
    # Strictly positive, distinct native rows make every synthetic answer legal.
    rows = torch.arange(1, 33, dtype=torch.float64).reshape(4, 8)
    rows /= rows.sum(-1, keepdim=True)
    query[:, :32] = rows.flatten()
    query[:, 32:35] = torch.tensor([1., 0., 1.])
    query[:, 35] = query[:, 39] = 1.
    data = {'base': receipt(query, 3, 'claim')[:, None].repeat(1, 9, 1).numpy()}
    for name in ('first', 'second', 'target', 'protected'):
        data[name + '_q'] = query.clone().numpy()
        data[name + '_y'] = np.arange(size, dtype=np.int64) % 8
    data['protected_q'][:, 39:41] = [0., 1.]
    return data


class TemporalNativeModels(unittest.TestCase):
    def test_parameter_budget_shared_initialization_and_rng_isolation(self):
        rng = torch.random.get_rng_state().clone()
        native, flat = Model('native', 7), Model('flat', 7)
        self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))
        self.assertEqual([sum(p.numel() for p in model.parameters()) for model in (native, flat)], [1108, 1144])
        for name, value in native.state_dict().items():
            self.assertEqual(value.dtype, torch.float64)
            if not name.startswith('output.'):
                self.assertTrue(torch.equal(value, flat.state_dict()[name]))
        self.assertEqual(fingerprint(native), fingerprint(Model('native', 7)))
        self.assertNotEqual(fingerprint(native), fingerprint(Model('native', 11)))

    def test_receipt_uses_observed_endpoint_and_rejects_boolean_or_invalid_ids(self):
        query = examples()['first_q']
        encoded = receipt(query, [0, 5, 7], 'claim')
        self.assertEqual(tuple(encoded.shape), (3, 18))
        self.assertEqual(encoded[:, 4:7].tolist(), [[0., 0., 0.], [1., 0., 1.], [1., 1., 1.]])
        self.assertEqual(encoded[:, 14:16].tolist(), [[0., 1.]] * 3)
        self.assertTrue(torch.equal(encoded[:, :4], torch.as_tensor(query[:, :32]).reshape(3, 4, 8)[torch.arange(3), :, [0, 5, 7]]))
        self.assertTrue(torch.equal(receipt(query[1], 5, 'claim'), encoded[1]))
        for answer in (True, [False] * 3, 1., -1, 8):
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                receipt(query, answer)
        invalid = examples()
        invalid['second_y'] = np.ones(3, dtype=bool)
        with self.assertRaisesRegex(ValueError, 'non-boolean integers'):
            collect(Model('native', 7), invalid)

    def test_prediction_uses_recurrent_evidence_and_trains_all_parameter_groups(self):
        data = examples()
        for arm in ('native', 'flat'):
            model = Model(arm, 7)
            state = model.history(data['base'])
            probabilities = model.predict(state, data['target_q'])
            self.assertTrue(torch.allclose(probabilities.sum(-1), torch.ones(3, dtype=torch.float64)))
            self.assertFalse(torch.equal(probabilities, model.predict(model.initial(3), data['target_q'])))
            loss = -probabilities[:, 0].log().mean()
            loss.backward()
            for name, parameter in model.named_parameters():
                self.assertIsNotNone(parameter.grad, name)
                self.assertTrue(torch.isfinite(parameter.grad).all(), name)
                self.assertGreater(parameter.grad.abs().sum().item(), 0., name)

    def test_pre_answer_branches_do_not_read_actual_answer_or_target(self):
        data, changed = examples(), examples()
        changed['second_y'] = (changed['second_y'] + 1) % 8
        changed['target_y'] = (changed['target_y'] + 4) % 8
        model = Model('native', 23)
        original, modified = collect(model, data, chunk=2), collect(model, changed, chunk=2)
        for branch in (None, 'cleared'):
            left, right = (original, modified) if branch is None else (original[branch], modified[branch])
            for field in ('q2distribution', 'pretarget', 'branches', 'tower_residual', 'question_value', 'question_asks'):
                self.assertTrue(torch.equal(left[field], right[field]), (branch, field))
            self.assertFalse(left['question_asks'][:, 1:].any())
            self.assertEqual(left['question_asks'].dtype, torch.bool)
            self.assertFalse(torch.equal(left['after_second'], right['after_second']))
        self.assertEqual(tuple(original['branches'].shape), (3, 8, 8))
        expected = original['branches'][torch.arange(3), torch.as_tensor(data['second_y'])]
        self.assertTrue(torch.allclose(expected, original['after_second'], atol=1e-15, rtol=0))

    def test_prefix_and_cleared_forecasts_ignore_the_first_answer(self):
        data, changed = examples(), examples()
        changed['first_y'] = (changed['first_y'] + 2) % 8
        model = Model('flat', 37)
        first, second = collect(model, data), collect(model, changed)
        self.assertTrue(torch.equal(first['base_target'], second['base_target']))
        for field in first['cleared']:
            self.assertTrue(torch.equal(first['cleared'][field], second['cleared'][field]), field)
        self.assertFalse(torch.equal(first['after_first'], second['after_first']))

    def test_synthetic_fits_have_identical_exposure_and_six_loss_terms(self):
        data = examples(5)
        receipts = [fit(Model(arm, 7), data, 7, steps=2) for arm in ('native', 'flat')]
        self.assertEqual(receipts[0]['minibatch_sha256'], receipts[1]['minibatch_sha256'])
        for result in receipts:
            self.assertEqual(result['sampled_episodes'], 256)
            self.assertEqual(result['forecast_terms'], 1536)
            self.assertNotEqual(result['initial_sha256'], result['final_sha256'])
            for step in result['losses']:
                self.assertEqual(len(step['forecast_nll']), 6)
                self.assertAlmostEqual(step['mean_nll'], sum(step['forecast_nll'].values()) / 6)


if __name__ == '__main__':
    unittest.main()
