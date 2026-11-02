"""Prospective probability-neutral G3 study over unchanged observed training.

The completed v1 study is immutable opened regression evidence. New identities
and structures are fresh; previously opened lexical cells are not relabeled.
"""
import argparse
import json
import math
from pathlib import Path
import time
import traceback

from . import acceptance_contract as c, continuation_run as io, effect_role_run as prior
from .effect_role_neutral import learner
from .effect_role_neutral_fit import fit_one
from .set_acquisition_runtime_v2 import runtime, verify_runtime

ROOT, native = io.ROOT, prior.native
PROTOCOL = ROOT / 'effect_role_protocol_v2.json'
LOCK = ROOT / 'snapshots/effect_role_protocol_v2.sha256'
COMMITMENT = ROOT / 'effect_role_freeze_v2.json'
PARENT_DATA, PARENT_FIT = ROOT / 'data/effect-role-v1', ROOT / 'data/effect-role-fit-v1'
PARENT_RESULT = ROOT / 'results/effect-role-v1'
OPENED = 'opened_effect_role_v1'
GENERATOR_SOURCES = ('effect_role_data_v2.py', 'effect_role_data.py', 'acceptance_contract.py', 'bilingual_contract.py', 'bilingual_data.py', 'binding_data.py', 'centering_data.py', 'continuation_run.py', 'coordinate_data.py', 'multisource_law_oracle.py', 'prospective_data.py', 'prospective_oracle.py', 'protocol.py', 'saturation_data.py', 'set_acquisition_data.py', 'world.py', 'mixed_composition_data.py', 'multisource_law_data.py', 'hidden_cycle_data.py', 'joint_correlation_data.py', 'timing_data.py', 'timing_contract.py', 'timing_oracle.py', 'continuation_data.py', 'set_acquisition_data_v2.py', 'sensor_transfer_data.py', 'comparison_data.py')
WORLD, LANGUAGE, ARMS, LAWS, BANKS = prior.WORLD, prior.LANGUAGE, prior.ARMS, prior.LAWS, prior.BANKS
archive_path, world_for, points = prior.archive_path, prior.world_for, prior.points
lexical_controls, validate_lexical_controls = prior.lexical_controls, prior.validate_lexical_controls
validate_recipe_counts = prior.validate_recipe_counts


def sources():
    names = set(GENERATOR_SOURCES) | {'effect_role_neutral.py', 'effect_role_neutral_fit.py',
        'effect_role_run_v2.py', 'effect_role_scoring_v2.py', 'audit_effect_role_saved_v2.py',
        'tests/test_effect_role_data_v2.py', 'tests/test_effect_role_neutral.py',
        'tests/test_effect_role_neutral_fit.py', 'tests/test_effect_role_run_v2.py',
        'tests/test_effect_role_scoring_v2.py', 'tests/test_effect_role_saved_audit_v2.py',
        'EFFECT_ROLE_STUDY_V2.md', PROTOCOL.name, 'snapshots/' + LOCK.name}
    return {**prior.sources(), **{name: io._hash(ROOT / name) for name in sorted(names)}}


def prepare(output):
    from . import effect_role_data_v2 as recipe
    c.require(GENERATOR_SOURCES == recipe.SOURCE_FILES, 'generator dependency closure differs')
    config = protocol(); parent_config, parent_freeze = prior.verify(PARENT_DATA)
    prior.validate_fit(PARENT_DATA, PARENT_FIT, parent_config, parent_freeze)
    prior.validate_collection(PARENT_DATA, PARENT_FIT, PARENT_RESULT / 'traces', parent_config, parent_freeze)
    decision = io._read(PARENT_RESULT / 'scored/decision.json')
    audit = io._read(ROOT / 'results/effect-role-saved-audit-v1.json')
    c.require(decision['execution_complete'] is True and decision['decision'] == 'REVISE_EFFECT_ROLE_GROUNDING'
        and decision['g3_complete'] is False and audit['audit_passed'] is True and audit['discrepancy_count'] == 0,
        'complete audited v1 result required')
    parent_publication = config['parent_result_publication']
    c.require(io._git('merge-base', '--is-ancestor', parent_publication, 'HEAD') == '', 'v1 result is not ancestor')
    path = (PARENT_RESULT / 'scored/decision.json').relative_to(io.REPO).as_posix()
    c.require(io._git('show', parent_publication + ':' + path) ==
        (PARENT_RESULT / 'scored/decision.json').read_text().strip(), 'v1 published result differs')
    c.require(config['fit'] == parent_config['fit'] and config['analysis'] == parent_config['analysis'] and
        config['model_seeds'] == parent_config['model_seeds'] and config['parameters'] == parent_config['parameters'],
        'normalization-only study changed budget, gates, seeds or model size')
    assets = recipe.build_assets(); validate_recipe_counts(config, assets); numerical = runtime(config)
    retention_count = sum(sum(len(r['utterances']) for r in io._read(
        ROOT / 'data' / folder / f'{law}-inputs.json.xz')['episodes']) for law in LAWS for folder in BANKS.values())
    opened_count = sum(sum(len(r['utterances']) for r in io._read(
        PARENT_DATA / f'{law}-inputs.json.xz')['episodes']) for law in LAWS)
    c.require(retention_count * len(config['model_seeds']) == config['retention_saved_forecasts'] and
        opened_count * 2 * len(config['model_seeds']) == config['opened_saved_forecasts'] and
        config['total_saved_forecasts'] == sum(config[k] for k in
        ('fresh_saved_forecasts', 'retention_saved_forecasts', 'opened_saved_forecasts')), 'saved forecast counts differ')
    output.mkdir(parents=True, exist_ok=False); artifacts = {}
    for key, name in recipe.TRAINING_FILES.items():
        source = PARENT_DATA / name
        (output / name).write_bytes(source.read_bytes())
        artifacts[name] = dict(parent_freeze['artifacts'][name])
        c.require(io._hash(output / name) == artifacts[name]['sha256'] and
            io._read(output / name) == assets[key], 'exact published training artifact differs')
    artifacts['audit.json'] = io._write(output / 'audit.json', assets['audit'])
    for law, bundle in assets['laws'].items():
        artifacts[law + '-inputs.json.xz'] = io._write(output / (law + '-inputs.json.xz'), bundle['inputs'])
        artifacts[law + '-evaluator.json.xz'] = io._write(output / (law + '-evaluator.json.xz'),
            {key: value for key, value in bundle.items() if key != 'inputs'})
    paths = [ROOT / 'effect_role_freeze_v1.json', ROOT / 'results/effect-role-saved-audit-v1.json',
             ROOT / 'results/effect-role-pre-score-audit-v1.json', ROOT / 'EFFECT_ROLE_DECISION_V1.md']
    for directory in (PARENT_DATA, PARENT_FIT, PARENT_RESULT, ROOT / 'diagnostics/effect-role-v1'):
        c.require(directory.is_dir(), 'required v1 evidence missing: ' + str(directory))
        paths += [p for p in sorted(directory.rglob('*')) if p.is_file()]
    freeze = {'version': config['version'], 'sources': sources(), 'artifacts': artifacts,
        'world_checkpoints': parent_freeze['world_checkpoints'], 'runtime': numerical,
        'runtime_sha256': c.digest(numerical), 'protocol_sha256': io._hash(PROTOCOL),
        'parent_result_publication': parent_publication,
        'historical': {**parent_freeze['historical'],
            **{p.relative_to(ROOT).as_posix(): io._hash(p) for p in paths}}}
    io._write(output / 'freeze.json', freeze)
    io._write(COMMITMENT, {p.name: io._hash(p) for p in sorted(output.iterdir())})
    print(json.dumps({'prepared': str(output), 'freeze_sha256': io._hash(output / 'freeze.json'),
                      'audit': assets['audit']}), flush=True)


def text_only_reproduction(fitted, config, saved):
    """Require exact control reproduction before any archive-control reuse."""
    archive = io._read(PARENT_FIT / 'training.json'); checks = {}
    for seed in config['model_seeds']:
        key = f'text_only/{seed}'; current, old = saved['reports'][key], archive['reports'][key]
        report_equal = {k: v for k, v in current.items() if k != 'resources'} == {
            k: v for k, v in old.items() if k != 'resources'}
        current_item, old_item = saved['checkpoints'][key], archive['checkpoints'][key]
        current_hash, old_hash = io._hash(fitted / current_item['file']), io._hash(PARENT_FIT / old_item['file'])
        checks[str(seed)] = {'checkpoint_bytes_equal': current_hash == old_hash ==
            current_item['sha256'] == old_item['sha256'], 'report_except_resources_equal': report_equal,
            'checkpoint_sha256': current_hash, 'state_sha256': current['final_sha256']}
        c.require(checks[str(seed)]['checkpoint_bytes_equal'] and report_equal,
                  'text-only control no longer exactly reproduces v1')
    return {'version': 'effect-role-text-only-reproduction-v2', 'passed': True,
            'resources_excluded': True, 'seeds': checks}


def validate_fit(data, fitted, config, freeze):
    saved = prior.validate_fit(data, fitted, config, freeze)
    c.require(saved['text_only_reproduction'] == text_only_reproduction(fitted, config, saved),
              'text-only reproduction receipt differs')
    return saved


def observations(data, law, bank):
    if bank == 'fresh': path = data
    elif bank == OPENED: path = PARENT_DATA
    else:
        c.require(bank in BANKS, 'unknown retention bank')
        path = ROOT / 'data' / BANKS[bank]
    return io._read(path / f'{law}-inputs.json.xz')


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
    registry = validate_registry(io._read(data / 'lexical-registry.json'))
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
            net, report = fit_one(arm, seed, parents[f'coordinates/{seed}']['state'], world, tapes, labels, config['fit'])
            key, name = f'{arm}/{seed}', f'{arm}-{seed}.json'
            checkpoints[key] = {'file': name, **io._write(output / name, {'arm': arm, 'seed': seed,
                'state': {k: v.detach().tolist() for k, v in net.state_dict().items()},
                'state_sha256': fingerprint(net.state_dict())})}
            reports[key] = report; io._write(output / f'fit-{arm}-{seed}.json', report)
            print(json.dumps({'fit': key, 'objectives': report['final_objective']}), flush=True)
    verify(data); verify_runtime(config, freeze['runtime'])
    saved = {**identity, 'version': config['version'], 'complete': True,
        'training_input_sha256': {k: c.digest(v) for k, v in observed.items()}, 'checkpoints': checkpoints,
        'reports': reports, 'resources': native.resources(cpu, started)}
    saved['text_only_reproduction'] = text_only_reproduction(output, config, saved)
    io._write(output / 'training.json', saved)


def collect(data, fitted, output, published):
    import torch
    from .effect_role_model import validate_registry
    from .joint_objective import fingerprint
    config, freeze = verify(data); saved = validate_fit(data, fitted, config, freeze)
    identity = {'weights_publication': native.publication(published), 'runtime': verify_runtime(config, freeze['runtime']),
        'freeze_sha256': io._hash(data / 'freeze.json'), 'training_sha256': io._hash(fitted / 'training.json')}
    output.mkdir(parents=True, exist_ok=False); io._write(output / 'attempt.json', identity)
    registry = validate_registry(io._read(data / 'lexical-registry.json'))
    artifacts = {'lexical-identities.json': io._write(output / 'lexical-identities.json',
                                                    lexical_controls(registry, config['unknown_tokens']))}
    parents = io._read(LANGUAGE)['checkpoints']; cpu, started = time.process_time(), time.perf_counter()
    for law in LAWS:
        inputs = io._read(data / f'{law}-inputs.json.xz')
        for seed in config['model_seeds']:
            world = world_for(freeze, law, seed); world_hash = fingerprint(world.state_dict())
            for arm in ARMS:
                item = saved['checkpoints'][f'{arm}/{seed}']; record = io._read(fitted / item['file'])
                net = learner(arm, seed, parents[f'coordinates/{seed}']['state'])
                net.load_state_dict({k: torch.tensor(v, dtype=torch.float64) for k, v in record['state'].items()}, strict=True)
                net.eval().requires_grad_(False)
                for bank in ('fresh', *BANKS, OPENED) if arm == 'grounded' else ('fresh',):
                    observed = observations(data, law, bank)
                    views = ('canonical', 'masked') if arm == 'grounded' and bank in ('fresh', OPENED) else ('canonical',)
                    name = f'trace-{law}-{seed}-{arm}-{bank}.json.xz'
                    artifacts[name] = io._write(output / name, {**identity, 'law': law, 'seed': seed, 'arm': arm,
                        'bank': bank, 'input_sha256': c.digest(observed), 'state_sha256': record['state_sha256'],
                        'points': points(observed, world, net, arm, registry, views)})
                c.require(fingerprint(net.state_dict()) == record['state_sha256'], 'language changed during collection')
            c.require(fingerprint(world.state_dict()) == world_hash, 'world changed during collection')
            print(json.dumps({'collected': f'{law}/{seed}'}), flush=True)
    verify(data); verify_runtime(config, freeze['runtime'])
    io._write(output / 'manifest.json', {**identity, 'complete': True, 'oracle_opened': False,
        'artifacts': artifacts, 'resources': native.resources(cpu, started)})


def validate_collection(data, fitted, traces, config, freeze):
    manifest, attempt = io._read(traces / 'manifest.json'), io._read(traces / 'attempt.json')
    expected = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for law in LAWS for seed in config['model_seeds']
        for arm in ARMS for bank in (('fresh', *BANKS, OPENED) if arm == 'grounded' else ('fresh',))}
    expected.add('lexical-identities.json')
    c.require(manifest['complete'] is True and manifest['oracle_opened'] is False and
        manifest['freeze_sha256'] == io._hash(data / 'freeze.json') and manifest['runtime'] == freeze['runtime'] and
        manifest['training_sha256'] == io._hash(fitted / 'training.json') and set(manifest['artifacts']) == expected and
        all(manifest[k] == attempt[k] for k in ('weights_publication', 'runtime', 'freeze_sha256', 'training_sha256')),
        'collection inventory/binding differs')
    for name, item in manifest['artifacts'].items():
        c.require(io._hash(traces / name) == item['sha256'], 'raw forecast bytes differ')
    return manifest


def score(data, fitted, traces, output, published):
    from .effect_role_scoring_v2 import analyze, retention, analyze_opened
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
                c.require(value['state_sha256'] == saved['reports'][f'{arm}/{seed}']['final_sha256'], 'language state differs')
                return value['points']
            fresh = analyze(bundle, {arm: read(arm, 'fresh', inputs) for arm in ARMS}, config['analysis'])
            retained = {}
            for bank, folder in BANKS.items():
                observed = io._read(ROOT / 'data' / folder / f'{law}-inputs.json.xz')
                old = io._read(archive_path(law, seed, bank))
                c.require(old['input_sha256'] == c.digest(observed), 'retention archive binding differs')
                retained[bank] = retention(observed, read('grounded', bank, observed), old['points'], config['analysis'])
            old_inputs = observations(data, law, OPENED)
            old_bundle = {'inputs': old_inputs, **io._read(PARENT_DATA / f'{law}-evaluator.json.xz')}
            def archived(arm):
                value = io._read(PARENT_RESULT / 'traces' / f'trace-{law}-{seed}-{arm}-fresh.json.xz')
                c.require((value['law'], value['seed'], value['arm'], value['bank']) == (law, seed, arm, 'fresh')
                    and value['input_sha256'] == c.digest(old_inputs), 'opened archive binding differs')
                return value['points']
            opened = analyze_opened(old_bundle, {'grounded': read('grounded', OPENED, old_inputs),
                'parser': archived('parser'), 'text_only': archived('text_only')}, archived('grounded'), config['analysis'])
            key = f'{law}/{seed}'
            checks[key] = {**fresh['checks'], **{'opened/' + k: v for k, v in opened['checks'].items()}, **{bank + '/' + check: passed for bank, r in retained.items()
                                               for check, passed in r['checks'].items()}}
            reports[key] = io._write(output / f'report-{law}-{seed}.json.xz', {'fresh': fresh, 'retention': retained, 'opened': opened})
    passed = all(all(values.values()) for values in checks.values()) and all(lexical_checks.values())
    decision = {'decision': 'DEVELOPMENT_G3_COMPLETE' if passed else 'REVISE_EFFECT_ROLE_GROUNDING',
        'execution_complete': True, 'checks': checks, 'g3_complete': passed,
        'lexical_identity_checks': lexical_checks, 'text_only_reproduction': saved['text_only_reproduction'], 'next_stage': 'G4' if passed else 'G3', 'scientific_admission': False}
    verify(data); verify_runtime(config, freeze['runtime'])
    io._write(output / 'decision.json', decision)
    io._write(output / 'manifest.json', {**identity, 'reports': reports, 'resources': native.resources(cpu, started)})
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
        if not existed and args.output.is_dir(): io._write(args.output / 'failure.json', {'stage': args.stage,
            'error': type(error).__name__, 'message': str(error), 'traceback': traceback.format_exc(), 'retry_permitted': False})
        raise


if __name__ == '__main__': main()
