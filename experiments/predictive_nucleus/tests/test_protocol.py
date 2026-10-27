"""G0 implementation invariants; passing these is not a world-learning gate."""
import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from experiments.predictive_nucleus.evaluate import score_predictions
from experiments.predictive_nucleus.protocol import LOCK, digest_protocol, read_protocol, verify_protocol


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.config = read_protocol()

    def test_immutable_frozen_protocol(self):
        expected = LOCK.read_text().split()[0]
        self.assertEqual(expected, digest_protocol())
        verify_protocol(self.config, expected)

    def test_seed_lineage_overlap_refused(self):
        edited = copy.deepcopy(self.config)
        edited["splits"]["ood_challenge"]["seeds"][0] = self.config["splits"]["train"]["seeds"][0]
        with self.assertRaisesRegex(ValueError, "leaks"):
            verify_protocol(edited)

    def test_topology_ood_leak_refused(self):
        edited = copy.deepcopy(self.config)
        edited["splits"]["ood_challenge"]["families"].append("single_contact")
        with self.assertRaisesRegex(ValueError, "overlap"):
            verify_protocol(edited)

    def test_challenge_fitting_refused(self):
        edited = copy.deepcopy(self.config)
        edited["evaluation_policy"]["never_fit_on"] = ["ood_challenge"]
        with self.assertRaisesRegex(ValueError, "selection"):
            verify_protocol(edited)

    def test_verify_command(self):
        cwd = Path(__file__).resolve().parents[3]
        result = subprocess.run([sys.executable, "-m", "experiments.predictive_nucleus.protocol", "verify"],
                                cwd=cwd, capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)["G1"], "NOT_RUN")


class ScorerTests(unittest.TestCase):
    def setUp(self):
        self.gold = [
            {"case_id": "F", "seed": 1, "family": "single_contact", "pair_id": "P", "direction": 0,
             "truth": {"A": 1, "B": 0, "C": 0}},
            {"case_id": "R", "seed": 1, "family": "single_contact", "pair_id": "P", "direction": 1,
             "truth": {"A": 0, "B": 1, "C": 0}},
        ]
        self.predictions = [
            {"case_id": "F", "p1": {"A": 1.0, "B": 0.0, "C": 0.0}},
            {"case_id": "R", "p1": {"A": 0.0, "B": 1.0, "C": 0.0}},
        ]

    def test_complete_state_and_pair(self):
        score = score_predictions(self.gold, self.predictions)["aggregate"]
        self.assertEqual(score["full_world_exact"], 1.0)
        self.assertEqual(score["role_pair_exact"], 1.0)
        self.assertEqual(score["per_entity_nll"], 0.0)
        self.assertEqual(score["per_entity_brier"], 0.0)
        self.assertEqual(score["ece_10"], 0.0)

    def test_one_direction_wrong_pair_is_zero(self):
        edited = copy.deepcopy(self.predictions)
        edited[1]["p1"]["A"] = 0.9
        score = score_predictions(self.gold, edited)["aggregate"]
        self.assertEqual(score["role_pair_exact"], 0.0)
        self.assertEqual(score["full_world_exact"], 0.5)
        regressions = score_predictions(self.gold, edited, self.predictions)["regressions"]
        self.assertEqual(regressions["previously_correct_now_wrong"], ["R"])
        self.assertEqual(regressions["previously_wrong_now_correct"], [])

    def test_wrong_identity_and_missing_unchanged_entity_rejected(self):
        edited = copy.deepcopy(self.predictions)
        del edited[0]["p1"]["C"]
        with self.assertRaisesRegex(ValueError, "identity alias"):
            score_predictions(self.gold, edited)

    def test_missing_reverse_case_rejected(self):
        with self.assertRaisesRegex(ValueError, "missing or extra"):
            score_predictions(self.gold, self.predictions[:1])
        with self.assertRaisesRegex(ValueError, "incomplete"):
            score_predictions(self.gold[:1], self.predictions[:1])

    def test_abstentions_must_not_claim_a_state(self):
        edited = copy.deepcopy(self.predictions)
        edited[0] = {"case_id": "F", "abstain": True}
        score = score_predictions(self.gold, edited)["aggregate"]
        self.assertEqual(score["answered_coverage"], .5)
        self.assertEqual(score["role_pair_exact"], 0)
        edited[0]["p1"] = {"A": 1}
        with self.assertRaisesRegex(ValueError, "cannot assert"):
            score_predictions(self.gold, edited)

    def test_probability_and_duplicate_cases_rejected(self):
        for bad in (-0.01, 1.01, float("nan"), True):
            edited = copy.deepcopy(self.predictions)
            edited[0]["p1"]["A"] = bad
            with self.assertRaisesRegex(ValueError, "probability"):
                score_predictions(self.gold, edited)
        with self.assertRaisesRegex(ValueError, "duplicate model"):
            score_predictions(self.gold, self.predictions + self.predictions[:1])

    def test_inputs_pure_under_scoring(self):
        before = copy.deepcopy([self.gold, self.predictions])
        score_predictions(self.gold, self.predictions)
        self.assertEqual(before, [self.gold, self.predictions])

    def test_wrong_full_state_defeats_high_bit_accuracy(self):
        edited = copy.deepcopy(self.predictions)
        edited[0]["p1"]["C"] = .51
        score = score_predictions(self.gold, edited)["aggregate"]
        self.assertEqual(score["full_world_exact"], .5)
        self.assertEqual(score["role_pair_exact"], 0)


if __name__ == "__main__":
    unittest.main()
