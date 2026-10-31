"""Synthetic streaming/training integration; never open a research study bank."""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import bilingual_model as model, bilingual_run as run
from experiments.predictive_nucleus.domain_kernel import DomainKernel
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint


def inputs():
    return {'version': 'bilingual-input-v1', 'episodes': [{'id': 'synthetic-sequence',
        'entities': ['Ada', 'Ben', 'Cé'], 'anchor': [0, 0, 0], 'context': [
            {'action': [0, 0, 1, -1], 'reading': [0, 1, 0]},
            {'action': [1, 0, -1, 1], 'reading': [1, 1, 0]}],
        'utterances': [{'text': 'Ada touches Ben', 'reading': [1, 0, 0]},
                       {'text': 'Cé Ben dax', 'reading': [1, 0, 1]}]}]}


class BilingualRunTests(unittest.TestCase):
    def setUp(self):
        self.rng = torch.random.get_rng_state()
        torch.manual_seed(4217)
        self.world = model.freeze_world(DomainKernel(hidden=3, role_tying=False))
        self.net = model.OrderEncoder()

    def tearDown(self):
        torch.random.set_rng_state(self.rng)

    def test_observed_envelope_rejects_gold_roles_and_pack_preserves_original(self):
        original = inputs(); preserved = deepcopy(original)
        run.pack(original, self.world)
        self.assertEqual(original, preserved)
        for key, value in [('mode', 0), ('language', 'svo'), ('actions', [[0, 0, 1, -1]])]:
            invalid = inputs(); invalid['episodes'][0][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): run.pack(invalid, self.world)
        invalid = inputs(); invalid['episodes'][0]['utterances'][0]['role'] = 0
        with self.assertRaises(ValueError): run.pack(invalid, self.world)

    def test_each_forecast_is_independent_of_its_own_and_future_readings(self):
        original = inputs(); changed = deepcopy(original)
        changed['episodes'][0]['utterances'][0]['reading'] = [0, 1, 1]
        changed['episodes'][0]['utterances'][1]['reading'] = [0, 0, 0]
        for arm in ('grounded', 'sequence', 'text_only'):
            net = self.net if arm == 'grounded' else model.SequenceControl()
            first = next(run.forecasts(arm, net, self.world, run.pack(original, self.world)[0]))[0]
            alternative = next(run.forecasts(arm, net, self.world, run.pack(changed, self.world)[0]))[0]
            self.assertTrue(torch.equal(first, alternative), arm)
            last_only = deepcopy(original)
            last_only['episodes'][0]['utterances'][1]['reading'] = [0, 0, 0]
            before = list(run.forecasts(arm, net, self.world, run.pack(original, self.world)[0]))
            after = list(run.forecasts(arm, net, self.world, run.pack(last_only, self.world)[0]))
            self.assertTrue(all(torch.equal(a[0], b[0]) for a, b in zip(before, after, strict=True)), arm)

    def test_cache_plus_live_prior_matches_direct_native_order_enumeration(self):
        record = inputs()['episodes'][0]
        group = run.pack(inputs(), self.world)[0]
        cached = list(run.forecasts('grounded', self.net, self.world, group))
        pre = torch.tensor([record['anchor']], dtype=DTYPE)
        state = self.world.initial(1)
        for item in record['context']:
            _, pending = self.world.predict(pre, torch.tensor([item['action']]), state)
            pre = torch.tensor([item['reading']], dtype=DTYPE)
            state = self.world.receive(pending, pre)
        for t, event in enumerate(record['utterances']):
            features, mentions = model.tokenize_batch([event['text']], [record['entities']])
            weights = self.net(features).exp()
            joint = torch.zeros(1, 2, 8, dtype=DTYPE)
            for k, action in enumerate(model.action_candidates(mentions).unbind(1)):
                _, pending = self.world.predict(pre, action, state)
                joint = joint + weights[:, k, None, None] * pending.exp()
            self.assertTrue(torch.allclose(cached[t][0].exp(), joint.sum(1), atol=1e-14, rtol=1e-14))
            pre = torch.tensor([event['reading']], dtype=DTYPE)
            state = self.world.receive(joint.log(), pre)

    def test_later_outcome_gradient_reaches_earlier_language_belief(self):
        group = run.pack(inputs(), self.world)[0]
        stream = run.forecasts('grounded', self.net, self.world, group)
        _, first_order = next(stream)
        later_raw, _ = next(stream)
        gradient, = torch.autograd.grad(later_raw[0, 0], first_order)
        self.assertTrue(torch.isfinite(gradient).all())
        self.assertGreater(float(gradient.abs().sum()), 1e-12)

    def test_feedback_is_read_only_after_forecast_yield(self):
        group = run.pack(inputs(), self.world)[0]
        group['events'][0]['post'] = torch.full((1, 3), 2., dtype=DTYPE)
        stream = run.forecasts('grounded', self.net, self.world, group)
        self.assertTrue(torch.isfinite(next(stream)[0]).all())
        with self.assertRaises(ValueError): next(stream)

    def test_one_update_all_controls_fit_without_challenge_oracles_and_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory); data = root / 'data'; data.mkdir(); output = root / 'fit'
            run.io._write(data / 'freeze.json', {'synthetic': True})
            run.io._write(data / 'train-inputs.json.xz', inputs())
            run.io._write(data / 'parser-labels.json', {'synthetic-sequence': [0, 1]})
            config = {'version': 'synthetic-v1', 'model_seeds': [7], 'fit': {
                'updates': 1, 'learning_rate': .01, 'gradient_clip': 5., 'cpu_seconds_per_fit': 30.}}
            freeze = {'checkpoints': {'synthetic': True}}
            stack.enter_context(patch.object(run, 'verify', return_value=(config, freeze)))
            stack.enter_context(patch.object(run.io, '_runtime', return_value={'synthetic': True}))
            stack.enter_context(patch.object(run.io, '_git', return_value='synthetic-commit'))
            stack.enter_context(patch.object(run.old, 'checkpoints', return_value=freeze['checkpoints']))
            worlds = []
            def world_for(*args, **kwargs):
                world = deepcopy(self.world); worlds.append((world, fingerprint(world.state_dict())))
                return world
            factory = stack.enter_context(patch.object(run, 'world_for', side_effect=world_for))
            reader = stack.enter_context(patch.object(run.io, '_read', wraps=run.io._read))
            stack.enter_context(redirect_stdout(StringIO()))
            run.fit(data, output)
            report = run.io._read(output / 'training.json')
            self.assertTrue(report['complete'])
            self.assertEqual(set(report['checkpoints']), {f'{arm}/7' for arm in run.ARMS})
            self.assertTrue(all(row['updates'] == 1 and row['training_forecasts_per_update'] == 2
                                for row in report['reports'].values()))
            self.assertTrue(all(row['initial_sha256'] != row['final_sha256']
                                for row in report['reports'].values()))
            allowed = {'train-inputs.json.xz', 'parser-labels.json', 'training.json'}
            self.assertTrue(all(Path(call.args[0]).name in allowed for call in reader.call_args_list))
            self.assertTrue(all(fingerprint(world.state_dict()) == digest for world, digest in worlds))
            calls = factory.call_count
            with self.assertRaises(FileExistsError): run.fit(data, output)
            self.assertEqual(factory.call_count, calls)

    def test_collection_rejects_incomplete_or_substituted_training_before_forecasting(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory); data = root / 'data'; data.mkdir(); fitted = root / 'fit'; fitted.mkdir()
            run.io._write(data / 'freeze.json', {'synthetic': True})
            config = {'version': 'synthetic-v1', 'model_seeds': [7], 'fit': {'updates': 1}}
            checkpoints, reports = {}, {}
            for arm in run.ARMS:
                filename = f'{arm}-7.json'
                saved = {'arm': arm, 'seed': 7, 'state_sha256': 'f' * 64}
                checkpoints[f'{arm}/7'] = {'file': filename, **run.io._write(fitted / filename, saved)}
                reports[f'{arm}/7'] = {'updates': 1, 'training_forecasts_per_update': 384,
                                      'final_sha256': saved['state_sha256']}
            training = {'complete': True, 'freeze_sha256': run.io._hash(data / 'freeze.json'),
                        'checkpoints': checkpoints, 'reports': reports, 'world_checkpoints_unchanged': True}
            stack.enter_context(patch.object(run, 'verify', return_value=(config, {})))
            stack.enter_context(patch.object(run.io, '_committed'))
            stack.enter_context(patch.object(run.io, '_runtime', return_value={'synthetic': True}))
            factory = stack.enter_context(patch.object(run, 'world_for', side_effect=AssertionError('must not forecast')))
            examples = []
            incomplete = deepcopy(training); incomplete['reports']['grounded/7']['updates'] = 0
            examples.append((incomplete, 'incomplete or substituted'))
            missing = deepcopy(training); del missing['checkpoints']['text_only/7']
            examples.append((missing, 'inventory'))
            identity = deepcopy(training); identity['reports']['parser/7']['final_sha256'] = 'e' * 64
            examples.append((identity, 'identity'))
            for candidate, error in examples:
                path = fitted / 'training.json'
                if path.exists(): path.unlink()
                run.io._write(path, candidate)
                with self.subTest(error=error), self.assertRaisesRegex(ValueError, error):
                    run.collect(data, fitted, root / 'output')
            factory.assert_not_called()
            self.assertFalse((root / 'output').exists())


if __name__ == '__main__': unittest.main()
