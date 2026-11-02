"""Prospective G3 transfer: immutable worlds, observed teaching, frozen forecasts.

Preparation alone imports the recipe. Grounded fitting reads observed TRAIN
tapes only; parser labels enter only the explicitly supervised control.
"""
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import time
import traceback

from . import acceptance_contract as c, continuation_run as io, set_acquisition_run_v2 as native
from .set_acquisition_runtime_v2 import runtime, verify_runtime

ROOT = io.ROOT
PROTOCOL = ROOT / 'effect_role_protocol_v1.json'
LOCK = ROOT / 'snapshots/effect_role_protocol_v1.sha256'
COMMITMENT = ROOT / 'effect_role_freeze_v1.json'
WORLD = ROOT / 'data/set-acquisition-fit-v2'
NATIVE_RESULT = ROOT / 'results/set-acquisition-v2'
ARMS = ('grounded', 'parser', 'text_only')
LAWS, BANKS, LANGUAGE = native.LAWS, native.BANKS, native.LANGUAGE
OPTIMIZER = {'name': 'Adam', 'betas': [.9, .999], 'eps': 1e-8, 'weight_decay': 0., 'amsgrad': False}


def protocol():
    return c.load_json(PROTOCOL, LOCK.read_text().split()[0])


def sources():
    names = {'effect_role_data.py', 'effect_role_model.py', 'effect_role_run.py',
        'effect_role_scoring.py', 'tests/test_effect_role_data.py', 'tests/test_effect_role_model.py',
        'tests/test_effect_role_run.py', 'tests/test_effect_role_scoring.py',
        'audit_effect_role_saved.py', 'tests/test_effect_role_saved_audit.py', 'audit_bilingual_saved.py',
        'bilingual_data.py', 'binding_data.py', 'saturation_data.py', 'centering_data.py',
        'coordinate_data.py', 'prospective_oracle.py', 'world.py', 'protocol.py',
        'EFFECT_ROLE_STUDY_V1.md', PROTOCOL.name, 'snapshots/' + LOCK.name}
    return {**native.sources(), **{name: io._hash(ROOT / name) for name in sorted(names)}}


def archive_path(law, seed, bank):
    return NATIVE_RESULT / 'traces' / f'trace-{law}-{seed}-acquired-{bank}.json.xz'


def validate_recipe_counts(config, assets):
    counts = {name: sum(len(r['utterances']) for r in assets[name]['episodes']) for name in ('teach', 'rehearsal')}
    c.require(counts == config['training_forecasts'] and all(assets['audit'][name + '_forecasts'] == count
        for name, count in counts.items()) and set(assets['laws']) == set(LAWS) and config['arms'] == list(ARMS) and
        config['execution']['fits'] == len(ARMS) * len(config['model_seeds']), 'teaching/control recipe counts differ')
    fields = {'episodes': 'fresh_episodes_per_law', 'forecasts': 'fresh_forecasts_per_law',
        'identifiable_forecasts': 'identifiable_forecasts_per_law', 'ambiguous_forecasts': 'ambiguous_forecasts_per_law',
        'held_new_word_forecasts': 'held_new_word_forecasts_per_law', 'goal_groups': 'goal_groups_per_law',
        'goal_decisions': 'goal_decisions_per_law'}
    for law, bundle in assets['laws'].items():
        audit = assets['audit'][law]; records = bundle['inputs']['episodes']
        c.require(all(audit[k] == config[v] for k, v in fields.items()) and
            len(records) == audit['episodes'] and sum(len(r['utterances']) for r in records) == audit['forecasts'] and
            len(bundle['goal_groups']) == audit['goal_groups'] and
            sum(len(g['goals']) for g in bundle['goal_groups']) == audit['goal_decisions'], 'challenge recipe counts differ')
    c.require(config['fresh_saved_forecasts'] == config['fresh_forecasts_per_law'] * len(LAWS) *
        len(config['model_seeds']) * (len(ARMS) + 1), 'saved forecast plan differs')


def prepare(output):
    from .effect_role_data import build_assets
    from .effect_role_model import create_registry
    config = protocol()
    native_config, native_freeze = native.verify(ROOT / 'data/set-acquisition-v2')
    acquired = native.validate_fit(ROOT / 'data/set-acquisition-v2', WORLD, native_config, native_freeze)
    decision = io._read(NATIVE_RESULT / 'scored/decision.json')
    c.require(decision['execution_complete'] is True and decision['decision'] == 'KEEP_NATIVE_SET_ACQUISITION' and
        set(decision['checks']) == {f'{law}/{seed}' for law in LAWS for seed in config['model_seeds']} and
        all(checks and all(value is True for value in checks.values()) for checks in decision['checks'].values()),
        'accepted native acquisition required')
    assets = build_assets(); validate_recipe_counts(config, assets); numerical = runtime(config)
    retention_count = sum(sum(len(r['utterances']) for r in io._read(
        ROOT / 'data' / folder / f'{law}-inputs.json.xz')['episodes']) for law in LAWS for folder in BANKS.values())
    c.require(retention_count * len(config['model_seeds']) == config['retention_saved_forecasts'], 'retention recipe count differs')
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {}
    for name, value in [('teach-inputs.json.xz', assets['teach']), ('rehearsal-inputs.json.xz', assets['rehearsal']),
                        ('parser-labels.json.xz', assets['parser_labels']), ('audit.json', assets['audit']),
                        ('lexical-registry.json', create_registry([assets['rehearsal'], assets['teach']]))]:
        artifacts[name] = io._write(output / name, value)
    for law, bundle in assets['laws'].items():
        artifacts[law + '-inputs.json.xz'] = io._write(output / (law + '-inputs.json.xz'), bundle['inputs'])
        artifacts[law + '-evaluator.json.xz'] = io._write(output / (law + '-evaluator.json.xz'),
            {key: value for key, value in bundle.items() if key != 'inputs'})
    paths = [WORLD / 'training.json', LANGUAGE, NATIVE_RESULT / 'scored/decision.json',
             ROOT / 'data/set-acquisition-v2/freeze.json', ROOT / 'set_acquisition_freeze_v2.json']
    paths += [WORLD / item['file'] for item in acquired['checkpoints'].values()]
    paths += [WORLD / 'attempt.json', *[WORLD / ('fit-' + key.replace('/', '-') + '.json')
                                      for key in acquired['checkpoints']]]
    paths += [ROOT / 'data/set-acquisition-v2' / name for name in native_freeze['artifacts']]
    paths += [ROOT / 'coordinate_freeze_v1.json', ROOT / 'data/saturation-v1/train-inputs.json.xz']
    paths += [ROOT / 'data' / folder / f'{law}-inputs.json.xz' for law in LAWS for folder in BANKS.values()]
    paths += [archive_path(law, seed, bank) for law in LAWS for seed in config['model_seeds'] for bank in BANKS]
    freeze = {'version': config['version'], 'sources': sources(), 'artifacts': artifacts,
        'world_checkpoints': acquired['checkpoints'], 'runtime': numerical, 'runtime_sha256': c.digest(numerical),
        'historical': {**native_freeze['historical'], **{p.relative_to(ROOT).as_posix(): io._hash(p) for p in paths}},
        'protocol_sha256': io._hash(PROTOCOL)}
    io._write(output / 'freeze.json', freeze)
    io._write(COMMITMENT, {p.name: io._hash(p) for p in sorted(output.iterdir())})
    print(json.dumps({'prepared': str(output), 'freeze_sha256': io._hash(output / 'freeze.json'),
                      'audit': assets['audit']}), flush=True)


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


def world_for(freeze, law, seed):
    from .active_checkpoint import load_checkpoint
    item = freeze['world_checkpoints'][f'{law}/{seed}']
    return load_checkpoint(WORLD / item['file'], item['sha256'])['model'].eval().requires_grad_(False)


def learner(arm, seed, parent):
    import torch
    from .bilingual_model import SequenceControl
    from .effect_role_model import encoder
    c.require(arm in ARMS, 'unknown learner')
    if arm != 'text_only': return encoder(seed, parent)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        return SequenceControl()


def objective(arm, net, world, groups, labels=None):
    import torch
    from .effect_role_model import forecasts
    c.require(arm in ARMS and (labels is not None) == (arm == 'parser'), 'labels belong exclusively to parser control')
    c.require(type(groups) is list and groups, 'nonempty observed groups required')
    if arm == 'parser':
        expected = {r['id']: len(group['events']) for group in groups for r in group['records']}
        c.require(type(labels) is dict and set(labels) == set(expected) and all(type(labels[k]) is list and
            len(labels[k]) == count and all(type(v) is int and 0 <= v < 4 for v in labels[k])
            for k, count in expected.items()), 'parser label inventory/range differs')
    loss, count = 0., 0
    for group in groups:
        for step, ((raw, action), event) in enumerate(zip(forecasts(arm, net, world, group), group['events'], strict=True)):
            if arm == 'parser':
                target = torch.tensor([labels[r['id']][step] for r in group['records']], dtype=torch.long)
                loss = loss - action.gather(1, target[:, None]).sum()
            else: loss = loss - raw.gather(1, event['target'][:, None]).sum()
            count += len(raw)
    c.require(count > 0 and bool(torch.isfinite(loss)), 'empty/nonfinite observed objective')
    return loss / count, count


def fit_one(arm, seed, parent, world, tapes, labels, settings):
    import torch
    from .joint_objective import fingerprint
    c.require(type(tapes) is dict and set(tapes) == {'teach', 'rehearsal'}, 'both observed training tapes required')
    c.require(arm in ARMS and (labels is not None) == (arm == 'parser') and
        (labels is None or type(labels) is dict and all(k in labels for k in tapes)), 'parser-only labels required')
    c.require(type(settings) is dict and type(settings.get('updates')) is int and settings['updates'] > 0 and
        all(type(settings.get(k)) in (int, float) and math.isfinite(settings[k]) and settings[k] > 0
            for k in ('learning_rate', 'gradient_clip', 'cpu_seconds_per_fit')) and
        type(settings.get('teach_weight')) in (int, float) and math.isfinite(settings['teach_weight']) and
        0 < settings['teach_weight'] < 1, 'invalid fixed fit budget/weight')
    c.require(not world.training and all(not p.requires_grad and p.grad is None for p in world.parameters()),
              'explicit frozen world required before fitting')
    net = learner(arm, seed, parent); initial = fingerprint(net.state_dict()); native_before = fingerprint(world.state_dict())
    optimizer = torch.optim.Adam(net.parameters(), lr=settings['learning_rate'], betas=tuple(OPTIMIZER['betas']),
                                 eps=OPTIMIZER['eps'], weight_decay=OPTIMIZER['weight_decay'], amsgrad=OPTIMIZER['amsgrad'])
    curves, cpu, started = [], time.process_time(), time.perf_counter()
    for step in range(settings['updates']):
        c.require(time.process_time() - cpu <= settings['cpu_seconds_per_fit'], 'fixed training CPU ceiling exceeded')
        optimizer.zero_grad(set_to_none=True)
        losses, counts = {}, {}
        for name in ('teach', 'rehearsal'):
            losses[name], counts[name] = objective(arm, net, world, tapes[name], labels[name] if labels is not None else None)
        loss = settings['teach_weight'] * losses['teach'] + (1. - settings['teach_weight']) * losses['rehearsal']
        c.require(bool(torch.isfinite(loss)), 'nonfinite weighted objective')
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), settings['gradient_clip'], error_if_nonfinite=True)
        optimizer.step()
        c.require(all(bool(torch.isfinite(p).all()) for p in net.parameters()), 'nonfinite learned language tensor')
        c.require(fingerprint(world.state_dict()) == native_before and all(p.grad is None for p in world.parameters()),
                  'frozen native world mutated')
        if step == 0 or (step + 1) % 16 == 0:
            curves.append({'update': step + 1, **{k: float(v.detach()) for k, v in losses.items()}})
        c.require(time.process_time() - cpu <= settings['cpu_seconds_per_fit'], 'fixed training CPU ceiling exceeded')
    with torch.no_grad():
        measured = {name: objective(arm, net, world, groups, labels[name] if labels is not None else None)
                    for name, groups in tapes.items()}
        final = {name: float(value[0]) for name, value in measured.items()}
    c.require(all(math.isfinite(v) for v in final.values()) and
        {name: value[1] for name, value in measured.items()} == counts, 'final objective/count differs')
    c.require(fingerprint(world.state_dict()) == native_before and all(p.grad is None for p in world.parameters()),
              'frozen native world mutated during final measurement')
    c.require(time.process_time() - cpu <= settings['cpu_seconds_per_fit'], 'fixed training CPU ceiling exceeded')
    report = {'initial_sha256': initial, 'final_sha256': fingerprint(net.state_dict()),
        'world_sha256': native_before, 'world_unchanged': True, 'parameters': sum(p.numel() for p in net.parameters()),
        'updates': settings['updates'], 'observed_forecasts_per_update': counts, 'settings': dict(settings),
        'optimizer': {**OPTIMIZER, 'betas': list(OPTIMIZER['betas'])},
        'fresh_optimizer': True, 'curve': curves, 'final_objective': final,
        'resources': native.resources(cpu, started)}
    return net, report


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
    io._write(output / 'training.json', {**identity, 'version': config['version'], 'complete': True,
        'training_input_sha256': {k: c.digest(v) for k, v in observed.items()}, 'checkpoints': checkpoints,
        'reports': reports, 'resources': native.resources(cpu, started)})


def validate_fit(data, fitted, config, freeze):
    import torch
    from .joint_objective import fingerprint
    saved, attempt = io._read(fitted / 'training.json'), io._read(fitted / 'attempt.json')
    expected = {f'{arm}/{seed}' for arm in ARMS for seed in config['model_seeds']}
    c.require(saved['complete'] is True and saved['version'] == config['version'] and
        saved['freeze_sha256'] == io._hash(data / 'freeze.json') and saved['runtime'] == freeze['runtime'] and
        set(saved['reports']) == set(saved['checkpoints']) == expected and
        all(saved[k] == attempt[k] for k in ('source_publication', 'runtime', 'freeze_sha256')) and
        saved['training_input_sha256'] == {name: c.digest(io._read(data / f'{name}-inputs.json.xz'))
            for name in ('teach', 'rehearsal')}, 'fitted inventory/binding/runtime differs')
    relative = (data / 'freeze.json').resolve().relative_to(io.REPO).as_posix()
    c.require(io._git('show', saved['source_publication'] + ':' + relative) == (data / 'freeze.json').read_text().strip(),
              'source publication differs')
    parents = io._read(LANGUAGE)['checkpoints']
    for key, item in saved['checkpoints'].items():
        arm, seed = key.split('/'); report = saved['reports'][key]
        c.require(item['file'] == f'{arm}-{seed}.json' and io._hash(fitted / item['file']) == item['sha256'], 'weight bytes differ')
        record = io._read(fitted / item['file'])
        state = {k: torch.tensor(v, dtype=torch.float64) for k, v in record['state'].items()}
        net = learner(arm, int(seed), parents[f'coordinates/{seed}']['state'])
        c.require(fingerprint(net.state_dict()) == report['initial_sha256'] and
                  all(bool(torch.isfinite(v).all()) for v in state.values()), 'initial/nonfinite language tensors differ')
        net.load_state_dict(state, strict=True)
        c.require(record['arm'] == arm and record['seed'] == int(seed) and
            fingerprint(state) == record['state_sha256'] == report['final_sha256'] and
            report['world_sha256'] == freeze['world_checkpoints'][f'nand/{seed}']['state_sha256'] and
            report['world_unchanged'] is True and report['updates'] == config['fit']['updates'] and
            report['settings'] == config['fit'] and report['parameters'] == config['parameters'][arm] and
            sum(p.numel() for p in net.parameters()) == report['parameters'] and
            report['optimizer'] == OPTIMIZER and report['fresh_optimizer'] is True and
            report['observed_forecasts_per_update'] == config['training_forecasts'] and
            type(report['final_objective']) is dict and set(report['final_objective']) == {'teach', 'rehearsal'} and
            all(type(v) in (int, float) and math.isfinite(v) for v in report['final_objective'].values()) and
            report == io._read(fitted / f'fit-{arm}-{seed}.json'), 'fit recipe/state differs')
    return saved


def points(inputs, world, net, arm, registry, views):
    import torch
    from .effect_role_model import pack, forecasts
    c.require(type(views) in (tuple, list) and bool(views) and len(set(views)) == len(views) and
              set(views) <= {'canonical', 'masked'}, 'invalid forecast views')
    rows = []
    def encoded(values):
        c.require(not bool((torch.isnan(values) | torch.isposinf(values)).any()), 'invalid nonfinite forecast')
        return [float(x) if torch.isfinite(x) else 'negative_infinity' for x in values]
    with torch.no_grad():
        for group in pack(inputs, world, registry):
            for view in views:
                for step, (raw, actions) in enumerate(forecasts(arm, net, world, group, view)):
                    for index, record in enumerate(group['records']):
                        rows.append({'id': record['id'], 'step': step, 'view': view,
                            'logp': encoded(raw[index]), 'action_logp': None if actions is None else encoded(actions[index])})
    return sorted(rows, key=lambda r: (r['id'], r['step'], r['view']))


def _lexical_checks(registry, tokens, receipt):
    from .effect_role_model import validate_registry
    validate_registry(registry)
    c.require(type(tokens) is list and len(tokens) == 2 and all(type(t) is str and 0 < len(t) <= 512 and
        len(t.split()) == 1 for t in tokens) and len(set(tokens)) == 2 and
        not set(tokens) & (registry['tokens'].keys() | {'ProbeA', 'ProbeB', 'ProbeC'}), 'distinct unregistered controls required')
    c.fields(receipt, ('version', 'registry_sha256', 'registry_after_sha256', 'known_tokens', 'known_unique_ids',
        'known_unique_features', 'unknown', 'unresolved_exception', 'semantic_model_calls', 'checks'))
    c.require(receipt['version'] == 'effect-role-lexical-controls-v1' and type(receipt['unknown']) is list and
        all(type(receipt[k]) is int for k in ('known_tokens', 'known_unique_ids', 'known_unique_features', 'semantic_model_calls')),
        'invalid lexical control receipt')
    for record in receipt['unknown']: c.fields(record, ('token', 'id', 'status'))
    expected = [{'token': token, 'id': sha256(token.encode('utf-8')).hexdigest(),
                 'status': 'UNRESOLVED_LEXICAL_IDENTITY'} for token in sorted(tokens)]
    known = registry['tokens']; count = len(known)
    return {'registry_bound': receipt['registry_sha256'] == c.digest(registry),
        'known_identities_distinct': receipt['known_tokens'] == receipt['known_unique_ids'] ==
            len({r['id'] for r in known.values()}) == count,
        'known_features_distinct': receipt['known_unique_features'] ==
            len({tuple(r['features']) for r in known.values()}) == count,
        'unknown_identities_unresolved': receipt['unresolved_exception'] is True and receipt['unknown'] == expected,
        'registry_unchanged': receipt['registry_after_sha256'] == receipt['registry_sha256'],
        'no_semantic_forecast': receipt['semantic_model_calls'] == 0}


def lexical_controls(registry, tokens):
    from .effect_role_model import UnresolvedLexeme, tokenize_batch, validate_registry
    validate_registry(registry); before = c.digest(registry)
    receipt = {'version': 'effect-role-lexical-controls-v1', 'registry_sha256': before,
        'registry_after_sha256': before, 'known_tokens': len(registry['tokens']),
        'known_unique_ids': len({r['id'] for r in registry['tokens'].values()}),
        'known_unique_features': len({tuple(r['features']) for r in registry['tokens'].values()}),
        'unknown': [], 'unresolved_exception': False, 'semantic_model_calls': 0, 'checks': {}}
    _lexical_checks(registry, tokens, receipt)  # Validate the prospective control, not its result.
    try:
        tokenize_batch([f'ProbeA {token} ProbeB' for token in tokens], [['ProbeA', 'ProbeB', 'ProbeC']] * 2, registry)
    except UnresolvedLexeme as error:
        receipt['unknown'], receipt['unresolved_exception'] = error.records, True
    receipt['registry_after_sha256'] = c.digest(registry)
    receipt['checks'] = _lexical_checks(registry, tokens, receipt)
    return receipt


def validate_lexical_controls(registry, tokens, receipt):
    checks = _lexical_checks(registry, tokens, receipt)
    c.require(receipt['checks'] == checks, 'lexical control arithmetic differs')
    return checks


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
                for bank in ('fresh', *BANKS) if arm == 'grounded' else ('fresh',):
                    observed = inputs if bank == 'fresh' else io._read(ROOT / 'data' / BANKS[bank] / f'{law}-inputs.json.xz')
                    views = ('canonical', 'masked') if arm == 'grounded' and bank == 'fresh' else ('canonical',)
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
        for arm in ARMS for bank in (('fresh', *BANKS) if arm == 'grounded' else ('fresh',))}
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
    from .effect_role_scoring import analyze, retention
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
            key = f'{law}/{seed}'
            checks[key] = {**fresh['checks'], **{bank + '/' + check: passed for bank, r in retained.items()
                                               for check, passed in r['checks'].items()}}
            reports[key] = io._write(output / f'report-{law}-{seed}.json.xz', {'fresh': fresh, 'retention': retained})
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
