"""Fresh native acquisition with explicit numerical retention and complete reporting.

The v1 predictor, fitter, native scorer and failed study remain byte-identical.
Only this prospective runner, data recipe, runtime receipt and retention rule vary.
"""
import argparse
import json
from pathlib import Path
import resource
import time
import traceback

from . import acceptance_contract as c, continuation_run as io, set_acquisition_run as v1
from .set_acquisition_retention_v2 import retention
from .set_acquisition_runtime_v2 import runtime, verify_runtime

ROOT = io.ROOT
BASE = '9ad9656e0f47209082556fa7f3602dc4f8ed5b54'
PROTOCOL = ROOT / 'set_acquisition_protocol_v2.json'
LOCK = ROOT / 'snapshots/set_acquisition_protocol_v2.sha256'
COMMITMENT = ROOT / 'set_acquisition_freeze_v2.json'
PARENTS, LANGUAGE, BANKS, ARMS, LAWS = v1.PARENTS, v1.LANGUAGE, v1.BANKS, v1.ARMS, v1.LAWS


def protocol():
    return c.load_json(PROTOCOL, LOCK.read_text().split()[0])


def sources():
    names = {'set_acquisition_data_v2.py', 'set_acquisition_run_v2.py',
        'set_acquisition_retention_v2.py', 'set_acquisition_runtime_v2.py',
        'tests/test_set_acquisition_data_v2.py', 'tests/test_set_acquisition_run_v2.py',
        'tests/test_set_acquisition_retention_v2.py', 'SET_ACQUISITION_STUDY_V2.md',
        PROTOCOL.name, 'snapshots/' + LOCK.name}
    return {**v1.sources(), **{name: io._hash(ROOT / name) for name in sorted(names)}}


def prepare(output):
    from .set_acquisition_data_v2 import build_assets, TRAIN, HISTORY
    config, assets = protocol(), build_assets()
    _, parent_freeze = v1.verify(ROOT / 'data/set-acquisition-v1')
    audit = assets['audit']
    c.require(audit['train_forecasts'] == config['train_forecasts'] and
        audit['evaluation_forecasts_per_law'] == config['fresh_forecasts_per_law'] and
        all(audit[law]['identifiable_points'] == config['identifiable_forecasts_per_law'] and
            audit[law]['ambiguous_points'] == config['ambiguous_forecasts_per_law'] for law in LAWS),
        'prospective recipe counts differ')
    numerical = runtime(config)
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'train-inputs.json.xz': io._write(output / 'train-inputs.json.xz', assets['train'])}
    for law, bundle in assets['laws'].items():
        artifacts[law + '-inputs.json.xz'] = io._write(output / (law + '-inputs.json.xz'), bundle['inputs'])
        artifacts[law + '-evaluator.json.xz'] = io._write(output / (law + '-evaluator.json.xz'),
            {k: v for k, v in bundle.items() if k != 'inputs'})
    artifacts['audit.json'] = io._write(output / 'audit.json', audit)
    historical = {**parent_freeze['historical'], **{name: io._hash(ROOT / name)
        for name in (TRAIN, *HISTORY, 'data/set-acquisition-v1/freeze.json', 'set_acquisition_freeze_v1.json')}}
    io._write(output / 'freeze.json', {'version': config['version'], 'base_commit': BASE,
        'sources': sources(), 'artifacts': artifacts, 'parents': parent_freeze['parents'],
        'historical': historical, 'runtime': numerical, 'runtime_sha256': c.digest(numerical),
        'protocol_sha256': io._hash(PROTOCOL)})
    io._write(COMMITMENT, {p.name: io._hash(p) for p in sorted(output.iterdir())})
    print(json.dumps({'prepared': str(output), 'freeze_sha256': io._hash(output / 'freeze.json')}), flush=True)


def verify(data):
    config, freeze, commitment = protocol(), io._read(data / 'freeze.json'), io._read(COMMITMENT)
    c.require(set(commitment) == set(freeze['artifacts']) | {'freeze.json'}, 'data inventory differs')
    for name, digest in commitment.items(): c.require(io._hash(data / name) == digest, 'data differs: ' + name)
    c.require(freeze['sources'] == sources() and freeze['protocol_sha256'] == io._hash(PROTOCOL) and
        freeze['version'] == config['version'] and freeze['base_commit'] == BASE and
        c.digest(freeze['runtime']) == freeze['runtime_sha256'], 'frozen source/runtime differs')
    for name, digest in freeze['historical'].items():
        c.require(io._hash(ROOT / name) == digest, 'historical bytes differ: ' + name)
    return config, freeze


def publication(value):
    v1.publication(value)
    c.require(io._git('status', '--porcelain') == '', 'clean published checkout required')
    return value  # Remote ref/tree visibility is checked separately before each invocation.


def resources(cpu, started):
    return {'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - started,
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def fit(data, output, published):
    from .active_checkpoint import load_checkpoint, save_checkpoint
    from .observed_io import as_batches
    from .set_acquisition_fit import fit_masked
    config, freeze = verify(data)
    identity = {'source_publication': publication(published), 'runtime': verify_runtime(config, freeze['runtime']),
                'freeze_sha256': io._hash(data / 'freeze.json')}
    output.mkdir(parents=True, exist_ok=False); io._write(output / 'attempt.json', identity)
    inputs = io._read(data / 'train-inputs.json.xz'); batches = as_batches(inputs, batch_size=48)
    states, reports = {}, {}; started, cpu = time.perf_counter(), time.process_time()
    for law in LAWS:
        for seed in config['model_seeds']:
            item = freeze['parents'][law][str(seed)]
            model = load_checkpoint(PARENTS / item['file'], item['sha256'])['model']
            try: report = fit_masked(model, batches, config['fit'])
            except BaseException:
                io._write(output / f'interrupted-{law}-{seed}.json', getattr(model, 'training_provenance', {}))
                raise
            c.require(report['completed_updates'] == config['fit']['updates'] and
                report['observed_events_per_update'] == config['train_forecasts'], 'incomplete training exposure')
            name, key = f'{law}-{seed}.json', f'{law}/{seed}'
            states[key] = {'file': name, **save_checkpoint(output / name, model=model, provenance=report)}
            reports[key] = report; io._write(output / f'fit-{law}-{seed}.json', report)
            print(json.dumps({'fit': key, 'nll': report['final_observed_train_nll']}), flush=True)
    verify(data); verify_runtime(config, freeze['runtime'])
    io._write(output / 'training.json', {**identity, 'version': config['version'], 'complete': True,
        'training_input_sha256': c.digest(inputs), 'checkpoints': states, 'reports': reports,
        'resources': resources(cpu, started)})


def validate_fit(data, fitted, config, freeze):
    saved = v1.validate_fit(data, fitted, config, freeze)
    settings = config['fit']
    expected = {'status': 'COMPLETED', 'version': 'set-acquisition-fit-v1',
        'all_prescribed_updates_completed': True, 'requested_updates': settings['updates'],
        'learning_rate': settings['learning_rate'], 'gradient_clip': settings['gradient_clip'],
        'cpu_ceiling_seconds': settings['cpu_seconds'], 'live_path_limit': settings['live_path_limit'],
        'candidate_expansion_limit': settings['candidate_expansions'], 'optimizer': 'Adam',
        'optimizer_defaults': {'betas': [.9, .999], 'eps': 1e-8, 'weight_decay': 0., 'amsgrad': False},
        'fresh_optimizer': True, 'mask_before_clipping': True,
        'training_source_sha256': io._hash(ROOT / 'set_acquisition_fit.py')}
    c.require(saved['runtime'] == freeze['runtime'] and all(all(r.get(k) == value
        for k, value in expected.items()) for r in saved['reports'].values()), 'fitted runtime/recipe differs')
    return saved


def collect(data, fitted, output, published):
    import torch
    from .active_checkpoint import load_checkpoint
    from .binding_layout_coordinates import coordinate_encoder
    from .joint_objective import fingerprint
    config, freeze = verify(data); saved = validate_fit(data, fitted, config, freeze)
    identity = {'weights_publication': publication(published), 'runtime': verify_runtime(config, freeze['runtime']),
        'freeze_sha256': io._hash(data / 'freeze.json'), 'training_sha256': io._hash(fitted / 'training.json')}
    output.mkdir(parents=True, exist_ok=False); io._write(output / 'attempt.json', identity)
    accepted = io._read(LANGUAGE); artifacts = {}; cpu, started = time.process_time(), time.perf_counter()
    for law in LAWS:
        inputs = io._read(data / f'{law}-inputs.json.xz'); baseline = v1.native_points(inputs)
        for seed in config['model_seeds']:
            key, models = f'{law}/{seed}', {}
            for arm, directory, item in (('parent', PARENTS, freeze['parents'][law][str(seed)]),
                                        ('acquired', fitted, saved['checkpoints'][f'{law}/{seed}'])):
                models[arm] = load_checkpoint(directory / item['file'], item['sha256'])['model'].eval().requires_grad_(False)
            for arm in ARMS:
                points = baseline if arm == 'no_change' else v1.native_points(inputs, models[arm])
                name = f'trace-{law}-{seed}-{arm}-fresh.json.xz'
                artifacts[name] = io._write(output / name, {**identity, 'law': law, 'seed': seed, 'arm': arm,
                    'bank': 'fresh', 'input_sha256': c.digest(inputs), 'points': points})
            net = coordinate_encoder(seed); record = accepted['checkpoints'][f'coordinates/{seed}']
            net.load_state_dict({k: torch.tensor(v, dtype=torch.float64) for k, v in record['state'].items()}, strict=True)
            net.eval().requires_grad_(False)
            c.require(fingerprint(net.state_dict()) == record['state_sha256'], 'accepted language weights differ')
            for bank, folder in BANKS.items():
                observed = io._read(ROOT / 'data' / folder / f'{law}-inputs.json.xz')
                name = f'trace-{law}-{seed}-acquired-{bank}.json.xz'
                artifacts[name] = io._write(output / name, {**identity, 'law': law, 'seed': seed, 'arm': 'acquired',
                    'bank': bank, 'input_sha256': c.digest(observed), 'language_sha256': record['state_sha256'],
                    'points': v1.language_points(observed, models['acquired'], net)})
            for arm, model in models.items():
                item = saved['checkpoints'][key] if arm == 'acquired' else freeze['parents'][law][str(seed)]
                c.require(fingerprint(model.state_dict()) == item['state_sha256'], 'world changed during collection')
            c.require(fingerprint(net.state_dict()) == record['state_sha256'], 'language changed during collection')
            print(json.dumps({'collected': key}), flush=True)
    verify(data); verify_runtime(config, freeze['runtime'])
    io._write(output / 'manifest.json', {**identity, 'complete': True, 'oracle_opened': False,
        'artifacts': artifacts, 'resources': resources(cpu, started)})


def validate_collection(data, fitted, traces, config, freeze):
    manifest = io._read(traces / 'manifest.json')
    expected = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for law in LAWS for seed in config['model_seeds']
        for arm, bank in [*((arm, 'fresh') for arm in ARMS), *(('acquired', bank) for bank in BANKS)]}
    c.require(manifest['complete'] is True and manifest['oracle_opened'] is False and
        manifest['freeze_sha256'] == io._hash(data / 'freeze.json') and manifest['runtime'] == freeze['runtime'] and
        manifest['training_sha256'] == io._hash(fitted / 'training.json') and set(manifest['artifacts']) == expected,
        'collection inventory/binding/runtime differs')
    for name, item in manifest['artifacts'].items():
        c.require(io._hash(traces / name) == item['sha256'], 'trace bytes differ')
    attempt = io._read(traces / 'attempt.json')
    c.require(all(manifest[k] == attempt[k] for k in
        ('weights_publication', 'runtime', 'freeze_sha256', 'training_sha256')), 'collection attempt differs')
    return manifest


def score(data, fitted, traces, output, published):
    from .set_acquisition_scoring import analyze_native
    config, freeze = verify(data); saved = validate_fit(data, fitted, config, freeze)
    manifest = validate_collection(data, fitted, traces, config, freeze)
    identity = {'traces_publication': publication(published), 'runtime': verify_runtime(config, freeze['runtime']),
                'trace_manifest_sha256': io._hash(traces / 'manifest.json')}
    accepted = io._read(LANGUAGE)['checkpoints']
    output.mkdir(parents=True, exist_ok=False); io._write(output / 'attempt.json', identity)
    reports, checks = {}, {}; started, cpu = time.perf_counter(), time.process_time()
    # All published forecast bytes validate before evaluator metadata is opened.
    for law in LAWS:
        inputs = io._read(data / f'{law}-inputs.json.xz')
        bundle = {'inputs': inputs, **io._read(data / f'{law}-evaluator.json.xz')}
        for seed in config['model_seeds']:
            key = f'{law}/{seed}'
            def read(arm, bank, observed):
                value = io._read(traces / f'trace-{law}-{seed}-{arm}-{bank}.json.xz')
                c.require((value['law'], value['seed'], value['arm'], value['bank']) == (law, seed, arm, bank) and
                    value['input_sha256'] == c.digest(observed) and all(value[k] == manifest[k] for k in
                    ('weights_publication', 'freeze_sha256', 'training_sha256', 'runtime')), 'trace identity/runtime differs')
                if bank != 'fresh': c.require(value['language_sha256'] ==
                    accepted[f'coordinates/{seed}']['state_sha256'], 'retained language checkpoint differs')
                return value['points']
            native = analyze_native(bundle, {arm: read(arm, 'fresh', inputs) for arm in ARMS}, config['analysis'])
            retained = {}
            for bank, folder in BANKS.items():
                observed = io._read(ROOT / 'data' / folder / f'{law}-inputs.json.xz')
                old = io._read(v1.archive_path(law, seed, bank))
                c.require(old['input_sha256'] == c.digest(observed), 'archive inputs differ')
                retained[bank] = retention(observed, read('acquired', bank, observed), old['points'], config['analysis'])
            reports[key] = io._write(output / f'report-{law}-{seed}.json.xz', {'native': native, 'retention': retained})
            checks[key] = {**native['checks'], 'observed_training_fit':
                saved['reports'][key]['final_observed_train_nll'] <= config['analysis']['max_set_mean_nll'],
                **{bank + '/' + check: passed for bank, r in retained.items() for check, passed in r['checks'].items()}}
    decision = {'decision': 'KEEP_NATIVE_SET_ACQUISITION' if all(all(v.values()) for v in checks.values()) else
        'REVISE_NATIVE_SET_ACQUISITION', 'execution_complete': True, 'checks': checks,
        'scientific_admission': False, 'g3_complete': False}
    verify(data); verify_runtime(config, freeze['runtime'])
    io._write(output / 'decision.json', decision)
    io._write(output / 'manifest.json', {**identity, 'reports': reports, 'resources': resources(cpu, started)})
    print(json.dumps(decision), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'fit', 'collect', 'score'))
    for name in ('data', 'fitted', 'traces', 'output'): parser.add_argument('--' + name, type=Path, required=name == 'output')
    parser.add_argument('--publication'); args = parser.parse_args()
    required = {'prepare': (), 'fit': ('data', 'publication'), 'collect': ('data', 'fitted', 'publication'),
                'score': ('data', 'fitted', 'traces', 'publication')}[args.stage]
    for name in required:
        if getattr(args, name) is None: parser.error('--' + name + ' required')
    existed = args.output.exists()
    try:
        if args.stage == 'prepare': prepare(args.output)
        elif args.stage == 'fit': fit(args.data, args.output, args.publication)
        elif args.stage == 'collect': collect(args.data, args.fitted, args.output, args.publication)
        else: score(args.data, args.fitted, args.traces, args.output, args.publication)
    except BaseException as error:
        if not existed and args.output.is_dir(): io._write(args.output / 'failure.json',
            {'stage': args.stage, 'error': type(error).__name__, 'message': str(error),
             'traceback': traceback.format_exc(), 'retry_permitted': False})
        raise


if __name__ == '__main__': main()
