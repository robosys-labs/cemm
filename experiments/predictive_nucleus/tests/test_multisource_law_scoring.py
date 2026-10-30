"""Synthetic law-swap arithmetic; no learned checkpoints or model execution."""
from copy import deepcopy
import math
import unittest

from experiments.predictive_nucleus import acceptance_scoring as base
from experiments.predictive_nucleus import mixed_composition_run as mixed
from experiments.predictive_nucleus import multisource_law_scoring as scoring
from experiments.predictive_nucleus.tests.test_acceptance_scoring import row


LIMITS = {'contexts': 2, 'min_matched_probability': .9, 'max_wrong_law_probability': .1,
          'min_gap': .8, 'min_mean_nll_gain': .1, 'probability_tolerance': 1e-12}


def fixture(probability=1., tail=0.):
    contexts, points = [], {'nand': [], 'nor': []}
    for mode, worlds in enumerate(((3, 2), (6, 4))):
        context = {'episode': f'mode-{mode}', 'step': 1, 'nand_world': worlds[0],
                   'nor_world': worlds[1], 'information_key': str(mode) * 64}
        contexts.append(context)
        for law, truth in zip(points, worlds):
            for arm in ('matched', 'crossed'):
                target = truth if arm == 'matched' else next(w for w in worlds if w != truth)
                probabilities = [0.] * 8
                probabilities[target], probabilities[next(w for w in worlds if w != target)] = probability, 1. - probability - tail
                probabilities[7] = tail
                p = base._point(row(episode=context['episode'], step=1, participant=arm,
                    truth=truth, probabilities=probabilities))
                p['information_key'] = context['information_key']
                p.update(mixed.information_scores(p, {**context, 'possible_worlds': [truth],
                    'probabilities': [1.]}, [truth]))
                points[law].append(p)
    return points, contexts


class MultisourceLawScoringTests(unittest.TestCase):
    def test_opposite_worlds_both_modes_and_infinite_crossed_loss_pass(self):
        points, contexts = fixture()
        result = scoring.compare_laws(points, contexts, [7], LIMITS)
        self.assertTrue(result['passed'])
        self.assertEqual(len(result['rows']), 2)
        for law in points:
            self.assertEqual(result['means']['7'][law], {'matched': 0., 'crossed': 'positive_infinity',
                'gain': 'positive_infinity', 'answered': {'matched': 2, 'crossed': 2}})

    def test_threshold_boundary_passes_and_identical_forecasts_fail(self):
        for probability, passed in ((.9, True), (.5, False)):
            points, contexts = fixture(probability)
            self.assertEqual(scoring.compare_laws(points, contexts, [7], LIMITS)['passed'], passed)

    def test_missing_and_abstaining_keep_all_planned_contexts(self):
        for status in (None, 'ABSTAIN', 'UNPRODUCED'):
            points, contexts = fixture()
            if status is None: points['nand'].pop(0)
            else: points['nand'][0].update(status=status, log_probabilities=None)
            result = scoring.compare_laws(points, contexts, [7], LIMITS)
            self.assertFalse(result['passed'])
            self.assertEqual((result['planned_contexts_per_seed'], len(result['rows'])), (2, 2))
            self.assertIsNone(result['means']['7']['nand']['matched'])

    def test_outside_mass_is_not_conditioned_away_and_log_underflow_is_preserved(self):
        points, contexts = fixture(.85, .1)
        result = scoring.compare_laws(points, contexts, [7], LIMITS)
        self.assertFalse(result['passed'])
        self.assertAlmostEqual(result['rows'][0]['nand_probability'], .85)
        points, contexts = fixture()
        for law in points:
            for p in points[law]:
                p['log_probabilities'] = [-1000. if v == -math.inf else v for v in p['log_probabilities']]
        result = scoring.compare_laws(points, contexts, [7], LIMITS)
        self.assertTrue(result['passed'])
        self.assertEqual(result['means']['7']['nand']['crossed'], 1000.)

    def test_full_vector_checkpoint_binding_and_information_alignment_are_required(self):
        for corruption in ('vector', 'information_key', 'possible_worlds', 'ids'):
            points, contexts = fixture(.9)
            p = points['nand'][1]  # Crossed NAND must equal matched NOR on this same history.
            if corruption == 'vector':
                p['log_probabilities'][0], p['log_probabilities'][3] = math.log(.1), -math.inf
            elif corruption == 'information_key': p[corruption] = 'f' * 64
            elif corruption == 'possible_worlds': p[corruption] = [2]
            else: p[corruption] = list(reversed(p[corruption]))
            with self.assertRaises(ValueError): scoring.compare_laws(points, contexts, [7], LIMITS)

    def test_zero_matched_mass_fails_without_nan(self):
        points, contexts = fixture(0.)
        result = scoring.compare_laws(points, contexts, [7], LIMITS)
        self.assertFalse(result['passed'])
        self.assertIsNone(result['means']['7']['nand']['gain'])

    def test_primary_subset_flow_gates_and_paired_ids(self):
        points, _ = fixture()
        primary = deepcopy(points['nand'])
        cases = [{'episode': f'mode-{mode}', 'family': 'family', 'flow': flow, 'query_steps': [2]}
                 for mode, flow in enumerate(('fan_in', 'fan_out'))]
        for p in primary: p['step'] = 2
        result = scoring.summarize_composition(points['nand'] + primary, cases, [7], {'identifiable_accuracy': .95})
        self.assertTrue(result['passed'])
        self.assertEqual(result['by_arm']['matched']['7']['all']['planned_points'], 2)
        self.assertEqual(result['changes']['7']['repairs'], [['mode-0', 2], ['mode-1', 2]])
        regressed = deepcopy(primary)
        for p in regressed:
            if p['episode'] == 'mode-1': p['participant'] = 'crossed' if p['participant'] == 'matched' else 'matched'
        result = scoring.summarize_composition(regressed, cases, [7], {'identifiable_accuracy': .95})
        self.assertFalse(result['passed'])
        self.assertEqual(result['changes']['7']['regressions'], [['mode-1', 2]])
        self.assertTrue(result['checks']['7']['family/fan_in']['accuracy'])
        self.assertFalse(result['checks']['7']['family/fan_out']['accuracy'])
        primary.pop(0)
        result = scoring.summarize_composition(primary, cases, [7], {'identifiable_accuracy': .95})
        self.assertFalse(result['passed'])
        metrics = result['by_arm']['matched']['7']['all']
        self.assertEqual((metrics['planned_points'], metrics['accuracy'], metrics['support_coverage']), (2, .5, .5))
        self.assertIsNone(metrics['mean_nll'])


if __name__ == '__main__': unittest.main()
