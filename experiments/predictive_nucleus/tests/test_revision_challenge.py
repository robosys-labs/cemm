"""One prospective evaluation of the previously frozen G5 task and gates."""

import json
import unittest

from experiments.predictive_nucleus.revision_study import LAWS, SEEDS, score_bank
from experiments.predictive_nucleus.transfer_task import catalogue


class RevisionChallenge(unittest.TestCase):
    def test_prespecified_heldout_correction_and_retention(self):
        results = {}
        for law in LAWS:
            held = catalogue(law, 'challenge')
            for seed in SEEDS:
                measured = score_bank(law, seed, held)
                self.assertEqual(measured['resolved'], 7680)
                self.assertEqual(measured['unresolved'], 1536)
                self.assertEqual(measured['sentinel_retained'], 9216)
                self.assertEqual(measured['policy_questions_0'], 768)
                self.assertEqual(measured['policy_questions_1'], 0)
                self.assertEqual(measured['policy_questions_2'], 0)
                self.assertGreater(measured['policy_net100_0'], measured['baseline_net100_0'])
                results[f'{law}-{seed}'] = measured
        print('G5_SCOPED_HELDOUT_REPORT ' + json.dumps(results, sort_keys=True), flush=True)
