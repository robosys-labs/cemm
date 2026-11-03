"""Synthetic intervention records with known weights. No research bank access."""
from copy import deepcopy
from itertools import product
import unittest

from experiments.predictive_nucleus import transfer_score as score
from experiments.predictive_nucleus.acceptance_contract import digest

PAIR = ((.9, .1), (.1, .9))
CHECKPOINT = {
    'shared': {'matrix': [[0., 1., 0., 0.], [-1., 0., 0., 0.], [0., 0., 0., 1.], [0., 0., -1., 0.]]},
    'lookup': {'entries': [], 'fallback': 0}, 'legacy': {'weights': []},
    'request': {'gains': [[0, 2, .5]]}, 'margin': {'gains': [[0, .5]]}}


def claim(episode, pair, bits, token):
    return digest(['g4-transfer-claim-v1', 'nand', 7, episode, 'W0', 1,
                   [f'{pair}/left/{bits[0]}', f'{pair}/right/{bits[1]}'], token])


def fixture():
    raw, targets = [], []
    for pi, part, order, site, bits, st, rep in product(
            range(12), score.PARTS, (0, 1), (0, 1), score.BITS, score.STRATA, range(4)):
        pair = f'physical-{pi:02d}'
        masks = (10, 12, 10) if part == 'recombined' else (3, 12, 3)
        mask = masks[pi // 4]
        left = [i for i in range(16) if i.bit_count() % 2 == int(part == 'fresh') and i < i ^ mask][pi % 4]
        a, b = left, left ^ mask
        ids = (b, a) if order else (a, b)
        gid = ids[site]
        sites = tuple(map(score._badge, ids))
        g = score._badge(gid)
        goal = (-g[1], g[0], -g[3], g[2])
        bit = bits[site]
        episode = score._round_id('nand', pair, part, ids, gid, bits, st, rep)
        donor_bits = tuple(b ^ int(i != site or rep >= 2 and st != 'known') for i, b in enumerate(bits))
        donor = score._round_id('nand', pair, part, ids, gid, donor_bits, st, rep)
        noise = int(digest(['g4-transfer-random-v1', episode])[:16], 16) % 2
        witness = [f'{pair}/left/{bits[0]}', f'{pair}/right/{bits[1]}']
        matrix = [v[::-1] if rep % 2 else v for v in PAIR]
        rewards = [int(i == (bit ^ (rep % 2))) for i in (0, 1)]
        local = bit if st == 'known' else None
        if st == 'indifferent':
            matrix, rewards = [(1., 1.)] * 2, [1, 1]
        prior = matrix[local] if local is not None else tuple((a + b) / 2 for a, b in zip(*matrix))
        targets.append(dict(id=episode, seed=7, law='nand', split='challenge', pair_id=pair, partition=part,
                            badge_ids=ids, goal_id=gid, sites=sites, goal=goal, bits=bits, rep=rep, source='W0',
                            menu_reversed=bool(rep % 2), stratum=st, prior=prior, cost=.75 if st == 'costly' else .05,
                            random_bit=noise, donor=donor, matrix=matrix, rewards=rewards, local=local,
                            witness_ids=witness))
        asked = st == 'hidden'
        margin_asked = st in ('hidden', 'indifferent')
        origin_claim = claim(episode, pair, bits, bit)
        arms = {}
        tokens = (bit, None, noise, donor_bits[site], 0, 0, score._raw_dot(sites, goal, bits), None, bit, bit)
        for arm, token in zip(score.ARMS, tokens, strict=True):
            paid = margin_asked if arm == 'margin' else asked and arm != 'free_silent'
            token = token if paid else None
            values = prior if token is None or local is not None else matrix[token]
            origin = None
            if token is not None:
                if arm in ('margin', 'delivered'):
                    origin = origin_claim
                elif arm == 'shuffled':
                    origin = claim(donor, pair, donor_bits, token)
                else:
                    origin = digest(['g4-transfer-control-v1', arm, episode, token])
            arms[arm] = dict(token=token, origin=origin, action=int(values[1] > values[0]))
        raw.append(dict(id=episode, emitted=bit, claim_id=origin_claim, asked=asked,
                        margin_asked=margin_asked, arms=arms))
    return raw, targets


class TransferScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.targets = fixture()

    def test_complete_scored_partition_and_cost(self):
        r = score.score_condition(self.rows, reversed(self.targets), 'nand', 7, CHECKPOINT)
        self.assertTrue(r['passed'])
        for p in r['partitions'].values():
            self.assertEqual(p['n'], 3072)
            self.assertEqual(p['arms']['delivered']['successes'], 2688)
            self.assertAlmostEqual(p['arms']['delivered']['mean_net'] - p['goal_blind_net'], .0625)
            self.assertEqual(p['arms']['margin']['requests'], 1536)
            self.assertEqual(p['causal']['opposing_goal_flips'], p['causal']['opposing_goal_pairs'])
        with self.assertRaises(ValueError):
            score.decision([r] * 10)

    def test_missing_or_duplicated_banks(self):
        with self.assertRaises(ValueError):
            score.score_condition(self.rows[:-1], self.targets[:-1], 'nand', 7, CHECKPOINT)
        with self.assertRaises(ValueError):
            score.score_condition(self.rows[:-1] + [self.rows[0]], self.targets, 'nand', 7, CHECKPOINT)

    def test_altered_checkpoint_choice_donor_or_silent_receipt(self):
        for defect in ('checkpoint', 'request', 'silent', 'origin', 'donor', 'seed', 'argmax'):
            case = self.rows.copy()
            targets = self.targets.copy()
            case[0] = deepcopy(case[0])
            targets[0] = deepcopy(targets[0])
            cp = deepcopy(CHECKPOINT)
            if defect == 'checkpoint':
                cp['shared']['matrix'] = [[0.] * 4 for _ in range(4)]
            elif defect == 'request':
                case[0]['asked'] = False
            elif defect == 'silent':
                case[0]['arms']['silent']['token'] = 0
            elif defect == 'origin':
                case[0]['arms']['shuffled']['origin'] = case[0]['claim_id']
            elif defect == 'donor':
                targets[0]['donor'] = case[0]['id']
            elif defect == 'seed':
                targets[0]['seed'] = 11
            else:
                case[0]['arms']['delivered']['action'] ^= 1
            with self.subTest(defect=defect), self.assertRaises(ValueError):
                score.score_condition(case, targets, 'nand', 7, cp)
