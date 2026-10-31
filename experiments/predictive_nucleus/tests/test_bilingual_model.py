"""Synthetic language-interface invariants; no fitted research checkpoints."""
import math
import unittest

import torch

from experiments.predictive_nucleus import bilingual_model as text
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint


class BilingualModelTests(unittest.TestCase):
    def setUp(self):
        self.rng = torch.random.get_rng_state()
        torch.manual_seed(3081)
        self.roster = ['Ada', 'Ben', 'Cé']
        self.features, self.mentions = text.tokenize_batch(['Ada touches Ben'], [self.roster])
        self.pre = torch.tensor([[1., 0., 1.]], dtype=DTYPE)
        self.world = text.freeze_world(DomainKernel(hidden=3, role_tying=False))

    def tearDown(self):
        torch.random.set_rng_state(self.rng)

    def test_new_names_are_exactly_equivariant_and_lexemes_have_character_features(self):
        features, mentions = text.tokenize_batch(['new_888 ζήτημα fresh_930'],
                                                [['fresh_930', 'idle', 'new_888']])
        expected, _ = text.tokenize_batch(['Ada ζήτημα Ben'], [self.roster])
        self.assertTrue(torch.equal(features, expected))
        self.assertEqual(mentions.tolist(), [[2, 0]])
        self.assertGreater(float(features[0, 1, 1:].abs().sum()), 0.)
        encoder = text.OrderEncoder()
        self.assertTrue(torch.equal(encoder(features), encoder(expected)))

    def test_order_candidates_preserve_occurrence_order_without_role_assignment(self):
        features, mentions = text.tokenize_batch(['Ben Ada dax'], [self.roster])
        self.assertEqual(mentions.tolist(), [[1, 0]])
        self.assertEqual(text.action_candidates(mentions).tolist(), [[[0, 1, 0, -1], [0, 0, 1, -1]]])
        self.assertNotEqual(features.tolist(), self.features.tolist())

    def test_aliases_remain_one_physical_identity(self):
        features, mentions = text.tokenize_batch(['Ada touches Ada'], [self.roster])
        options = text.frozen_options(self.world, self.pre, self.world.initial(1), mentions)
        self.assertTrue(torch.equal(options[:, 0], options[:, 1]))
        self.assertTrue(torch.isfinite(text.OrderEncoder()(features)).all())

    def test_invalid_unknown_or_duplicate_roster_inputs_fail(self):
        cases = [('Ada touches Missing', self.roster), ('Ada Ben Cé', self.roster),
                 ('Ada touches Ben now', self.roster), ('Ada touches Ben', ['Ada', 'Ben', 'Ben'])]
        for message, roster in cases:
            with self.subTest(message=message), self.assertRaises(ValueError):
                text.tokenize_batch([message], [roster])

    def test_mixture_matches_explicit_probability_enumeration(self):
        state = torch.tensor([[math.log(.23), math.log(.77)]], dtype=DTYPE)
        options = text.frozen_options(self.world, self.pre, state, self.mentions)
        weights = torch.tensor([[.31, .69]], dtype=DTYPE)
        actual, pending = text.combine(weights.log(), options)
        expected = torch.zeros_like(pending)
        for order, action in enumerate(text.action_candidates(self.mentions).unbind(1)):
            _, native = self.world.predict(self.pre, action, state)
            expected += weights[:, order, None, None] * native.exp()
        self.assertTrue(torch.allclose(pending.exp(), expected, atol=1e-14, rtol=1e-14))
        self.assertTrue(torch.allclose(actual.exp(), expected.sum(1), atol=1e-14, rtol=1e-14))
        self.assertAlmostEqual(float(actual.exp().sum()), 1., places=13)

    def test_certain_order_reduces_to_native_and_feedback_keeps_dependence(self):
        state = self.world.initial(1)
        options = text.frozen_options(self.world, self.pre, state, self.mentions)
        actual, pending = text.combine(torch.tensor([[0., -torch.inf]], dtype=DTYPE), options)
        native, native_pending = self.world.predict(self.pre, text.action_candidates(self.mentions)[:, 0], state)
        self.assertTrue(torch.equal(actual, native))
        self.assertTrue(torch.equal(pending, native_pending))
        posterior = self.world.receive(pending, self.pre)
        evidence = pending[:, :, 5]
        self.assertTrue(torch.equal(posterior, evidence - evidence.logsumexp(-1, keepdim=True)))

    def test_gradients_reach_encoder_only_and_prediction_does_not_change_observations(self):
        encoder = text.OrderEncoder()
        before = fingerprint(self.world.state_dict())
        pre, state = self.pre.clone(), self.world.initial(1)
        options = text.frozen_options(self.world, pre, state, self.mentions)
        forecast, _ = text.combine(encoder(self.features), options)
        (-forecast[0, 3]).backward()
        self.assertTrue(all(p.grad is not None and bool(torch.isfinite(p.grad).all())
                            for p in encoder.parameters()))
        self.assertGreater(sum(float(p.grad.abs().sum()) for p in encoder.parameters()), 0.)
        self.assertTrue(all(p.grad is None for p in self.world.parameters()))
        self.assertEqual(before, fingerprint(self.world.state_dict()))
        self.assertTrue(torch.equal(pre, self.pre))
        self.assertTrue(torch.equal(state, self.world.initial(1)))

    def test_frozen_world_and_probability_validation_are_required(self):
        unfrozen = DomainKernel(hidden=3)
        with self.assertRaises(ValueError):
            text.frozen_options(unfrozen, self.pre, unfrozen.initial(1), self.mentions)
        options = text.frozen_options(self.world, self.pre, self.world.initial(1), self.mentions)
        for bad in (torch.zeros(1, 2, dtype=DTYPE), torch.tensor([[float('nan'), 0.]], dtype=DTYPE)):
            with self.assertRaises(ValueError): text.combine(bad, options)
        with self.assertRaises(ValueError): text.combine(torch.full((1, 2), -math.log(2), dtype=DTYPE), options + .1)
        with self.assertRaises(ValueError): text.OrderEncoder()(self.features.float())

    def test_exact_zero_support_has_finite_order_gradients(self):
        world = text.freeze_world(DomainKernel(hidden=3, persistence=True, role_tying=False))
        logits = torch.tensor([[.1, -.2]], dtype=DTYPE, requires_grad=True)
        options = text.frozen_options(world, self.pre, world.initial(1), self.mentions)
        forecast, _ = text.combine(logits.log_softmax(-1), options)
        self.assertTrue(torch.isneginf(forecast[0, [0, 2, 4, 6]]).all())
        (-forecast[0, 3]).backward()
        self.assertTrue(torch.isfinite(logits.grad).all())

    def test_control_context_ablation_removes_every_observation(self):
        before = torch.zeros_like(self.pre)
        after = torch.tensor([[0., 1., 0.]], dtype=DTYPE)
        action = torch.tensor([[0, 0, 1, -1]], dtype=torch.long)
        context = text.make_context(self.pre, before, action, after, self.mentions)
        ablated = text.make_context(self.pre, before, action, after, self.mentions, text_only=True)
        self.assertEqual(context.shape, (1, 48))
        self.assertEqual(float(ablated[:, :6].abs().sum() + ablated[:, 12:36].abs().sum()), 0.)
        self.assertTrue(torch.equal(context[:, 6:12], ablated[:, 6:12]))
        self.assertTrue(torch.equal(context[:, 36:], ablated[:, 36:]))
        self.assertTrue(torch.equal(self.pre, torch.tensor([[1., 0., 1.]], dtype=DTYPE)))

    def test_sequence_control_normalizes_all_entity_counts_and_parameter_match_is_explicit(self):
        sequence = text.SequenceControl()
        for n in range(3, 7):
            result = sequence(self.features, torch.zeros(1, 48, dtype=DTYPE), n)
            self.assertEqual(result.shape, (1, 2 ** n))
            self.assertAlmostEqual(float(result.exp().sum().detach()), 1., places=13)
        self.assertEqual(sum(p.numel() for p in text.OrderEncoder().parameters()), 474)
        self.assertEqual(sum(p.numel() for p in sequence.parameters()), 1048)


if __name__ == '__main__': unittest.main()
