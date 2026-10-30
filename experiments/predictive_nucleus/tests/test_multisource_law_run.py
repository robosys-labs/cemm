"""Synthetic artifact binding only: no model construction, fitting or forecasts."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import acceptance_contract as contract
from experiments.predictive_nucleus import multisource_law_run as run
from experiments.predictive_nucleus.observed_io import load_batches


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n')


class MultisourceLawRunTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.root = Path(directory.name); self.data = self.root / 'data'; self.fitted = self.root / 'fitted'
        self.data.mkdir(); self.fitted.mkdir()
        self.config = {'version': 'synthetic-binding-v1', 'model_seeds': [7, 11], 'parameters': 562,
            'model': {'hidden': 11, 'persistence': False, 'role_tying': False, 'memory': True},
            'data': {'train': {'events': 2, 'visible_bits': 6}}, 'fit': {'updates': 3, 'cpu_seconds': 2,
                'learning_rate': .02, 'batch_size': 1, 'live_path_limit': 64, 'candidate_expansions': 512}}
        self.frozen = {'sources': {'active_learning.py': 'a' * 64}, 'artifacts': {},
            'evaluation_oracles': {law: {k: contract.digest([law, k]) for k in
                ('oracle_sha256', 'oracle_source_sha256', 'information_law_sha256')} for law in run.LAWS}}
        self.inputs, histories = {}, {}
        for law in run.LAWS:
            self.inputs[law] = {'version': 'active-acceptance-input-v1', 'episodes': [{'episode': 'synthetic',
                'ids': list('abc'), 'actions': [{'kind': 'contact', 'participants': list(pair)} for pair in ('ab', 'bc')],
                'coverage': [list('abc'), list('abc')], 'observations': [dict(zip('abc', state))
                    for state in ((0, 0, 0), (0, 1, 0), (0, 1, int(law == 'nand')))]}]}
            name = f'{law}-train-inputs.json'; write(self.data / name, self.inputs[law])
            self.frozen['artifacts'][name] = {'sha256': run.io._hash(self.data / name)}
            histories[law] = [b.digest() for b in load_batches(self.data / name,
                self.frozen['artifacts'][name]['sha256'], batch_size=1)]
        write(self.data / 'prefit.json', self.frozen)
        attempt = {'stage': 'fit', 'prefit_sha256': run.io._hash(self.data / 'prefit.json')}
        write(self.fitted / 'attempt.json', attempt)
        self.training = {'version': self.config['version'], 'prefit_sha256': attempt['prefit_sha256'],
            'attempt_sha256': run.io._hash(self.fitted / 'attempt.json'), 'reports': {},
            'checkpoints': {law: {} for law in (*run.LAWS, 'initial')},
            'all_prescribed_updates_completed': True, 'status': 'COMPLETE'}
        predictor = {'kind': 'kernel', 'configuration': self.config['model']}
        for seed in self.config['model_seeds']:
            initial = contract.digest(['synthetic-initial', seed])
            for law in ('initial', *run.LAWS):
                state = initial if law == 'initial' else contract.digest(['synthetic-final', law, seed])
                report = {'objective': 'untrained_or_inherited', 'completed_updates': 0, 'training_input_sha256': None}
                if law != 'initial':
                    report = {'training_input_sha256': contract.digest(histories[law]), 'history_sha256': histories[law],
                        'training_source_sha256': 'a' * 64, 'initial_weights_sha256': initial, 'final_weights_sha256': state,
                        'objective': 'observed_joint_nll', 'status': 'COMPLETED', 'stop_reason': 'update_limit',
                        'requested_updates': 3, 'completed_updates': 3, 'parameters': 562, 'observed_events_per_update': 2,
                        'action_events_per_update': 2, 'visible_bits_per_update': 6, 'learning_rate': .02,
                        'cpu_ceiling_seconds': 2, 'live_path_limit': 64, 'candidate_expansion_limit': 512, 'predictor': predictor}
                    self.training['reports'][f'{law}/{seed}'] = report
                    write(self.fitted / f'fit-{law}-{seed}.json', report)
                name = f'{law}-{seed}.json'
                write(self.fitted / name, {'state_sha256': state, 'predictor': predictor, 'provenance': report})
                self.training['checkpoints'][law][str(seed)] = {'file': name, 'state_sha256': state,
                    'sha256': run.io._hash(self.fitted / name)}
        self.save()

    def save(self): write(self.fitted / 'training.json', self.training)

    def validate(self): return run._training(self.data, self.fitted, self.config, self.frozen)

    def rewrite_report(self, law, seed, report):
        self.training['reports'][f'{law}/{seed}'] = report
        write(self.fitted / f'fit-{law}-{seed}.json', report)
        item = self.training['checkpoints'][law][str(seed)]
        saved = run.io._read(self.fitted / item['file']); saved['provenance'] = report
        write(self.fitted / item['file'], saved); item['sha256'] = run.io._hash(self.fitted / item['file']); self.save()

    def test_valid_bindings_and_matched_crossed_maps(self):
        self.assertEqual(self.validate(), self.training)
        for law, other in (('nand', 'nor'), ('nor', 'nand')):
            result = run._participants(self.training, law, self.config['model_seeds'])
            for seed in ('7', '11'):
                self.assertEqual(result['matched'][seed], self.training['checkpoints'][law][seed]['sha256'])
                self.assertEqual(result['crossed'][seed], self.training['checkpoints'][other][seed]['sha256'])

    def test_stale_prefit_rejected(self):
        write(self.data / 'prefit.json', {**self.frozen, 'different_bank': True})
        with self.assertRaisesRegex(ValueError, 'different prefit'): self.validate()

    def test_wrong_law_tape_rejected_even_when_all_report_copies_agree(self):
        report = deepcopy(self.training['reports']['nand/7'])
        for key in ('training_input_sha256', 'history_sha256'): report[key] = self.training['reports']['nor/7'][key]
        self.rewrite_report('nand', 7, report)
        with self.assertRaisesRegex(ValueError, 'provenance differs'): self.validate()

    def test_incomplete_updates_rejected_despite_complete_boolean(self):
        report = deepcopy(self.training['reports']['nand/7']); report['completed_updates'] = 2
        self.rewrite_report('nand', 7, report)
        with self.assertRaisesRegex(ValueError, 'exposure'): self.validate()

    def test_missing_seed_inventory_rejected(self):
        del self.training['reports']['nor/11']; self.save()
        with self.assertRaisesRegex(ValueError, 'incomplete fitted inventory'): self.validate()

    def test_checkpoint_provenance_swap_rejected_after_rehashing(self):
        item = self.training['checkpoints']['nand']['7']; saved = run.io._read(self.fitted / item['file'])
        saved['provenance'] = self.training['reports']['nor/7']; write(self.fitted / item['file'], saved)
        item['sha256'] = run.io._hash(self.fitted / item['file']); self.save()
        with self.assertRaisesRegex(ValueError, 'provenance differs'): self.validate()

    def test_swapped_collection_arms_rejected_before_runtime_or_forecasts(self):
        for law in run.LAWS:
            write(self.data / f'{law}-evaluation-inputs.json', self.inputs[law])
            participants = run._participants(self.training, law, self.config['model_seeds'])
            if law == 'nand': participants['matched'], participants['crossed'] = participants['crossed'], participants['matched']
            plan = {'version': 'active-acceptance-plan-v1', 'contract_sha256': contract.contract_digest(),
                'study_id': self.config['version'] + '-' + law, 'scope': 'SYNTHETIC_INVARIANTS',
                'input_sha256': contract.digest(self.inputs[law]), **self.frozen['evaluation_oracles'][law],
                'model_seeds': self.config['model_seeds'], 'participants': participants, 'reference_participant': 'crossed',
                'cases': [{'episode': 'synthetic', 'family': 'query', 'partition': 'held_out', 'lineage': 'synthetic-lineage',
                           'pair_id': None, 'direction': None}], 'split_lineage': {'train': [], 'selection': [],
                           'calibration': [], 'evaluation': ['synthetic-lineage']},
                'development_families': [], 'software_sha256': contract.software_sources()}
            write(self.fitted / f'plan-{law}.json', plan)
        with patch.object(run, 'verify', return_value=(self.config, self.frozen)), patch.object(run.io, '_committed'), \
                patch.object(run.io, '_runtime', side_effect=AssertionError('runtime must not start')), \
                patch('experiments.predictive_nucleus.acceptance_runner.collect', side_effect=AssertionError('no forecasts')):
            with self.assertRaisesRegex(ValueError, 'collection plan binding differs'):
                run.collect(self.data, self.fitted, self.root / 'unused-output')


if __name__ == '__main__': unittest.main()
