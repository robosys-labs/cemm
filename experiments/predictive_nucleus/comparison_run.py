"""Execute the frozen public comparison once; never a G1 admission claim.

Reuse the existing fit/checkpoint phase. No hyperparameter search, model edits,
retries or resumed partial studies. Ordinary CI exercises only synthetic tests.
"""
from collections import Counter, defaultdict
from contextlib import contextmanager
from hashlib import sha256
import gzip
import json
import os
from pathlib import Path
import subprocess
from time import perf_counter, process_time

import numpy as np
import torch

from . import comparison_scoring as s


def emit(stream, record):
    stream.write(json.dumps(record, separators=(',', ':'), allow_nan=False) + '\n')
    stream.flush()


def _array_record(raw):
    a = raw.detach().cpu().numpy()
    if np.isnan(a).any() or np.isposinf(a).any():
        # Keep the offending vector as data; never feed these values to scores.
        return {'values': np.where(np.isfinite(a), a, None).tolist(),
                'negative_infinity': np.argwhere(np.isneginf(a)).tolist(),
                'positive_infinity': np.argwhere(np.isposinf(a)).tolist(),
                'nan': np.argwhere(np.isnan(a)).tolist()}
    return s.log_record(a)


def _freeze_model(model):
    from .joint_objective import fingerprint
    return fingerprint(model.state_dict())


def replay(model, batch, stream, *, memory=None, no_change=False):
    """Persist each forecast block BEFORE requesting its own feedback.

    Axis e = case*6 + lexicographic-ID-view. Forecast blocks contain all cases
    in this fixed order; subsequent case records reference those exact blocks.
    This is cooperative causal ordering on public arrays, not secure custody.
    """
    from .joint_objective import fingerprint
    batch.validate()
    steps, episodes = batch.actions.shape[:2]
    before = batch.digest()
    weights = _freeze_model(model) if model is not None else None
    table_hash = memory.digest() if memory is not None else None
    if model is not None:
        model.eval()
        state = model.initial(episodes)
    raw_all, norm_all, offsets, answers = [], [], [], []
    past = [() for _ in range(episodes)]
    for t in range(steps):
        pre = batch.observations[t].clone()
        action = batch.actions[t].clone()
        answered = np.ones(episodes, dtype=bool)
        with torch.inference_mode():
            if model is not None:
                raw, pending = model.predict(pre, action, state)
                # Cloning prevents receive() changing a saved prediction by alias.
                raw = raw.detach().clone()
            else:
                raw = torch.full((episodes, 8), -torch.inf, dtype=torch.float64)
                for e, (bits, event) in enumerate(zip(pre.long().tolist(), action.tolist(), strict=True)):
                    if no_change:
                        raw[e, bits[0] * 4 + bits[1] * 2 + bits[2]] = 0.
                    else:
                        p = memory.predict(tuple(bits), tuple(event), past[e])
                        if p is None:
                            answered[e] = False
                        else:
                            s.require(len(p) == 8 and all(type(x) in (int, float) and
                                      np.isfinite(x) and 0 <= x <= 1 for x in p) and
                                      abs(sum(p) - 1) <= 1e-12, 'invalid empirical probabilities')
                            raw[e] = torch.tensor(p, dtype=torch.float64).log()
        # Raw record is retained even if normalization or the shape check fails.
        emit(stream, {'kind': 'raw_forecast', 'step': t, 'shape': list(raw.shape),
                      'answered': answered.tolist(), 'raw_log': _array_record(raw)})
        normalized, correction = s.normalize(raw, answered)
        emit(stream, {'kind': 'normalized_forecast', 'step': t,
                      'normalized_log': s.log_record(normalized), 'subtracted_log_mass': correction.tolist()})
        raw_all.append(raw.numpy().copy())
        norm_all.append(normalized)
        offsets.append(correction)
        answers.append(answered)
        # The sole own-feedback access follows the flushed raw/normalized block.
        post = batch.observations[t + 1].clone()
        if model is not None:
            with torch.inference_mode():
                state = model.receive(pending, post)
        else:
            for e, (bits, event, target) in enumerate(zip(pre.long().tolist(), action.tolist(),
                                                        post.long().tolist(), strict=True)):
                past[e] += ((tuple(bits), tuple(event), tuple(target)),)
        s.require(torch.equal(pre, batch.observations[t]) and torch.equal(action, batch.actions[t]) and
                  torch.equal(post, batch.observations[t + 1]), 'callback mutated delivered records')
    s.require(batch.digest() == before, 'replay mutated observations/actions')
    s.require(model is None or fingerprint(model.state_dict()) == weights, 'replay changed weights')
    s.require(memory is None or memory.digest() == table_hash, 'replay changed control table')
    return np.stack(raw_all), np.stack(norm_all), np.stack(answers), np.stack(offsets)


def ambiguous_mask(batch):
    """Evaluator-only grouping from exact preforecast history, after fitting."""
    from .empirical_joint import queries
    groups, keys = defaultdict(set), []
    targets = batch.observations[1:].long().tolist()
    for t, e, pre, action, past in queries(batch):
        key = (t, pre, action, past)
        groups[key].add(tuple(targets[t][e]))
        keys.append((t, e, key))
    result = np.zeros(batch.actions.shape[:2], dtype=bool)
    for t, e, key in keys:
        result[t, e] = len(groups[key]) > 1
    return result


def _load_control(record, folder):
    from .comparison_execution import digest_file
    from .empirical_joint import SensorMemory
    path = folder / record['file']
    s.require(path.parent == folder and digest_file(path) == record['file_sha256'], 'control archive changed')
    data = json.loads(path.read_text())
    def tuples(value):
        return tuple(tuples(x) for x in value) if isinstance(value, list) else value
    memory = SensorMemory(data['mode'])
    for key, entries in data['rows']:
        key = tuples(key)
        s.require(key not in memory.table, 'duplicate control key')
        counts = Counter()
        for world, count in entries:
            world = tuples(world)
            s.require(len(world) == 3 and all(type(x) is int and x in (0, 1) for x in world) and
                      type(count) is int and count > 0 and world not in counts, 'invalid control archive')
            counts[world] = count
        memory.table[key] = counts
    s.require(memory.mode == record['mode'] and memory.digest() == record['table_sha256'] ==
              data['table_sha256'], 'control table fingerprint mismatch')
    return memory


def _sequence(model, observations, actions):
    state = model.initial(actions.shape[1])
    for t, action in enumerate(actions):
        _, pending = model.predict(observations[t], action, state)
        state = model.receive(pending, observations[t + 1])


def latency(model, batch):
    """Frozen procedure: first scored physical case, six views, one warmup + 20."""
    before = _freeze_model(model)
    x, a = batch.observations[:, :6].clone(), batch.actions[:, :6].clone()
    times, cpu = [], []
    with torch.inference_mode():
        _sequence(model, x, a)
        for _ in range(20):
            start, cpu_start = perf_counter(), process_time()
            _sequence(model, x, a)
            cpu.append(process_time() - cpu_start)
            times.append(perf_counter() - start)
    s.require(_freeze_model(model) == before and torch.equal(x, batch.observations[:, :6]) and
              torch.equal(a, batch.actions[:, :6]), 'latency replay mutated model/data')
    return {'batch_size': 6, 'actions_per_sequence': len(a), 'discarded_warmups': 1, 'repeats': 20,
            'wall_seconds': times, 'cpu_seconds': cpu,
            'wall_p50': s.nearest_rank(times, .5), 'wall_p95': s.nearest_rank(times, .95),
            'cpu_p50': s.nearest_rank(cpu, .5), 'cpu_p95': s.nearest_rank(cpu, .95),
            'interpretation': 'batched full-sequence latency, not single-query service latency'}


def evaluate(model, batch, folder, key, ambiguity, *, memory=None, no_change=False, query=6):
    from .comparison_execution import digest_file
    n_cases = batch.actions.shape[1] // 6
    s.require(n_cases * 6 == batch.actions.shape[1], 'incomplete ID-view inventory')
    path = folder / (key + '.jsonl.gz')
    with path.open('xb') as binary, gzip.open(binary, 'wt', encoding='utf-8') as stream:
        emit(stream, {'kind': 'header', 'key': key, 'cases': n_cases, 'views': 6,
                      'view_mappings': s.PERMUTATIONS, 'worlds': s.WORLDS.tolist(),
                      'episode_index': '6*case+view; raw blocks indexed [episode][world]',
                      'status': 'PUBLIC_DIAGNOSTIC_NOT_G1'})
        raw, normalized, answered, offsets = replay(model, batch, stream, memory=memory, no_change=no_change)
        # Scoring/truth use begins only after all forecasts for this evaluation.
        truth = batch.observations[1:].long().numpy()
        pre = batch.observations[:-1].long().numpy()
        scores = s.score(normalized, answered, truth, pre, raw)
        renaming, tv, map_change = s.renaming(normalized, answered, n_cases)
        codes = np.where(answered, scores['correct'].astype(np.uint8), 2)
        for case in range(n_cases):
            rows = slice(case * 6, (case + 1) * 6)
            log_nll = scores['nll'][:, rows]
            numeric = np.where(answered[:, rows] & np.isfinite(log_nll), log_nll, None)
            emit(stream, {'kind': 'case_scores', 'case': case, 'states': batch.observations[:, rows].tolist(),
                          'actions': batch.actions[:, rows].tolist(), 'answered': answered[:, rows].tolist(),
                          'codes': codes[:, rows].tolist(), 'map': scores['map'][:, rows].tolist(),
                          'maximizers': scores['maximizers'][:, rows].tolist(),
                          'nll': numeric.tolist(),
                          'nll_status': np.where(~answered[:, rows], 'abstained',
                                         np.where(np.isfinite(log_nll), 'finite', 'infinite')).tolist(),
                          'brier': np.where(answered[:, rows], scores['brier'][:, rows], None).tolist(),
                          'confidence': np.where(answered[:, rows], scores['confidence'][:, rows], None).tolist(),
                          'underflow_world_count': scores['underflow'][:, rows].tolist(),
                          'unchanged_bit_errors': scores['unchanged_bit_errors'][:, rows].tolist(),
                          'ambiguous': ambiguity[:, rows].tolist(),
                          'renaming_tv': np.where(np.isfinite(tv[:, case]), tv[:, case], None).tolist(),
                          'renaming_map_changed': map_change[:, case].tolist(),
                          'normalization_map_changed': scores['map_changed'][:, rows].tolist(),
                          'normalization_maximizers_changed': scores['maximizers_changed'][:, rows].tolist()})
        report = {'key': key, 'steps': [{'step': t, **s.summary(s.subset(scores, t)),
                   'ambiguous_subset': s.summary(s.subset(scores, t), ambiguity[t])} for t in range(len(raw))],
                  'all_steps': s.summary(scores),
                  'all_steps_correct_with_feedback': int(scores['correct'].all(0).sum()),
                  'complete_episode_views': n_cases * 6,
                  'reverse_role_pairs': s.role_pairs(codes, query, n_cases),
                  'renaming': renaming, 'max_abs_log_correction': float(np.abs(offsets).max()),
                  'file': path.name}
        emit(stream, {'kind': 'evaluation_summary', **report})
    report['file_sha256'] = digest_file(path)
    return report, codes


def _paired_reports(cache, spec, stream):
    conditions = spec['data']['conditions']
    regimes = [x['id'] for x in spec['fit']['regimes']]
    models = [x['id'] for x in spec['models']]
    controls = spec['controls']
    count = 0
    def output(kind, before_key, after_key):
        nonlocal count
        before, after = cache[before_key], cache[after_key]
        for step in range(len(before)):
            emit(stream, {'kind': kind, 'before': before_key, 'after': after_key, 'step': step,
                          'id_decode': 'case = id//6; view = id%6', **s.paired(before[step], after[step])})
            count += 1
    for regime in regimes:
        for condition in conditions:
            for seed in spec['seeds']:
                for fixture in spec['data']['evaluation']:
                    prefix = (regime, condition, seed, fixture)
                    for model in models + controls:
                        for reference in ('flat', 'kernel_learned_persistence'):
                            if model != reference:
                                output('arm_vs_reference', (*prefix, reference), (*prefix, model))
    for regime in regimes:
        for seed in spec['seeds']:
            for fixture in spec['data']['evaluation']:
                for model in models + controls:
                    output('information_condition', (regime, conditions[0], seed, fixture, model),
                           (regime, conditions[1], seed, fixture, model))
    for condition in conditions:
        for seed in spec['seeds']:
            for fixture in spec['data']['evaluation']:
                for model in models + controls:
                    output('resource_regime', (regimes[0], condition, seed, fixture, model),
                           (regimes[1], condition, seed, fixture, model))
    for regime in regimes:
        for condition in conditions:
            for seed in spec['seeds']:
                for model in models + controls:
                    output('fixture_transfer', (regime, condition, seed, 'same_pair', model),
                           (regime, condition, seed, 'second_pair', model))
    return count


def _decision_table(results, query):
    groups = defaultdict(list)
    for record in results:
        if record['type'] == 'neural':
            task = record['task']
            groups[(task['regime'], task['condition'], record['fixture'], task['model'])].append(record)
    rows = []
    for key, group in sorted(groups.items()):
        scores = [r['steps'][query] for r in group]
        rows.append({'regime': key[0], 'condition': key[1], 'fixture': key[2], 'model': key[3],
                     'seeds': [r['task']['seed'] for r in group],
                     'query_correct_counts': [s['correct'] for s in scores],
                     'query_denominator_per_seed': scores[0]['queries'],
                     'query_accuracy_mean': float(np.mean([x['correct_per_query'] for x in scores])),
                     'query_accuracy_worst_seed': min(x['correct_per_query'] for x in scores),
                     'query_nll_per_seed': [x['mean_nll'] for x in scores],
                     'query_nll_status': [x['nll_status'] for x in scores],
                     'query_brier_per_seed': [x['mean_brier'] for x in scores]})
    return rows


def execute(spec, batches, output, provenance):
    """Complete pipeline; caller supplies frozen verification and fresh output."""
    from . import comparison_execution as stage
    from .informative_curriculum import model_factories
    phase, current = 'fit', None
    started, cpu_started = perf_counter(), process_time()
    try:
        training = {c: batches[c + '_same_pair'] for c in spec['data']['conditions']}
        fits = stage._fit_phase(spec, training, output / 'fits')
        s.require(len(fits['fits']) == spec['fit']['total_neural_fits'], 'incomplete fit phase')
        stage.write_json(output / 'provenance.json', provenance)
        phase = 'replay'
        records_dir = output / 'records'
        records_dir.mkdir()
        results, cache, latency_results = [], {}, []
        ambiguities = {k: ambiguous_mask(v) for k, v in batches.items()}
        factories = model_factories()
        for fit in fits['fits']:
            task = fit['task']
            current = task
            folder = output / 'fits' / f"fit-{task['ordinal']:03d}"
            model = stage._restore(factories[task['model']], folder / 'final.pt', fit['final'])
            for fixture in spec['data']['evaluation']:
                current = {**task, 'fixture': fixture}
                name = task['condition'] + '_' + fixture
                result, codes = evaluate(model, batches[name], records_dir,
                    f"fit-{task['ordinal']:03d}-{fixture}", ambiguities[name], query=spec['data']['query_step'])
                s.require(bool((codes != 2).all()), 'neural forecast abstained')
                results.append({'type': 'neural', 'task': task, 'fixture': fixture, **result})
                cache[(task['regime'], task['condition'], task['seed'], fixture, task['model'])] = codes
            latency_results.append({'ordinal': task['ordinal'], **latency(model, training[task['condition']])})
            print(json.dumps({'phase': 'replay', 'fit': task['ordinal'], 'completed': True}), flush=True)
        phase, current = 'controls', None
        controls = {(r['condition'], r['mode']): _load_control(r, output / 'fits') for r in fits['controls']}
        for condition in spec['data']['conditions']:
            for control in spec['controls']:
                for fixture in spec['data']['evaluation']:
                    current = {'condition': condition, 'control': control, 'fixture': fixture}
                    name = condition + '_' + fixture
                    result, codes = evaluate(None, batches[name], records_dir,
                        f'{condition}-{control}-{fixture}', ambiguities[name],
                        memory=controls.get((condition, control)), no_change=control == 'no_change',
                        query=spec['data']['query_step'])
                    results.append({'type': 'control', **current, **result})
                    # Static control scores reused descriptively, not new independent samples.
                    for regime in spec['fit']['regimes']:
                        for seed in spec['seeds']:
                            cache[(regime['id'], condition, seed, fixture, control)] = codes
        phase, current = 'summary', None
        with (output / 'paired.jsonl.gz').open('xb') as binary, gzip.open(binary, 'wt', encoding='utf-8') as stream:
            paired_count = _paired_reports(cache, spec, stream)
        expected_results = 2 * spec['fit']['total_neural_fits'] + 2 * len(spec['data']['conditions']) * len(spec['controls'])
        s.require(len(results) == expected_results and len(cache) ==
                  len(spec['seeds']) * len(spec['fit']['regimes']) * len(spec['data']['conditions']) *
                  len(spec['data']['evaluation']) * (len(spec['models']) + len(spec['controls'])), 'evaluation inventory mismatch')
        for result in results:
            s.require(len(result['steps']) == spec['data']['actions_per_history'] and
                      all(x['queries'] == spec['data']['views_per_dataset'] for x in result['steps']), 'score denominator mismatch')
            s.require(stage.digest_file(records_dir / result['file']) == result['file_sha256'], 'record archive changed')
        report = {'status': 'COMPLETE_OPEN_PUBLIC_DIAGNOSTIC_NOT_G1', 'gate_g1': 'HOLD_REVISE',
                  'protocol_sha256': stage.PROTOCOL_SHA256, 'provenance': provenance,
                  'fits': fits, 'results': results, 'latency': latency_results,
                  'decision_table': _decision_table(results, spec['data']['query_step']),
                  'paired_records': paired_count, 'paired_sha256': stage.digest_file(output / 'paired.jsonl.gz'),
                  'neural_forecast_count': spec['fit']['total_neural_fits'] * 2 *
                      spec['data']['views_per_dataset'] * spec['data']['actions_per_history'],
                  'wall_seconds': perf_counter() - started, 'cpu_seconds': process_time() - cpu_started,
                  'environment': {**stage.environment(), 'numpy': np.__version__},
                  'limits': ['Opened public data; same-pair resubstitution; familiar local contexts.',
                             'No independent challenge, matched capacity or learned acquisition.',
                             'Equal ceilings are not equal consumed compute. Historical failures remain unchanged.']}
        phase = 'publication'
        digest = stage.write_json(output / 'report.json', report)
        with (output / 'COMPLETE').open('x') as marker:
            marker.write(digest + '\n')
            marker.flush()
            os.fsync(marker.fileno())
        return report
    except BaseException as exc:
        (output / 'COMPLETE').unlink(missing_ok=True)
        (output / 'report.json').unlink(missing_ok=True)
        try:
            stage.write_json(output / 'FAILED.json', {'status': 'INCOMPLETE', 'phase': phase,
                'current': current, 'type': type(exc).__name__, 'error': str(exc), 'gate_g1': 'HOLD_REVISE',
                'note': 'No retry or continuation permitted. Retain every available file.'})
        except OSError:
            pass
        raise


def run(output_dir):
    """Guarded CI invocation, on a separately committed, reviewed source state."""
    from . import comparison_execution as stage
    s.require(os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('GITHUB_RUN_ATTEMPT') == '1',
              'only the one-attempt guarded workflow may run the frozen study')
    approved = os.environ.get('CEMM_REVIEWED_RUNNER', '')
    s.require(len(approved) == 40, 'missing reviewed runner commit')
    output = Path(output_dir)
    s.require(not output.is_symlink() and not output.resolve().is_relative_to(stage.ROOT), 'invalid output location')
    output.mkdir(exist_ok=False, parents=False)
    try:
        spec = stage.read_protocol()
        lineage = stage.lineage(spec)
        for name in ('comparison_run.py', 'comparison_scoring.py'):
            path = Path(__file__).with_name(name)
            relative = str(path.relative_to(stage.ROOT))
            committed = subprocess.run(['git', '-C', str(stage.ROOT), 'show', f'{approved}:{relative}'],
                                       check=True, capture_output=True).stdout
            s.require(committed == path.read_bytes(), 'reviewed runner bytes changed')
        host = stage.configure_runtime()
        batches = stage.prepare_batches(spec)
        provenance = {'lineage': lineage, 'reviewed_runner_commit': approved, 'environment': host,
                      'source_sha256': {name: stage.digest_file(Path(__file__).with_name(name))
                                        for name in ('comparison_run.py', 'comparison_scoring.py')},
                      'data_sha256': {key: value.digest() for key, value in batches.items()},
                      'run_id': os.environ.get('GITHUB_RUN_ID')}
        stage.write_json(output / 'STARTED.json', provenance)
        return execute(spec, batches, output, provenance)
    except BaseException as exc:
        if not (output / 'FAILED.json').exists():
            stage.write_json(output / 'FAILED.json', {'status': 'INCOMPLETE', 'phase': 'preflight',
                'type': type(exc).__name__, 'error': str(exc), 'gate_g1': 'HOLD_REVISE'})
        raise


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    args = parser.parse_args()
    report = run(args.output_dir)
    print(json.dumps({'status': report['status'], 'decision_table': report['decision_table']}, allow_nan=False))
