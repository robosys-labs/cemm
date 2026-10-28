"""Flat reference boundary and likelihood invariants, not scientific scores."""
import math
import unittest
from copy import deepcopy
from itertools import product

from experiments.predictive_nucleus.flat_data import FEATURES, event_features, initial_ids, sensor_episode
from experiments.predictive_nucleus.flat_trial import evaluate_models, frozen_config_v7
from experiments.predictive_nucleus.tests.test_uncertainty import ToyKernel
from experiments.predictive_nucleus.world import make_episode

try:
    import torch
except ModuleNotFoundError:
    torch = None


class SensorOnlyProxy:
    def __init__(self, episode):
        self._episode = episode
        self.actions = tuple(None for _ in episode.actions)

    def learner_turn(self, index):
        return self._episode.learner_turn(index)

    def reveal_after_prediction(self, index):
        return self._episode.reveal_after_prediction(index)

    @property
    def states(self):
        raise AssertionError("oracle state accessed")

    def gold_after(self, index):
        raise AssertionError("oracle gold accessed")


class FlatDataTests(unittest.TestCase):
    def test_sensor_only_proxy_and_fixed_feature_width(self):
        ep = make_episode("train", 101, 0, "single_contact")
        extracted = sensor_episode(SensorOnlyProxy(ep))
        self.assertEqual(len(extracted), len(ep.actions))
        self.assertTrue(all(len(x) == FEATURES == 36 and len(y) == 6 for x, y in extracted))
        self.assertTrue(all(v in (-1, 0, 1) for _, target in extracted for v in target))

    def test_missing_values_are_masked_and_sensor_metadata_is_supplied(self):
        obs = {"t": 0, "measurements": [{"id": "A", "bit": 1},
                                         {"id": "B", "bit": 0}, {"id": "C", "bit": 1}]}
        ids = initial_ids(obs)
        partial = {"t": 1, "measurements": [{"id": "A", "bit": 0}]}
        x = event_features(ids, partial, {"kind": "contact", "participants": ["A", "B"]},
                           sensor_error_rate=.08)
        self.assertEqual(x[:3], [0, 0, 0])
        self.assertEqual(x[6:9], [1, 0, 0])
        self.assertAlmostEqual(x[-1], .08)
        with self.assertRaises(ValueError):
            event_features(ids, partial, {"kind": "observe", "participants": []}, sensor_error_rate=.5)

    def test_v7_lock_does_not_run_scored_worlds(self):
        cfg = frozen_config_v7()
        self.assertEqual(cfg["flat_architecture"]["parameters_expected"], 1457)
        self.assertEqual(cfg["decision"], "G1_NOT_ADMITTED")

    def test_paired_evaluator_passes_only_public_actions_and_observations(self):
        class UniformFlat:
            def reset(self, anchor, *, sensor_error_rate):
                self.ids = initial_ids(anchor)
                self.time = anchor["t"]
                self.pending = False

            def commit(self, action, *, temperature):
                self.assert_public_action(action)
                self.pending = True

            def receive(self, observation):
                if not self.pending or observation["t"] != self.time + 1:
                    raise AssertionError("noncausal flat feedback")
                self.time += 1
                self.pending = False

            def preview(self, action, *, temperature):
                self.assert_public_action(action)
                if self.pending:
                    raise AssertionError("prediction before feedback")
                states = list(product((0, 1), repeat=len(self.ids)))
                return {bits: 1 / len(states) for bits in states}, None

            @staticmethod
            def assert_public_action(action):
                if set(action) - {"kind", "participants", "value"}:
                    raise AssertionError("nonpublic action field")

        cfg = deepcopy(frozen_config_v7())
        cfg["opened_v6_world_seeds"] = [951]
        cfg["new_public_world_seeds"] = [953]
        result = evaluate_models(ToyKernel(), UniformFlat(), 1.0, cfg, 1)
        for split in result.values():
            for summary in split.values():
                self.assertEqual(summary["flat"]["queries"], 2)
                self.assertEqual(summary["structured"]["queries"], 2)
                self.assertLessEqual(summary["mean_physical_probes"], 2)


@unittest.skipIf(torch is None, "PyTorch required for learned reference invariants")
class FlatTorchTests(unittest.TestCase):
    def test_parameter_budget_and_sensor_only_likelihood(self):
        from experiments.predictive_nucleus.flat_reference import FlatWorldGRU, sensor_nll
        self.assertEqual(FlatWorldGRU().param_count(), 1457)
        logits = torch.zeros((1, 1, 64))
        target = torch.tensor([[[1, -1, -1, -1, -1, -1]]])
        valid = torch.tensor([[True]])
        self.assertAlmostEqual(float(sensor_nll(logits, target, valid)), math.log(2), places=6)
        with self.assertRaises(ValueError):
            sensor_nll(logits, torch.full_like(target, -1), valid)

    def test_preview_is_pure_and_feedback_is_causally_required(self):
        from experiments.predictive_nucleus.flat_reference import FlatWorldGRU
        model = FlatWorldGRU()
        first = {"t": 0, "measurements": [{"id": "A", "bit": 1},
                                          {"id": "B", "bit": 0}, {"id": "C", "bit": 1}]}
        action = {"kind": "contact", "participants": ["A", "B"]}
        model.reset(first, sensor_error_rate=.08)
        one, _ = model.preview(action)
        two, _ = model.preview(action)
        self.assertEqual(one, two)
        self.assertEqual(len(one), 8)
        self.assertAlmostEqual(sum(one.values()), 1, places=6)
        model.commit(action)
        with self.assertRaises(RuntimeError):
            model.preview(action)
        with self.assertRaises(ValueError):
            model.receive({"t": 2, "measurements": []})
        model.receive({"t": 1, "measurements": [{"id": "A", "bit": 0}]})
        self.assertEqual(model.time, 1)
        self.assertIsNone(model.pending)

    def test_sensor_only_fit_and_disjoint_calibration_replay(self):
        from experiments.predictive_nucleus.flat_reference import batch_episodes, calibrate_flat, fit_flat
        train = [SensorOnlyProxy(make_episode("train", 101, i, "single_contact")) for i in range(3)]
        calibration = [SensorOnlyProxy(make_episode("calibration", 307, i, "single_contact")) for i in range(3)]
        batch = batch_episodes(train)
        model, report = fit_flat(batch, seed=7, max_steps=2, wall_budget_seconds=10, fixed_steps=2)
        self.assertEqual(report["gradient_steps"], 2)
        self.assertTrue(math.isfinite(report["training_sensor_nll"]))
        replay, replay_report = fit_flat(batch, seed=7, max_steps=2, wall_budget_seconds=10, fixed_steps=2)
        self.assertEqual(replay_report["schedule"], "fixed_replay")
        self.assertTrue(all(torch.equal(value, replay.state_dict()[name])
                            for name, value in model.state_dict().items()))
        temperature, info = calibrate_flat(model, batch_episodes(calibration))
        self.assertIn(temperature, (.5, .75, 1., 1.5, 2., 3.))
        self.assertEqual(info["episodes"], 3)


if __name__ == "__main__":
    unittest.main()
