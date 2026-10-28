"""Synthetic validation only: never evaluate the opened case or fit a model."""
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus.diagnose_failed_case6 import ARMS, SEEDS, _forbid_truth, _progress, inspect_forecast


class FailedCaseDiagnosticTests(unittest.TestCase):
    def test_probability_contract_and_abstention(self):
        self.assertEqual(inspect_forecast(("PREDICTED", None, {(0, 1, 0): .4, (1, 0, 1): .6}), 3), [])
        self.assertEqual(inspect_forecast(("ABSTAIN", "unseen", None), 3), [])
        self.assertEqual(inspect_forecast(("ABSTAIN", "unseen", {(0, 0, 0): 1.}), 3)[0]["kind"],
                         "abstention_with_distribution")
        self.assertEqual(inspect_forecast(("PREDICTED", None, {}), 3)[0]["kind"],
                         "invalid_status_or_distribution")
        for value in (1.0000001192092896, -0.1, float("nan"), float("inf"), True, "1"):
            problems = inspect_forecast(("PREDICTED", None, {(0, 0, 0): value}), 3)
            self.assertEqual(problems[0]["kind"], "invalid_probability")
            self.assertEqual(problems[0]["probability"], repr(value))
            json.dumps(problems, allow_nan=False)
        self.assertEqual(inspect_forecast(("PREDICTED", None, {(0, 0): 1.}), 3)[0]["kind"], "invalid_world")
        self.assertEqual(inspect_forecast(("PREDICTED", None, {(0, 0, 0): .9}), 3)[0]["kind"], "not_normalized")

    def test_tolerates_joint_sum_rounding_but_not_out_of_range_mass(self):
        almost = {(0, 0, 0): .6000002, (1, 1, 1): .4}
        self.assertEqual(inspect_forecast(("PREDICTED", None, almost), 3), [])
        above_one = {(0, 0, 0): 1.0000000000000002}
        self.assertEqual(inspect_forecast(("PREDICTED", None, above_one), 3)[0]["kind"], "invalid_probability")

    def test_forbid_truth_guard(self):
        with self.assertRaisesRegex(RuntimeError, "must not read evaluator truth"):
            _forbid_truth(None, 0)

    def test_checkpoint_inventory_requires_logged_hashes_and_complete_set(self):
        with TemporaryDirectory() as root:
            directory = Path(root)
            failed = {"status": "INCOMPLETE", "phase": "evaluation", "message": "invalid represented world",
                      "completed_cases": list(range(6))}
            failure_bytes = json.dumps(failed).encode()
            (directory / "FAILED.json").write_bytes(failure_bytes)
            rows = [{"phase": "case_started", "case": 6}]
            for seed in SEEDS:
                for arm, target in ARMS:
                    key = f"{arm}/{target}/{seed}"
                    for model in ("structured", "flat"):
                        name = key.replace("/", "-") + "-" + model + ".pt"
                        content = name.encode()
                        (directory / name).write_bytes(content)
                        rows.append({"phase": "checkpoint_verified", "arm": key, "model": model,
                                     "checkpoint": {"path": name, "sha256": sha256(content).hexdigest(),
                                                    "weight_fingerprint": "synthetic"}})
            for arm in ("repeated", "augmented"):
                for name in ("event", "literal", "role"):
                    rows.append({"phase": "control_fit_finished", "id_arm": arm, "model": name,
                                 "table_sha256": "synthetic"})
            progress_bytes = ("\n".join(json.dumps(row) for row in rows) + "\n").encode()
            (directory / "progress.jsonl").write_bytes(progress_bytes)
            with patch("experiments.predictive_nucleus.diagnose_failed_case6.FAILURE_SHA256",
                       sha256(failure_bytes).hexdigest()), patch(
                           "experiments.predictive_nucleus.diagnose_failed_case6.PROGRESS_SHA256",
                           sha256(progress_bytes).hexdigest()):
                checkpoints, controls = _progress(directory)
                self.assertEqual((len(checkpoints), len(controls)), (40, 6))
                (directory / "FAILED.json").write_bytes(failure_bytes + b" ")
                with self.assertRaisesRegex(ValueError, "failure or progress log hash mismatch"):
                    _progress(directory)
                (directory / "FAILED.json").write_bytes(failure_bytes)
                (directory / "progress.jsonl").write_bytes(progress_bytes + b" ")
                with self.assertRaisesRegex(ValueError, "progress log hash mismatch"):
                    _progress(directory)
                (directory / "progress.jsonl").write_bytes(progress_bytes)
                path = directory / next(iter(checkpoints.values()))["path"]
                path.write_bytes(b"tampered")
                with self.assertRaisesRegex(ValueError, "checkpoint byte hash"):
                    _progress(directory)
                path.write_bytes(path.name.encode())
                (directory / "COMPLETE").write_text("not allowed")
                with self.assertRaisesRegex(ValueError, "not the expected incomplete"):
                    _progress(directory)


if __name__ == "__main__":
    unittest.main()
