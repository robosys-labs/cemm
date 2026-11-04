"""Single v6 challenge collection, no evaluator truth, no scorer, no refit."""
import json
from hashlib import sha256
from pathlib import Path
import unittest

from experiments.predictive_nucleus.independent_collection_v6 import collect
from experiments.predictive_nucleus.independent_task_v6 import LAWS, SEEDS
from experiments.predictive_nucleus.transfer_task import catalogue, split_audit

ROOT=Path(__file__).resolve().parents[1]/'results/independent-v6'
CHUNK=16

class FrozenIndependentCollection(unittest.TestCase):
    def test_publish_heldout_forecasts_only(self):
        freeze=json.loads((ROOT/'train-fitted.json').read_text())
        self.assertEqual(freeze['stage'],'TRAIN_ONLY')
        self.assertTrue(freeze['no_oracle_meaning_used_to_select_parameters'])
        self.assertEqual((freeze['fit']['h'],freeze['fit']['e']),(.15,.1))
        seen=set()
        signatures=set()
        for law in LAWS:
            split=split_audit(law)  # provenance only; no hidden oracle scoring
            self.assertFalse(any(split['physical_overlap'].values()))
            bank=catalogue(law,'challenge')
            for seed in SEEDS:
                key=f'{law}-{seed}'
                raw=collect(law,seed,bank,freeze['fit'])
                rows=raw['rows']
                self.assertEqual(len(rows),192)
                self.assertEqual(raw['split'],'challenge')
                self.assertTrue(all(len(r['beliefs'])==5 and len(r['payoff_p'])==15
                                    and len(r['source_ids'])==15 for r in rows))
                ids={r['id'] for r in rows}
                self.assertEqual(len(ids),192)
                self.assertFalse(ids&seen)
                seen.update(ids)
                signature=sha256(json.dumps(
                    [r['source_ids'] for r in rows],separators=(',',':')).encode()).hexdigest()
                self.assertNotIn(signature,signatures)
                signatures.add(signature)
                source_digest=sha256(json.dumps(
                    [[r['id'],r['record_hash']] for r in rows],
                    separators=(',',':')).encode()).hexdigest()
                print('G5_V6_RAW_META '+key+' '+json.dumps(
                    {'law':law,'seed':seed,'split':'challenge','n':len(rows),
                     'source_digest':source_digest,'source_pattern_digest':signature,
                     'h':raw['parameters'][0],'e':raw['parameters'][1],
                     'cpu_seconds':raw['cpu_seconds'],'chunks':len(rows)//CHUNK},
                     separators=(',',':'),sort_keys=True),flush=True)
                for i in range(len(rows)//CHUNK):
                    block=rows[i*CHUNK:(i+1)*CHUNK]
                    print('G5_V6_RAW_CHUNK '+key+' '+str(i)+' '+
                          json.dumps(block,separators=(',',':')),flush=True)
        self.assertEqual(len(seen),1920)
        self.assertEqual(len(signatures),10)

if __name__=='__main__':
    unittest.main()
