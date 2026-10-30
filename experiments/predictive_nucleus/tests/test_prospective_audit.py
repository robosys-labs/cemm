"""Analytic law checks and complete-inventory regressions, with no learned model."""
from copy import deepcopy
import json
import math
import unittest

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import prospective_audit as audit
from experiments.predictive_nucleus import prospective_data as data
from experiments.predictive_nucleus import prospective_oracle as oracle
from experiments.predictive_nucleus.world import Action, World, step


def contact(a, b):
    return {'kind': 'contact', 'participants': [a, b]}


def tape(actions, *, n=3, mode=0, anchor=None, missing=None, name='toy'):
    ids = list('abcdef'[:n])
    anchor = [1] + [0] * (n - 1) if anchor is None else anchor
    current = World(tuple(ids), tuple(anchor), mode)
    observed = [dict(zip(ids, anchor))]
    for t, action in enumerate(actions):
        current = step(current, Action(action['kind'], tuple(action['participants']), action.get('value')))
        observed.append({i: None if missing and i in missing[t] else bit for i, bit in zip(ids, current.bits)})
    return {'episode': name, 'ids': ids, 'observations': observed, 'actions': deepcopy(actions),
            'coverage': [ids.copy() for _ in actions]}


def records(case, *, actual_mode=0, paired=True):
    cases = [deepcopy(case)]
    if paired:
        other = deepcopy(case); other['episode'] += '-reverse'
        for action in other['actions']:
            if action['kind'] == 'contact': action['participants'].reverse()
        cases.append(other)
    return [{'episode': c['episode'], 'family': 'toy', 'partition': 'in_family', 'lineage': 'one-physical-draw',
             'split': 'evaluation', 'pair_id': 'pair' if paired else None, 'direction': direction if paired else None,
             'hidden_source_slot': actual_mode, 'resources': audit._resources(c, 3),
             'modes': [audit._branch(c, mode) for mode in (0, 1)]} for direction, c in enumerate(cases)]


def small_bundle(n=3):
    config = data.read_config()
    config['entity_counts'] = [n]
    config['draws_per_family_entity'] = {split: 1 for split in data.SPLITS}
    return data.build_assets(config)


def refresh(part):
    by_name = {r['episode']: r for r in part['cases']}
    gold = []
    for case in part['inputs']['episodes']:
        meta = by_name[case['episode']]
        actual, truth = audit._simulate(case, meta['hidden_source_slot'])
        case['observations'] = actual['observations']
        meta['blueprint_sha256'] = data.blueprint_digest(case)
        meta['template_sha256'] = data.template_digest(case)
        forecasts = oracle.forecast_episode(case)
        gold.append({'episode': case['episode'], 'truth': truth,
                     'possible_worlds': [p['possible_worlds'] for p in forecasts],
                     'information_keys': [p['information_key'] for p in forecasts]})
    part['oracle']['episodes'] = gold
    part['oracle']['input_sha256'] = contract.digest(part['inputs'])


class LawWeightedAuditTests(unittest.TestCase):
    def test_first_contact_balanced_law_and_reversed_pair_tie_are_exact(self):
        for n in range(3, 7):
            with self.subTest(n=n):
                rows = records(tape([contact('a', 'b')], n=n))
                result = audit._summary(rows)
                self.assertEqual(result['counts'], {'episodes': 2, 'physical_draws': 1, 'role_pairs': 1,
                    'planned_steps': 2, 'contact_steps': 2, 'answerable_steps': 0, 'ambiguous_steps': 2})
                probability = result['law_expected']['all']
                self.assertEqual(probability['bayes_map_accuracy'], .5)
                self.assertEqual(probability['frozen_lexicographic_map_accuracy'], .5)
                self.assertAlmostEqual(probability['mean_entropy_nats'], math.log(2))
                self.assertEqual(probability['mean_brier_floor'], .5)
                self.assertEqual(result['frozen_lexicographic_trajectory_exact'], .5)
                self.assertEqual(result['frozen_lexicographic_role_pair_exact'], 0.)
                self.assertFalse(result['original_in_family_target']['expected_ceiling_at_least_target'])
                self.assertFalse(result['original_in_family_target']['admission_decision'])

    def test_world_mass_is_aggregated_before_entropy_and_self_is_one_physical_output(self):
        for n in range(3, 7):
            branch = audit._branch(tape([contact('a', 'a')], n=n), 0)
            point = branch['points'][0]
            self.assertEqual(point['surviving_modes'], [0, 1])
            self.assertEqual(point['possible_worlds'], [0])
            self.assertEqual(point['probabilities'], [1.])
            self.assertTrue(point['answerable'])
            self.assertEqual(point['entropy_nats'], 0.)
            self.assertEqual(point['brier_floor'], 0.)
            result = audit._summary(records(tape([contact('a', 'a')], n=n), paired=False))
            self.assertEqual(result['frozen_lexicographic_trajectory_exact'], 1.)
            self.assertIsNone(result['frozen_lexicographic_role_pair_exact'])

    def test_coherent_trajectory_conjunction_is_not_product_of_marginal_ceilings(self):
        case = tape([contact('a', 'b'), contact('b', 'c')], missing=[set('abc'), set()])
        result = audit._summary(records(case))
        self.assertEqual(result['law_expected']['all']['bayes_map_accuracy'], .5)
        self.assertEqual(result['frozen_lexicographic_trajectory_exact'], .5)
        self.assertNotEqual(result['frozen_lexicographic_trajectory_exact'], .5 * .5)
        self.assertEqual(result['frozen_lexicographic_role_pair_exact'], 0.)
        known = audit._summary(records(tape([contact('a', 'b'), contact('b', 'c')])))
        self.assertEqual(known['law_expected']['all']['bayes_map_accuracy'], .75)
        self.assertEqual(known['frozen_lexicographic_trajectory_exact'], .5)

    def test_actual_hidden_draw_never_selects_the_law_weighted_result(self):
        actions = [contact('a', 'b'), contact('b', 'c')]
        left = records(tape(actions, mode=0), actual_mode=0)
        right = records(tape(actions, mode=1), actual_mode=1)
        self.assertEqual(audit._summary(left), audit._summary(right))
        self.assertEqual([r['modes'] for r in left], [r['modes'] for r in right])

    def test_all_actions_and_contact_denominators_remain_distinct(self):
        case = tape([{'kind': 'set', 'participants': ['c'], 'value': 0}, contact('a', 'b')])
        result = audit._summary(records(case))
        self.assertEqual(result['counts']['planned_steps'], 4)
        self.assertEqual(result['counts']['contact_steps'], 2)
        self.assertEqual(result['counts']['answerable_steps'], 2)
        self.assertEqual(result['law_expected']['all']['bayes_map_accuracy'], .75)
        self.assertEqual(result['law_expected']['contact']['bayes_map_accuracy'], .5)
        self.assertEqual(result['law_expected']['answerable']['bayes_map_accuracy'], 1.)
        self.assertFalse(result['original_in_family_target']['expected_ceiling_at_least_target'])

    def test_resource_bound_uses_cumulative_hidden_history_and_keeps_complete_later_readings(self):
        actions = [contact('a', 'b'), contact('b', 'c'), {'kind': 'observe', 'participants': []}]
        bad = audit._resources(tape(actions, n=6, missing=[set('ab'), set('cd'), set()]), 3)
        self.assertEqual([r['live_histories_before'] for r in bad['steps']], [1, 4, 16])
        self.assertEqual([r['candidate_expansions'] for r in bad['steps']], [64, 256, 1024])
        self.assertEqual(bad['steps'][-1]['live_histories_after'], 16)
        self.assertFalse(bad['within_dense_support_bounds'])
        self.assertFalse(bad['within_configured_missing_limit'])
        good = audit._resources(tape(actions, n=6, missing=[set('abc'), set(), set()]), 3)
        self.assertEqual(good['steps'][1]['candidate_expansions'], 512)
        self.assertTrue(good['within_dense_support_bounds'])

    def test_carry_targets_later_contact_effects_not_persistent_bystander_changes(self):
        chain = audit._branch(tape([contact('a', 'b'), contact('b', 'c')]), 0)['carry']
        self.assertEqual(chain, {'tested_contact_pairs': 1, 'witnesses': [
            {'earlier_step': 0, 'later_step': 1, 'destination': 'c', 'factual_bit': 1, 'suppressed_bit': 0}]})
        disjoint = audit._branch(tape([contact('a', 'b'), contact('c', 'd')], n=4), 0)['carry']
        self.assertEqual(disjoint, {'tested_contact_pairs': 1, 'witnesses': []})
        reset = [contact('a', 'b'), {'kind': 'set', 'participants': ['b'], 'value': 0}, contact('b', 'c')]
        self.assertFalse(audit._branch(tape(reset), 0)['carry']['witnesses'])


class AssetAuditContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = small_bundle()

    def test_complete_small_bundle_is_strict_json_pure_and_retains_every_family_and_draw(self):
        before = contract.digest(self.bundle)
        report = audit.audit_assets(self.bundle)
        self.assertEqual(before, contract.digest(self.bundle))
        self.assertEqual(json.loads(json.dumps(report, allow_nan=False)), report)
        self.assertEqual(report, audit.audit_assets(self.bundle))
        self.assertEqual(report['aggregate']['counts']['episodes'], 19)
        self.assertEqual(report['aggregate']['counts']['physical_draws'], 10)
        self.assertEqual(set(report['by_split']['evaluation']['by_family']),
                         {'single_contact', 'two_contacts', 'cycle', 'self_contact'})
        self.assertEqual(report['gate_g1'], 'NOT_ADMITTED')
        self.assertFalse(report['learned_model_evaluated'])
        self.assertFalse(report['assumptions']['scientific_comparison_design_complete'])
        self.assertFalse(report['assumptions']['exogenous_design_independently_authenticated'])
        self.assertTrue(report['assumptions']['configured_resource_envelope_satisfied'])
        self.assertIsInstance(report['templates_shared_across_splits'], dict)

    def test_removing_a_whole_physical_pair_cannot_shorten_the_configured_denominator(self):
        broken = deepcopy(self.bundle); part = broken['splits']['train']
        lineage = part['cases'][0]['lineage']
        names = {r['episode'] for r in part['cases'] if r['lineage'] == lineage}
        part['cases'] = [r for r in part['cases'] if r['episode'] not in names]
        for key in ('inputs', 'oracle'):
            part[key]['episodes'] = [r for r in part[key]['episodes'] if r['episode'] not in names]
        part['oracle']['input_sha256'] = contract.digest(part['inputs'])
        with self.assertRaisesRegex(ValueError, 'configured.*inventory'):
            audit.audit_assets(broken)

    def test_family_relabel_and_reset_between_contacts_are_rejected(self):
        broken = deepcopy(self.bundle)
        for row in broken['splits']['train']['cases']:
            if row['family'] == 'single_contact': row['family'] = 'two_contacts'
        with self.assertRaisesRegex(ValueError, 'declared family'):
            audit.audit_assets(broken)
        broken = deepcopy(self.bundle); part = broken['splits']['train']
        name = next(r['episode'] for r in part['cases'] if r['family'] == 'two_contacts')
        case = next(r for r in part['inputs']['episodes'] if r['episode'] == name)
        first = next(t for t, a in enumerate(case['actions']) if a['kind'] == 'contact')
        case['actions'].insert(first + 1, {'kind': 'set', 'participants': [case['ids'][0]], 'value': 0})
        case['coverage'].insert(first + 1, case['ids'].copy())
        case['observations'].insert(first + 2, deepcopy(case['observations'][first + 1]))
        part['oracle']['input_sha256'] = contract.digest(part['inputs'])
        with self.assertRaisesRegex(ValueError, 'optional leading set'):
            audit.audit_assets(broken)

    def test_source_truth_and_incomplete_oracle_are_rejected(self):
        broken = deepcopy(self.bundle)
        broken['source_sha256']['world.py'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'source identity'):
            audit.audit_assets(broken)
        broken = deepcopy(self.bundle)
        truth = broken['splits']['train']['oracle']['episodes'][0]['truth'][-1]
        truth[next(iter(truth))] ^= 1
        with self.assertRaisesRegex(ValueError, 'truth contradict'):
            audit.audit_assets(broken)
        broken = deepcopy(self.bundle)
        target = next(r for part in broken['splits'].values() for r in part['oracle']['episodes']
                      if any(len(p) == 2 for p in r['possible_worlds']))
        index = next(t for t, p in enumerate(target['possible_worlds']) if len(p) == 2)
        actual = int(''.join(str(target['truth'][index + 1][i]) for i in sorted(target['truth'][index + 1])), 2)
        target['possible_worlds'][index] = [actual]
        with self.assertRaisesRegex(ValueError, 'support is incomplete'):
            audit.audit_assets(broken)

    def test_pair_mode_consistency_and_cross_split_lineage_are_checked(self):
        broken = deepcopy(self.bundle); part = broken['splits']['train']
        part['cases'][0]['hidden_source_slot'] ^= 1
        refresh(part)
        with self.assertRaisesRegex(ValueError, 'role views differ'):
            audit.audit_assets(broken)
        broken = deepcopy(self.bundle)
        reused = broken['splits']['train']['cases'][0]['lineage']
        pair = broken['splits']['selection']['cases'][0]['lineage']
        for row in broken['splits']['selection']['cases']:
            if row['lineage'] == pair: row['lineage'] = reused
        with self.assertRaisesRegex(ValueError, 'lineage crosses'):
            audit.audit_assets(broken)

    def test_bound_exceedance_remains_reported_without_dropping_cases_or_claiming_conformance(self):
        broken = small_bundle(6); part = broken['splits']['train']
        lineage = next(r['lineage'] for r in part['cases'] if r['family'] == 'two_contacts')
        names = {r['episode'] for r in part['cases'] if r['lineage'] == lineage}
        for case in part['inputs']['episodes']:
            if case['episode'] in names:
                case['observations'][1] = {i: None for i in case['ids']}
        refresh(part)
        report = audit.audit_assets(broken)
        self.assertEqual(report['by_split']['train']['counts']['episodes'], 4)
        self.assertEqual(report['by_split']['train']['resources']['episodes_with_dense_bound_exceedance'], 2)
        self.assertEqual(report['by_split']['train']['resources']['episodes_exceeding_configured_missing_bits'], 2)
        self.assertFalse(report['assumptions']['configured_resource_envelope_satisfied'])
        self.assertEqual(report['gate_g1'], 'NOT_ADMITTED')


if __name__ == '__main__':
    unittest.main()
