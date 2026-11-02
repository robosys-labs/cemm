"""One native-effect acquisition: freeze, fit, publish weights, collect, score.

Reuses the existing observed replay and frozen language predictor. No action
meaning, simulator or evaluation target is available to the fitting function.
"""
import argparse
import json
import math
from pathlib import Path
import resource
import time
import traceback

from . import acceptance_contract as c, continuation_run as io

ROOT = io.ROOT
BASE = '2ba2843b3a456957b9c4f0b789e42e90387354c8'
PROTOCOL = ROOT / 'set_acquisition_protocol_v1.json'
PARENTS = ROOT / 'data/multisource-law-fit-v1'
LANGUAGE = ROOT / 'data/coordinate-fit-v1/checkpoints.json.xz'
BANKS = {name + '_retention': name + '-v1' for name in
         ('bilingual', 'lexical', 'binding', 'saturation', 'centering', 'coordinate')}
ARMS = ('parent', 'acquired', 'no_change')
LAWS = ('nand', 'nor')


def protocol():
    return c.load_json(PROTOCOL, (ROOT / 'snapshots/set_acquisition_protocol_v1.sha256').read_text().split()[0])


def sources():
    names = set(c.software_sources()) | {'active_learning.py', 'observed_io.py', 'continuation_run.py',
        'bilingual_run.py', 'bilingual_model.py', 'bilingual_contract.py', 'bilingual_scoring.py',
        'binding_model.py', 'binding_unsaturated.py', 'binding_centered_init.py', 'binding_layout_coordinates.py',
        'multisource_law_oracle.py', 'prospective_data.py', 'mixed_composition_run.py', 'audit_bilingual_saved.py',
        'set_acquisition_data.py', 'set_acquisition_fit.py', 'set_acquisition_scoring.py',
        'set_acquisition_run.py', PROTOCOL.name, 'snapshots/set_acquisition_protocol_v1.sha256',
        'SET_ACQUISITION_STUDY_V1.md'}
    return {name: io._hash(ROOT / name) for name in sorted(names)}


def archive_path(law, seed, bank):
    oldbank = 'fresh' if bank == 'coordinate_retention' else bank
    return ROOT / 'results/coordinate-v1/traces' / f'trace-{law}-{seed}-coordinates-{oldbank}.json.xz'


def prepare(output):
    from .set_acquisition_data import build_assets
    config, assets = protocol(), build_assets()
    c.require(assets['audit']['train_forecasts'] == config['train_forecasts'] and
        assets['audit']['evaluation_forecasts_per_law'] == config['fresh_forecasts_per_law'], 'recipe count differs')
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'train-inputs.json.xz': io._write(output / 'train-inputs.json.xz', assets['train'])}
    for law, bundle in assets['laws'].items():
        artifacts[law + '-inputs.json.xz'] = io._write(output / (law + '-inputs.json.xz'), bundle['inputs'])
        artifacts[law + '-evaluator.json.xz'] = io._write(output / (law + '-evaluator.json.xz'),
            {k: v for k, v in bundle.items() if k != 'inputs'})
    artifacts['audit.json'] = io._write(output / 'audit.json', assets['audit'])
    training = io._read(PARENTS / 'training.json')
    parents = {law: training['checkpoints'][law] for law in LAWS}
    paths = [PARENTS / 'training.json', LANGUAGE]
    paths += [PARENTS / item['file'] for group in parents.values() for item in group.values()]
    paths += [ROOT / 'data' / folder / f'{law}-inputs.json.xz' for law in LAWS for folder in BANKS.values()]
    paths += [archive_path(law, seed, bank) for law in LAWS for seed in config['model_seeds'] for bank in BANKS]
    historical = {p.relative_to(ROOT).as_posix(): io._hash(p) for p in paths}
    io._write(output / 'freeze.json', {'version': config['version'], 'base_commit': BASE,
        'sources': sources(), 'artifacts': artifacts, 'parents': parents, 'historical': historical,
        'protocol_sha256': io._hash(PROTOCOL)})
    io._write(ROOT / 'set_acquisition_freeze_v1.json', {p.name: io._hash(p) for p in sorted(output.iterdir())})


def verify(data):
    config, freeze = protocol(), io._read(data / 'freeze.json')
    commitment = io._read(ROOT / 'set_acquisition_freeze_v1.json')
    c.require(set(commitment) == set(freeze['artifacts']) | {'freeze.json'}, 'data inventory differs')
    for name, digest in commitment.items(): c.require(io._hash(data / name) == digest, 'data differs: ' + name)
    c.require(freeze['sources'] == sources() and freeze['protocol_sha256'] == io._hash(PROTOCOL)
        and freeze['version'] == config['version'] and freeze['base_commit'] == BASE, 'frozen source differs')
    for name, digest in freeze['historical'].items():
        c.require(io._hash(ROOT / name) == digest, 'historical bytes differ: ' + name)
    return config, freeze


def publication(value):
    c.require(type(value) is str and len(value) == 40 and set(value) <= set('0123456789abcdef') and
        io._git('rev-parse', 'HEAD') == value, 'current published commit required')
    return value  # Remote visibility is verified separately through GitHub before invocation.


def fit(data, output, published):
    from .active_checkpoint import load_checkpoint, save_checkpoint
    from .observed_io import as_batches
    from .set_acquisition_fit import fit_masked
    config, freeze = verify(data); runtime = io._runtime(config)
    identity = {'source_publication': publication(published), 'runtime': runtime,
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
            name = f'{law}-{seed}.json'
            states[f'{law}/{seed}'] = {'file': name, **save_checkpoint(output / name, model=model, provenance=report)}
            reports[f'{law}/{seed}'] = report
            io._write(output / f'fit-{law}-{seed}.json', report)
            print(json.dumps({'fit': f'{law}/{seed}', 'nll': report['final_observed_train_nll']}), flush=True)
    verify(data)
    io._write(output / 'training.json', {**identity, 'version': config['version'], 'complete': True,
        'training_input_sha256': c.digest(inputs), 'checkpoints': states, 'reports': reports,
        'resources': {'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - started,
        'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}})


def validate_fit(data, fitted, config, freeze):
    saved = io._read(fitted / 'training.json')
    expected = {f'{law}/{seed}' for law in LAWS for seed in config['model_seeds']}
    c.require(saved['complete'] is True and saved['version'] == config['version'] and
        saved['freeze_sha256'] == io._hash(data / 'freeze.json') and
        saved['training_input_sha256'] == c.digest(io._read(data / 'train-inputs.json.xz')) and
        set(saved['reports']) == set(saved['checkpoints']) == expected, 'fitted inventory/binding differs')
    attempt = io._read(fitted / 'attempt.json')
    c.require(all(saved[k] == attempt[k] for k in ('source_publication', 'runtime', 'freeze_sha256')) and
        all(saved['runtime'][k] == v for k, v in config['execution']['runtime'].items()), 'fit attempt/runtime differs')
    published = saved['source_publication']
    c.require(type(published) is str and len(published) == 40 and set(published) <= set('0123456789abcdef') and
        io._git('show', published + ':' + (data / 'freeze.json').resolve().relative_to(io.REPO).as_posix()) ==
        (data / 'freeze.json').read_text().strip(), 'fit source publication differs')
    for key, item in saved['checkpoints'].items():
        law, seed = key.split('/'); report = saved['reports'][key]
        c.require(item['file'] == f'{law}-{seed}.json' and io._hash(fitted / item['file']) == item['sha256'], 'weights differ')
        state = io._read(fitted / item['file'])
        c.require(state['state_sha256'] == item['state_sha256'] == report['final_weights_sha256'] and
            report['initial_weights_sha256'] == freeze['parents'][law][seed]['state_sha256'] and
            state['provenance'] == report == io._read(fitted / f'fit-{law}-{seed}.json') and
            report['completed_updates'] == config['fit']['updates'] and
            report['observed_events_per_update'] == config['train_forecasts'], 'fitted provenance differs')
        parent = io._read(PARENTS / freeze['parents'][law][seed]['file'])
        verify_mask(parent, state, report)
    return saved


def verify_mask(parent, current, report):
    """Check actual serialized tensors with stdlib, not self-reported preservation."""
    from .audit_bilingual_saved import fingerprint
    before, after = parent['state'], current['state']
    c.require(set(before) == set(after) and parent['predictor'] == current['predictor'], 'checkpoint topology differs')
    complements = [{}, {}]; allowed = changed = total = 0
    for name, old in before.items():
        new = after[name]
        c.require(old['shape'] == new['shape'] and old['dtype'] == new['dtype'] == 'torch.float64' and
            len(old['values']) == len(new['values']) == math.prod(old['shape']), 'tensor geometry differs')
        mask = [name.startswith('intervention.') or name == 'background.0.weight' and i % 4 == 2
                for i in range(len(old['values']))]
        allowed += sum(mask); total += len(mask)
        for a, b, permitted in zip(old['values'], new['values'], mask, strict=True):
            c.require(type(a) is float and type(b) is float and math.isfinite(a) and math.isfinite(b), 'invalid tensor scalar')
            differs = a.hex() != b.hex()
            c.require(permitted or not differs, 'forbidden parameter update in checkpoint')
            changed += differs
        for target, tensor in zip(complements, (old, new), strict=True):
            values = [v for v, permitted in zip(tensor['values'], mask, strict=True) if not permitted]
            if values: target[name] = {'dtype': 'torch.float64', 'shape': [len(values)], 'values': values}
    c.require(total == 562 and allowed == 68 and before['background.0.weight']['shape'] == [11, 4] and
        sum(len(t['values']) for k, t in before.items() if k.startswith('intervention.')) == 57,
        'actual parameter mask differs')
    c.require(fingerprint(before)[0] == parent['state_sha256'] == report['initial_weights_sha256'] and
        fingerprint(after)[0] == current['state_sha256'] == report['final_weights_sha256'] and
        fingerprint(complements[0])[0] == report['immutable_before_sha256'] ==
        report['immutable_after_sha256'] == fingerprint(complements[1])[0] and
        report['parameters'] == 562 and report['permitted_scalars'] == 68 and report['immutable_scalars'] == 494 and
        report['changed_permitted_scalars'] == changed and report['changed_forbidden_scalars'] == 0,
        'actual preservation differs from fit receipt')


def native_points(inputs, model=None):
    from .active_learning import replay
    from .observed_io import as_batches
    points = []
    for batch in as_batches(inputs, batch_size=128):
        result = replay(batch, model=model, control=None if model is not None else 'no_change')
        c.require(bool(result['answered'].all()), 'incomplete native forecast coverage')
        logs = result['log_probabilities'].detach().tolist()
        c.require(all(not math.isnan(v) and v != math.inf for rows in logs for row in rows for v in row),
                  'invalid native log probability')
        points.extend({'id': name, 'step': t, 'logp': [v if math.isfinite(v) else 'negative_infinity' for v in row]}
            for t, rows in enumerate(logs) for name, row in zip(batch.episode_ids, rows, strict=True))
    return points


def language_points(inputs, world, net):
    import torch
    from .bilingual_run import pack, forecasts
    points = []
    with torch.no_grad():
        for group in pack(inputs, world):
            for t, (raw, order) in enumerate(forecasts('grounded', net, world, group)):
                points.extend({'id': record['id'], 'step': t, 'view': 'canonical',
                    'logp': raw[i].tolist(), 'order_logp': order[i].tolist()}
                    for i, record in enumerate(group['records']))
    return points


def collect(data, fitted, output, published):
    import torch
    from .active_checkpoint import load_checkpoint
    from .binding_layout_coordinates import coordinate_encoder
    from .joint_objective import fingerprint
    config, freeze = verify(data); saved = validate_fit(data, fitted, config, freeze); runtime = io._runtime(config)
    identity = {'weights_publication': publication(published), 'runtime': runtime,
        'freeze_sha256': io._hash(data / 'freeze.json'), 'training_sha256': io._hash(fitted / 'training.json')}
    output.mkdir(parents=True, exist_ok=False); io._write(output / 'attempt.json', identity)
    accepted = io._read(LANGUAGE); artifacts = {}; cpu, started = time.process_time(), time.perf_counter()
    for law in LAWS:
        inputs = io._read(data / f'{law}-inputs.json.xz')
        # One deterministic baseline, shared across seed labels; no invented independent fits.
        baseline = native_points(inputs)
        for seed in config['model_seeds']:
            key = f'{law}/{seed}'; models = {}
            for arm, directory, item in (('parent', PARENTS, freeze['parents'][law][str(seed)]),
                                        ('acquired', fitted, saved['checkpoints'][key])):
                models[arm] = load_checkpoint(directory / item['file'], item['sha256'])['model'].eval().requires_grad_(False)
            for arm in ARMS:
                points = baseline if arm == 'no_change' else native_points(inputs, models[arm])
                name = f'trace-{law}-{seed}-{arm}-fresh.json.xz'
                artifacts[name] = io._write(output / name, {**identity, 'law': law, 'seed': seed, 'arm': arm,
                    'bank': 'fresh', 'input_sha256': c.digest(inputs), 'points': points})
            net = coordinate_encoder(seed); record = accepted['checkpoints'][f'coordinates/{seed}']
            net.load_state_dict({k: torch.tensor(v, dtype=torch.float64) for k, v in record['state'].items()}, strict=True)
            net.eval().requires_grad_(False)
            c.require(fingerprint(net.state_dict()) == record['state_sha256'], 'accepted language weights differ')
            for bank, folder in BANKS.items():
                observed = io._read(ROOT / 'data' / folder / f'{law}-inputs.json.xz')
                points = language_points(observed, models['acquired'], net)
                name = f'trace-{law}-{seed}-acquired-{bank}.json.xz'
                artifacts[name] = io._write(output / name, {**identity, 'law': law, 'seed': seed, 'arm': 'acquired',
                    'bank': bank, 'input_sha256': c.digest(observed), 'language_sha256': record['state_sha256'], 'points': points})
            for arm, model in models.items():
                digest = saved['checkpoints'][key]['state_sha256'] if arm == 'acquired' else freeze['parents'][law][str(seed)]['state_sha256']
                c.require(fingerprint(model.state_dict()) == digest, 'world changed during collection')
            c.require(fingerprint(net.state_dict()) == record['state_sha256'], 'language changed during collection')
            print(json.dumps({'collected': key}), flush=True)
    verify(data)
    io._write(output / 'manifest.json', {**identity, 'complete': True, 'oracle_opened': False, 'artifacts': artifacts,
        'resources': {'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - started,
        'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}})


def retention(inputs, current, archive, tolerance):
    from .bilingual_scoring import _logs
    from .bilingual_contract import validate_inputs
    from .acceptance_scoring import _index
    inputs = validate_inputs(inputs)
    records = {r['id']: r for r in inputs['episodes']}
    expected = {(r['id'], t) for r in records.values() for t in range(len(r['utterances']))}
    def indexed(rows, archived=False):
        values = {}
        for row in rows:
            if row.get('view', 'canonical') != 'canonical':
                c.require(archived and row['view'] in ('masked', 'swapped'), 'unexpected retention view')
                continue
            key = row['id'], row['step']
            c.require(type(row['step']) is int and key in expected and key not in values, 'retention inventory differs')
            values[key] = {**row, 'logp': _logs(row['logp'], 2 ** len(records[row['id']]['entities'])),
                          'order_logp': _logs(row['order_logp'], 2)}
        c.require(values.keys() == expected, 'missing retention rows'); return values
    now, before = indexed(current), indexed(archive, True); rows = []
    for key, point in now.items():
        old = before[key]; target = _index(records[key[0]]['utterances'][key[1]]['reading'])
        best = lambda p: max(range(len(p['logp'])), key=p['logp'].__getitem__)
        c.require(point['order_logp'] == old['order_logp'], 'frozen language output changed')
        rows.append({'id': key[0], 'step': key[1], 'correct': best(point) == target,
            'regression': best(old) == target and best(point) != target,
            'nll': -point['logp'][target], 'nll_change': old['logp'][target] - point['logp'][target],
            'max_logp_change': max(abs(a - b) for a, b in zip(point['logp'], old['logp'], strict=True))})
    maximum = max(r['max_logp_change'] for r in rows)
    return {'planned': len(rows), 'correct': sum(r['correct'] for r in rows),
        'regressions': [[r['id'], r['step']] for r in rows if r['regression']],
        'nll_worse': sum(r['nll_change'] > 0 for r in rows), 'nll_better': sum(r['nll_change'] < 0 for r in rows),
        'mean_nll_change': math.fsum(r['nll_change'] for r in rows) / len(rows), 'max_logp_change': maximum,
        'passed': maximum <= tolerance and not any(r['regression'] for r in rows), 'points': rows}


def score(data, fitted, traces, output):
    from .set_acquisition_scoring import analyze_native
    config, freeze = verify(data); saved = validate_fit(data, fitted, config, freeze)
    manifest = io._read(traces / 'manifest.json')
    expected = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for law in LAWS for seed in config['model_seeds']
        for arm, bank in [*((arm, 'fresh') for arm in ARMS), *(('acquired', bank) for bank in BANKS)]}
    c.require(manifest['complete'] is True and manifest['oracle_opened'] is False and
        manifest['freeze_sha256'] == io._hash(data / 'freeze.json') and
        manifest['training_sha256'] == io._hash(fitted / 'training.json') and
        set(manifest['artifacts']) == expected, 'collection inventory/binding differs')
    for name, item in manifest['artifacts'].items():
        c.require(io._hash(traces / name) == item['sha256'], 'trace bytes differ')
    attempt = io._read(traces / 'attempt.json')
    c.require(all(manifest[k] == attempt[k] for k in
        ('weights_publication', 'runtime', 'freeze_sha256', 'training_sha256')), 'collection attempt differs')
    accepted = io._read(LANGUAGE)['checkpoints']
    # Only after all frozen forecast files validate, open the evaluator metadata.
    output.mkdir(parents=True, exist_ok=False); reports, checks = {}, {}
    for law in LAWS:
        inputs = io._read(data / f'{law}-inputs.json.xz')
        bundle = {'inputs': inputs, **io._read(data / f'{law}-evaluator.json.xz')}
        for seed in config['model_seeds']:
            key = f'{law}/{seed}'
            def read(arm, bank, observed):
                value = io._read(traces / f'trace-{law}-{seed}-{arm}-{bank}.json.xz')
                c.require((value['law'], value['seed'], value['arm'], value['bank']) == (law, seed, arm, bank) and
                    value['input_sha256'] == c.digest(observed) and all(value[k] == manifest[k] for k in
                    ('weights_publication', 'freeze_sha256', 'training_sha256')), 'trace identity differs')
                if bank != 'fresh': c.require(value['language_sha256'] ==
                    accepted[f'coordinates/{seed}']['state_sha256'], 'retained language checkpoint differs')
                return value['points']
            native = analyze_native(bundle, {arm: read(arm, 'fresh', inputs) for arm in ARMS}, config['analysis'])
            retained = {}
            for bank, folder in BANKS.items():
                observed = io._read(ROOT / 'data' / folder / f'{law}-inputs.json.xz')
                old = io._read(archive_path(law, seed, bank))
                c.require(old['input_sha256'] == c.digest(observed), 'archive inputs differ')
                retained[bank] = retention(observed, read('acquired', bank, observed), old['points'],
                                           config['analysis']['max_retention_logp_change'])
            report = {'native': native, 'retention': retained}
            reports[key] = io._write(output / f'report-{law}-{seed}.json.xz', report)
            checks[key] = {**native['checks'], 'observed_training_fit':
                saved['reports'][key]['final_observed_train_nll'] <= config['analysis']['max_set_mean_nll'],
                'language_retention': all(r['passed'] for r in retained.values())}
    decision = {'decision': 'KEEP_NATIVE_SET_ACQUISITION' if all(all(v.values()) for v in checks.values()) else
        'REVISE_NATIVE_SET_ACQUISITION', 'execution_complete': True, 'checks': checks,
        'scientific_admission': False, 'g3_complete': False}
    io._write(output / 'decision.json', decision)
    io._write(output / 'manifest.json', {'reports': reports, 'trace_manifest_sha256': io._hash(traces / 'manifest.json')})
    print(json.dumps(decision), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'fit', 'collect', 'score'))
    for name in ('data', 'fitted', 'traces', 'output'): parser.add_argument('--' + name, type=Path, required=name == 'output')
    parser.add_argument('--publication'); args = parser.parse_args()
    for name in {'prepare': (), 'fit': ('data', 'publication'), 'collect': ('data', 'fitted', 'publication'),
                 'score': ('data', 'fitted', 'traces')}[args.stage]:
        if getattr(args, name) is None: parser.error('--' + name + ' required')
    existed = args.output.exists()
    try:
        if args.stage == 'prepare': prepare(args.output)
        elif args.stage == 'fit': fit(args.data, args.output, args.publication)
        elif args.stage == 'collect': collect(args.data, args.fitted, args.output, args.publication)
        else: score(args.data, args.fitted, args.traces, args.output)
    except BaseException as error:
        if not existed and args.output.is_dir(): io._write(args.output / 'failure.json',
            {'stage': args.stage, 'error': type(error).__name__, 'message': str(error),
             'traceback': traceback.format_exc(), 'retry_permitted': False})
        raise


if __name__ == '__main__': main()
