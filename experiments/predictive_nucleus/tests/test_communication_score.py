"""Synthetic saved-record checks only."""
import subprocess
import sys
import unittest
from copy import deepcopy
from itertools import product

from experiments.predictive_nucleus import communication_score as scoring


def fixture():
    targets, rows = [], []
    for law, seed, label in product(scoring.LAWS, scoring.SEEDS, scoring.STRATA):
        request = label in ('useful', 'misleading')
        target = {'id': 'fixture-' + label, 'law': law, 'seed': seed, 'stratum': label,
                  'cost': .75 if label == 'costly' else .05}
        targets.append(dict(target, rewards=[int(not request), int(request)]))
        arms = {}
        for arm in scoring.ARMS:
            asked = request and arm != 'free_silent'
            action = int(asked and (arm == 'delivered' or (arm == 'shortcut' and label == 'useful')))
            arms[arm] = {'asked': asked, 'action': action, 'values': [1 - action, action], 'steps': 1}
        rows.append(dict(target, arms=arms))
    return rows, targets


class CommunicationScoreTests(unittest.TestCase):
    def test_paired_reward_net_cost_and_calibration_are_joined_by_identity(self):
        rows, targets = fixture()
        result = scoring.score(reversed(rows), targets)
        self.assertTrue(result['passed'])
        self.assertEqual(result['decision'], 'KEEP_BOUNDED_RECEIVER')
        self.assertEqual((result['episodes'], result['arm_decisions']), (90, 540))
        condition = result['conditions']['nand/7']
        self.assertEqual(condition['comparisons']['random']['gained_successes'], 2)
        self.assertEqual(condition['comparisons']['random']['lost_successes'], 0)
        self.assertAlmostEqual(condition['comparisons']['silent']['mean_paired_net_gain'], 2 / 9)
        self.assertAlmostEqual(condition['comparisons']['free_silent']['mean_paired_net_gain'], 1.9 / 9)
        self.assertAlmostEqual(condition['comparisons']['shortcut']['mean_paired_net_gain'], 1 / 9)
        self.assertEqual(condition['arms']['delivered']['selected_reward_calibration']['brier'], 0.)
        self.assertAlmostEqual(condition['arms']['silent']['selected_reward_calibration']['brier'], 2 / 9)

    def test_one_failed_condition_cannot_be_rescued_by_pooling(self):
        rows, targets = fixture()
        row = next(r for r in rows if r['stratum'] == 'misleading')
        row['arms']['delivered'] = dict(row['arms']['shortcut'])
        result = scoring.score(rows, targets)
        self.assertEqual(result['decision'], 'REVISE')
        failed = result['conditions']['nand/7']
        self.assertFalse(failed['checks']['net_over_shortcut'])
        self.assertFalse(failed['checks']['success_misleading'])
        self.assertEqual(failed['strata']['misleading']['failed_goal_examples'], ['fixture-misleading'])
        self.assertTrue(result['conditions']['nor/7']['passed'])

    def test_missing_extra_duplicate_condition_or_stratum_fails_closed(self):
        rows, targets = fixture()
        for r, t in ((rows[:-1], targets), (rows + [rows[0]], targets), (rows, targets + [targets[0]]),
                     (rows[:-1], targets[:-1]), (rows[9:], targets[9:]),
                     (rows + [dict(rows[0], id='extra')], targets)):
            with self.assertRaises(ValueError):
                scoring.score(r, t)

    def test_invalid_budgets_probabilities_and_no_request_leakage_rejected(self):
        rows, targets = fixture()
        for label, arm, changes in (
            ('useful', 'shuffled', {'asked': False}), ('useful', 'free_silent', {'asked': True}),
            ('known', 'delivered', {'steps': True}), ('known', 'shuffled', {'values': [1., .1]}),
            ('known', 'silent', {'action': 1}), ('known', 'silent', {'values': [0., float('nan')]}),
        ):
            source = deepcopy(rows)
            next(r for r in source if r['stratum'] == label)['arms'][arm].update(changes)
            with self.subTest(label=label, arm=arm, changes=changes), self.assertRaises(ValueError):
                scoring.score(source, targets)

    def test_costly_request_and_unknown_are_handled_per_registration(self):
        rows, targets = fixture()
        for label in ('costly', 'unknown'):
            arms = next(r for r in rows if r['stratum'] == label)['arms']
            for arm in set(arms) - {'free_silent'}:
                arms[arm]['asked'] = True
        result = scoring.score(rows, targets)['conditions']['nand/7']
        self.assertFalse(result['checks']['avoid_request_costly'])
        self.assertFalse(any('unknown' in key for key in result['checks']))
        self.assertAlmostEqual(result['arms']['delivered']['mean_cost'], .90 / 9)
        self.assertEqual(result['strata']['costly']['request_error_examples'], ['fixture-costly'])

    def test_scorer_never_imports_the_model_or_study_generator(self):
        script = ('import sys; from experiments.predictive_nucleus import communication_score; '
                  'assert "torch" not in sys.modules; '
                  'assert not any(k.startswith("experiments.predictive_nucleus.communication_") '
                  'and not k.endswith(".communication_score") for k in sys.modules)')
        subprocess.run([sys.executable, '-c', script], check=True)

    def test_binary_calibration_uses_all_forecasts_including_boundaries(self):
        result = scoring.binary_calibration([0, .5, .55, 1], [0, 1, 0, 1])
        self.assertAlmostEqual(result['brier'], (.5 ** 2 + .55 ** 2) / 4)
        self.assertAlmostEqual(result['ece'], .025 / 2)
        self.assertEqual([r['count'] for r in result['bins']], [1, 0, 0, 0, 0, 2, 0, 0, 0, 1])

    def test_malformed_probabilities_or_missing_outcomes_fail_closed(self):
        for p, y in (([float('nan')], [0]), ([1.2], [1]), ([True], [1]), ([.2], [2]),
                     ([.2], [False]), ([1, 0], [1]), ([], [])):
            with self.subTest(p=p, y=y), self.assertRaises(ValueError):
                scoring.binary_calibration(p, y)
