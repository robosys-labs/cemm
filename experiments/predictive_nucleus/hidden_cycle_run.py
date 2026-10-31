"""Freeze and collect one hidden-intermediate challenge with unchanged weights.

Prepare -> publish source/data/plans -> collect once. No fitting entry point.
All observed-only traces precede evaluator targets and probability scoring.
"""
import argparse
import json
from pathlib import Path
import subprocess
import traceback

from . import acceptance_contract as contract, continuation_run as io
from . import multisource_law_run as previous

ROOT = io.ROOT
PROTOCOL = ROOT / 'hidden_cycle_protocol_v1.json'
FITTED = ROOT / 'data/multisource-law-fit-v1'
LAWS = ('nand', 'nor')


def protocol():
    lock = ROOT / 'snapshots/hidden_cycle_protocol_v1.sha256'
    return contract.load_json(PROTOCOL, lock.read_text().split()[0])


def sources():
    names = set(previous.sources()) | {
        'hidden_cycle_run.py', 'hidden_cycle_data.py', 'hidden_cycle_scoring.py',
        PROTOCOL.name, 'snapshots/hidden_cycle_protocol_v1.sha256',
        'data/multisource-law-v1/assets.json.xz',
        'data/multisource-law-fit-v1/training.json',
        'data/multisource-law-fit-v1/plan-nand.json',
        'data/multisource-law-fit-v1/plan-nor.json'}
    return {name: io._hash(ROOT / name) for name in sorted(names)}


def checkpoints(config):
    """Verify historical provenance and bytes without loading or evaluating weights."""
    training = io._read(FITTED / 'training.json')
    seeds = [str(seed) for seed in config['model_seeds']]
    contract.require(training['status'] == 'COMPLETE' and
        training['all_prescribed_updates_completed'] is True, 'historical fit incomplete')
    inventory = {law: training['checkpoints'][law] for law in LAWS}
    names = ['training.json', 'attempt.json', 'plan-nand.json', 'plan-nor.json']
    for law, items in inventory.items():
        contract.require(set(items) == set(seeds), 'checkpoint seed inventory differs')
        for seed, item in items.items():
            contract.require(item['file'] == f'{law}-{seed}.json' and
                io._hash(FITTED / item['file']) == item['sha256'], 'historical checkpoint differs')
            saved = io._read(FITTED / item['file'])
            contract.require(saved['state_sha256'] == item['state_sha256'] and
                saved['provenance'] == training['reports'][f'{law}/{seed}'] and
                saved['provenance']['parameters'] == config['parameters'] and
                saved['provenance']['completed_updates'] == 128,
                'historical checkpoint provenance differs')
            names.append(item['file'])
    for name in names:
        path = FITTED / name
        original = subprocess.check_output(['git', '-C', str(io.REPO), 'show',
            config['checkpoint_commit'] + ':' + path.relative_to(io.REPO).as_posix()])
        contract.require(original == path.read_bytes(), 'historical bytes differ: ' + name)
    return inventory


def plan_for(bundle, law, inventory, config):
    inputs, oracle = bundle['inputs'], bundle['oracle']
    old = io._read(FITTED / f'plan-{law}.json')
    plan = {'version': 'active-acceptance-plan-v1', 'contract_sha256': contract.contract_digest(),
        'study_id': config['version'] + '-' + law, 'scope': 'PROSPECTIVE_DIAGNOSTIC',
        'input_sha256': contract.digest(inputs), 'oracle_sha256': contract.digest(oracle),
        'oracle_source_sha256': oracle['source_sha256'],
        'information_law_sha256': oracle['information_law_sha256'],
        'model_seeds': config['model_seeds'], 'participants': {'frozen': {
            str(seed): inventory[law][str(seed)]['sha256'] for seed in config['model_seeds']}},
        'reference_participant': 'frozen',
        'cases': [{k: case[k] for k in ('episode', 'family', 'partition', 'lineage', 'pair_id', 'direction')}
            for case in bundle['cases']],
        'split_lineage': {**old['split_lineage'],
            'evaluation': sorted({case['lineage'] for case in bundle['cases']})},
        'development_families': old['development_families'],
        'software_sha256': contract.software_sources()}
    contract.validate_bundle(plan, inputs, oracle, [])
    return plan


def prepare(output):
    from .hidden_cycle_data import build_assets
    config = protocol()
    assets = build_assets({'version': config['version'], 'data': {
        k: config['data'][k] for k in ('entity_counts', 'split_seed')}})
    inventory = checkpoints(config)
    plans = {}
    for law, bundle in assets['banks'].items():
        episodes, cases = bundle['inputs']['episodes'], bundle['cases']
        rows = [r for episode in bundle['information']['episodes'] for r in episode['forecasts']]
        expected = config['data']
        contract.require(len(episodes) == expected['episodes_per_law'] and
            sum(len(e['actions']) for e in episodes) == expected['forecasts_per_law_seed'] and
            sum(c['critical'] and c['condition'] == 'hidden' for c in cases) == expected['critical_pairs_per_law'] and
            sum(len(r['possible_worlds']) == 1 for r in rows) == expected['identifiable_per_law_seed'],
            'prepared inventory differs from frozen protocol')
        plans[law] = plan_for(bundle, law, inventory, config)
    contract.require(set(assets['banks']) == set(LAWS), 'law inventory differs')
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'assets.json.xz': io._write(output / 'assets.json.xz', assets)}
    for law in LAWS:
        for kind, value in (('inputs', assets['banks'][law]['inputs']), ('plan', plans[law])):
            name = f'{law}-{kind}.json'
            artifacts[name] = io._write(output / name, value)
    io._write(output / 'freeze.json', {'version': config['version'], 'sources': sources(),
        'protocol_sha256': io._hash(PROTOCOL), 'artifacts': artifacts,
        'checkpoint_commit': config['checkpoint_commit'], 'checkpoints': inventory,
        'training_permitted': False, 'gate_g1': 'NOT_ADMITTED'})
    print(json.dumps({'prepared': str(output), 'audit': assets['audit']}), flush=True)


def verify(data):
    io._committed(data / 'freeze.json')
    config, frozen = protocol(), io._read(data / 'freeze.json')
    contract.require(frozen['sources'] == sources() and frozen['protocol_sha256'] == io._hash(PROTOCOL) and
        frozen['version'] == config['version'] and frozen['training_permitted'] is False and
        frozen['checkpoint_commit'] == config['checkpoint_commit'], 'frozen source/protocol differs')
    expected_names = {'assets.json.xz', *(f'{law}-{kind}.json' for law in LAWS for kind in ('inputs', 'plan'))}
    contract.require(set(frozen['artifacts']) == expected_names, 'frozen artifact inventory differs')
    for name, item in frozen['artifacts'].items():
        contract.require(io._hash(data / name) == item['sha256'], 'prepared artifact differs: ' + name)
    inventory = checkpoints(config)
    contract.require(frozen['checkpoints'] == inventory, 'frozen checkpoint inventory differs')
    inputs_by_law, plans = {}, {}
    for law in LAWS:
        inputs = contract.validate_inputs(io._read(data / f'{law}-inputs.json'))
        plan = contract.validate_plan(io._read(data / f'{law}-plan.json'), inputs)
        contract.require(plan['study_id'] == config['version'] + '-' + law and
            plan['model_seeds'] == config['model_seeds'] and plan['participants'] == {'frozen': {
                str(seed): inventory[law][str(seed)]['sha256'] for seed in config['model_seeds']}},
            'frozen plan/checkpoint binding differs')
        inputs_by_law[law], plans[law] = inputs, plan
    return config, frozen, inventory, inputs_by_law, plans


def collect(data, output):
    from .acceptance_runner import collect as record
    config, frozen, inventory, inputs, plans = verify(data)
    runtime = io._runtime(config)
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'attempt.json': io._write(output / 'attempt.json', {
        'source_data_commit': io._git('rev-parse', 'HEAD'), 'runtime': runtime,
        'freeze_sha256': io._hash(data / 'freeze.json'), 'one_attempt': True,
        'new_training_updates': 0})}
    costs = {}
    for law in LAWS:
        for seed in config['model_seeds']:
            item = inventory[law][str(seed)]
            trace = record(inputs[law], checkpoint=FITTED / item['file'],
                expected_sha256=item['sha256'], participant='frozen', model_seed=seed)
            name = f'trace-{law}-{seed}.json.xz'
            artifacts[name] = io._write(output / name, trace)
            costs[f'{law}/{seed}'] = trace['resources']
            print(json.dumps({'collected': f'{law}/{seed}',
                'cpu_seconds': trace['resources']['collection_cpu_seconds']}), flush=True)
    # No target/oracle asset is parsed until every observed-only trace is saved.
    from .acceptance_scoring import evaluate, _safe
    from .hidden_cycle_scoring import analyze
    assets, results = io._read(data / 'assets.json.xz'), {}
    for law in LAWS:
        bundle = assets['banks'][law]
        traces = [io._read(output / f'trace-{law}-{seed}.json.xz') for seed in config['model_seeds']]
        report = evaluate(plans[law], bundle['inputs'], bundle['oracle'], traces)
        results[law] = analyze(report, bundle, config)
        name = f'all-action-{law}.json.xz'
        artifacts[name] = io._write(output / name, _safe(report))
    complete = all(r['decision']['execution_complete'] for r in results.values())
    checks = {law: r['decision']['decision'] == 'KEEP_HIDDEN_CYCLE' for law, r in results.items()}
    decision = {'decision': 'STOP_INCOMPLETE_EXECUTION' if not complete else
        'KEEP_HIDDEN_CYCLE' if all(checks.values()) else 'REVISE_HIDDEN_CYCLE',
        'execution_complete': complete, 'checks': checks, 'gate_g1': 'NOT_ADMITTED',
        'g1_development_readiness': 'PROCEED_TO_G2', 'scientific_admission': False,
        'new_training_updates': 0, 'new_parameters_each': 0, 'historical_checkpoints_changed': False}
    summary = _safe({'version': config['version'], 'by_law': results, 'decision': decision,
        'collection_costs': costs, 'protocol_sha256': io._hash(PROTOCOL)})
    for name, value in (('summary.json.xz', summary), ('decision.json', decision)):
        artifacts[name] = io._write(output / name, value)
    io._write(output / 'manifest.json', {'version': config['version'], 'artifacts': artifacts,
        'artifacts_complete': True, 'execution_complete': complete,
        'freeze_sha256': io._hash(data / 'freeze.json'), 'gate_g1': 'NOT_ADMITTED'})
    print(json.dumps(decision), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'collect'))
    parser.add_argument('--data', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.stage == 'collect' and args.data is None: parser.error('--data required')
    existed = args.output.exists()
    try:
        if args.stage == 'prepare': prepare(args.output)
        else: collect(args.data, args.output)
    except BaseException as error:
        if not existed and args.output.is_dir() and not (args.output / 'failure.json').exists():
            io._write(args.output / 'failure.json', {'stage': args.stage, 'type': type(error).__name__,
                'message': str(error), 'traceback': traceback.format_exc(), 'retry_permitted': False})
        raise


if __name__ == '__main__': main()
