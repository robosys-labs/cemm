"""One frozen development comparison, composed from the existing observed APIs.

prepare -> commit source/data -> fit once -> bind/commit actual checkpoints ->
collect once. Outputs are exclusive. Only prepare imports the world generator.
Selection/calibration tapes are reserved, never loaded by the fitter/collector.
"""
import argparse
from copy import deepcopy
from hashlib import sha256
import json
import lzma
import math
from pathlib import Path
import platform
import subprocess
import sys
import time
import traceback

from . import acceptance_contract as contract

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
PROTOCOL = ROOT / 'continuation_protocol_v1.json'
PREFIT = ROOT / 'data' / 'continuation-prefit-v1.json'
SEEDS = (7, 11, 23, 37, 53)


def _hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def _read(path):
    path = Path(path)
    raw = lzma.decompress(path.read_bytes()) if path.suffix == '.xz' else path.read_bytes()
    return json.loads(raw)


def _write(path, value):
    path = Path(path)
    raw = (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    if path.suffix == '.xz': raw = lzma.compress(raw, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64)
    with path.open('xb') as stream: stream.write(raw)
    return {'sha256': _hash(path), 'bytes': len(raw)}


def _protocol():
    expected = (ROOT / 'snapshots' / 'continuation_protocol_v1.sha256').read_text().split()[0]
    contract.require(_hash(PROTOCOL) == expected, 'protocol lock differs')
    return _read(PROTOCOL)


def _sources():
    names = set(contract.software_sources()) | {
        'active_learning.py', 'observed_io.py', 'prospective_data.py', 'prospective_oracle.py',
        'world.py', 'protocol.py', 'protocol.json', 'continuation_data.py', 'continuation_summary.py',
        'continuation_run.py', 'continuation_protocol_v1.json', 'snapshots/continuation_protocol_v1.sha256'}
    return {name: _hash(ROOT / name) for name in sorted(names)}


def _git(*args):
    return subprocess.check_output(['git', '-C', str(REPO), *args], text=True).strip()


def _committed(path):
    relative = Path(path).resolve().relative_to(REPO).as_posix()
    _git('ls-files', '--error-unmatch', relative)
    contract.require(_git('status', '--porcelain') == '', 'clean committed checkout required')
    contract.require(subprocess.check_output(['git', '-C', str(REPO), 'show', 'HEAD:' + relative]) ==
                     Path(path).read_bytes(), 'artifact differs from committed bytes')


def _verify(data):
    _committed(PREFIT)
    manifest = _read(PREFIT)
    contract.require((data / 'prefit.json').read_bytes() == PREFIT.read_bytes(), 'prefit manifest differs')
    contract.require(manifest['sources'] == _sources(), 'prefit source bytes differ')
    for name, info in manifest['artifacts'].items():
        contract.require(_hash(data / name) == info['sha256'], 'prepared bytes differ: ' + name)
    return _protocol()


def _runtime(config):
    import numpy as np
    import torch
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    actual = {'python': platform.python_version(), 'torch': str(torch.__version__),
        'numpy': np.__version__, 'threads': torch.get_num_threads(), 'dtype': 'float64',
        'deterministic_algorithms': torch.are_deterministic_algorithms_enabled()}
    contract.require(actual == config['execution']['runtime'], 'frozen runtime differs')
    return {**actual, 'platform': platform.platform(), 'cpu_architecture': platform.machine()}


def prepare(output):
    from .continuation_data import build_assets
    config = _protocol()
    output.mkdir(parents=True, exist_ok=False)
    assets = build_assets(config)
    artifacts = {}
    for split, bundle in assets['splits'].items():
        for kind in ('inputs', 'oracle'):
            name = split + '-' + kind + '.json'
            artifacts[name] = _write(output / name, bundle[kind])
    artifacts['cases.json'] = _write(output / 'cases.json',
        {split: bundle['cases'] for split, bundle in assets['splits'].items()})
    artifacts['audit.json'] = _write(output / 'audit.json', assets['audit'])
    artifacts['assets.json.xz'] = _write(output / 'assets.json.xz', assets)
    manifest = {'version': 'continuation-prefit-v1', 'protocol_sha256': _hash(PROTOCOL),
        'sources': _sources(), 'artifacts': artifacts, 'audit': assets['audit'],
        'scope': config['scope'], 'gate_g1': 'NOT_ADMITTED'}
    _write(output / 'prefit.json', manifest)
    print(json.dumps({'prepared': str(output), 'manifest_sha256': _hash(output / 'prefit.json'),
                      'audit': assets['audit']}), flush=True)


def fit(data, output):
    # No generator/oracle import or truth read in this stage.
    from .active_checkpoint import save_checkpoint
    from .active_learning import fit as learn, fit_empirical
    from .domain_kernel import DomainKernel
    from .domain_flat import DomainFlatGRU
    from .observed_io import load_batches
    import torch
    config = _verify(data)
    runtime = _runtime(config)
    output.mkdir(parents=True, exist_ok=False)
    _write(output / 'attempt.json', {'stage': 'fit', 'prefit_commit': _git('rev-parse', 'HEAD'),
        'prefit_sha256': _hash(PREFIT), 'runtime': runtime, 'one_attempt': True})
    settings = config['fit']
    batches = load_batches(data / 'train-inputs.json',
        _read(PREFIT)['artifacts']['train-inputs.json']['sha256'], batch_size=settings['batch_size'])
    inventory, reports = {}, {}
    initial_provenance = {'objective': 'untrained_or_inherited', 'completed_updates': 0,
                          'training_input_sha256': None}

    def save(arm, seed, **predictor):
        name = f'{arm}-{seed}.json'
        saved = save_checkpoint(output / name, **predictor)
        inventory.setdefault(arm, {})[str(seed)] = {'file': name, **saved}
        return saved

    for seed in SEEDS:
        torch.manual_seed(seed)
        shared = DomainKernel(hidden=11, persistence=False, role_tying=False, memory=True)
        reset = DomainKernel(hidden=11, persistence=False, role_tying=False, memory=False)
        reset.load_state_dict(shared.state_dict())
        torch.manual_seed(seed)
        flat = DomainFlatGRU(hidden=3, persistence=False)
        for arm, model in (('shared', shared), ('reset', reset), ('flat', flat)):
            contract.require(sum(p.numel() for p in model.parameters()) == config['neural_parameters_each'],
                             'parameter match failed')
            initial = save_checkpoint(output / f'initial-{arm}-{seed}.json', model=model,
                                      provenance=initial_provenance)
            if arm == 'shared': inventory.setdefault('untrained_shared', {})[str(seed)] = {
                'file': f'initial-{arm}-{seed}.json', **initial}
            report = learn(model, batches, updates=settings['updates'], cpu_seconds=settings['cpu_seconds'],
                learning_rate=settings['learning_rate'], limit=settings['live_path_limit'],
                expansion_limit=settings['candidate_expansions'])
            save(arm, seed, model=model, provenance=report)
            reports[f'{arm}/{seed}'] = report
            _write(output / f'fit-{arm}-{seed}.json', report)
            print(json.dumps({'fit': f'{arm}/{seed}', 'updates': report['completed_updates'],
                'cpu_seconds': report['fit_cpu_seconds'], 'stop_reason': report['stop_reason']}), flush=True)
    for arm, mode, first in (('empirical_local', 'local', False), ('empirical_contact', 'contact', False),
                            ('empirical_first_contact', 'contact', True), ('empirical_prefix', 'prefix', False)):
        wall, cpu = time.perf_counter(), time.process_time()
        memory, report = fit_empirical(batches, mode=mode, first_contact=first)
        report.update(fit_wall_seconds=time.perf_counter() - wall, fit_cpu_seconds=time.process_time() - cpu)
        saved = save(arm, SEEDS[0], memory=memory, provenance=report)
        reports[arm] = report
        for seed in SEEDS[1:]: inventory[arm][str(seed)] = deepcopy(inventory[arm][str(SEEDS[0])])
    save('no_change', SEEDS[0], control='no_change',
         provenance={'objective': 'no_change', 'completed_updates': 0, 'training_input_sha256': None})
    for seed in SEEDS[1:]: inventory['no_change'][str(seed)] = deepcopy(inventory['no_change'][str(SEEDS[0])])
    neural = [r for k, r in reports.items() if '/' in k]
    exposure = all(r['completed_updates'] == settings['updates'] for r in neural)
    contract.require(len({r['training_input_sha256'] for r in reports.values()}) == 1, 'fit input differs')
    _write(output / 'training.json', {'version': 'continuation-training-v1', 'runtime': runtime,
        'reports': reports, 'checkpoints': inventory, 'all_prescribed_updates_completed': exposure,
        'status': 'COMPLETE' if exposure else 'STOP_INCOMPLETE_EXPOSURE',
        'deterministic_control_reuse': config['execution']['deterministic_control_reuse']})


def bind(data, fitted):
    _verify(data)
    training, cases = _read(fitted / 'training.json'), _read(data / 'cases.json')
    inputs, oracle = _read(data / 'evaluation-inputs.json'), _read(data / 'evaluation-oracle.json')
    participants = {}
    for arm, seeds in training['checkpoints'].items():
        participants[arm] = {}
        for seed, item in seeds.items():
            contract.require(_hash(fitted / item['file']) == item['sha256'], 'checkpoint bytes differ')
            participants[arm][seed] = item['sha256']
    plan = {'version': 'active-acceptance-plan-v1', 'contract_sha256': contract.contract_digest(),
        'study_id': 'continuation-study-v1', 'scope': 'PROSPECTIVE_DIAGNOSTIC',
        'input_sha256': contract.digest(inputs), 'oracle_sha256': contract.digest(oracle),
        'oracle_source_sha256': oracle['source_sha256'], 'information_law_sha256': oracle['information_law_sha256'],
        'model_seeds': list(SEEDS), 'participants': participants, 'reference_participant': 'flat',
        'cases': [{k: row[k] for k in ('episode', 'family', 'partition', 'lineage', 'pair_id', 'direction')}
                  for row in cases['evaluation']],
        'split_lineage': {split: sorted({r['lineage'] for r in rows}) for split, rows in cases.items()},
        'development_families': ['single_contact', 'two_contacts'], 'software_sha256': contract.software_sources()}
    contract.validate_bundle(plan, inputs, oracle, [])
    _write(fitted / 'plan.json', plan)


def decision(by_arm, complete, config):
    for values in by_arm.values():
        contract.require(set(values['by_seed']) == {str(s) for s in SEEDS}, 'decision seed inventory differs')
        for entry in values['by_seed'].values():
            contract.require(set(entry['ood_family_accuracy']) == set(config['design']['ood_families']),
                             'decision OOD family inventory differs')
    shared, flat = (by_arm[a]['by_seed'] for a in ('shared', 'flat'))
    differences = [shared[str(s)]['ood_macro_accuracy'] - flat[str(s)]['ood_macro_accuracy'] for s in SEEDS]
    wins = sum(d > 0 for d in differences)
    p = sum(math.comb(len(SEEDS), k) for k in range(wins, len(SEEDS) + 1)) / 2 ** len(SEEDS)
    checks = {}
    for seed in SEEDS:
        a, b = shared[str(seed)], flat[str(seed)]
        pairs = [r for r in a['query_role_pairs']['records'] if r['family'] == 'two_contacts']
        checks[str(seed)] = {'in_family_accuracy': a['in_family_continuation']['accuracy'] >= .95,
            'in_family_pair_exactness': sum(r['both_exact'] for r in pairs) / len(pairs) >= .95,
            'continuation_support': a['continuation']['support_coverage'] == 1.,
            'continuation_preservation': a['continuation']['unchanged_bit_errors'] == 0,
            'in_family_reference_nonregression': a['in_family_continuation']['accuracy'] >= b['in_family_continuation']['accuracy']}
    mean = lambda values: sum(values) / len(values)
    candidate = mean([shared[str(s)]['ood_macro_accuracy'] for s in SEEDS])
    empirical = {arm: mean([entry['ood_macro_accuracy'] for entry in values['by_seed'].values()])
                 for arm, values in by_arm.items() if arm.startswith('empirical_')}
    competent = all(all(row.values()) for row in checks.values())
    material = mean(differences) >= config['analysis']['material_mean_gain']
    matched = max(empirical.values()) >= candidate - config['analysis']['empirical_match_tolerance']
    outcome = ('STOP_INCOMPLETE_RUN' if not complete else 'REJECT_CURRENT_CONFIGURATION' if not competent else
        'REJECT_SUPERIORITY_SIMPLIFY' if matched else 'KEEP_BOUNDED_ADVANTAGE' if material and wins == 5 and p <= .05 else
        'REJECT_MATERIAL_ADVANTAGE')
    return {'decision': outcome, 'gate_g1': 'NOT_ADMITTED', 'paired_ood_macro_differences': differences,
        'mean_gain': mean(differences), 'positive_seeds': wins, 'one_sided_sign_p': p,
        'sign_test_scope': config['analysis']['seed_test_null'], 'competence_checks': checks,
        'mean_shared_ood_macro': candidate, 'empirical_ood_macro': empirical, 'empirical_matches': matched,
        'material_gain_pass': material, 'competence_pass': competent, 'run_complete': complete}


def collect(data, fitted, output):
    from .acceptance_runner import collect as record
    from .acceptance_scoring import evaluate, _comparisons
    from .continuation_summary import summarize
    config = _verify(data)
    runtime = _runtime(config)
    for path in (fitted / 'training.json', fitted / 'plan.json'): _committed(path)
    training, plan = _read(fitted / 'training.json'), _read(fitted / 'plan.json')
    for seeds in training['checkpoints'].values():
        for item in seeds.values():
            _committed(fitted / item['file'])
            contract.require(_hash(fitted / item['file']) == item['sha256'], 'checkpoint hash differs')
    inputs, oracle = _read(data / 'evaluation-inputs.json'), _read(data / 'evaluation-oracle.json')
    cases = _read(data / 'cases.json')['evaluation']
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'attempt.json': _write(output / 'attempt.json', {'stage': 'collection',
        'checkpoint_commit': _git('rev-parse', 'HEAD'), 'plan_sha256': _hash(fitted / 'plan.json'), 'runtime': runtime})}
    by_arm, slim_points, costs, failures = {}, [], {}, {}
    complete = training['all_prescribed_updates_completed']
    for arm in plan['participants']:
        traces = []
        for seed in SEEDS:
            item = training['checkpoints'][arm][str(seed)]
            trace = record(inputs, checkpoint=fitted / item['file'], expected_sha256=item['sha256'],
                           participant=arm, model_seed=seed)
            name = f'trace-{arm}-{seed}.json.xz'
            artifacts[name] = _write(output / name, trace)
            costs[f'{arm}/{seed}'] = trace['resources']
            traces.append(trace)
            print(json.dumps({'collected': f'{arm}/{seed}', 'cpu_seconds': trace['resources']['collection_cpu_seconds']}), flush=True)
        projected = deepcopy(plan)
        projected['participants'] = {arm: plan['participants'][arm]}
        projected['reference_participant'] = arm
        report = evaluate(projected, inputs, oracle, traces)
        name = f'all-action-{arm}.json.xz'
        artifacts[name] = _write(output / name, report)
        supplemental = summarize(report['points'], cases, list(SEEDS))['by_arm']
        for entry in supplemental[arm]['by_seed'].values():
            ambiguous = entry['acquisition_ambiguous']
            entry['acquisition_expected_floor_excess'] = {
                key: value - floor if isinstance(value, (int, float)) else value
                for key, value, floor in (('nll', ambiguous['mean_nll'], math.log(2)),
                                         ('brier', ambiguous['mean_brier'], .5))}
        by_arm.update(supplemental)
        failures[arm] = report['metadata']
        complete &= (not report['metadata']['failure_records'] and not report['metadata']['incomplete_inventory']
                     and all(p['status'] != 'UNPRODUCED' for p in report['points']))
        slim_points.extend({k: p[k] for k in ('participant', 'model_seed', 'episode', 'step', 'lineage', 'status', 'correct')}
                           for p in report['points'])
        del traces, report
    summary = {'version': 'continuation-result-v1', 'by_arm': by_arm, 'collection_costs': costs,
        'metadata': failures, 'decision': decision(by_arm, complete, config),
        'all_action_comparisons': _comparisons(slim_points, 'flat'),
        'fit_status': training['status'], 'protocol_sha256': _hash(PROTOCOL), 'prefit_sha256': _hash(PREFIT)}
    artifacts['summary.json.xz'] = _write(output / 'summary.json.xz', summary)
    artifacts['decision.json'] = _write(output / 'decision.json', summary['decision'])
    _write(output / 'manifest.json', {'version': 'continuation-results-v1', 'artifacts_complete': True,
        'run_complete': complete,
        'artifacts': artifacts, 'plan_sha256': _hash(fitted / 'plan.json'),
        'training_sha256': _hash(fitted / 'training.json'), 'gate_g1': 'NOT_ADMITTED'})
    print(json.dumps(summary['decision']), flush=True)


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
    if args.output is not None and args.output.exists(): raise FileExistsError(args.output)
    try:
        if args.stage == 'prepare': prepare(args.output)
        elif args.stage == 'fit': fit(args.data, args.output)
        elif args.stage == 'bind': bind(args.data, args.fitted)
        else: collect(args.data, args.fitted, args.output)
    except BaseException as error:
        if args.output is not None and args.output.is_dir() and not (args.output / 'failure.json').exists():
            _write(args.output / 'failure.json', {'stage': args.stage, 'type': type(error).__name__,
                'message': str(error), 'traceback': traceback.format_exc(), 'retry_permitted': False})
        raise
    return 0


if __name__ == '__main__':
    sys.exit(main())
