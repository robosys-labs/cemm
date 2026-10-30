"""One paired outcome-law study on the unchanged native pairwise nucleus.

Prepare/public freeze -> fit once -> bind/public checkpoint freeze -> collect
once. Only prepare imports the generator. Fit reads delivered training tapes;
collection receives observed evaluation tapes before evaluator-only joins.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import traceback

from . import acceptance_contract as contract, continuation_run as io

ROOT = io.ROOT
PROTOCOL = ROOT / 'multisource_law_protocol_v1.json'
LAWS, ARMS = ('nand', 'nor'), ('crossed', 'matched')


def protocol():
    lock = ROOT / 'snapshots/multisource_law_protocol_v1.sha256'
    return contract.load_json(PROTOCOL, lock.read_text().split()[0])


def sources():
    names = set(io._sources()) | {'multisource_law_run.py', 'multisource_law_data.py',
        'multisource_law_oracle.py', 'multisource_law_scoring.py', 'mixed_composition_run.py',
        'mixed_composition_data.py', PROTOCOL.name, 'snapshots/multisource_law_protocol_v1.sha256',
        *('data/' + name for name in ('prospective-assets-v1.json.xz', 'continuation-assets-v1.json.xz',
          'alias-evidence-assets-v1.json.xz', 'alias-evidence-assets-v2.json.xz',
          'mixed-composition-v1/assets.json.xz', 'joint-correlation-v1/assets.json.xz'))}
    return {name: io._hash(ROOT / name) for name in sorted(names)}


def verify(data):
    io._committed(data / 'prefit.json')
    frozen = io._read(data / 'prefit.json')
    contract.require(frozen['sources'] == sources() and
                     frozen['protocol_sha256'] == io._hash(PROTOCOL), 'frozen source/protocol differs')
    for name, item in frozen['artifacts'].items():
        contract.require(io._hash(data / name) == item['sha256'], 'prepared artifact differs: ' + name)
    return protocol(), frozen


def prepare(output):
    from .multisource_law_data import build_assets
    config = protocol()
    assets = build_assets({'version': config['version'], 'data': {
        k: config['data'][k] for k in ('entity_counts', 'split_seeds')}})
    for law in LAWS:
        for split in ('train', 'evaluation'):
            group = assets['banks'][law]['splits'][split]
            episodes = group['inputs']['episodes']
            expected = config['data'][split]
            contract.require(len(episodes) == expected['episodes'] and
                sum(len(e['actions']) for e in episodes) == expected['events'], 'planned inventory differs')
    contract.require(len(assets['law_contrasts']) == config['analysis']['law_contrast']['contexts'],
                     'law contrast inventory differs')
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'assets.json.xz': io._write(output / 'assets.json.xz', assets)}
    for law in LAWS:
        for split in ('train', 'evaluation'):
            name = f'{law}-{split}-inputs.json'
            artifacts[name] = io._write(output / name, assets['banks'][law]['splits'][split]['inputs'])
    io._write(output / 'prefit.json', {'version': config['version'], 'sources': sources(),
        'protocol_sha256': io._hash(PROTOCOL), 'artifacts': artifacts,
        'evaluation_oracles': {law: {key: contract.digest(assets['banks'][law]['splits']['evaluation']['oracle'])
            if key == 'oracle_sha256' else assets['banks'][law]['splits']['evaluation']['oracle'][source]
            for key, source in (('oracle_sha256', None), ('oracle_source_sha256', 'source_sha256'),
                                ('information_law_sha256', 'information_law_sha256'))} for law in LAWS},
        'training_permitted_after_public_commit': True, 'gate_g1': 'NOT_ADMITTED'})
    print(json.dumps({'prepared': str(output), 'audit': assets['audit']}), flush=True)


def fit(data, output):
    from .active_checkpoint import save_checkpoint
    from .active_learning import fit as learn
    from .domain_kernel import DomainKernel
    from .observed_io import load_batches
    import torch
    config, frozen = verify(data)
    runtime = io._runtime(config)
    output.mkdir(parents=True, exist_ok=False)
    io._write(output / 'attempt.json', {'stage': 'fit', 'prefit_commit': io._git('rev-parse', 'HEAD'),
        'prefit_sha256': io._hash(data / 'prefit.json'), 'runtime': runtime, 'one_attempt': True})
    settings = config['fit']
    batches = {law: load_batches(data / f'{law}-train-inputs.json',
        frozen['artifacts'][f'{law}-train-inputs.json']['sha256'], batch_size=settings['batch_size']) for law in LAWS}
    inventory, reports = {law: {} for law in (*LAWS, 'initial')}, {}
    for seed in config['model_seeds']:
        torch.manual_seed(seed)
        original = DomainKernel(**config['model'])
        contract.require(sum(p.numel() for p in original.parameters()) == config['parameters'], 'parameter mismatch')
        name = f'initial-{seed}.json'
        saved = save_checkpoint(output / name, model=original,
            provenance={'objective': 'untrained_or_inherited', 'completed_updates': 0, 'training_input_sha256': None})
        inventory['initial'][str(seed)] = {'file': name, **saved}
        for law in LAWS:
            model = deepcopy(original)
            report = learn(model, batches[law], updates=settings['updates'], cpu_seconds=settings['cpu_seconds'],
                learning_rate=settings['learning_rate'], limit=settings['live_path_limit'],
                expansion_limit=settings['candidate_expansions'])
            name = f'{law}-{seed}.json'
            saved = save_checkpoint(output / name, model=model, provenance=report)
            inventory[law][str(seed)] = {'file': name, **saved}
            reports[f'{law}/{seed}'] = report
            io._write(output / f'fit-{law}-{seed}.json', report)
            print(json.dumps({'fit': f'{law}/{seed}', 'updates': report['completed_updates'],
                'cpu_seconds': report['fit_cpu_seconds'], 'stop_reason': report['stop_reason']}), flush=True)
        left, right = (reports[f'{law}/{seed}'] for law in LAWS)
        contract.require(all(left[k] == right[k] for k in ('initial_weights_sha256', 'parameters',
            'observed_events_per_update', 'action_events_per_update', 'visible_bits_per_update')),
            'paired initial state or exposure differs')
    complete = all(r['completed_updates'] == settings['updates'] for r in reports.values())
    io._write(output / 'training.json', {'version': config['version'], 'runtime': runtime,
        'prefit_sha256': io._hash(data / 'prefit.json'), 'attempt_sha256': io._hash(output / 'attempt.json'),
        'reports': reports, 'checkpoints': inventory, 'all_prescribed_updates_completed': complete,
        'status': 'COMPLETE' if complete else 'STOP_INCOMPLETE_EXPOSURE'})


def _training(data, fitted, config, frozen):
    """Bind fitted evidence to this prepared bank without running a predictor."""
    from .observed_io import load_batches
    training, attempt = io._read(fitted / 'training.json'), io._read(fitted / 'attempt.json')
    expected = io._hash(data / 'prefit.json')
    contract.require(training['prefit_sha256'] == attempt['prefit_sha256'] == expected and
        training['attempt_sha256'] == io._hash(fitted / 'attempt.json') and attempt['stage'] == 'fit' and
        training['version'] == config['version'], 'fit belongs to a different prefit bank')
    seeds, settings = config['model_seeds'], config['fit']
    contract.require(training['all_prescribed_updates_completed'] is True and training['status'] == 'COMPLETE' and
        set(training['reports']) == {f'{law}/{seed}' for law in LAWS for seed in seeds} and
        set(training['checkpoints']) == {*LAWS, 'initial'} and all(set(group) == {str(s) for s in seeds}
        for group in training['checkpoints'].values()), 'incomplete fitted inventory')
    checkpoints = {}
    for law, group in training['checkpoints'].items():
        for seed, item in group.items():
            contract.require(item['file'] == f'{law}-{seed}.json' and
                io._hash(fitted / item['file']) == item['sha256'], 'checkpoint artifact differs')
            saved = io._read(fitted / item['file'])
            contract.require(saved['state_sha256'] == item['state_sha256'] and
                saved['predictor']['configuration'] == config['model'] and
                saved['predictor']['kind'] == 'kernel', 'checkpoint model/state binding differs')
            checkpoints[law, seed] = saved
    for law in LAWS:
        name = f'{law}-train-inputs.json'
        batches = load_batches(data / name, frozen['artifacts'][name]['sha256'], batch_size=settings['batch_size'])
        histories = [b.digest() for b in batches]
        for seed in seeds:
            report, saved = training['reports'][f'{law}/{seed}'], checkpoints[law, str(seed)]
            initial = checkpoints['initial', str(seed)]
            required = {'training_input_sha256': contract.digest(histories), 'history_sha256': histories,
                'training_source_sha256': frozen['sources']['active_learning.py'],
                'initial_weights_sha256': initial['state_sha256'], 'final_weights_sha256': saved['state_sha256'],
                'objective': 'observed_joint_nll', 'status': 'COMPLETED', 'stop_reason': 'update_limit',
                'requested_updates': settings['updates'], 'completed_updates': settings['updates'],
                'parameters': config['parameters'], 'observed_events_per_update': config['data']['train']['events'],
                'action_events_per_update': config['data']['train']['events'],
                'visible_bits_per_update': config['data']['train']['visible_bits'],
                'learning_rate': settings['learning_rate'], 'cpu_ceiling_seconds': settings['cpu_seconds'],
                'live_path_limit': settings['live_path_limit'], 'candidate_expansion_limit': settings['candidate_expansions']}
            contract.require(all(report[k] == v for k, v in required.items()) and
                report == io._read(fitted / f'fit-{law}-{seed}.json') == saved['provenance'] and
                report['predictor'] == saved['predictor'] and initial['provenance'] == {
                    'objective': 'untrained_or_inherited', 'completed_updates': 0, 'training_input_sha256': None},
                'fitted evidence, exposure or tensor provenance differs')
    return training


def _participants(training, law, seeds):
    return {arm: {str(seed): training['checkpoints'][law if arm == 'matched' else
        next(x for x in LAWS if x != law)][str(seed)]['sha256'] for seed in seeds} for arm in ARMS}


def bind(data, fitted):
    config, frozen = verify(data)
    training, assets = _training(data, fitted, config, frozen), io._read(data / 'assets.json.xz')
    for law in LAWS:
        bundle = assets['banks'][law]['splits']['evaluation']
        inputs, oracle = bundle['inputs'], bundle['oracle']
        participants = _participants(training, law, config['model_seeds'])
        plan = {'version': 'active-acceptance-plan-v1', 'contract_sha256': contract.contract_digest(),
            'study_id': config['version'] + '-' + law, 'scope': 'PROSPECTIVE_DIAGNOSTIC',
            'input_sha256': contract.digest(inputs), 'oracle_sha256': contract.digest(oracle),
            'oracle_source_sha256': oracle['source_sha256'], 'information_law_sha256': oracle['information_law_sha256'],
            'model_seeds': config['model_seeds'], 'participants': participants, 'reference_participant': 'crossed',
            'cases': [{k: c[k] for k in ('episode', 'family', 'partition', 'lineage', 'pair_id', 'direction')}
                for c in bundle['cases']],
            'split_lineage': {**{s: sorted({c['lineage'] for c in assets['banks'][law]['splits'][s]['cases']})
                for s in ('train', 'evaluation')}, 'selection': [], 'calibration': []},
            'development_families': ['two_contact_chain'], 'software_sha256': contract.software_sources()}
        contract.validate_bundle(plan, inputs, oracle, [])
        io._write(fitted / f'plan-{law}.json', plan)


def collect(data, fitted, output):
    from .acceptance_runner import collect as record
    from .acceptance_scoring import evaluate, _safe
    config, frozen = verify(data)
    for name in ('attempt.json', 'training.json', 'plan-nand.json', 'plan-nor.json'): io._committed(fitted / name)
    training = _training(data, fitted, config, frozen)
    for law in (*LAWS, 'initial'):
        for item in training['checkpoints'][law].values():
            io._committed(fitted / item['file'])
            contract.require(io._hash(fitted / item['file']) == item['sha256'], 'frozen checkpoint differs')
    plans, inputs_by_law = {}, {}
    for law in LAWS:
        inputs_by_law[law] = io._read(data / f'{law}-evaluation-inputs.json')
        plan = contract.validate_plan(io._read(fitted / f'plan-{law}.json'), inputs_by_law[law])
        contract.require(plan['participants'] == _participants(training, law, config['model_seeds']) and
            plan['model_seeds'] == config['model_seeds'] and plan['study_id'] == config['version'] + '-' + law and
            plan['reference_participant'] == 'crossed' and all(plan[k] == v for k, v in
            frozen['evaluation_oracles'][law].items()), 'frozen collection plan binding differs')
        plans[law] = plan
    runtime = io._runtime(config)
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'attempt.json': io._write(output / 'attempt.json', {
        'checkpoint_commit': io._git('rev-parse', 'HEAD'), 'runtime': runtime,
        'prefit_sha256': io._hash(data / 'prefit.json'), 'training_sha256': io._hash(fitted / 'training.json'),
        'plan_sha256': {law: io._hash(fitted / f'plan-{law}.json') for law in LAWS}, 'one_attempt': True})}
    costs = {}
    for law in LAWS:
        inputs = inputs_by_law[law]
        for arm in ARMS:
            learned_law = law if arm == 'matched' else next(x for x in LAWS if x != law)
            for seed in config['model_seeds']:
                item = training['checkpoints'][learned_law][str(seed)]
                trace = record(inputs, checkpoint=fitted / item['file'], expected_sha256=item['sha256'],
                               participant=arm, model_seed=seed)
                name = f'trace-{law}-{arm}-{seed}.json.xz'
                artifacts[name] = io._write(output / name, trace)
                costs[f'{law}/{arm}/{seed}'] = trace['resources']
                print(json.dumps({'collected': f'{law}/{arm}/{seed}',
                    'cpu_seconds': trace['resources']['collection_cpu_seconds']}), flush=True)
    # Only after all forecasts are recorded, read evaluator assets and score.
    from . import mixed_composition_run as mixed, multisource_law_scoring as score
    assets = io._read(data / 'assets.json.xz')
    results, critical = {}, {}
    identities = {(c['episode'], c['step']) for c in assets['law_contrasts']}
    for law in LAWS:
        bundle = assets['banks'][law]['splits']['evaluation']
        traces = [io._read(output / f'trace-{law}-{arm}-{seed}.json.xz')
                  for arm in ARMS for seed in config['model_seeds']]
        report = evaluate(plans[law], bundle['inputs'], bundle['oracle'], traces)
        result = mixed.analyze(report, bundle, config, arms=ARMS, reference='crossed', candidate='matched',
            study='MULTISOURCE_LAWS', protocol_path=PROTOCOL,
            scope='Separate learned pairwise laws; fully observed one-step multisource compositions; full G2 remains open',
            training_updates=len(config['model_seeds']) * config['fit']['updates'])
        result['composition'] = score.summarize_composition(report['points'], bundle['cases'],
            config['model_seeds'], config['analysis'])
        critical[law] = [p for p in report['points'] if (p['episode'], p['step']) in identities]
        name = f'all-action-{law}.json.xz'
        artifacts[name] = io._write(output / name, _safe(report))
        results[law] = result
    contrast = score.compare_laws(critical, assets['law_contrasts'], config['model_seeds'],
                                  config['analysis']['law_contrast'])
    complete = all(r['decision']['execution_complete'] for r in results.values())
    checks = {law: r['decision']['decision'] == 'KEEP_MULTISOURCE_LAWS' and r['composition']['passed']
              for law, r in results.items()}
    checks['common_history_law_contrasts'] = contrast['passed']
    decision = {'decision': 'STOP_INCOMPLETE_EXECUTION' if not complete else
        'KEEP_MULTISOURCE_LAWS' if all(checks.values()) else 'REVISE_MULTISOURCE_LAWS',
        'execution_complete': complete, 'checks': checks, 'gate_g1': 'NOT_ADMITTED',
        'g1_development_readiness': 'PROCEED_TO_G2', 'scientific_admission': False,
        'new_training_updates': sum(r['completed_updates'] for r in training['reports'].values()),
        'new_parameters_each': 0, 'historical_checkpoints_changed': False}
    summary = _safe({'version': config['version'], 'by_law': results, 'law_contrasts': contrast,
        'decision': decision, 'collection_costs': costs, 'protocol_sha256': io._hash(PROTOCOL)})
    for name, value in (('summary.json.xz', summary), ('decision.json', decision)):
        artifacts[name] = io._write(output / name, value)
    io._write(output / 'manifest.json', {'version': config['version'], 'artifacts': artifacts,
        'artifacts_complete': True, 'execution_complete': complete, 'gate_g1': 'NOT_ADMITTED',
        'prefit_sha256': io._hash(data / 'prefit.json'), 'training_sha256': io._hash(fitted / 'training.json')})
    print(json.dumps(decision), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'fit', 'bind', 'collect'))
    parser.add_argument('--data', type=Path)
    parser.add_argument('--fitted', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.stage != 'prepare' and args.data is None: parser.error('--data required')
    if args.stage in ('bind', 'collect') and args.fitted is None: parser.error('--fitted required')
    if args.stage != 'bind' and args.output is None: parser.error('--output required')
    target = args.fitted if args.stage == 'bind' else args.output
    try:
        if args.stage == 'prepare': prepare(args.output)
        elif args.stage == 'fit': fit(args.data, args.output)
        elif args.stage == 'bind': bind(args.data, args.fitted)
        else: collect(args.data, args.fitted, args.output)
    except BaseException as error:
        if target.is_dir() and not (target / 'failure.json').exists():
            io._write(target / 'failure.json', {'stage': args.stage, 'type': type(error).__name__,
                'message': str(error), 'traceback': traceback.format_exc(), 'retry_permitted': False})
        raise


if __name__ == '__main__': main()
