"""Causal sensor-context invariants; no held-out challenge is exercised."""
import unittest
from copy import deepcopy

from experiments.predictive_nucleus.context_support import ObservedContextSupport
from experiments.predictive_nucleus.context_trial import evaluate_kernel, frozen_config_v6
from experiments.predictive_nucleus.stress_trial import rollout
from experiments.predictive_nucleus.stress_world import StressWorld
from experiments.predictive_nucleus.tests.test_uncertainty import ToyKernel


ANCHOR = {"t": 0, "measurements": [
    {"id": "A", "bit": 1}, {"id": "B", "bit": 0}, {"id": "C", "bit": 0}]}
AB = {"kind": "contact", "participants": ["A", "B"]}
AC = {"kind": "contact", "participants": ["A", "C"]}


class ObservedContextTests(unittest.TestCase):
    def test_only_received_complete_contact_creates_context_support(self):
        support = ObservedContextSupport(ANCHOR)
        self.assertEqual(support.assess(AB)["status"], "UNTESTED_CONTEXT")
        support.commit_action(AB, intended_sensor_ids=("A", "B"), next_time=1)
        with self.assertRaises(RuntimeError):
            support.assess(AB)
        support.receive({"t": 1, "measurements": [
            {"id": "A", "bit": 1}, {"id": "B", "bit": 1}]}, "one")
        # Same entity pair at (1,1) is not a witnessed (1,0) context.
        self.assertEqual(support.assess(AB)["status"], "UNTESTED_CONTEXT")
        # Same ordered input context on different same-kind entities is shared.
        self.assertEqual(support.assess(AC), {"supported": True, "status": "OBSERVED_CONTEXT",
                                               "observed_events": 1})
        self.assertEqual(support.assess({"kind": "contact", "participants": ["C", "A"]})["status"],
                         "UNTESTED_CONTEXT")

    def test_dropout_invalidates_acted_inputs_and_does_not_mark_support(self):
        support = ObservedContextSupport(ANCHOR)
        support.commit_action(AB, intended_sensor_ids=("A", "B"), next_time=1)
        support.receive({"t": 1, "measurements": [{"id": "A", "bit": 1}]}, "drop")
        self.assertEqual(support.assess(AB)["status"], "UNOBSERVED_INPUT")
        self.assertEqual(support.assess(AC)["status"], "UNTESTED_CONTEXT")

    def test_duplicate_and_out_of_order_receipts_cannot_inflate_support(self):
        support = ObservedContextSupport(ANCHOR)
        support.commit_action(AB, intended_sensor_ids=("A", "B"), next_time=1)
        obs = {"t": 1, "measurements": [{"id": "A", "bit": 1}, {"id": "B", "bit": 1}]}
        with self.assertRaises(ValueError):
            support.receive({"t": 2, "measurements": []}, "future")
        self.assertIsNotNone(support.pending)
        support.receive(obs, "one")
        support.receive(deepcopy(obs), "one")
        self.assertEqual(support.assess(AC)["observed_events"], 1)
        with self.assertRaises(ValueError):
            support.receive({"t": 1, "measurements": [{"id": "A", "bit": 0}]}, "one")
        with self.assertRaises(RuntimeError):
            support.receive(obs, "different-id")
        self.assertEqual(support.assess(AC)["observed_events"], 1)

    def test_no_uncommitted_postcondition_or_outside_coverage(self):
        support = ObservedContextSupport(ANCHOR)
        support.commit_action(AB, intended_sensor_ids=("A",), next_time=1)
        with self.assertRaises(ValueError):
            support.receive({"t": 1, "measurements": [{"id": "B", "bit": 1}]}, "outside")
        support.receive({"t": 1, "measurements": [{"id": "A", "bit": 1}]}, "actual")
        self.assertEqual(support.assess(AC)["status"], "UNTESTED_CONTEXT")
        self.assertEqual(support.assess(AB)["status"], "UNOBSERVED_INPUT")

    def test_set_feedback_is_not_fabricated_contact_support(self):
        support = ObservedContextSupport(ANCHOR)
        set_action = {"kind": "set", "participants": ["A"], "value": 1}
        support.commit_action(set_action, intended_sensor_ids=("A",), next_time=1)
        support.receive({"t": 1, "measurements": [{"id": "A", "bit": 1}]}, "set")
        self.assertEqual(support.assess(AB)["status"], "UNTESTED_CONTEXT")
        self.assertEqual(support.assess(set_action)["status"], "UNSUPPORTED_ACTION")

    def test_rollout_context_is_a_subset_of_guard_with_identical_cost(self):
        world = StressWorld(("A", "B", "C"), (1, 0, 0), 0, "reference")
        result = rollout(world, ToyKernel(), scenario="reference_clean", policy="active_validate", seed=71)
        self.assertLessEqual(result["probes"], 2)
        self.assertEqual(len(result["rows"]), 2)
        for row in result["rows"]:
            self.assertFalse(row["context_eligible"] and not row["guard_eligible"])
        self.assertEqual(world.bits, (1, 0, 0))

    def test_v6_lock_and_separate_synthetic_lineages(self):
        cfg = deepcopy(frozen_config_v6())
        # Never execute a locked diagnostic lineage during the unit test.
        cfg["opened_v5_world_seeds"] = [951]
        cfg["new_public_world_seeds"] = [953]
        data = evaluate_kernel(ToyKernel(), cfg, 1)
        self.assertEqual(set(data), {"opened_v5", "new_public_v6"})
        for split in data.values():
            for summary in split.values():
                self.assertEqual(summary["target_queries"], 2)
                self.assertEqual(summary["newly_covered_wrong"], [])
                self.assertEqual(summary["newly_covered_correct"], [])


if __name__ == "__main__":
    unittest.main()
