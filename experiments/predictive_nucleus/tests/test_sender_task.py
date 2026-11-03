"""Synthetic mechanics only, independent of TRAIN and challenge banks."""
from collections import Counter
from itertools import product
import unittest

from experiments.predictive_nucleus.sender_policy import Requester, Sender, values
from experiments.predictive_nucleus.sender_task import rounds


def toy_site(name, reverse=False):
    matrix = ((.98, .02), (.03, .97))
    if reverse:
        matrix = tuple(row[::-1] for row in matrix)
    return {'id': name, 'witness': [{'id': f'{name}-{b}'} for b in (0, 1)], 'predicted': matrix,
            'rewards': [[int(x > .5) for x in row] for row in matrix]}


class GoalSenderTests(unittest.TestCase):
    def test_joint_rounds_are_fully_crossed_and_attributed(self):
        pair = (toy_site('first'), toy_site('second', reverse=True))
        train = list(rounds(pair, 'nand', 'train'))
        held = list(rounds(pair, 'nand', 'challenge'))
        self.assertEqual(len(train), 384)
        self.assertEqual(len({r['id'] for r in held} | {r['id'] for r in train}), 768)
        self.assertEqual(Counter(r['bits'] for r in held), dict.fromkeys(product((0, 1), repeat=2), 96))
        train_combos = {(r['source'], r['goal']) for r in train if r['source'] != 'W0'}
        held_combos = {(r['source'], r['goal']) for r in held if r['source'] != 'W0'}
        self.assertTrue(train_combos.isdisjoint(held_combos))
        for r in held:
            site = r['tags'].index(r['goal'])
            h = r['bits'][site]
            selected = pair[site]
            order = slice(None, None, -1 if r['rep'] % 2 else 1)
            self.assertEqual(r['witness_ids'][site], selected['witness'][h]['id'])
            self.assertEqual(r['rewards'], selected['rewards'][h][order])
            self.assertEqual(r['matrix'][h], selected['predicted'][h][order])
            if r['stratum'] == 'known':
                self.assertEqual(values(r['prior'], r['matrix'], h, 1-h), r['matrix'][h])

    def test_reward_only_sender_recovers_goal_and_opposite_wire_conventions(self):
        for polarity in (0, 1):
            data = []
            for tags, goal, bits, message in product(((0, 1), (1, 0)), (0, 1),
                                                      product((0, 1), repeat=2), (0, 1)):
                data.append((tags, goal, bits, message, int(message == (bits[tags.index(goal)] ^ polarity))))
            sender = Sender.fit(data)
            restored = Sender.from_dict(sender.to_dict())
            for tags, goal, bits, _, _ in data:
                self.assertEqual(restored.send(tags, goal, bits), bits[tags.index(goal)] ^ polarity)

    def test_request_policy_uses_only_prior_and_cost(self):
        prior = (.5, .5)
        requester = Requester.fit([(prior, True, 1), (prior, True, 1),
                                   (prior, False, 0), (prior, False, 1)])
        restored = Requester.from_dict(requester.to_dict())
        self.assertTrue(restored.ask(prior, .05))
        self.assertFalse(restored.ask(prior, .50))
        self.assertFalse(restored.ask((0., 1.), 0))
        matrix = ((1., 0.), (0., 1.))
        self.assertEqual(values(prior, matrix, None, None), prior)
        self.assertEqual(values(prior, matrix, None, 0), matrix[0])
        with self.assertRaises(ValueError):
            values(prior, matrix, None, 3)
