"""Stdlib audit of complete v2 saved evidence; no model or study-scorer imports.

Recomputes every acceptance check, native/retention point metric and scalar
summary from published logs and saved evaluator distributions. Hashes, runtime
receipts and actual tensor masks are checked separately. This is same-team
arithmetic verification, not independent challenge custody or another trial.
"""
import argparse
from collections import defaultdict
import importlib
import json
import math
from pathlib import Path
import sys

LAWS, SEEDS, ARMS = ('nand', 'nor'), (7, 11, 23, 37, 53), ('parent', 'acquired', 'no_change')
BANKS = ('bilingual', 'lexical', 'binding', 'saturation', 'centering', 'coordinate')


def require(ok, label):
    if not ok: raise ValueError(label)


def average(values):
    return math.fsum(v / len(values) for v in values) if values else None


def logs(values, count, tolerance=1e-12):
    require(type(values) is list and len(values) == count, 'log geometry')
    values = [h.number(v) for v in values]
    require(all(type(v) in (float, int) and not math.isnan(v) and v != math.inf for v in values), 'log values')
    top = max(values)
    require(math.isfinite(top) and abs(top + math.log(math.fsum(math.exp(v - top) for v in values))) <= tolerance,
            'log normalization')
    return values


def index_rows(rows, records, language=False, archived=False):
    expected = {(i, t) for i, e in records.items() for t in range(len(e['utterances' if language else 'actions']))}
    result, seen = {}, set()
    for row in rows:
        require(set(row) == {'id', 'step', 'logp'} | ({'view', 'order_logp'} if language else set()), 'row fields')
        key, view = (row['id'], row['step']), row.get('view', 'canonical')
        require(type(row['step']) is int and key in expected and (*key, view) not in seen and
            (view == 'canonical' or archived and view in ('masked', 'swapped')), 'row identity/coverage')
        seen.add((*key, view)); n = len(records[key[0]]['entities' if language else 'ids'])
        world = logs(row['logp'], 2 ** n, 1e-10 if language else 1e-12)
        order = logs(row['order_logp'], 2, 1e-10) if language else None
        if view == 'canonical': result[key] = {'logp': world, 'order_logp': order}
    require(result.keys() == expected, 'missing forecast rows')
    return result


def metric(points):
    n = len(points); correct = sum(p['correct'] for p in points)
    mean = lambda key: average([p[key] for p in points])
    bins, ece = [], 0.
    for i in range(10):
        group = [p for p in points if p['confidence'] >= i / 10 and (i == 9 or p['confidence'] < (i + 1) / 10)]
        accuracy, confidence = average([int(p['correct']) for p in group]), average([p['confidence'] for p in group])
        if group: ece += len(group) / n * abs(accuracy - confidence)
        bins.append({'bin': i, 'lower': i / 10, 'upper': (i + 1) / 10, 'count': len(group),
                     'accuracy': accuracy, 'confidence': confidence})
    result = {'planned_points': n, 'produced_forecasts': n, 'supported_forecasts': n,
        'explicit_abstentions': 0, 'unproduced_forecasts': 0, 'correct': correct, 'wrong_supported': n - correct,
        'accuracy': correct / n if n else None, 'accuracy_among_supported': correct / n if n else None,
        'production_coverage': 1. if n else None, 'support_coverage': 1. if n else None,
        'mean_nll': mean('nll'), 'mean_brier': mean('brier'), 'conditional_mean_nll': mean('nll'),
        'conditional_mean_brier': mean('brier'), 'infinite_nll_count': sum(math.isinf(p['nll']) for p in points),
        'ece_10_conditional_on_support': ece if n else None, 'ece_bins': bins,
        'tied_forecasts': sum(p['ties'] > 1 for p in points),
        'underflow_world_count': sum(p['underflow'] for p in points),
        'unchanged_bit_errors': sum(p['unchanged_errors'] for p in points),
        'unchanged_bits_planned': sum(p['unchanged'] for p in points),
        'unchanged_bits_answered': sum(p['unchanged'] for p in points),
        'physical_lineages': len({p['lineage'] for p in points}), 'timed_forecasts': 0,
        **{k: None for k in ('mean_reported_wall_seconds', 'mean_reported_cpu_seconds',
            'wall_seconds_p50', 'wall_seconds_p95', 'cpu_seconds_p50', 'cpu_seconds_p95')},
        'map_outside_support': sum(p['map_outside_support'] for p in points),
        'known_unchanged_errors': sum(p['known_unchanged_errors'] for p in points)}
    for key in ('oracle_kl', 'oracle_total_variation', 'oracle_brier_regret',
                'outside_support_mass', 'oracle_map_expected_accuracy'):
        result['mean_' + key] = mean(key); result['max_' + key] = max((p[key] for p in points), default=None)
    return result


def strata(points):
    return {'all': metric(points), 'identifiable': metric([p for p in points if p['answerable']]),
            'ambiguous': metric([p for p in points if not p['answerable']])}


def summarize(points, pairs):
    trajectories, cells = defaultdict(list), defaultdict(list)
    for p in points:
        trajectories[p['episode']].append(p)
        if p['set'] is not None:
            s = p['set']; cells[f"{p['family']}/n{p['n']}/prior{s['prior']}/request{s['requested']}/changed{int(s['changed'])}"].append(p)
    whole = [{'episode': key, 'correct': all(p['correct'] for p in rows),
        'identifiable_points': sum(p['answerable'] for p in rows),
        'identifiable_correct': all(p['correct'] for p in rows if p['answerable'])}
        for key, rows in sorted(trajectories.items())]
    lookup = {p['episode']: p for p in whole}
    paired = [{'pair_id': key, 'episodes': ids, 'correct': all(lookup[i]['correct'] for i in ids),
        'identifiable_correct': all(lookup[i]['identifiable_correct'] for i in ids)} for key, ids in sorted(pairs.items())]
    return {**strata(points), **{name: {'planned': len(rows), 'correct': sum(r['correct'] for r in rows),
        'identifiable_correct': sum(r['identifiable_correct'] for r in rows), 'records': rows}
        for name, rows in (('trajectories', whole), ('role_pairs', paired))},
        'by_family': {f: strata([p for p in points if p['family'] == f]) for f in sorted({p['family'] for p in points})},
        'by_entity_count': {str(n): strata([p for p in points if p['n'] == n]) for n in sorted({p['n'] for p in points})},
        'by_set_cell': {k: metric(v) for k, v in sorted(cells.items())},
        'set_by_changed': {str(v).lower(): metric([p for p in points if p['set'] is not None and p['set']['changed'] == v])
                           for v in (False, True)},
        'wrong_records': [[p['episode'], p['step']] for p in points if not p['correct']]}


def measured_native(indexed, records, target, information, metadata, audit):
    points = {}
    for (identity, t), row in indexed.items():
        e, meta, inf = records[identity], metadata[identity], information[identity]['forecasts'][t]
        ids = sorted(e['ids']); n = len(ids); before, after = e['observations'][t:t + 2]
        truth, previous = h.index([after[i] for i in ids]), h.index([before[i] for i in ids])
        support, weights = inf['possible_worlds'], inf['probabilities']; q = dict(zip(support, weights, strict=True))
        require(support == sorted(set(support)) and truth in q and all(v > 0 for v in weights) and
                abs(math.fsum(weights) - 1.) <= 1e-12, 'invalid evaluator distribution')
        audit.equal(target[identity]['truth'][t + 1], after, 'truth agrees with delivered reading')
        audit.equal(target[identity]['possible_worlds'][t], support, 'information support binding')
        audit.equal(target[identity]['information_keys'][t], inf['information_key'], 'information-key binding')
        values = row['logp']; probability = [math.exp(v) for v in values]; top = max(values); best = values.index(top)
        unchanged = [i for i in range(n) if ((truth >> i) & 1) == ((previous >> i) & 1)]
        known = [i for i in range(n) if len({(w >> i) & 1 for w in [previous, *support]}) == 1]
        s = next((x for x in meta['set_points'] if x['step'] == t), None)
        action = e['actions'][t]
        if s is not None:
            a = action['participants'][0]
            audit.equal(s, {'step': t, 'prior': before[a], 'requested': action['value'],
                             'changed': before[a] != action['value']}, 'SET cell metadata')
        points[identity, t] = {'episode': identity, 'step': t, 'action_kind': action['kind'],
            'answerable': len(support) == 1, 'correct': best == truth, 'map_world': best,
            'nll': -values[truth], 'brier': math.fsum((p - int(w == truth)) ** 2 for w, p in enumerate(probability)),
            'oracle_kl': math.fsum(p * (math.log(p) - values[w]) for w, p in q.items()),
            'oracle_total_variation': math.fsum(abs(p - q.get(w, 0.)) for w, p in enumerate(probability)) / 2,
            'oracle_brier_regret': math.fsum((p - q.get(w, 0.)) ** 2 for w, p in enumerate(probability)),
            'outside_support_mass': math.fsum(p for w, p in enumerate(probability) if w not in q),
            'map_outside_support': best not in q, 'known_unchanged_errors': sum(((best >> i) & 1) != ((previous >> i) & 1) for i in known),
            'set': s, 'family': meta['family'], 'lineage': meta['lineage'], 'n': n, 'confidence': probability[best],
            'ties': values.count(top), 'underflow': sum(math.isfinite(v) and p == 0 for v, p in zip(values, probability)),
            'unchanged': len(unchanged), 'unchanged_errors': sum(((best >> i) & 1) != ((truth >> i) & 1) for i in unchanged),
            'oracle_map_expected_accuracy': max(weights), 'probabilities': probability}
    return points


def changes(now, before):
    result = {k: [] for k in ('repairs', 'regressions', 'identifiable_regressions', 'nll_worse',
                             'nll_better', 'nll_undefined', 'probability_changes')}
    for key, p in now.items():
        old = before[key]; delta = h.difference(p['nll'], old['nll'])
        if p['correct'] and not old['correct']: result['repairs'].append(list(key))
        if old['correct'] and not p['correct']:
            result['regressions'].append(list(key))
            if p['answerable']: result['identifiable_regressions'].append(list(key))
        if delta is None: result['nll_undefined'].append(list(key))
        elif delta: result['nll_worse' if delta > 0 else 'nll_better'].append([*key, delta])
        distances = [abs(a - b) for a, b in zip(p['probabilities'], old['probabilities'], strict=True)]
        result['probability_changes'].append({'id': key[0], 'step': key[1], 'nll_change': delta,
            'max_abs_probability_change': max(distances), 'total_variation': math.fsum(distances) / 2})
    keys = [k for k, p in now.items() if p['set'] is not None and p['set']['changed']]
    mean = lambda rows, selected: average([rows[k]['nll'] for k in selected])
    return {**result, 'planned': len(now), 'mean_nll_change': h.difference(mean(now, now), mean(before, before)),
        'changed_set_planned': len(keys), 'changed_set_nll_gain': h.difference(mean(before, keys), mean(now, keys)) if keys else None}


def native_checks(report, comparisons, limits):
    identifiable = [report['identifiable'], *[v['identifiable'] for v in report['by_family'].values()],
                    *[v['identifiable'] for v in report['by_entity_count'].values()]]
    probability = [v[k] for v in report['by_family'].values() for k in ('identifiable', 'ambiguous') if v[k]['planned_points']]
    cells = list(report['by_set_cell'].values())
    return {'complete_support': report['all']['support_coverage'] == 1.,
        'identifiable_accuracy': all(s['accuracy'] is not None and s['accuracy'] >= limits['identifiable_accuracy'] for s in identifiable),
        'supported_MAP_worlds': report['all']['map_outside_support'] == 0,
        'known_unchanged_preserved': report['all']['known_unchanged_errors'] == 0,
        'conditional_probability_quality': all(s['mean_oracle_kl'] <= limits['mean_oracle_kl'] for s in probability),
        'ambiguous_no_collapse': not report['ambiguous']['planned_points'] or
            report['ambiguous']['max_oracle_total_variation'] <= limits['max_ambiguous_total_variation'],
        'each_set_cell': bool(cells) and all(s['accuracy'] >= limits['identifiable_accuracy'] and
            s['mean_nll'] <= limits['max_set_mean_nll'] and s['known_unchanged_errors'] == 0 for s in cells),
        'identifiable_trajectories': report['trajectories']['identifiable_correct'] == report['trajectories']['planned'],
        'identifiable_role_pairs': report['role_pairs']['identifiable_correct'] == report['role_pairs']['planned'],
        'parent_identifiable_retention': not comparisons['parent']['identifiable_regressions'],
        **{arm + '_changed_set_gain': comparisons[arm]['changed_set_nll_gain'] is not None and
            comparisons[arm]['changed_set_nll_gain'] >= limits['min_changed_set_nll_gain'] for arm in ('parent', 'no_change')}}


def retained(now, old, records, limits):
    result = []
    distance = lambda a, b: 0. if a == b else math.inf if math.isinf(a) or math.isinf(b) else abs(a - b)
    for key in sorted(now):
        a, b = now[key], old[key]; truth = h.index(records[key[0]]['utterances'][key[1]]['reading'])
        maps = {name: (a[name].index(max(a[name])), b[name].index(max(b[name]))) for name in ('logp', 'order_logp')}
        aw, bw = maps['logp']; ao, bo = maps['order_logp']; an, bn = -a['logp'][truth], -b['logp'][truth]
        result.append({'id': key[0], 'step': key[1], 'correct': aw == truth, 'archived_correct': bw == truth,
            'regression': bw == truth and aw != truth, 'map_world': aw, 'archived_map_world': bw,
            'map_order': ao, 'archived_map_order': bo, 'world_map_changed': aw != bw, 'order_map_changed': ao != bo,
            'logp_equal': a['logp'] == b['logp'], 'order_logp_equal': a['order_logp'] == b['order_logp'],
            'nll': an, 'archived_nll': bn, 'nll_change': h.difference(an, bn),
            **{label: max(distance(x, y) for x, y in zip(a[name], b[name], strict=True)) for name, label in
               (('logp', 'max_logp_change'), ('order_logp', 'max_order_logp_change'))},
            **{label: math.fsum(abs(math.exp(x) - math.exp(y)) for x, y in zip(a[name], b[name], strict=True)) / 2
               for name, label in (('logp', 'total_variation'), ('order_logp', 'order_total_variation'))}})
    selected = lambda field: [[p['id'], p['step']] for p in result if p[field]]
    world_max = max(p['max_logp_change'] for p in result); order_max = max(p['max_order_logp_change'] for p in result)
    checks = {'world_logp_retained': world_max <= limits['max_retention_logp_change'],
        'order_logp_retained': order_max <= limits['max_retention_order_logp_change'],
        'world_map_retained': not selected('world_map_changed'), 'order_map_retained': not selected('order_map_changed'),
        'no_exact_regressions': not selected('regression')}
    an, bn = average([p['nll'] for p in result]), average([p['archived_nll'] for p in result])
    return {'planned': len(result), 'correct': sum(p['correct'] for p in result),
        'archived_correct': sum(p['archived_correct'] for p in result), 'regressions': selected('regression'),
        'world_map_changes': selected('world_map_changed'), 'order_map_changes': selected('order_map_changed'),
        'exact_world_vectors': sum(p['logp_equal'] for p in result), 'exact_order_vectors': sum(p['order_logp_equal'] for p in result),
        'nll_worse': sum(p['nll_change'] is not None and p['nll_change'] > 0 for p in result),
        'nll_better': sum(p['nll_change'] is not None and p['nll_change'] < 0 for p in result),
        'nll_equal': sum(p['nll_change'] == 0 for p in result), 'nll_undefined': sum(p['nll_change'] is None for p in result),
        'mean_nll': an, 'archived_mean_nll': bn, 'mean_nll_change': h.difference(an, bn),
        'max_logp_change': world_max, 'max_order_logp_change': order_max,
        'limits': {k: limits[k] for k in ('max_retention_logp_change', 'max_retention_order_logp_change')},
        'checks': checks, 'passed': all(checks.values()), 'points': result}


def audit_saved(repo, audit, pre_score=False):
    root = repo / 'experiments/predictive_nucleus'; data = root / 'data/set-acquisition-v2'
    fitted, traces = root / 'data/set-acquisition-fit-v2', root / 'results/set-acquisition-v2/traces'
    scored = traces.parent / 'scored'
    config, freeze, trained, manifest = [h.read(p) for p in (root / 'set_acquisition_protocol_v2.json',
        data / 'freeze.json', fitted / 'training.json', traces / 'manifest.json')]
    audit.equal(config['model_seeds'], list(SEEDS), 'prescribed seeds')
    audit.equal(config['arms'], list(ARMS), 'prescribed arms')
    audit.equal([config['version'], freeze['version'], trained['version']], ['set-acquisition-v2'] * 3, 'study versions')
    audit.equal(h.sha(root / 'set_acquisition_protocol_v2.json'),
                (root / 'snapshots/set_acquisition_protocol_v2.sha256').read_text().split()[0], 'protocol lock')
    audit.equal(freeze['protocol_sha256'], h.sha(root / 'set_acquisition_protocol_v2.json'), 'protocol binding')
    for name, digest in {**freeze['sources'], **freeze['historical']}.items(): audit.equal(h.sha(root / name), digest, name)
    commitment = h.read(root / 'set_acquisition_freeze_v2.json')
    audit.equal(set(commitment), set(freeze['artifacts']) | {'freeze.json'}, 'data inventory')
    for name, digest in commitment.items(): audit.equal(h.sha(data / name), digest, 'data/' + name)
    for name, item in freeze['artifacts'].items():
        audit.equal([h.sha(data / name), (data / name).stat().st_size], [item['sha256'], item['bytes']], 'artifact/' + name)
    for receipt in (trained, manifest):
        audit.check(receipt['complete'] is True and receipt['freeze_sha256'] == h.sha(data / 'freeze.json'), 'completed bound stage')
        audit.check(receipt['runtime'] == freeze['runtime'], 'exact runtime receipt')
    audit.check(manifest['oracle_opened'] is False, 'collection has not opened evaluator')
    audit.check(h.canonical(freeze['runtime']) == freeze['runtime_sha256'], 'runtime digest')
    audit.check({k: freeze['runtime'][k] for k in config['execution']['runtime']} == config['execution']['runtime'], 'runtime versions')
    audit.equal(manifest['training_sha256'], h.sha(fitted / 'training.json'), 'actual fitted bytes binding')
    training = h.read(data / 'train-inputs.json.xz')
    audit.equal(h.sha(data / 'train-inputs.json.xz'), h.sha(root / 'data/set-acquisition-v1/train-inputs.json.xz'), 'identical training bytes')
    audit.equal(trained['training_input_sha256'], h.canonical(training), 'training observed history')
    keys = {f'{law}/{seed}' for law in LAWS for seed in SEEDS}
    require(set(trained['reports']) == set(trained['checkpoints']) == keys, 'fit inventory')
    fit_attempt = h.read(fitted / 'attempt.json'); raw_attempt = h.read(traces / 'attempt.json')
    for name in ('source_publication', 'runtime', 'freeze_sha256'): audit.check(trained[name] == fit_attempt[name], 'fit attempt/' + name)
    for name in ('weights_publication', 'runtime', 'freeze_sha256', 'training_sha256'):
        audit.check(manifest[name] == raw_attempt[name], 'raw attempt/' + name)
    for key in sorted(keys):
        law, seed = key.split('/'); item, fit = trained['checkpoints'][key], trained['reports'][key]
        parent_item = freeze['parents'][law][seed]
        parent = h.read(root / 'data/multisource-law-fit-v1' / parent_item['file'])
        current = h.read(fitted / item['file'])
        audit.equal(h.sha(fitted / item['file']), item['sha256'], 'checkpoint bytes/' + key)
        audit.equal([*h.fingerprint(current['state']), current['state_sha256']],
                    [fit['final_weights_sha256'], 562, fit['final_weights_sha256']], 'actual fitted tensor/' + key)
        audit.equal(h.fingerprint(parent['state'])[0], fit['initial_weights_sha256'], 'actual parent/' + key)
        audit.equal(current['provenance'], fit, 'checkpoint provenance/' + key)
        audit.equal(fit, h.read(fitted / f'fit-{law}-{seed}.json'), 'fit report copy/' + key)
        require(parent['state'].keys() == current['state'].keys(), 'tensor inventory')
        allowed = changed = forbidden = 0
        for name, old in parent['state'].items():
            new = current['state'][name]
            audit.check(old['shape'] == new['shape'] and old['dtype'] == new['dtype'] == 'torch.float64', 'tensor shape/dtype')
            for i, (a, b) in enumerate(zip(old['values'], new['values'], strict=True)):
                permit = name.startswith('intervention.') or name == 'background.0.weight' and i % 4 == 2
                allowed += permit; different = a.hex() != b.hex(); changed += permit and different; forbidden += not permit and different
        audit.equal([allowed, forbidden, changed], [68, 0, fit['changed_permitted_scalars']], 'actual scalar mask/' + key)
        audit.check(fit['status'] == 'COMPLETED' and fit['completed_updates'] == config['fit']['updates'] and
                    fit['observed_events_per_update'] == config['train_forecasts'], 'fit completion/exposure/' + key)
        for field in ('learning_rate', 'gradient_clip'): audit.equal(fit[field], config['fit'][field], 'fit recipe/' + field)
        audit.check([p[0] for p in fit['curve']] == list(range(config['fit']['updates'] + 1)), 'complete loss curve')
        audit.equal(fit['curve'][-1][1], fit['final_observed_train_nll'], 'final training NLL')
    language = h.read(root / 'data/coordinate-fit-v1/checkpoints.json.xz')['checkpoints']
    for seed in SEEDS:
        state = language[f'coordinates/{seed}']; audit.equal(h.fingerprint(state['state']), (state['state_sha256'], 88), 'frozen language state')
    native_inputs = {law: h.read(data / f'{law}-inputs.json.xz') for law in LAWS}
    language_inputs = {(law, bank): h.read(root / f'data/{bank}-v1/{law}-inputs.json.xz') for law in LAWS for bank in BANKS}
    expected_files = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for law in LAWS for seed in SEEDS
        for arm, bank in [*((a, 'fresh') for a in ARMS), *(('acquired', b + '_retention') for b in BANKS)]}
    require(set(manifest['artifacts']) == expected_files, 'raw trace file inventory')
    totals = defaultdict(int)
    # Complete input-only coverage/normalization checks precede any evaluator read.
    def trace(law, seed, arm, bank):
        name = f'trace-{law}-{seed}-{arm}-{bank}.json.xz'; path = traces / name
        require(h.sha(path) == manifest['artifacts'][name]['sha256'], 'raw file hash')
        value = h.read(path); observed = native_inputs[law] if bank == 'fresh' else language_inputs[law, bank[:-10]]
        require((value['law'], value['seed'], value['arm'], value['bank']) == (law, seed, arm, bank), 'trace header')
        require(value['input_sha256'] == h.canonical(observed) and all(value[k] == manifest[k] for k in
            ('runtime', 'freeze_sha256', 'training_sha256', 'weights_publication')), 'trace input/runtime/publication')
        if bank != 'fresh': require(value['language_sha256'] == language[f'coordinates/{seed}']['state_sha256'], 'trace language weights')
        field = 'episode' if bank == 'fresh' else 'id'; records = {r[field]: r for r in observed['episodes']}
        require(len(records) == len(observed['episodes']), 'input duplicate identity')
        return index_rows(value['points'], records, bank != 'fresh')
    for law in LAWS:
        for seed in SEEDS:
            for arm, bank in [*((a, 'fresh') for a in ARMS), *(('acquired', b + '_retention') for b in BANKS)]:
                totals['native' if bank == 'fresh' else 'language'] += len(trace(law, seed, arm, bank))
    audit.equal(dict(totals), {'native': config['planned_native_forecasts'], 'language': config['planned_language_retention_forecasts']}, 'planned forecast counts')
    require(audit.discrepancy_count == 0, 'artifact audit failed before evaluator read')
    if pre_score:
        require('torch' not in sys.modules and not any(name.endswith(('set_acquisition_scoring',
            'set_acquisition_retention_v2')) for name in sys.modules), 'auditor imported model/scorer')
        return {'version': 'set-acquisition-v2-pre-score-audit', 'decision': None, 'audit_passed': True,
            'check_count': audit.checks, 'discrepancy_count': 0, 'discrepancies': [],
            'scope': 'All actual checkpoint masks, bound source/data/trace hashes and runtime receipts; '
                'every native and language point inventory, header, geometry and normalization. '
                'Targets are not decoded or parsed; frozen evaluator files are hashed as opaque bytes. '
                'No score files are read and no acceptance conclusion is drawn.',
            'forecast_counts': dict(totals), 'evaluator_targets_parsed': False,
            'evaluator_bytes_hashed': True, 'score_files_read': False,
            'new_fits': 0, 'new_collections': 0, 'model_execution': False, 'original_scorer_execution': False,
            'scientific_admission': False, 'independent_custody': False,
            'source_publication': trained['source_publication'], 'weights_publication': manifest['weights_publication'],
            'auditor_sha256': h.sha(__file__), 'helper_sha256': h.sha(h.__file__)}
    scored_manifest, decision = h.read(scored / 'manifest.json'), h.read(scored / 'decision.json')
    audit.equal(scored_manifest['trace_manifest_sha256'], h.sha(traces / 'manifest.json'), 'score trace binding')
    audit.check(scored_manifest['runtime'] == freeze['runtime'], 'score runtime')
    audit.equal(set(scored_manifest['reports']), keys, 'score report inventory')
    checks, details = {}, {}
    for law in LAWS:
        inputs = native_inputs[law]; bundle = h.read(data / f'{law}-evaluator.json.xz')
        records = {e['episode']: e for e in inputs['episodes']}
        gold, information, metadata = [{e['episode']: e for e in bundle[k]['episodes']} if k != 'cases' else
            {e['episode']: e for e in bundle[k]} for k in ('oracle', 'information', 'cases')]
        require(records.keys() == gold.keys() == information.keys() == metadata.keys(), 'evaluator inventory')
        for kind in ('oracle', 'information'): audit.equal(bundle[kind]['input_sha256'], h.canonical(inputs), 'evaluator input binding')
        pairs = defaultdict(list)
        for identity, meta in metadata.items():
            if meta['pair_id'] is not None: pairs[meta['pair_id']].append(identity)
        require(all(len(ids) == 2 and {metadata[i]['direction'] for i in ids} == {0, 1} for ids in pairs.values()), 'paired coverage')
        for seed in SEEDS:
            key = f'{law}/{seed}'; print('Audit ' + key, flush=True)
            report_path = scored / f'report-{law}-{seed}.json.xz'
            audit.equal(h.sha(report_path), scored_manifest['reports'][key]['sha256'], 'score file hash/' + key)
            saved = h.read(report_path); measured, summaries = {}, {}
            for arm in ARMS:
                measured[arm] = measured_native(trace(law, seed, arm, 'fresh'), records, gold, information, metadata, audit)
                summaries[arm] = summarize(list(measured[arm].values()), pairs)
                audit.equal(saved['native']['reports'][arm], summaries[arm], 'native summary/' + key + '/' + arm)
                point_fields = ('episode', 'step', 'action_kind', 'answerable', 'correct', 'map_world', 'nll', 'brier',
                    'oracle_kl', 'oracle_total_variation', 'map_outside_support', 'known_unchanged_errors', 'set')
                audit.equal(saved['native']['points'][arm], [{k: p[k] for k in point_fields} for p in measured[arm].values()], 'native points/' + arm)
            comparisons = {arm: changes(measured['acquired'], measured[arm]) for arm in ('parent', 'no_change')}
            audit.equal(saved['native']['comparisons'], comparisons, 'native deltas/' + key)
            checks[key] = native_checks(summaries['acquired'], comparisons, config['analysis'])
            audit.check(saved['native']['checks'] == checks[key] and saved['native']['passed'] == all(checks[key].values()), 'exact native decisions/' + key)
            checks[key]['observed_training_fit'] = trained['reports'][key]['final_observed_train_nll'] <= config['analysis']['max_set_mean_nll']
            for bank in BANKS:
                full = bank + '_retention'; observed = language_inputs[law, bank]; oldbank = 'fresh' if bank == 'coordinate' else full
                archive = h.read(root / f'results/coordinate-v1/traces/trace-{law}-{seed}-coordinates-{oldbank}.json.xz')
                require(archive['input_sha256'] == h.canonical(observed), 'archive input')
                cases = {r['id']: r for r in observed['episodes']}
                before = index_rows(archive['points'], cases, True, True)
                result = retained(trace(law, seed, 'acquired', full), before, cases, config['analysis'])
                audit.equal(saved['retention'][full], result, 'full retention report/' + key + '/' + bank)
                audit.check(saved['retention'][full]['checks'] == result['checks'], 'exact retention decisions/' + key + '/' + bank)
                for name in ('max_logp_change', 'max_order_logp_change'):
                    audit.check(h.number(saved['retention'][full][name]) == result[name], 'exact retention maximum/' + name)
                checks[key].update({full + '/' + name: ok for name, ok in result['checks'].items()})
            details[key] = {'checks': checks[key], 'native': summaries['acquired']['all'],
                'set_changed': summaries['acquired']['set_by_changed'],
                'parent_repairs': len(comparisons['parent']['repairs']), 'parent_regressions': len(comparisons['parent']['regressions'])}
    expected = 'KEEP_NATIVE_SET_ACQUISITION' if all(all(v.values()) for v in checks.values()) else 'REVISE_NATIVE_SET_ACQUISITION'
    audit.check(decision['checks'] == checks and decision['decision'] == expected, 'exact full decision')
    audit.check(decision['execution_complete'] is True and decision['scientific_admission'] is False and decision['g3_complete'] is False, 'decision limits')
    audit.check(not any((p / 'failure.json').exists() for p in (fitted, traces, scored)), 'no interrupted stage')
    require('torch' not in sys.modules and not any(name.endswith(('set_acquisition_scoring', 'set_acquisition_retention_v2')) for name in sys.modules), 'auditor imported model/scorer')
    return {'version': 'set-acquisition-v2-saved-audit', 'decision': expected, 'audit_passed': audit.discrepancy_count == 0,
        'check_count': audit.checks, 'discrepancy_count': audit.discrepancy_count, 'discrepancies': audit.discrepancies,
        'scope': 'All acceptance checks and full native/retention point metrics, summaries and probability-change records. '
                 'Saved evaluator distributions used as targets; original simulator/oracle is not rerun. '
                 'Actual checkpoint masks, hashes and runtime receipts verified. Reported timing/CPU costs are not remeasured.',
        'forecast_counts': dict(totals), 'new_fits': 0, 'new_collections': 0, 'model_execution': False,
        'original_scorer_execution': False, 'original_oracle_execution': False, 'evaluator_targets_parsed': True,
        'scientific_admission': False, 'independent_custody': False,
        'auditor_sha256': h.sha(__file__), 'helper_sha256': h.sha(h.__file__), 'details': details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pre-score', action='store_true', help='Validate complete evidence using observed inputs only.')
    args = parser.parse_args(); repo = args.repo.resolve(); sys.path.insert(0, str(repo))
    global h
    h = importlib.import_module('experiments.predictive_nucleus.audit_bilingual_saved')
    report = audit_saved(repo, h.Audit(), args.pre_score)
    with args.output.open('x') as stream: json.dump(h.safe(report), stream, sort_keys=True, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({k: report[k] for k in ('decision', 'audit_passed', 'check_count', 'discrepancy_count')}), flush=True)
    return int(not report['audit_passed'])


if __name__ == '__main__': raise SystemExit(main())
