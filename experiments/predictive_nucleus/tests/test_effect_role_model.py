"""Synthetic four-action/identity invariants; no real tape or fitted checkpoint."""
from copy import deepcopy
import json
import math
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import effect_role_model as model
from experiments.predictive_nucleus import bilingual_model as prior
from experiments.predictive_nucleus.binding_layout_coordinates import coordinate_encoder
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint


def bank(words=('touches',), readings=None):
    readings = readings or [[1, 0, 1] for _ in words]
    return {'version': 'bilingual-input-v1', 'episodes': [{'id': 'synthetic',
        'entities': ['Ada', 'Ben', 'Cé'], 'anchor': [0, 0, 0],
        'context': [{'action': [1, 2, -1, 1], 'reading': [1, 0, 1]}],
        'utterances': [{'text': f'Ada {word} Ben', 'reading': reading}
                       for word, reading in zip(words, readings, strict=True)]}]}


class EffectRoleModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = torch.get_num_threads(); torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.threads)

    def setUp(self):
        self.rng = torch.random.get_rng_state(); torch.manual_seed(481)
        self.inputs = bank(('touches', 'lights'))
        self.registry = model.create_registry([bank(), bank(('lights',))])
        self.parent = coordinate_encoder(7)
        self.net = model.encoder(7, self.parent.state_dict())
        self.world = prior.freeze_world(DomainKernel(hidden=3, role_tying=False))
        self.pre = torch.tensor([[1., 0., 1.]], dtype=DTYPE)
        self.features, self.mentions = model.tokenize_batch(['Ada lights Ben'], [['Ada', 'Ben', 'Cé']], self.registry)

    def tearDown(self):
        torch.random.set_rng_state(self.rng)

    def test_extension_copies_all_88_scalars_and_adds_only_four_neutral_scalars(self):
        before = fingerprint(self.parent.state_dict()); rng = torch.random.get_rng_state()
        net = model.encoder(23, {k: v.tolist() for k, v in self.parent.state_dict().items()})
        copied = 0
        for name, old in self.parent.state_dict().items():
            new = net.state_dict()[name]
            inherited = new[:2] if name.startswith('order.') else new
            self.assertTrue(torch.equal(inherited, old)); copied += old.numel()
            if name.startswith('order.'): self.assertEqual(float(new[2:].abs().sum()), 0.)
        self.assertEqual((copied, sum(p.numel() for p in net.parameters())), (88, 92))
        self.assertTrue(torch.equal(torch.random.get_rng_state(), rng))
        self.assertEqual(fingerprint(self.parent.state_dict()), before)
        new = net(self.features)
        torch.testing.assert_close(new[:, :2] - new[:, :2].logsumexp(-1, keepdim=True),
                                   self.parent(self.features), atol=1e-14, rtol=0.)
        self.assertTrue(torch.equal(new[:, 2], new[:, 3]))

    def test_invalid_parent_tensors_cannot_be_silently_adapted(self):
        original = self.parent.state_dict()
        bad = deepcopy(original); bad['order.bias'] = torch.zeros(4, dtype=DTYPE)
        with self.assertRaises(ValueError): model.encoder(7, bad)
        bad = deepcopy(original); bad['order.bias'][0] = torch.nan
        with self.assertRaises(ValueError): model.encoder(7, bad)
        bad = {k: v.float() for k, v in original.items()}
        with self.assertRaises(ValueError): model.encoder(7, bad)
        with self.assertRaises(ValueError): model.encoder(True, original)
        with self.assertRaises(ValueError): model.encoder(7, {})

    def test_registry_preserves_existing_features_and_survives_json_roundtrip(self):
        clone = json.loads(json.dumps(self.registry, allow_nan=False))
        self.assertEqual(model.validate_registry(clone), self.registry)
        self.assertEqual(model.create_registry([bank(), bank(('lights',))]), self.registry)
        old, occurrences = prior.tokenize_batch(['Ada touches Ben'], [['Ada', 'Ben', 'Cé']])
        new, mapped = model.tokenize_batch(['Ada touches Ben'], [['Ada', 'Ben', 'Cé']], clone)
        self.assertTrue(torch.equal(new, old)); self.assertTrue(torch.equal(mapped, occurrences))
        self.assertEqual(clone['legacy_tokens'], ['touches'])
        self.assertEqual(clone['tokens']['lights']['source'], 'characters')

    def test_new_feature_collision_is_resolved_without_rewriting_legacy_identity(self):
        character = prior._characters('touches')
        with patch.object(prior, '_characters', return_value=character):
            registry = model.create_registry([bank(), bank(('lights', 'zef'))])
            self.assertEqual(registry['tokens']['touches']['features'], list(character))
            self.assertTrue(all(registry['tokens'][name]['source'] == 'identity_collision' for name in ('lights', 'zef')))
            self.assertEqual(len({tuple(r['features']) for r in registry['tokens'].values()}), 3)
            self.assertEqual(len({r['id'] for r in registry['tokens'].values()}), 3)
            model.validate_registry(json.loads(json.dumps(registry)))
            features, _ = model.tokenize_batch(['Ada lights Ben', 'Ada zef Ben'],
                                               [['Ada', 'Ben', 'Cé']] * 2, registry)
            self.assertFalse(torch.equal(features[0], features[1]))
            with self.assertRaisesRegex(ValueError, 'inherited lexical character features collide'):
                model.create_registry([bank(('touches', 'lights'))])

    def test_registry_tampering_and_semantic_fields_are_rejected(self):
        bad = deepcopy(self.registry); bad['tokens']['lights']['features'][0] += .1
        with self.assertRaises(ValueError): model.validate_registry(bad)
        bad = deepcopy(self.registry); bad['tokens']['lights']['id'] = bad['tokens']['touches']['id']
        with self.assertRaises(ValueError): model.validate_registry(bad)
        bad = deepcopy(self.registry); bad['tokens']['lights']['meaning'] = 2
        with self.assertRaises(ValueError): model.validate_registry(bad)

    def test_unknown_strings_remain_distinct_unresolved_and_registry_is_unchanged(self):
        before = deepcopy(self.registry)
        with self.assertRaises(model.UnresolvedLexeme) as failure:
            model.tokenize_batch(['Ada unfamiliar_one Ben', 'Ben unfamiliar_two Ada'],
                                 [['Ada', 'Ben', 'Cé']] * 2, self.registry)
        records = failure.exception.records
        self.assertEqual([r['token'] for r in records], ['unfamiliar_one', 'unfamiliar_two'])
        self.assertEqual(len({r['id'] for r in records}), 2)
        self.assertEqual({r['status'] for r in records}, {'UNRESOLVED_LEXICAL_IDENTITY'})
        self.assertEqual(self.registry, before)
        with self.assertRaises(model.UnresolvedLexeme):
            model.pack(bank(('unfamiliar_one',)), self.world, self.registry)

    def test_names_only_address_entities_and_menu_never_depends_on_words(self):
        features, mentions = model.tokenize_batch(['new_888 lights fresh_930'],
            [['fresh_930', 'idle', 'new_888']], self.registry)
        self.assertTrue(torch.equal(features, self.features)); self.assertEqual(mentions.tolist(), [[2, 0]])
        self.assertEqual(model.action_candidates(mentions).tolist(),
                         [[[0, 2, 0, -1], [0, 0, 2, -1], [1, 2, -1, 1], [1, 0, -1, 1]]])
        _, other = model.tokenize_batch(['Ada touches Ben'], [['Ada', 'Ben', 'Cé']], self.registry)
        self.assertTrue(torch.equal(model.action_candidates(other), model.action_candidates(self.mentions)))

    def test_four_action_mixture_matches_explicit_native_enumeration(self):
        state = torch.tensor([[math.log(.23), math.log(.77)]], dtype=DTYPE)
        options = model.frozen_options(self.world, self.pre, state, self.mentions)
        weights = torch.tensor([[.1, .2, .3, .4]], dtype=DTYPE)
        actual, pending = model.combine(weights.log(), options); expected = torch.zeros_like(pending)
        for index, action in enumerate(model.action_candidates(self.mentions).unbind(1)):
            _, native = self.world.predict(self.pre, action, state)
            expected += weights[:, index, None, None] * native.exp()
        torch.testing.assert_close(pending.exp(), expected, atol=1e-14, rtol=0.)
        torch.testing.assert_close(actual.exp(), expected.sum(1), atol=1e-14, rtol=0.)
        self.assertAlmostEqual(float(actual.exp().sum()), 1., places=13)

    def test_certain_set_uses_learned_native_distribution_without_assignment_shortcut(self):
        state = self.world.initial(1)
        options = model.frozen_options(self.world, self.pre, state, self.mentions)
        for selected in (2, 3):
            weights = torch.full((1, 4), -torch.inf, dtype=DTYPE); weights[:, selected] = 0.
            actual, pending = model.combine(weights, options)
            native, expected = self.world.predict(self.pre, model.action_candidates(self.mentions)[:, selected], state)
            torch.testing.assert_close(actual, native, atol=1e-14, rtol=0.)
            torch.testing.assert_close(pending, expected, atol=1e-14, rtol=0.)
            self.assertTrue(bool(torch.isfinite(actual).all()))
            self.assertGreater(int((actual.exp() > .01).sum()), 1)

    def test_feedback_retains_action_mode_correlation_instead_of_resampling_modes(self):
        probabilities = torch.zeros(1, 4, 2, 8, dtype=DTYPE)
        for action in range(4):
            probabilities[0, action, 0, 0 if action % 2 == 0 else 7] = .25
            probabilities[0, action, 1, 7 if action % 2 == 0 else 0] = .75
        action_logp = torch.tensor([[.8, .2, 0., 0.]], dtype=DTYPE).log()
        raw, pending = model.combine(action_logp, probabilities.log())
        self.assertAlmostEqual(float(raw[0, 0].exp()), .35, places=14)
        posterior = self.world.receive(pending, torch.zeros(1, 3, dtype=DTYPE))
        torch.testing.assert_close(posterior.exp(), torch.tensor([[4 / 7, 3 / 7]], dtype=DTYPE), atol=1e-14, rtol=0.)
        self.assertFalse(torch.allclose(posterior.exp(), torch.tensor([[.25, .75]], dtype=DTYPE)))

    def test_training_gradient_reaches_language_only_and_keeps_world_bytes_unchanged(self):
        before = fingerprint(self.world.state_dict()); pre = self.pre.clone(); state = self.world.initial(1)
        options = model.frozen_options(self.world, pre, state, self.mentions)
        result, _ = model.combine(self.net(self.features), options); (-result[0, 3]).backward()
        self.assertTrue(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in self.net.parameters()))
        self.assertGreater(sum(float(p.grad.abs().sum()) for p in self.net.parameters()), 0.)
        self.assertTrue(all(p.grad is None for p in self.world.parameters()))
        self.assertEqual(fingerprint(self.world.state_dict()), before)
        self.assertTrue(torch.equal(pre, self.pre)); self.assertTrue(torch.equal(state, self.world.initial(1)))

    def test_set_only_context_is_supported_and_text_only_context_contains_no_bits(self):
        groups = model.pack(self.inputs, self.world, self.registry)
        self.assertEqual(len(groups), 1)
        torch.testing.assert_close(groups[0]['state'], self.world.initial(1), atol=1e-14, rtol=0.)
        context = groups[0]['events'][0]['text_context']
        self.assertEqual(context.shape, (1, 48))
        self.assertEqual(float(context[:, :6].abs().sum() + context[:, 12:36].abs().sum()), 0.)
        self.assertEqual(context[0, 6:12].tolist(), [1., 1., 1., 0., 0., 0.])
        self.assertEqual(int(context[:, 36:].sum()), 2)
        changed = model.text_only_context(1. - self.pre, self.mentions)
        self.assertTrue(torch.equal(context, changed))

    def test_forecasts_never_use_current_or_future_readings(self):
        inputs = bank(('touches', 'lights'), [[0, 1, 1], [1, 1, 1]])
        before = deepcopy(inputs); fingerprint_before = fingerprint(self.world.state_dict())
        forecast = lambda data: [raw.detach().clone() for raw, _ in model.forecasts(
            'grounded', self.net, self.world, model.pack(data, self.world, self.registry)[0])]
        original = forecast(inputs)
        last = deepcopy(inputs); last['episodes'][0]['utterances'][-1]['reading'] = [0, 0, 0]
        for a, b in zip(original, forecast(last), strict=True): self.assertTrue(torch.equal(a, b))
        earlier = deepcopy(inputs); earlier['episodes'][0]['utterances'][0]['reading'] = [1, 0, 0]
        changed = forecast(earlier)
        self.assertTrue(torch.equal(original[0], changed[0])); self.assertFalse(torch.equal(original[1], changed[1]))
        self.assertEqual(inputs, before); self.assertEqual(fingerprint(self.world.state_dict()), fingerprint_before)

    def test_masked_view_changes_only_current_lexeme_not_prefix_belief(self):
        group = model.pack(self.inputs, self.world, self.registry)[0]
        events = group['events']; state = group['state'].clone()
        masked = list(model.forecasts('grounded', self.net, self.world, group, view='masked'))
        for event, (raw, actions) in zip(events, masked, strict=True):
            features = event['features'].clone(); features[:, :, 1:] = 0.
            options = event['likelihood'] + state[:, None, :, None]
            expected, _ = model.combine(self.net(features), options)
            torch.testing.assert_close(raw, expected, atol=1e-14, rtol=0.)
            self.assertTrue(torch.equal(actions, self.net(features)))
            _, pending = model.combine(self.net(event['features']), options)
            state = self.world.receive(pending, event['post'])
        self.assertGreater(float(events[0]['features'][:, :, 1:].abs().sum()), 0.)

    def test_parser_and_text_only_interfaces_need_no_gold_labels(self):
        group = model.pack(self.inputs, self.world, self.registry)[0]
        a = list(model.forecasts('grounded', self.net, self.world, group))
        b = list(model.forecasts('parser', self.net, self.world, group))
        for x, y in zip(a, b, strict=True):
            self.assertTrue(torch.equal(x[0], y[0])); self.assertTrue(torch.equal(x[1], y[1]))
        control = prior.SequenceControl()
        for raw, weights in model.forecasts('text_only', control, self.world, group):
            self.assertEqual(raw.shape, (1, 8)); self.assertIsNone(weights)
            self.assertAlmostEqual(float(raw.exp().sum().detach()), 1., places=13)
        bad = deepcopy(self.inputs); bad['episodes'][0]['utterances'][0]['action_label'] = 2
        with self.assertRaises(ValueError): model.pack(bad, self.world, self.registry)

    def test_invalid_probabilities_or_mutable_world_fail_closed(self):
        options = model.frozen_options(self.world, self.pre, self.world.initial(1), self.mentions)
        for bad in (torch.zeros(1, 4, dtype=DTYPE), torch.full((1, 2), -math.log(2), dtype=DTYPE),
                    torch.tensor([[math.nan, 0., 0., 0.]], dtype=DTYPE)):
            with self.assertRaises(ValueError): model.combine(bad, options)
        with self.assertRaises(ValueError): model.combine(torch.full((1, 4), -math.log(4), dtype=DTYPE), options + .1)
        with self.assertRaises(ValueError): model.frozen_options(DomainKernel(hidden=3), self.pre, self.world.initial(1), self.mentions)
        with self.assertRaises(ValueError): model.pack(self.inputs, DomainKernel(hidden=3), self.registry)
        group = model.pack(self.inputs, self.world, self.registry)[0]
        with self.assertRaises(ValueError): list(model.forecasts('unsupported', self.net, self.world, group))


if __name__ == '__main__': unittest.main()
