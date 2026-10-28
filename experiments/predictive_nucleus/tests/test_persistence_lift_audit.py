"""Tests for post-hoc supplied-persistence archive analysis."""
from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from experiments.predictive_nucleus.development_run import score_forecast
from experiments.predictive_nucleus.persistence_lift_audit import (
    analyze, audit_case, lift_distribution, read_archive,
)


class PersistenceLiftAuditTests(unittest.TestCase):
    def test_marginalize_before_map_and_use_only_prior_readings(self):
        ids = ("a", "b", "c")
        probabilities = {world: 0.0 for world in product((0, 1), repeat=3)}
        probabilities[(0, 0, 0)] = .3
        probabilities[(0, 0, 1)] = .3
        probabilities[(1, 0, 0)] = .4
        anchor = {"t": 0, "measurements": [{"id": "a", "bit": 0},
                  {"id": "b", "bit": 1}, {"id": "c", "bit": 0}]}
        turn = {"observation": anchor, "action": {"kind": "set", "participants": ["a"], "value": 0}}
        feedback = {"t": 1, "measurements": [{"id": "a", "bit": 1}]}
        truth = (0, 1, 0)
        original = score_forecast("PREDICTED", None, probabilities, truth)
        case = {"case": 0, "public_history": [anchor, turn, feedback], "steps": [{
            "step": 0, "action_kind": "set", "action": turn["action"], "ids": list(ids),
            "truth": list(truth), "models": {"flat": original}}]}
        lifted = audit_case(case)["steps"][0]["persistence_lift"]
        self.assertEqual(original["map_world"], [1, 0, 0])
        self.assertEqual(lifted["map_world"], [0, 1, 0])
        self.assertAlmostEqual(lifted["truth_probability"], .6)
        self.assertEqual(lifted["latest_readings_before_prediction"], {"a": 0, "b": 1, "c": 0})
        self.assertEqual(lifted["change"], "corrected")
        self.assertNotIn("persistence_lift", case["steps"][0])

    def test_prior_feedback_used_next_step_current_feedback_excluded(self):
        ids = ("a", "b", "c")
        probabilities = {world: .125 for world in product((0, 1), repeat=3)}
        anchor = {"t": 0, "measurements": [{"id": name, "bit": 0} for name in ids]}
        first_action = {"kind": "set", "participants": ["a"], "value": 1}
        second_action = {"kind": "set", "participants": ["b"], "value": 1}
        first_feedback = {"t": 1, "measurements": [{"id": "a", "bit": 1}]}
        second_feedback = {"t": 2, "measurements": [{"id": "b", "bit": 1}]}
        first_truth, second_truth = (1, 0, 0), (1, 1, 0)
        steps = [{"step": i, "action_kind": "set", "action": action, "ids": list(ids),
                  "truth": list(truth), "models": {"flat": score_forecast(
                      "PREDICTED", None, probabilities, truth)}}
                 for i, (action, truth) in enumerate(((first_action, first_truth),
                                                       (second_action, second_truth)))]
        case = {"case": 0, "steps": steps, "public_history": [anchor,
                {"observation": anchor, "action": first_action}, first_feedback,
                {"observation": first_feedback, "action": second_action}, second_feedback]}
        audited = audit_case(case)["steps"]
        self.assertEqual(audited[0]["persistence_lift"]["latest_readings_before_prediction"],
                         {"a": 0, "b": 0, "c": 0})
        self.assertEqual(audited[1]["persistence_lift"]["latest_readings_before_prediction"],
                         {"a": 1, "b": 0, "c": 0})
        self.assertEqual(audited[1]["persistence_lift"]["map_world"], [1, 0, 0])

    def test_ties_lexicographic_and_invalid_distributions(self):
        ids = ("a", "b", "c")
        probabilities = {world: .125 for world in product((0, 1), repeat=3)}
        lifted = lift_distribution(ids, ["a"], {"a": 1, "b": 1, "c": 0}, probabilities)
        score = score_forecast("PREDICTED", None, lifted, (0, 1, 0))
        self.assertEqual(score["map_world"], [0, 1, 0])
        with self.assertRaises(ValueError):
            lift_distribution(ids, ["a"], {"a": 1, "b": 1}, probabilities)
        probabilities.pop((0, 0, 0))
        with self.assertRaises(ValueError):
            lift_distribution(ids, ["a"], {"a": 1, "b": 1, "c": 0}, probabilities)

    def test_zip_hash_is_required(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "fake.zip"
            path.write_bytes(b"not the archived evidence")
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                read_archive(path)

    def test_recorded_public_archive_regression(self):
        archived = read_archive()
        result = analyze(archived)
        self.assertEqual(len(result["results"]), 5)
        self.assertEqual([len(x["cases"]) for x in result["results"]], [64] * 5)
        self.assertEqual([r["post_hoc_summaries"]["contact_set"]["original_flat"]["correct"]
                          for r in result["results"]], [52, 65, 66, 67, 74])
        self.assertEqual([r["post_hoc_summaries"]["contact_set"]["persistence_lift"]["correct"]
                          for r in result["results"]], [146, 126, 155, 149, 169])
        self.assertTrue(all(r["post_hoc_summaries"]["contact_set"]["nonparticipant_readings_match_truth"] == 256
                            for r in result["results"]))
        self.assertTrue(all(case["steps"][2]["persistence_lift"]["status"] == "NOT_SCORED"
                            for r in result["results"] for case in r["cases"]))
        self.assertNotIn("persistence_lift", archived["results"][0]["cases"][0]["steps"][0])


if __name__ == "__main__":
    unittest.main()
