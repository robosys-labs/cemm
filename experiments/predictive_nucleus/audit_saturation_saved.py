"""Stdlib-only paired-study audit; reuses independent saved-record metric helpers.

No fitting, model inference, original scoring, or closed-study replay. This is
internal arithmetic verification, not independent scientific custody.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path

from . import audit_binding_saved as b

h = b.h
ARMS = ('factor', 'unsaturated')
BANKS = {'fresh': 'saturation-v1', 'bilingual_retention': 'bilingual-v1',
         'lexical_retention': 'lexical-v1', 'binding_retention': 'binding-v1'}


def decision_checks(report, comparison, fit, limit):
    checks = dict(report['checks'])
    checks.update(observed_training_fit=fit['final_observed_train_nll'] <= limit,
        native_exact_retention=not comparison['native']['unsaturated']['regressions'],
        archived_exact_retention=not any(v['regressions'] for v in comparison['retention']['unsaturated'].values()),
        paired_exact_retention=not comparison['fresh_pair']['regressions'] and
            not any(v['regressions'] for v in comparison['retention_pair'].values()),
        paired_mean_nll=comparison['fresh_pair']['mean_nll_change'] is not None and
            comparison['fresh_pair']['mean_nll_change'] <= 0)
    return checks


def canonical(measured):
    return {(i, t): p for (i, t, view), p in measured.items() if view == 'canonical'}


def audit_saved(repo, audit):
    root = repo / 'experiments/predictive_nucleus'; data = root / 'data/saturation-v1'
    traces = root / 'results/saturation-v1/traces'; scoring = traces.parent / 'scoring'
    config, freeze, trained, manifest = map(h.read, (root / 'saturation_protocol_v1.json', data / 'freeze.json',
        root / 'data/saturation-fit-v1/checkpoints.json.xz', traces / 'manifest.json'))
    seeds = config['model_seeds']
    audit.equal(h.sha(root / 'saturation_protocol_v1.json'),
        (root / 'snapshots/saturation_protocol_v1.sha256').read_text().split()[0], 'protocol lock')
    audit.equal(freeze['protocol_sha256'], h.sha(root / 'saturation_protocol_v1.json'), 'protocol binding')
    for name, digest in {**freeze['sources'], **freeze['historical']}.items(): audit.equal(h.sha(root / name), digest, name)
    for name, digest in h.read(root / 'saturation_freeze_v1.json').items(): audit.equal(h.sha(data / name), digest, 'data/' + name)
    audit.equal([manifest['complete'], manifest['oracle_opened'], trained['complete']], [True, False, True], 'completion')
    audit.equal(manifest['freeze_sha256'], h.sha(data / 'freeze.json'), 'data binding')
    audit.equal(trained['freeze_sha256'], manifest['freeze_sha256'], 'fit data')
    audit.equal(manifest['checkpoint_sha256'], h.sha(root / 'data/saturation-fit-v1/checkpoints.json.xz'), 'fit bytes')
    audit.equal(set(trained['checkpoints']), {f'{arm}/{seed}' for arm in ARMS for seed in seeds}, 'fit inventory')
    training = h.read(data / 'train-inputs.json.xz')
    audit.equal(sum(len(r['utterances']) for r in training['episodes']), config['train_forecasts'], 'training events')
    for key, checkpoint in trained['checkpoints'].items():
        arm, seed = key.split('/'); fit = trained['reports'][seed]['reports'][arm]
        audit.equal([*h.fingerprint(checkpoint['state']), checkpoint['state_sha256']], [fit['final_sha256'], 89, fit['final_sha256']], 'state/' + key)
        audit.equal([fit['updates'], fit['observed_events_per_update']], [config['fit']['updates'], config['train_forecasts']], 'exposure/' + key)
        audit.equal(fit['initial_sha256'], trained['reports'][seed]['reports']['factor']['initial_sha256'], 'paired initialization')
        audit.equal(trained['reports'][seed]['training_input_sha256'], h.canonical(training), 'observed history')
    for runtime in (trained['runtime'], manifest['runtime']):
        audit.equal({k: runtime[k] for k in config['execution']['runtime']}, config['execution']['runtime'], 'runtime')
    inputs = {(law, bank): h.read(root / 'data' / folder / f'{law}-inputs.json.xz') for law in b.LAWS for bank, folder in BANKS.items()}
    expected = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for law in b.LAWS for seed in seeds for arm in ARMS for bank in BANKS}
    b.require(set(manifest['artifacts']) == expected, 'trace file inventory differs'); totals = defaultdict(int)
    for name, item in manifest['artifacts'].items():
        audit.equal([h.sha(traces / name), (traces / name).stat().st_size], [item['sha256'], item['bytes']], 'receipt/' + name)
        trace = h.read(traces / name); law, seed, arm, bank = (trace[k] for k in ('law', 'seed', 'arm', 'bank'))
        b.require(name == f'trace-{law}-{seed}-{arm}-{bank}.json.xz', 'trace substitution')
        for field in ('freeze_sha256', 'checkpoint_sha256', 'weights_publication'): audit.equal(trace[field], manifest[field], field)
        audit.equal(trace['state_sha256'], trained['checkpoints'][f'{arm}/{seed}']['state_sha256'], 'trace state')
        audit.equal(trace['input_sha256'], h.canonical(inputs[law, bank]), 'trace input')
        totals[bank] += len(b.rows(trace['points'], {r['id']: r for r in inputs[law, bank]['episodes']}, bank == 'fresh'))
    b.require(audit.discrepancy_count == 0, 'audit failed before targets')
    saved, decision = h.read(scoring / 'summary.json.xz'), h.read(scoring / 'decision.json')
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
                    oldarm = 'retention' if bank == 'bilingual_retention' else 'grounded'
                    path = (root / f'results/binding-v1/traces/trace-{law}-{seed}-factor-fresh.json.xz' if bank == 'binding_retention'
                            else root / f'results/lexical-v1/trace-{law}-{seed}-{oldarm}.json.xz')
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
            comparison = {'fresh_pair': b.delta(current['unsaturated', 'fresh'], current['factor', 'fresh']),
                'native': {arm: b.delta(current[arm, 'fresh'], native) for arm in ARMS}, 'retention': retained,
                'retention_pair': {bank: b.delta(current['unsaturated', bank], current['factor', bank]) for bank in BANKS if bank != 'fresh'}}
            audit.equal(saved['comparisons'][key], comparison, key + '/comparisons')
            checks[key] = decision_checks(reports['unsaturated'], comparison, trained['reports'][str(seed)]['reports']['unsaturated'], config['analysis']['max_mean_nll'])
            details[key] = {arm: {'all': reports[arm]['all'], 'held': reports[arm]['held'],
                'archive_regressions': {bank: len(v['regressions']) for bank, v in retained[arm].items()}} for arm in ARMS}
    audit.equal(dict(totals), {'fresh': 49920, 'bilingual_retention': 41600, 'lexical_retention': 83200, 'binding_retention': 34560}, 'forecast denominator')
    outcome = 'KEEP_UNSATURATED_BINDING' if all(all(v.values()) for v in checks.values()) else 'REVISE_SATURATION_HYPOTHESIS'
    audit.equal(decision['checks'], checks, 'all decision checks'); audit.equal(decision['decision'], outcome, 'decision')
    audit.equal([decision['execution_complete'], decision['scientific_admission']], [True, False], 'decision scope')
    return {'version': 'saturation-saved-audit-v1', 'decision': outcome, 'audit_passed': audit.discrepancy_count == 0,
        'check_count': audit.checks, 'discrepancy_count': audit.discrepancy_count, 'discrepancies': audit.discrepancies,
        'forecast_count': sum(totals.values()), 'native_reference_count': sum(len(v) for v in saved['native_references'].values()),
        'bound_sources': len(freeze['sources']), 'bound_historical_files': len(freeze['historical']), 'verified_checkpoints': 10,
        'source_publication': trained['source_publication'], 'weights_publication': manifest['weights_publication'],
        'auditor_sha256': h.sha(__file__), 'helper_sha256': h.sha(b.__file__), 'metric_helper_sha256': h.sha(h.__file__),
        'summary_sha256': h.sha(scoring / 'summary.json.xz'), 'details': details,
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
