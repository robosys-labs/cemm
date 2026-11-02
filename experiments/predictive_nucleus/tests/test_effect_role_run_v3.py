"""Synthetic v3 orchestration boundaries; no real fit, bank or forecast calls."""
from contextlib import contextmanager, ExitStack, redirect_stdout
from copy import deepcopy
import io
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import effect_role_run_v3 as run
from experiments.predictive_nucleus import effect_role_scoring_v3 as scoring
from experiments.predictive_nucleus import effect_role_model as model
from experiments.predictive_nucleus.joint_objective import DTYPE, fingerprint
from experiments.predictive_nucleus.tests.test_effect_role_model import bank
from experiments.predictive_nucleus.tests.test_effect_role_lexical import fixture
from experiments.predictive_nucleus.tests.test_effect_role_run import SETTINGS, replace, small_net


SEEDS = (7, 11, 23, 37, 53)


@contextmanager
def saved_fit():
    """Serialize synthetic initialized states, modifying only acquisition slots."""
    with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
        root = Path(directory); data, fitted = root / 'data', root / 'fit'; data.mkdir(); fitted.mkdir()
        parent, registry, legacy = fixture(); observed = {'teach': bank(('novel_a', 'novel_b')), 'rehearsal': bank()}
        for name, value in observed.items(): run.io._write(data / f'{name}-inputs.json.xz', value)
        run.io._write(data / 'lexical-registry.json', registry); run.io._write(data / 'freeze.json', {'synthetic': True})
        language = root / 'language.json'; run.io._write(language, {'checkpoints': {'coordinates/7': {
            'state': {k: v.tolist() for k, v in parent.state_dict().items()}}}})
        config = {'version': 'synthetic-v3', 'model_seeds': [7], 'fit': SETTINGS,
            'parameters': {'grounded': 92, 'parser': 92, 'text_only': 1048},
            'training_forecasts': {'teach': 2, 'rehearsal': 1}}
        freeze = {'runtime': {'synthetic': True}, 'world_checkpoints': {'nand/7': {'state_sha256': 'native'}}}
        identity = {'source_publication': 'a' * 40, 'runtime': freeze['runtime'],
                    'freeze_sha256': run.io._hash(data / 'freeze.json')}
        run.io._write(fitted / 'attempt.json', identity); reports, checkpoints = {}, {}
        for arm in run.ARMS:
            net = run.learner(arm, 7, parent.state_dict(), registry, legacy)
            initial = fingerprint(net.state_dict()); protected = fingerprint(parent.state_dict())
            if arm != 'text_only':
                with torch.no_grad(): net.new_coordinates.fill_(.25)
            report = {'initial_sha256': initial, 'final_sha256': fingerprint(net.state_dict()),
                'world_sha256': 'native', 'world_unchanged': True, 'updates': SETTINGS['updates'],
                'settings': SETTINGS, 'parameters': config['parameters'][arm], 'optimizer': run.OPTIMIZER,
                'fresh_optimizer': True, 'observed_forecasts_per_update': config['training_forecasts'],
                'final_objective': {'teach': .1, 'rehearsal': .2}}
            if arm != 'text_only':
                report.update(protected_parameters=88, learned_parameters=4, protected_unchanged=True,
                    protected_initial_sha256=protected, protected_final_sha256=protected,
                    registry_sha256=run.c.digest(registry), legacy_ids=legacy, new_ids=list(net.new_ids))
            key, name = arm + '/7', arm + '-7.json'
            checkpoints[key] = {'file': name, **run.io._write(fitted / name, {'arm': arm, 'seed': 7,
                'state': {k: v.tolist() for k, v in net.state_dict().items()}, 'state_sha256': report['final_sha256']})}
            reports[key] = report; run.io._write(fitted / f'fit-{arm}-7.json', report)
        saved = {**identity, 'complete': True, 'version': config['version'], 'reports': reports,
            'checkpoints': checkpoints, 'training_input_sha256': {k: run.c.digest(v) for k, v in observed.items()}}
        run.io._write(fitted / 'training.json', saved)
        stack.enter_context(patch.object(run, 'LANGUAGE', language))
        stack.enter_context(patch.object(run, 'published_file'))
        yield SimpleNamespace(data=data, fitted=fitted, config=config, freeze=freeze, saved=saved)


@contextmanager
def collected(seeds=SEEDS):
    """Small placeholder bytes with a complete, independently counted inventory."""
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory); data, fitted, traces = [root / n for n in ('data', 'fit', 'traces')]
        for path in (data, fitted, traces): path.mkdir()
        run.io._write(data / 'freeze.json', {}); run.io._write(fitted / 'training.json', {})
        freeze = {'runtime': {'synthetic': True}}; config = {'model_seeds': list(seeds)}
        identity = {'weights_publication': 'a' * 40, 'runtime': freeze['runtime'],
            'freeze_sha256': run.io._hash(data / 'freeze.json'), 'training_sha256': run.io._hash(fitted / 'training.json')}
        run.io._write(traces / 'attempt.json', identity)
        artifacts = {'lexical-identities.json': run.io._write(traces / 'lexical-identities.json', {})}; shards = {}
        for index, (law, seed) in enumerate((law, seed) for law in run.LAWS for seed in seeds):
            shard_id = {'law': law, 'seed': seed, 'execution_publication': 'b' * 40}
            attempt = f'shard-attempt-{law}-{seed}.json'; name = f'shard-{law}-{seed}.json'
            begun = run.io._write(traces / attempt, {**identity, **shard_id})
            members = {}
            for arm, target in run.schedules():
                trace_name = f'trace-{law}-{seed}-{arm}-{target}.json.xz'
                members[trace_name] = run.io._write(traces / trace_name, {'synthetic': trace_name})
            value = {**identity, **shard_id, 'complete': True, 'oracle_opened': False, 'artifacts': members,
                     'resources': {'cpu_seconds': index + 1., 'wall_seconds': 2. * (index + 1), 'peak_rss_kib': 100 + index}}
            shards[f'{law}/{seed}'] = {'file': name, **run.io._write(traces / name, value),
                                     'attempt': {'file': attempt, **begun}}
            artifacts.update(members)
        count = len(run.LAWS) * len(seeds); cpu = count * (count + 1) / 2
        manifest = {**identity, 'complete': True, 'oracle_opened': False, 'artifacts': artifacts, 'shards': shards,
            'resources': {'cpu_seconds': cpu, 'wall_seconds': 2 * cpu, 'peak_rss_kib': 99 + count},
            'resource_aggregation': 'sum of shard executions; publication gaps excluded'}
        run.io._write(traces / 'manifest.json', manifest)
        yield SimpleNamespace(root=root, data=data, fitted=fitted, traces=traces, config=config,
                              freeze=freeze, identity=identity, manifest=manifest)


@contextmanager
def score_inputs():
    """Route named synthetic records, with arithmetic mocked at its public API."""
    with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
        root = Path(directory); data, fitted, traces, output = [root / k for k in ('data', 'fit', 'traces', 'scores')]
        parent_fit = root / 'v2-fit'; real_read = run.io._read
        config = {'model_seeds': list(SEEDS), 'analysis': {}, 'unknown_tokens': ['x', 'y'],
            'reference_v2': {'checkpoint_publication': 'c' * 40, 'implementation_publication': 'd' * 40}}
        freeze = {'runtime': {'synthetic': 'v3'}}
        identity = {'weights_publication': 'a' * 40, 'runtime': freeze['runtime'],
                    'freeze_sha256': 'h', 'training_sha256': 'h'}
        old = {'source_publication': 'd' * 40, 'checkpoints': {}, 'reports': {}}
        files, reports = {str(data / 'lexical-registry.json'): {}, str(traces / 'lexical-identities.json'): {}}, {}
        for seed in SEEDS:
            old['checkpoints'][f'grounded/{seed}'] = {'file': f'grounded-{seed}.json', 'sha256': f'checkpoint-{seed}'}
            old['reports'][f'grounded/{seed}'] = {'final_sha256': f'v2-state-{seed}'}
            for arm in run.ARMS: reports[f'{arm}/{seed}'] = {'final_sha256': f'v3-{arm}-{seed}'}
        files[str(parent_fit / 'training.json')] = old
        for law in run.LAWS:
            observed = {'fresh': {'episodes': [], 'marker': 'fresh-' + law}}
            files[str(data / f'{law}-inputs.json.xz')] = observed['fresh']
            files[str(data / f'{law}-evaluator.json.xz')] = {}
            for version, target in run.OPENED.items():
                observed[target] = {'episodes': [], 'marker': version + '-' + law}
                files[str(root / f'data/effect-role-{version}/{law}-inputs.json.xz')] = observed[target]
                files[str(root / f'data/effect-role-{version}/{law}-evaluator.json.xz')] = {}
            for target, folder in run.BANKS.items():
                observed[target] = {'episodes': [], 'marker': target + law}
                files[str(root / f'data/{folder}/{law}-inputs.json.xz')] = observed[target]
            for seed in SEEDS:
                for arm, target in run.schedules():
                    value = {**identity, 'law': law, 'seed': seed, 'arm': arm, 'bank': target,
                        'input_sha256': run.c.digest(observed[target]),
                        'state_sha256': f'v2-state-{seed}' if arm == 'reference_v2' else f'v3-{arm}-{seed}',
                        'points': [{'marker': f'{law}-{seed}-{arm}-{target}'}]}
                    if arm == 'reference_v2': value.update(source_study='effect-role-v2',
                        source_checkpoint_publication='c' * 40, source_implementation_publication='d' * 40,
                        source_training_sha256='h', source_checkpoint_sha256=f'checkpoint-{seed}',
                        parameters_frozen=True, model_updates=0)
                    files[str(traces / f'trace-{law}-{seed}-{arm}-{target}.json.xz')] = value
                for target in run.BANKS:
                    files[str(root / f'archive/{law}-{seed}-{target}')] = {
                        'input_sha256': run.c.digest(observed[target]), 'points': []}
                files[str(root / f'results/effect-role-v1/traces/trace-{law}-{seed}-grounded-fresh.json.xz')] = {
                    'input_sha256': run.c.digest(observed[run.OPENED['v1']]), 'points': [{'marker': 'archived-v1'}]}
        for name, value in (('ROOT', root), ('PARENT_FIT', parent_fit)):
            stack.enter_context(patch.object(run, name, value))
        stack.enter_context(patch.object(run, 'archive_path', side_effect=lambda law, seed, target: root / f'archive/{law}-{seed}-{target}'))
        stack.enter_context(patch.object(run, 'verify', return_value=(config, freeze)))
        stack.enter_context(patch.object(run, 'validate_fit', return_value={'reports': reports}))
        validation = stack.enter_context(patch.object(run, 'validate_collection', return_value=identity))
        stack.enter_context(patch.object(run, 'validate_lexical_controls', return_value={'identity': True}))
        stack.enter_context(patch.object(run, 'verify_runtime', return_value=freeze['runtime']))
        stack.enter_context(patch.object(run.native, 'publication', side_effect=lambda value: value))
        reads = stack.enter_context(patch.object(run.io, '_read', side_effect=lambda path: files[str(path)]))
        stack.enter_context(patch.object(run.io, '_hash', return_value='h'))
        stack.enter_context(patch.object(run, 'published_file'))
        fresh = stack.enter_context(patch.object(scoring, 'analyze', return_value={'checks': {'fresh': True}}))
        retained = stack.enter_context(patch.object(scoring, 'retention', return_value={'checks': {'retained': True}}))
        opened = stack.enter_context(patch.object(scoring, 'analyze_opened', return_value={'checks': {'retained': True}}))
        yield SimpleNamespace(root=root, data=data, fitted=fitted, traces=traces, output=output, files=files,
            config=config, reads=reads, validation=validation, real_read=real_read,
            fresh=fresh, retained=retained, opened=opened)


@contextmanager
def collection_inputs():
    with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
        root = Path(directory); data, fitted, parent_fit, output = [root / k for k in ('data', 'fit', 'old', 'traces')]
        for path in (data, fitted, parent_fit): path.mkdir()
        _, registry, legacy = fixture(); run.io._write(data / 'lexical-registry.json', registry)
        run.io._write(data / 'freeze.json', {}); language = root / 'language.json'
        run.io._write(language, {'checkpoints': {'coordinates/7': {'state': {}}}})
        config = {'model_seeds': [7], 'unknown_tokens': ['unknown_a', 'unknown_b'],
            'reference_v2': {'checkpoint_publication': 'c' * 40, 'implementation_publication': 'd' * 40}}
        freeze = {'runtime': {'synthetic': True}}; saved = {'checkpoints': {}, 'reports': {}}
        for arm in run.ARMS:
            net = small_net(); name = arm + '-7.json'; digest = fingerprint(net.state_dict())
            saved['checkpoints'][arm + '/7'] = {'file': name, **run.io._write(fitted / name, {
                'arm': arm, 'seed': 7, 'state': {'weight': [[.5]]}, 'state_sha256': digest})}
            saved['reports'][arm + '/7'] = {'final_sha256': digest}
        run.io._write(fitted / 'training.json', saved)
        state = {'weight': torch.tensor([[.7]], dtype=DTYPE)}; digest = fingerprint(state)
        old = {'source_publication': 'd' * 40, 'checkpoints': {'grounded/7': {'file': 'grounded-7.json',
            **run.io._write(parent_fit / 'grounded-7.json', {'arm': 'grounded', 'seed': 7,
                'state': {'weight': [[.7]]}, 'state_sha256': digest})}},
            'reports': {'grounded/7': {'final_sha256': digest}}}
        run.io._write(parent_fit / 'training.json', old)
        for name, value in (('PARENT_FIT', parent_fit), ('LANGUAGE', language)):
            stack.enter_context(patch.object(run, name, value))
        stack.enter_context(patch.object(run, 'verify', return_value=(config, freeze)))
        stack.enter_context(patch.object(run, 'validate_fit', return_value=saved))
        stack.enter_context(patch.object(run, 'verify_runtime', return_value=freeze['runtime']))
        stack.enter_context(patch.object(run, 'weights_publication', side_effect=lambda value, *args: value))
        stack.enter_context(patch.object(run, 'published_file'))
        stack.enter_context(patch.object(run.io, '_git', side_effect=lambda *args: '' if args[0] in ('status', 'merge-base') else 'e' * 40))
        stack.enter_context(patch.object(run, 'world_for', return_value=small_net().eval().requires_grad_(False)))
        current = stack.enter_context(patch.object(run, 'learner', side_effect=lambda *args: small_net()))
        reference = stack.enter_context(patch.object(run.prior, 'learner', side_effect=lambda *args: small_net()))
        observed = stack.enter_context(patch.object(run, 'observations', side_effect=lambda _, law, target: {'marker': law + target}))
        predictions = stack.enter_context(patch.object(run, 'points', return_value=[]))
        yield SimpleNamespace(data=data, fitted=fitted, output=output, config=config,
            current=current, reference=reference, observations=observed, predictions=predictions)


class LexicalRunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.threads = torch.get_num_threads(); torch.set_num_threads(1)

    @classmethod
    def tearDownClass(cls): torch.set_num_threads(cls.threads)

    def test_fit_routes_only_training_observations_and_parser_labels_with_exact_ids(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory); data, output, language = root / 'data', root / 'fit', root / 'language.json'
            _, registry, legacy = fixture(); observed = {'teach': bank(('novel_a', 'novel_b')), 'rehearsal': bank()}
            labels = {'version': 'effect-role-parser-labels-v1', 'teach': {'synthetic': [3, 2]},
                'rehearsal': {'synthetic': [0]}, **{name + '_input_sha256': run.c.digest(value) for name, value in observed.items()}}
            files = {str(data / 'lexical-registry.json'): registry, str(data / 'parser-labels.json.xz'): labels,
                str(language): {'checkpoints': {'coordinates/7': {'state': {}}}},
                **{str(data / f'{name}-inputs.json.xz'): value for name, value in observed.items()}}
            opened, fitted = [], []
            def read(path): opened.append(path.name); return files[str(path)]
            def fit_one(arm, seed, parent, world, tapes, supplied, settings, **kwargs):
                self.assertEqual(kwargs, {'registry': registry, 'legacy_ids': legacy})
                self.assertEqual(supplied, labels if arm == 'parser' else None)
                self.assertEqual(tapes, {name: [value] for name, value in observed.items()})
                fitted.append(arm); return small_net(), {'final_objective': {'teach': .1, 'rehearsal': .2}}
            stack.enter_context(patch.object(run, 'LANGUAGE', language))
            stack.enter_context(patch.object(run, 'verify', return_value=({'model_seeds': [7],
                'fit': SETTINGS, 'version': 'synthetic'}, {'runtime': {}})))
            stack.enter_context(patch.object(run, 'verify_runtime', return_value={}))
            stack.enter_context(patch.object(run.native, 'publication', side_effect=lambda value: value))
            stack.enter_context(patch.object(run, 'world_for', return_value=small_net().eval().requires_grad_(False)))
            stack.enter_context(patch.object(model, 'pack', side_effect=lambda inputs, *args: [inputs]))
            stack.enter_context(patch.object(run.io, '_read', side_effect=read))
            stack.enter_context(patch.object(run.io, '_hash', return_value='h'))
            stack.enter_context(patch.object(run, 'fit_one', side_effect=fit_one))
            with redirect_stdout(io.StringIO()): run.fit(data, output, 'a' * 40)
            self.assertEqual(fitted, list(run.ARMS)); self.assertEqual(opened.count('parser-labels.json.xz'), 1)
            self.assertFalse(any('evaluator' in name or 'oracle' in name for name in opened))

    def test_fit_loader_accepts_only_protected88_and_learned4_metadata(self):
        with saved_fit() as s:
            self.assertEqual(run.validate_fit(s.data, s.fitted, s.config, s.freeze), s.saved)
            for field, value in (('protected_parameters', 87), ('learned_parameters', 5),
                ('protected_unchanged', False), ('protected_initial_sha256', 'foreign'),
                ('protected_final_sha256', 'foreign'), ('registry_sha256', 'foreign'),
                ('legacy_ids', []), ('new_ids', []), ('initial_sha256', 'foreign'),
                ('fresh_optimizer', False), ('final_objective', {'teach': .1})):
                with self.subTest(field=field):
                    changed = deepcopy(s.saved); changed['reports']['grounded/7'][field] = value
                    replace(s.fitted / 'training.json', changed)
                    replace(s.fitted / 'fit-grounded-7.json', changed['reports']['grounded/7'])
                    with self.assertRaises(ValueError): run.validate_fit(s.data, s.fitted, s.config, s.freeze)

    def test_rehashed_parent_mutation_cannot_be_blessed_by_self_consistent_reports(self):
        with saved_fit() as s:
            changed = deepcopy(s.saved); record = run.io._read(s.fitted / 'grounded-7.json')
            state = {k: torch.tensor(v, dtype=DTYPE) for k, v in record['state'].items()}
            next(v for k, v in state.items() if k.startswith('parent.')).view(-1)[0] += .1
            record['state'] = {k: v.tolist() for k, v in state.items()}; record['state_sha256'] = fingerprint(state)
            report = changed['reports']['grounded/7']; report['final_sha256'] = record['state_sha256']
            protected = fingerprint({k.removeprefix('parent.'): v for k, v in state.items() if k.startswith('parent.')})
            report['protected_initial_sha256'] = report['protected_final_sha256'] = protected
            changed['checkpoints']['grounded/7'].update(replace(s.fitted / 'grounded-7.json', record))
            replace(s.fitted / 'fit-grounded-7.json', report); replace(s.fitted / 'training.json', changed)
            with self.assertRaisesRegex(ValueError, 'protected lexical complement'):
                run.validate_fit(s.data, s.fitted, s.config, s.freeze)

    def test_schedule_has_sixteen_traces_and_current_controls_on_both_opened_banks(self):
        expected = {('grounded', name) for name in ('fresh', *run.BANKS, *run.OPENED.values())}
        expected |= {(arm, name) for arm in ('parser', 'text_only') for name in ('fresh', *run.OPENED.values())}
        expected.add(('reference_v2', run.OPENED['v2']))
        self.assertEqual(len(run.schedules()), 16); self.assertEqual(set(run.schedules()), expected)

    def test_complete_shards_seal_exactly160_traces_and_record_summed_costs(self):
        with collected() as s:
            self.assertEqual(len(list(s.traces.iterdir())), 183)
            artifacts, shards, resources = run.shard_inventory(s.traces, s.config, s.identity)
            self.assertEqual((len(artifacts), len(shards)), (161, 10))
            self.assertEqual(resources, {'cpu_seconds': 55., 'wall_seconds': 110., 'peak_rss_kib': 109})
            self.assertEqual(run.validate_collection(s.data, s.fitted, s.traces, s.config, s.freeze), s.manifest)
            (s.traces / 'manifest.json').unlink()
            with patch.object(run, 'verify', return_value=(s.config, s.freeze)), \
                 patch.object(run, 'validate_fit', return_value={}), patch.object(run, 'weights_publication'), \
                 patch.object(run, 'verify_runtime'), redirect_stdout(io.StringIO()):
                run.seal(s.data, s.fitted, s.traces, 'a' * 40)
                sealed = (s.traces / 'manifest.json').read_bytes()
                with self.assertRaises((ValueError, FileExistsError)):
                    run.seal(s.data, s.fitted, s.traces, 'a' * 40)
                self.assertEqual((s.traces / 'manifest.json').read_bytes(), sealed)
            self.assertEqual(run.io._read(s.traces / 'manifest.json'), s.manifest)

    def test_missing_partial_failed_or_unmanifested_collection_is_rejected(self):
        for defect in ('missing_attempt', 'partial', 'missing_trace', 'missing_shard_member',
                       'failed', 'extra_trace', 'extra_file', 'bad_manifest', 'changed_trace'):
            with self.subTest(defect=defect), collected((7,)) as s:
                shard_path = s.traces / 'shard-nand-7.json'; shard = run.io._read(shard_path)
                name = next(iter(shard['artifacts']))
                if defect == 'missing_attempt': (s.traces / 'shard-attempt-nand-7.json').unlink()
                elif defect == 'partial': shard['complete'] = False; replace(shard_path, shard)
                elif defect == 'missing_trace': (s.traces / name).unlink()
                elif defect == 'missing_shard_member': del shard['artifacts'][name]; replace(shard_path, shard)
                elif defect == 'failed': run.io._write(s.traces / 'failure-nand-7.json', {})
                elif defect == 'extra_trace': run.io._write(s.traces / 'trace-foreign.json.xz', {})
                elif defect == 'extra_file': run.io._write(s.traces / 'unmanifested.json', {})
                elif defect == 'bad_manifest':
                    value = deepcopy(s.manifest); value['resources']['cpu_seconds'] += 1; replace(s.traces / 'manifest.json', value)
                else: (s.traces / name).write_bytes(b'changed')
                with self.assertRaises((ValueError, FileNotFoundError)):
                    run.validate_collection(s.data, s.fitted, s.traces, s.config, s.freeze)

    def test_invalid_shard_resource_receipts_are_rejected_before_sealing(self):
        for field, value in (('cpu_seconds', -1.), ('cpu_seconds', True), ('cpu_seconds', math.inf),
                             ('cpu_seconds', math.nan), ('wall_seconds', -1.), ('wall_seconds', math.inf),
                             ('peak_rss_kib', 0), ('peak_rss_kib', 1.5), ('peak_rss_kib', True)):
            with self.subTest(field=field, value=value), collected((7,)) as s:
                path = s.traces / 'shard-nand-7.json'; shard = run.io._read(path)
                shard['resources'][field] = value
                path.write_text(json.dumps(shard))  # Deliberately malformed external receipt, including NaN/Infinity.
                with self.assertRaises(ValueError): run.shard_inventory(s.traces, s.config, s.identity)

    def test_weights_can_be_ancestor_but_must_bind_every_actual_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(run.io, 'REPO', Path(directory)):
            fitted = Path(directory) / 'fit'; saved = {'checkpoints': {'g/7': {'file': 'g.json'}, 'p/7': {'file': 'p.json'}}}
            calls = []
            def git(*args):
                calls.append(args)
                return '' if args[0] in ('status', 'merge-base') else 'same-blob'
            with patch.object(run.io, '_git', side_effect=git):
                self.assertEqual(run.weights_publication('a' * 40, fitted, saved), 'a' * 40)
            self.assertIn(('merge-base', '--is-ancestor', 'a' * 40, 'HEAD'), calls)
            self.assertEqual(len([args for args in calls if args[0] == 'hash-object']), 3)
            for defect in ('dirty', 'ancestor', 'bytes'):
                def bad_git(*args):
                    if defect == 'dirty' and args[0] == 'status': return ' M source.py'
                    if defect == 'ancestor' and args[0] == 'merge-base': return 'not-ancestor'
                    if defect == 'bytes' and args[0] == 'hash-object': return 'different-blob'
                    return git(*args)
                with self.subTest(defect=defect), patch.object(run.io, '_git', side_effect=bad_git), self.assertRaises(ValueError):
                    run.weights_publication('a' * 40, fitted, saved)

    def test_collection_uses_all16_pairs_with_frozen_v2_reference_and_cannot_repeat(self):
        with collection_inputs() as s, redirect_stdout(io.StringIO()):
            run.collect(s.data, s.fitted, s.output, 'a' * 40, 'nand', 7)
            self.assertEqual((s.current.call_count, s.reference.call_count, s.predictions.call_count), (3, 1, 16))
            self.assertEqual(len(list(s.output.glob('trace-*.json.xz'))), 16)
            for observation, prediction in zip(s.observations.call_args_list, s.predictions.call_args_list):
                target = observation.args[2]; arm = prediction.args[3]
                expected = ('canonical', 'masked') if arm == 'grounded' and target not in run.BANKS else ('canonical',)
                self.assertEqual(prediction.args[-1], expected)
            reference = run.io._read(s.output / 'trace-nand-7-reference_v2-opened_effect_role_v2.json.xz')
            self.assertEqual(reference['source_study'], 'effect-role-v2')
            self.assertTrue(reference['parameters_frozen']); self.assertEqual(reference['model_updates'], 0)
            self.assertEqual(reference['runtime'], {'synthetic': True})
            done = s.output / 'shard-nand-7.json'; original = done.read_bytes()
            with self.assertRaises((ValueError, FileExistsError)):
                run.collect(s.data, s.fitted, s.output, 'a' * 40, 'nand', 7)
            self.assertEqual(s.predictions.call_count, 16); self.assertEqual(done.read_bytes(), original)
            self.assertFalse((s.output / 'failure-nand-7.json').exists())
            run.io._write(s.output / 'manifest.json', {'synthetic_sealed_marker': True})
            with self.assertRaisesRegex(ValueError, 'already sealed'):
                run.collect(s.data, s.fitted, s.output, 'a' * 40, 'nor', 7)
            self.assertEqual(s.predictions.call_count, 16)
            self.assertFalse((s.output / 'shard-attempt-nor-7.json').exists())

    def test_reference_mutation_writes_nonretryable_failure_without_completion(self):
        with collection_inputs() as s, redirect_stdout(io.StringIO()):
            def mutate(observed, world, net, arm, registry, views):
                if float(net.weight.detach()[0, 0]) == .7:
                    with torch.no_grad(): net.weight.add_(.1)
                return []
            s.predictions.side_effect = mutate
            with self.assertRaisesRegex(ValueError, 'language changed during collection'):
                run.collect(s.data, s.fitted, s.output, 'a' * 40, 'nand', 7)
            failure = run.io._read(s.output / 'failure-nand-7.json')
            self.assertFalse(failure['retry_permitted']); self.assertEqual(failure['stage'], 'collect')
            self.assertFalse((s.output / 'shard-nand-7.json').exists())
            count = s.predictions.call_count; original = (s.output / 'failure-nand-7.json').read_bytes()
            with self.assertRaises((ValueError, FileExistsError)):
                run.collect(s.data, s.fitted, s.output, 'a' * 40, 'nand', 7)
            self.assertEqual(s.predictions.call_count, count)
            self.assertEqual((s.output / 'failure-nand-7.json').read_bytes(), original)

    def test_orphaned_shard_artifacts_cannot_authorize_another_forward_execution(self):
        for name in ('failure-nand-7.json', 'shard-nand-7.json', 'trace-nand-7-grounded-fresh.json.xz',
                     'trace-nand-7-parser-opened_effect_role_v2.json.xz'):
            with self.subTest(name=name), collection_inputs() as s, redirect_stdout(io.StringIO()):
                s.output.mkdir()
                run.io._write(s.output / 'attempt.json', {'weights_publication': 'a' * 40,
                    'runtime': {'synthetic': True}, 'freeze_sha256': run.io._hash(s.data / 'freeze.json'),
                    'training_sha256': run.io._hash(s.fitted / 'training.json')})
                registry = run.io._read(s.data / 'lexical-registry.json')
                run.io._write(s.output / 'lexical-identities.json', run.lexical_controls(registry, s.config['unknown_tokens']))
                run.io._write(s.output / name, {'synthetic_orphan': True})
                original = (s.output / name).read_bytes()
                with self.assertRaises((ValueError, FileExistsError)):
                    run.collect(s.data, s.fitted, s.output, 'a' * 40, 'nand', 7)
                self.assertEqual(s.predictions.call_count, 0)
                self.assertEqual((s.output / name).read_bytes(), original)
                self.assertFalse((s.output / 'shard-attempt-nand-7.json').exists())

    def test_invalid_collection_stops_before_target_read_or_any_scoring(self):
        with score_inputs() as s:
            s.validation.side_effect = ValueError('synthetic invalid collection')
            with self.assertRaisesRegex(ValueError, 'invalid collection'):
                run.score(s.data, s.fitted, s.traces, s.output, 'b' * 40)
            s.reads.assert_not_called(); s.fresh.assert_not_called(); s.opened.assert_not_called()
            self.assertFalse(s.output.exists())

    def test_valid_opened_failure_keeps_all_ten_reports_and_current_controls(self):
        with score_inputs() as s:
            s.opened.side_effect = [{'checks': {'retained': False}}] + [{'checks': {'retained': True}}] * 19
            with redirect_stdout(io.StringIO()): run.score(s.data, s.fitted, s.traces, s.output, 'b' * 40)
            decision = s.real_read(s.output / 'decision.json'); manifest = s.real_read(s.output / 'manifest.json')
            self.assertEqual(decision['decision'], 'REVISE_EFFECT_ROLE_GROUNDING')
            self.assertTrue(decision['execution_complete']); self.assertFalse(decision['g3_complete'])
            self.assertEqual(decision['next_stage'], 'G3'); self.assertFalse(decision['scientific_admission'])
            self.assertFalse(decision['checks']['nand/7']['opened_v1/retained'])
            self.assertTrue(decision['checks']['nand/7']['opened_v2/retained'])
            self.assertEqual((s.fresh.call_count, s.retained.call_count, s.opened.call_count), (10, 60, 20))
            self.assertEqual(len(manifest['reports']), 10); self.assertEqual(len(list(s.output.glob('report-*.json.xz'))), 10)
            self.assertEqual(set(s.real_read(s.output / 'report-nand-7.json.xz')['opened']), {'v1', 'v2'})
            for call in s.opened.call_args_list:
                _, traces, reference, _, version = call.args
                for arm in ('parser', 'text_only'):
                    self.assertIn('-' + arm + '-opened_effect_role_' + version, traces[arm][0]['marker'])
                self.assertEqual(reference[0]['marker'] == 'archived-v1', version == 'v1')
            self.assertFalse(any('text_only_reproduction' in str(call) for call in s.reads.call_args_list))

    def test_reference_v2_state_and_every_provenance_field_are_bound_before_comparison(self):
        with score_inputs() as s:
            path = s.traces / 'trace-nand-7-reference_v2-opened_effect_role_v2.json.xz'
            original = deepcopy(s.files[str(path)])
            defects = {'state_sha256': 'foreign', 'source_study': 'effect-role-v1',
                'source_checkpoint_publication': 'e' * 40, 'source_implementation_publication': 'e' * 40,
                'source_training_sha256': 'foreign', 'source_checkpoint_sha256': 'foreign',
                'parameters_frozen': False, 'model_updates': 1, 'runtime': {'synthetic': 'wrong-runtime'},
                'input_sha256': 'foreign'}
            for index, (field, value) in enumerate(defects.items()):
                s.files[str(path)] = {**original, field: value}
                with self.subTest(field=field), redirect_stdout(io.StringIO()), self.assertRaises(ValueError):
                    run.score(s.data, s.fitted, s.traces, s.root / f'bad-{index}', 'b' * 40)


if __name__ == '__main__': unittest.main()
