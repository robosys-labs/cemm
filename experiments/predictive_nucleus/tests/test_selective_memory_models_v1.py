"""Synthetic invariants; never load a prepared study or fit a real seed bank."""
import copy
import unittest
import torch

from experiments.predictive_nucleus import selective_memory_models_v1 as learned


def synthetic():
    generator = torch.Generator().manual_seed(1019)
    size = 4
    def queries(words):
        rows = torch.rand(size, len(words[0]), 4, 8, generator=generator, dtype=torch.float64)
        rows /= rows.sum(-1, keepdim=True)
        values = torch.zeros(size, len(words[0]), 41, dtype=torch.float64)
        values[..., :32] = rows.flatten(-2)
        values[..., 32:35] = torch.randint(0, 2, (size, len(words[0]), 3), generator=generator)
        values[..., 36] = 1
        values[..., 38] = 1
        values[..., 39:41] = torch.nn.functional.one_hot(torch.tensor(words), 2)
        return values
    words = [[0, 1, 0, 1], [1, 0, 1, 0], [0, 1, 1, 0], [1, 0, 0, 1]]
    probes = queries(words)
    targets = queries([[0, 1]] * size)
    base_queries = queries([[index % 2 for index in range(10)]] * size)
    base_answers = torch.randint(0, 8, (size, 10), generator=generator)
    base = torch.stack([learned.receipt(base_queries[:, i], base_answers[:, i],
                                       'physical' if i < 8 else 'claim') for i in range(10)], 1)
    return {'base': base, 'probe_q': probes,
            'probe_y': torch.randint(0, 8, (size, 4), generator=generator),
            'target_q': targets, 'target_y': torch.randint(0, 8, (size, 2), generator=generator)}


class SelectiveMemoryModelTests(unittest.TestCase):
    def test_registered_inventory_seed_isolation_and_generic_initial_state(self):
        before = torch.random.get_rng_state().clone()
        for arm, count in learned.PARAMETERS.items():
            model = learned.Model(arm, 7)
            assert sum(p.numel() for p in model.parameters()) == count
            assert model.initial(3).numel() == 3 * 16
            assert learned.fingerprint(model) == learned.fingerprint(learned.Model(arm, 7))
            assert not torch.equal(model.initial_state.flatten()[:8], model.initial_state.flatten()[8:])
        assert torch.equal(before, torch.random.get_rng_state())


    def test_soft_slots_are_exchangeable_in_state_update_and_readout(self):
        model, data = learned.Model('selective', 11), synthetic()
        state = model.initial(4)
        observed = data['base'][:, 0]
        updated = model.receive(state, observed)
        permuted = model.receive(state.flip(1), observed)
        torch.testing.assert_close(permuted, updated.flip(1), atol=1e-14, rtol=0)
        query = data['target_q'][:, 0]
        torch.testing.assert_close(model.predict(updated, query), model.predict(permuted, query), atol=1e-14, rtol=0)
        attention = model._attention(state, model.write_key(observed))
        assert (attention > 0).all() and (attention < 1).all()
        assert ((updated - state).abs().sum(-1) > 0).all()


    def test_synthetic_fits_share_exposure_and_six_loss_terms(self):
        data, receipts = synthetic(), []
        for arm in learned.ARMS:
            model = learned.Model(arm, 23)
            receipts.append(learned.fit(model, data, 23, steps=2, synthetic=True))
        assert len({r['minibatch_sha256'] for r in receipts}) == 1
        for report in receipts:
            assert report['sampled_episodes'] == 256
            assert report['forecast_terms'] == 1536
            assert report['initial_sha256'] != report['final_sha256']
            assert set(report['losses'][0]['forecast_nll']) == set(learned.FORECASTS)
            for loss in report['losses']:
                self.assertAlmostEqual(loss['mean_nll'], sum(loss['forecast_nll'].values()) / 6, places=12)
        with self.assertRaisesRegex(ValueError, 'exactly 256'):
            learned.fit(learned.Model('native', 7), data, 7, steps=1)


    def test_collection_freezes_parameters_and_branches_precede_answers(self):
        for arm in learned.ARMS:
            with self.subTest(arm=arm):
                self._check_collection(arm)

    def _check_collection(self, arm):
        data, model = synthetic(), learned.Model(arm, 37)
        initial = learned.fingerprint(model)
        result = learned.collect(model, data, chunk=2)
        assert initial == learned.fingerprint(model)
        assert all(p.grad is None for p in model.parameters())
        for prefix in ('optional_', 'cleared_optional_'):
            branches = result[prefix + 'branches']
            actual = branches.gather(2, result['optional_y'][..., None, None].expand(-1, -1, 1, 8)).squeeze(2)
            torch.testing.assert_close(actual, result[prefix + 'after'], atol=1e-14, rtol=0)
            assert not result[prefix + 'asks'][..., 1:].any()
        changed = {key: value.clone() for key, value in data.items()}
        changed['probe_y'][:, 2:] = (changed['probe_y'][:, 2:] + 1) % 8
        changed['target_y'].fill_(99)  # Target labels are not even validated during inference.
        alternate = learned.collect(model, changed, chunk=2)
        for key in ('teaching', 'claims', 'pair', 'optional_probe', 'optional_before',
                    'optional_branches', 'optional_value', 'optional_asks',
                    'cleared_optional_probe', 'cleared_optional_before', 'cleared_optional_branches'):
            assert torch.equal(result[key], alternate[key]), key
        assert torch.equal(result['next_probe'][:, :3], alternate['next_probe'][:, :3])
        assert not torch.equal(result['final'], alternate['final'])


    def test_clearing_omits_exactly_first_pair_and_question_mapping_follows_observed_words(self):
        data, model = synthetic(), learned.Model('selective', 53)
        result = learned.collect(model, data)
        changed = copy.deepcopy(data)
        changed['probe_y'][:, :2] = (changed['probe_y'][:, :2] + 3) % 8
        alternate = learned.collect(model, changed)
        for key in result:
            if key.startswith('cleared_'):
                assert torch.equal(result[key], alternate[key]), key
        assert not torch.equal(result['pair'], alternate['pair'])
        for row in range(4):
            for word in range(2):
                index = next(i for i in (2, 3) if data['probe_q'][row, i, 39 + word] == 1)
                assert result['optional_y'][row, word] == data['probe_y'][row, index]


    def test_rejects_invalid_tensor_contract_without_fitting(self):
        data, model = synthetic(), learned.Model('flat', 7)
        data['probe_y'] = data['probe_y'].bool()
        with self.assertRaisesRegex(ValueError, 'non-boolean integers'):
            learned.collect(model, data)
        data = synthetic()
        data['probe_q'][:, 3, 39:41] = data['probe_q'][:, 2, 39:41]
        with self.assertRaisesRegex(ValueError, 'each observed word'):
            learned.collect(model, data)


if __name__ == '__main__':
    unittest.main()
