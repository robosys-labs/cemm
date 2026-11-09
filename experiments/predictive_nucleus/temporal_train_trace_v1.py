"""Post-score TRAIN receipt attribution; no fitting, evaluator or new episodes.

prepare-input selects only existing TRAIN records from the shared public file.
trace opens only that selection, checkpoint files, and source/manifests. It never
opens the shared public file, held-out answers, or evaluator records.
"""
import argparse
from hashlib import sha256
import importlib
import json
import lzma
import math
from pathlib import Path
import subprocess
import sys

SEEDS = (7, 11, 23, 37, 53)
STAGES = ('teaching', 'claim', 'first', 'second')
VERSION = 'temporal-native-train-trace-v1'
PROTOCOL = 'TEMPORAL_TRAIN_TRACE_PROTOCOL_V1.md'


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    data = Path(path).read_bytes()
    return json.loads(lzma.decompress(data) if str(path).endswith('.xz') else data)


def write(path, value):
    path = Path(path)
    if path.exists():
        raise ValueError('output already exists: ' + str(path))
    data = encoded(value)
    path.write_bytes(lzma.compress(data) if str(path).endswith('.xz') else data)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def prepare_input(prepared, output):
    """Only project existing records; no learned module is imported here."""
    manifest = read(prepared / 'manifest.json')
    def locked(name):
        require(digest(prepared / name) == manifest['artifacts'][name]['sha256'], 'input hash differs: ' + name)
        return read(prepared / name)
    rows = locked('public.json.xz')['train']
    require(len(rows) == 2048 and len({r['id'] for r in rows}) == 2048, 'TRAIN inventory differs')
    require(sha256(encoded(rows)).hexdigest() == manifest['history_digest'], 'TRAIN history digest differs')
    keys = sorted({q['native_key'] for r in rows for q in
                   [*(x['query'] for x in r['base']), r['first']['query'], r['second'], r['target'], r['protected']]})
    require(all(key.split('/')[2] in ('svo', 'osv') for key in keys), 'non-TRAIN layout')
    native = {}
    for seed in SEEDS:
        bank = locked(f'native-{seed}.json.xz')
        native[str(seed)] = {key: bank[key] for key in keys}
    write(output, {'version': VERSION, 'data_sha256': digest(prepared / 'manifest.json'),
                   'history_digest': manifest['history_digest'], 'source_sha256': manifest['source_sha256'],
                   'source_artifacts': {n: manifest['artifacts'][n] for n in
                       ['public.json.xz', *(f'native-{s}.json.xz' for s in SEEDS)]},
                   'rows': rows, 'native': native})
    return {'input_sha256': digest(output), 'TRAIN_rows': len(rows), 'native_keys_per_seed': len(keys)}


def stamp(root, selected):
    """Require the tracer and protocol to be committed before model execution."""
    repo = root.parents[1]
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=repo, text=True).strip()
    require(not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=repo),
            'commit tracked changes before tracing')
    hashes = {}
    for path in (Path(__file__).resolve(), root / PROTOCOL, selected.resolve()):
        relative = path.relative_to(repo).as_posix()
        saved = subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=repo)
        require(sha256(saved).hexdigest() == digest(path), 'diagnostic source is not committed')
        hashes[relative] = digest(path)
    return {'source_commit': commit, 'diagnostic_source_sha256': hashes}


def summarize(raw, rows):
    """Saved-array arithmetic: no model calls, and no hidden cause labels."""
    groups = {'all': list(range(len(rows)))}
    for i, row in enumerate(rows):
        key = '/'.join((row['law'], 'target-' + row['target']['scope'],
                        'first-' + row['first']['query']['scope']))
        groups.setdefault(key, []).append(i)
    report = {}
    for group, indices in groups.items():
        report[group] = {}
        for field in ('target', 'protected'):
            stage_metrics, correct, losses = {}, {}, {}
            for stage in STAGES:
                predictions = raw['predictions'][stage][field]
                require(len(predictions) == len(rows), 'prediction inventory differs')
                cs, ns, bs = [], [], []
                for i in indices:
                    p, y = predictions[i], rows[i]['answers'][field + '_y']
                    require(len(p) == 8 and all(math.isfinite(x) and 0 <= x <= 1 + 1e-10 for x in p)
                            and abs(math.fsum(p) - 1) <= 1e-10, 'invalid forecast')
                    cs.append(max(range(8), key=p.__getitem__) == y)
                    ns.append(-math.log(p[y]) if p[y] else math.inf)
                    bs.append(math.fsum((x - int(j == y)) ** 2 for j, x in enumerate(p)))
                correct[stage], losses[stage] = cs, ns
                stage_metrics[stage] = {'count': len(indices), 'correct': sum(cs), 'accuracy': sum(cs)/len(cs),
                    'nll': math.fsum(ns)/len(ns) if all(math.isfinite(x) for x in ns) else 'Infinity',
                    'brier': math.fsum(bs)/len(bs)}
            transitions = {}
            for before, after in zip(STAGES, STAGES[1:]):
                old, new = correct[before], correct[after]
                transitions[before + '->' + after] = {
                    'regressions': [rows[i]['id'] for j, i in enumerate(indices) if old[j] and not new[j]],
                    'repairs': [rows[i]['id'] for j, i in enumerate(indices) if new[j] and not old[j]],
                    'nll_worse': [rows[i]['id'] for j, i in enumerate(indices)
                                  if losses[after][j] > losses[before][j]]}
            report[group][field] = {'stages': stage_metrics, 'transitions': transitions}
    return report


def trace(root, prepared, fitted, selected, output):
    """One inference-only replay of every saved TRAIN history and frozen fit."""
    frozen = stamp(root, selected)
    source, fit_manifest, data_manifest = read(selected), read(fitted/'manifest.json'), read(prepared/'manifest.json')
    data_sha = digest(prepared/'manifest.json')
    require(source['version'] == VERSION and source['data_sha256'] == fit_manifest['data_sha256'] == data_sha,
            'source data binding differs')
    rows = source['rows']
    require(len(rows) == len({r['id'] for r in rows}) == 2048, 'TRAIN inventory differs')
    require(sha256(encoded(rows)).hexdigest() == source['history_digest'] == data_manifest['history_digest'],
            'selected TRAIN records differ')
    require(source['source_sha256'] == data_manifest['source_sha256'] == fit_manifest['source_sha256'],
            'frozen source inventories differ')
    expected_names = ['public.json.xz', *(f'native-{s}.json.xz' for s in SEEDS)]
    require(source['source_artifacts'] == {n: data_manifest['artifacts'][n] for n in expected_names},
            'TRAIN projection source receipts differ')
    for name, expected in source['source_sha256'].items():
        require(digest(root/name) == expected, 'frozen study source changed: ' + name)
    # Input projection is published before tracing; its exact file hash is retained.
    # The native frames here are selected by TRAIN keys; they are never regenerated.
    output.mkdir(parents=True, exist_ok=False)
    sys.path.insert(0, str(root.parents[1]))
    import torch
    learned = importlib.import_module('experiments.predictive_nucleus.temporal_native_models_v1')
    packing = importlib.import_module('experiments.predictive_nucleus.temporal_native_transfer_v1')
    torch.set_num_threads(1)
    summary = {'version': VERSION, **frozen, 'input_sha256': digest(selected), 'data_sha256': data_sha,
               'fit_manifest_sha256': digest(fitted/'manifest.json'), 'models': {}, 'artifacts': {}}
    with torch.inference_mode():
        for seed in SEEDS:
            arrays = packing.tensors(rows, source['native'][str(seed)])
            for arm in ('native', 'flat'):
                name = f'{arm}-{seed}.json'
                require(digest(fitted/name) == fit_manifest['checkpoints'][name]['sha256'], 'checkpoint hash differs')
                saved = read(fitted/name)
                require(saved['seed'] == seed and saved['arm'] == arm and saved['data_sha256'] == data_sha
                        and sha256(encoded(saved['state'])).hexdigest() == saved['state_sha256'], 'checkpoint binding differs')
                model = learned.Model(arm, seed).eval().requires_grad_(False)
                model.load_state_dict({k: torch.tensor(v, dtype=torch.float64) for k, v in saved['state'].items()})
                before = learned.fingerprint(model)
                require(before == saved['fit']['final_sha256'], 'loaded weights differ')
                state = model.history(arrays['base'][:, :8])
                predictions = {}
                receipts = (None, arrays['base'][:, 8],
                            learned.receipt(arrays['first_q'], arrays['first_y']),
                            learned.receipt(arrays['second_q'], arrays['second_y']))
                for stage, receipt in zip(STAGES, receipts):
                    if receipt is not None:
                        state = model.receive(state, receipt)
                    predictions[stage] = {field: model.predict(state, arrays[field+'_q']).tolist()
                                          for field in ('target', 'protected')}
                require(learned.fingerprint(model) == before and all(p.grad is None for p in model.parameters()),
                        'frozen weights or gradients changed')
                raw = {'version': VERSION, 'arm': arm, 'seed': seed, 'ids': [r['id'] for r in rows],
                       'checkpoint_sha256': digest(fitted/name), 'weights_sha256': before, 'predictions': predictions}
                filename = f'raw-{arm}-{seed}.json.xz'
                write(output/filename, raw)
                summary['artifacts'][filename] = {'sha256': digest(output/filename), 'bytes': (output/filename).stat().st_size}
                summary['models'][f'{arm}/{seed}'] = summarize(raw, rows)
    write(output/'summary.json.xz', summary)
    write(output/'manifest.json', {'version': VERSION, **frozen, 'input_sha256': digest(selected),
          'data_sha256': data_sha, 'fit_manifest_sha256': digest(fitted/'manifest.json'),
          'artifacts': {**summary['artifacts'], 'summary.json.xz': {'sha256': digest(output/'summary.json.xz'),
                                                                'bytes': (output/'summary.json.xz').stat().st_size}},
          'trained_updates': 0, 'checkpoint_count': 10, 'histories_per_checkpoint': 2048,
          'forecasts_per_checkpoint': 2048 * 4 * 2})
    return {'status': 'COMPLETE_POST_HOC_TRAIN_TRACE', 'manifest_sha256': digest(output/'manifest.json')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare-input', 'trace'))
    parser.add_argument('--root', type=Path)
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--fitted', type=Path)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = prepare_input(args.prepared, args.output) if args.stage == 'prepare-input' else trace(
        args.root.resolve(), args.prepared, args.fitted, args.input, args.output)
    print(json.dumps(result, sort_keys=True))
