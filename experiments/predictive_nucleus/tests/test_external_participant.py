"""Transport/extraction invariants on synthetic histories; no challenge or fits."""
from collections import Counter
from contextlib import ExitStack
from copy import deepcopy
from hashlib import sha256
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import torch
from experiments.predictive_nucleus import external_participant as api
from experiments.predictive_nucleus import export_participant as export
from experiments.predictive_nucleus import joint_objective as joint
from experiments.predictive_nucleus import masked_replay as paths
from experiments.predictive_nucleus import comparison_scoring as scores
from experiments.predictive_nucleus.empirical_joint import SensorMemory
from experiments.predictive_nucleus.informative_curriculum import model_factories


def start():
    return {'op': 'start', 'episode': 'toy', 'ids': ['c', 'a', 'b'],
            'observation': {'a': 0, 'b': 1, 'c': 0}}


def predict(step=0, kind='observe', members=None, **extra):
    action = {'kind': kind, 'participants': members or []}
    action.update(extra)
    return {'op': 'predict', 'episode': 'toy', 'step': step, 'action': action}


def feedback(receipt, step=0, values=(0, 1, 0)):
    return {'op': 'feedback', 'episode': 'toy', 'step': step, 'receipt': receipt,
            'observation': dict(zip('abc', values, strict=True))}


def session(model=None, memory=None, control='no_change'):
    return api.Session(paths, scores, joint, model=model, memory=memory, control=control)


def synthetic_evidence(root):
    """Thirty INITIAL random states, NOT trained checkpoints or scientific evidence."""
    fits, controls = [], []
    (root / 'fits').mkdir(parents=True)
    with torch.random.fork_rng(devices=[]):
        for name, factory in model_factories().items():
            for seed in export.SEEDS:
                torch.manual_seed(seed)
                model = factory()
                ordinal = len(fits)
                folder = root / 'fits' / f'fit-{ordinal:03d}'
                folder.mkdir()
                tensors = {k: v.detach().clone() for k, v in model.state_dict().items()}
                torch.save(tensors, folder / 'final.pt')
                fits.append({'task': {'ordinal': ordinal, 'regime': 'fixed_exposure', 'condition': 'informative',
                                      'model': name, 'seed': seed},
                             'final': {'file': 'final.pt', 'file_sha256': export.digest(folder / 'final.pt'),
                                       'tensor_sha256': joint.fingerprint(tensors)},
                             'fit': {'SYNTHETIC_UNTRAINED_UNIT_TEST': True}})
    for mode in ('prefix', 'local', 'contact'):
        memory = SensorMemory(mode)
        from experiments.predictive_nucleus.empirical_joint import context
        key, _ = context((0, 1, 0), (2, -1, -1, -1), (), mode)
        memory.table[key] = Counter({(0, 1, 0): 1})
        file = 'informative-' + mode + '.json'
        payload = {'mode': mode, 'table_sha256': memory.digest(),
                   'rows': [[k, sorted(v.items())] for k, v in sorted(memory.table.items())]}
        (root / 'fits' / file).write_text(json.dumps(payload))
        controls.append({'condition': 'informative', 'mode': mode, 'file': file,
                         'file_sha256': export.digest(root / 'fits' / file), 'table_sha256': memory.digest()})
    fit_report = {'fits': fits, 'controls': controls}
    (root / 'fits' / 'FIT_PHASE.json').write_text(json.dumps(fit_report))
    (root / 'report.json').write_text(json.dumps({'fits': fit_report}))
    digest = export.digest(root / 'report.json')
    (root / 'COMPLETE').write_text(digest)
    return digest


class ParticipantProtocolTests(unittest.TestCase):
    def setUp(self):
        self.rng = torch.random.get_rng_state()
        self.addCleanup(torch.random.set_rng_state, self.rng)
        self.s = session()

    def test_sorted_addresses_and_unknown_strings_are_not_role_labels(self):
        r = start()
        r['ids'] = ['zorb', 'q', '007']
        r['observation'] = {'zorb': 1, 'q': 0, '007': 1}
        result = self.s.handle(r)
        self.assertEqual(result['ids'], ('007', 'q', 'zorb'))
        self.assertEqual(result['world_order'], paths.WORLDS)
        self.assertEqual(self.s.handle(predict())['status'], 'PREDICTED')

    def test_full_anchor_and_no_label_fields(self):
        for change in ('missing', 'null', 'truth', 'duplicate', 'boolean'):
            r = start()
            if change == 'missing': r['observation'].pop('a')
            elif change == 'null': r['observation']['a'] = None
            elif change == 'truth': r['truth'] = [0, 1, 0]
            elif change == 'duplicate': r['ids'] = ['a', 'a', 'b']
            else: r['observation']['a'] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                session().handle(r)

    def test_forecast_precedes_matching_feedback(self):
        self.s.handle(start())
        result = self.s.handle(predict())
        self.assertEqual(self.s.phase, 'PENDING')
        self.assertEqual(result['status'], 'PREDICTED')
        self.assertEqual(self.s.handle(feedback(result['receipt']))['next_step'], 1)
        self.assertEqual(self.s.phase, 'READY')
        result = self.s.handle(predict(1))
        self.assertEqual(result['step'], 1)

    def test_feedback_without_forecast_is_fatal(self):
        self.s.handle(start())
        with self.assertRaises(ValueError): self.s.handle(feedback('missing'))
        self.assertEqual(self.s.phase, 'ERROR')
        with self.assertRaises(ValueError): self.s.handle(predict())

    def test_wrong_receipt_step_or_episode_fails_without_retry(self):
        for field, value in (('receipt', 'changed'), ('step', True), ('step', 1), ('episode', 'other')):
            s = session(); s.handle(start()); r = s.handle(predict())
            f = feedback(r['receipt']); f[field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError): s.handle(f)
            self.assertEqual(s.phase, 'ERROR')

    def test_repeated_feedback_not_independent_evidence(self):
        self.s.handle(start()); r = self.s.handle(predict())
        f = feedback(r['receipt']); self.s.handle(f)
        with self.assertRaises(ValueError): self.s.handle(f)

    def test_second_forecast_cannot_replace_unconsumed_forecast(self):
        self.s.handle(start()); self.s.handle(predict())
        with self.assertRaises(ValueError): self.s.handle(predict())

    def test_invalid_actions_and_extra_hidden_labels(self):
        requests = [predict(kind='contact', members=['a', 'a']), predict(kind='set', members=['a'], value=True),
                    predict(kind='contact', members=['a', 'unknown']), predict(kind='observe', members=['b']),
                    predict(kind='contact', members=['a', 'b'], mode=1)]
        for r in requests:
            s = session(); s.handle(start())
            with self.subTest(r=r), self.assertRaises(ValueError): s.handle(r)

    def test_hidden_sensor_is_null_not_filled_from_any_truth(self):
        self.s.handle(start()); r = self.s.handle(predict())
        self.s.handle(feedback(r['receipt'], values=(None, 0, None)))
        self.assertEqual(self.s.filter.bits.tolist(), [[0., 0., 0.]])  # explicit last-observed baseline

    def test_end_after_query_does_not_require_gold_feedback(self):
        self.s.handle(start()); self.s.handle(predict())
        result = self.s.handle({'op': 'end', 'episode': 'toy'})
        self.assertTrue(result['pending_forecast'])
        self.assertEqual((result['predictions'], result['feedback_steps']), (1, 0))
        self.assertFalse(result['evaluated'])

    def test_changed_weights_block_normal_end(self):
        model = joint.JointFlatGRU(); s = session(model=model); s.handle(start())
        with torch.no_grad(): next(model.parameters()).add_(1.)
        with self.assertRaisesRegex(ValueError, 'weights changed'): s.handle({'op': 'end', 'episode': 'toy'})

    def test_cap_no_silent_pruning_or_retry(self):
        s = session(model=joint.JointKernel()); s.handle(start())
        for step in range(2):
            r = s.handle(predict(step)); s.handle(feedback(r['receipt'], step, (None, None, None)))
        r = s.handle(predict(2))
        with self.assertRaisesRegex(ValueError, 'path bound'): s.handle(feedback(r['receipt'], 2, (None, None, None)))
        self.assertEqual(s.phase, 'ERROR')

    def test_controls_abstain_without_numeric_distribution(self):
        s = session(memory=SensorMemory('prefix'), control='prefix'); s.handle(start())
        r = s.handle(predict())
        self.assertEqual(r['status'], 'ABSTAIN')
        self.assertIsNone(r['raw_log']); self.assertIsNone(r['log'])

    def test_both_families_match_unchanged_path_filter_on_synthetic_masked_history(self):
        for name, factory in model_factories().items():
            torch.manual_seed(7); model = factory(); s = session(model=model); s.handle(start())
            direct = paths.NeuralPaths(model, torch.tensor([[0., 1., 0.]], dtype=torch.float64))
            with torch.inference_mode():
                for step, values in enumerate(((None, 1, 0), (0, 1, 0))):
                    r = s.handle(predict(step))
                    raw, answered = direct.predict(torch.tensor([[2, -1, -1, -1]]))
                    log, _ = scores.normalize(raw, answered)
                    self.assertEqual(r['log'], scores.log_record(log), name)
                    if step == 0:
                        direct.receive(torch.tensor([[-1., 1., 0.]], dtype=torch.float64),
                                       torch.tensor([[False, True, True]]))
                        s.handle(feedback(r['receipt'], step, values))

    def test_json_duplicates_nan_and_nonfinite_are_rejected(self):
        for raw in ('{"a":1,"a":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":{"b":1,"b":2}}'):
            with self.assertRaises(ValueError): api.strict_json(raw)

    def test_stdout_flush_occurs_before_next_input_read(self):
        output = io.StringIO()
        frames = [start(), predict(), {'op': 'end', 'episode': 'toy'}]
        flushed = []
        class Output:
            def write(self, text): output.write(text)
            def flush(self): flushed.append(output.getvalue())
        class Input:
            def readline(inner, size):
                i = len(flushed)
                self.assertEqual(len(output.getvalue().splitlines()), i)
                return json.dumps(frames[i]) + '\n'
        self.assertEqual(api.serve(self.s, Input(), Output()), 0)
        self.assertEqual(len(flushed), 3)

    def test_transport_failure_stops_before_next_command(self):
        incoming = io.StringIO(json.dumps(start()) + '\n' + '{"truth":42}\n' + json.dumps(predict()) + '\n')
        output = io.StringIO()
        self.assertEqual(api.serve(self.s, incoming, output), 2)
        self.assertEqual(json.loads(output.getvalue().splitlines()[-1])['status'], 'ERROR')
        self.assertEqual(incoming.readline(), json.dumps(predict()) + '\n')

    def test_frame_limit_truncated_frame_and_missing_end(self):
        for text in ('x' * (api.MAX_LINE + 1) + '\n', json.dumps(start()), json.dumps(start()) + '\n'):
            output = io.StringIO()
            self.assertEqual(api.serve(session(), io.StringIO(text), output), 2)
            self.assertEqual(json.loads(output.getvalue().splitlines()[-1])['status'], 'ERROR')


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.evidence = cls.root / 'evidence'
        cls.report_digest = synthetic_evidence(cls.evidence)
        cls.bundle = cls.root / 'bundle'
        with patch.object(export, 'REPORT_SHA256', cls.report_digest):
            cls.manifest = export.export(cls.evidence, cls.bundle)
        sys.path.insert(0, str(cls.bundle))
        cls.addClassCleanup(sys.path.remove, str(cls.bundle))

    def test_bundle_contains_only_inference_code_selected_weights_and_tables(self):
        self.assertEqual(len(self.manifest['models']), 30)
        self.assertEqual(len(self.manifest['controls']), 3)
        self.assertFalse(self.manifest['independent_evaluation'])
        for p in (self.bundle / 'participant_core').glob('*.py'):
            text = p.read_text()
            for forbidden in ('from .world', 'comparison_run', 'gold_after', 'torch.optim', 'def score(', 'def make_history'):
                self.assertNotIn(forbidden, text)
        self.assertEqual(len(list((self.bundle / 'weights').glob('*.pt'))), 30)

    def test_extraction_preserves_definition_ast_and_exact_source_blocks(self):
        import ast
        for name, (_, names) in export.SELECTION.items():
            original = {n.name: n for n in ast.parse((export.SOURCE / name).read_text()).body
                        if isinstance(n, (ast.ClassDef, ast.FunctionDef))}
            generated = {n.name: n for n in ast.parse((self.bundle / 'participant_core' / name).read_text()).body
                         if isinstance(n, (ast.ClassDef, ast.FunctionDef))}
            self.assertEqual(set(names), set(generated))
            for symbol in names:
                self.assertEqual(ast.dump(original[symbol]), ast.dump(generated[symbol]), (name, symbol))

    def test_export_is_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(export, 'REPORT_SHA256', self.report_digest):
            other = Path(tmp) / 'again'
            result = export.export(self.evidence, other)
            self.assertEqual(result, self.manifest)
            self.assertEqual((other / 'manifest.json').read_bytes(), (self.bundle / 'manifest.json').read_bytes())

    def test_existing_export_and_changed_original_report_are_rejected(self):
        with patch.object(export, 'REPORT_SHA256', self.report_digest):
            with self.assertRaises(FileExistsError): export.export(self.evidence, self.bundle)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, 'original completed report'):
                export.export(self.evidence, Path(tmp) / 'out')

    def test_source_pin_change_stops_export_before_building(self):
        with patch.dict(export.PINS, {'masked_replay.py': '0' * 64}):
            with self.assertRaisesRegex(ValueError, 'frozen source changed'):
                export.selected_source('masked_replay.py')

    def test_expected_manifest_digest_is_mandatory(self):
        with self.assertRaisesRegex(ValueError, 'manifest hash'):
            api.verify_bundle(self.bundle, '0' * 64)
        self.assertEqual(api.verify_bundle(self.bundle, export.digest(self.bundle / 'manifest.json')), self.manifest)

    def test_all_thirty_synthetic_checkpoints_restore_exactly_without_rng_changes(self):
        rng = torch.random.get_rng_state()
        for row in self.manifest['models']:
            model, memory = api.restore('participant_core', self.manifest, self.bundle, row['model'], row['seed'])
            self.assertIsNone(memory)
            self.assertEqual(joint.fingerprint(model.state_dict()), row['tensor_sha256'])
        self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))

    def test_generated_filters_and_models_equal_original_for_all_arms(self):
        generated_paths = importlib.import_module('participant_core.masked_replay')
        for name, factory in model_factories().items():
            exported, _ = api.restore('participant_core', self.manifest, self.bundle, name, 7)
            with torch.random.fork_rng(devices=[]): original = factory()
            original.load_state_dict(exported.state_dict())
            anchor = torch.tensor([[0., 1., 0.]], dtype=torch.float64)
            left, right = paths.NeuralPaths(original, anchor), generated_paths.NeuralPaths(exported, anchor)
            with torch.inference_mode():
                for step in range(3):
                    action = torch.tensor([[2, -1, -1, -1]])
                    a, ma = left.predict(action); b, mb = right.predict(action)
                    self.assertTrue(torch.equal(a, b), name)
                    self.assertTrue(np.array_equal(ma, mb))
                    if step < 2:
                        reading = torch.tensor([[-1., 1., 0.]], dtype=torch.float64)
                        mask = torch.tensor([[False, True, True]])
                        left.receive(reading, mask); right.receive(reading, mask)

    def test_strong_control_restoration_and_seed_replication_rejection(self):
        for mode in ('prefix', 'local', 'contact', 'first_contact', 'no_change'):
            model, memory = api.restore('participant_core', self.manifest, self.bundle, mode, None)
            self.assertIsNone(model)
            self.assertEqual(memory is None, mode == 'no_change')
        with self.assertRaisesRegex(ValueError, 'controls have no seed'):
            api.restore('participant_core', self.manifest, self.bundle, 'contact', 7)
        with self.assertRaises(ValueError): api.restore('participant_core', self.manifest, self.bundle, 'flat', 99)

    def test_real_export_verifier_covers_all_models_and_controls_without_scoring(self):
        result = export.verify_export(self.bundle)
        self.assertEqual(result['forecast_vectors_compared'], 280)
        self.assertEqual(result['verified_neural_checkpoints'], 30)
        self.assertEqual(len(result['checks']), 70)
        self.assertFalse(result['study_run'])
        self.assertFalse(result['score_computed'])
        self.assertFalse(result['independent_review'])

    def test_modified_payload_is_rejected_before_deserialization(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'bundle'
            shutil.copytree(self.bundle, copy)
            checkpoint = next((copy / 'weights').glob('*.pt'))
            checkpoint.write_bytes(checkpoint.read_bytes() + b'changed')
            with patch.object(torch, 'load', side_effect=AssertionError('must not deserialize')):
                with self.assertRaisesRegex(ValueError, 'bundle file mismatch'):
                    api.verify_bundle(copy, export.digest(copy / 'manifest.json'))

    def test_unsafe_manifest_location_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = deepcopy(self.manifest)
            data['files'] = {'../outside': '0' * 64}
            (root / 'manifest.json').write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'unsafe bundle path'):
                api.verify_bundle(root, export.digest(root / 'manifest.json'))

    def test_real_cli_runs_from_unrelated_directory_with_no_research_imports(self):
        frames = [start(), predict(), {'op': 'end', 'episode': 'toy'}]
        result = subprocess.run([sys.executable, str(self.bundle / 'participant.py'),
            '--manifest-sha256', export.digest(self.bundle / 'manifest.json'), '--participant', 'flat', '--seed', '7'],
            cwd=self.root, input=''.join(json.dumps(r) + '\n' for r in frames), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = [json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual([r['status'] for r in rows], ['STARTED', 'PREDICTED', 'ENDED'])
        self.assertFalse(rows[-1]['evaluated'])


if __name__ == '__main__':
    unittest.main()
