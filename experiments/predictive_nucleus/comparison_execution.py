"""Frozen comparison preflight and fit/checkpoint phase; no study entrypoint.

The public CLI only verifies inputs and prints the fit plan. Replay, scoring,
publication and the one-attempt workflow are deliberately NOT enabled here.
Internal phase helpers are exercised with synthetic data, not public fits.
"""
from collections import Counter
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import platform
import re
import resource
import subprocess
from time import perf_counter, process_time

import torch

from . import joint_objective as joint
from .empirical_joint import SensorMemory
from .informative_curriculum import model_factories

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).resolve().parent
PROTOCOL = 'common_objective_comparison_protocol_v1.json'
PROTOCOL_SHA256 = '15732afe065f19f3b412a7638e386373eb586ddaa273104e2de63c14a782b1f3'
PROTOCOL_COMMIT = '2eeae6323d8123da5ded40a56e77ef68e6aac5ac'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest_file(path):
    with Path(path).open('rb') as stream:
        return sha256(stream.read()).hexdigest()


def diagnostic_json(value):
    """Lossless nonfinite tags for failed metadata; never an accepted metric."""
    if type(value) is float and not math.isfinite(value):
        return {'value': None, 'status': 'nan' if math.isnan(value) else
                ('positive_infinity' if value > 0 else 'negative_infinity')}
    if isinstance(value, dict):
        return {key: diagnostic_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [diagnostic_json(item) for item in value]
    return value


def write_json(path, value):
    """Serialize first, create exclusively, flush; never replace old evidence."""
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    return sha256(raw).hexdigest()


def read_protocol():
    path = SOURCE / PROTOCOL
    require(digest_file(path) == PROTOCOL_SHA256, 'protocol hash mismatch')
    spec = json.loads(path.read_text())
    for name, expected in spec['source_sha256'].items():
        relative = Path(name)
        require(not relative.is_absolute() and '..' not in relative.parts, 'unsafe source path')
        target = SOURCE / relative
        require(target.resolve().is_relative_to(SOURCE.resolve()) and
                not target.is_symlink() and digest_file(target) == expected, f'source hash mismatch: {name}')
    require(spec['status'] == 'FROZEN_PUBLIC_DIAGNOSTIC_NOT_RUN' and
            spec['gate_g1'] == 'HOLD_REVISE', 'unexpected protocol status')
    return spec


def fit_plan(spec):
    """Exact rotation and inventory, without constructing or training a model."""
    models = [item['id'] for item in spec['models']]
    conditions, seeds = spec['data']['conditions'], spec['seeds']
    regimes = spec['fit']['regimes']
    for values in (models, conditions, [regime['id'] for regime in regimes]):
        require(values and len(set(values)) == len(values) and
                all(type(v) is str and re.fullmatch('[a-z][a-z0-9_]*', v) for v in values),
                'invalid or duplicate plan identifiers')
    require(seeds and all(type(seed) is int and seed >= 0 for seed in seeds) and
            len(set(seeds)) == len(seeds), 'invalid or duplicate seeds')
    result = []
    for r, regime in enumerate(regimes):
        for c, condition in enumerate(conditions):
            for s, seed in enumerate(seeds):
                offset = (r + c + s) % len(models)
                for model in models[offset:] + models[:offset]:
                    result.append({'ordinal': len(result), 'regime': regime['id'],
                                   'condition': condition, 'seed': seed, 'model': model,
                                   'updates': regime['updates'], 'cpu_seconds': regime['cpu_seconds']})
    require(len(result) == spec['fit']['total_neural_fits'], 'fit inventory mismatch')
    return result


def lineage(spec):
    def git(*args):
        return subprocess.run(['git', '-C', str(ROOT), *args], check=True,
                              capture_output=True, text=True).stdout.strip()
    def ancestor(a, b):
        return subprocess.run(['git', '-C', str(ROOT), 'merge-base', '--is-ancestor', a, b],
                              capture_output=True).returncode == 0
    require(Path(git('rev-parse', '--show-toplevel')).resolve() == ROOT, 'wrong checkout root')
    require(git('rev-parse', '--is-shallow-repository') == 'false', 'complete history required')
    sparse = subprocess.run(['git', '-C', str(ROOT), 'config', '--bool', 'core.sparseCheckout'],
                            capture_output=True, text=True)
    require(sparse.returncode in (0, 1) and sparse.stdout.strip() != 'true', 'sparse checkout forbidden')
    require(not git('diff', '--name-only', 'HEAD') and not git('ls-files', '--deleted'), 'dirty tracked tree')
    require(all((ROOT / name).is_file() for name in git('ls-files', '-z').split('\x00') if name),
            'incomplete tracked checkout')
    require(ancestor(spec['source_commit'], PROTOCOL_COMMIT) and ancestor(PROTOCOL_COMMIT, 'HEAD'),
            'frozen source/protocol ancestry mismatch')
    protocol_path = str((SOURCE / PROTOCOL).relative_to(ROOT))
    require(git('log', '-1', '--format=%H', '--', protocol_path) == PROTOCOL_COMMIT,
            'protocol was changed after freeze')
    runner_path = str(Path(__file__).resolve().relative_to(ROOT))
    runner_commit = git('log', '-1', '--format=%H', '--', runner_path)
    require(runner_commit and runner_commit != PROTOCOL_COMMIT and ancestor(PROTOCOL_COMMIT, runner_commit),
            'runner must be committed after protocol')
    paths = [SOURCE / name for name in spec['source_sha256']] + [SOURCE / PROTOCOL, Path(__file__).resolve()]
    for path in paths:
        relative = str(path.relative_to(ROOT))
        committed = subprocess.run(['git', '-C', str(ROOT), 'show', f'HEAD:{relative}'], capture_output=True)
        require(committed.returncode == 0 and committed.stdout == path.read_bytes(), f'uncommitted source: {relative}')
    return {'execution_commit': git('rev-parse', 'HEAD'), 'protocol_commit': PROTOCOL_COMMIT,
            'source_commit': spec['source_commit'], 'runner_commit': runner_commit,
            'runner_sha256': digest_file(__file__),
            'untracked_present': bool(git('ls-files', '--others', '--exclude-standard')),
            'tracked_tree_clean': True, 'complete_history': True}


def configure_runtime():
    """Fresh-process setup only: inter-op settings cannot be safely restored."""
    require(platform.python_version().startswith('3.13.') and torch.__version__ == '2.10.0+cpu',
            'requires Python 3.13 and PyTorch 2.10.0+cpu')
    require(os.environ.get('PYTHONHASHSEED') == '0', 'PYTHONHASHSEED=0 required at process startup')
    require(torch.version.cuda is None and torch.version.hip is None and
            not (hasattr(torch.backends, 'mps') and torch.backends.mps.is_available()) and
            not (hasattr(torch, 'xpu') and torch.xpu.is_available()) and
            str(torch.get_default_device()) == 'cpu', 'CPU-only runtime required')
    if torch.get_num_interop_threads() != 1:
        torch.set_num_interop_threads(1)  # Must happen before any inter-op work.
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True, warn_only=False)
    return environment()


def environment():
    try:
        cpu = next(line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines()
                   if line.lower().startswith('model name'))
    except (OSError, StopIteration):
        cpu = platform.processor() or 'unknown'
    return {'python': platform.python_version(), 'torch': str(torch.__version__), 'platform': platform.platform(),
            'cpu_model': cpu, 'torch_config_sha256': sha256(torch.__config__.show().encode()).hexdigest(),
            'intraop_threads': torch.get_num_threads(), 'interop_threads': torch.get_num_interop_threads(),
            'deterministic_algorithms': torch.are_deterministic_algorithms_enabled(),
            'deterministic_warn_only': torch.is_deterministic_algorithms_warn_only_enabled(),
            'default_dtype': str(torch.get_default_dtype()),
            'peak_rss': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'peak_rss_unit': 'KiB' if platform.system() == 'Linux' else
                             ('bytes' if platform.system() == 'Darwin' else 'platform-dependent')}


def prepare_batches(spec):
    """Build/hash all four opened datasets; do not fit or score any model."""
    from .comparison_data import histories
    result = {}
    for condition in spec['data']['conditions']:
        for fixture in spec['data']['evaluation']:
            name = f'{condition}_{fixture}'
            batch = joint.batch_histories(histories(informative=condition == 'informative',
                                                    composition=fixture == 'second_pair'))
            require(batch.digest() == spec['data']['input_sha256'][name], f'dataset hash mismatch: {name}')
            require(tuple(batch.actions.shape[:2]) == (spec['data']['actions_per_history'],
                    spec['data']['views_per_dataset']), 'dataset inventory mismatch')
            result[name] = batch
    return result


def _state(model):
    return {name: tensor.detach().cpu().clone().contiguous() for name, tensor in model.state_dict().items()}


def _restore(factory, path, metadata):
    """Verify before loading; strict loading alone allows silent dtype casts."""
    require(digest_file(path) == metadata['file_sha256'], 'checkpoint byte hash mismatch')
    tensors = torch.load(path, map_location='cpu', weights_only=True)
    require(type(tensors) is dict and all(type(k) is str and type(v) is torch.Tensor
                                        for k, v in tensors.items()), 'checkpoint must contain plain tensors')
    require(joint.fingerprint(tensors) == metadata['tensor_sha256'], 'checkpoint tensor hash mismatch')
    with torch.random.fork_rng(devices=[]):
        model = factory()
    expected = model.state_dict()
    require(set(expected) == set(tensors), 'checkpoint key mismatch')
    for name, tensor in tensors.items():
        require(tensor.device.type == 'cpu' and tensor.layout == torch.strided and
                tensor.dtype == expected[name].dtype and tensor.shape == expected[name].shape and
                bool(torch.isfinite(tensor).all()), f'invalid checkpoint tensor: {name}')
    model.load_state_dict(tensors, strict=True)
    require(joint.fingerprint(model.state_dict()) == metadata['tensor_sha256'], 'restored fingerprint mismatch')
    return model


def _save_state(model, path, factory=None):
    tensors = _state(model)
    with Path(path).open('xb') as stream:
        torch.save(tensors, stream)
        stream.flush()
        os.fsync(stream.fileno())
    metadata = {'file': Path(path).name, 'file_sha256': digest_file(path),
                'tensor_sha256': joint.fingerprint(tensors)}
    # Failed partial states may be nonfinite. Retain them without admitting them.
    if factory is not None:
        _restore(factory, path, metadata)
    return metadata


def _save_control(control, path):
    rows = [[key, sorted(counts.items())] for key, counts in sorted(control.table.items())]
    value = {'mode': control.mode, 'table_sha256': control.digest(), 'rows': rows}
    file_hash = write_json(path, value)
    def tuples(value):
        return tuple(map(tuples, value)) if isinstance(value, list) else value
    saved = json.loads(Path(path).read_text())
    restored = SensorMemory(saved['mode'])
    for key, entries in saved['rows']:
        key = tuples(key)
        require(key not in restored.table, 'duplicate control key')
        counts = Counter()
        for world, count in entries:
            world = tuples(world)
            require(len(world) == 3 and all(type(bit) is int and bit in (0, 1) for bit in world) and
                    type(count) is int and count > 0 and world not in counts, 'invalid control count')
            counts[world] = count
        restored.table[key] = counts
    require(restored.digest() == control.digest() == saved['table_sha256'], 'control round-trip mismatch')
    return {'file': Path(path).name, 'file_sha256': file_hash, 'table_sha256': control.digest(),
            'keys': len(control.table), 'measured_events': sum(sum(c.values()) for c in control.table.values())}


def _validate_fit(meta, task, initial, final, data_hash, events, parameters):
    for name in ('setup_wall_seconds', 'fit_wall_seconds', 'fit_cpu_seconds', 'cpu_ceiling_seconds',
                 'cpu_overshoot_seconds', 'last_step_cpu_seconds', 'last_preupdate_nll'):
        require(type(meta.get(name)) in (int, float) and math.isfinite(meta[name]), f'invalid fit metric: {name}')
        if name != 'last_preupdate_nll':
            require(meta[name] >= 0, f'negative fit cost: {name}')
    for name in ('requested_updates', 'parameters', 'events_per_update'):
        require(type(meta.get(name)) is int, f'invalid integer fit metric: {name}')
    done = meta.get('completed_updates')
    require(type(done) is int and 0 < done <= task['updates'], 'invalid completed update count')
    require(meta['requested_updates'] == task['updates'] and meta['parameters'] == parameters and
            meta['cpu_ceiling_seconds'] == task['cpu_seconds'] and meta['events_per_update'] == events and
            meta['training_input_sha256'] == data_hash and
            meta['initial_weights_sha256'] == initial['tensor_sha256'] and
            meta['final_weights_sha256'] == final['tensor_sha256'], 'fit metadata mismatch')
    expected_stop = 'update_limit' if done == task['updates'] else 'cpu_limit'
    require(meta['stop_reason'] == expected_stop, 'fit stop reason mismatch')
    require(meta['cpu_overshoot_seconds'] == max(0.0, meta['fit_cpu_seconds'] - task['cpu_seconds']),
            'fit overshoot mismatch')
    if expected_stop == 'cpu_limit':
        require(meta['fit_cpu_seconds'] >= task['cpu_seconds'], 'CPU stop before budget')
    if task['regime'] == 'fixed_exposure':
        require(done == task['updates'], 'incomplete fixed-exposure fit')


def _fit_phase(spec, training, output_dir):
    """Internal phase only. Never called by CLI/CI on public data in this tranche.

    Caller must run frozen preflight and fresh-process configuration first.
    This helper has NO success/COMPLETE publication or continuation/retry mode.
    Synthetic tests patch the fitter, not the frozen protocol or old results.
    """
    plan = fit_plan(spec)
    require(set(training) == set(spec['data']['conditions']), 'training-only condition mapping required')
    for condition, batch in training.items():
        batch.validate()
        require(batch.digest() == spec['data']['input_sha256'][f'{condition}_same_pair'], 'training hash mismatch')
    require(not Path(output_dir).is_symlink(), 'output cannot be a symlink')
    output = Path(output_dir).resolve()
    require(not output.is_relative_to(ROOT.resolve()), 'output must be outside source checkout')
    output.mkdir(parents=False, exist_ok=False)
    started, cpu_started = perf_counter(), process_time()
    completed, controls, initial_hashes = [], [], {}
    phase, current, model, task_dir = 'setup', None, None, None
    try:
        factories = model_factories()
        require([m['id'] for m in spec['models']] == list(factories), 'factory inventory mismatch')
        parameters = {m['id']: m['parameters'] for m in spec['models']}
        write_json(output / 'plan.json', {'status': 'FIT_PHASE_STARTED_NOT_EVALUATED', 'plan': plan,
                                        'gate_g1': 'HOLD_REVISE', 'environment': environment()})
        with torch.random.fork_rng(devices=[]):
            for current in plan:
                model = None
                phase = 'initialization'
                task_dir = output / f"fit-{current['ordinal']:03d}"
                task_dir.mkdir()
                write_json(task_dir / 'task.json', current)
                factory = factories[current['model']]
                torch.manual_seed(current['seed'])
                model = factory()
                require(sum(p.numel() for p in model.parameters()) == parameters[current['model']], 'parameter count mismatch')
                initial = _save_state(model, task_dir / 'initial.pt', factory)
                write_json(task_dir / 'initial.json', initial)
                key = (current['model'], current['seed'])
                require(initial_hashes.setdefault(key, initial['tensor_sha256']) == initial['tensor_sha256'],
                        'initial weights differ between conditions/regimes')
                source = training[current['condition']]
                data_hash = source.digest()
                batch = joint.SensorBatch(source.observations.clone(), source.actions.clone())
                phase = 'fit'
                metadata = joint.fit(model, batch, updates=current['updates'], cpu_seconds=current['cpu_seconds'])
                phase = 'checkpoint'
                final = _save_state(model, task_dir / 'final.pt', factory)
                # Retain raw returned metadata before rejecting an incomplete fit.
                write_json(task_dir / 'returned_fit.json', diagnostic_json(metadata))
                write_json(task_dir / 'final.json', final)
                require(source.digest() == batch.digest() == data_hash, 'fit mutated sensor/action data')
                _validate_fit(metadata, current, initial, final, data_hash,
                              spec['data']['event_targets_per_update'], parameters[current['model']])
                record = {'task': current, 'initial': initial, 'final': final, 'fit': metadata,
                          'events_processed': metadata['completed_updates'] * metadata['events_per_update']}
                write_json(task_dir / 'VERIFIED.json', record)
                completed.append(record)
            current, model, task_dir = None, None, None
            phase = 'controls'
            require(spec['controls'] == ['no_change', 'prefix', 'local', 'contact'], 'control inventory mismatch')
            for condition, batch in training.items():
                before = batch.digest()
                for mode in spec['controls'][1:]:
                    control = SensorMemory(mode).fit(batch)
                    record = _save_control(control, output / f'{condition}-{mode}.json')
                    require(record['measured_events'] == spec['data']['event_targets_per_update'], 'control event count mismatch')
                    controls.append({'condition': condition, 'mode': mode, **record})
                require(batch.digest() == before, 'control fit mutated observations')
            phase = 'verification'
            require([row['task'] for row in completed] == plan and
                    len(controls) == 3 * len(training), 'incomplete fit/control inventory')
            for row in completed:
                folder = output / f"fit-{row['task']['ordinal']:03d}"
                for stage in ('initial', 'final'):
                    _restore(factories[row['task']['model']], folder / row[stage]['file'], row[stage])
            for record in controls:
                require(digest_file(output / record['file']) == record['file_sha256'], 'changed control archive')
            report = {'status': 'FITS_VERIFIED_NOT_EVALUATED', 'gate_g1': 'HOLD_REVISE',
                      'study_complete': False, 'fits': completed, 'controls': controls,
                      'wall_seconds': perf_counter() - started, 'cpu_seconds': process_time() - cpu_started,
                      'environment': environment()}
            write_json(output / 'FIT_PHASE.json', report)
            return report
    except BaseException as exc:
        failure = {'status': 'INCOMPLETE', 'phase': phase, 'type': type(exc).__name__, 'error': str(exc),
                   'current_task': current, 'verified_ordinals': [r['task']['ordinal'] for r in completed],
                   'missing_ordinals': [t['ordinal'] for t in plan[len(completed):]],
                   'study_complete': False, 'gate_g1': 'HOLD_REVISE'}
        if model is not None and task_dir is not None:
            try:
                failure['failed_partial_state'] = _save_state(model, task_dir / 'FAILED-partial.pt')
                failure['failed_partial_state']['usable_as_completed_fit'] = False
            except BaseException as retention_error:
                failure['partial_state_retention_error'] = str(retention_error)
        try:
            (output / 'FIT_PHASE.json').unlink(missing_ok=True)
            write_json(output / 'FAILED.json', failure)
        except OSError:
            pass  # Earlier evidence stays in place even when the filesystem fails.
        raise


def preflight():
    """Verify lineage/data/inventory only; zero optimization or prediction calls."""
    spec = read_protocol()
    origin = lineage(spec)
    host = configure_runtime()
    batches = prepare_batches(spec)
    return {'status': 'PREFLIGHT_ONLY_NO_FITS_OR_SCORES', 'gate_g1': 'HOLD_REVISE',
            'protocol_sha256': PROTOCOL_SHA256, 'lineage': origin, 'environment': host,
            'data_sha256': {name: batch.digest() for name, batch in batches.items()},
            'fit_plan': fit_plan(spec), 'study_execution_enabled': False}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preflight', action='store_true', required=True)
    parser.parse_args()
    print(json.dumps(preflight(), indent=2, sort_keys=True, allow_nan=False))
