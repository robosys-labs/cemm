"""One matched evidence substitution, using the existing training/acceptance APIs.

Prepare and commit -> fit once -> bind and commit -> collect once. Historical
continuation v1 sources/results stay intact. Only prepare imports generation.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import traceback

from . import acceptance_contract as contract, continuation_run as io

ROOT, SEEDS = io.ROOT, io.SEEDS
PROTOCOL = ROOT / 'alias_evidence_protocol_v1.json'
PREFIT = ROOT / 'data/alias-evidence-prefit-v1.json'
ARMS = ('ordinary', 'alias')


def sources():
    names = set(io._sources()) | {'alias_evidence_run.py', 'alias_evidence_data.py',
        'alias_evidence_protocol_v1.json', 'snapshots/alias_evidence_protocol_v1.sha256',
        'data/continuation-assets-v1.json.xz'}
    return {name: io._hash(ROOT / name) for name in sorted(names)}


def protocol():
    expected = (ROOT / 'snapshots/alias_evidence_protocol_v1.sha256').read_text().split()[0]
    contract.require(io._hash(PROTOCOL) == expected, 'alias protocol lock differs')
    return io._read(PROTOCOL)


def verify(data):
    io._committed(PREFIT)
    manifest = io._read(PREFIT)
    contract.require((data / 'prefit.json').read_bytes() == PREFIT.read_bytes(), 'prefit manifest differs')
    contract.require(manifest['sources'] == sources(), 'frozen source bytes differ')
    for name, info in manifest['artifacts'].items():
        contract.require(io._hash(data / name) == info['sha256'], 'prepared bytes differ: ' + name)
    return protocol()


def prepare(output):
    from .alias_evidence_data import build_assets
    config = protocol()
    assets = build_assets(config)
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {}
    values = {'ordinary-inputs.json': assets['splits']['train']['inputs'],
        'alias-inputs.json': assets['alias_training']['inputs'],
        'evaluation-inputs.json': assets['splits']['evaluation']['inputs'],
        'evaluation-oracle.json': assets['splits']['evaluation']['oracle'],
        'cases.json': {split: bundle['cases'] for split, bundle in assets['splits'].items()},
        'audit.json': assets['audit'], 'assets.json.xz': assets}
    for name, value in values.items(): artifacts[name] = io._write(output / name, value)
    io._write(output / 'prefit.json', {'version': 'alias-evidence-prefit-v1',
        'protocol_sha256': io._hash(PROTOCOL), 'sources': sources(), 'artifacts': artifacts,
        'gate_g1': 'NOT_ADMITTED'})
    print(json.dumps({'prepared': str(output), 'audit': assets['audit']}), flush=True)


def fit(data, output):
    from .active_learning import fit as learn
    from .active_checkpoint import save_checkpoint
    from .domain_kernel import DomainKernel
    from .observed_io import load_batches
    import torch
    config = verify(data)
    runtime = io._runtime(config)
    output.mkdir(parents=True, exist_ok=False)
    io._write(output / 'attempt.json', {'prefit_commit': io._git('rev-parse', 'HEAD'),
        'prefit_sha256': io._hash(PREFIT), 'runtime': runtime, 'one_attempt': True})
    settings, manifest = config['fit'], io._read(PREFIT)
    batches = {arm: load_batches(data / (arm + '-inputs.json'),
        manifest['artifacts'][arm + '-inputs.json']['sha256'], batch_size=settings['batch_size']) for arm in ARMS}
    reports, checkpoints = {}, {arm: {} for arm in ARMS}
    for seed in SEEDS:
        torch.manual_seed(seed)
        original = DomainKernel(**config['model'])
        initial = save_checkpoint(output / f'initial-{seed}.json', model=original,
            provenance={'objective': 'untrained_or_inherited', 'completed_updates': 0, 'training_input_sha256': None})
        for arm in ARMS:
            model = deepcopy(original)
            contract.require(sum(p.numel() for p in model.parameters()) == config['parameters'], 'parameter mismatch')
            report = learn(model, batches[arm], updates=settings['updates'], cpu_seconds=settings['cpu_seconds'],
                learning_rate=settings['learning_rate'], limit=settings['live_path_limit'],
                expansion_limit=settings['candidate_expansions'])
            name = f'{arm}-{seed}.json'
            saved = save_checkpoint(output / name, model=model, provenance=report)
            checkpoints[arm][str(seed)] = {'file': name, **saved}
            reports[f'{arm}/{seed}'] = report
            io._write(output / f'fit-{arm}-{seed}.json', report)
            print(json.dumps({'fit': f'{arm}/{seed}', 'updates': report['completed_updates'],
                'cpu_seconds': report['fit_cpu_seconds'], 'initial_checkpoint_sha256': initial['sha256']}), flush=True)
        a, b = (reports[f'{arm}/{seed}'] for arm in ARMS)
        contract.require(all(a[k] == b[k] for k in ('initial_weights_sha256', 'parameters',
            'observed_events_per_update', 'action_events_per_update', 'visible_bits_per_update')), 'paired exposure mismatch')
    complete = all(r['completed_updates'] == settings['updates'] for r in reports.values())
    io._write(output / 'training.json', {'version': 'alias-evidence-training-v1', 'runtime': runtime,
        'reports': reports, 'checkpoints': checkpoints, 'all_prescribed_updates_completed': complete,
        'status': 'COMPLETE' if complete else 'STOP_INCOMPLETE_EXPOSURE'})


def bind(data, fitted):
    verify(data)
    training, cases = io._read(fitted / 'training.json'), io._read(data / 'cases.json')
    inputs, oracle = io._read(data / 'evaluation-inputs.json'), io._read(data / 'evaluation-oracle.json')
    participants = {}
    for arm, seeds in training['checkpoints'].items():
        participants[arm] = {}
        for seed, item in seeds.items():
            contract.require(io._hash(fitted / item['file']) == item['sha256'], 'checkpoint bytes differ')
            participants[arm][seed] = item['sha256']
    plan = {'version': 'active-acceptance-plan-v1', 'contract_sha256': contract.contract_digest(),
        'study_id': 'alias-evidence-v1', 'scope': 'PROSPECTIVE_DIAGNOSTIC',
        'input_sha256': contract.digest(inputs), 'oracle_sha256': contract.digest(oracle),
        'oracle_source_sha256': oracle['source_sha256'], 'information_law_sha256': oracle['information_law_sha256'],
        'model_seeds': list(SEEDS), 'participants': participants, 'reference_participant': 'ordinary',
        'cases': [{k: row[k] for k in ('episode', 'family', 'partition', 'lineage', 'pair_id', 'direction')}
            for row in cases['evaluation']],
        'split_lineage': {split: sorted({r['lineage'] for r in rows}) for split, rows in cases.items()},
        'development_families': ['single_contact', 'two_contacts', 'self_contact'],
        'software_sha256': contract.software_sources()}
    contract.validate_bundle(plan, inputs, oracle, [])
    io._write(fitted / 'plan.json', plan)


def execution_complete(report):
    """Separate a scored participant failure from interrupted/invalid execution."""
    if report['metadata']['incomplete_inventory']: return False
    for failure in report['metadata']['failure_records']:
        evidence = failure.get('evidence', {})
        if not (failure.get('phase') == 'feedback' and failure.get('error_type') == 'ValueError' and
                failure.get('message') in ('visible evidence outside model support', 'observation outside model support') and
                evidence.get('impossible_observation') is True):
            return False
    return True


def analyze(report, cases, complete, config):
    from .continuation_summary import summarize, _metric
    by_arm = summarize(report['points'], cases, list(SEEDS))['by_arm']
    metadata = {c['episode']: c for c in cases}
    points = {(p['participant'], p['model_seed'], p['episode'], p['step']): p for p in report['points']}
    changes, checks, gains = {}, {}, []
    for seed in SEEDS:
        a, b = (by_arm[arm]['by_seed'][str(seed)] for arm in ARMS)
        for arm, summary in zip(ARMS, (a, b), strict=True):
            summary['self_by_prebit'] = {str(bit): _metric([p for p in report['points'] if
                p['participant'] == arm and p['model_seed'] == seed and
                metadata[p['episode']]['query_scope'] == 'self_contact' and
                metadata[p['episode']]['self_prebit'] == bit and p['step'] in metadata[p['episode']]['query_steps']])
                for bit in (0, 1)}
        changed = {scope: {'repaired': [], 'regressed': []} for scope in ('self_contact', 'continuation')}
        for c in cases:
            if c['query_scope'] == 'acquisition_only': continue
            for step in c['query_steps']:
                old, new = (points[arm, seed, c['episode'], step] for arm in ARMS)
                if old['correct'] != new['correct']:
                    changed[c['query_scope']]['repaired' if new['correct'] else 'regressed'].append([c['episode'], step])
        changes[str(seed)] = changed
        threshold = config['analysis']['accuracy_each_seed']
        checks[str(seed)] = {
            'self_both_bits': all(v['accuracy'] >= threshold for v in b['self_by_prebit'].values()),
            'self_support': b['self_contact']['support_coverage'] == 1.,
            'self_preservation': b['self_contact']['unchanged_bit_errors'] == 0,
            'continuation_accuracy': b['continuation']['accuracy'] >= threshold,
            'continuation_pairs': b['query_role_pairs']['exact_rate'] >= threshold,
            'continuation_support': b['continuation']['support_coverage'] == 1.,
            'continuation_preservation': b['continuation']['unchanged_bit_errors'] == 0,
            'no_new_continuation_errors': not changed['continuation']['regressed']}
        gains.append(b['self_contact']['accuracy'] - a['self_contact']['accuracy'])
    competent = all(all(row.values()) for row in checks.values())
    material = sum(gains) / len(gains) >= config['analysis']['material_self_gain'] and all(g > 0 for g in gains)
    decision = ('STOP_INCOMPLETE_EXECUTION' if not complete else 'REVISE_EVIDENCE_FIX' if not competent else
                'KEEP_EVIDENCE_FIX' if material else 'NO_MATERIAL_EVIDENCE_EFFECT')
    return {'version': 'alias-evidence-result-v1', 'by_arm': by_arm, 'changes': changes,
        'decision': {'decision': decision, 'gate_g1': 'NOT_ADMITTED', 'execution_complete': complete,
            'competence_checks': checks, 'competence_pass': competent, 'paired_self_accuracy_gains': gains,
            'mean_gain': sum(gains) / len(gains), 'material_gain_pass': material,
            'scope': 'Public fixed-law evidence intervention; no architecture superiority or broad calibration claim'}}


def collect(data, fitted, output):
    from .acceptance_runner import collect as record
    from .acceptance_scoring import evaluate
    config = verify(data)
    runtime = io._runtime(config)
    for path in (fitted / 'training.json', fitted / 'plan.json'): io._committed(path)
    training, plan = io._read(fitted / 'training.json'), io._read(fitted / 'plan.json')
    for seeds in training['checkpoints'].values():
        for item in seeds.values(): io._committed(fitted / item['file'])
    inputs, oracle = io._read(data / 'evaluation-inputs.json'), io._read(data / 'evaluation-oracle.json')
    cases = io._read(data / 'cases.json')['evaluation']
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'attempt.json': io._write(output / 'attempt.json', {'checkpoint_commit': io._git('rev-parse', 'HEAD'),
        'plan_sha256': io._hash(fitted / 'plan.json'), 'runtime': runtime})}
    traces = []
    for arm in ARMS:
        for seed in SEEDS:
            item = training['checkpoints'][arm][str(seed)]
            trace = record(inputs, checkpoint=fitted / item['file'], expected_sha256=item['sha256'],
                           participant=arm, model_seed=seed)
            name = f'trace-{arm}-{seed}.json.xz'
            artifacts[name] = io._write(output / name, trace)
            traces.append(trace)
            print(json.dumps({'collected': f'{arm}/{seed}', 'cpu_seconds': trace['resources']['collection_cpu_seconds']}), flush=True)
    report = evaluate(plan, inputs, oracle, traces)
    complete = training['all_prescribed_updates_completed'] and execution_complete(report)
    result = analyze(report, cases, complete, config)
    result.update(metadata=report['metadata'], collection_costs={f"{t['participant']}/{t['model_seed']}":
        t['resources'] for t in traces}, protocol_sha256=io._hash(PROTOCOL), prefit_sha256=io._hash(PREFIT))
    for name, value in (('all-action.json.xz', report), ('summary.json.xz', result), ('decision.json', result['decision'])):
        artifacts[name] = io._write(output / name, value)
    io._write(output / 'manifest.json', {'version': 'alias-evidence-results-v1', 'artifacts_complete': True,
        'execution_complete': complete, 'artifacts': artifacts, 'gate_g1': 'NOT_ADMITTED',
        'plan_sha256': io._hash(fitted / 'plan.json'), 'training_sha256': io._hash(fitted / 'training.json')})
    print(json.dumps(result['decision']), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'fit', 'bind', 'collect'))
    for name in ('data', 'fitted', 'output'): parser.add_argument('--' + name, type=Path)
    args = parser.parse_args()
    if args.stage != 'prepare' and args.data is None: parser.error('--data required')
    if args.stage in ('bind', 'collect') and args.fitted is None: parser.error('--fitted required')
    if args.stage != 'bind' and args.output is None: parser.error('--output required')
    try:
        if args.stage == 'prepare': prepare(args.output)
        elif args.stage == 'fit': fit(args.data, args.output)
        elif args.stage == 'bind': bind(args.data, args.fitted)
        else: collect(args.data, args.fitted, args.output)
    except BaseException as error:
        if args.output is not None and args.output.is_dir() and not (args.output / 'failure.json').exists():
            io._write(args.output / 'failure.json', {'stage': args.stage, 'type': type(error).__name__,
                'message': str(error), 'traceback': traceback.format_exc(), 'retry_permitted': False})
        raise


if __name__ == '__main__': main()
