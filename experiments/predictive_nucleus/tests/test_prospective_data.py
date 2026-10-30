"""Fresh generator invariants only; no learner fitting or historical challenge runs."""
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
from itertools import permutations
from unittest.mock import patch
import unittest

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import prospective_data as data
from experiments.predictive_nucleus.world import Action, FAMILIES, World, step


class ProspectiveDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bundle = data.build_assets()

    def test_locked_recipe_exact_counts_sources_and_reproducibility(self):
        config = data.read_config()
        before = deepcopy(config)
        again = data.build_assets(config)
        self.assertEqual(config, before)
        self.assertEqual(self.bundle, again)
        self.assertEqual(self.bundle['source_sha256'], data.source_digests())
        self.assertEqual(sha256(data.PROTOCOL.read_bytes()).hexdigest(),
                         data.LOCK.read_text().split()[0])
        self.assertEqual(self.bundle['config']['scope'], 'PUBLIC_SAME_AUTHOR_ENGINEERING_ASSETS')
        self.assertFalse(config['execution_policy']['research_fit_enabled'])
        self.assertFalse(config['execution_policy']['research_model_scoring_enabled'])
        self.assertEqual(config['reporting']['gate_g1'], 'NOT_ADMITTED')
        for split, assets in self.bundle['splits'].items():
            expected = Counter()
            families = config['evaluation_families'] if split == 'evaluation' else config['development_families']
            for family in families:
                minimum = max(3, 1 + max(max(pair) for pair in FAMILIES[family]))
                for n in config['entity_counts']:
                    if n >= minimum:
                        expected[family, n] = config['draws_per_family_entity'][split] * (1 if family == 'self_contact' else 2)
            by_name = {x['episode']: x for x in assets['inputs']['episodes']}
            actual = Counter((r['family'], len(by_name[r['episode']]['ids'])) for r in assets['cases'])
            self.assertEqual(actual, expected)

    def test_observed_fields_and_separate_gold_match_physics(self):
        for split, assets in self.bundle['splits'].items():
            inputs, oracle = assets['inputs'], assets['oracle']
            contract.validate_inputs(inputs)
            commitment = {'oracle_sha256': contract.digest(oracle),
                'oracle_source_sha256': oracle['source_sha256'],
                'information_law_sha256': oracle['information_law_sha256']}
            gold = contract.validate_oracle(oracle, inputs, commitment)
            metadata = {x['episode']: x for x in assets['cases']}
            for case in inputs['episodes']:
                with self.subTest(split=split, episode=case['episode']):
                    self.assertEqual(set(case), {'episode', 'ids', 'observations', 'actions', 'coverage'})
                    ids = case['ids']
                    actual = World(tuple(ids), tuple(case['observations'][0][i] for i in ids),
                                   metadata[case['episode']]['hidden_source_slot'])
                    truths = gold[case['episode']]['truth']
                    self.assertEqual(truths[0], dict(zip(ids, actual.bits)))
                    for t, action in enumerate(case['actions']):
                        actual = step(actual, Action(action['kind'], tuple(action['participants']), action.get('value')))
                        self.assertEqual(truths[t + 1], dict(zip(ids, actual.bits)))
                        for i, bit in case['observations'][t + 1].items():
                            if bit is not None: self.assertEqual(bit, truths[t + 1][i])

    def test_blueprints_and_lineages_are_disjoint_and_identity_normalized(self):
        seen, lineages = {}, {}
        for split, assets in self.bundle['splits'].items():
            cases = {x['episode']: x for x in assets['inputs']['episodes']}
            for row in assets['cases']:
                blueprint, lineage = row['blueprint_sha256'], row['lineage']
                self.assertEqual(seen.setdefault(blueprint, (split, lineage)), (split, lineage))
                self.assertEqual(lineages.setdefault(lineage, blueprint), blueprint)
                self.assertEqual(blueprint, data.blueprint_digest(cases[row['episode']]))
                self.assertEqual(row['template_sha256'], data.template_digest(cases[row['episode']]))
        case = deepcopy(self.bundle['splits']['train']['inputs']['episodes'][0])
        for permutation in permutations(case['ids']):
            names = dict(zip(case['ids'], permutation, strict=True))
            changed = deepcopy(case)
            changed['ids'] = [names[i] for i in reversed(case['ids'])]
            changed['observations'] = [{names[i]: bit for i, bit in row.items()} for row in case['observations']]
            changed['coverage'] = [[names[i] for i in row] for row in case['coverage']]
            for action in changed['actions']: action['participants'] = [names[i] for i in action['participants']]
            self.assertEqual(data.blueprint_digest(case), data.blueprint_digest(changed))
            self.assertEqual(data.template_digest(case), data.template_digest(changed))

    def test_blueprint_uses_mask_and_anchor_but_never_later_values(self):
        case = deepcopy(self.bundle['splits']['train']['inputs']['episodes'][0])
        before = data.blueprint_digest(case)
        altered = deepcopy(case)
        for row in altered['observations'][1:]:
            for i, bit in row.items():
                if bit is not None: row[i] = 1 - bit
        self.assertEqual(data.blueprint_digest(altered), before)
        identifier = case['ids'][0]
        altered['observations'][0][identifier] = 1 - altered['observations'][0][identifier]
        self.assertNotEqual(data.blueprint_digest(altered), before)
        self.assertEqual(data.template_digest(altered), data.template_digest(case))
        altered = deepcopy(case)
        altered['observations'][1][identifier] = None if altered['observations'][1][identifier] is not None else 0
        self.assertNotEqual(data.blueprint_digest(altered), before)

    def test_role_pairs_share_mode_anchor_and_realized_masks(self):
        for assets in self.bundle['splits'].values():
            observed = {x['episode']: x for x in assets['inputs']['episodes']}
            groups = defaultdict(list)
            for row in assets['cases']: groups[row['lineage']].append(row)
            for rows in groups.values():
                if rows[0]['family'] == 'self_contact':
                    self.assertEqual(len(rows), 1)
                    self.assertIsNone(rows[0]['pair_id']); self.assertIsNone(rows[0]['direction'])
                    continue
                self.assertEqual(len(rows), 2)
                first, second = sorted(rows, key=lambda r: r['direction'])
                self.assertEqual([first['direction'], second['direction']], [0, 1])
                for field in ('pair_id', 'hidden_source_slot', 'blueprint_sha256', 'template_sha256'):
                    self.assertEqual(first[field], second[field])
                a, b = observed[first['episode']], observed[second['episode']]
                self.assertEqual(a['ids'], b['ids'])
                self.assertEqual(a['observations'][0], b['observations'][0])
                self.assertEqual(a['coverage'], b['coverage'])
                self.assertEqual([[r[i] is None for i in a['ids']] for r in a['observations']],
                                 [[r[i] is None for i in b['ids']] for r in b['observations']])
                reversed_actions = deepcopy(a['actions'])
                for action in reversed_actions:
                    if action['kind'] == 'contact': action['participants'].reverse()
                self.assertEqual(reversed_actions, b['actions'])

    def test_schedules_have_no_contact_resets_and_missingness_is_bounded(self):
        templates = set()
        for assets in self.bundle['splits'].values():
            metadata = {r['episode']: r for r in assets['cases']}
            for case in assets['inputs']['episodes']:
                kinds = [a['kind'] for a in case['actions']]
                self.assertLessEqual(len(kinds), 12)
                self.assertLessEqual(kinds.count('set'), 1)
                if 'set' in kinds: self.assertEqual(kinds[0], 'set')
                self.assertLessEqual(kinds.count('observe'), 1)
                if 'observe' in kinds: self.assertEqual(kinds[-1], 'observe')
                missing = sum(bit is None for row in case['observations'][1:] for bit in row.values())
                self.assertLessEqual(missing, 3)
                self.assertLessEqual((2 ** missing) * (2 ** len(case['ids'])), 512)
                self.assertTrue(all(set(row) == set(case['ids']) for row in case['coverage']))
                if metadata[case['episode']]['family'] == 'two_contacts':
                    contacts = [a['participants'] for a in case['actions'] if a['kind'] == 'contact']
                    templates.add(contacts[0] == contacts[1])
        self.assertEqual(templates, {False, True})

    def test_mode_choice_happens_after_blueprint_acceptance(self):
        config = data.read_config()
        config['entity_counts'] = [3]
        config['draws_per_family_entity'] = dict.fromkeys(data.SPLITS, 1)
        real_rng = data._rng
        class Mode:
            def __init__(self, value): self.value = value
            def randrange(self, bound): return self.value
        def with_mode(value):
            return lambda label, material: Mode(value) if label == 'hidden-mode-v1' else real_rng(label, material)
        with patch.object(data, '_rng', side_effect=with_mode(0)): zero = data.build_assets(config)
        with patch.object(data, '_rng', side_effect=with_mode(1)): one = data.build_assets(config)
        for split in data.SPLITS:
            a, b = zero['splits'][split], one['splits'][split]
            for left, right in zip(a['cases'], b['cases'], strict=True):
                self.assertEqual({k: v for k, v in left.items() if k != 'hidden_source_slot'},
                                 {k: v for k, v in right.items() if k != 'hidden_source_slot'})
            self.assertEqual([data.blueprint_digest(c) for c in a['inputs']['episodes']],
                             [data.blueprint_digest(c) for c in b['inputs']['episodes']])

    def test_config_rejects_historical_seeds_changed_law_and_unbounded_work(self):
        def rejected(change):
            config = data.read_config(); change(config)
            with self.assertRaises(ValueError): data.validate_config(config)
        for change in (
            lambda c: c['split_seeds'].update(train=401),
            lambda c: c['split_seeds'].update(train=c['split_seeds']['evaluation']),
            lambda c: c['split_seeds'].update(train=True),
            lambda c: c['draws_per_family_entity'].update(train=0),
            lambda c: c.update(entity_counts=[3, 3]),
            lambda c: c.update(max_cumulative_missing_bits=4),
            lambda c: c.update(max_blueprint_attempts=10001),
            lambda c: c.update(max_actions=12.0),
            lambda c: c['information_law'].update(hidden_source_slot_prior=[1.0, 0.0]),
            lambda c: c['execution_policy'].update(research_fit_enabled=True),
            lambda c: c.update(extra='undeclared'),
        ): rejected(change)
        for split in data.SPLITS:
            with self.subTest(increased_split=split):
                rejected(lambda c: c['draws_per_family_entity'].__setitem__(
                    split, c['draws_per_family_entity'][split] + 1))

    def test_duplicate_exhaustion_fails_instead_of_shortening_inventory(self):
        config = data.read_config()
        config['entity_counts'] = [3]
        config['draws_per_family_entity'] = dict.fromkeys(data.SPLITS, 1)
        config['max_blueprint_attempts'] = 1
        candidate = deepcopy(self.bundle['splits']['train']['inputs']['episodes'][0])
        with patch.object(data, '_candidate', return_value=candidate), \
             self.assertRaisesRegex(ValueError, 'unique blueprint budget exhausted'):
            data.build_assets(config)


if __name__ == '__main__':
    unittest.main()
