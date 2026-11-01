"""Algebra and synthetic invariants only; no research fitting or held-bank reads."""
from copy import deepcopy
import unittest

import torch

from experiments.predictive_nucleus.binding_centered_init import centered_encoder
from experiments.predictive_nucleus.binding_layout_coordinates import coordinate_encoder
from experiments.predictive_nucleus.bilingual_model import tokenize_batch
from experiments.predictive_nucleus.joint_objective import DTYPE


def features():
    messages = []
    for word in ('synthetic', 'zebra', 'quux'):
        for position in range(3):
            tokens = ['A', 'B']; tokens.insert(position, word)
            messages.append(' '.join(tokens))
    return tokenize_batch(messages, [['A', 'B', 'C']] * len(messages))[0]


class LayoutCoordinatesTests(unittest.TestCase):
    def test_initial_response_equivalence_85_unchanged_scalars_and_rng(self):
        rng = torch.random.get_rng_state().clone(); inputs = features()
        for seed in (7, 11, 23, 37, 53):
            reference, candidate = centered_encoder(seed), coordinate_encoder(seed)
            old, new = reference.state_dict(), candidate.state_dict()
            other = [key for key in old if not key.startswith('layout.')]
            self.assertEqual(sum(old[key].numel() for key in other), 85)
            for key in other: self.assertTrue(torch.equal(old[key], new[key]))
            self.assertEqual(sum(p.numel() for p in candidate.parameters()), 88)
            self.assertNotIn('layout.0.bias', new)
            self.assertTrue(all(p.requires_grad for p in candidate.parameters()))
            torch.testing.assert_close(candidate(inputs), reference(inputs), rtol=0., atol=1e-14)
            repeated = coordinate_encoder(seed).state_dict()
            self.assertTrue(all(torch.equal(value, repeated[key]) for key, value in new.items()))
        self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))

    def test_all_legal_responses_remain_unconstrained_including_same_sign(self):
        model = coordinate_encoder(19)
        masks = torch.ones(3, 3, dtype=DTYPE) - torch.eye(3, dtype=DTYPE)
        for values in ((1., 2., 3.), (-3., -1., -2.), (2., 2., 2.), (-2., 0., 3.)):
            q = torch.tensor(values, dtype=DTYPE)
            with torch.no_grad(): model.layout[0].weight.copy_(q[None])
            actual = model.layout[0](1. - masks).flatten()
            self.assertTrue(torch.equal(actual, q))
            # Construct a valid old affine representation for arbitrary q.
            self.assertTrue(torch.equal(masks @ (-q) + q.sum(), q))

    def test_layout_response_jacobian_removes_affine_common_mode_coupling(self):
        reference, candidate = centered_encoder(19), coordinate_encoder(19)
        masks = torch.ones(3, 3, dtype=DTYPE) - torch.eye(3, dtype=DTYPE)
        jacobians = []
        for module, inputs in ((reference.layout[0], masks), (candidate.layout[0], 1. - masks)):
            rows = []
            for inputs_row in inputs:
                gradients = torch.autograd.grad(module(inputs_row).sum(), tuple(module.parameters()))
                rows.append(torch.cat([g.flatten() for g in gradients]))
            jacobians.append(torch.stack(rows))
        old, new = jacobians
        expected = torch.eye(3, dtype=DTYPE) + 2. * torch.ones(3, 3, dtype=DTYPE)
        self.assertTrue(torch.equal(old @ old.T, expected))
        self.assertTrue(torch.equal(new, torch.eye(3, dtype=DTYPE)))
        torch.testing.assert_close(torch.linalg.eigvalsh(expected), torch.tensor([1., 1., 7.], dtype=DTYPE))

    def test_full_encoder_gradients_obey_coordinate_change(self):
        reference, candidate = centered_encoder(19), coordinate_encoder(19)
        inputs = features()
        coefficients = torch.linspace(-.7, .9, 2 * len(inputs), dtype=DTYPE).reshape(-1, 2)
        for model in (reference, candidate): (model(inputs) * coefficients).sum().backward()
        old, new = dict(reference.named_parameters()), dict(candidate.named_parameters())
        for key in old:
            if not key.startswith('layout.'):
                torch.testing.assert_close(old[key].grad, new[key].grad, rtol=1e-12, atol=1e-14)
        q_gradient = new['layout.0.weight'].grad.flatten()
        masks = torch.ones(3, 3, dtype=DTYPE) - torch.eye(3, dtype=DTYPE)
        torch.testing.assert_close(old['layout.0.weight'].grad.flatten(), masks.T @ q_gradient, rtol=1e-12, atol=1e-14)
        torch.testing.assert_close(old['layout.0.bias'].grad[0], q_gradient.sum(), rtol=1e-12, atol=1e-14)

    def test_strict_state_roundtrip_nonsharing_and_invalid_boundaries(self):
        first, second = coordinate_encoder(19), coordinate_encoder(23)
        state = deepcopy(first.state_dict()); second.load_state_dict(state, strict=True)
        self.assertTrue(torch.equal(first(features()), second(features())))
        with torch.no_grad(): second.layout[0].weight.add_(1.)
        self.assertTrue(torch.equal(first.layout[0].weight, state['layout.0.weight']))
        self.assertFalse(torch.equal(first.layout[0].weight, second.layout[0].weight))
        for seed in (True, -1):
            with self.assertRaises(ValueError): coordinate_encoder(seed)
        invalid = features(); invalid[0, :, 0] = 1.
        with self.assertRaises(ValueError): first(invalid)


if __name__ == '__main__': unittest.main()
