"""Frozen-denominator bilingual scoring; gold is opened after every trace validates.

The native action reference is evaluator-only. Trajectory conjunctions include
delivered intermediate feedback and are not open-loop rollout claims.
"""
from collections import defaultdict
import math

from . import acceptance_contract as contract, continuation_run as io
from .acceptance_scoring import _index, _safe
from .bilingual_contract import validate_inputs

LAWS = ('nand', 'nor')
ARMS = ('grounded', 'parser', 'sequence', 'text_only', 'ungrounded', 'shuffled')


def _difference(left, right):
    return None if math.isinf(left) and math.isinf(right) else left - right


def _logs(values, size):
    contract.require(type(values) is list and len(values) == size, 'forecast geometry differs')
    values = [-math.inf if value == 'negative_infinity' else value for value in values]
    contract.require(all(type(value) in (int, float) and not math.isnan(value) and
                         value != math.inf for value in values), 'invalid log forecast')
    maximum = max(values)
    contract.require(math.isfinite(maximum) and abs(maximum + math.log(math.fsum(
        math.exp(value - maximum) for value in values))) <= 1e-10, 'forecast not normalized')
    return values


def _inventory(inputs, oracle, law):
    records = {episode['id']: episode for episode in inputs['episodes']}
    contract.require(oracle['version'] == 'bilingual-oracle-v1' and
        oracle['input_sha256'] == contract.digest(inputs), 'oracle/input binding differs')
    gold = {episode['id']: episode for episode in oracle['episodes']}
    contract.require(len(gold) == len(oracle['episodes']) and gold.keys() == records.keys(),
                     'oracle episode inventory differs')
    pairs = {kind: defaultdict(list) for kind in ('role', 'bilingual', 'synonym')}
    for identity, meta in gold.items():
        record, steps = records[identity], len(records[identity]['utterances'])
        contract.require(meta['law'] == law and meta['language'] in ('svo', 'osv') and
            meta['direction'] in (0, 1) and meta['synonym'] in (0, 1) and all(
            len(meta[key]) == steps for key in ('actions', 'action_orders', 'truth', 'opposite_truth')),
            'oracle geometry or metadata differs')
        for t, event in enumerate(record['utterances']):
            mentions = [record['entities'].index(word) for word in event['text'].split()
                        if word in record['entities']]
            order = meta['action_orders'][t]
            contract.require(type(order) is int and order in (0, 1) and meta['actions'][t] ==
                [0, mentions[order], mentions[1 - order], -1], 'oracle order/action differs')
            contract.require(meta['truth'][t] == event['reading'] and all(
                type(bits) is list and len(bits) == len(record['entities']) and
                all(type(bit) is int and bit in (0, 1) for bit in bits)
                for bits in (meta['truth'][t], meta['opposite_truth'][t])), 'invalid complete truth')
        for kind in pairs: pairs[kind][meta[kind + '_pair_id']].append(identity)
    for kind, groups in pairs.items():
        for members in groups.values():
            contract.require(len(members) == 2, 'incomplete planned ' + kind + ' pair')
            a, b = [gold[identity] for identity in members]
            dimension = {'role': 'direction', 'bilingual': 'language', 'synonym': 'synonym'}[kind]
            values = {'svo', 'osv'} if kind == 'bilingual' else {0, 1}
            contract.require({a[dimension], b[dimension]} == values and
                all(a[key] == b[key] for key in ('family', 'lineage', 'mode')),
                'cross-stratum or duplicate ' + kind + ' pair')
            shared = ('entities', 'anchor', 'context')
            contract.require(all(records[members[0]][key] == records[members[1]][key] for key in shared),
                             'paired observed contexts differ')
            if kind == 'role':
                contract.require(a['language'] == b['language'] and a['synonym'] == b['synonym'] and
                    len(a['actions']) == len(b['actions']) and all(x == [0, y[2], y[1], -1]
                    for x, y in zip(a['actions'], b['actions'], strict=True)), 'role actions not reversed')
            else:
                contract.require(all(a[key] == b[key] for key in
                    ('physical_id', 'direction', 'actions', 'truth', 'opposite_truth')) and
                    a['synonym' if kind == 'bilingual' else 'language'] ==
                    b['synonym' if kind == 'bilingual' else 'language'], 'twins differ physically')
    return records, gold, pairs


def _point(row, record, meta):
    t, logs = row['step'], row['logp']
    truth, opposite = _index(meta['truth'][t]), _index(meta['opposite_truth'][t])
    probabilities = [math.exp(value) for value in logs]
    best = max(range(len(logs)), key=logs.__getitem__)  # First world wins exact ties.
    previous = record['context'][-1]['reading'] if t == 0 else record['utterances'][t - 1]['reading']
    unchanged = [i for i, bit in enumerate(previous) if bit == meta['truth'][t][i]]
    order = row['order_logp']
    return {'id': row['id'], 'step': t, 'correct': best == truth, 'map_world': best,
        'nll': -float(logs[truth]), 'brier': math.fsum((p - int(i == truth)) ** 2
            for i, p in enumerate(probabilities)), 'confidence': probabilities[best],
        'true_probability': probabilities[truth], 'critical': truth != opposite,
        'wrong_order_probability': probabilities[opposite] if truth != opposite else None,
        'order_correct': None if order is None else
            max(range(2), key=order.__getitem__) == meta['action_orders'][t],
        'unchanged_bits': len(unchanged), 'unchanged_bit_errors': sum(
            ((best >> (len(previous) - i - 1)) & 1) != meta['truth'][t][i] for i in unchanged)}


def _stats(points):
    contract.require(bool(points), 'empty scoring stratum')
    count = len(points)
    mean = lambda key: math.fsum(p[key] / count for p in points)
    bins = [[p for p in points if min(9, int(p['confidence'] * 10)) == i] for i in range(10)]
    critical, ordered = [p for p in points if p['critical']], [p for p in points if p['order_correct'] is not None]
    return {'planned': count, 'answered': count, 'correct': sum(p['correct'] for p in points),
        'accuracy': mean('correct'), 'mean_nll': mean('nll'), 'mean_brier': mean('brier'),
        'ece_10': math.fsum(abs(sum(p['correct'] for p in group) -
            math.fsum(p['confidence'] for p in group)) / count for group in bins),
        'ece_bin_counts': [len(group) for group in bins], 'order_planned': len(ordered),
        'order_correct': sum(p['order_correct'] for p in ordered), 'critical_planned': len(critical),
        'min_critical_true_probability': min((p['true_probability'] for p in critical), default=None),
        'max_wrong_order_probability': max((p['wrong_order_probability'] for p in critical), default=None),
        'unchanged_bits': sum(p['unchanged_bits'] for p in points),
        'unchanged_bit_errors': sum(p['unchanged_bit_errors'] for p in points)}


def _summary(rows, records, gold, pairs):
    points = [_point(row, records[row['id']], gold[row['id']]) for row in rows.values()]
    episodes = defaultdict(list)
    for point in points: episodes[point['id']].append(point)
    roles = [{'pair_id': identity, 'episodes': members, 'correct': all(
        p['correct'] for member in members for p in episodes[member]),
        'cell': gold[members[0]]['family'] + '/' + gold[members[0]]['language']}
        for identity, members in sorted(pairs['role'].items())]
    twins = {}
    for kind in ('bilingual', 'synonym'):
        values = []
        for identity, (left, right) in sorted(pairs[kind].items()):
            tvs, agrees = [], []
            for t in range(len(episodes[left])):
                a, b = [rows[key, t]['logp'] for key in (left, right)]
                tvs.append(math.fsum(abs(math.exp(x) - math.exp(y)) for x, y in zip(a, b, strict=True)) / 2)
                agrees.append(max(range(len(a)), key=a.__getitem__) == max(range(len(b)), key=b.__getitem__))
            values.append({'pair_id': identity, 'steps': len(tvs), 'max_tv': max(tvs), 'all_maps_equal': all(agrees)})
        twins[kind] = {'planned_pairs': len(values), 'forecast_pairs': sum(v['steps'] for v in values),
            'map_consistent_pairs': sum(v['all_maps_equal'] for v in values),
            'max_tv': max(v['max_tv'] for v in values), 'records': values}
    cells = sorted({meta['family'] + '/' + meta['language'] for meta in gold.values()})
    return {'all': _stats(points), 'by_family_language': {cell: {
        **_stats([p for p in points if gold[p['id']]['family'] + '/' + gold[p['id']]['language'] == cell]),
        'role_pairs_planned': sum(r['cell'] == cell for r in roles),
        'role_pairs_correct': sum(r['cell'] == cell and r['correct'] for r in roles)} for cell in cells},
        'by_entity_count': {str(n): _stats([p for p in points if len(records[p['id']]['entities']) == n])
            for n in sorted({len(r['entities']) for r in records.values()})},
        'trajectories': {'planned': len(episodes), 'correct': sum(all(p['correct'] for p in group) for group in episodes.values())},
        'role_pairs': roles, 'twins': twins,
        'wrong_ids': [[p['id'], p['step']] for p in points if not p['correct']]}, points


def _native(inputs, gold, inventory, law, seed):
    """Replay observed context and gold native actions only after candidate collection."""
    import torch
    from .bilingual_run import world_for
    from .joint_objective import fingerprint
    world, result, groups = world_for(inventory, law, seed), {}, defaultdict(list)
    before = fingerprint(world.state_dict())
    for record in inputs['episodes']:
        groups[len(record['entities']), len(record['utterances']), len(record['context'])].append(record)
    with torch.no_grad():
        for (_, steps, context_steps), records in groups.items():
            pre = torch.tensor([r['anchor'] for r in records], dtype=torch.float64)
            state = world.initial(len(records))
            for t in range(context_steps + steps):
                observed = t < context_steps
                actions = [r['context'][t]['action'] if observed else
                           gold[r['id']]['actions'][t - context_steps] for r in records]
                readings = [r['context'][t]['reading'] if observed else
                            r['utterances'][t - context_steps]['reading'] for r in records]
                raw, pending = world.predict(pre, torch.tensor(actions, dtype=torch.long), state)
                if not observed:
                    for j, record in enumerate(records):
                        key = record['id'], t - context_steps
                        result[key] = {'id': key[0], 'step': key[1],
                            'logp': _logs(raw[j].tolist(), 2 ** len(record['entities'])), 'order_logp': None}
                pre = torch.tensor(readings, dtype=torch.float64)
                state = world.receive(pending, pre)
    contract.require(fingerprint(world.state_dict()) == before, 'native reference changed world weights')
    return result


def evaluate(data, output, config, freeze):
    limits, seeds = config['analysis'], config['model_seeds']
    contract.require(bool(seeds) and len(set(seeds)) == len(seeds), 'invalid model seed inventory')
    contract.require(io._read(data / 'freeze.json') == freeze, 'freeze manifest differs')
    for name, digest in freeze['sources'].items():
        contract.require(io._hash(io.ROOT / name) == digest, 'frozen scorer source differs: ' + name)
    def bound_read(name):
        contract.require(io._hash(data / name) == freeze['artifacts'][name]['sha256'], 'data bytes differ: ' + name)
        return io._read(data / name)
    inputs = {law: validate_inputs(bound_read(law + '-inputs.json.xz')) for law in LAWS}
    traces, trace_hashes, checkpoint_hashes, training_hashes = {}, {}, {}, set()
    for law in LAWS:
        records = {r['id']: r for r in inputs[law]['episodes']}
        expected = {(r['id'], t) for r in records.values() for t in range(len(r['utterances']))}
        for seed in seeds:
            for arm in ARMS:
                name = f'trace-{law}-{seed}-{arm}.json.xz'
                trace_hashes[name] = io._hash(output / name)
                trace = io._read(output / name)
                contract.require((trace['law'], trace['seed'], trace['arm']) == (law, seed, arm) and
                    trace['input_sha256'] == contract.digest(inputs[law]) and
                    trace['freeze_sha256'] == io._hash(data / 'freeze.json'), 'trace identity/input binding differs')
                fit_key = seed, 'grounded' if arm == 'shuffled' else arm
                contract.require(all(type(trace[key]) is str and len(trace[key]) == 64 and
                    set(trace[key]) <= set('0123456789abcdef') for key in ('checkpoint_sha256', 'training_sha256')),
                    'invalid checkpoint/training digest')
                contract.require(checkpoint_hashes.setdefault(fit_key, trace['checkpoint_sha256']) ==
                    trace['checkpoint_sha256'], 'cross-law or shuffle checkpoint binding differs')
                training_hashes.add(trace['training_sha256']); indexed = {}
                for row in trace['points']:
                    contract.fields(row, ('id', 'step', 'logp', 'order_logp'))
                    key = row['id'], row['step']
                    contract.require(type(row['step']) is int and key in expected and key not in indexed,
                                     'unexpected or duplicate forecast identity')
                    row['logp'] = _logs(row['logp'], 2 ** len(records[row['id']]['entities']))
                    if arm in ('sequence', 'text_only'):
                        contract.require(row['order_logp'] is None, 'unexpected control order forecast')
                    else: row['order_logp'] = _logs(row['order_logp'], 2)
                    indexed[key] = row
                contract.require(indexed.keys() == expected, 'missing planned forecasts')
                traces[law, seed, arm] = indexed, trace['resources']
    contract.require(len(training_hashes) == 1, 'traces mix training manifests')
    # Every planned trace exists and validates before any evaluator target is opened.
    banks = {law: _inventory(inputs[law], bound_read(law + '-oracle.json.xz'), law) for law in LAWS}
    by_trace, references, retention, comparisons, checks = {}, {}, {}, {}, {}
    for law in LAWS:
        records, gold, pairs = banks[law]
        for seed in seeds:
            key, scored = f'{law}/{seed}', {}
            for arm in ARMS:
                rows, resources = traces[law, seed, arm]
                summary, points = _summary(rows, records, gold, pairs)
                by_trace[key + '/' + arm] = {**summary, 'resources': resources}
                scored[arm] = {(p['id'], p['step']): p for p in points}
            native = _native(inputs[law], gold, freeze['checkpoints'], law, seed)
            contract.require(native.keys() == traces[law, seed, 'grounded'][0].keys(), 'native reference inventory differs')
            native_points = {identity: _point(row, records[row['id']], gold[row['id']]) for identity, row in native.items()}
            references[key] = {'points': list(native.values()), 'all': _stats(list(native_points.values()))}
            candidate = scored['grounded']; losses = []
            for identity, prior in native_points.items():
                current = candidate[identity]
                if current['nll'] > prior['nll']:
                    losses.append({'id': identity[0], 'step': identity[1], 'increase': current['nll'] - prior['nll']})
            retention[key] = {'native_correct_now_wrong': [list(i) for i in candidate if native_points[i]['correct'] and not candidate[i]['correct']],
                'native_wrong_now_correct': [list(i) for i in candidate if not native_points[i]['correct'] and candidate[i]['correct']],
                'nll_worse_count': len(losses), 'nll_worse': losses,
                'nll_better_count': sum(candidate[i]['nll'] < native_points[i]['nll'] for i in candidate)}
            primary = by_trace[key + '/grounded']; overall = primary['all']
            comparisons[key] = {arm: {'grounded_minus_accuracy': overall['accuracy'] - by_trace[key + '/' + arm]['all']['accuracy'],
                'grounded_minus_nll': _difference(overall['mean_nll'], by_trace[key + '/' + arm]['all']['mean_nll'])}
                for arm in ARMS if arm != 'grounded'}
            checks[key] = {
                'accuracy_each_cell': all(v['accuracy'] >= limits['min_accuracy'] for v in primary['by_family_language'].values()),
                'order_accuracy_each_cell': all(v['order_planned'] > 0 and v['order_correct'] >=
                    limits['min_accuracy'] * v['order_planned'] for v in primary['by_family_language'].values()),
                'nll_each_cell': all(v['mean_nll'] <= limits['max_mean_nll'] for v in primary['by_family_language'].values()),
                'role_trajectories_each_cell': all(v['role_pairs_planned'] > 0 and v['role_pairs_correct'] >=
                    limits['min_accuracy'] * v['role_pairs_planned'] for v in primary['by_family_language'].values()),
                'critical_true_probability': overall['critical_planned'] > 0 and overall['min_critical_true_probability'] >= limits['min_true_probability'],
                'critical_opposite_probability': overall['critical_planned'] > 0 and overall['max_wrong_order_probability'] <= limits['max_wrong_order_probability'],
                'twins': all(v['max_tv'] <= limits['max_twin_tv'] and v['map_consistent_pairs'] == v['planned_pairs'] for v in primary['twins'].values()),
                'native_retention': not retention[key]['native_correct_now_wrong'],
                'parser_gap': comparisons[key]['parser']['grounded_minus_accuracy'] >= -limits['max_parser_accuracy_gap'],
                'grounding_ablation_gain': all(comparisons[key][arm]['grounded_minus_accuracy'] >= limits['min_ablation_accuracy_gain'] for arm in ('text_only', 'ungrounded')),
                'shuffle_gain': comparisons[key]['shuffled']['grounded_minus_accuracy'] >= limits['min_shuffle_accuracy_gain']}
    passed = all(all(values.values()) for values in checks.values())
    return _safe({'version': config['version'], 'by_trace': by_trace, 'native_reference': references,
        'retention': retention, 'comparisons': comparisons,
        'bindings': {'freeze_sha256': io._hash(data / 'freeze.json'), 'sources': freeze['sources'],
            'checkpoints': freeze['checkpoints'], 'trace_sha256': trace_hashes,
            'training_sha256': next(iter(training_hashes))},
        'decision': {'decision': 'KEEP_BILINGUAL_GROUNDING' if passed else 'REVISE_BILINGUAL_GROUNDING',
            'execution_complete': True, 'checks': checks, 'scientific_admission': False,
            'scope': 'Bounded full-feedback bilingual comprehension with a supplied two-order contact interface; no language generation or clarification result.',
            'control_limit': 'Sequence control is matched on current language-fit budget, not lifetime compute. Its 64-output head trains only 16 coordinates at 3–4 entities; 5–6 entities expose untrained rows. No architecture-superiority claim.'}})
