"""Saved-evidence recovery invariants; no research fitting or collection."""
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import audit_binding_saved as a


class BindingSavedAuditTests(unittest.TestCase):
    def records(self):
        return {'one': {'entities': ['A', 'B', 'C'], 'utterances': [{'text': 'A z B'}]}}

    def row(self, **changes):
        return dict({'id': 'one', 'step': 0, 'logp': [-math.log(8)] * 8,
                     'order_logp': [-math.log(2)] * 2}, **changes)

    def report(self):
        return {'audit_passed': True, 'recovered_scientific_interpretation': 'REVISE_STRUCTURAL_BINDING',
                'original_process_status': 'STOP_INCOMPLETE_EXECUTION'}

    def test_normalization_and_finite_extreme_logs(self):
        a.logs([0., -1000.], 2)
        a.logs([0., 'negative_infinity'], 2)
        for values in ([0., 0.], [True, -1000.], [float('nan'), 0.], [float('inf'), 0.],
                       ['negative_infinity'] * 2, ['oops', 0.], [0.]):
            with self.subTest(values=values), self.assertRaises(ValueError): a.logs(values, 2)

    def test_missing_duplicate_unplanned_and_boolean_steps_rejected(self):
        records = self.records()
        self.assertEqual(len(a.rows([self.row()], records)), 1)
        for value in ([], [self.row(), self.row()], [self.row(step=True)],
                      [self.row(step=1)], [self.row(id='other')]):
            with self.subTest(value=value), self.assertRaises(ValueError): a.rows(value, records)

    def test_fresh_requires_both_controls_and_exact_fields(self):
        values = [self.row(view=view) for view in ('canonical', 'masked', 'swapped')]
        self.assertEqual(len(a.rows(values, self.records(), fresh=True)), 3)
        with self.assertRaises(ValueError): a.rows(values[:-1], self.records(), fresh=True)
        bad = deepcopy(values); bad[0]['target'] = [0, 1, 0]
        with self.assertRaises(ValueError): a.rows(bad, self.records(), fresh=True)

    def test_native_references_cannot_supply_language_order(self):
        self.assertEqual(len(a.rows([self.row(order_logp=None)], self.records(), native=True)), 1)
        with self.assertRaises(ValueError): a.rows([self.row()], self.records(), native=True)
        with self.assertRaises(ValueError): a.rows([self.row(order_logp=None)], self.records())

    def test_delta_retains_repairs_regressions_and_infinite_losses(self):
        old = {('a', 0): {'correct': True, 'nll': 0.}, ('b', 0): {'correct': False, 'nll': 3.},
               ('c', 0): {'correct': False, 'nll': math.inf}}
        new = {('a', 0): {'correct': False, 'nll': 2.}, ('b', 0): {'correct': True, 'nll': .2},
               ('c', 0): {'correct': False, 'nll': math.inf}}
        result = a.delta(new, old)
        self.assertEqual(result['repairs'], [['b', 0]])
        self.assertEqual(result['regressions'], [['a', 0]])
        self.assertEqual(result['nll_undefined_difference'], [['c', 0]])
        self.assertIsNone(result['mean_nll_change'])
        with self.assertRaises(ValueError): a.delta({}, old)

    def test_writer_and_console_are_both_serialized_and_preserve_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'audit.json'
            console = json.loads(a.write_report(path, self.report()))
            self.assertEqual(json.loads(path.read_text()), self.report())
            self.assertEqual(console['original_process_status'], 'STOP_INCOMPLETE_EXECUTION')
            with self.assertRaises(FileExistsError): a.write_report(path, self.report())

    def test_serialization_failure_leaves_no_output(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'audit.json'
            with self.assertRaises(ValueError): a.write_report(path, {**self.report(), 'bad': float('nan')})
            self.assertFalse(path.exists())

    def test_complete_cli_reaches_stdout_and_exit_code(self):
        for passed in (True, False):
            with self.subTest(passed=passed), tempfile.TemporaryDirectory() as folder:
                path, stdout = Path(folder) / 'audit.json', StringIO()
                with patch.object(a, 'audit_saved', return_value={**self.report(), 'audit_passed': passed}), redirect_stdout(stdout):
                    code = a.main(['--repo', folder, '--output', str(path)])
                self.assertEqual(code, int(not passed))
                self.assertEqual(json.loads(stdout.getvalue())['audit_passed'], passed)
                self.assertEqual(json.loads(path.read_text())['audit_passed'], passed)

    def test_saved_factor_geometry_matches_original_tensor_algebra(self):
        import torch
        from experiments.predictive_nucleus.binding_model import encoder, factor_inputs
        from experiments.predictive_nucleus.bilingual_model import tokenize_batch
        model = encoder('factor', 7)
        words = ['violet', 'amber', 'indigo']
        state = {key: value.detach().tolist() for key, value in model.state_dict().items()}
        result = a.factor_geometry(state, words)
        features, _ = tokenize_batch(['A ' + word + ' B' for word in words], [['A', 'B', 'C']] * 3)
        with torch.no_grad():
            lexical, _ = factor_inputs(features)
            expected = model.lexical(lexical).flatten().tolist()
            layouts = model.layout(torch.tensor([[0., 1., 1.], [1., 0., 1.], [1., 1., 0.]], dtype=torch.float64)).flatten().tolist()
        for word, value in zip(words, expected):
            self.assertAlmostEqual(result['lexical'][word]['scalar'], value, places=14)
            self.assertAlmostEqual(result['lexical'][word]['output_tanh_derivative'], 1 - value * value, places=14)
        for index, value in enumerate(layouts):
            self.assertAlmostEqual(result['layout_by_lexical_position'][str(index)]['scalar'], value, places=14)

    def test_import_has_no_model_or_scientific_runner_side_effects(self):
        code = "from experiments.predictive_nucleus import audit_binding_saved; import sys; assert 'torch' not in sys.modules; assert 'experiments.predictive_nucleus.binding_scoring' not in sys.modules; assert 'experiments.predictive_nucleus.binding_study' not in sys.modules"
        subprocess.run([sys.executable, '-c', code], check=True)


if __name__ == '__main__': unittest.main()
