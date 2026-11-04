"""G5 temporal learner: exact software invariants and TRAIN-only fit receipt."""
import json
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus.revision_memory import Memory
from experiments.predictive_nucleus.temporal_belief_v5 import (
    TimedReceipt, probability, decision, causal_nll, fit, GRID_E, GRID_H
)
from experiments.predictive_nucleus.temporal_task_v5 import (
    episodes, inventory, LAWS, SEEDS
)


def sample(identity,term,scope,t,target,epoch=False,physical=True):
    # Given equal physical hypotheses, this selected reward supports 0 or 1.
    return TimedReceipt(identity,term,scope,t,
        'verified-sensor' if physical else 'unverified-witness',
        (.99,.01) if physical else None,1-target,physical,epoch)


class TemporalModelInvariants(unittest.TestCase):
    def test_scoped_revision_sentinel_reset_and_duplicate(self):
        root=('world',)
        region=root+('region',)
        unit=region+('unit',)
        sibling=region+('sibling',)
        outside=root+('outside',)
        records=[*(sample('r'+str(t),'qor',root,t,0) for t in range(3)),
                 *(sample('n'+str(t),'nav',root,t,1) for t in range(3)),
                 *(sample('g'+str(t),'qor',region,t+3,1) for t in range(3)),
                 *(sample('u'+str(t),'qor',unit,t+6,1) for t in range(3))]
        m=Memory(records)
        self.assertEqual(decision(probability(m.snapshot(),'qor',sibling,.35,.1)),1)
        self.assertEqual(decision(probability(m.snapshot(),'qor',outside,.35,.1)),0)
        self.assertEqual(decision(probability(m.snapshot(),'nav',unit,.35,.1)),1)
        m.add(sample('epoch','qor',unit,9,0,True))
        self.assertIsNone(decision(probability(m.snapshot(),'qor',unit,.35,.1)))
        m.add(sample('later1','qor',unit,10,0))
        m.add(sample('later2','qor',unit,11,0))
        self.assertEqual(decision(probability(m.snapshot(),'qor',unit,.35,.1)),0)
        self.assertEqual(decision(probability(m.snapshot(),'qor',sibling,.35,.1)),1)
        self.assertEqual(decision(probability(m.snapshot(),'qor',outside,.35,.1)),0)
        self.assertEqual(decision(probability(m.snapshot(),'nav',unit,.35,.1)),1)
        before=probability(m.snapshot(),'qor',unit,.35,.1)
        m.add(sample('false-witness','qor',unit,12,1,physical=False))
        m.add(records[0])  # duplicate physical receipt is not new evidence
        m.add(TimedReceipt('no-info','qor',unit,13,'verified-sensor',(.5,.5),1))
        after=probability(Memory(m.snapshot()).snapshot(),'qor',unit,.35,.1)
        self.assertAlmostEqual(before,after,places=12)
        with self.assertRaisesRegex(ValueError,'conflicting reuse'):
            m.add(sample('epoch','qor',unit,9,1,True))

    def test_same_time_opposing_physical_evidence_commutes(self):
        scope=('w',)
        a=sample('a','qor',scope,0,0,True)
        b=sample('b','qor',scope,0,1,True)
        first=probability(Memory([a,b]).snapshot(),'qor',scope,.35,.1)
        second=probability(Memory([b,a]).snapshot(),'qor',scope,.35,.1)
        self.assertAlmostEqual(first,second,places=14)
        self.assertAlmostEqual(first,.5,places=14)

    def test_causal_only_one_step_likelihood(self):
        scope=('w',)
        row=sample('a','qor',scope,0,0)
        independent=sample('b','qor',scope,1,0)
        before,_=causal_nll([[row]],.15,.1)
        after,_=causal_nll([[row,independent]],.15,.1)
        self.assertLess(after,before)
        self.assertEqual(len(GRID_H)*len(GRID_E),16)

    def test_real_train_fit_and_matched_counterfactuals(self):
        from experiments.predictive_nucleus.transfer_task import catalogue
        fitted={}
        with patch('experiments.predictive_nucleus.transfer_task.catalogue',
                   wraps=catalogue) as watched:
            for law in LAWS:
                bank=catalogue(law,'train')
                for seed in SEEDS:
                    episodes=inventory(law,seed,'train',bank)
                    self.assertEqual(len(episodes),192)
                    self.assertTrue(all(len(ep.records)==16 for ep in episodes))
                    self.assertTrue(all(ep.records[12].epoch for ep in episodes))
                    result=fit([ep.records for ep in episodes])
                    self.assertIn(result['h'],GRID_H)
                    self.assertIn(result['e'],GRID_E)
                    self.assertEqual(result['outcomes'],192*15)
                    fitted[f'{law}-{seed}']=result
        self.assertEqual(len(fitted),10)
        self.assertTrue(all(call.args[1]=='train' for call in watched.call_args_list))
        print('G5_V5_TRAIN_FITS '+json.dumps(fitted,sort_keys=True),flush=True)


if __name__=='__main__':
    unittest.main()
