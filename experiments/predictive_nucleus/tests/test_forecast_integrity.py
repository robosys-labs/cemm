"""Regression tests for local transition and forecast commitment integrity."""
import copy
import unittest
from dataclasses import replace

from experiments.predictive_nucleus.evidence_guard import EpisodeEvidenceGuard
from experiments.predictive_nucleus.evidence_monitor import PredictiveAdequacyMonitor
from experiments.predictive_nucleus.tests.test_evidence_monitor import fixed
from experiments.predictive_nucleus.tests.test_uncertainty import ToyKernel
from experiments.predictive_nucleus.uncertainty import EvidenceBelief


ANCHOR = {"t": 0, "measurements": [
    {"id": "A", "bit": 1}, {"id": "B", "bit": 0}, {"id": "C", "bit": 0}]}
CONTACT = {"kind": "contact", "participants": ["A", "B"]}


class ForecastIntegrityTests(unittest.TestCase):
    def test_set_distribution_requires_exactly_two_binary_outcomes(self):
        class InvalidSetKernel(ToyKernel):
            def intervention(self, previous, value):
                return (0.0, 0.0, 1.0)

        belief = EvidenceBelief(InvalidSetKernel(), ANCHOR)
        before = copy.deepcopy(belief.mass)
        action = {"kind": "set", "participants": ["A"], "value": 0}
        with self.assertRaisesRegex(ValueError, "kernel probability distribution"):
            belief.assess(action)
        self.assertEqual(belief.mass, before)
        self.assertIsNone(belief.pending)

    def test_invalid_per_mode_rows_cannot_cancel_in_aggregate(self):
        class InvalidContactKernel(ToyKernel):
            def contact(self, a, b, hypothesis):
                return (.8, .8, 0, 0) if hypothesis == 0 else (.2, .2, 0, 0)

        belief = EvidenceBelief(InvalidContactKernel(), ANCHOR)
        before = copy.deepcopy(belief.mass)
        # Prior aggregate mass would misleadingly sum to one, but the local
        # distributions sum to 1.6 and .4 and cannot describe probabilities.
        with self.assertRaisesRegex(ValueError, "kernel probability distribution"):
            belief.preview(CONTACT)
        self.assertEqual(belief.mass, before)
        self.assertEqual(belief.mechanism_masses(), (.5, .5))

    def test_rejects_bad_arity_nan_negative_and_boolean_in_each_row(self):
        for row in ((1, 0, 0), (float("nan"), 0, 0, 1), (-.1, 1, .1, 0),
                    (True, 0, 0, 0), (.5, 0, 0, 0)):
            with self.subTest(row=row):
                class BadRowKernel(ToyKernel):
                    def contact(self, a, b, hypothesis):
                        return row
                with self.assertRaisesRegex(ValueError, "kernel probability distribution"):
                    EvidenceBelief(BadRowKernel(), ANCHOR).preview(CONTACT)

    def test_returned_and_inspected_snapshots_cannot_mutate_committed_forecast(self):
        belief = EvidenceBelief(ToyKernel(), ANCHOR)
        monitor = PredictiveAdequacyMonitor({"s": 0})
        guard = EpisodeEvidenceGuard()
        forecast = belief.commit_action(CONTACT)
        monitor.commit(forecast, source_id="s", next_time=1, intended_sensor_ids=("A", "B"))
        forecast.states.clear()
        forecast.states[(1, (1, 0, 0))] = 1.0
        belief.pending.states.clear()
        monitor.pending[0].states.clear()
        observed = {"t": 1, "measurements": [{"id": "A", "bit": 1}, {"id": "B", "bit": 1}]}
        checked = monitor.observe(observed, evidence_id="monitor-1", source_id="s")
        result = belief.receive(observed, "belief-1")
        self.assertEqual(checked.observed_likelihood, .5)
        self.assertEqual(result.observed_probability, .5)
        self.assertEqual(belief.mechanism_masses(), (1, 0))
        self.assertEqual(belief.receipt_forecast_signature("belief-1")[1],
                         ("contact", ("A", "B"), None))
        self.assertEqual(belief.receipt_forecast_signature("belief-1"), monitor.last_forecast_signature)
        guard.record(monitor, belief, result)
        self.assertEqual(guard.time, 1)

    def test_guard_rejects_different_committed_distributions(self):
        belief = EvidenceBelief(ToyKernel(), ANCHOR)
        monitor = PredictiveAdequacyMonitor({"s": 0})
        guard = EpisodeEvidenceGuard()
        belief.commit_action(CONTACT)
        # The unrelated monitor forecast assigns .001 to A=1, whereas the
        # belief's actual committed forecast assigns that event probability 1.
        monitor.commit(fixed(.001), source_id="s", next_time=1, intended_sensor_ids=("A",))
        observed = {"t": 1, "measurements": [{"id": "A", "bit": 1}]}
        checked = monitor.observe(observed, evidence_id="m", source_id="s")
        result = belief.receive(observed, "b")
        self.assertAlmostEqual(checked.observed_likelihood, .001)
        self.assertEqual(result.observed_probability, 1.0)
        with self.assertRaisesRegex(ValueError, "same committed forecast"):
            guard.record(monitor, belief, result)
        self.assertEqual(guard.time, 0)
        self.assertFalse(guard.blocked)

    def test_guard_rejects_same_distribution_bound_to_another_action(self):
        belief = EvidenceBelief(ToyKernel(), ANCHOR)
        monitor = PredictiveAdequacyMonitor({"s": 0})
        guard = EpisodeEvidenceGuard()
        forecast = belief.commit_action(CONTACT)
        other_action = replace(forecast, action=("contact", ("B", "A"), None))
        monitor.commit(other_action, source_id="s", next_time=1, intended_sensor_ids=("A",))
        observed = {"t": 1, "measurements": [{"id": "A", "bit": 1}]}
        monitor.observe(observed, evidence_id="m", source_id="s")
        result = belief.receive(observed, "b")
        with self.assertRaisesRegex(ValueError, "same committed forecast"):
            guard.record(monitor, belief, result)

    def test_guard_rejects_different_sensor_likelihood_contracts(self):
        belief = EvidenceBelief(ToyKernel(), ANCHOR, sensor_error_rate=.1)
        monitor = PredictiveAdequacyMonitor({"s": .05})
        guard = EpisodeEvidenceGuard()
        forecast = belief.commit_action(CONTACT)
        monitor.commit(forecast, source_id="s", next_time=1, intended_sensor_ids=("A",))
        observed = {"t": 1, "measurements": [{"id": "A", "bit": 1}]}
        monitor.observe(observed, evidence_id="m", source_id="s")
        result = belief.receive(observed, "b")
        with self.assertRaisesRegex(ValueError, "sensor calibration"):
            guard.record(monitor, belief, result)

    def test_public_sensor_calibration_and_posterior_cannot_be_reassigned(self):
        belief = EvidenceBelief(ToyKernel(), ANCHOR, sensor_error_rate=.05)
        before = belief.mass
        inspection = belief.mass
        inspection.clear()
        inspection[(0, (0, 0, 0))] = 1.0
        self.assertEqual(belief.mass, before)
        with self.assertRaises(AttributeError):
            belief.mass = {(0, (0, 0, 0)): 1.0}
        with self.assertRaises(AttributeError):
            belief.sensor_error_rate = .2
        monitor = PredictiveAdequacyMonitor({"s": .05})
        forecast = belief.commit_action(CONTACT)
        monitor.commit(forecast, source_id="s", next_time=1, intended_sensor_ids=("A", "B"))
        with self.assertRaises(AttributeError):
            belief.sensor_error_rate = .2
        observed = {"t": 1, "measurements": [{"id": "A", "bit": 1}, {"id": "B", "bit": 1}]}
        checked = monitor.observe(observed, evidence_id="m", source_id="s")
        result = belief.receive(observed, "b")
        self.assertAlmostEqual(checked.observed_likelihood, .475)
        self.assertAlmostEqual(result.observed_probability, checked.observed_likelihood)
        EpisodeEvidenceGuard().record(monitor, belief, result)

    def test_malformed_event_times_and_missing_envelopes_fail_before_consumption(self):
        belief = EvidenceBelief(ToyKernel(), ANCHOR)
        monitor = PredictiveAdequacyMonitor({"s": 0})
        forecast = belief.commit_action(CONTACT)
        monitor.commit(forecast, source_id="s", next_time=1, intended_sensor_ids=("A",))
        for malformed in ({"t": True, "measurements": []}, {"t": 1.0, "measurements": []},
                          {"t": 1}, {"t": 1, "measurements": [{"id": "A", "bit": 1, "extra": 0}]}):
            with self.subTest(observation=malformed):
                with self.assertRaises(ValueError):
                    belief.receive(malformed, "b")
                with self.assertRaises(ValueError):
                    monitor.observe(malformed, evidence_id="m", source_id="s")
                self.assertEqual(belief.t, 0)
                self.assertEqual(monitor.time, 0)
                self.assertIsNotNone(belief.pending)
                self.assertIsNotNone(monitor.pending)
        good = {"t": 1, "measurements": [{"id": "A", "bit": 1}]}
        monitor.observe(good, evidence_id="m", source_id="s")
        result = belief.receive(good, "b")
        guard = EpisodeEvidenceGuard()
        guard.record(monitor, belief, result)
        self.assertEqual(guard.time, 1)


if __name__ == "__main__":
    unittest.main()
