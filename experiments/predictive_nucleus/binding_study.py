"""Bounded binding study adapter: prepare, fit, publish, collect, then score.

Reuse existing native worlds, outcome fitter, tokenization, caching and metrics.
Publication SHAs are caller attestations checked outside this offline runner;
source/data/tensor bytes are checked here. No OS sandbox or custody is claimed.
"""
import argparse
import json
from pathlib import Path
import resource
import time
import traceback

from . import acceptance_contract as c, continuation_run as io, bilingual_run as prior

PROTOCOL = io.ROOT / 'binding_protocol_v1.json'
OLD = io.ROOT / 'results/lexical-v1'
BANKS = {'bilingual_retention': 'bilingual-v1', 'lexical_retention': 'lexical-v1'}


def protocol():
    return c.load_json(PROTOCOL, (io.ROOT / 'snapshots/binding_protocol_v1.sha256').read_text().split()[0])


def sources():
    names = set(prior.sources()) | {'binding_model.py', 'binding_training.py', 'binding_data.py',
        'binding_study.py', 'binding_scoring.py', PROTOCOL.name, 'snapshots/binding_protocol_v1.sha256'}
    return {name: io._hash(io.ROOT / name) for name in sorted(names)}


def prepare(output):
    from .binding_data import build_assets
    config = protocol(); assets = build_assets()
    c.require(assets['audit']['train_forecasts'] == config['train_forecasts'] and
        assets['audit']['challenge_forecasts_per_law'] == config['challenge_forecasts_per_law'], 'bank count differs')
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'train-inputs.json.xz': io._write(output / 'train-inputs.json.xz', assets['train'])}
    for law in ('nand', 'nor'):
        for kind in ('inputs', 'oracle'):
            name = f'{law}-{kind}.json.xz'; artifacts[name] = io._write(output / name, assets[law][kind])
    artifacts['audit.json'] = io._write(output / 'audit.json', assets['audit'])
    inventory = io._read(io.ROOT / 'data/lexical-v1/freeze.json')['checkpoints']
    paths = [prior.old.FITTED / item['file'] for group in inventory.values() for item in group.values()]
    for folder in BANKS.values():
        paths.extend((io.ROOT / 'data' / folder).glob('*'))
    paths.extend(OLD.glob('trace-*-grounded.json.xz')); paths.extend(OLD.glob('trace-*-retention.json.xz'))
    historical = {p.relative_to(io.ROOT).as_posix(): io._hash(p) for p in sorted(paths) if p.is_file()}
    io._write(output / 'freeze.json', {'version': config['version'], 'sources': sources(),
        'artifacts': artifacts, 'checkpoints': inventory, 'historical': historical,
        'protocol_sha256': io._hash(PROTOCOL), 'audit': assets['audit']})


def verify(data):
    config, freeze = protocol(), io._read(data / 'freeze.json')
    commitment = io._read(io.ROOT / 'binding_freeze_v1.json')
    c.require(set(commitment) == set(freeze['artifacts']) | {'freeze.json'}, 'data commitment inventory differs')
    for name, digest in commitment.items():
        c.require(io._hash(data / name) == digest, 'public data commitment differs: ' + name)
    c.require(freeze['version'] == config['version'] and freeze['sources'] == sources() and
              freeze['protocol_sha256'] == io._hash(PROTOCOL), 'source/protocol freeze differs')
    for name, item in freeze['artifacts'].items():
        c.require(io._hash(data / name) == item['sha256'], 'data bytes differ: ' + name)
    for name, digest in freeze['historical'].items():
        c.require(io._hash(io.ROOT / name) == digest, 'historical bytes differ: ' + name)
    for group in freeze['checkpoints'].values():
        for item in group.values():
            c.require(io._hash(prior.old.FITTED / item['file']) == item['sha256'], 'world checkpoint differs')
    return config, freeze


def publication(value):
    c.require(type(value) is str and len(value) == 40 and set(value) <= set('0123456789abcdef'),
              'verified publication commit SHA required')
    return value


def fit(data, output, published):
    from .binding_training import fit_comparison
    from .binding_model import ARMS
    config, freeze = verify(data); runtime = io._runtime(config)
    output.mkdir(parents=True, exist_ok=False)
    io._write(output / 'attempt.json', {'source_publication': publication(published), 'runtime': runtime,
        'freeze_sha256': io._hash(data / 'freeze.json'), 'one_attempt': True})
    observed = io._read(data / 'train-inputs.json.xz'); checkpoints, reports = {}, {}
    wall, cpu = time.perf_counter(), time.process_time()
    for seed in config['model_seeds']:
        world = prior.world_for(freeze['checkpoints'], 'nand', seed)
        result = fit_comparison(observed, world, seed=seed, **config['fit'])
        c.require(all(r['observed_events_per_update'] == config['train_forecasts'] for r in result['reports'].values()),
                  'prescribed training exposure differs')
        record = {k: v for k, v in result.items() if k != 'models'}
        reports[str(seed)] = record
        for arm in ARMS:
            model = result['models'][arm]
            checkpoints[f'{arm}/{seed}'] = {'arm': arm, 'seed': seed,
                'state_sha256': result['reports'][arm]['final_sha256'],
                'state': {k: v.detach().tolist() for k, v in model.state_dict().items()}}
        io._write(output / f'completed-{seed}.json', record)
        print(json.dumps({'completed_seed': seed, 'reports': record['reports']}), flush=True)
    verify(data)
    io._write(output / 'checkpoints.json.xz', {'version': config['version'], 'complete': True,
        'source_publication': publication(published), 'freeze_sha256': io._hash(data / 'freeze.json'),
        'runtime': runtime, 'reports': reports, 'checkpoints': checkpoints,
        'resources': {'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - wall,
                      'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}})


def load_models(fitted, config, data):
    import torch
    from .binding_model import ARMS, PARAMETERS, encoder
    from .joint_objective import fingerprint
    saved = io._read(fitted / 'checkpoints.json.xz')
    expected = {f'{arm}/{seed}' for arm in ARMS for seed in config['model_seeds']}
    c.require(saved['complete'] is True and saved['version'] == config['version'] and
        saved['freeze_sha256'] == io._hash(data / 'freeze.json') and
        set(saved['checkpoints']) == expected and set(saved['reports']) == {str(s) for s in config['model_seeds']},
        'incomplete/substituted fit inventory')
    result = {}
    for key, item in saved['checkpoints'].items():
        arm, textseed = key.split('/'); seed = int(textseed)
        report = saved['reports'][textseed]['reports'][arm]
        c.require(item['arm'] == arm and item['seed'] == seed and
            report['updates'] == config['fit']['updates'] and report['parameters'] == PARAMETERS[arm] and
            report['observed_events_per_update'] == config['train_forecasts'] and
            saved['reports'][textseed]['training_input_sha256'] == c.digest(io._read(data / 'train-inputs.json.xz')),
            'fit identity/exposure differs')
        net = encoder(arm, seed)
        c.require(fingerprint(net.state_dict()) == report['initial_sha256'], 'fit initial state differs')
        net.load_state_dict({k: torch.tensor(v, dtype=torch.float64) for k, v in item['state'].items()}, strict=True)
        c.require(fingerprint(net.state_dict()) == item['state_sha256'] == report['final_sha256'] and
            all(bool(torch.isfinite(p).all()) for p in net.parameters()), 'fit state differs')
        result[key] = net.eval().requires_grad_(False)
    return result


def probes(net, world, group):
    """Final mask/swap probes share exactly the real prefix; probes do not update it."""
    from .bilingual_model import combine, tokenize_batch
    from .binding_data import SWAPS  # Evaluator intervention only, outside the learner.
    state = group['state']
    for t, event in enumerate(group['events']):
        options = event['likelihood'] + state[:, None, :, None]
        order = net(event['features']); raw, pending = combine(order, options)
        yield 'canonical', t, raw, order
        if t == len(group['events']) - 1:
            masked = event['features'].clone(); masked[:, :, 1:] = 0.
            texts = [' '.join(word if word in r['entities'] else SWAPS[word]
                       for word in r['utterances'][t]['text'].split()) for r in group['records']]
            swapped, mentions = tokenize_batch(texts, [r['entities'] for r in group['records']])
            c.require(mentions.equal(event['mentions']), 'swap changed entity mentions')
            for view, features in (('masked', masked), ('swapped', swapped)):
                alternate = net(features); predicted, _ = combine(alternate, options)
                yield view, t, predicted, alternate
        state = world.receive(pending, event['post'])


def collect(data, fitted, output, published):
    import torch
    from .binding_model import ARMS
    from .joint_objective import fingerprint
    config, freeze = verify(data); runtime = io._runtime(config)
    models = load_models(fitted, config, data)
    output.mkdir(parents=True, exist_ok=False)
    identity = {'weights_publication': publication(published), 'runtime': runtime,
        'freeze_sha256': io._hash(data / 'freeze.json'), 'checkpoint_sha256': io._hash(fitted / 'checkpoints.json.xz')}
    io._write(output / 'attempt.json', identity); artifacts = {}
    for law in ('nand', 'nor'):
        inputs = {'fresh': io._read(data / f'{law}-inputs.json.xz'), **{bank: io._read(
            io.ROOT / 'data' / folder / f'{law}-inputs.json.xz') for bank, folder in BANKS.items()}}
        for seed in config['model_seeds']:
            world = prior.world_for(freeze['checkpoints'], law, seed); before = fingerprint(world.state_dict())
            for bank, observed in inputs.items():
                wall, cpu = time.perf_counter(), time.process_time(); groups = prior.pack(observed, world)
                preparation = {'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - wall}
                for arm in ARMS:
                    net = models[f'{arm}/{seed}']; tensor_hash = fingerprint(net.state_dict()); points, latencies = [], []
                    wall, cpu = time.perf_counter(), time.process_time()
                    with torch.no_grad():
                        for group in groups:
                            stream = probes(net, world, group) if bank == 'fresh' else (
                                ('canonical', t, raw, order) for t, (raw, order) in enumerate(
                                    prior.forecasts('grounded', net, world, group)))
                            stream = iter(stream)
                            while True:
                                started = time.perf_counter()
                                try: view, t, raw, order = next(stream)
                                except StopIteration: break
                                latencies.append((time.perf_counter() - started) / len(raw))
                                points.extend({'id': e['id'], 'step': t, 'view': view,
                                    'logp': raw[j].tolist(), 'order_logp': order[j].tolist()}
                                    for j, e in enumerate(group['records']))
                    costs = {'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - wall,
                        'native_cache_shared': preparation,
                        'batch_amortized_forecast_p95_seconds': sorted(latencies)[int(.95 * (len(latencies) - 1))],
                        'latency_scope': 'Forecast chunks divided by batch size; not single-request service latency.',
                        'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
                    c.require(fingerprint(net.state_dict()) == tensor_hash and fingerprint(world.state_dict()) == before,
                              'collection changed model weights')
                    name = f'trace-{law}-{seed}-{arm}-{bank}.json.xz'
                    artifacts[name] = io._write(output / name, {**identity, 'law': law, 'seed': seed,
                        'arm': arm, 'bank': bank, 'state_sha256': tensor_hash,
                        'input_sha256': c.digest(observed), 'points': points, 'resources': costs})
            print(json.dumps({'collected': f'{law}/{seed}'}), flush=True)
    verify(data)
    io._write(output / 'manifest.json', {**identity, 'complete': True, 'artifacts': artifacts,
        'oracle_opened': False, 'scope': 'All observed-only forecasts persisted; score is a separate stage.'})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'fit', 'collect', 'score'))
    for key in ('data', 'fitted', 'traces', 'output'): parser.add_argument('--' + key, type=Path, required=key == 'output')
    parser.add_argument('--publication'); args = parser.parse_args()
    for key in {'prepare': (), 'fit': ('data', 'publication'), 'collect': ('data', 'fitted', 'publication'),
                'score': ('data', 'fitted', 'traces')}[args.stage]:
        if getattr(args, key) is None: parser.error('--' + key + ' required')
    existed = args.output.exists()
    try:
        if args.stage == 'prepare': prepare(args.output)
        elif args.stage == 'fit': fit(args.data, args.output, args.publication)
        elif args.stage == 'collect': collect(args.data, args.fitted, args.output, args.publication)
        else:
            from .binding_scoring import score
            score(args.data, args.fitted, args.traces, args.output)
    except BaseException as error:
        if not existed and args.output.is_dir():
            io._write(args.output / 'failure.json', {'stage': args.stage, 'error': type(error).__name__,
                'message': str(error), 'traceback': traceback.format_exc(), 'retry_permitted': False,
                'decision': 'STOP_INCOMPLETE_EXECUTION', 'scientific_admission': False})
        raise


if __name__ == '__main__': main()
