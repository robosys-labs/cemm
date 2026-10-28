"""Protocol and scoring invariants for the public diagnostic, not G1."""
from collections import defaultdict
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json
import unittest

from experiments.predictive_nucleus.causal_replay import PublicReplay
from experiments.predictive_nucleus.development_run import (
    MODEL_NAMES, PROTOCOL_PATH, _evaluate_case, _summary, _training_history, read_protocol, score_forecast,
)
from experiments.predictive_nucleus.schedule_fixture import make_evaluator_episode as training_episode
from experiments.predictive_nucleus.schedule_fixture import sensor_view as training_view
from experiments.predictive_nucleus.sensor_controls import EventMemory
from experiments.predictive_nucleus.shared_training_smoke import collect_shared, collect_shared_development
from experiments.predictive_nucleus.two_pair_fixture import make_evaluator_episode as evaluation_episode
from experiments.predictive_nucleus.two_pair_fixture import sensor_view as evaluation_view
from experiments.predictive_nucleus.world import Episode


class UniformKernel:
    def contact(self, a, b, hypothesis):
        return (.25, .25, .25, .25)

    def intervention(self, previous, value):
        return (.5, .5)


class UniformFlat:
    def reset(self, anchor, *, sensor_error_rate, sensor_metadata_mode):
        self.ids = tuple(sorted(item["id"] for item in anchor["measurements"]))
        self.pending = False

    def commit(self, action, *, temperature):
        if self.pending:
            raise RuntimeError("prediction already pending")
        self.pending = True
        return {(a, b, c): .125 for a in (0, 1) for b in (0, 1) for c in (0, 1)}

    def receive(self, feedback):
        if not self.pending:
            raise RuntimeError("feedback before prediction")
        self.pending = False


class DevelopmentDiagnosticTests(unittest.TestCase):
    def test_public_first_contact_fixture_oracle_majority_limit(self):
        # This finite enumeration applies only to a deterministic reset model
        # with fixed weights and access limited to the current input. It is
        # not a G1 gate, a claim about public-ID leakage in other generators,
        # or a limit for a model that reads evaluator/future records.
        groups = defaultdict(lambda: defaultdict(int))
        for case in range(64):
            episode = evaluation_episode(case, block=0)
            first_turn = evaluation_view(episode).learner_turn(0)
            key = json.dumps(first_turn, sort_keys=True)
            gold = episode.gold_after(0)
            truth = tuple(gold[name] for name in sorted(gold))
            groups[key][truth] += 1
        self.assertEqual(len(groups), 8)
        self.assertEqual(sum(sum(counts.values()) for counts in groups.values()), 64)
        self.assertEqual(sum(max(counts.values()) for counts in groups.values()), 40)

    def test_frozen_protocol_hash_and_inventory(self):
        plan = read_protocol()
        self.assertEqual(plan["training"]["blocks"], [0, 1])
        self.assertEqual(plan["evaluation"]["scored_actions"], [0, 1, 2, 3, 4])
        self.assertEqual(plan["evaluation"]["strata"], {"contact_set": [0, 1, 3, 4], "observe": [2]})
        with TemporaryDirectory() as directory:
            path = Path(directory) / "modified.json"
            path.write_bytes(PROTOCOL_PATH.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "protocol hash"):
                read_protocol(path)

    def test_observe_insertion_preserves_original_local_samples(self):
        for block in (0, 1):
            for case in range(32):
                episode = training_episode(case, block=block)
                before = collect_shared(training_view(episode))
                history = _training_history(episode)
                after = collect_shared_development(history)
                self.assertEqual((before.contacts, before.interventions), (after.contacts, after.interventions))
                self.assertEqual(len(after.flat_rows), 5)
                self.assertEqual(sum(value >= 0 for _, target in after.flat_rows for value in target), 8)
                self.assertEqual(history.learner_turn(1)["action"], {"kind": "observe", "participants": []})
                self.assertEqual({x["id"] for x in history.reveal_after_prediction(1)["measurements"]},
                                 set(history.learner_turn(0)["action"]["participants"]))
                self.assertEqual(sum(features[32] != 0 for features, _ in after.flat_rows), 1)

    def test_scoring_preserves_abstention_zero_and_proper_joint_brier(self):
        truth = (1, 1, 1)
        abstain = score_forecast("ABSTAIN", "UNSEEN_CONTEXT", None, truth)
        self.assertIsNone(abstain["truth_probability"])
        self.assertIsNone(abstain["joint_log_score"])
        self.assertIsNone(abstain["joint_brier"])
        deterministic_wrong = score_forecast("PREDICTED", None, {(0, 0, 0): 1.0}, truth)
        self.assertEqual(deterministic_wrong["truth_probability"], 0.0)
        self.assertTrue(deterministic_wrong["joint_log_score"]["zero_probability"])
        self.assertTrue(deterministic_wrong["joint_log_score"]["floor_applied"])
        self.assertIsNone(deterministic_wrong["joint_log_score"]["uncapped_log_loss"])
        self.assertEqual(deterministic_wrong["joint_brier"], 2.0)
        tied = score_forecast("PREDICTED", None, {(1, 1, 1): .5, (0, 0, 0): .5}, truth)
        self.assertEqual(tied["map_world"], [0, 0, 0])
        self.assertEqual(tied["joint_brier"], .5)
        correct = score_forecast("PREDICTED", None, {truth: 1.0}, truth)
        summary = _summary([abstain, deterministic_wrong, correct])
        self.assertEqual((summary["queries"], summary["answered"], summary["abstained"]), (3, 2, 1))
        self.assertEqual((summary["coverage"], summary["correct_per_query"], summary["wrong_per_query"]),
                         (2/3, 1/3, 1/3))
        self.assertEqual(summary["accuracy_answered"], .5)
        self.assertTrue(summary["joint_log_loss"]["uncapped_mean_is_infinite"])
        self.assertIsNone(summary["joint_log_loss"]["uncapped_mean"])
        with self.assertRaises(ValueError):
            score_forecast("PREDICTED", None, {(0, 0, 0): float("nan")}, truth)
        with self.assertRaises(ValueError):
            score_forecast("PREDICTED", None, {(0, 0, 0): .3}, truth)
        with self.assertRaises(ValueError):
            score_forecast("ABSTAIN", None, {(0, 0, 0): 1.0}, truth)

    def test_all_forecasts_precede_oracle_reads_and_histories_match(self):
        episode = evaluation_episode(0)
        passes = []
        original_run, original_gold = PublicReplay.run, Episode.gold_after

        def recorded_run(replay, first, second):
            result = original_run(replay, first, second)
            passes.append((first, second))
            return result

        def after_forecasts(source, index):
            self.assertEqual(len(passes), 2)
            self.assertTrue(all(len(consumer.forecasts) == 5 for pair in passes for consumer in pair))
            return original_gold(source, index)

        with patch.object(PublicReplay, "run", recorded_run), patch.object(Episode, "gold_after", after_forecasts):
            rows, public_history, costs = _evaluate_case(episode, UniformKernel(), UniformFlat(), EventMemory((), 0, 0))
        self.assertEqual(len(rows), 5)
        self.assertEqual(len(public_history), 11)
        self.assertEqual(set(costs), set(MODEL_NAMES))
        self.assertEqual([row["action_kind"] for row in rows], ["contact", "set", "observe", "contact", "set"])
        for row in rows:
            self.assertEqual(set(row["models"]), set(MODEL_NAMES))
            self.assertEqual(row["models"]["local_memory_with_persistence"]["status"], "ABSTAIN")
            self.assertEqual(len(row["models"]["flat"]["world_probabilities"]), 8)
            diagnostic = row["models"]["structured"]["feedback_diagnostic"]
            self.assertIn("observed_probability", diagnostic)
            self.assertIs(type(diagnostic["retained_unconditioned_forecast"]), bool)
        json.dumps(rows, allow_nan=False)


if __name__ == "__main__":
    unittest.main()
