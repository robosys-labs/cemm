"""Synthetic inference checks and evaluator feasibility; no saved-model scores."""
from copy import deepcopy
from io import StringIO
from itertools import product
import json
import unittest
from unittest.mock import patch

import numpy as np
import torch

from experiments.predictive_nucleus import masked_replay as m
from experiments.predictive_nucleus import sensor_transfer_data as d
from experiments.predictive_nucleus import comparison_scoring as s
from experiments.predictive_nucleus.comparison_run import replay as direct_replay
from experiments.predictive_nucleus.joint_objective import SensorBatch
from experiments.predictive_nucleus.informative_curriculum import model_factories
from experiments.predictive_nucleus.world import World, Action, step


def trace():
    x = torch.tensor([[[0, 1, 0]], [[1, 1, 0]], [[0, 1, 0]], [[0, 1, 0]]], dtype=torch.float64)
    a = torch.tensor([[[0, 0, 1, -1]], [[1, 0, -1, 0]], [[2, -1, -1, -1]]])
    return m.MaskedTrace(x, torch.ones_like(x, dtype=torch.bool), a)


class PersistentCoin(torch.nn.Module):
    """Synthetic two-world mechanism; hidden event outcome remains correlated."""
    def initial(self, n):
        return torch.full((n, 2), -np.log(2), dtype=torch.float64)
    def predict(self, pre, action, state):
        pending = torch.full((len(pre), 2, 8), -torch.inf, dtype=torch.float64)
        pending[:, 0, 0], pending[:, 1, 7] = state[:, 0], state[:, 1]
        return pending.logsumexp(1), pending
    def receive(self, pending, post):
        ids = (post.long() * torch.tensor([4, 2, 1])).sum(-1)
        selected = pending.gather(2, ids[:, None, None].expand(-1, 2, 1)).squeeze(-1)
        if not torch.isfinite(selected.logsumexp(-1)).all():
            raise AssertionError('receive called on impossible path')
        return selected - selected.logsumexp(-1, keepdim=True)


class MaskedInferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = torch.get_num_threads(); torch.set_num_threads(1)
    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.threads)
    def setUp(self):
        self.rng = torch.random.get_rng_state(); torch.manual_seed(7)
    def tearDown(self):
        torch.random.set_rng_state(self.rng)

    def test_all_six_full_sensor_paths_equal_direct_replay(self):
        t = trace()
        for name, factory in model_factories().items():
            with self.subTest(model=name):
                model = factory()
                actual = m.replay(t, StringIO(), model=model)
                expected = direct_replay(model, SensorBatch(t.readings, t.actions), StringIO())
                self.assertTrue(np.allclose(actual[1], expected[1], atol=1e-12, rtol=0))
                self.assertTrue(np.array_equal(actual[2], expected[2]))

    def test_missing_probe_retains_joint_world_correlation(self):
        model = PersistentCoin()
        paths = m.NeuralPaths(model, torch.zeros(1, 3, dtype=torch.float64))
        action = torch.tensor([[0, 0, 1, -1]])
        paths.predict(action)
        paths.receive(torch.full((1, 3), -1., dtype=torch.float64), torch.zeros(1, 3, dtype=torch.bool))
        raw, _ = paths.predict(action)
        self.assertEqual(torch.isfinite(raw).sum(), 2)
        self.assertTrue(torch.allclose(raw.exp()[0, [0, 7]], torch.tensor([.5, .5], dtype=torch.float64)))
        # A real single-bit measurement resolves the correlated state.
        paths.receive(torch.tensor([[1., -1., -1.]], dtype=torch.float64), torch.tensor([[True, False, False]]))
        raw, _ = paths.predict(action)
        self.assertEqual(raw.exp()[0, 7], 1.)
        self.assertEqual(raw.exp()[0, 0], 0.)

    def test_bound_fails_without_truncation(self):
        paths = m.NeuralPaths(PersistentCoin(), torch.zeros(1, 3, dtype=torch.float64), limit=4)
        paths.predict(torch.tensor([[0, 0, 1, -1]]))
        with self.assertRaisesRegex(ValueError, 'no pruning'):
            paths.receive(torch.full((1, 3), -1., dtype=torch.float64), torch.zeros(1, 3, dtype=torch.bool))

    def test_hidden_bits_cannot_be_smuggled_through_a_mask(self):
        t = trace(); mask = t.masks.clone(); mask[1, 0, 2] = False
        with self.assertRaisesRegex(ValueError, 'hidden readings'):
            m.MaskedTrace(t.readings, mask, t.actions).validate()

    def test_own_future_reading_does_not_change_its_forecast(self):
        t = trace(); model = model_factories()['flat']()
        prior = m.replay(t, StringIO(), model=model)[1]
        x = t.readings.clone(); x[2:, 0, 0] = 1 - x[2:, 0, 0]
        after = m.replay(m.MaskedTrace(x, t.masks, t.actions), StringIO(), model=model)[1]
        self.assertTrue(np.array_equal(prior[:2], after[:2]))

    def test_forecast_is_flushed_before_feedback(self):
        t, stream = trace(), StringIO()
        old = m.NeuralPaths.receive
        calls = []
        def checked(filter_, reading, mask):
            rows = [json.loads(line) for line in stream.getvalue().splitlines()]
            self.assertEqual(rows[-1]['kind'], 'normalized_forecast')
            self.assertEqual(rows[-1]['step'], len(calls))
            calls.append(1)
            return old(filter_, reading, mask)
        with patch.object(m.NeuralPaths, 'receive', new=checked):
            m.replay(t, stream, model=model_factories()['flat']())
        self.assertEqual(len(calls), 3)

    def test_unknown_empirical_branch_abstains_instead_of_discarding_mass(self):
        class Memory:
            def predict(self, pre, action, past):
                if not past:
                    return (.5, 0, 0, 0, 0, 0, 0, .5)
                return None if pre == (1, 1, 1) else (1., 0, 0, 0, 0, 0, 0, 0)
        f = m.EmpiricalPaths(Memory(), torch.zeros(1, 3))
        action = torch.tensor([[0, 0, 1, -1]])
        f.predict(action); f.receive(torch.full((1, 3), -1.), torch.zeros(1, 3, dtype=torch.bool))
        _, answered = f.predict(action)
        self.assertFalse(answered[0]); self.assertEqual(f.diagnostic['unsupported_positive_paths'], 1)

    def test_first_contact_is_explicit_context_abstraction(self):
        class Memory:
            def predict(self, pre, action, past):
                self.past = past
                return (1., 0, 0, 0, 0, 0, 0, 0)
        memory = Memory(); f = m.EmpiricalPaths(memory, torch.zeros(1, 3), first_contact=True)
        first = ((0, 0, 0), (0, 0, 1, -1), (0, 0, 0))
        second = ((0, 0, 0), (0, 1, 2, -1), (0, 0, 0))
        f.paths = [[(1., (0, 0, 0), (first, second))]]
        f.predict(torch.tensor([[0, 1, 0, -1]]))
        self.assertEqual(memory.past, (first,))

    def test_last_observed_updates_only_measured_coordinates(self):
        f = m.LastObserved(torch.tensor([[0., 1., 0.]], dtype=torch.float64))
        f.receive(torch.tensor([[1., -1., -1.]], dtype=torch.float64), torch.tensor([[True, False, False]]))
        p, _ = f.predict(None)
        self.assertEqual(p.exp()[0, 6], 1.)

    def test_inconsistent_visible_evidence_is_not_silently_repaired(self):
        f = m.NeuralPaths(PersistentCoin(), torch.zeros(1, 3, dtype=torch.float64))
        f.predict(torch.tensor([[0, 0, 1, -1]]))
        with self.assertRaisesRegex(ValueError, 'outside model support'):
            f.receive(torch.tensor([[0., 1., 0.]], dtype=torch.float64), torch.ones(1, 3, dtype=torch.bool))

    def test_malformed_actions_shapes_and_sensors_fail(self):
        t = trace()
        variants = [m.MaskedTrace(t.readings.float(), t.masks, t.actions),
                    m.MaskedTrace(t.readings, t.masks, t.actions + 20),
                    m.MaskedTrace(t.readings[:-1], t.masks[:-1], t.actions),
                    m.MaskedTrace(t.readings, t.masks.long(), t.actions)]
        for value in variants:
            with self.assertRaises(ValueError): value.validate()


class TransferFixtureTests(unittest.TestCase):
    def test_evaluator_matches_original_physics_and_separate_scalar_oracle(self):
        ids = ('a', 'b', 'c')
        actions = [(0, a, b, -1) for a in range(3) for b in range(3) if a != b]
        actions += [(1, a, -1, v) for a in range(3) for v in (0, 1)] + [(2, -1, -1, -1)]
        for bits, mode, action in product(d.WORLDS, (0, 1), actions):
            kind, a, b, value = action
            old = Action(('contact', 'set', 'observe')[kind], tuple(ids[i] for i in (a, b) if i >= 0),
                         value if kind == 1 else None)
            expected = step(World(ids, bits, mode), old).bits
            self.assertEqual(d.advance(bits, action, mode), expected)
            self.assertEqual(d.oracle_step(bits, action, mode), expected)

    def test_masks_keep_truth_separate_and_query_bounds_are_information_based(self):
        for family in ('reordered', 'reversed'):
            full, truth, _ = d.build(family, 'full')
            for policy in ('full', 'hidden_resets', 'hidden_probe'):
                trace_, y, oracle = d.build(family, policy)
                self.assertTrue(np.array_equal(y, truth))
                self.assertTrue(torch.equal(trace_.actions, full.actions))
                self.assertTrue((trace_.readings[~trace_.masks] == -1).all())
                self.assertAlmostEqual(oracle[6].max(-1).mean(), .625 if policy == 'hidden_probe' else 1.)
                # The oracle can be ambiguous; it never reads the private mode.
                gold = y[1:] @ np.array([4, 2, 1])
                self.assertTrue((np.take_along_axis(oracle, gold[..., None], -1) > 0).all())

    def test_hidden_probe_orientation_twins_have_identical_prequery_histories(self):
        for family in ('reordered', 'reversed'):
            for case in range(256):
                a = d.episode(case, family, 'hidden_probe')
                b = d.episode(case ^ 16, family, 'hidden_probe')
                self.assertTrue(np.array_equal(a[0][:7], b[0][:7]))
                self.assertTrue(np.array_equal(a[2], b[2]))

    def test_id_views_have_exact_oracle_equivariance_and_all_directions(self):
        t, truth, oracle = d.build('reordered', 'hidden_probe')
        with np.errstate(divide='ignore'):
            logp = np.log(oracle)
        report, _, _ = s.renaming(logp, np.ones(logp.shape[:2], dtype=bool), 256)
        self.assertEqual(report['max_tv'], 0.)
        self.assertEqual(tuple(t.readings.shape), (9, 1536, 3))
        self.assertEqual(len(set(tuple(a) for a in t.actions[6].tolist())), 6)

    def test_invalid_cases_are_not_coerced(self):
        for case in (True, -1, 256, 1.0):
            with self.assertRaises(ValueError): d.episode(case, 'reordered', 'full')
        with self.assertRaises(ValueError): d.episode(0, 'unknown', 'full')


if __name__ == '__main__':
    unittest.main()
