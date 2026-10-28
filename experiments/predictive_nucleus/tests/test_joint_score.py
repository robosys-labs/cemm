"""The historical probability floor must not masquerade as true log loss."""
import json
import math
import unittest

from experiments.predictive_nucleus.joint_score import joint_log_loss, summarize_joint_log_loss
from experiments.predictive_nucleus.stress_trial import evaluate_pair
from experiments.predictive_nucleus.stress_world import StressWorld
from experiments.predictive_nucleus.tests.test_uncertainty import ToyKernel
from experiments.predictive_nucleus.uncertainty import EvidenceBelief


class JointScoreTests(unittest.TestCase):
    def test_clipped_values_do_not_hide_worse_uncapped_losses(self):
        a, b = joint_log_loss(1e-13), joint_log_loss(1e-30)
        self.assertEqual(a["clipped_log_loss"], b["clipped_log_loss"])
        self.assertTrue(a["floor_applied"] and b["floor_applied"])
        self.assertGreater(b["uncapped_log_loss"], a["uncapped_log_loss"])
        self.assertAlmostEqual(a["uncapped_log_loss"], -math.log(1e-13))

    def test_zero_is_explicit_and_json_safe_not_a_finite_log_score(self):
        scores = [joint_log_loss(0.), joint_log_loss(.5)]
        out = summarize_joint_log_loss(scores)
        self.assertEqual(out["zero_probability_count"], 1)
        self.assertEqual(out["floor_applied_count"], 1)
        self.assertTrue(out["uncapped_mean_is_infinite"])
        self.assertIsNone(out["uncapped_mean"])
        json.dumps(out, allow_nan=False)

    def test_nonzero_scores_mean_and_invalid_input(self):
        result = summarize_joint_log_loss([joint_log_loss(.5), joint_log_loss(.25)])
        self.assertAlmostEqual(result["uncapped_mean"], (math.log(2) + math.log(4)) / 2)
        self.assertFalse(result["uncapped_mean_is_infinite"])
        for bad in (-.01, 1.01, float("nan"), float("inf"), True):
            with self.assertRaises(ValueError):
                joint_log_loss(bad)

    def test_evaluator_reports_a_represented_zero_separately_from_legacy_nll(self):
        world = StressWorld(("A", "B", "C"), (1, 1, 0), 0, "bilateral_flip")
        initial = {"t": 0, "measurements": [{"id": name, "bit": bit}
                                                for name, bit in zip(world.ids, world.bits)]}
        rows = evaluate_pair(EvidenceBelief(ToyKernel(), initial), world, ("A", "B"))
        for row in rows:
            self.assertAlmostEqual(row["joint_nll"], -math.log(1e-12))  # frozen legacy field
            self.assertTrue(row["joint_log_score"]["zero_probability"])
            self.assertTrue(row["joint_log_score"]["floor_applied"])
            self.assertIsNone(row["joint_log_score"]["uncapped_log_loss"])


if __name__ == "__main__":
    unittest.main()
