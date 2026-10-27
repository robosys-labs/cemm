"""Public stress runner controls; no scientific challenge opened."""
import unittest
from experiments.predictive_nucleus.stress_world import StressWorld
from experiments.predictive_nucleus.stress_trial import (
    SCENARIOS, WORLD_SEEDS, rollout, summarize)
from experiments.predictive_nucleus.tests.test_uncertainty import ToyKernel
from experiments.predictive_nucleus.uncertainty import EvidenceBelief


class StressPolicyTests(unittest.TestCase):
    def setUp(self):
        self.world = StressWorld(("A", "B", "C"), (1, 0, 0), 0, "reference")
        self.kernel = ToyKernel()

    def test_cost_matched_random_controls_use_exact_active_probe_budget(self):
        active = rollout(self.world, self.kernel, scenario="reference_clean",
                         policy="active", seed=71)
        random = rollout(self.world, self.kernel, scenario="reference_clean",
                         policy="random_contact", seed=71, budget=active["probes"])
        any_random = rollout(self.world, self.kernel, scenario="reference_clean",
                             policy="random_any", seed=71, budget=active["probes"])
        self.assertEqual(active["probes"], random["probes"])
        self.assertEqual(active["probes"], any_random["probes"])
        self.assertEqual(len(active["rows"]), 2)
        self.assertEqual(len(random["rows"]), 2)
        self.assertEqual(self.world.bits, (1, 0, 0))  # physical simulator remained immutable
        self.assertEqual(active["alarm"], False)

    def test_passive_has_no_probes_and_well_defined_strata(self):
        passive = rollout(self.world, self.kernel, scenario="reference_clean",
                          policy="passive", seed=17, budget=0)
        self.assertEqual(passive["probes"], 0)
        self.assertEqual(passive["probe_statuses"], [])
        summary = summarize([passive])
        self.assertEqual(summary["worlds"], 1)
        self.assertEqual(summary["target_queries"], 2)
        self.assertEqual(summary["latency_p95_ms"], None)

    def test_alternative_physics_is_evaluator_only_not_an_action_feature(self):
        world = StressWorld(("A", "B", "C"), (1, 1, 0), 0, "bilateral_flip")
        results = rollout(world, self.kernel, scenario="bilateral_flip",
                          policy="active", seed=71)
        self.assertEqual(len(results["rows"]), 2)
        self.assertTrue(all(isinstance(x["correct"], bool) for x in results["rows"]))

    def test_temporal_validation_probes_are_matched_by_actual_cost(self):
        switched = StressWorld(("A", "B", "C"), (1, 0, 0), 0, "switch_orientation")
        tested = rollout(switched, self.kernel, scenario="switch_orientation",
                         policy="active_validate", seed=71, budget=2)
        random = rollout(switched, self.kernel, scenario="switch_orientation",
                         policy="random_contact", seed=71, budget=tested["probes"])
        self.assertEqual(tested["probes"], random["probes"])
        self.assertGreaterEqual(tested["verification_probes"], 0)
        self.assertEqual(len(tested["rows"]), 2)
        self.assertEqual(switched.contact_count, 0)

    def test_probe_uses_its_own_sensor_geometry(self):
        first = {"t": 0, "measurements": [
            {"id": "A", "bit": 1}, {"id": "B", "bit": 0}, {"id": "C", "bit": 0}]}
        belief = EvidenceBelief(self.kernel, first, sensor_error_rate=.1)
        a = {"kind": "contact", "participants": ["A", "B"]}
        self.assertAlmostEqual(
            belief.choose_probe([a], sensor_ids="participants")["expected_info_gain_bits"],
            belief.preview(a, sensor_ids=("A", "B")).expected_info_gain)
        self.assertIsNone(belief.pending)

    def test_physics_and_sensor_scenarios_explicit_not_mixed_into_train(self):
        self.assertEqual(WORLD_SEEDS, (601, 607, 613, 617, 619))
        self.assertEqual(len(SCENARIOS), 7)
        self.assertEqual(SCENARIOS["reference_sensor_misspecified"][-1], .01)
        self.assertEqual(SCENARIOS["reference_sensor_misspecified"][1], .20)


if __name__ == "__main__":
    unittest.main()
