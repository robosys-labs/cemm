"""Synthetic provenance wrapper tests; never execute a scientific bank."""
from copy import deepcopy
import json
import subprocess
import sys
import unittest

from experiments.predictive_nucleus import effect_role_scoring as v1
from experiments.predictive_nucleus import effect_role_scoring_v2 as v2, effect_role_scoring_v3 as v3
from experiments.predictive_nucleus.tests.test_effect_role_scoring import fixture, LIMITS, one_hot
from experiments.predictive_nucleus.tests.test_effect_role_scoring_v2 import saved_row


class EffectRoleScoringV3Tests(unittest.TestCase):
    def test_fresh_functions_are_exact_v1_aliases(self):
        self.assertIs(v3.analyze, v1.analyze)
        self.assertIs(v3.retention, v1.retention)

    def test_both_references_preserve_numerics_with_current_controls(self):
        bundle, traces = fixture(); archive = deepcopy(traces['grounded'])
        before = deepcopy((bundle, traces, archive))
        expected = v2.analyze_opened(bundle, traces, archive, LIMITS)
        original_expected = deepcopy(expected)
        for reference in ('v1', 'v2'):
            with self.subTest(reference=reference):
                result = v3.analyze_opened(bundle, traces, archive, LIMITS, reference)
                self.assertEqual(result['version'], 'effect-role-opened-regression-v3')
                self.assertEqual(result['reference_study'], reference)
                for key in ('analysis', 'comparisons', 'checks', 'passed'):
                    self.assertEqual(result[key], expected[key])
                self.assertTrue(result['passed'])
                roles = result['evidence_roles']
                for arm in ('grounded', 'masked', 'parser', 'text_only'):
                    self.assertEqual(roles[arm]['origin'], 'current_v3')
                self.assertEqual(roles['reference_grounded']['origin'],
                    'archived_v1' if reference == 'v1' else 'frozen_v2_checkpoint_reforecast')
                self.assertEqual(roles['parser']['role'], 'parser_control')
                self.assertEqual(roles['text_only']['role'], 'text_only_control')
                self.assertEqual(roles['reference_grounded']['gated_view'], 'canonical')
                self.assertNotIn('reproduction_required', roles['text_only'])
                json.dumps(result, allow_nan=False)
        self.assertEqual((bundle, traces, archive), before)
        self.assertEqual(expected, original_expected)

    def test_failures_infinities_and_complete_point_inventory_match_v2(self):
        bundle, traces = fixture(); archive = deepcopy(traces['grounded'])
        first, second = [r for r in traces['grounded'] if r['view'] == 'canonical'][:2]
        first['logp'] = one_hot(8, 0)
        saved_row(archive, second['id'], second['step'])['logp'] = one_hot(8, 0)
        expected = v2.analyze_opened(bundle, traces, archive, LIMITS)
        for reference in ('v1', 'v2'):
            with self.subTest(reference=reference):
                result = v3.analyze_opened(bundle, traces, archive, LIMITS, reference)
                for key in ('analysis', 'comparisons', 'checks', 'passed'):
                    self.assertEqual(result[key], expected[key])
                self.assertFalse(result['passed'])
                self.assertFalse(result['checks']['opened_identifiable_world_retention'])
                canonical = result['comparisons']['canonical']
                self.assertEqual(len(canonical['points']), 48)
                self.assertEqual(canonical['nll_worse'], 1)
                self.assertEqual(canonical['nll_better'], 1)
                self.assertIsNone(canonical['mean_nll_change'])
                json.dumps(result, allow_nan=False)

    def test_reference_is_required_and_invalid_values_fail_closed(self):
        bundle, traces = fixture(); archive = deepcopy(traces['grounded'])
        with self.assertRaises(TypeError):
            v3.analyze_opened(bundle, traces, archive, LIMITS)
        for reference in (None, '', 'v3', 'V1', 'effect-role-v1', True, 1, [], {}):
            with self.subTest(reference=reference):
                with self.assertRaises(ValueError):
                    v3.analyze_opened(bundle, traces, archive, LIMITS, reference)

    def test_malformed_archive_still_fails_closed_for_each_study(self):
        bundle, traces = fixture(); archive = deepcopy(traces['grounded'])
        archive.pop()
        for reference in ('v1', 'v2'):
            with self.subTest(reference=reference):
                with self.assertRaises(ValueError):
                    v3.analyze_opened(bundle, traces, archive, LIMITS, reference)

    def test_import_does_not_load_models_or_generators(self):
        code = ('import sys; import experiments.predictive_nucleus.effect_role_scoring_v3; '
                'assert "torch" not in sys.modules; '
                'assert not any(k.endswith(("effect_role_data", "effect_role_model", '
                '"effect_role_data_v2", "effect_role_data_v3", "effect_role_neutral", '
                '"effect_role_lexical", "effect_role_lexical_fit")) for k in sys.modules)')
        subprocess.run([sys.executable, '-c', code], check=True)


if __name__ == '__main__': unittest.main()
