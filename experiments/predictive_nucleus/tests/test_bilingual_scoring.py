"""Synthetic forecasts exercise scoring and hostile trace failures; no models fit/run."""
from copy import deepcopy
from itertools import product
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import bilingual_scoring as scoring

LIMITS = {'min_accuracy': .95, 'max_mean_nll': .05, 'min_true_probability': .9,
    'max_wrong_order_probability': .1, 'max_twin_tv': .02, 'max_parser_accuracy_gap': .02,
    'min_ablation_accuracy_gain': .10, 'min_shuffle_accuracy_gain': .25}


def distribution(target, probability=.99, size=8):
    return [math.log(probability if i == target else (1 - probability) / (size - 1)) for i in range(size)]


def bank(law):
    records, gold = [], []
    for direction, language, synonym in product((0, 1), ('svo', 'osv'), (0, 1)):
        identity = f'{direction}-{language}-{synonym}'
        action = [0, direction, 1 - direction, -1]
        a, b = ['a', 'b'][direction], ['a', 'b'][1 - direction]
        word = ('contacts', 'touches')[synonym] if language == 'svo' else ('dax', 'mip')[synonym]
        text = f'{a} {word} {b}' if language == 'svo' else f'{b} {a} {word}'
        truth = [1, 0, 0] if direction == 0 else [0, 1, 0]
        opposite = [0, 1, 0] if direction == 0 else [1, 0, 0]
        records.append({'id': identity, 'entities': ['a', 'b', 'c'], 'anchor': [0, 0, 0],
            'context': [{'action': [0, 0, 1, -1], 'reading': [0, 0, 0]}],
            'utterances': [{'text': text, 'reading': truth.copy()} for _ in range(2)]})
        gold.append({'id': identity, 'family': 'synthetic', 'lineage': 'lineage', 'mode': 0,
            'law': law, 'direction': direction, 'language': language, 'synonym': synonym,
            'physical_id': f'physical-{direction}', 'role_pair_id': f'role-{language}-{synonym}',
            'bilingual_pair_id': f'bilingual-{direction}-{synonym}', 'synonym_pair_id': f'synonym-{direction}-{language}',
            'actions': [action.copy() for _ in range(2)], 'action_orders': [int(language == 'osv')] * 2,
            'truth': [truth.copy() for _ in range(2)], 'opposite_truth': [opposite.copy() for _ in range(2)]})
    inputs = {'version': 'bilingual-input-v1', 'episodes': records}
    return inputs, {'version': 'bilingual-oracle-v1', 'input_sha256': scoring.contract.digest(inputs), 'episodes': gold}


class BilingualScoringTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.data, self.output = Path(temporary.name) / 'data', Path(temporary.name) / 'output'
        self.data.mkdir(); self.output.mkdir()
        self.config = {'version': 'bilingual-synthetic-v1', 'model_seeds': [7], 'analysis': LIMITS}
        artifacts, self.banks = {}, {}
        for law in scoring.LAWS:
            inputs, oracle = self.banks[law] = bank(law)
            for kind, value in (('inputs', inputs), ('oracle', oracle)):
                name = f'{law}-{kind}.json.xz'
                artifacts[name] = scoring.io._write(self.data / name, value)
        self.freeze = {'sources': {'bilingual_scoring.py': scoring.io._hash(Path(scoring.__file__))},
                       'artifacts': artifacts, 'checkpoints': {'synthetic': True}}
        scoring.io._write(self.data / 'freeze.json', self.freeze)
        for law in scoring.LAWS:
            inputs, oracle = self.banks[law]
            for arm in scoring.ARMS:
                rows = []
                for meta in oracle['episodes']:
                    for t, truth in enumerate(meta['truth']):
                        successful = arm in ('grounded', 'parser', 'sequence')
                        target = scoring._index(truth if successful else meta['opposite_truth'][t])
                        order = meta['action_orders'][t] if successful else 1 - meta['action_orders'][t]
                        rows.append({'id': meta['id'], 'step': t, 'logp': distribution(target),
                            'order_logp': None if arm in ('sequence', 'text_only') else distribution(order, size=2)})
                digest = scoring.contract.digest('grounded' if arm == 'shuffled' else arm)
                scoring.io._write(self.path(law, arm), {'law': law, 'seed': 7, 'arm': arm, 'points': rows,
                    'resources': {'cpu_seconds': 0.001}, 'input_sha256': scoring.contract.digest(inputs),
                    'freeze_sha256': scoring.io._hash(self.data / 'freeze.json'),
                    'checkpoint_sha256': digest, 'training_sha256': 'a' * 64})

    def path(self, law='nand', arm='grounded'):
        return self.output / f'trace-{law}-7-{arm}.json.xz'

    def edit_trace(self, change, law='nand', arm='grounded'):
        path = self.path(law, arm)
        trace = scoring.io._read(path); change(trace)
        path.unlink(); scoring.io._write(path, trace)

    @staticmethod
    def native(inputs, gold, inventory, law, seed):
        return {(meta['id'], t): {'id': meta['id'], 'step': t,
            'logp': distribution(scoring._index(bits), .999), 'order_logp': None}
            for meta in gold.values() for t, bits in enumerate(meta['truth'])}

    def evaluate(self):
        with patch.object(scoring, '_native', side_effect=self.native):
            return scoring.evaluate(self.data, self.output, self.config, self.freeze)

    def test_complete_synthetic_result_with_every_control_and_denominator(self):
        report = self.evaluate()
        self.assertEqual(report['decision']['decision'], 'KEEP_BILINGUAL_GROUNDING')
        self.assertFalse(report['decision']['scientific_admission'])
        self.assertEqual(len(report['by_trace']), 12)
        row = report['by_trace']['nand/7/grounded']
        self.assertEqual(row['all']['planned'], 16)
        self.assertEqual(row['all']['accuracy'], 1.)
        self.assertEqual(row['all']['order_correct'], 16)
        self.assertAlmostEqual(row['all']['mean_nll'], -math.log(.99))
        self.assertAlmostEqual(row['all']['mean_brier'], .0001 + .0001 / 7)
        self.assertAlmostEqual(row['all']['ece_10'], .01)
        self.assertEqual(row['by_entity_count']['3']['planned'], 16)
        self.assertEqual(row['by_family_language']['synthetic/svo']['role_pairs_planned'], 2)
        self.assertEqual(row['twins']['bilingual']['forecast_pairs'], 8)
        self.assertEqual(row['twins']['synonym']['max_tv'], 0.)
        self.assertEqual(report['retention']['nand/7']['nll_worse_count'], 16)
        self.assertEqual(len(report['native_reference']['nand/7']['points']), 16)
        json.dumps(report, allow_nan=False)

    def test_native_correct_regression_keeps_exact_id_and_probability_cost(self):
        self.edit_trace(lambda trace: trace['points'][0].update(logp=distribution(2)))
        result = self.evaluate()
        self.assertEqual(result['decision']['decision'], 'REVISE_BILINGUAL_GROUNDING')
        self.assertEqual(result['retention']['nand/7']['native_correct_now_wrong'], [['0-svo-0', 0]])
        self.assertFalse(result['decision']['checks']['nand/7']['native_retention'])
        self.assertFalse(result['decision']['checks']['nand/7']['role_trajectories_each_cell'])
        self.assertFalse(result['decision']['checks']['nand/7']['twins'])

    def test_map_accuracy_cannot_hide_bad_probabilities(self):
        self.edit_trace(lambda trace: trace['points'][0].update(logp=distribution(4, .80)))
        result = self.evaluate()
        self.assertEqual(result['by_trace']['nand/7/grounded']['all']['accuracy'], 1.)
        self.assertFalse(result['decision']['checks']['nand/7']['critical_true_probability'])
        self.assertEqual(result['decision']['decision'], 'REVISE_BILINGUAL_GROUNDING')

    def test_missing_and_duplicate_records_fail_before_gold_is_opened(self):
        self.edit_trace(lambda trace: trace['points'].pop(), law='nor', arm='shuffled')
        original, opened = scoring.io._read, []
        def read(path):
            opened.append(Path(path).name)
            return original(path)
        with patch.object(scoring.io, '_read', side_effect=read), self.assertRaisesRegex(ValueError, 'missing planned'):
            self.evaluate()
        self.assertFalse(any('oracle' in name for name in opened))
        self.edit_trace(lambda trace: trace['points'].append(deepcopy(trace['points'][0])))
        with self.assertRaisesRegex(ValueError, 'duplicate forecast'):
            self.evaluate()

    def test_missing_file_is_execution_failure(self):
        self.path('nor', 'parser').unlink()
        with self.assertRaises(FileNotFoundError): self.evaluate()

    def test_forecast_geometry_normalization_and_infinity(self):
        for values in ([0.] * 8, distribution(4)[:-1], [math.nan] * 8, [math.inf] * 8, [True] * 8):
            with self.subTest(values=values), self.assertRaises(ValueError): scoring._logs(values, 8)
        self.assertEqual(scoring._logs([0.] + ['negative_infinity'] * 7, 8), [0.] + [-math.inf] * 7)

    def test_source_input_checkpoint_and_training_bindings_are_checked(self):
        original = scoring.io._read(self.path('nor'))
        for key, value in (('input_sha256', 'b' * 64), ('freeze_sha256', 'b' * 64),
                           ('checkpoint_sha256', 'b' * 64), ('training_sha256', 'b' * 64)):
            with self.subTest(key=key):
                self.edit_trace(lambda trace: trace.update({key: value}), law='nor')
                with self.assertRaises(ValueError): self.evaluate()
                self.path('nor').unlink(); scoring.io._write(self.path('nor'), original)
        self.freeze['sources']['bilingual_scoring.py'] = 'b' * 64
        with self.assertRaisesRegex(ValueError, 'freeze manifest'): self.evaluate()

    def test_exact_ties_use_first_world_without_gold_tiebreak(self):
        inputs, oracle = self.banks['nand']
        records, gold, _ = scoring._inventory(inputs, oracle, 'nand')
        row = {'id': '0-svo-0', 'step': 0, 'logp': [-math.log(8)] * 8, 'order_logp': [-math.log(2)] * 2}
        point = scoring._point(row, records[row['id']], gold[row['id']])
        self.assertEqual(point['map_world'], 0)
        self.assertFalse(point['correct'])

    def test_oracle_twin_and_order_tampering_rejected(self):
        inputs, oracle = self.banks['nand']
        changed = deepcopy(oracle); changed['episodes'][0]['action_orders'][0] = 1
        with self.assertRaisesRegex(ValueError, 'order/action'): scoring._inventory(inputs, changed, 'nand')
        changed = deepcopy(oracle); changed['episodes'][0]['bilingual_pair_id'] = 'unpaired'
        with self.assertRaisesRegex(ValueError, 'incomplete planned'): scoring._inventory(inputs, changed, 'nand')

    def test_control_success_prevents_false_grounding_superiority(self):
        def correct_control(trace):
            for row in trace['points']:
                row['logp'] = distribution(4 if row['id'].startswith('0') else 2)
        self.edit_trace(correct_control, arm='text_only')
        report = self.evaluate()
        self.assertFalse(report['decision']['checks']['nand/7']['grounding_ablation_gain'])
        self.assertEqual(report['decision']['decision'], 'REVISE_BILINGUAL_GROUNDING')

    def test_zero_probability_truth_is_retained_failure_not_execution_error(self):
        def impossible_truth(trace):
            for row in trace['points']:
                row['logp'] = [0.] + ['negative_infinity'] * 7
        for arm in scoring.ARMS: self.edit_trace(impossible_truth, arm=arm)
        report = self.evaluate()
        self.assertEqual(report['decision']['decision'], 'REVISE_BILINGUAL_GROUNDING')
        self.assertEqual(report['by_trace']['nand/7/grounded']['all']['mean_nll'], 'positive_infinity')
        self.assertIsNone(report['comparisons']['nand/7']['parser']['grounded_minus_nll'])
        self.assertEqual(report['retention']['nand/7']['nll_worse_count'], 16)
        json.dumps(report, allow_nan=False)


if __name__ == '__main__': unittest.main()
