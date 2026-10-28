"""Public collection and one-step wiring checks, not scientific evaluation."""
from copy import deepcopy
from dataclasses import replace
import importlib.util
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus.flat_data import sensor_episode
from experiments.predictive_nucleus.schedule_fixture import make_evaluator_episode, sensor_view
from experiments.predictive_nucleus.shared_training_smoke import (
    _FlatCollector, _StructuredCollector, collect_shared, collect_shared_development,
)


def fixture(case=0):
    return sensor_view(make_evaluator_episode(case))


class SharedCollectionTests(unittest.TestCase):
    def test_all_public_rows_match_offline_extractors_without_gold(self):
        for case in range(32):
            view = fixture(case)
            collected = collect_shared(view)
            self.assertEqual([(list(x), list(y)) for x, y in collected.flat_rows], sensor_episode(view))
            self.assertEqual(len(collected.contacts), 2)
            self.assertEqual(len(collected.interventions), 2)
            self.assertEqual(len(collected.history), 9)  # anchor + four turn/feedback pairs
            self.assertFalse(hasattr(collected, "states"))
            for t in range(4):
                turn, feedback = view.learner_turn(t), view.reveal_after_prediction(t)
                pre = {m["id"]: m["bit"] for m in turn["observation"]["measurements"]}
                post = {m["id"]: m["bit"] for m in feedback["measurements"]}
                action = turn["action"]
                if t < 2:
                    a, b = action["participants"]
                    self.assertEqual(collected.contacts[t], (pre[a], pre[b], post[a], post[b]))
                else:
                    a = action["participants"][0]
                    self.assertEqual(collected.interventions[t - 2], (pre[a], action["value"], post[a]))
                # Three participants slots are invalid; the unmeasured nonparticipant
                # in the three-entity world must also remain masked, not imputed.
                self.assertEqual(sum(v >= 0 for v in collected.flat_rows[t][1]),
                                 len(feedback["measurements"]))
                self.assertIn(-1, collected.flat_rows[t][1])

    def test_future_feedback_and_actions_do_not_modify_prior_features(self):
        original = fixture(8)
        collected = collect_shared(original)
        for t in range(1, 5):
            values = list(original._observations)
            sensor = list(values[t])
            sensor[0] = (sensor[0][0], sensor[0][1] ^ 1)
            values[t] = tuple(sensor)
            altered = collect_shared(replace(original, _observations=tuple(values)))
            for i in range(t):
                self.assertEqual(collected.flat_rows[i][0], altered.flat_rows[i][0])
                if i + 1 < t:
                    self.assertEqual(collected.flat_rows[i][1], altered.flat_rows[i][1])
            self.assertNotEqual(collected.flat_rows[t - 1][1], altered.flat_rows[t - 1][1])
        for t in (2, 3):
            actions = list(original._action_records)
            kind, members, value = actions[t]
            actions[t] = (kind, members, 1 - value)
            altered = collect_shared(replace(original, _action_records=tuple(actions)))
            for i in range(t):
                self.assertEqual(collected.flat_rows[i][0], altered.flat_rows[i][0])
                self.assertEqual(collected.flat_rows[i][1], altered.flat_rows[i][1])

    def test_sequencing_validation_and_time_type(self):
        view = fixture()
        collector = _FlatCollector()
        with self.assertRaises(RuntimeError):
            collector.predict(view.learner_turn(0))
        collector.start(view.learner_turn(0)["observation"])
        with self.assertRaises(RuntimeError):
            collector.start(view.learner_turn(0)["observation"])
        with self.assertRaises(RuntimeError):
            collector.receive(view.reveal_after_prediction(0))
        collector.predict(view.learner_turn(0))
        with self.assertRaises(RuntimeError):
            collector.predict(view.learner_turn(0))
        feedback = deepcopy(view.reveal_after_prediction(0))
        feedback["t"] = True
        with self.assertRaises(ValueError):
            collector.receive(feedback)
        collector.receive(view.reveal_after_prediction(0))
        bad = view.learner_turn(1)
        bad["observation"]["measurements"][0]["bit"] ^= 1
        with self.assertRaises(ValueError):
            collector.predict(bad)
        collector.predict(view.learner_turn(1))

    def test_partial_collection_failure_does_not_return_rows(self):
        view = fixture()
        with patch("experiments.predictive_nucleus.shared_training_smoke._StructuredCollector._accept",
                   side_effect=ValueError("structured collection failure")):
            with self.assertRaisesRegex(ValueError, "structured collection failure"):
                collect_shared(view)
        complete = collect_shared(view)
        self.assertEqual((len(complete.flat_rows), len(complete.contacts), len(complete.interventions)),
                         (4, 2, 2))

    def test_missing_contact_input_is_not_imputed(self):
        anchor = fixture().learner_turn(0)["observation"]
        a, b = [item["id"] for item in anchor["measurements"][:2]]
        collector = _StructuredCollector()
        collector.start(anchor)
        collector.predict({"observation": anchor, "action": {"kind": "set", "participants": [a], "value": 0}})
        pre = {"t": 1, "measurements": [{"id": a, "bit": 0}]}
        collector.receive(pre)
        collector.predict({"observation": pre, "action": {"kind": "contact", "participants": [a, b]}})
        collector.receive({"t": 2, "measurements": [{"id": a, "bit": 0}, {"id": b, "bit": 1}]})
        self.assertEqual(collector.contacts, [])

    @unittest.skipUnless(importlib.util.find_spec("torch"), "PyTorch is not installed")
    def test_existing_tensor_paths_and_one_step_wiring(self):
        import torch
        from experiments.predictive_nucleus.flat_reference import batch_episodes
        from experiments.predictive_nucleus.latent_model import build_samples, sensor_only_samples
        from experiments.predictive_nucleus.shared_training_smoke import tensorize, run_fixture
        views = [fixture(i) for i in range(32)]
        records = [collect_shared(view) for view in views]
        for view, record in zip(views, records):
            contacts, interventions = sensor_only_samples(view)
            self.assertEqual(record.contacts, tuple(contacts))
            self.assertEqual(record.interventions, tuple(interventions))
        batch, samples = tensorize(records)
        expected_batch, expected_samples = batch_episodes(views), build_samples(views)
        for x, expected in zip(batch, expected_batch):
            self.assertTrue(torch.equal(x, expected))
        self.assertEqual(samples.episodes, expected_samples.episodes)
        for name in ("contact", "episode_id", "intervention"):
            self.assertTrue(torch.equal(getattr(samples, name), getattr(expected_samples, name)))
        self.assertEqual(samples.episode_id.tolist(), [i for i in range(32) for _ in range(2)])
        prior_rng = torch.random.get_rng_state().clone()
        prior_threads = torch.get_num_threads()
        report = run_fixture()
        self.assertTrue(torch.equal(torch.random.get_rng_state(), prior_rng))
        self.assertEqual(torch.get_num_threads(), prior_threads)
        self.assertEqual(report["status"], "PUBLIC_ONE_STEP_WIRING_ONLY")
        self.assertEqual(report["gate_g1"], "NOT_RUN")
        self.assertEqual((report["episodes"], report["events"], report["observed_bits"]), (32, 128, 192))
        self.assertEqual((report["contact_samples"], report["set_samples"], report["structured_episode_groups"]), (64, 64, 32))
        self.assertEqual((report["structured_steps"], report["flat_steps"]), (1, 1))
        self.assertTrue(all(report["structured_check"].values()))
        self.assertTrue(all(report["flat_check"].values()))
        self.assertEqual(set(report["tensor_sha256"]), {"flat_features", "flat_targets", "flat_valid",
                                                        "structured_contact", "structured_episode_id",
                                                        "structured_intervention"})
        self.assertTrue(all(len(v) == 64 for v in report["tensor_sha256"].values()))
        self.assertEqual(len(report["flat_weights_sha256"]), 64)
        self.assertEqual(len(report["structured_weights_sha256"]), 64)
        self.assertEqual(len(report["torch_config_sha256"]), 64)
        def fail_after_rng_use():
            torch.manual_seed(123)
            raise ValueError("synthetic failure")
        with patch("experiments.predictive_nucleus.shared_training_smoke._run_fixture_once",
                   side_effect=fail_after_rng_use):
            with self.assertRaisesRegex(ValueError, "synthetic failure"):
                run_fixture()
        self.assertTrue(torch.equal(torch.random.get_rng_state(), prior_rng))
        self.assertEqual(torch.get_num_threads(), prior_threads)


class TwoPairCollectionTests(unittest.TestCase):
    @staticmethod
    def fixture(case=0):
        from experiments.predictive_nucleus.two_pair_fixture import make_evaluator_episode, sensor_view
        return sensor_view(make_evaluator_episode(case))

    @staticmethod
    def collect(view):
        from experiments.predictive_nucleus.causal_replay import DevelopmentHistory
        return collect_shared_development(DevelopmentHistory.from_sensor_view(view))

    def test_all_public_two_pair_histories_produce_shared_samples(self):
        for case in range(64):
            view = self.fixture(case)
            record = self.collect(view)
            self.assertEqual(len(record.flat_rows), 5)
            self.assertEqual((len(record.contacts), len(record.interventions)), (2, 2))
            self.assertEqual(len(record.history), 11)  # anchor + five turns and feedbacks
            self.assertEqual([(list(x), list(y)) for x, y in record.flat_rows], sensor_episode(view))
            contacts, sets = [], []
            for i in range(5):
                turn, feedback = view.learner_turn(i), view.reveal_after_prediction(i)
                before = {m['id']: m['bit'] for m in turn['observation']['measurements']}
                after = {m['id']: m['bit'] for m in feedback['measurements']}
                action, names = turn['action'], turn['action']['participants']
                if action['kind'] == 'contact':
                    self.assertTrue(all(n in before and n in after for n in names))
                    contacts.append((before[names[0]], before[names[1]], after[names[0]], after[names[1]]))
                elif action['kind'] == 'set':
                    self.assertTrue(names[0] in before and names[0] in after)
                    sets.append((before[names[0]], action['value'], after[names[0]]))
                else:
                    self.assertEqual(action, {'kind': 'observe', 'participants': []})
                    bc = set(view.learner_turn(3)['action']['participants'])
                    self.assertEqual(set(after), bc)
                    self.assertEqual(sum(x >= 0 for x in record.flat_rows[i][1]), 2)
            self.assertEqual(record.contacts, tuple(contacts))
            self.assertEqual(record.interventions, tuple(sets))

    def test_future_feedback_and_action_do_not_change_earlier_features(self):
        original = self.fixture(9)
        rows = self.collect(original).flat_rows
        for time in range(1, 6):
            observations = list(original._observations)
            reading = list(observations[time])
            reading[0] = (reading[0][0], 1 - reading[0][1])
            observations[time] = tuple(reading)
            altered = self.collect(replace(original, _observations=tuple(observations))).flat_rows
            for earlier in range(time):
                self.assertEqual(rows[earlier][0], altered[earlier][0])
                if earlier + 1 < time:
                    self.assertEqual(rows[earlier][1], altered[earlier][1])
            self.assertNotEqual(rows[time - 1][1], altered[time - 1][1])
        for time in (1, 4):
            actions = list(original._action_records)
            kind, members, value = actions[time]
            actions[time] = (kind, members, 1 - value)
            altered = self.collect(replace(original, _action_records=tuple(actions))).flat_rows
            for earlier in range(time):
                self.assertEqual(rows[earlier], altered[earlier])

    def test_existing_collection_does_not_silently_accept_the_new_schedule(self):
        view = self.fixture()
        with self.assertRaises(ValueError):
            collect_shared(view)
        self.assertEqual(len(collect_shared(fixture()).flat_rows), 4)

    @unittest.skipUnless(importlib.util.find_spec('torch'), 'PyTorch is not installed')
    def test_actual_legacy_extractors_and_episode_grouping(self):
        import torch
        from experiments.predictive_nucleus.flat_reference import batch_episodes
        from experiments.predictive_nucleus.latent_model import build_samples, sensor_only_samples
        from experiments.predictive_nucleus.shared_training_smoke import tensorize
        views = [self.fixture(case) for case in range(64)]
        records = [self.collect(view) for view in views]
        for view, record in zip(views, records):
            contacts, interventions = sensor_only_samples(view)
            self.assertEqual(record.contacts, tuple(contacts))
            self.assertEqual(record.interventions, tuple(interventions))
        batch, samples = tensorize(records)
        legacy_batch, legacy_samples = batch_episodes(views), build_samples(views)
        for actual, expected in zip(batch, legacy_batch):
            self.assertTrue(torch.equal(actual, expected))
        self.assertEqual(samples.episodes, 64)
        for key in ('contact', 'episode_id', 'intervention'):
            self.assertTrue(torch.equal(getattr(samples, key), getattr(legacy_samples, key)))
        self.assertEqual(samples.episode_id.tolist(), [i for i in range(64) for _ in range(2)])
        self.assertEqual(tuple(batch[0].shape[:2]), (5, 64))
        self.assertTrue(bool((batch[2][2]).all()))  # observe is a real measured event


if __name__ == "__main__":
    unittest.main()
