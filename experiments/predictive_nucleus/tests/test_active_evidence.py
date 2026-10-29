"""Active diagnostic invariants on synthetic traces; no fits or scientific scores."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import io
import json
import math
import unittest

import torch

from experiments.predictive_nucleus import active_participant as api
from experiments.predictive_nucleus import active_paths, comparison_scoring, external_participant, joint_objective
from experiments.predictive_nucleus.active_evidence import ActiveEvidence
from experiments.predictive_nucleus.empirical_joint import SensorMemory, context
from experiments.predictive_nucleus.informative_curriculum import model_factories


IDS = tuple('abc')
ANCHOR = {'a': 0, 'b': 1, 'c': 0}
OBSERVE = {'kind': 'observe', 'participants': []}
CONTACT = {'kind': 'contact', 'participants': ['a', 'b']}
UNIFORM = [-math.log(8)] * 8


def start():
    return {'op': 'start', 'episode': 'toy', 'ids': list(IDS), 'observation': dict(ANCHOR)}


def predict(step=0, action=OBSERVE, **extra):
    return {'op': 'predict', 'episode': 'toy', 'step': step, 'action': deepcopy(action), **extra}


def feedback(receipt, step=0, values=(0, 1, 0)):
    return {'op': 'feedback', 'episode': 'toy', 'step': step, 'receipt': receipt,
            'observation': dict(zip(IDS, values, strict=True))}


def begin(monitor, logs=UNIFORM, action=OBSERVE, sensor_ids=IDS):
    metadata = monitor.begin(deepcopy(action), deepcopy(logs), list(sensor_ids))
    receipt = sha256(str(monitor.time).encode()).hexdigest()
    monitor.bind(receipt)
    return receipt, metadata


def point(index):
    result = [None] * 8
    result[index] = 0.
    return result


def local_memory():
    memory = SensorMemory('local')
    key, order = context((0, 1, 0), (2, -1, -1, -1), (), memory.mode)
    memory.table[key] = Counter({tuple((0, 1, 0)[i] for i in order): 1})
    return memory


class FixedForecast(torch.nn.Module):
    """Hand-written distribution, deliberately unrelated to a simulator law."""
    def __init__(self, logs):
        super().__init__()
        self.register_buffer('logs', torch.tensor(
            [float('-inf') if x is None else x for x in logs], dtype=torch.float64))

    def initial(self, n):
        return torch.zeros(n, 1, dtype=torch.float64)

    def predict(self, pre, action, state):
        return self.logs.expand(len(pre), -1).clone(), state.clone()

    def receive(self, pending, post):
        return pending + 1


class LogEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.m = ActiveEvidence(IDS, ANCHOR)

    def test_finite_underflow_is_surprise_not_impossibility(self):
        logs = point(0); logs[1] = -1000.
        receipt, _ = begin(self.m, logs)
        result = self.m.receive({'a': 0, 'b': 0, 'c': 1}, receipt)
        self.assertEqual(math.exp(-1000), 0.)
        self.assertEqual(result['observed_log_likelihood'], -1000.)
        self.assertAlmostEqual(result['log_e_increment'], 1000 - math.log(8))
        self.assertFalse(result['impossible_observation'])
        self.assertTrue(result['episode_alarm'])
        json.dumps(result, allow_nan=False)

    def test_exact_zero_mass_is_explicit_and_strict_json(self):
        receipt, _ = begin(self.m, point(0))
        result = self.m.receive({'a': 0, 'b': 0, 'c': 1}, receipt)
        self.assertEqual(result['observed_log_likelihood'], 'negative_infinity')
        self.assertEqual(result['log_e_value'], 'positive_infinity')
        self.assertTrue(result['impossible_observation'])
        self.assertEqual(result['status'], 'MODEL_MISMATCH_EVIDENCE')
        json.dumps(result, allow_nan=False)

    def test_partial_observations_use_joint_marginal_not_independent_bits(self):
        logs = [None] * 8; logs[0] = logs[6] = -math.log(2)
        receipt, _ = begin(self.m, logs, sensor_ids=('b', 'a'))
        result = self.m.receive({'a': 1, 'b': 1, 'c': None}, receipt)
        self.assertAlmostEqual(result['observed_log_likelihood'], -math.log(2))
        self.assertAlmostEqual(result['reference_log_likelihood'], -math.log(4))
        self.assertEqual((result['observed_bits'], result['missing_bits']), (2, 0))
        other = ActiveEvidence(IDS, ANCHOR)
        receipt, _ = begin(other, logs)
        result = other.receive({'a': 1, 'b': 0, 'c': None}, receipt)
        self.assertTrue(result['impossible_observation'])  # both individual bits had positive marginals

    def test_alarm_is_latched_after_finite_statistic_falls_and_missing_feedback(self):
        logs = point(0); logs[0] = math.log1p(-math.exp(-6)); logs[1] = -6.
        receipt, _ = begin(self.m, logs)
        first = self.m.receive({'a': 0, 'b': 0, 'c': 1}, receipt)
        self.assertTrue(first['episode_alarm'])
        receipt, _ = begin(self.m, point(0))
        second = self.m.receive(dict.fromkeys(IDS, 0), receipt)
        self.assertLess(second['log_e_value'], math.log(20))
        self.assertTrue(second['episode_alarm'])
        receipt, _ = begin(self.m, point(0))
        third = self.m.receive(dict.fromkeys(IDS), receipt)
        self.assertEqual(third['status'], 'NO_EVIDENCE')
        self.assertEqual(third['log_e_increment'], 0.)
        self.assertEqual(third['log_e_value'], second['log_e_value'])
        self.assertEqual(third['scored_steps'], second['scored_steps'])
        self.assertEqual((self.m.time, third['scored_steps']), (3, 2))
        self.assertTrue(third['episode_alarm'])

    def test_unsupported_prediction_has_no_likelihood_or_e_increment(self):
        receipt, _ = begin(self.m, None)
        result = self.m.receive(ANCHOR, receipt)
        self.assertEqual(result['status'], 'UNSUPPORTED_PREDICTION')
        self.assertIsNone(result['observed_log_likelihood'])
        self.assertIsNone(result['log_e_increment'])
        self.assertEqual(result['log_e_value'], 0.)
        self.assertEqual(result['scored_steps'], 0)
        self.assertFalse(result['impossible_observation'])

    def test_preview_is_pure_and_mutating_it_does_not_change_commit(self):
        receipt, _ = begin(self.m)
        preview = self.m.preview(ANCHOR, receipt)
        self.assertEqual((self.m.time, self.m.support.time, self.m.log_e_value), (0, 0, 0.))
        preview['log_e_value'] = 12345
        result = self.m.receive(ANCHOR, receipt)
        self.assertEqual(result['log_e_value'], 0.)
        self.assertTrue(result['committed'])
        self.assertEqual((self.m.time, self.m.support.time), (1, 1))

    def test_invalid_forecast_rejected_before_context_commit(self):
        invalid = ([None] * 8, [0.] * 8, [float('nan')] * 8,
                   [float('inf')] * 8, UNIFORM[:-1], [True] + UNIFORM[1:])
        for logs in invalid:
            m = ActiveEvidence(IDS, ANCHOR)
            with self.subTest(logs=logs), self.assertRaises((ValueError, TypeError)):
                begin(m, logs)
            self.assertEqual(m.support.time, 0)
            self.assertIsNone(m.support.pending)

    def test_support_requires_actual_before_and_after_operand_readings(self):
        receipt, meta = begin(self.m, None, CONTACT)
        self.assertEqual(meta['context_support']['status'], 'UNTESTED_CONTEXT')
        self.m.receive({'a': 0, 'b': None, 'c': 0}, receipt)
        receipt, meta = begin(self.m, None, CONTACT)
        self.assertEqual(meta['context_support']['status'], 'UNOBSERVED_INPUT')
        self.m.receive(ANCHOR, receipt)  # full current state cannot invent the missing prior input
        receipt, meta = begin(self.m, None, CONTACT)
        self.assertEqual(meta['context_support']['observed_events'], 0)
        self.m.receive({'a': 0, 'b': 1, 'c': None}, receipt)
        receipt, meta = begin(self.m, None, CONTACT)
        self.assertEqual(meta['context_support']['observed_events'], 1)
        self.m.receive(ANCHOR, receipt)
        reverse = {'kind': 'contact', 'participants': ['b', 'a']}
        _, meta = begin(self.m, None, reverse)
        self.assertEqual(meta['context_support']['observed_events'], 0)

    def test_noncontact_context_is_not_mislabeled_as_model_failure(self):
        _, meta = begin(self.m)
        self.assertEqual(meta['context_support']['status'], 'NOT_APPLICABLE')


class ActiveEvidenceSessionTests(unittest.TestCase):
    def setUp(self):
        self.rng = torch.random.get_rng_state()
        self.addCleanup(torch.random.set_rng_state, self.rng)
        self.threads = torch.get_num_threads()
        torch.set_num_threads(1)
        self.addCleanup(torch.set_num_threads, self.threads)
        torch.manual_seed(7)

    def session(self, **kwargs):
        session = api.Session(**kwargs)
        started = session.handle(start())
        self.assertEqual(started['implementation']['version'], 'active-inference-v3')
        self.assertIn('evidence_contract', started)
        return session

    def test_receipt_covers_action_evidence_and_canonical_sensor_coverage(self):
        s = self.session(); response = s.handle(predict(sensor_ids=['c', 'a']))
        canonical = {k: v for k, v in response.items() if k not in ('wall_seconds', 'cpu_seconds', 'receipt')}
        digest = sha256(json.dumps(canonical, sort_keys=True, allow_nan=False).encode()).hexdigest()
        self.assertEqual(response['receipt'], digest)
        self.assertEqual(response['action'], OBSERVE)
        same = self.session().handle(predict(sensor_ids=['a', 'c']))
        different_coverage = self.session().handle(predict(sensor_ids=['a']))
        different_action = self.session().handle(predict(action=CONTACT, sensor_ids=['a', 'c']))
        self.assertEqual(same['receipt'], response['receipt'])
        self.assertNotEqual(different_coverage['receipt'], response['receipt'])
        self.assertNotEqual(different_action['receipt'], response['receipt'])

    def test_invalid_coverage_does_not_advance_filter_or_evidence(self):
        for coverage in ([], ['a', 'a'], ['unknown'], 'abc', [True], None):
            s = self.session(); before = s.filter.bits.clone()
            with self.subTest(coverage=coverage), self.assertRaises(ValueError):
                s.handle(predict(sensor_ids=coverage))
            self.assertEqual(s.phase, 'ERROR')
            self.assertEqual((s.evidence.time, s.evidence.support.time), (0, 0))
            self.assertTrue(torch.equal(s.filter.bits, before))

    def test_bad_envelopes_and_outside_coverage_never_enter_evidence(self):
        mutations = [lambda r: r.update(receipt='altered'), lambda r: r.update(step=True),
                     lambda r: r.update(step=1), lambda r: r.update(episode='other'),
                     lambda r: r.update(truth=[0, 1, 0]),
                     lambda r: r['observation'].update(a=True),
                     lambda r: r['observation'].update(b=1),
                     lambda r: r['observation'].pop('c')]
        for mutate in mutations:
            s = self.session(); response = s.handle(predict(sensor_ids=['a']))
            request = feedback(response['receipt'], values=(0, None, None)); mutate(request)
            before = s.filter.bits.clone()
            with self.assertRaises(ValueError): s.handle(request)
            self.assertEqual(s.phase, 'ERROR')
            self.assertEqual((s.evidence.time, s.evidence.support.time, s.evidence.log_e_value), (0, 0, 0.))
            self.assertTrue(torch.equal(s.filter.bits, before))

    def test_duplicate_feedback_cannot_inflate_support_or_statistics(self):
        s = self.session(); response = s.handle(predict(action=CONTACT))
        request = feedback(response['receipt']); s.handle(request)
        before = (s.evidence.time, s.evidence.log_e_value, s.evidence.support.assess(CONTACT))
        with self.assertRaises(ValueError): s.handle(request)
        self.assertEqual(before, (s.evidence.time, s.evidence.log_e_value, s.evidence.support.assess(CONTACT)))

    def test_returned_forecast_and_request_mutation_cannot_rewrite_committed_evidence(self):
        s = self.session(); request = predict(action=CONTACT)
        response = s.handle(request)
        response['log']['values'][0] = point(0)
        response['action']['participants'].reverse()
        request['action']['participants'][:] = ['b', 'c']
        response['evidence']['context_support']['observed_events'] = 999
        result = s.handle(feedback(response['receipt']))
        self.assertEqual(result['evidence']['observed_log_likelihood'], 0.)
        self.assertEqual(s.evidence.support.assess(CONTACT)['observed_events'], 1)
        self.assertEqual(s.evidence.support.assess({'kind': 'contact', 'participants': ['b', 'a']})['observed_events'], 0)

    def test_tiny_finite_neural_path_is_accepted_by_filter_and_monitor(self):
        logs = point(0); logs[1] = -1000.
        s = self.session(model=FixedForecast(logs)); response = s.handle(predict())
        result = s.handle(feedback(response['receipt'], values=(0, 0, 1)))
        self.assertEqual(result['evidence']['observed_log_likelihood'], -1000.)
        self.assertFalse(result['evidence']['impossible_observation'])
        self.assertEqual(s.filter.bits.tolist(), [[0., 0., 1.]])
        self.assertEqual(s.phase, 'READY')

    def test_no_change_control_continues_after_impossible_prediction_and_latches_alarm(self):
        s = self.session(control='no_change'); response = s.handle(predict())
        result = s.handle(feedback(response['receipt'], values=(1, 1, 0)))
        self.assertTrue(result['evidence']['impossible_observation'])
        self.assertTrue(result['evidence']['episode_alarm'])
        self.assertEqual(s.filter.bits.tolist(), [[1., 1., 0.]])
        response = s.handle(predict(1))
        result = s.handle(feedback(response['receipt'], 1, (None, None, None)))
        self.assertEqual(result['evidence']['status'], 'NO_EVIDENCE')
        self.assertTrue(result['evidence']['episode_alarm'])
        self.assertEqual((s.evidence.time, result['evidence']['scored_steps']), (2, 1))
        self.assertEqual(s.phase, 'READY')

    def test_supported_neural_and_empirical_conflicts_keep_terminal_evidence(self):
        for kwargs in ({'model': joint_objective.JointKernel(persistence=True)},
                       {'memory': local_memory(), 'control': 'local'}):
            s = self.session(**kwargs); response = s.handle(predict())
            with self.assertRaises(api.FeedbackFailure) as caught:
                s.handle(feedback(response['receipt'], values=(1, 1, 0)))
            evidence = caught.exception.evidence
            self.assertTrue(evidence['impossible_observation'])
            self.assertFalse(evidence['committed'])
            self.assertEqual(evidence['status'], 'MODEL_MISMATCH_EVIDENCE')
            self.assertEqual((s.step, s.evidence.time, s.evidence.support.time), (0, 0, 0))
            self.assertEqual(s.evidence.log_e_value, 0.)
            self.assertEqual(s.phase, 'ERROR')
            json.dumps(evidence, allow_nan=False)

    def test_resource_failure_does_not_become_model_mismatch_or_completed_feedback(self):
        s = self.session(model=FixedForecast(UNIFORM))
        for step in range(2):
            response = s.handle(predict(step))
            s.handle(feedback(response['receipt'], step, (None, None, None)))
        response = s.handle(predict(2))
        with self.assertRaisesRegex(api.FeedbackFailure, 'path bound') as caught:
            s.handle(feedback(response['receipt'], 2, (None, None, None)))
        evidence = caught.exception.evidence
        self.assertEqual(evidence['status'], 'NO_EVIDENCE')
        self.assertFalse(evidence['impossible_observation'])
        self.assertFalse(evidence['episode_alarm'])
        self.assertFalse(evidence['committed'])
        self.assertEqual((s.step, s.evidence.time, s.evidence.support.time), (2, 2, 2))
        self.assertEqual(len(s.filter.weight), 64)

    def test_unsupported_empirical_prediction_recovers_without_fake_likelihood(self):
        memory = local_memory(); before = memory.digest()
        s = self.session(memory=memory, control='local')
        response = s.handle(predict(action={'kind': 'set', 'participants': ['c'], 'value': 0}))
        self.assertEqual(response['status'], 'ABSTAIN')
        result = s.handle(feedback(response['receipt']))
        self.assertEqual(result['evidence']['status'], 'UNSUPPORTED_PREDICTION')
        self.assertIsNone(result['evidence']['observed_log_likelihood'])
        self.assertEqual(result['evidence']['log_e_value'], 0.)
        self.assertEqual(result['inference']['recovery'], ['recovered_observed_context'])
        response = s.handle(predict(1))
        self.assertEqual(response['status'], 'PREDICTED')
        self.assertEqual(s.handle(feedback(response['receipt'], 1))['evidence']['observed_log_likelihood'], 0.)
        self.assertEqual(memory.digest(), before)

    def test_all_six_model_forecasts_and_weights_match_unmonitored_repaired_path(self):
        history = [(CONTACT, (0, 1, 0)), ({'kind': 'set', 'participants': ['c'], 'value': 1}, (0, 1, None)),
                   (OBSERVE, (0, 1, 1)), ({'kind': 'contact', 'participants': ['c', 'a']}, None)]
        for name, factory in model_factories().items():
            with self.subTest(model=name):
                model = factory(); before = joint_objective.fingerprint(model.state_dict())
                s = self.session(model=model)
                reference = external_participant.Session(active_paths, comparison_scoring, joint_objective,
                                                         model=deepcopy(model))
                reference.handle(start())
                for step, (action, values) in enumerate(history):
                    left, right = s.handle(predict(step, action)), reference.handle(predict(step, action))
                    for field in ('status', 'raw_log', 'log', 'subtracted_log_mass'):
                        self.assertEqual(left[field], right[field], (name, step, field))
                    if values is not None:
                        s.handle(feedback(left['receipt'], step, values))
                        reference.handle(feedback(right['receipt'], step, values))
                        self.assertEqual((s.evidence.time, s.evidence.scored_steps), (step + 1, step + 1))
                self.assertEqual(joint_objective.fingerprint(model.state_dict()), before)
                self.assertEqual((s.step, s.evidence.time, s.evidence.support.time), (3, 3, 3))
                self.assertFalse(s.handle({'op': 'end', 'episode': 'toy'})['evaluated'])

    def test_serve_flushes_forecast_before_feedback_and_retains_terminal_diagnostic(self):
        s = api.Session(model=joint_objective.JointKernel(persistence=True))
        output = io.StringIO(); flushed = []; consumed = []
        class Output:
            def write(inner, text): output.write(text)
            def flush(inner): flushed.append(output.getvalue())
        class Input:
            def readline(inner, size):
                i = len(consumed)
                self.assertEqual(len(flushed), i)
                frames = [start(), predict()]
                frame = frames[i] if i < 2 else feedback(
                    json.loads(flushed[-1].splitlines()[-1])['receipt'], values=(1, 1, 0))
                consumed.append(frame)
                return json.dumps(frame) + '\n'
        self.assertEqual(api.serve(s, Input(), Output()), 2)
        self.assertEqual(len(consumed), 3)
        result = json.loads(output.getvalue().splitlines()[-1])
        self.assertEqual((result['status'], result['error_type']), ('ERROR', 'ValueError'))
        self.assertTrue(result['evidence']['impossible_observation'])
        self.assertFalse(result['evidence']['committed'])

    def test_end_with_unobserved_final_query_does_not_manufacture_evidence(self):
        s = self.session(); s.handle(predict())
        result = s.handle({'op': 'end', 'episode': 'toy'})
        self.assertTrue(result['pending_forecast'])
        self.assertEqual(s.evidence.time, 0)
        self.assertEqual(s.evidence.log_e_value, 0.)
        self.assertFalse(result['evaluated'])


if __name__ == '__main__':
    unittest.main()
