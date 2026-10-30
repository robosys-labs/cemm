"""Hand-computed fixed-query and cluster-weighting invariants; no model runs."""
from copy import deepcopy
import json
import math
import unittest

from experiments.predictive_nucleus import acceptance_scoring as scoring
from experiments.predictive_nucleus.continuation_summary import summarize
from experiments.predictive_nucleus.tests.test_acceptance_scoring import row


def pair(name, family='two_contacts', *, n=3, contacts=2, correct=True, seed=7):
    cases, rows = [], []
    for direction in (0, 1):
        episode = f'{name}-{direction}'
        c = {'episode': episode, 'family': family,
             'partition': 'in_family' if family == 'two_contacts' else 'held_out',
             'lineage': name, 'pair_id': name, 'direction': direction, 'entities': n,
             'contact_count': contacts, 'query_scope': 'continuation',
             'query_steps': list(range(2, contacts + 1)), 'acquisition_step': 1}
        cases.append(c)
        for step in range(contacts + 2):
            p = row(n, episode=episode, family=family, partition=c['partition'], step=step,
                    seed=seed, pair_id=name, direction=direction,
                    truth=1 if step == 1 or (step in c['query_steps'] and not correct) else 0,
                    previous=1 if step in c['query_steps'] and not correct else 0,
                    probabilities=[.5, .5] + [0.] * (2 ** n - 2) if step == 1 else None,
                    possible=[0, 1] if step == 1 else None)
            p['lineage'] = name
            p['action_kind'] = 'set' if step == 0 else 'observe' if step == contacts + 1 else 'contact'
            rows.append(p)
    return cases, rows


def points(rows):
    return scoring.score_rows(rows)['points']


class ContinuationSummaryTests(unittest.TestCase):
    def test_fixed_original_query_indices_exclude_acquisition_without_relabeling_whole_trajectory(self):
        cases, rows = pair('p')
        for name, scope, queries, acquisition in [('single', 'acquisition_only', [], 0),
                                                 ('self', 'self_contact', [0], None)]:
            family = 'single_contact' if name == 'single' else 'self_contact'
            cases.append({'episode': name, 'family': family, 'partition': 'held_out', 'lineage': name,
                'pair_id': None, 'direction': None, 'entities': 3, 'contact_count': 1,
                'query_scope': scope, 'query_steps': queries, 'acquisition_step': acquisition})
            r = row(episode=name, family=family, partition='held_out'); r['lineage'] = name; rows.append(r)
        report = scoring.score_rows(rows); original = deepcopy(report)
        result = summarize(report['points'], cases, [7])['by_arm']['reference']['by_seed']['7']
        self.assertEqual(result['in_family_continuation']['planned_points'], 2)
        self.assertEqual(result['in_family_continuation']['accuracy'], 1.)
        self.assertEqual(result['query_role_pairs']['exact_rate'], 1.)
        self.assertEqual(result['query_role_pairs']['records'][0]['query_steps'], [2])
        self.assertEqual(result['self_contact']['planned_points'], 1)
        self.assertEqual(result['by_family']['single_contact']['planned_points'], 0)
        self.assertIsNone(result['by_family']['single_contact']['accuracy'])
        self.assertEqual(result['zero_query_episodes'], ['single'])
        self.assertEqual(report['aggregate']['role_pairs']['exact_rate'], 0.)
        self.assertAlmostEqual(result['acquisition_ambiguous']['mean_nll'], math.log(2))
        self.assertEqual(report, original)

    def test_missing_outputs_stay_in_query_and_pair_denominators(self):
        cases, rows = pair('missing', contacts=3)
        for r in rows:
            if r['step'] == 2:
                r['status'] = 'ABSTAIN' if r['direction'] == 0 else 'UNPRODUCED'
                r['log_probabilities'] = None
        result = summarize(points(rows), cases)['by_arm']['reference']['by_seed']['7']
        m = result['continuation']
        self.assertEqual((m['planned_points'], m['correct'], m['explicit_abstentions'], m['unproduced_forecasts']),
                         (4, 2, 1, 1))
        self.assertEqual((m['accuracy'], m['support_coverage']), (.5, .5))
        self.assertIsNone(m['mean_nll'])
        self.assertEqual(result['query_role_pairs']['exact_rate'], 0.)
        self.assertEqual(result['per_lineage'][0]['accuracy'], .5)

    def test_macro_averages_physical_draws_cells_then_families_instead_of_pooling_queries(self):
        cases, rows = [], []
        for name, family, n, k, correct in [('a', 'chain', 4, 3, True),
                ('b', 'chain', 5, 4, False), ('c', 'chain', 5, 4, False), ('d', 'cycle', 3, 3, True)]:
            c, r = pair(name, family, n=n, contacts=k, correct=correct); cases += c; rows += r
        result = summarize(points(rows), cases)['by_arm']['reference']['by_seed']['7']
        self.assertEqual(result['ood_family_accuracy'], {'chain': .5, 'cycle': 1.})
        self.assertEqual(result['ood_macro_accuracy'], .75)
        self.assertEqual(result['ood_continuation']['accuracy'], .4)
        self.assertEqual(len(result['per_lineage']), 4)

    def test_incomplete_or_changed_query_inventory_is_rejected(self):
        cases, rows = pair('p'); scored = points(rows)
        for bad in [[p for p in scored if p['episode'] != 'p-1'],
                    [p for p in scored if not (p['episode'] == 'p-0' and p['step'] == 2)]]:
            with self.assertRaises(ValueError): summarize(bad, cases)
        with self.assertRaises(ValueError): summarize(scored, cases, [7, 11])
        bad = deepcopy(cases); bad[0]['query_steps'] = [2, 2]
        with self.assertRaises(ValueError): summarize(scored, bad)
        bad = deepcopy(cases); bad[0]['lineage'] = 'another'
        with self.assertRaises(ValueError): summarize(scored, bad)

    def test_infinite_losses_and_seed_failure_records_remain_strict_json_and_order_independent(self):
        cases, rows = pair('p', correct=False)
        _, second = pair('p', seed=11)
        scored = points(rows + second)
        before = deepcopy(scored)
        a = summarize(scored, cases, [7, 11], {'reference': {'7': 'COMPLETED', '11': 'STOPPED'}})
        b = summarize(scored[::-1], cases[::-1], [11, 7], a['fit_status'])
        self.assertEqual(a, b)
        self.assertEqual(a['by_arm']['reference']['by_seed']['7']['continuation']['mean_nll'], 'positive_infinity')
        self.assertGreater(a['by_arm']['reference']['by_seed']['7']['continuation']['unchanged_bit_errors'], 0)
        self.assertEqual(a['fit_status']['reference']['11'], 'STOPPED')
        self.assertEqual(scored, before)
        json.dumps(a, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
