"""V8 TRAIN-only collection/evaluator plumbing; challenge remains unopened."""
import json
import unittest
from unittest.mock import patch
from experiments.predictive_nucleus import independent_collection_v8 as col
from experiments.predictive_nucleus import independent_score_v8 as sc
from experiments.predictive_nucleus.independent_task_v8 import episodes,inventory
from experiments.predictive_nucleus.transfer_task import catalogue

class V8TrainPreflight(unittest.TestCase):
    def test_paired_train_full_collector_and_scorer(self):
        bank=catalogue('nand','train')
        with patch.object(col,'episodes',side_effect=lambda law,seed,split,b:
                          episodes(law,seed,'train',b)):
            raw=col.collect('nand',7,bank)
            raw2=col.collect('nand',7,bank)
        self.assertEqual(raw['rows'],raw2['rows'])
        self.assertEqual(len(raw['rows']),192)
        self.assertEqual(len(raw['rows'][0]['beliefs']),5)
        self.assertEqual(len(raw['rows'][0]['beliefs'][0]),4)
        wire=json.loads(json.dumps(raw))
        with patch.object(sc,'inventory',side_effect=lambda law,seed,split,b:
                          inventory(law,seed,'train',b)):
            report=sc.score(wire,'nand',7,bank)
        self.assertEqual(report['twin_pairs'],96)
        self.assertEqual(report['premature_confident_twin_pairs'],0)
        self.assertEqual(set(report['arms']),set(col.ARMS))
        self.assertEqual(report['arms']['joint']['belief_cases'],960)
        self.assertEqual(report['arms']['joint']['action_count'],384)
        self.assertEqual(report['payoff']['joint']['total']['n'],2880)
        self.assertEqual(report['mode']['n'],192)
        print('G5_V8_TRAIN_EVALUATOR_PREFLIGHT '
              '{"worlds":192,"pairs":96,"joint_states":32,'
              '"oracle_only_in_train_scorer":true,"challenge_opened":false}',
              flush=True)

if __name__=='__main__':
    unittest.main()
