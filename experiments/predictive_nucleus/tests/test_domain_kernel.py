"""Structural domain/alias checks, never new learned-generalization evidence."""
from copy import deepcopy
import json
import math
import unittest

import torch
from torch import nn

from experiments.predictive_nucleus import domain_contract as d
from experiments.predictive_nucleus import joint_objective as old
from experiments.predictive_nucleus.domain_kernel import DomainKernel


CONFIGS = ({'persistence': True}, {}, {'role_tying': False}, {'memory': False})


def actions(*rows):
    return torch.tensor(rows, dtype=torch.long)


class FixedPair(nn.Module):
    def __init__(self, logits):
        super().__init__()
        self.register_buffer('logits', torch.tensor(logits, dtype=old.DTYPE))

    def forward(self, inputs):
        return self.logits[None].expand(len(inputs), -1)


class DomainKernelTests(unittest.TestCase):
    def setUp(self):
        self.rng = torch.random.get_rng_state()
        torch.manual_seed(17)

    def tearDown(self):
        torch.random.set_rng_state(self.rng)

    def test_explicit_transfer_preserves_source_parameters_and_rng_without_stale_geometry(self):
        for config in CONFIGS:
            with self.subTest(config=config):
                source = old.JointKernel(**config).eval()
                before, rng = old.fingerprint(source.state_dict()), torch.random.get_rng_state()
                model = DomainKernel.from_legacy(source)
                self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))
                self.assertEqual(before, old.fingerprint(source.state_dict()))
                self.assertNotIn('worlds', model.state_dict())
                self.assertFalse(hasattr(model, 'worlds'))
                self.assertEqual(set(model.state_dict()), set(dict(source.named_parameters())))
                self.assertFalse(model.training)
                for name, value in model.named_parameters():
                    original = dict(source.named_parameters())[name]
                    self.assertTrue(torch.equal(value, original))
                    self.assertNotEqual(value.data_ptr(), original.data_ptr())
                record = model.domain_adaptation
                self.assertEqual(record['source_full_state_sha256'], before)
                self.assertEqual(record['active_learned_parameters_sha256'], old.fingerprint(model.state_dict()))
                self.assertEqual(record['active_learned_parameters_sha256'], record['source_learned_parameters_sha256'])
                json.dumps(record, allow_nan=False)

    def test_verified_export_style_class_identity_is_accepted_but_other_architecture_is_not(self):
        exported_class = type('JointKernel', (old.JointKernel,), {'__module__': 'verified_bundle.joint_objective'})
        self.assertIsInstance(DomainKernel.from_legacy(exported_class()), DomainKernel)
        for invalid in (old.JointFlatGRU(), DomainKernel(), object()):
            with self.subTest(invalid=type(invalid).__name__), self.assertRaises(ValueError):
                DomainKernel.from_legacy(invalid)

    def test_malformed_configuration_geometry_inventory_and_tensors_fail_strictly(self):
        source = old.JointKernel()
        mutations = (
            lambda m: setattr(m, 'memory', 1),
            lambda m: m.worlds.fill_(1),
            lambda m: m.float(),
            lambda m: m.register_buffer('extra', torch.zeros(1)),
            lambda m: m.pair.__setitem__(1, nn.Sigmoid()),
            lambda m: m.pair.__setitem__(0, nn.Linear(2, 3, dtype=old.DTYPE)),
            lambda m: m.pair[0].weight.data.fill_(float('nan')),
        )
        for mutate in mutations:
            bad = deepcopy(source)
            mutate(bad)
            with self.subTest(mutation=mutate), self.assertRaises(ValueError):
                DomainKernel.from_legacy(bad)

    def test_three_entity_nonalias_forecasts_and_mode_updates_match_all_four_legacy_arms(self):
        for config in CONFIGS:
            source = old.JointKernel(**config)
            model = DomainKernel.from_legacy(source)
            x = torch.tensor([[0., 1., 0.], [1., 1., 0.]], dtype=old.DTYPE)
            state = source.initial(2)
            unchanged = old.fingerprint(model.state_dict())
            for action in (actions((0, 0, 1, -1), (0, 2, 0, -1)),
                           actions((1, 2, -1, 1), (1, 0, -1, 0)),
                           actions((2, -1, -1, -1), (2, -1, -1, -1))):
                with self.subTest(config=config, action=action.tolist()):
                    reference, pending_ref = source.predict(x, action, state)
                    actual, pending = model.predict(x, action, state)
                    torch.testing.assert_close(actual, reference, atol=1e-12, rtol=0)
                    torch.testing.assert_close(pending, pending_ref, atol=1e-12, rtol=0)
                    next_state = model.receive(pending, x)
                    torch.testing.assert_close(next_state, source.receive(pending_ref, x), atol=1e-12, rtol=0)
                    state = next_state
            self.assertEqual(unchanged, old.fingerprint(model.state_dict()))

    def test_every_domain_action_and_configuration_is_normalized_with_coherent_geometry(self):
        for config in CONFIGS:
            model = DomainKernel(**config)
            for entities in model.supported_entities:
                x = torch.tensor(d.binary_worlds(entities), dtype=old.DTYPE)
                state = model.initial(len(x))
                for action in ((0, 0, entities - 1, -1), (0, entities - 1, entities - 1, -1),
                               (1, entities - 1, -1, 1), (2, -1, -1, -1)):
                    with self.subTest(config=config, entities=entities, action=action):
                        a = actions(*([action] * len(x)))
                        before = (x.clone(), a.clone(), state.clone())
                        logp, pending = model.predict(x, a, state)
                        self.assertEqual(tuple(logp.shape), (2 ** entities, 2 ** entities))
                        self.assertEqual(tuple(pending.shape), (2 ** entities, 2, 2 ** entities))
                        torch.testing.assert_close(logp.logsumexp(-1), torch.zeros(len(x), dtype=old.DTYPE),
                                                   atol=1e-12, rtol=0)
                        for actual, original in zip((x, a, state), before):
                            self.assertTrue(torch.equal(actual, original))

    def test_alias_conditions_each_mode_before_mixing_without_forcing_a_physical_outcome(self):
        model = DomainKernel(persistence=True, role_tying=False)
        model.pair = FixedPair([math.log(p) for p in (.1, .2, .3, .4)])
        model.pair_other = FixedPair([math.log(p) for p in (.4, .1, .3, .2)])
        x = torch.ones(1, 6, dtype=old.DTYPE)
        action = actions((0, 2, 2, -1))
        state = torch.tensor([[math.log(.8), math.log(.2)]], dtype=old.DTYPE)
        logp, _ = model.predict(x, action, state)
        zero_world = x.clone(); zero_world[0, 2] = 0
        zero = int(d.world_index(zero_world)[0]); one = 63
        self.assertEqual(int(torch.isfinite(logp).sum()), 2)
        self.assertAlmostEqual(float(logp[0, zero].exp().detach()), .8 * (.1 / .5) + .2 * (.4 / .6))
        self.assertAlmostEqual(float(logp[0, one].exp().detach()), .8 * (.4 / .5) + .2 * (.2 / .6))
        self.assertGreater(float(logp[0, one].exp().detach()), .5)  # Identity is supplied; a zero outcome is not.
        torch.testing.assert_close(model.alias_log_mass(x, action),
            torch.tensor([[math.log(.5), math.log(.6)]], dtype=old.DTYPE), atol=1e-12, rtol=0)

    def test_tiny_finite_alias_mass_survives_and_genuinely_empty_diagonal_fails(self):
        model = DomainKernel(persistence=True)
        model.pair = FixedPair([-1000., 0., 0., -1001.])
        x = torch.zeros(1, 4, dtype=old.DTYPE)
        action = actions((0, 0, 0, -1))
        retained = model.alias_log_mass(x, action)
        self.assertTrue(torch.isfinite(retained).all())
        self.assertTrue((retained < -999).all())
        logp, _ = model.predict(x, action, model.initial(1))
        self.assertAlmostEqual(float(logp[0, 0].exp().detach()), 1 / (1 + math.exp(-1)), places=12)
        self.assertAlmostEqual(float(logp[0, 8].exp().detach()), 1 / (1 + math.exp(1)), places=12)
        model.pair = FixedPair([-torch.inf, 0., 0., -torch.inf])
        with self.assertRaisesRegex(ValueError, 'diagonal support'):
            model.predict(x, action, model.initial(1))
        distinct = actions((0, 0, 1, -1))
        logp, _ = model.predict(x, distinct, model.initial(1))
        self.assertAlmostEqual(float(logp.logsumexp(-1)[0].detach()), 0.)

    def test_background_persistence_is_supplied_only_to_the_declared_arm(self):
        x = torch.tensor([[1., 0., 1., 0., 1.]], dtype=old.DTYPE)
        a = actions((0, 0, 0, -1))
        learned, fixed = DomainKernel(), DomainKernel(persistence=True)
        p, _ = learned.predict(x, a, learned.initial(1))
        q, _ = fixed.predict(x, a, fixed.initial(1))
        self.assertEqual(int(torch.isfinite(p).sum()), 32)
        self.assertEqual(int(torch.isfinite(q).sum()), 2)
        worlds = torch.tensor(d.binary_worlds(5), dtype=torch.long)
        possible = worlds[torch.isfinite(q[0])]
        self.assertTrue(torch.equal(possible[:, 1:], x[:, 1:].long().expand(2, -1)))

    def test_identity_permutation_preserves_full_distributions_including_self_contact(self):
        mapping = [2, 5, 1, 0, 4, 3]  # new slot -> old slot
        inverse = [mapping.index(i) for i in range(6)]
        worlds = torch.tensor(d.binary_worlds(6), dtype=torch.long)
        new_index = d.world_index(worlds[:, mapping])
        x = torch.tensor([[0., 1., 1., 0., 1., 0.]], dtype=old.DTYPE)
        for config in CONFIGS:
            model = DomainKernel(**config)
            for left, right in ((1, 4), (2, 2)):
                a, b = actions((0, left, right, -1)), actions((0, inverse[left], inverse[right], -1))
                p, _ = model.predict(x, a, model.initial(1))
                q, _ = model.predict(x[:, mapping], b, model.initial(1))
                torch.testing.assert_close(p, q[:, new_index], atol=1e-12, rtol=0)

    def test_alias_and_partial_zero_support_preserve_finite_training_gradients(self):
        for config in CONFIGS:
            model = DomainKernel(**config)
            x = torch.tensor([[0., 1., 0., 1., 0., 1.]], dtype=old.DTYPE)
            state, losses = model.initial(1), []
            for action in ((0, 1, 1, -1), (1, 3, -1, 0), (0, 2, 4, -1), (2, -1, -1, -1)):
                logp, pending = model.predict(x, actions(action), state)
                losses.append(-logp[0, d.world_index(x)[0]])
                state = model.receive(pending, x)
            torch.stack(losses).mean().backward()
            self.assertTrue(all(p.grad is not None and bool(torch.isfinite(p.grad).all())
                                for p in model.parameters()))


if __name__ == '__main__':
    unittest.main()
