"""Temporal change-point/falsification contract, no held-out challenge open."""
import unittest
from experiments.predictive_nucleus.stability_trial import frozen_config
from experiments.predictive_nucleus.stress_world import StressWorld
from experiments.predictive_nucleus.stress_trial import rollout
from experiments.predictive_nucleus.tests.test_uncertainty import ToyKernel


class StabilityTests(unittest.TestCase):
    def test_new_public_world_seed_lineage_is_disjoint(self):
        cfg = frozen_config()
        seen = set(cfg["gates"]["new_world_seeds"])
        old = set((601, 607, 613, 617, 619))
        sealed = set((401, 409, 419, 421, 431, 503, 509, 521, 523, 541))
        self.assertFalse(seen & (old | sealed))
        self.assertEqual(len(seen), 5)
        self.assertEqual(cfg["decision"], "NOT_RUN_NO_G1_ADMISSION")

    def test_two_step_mechanism_validation_has_extra_probe_cost(self):
        world = StressWorld(("A", "B", "C"), (1, 0, 0), 0, "switch_orientation")
        vanilla = rollout(world, ToyKernel(), scenario="switch_orientation",
                          policy="active", seed=71, budget=2)
        validated = rollout(world, ToyKernel(), scenario="switch_orientation",
                            policy="active_validate", seed=71, budget=2)
        self.assertLessEqual(vanilla["probes"], validated["probes"])
        self.assertGreaterEqual(validated["verification_probes"], 1)
        self.assertEqual(validated["probes"], 2)
        self.assertEqual(world.contact_count, 0)

    def test_monitor_probes_not_treated_as_hypothetical_gold(self):
        world = StressWorld(("A", "B", "C"), (1, 0, 0), 0, "reference")
        checked = rollout(world, ToyKernel(), scenario="reference_clean",
                          policy="active_validate", seed=71, budget=2)
        self.assertFalse(checked["alarm"])
        self.assertFalse(checked["change_point_alarm"])
        self.assertEqual(len(checked["rows"]), 2)


if __name__ == "__main__":
    unittest.main()
