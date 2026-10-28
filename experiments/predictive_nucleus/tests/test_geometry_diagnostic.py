"""Coverage-only public fixture tests; no model is trained or scored."""
import copy
import importlib.util
from dataclasses import replace
import unittest

from experiments.predictive_nucleus.geometry_diagnostic import coverage_report, participant_replay
from experiments.predictive_nucleus.world import Action, Episode, World, make_episode, step


def episode_for(actions):
    start = World(("A", "B", "C"), (1, 0, 1), 0)
    states = [start]
    for action in actions:
        states.append(step(states[-1], action))
    # Existing sensor records are deliberately irrelevant: participant readings
    # are freshly sampled from evaluator states, not intersected with old masks.
    sensors = tuple({"t": i, "measurements": []} for i in range(len(states)))
    return Episode("fixture", "development", "fixture", 1, tuple(states), tuple(actions), sensors)


class GeometryDiagnosticTests(unittest.TestCase):
    def test_fresh_action_local_feedback_and_exact_chronology(self):
        episode = episode_for((Action("set", ("A",), 0), Action("contact", ("B", "A")),
                               Action("observe"), Action("contact", ("A", "C"))))
        original = copy.deepcopy(episode)
        replay = participant_replay(episode)
        self.assertEqual({m["id"] for m in replay[0][0]["observation"]["measurements"]}, {"A", "B", "C"})
        self.assertEqual([[m["id"] for m in feedback["measurements"]] for _, feedback in replay],
                         [["A"], ["B", "A"], [], ["A", "C"]])
        for i, (turn, feedback) in enumerate(replay):
            self.assertEqual(set(turn), {"observation", "action"})
            self.assertEqual(set(feedback), {"t", "measurements"})
            self.assertEqual(feedback["t"], i + 1)
            self.assertTrue(all(set(m) == {"id", "bit"} for m in feedback["measurements"]))
            if i + 1 < len(replay):
                self.assertEqual(feedback, replay[i + 1][0]["observation"])
        replay[0][1]["measurements"][0]["bit"] = 9
        self.assertNotEqual(replay[0][1], replay[1][0]["observation"])
        self.assertEqual(episode, original)
        self.assertEqual(participant_replay(episode), participant_replay(original))

    def test_later_evaluator_state_does_not_change_earlier_input(self):
        episode = episode_for((Action("set", ("A",), 0), Action("contact", ("A", "B"))))
        altered_last = replace(episode.states[-1], bits=(1, 1, 0))
        altered = replace(episode, states=(*episode.states[:-1], altered_last))
        before = participant_replay(episode)
        after = participant_replay(altered)
        self.assertEqual(before[0], after[0])
        self.assertEqual(before[1][0], after[1][0])
        self.assertNotEqual(before[1][1], after[1][1])

    def test_counts_match_complete_sensor_pair_requirements(self):
        no_pair = episode_for((Action("set", ("A",), 1), Action("set", ("B",), 1),
                               Action("contact", ("A", "B")), Action("observe")))
        repeated = episode_for((Action("contact", ("A", "B")), Action("contact", ("B", "A"))))
        self_contact = episode_for((Action("contact", ("C", "C")),))
        report = coverage_report([no_pair, repeated, self_contact])
        self.assertEqual(report, {"episodes": 3, "actions": 7, "set_actions": 2,
                                  "contact_actions": 4, "observe_actions": 1,
                                  "empty_feedback": 1, "pre_measurements": 15,
                                  "post_measurements": 9, "complete_contact_pairs": 2,
                                  "complete_set_pairs": 1})
        self.assertEqual(coverage_report([])["complete_contact_pairs"], 0)

    def test_historical_training_schedule_coverage_regression(self):
        seeds = (101, 103, 107, 109, 113)
        episodes = [make_episode("train", seeds[i % len(seeds)], i,
                                 ("single_contact", "two_contacts")[i % 2])
                    for i in range(600)]
        self.assertEqual(coverage_report(episodes),
                         {"episodes": 600, "actions": 2978, "set_actions": 1800,
                          "contact_actions": 900, "observe_actions": 278,
                          "empty_feedback": 278, "pre_measurements": 5438,
                          "post_measurements": 3600, "complete_contact_pairs": 0,
                          "complete_set_pairs": 805})

    @unittest.skipUnless(importlib.util.find_spec("torch"), "PyTorch is not installed")
    def test_pair_counts_match_structured_sample_extractor(self):
        from experiments.predictive_nucleus.latent_model import sensor_only_samples
        fixtures = [
            episode_for((Action("set", ("A",), 1), Action("set", ("B",), 1),
                         Action("contact", ("A", "B")), Action("observe"))),
            episode_for((Action("contact", ("A", "B")), Action("contact", ("B", "A")))),
            episode_for((Action("contact", ("C", "C")), Action("set", ("C",), 1))),
        ]
        for episode in fixtures:
            replay = participant_replay(episode)
            sensors = (copy.deepcopy(replay[0][0]["observation"]),
                       *(copy.deepcopy(feedback) for _, feedback in replay))
            rebuilt = replace(episode, sensors=sensors)
            contacts, interventions = sensor_only_samples(rebuilt)
            counts = coverage_report([episode])
            self.assertEqual(len(contacts), counts["complete_contact_pairs"])
            self.assertEqual(len(interventions), counts["complete_set_pairs"])

    def test_invalid_inputs_rejected(self):
        with self.assertRaises(ValueError):
            participant_replay(None)
        episode = episode_for((Action("set", ("A",), 0),))
        for bad_action in (Action("set", ("A",), True), Action("contact", ("A",)),
                           Action("observe", ("A",)), Action("set", ("Z",), 1),
                           Action("unknown"), Action("set", ["A"], 1)):
            with self.subTest(bad_action=bad_action), self.assertRaises(ValueError):
                participant_replay(replace(episode, actions=(bad_action,)))
        different = World(("X", "Y", "Z"), (0, 0, 0), 0)
        with self.assertRaises(ValueError):
            participant_replay(replace(episode, states=(episode.states[0], different)))


if __name__ == "__main__":
    unittest.main()
