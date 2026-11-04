"""One G5 v6 evaluation from ten previously sealed raw forecast banks."""
import json
from pathlib import Path
import unittest
from experiments.predictive_nucleus.independent_score_v6 import score, ARMS
from experiments.predictive_nucleus.independent_task_v6 import LAWS, SEEDS
from experiments.predictive_nucleus.transfer_task import catalogue, split_audit

ROOT=Path(__file__).resolve().parents[1]/'results/independent-v6'
RAW_COMMIT='3f0d247d88c51132ff63e1fde34dfca1b45747ab'

class ProspectiveIndependentScorer(unittest.TestCase):
    def test_proper_meaning_and_goal_costs_only_after_raw_seal(self):
        fit=json.loads((ROOT/'train-fitted.json').read_text())
        manifest=json.loads((ROOT/'raw/manifest.json').read_text())
        self.assertEqual(manifest['stage'],'COLLECTED_NOT_SCORED')
        self.assertEqual(manifest['collector_commit'],
                         '9e738c9899f6cf173f9e0fe40dca497b12766707')
        self.assertEqual(len(manifest['files']),10)
        self.assertEqual(manifest['worlds_total'],1920)
        self.assertEqual(manifest['payoff_forecasts_total'],28800)
        self.assertEqual((fit['fit']['h'],fit['fit']['e']),(.15,.1))
        self.assertTrue(RAW_COMMIT)
        for law in LAWS:
            split=split_audit(law)
            self.assertFalse(any(split['physical_overlap'].values()))
            bank=catalogue(law,'challenge')
            for seed in SEEDS:
                key=f'{law}-{seed}'
                source=json.loads((ROOT/'raw'/f'{key}.json').read_text())
                report=score(source,law,seed,bank,fit['fit'])
                self.assertEqual(report['payoff']['n'],2880)
                self.assertEqual(report['payoff']['epoch_n'],192)
                self.assertEqual(sum(v['observations'] for v in
                    report['sources'].values()),2880)
                self.assertEqual(sum(v['episodes'] for v in
                    report['epoch_change'].values()),192)
                self.assertEqual(sum(bin[0] for bin in
                    report['calibration']['bins']),960)
                self.assertEqual(set(report['arms']),set(ARMS))
                for arm,item in report['arms'].items():
                    self.assertEqual(item['episodes'],192)
                    self.assertEqual(item['action_count'],384)
                    self.assertEqual(item['belief_cases'],960)
                    self.assertLessEqual(item['queries'],192)
                    self.assertGreaterEqual(item['mean_net_per_action'],-.5)
                    self.assertLessEqual(item['mean_net_per_action'],1.)
                    self.assertTrue(0<=item['mean_brier']<=1)
                print('G5_V6_SCORED '+key+' '+json.dumps(
                    report,separators=(',',':'),sort_keys=True),flush=True)

if __name__=='__main__':
    unittest.main()
