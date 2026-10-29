"""Synthetic collector wiring; no scientific fits, oracle, or held-out runs."""
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import acceptance_runner as runner
from experiments.predictive_nucleus import active_learning as learning
from experiments.predictive_nucleus.active_checkpoint import load_checkpoint, save_checkpoint
from experiments.predictive_nucleus.active_participant import Session
from experiments.predictive_nucleus.domain_contract import DomainMemory, domain_context
from experiments.predictive_nucleus.domain_flat import DomainFlatGRU
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import fingerprint


def episode(n=3, name='case', masked=True):
    ids = [f'unit-{i}' for i in reversed(range(n))]
    first, last = min(ids), max(ids)
    anchor = dict.fromkeys(ids, 0)
    after_contact = {**anchor, last: None if masked else 1}
    after_set = {**anchor, first: 1, last: 1}
    return {'episode': name, 'ids': ids, 'observations': [anchor, after_contact, after_set, deepcopy(after_set)],
            'actions': [{'kind': 'contact', 'participants': [last, last]},
                        {'kind': 'set', 'participants': [first], 'value': 1},
                        {'kind': 'observe', 'participants': []}], 'coverage': [ids.copy() for _ in range(3)]}


def inputs(*cases):
    return {'version': 'active-acceptance-input-v1', 'episodes': list(cases)}


def tensor_batch(case):
    ids = sorted(case['ids'])
    x = torch.tensor([[[row[i] if row[i] is not None else -1 for i in ids]]
                      for row in case['observations']], dtype=torch.float64)
    actions = []
    for action in case['actions']:
        members = action['participants']
        actions.append([['contact', 'set', 'observe'].index(action['kind']),
                        ids.index(members[0]) if members else -1,
                        ids.index(members[1]) if len(members) == 2 else -1, action.get('value', -1)])
    coverage = torch.tensor([[[i in row for i in ids]] for row in case['coverage']], dtype=torch.bool)
    return learning.ObservedBatch(x, torch.tensor(actions, dtype=torch.long)[:, None], x != -1,
                                  coverage, (case['episode'],)).validate()


class AcceptanceRunnerTests(unittest.TestCase):
    def setUp(self):
        state = torch.random.get_rng_state()
        self.addCleanup(torch.random.set_rng_state, state)
        torch.manual_seed(83)
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root, self.counter = Path(self.folder.name), 0

    def checkpoint(self, **predictor):
        self.counter += 1
        path = self.root / f'checkpoint-{self.counter}.json'
        provenance = {'objective': 'no_change' if predictor.get('control') == 'no_change' else 'untrained_or_inherited',
                      'training_input_sha256': None, 'completed_updates': 0}
        saved = save_checkpoint(path, provenance=provenance, **predictor)
        return path, saved['sha256']

    def collect(self, data, saved):
        path, digest = saved
        return runner.collect(data, checkpoint=path, expected_sha256=digest, participant='declared-arm', model_seed=7)

    def test_all_neural_arms_and_domains_equal_the_common_observed_replay(self):
        data = inputs(*(episode(n, f'case-{n}') for n in range(3, 7)))
        original = contract.digest(data)
        factories = (lambda: DomainKernel(hidden=4), lambda: DomainKernel(hidden=4, persistence=True),
                     lambda: DomainKernel(hidden=4, role_tying=False), lambda: DomainKernel(hidden=4, memory=False),
                     lambda: DomainFlatGRU(hidden=4), lambda: DomainFlatGRU(hidden=4, persistence=True))
        for factory in factories:
            model = factory(); checkpoint = self.checkpoint(model=model)
            initial, rng = fingerprint(model.state_dict()), torch.random.get_rng_state()
            trace = self.collect(data, checkpoint)
            self.assertEqual(trace['input_sha256'], original)
            self.assertEqual(trace['frozen_predictor_before'], trace['frozen_predictor_after'])
            self.assertEqual(trace['frozen_predictor_before']['state_sha256'], initial)
            self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))
            restored = load_checkpoint(*checkpoint)['model']
            for case, record in zip(data['episodes'], trace['episodes'], strict=True):
                with self.subTest(model=type(model).__name__, case=case['episode']):
                    self.assertIsNone(record['failure'])
                    self.assertEqual(record['started']['ids'], sorted(case['ids']))
                    self.assertIs(type(record['started']['world_order']), list)
                    self.assertEqual(record['ended']['feedback_steps'], len(case['actions']))
                    replay = learning.replay(tensor_batch(case), model=restored)
                    for t, event in enumerate(record['events']):
                        values = event['forecast']['log']['values'][0]
                        logs = torch.tensor([-torch.inf if v is None else v for v in values], dtype=torch.float64)
                        torch.testing.assert_close(logs, replay['log_probabilities'][t, 0], atol=1e-12, rtol=0)
                        self.assertEqual(event['forecast']['receipt'], contract.receipt(event['forecast']))
            json.dumps(trace, allow_nan=False)
        self.assertEqual(original, contract.digest(data))

    def test_forecast_is_copied_before_feedback_reuses_the_response_object(self):
        class ReusedReply(Session):
            def _handle(self, request):
                response = super()._handle(request)
                if request['op'] == 'predict': self.previous_response = response
                if request['op'] == 'feedback':
                    self.previous_response['log']['values'][0][0] = 999.
                    self.previous_response['action']['participants'].append('changed-after-forecast')
                return response
        saved = self.checkpoint(control='no_change')
        data = inputs(episode())
        with patch.object(runner, 'Session', ReusedReply):
            trace = self.collect(data, saved)
        self.assertIsNone(trace['episodes'][0]['failure'])
        for event, action in zip(trace['episodes'][0]['events'], data['episodes'][0]['actions'], strict=True):
            forecast = event['forecast']
            self.assertEqual(forecast['action'], action)
            self.assertNotIn(999., forecast['log']['values'][0])
            self.assertEqual(forecast['receipt'], contract.receipt(forecast))

    def test_feedback_contradiction_retains_prefix_and_offending_forecast_then_continues_other_episode(self):
        bad = episode(name='contradiction', masked=False)
        anchor = deepcopy(bad['observations'][0])
        changed = {**anchor, min(bad['ids']): 1}
        bad['actions'] = [{'kind': 'observe', 'participants': []} for _ in range(3)]
        bad['observations'] = [anchor, deepcopy(anchor), changed, deepcopy(changed)]
        trace = self.collect(inputs(bad, episode(4, 'unrelated')),
                             self.checkpoint(model=DomainKernel(persistence=True)))
        failed, good = trace['episodes']
        self.assertEqual((failed['failure']['phase'], failed['failure']['step']), ('feedback', 1))
        self.assertEqual(len(failed['events']), 2)
        self.assertEqual(failed['events'][0]['feedback']['status'], 'RECEIVED')
        self.assertIsNone(failed['events'][1]['feedback'])
        self.assertTrue(failed['failure']['evidence']['impossible_observation'])
        self.assertFalse(failed['failure']['evidence']['committed'])
        self.assertEqual(failed['events'][1]['forecast']['receipt'], contract.receipt(failed['events'][1]['forecast']))
        self.assertIsNone(failed['ended'])
        self.assertIsNone(good['failure'])
        self.assertEqual(len(good['events']), 3)

    def test_real_expansion_limit_preserves_committed_prefix_and_does_not_retry(self):
        bad = episode(6, 'budget')
        bad['actions'] = [{'kind': 'observe', 'participants': []} for _ in range(3)]
        bad['observations'][1] = dict.fromkeys(bad['ids'])
        trace = self.collect(inputs(bad, episode(3, 'next')), self.checkpoint(model=DomainFlatGRU()))
        failed, good = trace['episodes']
        self.assertEqual((failed['failure']['phase'], failed['failure']['step']), ('predict', 1))
        self.assertIn('expansion bound', failed['failure']['message'])
        self.assertEqual(len(failed['events']), 1)
        self.assertEqual(failed['events'][0]['feedback']['status'], 'RECEIVED')
        self.assertEqual(failed['events'][0]['feedback']['inference']['live_paths'], [64])
        self.assertIsNone(failed['ended'])
        self.assertIsNone(good['failure'])

    def test_start_and_end_failures_are_local_and_preserve_planned_episode_order(self):
        for rejected in ('start', 'end'):
            class RejectedPhase(Session):
                def _handle(self, request):
                    if request['episode'] == 'failed' and request['op'] == rejected:
                        raise ValueError('synthetic phase failure')
                    return super()._handle(request)
            with patch.object(runner, 'Session', RejectedPhase):
                trace = self.collect(inputs(episode(name='failed'), episode(name='next')),
                                     self.checkpoint(control='no_change'))
            failed, good = trace['episodes']
            self.assertEqual(failed['failure']['phase'], rejected)
            self.assertEqual(len(failed['events']), 0 if rejected == 'start' else 3)
            self.assertIsNone(failed['ended'])
            self.assertIsNone(good['failure'])

    def test_empirical_abstention_and_no_change_remain_distinct_native_controls(self):
        for predictor in ({'memory': DomainMemory('local')},
                          {'memory': DomainMemory('contact'), 'control': 'first_contact'}, {'control': 'no_change'}):
            trace = self.collect(inputs(episode()), self.checkpoint(**predictor))
            record = trace['episodes'][0]
            self.assertIsNone(record['failure'])
            expected = 'ABSTAIN' if 'memory' in predictor else 'PREDICTED'
            for event in record['events']:
                self.assertEqual(event['forecast']['status'], expected)
                if expected == 'ABSTAIN': self.assertIsNone(event['forecast']['log'])
            policy = predictor.get('control', 'local')
            self.assertEqual(trace['frozen_predictor_before']['effective_control'], policy)

    def test_gold_fields_are_rejected_before_checkpoint_loading_and_receipts_before_feedback(self):
        saved = self.checkpoint(control='no_change')
        for target in ('top', 'episode'):
            data = inputs(episode())
            (data if target == 'top' else data['episodes'][0])['oracle'] = {'truth': 1}
            with patch.object(runner, 'load_checkpoint') as loader, self.assertRaises(ValueError):
                self.collect(data, saved)
            loader.assert_not_called()
        seen = []
        class BadReceipt(Session):
            def _handle(self, request):
                seen.append(request['op'])
                reply = super()._handle(request)
                if request['op'] == 'predict': reply['receipt'] = '0' * 64
                return reply
        with patch.object(runner, 'Session', BadReceipt):
            record = self.collect(inputs(episode()), saved)['episodes'][0]
        self.assertEqual(seen, ['start', 'predict'])
        self.assertEqual(record['events'], [])
        self.assertEqual(record['failure']['phase'], 'predict')
        self.assertIn('receipt', record['failure']['message'])

    def test_weight_configuration_and_current_metadata_mutation_on_error_invalidate_entire_trace(self):
        saved = self.checkpoint(model=DomainKernel())
        def weight(session):
            with torch.no_grad(): next(session.model.parameters()).add_(.125)
        mutations = (weight, lambda s: setattr(s.model, 'persistence', not s.model.persistence),
                     lambda s: s.model.training_provenance.update(status='changed'),
                     lambda s: s.model.domain_adaptation.update(active_learned_parameters_sha256='0' * 64),
                     lambda s: s.model.checkpoint_metadata.update(version='changed'),
                     lambda s: s.model.train())
        for mutate in mutations:
            loaded = load_checkpoint(*saved)
            class Mutated(Session):
                def _handle(self, request):
                    if request['op'] == 'feedback':
                        mutate(self)
                        raise RuntimeError('synthetic terminal error after mutation')
                    return super()._handle(request)
            with patch.object(runner, 'load_checkpoint', return_value=loaded), \
                    patch.object(runner, 'Session', Mutated), self.assertRaisesRegex(ValueError, 'frozen predictor'):
                self.collect(inputs(episode()), saved)

    def test_table_effective_policy_and_no_change_metadata_mutation_on_error_are_rejected(self):
        def table(session):
            key, _ = domain_context((0, 0, 0), (0, 2, 2, -1), (), 'local')
            session.memory.table[key] = Counter({(0, 0, 0): 1})
        for predictor, mutate in (({'memory': DomainMemory('local')}, table),
                ({'memory': DomainMemory('local')}, lambda s: setattr(s.memory, 'control_name', 'contact')),
                ({'control': 'no_change'}, lambda s: s.checkpoint_metadata.update(version='changed'))):
            saved = self.checkpoint(**predictor)
            class Mutated(Session):
                def _handle(self, request):
                    if request['op'] == 'feedback':
                        mutate(self)
                        raise RuntimeError('synthetic terminal error after mutation')
                    return super()._handle(request)
            with patch.object(runner, 'Session', Mutated), self.assertRaisesRegex(ValueError, 'frozen predictor'):
                self.collect(inputs(episode()), saved)

    def test_actual_cli_loads_only_hashed_native_inputs_and_does_not_overwrite(self):
        checkpoint, checkpoint_sha = self.checkpoint(model=DomainFlatGRU(hidden=4))
        source, output = self.root / 'inputs.json', self.root / 'trace.json'
        source_sha = contract.write_json(source, inputs(episode(6)))
        command = [sys.executable, '-m', 'experiments.predictive_nucleus.acceptance_runner', 'collect',
                   '--inputs', str(source), '--inputs-sha256', source_sha, '--checkpoint', str(checkpoint),
                   '--checkpoint-sha256', checkpoint_sha, '--participant', 'flat', '--seed', '7', '--output', str(output)]
        environment = {**os.environ, 'OMP_NUM_THREADS': '1', 'MKL_NUM_THREADS': '1', 'PYTHONHASHSEED': '0'}
        completed = subprocess.run(command, cwd=Path(__file__).resolve().parents[3], env=environment,
                                   text=True, capture_output=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        raw = output.read_bytes(); trace = contract.load_json(output, sha256(raw).hexdigest())
        self.assertEqual(trace['version'], runner.VERSION)
        self.assertEqual(trace['input_sha256'], contract.digest(contract.validate_inputs(json.loads(source.read_text()))))
        self.assertIsNone(trace['episodes'][0]['failure'])
        self.assertEqual(trace['frozen_predictor_before'], trace['frozen_predictor_after'])
        repeated = subprocess.run(command, cwd=Path(__file__).resolve().parents[3], env=environment,
                                  text=True, capture_output=True, timeout=30)
        self.assertNotEqual(repeated.returncode, 0)
        self.assertEqual(output.read_bytes(), raw)


if __name__ == '__main__':
    unittest.main()
