"""G5 v6 TRAIN-only stochastic-data and shared-fit evidence.

Do not import or open the v6 challenge physical bank in this file.
"""
import json
import unittest
from experiments.predictive_nucleus.independent_task_v6 import inventory, SOURCE_ERROR
from experiments.predictive_nucleus.temporal_belief_v5 import fit, GRID_H, GRID_E
from experiments.predictive_nucleus.transfer_task import catalogue

TRAIN_SEEDS=(7,11,23)

class IndependentNuisanceTraining(unittest.TestCase):
    def test_full_nand_train_invariant_and_frozen_global_fit(self):
        seen_ids=set()
        worlds=[]
        changed=0
        selected_source={'A':0,'B':0}
        lineages=set()
        for seed in TRAIN_SEEDS:
            bank=catalogue('nand','train')
            scenes=inventory('nand',seed,'train',bank)
            self.assertEqual(len(scenes),192)
            for s in scenes:
                self.assertNotIn(s.uid,seen_ids)
                seen_ids.add(s.uid)
                lineages.add(s.lineage)
                changed+=s.truth[2]!=s.truth[3]
                worlds.append(s.records)  # only learner-visible evidence
                self.assertEqual(sum(int(r.epoch) for r in s.records),1)
                self.assertFalse(s.records[-1].physical)
                self.assertEqual(s.records[-1].probabilities,None)
                self.assertEqual(s.records[12].term,'qor')
                self.assertEqual(s.records[12].scope,s.unit)
                self.assertTrue(s.records[12].epoch)
                self.assertFalse(any(r.epoch for r in s.records[:12]))
                for src in s.observed_sources:
                    selected_source[src]+=1
        self.assertEqual(len(worlds),576)
        self.assertEqual(sum(selected_source.values()),576*15)
        self.assertGreater(selected_source['A'],1500)
        self.assertGreater(selected_source['B'],1500)
        self.assertGreater(changed,55)
        self.assertLess(changed,175)
        self.assertEqual(set(SOURCE_ERROR),{'train','challenge'})
        result=fit(worlds)  # no model/oracle hidden truth, no external fit labels
        self.assertIn(result['h'],GRID_H)
        self.assertIn(result['e'],GRID_E)
        self.assertEqual(result['outcomes'],576*15)
        self.assertEqual(len(result['grid']),16)
        print('G5_V6_TRAIN_FIT '+json.dumps(dict(
            result=result,worlds=len(worlds),changed=changed,
            selected_source=selected_source,lineages=len(lineages),
            training_law='nand',training_seeds=TRAIN_SEEDS,
            note='three TRAIN source strata, one common two-scalar fit'),
            sort_keys=True,separators=(',',':')),flush=True)

if __name__=='__main__':
    unittest.main()
