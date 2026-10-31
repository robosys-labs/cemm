"""Synthetic derivative/boundary invariants; no saved research model is run."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import training_gradient_audit as audit
from experiments.predictive_nucleus import saturation_run as original
from experiments.predictive_nucleus.bilingual_model import freeze_world
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import fingerprint
from experiments.predictive_nucleus.tests.test_binding import observations


def fixture(arm='unsaturated'):
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(819)
        world = freeze_world(DomainKernel(hidden=2, persistence=False, role_tying=False, memory=True))
    return original.encoder(arm, 7), world, observations()


class TrainingGradientAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        torch.set_num_threads(1)

    def test_exact_objective_full_gradient_and_cell_partition_match_original(self):
        model, world, observed = fixture()
        loss, count = original.loss(model, world, original.prior.pack(observed, world))
        grad = audit.flat(torch.autograd.grad(loss, tuple(model.parameters())))
        result = audit.analyze(model, world, observed)
        self.assertAlmostEqual(result['mean_nll'], float(loss.detach()), places=12)
        self.assertEqual(result['observed_events'], count)
        self.assertAlmostEqual(result['parameter_gradient_norm'], float(grad.norm()), places=12)
        self.assertLess(result['cell_gradient_sum_max_error'], 1e-12)
        self.assertEqual(sum(c['events'] for c in result['cells']), count)
        self.assertAlmostEqual(sum(c['mean_nll'] * c['events'] for c in result['cells']) / count,
                               result['mean_nll'], places=12)

    def test_hessian_matches_synthetic_finite_difference_direction(self):
        model, world, observed = fixture()
        result = audit.analyze(model, world, observed)
        # Finite differences are confined to private synthetic fixture copies.
        params = tuple(model.parameters()); count = sum(p.numel() for p in params)
        basis = torch.eye(count, dtype=torch.float64)
        groups = original.prior.pack(observed, world)
        hessian = []
        for direction in basis:
            gradients = []
            for sign in (-1, 1):
                copy = deepcopy(model); offset = 0
                with torch.no_grad():
                    for p in copy.parameters():
                        p.add_(sign * 1e-5 * direction[offset:offset+p.numel()].reshape(p.shape)); offset += p.numel()
                loss, _ = original.loss(copy, world, groups)
                gradients.append(audit.flat(torch.autograd.grad(loss, tuple(copy.parameters()))))
            hessian.append((gradients[1] - gradients[0]) / 2e-5)
        hessian = torch.stack(hessian)
        numerical = torch.linalg.eigvalsh((hessian + hessian.T) / 2)
        self.assertTrue(torch.allclose(numerical, torch.tensor(result['hessian_eigenvalues'], dtype=torch.float64), atol=1e-7, rtol=1e-6))

    def test_preserves_weights_modes_gradients_trainability_inputs_rng_and_hooks(self):
        model, world, observed = fixture(); model.train()
        for p in model.parameters(): p.grad = torch.ones_like(p)
        params = list(model.parameters()); params[0].requires_grad_(False)
        before = (fingerprint(model.state_dict()), fingerprint(world.state_dict()), deepcopy(observed))
        flags = [p.requires_grad for p in params]; rng = torch.random.get_rng_state().clone()
        audit.analyze(model, world, observed)
        self.assertEqual(before, (fingerprint(model.state_dict()), fingerprint(world.state_dict()), observed))
        self.assertTrue(model.training); self.assertEqual(flags, [p.requires_grad for p in params])
        self.assertTrue(all(torch.equal(p.grad, torch.ones_like(p)) for p in params))
        self.assertTrue(all(p.grad is None for p in world.parameters()))
        self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))
        self.assertFalse(model.order._forward_hooks)

    def test_both_registered_arms_and_no_future_gradient_in_single_event_episodes(self):
        for arm in original.ARMS:
            model, world, observed = fixture(arm)
            observed = deepcopy(observed)
            for record in observed['episodes']: record['utterances'] = record['utterances'][:1]
            result = audit.analyze(model, world, observed)
            self.assertLess(result['future_parameter_gradient_norm'], 1e-12)
            self.assertEqual(len(result['hessian_eigenvalues']), 89)
            for cell in result['cells']:
                self.assertLess(cell['future_logit_gradient_l1']['max'], 1e-12)
                self.assertGreaterEqual(cell['hidden_tanh_derivative']['min'], 0.)
                self.assertLessEqual(cell['hidden_tanh_derivative']['max'], 1.)

    def test_analytic_responsibility_gradient_and_uninformative_evidence(self):
        logits = torch.tensor([[.3, -.2]], dtype=torch.float64, requires_grad=True)
        for ll in (torch.tensor([[0., -2.]], dtype=torch.float64), torch.zeros((1, 2), dtype=torch.float64)):
            q = logits.log_softmax(-1); nll = -(q + ll).logsumexp(-1).sum()
            grad = torch.autograd.grad(nll, logits)[0]
            self.assertTrue(torch.allclose(grad, q.exp() - (q + ll).softmax(-1), atol=1e-14))
            if bool((ll == 0).all()): self.assertLess(float(grad.abs().max()), 1e-14)

    def test_rejects_gold_unfrozen_world_and_empty_inputs(self):
        model, world, observed = fixture()
        bad = deepcopy(observed); bad['episodes'][0]['action_orders'] = [0]
        with self.assertRaises(ValueError): audit.analyze(model, world, bad)
        with self.assertRaises(ValueError): audit.analyze(model, world.train(), observed)
        world.eval().requires_grad_(True)
        with self.assertRaises(ValueError): audit.analyze(model, world, observed)
        world.requires_grad_(False)
        bad = deepcopy(observed); bad['episodes'] = []
        with self.assertRaises(ValueError): audit.analyze(model, world, bad)

    def test_no_optimizer_or_closed_study_execution(self):
        model, world, observed = fixture()
        with patch.object(torch.optim.Adam, 'step', side_effect=AssertionError('update forbidden')), \
             patch.object(original, 'collect', side_effect=AssertionError('collection forbidden')), \
             patch.object(original, 'verify', side_effect=AssertionError('held-file verification forbidden')):
            audit.analyze(model, world, observed)

    def test_read_boundary_blocks_held_data_and_repository_writes(self):
        path = audit.DATA / 'train-inputs.json.xz'
        with audit.TrainingReadBoundary([path]) as guard:
            self.assertTrue(path.read_bytes())
            with self.assertRaisesRegex(ValueError, 'unapproved'): (audit.DATA / 'nand-oracle.json.xz').read_bytes()
            with self.assertRaisesRegex(ValueError, 'writes prohibited'): path.open('wb')
        self.assertEqual(guard.reads, {path.resolve()})

    def test_output_reuse_rejected_before_any_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'exists.json'; path.write_text('{}')
            with patch.object(audit.io, '_read', side_effect=AssertionError('must not read')), self.assertRaises(ValueError):
                audit.run(path)

    def test_nonfinite_statistics_and_wrong_model_fail(self):
        with self.assertRaises(ValueError): audit.stats(torch.tensor([float('nan')]))
        model, world, observed = fixture()
        with self.assertRaises(ValueError): audit.analyze(original.prior.learner('grounded', 7), world, observed)



class CenteredInitializationTests(unittest.TestCase):
    def test_changes_only_one_initial_scalar_without_changing_parameter_count(self):
        from experiments.predictive_nucleus.binding_centered_init import centered_encoder
        for seed in (7, 11, 23, 37, 53):
            original_model = original.encoder('unsaturated', seed)
            centered = centered_encoder(seed)
            self.assertEqual(sum(p.numel() for p in centered.parameters()), 89)
            changed = [k for k, v in centered.state_dict().items() if not torch.equal(v, original_model.state_dict()[k])]
            self.assertEqual(changed, ['layout.0.bias'])
            self.assertEqual(centered.layout[0].bias.numel(), 1)
            self.assertTrue(centered.layout[0].bias.requires_grad)
            self.assertEqual(type(centered), type(original_model))

    def test_zero_mean_over_all_positions_with_no_prescribed_polarity(self):
        from experiments.predictive_nucleus.binding_centered_init import centered_encoder
        layouts = torch.ones(3, 3, dtype=torch.float64) - torch.eye(3, dtype=torch.float64)
        signs = []
        for seed in (7, 11, 23, 37, 53):
            model = centered_encoder(seed)
            response = model.layout[0](layouts).detach().flatten()
            self.assertLess(abs(float(response.mean())), 1e-14)
            self.assertLess(float(response.min()), 0.)
            self.assertGreater(float(response.max()), 0.)
            signs.append(tuple(response.sign().tolist()))
        self.assertGreater(len(set(signs)), 1)

    def test_rng_determinism_and_unrestricted_bias_after_initialization(self):
        from experiments.predictive_nucleus.binding_centered_init import centered_encoder
        rng = torch.random.get_rng_state().clone()
        model = centered_encoder(7)
        self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))
        self.assertEqual(fingerprint(model.state_dict()), fingerprint(centered_encoder(7).state_dict()))
        with torch.no_grad(): model.layout[0].bias.add_(10.)
        layouts = torch.ones(3, 3, dtype=torch.float64) - torch.eye(3, dtype=torch.float64)
        self.assertTrue(bool((model.layout[0](layouts) > 0).all()))
        for invalid in (True, -1):
            with self.assertRaises(ValueError): centered_encoder(invalid)


if __name__ == '__main__': unittest.main()
