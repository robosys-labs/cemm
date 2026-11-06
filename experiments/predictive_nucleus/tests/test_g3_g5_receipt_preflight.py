"""Synthetic guards for the delivered-prefix identity used by the TRAIN preflight."""
from copy import deepcopy
import unittest

from experiments.predictive_nucleus.g3_g5_receipt_preflight import prefix_digest


class ReceiptPrefix(unittest.TestCase):
    def setUp(self):
        self.record = {'id': 'example', 'entities': ['a', 'b'], 'anchor': [0, 1],
                       'context': [{'action': [0, 0, 1, -1], 'reading': [1, 1]},
                                   {'action': [1, 0, -1, 0], 'reading': [0, 1]}],
                       'utterances': [{'text': 'a verb b', 'reading': [1, 1]}]}

    def test_current_endpoint_is_excluded(self):
        changed = deepcopy(self.record)
        changed['utterances'][0]['reading'] = [0, 0]
        self.assertEqual(prefix_digest(changed), prefix_digest(self.record))

    def test_delivered_order_and_prior_observation_are_bound(self):
        changed = deepcopy(self.record)
        changed['context'].reverse()
        self.assertNotEqual(prefix_digest(changed), prefix_digest(self.record))
        changed = deepcopy(self.record)
        changed['context'][0]['reading'] = [0, 1]
        self.assertNotEqual(prefix_digest(changed), prefix_digest(self.record))

    def test_utterance_and_participant_order_are_bound(self):
        changed = deepcopy(self.record)
        changed['utterances'][0]['text'] = 'b verb a'
        self.assertNotEqual(prefix_digest(changed), prefix_digest(self.record))
        changed = deepcopy(self.record)
        changed['entities'].reverse()
        self.assertNotEqual(prefix_digest(changed), prefix_digest(self.record))
