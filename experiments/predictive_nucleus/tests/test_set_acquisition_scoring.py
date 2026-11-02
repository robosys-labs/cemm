"""Fabricated score invariants, never a fitted model or the scientific bank."""
from copy import deepcopy
import json
import math
import subprocess
import sys
import unittest

from experiments.predictive_nucleus import acceptance_contract as c
from experiments.predictive_nucleus.set_acquisition_scoring import analyze_native

LIMITS = {'identifiable_accuracy': .95, 'mean_oracle_kl': .05,
          'max_ambiguous_total_variation': .1, 'max_set_mean_nll': .05,
          'min_changed_set_nll_gain': .1}


def fixture():
    ids = ['a', 'b', 'c']; cases, observed, gold, information = [], [], [], []
    traces = {arm: [] for arm in ('parent', 'acquired', 'no_change')}
    bits = lambda code: dict(zip(ids, [(code >> i) & 1 for i in (2, 1, 0)]))
    set_a = {'kind': 'set', 'participants': ['a'], 'value': 1}
    set_c = {'kind': 'set', 'participants': ['c'], 'value': 1}
    designs = [('change', [0, 4], [set_a], [[4]], None),
               ('retain', [4, 4], [set_a], [[4]], None),
               ('left', [0, 2, 3], [{'kind': 'contact', 'participants': ['a', 'b']}, set_c], [[2, 4], [3]], 0),
               ('right', [0, 4, 5], [{'kind': 'contact', 'participants': ['b', 'a']}, set_c], [[2, 4], [5]], 1)]
    for identity, worlds, actions, supports, direction in designs:
        readings = [bits(world) for world in worlds]
        record = {'episode': identity, 'ids': ids, 'observations': readings,
                  'actions': actions, 'coverage': [ids.copy() for _ in actions]}
        observed.append(record); keys = [c.information_key(record, t) for t in range(len(actions))]
        cases.append({'episode': identity, 'family': 'set' if direction is None else 'bridge',
            'partition': 'held_out', 'lineage': identity if direction is None else 'pair-lineage',
            'pair_id': None if direction is None else 'pair', 'direction': direction,
            'entities': 3, 'hidden_source_slot': None if direction is None else 0, 'requested': 1,
            'set_points': [{'step': t, 'prior': readings[t][a['participants'][0]], 'requested': 1,
                'changed': readings[t][a['participants'][0]] != 1} for t, a in enumerate(actions) if a['kind'] == 'set']})
        gold.append({'episode': identity, 'truth': readings, 'possible_worlds': supports, 'information_keys': keys})
        information.append({'episode': identity, 'forecasts': [{'information_key': keys[t],
            'possible_worlds': support, 'probabilities': [1 / len(support)] * len(support),
            'surviving_modes': [0, 1] if t == 0 else [0]} for t, support in enumerate(supports)]})
        for t, support in enumerate(supports):
            distributions = {'parent': [1 / 8] * 8,
                'acquired': [1 / len(support) if w in support else 0. for w in range(8)],
                'no_change': [float(w == worlds[t]) for w in range(8)]}
            for arm, probabilities in distributions.items():
                traces[arm].append({'id': identity, 'step': t,
                    'logp': [math.log(p) if p else 'negative_infinity' for p in probabilities]})
    inputs = {'version': 'active-acceptance-input-v1', 'episodes': observed}
    hashes = {'input_sha256': c.digest(inputs), 'source_sha256': 'a' * 64, 'information_law_sha256': 'b' * 64}
    return {'inputs': inputs, 'cases': cases, 'oracle': {'version': 'active-acceptance-oracle-v1', **hashes, 'episodes': gold},
        'information': {'version': 'set-acquisition-v1-information', **hashes, 'episodes': information}}, traces


class SetAcquisitionScoringTests(unittest.TestCase):
    def test_ambiguous_actual_errors_do_not_become_identifiable_failures(self):
        bundle, traces = fixture(); original = deepcopy((bundle, traces))
        result = analyze_native(bundle, traces, LIMITS)
        self.assertTrue(result['passed']); self.assertTrue(all(result['checks'].values()))
        score = result['reports']['acquired']
        self.assertEqual((score['all']['correct'], score['all']['planned_points']), (5, 6))
        self.assertEqual((score['identifiable']['correct'], score['ambiguous']['correct']), (4, 1))
        self.assertEqual(score['ambiguous']['mean_oracle_kl'], 0.)
        self.assertEqual(score['role_pairs']['correct'], 0)
        self.assertEqual(score['role_pairs']['identifiable_correct'], 1)
        self.assertEqual(result['reports']['no_change']['all']['mean_nll'], 'positive_infinity')
        self.assertEqual(result['comparisons']['no_change']['changed_set_nll_gain'], 'positive_infinity')
        json.dumps(result, allow_nan=False)
        self.assertEqual((bundle, traces), original)

    def test_spectator_regression_and_probability_worsening_are_retained(self):
        bundle, traces = fixture()
        for arm, world in (('parent', 4), ('acquired', 5)):
            row = next(p for p in traces[arm] if p['id'] == 'retain')
            row['logp'] = [0. if w == world else 'negative_infinity' for w in range(8)]
        result = analyze_native(bundle, traces, LIMITS)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['known_unchanged_preserved'])
        self.assertFalse(result['checks']['parent_identifiable_retention'])
        changes = result['comparisons']['parent']
        self.assertIn(['retain', 0], changes['identifiable_regressions'])
        self.assertIn(['retain', 0, 'positive_infinity'], changes['nll_worse'])
        self.assertEqual(next(p for p in changes['probability_changes'] if p['id'] == 'retain')['total_variation'], 1.)

    def test_missing_duplicate_and_nonprobability_forecasts_fail_closed(self):
        for defect in ('missing', 'duplicate', 'nan', 'mass', 'extra'):
            with self.subTest(defect=defect):
                bundle, traces = fixture(); rows = traces['acquired']
                if defect == 'missing': rows.pop()
                elif defect == 'duplicate': rows.append(deepcopy(rows[0]))
                elif defect == 'nan': rows[0]['logp'][0] = math.nan
                elif defect == 'mass': rows[0]['logp'] = [0.] * 8
                else: rows[0]['gold'] = 4
                with self.assertRaises(ValueError): analyze_native(bundle, traces, LIMITS)

    def test_oracle_information_stratum_and_pair_mismatches_fail_closed(self):
        for defect in ('truth', 'probabilities', 'key', 'set_prior', 'pair'):
            with self.subTest(defect=defect):
                bundle, traces = fixture()
                if defect == 'truth': bundle['oracle']['episodes'][0]['truth'][-1]['b'] = 1
                elif defect == 'probabilities': bundle['information']['episodes'][2]['forecasts'][0]['probabilities'] = [.75, .25]
                elif defect == 'key': bundle['information']['episodes'][0]['forecasts'][0]['information_key'] = 'c' * 64
                elif defect == 'set_prior': bundle['cases'][0]['set_points'][0]['prior'] = 1
                else: bundle['cases'][3]['direction'] = 0
                with self.assertRaises(ValueError): analyze_native(bundle, traces, LIMITS)

    def test_import_does_not_load_torch_or_data_generator(self):
        code = ('import sys; import experiments.predictive_nucleus.set_acquisition_scoring; '
                'assert "torch" not in sys.modules; '
                'assert "experiments.predictive_nucleus.set_acquisition_data" not in sys.modules')
        subprocess.run([sys.executable, '-c', code], check=True)


if __name__ == '__main__': unittest.main()
