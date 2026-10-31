"""Freeze -> fit once -> publish weights -> collect once, with old worlds frozen."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import resource
import time
import traceback

from . import acceptance_contract as base, continuation_run as io, hidden_cycle_run as old

ROOT = io.ROOT
PROTOCOL = ROOT / 'bilingual_protocol_v1.json'
ARMS = ('grounded', 'parser', 'sequence', 'text_only', 'ungrounded')


def protocol():
    return base.load_json(PROTOCOL, (ROOT / 'snapshots/bilingual_protocol_v1.sha256').read_text().split()[0])


def sources():
    names = set(old.sources()) | {'bilingual_model.py', 'bilingual_contract.py', 'bilingual_data.py', 'bilingual_run.py',
        'bilingual_scoring.py', PROTOCOL.name, 'snapshots/bilingual_protocol_v1.sha256'}
    return {name: io._hash(ROOT / name) for name in sorted(names)}


def prepare(output):
    from .bilingual_data import build_assets
    config = protocol()
    assets, inventory = build_assets(config), old.checkpoints(config)
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {}
    banks = {'train': assets['train'], **assets['challenge']}
    for split, bank in banks.items():
        for kind, value in bank.items():
            name = f'{split}-{kind}.json.xz'
            artifacts[name] = io._write(output / name, value)
    labels = {e['id']: e['action_orders'] for e in assets['train']['oracle']['episodes']}
    artifacts['parser-labels.json'] = io._write(output / 'parser-labels.json', labels)
    artifacts['audit.json'] = io._write(output / 'audit.json', assets['audit'])
    base.require(assets['audit']['train']['forecasts'] == 384 and
                 all(assets['audit'][law]['forecasts'] == 2080 for law in old.LAWS), 'bank size differs')
    io._write(output / 'freeze.json', {'version': config['version'], 'sources': sources(),
        'artifacts': artifacts, 'checkpoints': inventory, 'protocol_sha256': io._hash(PROTOCOL),
        'train_law': 'nand', 'transfer_law': 'nor', 'world_fitting_permitted': False})
    print(json.dumps({'prepared': str(output), 'audit': assets['audit']}), flush=True)


def verify(data):
    io._committed(data / 'freeze.json')
    config, freeze = protocol(), io._read(data / 'freeze.json')
    base.require(freeze['sources'] == sources() and freeze['protocol_sha256'] == io._hash(PROTOCOL),
                 'frozen language source/protocol differs')
    base.require(freeze['checkpoints'] == old.checkpoints(config), 'acquired world checkpoints differ')
    for name, item in freeze['artifacts'].items():
        base.require(io._hash(data / name) == item['sha256'], 'prepared artifact differs: ' + name)
    return config, freeze


def world_for(inventory, law, seed, *, untrained=False):
    import torch
    from .active_checkpoint import load_checkpoint
    from .bilingual_model import freeze_world
    from .domain_kernel import DomainKernel
    item = inventory[law][str(seed)]
    world = load_checkpoint(old.FITTED / item['file'], item['sha256'])['model']
    if untrained:
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed + 1000)
            world = DomainKernel(hidden=world.pair[0].out_features, persistence=world.persistence,
                                 role_tying=world.role_tying, memory=world.memory)
    return freeze_world(world)


def pack(inputs, world):
    """Cache native likelihoods using only observed prefixes, never hidden actions."""
    import torch
    from . import bilingual_model as model, domain_contract as domain
    from .bilingual_contract import validate_inputs
    grouped = defaultdict(list)
    for episode in validate_inputs(inputs)['episodes']:
        grouped[len(episode['entities']), len(episode['utterances']), len(episode['context'])].append(episode)
    result = []
    for (n, steps, context_steps), records in sorted(grouped.items()):
        tensor = lambda value: torch.tensor(value, dtype=torch.float64)
        pre = tensor([r['anchor'] for r in records])
        state = world.initial(len(records))
        for t in range(context_steps):
            action = torch.tensor([r['context'][t]['action'] for r in records], dtype=torch.long)
            post = tensor([r['context'][t]['reading'] for r in records])
            with torch.no_grad():
                _, pending = world.predict(pre, action, state)
                state = world.receive(pending, post)
            pre = post
        group = {'n': n, 'records': records, 'state': state.detach(), 'events': []}
        for t in range(steps):
            features, mentions = model.tokenize_batch([r['utterances'][t]['text'] for r in records],
                                                       [r['entities'] for r in records])
            uniform = world.initial(len(records))
            likelihood = model.frozen_options(world, pre, uniform, mentions) - uniform[:, None, :, None]
            post = tensor([r['utterances'][t]['reading'] for r in records])
            args = (pre, tensor([r['anchor'] for r in records]),
                torch.tensor([r['context'][0]['action'] for r in records], dtype=torch.long),
                tensor([r['context'][0]['reading'] for r in records]), mentions)
            group['events'].append({'features': features, 'mentions': mentions,
                'likelihood': likelihood, 'post': post, 'target': domain.world_index(post),
                'context': model.make_context(*args), 'text_context': model.make_context(*args, text_only=True)})
            pre = post
        result.append(group)
    return result


def learner(arm, seed):
    import torch
    from .bilingual_model import OrderEncoder, SequenceControl
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        return SequenceControl() if arm in ('sequence', 'text_only') else OrderEncoder()


def forecasts(arm, net, world, group):
    """Yield before using that event's reading; feedback affects only the next event."""
    from .bilingual_model import combine
    state = group['state']
    for event in group['events']:
        if arm in ('sequence', 'text_only'):
            key = 'text_context' if arm == 'text_only' else 'context'
            raw = net(event['features'], event[key], group['n'])
            order, pending = None, None
        else:
            order = net(event['features'])
            # Shuffling reverses only the two entity names in the message; generic
            # token features stay identical, so the two action weights are swapped.
            if arm == 'shuffled': order = order.flip(-1)
            raw, pending = combine(order, event['likelihood'] + state[:, None, :, None])
        yield raw, order
        if pending is not None: state = world.receive(pending, event['post'])


def fit(data, output):
    import torch
    from .joint_objective import fingerprint
    config, freeze = verify(data)
    runtime = io._runtime(config)
    output.mkdir(parents=True, exist_ok=False)
    io._write(output / 'attempt.json', {'source_data_commit': io._git('rev-parse', 'HEAD'),
        'freeze_sha256': io._hash(data / 'freeze.json'), 'runtime': runtime, 'one_attempt': True})
    inputs = io._read(data / 'train-inputs.json.xz')
    reports, checkpoints = {}, {}
    total_start, total_cpu = time.perf_counter(), time.process_time()
    for seed in config['model_seeds']:
        world = world_for(freeze['checkpoints'], 'nand', seed)
        world_hash = fingerprint(world.state_dict())
        groups = pack(inputs, world)
        for arm in ARMS:
            native = world_for(freeze['checkpoints'], 'nand', seed, untrained=True) if arm == 'ungrounded' else world
            batches = pack(inputs, native) if arm == 'ungrounded' else groups
            labels = io._read(data / 'parser-labels.json') if arm == 'parser' else None
            net = learner(arm, seed)
            initial = fingerprint(net.state_dict())
            optimizer = torch.optim.Adam(net.parameters(), lr=config['fit']['learning_rate'])
            curves, start, cpu = [], time.perf_counter(), time.process_time()
            for step in range(config['fit']['updates']):
                optimizer.zero_grad(set_to_none=True)
                loss, count = 0., 0
                for group in batches:
                    for t, ((raw, order), event) in enumerate(zip(forecasts(arm, net, native, group), group['events'], strict=True)):
                        if labels is not None:
                            target = torch.tensor([labels[r['id']][t] for r in group['records']], dtype=torch.long)
                            loss = loss - order.gather(1, target[:, None]).sum()
                        else:
                            loss = loss - raw.gather(1, event['target'][:, None]).sum()
                        count += len(raw)
                loss = loss / count
                base.require(bool(torch.isfinite(loss)), 'nonfinite training objective')
                loss.backward()
                torch.nn.utils.clip_grad_norm_(net.parameters(), config['fit']['gradient_clip'], error_if_nonfinite=True)
                optimizer.step()
                if step == 0 or (step + 1) % 16 == 0: curves.append([step + 1, float(loss.detach())])
                base.require(time.process_time() - cpu <= config['fit']['cpu_seconds_per_fit'], 'fit CPU limit exceeded')
            name = f'{arm}-{seed}.json'
            state = {k: v.detach().tolist() for k, v in net.state_dict().items()}
            checkpoints[f'{arm}/{seed}'] = {'file': name, **io._write(output / name, {
                'arm': arm, 'seed': seed, 'state': state, 'state_sha256': fingerprint(net.state_dict())})}
            reports[f'{arm}/{seed}'] = {'initial_sha256': initial, 'final_sha256': fingerprint(net.state_dict()),
                'parameters': sum(p.numel() for p in net.parameters()), 'updates': step + 1,
                'training_forecasts_per_update': count, 'curve': curves,
                'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - start,
                'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
            base.require(fingerprint(world.state_dict()) == world_hash, 'acquired weights changed')
            print(json.dumps({'fit': f'{arm}/{seed}', **reports[f'{arm}/{seed}']}), flush=True)
    io._write(output / 'training.json', {'version': config['version'], 'complete': True,
        'freeze_sha256': io._hash(data / 'freeze.json'), 'checkpoints': checkpoints, 'reports': reports,
        'training_input_sha256': base.digest(inputs), 'resources': {
            'cpu_seconds': time.process_time() - total_cpu, 'wall_seconds': time.perf_counter() - total_start,
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'scope': 'All cache preparation, 25 fits and checkpoint serialization; no world fitting.'},
        'world_checkpoints_unchanged': old.checkpoints(config) == freeze['checkpoints']})


def collect(data, fitted, output):
    import torch
    from .joint_objective import fingerprint
    config, freeze = verify(data)
    io._committed(fitted / 'training.json')
    runtime = io._runtime(config)
    trained = io._read(fitted / 'training.json')
    base.require(trained['complete'] and trained['freeze_sha256'] == io._hash(data / 'freeze.json'), 'fit binding differs')
    expected = {f'{arm}/{seed}' for arm in ARMS for seed in config['model_seeds']}
    base.require(set(trained['checkpoints']) == set(trained['reports']) == expected and
        trained['world_checkpoints_unchanged'] is True, 'fit inventory differs')
    for key, report in trained['reports'].items():
        arm, seed = key.split('/')
        item = trained['checkpoints'][key]
        base.require(item['file'] == f'{arm}-{seed}.json' and
            io._hash(fitted / item['file']) == item['sha256'] and
            report['updates'] == config['fit']['updates'] and report['training_forecasts_per_update'] == 384,
            'incomplete or substituted language fit: ' + key)
        saved = io._read(fitted / item['file'])
        base.require(saved['arm'] == arm and saved['seed'] == int(seed) and
            saved['state_sha256'] == report['final_sha256'], 'language checkpoint identity differs')
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'attempt.json': io._write(output / 'attempt.json', {
        'weights_commit': io._git('rev-parse', 'HEAD'), 'runtime': runtime, 'one_attempt': True})}
    for law in old.LAWS:
        inputs = io._read(data / f'{law}-inputs.json.xz')
        for seed in config['model_seeds']:
            pack_start, pack_cpu = time.perf_counter(), time.process_time()
            world = world_for(freeze['checkpoints'], law, seed)
            groups = pack(inputs, world)
            shared_pack_cost = {'cpu_seconds': time.process_time() - pack_cpu,
                               'wall_seconds': time.perf_counter() - pack_start}
            for arm in (*ARMS, 'shuffled'):
                fit_arm = 'grounded' if arm == 'shuffled' else arm
                item = trained['checkpoints'][f'{fit_arm}/{seed}']
                base.require(io._hash(fitted / item['file']) == item['sha256'], 'language checkpoint bytes differ')
                saved, net = io._read(fitted / item['file']), learner(fit_arm, seed)
                net.load_state_dict({k: torch.tensor(v, dtype=torch.float64) for k, v in saved['state'].items()})
                base.require(fingerprint(net.state_dict()) == saved['state_sha256'], 'language tensors differ')
                native = world_for(freeze['checkpoints'], law, seed, untrained=True) if arm == 'ungrounded' else world
                pack_start, pack_cpu = time.perf_counter(), time.process_time()
                batches = pack(inputs, native) if arm == 'ungrounded' else groups
                pack_cost = {'cpu_seconds': time.process_time() - pack_cpu,
                             'wall_seconds': time.perf_counter() - pack_start} if arm == 'ungrounded' else shared_pack_cost
                rows, latencies, start, cpu = [], [], time.perf_counter(), time.process_time()
                with torch.no_grad():
                    for group in batches:
                        stream = forecasts(arm, net, native, group)
                        for t, event in enumerate(group['events']):
                            before = time.perf_counter(); raw, order = next(stream)
                            latencies.append((time.perf_counter() - before) / len(raw))
                            for j, record in enumerate(group['records']):
                                rows.append({'id': record['id'], 'step': t, 'logp': raw[j].tolist(),
                                             'order_logp': None if order is None else order[j].tolist()})
                        base.require(next(stream, None) is None, 'unexpected forecast after final feedback')
                trace = {'law': law, 'seed': seed, 'arm': arm, 'points': rows,
                    'input_sha256': base.digest(inputs), 'freeze_sha256': io._hash(data / 'freeze.json'),
                    'training_sha256': io._hash(fitted / 'training.json'),
                    'checkpoint_sha256': item['sha256'], 'resources': {
                    'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - start,
                    'batch_amortized_latency_p95_seconds': sorted(latencies)[int(.95 * (len(latencies) - 1))],
                    'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                    'native_cache_and_tokenization': pack_cost,
                    'scope': 'Forecast loop with cached native likelihoods; preparation cost separately recorded, shared across arms. Batch-amortized latency is not single-request latency.'}}
                name = f'trace-{law}-{seed}-{arm}.json.xz'
                artifacts[name] = io._write(output / name, trace)
            print(json.dumps({'collected': f'{law}/{seed}', 'arms': len(ARMS) + 1}), flush=True)
    # All model traces are durable before opening any challenge oracle.
    from .bilingual_scoring import evaluate
    score_start, score_cpu = time.perf_counter(), time.process_time()
    report = evaluate(data, output, config, freeze)
    report['evaluator_resources'] = {'cpu_seconds': time.process_time() - score_cpu,
        'wall_seconds': time.perf_counter() - score_start,
        'scope': 'Post-collection scoring and separate gold-action native reference; not candidate inference or fitting.'}
    artifacts['summary.json.xz'] = io._write(output / 'summary.json.xz', report)
    artifacts['decision.json'] = io._write(output / 'decision.json', report['decision'])
    io._write(output / 'manifest.json', {'artifacts': artifacts, 'execution_complete': True,
        'world_checkpoints_unchanged': old.checkpoints(config) == freeze['checkpoints']})
    print(json.dumps(report['decision']), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'fit', 'collect'))
    parser.add_argument('--data', type=Path)
    parser.add_argument('--fitted', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
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
                    'execution_complete': False, 'stage': args.stage, 'retry_permitted': False,
                    'scientific_admission': False})
        raise


if __name__ == '__main__': main()
