"""Generator/oracle boundaries and whole-family transfer; no learned model runs."""
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import product
import subprocess
import sys
import unittest

from experiments.predictive_nucleus import bilingual_data as data
from experiments.predictive_nucleus.bilingual_contract import validate_inputs
from experiments.predictive_nucleus.acceptance_contract import digest


def config():
    return {'version': 'bilingual-data-tests-v1', 'data': {
        'split_seeds': {'train': 20261031971, 'challenge': 20261031973},
        'train_entity_counts': [3, 4], 'challenge_entity_counts': [3, 4, 5, 6]}}


def reference(before, action, mode, law):
    """Truth-table indexing is independent of the generator's Boolean formula."""
    after = list(before)
    kind, first, second, value = action
    if kind == 1:
        after[first] = value
    else:
        members = (first, second); source, target = members[mode], members[1 - mode]
        table = (1, 1, 1, 0) if law == 'nand' else (1, 0, 0, 0)
        after[target] = table[2 * before[source] + before[target]]
    return after


class BilingualDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = data.build_assets(config())

    def banks(self):
        return [('train', 'nand', self.assets['train']),
                *[('challenge', law, bank) for law, bank in self.assets['challenge'].items()]]

    def test_deterministic_inventory_and_disjoint_families(self):
        settings = config(); before = deepcopy(settings)
        self.assertEqual(self.assets, data.build_assets(settings)); self.assertEqual(settings, before)
        audit = self.assets['audit']
        self.assertEqual((audit['train']['episodes'], audit['train']['forecasts'], audit['train']['lineages']), (256, 384, 16))
        for law in data.LAWS:
            self.assertEqual(tuple(audit[law][key] for key in ('episodes', 'forecasts', 'lineages', 'physical_trajectories')),
                             (576, 2080, 36, 144))
            self.assertEqual(set(audit[law]['families']), {'chain', 'fork', 'cycle', 'repeated', 'disjoint'})
        self.assertEqual(audit['split_overlap'], {'entity_names': 0, 'lineages': 0, 'whole_families': 0})
        self.assertFalse(set(data.FAMILIES['train']) & set(data.FAMILIES['challenge']))

    def test_complete_context_and_independent_future_counterfactuals(self):
        for _, law, bank in self.banks():
            self.assertEqual(bank['oracle']['input_sha256'], digest(bank['inputs']))
            for episode, gold in zip(bank['inputs']['episodes'], bank['oracle']['episodes'], strict=True):
                state = list(episode['anchor']); n = len(state)
                self.assertEqual(len(episode['context']), n + 1)
                self.assertEqual(episode['context'][0]['action'], [0, 0, 1, -1])
                survivors = []
                for mode in (0, 1):
                    if reference(state, episode['context'][0]['action'], mode, law) == episode['context'][0]['reading']:
                        survivors.append(mode)
                self.assertEqual(survivors, [gold['mode']])
                for event in episode['context']:
                    state = reference(state, event['action'], gold['mode'], law)
                    self.assertEqual(event['reading'], state)
                self.assertEqual(state, gold['initial_bits'])
                for t, (event, action) in enumerate(zip(episode['utterances'], gold['actions'], strict=True)):
                    reversed_action = [0, action[2], action[1], -1]
                    self.assertEqual(gold['opposite_truth'][t], reference(state, reversed_action, gold['mode'], law))
                    predicted = reference(state, action, gold['mode'], law)
                    self.assertEqual(event['reading'], predicted); self.assertEqual(gold['truth'][t], predicted)
                    target = action[1:3][1 - gold['mode']]
                    self.assertTrue(all(state[i] == predicted[i] for i in range(n) if i != target))
                    state = predicted

    def test_roles_are_evaluator_only_and_realization_is_genuinely_different(self):
        for split, _, bank in self.banks():
            for episode, gold in zip(bank['inputs']['episodes'], bank['oracle']['episodes'], strict=True):
                self.assertEqual(set(episode), {'id', 'entities', 'anchor', 'context', 'utterances'})
                ids = episode['entities']
                for t, (event, action) in enumerate(zip(episode['utterances'], gold['actions'], strict=True)):
                    self.assertEqual(set(event), {'text', 'reading'})
                    tokens = event['text'].split(); first, second = action[1:3]
                    wanted = [ids[first], gold['lexemes'][t], ids[second]] if gold['language'] == 'svo' else [ids[second], ids[first], gold['lexemes'][t]]
                    self.assertEqual(tokens, wanted)
                    mentions = [ids.index(token) for token in tokens if token in ids]
                    self.assertEqual(mentions[gold['action_orders'][t]], first)
                expected = 1 if split == 'train' else min(2, len(episode['utterances']))
                self.assertEqual(len(set(gold['lexemes'])), expected)

    def test_bilingual_synonym_twins_and_reversals_share_whole_lineages(self):
        for _, _, bank in self.banks():
            physical, roles, lineages = defaultdict(list), defaultdict(list), defaultdict(set)
            for episode, gold in zip(bank['inputs']['episodes'], bank['oracle']['episodes'], strict=True):
                physical[gold['physical_id']].append((episode, gold))
                roles[gold['role_pair_id']].append((episode, gold))
                lineages[gold['lineage']].add((gold['mode'], gold['direction'], gold['language'], gold['synonym']))
            self.assertTrue(all(rows == set(product((0, 1), (0, 1), data.LEXEMES, (0, 1))) for rows in lineages.values()))
            for twins in physical.values():
                self.assertEqual(len(twins), 4)
                first, reference_gold = twins[0]
                for episode, gold in twins[1:]:
                    for key in ('entities', 'anchor', 'context'): self.assertEqual(episode[key], first[key])
                    for key in ('actions', 'truth', 'opposite_truth'): self.assertEqual(gold[key], reference_gold[key])
            for twins in roles.values():
                self.assertEqual(len(twins), 2)
                (a, x), (b, y) = sorted(twins, key=lambda pair: pair[1]['direction'])
                self.assertEqual(a['context'], b['context']); self.assertEqual(a['entities'], b['entities'])
                self.assertEqual(y['actions'], [[0, r[2], r[1], -1] for r in x['actions']])

    def test_cross_law_transfer_keeps_ids_language_and_context_exposure(self):
        a, b = [self.assets['challenge'][law] for law in data.LAWS]
        contrast_count = 0
        for x, y, gx, gy in zip(a['inputs']['episodes'], b['inputs']['episodes'], a['oracle']['episodes'], b['oracle']['episodes'], strict=True):
            for key in ('id', 'entities', 'anchor', 'context'): self.assertEqual(x[key], y[key])
            self.assertEqual([r['text'] for r in x['utterances']], [r['text'] for r in y['utterances']])
            for key in ('lineage', 'actions', 'mode', 'direction'): self.assertEqual(gx[key], gy[key])
            contrast_count += sum(p != q for p, q in zip(gx['truth'], gy['truth'], strict=True))
        self.assertGreater(contrast_count, 0)

    def test_input_boundary_rejects_gold_and_malformed_readings(self):
        original = {'version': 'bilingual-input-v1', 'episodes': [deepcopy(self.assets['train']['inputs']['episodes'][0])]}
        changes = [lambda x: x.update(law='nand'), lambda x: x['episodes'][0].update(mode=0),
            lambda x: x['episodes'][0]['utterances'][0].update(action=[0, 0, 1, -1]),
            lambda x: x['episodes'][0]['context'][0].update(mode=0),
            lambda x: x['episodes'][0]['utterances'][0]['reading'].__setitem__(0, None),
            lambda x: x['episodes'][0]['utterances'][0]['reading'].__setitem__(0, True),
            lambda x: x['episodes'][0]['context'][0].__setitem__('action', [0, 0, 0, -1]),
            lambda x: x['episodes'][0]['utterances'][0].__setitem__('text', 'unseen contacts ungrounded')]
        for mutate in changes:
            bad = deepcopy(original); mutate(bad)
            with self.assertRaises(ValueError): validate_inputs(bad)
        valid = validate_inputs(original); valid['episodes'][0]['anchor'][0] = 1
        self.assertEqual(original['episodes'][0]['anchor'][0], 0)
        bad = config(); bad['data']['split_seeds']['challenge'] = bad['data']['split_seeds']['train']
        with self.assertRaises(ValueError): data.build_assets(bad)

    def test_runtime_validation_import_has_no_generator_or_physics(self):
        subprocess.run([sys.executable, '-c',
            "import sys; from experiments.predictive_nucleus.bilingual_contract import validate_inputs; "
            "assert not any(name.endswith(('bilingual_data', 'multisource_law_oracle')) for name in sys.modules)"],
            check=True, capture_output=True)


if __name__ == '__main__': unittest.main()
