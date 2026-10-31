"""One outcome-only lexical continuation; frozen bilingual/native code is reused."""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import resource
import subprocess
import time
import traceback

from . import acceptance_contract as base, bilingual_run as previous, continuation_run as io

ROOT = io.ROOT
PROTOCOL = ROOT / 'lexical_protocol_v1.json'
PARENT_FIT, PARENT_DATA, PARENT_RESULTS = (ROOT / p for p in
    ('data/bilingual-fit-v1', 'data/bilingual-v1', 'results/bilingual-v1'))
VIEWS = ('masked', 'swapped', 'cross_order')
ARMS = ('grounded', 'prior', *VIEWS, 'retention')


def protocol():
    return base.load_json(PROTOCOL, (ROOT / 'snapshots/lexical_protocol_v1.sha256').read_text().split()[0])


def sources():
    names = set(previous.sources()) | {'lexical_run.py', 'lexical_data.py', 'lexical_scoring.py',
        PROTOCOL.name, 'snapshots/lexical_protocol_v1.sha256'}
    return {name: io._hash(ROOT / name) for name in sorted(names)}


def load_encoder(directory, item, seed, *, parent_sha256=None):
    """Hash-bound numeric tensors only; never pickle, permissive casts or code."""
    import torch
    from .joint_objective import fingerprint
    base.require(item['file'] == f'grounded-{seed}.json', 'language filename/seed differs')
    saved = base.load_json(directory / item['file'], item['sha256'])
    expected = {'arm', 'seed', 'state', 'state_sha256'} | ({'parent_sha256'} if parent_sha256 else set())
    base.fields(saved, expected)
    base.require(saved['arm'] == 'grounded' and type(saved['seed']) is int and saved['seed'] == seed and
        (parent_sha256 is None or saved['parent_sha256'] == parent_sha256), 'language identity/parent differs')
    net = previous.learner('grounded', seed)
    base.require(type(saved['state']) is dict and saved['state'].keys() == net.state_dict().keys(),
                 'language tensor inventory differs')
    def numeric(value):
        return all(map(numeric, value)) if type(value) is list else type(value) in (int, float) and math.isfinite(value)
    tensors = {}
    for key, reference in net.state_dict().items():
        values = saved['state'][key]
        base.require(type(values) is list and numeric(values), 'nonfinite or nonnumeric language tensor')
        tensor = torch.tensor(values, dtype=torch.float64)
        base.require(tensor.shape == reference.shape and bool(torch.isfinite(tensor).all()), 'language tensor shape differs')
        tensors[key] = tensor
    net.load_state_dict(tensors, strict=True)
    base.require(fingerprint(net.state_dict()) == saved['state_sha256'] == item['state_sha256'],
                 'language tensor fingerprint differs')
    return net


def parents(config):
    training = base.load_json(PARENT_FIT / 'training.json', config['parent_language_training_sha256'])
    base.require(training['complete'] is True and training['world_checkpoints_unchanged'] is True and
                 training['version'] == 'bilingual-v1', 'parent language fitting incomplete')
    inventory, historical = {}, {'data/bilingual-fit-v1/training.json': config['parent_language_training_sha256']}
    for seed in config['model_seeds']:
        item = dict(training['checkpoints'][f'grounded/{seed}'])
        report = training['reports'][f'grounded/{seed}']
        base.require(report['updates'] == 256 and report['training_forecasts_per_update'] == 384 and
                     report['parameters'] == 474, 'parent language exposure differs')
        item['state_sha256'] = report['final_sha256']
        load_encoder(PARENT_FIT, item, seed)
        inventory[str(seed)] = item
        historical['data/bilingual-fit-v1/' + item['file']] = item['sha256']
    for name in historical:
        original = subprocess.check_output(['git', '-C', str(io.REPO), 'show',
            config['language_checkpoint_commit'] + ':experiments/predictive_nucleus/' + name])
        base.require(original == (ROOT / name).read_bytes(), 'published parent bytes differ: ' + name)
    old_data = base.load_json(PARENT_DATA / 'freeze.json', config['old_data_freeze_sha256'])
    old_results = base.load_json(PARENT_RESULTS / 'manifest.json', config['old_result_manifest_sha256'])
    historical['data/bilingual-v1/freeze.json'] = config['old_data_freeze_sha256']
    historical['results/bilingual-v1/manifest.json'] = config['old_result_manifest_sha256']
    for name in ('train-inputs.json.xz', *(f'{law}-{kind}.json.xz'
                  for law in previous.old.LAWS for kind in ('inputs', 'oracle'))):
        historical['data/bilingual-v1/' + name] = old_data['artifacts'][name]['sha256']
    for law in previous.old.LAWS:
        for seed in config['model_seeds']:
            name = f'trace-{law}-{seed}-grounded.json.xz'
            historical['results/bilingual-v1/' + name] = old_results['artifacts'][name]['sha256']
    for name, digest in historical.items():
        base.require(io._hash(ROOT / name) == digest, 'historical artifact differs: ' + name)
    return inventory, historical


def prepare(output):
    from .lexical_data import build_assets
    config = protocol()
    language, historical = parents(config)
    assets, inventory = build_assets(config), previous.old.checkpoints(config)
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {}
    for split, bank in {'train': assets['train'], **assets['challenge']}.items():
        for kind, value in bank.items():
            name = f'{split}-{kind}.json.xz'; artifacts[name] = io._write(output / name, value)
    base.require(set(assets['train']) == {'inputs'} and
        sum(len(e['utterances']) for e in assets['train']['inputs']['episodes']) == 768 and all(
        sum(len(e['utterances']) for e in bank['inputs']['episodes']) == 4160
        for bank in assets['challenge'].values()), 'prepared lexical inventory differs')
    artifacts['audit.json'] = io._write(output / 'audit.json', assets['audit'])
    io._write(output / 'freeze.json', {'version': config['version'], 'sources': sources(),
        'artifacts': artifacts, 'checkpoints': inventory, 'language_checkpoints': language,
        'historical_artifacts': historical, 'protocol_sha256': io._hash(PROTOCOL),
        'world_fitting_permitted': False, 'language_parameters': 474})
    print(json.dumps({'prepared': str(output), 'audit': assets['audit']}), flush=True)


def verify(data):
    io._committed(data / 'freeze.json')
    config, freeze = protocol(), io._read(data / 'freeze.json')
    language, historical = parents(config)
    base.require(freeze['version'] == config['version'] and freeze['sources'] == sources() and
        freeze['protocol_sha256'] == io._hash(PROTOCOL) and freeze['checkpoints'] == previous.old.checkpoints(config) and
        freeze['language_checkpoints'] == language and freeze['historical_artifacts'] == historical,
        'frozen lexical provenance differs')
    expected = {'train-inputs.json.xz', 'audit.json', *(f'{law}-{kind}.json.xz'
                for law in previous.old.LAWS for kind in ('inputs', 'oracle'))}
    base.require(set(freeze['artifacts']) == expected, 'lexical artifact inventory differs')
    for name, item in freeze['artifacts'].items():
        base.require(io._hash(data / name) == item['sha256'], 'prepared artifact differs: ' + name)
    return config, freeze


def fit(data, output):
    import torch
    from .joint_objective import fingerprint
    config, freeze = verify(data); runtime = io._runtime(config)
    output.mkdir(parents=True, exist_ok=False)
    io._write(output / 'attempt.json', {'source_data_commit': io._git('rev-parse', 'HEAD'),
        'freeze_sha256': io._hash(data / 'freeze.json'), 'runtime': runtime, 'one_attempt': True})
    inputs = io._read(data / 'train-inputs.json.xz')
    reports, checkpoints, start, cpu = {}, {}, time.perf_counter(), time.process_time()
    for seed in config['model_seeds']:
        world = previous.world_for(freeze['checkpoints'], 'nand', seed)
        before = fingerprint(world.state_dict()); batches = previous.pack(inputs, world)
        parent = freeze['language_checkpoints'][str(seed)]
        net = load_encoder(PARENT_FIT, parent, seed); initial = fingerprint(net.state_dict())
        optimizer = torch.optim.Adam(net.parameters(), lr=config['fit']['learning_rate'])
        curves, wall0, cpu0 = [], time.perf_counter(), time.process_time()
        for step in range(config['fit']['updates']):
            optimizer.zero_grad(set_to_none=True); loss, count = 0., 0
            for group in batches:
                for (raw, _), event in zip(previous.forecasts('grounded', net, world, group), group['events'], strict=True):
                    loss = loss - raw.gather(1, event['target'][:, None]).sum(); count += len(raw)
            base.require(count == config['fit']['training_forecasts_per_update'], 'lexical training exposure differs')
            loss = loss / count
            base.require(bool(torch.isfinite(loss)), 'nonfinite lexical objective')
            loss.backward()
            torch.nn.utils.clip_grad_norm_(net.parameters(), config['fit']['gradient_clip'], error_if_nonfinite=True)
            optimizer.step()
            if step == 0 or (step + 1) % 16 == 0: curves.append([step + 1, float(loss.detach())])
            base.require(time.process_time() - cpu0 <= config['fit']['cpu_seconds_per_fit'], 'lexical CPU limit exceeded')
        digest = fingerprint(net.state_dict()); name = f'grounded-{seed}.json'
        checkpoints[f'grounded/{seed}'] = {'file': name, 'state_sha256': digest, **io._write(output / name,
            {'arm': 'grounded', 'seed': seed, 'parent_sha256': parent['sha256'], 'state_sha256': digest,
             'state': {k: v.detach().tolist() for k, v in net.state_dict().items()}})}
        reports[f'grounded/{seed}'] = {'initial_sha256': initial, 'final_sha256': digest,
            'parent_sha256': parent['sha256'], 'optimizer': 'fresh_Adam', 'parameters': 474,
            'updates': step + 1, 'training_forecasts_per_update': count, 'curve': curves,
            'cpu_seconds': time.process_time() - cpu0, 'wall_seconds': time.perf_counter() - wall0}
        base.require(fingerprint(world.state_dict()) == before, 'native world weights changed')
        print(json.dumps({'fit': f'grounded/{seed}', **reports[f'grounded/{seed}']}), flush=True)
    io._write(output / 'training.json', {'version': config['version'], 'complete': True,
        'freeze_sha256': io._hash(data / 'freeze.json'), 'checkpoints': checkpoints, 'reports': reports,
        'training_input_sha256': base.digest(inputs), 'world_checkpoints_unchanged':
        previous.old.checkpoints(config) == freeze['checkpoints'], 'resources': {
            'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - start,
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}})


def view_features(group, event, view):
    """Evaluator intervention on one current lexeme, never candidate supervision."""
    import torch
    from .bilingual_model import tokenize_batch
    base.require(view in VIEWS, 'unknown lexical view')
    if view == 'masked':
        features = event['features'].clone(); features[:, :, 1:] = 0.; return features
    from .lexical_data import swap_lexeme, borrow_lexeme
    change = swap_lexeme if view == 'swapped' else borrow_lexeme
    texts = [change(r['utterances'][-1]['text'], r['entities']) for r in group['records']]
    features, mentions = tokenize_batch(texts, [r['entities'] for r in group['records']])
    base.require(torch.equal(mentions, event['mentions']), 'lexical control changed entity occurrences')
    return features


def paired_forecasts(net, world, group):
    """All final views share the exact updated-encoder prefix and live prior."""
    from .bilingual_model import combine
    state = group['state']
    for t, event in enumerate(group['events']):
        options = event['likelihood'] + state[:, None, :, None]
        order = net(event['features']); raw, pending = combine(order, options)
        yield 'grounded', t, raw, order
        if t == len(group['events']) - 1:
            for view in VIEWS:
                alt_order = net(view_features(group, event, view)); alt, _ = combine(alt_order, options)
                yield view, t, alt, alt_order
        if t + 1 < len(group['events']): state = world.receive(pending, event['post'])


def collect(data, fitted, output):
    import torch
    from .joint_objective import fingerprint
    config, freeze = verify(data); io._committed(fitted / 'training.json'); runtime = io._runtime(config)
    trained = io._read(fitted / 'training.json')
    expected = {f'grounded/{seed}' for seed in config['model_seeds']}
    base.require(trained['complete'] is True and trained['world_checkpoints_unchanged'] is True and
        trained['version'] == config['version'] and trained['freeze_sha256'] == io._hash(data / 'freeze.json') and
        set(trained['checkpoints']) == set(trained['reports']) == expected, 'lexical fit binding/inventory differs')
    nets = {}
    for seed in config['model_seeds']:
        key = f'grounded/{seed}'; parent = freeze['language_checkpoints'][str(seed)]; report = trained['reports'][key]
        base.require(report['updates'] == config['fit']['updates'] and
            report['training_forecasts_per_update'] == config['fit']['training_forecasts_per_update'] and
            report['initial_sha256'] == parent['state_sha256'] and report['parent_sha256'] == parent['sha256'] and
            report['final_sha256'] == trained['checkpoints'][key]['state_sha256'], 'incomplete or substituted lexical fit')
        nets[seed] = load_encoder(fitted, trained['checkpoints'][key], seed, parent_sha256=parent['sha256']).eval()
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'attempt.json': io._write(output / 'attempt.json', {
        'weights_commit': io._git('rev-parse', 'HEAD'), 'runtime': runtime, 'one_attempt': True})}
    for law in previous.old.LAWS:
        inputs, retention = io._read(data / f'{law}-inputs.json.xz'), io._read(PARENT_DATA / f'{law}-inputs.json.xz')
        for seed in config['model_seeds']:
            wall0, cpu0 = time.perf_counter(), time.process_time()
            world = previous.world_for(freeze['checkpoints'], law, seed); native_hash = fingerprint(world.state_dict())
            groups, retained = previous.pack(inputs, world), previous.pack(retention, world)
            preparation = {'cpu_seconds': time.process_time() - cpu0, 'wall_seconds': time.perf_counter() - wall0}
            parent = freeze['language_checkpoints'][str(seed)]; prior = load_encoder(PARENT_FIT, parent, seed).eval()
            rows, costs, latencies = defaultdict(list), defaultdict(lambda: [0., 0.]), defaultdict(list)
            def record(stream, group):
                while True:
                    wall, cpu = time.perf_counter(), time.process_time()
                    try: arm, t, raw, order = next(stream)
                    except StopIteration: break
                    elapsed = time.perf_counter() - wall
                    costs[arm][0] += time.process_time() - cpu; costs[arm][1] += elapsed
                    latencies[arm].append(elapsed / len(raw))
                    for j, episode in enumerate(group['records']):
                        rows[arm].append({'id': episode['id'], 'step': t, 'logp': raw[j].tolist(),
                                          'order_logp': order[j].tolist()})
            with torch.no_grad():
                for group in groups:
                    record(paired_forecasts(nets[seed], world, group), group)
                    record((('prior', t, raw, order) for t, (raw, order) in enumerate(
                        previous.forecasts('grounded', prior, world, group))), group)
                for group in retained:
                    record((('retention', t, raw, order) for t, (raw, order) in enumerate(
                        previous.forecasts('grounded', nets[seed], world, group))), group)
            base.require(fingerprint(world.state_dict()) == native_hash, 'collection changed native world')
            for arm in ARMS:
                item = parent if arm == 'prior' else trained['checkpoints'][f'grounded/{seed}']
                trace = {'law': law, 'seed': seed, 'arm': arm, 'points': rows[arm],
                    'input_sha256': base.digest(retention if arm == 'retention' else inputs),
                    'freeze_sha256': io._hash(data / 'freeze.json'), 'training_sha256': io._hash(fitted / 'training.json'),
                    'checkpoint_sha256': item['sha256'], 'resources': {'cpu_seconds': costs[arm][0],
                        'wall_seconds': costs[arm][1], 'batch_amortized_latency_p95_seconds':
                        sorted(latencies[arm])[int(.95 * (len(latencies[arm]) - 1))],
                        'native_cache_preparation_shared_once': preparation if arm == 'grounded' else None,
                        'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                        'scope': 'Cached forecast chunks; control prefixes reuse grounded computation. Preparation shared; serialization excluded; not single-request latency.'}}
                name = f'trace-{law}-{seed}-{arm}.json.xz'; artifacts[name] = io._write(output / name, trace)
            print(json.dumps({'collected': f'{law}/{seed}', 'rows': {k: len(v) for k, v in rows.items()}}), flush=True)
    from .lexical_scoring import evaluate  # No challenge oracle or old prediction is decoded before all traces persist.
    wall, cpu = time.perf_counter(), time.process_time(); report = evaluate(data, output, config, freeze, fitted)
    report['evaluator_resources'] = {'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - wall}
    artifacts['summary.json.xz'] = io._write(output / 'summary.json.xz', report)
    artifacts['decision.json'] = io._write(output / 'decision.json', report['decision'])
    io._write(output / 'manifest.json', {'artifacts': artifacts, 'execution_complete': True,
        'world_checkpoints_unchanged': previous.old.checkpoints(config) == freeze['checkpoints']})
    print(json.dumps(report['decision']), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'fit', 'collect'))
    parser.add_argument('--data', type=Path); parser.add_argument('--fitted', type=Path)
    parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    if args.stage != 'prepare' and args.data is None: parser.error('--data required')
    if args.stage == 'collect' and args.fitted is None: parser.error('--fitted required')
    existed = args.output.exists()
    try:
        if args.stage == 'prepare': prepare(args.output)
        elif args.stage == 'fit': fit(args.data, args.output)
        else: collect(args.data, args.fitted, args.output)
    except BaseException as error:
        if not existed and args.output.is_dir() and not (args.output / 'failure.json').exists():
            io._write(args.output / 'failure.json', {'stage': args.stage, 'type': type(error).__name__,
                'message': str(error), 'traceback': traceback.format_exc(), 'retry_permitted': False})
            if args.stage != 'prepare' and not (args.output / 'decision.json').exists():
                io._write(args.output / 'decision.json', {'decision': 'STOP_INCOMPLETE_EXECUTION',
                    'execution_complete': False, 'stage': args.stage, 'retry_permitted': False, 'scientific_admission': False})
        raise


if __name__ == '__main__': main()
