"""Synthetic orchestration boundaries; no research fitting or task forecasts."""
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import effect_role_run_v2 as run
from experiments.predictive_nucleus import effect_role_scoring_v2 as scoring


class NeutralRunTests(unittest.TestCase):
    def test_control_reproduction_compares_bytes_and_every_nontiming_report_field(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); old, new = root / 'old', root / 'new'
            old.mkdir(); new.mkdir()
            report = {'final_sha256': 'state', 'curve': [{'update': 1, 'teach': .2}],
                      'settings': {'updates': 256}, 'resources': {'cpu_seconds': 1}}
            item = {'file': 'text_only-7.json'}
            item.update(run.io._write(old / item['file'], {'state': [1, 2, 3]}))
            (new / item['file']).write_bytes((old / item['file']).read_bytes())
            saved = {'reports': {'text_only/7': report}, 'checkpoints': {'text_only/7': item}}
            run.io._write(old / 'training.json', saved)
            current = deepcopy(saved); current['reports']['text_only/7']['resources']['cpu_seconds'] = 9
            with patch.object(run, 'PARENT_FIT', old):
                receipt = run.text_only_reproduction(new, {'model_seeds': [7]}, current)
                self.assertTrue(receipt['passed']); self.assertTrue(receipt['seeds']['7']['checkpoint_bytes_equal'])
                changed = deepcopy(current); changed['reports']['text_only/7']['curve'][0]['teach'] += .00001
                with self.assertRaisesRegex(ValueError, 'exactly reproduces'):
                    run.text_only_reproduction(new, {'model_seeds': [7]}, changed)
                (new / item['file']).write_text('changed')
                with self.assertRaisesRegex(ValueError, 'exactly reproduces'):
                    run.text_only_reproduction(new, {'model_seeds': [7]}, current)

    def test_fit_validation_rechecks_control_receipt_after_parent_integrity(self):
        receipt = {'passed': True}
        with patch.object(run.prior, 'validate_fit', return_value={'text_only_reproduction': receipt}) as parent, \
             patch.object(run, 'text_only_reproduction', return_value=receipt):
            self.assertEqual(run.validate_fit('d', 'f', {}, {}), {'text_only_reproduction': receipt})
            parent.assert_called_once_with('d', 'f', {}, {})
        with patch.object(run.prior, 'validate_fit', return_value={'text_only_reproduction': {}}), \
             patch.object(run, 'text_only_reproduction', return_value=receipt), self.assertRaises(ValueError):
            run.validate_fit('d', 'f', {}, {})

    def test_opened_input_is_routed_to_immutable_parent(self):
        with patch.object(run.io, '_read', side_effect=lambda path: path):
            self.assertEqual(run.observations(Path('new'), 'nor', 'fresh'), Path('new/nor-inputs.json.xz'))
            self.assertEqual(run.observations(Path('new'), 'nor', run.OPENED), run.PARENT_DATA / 'nor-inputs.json.xz')
            with self.assertRaises(ValueError): run.observations(Path('new'), 'nor', 'unknown')

    def test_collection_requires_opened_bank_before_any_evaluator_is_read(self):
        config = {'model_seeds': [7, 11, 23, 37, 53]}; frozen = {'runtime': {'synthetic': True}}
        identity = {'freeze_sha256': 'h', 'runtime': frozen['runtime'], 'training_sha256': 'h',
                    'weights_publication': 'a' * 40}
        names = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for law in run.LAWS
            for seed in config['model_seeds'] for arm in run.ARMS
            for bank in (('fresh', *run.BANKS, run.OPENED) if arm == 'grounded' else ('fresh',))}
        names.add('lexical-identities.json'); self.assertEqual(len(names), 101)
        manifest = {**identity, 'complete': True, 'oracle_opened': False,
                    'artifacts': {name: {'sha256': 'h'} for name in names}}
        opened = []
        def read(path):
            opened.append(path.name)
            return manifest if path.name == 'manifest.json' else identity
        with patch.object(run.io, '_read', side_effect=read), patch.object(run.io, '_hash', return_value='h'):
            run.validate_collection(Path('d'), Path('f'), Path('t'), config, frozen)
            del manifest['artifacts']['trace-nand-7-grounded-opened_effect_role_v1.json.xz']
            with self.assertRaisesRegex(ValueError, 'collection inventory'):
                run.validate_collection(Path('d'), Path('f'), Path('t'), config, frozen)
        self.assertEqual(set(opened), {'manifest.json', 'attempt.json'})

    def test_opened_valid_failure_produces_every_report_and_revise_decision(self):
        with tempfile.TemporaryDirectory() as directory, ExitStack() as stack:
            root = Path(directory); data, fitted, traces, output = [root / k for k in ('data', 'fit', 'traces', 'score')]
            config = {'model_seeds': [7, 11, 23, 37, 53], 'analysis': {}, 'unknown_tokens': ['x', 'y']}
            freeze = {'runtime': {'synthetic': True}}; inputs = {'episodes': []}
            identity = {'weights_publication': 'a' * 40, 'runtime': freeze['runtime'],
                        'freeze_sha256': 'h', 'training_sha256': 'h'}
            files, reports = {}, {}; real_read = run.io._read
            for law in run.LAWS:
                files[str(data / f'{law}-inputs.json.xz')] = inputs
                files[str(data / f'{law}-evaluator.json.xz')] = {}
                files[str(run.PARENT_DATA / f'{law}-inputs.json.xz')] = inputs
                files[str(run.PARENT_DATA / f'{law}-evaluator.json.xz')] = {}
                for seed in config['model_seeds']:
                    for arm in run.ARMS:
                        reports[f'{arm}/{seed}'] = {'final_sha256': 'language'}
                        for bank in (('fresh', *run.BANKS, run.OPENED) if arm == 'grounded' else ('fresh',)):
                            value = {**identity, 'law': law, 'seed': seed, 'arm': arm, 'bank': bank,
                                'input_sha256': run.c.digest(inputs), 'state_sha256': 'language', 'points': []}
                            files[str(traces / f'trace-{law}-{seed}-{arm}-{bank}.json.xz')] = value
                            if bank == 'fresh': files[str(run.PARENT_RESULT / 'traces' /
                                f'trace-{law}-{seed}-{arm}-fresh.json.xz')] = value
                    for bank, folder in run.BANKS.items():
                        files[str(root / 'data' / folder / f'{law}-inputs.json.xz')] = inputs
                        files[str(run.archive_path(law, seed, bank))] = {'input_sha256': run.c.digest(inputs), 'points': []}
            files[str(data / 'lexical-registry.json')] = {}
            files[str(traces / 'lexical-identities.json')] = {}
            for obj, name, value in ((run, 'ROOT', root),): stack.enter_context(patch.object(obj, name, value))
            stack.enter_context(patch.object(run, 'verify', return_value=(config, freeze)))
            stack.enter_context(patch.object(run, 'validate_fit', return_value={
                'reports': reports, 'text_only_reproduction': {'passed': True}}))
            stack.enter_context(patch.object(run, 'validate_collection', return_value=identity))
            stack.enter_context(patch.object(run, 'validate_lexical_controls', return_value={'identity': True}))
            stack.enter_context(patch.object(run, 'verify_runtime', return_value=freeze['runtime']))
            stack.enter_context(patch.object(run.native, 'publication', side_effect=lambda value: value))
            stack.enter_context(patch.object(run.io, '_read', side_effect=lambda path: files[str(path)]))
            stack.enter_context(patch.object(run.io, '_hash', return_value='h'))
            fresh = stack.enter_context(patch.object(scoring, 'analyze', return_value={'checks': {'fresh': True}}))
            retained = stack.enter_context(patch.object(scoring, 'retention', return_value={'checks': {'retained': True}}))
            opened = stack.enter_context(patch.object(scoring, 'analyze_opened', side_effect=[
                {'checks': {'retained': False}}] + [{'checks': {'retained': True}}] * 9))
            with redirect_stdout(io.StringIO()): run.score(data, fitted, traces, output, 'b' * 40)
            decision = real_read(output / 'decision.json'); manifest = real_read(output / 'manifest.json')
            self.assertEqual(decision['decision'], 'REVISE_EFFECT_ROLE_GROUNDING')
            self.assertTrue(decision['execution_complete']); self.assertFalse(decision['g3_complete'])
            self.assertFalse(decision['checks']['nand/7']['opened/retained'])
            self.assertEqual((fresh.call_count, retained.call_count, opened.call_count), (10, 60, 10))
            self.assertEqual(len(manifest['reports']), 10)
            self.assertEqual(set(real_read(output / 'report-nand-7.json.xz')), {'fresh', 'retention', 'opened'})


if __name__ == '__main__': unittest.main()
