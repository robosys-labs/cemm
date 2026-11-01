"""Synthetic centering-study boundaries; never fit or score research checkpoints."""
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

from experiments.predictive_nucleus import centering_run as run, centering_scoring as scoring
from experiments.predictive_nucleus import saturation_data as data, saturation_run as previous
from experiments.predictive_nucleus.continuation_run import _read, _write
from experiments.predictive_nucleus.joint_objective import fingerprint
from experiments.predictive_nucleus.tests.test_saturation_study import toy_inputs, toy_world


def fixture(root):
    prepared = root / 'prepared'; prepared.mkdir()
    _write(prepared / 'freeze.json', {})
    _write(prepared / 'train-inputs.json.xz', toy_inputs())
    retained = root / 'data' / 'synthetic-retention'; retained.mkdir(parents=True)
    for law in ('nand', 'nor'):
        records, cases = [], []
        for direction in (0, 1):
            for polarity in (0, 1):
                record, gold = data.episode(['synthetic-centering-only'], 3, (0, 1, 0), 0,
                    direction, law, ((0, 1),), [(4, polarity)], [1])
                gold.update(family='toy', polarity=polarity,
                    lexical_pair_id='lex-' + str(direction), role_pair_id='role-' + str(polarity))
                records.append(record); cases.append(gold)
        inputs = {'version': 'bilingual-input-v1', 'episodes': records}
        gold = {'version': 'binding-oracle-v1', 'input_sha256': run.c.digest(inputs), 'episodes': cases}
        for folder in (prepared, retained):
            _write(folder / f'{law}-inputs.json.xz', inputs)
            _write(folder / f'{law}-oracle.json.xz', gold)
    config = deepcopy(run.protocol()); config.update(model_seeds=[7], train_forecasts=3)
    config['fit']['updates'] = 1
    return prepared, config


@contextmanager
def synthetic(root, prepared, config, *, retention=False):
    banks = {'saturation_retention': 'synthetic-retention'} if retention else {}
    with patch.object(run, 'verify', return_value=(config, {'checkpoints': {}})), \
         patch.object(run.io, '_runtime', return_value={'synthetic': True}), \
         patch.object(run.io, 'ROOT', root), patch.object(run, 'BANKS', banks), \
         patch.object(run.prior, 'world_for', return_value=toy_world()), redirect_stdout(StringIO()) as stdout:
        yield stdout


class CenteringInitializationTests(unittest.TestCase):
    def test_exact_one_scalar_intervention_and_receipt_at_every_prescribed_seed(self):
        rng = torch.random.get_rng_state().clone()
        for seed in (7, 11, 23, 37, 53):
            models, receipt = run.initial_pair(seed)
            control, candidate = (models[a].state_dict() for a in run.ARMS)
            changed = [k for k in control if not torch.equal(control[k], candidate[k])]
            self.assertEqual(changed, ['layout.0.bias'])
            self.assertEqual((receipt['changed_scalars'], receipt['unchanged_scalars']), (1, 88))
            self.assertEqual(receipt['changed_key'], changed[0])
            for arm, model in models.items():
                self.assertEqual(fingerprint(model.state_dict()), receipt['initial_sha256'][arm])
                self.assertEqual(sum(p.numel() for p in model.parameters()), 89)
                self.assertTrue(all(p.requires_grad for p in model.parameters()))
            layout = torch.ones(3, 3, dtype=torch.float64) - torch.eye(3, dtype=torch.float64)
            self.assertAlmostEqual(float(models['centered'].layout[0](layout).mean().detach()), 0., places=15)
            self.assertEqual(receipt, run.initial_pair(seed)[1])
        self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))

    def test_initializer_rejects_wrong_bias_or_any_second_tensor_change(self):
        original = run.encoder
        for key in ('layout.0.bias', 'lexical.0.weight'):
            def altered(arm, seed):
                model = original(arm, seed)
                if arm == 'centered':
                    with torch.no_grad(): dict(model.named_parameters())[key].flatten()[0].add_(0.125)
                return model
            with self.subTest(key=key), patch.object(run, 'encoder', side_effect=altered), self.assertRaises(ValueError):
                run.initial_pair(7)


class CenteringTrainingTests(unittest.TestCase):
    def test_one_step_uses_unchanged_observed_loss_and_preserves_world_history_rng(self):
        observed, world = toy_inputs(), toy_world(); original = deepcopy(observed)
        before = fingerprint(world.state_dict()); rng = torch.random.get_rng_state().clone()
        models, receipt = run.initial_pair(7); groups = run.prior.pack(observed, world)
        self.assertIs(run.loss, previous.loss)
        expected = {arm: float(previous.loss(net, world, groups)[0].detach()) for arm, net in models.items()}
        fitted, report = run.fit_pair(observed, world, 7, dict(run.protocol()['fit'], updates=1))
        self.assertEqual(report['initialization'], receipt)
        for arm, net in fitted.items():
            result = report['reports'][arm]
            self.assertEqual((result['updates'], result['observed_events_per_update'], result['parameters']), (1, 3, 89))
            self.assertAlmostEqual(result['curve'][0][1], expected[arm], places=12)
            self.assertTrue(math.isfinite(result['final_observed_train_nll']))
            self.assertNotEqual(result['initial_sha256'], result['final_sha256'])
            self.assertTrue(any(p.grad is not None and bool(p.grad.abs().sum() > 0) for p in net.parameters()))
            self.assertFalse(net.training)
        self.assertEqual(observed, original); self.assertEqual(before, fingerprint(world.state_dict()))
        self.assertTrue(all(p.grad is None for p in world.parameters()))
        self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))

    def test_invalid_budget_gold_labels_and_unfrozen_world_fail(self):
        config = dict(run.protocol()['fit'], updates=1)
        for key, value in (('updates', True), ('updates', 0), ('learning_rate', 0), ('gradient_clip', float('nan'))):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                run.fit_pair(toy_inputs(), toy_world(), 7, dict(config, **{key: value}))
        observed = toy_inputs(); observed['episodes'][0]['utterances'][0]['order'] = 0
        with self.assertRaises(ValueError): run.fit_pair(observed, toy_world(), 7, config)
        world = toy_world().train()
        with self.assertRaises(ValueError): run.fit_pair(toy_inputs(), world, 7, config)
        self.assertTrue(world.training)


class CenteringPipelineTests(unittest.TestCase):
    def test_roundtrip_serialization_saturation_retention_and_all_output_reuse_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); prepared, config = fixture(root)
            with synthetic(root, prepared, config, retention=True) as stdout:
                run.fit(prepared, root / 'fit', 'a' * 40)
                restored = run.load_models(root / 'fit', config, prepared)
                self.assertEqual(set(restored), {'unsaturated/7', 'centered/7'})
                self.assertTrue(all(not p.requires_grad for m in restored.values() for p in m.parameters()))
                run.collect(prepared, root / 'fit', root / 'traces', 'b' * 40)
                archive = root / 'results/saturation-v1/traces'; archive.mkdir(parents=True)
                for law in ('nand', 'nor'):
                    trace = _read(root / 'traces' / f'trace-{law}-7-unsaturated-fresh.json.xz')
                    _write(archive / f'trace-{law}-7-unsaturated-fresh.json.xz', trace)
                scoring.score(prepared, root / 'fit', root / 'traces', root / 'score')
                decision = _read(root / 'score/decision.json')
                self.assertEqual(json.loads(stdout.getvalue().splitlines()[-1]), decision)
                self.assertFalse(decision['scientific_admission']); self.assertTrue(decision['execution_complete'])
                summary = _read(root / 'score/summary.json.xz')
                for pair in summary['comparisons'].values():
                    self.assertEqual(pair['retention']['unsaturated']['saturation_retention']['regressions'], [])
                    self.assertEqual(pair['retention']['unsaturated']['saturation_retention']['mean_nll_change'], 0.)
                self.assertEqual(len(_read(root / 'traces/manifest.json')['artifacts']), 8)
                paths = [root / 'fit/checkpoints.json.xz', root / 'traces/manifest.json', root / 'score/decision.json']
                saved = [p.read_bytes() for p in paths]
                calls = (lambda: run.fit(prepared, root / 'fit', 'a' * 40),
                    lambda: run.collect(prepared, root / 'fit', root / 'traces', 'b' * 40),
                    lambda: scoring.score(prepared, root / 'fit', root / 'traces', root / 'score'))
                for call in calls:
                    with self.assertRaises(FileExistsError): call()
                self.assertEqual(saved, [p.read_bytes() for p in paths])

    def test_missing_trace_stops_before_any_oracle_decode(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); prepared, config = fixture(root)
            with synthetic(root, prepared, config):
                run.fit(prepared, root / 'fit', 'a' * 40)
                run.collect(prepared, root / 'fit', root / 'traces', 'b' * 40)
                path = root / 'traces/manifest.json'; manifest = _read(path)
                manifest['artifacts'].pop(next(iter(manifest['artifacts'])))
                path.unlink(); _write(path, manifest)
                reads = []
                def read(path): reads.append(str(path)); return _read(path)
                with patch.object(run.io, '_read', side_effect=read), self.assertRaises(ValueError):
                    scoring.score(prepared, root / 'fit', root / 'traces', root / 'score')
                self.assertFalse(any('oracle' in path for path in reads))
                self.assertFalse((root / 'score').exists())

    def test_initialization_exposure_arm_swap_and_tensor_tampering_fail(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); prepared, config = fixture(root)
            with synthetic(root, prepared, config): run.fit(prepared, root / 'fit', 'a' * 40)
            path = root / 'fit/checkpoints.json.xz'; original = _read(path)
            for mutation in ('receipt', 'initial', 'updates', 'swap', 'tensor', 'missing'):
                saved = deepcopy(original); report = saved['reports']['7']
                if mutation == 'receipt': report['initialization']['unchanged_scalars'] = 87
                elif mutation == 'initial': report['reports']['centered']['initial_sha256'] = report['reports']['unsaturated']['initial_sha256']
                elif mutation == 'updates': report['reports']['centered']['updates'] = 2
                elif mutation == 'swap': saved['checkpoints']['centered/7'], saved['checkpoints']['unsaturated/7'] = saved['checkpoints']['unsaturated/7'], saved['checkpoints']['centered/7']
                elif mutation == 'tensor': saved['checkpoints']['centered/7']['state']['order.bias'][0] += .1
                else: saved['checkpoints'].pop('unsaturated/7')
                path.unlink(); _write(path, saved)
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    run.load_models(root / 'fit', config, prepared)


class CenteringDecisionTests(unittest.TestCase):
    def test_every_failed_seed_law_probability_or_retention_gate_is_retained(self):
        config = run.protocol()
        saved = {'reports': {str(seed): {'reports': {'centered': {'final_observed_train_nll': .01}}}
                            for seed in config['model_seeds']}}
        reports, comparisons = {}, {}
        checks = ('cell_world_accuracy', 'cell_order_accuracy', 'cell_nll', 'critical_probabilities',
                  'lexical_and_role_pairs', 'lexical_gap', 'masked_invariance', 'swap_equivariance')
        for law in ('nand', 'nor'):
            for seed in config['model_seeds']:
                key = f'{law}/{seed}'
                clean = lambda: {'regressions': [], 'mean_nll_change': -.1}
                reports[key + '/centered'] = {'checks': dict.fromkeys(checks, True)}
                comparisons[key] = {'native': {'centered': clean()},
                    'retention': {'centered': {'old': clean()}}, 'retention_pair': {'old': clean()}, 'fresh_pair': clean()}
        self.assertEqual(scoring.decide(reports, comparisons, saved, config)['decision'], 'KEEP_CENTERED_INITIALIZATION')
        for key in comparisons:
            for check in checks:
                changed = deepcopy(reports); changed[key + '/centered']['checks'][check] = False
                self.assertEqual(scoring.decide(changed, comparisons, saved, config)['decision'], 'REVISE_CENTERING_HYPOTHESIS')
        for target in ('native', 'archive', 'pair_fresh', 'pair_retention', 'nll', 'undefined_nll', 'train'):
            changed, fitted = deepcopy(comparisons), deepcopy(saved); pair = changed['nor/53']
            if target == 'native': pair['native']['centered']['regressions'] = [['x', 0]]
            elif target == 'archive': pair['retention']['centered']['old']['regressions'] = [['x', 0]]
            elif target == 'pair_fresh': pair['fresh_pair']['regressions'] = [['x', 0]]
            elif target == 'pair_retention': pair['retention_pair']['old']['regressions'] = [['x', 0]]
            elif target == 'train': fitted['reports']['53']['reports']['centered']['final_observed_train_nll'] = .06
            else: pair['fresh_pair']['mean_nll_change'] = .001 if target == 'nll' else None
            with self.subTest(target=target):
                self.assertEqual(scoring.decide(reports, changed, fitted, config)['decision'], 'REVISE_CENTERING_HYPOTHESIS')


if __name__ == '__main__': unittest.main()
