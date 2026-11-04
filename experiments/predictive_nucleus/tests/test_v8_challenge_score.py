"""Evaluate ONLY previously sealed v8 raw forecasts, never re-fit or collect.

Collector and full source snapshot were frozen before the raw commit.
This test is first authored strictly after raw seal, and joins hidden
meaning/source-mode labels solely inside the evaluator.
"""
from hashlib import sha256
import json
from pathlib import Path
import unittest

from experiments.predictive_nucleus.independent_score_v8 import score,assess
from experiments.predictive_nucleus.independent_task_v8 import LAWS,SEEDS
from experiments.predictive_nucleus.independent_collection_v8 import ARMS
from experiments.predictive_nucleus.transfer_task import catalogue,split_audit

ROOT=Path(__file__).resolve().parents[1]/'results/independent-v8'
RAW_COMMIT='21324519573b917af4ab1e13ed2b45027b7ef513'
FIT_COMMIT='4c3a9d5ee63e824029b48a9cb32235a9e46964c5'
SOURCE_COMMIT='771c66df1ce6a15c16ead6b279367594bfbccdce'
COLLECTOR_COMMIT='d0ee3fdd70cf8cfc1b81514f1d67eebe5ab478d4'

class SealedV8Scorer(unittest.TestCase):
    def test_prespecified_source_shift_and_twin_gates(self):
        train=json.loads((ROOT/'train-locked.json').read_text())
        manifest=json.loads((ROOT/'raw/manifest.json').read_text())
        self.assertTrue(RAW_COMMIT)
        self.assertEqual(train['stage'],'TRAIN_ONLY_NO_V8_TEST_OPENED')
        self.assertFalse(train['challenge_opened'])
        self.assertEqual(train['new_v8_fitted_parameters'],0)
        self.assertEqual(train['model_generator_collector_scorer_train_test_commit'],SOURCE_COMMIT)
        self.assertEqual(manifest['stage'],'COLLECTED_NOT_SCORED')
        self.assertEqual(manifest['train_locked_commit'],FIT_COMMIT)
        self.assertEqual(manifest['frozen_source_and_preflight_commit'],SOURCE_COMMIT)
        self.assertEqual(manifest['collection_driver_commit'],COLLECTOR_COMMIT)
        self.assertFalse(manifest['oracle_truth_used_in_collection'])
        self.assertEqual(manifest['worlds'],1920)
        self.assertEqual(manifest['matched_pairs'],960)
        self.assertEqual(manifest['physical_payoff_forecasts'],28800)
        self.assertEqual(manifest['hosted_tests_passed'],1234)
        self.assertEqual(manifest['public_id_overlap_with_v6'],0)
        self.assertEqual(manifest['public_id_overlap_with_v7'],0)
        self.assertEqual(len(manifest['files']),10)
        reports=[]
        for law in LAWS:
            self.assertFalse(any(split_audit(law)['physical_overlap'].values()))
            bank=catalogue(law,'challenge')
            for seed in SEEDS:
                key=f'{law}-{seed}'
                entry=manifest['files'][key]
                raw=json.loads((ROOT/'raw'/f'{key}.json').read_text())
                self.assertEqual(raw['law'],law)
                self.assertEqual(raw['seed'],seed)
                self.assertEqual(len(raw['rows']),192)
                self.assertEqual(entry['worlds'],192)
                self.assertEqual(entry['pairs'],96)
                sha=sha256(json.dumps(raw['rows'],separators=(',',':')).encode()).hexdigest()
                self.assertEqual(sha,entry['row_digest'])
                report=score(raw,law,seed,bank)
                self.assertEqual(report['twin_pairs'],96)
                self.assertEqual(report['premature_confident_twin_pairs'],0)
                self.assertEqual(set(report['arms']),set(ARMS))
                self.assertEqual(report['mode']['n'],192)
                self.assertEqual(report['payoff']['joint']['total']['n'],2880)
                self.assertEqual(report['payoff']['frozen_v7']['total']['n'],2880)
                for arm,metrics in report['arms'].items():
                    self.assertEqual(metrics['belief_cases'],960)
                    self.assertEqual(metrics['action_count'],384)
                    self.assertEqual(metrics['episodes'],192)
                    self.assertTrue(0<=metrics['mean_brier']<=1)
                    self.assertTrue(0<=metrics['optimal_rate']<=1)
                    self.assertTrue(0<=metrics['queries']<=192)
                print('G5_V8_SCORED '+key+' '+
                      json.dumps(report,separators=(',',':'),sort_keys=True),flush=True)
                reports.append(report)
        result=assess(reports)
        self.assertEqual(result['worlds'],1920)
        self.assertEqual(result['matched_twin_pairs'],960)
        self.assertEqual(result['premature_confident_pairs'],0)
        self.assertFalse(result['g5_scientific_admission'])
        self.assertIn(result['decision'],('KEEP_JOINT_V8_DEVELOPMENT','REVISE_JOINT_V8'))
        self.assertEqual(set(result['per_seed_goal_net_action']),{'7','11','23','37','53'})
        self.assertEqual(len(result['gates']),13)
        print('G5_V8_DECISION '+
              json.dumps(result,separators=(',',':'),sort_keys=True),flush=True)

if __name__=='__main__':
    unittest.main()
