"""Synthetic physical-answer tests independent of native TRAIN or challenge data."""
from math import fsum
import unittest

from experiments.predictive_nucleus.physical_query_v1 import choose, posterior


class PhysicalQuery(unittest.TestCase):
    def test_informative_physical_answer_and_fee_boundary(self):
        prior, likelihood, rewards = (.5, .5), ((1., 0.), (0., 1.)), ((1., 0.), (0., 1.))
        result = choose(prior, likelihood, rewards, .05)
        self.assertEqual(result, {'action': 0, 'ask': True, 'expected_before': .5,
                                  'expected_after': 1., 'value': .5})
        self.assertFalse(choose(prior, likelihood, rewards, .5)['ask'])
        self.assertFalse(choose(prior, likelihood, rewards, .75)['ask'])
        self.assertFalse(choose(prior, likelihood, rewards, None)['ask'])
        self.assertEqual(posterior(prior, likelihood, 1), (0., 1.))
        with self.assertRaises(TypeError):
            choose(prior, likelihood, rewards, .05, truth=1)

    def test_indistinguishable_answers_preserve_role_uncertainty(self):
        prior = (0., 0., .5, .5)
        likelihood = ((1., 0.), (0., 1.), (1., 0.), (1., 0.))
        rewards = tuple(tuple(float(i == j) for j in range(4)) for i in range(4))
        result = choose(prior, likelihood, rewards, 0.)
        self.assertEqual(result['value'], 0.)
        self.assertFalse(result['ask'])
        self.assertEqual(posterior(prior, likelihood, 0), prior)
        with self.assertRaisesRegex(ValueError, 'zero predicted probability'):
            posterior(prior, likelihood, 1)

    def test_identical_likelihood_rows_have_zero_value(self):
        prior = (.25,) * 4
        likelihood = ((.2, .8),) * 4
        rewards = tuple(tuple(float(i == j) for j in range(4)) for i in range(4))
        self.assertFalse(choose(prior, likelihood, rewards, 0.)['ask'])
        self.assertEqual(posterior(prior, likelihood, 0), prior)
        self.assertEqual(posterior(prior, likelihood, 1), prior)

    def test_roundoff_normalization_cannot_buy_an_indifferent_answer(self):
        prior = (.500000000025, .500000000025)
        likelihood = ((.500000000025, .500000000025),) * 2
        result = choose(prior, likelihood, ((1., 1.), (1., 1.)), 0.)
        self.assertEqual(result['value'], 0.)
        self.assertFalse(result['ask'])
        self.assertEqual(posterior(prior, likelihood, 0), (.5, .5))

    def test_nonfinite_computed_value_is_rejected(self):
        likelihood = tuple(tuple(float(i == j) for j in range(4)) for i in range(4))
        rewards = tuple(tuple(1.7e308 if i == j else -1.7e308 for j in range(4)) for i in range(4))
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            choose((.25,) * 4, likelihood, rewards, .05)

    def test_equal_rewards_and_small_predictive_differences(self):
        prior, likelihood = (.5, .5), ((.9, .1), (.9001, .0999))
        result = choose(prior, likelihood, ((1., 0.), (0., 1.)), .05)
        self.assertFalse(result['ask'])
        self.assertAlmostEqual(result['value'], .00005)
        indifferent = choose(prior, likelihood, ((1., 1.), (1., 1.)), 0.)
        self.assertAlmostEqual(indifferent['value'], 0.)
        self.assertFalse(indifferent['ask'])

    def test_formula_matches_explicit_bayes_expectation(self):
        prior = (.2, .3, .5)
        likelihood = ((.6, .4, 0., 0.), (.1, .2, .7, 0.), (.3, .3, .4, 0.))
        rewards = ((1., .2), (.4, .7), (0., 1.))
        expected = 0.
        for endpoint in range(4):
            mass = fsum(p * row[endpoint] for p, row in zip(prior, likelihood))
            if mass:
                updated = posterior(prior, likelihood, endpoint)
                expected += mass * max(fsum(p * row[a] for p, row in zip(updated, rewards))
                                       for a in range(2))
        self.assertAlmostEqual(choose(prior, likelihood, rewards, .05)['expected_after'], expected)

    def test_invalid_inputs_rejected(self):
        prior, likelihood, rewards = (.5, .5), ((1., 0.), (0., 1.)), ((1., 0.), (0., 1.))
        for bad in ((), (.4, .4), (-.1, 1.1), (float('nan'), .5)):
            with self.subTest(prior=bad), self.assertRaises(ValueError):
                choose(bad, likelihood, rewards, .05)
        for bad in ((), ((1.,),), ((1.,), (1., 0.)), ((1., 0.), (.5, .2))):
            with self.subTest(likelihood=bad), self.assertRaises(ValueError):
                choose(prior, bad, rewards, .05)
        for bad in ((), ((1.,),), ((1., 0.), (float('inf'), 1.))):
            with self.subTest(rewards=bad), self.assertRaises(ValueError):
                choose(prior, likelihood, bad, .05)
        for fee in (-.1, float('nan'), True):
            with self.subTest(fee=fee), self.assertRaises(ValueError):
                choose(prior, likelihood, rewards, fee)
        for endpoint in (-1, 2, True):
            with self.subTest(endpoint=endpoint), self.assertRaises(ValueError):
                posterior(prior, likelihood, endpoint)
