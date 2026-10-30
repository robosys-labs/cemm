"""Synthetic contrast arithmetic only; no checkpoint, collector or study run."""
from copy import deepcopy
import math
import unittest

from experiments.predictive_nucleus import mixed_composition_run as run


IDS, TARGET = ['opaque-z', 'opaque-k', 'opaque-a'], 'opaque-k'
LIMITS = {'pairs': 1, 'max_equal_p_one': .1, 'min_opposite_p_one': .9, 'min_gap': .8}


def forecast(episode, p_one, ids=None, strings=False):
    ids = list(IDS if ids is None else ids)
    probabilities = [0.] * (2 ** len(ids))
    probabilities[0] = 1. - p_one
    probabilities[1 << (len(ids) - ids.index(TARGET) - 1)] = p_one
    zero = 'negative_infinity' if strings else -math.inf
    return {'episode': episode, 'step': 2, 'ids': ids, 'status': 'ANSWERED',
        'log_probabilities': [math.log(p) if p else zero for p in probabilities]}


def pair(name='pair', equal=0., opposite=1., strings=False):
    cases = [{'episode': name + '-' + condition, 'contrast_id': name, 'condition': condition,
        'query_step': 2, 'target_id': TARGET, 'expected_target_bit': bit}
        for condition, bit in [('equal', 0), ('opposite', 1)]]
    points = [forecast(cases[0]['episode'], equal, strings=strings),
              forecast(cases[1]['episode'], opposite, strings=strings)]
    return points, cases


class JointCorrelationRunTests(unittest.TestCase):
    def test_ideal_opposite_outcomes_pass_numeric_and_serialized_zero_support(self):
        for strings in (False, True):
            points, cases = pair(strings=strings)
            distractor = dict(forecast(cases[0]['episode'], .5), step=1)
            result = run.correlation_scores([distractor, *points], cases, LIMITS)
            self.assertEqual([result[k] for k in ('planned', 'observed_pairs', 'complete_pairs', 'passed_pairs')],
                             [1, 1, 1, 1])
            self.assertTrue(result['all_passed']); self.assertEqual(result['min_gap'], 1.)
            entry = result['pairs'][0]
            self.assertEqual((entry['contrast_id'], entry['equal_episode'], entry['opposite_episode']),
                             ('pair', 'pair-equal', 'pair-opposite'))
            self.assertEqual((entry['p_one_equal'], entry['p_one_opposite'], entry['gap']), (0., 1., 1.))

    def test_identical_half_probability_marginal_control_fails(self):
        points, cases = pair(equal=.5, opposite=.5)
        result = run.correlation_scores(points, cases, LIMITS)
        self.assertEqual((result['complete_pairs'], result['passed_pairs'], result['min_gap']), (1, 0, 0.))
        self.assertFalse(result['all_passed'])

    def test_threshold_boundaries_and_each_outside_limit(self):
        points, cases = pair(equal=.1, opposite=.9)
        result = run.correlation_scores(points, cases, LIMITS)
        self.assertTrue(result['all_passed'])
        self.assertAlmostEqual(result['min_gap'], .8)
        for equal, opposite, gap in ((.100001, .95, .8), (.05, .899999, .8), (.1, .9, .800001)):
            points, cases = pair(equal=equal, opposite=opposite)
            self.assertFalse(run.correlation_scores(points, cases, dict(LIMITS, min_gap=gap))['all_passed'])

    def test_missing_condition_or_forecast_keeps_planned_denominator(self):
        first, first_cases = pair('first')
        second, second_cases = pair('second')
        for failure in ('condition', 'forecast', 'ABSTAIN', 'UNPRODUCED'):
            points, cases = deepcopy(first + second), deepcopy(first_cases + second_cases)
            if failure == 'condition': cases.pop()
            if failure in ('condition', 'forecast'): points.pop()
            else: points[-1].update(status=failure, log_probabilities=None)
            result = run.correlation_scores(points, cases, dict(LIMITS, pairs=2))
            self.assertEqual((result['planned'], result['complete_pairs'], result['passed_pairs']), (2, 1, 1))
            self.assertFalse(result['all_passed'])
            incomplete = next(p for p in result['pairs'] if p['contrast_id'] == 'second')
            self.assertFalse(incomplete['complete']); self.assertFalse(incomplete['passed'])
        result = run.correlation_scores([], [], dict(LIMITS, pairs=2))
        self.assertEqual((result['planned'], result['observed_pairs'], result['complete_pairs']), (2, 0, 0))
        self.assertFalse(result['all_passed'])

    def test_probability_mass_is_not_renormalized_to_oracle_support(self):
        points, cases = pair(equal=.05, opposite=.85)
        points[1]['possible_worlds'] = [2]
        result = run.correlation_scores(points, cases, LIMITS)
        self.assertAlmostEqual(result['pairs'][0]['p_one_opposite'], .85)
        self.assertFalse(result['all_passed'])

    def test_target_is_located_in_each_forecasts_opaque_id_order(self):
        _, cases = pair()
        points = [forecast(cases[0]['episode'], .05, ids=[TARGET, 'opaque-a', 'opaque-z']),
                  forecast(cases[1]['episode'], .95, ids=['opaque-a', 'opaque-z', TARGET])]
        result = run.correlation_scores(points, cases, LIMITS)
        self.assertTrue(result['all_passed'])
        self.assertAlmostEqual(result['pairs'][0]['p_one_equal'], .05)
        self.assertAlmostEqual(result['pairs'][0]['p_one_opposite'], .95)

    def test_duplicate_conditions_and_mismatched_query_bindings_are_rejected(self):
        points, cases = pair()
        with self.assertRaisesRegex(ValueError, 'duplicate contrast'):
            run.correlation_scores(points, cases + [deepcopy(cases[0])], LIMITS)
        for field, value in [('target_id', 'opaque-z'), ('query_step', 1)]:
            altered, metadata = deepcopy(points), deepcopy(cases)
            metadata[1][field] = value
            if field == 'query_step': altered[1]['step'] = value
            with self.assertRaisesRegex(ValueError, 'contrast query differs'):
                run.correlation_scores(altered, metadata, LIMITS)


if __name__ == '__main__': unittest.main()
