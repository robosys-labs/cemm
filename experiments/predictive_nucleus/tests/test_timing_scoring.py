"""Synthetic timing arithmetic and inventory failures; no model forecasts."""
from copy import deepcopy
import math
import unittest

from experiments.predictive_nucleus import acceptance_scoring as base
from experiments.predictive_nucleus import mixed_composition_run as mixed
from experiments.predictive_nucleus import timing_scoring as scoring
from experiments.predictive_nucleus.tests.test_acceptance_scoring import bits, row


LIMITS = {'identifiable_accuracy': .95, 'mean_oracle_kl': .05,
          'max_ambiguous_total_variation': .1, 'critical_pairs': 2,
          'min_critical_probability': .9, 'max_opposite_probability': .1,
          'min_timing_gap': .8, 'probability_tolerance': 1e-12}


def fixture():
    cases, raw = [], []
    for family in ('chain', 'disjoint'):
        n = 4 if family == 'disjoint' else 3
        for direction in (0, 1):
            identity = f'{family}-{direction}'
            for condition in scoring.CONDITIONS:
                episode = identity + '-' + condition
                case = {'episode': episode, 'family': family, 'partition': 'held_out',
                    'lineage': family, 'pair_id': family + '-' + condition, 'direction': direction,
                    'hidden_source_slot': 0, 'entities': n, 'contact_count': 4,
                    'group_step': 1, 'query_steps': [1, 2], 'critical': family == 'chain',
                    'condition': condition, 'ids': list('abcd'[:n]), 'pre_group_key': identity,
                    'timing_pair_id': identity, 'permutation_pair_id': 'permutation-' + identity,
                    'permutation_nontrivial': family == 'chain',
                    'forecast_information': []}
                acquisition = 4 * direction
                target = 1 if family == 'disjoint' or condition == 'ordered' else 2
                truths, previous = [acquisition, target, 7], 0
                for step, truth in enumerate(truths):
                    support = [0, 4] if step == 0 else [truth]
                    probabilities = [.5, .5] if step == 0 else [1.]
                    key = identity + f'-{step}' + ('' if step == 0 else '-' + condition)
                    info = {'possible_worlds': support, 'probabilities': probabilities,
                        'information_key': key, 'truth': bits(truth, n), 'previous_truth': bits(previous, n)}
                    case['forecast_information'].append(info)
                    vector = [0.] * 2 ** n
                    for world, probability in zip(support, probabilities, strict=True): vector[world] = probability
                    # Background-duration drift is permitted in the disjoint control.
                    if family == 'disjoint' and condition == 'ordered' and step == 1:
                        vector[truth], vector[0] = .99, .01
                    record = row(n, episode=episode, step=step, participant='frozen', truth=truth,
                        previous=previous, probabilities=vector, possible=support, family=family,
                        partition='held_out', pair_id=case['pair_id'], direction=direction)
                    record.update(lineage=family, information_key=key,
                                  action_kind='contact_group' if step == 1 else 'contact')
                    raw.append(record); previous = truth
                cases.append(case)
    points = base.score_rows(raw)['points']
    inventory = {c['episode']: c for c in cases}
    for point in points:
        info = inventory[point['episode']]['forecast_information'][point['step']]
        point.update(mixed.information_scores(point, info, [base._index(point['previous_truth'])]),
                     oracle_probabilities=info['probabilities'])
    return points, cases


def replace_forecast(points, cases, episode, step, *, probabilities=None, logs=None, status='ANSWERED'):
    case = next(c for c in cases if c['episode'] == episode)
    info = case['forecast_information'][step]
    position = next(i for i, p in enumerate(points) if (p['episode'], p['step']) == (episode, step))
    record = deepcopy(points[position]); record.update(status=status, log_probabilities=logs)
    if status == 'ANSWERED' and logs is None:
        record['log_probabilities'] = [math.log(p) if p else -math.inf for p in probabilities]
    point = base._point(record)
    point.update(mixed.information_scores(point, info, [base._index(point['previous_truth'])]),
                 oracle_probabilities=info['probabilities'])
    points[position] = point


class TimingScoringTests(unittest.TestCase):
    def test_complete_inventory_scores_timing_without_disjoint_equality_or_suffix_difference_gate(self):
        points, cases = fixture(); before = deepcopy((points, cases))
        result = scoring.summarize(points, cases, [7], LIMITS)
        self.assertEqual(result['decision']['decision'], 'KEEP_TIMING')
        self.assertTrue(result['execution_complete'])
        self.assertEqual(result['planned_points_per_seed'], 36)
        self.assertEqual(result['by_seed']['7']['identifiable']['correct'], 24)
        self.assertEqual(result['by_seed']['7']['identifiable_role_pairs']['correct'], 6)
        self.assertEqual(result['timing']['7']['critical_passed'], 2)
        self.assertEqual(result['permutation']['7']['equal'], 12)
        self.assertEqual(result['permutation']['7']['nontrivial_pairs_planned'], 2)
        self.assertEqual(result['permutation']['7']['nontrivial_points_equal'], 6)
        disjoint = next(r for r in result['timing']['7']['records'] if r['disjoint_control'])
        self.assertAlmostEqual(disjoint['temporal'][0]['full_vector_tv'], .01)
        self.assertLess(disjoint['temporal'][0]['common_minus_ordered_nll'], 0)
        chain = next(r for r in result['timing']['7']['records'] if r['critical'])
        self.assertFalse(chain['temporal'][0]['oracle_worlds_equal'])
        self.assertTrue(chain['temporal'][1]['oracle_worlds_equal'])
        self.assertEqual(chain['temporal'][1]['full_vector_tv'], 0.)
        self.assertEqual((points, cases), before)

    def test_missing_records_keep_whole_plan_and_absent_seed_denominators(self):
        points, cases = fixture(); points.pop(0)
        result = scoring.summarize(points, cases, [7, 11], LIMITS)
        self.assertEqual(result['decision']['decision'], 'STOP_INCOMPLETE_EXECUTION')
        self.assertEqual(len(result['missing_records']), 37)
        self.assertEqual(result['by_seed']['7']['all']['planned_points'], 36)
        self.assertEqual(result['by_seed']['7']['all']['support_coverage'], 35 / 36)
        self.assertEqual(result['by_seed']['11']['all']['planned_points'], 36)
        self.assertEqual(result['by_seed']['11']['all']['support_coverage'], 0.)
        self.assertIsNone(result['by_seed']['7']['all']['mean_nll'])
        self.assertEqual(result['timing']['11']['critical_planned'], 2)
        self.assertEqual(result['timing']['11']['critical_passed'], 0)

    def test_abstentions_and_unproduced_forecasts_cannot_pass_on_reduced_denominators(self):
        for status in ('ABSTAIN', 'UNPRODUCED'):
            with self.subTest(status=status):
                points, cases = fixture()
                replace_forecast(points, cases, 'chain-0-common_snapshot', 1, status=status)
                result = scoring.summarize(points, cases, [7], LIMITS)
                self.assertFalse(result['execution_complete'])
                self.assertEqual(result['timing']['7']['critical_planned'], 2)
                self.assertEqual(result['timing']['7']['critical_passed'], 1)
                self.assertEqual(result['by_seed']['7']['identifiable']['planned_points'], 24)
                self.assertEqual(result['by_seed']['7']['identifiable']['correct'], 23)

    def test_identical_timing_predictions_fail_critical_world_separation(self):
        points, cases = fixture()
        for condition in scoring.CONDITIONS[1:]:
            replace_forecast(points, cases, 'chain-0-' + condition, 1,
                             probabilities=[0., 1., 0., 0., 0., 0., 0., 0.])
        result = scoring.summarize(points, cases, [7], LIMITS)
        self.assertEqual(result['decision']['decision'], 'REVISE_TIMING')
        self.assertFalse(result['decision']['checks']['7']['every_critical_timing'])
        self.assertEqual(result['timing']['7']['critical_passed'], 1)
        self.assertEqual(result['by_seed']['7']['all']['infinite_nll_count'], 2)

    def test_timing_probability_boundary_and_matched_prefix_are_distinct_checks(self):
        for probability, passed in ((.9, True), (.8999, False)):
            points, cases = fixture()
            for condition in scoring.CONDITIONS:
                vector = [0.] * 8
                target = 1 if condition == 'ordered' else 2
                vector[target], vector[3 - target] = probability, 1. - probability
                replace_forecast(points, cases, 'chain-0-' + condition, 1, probabilities=vector)
            result = scoring.summarize(points, cases, [7], LIMITS)
            self.assertEqual(result['decision']['checks']['7']['every_critical_timing'], passed)
            self.assertEqual(result['decision']['decision'], 'KEEP_TIMING' if passed else 'REVISE_TIMING')
        points, cases = fixture()
        for condition in scoring.CONDITIONS[1:]:
            replace_forecast(points, cases, 'chain-0-' + condition, 0,
                             probabilities=[.6, 0., 0., 0., .4, 0., 0., 0.])
        result = scoring.summarize(points, cases, [7], LIMITS)
        self.assertFalse(result['decision']['checks']['7']['identical_pre_group_predictions'])
        self.assertTrue(result['decision']['checks']['7']['every_critical_timing'])

    def test_outside_support_mass_is_not_projected_away(self):
        points, cases = fixture()
        for condition in scoring.CONDITIONS[1:]:
            replace_forecast(points, cases, 'chain-0-' + condition, 1,
                             probabilities=[.15, 0., .85, 0., 0., 0., 0., 0.])
        result = scoring.summarize(points, cases, [7], LIMITS)
        self.assertEqual(result['decision']['decision'], 'REVISE_TIMING')
        contrast = next(r for r in result['timing']['7']['records'] if r['timing_pair_id'] == 'chain-0')
        self.assertAlmostEqual(contrast['own_world_probabilities'][1], .85)
        self.assertEqual(result['by_seed']['7']['all']['correct'], 30)
        self.assertGreater(result['by_seed']['7']['all']['mean_outside_support_mass'], 0)

    def test_permutation_compares_every_forecast_including_finite_underflowed_tails(self):
        for step in (0, 1, 2):
            points, cases = fixture()
            p = next(p for p in points if p['episode'] == 'chain-0-common_snapshot_permuted' and p['step'] == step)
            logs = [-1000. if v == 'negative_infinity' else v for v in p['log_probabilities']]
            replace_forecast(points, cases, p['episode'], step, logs=logs)
            result = scoring.summarize(points, cases, [7], LIMITS)
            self.assertEqual(result['decision']['decision'], 'REVISE_TIMING')
            self.assertFalse(result['decision']['checks']['7']['common_snapshot_permutation'])
            self.assertEqual(result['permutation']['7']['equal'], 11)

    def test_all_finite_underflowed_tails_remain_valid_and_do_not_change_native_exact_zero_rules(self):
        points, cases = fixture()
        for point in list(points):
            logs = [-1000. if v == 'negative_infinity' else v for v in point['log_probabilities']]
            replace_forecast(points, cases, point['episode'], point['step'], logs=logs)
        result = scoring.summarize(points, cases, [7], LIMITS)
        self.assertEqual(result['decision']['decision'], 'KEEP_TIMING')
        self.assertGreater(result['by_seed']['7']['all']['underflow_world_count'], 0)

    def test_wrong_metadata_and_duplicate_or_unplanned_points_are_rejected(self):
        for field in ('truth', 'information_key', 'ids', 'oracle_probabilities', 'family', 'step', 'duplicate'):
            with self.subTest(field=field):
                points, cases = fixture()
                if field == 'truth': points[0][field] = [1, 1, 1]
                elif field == 'ids': points[0][field] = list(reversed(points[0][field]))
                elif field == 'oracle_probabilities': points[0][field] = [.6, .4]
                elif field == 'step': points[0][field] = 99
                elif field == 'duplicate': points.append(deepcopy(points[0]))
                else: points[0][field] = 'wrong'
                with self.assertRaises(ValueError): scoring.summarize(points, cases, [7], LIMITS)

    def test_cross_context_pairs_or_gold_can_never_manufacture_a_timing_success(self):
        for corruption in ('history', 'critical', 'role', 'permutation', 'truth', 'probabilities', 'missing_case'):
            with self.subTest(corruption=corruption):
                points, cases = fixture()
                c = next(c for c in cases if c['episode'] == 'chain-0-common_snapshot')
                if corruption == 'history': c['pre_group_key'] = 'different'
                elif corruption == 'critical': c['critical'] = False
                elif corruption == 'role': c['direction'] = 1
                elif corruption == 'permutation': c['permutation_pair_id'] = 'wrong'
                elif corruption == 'truth': c['forecast_information'][1]['truth'] = [1, 1, 1]
                elif corruption == 'probabilities': c['forecast_information'][0]['probabilities'] = [.6, .6]
                else: cases.remove(c)
                with self.assertRaises(ValueError): scoring.summarize(points, cases, [7], LIMITS)

    def test_strict_json_infinity_values_and_two_infinite_losses_never_form_nan(self):
        points, cases = fixture()
        for condition in scoring.CONDITIONS:
            replace_forecast(points, cases, 'chain-0-' + condition, 2,
                             probabilities=[1., 0., 0., 0., 0., 0., 0., 0.])
        result = scoring.summarize(base._safe(points), cases, [7], LIMITS)
        record = next(r for r in result['timing']['7']['records'] if r['timing_pair_id'] == 'chain-0')
        self.assertTrue(record['temporal'][1]['both_infinite_nll'])
        self.assertIsNone(record['temporal'][1]['common_minus_ordered_nll'])
        self.assertEqual(result['by_seed']['7']['all']['mean_nll'], 'positive_infinity')


if __name__ == '__main__': unittest.main()
