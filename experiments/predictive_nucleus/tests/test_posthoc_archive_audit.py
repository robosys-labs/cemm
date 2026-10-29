"""Synthetic arithmetic adversaries; no fitting or public challenge access."""
import copy
from hashlib import sha256
import json
from math import fsum, log
from pathlib import Path
import tempfile
import unittest

from experiments.predictive_nucleus import audit_posthoc_archive as audit


def point(truth=(1, 1, 1)):
    mass = 1.00000004
    delta = 1.0 - mass
    raw = [0, 0, 0]
    normalization = {
        'raw_total': mass, 'normalized_total': 1.0,
        'mass_tolerance': 1e-6, 'normalized_tolerance': 1e-12,
        'raw_max_probability': mass, 'raw_max_overshoot': mass - 1,
        'raw_over_one_count': 1, 'raw_maximizers': [raw], 'normalized_maximizers': [raw],
        'maximizer_set_changed': False, 'raw_lexicographic_map': raw,
        'normalized_lexicographic_map': raw, 'lexicographic_map_changed': False,
        'max_absolute_correction': abs(delta), 'total_absolute_correction': abs(delta),
        'per_world': [{'world': raw, 'before': mass, 'after': 1.0, 'delta': delta},
                      {'world': [1, 1, 1], 'before': 0.0, 'after': 0.0, 'delta': 0.0}],
    }
    correct = truth == (0, 0, 0)
    return {'status': 'PREDICTED', 'reason': None, 'normalization': normalization,
            'map_world': raw, 'map_correct': correct, 'truth_probability': float(correct),
            'joint_brier': 0.0 if correct else 2.0,
            'joint_log_score': {'clipped_log_loss': 0.0 if correct else -log(1e-12),
                                'uncapped_log_loss': 0.0 if correct else None,
                                'zero_probability': not correct, 'floor_applied': not correct},
            'world_probabilities': [{'world': list(w), 'probability': float(w == (0, 0, 0))}
                                    for w in audit.WORLDS]}


def abstain():
    return {'status': 'ABSTAIN', 'reason': 'unsupported', **dict.fromkeys((
        'map_world', 'map_correct', 'truth_probability', 'joint_log_score',
        'joint_brier', 'world_probabilities', 'normalization'))}


class ArchiveAuditTests(unittest.TestCase):
    def test_valid_raw_overshoot_zero_and_correct_forecasts_are_not_mutated(self):
        for truth in ([0, 0, 0], [1, 1, 1]):
            score = point(tuple(truth))
            before = copy.deepcopy(score)
            self.assertEqual(fsum(audit.check_score(score, truth).values()), 1.0)
            self.assertEqual(score, before)

    def test_abstention_is_not_numeric_failure(self):
        score = abstain()
        self.assertIsNone(audit.check_score(score, [0, 0, 0]))
        score['truth_probability'] = 0.0
        with self.assertRaisesRegex(ValueError, 'abstention'):
            audit.check_score(score, [0, 0, 0])

    def test_rejects_invalid_or_duplicate_raw_mass(self):
        for value in (True, -1.0, float('nan'), float('inf'), 1.1):
            score = point()
            score['normalization']['per_world'][0]['before'] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                audit.check_score(score, [1, 1, 1])
        score = point()
        score['normalization']['per_world'].append(copy.deepcopy(score['normalization']['per_world'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            audit.check_score(score, [1, 1, 1])

    def test_rejects_forged_normalization_and_scores(self):
        changes = (
            lambda x: x.update(map_correct=True),
            lambda x: x.update(joint_brier=0.0),
            lambda x: x.update(truth_probability=1.0),
            lambda x: x['joint_log_score'].update(uncapped_log_loss=0.0),
            lambda x: x['normalization'].update(raw_over_one_count=0),
            lambda x: x['normalization'].update(lexicographic_map_changed=True),
            lambda x: x['normalization']['per_world'][0].update(after=0.99),
            lambda x: x['normalization']['per_world'][0].update(delta=0.0),
            lambda x: x['world_probabilities'][0].update(probability=0.5),
            lambda x: x.update(status='UNKNOWN'),
        )
        for change in changes:
            score = point()
            change(score)
            with self.subTest(change=change), self.assertRaises(ValueError):
                audit.check_score(score, [1, 1, 1])

    def test_summary_keeps_infinite_log_loss_and_explicit_coverage(self):
        rows = [point(), point((0, 0, 0)), abstain()]
        summary = {'queries': 3, 'answered': 2, 'abstained': 1, 'correct': 1, 'wrong': 1,
                   'coverage': 2/3, 'accuracy_answered': 0.5, 'correct_per_query': 1/3,
                   'wrong_per_query': 1/3, 'mean_joint_brier_answered': 1.0,
                   'joint_log_loss': {'clipped_mean': -log(1e-12)/2, 'floor_applied_count': 1,
                       'zero_probability_count': 1, 'uncapped_mean_is_infinite': True, 'uncapped_mean': None}}
        audit.check_summary(summary, rows)
        for key, value in (('uncapped_mean', 0.0), ('zero_probability_count', 0)):
            damaged = copy.deepcopy(summary)
            damaged['joint_log_loss'][key] = value
            with self.assertRaises(ValueError):
                audit.check_summary(damaged, rows)

    def test_hash_or_incomplete_inventory_never_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = {'status': 'POST_HOC_OPEN_PUBLIC_DEVELOPMENT_NOT_G1',
                      'verified_checkpoints': 40, 'verified_control_tables': 6}
            raw = json.dumps(report).encode()
            (root / 'report.json').write_bytes(raw)
            (root / 'COMPLETE').write_text('0' * 64)
            (root / 'cases.jsonl').write_text('')
            with self.assertRaisesRegex(ValueError, 'report hash'):
                audit.run(root)
            (root / 'COMPLETE').write_text(sha256(raw).hexdigest())
            with self.assertRaisesRegex(ValueError, 'inventory'):
                audit.run(root)
            (root / 'FAILED.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'failure marker'):
                audit.run(root)


if __name__ == '__main__':
    unittest.main()
