"""Frozen G5 v3 TRAIN-only diagnosis; failure is a scientific result, not a code failure."""
import json
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus.revision_objective_v3 import GRID, run


class BalancedObjectiveDiagnostic(unittest.TestCase):
    def test_complete_train_only_grid_and_controls(self):
        from experiments.predictive_nucleus.transfer_task import catalogue
        with patch('experiments.predictive_nucleus.transfer_task.catalogue',
                   wraps=catalogue) as watched:
            results=run()
        self.assertEqual(len(results),10)
        self.assertEqual(len(watched.call_args_list),10)  # one call per law/seed
        self.assertTrue(all(call.args[1]=='train' for call in watched.call_args_list))
        total_previous=0
        for key,record in results.items():
            self.assertTrue(record['train_only'])
            self.assertEqual(record['matched_prefix_pairs'],96)
            self.assertEqual(record['rows'],{'pre':192,'post':192,'retain':576})
            self.assertIn(record['balanced_switch'],GRID)
            self.assertIn(record['v2_switch'],GRID)
            self.assertEqual(len(record['grid']),8)
            total_previous+=record['grid'][str(record['v2_switch'])]['audit']['pre']['confident_pairs']
            self.assertEqual(record['v1_rule_audit']['pre']['confident_pairs'],0)
            self.assertEqual(record['v1_rule_audit']['post']['confident'],192)
            self.assertEqual(record['v1_rule_audit']['post']['wrong_confident'],0)
            self.assertEqual(record['v1_rule_audit']['retain']['confident'],576)
            self.assertEqual(record['v1_rule_audit']['retain']['wrong_confident'],0)
        self.assertEqual(total_previous,864)  # unchanged original TRAIN failure
        print('G5_V3_TRAIN_OBJECTIVE '+json.dumps(results,sort_keys=True),flush=True)


if __name__=='__main__':
    unittest.main()
