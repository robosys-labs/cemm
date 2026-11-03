"""Synthetic factorial data only. Exercise the saved decision without G3 evaluation."""
from copy import deepcopy
import unittest

from experiments.predictive_nucleus.acceptance_contract import digest
from experiments.predictive_nucleus import sender_scoring as s, sender_task as task


def toy_site(i):
    return {'id': f'physical-{i}', 'predicted': [[.95, .05], [.05, .95]], 'rewards': [[1, 0], [0, 1]],
            'witness': [{'id': f'{i}/0'}, {'id': f'{i}/1'}]}


def fixture(fixed=False):
    rows, targets = [], []
    for i in range(12):
        pair = (toy_site(2 * i), toy_site(2 * i + 1))
        for r in task.rounds(pair, 'nand', 'challenge'):
            focus = r['tags'].index(r['goal'])
            bits = r['bits']
            emitted = bits[0] if fixed else bits[focus]
            donor_bits = list(bits)
            donor_bits[1 - focus] ^= 1
            donor_bits[focus] ^= int(r['rep'] >= 2 and r['stratum'] != 'known')
            donor = task.round_id(r['pair_id'], donor_bits, r['tags'], r['goal'], r['source'], r['stratum'], r['rep'])
            noise = int(digest(['g4-sender-random-v1', r['id']])[:16], 16) % 2
            targets.append(dict(r, donor=donor, random_bit=noise))
            asked = r['stratum'] == 'hidden'
            def claim(identity, readings, symbol):
                witness_ids = [case['witness'][b]['id'] for case, b in zip(pair, readings)]
                return digest(['g4-sender-claim-v1', 'nand', 7, r['pair_id'], identity, r['source'],
                               1, witness_ids, symbol])
            potential = claim(r['id'], bits, emitted)
            shuffled = claim(donor, donor_bits, donor_bits[0 if fixed else focus])
            tokens = (emitted, None, noise, donor_bits[0 if fixed else focus], *bits, emitted, None, bits[focus])
            arms = {}
            for arm, token in zip(s.ARMS, tokens, strict=True):
                paid = asked and arm != 'free_silent'
                token = token if paid else None
                values = r['prior'] if token is None or r['local'] is not None else r['matrix'][token]
                if arm == 'action_code' and token is not None:
                    values = (1 - token, token)
                origins = {'shuffled': shuffled, 'delivered': potential, 'action_code': potential}
                origin = None if token is None else origins.get(
                    arm, digest(['g4-sender-intervention-v1', arm, r['id'], token]))
                arms[arm] = {'asked': paid, 'token': token, 'origin': origin, 'action': int(values[1] > values[0]),
                             'values': values, 'steps': 1}
            rows.append({k: r[k] for k in ('id', 'pair_id', 'matrix', 'prior', 'local')} |
                        {'law': 'nand', 'seed': 7, 'emitted': emitted, 'claim_id': potential, 'arms': arms})
    return rows, targets


class SenderScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.targets = fixture()

    def test_reports_paired_gain_and_strong_truth_table_envelope(self):
        r = s.score_condition(reversed(self.rows), self.targets, 'nand', 7)
        self.assertTrue(r['passed'])
        self.assertEqual(r['n'], 4608)
        self.assertEqual(r['causal']['goal_pairs'], 1152)
        self.assertEqual(r['causal']['goal_flips'], 576)
        a = r['arms']
        self.assertEqual(a['delivered']['successes'], 3840)
        self.assertEqual(a['delivered']['requests'], 1536)
        self.assertAlmostEqual(a['delivered']['mean_net'], (3840 - .05 * 1536) / 4608)
        self.assertAlmostEqual(r['comparisons']['public_router']['gain'], 0)
        self.assertAlmostEqual(r['goal_blind_envelope']['all']['gain'], 1 / 12)
        self.assertAlmostEqual(r['goal_blind_envelope']['crossed']['gain'], 1 / 12)
        with self.assertRaisesRegex(ValueError, 'incomplete or duplicate'):
            s.decision([r] * 10)

    def test_fixed_channel_fails_content_and_hindsight_gates(self):
        r = s.score_condition(*fixture(fixed=True), 'nand', 7)
        self.assertFalse(r['passed'])
        self.assertFalse(r['checks']['goal_only_switch'])
        self.assertFalse(r['checks']['relevant_signal'])
        self.assertFalse(r['checks']['net_over_goal_blind_all'])
        self.assertFalse(r['checks']['net_vs_public_router'])

    def test_truncated_duplicated_and_jointly_truncated_records_rejected(self):
        for rows, targets in ((self.rows[:-1], self.targets[:-1]), (self.rows, self.targets[:-1]),
                              (self.rows[:-1] + [self.rows[0]], self.targets)):
            with self.assertRaises(ValueError):
                s.score_condition(rows, targets, 'nand', 7)

    def test_foreign_donor_and_silent_leak_and_wrong_argmax_rejected(self):
        for field in ('donor', 'random_bit', 'goal_pair', 'menu_reversed', 'matrix', 'hidden_leak', 'argmax',
                      'counterfactual_value', 'token_bool', 'forged_claim', 'wrong_origin'):
            rows, targets = self.rows.copy(), self.targets.copy()
            rows[0] = deepcopy(rows[0])
            targets[0] = deepcopy(targets[0])
            a = rows[0]['arms']['silent']
            if field == 'donor':
                targets[0]['donor'] = targets[0]['id']
            elif field == 'random_bit':
                targets[0][field] = bool(targets[0][field])
            elif field == 'goal_pair':
                targets[0][field] = 'other'
            elif field == 'menu_reversed':
                targets[0][field] = True
            elif field == 'matrix':
                rows[0][field] = [[float('nan'), 0], [0, 1]]
            elif field == 'hidden_leak':
                a['token'] = 1
            elif field == 'argmax':
                a['action'] ^= 1
            elif field == 'counterfactual_value':
                a['values'] = [0.1, 0.9]
            elif field == 'forged_claim':
                rows[0]['claim_id'] = digest(['different witness'])
            elif field == 'wrong_origin':
                rows[0]['arms']['shuffled']['origin'] = rows[0]['claim_id']
            else:
                rows[0]['arms']['delivered']['token'] = False
            with self.subTest(field=field), self.assertRaises(ValueError):
                s.score_condition(rows, targets, 'nand', 7)
