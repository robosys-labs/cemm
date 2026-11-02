"""Fabricated saved-record invariants; no study bank, model or fitting."""
from copy import deepcopy
import json
import math
import subprocess
import sys
import unittest

from experiments.predictive_nucleus import acceptance_contract as c
from experiments.predictive_nucleus import effect_role_scoring as scoring

LIMITS = {'identifiable_accuracy': .95, 'mean_oracle_kl': .05,
    'max_ambiguous_total_variation': .1, 'identifiable_trajectory_accuracy': .95,
    'identifiable_role_pair_accuracy': .95, 'action_accuracy': .95,
    'max_bilingual_total_variation': .05, 'goal_optimal_accuracy': .95,
    'mean_goal_regret': .01, 'max_goal_regret': .05, 'min_effect_sensitive_goal_gain': .1,
    'min_effect_sensitive_goals': 16, 'max_retention_mean_nll': .05}


def logs(probabilities):
    return [math.log(p) if p else 'negative_infinity' for p in probabilities]


def one_hot(size, target):
    return logs([float(i == target) for i in range(size)])


def fixture(ambiguous=False):
    """A hand-made three-object inventory with all four goals and aligned twins."""
    roster = ['a', 'b', 'c']; records, gold, groups = [], [], []
    traces = {arm: [] for arm in scoring.ARMS}
    def render(a, b, setting, layout):
        word = ('zef' if setting else 'zor') if layout == 'osv' else ('lights' if setting else 'touches')
        tokens = {'svo': [roster[a], word, roster[b]], 'osv': [roster[b], roster[a], word],
                  'vos': [word, roster[b], roster[a]]}[layout]
        return ' '.join(tokens), word
    def advance(before, action):
        after = before.copy()
        if action[0]: after[action[1]] = 1
        else: after[action[2]] = 1 - before[action[1]] * before[action[2]]
        return after
    def distribution(before, action):
        truth = advance(before, action); support = [scoring._index(truth)]
        if ambiguous and not action[0]:
            other = truth.copy(); other[action[2]] ^= 1
            support.append(scoring._index(other))
        return sorted(support), [1 / len(support)] * len(support)
    for direction in (0, 1):
        for layout in ('svo', 'osv', 'vos'):
            group_id = f'goal-{direction}-{layout}'; members = []
            a, b = (0, 1) if direction == 0 else (1, 0)
            actions = [[0, a, b, -1], [0, b, a, -1], [1, a, -1, 1], [1, b, -1, 1]]
            prefix = [0, 0, 2, -1] if not direction else [0, 2, 0, -1]
            for choice, action in enumerate(actions):
                identity = f'case-{direction}-{layout}-{choice}'
                record = {'id': identity, 'entities': roster.copy(), 'anchor': [1, 1, 0],
                    'context': [{'action': [1, 0, -1, 1], 'reading': [1, 1, 0]}], 'utterances': []}
                chosen, cells, indices, forecasts = [prefix, action], [], [], []
                before = [1, 1, 0]
                for t, native in enumerate(chosen):
                    first = native[1]; second = native[2] if not native[0] else b if choice == 2 else a
                    text, word = render(first, second, native[0] == 1, layout)
                    after = advance(before, native)
                    record['utterances'].append({'text': text, 'reading': after})
                    menu = scoring._menu(record, t); index = menu.index(native)
                    worlds, probabilities = distribution(before, native)
                    indices.append(index); forecasts.append({'possible_worlds': worlds, 'probabilities': probabilities,
                        'surviving_modes': [0, 1] if ambiguous else [0],
                        'equivalent_action_indices': [i for i, option in enumerate(menu)
                            if distribution(before, option) == (worlds, probabilities)],
                        'information_key': scoring._key(record, t)})
                    cells.append({'word': word, 'layout': layout, 'new_word': bool(native[0]),
                                  'held_layout': bool(native[0]) and layout == 'vos'})
                    before = after
                meta = {'id': identity, 'law': 'nand', 'mode': 0, 'family': 'synthetic', 'lineage': 'synthetic-lineage',
                    'direction': direction, 'layout': layout, 'context_mode': 'unresolved' if ambiguous else 'established',
                    'phase': 0, 'actions': chosen, 'action_indices': indices,
                    'truth': [e['reading'].copy() for e in record['utterances']], 'forecasts': forecasts, 'cells': cells,
                    'role_pair_id': f'role-{layout}-{choice}',
                    'bilingual_pair_id': f'bilingual-{direction}-{choice}' if layout != 'vos' else None,
                    'translation_group_id': f'translation-{direction}-{choice}',
                    'effect_pair_id': f'effect-{group_id}-{choice % 2}', 'goal_group_id': group_id,
                    'final_choice': choice, 'shared_prefix_sha256': c.digest(scoring._prefix(record))}
                records.append(record); gold.append(meta); members.append(identity)
                for arm in scoring.ARMS:
                    for t, expected in enumerate(forecasts):
                        probabilities = [dict(zip(expected['possible_worlds'], expected['probabilities'], strict=True)).get(i, 0.)
                                         for i in range(8)]
                        traces[arm].append({'id': identity, 'step': t, 'view': 'canonical',
                            'logp': logs(probabilities) if arm != 'text_only' else [-math.log(8)] * 8,
                            'action_logp': None if arm == 'text_only' else one_hot(4, indices[t])})
                        if arm == 'grounded':
                            traces[arm].append({'id': identity, 'step': t, 'view': 'masked',
                                'logp': [-math.log(8)] * 8, 'action_logp': [-math.log(4)] * 4})
            first = records[-4]; before = first['utterances'][-2]['reading']; goal_rows = []
            for bits in ([0, 0], [0, 1], [1, 0], [1, 1]):
                target = list(before); target[a], target[b] = bits
                utilities = [dict(zip(m['forecasts'][-1]['possible_worlds'], m['forecasts'][-1]['probabilities'], strict=True)).get(
                    scoring._index(target), 0.) for m in gold[-4:]]
                maximum = max(utilities); contact, setting = max(utilities[:2]), max(utilities[2:])
                goal_rows.append({'id': group_id + ''.join(map(str, bits)), 'target_bits': bits,
                    'oracle_utilities': utilities, 'optimal_choices': [i for i, u in enumerate(utilities) if u == maximum],
                    'max_utility': maximum, 'attainable': maximum > 0, 'effect_sensitive': contact != setting,
                    'set_required': setting > contact, 'contact_required': contact > setting})
            groups.append({'id': group_id, 'episodes': members, 'participants': [a, b], 'before': before.copy(),
                           'shared_prefix_sha256': c.digest(scoring._prefix(first)), 'goals': goal_rows})
    inputs = {'version': 'bilingual-input-v1', 'episodes': records}
    return {'inputs': inputs, 'oracle': {'version': 'effect-role-oracle-v1', 'input_sha256': c.digest(inputs),
        'source_sha256': 'a' * 64, 'information_law_sha256': 'b' * 64, 'episodes': gold}, 'goal_groups': groups}, traces


def retention_fixture(count=1):
    inputs = {'version': 'bilingual-input-v1', 'episodes': [{'id': 'synthetic-retention',
        'entities': ['a', 'b', 'c'], 'anchor': [0, 0, 0],
        'context': [{'action': [1, 0, -1, 0], 'reading': [0, 0, 0]}],
        'utterances': [{'text': 'a touches b', 'reading': [0, 0, 0]} for _ in range(count)]}]}
    old = [{'id': 'synthetic-retention', 'step': t, 'view': 'canonical',
            'logp': logs([.99, .01] + [0.] * 6), 'order_logp': logs([.8, .2])} for t in range(count)]
    now = [{k: v for k, v in row.items() if k != 'order_logp'} | {'action_logp': logs([.78, .2, .01, .01])}
           for row in deepcopy(old)]
    return inputs, now, old


class EffectRoleScoringTests(unittest.TestCase):
    def test_complete_synthetic_pass_and_failed_controls_are_separate(self):
        bundle, traces = fixture(); before = deepcopy((bundle, traces, LIMITS))
        result = scoring.analyze(bundle, traces, LIMITS)
        self.assertTrue(result['passed'], result['checks'])
        self.assertEqual(result['reports']['grounded']['all']['planned_points'], 48)
        self.assertLess(result['reports']['text_only']['all']['accuracy'], .95)
        self.assertIsNone(result['reports']['text_only']['actions']['accuracy'])
        self.assertEqual(result['goals']['grounded']['all']['planned'], 24)
        self.assertEqual(result['goals']['grounded']['impossible']['planned'], 6)
        self.assertEqual(result['goals']['grounded']['impossible']['optimal_accuracy'], 1.)
        self.assertEqual(result['goals']['grounded']['set_required']['planned'], 6)
        self.assertEqual(result['goals']['grounded']['contact_required']['planned'], 12)
        self.assertEqual((bundle, traces, LIMITS), before)
        json.dumps(result, allow_nan=False)

    def test_ambiguity_keeps_actual_errors_but_gates_conditional_forecasts(self):
        bundle, traces = fixture(True); result = scoring.analyze(bundle, traces, LIMITS)
        self.assertTrue(result['passed'], result['checks'])
        score = result['reports']['grounded']
        self.assertLess(score['all']['accuracy'], 1.)
        self.assertEqual(score['identifiable']['accuracy'], 1.)
        self.assertEqual(score['ambiguous']['mean_oracle_kl'], 0.)
        self.assertLess(score['trajectories']['correct'], score['trajectories']['planned'])
        self.assertEqual(score['trajectories']['identifiable_accuracy'], 1.)

    def test_action_identity_does_not_become_false_endpoint_gold(self):
        bundle, traces = fixture()
        meta = next(m for m in bundle['oracle']['episodes'] if m['layout'] == 'svo' and m['final_choice'] == 2)
        equivalent = meta['forecasts'][-1]['equivalent_action_indices']
        alternative = next(i for i in equivalent if i != meta['action_indices'][-1])
        row = next(r for r in traces['grounded'] if r['id'] == meta['id'] and r['step'] == 1 and r['view'] == 'canonical')
        row['action_logp'] = one_hot(4, alternative)
        result = scoring.analyze(bundle, traces, LIMITS)
        self.assertFalse(result['checks']['globally_taught_action_identity'])
        self.assertTrue(result['checks']['identifiable_accuracy'])
        point = next(p for p in result['points']['grounded'] if p['episode'] == meta['id'] and p['step'] == 1)
        self.assertFalse(point['action_correct']); self.assertTrue(point['endpoint_action_compatible'])
        self.assertTrue(point['correct'])

    def test_scientific_failures_return_every_point_goal_and_check(self):
        bundle, traces = fixture()
        for row in traces['grounded']:
            if row['view'] == 'canonical': row['logp'], row['action_logp'] = [-math.log(8)] * 8, [-math.log(4)] * 4
        result = scoring.analyze(bundle, traces, LIMITS)
        self.assertFalse(result['passed'])
        self.assertEqual(len(result['points']['grounded']), 48)
        self.assertEqual(len(result['goals']['grounded']['records']), 24)
        for key in ('identifiable_accuracy', 'supported_MAP_worlds', 'known_unchanged_preserved',
                    'conditional_probability_quality', 'goal_optimal_choices', 'goal_mean_regret',
                    'goal_max_regret', 'masked_goal_gain', 'text_only_goal_gain'):
            self.assertFalse(result['checks'][key], key)

    def test_actual_mode_peeking_fails_probability_gate_without_aborting(self):
        bundle, traces = fixture(True)
        gold = {m['id']: m for m in bundle['oracle']['episodes']}
        for row in traces['grounded']:
            if row['view'] == 'canonical': row['logp'] = one_hot(8, scoring._index(gold[row['id']]['truth'][row['step']]))
        result = scoring.analyze(bundle, traces, LIMITS)
        self.assertEqual(result['reports']['grounded']['all']['accuracy'], 1.)
        self.assertFalse(result['checks']['conditional_probability_quality'])
        self.assertFalse(result['checks']['ambiguous_no_collapse'])
        self.assertEqual(result['reports']['grounded']['ambiguous']['mean_oracle_kl'], 'positive_infinity')
        json.dumps(result, allow_nan=False)

    def test_held_new_word_calibration_cannot_hide_in_family_average(self):
        bundle, traces = fixture(); gold = {m['id']: m for m in bundle['oracle']['episodes']}
        for row in traces['grounded']:
            meta = gold[row['id']]
            if row['view'] == 'canonical' and meta['cells'][row['step']]['held_layout']:
                world = scoring._index(meta['truth'][row['step']]); probabilities = [0.] * 8
                probabilities[world], probabilities[world ^ 1] = .9, .1
                row['logp'] = logs(probabilities)
        result = scoring.analyze(bundle, traces, LIMITS)
        family = result['reports']['grounded']['by_family']['synthetic']['identifiable']
        self.assertLess(family['mean_oracle_kl'], LIMITS['mean_oracle_kl'])
        self.assertTrue(result['checks']['identifiable_accuracy'])
        self.assertFalse(result['checks']['conditional_probability_quality'])
        cell = result['reports']['grounded']['by_cell']['synthetic/vos/set/new']['identifiable']
        self.assertGreater(cell['mean_oracle_kl'], LIMITS['mean_oracle_kl'])

    def test_goal_rewards_require_spectator_preservation(self):
        bundle, traces = fixture(); group = bundle['goal_groups'][0]
        target = group['before'].copy(); target[:2] = [1, 1]
        bad = target.copy(); bad[2] ^= 1
        row = next(r for r in traces['grounded'] if r['id'] == group['episodes'][2] and r['step'] == 1 and r['view'] == 'canonical')
        row['logp'] = one_hot(8, scoring._index(bad))
        result = scoring.analyze(bundle, traces, LIMITS)
        goal = next(g for g in result['goals']['grounded']['records'] if g['group_id'] == group['id'] and g['target_bits'] == [1, 1])
        self.assertEqual(goal['chosen'], 3)
        self.assertEqual(goal['predicted_utilities'][2], 0.)
        self.assertFalse(result['checks']['known_unchanged_preserved'])

    def test_goal_decisions_use_log_space_before_probability_underflow(self):
        bundle, traces = fixture(); group = bundle['goal_groups'][0]
        target = group['before'].copy(); target[:2] = [1, 1]; world = scoring._index(target)
        for choice, identity in enumerate(group['episodes']):
            row = next(r for r in traces['grounded'] if r['id'] == identity and r['step'] == 1 and r['view'] == 'canonical')
            row['logp'] = one_hot(8, 0); row['logp'][world] = -900. if choice != 3 else -800.
        result = scoring.analyze(bundle, traces, LIMITS)
        goal = next(g for g in result['goals']['grounded']['records'] if g['group_id'] == group['id'] and g['target_bits'] == [1, 1])
        self.assertEqual(goal['predicted_utilities'], [0.] * 4)
        self.assertEqual(goal['chosen'], 3)

    def test_named_inventory_and_null_control_action_law_fail_closed(self):
        for defect in ('missing', 'duplicate', 'foreign', 'bool_step', 'extra_view', 'extra_field',
                       'nan', 'positive_inf', 'mass', 'dimension', 'grounded_null', 'text_not_null'):
            with self.subTest(defect=defect):
                bundle, traces = fixture(); rows = traces['grounded']; row = rows[0]
                if defect == 'missing': rows.pop()
                elif defect == 'duplicate': rows.append(deepcopy(row))
                elif defect == 'foreign': row['id'] = 'foreign'
                elif defect == 'bool_step': row['step'] = True
                elif defect == 'extra_view': row['view'] = 'swapped'
                elif defect == 'extra_field': row['gold'] = 1
                elif defect == 'nan': row['logp'][0] = math.nan
                elif defect == 'positive_inf': row['action_logp'][0] = math.inf
                elif defect == 'mass': row['logp'] = [0.] * 8
                elif defect == 'dimension': row['action_logp'] = [0.]
                elif defect == 'grounded_null': row['action_logp'] = None
                else: traces['text_only'][0]['action_logp'] = [-math.log(4)] * 4
                with self.assertRaises(ValueError): scoring.analyze(bundle, traces, LIMITS)

    def test_oracle_pair_prefix_and_goal_inconsistency_fail_closed(self):
        for defect in ('source', 'truth', 'action', 'probabilities', 'information_key', 'prefix',
                       'pair', 'goal_prefix', 'goal_utilities', 'goal_sensitivity', 'goal_target', 'goal_missing'):
            with self.subTest(defect=defect):
                bundle, traces = fixture(); meta = bundle['oracle']['episodes'][0]
                goal = bundle['goal_groups'][0]['goals'][0]
                if defect == 'source': bundle['oracle']['source_sha256'] = 'invalid'
                elif defect == 'truth': meta['truth'][0][0] ^= 1
                elif defect == 'action': meta['action_indices'][0] ^= 1
                elif defect == 'probabilities': meta['forecasts'][0]['probabilities'] = [.5]
                elif defect == 'information_key': meta['forecasts'][0]['information_key'] = '0' * 64
                elif defect == 'prefix': meta['shared_prefix_sha256'] = '0' * 64
                elif defect == 'pair': meta['role_pair_id'] = 'foreign'
                elif defect == 'goal_prefix': bundle['goal_groups'][0]['shared_prefix_sha256'] = '0' * 64
                elif defect == 'goal_utilities': goal['oracle_utilities'][0] = 1.
                elif defect == 'goal_sensitivity': goal['effect_sensitive'] = True
                elif defect == 'goal_target': goal['target_bits'] = [1, 1]
                else: bundle['goal_groups'].pop()
                with self.assertRaises(ValueError): scoring.analyze(bundle, traces, LIMITS)

    def test_information_key_excludes_current_and_future_feedback(self):
        bundle, _ = fixture(); record = deepcopy(bundle['inputs']['episodes'][0])
        expected = scoring._key(record, 0)
        record['utterances'][0]['reading'][0] ^= 1; record['utterances'][1]['text'] = 'c lights a'
        self.assertEqual(scoring._key(record, 0), expected)
        record['context'][-1]['reading'][0] ^= 1
        self.assertNotEqual(scoring._key(record, 0), expected)

    def test_required_prospective_limits_cannot_be_omitted_or_nonfinite(self):
        bundle, traces = fixture()
        for name in scoring.LIMITS:
            for invalid in (None, -1., math.inf, math.nan, True):
                with self.subTest(name=name, value=invalid), self.assertRaises(ValueError):
                    scoring.analyze(bundle, traces, {**LIMITS, name: invalid})
            reduced = {k: v for k, v in LIMITS.items() if k != name}
            with self.subTest(missing=name), self.assertRaises(ValueError):
                scoring.analyze(bundle, traces, reduced)
        for invalid in (0, 1.5):
            with self.subTest(count=invalid), self.assertRaises(ValueError):
                scoring.analyze(bundle, traces, {**LIMITS, 'min_effect_sensitive_goals': invalid})

    def test_import_never_loads_model_or_study_generator(self):
        code = ('import sys; import experiments.predictive_nucleus.effect_role_scoring; '
                'assert "torch" not in sys.modules; '
                'assert "experiments.predictive_nucleus.effect_role_data" not in sys.modules; '
                'assert "experiments.predictive_nucleus.effect_role_model" not in sys.modules')
        subprocess.run([sys.executable, '-c', code], check=True)


class EffectRoleRetentionTests(unittest.TestCase):
    def test_probability_changes_are_reported_without_an_equality_gate(self):
        inputs, now, old = retention_fixture(); before = deepcopy((inputs, now, old))
        now[0]['logp'] = logs([.98, .02] + [0.] * 6)
        result = scoring.retention(inputs, now, old, LIMITS)
        self.assertTrue(result['passed']); self.assertGreater(result['max_logp_change'], .1)
        self.assertEqual(result['exact_world_vectors'], 0)
        self.assertAlmostEqual(result['mean_candidate_set_mass'], .02)
        self.assertAlmostEqual(sum(result['points'][0]['action_probability_changes']), 0.)
        self.assertEqual((inputs, old), (before[0], before[2]))
        self.assertEqual(result['points'][0]['map_action'], 0)

    def test_set_action_leakage_fails_even_when_world_forecast_is_unchanged(self):
        inputs, now, old = retention_fixture()
        now[0]['action_logp'] = logs([.1, .1, .7, .1])
        result = scoring.retention(inputs, now, old, LIMITS)
        self.assertFalse(result['checks']['retention_action_MAP'])
        self.assertTrue(result['checks']['no_exact_regressions'])
        self.assertEqual(result['exact_world_vectors'], 1)
        self.assertEqual(result['action_map_changes'], [['synthetic-retention', 0]])
        self.assertAlmostEqual(result['max_candidate_set_mass'], .8)

    def test_complete_numerical_failure_report_handles_opposing_infinities(self):
        inputs, now, old = retention_fixture(3)
        now[0]['logp'] = old[0]['logp'] = one_hot(8, 1)
        now[1]['logp'] = one_hot(8, 1); old[2]['logp'] = one_hot(8, 1)
        result = scoring.retention(inputs, now[::-1], old, LIMITS)
        self.assertFalse(result['passed']); self.assertEqual(result['planned'], 3)
        self.assertEqual([p['nll_change'] for p in result['points']], [None, 'positive_infinity', 'negative_infinity'])
        self.assertIsNone(result['mean_nll_change'])
        self.assertEqual(result['regressions'], [['synthetic-retention', 1]])
        self.assertEqual(result['repairs'], [['synthetic-retention', 2]])
        json.dumps(result, allow_nan=False)

    def test_retention_mean_loss_can_fail_with_all_exact_predictions_preserved(self):
        inputs, now, old = retention_fixture(); now[0]['logp'] = logs([.9, .1] + [0.] * 6)
        result = scoring.retention(inputs, now, old, LIMITS)
        self.assertTrue(result['checks']['no_exact_regressions'])
        self.assertFalse(result['checks']['retention_mean_nll'])

    def test_retention_inventory_auxiliary_views_and_normalization(self):
        inputs, now, old = retention_fixture()
        archive = old + [dict(old[0], view='masked'), dict(old[0], view='swapped')]
        self.assertEqual(scoring.retention(inputs, now, archive, LIMITS)['planned'], 1)
        for value in ([], now * 2, [dict(now[0], view='masked')], [dict(now[0], step=True)],
                      [dict(now[0], action_logp=None)], [dict(now[0], logp=[0.] * 8)]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                scoring.retention(inputs, value, old, LIMITS)
        for value in (old * 2, [], old + [dict(old[0], view='foreign')]):
            with self.subTest(archive=value), self.assertRaises(ValueError):
                scoring.retention(inputs, now, value, LIMITS)


if __name__ == '__main__': unittest.main()
