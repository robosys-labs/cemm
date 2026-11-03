"""Mechanics only. These synthetic numbers are independent of the research bank."""
import json
import unittest

from experiments.predictive_nucleus.communication_policy import (
    ActionSample, Policy, RequestSample, Witness,
)


class CommunicationPolicyTests(unittest.TestCase):
    def setUp(self):
        self.a = Witness("A", 0, True)
        self.b = Witness("B", 0, True)
        self.prior = (.5, .5)
        self.claim = (0., 1.)

    def test_reward_alone_can_reverse_source_and_changed_goal(self):
        records = [ActionSample(w, self.prior, self.claim, i, i if w == self.a else 1 - i)
                   for w in (self.a, self.b) for i in (0, 1)]
        policy = Policy.fit_actions(records)
        self.assertEqual(policy.act(self.prior, self.a, self.claim), 1)
        self.assertEqual(policy.act(self.prior, self.b, self.claim), 0)
        self.assertEqual(policy.act(self.prior, self.a, self.claim[::-1]), 0)
        self.assertEqual(policy.act(self.prior, self.b, self.claim[::-1]), 1)
        self.assertEqual(policy.values(self.prior), self.prior)
        for unknown in (Witness("unseen", 0, True), Witness("A", 2, True),
                        Witness("A", 0, False)):
            self.assertEqual(policy.values(self.prior, unknown, self.claim), self.prior)

    def test_explored_requests_use_silent_outcomes_and_pay_cost(self):
        def sample(reward, requested, witness=self.a):
            return RequestSample(witness, self.prior, True, reward, requested)
        rows = [sample(1, True), sample(1, False), sample(0, False),
                sample(1, True, self.b)]
        policy = Policy.fit_actions([]).fit_requests(rows)
        self.assertTrue(policy.ask(self.prior, self.a, True, .49))
        self.assertFalse(policy.ask(self.prior, self.a, True, .5))
        self.assertFalse(policy.ask(self.prior, self.a, False, 0))
        self.assertFalse(policy.ask(self.prior, self.b, True, 0))
        self.assertFalse(policy.ask(self.prior, Witness("A", 1, True), True, 0))
        self.assertEqual(policy, Policy.from_dict(json.loads(json.dumps(policy.to_dict()))))

    def test_invalid_feedback_and_unattributed_claims_rejected(self):
        policy = Policy.fit_actions([])
        with self.assertRaises(ValueError):
            policy.values(self.prior, claimed=self.claim)
        with self.assertRaises(ValueError):
            Policy.fit_actions([ActionSample(self.a, self.prior, self.claim, 2, 1)])
        with self.assertRaises(ValueError):
            policy.ask(self.prior, self.a, True, float("nan"))
        with self.assertRaises(ValueError):
            Policy.from_dict({"weights": [["A", False, True, float("inf")]], "gains": []})
