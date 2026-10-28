"""Matched public-world fixture invariants; no scientific challenge is run."""
from dataclasses import FrozenInstanceError
import unittest

from experiments.predictive_nucleus.paired_world import PairedBaseWorld, draw_paired_base
from experiments.predictive_nucleus.stress_world import FAMILIES


class MatchedWorldTests(unittest.TestCase):
    def test_physics_does_not_change_the_common_initial_world(self):
        base = draw_paired_base(123456, 7)
        self.assertEqual(base, draw_paired_base(123456, 7))
        self.assertNotEqual(base, draw_paired_base(123456, 8))
        worlds = [base.instantiate(physics) for physics in FAMILIES]
        for world in worlds:
            self.assertEqual(world.ids, base.ids)
            self.assertEqual(world.bits, base.bits)
            self.assertEqual(world.hidden_orientation, base.hidden_orientation)
            self.assertEqual(world.contact_count, 0)
        self.assertEqual({world.physics for world in worlds}, set(FAMILIES))
        with self.assertRaises(FrozenInstanceError):
            base.bits = (0, 0, 0)
        with self.assertRaises(ValueError):
            base.instantiate("not-a-family")

    def test_invalid_base_lineage_rejected(self):
        for seed, index in ((True, 0), (-1, 0), (1, -1), (1, False)):
            with self.subTest(seed=seed, index=index), self.assertRaises(ValueError):
                draw_paired_base(seed, index)
        with self.assertRaises(ValueError):
            PairedBaseWorld("0" * 64, ["A", "B", "C"], (0, 0, 0), 0)
        with self.assertRaises(ValueError):
            PairedBaseWorld("0" * 64, ("A", "B", "C"), [0, 0, 0], 0)
        with self.assertRaises(ValueError):
            PairedBaseWorld("0" * 64, ("A", "B", "C"), (0, 0, 0), True)

    def test_public_seed_inventory_does_not_hide_orientation(self):
        base = draw_paired_base(81, 2)
        matches = [draw_paired_base(seed, 2) for seed in (79, 80, 81, 82)
                   if draw_paired_base(seed, 2).ids == base.ids]
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].hidden_orientation, base.hidden_orientation)

    def test_lineage_identity_binds_the_full_public_fixture(self):
        base = draw_paired_base(123456, 7)
        changed_bits = (1 - base.bits[0], *base.bits[1:])
        with self.assertRaisesRegex(ValueError, "identity does not match"):
            PairedBaseWorld(base.lineage_id, base.ids, changed_bits, base.hidden_orientation)
        with self.assertRaisesRegex(ValueError, "identity does not match"):
            PairedBaseWorld(base.lineage_id, base.ids, base.bits, 1 - base.hidden_orientation)

        class AlwaysEqual(str):
            def __ne__(self, other):
                return False

        with self.assertRaises(ValueError):
            PairedBaseWorld(AlwaysEqual("0" * 64), ("A", "B", "C"), (0, 0, 0), 0)
        with self.assertRaises(ValueError):
            base.instantiate(AlwaysEqual("reference"))


if __name__ == "__main__":
    unittest.main()
