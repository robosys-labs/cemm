"""Synthetic scheduler invariants; no fitted checkpoints or study predictions."""
from itertools import product
import math
import unittest

import torch
from torch import nn

from experiments.predictive_nucleus import domain_contract as domain
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint
from experiments.predictive_nucleus.timing_kernel import TimingKernel


class FixedPair(nn.Module):
    def __init__(self, values):
        super().__init__()
        self.register_buffer('values', torch.tensor(values, dtype=DTYPE))

    def forward(self, inputs):
        return self.values.expand(len(inputs), -1)


def contacts(*pairs):
    return torch.tensor([[[0, a, b, -1] for a, b in pairs]], dtype=torch.long)


def oracle(model, pre, actions, prior, timing):
    """Small probability-space enumeration independent of the adapter's reductions."""
    n, x = pre.shape[1], pre[0].tolist()
    worlds = domain.binary_worlds(n)
    result = torch.zeros(2, 2 ** n, dtype=DTYPE)
    for mode in (0, 1):
        mass = math.exp(float(prior[0, mode]))
        certain = torch.full((1, 2), -torch.inf, dtype=DTYPE)
        certain[0, mode] = 0.
        if timing == 'ordered':
            first, _ = model.predict(pre, actions[:, 0], certain)
            for middle, probability in zip(worlds, first[0].exp().tolist(), strict=True):
                second, _ = model.predict(torch.tensor([middle], dtype=DTYPE), actions[:, 1], certain)
                result[mode] += mass * probability * second[0].exp()
            continue
        pairs, probabilities = actions[0, :, 1:3].tolist(), []
        for a, b in pairs:
            inputs = torch.tensor([[x[a], x[b]]], dtype=DTYPE)
            if mode == 0:
                logits = model.pair(inputs)
            elif model.role_tying:
                logits = model.pair(inputs.flip(-1))[:, [0, 2, 1, 3]]
            else:
                logits = model.pair_other(inputs)
            probabilities.append(logits.softmax(-1)[0].tolist())
        spectators = [i for i in range(n) if all(i not in pair for pair in pairs)]
        background = {}
        for i in spectators:
            if model.persistence:
                background[i] = [float(x[i] == bit) for bit in (0, 1)]
            else:
                context = torch.tensor([[x[i], 1., 0., 0.]], dtype=DTYPE)
                background[i] = model.background(context).softmax(-1)[0].tolist()
        for left, right in product(range(4), repeat=2):
            changed = [False] * n
            probability = mass * probabilities[0][left] * probabilities[1][right]
            for pair, output in zip(pairs, (left, right), strict=True):
                for coordinate, bit in zip(pair, divmod(output, 2), strict=True):
                    changed[coordinate] |= bit != x[coordinate]
            merged = [int(bit) ^ int(change) for bit, change in zip(x, changed, strict=True)]
            for values in product((0, 1), repeat=len(spectators)):
                final, p = merged.copy(), probability
                for coordinate, bit in zip(spectators, values, strict=True):
                    final[coordinate] = bit
                    p *= background[coordinate][bit]
                index = sum(bit << (n - i - 1) for i, bit in enumerate(final))
                result[mode, index] += p
    return result[None]


class TimingKernelTests(unittest.TestCase):
    def setUp(self):
        self.rng = torch.random.get_rng_state()
        torch.manual_seed(2067)

    def tearDown(self):
        torch.random.set_rng_state(self.rng)

    def test_single_contact_is_bitwise_native_including_pending_mode_joint(self):
        for config in ({}, {'persistence': True}, {'role_tying': False}):
            model = DomainKernel(**config).eval()
            adapter = TimingKernel(model)
            for n in (3, 6):
                pre = torch.tensor([[i % 2 for i in range(n)]], dtype=DTYPE)
                group = contacts((n - 1, 0))
                state = torch.tensor([[math.log(.2), math.log(.8)]], dtype=DTYPE)
                expected = model.predict(pre, group[:, 0], state)
                for timing in ('ordered', 'common_snapshot'):
                    actual = adapter.predict(pre, group, timing=timing, state=state)
                    for a, b in zip(actual, expected, strict=True):
                        self.assertTrue(torch.equal(a, b))

    def test_both_schedulers_match_independent_full_probability_enumeration(self):
        for config in ({}, {'persistence': True}, {'role_tying': False}):
            model = DomainKernel(**config).eval()
            adapter = TimingKernel(model)
            for n, pairs in ((3, ((0, 1), (1, 2))), (4, ((0, 1), (2, 3))),
                             (6, ((4, 0), (0, 2)))):
                pre = torch.tensor([[i % 2 for i in range(n)]], dtype=DTYPE)
                group = contacts(*pairs)
                state = torch.tensor([[math.log(.37), math.log(.63)]], dtype=DTYPE)
                for timing in ('ordered', 'common_snapshot'):
                    with self.subTest(config=config, n=n, timing=timing):
                        raw, joint = adapter.predict(pre, group, timing=timing, state=state)
                        expected = oracle(model, pre, group, state, timing)
                        torch.testing.assert_close(joint.exp(), expected, atol=1e-13, rtol=0)
                        torch.testing.assert_close(raw.exp(), expected.sum(1), atol=1e-13, rtol=0)
                        self.assertAlmostEqual(float(raw.logsumexp(-1)[0].detach()), 0., places=12)

    def test_modes_are_shared_across_events_and_feedback_conditions_once(self):
        model = DomainKernel(persistence=True, role_tying=False).eval()
        model.pair = FixedPair([0., -torch.inf, -torch.inf, -torch.inf])
        model.pair_other = FixedPair([-torch.inf, -torch.inf, -torch.inf, 0.])
        adapter = TimingKernel(model)
        pre = torch.zeros(1, 4, dtype=DTYPE)
        prior = torch.tensor([[math.log(.3), math.log(.7)]], dtype=DTYPE)
        for timing in ('ordered', 'common_snapshot'):
            raw, joint = adapter.predict(pre, contacts((0, 1), (2, 3)), timing=timing, state=prior)
            self.assertEqual(torch.isfinite(raw[0]).nonzero().flatten().tolist(), [0, 15])
            self.assertAlmostEqual(float(raw[0, 0].exp()), .3, places=12)
            self.assertAlmostEqual(float(raw[0, 15].exp()), .7, places=12)
            state = model.receive(joint, torch.ones_like(pre))
            self.assertTrue(torch.equal(state, torch.tensor([[-torch.inf, 0.]], dtype=DTYPE)))
            self.assertTrue(torch.equal(prior, torch.tensor([[math.log(.3), math.log(.7)]], dtype=DTYPE)))

    def test_overlapping_neutral_output_does_not_cancel_a_proposed_change(self):
        model = DomainKernel(persistence=True, role_tying=False).eval()
        # Both events emit 01: AB changes B, while BC reads original B=0.
        model.pair = FixedPair([-torch.inf, 0., -torch.inf, -torch.inf])
        model.pair_other = FixedPair([-torch.inf, 0., -torch.inf, -torch.inf])
        pre = torch.zeros(1, 3, dtype=DTYPE)
        raw, _ = TimingKernel(model).predict(pre, contacts((0, 1), (1, 2)),
            timing='common_snapshot', state=model.initial(1))
        self.assertEqual(torch.isfinite(raw[0]).nonzero().flatten().tolist(), [3])  # 011
        self.assertAlmostEqual(float(raw[0, 3]), 0., places=12)

    def test_snapshot_event_permutation_and_entity_renaming_preserve_full_joint(self):
        model = DomainKernel(role_tying=False).eval()
        adapter = TimingKernel(model)
        pre = torch.tensor([[0., 1., 1., 0., 1., 0.]], dtype=DTYPE)
        group = contacts((1, 4), (4, 2))
        prior = torch.tensor([[math.log(.15), math.log(.85)]], dtype=DTYPE)
        first = adapter.predict(pre, group, timing='common_snapshot', state=prior)
        permuted = adapter.predict(pre, group.flip(1), timing='common_snapshot', state=prior)
        for a, b in zip(first, permuted, strict=True):
            torch.testing.assert_close(a, b, atol=1e-12, rtol=0)
        mapping = [2, 5, 1, 0, 4, 3]
        inverse = [mapping.index(i) for i in range(6)]
        renamed = contacts(*[(inverse[a], inverse[b]) for a, b in group[0, :, 1:3].tolist()])
        worlds = torch.tensor(domain.binary_worlds(6), dtype=torch.long)
        indices = domain.world_index(worlds[:, mapping])
        for timing in ('ordered', 'common_snapshot'):
            p, pending = adapter.predict(pre, group, timing=timing, state=prior)
            q, other = adapter.predict(pre[:, mapping], renamed, timing=timing, state=prior)
            torch.testing.assert_close(p, q[:, indices], atol=1e-12, rtol=0)
            torch.testing.assert_close(pending, other[:, :, indices], atol=1e-12, rtol=0)

    def test_log_space_retains_finite_underflow_tails_and_exact_zero_support(self):
        model = DomainKernel(persistence=True, role_tying=False).eval()
        model.pair = FixedPair([0., -1000., -torch.inf, -torch.inf])
        model.pair_other = FixedPair([0., -1000., -torch.inf, -torch.inf])
        pre = torch.zeros(1, 4, dtype=DTYPE)
        for timing in ('ordered', 'common_snapshot'):
            raw, joint = TimingKernel(model).predict(pre, contacts((0, 1), (2, 3)),
                timing=timing, state=model.initial(1))
            self.assertEqual(torch.isfinite(raw[0]).nonzero().flatten().tolist(), [0, 1, 4, 5])
            self.assertAlmostEqual(float(raw[0, 5]), -2000., places=10)
            self.assertEqual(float(raw[0, 5].exp()), 0.)
            self.assertTrue(torch.isneginf(raw[0, 15]))
            self.assertFalse(bool(torch.isnan(joint).any()))

    def test_batch_forecasts_are_pure_and_agree_with_individual_forecasts(self):
        model = DomainKernel().eval()
        adapter = TimingKernel(model)
        pre = torch.tensor([[0., 1., 0., 1.], [1., 0., 1., 0.]], dtype=DTYPE)
        group = torch.cat((contacts((0, 1), (1, 3)), contacts((2, 0), (2, 1))))
        prior = torch.tensor([[math.log(.3), math.log(.7)], [0., -torch.inf]], dtype=DTYPE)
        saved, tensors = fingerprint(model.state_dict()), [x.clone() for x in (pre, group, prior)]
        for timing in ('ordered', 'common_snapshot'):
            outputs = adapter.predict(pre, group, timing=timing, state=prior)
            singles = [adapter.predict(pre[i:i+1], group[i:i+1], timing=timing,
                        state=prior[i:i+1]) for i in range(2)]
            for j, output in enumerate(outputs):
                torch.testing.assert_close(output, torch.cat([s[j] for s in singles]), atol=1e-12, rtol=0)
            for before, after in zip(tensors, (pre, group, prior), strict=True):
                self.assertTrue(torch.equal(before, after))
        self.assertEqual(saved, fingerprint(model.state_dict()))

    def test_rejects_unsupported_mode_memory_actions_shapes_and_aliases(self):
        with self.assertRaises(ValueError):
            TimingKernel(DomainKernel(memory=False))
        adapter = TimingKernel(DomainKernel())
        pre = torch.zeros(1, 3, dtype=DTYPE)
        prior = adapter.model.initial(1)
        invalid = (
            (contacts((0, 1), (1, 2)), 'simultaneous', prior),
            (contacts((0, 1), (1, 2), (2, 0)), 'ordered', prior),
            (contacts((0, 0), (1, 2)), 'common_snapshot', prior),
            (contacts((0, 3), (1, 2)), 'ordered', prior),
            (contacts((0, 1), (1, 2)).double(), 'ordered', prior),
            (contacts((0, 1), (1, 2))[0], 'ordered', prior),
            (torch.tensor([[[1, 0, -1, 1], [0, 1, 2, -1]]]), 'ordered', prior),
            (contacts((0, 1), (1, 2)), 'ordered', torch.zeros(1, 2, dtype=DTYPE)),
        )
        for group, timing, state in invalid:
            with self.subTest(shape=group.shape, timing=timing), self.assertRaises(ValueError):
                adapter.predict(pre, group, timing=timing, state=state)


if __name__ == '__main__':
    unittest.main()
