"""Causal sensor-context invariants; no held-out challenge is exercised."""
import unittest
from copy import deepcopy

from experiments.predictive_nucleus.context_support import ObservedContextSupport
from experiments.predictive_nucleus.context_trial import evaluate_kernel, frozen_config_v6
from experiments.predictive_nucleus.stress_trial import rollout
from experiments.predictive_nucleus.stress_world import StressWorld
from experiments.predictive_nucleus.tests.test_uncertainty import ToyKernel
from experiments.predictive_nucleus.uncertainty import EvidenceBelief


ANCHOR = {"t": 0, "measurements": [
    {"id": "A", "bit": 1}, {"id": "B", "bit": 0}, {"id": "C", "bit": 0}]}
AB = {"kind": "contact", "participants": ["A", "B"]}
AC = {"kind": "contact", "participants": ["A", "C"]}


class IdentityKernel:
    """Deterministic test fixture, not the learned or simulator kernel."""
    def contact(self, a, b, hypothesis):
        values = [0.0] * 4
        values[2 * a + b] = 1.0
        return tuple(values)

    def intervention(self, previous, value):
        return (float(1 - value), float(value))


def feed_both(context, belief, action, observation, event):
    coverage = tuple(action["participants"])
    context.commit_action(action, intended_sensor_ids=coverage, next_time=observation["t"])
    belief.commit_action(action)
    belief.receive(observation, "belief-" + event)
    context.receive(observation, "context-" + event)


class PosteriorContextTests(unittest.TestCase):
    def setUp(self):
        self.anchor = {"t": 0, "measurements": [
            {"id": "A", "bit": 0}, {"id": "B", "bit": 0}, {"id": "C", "bit": 1}]}
        self.context = ObservedContextSupport(self.anchor)
        self.belief = EvidenceBelief(IdentityKernel(), self.anchor, sensor_error_rate=.08)

    def witness_zero_zero(self):
        observation = {"t": 1, "measurements": [
            {"id": "A", "bit": 0}, {"id": "B", "bit": 0}]}
        feed_both(self.context, self.belief, AB, observation, "first")

    def test_noisy_raw_reading_does_not_support_a_different_belief_context(self):
        self.witness_zero_zero()
        setting = {"kind": "set", "participants": ["C"], "value": 1}
        feed_both(self.context, self.belief, setting,
                  {"t": 2, "measurements": [{"id": "C", "bit": 0}]}, "noisy")
        self.assertTrue(self.context.assess(AC)["supported"])  # historical v6 behavior
        self.assertEqual(self.belief.assess(AC)["status"], "PREDICT_WITH_EVIDENCE")
        self.assertEqual(self.belief.assess(AC)["max_full_world_probability"], 1.0)
        assessed = self.context.assess_posterior(AC, self.belief)
        self.assertEqual(assessed["status"], "NO_OBSERVED_CONTEXT_MASS")
        self.assertEqual(assessed["observed_context_mass"], 0.0)
        self.assertEqual(assessed["unobserved_context_mass"], 1.0)
        self.assertEqual(assessed["contexts"], [{"input_bits": [0, 1],
            "posterior_mass": 1.0, "observed_events": 0}])

    def test_supported_and_unseen_ordered_contexts_are_separate(self):
        self.witness_zero_zero()
        observed = self.context.assess_posterior(AB, self.belief)
        unseen = self.context.assess_posterior(AC, self.belief)
        self.assertEqual(observed["status"], "ALL_OBSERVED_CONTEXT_MASS")
        self.assertEqual(observed["observed_context_mass"], 1.0)
        self.assertEqual(observed["contexts"][0]["observed_events"], 1)
        self.assertEqual(unseen["status"], "NO_OBSERVED_CONTEXT_MASS")
        self.assertEqual(unseen["unobserved_context_mass"], 1.0)

    def test_joint_mass_is_grouped_across_modes_without_dropping_alternatives(self):
        self.witness_zero_zero()
        # Deliberately inject a test-only posterior to exercise grouped mass.
        self.belief._mass = {(0, (0, 0, 1)): .10, (1, (0, 0, 1)): .15,
                             (1, (0, 1, 1)): .75}
        before = self.belief.mass.copy()
        result = self.context.assess_posterior(AB, self.belief)
        self.assertEqual(result["status"], "PARTIAL_OBSERVED_CONTEXT_MASS")
        self.assertAlmostEqual(result["observed_context_mass"], .25)
        self.assertAlmostEqual(result["unobserved_context_mass"], .75)
        self.assertEqual(result["contexts"], [
            {"input_bits": [0, 0], "posterior_mass": .25, "observed_events": 1},
            {"input_bits": [0, 1], "posterior_mass": .75, "observed_events": 0}])
        self.assertEqual(self.belief.mass, before)

    def test_rejects_invalid_joint_mass_and_mismatched_identity_or_history(self):
        for bad in ({}, {(0, (0, 0, 1)): .9}, {(2, (0, 0, 1)): 1.0},
                    {(0, (0, 0)): 1.0}, {(0, (0, 0, 1)): float("nan")},
                    {(0, (0, 0, 1)): -.1, (1, (0, 0, 1)): 1.1},
                    {(True, (0, 0, 1)): 1.0}, {(0, (0, 0, True)): 1.0}):
            self.belief._mass = bad  # deliberate corruption fixture
            with self.assertRaises(ValueError):
                self.context.assess_posterior(AB, self.belief)
        self.belief = EvidenceBelief(IdentityKernel(), self.anchor)
        self.belief.ids = ("B", "A", "C")
        with self.assertRaisesRegex(ValueError, "identity scope"):
            self.context.assess_posterior(AB, self.belief)
        self.belief.ids = ("A", "B", "C")
        self.belief.t = 1
        with self.assertRaisesRegex(ValueError, "time"):
            self.context.assess_posterior(AB, self.belief)
        self.belief.t = 0
        self.belief.observed_evidence = [(0, (("A", 1), ("B", 0), ("C", 1)))]
        with self.assertRaisesRegex(ValueError, "sensor histories"):
            self.context.assess_posterior(AB, self.belief)

    def test_rejects_unfinished_events_and_noncontact_actions(self):
        with self.assertRaisesRegex(ValueError, "requires a contact"):
            self.context.assess_posterior({"kind": "observe", "participants": []}, self.belief)
        self.belief.commit_action(AB)
        with self.assertRaisesRegex(RuntimeError, "belief feedback"):
            self.context.assess_posterior(AB, self.belief)
        self.context.commit_action(AB, intended_sensor_ids=("A", "B"), next_time=1)
        with self.assertRaisesRegex(RuntimeError, "context feedback"):
            self.context.assess_posterior(AB, self.belief)

    def test_identical_sensor_history_with_different_actions_is_rejected(self):
        context_action = {"kind": "set", "participants": ["A"], "value": 0}
        belief_action = {"kind": "set", "participants": ["A"], "value": 1}
        observation = {"t": 1, "measurements": [{"id": "A", "bit": 0}]}
        self.context.commit_action(context_action, intended_sensor_ids=("A",), next_time=1)
        self.belief.commit_action(belief_action)
        self.context.receive(observation, "context")
        self.belief.receive(observation, "belief")
        with self.assertRaisesRegex(ValueError, "committed action histories"):
            self.context.assess_posterior(AB, self.belief)


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
