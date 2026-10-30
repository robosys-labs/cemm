"""Hand-computed joint-distribution decisions; no fitted model or study replay."""
from copy import deepcopy
import math
import unittest

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import acceptance_scoring as scoring
from experiments.predictive_nucleus import mixed_composition_run as run
from experiments.predictive_nucleus.tests.test_acceptance_scoring import bits, row


def synthetic():
    """One role pair: ambiguous contact, visible feedback, identifiable observe."""
    cases, information, rows = [], [], []
    for direction, truth in enumerate((2, 1)):
        case = {'episode': f'hand-{direction}', 'ids': list('abc'),
            'actions': [{'kind': 'contact', 'participants': list('bc' if direction == 0 else 'cb')},
                        {'kind': 'observe', 'participants': []}],
            'observations': [dict(zip('abc', bits(w, 3))) for w in (3, truth, truth)],
            'coverage': [list('abc'), list('abc')]}
        forecasts = []
        for step, possible in enumerate(([1, 2], [truth])):
            probabilities = [float(w in possible) / len(possible) for w in range(8)]
            expected = {'information_key': contract.information_key(case, step),
                'possible_worlds': possible, 'probabilities': [1. / len(possible)] * len(possible)}
            forecasts.append(expected)
            for arm in run.ARMS:
                point = row(episode=case['episode'], step=step, participant=arm, seed=99,
                    truth=truth, previous=3 if step == 0 else truth, probabilities=probabilities,
                    possible=possible, pair_id='hand-pair', direction=direction)
                point['information_key'] = expected['information_key']; rows.append(point)
        cases.append(case); information.append({'episode': case['episode'], 'forecasts': forecasts})
    assets = {'inputs': {'episodes': cases}, 'information': {'episodes': information}}
    config = {'version': 'hand-arithmetic', 'model_seeds': [99], 'analysis': {
        'identifiable_accuracy': .95, 'mean_oracle_kl': .05, 'max_ambiguous_total_variation': .1}}
    return rows, assets, config


def analyze(rows, assets, config, incomplete=()):
    report = scoring.score_rows(rows)
    report['metadata'] = {'incomplete_inventory': list(incomplete), 'failure_records': []}
    return run.analyze(report, assets, config)


class MixedCompositionRunTests(unittest.TestCase):
    def test_ideal_uncertainty_passes_despite_wrong_realized_map(self):
        rows, assets, config = synthetic()
        result = analyze(rows, assets, config)
        self.assertEqual(result['decision']['decision'], 'KEEP_MIXED_COMPOSITION')
        metrics = result['by_arm']['alias']['99']
        self.assertEqual((metrics['all']['accuracy'], metrics['ambiguous']['accuracy']), (.75, .5))
        self.assertEqual(metrics['identifiable']['accuracy'], 1.)
        self.assertAlmostEqual(metrics['ambiguous']['mean_oracle_kl'], 0.)
        self.assertEqual(result['decision']['gate_g1'], 'NOT_ADMITTED')

    def test_same_marginals_wrong_joint_correlation_fails(self):
        rows, assets, config = synthetic()
        ideal, wrong = [0., .5, .5, 0.] + [0.] * 4, [.24, .26, .26, .24] + [0.] * 4
        for bit in range(3):
            self.assertEqual(sum(p for w, p in enumerate(ideal) if bits(w, 3)[bit]),
                             sum(p for w, p in enumerate(wrong) if bits(w, 3)[bit]))
        for p in rows:
            if p['participant'] == 'alias' and p['step'] == 0:
                p['log_probabilities'] = [math.log(v) if v else -math.inf for v in wrong]
        result = analyze(rows, assets, config)
        checks = result['decision']['checks']['99']
        self.assertTrue(checks['supported_MAP_worlds'])
        self.assertFalse(checks['joint_probability_quality'])
        self.assertFalse(checks['ambiguous_no_collapse'])
        self.assertEqual(result['decision']['decision'], 'REVISE_MIXED_COMPOSITION')

    def test_realized_unchanged_is_distinct_from_known_unchanged(self):
        rows, assets, _ = synthetic()
        p = scoring._point(rows[0]); expected = assets['information']['episodes'][0]['forecasts'][0]
        self.assertEqual(p['unchanged_bit_errors'], 1)
        result = run.information_scores(p, expected, [3])
        self.assertEqual((result['known_unchanged_bits'], result['known_unchanged_errors']), (1, 0))
        changed = deepcopy(rows[0]); changed['log_probabilities'] = [-math.inf] * 8
        changed['log_probabilities'][2], changed['log_probabilities'][6] = math.log(.1), math.log(.9)
        result = run.information_scores(scoring._point(changed), expected, [3])
        self.assertEqual(result['known_unchanged_errors'], 1)
        self.assertTrue(result['map_outside_support'])

    def test_newly_known_bit_is_not_counted_as_preserved(self):
        p = scoring._point(row())
        expected = {'information_key': p['information_key'], 'possible_worlds': [0], 'probabilities': [1.]}
        self.assertEqual(run.information_scores(p, expected, [0, 1])['known_unchanged_bits'], 2)
        expected['information_key'] = '1' * 64
        with self.assertRaisesRegex(ValueError, 'information alignment'):
            run.information_scores(p, expected, [0])

    def test_missing_forecasts_keep_denominator_and_no_fabricated_probability(self):
        for status in ('ABSTAIN', 'UNPRODUCED'):
            rows, assets, config = synthetic()
            p = next(p for p in rows if p['participant'] == 'alias' and p['step'] == 1)
            p.update(status=status, log_probabilities=None)
            incomplete = ['hand-0/1'] if status == 'UNPRODUCED' else []
            result = analyze(rows, assets, config, incomplete)
            metrics = result['by_arm']['alias']['99']['identifiable']
            self.assertEqual((metrics['planned_points'], metrics['correct']), (2, 1))
            self.assertIsNone(metrics['mean_oracle_kl'])
            self.assertFalse(result['decision']['checks']['99']['complete_support'])
            self.assertEqual(result['decision']['decision'],
                'STOP_INCOMPLETE_EXECUTION' if incomplete else 'REVISE_MIXED_COMPOSITION')

    def test_zero_truth_mass_is_retained_as_infinite_loss_and_fails_without_crash(self):
        rows, assets, config = synthetic()
        p = next(p for p in rows if p['participant'] == 'alias' and p['step'] == 0 and p['truth'] == [0, 1, 0])
        p['log_probabilities'] = [-math.inf, 0.] + [-math.inf] * 6
        result = analyze(rows, assets, config)
        self.assertEqual(result['decision']['decision'], 'REVISE_MIXED_COMPOSITION')
        metrics = result['by_arm']['alias']['99']['ambiguous']
        self.assertEqual((metrics['mean_nll'], metrics['mean_oracle_kl']), ('positive_infinity', 'positive_infinity'))


if __name__ == '__main__': unittest.main()
