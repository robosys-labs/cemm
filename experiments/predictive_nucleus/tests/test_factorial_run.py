"""Synthetic ordering/failure tests: no public fit or scored run."""
import json
import os
import subprocess
import tempfile
import unittest
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from experiments.predictive_nucleus import factorial_run as runner


class FactorialRunTests(unittest.TestCase):
    def test_unfrozen_protocol_fails_closed(self):
        with patch.object(runner, "PROTOCOL_SHA256", None):
            with self.assertRaisesRegex(RuntimeError, "not frozen"):
                runner.read_protocol()

    def test_committed_protocol_digest_and_tamper_rejection(self):
        with patch.object(runner, "PROTOCOL_SHA256", "2386a03847e85a75a259b0f87f03070f1643c53ca932c12abdd386cb59147377"):
            protocol = runner.read_protocol()
            self.assertEqual(protocol['source_parent'], 'ae618a0dd6011e060697ead6666a33673b2eff08')
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / 'tampered.json'
                path.write_bytes(runner.PROTOCOL_PATH.read_bytes() + b' ')
                with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                    runner.read_protocol(path)

    def test_all_case_replays_finish_before_first_truth(self):
        class History:
            _observations = ((('a', 0), ('b', 0), ('c', 0)),)
        history = History()
        replay_count, gold_calls = [], []
        anchor = json.dumps({"t": 0, "measurements": []})
        turn = json.dumps({"action": {"kind": "observe", "participants": []}, "observation": {}})
        feedback = json.dumps({"t": 1, "measurements": []})
        fake_history = [anchor] + [x for _ in range(5) for x in (turn, feedback)]
        def replay(view, fit):
            replay_count.append(1)
            agent = SimpleNamespace(ids=('a', 'b', 'c'), history=fake_history,
                                    forecasts=[('PREDICTED', None, {(0, 0, 0): 1.0})] * 5,
                                    feedback_diagnostics=[None] * 5)
            calls = [{"phase": phase, "wall_seconds": 0.0, "cpu_seconds": 0.0}
                     for _ in range(5) for phase in ("predict", "receive")]
            return (agent,) * 6, (SimpleNamespace(calls=calls),) * 6
        class Episode:
            def gold_after(self, step):
                if len(replay_count) != 120:
                    raise AssertionError("truth accessed before all replays")
                gold_calls.append(step)
                return {"a": 0, "b": 0, "c": 0}
        fits = {(a, m, seed): object() for a, m in runner.ARMS for seed in runner.SEEDS}
        def fake_score(*args):
            return {"status": "PREDICTED", "map_correct": True,
                    "joint_brier": 0.0, "joint_log_score": None, "world_probabilities": []}
        with patch.object(runner, "rename_full_history", side_effect=lambda value, mapping: value), \
             patch.object(runner, "_replay", side_effect=replay), \
             patch.object(runner, "score_forecast", side_effect=fake_score), \
             patch.object(runner, "compare_forecasts", return_value={}):
            result = runner._evaluate_case(Episode(), history, fits)
        self.assertEqual((len(replay_count), gold_calls, len(result["case_rows"])), (120, list(range(5)), 120))
        rows, timing, paired = defaultdict(list), defaultdict(list), defaultdict(Counter)
        runner._aggregate_case(result, rows, timing, paired)
        for counts in paired.values():
            self.assertEqual(counts["queries"], 24)
            self.assertEqual((counts["fixed"], counts["regressed"]), (0, 0))

    def test_failure_removes_success_artifacts_and_inventories_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "report.json").write_text("incomplete primary result")
            (root / "COMPLETE").write_text("invalid")
            (root / "repeated-masked-7-flat.pt").write_bytes(b"checkpoint")
            runner._write_failure(root, "evaluation", ValueError("bad callback"), [0, 1])
            self.assertFalse((root / "report.json").exists())
            self.assertFalse((root / "COMPLETE").exists())
            failure = json.loads((root / "FAILED.json").read_text())
            self.assertEqual(failure["status"], "INCOMPLETE")
            self.assertEqual(failure["completed_cases"], [0, 1])
            self.assertEqual(len(failure["missing_cases"]), 62)
            self.assertEqual(len(failure["present_checkpoint_files"]), 1)
            self.assertEqual(len(failure["missing_checkpoint_files"]), 39)

    def test_synthetic_nontied_world_maps_through_all_six_permutations(self):
        class History:
            _observations = ((('a', 1), ('b', 0), ('c', 1)),)
            def __init__(self, mapping): self.mapping = mapping
            def __eq__(self, other): return isinstance(other, History) and self.mapping == other.mapping
        initial = History({"a": "a", "b": "b", "c": "c"})
        def rename(history, mapping):
            return History({name: mapping[renamed] for name, renamed in history.mapping.items()})
        anchor = json.dumps({"t": 0, "measurements": []})
        turn = json.dumps({"action": {"kind": "observe", "participants": []}, "observation": {}})
        feedback = json.dumps({"t": 1, "measurements": []})
        fake_history = [anchor] + [x for _ in range(5) for x in (turn, feedback)]
        truth = {"a": 1, "b": 0, "c": 1}
        def replay(history, fit):
            inverse = {v: k for k, v in history.mapping.items()}
            renamed_truth = tuple(truth[inverse[name]] for name in ("a", "b", "c"))
            agent = SimpleNamespace(ids=('a', 'b', 'c'), history=fake_history,
                                    forecasts=[('PREDICTED', None, {renamed_truth: 1.0})] * 5,
                                    feedback_diagnostics=[None] * 5)
            calls = [{"phase": phase, "wall_seconds": 0.0, "cpu_seconds": 0.0}
                     for _ in range(5) for phase in ("predict", "receive")]
            return (agent,) * 6, (SimpleNamespace(calls=calls),) * 6
        episode = SimpleNamespace(gold_after=lambda step: truth)
        fits = {(a, m, seed): object() for a, m in runner.ARMS for seed in runner.SEEDS}
        with patch.object(runner, "rename_full_history", side_effect=rename), \
             patch.object(runner, "_replay", side_effect=replay):
            result = runner._evaluate_case(episode, initial, fits)
        for row in result["case_rows"]:
            score = row["steps"][0]["models"]["flat"]
            self.assertTrue(score["map_correct"])
            self.assertEqual(score["renaming_comparison"]["tv"], 0.0)
            self.assertFalse(score["renaming_comparison"]["map_changed"])
            mapped = score["renaming_comparison"]["renamed_world_probabilities_mapped_back"]
            self.assertEqual(next(item["world"] for item in mapped if item["probability"] == 1.0), [1, 0, 1])

    def test_synthetic_exact_tie_changes_map_but_not_distribution(self):
        original = ('PREDICTED', None, {(1, 0, 0): .5, (0, 1, 0): .5})
        renamed = ('PREDICTED', None, {(0, 0, 1): .5, (1, 0, 0): .5})
        result = runner.compare_forecasts(original, renamed, ('a', 'b', 'c'),
                                          {'a': 'c', 'b': 'a', 'c': 'b'}, (0, 1, 0))
        self.assertEqual(result['tv'], 0.0)
        self.assertTrue(result['original_map_tied'])
        self.assertTrue(result['renamed_map_tied'])
        self.assertTrue(result['map_changed'])
        self.assertTrue(result['correct_original'])
        self.assertFalse(result['correct_renamed'])

    def test_git_lineage_rejects_uncommitted_and_same_commit_runner(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / 'experiments' / 'predictive_nucleus'
            src.mkdir(parents=True)
            protocol = src / 'full_sensor_paired_protocol_v2.json'
            source = src / 'model.py'
            script = src / 'factorial_run.py'
            protocol.write_text('protocol')
            source.write_text('source')
            def git(*args):
                return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
            git('init', '-q')
            git('config', 'user.name', 'Synthetic Test')
            git('config', 'user.email', 'synthetic@localhost')
            git('add', str(protocol.relative_to(root)), str(source.relative_to(root)))
            git('commit', '-qm', 'freeze protocol')
            protocol_commit = git('rev-parse', 'HEAD')
            script.write_text('runner')
            data = {'source_parent': protocol_commit, 'source_file_sha256': {'model.py': 'unused'}}
            with patch.object(runner, '__file__', str(script)), patch.object(runner, 'PROTOCOL_PATH', protocol), \
                 patch.object(runner, 'PROTOCOL_COMMIT', protocol_commit), patch.dict(os.environ, {'PYTHONHASHSEED': '0'}):
                with self.assertRaisesRegex(RuntimeError, 'uncommitted'):
                    runner._lineage(data)
                git('add', str(script.relative_to(root)))
                git('commit', '-qm', 'add runner')
                actual = runner._lineage(data)
                self.assertEqual(actual['protocol_commit'], protocol_commit)
                self.assertNotEqual(actual['runner_commit'], protocol_commit)
                git('reset', '--soft', protocol_commit)
                git('commit', '--amend', '-qm', 'incorrect combined commit')
                combined = git('rev-parse', 'HEAD')
                with patch.object(runner, 'PROTOCOL_COMMIT', combined):
                    with self.assertRaisesRegex(RuntimeError, 'must precede'):
                        runner._lineage({**data, 'source_parent': combined})
                git('reset', '--hard', actual['runner_commit'])
                script.write_text('changed')
                with self.assertRaisesRegex(RuntimeError, 'tracked tree'):
                    runner._lineage(data)
                script.write_text('runner')
                git('rm', '-q', str(source.relative_to(root)))
                git('commit', '-qm', 'remove source')
                source.write_text('source')
                with self.assertRaisesRegex(RuntimeError, 'uncommitted'):
                    runner._lineage(data)


if __name__ == "__main__":
    unittest.main()
