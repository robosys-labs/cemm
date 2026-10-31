#!/usr/bin/env python3
"""Stdlib-only verification of saved bilingual study artifacts; no model/scorer imports."""
import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import lzma
import math
from pathlib import Path
import struct
import subprocess
import time
import traceback

LAWS = ('nand', 'nor')
ARMS = ('grounded', 'parser', 'sequence', 'text_only', 'ungrounded', 'shuffled')
FIT_ARMS = ARMS[:-1]


def read(path):
    raw = Path(path).read_bytes()
    return json.loads(lzma.decompress(raw) if str(path).endswith('.xz') else raw)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def number(value):
    return {'positive_infinity': math.inf, 'negative_infinity': -math.inf}.get(value, value) if isinstance(value, str) else value


def safe(value):
    if isinstance(value, dict): return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [safe(v) for v in value]
    if type(value) is float and not math.isfinite(value):
        if math.isnan(value): raise ValueError('NaN in audit report')
        return 'positive_infinity' if value > 0 else 'negative_infinity'
    return value


class Audit:
    def __init__(self):
        self.checks, self.discrepancy_count, self.discrepancies = 0, 0, []

    def check(self, value, label):
        self.checks += 1
        if not value:
            self.discrepancy_count += 1
            if len(self.discrepancies) < 100: self.discrepancies.append(label)

    def equal(self, actual, expected, label):
        if isinstance(expected, dict):
            self.check(isinstance(actual, dict) and set(actual) == set(expected), label + '/keys')
            if isinstance(actual, dict):
                for key in expected:
                    if key in actual: self.equal(actual[key], expected[key], label + '/' + str(key))
        elif isinstance(expected, (list, tuple)):
            self.check(isinstance(actual, (list, tuple)) and len(actual) == len(expected), label + '/length')
            if isinstance(actual, (list, tuple)):
                for i, (a, b) in enumerate(zip(actual, expected)): self.equal(a, b, label + '/' + str(i))
        else:
            a, b = number(actual), number(expected)
            numeric = type(a) in (int, float) and type(b) in (int, float)
            self.check((a == b or math.isclose(a, b, rel_tol=1e-10, abs_tol=2e-12)) if numeric else a == b,
                       label + ': ' + repr(actual) + ' != ' + repr(expected))


def tensor_shape(value):
    if not isinstance(value, list): return [], [value]
    if not value: return [0], []
    children = [tensor_shape(item) for item in value]
    if len({tuple(shape) for shape, _ in children}) != 1: raise ValueError('ragged tensor')
    return [len(value), *children[0][0]], [scalar for _, values in children for scalar in values]


def fingerprint(state):
    digest, count = hashlib.sha256(), 0
    for name, entry in sorted(state.items()):
        if isinstance(entry, dict):
            dtype, shape, values = entry['dtype'], entry['shape'], entry['values']
        else:
            dtype = 'torch.float64'
            shape, values = tensor_shape(entry)
        if math.prod(shape) != len(values): raise ValueError('tensor shape mismatch')
        if not all(type(v) in (float, int) and math.isfinite(v) for v in values): raise ValueError('invalid tensor values')
        code = {'torch.float64': 'd', 'torch.int64': 'q'}[dtype]
        metadata = json.dumps([name, dtype, shape]).encode()
        raw = struct.pack('<' + code * len(values), *values)
        for part in (metadata, raw): digest.update(len(part).to_bytes(8, 'big')); digest.update(part)
        count += len(values)
    return digest.hexdigest(), count


def index(bits):
    return int(''.join(str(bit) for bit in bits), 2)


def transition(before, action, mode, law):
    after = before.copy()
    if action[0] == 1:
        after[action[1]] = action[3]
    else:
        source, target = action[1 + mode], action[2 - mode]
        truth_table = {'nand': (1, 1, 1, 0), 'nor': (1, 0, 0, 0)}[law]
        after[target] = truth_table[2 * before[source] + before[target]]
    return after


def verify_gold(audit, inputs, oracle, label):
    audit.equal(oracle['input_sha256'], canonical(inputs), label + '/input_digest')
    records = {r['id']: r for r in inputs['episodes']}
    gold = {r['id']: r for r in oracle['episodes']}
    audit.check(len(records) == len(inputs['episodes']) and len(gold) == len(oracle['episodes']) and records.keys() == gold.keys(), label + '/ids')
    groups = {kind: defaultdict(list) for kind in ('role', 'bilingual', 'synonym')}
    for identity, meta in gold.items():
        record, previous = records[identity], records[identity]['anchor'].copy()
        for event in record['context']:
            previous = transition(previous, event['action'], meta['mode'], meta['law'])
            audit.equal(event['reading'], previous, label + '/context/' + identity)
        for t, event in enumerate(record['utterances']):
            action = meta['actions'][t]
            mentions = [record['entities'].index(word) for word in event['text'].split() if word in record['entities']]
            order = meta['action_orders'][t]
            audit.equal(action, [0, mentions[order], mentions[1 - order], -1], label + '/order/' + identity)
            opposite = transition(previous, [0, action[2], action[1], -1], meta['mode'], meta['law'])
            previous = transition(previous, action, meta['mode'], meta['law'])
            audit.equal(meta['truth'][t], previous, label + '/truth/' + identity)
            audit.equal(meta['opposite_truth'][t], opposite, label + '/opposite/' + identity)
            audit.equal(event['reading'], previous, label + '/reading/' + identity)
        for kind in groups: groups[kind][meta[kind + '_pair_id']].append(identity)
    audit.check(all(len(members) == 2 for group in groups.values() for members in group.values()), label + '/complete_pairs')
    return records, gold, groups


def measure(audit, row, record, gold, label):
    logs = [number(v) for v in row['logp']]
    audit.check(len(logs) == 2 ** len(record['entities']) and all(type(v) in (float, int) and not math.isnan(v) and v != math.inf for v in logs), label + '/logs')
    top = max(logs)
    normalizer = top + math.log(sum(math.exp(v - top) for v in logs))
    audit.check(abs(normalizer) <= 1e-10, label + '/normalized')
    probabilities = [math.exp(v) for v in logs]
    predicted, truth, opposite = logs.index(top), index(gold['truth'][row['step']]), index(gold['opposite_truth'][row['step']])
    t = row['step']; previous = record['context'][-1]['reading'] if t == 0 else record['utterances'][t - 1]['reading']
    fixed = [i for i in range(len(previous)) if previous[i] == gold['truth'][t][i]]
    order = None if row['order_logp'] is None else [number(v) for v in row['order_logp']]
    if order is not None:
        audit.check(len(order) == 2 and abs(sum(math.exp(v) for v in order) - 1) <= 1e-10, label + '/order_normalized')
    return {'id': row['id'], 'step': t, 'correct': predicted == truth, 'map': predicted,
        'nll': -logs[truth], 'brier': sum((probability - int(i == truth)) ** 2 for i, probability in enumerate(probabilities)),
        'confidence': probabilities[predicted], 'true_probability': probabilities[truth],
        'critical': truth != opposite, 'wrong_probability': probabilities[opposite],
        'order_correct': None if order is None else order.index(max(order)) == gold['action_orders'][t],
        'unchanged_bits': len(fixed), 'unchanged_errors': sum(((predicted >> (len(previous) - i - 1)) & 1) != previous[i] for i in fixed),
        'probabilities': probabilities}


def metrics(points):
    count = len(points)
    average = lambda key: math.fsum(p[key] for p in points) / count
    bins = [[] for _ in range(10)]
    for p in points: bins[min(9, int(p['confidence'] * 10))].append(p)
    ece = sum(len(b) / count * abs(sum(p['correct'] for p in b) / len(b) - sum(p['confidence'] for p in b) / len(b)) for b in bins if b)
    critical = [p for p in points if p['critical']]
    ordered = [p for p in points if p['order_correct'] is not None]
    return {'planned': count, 'answered': count, 'correct': sum(p['correct'] for p in points),
        'accuracy': average('correct'), 'mean_nll': average('nll'), 'mean_brier': average('brier'),
        'ece_10': ece, 'ece_bin_counts': [len(b) for b in bins], 'order_planned': len(ordered),
        'order_correct': sum(p['order_correct'] for p in ordered), 'critical_planned': len(critical),
        'min_critical_true_probability': min((p['true_probability'] for p in critical), default=None),
        'max_wrong_order_probability': max((p['wrong_probability'] for p in critical), default=None),
        'unchanged_bits': sum(p['unchanged_bits'] for p in points), 'unchanged_bit_errors': sum(p['unchanged_errors'] for p in points)}


def summarize(points, records, gold, groups):
    episodes = defaultdict(list)
    for p in points.values(): episodes[p['id']].append(p)
    cell = lambda identity: gold[identity]['family'] + '/' + gold[identity]['language']
    role_records = [{'pair_id': pair, 'episodes': members,
        'correct': all(p['correct'] for member in members for p in episodes[member]), 'cell': cell(members[0])}
        for pair, members in sorted(groups['role'].items())]
    twins = {}
    for kind in ('bilingual', 'synonym'):
        pair_records = []
        for pair, (left, right) in sorted(groups[kind].items()):
            tv, same = [], []
            for t in range(len(episodes[left])):
                a, b = points[left, t], points[right, t]
                tv.append(sum(abs(x - y) for x, y in zip(a['probabilities'], b['probabilities'])) / 2)
                same.append(a['map'] == b['map'])
            pair_records.append({'pair_id': pair, 'steps': len(tv), 'max_tv': max(tv), 'all_maps_equal': all(same)})
        twins[kind] = {'planned_pairs': len(pair_records), 'forecast_pairs': sum(p['steps'] for p in pair_records),
            'map_consistent_pairs': sum(p['all_maps_equal'] for p in pair_records),
            'max_tv': max(p['max_tv'] for p in pair_records), 'records': pair_records}
    cells = {}
    for name in sorted({cell(identity) for identity in gold}):
        cells[name] = {**metrics([p for p in points.values() if cell(p['id']) == name]),
            'role_pairs_planned': sum(p['cell'] == name for p in role_records),
            'role_pairs_correct': sum(p['cell'] == name and p['correct'] for p in role_records)}
    return {'all': metrics(list(points.values())), 'by_family_language': cells,
        'by_entity_count': {str(n): metrics([p for p in points.values() if len(records[p['id']]['entities']) == n])
            for n in sorted({len(r['entities']) for r in records.values()})},
        'trajectories': {'planned': len(episodes), 'correct': sum(all(p['correct'] for p in group) for group in episodes.values())},
        'role_pairs': role_records, 'twins': twins,
        'wrong_ids': [[p['id'], p['step']] for p in points.values() if not p['correct']]}


def difference(a, b):
    return None if math.isinf(a) and math.isinf(b) else a - b


def main_audit(repo, data, fitted, results, audit):
    root = repo / 'experiments/predictive_nucleus'
    protocol = read(root / 'bilingual_protocol_v1.json')
    seeds, limits = protocol['model_seeds'], protocol['analysis']
    freeze, trained, report = read(data / 'freeze.json'), read(fitted / 'training.json'), read(results / 'summary.json.xz')
    manifest, decision = read(results / 'manifest.json'), read(results / 'decision.json')
    audit.equal(seeds, [7, 11, 23, 37, 53], 'five_seeds')
    audit.equal(freeze['protocol_sha256'], sha(root / 'bilingual_protocol_v1.json'), 'protocol_digest')
    for name, digest in freeze['sources'].items(): audit.equal(sha(root / name), digest, 'source/' + name)
    for name, item in freeze['artifacts'].items(): audit.equal(sha(data / name), item['sha256'], 'data/' + name)
    for name, item in manifest['artifacts'].items():
        audit.equal(sha(results / name), item['sha256'], 'result/' + name)
        audit.equal((results / name).stat().st_size, item['bytes'], 'result_size/' + name)
    audit.equal(decision, report['decision'], 'decision_copy')
    audit.check(manifest['execution_complete'] is True and manifest['world_checkpoints_unchanged'] is True, 'complete_manifest')
    audit.equal(report['bindings']['freeze_sha256'], sha(data / 'freeze.json'), 'summary_freeze')
    audit.equal(report['bindings']['sources'], freeze['sources'], 'summary_sources')
    audit.equal(report['bindings']['checkpoints'], freeze['checkpoints'], 'summary_world_inventory')
    audit.equal(report['bindings']['training_sha256'], sha(fitted / 'training.json'), 'summary_training')
    audit.equal(trained['freeze_sha256'], sha(data / 'freeze.json'), 'training_freeze')
    audit.check(trained['complete'] is True and trained['world_checkpoints_unchanged'] is True, 'training_complete')
    expected_fits = {f'{arm}/{seed}' for arm in FIT_ARMS for seed in seeds}
    audit.check(set(trained['reports']) == set(trained['checkpoints']) == expected_fits, '25_fit_inventory')
    parameters, updates = {}, 0
    for key in sorted(expected_fits):
        arm, seed = key.split('/'); item, details = trained['checkpoints'][key], trained['reports'][key]
        checkpoint = read(fitted / item['file'])
        audit.equal(sha(fitted / item['file']), item['sha256'], 'fit_bytes/' + key)
        actual, count = fingerprint(checkpoint['state']); parameters[key] = count
        audit.equal(actual, checkpoint['state_sha256'], 'fit_tensors/' + key)
        audit.equal(actual, details['final_sha256'], 'fit_report_tensors/' + key)
        audit.equal([checkpoint['arm'], checkpoint['seed']], [arm, int(seed)], 'fit_identity/' + key)
        audit.equal(count, details['parameters'], 'fit_parameter_count/' + key)
        audit.equal(count, 1048 if arm in ('sequence', 'text_only') else 474, 'fit_expected_parameters/' + key)
        audit.equal(details['updates'], 256, 'fit_updates/' + key)
        audit.equal(details['training_forecasts_per_update'], 384, 'fit_exposure/' + key)
        audit.check(details['cpu_seconds'] <= protocol['fit']['cpu_seconds_per_fit'], 'fit_cpu_ceiling/' + key)
        updates += details['updates']
    for seed in seeds:
        initials = lambda arms: {trained['reports'][f'{arm}/{seed}']['initial_sha256'] for arm in arms}
        audit.equal(len(initials(('grounded', 'parser', 'ungrounded'))), 1, 'matched_order_initialization/' + str(seed))
        audit.equal(len(initials(('sequence', 'text_only'))), 1, 'matched_sequence_initialization/' + str(seed))
    audit.equal(updates, 6400, 'total_updates')
    native_directory = root / 'data/multisource-law-fit-v1'
    for law in LAWS:
        audit.check(set(freeze['checkpoints'][law]) == {str(s) for s in seeds}, 'native_seed_inventory/' + law)
        for seed in seeds:
            item = freeze['checkpoints'][law][str(seed)]; path = native_directory / item['file']
            checkpoint = read(path); actual, count = fingerprint(checkpoint['state'])
            audit.equal(sha(path), item['sha256'], 'native_bytes/' + path.name)
            audit.equal(actual, item['state_sha256'], 'native_tensor_manifest/' + path.name)
            audit.equal(actual, checkpoint['state_sha256'], 'native_tensor_checkpoint/' + path.name)
            audit.equal(count, 562, 'native_parameters/' + path.name)
            for commit in (protocol['base_commit'], protocol['checkpoint_commit']):
                original = subprocess.check_output(['git', '-C', str(repo), 'show', commit + ':' + path.relative_to(repo).as_posix()])
                audit.check(original == path.read_bytes(), 'native_historical_bytes/' + commit[:8] + '/' + path.name)
    train_inputs = read(data / 'train-inputs.json.xz')
    train_records, train_gold, _ = verify_gold(audit, train_inputs, read(data / 'train-oracle.json.xz'), 'train')
    audit.equal(trained['training_input_sha256'], canonical(train_inputs), 'training_input_digest')
    audit.equal(sum(len(r['utterances']) for r in train_records.values()), 384, 'training_point_count')
    audit.equal(read(data / 'parser-labels.json'), {identity: meta['action_orders'] for identity, meta in train_gold.items()}, 'parser_labels')
    predicted_checks, computed, totals, resources, retention = {}, {}, defaultdict(int), [], {}
    expected_traces = {f'trace-{law}-{seed}-{arm}.json.xz' for law in LAWS for seed in seeds for arm in ARMS}
    audit.equal(set(manifest['artifacts']), expected_traces | {'attempt.json', 'summary.json.xz', 'decision.json'}, 'manifest_inventory')
    audit.equal(set(report['bindings']['trace_sha256']), expected_traces, 'summary_trace_inventory')
    audit.equal(set(report['by_trace']), {f'{law}/{seed}/{arm}' for law in LAWS for seed in seeds for arm in ARMS}, 'summary_score_inventory')
    audit.equal(set(report['native_reference']), {f'{law}/{seed}' for law in LAWS for seed in seeds}, 'summary_native_inventory')
    audit.equal(set(p.name for p in results.glob('trace-*.json.xz')), expected_traces, 'directory_trace_inventory')
    for law in LAWS:
        inputs = read(data / f'{law}-inputs.json.xz')
        records, gold, groups = verify_gold(audit, inputs, read(data / f'{law}-oracle.json.xz'), law)
        audit.equal(len(records), 576, law + '/episode_count')
        expected_ids = {(identity, t) for identity, record in records.items() for t in range(len(record['utterances']))}
        audit.equal(len(expected_ids), 2080, law + '/point_count')
        audit.check(not ({name for r in records.values() for name in r['entities']} & {name for r in train_records.values() for name in r['entities']}), law + '/disjoint_names')
        audit.check(not ({m['family'] for m in gold.values()} & {m['family'] for m in train_gold.values()}), law + '/disjoint_families')
        for seed in seeds:
            key, arms, shared_pack = f'{law}/{seed}', {}, None
            for arm in ARMS:
                identity = key + '/' + arm; name = f'trace-{law}-{seed}-{arm}.json.xz'
                trace = read(results / name)
                audit.equal(sha(results / name), report['bindings']['trace_sha256'][name], 'trace_hash/' + identity)
                for field, value in {'law': law, 'seed': seed, 'arm': arm, 'input_sha256': canonical(inputs),
                    'freeze_sha256': sha(data / 'freeze.json'), 'training_sha256': sha(fitted / 'training.json'),
                    'checkpoint_sha256': trained['checkpoints'][f'{"grounded" if arm == "shuffled" else arm}/{seed}']['sha256']}.items():
                    audit.equal(trace[field], value, 'trace_binding/' + identity + '/' + field)
                ids = [(r['id'], r['step']) for r in trace['points']]
                audit.check(len(ids) == len(set(ids)) == 2080 and set(ids) == expected_ids, 'trace_inventory/' + identity)
                points = {(r['id'], r['step']): measure(audit, r, records[r['id']], gold[r['id']], identity + '/' + r['id'] + '/' + str(r['step'])) for r in trace['points']}
                summary = summarize(points, records, gold, groups)
                audit.equal({k: v for k, v in report['by_trace'][identity].items() if k != 'resources'}, summary, 'metrics/' + identity)
                audit.equal(report['by_trace'][identity]['resources'], trace['resources'], 'resources_copy/' + identity)
                computed[identity], arms[arm] = summary, points
                totals['forecast_points'] += len(points); totals['traces'] += 1
                cost = trace['resources']; resources.append({'kind': 'forecast', 'law_seed': key, 'arm': arm, **cost})
                pack = cost['native_cache_and_tokenization']
                if arm == 'ungrounded': resources.append({'kind': 'preparation', 'law_seed': key, 'arm': arm, **pack})
                elif shared_pack is None:
                    shared_pack = pack; resources.append({'kind': 'preparation', 'law_seed': key, 'arm': 'shared', **pack})
                else: audit.equal(pack, shared_pack, 'shared_pack_cost/' + identity)
            reference = report['native_reference'][key]
            ids = [(r['id'], r['step']) for r in reference['points']]
            audit.check(len(ids) == len(set(ids)) == 2080 and set(ids) == expected_ids, 'native_reference_inventory/' + key)
            native = {(r['id'], r['step']): measure(audit, r, records[r['id']], gold[r['id']], 'native/' + key + '/' + r['id']) for r in reference['points']}
            audit.equal(reference['all'], metrics(list(native.values())), 'native_metrics/' + key)
            totals['native_reference_points'] += len(native)
            candidate = arms['grounded']; costs, regressions, repairs = {}, [], []
            for identity, point in native.items():
                now = candidate[identity]
                if point['correct'] and not now['correct']: regressions.append(identity)
                if not point['correct'] and now['correct']: repairs.append(identity)
                if now['nll'] > point['nll']: costs[identity] = now['nll'] - point['nll']
            saved = report['retention'][key]
            audit.equal(sorted(tuple(p) for p in saved['native_correct_now_wrong']), sorted(regressions), 'native_regressions/' + key)
            audit.equal(sorted(tuple(p) for p in saved['native_wrong_now_correct']), sorted(repairs), 'native_repairs/' + key)
            audit.equal(saved['nll_worse_count'], len(costs), 'native_nll_worse_count/' + key)
            audit.equal({(r['id'], r['step']): r['increase'] for r in saved['nll_worse']}, costs, 'native_nll_increases/' + key)
            audit.equal(saved['nll_better_count'], sum(candidate[i]['nll'] < native[i]['nll'] for i in native), 'native_nll_improvements/' + key)
            retention[key] = {'regressions': len(regressions), 'repairs': len(repairs), 'nll_worse': len(costs), 'max_nll_increase': max(costs.values(), default=0.)}
            primary, overall = computed[key + '/grounded'], computed[key + '/grounded']['all']
            comparison = {arm: {'grounded_minus_accuracy': overall['accuracy'] - computed[key + '/' + arm]['all']['accuracy'],
                'grounded_minus_nll': difference(overall['mean_nll'], computed[key + '/' + arm]['all']['mean_nll'])} for arm in ARMS if arm != 'grounded'}
            audit.equal(report['comparisons'][key], comparison, 'comparisons/' + key)
            cells = list(primary['by_family_language'].values())
            predicted_checks[key] = {'accuracy_each_cell': all(c['accuracy'] >= limits['min_accuracy'] for c in cells),
                'order_accuracy_each_cell': all(c['order_planned'] > 0 and c['order_correct'] / c['order_planned'] >= limits['min_accuracy'] for c in cells),
                'nll_each_cell': all(c['mean_nll'] <= limits['max_mean_nll'] for c in cells),
                'role_trajectories_each_cell': all(c['role_pairs_planned'] > 0 and c['role_pairs_correct'] / c['role_pairs_planned'] >= limits['min_accuracy'] for c in cells),
                'critical_true_probability': overall['critical_planned'] > 0 and overall['min_critical_true_probability'] >= limits['min_true_probability'],
                'critical_opposite_probability': overall['critical_planned'] > 0 and overall['max_wrong_order_probability'] <= limits['max_wrong_order_probability'],
                'twins': all(t['max_tv'] <= limits['max_twin_tv'] and t['map_consistent_pairs'] == t['planned_pairs'] for t in primary['twins'].values()),
                'native_retention': not regressions,
                'parser_gap': comparison['parser']['grounded_minus_accuracy'] >= -limits['max_parser_accuracy_gap'],
                'grounding_ablation_gain': all(comparison[arm]['grounded_minus_accuracy'] >= limits['min_ablation_accuracy_gain'] for arm in ('text_only', 'ungrounded')),
                'shuffle_gain': comparison['shuffled']['grounded_minus_accuracy'] >= limits['min_shuffle_accuracy_gain']}
    audit.equal(totals, {'forecast_points': 124800, 'traces': 60, 'native_reference_points': 20800}, 'complete_denominators')
    expected_decision = 'KEEP_BILINGUAL_GROUNDING' if all(all(row.values()) for row in predicted_checks.values()) else 'REVISE_BILINGUAL_GROUNDING'
    audit.equal(decision['decision'], expected_decision, 'decision_reconstruction')
    audit.equal(decision['checks'], predicted_checks, 'threshold_reconstruction')
    audit.check(decision['scientific_admission'] is False and decision['execution_complete'] is True, 'scientific_scope')
    cost_totals = {kind: {metric: sum(row[metric] for row in resources if row['kind'] == kind) for metric in ('cpu_seconds', 'wall_seconds')} for kind in ('forecast', 'preparation')}
    headlines = {law: {arm: {'correct': sum(computed[f'{law}/{seed}/{arm}']['all']['correct'] for seed in seeds),
        'planned': sum(computed[f'{law}/{seed}/{arm}']['all']['planned'] for seed in seeds),
        'worst_nll': max(computed[f'{law}/{seed}/{arm}']['all']['mean_nll'] for seed in seeds)} for arm in ARMS} for law in LAWS}
    return {'decision_reconstructed': expected_decision, 'counts': {**totals, 'new_fits': 25, 'updates': updates,
        'tensor_fingerprints': 35, 'source_bindings': len(freeze['sources']), 'data_artifacts': len(freeze['artifacts']),
        'result_artifacts': len(manifest['artifacts'])},
        'headlines': headlines, 'retention': retention, 'deduplicated_costs': cost_totals,
        'training_resources': trained['resources'], 'evaluator_resources': report['evaluator_resources'],
        'peak_recorded_rss_kib': max(row['peak_rss_kib'] for row in resources if row['kind'] == 'forecast'),
        'source_data_commit': read(fitted / 'attempt.json')['source_data_commit'],
        'weights_commit': read(results / 'attempt.json')['weights_commit'],
        'result_manifest_sha256': sha(results / 'manifest.json'), 'training_manifest_sha256': sha(fitted / 'training.json')}


def self_test():
    audit = Audit()
    record = {'entities': ['a', 'b', 'c'], 'context': [{'reading': [0, 0, 0]}], 'utterances': [{'reading': [1, 0, 0]}]}
    gold = {'truth': [[1, 0, 0]], 'opposite_truth': [[0, 1, 0]], 'action_orders': [0]}
    row = {'id': 'synthetic', 'step': 0, 'logp': [math.log(.99 if i == 4 else .01 / 7) for i in range(8)], 'order_logp': [math.log(.99), math.log(.01)]}
    result = metrics([measure(audit, row, record, gold, 'synthetic')])
    audit.equal(result['accuracy'], 1., 'synthetic_accuracy')
    audit.equal(result['mean_nll'], -math.log(.99), 'synthetic_nll')
    audit.equal(result['mean_brier'], .0001 + .0001 / 7, 'synthetic_brier')
    audit.equal(result['ece_10'], .01, 'synthetic_ece')
    a, count = fingerprint({'x': [[1., 2.]]})
    b, _ = fingerprint({'x': {'dtype': 'torch.float64', 'shape': [1, 2], 'values': [1., 2.]}})
    audit.equal(a, b, 'synthetic_tensor_serializations'); audit.equal(count, 2, 'synthetic_tensor_count')
    if audit.discrepancies: raise AssertionError(audit.discrepancies)
    print(json.dumps({'self_test': 'PASS', 'checks': audit.checks, 'models_executed': 0}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--self-test', action='store_true')
    args = parser.parse_args()
    if args.self_test: self_test(); return
    if args.output is None: parser.error('--output required')
    root = args.repo / 'experiments/predictive_nucleus'
    started, audit, result = time.perf_counter(), Audit(), {}
    try:
        result = main_audit(args.repo, root / 'data/bilingual-v1', root / 'data/bilingual-fit-v1', root / 'results/bilingual-v1', audit)
    except Exception as error:
        audit.check(False, type(error).__name__ + ': ' + str(error))
        result['exception'] = traceback.format_exc()
    result.update(version='bilingual-saved-artifact-audit-v1', recorded_at=datetime.now(timezone.utc).isoformat(),
        status='PASS' if audit.discrepancy_count == 0 else 'FAIL', checks=audit.checks,
        discrepancy_count=audit.discrepancy_count, discrepancies=audit.discrepancies,
        wall_seconds=time.perf_counter() - started, auditor_source_sha256=sha(Path(__file__)),
        auditor_python_lines=len(Path(__file__).read_text().splitlines()), models_executed=0, fitting_updates=0,
        scope='Independent implementation of saved-byte and arithmetic checks; same team, not independent scientific custody. No learner, collector or repository scorer executed.')
    args.output.write_text(json.dumps(safe(result), indent=2, sort_keys=True, allow_nan=False) + '\n')
    print(json.dumps({'status': result['status'], 'checks': audit.checks, 'discrepancies': audit.discrepancy_count, 'output': str(args.output)}))
    if audit.discrepancy_count: raise SystemExit(1)


if __name__ == '__main__': main()
