"""Synthetic warm-start and causal-view checks; no research fit or bank replay."""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import bilingual_model as model, lexical_run as run
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint


def inputs():
    return {'version': 'bilingual-input-v1', 'episodes': [{'id': 'synthetic-lexical',
        'entities': ['Ada', 'Ben', 'Cé'], 'anchor': [0, 0, 0], 'context': [
            {'action': [0, 0, 1, -1], 'reading': [0, 1, 0]},
            {'action': [1, 0, -1, 1], 'reading': [1, 1, 0]}], 'utterances': [
            {'text': 'Ada contacts Ben', 'reading': [1, 0, 0]},
            {'text': 'Cé Ben dax', 'reading': [1, 0, 1]}]}]}


def save_encoder(directory, seed=7, parent=None):
    net = run.previous.learner('grounded', seed)
    saved = {'arm': 'grounded', 'seed': seed, 'state_sha256': fingerprint(net.state_dict()),
             'state': {k: v.tolist() for k, v in net.state_dict().items()}}
    if parent: saved['parent_sha256'] = parent
    name = f'grounded-{seed}.json'
    return {'file': name, 'state_sha256': saved['state_sha256'], **run.io._write(directory / name, saved)}, saved


class LexicalRunTests(unittest.TestCase):
    def setUp(self):
        self.rng = torch.random.get_rng_state(); torch.manual_seed(9517)
        self.world = model.freeze_world(DomainKernel(hidden=3, role_tying=False))
        self.net = model.OrderEncoder()

    def tearDown(self): torch.random.set_rng_state(self.rng)

    def test_checkpoint_roundtrip_is_hash_bound_and_preserves_parent_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory); item, saved = save_encoder(directory)
            before = (directory / item['file']).read_bytes()
            net = run.load_encoder(directory, item, 7)
            self.assertEqual(fingerprint(net.state_dict()), saved['state_sha256'])
            self.assertTrue(all(p.dtype == DTYPE and p.device.type == 'cpu' for p in net.parameters()))
            next(net.parameters()).data.add_(1.)
            self.assertEqual((directory / item['file']).read_bytes(), before)
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                run.load_encoder(directory, {**item, 'sha256': '0' * 64}, 7)

    def test_checkpoint_rejects_silent_casts_wrong_shape_identity_and_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory); item, saved = save_encoder(directory, parent='a' * 64)
            path = directory / item['file']; cases = []
            for value in (True, '0.5', float('nan')):
                bad = deepcopy(saved); bad['state']['order.bias'][0] = value; cases.append(bad)
            bad = deepcopy(saved); bad['state']['order.bias'].append(0.); cases.append(bad)
            bad = deepcopy(saved); bad['seed'] = True; cases.append(bad)
            bad = deepcopy(saved); bad['parent_sha256'] = 'b' * 64; cases.append(bad)
            bad = deepcopy(saved); bad['state_sha256'] = 'b' * 64; cases.append(bad)
            for invalid in cases:
                path.write_text(json.dumps(invalid))
                changed = {**item, 'sha256': run.io._hash(path)}
                with self.subTest(invalid=invalid.get('seed')), self.assertRaises(ValueError):
                    run.load_encoder(directory, changed, 7, parent_sha256='a' * 64)

    def test_primary_is_unchanged_and_every_view_reuses_the_same_actual_prefix(self):
        group = run.previous.pack(inputs(), self.world)[0]
        original_features = [e['features'].clone() for e in group['events']]
        before = fingerprint(self.world.state_dict())
        outputs = list(run.paired_forecasts(self.net, self.world, group))
        primary = [row for row in outputs if row[0] == 'grounded']
        expected = list(run.previous.forecasts('grounded', self.net, self.world, group))
        self.assertEqual([(arm, t) for arm, t, _, _ in outputs],
                         [('grounded', 0), ('grounded', 1), ('masked', 1), ('swapped', 1), ('cross_order', 1)])
        for actual, native in zip(primary, expected, strict=True):
            self.assertTrue(torch.equal(actual[2], native[0]))
            self.assertTrue(torch.equal(actual[3], native[1]))
        for arm, t, actual, order in outputs[2:]:
            alternate = {**group, 'events': [*group['events'][:-1], {**group['events'][-1],
                'features': run.view_features(group, group['events'][-1], arm)}]}
            reference = list(run.previous.forecasts('grounded', self.net, self.world, alternate))[-1]
            self.assertTrue(torch.equal(actual, reference[0]), arm)
            self.assertTrue(torch.equal(order, reference[1]), arm)
        self.assertEqual(before, fingerprint(self.world.state_dict()))
        self.assertTrue(all(torch.equal(a, b['features']) for a, b in zip(original_features, group['events'], strict=True)))

    def test_final_truth_is_never_consumed_by_any_view(self):
        group = run.previous.pack(inputs(), self.world)[0]
        outputs = list(run.paired_forecasts(self.net, self.world, group))
        # An invalid final post would fail native receive; all final predictions
        # must still be available because no subsequent event needs this reading.
        group['events'][-1]['post'] = torch.full((1, 3), 2., dtype=DTYPE)
        changed = list(run.paired_forecasts(self.net, self.world, group))
        for a, b in zip(outputs, changed, strict=True): self.assertTrue(torch.equal(a[2], b[2]))
        group['events'][0]['post'] = torch.full((1, 3), 2., dtype=DTYPE)
        stream = run.paired_forecasts(self.net, self.world, group)
        self.assertTrue(torch.isfinite(next(stream)[2]).all())
        with self.assertRaises(ValueError): next(stream)

    def test_later_gradient_reaches_prior_language_but_not_native_parameters(self):
        group = run.previous.pack(inputs(), self.world)[0]
        stream = run.paired_forecasts(self.net, self.world, group)
        _, _, _, first_order = next(stream)
        _, _, final, _ = next(stream)
        gradient, = torch.autograd.grad(final[0, 0], first_order)
        self.assertTrue(torch.isfinite(gradient).all())
        self.assertGreater(float(gradient.abs().sum()), 1e-12)
        self.assertTrue(all(p.grad is None for p in self.world.parameters()))

    def test_current_lexical_mask_and_swaps_preserve_entities_and_context(self):
        group = run.previous.pack(inputs(), self.world)[0]; event = group['events'][-1]
        masked = run.view_features(group, event, 'masked')
        self.assertTrue(torch.equal(masked[:, :, 0], event['features'][:, :, 0]))
        self.assertEqual(float(masked[:, :, 1:].abs().sum()), 0.)
        swapped, _ = model.tokenize_batch(['Cé Ben vok'], [['Ada', 'Ben', 'Cé']])
        borrowed, _ = model.tokenize_batch(['Cé Ben contacts'], [['Ada', 'Ben', 'Cé']])
        self.assertTrue(torch.equal(run.view_features(group, event, 'swapped'), swapped))
        self.assertTrue(torch.equal(run.view_features(group, event, 'cross_order'), borrowed))
        self.assertNotEqual(float(event['features'][:, :, 1:].abs().sum()), 0.)

    def test_one_update_uses_only_observed_targets_and_warm_start_and_rejects_overwrite(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory); data = root / 'data'; data.mkdir(); parent = root / 'parent'; parent.mkdir()
            output = root / 'fit'; item, _ = save_encoder(parent)
            run.io._write(data / 'freeze.json', {'synthetic': True})
            run.io._write(data / 'train-inputs.json.xz', inputs())
            config = {'version': 'synthetic-v1', 'model_seeds': [7], 'fit': {'updates': 1,
                'learning_rate': .02, 'gradient_clip': 5., 'cpu_seconds_per_fit': 30.,
                'training_forecasts_per_update': 2}}
            freeze = {'checkpoints': {}, 'language_checkpoints': {'7': item}}
            stack.enter_context(patch.object(run, 'verify', return_value=(config, freeze)))
            stack.enter_context(patch.object(run, 'PARENT_FIT', parent))
            stack.enter_context(patch.object(run.io, '_runtime', return_value={'synthetic': True}))
            stack.enter_context(patch.object(run.io, '_git', return_value='synthetic-commit'))
            stack.enter_context(patch.object(run.previous.old, 'checkpoints', return_value={}))
            factory = stack.enter_context(patch.object(run.previous, 'world_for', return_value=self.world))
            reader = stack.enter_context(patch.object(run.io, '_read', wraps=run.io._read))
            stack.enter_context(redirect_stdout(StringIO()))
            before = fingerprint(self.world.state_dict()); run.fit(data, output)
            self.assertEqual([Path(c.args[0]).name for c in reader.call_args_list], ['train-inputs.json.xz'])
            training = run.io._read(output / 'training.json'); report = training['reports']['grounded/7']
            self.assertTrue(training['complete'])
            self.assertEqual(set(training['checkpoints']), {'grounded/7'})
            self.assertEqual(report['initial_sha256'], item['state_sha256'])
            self.assertNotEqual(report['final_sha256'], item['state_sha256'])
            self.assertEqual(report['parent_sha256'], item['sha256'])
            self.assertEqual(report['optimizer'], 'fresh_Adam')
            self.assertEqual((report['updates'], report['training_forecasts_per_update']), (1, 2))
            run.load_encoder(output, training['checkpoints']['grounded/7'], 7, parent_sha256=item['sha256'])
            self.assertEqual(fingerprint(self.world.state_dict()), before)
            self.assertEqual(run.io._hash(parent / item['file']), item['sha256'])
            calls = factory.call_count
            with self.assertRaises(FileExistsError): run.fit(data, output)
            self.assertEqual(factory.call_count, calls)
            retained = root / 'retained'; retained.mkdir()
            for law in run.previous.old.LAWS:
                run.io._write(data / f'{law}-inputs.json.xz', inputs())
                run.io._write(retained / f'{law}-inputs.json.xz', inputs())
            stack.enter_context(patch.object(run, 'PARENT_DATA', retained))
            stack.enter_context(patch.object(run.io, '_committed'))
            results = root / 'results'; evaluated = []
            def evaluate(actual_data, actual_output, actual_config, actual_freeze, actual_fit):
                self.assertEqual((actual_data, actual_output, actual_fit), (data, results, output))
                self.assertTrue(all('oracle' not in str(call.args[0]) and
                    not Path(call.args[0]).name.startswith('trace-') for call in reader.call_args_list))
                expected = {f'trace-{law}-7-{arm}.json.xz' for law in run.previous.old.LAWS for arm in run.ARMS}
                self.assertEqual({p.name for p in results.glob('trace-*.json.xz')}, expected)
                total = 0
                for name in expected:
                    trace = run.io._read(results / name); total += len(trace['points'])
                    if trace['arm'] in run.VIEWS:
                        self.assertEqual([row['step'] for row in trace['points']], [1])
                    expected_hash = item['sha256'] if trace['arm'] == 'prior' else training['checkpoints']['grounded/7']['sha256']
                    self.assertEqual(trace['checkpoint_sha256'], expected_hash)
                self.assertEqual(total, 18)
                evaluated.append(True)
                return {'decision': {'decision': 'KEEP_SYNTHETIC', 'execution_complete': True}}
            stack.enter_context(patch.dict(sys.modules, {
                'experiments.predictive_nucleus.lexical_scoring': SimpleNamespace(evaluate=evaluate)}))
            run.collect(data, output, results)
            self.assertEqual(evaluated, [True]); calls = factory.call_count
            self.assertTrue(run.io._read(results / 'manifest.json')['execution_complete'])
            # A stale/misreported warm start fails before collection can run a world.
            training['reports']['grounded/7']['initial_sha256'] = '0' * 64
            (output / 'training.json').write_text(json.dumps(training))
            with self.assertRaisesRegex(ValueError, 'incomplete or substituted'):
                run.collect(data, output, root / 'bad-results')
            self.assertEqual(factory.call_count, calls)
            self.assertFalse((root / 'bad-results').exists())


if __name__ == '__main__': unittest.main()
