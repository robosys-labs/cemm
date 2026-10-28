import json
import math
import unittest

from experiments.predictive_nucleus.forecast_normalization import normalize_joint


class ForecastNormalizationTests(unittest.TestCase):
    def test_synthetic_overshoot_is_globally_rescaled_and_audited(self):
        # The recorded case-6 anomaly included this single value but not the
        # complete original distribution. These other values are synthetic.
        raw = {(1, 1, 1): 1.00000003851976, (0, 0, 0): 1e-10, (0, 0, 1): 0.0}
        before = dict(raw)
        result, audit = normalize_joint(raw, n_ids=3)
        self.assertEqual(raw, before)
        self.assertEqual(set(result), set(raw))
        self.assertEqual(result[(0, 0, 1)], 0.0)
        self.assertGreater(result[(0, 0, 0)], 0.0)
        self.assertTrue(all(0 <= p <= 1 for p in result.values()))
        self.assertEqual(audit["raw_total"], math.fsum(raw.values()))
        self.assertAlmostEqual(audit["normalized_total"], 1.0, places=15)
        self.assertEqual(audit["raw_over_one_count"], 1)
        self.assertEqual(audit["raw_max_overshoot"], raw[(1, 1, 1)] - 1.0)
        self.assertGreater(audit["max_absolute_correction"], 0)
        for row in audit["per_world"]:
            state = tuple(row["world"])
            self.assertEqual(row["before"], raw[state])
            self.assertEqual(row["after"], raw[state] / audit["raw_total"])
            self.assertEqual(row["delta"], row["after"] - row["before"])
        json.dumps(audit, allow_nan=False)

    def test_exact_and_near_unit_forecasts_preserve_support_and_ties(self):
        exact, audit = normalize_joint({(0,): 0.0, (1,): 1.0}, n_ids=1)
        self.assertEqual(exact, {(0,): 0.0, (1,): 1.0})
        self.assertEqual(audit["max_absolute_correction"], 0.0)
        raw = {(0, 0): .249999875, (0, 1): .249999875, (1, 1): .5}
        normalized, audit = normalize_joint(raw, n_ids=2)
        self.assertEqual(normalized[(0, 0)], normalized[(0, 1)])
        self.assertAlmostEqual(math.fsum(normalized.values()), 1.0, places=15)
        self.assertFalse(audit["maximizer_set_changed"])
        self.assertEqual(audit["raw_maximizers"], [[1, 1]])

    def test_smallest_positive_float_is_not_imputed_to_zero(self):
        tiny = math.ulp(0.0)
        result, _ = normalize_joint({(0,): tiny, (1,): 1.00000003851976}, n_ids=1)
        self.assertGreater(result[(0,)], 0.0)
        self.assertLessEqual(result[(1,)], 1.0)

    def test_global_scaling_reports_new_exact_map_tie(self):
        # Floating division may collapse adjacent unequal values to a tie.
        raw = {(0, 0): 0.44629978540573867, (0, 1): 0.4462997854057387,
               (1, 0): 0.10740132918852269}
        result, audit = normalize_joint(raw, n_ids=2)
        self.assertEqual(result[(0, 0)], result[(0, 1)])
        self.assertEqual(audit["raw_maximizers"], [[0, 1]])
        self.assertEqual(audit["normalized_maximizers"], [[0, 0], [0, 1]])
        self.assertTrue(audit["maximizer_set_changed"])
        self.assertEqual(audit["raw_lexicographic_map"], [0, 1])
        self.assertEqual(audit["normalized_lexicographic_map"], [0, 0])
        self.assertTrue(audit["lexicographic_map_changed"])

    def test_rejects_invalid_values_and_bad_mass(self):
        bad = [
            {(0,): -1e-16, (1,): 1.0},
            {(0,): float("nan"), (1,): 1.0},
            {(0,): float("inf")},
            {(0,): True},
            {(0,): "1"},
            {(0,): 0.0},
            {(0,): 1.0 + 1.1e-6},
            {(0,): .499, (1,): .499},
            {(0,): 10 ** 1000},
        ]
        for distribution in bad:
            with self.subTest(distribution=distribution):
                with self.assertRaises(ValueError):
                    normalize_joint(distribution, n_ids=1)

    def test_rejects_wrong_world_shape_and_untrusted_types(self):
        bad = [({}, 1), ({(0,): 1.0}, 0), ({(0,): 1.0}, True),
               ({(0,): 1.0}, 2), ({(True,): 1.0}, 1),
               ({(2,): 1.0}, 1), ({"0": 1.0}, 1),
               ({(0, 0): .5, (1,): .5}, 2),
               ({(0,): 1.0}, 7)]
        for distribution, n_ids in bad:
            with self.subTest(distribution=distribution, n_ids=n_ids):
                with self.assertRaises(ValueError):
                    normalize_joint(distribution, n_ids=n_ids)

    def test_bounds_are_global_and_no_per_entry_clipping(self):
        raw = {(0,): 1.0000002, (1,): 0.0000003}
        normalized, audit = normalize_joint(raw, n_ids=1)
        self.assertEqual(normalized[(0,)], raw[(0,)] / audit["raw_total"])
        self.assertEqual(normalized[(1,)], raw[(1,)] / audit["raw_total"])
        self.assertNotEqual(normalized[(0,)], 1.0)
        self.assertGreater(normalized[(1,)], 0.0)


if __name__ == "__main__":
    unittest.main()
