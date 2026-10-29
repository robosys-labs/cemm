"""Domain expansion integration invariants; synthetic traces, no learned scores."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import selectors
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import active_participant as api
from experiments.predictive_nucleus import active_paths, external_participant, masked_replay
from experiments.predictive_nucleus import comparison_scoring, joint_objective
from experiments.predictive_nucleus import export_participant
from experiments.predictive_nucleus.domain_contract import DomainMemory, domain_context
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.empirical_joint import SensorMemory, context as legacy_context
from experiments.predictive_nucleus.informative_curriculum import model_factories
from experiments.predictive_nucleus.tests.test_external_participant import synthetic_evidence


def ids(n):
    return tuple('abcdef'[:n])


def start(n, values=None):
    return {'op': 'start', 'episode': 'domain', 'ids': list(reversed(ids(n))),
            'observation': dict(zip(ids(n), (0,) * n if values is None else values, strict=True))}


def predict(step=0, kind='observe', participants=(), value=None, sensor_ids=None):
    action = {'kind': kind, 'participants': list(participants)}
    if kind == 'set': action['value'] = value
    request = {'op': 'predict', 'episode': 'domain', 'step': step, 'action': action}
    if sensor_ids is not None: request['sensor_ids'] = list(sensor_ids)
    return request


def feedback(receipt, values, step=0):
    return {'op': 'feedback', 'episode': 'domain', 'step': step, 'receipt': receipt,
            'observation': dict(zip(ids(len(values)), values, strict=True))}


def reading(values):
    return (torch.tensor([[v if v is not None else -1 for v in values]], dtype=torch.float64),
            torch.tensor([[v is not None for v in values]], dtype=torch.bool))


def add_row(memory, pre, action, past, post, key_function=domain_context):
    key, order = key_function(pre, action, past, memory.mode)
    memory.table[key] = Counter({tuple(post[i] for i in order): 1})


class CountingForecast(torch.nn.Module):
    """Explicitly capable synthetic predictor with observable invocation counts."""
    supported_entities = (3, 4, 5, 6)
    supports_self_contact = True

    def __init__(self, logs=None):
        super().__init__()
        self.register_buffer('marker', torch.tensor([0.], dtype=torch.float64))
        self.logs = logs
        self.predict_calls = self.receive_calls = 0

    def initial(self, n):
        return torch.zeros(n, 1, dtype=torch.float64)

    def predict(self, pre, action, state):
        self.predict_calls += 1
        values = [-len(pre[0]) * math.log(2)] * (2 ** pre.shape[1]) if self.logs is None else self.logs
        logs = torch.tensor([float('-inf') if x is None else x for x in values], dtype=torch.float64)
        return logs.expand(len(pre), -1).clone(), state.clone()

    def receive(self, pending, post):
        self.receive_calls += 1
        return pending + 1


class ActiveDomainTests(unittest.TestCase):
    def setUp(self):
        state = torch.random.get_rng_state(); threads = torch.get_num_threads()
        self.addCleanup(torch.random.set_rng_state, state)
        self.addCleanup(torch.set_num_threads, threads)
        torch.set_num_threads(1); torch.manual_seed(7)

    def session(self, n, **kwargs):
        session = api.Session(**kwargs)
        result = session.handle(start(n))
        self.assertEqual(result['implementation']['version'], 'active-inference-v4')
        self.assertEqual(result['evidence_contract']['version'], 'active-evidence-v2')
        self.assertEqual(tuple(result['ids']), ids(n))
        self.assertEqual(len(result['world_order']), 2 ** n)
        self.assertTrue(all(len(world) == n for world in result['world_order']))
        return session

    def test_all_domain_sizes_handle_high_index_actions_and_self_contact(self):
        for n in range(3, 7):
            with self.subTest(entities=n):
                model = DomainKernel(persistence=True); before = joint_objective.fingerprint(model.state_dict())
                s = self.session(n, model=model); last = ids(n)[-1]
                history = [(predict(0, 'contact', (last, 'a')), (0,) * n),
                           (predict(1, 'set', (last,), 1), (0,) * (n - 1) + (1,)),
                           (predict(2, 'contact', (last, last), sensor_ids=(last,)),
                            (None,) * (n - 1) + (0,))]
                for step, (request, values) in enumerate(history):
                    response = s.handle(request)
                    self.assertEqual(len(response['log']['values'][0]), 2 ** n)
                    self.assertEqual(s.evidence.time, step)
                    result = s.handle(feedback(response['receipt'], values, step))
                    self.assertEqual(result['next_step'], step + 1)
                    self.assertFalse(result['evidence']['impossible_observation'])
                self.assertEqual(result['evidence']['observed_bits'], 1)
                self.assertEqual(joint_objective.fingerprint(model.state_dict()), before)
                self.assertFalse(s.handle({'op': 'end', 'episode': 'domain'})['evaluated'])

    def test_no_change_control_supports_every_size_and_retains_mismatch(self):
        for n in range(3, 7):
            s = self.session(n, control='no_change'); last = ids(n)[-1]
            response = s.handle(predict(kind='contact', participants=(last, last)))
            result = s.handle(feedback(response['receipt'], (0,) * (n - 1) + (1,)))
            self.assertTrue(result['evidence']['impossible_observation'])
            self.assertEqual(s.filter.bits[0, -1], 1.)
            response = s.handle(predict(1))
            self.assertEqual(response['log']['values'][0][1], 0.)
            result = s.handle(feedback(response['receipt'], (None,) * n, 1))
            self.assertEqual(result['evidence']['status'], 'NO_EVIDENCE')
            self.assertTrue(result['evidence']['episode_alarm'])

    def test_unadapted_models_reject_wider_scope_and_self_contact_before_prediction(self):
        for name, factory in model_factories().items():
            model = factory()
            with self.subTest(model=name), patch.object(model, 'predict', wraps=model.predict) as called:
                with self.assertRaises(ValueError): api.Session(model=model).handle(start(4))
                s = self.session(3, model=model)
                with self.assertRaises(ValueError): s.handle(predict(kind='contact', participants=('a', 'a')))
                self.assertEqual(called.call_count, 0)

    def test_invalid_wire_scope_or_forecast_dimension_fails_without_evidence(self):
        for count in (2, 7):
            request = {'op': 'start', 'episode': 'domain', 'ids': [str(i) for i in range(count)],
                       'observation': {str(i): 0 for i in range(count)}}
            with self.assertRaises(ValueError): api.Session(control='no_change').handle(request)
        s = self.session(6, model=CountingForecast([-math.log(8)] * 8))
        with self.assertRaises(ValueError): s.handle(predict())
        self.assertEqual((s.evidence.time, s.evidence.support.time), (0, 0))
        self.assertEqual(s.phase, 'ERROR')
        s = self.session(6, model=DomainKernel())
        with self.assertRaises(ValueError): s.handle(predict(kind='contact', participants=('a', 'outside')))
        self.assertEqual(s.evidence.time, 0)

    def test_uniform_six_bit_joint_is_compatible_not_a_small_probability_surprise(self):
        for n in range(3, 7):
            s = self.session(n, model=CountingForecast())
            response = s.handle(predict())
            result = s.handle(feedback(response['receipt'], (1,) * n))['evidence']
            self.assertEqual(result['status'], 'OBSERVATION_COMPATIBLE')
            self.assertAlmostEqual(result['observed_log_likelihood'], -n * math.log(2))
            self.assertAlmostEqual(result['log_e_increment'], 0.)
            self.assertFalse(result['episode_alarm'])
            self.assertEqual(result['scored_steps'], 1)

    def test_six_entity_finite_underflow_and_exact_zero_remain_distinct(self):
        for rare, impossible in ((-1000., False), (None, True)):
            logs = [None] * 64; logs[0] = 0.; logs[-1] = rare
            s = self.session(6, model=CountingForecast(logs)); response = s.handle(predict())
            if impossible:
                with self.assertRaises(api.FeedbackFailure) as caught:
                    s.handle(feedback(response['receipt'], (1,) * 6))
                evidence = caught.exception.evidence
                self.assertEqual(evidence['observed_log_likelihood'], 'negative_infinity')
                self.assertFalse(evidence['committed'])
            else:
                evidence = s.handle(feedback(response['receipt'], (1,) * 6))['evidence']
                self.assertEqual(evidence['observed_log_likelihood'], -1000.)
                self.assertEqual(s.filter.bits.tolist(), [[1.] * 6])
            self.assertEqual(evidence['impossible_observation'], impossible)
            json.dumps(evidence, allow_nan=False)

    def test_alias_counts_one_physical_reading_and_never_borrows_distinct_context(self):
        s = self.session(6, control='no_change')
        response = s.handle(predict(kind='contact', participants=('f', 'f'), sensor_ids=('f',)))
        self.assertEqual(response['evidence']['context_support']['observed_events'], 0)
        result = s.handle(feedback(response['receipt'], (None,) * 5 + (0,)))
        evidence = result['evidence']
        self.assertEqual((evidence['observed_bits'], evidence['missing_bits']), (1, 0))
        self.assertAlmostEqual(evidence['reference_log_likelihood'], -math.log(2))
        response = s.handle(predict(1, 'contact', ('f', 'e'), sensor_ids=('f', 'e')))
        self.assertEqual(response['evidence']['context_support']['observed_events'], 0)
        s.handle(feedback(response['receipt'], (None,) * 4 + (0, 0), 1))
        response = s.handle(predict(2, 'contact', ('f', 'f'), sensor_ids=('f',)))
        self.assertEqual(response['evidence']['context_support']['observed_events'], 1)
        s.handle(feedback(response['receipt'], (None,) * 6, 2))
        response = s.handle(predict(3, 'contact', ('f', 'f')))
        self.assertEqual(response['evidence']['context_support']['status'], 'UNOBSERVED_INPUT')

    def test_tiny_alias_factor_support_remains_visible_and_receipt_bound(self):
        model = DomainKernel(persistence=True)
        with torch.no_grad():
            for parameter in model.parameters(): parameter.zero_()
            model.pair[-1].bias.copy_(torch.tensor([-1000., 0., 0., -2000.], dtype=torch.float64))
        s = self.session(6, model=model)
        response = s.handle(predict(kind='contact', participants=('f', 'f')))
        self.assertAlmostEqual(response['log']['values'][0][0], 0., places=12)
        conditioned = response['filter']['alias_conditioning']
        self.assertEqual(conditioned['interpretation'], 'supplied_per_mode_diagonal_normalization')
        self.assertFalse(conditioned['learned_transfer_established'])
        self.assertEqual(conditioned['path_owners'], [0])
        retained = conditioned['retained_log_mass_by_path_and_mode']
        self.assertEqual((len(retained), len(retained[0])), (1, 2))
        for value in retained[0]:
            self.assertTrue(math.isfinite(value))
            self.assertAlmostEqual(value, -1000. - math.log(2), places=10)
            self.assertEqual(math.exp(value), 0.)
        canonical = {k: v for k, v in response.items() if k not in ('wall_seconds', 'cpu_seconds', 'receipt')}
        self.assertEqual(response['receipt'], sha256(json.dumps(canonical, sort_keys=True, allow_nan=False).encode()).hexdigest())
        s.handle(feedback(response['receipt'], (0,) * 6))
        self.assertNotIn('alias_conditioning', s.handle(predict(1))['filter'])

    def test_expansion_budget_is_checked_before_model_or_candidate_allocation(self):
        model = CountingForecast()
        anchor = torch.zeros(1, 6, dtype=torch.float64)
        action = torch.tensor([[2, -1, -1, -1]], dtype=torch.long)
        limited = active_paths.NeuralPaths(model, anchor, expansion_limit=63)
        with self.assertRaisesRegex(ValueError, 'expansion'): limited.predict(action)
        self.assertEqual(model.predict_calls, 0)
        f = active_paths.NeuralPaths(model, anchor)
        f.predict(action); f.receive(*reading((None,) * 6))
        self.assertEqual(len(f.weight), 64)
        before = (f.bits.clone(), f.weight.clone(), f.state.clone())
        with self.assertRaisesRegex(ValueError, 'expansion'): f.predict(action)
        self.assertEqual(model.predict_calls, 1)
        for current, previous in zip((f.bits, f.weight, f.state), before):
            self.assertTrue(torch.equal(current, previous))

    def test_live_path_limit_still_rejects_real_growth_without_pruning(self):
        model = CountingForecast()
        f = active_paths.NeuralPaths(model, torch.zeros(1, 6, dtype=torch.float64), limit=63)
        f.predict(torch.tensor([[2, -1, -1, -1]], dtype=torch.long))
        with self.assertRaisesRegex(ValueError, 'live path'): f.receive(*reading((None,) * 6))
        self.assertEqual(model.receive_calls, 0)
        self.assertEqual((len(f.weight), f.bits.shape), (1, torch.Size([1, 6])))

    def test_six_entity_batch_retains_unequal_episode_path_counts(self):
        model = DomainKernel(persistence=True)
        f = active_paths.NeuralPaths(model, torch.zeros(2, 6, dtype=torch.float64), limit=4)
        actions = torch.tensor([[0, 0, 5, -1], [2, -1, -1, -1]], dtype=torch.long)
        f.predict(actions)
        f.receive(torch.full((2, 6), -1., dtype=torch.float64), torch.zeros(2, 6, dtype=torch.bool))
        self.assertEqual(torch.bincount(f.owner).tolist(), [4, 1])
        self.assertEqual(len(f.weight), 5)
        logs, answered = f.predict(torch.tensor([[2, -1, -1, -1]] * 2, dtype=torch.long))
        self.assertEqual(logs.shape, (2, 64))
        self.assertTrue(all(answered))
        self.assertTrue(torch.allclose(logs.logsumexp(-1), torch.zeros(2, dtype=torch.float64), atol=1e-12, rtol=0))

    def test_three_entity_six_arm_wire_forecasts_match_unchanged_legacy_inference(self):
        history = [(predict(0, 'contact', ('a', 'b')), (0, 1, 0)),
                   (predict(1, 'set', ('c',), 1), (0, 1, None)),
                   (predict(2), (0, 1, 1)), (predict(3, 'contact', ('c', 'a')), None)]
        for name, factory in model_factories().items():
            with self.subTest(model=name):
                legacy = factory(); before = joint_objective.fingerprint(legacy.state_dict())
                successor = DomainKernel.from_legacy(legacy) if isinstance(legacy, joint_objective.JointKernel) else deepcopy(legacy)
                adapted_before = joint_objective.fingerprint(successor.state_dict())
                s = api.Session(model=successor)
                reference = external_participant.Session(masked_replay, comparison_scoring, joint_objective, model=legacy)
                initial = start(3, (0, 1, 0)); s.handle(initial); reference.handle(initial)
                for step, (request, values) in enumerate(history):
                    left, right = s.handle(request), reference.handle(request)
                    for field in ('raw_log', 'log'):
                        lp = torch.tensor([float('-inf') if x is None else x for x in left[field]['values'][0]], dtype=torch.float64)
                        rp = torch.tensor([float('-inf') if x is None else x for x in right[field]['values'][0]], dtype=torch.float64)
                        self.assertTrue(torch.allclose(lp, rp, atol=1e-12, rtol=0), (name, step, field))
                    if values is not None:
                        s.handle(feedback(left['receipt'], values, step))
                        reference.handle(feedback(right['receipt'], values, step))
                self.assertEqual(joint_objective.fingerprint(legacy.state_dict()), before)
                self.assertEqual(joint_objective.fingerprint(successor.state_dict()), adapted_before)
                self.assertEqual((s.evidence.time, s.evidence.scored_steps), (3, 3))

    def test_startup_identity_binds_configuration_and_copies_mutable_metadata(self):
        remembered = DomainKernel(memory=True)
        reset = DomainKernel(memory=False); reset.load_state_dict(remembered.state_dict(), strict=True)
        self.assertEqual(joint_objective.fingerprint(remembered.state_dict()),
                         joint_objective.fingerprint(reset.state_dict()))
        first = api.Session(model=remembered).handle(start(3))
        second = api.Session(model=reset).handle(start(3))
        self.assertNotEqual(first['implementation_sha256'], second['implementation_sha256'])
        adapted = DomainKernel.from_legacy(joint_objective.JointKernel())
        metadata = deepcopy(adapted.domain_adaptation)
        s = api.Session(model=adapted); response = s.handle(start(6))
        response['implementation']['adaptation']['configuration']['memory'] = False
        response['implementation']['adaptation']['supported_entities'].append(99)
        response['evidence_contract']['alpha'] = 1.
        response['evidence_contract']['calibration'] = 'changed'
        self.assertEqual(adapted.domain_adaptation, metadata)
        self.assertEqual(s.evidence.contract['alpha'], .05)
        self.assertEqual(s.evidence.contract['calibration'], 'NOT_ESTABLISHED')

    def test_converted_empirical_controls_preserve_three_entity_predictions(self):
        anchor, observe, contact = (0, 1, 0), (2, -1, -1, -1), (0, 0, 1, -1)
        for mode, first in (('local', False), ('prefix', False), ('contact', False), ('contact', True)):
            legacy = SensorMemory(mode); past = ()
            for action in (contact, observe, observe):
                add_row(legacy, anchor, action, past, anchor, legacy_context)
                past += ((anchor, action, anchor),)
            before = legacy.digest(); successor = DomainMemory.from_legacy(legacy)
            name = 'first_contact' if first else mode
            s = api.Session(memory=successor, control=name)
            reference = external_participant.Session(masked_replay, comparison_scoring, joint_objective,
                                                     memory=legacy, control=name)
            s.handle(start(3, anchor)); reference.handle(start(3, anchor))
            for step, request in enumerate((predict(0, 'contact', ('a', 'b')), predict(1), predict(2))):
                left, right = s.handle(request), reference.handle(request)
                self.assertEqual((left['status'], left['log']), (right['status'], right['log']))
                s.handle(feedback(left['receipt'], anchor, step))
                reference.handle(feedback(right['receipt'], anchor, step))
            self.assertEqual(legacy.digest(), before)

    def test_larger_empirical_scope_abstains_then_recovers_only_to_recorded_context(self):
        legacy = SensorMemory('local')
        add_row(legacy, (0, 0, 0), (2, -1, -1, -1), (), (0, 0, 0), legacy_context)
        migrated = DomainMemory.from_legacy(legacy); original = migrated.digest()
        s = self.session(6, memory=migrated, control='local')
        response = s.handle(predict()); self.assertEqual(response['status'], 'ABSTAIN')
        s.handle(feedback(response['receipt'], (0,) * 6))
        self.assertEqual(s.handle(predict(1))['status'], 'ABSTAIN')
        self.assertEqual(migrated.digest(), original)
        observed = DomainMemory('local')
        add_row(observed, (0,) * 6, (2, -1, -1, -1), (), (0,) * 6)
        original = observed.digest(); s = self.session(6, memory=observed, control='local')
        response = s.handle(predict(0, 'set', ('f',), 0)); self.assertEqual(response['status'], 'ABSTAIN')
        result = s.handle(feedback(response['receipt'], (0,) * 6))
        self.assertEqual(result['inference']['recovery'], ['recovered_observed_context'])
        self.assertEqual(result['evidence']['status'], 'UNSUPPORTED_PREDICTION')
        response = s.handle(predict(1)); self.assertEqual(response['status'], 'PREDICTED')
        self.assertEqual(response['log']['values'][0][0], 0.)
        self.assertEqual(observed.digest(), original)

    def test_missing_historic_high_index_contact_stays_unknown_after_full_current_reading(self):
        for mode in ('prefix', 'contact'):
            s = self.session(6, memory=DomainMemory(mode), control=mode)
            response = s.handle(predict(0, 'contact', ('f', 'a')))
            s.handle(feedback(response['receipt'], (0,) * 5 + (None,)))
            response = s.handle(predict(1))
            result = s.handle(feedback(response['receipt'], (0,) * 6, 1))
            self.assertEqual(result['inference']['recovery'], ['missing_relevant_history'])
            self.assertEqual(s.handle(predict(2))['status'], 'ABSTAIN')

    def test_jsonl_six_entity_self_contact_flushes_forecast_before_feedback(self):
        s = api.Session(control='no_change'); output = io.StringIO(); flushed = []
        class Output:
            def write(inner, text): output.write(text)
            def flush(inner): flushed.append(output.getvalue())
        class Input:
            def readline(inner, size):
                i = len(flushed)
                if i == 0: frame = start(6)
                elif i == 1: frame = predict(kind='contact', participants=('f', 'f'), sensor_ids=('f',))
                elif i == 2:
                    receipt = json.loads(flushed[-1].splitlines()[-1])['receipt']
                    frame = feedback(receipt, (None,) * 5 + (0,))
                else: frame = {'op': 'end', 'episode': 'domain'}
                return json.dumps(frame) + '\n'
        self.assertEqual(api.serve(s, Input(), Output()), 0)
        self.assertEqual(len(flushed), 4)
        messages = [json.loads(row) for row in output.getvalue().splitlines()]
        self.assertEqual([m['status'] for m in messages], ['STARTED', 'PREDICTED', 'RECEIVED', 'ENDED'])
        self.assertEqual(messages[2]['evidence']['observed_bits'], 1)
        self.assertEqual(messages[3]['feedback_steps'], 1)

    def test_real_cli_expands_verified_synthetic_kernel_and_rejects_fixed_flat(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); evidence = root / 'evidence'; bundle = root / 'bundle'
            report_digest = synthetic_evidence(evidence)
            with patch.object(export_participant, 'REPORT_SHA256', report_digest):
                export_participant.export(evidence, bundle)
            command = [sys.executable, '-m', 'experiments.predictive_nucleus.active_participant',
                       '--bundle', str(bundle), '--manifest-sha256', export_participant.digest(bundle / 'manifest.json'),
                       '--expand-domain', '--seed', '7', '--participant']
            process = subprocess.Popen(command + ['kernel_supplied_persistence'],
                                       cwd=Path(__file__).resolve().parents[3], stdin=subprocess.PIPE,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            try:
                with selectors.DefaultSelector() as selector:
                    selector.register(process.stdout, selectors.EVENT_READ)
                    def exchange(request):
                        process.stdin.write(json.dumps(request) + '\n'); process.stdin.flush()
                        self.assertTrue(selector.select(timeout=20), 'CLI response timed out')
                        line = process.stdout.readline()
                        self.assertTrue(line, 'CLI exited before producing a JSON response')
                        return external_participant.strict_json(line)
                    self.assertEqual(exchange(start(6))['status'], 'STARTED')
                    forecast = exchange(predict(kind='contact', participants=('f', 'f')))
                    self.assertEqual(forecast['status'], 'PREDICTED')
                    self.assertEqual(len(forecast['log']['values'][0]), 64)
                    self.assertEqual(exchange(feedback(forecast['receipt'], (0,) * 6))['status'], 'RECEIVED')
                    ended = exchange({'op': 'end', 'episode': 'domain'})
                    self.assertEqual((ended['status'], ended['feedback_steps']), ('ENDED', 1))
                    self.assertFalse(ended['evaluated'])
                    self.assertEqual(process.wait(timeout=20), 0)
            finally:
                if process.poll() is None:
                    process.kill(); process.wait(timeout=5)
                for stream in (process.stdin, process.stdout, process.stderr): stream.close()
            rejected = subprocess.run(command + ['flat'], cwd=Path(__file__).resolve().parents[3],
                                      input='', capture_output=True, text=True, timeout=20)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('fixed three-entity domain', rejected.stderr)


if __name__ == '__main__':
    unittest.main()
