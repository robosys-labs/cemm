"""G5 v7: evaluate only already sealed raw, with no recollection or refit.

The collector, generator, learner, scorer and fitted parameters were committed
before immutable TEST forecasts at RAW_COMMIT. Score all ten conditions once.
"""
import json
import unittest
from hashlib import sha256
from pathlib import Path
from experiments.predictive_nucleus.independent_score_v7 import score,assess,ARMS
from experiments.predictive_nucleus.independent_task_v7 import LAWS,SEEDS,REGIME
from experiments.predictive_nucleus.transfer_task import catalogue,split_audit

ROOT=Path(__file__).resolve().parents[1]/'results/independent-v7'
RAW_COMMIT='79a62ce8dc25b5421672a0a0b77d8f1f27866dd3'
FITTED_COMMIT='9dcb3e0be3b9090d0a7f57b60cc470744ad6c2c7'
CODE_SHA='a772d23570848ff51517fc481c2b22f996f0109b'
COLLECTION_DRIVER='c6c7c632d228b0614003dba07a0eac7ee7f2db3d'

class SealedV7Scoring(unittest.TestCase):
    def test_unchanged_forecasts_and_prospective_decision(self):
        fitted=json.loads((ROOT/'train-fitted.json').read_text())
        manifest=json.loads((ROOT/'raw/manifest.json').read_text())
        self.assertTrue(RAW_COMMIT)
        self.assertEqual(fitted['stage'],'TRAIN_ONLY')
        self.assertFalse(fitted['challenge_opened'])
        self.assertEqual(fitted['frozen_source_test_commit'],CODE_SHA)
        self.assertEqual(manifest['stage'],'COLLECTED_NOT_SCORED')
        self.assertEqual(manifest['fit_commit'],FITTED_COMMIT)
        self.assertEqual(manifest['frozen_scientific_source_commit'],CODE_SHA)
        self.assertEqual(manifest['collection_driver_commit'],COLLECTION_DRIVER)
        self.assertFalse(manifest['oracle_truth_used_in_collection'])
        self.assertEqual(manifest['hosted_full_software_tests_passed'],1229)
        self.assertEqual(manifest['public_world_id_overlap_with_v6'],0)
        self.assertEqual(manifest['distinct_source_signatures'],10)
        self.assertEqual(manifest['worlds_total'],1920)
        self.assertEqual(manifest['physical_forecasts_total'],28800)
        self.assertEqual(manifest['meaning_views_total'],9600)
        self.assertEqual(len(manifest['files']),10)
        reports=[]
        for law in LAWS:
            split=split_audit(law)
            self.assertFalse(any(split['physical_overlap'].values()))
            bank=catalogue(law,'challenge')
            for seed in SEEDS:
                key=f'{law}-{seed}'
                entry=manifest['files'][key]
                self.assertEqual(entry['regime'],REGIME[seed])
                self.assertEqual(entry['worlds'],192)
                raw=json.loads((ROOT/'raw'/f'{key}.json').read_text())
                self.assertEqual(raw['version'],'g5-v7-raw')
                self.assertEqual(raw['split'],'challenge')
                self.assertEqual(raw['law'],law)
                self.assertEqual(raw['seed'],seed)
                raw_rows_sha=sha256(json.dumps(raw['rows'],separators=(',',':')).encode()).hexdigest()
                self.assertEqual(raw_rows_sha,entry['rows_digest'])
                self.assertEqual(len(raw['rows']),192)
                self.assertEqual(len({r['id'] for r in raw['rows']}),192)
                report=score(raw,law,seed,bank,fitted)
                self.assertEqual(set(report['arms']),set(ARMS))
                self.assertEqual(report['regime'],REGIME[seed])
                for arm,metrics in report['arms'].items():
                    self.assertEqual(metrics['belief_cases'],960)
                    self.assertEqual(metrics['action_count'],384)
                    self.assertEqual(metrics['episodes'],192)
                    self.assertGreaterEqual(metrics['optimal_actions'],0)
                    self.assertLessEqual(metrics['queries'],192)
                    self.assertTrue(0<=metrics['mean_brier']<=1)
                self.assertEqual(report['payoff']['source_temporal']['total']['n'],2880)
                self.assertEqual(report['payoff']['sensor_neutral']['total']['n'],2880)
                self.assertEqual(report['payoff']['v6_frozen']['total']['n'],2880)
                print('G5_V7_SCORED '+key+' '+json.dumps(
                    report,separators=(',',':'),sort_keys=True),flush=True)
                reports.append(report)
        self.assertEqual(len(reports),10)
        decision=assess(reports)
        self.assertEqual(decision['worlds'],1920)
        self.assertFalse(decision['g5_scientific_admission'])
        self.assertEqual(set(decision['per_seed_net_action']),{'7','11','23','37','53'})
        self.assertIn(decision['decision'],('KEEP_SOURCE_V7_DEVELOPMENT','REVISE_SOURCE_V7'))
        print('G5_V7_DECISION '+json.dumps(
            decision,separators=(',',':'),sort_keys=True),flush=True)

if __name__=='__main__':
    unittest.main()
