"""Synthetic numerical and reporting boundaries; no research data or execution."""
from copy import deepcopy
import json
import math
import subprocess
import sys
import unittest

from experiments.predictive_nucleus.set_acquisition_retention_v2 import retention


LIMITS = {'max_retention_logp_change': 1e-10, 'max_retention_order_logp_change': 1e-10}


def fixture(count=1):
    inputs = {'version': 'bilingual-input-v1', 'episodes': [{'id': 'synthetic',
        'entities': ['a', 'b', 'c'], 'anchor': [0, 0, 0],
        'context': [{'action': [1, 0, -1, 0], 'reading': [0, 0, 0]}],
        'utterances': [{'text': 'a touches b', 'reading': [0, 0, 0]} for _ in range(count)]}]}
    rows = [{'id': 'synthetic', 'step': t, 'view': 'canonical',
        'logp': [math.log(.65)] + [math.log(.05)] * 7,
        'order_logp': [math.log(.8), math.log(.2)]} for t in range(count)]
    return inputs, rows


class SetAcquisitionRetentionV2Tests(unittest.TestCase):
    def test_identical_probabilities_pass_without_mutating_evidence(self):
        inputs, rows = fixture(); before = deepcopy((inputs, rows, LIMITS))
        report = retention(inputs, rows, rows, LIMITS)
        self.assertTrue(report['passed']); self.assertTrue(all(report['checks'].values()))
        self.assertEqual((report['max_logp_change'], report['max_order_logp_change']), (0., 0.))
        self.assertEqual((report['exact_world_vectors'], report['exact_order_vectors']), (1, 1))
        self.assertEqual(report['nll_equal'], 1); self.assertEqual(report['mean_nll_change'], 0.)
        self.assertEqual((inputs, rows, LIMITS), before)

    def test_ulp_drift_is_reported_without_becoming_behavioral_failure(self):
        inputs, old = fixture(); now = deepcopy(old)
        for field in ('logp', 'order_logp'):
            now[0][field][0] = math.nextafter(now[0][field][0], -math.inf)
        report = retention(inputs, now, old, LIMITS)
        self.assertTrue(report['passed']); self.assertEqual(report['nll_worse'], 1)
        self.assertEqual((report['exact_world_vectors'], report['exact_order_vectors']), (0, 0))
        self.assertGreater(report['max_logp_change'], 0.)
        self.assertGreater(report['max_order_logp_change'], 0.)
        self.assertGreater(report['points'][0]['nll_change'], 0.)

    def test_each_absolute_bound_is_inclusive_and_has_no_relative_term(self):
        inputs, old = fixture(); now = deepcopy(old)
        now[0]['order_logp'] = [math.log(.8 - 1e-8), math.log(.2 + 1e-8)]
        delta = max(abs(a - b) for a, b in zip(now[0]['order_logp'], old[0]['order_logp'], strict=True))
        exact = {**LIMITS, 'max_retention_order_logp_change': delta}
        self.assertTrue(retention(inputs, now, old, exact)['passed'])
        below = {**exact, 'max_retention_order_logp_change': math.nextafter(delta, 0.)}
        report = retention(inputs, now, old, below)
        self.assertFalse(report['passed']); self.assertFalse(report['checks']['order_logp_retained'])
        self.assertTrue(report['checks']['world_logp_retained'])
        now = deepcopy(old); now[0]['logp'] = [math.log(.65 - 1e-8), math.log(.05 + 1e-8)] + [math.log(.05)] * 6
        report = retention(inputs, now, old, LIMITS)
        self.assertFalse(report['checks']['world_logp_retained'])
        self.assertTrue(report['checks']['order_logp_retained'])
        self.assertTrue(report['checks']['world_map_retained'])

    def test_order_near_tie_flip_fails_despite_passing_numerical_bound(self):
        inputs, old = fixture(); old[0]['order_logp'] = [math.log(.5)] * 2
        now = deepcopy(old)
        now[0]['order_logp'] = [math.log(.5 - 1e-12), math.log(.5 + 1e-12)]
        report = retention(inputs, now, old, LIMITS)
        self.assertTrue(report['checks']['order_logp_retained'])
        self.assertFalse(report['checks']['order_map_retained']); self.assertFalse(report['passed'])
        self.assertEqual(report['order_map_changes'], [['synthetic', 0]])

    def test_world_near_tie_flip_fails_despite_passing_numerical_bound(self):
        inputs, old = fixture(); old[0]['logp'] = [math.log(.35)] * 2 + [math.log(.05)] * 6
        now = deepcopy(old)
        now[0]['logp'][:2] = [math.log(.35 - 1e-12), math.log(.35 + 1e-12)]
        report = retention(inputs, now, old, LIMITS)
        self.assertTrue(report['checks']['world_logp_retained'])
        self.assertFalse(report['checks']['world_map_retained'])
        self.assertFalse(report['checks']['no_exact_regressions']); self.assertFalse(report['passed'])
        self.assertEqual(report['regressions'], [['synthetic', 0]])

    def test_changed_world_map_fails_even_when_both_predictions_were_wrong(self):
        inputs, old = fixture(); old[0]['logp'][0], old[0]['logp'][1] = old[0]['logp'][1], old[0]['logp'][0]
        now = deepcopy(old); now[0]['logp'][1], now[0]['logp'][2] = now[0]['logp'][2], now[0]['logp'][1]
        report = retention(inputs, now, old, {k: 100. for k in LIMITS})
        self.assertTrue(report['checks']['no_exact_regressions'])
        self.assertFalse(report['checks']['world_map_retained']); self.assertFalse(report['passed'])

    def test_early_scientific_failure_preserves_later_improvements_and_every_point(self):
        inputs, old = fixture(3); now = deepcopy(old)
        now[0]['order_logp'].reverse()
        now[1]['logp'] = [math.log(.64), math.log(.06)] + [math.log(.05)] * 6
        now[2]['logp'] = [math.log(.66), math.log(.04)] + [math.log(.05)] * 6
        report = retention(inputs, now[::-1], old, LIMITS)
        self.assertFalse(report['passed']); self.assertEqual(report['planned'], 3)
        self.assertEqual([p['step'] for p in report['points']], [0, 1, 2])
        self.assertEqual((report['nll_worse'], report['nll_better'], report['nll_equal']), (1, 1, 1))
        self.assertEqual(report['correct'], 3)
        self.assertGreater(report['points'][1]['nll_change'], 0.)
        self.assertLess(report['points'][2]['nll_change'], 0.)

    def test_equal_zero_probability_entries_have_zero_distance(self):
        inputs, rows = fixture(); rows[0]['logp'] = [0.] + ['negative_infinity'] * 7
        rows[0]['order_logp'] = [0., 'negative_infinity']
        report = retention(inputs, rows, rows, LIMITS)
        self.assertTrue(report['passed'])
        self.assertEqual((report['max_logp_change'], report['max_order_logp_change']), (0., 0.))
        self.assertEqual(report['points'][0]['total_variation'], 0.)
        json.dumps(report, allow_nan=False)

    def test_probability_support_change_fails_without_nan_or_exception(self):
        inputs, old = fixture(); old[0]['logp'] = [0.] + ['negative_infinity'] * 7
        old[0]['order_logp'] = [0., 'negative_infinity']; now = deepcopy(old)
        now[0]['logp'] = [math.log(.999), math.log(.001)] + ['negative_infinity'] * 6
        now[0]['order_logp'] = [math.log(.999), math.log(.001)]
        report = retention(inputs, now, old, LIMITS)
        self.assertFalse(report['passed'])
        self.assertEqual(report['max_logp_change'], 'positive_infinity')
        self.assertEqual(report['max_order_logp_change'], 'positive_infinity')
        self.assertTrue(report['checks']['world_map_retained'])
        json.dumps(report, allow_nan=False)

    def test_infinite_nll_deltas_and_opposing_infinities_remain_defined_reports(self):
        inputs, old = fixture(3); now = deepcopy(old)
        zero = ['negative_infinity', 0.] + ['negative_infinity'] * 6
        old[0]['logp'] = zero.copy(); now[0]['logp'] = zero.copy()
        now[1]['logp'] = zero.copy(); old[2]['logp'] = zero.copy()
        report = retention(inputs, now, old, LIMITS)
        self.assertEqual((report['nll_undefined'], report['nll_worse'], report['nll_better']), (1, 1, 1))
        self.assertEqual([p['nll_change'] for p in report['points']],
                         [None, 'positive_infinity', 'negative_infinity'])
        self.assertIsNone(report['mean_nll_change'])
        self.assertEqual((report['mean_nll'], report['archived_mean_nll']),
                         ('positive_infinity', 'positive_infinity'))
        json.dumps(report, allow_nan=False)

    def test_missing_duplicate_extra_or_malformed_rows_are_integrity_errors(self):
        inputs, rows = fixture()
        malformed = [[], rows * 2, [dict(rows[0], id='foreign')], [dict(rows[0], id=[])],
            [dict(rows[0], step=True)], [dict(rows[0], view='masked')],
            [dict(rows[0], extra=1)], [dict(rows[0], logp=[0.] * 8)],
            [dict(rows[0], order_logp=[0.])], {'rows': rows}]
        for field in ('logp', 'order_logp'):
            for value in (math.nan, math.inf, True):
                bad = deepcopy(rows); bad[0][field][0] = value; malformed.append(bad)
        for candidate in malformed:
            with self.subTest(candidate=candidate), self.assertRaises(ValueError):
                retention(inputs, candidate, rows, LIMITS)
        for candidate in ([], rows * 2):
            with self.subTest(archive=candidate), self.assertRaises(ValueError):
                retention(inputs, rows, candidate, LIMITS)

    def test_archive_auxiliary_views_are_validated_but_not_double_counted(self):
        inputs, rows = fixture(); masked = dict(rows[0], view='masked')
        archive = rows + [masked, dict(rows[0], view='swapped')]
        self.assertEqual(retention(inputs, rows, archive, LIMITS)['planned'], 1)
        for invalid in (archive + [masked], rows + [dict(masked, step=3)],
                        rows + [dict(masked, logp=[0.] * 8)], rows + [dict(masked, view='unknown')]):
            with self.subTest(archive=invalid), self.assertRaises(ValueError):
                retention(inputs, rows, invalid, LIMITS)

    def test_invalid_limits_or_duplicate_input_identities_fail_closed(self):
        inputs, rows = fixture()
        for name in LIMITS:
            for value in (-1., math.nan, math.inf, True, None):
                with self.subTest(name=name, value=value), self.assertRaises(ValueError):
                    retention(inputs, rows, rows, {**LIMITS, name: value})
        with self.assertRaises(ValueError): retention(inputs, rows, rows, {})
        with self.assertRaises(ValueError): retention(inputs, rows, rows, None)
        inputs['episodes'] *= 2
        with self.assertRaises(ValueError): retention(inputs, rows, rows, LIMITS)

    def test_import_never_loads_a_model_or_study_generator(self):
        code = ('import sys; import experiments.predictive_nucleus.set_acquisition_retention_v2; '
                'assert "torch" not in sys.modules; '
                'assert "experiments.predictive_nucleus.set_acquisition_data" not in sys.modules')
        subprocess.run([sys.executable, '-c', code], check=True)


if __name__ == '__main__': unittest.main()
