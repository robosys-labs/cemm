"""G5 v5 evaluator-only one-shot score from ten already sealed raw banks."""
import json
from pathlib import Path
import unittest

from experiments.predictive_nucleus.temporal_audit_v5 import score
from experiments.predictive_nucleus.temporal_task_v5 import LAWS, SEEDS
from experiments.predictive_nucleus.transfer_task import catalogue, split_audit

ROOT=Path(__file__).resolve().parents[1]/'results/temporal-v5'


class TemporalV5HeldoutScoring(unittest.TestCase):
    def test_score_only_frozen_forecasts_without_retraining(self):
        fits=json.loads((ROOT/'train-fitted.json').read_text())
        manifest=json.loads((ROOT/'raw/manifest.json').read_text())
        self.assertEqual(manifest['status'],'COLLECTED_UNSCORED')
        self.assertEqual(manifest['parent_commit'],
                         'eabfd43f9c279c4f6a1c6fb5ec9fafdc3a10ce6c')
        self.assertEqual(len(manifest['files']),10)
        self.assertEqual(len(fits['fits']),10)
        for law in LAWS:
            separation=split_audit(law)
            self.assertFalse(any(separation['physical_overlap'].values()))
            held=catalogue(law,'challenge')
            for seed in SEEDS:
                key=f'{law}-{seed}'
                raw=json.loads((ROOT/'raw'/f'{key}.json').read_text())
                report=score(raw,law,seed,held,fits['fits'][key])
                summary=report['totals']
                self.assertEqual(summary['episodes'],192)
                self.assertEqual(summary['contexts'],960)
                self.assertEqual(summary['pre_twin_pairs'],96)
                self.assertEqual(summary['causal_payoffs'],2880)
                for arm in ('temporal','scoped_rule','latest','v4_scalar','no_memory'):
                    self.assertEqual(summary[f'{arm}_1_questions'],0)
                    self.assertEqual(summary[f'{arm}_2_questions'],0)
                print('G5_V5_SCORED '+key+' '+
                      json.dumps(report,separators=(',',':'),sort_keys=True),
                      flush=True)


if __name__=='__main__':
    unittest.main()
