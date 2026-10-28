"""Synthetic replay tests; no public case, fit or score is executed."""
from collections import Counter, defaultdict
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from experiments.predictive_nucleus import posthoc_replay as replay


class PosthocReplayTests(unittest.TestCase):
    def test_protocol_digest_and_source_hashes(self):
        self.assertEqual(replay.read_protocol()['status'], 'POST_HOC_OPEN_PUBLIC_DEVELOPMENT_NOT_G1')
        with patch.object(replay, 'PROTOCOL_SHA256', '0' * 64):
            with self.assertRaisesRegex(ValueError, 'protocol hash'):
                replay.read_protocol()

    def test_normalization_preserves_support_and_abstention(self):
        raw = {(1, 1, 1): 1.00000004, (0, 0, 0): 0.0}
        (status, reason, distribution), audit = replay._transform(('PREDICTED', None, raw), 3)
        self.assertEqual((status, reason), ('PREDICTED', None))
        self.assertEqual(set(distribution), set(raw))
        self.assertEqual(distribution[(0, 0, 0)], 0)
        self.assertEqual(raw[(1, 1, 1)], 1.00000004)
        self.assertEqual(audit['raw_over_one_count'], 1)
        self.assertEqual(replay._transform(('ABSTAIN', 'missing', None), 3),
                         (('ABSTAIN', 'missing', None), None))
        for invalid in [('ABSTAIN', None, {}), ('PREDICTED', None, {(1, 1, 1): 1.1}),
                        ('UNKNOWN', None, None)]:
            with self.assertRaises(ValueError):
                replay._transform(invalid, 3)

    def test_all_replays_complete_before_truth_and_only_normalized_scored(self):
        class History:
            _observations = ((('a', 0), ('b', 0), ('c', 0)),)
            actions = (None,) * 5
        history = History()
        calls, truth_calls = [], []
        anchor = json.dumps({'t': 0, 'measurements': []})
        turn = json.dumps({'action': {'kind': 'observe', 'participants': []}, 'observation': {}})
        feedback = json.dumps({'t': 1, 'measurements': []})
        fake_history = [anchor] + [x for _ in range(5) for x in (turn, feedback)]
        def produce(view, fit):
            calls.append(1)
            agents = []
            for model in replay.MODELS:
                forecast = ('ABSTAIN', 'missing', None) if model == 'literal_history_memory' else (
                    'PREDICTED', None, {(1, 1, 1): 1.00000004, (0, 0, 0): 0.0})
                agents.append(SimpleNamespace(ids=('a', 'b', 'c'), history=fake_history,
                              forecasts=[forecast] * 5, feedback_diagnostics=[None] * 5))
            timings = [{'phase': phase, 'wall_seconds': 0.0, 'cpu_seconds': 0.0}
                       for _ in range(5) for phase in ('predict', 'receive')]
            return agents, [SimpleNamespace(calls=timings)] * 6
        def gold(step):
            self.assertEqual(len(calls), 120)
            truth_calls.append(step)
            return {'a': 0, 'b': 0, 'c': 0}
        fits = {(a, m, seed): object() for a, m in replay.ARMS for seed in replay.SEEDS}
        with patch.object(replay, 'rename_full_history', side_effect=lambda value, mapping: value), \
             patch.object(replay, '_replay', side_effect=produce):
            result = replay._evaluate_case(SimpleNamespace(gold_after=gold), history, fits)
        self.assertEqual((len(calls), truth_calls, len(result['case_rows'])), (120, list(range(5)), 120))
        score = result['case_rows'][0]['steps'][0]['models']['flat']
        self.assertEqual(score['normalization']['raw_over_one_count'], 1)
        self.assertTrue(score['joint_log_score']['zero_probability'])
        self.assertIsNone(score['joint_log_score']['uncapped_log_loss'])
        self.assertEqual(score['normalization']['per_world'][1]['after'], 1.0)
        abstain = result['case_rows'][0]['steps'][0]['models']['literal_history_memory']
        self.assertEqual(abstain['status'], 'ABSTAIN')
        self.assertIsNone(abstain['normalization'])
        self.assertIsNone(abstain['joint_brier'])
        counts = defaultdict(Counter)
        replay._accumulate_diagnostics(result, counts)
        rows, timings, paired = defaultdict(list), defaultdict(list), defaultdict(Counter)
        replay._aggregate_case(result, rows, timings, paired)
        self.assertEqual(next(iter(paired.values()))['queries'], 24)
        self.assertTrue(all(c['queries'] == 6 for c in counts.values()))
        self.assertNotIn('normalization', result['case_rows'][0]['steps'][0]['models']['flat'])

    def test_failure_removes_success_and_records_incomplete_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('COMPLETE', 'report.json', 'cases.jsonl'):
                (root / name).write_text('partial')
            replay._write_failure(root, 'evaluation', ValueError('bad mass'), [0, 1])
            self.assertFalse((root / 'COMPLETE').exists())
            self.assertFalse((root / 'report.json').exists())
            failure = json.loads((root / 'FAILED.json').read_text())
            self.assertEqual(failure['status'], 'INCOMPLETE')
            self.assertEqual(failure['completed_cases'], [0, 1])
            self.assertEqual(len(failure['missing_cases']), 62)
            self.assertEqual(failure['partial_case_records'], 'cases.jsonl')

    def test_setup_failure_is_recorded_without_overwriting_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / 'fresh'
            with patch.object(replay, 'read_protocol', side_effect=ValueError('tampered protocol')):
                with self.assertRaisesRegex(ValueError, 'tampered protocol'):
                    replay.run('unused', output)
            failure = json.loads((output / 'FAILED.json').read_text())
            self.assertEqual((failure['phase'], failure['message']), ('setup', 'tampered protocol'))
            self.assertEqual(failure['completed_cases'], [])
            self.assertFalse((output / 'report.json').exists())
            self.assertFalse((output / 'COMPLETE').exists())
            existing = Path(tmp) / 'existing'
            existing.mkdir()
            sentinel = existing / 'report.json'
            sentinel.write_text('do not change')
            with self.assertRaises(FileExistsError):
                replay.run('unused', existing)
            self.assertEqual(sentinel.read_text(), 'do not change')
            self.assertFalse((existing / 'FAILED.json').exists())
            with self.assertRaisesRegex(ValueError, 'outside source tree'):
                replay.run('unused', replay.ROOT / 'invalid-test-output')

    def test_nonidentity_renaming_resolves_tie_in_renamed_coordinates(self):
        class History:
            _observations = ((('a', 0), ('b', 1), ('c', 0)),)
            actions = (None,) * 5
            def __init__(self, mapping):
                self.mapping = mapping
            def __eq__(self, other):
                return isinstance(other, History) and self.mapping == other.mapping
        initial = History({'a': 'a', 'b': 'b', 'c': 'c'})
        def rename(history, mapping):
            return History({name: mapping[value] for name, value in history.mapping.items()})
        anchor = json.dumps({'t': 0, 'measurements': []})
        turn = json.dumps({'action': {'kind': 'observe', 'participants': []}, 'observation': {}})
        feedback = json.dumps({'t': 1, 'measurements': []})
        public_history = [anchor] + [x for _ in range(5) for x in (turn, feedback)]
        def produce(history, fit):
            def world(winner):
                return tuple(int(name == history.mapping[winner]) for name in ('a', 'b', 'c'))
            forecast = ('PREDICTED', None, {world('a'): 0.5, world('b'): 0.5})
            agent = SimpleNamespace(ids=('a', 'b', 'c'), history=public_history,
                                    forecasts=[forecast] * 5, feedback_diagnostics=[None] * 5)
            calls = [{'phase': phase, 'wall_seconds': 0.0, 'cpu_seconds': 0.0}
                     for _ in range(5) for phase in ('predict', 'receive')]
            return [agent] * 6, [SimpleNamespace(calls=calls)] * 6
        fits = {(a, m, seed): object() for a, m in replay.ARMS for seed in replay.SEEDS}
        episode = SimpleNamespace(gold_after=lambda step: {'a': 0, 'b': 1, 'c': 0})
        with patch.object(replay, 'rename_full_history', side_effect=rename), \
             patch.object(replay, '_replay', side_effect=produce):
            result = replay._evaluate_case(episode, initial, fits)
        renamed = next(row for row in result['case_rows']
                       if row['mapping'] == {'a': 'c', 'b': 'a', 'c': 'b'})
        step = renamed['steps'][0]
        score = step['models']['flat']
        self.assertEqual(step['truth'], [1, 0, 0])
        self.assertEqual(score['map_world'], [0, 0, 1])
        self.assertFalse(score['map_correct'])
        comparison = score['renaming_comparison']
        self.assertEqual(comparison['tv'], 0.0)
        self.assertTrue(comparison['map_changed'])
        self.assertTrue(comparison['correct_original'])
        self.assertFalse(comparison['correct_renamed'])

    def test_invalid_mass_aborts_before_gold(self):
        class History:
            _observations = ((('a', 0), ('b', 0), ('c', 0)),)
            actions = (None,) * 5
        calls = []
        def produce(view, fit):
            agent = SimpleNamespace(ids=('a', 'b', 'c'), history=[],
                forecasts=[('PREDICTED', None, {(0, 0, 0): 1.1})] * 5,
                feedback_diagnostics=[None] * 5)
            return [agent] * 6, [SimpleNamespace(calls=[])] * 6
        fits = {(a, m, seed): object() for a, m in replay.ARMS for seed in replay.SEEDS}
        episode = SimpleNamespace(gold_after=lambda step: calls.append(step))
        with patch.object(replay, 'rename_full_history', side_effect=lambda history, mapping: history), \
             patch.object(replay, '_replay', side_effect=produce):
            with self.assertRaisesRegex(ValueError, 'within tolerance'):
                replay._evaluate_case(episode, History(), fits)
        self.assertEqual(calls, [])

    def test_lineage_requires_protocol_ancestor_clean_committed_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / 'experiments' / 'predictive_nucleus'
            src.mkdir(parents=True)
            protocol_path, runner_path, source = (src / 'p.json', src / 'runner.py', src / 'source.py')
            def git(*args):
                return subprocess.run(['git', '-C', tmp, *args], check=True, capture_output=True, text=True).stdout.strip()
            git('init', '-q')
            git('config', 'user.email', 'synthetic@example.test')
            git('config', 'user.name', 'Synthetic test')
            source.write_text('source\n')
            protocol_path.write_text('protocol\n')
            git('add', '.')
            git('commit', '-qm', 'freeze')
            protocol_commit = git('rev-parse', 'HEAD')
            runner_path.write_text('runner\n')
            git('add', '.')
            git('commit', '-qm', 'runner')
            protocol = {'source_parent': protocol_commit,
                        'source_file_sha256': {'source.py': sha256(source.read_bytes()).hexdigest()}}
            with patch.object(replay, 'ROOT', root), patch.object(replay, 'PROTOCOL_PATH', protocol_path), \
                 patch.object(replay, 'PROTOCOL_COMMIT', protocol_commit), \
                 patch.object(replay, '__file__', str(runner_path)), patch.dict(os.environ, {'PYTHONHASHSEED': '0'}):
                self.assertEqual(replay._lineage(protocol)['protocol_commit'], protocol_commit)
                runner_path.write_text('changed\n')
                with self.assertRaisesRegex(RuntimeError, 'not clean'):
                    replay._lineage(protocol)
                git('checkout', '--', str(runner_path))
                with patch.object(replay, 'PROTOCOL_COMMIT', '0' * 40):
                    with self.assertRaisesRegex(RuntimeError, 'frozen protocol'):
                        replay._lineage(protocol)


if __name__ == '__main__':
    unittest.main()
