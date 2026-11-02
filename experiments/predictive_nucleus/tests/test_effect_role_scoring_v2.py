"""Synthetic opened-bank invariants; never execute the scientific study."""
from copy import deepcopy
import json
import math
import subprocess
import sys
import unittest

from experiments.predictive_nucleus import acceptance_contract as c
from experiments.predictive_nucleus import effect_role_scoring as v1, effect_role_scoring_v2 as v2
from experiments.predictive_nucleus.tests.test_effect_role_scoring import fixture, LIMITS, logs, one_hot


def repeated_fixture(count):
    bundle, traces = fixture(); result = deepcopy(bundle); collected = {arm: [] for arm in traces}
    result['inputs']['episodes'], result['oracle']['episodes'], result['goal_groups'] = [], [], []
    for copy in range(count):
        suffix = '-copy' + str(copy)
        for record in deepcopy(bundle['inputs']['episodes']):
            record['id'] += suffix; result['inputs']['episodes'].append(record)
        for meta in deepcopy(bundle['oracle']['episodes']):
            for key in ('id', 'lineage', 'role_pair_id', 'bilingual_pair_id',
                        'translation_group_id', 'effect_pair_id', 'goal_group_id'):
                if meta[key] is not None: meta[key] += suffix
            result['oracle']['episodes'].append(meta)
        for group in deepcopy(bundle['goal_groups']):
            group['id'] += suffix; group['episodes'] = [e + suffix for e in group['episodes']]
            for goal in group['goals']: goal['id'] += suffix
            result['goal_groups'].append(group)
        for arm, rows in deepcopy(traces).items():
            for row in rows: row['id'] += suffix
            collected[arm].extend(rows)
    result['oracle']['input_sha256'] = c.digest(result['inputs'])
    return result, collected


def saved_row(rows, identity, step, view='canonical'):
    return next(row for row in rows if (row['id'], row['step'], row['view']) == (identity, step, view))


class EffectRoleScoringV2Tests(unittest.TestCase):
    def test_fresh_functions_are_exact_v1_aliases(self):
        self.assertIs(v2.analyze, v1.analyze); self.assertIs(v2.retention, v1.retention)

    def test_identical_opened_records_pass_and_archived_controls_are_explicit(self):
        bundle, traces = fixture(); archive = deepcopy(traces['grounded']); before = deepcopy((bundle, traces, archive))
        result = v2.analyze_opened(bundle, traces, archive, LIMITS)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['analysis'], v1.analyze(bundle, traces, LIMITS))
        self.assertEqual(set(result['checks']) - result['analysis']['checks'].keys(),
                         {'opened_identifiable_world_retention', 'opened_taught_action_retention'})
        for view in ('canonical', 'masked'):
            comparison = result['comparisons'][view]
            self.assertEqual(comparison['planned'], 48)
            self.assertEqual(comparison['world_regressions'], [])
            self.assertEqual(comparison['action_regressions'], [])
            self.assertEqual(comparison['mean_nll_change'], 0.)
        for arm in ('parser', 'text_only'):
            self.assertEqual(result['evidence_roles'][arm]['origin'], 'archived_v1')
        self.assertEqual(result['evidence_roles']['reference_grounded']['gated_view'], 'canonical')
        self.assertEqual((bundle, traces, archive), before)
        json.dumps(result, allow_nan=False)

    def test_previously_correct_action_regression_fails_even_above_v1_floor(self):
        bundle, traces = repeated_fixture(5); archive = deepcopy(traces['grounded'])
        meta = next(m for m in bundle['oracle']['episodes'] if m['layout'] == 'svo' and m['final_choice'] == 2)
        target = meta['action_indices'][-1]
        alternate = next(i for i in meta['forecasts'][-1]['equivalent_action_indices'] if i != target)
        saved_row(traces['grounded'], meta['id'], 1)['action_logp'] = one_hot(4, alternate)
        result = v2.analyze_opened(bundle, traces, archive, LIMITS)
        self.assertTrue(result['analysis']['passed'], result['analysis']['checks'])
        self.assertFalse(result['checks']['opened_taught_action_retention'])
        self.assertTrue(result['checks']['opened_identifiable_world_retention'])
        comparison = result['comparisons']['canonical']
        self.assertEqual(comparison['new_word_action_regressions'], [[meta['id'], 1]])
        self.assertEqual(comparison['world_regressions'], [])
        self.assertEqual(comparison['old_word_action_regressions'], [])

    def test_ambiguity_consistent_actual_regression_does_not_fail_retention(self):
        bundle, traces = fixture(True); archive = deepcopy(traces['grounded'])
        meta = next(m for m in bundle['oracle']['episodes'] if m['direction'] == 0 and m['layout'] == 'svo' and m['final_choice'] == 0)
        worlds = meta['forecasts'][-1]['possible_worlds']
        self.assertEqual(v1._index(meta['truth'][-1]), worlds[0])
        probabilities = [0.] * 8; probabilities[worlds[0]], probabilities[worlds[1]] = .49, .51
        saved_row(traces['grounded'], meta['id'], 1)['logp'] = logs(probabilities)
        result = v2.analyze_opened(bundle, traces, archive, LIMITS)
        self.assertTrue(result['passed'], result['checks'])
        comparison = result['comparisons']['canonical']
        self.assertEqual(comparison['world_regressions'], [[meta['id'], 1]])
        self.assertEqual(comparison['ambiguous_world_regressions'], [[meta['id'], 1]])
        self.assertEqual(comparison['identifiable_world_regressions'], [])
        self.assertEqual(comparison['world_map_changes'], [[meta['id'], 1]])

    def test_masked_accidental_successes_are_reported_without_retention_gates(self):
        bundle, traces = fixture(); archive = deepcopy(traces['grounded'])
        for row in archive:
            if row['view'] == 'masked':
                canonical = saved_row(archive, row['id'], row['step'])
                row['logp'], row['action_logp'] = canonical['logp'][:], canonical['action_logp'][:]
        result = v2.analyze_opened(bundle, traces, archive, LIMITS)
        self.assertTrue(result['passed'], result['checks'])
        self.assertGreater(len(result['comparisons']['masked']['world_regressions']), 0)
        self.assertGreater(len(result['comparisons']['masked']['action_regressions']), 0)
        self.assertEqual(result['comparisons']['canonical']['world_regressions'], [])

    def test_valid_world_failure_keeps_later_repairs_and_every_record(self):
        bundle, traces = fixture(); archive = deepcopy(traces['grounded'])
        first, second = [r for r in traces['grounded'] if r['view'] == 'canonical'][:2]
        first['logp'] = one_hot(8, 0)
        saved_row(archive, second['id'], second['step'])['logp'] = one_hot(8, 0)
        result = v2.analyze_opened(bundle, traces, archive, LIMITS)
        comparison = result['comparisons']['canonical']
        self.assertFalse(result['passed']); self.assertFalse(result['checks']['opened_identifiable_world_retention'])
        self.assertEqual(comparison['world_regressions'], [[first['id'], first['step']]])
        self.assertEqual(comparison['world_repairs'], [[second['id'], second['step']]])
        self.assertEqual(len(comparison['points']), 48)
        self.assertIsNone(comparison['mean_nll_change'])
        self.assertEqual(comparison['nll_worse'], 1); self.assertEqual(comparison['nll_better'], 1)
        json.dumps(result, allow_nan=False)

    def test_wrong_to_different_wrong_action_is_not_a_correct_action_regression(self):
        bundle, traces = fixture(); archive = deepcopy(traces['grounded'])
        row = next(r for r in traces['grounded'] if r['view'] == 'canonical')
        saved_row(archive, row['id'], row['step'])['action_logp'] = one_hot(4, 1)
        row['action_logp'] = one_hot(4, 2)
        result = v2.analyze_opened(bundle, traces, archive, LIMITS)
        self.assertTrue(result['checks']['opened_taught_action_retention'])
        self.assertFalse(result['analysis']['checks']['globally_taught_action_identity'])
        self.assertEqual(result['comparisons']['canonical']['action_regressions'], [])
        self.assertEqual(result['comparisons']['canonical']['action_map_changes'], [[row['id'], row['step']]])

    def test_malformed_archives_and_controls_fail_closed(self):
        for defect in ('missing', 'duplicate', 'foreign', 'missing_masked', 'extra_view', 'null_action', 'nan', 'mass', 'control_nullness'):
            with self.subTest(defect=defect):
                bundle, traces = fixture(); archive = deepcopy(traces['grounded'])
                if defect == 'missing': archive.pop()
                elif defect == 'duplicate': archive.append(deepcopy(archive[0]))
                elif defect == 'foreign': archive[0]['id'] = 'foreign'
                elif defect == 'missing_masked': archive = [r for r in archive if r['view'] == 'canonical']
                elif defect == 'extra_view': archive[0]['view'] = 'swapped'
                elif defect == 'null_action': archive[0]['action_logp'] = None
                elif defect == 'nan': archive[0]['logp'][0] = math.nan
                elif defect == 'mass': archive[0]['logp'] = [0.] * 8
                else: traces['text_only'][0]['action_logp'] = one_hot(4, 0)
                with self.assertRaises(ValueError): v2.analyze_opened(bundle, traces, archive, LIMITS)

    def test_import_does_not_load_models_or_generators(self):
        code = ('import sys; import experiments.predictive_nucleus.effect_role_scoring_v2; '
                'assert "torch" not in sys.modules; '
                'assert not any(k.endswith(("effect_role_data", "effect_role_model", "effect_role_data_v2", '
                '"effect_role_model_v2")) for k in sys.modules)')
        subprocess.run([sys.executable, '-c', code], check=True)


if __name__ == '__main__': unittest.main()
