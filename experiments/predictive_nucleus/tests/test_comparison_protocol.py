"""Frozen public diagnostic contract; no substantive fit or prediction scoring."""
from hashlib import sha256
import json
from pathlib import Path
import unittest

import torch
from experiments.predictive_nucleus import comparison_data as d
from experiments.predictive_nucleus import informative_curriculum as c
from experiments.predictive_nucleus import joint_objective as j

ROOT = Path(d.__file__).parent
NAME = 'common_objective_comparison_protocol_v1.json'
DIGEST = '15732afe065f19f3b412a7638e386373eb586ddaa273104e2de63c14a782b1f3'


class ComparisonProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads((ROOT / NAME).read_text())
        cls.data = {(info, comp): j.batch_histories(d.histories(informative=info, composition=comp))
                    for info in (False, True) for comp in (False, True)}

    def test_protocol_lock_and_all_declared_sources_are_exact(self):
        self.assertEqual(sha256((ROOT / NAME).read_bytes()).hexdigest(), DIGEST)
        self.assertEqual((ROOT / 'snapshots' / 'common_objective_comparison_protocol_v1.sha256').read_text(),
                         f'{DIGEST}  {NAME}\n')
        for name, digest in self.protocol['source_sha256'].items():
            self.assertEqual(sha256((ROOT / name).read_bytes()).hexdigest(), digest, name)

    def test_four_realized_datasets_match_the_frozen_inputs(self):
        for (info, comp), batch in self.data.items():
            name = ('informative' if info else 'uninformative') + ('_second_pair' if comp else '_same_pair')
            self.assertEqual(batch.digest(), self.protocol['data']['input_sha256'][name])
            self.assertEqual(batch.actions.shape[0] * batch.actions.shape[1], 12288)

    def test_paired_query_truth_is_identical_across_information_conditions(self):
        for comp in (False, True):
            a, b = self.data[False, comp], self.data[True, comp]
            self.assertTrue(torch.equal(a.actions[2:], b.actions[2:]))
            self.assertTrue(torch.equal(a.observations[6:], b.observations[6:]))

    def test_arm_inventory_parameters_and_fit_counts_are_fixed(self):
        spec = self.protocol
        self.assertEqual(spec['seeds'], [7, 11, 23, 37, 53])
        self.assertEqual([m['id'] for m in spec['models']], list(c.model_factories()))
        with torch.random.fork_rng(devices=[]):
            for item in spec['models']:
                self.assertEqual(sum(p.numel() for p in c.model_factories()[item['id']]().parameters()), item['parameters'])
        self.assertEqual(len(spec['seeds']) * len(spec['models']) * len(spec['data']['conditions']) *
                         len(spec['fit']['regimes']), spec['fit']['total_neural_fits'])
        self.assertEqual(spec['fit']['regimes'][0]['updates'], 128)
        self.assertEqual(spec['fit']['regimes'][1]['cpu_seconds'], 2.0)

    def test_freeze_is_not_execution_or_gate_admission(self):
        self.assertEqual(self.protocol['status'], 'FROZEN_PUBLIC_DIAGNOSTIC_NOT_RUN')
        self.assertEqual(self.protocol['gate_g1'], 'HOLD_REVISE')
        self.assertEqual(self.protocol['execution']['runner_status'], 'NOT_IMPLEMENTED_OR_REVIEWED_BY_THIS_PROTOCOL')


if __name__ == '__main__':
    unittest.main()
