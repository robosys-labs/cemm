"""Sensor-only baseline invariants; no training scores or challenge data."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import unittest

from experiments.predictive_nucleus.sensor_controls import EventMemory, NoChange


def obs(time, **bits):
    return {"t": time, "measurements": [{"id": name, "bit": bit} for name, bit in bits.items()]}


def contact(a, b):
    return {"kind": "contact", "participants": [a, b]}


def set_action(name, value):
    return {"kind": "set", "participants": [name], "value": value}


class SensorEpisode:
    def __init__(self, observations, actions):
        self.observations = deepcopy(observations)
        self._actions = deepcopy(actions)
        self.actions = (None,) * len(actions)

    @property
    def states(self):
        raise AssertionError("must not access evaluator state")

    def gold_after(self, index):
        raise AssertionError("must not access evaluator gold")

    def learner_turn(self, index):
        return {"observation": deepcopy(self.observations[index]), "action": deepcopy(self._actions[index])}

    def reveal_after_prediction(self, index):
        return deepcopy(self.observations[index + 1])


class SensorControlTests(unittest.TestCase):
    def test_persistence_updates_only_after_valid_feedback_and_masks_missing(self):
        control = NoChange()
        anchor = obs(0, A=0, B=1, C=1)
        control.start(anchor)
        turn = {"observation": anchor, "action": contact("A", "B")}
        preview = control.preview(turn)
        preview["B"] = 0
        self.assertEqual(control.preview(turn), {"A": 0, "B": 1, "C": 1})
        self.assertEqual(control.predict(turn), {"A": 0, "B": 1, "C": 1})
        with self.assertRaises(RuntimeError):
            control.predict(turn)
        with self.assertRaises(ValueError):
            control.receive(obs(2, B=0))
        with self.assertRaises(ValueError):
            control.receive(obs(1, Z=0))
        control.receive(obs(1, B=0))
        next_turn = {"observation": obs(1, B=0), "action": set_action("A", 1)}
        self.assertEqual(control.preview(next_turn), {"A": 0, "B": 0, "C": 1})
        wrong_turn = {"observation": obs(1, B=1), "action": set_action("A", 1)}
        with self.assertRaises(ValueError):
            control.preview(wrong_turn)
        self.assertEqual(control.predict(next_turn), {"A": 0, "B": 0, "C": 1})
        control.receive(obs(2))
        self.assertEqual(control.preview({"observation": obs(2), "action": contact("B", "A")}),
                         {"A": 0, "B": 0, "C": 1})
        with self.assertRaises(RuntimeError):
            control.receive(obs(3))

    def test_persistence_validation_and_atomic_reset(self):
        control = NoChange()
        with self.assertRaises(RuntimeError):
            control.preview({})
        control.start(obs(0, A=0, B=1, C=0))
        turn = {"observation": obs(0, A=0, B=1, C=0), "action": contact("A", "B")}
        for bad in (obs(True, A=0, B=1, C=0), obs(1, A=0, B=1), obs(1, A=True, B=1, C=0)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                control.start(bad)
            self.assertEqual(control.preview(turn), {"A": 0, "B": 1, "C": 0})
        control.predict(turn)
        with self.assertRaises(RuntimeError):
            control.start(obs(0, A=0, B=1, C=0))

    def test_event_memory_uses_observed_outcomes_and_freezes_counts(self):
        a = SensorEpisode([obs(0, A=0, B=1, C=0), obs(1, A=1, B=1), obs(2, A=0)],
                          [contact("A", "B"), set_action("A", 1)])
        b = SensorEpisode([obs(0, A=0, B=1, C=1), obs(1, A=0, B=0)], [contact("A", "B")])
        incomplete = SensorEpisode([obs(0, A=0, B=0, C=0), obs(1, A=1), obs(2, A=1, B=1)],
                                   [set_action("A", 1), contact("A", "B")])
        memory = EventMemory.fit([a, b, incomplete])
        self.assertEqual((memory.episode_count, memory.eligible_events), (3, 4))
        ids = ("A", "B", "C")
        query = {"observation": obs(10, A=0, B=1), "action": contact("A", "B")}
        got = memory.predict(ids, query)
        self.assertEqual(got, {"status": "PREDICTED", "reason": None,
                               "probabilities": {(0, 0): .5, (1, 1): .5}})
        got["probabilities"][(0, 0)] = 1.0
        a.observations[1]["measurements"][0]["bit"] ^= 1
        self.assertEqual(memory.predict(ids, query)["probabilities"], {(0, 0): .5, (1, 1): .5})
        with self.assertRaises(FrozenInstanceError):
            memory.rows = ()
        set_query = {"observation": obs(5, A=1), "action": set_action("A", 1)}
        self.assertEqual(memory.predict(ids, set_query)["probabilities"], {(0,): 1.0})

    def test_unseen_and_missing_context_abstain_and_order_is_respected(self):
        episode = SensorEpisode([obs(0, A=0, B=1, C=0), obs(1, A=1, B=0)], [contact("A", "B")])
        memory = EventMemory.fit([episode])
        ids = ("A", "B", "C")
        forward = {"observation": obs(0, A=0, B=1), "action": contact("A", "B")}
        reverse = {"observation": obs(0, A=0, B=1), "action": contact("B", "A")}
        missing = {"observation": obs(0, A=0), "action": contact("A", "B")}
        self.assertEqual(memory.predict(ids, forward)["probabilities"], {(1, 0): 1.0})
        self.assertEqual(memory.predict(ids, reverse)["reason"], "UNSEEN_CONTEXT")
        self.assertEqual(memory.predict(ids, missing)["reason"], "INCOMPLETE_CONTEXT")
        observe_turn = {"observation": obs(0, A=0), "action": {"kind": "observe", "participants": []}}
        self.assertEqual(memory.predict(ids, observe_turn)["reason"], "UNSUPPORTED_ACTION")
        self.assertEqual(EventMemory.fit([]).predict(ids, forward)["status"], "ABSTAIN")
        renamed = {"observation": obs(0, X=0, Y=1), "action": contact("X", "Y")}
        self.assertEqual(memory.predict(("X", "Y", "Z"), renamed)["probabilities"], {(1, 0): 1.0})

    def test_training_rejects_bad_timeline_and_does_not_read_future_gold(self):
        episode = SensorEpisode([obs(0, A=0, B=1, C=0), obs(2, A=1, B=0)], [contact("A", "B")])
        with self.assertRaises(ValueError):
            EventMemory.fit([episode])
        episode = SensorEpisode([obs(0, A=0, B=1, C=0), obs(1, A=1, B=0)], [contact("A", "B")])
        self.assertEqual(EventMemory.fit([episode]).eligible_events, 1)
        with self.assertRaises(ValueError):
            EventMemory.fit([SensorEpisode([obs(0, A=0, B=0, C=0)], [])])
        with self.assertRaises(ValueError):
            EventMemory.fit([SensorEpisode([obs(0, A=0, B=0, C=0), obs(1, Z=0)], [set_action("A", 1)])])

    def test_frozen_constructor_rejects_mutable_and_malformed_counts(self):
        invalid_rows = [
            [(('set', 0, 1), (((1,), 1),))],
            ((('set', 0, 1), [((1,), 1)]),),
            ((('set', 0, 1), (((1,), True),)),),
            ((('contact', 0, 1), (((1,), 1),)),),
            ((('set', 0, 1), (((1,), 0),)),),
            ((('set', 0, 1), (((1,), 1), ((1,), 1))),),
            ((('set', 0, 1), (((1,), 1),)), (('set', 0, 1), (((0,), 1),))),
        ]
        for rows in invalid_rows:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                EventMemory(rows, 1, 1)
        with self.assertRaises(ValueError):
            EventMemory(((('set', 0, 1), (((1,), 1),)),), 1, 2)
        self.assertEqual(EventMemory((), 0, 0).rows, ())

    def test_public_replay_integrates_both_sensor_controls_without_learning_on_query(self):
        from experiments.predictive_nucleus.causal_replay import PublicReplay
        from experiments.predictive_nucleus.schedule_fixture import make_evaluator_episode, sensor_view
        from experiments.predictive_nucleus.flat_data import initial_ids

        view = sensor_view(make_evaluator_episode(3))
        # Same fixture here checks the wiring only; no result or test claim.
        memory = EventMemory.fit([view])
        original = memory.rows

        class LocalEventAdapter:
            def __init__(self):
                self.results = []
                self.feedback = []

            def start(self, anchor):
                self.ids = initial_ids(anchor)

            def predict(self, turn):
                self.results.append(memory.predict(self.ids, turn))

            def receive(self, feedback):
                self.feedback.append(deepcopy(feedback))

        adapter = LocalEventAdapter()
        persistence = NoChange()
        replay = PublicReplay(view)
        replay.run(persistence, adapter)
        self.assertEqual(replay.state, "completed")
        self.assertEqual(len(adapter.results), 4)
        self.assertTrue(all(result["status"] == "PREDICTED" for result in adapter.results))
        self.assertEqual(adapter.feedback, [view.reveal_after_prediction(i) for i in range(4)])
        self.assertEqual(memory.rows, original)
        final_turn = {"observation": view.reveal_after_prediction(3), "action": contact(*view.learner_turn(0)["action"]["participants"])}
        self.assertEqual(set(persistence.preview(final_turn)), set(adapter.ids))


if __name__ == "__main__":
    unittest.main()
