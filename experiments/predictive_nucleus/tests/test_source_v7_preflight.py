"""TRAIN-only v7 collector/scorer preflight; no hidden challenge reads."""
import json
import unittest
from unittest.mock import patch
from experiments.predictive_nucleus import independent_collection_v7 as collection
from experiments.predictive_nucleus import independent_score_v7 as scoring
from experiments.predictive_nucleus.independent_task_v7 import episodes,inventory
from experiments.predictive_nucleus.transfer_task import catalogue

class V7BeforeSealPreflight(unittest.TestCase):
    def test_train_only_collection_and_evaluator(self):
        # Dummy prefit scalars exercise implementation, not training selection.
        freeze={'fit':{'h':.15,'e_A':.03,'e_B':.2},
                'rule':{'delta':.1},'neutral':{'h':.15,'e':.1}}
        bank=catalogue('nand','train')
        with patch.object(collection,'episodes',side_effect=lambda law,seed,split,b:
                          episodes(law,seed,'train',b)):
            raw=collection.collect('nand',7,bank,freeze)
            again=collection.collect('nand',7,bank,freeze)
        self.assertEqual(raw['rows'],again['rows'])
        self.assertEqual(len(raw['rows']),192)
        self.assertEqual(len(raw['rows'][0]['beliefs'][0]),6)
        self.assertEqual(len(raw['rows'][0]['v6_payoff_p']),15)
        self.assertEqual(len(raw['rows'][0]['sensor_payoff_p']),15)
        wire=json.loads(json.dumps(raw))
        with patch.object(scoring,'inventory',side_effect=lambda law,seed,split,b:
                          inventory(law,seed,'train',b)):
            output=scoring.score(wire,'nand',7,bank,freeze)
        self.assertEqual(set(output['arms']),set(collection.ARMS))
        self.assertEqual(output['arms']['source_temporal']['action_count'],384)
        self.assertEqual(output['arms']['rule_smoothed']['belief_cases'],960)
        self.assertEqual(output['payoff']['source_temporal']['total']['n'],2880)
        self.assertEqual(set(output['subgroups']).issubset(
            {'stable_A','stable_B','flip_A','flip_B'}),True)
        print('G5_V7_TRAIN_PREFLIGHT '+json.dumps({
            'stage':'TRAIN_ONLY','rows':192,'payoffs':2880,
            'arms':list(collection.ARMS),
            'collector_is_deterministic':True},sort_keys=True),flush=True)

if __name__=='__main__':
    unittest.main()
