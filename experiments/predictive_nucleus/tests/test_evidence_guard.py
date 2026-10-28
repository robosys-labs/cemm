"""Evidence lifecycle and paired scoring invariants, not a scientific gate."""
import itertools
import math
import unittest
from copy import deepcopy

from experiments.predictive_nucleus.evidence_guard import EpisodeEvidenceGuard, equally_weighted_log_e
from experiments.predictive_nucleus.evidence_monitor import PredictiveAdequacyMonitor
from experiments.predictive_nucleus.guard_trial import evaluate_kernel, frozen_config_v5, summarize_paired
from experiments.predictive_nucleus.stress_trial import joint_map_world
from experiments.predictive_nucleus.tests.test_evidence_monitor import ForecastFixture, fixed
from experiments.predictive_nucleus.tests.test_uncertainty import ToyKernel
from experiments.predictive_nucleus.uncertainty import EvidenceBelief


class GuardTests(unittest.TestCase):
    def test_conflict_remains_blocked_after_missing_feedback(self):
        start = {"t": 0, "measurements": [{"id": n, "bit": 0} for n in ("A", "B", "C")]}
        belief = EvidenceBelief(ToyKernel(), start, sensor_error_rate=.05)
        monitor = PredictiveAdequacyMonitor({"s": .05})
        guard = EpisodeEvidenceGuard()
        action = {"kind": "observe", "participants": []}
        prediction = belief.commit_action(action)
        monitor.commit(prediction, source_id="s", next_time=1, intended_sensor_ids=("C",))
        obs = {"t": 1, "measurements": [{"id": "C", "bit": 1}]}
        monitor.observe(obs, evidence_id="m1", source_id="s")
        receipt = belief.receive(obs, "b1", mismatch_limit=.1)
        self.assertEqual(receipt.status, "MODEL_MISMATCH_CANDIDATE")
        guard.record(monitor, belief, receipt)
        self.assertTrue(guard.blocked)
        self.assertFalse(guard.portfolio_alarm)
        with self.assertRaises(ValueError):
            guard.record(monitor, belief, receipt)
        prediction = belief.commit_action(action)
        monitor.commit(prediction, source_id="s", next_time=2, intended_sensor_ids=("C",))
        missing = {"t": 2, "measurements": []}
        monitor.observe(missing, evidence_id="m2", source_id="s")
        update = belief.receive(missing, "b2")
        guard.record(monitor, belief, update)
        self.assertEqual(belief.assess(action)["status"], "PREDICT_WITH_EVIDENCE")
        self.assertTrue(guard.blocked)
        self.assertEqual(guard.conflicts, {"MODEL_MISMATCH_CANDIDATE"})
        with self.assertRaises(AttributeError):
            guard.conflicts.clear()

    def test_guard_rejects_a_different_feedback_event(self):
        start = {"t": 0, "measurements": [{"id": n, "bit": 0} for n in ("A", "B", "C")]}
        belief = EvidenceBelief(ToyKernel(), start, sensor_error_rate=.05)
        monitor = PredictiveAdequacyMonitor({"s": .05})
        action = {"kind": "observe", "participants": []}
        forecast = belief.commit_action(action)
        monitor.commit(forecast, source_id="s", next_time=1, intended_sensor_ids=("C",))
        monitor.observe({"t": 1, "measurements": [{"id": "C", "bit": 0}]}, evidence_id="m", source_id="s")
        other = belief.receive({"t": 1, "measurements": [{"id": "C", "bit": 1}]}, "b")
        guard = EpisodeEvidenceGuard()
        with self.assertRaisesRegex(ValueError, "same sensor event"):
            guard.record(monitor, belief, other)
        self.assertEqual(guard.time, 0)
        self.assertFalse(guard.blocked)

    def test_equal_weight_mixture_and_anytime_bound_under_a_toy_null(self):
        self.assertEqual(equally_weighted_log_e(0, 0), 0)
        self.assertEqual(equally_weighted_log_e(float("-inf"), float("-inf")), float("-inf"))
        self.assertEqual(equally_weighted_log_e(float("inf"), 0), float("inf"))
        with self.assertRaises(ValueError):
            equally_weighted_log_e(float("nan"), 0)
        p = .1  # exact i.i.d. null; q's are fixed before each observation
        false_alarm_probability = 0.0
        for outcome in itertools.product((0, 1), repeat=8):
            l0 = l1 = 0.0
            crossed = False
            for bit in outcome:
                null = p if bit else 1 - p
                q0 = .5
                q1 = .8 if bit else .2
                l0 += math.log(q0 / null)
                l1 += math.log(q1 / null)
                crossed |= equally_weighted_log_e(l0, l1) >= math.log(20)
            if crossed:
                false_alarm_probability += math.prod(p if b else 1 - p for b in outcome)
        self.assertLessEqual(false_alarm_probability, .05 + 1e-12)

    def test_zero_alternative_then_impossible_null_never_creates_nan(self):
        monitor = PredictiveAdequacyMonitor({"s": 0})
        monitor.commit(fixed(.5), source_id="s", next_time=1, intended_sensor_ids=("A",),
                       alternative_forecast=fixed(0))
        monitor.observe({"t": 1, "measurements": [{"id": "A", "bit": 1}]}, evidence_id="one", source_id="s")
        self.assertEqual(monitor.change_point_log_e_value, float("-inf"))
        monitor.commit(fixed(0), source_id="s", next_time=2, intended_sensor_ids=("A",),
                       alternative_forecast=fixed(1))
        result = monitor.observe({"t": 2, "measurements": [{"id": "A", "bit": 1}]}, evidence_id="two", source_id="s")
        self.assertEqual(result.change_point_log_e_value, float("-inf"))
        self.assertEqual(result.log_e_value, float("inf"))
        self.assertTrue(result.alarm)

    def test_calibration_and_alternate_scope_are_frozen(self):
        monitor = PredictiveAdequacyMonitor({"s": .05})
        with self.assertRaises(TypeError):
            monitor.source_error_rates["s"] = 0
        with self.assertRaises(AttributeError):
            monitor.source_error_rates = {"s": 0}
        with self.assertRaises(AttributeError):
            monitor.alpha = .9
        invalid = ForecastFixture({"A": .5, "B": 0, "C": 0}, {(0, (0, 0)): 1.0})
        with self.assertRaisesRegex(ValueError, "alternate predictive distribution"):
            monitor.commit(fixed(.5), source_id="s", next_time=1, intended_sensor_ids=("A",),
                           alternative_forecast=invalid)
        self.assertIsNone(monitor.pending)

    def test_joint_map_confidence_matches_the_chosen_world(self):
        forecast = ForecastFixture({"A": .6, "B": .3, "C": .3}, {
            (0, (0, 0, 0)): .4, (0, (1, 1, 0)): .3, (1, (1, 0, 1)): .3})
        # Marginal rounding chooses (1,0,0), which has probability zero.
        world, confidence = joint_map_world(forecast)
        self.assertEqual(world, (0, 0, 0))
        self.assertAlmostEqual(confidence, .4)
        tied = ForecastFixture({"A": .5, "B": 0, "C": 0}, {
            (1, (1, 0, 0)): .5, (0, (0, 0, 0)): .5})
        self.assertEqual(joint_map_world(tied), ((0, 0, 0), .5))

    def test_paired_report_includes_both_repairs_and_regressions(self):
        rows = [{"eligible": True, "guard_eligible": False, "joint_map_correct": False, "joint_map_confidence": .96},
                {"eligible": False, "guard_eligible": True, "joint_map_correct": False, "joint_map_confidence": .96}]
        out = summarize_paired([{"case_id": "world", "rollout": {
            "rows": rows, "guard_portfolio_alarm": False, "guard_conflicts": [], "probes": 2,
            "set_probes": 0, "observed_bits": 4}}])
        self.assertEqual(out["previously_covered_wrong_now_abstained"], ["world:direction-0"])
        self.assertEqual(out["newly_covered_wrong"], ["world:direction-1"])
        self.assertEqual(out["guard"]["covered_wrong_per_query"], .5)
        self.assertEqual(out["mean_physical_probes"], 2)

    def test_locked_new_protocol_and_small_public_fixture_run(self):
        cfg = deepcopy(frozen_config_v5())
        # Synthetic test-only lineages; do not open the protocol's scored worlds.
        cfg["opened_v4_world_seeds"] = [901]
        cfg["new_public_world_seeds"] = [907]
        result = evaluate_kernel(ToyKernel(), cfg, 1)
        self.assertEqual(set(result), {"opened_v4", "fresh_public_v5"})
        for split in result.values():
            self.assertEqual(set(split), set(cfg["strata"]))
            for summary in split.values():
                self.assertEqual(summary["worlds"], 1)
                self.assertEqual(summary["target_queries"], 2)
                self.assertLessEqual(summary["mean_physical_probes"], 2)


if __name__ == "__main__":
    unittest.main()
