"""Hand-computed acceptance arithmetic and artifact wiring; no research scores."""
from contextlib import redirect_stdout
from copy import deepcopy
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import tempfile
import unittest

from experiments.predictive_nucleus import acceptance_scoring as scoring


def bits(index, entities):
    return [int(bit) for bit in format(index, f'0{entities}b')]


def row(entities=3, *, episode='case', step=0, participant='reference', seed=7,
        truth=0, previous=0, probabilities=None, logs=None, status='ANSWERED', possible=None,
        family='family', partition='in_family', pair_id=None, direction=None):
    if status == 'ANSWERED' and logs is None:
        probabilities = probabilities if probabilities is not None else [1.] + [0.] * (2 ** entities - 1)
        logs = [math.log(p) if p else -math.inf for p in probabilities]
    return {'participant': participant, 'model_seed': seed, 'episode': episode, 'step': step,
        'family': family, 'partition': partition, 'lineage': 'physical-cluster',
        'pair_id': pair_id, 'direction': direction, 'ids': list('abcdef'[:entities]),
        'truth': bits(truth, entities), 'previous_truth': bits(previous, entities),
        'possible_worlds': [truth] if possible is None else possible, 'information_key': '0' * 64,
        'action_kind': 'contact', 'status': status, 'log_probabilities': logs,
        'wall_seconds': .002 if status != 'UNPRODUCED' else None,
        'cpu_seconds': .001 if status != 'UNPRODUCED' else None}


def wrong(**kwargs):
    return row(probabilities=[0., 1.] + [0.] * 6, **kwargs)


class AcceptanceScoringTests(unittest.TestCase):
    def test_uniform_and_point_mass_scores_use_every_joint_world_at_each_size(self):
        for n in range(3, 7):
            with self.subTest(entities=n):
                uniform = row(n, logs=[-n * math.log(2)] * (2 ** n), truth=2 ** n - 1)
                result = scoring.score_rows([uniform])
                point, summary = result['points'][0], result['aggregate']['all']
                self.assertAlmostEqual(point['nll'], n * math.log(2), places=12)
                self.assertAlmostEqual(point['brier'], 1 - 1 / 2 ** n, places=12)
                self.assertEqual(point['map_world'], 0)
                self.assertEqual(point['maximizers'], list(range(2 ** n)))
                self.assertEqual((summary['tied_forecasts'], summary['correct']), (1, 0))
                correct = scoring.score_rows([row(n)])['points'][0]
                bad = scoring.score_rows([row(n, truth=1)])['points'][0]
                self.assertEqual((correct['nll'], correct['brier']), (0., 0.))
                self.assertEqual((bad['nll'], bad['brier']), ('positive_infinity', 2.))

    def test_joint_correlations_cannot_be_replaced_with_products_of_bit_marginals(self):
        correlated = [.5, 0., 0., .5] + [0.] * 4
        independent = [.25] * 4 + [0.] * 4
        for slot in (1, 2):
            self.assertEqual(sum(p for i, p in enumerate(correlated) if bits(i, 3)[slot]),
                             sum(p for i, p in enumerate(independent) if bits(i, 3)[slot]))
        result = scoring.score_rows([row(participant='correlated', probabilities=correlated),
                                     row(participant='independent', probabilities=independent)])
        a, b = [result['participants'][name]['aggregate']['all'] for name in ('correlated', 'independent')]
        self.assertAlmostEqual(a['mean_nll'], math.log(2))
        self.assertAlmostEqual(b['mean_nll'], math.log(4))
        self.assertEqual((a['mean_brier'], b['mean_brier']), (.5, .75))

    def test_declared_information_support_never_conditions_or_repairs_the_forecast(self):
        submitted = row(probabilities=[.25, .25, .5] + [0.] * 5, possible=[0, 1])
        before = deepcopy(submitted)
        report = scoring.score_rows([submitted])
        point = report['points'][0]
        self.assertFalse(point['answerable'])
        self.assertAlmostEqual(point['nll'], math.log(4))
        self.assertEqual(point['brier'], .875)
        self.assertEqual(point['map_world'], 2)
        self.assertEqual(report['aggregate']['answerable']['planned_points'], 0)
        self.assertEqual(submitted, before)

    def test_proper_scores_favor_the_declared_nonuniform_law_in_expectation(self):
        records = []
        for participant, p in (('honest', [.75, .25]), ('uniform', [.5, .5]), ('overconfident', [.9, .1])):
            records.extend(row(episode=f'case-{i}', participant=participant, truth=truth,
                               probabilities=p + [0.] * 6, possible=[0, 1])
                           for i, truth in enumerate((0, 0, 0, 1)))
        reports = scoring.score_rows(records)['participants']
        honest = reports['honest']['aggregate']['all']
        self.assertAlmostEqual(honest['mean_nll'], -.75 * math.log(.75) - .25 * math.log(.25))
        self.assertAlmostEqual(honest['mean_brier'], .375)
        for name in ('uniform', 'overconfident'):
            other = reports[name]['aggregate']['all']
            self.assertLess(honest['mean_nll'], other['mean_nll'])
            self.assertLess(honest['mean_brier'], other['mean_brier'])

    def test_finite_underflow_and_exact_zero_keep_distinct_uncapped_losses(self):
        records = [row(episode='finite', logs=[0., -1000.] + [-math.inf] * 6, truth=1),
                   row(episode='zero', truth=1)]
        report = scoring.score_rows(records)
        finite, zero = report['points']
        self.assertEqual((finite['nll'], finite['underflow_world_count']), (1000., 1))
        self.assertEqual((zero['nll'], zero['underflow_world_count']), ('positive_infinity', 0))
        self.assertEqual(report['aggregate']['all']['mean_nll'], 'positive_infinity')
        self.assertEqual(report['aggregate']['all']['infinite_nll_count'], 1)
        self.assertEqual(finite['log_probabilities'][1], -1000.)
        json.dumps(report, allow_nan=False)

    def test_missing_distributions_retain_denominators_without_inventing_probability_scores(self):
        report = scoring.score_rows([row(episode='answer'), row(episode='abstain', status='ABSTAIN'),
                                     row(episode='unproduced', status='UNPRODUCED')])
        summary = report['aggregate']['all']
        self.assertEqual((summary['planned_points'], summary['produced_forecasts'], summary['supported_forecasts'],
                          summary['explicit_abstentions'], summary['unproduced_forecasts']), (3, 2, 1, 1, 1))
        self.assertEqual((summary['accuracy'], summary['support_coverage'], summary['production_coverage']),
                         (1 / 3, 1 / 3, 2 / 3))
        self.assertIsNone(summary['mean_nll']); self.assertIsNone(summary['mean_brier'])
        self.assertEqual((summary['conditional_mean_nll'], summary['conditional_mean_brier']), (0., 0.))
        self.assertEqual((summary['unchanged_bits_planned'], summary['unchanged_bits_answered']), (9, 3))
        self.assertEqual(report['aggregate']['trajectories']['exact'], 1)
        empty = report['aggregate']['ambiguous']
        self.assertIsNone(empty['accuracy']); self.assertIsNone(empty['ece_10_conditional_on_support'])
        for point in report['points']:
            if point['status'] != 'ANSWERED':
                self.assertIsNone(point['log_probabilities']); self.assertIsNone(point['nll'])

    def test_valid_prefix_and_offending_forecast_survive_an_unproduced_tail(self):
        report = scoring.score_rows([row(step=0), wrong(step=1), row(step=2, status='UNPRODUCED')])
        summary = report['aggregate']['all']
        self.assertEqual((summary['planned_points'], summary['supported_forecasts'], summary['correct']), (3, 2, 1))
        self.assertIsNone(summary['mean_nll'])
        self.assertEqual(summary['conditional_mean_nll'], 'positive_infinity')
        self.assertEqual(summary['infinite_nll_count'], 1)
        self.assertEqual(report['aggregate']['trajectories']['exact'], 0)

    def test_whole_trajectory_exactness_is_and_not_final_step_or_mean_event_accuracy(self):
        records = []
        for participant, correctness in (('distributed', ((True, False), (False, True))),
                                          ('concentrated', ((True, True), (False, False)))):
            for episode, outcomes in enumerate(correctness):
                records.extend((row if correct else wrong)(episode=f'e-{episode}', step=step, participant=participant)
                               for step, correct in enumerate(outcomes))
        results = scoring.score_rows(records)['participants']
        a, b = [results[name]['aggregate'] for name in ('distributed', 'concentrated')]
        self.assertEqual((a['all']['accuracy'], b['all']['accuracy']), (.5, .5))
        self.assertEqual((a['trajectories']['exact_rate'], b['trajectories']['exact_rate']), (0., .5))
        self.assertNotIn('trajectory_nll', a)

    def test_explicit_role_pairs_require_both_entire_trajectories_and_ignore_row_order(self):
        records = []
        for pair, names in (('p1', ('z', 'a')), ('p2', ('q', 'b'))):
            for direction, episode in enumerate(names):
                for step in range(2):
                    create = wrong if pair == 'p1' and direction == 1 and step == 0 else row
                    status = 'ABSTAIN' if pair == 'p2' and direction == 1 and step == 0 else 'ANSWERED'
                    records.append(create(episode=episode, step=step, pair_id=pair, direction=direction, status=status))
        original = scoring.score_rows(records)
        shuffled = scoring.score_rows(records[::-1])
        self.assertEqual(original, shuffled)
        pairs = original['aggregate']['role_pairs']
        self.assertEqual((pairs['planned'], pairs['fully_supported'], pairs['exact']), (2, 1, 0))
        self.assertEqual(pairs['records'][0]['episodes'], {'0': 'z', '1': 'a'})
        self.assertEqual(original['aggregate']['all']['accuracy'], .75)

    def test_exact_ties_and_ece_bins_use_joint_map_confidence(self):
        records = [row(4, episode=f'c-{i}', probabilities=[p] + [(1 - p) / 15] * 15)
                   for i, p in enumerate((.1, .9, 1.))]
        summary = scoring.score_rows(records)['aggregate']['all']
        self.assertEqual(summary['ece_bins'][1]['count'], 1)
        self.assertEqual(summary['ece_bins'][9]['count'], 2)
        self.assertEqual(sum(b['count'] for b in summary['ece_bins']), 3)
        self.assertAlmostEqual(summary['ece_10_conditional_on_support'], 1 / 3)
        point = scoring.score_rows([row(probabilities=[.5, .5] + [0.] * 6, truth=1)])['points'][0]
        self.assertEqual(point['maximizers'], [0, 1])
        self.assertEqual(point['map_world'], 0)
        self.assertFalse(point['correct'])

    def test_unchanged_bit_errors_use_physical_coordinates_and_report_unanswered_opportunities(self):
        prediction = [0.] * 64; prediction[2] = 1.
        report = scoring.score_rows([row(6, episode='wrong', truth=1, previous=0, probabilities=prediction),
                                     row(6, episode='missing', truth=1, previous=0, status='ABSTAIN')])
        summary = report['aggregate']['all']
        self.assertEqual((summary['unchanged_bit_errors'], summary['unchanged_bits_planned'],
                          summary['unchanged_bits_answered']), (1, 10, 5))

    def test_seed_family_strata_preserve_worst_seed_and_do_not_drop_unavailable_seed_scores(self):
        records = [row(episode=family, family=family, seed=seed,
                       status='UNPRODUCED' if seed == 11 and family == 'hard' else 'ANSWERED')
                   for seed in (7, 11) for family in ('easy', 'hard')]
        report = scoring.score_rows(records)
        arm = report['participants']['reference']
        seeds = arm['seed_summary']
        self.assertEqual((seeds['metrics']['accuracy']['mean'], seeds['metrics']['accuracy']['worst']), (.75, .5))
        self.assertIsNone(seeds['metrics']['mean_nll']['mean'])
        self.assertEqual(seeds['metrics']['mean_nll']['unavailable_seeds'], ['11'])
        self.assertFalse(seeds['independent_physical_samples'])
        self.assertEqual(arm['by_seed']['11']['by_family']['hard']['all']['accuracy'], 0.)
        self.assertEqual(arm['by_seed']['11']['by_family']['hard']['trajectories']['exact'], 0)
        self.assertEqual(arm['aggregate']['all']['physical_lineages'], 1)
        target = arm['original_in_family_target']
        self.assertEqual((target['by_seed']['7']['at_least_target'], target['by_seed']['11']['at_least_target']), (True, False))
        self.assertFalse(target['admission_decision'])
        self.assertEqual(report['gate_g1'], 'NOT_ADMITTED')

    def test_entity_action_partition_subsets_and_nearest_rank_forecast_costs(self):
        records = []
        for step in range(20):
            item = row(6, step=step, possible=[0, 1], family='wide', partition='held_out')
            item.update(action_kind='observe', wall_seconds=float(step), cpu_seconds=float(2 * step))
            records.append(item)
        records.append(row(3, episode='narrow', family='narrow'))
        arm = scoring.score_rows(records)['participants']['reference']
        wide = arm['by_entity_count']['6']['all']
        self.assertEqual((wide['wall_seconds_p50'], wide['wall_seconds_p95'], wide['cpu_seconds_p95']), (9., 18., 36.))
        self.assertEqual(arm['by_action']['observe']['ambiguous']['planned_points'], 20)
        self.assertEqual(arm['by_partition']['held_out']['all']['planned_points'], 20)
        self.assertEqual(arm['by_partition']['in_family']['answerable']['planned_points'], 1)

    def test_reference_comparison_keeps_exact_regression_and_recovery_identifiers(self):
        records = []
        for index in range(6):
            ref_status = 'ABSTAIN' if index == 4 else 'UNPRODUCED' if index == 5 else 'ANSWERED'
            candidate_status = 'ABSTAIN' if index == 1 else 'UNPRODUCED' if index == 2 else 'ANSWERED'
            records.append((wrong if index == 3 else row)(episode=f'c{index}', status=ref_status))
            records.append((wrong if index == 0 else row)(episode=f'c{index}', participant='candidate', status=candidate_status))
        points = scoring.score_rows(records)['points']
        comparison = scoring._comparisons(points, 'reference')['candidate']
        for field, expected in (('correct_to_wrong', ['c0']), ('correct_to_abstain', ['c1']),
                                ('correct_to_unproduced', ['c2']), ('newly_correct', ['c3', 'c4', 'c5'])):
            self.assertEqual([r['episode'] for r in comparison[field]], expected)
        self.assertEqual((comparison['reference_correct'], comparison['candidate_correct']), (3, 3))
        self.assertEqual(comparison['common_support_coverage'], 2 / 6)
        self.assertFalse(comparison['significance_claim'])

    def test_invalid_distributions_and_duplicate_points_do_not_receive_scores(self):
        for bad in (row(logs=[0.] * 8), row(logs=[-math.inf] * 8), row(logs=[math.nan] * 8),
                    row(logs=[0.] * 7), row(status='ABSTAIN', logs=[0.] * 8)):
            with self.subTest(bad=bad['status']), self.assertRaises(ValueError): scoring.score_rows([bad])
        with self.assertRaises(ValueError): scoring.score_rows([row(), row()])
        with self.assertRaises(ValueError): scoring.score_rows([])

    def test_validated_missing_trial_retains_all_planned_rows_and_source_identity(self):
        from experiments.predictive_nucleus.tests.test_acceptance_contract import make_bundle
        plan, inputs, oracle = make_bundle(entities=6)
        before = deepcopy((plan, inputs, oracle))
        report = scoring.evaluate(plan, inputs, oracle, [])
        self.assertEqual(report['aggregate']['all']['unproduced_forecasts'], 4)
        self.assertEqual(report['aggregate']['role_pairs']['planned'], 1)
        self.assertEqual(report['aggregate']['role_pairs']['exact'], 0)
        self.assertTrue(report['metadata']['incomplete_inventory'])
        self.assertEqual(report['metadata']['source_sha256']['acceptance_scoring.py'],
                         sha256(Path(scoring.__file__).read_bytes()).hexdigest())
        self.assertEqual(report['comparisons'], {})
        self.assertEqual(report['gate_g1'], 'NOT_ADMITTED')
        self.assertEqual((plan, inputs, oracle), before)
        json.dumps(report, allow_nan=False)

    def test_cli_hashes_all_artifacts_and_never_overwrites_output_or_accepts_unpaired_trace_hashes(self):
        from experiments.predictive_nucleus import acceptance_contract as contract
        from experiments.predictive_nucleus.tests.test_acceptance_contract import make_bundle
        with tempfile.TemporaryDirectory() as folder:
            args = []
            for name, value in zip(('plan', 'inputs', 'oracle'), make_bundle(), strict=True):
                path = Path(folder) / f'{name}.json'
                digest = contract.write_json(path, value)
                args += ['--' + name, str(path), '--' + name + '-sha256', digest]
            output = Path(folder) / 'report.json'
            stdout = io.StringIO()
            with redirect_stdout(stdout): self.assertEqual(scoring.main(args + ['--output', str(output)]), 0)
            original = output.read_bytes()
            self.assertEqual(json.loads(stdout.getvalue())['report_sha256'], sha256(original).hexdigest())
            self.assertEqual(json.loads(original)['gate_g1'], 'NOT_ADMITTED')
            with self.assertRaises(FileExistsError): scoring.main(args + ['--output', str(output)])
            self.assertEqual(output.read_bytes(), original)
            with self.assertRaisesRegex(ValueError, 'trace'):
                scoring.main(args + ['--output', str(Path(folder) / 'bad.json'), '--trace', 'unpaired.json'])


if __name__ == '__main__':
    unittest.main()
