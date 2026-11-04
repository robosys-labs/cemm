"""V4 TRAIN boundary experiment: stop at protocol, never open G5 challenge."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus.revision_boundary_v4 import RATES,run


class BoundaryAudit(unittest.TestCase):
    def test_full_grid_retains_v3_without_challenge_access(self):
        from experiments.predictive_nucleus.transfer_task import catalogue
        frozen=json.loads((Path(__file__).resolve().parents[1]/
                          'results/revision-v3/train-diagnosis.json').read_text())['results']
        with patch('experiments.predictive_nucleus.transfer_task.catalogue',
                   wraps=catalogue) as seen:
            report=run()
        self.assertEqual(len(seen.call_args_list),10)
        self.assertTrue(all(call.args[1]=='train' for call in seen.call_args_list))
        self.assertEqual(set(report),set(frozen))
        total_confident_pairs=0
        for key,item in report.items():
            self.assertEqual(item['matched_prefix_pairs'],96)
            self.assertEqual(len(item['grid']),len(RATES))
            old=frozen[key]['grid']['0.0025']
            boundary=item['grid']['0.0025']
            self.assertAlmostEqual(boundary['balanced_mean_nll'],
                                   old['balanced_nll'],places=12)
            self.assertEqual(boundary['pre_confident_pairs'],
                             old['audit']['pre']['confident_pairs'])
            self.assertEqual(boundary['post']['confident'],
                             old['audit']['post']['confident'])
            self.assertEqual(boundary['retain']['confident'],
                             old['audit']['retain']['confident'])
            for rate in RATES:
                grid=item['grid'][str(rate)]
                self.assertEqual(grid['pre']['observations'],192)
                self.assertEqual(grid['post']['observations'],192)
                self.assertEqual(grid['retain']['observations'],576)
                self.assertEqual(grid['no_info']['trials'],192)
            total_confident_pairs+=boundary['pre_confident_pairs']
        self.assertEqual(total_confident_pairs,54)
        print('G5_V4_BOUNDARY_TRAIN '+json.dumps(report,sort_keys=True),flush=True)


if __name__=='__main__':
    unittest.main()
