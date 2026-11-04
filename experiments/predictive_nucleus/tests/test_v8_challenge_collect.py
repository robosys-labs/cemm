"""One-time v8 TEST forecast publication: no evaluator, truth or refit.

Frozen parameters and full TRAIN-suite receipt predate this file. The
observable raw rows are committed before any TEST truth-joined scorer runs.
"""
from hashlib import sha256
import json
from pathlib import Path
import unittest

from experiments.predictive_nucleus.independent_collection_v8 import collect
from experiments.predictive_nucleus.independent_task_v8 import LAWS,SEEDS,episodes
from experiments.predictive_nucleus.independent_task_v7 import episodes as v7_episodes
from experiments.predictive_nucleus.independent_task_v6 import episodes as v6_episodes
from experiments.predictive_nucleus.transfer_task import catalogue,split_audit
from experiments.predictive_nucleus.goal_policy_v6 import public_task

ROOT=Path(__file__).resolve().parents[1]/'results/independent-v8'
LOCK_SHA='771c66df1ce6a15c16ead6b279367594bfbccdce'
CHUNK=16

class SealedV8RawCollection(unittest.TestCase):
    def test_collect_once_without_evaluator_truth(self):
        if (ROOT/'raw/manifest.json').exists():
            self.skipTest('v8 raw TEST already sealed; never regenerate')
        freeze=json.loads((ROOT/'train-locked.json').read_text())
        self.assertEqual(freeze['stage'],'TRAIN_ONLY_NO_V8_TEST_OPENED')
        self.assertEqual(freeze['model_generator_collector_scorer_train_test_commit'],LOCK_SHA)
        self.assertFalse(freeze['challenge_opened'])
        self.assertEqual(freeze['new_v8_fitted_parameters'],0)
        self.assertEqual(freeze['joint_state_count'],32)
        self.assertEqual(freeze['train_preflight_test_counts'],1233)
        seen=set()
        v6_ids=set()
        v7_ids=set()
        signatures=set()
        for law in LAWS:
            split=split_audit(law)
            self.assertFalse(any(split['physical_overlap'].values()))
            bank=catalogue(law,'challenge')
            for seed in SEEDS:
                # Previous open-study IDs are read for overlap only.
                v6_ids.update(x.uid for x in v6_episodes(law,seed,'challenge',bank))
                v7_ids.update(x.uid for x in v7_episodes(law,seed,'challenge',bank))
                raw=collect(law,seed,bank)
                rows=raw['rows']
                self.assertEqual(raw['version'],'g5-v8-raw')
                self.assertEqual(raw['parameters'],(.15,.03,.2,32))
                self.assertEqual(len(rows),192)
                ids={r['id'] for r in rows}
                self.assertEqual(len(ids),192)
                self.assertFalse(ids&seen)
                seen.update(ids)
                for left,right in zip(rows[::2],rows[1::2],strict=True):
                    self.assertEqual(left['pre_record_hash'],right['pre_record_hash'])
                    self.assertEqual(left['pre_post_meaning_p'],right['pre_post_meaning_p'])
                    self.assertEqual(left['trust_pre_p'],right['trust_pre_p'])
                    self.assertTrue(.05<left['pre_post_meaning_p']<.95)
                self.assertTrue(all(
                    len(r['beliefs'])==5 and
                    all(len(z)==4 for z in r['beliefs']) and
                    len(r['payoff_p'])==15 and
                    len(r['v7_payoff_p'])==15 and
                    len(r['neutral_payoff_p'])==15 and
                    len(r['source_ids'])==15 and
                    r['goals']==public_task(r['id'])[:2] and
                    r['fee']==public_task(r['id'])[2]
                    for r in rows))
                signature=sha256(json.dumps(
                    [r['source_ids'] for r in rows],
                    separators=(',',':')).encode()).hexdigest()
                self.assertNotIn(signature,signatures)
                signatures.add(signature)
                rowhash=sha256(json.dumps(
                    rows,separators=(',',':')).encode()).hexdigest()
                key=f'{law}-{seed}'
                meta=dict(version=raw['version'],law=law,seed=seed,
                    split=raw['split'],parameters=raw['parameters'],
                    rows_digest=rowhash,source_pattern_digest=signature,
                    worlds=len(rows),chunks=len(rows)//CHUNK,
                    cpu_seconds=raw['cpu_seconds'])
                print('G5_V8_RAW_META '+key+' '+
                      json.dumps(meta,separators=(',',':'),sort_keys=True),flush=True)
                for i in range(len(rows)//CHUNK):
                    block=rows[i*CHUNK:(i+1)*CHUNK]
                    print('G5_V8_RAW_CHUNK '+key+' '+str(i)+' '+
                          json.dumps(block,separators=(',',':')),flush=True)
        self.assertEqual(len(seen),1920)
        self.assertEqual(len(signatures),10)
        self.assertEqual(len(v6_ids),1920)
        self.assertEqual(len(v7_ids),1920)
        self.assertFalse(seen&v6_ids)
        self.assertFalse(seen&v7_ids)
        print('G5_V8_RAW_AUDIT '+json.dumps({
            'worlds':len(seen),'matched_pairs':len(seen)//2,
            'v6_id_overlap':len(seen&v6_ids),
            'v7_id_overlap':len(seen&v7_ids),
            'source_signatures':len(signatures),
            'physical_payoff_forecasts':len(seen)*15,
            'correlated_meaning_views':len(seen)*5,
            'selected_payoffs_only':True,
            'oracle_truth_used_in_collection':False},sort_keys=True),flush=True)

if __name__=='__main__':
    unittest.main()
