"""Single frozen G5 v5 challenge collection; NO evaluator scoring.

Only the ten previously published TRAIN fitted settings are read. Output
is chunked for reliable archival of every forecast before scoring.
"""
import json
from pathlib import Path
import unittest

from experiments.predictive_nucleus.temporal_audit_v5 import collect
from experiments.predictive_nucleus.temporal_task_v5 import LAWS, SEEDS
from experiments.predictive_nucleus.transfer_task import catalogue

FIT_PATH=(Path(__file__).resolve().parents[1]/
          'results/temporal-v5/train-fitted.json')
CHUNK=16


class TemporalV5RawCollection(unittest.TestCase):
    def test_collect_saved_probabilities_before_evaluator_truth(self):
        frozen=json.loads(FIT_PATH.read_text())
        self.assertEqual(frozen['scope'],'TRAIN_ONLY')
        self.assertEqual(len(frozen['fits']),10)
        for law in LAWS:
            challenge=catalogue(law,'challenge')
            for seed in SEEDS:
                key=f'{law}-{seed}'
                result=collect(law,seed,challenge,frozen['fits'][key])
                self.assertEqual(len(result['rows']),192)
                self.assertTrue(all(len(row)==4 and len(row[2])==5
                                    and len(row[3])==15 for row in result['rows']))
                metadata={k:v for k,v in result.items() if k!='rows'}
                metadata['chunks']=192//CHUNK
                print('G5_V5_RAW_META '+key+' '+
                      json.dumps(metadata,separators=(',',':'),sort_keys=True),flush=True)
                for i in range(metadata['chunks']):
                    subset=result['rows'][i*CHUNK:(i+1)*CHUNK]
                    self.assertEqual(len(subset),CHUNK)
                    print('G5_V5_RAW_CHUNK '+key+' '+str(i)+' '+
                          json.dumps(subset,separators=(',',':')),flush=True)


if __name__=='__main__':
    unittest.main()
