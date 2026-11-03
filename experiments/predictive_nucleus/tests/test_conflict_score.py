"""Synthetic negative controls for independent matched-history replay."""
import unittest

from experiments.predictive_nucleus.conflict_policy import Evidence
from experiments.predictive_nucleus.conflict_score import _expected, _replay


class ConflictScoreTest(unittest.TestCase):
    matrix = ((.99, .01), (.01, .99))

    def test_balanced_single_witness_and_matched_fits(self):
        row = Evidence(self.matrix, (('z', 0), ('a', 1)), 0, 1, self.matrix, (('a', 0), ('z', 1)))
        case = {'public': row, 'ca': (0,1), 'cb': (1,0)}
        fits = [{'neural': 5., 'empirical': 1}, {'neural': -5., 'empirical': -1}]
        persist, switch = (_expected(case, fits, env) for env in (0,1))
        self.assertGreater(persist['learned'], .98)
        self.assertEqual(persist['crossed'], switch['learned'])
        self.assertAlmostEqual(persist['fixed0'], 5/6)
        self.assertEqual(persist['fixed1'], .5)
        self.assertAlmostEqual(switch['fixed0'], 2/3)
        self.assertEqual(switch['fixed1'], 0)
        self.assertEqual(persist['blind'], .5)

    def test_suppression_never_receives_private_reading(self):
        neutral = [.5, 0, 2, 0, 0]
        self.assertEqual(list(_replay(neutral, .5, 'suppressed', self.matrix, 1, 1)),
                         [(1,0), (0,0), (0,0)])
        with self.assertRaisesRegex(ValueError, 'request or action'):
            list(_replay([.5,0,3,0,0], .5, 'suppressed', self.matrix, 1, 1))
        with self.assertRaisesRegex(ValueError, 'unassisted action'):
            list(_replay([.5,1,3,0,0], .5, 'shuffled', self.matrix, 1, 1))

    def test_two_worlds_and_two_conventions_on_fabricated_sites(self):
        from experiments.predictive_nucleus.conflict_run import collect, fit_condition
        from experiments.predictive_nucleus.conflict_score import score
        from experiments.predictive_nucleus.conflict_task import cases

        for law, reverse in [('nand',False), ('nor',True)]:
            matrix = self.matrix[::-1] if reverse else self.matrix
            rewards = [[int(a == int(row[1] > row[0])) for a in range(2)] for row in matrix]
            pairs = {f'pair-{i}': [{'texts': ['first','second'], 'rewards': rewards} for _ in range(2)]
                     for i in range(12)}
            tables = {p: [matrix, matrix] for p in pairs}
            bank = {'sites': pairs, 'forecasts': {'7': tables}}
            cp, observations = fit_condition(list(cases(bank, law, 7, 'train')))
            self.assertEqual(len(observations), 6144)
            held = list(cases(bank, law, 7, 'challenge'))
            raw = {'live_matrices': tables, 'rows': list(collect(held, cp))}
            result = score(law, 7, bank, raw, cp)
            self.assertTrue(result['passed'], result['checks'])
            self.assertTrue(result['empirical_tie'])
            self.assertEqual(result['twin_hits'], result['twin_count'])
            for r in result['conventions']:
                self.assertAlmostEqual(r['arms']['learned']['mean_net'], .9125)
                for projection in r['ceilings'].values():
                    self.assertEqual((projection['max_correct'], projection['n']), (768,1536))
                self.assertEqual(r['arms']['learned']['pre_successes'], 5376)
            raw['rows'][0][2][0][1] ^= 1
            with self.assertRaisesRegex(ValueError, 'unassisted action'):
                score(law, 7, bank, raw, cp)
