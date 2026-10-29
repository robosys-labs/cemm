"""Post-hoc replay of saved checkpoints on opened cases; never a G1 test."""
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import permutations
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
from time import perf_counter, process_time
from unittest.mock import patch

from .development_run import _json, score_forecast
from .diagnose_failed_case6 import _progress, _restore_controls, _restore_models, _forbid_truth
from .factorial_run import ARMS, MODELS, SEEDS, _aggregate_case, _replay, _results_summary
from .factorial_training_data import rename_full_history
from .forecast_normalization import normalize_joint
from .full_sensor_evaluation import full_sensor_evaluation_view
from .relabel_diagnostic import compare_forecasts
from .two_pair_fixture import make_evaluator_episode
from .world import Episode

PROTOCOL_PATH = Path(__file__).with_name('full_sensor_posthoc_replay_protocol_v1.json')
PROTOCOL_SHA256 = 'ced95f5692a2b3172874f3f6911aac660930b858be05b34ee290c1dbe249437f'
PROTOCOL_COMMIT = '8905b0529af6ba0e4bade780d737f4d17fad0ccd'
ROOT = Path(__file__).resolve().parents[2]


def read_protocol():
    raw = PROTOCOL_PATH.read_bytes()
    if sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('post-hoc protocol hash mismatch')
    protocol = json.loads(raw)
    for name, digest in protocol['source_file_sha256'].items():
        if Path(name).name != name or sha256(PROTOCOL_PATH.with_name(name).read_bytes()).hexdigest() != digest:
            raise ValueError(f'source hash mismatch: {name}')
    return protocol


def _lineage(protocol):
    if os.environ.get('PYTHONHASHSEED') != '0':
        raise RuntimeError('PYTHONHASHSEED=0 required at startup')
    def git(*args):
        return subprocess.run(['git', '-C', str(ROOT), *args], check=True, capture_output=True, text=True).stdout.strip()
    def is_ancestor(first, second):
        return subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', first, second],
                              capture_output=True).returncode == 0
    if not is_ancestor(protocol['source_parent'], 'HEAD'):
        raise RuntimeError('source parent is not an ancestor')
    for args in (('diff', '--quiet'), ('diff', '--cached', '--quiet')):
        if subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True).returncode:
            raise RuntimeError('tracked tree is not clean')
    paths = [PROTOCOL_PATH.with_name(name) for name in protocol['source_file_sha256']]
    paths.extend((PROTOCOL_PATH, Path(__file__).resolve()))
    for path in paths:
        relative = str(path.resolve().relative_to(ROOT))
        result = subprocess.run(['git', '-C', str(ROOT), 'show', f'HEAD:{relative}'], capture_output=True)
        if result.returncode or result.stdout != path.read_bytes():
            raise RuntimeError(f'source file differs from HEAD: {relative}')
    runner_path = str(Path(__file__).resolve().relative_to(ROOT))
    protocol_path = str(PROTOCOL_PATH.resolve().relative_to(ROOT))
    runner_commit = git('log', '-1', '--format=%H', '--', runner_path)
    protocol_commit = git('log', '-1', '--format=%H', '--', protocol_path)
    if (protocol_commit != PROTOCOL_COMMIT or runner_commit == protocol_commit or
            not is_ancestor(protocol_commit, runner_commit)):
        raise RuntimeError('reviewed runner must follow the frozen protocol commit')
    return {'source_parent': protocol['source_parent'], 'execution_commit': git('rev-parse', 'HEAD'),
            'protocol_commit': protocol_commit, 'runner_commit': runner_commit,
            'runner_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
            'tracked_tree_clean': True,
            'untracked_present': bool(git('ls-files', '--others', '--exclude-standard'))}


def _transform(forecast, n_ids):
    status, reason, distribution = forecast
    if status == 'ABSTAIN':
        if distribution is not None:
            raise ValueError('abstention carries a distribution')
        return (status, reason, None), None
    if status != 'PREDICTED':
        raise ValueError('unknown forecast status')
    normalized, audit = normalize_joint(distribution, n_ids=n_ids)
    return (status, reason, normalized), audit


def _evaluate_case(episode, history, fits):
    original_ids = tuple(sorted(name for name, _ in history._observations[0]))
    if len(original_ids) != 3 or len(history.actions) != 5:
        raise ValueError('unexpected history inventory')
    replays, identity, shared = [], {}, {}
    # Guard ordering even against an accidental future learner or replay call.
    with patch.object(Episode, 'gold_after', _forbid_truth):
        for names in permutations(original_ids):
            mapping = dict(zip(original_ids, names))
            renamed = rename_full_history(history, mapping)
            if rename_full_history(renamed, {v: k for k, v in mapping.items()}) != history:
                raise RuntimeError('renamed history did not round-trip')
            for id_arm, target in ARMS:
                for seed in SEEDS:
                    agents, measured = _replay(renamed, fits[(id_arm, target, seed)])
                    if names not in shared:
                        shared[names] = agents[0].history
                    elif agents[0].history != shared[names]:
                        raise RuntimeError('delivered histories differ across fits')
                    transformed = []
                    for agent in agents:
                        if len(agent.feedback_diagnostics) != 5:
                            raise RuntimeError('missing feedback diagnostic')
                        transformed.append([_transform(forecast, len(original_ids)) for forecast in agent.forecasts])
                    if names == original_ids:
                        identity[(id_arm, target, seed)] = transformed
                    replays.append((mapping, id_arm, target, seed, agents, measured, transformed))
        if len(replays) != 120 or len(identity) != 20:
            raise RuntimeError('replay inventory mismatch')
    truths = [episode.gold_after(i) for i in range(5)]
    rows = []
    for mapping, id_arm, target, seed, agents, measured, transformed in replays:
        inverse = {v: k for k, v in mapping.items()}
        ids = agents[0].ids
        steps = []
        for index, truth in enumerate(truths):
            renamed_truth = tuple(truth[inverse[name]] for name in ids)
            original_truth = tuple(truth[name] for name in original_ids)
            scores = {}
            for i, (name, agent) in enumerate(zip(MODELS, agents, strict=True)):
                forecast, audit = transformed[i][index]
                score = score_forecast(*forecast, renamed_truth)
                score['normalization'] = audit
                score['feedback_diagnostic'] = agent.feedback_diagnostics[index]
                score['renaming_comparison'] = compare_forecasts(
                    identity[(id_arm, target, seed)][i][index][0], forecast,
                    original_ids, mapping, original_truth)
                scores[name] = score
            steps.append({'step': index, 'action': json.loads(agents[0].history[1 + 2 * index])['action'],
                          'ids': list(ids), 'truth': list(renamed_truth), 'models': scores})
        rows.append({'id_arm': id_arm, 'target': target, 'seed': seed, 'mapping': mapping,
                     'public_history': [json.loads(item) for item in agents[0].history], 'steps': steps,
                     'callbacks': {name: item.calls for name, item in zip(MODELS, measured, strict=True)}})
    return {'original_ids': original_ids, 'case_rows': rows}


def _accumulate_diagnostics(result, counts):
    for row in result['case_rows']:
        for step in row['steps']:
            for model, score in step['models'].items():
                count = counts[(row['id_arm'], row['target'], row['seed'], step['step'], model)]
                for field in ('queries', 'predicted', 'raw_over_one_forecasts', 'maximizer_set_changed',
                              'lexicographic_map_changed', 'renaming_comparable', 'renaming_over_tolerance',
                              'renaming_map_changed'):
                    count.setdefault(field, 0)
                audit, comparison = score.pop('normalization'), score['renaming_comparison']
                count['queries'] += 1
                if audit is not None:
                    count['predicted'] += 1
                    count['raw_over_one_forecasts'] += audit['raw_over_one_count'] > 0
                    count['maximizer_set_changed'] += audit['maximizer_set_changed']
                    count['lexicographic_map_changed'] += audit['lexicographic_map_changed']
                if comparison.get('tv') is not None:
                    count['renaming_comparable'] += 1
                    count['renaming_over_tolerance'] += comparison['over_tolerance']
                    count['renaming_map_changed'] += comparison['map_changed']


def _environment(torch):
    try:
        cpu = next((line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                    if line.lower().startswith('model name')), platform.processor() or 'unknown')
    except OSError:
        cpu = platform.processor() or 'unknown'
    return {'python': platform.python_version(), 'torch': torch.__version__, 'platform': platform.platform(),
            'cpu_model': cpu, 'torch_config_sha256': sha256(torch.__config__.show().encode()).hexdigest(),
            'threads': torch.get_num_threads(), 'inter_op_threads': torch.get_num_interop_threads(),
            'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
            'peak_rss_platform_units': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'peak_rss_unit': 'KiB' if platform.system() == 'Linux' else
                             ('bytes' if platform.system() == 'Darwin' else 'platform-defined')}


def _write_failure(output, phase, exc, completed):
    (output / 'COMPLETE').unlink(missing_ok=True)
    (output / 'report.json').unlink(missing_ok=True)
    (output / 'FAILED.json').write_text(_json({
        'status': 'INCOMPLETE', 'phase': phase, 'type': type(exc).__name__, 'message': str(exc),
        'completed_cases': completed, 'missing_cases': [i for i in range(64) if i not in completed],
        'partial_case_records': 'cases.jsonl' if (output / 'cases.jsonl').exists() else None,
        'note': 'This separate post-hoc replay did not complete; the original v2 remains incomplete.'}),
        encoding='utf-8')


def run(failed_dir, output_dir):
    output = Path(output_dir).resolve()
    if output.is_relative_to(ROOT):
        raise ValueError('output must be outside source tree')
    output.mkdir(parents=False, exist_ok=False)
    started, cpu_started = perf_counter(), process_time()
    phase, completed, restored, old_runtime = 'setup', [], False, None
    try:
        protocol = read_protocol()
        import torch
        if (torch.__version__ != '2.10.0+cpu' or not platform.python_version().startswith('3.13.') or
                torch.get_default_dtype() != torch.float32 or torch.version.cuda is not None or
                torch.version.hip is not None or (hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()) or
                (hasattr(torch, 'xpu') and torch.xpu.is_available())):
            raise RuntimeError('requires CPU-only PyTorch 2.10 and Python 3.13')
        lineage = _lineage(protocol)
        old_runtime = (torch.get_num_threads(), torch.are_deterministic_algorithms_enabled(),
                       torch.is_deterministic_algorithms_warn_only_enabled())
        phase = 'verification'
        with torch.random.fork_rng(devices=[]):
            torch.set_num_threads(1)
            torch.use_deterministic_algorithms(True)
            checkpoints, controls = _progress(Path(failed_dir))
            fits = _restore_models(Path(failed_dir), checkpoints, torch)
            _restore_controls(fits, controls)
            phase = 'evaluation'
            rows, callback_times, paired = defaultdict(list), defaultdict(list), defaultdict(Counter)
            diagnostics = defaultdict(Counter)
            replay_start, replay_cpu = perf_counter(), process_time()
            with (output / 'cases.jsonl').open('x', encoding='utf-8') as stream:
                for case in range(64):
                    episode = make_evaluator_episode(case, block=0)
                    history = full_sensor_evaluation_view(episode)
                    result = _evaluate_case(episode, history, fits)
                    result['case'] = case
                    stream.write(_json(result) + '\n')
                    stream.flush()
                    _accumulate_diagnostics(result, diagnostics)
                    _aggregate_case(result, rows, callback_times, paired)
                    completed.append(case)
            replay_cost = {'wall_seconds': perf_counter() - replay_start,
                           'cpu_seconds': process_time() - replay_cpu}
            phase = 'verification'
            summaries, latency, primary, contrasts, interactions = _results_summary(rows, callback_times, paired)
            if len(completed) != 64 or len(diagnostics) != len(summaries) or any(c['queries'] != 384 for c in diagnostics.values()):
                raise RuntimeError('incomplete diagnostic inventory')
            for summary in summaries:
                summary['wrong'] = summary['answered'] - summary['correct']
            diagnostics_rows = [{'id_arm': key[0], 'target': key[1], 'seed': key[2], 'step': key[3],
                                 'model': key[4], **value} for key, value in sorted(diagnostics.items())]
            case_hash = sha256()
            with (output / 'cases.jsonl').open('rb') as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                    case_hash.update(chunk)
            report = {'status': protocol['status'], 'protocol_sha256': PROTOCOL_SHA256, 'protocol': protocol,
                      'lineage': lineage, 'verified_checkpoints': len(checkpoints),
                      'checkpoint_checks': [{'arm': key[0], 'model': key[1], **value}
                                            for key, value in sorted(checkpoints.items())],
                      'verified_control_tables': len(controls),
                      'control_checks': [{'id_arm': key[0], 'model': key[1],
                                          'table_sha256': value['table_sha256']}
                                         for key, value in sorted(controls.items())],
                      'prior_host_and_training_metadata': 'not recorded',
                      'archive_zip_hash_verified': False, 'cases_sha256': case_hash.hexdigest(),
                      'summaries': summaries, 'callback_p95': latency, 'primary': primary,
                      'paired_contrasts': contrasts, 'interactions': interactions, 'diagnostics': diagnostics_rows,
                      'replay_cost': replay_cost, 'environment': _environment(torch),
                      'wall_seconds': perf_counter() - started, 'cpu_seconds': process_time() - cpu_started}
            torch.set_num_threads(old_runtime[0])
            torch.use_deterministic_algorithms(old_runtime[1], warn_only=old_runtime[2])
            restored = True
            phase = 'publication'
            report_json = _json(report)
            (output / 'report.json').write_text(report_json, encoding='utf-8')
            (output / 'COMPLETE').write_text(sha256(report_json.encode()).hexdigest() + '\n', encoding='ascii')
            return report
    except BaseException as exc:
        try:
            _write_failure(output, phase, exc, completed)
        except OSError:
            pass
        raise
    finally:
        if old_runtime is not None and not restored:
            torch.set_num_threads(old_runtime[0])
            torch.use_deterministic_algorithms(old_runtime[1], warn_only=old_runtime[2])


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--failed-output', required=True)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    run(args.failed_output, args.output_dir)
