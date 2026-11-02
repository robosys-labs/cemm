"""Synthetic publication/reporting pipeline; no research bank, fit or model run."""
from contextlib import contextmanager, ExitStack, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from experiments.predictive_nucleus import set_acquisition_run_v2 as run
from experiments.predictive_nucleus import set_acquisition_runtime_v2 as numerical
from experiments.predictive_nucleus import set_acquisition_scoring as native
from experiments.predictive_nucleus.tests.test_set_acquisition_retention_v2 import fixture, LIMITS


@contextmanager
def score_fixture(fail_first=False):
    """Actual temporary serialization, mocked native scorer and frozen identities."""
    with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
        root = Path(directory); data, fitted, traces = (root / n for n in ('data', 'fit', 'traces'))
        for path in (data, fitted, traces, root / 'archive'): path.mkdir()
        write, read = run.io._write, run.io._read
        write(data / 'freeze.json', {'synthetic': True}); write(fitted / 'training.json', {'synthetic': True})
        config = {'model_seeds': [7, 11, 23, 37, 53],
                  'analysis': {**LIMITS, 'max_set_mean_nll': .05}}
        frozen_runtime = {'synthetic': 'runtime'}; freeze = {'runtime': frozen_runtime}
        identity = {'weights_publication': 'a' * 40, 'runtime': frozen_runtime,
            'freeze_sha256': run.io._hash(data / 'freeze.json'),
            'training_sha256': run.io._hash(fitted / 'training.json')}
        accepted = {'checkpoints': {f'coordinates/{s}': {'state_sha256': f'language-{s}'}
                                   for s in config['model_seeds']}}
        language = root / 'language.json'; write(language, accepted)
        artifacts = {}; reports = {}; observed, old = fixture()
        archive_path = lambda law, seed, bank: root / 'archive' / f'{law}-{seed}-{bank}.json.xz'
        first_bank = next(iter(run.BANKS))
        for law in run.LAWS:
            inputs = {'synthetic': law}; write(data / f'{law}-inputs.json.xz', inputs)
            write(data / f'{law}-evaluator.json.xz', {'synthetic_evaluator': law})
            for bank, folder in run.BANKS.items():
                path = root / 'data' / folder; path.mkdir(exist_ok=True)
                write(path / f'{law}-inputs.json.xz', observed)
            for seed in config['model_seeds']:
                reports[f'{law}/{seed}'] = {'final_observed_train_nll': .01}
                for arm in run.ARMS:
                    name = f'trace-{law}-{seed}-{arm}-fresh.json.xz'
                    artifacts[name] = write(traces / name, {**identity, 'law': law, 'seed': seed,
                        'arm': arm, 'bank': 'fresh', 'input_sha256': run.c.digest(inputs), 'points': []})
                for bank in run.BANKS:
                    rows = deepcopy(old)
                    if fail_first and (law, seed, bank) == (run.LAWS[0], config['model_seeds'][0], first_bank):
                        rows[0]['order_logp'].reverse()
                    name = f'trace-{law}-{seed}-acquired-{bank}.json.xz'
                    artifacts[name] = write(traces / name, {**identity, 'law': law, 'seed': seed,
                        'arm': 'acquired', 'bank': bank, 'input_sha256': run.c.digest(observed),
                        'language_sha256': accepted['checkpoints'][f'coordinates/{seed}']['state_sha256'], 'points': rows})
                    write(archive_path(law, seed, bank), {'input_sha256': run.c.digest(observed), 'points': old})
        write(traces / 'attempt.json', identity)
        write(traces / 'manifest.json', {**identity, 'complete': True, 'oracle_opened': False, 'artifacts': artifacts})
        for obj, name, value in ((run, 'ROOT', root), (run, 'LANGUAGE', language)):
            stack.enter_context(patch.object(obj, name, value))
        stack.enter_context(patch.object(run.v1, 'archive_path', side_effect=archive_path))
        stack.enter_context(patch.object(run, 'verify', return_value=(config, freeze)))
        stack.enter_context(patch.object(run, 'validate_fit', return_value={'reports': reports}))
        stack.enter_context(patch.object(run, 'verify_runtime', return_value=frozen_runtime))
        stack.enter_context(patch.object(run, 'publication', side_effect=lambda value: value))
        scorer = stack.enter_context(patch.object(native, 'analyze_native', return_value={
            'passed': True, 'checks': {'native_criterion': True}, 'synthetic': True}))
        yield SimpleNamespace(root=root, data=data, fitted=fitted, traces=traces, output=root / 'scores',
            config=config, freeze=freeze, reports=reports, scorer=scorer, first_bank=first_bank, read=read)


def replace(path, value):
    path.unlink(); return run.io._write(path, value)


class SetAcquisitionRunV2Tests(unittest.TestCase):
    def execute(self, case):
        with redirect_stdout(io.StringIO()):
            run.score(case.data, case.fitted, case.traces, case.output, 'b' * 40)

    def test_first_retention_failure_keeps_all_laws_seeds_banks_and_completed_decision(self):
        with score_fixture(fail_first=True) as case:
            self.execute(case)
            decision = case.read(case.output / 'decision.json')
            manifest = case.read(case.output / 'manifest.json')
            expected = {f'{law}/{seed}' for law in run.LAWS for seed in case.config['model_seeds']}
            self.assertEqual(decision['decision'], 'REVISE_NATIVE_SET_ACQUISITION')
            self.assertTrue(decision['execution_complete']); self.assertEqual(set(manifest['reports']), expected)
            self.assertEqual(set(decision['checks']), expected); self.assertEqual(case.scorer.call_count, 10)
            failed_checks = []
            for key in sorted(expected):
                law, seed = key.split('/'); report = case.read(case.output / f'report-{law}-{seed}.json.xz')
                self.assertTrue(report['native']['passed']); self.assertEqual(set(report['retention']), set(run.BANKS))
                self.assertTrue(all(r['planned'] == len(r['points']) == 1 for r in report['retention'].values()))
                failed_checks.extend((key, check) for check, passed in decision['checks'][key].items() if not passed)
            self.assertEqual(failed_checks, [('nand/7', case.first_bank + '/order_logp_retained'),
                                             ('nand/7', case.first_bank + '/order_map_retained')])
            self.assertFalse(decision['scientific_admission']); self.assertFalse(decision['g3_complete'])
            self.assertFalse((case.output / 'failure.json').exists())

    def test_valid_completed_pipeline_passes_without_inventing_scientific_admission(self):
        with score_fixture() as case:
            self.execute(case); decision = case.read(case.output / 'decision.json')
            self.assertEqual(decision['decision'], 'KEEP_NATIVE_SET_ACQUISITION')
            self.assertTrue(all(all(row.values()) for row in decision['checks'].values()))
            self.assertFalse(decision['scientific_admission']); self.assertFalse(decision['g3_complete'])

    def test_collection_runtime_or_missing_inventory_aborts_before_opening_evaluator(self):
        with score_fixture() as case:
            path = case.traces / 'manifest.json'; original = case.read(path)
            for field, value in (('runtime', {'synthetic': 'different'}), ('artifacts', {}), ('complete', False)):
                with self.subTest(field=field):
                    replace(path, {**original, field: value}); opened = []
                    def read(target):
                        opened.append(target.name); return case.read(target)
                    with patch.object(run.io, '_read', side_effect=read), self.assertRaises(ValueError):
                        self.execute(case)
                    self.assertFalse(any('evaluator' in name for name in opened))
                    self.assertFalse(case.output.exists()); case.scorer.assert_not_called()

    def test_trace_byte_drift_is_an_integrity_failure_before_evaluator_access(self):
        with score_fixture() as case:
            path = case.traces / 'trace-nand-7-parent-fresh.json.xz'
            replace(path, {**case.read(path), 'points': ['changed']}); opened = []
            def read(target):
                opened.append(target.name); return case.read(target)
            with patch.object(run.io, '_read', side_effect=read), self.assertRaisesRegex(ValueError, 'trace bytes differ'):
                self.execute(case)
            self.assertFalse(any('evaluator' in name for name in opened)); self.assertFalse(case.output.exists())

    def test_rehashed_trace_runtime_or_malformed_rows_cannot_receive_acceptance(self):
        with score_fixture() as case:
            name = f'trace-nand-7-acquired-{case.first_bank}.json.xz'
            path, manifest_path = case.traces / name, case.traces / 'manifest.json'
            original, manifest = case.read(path), case.read(manifest_path)
            for field, value, message in (('runtime', {'synthetic': 'different'}, 'trace identity/runtime'),
                                          ('points', [], 'missing retention rows')):
                with self.subTest(field=field):
                    item = replace(path, {**original, field: value})
                    updated = deepcopy(manifest); updated['artifacts'][name] = item
                    replace(manifest_path, updated)
                    case.output = case.root / ('scores-' + field)
                    with self.assertRaisesRegex(ValueError, message): self.execute(case)
                    self.assertFalse((case.output / 'decision.json').exists())
                    self.assertFalse((case.output / 'manifest.json').exists())

    def test_frozen_source_and_runtime_digest_drift_fail_before_execution(self):
        config = {'version': 'synthetic'}
        frozen = {'version': 'synthetic', 'base_commit': run.BASE, 'sources': {'source': 'bound'},
            'protocol_sha256': 'h', 'historical': {}, 'artifacts': {}, 'runtime': {'identity': 'bound'}}
        frozen['runtime_sha256'] = run.c.digest(frozen['runtime'])
        values = {'freeze.json': frozen, run.COMMITMENT.name: {'freeze.json': 'h'}}
        with patch.object(run, 'protocol', return_value=config), patch.object(run, 'sources', return_value={'source': 'bound'}), \
             patch.object(run.io, '_read', side_effect=lambda path: values[path.name]), \
             patch.object(run.io, '_hash', return_value='h'):
            self.assertEqual(run.verify(Path('synthetic'))[1], frozen)
            for field, value in (('sources', {'source': 'changed'}), ('runtime_sha256', 'wrong'),
                                 ('base_commit', 'wrong'), ('protocol_sha256', 'wrong')):
                with self.subTest(field=field):
                    values['freeze.json'] = {**frozen, field: value}
                    with self.assertRaisesRegex(ValueError, 'frozen source/runtime'):
                        run.verify(Path('synthetic'))

    def test_fit_runtime_and_recipe_remain_exact_after_base_validation(self):
        frozen = {'runtime': {'identity': 'bound'}}
        config = {'fit': {'updates': 256, 'learning_rate': .02, 'gradient_clip': 1.,
                         'cpu_seconds': 180, 'live_path_limit': 64, 'candidate_expansions': 512}}
        report = {'status': 'COMPLETED', 'version': 'set-acquisition-fit-v1',
            'all_prescribed_updates_completed': True, 'requested_updates': 256,
            'learning_rate': .02, 'gradient_clip': 1., 'cpu_ceiling_seconds': 180.,
            'live_path_limit': 64, 'candidate_expansion_limit': 512, 'optimizer': 'Adam',
            'optimizer_defaults': {'betas': [.9, .999], 'eps': 1e-8, 'weight_decay': 0., 'amsgrad': False},
            'fresh_optimizer': True, 'mask_before_clipping': True, 'training_source_sha256': 'synthetic-fit-source'}
        saved = {'runtime': frozen['runtime'], 'reports': {'nand/7': report}}
        with patch.object(run.v1, 'validate_fit', return_value=saved), \
             patch.object(run.io, '_hash', return_value='synthetic-fit-source'):
            self.assertEqual(run.validate_fit(Path('data'), Path('fit'), config, frozen), saved)
            saved['runtime'] = {'identity': 'different'}
            with self.assertRaisesRegex(ValueError, 'fitted runtime/recipe'):
                run.validate_fit(Path('data'), Path('fit'), config, frozen)
            saved['runtime'] = frozen['runtime']
            changed = [('status', 'INTERRUPTED'), ('version', 'different'), ('requested_updates', 257),
                ('all_prescribed_updates_completed', False), ('learning_rate', .03), ('gradient_clip', 2.),
                ('cpu_ceiling_seconds', 181.), ('live_path_limit', 65), ('candidate_expansion_limit', 513),
                ('optimizer', 'SGD'), ('fresh_optimizer', False), ('mask_before_clipping', False),
                ('training_source_sha256', 'different'),
                ('optimizer_defaults', {**report['optimizer_defaults'], 'weight_decay': .1})]
            for field, value in changed:
                saved['reports']['nand/7'] = {**report, field: value}
                with self.subTest(field=field), self.assertRaisesRegex(ValueError, 'fitted runtime/recipe'):
                    run.validate_fit(Path('data'), Path('fit'), config, frozen)

    def test_publication_requires_current_commit_and_clean_checkout(self):
        sha = 'a' * 40
        def git(*args):
            self.assertIn(args, (('rev-parse', 'HEAD'), ('status', '--porcelain')))
            return sha if args[0] == 'rev-parse' else ''
        with patch.object(run.io, '_git', side_effect=git):
            self.assertEqual(run.publication(sha), sha)
            with self.assertRaisesRegex(ValueError, 'current published commit'): run.publication('b' * 40)
        with patch.object(run.io, '_git', side_effect=[sha, ' M synthetic.py']):
            with self.assertRaisesRegex(ValueError, 'clean published checkout'): run.publication(sha)

    def test_runtime_freeze_compares_complete_receipt(self):
        frozen = {'python': 'synthetic', 'cpu_capability': 'synthetic', 'interop_threads': 1}
        with patch.object(numerical, 'runtime', return_value=frozen):
            self.assertEqual(numerical.verify_runtime({}, frozen), frozen)
        for field, value in (('cpu_capability', 'different'), ('interop_threads', 2)):
            with self.subTest(field=field), patch.object(numerical, 'runtime', return_value={**frozen, field: value}), \
                 self.assertRaisesRegex(ValueError, 'execution identity differs'):
                numerical.verify_runtime({}, frozen)

    def test_runtime_basic_config_and_allowlisted_evidence_without_tensor_execution(self):
        torch = SimpleNamespace(__version__='synthetic-torch', set_num_threads=Mock(),
            get_num_threads=lambda: 1, get_num_interop_threads=lambda: 1, set_num_interop_threads=Mock(),
            use_deterministic_algorithms=Mock(), are_deterministic_algorithms_enabled=lambda: True,
            backends=SimpleNamespace(cpu=SimpleNamespace(get_cpu_capability=lambda: 'synthetic-capability')),
            __config__=SimpleNamespace(show=lambda: 'synthetic-build', parallel_info=lambda: 'synthetic-parallel'))
        config = {'execution': {'runtime': {'python': 'synthetic-python', 'torch': 'synthetic-torch',
            'numpy': 'synthetic-numpy', 'threads': 1, 'dtype': 'float64', 'deterministic_algorithms': True}}}
        cpu = Mock(); cpu.is_file.return_value = True
        cpu.read_text.return_value = 'vendor_id: synthetic\nmodel name: synthetic CPU\nserial: excluded\n\nvendor_id: second'
        with patch.dict('sys.modules', {'torch': torch, 'numpy': SimpleNamespace(__version__='synthetic-numpy')}), \
             patch.object(numerical.platform, 'python_version', return_value='synthetic-python'), \
             patch.object(numerical, 'Path', return_value=cpu), \
             patch.dict(numerical.os.environ, {'ATEN_CPU_CAPABILITY': 'synthetic', 'SECRET': 'must-not-appear'}, clear=True):
            receipt = numerical.runtime(config)
            self.assertEqual(receipt['cpu'], {'vendor_id': 'synthetic', 'model name': 'synthetic CPU'})
            self.assertEqual(set(receipt['environment']), set(numerical.ENVIRONMENT))
            self.assertNotIn('must-not-appear', json.dumps(receipt))
            self.assertEqual(receipt['environment']['ATEN_CPU_CAPABILITY'], 'synthetic')
            torch.set_num_threads.assert_called_with(1); torch.use_deterministic_algorithms.assert_called_with(True)
            config['execution']['runtime']['torch'] = 'different'
            with self.assertRaisesRegex(ValueError, 'frozen numerical runtime differs'):
                numerical.runtime(config)


if __name__ == '__main__': unittest.main()
