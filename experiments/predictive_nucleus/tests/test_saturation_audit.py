"""Synthetic saved-audit checks: no scientific fitting or forecast execution."""
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import audit_saturation_saved as audit


class SaturationAuditTests(unittest.TestCase):
    def fixture(self):
        delta = {'regressions': [], 'mean_nll_change': -.1}
        comparison = {'native': {'unsaturated': deepcopy(delta)},
            'retention': {'unsaturated': {'old': deepcopy(delta)}},
            'retention_pair': {'old': deepcopy(delta)}, 'fresh_pair': deepcopy(delta)}
        return {'checks': {'probability': True}}, comparison, {'final_observed_train_nll': .01}

    def test_every_retention_boundary_can_block_decision(self):
        for path in (('native', 'unsaturated'), ('retention', 'unsaturated', 'old'),
                     ('retention_pair', 'old'), ('fresh_pair',)):
            report, comparison, fit = self.fixture(); node = comparison
            for key in path: node = node[key]
            node['regressions'] = [['synthetic', 0]]
            self.assertFalse(all(audit.decision_checks(report, comparison, fit, .05).values()))

    def test_probability_fit_and_undefined_changes_remain_failures(self):
        report, comparison, fit = self.fixture()
        self.assertTrue(all(audit.decision_checks(report, comparison, fit, .05).values()))
        for value in (.01, None):
            comparison['fresh_pair']['mean_nll_change'] = value
            self.assertFalse(audit.decision_checks(report, comparison, fit, .05)['paired_mean_nll'])
        fit['final_observed_train_nll'] = .051
        self.assertFalse(audit.decision_checks(report, comparison, fit, .05)['observed_training_fit'])
        report['checks']['probability'] = False
        self.assertFalse(audit.decision_checks(report, comparison, fit, .05)['probability'])

    def test_canonical_excludes_controls(self):
        measured = {('x', 0, 'canonical'): {'correct': True}, ('x', 0, 'swapped'): {'correct': False}}
        self.assertEqual(audit.canonical(measured), {('x', 0): {'correct': True}})

    def test_cli_serializes_failure_and_never_overwrites(self):
        report = {'decision': 'REVISE_SATURATION_HYPOTHESIS', 'audit_passed': False, 'check_count': 3, 'discrepancy_count': 1}
        with tempfile.TemporaryDirectory() as folder, patch.object(audit, 'audit_saved', return_value=report):
            path = Path(folder) / 'audit.json'; args = ['--repo', folder, '--output', str(path)]
            with redirect_stdout(StringIO()) as out: self.assertEqual(audit.main(args), 1)
            self.assertEqual(json.loads(path.read_text()), report)
            self.assertEqual(json.loads(out.getvalue()), report)
            with self.assertRaises(FileExistsError): audit.main(args)

    def test_auditor_imports_no_predictor_or_numerical_runtime(self):
        code = ('import sys; import experiments.predictive_nucleus.audit_saturation_saved; '
                'assert not any(m in sys.modules for m in ("torch", "numpy", '
                '"experiments.predictive_nucleus.saturation_run", "experiments.predictive_nucleus.saturation_scoring"))')
        subprocess.run([sys.executable, '-S', '-c', code], check=True, timeout=10)


if __name__ == '__main__': unittest.main()
