"""Synthetic artifact-contract checks; no world generation, model fitting or gate score."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import acceptance_contract as contract


def refresh_hashes(plan, inputs, oracle):
    """Commit intentionally authored synthetic records after a test mutation."""
    observed = {row['episode']: row for row in inputs['episodes']}
    oracle['input_sha256'] = plan['input_sha256'] = contract.digest(inputs)
    for row in oracle['episodes']:
        if row['episode'] in observed:
            case = observed[row['episode']]
            row['information_keys'] = [contract.information_key(case, t) for t in range(len(case['actions']))]
    plan['oracle_sha256'] = contract.digest(oracle)


def make_bundle(entities=3, steps=2):
    """Two zero-state synthetic histories; supplied support is not a physics oracle."""
    ids = [chr(97 + i) for i in reversed(range(entities))]
    episodes, gold, cases = [], [], []
    for direction in (0, 1):
        name = 'forward' if direction == 0 else 'reverse'
        contact = [ids[0], ids[1]][::1 if direction == 0 else -1]
        episodes.append({'episode': name, 'ids': ids.copy(),
            'observations': [dict.fromkeys(ids, 0) for _ in range(steps + 1)],
            'actions': [{'kind': 'contact', 'participants': contact}] +
                       [{'kind': 'observe', 'participants': []} for _ in range(steps - 1)],
            'coverage': [ids.copy() for _ in range(steps)]})
        gold.append({'episode': name, 'truth': [dict.fromkeys(ids, 0) for _ in range(steps + 1)],
                     'possible_worlds': [[0] for _ in range(steps)], 'information_keys': []})
        cases.append({'episode': name, 'family': 'synthetic_reversal', 'partition': 'held_out',
                      'lineage': 'evaluation-root', 'pair_id': 'role-pair', 'direction': direction})
    inputs = {'version': 'active-acceptance-input-v1', 'episodes': episodes}
    oracle = {'version': 'active-acceptance-oracle-v1', 'input_sha256': '',
              'source_sha256': '2' * 64, 'information_law_sha256': '3' * 64, 'episodes': gold}
    plan = {'version': 'active-acceptance-plan-v1', 'contract_sha256': contract.contract_digest(),
            'study_id': 'contract-invariant', 'scope': 'SYNTHETIC_INVARIANTS', 'input_sha256': '',
            'oracle_sha256': '', 'oracle_source_sha256': oracle['source_sha256'],
            'information_law_sha256': oracle['information_law_sha256'], 'model_seeds': [7],
            'participants': {'no_change': {'7': '1' * 64}}, 'reference_participant': 'no_change',
            'cases': cases, 'split_lineage': {'train': ['train-root'], 'selection': ['selection-root'],
            'calibration': ['calibration-root'], 'evaluation': ['evaluation-root']},
            'development_families': ['training_family'], 'software_sha256': contract.software_sources()}
    refresh_hashes(plan, inputs, oracle)
    return plan, inputs, oracle


class AcceptanceContractTests(unittest.TestCase):
    def test_new_contract_lock_and_original_protocol_remain_separate(self):
        original = (contract.ROOT / 'protocol.json').read_bytes()
        self.assertEqual(sha256(original).hexdigest(),
                         '622a0dfdf94d14b4f16461a0f20acce18bb880f094d5071e58cd1764bdc9c1e7')
        frozen = (contract.ROOT / 'acceptance_protocol_v1.json').read_bytes()
        self.assertEqual(contract.contract_digest(), sha256(frozen).hexdigest())
        settings = json.loads(frozen)
        self.assertEqual(settings['gate_g1'], 'NOT_ADMITTED')
        self.assertTrue(settings['original_protocol_unchanged'])
        self.assertEqual(settings['limits']['actions_per_episode'], 128)

    def test_dynamic_geometry_aliases_and_session_horizon(self):
        for entities in range(3, 7):
            with self.subTest(entities=entities):
                plan, inputs, oracle = make_bundle(entities, steps=13)
                before = deepcopy((plan, inputs, oracle))
                result = contract.validate_bundle(plan, inputs, oracle, [])
                self.assertEqual(len(result['rows']), 26)
                self.assertEqual(result['rows'][0]['ids'], sorted(inputs['episodes'][0]['ids']))
                self.assertEqual((plan, inputs, oracle), before)
                alias = deepcopy(inputs)
                alias['episodes'][0]['actions'][0]['participants'] = ['a', 'a']
                contract.validate_inputs(alias)
        _, longest, _ = make_bundle(steps=128)
        contract.validate_inputs(longest)
        _, too_long, _ = make_bundle(steps=129)
        with self.assertRaises(ValueError): contract.validate_inputs(too_long)

    def test_input_rejects_hidden_fields_bad_coordinates_and_nonbinary_types(self):
        _, inputs, _ = make_bundle()
        def check(change):
            candidate = deepcopy(inputs); change(candidate)
            with self.assertRaises(ValueError): contract.validate_inputs(candidate)
        mutations = [
            lambda x: x.update(hidden_mode=0),
            lambda x: x['episodes'][0].update(truth=[]),
            lambda x: x['episodes'].append(deepcopy(x['episodes'][0])),
            lambda x: x['episodes'][0]['ids'].__setitem__(0, 'a'),
            lambda x: x['episodes'][0]['observations'][0].__setitem__('a', None),
            lambda x: x['episodes'][0]['observations'][1].__setitem__('a', True),
            lambda x: x['episodes'][0]['coverage'].__setitem__(0, []),
            lambda x: x['episodes'][0]['coverage'].__setitem__(0, ['a']),
            lambda x: x['episodes'][0]['actions'][0]['participants'].__setitem__(0, 'unknown'),
            lambda x: x['episodes'][0]['actions'].__setitem__(0,
                {'kind': 'set', 'participants': ['a'], 'value': False}),
        ]
        for index, change in enumerate(mutations):
            with self.subTest(index=index): check(change)

    def test_information_key_excludes_future_outcomes_and_names_but_binds_current_coverage(self):
        _, inputs, _ = make_bundle()
        case = inputs['episodes'][0]
        key = contract.information_key(case, 0)
        future = deepcopy(case)
        future['episode'] = 'different-label'
        future['ids'].reverse()
        future['observations'][1]['a'] = None
        future['actions'][1] = {'kind': 'set', 'participants': ['a'], 'value': 1}
        self.assertEqual(contract.information_key(future, 0), key)
        renamed = deepcopy(case)
        rename = {name: 'new-' + name for name in case['ids']}
        renamed['ids'] = [rename[name] for name in case['ids']]
        renamed['observations'] = [{rename[k]: v for k, v in row.items()} for row in case['observations']]
        renamed['coverage'] = [[rename[k] for k in row] for row in case['coverage']]
        for action in renamed['actions']: action['participants'] = [rename[k] for k in action['participants']]
        self.assertEqual(contract.information_key(renamed, 0), key)
        selected = deepcopy(case); selected['coverage'][0] = ['a']
        self.assertNotEqual(contract.information_key(selected, 0), key)
        past = deepcopy(case); past['observations'][0]['a'] = 1
        self.assertNotEqual(contract.information_key(past, 0), key)
        for bad in (True, -1, 2):
            with self.assertRaises(ValueError): contract.information_key(case, bad)

    def test_prospective_requires_all_five_exact_seeds_and_every_arm_checkpoint(self):
        plan, inputs, _ = make_bundle()
        plan['scope'] = 'PROSPECTIVE_DIAGNOSTIC'
        with self.assertRaises(ValueError): contract.validate_plan(plan, inputs)
        plan['model_seeds'] = [7, 11, 23, 37, 53]
        plan['participants']['no_change'] = {str(seed): '1' * 64 for seed in plan['model_seeds']}
        contract.validate_plan(plan, inputs)
        del plan['participants']['no_change']['53']
        with self.assertRaises(ValueError): contract.validate_plan(plan, inputs)
        for seeds in ([True], [7, 7], [-1]):
            bad, observed, _ = make_bundle(); bad['model_seeds'] = seeds
            with self.assertRaises(ValueError): contract.validate_plan(bad, observed)

    def test_plan_rejects_cross_partition_lineage_and_developed_heldout_family(self):
        plan, inputs, _ = make_bundle()
        bad = deepcopy(plan); bad['split_lineage']['train'].append('evaluation-root')
        with self.assertRaises(ValueError): contract.validate_plan(bad, inputs)
        bad = deepcopy(plan); bad['development_families'].append('synthetic_reversal')
        with self.assertRaises(ValueError): contract.validate_plan(bad, inputs)
        bad = deepcopy(plan); bad['cases'][0]['lineage'] = 'undeclared'
        with self.assertRaises(ValueError): contract.validate_plan(bad, inputs)

    def test_plan_freezes_exact_collector_scorer_and_inference_sources(self):
        plan, inputs, _ = make_bundle()
        self.assertEqual(set(plan['software_sha256']), set(contract.INFERENCE_SOURCES) |
                         {'acceptance_contract.py', 'acceptance_runner.py', 'acceptance_scoring.py'})
        for name in ('acceptance_runner.py', 'acceptance_scoring.py', 'domain_kernel.py'):
            bad = deepcopy(plan); bad['software_sha256'][name] = '0' * 64
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'software differs'):
                contract.validate_plan(bad, inputs)
        bad = deepcopy(plan); del bad['software_sha256']['active_participant.py']
        with self.assertRaises(ValueError): contract.validate_plan(bad, inputs)

    def test_pair_requires_two_directions_and_actual_reversed_contacts(self):
        plan, inputs, oracle = make_bundle()
        for change in (lambda p: p['cases'][1].update(direction=0),
                       lambda p: p['cases'][1].update(direction=True),
                       lambda p: p['cases'][1].update(pair_id=None, direction=None)):
            bad = deepcopy(plan); change(bad)
            with self.assertRaises(ValueError): contract.validate_plan(bad, inputs)
        bad_inputs = deepcopy(inputs)
        bad_inputs['episodes'][1]['actions'][0] = deepcopy(bad_inputs['episodes'][0]['actions'][0])
        refresh_hashes(plan, bad_inputs, oracle)
        with self.assertRaises(ValueError): contract.validate_plan(plan, bad_inputs)

    def test_plan_and_gold_inventory_hashes_and_extra_fields_are_strict(self):
        plan, inputs, oracle = make_bundle()
        for key in ('contract_sha256', 'input_sha256', 'oracle_sha256', 'oracle_source_sha256', 'information_law_sha256'):
            bad = deepcopy(plan); bad[key] = '0' * 64
            with self.subTest(key=key), self.assertRaises(ValueError): contract.validate_bundle(bad, inputs, oracle, [])
        for target in ('plan', 'oracle'):
            for operation in ('missing', 'extra', 'field'):
                p, x, g = make_bundle()
                obj, key = (p, 'cases') if target == 'plan' else (g, 'episodes')
                if operation == 'missing': obj[key].pop()
                elif operation == 'extra':
                    new = deepcopy(obj[key][0]); new['episode'] = 'unplanned'; obj[key].append(new)
                else: obj['independent_custody'] = True
                p['oracle_sha256'] = contract.digest(g)
                with self.subTest(target=target, operation=operation), self.assertRaises(ValueError):
                    contract.validate_bundle(p, x, g, [])

    def test_oracle_rejects_false_support_and_inconsistent_visible_truth(self):
        mutations = [lambda g: g['episodes'][0]['possible_worlds'].__setitem__(0, []),
                     lambda g: g['episodes'][0]['possible_worlds'].__setitem__(0, [0, 0]),
                     lambda g: g['episodes'][0]['possible_worlds'].__setitem__(0, [0, True]),
                     lambda g: g['episodes'][0]['possible_worlds'].__setitem__(0, [8]),
                     lambda g: g['episodes'][0]['possible_worlds'].__setitem__(0, [1]),
                     lambda g: g['episodes'][0]['truth'][1].__setitem__('a', 1),
                     lambda g: g['episodes'][0]['information_keys'].__setitem__(0, '0' * 64)]
        for index, change in enumerate(mutations):
            p, x, g = make_bundle(); change(g); p['oracle_sha256'] = contract.digest(g)
            with self.subTest(index=index), self.assertRaises(ValueError): contract.validate_bundle(p, x, g, [])

    def test_identical_preforecast_information_cannot_get_outcome_selected_support(self):
        p, x, g = make_bundle()
        alternate = deepcopy(x['episodes'][0]); alternate['episode'] = 'alternate'
        for observed in alternate['observations'][1:]: observed['a'] = 1
        x['episodes'].append(alternate)
        p['cases'].append({**p['cases'][0], 'episode': 'alternate', 'pair_id': None, 'direction': None})
        alternate_gold = deepcopy(g['episodes'][0]); alternate_gold['episode'] = 'alternate'
        for truth in alternate_gold['truth'][1:]: truth['a'] = 1
        alternate_gold['possible_worlds'] = [[0, 4], [4]]
        g['episodes'][0]['possible_worlds'][0] = [0, 4]
        g['episodes'].append(alternate_gold)
        refresh_hashes(p, x, g)
        contract.validate_bundle(p, x, g, [])
        g['episodes'][-1]['possible_worlds'][0] = [4]
        p['oracle_sha256'] = contract.digest(g)
        with self.assertRaisesRegex(ValueError, 'same visible information'):
            contract.validate_bundle(p, x, g, [])

    def test_missing_trials_keep_every_planned_point_and_never_admit_gate(self):
        p, x, g = make_bundle()
        p['model_seeds'] = [7, 11]
        p['participants'] = {name: {str(seed): '1' * 64 for seed in p['model_seeds']}
                             for name in ('no_change', 'other_control')}
        result = contract.validate_bundle(p, x, g, [])
        self.assertEqual(len(result['rows']), 16)
        self.assertEqual({r['status'] for r in result['rows']}, {'UNPRODUCED'})
        self.assertTrue(all(r['log_probabilities'] is None for r in result['rows']))
        self.assertEqual(sum(r['reason'] == 'MISSING_TRIAL' for r in result['metadata']['incomplete_inventory']), 4)
        self.assertEqual(result['metadata']['gate_g1'], 'NOT_ADMITTED')
        for key in ('scientific_admission', 'independent_custody_verified',
                    'oracle_support_completeness_verified', 'capacity_or_compute_match_established'):
            self.assertIs(result['metadata'][key], False)

    def test_json_hash_duplicate_nonfinite_size_and_no_overwrite_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'artifact.json'
            value = {'record': [0, None, 'kept']}
            digest = contract.write_json(path, value)
            original = path.read_bytes()
            self.assertEqual(contract.load_json(path, digest), value)
            with self.assertRaises(FileExistsError): contract.write_json(path, {'different': True})
            self.assertEqual(path.read_bytes(), original)
            for expected in (None, '0' * 64, digest.upper()):
                with self.assertRaises(ValueError): contract.load_json(path, expected)
            with patch.object(contract, 'MAX_BYTES', 2):
                with self.assertRaises(ValueError): contract.load_json(path, digest)
            for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}'):
                path.write_bytes(raw)
                with self.assertRaises(ValueError): contract.load_json(path, sha256(raw).hexdigest())


if __name__ == '__main__':
    unittest.main()
