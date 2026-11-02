"""Synthetic normalization invariants; no research tape or checkpoint reads."""
from copy import deepcopy
import unittest

import torch

from experiments.predictive_nucleus import effect_role_neutral as model
from experiments.predictive_nucleus import effect_role_model as prior
from experiments.predictive_nucleus import effect_role_run as historical
from experiments.predictive_nucleus.bilingual_model import tokenize_batch
from experiments.predictive_nucleus.binding_layout_coordinates import coordinate_encoder
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint


class EffectRoleNeutralTests(unittest.TestCase):
    def setUp(self):
        self.parent = coordinate_encoder(7)
        self.features, _ = tokenize_batch(
            ['Ada novel Ben', 'Ben Ada novel', 'novel Ada Ben'], [['Ada', 'Ben', 'Cé']] * 3)

    def test_initialization_preserves_all_inherited_bytes_and_adds_four_zero_scalars(self):
        before, rng = fingerprint(self.parent.state_dict()), torch.random.get_rng_state()
        net = model.encoder(23, self.parent.state_dict())
        copied = 0
        for name, old in self.parent.state_dict().items():
            new = net.state_dict()[name]
            inherited = new[:2] if name.startswith('order.') else new
            self.assertEqual(inherited.numpy().tobytes(), old.numpy().tobytes())
            copied += old.numel()
            if name.startswith('order.'):
                self.assertEqual(new[2:].numpy().tobytes(), torch.zeros_like(new[2:]).numpy().tobytes())
        self.assertEqual((copied, sum(p.numel() for p in net.parameters())), (88, 92))
        self.assertEqual(fingerprint(self.parent.state_dict()), before)
        self.assertTrue(torch.equal(torch.random.get_rng_state(), rng))
        raw = prior.encoder(23, self.parent.state_dict())
        self.assertEqual(fingerprint(net.state_dict()), fingerprint(raw.state_dict()))

    def test_initial_family_and_direction_probabilities_preserve_parent_conditional(self):
        net = model.encoder(7, {k: v.tolist() for k, v in self.parent.state_dict().items()})
        logp = net(self.features); probabilities = logp.exp()
        torch.testing.assert_close(probabilities[:, :2].sum(-1), torch.full((3,), .5, dtype=DTYPE), atol=1e-14, rtol=0.)
        torch.testing.assert_close(probabilities[:, 2:], torch.full((3, 2), .25, dtype=DTYPE), atol=1e-14, rtol=0.)
        conditional = logp[:, :2] - logp[:, :2].logsumexp(-1, keepdim=True)
        torch.testing.assert_close(conditional, self.parent(self.features), atol=1e-14, rtol=0.)
        torch.testing.assert_close(logp.logsumexp(-1), torch.zeros(3, dtype=DTYPE), atol=1e-14, rtol=0.)

    def test_common_old_logit_shift_is_irrelevant_with_nonzero_new_parameters(self):
        net = model.encoder(7, self.parent.state_dict())
        with torch.no_grad():
            net.order.weight[2:, 0, 0].copy_(torch.tensor([-.7, .9], dtype=DTYPE))
            net.order.bias[2:].copy_(torch.tensor([.2, -.4], dtype=DTYPE))
        shifted = deepcopy(net)
        with torch.no_grad():
            shifted.order.weight[:2].add_(3.75)
            shifted.order.bias[:2].add_(17.)
        torch.testing.assert_close(shifted(self.features), net(self.features), atol=1e-14, rtol=0.)
        # Family probability is learned after initialization, not fixed forever.
        self.assertGreater(float((net(self.features)[:, 2:].exp().sum(-1) - .5).abs().max().detach()), .01)

    def test_extreme_inherited_logits_leave_finite_informative_endpoint_gradient(self):
        state = deepcopy(self.parent.state_dict())
        state['order.weight'].zero_(); state['order.bias'].copy_(torch.tensor([1000., -1000.], dtype=DTYPE))
        net = model.encoder(7, state)
        logp = net(self.features[:1])
        likelihood = torch.tensor([[.0003, .0003, .998, .0003]], dtype=DTYPE).log()
        loss = -(logp + likelihood).logsumexp(-1).mean()
        gradients = torch.autograd.grad(loss, tuple(net.parameters()))
        self.assertTrue(bool(torch.isfinite(loss)))
        self.assertTrue(all(bool(torch.isfinite(g).all()) for g in gradients))
        bias_gradient = dict(zip(dict(net.named_parameters()), gradients, strict=True))['order.bias']
        self.assertLess(float(bias_gradient[2]), -.7)
        self.assertGreater(float(bias_gradient[3]), .2)
        torch.testing.assert_close(logp[:, 2:].exp(), torch.full((1, 2), .25, dtype=DTYPE), atol=1e-14, rtol=0.)

    def test_arm_selection_retains_exact_text_only_initialization_and_rng(self):
        before = torch.random.get_rng_state()
        for arm in ('grounded', 'parser'):
            self.assertIsInstance(model.learner(arm, 7, self.parent.state_dict()), model.ProbabilityNeutralEncoder)
        actual = model.learner('text_only', 7, self.parent.state_dict())
        expected = historical.learner('text_only', 7, self.parent.state_dict())
        self.assertEqual(fingerprint(actual.state_dict()), fingerprint(expected.state_dict()))
        self.assertEqual(sum(p.numel() for p in actual.parameters()), 1048)
        self.assertTrue(torch.equal(torch.random.get_rng_state(), before))

    def test_invalid_parent_seed_arm_and_nonfinite_scores_fail(self):
        bad = deepcopy(self.parent.state_dict()); bad['order.bias'][0] = torch.nan
        with self.assertRaises(ValueError): model.encoder(7, bad)
        with self.assertRaises(ValueError): model.learner('grounded', True, self.parent.state_dict())
        with self.assertRaises(ValueError): model.learner('unknown', 7, self.parent.state_dict())
        net = model.encoder(7, self.parent.state_dict())
        with torch.no_grad(): net.order.bias[2] = torch.inf
        with self.assertRaisesRegex(ValueError, 'nonfinite'): net(self.features)


if __name__ == '__main__': unittest.main()
