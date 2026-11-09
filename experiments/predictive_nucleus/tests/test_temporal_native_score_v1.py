"""Independent small examples for saved-score mathematics and answer timing."""
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from experiments.predictive_nucleus.temporal_native_score_v1 import digest, metrics, paired, policy, validate_decisions, validate_view, vector, verify_manifest


def point(y):
    return [int(i == y) for i in range(8)]


class TemporalNativeScoreTests(unittest.TestCase):
    def test_roundoff_is_preserved_and_raw_manifest_binds_bytes_and_data(self):
        p = [1 + 1e-12] + [0.] * 7
        self.assertIs(vector(p), p)
        for invalid in ([1 + 1e-8] + [0.] * 7, [1., -1e-15] + [0.] * 6):
            with self.assertRaises(ValueError): vector(invalid)
        with TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'forecast.json').write_text('{}')
            manifest = {'data_sha256': 'prepared', 'artifacts': {'forecast.json': {'sha256': digest(root / 'forecast.json')}}}
            (root / 'manifest.json').write_text(json.dumps(manifest))
            self.assertEqual(verify_manifest(root, 'prepared'), manifest)
            with self.assertRaises(ValueError): verify_manifest(root, 'other-prepared')
            (root / 'forecast.json').write_text('{"tampered":true}')
            with self.assertRaises(ValueError): verify_manifest(root, 'prepared')

    def test_conditional_regret_does_not_treat_ambiguous_truth_as_certain(self):
        p = [.5, .5] + [0.] * 6
        row = {'id': 'a', 'target_y': 1, 'distributions': {'both': p}}
        result, _ = metrics([p], [row], 'both')
        self.assertEqual(result['brier'], .5)
        self.assertEqual(result['excess_brier'], 0)
        self.assertEqual(result['conditional_accuracy_optimum'], .5)
        self.assertEqual(result['accuracy'], 0)

    def test_nll_is_not_capped_and_confident_error_denominator_is_all_targets(self):
        rows = [{'id': str(y), 'target_y': y, 'distributions': {'both': point(y)}} for y in (0, 1)]
        result, _ = metrics([point(0), point(0)], rows, 'both')
        self.assertEqual(result['nll'], 'Infinity')
        self.assertEqual(result['confident_error_fraction'], .5)
        self.assertEqual(result['zero_probability_cases'], ['1'])
        with self.assertRaises(ValueError): vector([float('nan')] + [0.] * 7)
        adverse = paired([('a', 1, 1e-20, float('inf'))], [('a', 1, 0., 1.)])
        self.assertEqual(adverse['brier_regressions'], [{'id': 'a', 'delta': 1e-20}])
        self.assertEqual(adverse['nll_regressions'], [{'id': 'a', 'delta': 'Infinity'}])

    def test_query_decision_precedes_actual_answer_and_reports_realized_harm(self):
        before = [.6, .4] + [0.] * 6
        branches = [point(y) for y in range(8)]
        view = {'probe': [[.5, .5] + [0.] * 6], 'before': [before], 'branches': [branches],
                'after_second': [point(1)], 'protected': [point(0)]}
        rows = [{'id': 'a', 'target_y': 0, 'second_y': 1}]
        validate_view(view, rows)
        decisions = {'value': [.4], 'asks': [[True, False, False]]}
        validate_decisions(decisions, view)
        with self.assertRaises(ValueError): validate_decisions({'value': [.3], 'asks': decisions['asks']}, view)
        with self.assertRaises(ValueError): validate_decisions({'value': [.4], 'asks': [[False, False, False]]}, view)
        cheap, _ = policy(view, rows, .05)
        self.assertEqual(cheap['paid_questions'], 1)
        self.assertEqual(cheap['correct'], 0)
        self.assertAlmostEqual(cheap['net_gain_from_query'], -1.05)
        self.assertAlmostEqual(cheap['coherence_linf_max'], .1)
        changed, _ = policy(view, [{'id': 'a', 'target_y': 1, 'second_y': 0}], .05)
        self.assertEqual(changed['paid_questions'], cheap['paid_questions'])
        for fee in (1., None, .4):
            result, _ = policy(view, rows, fee)
            self.assertEqual(result['paid_questions'], 0)
        view['after_second'] = [point(0)]
        with self.assertRaises(ValueError): validate_view(view, rows)


if __name__ == '__main__':
    unittest.main()
