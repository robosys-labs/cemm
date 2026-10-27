"""Evaluator world mechanics: independent truth tables and split rules."""
import random
import unittest

from experiments.predictive_nucleus.stress_world import (
    StressWorld, draw_world, change, choose_visibility, sensor_reading)


class IndependentWorldTests(unittest.TestCase):
    def test_development_world_replay_and_seed_separation(self):
        a = draw_world(601, 0, "reference")
        self.assertEqual(a, draw_world(601, 0, "reference"))
        self.assertNotEqual(a, draw_world(601, 1, "reference"))
        self.assertNotEqual(a.ids, draw_world(601, 0, "bilateral_flip").ids)

    def test_all_reference_truth_table_orientations(self):
        for h in (0, 1):
            for a in (0, 1):
                for b in (0, 1):
                    w = StressWorld(("A", "B", "C"), (a, b, 0), h, "reference")
                    out = change(w, {"kind": "contact", "participants": ["A", "B"]})
                    self.assertEqual(out.bits, (a, b ^ a, 0) if h == 0 else (a ^ b, b, 0))
                    self.assertEqual(w.bits, (a, b, 0))

    def test_bilateral_flip_cannot_be_explained_by_single_source_on_11(self):
        w = StressWorld(("A", "B", "C"), (1, 1, 0), 0, "bilateral_flip")
        out = change(w, {"kind": "contact", "participants": ["A", "B"]})
        self.assertEqual(out.bits, (0, 0, 0))
        self.assertNotIn(out.bits, ((1, 0, 0), (0, 1, 0)))

    def test_fixed_role_can_become_invalid_after_first_contact(self):
        w = StressWorld(("A", "B", "C"), (1, 0, 0), 0, "switch_orientation")
        act = {"kind": "contact", "participants": ["A", "B"]}
        one = change(w, act)
        self.assertEqual(one.bits, (1, 1, 0))
        two = change(one, act)
        self.assertEqual(two.bits, (0, 1, 0))
        self.assertEqual(w.contact_count, 0)
        self.assertEqual(two.contact_count, 2)

    def test_visibility_mask_selected_before_sensor_measurements(self):
        w = StressWorld(("A", "B", "C"), (0, 1, 0), 1, "reference")
        rng = random.Random(3)
        selected = choose_visibility(w.ids, rng, .5)
        initial = w.bits
        seen = sensor_reading(w, 2, selected, rng, flip_rate=.2)
        self.assertEqual({m["id"] for m in seen["measurements"]}, set(selected))
        self.assertEqual(w.bits, initial)
        self.assertEqual(len(seen["measurements"]), len(selected))

    def test_observation_and_set_do_not_fabricate_interactions(self):
        w = StressWorld(("A", "B", "C"), (1, 0, 0), 0, "conditional_flip")
        self.assertEqual(change(w, {"kind": "observe", "participants": []}), w)
        assigned = change(w, {"kind": "set", "participants": ["B"], "value": 1})
        self.assertEqual(assigned.bits, (1, 1, 0))
        touched = change(assigned, {"kind": "contact", "participants": ["A", "B"]})
        self.assertEqual(touched.bits, (1, 0, 0))
        self.assertEqual(w.bits, (1, 0, 0))


if __name__ == "__main__":
    unittest.main()
