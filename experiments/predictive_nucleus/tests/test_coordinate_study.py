"""Synthetic study boundaries only; no research fits or held-bank scores."""
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
from io import StringIO
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import coordinate_run as run, coordinate_scoring as scoring
from experiments.predictive_nucleus import saturation_run as objective
from experiments.predictive_nucleus.continuation_run import _read, _write
from experiments.predictive_nucleus.joint_objective import fingerprint
from experiments.predictive_nucleus.tests.test_centering_study import fixture as old_fixture
from experiments.predictive_nucleus.tests.test_saturation_study import toy_inputs, toy_world


def fixture(root):
    prepared, config = old_fixture(root)
    config['version'] = run.protocol()['version']
    config['arms'] = list(run.ARMS)
    return prepared, config


@contextmanager
def synthetic(root, config, *, retention=False):
    banks = {'centering_retention': 'synthetic-retention'} if retention else {}
    with patch.object(run, 'verify', return_value=(config, {'checkpoints': {}})), \
         patch.object(run.io, '_runtime', return_value={'synthetic': True}), \
         patch.object(run.io, 'ROOT', root), patch.object(run, 'BANKS', banks), \
         patch.object(run.prior, 'world_for', return_value=toy_world()), \
         patch.object(run, '_control_receipt', return_value={'synthetic': True}), \
         redirect_stdout(StringIO()) as stdout:
        yield stdout


class CoordinateInitializationTests(unittest.TestCase):
    def test_matched_legal_functions_parameter_counts_shared_tensors_and_rng(self):
        rng = torch.random.get_rng_state().clone()
        for seed in (7, 11, 23, 37, 53):
            models, receipt = run.initial_pair(seed)
            self.assertEqual(receipt['parameters'], {'centered': 89, 'coordinates': 88})
            self.assertEqual(receipt['unchanged_scalars'], 85)
            self.assertEqual(receipt['layout_masks'], [[0., 1., 1.], [1., 0., 1.], [1., 1., 0.]])
            self.assertEqual(receipt['layout_responses']['centered'], receipt['layout_responses']['coordinates'])
            for arm, model in models.items():
                self.assertEqual(fingerprint(model.state_dict()), receipt['initial_sha256'][arm])
                self.assertTrue(all(p.requires_grad for p in model.parameters()))
            self.assertEqual(receipt, run.initial_pair(seed)[1])
        self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))

    def test_equivalence_guard_rejects_response_or_shared_tensor_change(self):
        original = run.encoder
        for key in ('layout.0.weight', 'lexical.0.weight', 'order.bias'):
            def altered(arm, seed):
                model = original(arm, seed)
                if arm == 'coordinates':
                    with torch.no_grad(): dict(model.named_parameters())[key].flatten()[0].add_(.125)
                return model
            with self.subTest(key=key), patch.object(run, 'encoder', side_effect=altered), self.assertRaises(ValueError):
                run.initial_pair(7)


class CoordinateTrainingTests(unittest.TestCase):
    def test_one_step_uses_same_observations_loss_and_frozen_world(self):
        observed, world = toy_inputs(), toy_world(); original = deepcopy(observed)
        before = fingerprint(world.state_dict()); rng = torch.random.get_rng_state().clone()
        models, initialization = run.initial_pair(7); groups = run.prior.pack(observed, world)
        expected = {arm: float(objective.loss(net, world, groups)[0].detach()) for arm, net in models.items()}
        fitted, report = run.fit_pair(observed, world, 7, dict(run.protocol()['fit'], updates=1))
        self.assertIs(run.loss, objective.loss); self.assertIs(run.probes, objective.probes)
        self.assertEqual(report['initialization'], initialization)
        self.assertAlmostEqual(expected['centered'], expected['coordinates'], places=14)
        for arm, net in fitted.items():
            result = report['reports'][arm]
            self.assertEqual((result['updates'], result['observed_events_per_update'], result['parameters']),
                             (1, 3, run.PARAMETERS[arm]))
            self.assertAlmostEqual(result['curve'][0][1], expected[arm], places=14)
            self.assertTrue(math.isfinite(result['final_observed_train_nll']))
            self.assertNotEqual(result['initial_sha256'], result['final_sha256'])
            self.assertTrue(any(p.grad is not None and bool(p.grad.abs().sum() > 0) for p in net.parameters()))
            self.assertFalse(net.training)
        self.assertEqual(observed, original); self.assertEqual(before, fingerprint(world.state_dict()))
        self.assertTrue(all(p.grad is None for p in world.parameters()))
        self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))

    def test_invalid_budget_gold_labels_and_unfrozen_world_fail(self):
        settings = dict(run.protocol()['fit'], updates=1)
        for key, value in (('updates', True), ('updates', 0), ('learning_rate', 0), ('gradient_clip', float('nan'))):
            with self.subTest(key=key), self.assertRaises(ValueError):
                run.fit_pair(toy_inputs(), toy_world(), 7, dict(settings, **{key: value}))
        observed = toy_inputs(); observed['episodes'][0]['utterances'][0]['order'] = 0
        with self.assertRaises(ValueError): run.fit_pair(observed, toy_world(), 7, settings)
        world = toy_world().train()
        with self.assertRaises(ValueError): run.fit_pair(toy_inputs(), world, 7, settings)
        self.assertTrue(world.training)


class CoordinatePipelineTests(unittest.TestCase):
    def test_roundtrip_includes_centering_retention_and_rejects_stage_reuse(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); prepared, config = fixture(root)
            with synthetic(root, config, retention=True) as stdout:
                run.fit(prepared, root / 'fit', 'a' * 40)
                restored = run.load_models(root / 'fit', config, prepared)
                self.assertEqual(set(restored), {'centered/7', 'coordinates/7'})
                self.assertTrue(all(not p.requires_grad for net in restored.values() for p in net.parameters()))
                completed = _read(root / 'fit/completed-7.json')
                self.assertEqual(set(completed['checkpoints']), set(run.ARMS))
                run.collect(prepared, root / 'fit', root / 'traces', 'b' * 40)
                archive = root / 'results/centering-v1/traces'; archive.mkdir(parents=True)
                for law in ('nand', 'nor'):
                    trace = _read(root / 'traces' / f'trace-{law}-7-centered-fresh.json.xz')
                    _write(archive / f'trace-{law}-7-centered-fresh.json.xz', trace)
                scoring.score(prepared, root / 'fit', root / 'traces', root / 'score')
                decision = _read(root / 'score/decision.json')
                self.assertEqual(json.loads(stdout.getvalue().splitlines()[-1]), decision)
                self.assertFalse(decision['scientific_admission']); self.assertTrue(decision['execution_complete'])
                summary = _read(root / 'score/summary.json.xz')
                for pair in summary['comparisons'].values():
                    retained = pair['retention']['centered']['centering_retention']
                    self.assertEqual(retained['regressions'], []); self.assertEqual(retained['mean_nll_change'], 0.)
                self.assertEqual(len(_read(root / 'traces/manifest.json')['artifacts']), 8)
                paths = [root / 'fit/checkpoints.json.xz', root / 'traces/manifest.json', root / 'score/decision.json']
                saved = [p.read_bytes() for p in paths]
                for call in (lambda: run.fit(prepared, root / 'fit', 'a' * 40),
                             lambda: run.collect(prepared, root / 'fit', root / 'traces', 'b' * 40),
                             lambda: scoring.score(prepared, root / 'fit', root / 'traces', root / 'score')):
                    with self.assertRaises(FileExistsError): call()
                self.assertEqual(saved, [p.read_bytes() for p in paths])

    def test_missing_trace_stops_before_any_oracle_decode(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); prepared, config = fixture(root)
            with synthetic(root, config):
                run.fit(prepared, root / 'fit', 'a' * 40)
                run.collect(prepared, root / 'fit', root / 'traces', 'b' * 40)
                path = root / 'traces/manifest.json'; manifest = _read(path)
                manifest['artifacts'].pop(next(iter(manifest['artifacts'])))
                path.unlink(); _write(path, manifest); reads = []
                def read(path): reads.append(str(path)); return _read(path)
                with patch.object(run.io, '_read', side_effect=read), self.assertRaises(ValueError):
                    scoring.score(prepared, root / 'fit', root / 'traces', root / 'score')
                self.assertFalse(any('oracle' in path for path in reads))
                self.assertFalse((root / 'score').exists())

    def test_initialization_capacity_exposure_state_and_reproduction_tampering_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); prepared, config = fixture(root)
            with synthetic(root, config):
                run.fit(prepared, root / 'fit', 'a' * 40)
                path = root / 'fit/checkpoints.json.xz'; original = _read(path)
                for mutation in ('receipt', 'initial', 'updates', 'parameters', 'swap', 'tensor', 'missing', 'archive'):
                    saved = deepcopy(original); report = saved['reports']['7']
                    if mutation == 'receipt': report['initialization']['unchanged_scalars'] = 84
                    elif mutation == 'initial': report['reports']['coordinates']['initial_sha256'] = report['reports']['centered']['initial_sha256']
                    elif mutation == 'updates': report['reports']['coordinates']['updates'] = 2
                    elif mutation == 'parameters': report['reports']['coordinates']['parameters'] = 89
                    elif mutation == 'swap': saved['checkpoints']['coordinates/7'], saved['checkpoints']['centered/7'] = saved['checkpoints']['centered/7'], saved['checkpoints']['coordinates/7']
                    elif mutation == 'tensor': saved['checkpoints']['coordinates/7']['state']['order.bias'][0] += .1
                    elif mutation == 'missing': saved['checkpoints'].pop('centered/7')
                    else: saved['control_reproduction'] = {'synthetic': False}
                    path.unlink(); _write(path, saved)
                    with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                        run.load_models(root / 'fit', config, prepared)

    def test_real_control_guard_compares_tensors_initial_states_and_training(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); prepared, config = fixture(root)
            with synthetic(root, config): run.fit(prepared, root / 'fit', 'a' * 40)
            saved = _read(root / 'fit/checkpoints.json.xz'); archive = deepcopy(saved)
            receipt = run.verify_control_reproduction(saved['checkpoints'], saved['reports'], archive)
            self.assertTrue(receipt['7']['matched'])
            for mutation in ('curve', 'tensor', 'initial', 'training', 'world'):
                changed = deepcopy(archive); report = changed['reports']['7']
                if mutation == 'curve': report['reports']['centered']['curve'][0][1] += .01
                elif mutation == 'tensor': changed['checkpoints']['centered/7']['state']['order.bias'][0] += .1
                elif mutation == 'initial': report['initialization']['states']['centered']['order.bias'][0] += .1
                elif mutation == 'training': report['training_input_sha256'] = '0' * 64
                else: report['world_state_sha256'] = '0' * 64
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    run.verify_control_reproduction(saved['checkpoints'], saved['reports'], changed)


if __name__ == '__main__': unittest.main()
