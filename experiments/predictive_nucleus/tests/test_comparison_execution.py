"""Synthetic runner-phase validation. Never fit/score the public comparison."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import torch

from experiments.predictive_nucleus import comparison_execution as run
from experiments.predictive_nucleus import joint_objective as joint
from experiments.predictive_nucleus.informative_curriculum import model_factories


def batch():
    return joint.SensorBatch(torch.tensor([[[0, 1, 0]], [[1, 1, 0]], [[0, 1, 0]], [[0, 1, 0]]],
                                         dtype=torch.float64),
                             torch.tensor([[[0, 0, 1, -1]], [[1, 0, -1, 0]], [[2, -1, -1, -1]]]))


def spec():
    digest = batch().digest()
    return {'models': [{'id': 'flat', 'parameters': 648}], 'seeds': [7],
            'data': {'conditions': ['uninformative', 'informative'], 'event_targets_per_update': 3,
                     'input_sha256': {name + '_same_pair': digest for name in ('uninformative', 'informative')}},
            'controls': ['no_change', 'prefix', 'local', 'contact'],
            'fit': {'total_neural_fits': 4, 'regimes': [
                {'id': 'fixed_exposure', 'updates': 2, 'cpu_seconds': 1.0},
                {'id': 'cpu_budget', 'updates': 2, 'cpu_seconds': 1.0}]}}


def fake_fit(model, data, *, updates, cpu_seconds):
    initial = joint.fingerprint(model.state_dict())
    with torch.no_grad():
        next(model.parameters()).add_(.001)
    return {'parameters': sum(p.numel() for p in model.parameters()), 'completed_updates': updates,
            'requested_updates': updates, 'stop_reason': 'update_limit', 'setup_wall_seconds': 0.,
            'fit_wall_seconds': .1, 'fit_cpu_seconds': .1, 'cpu_ceiling_seconds': cpu_seconds,
            'cpu_overshoot_seconds': 0., 'last_step_cpu_seconds': .05, 'last_preupdate_nll': 1.,
            'events_per_update': data.actions.shape[0] * data.actions.shape[1],
            'training_input_sha256': data.digest(), 'initial_weights_sha256': initial,
            'final_weights_sha256': joint.fingerprint(model.state_dict())}


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.output = self.root / 'new'
        self.spec = spec()
        self.training = {name: batch() for name in self.spec['data']['conditions']}
        self.rng = torch.random.get_rng_state()
        self.addCleanup(torch.random.set_rng_state, self.rng)
        self.factories = patch.object(run, 'model_factories', return_value={'flat': joint.JointFlatGRU})
        self.factories.start()
        self.addCleanup(self.factories.stop)

    def phase(self, fitter=fake_fit):
        with patch.object(joint, 'fit', side_effect=fitter):
            return run._fit_phase(self.spec, self.training, self.output)

    def failure(self):
        data = json.loads((self.output / 'FAILED.json').read_text())
        self.assertEqual(data['status'], 'INCOMPLETE')
        self.assertFalse(data['study_complete'])
        self.assertFalse((self.output / 'COMPLETE').exists())
        self.assertFalse((self.output / 'FIT_PHASE.json').exists())
        return data

    def test_exact_120_fit_rotation_without_factory_or_fitter(self):
        full = spec()
        full['models'] = [{'id': name} for name in model_factories()]
        full['seeds'] = [7, 11, 23, 37, 53]
        full['fit']['total_neural_fits'] = 120
        with patch.object(joint, 'fit', side_effect=AssertionError('not allowed')):
            plan = run.fit_plan(full)
        self.assertEqual(len(plan), 120)
        self.assertEqual([p['ordinal'] for p in plan], list(range(120)))
        names = [m['id'] for m in full['models']]
        for r in range(2):
            for c in range(2):
                for s in range(5):
                    start = ((r * 2 + c) * 5 + s) * 6
                    shift = (r + c + s) % 6
                    self.assertEqual([p['model'] for p in plan[start:start + 6]], names[shift:] + names[:shift])
        self.assertEqual(len({(p['model'], p['seed'], p['condition'], p['regime']) for p in plan}), 120)

    def test_invalid_plan_has_no_partial_execution(self):
        for mutate in (lambda s: s['seeds'].append(7), lambda s: s['seeds'].append(True),
                       lambda s: s['models'].append({'id': '../escape'}),
                       lambda s: s['fit'].update(total_neural_fits=99)):
            item = deepcopy(self.spec)
            mutate(item)
            with self.assertRaises(ValueError):
                run.fit_plan(item)
        self.assertFalse(self.output.exists())

    def test_all_checkpoints_and_tables_retained_but_no_study_success(self):
        result = self.phase()
        self.assertEqual(result['status'], 'FITS_VERIFIED_NOT_EVALUATED')
        self.assertEqual((len(result['fits']), len(result['controls'])), (4, 6))
        self.assertFalse(result['study_complete'])
        self.assertEqual(len(list(self.output.glob('fit-*/*.pt'))), 8)
        self.assertFalse((self.output / 'COMPLETE').exists())
        self.assertEqual(len({r['initial']['tensor_sha256'] for r in result['fits']}), 1)
        self.assertTrue(all(r['events_processed'] == 6 for r in result['fits']))
        self.assertTrue(all(r['measured_events'] == 3 for r in result['controls']))
        self.assertTrue(torch.equal(self.rng, torch.random.get_rng_state()))

    def test_real_one_update_synthetic_training_roundtrips(self):
        for regime in self.spec['fit']['regimes']:
            regime.update(updates=1, cpu_seconds=10.)
        threads = torch.get_num_threads()
        try:
            torch.set_num_threads(1)
            result = run._fit_phase(self.spec, self.training, self.output)
        finally:
            torch.set_num_threads(threads)
        self.assertTrue(all(r['fit']['completed_updates'] == 1 for r in result['fits']))
        self.assertTrue(all(r['initial']['tensor_sha256'] != r['final']['tensor_sha256'] for r in result['fits']))
        self.assertTrue(torch.equal(self.rng, torch.random.get_rng_state()))

    def test_model_never_receives_second_pair_evaluation_inputs(self):
        self.training['informative_second_pair'] = batch()
        with patch.object(joint, 'fit', side_effect=AssertionError('not allowed')):
            with self.assertRaisesRegex(ValueError, 'training-only'):
                run._fit_phase(self.spec, self.training, self.output)
        self.assertFalse(self.output.exists())

    def test_input_hash_mismatch_prevents_fit_and_output_creation(self):
        self.training['informative'].observations[0, 0, 0] = 1
        with self.assertRaisesRegex(ValueError, 'training hash'):
            self.phase()
        self.assertFalse(self.output.exists())

    def test_existing_output_is_untouched(self):
        self.output.mkdir()
        sentinel = self.output / 'sentinel'
        sentinel.write_text('old')
        with self.assertRaises(FileExistsError):
            self.phase()
        self.assertEqual(list(self.output.iterdir()), [sentinel])
        self.assertEqual(sentinel.read_text(), 'old')

    def test_output_inside_source_or_dangling_symlink_is_refused(self):
        with patch.object(run, 'ROOT', self.root):
            with self.assertRaisesRegex(ValueError, 'outside source'):
                self.phase()
        self.output.symlink_to(self.root / 'missing')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.phase()
        self.assertFalse((self.root / 'missing').exists())

    def test_missing_parent_is_not_created(self):
        self.output = self.root / 'missing-parent' / 'out'
        with self.assertRaises(FileNotFoundError):
            self.phase()
        self.assertFalse(self.output.parent.exists())

    def test_fit_failure_preserves_initial_and_failed_partial_without_retry(self):
        calls = []
        def explode(model, data, **kwargs):
            calls.append(1)
            with torch.no_grad():
                next(model.parameters()).fill_(float('nan'))
            raise ValueError('synthetic numerical failure')
        with self.assertRaisesRegex(ValueError, 'synthetic'):
            self.phase(explode)
        failure = self.failure()
        self.assertEqual(calls, [1])
        self.assertEqual(failure['verified_ordinals'], [])
        self.assertEqual(failure['missing_ordinals'], list(range(4)))
        self.assertFalse(failure['failed_partial_state']['usable_as_completed_fit'])
        raw = torch.load(self.output / 'fit-000' / 'FAILED-partial.pt', weights_only=True)
        self.assertTrue(any(torch.isnan(v).any() for v in raw.values()))
        self.assertTrue((self.output / 'fit-000' / 'initial.pt').exists())
        self.assertFalse((self.output / 'fit-001').exists())

    def test_fixed_exposure_early_stop_retains_final_then_aborts(self):
        def early(model, data, **kwargs):
            result = fake_fit(model, data, **kwargs)
            result.update(completed_updates=1, stop_reason='cpu_limit', fit_cpu_seconds=1.2,
                          cpu_overshoot_seconds=1.2 - 1.)
            return result
        with self.assertRaisesRegex(ValueError, 'incomplete fixed'):
            self.phase(early)
        self.failure()
        self.assertTrue((self.output / 'fit-000' / 'final.pt').exists())
        self.assertTrue((self.output / 'fit-000' / 'returned_fit.json').exists())
        self.assertFalse((self.output / 'fit-000' / 'VERIFIED.json').exists())

    def test_invalid_returned_metadata_is_retained_with_strict_nonfinite_tags(self):
        def invalid(model, data, **kwargs):
            result = fake_fit(model, data, **kwargs)
            result['last_preupdate_nll'] = float('nan')
            return result
        with self.assertRaisesRegex(ValueError, 'invalid fit metric'):
            self.phase(invalid)
        self.failure()
        raw = (self.output / 'fit-000' / 'returned_fit.json').read_text()
        self.assertNotIn('NaN', raw)
        self.assertEqual(json.loads(raw)['last_preupdate_nll'], {'value': None, 'status': 'nan'})

    def test_mutated_working_copy_fails_without_corrupting_shared_training(self):
        before = {name: value.digest() for name, value in self.training.items()}
        def mutate(model, data, **kwargs):
            result = fake_fit(model, data, **kwargs)
            data.observations[0, 0, 0] = 1
            return result
        with self.assertRaisesRegex(ValueError, 'mutated sensor'):
            self.phase(mutate)
        self.failure()
        self.assertEqual(before, {name: value.digest() for name, value in self.training.items()})

    def test_later_failure_keeps_verified_earlier_fit_and_never_continues(self):
        calls = []
        def fail_second(model, data, **kwargs):
            calls.append(1)
            if len(calls) == 2:
                raise RuntimeError('second fit failed')
            return fake_fit(model, data, **kwargs)
        with self.assertRaises(RuntimeError):
            self.phase(fail_second)
        failure = self.failure()
        self.assertEqual(failure['verified_ordinals'], [0])
        self.assertEqual(failure['missing_ordinals'], [1, 2, 3])
        self.assertTrue((self.output / 'fit-000' / 'VERIFIED.json').exists())
        self.assertFalse((self.output / 'fit-002').exists())
        self.assertTrue(torch.equal(self.rng, torch.random.get_rng_state()))

    def test_controls_are_fitted_only_after_every_neural_fit(self):
        calls = []
        actual = run.SensorMemory.fit
        def fit_model(model, data, **kwargs):
            calls.append('neural')
            return fake_fit(model, data, **kwargs)
        def control(memory, data):
            self.assertEqual(calls[:4], ['neural'] * 4)
            calls.append('control')
            return actual(memory, data)
        with patch.object(run.SensorMemory, 'fit', new=control):
            result = self.phase(fit_model)
        self.assertEqual(calls, ['neural'] * 4 + ['control'] * 6)
        self.assertEqual(len(result['controls']), 6)

    def test_control_failure_never_publishes_fit_phase_as_verified(self):
        with patch.object(run.SensorMemory, 'fit', side_effect=ValueError('bad control')):
            with self.assertRaisesRegex(ValueError, 'bad control'):
                self.phase()
        failure = self.failure()
        self.assertEqual(failure['phase'], 'controls')
        self.assertEqual(failure['current_control'], {'condition': 'uninformative', 'mode': 'prefix'})
        self.assertEqual(failure['verified_controls'], [])
        self.assertEqual(failure['verified_ordinals'], list(range(4)))
        self.assertEqual(failure['missing_ordinals'], [])

    def test_final_publication_io_failure_removes_partial_phase_marker(self):
        writer = run.write_json
        def fail_publication(path, value):
            result = writer(path, value)
            if Path(path).name == 'FIT_PHASE.json':
                raise OSError('synthetic fsync failure')
            return result
        with patch.object(run, 'write_json', side_effect=fail_publication):
            with self.assertRaisesRegex(OSError, 'fsync'):
                self.phase()
        self.failure()

    def test_checkpoint_hash_is_verified_before_torch_load(self):
        model = joint.JointFlatGRU()
        checkpoint = self.root / 'weights.pt'
        meta = run._save_state(model, checkpoint, joint.JointFlatGRU)
        checkpoint.write_bytes(checkpoint.read_bytes() + b'tampered')
        with patch.object(torch, 'load', side_effect=AssertionError('must not deserialize')):
            with self.assertRaisesRegex(ValueError, 'byte hash'):
                run._restore(joint.JointFlatGRU, checkpoint, meta)

    def test_checkpoint_dtype_mismatch_not_silently_cast(self):
        checkpoint = self.root / 'weights.pt'
        model = joint.JointFlatGRU().float()
        meta = run._save_state(model, checkpoint)
        with self.assertRaisesRegex(ValueError, 'invalid checkpoint tensor'):
            run._restore(joint.JointFlatGRU, checkpoint, meta)

    def test_checkpoint_keys_shapes_nonfinite_and_semantic_hash_are_checked(self):
        model = joint.JointFlatGRU()
        original = run._state(model)
        for mode in ('missing', 'shape', 'nan', 'semantic'):
            values = deepcopy(original)
            key = next(k for k in values if values[k].dtype.is_floating_point)
            if mode == 'missing':
                values.pop(key)
            elif mode == 'shape':
                values[key] = values[key].flatten()
            elif mode == 'nan':
                values[key].flatten()[0] = float('nan')
            path = self.root / f'{mode}.pt'
            torch.save(values, path)
            meta = {'file_sha256': run.digest_file(path), 'tensor_sha256': joint.fingerprint(values)}
            if mode == 'semantic':
                meta['tensor_sha256'] = '0' * 64
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                run._restore(joint.JointFlatGRU, path, meta)

    def test_checkpoint_restore_uses_weights_only_and_preserves_rng(self):
        model = joint.JointFlatGRU()
        path = self.root / 'weights.pt'
        meta = run._save_state(model, path)
        before = torch.random.get_rng_state()
        with patch.object(torch, 'load', wraps=torch.load) as load:
            restored = run._restore(joint.JointFlatGRU, path, meta)
        load.assert_called_once_with(path, map_location='cpu', weights_only=True)
        self.assertTrue(torch.equal(before, torch.random.get_rng_state()))
        self.assertEqual(joint.fingerprint(restored.state_dict()), meta['tensor_sha256'])

    def test_checkpoint_and_json_never_overwrite(self):
        path = self.root / 'keep'
        path.write_bytes(b'old')
        with self.assertRaises(FileExistsError):
            run._save_state(joint.JointFlatGRU(), path)
        with self.assertRaises(FileExistsError):
            run.write_json(path, {})
        self.assertEqual(path.read_bytes(), b'old')
        invalid = self.root / 'invalid'
        with self.assertRaises(ValueError):
            run.write_json(invalid, {'bad': float('inf')})
        self.assertFalse(invalid.exists())

    def test_configuration_mismatch_is_failure_not_fallback(self):
        with patch.object(run, 'model_factories', return_value={}):
            with self.assertRaisesRegex(ValueError, 'factory inventory'):
                self.phase()
        self.failure()

    def test_changed_initialization_between_conditions_is_rejected(self):
        calls = []
        def inconsistent_factory():
            model = joint.JointFlatGRU()
            calls.append(1)
            with torch.no_grad():
                next(model.parameters()).add_(len(calls) / 10.)
            return model
        with patch.object(run, 'model_factories', return_value={'flat': inconsistent_factory}):
            with self.assertRaisesRegex(ValueError, 'initial weights differ'):
                self.phase()
        failure = self.failure()
        self.assertEqual(failure['verified_ordinals'], [0])
        self.assertEqual(failure['phase'], 'initialization')

    def test_cpu_budget_stop_with_overshoot_is_reported_not_dropped(self):
        self.spec['fit']['regimes'] = [self.spec['fit']['regimes'][1]]
        self.spec['fit']['total_neural_fits'] = 2
        def limited(model, data, **kwargs):
            result = fake_fit(model, data, **kwargs)
            result.update(completed_updates=1, stop_reason='cpu_limit', fit_cpu_seconds=1.1,
                          cpu_overshoot_seconds=1.1 - 1.)
            return result
        result = self.phase(limited)
        self.assertTrue(all(row['fit']['completed_updates'] == 1 for row in result['fits']))
        self.assertTrue(all(row['fit']['cpu_overshoot_seconds'] > 0 for row in result['fits']))
        self.assertTrue(all(row['events_processed'] == 3 for row in result['fits']))

    def test_invalid_boolean_update_metadata_is_not_accepted_as_one(self):
        def malformed(model, data, **kwargs):
            result = fake_fit(model, data, **kwargs)
            result['completed_updates'] = True
            return result
        with self.assertRaisesRegex(ValueError, 'invalid completed'):
            self.phase(malformed)
        self.failure()

    def test_final_inventory_rechecks_earlier_checkpoint_bytes(self):
        save_control = run._save_control
        def corrupt_after_fit(control, path):
            result = save_control(control, path)
            prior = self.output / 'fit-000' / 'final.pt'
            prior.write_bytes(prior.read_bytes() + b'changed after immediate verification')
            return result
        with patch.object(run, '_save_control', side_effect=corrupt_after_fit):
            with self.assertRaisesRegex(ValueError, 'checkpoint byte hash'):
                self.phase()
        failure = self.failure()
        self.assertEqual(failure['phase'], 'verification')
        self.assertEqual(failure['current_task']['ordinal'], 0)
        self.assertEqual(failure['checking_checkpoint'], 'fit-000/final.pt')
        self.assertEqual(failure['verified_ordinals'], list(range(4)))

    def test_final_restore_failure_retains_returned_metrics_and_hashes(self):
        restore = run._restore
        def broken(factory, path, meta):
            if Path(path).name == 'final.pt':
                raise ValueError('synthetic final restore failure')
            return restore(factory, path, meta)
        with patch.object(run, '_restore', side_effect=broken):
            with self.assertRaisesRegex(ValueError, 'final restore'):
                self.phase()
        failure = self.failure()
        self.assertEqual(failure['checking_checkpoint'], 'fit-000/final.pt')
        self.assertTrue((self.output / 'fit-000' / 'returned_fit.json').exists())
        self.assertTrue((self.output / 'fit-000' / 'final.json').exists())

    def test_no_public_fit_flag_in_cli(self):
        result = subprocess.run([sys.executable, '-m', run.__name__, '--fit'], capture_output=True,
                                text=True, cwd=run.ROOT)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('--preflight', result.stderr)


class PreflightTests(unittest.TestCase):
    def test_protocol_and_source_tampering_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / 'model.py').write_text('model\n')
            protocol = {'status': 'FROZEN_PUBLIC_DIAGNOSTIC_NOT_RUN', 'gate_g1': 'HOLD_REVISE',
                        'source_sha256': {'model.py': run.digest_file(source / 'model.py')}}
            path = source / run.PROTOCOL
            path.write_text(json.dumps(protocol))
            digest = run.digest_file(path)
            with patch.object(run, 'SOURCE', source), patch.object(run, 'PROTOCOL_SHA256', digest):
                self.assertEqual(run.read_protocol(), protocol)
                (source / 'model.py').write_text('changed')
                with self.assertRaisesRegex(ValueError, 'source hash'):
                    run.read_protocol()
                path.write_text('{}')
                with self.assertRaisesRegex(ValueError, 'protocol hash'):
                    run.read_protocol()

    def test_preflight_does_not_call_optimization_or_prediction(self):
        data = {'toy': batch()}
        with patch.object(run, 'read_protocol', return_value=spec()), \
             patch.object(run, 'lineage', return_value={}), patch.object(run, 'configure_runtime', return_value={}), \
             patch.object(run, 'prepare_batches', return_value=data), \
             patch.object(joint, 'fit', side_effect=AssertionError('no fits')), \
             patch.object(joint.JointFlatGRU, 'predict', side_effect=AssertionError('no scores')):
            report = run.preflight()
        self.assertEqual(report['status'], 'PREFLIGHT_ONLY_NO_FITS_OR_SCORES')
        self.assertFalse(report['study_execution_enabled'])
        self.assertEqual(report['data_sha256'], {'toy': data['toy'].digest()})

    def test_dataset_preparation_rejects_changed_shape_or_fingerprint(self):
        item = spec()
        item['data'].update(evaluation=['same_pair'], actions_per_history=3, views_per_dataset=1)
        with patch('experiments.predictive_nucleus.comparison_data.histories', return_value=()), \
             patch.object(joint, 'batch_histories', side_effect=lambda records: batch()):
            result = run.prepare_batches(item)
            self.assertEqual(len(result), 2)
            item['data']['views_per_dataset'] = 2
            with self.assertRaisesRegex(ValueError, 'dataset inventory'):
                run.prepare_batches(item)
            item['data']['views_per_dataset'] = 1
            item['data']['input_sha256']['uninformative_same_pair'] = '0' * 64
            with self.assertRaisesRegex(ValueError, 'dataset hash'):
                run.prepare_batches(item)

    def test_fresh_subprocess_runtime_configuration_and_idempotent_check(self):
        command = ('import json; from experiments.predictive_nucleus.comparison_execution '
                   'import configure_runtime; configure_runtime(); print(json.dumps(configure_runtime()))')
        result = subprocess.run([sys.executable, '-c', command], cwd=run.ROOT, check=True, capture_output=True,
                                text=True, env={**os.environ, 'PYTHONHASHSEED': '0'})
        report = json.loads(result.stdout)
        self.assertEqual((report['intraop_threads'], report['interop_threads']), (1, 1))
        self.assertTrue(report['deterministic_algorithms'])
        self.assertFalse(report['deterministic_warn_only'])

    @unittest.skipUnless((run.ROOT / '.git').exists(), 'requires complete committed checkout, not source archive')
    def test_real_frozen_preflight_in_complete_checkout(self):
        result = subprocess.run([sys.executable, '-m', run.__name__, '--preflight'], cwd=run.ROOT,
                                check=True, capture_output=True, text=True,
                                env={**os.environ, 'PYTHONHASHSEED': '0', 'OMP_NUM_THREADS': '1',
                                     'MKL_NUM_THREADS': '1'})
        report = json.loads(result.stdout)
        protocol = run.read_protocol()
        self.assertEqual(report['protocol_sha256'], run.PROTOCOL_SHA256)
        self.assertEqual(report['data_sha256'], protocol['data']['input_sha256'])
        self.assertEqual(len(report['fit_plan']), 120)
        self.assertEqual(report['status'], 'PREFLIGHT_ONLY_NO_FITS_OR_SCORES')
        self.assertFalse(report['study_execution_enabled'])
        self.assertTrue(report['lineage']['tracked_tree_clean'])

    def test_wrong_startup_environment_fails_before_thread_changes(self):
        with patch.dict(os.environ, {'PYTHONHASHSEED': '1'}), \
             patch.object(torch, 'set_num_threads', side_effect=AssertionError('must not set')):
            with self.assertRaisesRegex(ValueError, 'PYTHONHASHSEED'):
                run.configure_runtime()

    def test_synthetic_git_lineage_clean_separate_commits_and_ancestry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'experiments' / 'predictive_nucleus'
            source.mkdir(parents=True)
            def git(*args):
                return subprocess.run(['git', '-C', tmp, *args], check=True, capture_output=True,
                                      text=True).stdout.strip()
            git('init', '-q')
            git('config', 'user.name', 'Synthetic')
            git('config', 'user.email', 'synthetic@example.test')
            (source / 'model.py').write_text('model\n')
            git('add', '.')
            git('commit', '-qm', 'source')
            original = git('rev-parse', 'HEAD')
            (source / run.PROTOCOL).write_text('{}\n')
            git('add', '.')
            git('commit', '-qm', 'protocol')
            frozen = git('rev-parse', 'HEAD')
            runner = source / 'runner.py'
            runner.write_text('runner\n')
            git('add', '.')
            git('commit', '-qm', 'runner')
            item = {'source_commit': original, 'source_sha256': {'model.py': 'unused'}}
            with patch.object(run, 'ROOT', root), patch.object(run, 'SOURCE', source), \
                 patch.object(run, '__file__', str(runner)), patch.object(run, 'PROTOCOL_COMMIT', frozen):
                self.assertEqual(run.lineage(item)['runner_commit'], git('rev-parse', 'HEAD'))
                runner.write_text('dirty')
                with self.assertRaisesRegex(ValueError, 'dirty'):
                    run.lineage(item)
                git('checkout', '--', str(runner))
                with patch.object(run, 'PROTOCOL_COMMIT', git('rev-parse', 'HEAD')):
                    with self.assertRaisesRegex(ValueError, 'changed after freeze'):
                        run.lineage(item)
                git('update-index', '--assume-unchanged', str(runner))
                runner.write_text('hidden dirty change')
                with self.assertRaisesRegex(ValueError, 'uncommitted source'):
                    run.lineage(item)
                runner.write_text('runner\n')
                git('update-index', '--no-assume-unchanged', str(runner))
                git('config', 'core.sparseCheckout', 'true')
                with self.assertRaisesRegex(ValueError, 'sparse'):
                    run.lineage(item)


if __name__ == '__main__':
    unittest.main()
