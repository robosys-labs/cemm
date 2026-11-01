"""Corrupt synthetic receipts and boundaries; no research fits or bank evaluation."""
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

from experiments.predictive_nucleus import audit_coordinate_saved as audit


def fixture():
    def tensor(shape):
        return [tensor(shape[1:]) for _ in range(shape[0])] if shape else .125
    centered = {key: tensor(shape) for key, shape in audit.SHAPES.items()}
    centered['layout.0.weight'], centered['layout.0.bias'] = [[.25, -.5, .625]], [-.25]
    coordinates = {k: deepcopy(v) for k, v in centered.items() if k != 'layout.0.bias'}
    coordinates['layout.0.weight'] = [[-.125, .625, -.5]]
    report = {'reports': {arm: {} for arm in audit.ARMS}, 'initialization': {
        'states': dict(zip(audit.ARMS, (centered, coordinates), strict=True)),
        'parameters': dict(audit.PARAMETERS), 'unchanged_scalars': 85,
        'layout_masks': [[0., 1., 1.], [1., 0., 1.], [1., 1., 0.]],
        'layout_responses': {'centered': [-.125, .625, -.5], 'coordinates': [-.125, .625, -.5]}}}
    reseal(report)
    return report


def reseal(report):
    receipt = report['initialization']; states = receipt['states']
    receipt['shared_sha256'] = audit.h.fingerprint({k: v for k, v in states['centered'].items() if not k.startswith('layout.')})[0]
    receipt['initial_sha256'] = {arm: audit.h.fingerprint(state)[0] for arm, state in states.items()}
    for arm in audit.ARMS: report['reports'][arm]['initial_sha256'] = receipt['initial_sha256'][arm]


class CoordinateAuditTests(unittest.TestCase):
    def check_receipt(self, report):
        result = audit.h.Audit(); audit.verify_initialization(result, report, 'synthetic')
        return result

    def test_actual_states_pass_without_mutation_and_shapes_are_distinct(self):
        report = fixture(); before = deepcopy(report)
        self.assertEqual(self.check_receipt(report).discrepancy_count, 0)
        self.assertEqual(report, before)
        for arm in audit.ARMS:
            self.assertEqual(audit.state_inventory(report['initialization']['states'][arm], arm)[1], audit.PARAMETERS[arm])

    def test_rehashed_shared_parameter_or_response_change_still_fails(self):
        for key, mutate in (
            ('shared', lambda s: s['lexical.0.weight'][0].__setitem__(0, .125 + 1e-14)),
            ('layout', lambda s: s['layout.0.weight'][0].__setitem__(0, -.124)),
        ):
            report = fixture(); mutate(report['initialization']['states']['coordinates']); reseal(report)
            with self.subTest(key=key): self.assertGreater(self.check_receipt(report).discrepancy_count, 0)

    def test_extra_bias_wrong_shape_or_missing_arm_is_rejected(self):
        for mutate in (
            lambda r: r['initialization']['states']['coordinates'].__setitem__('layout.0.bias', [0.]),
            lambda r: r['initialization']['states']['coordinates']['layout.0.weight'][0].append(0.),
            lambda r: r['initialization']['states'].pop('centered'),
        ):
            report = fixture(); mutate(report)
            with self.assertRaisesRegex(ValueError, 'inventory|shape'): self.check_receipt(report)

    def test_forged_hash_geometry_count_and_response_receipts_fail(self):
        for mutate in (
            lambda r: r['initialization'].__setitem__('shared_sha256', '0' * 64),
            lambda r: r['initialization'].__setitem__('unchanged_scalars', 88),
            lambda r: r['initialization']['parameters'].__setitem__('coordinates', 89),
            lambda r: r['initialization']['layout_masks'][0].__setitem__(0, 1.),
            lambda r: r['initialization']['layout_responses']['centered'].__setitem__(1, .5),
            lambda r: r['reports']['coordinates'].__setitem__('initial_sha256', '0' * 64),
        ):
            report = fixture(); mutate(report)
            self.assertGreater(self.check_receipt(report).discrepancy_count, 0)

    def test_old_and_new_retention_and_probability_failures_all_block(self):
        delta = {'regressions': [], 'mean_nll_change': -.1}
        good = {'fresh_pair': deepcopy(delta), 'native': {'coordinates': deepcopy(delta)},
            'retention': {'coordinates': {bank: deepcopy(delta) for bank in audit.BANKS if bank != 'fresh'}},
            'retention_pair': {bank: deepcopy(delta) for bank in audit.BANKS if bank != 'fresh'}}
        report, fit = {'checks': {'cell_nll': True}}, {'final_observed_train_nll': .01}
        paths = [('fresh_pair',), ('native', 'coordinates')]
        paths += [('retention', 'coordinates', bank) for bank in audit.BANKS if bank != 'fresh']
        paths += [('retention_pair', bank) for bank in audit.BANKS if bank != 'fresh']
        self.assertTrue(all(audit.decision_checks(report, good, fit, .05).values()))
        for path in paths:
            comparison = deepcopy(good); node = comparison
            for key in path: node = node[key]
            node['regressions'] = [['synthetic', 0]]
            with self.subTest(path=path): self.assertFalse(all(audit.decision_checks(report, comparison, fit, .05).values()))
        for value in (.001, None):
            comparison = deepcopy(good); comparison['fresh_pair']['mean_nll_change'] = value
            self.assertFalse(audit.decision_checks(report, comparison, fit, .05)['paired_mean_nll'])
        self.assertFalse(audit.decision_checks(report, good, {'final_observed_train_nll': .051}, .05)['observed_training_fit'])
        self.assertFalse(audit.decision_checks({'checks': {'cell_nll': False}}, good, fit, .05)['cell_nll'])

    def test_retention_reference_and_variable_inventory_denominators(self):
        root = Path('synthetic')
        self.assertEqual(audit.archived_path(root, 'nand', 11, 'centering_retention'),
            root / 'results/centering-v1/traces/trace-nand-11-centered-fresh.json.xz')
        self.assertEqual(audit.archived_path(root, 'nor', 7, 'saturation_retention'),
            root / 'results/saturation-v1/traces/trace-nor-7-unsaturated-fresh.json.xz')
        with self.assertRaises(ValueError): audit.archived_path(root, 'nand', 7, 'fresh')
        inputs = {('nand', 'fresh'): {'episodes': [{'utterances': [0] * 4}, {'utterances': [0] * 5}]},
                  ('nor', 'fresh'): {'episodes': [{'utterances': [0] * 3}]},
                  ('nand', 'centering_retention'): {'episodes': [{'utterances': [0] * 2}]}}
        self.assertEqual(audit.planned_counts(inputs, [7, 11]), ({'fresh': 72, 'centering_retention': 8}, 24))
        measured = {('x', 0, 'canonical'): {'correct': True}, ('x', 0, 'swapped'): {'correct': False}}
        self.assertEqual(audit.canonical(measured), {('x', 0): {'correct': True}})

    def test_cli_serializes_and_refuses_evidence_overwrite(self):
        for passed in (True, False):
            report = {'decision': 'REVISE_COORDINATE_HYPOTHESIS', 'audit_passed': passed,
                'check_count': 3, 'discrepancy_count': int(not passed)}
            with tempfile.TemporaryDirectory() as folder, patch.object(audit, 'audit_saved', return_value=report):
                path = Path(folder) / 'audit.json'; args = ['--repo', folder, '--output', str(path)]
                with redirect_stdout(StringIO()) as out: self.assertEqual(audit.main(args), int(not passed))
                self.assertEqual(json.loads(path.read_text()), report)
                self.assertEqual(json.loads(out.getvalue()), report)
                with self.assertRaises(FileExistsError): audit.main(args)

    def test_import_requires_only_stdlib_and_saved_record_helpers(self):
        code = ('import sys; import experiments.predictive_nucleus.audit_coordinate_saved; '
                'assert not any(m in sys.modules for m in ("torch", "numpy", '
                '"experiments.predictive_nucleus.coordinate_run", "experiments.predictive_nucleus.coordinate_scoring", '
                '"experiments.predictive_nucleus.centering_run", "experiments.predictive_nucleus.binding_model", '
                '"experiments.predictive_nucleus.binding_scoring", "experiments.predictive_nucleus.bilingual_scoring"))')
        subprocess.run([sys.executable, '-S', '-c', code], check=True, timeout=10)


if __name__ == '__main__': unittest.main()
