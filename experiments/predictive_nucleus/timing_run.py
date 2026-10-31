"""Publish the timing freeze, then collect once with ten unchanged checkpoints."""
import argparse
import json
from pathlib import Path
import traceback

from . import acceptance_contract as base, continuation_run as io, hidden_cycle_run as historical
from . import timing_contract as contract

ROOT, FITTED, LAWS = io.ROOT, historical.FITTED, historical.LAWS
PROTOCOL = ROOT / 'timing_protocol_v1.json'


def protocol():
    return base.load_json(PROTOCOL, (ROOT / 'snapshots/timing_protocol_v1.sha256').read_text().split()[0])


def sources():
    names = set(historical.sources()) | {'timing_contract.py', 'timing_kernel.py', 'timing_session.py',
        'timing_runner.py', 'timing_evaluate.py', 'timing_scoring.py', 'timing_data.py', 'timing_oracle.py',
        'timing_run.py', PROTOCOL.name, 'snapshots/timing_protocol_v1.sha256'}
    return {name: io._hash(ROOT / name) for name in sorted(names)}


def prepare(output):
    from .timing_data import build_assets
    config = protocol()
    assets = build_assets({'version': config['version'], 'data': {
        k: config['data'][k] for k in ('entity_counts', 'split_seed')}})
    inventory, plans = historical.checkpoints(config), {}
    for law, bundle in assets['banks'].items():
        inputs = contract.validate_inputs(bundle['inputs'])
        count = sum(len(e['actions']) for e in inputs['episodes'])
        info = [r for e in bundle['information']['episodes'] for r in e['forecasts']]
        base.require(len(inputs['episodes']) == config['data']['episodes_per_law'] and
            count == config['data']['forecasts_per_law_seed'] and
            sum(len(r['possible_worlds']) == 1 for r in info) == config['data']['identifiable_per_law_seed'] and
            sum(c['critical'] for c in bundle['timing_contrasts']) == config['analysis']['critical_pairs'],
            'prepared timing inventory differs')
        plans[law] = {'version': 'timing-plan-v1', 'study_id': config['version'] + '-' + law,
            'scope': config['scope'], 'input_sha256': base.digest(inputs),
            **{k + '_sha256': base.digest(bundle[k]) for k in ('oracle', 'information', 'cases')},
            'model_seeds': config['model_seeds'], 'checkpoints': {
                str(seed): inventory[law][str(seed)]['sha256'] for seed in config['model_seeds']},
            'checkpoint_states': {str(seed): inventory[law][str(seed)]['state_sha256'] for seed in config['model_seeds']},
            'software_sha256': sources(), 'gate_g1': 'NOT_ADMITTED'}
    base.require(set(assets['banks']) == set(LAWS), 'law inventory differs')
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
    base.require(frozen['sources'] == sources() and frozen['protocol_sha256'] == io._hash(PROTOCOL) and
        frozen['version'] == config['version'] and frozen['training_permitted'] is False and
        frozen['checkpoint_commit'] == config['checkpoint_commit'], 'frozen timing source/protocol differs')
    expected = {'assets.json.xz', *(f'{law}-{kind}.json' for law in LAWS for kind in ('inputs', 'plan'))}
    base.require(set(frozen['artifacts']) == expected, 'frozen artifact inventory differs')
    for name, item in frozen['artifacts'].items():
        base.require(io._hash(data / name) == item['sha256'], 'prepared artifact differs: ' + name)
    inventory = historical.checkpoints(config)
    base.require(frozen['checkpoints'] == inventory, 'historical checkpoints differ')
    inputs, plans = {}, {}
    for law in LAWS:
        inputs[law] = contract.validate_inputs(io._read(data / f'{law}-inputs.json'))
        plan = io._read(data / f'{law}-plan.json')
        base.require(plan['version'] == 'timing-plan-v1' and plan['study_id'] == config['version'] + '-' + law and
            plan['input_sha256'] == base.digest(inputs[law]) and plan['software_sha256'] == sources() and
            plan['model_seeds'] == config['model_seeds'] and plan['checkpoints'] == {
                str(seed): inventory[law][str(seed)]['sha256'] for seed in config['model_seeds']} and
            plan['checkpoint_states'] == {str(seed): inventory[law][str(seed)]['state_sha256']
                for seed in config['model_seeds']}, 'timing plan/checkpoint binding differs')
        plans[law] = plan
    return config, frozen, inventory, inputs, plans


def collect(data, output):
    from .timing_runner import collect as record
    config, frozen, inventory, inputs, plans = verify(data)
    runtime = io._runtime(config)
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'attempt.json': io._write(output / 'attempt.json', {
        'source_data_commit': io._git('rev-parse', 'HEAD'), 'runtime': runtime,
        'freeze_sha256': io._hash(data / 'freeze.json'), 'one_attempt': True, 'new_training_updates': 0})}
    costs = {}
    for law in LAWS:
        for seed in config['model_seeds']:
            item = inventory[law][str(seed)]
            trace = record(inputs[law], checkpoint=FITTED / item['file'],
                           expected_sha256=item['sha256'], model_seed=seed)
            name = f'trace-{law}-{seed}.json.xz'
            artifacts[name] = io._write(output / name, trace)
            costs[f'{law}/{seed}'] = trace['resources']
            print(json.dumps({'collected': f'{law}/{seed}',
                'cpu_seconds': trace['resources']['collection_cpu_seconds'],
                'failures': sum(e['failure'] is not None for e in trace['episodes'])}), flush=True)
    # Read evaluator-only gold AFTER all ten observed-only traces are durable.
    from .acceptance_scoring import _safe
    from .timing_evaluate import evaluate
    from .timing_scoring import summarize
    assets, results, complete = io._read(data / 'assets.json.xz'), {}, True
    for law in LAWS:
        traces = [io._read(output / f'trace-{law}-{seed}.json.xz') for seed in config['model_seeds']]
        report, cases = evaluate(plans[law], assets['banks'][law], traces)
        results[law] = summarize(report['points'], cases, config['model_seeds'], config['analysis'])
        complete &= report['execution_complete'] and results[law]['decision']['execution_complete']
        name = f'all-action-{law}.json.xz'
        artifacts[name] = io._write(output / name, _safe(report))
    checks = {law: result['decision']['decision'] == 'KEEP_TIMING' for law, result in results.items()}
    decision = {'decision': 'STOP_INCOMPLETE_EXECUTION' if not complete else
        'KEEP_TIMING' if all(checks.values()) else 'REVISE_TIMING', 'execution_complete': complete,
        'checks': checks, 'gate_g1': 'NOT_ADMITTED', 'g1_development_readiness': 'PROCEED_TO_G2',
        'scientific_admission': False, 'new_training_updates': 0, 'new_parameters_each': 0,
        'new_inference_scheduler': True, 'native_inference_sources_changed': False,
        'historical_checkpoints_changed': False}
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
