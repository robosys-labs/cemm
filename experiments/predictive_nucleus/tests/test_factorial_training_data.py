import json
import unittest
from itertools import permutations

from experiments.predictive_nucleus.development_run import _training_history
from experiments.predictive_nucleus.causal_replay import FullSensorHistory
from experiments.predictive_nucleus.factorial_training_data import prepare_training, rename_full_history
from experiments.predictive_nucleus.full_sensor_evaluation import full_sensor_evaluation_view
from experiments.predictive_nucleus.full_sensor_fixture import make_full_training_history
from experiments.predictive_nucleus.relabel_diagnostic import rename_history
from experiments.predictive_nucleus.schedule_fixture import make_evaluator_episode
from experiments.predictive_nucleus.two_pair_fixture import make_evaluator_episode as make_evaluation_episode


class FactorialTrainingDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repeated = prepare_training("repeated")
        cls.augmented = prepare_training("augmented")

    def test_inventory_and_matching_loss_inputs(self):
        for examples in (self.repeated, self.augmented):
            self.assertEqual(len(examples), 384)
            self.assertEqual(sum(len(e.full.flat_rows) for e in examples), 1920)
            self.assertEqual(sum(len(e.full.contacts) for e in examples), 768)
            self.assertEqual(sum(len(e.full.interventions) for e in examples), 768)
            self.assertEqual(sum(sum(bit >= 0 for bit in y) for e in examples for _, y in e.full.flat_rows), 5760)
            self.assertEqual(sum(sum(bit >= 0 for bit in y) for e in examples for _, y in e.masked.flat_rows), 3072)
            for e in examples:
                self.assertEqual(e.full.history, e.masked.history)
                self.assertEqual(e.full.contacts, e.masked.contacts)
                self.assertEqual(e.full.interventions, e.masked.interventions)
                self.assertEqual([x for x, _ in e.full.flat_rows], [x for x, _ in e.masked.flat_rows])
                for encoded in e.full.history:
                    payload = json.loads(encoded)
                    self.assertFalse({"case", "gold", "states", "hidden_source_slot"} & set(payload))

    def test_all_six_permutations_preserve_sensor_values_and_mask_each_id(self):
        for block in (0, 1):
            for case in range(32):
                i = 6 * (block * 32 + case)
                partial = _training_history(make_evaluator_episode(case, block=block))
                full = make_full_training_history(case, block=block)
                original_ids = tuple(sorted(name for name, _ in full._observations[0]))
                self.assertEqual([tuple(dict(e.mapping)[name] for name in original_ids)
                                  for e in self.augmented[i:i + 6]], list(permutations(original_ids)))
                for e in self.augmented[i:i + 6]:
                    mapping = dict(e.mapping)
                    renamed_ids = tuple(sorted(mapping.values()))
                    self.assertEqual(e.history._action_records,
                                     tuple((kind, tuple(mapping[n] for n in names), value)
                                           for kind, names, value in full._action_records))
                    for t, (features, targets) in enumerate(e.masked.flat_rows):
                        expected_sensor = tuple((mapping[n], b) for n, b in full._observations[t + 1])
                        retained = {mapping[n]: b for n, b in partial._observations[t + 1]}
                        self.assertEqual(e.history._observations[t + 1], expected_sensor)
                        self.assertEqual(tuple(targets[:3]), tuple(retained.get(n, -1) for n in renamed_ids))
                        self.assertEqual(tuple(targets[3:]), (-1, -1, -1))
                        self.assertEqual(features, e.full.flat_rows[t][0])

    def test_repeated_arm_and_inverse_mapping(self):
        for repeated, augmented in zip(self.repeated, self.augmented, strict=True):
            self.assertEqual(repeated.full.contacts, augmented.full.contacts)
            self.assertEqual(repeated.full.interventions, augmented.full.interventions)
        for start in range(0, 384, 6):
            copies = self.repeated[start:start + 6]
            self.assertTrue(all(e == copies[0] for e in copies))
            original = copies[0].history
            for e in self.augmented[start:start + 6]:
                inverse = {v: k for k, v in e.mapping}
                self.assertEqual(tuple(tuple((inverse[n], bit) for n, bit in o)
                                       for o in e.history._observations), original._observations)
                self.assertEqual(tuple((kind, tuple(inverse[n] for n in members), value)
                                       for kind, members, value in e.history._action_records), original._action_records)

    def test_invalid_arm_rejected(self):
        with self.assertRaises(ValueError):
            prepare_training("not-an-arm")

    def test_full_evaluation_history_renamer_is_explicit_and_reversible(self):
        history = full_sensor_evaluation_view(make_evaluation_episode(0))
        ids = tuple(sorted(name for name, _ in history._observations[0]))
        for names in permutations(ids):
            mapping = dict(zip(ids, names, strict=True))
            renamed = rename_full_history(history, mapping)
            self.assertIs(type(renamed), FullSensorHistory)
            self.assertEqual(rename_full_history(renamed, {v: k for k, v in mapping.items()}), history)
            self.assertEqual(renamed._observations,
                             tuple(tuple((mapping[n], bit) for n, bit in obs) for obs in history._observations))
            self.assertEqual(renamed._action_records,
                             tuple((kind, tuple(mapping[n] for n in members), value)
                                   for kind, members, value in history._action_records))
        with self.assertRaises(ValueError):
            rename_history(history, dict(zip(ids, ids, strict=True)))
        for invalid in ({ids[0]: ids[0]}, dict.fromkeys(ids, ids[0]), {ids[0]: []}):
            with self.assertRaises(ValueError):
                rename_full_history(history, invalid)


if __name__ == "__main__":
    unittest.main()
