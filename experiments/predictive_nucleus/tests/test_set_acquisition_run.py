"""Synthetic runner boundaries; no research checkpoint, tape, fit or score."""
from copy import deepcopy
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import set_acquisition_run as run


def language_fixture():
    inputs = {'version': 'bilingual-input-v1', 'episodes': [{'id': 'synthetic',
        'entities': ['a', 'b', 'c'], 'anchor': [0, 0, 0],
        'context': [{'action': [1, 0, -1, 0], 'reading': [0, 0, 0]}],
        'utterances': [{'text': 'a touches b', 'reading': [0, 0, 0]}]}]}
    point = {'id': 'synthetic', 'step': 0, 'view': 'canonical',
        'logp': [math.log(.65)] + [math.log(.05)] * 7, 'order_logp': [math.log(.8), math.log(.2)]}
    return inputs, point


class SetAcquisitionRunTests(unittest.TestCase):
    def test_native_points_use_only_past_feedback(self):
        a = {'a': 0, 'b': 0, 'c': 0}; b = {**a, 'a': 1}; d = {**b, 'b': 1}
        inputs = {'version': 'active-acceptance-input-v1', 'episodes': [{'episode': 'synthetic',
            'ids': list(a), 'observations': [a, b, d], 'coverage': [list(a), list(a)],
            'actions': [{'kind': 'set', 'participants': ['a'], 'value': 1},
                        {'kind': 'set', 'participants': ['b'], 'value': 1}]}]}
        before = deepcopy(inputs); rows = run.native_points(inputs)
        altered = deepcopy(inputs); altered['episodes'][0]['observations'][1] = d
        changed = run.native_points(altered)
        self.assertEqual(rows[0], changed[0]); self.assertNotEqual(rows[1], changed[1])
        altered = deepcopy(inputs); altered['episodes'][0]['observations'][2] = a
        self.assertEqual(rows, run.native_points(altered)); self.assertEqual(inputs, before)
        self.assertEqual(rows[0]['logp'][0], 0.); self.assertEqual(rows[1]['logp'][4], 0.)
        self.assertEqual(rows[0]['logp'].count('negative_infinity'), 7)

    def test_retention_reports_probability_loss_and_exact_regression(self):
        inputs, old = language_fixture(); same = run.retention(inputs, [old], [old], 1e-10)
        self.assertTrue(same['passed']); self.assertEqual(same['max_logp_change'], 0.)
        worse = deepcopy(old); worse['logp'] = [math.log(.58), math.log(.12)] + [math.log(.05)] * 6
        report = run.retention(inputs, [worse], [old], .2)
        self.assertEqual(report['correct'], 1); self.assertEqual(report['regressions'], [])
        self.assertEqual(report['nll_worse'], 1); self.assertGreater(report['mean_nll_change'], 0.)
        broken = deepcopy(old); broken['logp'][0], broken['logp'][1] = broken['logp'][1], broken['logp'][0]
        report = run.retention(inputs, [broken], [old], 10.)
        self.assertFalse(report['passed']); self.assertEqual(report['regressions'], [['synthetic', 0]])

    def test_retention_rejects_missing_duplicate_extra_or_malformed_canonical_points(self):
        inputs, old = language_fixture()
        for rows in ([], [old, old], [dict(old, id='foreign')], [dict(old, step=True)],
                     [dict(old, order_logp=[math.log(.2), math.log(.8)])], [dict(old, logp=[0.] * 8)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError): run.retention(inputs, rows, [old], 1e-10)

    def test_only_archive_may_include_noncanonical_views_and_inputs_cannot_duplicate(self):
        inputs, old = language_fixture(); masked = dict(old, view='masked')
        self.assertTrue(run.retention(inputs, [old], [old, masked], 1e-10)['passed'])
        with self.assertRaises(ValueError): run.retention(inputs, [old, masked], [old], 1e-10)
        duplicated = deepcopy(inputs); duplicated['episodes'].append(deepcopy(inputs['episodes'][0]))
        with self.assertRaises(ValueError): run.retention(duplicated, [old], [old], 1e-10)

    def test_verify_rejects_source_or_commitment_inventory_drift(self):
        freeze = {'version': 'synthetic', 'base_commit': run.BASE, 'sources': {'x': 'bound'},
                  'protocol_sha256': 'h', 'historical': {}, 'artifacts': {}}
        values = {'freeze.json': freeze, 'set_acquisition_freeze_v1.json': {'freeze.json': 'h'}}
        with patch.object(run, 'protocol', return_value={'version': 'synthetic'}), \
             patch.object(run, 'sources', return_value={'x': 'bound'}), \
             patch.object(run.io, '_read', side_effect=lambda p: values[p.name]), \
             patch.object(run.io, '_hash', return_value='h'):
            self.assertEqual(run.verify(Path('synthetic'))[1], freeze)
            freeze['sources'] = {'x': 'changed'}
            with self.assertRaises(ValueError): run.verify(Path('synthetic'))
            freeze['sources'] = {'x': 'bound'}; values['set_acquisition_freeze_v1.json']['extra'] = 'h'
            with self.assertRaises(ValueError): run.verify(Path('synthetic'))

    def test_serialized_mask_allows_intervention_but_rejects_rehashed_contact_change(self):
        import torch
        from experiments.predictive_nucleus.active_checkpoint import _tensors, predictor_spec
        from experiments.predictive_nucleus.domain_kernel import DomainKernel
        from experiments.predictive_nucleus.joint_objective import fingerprint
        with torch.random.fork_rng(devices=[]): model = DomainKernel(hidden=11, role_tying=False)
        def snapshot():
            return {'state': _tensors(model), 'state_sha256': fingerprint(model.state_dict()),
                    'predictor': predictor_spec(model=model)}
        immutable = {k: (v[:, [0, 1, 3]] if k == 'background.0.weight' else v).flatten()
                     for k, v in model.state_dict().items() if not k.startswith('intervention.')}
        parent = snapshot(); digest = fingerprint(immutable)
        with torch.no_grad(): model.intervention[0].weight[0, 0] += .125
        acquired = snapshot()
        report = {'parameters': 562, 'permitted_scalars': 68, 'immutable_scalars': 494,
            'changed_permitted_scalars': 1, 'changed_forbidden_scalars': 0,
            'initial_weights_sha256': parent['state_sha256'], 'final_weights_sha256': acquired['state_sha256'],
            'immutable_before_sha256': digest, 'immutable_after_sha256': digest}
        run.verify_mask(parent, acquired, report)
        with torch.no_grad(): model.pair[0].weight[0, 0] += .125
        tampered = snapshot(); report['final_weights_sha256'] = tampered['state_sha256']
        with self.assertRaises(ValueError): run.verify_mask(parent, tampered, report)

    def test_fitted_inventory_and_training_tape_bindings_fail_before_checkpoint_reads(self):
        config = {'version': 'synthetic', 'model_seeds': [7], 'fit': {'updates': 1}, 'train_forecasts': 1}
        inputs = {'synthetic': True}; keys = {'nand/7': {}, 'nor/7': {}}
        saved = {'complete': True, 'version': 'synthetic', 'freeze_sha256': 'h',
                 'training_input_sha256': run.c.digest(inputs), 'reports': keys, 'checkpoints': keys}
        for field, value in (('complete', False), ('freeze_sha256', 'wrong'),
                             ('training_input_sha256', 'wrong'), ('reports', {}), ('checkpoints', {})):
            invalid = {**saved, field: value}
            with self.subTest(field=field), patch.object(run.io, '_hash', return_value='h'), \
                 patch.object(run.io, '_read', side_effect=lambda p: invalid if p.name == 'training.json' else inputs), \
                 self.assertRaisesRegex(ValueError, 'fitted inventory/binding'):
                run.validate_fit(Path('data'), Path('fit'), config, {})

    def test_invalid_trace_manifest_stops_before_opening_evaluator(self):
        config = {'model_seeds': [7]}
        names = {f'trace-{law}-7-{arm}-{bank}.json.xz': {'sha256': 'h'} for law in run.LAWS
            for arm, bank in [*((arm, 'fresh') for arm in run.ARMS), *(('acquired', bank) for bank in run.BANKS)]}
        manifest = {'complete': True, 'oracle_opened': False, 'freeze_sha256': 'h',
                    'training_sha256': 'h', 'artifacts': names}
        for field, value in (('complete', False), ('oracle_opened', True), ('freeze_sha256', 'wrong'),
                             ('training_sha256', 'wrong'), ('artifacts', {})):
            def read(path):
                self.assertEqual(path.name, 'manifest.json', 'evaluator opened before trace validation')
                return {**manifest, field: value}
            with self.subTest(field=field), patch.object(run, 'verify', return_value=(config, {})), \
                 patch.object(run, 'validate_fit', return_value={}), patch.object(run.io, '_read', side_effect=read), \
                 patch.object(run.io, '_hash', return_value='h'), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaisesRegex(ValueError, 'collection inventory/binding'):
                    run.score(Path('data'), Path('fit'), Path('traces'), Path(tmp) / 'scores')


if __name__ == '__main__': unittest.main()
