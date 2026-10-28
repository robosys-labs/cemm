"""Paired update-budget ablation invariants, no scientific challenge."""
import unittest
from copy import deepcopy
from itertools import product

from experiments.predictive_nucleus.flat_data import initial_ids
from experiments.predictive_nucleus.flat_updates_trial import evaluate_pair, frozen_config_v8
from experiments.predictive_nucleus.tests.test_uncertainty import ToyKernel


class UniformFlat:
    def reset(self, anchor, *, sensor_error_rate):
        self.ids = initial_ids(anchor)
        self.time = anchor["t"]
        self.pending = False

    def commit(self, action, *, temperature):
        if self.pending:
            raise RuntimeError("missing feedback")
        self.pending = True

    def receive(self, observation):
        if not self.pending or observation["t"] != self.time + 1:
            raise RuntimeError("nonsequential feedback")
        self.time += 1
        self.pending = False

    def preview(self, action, *, temperature):
        if self.pending:
            raise RuntimeError("pending feedback")
        states = list(product((0, 1), repeat=len(self.ids)))
        return {state: 1 / len(states) for state in states}, None


class FlatUpdateTests(unittest.TestCase):
    def test_locked_new_protocol_uses_separate_worlds(self):
        cfg = frozen_config_v8()
        self.assertEqual(cfg["canonical_budget"]["structured_steps"], 200)
        self.assertEqual(cfg["canonical_budget"]["equal_flat_steps"], 200)
        self.assertTrue(set(cfg["opened_v7_world_seeds"]).isdisjoint(cfg["new_public_world_seeds"]))
        self.assertEqual(cfg["decision"], "G1_NOT_ADMITTED")

    def test_pair_uses_identical_public_trajectory_and_reports_transitions(self):
        cfg = deepcopy(frozen_config_v8())
        # Unit fixtures do not generate either locked development split.
        cfg["opened_v7_world_seeds"] = [1151]
        cfg["new_public_world_seeds"] = [1153]
        out = evaluate_pair(ToyKernel(), UniformFlat(), 1., UniformFlat(), 1., cfg, 1)
        for split in out.values():
            for result in split.values():
                self.assertEqual(result["wall_flat"], result["equal_update_flat"])
                self.assertEqual(result["equal_update_repairs"], [])
                self.assertEqual(result["equal_update_regressions"], [])
                self.assertEqual(len(result["public_trajectory_digests"]), 1)
                self.assertEqual(len(result["public_trajectory_digests"][0]["sha256"]), 64)
                self.assertLessEqual(result["mean_physical_probes"], 2)


if __name__ == "__main__":
    unittest.main()
