"""Synthetic tables test custody and conditional arithmetic, not real challenge rows."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

import numpy as np
import torch

from experiments.predictive_nucleus import selective_memory_data_v1 as data
from experiments.predictive_nucleus.temporal_native_models_v1 import receipt


def fixture(split='test'):
    context = {'split': split, 'law': 'synthetic', 'mode': 0, 'old': [1, 2],
               'target_scope': ['local', 'sibling'], 'a': [0, 3], 'b': [2, 1],
               'start': 0, 'ticket': 'synthetic-selective-context'}
    # Distinct generic translations retain a spectator bit and identify all
    # four old operations. This is not a sampled NAND/NOR challenge context.
    table = [[(state + 2 * op) % 8 for state in range(8)] for op in range(4)]
    return context, table


def basis(rows):
    result = {}
    for row in rows:
        queries = [r['query'] for r in row['base'] + row['probes']] + row['targets']
        for query in queries:
            value = np.arange(1, 33, dtype=np.float64).reshape(4, 8)
            value /= value.sum(-1, keepdims=True)
            result[query['native_key']] = {'likelihood': value.tolist()}
    return result


class SelectiveMemoryDataTests(unittest.TestCase):
    def test_joint_population_and_disjoint_receipt_structures(self):
        context, table = fixture()
        test, private = data.context_rows(context, table)
        train, _ = data.context_rows({**context, 'split': 'train'}, table, False)
        self.assertEqual(len(test), 144)
        self.assertEqual(data.Counter(r['persistent_change_mask'] for r in private),
                         {0: 36, 1: 36, 2: 36, 3: 36})
        self.assertEqual([r['query']['word'] for r in test[0]['probes']], [0, 1, 1, 0])
        self.assertEqual([r['query']['word'] for r in train[0]['probes']], [0, 1, 0, 1])
        self.assertNotIn('target_y', test[0])
        self.assertIn('target_y', train[0])
        self.assertEqual(private[0]['old'], [1, 2])
        self.assertEqual([q['word'] for q in test[0]['targets']], [0, 1])
        for row in test:
            for probe in row['probes']:
                q = probe['query']
                self.assertNotEqual(q['before'][:2], row['targets'][q['word']]['before'][:2])
        # Hidden alternatives share every public query/identity descriptor.
        self.assertEqual(test[0]['targets'], test[-1]['targets'])
        self.assertEqual([r['query'] for r in test[0]['base']], [r['query'] for r in test[-1]['base']])

    def test_conditional_support_uses_observations_not_hidden_masks(self):
        public, rows = data.context_rows(*fixture())
        for i, row in enumerate(rows):
            observed = [r['endpoint'] for r in public[i]['base'][8:] + public[i]['probes']]
            for stage, count in (('claims', 2), ('pair', 4), ('third', 5), ('final', 6)):
                matching = [j for j, p in enumerate(public)
                            if [r['endpoint'] for r in p['base'][8:] + p['probes']][:count]
                            == observed[:count]]
                for word in range(2):
                    expected = [sum(rows[j]['target_y'][word] == y for j in matching) / len(matching)
                                for y in range(8)]
                    self.assertEqual(row['distributions'][stage][word], expected)
                    self.assertGreater(expected[row['target_y'][word]], 0)
            # Oracle optional forecasts condition on one answer only.
            for key in ('optional', 'cleared_optional'):
                view = row[key]
                for word in range(2):
                    self.assertEqual(view['after'][word], view['branches'][word][view['answer'][word]])
                    self.assertGreater(view['probe'][word][view['answer'][word]], 0)
                    total = np.zeros(8)
                    for probability, branch in zip(view['probe'][word], view['branches'][word]):
                        if probability:
                            total += probability * np.asarray(branch)
                        else:
                            self.assertIsNone(branch)
                    np.testing.assert_allclose(total, view['before'][word], atol=1e-14, rtol=0)
        # More than one hidden semantic mask occurs under the same claim prefix.
        groups = {}
        for row, p in zip(rows, public):
            key = tuple(r['endpoint'] for r in p['base'][8:])
            groups.setdefault(key, []).append(row)
        self.assertTrue(any(len({r['target_change_mask'] for r in g}) > 1 for g in groups.values()))

    def test_scope_specific_retention_and_old_identifiability(self):
        _, rows = data.context_rows(*fixture())
        pair = next(row for row in rows if row['causes'] == ['local_correction', 'local_correction'])
        self.assertEqual(pair['persistent_change_mask'], 3)
        self.assertEqual(pair['target_change_mask'], 1)
        context, table = fixture()
        table[2] = table[1]
        with self.assertRaisesRegex(ValueError, 'identify old'):
            data.context_rows(context, table)

    def test_features_equal_frozen_receipt_contract_and_ignore_metadata(self):
        rows, _ = data.context_rows(*fixture('train'), include_oracle=False)
        rows = rows[:2]
        native = basis(rows)
        packed = data.tensorize(rows, native)
        self.assertEqual(tuple(packed['base'].shape), (2, 10, 18))
        self.assertEqual(tuple(packed['probe_q'].shape), (2, 4, 41))
        for i, row in enumerate(rows):
            for position, r in enumerate(row['base']):
                q = r['query']
                vector = sum(native[q['native_key']]['likelihood'], []) + q['before']
                vector += [int(q['scope'] == s) for s in ('parent', 'local', 'sibling')]
                vector += [q['time']] + [int(q['word'] == w) for w in (0, 1)]
                self.assertTrue(torch.equal(packed['base'][i, position], receipt(vector, r['endpoint'], r['source'])))
        renamed = deepcopy(rows)
        for row in renamed:
            row['id'] += '-renamed'
            row['private_change_mask'] = 'ignored metadata, never encoded'
            for r in row['base'] + row['probes']:
                r['query']['evidence_id'] += '-renamed'
                r['query']['entities'] = ['fresh-a', 'fresh-b', 'fresh-c']
        again = data.tensorize(renamed, native)
        self.assertTrue(all(torch.equal(value, again[key]) for key, value in packed.items()))
        test_rows = deepcopy(rows)
        for row in test_rows:
            del row['target_y']
        self.assertNotIn('target_y', data.tensorize(test_rows, native))

    def test_duplicate_receipts_and_conflicting_identity(self):
        rows, _ = data.context_rows(*fixture('train'), include_oracle=False)
        row = rows[0]
        native = basis([row])
        expected = data.tensorize([row], native)
        replay = deepcopy(row)
        replay['base'].append(deepcopy(replay['base'][0]))
        replay['probes'].insert(0, deepcopy(replay['base'][0]))
        actual = data.tensorize([replay], native)
        self.assertTrue(all(torch.equal(value, actual[key]) for key, value in expected.items()))
        replay['base'][-1]['endpoint'] = (replay['base'][-1]['endpoint'] + 1) % 8
        with self.assertRaisesRegex(ValueError, 'conflicting evidence'):
            data.tensorize([replay], native)

    def test_streamed_canonical_serialization(self):
        value = {'z': [0, 1, None], 'a': {'probability': .25}}
        with tempfile.TemporaryDirectory() as name:
            for suffix in ('.json', '.json.xz'):
                path = Path(name) / ('sample' + suffix)
                data.write(path, value)
                raw = path.read_bytes()
                if suffix.endswith('.xz'):
                    raw = data.lzma.decompress(raw)
                self.assertEqual(raw, data.encoded(value))
                self.assertEqual(data.read(path), value)


if __name__ == '__main__':
    unittest.main()
