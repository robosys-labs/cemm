"""Synthetic gate boundaries and saved-record identity regressions."""
import lzma
import math
from pathlib import Path
import tempfile
import unittest

from experiments.predictive_nucleus import prefix_protection_score_v1 as scorer


def metric(correct=2, brier=.2):
    return {'count': 2, 'correct': correct, 'accuracy': correct / 2, 'brier': brier, 'nll': .1}


def passing_cell():
    cell = {field: {stage: {'baseline': metric(), 'candidate': metric()}
                   for stage in scorer.STAGES} for field in scorer.FIELDS}
    for stage in scorer.STAGES[1:]:
        cell['protected'][stage]['candidate']['brier'] = .1
    return cell


class PrefixProtectionScoreTests(unittest.TestCase):
    def test_each_law_cell_is_required_even_when_other_cells_improve(self):
        cells = {}
        for law in scorer.LAWS:
            for seed in scorer.SEEDS:
                cell = passing_cell()
                cell['target']['second']['baseline'] = metric(correct=1)
                cells[f'{law}/{seed}'] = scorer.cell_gates(cell)
        self.assertEqual(scorer.decide(cells)['passed_checks'], 70)
        failing = passing_cell()
        failing['target']['second']['candidate'] = metric(correct=1)
        cells['nand/7'] = scorer.cell_gates(failing)
        self.assertGreater(sum(c['final_target']['candidate']['correct'] -
                               c['final_target']['baseline']['correct'] for c in cells.values()), 0)
        decision = scorer.decide(cells)
        self.assertEqual(decision['passed_checks'], 69)
        self.assertEqual(decision['decision'], 'REVISE_PREFIX_OBJECTIVE')
        del cells['nand/7']
        with self.assertRaisesRegex(ValueError, 'ten native'):
            scorer.decide(cells)

    def test_after_teaching_failures_are_two_independent_gates(self):
        cell = passing_cell()
        cell['protected']['teaching']['candidate'] = metric(correct=1, brier=.3)
        gates = scorer.cell_gates(cell)['gates']
        self.assertFalse(gates['teaching_protected_accuracy'])
        self.assertFalse(gates['teaching_protected_brier'])
        self.assertEqual(sum(gates.values()), 5)

    def test_strict_improvement_and_allowed_roundoff_boundaries(self):
        cell = passing_cell()
        for stage in scorer.STAGES[1:]:
            cell['protected'][stage]['baseline']['brier'] = 1e-4
            cell['protected'][stage]['candidate']['brier'] = 0.
        gates = scorer.cell_gates(cell)['gates']
        self.assertFalse(gates['final_protected_brier_gain'])
        self.assertFalse(gates['prefix_protected_brier_gain'])
        for stage in scorer.STAGES[1:]:
            cell['protected'][stage]['baseline']['brier'] = math.nextafter(1e-4, math.inf)
        self.assertTrue(scorer.cell_gates(cell)['gates']['final_protected_brier_gain'])
        for field, stage, gate in (('target', 'second', 'final_target_brier'),
                                    ('protected', 'teaching', 'teaching_protected_brier')):
            cell[field][stage]['baseline']['brier'] = 0.
            cell[field][stage]['candidate']['brier'] = 1e-12
            self.assertTrue(scorer.cell_gates(cell)['gates'][gate])
            cell[field][stage]['candidate']['brier'] = math.nextafter(1e-12, math.inf)
            self.assertFalse(scorer.cell_gates(cell)['gates'][gate])

    def test_zero_probability_stays_infinite_and_adverse_ids_are_exact(self):
        old = scorer.point_scores([[.8, .2, 0, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0, 0, 0]], [0, 0])
        new = scorer.point_scores([[0, 1, 0, 0, 0, 0, 0, 0], [.8, .2, 0, 0, 0, 0, 0, 0]], [0, 0])
        result = scorer.compare_points(old, new, ['lost', 'fixed'], [0, 1])
        self.assertEqual(result['regressions'], ['lost'])
        self.assertEqual(result['repairs'], ['fixed'])
        self.assertEqual(result['brier_worse'], ['lost'])
        self.assertEqual(result['nll_worse'], ['lost'])
        self.assertEqual(result['baseline']['nll'], 'Infinity')
        self.assertEqual(result['candidate']['nll'], 'Infinity')
        self.assertIsNone(result['change']['nll'])
        self.assertFalse(result['change']['nll_difference_defined'])
        scorer.encoded(result)  # Strict JSON must not contain NaN or numeric Infinity.
        repaired = scorer.compare_points(old, new, ['lost', 'fixed'], [1])
        self.assertEqual(repaired['change']['nll'], '-Infinity')

    def test_bad_probability_and_wrong_case_order_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'distribution'):
            scorer.point_scores([[float('nan')] * 8], [0])
        with self.assertRaisesRegex(ValueError, 'distribution'):
            scorer.point_scores([[.2] * 8], [0])
        raw = {'version': scorer.VERSION, 'arm': 'native', 'seed': 7, 'ids': ['second', 'first'],
               'predictions': {s: {f: [[1, 0, 0, 0, 0, 0, 0, 0]] * 2 for f in scorer.FIELDS} for s in scorer.STAGES}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'raw.json.xz'
            path.write_bytes(lzma.compress(scorer.encoded(raw)))
            with self.assertRaisesRegex(ValueError, 'case IDs'):
                scorer.load_raw(path, scorer.VERSION, 'native', 7, ['first', 'second'],
                                {'target': [0, 0], 'protected': [0, 0]}, 'a' * 64)

    def test_manifest_rejects_changed_bytes_and_input_binding(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifacts = {}
            for seed in scorer.SEEDS:
                for arm in ('native', 'flat'):
                    name = f'raw-{arm}-{seed}.json.xz'
                    (root / name).write_bytes(b'fixture')
                    artifacts[name] = {'sha256': scorer.digest(root / name), 'bytes': 7}
            manifest = {'version': scorer.VERSION, 'input_sha256': 'a' * 64, 'source_commit': 'b' * 40,
                        'fit_manifest_sha256': 'c' * 64, 'artifacts': artifacts}
            (root / 'manifest.json').write_bytes(scorer.encoded(manifest))
            scorer.load_manifest(root, scorer.VERSION, 'a' * 64)
            with self.assertRaisesRegex(ValueError, 'input binding'):
                scorer.load_manifest(root, scorer.VERSION, 'd' * 64)
            (root / 'raw-native-7.json.xz').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'hash or size'):
                scorer.load_manifest(root, scorer.VERSION, 'a' * 64)

    def test_candidate_requires_matching_checkpoint_weights_and_input(self):
        expected = {'checkpoint_sha256': 'b' * 64, 'weights_sha256': 'c' * 64}
        raw = {'version': scorer.VERSION, 'arm': 'native', 'seed': 7, 'ids': ['one'],
               'input_sha256': 'a' * 64, **expected,
               'predictions': {s: {f: [[1, 0, 0, 0, 0, 0, 0, 0]] for f in scorer.FIELDS} for s in scorer.STAGES}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'raw.json.xz'
            def load():
                path.write_bytes(lzma.compress(scorer.encoded(raw)))
                return scorer.load_raw(path, scorer.VERSION, 'native', 7, ['one'],
                                       {'target': [0], 'protected': [0]}, 'a' * 64, expected)
            load()
            for key in expected:
                raw[key] = 'd' * 64
                with self.assertRaisesRegex(ValueError, 'checkpoint or weight'):
                    load()
                raw[key] = expected[key]
            del raw['input_sha256']
            with self.assertRaisesRegex(ValueError, 'input binding'):
                load()


if __name__ == '__main__':
    unittest.main()
