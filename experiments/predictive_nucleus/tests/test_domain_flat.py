"""Synthetic structural checks; no trained accuracy or transfer claims."""
from itertools import product
import unittest

import torch

from experiments.predictive_nucleus import domain_contract as domain
from experiments.predictive_nucleus.domain_flat import DomainFlatGRU
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint


def actions(*rows):
    return torch.tensor(rows, dtype=torch.long)


class DomainFlatTests(unittest.TestCase):
    def setUp(self):
        self.rng = torch.random.get_rng_state()
        torch.manual_seed(19)

    def tearDown(self):
        torch.random.set_rng_state(self.rng)

    def test_declared_flat_geometry_and_parameter_counts(self):
        for hidden in (3, 5, 8):
            for persistence in (False, True):
                model = DomainFlatGRU(hidden, persistence=persistence)
                self.assertEqual(model.supported_entities, (3, 4, 5, 6))
                self.assertTrue(model.supports_self_contact)
                self.assertEqual((model.hidden, model.persistence), (hidden, persistence))
                self.assertEqual((model.cell.input_size, model.head.out_features), (29, 64))
                self.assertEqual(sum(p.numel() for p in model.parameters()), 3 * hidden ** 2 + 157 * hidden + 64)
                self.assertTrue(all(p.dtype == DTYPE and p.device.type == 'cpu' for p in model.parameters()))
                self.assertEqual(list(model.named_buffers()), [])

    def test_every_domain_action_and_binary_anchor_has_normalized_joint_output(self):
        for persistence, entities in product((False, True), range(3, 7)):
            model = DomainFlatGRU(persistence=persistence)
            pre = torch.tensor(domain.binary_worlds(entities), dtype=DTYPE)
            events = ((0, entities - 1, entities - 2, -1), (0, entities - 1, entities - 1, -1),
                      (1, entities - 1, -1, 0), (1, entities - 1, -1, 1), (2, -1, -1, -1))
            for event in events:
                with self.subTest(persistence=persistence, entities=entities, event=event):
                    action = actions(*([event] * len(pre)))
                    logp, pending = model.predict(pre, action, model.initial(len(pre)))
                    self.assertEqual(logp.shape, (len(pre), 2 ** entities))
                    self.assertEqual(pending.shape, (len(pre), model.hidden))
                    self.assertTrue(torch.allclose(logp.logsumexp(-1), torch.zeros(len(pre), dtype=DTYPE),
                                                   atol=1e-12, rtol=0))
                    if persistence:
                        expected = domain.persistence_support(pre, action, pre.long())
                        self.assertTrue(torch.equal(torch.isfinite(logp), expected))
                    else:
                        self.assertTrue(torch.isfinite(logp).all())

    def test_padding_is_observable_and_roles_keep_alias_identity(self):
        model, captured = DomainFlatGRU(), []
        hook = model.cell.register_forward_pre_hook(lambda module, args: captured.append(args[0].clone()))
        try:
            for pre in ((1, 0, 1), (1, 0, 1, 0)):
                model.predict(torch.tensor([pre], dtype=DTYPE), actions((0, 2, 2, -1)), model.initial(1))
            model.predict(torch.zeros(1, 5, dtype=DTYPE), actions((1, 4, -1, 1)), model.initial(1))
            model.predict(torch.zeros(1, 6, dtype=DTYPE), actions((2, -1, -1, -1)), model.initial(1))
        finally:
            hook.remove()
        expected = [1, 0, 1, 0, 0, 0, 1, 1, 1, 0, 0, 0,
                    0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 0, 0]
        self.assertTrue(torch.equal(captured[0], torch.tensor([expected], dtype=DTYPE)))
        self.assertEqual((captured[0] != captured[1]).nonzero().tolist(), [[0, 9]])
        self.assertEqual(captured[2][0, 12:].tolist(), [0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0, 1])
        self.assertEqual(captured[3][0, 12:].tolist(), [0] * 12 + [0, 0, 1, 0, 0])

    def test_global_head_selects_padded_tail_zero_worlds_before_normalization(self):
        for entities in range(3, 7):
            model = DomainFlatGRU()
            with torch.no_grad():
                for parameter in model.parameters():
                    parameter.zero_()
                model.head.bias.copy_(torch.arange(64, dtype=DTYPE) / 10)
            pre, action = torch.zeros(1, entities, dtype=DTYPE), actions((2, -1, -1, -1))
            before, _ = model.predict(pre, action, model.initial(1))
            indices = [int(''.join(map(str, world + (0,) * (6 - entities))), 2)
                       for world in domain.binary_worlds(entities)]
            expected = model.head.bias[indices].log_softmax(-1)
            self.assertTrue(torch.equal(before[0], expected))
            invalid = [i for i in range(64) if i not in indices]
            with torch.no_grad():
                model.head.bias[invalid] = 1000
            after, _ = model.predict(pre, action, model.initial(1))
            self.assertTrue(torch.equal(before, after))

    def test_persistence_matches_shared_support_and_alias_is_one_unforced_bit(self):
        model, kernel = DomainFlatGRU(persistence=True), DomainKernel(persistence=True)
        for entities in range(3, 7):
            pre = torch.zeros(1, entities, dtype=DTYPE)
            for event in ((0, entities - 1, entities - 1, -1), (0, 0, entities - 1, -1),
                          (1, entities - 1, -1, 1), (2, -1, -1, -1)):
                left, _ = model.predict(pre, actions(event), model.initial(1))
                right, _ = kernel.predict(pre, actions(event), kernel.initial(1))
                self.assertTrue(torch.equal(torch.isfinite(left), torch.isfinite(right)))
        with torch.no_grad():
            for parameter in model.parameters():
                parameter.zero_()
            model.head.bias[1] = 5
        logp, _ = model.predict(torch.zeros(1, 6, dtype=DTYPE), actions((0, 5, 5, -1)), model.initial(1))
        self.assertEqual(torch.isfinite(logp).nonzero().tolist(), [[0, 0], [0, 1]])
        self.assertGreater(float(logp[0, 1].detach().exp()), .99)

    def test_finite_underflow_is_preserved_and_structural_zeros_remain_exact(self):
        model = DomainFlatGRU(persistence=True)
        with torch.no_grad():
            for parameter in model.parameters():
                parameter.zero_()
            model.head.bias[1] = -1000
        logp, _ = model.predict(torch.zeros(1, 6, dtype=DTYPE), actions((0, 5, 5, -1)), model.initial(1))
        self.assertEqual(float(logp[0, 1].detach()), -1000)
        self.assertEqual(float(logp[0, 1].detach().exp()), 0)
        self.assertTrue(torch.isneginf(logp[0, 2:]).all())

    def test_sequence_has_finite_gradients_in_every_domain_and_persistence_arm(self):
        for entities, persistence in product(range(3, 7), (False, True)):
            model = DomainFlatGRU(persistence=persistence)
            pre, state, losses = torch.zeros(1, entities, dtype=DTYPE), model.initial(1), []
            events = ((0, entities - 1, entities - 1, -1), (1, 0, -1, 1),
                      (0, 0, entities - 1, -1), (2, -1, -1, -1))
            for step, event in enumerate(events):
                logp, pending = model.predict(pre, actions(event), state)
                post = pre.clone()
                if step < 3:
                    slot = entities - 1 if step == 0 else 0
                    post[:, slot] = 1 - post[:, slot]
                losses.append(-logp[0, domain.world_index(post)[0]])
                state, pre = model.receive(pending, post), post
            torch.stack(losses).mean().backward()
            self.assertTrue(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in model.parameters()))
            self.assertGreater(float(model.cell.weight_hh.grad.abs().sum()), 0)

    def test_prediction_and_feedback_preserve_inputs_weights_and_rng(self):
        model = DomainFlatGRU()
        pre = torch.tensor([[1, 0, 0, 1, 0]], dtype=DTYPE)
        action, state = actions((0, 4, 4, -1)), model.initial(1)
        original = (pre.clone(), action.clone(), state.clone())
        weights, rng = fingerprint(model.state_dict()), torch.random.get_rng_state()
        one, pending = model.predict(pre, action, state)
        two, repeated = model.predict(pre, action, state)
        self.assertTrue(torch.equal(one, two) and torch.equal(pending, repeated))
        self.assertIs(model.receive(pending, pre), pending)
        self.assertNotEqual(pending.data_ptr(), state.data_ptr())
        self.assertTrue(all(torch.equal(a, b) for a, b in zip((pre, action, state), original, strict=True)))
        self.assertEqual(weights, fingerprint(model.state_dict()))
        self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))

    def test_invalid_configuration_observations_actions_and_state_are_rejected(self):
        for hidden, persistence in ((0, False), (True, False), (3.0, False), (4, 0)):
            with self.assertRaises(ValueError):
                DomainFlatGRU(hidden, persistence=persistence)
        model, pre, action = DomainFlatGRU(), torch.zeros(1, 3, dtype=DTYPE), actions((0, 0, 0, -1))
        for size in (0, -1, True, 1.0):
            with self.assertRaises(ValueError):
                model.initial(size)
        for bad in (pre.float(), pre - 1, torch.zeros(1, 2, dtype=DTYPE), torch.zeros(1, 7, dtype=DTYPE)):
            with self.assertRaises(ValueError):
                model.predict(bad, action, model.initial(1))
        for bad in (action.float(), actions((0, 3, 0, -1)), actions((2, 0, -1, -1))):
            with self.assertRaises(ValueError):
                model.predict(pre, bad, model.initial(1))
        for bad in (model.initial(2), model.initial(1).float(),
                    torch.full((1, 8), torch.inf, dtype=DTYPE), torch.full((1, 8), torch.nan, dtype=DTYPE)):
            with self.assertRaises(ValueError):
                model.predict(pre, action, bad)
            with self.assertRaises(ValueError):
                model.receive(bad, pre)
        with self.assertRaises(ValueError):
            model.receive(model.initial(1), pre - 1)


if __name__ == '__main__':
    unittest.main()
