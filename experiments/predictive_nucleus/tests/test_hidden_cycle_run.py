"""Synthetic frozen-artifact and collection-order checks; no trained predictions."""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import hidden_cycle_run as run


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True) + '\n')


class HiddenCycleRunTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'repo'; self.root.mkdir()
        self.data, self.fitted = self.root / 'data', self.root / 'fitted'
        self.data.mkdir(); self.fitted.mkdir()
        self.output = Path(temporary.name) / 'output'
        self.source = self.root / 'synthetic_inference.py'; self.source.write_text('unchanged = True\n')
        self.protocol = self.root / 'protocol.json'
        self.config = {'version': 'synthetic-hidden-cycle-v1', 'model_seeds': [7, 11], 'parameters': 562}
        training = {'status': 'COMPLETE', 'all_prescribed_updates_completed': True,
                    'checkpoints': {law: {} for law in run.LAWS}, 'reports': {}}
        for law in run.LAWS:
            for seed in self.config['model_seeds']:
                name = f'{law}-{seed}.json'; state = contract.digest([law, seed])
                provenance = {'parameters': 562, 'completed_updates': 128}
                write(self.fitted / name, {'state_sha256': state, 'provenance': provenance})
                training['reports'][f'{law}/{seed}'] = provenance
                training['checkpoints'][law][str(seed)] = {
                    'file': name, 'state_sha256': state, 'sha256': run.io._hash(self.fitted / name)}
            write(self.fitted / f'plan-{law}.json', {'historical_plan': law})
        write(self.fitted / 'training.json', training); write(self.fitted / 'attempt.json', {'historical': True})
        self.inventory = deepcopy(training['checkpoints'])
        subprocess.run(['git', 'init', '-q', str(self.root)], check=True)
        self.config['checkpoint_commit'] = self.commit()
        write(self.protocol, self.config)
        self.patches = ExitStack(); self.addCleanup(self.patches.close)
        for target, key, value in ((run, 'FITTED', self.fitted), (run, 'PROTOCOL', self.protocol),
                                   (run.io, 'REPO', self.root)):
            self.patches.enter_context(patch.object(target, key, value))
        self.patches.enter_context(patch.object(run, 'protocol', side_effect=lambda: deepcopy(self.config)))
        self.patches.enter_context(patch.object(run, 'sources', side_effect=self.sources))
        self.patches.enter_context(patch.object(contract, 'software_sources', side_effect=self.sources))
        artifacts = {}; banks = {}
        for law in run.LAWS:
            inputs = {'version': 'active-acceptance-input-v1', 'episodes': [{
                'episode': 'synthetic', 'ids': list('abc'),
                'observations': [dict.fromkeys('abc', 0), dict.fromkeys('abc', 0)],
                'actions': [{'kind': 'contact', 'participants': list('ab')}], 'coverage': [list('abc')]}]}
            plan = {'version': 'active-acceptance-plan-v1', 'contract_sha256': contract.contract_digest(),
                'study_id': self.config['version'] + '-' + law, 'scope': 'SYNTHETIC_INVARIANTS',
                'input_sha256': contract.digest(inputs), 'oracle_sha256': contract.digest([law, 'oracle']),
                'oracle_source_sha256': contract.digest('synthetic-oracle'),
                'information_law_sha256': contract.digest(law), 'model_seeds': self.config['model_seeds'],
                'participants': {'frozen': {seed: item['sha256'] for seed, item in self.inventory[law].items()}},
                'reference_participant': 'frozen', 'cases': [{'episode': 'synthetic', 'family': 'cycle',
                    'partition': 'held_out', 'lineage': 'synthetic-lineage', 'pair_id': None, 'direction': None}],
                'split_lineage': {'train': [], 'selection': [], 'calibration': [],
                                  'evaluation': ['synthetic-lineage']},
                'development_families': [], 'software_sha256': self.sources()}
            banks[law] = {'inputs': inputs, 'oracle': {'sentinel': 'evaluator-only'}}
            for kind, value in (('inputs', inputs), ('plan', plan)):
                name = f'{law}-{kind}.json'; artifacts[name] = run.io._write(self.data / name, value)
        artifacts['assets.json.xz'] = run.io._write(self.data / 'assets.json.xz', {'banks': banks})
        self.frozen = {'version': self.config['version'], 'sources': self.sources(),
            'protocol_sha256': run.io._hash(self.protocol), 'artifacts': artifacts,
            'checkpoint_commit': self.config['checkpoint_commit'], 'checkpoints': self.inventory,
            'training_permitted': False, 'gate_g1': 'NOT_ADMITTED'}
        self.save_freeze(); self.commit()

    def sources(self): return {'synthetic_inference.py': run.io._hash(self.source)}

    def commit(self):
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.root), '-c', 'user.name=Synthetic test',
                        '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'Synthetic fixture'], check=True)
        return subprocess.check_output(['git', '-C', str(self.root), 'rev-parse', 'HEAD'], text=True).strip()

    def save_freeze(self): write(self.data / 'freeze.json', self.frozen)

    def test_committed_fixture_verifies_without_loading_a_model(self):
        result = run.verify(self.data)
        self.assertEqual(result[2], self.inventory)
        self.assertEqual(set(result[3]), {'nand', 'nor'})

    def test_changed_source_is_rejected_before_runtime_or_forecasts(self):
        self.source.write_text('unchanged = False\n'); self.commit()
        with patch.object(run.io, '_runtime', side_effect=AssertionError('runtime must not start')):
            with self.assertRaisesRegex(ValueError, 'frozen source/protocol'):
                run.collect(self.data, self.output)
        self.assertFalse(self.output.exists())

    def test_rehashed_wrong_law_plan_still_fails_checkpoint_binding(self):
        name = 'nand-plan.json'; plan = run.io._read(self.data / name)
        plan['participants']['frozen']['7'] = self.inventory['nor']['7']['sha256']
        write(self.data / name, plan)
        self.frozen['artifacts'][name]['sha256'] = run.io._hash(self.data / name)
        self.save_freeze(); self.commit()
        with self.assertRaisesRegex(ValueError, 'plan/checkpoint binding'):
            run.verify(self.data)

    def test_coherently_rehashed_checkpoint_cannot_replace_historical_bytes(self):
        training = run.io._read(self.fitted / 'training.json')
        item = training['checkpoints']['nand']['7']; path = self.fitted / item['file']
        saved = run.io._read(path); saved['unreviewed_change'] = True; write(path, saved)
        item['sha256'] = run.io._hash(path); write(self.fitted / 'training.json', training)
        self.frozen['checkpoints'] = training['checkpoints']; self.save_freeze(); self.commit()
        with self.assertRaisesRegex(ValueError, 'historical bytes differ'):
            run.verify(self.data)

    def test_missing_seed_and_missing_prepared_artifact_are_rejected(self):
        training = run.io._read(self.fitted / 'training.json')
        del training['checkpoints']['nor']['11']; write(self.fitted / 'training.json', training); self.commit()
        with self.assertRaisesRegex(ValueError, 'seed inventory'):
            run.verify(self.data)
        del self.frozen['artifacts']['nor-plan.json']; self.save_freeze(); self.commit()
        with self.assertRaisesRegex(ValueError, 'artifact inventory'):
            run.verify(self.data)

    def test_every_trace_is_saved_before_evaluator_assets_are_parsed(self):
        reads, calls = [], []
        original_read = run.io._read
        def read(path):
            if Path(path) == self.data / 'assets.json.xz':
                self.assertEqual(len(calls), 4)
                self.assertEqual(len(list(self.output.glob('trace-*.json.xz'))), 4)
                reads.append('targets')
            return original_read(path)
        def record(inputs, **kwargs):
            self.assertFalse(reads)
            self.assertEqual(set(inputs), {'version', 'episodes'})
            calls.append(kwargs['checkpoint'].name)
            return {'resources': {'collection_cpu_seconds': 0.}, 'synthetic': True}
        with patch.object(run.io, '_read', side_effect=read), patch.object(run.io, '_runtime', return_value={}), \
                patch('experiments.predictive_nucleus.acceptance_runner.collect', side_effect=record), \
                patch('experiments.predictive_nucleus.acceptance_scoring.evaluate', return_value={}), \
                patch('experiments.predictive_nucleus.hidden_cycle_scoring.analyze', return_value={
                    'decision': {'execution_complete': True, 'decision': 'KEEP_HIDDEN_CYCLE'}}), \
                redirect_stdout(io.StringIO()):
            run.collect(self.data, self.output)
        self.assertEqual(reads, ['targets'])
        self.assertEqual(original_read(self.output / 'decision.json')['new_training_updates'], 0)

    def test_failed_collection_retains_prefix_and_existing_output_is_never_mutated(self):
        original_read = run.io._read; calls = []
        def read(path):
            self.assertNotEqual(Path(path), self.data / 'assets.json.xz', 'targets opened after incomplete collection')
            return original_read(path)
        def record(inputs, **kwargs):
            calls.append(kwargs['checkpoint'].name)
            if len(calls) == 4: raise RuntimeError('synthetic collector failure')
            return {'resources': {'collection_cpu_seconds': 0.}, 'synthetic': True}
        argv = ['hidden_cycle_run', 'collect', '--data', str(self.data), '--output', str(self.output)]
        with patch('sys.argv', argv), patch.object(run.io, '_read', side_effect=read), \
                patch.object(run.io, '_runtime', return_value={}), \
                patch('experiments.predictive_nucleus.acceptance_runner.collect', side_effect=record), \
                redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(RuntimeError, 'synthetic collector failure'): run.main()
            before = {p.name: p.read_bytes() for p in self.output.iterdir()}
            self.assertEqual(len(list(self.output.glob('trace-*.json.xz'))), 3)
            self.assertFalse(original_read(self.output / 'failure.json')['retry_permitted'])
            with self.assertRaises(FileExistsError): run.main()
            self.assertEqual(before, {p.name: p.read_bytes() for p in self.output.iterdir()})
        self.assertEqual(len(calls), 4)


if __name__ == '__main__': unittest.main()
