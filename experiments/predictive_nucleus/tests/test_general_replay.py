"""Explicit development replay checks; no model training or challenge."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import unittest

from experiments.predictive_nucleus.causal_replay import DevelopmentHistory, PublicReplay
from experiments.predictive_nucleus.schedule_fixture import SensorEpisode
from experiments.predictive_nucleus.two_pair_fixture import make_evaluator_episode, sensor_view


class Consumer:
    def __init__(self, name, calls, mutate=False, fail=False):
        self.name, self.calls, self.mutate, self.fail = name, calls, mutate, fail

    def _record(self, name, value):
        self.calls.append((self.name, name, deepcopy(value)))
        if self.mutate:
            if name == "predict":
                value["observation"]["measurements"].clear()
                value["action"]["participants"].clear()
            else:
                value["measurements"].clear()
        if self.fail and name == "predict":
            raise ValueError("consumer failed")

    def start(self, anchor): self._record("start", anchor)
    def predict(self, turn): self._record("predict", turn)
    def receive(self, feedback): self._record("receive", feedback)


def view(case=0):
    return sensor_view(make_evaluator_episode(case))


class GeneralReplayTests(unittest.TestCase):
    def test_explicit_opt_in_keeps_old_four_step_boundary(self):
        source = view()
        with self.assertRaises(ValueError):
            PublicReplay(source)
        with self.assertRaises(ValueError):
            PublicReplay.from_development_history(source)
        history = DevelopmentHistory.from_sensor_view(source)
        self.assertEqual(len(history.actions), 5)
        self.assertEqual(history.learner_turn(2)["action"], {"kind": "observe", "participants": []})
        self.assertEqual(len(history.reveal_after_prediction(2)["measurements"]), 2)
        self.assertFalse(hasattr(history, "states"))
        self.assertFalse(hasattr(history, "gold_after"))
        calls = []
        replay = PublicReplay.from_development_history(history)
        replay.run(Consumer("first", calls, mutate=True), Consumer("second", calls))
        self.assertEqual(replay.state, "completed")
        self.assertEqual(calls[0][2], calls[1][2])
        for i in range(5):
            group = calls[2 + 4*i : 6 + 4*i]
            self.assertEqual([(n, op) for n, op, _ in group],
                             [("first", "predict"), ("second", "predict"),
                              ("first", "receive"), ("second", "receive")])
            self.assertEqual(group[0][2], group[1][2])
            self.assertEqual(group[0][2], source.learner_turn(i))
            self.assertEqual(group[2][2], group[3][2])
            self.assertEqual(group[2][2], source.reveal_after_prediction(i))

    def test_all_public_cases_preserve_exact_histories(self):
        for case in range(64):
            source = view(case)
            history = DevelopmentHistory.from_sensor_view(source)
            for i in range(5):
                self.assertEqual(history.learner_turn(i), source.learner_turn(i))
                self.assertEqual(history.reveal_after_prediction(i), source.reveal_after_prediction(i))
                if i < 4:
                    self.assertEqual(history.reveal_after_prediction(i),
                                     history.learner_turn(i + 1)["observation"])

    def test_freeze_copies_and_rejects_mutable_or_malformed_records(self):
        source = view()
        history = DevelopmentHistory.from_sensor_view(source)
        before = history.learner_turn(0)
        leaked = history.learner_turn(0)
        leaked["observation"]["measurements"].clear()
        leaked["action"]["participants"].clear()
        self.assertEqual(history.learner_turn(0), before)
        with self.assertRaises(FrozenInstanceError):
            history._observations = ()
        with self.assertRaises(ValueError):
            replace(history, _observations=list(history._observations))
        with self.assertRaises(ValueError):
            replace(history, _action_records=(list(history._action_records[0]), *history._action_records[1:]))
        with self.assertRaises(ValueError):
            replace(history, _observations=history._observations[:-1])
        with self.assertRaises(ValueError):
            DevelopmentHistory.from_sensor_view(None)
        with self.assertRaisesRegex(ValueError, "misaligned"):
            DevelopmentHistory.from_sensor_view(replace(source, _observations=source._observations[:-1]))
        with self.assertRaisesRegex(ValueError, "misaligned"):
            DevelopmentHistory.from_sensor_view(replace(source, _observations=source._observations + ((),)))
        raw_observations = list(source._observations)
        raw_observations[0] = list(raw_observations[0])
        with self.assertRaisesRegex(ValueError, "raw development observation"):
            DevelopmentHistory.from_sensor_view(replace(source, _observations=tuple(raw_observations)))
        raw_observations[0] = (list(source._observations[0][0]), *source._observations[0][1:])
        with self.assertRaisesRegex(ValueError, "raw development measurement"):
            DevelopmentHistory.from_sensor_view(replace(source, _observations=tuple(raw_observations)))

    def test_feedback_masks_and_id_bounds(self):
        source = view()
        # Contact can reveal any subset, including no participants.
        observations = list(source._observations)
        observations[1] = ()
        sparse = DevelopmentHistory.from_sensor_view(replace(source, _observations=tuple(observations)))
        self.assertEqual(sparse.reveal_after_prediction(0)["measurements"], [])
        # Contact cannot reveal a known nonparticipant, and no event may
        # introduce an identity absent from the supplied anchor.
        observations[1] = (source._observations[0][2],)
        nonparticipants = set(dict(source._observations[0])) - set(source._action_records[0][1])
        name = nonparticipants.pop()
        observations[1] = ((name, 0),)
        with self.assertRaisesRegex(ValueError, "only participants"):
            DevelopmentHistory.from_sensor_view(replace(source, _observations=tuple(observations)))
        observations[1] = (("new-id", 0),)
        with self.assertRaisesRegex(ValueError, "unknown"):
            DevelopmentHistory.from_sensor_view(replace(source, _observations=tuple(observations)))
        actions = list(source._action_records)
        actions[1] = ("set", actions[1][1], True)
        with self.assertRaises(ValueError):
            DevelopmentHistory.from_sensor_view(replace(source, _action_records=tuple(actions)))
        actions = list(source._action_records)
        actions[0] = ("contact", "AB", None)
        with self.assertRaisesRegex(ValueError, "raw development action"):
            DevelopmentHistory.from_sensor_view(replace(source, _action_records=tuple(actions)))
        for i in (0, 2):
            actions = list(source._action_records)
            kind, members, _ = actions[i]
            actions[i] = (kind, members, 1)
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "raw development action"):
                DevelopmentHistory.from_sensor_view(replace(source, _action_records=tuple(actions)))
            original = DevelopmentHistory.from_sensor_view(source)
            with self.subTest(kind=kind, direct=True), self.assertRaisesRegex(ValueError, "raw development action"):
                replace(original, _action_records=tuple(actions))

    def test_sensor_count_and_step_bounds(self):
        for n in range(3, 7):
            names = tuple(chr(65+i) for i in range(n))
            anchor = tuple((name, i % 2) for i, name in enumerate(names))
            one = SensorEpisode((anchor, ()), (("observe", (), None),))
            history = DevelopmentHistory.from_sensor_view(one)
            self.assertEqual(len(history.actions), 1)
            self.assertEqual(len(history.learner_turn(0)["observation"]["measurements"]), n)
            twelve = SensorEpisode((anchor,) + ((),) * 12, (("observe", (), None),) * 12)
            self.assertEqual(len(DevelopmentHistory.from_sensor_view(twelve).actions), 12)
            too_many = SensorEpisode((anchor,) + ((),) * 13, (("observe", (), None),) * 13)
            with self.assertRaises(ValueError):
                DevelopmentHistory.from_sensor_view(too_many)
        for n in (2, 7):
            anchor = tuple((str(i), 0) for i in range(n))
            with self.assertRaises(ValueError):
                DevelopmentHistory.from_sensor_view(SensorEpisode((anchor, ()), (("observe", (), None),)))
        with self.assertRaises(ValueError):
            DevelopmentHistory.from_sensor_view(SensorEpisode(((('A', 0), ('B', 0), ('C', 0)),), ()))

    def test_future_feedback_does_not_change_prior_delivered_inputs(self):
        source = view(7)
        for t in range(1, 6):
            observations = list(source._observations)
            row = list(observations[t])
            row[0] = (row[0][0], 1 - row[0][1])
            observations[t] = tuple(row)
            altered = replace(source, _observations=tuple(observations))
            histories = [DevelopmentHistory.from_sensor_view(s) for s in (source, altered)]
            logs = []
            for history in histories:
                calls = []
                PublicReplay.from_development_history(history).run(Consumer("first", calls), Consumer("second", calls))
                logs.append(calls)
            for i in range(t):
                self.assertEqual(logs[0][2 + 4*i][2], logs[1][2 + 4*i][2])
            self.assertNotEqual(logs[0][2 + 4*(t-1) + 2][2], logs[1][2 + 4*(t-1) + 2][2])

    def test_failure_aborts_without_feedback(self):
        history = DevelopmentHistory.from_sensor_view(view())
        calls = []
        replay = PublicReplay.from_development_history(history)
        with self.assertRaisesRegex(ValueError, "consumer failed"):
            replay.run(Consumer("first", calls), Consumer("second", calls, fail=True))
        self.assertEqual(replay.state, "aborted")
        self.assertEqual([op for _, op, _ in calls], ["start", "start", "predict", "predict"])
        with self.assertRaises(RuntimeError):
            replay.run(Consumer("first", calls), Consumer("second", calls))


if __name__ == "__main__":
    unittest.main()
