from itertools import product
import unittest

from experiments.predictive_nucleus.conflict_policy import Evidence, Receiver, choose, fit


MATRIX = ((.99, .01), (.01, .99))


def tape(reverse_convention):
    for probe, first, other, a, b, trusted, action in product(range(2), repeat=7):
        probe_bit = (first, other)[trusted]
        target_bit = (a, b)[trusted ^ reverse_convention]
        yield Evidence(MATRIX, (('w', first), ('x', other)), probe, int(probe == probe_bit),
                       MATRIX, (('x', b), ('w', a))), action, int(action == target_bit)


class ConflictPolicyTest(unittest.TestCase):
    def test_matched_exposure_learns_opposite_conventions(self):
        repeat = fit(tape(0))
        switch = fit(tape(1))
        for x, y in zip(repeat, switch):
            row = Evidence(MATRIX, (('u', 0), ('v', 1)), 0, 1, MATRIX, (('v', 0), ('u', 1)))
            self.assertGreater(x.probability(row), .95)
            self.assertLess(y.probability(row), .05)
            self.assertEqual(x.probability(row), x.probability(row._replace(probe_claims=row.probe_claims[::-1])))
            self.assertEqual(choose(MATRIX, x.probability(row), .05), (1, False))

    def test_ambiguous_outcomes_and_verification(self):
        row = Evidence(MATRIX, (('u', 1), ('v', 1)), 1, 1, MATRIX, (('u', 0), ('v', 1)))
        for policy in (Receiver(8), Receiver(-1, 'empirical')):
            self.assertEqual(policy.probability(row), .5)
            self.assertEqual(policy.probability(row._replace(probe_reward=None)), .5)
            self.assertEqual(policy.probability(row._replace(target_claims=(('v', 1), ('u', 1)))), 1)
        self.assertEqual(choose(MATRIX, .5, .05), (0, True))
        self.assertEqual(choose(MATRIX, .5, .75), (0, False))
        self.assertEqual(choose(MATRIX, .5, None), (0, False))
        self.assertEqual(choose(((0., 1.), (0., 1.)), .5, .05), (1, False))
