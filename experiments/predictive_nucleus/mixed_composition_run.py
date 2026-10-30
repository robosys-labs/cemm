"""Frozen-weight composition challenges; no fitting or runtime changes.

Prepare and commit the source, protocol, assets and checkpoint inventory, then
collect once. The existing collector receives observed inputs only. Evaluator
probabilities are joined after every forecast has been recorded.
"""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import subprocess
import traceback

from . import acceptance_contract as contract, continuation_run as io

ROOT = io.ROOT
PROTOCOL = ROOT / 'mixed_composition_protocol_v1.json'
FITTED = ROOT / 'data/alias-evidence-fit-v2'
ARMS = ('ordinary', 'alias')


def protocol():
    lock = ROOT / 'snapshots' / (PROTOCOL.stem + '.sha256')
    return contract.load_json(PROTOCOL, lock.read_text().split()[0])


def sources():
    names = set(contract.software_sources()) | {
        'mixed_composition_run.py', 'mixed_composition_data.py',
        'prospective_data.py', 'prospective_oracle.py', 'world.py',
        'continuation_run.py', 'protocol.py', 'protocol.json', PROTOCOL.name,
        'snapshots/' + PROTOCOL.stem + '.sha256',
        'data/alias-evidence-fit-v2/training.json', 'data/alias-evidence-fit-v2/plan.json',
        *('data/' + name for name in ('prospective-assets-v1.json.xz', 'continuation-assets-v1.json.xz',
          'alias-evidence-assets-v1.json.xz', 'alias-evidence-assets-v2.json.xz'))}
    if PROTOCOL.name == 'joint_correlation_protocol_v1.json':
        names.update(('joint_correlation_data.py', 'data/mixed-composition-v1/assets.json.xz'))
    return {name: io._hash(ROOT / name) for name in sorted(names)}


def prepare(output):
    config = protocol()
    if 'critical_contrast' in config['analysis']:
        from .joint_correlation_data import build_assets
    else:
        from .mixed_composition_data import build_assets
    assets = build_assets({'version': config['version'], 'data': {
        k: config['data'][k] for k in ('entity_counts', 'split_seed')}})
    contract.require(assets['audit']['episode_views'] == config['data']['episodes'] and
        assets['audit']['physical_lineages'] == config['data']['physical_lineages'] and
        assets['audit']['max_cumulative_missing_bits'] <= config['data']['max_cumulative_missing_bits'],
        'prepared inventory differs from protocol')
    if 'critical_contrast' in config['analysis']:
        audit, settings = assets['audit'], config['data']
        contract.require(all(audit[a] == settings[b] for a, b in (
            ('planned_forecasts', 'planned_forecasts'), ('identifiable_points', 'identifiable_forecasts'),
            ('ambiguous_points', 'ambiguous_forecasts'), ('contrast_pairs', 'critical_contrast_pairs'),
            ('expected_best_all_action_accuracy', 'expected_best_all_action_accuracy'))) and
            audit['contrast_pairs'] == config['analysis']['critical_contrast']['pairs'],
            'correlation inventory differs from protocol')
        control = audit['factorized_control']
        contract.require(control['contrast_pairs'] == audit['contrast_pairs'] and
            control['target_one_range'] == [.5, .5] and control['max_abs_gap'] == 0.,
            'marginal information-loss control differs')
    old_plan = io._read(FITTED / 'plan.json')
    inventory = io._read(FITTED / 'training.json')['checkpoints']
    pinned_files = ['training.json', 'plan.json'] + [inventory[arm][str(seed)]['file']
        for arm in ARMS for seed in config['model_seeds']]
    for name in pinned_files:
        path = FITTED / name
        original = subprocess.check_output(['git', '-C', str(io.REPO), 'show',
            config['checkpoint_commit'] + ':' + path.relative_to(io.REPO).as_posix()])
        contract.require(original == path.read_bytes(), 'checkpoint differs from pinned commit')
    for arm in ARMS:
        for seed in config['model_seeds']:
            item = inventory[arm][str(seed)]
            contract.require(io._hash(FITTED / item['file']) == item['sha256'], 'checkpoint differs')
    inputs, oracle = assets['inputs'], assets['oracle']
    plan = {'version': 'active-acceptance-plan-v1', 'contract_sha256': contract.contract_digest(),
        'study_id': config['version'], 'scope': 'PROSPECTIVE_DIAGNOSTIC',
        'input_sha256': contract.digest(inputs), 'oracle_sha256': contract.digest(oracle),
        'oracle_source_sha256': oracle['source_sha256'],
        'information_law_sha256': oracle['information_law_sha256'],
        'model_seeds': config['model_seeds'],
        'participants': {arm: {str(seed): inventory[arm][str(seed)]['sha256']
            for seed in config['model_seeds']} for arm in ARMS},
        'reference_participant': 'ordinary',
        'cases': [{k: c[k] for k in ('episode', 'family', 'partition', 'lineage', 'pair_id', 'direction')}
            for c in assets['cases']],
        'split_lineage': {**old_plan['split_lineage'],
            'evaluation': sorted({c['lineage'] for c in assets['cases']})},
        'development_families': old_plan['development_families'],
        'software_sha256': contract.software_sources()}
    contract.validate_bundle(plan, inputs, oracle, [])
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {name: io._write(output / name, value) for name, value in
        (('assets.json.xz', assets), ('plan.json', plan))}
    io._write(output / 'freeze.json', {'version': config['version'], 'sources': sources(),
        'protocol_sha256': io._hash(PROTOCOL), 'artifacts': artifacts,
        'checkpoint_commit': config['checkpoint_commit'], 'checkpoints': inventory,
        'training_permitted': False, 'gate_g1': 'NOT_ADMITTED'})
    print(json.dumps({'prepared': str(output), 'audit': assets['audit']}), flush=True)


def correlation_scores(points, cases, limits):
    """Retain every planned observed-history contrast, including missing answers."""
    inventory, indexed = defaultdict(dict), {(p['episode'], p['step']): p for p in points}
    for case in cases:
        members, condition = inventory[case['contrast_id']], case['condition']
        contract.require(condition in ('equal', 'opposite') and condition not in members,
                         'invalid or duplicate contrast condition')
        contract.require(case['expected_target_bit'] == int(condition == 'opposite'),
                         'contrast target differs from protocol')
        members[condition] = case
    rows = []
    for identity, members in sorted(inventory.items()):
        row = {'contrast_id': identity, 'equal_episode': None, 'opposite_episode': None,
               'p_one_equal': None, 'p_one_opposite': None, 'gap': None,
               'complete': False, 'passed': False}
        for condition, case in members.items():
            row[condition + '_episode'] = case['episode']
            point = indexed.get((case['episode'], case['query_step']))
            if point is None or point['status'] != 'ANSWERED': continue
            logs, ids = point['log_probabilities'], point['ids']
            if logs is None: continue
            contract.require(case['target_id'] in ids and len(logs) == 2 ** len(ids),
                             'invalid contrast forecast geometry')
            shift = len(ids) - ids.index(case['target_id']) - 1
            row['p_one_' + condition] = sum(math.exp(-math.inf if v == 'negative_infinity' else v)
                for world, v in enumerate(logs) if (world >> shift) & 1)
        row['complete'] = all(row['p_one_' + c] is not None for c in ('equal', 'opposite'))
        if row['complete']:
            contract.require(members['equal']['target_id'] == members['opposite']['target_id'] and
                members['equal']['query_step'] == members['opposite']['query_step'], 'contrast query differs')
            row['gap'] = row['p_one_opposite'] - row['p_one_equal']
            row['passed'] = (row['p_one_equal'] <= limits['max_equal_p_one'] + 1e-12 and
                row['p_one_opposite'] >= limits['min_opposite_p_one'] - 1e-12 and
                row['gap'] >= limits['min_gap'] - 1e-12)
        rows.append(row)
    complete, passed = sum(r['complete'] for r in rows), sum(r['passed'] for r in rows)
    return {'planned': limits['pairs'], 'observed_pairs': len(rows),
        'complete_pairs': complete, 'passed_pairs': passed,
        'all_passed': len(rows) == complete == passed == limits['pairs'],
        'min_gap': min(r['gap'] for r in rows) if rows and complete == len(rows) == limits['pairs'] else None,
        'pairs': rows}


def information_scores(point, expected, previous_worlds):
    """Compare the full forecast with the law-conditional joint distribution.

    The historical realized-world unchanged metric is retained. The added known
    unchanged metric requires a unique same bit before AND after the action.
    Missing outputs never acquire a probability score or a correct MAP label.
    """
    contract.require(point['information_key'] == expected['information_key'] and
        point['possible_worlds'] == expected['possible_worlds'], 'information alignment differs')
    n = len(point['ids'])
    target = dict(zip(expected['possible_worlds'], expected['probabilities'], strict=True))
    contract.require(bool(previous_worlds) and all(p > 0 for p in target.values()) and
        abs(sum(target.values()) - 1.) < 1e-12, 'invalid conditional probability inventory')
    known_unchanged = [i for i in range(n) if len({(w >> (n - i - 1)) & 1
        for w in [*previous_worlds, *target]}) == 1]
    result = {'oracle_map_expected_accuracy': max(target.values()),
        'oracle_entropy': -sum(p * math.log(p) for p in target.values()),
        'oracle_kl': None, 'oracle_total_variation': None, 'oracle_brier_regret': None,
        'outside_support_mass': None, 'map_outside_support': None,
        'known_unchanged_bits': len(known_unchanged), 'known_unchanged_errors': None}
    if point['status'] != 'ANSWERED': return result
    logs = [-math.inf if v == 'negative_infinity' else v for v in point['log_probabilities']]
    probabilities = [math.exp(v) for v in logs]
    kl = sum(p * (math.log(p) - logs[w]) for w, p in target.items())
    result.update(oracle_kl=kl,
        oracle_total_variation=.5 * sum(abs(q - target.get(w, 0.)) for w, q in enumerate(probabilities)),
        oracle_brier_regret=sum((q - target.get(w, 0.)) ** 2 for w, q in enumerate(probabilities)),
        outside_support_mass=sum(q for w, q in enumerate(probabilities) if w not in target),
        map_outside_support=point['map_world'] not in target,
        known_unchanged_errors=sum(((point['map_world'] >> (n - i - 1)) & 1) !=
            ((next(iter(target)) >> (n - i - 1)) & 1) for i in known_unchanged))
    return result


def _metrics(points):
    from .acceptance_scoring import _metrics as exact_metrics
    result = exact_metrics(points)
    complete = all(p['status'] == 'ANSWERED' for p in points)
    for key in ('oracle_kl', 'oracle_total_variation', 'oracle_brier_regret',
                'outside_support_mass', 'oracle_map_expected_accuracy'):
        values = [p[key] for p in points]
        result['mean_' + key] = sum(values) / len(values) if points and complete else None
        result['max_' + key] = max(values) if points and complete else None
    result['map_outside_support'] = sum(p['map_outside_support'] is True for p in points)
    result['known_unchanged_errors'] = sum(p['known_unchanged_errors'] or 0 for p in points)
    return result


def analyze(report, assets, config):
    from .acceptance_scoring import _safe
    observed = {c['episode']: c for c in assets['inputs']['episodes']}
    information = {c['episode']: c['forecasts'] for c in assets['information']['episodes']}
    groups, pairs = defaultdict(list), defaultdict(list)
    by_identity = {}
    for p in report['points']:
        if p['nll'] == 'positive_infinity': p['nll'] = math.inf
        case, t = observed[p['episode']], p['step']
        if t == 0:
            previous = [sum(case['observations'][0][name] << (len(p['ids']) - i - 1)
                for i, name in enumerate(p['ids']))]
        else:
            previous = [w for w in information[p['episode']][t - 1]['possible_worlds']
                if all(v is None or v == ((w >> (len(p['ids']) - i - 1)) & 1)
                       for i, name in enumerate(p['ids'])
                       for v in [case['observations'][t][name]])]
        p.update(information_scores(p, information[p['episode']][t], previous))
        groups[p['participant'], p['model_seed']].append(p)
        by_identity[p['participant'], p['model_seed'], p['episode'], t] = p
        if p['answerable']: pairs[p['participant'], p['model_seed'], p['pair_id']].append(p)
    metrics, checks, changes = {}, {}, {}
    for arm in ARMS:
        metrics[arm] = {}
        for seed in config['model_seeds']:
            points = groups[arm, seed]
            strata = {'all': points, 'identifiable': [p for p in points if p['answerable']],
                'ambiguous': [p for p in points if not p['answerable']]}
            row = {k: _metrics(v) for k, v in strata.items()}
            row['by_family'] = {family: {k: _metrics([p for p in v if p['family'] == family])
                for k, v in strata.items()} for family in sorted({p['family'] for p in points})}
            pair_values = [v for (a, s, _), v in pairs.items() if a == arm and s == seed]
            row['identifiable_role_pairs'] = {'planned': len(pair_values),
                'correct': sum(all(p['correct'] for p in v) for v in pair_values)}
            if 'critical_contrast' in config['analysis']:
                row['critical_contrasts'] = correlation_scores(points, assets['cases'],
                    config['analysis']['critical_contrast'])
            for family, values in row['by_family'].items():
                selected = [v for v in pair_values if v[0]['family'] == family]
                values['identifiable_role_pairs'] = {'planned': len(selected),
                    'correct': sum(all(p['correct'] for p in v) for v in selected)}
            metrics[arm][str(seed)] = row
    for seed in config['model_seeds']:
        points = groups['alias', seed]
        changed = {key: [] for key in ('identifiable_repairs', 'identifiable_regressions',
                                      'ambiguous_repairs', 'ambiguous_regressions')}
        for p in points:
            before = by_identity['ordinary', seed, p['episode'], p['step']]
            if before['correct'] != p['correct']:
                key = ('identifiable' if p['answerable'] else 'ambiguous') + (
                    '_repairs' if p['correct'] else '_regressions')
                changed[key].append([p['episode'], p['step']])
        changes[str(seed)] = changed
        row, limits = metrics['alias'][str(seed)], config['analysis']
        families = list(row['by_family'].values())
        checks[str(seed)] = {
            'complete_support': row['all']['support_coverage'] == 1.,
            'identifiable_accuracy_each_family': all(f['identifiable']['accuracy'] is not None and
                f['identifiable']['accuracy'] >= limits['identifiable_accuracy'] for f in families),
            'identifiable_role_pairs_each_family': all(f['identifiable_role_pairs']['planned'] > 0 and
                f['identifiable_role_pairs']['correct'] >=
                limits['identifiable_accuracy'] * f['identifiable_role_pairs']['planned'] for f in families),
            'no_identifiable_regressions': not changed['identifiable_regressions'],
            'supported_MAP_worlds': row['all']['map_outside_support'] == 0,
            'known_unchanged_preserved': row['all']['known_unchanged_errors'] == 0,
            'joint_probability_quality': all(f[stratum]['mean_oracle_kl'] is not None and
                f[stratum]['mean_oracle_kl'] <= limits['mean_oracle_kl']
                for f in families for stratum in ('identifiable', 'ambiguous')),
            'ambiguous_no_collapse': row['ambiguous']['max_oracle_total_variation'] is not None and
                row['ambiguous']['max_oracle_total_variation'] <= limits['max_ambiguous_total_variation']}
        if 'critical_contrast' in limits:
            checks[str(seed)]['every_correlation_contrast'] = row['critical_contrasts']['all_passed']
    complete = not report['metadata']['incomplete_inventory'] and not report['metadata']['failure_records']
    passed = complete and all(all(c.values()) for c in checks.values())
    study = 'JOINT_CORRELATION' if 'critical_contrast' in config['analysis'] else 'MIXED_COMPOSITION'
    decision = 'KEEP_' + study if passed else (
        'STOP_INCOMPLETE_EXECUTION' if not complete else 'REVISE_' + study)
    return _safe({'version': config['version'], 'by_arm': metrics, 'changes': changes,
        'decision': {'decision': decision, 'execution_complete': complete, 'checks': checks,
            'gate_g1': 'NOT_ADMITTED', 'g1_development_readiness': 'PROCEED_TO_G2',
            'g2_scope': ('Equal-marginal observed histories with different joint correlations; full G2 remains open'
                if study == 'JOINT_CORRELATION' else 'Mixed alias/ordinary ordered composition; full G2 remains open'),
            'scientific_admission': False, 'new_training_updates': 0},
        'metadata': report['metadata'], 'protocol_sha256': io._hash(PROTOCOL)})


def collect(data, output):
    from .acceptance_runner import collect as record
    from .acceptance_scoring import evaluate, _safe
    config = protocol()
    for name in ('freeze.json', 'plan.json', 'assets.json.xz'): io._committed(data / name)
    frozen = io._read(data / 'freeze.json')
    contract.require(frozen['sources'] == sources(), 'frozen source bytes differ')
    for name, item in frozen['artifacts'].items():
        contract.require(io._hash(data / name) == item['sha256'], 'frozen artifact differs')
    for arm in ARMS:
        for item in frozen['checkpoints'][arm].values():
            io._committed(FITTED / item['file'])
            contract.require(io._hash(FITTED / item['file']) == item['sha256'], 'frozen checkpoint differs')
    runtime = io._runtime(config)
    assets, plan = io._read(data / 'assets.json.xz'), io._read(data / 'plan.json')
    output.mkdir(parents=True, exist_ok=False)
    artifacts = {'attempt.json': io._write(output / 'attempt.json', {
        'freeze_commit': io._git('rev-parse', 'HEAD'), 'runtime': runtime,
        'freeze_sha256': io._hash(data / 'freeze.json'), 'one_attempt': True})}
    traces = []
    for arm in ARMS:
        for seed in config['model_seeds']:
            item = frozen['checkpoints'][arm][str(seed)]
            trace = record(assets['inputs'], checkpoint=FITTED / item['file'],
                expected_sha256=item['sha256'], participant=arm, model_seed=seed)
            name = f'trace-{arm}-{seed}.json.xz'
            artifacts[name] = io._write(output / name, trace)
            traces.append(trace)
            print(json.dumps({'collected': f'{arm}/{seed}',
                'cpu_seconds': trace['resources']['collection_cpu_seconds']}), flush=True)
    report = evaluate(plan, assets['inputs'], assets['oracle'], traces)
    result = analyze(report, assets, config)
    result['collection_costs'] = {f"{t['participant']}/{t['model_seed']}": t['resources'] for t in traces}
    for name, value in (('all-action.json.xz', _safe(report)), ('summary.json.xz', result),
                        ('decision.json', result['decision'])):
        artifacts[name] = io._write(output / name, value)
    io._write(output / 'manifest.json', {'version': config['version'], 'artifacts': artifacts,
        'artifacts_complete': True, 'execution_complete': result['decision']['execution_complete'],
        'freeze_sha256': io._hash(data / 'freeze.json'), 'plan_sha256': io._hash(data / 'plan.json'),
        'gate_g1': 'NOT_ADMITTED', 'training_updates': 0})
    print(json.dumps(result['decision']), flush=True)


def main():
    global PROTOCOL
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'collect'))
    parser.add_argument('--study', choices=('mixed', 'correlation'), default='mixed')
    parser.add_argument('--data', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.study == 'correlation': PROTOCOL = ROOT / 'joint_correlation_protocol_v1.json'
    if args.stage == 'collect' and args.data is None: parser.error('--data required')
    try:
        prepare(args.output) if args.stage == 'prepare' else collect(args.data, args.output)
    except BaseException as error:
        if args.output.is_dir() and not (args.output / 'failure.json').exists():
            io._write(args.output / 'failure.json', {'stage': args.stage, 'type': type(error).__name__,
                'message': str(error), 'traceback': traceback.format_exc(), 'retry_permitted': False})
        raise


if __name__ == '__main__': main()
