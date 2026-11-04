import unittest
from unittest.mock import patch

from experiments.predictive_nucleus.revision_memory import Memory, Receipt
from experiments.predictive_nucleus.revision_study import score_bank, select_triples


def record(identity, term, scope, t, val, physical=True):
    matrix = ((.99, .01) if val == 0 else (.01, .99)) if physical else None
    return Receipt(identity, term, tuple(scope), t, 'sensor', matrix,
                   1 if physical else None, physical)


class RevisionMemoryTests(unittest.TestCase):
    def test_scoped_correction_reset_and_deduplication(self):
        root = ('world',)
        region = root + ('region',)
        here, other, elsewhere = region + ('a',), region + ('b',), root + ('elsewhere',)
        m = Memory([record('global', 'qor', root, 0, 0),
                    record('sentinel', 'nav', root, 0, 1)])
        m.add(record('region1', 'qor', region, 1, 1))
        self.assertIsNone(m.belief('qor', other))
        m.add(record('region2', 'qor', region, 2, 1))
        self.assertEqual(m.belief('qor', other), 1)
        m.add(record('local1', 'qor', here, 3, 0))
        self.assertIsNone(m.belief('qor', here))
        m.add(record('claim', 'qor', here, 12, 1, physical=False))
        m.add(record('global', 'qor', root, 0, 0))
        self.assertIsNone(m.belief('qor', here))
        m.add(record('local2', 'qor', here, 4, 0))
        carried = Memory(m.snapshot())
        self.assertEqual(carried.belief('qor', here), 0)
        self.assertEqual(carried.belief('qor', other), 1)
        self.assertEqual(carried.belief('qor', elsewhere), 0)
        self.assertEqual(carried.belief('nav', here), 1)
        with self.assertRaisesRegex(ValueError, 'conflicting reuse'):
            carried.add(record('global', 'qor', root, 0, 1))

    def test_nondiscriminating_and_simultaneous_conflict(self):
        m = Memory([record('global', 'qor', ('w',), 0, 0),
                    record('disputed', 'qor', ('w', 'unit'), 1, 1)])
        m.add(Receipt('uninformative', 'qor', ('w', 'unit'), 2, 'sensor', (.5,.5), 1))
        self.assertIsNone(m.belief('qor', ('w', 'unit')))
        m.add(record('confirm', 'qor', ('w', 'unit'), 3, 0))
        self.assertEqual(m.belief('qor', ('w','unit')), 0)
        m.add(record('conflict', 'qor', ('w','unit'), 3, 1))
        self.assertIsNone(m.belief('qor', ('w','unit')))

    def test_full_toy_bank_before_opening_challenge(self):
        # Construct synthetic sites; no parent challenge outcome is inspected.
        from experiments.predictive_nucleus.revision_preflight import layout
        def site(label, position):
            a, b = label+'A', label+'B'
            phrases = ([a, 'touches', b], [a, b, 'touches'], ['touches', a, b])
            words = phrases[position]
            reverse = [b if w == a else a if w == b else w for w in words]
            return {
                'id': label, 'entities': (a,b), 'lineage': label,
                'actions': ((0,a,b),(0,b,a)), 'texts': (' '.join(words), ' '.join(reverse)),
                'rewards': ((1,0),(0,1))
            }
        # Toy score uses six triples; structure selection is tested independently.
        mock = ((.99,.01),(.01,.99))
        trip = [(site('a',0),mock),(site('b',1),mock),(site('c',2),mock)]
        for s,_ in trip:
            self.assertIsNotNone(layout(s))
        with patch('experiments.predictive_nucleus.revision_study.select_triples',
                   return_value=[trip]*6):
            report = score_bank('nand', 7, {})
        self.assertEqual(report['cases'], 9216)
        self.assertEqual(report['resolved'], 7680)
        self.assertEqual(report['unresolved'], 1536)
        self.assertEqual(report['policy_questions_0'], 768)
        self.assertGreater(report['policy_net100_0'], report['baseline_net100_0'])

    def test_challenge_metadata_only(self):
        # Split selection is by entity, lineage and layout, not target outcome.
        from experiments.predictive_nucleus.transfer_task import catalogue
        for law in ('nand', 'nor'):
            shapes = select_triples(catalogue(law, 'challenge'), 7)
            self.assertEqual(len(shapes), 6)
            self.assertTrue(all(len({s[0]['id'] for s in triple}) == 3 for triple in shapes))
