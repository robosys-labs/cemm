"""Independent tiny counterexamples for the opened-record reuse audit."""
from fractions import Fraction
import unittest

from experiments.predictive_nucleus import temporal_reuse_audit_v1 as audit


class TemporalReuseAudit(unittest.TestCase):
    def test_spectator_change_and_historical_verification_cannot_bypass_exclusion(self):
        descriptors = {'exact': {'before': (1, 1, 0)}, 'spectator': {'before': (1, 1, 1)},
                       'verify_original': {'before': (1, 1, 1)}, 'different': {'before': (1, 0, 0)},
                       'replay': {'kind': 'same_source_receipt'}}
        self.assertEqual(audit.permitted(tuple(descriptors), descriptors, (1, 1, 0)), ('different', 'replay'))

    def test_filter_uses_only_public_descriptors_and_rejects_missing_inputs(self):
        descriptors = {'alpha': {'before': (0, 1, 0)}, 'beta': {'before': (0, 0, 1)}}
        self.assertEqual(audit.permitted(('alpha', 'beta'), descriptors, (0, 0, 0)), ('alpha',))
        renamed = {'z': descriptors['alpha'], 'x': descriptors['beta']}
        self.assertEqual(audit.permitted(('z', 'x'), renamed, (0, 0, 0)), ('z',))
        with self.assertRaisesRegex(ValueError, 'missing public'):
            audit.permitted(('x',), {'x': {}}, (0, 0, 0))

    def test_unequal_report_groups_retain_population_weight(self):
        small, large = audit.case_weight(4, 1, 1), audit.case_weight(8, 1, 1)
        self.assertEqual(small + large, 1)
        self.assertEqual(small * 1 + large * Fraction(1, 2), Fraction(2, 3))
        self.assertNotEqual(small * 1 + large * Fraction(1, 2), Fraction(3, 4))

    def test_indistinguishable_targets_remain_ambiguous(self):
        result = audit.analyze({'allowed': (2, 2), 'replay': (6, 6)}, (4, 6))
        self.assertIsNone(result['minimum_probes'])
        self.assertEqual(result['full_accuracy'], Fraction(1, 2))
        self.assertEqual(result['unresolved_witnesses'], ((0, 1),))
        self.assertFalse(any(policy['ask'] for policy in result['one_step_policies']))

    def test_two_distinct_probes_can_supply_joint_information(self):
        result = audit.analyze({'a': (0, 0, 1, 1), 'a_again': (0, 0, 1, 1),
                                'b': (0, 1, 0, 1)}, (0, 1, 1, 0))
        self.assertEqual(result['one_accuracy'], Fraction(1, 2))
        self.assertEqual(result['two_nonadaptive_accuracy'], 1)
        self.assertEqual(result['minimum_probes'], ('a', 'b'))
        self.assertFalse(result['one_step_policies'][0]['ask'])

    def test_unavailable_and_prohibitive_questions_preserve_prior(self):
        result = audit.analyze({'answer': (1, 0)}, (4, 6))
        cheap, costly, unavailable = result['one_step_policies']
        self.assertEqual((cheap['ask'], cheap['net']), (True, Fraction(19, 20)))
        for policy in (costly, unavailable):
            self.assertEqual((policy['ask'], policy['accuracy'], policy['selected']), (False, Fraction(1, 2), None))
        empty = audit.analyze({}, (4, 6))
        self.assertEqual(empty['full_accuracy'], Fraction(1, 2))
        self.assertFalse(any(p['ask'] for p in empty['one_step_policies']))


if __name__ == '__main__':
    unittest.main()
