"""Audit closed binding-v1 receipts and recover arithmetic, never fit or predict.

The original score process failed after writing its decision. Its failure and
all frozen files stay intact. This stdlib-only successor reuses the independent
bilingual auditor, not the study scorer, and distinguishes artifact completeness
from process success. It does not establish independent scientific custody.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import sys

from . import audit_bilingual_saved as h

ARMS = ('gru', 'factor', 'additive')
LAWS = ('nand', 'nor')
BANKS = {'fresh': 'binding-v1', 'bilingual_retention': 'bilingual-v1', 'lexical_retention': 'lexical-v1'}
PARAMETERS = {'gru': 474, 'factor': 89, 'additive': 91}


def require(condition, message):
    if not condition: raise ValueError(message)


def logs(values, count):
    require(type(values) is list and len(values) == count, 'log geometry differs')
    numbers = [h.number(v) for v in values]
    require(all(type(v) in (int, float) and not math.isnan(v) and v != math.inf for v in numbers), 'invalid log value')
    top = max(numbers)
    require(math.isfinite(top) and abs(top + math.log(math.fsum(math.exp(v - top) for v in numbers))) <= 1e-10,
            'log probabilities not normalized')


def rows(value, records, fresh=False, native=False):
    expected = {(i, t, 'canonical') for i, r in records.items() for t in range(len(r['utterances']))}
    if fresh:
        expected |= {(i, len(r['utterances']) - 1, view) for i, r in records.items() for view in ('masked', 'swapped')}
    indexed = {}
    for row in value:
        require(set(row) == {'id', 'step', 'logp', 'order_logp'} | ({'view'} if fresh or 'view' in row else set()),
                'forecast fields differ')
        key = row['id'], row['step'], row.get('view', 'canonical')
        require(type(row['step']) is int and key in expected and key not in indexed, 'duplicate/unplanned point')
        logs(row['logp'], 2 ** len(records[row['id']]['entities']))
        if native: require(row['order_logp'] is None, 'native reference contains language order')
        else: logs(row['order_logp'], 2)
        indexed[key] = row
    require(set(indexed) == expected, 'missing planned points')
    return indexed


def delta(current, old):
    require(current.keys() == old.keys(), 'comparison inventory differs')
    output = {name: [] for name in ('repairs', 'regressions', 'nll_worse', 'nll_better', 'nll_undefined_difference')}
    for key, new in current.items():
        prior = old[key]; change = h.difference(new['nll'], prior['nll'])
        if new['correct'] and not prior['correct']: output['repairs'].append(list(key))
        if prior['correct'] and not new['correct']: output['regressions'].append(list(key))
        if change is None: output['nll_undefined_difference'].append(list(key))
        elif change != 0: output['nll_worse' if change > 0 else 'nll_better'].append([*key, change])
    output.update(planned=len(current), mean_nll_change=h.difference(
        math.fsum(p['nll'] for p in current.values()) / len(current), math.fsum(p['nll'] for p in old.values()) / len(old)))
    return output


def gold_inventory(audit, inputs, target):
    records, gold = ({r['id']: r for r in value['episodes']} for value in (inputs, target))
    require(len(records) == len(inputs['episodes']) and len(gold) == len(target['episodes']) and records.keys() == gold.keys(), 'gold inventory differs')
    audit.equal(target['input_sha256'], h.canonical(inputs), 'gold input binding')
    pairs = {kind: defaultdict(list) for kind in ('lexical', 'role')}
    for identity, meta in gold.items():
        record = records[identity]; before = record['anchor']
        for event in record['context']:
            before = h.transition(before, event['action'], meta['mode'], meta['law'])
            audit.equal(before, event['reading'], 'context physics')
        count = len(record['utterances'])
        require(all(len(meta[k]) == count for k in ('actions', 'action_orders', 'truth', 'opposite_truth')), 'gold geometry differs')
        for t, event in enumerate(record['utterances']):
            tokens = event['text'].split(); mentions = [record['entities'].index(w) for w in tokens if w in record['entities']]
            order, action = meta['action_orders'][t], meta['actions'][t]
            require(type(order) is int and order in (0, 1), 'invalid gold order')
            audit.equal(action, [0, mentions[order], mentions[1 - order], -1], 'order action')
            audit.equal(meta['opposite_truth'][t], h.transition(before, [0, action[2], action[1], -1], meta['mode'], meta['law']), 'foil physics')
            before = h.transition(before, action, meta['mode'], meta['law'])
            audit.equal(meta['truth'][t], before, 'target physics'); audit.equal(event['reading'], before, 'reading physics')
        if 'cells' in meta:
            require(len(meta['cells']) == count, 'cell count differs')
            for kind in pairs: pairs[kind][meta[kind + '_pair_id']].append(identity)
    for kind, groups in pairs.items():
        for members in groups.values():
            require(len(members) == 2, 'pair incomplete')
            a, b = members
            for field in ('entities', 'anchor', 'context'): audit.equal(records[a][field], records[b][field], 'paired ' + field)
            if kind == 'lexical':
                audit.equal(records[a]['utterances'][:-1], records[b]['utterances'][:-1], 'lexical prefix')
                audit.equal(gold[a]['actions'][-1], [0, gold[b]['actions'][-1][2], gold[b]['actions'][-1][1], -1], 'lexical reversal')
            else:
                audit.equal(gold[a]['actions'], [[0, act[2], act[1], -1] for act in gold[b]['actions']], 'role reversal')
    return records, gold, pairs


def measure(audit, indexed, records, gold):
    return {key: h.measure(audit, row, records[key[0]], gold[key[0]], 'point') for key, row in indexed.items()}


def fresh_summary(measured, records, gold, pairs, limits):
    points = {(i, t): p for (i, t, view), p in measured.items() if view == 'canonical'}
    grouped, held = defaultdict(list), []
    for (i, t), p in points.items():
        cell = gold[i]['cells'][t]; grouped['/'.join((gold[i]['family'], cell['word'], cell['layout']))].append(p)
        if cell['held']: held.append(p)
    cells = {key: h.metrics(value) for key, value in grouped.items()}
    conjunctions = {kind: {'planned': len(groups), 'correct': sum(all(points[i, t]['correct'] for i in members
        for t in (range(len(records[i]['utterances'])) if kind == 'role' else (len(records[i]['utterances']) - 1,)))
        for members in groups.values())} for kind, groups in pairs.items()}
    tv = lambda a, b: math.fsum(abs(x - y) for x, y in zip(a['probabilities'], b['probabilities'], strict=True)) / 2
    contrasts = []
    for identity, (a, b) in pairs['lexical'].items():
        t = len(records[a]['utterances']) - 1; left, right = (measured[i, t, 'canonical'] for i in (a, b))
        index = h.index(gold[a]['truth'][t])
        contrasts.append({'pair_id': identity, 'critical': gold[a]['truth'][t] != gold[b]['truth'][t],
            'gap': abs(left['probabilities'][index] - right['probabilities'][index]),
            'masked_tv': tv(measured[a, t, 'masked'], measured[b, t, 'masked']),
            'swap_tv': max(tv(measured[a, t, 'swapped'], right), tv(measured[b, t, 'swapped'], left)),
            'masked_both_correct': measured[a, t, 'masked']['correct'] and measured[b, t, 'masked']['correct']})
    critical = [p for p in contrasts if p['critical']]
    checks = {'cell_world_accuracy': all(s['accuracy'] >= limits['min_accuracy'] for s in cells.values()),
        'cell_order_accuracy': all(s['order_correct'] >= limits['min_accuracy'] * s['order_planned'] for s in cells.values()),
        'cell_nll': all(s['mean_nll'] <= limits['max_mean_nll'] for s in cells.values()),
        'critical_probabilities': all(not s['critical_planned'] or (s['min_critical_true_probability'] >= limits['min_true_probability']
            and s['max_wrong_order_probability'] <= limits['max_foil_probability']) for s in cells.values()),
        'lexical_and_role_pairs': all(s['correct'] >= limits['min_accuracy'] * s['planned'] for s in conjunctions.values()),
        'lexical_gap': bool(critical) and min(p['gap'] for p in critical) >= limits['min_gap'],
        'masked_invariance': max(p['masked_tv'] for p in contrasts) <= limits['max_control_tv'] and not any(p['masked_both_correct'] for p in critical),
        'swap_equivariance': max(p['swap_tv'] for p in contrasts) <= limits['max_control_tv']}
    return {'all': h.metrics(list(points.values())), 'held': h.metrics(held), 'by_cell': cells,
        'pairs': conjunctions, 'contrasts': contrasts, 'checks': checks}, points


def factor_geometry(state, words):
    """Inspect saved bottlenecks algebraically, without assigning semantic signs.

    This is a diagnostic, not a new forecast or proof of a saturation cause.
    Derivatives below are local output-Tanh derivatives, not total gradients.
    """
    affine = lambda x, w, b: [bias + math.fsum(a * v for a, v in zip(row, x, strict=True))
                              for row, bias in zip(w, b, strict=True)]
    def features(word):
        pieces = list(word) + [word[i:i + 2] for i in range(len(word) - 1)]
        values = [0.] * 8
        for piece in pieces:
            code = hashlib.sha256(piece.encode()).digest()
            values[code[0] % 8] += 1. if code[1] & 1 else -1.
        return [value / max(1, len(pieces)) for value in values]
    result = {'lexical': {}, 'layout_by_lexical_position': {}}
    for word in sorted(set(words)):
        hidden = [math.tanh(v) for v in affine(features(word), state['lexical.0.weight'], state['lexical.0.bias'])]
        content = math.tanh(affine(hidden, state['lexical.2.weight'], state['lexical.2.bias'])[0])
        result['lexical'][word] = {'scalar': content, 'output_tanh_derivative': 1 - content * content}
    for position in range(3):
        layout = math.tanh(affine([int(i != position) for i in range(3)], state['layout.0.weight'], state['layout.0.bias'])[0])
        result['layout_by_lexical_position'][str(position)] = {'scalar': layout, 'output_tanh_derivative': 1 - layout * layout}
    return result


def audit_saved(repo, audit):
    root = repo / 'experiments/predictive_nucleus'; data = root / 'data/binding-v1'
    result = root / 'results/binding-v1'; traces = result / 'traces'; scoring = result / 'scoring'
    config, freeze = h.read(root / 'binding_protocol_v1.json'), h.read(data / 'freeze.json')
    manifest, trained = h.read(traces / 'manifest.json'), h.read(root / 'data/binding-fit-v1/checkpoints.json.xz')
    seeds = config['model_seeds']; audit.equal(seeds, [7, 11, 23, 37, 53], 'seeds')
    audit.equal(h.sha(root / 'binding_protocol_v1.json'), (root / 'snapshots/binding_protocol_v1.sha256').read_text().split()[0], 'lock')
    audit.equal(freeze['protocol_sha256'], h.sha(root / 'binding_protocol_v1.json'), 'protocol binding')
    for name, digest in {**freeze['sources'], **freeze['historical']}.items(): audit.equal(h.sha(root / name), digest, 'frozen/' + name)
    for name, digest in h.read(root / 'binding_freeze_v1.json').items(): audit.equal(h.sha(data / name), digest, 'data/' + name)
    audit.equal([manifest['complete'], manifest['oracle_opened']], [True, False], 'collection status')
    audit.equal(manifest['freeze_sha256'], h.sha(data / 'freeze.json'), 'collection data')
    audit.equal(manifest['checkpoint_sha256'], h.sha(root / 'data/binding-fit-v1/checkpoints.json.xz'), 'collection weights')
    audit.equal(trained['freeze_sha256'], manifest['freeze_sha256'], 'fitted data')
    audit.equal(trained['complete'], True, 'fit completion')
    audit.equal(set(trained['checkpoints']), {f'{a}/{s}' for a in ARMS for s in seeds}, 'fits inventory')
    for key, checkpoint in trained['checkpoints'].items():
        arm, seed = key.split('/'); fit = trained['reports'][seed]['reports'][arm]
        audit.equal([*h.fingerprint(checkpoint['state']), checkpoint['state_sha256'], fit['final_sha256']],
                    [fit['final_sha256'], PARAMETERS[arm], fit['final_sha256'], fit['final_sha256']], 'checkpoint/' + key)
        audit.equal([fit['updates'], fit['observed_events_per_update']], [256, 1024], 'exposure/' + key)
    training = h.read(data / 'train-inputs.json.xz')
    words = {word for r in training['episodes'] for event in r['utterances'] for word in event['text'].split() if word not in r['entities']}
    for seed in seeds:
        audit.equal(trained['reports'][str(seed)]['training_input_sha256'], h.canonical(training), 'training input')
    audit.equal({key: trained['runtime'][key] for key in config['execution']['runtime']}, config['execution']['runtime'], 'fit runtime')
    inputs = {(law, bank): h.read(root / 'data' / folder / f'{law}-inputs.json.xz') for law in LAWS for bank, folder in BANKS.items()}
    expected = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for law in LAWS for seed in seeds for arm in ARMS for bank in BANKS}
    require(set(manifest['artifacts']) == expected, 'trace inventory differs')
    totals = defaultdict(int)
    # Validate every required point before opening targets or saved scoring outputs.
    for name, item in manifest['artifacts'].items():
        audit.equal([h.sha(traces / name), (traces / name).stat().st_size], [item['sha256'], item['bytes']], 'receipt/' + name)
        trace = h.read(traces / name); law, seed, arm, bank = (trace[k] for k in ('law', 'seed', 'arm', 'bank'))
        require(name == f'trace-{law}-{seed}-{arm}-{bank}.json.xz', 'trace substitution')
        for field in ('freeze_sha256', 'checkpoint_sha256', 'weights_publication'): audit.equal(trace[field], manifest[field], field)
        audit.equal(trace['state_sha256'], trained['checkpoints'][f'{arm}/{seed}']['state_sha256'], 'trace state')
        audit.equal(trace['input_sha256'], h.canonical(inputs[law, bank]), 'trace input')
        indexed = rows(trace['points'], {r['id']: r for r in inputs[law, bank]['episodes']}, bank == 'fresh')
        totals[bank] += len(indexed)
    print('Audit: all 262080 trace inventories validated; opening saved targets', file=sys.stderr, flush=True)
    require(audit.discrepancy_count == 0, 'binding audit failed before gold access')
    saved = h.read(scoring / 'summary.json.xz'); decision = h.read(scoring / 'decision.json'); failure = h.read(scoring / 'failure.json')
    audit.equal(saved['trace_manifest_sha256'], h.sha(traces / 'manifest.json'), 'summary manifest')
    audit.equal(saved['decision'], decision, 'decision copy')
    audit.equal([failure['stage'], failure['error'], failure['decision'], failure['retry_permitted']],
                ['score', 'NameError', 'STOP_INCOMPLETE_EXECUTION', False], 'retained original failure')
    audit.check("name 'json' is not defined" in failure['message'], 'original reporting defect')
    checks, details = {}, {}
    for law in LAWS:
        inventories = {bank: gold_inventory(audit, inputs[law, bank], h.read(root / 'data' / folder / f'{law}-oracle.json.xz')) for bank, folder in BANKS.items()}
        records, gold, pairs = inventories['fresh']
        for seed in seeds:
            key = f'{law}/{seed}'; scored, reports, retained = {}, {}, defaultdict(dict)
            print('Audit: ' + key, file=sys.stderr, flush=True)
            native_rows = rows(saved['native_references'][key], records, native=True)
            native = {(i, t): p for (i, t, _), p in measure(audit, native_rows, records, gold).items()}
            for arm in ARMS:
                for bank in BANKS:
                    name = f'trace-{law}-{seed}-{arm}-{bank}.json.xz'
                    require(h.sha(traces / name) == manifest['artifacts'][name]['sha256'], 'trace changed during audit')
                    rec, target, pair = inventories[bank]
                    measured = measure(audit, rows(h.read(traces / name)['points'], rec, bank == 'fresh'), rec, target)
                    if bank == 'fresh':
                        reports[arm], scored[arm] = fresh_summary(measured, rec, target, pair, config['analysis'])
                        audit.equal(saved['reports'][key + '/' + arm], reports[arm], key + '/' + arm)
                    else:
                        prior_arm = 'retention' if bank == 'bilingual_retention' else 'grounded'
                        prior = h.read(root / f'results/lexical-v1/trace-{law}-{seed}-{prior_arm}.json.xz')
                        old = {(i, t): p for (i, t, _), p in measure(audit, rows(prior['points'], rec), rec, target).items()}
                        current = {(i, t): p for (i, t, _), p in measured.items()}
                        retained[arm][bank] = {'all': h.metrics(list(current.values())), **delta(current, old)}
            comparisons = {'factor_vs_' + arm: delta(scored['factor'], scored[arm]) for arm in ('gru', 'additive')}
            comparisons.update(native={arm: delta(points, native) for arm, points in scored.items()}, retention=dict(retained))
            audit.equal(saved['comparisons'][key], comparisons, key + '/comparisons')
            check = dict(reports['factor']['checks'])
            check.update(native_exact_retention=not comparisons['native']['factor']['regressions'],
                old_exact_retention=not any(v['regressions'] for v in retained['factor'].values()),
                additive_held_order_gain=(reports['factor']['held']['order_correct'] - reports['additive']['held']['order_correct']) /
                    reports['factor']['held']['order_planned'] >= config['analysis']['min_additive_gain'])
            checks[key] = check
            details[key] = {arm: {'all': reports[arm]['all'], 'held': reports[arm]['held'],
                'retention_regressions': {bank: len(value['regressions']) for bank, value in retained[arm].items()}}
                for arm in ARMS}
    audit.equal(dict(totals), {'fresh': 74880, 'bilingual_retention': 62400, 'lexical_retention': 124800}, 'all planned forecasts')
    audit.equal(decision['checks'], checks, 'decision checks')
    outcome = 'KEEP_STRUCTURAL_BINDING' if all(all(c.values()) for c in checks.values()) else 'REVISE_STRUCTURAL_BINDING'
    audit.equal(decision['decision'], outcome, 'arithmetic decision')
    return {'version': 'binding-saved-audit-v1', 'recovered_scientific_interpretation': outcome,
        'original_process_status': 'STOP_INCOMPLETE_EXECUTION', 'original_failure_preserved': True,
        'source_commit': 'b63749c90fd91148f0451bd2e2fd030f3de279cd',
        'forecast_count': sum(totals.values()), 'native_reference_count': sum(len(v) for v in saved['native_references'].values()),
        'new_fits': 0, 'new_collections': 0, 'model_execution': False, 'scientific_admission': False,
        'scope': 'Internal saved-byte/arithmetic audit; no independent custody or replay of candidate/native models.',
        'auditor_sha256': h.sha(__file__), 'metric_helper_sha256': h.sha(h.__file__),
        'factor_geometry': {str(seed): factor_geometry(trained['checkpoints'][f'factor/{seed}']['state'], words) for seed in seeds},
        'bound_sources': len(freeze['sources']), 'bound_historical_files': len(freeze['historical']),
        'artifacts': {name: h.sha(scoring / name) for name in ('summary.json.xz', 'decision.json', 'failure.json')},
        'details': details, 'check_count': audit.checks, 'discrepancy_count': audit.discrepancy_count,
        'discrepancies': audit.discrepancies, 'audit_passed': audit.discrepancy_count == 0}


def write_report(path, report):
    """Serialize before creating the exclusive output; never overwrite evidence."""
    payload = json.dumps(h.safe(report), sort_keys=True, indent=2, allow_nan=False) + '\n'
    with path.open('x') as stream: stream.write(payload)
    return json.dumps({key: report[key] for key in ('audit_passed', 'recovered_scientific_interpretation', 'original_process_status')})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv); audit = h.Audit()
    result = audit_saved(args.repo.resolve(), audit)
    print(write_report(args.output, result), flush=True)
    return int(not result['audit_passed'])


if __name__ == '__main__': raise SystemExit(main())
