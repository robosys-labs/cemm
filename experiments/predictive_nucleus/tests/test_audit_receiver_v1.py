"""Adversarial saved-record checks for two gaps in the v1 arithmetic scorer."""
from copy import deepcopy
import unittest

from experiments.predictive_nucleus import audit_receiver_v1 as review
from experiments.predictive_nucleus.communication_score import _measure


class ReceiverReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.matrix = [[.875, .125], [.125, .875]]
        self.key = ('A', False, True)
        self.shared = {'support': [0, 1], 'sensor_observations': [{'reading': [0, 0]}],
                       'witness': {'source': 'A', 'age': 0, 'focus_matches': True},
                       'potential_deliveries': {k: {'token': 'lo'} for k in ('delivered', 'random', 'shuffled')}}
        self.target = {'cost': .05, 'stratum': 'useful', 'rewards': [1, 0]}
        self.raw = {'id': 'trial', 'cost': .05, 'stratum': 'useful', 'prior': [.5, .5], 'opportunity': True,
                    'arms': {a: {'asked': a != 'free_silent', 'action': 0, 'steps': 1,
                                 'values': [.5, .5] if a in ('free_silent', 'silent') else [.875, .125]}
                             for a in review.ARMS}}

    def verify(self, raw):
        return review.verify_decision(raw, self.shared, self.matrix, {self.key: 1.}, {(*self.key, True): .5})

    def test_argmax_and_suppressed_values_checked(self):
        self.assertEqual(self.verify(self.raw), (True, True))
        for arm, field, value in [('delivered', 'action', 1), ('silent', 'values', [.875, .125])]:
            corrupt = deepcopy(self.raw)
            corrupt['arms'][arm][field] = value
            _measure(corrupt, self.target)  # The frozen scorer trusts these fields on paid turns.
            with self.assertRaisesRegex(ValueError, 'decision differs'):
                self.verify(corrupt)

    def test_unsupported_sensor_projection_rejected(self):
        self.shared['support'] = [1]
        with self.assertRaisesRegex(ValueError, 'physical support'):
            self.verify(self.raw)
