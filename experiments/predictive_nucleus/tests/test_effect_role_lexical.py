"""Synthetic protected-complement and identity-coordinate invariants."""
from copy import deepcopy
import math
import unittest

import torch

from experiments.predictive_nucleus import effect_role_lexical as model
from experiments.predictive_nucleus import effect_role_model as prior
from experiments.predictive_nucleus import effect_role_run as historical
from experiments.predictive_nucleus.binding_layout_coordinates import coordinate_encoder
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint
from experiments.predictive_nucleus.tests.test_effect_role_model import bank


def fixture():
    registry = prior.create_registry([bank(), bank(('novel_a', 'novel_b'))])
    parent = coordinate_encoder(7)
    return parent, registry, model.inherited_ids(registry)


class EffectRoleLexicalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = torch.get_num_threads(); torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.threads)

    def setUp(self):
        self.parent, self.registry, self.legacy = fixture()
        self.net = model.encoder(7, self.parent.state_dict(), self.registry, self.legacy)

    def features(self, word):
        return prior.tokenize_batch([f'Ada {word} Ben', f'Ben Ada {word}', f'{word} Ben Ada'],
                                    [['Ada', 'Ben', 'Cé']] * 3, self.registry)[0]

    def test_exact_state_accounting_bytes_identity_binding_and_rng(self):
        rng = torch.random.get_rng_state()
        net = model.encoder(23, {k: v.tolist() for k, v in self.parent.state_dict().items()}, self.registry, self.legacy)
        self.assertEqual(set(net.state_dict()), {'parent.' + k for k in self.parent.state_dict()} | {'new_coordinates'})
        for name, value in self.parent.state_dict().items():
            self.assertEqual(net.state_dict()['parent.' + name].numpy().tobytes(), value.numpy().tobytes())
        self.assertEqual(tuple(net.new_coordinates.shape), (2, 2))
        self.assertEqual(float(net.new_coordinates.detach().abs().sum()), 0.)
        self.assertEqual(sum(p.numel() for p in net.parameters()), 92)
        self.assertEqual(sum(p.numel() for p in net.parameters() if p.requires_grad), 4)
        self.assertFalse(list(net.buffers()))
        self.assertEqual(net.registry_sha256, historical.c.digest(self.registry))
        self.assertEqual(list(net.legacy_ids), self.legacy)
        self.assertEqual(list(net.new_ids), sorted(self.registry['tokens'][w]['id'] for w in ('novel_a', 'novel_b')))
        self.assertTrue(torch.equal(torch.random.get_rng_state(), rng))

    def test_new_rows_are_uniform_and_legacy_function_survives_any_new_coordinate_update(self):
        old_features = self.features('touches')
        old = self.net(old_features).detach().clone()
        self.assertTrue(torch.equal(old[:, :2], self.parent(old_features)))
        self.assertTrue(bool(torch.isneginf(old[:, 2:]).all()))
        for word in ('novel_a', 'novel_b'):
            torch.testing.assert_close(self.net(self.features(word)).exp(),
                torch.full((3, 4), .25, dtype=DTYPE), atol=1e-14, rtol=0.)
        with torch.no_grad(): self.net.new_coordinates.copy_(torch.tensor([[5., -4.], [-3., 6.]], dtype=DTYPE))
        self.assertTrue(torch.equal(self.net(old_features), old))
        self.assertEqual(fingerprint(self.net.parent.state_dict()), fingerprint(self.parent.state_dict()))

    def test_effect_mass_does_not_depend_on_layout_magnitude(self):
        with torch.no_grad(): self.net.new_coordinates[:, :].copy_(torch.tensor([[1.3, 2.], [1.3, 2.]], dtype=DTYPE))
        for word in ('novel_a', 'novel_b'):
            probabilities = self.net(self.features(word)).exp()
            expected = torch.full((3,), 1. / (1. + math.exp(-1.3)), dtype=DTYPE)
            torch.testing.assert_close(probabilities[:, 2:].sum(-1), expected, atol=1e-14, rtol=0.)
            self.assertGreater(float((probabilities[0] - probabilities[1]).abs().max().detach()), .01)

    def test_endpoint_gradient_teaches_new_effect_and_transfers_roles_without_hash_prior(self):
        state = deepcopy(self.parent.state_dict())
        state['layout.0.weight'] = torch.tensor([[-2., 1., -.5]], dtype=DTYPE)
        state['order.weight'] = torch.tensor([[[1.]], [[-1.]]], dtype=DTYPE)
        state['order.bias'] = torch.tensor([1000., -1000.], dtype=DTYPE)
        net = model.encoder(7, state, self.registry, self.legacy)
        row = net.new_ids.index(self.registry['tokens']['novel_a']['id'])
        features = self.features('novel_a')
        torch.testing.assert_close(net(features).exp(), torch.full((3, 4), .25, dtype=DTYPE), atol=1e-14, rtol=0.)
        # Four native alternatives' likelihoods for one synthetic observed endpoint.
        likelihood = torch.tensor([[.0003, .0003, .0003, .998]], dtype=DTYPE).log()
        loss = -(net(features[:1]) + likelihood).logsumexp(-1).mean()
        gradient, = torch.autograd.grad(loss, (net.new_coordinates,))
        self.assertTrue(bool(torch.isfinite(gradient).all()))
        self.assertLess(float(gradient[row, 0]), -.4)
        self.assertGreater(float(gradient[row, 1]), .9)
        self.assertEqual(float(gradient[1 - row].abs().sum()), 0.)
        with torch.no_grad(): net.new_coordinates.sub_(gradient)
        self.assertEqual(net(features).argmax(-1).tolist(), [3, 2, 2])
        self.assertTrue(all(p.grad is None and not p.requires_grad for p in net.parent.parameters()))

    def test_masking_removes_identity_and_unknown_tokens_never_get_a_prediction(self):
        with torch.no_grad(): self.net.new_coordinates.fill_(20.)
        features = self.features('novel_a'); features[:, :, 1:] = 0.
        torch.testing.assert_close(self.net(features).exp(), torch.full((3, 4), .25, dtype=DTYPE), atol=1e-14, rtol=0.)
        with self.assertRaises(prior.UnresolvedLexeme):
            prior.tokenize_batch(['Ada unseen_raw_token Ben'], [['Ada', 'Ben', 'Cé']], self.registry)
        features = self.features('novel_a')
        for row in range(len(features)):
            position = int((1. - features[row, :, 0]).argmax())
            features[row, position, 1:] = .123456
        with self.assertRaisesRegex(ValueError, 'no registered lexical identity'): self.net(features)

    def test_training_mode_cannot_unfreeze_parent_and_invalid_inventories_fail(self):
        self.net.train(); self.assertFalse(self.net.parent.training)
        self.net.parent.requires_grad_(True)
        with self.assertRaisesRegex(ValueError, 'must remain frozen'): self.net(self.features('touches'))
        with self.assertRaisesRegex(ValueError, 'identity inventory'):
            model.encoder(7, self.parent.state_dict(), self.registry, [])
        one = prior.create_registry([bank(), bank(('novel_a',))])
        with self.assertRaisesRegex(ValueError, 'two prospective'):
            model.encoder(7, self.parent.state_dict(), one, model.inherited_ids(one))
        bad = deepcopy(self.parent.state_dict()); bad['order.bias'][0] = torch.nan
        with self.assertRaises(ValueError): model.encoder(7, bad, self.registry, self.legacy)

    def test_text_only_initialization_is_unchanged(self):
        actual = model.learner('text_only', 11, self.parent.state_dict(), self.registry, self.legacy)
        old = historical.learner('text_only', 11, self.parent.state_dict())
        self.assertEqual(fingerprint(actual.state_dict()), fingerprint(old.state_dict()))


if __name__ == '__main__': unittest.main()
