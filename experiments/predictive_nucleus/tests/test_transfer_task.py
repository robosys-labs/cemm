import unittest
from collections import Counter

from experiments.predictive_nucleus import transfer_task as task


class TransferTaskTests(unittest.TestCase):
    def test_sender_visible_and_structural_holdouts(self):
        for law in ('nand', 'nor'):
            audit = task.split_audit(law)
            p = audit['partitions']
            self.assertEqual(p['train']['bilinear_contrast_rank'], 16)
            self.assertEqual([p[k]['signatures'] for k in ('train', 'recombined', 'fresh')], [256, 128, 128])
            self.assertEqual(set(p['train']['badges']), set(p['recombined']['badges']))
            self.assertTrue(set(p['train']['badges']).isdisjoint(p['fresh']['badges']))
            self.assertFalse(any(audit['physical_overlap'].values()))

    def test_train_exploration_is_not_confounded_by_action_order(self):
        rows = iter(task.rounds('nand', 7, 'train'))
        cells = 0
        for first in rows:
            second, third, fourth = (next(rows) for _ in range(3))
            self.assertEqual([first['rep'], second['rep'], third['rep'], fourth['rep']], [0, 1, 2, 3])
            self.assertEqual(first['matrix'], second['matrix'])
            self.assertEqual(third['matrix'], fourth['matrix'])
            self.assertNotEqual(first['menu_reversed'], third['menu_reversed'])
            cells += 1
        self.assertEqual(cells, 1536)

    def test_round_identity_menu_order_and_donor(self):
        bank = task.catalogue('nand', 'challenge')
        rows = {r['id']: r for r in task.rounds('nand', 7, 'challenge')}
        self.assertEqual(Counter(r['partition'] for r in rows.values()), {'recombined': 3072, 'fresh': 3072})
        self.assertEqual(set(rows), {r['donor'] for r in rows.values()})
        for r in rows.values():
            pair = bank['sites'][r['pair_id']]
            i = r['badge_ids'].index(r['goal_id'])
            order = (1, 0) if r['rep'] % 2 else (0, 1)
            bit = r['bits'][i]
            self.assertEqual(r['physical_ids'], [pair[i]['episodes'][bit][a] for a in order])
            self.assertEqual(r['witness_ids'], tuple(s['witness'][b]['id'] for s, b in zip(pair, r['bits'])))
            donor = rows[r['donor']]
            self.assertNotEqual(r['id'], r['donor'])
            self.assertEqual(r['id'], donor['donor'])
            self.assertEqual((r['goal'], r['sites'], r['local'], r['prior'], r['rep']),
                             (donor['goal'], donor['sites'], donor['local'], donor['prior'], donor['rep']))
            expected = [1, 1] if r['stratum'] == 'indifferent' else [pair[i]['rewards'][bit][a] for a in order]
            self.assertEqual(r['rewards'], expected)
