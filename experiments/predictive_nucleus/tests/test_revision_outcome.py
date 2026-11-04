"""TRAIN-only tests for the outcome-fitted G5 candidate; no challenge reads."""
import json
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus.revision_memory import Memory, Receipt
from experiments.predictive_nucleus.revision_outcome import (
    GRID, decision, fit_train, history, posterior, train_samples,
)


def r(key, term, scope, time, meaning, physical=True):
    return Receipt(key, term, scope, time, 'sensor' if physical else 'unverified',
                   (.99, .01) if physical else None,
                   (1-meaning) if physical else None, physical)


class OutcomeCorrectionTests(unittest.TestCase):
    def test_scoped_correction_replay_uncertainty_and_sentinel(self):
        root = ('world',)
        region = root + ('region',)
        unit, sibling = region + ('a',), region + ('b',)
        m = Memory([r('root', 'qor', root, 0, 0),
                    r('sentinel', 'nav', root, 0, 1)])
        self.assertEqual(decision(posterior(m, 'qor', root, .01)), 0)
        m.add(r('regional1', 'qor', region, 1, 1))
        self.assertIsNone(decision(posterior(m, 'qor', sibling, .01)))
        m.add(r('regional2', 'qor', region, 2, 1))
        self.assertEqual(decision(posterior(m, 'qor', sibling, .01)), 1)
        m.add(r('exception', 'qor', unit, 3, 0))
        self.assertIsNone(decision(posterior(m, 'qor', unit, .01)))
        m.add(r('assertion', 'qor', unit, 99, 1, False))
        prior = posterior(m, 'qor', unit, .01)
        m.add(r('root', 'qor', root, 0, 0))
        self.assertEqual(posterior(Memory(m.snapshot()), 'qor', unit, .01), prior)
        m.add(r('revision', 'qor', unit, 4, 0))
        self.assertEqual(decision(posterior(m, 'qor', unit, .01)), 0)
        self.assertEqual(decision(posterior(m, 'qor', sibling, .01)), 1)
        self.assertEqual(decision(posterior(m, 'nav', unit, .01)), 1)
        with self.assertRaises(ValueError):
            m.add(r('root', 'qor', root, 0, 1))

    def test_simultaneous_conflict_and_unidentifiable_payoff(self):
        scope = ('w',)
        m = Memory([r('s1', 'qor', scope, 1, 0),
                    r('s2', 'qor', scope, 1, 1)])
        self.assertIsNone(decision(posterior(m, 'qor', scope, .01)))
        m.add(Receipt('ambiguous', 'qor', scope, 2, 'sensor', (.5, .5), 1))
        self.assertIsNone(decision(posterior(m, 'qor', scope, .01)))
        self.assertAlmostEqual(posterior(m, 'qor', scope, .01), .5)
        m.add(r('newer', 'qor', scope, 3, 1))
        self.assertEqual(decision(posterior(m, 'qor', scope, .01)), 1)

    def test_train_from_only_selected_payoffs(self):
        def site(tag, pos):
            a, b = tag+'A', tag+'B'
            phrases = ([a, 'touches', b], [a,b,'touches'], ['touches', a,b])
            words = phrases[pos]
            reverse = [b if x == a else a if x == b else x for x in words]
            return dict(id=tag, entities=(a,b), lineage=tag,
                        actions=((0,a,b),(0,b,a)),
                        texts=(' '.join(words),' '.join(reverse)),
                        rewards=((1,0),(0,1)))
        matrix = ((.99,.01),(.01,.99))
        triples = [[(site('a',0),matrix),(site('b',1),matrix),
                    (site('c',2),matrix)]]*6
        with patch('experiments.predictive_nucleus.revision_outcome.select_triples',
                   return_value=triples):
            samples = tuple(train_samples({},7))
            result = fit_train({},7)
        self.assertEqual(len(samples), 1152)
        self.assertEqual(result['train_count'], 1152)
        self.assertIn(result['switch'], GRID)
        self.assertEqual(len(result['grid_mean_nll']), len(GRID))
        self.assertTrue(all(0 <= p <= 1 for m,t,s,pair,y in samples
                            for p in (posterior(m,t,s,result['switch']),)))
        self.assertTrue(all(type(y) is int and y in (0,1)
                            for _,_,_,_,y in samples))

    def test_real_train_fits_never_open_challenge(self):
        from experiments.predictive_nucleus.transfer_task import catalogue
        results = {f'{law}-{seed}': fit_train(catalogue(law, 'train'), seed)
                   for law in ('nand','nor') for seed in (7,11,23,37,53)}
        self.assertEqual(len(results), 10)
        self.assertTrue(all(item['train_count']==1152 for item in results.values()))
        print('G5_V2_TRAIN_ONLY ' + json.dumps(results,sort_keys=True),flush=True)


if __name__ == '__main__':
    unittest.main()
