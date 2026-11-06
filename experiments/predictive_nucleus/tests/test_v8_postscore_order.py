"""Synthetic witness for the immutable v8 payoff-order erratum."""
from dataclasses import replace
import unittest

from experiments.predictive_nucleus import joint_trust_v8, source_temporal_v7
from experiments.predictive_nucleus.temporal_belief_v5 import TimedReceipt


class FrozenV8PayoffOrder(unittest.TestCase):
    def test_reindexing_cannot_recover_a_causal_forecast(self):
        # Public delivery order at t=0 is qor then nav. The two menus make
        # their prior payoff forecasts distinguishable even with uniform meaning.
        qor = TimedReceipt('w:qor:0', 'qor', ('w',), 0, 'sensor-A',
                           (1., 1.), 1, True)
        nav = TimedReceipt('w:nav:0', 'nav', ('w',), 0, 'sensor-B',
                           (0., 0.), 0, True)
        first, second = joint_trust_v8.payoff_forecasts((qor, nav))
        expected_qor, = joint_trust_v8.payoff_forecasts((qor,))
        self.assertAlmostEqual(expected_qor, .885)
        self.assertAlmostEqual(first, .115)  # scored as qor, actually nav

        # Even if we attach the second forecast to qor, it has seen nav's
        # outcome. Changing that later-delivered outcome changes this forecast.
        revised = (qor, replace(nav, outcome=1))
        self.assertNotAlmostEqual(second, expected_qor)
        self.assertNotAlmostEqual(second, joint_trust_v8.payoff_forecasts(revised)[1])

        # Both frozen controls emit the first forecast on the delivered prefix.
        for error_a, error_b in ((.03, .20), (.10, .10)):
            args = (.15, error_a, error_b)
            prior, = source_temporal_v7.payoff_forecasts((qor,), *args)
            for history in ((qor, nav), revised):
                self.assertEqual(source_temporal_v7.payoff_forecasts(history, *args)[0], prior)

    def test_fixed_hazard_alone_guarantees_the_abstention_cutoff(self):
        # A distribution over all 32 latent states is a mixture of these
        # extremes, so this also bounds every possible pre-epoch posterior.
        for state in range(joint_trust_v8.STATES):
            weights = [0.] * joint_trust_v8.STATES
            weights[state] = 1.
            posterior = joint_trust_v8._transition(weights)
            p = sum(weight for index, weight in enumerate(posterior)
                    if index & joint_trust_v8.LOCAL)
            expected = .85 if state & joint_trust_v8.LOCAL else .15
            self.assertAlmostEqual(p, expected)
            self.assertTrue(.05 < p < .95)
