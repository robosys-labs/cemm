"""Post-fit TRAIN-only identifiability audit. Never opens the challenge bank."""
from itertools import product
from pathlib import Path
import json
import unittest

from experiments.predictive_nucleus.revision_memory import Memory
from experiments.predictive_nucleus.revision_outcome import decision, history, posterior
from experiments.predictive_nucleus.revision_study import select_triples
from experiments.predictive_nucleus.transfer_task import catalogue

FITS = Path(__file__).resolve().parents[1] / 'results/revision-v2/train-fitted.json'


class OutcomePrefixReview(unittest.TestCase):
    def test_identical_public_prefix_opposite_latent_truth(self):
        frozen = json.loads(FITS.read_text())
        self.assertEqual(frozen['stage'], 'train_only')
        self.assertEqual(len(frozen['condition_fits']), 10)
        report = {}
        for law in ('nand', 'nor'):
            bank = catalogue(law, 'train')
            for seed in (7, 11, 23, 37, 53):
                s = frozen['condition_fits'][f'{law}-{seed}']['switch']
                total = 0
                confident = 0
                largest_confidence = .5
                for k, (earlier, probe, later) in enumerate(select_triples(bank, seed)):
                    for old, regional, sentinel, reading in product((0,1), repeat=4):
                        m0, scopes0, targets0 = history(
                            earlier, probe, f'prefix-{k}', old, regional,
                            sentinel, reading, 1, 0)
                        m1, scopes1, targets1 = history(
                            earlier, probe, f'prefix-{k}', old, regional,
                            sentinel, reading, 1, 1)
                        # Withhold the later physical payoff entirely: both
                        # latent worlds have an identical public prefix.
                        prefix0 = Memory(r for r in m0.snapshot() if r.event_time < 4)
                        prefix1 = Memory(r for r in m1.snapshot() if r.event_time < 4)
                        self.assertEqual(prefix0.snapshot(), prefix1.snapshot())
                        self.assertNotEqual(targets0[0], targets1[0])
                        p = posterior(prefix0, 'qor', scopes0[0], s)
                        self.assertEqual(p, posterior(prefix1, 'qor', scopes1[0], s))
                        confident += decision(p) is not None
                        largest_confidence = max(largest_confidence, p, 1-p)
                        total += 1
                self.assertEqual(total, 96)
                report[f'{law}-{seed}'] = dict(
                    switch=s, identical_prefix_pairs=total,
                    premature_confident_pairs=confident,
                    necessarily_wrong_high_confidence_cases=confident,
                    max_posterior_confidence=largest_confidence)
        print('G5_V2_TRAIN_PREFIX_AUDIT ' + json.dumps(report,sort_keys=True), flush=True)


if __name__ == '__main__':
    unittest.main()
