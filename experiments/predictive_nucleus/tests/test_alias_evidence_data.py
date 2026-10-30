"""Matched evidence, prospective selection and fresh self queries; no fitting."""
from collections import Counter
from copy import deepcopy
from unittest.mock import patch
import unittest

from experiments.predictive_nucleus import alias_evidence_data as data
from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import continuation_data as continuation
from experiments.predictive_nucleus.prospective_data import blueprint_digest, _realize


def config():
    return {'version': 'alias-evidence-v1', 'data': {'entity_counts': [3, 4, 5, 6],
        'split_seeds': dict(zip(continuation.SPLITS, range(20261030021, 20261030025))),
        'draws_per_cell': {'train': 8, 'selection': 4, 'calibration': 4, 'evaluation': 4},
        'max_blueprint_attempts': 10000}}


class AliasEvidenceDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = data.build_assets(config())

    def test_reproducible_complete_inventory_without_mutating_config(self):
        settings = config(); original = deepcopy(settings)
        self.assertEqual(data.build_assets(settings), self.assets)
        self.assertEqual(settings, original)
        self.assertEqual(self.assets['audit']['evaluation']['continuation_queries'], 704)
        self.assertEqual(len(self.assets['splits']['evaluation']['cases']), 320)
        audit = self.assets['alias_training']['audit']
        self.assertEqual(len(audit['replaced_episodes']), 16)
        self.assertEqual(audit['baseline_exposure'], audit['alias_exposure'])
        self.assertEqual(set(audit['self_prebit_counts'].values()), {2})
        self.assertEqual(len(audit['self_prebit_counts']), 8)

    def test_only_selected_contacts_and_their_observed_consequences_change(self):
        baseline, alias = self.assets['splits']['train'], self.assets['alias_training']
        selected = set(alias['audit']['replaced_episodes'])
        modes = {r['episode']: r['hidden_source_slot'] for r in alias['cases']}
        for left, right in zip(baseline['inputs']['episodes'], alias['inputs']['episodes'], strict=True):
            if left['episode'] not in selected:
                self.assertEqual(left, right); continue
            for key in ('episode', 'ids', 'coverage'): self.assertEqual(left[key], right[key])
            self.assertEqual(left['observations'][0], right['observations'][0])
            t, before = data._precontact(left)
            self.assertEqual(set(before), {0, 1})
            expected = deepcopy(left)
            who = expected['actions'][t]['participants'][0]
            expected['actions'][t]['participants'] = [who, who]
            _realize(expected, modes[left['episode']])
            self.assertEqual(expected, right)
        for n in (3, 4, 5, 6):
            candidates = [r['lineage'] for r, c in zip(baseline['cases'], baseline['inputs']['episodes'], strict=True)
                if r['family'] == 'single_contact' and r['entities'] == n and r['direction'] == 0 and
                len(set(data._precontact(c)[1])) == 2]
            self.assertEqual(alias['audit']['selected_lineages'][str(n)], candidates[:2])

    def test_evaluation_self_is_balanced_identifiable_and_disjoint_from_all_development(self):
        development = {blueprint_digest(c) for split in ('train', 'selection', 'calibration')
            for c in self.assets['splits'][split]['inputs']['episodes']}
        development.update(blueprint_digest(c) for c in self.assets['alias_training']['inputs']['episodes'])
        evaluation = self.assets['splits']['evaluation']
        inputs = evaluation['inputs']; contract.validate_inputs(inputs)
        gold = contract.validate_oracle(evaluation['oracle'], inputs,
            {'oracle_sha256': contract.digest(evaluation['oracle']),
             'oracle_source_sha256': evaluation['oracle']['source_sha256'],
             'information_law_sha256': evaluation['oracle']['information_law_sha256']})
        counts, seen = Counter(), set()
        for meta, case in zip(evaluation['cases'], inputs['episodes'], strict=True):
            if meta['family'] != 'self_contact': continue
            t, pre = data._precontact(case); fingerprint = blueprint_digest(case)
            self.assertEqual(pre, (meta['self_prebit'],) * 2)
            self.assertEqual(meta['partition'], 'in_family')
            self.assertEqual(len(gold[case['episode']]['possible_worlds'][t]), 1)
            self.assertNotIn(fingerprint, development | seen); seen.add(fingerprint)
            counts[len(case['ids']), pre[0]] += 1
        self.assertEqual(counts, Counter({(n, b): 2 for n in range(3, 7) for b in (0, 1)}))
        self.assertEqual(self.assets['audit']['fresh_self']['prior_self_blueprint_overlap'], 0)

    def test_mode_never_changes_selection_query_blueprint_or_balancing(self):
        rng = continuation._rng
        class FixedMode:
            def __init__(self, mode): self.mode = mode
            def randrange(self, bound): return self.mode
        settings = config(); settings['data']['entity_counts'] = [3]
        versions = []
        for mode in (0, 1):
            with patch.object(continuation, '_rng', side_effect=lambda label, material, m=mode:
                FixedMode(m) if label in ('continuation-hidden-mode-v1', 'alias-hidden-mode-v1') else rng(label, material)):
                versions.append(data.build_assets(settings))
        for group in (*continuation.SPLITS, 'alias_training'):
            left, right = [a[group] if group == 'alias_training' else a['splits'][group] for a in versions]
            self.assertEqual([blueprint_digest(c) for c in left['inputs']['episodes']],
                             [blueprint_digest(c) for c in right['inputs']['episodes']])
            self.assertEqual([{k: v for k, v in r.items() if k != 'hidden_source_slot'} for r in left['cases']],
                             [{k: v for k, v in r.items() if k != 'hidden_source_slot'} for r in right['cases']])

    def test_wrong_seed_inventory_fails(self):
        settings = config(); settings['data']['split_seeds']['train'] -= 1
        with self.assertRaisesRegex(ValueError, 'split seeds'): data.build_assets(settings)


if __name__ == '__main__': unittest.main()
