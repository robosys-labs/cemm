"""Saved-forecast binding analysis, reusing the original probability metrics.

All planned traces validate before oracle metadata is opened. Native gold-action
references are evaluated afterwards and remain separately labeled. No refitting.
"""
from collections import defaultdict
import math

from . import acceptance_contract as c, continuation_run as io, bilingual_scoring as metrics
from .bilingual_contract import validate_inputs
from .binding_model import ARMS
from . import binding_study as study


def oracle(inputs, value, law):
    records = {r['id']: r for r in validate_inputs(inputs)['episodes']}
    c.require(value['version'] == 'binding-oracle-v1' and value['input_sha256'] == c.digest(inputs), 'oracle binding differs')
    gold = {g['id']: g for g in value['episodes']}
    c.require(len(gold) == len(value['episodes']) and gold.keys() == records.keys(), 'oracle coverage differs')
    pairs = {kind: defaultdict(list) for kind in ('lexical', 'role')}
    table = {'nand': (1, 1, 1, 0), 'nor': (1, 0, 0, 0)}[law]
    def step(bits, action, mode):
        after = list(bits)
        if action[0] == 1: after[action[1]] = action[3]
        else:
            source, target = action[1:3] if mode == 0 else action[1:3][::-1]
            after[target] = table[2 * bits[source] + bits[target]]
        return after
    for identity, meta in gold.items():
        record = records[identity]; count = len(record['utterances'])
        c.require(meta['law'] == law and meta['mode'] in (0, 1) and all(len(meta[key]) == count
            for key in ('actions', 'action_orders', 'truth', 'opposite_truth', 'cells')), 'oracle geometry differs')
        before = record['anchor']
        for event in record['context']:
            c.require(step(before, event['action'], meta['mode']) == event['reading'], 'context physics differs')
            before = event['reading']
        for t, event in enumerate(record['utterances']):
            tokens = event['text'].split(); mentions = [record['entities'].index(w) for w in tokens if w in record['entities']]
            order = meta['action_orders'][t]; action = meta['actions'][t]
            cell = meta['cells'][t]
            c.require(type(order) is int and order in (0, 1) and action ==
                [0, mentions[order], mentions[1 - order], -1], 'oracle action/order differs')
            c.require(cell['word'] == next(w for w in tokens if w not in record['entities']) and
                cell['layout'] == {1: 'svo', 2: 'osv', 0: 'vos'}[tokens.index(cell['word'])], 'oracle cell differs')
            c.require(step(before, action, meta['mode']) == meta['truth'][t] == event['reading'] and
                step(before, [0, action[2], action[1], -1], meta['mode']) == meta['opposite_truth'][t], 'oracle physics differs')
            before = event['reading']
        for kind in pairs: pairs[kind][meta[kind + '_pair_id']].append(identity)
    for kind, groups in pairs.items():
        for members in groups.values():
            c.require(len(members) == 2, 'incomplete pair')
            a, b = (gold[k] for k in members); x, y = (records[k] for k in members)
            c.require(all(x[k] == y[k] for k in ('entities', 'anchor', 'context')), 'paired context differs')
            if kind == 'lexical':
                c.require({a['polarity'], b['polarity']} == {0, 1} and x['utterances'][:-1] == y['utterances'][:-1], 'lexical prefix differs')
            else:
                c.require({a['direction'], b['direction']} == {0, 1} and all(
                    u == [0, v[2], v[1], -1] for u, v in zip(a['actions'], b['actions'], strict=True)), 'role pair not reversed')
    return records, gold, pairs


def index_trace(trace, inputs, fresh):
    records = {r['id']: r for r in inputs['episodes']}
    expected = {(r['id'], t, 'canonical') for r in records.values() for t in range(len(r['utterances']))}
    if fresh:
        expected |= {(r['id'], len(r['utterances']) - 1, view) for r in records.values() for view in ('masked', 'swapped')}
    rows = {}
    for row in trace['points']:
        c.fields(row, ('id', 'step', 'view', 'logp', 'order_logp'))
        key = row['id'], row['step'], row['view']
        c.require(type(row['step']) is int and key in expected and key not in rows, 'unexpected/duplicate forecast')
        row = dict(row); row['logp'] = metrics._logs(row['logp'], 2 ** len(records[row['id']]['entities']))
        row['order_logp'] = metrics._logs(row['order_logp'], 2); rows[key] = row
    c.require(rows.keys() == expected, 'missing planned forecasts')
    return rows


def points(rows, records, gold):
    return {(i, t): metrics._point(row, records[i], gold[i]) for (i, t, view), row in rows.items() if view == 'canonical'}


def deltas(current, reference):
    c.require(current.keys() == reference.keys(), 'comparison denominator differs')
    repaired, broken, worse, better, undefined = [], [], [], [], []
    for key, now in current.items():
        old = reference[key]; change = metrics._difference(now['nll'], old['nll'])
        if now['correct'] and not old['correct']: repaired.append(list(key))
        if old['correct'] and not now['correct']: broken.append(list(key))
        if change is None: undefined.append(list(key))
        elif change > 0: worse.append([*key, change])
        elif change < 0: better.append([*key, change])
    return {'planned': len(current), 'repairs': repaired, 'regressions': broken,
        'nll_worse': worse, 'nll_better': better, 'nll_undefined_difference': undefined,
        'mean_nll_change': metrics._difference(math.fsum(v['nll'] for v in current.values()) / len(current),
                                              math.fsum(v['nll'] for v in reference.values()) / len(reference))}


def summary(rows, records, gold, pairs, limits):
    scored = points(rows, records, gold)
    cells = defaultdict(list); held = []
    for (identity, t), point in scored.items():
        meta = gold[identity]; cell = meta['cells'][t]
        cells['/'.join((meta['family'], cell['word'], cell['layout']))].append(point)
        if cell['held']: held.append(point)
    stats = {key: metrics._stats(value) for key, value in cells.items()}
    pair_results = {}
    for kind, groups in pairs.items():
        pair_results[kind] = {'planned': len(groups), 'correct': sum(all(scored[i, t]['correct']
            for i in members for t in (range(len(records[i]['utterances'])) if kind == 'role' else
                                      (len(records[i]['utterances']) - 1,))) for members in groups.values())}
    tv = lambda a, b: math.fsum(abs(math.exp(x) - math.exp(y)) for x, y in zip(a, b, strict=True)) / 2
    contrasts = []
    for pair_id, (a, b) in pairs['lexical'].items():
        t = len(records[a]['utterances']) - 1; ca, cb = scored[a, t], scored[b, t]
        critical = gold[a]['truth'][t] != gold[b]['truth'][t]
        index = metrics._index(gold[a]['truth'][t])
        contrasts.append({'pair_id': pair_id, 'critical': critical,
            'gap': abs(math.exp(rows[a, t, 'canonical']['logp'][index]) - math.exp(rows[b, t, 'canonical']['logp'][index])),
            'masked_tv': tv(rows[a, t, 'masked']['logp'], rows[b, t, 'masked']['logp']),
            'swap_tv': max(tv(rows[a, t, 'swapped']['logp'], rows[b, t, 'canonical']['logp']),
                           tv(rows[b, t, 'swapped']['logp'], rows[a, t, 'canonical']['logp'])),
            'masked_both_correct': all(metrics._point(rows[i, t, 'masked'], records[i], gold[i])['correct'] for i in (a, b))})
    critical = [p for p in contrasts if p['critical']]
    checks = {'cell_world_accuracy': all(s['accuracy'] >= limits['min_accuracy'] for s in stats.values()),
        'cell_order_accuracy': all(s['order_correct'] >= limits['min_accuracy'] * s['order_planned'] for s in stats.values()),
        'cell_nll': all(s['mean_nll'] <= limits['max_mean_nll'] for s in stats.values()),
        'critical_probabilities': all(not s['critical_planned'] or (s['min_critical_true_probability'] >=
            limits['min_true_probability'] and s['max_wrong_order_probability'] <= limits['max_foil_probability']) for s in stats.values()),
        'lexical_and_role_pairs': all(s['correct'] >= limits['min_accuracy'] * s['planned'] for s in pair_results.values()),
        'lexical_gap': bool(critical) and min(p['gap'] for p in critical) >= limits['min_gap'],
        'masked_invariance': max(p['masked_tv'] for p in contrasts) <= limits['max_control_tv'] and not any(p['masked_both_correct'] for p in critical),
        'swap_equivariance': max(p['swap_tv'] for p in contrasts) <= limits['max_control_tv']}
    return {'all': metrics._stats(list(scored.values())), 'held': metrics._stats(held),
        'by_cell': stats, 'pairs': pair_results, 'contrasts': contrasts, 'checks': checks}, scored


def score(data, fitted, traces, output):
    config, freeze = study.verify(data); manifest = io._read(traces / 'manifest.json')
    saved = io._read(fitted / 'checkpoints.json.xz')
    c.require(manifest['complete'] is True and manifest['oracle_opened'] is False and
        manifest['freeze_sha256'] == io._hash(data / 'freeze.json') and
        manifest['checkpoint_sha256'] == io._hash(fitted / 'checkpoints.json.xz'), 'trace manifest differs')
    expected = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for law in ('nand', 'nor') for seed in config['model_seeds']
                for arm in ARMS for bank in ('fresh', *study.BANKS)}
    c.require(set(manifest['artifacts']) == expected, 'trace file inventory differs')
    inputs, indexed = {}, {}
    for law in ('nand', 'nor'):
        for bank in ('fresh', *study.BANKS):
            path = data if bank == 'fresh' else io.ROOT / 'data' / study.BANKS[bank]
            inputs[law, bank] = validate_inputs(io._read(path / f'{law}-inputs.json.xz'))
    for name, item in manifest['artifacts'].items():
        c.require(io._hash(traces / name) == item['sha256'], 'trace bytes differ')
        trace = io._read(traces / name); law, seed, arm, bank = (trace[k] for k in ('law', 'seed', 'arm', 'bank'))
        c.require(name == f'trace-{law}-{seed}-{arm}-{bank}.json.xz' and
            trace['input_sha256'] == c.digest(inputs[law, bank]) and
            all(trace[k] == manifest[k] for k in ('freeze_sha256', 'checkpoint_sha256', 'weights_publication')) and
            trace['state_sha256'] == saved['checkpoints'][f'{arm}/{seed}']['state_sha256'], 'trace identity differs')
        indexed[law, seed, arm, bank] = index_trace(trace, inputs[law, bank], bank == 'fresh')
    # Only now open evaluator targets and archived forecast baselines.
    output.mkdir(parents=True, exist_ok=False); reports, comparisons, decisions, references = {}, {}, {}, {}
    for law in ('nand', 'nor'):
        records, gold, pairs = oracle(inputs[law, 'fresh'], io._read(data / f'{law}-oracle.json.xz'), law)
        for seed in config['model_seeds']:
            key = f'{law}/{seed}'; all_scored = {}; retained = defaultdict(dict)
            for arm in ARMS:
                report, scored = summary(indexed[law, seed, arm, 'fresh'], records, gold, pairs, config['analysis'])
                reports[key + '/' + arm] = report; all_scored[arm] = scored
            native = metrics._native(inputs[law, 'fresh'], gold, freeze['checkpoints'], law, seed)
            references[key] = list(native.values())
            native_points = {(i, t): metrics._point(row, records[i], gold[i]) for (i, t), row in native.items()}
            for bank, folder in study.BANKS.items():
                oldrecords, oldgold, _ = metrics._inventory(inputs[law, bank], io._read(
                    io.ROOT / 'data' / folder / f'{law}-oracle.json.xz'), law)
                oldarm = 'retention' if bank == 'bilingual_retention' else 'grounded'
                archived = io._read(study.OLD / f'trace-{law}-{seed}-{oldarm}.json.xz')
                c.require(archived['input_sha256'] == c.digest(inputs[law, bank]), 'archived input differs')
                oldpoints = {(r['id'], r['step']): metrics._point(r, oldrecords[r['id']], oldgold[r['id']]) for r in archived['points']}
                for arm in ARMS:
                    current = points(indexed[law, seed, arm, bank], oldrecords, oldgold)
                    retained[arm][bank] = {'all': metrics._stats(list(current.values())), **deltas(current, oldpoints)}
            comparisons[key] = {'factor_vs_' + arm: deltas(all_scored['factor'], all_scored[arm]) for arm in ('gru', 'additive')}
            comparisons[key]['native'] = {arm: deltas(current, native_points) for arm, current in all_scored.items()}
            comparisons[key]['retention'] = dict(retained)
            check = dict(reports[key + '/factor']['checks'])
            check['native_exact_retention'] = not comparisons[key]['native']['factor']['regressions']
            check['old_exact_retention'] = not any(v['regressions'] for v in retained['factor'].values())
            check['additive_held_order_gain'] = (reports[key + '/factor']['held']['order_correct'] -
                reports[key + '/additive']['held']['order_correct']) / reports[key + '/factor']['held']['order_planned'] >= config['analysis']['min_additive_gain']
            decisions[key] = check
    kept = all(all(v.values()) for v in decisions.values())
    decision = {'decision': 'KEEP_STRUCTURAL_BINDING' if kept else 'REVISE_STRUCTURAL_BINDING',
        'execution_complete': True, 'checks': decisions, 'scientific_admission': False,
        'scope': 'Public same-team third-layout mixed-sequence transfer; no general language or independent custody claim.'}
    io._write(output / 'summary.json.xz', metrics._safe({'decision': decision, 'reports': reports,
        'comparisons': comparisons, 'native_references': references, 'trace_manifest_sha256': io._hash(traces / 'manifest.json')}))
    io._write(output / 'decision.json', decision)
    print(json.dumps(decision), flush=True)
