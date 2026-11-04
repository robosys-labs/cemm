"""G5 v7 source/reliability and TRAIN-only fit; no challenge reads here."""
import json
import unittest
from experiments.predictive_nucleus import source_temporal_v7 as source
from experiments.predictive_nucleus import calibrated_rule_v7 as rule
from experiments.predictive_nucleus.temporal_belief_v5 import (
    TimedReceipt,probability as p_v6,causal_nll as loss_v6)
from experiments.predictive_nucleus.independent_task_v7 import (
    inventory,SOURCE_ERROR,REGIME,NAMESPACE)
from experiments.predictive_nucleus.transfer_task import catalogue

class V7NoGoldTraining(unittest.TestCase):
    def test_exact_likelihood_equivalence_and_source_discrimination(self):
        scope=('root','unit')
        a=TimedReceipt('a','qor',scope,0,'sensor-A',(1.,0.),1,True,False)
        b=TimedReceipt('b','qor',scope,1,'sensor-B',(1.,0.),1,True,False)
        self.assertAlmostEqual(source.probability((a,), 'qor',scope,.15,.01,.3),.01)
        self.assertAlmostEqual(source.probability((b,), 'qor',scope,.15,.01,.3),.3)
        self.assertAlmostEqual(source.probability((a,b), 'qor',scope,.15,.1,.1),
                               p_v6((a,b),'qor',scope,.15,.1))
        self.assertEqual(len(source.payoff_forecasts((a,b),.15,.1,.1)),2)
        # Crucial non-complementary physical menu: output inversion is
        # not a hidden-meaning swap. p(0)=p(1)=1 must become 1-e.
        flat=TimedReceipt('flat','qor',scope,2,'sensor-B',(1.,1.),0)
        self.assertAlmostEqual(source.payoff_forecasts((flat,),.15,.1,.2)[0],.8)
        self.assertAlmostEqual(
            source.causal_nll(((a,b),),.15,.1,.1)[0],
            loss_v6(((a,b),),.15,.1)[0])
        ghost=TimedReceipt('ghost','qor',scope,2,'witness',None,0,False,False)
        self.assertEqual(source.probability((a,b,ghost),'qor',scope,.15,.1,.2),
                         source.probability((a,b),'qor',scope,.15,.1,.2))
        wrong=TimedReceipt('bad','qor',scope,2,'trusted-certificate',(1.,0.),1)
        with self.assertRaises(ValueError):
            source.probability((wrong,),'qor',scope,.15,.1,.2)
        self.assertAlmostEqual(rule.rule_probability(None,.2),.5)
        self.assertAlmostEqual(rule.rule_probability(1,.2),.8)

    def test_train_only_three_scalar_and_smoothed_rule_fits(self):
        self.assertNotEqual(NAMESPACE,'cemm-g5-v6-independent-nuisance-20261104')
        self.assertEqual(len(REGIME),5)
        self.assertEqual((SOURCE_ERROR['train']['A'],SOURCE_ERROR['train']['B']),(.03,.18))
        ids=set()
        evidence=[]
        samples={'A':0,'B':0}
        noncomplementary=0
        same_meaning_forecast=0
        for seed in (7,11,23):
            bank=catalogue('nand','train')
            for ep in inventory('nand',seed,'train',bank):
                self.assertNotIn(ep.uid,ids)
                ids.add(ep.uid)
                self.assertEqual(len(ep.records),16)
                self.assertEqual(sum(r.physical for r in ep.records),15)
                self.assertTrue(ep.records[12].epoch)
                self.assertEqual(len(ep.observed_sources),15)
                for s in ep.observed_sources:
                    samples[s]+=1
                for rec in ep.records:
                    if rec.physical:
                        a,b=rec.probabilities
                        noncomplementary+=abs(a+b-1)>1e-10
                        same_meaning_forecast+=abs(a-b)<1e-10
                # None of the fit functions sees ep.truth or an oracle.
                evidence.append(ep.records)
        self.assertEqual(len(evidence),576)
        self.assertEqual(sum(samples.values()),8640)
        fit=source.fit(evidence)
        neutral=source.fit_neutral(evidence)
        control=rule.fit(evidence)
        self.assertEqual(fit['outcomes'],8640)
        self.assertEqual(control['outcomes'],8640)
        self.assertEqual(neutral['outcomes'],8640)
        self.assertEqual(len(neutral['grid']),24)
        self.assertIn(neutral['e'],source.NEUTRAL_E_GRID)
        self.assertEqual(len(fit['grid']),64)
        self.assertEqual(len(control['grid']),7)
        self.assertIn(fit['h'],source.H_GRID)
        self.assertIn(fit['e_A'],source.EA_GRID)
        self.assertIn(fit['e_B'],source.EB_GRID)
        self.assertIn(control['delta'],rule.DELTA_GRID)
        print('G5_V7_TRAIN_FIT '+json.dumps(
            {'stage':'TRAIN_ONLY','worlds':576,'law':'nand',
             'seeds':[7,11,23],'samples':samples,
             'noncomplementary_forecast_rows':noncomplementary,
             'same_meaning_forecast_rows':same_meaning_forecast,
             'fit':fit,'neutral':neutral,'rule':control,'no_oracle_labels':True},
            separators=(',',':'),sort_keys=True),flush=True)

if __name__=='__main__':
    unittest.main()
