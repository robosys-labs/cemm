"""Synthetic arithmetic tests; no checkpoint replay or fixture scoring."""
from hashlib import sha256
from itertools import product
import json
from math import fsum
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus.inspect_case6_masses import EXPECTED_MAPPING, _prior_finding, inspect_masses


WORLDS = tuple(product((0, 1), repeat=3))


class RawMassInspectionTests(unittest.TestCase):
    def test_small_overshoot_full_distribution_is_only_a_candidate(self):
        masses = {world: 1e-9 for world in WORLDS}
        masses[(1, 1, 1)] = 1.00000003851976
        result = inspect_masses(("PREDICTED", None, masses))
        self.assertEqual(len(result["raw_masses"]), 8)
        self.assertEqual(result["raw_sum"], fsum(masses.values()))
        self.assertEqual(result["raw_max"], 1.00000003851976)
        self.assertAlmostEqual(result["raw_max_above_one"], 0.00000003851976, places=15)
        self.assertTrue(result["normalization_eligible"])
        candidate = result["normalization_candidate"]
        self.assertEqual(len(candidate["masses"]), 8)
        self.assertAlmostEqual(candidate["sum"], 1.0, places=15)
        self.assertTrue(all(0 <= item["probability"] <= 1 for item in candidate["masses"]))
        self.assertFalse(candidate["map_changed"])
        self.assertEqual(candidate["raw_map"], [1, 1, 1])
        self.assertGreater(candidate["max_absolute_change"], 0)
        self.assertGreater(candidate["half_l1_change"], 0)
        self.assertAlmostEqual(candidate["half_l1_change"],
                               .5 * fsum(abs(masses[world] - item["probability"])
                                           for world, item in zip(WORLDS, candidate["masses"], strict=True)))
        self.assertNotIn("total_variation", candidate)

    def test_missing_negative_nan_large_mass_and_bad_status_fail_closed(self):
        base = {world: .125 for world in WORLDS}
        cases = [("ABSTAIN", "unseen", None), ("PREDICTED", None, {(0, 0, 0): 1.0})]
        for bad in (-1e-12, float("nan"), float("inf"), 1.1, True):
            values = dict(base); values[(0, 0, 0)] = bad
            cases.append(("PREDICTED", None, values))
        bad_world = dict(base); bad_world[(True, 0, 0)] = bad_world.pop((1, 0, 0))
        cases.append(("PREDICTED", None, bad_world))
        for case in cases:
            result = inspect_masses(case)
            self.assertFalse(result["normalization_eligible"])
            self.assertIsNone(result["normalization_candidate"])
            json.dumps(result, allow_nan=False)

    def test_zero_distribution_and_nontrivial_sum_fail_closed(self):
        for value in (0.0, .1, .2):
            result = inspect_masses(("PREDICTED", None, {world: value for world in WORLDS}))
            self.assertFalse(result["normalization_eligible"])
            self.assertIsNone(result["normalization_candidate"])

    def test_near_sum_tolerance_and_lexicographic_ties(self):
        tied = {world: 0.0 for world in WORLDS}
        tied[(0, 0, 1)] = .5
        tied[(1, 0, 0)] = .5
        result = inspect_masses(("PREDICTED", None, tied))
        self.assertTrue(result["normalization_eligible"])
        self.assertEqual(result["normalization_candidate"]["raw_map"], [0, 0, 1])
        self.assertEqual(result["normalization_candidate"]["normalized_map"], [0, 0, 1])
        self.assertFalse(result["normalization_candidate"]["map_changed"])
        outside = dict(tied); outside[(0, 0, 0)] = 2e-6
        result = inspect_masses(("PREDICTED", None, outside))
        self.assertFalse(result["normalization_eligible"])
        self.assertIsNone(result["normalization_candidate"])

    def test_prior_context_and_hash_are_required(self):
        anomaly = {"case": 6, "id_arm": "augmented", "target": "masked", "seed": 37,
                   "model": "flat", "step": 4, "mapping": EXPECTED_MAPPING,
                   "kind": "invalid_probability", "world": "(1, 1, 1)",
                   "probability": "1.00000003851976"}
        payload = json.dumps({"status": "RAW_CONTRACT_VIOLATION_OBSERVED", "anomalies": [anomaly],
                              "environment": {"cpu": "synthetic"}}).encode()
        with TemporaryDirectory() as root:
            path = Path(root) / "prior.json"
            path.write_bytes(payload)
            with patch("experiments.predictive_nucleus.inspect_case6_masses.PRIOR_RESULT", path), patch(
                    "experiments.predictive_nucleus.inspect_case6_masses.PRIOR_RESULT_SHA256",
                    sha256(payload).hexdigest()):
                result, environment = _prior_finding()
                self.assertEqual(result, anomaly)
                self.assertEqual(environment, {"cpu": "synthetic"})
                path.write_bytes(payload + b" ")
                with self.assertRaisesRegex(ValueError, "hash mismatch"):
                    _prior_finding()
            altered = dict(anomaly, world="(0, 0, 0)")
            other = json.dumps({"status": "RAW_CONTRACT_VIOLATION_OBSERVED", "anomalies": [altered]}).encode()
            path.write_bytes(other)
            with patch("experiments.predictive_nucleus.inspect_case6_masses.PRIOR_RESULT", path), patch(
                    "experiments.predictive_nucleus.inspect_case6_masses.PRIOR_RESULT_SHA256",
                    sha256(other).hexdigest()):
                with self.assertRaisesRegex(ValueError, "context changed"):
                    _prior_finding()


if __name__ == "__main__":
    unittest.main()
