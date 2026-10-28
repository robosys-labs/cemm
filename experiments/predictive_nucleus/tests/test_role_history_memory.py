import unittest
from itertools import permutations

from experiments.predictive_nucleus.causal_replay import FullSensorHistory, PublicReplay
from experiments.predictive_nucleus.full_sensor_evaluation import full_sensor_evaluation_view
from experiments.predictive_nucleus.full_sensor_fixture import make_full_training_history
from experiments.predictive_nucleus.role_history_memory import RoleHistoryMemory, _normalized_history
from experiments.predictive_nucleus.two_pair_fixture import make_evaluator_episode


def example(names=("a", "b", "c"), outcome=(1, 0, 1)):
    a, b, c = names
    return FullSensorHistory(
        (((c, 1), (a, 0), (b, 1)),
         ((b, outcome[1]), (c, outcome[2]), (a, outcome[0])),
         ((c, outcome[2]), (a, 0), (b, outcome[1]))),
        (("contact", (a, b), None), ("set", (a,), 0)))


def predict_first(memory, history):
    predictor = memory.new_predictor()
    predictor.start(history.learner_turn(0)["observation"])
    return predictor, predictor.predict(history.learner_turn(0))


def prefix_keys(history):
    normalized = _normalized_history(history)
    parts = [normalized._observations[0]]
    for action, feedback in zip(normalized._action_records, normalized._observations[1:], strict=True):
        parts.append(action)
        yield tuple(parts)
        parts.append(feedback)


class RoleHistoryMemoryTests(unittest.TestCase):
    def test_relabels_are_invariant_and_worlds_follow_original_id_order(self):
        h = example()
        memory = RoleHistoryMemory.fit([h, h, example(outcome=(0, 1, 1))])
        renamed = example(names=("z", "x", "y"))
        original_model, original = predict_first(memory, h)
        renamed_model, result = predict_first(memory, renamed)
        self.assertEqual(original["worlds"], {(1, 0, 1): 2 / 3, (0, 1, 1): 1 / 3})
        # Sorted physical IDs are x,y,z: first operand z, second x, remaining y.
        self.assertEqual(result["ids"], ("x", "y", "z"))
        self.assertEqual(result["worlds"], {(0, 1, 1): 2 / 3, (1, 1, 0): 1 / 3})
        original_model.receive(h.reveal_after_prediction(0))
        renamed_model.receive(renamed.reveal_after_prediction(0))
        second = renamed_model.predict(renamed.learner_turn(1))
        self.assertEqual(second["status"], "PREDICTED")
        self.assertEqual(second["worlds"], {(0, 1, 0): 1.0})
        for names in permutations(("red", "green", "blue")):
            renamed = example(names=names)
            _, result = predict_first(memory, renamed)
            self.assertEqual(result["status"], "PREDICTED")
            self.assertEqual(result["ids"], tuple(sorted(names)))
            expected = {tuple(dict(zip(names, bits))[name] for name in sorted(names)): probability
                        for bits, probability in (((1, 0, 1), 2 / 3), ((0, 1, 1), 1 / 3))}
            self.assertEqual(result["worlds"], expected)

    def test_sensor_order_is_ignored_but_history_and_actions_are_not(self):
        h = example()
        memory = RoleHistoryMemory.fit([h])
        reordered = FullSensorHistory(tuple(tuple(reversed(obs)) for obs in h._observations), h._action_records)
        model, first = predict_first(memory, reordered)
        self.assertEqual(first["status"], "PREDICTED")
        model.receive(reordered.reveal_after_prediction(0))
        turn = reordered.learner_turn(1)
        turn["action"]["value"] = 1
        self.assertEqual(model.predict(turn)["status"], "ABSTAIN")
        changed = FullSensorHistory((h._observations[0], (("a", 0), ("b", 1), ("c", 1)), h._observations[2]),
                                    h._action_records)
        model, _ = predict_first(memory, changed)
        model.receive(changed.reveal_after_prediction(0))
        self.assertEqual(model.predict(changed.learner_turn(1))["status"], "ABSTAIN")

    def test_unsupported_and_unseen_contexts_abstain(self):
        h = example()
        memory = RoleHistoryMemory.fit([h])
        no_contact = FullSensorHistory((h._observations[0], h._observations[1]), (("observe", (), None),))
        with self.assertRaises(ValueError):
            RoleHistoryMemory.fit([no_contact])
        model, result = predict_first(memory, no_contact)
        self.assertEqual(result["reason"], "UNSUPPORTED_FIRST_ACTION_OR_ANCHOR")
        model.receive(no_contact.reveal_after_prediction(0))
        four_ids = FullSensorHistory(((('a', 0), ('b', 1), ('c', 0), ('d', 0)),
                                      (('a', 0), ('b', 1), ('c', 0), ('d', 0))),
                                     (("contact", ("a", "b"), None),))
        with self.assertRaises(ValueError):
            RoleHistoryMemory.fit([four_ids])
        model, result = predict_first(memory, four_ids)
        self.assertEqual(result["reason"], "UNSUPPORTED_FIRST_ACTION_OR_ANCHOR")
        model.receive(four_ids.reveal_after_prediction(0))
        unseen = example(outcome=(0, 0, 0))
        # Different outcome only appears after first prediction; it must not
        # affect the first lookup, but makes the next prefix unseen.
        model, result = predict_first(memory, unseen)
        self.assertEqual(result["status"], "PREDICTED")
        model.receive(unseen.reveal_after_prediction(0))
        self.assertEqual(model.predict(unseen.learner_turn(1))["status"], "ABSTAIN")

    def test_feedback_order_full_policy_and_caller_copy(self):
        h = example()
        model = RoleHistoryMemory.fit([h]).new_predictor()
        anchor = h.learner_turn(0)["observation"]
        model.start(anchor)
        anchor["measurements"][0]["bit"] ^= 1
        with self.assertRaises(RuntimeError):
            model.receive(h.reveal_after_prediction(0))
        result = model.predict(h.learner_turn(0))
        self.assertEqual(result["status"], "PREDICTED")
        with self.assertRaises(RuntimeError):
            model.predict(h.learner_turn(0))
        with self.assertRaises(RuntimeError):
            model.start(h.learner_turn(0)["observation"])
        partial = h.reveal_after_prediction(0)
        partial["measurements"].pop()
        with self.assertRaises(ValueError):
            model.receive(partial)
        model.receive(h.reveal_after_prediction(0))
        self.assertEqual(model.predict(h.learner_turn(1))["status"], "PREDICTED")
        model.receive(h.reveal_after_prediction(1))

    def test_shared_replay_and_public_context_coverage_without_fitting(self):
        h = example()
        memory = RoleHistoryMemory.fit([h])
        PublicReplay.from_full_sensor_history(h).run(memory.new_predictor(), memory.new_predictor())
        training_keys = set()
        for block in (0, 1):
            for case in range(32):
                training_keys.update(prefix_keys(make_full_training_history(case, block=block)))
        counts = [0] * 5
        for case in range(64):
            view = full_sensor_evaluation_view(make_evaluator_episode(case))
            for i, key in enumerate(prefix_keys(view)):
                counts[i] += key in training_keys
        # Shared public cases and exact contexts, not a held-out score.
        self.assertEqual(counts, [64, 0, 0, 0, 0])


if __name__ == "__main__":
    unittest.main()
