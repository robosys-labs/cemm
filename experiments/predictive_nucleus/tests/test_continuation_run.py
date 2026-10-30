"""Synthetic decision and driver wiring; no fitting, generator, or study-bank run."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import acceptance_runner as runner
from experiments.predictive_nucleus import continuation_run as run
from experiments.predictive_nucleus.active_checkpoint import save_checkpoint
from experiments.predictive_nucleus.tests.test_acceptance_contract import make_bundle


def decision_fixture(config):
    arms = {}
    for arm, accuracy in [('shared', .8), ('flat', .7), ('empirical_local', .5), ('empirical_contact', .5)]:
        entry = {'ood_macro_accuracy': accuracy,
            'ood_family_accuracy': dict.fromkeys(config['design']['ood_families'], accuracy),
            'ood_continuation': {'accuracy': 1 - accuracy},
            'in_family_continuation': {'accuracy': .95},
            'continuation': {'support_coverage': 1., 'unchanged_bit_errors': 0},
            'query_role_pairs': {'records': [{'family': 'two_contacts', 'both_exact': i < 19}
                for i in range(20)] + [{'family': 'fork', 'both_exact': False}]}}
        arms[arm] = {'by_seed': {str(seed): deepcopy(entry) for seed in run.SEEDS}}
    return arms


def synthetic_assets():
    """Zero-state hand-authored targets/support, deliberately not a physics oracle."""
    topologies = {'single_contact': [('a', 'b')], 'two_contacts': [('a', 'b'), ('b', 'c')],
        'three_contact_chain': [('a', 'b'), ('b', 'c'), ('c', 'd')],
        'fork': [('a', 'b'), ('a', 'c'), ('a', 'd')],
        'cycle': [('a', 'b'), ('b', 'c'), ('c', 'a')],
        'disjoint': [('a', 'b'), ('c', 'd'), ('a', 'b')], 'self_contact': [('a', 'a')]}
    episodes, gold, cases = [], [], []
    for family, edges in topologies.items():
        _, inputs, oracle = make_bundle(entities=4, steps=len(edges))
        for direction in ((None,) if family == 'self_contact' else (0, 1)):
            case, target = inputs['episodes'][direction or 0], oracle['episodes'][direction or 0]
            case['episode'] = target['episode'] = f'synthetic-{family}-{direction}'
            case['actions'] = [{'kind': 'contact', 'participants': list(edge)[::-1 if direction else 1]}
                               for edge in edges]
            target['information_keys'] = [contract.information_key(case, t) for t in range(len(edges))]
            queries = [0] if direction is None else list(range(1, len(edges)))
            cases.append({'episode': case['episode'], 'family': family,
                'partition': 'in_family' if family in ('single_contact', 'two_contacts') else 'held_out',
                'lineage': family, 'pair_id': family if direction is not None else None, 'direction': direction,
                'entities': 4, 'contact_count': len(edges), 'query_steps': queries,
                'acquisition_step': 0 if direction is not None else None,
                'query_scope': 'self_contact' if direction is None else 'continuation' if queries else 'acquisition_only'})
            episodes.append(case); gold.append(target)
    inputs['episodes'], oracle['episodes'] = episodes, gold
    oracle['input_sha256'] = contract.digest(inputs)
    return inputs, oracle, cases


class ContinuationRunTests(unittest.TestCase):
    def setUp(self):
        self.config = run._read(run.PROTOCOL)

    def test_exact_sign_test_requires_five_positive_seeds_and_material_macro_gain(self):
        scenarios = [([.75] * 5, 5, 1 / 32, True, 'KEEP_BOUNDED_ADVANTAGE'),
                     ([.7] * 4 + [.8], 4, 6 / 32, True, 'REJECT_MATERIAL_ADVANTAGE'),
                     ([.751] * 5, 5, 1 / 32, False, 'REJECT_MATERIAL_ADVANTAGE')]
        for scores, wins, p, material, outcome in scenarios:
            arms = decision_fixture(self.config)
            for seed, value in zip(run.SEEDS, scores, strict=True):
                arms['flat']['by_seed'][str(seed)]['ood_macro_accuracy'] = value
            with self.subTest(scores=scores):
                result = run.decision(arms, True, self.config)
                self.assertEqual((result['positive_seeds'], result['one_sided_sign_p']), (wins, p))
                self.assertEqual((result['material_gain_pass'], result['decision']), (material, outcome))
                self.assertEqual(result['gate_g1'], 'NOT_ADMITTED')

    def test_each_competence_condition_is_required_at_every_seed(self):
        for condition in ('accuracy', 'pair', 'support', 'preservation', 'nonregression'):
            arms = decision_fixture(self.config)
            candidate = arms['shared']['by_seed']['53']
            if condition == 'accuracy': candidate['in_family_continuation']['accuracy'] = .949
            elif condition == 'pair': candidate['query_role_pairs']['records'][0]['both_exact'] = False
            elif condition == 'support': candidate['continuation']['support_coverage'] = .999
            elif condition == 'preservation': candidate['continuation']['unchanged_bit_errors'] = 1
            else: arms['flat']['by_seed']['53']['in_family_continuation']['accuracy'] = .96
            with self.subTest(condition=condition):
                result = run.decision(arms, True, self.config)
                self.assertFalse(result['competence_pass'])
                self.assertEqual(result['decision'], 'REJECT_CURRENT_CONFIGURATION')

    def test_strongest_empirical_match_and_incomplete_run_have_priority(self):
        arms = decision_fixture(self.config)
        for value, matched, outcome in [(.789, False, 'KEEP_BOUNDED_ADVANTAGE'),
                                       (.79, True, 'REJECT_SUPERIORITY_SIMPLIFY')]:
            for entry in arms['empirical_contact']['by_seed'].values(): entry['ood_macro_accuracy'] = value
            result = run.decision(arms, True, self.config)
            self.assertEqual((result['empirical_matches'], result['decision']), (matched, outcome))
        self.assertEqual(run.decision(arms, False, self.config)['decision'], 'STOP_INCOMPLETE_RUN')
        arms['shared']['by_seed']['53']['continuation']['unchanged_bit_errors'] = 1
        self.assertEqual(run.decision(arms, True, self.config)['decision'], 'REJECT_CURRENT_CONFIGURATION')

    def test_seed_and_ood_family_inventory_cannot_silently_shrink(self):
        for arm, change in [('shared', 'seed'), ('flat', 'family'), ('empirical_local', 'extra')]:
            arms = decision_fixture(self.config)
            if change == 'seed': del arms[arm]['by_seed']['53']
            elif change == 'family': del arms[arm]['by_seed']['53']['ood_family_accuracy']['cycle']
            else: arms[arm]['by_seed']['53']['ood_family_accuracy']['self_contact'] = 1.
            with self.subTest(arm=arm), self.assertRaisesRegex(ValueError, 'inventory differs'):
                run.decision(arms, True, self.config)

    def test_synthetic_bind_collect_preserves_all_query_scopes_and_native_hashes(self):
        inputs, oracle, cases = synthetic_assets()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data, fitted, output = (root / name for name in ('data', 'fitted', 'results'))
            data.mkdir(); fitted.mkdir()
            run._write(data / 'evaluation-inputs.json', inputs)
            run._write(data / 'evaluation-oracle.json', oracle)
            run._write(data / 'cases.json', {'train': [], 'selection': [], 'calibration': [], 'evaluation': cases})
            run._write(data / 'prefit.json', {'scope': 'SYNTHETIC_INVARIANTS'})
            saved = save_checkpoint(fitted / 'synthetic.json', control='no_change',
                provenance={'objective': 'no_change', 'completed_updates': 0, 'training_input_sha256': None})
            inventory = {arm: {str(seed): {'file': 'synthetic.json', **saved} for seed in run.SEEDS}
                         for arm in ('shared', 'flat', 'empirical_local')}
            run._write(fitted / 'training.json', {'checkpoints': inventory,
                'all_prescribed_updates_completed': True, 'status': 'COMPLETE'})
            # Only custody/runtime plumbing is substituted; native binding, collection and scoring run.
            with patch.object(run, '_verify', return_value=self.config), patch.object(run, '_runtime', return_value={}), \
                    patch.object(run, '_committed'), patch.object(run, '_git', return_value='synthetic-commit'), \
                    patch.object(run, 'PREFIT', data / 'prefit.json'), redirect_stdout(io.StringIO()):
                run.bind(data, fitted)
                plan = run._read(fitted / 'plan.json')
                self.assertEqual(plan['participants']['shared'], dict.fromkeys(map(str, run.SEEDS), saved['sha256']))
                self.assertTrue(all(set(c) == {'episode', 'family', 'partition', 'lineage', 'pair_id', 'direction'}
                                    for c in plan['cases']))
                run.collect(data, fitted, output)
                result = run._read(output / 'summary.json.xz')
                self.assertEqual(result['decision']['decision'], 'REJECT_SUPERIORITY_SIMPLIFY')
                self.assertEqual(result['decision']['gate_g1'], 'NOT_ADMITTED')
                for arm in result['by_arm'].values():
                    self.assertEqual(set(arm['by_seed']), set(map(str, run.SEEDS)))
                    for entry in arm['by_seed'].values():
                        self.assertEqual(set(entry['by_family']), {c['family'] for c in cases})
                        self.assertEqual((entry['all_action']['planned_points'], entry['continuation']['planned_points']), (31, 18))
                        self.assertEqual((entry['self_contact']['planned_points'], entry['query_role_pairs']['planned']), (1, 5))
                        self.assertEqual(entry['by_family']['single_contact']['planned_points'], 0)
                        self.assertEqual(entry['ood_macro_accuracy'], 1.)
                manifest = (output / 'manifest.json').read_bytes()
                self.assertTrue(run._read(output / 'manifest.json')['run_complete'])
                with self.assertRaises(FileExistsError): run.collect(data, fitted, output)
                self.assertEqual((output / 'manifest.json').read_bytes(), manifest)
                class EndFailure(runner.Session):
                    def _handle(self, request):
                        if request['op'] == 'end' and request['episode'] == cases[0]['episode']:
                            raise RuntimeError('synthetic end failure after every forecast')
                        return super()._handle(request)
                failed_output = root / 'end-failure'
                with patch.object(runner, 'Session', EndFailure): run.collect(data, fitted, failed_output)
                failed = run._read(failed_output / 'summary.json.xz')
                self.assertEqual(failed['decision']['decision'], 'STOP_INCOMPLETE_RUN')
                for arm, entries in failed['by_arm'].items():
                    self.assertEqual(len(failed['metadata'][arm]['failure_records']), len(run.SEEDS))
                    self.assertEqual(failed['metadata'][arm]['incomplete_inventory'], [])
                    self.assertTrue(all(e['all_action']['unproduced_forecasts'] == 0
                                        for e in entries['by_seed'].values()))
                failed_manifest = run._read(failed_output / 'manifest.json')
                self.assertTrue(failed_manifest['artifacts_complete'])
                self.assertFalse(failed_manifest['run_complete'])


if __name__ == '__main__':
    unittest.main()
