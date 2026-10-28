import unittest
from copy import deepcopy
from dataclasses import FrozenInstanceError

from experiments.predictive_nucleus.causal_replay import DevelopmentHistory, PublicReplay
from experiments.predictive_nucleus.history_memory import HistoryMemory
from experiments.predictive_nucleus.schedule_fixture import make_evaluator_episode, sensor_view


def history(last=(0, 0, 0), names=("a", "b", "c"), partial=False):
    a, b, c = names
    return DevelopmentHistory(
        (((a, 0), (b, 0), (c, 0)), ((a, 1), (b, 0)),
         ((a, last[0]), (b, last[1])) if partial else
         ((a, last[0]), (b, last[1]), (c, last[2]))),
        (("contact", (a, b), None), ("observe", (), None)))


def run_first(model, h):
    model.start(h.learner_turn(0)["observation"])
    first = model.predict(h.learner_turn(0))
    model.receive(h.reveal_after_prediction(0))
    return first, model.predict(h.learner_turn(1))


class HistoryMemoryTests(unittest.TestCase):
    def test_only_complete_sensor_targets_contribute(self):
        a, b = history((0, 0, 0)), history((1, 1, 1))
        memory = HistoryMemory.fit([a, a, b, history(partial=True)])
        self.assertEqual((memory.episode_count, memory.total_events, memory.complete_targets), (4, 8, 3))
        first, second = run_first(memory.new_predictor(), a)
        self.assertEqual(first["status"], "ABSTAIN")
        self.assertIsNone(first["worlds"])
        self.assertEqual(second["ids"], ("a", "b", "c"))
        self.assertEqual(second["worlds"], {(0, 0, 0): 2 / 3, (1, 1, 1): 1 / 3})
        second["worlds"].clear()
        self.assertEqual(run_first(memory.new_predictor(), a)[1]["worlds"][(0, 0, 0)], 2 / 3)

    def test_literal_identity_and_complete_history(self):
        original = history()
        memory = HistoryMemory.fit([original])
        renamed = history(names=("x", "y", "z"))
        self.assertEqual(run_first(memory.new_predictor(), renamed)[1]["status"], "ABSTAIN")
        changed = DevelopmentHistory((original._observations[0], (("a", 0), ("b", 1)), original._observations[2]),
                                     original._action_records)
        self.assertEqual(run_first(memory.new_predictor(), changed)[1]["status"], "ABSTAIN")
        swapped_action = DevelopmentHistory(original._observations,
                                            (("contact", ("b", "a"), None), original._action_records[1]))
        self.assertEqual(run_first(memory.new_predictor(), swapped_action)[1]["status"], "ABSTAIN")
        reordered = DevelopmentHistory((original._observations[0], (("b", 0), ("a", 1)), original._observations[2]),
                                       original._action_records)
        self.assertEqual(run_first(memory.new_predictor(), reordered)[1]["status"], "ABSTAIN")

    def test_requires_prediction_before_feedback_and_valid_order(self):
        h = history()
        model = HistoryMemory.fit([h]).new_predictor()
        with self.assertRaises(RuntimeError):
            model.predict(h.learner_turn(0))
        model.start(h.learner_turn(0)["observation"])
        with self.assertRaises(RuntimeError):
            model.receive(h.reveal_after_prediction(0))
        model.predict(h.learner_turn(0))
        with self.assertRaises(RuntimeError):
            model.predict(h.learner_turn(0))
        with self.assertRaises(RuntimeError):
            model.start(h.learner_turn(0)["observation"])
        invalid = deepcopy(h.reveal_after_prediction(0))
        invalid["t"] = 9
        with self.assertRaises(ValueError):
            model.receive(invalid)
        model.receive(h.reveal_after_prediction(0))
        with self.assertRaises(ValueError):
            model.predict(h.learner_turn(0))
        self.assertEqual(model.predict(h.learner_turn(1))["status"], "PREDICTED")
        model.receive(h.reveal_after_prediction(1))

    def test_frozen_table_rejects_invalid_direct_construction(self):
        memory = HistoryMemory.fit([history()])
        key, outcomes = memory._rows[0]
        world, _ = outcomes[0]
        with self.assertRaises(FrozenInstanceError):
            memory._rows = ()
        for rows, episodes, events, complete in (
            (list(memory._rows), 1, 2, 1),
            (((key, ((list(world), 1),)),), 1, 2, 1),
            (((key, ((world, 0),)),), 1, 2, 1),
            (((key, ((world, 1), (world, 1))),), 1, 2, 2),
            ((memory._rows[0], memory._rows[0]), 1, 2, 2),
            (memory._rows, 1, 2, 0),
            (((key[:-1] + ("{}",), outcomes),), 1, 2, 1),
        ):
            with self.subTest(rows=rows, complete=complete):
                with self.assertRaises(ValueError):
                    HistoryMemory(rows, episodes, events, complete)

    def test_shared_replay_and_existing_partial_fixture(self):
        h = history()
        model = HistoryMemory.fit([h]).new_predictor()
        replay = PublicReplay.from_development_history(h)
        replay.run(model, HistoryMemory.fit([]).new_predictor())
        self.assertEqual(replay.state, "completed")
        samples = [DevelopmentHistory.from_sensor_view(sensor_view(make_evaluator_episode(i))) for i in range(32)]
        memory = HistoryMemory.fit(samples)
        self.assertEqual((memory.total_events, memory.complete_targets), (128, 0))
        self.assertEqual(run_first(memory.new_predictor(), samples[0])[1]["status"], "ABSTAIN")


if __name__ == "__main__":
    unittest.main()
