"""One frozen-checkpoint transfer evaluation. No optimizer or training invocation."""
from hashlib import sha256
import gzip
import json
import os
from pathlib import Path
import signal
from time import perf_counter, process_time

import numpy as np
import torch

from . import comparison_scoring as s
from .comparison_execution import (_restore, configure_runtime, digest_file, environment,
                                  read_protocol, write_json)
from .comparison_run import _load_control, emit
from .informative_curriculum import model_factories
from .masked_replay import replay
from .sensor_transfer_data import build, HANDLES

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).parent
PROTOCOL = SOURCE / 'sensor_transfer_protocol_v1.json'


def evaluate(trace, truth, oracle, folder, key, *, model=None, memory=None,
             first_contact=False, no_change=False):
    start, cpu_start = perf_counter(), process_time()
    path = folder / (key + '.jsonl.gz')
    with path.open('xb') as binary, gzip.open(binary, 'wt', encoding='utf-8') as stream:
        emit(stream, {'kind': 'header', 'key': key, 'episode_index': 'case*6 + lexicographic view',
                      'handles': HANDLES, 'physical_to_view_mappings': s.PERMUTATIONS,
                      'readings': trace.readings.tolist(), 'masks': trace.masks.tolist(),
                      'actions': trace.actions.tolist(), 'trace_sha256': trace.digest()})
        raw, logp, answered, offsets, diagnostics = replay(trace, stream, model=model, memory=memory,
                                        first_contact=first_contact, no_change=no_change)
        # Only after all flushed forecasts/feedback: use evaluator truth and oracle.
        score = s.score(logp, answered, truth[1:], truth[:-1], raw)
        ambiguity = (oracle > 0).sum(-1) > 1
        renaming, _, _ = s.renaming(logp, answered, len(truth[0]) // 6)
        codes = np.where(answered, score['correct'].astype(np.uint8), 2)
        report = {'key': key, 'steps': [{'step': t, **s.summary(s.subset(score, t)),
                    'identifiable': s.summary(s.subset(score, t), ~ambiguity[t]),
                    'ambiguous': s.summary(s.subset(score, t), ambiguity[t])} for t in range(len(logp))],
                  'role_pairs': s.role_pairs(codes, 6, len(truth[0]) // 6), 'renaming': renaming,
                  'max_abs_log_correction': float(np.abs(offsets).max()), 'filter_diagnostics': diagnostics}
        emit(stream, {'kind': 'evaluator', 'truth': truth.tolist(), 'oracle': oracle.tolist(),
                      'codes': codes.tolist(), 'maximizers': score['maximizers'].tolist(),
                      'unchanged_bit_errors': score['unchanged_bit_errors'].tolist()})
        emit(stream, {'kind': 'summary', **report})
    report.update(file=path.name, file_sha256=digest_file(path), wall_seconds=perf_counter() - start,
                  cpu_seconds=process_time() - cpu_start, timing_includes='replay, scoring and output I/O')
    return report, codes


def run(evidence, output, manifest, manifest_sha, code_commit):
    # Verify committed implementation bytes before any scientific forecasts.
    s.require(digest_file(manifest) == manifest_sha, 'implementation manifest changed')
    implementation = json.loads(Path(manifest).read_text())
    for name, digest in implementation['source_sha256'].items():
        s.require(Path(name).as_posix() == name and not Path(name).is_absolute() and '..' not in Path(name).parts,
                  'unsafe source manifest path')
        s.require(digest_file(SOURCE / name) == digest, f'implementation changed: {name}')
    spec = json.loads(PROTOCOL.read_text())
    read_protocol()  # Preserve every historical learner/data source lock.
    evidence, output = Path(evidence).resolve(), Path(output)
    s.require(not output.is_symlink() and not output.resolve().is_relative_to(ROOT), 'output outside source required')
    output.mkdir(exist_ok=False, parents=False)
    started, cpu_started, completed = perf_counter(), process_time(), []
    phase, key = 'verification', None
    def timeout(signum, frame):
        raise TimeoutError('frozen 15-minute deadline reached')
    prior_handler = signal.signal(signal.SIGALRM, timeout)
    signal.alarm(900)
    try:
        host = configure_runtime()
        s.require(digest_file(evidence / 'report.json') == spec['checkpoint_archive']['report_sha256'],
                  'prior report hash mismatch')
        s.require((evidence / 'COMPLETE').read_text().strip() == spec['checkpoint_archive']['report_sha256'],
                  'prior completion hash mismatch')
        old_report = json.loads((evidence / 'report.json').read_text())
        # Require exact metadata equality with the hash-pinned full report.
        fit_path = evidence / 'fits' / 'FIT_PHASE.json'
        fitted = json.loads(fit_path.read_text())
        s.require(fitted == old_report['fits'], 'prior fit phase disagrees with pinned report')
        chosen = [r for r in fitted['fits'] if r['task']['regime'] == spec['selection']['regime'] and
                  r['task']['condition'] == spec['selection']['training_condition']]
        expected = {(name, seed) for name in spec['selection']['models'] for seed in spec['selection']['seeds']}
        s.require(len(chosen) == 30 and {(r['task']['model'], r['task']['seed']) for r in chosen} == expected,
                  'checkpoint selection mismatch')
        factories, models = model_factories(), []
        for row in chosen:
            task = row['task']
            folder = evidence / 'fits' / f"fit-{task['ordinal']:03d}"
            model = _restore(factories[task['model']], folder / 'final.pt', row['final'])
            models.append((task['model'], task['seed'], model))
        controls = {r['mode']: _load_control(r, evidence / 'fits') for r in fitted['controls']
                    if r['condition'] == 'informative'}
        s.require(set(controls) == {'prefix', 'local', 'contact'}, 'control inventory mismatch')
        write_json(output / 'STARTED.json', {'status': 'IN_PROGRESS', 'protocol': spec,
            'protocol_sha256': digest_file(PROTOCOL), 'implementation': implementation,
            'manifest_sha256': manifest_sha, 'code_commit': code_commit, 'environment': host,
            'checkpoint_checks': chosen, 'control_checks': [r for r in fitted['controls'] if r['condition'] == 'informative'],
            'source_note': 'all manifest source bytes checked; code commit supplied by invoking verified workflow; hashes are integrity checks, not independent custody'})
        (output / 'records').mkdir()
        reports, cache, data = [], {}, {}
        phase = 'evaluation'
        for family in spec['families']:
            for policy in spec['sensor_policies']:
                trace, truth, oracle = build(family, policy)
                data[family + '-' + policy] = {'trace_sha256': trace.digest(),
                    'truth_sha256': sha256(truth.tobytes()).hexdigest(),
                    'oracle_sha256': sha256(oracle.tobytes()).hexdigest()}
                candidates = [(name, seed, {'model': model}) for name, seed, model in models]
                candidates += [(name, None, {'no_change': True} if name == 'no_change_last_observed' else
                        {'memory': controls['contact' if name == 'first_contact' else name],
                         'first_contact': name == 'first_contact'}) for name in spec['controls']]
                for name, seed, kwargs in candidates:
                    key = f'{family}-{policy}-{name}-{seed}'
                    report, codes = evaluate(trace, truth, oracle, output / 'records', key, **kwargs)
                    report.update(family=family, policy=policy, model=name, seed=seed)
                    reports.append(report); cache[family, policy, name, seed] = codes
                    completed.append(key)
                    print(key, 'retained', flush=True)  # No outcome-dependent scheduling.
        phase = 'publication'
        s.require(len(reports) == 210 and len(set(completed)) == 210, 'incomplete transfer inventory')
        pairs = []
        for (family, policy, name, seed), codes in cache.items():
            if policy != 'full':
                before = cache[family, 'full', name, seed]
                for t in range(8):
                    pairs.append({'family': family, 'policy': policy, 'model': name, 'seed': seed,
                                  'step': t, **s.paired(before[t], codes[t])})
        report = {'status': 'COMPLETE_FROZEN_TRANSFER_NOT_G1', 'gate_g1': 'NOT_ADMITTED',
                  'protocol_sha256': digest_file(PROTOCOL), 'manifest_sha256': manifest_sha,
                  'code_commit': code_commit, 'checkpoint_checks': chosen, 'evaluations': reports,
                  'paired_full_to_masked': pairs, 'datasets': data, 'environment': environment(),
                  'wall_seconds': perf_counter() - started, 'cpu_seconds': process_time() - cpu_started,
                  'limits': ['same-author evaluation, not independent custody', 'supplied finite-path filter',
                             'same physics and three entities', 'unmatched original capacities/training costs',
                             'opened outcome must not be tuned', 'no retraining or calibration']}
        digest = write_json(output / 'report.json', report)
        with (output / 'COMPLETE').open('x') as stream:
            stream.write(digest + '\n'); stream.flush(); os.fsync(stream.fileno())
        return report
    except BaseException as exc:
        (output / 'COMPLETE').unlink(missing_ok=True)
        (output / 'report.json').unlink(missing_ok=True)
        write_json(output / 'FAILED.json', {'status': 'INCOMPLETE', 'phase': phase, 'key': key,
                   'type': type(exc).__name__, 'error': str(exc), 'completed': completed,
                   'wall_seconds': perf_counter() - started})
        raise
    finally:
        signal.alarm(0); signal.signal(signal.SIGALRM, prior_handler)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('evidence', 'output', 'manifest', 'manifest-sha', 'code-commit'):
        parser.add_argument('--' + flag, required=True)
    args = parser.parse_args()
    run(args.evidence, args.output, args.manifest, args.manifest_sha, args.code_commit)
