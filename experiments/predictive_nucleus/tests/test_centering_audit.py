"""Synthetic receipts and decision boundaries; no research models or outcomes."""
from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import audit_centering_saved as audit


def initialization_fixture():
    def tensor(shape):
        return [tensor(shape[1:]) for _ in range(shape[0])] if shape else .125
    standard = {key: tensor(shape) for key, shape in audit.SHAPES.items()}
    standard['layout.0.weight'] = [[.15, -.3, .6]]
    standard['layout.0.bias'] = [.2]
    centered = deepcopy(standard)
    centered['layout.0.bias'] = [-.3]
    report = {'reports': {arm: {} for arm in audit.ARMS}, 'initialization': {
        'states': dict(zip(audit.ARMS, (standard, centered), strict=True)),
        'changed_key': 'layout.0.bias', 'changed_scalars': 1, 'unchanged_scalars': 88}}
    reseal(report)
    return report


def reseal(report):
    receipt = report['initialization']; standard, centered = (receipt['states'][arm] for arm in audit.ARMS)
    receipt['standard_bias'] = standard['layout.0.bias'][0]
    receipt['centered_bias'] = centered['layout.0.bias'][0]
    receipt['shared_sha256'] = audit.h.fingerprint({k: v for k, v in standard.items() if k != 'layout.0.bias'})[0]
    receipt['initial_sha256'] = {arm: audit.h.fingerprint(state)[0] for arm, state in receipt['states'].items()}
    for arm in audit.ARMS: report['reports'][arm]['initial_sha256'] = receipt['initial_sha256'][arm]


class CenteringAuditTests(unittest.TestCase):
    def check_receipt(self, report):
        result = audit.h.Audit()
        audit.verify_initialization(result, report, 'synthetic')
        return result

    def test_saved_initial_tensors_are_verified_without_mutation(self):
        report = initialization_fixture(); before = deepcopy(report)
        self.assertEqual(self.check_receipt(report).discrepancy_count, 0)
        self.assertEqual(report, before)
        self.assertEqual(audit.h.fingerprint(report['initialization']['states']['centered'])[1], 89)

    def test_even_coherently_rehashed_nonbias_change_is_rejected_exactly(self):
        report = initialization_fixture()
        report['initialization']['states']['centered']['lexical.0.weight'][0][0] += 1e-14
        reseal(report)
        result = self.check_receipt(report)
        self.assertGreater(result.discrepancy_count, 0)
        self.assertIn('synthetic/88 exact shared scalars', result.discrepancies)

    def test_wrong_formula_and_absent_intervention_are_rejected(self):
        for bias in (-.29999, .2):
            with self.subTest(bias=bias):
                report = initialization_fixture()
                report['initialization']['states']['centered']['layout.0.bias'][0] = bias
                reseal(report)
                self.assertGreater(self.check_receipt(report).discrepancy_count, 0)

    def test_forged_receipt_hash_bias_and_inventory_are_rejected(self):
        mutations = (
            lambda r: r['initialization'].__setitem__('shared_sha256', '0' * 64),
            lambda r: r['initialization'].__setitem__('centered_bias', -.2),
            lambda r: r['initialization'].__setitem__('changed_scalars', 2),
            lambda r: r['reports']['centered'].__setitem__('initial_sha256', '0' * 64),
        )
        for mutation in mutations:
            report = initialization_fixture(); mutation(report)
            self.assertGreater(self.check_receipt(report).discrepancy_count, 0)
        report = initialization_fixture()
        report['initialization']['states']['centered']['layout.0.weight'][0].append(0.)
        with self.assertRaisesRegex(ValueError, 'shape'): self.check_receipt(report)
        report = initialization_fixture(); del report['initialization']['states']['centered']
        with self.assertRaisesRegex(ValueError, 'inventory'): self.check_receipt(report)

    def gate_fixture(self):
        delta = {'regressions': [], 'mean_nll_change': -.1}
        comparison = {'native': {'centered': deepcopy(delta)},
            'retention': {'centered': {bank: deepcopy(delta) for bank in audit.BANKS if bank != 'fresh'}},
            'retention_pair': {bank: deepcopy(delta) for bank in audit.BANKS if bank != 'fresh'},
            'fresh_pair': deepcopy(delta)}
        return {'checks': {'probability': True}}, comparison, {'final_observed_train_nll': .01}

    def test_every_archived_and_paired_retention_bank_blocks(self):
        paths = [('native', 'centered'), ('fresh_pair',)]
        paths += [('retention', 'centered', bank) for bank in audit.BANKS if bank != 'fresh']
        paths += [('retention_pair', bank) for bank in audit.BANKS if bank != 'fresh']
        for path in paths:
            report, comparison, fit = self.gate_fixture(); node = comparison
            for key in path: node = node[key]
            node['regressions'] = [['synthetic', 0]]
            with self.subTest(path=path):
                self.assertFalse(all(audit.decision_checks(report, comparison, fit, .05).values()))

    def test_probability_training_and_undefined_comparisons_stay_failures(self):
        report, comparison, fit = self.gate_fixture()
        self.assertTrue(all(audit.decision_checks(report, comparison, fit, .05).values()))
        for value in (.01, None):
            comparison['fresh_pair']['mean_nll_change'] = value
            self.assertFalse(audit.decision_checks(report, comparison, fit, .05)['paired_mean_nll'])
        fit['final_observed_train_nll'] = .051
        self.assertFalse(audit.decision_checks(report, comparison, fit, .05)['observed_training_fit'])
        report['checks']['probability'] = False
        self.assertFalse(audit.decision_checks(report, comparison, fit, .05)['probability'])

    def test_retention_uses_original_archived_arm_and_canonical_points(self):
        root = Path('synthetic')
        self.assertEqual(audit.archived_path(root, 'nand', 7, 'saturation_retention'),
            root / 'results/saturation-v1/traces/trace-nand-7-unsaturated-fresh.json.xz')
        self.assertEqual(audit.archived_path(root, 'nor', 11, 'binding_retention'),
            root / 'results/binding-v1/traces/trace-nor-11-factor-fresh.json.xz')
        with self.assertRaises(ValueError): audit.archived_path(root, 'nand', 7, 'fresh')
        measured = {('x', 0, 'canonical'): {'correct': True}, ('x', 0, 'swapped'): {'correct': False}}
        self.assertEqual(audit.canonical(measured), {('x', 0): {'correct': True}})

    def test_cli_serializes_success_failure_and_never_overwrites(self):
        for passed in (True, False):
            report = {'decision': 'REVISE_CENTERING_HYPOTHESIS', 'audit_passed': passed,
                'check_count': 3, 'discrepancy_count': int(not passed)}
            with tempfile.TemporaryDirectory() as folder, patch.object(audit, 'audit_saved', return_value=report):
                path = Path(folder) / 'audit.json'; args = ['--repo', folder, '--output', str(path)]
                with redirect_stdout(StringIO()) as out: self.assertEqual(audit.main(args), int(not passed))
                self.assertEqual(json.loads(path.read_text()), report)
                self.assertEqual(json.loads(out.getvalue()), report)
                with self.assertRaises(FileExistsError): audit.main(args)

    def test_import_works_without_numerical_runtime_or_scientific_modules(self):
        code = ('import sys; import experiments.predictive_nucleus.audit_centering_saved; '
                'assert not any(m in sys.modules for m in ("torch", "numpy", '
                '"experiments.predictive_nucleus.centering_run", "experiments.predictive_nucleus.centering_scoring", '
                '"experiments.predictive_nucleus.saturation_run", "experiments.predictive_nucleus.binding_model", '
                '"experiments.predictive_nucleus.binding_scoring", "experiments.predictive_nucleus.bilingual_scoring"))')
        subprocess.run([sys.executable, '-S', '-c', code], check=True, timeout=10)


if __name__ == '__main__': unittest.main()
