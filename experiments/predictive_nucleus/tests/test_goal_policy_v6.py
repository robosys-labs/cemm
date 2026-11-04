"""Goal-aware verification is identical for every G5 v6 comparison arm."""
import unittest
from experiments.predictive_nucleus.goal_policy_v6 import (
    GOALS, FEES, choose, public_task, after_answer
)

class QueryValueChecks(unittest.TestCase):
    def test_useful_cheap_only_and_never_peek_oracle(self):
        self.assertTrue(choose(.5,GOALS[0],.05)['ask'])
        self.assertFalse(choose(.5,GOALS[0],.75)['ask'])
        self.assertFalse(choose(.5,GOALS[0],None)['ask'])
        self.assertFalse(choose(.5,GOALS[2],.05)['ask'])
        self.assertFalse(choose(.5,GOALS[3],.05)['ask'])
        self.assertFalse(choose(0.,GOALS[0],.05)['ask'])
        self.assertFalse(choose(1.,GOALS[1],.05)['ask'])
        self.assertEqual(after_answer(GOALS[0],0),0)
        self.assertEqual(after_answer(GOALS[0],1),1)
        self.assertEqual(after_answer(GOALS[1],0),1)
        self.assertEqual(after_answer(GOALS[1],1),0)
        self.assertEqual(len(FEES),3)

    def test_opaque_public_task_and_negative_inputs(self):
        uid='0123456789abcdef01234567'
        g1,g2,fee=public_task(uid)
        self.assertIn(g1,GOALS)
        self.assertIn(g2,GOALS)
        self.assertIn(fee,FEES)
        with self.assertRaises(ValueError):
            choose(1.01,GOALS[0],.05)
        with self.assertRaises(ValueError):
            choose(.5,GOALS[0],-.01)
        with self.assertRaises(ValueError):
            public_task('bad')
