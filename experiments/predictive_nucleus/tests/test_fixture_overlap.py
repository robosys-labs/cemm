"""Exact public fixture overlap; no sample-independence inference."""
from dataclasses import replace
import importlib.util
import unittest

from experiments.predictive_nucleus.fixture_overlap import audit_blocks, normalized_trace, observed_local_samples
from experiments.predictive_nucleus.schedule_fixture import make_evaluator_episode, sensor_view


class FixtureOverlapTests(unittest.TestCase):
    def test_complete_enumeration_has_28_observable_histories_per_block(self):
        report = audit_blocks()
        self.assertEqual(report["status"], "PUBLIC_FINITE_FIXTURE_OVERLAP_ONLY")
        self.assertEqual(report["gate_g1"], "NOT_RUN")
        self.assertFalse(report["calibration_or_challenge"])
        self.assertEqual(report["cases_per_block"], 32)
        self.assertEqual(report["unique_normalized_traces"], {str(i): 28 for i in range(4)})
        pairs = {tuple(row["blocks"]): row["unique_shared_traces"] for row in report["pairwise_overlap"]}
        self.assertEqual(pairs, {(0, 1): 0, (0, 2): 28, (0, 3): 0,
                                 (1, 2): 0, (1, 3): 28, (2, 3): 0})
        for summary in report["local_sample_summary"].values():
            self.assertEqual(summary, {"contact_events": 64, "unique_contact_samples": 7,
                                       "set_events": 64, "unique_set_samples": 4})
        for overlap in report["pairwise_local_overlap"]:
            self.assertEqual(overlap["unique_shared_contact_samples"], 7)
            self.assertEqual(overlap["shared_contact_events_by_multiplicity"], 64)
            self.assertEqual(overlap["unique_shared_set_samples"], 4)
            self.assertEqual(overlap["shared_set_events_by_multiplicity"], 64)

    def test_separate_public_block_inventories_replay_same_normalized_histories(self):
        traces = []
        inventories = []
        for block in range(4):
            views = [sensor_view(make_evaluator_episode(case, block=block)) for case in range(32)]
            traces.append({normalized_trace(view) for view in views})
            inventories.append({m["id"] for m in views[0].learner_turn(0)["observation"]["measurements"]})
        for i, first in enumerate(inventories):
            for second in inventories[i + 1:]:
                self.assertTrue(first.isdisjoint(second))
        train, calibration = traces[0] | traces[1], traces[2] | traces[3]
        self.assertEqual(len(train), 56)
        self.assertEqual(train, calibration)

    def test_measurement_order_and_opaque_names_do_not_change_the_trace(self):
        first = sensor_view(make_evaluator_episode(7, block=0))
        other_ids = sensor_view(make_evaluator_episode(7, block=2))
        reordered = replace(first, _observations=tuple(tuple(reversed(row)) for row in first._observations))
        self.assertEqual(normalized_trace(first), normalized_trace(reordered))
        self.assertEqual(normalized_trace(first), normalized_trace(other_ids))

    def test_structured_local_samples_match_casewise_across_all_four_blocks(self):
        for case in range(32):
            views = [sensor_view(make_evaluator_episode(case, block=block)) for block in range(4)]
            expected = observed_local_samples(views[0])
            self.assertEqual(tuple(len(group) for group in expected), (2, 2))
            for view in views:
                # Independently extract directly from delivered records using
                # the existing structured model's visibility conditions.
                contacts, sets = [], []
                for i in range(4):
                    turn = view.learner_turn(i)
                    before = {m["id"]: m["bit"] for m in turn["observation"]["measurements"]}
                    after = {m["id"]: m["bit"] for m in view.reveal_after_prediction(i)["measurements"]}
                    action, names = turn["action"], turn["action"]["participants"]
                    if (action["kind"] == "contact" and len(names) == 2 and
                            len(set(names)) == 2 and all(name in before and name in after for name in names)):
                        contacts.append((before[names[0]], before[names[1]], after[names[0]], after[names[1]]))
                    elif action["kind"] == "set" and names[0] in before and names[0] in after:
                        sets.append((before[names[0]], action["value"], after[names[0]]))
                self.assertEqual(observed_local_samples(view), (tuple(contacts), tuple(sets)))
                self.assertEqual(observed_local_samples(view), expected)

    def test_missing_participant_never_becomes_a_local_contact_sample(self):
        view = sensor_view(make_evaluator_episode(4))
        observations = list(view._observations)
        observations[1] = observations[1][:1]
        missing = replace(view, _observations=tuple(observations))
        contacts, sets = observed_local_samples(missing)
        self.assertEqual(contacts, ())
        self.assertEqual(len(sets), 2)

    @unittest.skipUnless(importlib.util.find_spec("torch"), "PyTorch is not installed")
    def test_local_samples_match_existing_structured_extractor(self):
        from experiments.predictive_nucleus.latent_model import sensor_only_samples
        for block in range(4):
            for case in range(32):
                view = sensor_view(make_evaluator_episode(case, block=block))
                contacts, sets = sensor_only_samples(view)
                self.assertEqual(observed_local_samples(view), (tuple(contacts), tuple(sets)))

    def test_invalid_blocks_and_views_are_rejected(self):
        for blocks in ((), (0, 0), (True,), (-1,), [0, 1]):
            with self.subTest(blocks=blocks), self.assertRaises(ValueError):
                audit_blocks(blocks)
        with self.assertRaises(ValueError):
            normalized_trace(None)


if __name__ == "__main__":
    unittest.main()
