"""Archived physical input checks only. No G4 policy fitting or challenge scoring."""
from collections import Counter, defaultdict
from pathlib import Path
import tempfile
import unittest

from experiments.predictive_nucleus import communication_world as world


class CommunicationWorldTests(unittest.TestCase):
    def test_physical_menus_and_held_out_rosters(self):
        inventories = {'nand': (63, 66), 'nor': (66, 30)}
        for law, (train, held) in inventories.items():
            cases = world.load_cases(law, 7)
            self.assertEqual(Counter(c['family'] for c in cases),
                             {'path_return4': train, 'branch_return5': held})
            self.assertEqual(len({c['id'] for c in cases}), len(cases))
            rosters, changed = defaultdict(set), defaultdict(set)
            for c in cases:
                rosters[c['family']].update(c['entities'])
                self.assertEqual([w['reading'] for w in c['witness']], [0, 1])
                self.assertNotEqual(c['witness'][0]['id'], c['witness'][1]['id'])
                self.assertEqual(c['rewards'][0], c['rewards'][1][::-1])
                self.assertEqual(sum(c['rewards'][0]), 1)
                self.assertEqual(len({i for row in c['episodes'] for i in row}), 4)
                changed[c['family'], tuple(c['episodes'][0])].add(tuple(c['rewards'][0]))
            self.assertTrue(rosters['path_return4'].isdisjoint(rosters['branch_return5']))
            for family in rosters:
                self.assertTrue(any(len(rows) == 2 for (name, _), rows in changed.items() if name == family))

    def test_world_probability_and_reward_are_separate(self):
        case = world.load_cases('nand', 7)[0]
        tape = world.io._read(world.DATA / 'nand-inputs.json.xz')
        trace = world.io._read(world.TRACES / 'trace-nand-7-grounded-fresh.json.xz')
        records = {r['id']: r for r in tape['episodes']}
        final = {(p['id'], p['step']): p for p in trace['points'] if p['view'] == 'canonical'}
        for h, row in enumerate(case['episodes']):
            for a, identity in enumerate(row):
                r = records[identity]
                before = r['utterances'][-2]['reading'].copy()
                for i, bit in zip(case['participants'], case['goal'], strict=True):
                    before[i] = bit
                target = int(''.join(map(str, before)), 2)
                logp = final[identity, len(r['utterances']) - 1]['logp'][target]
                self.assertEqual(case['predicted'][h][a], world.math.exp(logp))
                self.assertEqual(case['rewards'][h][a], int(r['utterances'][-1]['reading'] == before))
                self.assertEqual(case['witness'][h]['reading'], r['context'][0]['reading'][0])
                self.assertEqual(case['texts'][a], r['utterances'][-1]['text'])

    def test_archive_binding_and_unregistered_conditions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'evidence.json'
            path.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'archive hash differs'):
                world._bound(path, '0' * 64)
        for law, seed in [('nor', True), ('invented', 7), ('nand', 3)]:
            with self.assertRaisesRegex(ValueError, 'unknown G3 condition'):
                world.load_cases(law, seed)
