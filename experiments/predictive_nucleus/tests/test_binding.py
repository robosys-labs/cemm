"""Binding implementation invariants; synthetic observations, no research scores."""
from copy import deepcopy
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import bilingual_model as text, binding_model as binding
from experiments.predictive_nucleus import bilingual_run as previous, binding_training as training
from experiments.predictive_nucleus.acceptance_contract import digest
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint


def observations():
    first = {'id': 'synthetic-one', 'entities': ['Ada', 'Ben', 'Cee'], 'anchor': [0, 0, 0],
             'context': [{'action': [0, 0, 1, -1], 'reading': [0, 1, 0]}],
             'utterances': [{'text': 'Ada oddword Ben', 'reading': [1, 1, 0]}]}
    second = deepcopy(first)
    second['id'] = 'synthetic-two'
    second['utterances'].append({'text': 'Cee Ada otherword', 'reading': [1, 0, 0]})
    return {'version': 'bilingual-input-v1', 'episodes': [first, second]}


class BindingModelTests(unittest.TestCase):
    def setUp(self):
        self.rng = torch.random.get_rng_state()
        self.roster = ['Ada', 'Ben', 'Cee']
        self.features, self.mentions = text.tokenize_batch(['Ada oddword Ben'], [self.roster])

    def tearDown(self):
        torch.random.set_rng_state(self.rng)

    def test_actual_parameter_budget_and_unchanged_gru(self):
        for arm in binding.ARMS:
            net = binding.encoder(arm, 7)
            self.assertEqual(sum(p.numel() for p in net.parameters()), binding.PARAMETERS[arm])
            self.assertLessEqual(binding.PARAMETERS[arm], 474)
        self.assertEqual(fingerprint(binding.encoder('gru', 7).state_dict()),
                         fingerprint(previous.learner('grounded', 7).state_dict()))

    def test_factory_is_deterministic_without_rng_side_effects(self):
        before = torch.random.get_rng_state().clone()
        for arm in binding.ARMS:
            one, two = binding.encoder(arm, 23), binding.encoder(arm, 23)
            self.assertEqual(fingerprint(one.state_dict()), fingerprint(two.state_dict()))
            self.assertNotEqual(fingerprint(one.state_dict()), fingerprint(binding.encoder(arm, 37).state_dict()))
        self.assertTrue(torch.equal(before, torch.random.get_rng_state()))

    def test_factory_rejects_invalid_arms_and_seeds(self):
        for arm, seed in [('other', 7), (None, 7), ('gru', True), ('factor', -1),
                          ('additive', 2 ** 63), ('gru', 7.)]:
            with self.subTest(arm=arm, seed=seed), self.assertRaises(ValueError):
                binding.encoder(arm, seed)
        for value in (0, 1, 'yes', None):
            with self.assertRaises(ValueError): binding.FactorOrderEncoder(interaction=value)

    def test_split_preserves_content_across_layout_without_assigning_roles(self):
        features, _ = text.tokenize_batch(['Ada oddword Ben', 'Ben Ada oddword', 'oddword Ada Ben'],
                                          [self.roster] * 3)
        content, layout = binding.factor_inputs(features)
        self.assertTrue(torch.equal(content[0], content[1]))
        self.assertTrue(torch.equal(content[0], content[2]))
        self.assertEqual(layout.tolist(), [[1., 0., 1.], [1., 1., 0.], [0., 1., 1.]])
        self.assertTrue(torch.equal(content[0], self.features[0, 1, 1:]))

    def test_renaming_and_roster_permutation_do_not_change_order_probabilities(self):
        renamed, mentions = text.tokenize_batch(['New_1 oddword New_2'], [['New_2', 'Idle', 'New_1']])
        self.assertEqual(mentions.tolist(), [[2, 0]])
        for arm in binding.ARMS:
            net = binding.encoder(arm, 11)
            self.assertTrue(torch.equal(net(self.features), net(renamed)))

    def test_masked_lexeme_has_identical_effective_input(self):
        features, _ = text.tokenize_batch(['Ada oddword Ben', 'Ada otherword Ben'], [self.roster] * 2)
        features[:, :, 1:] = 0.
        for arm in binding.ARMS:
            result = binding.encoder(arm, 7)(features)
            self.assertTrue(torch.equal(result[0], result[1]))

    def test_invalid_features_and_identity_contamination_fail(self):
        bads = [self.features.float(), self.features[:, :2], self.features.repeat(0, 1, 1)]
        for position, value in [((0, 0, 0), .5), ((0, 0, 0), 0.),
                                ((0, 0, 1), .1), ((0, 1, 1), float('nan'))]:
            bad = self.features.clone(); bad[position] = value; bads.append(bad)
        for bad in bads:
            with self.subTest(shape=bad.shape), self.assertRaises(ValueError):
                binding.encoder('factor', 7)(bad)

    def test_finite_normalized_outputs_and_no_feature_mutation(self):
        before = self.features.clone()
        for arm in binding.ARMS:
            result = binding.encoder(arm, 7)(self.features)
            self.assertEqual(result.shape, (1, 2))
            self.assertTrue(torch.isfinite(result).all())
            torch.testing.assert_close(result.logsumexp(-1), torch.zeros(1, dtype=DTYPE), atol=1e-14, rtol=0.)
        self.assertTrue(torch.equal(before, self.features))

    def test_readouts_match_their_declared_learned_operations(self):
        for arm in ('factor', 'additive'):
            net = binding.encoder(arm, 7)
            content, layout = binding.factor_inputs(self.features)
            left, right = net.lexical(content), net.layout(layout)
            if arm == 'factor':
                expected = (left * right) @ net.order.weight[:, 0, 0][None, :] + net.order.bias
            else:
                expected = torch.cat((left, right), -1) @ net.order.weight.T + net.order.bias
            torch.testing.assert_close(net(self.features), expected.log_softmax(-1), atol=1e-14, rtol=0.)

    def test_no_forced_inverse_when_learned_layout_is_constant(self):
        net = binding.encoder('factor', 7)
        with torch.no_grad(): net.layout[0].weight.zero_()
        features, _ = text.tokenize_batch(['Ada oddword Ben', 'Ben Ada oddword'], [self.roster] * 2)
        result = net(features)
        self.assertTrue(torch.equal(result[0], result[1]))

    def test_state_dictionary_roundtrip_without_new_checkpoint_format(self):
        for arm in binding.ARMS:
            first, restored = binding.encoder(arm, 7), binding.encoder(arm, 53)
            restored.load_state_dict(deepcopy(first.state_dict()), strict=True)
            self.assertTrue(torch.equal(first(self.features), restored(self.features)))
        with self.assertRaises(RuntimeError):
            binding.encoder('factor', 7).load_state_dict(binding.encoder('additive', 7).state_dict())

    def test_outcome_gradients_reach_both_factors_and_readout_not_world(self):
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(3081)
            world = text.freeze_world(DomainKernel(hidden=3, role_tying=False))
        pre = torch.tensor([[1., 0., 1.]], dtype=DTYPE)
        original = fingerprint(world.state_dict())
        options = text.frozen_options(world, pre, world.initial(1), self.mentions)
        for arm in ('factor', 'additive'):
            net = binding.encoder(arm, 7)
            raw, _ = text.combine(net(self.features), options)
            (-raw[0, 3]).backward()
            for component in (net.lexical, net.layout, net.order):
                self.assertTrue(all(p.grad is not None and torch.isfinite(p.grad).all() for p in component.parameters()))
                self.assertGreater(sum(float(p.grad.abs().sum()) for p in component.parameters()), 0.)
        self.assertTrue(all(p.grad is None for p in world.parameters()))
        self.assertEqual(original, fingerprint(world.state_dict()))


class BindingTrainingTests(unittest.TestCase):
    def setUp(self):
        self.rng = torch.random.get_rng_state()
        torch.manual_seed(3081)
        self.world = text.freeze_world(DomainKernel(hidden=3, role_tying=False))
        self.inputs = observations()

    def tearDown(self):
        torch.random.set_rng_state(self.rng)

    def test_one_step_shared_observed_exposure_and_event_weighting(self):
        groups = previous.pack(self.inputs, self.world)
        expected = {}
        for arm in binding.ARMS:
            net = binding.encoder(arm, 7)
            losses = [-raw.gather(1, event['target'][:, None]).sum()
                      for group in groups
                      for (raw, _), event in zip(previous.forecasts('grounded', net, self.world, group),
                                                group['events'], strict=True)]
            expected[arm] = float((sum(losses) / 3).detach())
        before, world_before = deepcopy(self.inputs), fingerprint(self.world.state_dict())
        rng = torch.random.get_rng_state().clone()
        result = training.fit_comparison(self.inputs, self.world, seed=7, updates=1)
        self.assertEqual(set(result['models']), set(binding.ARMS))
        self.assertEqual(result['training_input_sha256'], digest(self.inputs))
        self.assertFalse(result['scientific_admission'])
        for arm, report in result['reports'].items():
            self.assertEqual(report['observed_events_per_update'], 3)
            self.assertEqual(report['updates'], 1)
            self.assertAlmostEqual(report['curve'][0][1], expected[arm], places=12)
            self.assertNotEqual(report['initial_sha256'], report['final_sha256'])
            self.assertFalse(result['models'][arm].training)
        self.assertEqual(before, self.inputs)
        self.assertEqual(world_before, fingerprint(self.world.state_dict()))
        self.assertTrue(all(p.grad is None for p in self.world.parameters()))
        self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))

    def test_repeatability_on_synthetic_observations_only(self):
        first = training.fit_comparison(self.inputs, self.world, seed=11, updates=2)
        second = training.fit_comparison(self.inputs, self.world, seed=11, updates=2)
        for arm in binding.ARMS:
            self.assertEqual(first['reports'][arm]['final_sha256'], second['reports'][arm]['final_sha256'])
            self.assertEqual(first['reports'][arm]['curve'], second['reports'][arm]['curve'])

    def test_gold_labels_are_rejected_not_ignored(self):
        for field in ('action_orders', 'language', 'mode', 'family', 'oracle', 'teacher_logits'):
            bad = deepcopy(self.inputs); bad['episodes'][0][field] = [0]
            with self.subTest(field=field), self.assertRaises(ValueError):
                training.fit_comparison(bad, self.world, seed=7, updates=1)
        bad = deepcopy(self.inputs); bad['episodes'][0]['utterances'][0]['action'] = [0, 0, 1, -1]
        with self.assertRaises(ValueError): training.fit_comparison(bad, self.world, seed=7, updates=1)

    def test_invalid_budgets_fail_before_training(self):
        for key, value in [('updates', True), ('updates', 0), ('updates', 4097), ('updates', 1.),
                           ('seed', True), ('learning_rate', 0.), ('learning_rate', float('nan')),
                           ('gradient_clip', False), ('cpu_seconds_per_arm', float('inf'))]:
            args = {'seed': 7, 'updates': 1, key: value}
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                training.fit_comparison(self.inputs, self.world, **args)

    def test_world_requires_explicit_frozen_contract(self):
        self.world.requires_grad_(True)
        with self.assertRaises(ValueError): training.fit_comparison(self.inputs, self.world, seed=7, updates=1)
        self.assertTrue(all(p.requires_grad for p in self.world.parameters()))
        self.world.requires_grad_(False).train()
        with self.assertRaises(ValueError): training.fit_comparison(self.inputs, self.world, seed=7, updates=1)
        self.assertTrue(self.world.training)

    def test_partially_training_world_is_rejected_without_flag_mutation(self):
        child = next(module for module in self.world.modules() if module is not self.world)
        child.train()
        flags = [module.training for module in self.world.modules()]
        with self.assertRaises(ValueError):
            training.fit_comparison(self.inputs, self.world, seed=7, updates=1)
        self.assertEqual(flags, [module.training for module in self.world.modules()])
        with self.assertRaises(ValueError):
            training.fit_comparison(self.inputs, object(), seed=7, updates=1)

    def test_cpu_limit_fails_without_a_completed_result(self):
        before = fingerprint(self.world.state_dict())
        with self.assertRaisesRegex(ValueError, 'CPU limit'):
            training.fit_comparison(self.inputs, self.world, seed=7, updates=1, cpu_seconds_per_arm=1e-12)
        self.assertEqual(before, fingerprint(self.world.state_dict()))

    def test_interrupted_optimizer_does_not_return_partial_success(self):
        before = fingerprint(self.world.state_dict())
        with patch.object(torch.optim.Adam, 'step', side_effect=KeyboardInterrupt), self.assertRaises(KeyboardInterrupt):
            training.fit_comparison(self.inputs, self.world, seed=7, updates=1)
        self.assertEqual(before, fingerprint(self.world.state_dict()))

    def test_no_generator_or_oracle_is_needed_for_fitting(self):
        import builtins
        original = builtins.__import__
        def checked(name, *args, **kwargs):
            if any(word in name for word in ('bilingual_data', 'lexical_data', 'oracle', 'scoring')):
                raise AssertionError('unexpected evaluator import: ' + name)
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', side_effect=checked):
            result = training.fit_comparison(self.inputs, self.world, seed=7, updates=1)
        self.assertEqual(set(result['models']), set(binding.ARMS))


if __name__ == '__main__': unittest.main()
