"""G1d instrument-error tests; never use simulator orientation as learner input."""
import unittest

from experiments.predictive_nucleus.uncertainty import EvidenceBelief
from experiments.predictive_nucleus.tests.test_uncertainty import ToyKernel


START = {"t": 0, "measurements": [
    {"id": "C", "bit": 0}, {"id": "B", "bit": 0}, {"id": "A", "bit": 1}]}
CONTACT = {"kind": "contact", "participants": ["A", "B"]}


class InstrumentReliabilityTests(unittest.TestCase):
    def test_invalid_instrument_calibration_rejected(self):
        for bad in (-.001, .5, 1., float("nan"), float("inf"), True):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                EvidenceBelief(ToyKernel(), START, sensor_error_rate=bad)

    def test_noise_aware_probe_information_gain_not_oracle_gain(self):
        clean = EvidenceBelief(ToyKernel(), START)
        noisy = EvidenceBelief(ToyKernel(), START, sensor_error_rate=.1)
        clean_gain = clean.preview(CONTACT).expected_info_gain
        noisy_gain = noisy.preview(CONTACT).expected_info_gain
        self.assertAlmostEqual(clean_gain, 1, places=8)
        self.assertGreater(noisy_gain, 0)
        self.assertLess(noisy_gain, clean_gain)
        self.assertEqual(noisy.t, 0)
        self.assertIsNone(noisy.pending)

    def test_noisy_outcome_updates_but_does_not_delete_valid_alternatives(self):
        belief = EvidenceBelief(ToyKernel(), START, sensor_error_rate=.1)
        belief.commit_action(CONTACT)
        report = belief.receive({"t": 1, "measurements": [
            {"id": "A", "bit": 1}, {"id": "B", "bit": 0}, {"id": "C", "bit": 0}]}, "sensor-1")
        self.assertNotEqual(report.status, "MODEL_MISMATCH_CANDIDATE")
        posterior = belief.mechanism_masses()
        self.assertAlmostEqual(posterior[0], .1, places=8)
        self.assertAlmostEqual(posterior[1], .9, places=8)
        self.assertGreater(report.observed_probability, 0.4)
        replay = belief.receive({"t": 1, "measurements": [
            {"id": "A", "bit": 1}, {"id": "B", "bit": 0}, {"id": "C", "bit": 0}]}, "sensor-1")
        self.assertEqual(report, replay)
        self.assertEqual(belief.mechanism_masses(), posterior)

    def test_empty_reading_is_not_negative_observation(self):
        belief = EvidenceBelief(ToyKernel(), START, sensor_error_rate=.08)
        belief.commit_action(CONTACT)
        report = belief.receive({"t": 1, "measurements": []}, "sensor-dropout")
        self.assertEqual(report.status, "NO_NEW_EVIDENCE")
        self.assertAlmostEqual(report.observed_probability, 1)
        self.assertEqual(belief.mechanism_masses(), (.5, .5))
        self.assertEqual(belief.t, 1)

    def test_default_zero_error_remains_compatible(self):
        hard = EvidenceBelief(ToyKernel(), START)
        hard.commit_action(CONTACT)
        result = hard.receive({"t": 1, "measurements": [
            {"id": "A", "bit": 1}, {"id": "B", "bit": 1}, {"id": "C", "bit": 0}]}, "hard-1")
        self.assertEqual(result.status, "EVIDENCE_SUPPORTED")
        self.assertEqual(hard.mechanism_masses(), (1, 0))

    def test_repeated_sensor_error_does_not_erase_all_support(self):
        belief = EvidenceBelief(ToyKernel(), START, sensor_error_rate=.04)
        belief.commit_action(CONTACT)
        result = belief.receive({"t": 1, "measurements": [
            {"id": "A", "bit": 0}, {"id": "B", "bit": 0}, {"id": "C", "bit": 1}]}, "sensor-corrupt")
        self.assertGreater(result.observed_probability, 0)
        self.assertAlmostEqual(sum(belief.mass.values()), 1)
        self.assertFalse(any(p < 0 for p in belief.mass.values()))


if __name__ == "__main__":
    unittest.main()
