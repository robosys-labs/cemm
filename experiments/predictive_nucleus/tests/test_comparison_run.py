"""Synthetic arithmetic/replay tests plus a small full-pipeline CI smoke.

No production comparison fit occurs during ordinary invariant CI.
"""
from contextlib import redirect_stdout
from dataclasses import dataclass
from hashlib import sha256
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import torch

from experiments.predictive_nucleus import comparison_run as r
from experiments.predictive_nucleus import comparison_scoring as s


@dataclass
class ToyBatch:
    observations: torch.Tensor
    actions: torch.Tensor
    def validate(self):
        return self
    def digest(self):
        return sha256(self.observations.numpy().tobytes() + self.actions.numpy().tobytes()).hexdigest()


def fingerprint(state):
    return sha256(b''.join(x.detach().numpy().tobytes() for _, x in sorted(state.items()))).hexdigest()


class ToyModel(torch.nn.Module):
    def __init__(self, stream=None):
        super().__init__()
        self.register_buffer('fixed', torch.tensor(0.))
        self.stream = stream
        self.seen = 0
    def initial(self, n):
        return torch.zeros(n, dtype=torch.float64)
    def predict(self, pre, action, state):
        p = torch.full((len(pre), 8), -math.log(8), dtype=torch.float64)
        return p, state + 1
    def receive(self, pending, post):
        if self.stream:
            lines = [json.loads(x) for x in self.stream.getvalue().splitlines()]
            assert lines[-1]['kind'] == 'normalized_forecast'
            assert lines[-1]['step'] == self.seen
        self.seen += 1
        return pending


class ScoringTests(unittest.TestCase):
    def test_uniform_and_one_hot_scores_match_scalar_oracle(self):
        for p in ([.125] * 8, [0, 0, 1, 0, 0, 0, 0, 0], [.5, 0, 0, .5, 0, 0, 0, 0]):
            raw = torch.tensor([p] * 8, dtype=torch.float64).log()
            norm, correction = s.normalize(raw, np.ones(8, dtype=bool))
            scores = s.score(norm, np.ones(8, dtype=bool), s.WORLDS, s.WORLDS, raw.numpy())
            for i in range(8):
                self.assertAlmostEqual(scores['brier'][i], sum((v - int(k == i)) ** 2 for k, v in enumerate(p)))
                if p[i]:
                    self.assertAlmostEqual(scores['nll'][i], -math.log(p[i]))
                else:
                    self.assertTrue(np.isinf(scores['nll'][i]))
            self.assertTrue(np.all(np.abs(correction) <= 1e-10))
            summary = s.summary(scores)
            self.assertEqual(summary['queries'], 8)
            self.assertEqual(summary['correct'], 1)
            self.assertEqual(summary['nll_status'], 'infinite' if 0 in p else 'finite')

    def test_underflow_is_not_structural_infinity(self):
        raw = torch.tensor([[0., -1000., -math.inf, -math.inf, -math.inf, -math.inf, -math.inf, -math.inf]], dtype=torch.float64)
        norm, _ = s.normalize(raw, np.array([True]))
        scores = s.score(norm, np.array([True]), np.array([[0, 0, 1]]), np.array([[0, 0, 0]]))
        self.assertEqual(scores['nll'][0], 1000.)
        self.assertEqual(scores['underflow'][0], 1)
        self.assertEqual(s.summary(scores)['nll_status'], 'finite')
        encoded = s.log_record(norm)
        self.assertEqual(encoded['values'][0][1], -1000.)
        self.assertIsNone(encoded['values'][0][2])
        json.dumps(encoded, allow_nan=False)

    def test_invalid_mass_and_nonfinite_values_rejected_without_clipping(self):
        for values in ([0.] * 8, [float('nan')] * 8, [float('inf')] * 8, [-math.inf] * 8):
            with self.subTest(values=values), self.assertRaises(ValueError):
                s.normalize(torch.tensor([values], dtype=torch.float64), np.array([True]))
        raw = torch.full((1, 8), -math.log(8) + 5e-11, dtype=torch.float64)
        norm, mass = s.normalize(raw, np.array([True]))
        self.assertAlmostEqual(mass[0], 5e-11)
        self.assertTrue(np.allclose(np.exp(norm).sum(-1), 1.))

    def test_abstention_has_no_numeric_metric_or_probability(self):
        raw = torch.full((2, 8), -math.inf, dtype=torch.float64)
        raw[0, 0] = 0
        norm, _ = s.normalize(raw, np.array([True, False]))
        scores = s.score(norm, np.array([True, False]), np.zeros((2, 3), dtype=int), np.zeros((2, 3), dtype=int))
        result = s.summary(scores)
        self.assertEqual((result['queries'], result['answered'], result['correct'], result['abstained']), (2, 1, 1, 1))
        self.assertEqual(result['mean_nll'], 0.)
        only_missing = s.summary(scores, np.array([False, True]))
        self.assertEqual(only_missing['nll_status'], 'no_answers')
        self.assertIsNone(only_missing['mean_nll'])
        self.assertIsNone(only_missing['mean_brier'])

    def test_ties_and_ece_boundaries(self):
        p = np.zeros((3, 8))
        p[0, :2] = .5
        p[1, 0], p[1, 1:] = .9, .1 / 7
        p[2, 0] = 1
        norm, _ = s.normalize(torch.tensor(p).log(), np.ones(3, dtype=bool))
        scores = s.score(norm, np.ones(3, dtype=bool), np.zeros((3, 3), dtype=int), np.zeros((3, 3), dtype=int))
        self.assertEqual(scores['map'].tolist(), [0, 0, 0])
        self.assertEqual(scores['maximizers'].sum(-1).tolist(), [2, 1, 1])
        result = s.summary(scores)
        self.assertEqual(sum(b['count'] for b in result['ece_bins']), 3)
        self.assertAlmostEqual(result['ece_10'], (.5 + .1) / 3)

    def test_renaming_inverse_coordinates_and_tie_map_difference(self):
        physical = np.array([0, .5, .5, 0, 0, 0, 0, 0])
        vectors = []
        for mapping in s.PERMUTATIONS:
            inverse = np.argsort(mapping)
            renamed = np.zeros(8)
            for world, probability in zip(s.WORLDS, physical, strict=True):
                renamed[world[inverse] @ np.array([4, 2, 1])] = probability
            vectors.append(renamed)
        with np.errstate(divide='ignore'):
            logs = np.log(np.array([vectors]))
        result, tv, changed = s.renaming(logs, np.ones((1, 6), dtype=bool), 1)
        self.assertEqual(result['max_tv'], 0.)
        self.assertEqual(result['over_tolerance'], 0)
        self.assertGreater(result['map_changed'], 0)
        altered = logs.copy()
        altered[0, 1] = -math.log(8)
        self.assertGreater(s.renaming(altered, np.ones((1, 6), dtype=bool), 1)[0]['over_tolerance'], 0)

    def test_pairs_retain_exact_regressions_and_common_answered_subset(self):
        result = s.paired(np.array([1, 0, 1, 2, 2]), np.array([0, 1, 2, 1, 2]))
        self.assertEqual(result['correct_to_wrong'], [0])
        self.assertEqual(result['wrong_to_correct'], [1])
        self.assertEqual(result['correct_to_abstained'], [2])
        self.assertEqual(result['abstained_to_correct'], [3])
        self.assertEqual(result['common_answered'], 2)
        codes = np.ones((8, 12), dtype=np.uint8)
        codes[6, 6] = 2
        role = s.role_pairs(codes, 6, 2)
        self.assertEqual((role['pairs'], role['both_answered'], role['both_correct']), (6, 5, 5))

    def test_latency_nearest_rank(self):
        self.assertEqual(s.nearest_rank(list(range(20)), .95), 18)
        self.assertEqual(s.nearest_rank(list(range(20)), .5), 9)
        with self.assertRaises(ValueError):
            s.nearest_rank([], .95)


class ReplayTests(unittest.TestCase):
    def setUp(self):
        self.batch = ToyBatch(torch.zeros((3, 6, 3), dtype=torch.float64),
                              torch.tensor([[[2, -1, -1, -1]] * 6] * 2))
        self.joint_stub = patch.dict(sys.modules, {'experiments.predictive_nucleus.joint_objective':
                                                   SimpleNamespace(fingerprint=fingerprint)})
        self.joint_stub.start()
        self.addCleanup(self.joint_stub.stop)

    def test_records_precede_own_feedback_and_repeatable_no_mutation(self):
        stream = io.StringIO()
        model = ToyModel(stream)
        before = self.batch.digest()
        raw, norm, mask, _ = r.replay(model, self.batch, stream)
        self.assertEqual(model.seen, 2)
        self.assertEqual(raw.shape, (2, 6, 8))
        self.assertTrue(mask.all())
        self.assertEqual(before, self.batch.digest())
        self.assertEqual(len(stream.getvalue().splitlines()), 4)
        self.assertTrue(np.allclose(np.exp(norm).sum(-1), 1.))

    def test_invalid_forecast_retained_and_feedback_not_delivered(self):
        class Bad(ToyModel):
            def predict(self, pre, action, state):
                return torch.ones((len(pre), 8), dtype=torch.float64), state
        model, stream = Bad(), io.StringIO()
        with self.assertRaises(ValueError):
            r.replay(model, self.batch, stream)
        self.assertEqual(model.seen, 0)
        self.assertEqual(json.loads(stream.getvalue())['kind'], 'raw_forecast')

    def test_future_feedback_cannot_change_earlier_forecasts(self):
        raw, _, _, _ = r.replay(ToyModel(), self.batch, io.StringIO())
        self.batch.observations[2] = 1
        changed, _, _, _ = r.replay(ToyModel(), self.batch, io.StringIO())
        self.assertTrue(np.array_equal(raw, changed))

    def test_parameter_or_delivered_input_mutation_is_not_hidden(self):
        class Mutating(ToyModel):
            def receive(self, pending, post):
                self.fixed.add_(1)
                return pending
        with self.assertRaisesRegex(ValueError, 'changed weights'):
            r.replay(Mutating(), self.batch, io.StringIO())
        class MutatingInput(ToyModel):
            def receive(self, pending, post):
                post.fill_(1)
                return pending
        with self.assertRaisesRegex(ValueError, 'mutated delivered'):
            r.replay(MutatingInput(), self.batch, io.StringIO())

    def test_no_change_and_empirical_abstention_are_separate(self):
        raw, normalized, mask, _ = r.replay(None, self.batch, io.StringIO(), no_change=True)
        self.assertTrue(mask.all())
        self.assertTrue((np.exp(normalized)[..., 0] == 1).all())
        memory = SimpleNamespace(digest=lambda: 'same', predict=lambda *args: None)
        _, _, mask, _ = r.replay(None, self.batch, io.StringIO(), memory=memory)
        self.assertFalse(mask.any())


@unittest.skipUnless(importlib.util.find_spec('experiments.predictive_nucleus.joint_objective') is not None,
                     'requires the newer parent modules absent from the local retained source archive')
class FullPipelineTests(unittest.TestCase):
    def setUp(self):
        from experiments.predictive_nucleus.joint_objective import SensorBatch
        from experiments.predictive_nucleus.informative_curriculum import model_factories
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.threads = torch.get_num_threads()
        torch.set_num_threads(1)
        self.addCleanup(torch.set_num_threads, self.threads)
        # Two explicit synthetic cases, six repeated views. NOT public fixture data.
        states = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (1, 0, 0), (0, 0, 0),
                  (0, 0, 0), (0, 0, 0), (0, 0, 0), (0, 0, 0)]
        actions = [(1, 0, -1, 1), (1, 1, -1, 1), (0, 0, 1, -1),
                   (1, 0, -1, 0), (1, 1, -1, 0), (1, 2, -1, 0), (0, 0, 1, -1), (2, -1, -1, -1)]
        batch = SensorBatch(torch.tensor([[x] * 12 for x in states], dtype=torch.float64),
                            torch.tensor([[x] * 12 for x in actions]))
        conditions = ['uninformative', 'informative']
        self.batches = {c + '_' + f: batch for c in conditions for f in ('same_pair', 'second_pair')}
        with torch.random.fork_rng(devices=[]):
            models = [{'id': name, 'parameters': sum(p.numel() for p in factory().parameters())}
                      for name, factory in model_factories().items()]
        self.spec = {'models': models, 'seeds': [7], 'controls': ['no_change', 'prefix', 'local', 'contact'],
            'data': {'conditions': conditions, 'evaluation': ['same_pair', 'second_pair'], 'query_step': 6,
                     'views_per_dataset': 12, 'actions_per_history': 8, 'event_targets_per_update': 96,
                     'input_sha256': {key: value.digest() for key, value in self.batches.items()}},
            'fit': {'total_neural_fits': 24, 'regimes': [
                {'id': 'fixed_exposure', 'updates': 1, 'cpu_seconds': 30.},
                {'id': 'cpu_budget', 'updates': 1, 'cpu_seconds': 30.}]}}

    def test_complete_synthetic_pipeline_all_six_models_and_controls(self):
        from experiments.predictive_nucleus.comparison_execution import digest_file
        with redirect_stdout(io.StringIO()):
            report = r.execute(self.spec, self.batches, self.output, {'synthetic': True})
        self.assertEqual(report['neural_forecast_count'], 4608)
        self.assertEqual(len(report['results']), 64)
        self.assertEqual(len(report['latency']), 24)
        self.assertEqual(report['paired_records'], 2112)
        self.assertEqual((self.output / 'COMPLETE').read_text().strip(), digest_file(self.output / 'report.json'))
        self.assertFalse((self.output / 'FAILED.json').exists())

    def test_failed_replay_leaves_no_success_and_retains_fit_evidence(self):
        with patch.object(r, 'evaluate', side_effect=ValueError('synthetic replay fault')):
            with self.assertRaisesRegex(ValueError, 'replay fault'):
                r.execute(self.spec, self.batches, self.output, {'synthetic': True})
        self.assertTrue((self.output / 'fits' / 'FIT_PHASE.json').exists())
        self.assertFalse((self.output / 'COMPLETE').exists())
        self.assertFalse((self.output / 'report.json').exists())
        failure = json.loads((self.output / 'FAILED.json').read_text())
        self.assertEqual(failure['phase'], 'replay')
        self.assertEqual(failure['status'], 'INCOMPLETE')


if __name__ == '__main__':
    unittest.main()
