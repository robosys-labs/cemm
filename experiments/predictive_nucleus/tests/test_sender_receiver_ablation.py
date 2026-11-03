import unittest

from experiments.predictive_nucleus.communication_policy import Witness
from experiments.predictive_nucleus.sender_receiver_ablation import _tables


class ReceiverAblationTests(unittest.TestCase):
    def test_cue_is_removed_before_refitting(self):
        source = Witness('a', 0, True)
        samples = [(source, prior, cue, paid, reward)
                   for prior, cue, hits in [((.5, .5), True, (0, 1)), ((1., 0.), False, (1, 1))]
                   for paid, reward in zip((False, True), hits)]
        tables = _tables(samples)
        self.assertEqual([r[-1] for r in tables['original']], [0., 1.])
        self.assertEqual(tables['removed'], [['a', False, True, None, .5]])
        self.assertEqual([r[-2:] for r in tables['margin']], [[0, 1.], [3, 0.]])
        changed = _tables([(w, p, not cue, asked, reward) for w, p, cue, asked, reward in samples])
        self.assertNotEqual(tables['original'], changed['original'])
        for arm in ('removed', 'margin'):
            self.assertEqual(tables[arm], changed[arm])
