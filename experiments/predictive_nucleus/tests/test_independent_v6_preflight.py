"""TRAIN-only preflight of the v6 raw collector; no challenge/oracle access."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from experiments.predictive_nucleus.independent_collection_v6 import collect
from experiments.predictive_nucleus.independent_task_v6 import episodes
from experiments.predictive_nucleus.transfer_task import catalogue
from experiments.predictive_nucleus.goal_policy_v6 import public_task

ROOT=Path(__file__).resolve().parents[1]/'results/independent-v6'

class NoGoldCollectionPreflight(unittest.TestCase):
    def test_train_substitution_is_complete_and_stable(self):
        fit=json.loads((ROOT/'train-fitted.json').read_text())
        self.assertEqual(fit['stage'],'TRAIN_ONLY')
        bank=catalogue('nand','train')
        with patch('experiments.predictive_nucleus.independent_collection_v6.episodes',
                   side_effect=lambda law,seed,split,source: episodes(law,seed,'train',source)):
            raw=collect('nand',7,bank,fit['fit'])
            again=collect('nand',7,bank,fit['fit'])
        self.assertEqual(len(raw['rows']),192)
        self.assertEqual(raw['rows'],again['rows'])
        self.assertEqual(len(set(x['id'] for x in raw['rows'])),192)
        self.assertTrue(all(len(x['beliefs'])==5 and len(x['payoff_p'])==15
                            and len(x['source_ids'])==15 for x in raw['rows']))
        self.assertTrue(all(tuple(x['goals'])==public_task(x['id'])[:2]
                            for x in raw['rows']))
        self.assertTrue(all(x['fee']==public_task(x['id'])[2] for x in raw['rows']))
        print('G5_V6_TRAIN_RAW_PREFLIGHT '+json.dumps(
            {'rows':len(raw['rows']),'selected_payoff_forecasts':192*15,
             'source':'TRAIN substitution only; no challenge/oracle',
             'stable_snapshot':raw['rows']==again['rows']},
            sort_keys=True),flush=True)

if __name__=='__main__':
    unittest.main()
