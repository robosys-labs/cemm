"""Paired saved-forecast analysis; targets open only after complete inventory checks."""
import json
import math

from . import acceptance_contract as c, continuation_run as io, bilingual_scoring as metrics
from . import binding_scoring as old, saturation_run as run
from .bilingual_contract import validate_inputs


def validated_traces(data, fitted, traces, config):
    manifest = io._read(traces / 'manifest.json'); saved = io._read(fitted / 'checkpoints.json.xz')
    run.load_models(fitted, config, data)  # Validate tensors/provenance without forecasting.
    c.require(manifest['complete'] is True and manifest['oracle_opened'] is False and
        manifest['freeze_sha256'] == io._hash(data / 'freeze.json') and
        manifest['checkpoint_sha256'] == io._hash(fitted / 'checkpoints.json.xz'), 'trace manifest differs')
    run.old.publication(manifest['weights_publication'])
    expected = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for law in ('nand', 'nor') for seed in config['model_seeds']
                for arm in run.ARMS for bank in ('fresh', *run.BANKS)}
    c.require(set(manifest['artifacts']) == expected, 'trace file inventory differs')
    inputs, indexed = {}, {}
    for law in ('nand', 'nor'):
        for bank in ('fresh', *run.BANKS):
            path = data if bank == 'fresh' else io.ROOT / 'data' / run.BANKS[bank]
            inputs[law, bank] = validate_inputs(io._read(path / f'{law}-inputs.json.xz'))
    for name, item in manifest['artifacts'].items():
        c.require(io._hash(traces / name) == item['sha256'], 'trace bytes differ')
        trace = io._read(traces / name); law, seed, arm, bank = (trace[k] for k in ('law', 'seed', 'arm', 'bank'))
        c.require(type(seed) is int and (law, bank) in inputs and arm in run.ARMS and seed in config['model_seeds'] and
            name == f'trace-{law}-{seed}-{arm}-{bank}.json.xz' and trace['input_sha256'] == c.digest(inputs[law, bank]) and
            all(trace[k] == manifest[k] for k in ('freeze_sha256', 'checkpoint_sha256', 'weights_publication')) and
            trace['state_sha256'] == saved['checkpoints'][f'{arm}/{seed}']['state_sha256'], 'trace identity differs')
        indexed[law, seed, arm, bank] = old.index_trace(trace, inputs[law, bank], bank == 'fresh')
    c.require(len(indexed) == len(expected), 'duplicate trace identity')
    return manifest, saved, inputs, indexed


def archived_points(law, seed, bank, records, gold):
    if bank == 'binding_retention':
        path = io.ROOT / 'results/binding-v1/traces' / f'trace-{law}-{seed}-factor-fresh.json.xz'
    else:
        arm = 'retention' if bank == 'bilingual_retention' else 'grounded'
        path = run.old.OLD / f'trace-{law}-{seed}-{arm}.json.xz'
    trace = io._read(path); points = {}
    expected = {(r['id'], t) for r in records.values() for t in range(len(r['utterances']))}
    for row in trace['points']:
        if row.get('view', 'canonical') != 'canonical': continue
        row = dict(row); key = row['id'], row['step']
        c.require(type(row['step']) is int and key in expected and key not in points, 'archived inventory differs')
        row['logp'] = metrics._logs(row['logp'], 2 ** len(records[row['id']]['entities']))
        row['order_logp'] = metrics._logs(row['order_logp'], 2)
        points[key] = metrics._point(row, records[row['id']], gold[row['id']])
    c.require(points.keys() == expected, 'incomplete archived forecasts')
    return points


def decide(reports, comparisons, saved, config):
    checks = {}
    for law in ('nand', 'nor'):
        for seed in config['model_seeds']:
            key = f'{law}/{seed}'; pair = comparisons[key]
            check = dict(reports[key + '/unsaturated']['checks'])
            check['observed_training_fit'] = saved['reports'][str(seed)]['reports']['unsaturated']['final_observed_train_nll'] <= config['analysis']['max_mean_nll']
            check['native_exact_retention'] = not pair['native']['unsaturated']['regressions']
            check['archived_exact_retention'] = not any(v['regressions'] for v in pair['retention']['unsaturated'].values())
            check['paired_exact_retention'] = not pair['fresh_pair']['regressions'] and not any(v['regressions'] for v in pair['retention_pair'].values())
            change = pair['fresh_pair']['mean_nll_change']
            check['paired_mean_nll'] = change is not None and change <= 0
            checks[key] = check
    kept = all(all(v.values()) for v in checks.values())
    return {'decision': 'KEEP_UNSATURATED_BINDING' if kept else 'REVISE_SATURATION_HYPOTHESIS',
        'execution_complete': True, 'checks': checks, 'scientific_admission': False,
        'scope': 'Paired terminal-activation ablation on fresh word-layout cells; no general parser or independent custody claim.'}


def score(data, fitted, traces, output):
    config, freeze = run.verify(data)
    manifest, saved, inputs, indexed = validated_traces(data, fitted, traces, config)
    # No evaluator target has been decoded above this point.
    output.mkdir(parents=True, exist_ok=False); reports, comparisons, references = {}, {}, {}
    for law in ('nand', 'nor'):
        records, gold, pairs = old.oracle(inputs[law, 'fresh'], io._read(data / f'{law}-oracle.json.xz'), law)
        for seed in config['model_seeds']:
            key = f'{law}/{seed}'; scored = {}; retained = {arm: {} for arm in run.ARMS}; paired_retention = {}
            for arm in run.ARMS:
                reports[key + '/' + arm], scored[arm] = old.summary(indexed[law, seed, arm, 'fresh'], records, gold, pairs, config['analysis'])
            native = metrics._native(inputs[law, 'fresh'], gold, freeze['checkpoints'], law, seed)
            references[key] = list(native.values())
            native_points = {(i, t): metrics._point(row, records[i], gold[i]) for (i, t), row in native.items()}
            for bank, folder in run.BANKS.items():
                inventory = old.oracle if bank == 'binding_retention' else metrics._inventory
                oldrecords, oldgold, _ = inventory(inputs[law, bank], io._read(io.ROOT / 'data' / folder / f'{law}-oracle.json.xz'), law)
                archive = archived_points(law, seed, bank, oldrecords, oldgold); current = {}
                for arm in run.ARMS:
                    current[arm] = old.points(indexed[law, seed, arm, bank], oldrecords, oldgold)
                    retained[arm][bank] = {'all': metrics._stats(list(current[arm].values())), **old.deltas(current[arm], archive)}
                paired_retention[bank] = old.deltas(current['unsaturated'], current['factor'])
            comparisons[key] = {'fresh_pair': old.deltas(scored['unsaturated'], scored['factor']),
                'native': {arm: old.deltas(points, native_points) for arm, points in scored.items()},
                'retention': dict(retained), 'retention_pair': paired_retention}
    decision = decide(reports, comparisons, saved, config)
    io._write(output / 'summary.json.xz', metrics._safe({'decision': decision, 'reports': reports,
        'comparisons': comparisons, 'native_references': references, 'trace_manifest_sha256': io._hash(traces / 'manifest.json')}))
    io._write(output / 'decision.json', decision)
    print(json.dumps(decision, allow_nan=False), flush=True)
