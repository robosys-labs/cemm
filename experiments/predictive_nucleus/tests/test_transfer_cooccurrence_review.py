import unittest

from experiments.predictive_nucleus.transfer_cooccurrence_review import learn_view, query_site


class CooccurrenceReviewTests(unittest.TestCase):
    def test_unseen_view_can_match_or_remain_unresolved(self):
        a, b, c, d = (1, 1), (1, -1), (-1, 1), (-1, -1)
        model, seen = learn_view([((a, b), a), ((c, a), a), ((a, b), b), ((b, c), b)])
        self.assertNotIn(c, seen)
        self.assertEqual(query_site(model, len(seen), (d, c), c), 1)
        self.assertIsNone(query_site(model, len(seen), (a, b), c))
