"""Delivered-data boundary and actual native CLI; synthetic wiring only."""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import active_learning as learning
from experiments.predictive_nucleus.active_checkpoint import save_checkpoint, load_checkpoint
from experiments.predictive_nucleus.domain_flat import DomainFlatGRU
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import fingerprint


def batch(n=3, name='contract'):
    values = torch.zeros(2, 1, n, dtype=torch.float64)
    values[1, 0, -1] = 1.
    actions = torch.tensor([[[0, n - 1, n - 1, -1]]], dtype=torch.long)
    return learning.ObservedBatch(values, actions, torch.ones_like(values, dtype=torch.bool),
                                  torch.ones(1, 1, n, dtype=torch.bool), (name,))


class ActiveLearningContractTests(unittest.TestCase):
    def setUp(self):
        state = torch.random.get_rng_state()
        self.addCleanup(torch.random.set_rng_state, state)
        torch.manual_seed(71)

    def test_hidden_values_and_coverage_are_never_silently_coerced(self):
        good = batch(); good.validate()
        mutations = []
        mask = good.masks.clone(); mask[1, 0, -1] = False
        mutations.append(replace(good, masks=mask))  # hidden value still contains a bit
        cover = good.coverage.clone(); cover[0, 0, -1] = False
        mutations.extend((replace(good, coverage=cover), replace(good, coverage=cover.float()),
                          replace(good, coverage=torch.zeros_like(cover))))
        partial = good.observations.clone(); partial[0, 0, 0] = -1.
        mutations.extend((replace(good, observations=partial), replace(good, observations=good.observations.float()),
                          replace(good, actions=good.actions.float()), replace(good, episode_ids=['contract']),
                          replace(good, episode_ids=('',))))
        for invalid in mutations:
            with self.subTest(invalid=invalid), self.assertRaises(ValueError): invalid.validate()
        x = good.observations.clone(); x[1, 0, -1] = -1.
        replace(good, observations=x, masks=mask, coverage=cover).validate()

    def test_history_digest_binds_coverage_missingness_ids_and_is_copied(self):
        good = batch(); x = good.observations.clone(); x[1, 0, 0] = -1.
        mask = good.masks.clone(); mask[1, 0, 0] = False
        partial = replace(good, observations=x, masks=mask)
        cover = partial.coverage.clone(); cover[0, 0, 0] = False
        self.assertNotEqual(partial.digest(), replace(partial, coverage=cover).digest())
        self.assertNotEqual(partial.digest(), replace(partial, episode_ids=('renamed',)).digest())
        self.assertNotEqual(good.digest(), partial.digest())
        copied = good.snapshot(); before = copied.digest()
        good.observations[1, 0, 0] = 1.
        self.assertEqual(copied.digest(), before)
        self.assertNotEqual(good.digest(), before)

    def test_duplicate_episode_ids_fail_before_any_training_or_counting(self):
        data = (batch(3), batch(4))
        model = DomainKernel(); before = fingerprint(model.state_dict())
        with self.assertRaisesRegex(ValueError, 'duplicate episode'):
            learning.fit(model, data, updates=1, cpu_seconds=30)
        with self.assertRaisesRegex(ValueError, 'duplicate episode'):
            learning.fit_empirical(data, mode='local')
        with self.assertRaisesRegex(ValueError, 'duplicate episode'):
            learning.evaluate(data, control='no_change')
        self.assertEqual(fingerprint(model.state_dict()), before)

    def test_all_missing_history_cannot_claim_a_training_update(self):
        data = batch(); x = data.observations.clone(); x[1] = -1.
        mask = data.masks.clone(); mask[1] = False
        data = replace(data, observations=x, masks=mask)
        model = DomainKernel(); before = fingerprint(model.state_dict())
        with self.assertRaisesRegex(ValueError, 'no observed events'):
            learning.fit(model, [data], updates=1, cpu_seconds=30)
        self.assertEqual(fingerprint(model.state_dict()), before)
        result = learning.evaluate([data], control='no_change')
        self.assertEqual(result['scored_events'], 0)
        self.assertIsNone(result['observed_nll'])

    def test_empirical_skips_partition_events_and_abstention_has_no_distribution(self):
        data = batch(); x = data.observations.clone(); x[1, 0, 0] = -1.
        mask = data.masks.clone(); mask[1, 0, 0] = False
        memory, report = learning.fit_empirical([replace(data, observations=x, masks=mask)], mode='local')
        self.assertEqual(report['counted_events'] + report['skipped_incomplete_current'] +
                         report['skipped_incomplete_history'], report['action_events'])
        self.assertEqual(report['counted_events'], 0)
        result = learning.evaluate([data], memory=memory)
        self.assertEqual(result['answered_forecasts'], 0)
        self.assertIsNone(result['records'][0]['log_probabilities']['values'][0][0])
        self.assertIsNone(result['records'][0]['observed_log_likelihood'][0][0])
        json.dumps(result, allow_nan=False)

    def test_conflicting_predictor_and_invalid_limits_fail_even_for_no_change(self):
        data = batch()
        with self.assertRaisesRegex(ValueError, 'control'):
            learning.replay(data, model=DomainKernel(), control='no_change')
        for arguments in ({'limit': 0}, {'expansion_limit': True}, {'differentiable': True}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                learning.replay(data, control='no_change', **arguments)

    def test_user_interrupt_after_mutation_invalidates_current_checkpoint_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'initial.json'
            saved = save_checkpoint(path, model=DomainKernel(persistence=True), provenance={
                'objective': 'untrained_or_inherited', 'training_input_sha256': None, 'completed_updates': 0})
            model = load_checkpoint(path, saved['sha256'])['model']
            before = fingerprint(model.state_dict()); original = torch.optim.Adam.step
            def interrupt(optimizer, *args, **kwargs):
                original(optimizer, *args, **kwargs)
                raise KeyboardInterrupt()
            with patch.object(torch.optim.Adam, 'step', interrupt), self.assertRaises(KeyboardInterrupt):
                learning.fit(model, [batch()], updates=2, cpu_seconds=30)
            self.assertNotEqual(fingerprint(model.state_dict()), before)
            self.assertFalse(hasattr(model, 'checkpoint_metadata'))
            self.assertEqual(model.training_provenance['status'], 'INTERRUPTED')
            self.assertEqual(model.training_provenance['final_weights_sha256'], fingerprint(model.state_dict()))
            self.assertEqual(model.domain_adaptation['training_provenance'], model.training_provenance)

    def test_reporting_interrupt_after_update_invalidates_current_checkpoint_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'initial.json'
            saved = save_checkpoint(path, model=DomainKernel(hidden=4, persistence=True), provenance={
                'objective': 'untrained_or_inherited', 'training_input_sha256': None, 'completed_updates': 0})
            model = load_checkpoint(path, saved['sha256'])['model']
            before = fingerprint(model.state_dict())
            interrupted = KeyboardInterrupt('interrupted while collecting final report')
            with patch.object(learning.resource, 'getrusage', side_effect=interrupted), \
                    self.assertRaises(KeyboardInterrupt) as failure:
                learning.fit(model, [batch()], updates=1, cpu_seconds=30)
            self.assertIs(failure.exception, interrupted)
            after = fingerprint(model.state_dict())
            self.assertNotEqual(after, before)
            self.assertFalse(hasattr(model, 'checkpoint_metadata'))
            self.assertEqual(model.training_provenance['status'], 'INTERRUPTED')
            self.assertEqual(model.training_provenance['final_weights_sha256'], after)
            self.assertEqual(model.domain_adaptation['training_provenance'], model.training_provenance)
            self.assertEqual(model.domain_adaptation['active_learned_parameters_sha256'], after)

    def test_persistent_postupdate_fingerprint_failure_preserves_original_error_and_unknown_hash(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'initial.json'
            saved = save_checkpoint(path, model=DomainKernel(hidden=4, persistence=True), provenance={
                'objective': 'untrained_or_inherited', 'training_input_sha256': None, 'completed_updates': 0})
            model = load_checkpoint(path, saved['sha256'])['model']
            before, names, failures = fingerprint(model.state_dict()), set(model.state_dict()), []
            def unavailable_after_update(tensors):
                actual = fingerprint(tensors)
                if set(tensors) == names and actual != before:
                    error = RuntimeError(f'postupdate fingerprint unavailable, attempt {len(failures) + 1}')
                    failures.append(error)
                    raise error
                return actual
            with patch.object(learning, 'fingerprint', side_effect=unavailable_after_update), \
                    self.assertRaises(RuntimeError) as failure:
                learning.fit(model, [batch()], updates=1, cpu_seconds=30)
            self.assertTrue(failures)
            self.assertIs(failure.exception, failures[0])
            self.assertNotEqual(fingerprint(model.state_dict()), before)
            self.assertFalse(hasattr(model, 'checkpoint_metadata'))
            self.assertEqual(model.training_provenance['status'], 'INTERRUPTED')
            self.assertIsNone(model.training_provenance['final_weights_sha256'])
            self.assertEqual(model.domain_adaptation['training_provenance'], model.training_provenance)
            self.assertIsNone(model.domain_adaptation['active_learned_parameters_sha256'])

    def test_actual_native_cli_loads_trained_flat_and_no_change_into_fresh_episodes(self):
        data = batch(6, 'native-cli'); model = DomainFlatGRU(hidden=3, persistence=True)
        trained = learning.fit(model, [data], updates=1, cpu_seconds=30)
        names = list('abcdef')
        for predictor in ('flat', 'no_change'):
            with self.subTest(predictor=predictor), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'checkpoint.json'
                arguments = {'model': model, 'provenance': trained} if predictor == 'flat' else {
                    'control': 'no_change', 'provenance': {'objective': 'no_change',
                    'training_input_sha256': None, 'completed_updates': 0}}
                saved = save_checkpoint(path, **arguments)
                process = subprocess.Popen([sys.executable, '-m', 'experiments.predictive_nucleus.active_participant',
                    '--checkpoint', str(path), '--checkpoint-sha256', saved['sha256']],
                    cwd=Path(__file__).resolve().parents[3], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                    env={**os.environ, 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'PYTHONHASHSEED': '0'})
                def exchange(request):
                    process.stdin.write(json.dumps(request) + '\n'); process.stdin.flush()
                    return json.loads(process.stdout.readline())
                try:
                    opened = exchange({'op': 'start', 'episode': 'native', 'ids': names,
                                       'observation': dict.fromkeys(names, 0)})
                    self.assertEqual(opened['implementation']['version'], 'active-inference-v5')
                    self.assertEqual(opened['implementation']['checkpoint']['state_sha256'], saved['state_sha256'])
                    prediction = exchange({'op': 'predict', 'episode': 'native', 'step': 0,
                        'action': {'kind': 'contact', 'participants': ['f', 'f']}, 'sensor_ids': ['f']})
                    self.assertEqual(len(prediction['log']['values'][0]), 64)
                    received = exchange({'op': 'feedback', 'episode': 'native', 'step': 0,
                        'receipt': prediction['receipt'], 'observation': {**dict.fromkeys(names, None), 'f': 1}})
                    self.assertEqual(received['status'], 'RECEIVED')
                    self.assertEqual(exchange({'op': 'end', 'episode': 'native'})['feedback_steps'], 1)
                    stdout, stderr = process.communicate(timeout=20)
                    self.assertEqual(process.returncode, 0, stderr)
                    self.assertEqual(stdout, '')
                finally:
                    if process.poll() is None: process.kill(); process.communicate()


if __name__ == '__main__': unittest.main()
