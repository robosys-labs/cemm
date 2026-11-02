"""Prospective G3 lexical acquisition with protected inherited competence.

Current controls are collected on every challenge bank under the frozen v3
runtime. V2's lost raw collection is not treated as archived evidence. Each
law/seed collection shard executes once and can be published independently.
"""
import argparse
import json
import math
from pathlib import Path
import time
import traceback

from . import acceptance_contract as c, continuation_run as io, effect_role_run as v1
from . import effect_role_run_v2 as prior
from .effect_role_lexical import learner, inherited_ids
from .effect_role_lexical_fit import fit_one
from .set_acquisition_runtime_v2 import runtime, verify_runtime

ROOT, native = io.ROOT, prior.native
PROTOCOL = ROOT / 'effect_role_protocol_v3.json'
LOCK = ROOT / 'snapshots/effect_role_protocol_v3.sha256'
COMMITMENT = ROOT / 'effect_role_freeze_v3.json'
PARENT_DATA, PARENT_FIT = ROOT / 'data/effect-role-v2', ROOT / 'data/effect-role-fit-v2'
PARENT_INCIDENT = ROOT / 'results/effect-role-interruption-v2.json'
WORLD, LANGUAGE, ARMS, LAWS, BANKS = prior.WORLD, prior.LANGUAGE, prior.ARMS, prior.LAWS, prior.BANKS
OPENED = {'v1': 'opened_effect_role_v1', 'v2': 'opened_effect_role_v2'}
archive_path, world_for, points = v1.archive_path, v1.world_for, v1.points
lexical_controls, validate_lexical_controls = v1.lexical_controls, v1.validate_lexical_controls
validate_recipe_counts, OPTIMIZER = v1.validate_recipe_counts, v1.OPTIMIZER
GENERATOR_SOURCES = ('effect_role_data_v3.py', 'effect_role_data_v2.py', 'effect_role_data.py', 'acceptance_contract.py', 'bilingual_contract.py', 'bilingual_data.py', 'binding_data.py', 'centering_data.py', 'continuation_run.py', 'coordinate_data.py', 'multisource_law_oracle.py', 'prospective_data.py', 'prospective_oracle.py', 'protocol.py', 'saturation_data.py', 'set_acquisition_data.py', 'world.py', 'mixed_composition_data.py', 'multisource_law_data.py', 'hidden_cycle_data.py', 'joint_correlation_data.py', 'timing_data.py', 'timing_contract.py', 'timing_oracle.py', 'continuation_data.py', 'set_acquisition_data_v2.py', 'sensor_transfer_data.py', 'comparison_data.py')


def sources():
    names = set(GENERATOR_SOURCES) | {'effect_role_lexical.py', 'effect_role_lexical_fit.py',
        'effect_role_run_v3.py', 'effect_role_scoring_v3.py', 'audit_effect_role_saved_v3.py',
        'tests/test_effect_role_data_v3.py', 'tests/test_effect_role_lexical.py',
        'tests/test_effect_role_lexical_fit.py', 'tests/test_effect_role_run_v3.py',
        'tests/test_effect_role_scoring_v3.py', 'tests/test_effect_role_saved_audit_v3.py',
        'EFFECT_ROLE_STUDY_V3.md', PROTOCOL.name, 'snapshots/' + LOCK.name}
    return {**prior.sources(), **{name: io._hash(ROOT / name) for name in sorted(names)}}


def prepare(output):
    from . import effect_role_data_v3 as recipe
    c.require(GENERATOR_SOURCES == recipe.SOURCE_FILES, 'generator dependency closure differs')
    config = protocol(); parent_config, parent_freeze = prior.verify(PARENT_DATA)
    prior.validate_fit(PARENT_DATA, PARENT_FIT, parent_config, parent_freeze)
    incident = io._read(PARENT_INCIDENT)
    c.require(incident['decision'] == 'STOP_INCOMPLETE_EVIDENCE' and incident['execution_complete'] is False
        and incident['g3_complete'] is False, 'published incomplete v2 evidence required')
    parent_publication = config['parent_result_publication']
    c.require(io._git('merge-base', '--is-ancestor', parent_publication, 'HEAD') == '', 'v2 incident is not ancestor')
    published_file(parent_publication, PARENT_INCIDENT)
    c.require(all(config[k] == parent_config[k] for k in ('fit', 'analysis', 'model_seeds', 'parameters')),
        'training budget, numerical criteria, seeds or model size changed')
    assets = recipe.build_assets(); validate_recipe_counts(config, assets); numerical = runtime(config)
    retention_count = sum(sum(len(r['utterances']) for r in io._read(
        ROOT / 'data' / folder / f'{law}-inputs.json.xz')['episodes']) for law in LAWS for folder in BANKS.values())
    c.require(retention_count * len(config['model_seeds']) == config['retention_saved_forecasts'], 'retention count differs')
    for version in OPENED:
        n = sum(sum(len(r['utterances']) for r in io._read(
            ROOT / f'data/effect-role-{version}/{law}-inputs.json.xz')['episodes']) for law in LAWS)
        c.require(n * 4 * len(config['model_seeds']) == config['opened_' + version + '_saved_forecasts'], 'opened count differs')
    c.require(config['reference_v2_saved_forecasts'] * 2 == config['opened_v2_saved_forecasts'] and
        config['total_saved_forecasts'] == sum(config[k] for k in ('fresh_saved_forecasts',
        'retention_saved_forecasts', 'opened_v1_saved_forecasts', 'opened_v2_saved_forecasts',
        'reference_v2_saved_forecasts')), 'reference/total counts differ')
    output.mkdir(parents=True, exist_ok=False); artifacts = {}
    training_parent = recipe.TRAINING_PARENT
    old_artifacts = io._read(training_parent / 'freeze.json')['artifacts']
    for key, name in recipe.TRAINING_FILES.items():
        (output / name).write_bytes((training_parent / name).read_bytes()); artifacts[name] = dict(old_artifacts[name])
        c.require(io._hash(output / name) == artifacts[name]['sha256'] and io._read(output / name) == assets[key],
                  'exact published training artifact differs')
    artifacts['audit.json'] = io._write(output / 'audit.json', assets['audit'])
    for law, bundle in assets['laws'].items():
        artifacts[law + '-inputs.json.xz'] = io._write(output / (law + '-inputs.json.xz'), bundle['inputs'])
        artifacts[law + '-evaluator.json.xz'] = io._write(output / (law + '-evaluator.json.xz'),
            {k: v for k, v in bundle.items() if k != 'inputs'})
    paths = [ROOT / 'effect_role_freeze_v2.json', PARENT_INCIDENT, ROOT / 'EFFECT_ROLE_DECISION_V2.md']
    for directory in (PARENT_DATA, PARENT_FIT): paths += [p for p in sorted(directory.rglob('*')) if p.is_file()]
    freeze = {'version': config['version'], 'sources': sources(), 'artifacts': artifacts,
        'world_checkpoints': parent_freeze['world_checkpoints'], 'runtime': numerical,
        'runtime_sha256': c.digest(numerical), 'protocol_sha256': io._hash(PROTOCOL),
        'parent_result_publication': parent_publication,
        'historical': {**parent_freeze['historical'], **{p.relative_to(ROOT).as_posix(): io._hash(p) for p in paths}}}
    io._write(output / 'freeze.json', freeze)
    io._write(COMMITMENT, {p.name: io._hash(p) for p in sorted(output.iterdir())})
    print(json.dumps({'prepared': str(output), 'freeze_sha256': io._hash(output / 'freeze.json'),
                      'audit': assets['audit']}), flush=True)


def published_file(commit, path):
    relative = path.resolve().relative_to(io.REPO).as_posix()
    c.require(io._git('rev-parse', commit + ':' + relative) == io._git('hash-object', str(path)),
              'published bytes differ: ' + relative)


def weights_publication(published, fitted, saved):
    c.require(type(published) is str and len(published) == 40 and
        set(published) <= set('0123456789abcdef') and not io._git('status', '--porcelain'), 'clean published execution required')
    c.require(io._git('merge-base', '--is-ancestor', published, 'HEAD') == '', 'weights publication is not ancestor')
    published_file(published, fitted / 'training.json')
    for item in saved['checkpoints'].values(): published_file(published, fitted / item['file'])
    return published


def validate_fit(data, fitted, config, freeze):
    import torch
    from .effect_role_model import validate_registry
    from .joint_objective import fingerprint
    saved, attempt = io._read(fitted / 'training.json'), io._read(fitted / 'attempt.json')
    expected = {f'{arm}/{seed}' for arm in ARMS for seed in config['model_seeds']}
    c.require(saved['complete'] is True and saved['version'] == config['version'] and
        saved['freeze_sha256'] == io._hash(data / 'freeze.json') and saved['runtime'] == freeze['runtime'] and
        set(saved['reports']) == set(saved['checkpoints']) == expected and
        all(saved[k] == attempt[k] for k in ('source_publication', 'runtime', 'freeze_sha256')) and
        saved['training_input_sha256'] == {name: c.digest(io._read(data / f'{name}-inputs.json.xz'))
            for name in ('teach', 'rehearsal')}, 'fitted inventory/binding/runtime differs')
    published_file(saved['source_publication'], data / 'freeze.json')
    registry = validate_registry(io._read(data / 'lexical-registry.json')); legacy = inherited_ids(registry)
    parents = io._read(LANGUAGE)['checkpoints']
    for key, item in saved['checkpoints'].items():
        arm, seed = key.split('/'); report = saved['reports'][key]
        c.require(item['file'] == f'{arm}-{seed}.json' and io._hash(fitted / item['file']) == item['sha256'], 'weight bytes differ')
        record = io._read(fitted / item['file']); state = {k: torch.tensor(v, dtype=torch.float64) for k, v in record['state'].items()}
        net = learner(arm, int(seed), parents[f'coordinates/{seed}']['state'], registry, legacy)
        protected = fingerprint(net.parent.state_dict()) if arm != 'text_only' else None
        c.require(fingerprint(net.state_dict()) == report['initial_sha256'] and
            all(bool(torch.isfinite(v).all()) for v in state.values()), 'initial/nonfinite tensors differ')
        net.load_state_dict(state, strict=True)
        c.require(record['arm'] == arm and record['seed'] == int(seed) and
            fingerprint(state) == record['state_sha256'] == report['final_sha256'] and
            report['world_sha256'] == freeze['world_checkpoints'][f'nand/{seed}']['state_sha256'] and
            report['world_unchanged'] is True and report['updates'] == config['fit']['updates'] and
            report['settings'] == config['fit'] and report['parameters'] == config['parameters'][arm] and
            sum(p.numel() for p in net.parameters()) == report['parameters'] and
            report['optimizer'] == OPTIMIZER and report['fresh_optimizer'] is True and
            report['observed_forecasts_per_update'] == config['training_forecasts'] and
            set(report['final_objective']) == {'teach', 'rehearsal'} and
            all(type(v) in (int, float) and math.isfinite(v) for v in report['final_objective'].values()) and
            report == io._read(fitted / f'fit-{arm}-{seed}.json'), 'fit recipe/state differs')
        if protected is not None:
            c.require(report['protected_parameters'] == 88 and report['learned_parameters'] == 4 and
                report['protected_unchanged'] is True and fingerprint(net.parent.state_dict()) ==
                report['protected_initial_sha256'] == report['protected_final_sha256'] == protected and
                report['registry_sha256'] == c.digest(registry) and report['legacy_ids'] == legacy and
                report['new_ids'] == list(net.new_ids) and sum(p.numel() for p in net.parameters() if p.requires_grad) == 4,
                'protected lexical complement or acquisition slots differ')
    return saved


def observations(data, law, bank):
    if bank == 'fresh': directory = data
    elif bank in OPENED.values(): directory = ROOT / ('data/effect-role-' + bank[-2:])
    else:
        c.require(bank in BANKS, 'unknown observed bank'); directory = ROOT / 'data' / BANKS[bank]
    return io._read(directory / f'{law}-inputs.json.xz')


def schedules():
    return [(arm, bank) for arm in ARMS for bank in
        (('fresh', *BANKS, *OPENED.values()) if arm == 'grounded' else ('fresh', *OPENED.values()))] + [
        ('reference_v2', OPENED['v2'])]


def reference_header(config, seed):
    old = io._read(PARENT_FIT / 'training.json'); item = old['checkpoints'][f'grounded/{seed}']
    return {'source_study': 'effect-role-v2',
        'source_checkpoint_publication': config['reference_v2']['checkpoint_publication'],
        'source_implementation_publication': config['reference_v2']['implementation_publication'],
        'source_training_sha256': io._hash(PARENT_FIT / 'training.json'),
        'source_checkpoint_sha256': item['sha256'], 'parameters_frozen': True, 'model_updates': 0}


def collect(data, fitted, output, published, law, seed):
    import torch
    from .effect_role_model import validate_registry
    from .joint_objective import fingerprint
    config, freeze = verify(data); saved = validate_fit(data, fitted, config, freeze)
    c.require(law in LAWS and seed in config['model_seeds'], 'unplanned collection shard')
    identity = {'weights_publication': weights_publication(published, fitted, saved),
        'runtime': verify_runtime(config, freeze['runtime']), 'freeze_sha256': io._hash(data / 'freeze.json'),
        'training_sha256': io._hash(fitted / 'training.json')}
    registry = validate_registry(io._read(data / 'lexical-registry.json')); legacy = inherited_ids(registry)
    if not output.exists():
        output.mkdir(parents=True, exist_ok=False); io._write(output / 'attempt.json', identity)
        io._write(output / 'lexical-identities.json', lexical_controls(registry, config['unknown_tokens']))
    else: c.require(io._read(output / 'attempt.json') == identity, 'shared collection identity differs')
    c.require(not (output / 'manifest.json').exists(), 'collection already sealed')
    prior_attempt = [output / f'{prefix}-{law}-{seed}.json'
                     for prefix in ('shard-attempt', 'shard', 'failure')]
    c.require(not any(path.exists() or path.is_symlink() for path in prior_attempt) and
        not list(output.glob(f'trace-{law}-{seed}-*')), 'collection shard already attempted or has orphaned artifacts')
    shard_id = {'law': law, 'seed': seed, 'execution_publication': io._git('rev-parse', 'HEAD')}
    io._write(output / f'shard-attempt-{law}-{seed}.json', {**identity, **shard_id})
    try:
        parents = io._read(LANGUAGE)['checkpoints']; artifacts = {}; cpu, started = time.process_time(), time.perf_counter()
        world = world_for(freeze, law, seed); world_hash = fingerprint(world.state_dict())
        for arm in (*ARMS, 'reference_v2'):
            if arm == 'reference_v2':
                old = io._read(PARENT_FIT / 'training.json'); item = old['checkpoints'][f'grounded/{seed}']
                published_file(config['reference_v2']['checkpoint_publication'], PARENT_FIT / item['file'])
                record = io._read(PARENT_FIT / item['file'])
                net = prior.learner('grounded', seed, parents[f'coordinates/{seed}']['state'])
            else:
                item = saved['checkpoints'][f'{arm}/{seed}']; record = io._read(fitted / item['file'])
                net = learner(arm, seed, parents[f'coordinates/{seed}']['state'], registry, legacy)
            net.load_state_dict({k: torch.tensor(v, dtype=torch.float64) for k, v in record['state'].items()}, strict=True)
            net.eval().requires_grad_(False)
            for _, bank in [(a, b) for a, b in schedules() if a == arm]:
                observed = observations(data, law, bank)
                views = ('canonical', 'masked') if arm in ('grounded', 'reference_v2') and bank not in BANKS else ('canonical',)
                name = f'trace-{law}-{seed}-{arm}-{bank}.json.xz'
                artifacts[name] = io._write(output / name, {**identity, **({'law': law, 'seed': seed, 'arm': arm, 'bank': bank}),
                    **(reference_header(config, seed) if arm == 'reference_v2' else {}),
                    'input_sha256': c.digest(observed), 'state_sha256': record['state_sha256'],
                    'points': points(observed, world, net, 'grounded' if arm == 'reference_v2' else arm, registry, views)})
            c.require(fingerprint(net.state_dict()) == record['state_sha256'], 'language changed during collection')
        c.require(fingerprint(world.state_dict()) == world_hash, 'world changed during collection')
        verify(data); verify_runtime(config, freeze['runtime'])
        io._write(output / f'shard-{law}-{seed}.json', {**identity, **shard_id, 'complete': True,
            'oracle_opened': False, 'artifacts': artifacts, 'resources': native.resources(cpu, started)})
        print(json.dumps({'collected': f'{law}/{seed}', 'trace_files': len(artifacts)}), flush=True)
    except BaseException as error:
        io._write(output / f'failure-{law}-{seed}.json', {'stage': 'collect', 'error': type(error).__name__,
            'message': str(error), 'traceback': traceback.format_exc(), 'retry_permitted': False})
        raise


def _item(path):
    return {'file': path.name, 'sha256': io._hash(path), 'bytes': path.stat().st_size}


def shard_inventory(traces, config, identity):
    artifacts, shards, resources = {}, {}, []
    for law in LAWS:
        for seed in config['model_seeds']:
            path = traces / f'shard-{law}-{seed}.json'; attempt = traces / f'shard-attempt-{law}-{seed}.json'
            value, begun = io._read(path), io._read(attempt)
            expected = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for arm, bank in schedules()}
            c.require(value['complete'] is True and value['oracle_opened'] is False and
                value['law'] == begun['law'] == law and value['seed'] == begun['seed'] == seed and
                value['execution_publication'] == begun['execution_publication'] and
                all(value[k] == begun[k] == identity[k] for k in identity) and set(value['artifacts']) == expected and
                not (traces / f'failure-{law}-{seed}.json').exists(), 'invalid/incomplete shard')
            for name, item in value['artifacts'].items():
                c.require(io._hash(traces / name) == item['sha256'] and (traces / name).stat().st_size == item['bytes'], 'shard bytes differ')
            artifacts.update(value['artifacts']); shards[f'{law}/{seed}'] = {**_item(path), 'attempt': _item(attempt)}
            resource = value['resources']
            c.require(set(resource) == {'cpu_seconds', 'wall_seconds', 'peak_rss_kib'} and
                all(type(resource[k]) in (int, float) and math.isfinite(resource[k]) and resource[k] >= 0
                    for k in ('cpu_seconds', 'wall_seconds')) and
                type(resource['peak_rss_kib']) is int and resource['peak_rss_kib'] > 0,
                'invalid shard resources')
            resources.append(resource)
    lexical = traces / 'lexical-identities.json'; artifacts[lexical.name] = {k: v for k, v in _item(lexical).items() if k != 'file'}
    expected = set(artifacts) | {'attempt.json'} | {item['file'] for item in shards.values()} | {
        item['attempt']['file'] for item in shards.values()}
    if (traces / 'manifest.json').exists(): expected.add('manifest.json')
    c.require({p.name for p in traces.iterdir()} == expected and
        all(p.is_file() and not p.is_symlink() for p in traces.iterdir()), 'unmanifested collection files')
    measured = {'cpu_seconds': math.fsum(r['cpu_seconds'] for r in resources),
        'wall_seconds': math.fsum(r['wall_seconds'] for r in resources), 'peak_rss_kib': max(r['peak_rss_kib'] for r in resources)}
    return artifacts, shards, measured


def seal(data, fitted, traces, published):
    config, freeze = verify(data); saved = validate_fit(data, fitted, config, freeze)
    weights_publication(published, fitted, saved); verify_runtime(config, freeze['runtime'])
    identity = {'weights_publication': published, 'runtime': freeze['runtime'],
        'freeze_sha256': io._hash(data / 'freeze.json'), 'training_sha256': io._hash(fitted / 'training.json')}
    c.require(io._read(traces / 'attempt.json') == identity, 'collection identity differs')
    artifacts, shards, measured = shard_inventory(traces, config, identity)
    io._write(traces / 'manifest.json', {**identity, 'complete': True, 'oracle_opened': False,
        'artifacts': artifacts, 'shards': shards, 'resources': measured,
        'resource_aggregation': 'sum of shard executions; publication gaps excluded'})
    print(json.dumps({'sealed': True, 'artifacts': len(artifacts), 'shards': len(shards)}), flush=True)


def validate_collection(data, fitted, traces, config, freeze):
    manifest, identity = io._read(traces / 'manifest.json'), io._read(traces / 'attempt.json')
    c.require(identity == {'weights_publication': manifest['weights_publication'], 'runtime': freeze['runtime'],
        'freeze_sha256': io._hash(data / 'freeze.json'), 'training_sha256': io._hash(fitted / 'training.json')}, 'collection identity differs')
    artifacts, shards, measured = shard_inventory(traces, config, identity)
    c.require(manifest['complete'] is True and manifest['oracle_opened'] is False and
        all(manifest[k] == v for k, v in identity.items()) and manifest['artifacts'] == artifacts and manifest['shards'] == shards and
        manifest['resources'] == measured and manifest['resource_aggregation'] == 'sum of shard executions; publication gaps excluded',
        'sealed collection inventory differs')
    return manifest


def protocol():
    return c.load_json(PROTOCOL, LOCK.read_text().split()[0])


def verify(data):
    config, freeze, commitment = protocol(), io._read(data / 'freeze.json'), io._read(COMMITMENT)
    c.require(set(commitment) == set(freeze['artifacts']) | {'freeze.json'}, 'frozen inventory differs')
    for name, digest in commitment.items(): c.require(io._hash(data / name) == digest, 'data differs: ' + name)
    c.require(freeze['sources'] == sources() and freeze['protocol_sha256'] == io._hash(PROTOCOL) and
        freeze['version'] == config['version'] and c.digest(freeze['runtime']) == freeze['runtime_sha256'],
        'frozen source/runtime differs')
    for name, digest in freeze['historical'].items():
        c.require(io._hash(ROOT / name) == digest, 'historical bytes differ: ' + name)
    return config, freeze


def fit(data, output, published):
    from .effect_role_model import create_registry, pack, validate_registry
    from .joint_objective import fingerprint
    config, freeze = verify(data)
    identity = {'source_publication': native.publication(published), 'runtime': verify_runtime(config, freeze['runtime']),
                'freeze_sha256': io._hash(data / 'freeze.json')}
    output.mkdir(parents=True, exist_ok=False); io._write(output / 'attempt.json', identity)
    registry = validate_registry(io._read(data / 'lexical-registry.json')); legacy = inherited_ids(registry)
    observed = {name: io._read(data / f'{name}-inputs.json.xz') for name in ('teach', 'rehearsal')}
    c.require(registry == create_registry([observed['rehearsal'], observed['teach']]), 'registry differs from TRAIN identity inventory')
    parents = io._read(LANGUAGE)['checkpoints']; checkpoints, reports = {}, {}
    cpu, started = time.process_time(), time.perf_counter()
    for seed in config['model_seeds']:
        world = world_for(freeze, 'nand', seed); tapes = {k: pack(v, world, registry) for k, v in observed.items()}
        for arm in ARMS:
            labels = io._read(data / 'parser-labels.json.xz') if arm == 'parser' else None
            if labels is not None:
                c.fields(labels, ('version', 'teach_input_sha256', 'rehearsal_input_sha256', 'teach', 'rehearsal'))
                c.require(labels['version'] == 'effect-role-parser-labels-v1' and
                    all(labels[name + '_input_sha256'] == c.digest(observed[name])
                    for name in observed), 'parser label binding differs')
            net, report = fit_one(arm, seed, parents[f'coordinates/{seed}']['state'], world, tapes, labels, config['fit'], registry=registry, legacy_ids=legacy)
            key, name = f'{arm}/{seed}', f'{arm}-{seed}.json'
            checkpoints[key] = {'file': name, **io._write(output / name, {'arm': arm, 'seed': seed,
                'state': {k: v.detach().tolist() for k, v in net.state_dict().items()},
                'state_sha256': fingerprint(net.state_dict())})}
            reports[key] = report; io._write(output / f'fit-{arm}-{seed}.json', report)
            print(json.dumps({'fit': key, 'objectives': report['final_objective']}), flush=True)
    verify(data); verify_runtime(config, freeze['runtime'])
    io._write(output / 'training.json', {**identity, 'version': config['version'], 'complete': True,
        'training_input_sha256': {k: c.digest(v) for k, v in observed.items()}, 'checkpoints': checkpoints,
        'reports': reports, 'resources': native.resources(cpu, started)})


def score(data, fitted, traces, output, published):
    from .effect_role_scoring_v3 import analyze, retention, analyze_opened
    config, freeze = verify(data); saved = validate_fit(data, fitted, config, freeze)
    manifest = validate_collection(data, fitted, traces, config, freeze)
    lexical_checks = validate_lexical_controls(io._read(data / 'lexical-registry.json'), config['unknown_tokens'],
                                              io._read(traces / 'lexical-identities.json'))
    identity = {'traces_publication': native.publication(published), 'runtime': verify_runtime(config, freeze['runtime']),
                'trace_manifest_sha256': io._hash(traces / 'manifest.json')}
    output.mkdir(parents=True, exist_ok=False); io._write(output / 'attempt.json', identity)
    reports, checks = {}, {}; cpu, started = time.process_time(), time.perf_counter()
    for law in LAWS:
        inputs = io._read(data / f'{law}-inputs.json.xz')
        bundle = {'inputs': inputs, **io._read(data / f'{law}-evaluator.json.xz')}
        for seed in config['model_seeds']:
            def read(arm, bank, observed):
                value = io._read(traces / f'trace-{law}-{seed}-{arm}-{bank}.json.xz')
                c.require((value['law'], value['seed'], value['arm'], value['bank']) == (law, seed, arm, bank) and
                    value['input_sha256'] == c.digest(observed) and all(value[k] == manifest[k] for k in
                    ('weights_publication', 'runtime', 'freeze_sha256', 'training_sha256')), 'trace binding differs')
                expected = saved['reports'][f'{arm}/{seed}']['final_sha256'] if arm != 'reference_v2' else io._read(PARENT_FIT / 'training.json')['reports'][f'grounded/{seed}']['final_sha256']
                c.require(value['state_sha256'] == expected, 'language state differs')
                if arm == 'reference_v2':
                    c.require(all(value[k] == v for k, v in reference_header(config, seed).items()), 'reference provenance differs')
                return value['points']
            fresh = analyze(bundle, {arm: read(arm, 'fresh', inputs) for arm in ARMS}, config['analysis'])
            retained = {}
            for bank, folder in BANKS.items():
                observed = io._read(ROOT / 'data' / folder / f'{law}-inputs.json.xz')
                old = io._read(archive_path(law, seed, bank))
                c.require(old['input_sha256'] == c.digest(observed), 'retention archive binding differs')
                retained[bank] = retention(observed, read('grounded', bank, observed), old['points'], config['analysis'])
            opened = {}
            for version, bank in OPENED.items():
                observed = observations(data, law, bank)
                old_bundle = {'inputs': observed, **io._read(ROOT / f'data/effect-role-{version}/{law}-evaluator.json.xz')}
                if version == 'v1':
                    old = io._read(ROOT / f'results/effect-role-v1/traces/trace-{law}-{seed}-grounded-fresh.json.xz')
                    c.require(old['input_sha256'] == c.digest(observed), 'v1 reference input differs')
                    reference = old['points']
                else: reference = read('reference_v2', bank, observed)
                opened[version] = analyze_opened(old_bundle, {arm: read(arm, bank, observed) for arm in ARMS},
                    reference, config['analysis'], version)
            key = f'{law}/{seed}'
            checks[key] = {**fresh['checks'], **{'opened_' + version + '/' + k: v for version, r in opened.items() for k, v in r['checks'].items()}, **{bank + '/' + check: passed for bank, r in retained.items()
                                               for check, passed in r['checks'].items()}}
            reports[key] = io._write(output / f'report-{law}-{seed}.json.xz', {'fresh': fresh, 'retention': retained, 'opened': opened})
    passed = all(all(values.values()) for values in checks.values()) and all(lexical_checks.values())
    decision = {'decision': 'DEVELOPMENT_G3_COMPLETE' if passed else 'REVISE_EFFECT_ROLE_GROUNDING',
        'execution_complete': True, 'checks': checks, 'g3_complete': passed,
        'lexical_identity_checks': lexical_checks, 'next_stage': 'G4' if passed else 'G3', 'scientific_admission': False}
    verify(data); verify_runtime(config, freeze['runtime'])
    io._write(output / 'decision.json', decision)
    io._write(output / 'manifest.json', {**identity, 'reports': reports, 'resources': native.resources(cpu, started)})
    print(json.dumps(decision), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'fit', 'collect', 'seal', 'score'))
    for name in ('data', 'fitted', 'traces', 'output'): parser.add_argument('--' + name, type=Path)
    parser.add_argument('--publication'); parser.add_argument('--law', choices=LAWS); parser.add_argument('--seed', type=int)
    args = parser.parse_args()
    required = {'prepare': ('output',), 'fit': ('data', 'output', 'publication'),
        'collect': ('data', 'fitted', 'output', 'publication', 'law', 'seed'),
        'seal': ('data', 'fitted', 'traces', 'publication'),
        'score': ('data', 'fitted', 'traces', 'output', 'publication')}[args.stage]
    for name in required:
        if getattr(args, name) is None: parser.error('--' + name + ' required')
    existed = args.output.exists() if args.output is not None else True
    try:
        if args.stage == 'prepare': prepare(args.output)
        elif args.stage == 'fit': fit(args.data, args.output, args.publication)
        elif args.stage == 'collect': collect(args.data, args.fitted, args.output, args.publication, args.law, args.seed)
        elif args.stage == 'seal': seal(args.data, args.fitted, args.traces, args.publication)
        else: score(args.data, args.fitted, args.traces, args.output, args.publication)
    except BaseException as error:
        if args.stage not in ('collect', 'seal') and not existed and args.output.is_dir():
            io._write(args.output / 'failure.json', {'stage': args.stage, 'error': type(error).__name__,
                'message': str(error), 'traceback': traceback.format_exc(), 'retry_permitted': False})
        raise


if __name__ == '__main__': main()
