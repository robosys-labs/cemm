"""Synthetic runner boundaries; no research fitting, checkpoints or task bank."""
from contextlib import contextmanager, ExitStack, redirect_stdout
from copy import deepcopy
import io
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch
from torch import nn

from experiments.predictive_nucleus import effect_role_run as run, effect_role_model as model
from experiments.predictive_nucleus import effect_role_scoring as scoring
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint
from experiments.predictive_nucleus.tests.test_effect_role_model import bank


SETTINGS = {'updates': 1, 'learning_rate': .02, 'gradient_clip': 5., 'teach_weight': .5, 'cpu_seconds_per_fit': 400}


def small_net():
    net = nn.Linear(1, 1, bias=False, dtype=DTYPE)
    with torch.no_grad(): net.weight.fill_(.5)
    return net


@contextmanager
def synthetic_fit(objective=None):
    net, world, gradients = small_net(), small_net().eval().requires_grad_(False), []
    class Optimizer:
        def __init__(self, parameters, **kwargs): self.parameters = list(parameters)
        def zero_grad(self, **kwargs):
            for parameter in self.parameters: parameter.grad = None
        def step(self): gradients.append(float(net.weight.grad))
    def default(arm, candidate, native, groups, labels=None):
        return candidate.weight.sum() * (2 if groups == ['teach'] else 4), 1 if groups == ['teach'] else 100
    with patch.object(run, 'learner', return_value=net), patch.object(run, 'objective', side_effect=objective or default), \
         patch.object(torch.optim, 'Adam', Optimizer):
        yield net, world, gradients


@contextmanager
def saved_fit():
    with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
        root = Path(directory); data, fitted = root / 'data', root / 'fit'; data.mkdir(); fitted.mkdir()
        write = run.io._write; inputs = bank()
        for name in ('teach', 'rehearsal'): write(data / f'{name}-inputs.json.xz', inputs)
        write(data / 'freeze.json', {'synthetic': True})
        freeze = {'runtime': {'synthetic': 'runtime'}, 'world_checkpoints': {'nand/7': {'state_sha256': 'native'}}}
        identity = {'source_publication': 'a' * 40, 'runtime': freeze['runtime'], 'freeze_sha256': run.io._hash(data / 'freeze.json')}
        write(fitted / 'attempt.json', identity)
        language = root / 'language.json'; write(language, {'checkpoints': {'coordinates/7': {'state': {}}}})
        config = {'version': 'synthetic', 'model_seeds': [7], 'fit': SETTINGS,
                  'parameters': dict.fromkeys(run.ARMS, 1), 'training_forecasts': {'teach': 1, 'rehearsal': 1}}
        states, reports = {}, {}; initial = fingerprint(small_net().state_dict())
        for arm in run.ARMS:
            key, name = f'{arm}/7', f'{arm}-7.json'; net = small_net()
            with torch.no_grad(): net.weight.fill_(.7)
            digest = fingerprint(net.state_dict())
            states[key] = {'file': name, **write(fitted / name, {'arm': arm, 'seed': 7,
                'state': {k: v.tolist() for k, v in net.state_dict().items()}, 'state_sha256': digest})}
            reports[key] = {'initial_sha256': initial, 'final_sha256': digest, 'world_sha256': 'native',
                'world_unchanged': True, 'updates': 1, 'settings': SETTINGS, 'parameters': 1,
                'optimizer': run.OPTIMIZER, 'fresh_optimizer': True,
                'observed_forecasts_per_update': config['training_forecasts'],
                'final_objective': {'teach': .1, 'rehearsal': .2}}
            write(fitted / f'fit-{arm}-7.json', reports[key])
        saved = {**identity, 'complete': True, 'version': config['version'], 'reports': reports, 'checkpoints': states,
                 'training_input_sha256': {name: run.c.digest(inputs) for name in ('teach', 'rehearsal')}}
        write(fitted / 'training.json', saved)
        stack.enter_context(patch.object(run, 'LANGUAGE', language)); stack.enter_context(patch.object(run.io, 'REPO', root))
        stack.enter_context(patch.object(run.io, '_git', return_value=(data / 'freeze.json').read_text().strip()))
        stack.enter_context(patch.object(run, 'learner', side_effect=lambda *args: small_net()))
        yield data, fitted, config, freeze, saved


def replace(path, value):
    path.unlink(); return run.io._write(path, value)


class EffectRoleRunTests(unittest.TestCase):
    def test_objective_uses_endpoints_except_for_explicit_parser_and_rejects_label_leakage(self):
        raw = torch.tensor([[.1, .2, .3, .4, 0., 0., 0., 0.], [.4, .3, .2, .1, 0., 0., 0., 0.]], dtype=DTYPE).log()
        actions = torch.tensor([[.7, .1, .1, .1], [.1, .2, .6, .1]], dtype=DTYPE).log()
        groups = [{'records': [{'id': 'a'}, {'id': 'b'}], 'events': [{'target': torch.tensor([1, 2])}]}]
        with patch.object(model, 'forecasts', side_effect=lambda *args: iter([(raw, actions)])):
            for arm in ('grounded', 'text_only'):
                loss, count = run.objective(arm, None, None, groups)
                self.assertAlmostEqual(float(loss), -math.log(.2)); self.assertEqual(count, 2)
                with self.assertRaises(ValueError): run.objective(arm, None, None, groups, {})
            loss, _ = run.objective('parser', None, None, groups, {'a': [2], 'b': [0]})
            self.assertAlmostEqual(float(loss), -math.log(.1))
            for bad in (None, {}, {'a': [True], 'b': [0]}, {'a': [4], 'b': [0]},
                        {'a': [0, 1], 'b': [0]}, {'a': [0], 'b': [0], 'extra': [0]}):
                with self.subTest(labels=bad), self.assertRaises(ValueError):
                    run.objective('parser', None, None, groups, bad)

    def test_fit_weights_means_equally_despite_different_tape_sizes(self):
        with synthetic_fit() as (net, world, gradients):
            before = fingerprint(world.state_dict())
            _, report = run.fit_one('grounded', 7, {}, world,
                                   {'teach': ['teach'], 'rehearsal': ['rehearsal']}, None, SETTINGS)
            self.assertEqual(gradients, [3.])  # .5*2 + .5*4; not weighted by 1 versus 100 observations.
            self.assertEqual(report['observed_forecasts_per_update'], {'teach': 1, 'rehearsal': 100})
            self.assertEqual(report['final_objective'], {'teach': 1., 'rehearsal': 2.})
            self.assertEqual(report['optimizer'], run.OPTIMIZER); self.assertTrue(report['fresh_optimizer'])
            self.assertEqual(fingerprint(world.state_dict()), before)

    def test_fit_loader_opens_labels_only_for_parser_and_never_opens_an_evaluator(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory); data, output, language = root / 'data', root / 'fit', root / 'language.json'
            observed = {'teach': bank(('lights',)), 'rehearsal': bank()}
            registry = model.create_registry([observed['rehearsal'], observed['teach']])
            labels = {'version': 'effect-role-parser-labels-v1', 'teach_input_sha256': run.c.digest(observed['teach']),
                'rehearsal_input_sha256': run.c.digest(observed['rehearsal']), 'teach': {'synthetic': [3]},
                'rehearsal': {'synthetic': [0]}}
            files = {str(data / 'lexical-registry.json'): registry, str(data / 'parser-labels.json.xz'): labels,
                     str(language): {'checkpoints': {'coordinates/7': {'state': {'synthetic_parent': True}}}},
                     **{str(data / f'{name}-inputs.json.xz'): value for name, value in observed.items()}}
            opened, fitted = [], []
            def read(path):
                opened.append(path.name); return files[str(path)]
            def one(arm, seed, parent, world, tapes, supplied_labels, settings):
                self.assertEqual(parent, {'synthetic_parent': True})
                self.assertEqual(set(tapes), {'teach', 'rehearsal'})
                self.assertEqual(supplied_labels, labels if arm == 'parser' else None)
                fitted.append(arm)
                return small_net(), {'final_objective': {'teach': .1, 'rehearsal': .2}}
            frozen = {'runtime': {'synthetic': True}}
            stack.enter_context(patch.object(run, 'LANGUAGE', language))
            stack.enter_context(patch.object(run, 'verify', return_value=(
                {'model_seeds': [7], 'fit': SETTINGS, 'version': 'synthetic'}, frozen)))
            stack.enter_context(patch.object(run, 'verify_runtime', return_value=frozen['runtime']))
            stack.enter_context(patch.object(run.native, 'publication', side_effect=lambda value: value))
            stack.enter_context(patch.object(run, 'world_for', return_value=small_net().eval().requires_grad_(False)))
            stack.enter_context(patch.object(model, 'pack', side_effect=lambda inputs, *args: [inputs]))
            stack.enter_context(patch.object(run.io, '_read', side_effect=read))
            stack.enter_context(patch.object(run.io, '_hash', return_value='h'))
            stack.enter_context(patch.object(run, 'fit_one', side_effect=one))
            with redirect_stdout(io.StringIO()): run.fit(data, output, 'a' * 40)
            self.assertEqual(fitted, list(run.ARMS)); self.assertEqual(opened.count('parser-labels.json.xz'), 1)
            self.assertFalse(any('evaluator' in name or 'oracle' in name for name in opened))
            self.assertTrue((output / 'training.json').is_file())

    def test_preparation_count_mismatch_fails_before_any_fitting(self):
        inputs = bank(); assets = {'teach': inputs, 'rehearsal': inputs, 'laws': {},
                                  'audit': {'teach_forecasts': 1, 'rehearsal_forecasts': 1}}
        config = {'training_forecasts': {'teach': 1, 'rehearsal': 1}, 'arms': list(run.ARMS),
            'model_seeds': [7], 'execution': {'fits': 3}, 'fresh_episodes_per_law': 1,
            'fresh_forecasts_per_law': 1, 'identifiable_forecasts_per_law': 1, 'ambiguous_forecasts_per_law': 0,
            'held_new_word_forecasts_per_law': 0, 'goal_groups_per_law': 1, 'goal_decisions_per_law': 4,
            'fresh_saved_forecasts': 8}
        for law in run.LAWS:
            assets['laws'][law] = {'inputs': inputs, 'goal_groups': [{'goals': [0, 1, 2, 3]}]}
            assets['audit'][law] = {'episodes': 1, 'forecasts': 1, 'identifiable_forecasts': 1,
                'ambiguous_forecasts': 0, 'held_new_word_forecasts': 0, 'goal_groups': 1, 'goal_decisions': 4}
        run.validate_recipe_counts(config, assets)
        for field in ('fresh_forecasts_per_law', 'goal_decisions_per_law', 'fresh_saved_forecasts'):
            with self.subTest(field=field), self.assertRaises(ValueError):
                run.validate_recipe_counts({**config, field: config[field] + 1}, assets)
        invalid = deepcopy(assets); invalid['teach']['episodes'][0]['utterances'].append(
            deepcopy(invalid['teach']['episodes'][0]['utterances'][0]))
        with self.assertRaises(ValueError): run.validate_recipe_counts(config, invalid)

    def test_fit_invalid_settings_labels_and_mutable_world_stop_before_updates(self):
        tapes = {'teach': ['teach'], 'rehearsal': ['rehearsal']}
        with synthetic_fit() as (_, world, gradients):
            for key, value in (('updates', 0), ('updates', True), ('teach_weight', 0.), ('teach_weight', math.nan),
                               ('gradient_clip', -1.), ('cpu_seconds_per_fit', 0.)):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    run.fit_one('grounded', 7, {}, world, tapes, None, {**SETTINGS, key: value})
            with self.assertRaises(ValueError): run.fit_one('grounded', 7, {}, world, tapes, {}, SETTINGS)
            with self.assertRaises(ValueError): run.fit_one('parser', 7, {}, world, tapes, None, SETTINGS)
            world.requires_grad_(True)
            with self.assertRaises(ValueError): run.fit_one('grounded', 7, {}, world, tapes, None, SETTINGS)
            self.assertEqual(gradients, [])

    def test_final_objective_counts_native_identity_and_cpu_ceiling_are_checked(self):
        for defect in ('nonfinite', 'count', 'world'):
            def objective(arm, net, world, groups, labels=None):
                count = 1
                if not torch.is_grad_enabled():
                    if defect == 'nonfinite': return torch.tensor(math.nan, dtype=DTYPE), count
                    if defect == 'count': count = 2
                    if defect == 'world': world.weight.add_(.1)
                return net.weight.sum(), count
            with self.subTest(defect=defect), synthetic_fit(objective) as (_, world, _), self.assertRaises(ValueError):
                run.fit_one('grounded', 7, {}, world, {'teach': ['teach'], 'rehearsal': ['rehearsal']}, None, SETTINGS)
        with synthetic_fit() as (_, world, _), patch.object(run.time, 'process_time', side_effect=[0., 0., 0., 401.]):
            with self.assertRaisesRegex(ValueError, 'CPU ceiling'):
                run.fit_one('grounded', 7, {}, world, {'teach': ['teach'], 'rehearsal': ['rehearsal']}, None, SETTINGS)

    def test_saved_fit_binds_actual_topology_initialization_optimizer_and_standalone_report(self):
        with saved_fit() as (data, fitted, config, freeze, saved):
            self.assertEqual(run.validate_fit(data, fitted, config, freeze), saved)
            report_path = fitted / 'fit-grounded-7.json'
            replace(report_path, {**saved['reports']['grounded/7'], 'fresh_optimizer': False})
            with self.assertRaisesRegex(ValueError, 'fit recipe/state'): run.validate_fit(data, fitted, config, freeze)
            replace(report_path, saved['reports']['grounded/7'])
            original = deepcopy(saved)
            for field, value in (('optimizer', {**run.OPTIMIZER, 'name': 'SGD'}), ('initial_sha256', 'different'),
                                 ('world_unchanged', False), ('final_objective', {'teach': .1})):
                changed = deepcopy(original); changed['reports']['grounded/7'][field] = value
                replace(fitted / 'training.json', changed); replace(report_path, changed['reports']['grounded/7'])
                with self.subTest(field=field), self.assertRaises(ValueError): run.validate_fit(data, fitted, config, freeze)
            changed = deepcopy(original); record = run.io._read(fitted / 'grounded-7.json')
            record['state']['weight'] = [[.1, .2]]
            record['state_sha256'] = fingerprint({'weight': torch.tensor([[.1, .2]], dtype=DTYPE)})
            changed['reports']['grounded/7']['final_sha256'] = record['state_sha256']
            changed['checkpoints']['grounded/7'].update(replace(fitted / 'grounded-7.json', record))
            replace(fitted / 'training.json', changed); replace(report_path, changed['reports']['grounded/7'])
            with self.assertRaises((ValueError, RuntimeError)): run.validate_fit(data, fitted, config, freeze)

    def test_point_serialization_preserves_only_negative_infinity_and_rejects_nan(self):
        group = {'records': [{'id': 'synthetic'}]}
        raw = torch.tensor([[0.] + [-math.inf] * 7], dtype=DTYPE)
        actions = torch.tensor([[0., -math.inf, -math.inf, -math.inf]], dtype=DTYPE)
        with patch.object(model, 'pack', return_value=[group]), \
             patch.object(model, 'forecasts', side_effect=lambda *args: iter([(raw, actions)])):
            rows = run.points(None, None, None, 'grounded', None, ('canonical',))
            self.assertEqual(rows[0]['logp'][1:], ['negative_infinity'] * 7)
            self.assertEqual(rows[0]['action_logp'][1:], ['negative_infinity'] * 3)
            json.dumps(rows, allow_nan=False)
            for tensor in (raw, actions):
                for bad in (math.nan, math.inf):
                    tensor[0, 0] = bad
                    with self.assertRaisesRegex(ValueError, 'nonfinite forecast'):
                        run.points(None, None, None, 'grounded', None, ('canonical',))
                tensor[0, 0] = 0.
            with self.assertRaises(ValueError): run.points(None, None, None, 'grounded', None, ('canonical', 'canonical'))

    def test_lexical_controls_are_saved_evidence_and_cannot_bless_shared_unknowns(self):
        registry = model.create_registry([bank(), bank(('lights',))]); before = deepcopy(registry)
        tokens = ['g3_unknown_alpha', 'g3_unknown_beta']
        report = run.lexical_controls(registry, tokens)
        self.assertTrue(all(run.validate_lexical_controls(registry, tokens, report).values()))
        self.assertEqual(len({r['id'] for r in report['unknown']}), 2)
        self.assertEqual(report['semantic_model_calls'], 0); self.assertEqual(registry, before)
        broken = deepcopy(report); broken['unknown'][1]['id'] = broken['unknown'][0]['id']
        with self.assertRaisesRegex(ValueError, 'control arithmetic'): run.validate_lexical_controls(registry, tokens, broken)
        broken['checks']['unknown_identities_unresolved'] = False
        self.assertFalse(run.validate_lexical_controls(registry, tokens, broken)['unknown_identities_unresolved'])
        with self.assertRaises(ValueError): run.lexical_controls(registry, ['touches', 'g3_unknown_beta'])

    def test_scientific_failure_writes_every_report_and_does_not_advance_g3(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory); data, fitted, traces, output = (root / n for n in ('data', 'fit', 'traces', 'scores'))
            inputs = bank(); registry = model.create_registry([inputs]); unknown = ['unknown_a', 'unknown_b']
            config = {'model_seeds': [7, 11, 23, 37, 53], 'analysis': {}, 'unknown_tokens': unknown}
            freeze = {'runtime': {'synthetic': True}}; read = run.io._read
            identity = {'weights_publication': 'a' * 40, 'runtime': freeze['runtime'], 'freeze_sha256': 'h', 'training_sha256': 'h'}
            files = {str(data / 'lexical-registry.json'): registry,
                     str(traces / 'lexical-identities.json'): run.lexical_controls(registry, unknown),
                     str(traces / 'attempt.json'): identity}
            artifacts = {'lexical-identities.json': {'sha256': 'h'}}; reports = {}
            for law in run.LAWS:
                files[str(data / f'{law}-inputs.json.xz')] = inputs
                files[str(data / f'{law}-evaluator.json.xz')] = {'synthetic_evaluator': True}
                for seed in config['model_seeds']:
                    for arm in run.ARMS:
                        reports[f'{arm}/{seed}'] = {'final_sha256': 'language'}
                        for name in ('fresh', *run.BANKS) if arm == 'grounded' else ('fresh',):
                            path = traces / f'trace-{law}-{seed}-{arm}-{name}.json.xz'
                            artifacts[path.name] = {'sha256': 'h'}
                            files[str(path)] = {**identity, 'law': law, 'seed': seed, 'arm': arm, 'bank': name,
                                'input_sha256': run.c.digest(inputs), 'state_sha256': 'language', 'points': []}
                    for name, folder in run.BANKS.items():
                        files[str(root / 'data' / folder / f'{law}-inputs.json.xz')] = inputs
                        files[str(root / 'archive' / f'{law}-{seed}-{name}')] = {'input_sha256': run.c.digest(inputs), 'points': []}
            files[str(traces / 'manifest.json')] = {**identity, 'complete': True, 'oracle_opened': False, 'artifacts': artifacts}
            for obj, name, value in ((run, 'ROOT', root),): stack.enter_context(patch.object(obj, name, value))
            stack.enter_context(patch.object(run, 'archive_path', side_effect=lambda law, seed, name: root / 'archive' / f'{law}-{seed}-{name}'))
            stack.enter_context(patch.object(run, 'verify', return_value=(config, freeze)))
            stack.enter_context(patch.object(run, 'validate_fit', return_value={'reports': reports}))
            stack.enter_context(patch.object(run, 'verify_runtime', return_value=freeze['runtime']))
            stack.enter_context(patch.object(run.native, 'publication', side_effect=lambda value: value))
            stack.enter_context(patch.object(run.io, '_read', side_effect=lambda path: files[str(path)]))
            stack.enter_context(patch.object(run.io, '_hash', return_value='h'))
            fresh = stack.enter_context(patch.object(scoring, 'analyze', return_value={'checks': {'fresh': True}}))
            retained = stack.enter_context(patch.object(scoring, 'retention', side_effect=
                [{'checks': {'retained': False}}] + [{'checks': {'retained': True}}] * 59))
            with redirect_stdout(io.StringIO()): run.score(data, fitted, traces, output, 'b' * 40)
            decision, manifest = read(output / 'decision.json'), read(output / 'manifest.json')
            self.assertEqual(decision['decision'], 'REVISE_EFFECT_ROLE_GROUNDING')
            self.assertTrue(decision['execution_complete']); self.assertFalse(decision['g3_complete'])
            self.assertTrue(all(decision['lexical_identity_checks'].values()))
            self.assertEqual(len(manifest['reports']), 10); self.assertEqual((fresh.call_count, retained.call_count), (10, 60))
            self.assertEqual(len(list(output.glob('report-*.json.xz'))), 10)

    def test_invalid_collection_stops_before_reading_any_evaluator(self):
        config = {'model_seeds': [7]}; frozen = {'runtime': {'synthetic': True}}
        base = {'complete': True, 'oracle_opened': False, 'freeze_sha256': 'h', 'runtime': frozen['runtime'],
                'training_sha256': 'h', 'weights_publication': 'a' * 40, 'artifacts': {}}
        opened = []
        def read(path):
            opened.append(path.name); return base
        with patch.object(run.io, '_read', side_effect=read), patch.object(run.io, '_hash', return_value='h'):
            with self.assertRaisesRegex(ValueError, 'collection inventory/binding'):
                run.validate_collection(Path('data'), Path('fit'), Path('traces'), config, frozen)
        self.assertEqual(opened, ['manifest.json', 'attempt.json'])

    def test_exclusive_output_failure_keeps_existing_artifact_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory); sentinel = output / 'attempt.json'; sentinel.write_text('existing')
            def blocked(*args): output.mkdir(exist_ok=False)
            argv = ['runner', 'prepare', '--output', str(output)]
            with patch('sys.argv', argv), patch.object(run, 'prepare', side_effect=blocked), self.assertRaises(FileExistsError):
                run.main()
            self.assertEqual(sentinel.read_text(), 'existing'); self.assertFalse((output / 'failure.json').exists())
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'new'
            def failed(*args):
                output.mkdir(); raise ValueError('synthetic interruption')
            with patch('sys.argv', ['runner', 'prepare', '--output', str(output)]), \
                 patch.object(run, 'prepare', side_effect=failed), self.assertRaises(ValueError): run.main()
            self.assertFalse(run.io._read(output / 'failure.json')['retry_permitted'])


if __name__ == '__main__': unittest.main()
