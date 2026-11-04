"""Single fresh v7 raw challenge collection; NEVER imports evaluator/scorer.

This test is added only after the TRAIN fit has been published in a prior
commit. The raw logs are then committed before any held-out truth join.
"""
import json
import unittest
from hashlib import sha256
from pathlib import Path
from experiments.predictive_nucleus.independent_collection_v7 import collect
from experiments.predictive_nucleus.independent_task_v7 import LAWS,SEEDS,REGIME
from experiments.predictive_nucleus.independent_task_v6 import episodes as v6_episodes
from experiments.predictive_nucleus.transfer_task import catalogue,split_audit

ROOT=Path(__file__).resolve().parents[1]/'results/independent-v7'
CHUNK=16
SOURCE_CODE_SHA='a772d23570848ff51517fc481c2b22f996f0109b'

class ProspectiveV7Collection(unittest.TestCase):
    def test_seal_truth_blind_source_shift_forecasts(self):
        if (ROOT/'raw/manifest.json').exists():
            self.skipTest('v7 challenge already sealed; no raw recollection')
        train=json.loads((ROOT/'train-fitted.json').read_text())
        self.assertEqual(train['stage'],'TRAIN_ONLY')
        self.assertFalse(train['challenge_opened'])
        self.assertEqual(train['frozen_source_test_commit'],SOURCE_CODE_SHA)
        self.assertTrue(train['no_oracle_meaning_used_to_select_parameters'])
        self.assertEqual((train['fit']['h'],train['fit']['e_A'],train['fit']['e_B']),(.15,.03,.2))
        self.assertEqual((train['neutral']['h'],train['neutral']['e']),(.15,.1))
        self.assertEqual(train['rule']['delta'],.2)
        ids=set()
        previous_v6=set()
        signatures=set()
        for law in LAWS:
            split=split_audit(law)
            self.assertFalse(any(split['physical_overlap'].values()))
            bank=catalogue(law,'challenge')
            for seed in SEEDS:
                previous_v6.update(ep.uid for ep in v6_episodes(law,seed,'challenge',bank))
                raw=collect(law,seed,bank,train)
                rows=raw['rows']
                self.assertEqual(len(rows),192)
                current={r['id'] for r in rows}
                self.assertEqual(len(current),192)
                self.assertFalse(current & ids)
                ids.update(current)
                self.assertTrue(all(len(r['beliefs'])==5 and
                                    all(len(cell)==6 for cell in r['beliefs']) and
                                    len(r['payoff_p'])==15 and
                                    len(r['sensor_payoff_p'])==15 and
                                    len(r['v6_payoff_p'])==15 and
                                    len(r['source_ids'])==15
                                    for r in rows))
                signature=sha256(json.dumps(
                    [r['source_ids'] for r in rows],
                    separators=(',',':')).encode()).hexdigest()
                self.assertNotIn(signature,signatures)
                signatures.add(signature)
                rows_digest=sha256(json.dumps(
                    rows,separators=(',',':')).encode()).hexdigest()
                key=f'{law}-{seed}'
                meta={'version':raw['version'],'law':law,'seed':seed,
                      'split':raw['split'],'regime':REGIME[seed],
                      'parameters':raw['parameters'],
                      'cpu_seconds':raw['cpu_seconds'],
                      'rows_digest':rows_digest,
                      'source_pattern_digest':signature,
                      'worlds':len(rows),'chunks':len(rows)//CHUNK}
                print('G5_V7_RAW_META '+key+' '+json.dumps(
                    meta,separators=(',',':'),sort_keys=True),flush=True)
                for i in range(len(rows)//CHUNK):
                    block=rows[i*CHUNK:(i+1)*CHUNK]
                    print('G5_V7_RAW_CHUNK '+key+' '+str(i)+' '+
                          json.dumps(block,separators=(',',':')),flush=True)
        self.assertEqual(len(ids),1920)
        self.assertEqual(len(previous_v6),1920)
        self.assertFalse(ids & previous_v6)
        self.assertEqual(len(signatures),10)
        print('G5_V7_RAW_AUDIT '+json.dumps({
            'worlds':len(ids),'v6_worlds':len(previous_v6),
            'overlap':len(ids & previous_v6),
            'distinct_source_signatures':len(signatures),
            'physical_payoffs':len(ids)*15,'five_correlated_views':len(ids)*5,
            'oracle_truth_used':False},sort_keys=True),flush=True)

if __name__=='__main__':
    unittest.main()
