"""G5 v8 TRAIN-only exact-state and provenance checks; TEST never imported."""
import unittest
from experiments.predictive_nucleus import joint_trust_v8 as joint
from experiments.predictive_nucleus.independent_task_v8 import (
    episodes,inventory,NAMESPACE,REGIME)
from experiments.predictive_nucleus.temporal_belief_v5 import TimedReceipt
from experiments.predictive_nucleus.transfer_task import catalogue

class JointTrustTrainOnly(unittest.TestCase):
    def test_exact_32_state_normalization_sensor_likelihood(self):
        self.assertEqual(joint.STATES,32)
        weights=[1/32]*32
        t=joint._transition(weights)
        self.assertAlmostEqual(sum(t),1.)
        self.assertTrue(all(abs(a-b)<1e-15 for a,b in zip(weights,t)))
        r=TimedReceipt('r','qor',('x',),0,'sensor-A',(1.,1.),0,True,False)
        self.assertAlmostEqual(joint._predict(weights,r),.885)
        self.assertAlmostEqual(sum(joint._update(weights,r)),1.)
        w=TimedReceipt('w','qor',('x',),1,'witness',None,0,False,False)
        self.assertEqual(joint.state_after((r,)),joint.state_after((r,w)))
        with self.assertRaises(ValueError):
            joint.state_after((r,TimedReceipt(
                'r','qor',('x',),0,'sensor-A',(0.,0.),1,True,False)))
        with self.assertRaises(ValueError):
            joint.state_after((r,),after_epoch=True)

    def test_train_prefix_twins_and_causal_no_gold(self):
        self.assertNotIn('cemm-g5-v7-source-shift',NAMESPACE)
        self.assertEqual(len(REGIME),5)
        bank=catalogue('nand','train')
        scenes=inventory('nand',7,'train',bank)
        self.assertEqual(len(scenes),192)
        self.assertEqual(len({e.uid for e in scenes}),192)
        self.assertEqual(sum(e.flip for e in scenes),96)
        for a,b in zip(scenes[::2],scenes[1::2],strict=True):
            self.assertEqual(a.records[:12],b.records[:12])
            self.assertNotEqual(a.truth[3],b.truth[3])  # evaluator-only test
            av,bv=joint.views(a),joint.views(b)
            self.assertEqual(av['pre_after_epoch_local'],
                             bv['pre_after_epoch_local'])
            self.assertTrue(.05<av['pre_after_epoch_local']<.95)
            self.assertEqual(joint.payoff_forecasts(a.records)[:12],
                             joint.payoff_forecasts(b.records)[:12])
            self.assertEqual(len(joint.payoff_forecasts(a.records)),15)
            self.assertTrue(0<=av['trust_final']<=1)
            self.assertTrue(0<=av['final_root']<=1)
        print('G5_V8_TRAIN_PREFLIGHT '
              '{"worlds":192,"pairs":96,"joint_states":32,'
              '"fit":"inherited v7 TRAIN only","challenge_opened":false}',
              flush=True)

if __name__=='__main__':
    unittest.main()
