"""Synthetic polarity and provenance tests, without research fixtures."""
from itertools import product
import json
import unittest

from experiments.predictive_nucleus import transfer_sender as m
from experiments.predictive_nucleus.sender_policy import Sender as LegacySender


P = (1, -1, 1, -1)
N = tuple(-x for x in P)
X = (1, 1, -1, -1)
Y = tuple(-x for x in X)


def samples(switched=False):
    for sites, target, bits, emitted in product(((P, N), (N, P)), (X, Y), product(range(2), repeat=2), range(2)):
        site = sites.index(P if (target == X) != switched else N)
        yield sites, target, bits, emitted, int(emitted == bits[site])


class TransferSenderTests(unittest.TestCase):
    def test_selected_feedback_changes_bilinear_routing(self):
        left, right = (1, -1, 1, 1), (-1, 1, -1, -1)
        for reverse in (False, True):
            model = m.SharedSender.fit(samples(reverse))
            saved = json.loads(json.dumps(model.to_dict()))
            self.assertEqual(16, sum(len(row) for row in saved['matrix']))
            model = m.SharedSender.from_dict(saved)
            for sites, goal, bits in product(((left, right), (right, left)), (X, Y), product(range(2), repeat=2)):
                wanted = left if (goal == X) != reverse else right
                self.assertEqual(model.send(sites, goal, bits), bits[sites.index(wanted)])
        self.assertEqual(m.raw_dot((P, N), X, (1, 0)), 0)  # Raw features tie in this dummy fixture.

    def test_exact_lookup_is_conditioned_on_all_visible_inputs(self):
        seen = m.ExactLookup.fit(samples())
        restored = m.ExactLookup.from_dict(json.loads(json.dumps(seen.to_dict())))
        for sites, goal, bits, _, _ in samples():
            self.assertEqual(restored.send(sites, goal, bits), bits[sites.index(P if goal == X else N)])
        self.assertEqual(restored.fallback, 0)
        novel = ((1, 1, 1, 1), N)
        self.assertEqual(restored.send(novel, X, (1, 1)), restored.fallback)

    def test_legacy_adapter_never_relabels_a_fresh_badge(self):
        sender = LegacySender({(0, 0): (1., 0.), (1, 0): (0., 1.)})
        old = ((-1, -1, -1, -1), (1, 1, -1, -1))
        goal = (1, -1, 1, -1)
        self.assertEqual(m.legacy_send(sender, old, goal, (1, 0)), 1)
        self.assertEqual(m.legacy_send(sender, old[::-1], goal, (0, 1)), 1)
        self.assertEqual(m.legacy_send(sender, (old[0], P), goal, (1, 0)), 0)
        self.assertEqual(m.legacy_send(sender, old, X, (1, 0)), 0)

    def test_invalid_checkpoint_or_examples_fail_closed(self):
        with self.assertRaises(ValueError):
            m.SharedSender.from_dict({'matrix': [[float('nan')]*4]*4})
        with self.assertRaises(ValueError):
            m.SharedSender.fit([((P, N), X, (1, 1), True, 1)])
        with self.assertRaises(ValueError):
            m.ExactLookup.fit([((P, N), X, (1, 1), 0, 1)])
        model = m.ExactLookup.fit(samples())
        bad = model.to_dict()
        bad['entries'].append(bad['entries'][0])
        with self.assertRaises(ValueError):
            m.ExactLookup.from_dict(bad)


if __name__ == '__main__':
    unittest.main()
