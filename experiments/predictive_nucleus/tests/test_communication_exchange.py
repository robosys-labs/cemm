"""Synthetic receipt and matched-intervention invariants; no research execution."""
from collections import Counter
import unittest
from experiments.predictive_nucleus.communication_exchange import ledger, rounds

CASE = dict(id='case', entities=['x', 'y'], anchor=[0, 0],
            predicted=[[.9, .1], [.1, .9]], rewards=[[1, 0], [0, 1]],
            witness=[dict(id='raw'+str(i), time=1) for i in (0, 1)])


class CommunicationExchangeTests(unittest.TestCase):
    def setUp(self):
        self.rows = list(rounds(CASE, 'nand', 'synthetic'))
        self.by_id = {r['id']:r for r in self.rows}

    def test_delivery_conserves_physical_support_and_conflicting_receipts(self):
        self.assertEqual(len(self.by_id), 72)
        self.assertEqual(len({r['source_sensor']['id'] for r in self.rows}), 72)
        for r in self.rows:
            stratum, sensor = r['stratum'], r['sensor']
            self.assertEqual(tuple(sensor['prior']), r['prior'])
            if stratum in ('known', 'conflict'):
                self.assertEqual(sensor['support'], (r['h'],))
                self.assertFalse(r['opportunity'])
                for claimed in r['views'].values():
                    self.assertIn(claimed, (None, r['prior']))
            if stratum == 'conflict':
                old, = sensor['claims_on_file']
                new = r['claims']['delivered']
                self.assertNotEqual(new['token'], old['token'])
                self.assertEqual((old['source'], new['source']), ('A', 'B'))
                self.assertEqual(old['evidence_id'], r['on_file_source_sensors'][0]['id'])
                self.assertNotEqual(old['evidence_id'], new['evidence_id'])
                self.assertEqual(ledger(old, new, new), (old, new))
                with self.assertRaisesRegex(ValueError, 'collision'):
                    ledger(old, dict(old, token=new['token']))
            if stratum == 'unknown':
                self.assertTrue(all(v is None for v in r['views'].values()))

    def test_permutation_preserves_actual_donor_and_is_balanced(self):
        for stratum in {r['stratum'] for r in self.rows}:
            rows = [r for r in self.rows if r['stratum'] == stratum]
            delivered = [r['claims']['delivered'] for r in rows]
            shuffled = [r['claims']['shuffled'] for r in rows]
            self.assertEqual(Counter(x['origin_claim_id'] for x in delivered),
                             Counter(x['origin_claim_id'] for x in shuffled))
            for r in rows:
                receipt = r['claims']['shuffled']
                donor = self.by_id[receipt['origin']]
                self.assertNotEqual(donor['id'], r['id'])
                self.assertEqual(receipt['evidence_id'], donor['source_sensor']['id'])
                self.assertEqual(receipt['token'], donor['claims']['delivered']['token'])
            self.assertEqual(sum(x['token'] == y['token'] for x,y in zip(delivered, shuffled)), 4)

    def test_message_scope_and_prior_are_independent_of_withheld_reading(self):
        for r in self.rows:
            if r['stratum'] not in ('known', 'conflict'):
                expected = (1., 1.) if r['stratum'] == 'irrelevant' else (.5, .5)
                self.assertEqual(r['prior'], expected)
                self.assertNotIn('reading', r['claims']['delivered'])
            if r['stratum'] in ('stale', 'shifted'):
                self.assertEqual(r['source_sensor']['reading'], r['rep'] % 2)
                self.assertEqual(r['source_sensor']['kind'], 'synthetic_g4_probe')
                self.assertNotIn('native_evidence', r['source_sensor'])
                self.assertEqual(r['witness'].age, int(r['stratum'] == 'stale'))
                self.assertEqual(r['witness'].focus_matches, r['stratum'] != 'shifted')
