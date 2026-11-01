"""One prospective response-coordinate study; frozen inference/metrics are reused.

Publication SHAs are externally checked attestations, not offline authentication.
Exclusive stage directories retain failures; no resume, retry or best-seed choice.
"""
import argparse
import json
import math
from pathlib import Path
import resource
import time
import traceback

from . import acceptance_contract as c, continuation_run as io, bilingual_run as prior
from . import binding_study as old, centering_run as previous
from .bilingual_contract import validate_inputs

ARMS = ('centered', 'coordinates')
PARAMETERS = {'centered': 89, 'coordinates': 88}
BANKS = {**previous.BANKS, 'centering_retention': 'centering-v1'}
PROTOCOL = io.ROOT / 'coordinate_protocol_v1.json'


def protocol():
    return c.load_json(PROTOCOL, (io.ROOT / 'snapshots/coordinate_protocol_v1.sha256').read_text().split()[0])


def sources():
    names = set(previous.sources()) | {'binding_layout_coordinates.py', 'coordinate_data.py',
        'coordinate_run.py', 'coordinate_scoring.py', PROTOCOL.name, 'snapshots/coordinate_protocol_v1.sha256'}
    return {name: io._hash(io.ROOT / name) for name in sorted(names)}


def prepare(output):
    from .coordinate_data import build_assets
    config, assets = protocol(), build_assets()
    c.require(assets['audit']['train_forecasts'] == config['train_forecasts'] and
        assets['audit']['challenge_forecasts_per_law'] == config['challenge_forecasts_per_law'], 'bank count differs')
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'train-inputs.json.xz': io._write(output / 'train-inputs.json.xz', assets['train'])}
    for law in ('nand', 'nor'):
        for kind in ('inputs', 'oracle'):
            name = f'{law}-{kind}.json.xz'; artifacts[name] = io._write(output / name, assets[law][kind])
    c.require(io._hash(output / 'train-inputs.json.xz') ==
        io._hash(io.ROOT / 'data/saturation-v1/train-inputs.json.xz'), 'training tape changed')
    artifacts['audit.json'] = io._write(output / 'audit.json', assets['audit'])
    earlier = io._read(io.ROOT / 'data/centering-v1/freeze.json')
    historical = dict(earlier['historical'])
    paths = list((io.ROOT / 'data/centering-v1').glob('*'))
    paths += list((io.ROOT / 'results/centering-v1/traces').glob('trace-*-centered-fresh.json.xz'))
    paths += [io.ROOT / 'data/centering-fit-v1/checkpoints.json.xz']
    for path in paths:
        if path.is_file(): historical[path.relative_to(io.ROOT).as_posix()] = io._hash(path)
    io._write(output / 'freeze.json', {'version': config['version'], 'sources': sources(),
        'artifacts': artifacts, 'checkpoints': earlier['checkpoints'], 'historical': historical,
        'protocol_sha256': io._hash(PROTOCOL), 'audit': assets['audit']})


def verify(data):
    config, freeze = protocol(), io._read(data / 'freeze.json')
    commitment = io._read(io.ROOT / 'coordinate_freeze_v1.json')
    c.require(set(commitment) == set(freeze['artifacts']) | {'freeze.json'}, 'data commitment inventory differs')
    for name, digest in commitment.items():
        c.require(io._hash(data / name) == digest, 'public data commitment differs: ' + name)
    c.require(freeze['version'] == config['version'] and freeze['sources'] == sources() and
              freeze['protocol_sha256'] == io._hash(PROTOCOL), 'source/protocol freeze differs')
    for name, item in freeze['artifacts'].items():
        c.require(io._hash(data / name) == item['sha256'], 'data bytes differ')
    for name, digest in freeze['historical'].items():
        c.require(io._hash(io.ROOT / name) == digest, 'historical bytes differ: ' + name)
    for group in freeze['checkpoints'].values():
        for item in group.values():
            c.require(io._hash(prior.old.FITTED / item['file']) == item['sha256'], 'world checkpoint differs')
    return config, freeze


def encoder(arm, seed):
    from .binding_centered_init import centered_encoder
    from .binding_layout_coordinates import coordinate_encoder
    c.require(arm in ARMS, 'unknown coordinate arm')
    return (coordinate_encoder if arm == 'coordinates' else centered_encoder)(seed)


def initial_pair(seed):
    """Verify shared tensors and equal functions on every legal identity mask.

    All 85 lexical/readout scalars are identical; the three layout responses
    are equal. Together these establish equivalence for every legal lexical
    feature vector, not just the synthetic basis probes also checked here.
    """
    import torch
    from .joint_objective import DTYPE, fingerprint
    models = {arm: encoder(arm, seed) for arm in ARMS}
    standard, candidate = (models[arm].state_dict() for arm in ARMS)
    other = {k: v for k, v in standard.items() if not k.startswith('layout.')}
    c.require(set(candidate) == set(standard) - {'layout.0.bias'} and
        all(sum(p.numel() for p in models[arm].parameters()) == PARAMETERS[arm] for arm in ARMS),
        'paired parameter inventory differs')
    c.require(sum(v.numel() for v in other.values()) == 85 and
        all(torch.equal(v, candidate[k]) for k, v in other.items()), 'non-layout initial tensors differ')
    masks = torch.ones(3, 3, dtype=DTYPE) - torch.eye(3, dtype=DTYPE)
    with torch.no_grad():
        responses = {'centered': models['centered'].layout[0](masks).flatten(),
                     'coordinates': models['coordinates'].layout[0](1. - masks).flatten()}
        c.require(torch.equal(candidate['layout.0.weight'], responses['centered'][None]) and
                  torch.equal(responses['centered'], responses['coordinates']), 'initial layout response differs')
        lexical = torch.cat((torch.zeros(1, 8, dtype=DTYPE), torch.eye(8, dtype=DTYPE), -torch.eye(8, dtype=DTYPE)))
        features = torch.zeros(3 * len(lexical), 3, 9, dtype=DTYPE)
        features[:, :, 0] = masks.repeat_interleave(len(lexical), 0)
        features[torch.arange(len(features)), torch.arange(3).repeat_interleave(len(lexical)), 1:] = lexical.repeat(3, 1)
        c.require(torch.allclose(models['centered'](features), models['coordinates'](features),
                                rtol=0., atol=1e-14), 'initial function differs on lexical basis')
    return models, {'parameters': dict(PARAMETERS), 'unchanged_scalars': 85,
        'shared_sha256': fingerprint(other), 'layout_masks': masks.tolist(),
        'layout_responses': {arm: values.tolist() for arm, values in responses.items()},
        'initial_sha256': {arm: fingerprint(net.state_dict()) for arm, net in models.items()},
        'states': {arm: {k: v.detach().tolist() for k, v in net.state_dict().items()}
                   for arm, net in models.items()}}


def verify_control_reproduction(states, reports, archive):
    """Check saved mathematical control results; never refit an archived model."""
    matches = {}
    for seed, report in reports.items():
        key = 'centered/' + seed
        current, prior_report = report['reports']['centered'], archive['reports'][seed]['reports']['centered']
        fields = ('parameters', 'initial_sha256', 'final_sha256', 'updates',
                  'observed_events_per_update', 'curve', 'final_observed_train_nll')
        c.require(all(current[k] == prior_report[k] for k in fields) and
            states[key] == archive['checkpoints'][key] and
            all(report[k] == archive['reports'][seed][k] for k in ('training_input_sha256', 'world_state_sha256')) and
            report['initialization']['states']['centered'] == archive['reports'][seed]['initialization']['states']['centered'],
            'centered control does not reproduce archived fit: ' + seed)
        matches[seed] = {'initial_sha256': current['initial_sha256'],
                         'final_sha256': current['final_sha256'], 'matched': True}
    return matches


def _control_receipt(states, reports):
    path = io.ROOT / 'data/centering-fit-v1/checkpoints.json.xz'
    return {'archive_sha256': io._hash(path),
            'matches': verify_control_reproduction(states, reports, io._read(path))}


# Frozen outcome objective and canonical-prefix controls, reused without patches.
from .saturation_run import loss, probes


def fit_pair(observed, world, seed, settings):
    import torch
    from .domain_kernel import DomainKernel
    from .joint_objective import fingerprint
    c.require(type(world) is DomainKernel and world.memory and all(not p.requires_grad for p in world.parameters())
        and all(not m.training for m in world.modules()), 'frozen persistent evaluation world required')
    c.require(type(settings['updates']) is int and 1 <= settings['updates'] <= 4096, 'invalid updates')
    for key in ('learning_rate', 'gradient_clip', 'cpu_seconds_per_arm'):
        c.require(type(settings[key]) in (int, float) and math.isfinite(settings[key]) and settings[key] > 0, 'invalid ' + key)
    observed = validate_inputs(observed); groups = prior.pack(observed, world)
    expected = sum(len(r['utterances']) for r in observed['episodes'])
    before = fingerprint(world.state_dict()); models, reports = {}, {}
    initialized, initialization = initial_pair(seed)
    with torch.no_grad():
        for group in groups:
            for event in group['events']:
                c.require(torch.allclose(initialized['centered'](event['features']),
                    initialized['coordinates'](event['features']), rtol=0., atol=1e-14),
                    'initial predictions differ on observed training features')
    try:
        for arm in ARMS:
            net = initialized[arm]; initial = fingerprint(net.state_dict())
            c.require(sum(p.numel() for p in net.parameters()) == PARAMETERS[arm], 'parameter inventory differs')
            optimizer = torch.optim.Adam(net.parameters(), lr=settings['learning_rate'])
            wall, cpu = time.perf_counter(), time.process_time(); curve = []
            for step in range(settings['updates']):
                optimizer.zero_grad(set_to_none=True); value, count = loss(net, world, groups)
                c.require(count == expected and bool(torch.isfinite(value)), 'training exposure/objective differs')
                value.backward()
                torch.nn.utils.clip_grad_norm_(net.parameters(), settings['gradient_clip'], error_if_nonfinite=True)
                optimizer.step()
                c.require(all(bool(torch.isfinite(p).all()) for p in net.parameters()), 'nonfinite update')
                if step == 0 or (step + 1) % 16 == 0 or step + 1 == settings['updates']:
                    curve.append([step + 1, float(value.detach())])
                c.require(time.process_time() - cpu <= settings['cpu_seconds_per_arm'], 'training CPU limit exceeded')
            net.eval()
            with torch.no_grad(): final, _ = loss(net, world, groups)
            c.require(bool(torch.isfinite(final)), 'nonfinite final training diagnostic')
            models[arm] = net
            reports[arm] = {'parameters': PARAMETERS[arm], 'initial_sha256': initial, 'final_sha256': fingerprint(net.state_dict()),
                'updates': settings['updates'], 'observed_events_per_update': expected, 'curve': curve,
                'final_observed_train_nll': float(final), 'cpu_seconds': time.process_time() - cpu,
                'wall_seconds': time.perf_counter() - wall}
    finally: c.require(fingerprint(world.state_dict()) == before, 'frozen world changed')
    return models, {'reports': reports, 'initialization': initialization,
        'training_input_sha256': c.digest(observed), 'world_state_sha256': before}


def fit(data, output, published):
    config, freeze = verify(data); runtime = io._runtime(config)
    output.mkdir(parents=True, exist_ok=False)
    identity = {'source_publication': old.publication(published), 'runtime': runtime,
                'freeze_sha256': io._hash(data / 'freeze.json')}
    io._write(output / 'attempt.json', identity)
    observed = io._read(data / 'train-inputs.json.xz'); states, reports = {}, {}
    start, cpu = time.perf_counter(), time.process_time()
    for seed in config['model_seeds']:
        world = prior.world_for(freeze['checkpoints'], 'nand', seed)
        models, report = fit_pair(observed, world, seed, config['fit']); reports[str(seed)] = report
        for arm, net in models.items():
            c.require(report['reports'][arm]['observed_events_per_update'] == config['train_forecasts'], 'exposure differs')
            states[f'{arm}/{seed}'] = {'arm': arm, 'seed': seed,
                'state_sha256': report['reports'][arm]['final_sha256'],
                'state': {k: v.detach().tolist() for k, v in net.state_dict().items()}}
        io._write(output / f'completed-{seed}.json', {**report,
            'checkpoints': {arm: states[f'{arm}/{seed}'] for arm in ARMS}})
        print(json.dumps({'completed_seed': seed, 'reports': report['reports']}), flush=True)
    verify(data)
    io._write(output / 'checkpoints.json.xz', {**identity, 'version': config['version'], 'complete': True,
        'reports': reports, 'checkpoints': states, 'control_reproduction': _control_receipt(states, reports), 'resources': {'cpu_seconds': time.process_time() - cpu,
        'wall_seconds': time.perf_counter() - start, 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}})


def load_models(fitted, config, data):
    import torch
    from .joint_objective import fingerprint
    saved = io._read(fitted / 'checkpoints.json.xz')
    expected = {f'{arm}/{seed}' for arm in ARMS for seed in config['model_seeds']}
    c.require(saved['complete'] is True and saved['version'] == config['version'] and
        saved['freeze_sha256'] == io._hash(data / 'freeze.json') and set(saved['checkpoints']) == expected and
        set(saved['reports']) == {str(s) for s in config['model_seeds']}, 'incomplete/substituted fit inventory')
    old.publication(saved['source_publication']); result = {}
    initials = {str(seed): initial_pair(seed) for seed in config['model_seeds']}
    observed_hash = c.digest(validate_inputs(io._read(data / 'train-inputs.json.xz')))
    for key, item in saved['checkpoints'].items():
        arm, textseed = key.split('/'); seed = int(textseed); report = saved['reports'][textseed]['reports'][arm]
        c.fields(item, ('arm', 'seed', 'state_sha256', 'state'))
        c.require(type(item['seed']) is int and item['arm'] == arm and item['seed'] == seed and
            type(report['updates']) is int and report['updates'] == config['fit']['updates'] and
            report['parameters'] == PARAMETERS[arm] and report['observed_events_per_update'] == config['train_forecasts'] and
            saved['reports'][textseed]['training_input_sha256'] == observed_hash, 'fit identity/exposure differs')
        initial_models, receipt = initials[textseed]
        net = initial_models[arm]
        c.require(saved['reports'][textseed]['initialization'] == receipt and
            fingerprint(net.state_dict()) == report['initial_sha256'], 'paired initial state differs')
        net.load_state_dict({k: torch.tensor(v, dtype=torch.float64) for k, v in item['state'].items()}, strict=True)
        c.require(fingerprint(net.state_dict()) == item['state_sha256'] == report['final_sha256'] and
            all(bool(torch.isfinite(p).all()) for p in net.parameters()), 'fit state differs')
        result[key] = net.eval().requires_grad_(False)
    c.require(saved['control_reproduction'] == _control_receipt(saved['checkpoints'], saved['reports']),
              'archived control reproduction receipt differs')
    return result


def collect(data, fitted, output, published):
    import torch
    from .joint_objective import fingerprint
    config, freeze = verify(data); runtime = io._runtime(config); models = load_models(fitted, config, data)
    output.mkdir(parents=True, exist_ok=False)
    identity = {'weights_publication': old.publication(published), 'runtime': runtime,
        'freeze_sha256': io._hash(data / 'freeze.json'), 'checkpoint_sha256': io._hash(fitted / 'checkpoints.json.xz')}
    io._write(output / 'attempt.json', identity); artifacts = {}
    for law in ('nand', 'nor'):
        inputs = {'fresh': io._read(data / f'{law}-inputs.json.xz'), **{bank: io._read(
            io.ROOT / 'data' / folder / f'{law}-inputs.json.xz') for bank, folder in BANKS.items()}}
        for seed in config['model_seeds']:
            world = prior.world_for(freeze['checkpoints'], law, seed); before = fingerprint(world.state_dict())
            for bank, observed in inputs.items():
                groups = prior.pack(observed, world)
                for arm in ARMS:
                    net = models[f'{arm}/{seed}']; tensor_hash = fingerprint(net.state_dict()); points, latency = [], []
                    wall, cpu = time.perf_counter(), time.process_time()
                    with torch.no_grad():
                        for group in groups:
                            stream = probes(net, world, group) if bank == 'fresh' else (
                                ('canonical', t, raw, order) for t, (raw, order) in enumerate(prior.forecasts('grounded', net, world, group)))
                            iterator = iter(stream)
                            while True:
                                started = time.perf_counter()
                                try: view, t, raw, order = next(iterator)
                                except StopIteration: break
                                latency.append((time.perf_counter() - started) / len(raw))
                                points.extend({'id': r['id'], 'step': t, 'view': view,
                                    'logp': raw[j].tolist(), 'order_logp': order[j].tolist()} for j, r in enumerate(group['records']))
                    c.require(fingerprint(net.state_dict()) == tensor_hash and fingerprint(world.state_dict()) == before, 'weights changed')
                    name = f'trace-{law}-{seed}-{arm}-{bank}.json.xz'
                    artifacts[name] = io._write(output / name, {**identity, 'law': law, 'seed': seed, 'arm': arm,
                        'bank': bank, 'state_sha256': tensor_hash, 'input_sha256': c.digest(observed), 'points': points,
                        'resources': {'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - wall,
                        'batch_amortized_p95_seconds': sorted(latency)[int(.95 * (len(latency) - 1))],
                        'scope': 'Cached batched prediction only; not service latency or total preparation cost.',
                        'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}})
            print(json.dumps({'collected': f'{law}/{seed}'}), flush=True)
    verify(data)
    io._write(output / 'manifest.json', {**identity, 'complete': True, 'oracle_opened': False, 'artifacts': artifacts})


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
            from .coordinate_scoring import score
            score(args.data, args.fitted, args.traces, args.output)
    except BaseException as error:
        if not existed and args.output.is_dir():
            io._write(args.output / 'failure.json', {'stage': args.stage, 'error': type(error).__name__,
                'message': str(error), 'traceback': traceback.format_exc(), 'retry_permitted': False})
        raise


if __name__ == '__main__': main()
