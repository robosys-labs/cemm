"""One fixed TRAIN-only objective comparison; no simulator or TEST access."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import random
import resource
import subprocess
import time

import torch

from . import temporal_native_models_v1 as learned
from .temporal_native_transfer_v1 import tensors
from .temporal_train_trace_v1 import SEEDS, STAGES, digest, encoded, read, require, summarize, write

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
VERSION = 'prefix-protection-train-v1'
PROTOCOL = 'PREFIX_PROTECTION_TRAIN_PROTOCOL_V1.md'
PROTOCOL_COMMIT = 'caee7dd730a6d6e661a5d0a2b5af7a6bebc0a2b5'
INPUT_SHA256 = '660bb412f2d165295c30d2248daa2ae7a334c56d4fa95fe324f80aa356b7063f'
BASELINE_FIT_SHA256 = 'bd626b837f739a91971d296a448ee99cd1dcfcb841d7e78d275fc9945fa00ea3'


def tensor_fingerprint(data):
    """Bind every converted receipt, query and label, not only sampled IDs."""
    result = sha256()
    for name, value in sorted(data.items()):
        result.update(encoded([name, list(value.shape), str(value.dtype)]))
        result.update(value.detach().contiguous().numpy().astype(
            '<i8' if name.endswith('_y') else '<f8', copy=False).tobytes())
    return result.hexdigest()


def horizons(step, final_only=False):
    # final_only is exposed only to synthetic equivalence tests, never the CLI.
    return torch.full((128,), 2, dtype=torch.long) if final_only else (step * 128 + torch.arange(128)) % 3


def fit(model, values, seed, steps=256, *, final_only=False):
    """Same six-term loop; select only the protected term's prefix per sample."""
    require(type(steps) is int and 0 < steps <= 256, 'invalid fixed-budget update count')
    data = learned._arrays(values)
    size = len(data['base'])
    require(size > 0 and all(len(v) == size for v in data.values()), 'training batch inventory differs')
    rng, batches, schedule = random.Random(20261108200 + seed), sha256(), sha256()
    counts, losses = [0, 0, 0], []
    initial, inputs = learned.fingerprint(model), tensor_fingerprint(data)
    optimizer = torch.optim.Adam(model.parameters(), lr=.01)
    wall, cpu = time.perf_counter(), time.process_time()
    model.train()
    for step in range(steps):
        indices = [rng.randrange(size) for _ in range(128)]
        batches.update((json.dumps(indices, separators=(',', ':')) + '\n').encode())
        batch = {name: value[indices] for name, value in data.items()}
        before = model.history(batch['base'])
        first = model.receive(before, learned.receipt(batch['first_q'], batch['first_y']))
        both = model.receive(first, learned.receipt(batch['second_q'], batch['second_y']))
        selected = horizons(step, final_only)
        schedule.update(encoded(selected.tolist()))
        counts = [a + b for a, b in zip(counts, torch.bincount(selected, minlength=3).tolist())]
        protected = both if final_only else torch.stack((before, first, both), 1)[torch.arange(128), selected]
        forecasts = ((before, 'first'), (first, 'second'), (before, 'target'),
                     (first, 'target'), (both, 'target'), (protected, 'protected'))
        components = torch.stack(tuple(-model.predict(state, batch[name + '_q']).gather(
            1, batch[name + '_y'][:, None]).log().mean() for state, name in forecasts))
        loss = components.mean()
        require(bool(torch.isfinite(loss)), 'nonfinite uncapped training NLL')
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        losses.append({'update': step + 1, 'mean_nll': loss.item(),
                       'forecast_nll': dict(zip(learned.FORECASTS, components.detach().tolist()))})
    require(tensor_fingerprint(data) == inputs, 'training inputs were mutated')
    return {'arm': model.arm, 'seed': seed, 'initial_sha256': initial, 'final_sha256': learned.fingerprint(model),
            'parameters': sum(p.numel() for p in model.parameters()), 'updates': steps, 'batch_size': 128,
            'sampled_episodes': steps * 128, 'forecast_terms': steps * 128 * 6,
            'target_endpoint_forecasts_per_episode': 3, 'minibatch_seed': 20261108200 + seed,
            'minibatch_sha256': batches.hexdigest(), 'input_tensors_sha256': inputs,
            'horizon_counts': counts, 'horizon_sha256': schedule.hexdigest(),
            'horizon_rule': 'final-only synthetic control' if final_only else '(step*128+position)%3',
            'losses': losses, 'wall_seconds': time.perf_counter() - wall,
            'cpu_seconds': time.process_time() - cpu,
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def committed(path, commit):
    path = Path(path).resolve()
    saved = subprocess.check_output(['git', 'show', commit + ':' + path.relative_to(REPO).as_posix()], cwd=REPO)
    require(sha256(saved).hexdigest() == digest(path), 'file differs from committed bytes: ' + str(path))


def inputs(selected):
    require(digest(selected) == INPUT_SHA256, 'fixed TRAIN projection differs')
    source = read(selected)
    require(len(source['rows']) == len({r['id'] for r in source['rows']}) == 2048, 'TRAIN inventory differs')
    require(sha256(encoded(source['rows'])).hexdigest() == source['history_digest'], 'TRAIN history digest differs')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    subprocess.run(['git', 'merge-base', '--is-ancestor', PROTOCOL_COMMIT, commit], cwd=REPO, check=True)
    require(not subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=REPO),
            'commit tracked changes before execution')
    names = set(source['source_sha256']) | {PROTOCOL, Path(__file__).name,
        'tests/test_prefix_protection_train_v1.py', 'prefix_protection_score_v1.py',
        'tests/test_prefix_protection_score_v1.py', 'temporal_train_trace_v1.py'}
    hashes = {}
    for name in sorted(names):
        committed(ROOT / name, commit)
        hashes[name] = digest(ROOT / name)
        if name in source['source_sha256']:
            require(hashes[name] == source['source_sha256'][name], 'frozen study source changed: ' + name)
    committed(selected, commit)
    return source, {'source_commit': commit, 'source_sha256': hashes}


def entry(path):
    return {'sha256': digest(path), 'bytes': path.stat().st_size}


def fit_stage(selected, baseline, output):
    source, stamp = inputs(selected)
    require(digest(baseline / 'manifest.json') == BASELINE_FIT_SHA256, 'original fit manifest changed')
    original = read(baseline / 'manifest.json')
    require(original['data_sha256'] == source['data_sha256'] and
            original['source_sha256'] == source['source_sha256'], 'original data/source binding differs')
    # Verify all ten baseline receipts before beginning any candidate fit.
    receipts = {}
    for seed in SEEDS:
        for arm in ('native', 'flat'):
            name = f'{arm}-{seed}.json'
            require(digest(baseline / name) == original['checkpoints'][name]['sha256'], 'original checkpoint changed')
            saved = read(baseline / name)
            require(saved['arm'] == arm and saved['seed'] == seed and
                    saved['fit'] == original['checkpoints'][name]['fit'], 'original fit receipt differs')
            receipts[name] = saved['fit']
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    checkpoints = {}
    for seed in SEEDS:
        values, pair = tensors(source['rows'], source['native'][str(seed)]), []
        for arm in ('native', 'flat'):
            name = f'{arm}-{seed}.json'
            model = learned.Model(arm, seed)
            require(learned.fingerprint(model) == receipts[name]['initial_sha256'], 'initialization differs')
            report = fit(model, values, seed)
            require(report['minibatch_sha256'] == receipts[name]['minibatch_sha256'], 'minibatch exposure differs')
            require(report['horizon_counts'] == [10923, 10923, 10922], 'horizon allocation differs')
            report.update(initial_matches_baseline=True, minibatch_matches_baseline=True,
                          baseline_checkpoint_sha256=original['checkpoints'][name]['sha256'])
            pair.append((report['input_tensors_sha256'], report['minibatch_sha256'], report['horizon_sha256']))
            state = {k: v.tolist() for k, v in model.state_dict().items()}
            write(output / name, {'version': VERSION, **stamp, 'input_sha256': INPUT_SHA256,
                'data_sha256': source['data_sha256'], 'arm': arm, 'seed': seed,
                'state': state, 'state_sha256': sha256(encoded(state)).hexdigest(), 'fit': report})
            checkpoints[name] = entry(output / name)
            print(json.dumps({'stage': 'fit', 'arm': arm, 'seed': seed, 'updates': report['updates']}), flush=True)
        require(pair[0] == pair[1], 'native/flat receipt, label or schedule exposure differs')
    write(output / 'manifest.json', {'version': VERSION, **stamp, 'input_sha256': INPUT_SHA256,
        'baseline_fit_manifest_sha256': BASELINE_FIT_SHA256, 'checkpoints': checkpoints})
    return {'stage': 'fit', 'checkpoints': len(checkpoints), 'manifest_sha256': digest(output / 'manifest.json')}


@torch.inference_mode()
def predictions(model, values):
    """Four inference prefixes; target labels never enter recurrent state."""
    data = learned._arrays(values)
    require(all(p.grad is None for p in model.parameters()), 'inference starts with parameter gradients')
    model.eval().requires_grad_(False)
    before = learned.fingerprint(model)
    state, result = model.history(data['base'][:, :8]), {}
    receipts = (None, data['base'][:, 8], learned.receipt(data['first_q'], data['first_y']),
                learned.receipt(data['second_q'], data['second_y']))
    for stage, observed in zip(STAGES, receipts):
        if observed is not None:
            state = model.receive(state, observed)
        result[stage] = {name: model.predict(state, data[name + '_q']).tolist() for name in ('target', 'protected')}
    require(learned.fingerprint(model) == before and all(p.grad is None for p in model.parameters()),
            'inference changed parameters or gradients')
    return result


def evaluate(selected, fitted, output):
    source, stamp = inputs(selected)
    manifest = read(fitted / 'manifest.json')
    require(manifest['version'] == VERSION and manifest['input_sha256'] == INPUT_SHA256 and
            manifest['source_sha256'] == stamp['source_sha256'] and
            manifest['baseline_fit_manifest_sha256'] == BASELINE_FIT_SHA256, 'fit manifest binding differs')
    expected = {f'{arm}-{seed}.json' for seed in SEEDS for arm in ('native', 'flat')}
    require(set(manifest['checkpoints']) == expected, 'complete ten-checkpoint inventory required')
    # The entire fit stage must be committed before any evaluation inference.
    committed(fitted / 'manifest.json', stamp['source_commit'])
    for name in sorted(expected):
        require(entry(fitted / name) == manifest['checkpoints'][name], 'candidate checkpoint changed')
        committed(fitted / name, stamp['source_commit'])
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    artifacts, reports = {}, {}
    for seed in SEEDS:
        values = tensors(source['rows'], source['native'][str(seed)])
        for arm in ('native', 'flat'):
            name = f'{arm}-{seed}.json'
            saved = read(fitted / name)
            require(saved['version'] == VERSION and saved['arm'] == arm and saved['seed'] == seed and
                    saved['input_sha256'] == INPUT_SHA256 and saved['source_sha256'] == stamp['source_sha256'] and
                    sha256(encoded(saved['state'])).hexdigest() == saved['state_sha256'], 'checkpoint binding differs')
            model = learned.Model(arm, seed)
            model.load_state_dict({k: torch.tensor(v, dtype=torch.float64) for k, v in saved['state'].items()})
            require(learned.fingerprint(model) == saved['fit']['final_sha256'], 'loaded checkpoint fingerprint differs')
            raw = {'version': VERSION, 'input_sha256': INPUT_SHA256, 'arm': arm, 'seed': seed,
                'ids': [r['id'] for r in source['rows']], 'checkpoint_sha256': digest(fitted / name),
                'weights_sha256': learned.fingerprint(model), 'predictions': predictions(model, values)}
            filename = f'raw-{arm}-{seed}.json.xz'
            write(output / filename, raw)
            artifacts[filename] = entry(output / filename)
            reports[f'{arm}/{seed}'] = summarize(raw, source['rows'])
    write(output / 'summary.json.xz', {'version': VERSION, 'models': reports})
    artifacts['summary.json.xz'] = entry(output / 'summary.json.xz')
    write(output / 'manifest.json', {'version': VERSION, **stamp, 'input_sha256': INPUT_SHA256,
        'fit_manifest_sha256': digest(fitted / 'manifest.json'), 'artifacts': artifacts,
        'checkpoint_count': 10, 'histories_per_checkpoint': 2048, 'forecasts_per_checkpoint': 16384,
        'optimizer_updates': 0, 'weights_unchanged': True, 'parameter_gradients_absent': True})
    return {'stage': 'evaluate', 'manifest_sha256': digest(output / 'manifest.json')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('fit', 'evaluate'))
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--baseline', type=Path)
    parser.add_argument('--fitted', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if (args.stage == 'fit' and args.baseline is None) or (args.stage == 'evaluate' and args.fitted is None):
        parser.error('fit requires --baseline; evaluate requires --fitted')
    start = time.perf_counter(), time.process_time()
    result = fit_stage(args.input, args.baseline, args.output) if args.stage == 'fit' else evaluate(
        args.input, args.fitted, args.output)
    write(args.output / 'execution.json', {'stage': args.stage, 'wall_seconds': time.perf_counter() - start[0],
        'cpu_seconds': time.process_time() - start[1], 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
    print(json.dumps(result, sort_keys=True))
