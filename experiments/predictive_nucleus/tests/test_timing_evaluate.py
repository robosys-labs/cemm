"""Small synthetic checkpoint/trace fixtures for prospective failure accounting."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import active_checkpoint, timing_contract as contract
from experiments.predictive_nucleus import timing_data, timing_oracle, timing_runner
from experiments.predictive_nucleus.acceptance_contract import receipt
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.timing_evaluate import evaluate
from experiments.predictive_nucleus.timing_session import sources


def tiny_bundle():
    bundle = {'inputs': {'version': 'timing-input-v1', 'episodes': []}, 'cases': [], 'permutation_pairs': []}
    gold, information = [], []
    for direction in (0, 1):
        def pair(a, b): return [b, a] if direction else [a, b]
        case = {'episode': f'timing-{direction}', 'ids': ['c', 'a', 'b'],
            'observations': [{'a': 0, 'b': 1, 'c': 0}],
            'actions': [{'kind': 'contact', 'participants': pair('a', 'b')},
                {'kind': 'contact_group', 'timing': 'ordered', 'contacts': [pair('a', 'b'), pair('b', 'c')]},
                {'kind': 'contact', 'participants': pair('c', 'a')}],
            'coverage': [['c', 'a', 'b'] for _ in range(3)]}
        truth = timing_data._realize(case, 'nand', 0)
        forecasts = timing_oracle.forecast_episode(case, 'nand')
        bundle['inputs']['episodes'].append(case)
        bundle['cases'].append({'episode': case['episode'], 'family': 'chain', 'partition': 'held_out',
            'lineage': 'synthetic-lineage', 'pair_id': 'synthetic-pair', 'direction': direction,
            'condition': 'ordered', 'group_step': 1, 'contact_count': 4,
            'permutation_pair_id': f'synthetic-permutation-{direction}'})
        bundle['permutation_pairs'].append({'permutation_pair_id': f'synthetic-permutation-{direction}',
                                            'nontrivial_event_permutation': True})
        gold.append({'episode': case['episode'], 'truth': truth,
            'possible_worlds': [f['possible_worlds'] for f in forecasts],
            'information_keys': [f['information_key'] for f in forecasts]})
        information.append({'episode': case['episode'], 'forecasts': forecasts})
    identity = {'input_sha256': contract.digest(bundle['inputs']), 'source_sha256': timing_oracle.source_digest(),
                'information_law_sha256': timing_oracle.law_digest('nand')}
    bundle['oracle'] = {'version': 'timing-oracle-v1', **identity, 'episodes': gold}
    bundle['information'] = {'version': 'timing-information-v1', **identity, 'episodes': information}
    return bundle


def rebind(record):
    """Recompute self-reported hashes, so source/semantic checks must still reject."""
    identity = contract.digest(record['started']['implementation'])
    record['started']['implementation_sha256'] = identity
    for event in record['events']:
        event['forecast']['implementation_sha256'] = identity
        event['forecast']['receipt'] = receipt(event['forecast'])


class TimingEvaluateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = TemporaryDirectory()
        cls.path = Path(cls.directory.name) / 'synthetic.json'
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(67031)
            saved = active_checkpoint.save_checkpoint(cls.path, model=DomainKernel().eval(),
                provenance={'training_input_sha256': None, 'objective': 'untrained_or_inherited', 'completed_updates': 0})
        cls.sha = saved['sha256']
        cls.bundle = tiny_bundle()
        cls.trace = cls.collect()
        cls.plan = {'version': 'timing-plan-v1', 'input_sha256': contract.digest(cls.bundle['inputs']),
            **{k + '_sha256': contract.digest(cls.bundle[k]) for k in ('oracle', 'information', 'cases')},
            'model_seeds': [7], 'checkpoints': {'7': cls.sha},
            'checkpoint_states': {'7': saved['state_sha256']},
            'software_sha256': {**sources(), **cls.trace['source_sha256']}}

    @classmethod
    def tearDownClass(cls): cls.directory.cleanup()

    @classmethod
    def collect(cls):
        return timing_runner.collect(cls.bundle['inputs'], checkpoint=cls.path, expected_sha256=cls.sha, model_seed=7)

    def test_complete_and_missing_records_keep_the_same_planned_denominator(self):
        report, cases = evaluate(self.plan, self.bundle, [self.trace])
        self.assertTrue(report['execution_complete'])
        self.assertEqual(len(cases), 2)
        self.assertEqual(report['aggregate']['all']['planned_points'], 6)
        self.assertEqual(report['aggregate']['all']['supported_forecasts'], 6)
        self.assertTrue(all('oracle_kl' in p for p in report['points']))
        for trace in (None, {**deepcopy(self.trace), 'episodes': self.trace['episodes'][:1]}):
            missing, _ = evaluate(self.plan, self.bundle, [] if trace is None else [trace])
            metrics = missing['aggregate']['all']
            self.assertFalse(missing['execution_complete'])
            self.assertEqual(metrics['planned_points'], 6)
            self.assertEqual(metrics['unproduced_forecasts'], 6 if trace is None else 3)
            self.assertIsNone(metrics['mean_nll'])

    def test_feedback_failure_keeps_its_forecast_and_marks_only_later_points_missing(self):
        original = timing_runner.Session.handle
        def fail(session, request):
            if request.get('op') == 'feedback' and request['episode'] == 'timing-0' and request['step'] == 1:
                raise ValueError('synthetic endpoint failure')
            return original(session, request)
        with patch.object(timing_runner.Session, 'handle', fail): trace = self.collect()
        failed = trace['episodes'][0]
        self.assertEqual(failed['failure']['phase'], 'feedback')
        self.assertEqual(len(failed['events']), 2)
        self.assertIsNone(failed['events'][-1]['feedback'])
        report, _ = evaluate(self.plan, self.bundle, [trace])
        self.assertFalse(report['execution_complete'])
        self.assertEqual(report['aggregate']['all']['supported_forecasts'], 5)
        self.assertEqual(report['aggregate']['all']['unproduced_forecasts'], 1)
        states = {(p['episode'], p['step']): p['status'] for p in report['points']}
        self.assertEqual(states['timing-0', 1], 'ANSWERED')
        self.assertEqual(states['timing-0', 2], 'UNPRODUCED')

    def test_invalid_end_acknowledgment_is_retained_as_terminal_execution_failure(self):
        original = timing_runner.Session.handle
        def fail(session, request):
            result = original(session, request)
            if request.get('op') == 'end': result['predictions'] = 999
            return result
        with patch.object(timing_runner.Session, 'handle', fail): trace = self.collect()
        self.assertTrue(all(r['failure']['phase'] == 'end' and r['ended'] is None for r in trace['episodes']))
        report, _ = evaluate(self.plan, self.bundle, [trace])
        self.assertFalse(report['execution_complete'])
        self.assertEqual(report['aggregate']['all']['supported_forecasts'], 6)

    def test_tampered_receipts_timing_source_state_and_stray_fields_are_rejected(self):
        mutations = (
            lambda t: t['episodes'][0]['events'][1]['forecast'].__setitem__('receipt', '0' * 64),
            lambda t: t['episodes'][0]['events'][1]['forecast']['action'].__setitem__('timing', 'common_snapshot'),
            lambda t: t['source_sha256'].__setitem__('timing_runner.py', '0' * 64),
            lambda t: t.__setitem__('checkpoint_sha256', '0' * 64),
            lambda t: t['frozen_predictor_after'].__setitem__('state_sha256', '0' * 64),
            lambda t: t['episodes'][0].__setitem__('hidden_mode', 0),
        )
        for index, mutate in enumerate(mutations):
            changed = deepcopy(self.trace); mutate(changed)
            with self.subTest(index=index), self.assertRaises(ValueError): evaluate(self.plan, self.bundle, [changed])
        for field in ('source', 'extra', 'scheduler', 'domain', 'gate'):
            changed = deepcopy(self.trace)
            record = changed['episodes'][0]; identity = record['started']['implementation']
            if field == 'source': identity['source_sha256']['timing_kernel.py'] = '0' * 64
            elif field == 'extra': identity['hidden_mode'] = 0
            elif field == 'scheduler': identity['scheduler'] = 'independent_mode_resampling'
            elif field == 'domain': identity['domain']['full_feedback'] = False
            else: identity['gate_g1'] = 'ADMITTED'
            rebind(record)
            with self.subTest(identity=field), self.assertRaises(ValueError): evaluate(self.plan, self.bundle, [changed])

    def test_failure_phase_cannot_relabel_successful_history(self):
        for phase, step in (('start', 0), ('predict', 3), ('feedback', 2)):
            changed = deepcopy(self.trace)
            changed['episodes'][0]['ended'] = None
            changed['episodes'][0]['failure'] = {'phase': phase, 'step': step,
                'error_type': 'ValueError', 'message': 'invented boundary'}
            with self.subTest(phase=phase), self.assertRaises(ValueError): evaluate(self.plan, self.bundle, [changed])


if __name__ == '__main__':
    unittest.main()
