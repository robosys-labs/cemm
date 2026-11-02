"""Synthetic acquisition updates; no real TRAIN or challenge execution."""
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import effect_role_model as model
from experiments.predictive_nucleus import effect_role_lexical as lexical
from experiments.predictive_nucleus import effect_role_lexical_fit as fit
from experiments.predictive_nucleus import effect_role_run as historical
from experiments.predictive_nucleus.bilingual_model import freeze_world
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import fingerprint
from experiments.predictive_nucleus.tests.test_effect_role_model import bank
from experiments.predictive_nucleus.tests.test_effect_role_lexical import fixture


SETTINGS = {'updates': 2, 'learning_rate': .02, 'gradient_clip': 5.,
            'teach_weight': .5, 'cpu_seconds_per_fit': 400}


class EffectRoleLexicalFitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = torch.get_num_threads(); torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls):
        torch.set_num_threads(cls.threads)

    def setUp(self):
        parent, self.registry, self.legacy = fixture(); self.parent = parent.state_dict()
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(481)
            self.world = freeze_world(DomainKernel(hidden=3, role_tying=False))
        observed = {'teach': bank(('novel_a', 'novel_b')), 'rehearsal': bank(('touches',) * 3)}
        self.tapes = {k: model.pack(v, self.world, self.registry) for k, v in observed.items()}
        self.labels = {'teach': {'synthetic': [3, 2]}, 'rehearsal': {'synthetic': [0, 1, 0]}}
        self.kwargs = {'registry': self.registry, 'legacy_ids': self.legacy}

    def test_only_four_coordinates_train_and_protected_parent_world_and_legacy_predictions_survive(self):
        before, protected = fingerprint(self.world.state_dict()), fingerprint(self.parent)
        old_features = self.tapes['rehearsal'][0]['events'][0]['features']
        reference = lexical.encoder(7, self.parent, **self.kwargs)(old_features)
        for arm in ('grounded', 'parser'):
            net, report = fit.fit_one(arm, 7, self.parent, self.world, self.tapes,
                self.labels if arm == 'parser' else None, SETTINGS, **self.kwargs)
            self.assertEqual((report['parameters'], report['protected_parameters'], report['learned_parameters']), (92, 88, 4))
            self.assertEqual(report['protected_initial_sha256'], protected)
            self.assertEqual(report['protected_final_sha256'], protected)
            self.assertTrue(report['protected_unchanged'])
            self.assertEqual(report['registry_sha256'], historical.c.digest(self.registry))
            self.assertEqual(report['legacy_ids'], self.legacy)
            self.assertEqual(report['new_ids'], list(net.new_ids))
            self.assertGreater(float(net.new_coordinates.detach().abs().sum()), 0.)
            self.assertTrue(torch.equal(net(old_features), reference))
            self.assertEqual(fingerprint(net.parent.state_dict()), protected)
            self.assertEqual(fingerprint(self.world.state_dict()), before)
            self.assertTrue(all(p.grad is None for p in self.world.parameters()))
            self.assertTrue(all(p.grad is None and not p.requires_grad for p in net.parent.parameters()))
            self.assertEqual(report['observed_forecasts_per_update'], {'teach': 2, 'rehearsal': 3})
            self.assertEqual(report['settings'], SETTINGS)
            self.assertEqual(report['optimizer'], historical.OPTIMIZER)

    def test_optimizer_receives_only_the_new_identity_tensor(self):
        actual_adam, captured = torch.optim.Adam, []
        def optimizer(parameters, **kwargs):
            parameters = list(parameters); captured.extend(parameters)
            return actual_adam(parameters, **kwargs)
        with patch.object(torch.optim, 'Adam', side_effect=optimizer):
            net, _ = fit.fit_one('grounded', 7, self.parent, self.world, self.tapes, None, SETTINGS, **self.kwargs)
        self.assertEqual(len(captured), 1)
        self.assertIs(captured[0], net.new_coordinates)

    def test_text_only_weights_curves_and_full_nonresource_report_reproduce_v1(self):
        settings = {**SETTINGS, 'updates': 16}
        old, old_report = historical.fit_one('text_only', 11, self.parent, self.world, self.tapes, None, settings)
        new, new_report = fit.fit_one('text_only', 11, self.parent, self.world, self.tapes, None, settings, **self.kwargs)
        self.assertEqual(fingerprint(old.state_dict()), fingerprint(new.state_dict()))
        self.assertEqual({k: v for k, v in old_report.items() if k != 'resources'},
                         {k: v for k, v in new_report.items() if k != 'resources'})

    def test_parser_labels_cannot_enter_grounded_or_text_only_fit(self):
        self.assertIs(fit.objective, historical.objective)
        for arm, labels in (('grounded', self.labels), ('text_only', self.labels), ('parser', None)):
            with self.subTest(arm=arm), self.assertRaisesRegex(ValueError, 'parser-only'):
                fit.fit_one(arm, 7, self.parent, self.world, self.tapes, labels, SETTINGS, **self.kwargs)
        bad = {**self.labels, 'teach': {'synthetic': [True, 2]}}
        with self.assertRaisesRegex(ValueError, 'label inventory/range'):
            fit.fit_one('parser', 7, self.parent, self.world, self.tapes, bad, SETTINGS, **self.kwargs)

    def test_parent_mutation_during_final_measurement_is_a_hard_error(self):
        original = fit.objective
        def objective(arm, net, world, groups, labels=None):
            value = original(arm, net, world, groups, labels)
            if not torch.is_grad_enabled(): next(net.parent.parameters()).add_(.01)
            return value
        with patch.object(fit, 'objective', side_effect=objective), self.assertRaisesRegex(ValueError, 'inherited lexical model mutated'):
            fit.fit_one('grounded', 7, self.parent, self.world, self.tapes, None, SETTINGS, **self.kwargs)

    def test_cpu_ceiling_includes_final_protected_measurement(self):
        with patch.object(fit.time, 'process_time', side_effect=[0., 0., 0., 401.]):
            with self.assertRaisesRegex(ValueError, 'CPU ceiling'):
                fit.fit_one('grounded', 7, self.parent, self.world, self.tapes, None,
                            {**SETTINGS, 'updates': 1}, **self.kwargs)


if __name__ == '__main__': unittest.main()
