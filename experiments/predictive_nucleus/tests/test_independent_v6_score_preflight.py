"""TRAIN-only scorer preflight; fixes evaluator plumbing before challenge custody.

This is a software validation fixture. TRAIN scores are not research
generalization or G5 admission evidence.
"""
import json
import unittest
from unittest.mock import patch
from experiments.predictive_nucleus.independent_collection_v6 import collect
from experiments.predictive_nucleus.independent_score_v6 import score, ARMS
from experiments.predictive_nucleus.independent_task_v6 import episodes, inventory
from experiments.predictive_nucleus.transfer_task import catalogue
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'results/independent-v6'

class IndependentScorePreflight(unittest.TestCase):
    def test_train_evaluator_and_query_semantics_without_challenge(self):
        fit=json.loads((ROOT/'train-fitted.json').read_text())['fit']
        bank=catalogue('nand','train')
        with patch('experiments.predictive_nucleus.independent_collection_v6.episodes',
                   side_effect=lambda law,seed,split,source: episodes(law,seed,'train',source)):
            raw=collect('nand',7,bank,fit)
        raw=json.loads(json.dumps(raw))  # actual immutable JSON wire format
        with patch('experiments.predictive_nucleus.independent_score_v6.inventory',
                   side_effect=lambda law,seed,split,source: inventory(law,seed,'train',source)):
            report=score(raw,'nand',7,bank,fit)
        self.assertEqual(report['payoff']['n'],2880)
        self.assertEqual(report['payoff']['epoch_n'],192)
        self.assertEqual(sum(z['observations'] for z in report['sources'].values()),2880)
        self.assertEqual(sum(z['episodes'] for z in report['epoch_change'].values()),192)
        self.assertEqual(set(report['arms']),set(ARMS))
        for arm,metrics in report['arms'].items():
            self.assertEqual(metrics['episodes'],192)
            self.assertEqual(metrics['action_count'],384)
            self.assertEqual(metrics['belief_cases'],960)
            self.assertLessEqual(metrics['queries'],192)
            self.assertGreaterEqual(metrics['optimal_actions'],0)
            self.assertLessEqual(metrics['optimal_actions'],384)
        print('G5_V6_TRAIN_SCORE_PREFLIGHT '+json.dumps(
            {'worlds':192,'payoffs':report['payoff']['n'],'correct_scope_inventory':True,
             'policy_arms':list(ARMS),
             'WARNING':'TRAIN-only scorer plumbing, not challenge research evidence'},
            sort_keys=True),flush=True)

if __name__=='__main__':
    unittest.main()
