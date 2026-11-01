"""Stdlib-only coordinate-study receipt and saved-forecast audit.

No fitting, model inference or study-scorer imports. Saved tensor algebra and
forecast arithmetic are internal verification, not independent scientific custody.
"""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path

from . import audit_binding_saved as b

h = b.h
ARMS = ('centered', 'coordinates')
PARAMETERS = {'centered': 89, 'coordinates': 88}
BANKS = {'fresh': 'coordinate-v1', 'bilingual_retention': 'bilingual-v1',
         'lexical_retention': 'lexical-v1', 'binding_retention': 'binding-v1',
         'saturation_retention': 'saturation-v1', 'centering_retention': 'centering-v1'}
SHAPES = {'lexical.0.weight': [8, 8], 'lexical.0.bias': [8],
          'lexical.2.weight': [1, 8], 'lexical.2.bias': [1],
          'layout.0.weight': [1, 3], 'layout.0.bias': [1],
          'order.weight': [2, 1, 1], 'order.bias': [2]}


def state_inventory(state, arm):
    expected = {k: v for k, v in SHAPES.items() if arm == 'centered' or k != 'layout.0.bias'}
    b.require(arm in ARMS and set(state) == set(expected), 'tensor inventory differs')
    for name, shape in expected.items():
        b.require(h.tensor_shape(state[name])[0] == shape, 'tensor shape differs: ' + name)
    return h.fingerprint(state)


def verify_initialization(audit, report, label):
    """Verify full legal-mask response equivalence from saved actual tensors."""
    receipt = report['initialization']; states = receipt['states']
    b.require(set(states) == set(ARMS), 'initial arm inventory differs')
    for arm, state in states.items():
        digest, count = state_inventory(state, arm)
        audit.equal([digest, count, report['reports'][arm]['initial_sha256']],
            [receipt['initial_sha256'][arm], PARAMETERS[arm], digest], label + '/' + arm)
    shared = [{k: v for k, v in states[arm].items() if not k.startswith('layout.')} for arm in ARMS]
    # Metric comparisons tolerate roundoff; shared parameters must be exact.
    audit.check(shared[0] == shared[1], label + '/85 exact shared scalars')
    audit.equal(list(h.fingerprint(shared[0])), [receipt['shared_sha256'], 85], label + '/shared fingerprint')
    audit.equal(receipt['unchanged_scalars'], 85, label + '/unchanged scalars')
    audit.equal(receipt['parameters'], PARAMETERS, label + '/parameter inventory')
    audit.equal(receipt['layout_masks'], [[0., 1., 1.], [1., 0., 1.], [1., 1., 0.]], label + '/legal masks')
    centered, coordinates = (states[arm] for arm in ARMS)
    w, bias = centered['layout.0.weight'][0], centered['layout.0.bias'][0]
    responses = [math.fsum(w[j] for j in range(3) if j != i) + bias for i in range(3)]
    actual = coordinates['layout.0.weight'][0]
    for i, (expected, value) in enumerate(zip(responses, actual, strict=True)):
        audit.check(math.isclose(expected, value, rel_tol=0., abs_tol=2e-15), label + '/response/' + str(i))
    for arm, values in zip(ARMS, (responses, actual), strict=True):
        audit.equal(receipt['layout_responses'][arm], values, label + '/response receipt/' + arm)
    audit.check(receipt['initial_sha256']['centered'] != receipt['initial_sha256']['coordinates'],
        label + '/different state encodings')


def archived_path(root, law, seed, bank):
    b.require(bank in BANKS and bank != 'fresh', 'unknown retention bank')
    variants = {'centering_retention': ('centering-v1', 'centered'),
                'saturation_retention': ('saturation-v1', 'unsaturated'),
                'binding_retention': ('binding-v1', 'factor')}
    if bank in variants:
        folder, arm = variants[bank]
        return root / f'results/{folder}/traces/trace-{law}-{seed}-{arm}-fresh.json.xz'
    arm = 'retention' if bank == 'bilingual_retention' else 'grounded'
    return root / f'results/lexical-v1/trace-{law}-{seed}-{arm}.json.xz'


def decision_checks(report, comparison, fit, limit):
    checks = dict(report['checks'])
    checks.update(observed_training_fit=fit['final_observed_train_nll'] <= limit,
        native_exact_retention=not comparison['native']['coordinates']['regressions'],
        archived_exact_retention=not any(v['regressions'] for v in comparison['retention']['coordinates'].values()),
        paired_exact_retention=not comparison['fresh_pair']['regressions'] and
            not any(v['regressions'] for v in comparison['retention_pair'].values()),
        paired_mean_nll=comparison['fresh_pair']['mean_nll_change'] is not None and
            comparison['fresh_pair']['mean_nll_change'] <= 0)
    return checks


def canonical(measured):
    return {(i, t): p for (i, t, view), p in measured.items() if view == 'canonical'}


def planned_counts(inputs, seeds):
    totals = defaultdict(int); native = 0
    for (law, bank), observed in inputs.items():
        count = sum(len(r['utterances']) for r in observed['episodes'])
        if bank == 'fresh':
            native += len(seeds) * count
            count += 2 * len(observed['episodes'])
        totals[bank] += len(seeds) * len(ARMS) * count
    return dict(totals), native


def audit_saved(repo, audit):
    root = repo / 'experiments/predictive_nucleus'; data = root / 'data/coordinate-v1'
    traces = root / 'results/coordinate-v1/traces'; scoring = traces.parent / 'scoring'
    config, freeze, trained, manifest = map(h.read, (root / 'coordinate_protocol_v1.json', data / 'freeze.json',
        root / 'data/coordinate-fit-v1/checkpoints.json.xz', traces / 'manifest.json'))
    seeds = config['model_seeds']; audit.equal(seeds, [7, 11, 23, 37, 53], 'seeds')
    audit.equal(config['arms'], list(ARMS), 'arms')
    audit.equal(config['parameters'], PARAMETERS, 'parameter contract')
    audit.equal([v['version'] for v in (config, freeze, trained)], ['coordinate-v1'] * 3, 'versions')
    previous_config = h.read(root / 'centering_protocol_v1.json')
    for key in ('fit', 'analysis', 'execution', 'train_forecasts'):
        audit.equal(config[key], previous_config[key], 'unchanged/' + key)
    audit.equal(h.sha(root / 'coordinate_protocol_v1.json'),
        (root / 'snapshots/coordinate_protocol_v1.sha256').read_text().split()[0], 'protocol lock')
    audit.equal(freeze['protocol_sha256'], h.sha(root / 'coordinate_protocol_v1.json'), 'protocol binding')
    for name, digest in {**freeze['sources'], **freeze['historical']}.items(): audit.equal(h.sha(root / name), digest, name)
    commitment = h.read(root / 'coordinate_freeze_v1.json')
    expected_data = {'train-inputs.json.xz', 'audit.json', *(f'{law}-{kind}.json.xz'
        for law in b.LAWS for kind in ('inputs', 'oracle'))}
    audit.equal(set(freeze['artifacts']), expected_data, 'data inventory')
    audit.equal(set(commitment), expected_data | {'freeze.json'}, 'data commitment inventory')
    for name, digest in commitment.items(): audit.equal(h.sha(data / name), digest, 'data/' + name)
    for name, item in freeze['artifacts'].items():
        audit.equal([h.sha(data / name), (data / name).stat().st_size], [item['sha256'], item['bytes']], 'artifact/' + name)
    audit.equal([manifest['complete'], manifest['oracle_opened'], trained['complete']], [True, False, True], 'completion')
    audit.equal(manifest['freeze_sha256'], h.sha(data / 'freeze.json'), 'data binding')
    audit.equal(trained['freeze_sha256'], manifest['freeze_sha256'], 'fit data')
    audit.equal(manifest['checkpoint_sha256'], h.sha(root / 'data/coordinate-fit-v1/checkpoints.json.xz'), 'fit bytes')
    audit.equal(set(trained['checkpoints']), {f'{arm}/{seed}' for arm in ARMS for seed in seeds}, 'fit inventory')
    audit.equal(set(trained['reports']), {str(seed) for seed in seeds}, 'fit report inventory')
    training = h.read(data / 'train-inputs.json.xz')
    audit.equal(h.sha(data / 'train-inputs.json.xz'), h.sha(root / 'data/saturation-v1/train-inputs.json.xz'), 'identical training bytes')
    audit.equal(sum(len(r['utterances']) for r in training['episodes']), config['train_forecasts'], 'training events')
    archive_file = 'data/centering-fit-v1/checkpoints.json.xz'
    audit.equal(freeze['historical'][archive_file], h.sha(root / archive_file), 'archived control binding')
    archived = h.read(root / archive_file); final_matches, reproduced = {}, {}
    for seed in seeds:
        report = trained['reports'][str(seed)]
        audit.equal(set(report['reports']), set(ARMS), 'paired fit reports')
        verify_initialization(audit, report, 'initial/' + str(seed))
        control = report['reports']['centered']; previous = archived['reports'][str(seed)]['reports']['centered']
        audit.equal(control['initial_sha256'], previous['initial_sha256'], 'archived centered initial/' + str(seed))
        final_matches[str(seed)] = control['final_sha256'] == previous['final_sha256']
        audit.check(final_matches[str(seed)], 'archived centered final/' + str(seed))
        fields = ('parameters', 'initial_sha256', 'final_sha256', 'updates',
                  'observed_events_per_update', 'curve', 'final_observed_train_nll')
        audit.check(all(control[k] == previous[k] for k in fields), 'archived centered training/' + str(seed))
        key = 'centered/' + str(seed)
        audit.check(trained['checkpoints'][key] == archived['checkpoints'][key], 'archived centered actual state/' + str(seed))
        audit.check(report['initialization']['states']['centered'] ==
            archived['reports'][str(seed)]['initialization']['states']['centered'], 'archived centered actual initial/' + str(seed))
        reproduced[str(seed)] = {'initial_sha256': control['initial_sha256'],
                                'final_sha256': control['final_sha256'], 'matched': True}
        audit.equal(report['world_state_sha256'], freeze['checkpoints']['nand'][str(seed)]['state_sha256'], 'frozen training world')
    audit.equal(trained['control_reproduction'],
        {'archive_sha256': h.sha(root / archive_file), 'matches': reproduced}, 'control reproduction receipt')
    audit.equal(set(freeze['checkpoints']), set(b.LAWS), 'native law inventory')
    for law in b.LAWS:
        audit.equal(set(freeze['checkpoints'][law]), {str(seed) for seed in seeds}, 'native seed inventory/' + law)
        for seed in seeds:
            item = freeze['checkpoints'][law][str(seed)]
            path = root / 'data/multisource-law-fit-v1' / item['file']; world = h.read(path)
            audit.equal([h.sha(path), *h.fingerprint(world['state']), world['state_sha256']],
                [item['sha256'], item['state_sha256'], 562, item['state_sha256']], 'native checkpoint/' + law + '/' + str(seed))
    for key, checkpoint in trained['checkpoints'].items():
        arm, seed = key.split('/'); fit = trained['reports'][seed]['reports'][arm]
        audit.equal([checkpoint['arm'], checkpoint['seed'], fit['parameters']], [arm, int(seed), PARAMETERS[arm]], 'fit identity/' + key)
        audit.equal([*state_inventory(checkpoint['state'], arm), checkpoint['state_sha256']],
            [fit['final_sha256'], PARAMETERS[arm], fit['final_sha256']], 'state/' + key)
        audit.equal([fit['updates'], fit['observed_events_per_update']], [config['fit']['updates'], config['train_forecasts']], 'exposure/' + key)
        audit.equal(trained['reports'][seed]['training_input_sha256'], h.canonical(training), 'observed history')
    for runtime in (trained['runtime'], manifest['runtime']):
        audit.equal({k: runtime[k] for k in config['execution']['runtime']}, config['execution']['runtime'], 'runtime')
    inputs = {(law, bank): h.read(root / 'data' / folder / f'{law}-inputs.json.xz') for law in b.LAWS for bank, folder in BANKS.items()}
    for law in b.LAWS:
        audit.equal(sum(len(r['utterances']) for r in inputs[law, 'fresh']['episodes']),
            config['challenge_forecasts_per_law'], 'fresh denominator/' + law)
    expected = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for law in b.LAWS for seed in seeds for arm in ARMS for bank in BANKS}
    b.require(set(manifest['artifacts']) == expected, 'trace file inventory differs'); totals = defaultdict(int)
    audit.equal({p.name for p in traces.glob('trace-*.json.xz')}, expected, 'trace directory inventory')
    for name, item in manifest['artifacts'].items():
        audit.equal([h.sha(traces / name), (traces / name).stat().st_size], [item['sha256'], item['bytes']], 'receipt/' + name)
        trace = h.read(traces / name); law, seed, arm, bank = (trace[k] for k in ('law', 'seed', 'arm', 'bank'))
        b.require(type(seed) is int and name == f'trace-{law}-{seed}-{arm}-{bank}.json.xz', 'trace substitution')
        for field in ('freeze_sha256', 'checkpoint_sha256', 'weights_publication'): audit.equal(trace[field], manifest[field], field)
        audit.equal(trace['state_sha256'], trained['checkpoints'][f'{arm}/{seed}']['state_sha256'], 'trace state')
        audit.equal(trace['input_sha256'], h.canonical(inputs[law, bank]), 'trace input')
        totals[bank] += len(b.rows(trace['points'], {r['id']: r for r in inputs[law, bank]['episodes']}, bank == 'fresh'))
    b.require(audit.discrepancy_count == 0, 'audit failed before targets')
    saved, decision = h.read(scoring / 'summary.json.xz'), h.read(scoring / 'decision.json')
    expected_keys = {f'{law}/{seed}' for law in b.LAWS for seed in seeds}
    for section in ('comparisons', 'native_references'):
        audit.equal(set(saved[section]), expected_keys, section + '/inventory')
    audit.equal(set(saved['reports']), {key + '/' + arm for key in expected_keys for arm in ARMS}, 'summary report inventory')
    audit.check(not any((folder / 'failure.json').exists() for folder in
        (root / 'data/coordinate-fit-v1', traces, scoring)), 'no execution failure')
    audit.equal(saved['trace_manifest_sha256'], h.sha(traces / 'manifest.json'), 'summary binding')
    audit.equal(saved['decision'], decision, 'decision copy'); checks, details = {}, {}
    for law in b.LAWS:
        inventories = {bank: b.gold_inventory(audit, inputs[law, bank], h.read(root / 'data' / folder / f'{law}-oracle.json.xz')) for bank, folder in BANKS.items()}
        records, gold, pairs = inventories['fresh']
        for seed in seeds:
            key = f'{law}/{seed}'; print('Audit ' + key, flush=True)
            native = canonical(b.measure(audit, b.rows(saved['native_references'][key], records, native=True), records, gold))
            current, reports, retained = {}, {}, {arm: {} for arm in ARMS}
            for bank in BANKS:
                rec, target, pair = inventories[bank]
                if bank != 'fresh':
                    path = archived_path(root, law, seed, bank)
                    archive = h.read(path); audit.equal(archive['input_sha256'], h.canonical(inputs[law, bank]), 'archive input')
                    previous = canonical(b.measure(audit, b.rows([r for r in archive['points'] if r.get('view', 'canonical') == 'canonical'], rec), rec, target))
                for arm in ARMS:
                    name = f'trace-{law}-{seed}-{arm}-{bank}.json.xz'
                    b.require(h.sha(traces / name) == manifest['artifacts'][name]['sha256'], 'trace changed during audit')
                    measured = b.measure(audit, b.rows(h.read(traces / name)['points'], rec, bank == 'fresh'), rec, target)
                    current[arm, bank] = canonical(measured)
                    if bank == 'fresh':
                        reports[arm], _ = b.fresh_summary(measured, rec, target, pair, config['analysis'])
                        audit.equal(saved['reports'][key + '/' + arm], reports[arm], key + '/' + arm)
                    else: retained[arm][bank] = {'all': h.metrics(list(current[arm, bank].values())), **b.delta(current[arm, bank], previous)}
            comparison = {'fresh_pair': b.delta(current['coordinates', 'fresh'], current['centered', 'fresh']),
                'native': {arm: b.delta(current[arm, 'fresh'], native) for arm in ARMS}, 'retention': retained,
                'retention_pair': {bank: b.delta(current['coordinates', bank], current['centered', bank]) for bank in BANKS if bank != 'fresh'}}
            audit.equal(saved['comparisons'][key], comparison, key + '/comparisons')
            checks[key] = decision_checks(reports['coordinates'], comparison, trained['reports'][str(seed)]['reports']['coordinates'], config['analysis']['max_mean_nll'])
            details[key] = {arm: {'all': reports[arm]['all'], 'held': reports[arm]['held'],
                'archive_regressions': {bank: len(v['regressions']) for bank, v in retained[arm].items()}} for arm in ARMS}
    planned, native_count = planned_counts(inputs, seeds)
    audit.equal(dict(totals), planned, 'forecast denominator')
    audit.equal(sum(len(v) for v in saved['native_references'].values()), native_count, 'native reference denominator')
    outcome = 'KEEP_LAYOUT_COORDINATES' if all(all(v.values()) for v in checks.values()) else 'REVISE_COORDINATE_HYPOTHESIS'
    audit.equal(decision['checks'], checks, 'all decision checks'); audit.equal(decision['decision'], outcome, 'decision')
    audit.equal([decision['execution_complete'], decision['scientific_admission']], [True, False], 'decision scope')
    return {'version': 'coordinate-saved-audit-v1', 'decision': outcome, 'audit_passed': audit.discrepancy_count == 0,
        'check_count': audit.checks, 'discrepancy_count': audit.discrepancy_count, 'discrepancies': audit.discrepancies,
        'forecast_count': sum(totals.values()), 'native_reference_count': native_count,
        'bound_sources': len(freeze['sources']), 'bound_historical_files': len(freeze['historical']),
        'verified_checkpoints': len(trained['checkpoints']), 'verified_initial_states': len(seeds) * len(ARMS),
        'centered_archive_final_sha256_equal_by_seed': final_matches,
        'source_publication': trained['source_publication'], 'weights_publication': manifest['weights_publication'],
        'auditor_sha256': h.sha(__file__), 'helper_sha256': h.sha(b.__file__), 'metric_helper_sha256': h.sha(h.__file__),
        'summary_sha256': h.sha(scoring / 'summary.json.xz'), 'details': details,
        'initialization_scope': 'Saved actual tensors, shared 85 scalars and equivalent legal-mask responses; archived centered initial/final hashes verified. No RNG replay or independent custody.',
        'new_fits': 0, 'new_collections': 0, 'model_execution': False, 'scientific_admission': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv); report = audit_saved(args.repo, h.Audit())
    text = json.dumps(h.safe(report), sort_keys=True, indent=2, allow_nan=False) + '\n'
    with args.output.open('x') as stream: stream.write(text)
    print(json.dumps({k: report[k] for k in ('decision', 'audit_passed', 'check_count', 'discrepancy_count')}), flush=True)
    return int(not report['audit_passed'])


if __name__ == '__main__': raise SystemExit(main())
