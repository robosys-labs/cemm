"""G1d temporal verification requires falsifiable post-learning probes, not only IG."""
import unittest

from experiments.predictive_nucleus.uncertainty import EvidenceBelief
from experiments.predictive_nucleus.evidence_monitor import PredictiveAdequacyMonitor
from experiments.predictive_nucleus.tests.test_uncertainty import ToyKernel
from experiments.predictive_nucleus.tests.test_evidence_monitor import fixed, ambiguous


START = {"t": 0, "measurements": [
    {"id": "A", "bit": 1}, {"id": "B", "bit": 0}, {"id": "C", "bit": 0}]}
CONTACT = {"kind": "contact", "participants": ["A", "B"]}


class TemporalValidationTests(unittest.TestCase):
    def test_mechanism_can_be_identified_but_not_yet_validated_over_time(self):
        belief = EvidenceBelief(ToyKernel(), START)
        belief.commit_action(CONTACT)
        belief.receive({"t": 1, "measurements": [
            {"id": "A", "bit": 1}, {"id": "B", "bit": 1}, {"id": "C", "bit": 0}]}, "first")
        self.assertEqual(belief.mechanism_masses(), (1, 0))
        self.assertEqual(belief.choose_probe([CONTACT])["reason"], "NO_DISCRIMINATING_PROBE")
        mass = belief.mass.copy()
        validation = belief.choose_validation_probe([CONTACT])
        self.assertEqual(validation["reason"], "TEST_MECHANISM_PERSISTENCE")
        self.assertEqual(validation["action"], CONTACT)
        self.assertAlmostEqual(validation["disagreement_tv"], .5)
        self.assertEqual(belief.mass, mass)
        self.assertIsNone(belief.pending)

    def test_no_falsifiable_probe_does_not_authorize_uninformative_action(self):
        all_zero = {"t": 0, "measurements": [
            {"id": "A", "bit": 0}, {"id": "B", "bit": 0}, {"id": "C", "bit": 0}]}
        belief = EvidenceBelief(ToyKernel(), all_zero)
        result = belief.choose_validation_probe([CONTACT])
        self.assertEqual(result["reason"], "NO_FALSIFIABLE_VALIDATION_PROBE")
        self.assertIsNone(result["action"])

    def test_sensor_noise_reduces_expected_validation_separation(self):
        clean = EvidenceBelief(ToyKernel(), START)
        noisy = EvidenceBelief(ToyKernel(), START, sensor_error_rate=.1)
        for b in (clean, noisy):
            b.commit_action(CONTACT)
            b.receive({"t": 1, "measurements": [
                {"id": "A", "bit": 1}, {"id": "B", "bit": 1}, {"id": "C", "bit": 0}]},
                "first-contact")
        a = clean.choose_validation_probe([CONTACT])["disagreement_tv"]
        b = noisy.choose_validation_probe([CONTACT])["disagreement_tv"]
        self.assertGreater(a, b)
        self.assertGreater(b, 0)

    def test_validation_does_not_allow_reusing_pending_future_sensor(self):
        belief = EvidenceBelief(ToyKernel(), START)
        belief.commit_action(CONTACT)
        with self.assertRaises(RuntimeError):
            belief.choose_validation_probe([CONTACT])

    def test_change_point_comparator_is_separately_reported(self):
        m = PredictiveAdequacyMonitor({"verified": 0.0}, alpha=.05)
        m.commit(fixed(.001), source_id="verified", next_time=1,
                 intended_sensor_ids=("A",), alternative_forecast=ambiguous())
        r = m.observe({"t": 1, "measurements": [{"id": "A", "bit": 1}]},
                      evidence_id="rare", source_id="verified")
        self.assertTrue(r.change_point_alarm)
        self.assertGreaterEqual(r.change_point_log_e_value, 2.99)
        m.commit(fixed(.001), source_id="verified", next_time=2,
                 intended_sensor_ids=("A",))
        without_reference = m.observe({"t": 2, "measurements": []},
                                      evidence_id="missing", source_id="verified")
        self.assertIsNone(without_reference.change_point_log_e_value)
        self.assertFalse(without_reference.change_point_alarm)


if __name__ == "__main__":
    unittest.main()
