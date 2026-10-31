"""Synthetic oracle forecasts and hostile omissions; no checkpoint execution."""
from copy import deepcopy
import json
import math
import unittest

from experiments.predictive_nucleus import acceptance_scoring as base
from experiments.predictive_nucleus import hidden_cycle_data as data
from experiments.predictive_nucleus import hidden_cycle_scoring as scoring


LIMITS = {'identifiable_accuracy': .95, 'mean_oracle_kl': .05,
    'max_ambiguous_total_variation': .1, 'min_critical_probability': .9,
    'max_stale_target_probability': .1, 'probability_tolerance': 1e-12}


def fixture(bundle):
    cases = {c['episode']: c for c in bundle['cases']}
    gold = {c['episode']: c for c in bundle['oracle']['episodes']}
    information = {c['episode']: c['forecasts'] for c in bundle['information']['episodes']}
    points = []
    for case in bundle['inputs']['episodes']:
        name, ids = case['episode'], sorted(case['ids'])
        meta = cases[name]
        for step, target in enumerate(information[name]):
            probabilities = dict(zip(target['possible_worlds'], target['probabilities'], strict=True))
            points.append(base._point({'participant': 'frozen', 'model_seed': 7, 'episode': name,
                'step': step, **{k: meta[k] for k in ('family', 'partition', 'lineage', 'pair_id', 'direction')},
                'ids': ids, 'truth': [gold[name]['truth'][step + 1][i] for i in ids],
                'previous_truth': [gold[name]['truth'][step][i] for i in ids],
                'possible_worlds': target['possible_worlds'], 'information_key': target['information_key'],
                'action_kind': 'contact', 'status': 'ANSWERED', 'wall_seconds': .001, 'cpu_seconds': .001,
                'log_probabilities': [math.log(probabilities[w]) if w in probabilities else -math.inf
                                     for w in range(2 ** len(ids))]}))
    return {'points': points, 'metadata': {'incomplete_inventory': [], 'failure_records': []}}


def replace(point, probabilities=None, status='ANSWERED'):
    row = {**point, 'status': status, 'log_probabilities': None if status != 'ANSWERED' else
        [math.log(p) if p else -math.inf for p in probabilities]}
    point.clear(); point.update(base._point(row))


class HiddenCycleScoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bank = data.build_assets({'version': 'hidden-cycle-synthetic-v1', 'data': {
            'entity_counts': [3], 'split_seed': 20261030063}})['banks']['nand']
        lineage = next(c['lineage'] for c in bank['cases'] if c['critical'])
        selected = {c['episode'] for c in bank['cases'] if c['lineage'] == lineage}
        cls.bank = deepcopy(bank)
        cls.bank['cases'] = [c for c in bank['cases'] if c['episode'] in selected]
        for group in ('inputs', 'oracle', 'information'):
            cls.bank[group]['episodes'] = [c for c in bank[group]['episodes'] if c['episode'] in selected]
        cls.config = {'version': 'hidden-cycle-synthetic-v1', 'model_seeds': [7], 'analysis': {
            **LIMITS, 'critical_pairs': sum(c['critical'] and c['condition'] == 'hidden' for c in cls.bank['cases'])}}

    def setUp(self):
        self.bundle = deepcopy(self.bank); self.report = fixture(self.bundle)
        self.meta = next(c for c in self.bundle['cases'] if c['critical'] and c['condition'] == 'hidden')
        self.point = next(p for p in self.report['points'] if p['episode'] == self.meta['episode'] and p['step'] == 2)

    def analyze(self):
        return scoring.analyze(self.report, self.bundle, self.config)

    def test_perfect_information_forecasts_pass_without_demanding_95_percent_all_action(self):
        result = self.analyze(); self.assertEqual(result['decision']['decision'], 'KEEP_HIDDEN_CYCLE')
        row = result['by_seed']['7']
        self.assertAlmostEqual(row['all']['accuracy'], 5 / 6)
        self.assertEqual(row['identifiable']['accuracy'], 1.)
        self.assertEqual((row['all']['planned_points'], row['identifiable_role_pairs']['planned']), (24, 4))
        self.assertEqual(result['paired']['7']['critical_passed'], self.config['analysis']['critical_pairs'])
        json.dumps(result, allow_nan=False)

    def test_missing_rows_and_entire_missing_seed_preserve_denominators(self):
        self.report['points'].remove(self.point)
        result = self.analyze()
        self.assertEqual(result['decision']['decision'], 'STOP_INCOMPLETE_EXECUTION')
        self.assertEqual(result['by_seed']['7']['all']['planned_points'], 24)
        self.assertEqual(result['by_seed']['7']['all']['supported_forecasts'], 23)
        self.assertIsNone(result['by_seed']['7']['all']['mean_nll'])
        self.assertEqual(result['by_seed']['7']['identifiable_role_pairs']['planned'], 4)
        self.assertEqual(len(result['paired']['7']['unpaired']), 1)
        config = {**self.config, 'model_seeds': [7, 11]}
        result = scoring.analyze(self.report, self.bundle, config)
        self.assertEqual(result['by_seed']['11']['all']['planned_points'], 24)
        self.assertEqual(result['by_seed']['11']['all']['support_coverage'], 0.)
        self.assertEqual(len(result['missing_records']), 25)

    def test_abstention_failure_and_unproduced_do_not_pass(self):
        for status, decision in (('ABSTAIN', 'REVISE_HIDDEN_CYCLE'), ('UNPRODUCED', 'STOP_INCOMPLETE_EXECUTION')):
            self.setUp(); replace(self.point, status=status)
            result = self.analyze()
            self.assertEqual(result['decision']['decision'], decision)
            self.assertEqual(result['paired']['7']['complete'], 3)
            self.assertIn(self.meta['twin_id'], result['paired']['7']['regressions'])
        self.setUp(); self.report['metadata']['failure_records'] = [{'phase': 'end'}]
        self.assertEqual(self.analyze()['decision']['decision'], 'STOP_INCOMPLETE_EXECUTION')

    def test_critical_mass_uses_full_vector_and_entire_stale_target_event(self):
        true = base._index(self.point['truth']); target = self.point['ids'].index(self.meta['final_target'])
        stale = [w for w in range(8) if (w >> (2 - target)) & 1 == self.meta['stale_target_bit']]
        probabilities = [0.] * 8; probabilities[true] = .8
        probabilities[stale[0]] = .09; probabilities[stale[1]] = .11
        replace(self.point, probabilities)
        result = self.analyze(); record = next(r for r in result['paired']['7']['records'] if r['twin_id'] == self.meta['twin_id'])
        self.assertAlmostEqual(record['hidden_probability'], .8)
        self.assertAlmostEqual(record['stale_target_probability'], .2)
        self.assertFalse(record['critical_passed'])
        self.assertEqual(result['decision']['decision'], 'REVISE_HIDDEN_CYCLE')
        self.assertEqual(result['paired']['7']['regressions'], [])  # MAP retained; probability gate still fails.

    def test_critical_threshold_boundary_and_zero_truth_mass(self):
        true, stale = base._index(self.point['truth']), self.meta['stale_final_world']
        probabilities = [0.] * 8; probabilities[true], probabilities[stale] = .9, .1
        replace(self.point, probabilities)
        record = next(r for r in self.analyze()['paired']['7']['records'] if r['twin_id'] == self.meta['twin_id'])
        self.assertTrue(record['critical_passed'])
        self.setUp(); probabilities = [0.] * 8; probabilities[stale] = 1.
        replace(self.point, probabilities)
        result = self.analyze()
        self.assertEqual(result['decision']['decision'], 'REVISE_HIDDEN_CYCLE')
        self.assertEqual(result['by_seed']['7']['all']['mean_nll'], 'positive_infinity')
        self.assertIn(self.meta['twin_id'], result['paired']['7']['regressions'])
        json.dumps(result, allow_nan=False)

    def test_duplicates_unknown_points_and_metadata_disagreement_rejected(self):
        for corruption in ('duplicate', 'unknown', 'ids', 'stratum', 'target', 'case_duplicate'):
            self.setUp()
            if corruption == 'duplicate': self.report['points'].append(deepcopy(self.point))
            elif corruption == 'unknown': self.point['participant'] = 'other'
            elif corruption == 'ids': self.point['ids'].reverse()
            elif corruption == 'stratum': self.point['answerable'] = False
            elif corruption == 'target': self.meta['critical'] = False
            else: self.bundle['inputs']['episodes'].append(deepcopy(self.bundle['inputs']['episodes'][0]))
            with self.subTest(corruption=corruption), self.assertRaises(ValueError): self.analyze()

    def test_future_mask_cannot_change_identical_prefix_forecasts(self):
        first = next(p for p in self.report['points'] if p['episode'] == self.meta['episode'] and p['step'] == 0)
        probabilities = [0.] * 8
        a, b = first['possible_worlds']; probabilities[a], probabilities[b] = .51, .49
        replace(first, probabilities)
        result = self.analyze()
        self.assertFalse(result['decision']['checks']['7']['prefix_forecasts_equal'])
        self.assertEqual(result['decision']['decision'], 'REVISE_HIDDEN_CYCLE')


if __name__ == '__main__': unittest.main()
