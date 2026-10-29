"""Successor repair regressions, not a trained-performance or challenge study."""
from collections import Counter
from copy import deepcopy
import json
import math
import unittest

import numpy as np
import torch

from experiments.predictive_nucleus import active_paths as active, masked_replay as old
from experiments.predictive_nucleus.active_participant import Session
from experiments.predictive_nucleus.empirical_joint import SensorMemory, context
from experiments.predictive_nucleus.informative_curriculum import model_factories
from experiments.predictive_nucleus.joint_objective import JointKernel, fingerprint


def bits(*rows):
    return torch.tensor(rows, dtype=torch.float64)


def actions(*rows):
    return torch.tensor(rows, dtype=torch.long)


OBSERVE = (2, -1, -1, -1)
SET_C = (1, 2, -1, 0)
CONTACT = (0, 0, 1, -1)
ANCHOR = (1, 1, 0)


def visible(x):
    return bits(*x), torch.tensor([[b != -1 for b in row] for row in x], dtype=torch.bool)


def add(memory, pre, action, past, post):
    key, order = context(tuple(pre), action, past, memory.mode)
    memory.table[key] = Counter({tuple(post[i] for i in order): 1})


class HistoryModel:
    """Two histories converge to the same state, but predict different futures."""
    def initial(self, n):
        return torch.zeros(n, 2, dtype=torch.float64)

    def predict(self, pre, action, state):
        logp = torch.full((len(pre), 8), -torch.inf, dtype=torch.float64)
        for i, (phase, remembered) in enumerate(state.tolist()):
            if phase == 0:
                logp[i, [0, 4]] = -math.log(2)
            else:
                logp[i, 0 if phase == 1 else 1 + int(remembered)] = 0
        return logp, state.clone()

    def receive(self, pending, post):
        result = pending.clone()
        result[:, 1] = torch.where(pending[:, 0] == 0, post[:, 0], pending[:, 1])
        result[:, 0] += 1
        return result


class RepairTests(unittest.TestCase):
    def setUp(self):
        self.rng = torch.random.get_rng_state()
        self.addCleanup(torch.random.set_rng_state, self.rng)
        self.threads = torch.get_num_threads()
        torch.set_num_threads(1)
        self.addCleanup(torch.set_num_threads, self.threads)
        torch.manual_seed(7)

    def test_frozen_zero_path_defect_remains_reproducible(self):
        f = old.NeuralPaths(JointKernel(persistence=True), bits(ANCHOR))
        with torch.inference_mode():
            for _ in range(2):
                f.predict(actions(OBSERVE)); f.receive(*visible([(-1, -1, -1)]))
            self.assertEqual(f.weight.shape, (1, 64))
            self.assertEqual(int(torch.isfinite(f.weight).sum()), 1)
            f.predict(actions(OBSERVE))
            with self.assertRaisesRegex(ValueError, 'path bound'):
                f.receive(*visible([(-1, -1, -1)]))

    def test_known_state_survives_128_missing_observations_at_one_live_path(self):
        f = active.NeuralPaths(JointKernel(persistence=True), bits(ANCHOR), limit=1)
        for _ in range(128):
            p, answered = f.predict(actions(OBSERVE))
            self.assertEqual(p[0, 6], 0.)
            self.assertEqual(int(torch.isfinite(p).sum()), 1)
            self.assertTrue(answered[0])
            f.receive(*visible([(-1, -1, -1)]))
            self.assertEqual(f.weight.tolist(), [0.])
            self.assertEqual(f.bits.tolist(), [list(ANCHOR)])
            self.assertEqual(f.diagnostic['live_paths'], [1])

    def test_budget_is_per_episode_and_dead_padding_never_reenters(self):
        f = active.NeuralPaths(JointKernel(persistence=True), bits((0, 0, 0), (1, 1, 0)), limit=4)
        f.predict(actions(OBSERVE, CONTACT))
        f.receive(*visible([(-1, -1, -1), (-1, -1, 0)]))
        self.assertEqual(torch.bincount(f.owner).tolist(), [1, 4])
        self.assertEqual(len(f.weight), 5)
        for _ in range(10):
            f.predict(actions(OBSERVE, OBSERVE))
            f.receive(*visible([(-1, -1, -1), (-1, -1, -1)]))
            self.assertEqual(torch.bincount(f.owner).tolist(), [1, 4])
            self.assertTrue(torch.isfinite(f.weight).all())

    def test_distinct_recurrent_histories_are_not_merged_after_state_convergence(self):
        f = active.NeuralPaths(HistoryModel(), bits((0, 0, 0)), limit=2)
        f.predict(actions(OBSERVE)); f.receive(*visible([(-1, -1, -1)]))
        f.predict(actions(OBSERVE)); f.receive(*visible([(0, 0, 0)]))
        self.assertEqual(f.bits.tolist(), [[0, 0, 0], [0, 0, 0]])
        self.assertEqual(len(f.weight), 2)
        p, _ = f.predict(actions(OBSERVE))
        self.assertTrue(torch.equal(p[0, [1, 2]], torch.full((2,), -math.log(2), dtype=torch.float64)))

    def test_tiny_positive_log_mass_counts_even_when_exp_underflows(self):
        class Tiny(HistoryModel):
            def predict(self, pre, action, state):
                p = torch.full((len(pre), 8), -torch.inf, dtype=torch.float64)
                p[:, 0], p[:, 1] = 0., -1000.
                return p, state.clone()
        f = active.NeuralPaths(Tiny(), bits((0, 0, 0)), limit=1)
        f.predict(actions(OBSERVE))
        before = f.weight.clone()
        with self.assertRaisesRegex(ValueError, 'live path bound'):
            f.receive(*visible([(-1, -1, -1)]))
        self.assertTrue(torch.equal(before, f.weight))
        f = active.NeuralPaths(Tiny(), bits((0, 0, 0)), limit=2)
        f.predict(actions(OBSERVE)); f.receive(*visible([(-1, -1, -1)]))
        self.assertEqual(f.weight.tolist(), [0., -1000.])
        self.assertEqual(float(f.weight[1].exp()), 0.)

    def test_true_positive_path_explosion_still_fails_without_pruning(self):
        f = active.NeuralPaths(JointKernel(), bits(ANCHOR), limit=8)
        f.predict(actions(OBSERVE)); f.receive(*visible([(-1, -1, -1)]))
        self.assertEqual(len(f.weight), 8)
        f.predict(actions(OBSERVE))
        with self.assertRaisesRegex(ValueError, 'live path bound'):
            f.receive(*visible([(-1, -1, -1)]))
        self.assertEqual(len(f.weight), 8)

    def test_inconsistent_feedback_is_explicit_and_does_not_commit_state(self):
        f = active.NeuralPaths(JointKernel(persistence=True), bits(ANCHOR))
        f.predict(actions(OBSERVE))
        snapshot = (f.bits.clone(), f.weight.clone(), f.state.clone(), f.owner.clone())
        with self.assertRaisesRegex(ValueError, 'outside model support'):
            f.receive(*visible([(0, 0, 0)]))
        for value, before in zip((f.bits, f.weight, f.state, f.owner), snapshot):
            self.assertTrue(torch.equal(value, before))

    def test_batched_predictions_match_individual_reference_with_different_masks(self):
        model = JointKernel()
        f = active.NeuralPaths(model, bits(ANCHOR, (0, 1, 0)))
        references = [old.NeuralPaths(model, bits(row)) for row in (ANCHOR, (0, 1, 0))]
        with torch.inference_mode():
            for t in range(2):
                p, _ = f.predict(actions(OBSERVE, OBSERVE))
                for i, reference in enumerate(references):
                    q, _ = reference.predict(actions(OBSERVE))
                    self.assertTrue(torch.allclose(p[i], q[0], atol=1e-12, rtol=0))
                if t == 0:
                    rows = [(1, -1, 0), (-1, -1, -1)]
                    f.receive(*visible(rows))
                    for reference, row in zip(references, rows):
                        reference.receive(*visible([row]))

    def test_all_six_models_preserve_valid_reference_forecasts_and_weights(self):
        for name, factory in model_factories().items():
            with self.subTest(model=name), torch.inference_mode():
                model = factory(); before = fingerprint(model.state_dict())
                new = active.NeuralPaths(model, bits(ANCHOR)); ref = old.NeuralPaths(model, bits(ANCHOR))
                for action, reading in ((CONTACT, (1, 0, 0)), ((1, 2, -1, 1), (1, 0, -1)),
                                        (OBSERVE, (1, 0, 1)), ((0, 2, 0, -1), None)):
                    p, _ = new.predict(actions(action)); q, _ = ref.predict(actions(action))
                    self.assertTrue(torch.allclose(p, q, atol=1e-12, rtol=0))
                    if reading is not None:
                        new.receive(*visible([reading])); ref.receive(*visible([reading]))
                self.assertEqual(fingerprint(model.state_dict()), before)

    def test_forecast_and_feedback_order_is_explicit(self):
        for f in (active.NeuralPaths(JointKernel(), bits(ANCHOR)),
                  active.EmpiricalPaths(SensorMemory('local'), bits(ANCHOR))):
            with self.assertRaisesRegex(ValueError, 'prediction required'): f.receive(*visible([ANCHOR]))
            f.predict(actions(OBSERVE))
            with self.assertRaisesRegex(ValueError, 'feedback required'): f.predict(actions(OBSERVE))
            f.receive(*visible([ANCHOR]))
            with self.assertRaisesRegex(ValueError, 'prediction required'): f.receive(*visible([ANCHOR]))

    def test_invalid_feedback_and_action_do_not_sneak_hidden_bits(self):
        for factory in (lambda: active.NeuralPaths(JointKernel(), bits(ANCHOR)),
                        lambda: active.EmpiricalPaths(SensorMemory('local'), bits(ANCHOR))):
            f = factory()
            with self.assertRaises(ValueError): f.predict(actions((0, 0, 0, -1)))
            with self.assertRaises(ValueError): f.predict(actions(OBSERVE).float())
            f.predict(actions(OBSERVE))
            with self.assertRaises(ValueError): f.receive(bits(ANCHOR), torch.zeros(1, 3, dtype=torch.bool))
            with self.assertRaises(ValueError): f.receive(bits((2, 0, 0)), torch.ones(1, 3, dtype=torch.bool))
            with self.assertRaises(ValueError): f.receive(bits(ANCHOR).float(), torch.ones(1, 3, dtype=torch.bool))

    def test_invalid_anchor_limit_and_first_contact_policy_rejected(self):
        for anchor, limit in ((bits((0, 1, -1)), 64), (bits(ANCHOR), True), (bits(ANCHOR), 0),
                              (bits(ANCHOR).float(), 64)):
            with self.assertRaises(ValueError): active.NeuralPaths(JointKernel(), anchor, limit)
            with self.assertRaises(ValueError): active.EmpiricalPaths(SensorMemory('local'), anchor, limit=limit)
        with self.assertRaises(ValueError):
            active.EmpiricalPaths(SensorMemory('local'), bits(ANCHOR), first_contact=True)

    def test_frozen_empirical_defect_and_successor_recovery(self):
        memory = SensorMemory('local'); add(memory, ANCHOR, OBSERVE, (), ANCHOR)
        before = memory.digest()
        for cls, expected in ((old.EmpiricalPaths, False), (active.EmpiricalPaths, True)):
            f = cls(memory, bits(ANCHOR))
            _, yes = f.predict(actions(SET_C)); self.assertFalse(yes[0])
            f.receive(*visible([ANCHOR]))
            p, yes = f.predict(actions(OBSERVE))
            self.assertEqual(bool(yes[0]), expected)
            if expected: self.assertEqual(p[0, 6], 0.)
        self.assertEqual(memory.digest(), before)

    def test_local_partial_feedback_stays_unknown_then_full_feedback_recovers(self):
        memory = SensorMemory('local'); add(memory, ANCHOR, OBSERVE, (), ANCHOR)
        f = active.EmpiricalPaths(memory, bits(ANCHOR))
        f.predict(actions(SET_C)); f.receive(*visible([(-1, 1, 0)]))
        self.assertEqual(f.diagnostic['recovery'], ['missing_current_readings'])
        _, yes = f.predict(actions(OBSERVE)); self.assertFalse(yes[0])
        f.receive(*visible([ANCHOR]))
        self.assertEqual(f.diagnostic['recovery'], ['recovered_observed_context'])
        _, yes = f.predict(actions(OBSERVE)); self.assertTrue(yes[0])

    def test_prefix_recovery_requires_exact_observed_history_not_empty_reset(self):
        history = ((ANCHOR, SET_C, ANCHOR),)
        memory = SensorMemory('prefix'); add(memory, ANCHOR, OBSERVE, history, ANCHOR)
        f = active.EmpiricalPaths(memory, bits(ANCHOR))
        f.predict(actions(SET_C)); f.receive(*visible([ANCHOR]))
        self.assertEqual(f.paths[0][0][2], history)
        _, yes = f.predict(actions(OBSERVE)); self.assertTrue(yes[0])
        incomplete = active.EmpiricalPaths(memory, bits(ANCHOR))
        incomplete.predict(actions(SET_C)); incomplete.receive(*visible([(-1, 1, 0)]))
        incomplete.predict(actions(OBSERVE)); incomplete.receive(*visible([ANCHOR]))
        self.assertEqual(incomplete.diagnostic['recovery'], ['missing_relevant_history'])
        _, yes = incomplete.predict(actions(OBSERVE)); self.assertFalse(yes[0])

    def test_contact_recovers_with_observed_operands_despite_unknown_nonparticipant(self):
        post = (1, 0, -1); observed = (1, 0, 0)
        history = ((ANCHOR, CONTACT, post), (post, OBSERVE, observed))
        memory = SensorMemory('contact'); add(memory, observed, OBSERVE, history, observed)
        f = active.EmpiricalPaths(memory, bits(ANCHOR))
        f.predict(actions(CONTACT)); f.receive(*visible([post]))
        f.predict(actions(OBSERVE)); f.receive(*visible([observed]))
        self.assertEqual(f.diagnostic['recovery'], ['recovered_observed_context'])
        _, yes = f.predict(actions(OBSERVE)); self.assertTrue(yes[0])
        self.assertEqual(f.history[0][0][2][2], -1)  # never imputed

    def test_contact_unknown_operand_does_not_recover_from_new_current_state(self):
        memory = SensorMemory('contact'); add(memory, ANCHOR, OBSERVE, (), ANCHOR)
        f = active.EmpiricalPaths(memory, bits(ANCHOR))
        f.predict(actions(CONTACT)); f.receive(*visible([(-1, 1, 0)]))
        f.predict(actions(OBSERVE)); f.receive(*visible([ANCHOR]))
        self.assertEqual(f.diagnostic['recovery'], ['missing_relevant_history'])
        _, yes = f.predict(actions(OBSERVE)); self.assertFalse(yes[0])

    def test_first_contact_recovers_without_fabricating_later_contact_observations(self):
        first = (ANCHOR, CONTACT, (1, 0, 0))
        memory = SensorMemory('contact'); add(memory, ANCHOR, OBSERVE, (first,), ANCHOR)
        for first_only, expected in ((False, False), (True, True)):
            f = active.EmpiricalPaths(memory, bits(ANCHOR), first_contact=first_only)
            f.predict(actions(CONTACT)); f.receive(*visible([(1, 0, 0)]))
            f.predict(actions(CONTACT)); f.receive(*visible([(-1, 1, 0)]))
            f.predict(actions(OBSERVE)); f.receive(*visible([ANCHOR]))
            _, yes = f.predict(actions(OBSERVE)); self.assertEqual(bool(yes[0]), expected)
            self.assertEqual(f.history[0][1][2][0], -1)

    def test_missing_first_contact_is_not_replaced_with_later_known_contact(self):
        memory = SensorMemory('contact'); add(memory, ANCHOR, OBSERVE, (), ANCHOR)
        f = active.EmpiricalPaths(memory, bits(ANCHOR), first_contact=True)
        f.predict(actions(CONTACT)); f.receive(*visible([(-1, 1, 0)]))
        f.predict(actions(OBSERVE)); f.receive(*visible([ANCHOR]))
        f.predict(actions(CONTACT)); f.receive(*visible([(1, 0, 0)]))
        self.assertEqual(f.diagnostic['recovery'], ['missing_relevant_history'])

    def test_supported_empirical_conflict_is_not_silently_resynchronized(self):
        memory = SensorMemory('local'); add(memory, ANCHOR, OBSERVE, (), ANCHOR)
        f = active.EmpiricalPaths(memory, bits(ANCHOR))
        f.predict(actions(OBSERVE)); before = deepcopy(f.paths)
        with self.assertRaisesRegex(ValueError, 'outside empirical support'):
            f.receive(*visible([(0, 0, 0)]))
        self.assertEqual(f.paths, before)
        self.assertEqual(f.history, [()])

    def test_partial_unknown_support_is_not_renormalized_away(self):
        memory = SensorMemory('local'); add(memory, ANCHOR, OBSERVE, (), ANCHOR)
        f = active.EmpiricalPaths(memory, bits(ANCHOR))
        f.paths = [[(.5, ANCHOR, ()), (.5, (0, 0, 0), ())]]
        _, yes = f.predict(actions(OBSERVE)); self.assertFalse(yes[0])
        f.receive(*visible([(-1, -1, 0)]))
        self.assertEqual(f.paths, [[]])
        f.predict(actions(OBSERVE)); f.receive(*visible([ANCHOR]))
        _, yes = f.predict(actions(OBSERVE)); self.assertTrue(yes[0])

    def test_mixed_batch_recovery_is_episode_local(self):
        memory = SensorMemory('local'); add(memory, ANCHOR, OBSERVE, (), ANCHOR)
        f = active.EmpiricalPaths(memory, bits(ANCHOR, ANCHOR))
        f.predict(actions(SET_C, SET_C)); f.receive(*visible([ANCHOR, (-1, 1, 0)]))
        _, yes = f.predict(actions(OBSERVE, OBSERVE))
        self.assertEqual(yes.tolist(), [True, False])

    def test_supported_empirical_path_matches_frozen_reference(self):
        for mode in ('local', 'prefix', 'contact'):
            memory = SensorMemory(mode); past = ()
            for _ in range(3):
                add(memory, ANCHOR, OBSERVE, past, ANCHOR)
                past += ((ANCHOR, OBSERVE, ANCHOR),)
            f, ref = active.EmpiricalPaths(memory, bits(ANCHOR)), old.EmpiricalPaths(memory, bits(ANCHOR))
            for _ in range(3):
                p, yes = f.predict(actions(OBSERVE)); q, okay = ref.predict(actions(OBSERVE))
                self.assertTrue(torch.equal(p, q)); self.assertTrue(np.array_equal(yes, okay))
                f.receive(*visible([ANCHOR])); ref.receive(*visible([ANCHOR]))

    def test_transport_uses_new_filter_and_reports_version_not_historical_result(self):
        s = Session(model=JointKernel(persistence=True))
        start = s.handle({'op': 'start', 'episode': 'x', 'ids': ['a', 'b', 'c'],
                         'observation': dict(zip('abc', ANCHOR))})
        self.assertEqual(start['implementation']['version'], 'active-inference-v2')
        for step in range(10):
            p = s.handle({'op': 'predict', 'episode': 'x', 'step': step,
                          'action': {'kind': 'observe', 'participants': []}})
            result = s.handle({'op': 'feedback', 'episode': 'x', 'step': step, 'receipt': p['receipt'],
                              'observation': dict.fromkeys('abc')})
            self.assertEqual(result['inference']['live_paths'], [1])
        self.assertFalse(s.handle({'op': 'end', 'episode': 'x'})['evaluated'])

    def test_transport_empirical_recovery_is_end_to_end_and_missingness_explicit(self):
        memory = SensorMemory('local'); add(memory, ANCHOR, OBSERVE, (), ANCHOR)
        s = Session(memory=memory, control='local')
        s.handle({'op': 'start', 'episode': 'x', 'ids': list('abc'), 'observation': dict(zip('abc', ANCHOR))})
        p = s.handle({'op': 'predict', 'episode': 'x', 'step': 0,
                      'action': {'kind': 'set', 'participants': ['c'], 'value': 0}})
        self.assertEqual(p['status'], 'ABSTAIN'); self.assertIsNone(p['log'])
        r = s.handle({'op': 'feedback', 'episode': 'x', 'step': 0, 'receipt': p['receipt'],
                      'observation': dict(zip('abc', ANCHOR))})
        self.assertEqual(r['inference']['recovery'], ['recovered_observed_context'])
        p = s.handle({'op': 'predict', 'episode': 'x', 'step': 1,
                      'action': {'kind': 'observe', 'participants': []}})
        self.assertEqual(p['status'], 'PREDICTED'); self.assertEqual(p['log']['values'][0][6], 0.)
        self.assertFalse(s.handle({'op': 'end', 'episode': 'x'})['evaluated'])


if __name__ == '__main__':
    unittest.main()
