"""G1b learning-surface invariants only; not a scientific generalization gate."""
import math
import unittest

import torch

from experiments.predictive_nucleus.model import SharedWorldModel
from experiments.predictive_nucleus.train import run
from experiments.predictive_nucleus.world import make_episode


class LearnerTests(unittest.TestCase):
    def setUp(self):
        torch.manual_seed(9)
        self.model = SharedWorldModel(hidden=12)
        self.first = {"t": 0, "measurements": [{"id": "B", "bit": 1},
                                                 {"id": "A", "bit": 0}, {"id": "C", "bit": 1}]}
        self.turn = {"observation": self.first,
                     "action": {"kind": "contact", "participants": ["B", "A"]}}

    def test_prediction_must_precede_feedback(self):
        self.model.reset(self.first)
        with self.assertRaises(RuntimeError):
            self.model.receive({"t": 1, "measurements": []})
        prediction = self.model.predict(self.turn)
        self.assertEqual(set(prediction), {"A", "B", "C"})
        self.assertTrue(all(torch.isfinite(v).item() and 0 <= v.item() <= 1 for v in prediction.values()))
        with self.assertRaises(RuntimeError):
            self.model.predict(self.turn)
        with self.assertRaises(RuntimeError):
            self.model.receive({"t": 2, "measurements": []})
        self.model.receive({"t": 1, "measurements": [{"id": "C", "bit": 1}]})
        self.assertEqual(self.model.t, 1)
        self.assertEqual(len(self.model.losses), 1)

    def test_sensor_order_invariance(self):
        self.model.reset(self.first)
        p1 = self.model.predict(self.turn)
        first_reverse = {"t": 0, "measurements": list(reversed(self.first["measurements"]))}
        self.model.reset(first_reverse)
        p2 = self.model.predict({"observation": first_reverse, "action": self.turn["action"]})
        self.assertTrue(all(torch.equal(p1[k], p2[k]) for k in p1))

    def test_train_only_consumes_sensor_observations(self):
        episode = make_episode("train", 101, 2, "single_contact")
        class NoOracleProxy:
            def __getattr__(self, name):
                if name in ("gold_after", "states"):
                    raise AssertionError("training read evaluator-only gold")
                return getattr(episode, name)
        optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        truth, predicted, baseline = run(self.model, NoOracleProxy(), optimizer)
        self.assertEqual((truth, predicted, baseline), ([], [], []))
        self.assertTrue(math.isfinite(self.model.episode_loss().item()))
        self.assertLess(self.model.parameter_count(), 100000)

    def test_evaluation_outputs_independent_no_change_control(self):
        episode = make_episode("validation", 211, 0, "single_contact")
        with torch.no_grad():
            truth, predicted, baseline = run(self.model, episode)
        self.assertEqual(len(truth), 1)
        self.assertEqual(truth[0]["case_id"], predicted[0]["case_id"])
        self.assertEqual(truth[0]["case_id"], baseline[0]["case_id"])
        self.assertEqual(set(baseline[0]["p1"]), set(truth[0]["truth"]))
        self.assertTrue(all(value in (0, 1) for value in baseline[0]["p1"].values()))


if __name__ == "__main__":
    unittest.main()
