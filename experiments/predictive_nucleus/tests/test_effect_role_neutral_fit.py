"""Tiny synthetic fits only; no research inputs, labels or saved checkpoints."""
import math
import unittest
from unittest.mock import patch

import torch
from torch import nn

from experiments.predictive_nucleus import effect_role_model as model
from experiments.predictive_nucleus import effect_role_neutral as neutral
from experiments.predictive_nucleus import effect_role_neutral_fit as fit
from experiments.predictive_nucleus import effect_role_run as historical
from experiments.predictive_nucleus.bilingual_model import freeze_world
from experiments.predictive_nucleus.binding_layout_coordinates import coordinate_encoder
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint
from experiments.predictive_nucleus.tests.test_effect_role_model import bank


SETTINGS = {'updates': 2, 'learning_rate': .02, 'gradient_clip': 5.,
            'teach_weight': .5, 'cpu_seconds_per_fit': 400}


def small_net():
    net = nn.Linear(1, 1, bias=False, dtype=DTYPE)
    with torch.no_grad(): net.weight.fill_(.5)
    return net


class EffectRoleNeutralFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = torch.get_num_threads(); torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.threads)

    def setUp(self):
        self.parent = coordinate_encoder(7).state_dict()
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(481)
            self.world = freeze_world(DomainKernel(hidden=3, role_tying=False))
        observed = {'teach': bank(('novel',)), 'rehearsal': bank(('touches',) * 3)}
        registry = model.create_registry([observed['rehearsal'], observed['teach']])
        self.tapes = {k: model.pack(v, self.world, registry) for k, v in observed.items()}
        self.labels = {'teach': {'synthetic': [3]}, 'rehearsal': {'synthetic': [0, 1, 0]}}

    def test_grounded_and_parser_use_new_learner_with_unchanged_world_and_report(self):
        before = fingerprint(self.world.state_dict())
        self.assertIs(fit.objective, historical.objective)
        for arm in ('grounded', 'parser'):
            net, report = fit.fit_one(arm, 7, self.parent, self.world, self.tapes,
                                     self.labels if arm == 'parser' else None, SETTINGS)
            self.assertIsInstance(net, neutral.ProbabilityNeutralEncoder)
            self.assertEqual(report['parameters'], 92)
            self.assertEqual(report['settings'], SETTINGS)
            self.assertEqual(report['optimizer'], historical.OPTIMIZER)
            self.assertTrue(report['fresh_optimizer'])
            self.assertEqual(report['observed_forecasts_per_update'], {'teach': 1, 'rehearsal': 3})
            self.assertEqual(report['initial_sha256'], fingerprint(neutral.encoder(7, self.parent).state_dict()))
            self.assertEqual(report['final_sha256'], fingerprint(net.state_dict()))
            self.assertNotEqual(report['initial_sha256'], report['final_sha256'])
            self.assertTrue(all(math.isfinite(v) for v in report['final_objective'].values()))
            self.assertEqual(report['world_sha256'], before)
            self.assertTrue(report['world_unchanged'])
        self.assertEqual(fingerprint(self.world.state_dict()), before)
        self.assertTrue(all(p.grad is None for p in self.world.parameters()))

    def test_text_only_synthetic_weights_curves_and_objectives_reproduce_v1_exactly(self):
        settings = {**SETTINGS, 'updates': 16}
        old, old_report = historical.fit_one('text_only', 11, self.parent, self.world, self.tapes, None, settings)
        new, new_report = fit.fit_one('text_only', 11, self.parent, self.world, self.tapes, None, settings)
        self.assertEqual(fingerprint(new.state_dict()), fingerprint(old.state_dict()))
        self.assertEqual({k: v for k, v in new_report.items() if k != 'resources'},
                         {k: v for k, v in old_report.items() if k != 'resources'})

    def test_tape_means_receive_equal_weight_despite_different_counts(self):
        net, world = small_net(), small_net().eval().requires_grad_(False)
        def objective(arm, candidate, native, groups, labels=None):
            return candidate.weight.sum() * (2 if groups == ['teach'] else 4), 1 if groups == ['teach'] else 100
        with patch.object(fit, 'learner', return_value=net), patch.object(fit, 'objective', side_effect=objective):
            _, report = fit.fit_one('grounded', 7, {}, world,
                {'teach': ['teach'], 'rehearsal': ['rehearsal']}, None, {**SETTINGS, 'updates': 1})
        self.assertAlmostEqual(float(net.weight.grad), 3., places=14)
        self.assertEqual(report['observed_forecasts_per_update'], {'teach': 1, 'rehearsal': 100})

    def test_parser_labels_invalid_settings_and_mutable_world_are_rejected(self):
        for arm, labels in (('grounded', self.labels), ('text_only', self.labels), ('parser', None)):
            with self.subTest(arm=arm), self.assertRaisesRegex(ValueError, 'parser-only'):
                fit.fit_one(arm, 7, self.parent, self.world, self.tapes, labels, SETTINGS)
        bad_labels = {**self.labels, 'teach': {'synthetic': [True]}}
        with self.assertRaisesRegex(ValueError, 'label inventory/range'):
            fit.fit_one('parser', 7, self.parent, self.world, self.tapes, bad_labels, SETTINGS)
        for field, value in (('updates', True), ('learning_rate', math.nan), ('cpu_seconds_per_fit', 0.)):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'budget/weight'):
                fit.fit_one('grounded', 7, self.parent, self.world, self.tapes, None, {**SETTINGS, field: value})
        self.world.requires_grad_(True)
        with self.assertRaisesRegex(ValueError, 'frozen world'):
            fit.fit_one('grounded', 7, self.parent, self.world, self.tapes, None, SETTINGS)

    def test_final_nonfinite_count_and_world_mutation_cannot_yield_success(self):
        for defect in ('nonfinite', 'count', 'world'):
            net, world = small_net(), small_net().eval().requires_grad_(False)
            def objective(arm, candidate, native, groups, labels=None):
                count = 1
                if not torch.is_grad_enabled():
                    if defect == 'nonfinite': return torch.tensor(math.nan, dtype=DTYPE), count
                    if defect == 'count': count = 2
                    if defect == 'world': native.weight.add_(.1)
                return candidate.weight.sum(), count
            with self.subTest(defect=defect), patch.object(fit, 'learner', return_value=net), \
                 patch.object(fit, 'objective', side_effect=objective), self.assertRaises(ValueError):
                fit.fit_one('grounded', 7, {}, world, {'teach': ['teach'], 'rehearsal': ['rehearsal']},
                            None, {**SETTINGS, 'updates': 1})

    def test_cpu_ceiling_includes_final_objective_measurement(self):
        with patch.object(fit.time, 'process_time', side_effect=[0., 0., 0., 401.]):
            with self.assertRaisesRegex(ValueError, 'CPU ceiling'):
                fit.fit_one('grounded', 7, self.parent, self.world, self.tapes, None, {**SETTINGS, 'updates': 1})


if __name__ == '__main__': unittest.main()
