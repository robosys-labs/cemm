"""Public schedule mechanics only; not model or challenge evaluation."""
from collections import Counter
from copy import deepcopy
from dataclasses import replace
import importlib.util
import unittest

from experiments.predictive_nucleus.flat_data import sensor_episode
from experiments.predictive_nucleus.geometry_diagnostic import coverage_report
from experiments.predictive_nucleus.schedule_fixture import make_evaluator_episode, sensor_view
from experiments.predictive_nucleus.world import Action


class PublicScheduleTests(unittest.TestCase):
    def test_factorial_has_complete_observed_contact_and_set_contexts(self):
        episodes = [make_evaluator_episode(i) for i in range(32)]
        report = coverage_report(episodes)
        self.assertEqual(report["episodes"], 32)
        self.assertEqual(report["contact_actions"], 64)
        self.assertEqual(report["complete_contact_pairs"], 64)
        self.assertEqual(report["set_actions"], 64)
        self.assertEqual(report["complete_set_pairs"], 64)
        self.assertEqual(report["empty_feedback"], 0)
        self.assertEqual(len({ep.lineage_id for ep in episodes}), 32)
        self.assertEqual(len({ep.states[0].ids for ep in episodes}), 1)
        self.assertNotEqual(episodes[0].states[0].ids, make_evaluator_episode(0, block=1).states[0].ids)
        contact_contexts = [Counter(), Counter()]
        set_contexts = [Counter(), Counter()]
        for ep in episodes:
            view = sensor_view(ep)
            for i in range(4):
                turn = view.learner_turn(i)
                values = {x["id"]: x["bit"] for x in turn["observation"]["measurements"]}
                action = turn["action"]
                if i < 2:
                    contact_contexts[i][tuple(values[x] for x in action["participants"])] += 1
                else:
                    set_contexts[i - 2][(values[action["participants"][0]], action["value"])] += 1
        for counts in contact_contexts + set_contexts:
            self.assertEqual(counts, Counter({(0, 0): 8, (0, 1): 8, (1, 0): 8, (1, 1): 8}))

    def test_two_views_share_exact_recorded_history_without_mutable_aliases(self):
        ep = make_evaluator_episode(13, block=2)
        first, second = sensor_view(ep), sensor_view(ep)
        self.assertEqual(first, second)
        self.assertEqual(len(first.actions), 4)
        self.assertFalse(hasattr(first, "states"))
        self.assertFalse(hasattr(first, "gold_after"))
        for i in range(4):
            turn, other_turn = first.learner_turn(i), second.learner_turn(i)
            feedback = first.reveal_after_prediction(i)
            self.assertEqual(turn, other_turn)
            self.assertEqual(feedback, second.reveal_after_prediction(i))
            self.assertEqual(set(turn), {"observation", "action"})
            self.assertEqual(set(turn["observation"]), {"t", "measurements"})
            self.assertEqual(turn["observation"]["t"], i)
            self.assertEqual(feedback["t"], i + 1)
            self.assertEqual({m["id"] for m in feedback["measurements"]}, set(turn["action"]["participants"]))
            if i < 3:
                self.assertEqual(feedback, first.learner_turn(i + 1)["observation"])
            turn["action"]["participants"].clear()
            turn["observation"]["measurements"].clear()
            feedback["measurements"].clear()
            self.assertEqual(second.learner_turn(i), other_turn)
            self.assertEqual(sensor_view(ep), second)
        self.assertEqual(sensor_episode(first), sensor_episode(second))

    def test_schedule_and_future_input_independence(self):
        ep = make_evaluator_episode(4)
        self.assertEqual(ep, make_evaluator_episode(4))
        view = sensor_view(ep)
        actions = [view.learner_turn(i)["action"] for i in range(4)]
        self.assertEqual([a["kind"] for a in actions], ["contact", "contact", "set", "set"])
        self.assertEqual(actions[1]["participants"], actions[0]["participants"][::-1])
        self.assertEqual(actions[2]["participants"], actions[0]["participants"][:1])
        self.assertEqual(actions[3]["participants"], actions[2]["participants"])
        for t in range(1, 5):
            altered_sensors = deepcopy(ep.sensors)
            altered_sensors[t]["measurements"][0]["bit"] ^= 1
            altered = sensor_view(replace(ep, sensors=altered_sensors))
            original_rows, altered_rows = sensor_episode(view), sensor_episode(altered)
            for i in range(t):
                self.assertEqual(view.learner_turn(i), altered.learner_turn(i))
                self.assertEqual(original_rows[i][0], altered_rows[i][0])
                if i + 1 < t:
                    self.assertEqual(original_rows[i][1], altered_rows[i][1])
            self.assertNotEqual(view.reveal_after_prediction(t - 1), altered.reveal_after_prediction(t - 1))
            self.assertNotEqual(original_rows[t - 1][1], altered_rows[t - 1][1])

    def test_sensor_order_does_not_depend_on_factorial_case(self):
        for block in range(2):
            patterns = []
            for case in range(32):
                ep = make_evaluator_episode(case, block=block)
                ids = ep.states[0].ids
                patterns.append(tuple(tuple(ids.index(item["id"]) for item in obs["measurements"])
                                      for obs in ep.sensors))
            self.assertTrue(all(pattern == patterns[0] for pattern in patterns))
            for i in range(16):
                first, second = make_evaluator_episode(2 * i, block=block), make_evaluator_episode(2 * i + 1, block=block)
                self.assertEqual(first.sensors[0], second.sensors[0])
                self.assertEqual(first.actions, second.actions)

    def test_fixture_validation_and_bounds(self):
        for case, block in ((-1, 0), (32, 0), (False, 0), (0, -1), (0, True)):
            with self.subTest(case=case, block=block), self.assertRaises(ValueError):
                make_evaluator_episode(case, block=block)
        ep = make_evaluator_episode(0)
        for i in (-1, 4, True):
            with self.assertRaises(IndexError):
                sensor_view(ep).learner_turn(i)
        with self.assertRaises(ValueError):
            sensor_view(replace(ep, split="in_family_challenge"))
        sensors = deepcopy(ep.sensors)
        sensors[2]["measurements"].pop()
        with self.assertRaises(ValueError):
            sensor_view(replace(ep, sensors=sensors))
        sensors = deepcopy(ep.sensors)
        sensors[0]["t"] = False
        with self.assertRaises(ValueError):
            sensor_view(replace(ep, sensors=sensors))
        invalid = Action("contact", list(ep.actions[0].participants))
        with self.assertRaises(ValueError):
            sensor_view(replace(ep, actions=(invalid, *ep.actions[1:])))
        with self.assertRaises(ValueError):
            sensor_view(replace(ep, actions=(None, *ep.actions[1:])))

    @unittest.skipUnless(importlib.util.find_spec("torch"), "PyTorch is not installed")
    def test_both_existing_extractors_receive_same_realized_histories(self):
        from experiments.predictive_nucleus.latent_model import sensor_only_samples
        from experiments.predictive_nucleus.flat_reference import batch_episodes
        episodes = [make_evaluator_episode(i, block=block) for block in range(2) for i in range(32)]
        structured_views = [sensor_view(ep) for ep in episodes]
        flat_views = [sensor_view(ep) for ep in episodes]
        for structured, flat in zip(structured_views, flat_views):
            self.assertEqual([structured.learner_turn(i) for i in range(4)],
                             [flat.learner_turn(i) for i in range(4)])
            self.assertEqual([structured.reveal_after_prediction(i) for i in range(4)],
                             [flat.reveal_after_prediction(i) for i in range(4)])
            contacts, sets = sensor_only_samples(structured)
            self.assertEqual((len(contacts), len(sets)), (2, 2))
            expected_contacts, expected_sets = [], []
            for i in range(4):
                turn = structured.learner_turn(i)
                pre = {m["id"]: m["bit"] for m in turn["observation"]["measurements"]}
                post = {m["id"]: m["bit"] for m in structured.reveal_after_prediction(i)["measurements"]}
                action = turn["action"]
                if i < 2:
                    a, b = action["participants"]
                    expected_contacts.append((pre[a], pre[b], post[a], post[b]))
                else:
                    a = action["participants"][0]
                    expected_sets.append((pre[a], action["value"], post[a]))
            self.assertEqual(contacts, expected_contacts)
            self.assertEqual(sets, expected_sets)
            self.assertEqual(len(sensor_episode(flat)), 4)
        batch = batch_episodes(flat_views)
        self.assertEqual(tuple(batch[0].shape[:2]), (4, 64))
        self.assertEqual(int(batch[2].sum()), 256)
        for b, view in enumerate(flat_views):
            ids = sorted(m["id"] for m in view.learner_turn(0)["observation"]["measurements"])
            padded = ids + [None] * (6 - len(ids))
            for i in range(4):
                turn, feedback = view.learner_turn(i), view.reveal_after_prediction(i)
                pre = {m["id"]: m["bit"] for m in turn["observation"]["measurements"]}
                post = {m["id"]: m["bit"] for m in feedback["measurements"]}
                action, members = turn["action"], turn["action"]["participants"]
                expected_x = ([float(pre.get(name, 0)) if name is not None else 0.0 for name in padded] +
                              [float(name is not None and name in pre) for name in padded] +
                              [float(name is not None) for name in padded] +
                              [float(name is not None and bool(members) and name == members[0]) for name in padded] +
                              [float(name is not None and len(members) == 2 and name == members[1]) for name in padded] +
                              [float(action["kind"] == kind) for kind in ("contact", "set", "observe")] +
                              [float(action["kind"] == "set" and action.get("value") == v) for v in (0, 1)] + [0.0])
                expected_y = [post.get(name, -1) if name is not None else -1 for name in padded]
                self.assertEqual(batch[0][i, b].tolist(), expected_x)
                self.assertEqual(batch[1][i, b].tolist(), expected_y)
                self.assertTrue(bool(batch[2][i, b]))


if __name__ == "__main__":
    unittest.main()
