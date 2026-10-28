"""Invariant tests for the public full-sensor view; no fitting or scoring."""
import unittest
from copy import deepcopy
from dataclasses import replace

from experiments.predictive_nucleus.causal_replay import DevelopmentHistory, FullSensorHistory, PublicReplay
from experiments.predictive_nucleus.full_sensor_evaluation import full_sensor_evaluation_view
from experiments.predictive_nucleus.shared_training_smoke import collect_shared_full_sensor
from experiments.predictive_nucleus.two_pair_fixture import make_evaluator_episode, sensor_view
from experiments.predictive_nucleus.world import Action, observe, step


class FullSensorEvaluationTests(unittest.TestCase):
    def test_public_factorial_retains_actions_and_measures_all_entities(self):
        events = full_bits = old_bits = contacts = sets = observes = 0
        shared_ids = None
        for case in range(64):
            episode = make_evaluator_episode(case)
            original = sensor_view(episode)
            full = full_sensor_evaluation_view(episode)
            self.assertIs(type(full), FullSensorHistory)
            self.assertEqual(full._action_records, original._action_records)
            self.assertEqual(full._observations[0], original._observations[0])
            ids = tuple(sorted(name for name, _ in original._observations[0]))
            if shared_ids is None:
                shared_ids = ids
            self.assertEqual(ids, shared_ids)
            self.assertEqual(tuple(a[0] for a in full._action_records),
                             ("contact", "set", "observe", "contact", "set"))
            world = episode.states[0]
            for t, (kind, participants, value) in enumerate(full._action_records, 1):
                world = step(world, Action(kind, participants, value))
                self.assertEqual(world, episode.states[t])
                old, new = original._observations[t], full._observations[t]
                self.assertEqual(new[:len(old)], old)
                self.assertEqual(tuple(name for name, _ in new[len(old):]),
                                 tuple(name for name in ids if name not in dict(old)))
                self.assertEqual(set(dict(new)), set(ids))
                sampled = observe(world, t, tuple(name for name, _ in new))
                self.assertEqual(new, tuple((r["id"], r["bit"]) for r in sampled["measurements"]))
                events += 1
                full_bits += len(new)
                old_bits += len(old)
                contacts += kind == "contact"
                sets += kind == "set"
                observes += kind == "observe"
            records = collect_shared_full_sensor(full)
            self.assertEqual((len(records.flat_rows), len(records.contacts), len(records.interventions)), (5, 2, 2))
            self.assertEqual(sum(sum(bit >= 0 for bit in target) for _, target in records.flat_rows), 15)
        self.assertEqual((events, full_bits, old_bits, contacts, sets, observes), (320, 960, 512, 128, 128, 64))

    def test_replay_orders_callbacks_and_copies_full_history(self):
        history = full_sensor_evaluation_view(make_evaluator_episode(0))
        events = []

        class Consumer:
            def __init__(self, name, mutate):
                self.name, self.mutate = name, mutate

            def record(self, op, payload):
                events.append((self.name, op, deepcopy(payload)))
                if self.mutate:
                    observation = payload["observation"] if op == "predict" else payload
                    observation["measurements"].clear()
                    if op == "predict":
                        payload["action"]["participants"].clear()

            def start(self, anchor): self.record("start", anchor)
            def predict(self, turn): self.record("predict", turn)
            def receive(self, feedback): self.record("receive", feedback)

        replay = PublicReplay.from_full_sensor_history(history)
        replay.run(Consumer("first", True), Consumer("second", False))
        self.assertEqual(replay.state, "completed")
        self.assertEqual(events[0][2], events[1][2])
        for i in range(5):
            group = events[2 + 4 * i:6 + 4 * i]
            self.assertEqual([(name, op) for name, op, _ in group],
                             [("first", "predict"), ("second", "predict"),
                              ("first", "receive"), ("second", "receive")])
            self.assertEqual(group[0][2], group[1][2])
            self.assertEqual(group[1][2], history.learner_turn(i))
            self.assertEqual(group[2][2], group[3][2])
            self.assertEqual(group[3][2], history.reveal_after_prediction(i))

    def test_future_sensor_change_leaves_earlier_records_unchanged(self):
        history = full_sensor_evaluation_view(make_evaluator_episode(1))
        future = list(history._observations[4])
        name, bit = future[-1]
        future[-1] = (name, 1 - bit)
        changed = FullSensorHistory((*history._observations[:4], tuple(future), *history._observations[5:]),
                                    history._action_records)
        for i in range(3):
            self.assertEqual(changed.learner_turn(i), history.learner_turn(i))
            self.assertEqual(changed.reveal_after_prediction(i), history.reveal_after_prediction(i))
        self.assertNotEqual(changed.reveal_after_prediction(3), history.reveal_after_prediction(3))

    def test_mode_separation_and_inconsistent_evaluator_rejected(self):
        episode = make_evaluator_episode(0)
        full = full_sensor_evaluation_view(episode)
        with self.assertRaises(ValueError):
            PublicReplay.from_development_history(full)
        with self.assertRaises(ValueError):
            DevelopmentHistory(full._observations, full._action_records)
        with self.assertRaises(ValueError):
            full_sensor_evaluation_view(object())
        sensors = deepcopy(episode.sensors)
        sensors[0]["measurements"][0]["bit"] ^= 1
        with self.assertRaisesRegex(ValueError, "anchor sensor conflicts"):
            full_sensor_evaluation_view(replace(episode, sensors=sensors))
        # Corrupt an unobserved nonparticipant in the stored post-action
        # evaluator state: equality of the legacy visible readings alone must
        # not let an inconsistent episode silently pass.
        world = episode.states[1]
        other = next(name for name in world.ids if name not in episode.actions[0].participants)
        bits = list(world.bits)
        index = world.ids.index(other)
        bits[index] = 1 - bits[index]
        states = (episode.states[0], replace(world, bits=tuple(bits)), *episode.states[2:])
        with self.assertRaisesRegex(ValueError, "states disagree"):
            full_sensor_evaluation_view(replace(episode, states=states))


if __name__ == "__main__":
    unittest.main()
