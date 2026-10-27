"""G1 simulator invariants; no challenge seeds opened and no learner fitted."""
import dataclasses
import json
import unittest

from experiments.predictive_nucleus.world import Action, World, make_episode, observe, step, causal_replay


class WorldTests(unittest.TestCase):
    def setUp(self):
        self.base = World(("A", "B", "C", "D"), (1, 0, 1, 0), 0)

    def test_directed_truth_table_independent_of_step_implementation(self):
        # Independent equation: target flips iff the positional source bit is 1.
        for slot in (0, 1):
            for a in (0, 1):
                for b in (0, 1):
                    for reverse in (False, True):
                        world = World(("A", "B", "C"), (a, b, 0), slot)
                        pair = ("B", "A") if reverse else ("A", "B")
                        after = step(world, Action("contact", pair))
                        original = {"A": a, "B": b}
                        source, dest = pair[slot], pair[1 - slot]
                        expected = dict(original)
                        expected[dest] = original[dest] ^ original[source]
                        self.assertEqual(dict(zip(after.ids, after.bits)), {**expected, "C": 0})

    def test_pure_preview_and_source_only_preservation(self):
        before = dataclasses.asdict(self.base)
        after = step(self.base, Action("contact", ("A", "B")))
        self.assertEqual(after.bits, (1, 1, 1, 0))
        self.assertEqual(dataclasses.asdict(self.base), before)
        self.assertIsNot(after, self.base)
        self.assertEqual(step(self.base, Action("contact", ("B", "A"))).bits, self.base.bits)
        self.assertEqual(self.base.bits[0], after.bits[0])

    def test_intervention_and_observation_not_hidden_effect(self):
        set_b = step(self.base, Action("set", ("B",), 1))
        self.assertEqual(set_b.bits, (1, 1, 1, 0))
        observed = observe(set_b, 7, ("C", "A"))
        self.assertEqual(observed, {"t": 7, "measurements": [{"id": "C", "bit": 1}, {"id": "A", "bit": 1}]})
        self.assertEqual(step(set_b, Action("observe")), set_b)
        self.assertEqual(self.base.bits, (1, 0, 1, 0))

    def test_identity_equivariance(self):
        rename = {"A": "q3", "B": "q2", "C": "q1", "D": "q0"}
        action = Action("contact", ("A", "B"))
        out = step(self.base, action)
        renamed = World(tuple(rename[x] for x in self.base.ids), self.base.bits, 0)
        renamed_out = step(renamed, Action("contact", tuple(rename[x] for x in action.participants)))
        self.assertEqual(renamed_out.bits, out.bits)

    def test_invalid_actions_fail_closed(self):
        for action in [Action("set", ("A",), 2), Action("contact", ("A",)),
                       Action("observe", ("A",)), Action("contact", ("A", "Z")),
                       Action("touch", ("A", "B"))]:
            with self.assertRaises(ValueError):
                step(self.base, action)

    def test_deterministic_replay_and_distinct_lineage(self):
        one = make_episode("train", 101, 0, "single_contact")
        self.assertEqual(one, make_episode("train", 101, 0, "single_contact"))
        two = make_episode("train", 101, 1, "single_contact")
        self.assertNotEqual(one.lineage_id, two.lineage_id)
        self.assertEqual(len(one.states), len(one.actions) + 1)
        self.assertEqual(len(one.sensors), len(one.states))
        self.assertEqual({item["id"] for item in one.sensors[0]["measurements"]}, set(one.states[0].ids))
        self.assertEqual(one.sensors[0]["t"], 0)

    def test_never_present_gold_in_learner_input(self):
        episode = make_episode("validation", 211, 2, "two_contacts")
        seen = []
        def predict(inp):
            seen.append(("predict", inp))
            return None
        def receive(feedback):
            seen.append(("receive", feedback))
        causal_replay(episode, predict, receive)
        observed_first, feedback = seen[0][1], seen[1][1]
        self.assertEqual([event for event, _ in seen[:4]], ["predict", "receive", "predict", "receive"])
        self.assertEqual(set(observed_first), {"observation", "action"})
        self.assertEqual(set(observed_first["action"]), {"kind", "participants", "value"})
        text = json.dumps(observed_first)
        for forbidden in ("hidden_source_slot", "truth", "gold", "family", "source_role", "future"):
            self.assertNotIn(forbidden, text)
        self.assertEqual(feedback["t"], observed_first["observation"]["t"] + 1)
        self.assertEqual(feedback, episode.sensors[1])
        self.assertEqual(len(episode.gold_after(0)), len(episode.states[0].ids))

    def test_first_contact_not_identifiable_without_evidence(self):
        # Two different hidden worlds produce exactly identical learner input,
        # yet different correct next states. At t=0 no learner can distinguish.
        w0 = World(("A", "B", "C"), (1, 0, 0), 0)
        w1 = World(("A", "B", "C"), (1, 0, 0), 1)
        a = Action("contact", ("A", "B"))
        self.assertEqual(observe(w0, 0, w0.ids), observe(w1, 0, w1.ids))
        self.assertEqual(a.public(), a.public())
        self.assertNotEqual(step(w0, a).bits, step(w1, a).bits)

    def test_split_isolation(self):
        for split, seed, family in [("train", 401, "single_contact"),
                                    ("train", 101, "cycle"),
                                    ("ood_challenge", 101, "cycle")]:
            with self.assertRaisesRegex(ValueError, "split/family|seed"):
                make_episode(split, seed, 0, family)

    def test_no_predictions_or_training_in_generator(self):
        world = make_episode("train", 101, 3, "two_contacts")
        self.assertGreaterEqual(len(world.actions), 6)
        inputs, feedbacks = [], []
        causal_replay(world, lambda inp: inputs.append(inp), lambda fb: feedbacks.append(fb))
        for idx, (inp, output) in enumerate(zip(inputs, feedbacks)):
            self.assertEqual(inp, world.learner_turn(idx))
            self.assertEqual(output, world.reveal_after_prediction(idx))
            self.assertNotIn("truth", inp)


if __name__ == "__main__":
    unittest.main()
