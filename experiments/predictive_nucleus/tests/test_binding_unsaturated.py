"""Synthetic ablation invariants, not evidence of repaired structural transfer."""
import unittest

import torch

from experiments.predictive_nucleus.binding_model import encoder, factor_inputs
from experiments.predictive_nucleus.binding_unsaturated import unsaturated_encoder
from experiments.predictive_nucleus.bilingual_model import tokenize_batch, combine
from experiments.predictive_nucleus.joint_objective import fingerprint


class UnsaturatedBindingTests(unittest.TestCase):
    def features(self):
        return tokenize_batch(['A amber B', 'B A indigo', 'violet B A'], [['A', 'B', 'C']] * 3)[0]

    def test_exact_paired_initialization_and_original_rng(self):
        before = torch.get_rng_state().clone()
        for seed in (7, 11, 23, 37, 53):
            old, new = encoder('factor', seed), unsaturated_encoder(seed)
            self.assertEqual(fingerprint(old.state_dict()), fingerprint(new.state_dict()))
            self.assertEqual(sum(p.numel() for p in new.parameters()), 89)
        self.assertTrue(torch.equal(before, torch.get_rng_state()))

    def test_forward_is_only_the_two_terminal_tanh_ablation(self):
        model, x = unsaturated_encoder(7), self.features()
        content, layout = factor_inputs(x)
        expected = model.order(model.lexical[2](model.lexical[1](model.lexical[0](content))),
                               model.layout[0](layout)).log_softmax(-1)
        self.assertTrue(torch.equal(model(x), expected))
        self.assertTrue(torch.allclose(model(x).exp().sum(-1), torch.ones(3, dtype=torch.float64)))

    def test_output_bottleneck_gradient_is_not_forced_to_zero(self):
        old, new = encoder('factor', 7), unsaturated_encoder(7)
        with torch.no_grad():
            for model in (old, new):
                model.lexical[2].weight.zero_(); model.lexical[2].bias.fill_(30.)
                model.layout[0].weight.zero_(); model.layout[0].bias.fill_(1.)
                model.order.weight.zero_(); model.order.weight[0, 0, 0] = 1.; model.order.bias.zero_()
        # Synthetic opposite outcome: no word/order teaching in a research fit.
        (-old(self.features())[:, 1].mean()).backward()
        (-new(self.features())[:, 1].mean()).backward()
        self.assertEqual(old.lexical[2].bias.grad.item(), 0.)
        self.assertGreater(new.lexical[2].bias.grad.item(), .99)

    def test_same_outcome_marginalization_path_accepts_the_candidate(self):
        model = unsaturated_encoder(11)
        options = torch.full((3, 2, 2, 8), -torch.log(torch.tensor(16., dtype=torch.float64)), dtype=torch.float64)
        raw, pending = combine(model(self.features()), options)
        self.assertEqual(tuple(pending.shape), (3, 2, 8))
        self.assertTrue(torch.allclose(raw.exp().sum(-1), torch.ones(3, dtype=torch.float64)))

    def test_checkpoint_roundtrip_is_explicit_and_leaves_source_unchanged(self):
        source, target = unsaturated_encoder(23), unsaturated_encoder(37)
        before = fingerprint(source.state_dict())
        target.load_state_dict({k: v.clone() for k, v in source.state_dict().items()}, strict=True)
        self.assertEqual(before, fingerprint(source.state_dict()))
        self.assertTrue(torch.equal(source(self.features()), target(self.features())))

    def test_roster_renaming_has_no_effect(self):
        renamed = tokenize_batch(['X amber Y', 'Y X indigo', 'violet Y X'], [['X', 'Y', 'Z']] * 3)[0]
        model = unsaturated_encoder(53)
        self.assertTrue(torch.equal(model(self.features()), model(renamed)))

    def test_nonfinite_logits_fail_explicitly(self):
        model = unsaturated_encoder(7)
        with torch.no_grad(): model.order.bias.fill_(float('inf'))
        with self.assertRaisesRegex(ValueError, 'nonfinite'): model(self.features())

    def test_seed_and_feature_validation_preserved(self):
        for seed in (True, -1, 2 ** 63, 1.2):
            with self.assertRaises(ValueError): unsaturated_encoder(seed)
        with self.assertRaises(ValueError): unsaturated_encoder(7)(torch.zeros((1, 3, 9), dtype=torch.float64))


if __name__ == '__main__': unittest.main()
