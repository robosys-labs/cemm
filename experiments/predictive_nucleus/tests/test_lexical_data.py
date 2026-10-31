"""Fixed-layout word contrasts, observed-only training and independent physics."""
from collections import Counter, defaultdict
from copy import deepcopy
import json
import lzma
from unittest import mock
import unittest

from experiments.predictive_nucleus import lexical_data as data
from experiments.predictive_nucleus import bilingual_data as previous
from experiments.predictive_nucleus.acceptance_contract import digest
from experiments.predictive_nucleus.bilingual_contract import validate_inputs


def config():
    return {'version': 'lexical-data-tests-v1', 'data': {
        'split_seeds': {'train': 20261031983, 'challenge': 20261031989},
        'train_entity_counts': [3, 4], 'challenge_entity_counts': [3, 4, 5, 6]}}


def reference(before, action, mode, law):
    after = list(before)
    source, target = action[1:3][mode], action[1:3][1 - mode]
    table = ((1, 1), (1, 0)) if law == 'nand' else ((1, 0), (0, 0))
    after[target] = table[before[source]][before[target]]
    return after


class LexicalDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.assets = data.build_assets(config())

    def test_inventory_reproducibility_and_exact_observed_rehearsal(self):
        settings = config(); original = deepcopy(settings)
        self.assertEqual(self.assets, data.build_assets(settings)); self.assertEqual(settings, original)
        train, audit = self.assets['train'], self.assets['audit']
        self.assertEqual(set(train), {'inputs'})
        self.assertEqual(audit['train']['episodes'], 640); self.assertEqual(audit['train']['forecasts'], 768)
        self.assertEqual(audit['fresh_training']['episodes'], 384)
        self.assertEqual(audit['fresh_training']['forecasts'], 384)
        self.assertEqual(audit['fresh_training']['lexical_pairs'], 192)
        self.assertEqual(audit['layout_diagnostic']['borrowed_training_episodes'], 128)
        exposures = audit['training_semantic_exposures']
        self.assertEqual(exposures['rehearsal'], {'direct': 384, 'inverse': 0})
        self.assertEqual(exposures['fresh'], {'direct': 192, 'inverse': 192})
        self.assertEqual(exposures['total'], {'direct': 576, 'inverse': 192})
        old = json.loads(lzma.decompress(data.REHEARSAL.read_bytes()))
        self.assertEqual(train['inputs']['episodes'][:256], old['episodes'])
        self.assertTrue(all(len(e['utterances']) == 1 for e in train['inputs']['episodes'][256:]))
        for law in previous.LAWS:
            self.assertEqual(tuple(audit[law][k] for k in ('episodes', 'forecasts', 'lexical_pairs')), (1152, 4160, 576))
            self.assertEqual(audit[law]['families'], {'chain': 192, 'fork': 256, 'cycle': 256, 'repeated': 256, 'disjoint': 192})
        self.assertEqual(audit['split_overlap'], {'entity_names': 0, 'fresh_lineages': 0, 'whole_families': 0})
        with mock.patch.object(data.REHEARSAL.__class__, 'read_bytes', return_value=b'changed'):
            with self.assertRaises(ValueError): data.build_assets(config())

    def test_final_pairs_hold_all_history_names_and_positions_fixed(self):
        for law, bank in self.assets['challenge'].items():
            pairs = defaultdict(list)
            for episode, gold in zip(bank['inputs']['episodes'], bank['oracle']['episodes'], strict=True):
                pairs[gold['lexical_pair_id']].append((episode, gold))
                self.assertEqual(gold['shared_prefix_sha256'], digest(data.shared_prefix(episode)))
                self.assertEqual(gold['contrast_step'], len(episode['utterances']) - 1)
            self.assertEqual(len(pairs), 576)
            for twins in pairs.values():
                self.assertEqual(len(twins), 2)
                (a, x), (b, y) = sorted(twins, key=lambda pair: pair[1]['effect_polarity'])
                self.assertEqual((x['effect_polarity'], y['effect_polarity']), (0, 1))
                self.assertEqual(data.shared_prefix(a), data.shared_prefix(b))
                self.assertEqual((x['counterpart_id'], y['counterpart_id']), (b['id'], a['id']))
                self.assertEqual(data.swap_lexeme(a['utterances'][-1]['text'], a['entities']), b['utterances'][-1]['text'])
                self.assertEqual(y['actions'][-1], [0, x['actions'][-1][2], x['actions'][-1][1], -1])
                self.assertNotEqual(x['truth'][-1], y['truth'][-1])
                self.assertEqual(x['truth'][-1], y['opposite_truth'][-1])
                self.assertEqual(y['truth'][-1], x['opposite_truth'][-1])
                # A constant current-word view makes both complete predictor
                # inputs identical while their targets differ: at most one MAP
                # forecast can be correct, regardless of position/frequency.
                self.assertEqual(x['shared_prefix_sha256'], y['shared_prefix_sha256'])

    def test_fresh_physics_orders_and_realized_unchanged_bits(self):
        for law, bank in self.assets['challenge'].items():
            self.assertEqual(bank['oracle']['input_sha256'], digest(bank['inputs']))
            phases = defaultdict(set)
            for episode, gold in zip(bank['inputs']['episodes'], bank['oracle']['episodes'], strict=True):
                pre = episode['context'][-1]['reading']; ids = episode['entities']
                phase = gold['initial_bits'][gold['canonical_slots'][0]]
                phases[(gold['family'], len(ids))].add(phase)
                self.assertEqual(gold['effect_sequence'][:-1], [(phase + t) % 2 for t in range(len(gold['actions']) - 1)])
                for t, (event, action) in enumerate(zip(episode['utterances'], gold['actions'], strict=True)):
                    after = reference(pre, action, gold['mode'], law)
                    reverse = reference(pre, [0, action[2], action[1], -1], gold['mode'], law)
                    self.assertEqual(event['reading'], after); self.assertEqual(gold['truth'][t], after)
                    self.assertEqual(gold['opposite_truth'][t], reverse)
                    mentions = [ids.index(token) for token in event['text'].split() if token in ids]
                    self.assertEqual(mentions[gold['action_orders'][t]], action[1])
                    target = action[1:3][1 - gold['mode']]
                    self.assertTrue(all(pre[i] == after[i] for i in range(len(ids)) if i != target))
                    pre = after
            self.assertTrue(all(values == {0, 1} for values in phases.values()))

    def test_shared_word_training_and_held_out_word_layout_combinations(self):
        positions = defaultdict(set)
        for episode in self.assets['train']['inputs']['episodes']:
            for event in episode['utterances']:
                for i, word in enumerate(event['text'].split()):
                    if word not in episode['entities']: positions[word].add(i)
        for word in ('contacts', 'receives', 'dax', 'vok'): self.assertEqual(positions[word], {1, 2})
        for word in ('touches', 'accepts'): self.assertEqual(positions[word], {1})
        for word in ('mip', 'nuz'): self.assertEqual(positions[word], {2})
        for bank in self.assets['challenge'].values():
            for episode, gold in zip(bank['inputs']['episodes'], bank['oracle']['episodes'], strict=True):
                text = episode['utterances'][-1]['text']; ids = episode['entities']
                borrowed = data.borrow_lexeme(text, ids).split()
                index = next(i for i, word in enumerate(borrowed) if word not in ids)
                self.assertEqual(index in positions[borrowed[index]], gold['contrast_synonym'] == 0)
                self.assertEqual(data.borrow_lexeme(' '.join(borrowed), ids), text)

    def test_unchanged_character_features_distinguish_all_eight_words(self):
        from experiments.predictive_nucleus.bilingual_model import tokenize_batch
        words = sorted(data.SWAPS)
        features, mentions = tokenize_batch([f'A {word} B' for word in words], [['A', 'B', 'C']] * len(words))
        vectors = {tuple(row) for row in features[:, 1, 1:].tolist()}
        self.assertEqual(len(words), 8); self.assertEqual(len(vectors), 8)
        self.assertNotIn((0.,) * 8, vectors)
        self.assertEqual(mentions.tolist(), [[0, 1]] * 8)

    def test_bilingual_synonym_role_and_law_pairing_remains_coherent(self):
        for bank in self.assets['challenge'].values():
            for key in ('bilingual_pair_id', 'synonym_pair_id', 'role_pair_id'):
                groups = defaultdict(list)
                for episode, gold in zip(bank['inputs']['episodes'], bank['oracle']['episodes'], strict=True):
                    groups[gold[key]].append((episode, gold))
                self.assertEqual(len(groups), 576)
                for twins in groups.values():
                    self.assertEqual(len(twins), 2)
                    (a, x), (b, y) = twins
                    self.assertEqual(a['context'], b['context']); self.assertEqual(a['entities'], b['entities'])
                    if key == 'role_pair_id':
                        self.assertEqual(x['actions'], [[0, r[2], r[1], -1] for r in y['actions']])
                    else:
                        self.assertEqual(x['actions'], y['actions']); self.assertEqual(x['truth'], y['truth'])
        a, b = [self.assets['challenge'][law] for law in previous.LAWS]
        for x, y in zip(a['inputs']['episodes'], b['inputs']['episodes'], strict=True):
            for key in ('id', 'entities', 'anchor', 'context'): self.assertEqual(x[key], y[key])
            self.assertEqual([e['text'] for e in x['utterances']], [e['text'] for e in y['utterances']])

    def test_training_has_no_gold_envelope_and_helpers_reject_unknown_words(self):
        inputs = self.assets['train']['inputs']
        self.assertEqual(inputs, validate_inputs(inputs))
        bad = deepcopy(inputs); bad['episodes'][0]['utterances'][0]['effect_polarity'] = 0
        with self.assertRaises(ValueError): validate_inputs(bad)
        for helper in (data.swap_lexeme, data.borrow_lexeme):
            with self.assertRaises(ValueError): helper('A unknown B', ['A', 'B', 'C'])
            with self.assertRaises(ValueError): helper('A contacts ungrounded', ['A', 'B', 'C'])


if __name__ == '__main__': unittest.main()
