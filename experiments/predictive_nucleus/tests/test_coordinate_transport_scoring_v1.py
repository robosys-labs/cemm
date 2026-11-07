"""Handcrafted sealed-record tests without native models or scientific-bank generation."""
from copy import deepcopy
from hashlib import sha256
from itertools import permutations, product
import json
import math
import subprocess
import sys
import unittest

from experiments.predictive_nucleus import acceptance_contract as c
from experiments.predictive_nucleus import coordinate_transport_scoring_v1 as s
from experiments.predictive_nucleus.physical_query_v1 import choose, posterior


def one_hot(size, index):
    return [float(position == index) for position in range(size)]


def fixture(view='intact', meaning=0):
    """Two complementary ambiguous observations identify one synthetic meaning."""
    model = {'seed': 7, 'law': 'nand', 'training_sha256': s.TRAINING_SHA256,
             'freeze_sha256': '1' * 64, 'checkpoint_sha256': '2' * 64,
             'language_sha256': '3' * 64, 'registry_sha256': '4' * 64,
             'world_sha256': '5' * 64,
             'new_ids': [sha256(word.encode()).hexdigest() for word in s.WORDS]}
    tables = [[0, 0, 1, 1], [2, 3, 2, 3], [4, 5, 6, 7]]
    layouts = ['svo', 'osv', 'vos']
    oracle = {'id': 'synthetic-trial', 'law': 'nand', 'word': 'lights', 'meaning': meaning,
              'canonical_action': list(s.MEANINGS[meaning]), 'physical_actions': [],
              'action_indices': [], 'endpoints': [table[meaning] for table in tables],
              'outcomes_by_meaning': tables, 'instance_ids': ['synthetic-' + str(i) for i in range(3)],
              'evidence_ids': ['synthetic-' + str(i) + '/utterance/0' for i in range(3)],
              'metadata': {'layouts': layouts, 'pattern': 0, 'modes': [0, 1, 0]}}
    frame = {'version': 'coordinate-transport-v1', 'language_sha256': model['language_sha256'],
             'registry_sha256': model['registry_sha256'], 'world_sha256': model['world_sha256'],
             'lexical_id': sha256(b'lights').hexdigest(), 'transforms': deepcopy(s.TRANSFORMS), 'view': view}
    receipts = []
    for stage, table in enumerate(tables):
        order = (0, 1, 2, 3) if stage == 0 else (1, 0, 3, 2)
        a, b = (0, 1) if stage == 0 else (1, 0)
        actions = [[0, a, b, -1], [0, b, a, -1], [1, a, -1, 1], [1, b, -1, 1]]
        native = [one_hot(8, table[order.index(index)]) for index in range(4)]
        weights = [list(s.UNIFORM) if view == 'zero_layout' else one_hot(4, index) for index in order]
        likelihood = [s._mix(row, native) for row in weights]
        receipt = {'evidence_id': oracle['evidence_ids'][stage], 'prefix_digest': c.digest(['prefix', stage]),
                   'entities': ['synthetic-' + str(stage) + '-' + name for name in ('a', 'b', 'c')],
                   'actions': actions, 'endpoint_encoding': s.ENCODING, 'action_probabilities': weights,
                   'native_likelihood': native, 'likelihood': likelihood,
                   'frame': deepcopy(frame), 'frame_digest': c.digest(frame)}
        if stage < 2:
            receipt['observed_endpoint'] = oracle['endpoints'][stage]
        receipts.append(receipt)
        oracle['action_indices'].append(order[meaning])
        oracle['physical_actions'].append(actions[order[meaning]])
    first, second, target = receipts
    after_first = posterior(s.UNIFORM, first['likelihood'], oracle['endpoints'][0])
    beliefs = {'reset': s.UNIFORM, 'first': after_first,
               'latest': posterior(s.UNIFORM, second['likelihood'], oracle['endpoints'][1]),
               'retained': posterior(after_first, second['likelihood'], oracle['endpoints'][1])}
    predictions = {}
    for name, belief in beliefs.items():
        endpoints = s._mix(belief, target['likelihood'])
        actions = s._mix(belief, target['action_probabilities'])
        predictions[name] = {'endpoint_probabilities': endpoints, 'action_probabilities': actions,
                             'endpoint_action': s._argmax(endpoints), 'physical_action': s._argmax(actions)}
    policies = []
    for name, prior in (('retained', after_first), ('reset', s.UNIFORM)):
        for fee_index, fee in enumerate(s.FEES):
            decision = choose(prior, second['likelihood'], target['likelihood'], fee)
            final = posterior(prior, second['likelihood'], oracle['endpoints'][1]) if decision['ask'] else prior
            endpoints = s._mix(final, target['likelihood'])
            consumed = [first['evidence_id']] if name == 'retained' else []
            if decision['ask']:
                consumed.append(second['evidence_id'])
            policies.append({'prior': name, 'fee_index': fee_index, 'fee': fee, **decision,
                             'posterior': final, 'endpoint_probabilities': endpoints,
                             'target_selected_endpoint': s._argmax(endpoints), 'consumed_ids': consumed})
    return {'receipts': receipts, 'beliefs': beliefs, 'predictions': predictions, 'policies': policies}, oracle, model


def shard_fixture():
    value, oracle, model = fixture()
    check = {'records': 2304, 'endpoint_complement_checks': 2304, 'projection_checks': 9216,
             'uniform_hypothesis_checks': 2304, 'maximum_projection_error': 0., 'maximum_uniform_error': 0.,
             'language_unchanged': True, 'world_unchanged': True}
    return {'version': 'coordinate-transport-raw-v1', 'protocol_commit': s.PROTOCOL_COMMIT,
            'protocol_sha256': s.PROTOCOL_SHA256, 'source_commit': '6' * 40,
            'source_sha256': {'coordinate_transport_scoring_v1.py': '7' * 64}, 'inputs_sha256': '8' * 64,
            'seed': 7, 'law': 'nand', 'model': model, 'checks': {view: deepcopy(check) for view in s.VIEWS},
            'trials': [{'id': oracle['id'], 'views': {'intact': value}}] * 768}


def passing_summaries():
    metrics, policies = {}, {}
    for law in s.LAWS:
        for seed in s.SEEDS:
            for view in s.VIEWS:
                for belief in s.BELIEFS:
                    metrics[s._key(law, seed, view, belief)] = {
                        'count': 768, 'endpoint_accuracy': 1., 'action_accuracy': 1.,
                        'mean_brier': .01 if view == 'intact' and belief == 'retained' else .2,
                        'high_confidence_wrong': 0}
                for prior in ('retained', 'reset'):
                    for fee_index in range(3):
                        policies[s._key(law, seed, view, prior, fee_index)] = {'count': 768, 'mean_net': .9}
    return metrics, policies


def evaluator_fixture():
    """Fabricate the registered inventory using simple categorical tables, without physics."""
    _, template, _ = fixture()
    trials = []
    cells = product(s.LAWS, s.WORDS, range(4), permutations(s.LAYOUTS), range(2), product((0, 1), repeat=3))
    for number, (law, word, meaning, layouts, pattern, modes) in enumerate(cells):
        row = deepcopy(template)
        row.update(id='synthetic-trial-' + str(number), law=law, word=word, meaning=meaning,
                   canonical_action=list(s.MEANINGS[meaning]),
                   metadata={'layouts': list(layouts), 'pattern': pattern, 'modes': list(modes)})
        row['endpoints'] = [table[meaning] for table in row['outcomes_by_meaning']]
        row['action_indices'] = [meaning if layout == 'svo' else (1, 0, 3, 2)[meaning] for layout in layouts]
        row['physical_actions'] = [list(s.MEANINGS[meaning]) for _ in range(3)]
        row['instance_ids'] = [row['id'] + '-stage-' + str(stage) for stage in range(3)]
        row['evidence_ids'] = [identity + '/utterance/0' for identity in row['instance_ids']]
        trials.append(row)
    return {'version': 'coordinate-transport-v1', 'trials': trials}


class CoordinateTransportScoringTests(unittest.TestCase):
    def test_complementary_observations_and_conditional_oracle(self):
        value, oracle, model = fixture()
        original = deepcopy((value, oracle, model))
        predictions, policies = s._evaluate_view(value, oracle, 'intact', model)
        self.assertEqual(s._oracle_distribution(oracle, ()), [0.] * 4 + [.25] * 4)
        self.assertEqual(s._oracle_distribution(oracle, (0,)), [0.] * 4 + [.5, .5, 0., 0.])
        self.assertEqual(s._oracle_distribution(oracle, (1,)), [0.] * 4 + [.5, 0., .5, 0.])
        self.assertEqual(s._oracle_distribution(oracle, (0, 1)), one_hot(8, 4))
        for name, brier, nll in (('reset', .75, math.log(4)), ('first', .5, math.log(2)),
                                ('latest', .5, math.log(2)), ('retained', 0., 0.)):
            self.assertEqual(predictions[name]['brier'], brier)
            self.assertAlmostEqual(predictions[name]['nll'], nll)
            self.assertAlmostEqual(predictions[name]['oracle_kl'], 0.)
        self.assertTrue(predictions['retained']['action_correct'])
        self.assertEqual(policies[('retained', 0)]['fee_paid'], .05)
        self.assertEqual(policies[('retained', 0)]['net'], .95)
        self.assertEqual((value, oracle, model), original)

    def test_mapping_intervention_keeps_native_physics_and_loses_transport(self):
        intact, oracle, model = fixture()
        zero, zero_oracle, zero_model = fixture('zero_layout')
        self.assertEqual(oracle, zero_oracle)
        self.assertEqual(model, zero_model)
        self.assertEqual([row['native_likelihood'] for row in intact['receipts']],
                         [row['native_likelihood'] for row in zero['receipts']])
        predictions, policies = s._evaluate_view(zero, oracle, 'zero_layout', model)
        self.assertEqual(predictions['retained']['brier'], .75)
        self.assertAlmostEqual(predictions['retained']['oracle_kl'], math.log(4))
        self.assertFalse(any(row['ask'] for row in policies.values()))

    def test_zero_probability_losses_are_explicit_and_uncapped(self):
        _, oracle, _ = fixture()
        wrong = one_hot(8, 7)
        point = s._point('wrong', wrong, 7, 3, oracle, (0, 1))
        summary = s._prediction_summary([point])
        self.assertEqual(point['brier'], 2.)
        self.assertIsNone(point['nll'])
        self.assertIsNone(point['oracle_kl'])
        self.assertEqual(summary['nll_status'], 'infinite')
        self.assertEqual(summary['oracle_kl_status'], 'infinite')
        self.assertEqual(summary['infinite_nll_count'], 1)
        self.assertEqual(summary['infinite_oracle_kl_count'], 1)
        self.assertEqual(summary['high_confidence_wrong'], 1)
        self.assertEqual(summary['ece_10'], 1.)
        self.assertEqual(summary['calibration_bins'][9]['count'], 1)
        tiny = [0.] * 8
        tiny[4], tiny[7] = 1e-200, 1. - 1e-200
        point = s._point('tiny', tiny, 7, 3, oracle, (0, 1))
        self.assertAlmostEqual(point['nll'], 200 * math.log(10))
        json.dumps({'point': point, 'summary': summary}, allow_nan=False)

    def test_oracle_zero_failure_can_occur_with_finite_realized_nll(self):
        _, oracle, _ = fixture()
        point = s._point('partial', one_hot(8, 4), 4, 0, oracle, ())
        self.assertEqual(point['nll'], 0.)
        self.assertFalse(point['zero_probability_outcome'])
        self.assertTrue(point['oracle_zero_probability'])
        self.assertIsNone(point['oracle_kl'])

    def test_calibration_bins_and_inclusive_confidence_threshold(self):
        _, oracle, _ = fixture()
        rows = []
        for identity, probability in (('low', .5), ('boundary', .95), ('high', 1.)):
            probabilities = [0.] * 8
            probabilities[4], probabilities[7] = probability, 1. - probability
            rows.append(s._point(identity, probabilities, 4, 0, oracle, (0, 1)))
        summary = s._prediction_summary(rows)
        self.assertEqual(summary['high_confidence_count'], 2)
        self.assertAlmostEqual(summary['high_confidence_coverage'], 2 / 3)
        self.assertAlmostEqual(summary['ece_10'], (.5 + .05) / 3)
        self.assertEqual(summary['calibration_bins'][5]['count'], 1)
        self.assertEqual(summary['calibration_bins'][9]['count'], 2)

    def test_fee_controls_branch_from_same_first_posterior(self):
        value, oracle, model = fixture(meaning=1)
        predictions, policies = s._evaluate_view(value, oracle, 'intact', model)
        retained = {row['fee_index']: row for row in value['policies'] if row['prior'] == 'retained'}
        self.assertEqual({row['expected_before'] for row in retained.values()}, {.5})
        self.assertEqual({row['expected_after'] for row in retained.values()}, {1.})
        self.assertTrue(retained[0]['ask'])
        self.assertFalse(retained[1]['ask'])
        self.assertFalse(retained[2]['ask'])
        self.assertEqual(retained[0]['consumed_ids'], oracle['evidence_ids'][:2])
        self.assertEqual(retained[1]['consumed_ids'], oracle['evidence_ids'][:1])
        self.assertEqual(retained[2]['consumed_ids'], oracle['evidence_ids'][:1])
        self.assertTrue(policies[('retained', 0)]['correct'])
        self.assertFalse(policies[('retained', 1)]['correct'])
        summary = s._policy_summary([policies[('retained', index)] for index in range(3)])
        self.assertEqual(summary['purchased_count'], 1)
        self.assertEqual(summary['gross_total'], 1.)
        self.assertEqual(summary['fee_total'], .05)
        self.assertEqual(summary['net_total'], .95)
        self.assertTrue(predictions['retained']['endpoint_correct'])

    def test_invalid_probability_arrays_fail_closed(self):
        for values in ([0.] * 8, [1.] * 8, [float('nan')] + [0.] * 7,
                       [float('inf')] + [0.] * 7, [True] + [0.] * 7,
                       [-.1, 1.1] + [0.] * 6, [1.] + [0.] * 6):
            with self.subTest(values=values), self.assertRaises(ValueError):
                s._probabilities(values, 8)

    def test_projection_frame_and_endpoint_leakage_rejected(self):
        value, oracle, model = fixture()
        def projection(row):
            row['receipts'][0]['likelihood'][0] = one_hot(8, 1)
        def weights(row):
            row['receipts'][0]['action_probabilities'][1] = one_hot(4, 0)
        def digest(row):
            row['receipts'][0]['frame_digest'] = '0' * 64
        def frame(row):
            row['receipts'][0]['frame']['view'] = 'cycled_layout'
        def leak(row):
            row['receipts'][2]['observed_endpoint'] = oracle['endpoints'][2]
        def observed(row):
            row['receipts'][1]['observed_endpoint'] = 7
        def roster(row):
            row['receipts'][1]['entities'] = row['receipts'][0]['entities']
        def menu(row):
            row['receipts'][0]['actions'][2][1] = 2
        for change in (projection, weights, digest, frame, leak, observed, roster, menu):
            broken = deepcopy(value)
            change(broken)
            with self.subTest(change=change.__name__), self.assertRaises(ValueError):
                s._evaluate_view(broken, oracle, 'intact', model)

    def test_saved_posterior_predictions_and_policy_custody_rejected(self):
        value, oracle, model = fixture()
        def belief(row):
            row['beliefs']['retained'] = list(s.UNIFORM)
        def prediction(row):
            row['predictions']['retained']['endpoint_probabilities'] = one_hot(8, 7)
        def action(row):
            row['predictions']['retained']['physical_action'] = 0
        def consumed(row):
            row['policies'][0]['consumed_ids'].reverse()
        def ask(row):
            row['policies'][0]['ask'] = False
        def fee(row):
            row['policies'][0]['fee'] = .1
        def selected(row):
            row['policies'][0]['target_selected_endpoint'] = 7
        def final(row):
            row['policies'][0]['posterior'] = list(s.UNIFORM)
        def expected(row):
            row['policies'][0]['expected_after'] += .01
        def duplicate(row):
            row['policies'][1] = deepcopy(row['policies'][0])
        for change in (belief, prediction, action, consumed, ask, fee, selected, final, expected, duplicate):
            broken = deepcopy(value)
            change(broken)
            with self.subTest(change=change.__name__), self.assertRaises(ValueError):
                s._evaluate_view(broken, oracle, 'intact', model)

    def test_recorded_native_failures_are_not_valid_forecasts(self):
        value, oracle, model = fixture()
        value['failure'] = {'message': 'observed endpoint has zero predicted probability',
                            'evidence_id': oracle['evidence_ids'][1]}
        with self.assertRaisesRegex(ValueError, 'recorded native failure at synthetic-1/utterance/0'):
            s._evaluate_view(value, oracle, 'intact', model)

    def test_paired_records_retain_every_adverse_case_and_infinite_loss(self):
        _, oracle, _ = fixture()
        good = s._point('same', one_hot(8, 4), 4, oracle['action_indices'][2], oracle, (0, 1))
        bad = s._point('same', one_hot(8, 7), 7, 0, oracle, (0, 1))
        pair = s._paired_predictions([bad], [good])
        self.assertEqual(pair['count'], 1)
        self.assertEqual(pair['endpoint_regressions'], 1)
        self.assertEqual(pair['action_regressions'], 1)
        self.assertEqual(pair['brier_worse_count'], 1)
        self.assertEqual(pair['records'][0]['nll'], {'change': None, 'status': 'left_infinite'})
        self.assertEqual(s._paired_predictions([bad], [bad])['records'][0]['nll']['status'], 'both_infinite')
        self.assertEqual(s._paired_predictions([good], [bad])['records'][0]['nll']['status'], 'right_infinite')
        with self.assertRaises(ValueError):
            s._paired_predictions([bad], [])
        json.dumps(pair, allow_nan=False)

    def test_query_pairs_include_purchase_fee_and_net_changes(self):
        value, oracle, model = fixture(meaning=1)
        _, policies = s._evaluate_view(value, oracle, 'intact', model)
        pair = s._paired_policies([policies[('retained', 0)]], [policies[('reset', 2)]])
        self.assertEqual(pair['records'][0]['purchase_change'], 1)
        self.assertEqual(pair['records'][0]['gross_change'], 1)
        self.assertEqual(pair['records'][0]['fee_change'], .05)
        self.assertEqual(pair['mean_net_change'], .95)

    def test_every_condition_and_each_prespecified_gate_is_required(self):
        metrics, policies = passing_summaries()
        self.assertTrue(all(all(gates.values()) for gates in s._gates(metrics, policies).values()))
        retained = s._key('nor', 53, 'intact', 'retained')
        failures = [('endpoint_accuracy', .949, 'endpoint_accuracy_at_least_095'),
                    ('action_accuracy', .949, 'action_accuracy_at_least_095'),
                    ('high_confidence_wrong', 1, 'zero_high_confidence_wrong'),
                    ('count', 767, 'intact_retained_count')]
        for field, value, gate in failures:
            changed = deepcopy(metrics)
            changed[retained][field] = value
            result = s._gates(changed, policies)
            self.assertFalse(result['nor/53'][gate])
            self.assertTrue(all(result['nand/7'].values()))
        for view, belief in (('intact', 'reset'), ('intact', 'latest'), ('zero_layout', 'retained')):
            changed = deepcopy(metrics)
            changed[s._key('nor', 53, view, belief)]['mean_brier'] = .01
            self.assertFalse(s._gates(changed, policies)['nor/53']['brier_improves_over_' + view + '_' + belief])
        changed = deepcopy(policies)
        changed['nor/53/intact/retained/0']['mean_net'] -= 2e-12
        self.assertFalse(s._gates(metrics, changed)['nor/53']['cheap_retained_net_at_least_reset'])
        changed['nor/53/intact/retained/0']['mean_net'] += 1.5e-12
        self.assertTrue(s._gates(metrics, changed)['nor/53']['cheap_retained_net_at_least_reset'])

    def test_native_check_inventory_counts_hypothesis_projections(self):
        shard = shard_fixture()
        s._validate_shard(shard, None)
        for key, wrong in (('projection_checks', 2304), ('records', 9216),
                           ('maximum_projection_error', 2e-12), ('language_unchanged', False)):
            broken = deepcopy(shard)
            broken['checks']['intact'][key] = wrong
            with self.subTest(key=key), self.assertRaises(ValueError):
                s._validate_shard(broken, None)

    def test_source_binding_and_exact_inventory_are_required(self):
        shard = shard_fixture()
        source = {key: shard[key] for key in ('protocol_commit', 'protocol_sha256', 'source_sha256')}
        s._validate_shard(shard, source)
        source['source_sha256'] = {'coordinate_transport_scoring_v1.py': '0' * 64}
        with self.assertRaises(ValueError):
            s._validate_shard(shard, source)
        _, oracle, _ = fixture()
        with self.assertRaisesRegex(ValueError, 'trial count'):
            s._validate_oracle({'version': 'coordinate-transport-v1', 'trials': [oracle]})
        with self.assertRaisesRegex(ValueError, 'duplicate oracle trial ID'):
            s._validate_oracle({'version': 'coordinate-transport-v1', 'trials': [oracle] * 1536})

    def test_full_handcrafted_oracle_inventory_and_covariance(self):
        evaluator = evaluator_fixture()
        self.assertEqual(len(s._validate_oracle(evaluator)), 1536)
        broken = deepcopy(evaluator)
        broken['trials'][0]['action_indices'][0] = 3
        with self.assertRaisesRegex(ValueError, 'covariance'):
            s._validate_oracle(broken)
        broken = deepcopy(evaluator)
        broken['trials'][0]['metadata']['modes'] = broken['trials'][1]['metadata']['modes']
        with self.assertRaisesRegex(ValueError, 'factorial inventory'):
            s._validate_oracle(broken)

    def test_score_retains_every_recorded_failure_from_a_handcrafted_shard(self):
        evaluator = evaluator_fixture()
        shard = shard_fixture()
        shard['trials'] = []
        for row in evaluator['trials']:
            if row['law'] == 'nand':
                failure = {'message': 'synthetic impossible observation', 'evidence_id': row['evidence_ids'][1]}
                shard['trials'].append({'id': row['id'], 'views': {
                    view: {'failure': failure, 'receipts': []} for view in s.VIEWS}})
        collection_failure = {'message': 'collection interrupted', 'error': 'SyntheticInterruption',
                              'seed': 11, 'law': 'nor'}
        result = s.score([shard], evaluator, collection_failures=[collection_failure])
        self.assertEqual(result['decision'], 'REVISE_TRANSPORT_PREFLIGHT')
        failures = [row for row in result['validation_errors'] if 'recorded native failure' in row['message']]
        self.assertEqual(len(failures), 2304)
        self.assertEqual(len({row['location'] for row in failures}), 2304)
        self.assertEqual(result['counts']['oracle_trials'], 1536)
        self.assertEqual(result['counts']['predictions'], 0)
        self.assertEqual(result['counts']['collection_failures'], 1)
        self.assertEqual(result['validation_errors'][0]['location'], 'collection/0')
        self.assertEqual(result['validation_errors'][0]['collection_failure'], collection_failure)
        json.dumps(result, allow_nan=False)

    def test_collection_failures_are_retained_with_inventory_and_gate_failures(self):
        evaluator = {'version': 'coordinate-transport-v1', 'trials': []}
        failures = [{'message': 'incomplete manifest', 'complete': False},
                    {'message': 'missing published shard', 'file': 'raw-nor-53.json.xz'}]
        before = deepcopy(failures)
        empty = s.score([], evaluator)
        result = s.score([], evaluator, collection_failures=failures)
        self.assertEqual(result['decision'], 'REVISE_TRANSPORT_PREFLIGHT')
        self.assertEqual(result['failed_gates'], empty['failed_gates'])
        self.assertEqual(result['counts']['collection_failures'], 2)
        self.assertEqual([row['collection_failure'] for row in result['validation_errors'][:2]], failures)
        self.assertEqual(result['validation_errors'][2:], empty['validation_errors'])
        self.assertEqual(failures, before)
        for invalid in (None, {}, [None], [{}], [{'message': float('nan')}]):
            with self.subTest(invalid=invalid):
                malformed = s.score([], evaluator, collection_failures=invalid)
                self.assertEqual(malformed['decision'], 'REVISE_TRANSPORT_PREFLIGHT')
                self.assertTrue(malformed['validation_errors'][0]['location'].startswith('collection'))
                json.dumps(malformed, allow_nan=False)

    def test_incomplete_score_returns_deterministic_failure_decision(self):
        evaluator = {'version': 'coordinate-transport-v1', 'trials': []}
        result = s.score([], evaluator)
        self.assertEqual(result, s.score([], evaluator))
        self.assertEqual(result['decision'], 'REVISE_TRANSPORT_PREFLIGHT')
        self.assertGreater(len(result['validation_errors']), 0)
        self.assertEqual(len(result['condition_gates']), 10)
        self.assertEqual(len(result['failed_gates']), 80)
        self.assertEqual(result['counts']['predictions'], 0)
        json.dumps(result, allow_nan=False)

    def test_import_does_not_load_models_or_generators(self):
        code = ('import sys\n'
                'import experiments.predictive_nucleus.coordinate_transport_scoring_v1\n'
                'assert "torch" not in sys.modules\n'
                'assert not any(name.endswith(("coordinate_transport_data_v1", "coordinate_transport_run_v1", '
                '"coordinate_transport_v1", "effect_role_model", "effect_role_lexical")) for name in sys.modules)\n')
        subprocess.run([sys.executable, '-c', code], check=True)


if __name__ == '__main__':
    unittest.main()
