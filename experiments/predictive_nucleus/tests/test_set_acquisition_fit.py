"""Synthetic one/two-update mask and feedback checks; no study bank is read."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import active_checkpoint as checkpoints
from experiments.predictive_nucleus import active_learning as learning
from experiments.predictive_nucleus import set_acquisition_fit as fit
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.domain_contract import world_index
from experiments.predictive_nucleus.joint_objective import fingerprint


SETTINGS = {'updates': 2, 'learning_rate': .02, 'cpu_seconds': 30., 'gradient_clip': 1.}


def tape(*, contradictory=False):
    before = [[0., 1., 0.], [1., 0., 1.]]
    after = before if contradictory else [[1., 1., 0.], [0., 0., 1.]]
    observations = torch.tensor([before, after], dtype=torch.float64)
    actions = torch.tensor([[[1, 0, -1, 1], [1, 0, -1, 0]]], dtype=torch.long)
    masks = torch.ones_like(observations, dtype=torch.bool)
    return learning.ObservedBatch(observations, actions, masks, masks[1:].clone(),
                                   ('synthetic-set-a', 'synthetic-set-b')).validate()


def direct_nll(model, batch):
    """Independent one-event complete-world scoring from the delivered reading."""
    with torch.no_grad():
        raw, _ = model.predict(batch.observations[0], batch.actions[0], model.initial(2))
        raw = raw - raw.logsumexp(-1, keepdim=True)
        return float(-raw.gather(1, world_index(batch.observations[1])[:, None]).mean())


class SetAcquisitionFitTests(unittest.TestCase):
    def setUp(self):
        state, threads = torch.random.get_rng_state(), torch.get_num_threads()
        self.addCleanup(torch.random.set_rng_state, state)
        self.addCleanup(torch.set_num_threads, threads)
        torch.set_num_threads(1)
        torch.manual_seed(199)
        self.model = DomainKernel(hidden=11, persistence=False, role_tying=False, memory=True)

    def test_mask_is_applied_before_clipping_and_complement_is_immutable(self):
        original = {name: p.detach().clone() for name, p in self.model.named_parameters()}
        masks, clipping = fit.parameter_masks(self.model), torch.nn.utils.clip_grad_norm_
        calls = []

        def inspect(parameters, maximum, **kwargs):
            calls.append(True)
            for name, p in self.model.named_parameters():
                if bool(masks[name].any()):
                    self.assertEqual(int(torch.count_nonzero(p.grad[~masks[name]])), 0)
                else:
                    self.assertFalse(p.requires_grad)
                    self.assertIsNone(p.grad)
            return clipping(parameters, maximum, **kwargs)

        history = tape(); before_hash = history.digest()
        with patch.object(torch.nn.utils, 'clip_grad_norm_', side_effect=inspect):
            report = fit.fit_masked(self.model, [history], SETTINGS)
        self.assertEqual(len(calls), 2)
        self.assertEqual(history.digest(), before_hash)
        self.assertEqual(report['permitted_scalars'], 68)
        self.assertEqual(report['immutable_scalars'], 494)
        self.assertEqual(report['changed_forbidden_scalars'], 0)
        self.assertGreater(report['changed_permitted_scalars'], 0)
        self.assertEqual(report['immutable_before_sha256'], report['immutable_after_sha256'])
        for name, value in self.model.named_parameters():
            self.assertTrue(torch.equal(value.detach()[~masks[name]].view(torch.int64),
                                        original[name][~masks[name]].view(torch.int64)))
            self.assertTrue(value.requires_grad)
            self.assertIsNone(value.grad)
        self.assertFalse(self.model.background[0].weight._backward_hooks)

    def test_endpoint_losses_use_actual_feedback_even_when_request_disagrees(self):
        expected = []
        for contradictory in (False, True):
            model, history = deepcopy(self.model), tape(contradictory=contradictory)
            initial = direct_nll(model, history)
            report = fit.fit_masked(model, [history], {**SETTINGS, 'updates': 1})
            self.assertAlmostEqual(report['initial_observed_train_nll'], initial, places=12)
            self.assertAlmostEqual(report['final_observed_train_nll'], direct_nll(model, history), places=12)
            self.assertEqual([entry[0] for entry in report['curve']], [0, 1])
            self.assertEqual(report['costs']['observed_replay_passes'], 2)
            expected.append(report['final_weights_sha256'])
        self.assertNotEqual(*expected)

    def test_loaded_parent_provenance_survives_checkpoint_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            parent_path, fitted_path = Path(directory) / 'parent.json', Path(directory) / 'fitted.json'
            parent = checkpoints.save_checkpoint(parent_path, model=self.model, provenance={
                'objective': 'untrained_or_inherited', 'completed_updates': 0, 'training_input_sha256': None})
            model = checkpoints.load_checkpoint(parent_path, parent['sha256'])['model']
            report = fit.fit_masked(model, [tape()], {**SETTINGS, 'updates': 1})
            self.assertFalse(hasattr(model, 'checkpoint_metadata'))
            self.assertEqual(report['parent_checkpoint_state_sha256'], parent['state_sha256'])
            self.assertEqual(report['final_weights_sha256'], fingerprint(model.state_dict()))
            saved = checkpoints.save_checkpoint(fitted_path, model=model, provenance=report)
            loaded = checkpoints.load_checkpoint(fitted_path, saved['sha256'])['model']
            self.assertEqual(loaded.training_provenance, report)
            self.assertEqual(fingerprint(loaded.state_dict()), report['final_weights_sha256'])

    def test_forbidden_optimizer_mutation_is_retained_as_interrupted_not_repaired(self):
        step = torch.optim.Adam.step
        original = self.model.pair[0].weight.detach().clone()

        def corrupt(optimizer, *args, **kwargs):
            result = step(optimizer, *args, **kwargs)
            with torch.no_grad(): self.model.pair[0].weight[0, 0].add_(.125)
            return result

        with patch.object(torch.optim.Adam, 'step', new=corrupt):
            with self.assertRaisesRegex(ValueError, 'forbidden parameter update'):
                fit.fit_masked(self.model, [tape()], {**SETTINGS, 'updates': 1})
        self.assertFalse(torch.equal(original, self.model.pair[0].weight))
        self.assertEqual(self.model.training_provenance['status'], 'INTERRUPTED')
        self.assertEqual(self.model.training_provenance['completed_updates'], 1)
        self.assertEqual(self.model.training_provenance['changed_forbidden_scalars'], 1)

    def test_cpu_exhaustion_preserves_zero_update_attempt_without_mutation(self):
        initial = fingerprint(self.model.state_dict())
        with self.assertRaisesRegex(TimeoutError, 'CPU ceiling'):
            fit.fit_masked(self.model, [tape()], {**SETTINGS, 'cpu_seconds': 1e-12})
        self.assertEqual(fingerprint(self.model.state_dict()), initial)
        self.assertEqual(self.model.training_provenance['status'], 'INTERRUPTED')
        self.assertEqual(self.model.training_provenance['stop_reason'], 'cpu_limit')
        self.assertEqual(self.model.training_provenance['completed_updates'], 0)

    def test_rejects_configuration_or_non_set_partial_training(self):
        with self.assertRaisesRegex(ValueError, 'frozen 562-parameter'):
            fit.parameter_masks(DomainKernel(hidden=11, role_tying=True))
        history = tape(); history.actions[0, 0] = torch.tensor([0, 0, 1, -1])
        with self.assertRaisesRegex(ValueError, 'set-only'):
            fit.fit_masked(self.model, [history], SETTINGS)
        history = tape(); history.masks[1, 0, 1] = False; history.observations[1, 0, 1] = -1
        with self.assertRaisesRegex(ValueError, 'complete observed'):
            fit.fit_masked(self.model, [history], SETTINGS)


if __name__ == '__main__': unittest.main()
