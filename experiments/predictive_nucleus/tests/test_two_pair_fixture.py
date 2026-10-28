"""Public two-pair fixture invariants; no model performance is assessed."""
from collections import Counter
from copy import deepcopy
from dataclasses import replace
import importlib.util
import unittest

from experiments.predictive_nucleus.flat_data import sensor_episode
from experiments.predictive_nucleus.two_pair_fixture import fixture_report, make_evaluator_episode, sensor_view
from experiments.predictive_nucleus.world import Action


class TwoPairFixtureTests(unittest.TestCase):
    def test_factorial_coverage_and_declared_observe_cost(self):
        report = fixture_report()
        self.assertEqual(report["status"], "PUBLIC_TWO_PAIR_FEASIBILITY_ONLY")
        self.assertEqual(report["gate_g1"], "NOT_RUN")
        self.assertFalse(report["independent_world_claim"])
        self.assertEqual((report["cases"], report["shared_identity_blocks"], report["steps_per_case"]), (64, 1, 5))
        self.assertEqual((report["contact_actions"], report["set_actions"], report["observe_actions"]), (128, 128, 64))
        self.assertEqual((report["complete_contacts"], report["complete_sets"], report["observed_feedback_bits"]), (128, 128, 512))
        self.assertEqual((report["orientation_twin_pairs"], report["identical_sensor_history_twin_pairs"]), (32, 2))
        for i in (0, 1, 3, 4):
            self.assertEqual(report["contexts_by_action_position"][i], {"00": 16, "01": 16, "10": 16, "11": 16})
        self.assertEqual(report["contexts_by_action_position"][2], {})

    def test_shared_ids_and_orientation_twins_do_not_encode_case(self):
        for block in (0, 1):
            episodes = [make_evaluator_episode(i, block=block) for i in range(64)]
            self.assertEqual(len({ep.states[0].ids for ep in episodes}), 1)
            patterns = [tuple(tuple(ep.states[0].ids.index(m["id"]) for m in obs["measurements"])
                              for obs in ep.sensors) for ep in episodes]
            self.assertTrue(all(p == patterns[0] for p in patterns))
            for i in range(0, 64, 2):
                self.assertEqual(episodes[i].sensors[0], episodes[i + 1].sensors[0])
                self.assertEqual(episodes[i].actions, episodes[i + 1].actions)
        self.assertNotEqual(make_evaluator_episode(0).states[0].ids,
                            make_evaluator_episode(0, block=1).states[0].ids)
        twins = [(sensor_view(make_evaluator_episode(i)), sensor_view(make_evaluator_episode(i + 1)))
                 for i in range(0, 64, 2)]
        self.assertEqual([i for i, (left, right) in enumerate(twins) if left == right], [0, 1])

    def test_two_pairs_chronology_and_sensor_only_views(self):
        for case in range(64):
            episode = make_evaluator_episode(case)
            original = deepcopy(episode)
            # The observe-only action changes sensor visibility, not state.
            self.assertEqual(episode.states[2], episode.states[3])
            first, second = sensor_view(episode), sensor_view(episode)
            self.assertEqual(first, second)
            self.assertFalse(hasattr(first, "states"))
            self.assertFalse(hasattr(first, "gold_after"))
            self.assertEqual(len(first.actions), 5)
            turns = [first.learner_turn(i) for i in range(5)]
            self.assertEqual([turn["action"]["kind"] for turn in turns],
                             ["contact", "set", "observe", "contact", "set"])
            ab, bc = turns[0]["action"]["participants"], turns[3]["action"]["participants"]
            self.assertEqual(ab[1], bc[0])
            self.assertEqual(len(set(ab + bc)), 3)
            self.assertEqual(turns[1]["action"]["participants"], [ab[1]])
            self.assertEqual(turns[4]["action"]["participants"], [bc[1]])
            for i, turn in enumerate(turns):
                feedback = first.reveal_after_prediction(i)
                self.assertEqual(set(turn), {"observation", "action"})
                self.assertEqual(feedback["t"], i + 1)
                expected = bc if i == 2 else turn["action"]["participants"]
                self.assertEqual({m["id"] for m in feedback["measurements"]}, set(expected))
                if i < 4:
                    self.assertEqual(feedback, first.learner_turn(i + 1)["observation"])
                if i != 2:
                    pre = {m["id"] for m in turn["observation"]["measurements"]}
                    post = {m["id"] for m in feedback["measurements"]}
                    self.assertTrue(set(expected) <= pre and set(expected) <= post)
            rows = sensor_episode(first)
            self.assertEqual(len(rows), 5)
            self.assertEqual([sum(x >= 0 for x in y) for _, y in rows], [2, 1, 2, 2, 1])
            ids = sorted(m["id"] for m in first.learner_turn(0)["observation"]["measurements"])
            for i, (_, target) in enumerate(rows):
                measured = {m["id"]: m["bit"] for m in first.reveal_after_prediction(i)["measurements"]}
                self.assertEqual(target, [measured.get(name, -1) for name in ids] + [-1, -1, -1])
            first.learner_turn(0)["action"]["participants"].clear()
            first.reveal_after_prediction(0)["measurements"].clear()
            self.assertEqual(sensor_view(episode), second)
            self.assertEqual(episode, original)

    def test_later_feedback_and_actions_do_not_change_prior_features(self):
        original = sensor_view(make_evaluator_episode(9))
        rows = sensor_episode(original)
        for time in range(1, 6):
            observations = list(original._observations)
            records = list(observations[time])
            records[0] = (records[0][0], 1 - records[0][1])
            observations[time] = tuple(records)
            alternate = sensor_episode(replace(original, _observations=tuple(observations)))
            for earlier in range(time):
                self.assertEqual(rows[earlier][0], alternate[earlier][0])
                if earlier + 1 < time:
                    self.assertEqual(rows[earlier][1], alternate[earlier][1])
            self.assertNotEqual(rows[time - 1][1], alternate[time - 1][1])
        for time in (1, 4):
            actions = list(original._action_records)
            kind, members, value = actions[time]
            actions[time] = (kind, members, 1 - value)
            alternate = sensor_episode(replace(original, _action_records=tuple(actions)))
            for earlier in range(time):
                self.assertEqual(rows[earlier], alternate[earlier])

    def test_reject_invalid_case_metadata_sensors_and_actions(self):
        for case, block in ((-1, 0), (64, 0), (True, 0), (0, -1), (0, True)):
            with self.subTest(case=case, block=block), self.assertRaises(ValueError):
                make_evaluator_episode(case, block=block)
        episode = make_evaluator_episode(0)
        with self.assertRaises(ValueError):
            sensor_view(replace(episode, split="in_family_challenge"))
        observations = deepcopy(episode.sensors)
        observations[3]["measurements"].pop()
        with self.assertRaises(ValueError):
            sensor_view(replace(episode, sensors=observations))
        observations = deepcopy(episode.sensors)
        observations[1]["t"] = True
        with self.assertRaises(ValueError):
            sensor_view(replace(episode, sensors=observations))
        invalid = Action("set", list(episode.actions[1].participants), 0)
        with self.assertRaises(ValueError):
            sensor_view(replace(episode, actions=(episode.actions[0], invalid, *episode.actions[2:])))

    @unittest.skipUnless(importlib.util.find_spec("torch"), "PyTorch is not installed")
    def test_actual_extractor_uses_complete_contact_and_set_samples(self):
        from experiments.predictive_nucleus.latent_model import sensor_only_samples
        contacts, sets = Counter(), Counter()
        for case in range(64):
            view = sensor_view(make_evaluator_episode(case))
            c, s = sensor_only_samples(view)
            self.assertEqual((len(c), len(s)), (2, 2))
            expected_contacts, expected_sets = [], []
            for t in (0, 1, 3, 4):
                turn = view.learner_turn(t)
                pre = {m["id"]: m["bit"] for m in turn["observation"]["measurements"]}
                post = {m["id"]: m["bit"] for m in view.reveal_after_prediction(t)["measurements"]}
                action = turn["action"]
                if action["kind"] == "contact":
                    a, b = action["participants"]
                    expected_contacts.append((pre[a], pre[b], post[a], post[b]))
                else:
                    a = action["participants"][0]
                    expected_sets.append((pre[a], action["value"], post[a]))
            self.assertEqual(c, expected_contacts)
            self.assertEqual(s, expected_sets)
            for position, sample in enumerate(c):
                contacts[position, sample[:2]] += 1
            for position, sample in enumerate(s):
                sets[position, sample[:2]] += 1
        for position in range(2):
            for bits in ((0, 0), (0, 1), (1, 0), (1, 1)):
                self.assertEqual(contacts[position, bits], 16)
                self.assertEqual(sets[position, bits], 16)


if __name__ == "__main__":
    unittest.main()
