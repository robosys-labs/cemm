"""Observation-only learner and temperature calibrator invariants, no challenge seeds."""
import copy
import hashlib
import json
import math
import unittest
from pathlib import Path

import torch
from experiments.predictive_nucleus.latent_model import (
    ContactKernel, Samples, build_samples, fit_kernel, sensor_only_samples)
from experiments.predictive_nucleus.calibration import calibrate, contact_mixture_nll
from experiments.predictive_nucleus.world import make_episode


ROOT = Path(__file__).resolve().parents[1]


class EvidenceTrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)
        cls.train = [make_episode('train', (101, 103, 107, 109, 113)[i % 5], i,
                                   ('single_contact', 'two_contacts')[i % 2]) for i in range(300)]
        cls.validation = [make_episode('validation', (211, 223, 227, 229, 233)[i % 5], i,
                                        ('single_contact', 'two_contacts')[i % 2]) for i in range(100)]
        cls.calibration = [make_episode('calibration', (307, 311, 313, 317, 331)[i % 5], i,
                                         ('single_contact', 'two_contacts')[i % 2]) for i in range(100)]

    def test_no_gold_or_latent_truth_can_enter_training(self):
        class ReadOnlyEpisode:
            def __init__(self, episode):
                self.safe = episode
                self.actions = episode.actions

            def __getattr__(self, name):
                if name in ('states', 'gold_after', 'hidden_source_slot'):
                    raise AssertionError(f'oracle was read: {name}')
                return getattr(self.safe, name)
        supplied = [ReadOnlyEpisode(ep) for ep in self.train]
        actual = build_samples(supplied)
        baseline = build_samples(self.train)
        self.assertTrue(torch.equal(actual.contact, baseline.contact))
        self.assertTrue(torch.equal(actual.intervention, baseline.intervention))
        self.assertTrue(torch.equal(actual.episode_id, baseline.episode_id))
        self.assertGreater(actual.episodes, 100)

    def test_latent_mixture_learns_from_outcomes_without_truth_direction(self):
        samples = build_samples(self.train)
        checks = build_samples(self.validation)
        torch.manual_seed(7)
        unfitted = ContactKernel()
        before = contact_mixture_nll(unfitted, checks, 1.0)
        model, report = fit_kernel(samples, seed=7, steps=150)
        after = contact_mixture_nll(model, checks, 1.0)
        self.assertLess(after, before - 0.3)
        self.assertLess(report['parameters'], 100000)
        self.assertEqual(report['gradient_steps'], 150)
        self.assertGreater(report['interventions'], 100)
        frozen = model.freeze()
        for a in (0, 1):
            for b in (0, 1):
                for z in (0, 1):
                    probs = frozen.contact(a, b, z)
                    self.assertEqual(len(probs), 4)
                    self.assertAlmostEqual(sum(probs), 1, places=6)
                self.assertAlmostEqual(sum(frozen.intervention(a, b)), 1, places=6)
        self.assertNotEqual(frozen.contact(1, 0, 0), frozen.contact(1, 0, 1))

    def test_calibration_is_separate_and_frozen_weights_remain_same(self):
        fit, _ = fit_kernel(build_samples(self.train), seed=11, steps=80)
        before = copy.deepcopy(fit.state_dict())
        calibrated, info = calibrate(fit, build_samples(self.calibration))
        self.assertIn(info['temperature'], [0.5, 0.75, 1., 1.5, 2., 3.])
        for key in before:
            self.assertTrue(torch.equal(before[key], fit.state_dict()[key]))
        self.assertGreater(info['calibration_contact_events'], 30)
        self.assertAlmostEqual(sum(calibrated.contact(1, 0, 0)), 1, places=6)

    def test_versioned_protocol_hash_and_no_test_seed_overlap(self):
        original = json.loads((ROOT / 'protocol.json').read_text())
        cfg_path = ROOT / 'epistemic_protocol_v2.json'
        config = json.loads(cfg_path.read_text())
        digest = hashlib.sha256(cfg_path.read_bytes()).hexdigest()
        self.assertEqual(digest, (ROOT / 'snapshots/epistemic_protocol_v2.sha256').read_text().split()[0])
        self.assertEqual(config['schema_version'], 2)
        self.assertEqual(config['provisional_acceptance_targets_on_independently_custodied_new_challenges_only']['status'], 'NOT_RUN')
        self.assertEqual(config['selection']['model_seeds'], original['model_seeds'])
        splits = [config['selection'][key] for key in ('train_world_seeds', 'calibration_world_seeds',
                  'development_validation_world_seeds', 'frozen_original_challenge_world_seeds_must_not_run')]
        self.assertEqual(sum(len(x) for x in splits), len(set(seed for s in splits for seed in s)))
