"""Native recording-to-scoring invariants with hand-authored gold; no research results."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus.acceptance_runner import collect
from experiments.predictive_nucleus.acceptance_scoring import evaluate
from experiments.predictive_nucleus.active_checkpoint import save_checkpoint
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.tests.test_acceptance_contract import make_bundle, refresh_hashes


class AcceptanceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'native.json'

    def native(self, plan, inputs, model=None):
        arguments = {'model': model} if model is not None else {'control': 'no_change'}
        saved = save_checkpoint(self.path, provenance={'objective': 'untrained_or_inherited' if model is not None
            else 'no_change', 'training_input_sha256': None, 'completed_updates': 0}, **arguments)
        plan['participants'] = {'reference': {str(s): saved['sha256'] for s in plan['model_seeds']}}
        plan['reference_participant'] = 'reference'
        return collect(inputs, checkpoint=self.path, expected_sha256=saved['sha256'],
                       participant='reference', model_seed=7)

    def test_native_trace_scores_complete_role_pairs_and_missing_seed_stays_planned(self):
        plan, inputs, oracle = make_bundle(entities=6)
        plan['model_seeds'] = [7, 11]
        trace = self.native(plan, inputs)
        report = evaluate(plan, inputs, oracle, [trace])
        metrics = report['participants']['reference']
        self.assertEqual(metrics['aggregate']['all']['planned_points'], 8)
        self.assertEqual(metrics['aggregate']['all']['supported_forecasts'], 4)
        self.assertEqual(metrics['aggregate']['all']['unproduced_forecasts'], 4)
        self.assertEqual(metrics['aggregate']['all']['accuracy'], .5)
        self.assertIsNone(metrics['aggregate']['all']['mean_nll'])
        self.assertEqual(metrics['aggregate']['all']['conditional_mean_nll'], 0)
        self.assertEqual(metrics['by_seed']['7']['role_pairs']['exact'], 1)
        self.assertEqual(metrics['by_seed']['11']['role_pairs']['exact'], 0)
        self.assertEqual(metrics['seed_summary']['metrics']['accuracy']['worst'], 0)
        self.assertEqual(report['metadata']['physical_lineages'], 1)
        self.assertEqual(report['metadata']['reused_checkpoints'][0]['model_seeds'], [7, 11])
        self.assertFalse(report['metadata']['independent_custody_verified'])
        self.assertFalse(report['metadata']['scientific_admission'])

    def test_hidden_oracle_targets_cannot_change_recorded_predictions(self):
        plan, inputs, oracle = make_bundle(steps=1)
        for case, gold in zip(inputs['episodes'], oracle['episodes'], strict=True):
            case['observations'][1]['a'] = None
            gold['possible_worlds'][0] = [0, 4]
        refresh_hashes(plan, inputs, oracle)
        trace = self.native(plan, inputs)
        committed = contract.digest(trace)
        first = evaluate(plan, inputs, oracle, [trace])
        alternate = deepcopy(oracle)
        for case in alternate['episodes']: case['truth'][1]['a'] = 1
        second_plan = deepcopy(plan); second_plan['oracle_sha256'] = contract.digest(alternate)
        second = evaluate(second_plan, inputs, alternate, [trace])
        self.assertEqual(contract.digest(trace), committed)
        self.assertEqual(first['aggregate']['ambiguous']['planned_points'], 2)
        self.assertEqual(first['aggregate']['all']['accuracy'], 1)
        self.assertEqual(second['aggregate']['all']['accuracy'], 0)
        self.assertEqual(second['aggregate']['all']['mean_nll'], 'positive_infinity')
        self.assertEqual(first['metadata']['trace_sha256'], second['metadata']['trace_sha256'])

    def test_real_terminal_contradiction_retains_score_and_future_denominator(self):
        plan, inputs, oracle = make_bundle()
        for case in inputs['episodes']:
            case['actions'] = [{'kind': 'observe', 'participants': []} for _ in range(2)]
        for row in plan['cases']: row.update(pair_id=None, direction=None)
        for t in (1, 2):
            inputs['episodes'][0]['observations'][t]['a'] = 1
            oracle['episodes'][0]['truth'][t]['a'] = 1
        oracle['episodes'][0]['possible_worlds'] = [[0, 4], [4]]
        oracle['episodes'][1]['possible_worlds'] = [[0, 4], [0]]
        refresh_hashes(plan, inputs, oracle)
        trace = self.native(plan, inputs, DomainKernel(hidden=2, persistence=True))
        self.assertEqual(trace['episodes'][0]['failure']['phase'], 'feedback')
        report = evaluate(plan, inputs, oracle, [trace])
        scored = report['aggregate']['all']
        self.assertEqual((scored['planned_points'], scored['supported_forecasts'], scored['unproduced_forecasts']), (4, 3, 1))
        self.assertEqual(scored['infinite_nll_count'], 1)
        self.assertIsNone(scored['mean_nll'])
        self.assertEqual(scored['conditional_mean_nll'], 'positive_infinity')
        self.assertEqual(report['aggregate']['trajectories']['exact'], 1)
        failures = report['metadata']['failure_records']
        self.assertEqual(len(failures), 1)
        self.assertFalse(failures[0]['evidence']['committed'])

    def test_native_trace_receipt_identity_and_failure_accounting_are_checked(self):
        plan, inputs, oracle = make_bundle()
        trace = self.native(plan, inputs)
        variants = []
        altered = deepcopy(trace)
        altered['episodes'][0]['events'][0]['forecast']['log']['values'][0][0] = -1
        variants.append(altered)
        altered = deepcopy(trace)
        altered['episodes'][0]['events'][0]['forecast']['action']['participants'].reverse()
        forecast = altered['episodes'][0]['events'][0]['forecast']
        forecast['receipt'] = contract.receipt(forecast)
        variants.append(altered)
        altered = deepcopy(trace)
        altered['episodes'][0]['ended']['feedback_steps'] = 1
        variants.append(altered)
        altered = deepcopy(trace)
        altered['episodes'][0]['failure'] = {'phase': 'predict', 'step': 0, 'error_type': 'ValueError', 'message': 'forged'}
        altered['episodes'][0]['ended'] = None
        variants.append(altered)
        altered = deepcopy(trace)
        altered['frozen_predictor_before']['predictor']['configuration']['unbound_option'] = True
        altered['frozen_predictor_after'] = deepcopy(altered['frozen_predictor_before'])
        variants.append(altered)
        altered = deepcopy(trace)
        forecast = altered['episodes'][0]['events'][0]['forecast']
        forecast['raw_log']['values'][0][0] = -1
        forecast['receipt'] = contract.receipt(forecast)
        variants.append(altered)
        altered = deepcopy(trace)
        forecast = altered['episodes'][0]['events'][0]['forecast']
        forecast['subtracted_log_mass'] = [1e-3]
        forecast['receipt'] = contract.receipt(forecast)
        variants.append(altered)
        for i, invalid in enumerate(variants):
            with self.subTest(i=i), self.assertRaises(ValueError): evaluate(plan, inputs, oracle, [invalid])


if __name__ == '__main__': unittest.main()
