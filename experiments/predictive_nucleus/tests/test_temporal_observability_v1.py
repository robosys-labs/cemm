"""Small independent witnesses for the temporal task's information boundary."""
from fractions import Fraction
import unittest

from experiments.predictive_nucleus import temporal_observability_v1 as study


class TemporalObservationSupport(unittest.TestCase):
    def test_native_endpoints_use_the_actual_direction_and_preserve_third_entity(self):
        # NAND of two zero bits becomes one at the selected target only.
        self.assertEqual(study.checked_endpoint('nand', 0, 0, (0, 0, 0)), 2)
        self.assertEqual(study.checked_endpoint('nand', 1, 0, (0, 0, 0)), 4)
        self.assertEqual(study.checked_endpoint('nor', 0, 0, (1, 0, 1)), 5)
        self.assertEqual(study.checked_endpoint('nor', 0, 2, (0, 0, 1)), 5)

    def test_equal_public_report_cannot_reveal_private_new_operation(self):
        context = study.make_context('nand', 0, 0, 0)
        # At 000, reverse contact and SET(first) both produce endpoint 4.
        # They must remain in ONE eight-world information set. SET(second)
        # produces endpoint 2, coinciding with the old operation, and survives.
        self.assertEqual(len(context['worlds']), 12)
        self.assertEqual(sorted(len(group['support']) for group in context['groups']), [4, 8])
        for group in context['groups']:
            for menu in group['menus'].values():
                self.assertTrue(set(menu) <= set(group['probes']))
            self.assertTrue(all(len(column) == len(group['support'])
                                for column in group['probes'].values()))

    def test_cause_can_remain_unknown_when_target_is_decidable(self):
        # Worlds: local correction, exception, report-only, parent correction.
        local = (1, 0, 0, 1)
        sibling = (0, 0, 0, 1)
        blocks = study.partition((local, sibling), 4)
        self.assertEqual(blocks, ((0,), (1, 2), (3,)))
        self.assertTrue(study.identifies(blocks, local))
        self.assertTrue(study.identifies(blocks, sibling))
        self.assertFalse(study.identifies(blocks, ('local', 'exception', 'report', 'parent')))
        self.assertIsNone(study.minimum_probe_set({'local': local, 'sibling': sibling},
                                                  ('local', 'exception', 'report', 'parent')))

    def test_generated_event_boundary_keeps_exception_out_of_later_instances(self):
        context = study.make_context('nand', 0, 0, 0)
        group = next(group for group in context['groups'] if len(group['support']) == 8)
        self.assertEqual(group['probes']['verify_original'], (4, 4, 2, 4) * 2)
        self.assertEqual(group['probes']['local/0'], (4, 2, 2, 4) * 2)
        self.assertEqual(group['probes']['sibling/0'], (2, 2, 2, 4) * 2)
        self.assertEqual(group['probes']['protected_word'], (2,) * 8)
        self.assertNotIn('verify_original', group['menus']['lost'])

    def test_receipt_replay_is_idempotent_and_conflicting_identity_is_atomic(self):
        prior = (Fraction(1, 2), Fraction(1, 3), Fraction(1, 6))
        posterior, history = study.observe(prior, {}, 'receipt-1', (0, 1, 1), 1)
        self.assertEqual(posterior, (0, Fraction(2, 3), Fraction(1, 3)))
        self.assertEqual(study.observe(posterior, history, 'receipt-1', (0, 1, 1), 1),
                         (posterior, history))
        original_history = dict(history)
        for column, answer in (((0, 1, 1), 0), ((0, 1, 0), 1)):
            with self.subTest(column=column, answer=answer):
                with self.assertRaisesRegex(ValueError, 'conflicting evidence identity'):
                    study.observe(posterior, history, 'receipt-1', column, answer)
        self.assertEqual(history, original_history)

    def test_only_recorded_event_verification_separates_exception_from_report(self):
        current = (1, 1, 0, 1)
        local, sibling = (1, 0, 0, 1), (0, 0, 0, 1)
        probes = {'original': current, 'local': local, 'sibling': sibling}
        self.assertEqual(study.minimum_probe_set(probes, ('local', 'exception', 'report', 'parent')),
                         ('original', 'local', 'sibling'))
        coincident_original = (0, 0, 0, 0)
        probes['original'] = coincident_original
        self.assertIsNone(study.minimum_probe_set(probes, ('local', 'exception', 'report', 'parent')))

    def test_minimum_distinct_probes_can_require_joint_information(self):
        # Neither bit alone identifies XOR; duplicate first-bit probes add no help.
        probes = {'first': (0, 0, 1, 1), 'first_again': (0, 0, 1, 1), 'second': (0, 1, 0, 1)}
        self.assertEqual(study.minimum_probe_set(probes, (0, 1, 1, 0)), ('first', 'second'))
        self.assertEqual(study.minimum_probe_set(probes, (7, 7, 7, 7)), ())
        self.assertIsNone(study.minimum_probe_set({'first': probes['first']}, (0, 1, 1, 0)))

    def test_exact_query_value_and_fee_boundary(self):
        probes = {'useless': (0, 0, 0, 0), 'useful': (1, 0, 0, 1)}
        target = (1, 0, 0, 1)
        decision = study.analyze_target(probes, target, Fraction(1, 20))
        self.assertEqual(decision['before'], Fraction(1, 2))
        self.assertEqual(decision['after'], Fraction(1))
        self.assertEqual(decision['value'], Fraction(1, 2))
        self.assertEqual(decision['net'], Fraction(19, 20))
        self.assertTrue(decision['ask'])
        self.assertEqual(decision['selected'], 'useful')
        for fee in (Fraction(1, 2), Fraction(1), None):
            with self.subTest(fee=fee):
                self.assertFalse(study.analyze_target(probes, target, fee)['ask'])

    def test_no_questions_and_dependent_replay_cannot_create_information(self):
        target = (0, 1, 0, 1)
        for probes in ({}, {'report_replay': (2, 2, 2, 2)}):
            decision = study.analyze_target(probes, target, Fraction(0))
            self.assertFalse(decision['ask'])
            self.assertEqual(decision['value'], 0)
            self.assertEqual(decision['net'], Fraction(1, 2))

    def test_relabeling_worlds_and_handles_preserves_exact_query_value(self):
        target, probe = (0, 0, 1, 2), (0, 1, 2, 2)
        first = study.analyze_target({'alpha': probe}, target, Fraction(1, 20))
        permutation = (2, 0, 3, 1)
        second = study.analyze_target({'opaque-handle': tuple(probe[i] for i in permutation)},
                                      tuple(target[i] for i in permutation), Fraction(1, 20))
        for field in ('before', 'after', 'value', 'net', 'ask'):
            self.assertEqual(first[field], second[field])
        self.assertEqual(first['before'], Fraction(1, 2))
        self.assertEqual(first['after'], Fraction(3, 4))


if __name__ == '__main__':
    unittest.main()
