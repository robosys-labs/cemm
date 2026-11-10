"""Synthetic checks of denominators, conditional scoring and question timing."""
import copy
from hashlib import sha256
import json
import lzma
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np

from experiments.predictive_nucleus import selective_memory_score_v1 as scorer

from experiments.predictive_nucleus.selective_memory_score_v1 import (
    adverse, canonical, digest, gates, paired, point_scores, policy_points,
    pool, probabilities, summarize, validate_optional, verify_manifest,
)


def point(y):
    return np.eye(8)[y]


def optional_example():
    branches = np.broadcast_to(np.eye(8), (1, 2, 8, 8)).copy()
    answer = np.array([[1, 0]])
    raw = {'optional_probe': np.array([[[.5, .5] + [0.] * 6] * 2]),
           'optional_before': np.array([[[.6, .4] + [0.] * 6] * 2]),
           'optional_branches': branches, 'optional_after': point(answer),
           'optional_value': np.full((1, 2), .4),
           'optional_asks': np.array([[[True, False, False]] * 2])}
    q = {key: np.full((1, 2, 8), 1 / 8) for key in ('before', 'after')}
    return raw, answer, q


def passing_cell():
    return {'stages': {'final': {'accuracy': .98, 'oracle_realized_accuracy': 1.,
            'expected_attainable_accuracy': 1., 'excess_brier': .02,
            'confident_error_fraction': .01, 'brier': 0.}, 'cleared_final': {'brier': .001}},
            'retention': {'count': 1, 'accuracy': .95},
            'policies': {view: {'cheap': {'mean_net_reward': .8}} for view in ('retained', 'cleared')}}


class SelectiveMemoryScoreTests(unittest.TestCase):
    def test_complete_synthetic_score_preserves_gate_counts_and_artifact_binding(self):
        # Eight synthetic rows cover every law/mask. No simulator or study data.
        rows = []
        for law in ('nand', 'nor'):
            for mask in range(4):
                rows.append({'id': f'{law}-{mask}', 'law': law, 'target_change_mask': mask,
                    'persistent_change_mask': mask, 'causes': ['report_only'] * 2,
                    'target_scope': ['local', 'sibling'], 'target_y': [0, 0], 'probe_y': [0] * 4,
                    'distributions': {stage: point([0, 0]).tolist() for stage in scorer.STAGES},
                    'next_probe': point([0] * 4).tolist(),
                    **{view: {'before': point([0, 0]).tolist(), 'after': point([0, 0]).tolist(),
                              'answer': [0, 0]} for view in ('optional', 'cleared_optional')}})
        arrays = {stage: point(np.zeros((8, 2), int)) for stage in scorer.STAGES}
        arrays.update(next_probe=point(np.zeros((8, 4), int)), optional_y=np.zeros((8, 2), int))
        for prefix in ('optional_', 'cleared_optional_'):
            arrays.update({prefix + key: point(np.zeros((8, 2), int)) for key in ('probe', 'before', 'after')})
            arrays[prefix + 'branches'] = point(np.zeros((8, 2, 8), int))
            arrays[prefix + 'value'] = np.zeros((8, 2))
            arrays[prefix + 'asks'] = np.zeros((8, 2, 3), bool)
        inventory = lambda directory: {p.name: {'sha256': digest(p), 'bytes': p.stat().st_size}
                                       for p in directory.iterdir() if p.name != 'manifest.json'}
        with TemporaryDirectory() as temporary, patch.multiple(scorer, RECORDS=8, SEEDS=(7,)):
            root = Path(temporary)
            prepared, raw, output = (root / name for name in ('prepared', 'raw', 'output'))
            prepared.mkdir(); raw.mkdir()
            (prepared / 'oracle.json.xz').write_bytes(lzma.compress(canonical({'rows': rows})))
            (prepared / 'manifest.json').write_bytes(canonical({'artifacts': inventory(prepared)}))
            data_sha = digest(prepared / 'manifest.json')
            fits = {'data_sha256': data_sha, 'source_sha256': {}, 'fits': 3}
            (raw / 'fit-manifest.json').write_bytes(canonical(fits))
            for arm in scorer.ARMS:
                np.savez_compressed(raw / f'raw-{arm}-7.npz', **arrays)
            ids = [row['id'] for row in rows]
            manifest = {'data_sha256': data_sha, 'source_sha256': {}, 'records': 8,
                        'fit_sha256': digest(raw / 'fit-manifest.json'), 'ids': ids,
                        'id_order_sha256': sha256(canonical(ids)).hexdigest(),
                        'arms': list(scorer.ARMS), 'seeds': [7], 'artifacts': inventory(raw)}
            (raw / 'manifest.json').write_bytes(canonical(manifest))
            result = scorer.score(prepared, raw, output)
            self.assertEqual(result['decision'], 'REVISE_SELECTIVE_MEMORY_V1')
            self.assertEqual(result['total_checks'], 62)  # Eight cells minus two N/A retention gates.
            self.assertEqual(result['passed_checks'], 54)  # No positive retained-evidence Brier gain.
            self.assertEqual(result['pooled']['selective']['final']['count'], 16)
            self.assertEqual(result['cells']['nand/7/3']['arms']['selective']['retention']['count'], 0)
            self.assertEqual(scorer.verify_manifest(output)['data_sha256'], data_sha)
            self.assertTrue(scorer.load(output / 'adverse.json.xz')['records'])

    def test_oracle_map_stays_observational_inside_a_hidden_stratum(self):
        # Public observations leave a tie. This hidden stratum happens to contain
        # only endpoint 1; replacing q by its stratum truth would change the gate.
        q = np.array([[[.5, .5] + [0.] * 6] * 2])
        y = np.ones((1, 2), dtype=int)
        points = point_scores(q, y, q)
        result = summarize(points, [True])
        self.assertEqual(result['oracle_realized_accuracy'], 0.)
        self.assertEqual(result['expected_attainable_accuracy'], .5)
        self.assertEqual(result['accuracy'], 0.)
        self.assertEqual(result['excess_brier'], 0.)
        self.assertEqual(result['brier'], .5)
        candidate = passing_cell()
        candidate['stages']['final'].update(result)
        self.assertTrue(gates(candidate, passing_cell())['attainable_accuracy'])

    def test_confident_error_uses_all_targets_and_nll_is_uncapped(self):
        p = np.full((2, 2, 8), .125)
        p[0, 0] = point(0)
        y = np.array([[1, 2], [3, 4]])
        points = point_scores(p, y, np.full_like(p, .125))
        result = summarize(points, [True, True])
        self.assertEqual(result['count'], 4)
        self.assertEqual(result['confident_error_fraction'], .25)
        self.assertEqual(result['confident_error_rate'], 1.)
        self.assertEqual(result['nll'], 'Infinity')
        self.assertEqual(result['zero_probability_count'], 1)
        ids = np.array([['a/word:0', 'a/word:1'], ['b/word:0', 'b/word:1']])
        self.assertEqual(adverse(points, ids)['zero_probability'], ['a/word:0'])
        tiny = np.full((1, 1, 8), (1 - 1e-200) / 7)
        tiny[..., 0] = 1e-200
        observed = point_scores(tiny, np.zeros((1, 1), int))
        self.assertGreater(summarize(observed, [True])['nll'], 400)

    def test_retention_denominator_selects_unchanged_targets_and_na_is_explicit(self):
        y = np.array([[0, 1], [2, 3]])
        points = point_scores(point(y), y, point(y))
        masks = np.array([1, 3])  # word 1 unchanged in first row; neither in second.
        retained = (masks[:, None] & (1 << np.arange(2))) == 0
        self.assertEqual(summarize(points, retained)['count'], 1)
        missing = summarize(points, retained & np.array([[False], [True]]))
        self.assertEqual(missing, {'count': 0, 'accuracy': None, 'status': 'N/A'})
        candidate = passing_cell()
        candidate['retention'] = missing
        self.assertIsNone(gates(candidate, passing_cell())['protected_retention'])

    def test_frozen_thresholds_are_not_relaxed_for_no_evidence_benefit(self):
        candidate, flat = passing_cell(), passing_cell()
        self.assertTrue(all(gates(candidate, flat).values()))
        candidate['stages']['cleared_final']['brier'] = 1e-4
        self.assertFalse(gates(candidate, flat)['retained_brier_gain'])
        candidate['stages']['final']['excess_brier'] = np.nextafter(.02, 1.)
        self.assertFalse(gates(candidate, flat)['excess_brier'])
        candidate['retention']['accuracy'] = np.nextafter(.95, 0.)
        self.assertFalse(gates(candidate, flat)['protected_retention'])
        candidate['stages']['final']['confident_error_fraction'] = np.nextafter(.01, 1.)
        self.assertFalse(gates(candidate, flat)['confident_errors'])
        candidate['stages']['final']['accuracy'] = .979
        self.assertFalse(gates(candidate, flat)['attainable_accuracy'])

    def test_probability_validation_preserves_roundoff_and_rejects_invalid_values(self):
        p = np.array([1 + 1e-12] + [0.] * 7)
        self.assertIs(probabilities(p), p)
        for invalid in ([1 + 1e-8] + [0.] * 7, [1., -1e-15] + [0.] * 6,
                        [float('nan')] + [0.] * 7, [float('inf')] + [0.] * 7, [.1] * 8):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                probabilities(invalid)
        with self.assertRaises(ValueError):
            point_scores(point([[0]]), np.array([[1]]), point([[0]]))

    def test_optional_choices_precede_answer_and_actual_branch_must_match(self):
        raw, answer, q = optional_example()
        validate_optional(raw, answer)
        y = np.zeros((1, 2), dtype=int)
        cheap = policy_points(raw, y, q, 0)
        result = summarize(cheap, [True])
        self.assertEqual(result['paid_questions'], 2)
        self.assertEqual(result['correct'], 1)
        self.assertAlmostEqual(result['net_gain_from_query'], -1.1)
        self.assertAlmostEqual(result['coherence_linf_max'], .1)
        # Changing unseen truth affects realized reward, never the saved asks.
        changed_truth = policy_points(raw, 1 - y, q, 0)
        np.testing.assert_array_equal(changed_truth['paid'], cheap['paid'])
        for fee_index in (1, 2):
            self.assertEqual(summarize(policy_points(raw, y, q, fee_index), [True])['paid_questions'], 0)
        malformed = copy.deepcopy(raw)
        malformed['optional_after'][0, 0] = point(0)
        with self.assertRaisesRegex(ValueError, 'answer branch'):
            validate_optional(malformed, answer)
        malformed = copy.deepcopy(raw)
        malformed['optional_value'][0, 0] = .3
        with self.assertRaisesRegex(ValueError, 'pre-answer value'):
            validate_optional(malformed, answer)
        malformed = copy.deepcopy(raw)
        malformed['optional_asks'][0, 0, 0] = False
        with self.assertRaisesRegex(ValueError, 'pre-answer decisions'):
            validate_optional(malformed, answer)

    def test_adverse_deltas_include_tiny_and_infinite_changes_without_inf_minus_inf(self):
        ids = np.array([['a', 'b']])
        candidate = {'correct': np.array([[False, True]]), 'brier': np.array([[1e-20, 0.]]),
                     'nll': np.array([[np.inf, np.inf]])}
        reference = {'correct': np.array([[True, False]]), 'brier': np.zeros((1, 2)),
                     'nll': np.array([[1., np.inf]])}
        result = paired(candidate, reference, ids)
        self.assertEqual(result['exact_regressions'], ['a'])
        self.assertEqual(result['exact_repairs'], ['b'])
        self.assertEqual(result['brier_regressions'], [{'id': 'a', 'delta': 1e-20}])
        self.assertEqual(result['nll_regressions'], [{'id': 'a', 'delta': 'Infinity'}])

    def test_manifest_binds_exact_artifact_bytes_and_pool_preserves_denominators(self):
        with TemporaryDirectory() as temporary:
            directory = Path(temporary)
            file = directory / 'bank.json'
            file.write_bytes(b'{}')
            manifest = {'data_sha256': 'expected', 'artifacts': {
                file.name: {'sha256': digest(file), 'bytes': 2}}}
            (directory / 'manifest.json').write_bytes(canonical(manifest))
            self.assertEqual(verify_manifest(directory, 'expected'), manifest)
            with self.assertRaises(ValueError):
                verify_manifest(directory, 'wrong')
            file.write_bytes(b'{ }')
            with self.assertRaises(ValueError):
                verify_manifest(directory, 'expected')
        p = np.full((2, 2, 8), .125)
        y = np.array([[0, 1], [1, 1]])
        scored = point_scores(p, y)
        combined = pool([summarize(scored, [True, False]), summarize(scored, [False, True])])
        self.assertEqual(combined['count'], 4)
        self.assertEqual(combined['correct'], 1)
        self.assertEqual(combined['accuracy'], .25)
        json.dumps(combined, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
