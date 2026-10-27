"""Independent forecast-evidence tests, not neural model accuracy claims."""
import math
import unittest
from dataclasses import dataclass

from experiments.predictive_nucleus.evidence_monitor import PredictiveAdequacyMonitor


@dataclass(frozen=True)
class ForecastFixture:
    state_probability: dict
    states: dict


def fixed(probability_of_one: float):
    """Probabilistic one-bit outcome, all other world entities fixed."""
    return ForecastFixture({"A": probability_of_one, "B": 0, "C": 0},
                           {(0, (0, 0, 0)): 1 - probability_of_one,
                            (0, (1, 0, 0)): probability_of_one})


def ambiguous():
    return ForecastFixture({"A": 0.5, "B": 0, "C": 0},
                           {(0, (0, 0, 0)): .5, (1, (1, 0, 0)): .5})


class MonitorTests(unittest.TestCase):
    def monitor(self, error=.05):
        return PredictiveAdequacyMonitor({"verified-device": error}, alpha=.05)

    def read(self, monitor, forecast, time, bit, evidence_id, coverage=("A",)):
        monitor.commit(forecast, source_id="verified-device", next_time=time,
                       intended_sensor_ids=coverage)
        return monitor.observe({"t": time, "measurements": [{"id": "A", "bit": bit}]},
                               evidence_id=evidence_id, source_id="verified-device")

    def test_ambiguous_prediction_not_flagged_as_model_failure(self):
        m = self.monitor(error=0)
        r = self.read(m, ambiguous(), 1, 1, "r1")
        self.assertEqual(r.status, "OBSERVATION_COMPATIBLE")
        self.assertAlmostEqual(r.observed_likelihood, 0.5)
        self.assertAlmostEqual(r.log_e_value, 0.0)
        self.assertFalse(r.alarm)

    def test_one_plausible_sensor_flip_is_not_a_failure_verdict(self):
        m = self.monitor(error=.05)
        r = self.read(m, fixed(.001), 1, 1, "outlier1")
        self.assertEqual(r.status, "OBSERVATION_COMPATIBLE")
        self.assertFalse(r.alarm)
        self.assertAlmostEqual(r.observed_likelihood, .05 + .9 * .001)
        self.assertLess(r.log_e_value, math.log(1 / m.alpha))
        self.assertEqual(len(m.history), 1)

    def test_repeated_independent_surprise_can_reject_forecast_model(self):
        m = self.monitor(error=.05)
        self.read(m, fixed(.001), 1, 1, "outlier1")
        r = self.read(m, fixed(.001), 2, 1, "outlier2")
        self.assertEqual(r.status, "MODEL_MISMATCH_EVIDENCE")
        self.assertTrue(r.alarm)
        self.assertGreaterEqual(r.log_e_value, math.log(20))
        self.assertEqual(len(m.history), 2)

    def test_duplicate_source_and_time_cannot_manufacture_evidence(self):
        m = self.monitor()
        self.read(m, fixed(.001), 1, 1, "id1")
        previous = m.log_e_value
        original = m.observe({"t": 1, "measurements": [{"id": "A", "bit": 1}]},
                             evidence_id="id1", source_id="verified-device")
        self.assertEqual(previous, m.log_e_value)
        self.assertEqual(original, m.history[0])
        with self.assertRaisesRegex(ValueError, "different content"):
            m.observe({"t": 1, "measurements": [{"id": "A", "bit": 0}]},
                      evidence_id="id1", source_id="verified-device")
        with self.assertRaisesRegex(RuntimeError, "unsolicited"):
            m.observe({"t": 1, "measurements": [{"id": "A", "bit": 1}]},
                      evidence_id="id2", source_id="verified-device")
        self.assertEqual(m.log_e_value, previous)

    def test_missing_measurement_is_not_negative_evidence(self):
        m = self.monitor()
        m.commit(fixed(.001), source_id="verified-device", next_time=1,
                 intended_sensor_ids=("A", "B", "C"))
        r = m.observe({"t": 1, "measurements": []}, evidence_id="missing", source_id="verified-device")
        self.assertEqual(r.status, "NO_EVIDENCE")
        self.assertEqual(r.observed_bits, 0)
        self.assertEqual(r.missing_bits, 3)
        self.assertEqual(r.log_e_value, 0)
        self.assertFalse(r.alarm)

    def test_sensor_coverage_must_be_precommitted(self):
        m = self.monitor()
        m.commit(ambiguous(), source_id="verified-device", next_time=1,
                 intended_sensor_ids=("A",))
        for bad in ({"id": "B", "bit": 0}, {"id": "A", "bit": None}, {"id": "A", "bit": True}):
            with self.assertRaises(ValueError):
                m.observe({"t": 1, "measurements": [bad]},
                          evidence_id="bad", source_id="verified-device")
        self.assertEqual(m.time, 0)
        self.assertIsNotNone(m.pending)
        good = m.observe({"t": 1, "measurements": [{"id": "A", "bit": 0}]},
                         evidence_id="valid", source_id="verified-device")
        self.assertEqual(good.status, "OBSERVATION_COMPATIBLE")

    def test_reject_unknown_source_and_time_and_bad_probabilities(self):
        m = self.monitor()
        with self.assertRaisesRegex(ValueError, "unreviewed"):
            m.commit(ambiguous(), source_id="from-message", next_time=1, intended_sensor_ids=("A",))
        with self.assertRaisesRegex(ValueError, "non-sequential"):
            m.commit(ambiguous(), source_id="verified-device", next_time=3, intended_sensor_ids=("A",))
        with self.assertRaisesRegex(ValueError, "invalid joint predictive"):
            m.commit(fixed(1.5), source_id="verified-device", next_time=1, intended_sensor_ids=("A",))
        for bad in (-.1, .5, float('nan')):
            with self.assertRaises(ValueError):
                self.monitor(bad)

    def test_committed_forecast_cannot_be_mutated_after_commit(self):
        m = self.monitor(error=0)
        forecast = fixed(.001)
        m.commit(forecast, source_id="verified-device", next_time=1,
                 intended_sensor_ids=("A",))
        forecast.states[(0, (1, 0, 0))] = .999
        forecast.states[(0, (0, 0, 0))] = .001
        r = m.observe({"t": 1, "measurements": [{"id": "A", "bit": 1}]},
                      evidence_id="actual", source_id="verified-device")
        self.assertAlmostEqual(r.observed_likelihood, .001)

    def test_nonlinear_correlated_worlds_scored_as_joint_distribution(self):
        m = self.monitor(error=0)
        forecast = ForecastFixture({"A": 0.5, "B": 0.5, "C": 0},
                                   {(0, (0, 0, 0)): .5, (1, (1, 1, 0)): .5})
        m.commit(forecast, source_id="verified-device", next_time=1,
                 intended_sensor_ids=("A", "B"))
        r = m.observe({"t": 1, "measurements": [{"id": "A", "bit": 1}, {"id": "B", "bit": 0}]},
                      evidence_id="anti-correlation", source_id="verified-device")
        self.assertTrue(r.alarm)
        self.assertEqual(r.observed_likelihood, 0)
        self.assertEqual(r.log_e_value, float('inf'))


if __name__ == "__main__":
    unittest.main()
