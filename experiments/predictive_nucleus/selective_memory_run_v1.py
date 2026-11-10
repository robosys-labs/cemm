"""Publish-separated execution of the frozen selective-memory experiment.

The fit stage parses TRAIN only; other artifacts are read solely for hash checks.
Collection opens public TEST observations only
after every fitted checkpoint is committed; the scorer alone opens private gold.
"""
import argparse
from hashlib import sha256
import json
import lzma
from pathlib import Path
import platform
import resource
import shutil
import subprocess
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
VERSION = 'selective-memory-v1'
BRANCH = 'research/g5-selective-memory-v1'
PROTOCOL_COMMIT = '6e4aa1b737f4ce36d8608a8adea73e1420eaff42'
SEEDS = (7, 11, 23, 37, 53)
ARMS = ('selective', 'native', 'flat')
SOURCES = ('SELECTIVE_MEMORY_PROTOCOL_V1.md', 'selective_memory_run_v1.py',
           'selective_memory_data_v1.py', 'selective_memory_models_v1.py',
           'selective_memory_score_v1.py', 'temporal_native_models_v1.py',
           'temporal_observability_v1.py', 'bilingual_data.py',
           'effect_role_data.py', 'set_acquisition_data.py',
           'multisource_law_oracle.py', 'physical_query_v1.py',
           'tests/test_selective_memory_data_v1.py',
           'tests/test_selective_memory_models_v1.py',
           'tests/test_selective_memory_score_v1.py')


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'),
                       allow_nan=False) + '\n').encode()


def digest(value):
    return sha256(encoded(value)).hexdigest()


def file_hash(path):
    with Path(path).open('rb') as handle:
        return __import__('hashlib').file_digest(handle, 'sha256').hexdigest()


def write(path, value):
    data = encoded(value)
    Path(path).write_bytes(lzma.compress(data) if str(path).endswith('.xz') else data)


def read(path):
    opener = lzma.open if str(path).endswith('.xz') else open
    with opener(path, 'rt', encoding='utf-8') as handle:
        return json.load(handle)


def inventory(directory):
    return {p.name: {'sha256': file_hash(p), 'bytes': p.stat().st_size}
            for p in sorted(directory.iterdir()) if p.is_file() and p.name != 'manifest.json'}


def verify(directory):
    manifest = read(directory / 'manifest.json')
    for name, item in manifest['artifacts'].items():
        if Path(name).name != name or file_hash(directory / name) != item['sha256']:
            raise ValueError('artifact changed: ' + name)
    return manifest


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO)


def committed(paths):
    """Require exact published bytes, including data/fit/raw stage boundaries."""
    for path in paths:
        relative = str(Path(path).resolve().relative_to(REPO))
        if sha256(git('show', 'HEAD:' + relative)).hexdigest() != file_hash(path):
            raise ValueError('uncommitted artifact: ' + relative)


def source():
    import numpy as np
    import torch
    commit = git('rev-parse', 'HEAD').decode().strip()
    subprocess.run(['git', 'merge-base', '--is-ancestor', PROTOCOL_COMMIT, commit],
                   cwd=REPO, check=True)
    remote = git('ls-remote', '--heads', 'origin', 'refs/heads/' + BRANCH).decode().split()
    if not remote or remote[0] != commit:
        raise ValueError('publish the exact execution commit before running')
    committed([ROOT / name for name in SOURCES])
    if torch.__version__.split('+')[0] != '2.10.0' or np.__version__ != '2.3.5':
        raise ValueError('frozen numerical versions required')
    return {'source_commit': commit, 'protocol_commit': PROTOCOL_COMMIT,
            'source_sha256': {name: file_hash(ROOT / name) for name in SOURCES},
            'python': platform.python_version(), 'torch': torch.__version__,
            'numpy': np.__version__}


def frozen(manifest, stamp):
    if manifest['source_sha256'] != stamp['source_sha256']:
        raise ValueError('source changed after preparation')


def receipt(start, **extra):
    return {'wall_seconds': time.perf_counter() - start[0],
            'cpu_seconds': time.process_time() - start[1],
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            **extra}


def prepare(output):
    from .selective_memory_data_v1 import prepare as generate
    stamp, start = source(), (time.perf_counter(), time.process_time())
    generate(output)
    manifest = read(output / 'manifest.json')
    write(output / 'execution.json', receipt(start, stage='prepare', **stamp))
    manifest.update(stamp, artifacts=inventory(output))
    write(output / 'manifest.json', manifest)
    return {'stage': 'prepare', 'data_sha256': file_hash(output / 'manifest.json'),
            'train': 2048, 'test': 36864}


def fit(prepared, output):
    import torch
    from . import selective_memory_models_v1 as learned
    from .selective_memory_data_v1 import tensorize
    stamp, start = source(), (time.perf_counter(), time.process_time())
    manifest = verify(prepared)
    frozen(manifest, stamp)
    committed([prepared / name for name in (*manifest['artifacts'], 'manifest.json')])
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    rows = read(prepared / 'train.json.xz')['rows']
    if len(rows) != 2048:
        raise ValueError('frozen TRAIN inventory differs')
    reports = {}
    for seed in SEEDS:
        native = read(prepared / f'native-{seed}.json.xz')
        tensors = tensorize(rows, native)
        for arm in ARMS:
            model = learned.Model(arm, seed)
            report = learned.fit(model, tensors, seed)
            name = f'{arm}-{seed}.json'
            state = {key: value.detach().cpu().tolist()
                     for key, value in model.state_dict().items()}
            write(output / name, {'version': VERSION, 'arm': arm, 'seed': seed,
                                 'state': state, 'state_sha256': learned.fingerprint(model)})
            reports[f'{arm}/{seed}'] = report
            print(json.dumps({'stage': 'fit', 'arm': arm, 'seed': seed,
                              'parameters': sum(p.numel() for p in model.parameters())}), flush=True)
        signatures = [reports[f'{arm}/{seed}']['minibatch_sha256'] for arm in ARMS]
        if len(set(signatures)) != 1:
            raise ValueError('arms saw different TRAIN samples')
    write(output / 'training.json', {'version': VERSION, 'reports': reports})
    write(output / 'execution.json', receipt(start, stage='fit', fits=15, **stamp))
    write(output / 'manifest.json', {'version': VERSION, **stamp,
          'data_sha256': file_hash(prepared / 'manifest.json'),
          'arms': list(ARMS), 'seeds': list(SEEDS), 'fits': 15,
          'artifacts': inventory(output)})
    return {'stage': 'fit', 'fits': 15, 'fit_sha256': file_hash(output / 'manifest.json')}


def restore(path, arm, seed):
    import torch
    from .selective_memory_models_v1 import Model, fingerprint
    saved = read(path)
    if saved['arm'] != arm or saved['seed'] != seed:
        raise ValueError('checkpoint identity differs')
    model = Model(arm, seed)
    model.load_state_dict({key: torch.tensor(value, dtype=torch.float64)
                           for key, value in saved['state'].items()}, strict=True)
    if fingerprint(model) != saved['state_sha256']:
        raise ValueError('checkpoint state hash differs')
    return model.eval().requires_grad_(False)


def collect(prepared, fitted, output):
    import numpy as np
    import torch
    from . import selective_memory_models_v1 as learned
    from .selective_memory_data_v1 import tensorize
    stamp, start = source(), (time.perf_counter(), time.process_time())
    data, fits = verify(prepared), verify(fitted)
    frozen(data, stamp)
    frozen(fits, stamp)
    if fits['data_sha256'] != file_hash(prepared / 'manifest.json') or fits['fits'] != 15:
        raise ValueError('fit binding or inventory differs')
    committed([fitted / name for name in (*fits['artifacts'], 'manifest.json')])
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    rows = read(prepared / 'test.json.xz')['rows']
    if len(rows) != 36864 or any('target_y' in row for row in rows):
        raise ValueError('TEST observation inventory or separation differs')
    ids, reports = [row['id'] for row in rows], {}
    for seed in SEEDS:
        native = read(prepared / f'native-{seed}.json.xz')
        tensors = tensorize(rows, native)
        for arm in ARMS:
            model = restore(fitted / f'{arm}-{seed}.json', arm, seed)
            before = learned.fingerprint(model)
            tick = time.perf_counter(), time.process_time()
            arrays = learned.collect(model, tensors)
            after = learned.fingerprint(model)
            if before != after or any(p.grad is not None for p in model.parameters()):
                raise ValueError('collection changed model weights or gradients')
            np.savez_compressed(output / f'raw-{arm}-{seed}.npz',
                                **{key: value.cpu().numpy() for key, value in arrays.items()})
            reports[f'{arm}/{seed}'] = receipt(tick, before_sha256=before,
                  after_sha256=after, optimizer_updates=0,
                  arrays={key: list(value.shape) for key, value in arrays.items()})
            del arrays, model
            print(json.dumps({'stage': 'collect', 'arm': arm, 'seed': seed,
                              'records': len(rows)}), flush=True)
    shutil.copyfile(fitted / 'manifest.json', output / 'fit-manifest.json')
    write(output / 'execution.json', receipt(start, stage='collect', reports=reports, **stamp))
    write(output / 'manifest.json', {'version': VERSION, **stamp,
          'data_sha256': file_hash(prepared / 'manifest.json'),
          'fit_sha256': file_hash(fitted / 'manifest.json'), 'ids': ids,
          'id_order_sha256': digest(ids), 'records': len(rows),
          'arms': list(ARMS), 'seeds': list(SEEDS), 'artifacts': inventory(output)})
    return {'stage': 'collect', 'records': len(rows), 'frozen_models': 15,
            'raw_sha256': file_hash(output / 'manifest.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'fit', 'collect', 'score'))
    parser.add_argument('--prepared', type=Path, default=ROOT / 'data/selective-memory-v1')
    parser.add_argument('--fitted', type=Path, default=ROOT / 'data/selective-memory-fit-v1')
    parser.add_argument('--raw', type=Path, default=ROOT / 'results/selective-memory-v1/raw')
    parser.add_argument('--scored', type=Path, default=ROOT / 'results/selective-memory-v1/scored')
    args = parser.parse_args()
    if args.stage == 'prepare':
        result = prepare(args.prepared)
    elif args.stage == 'fit':
        result = fit(args.prepared, args.fitted)
    elif args.stage == 'collect':
        result = collect(args.prepared, args.fitted, args.raw)
    else:
        from .selective_memory_score_v1 import score
        stamp = source()
        raw = verify(args.raw)
        frozen(raw, stamp)
        committed([args.raw / name for name in (*raw['artifacts'], 'manifest.json')])
        start = time.perf_counter(), time.process_time()
        summary = score(args.prepared, args.raw, args.scored)
        write(args.scored / 'execution.json', receipt(start, stage='score', **stamp))
        manifest = read(args.scored / 'manifest.json')
        manifest['artifacts'] = inventory(args.scored)
        write(args.scored / 'manifest.json', manifest)
        result = {key: summary[key] for key in
                  ('decision', 'passed_checks', 'total_checks', 'fully_passing_cells')}
        result['output'] = str(args.scored)
    print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == '__main__':
    main()
