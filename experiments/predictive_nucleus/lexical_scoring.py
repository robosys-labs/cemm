"""Saved lexical contrasts and retention; oracle access follows trace validation."""
from collections import defaultdict
import math

from . import acceptance_contract as base, bilingual_scoring as previous, continuation_run as io
from .bilingual_contract import validate_inputs

VIEWS = ('masked', 'swapped', 'cross_order')
ARMS = ('grounded', 'prior', *VIEWS, 'retention')


def lexical_pairs(records, gold):
    pairs = defaultdict(list)
    for identity, meta in gold.items():
        record = records[identity]
        base.require(type(meta['contrast_step']) is int and meta['contrast_step'] == len(record['utterances']) - 1 and
            type(meta['effect_polarity']) is int and meta['effect_polarity'] in (0, 1) and
            type(meta['contrast_synonym']) is int and meta['contrast_synonym'] in (0, 1), 'invalid lexical metadata')
        words = record['utterances'][-1]['text'].split()
        prefix = {**{key: record[key] for key in ('entities', 'anchor', 'context')},
            'utterances': record['utterances'][:-1],
            'contrast_tokens': [word if word in record['entities'] else '<lexeme>' for word in words]}
        base.require(base.digest(prefix) == meta['shared_prefix_sha256'], 'lexical prefix binding differs')
        pairs[meta['lexical_pair_id']].append(identity)
    for members in pairs.values():
        base.require(len(members) == 2, 'incomplete lexical pair')
        a, b = (gold[identity] for identity in members)
        left, right = (records[identity]['utterances'][-1]['text'].split() for identity in members)
        changed = [i for i, (x, y) in enumerate(zip(left, right, strict=True)) if x != y]
        base.require(len(changed) == 1 and left[changed[0]] not in records[a['id']]['entities'] and
            right[changed[0]] not in records[b['id']]['entities'] and
            a['actions'][-1] == [0, b['actions'][-1][2], b['actions'][-1][1], -1],
            'lexical pair must change exactly one relation word and reverse the directed contact')
        base.require({a['effect_polarity'], b['effect_polarity']} == {0, 1} and
            a['counterpart_id'] == b['id'] and b['counterpart_id'] == a['id'] and
            all(a[key] == b[key] for key in ('family', 'language', 'mode', 'direction', 'synonym',
                'contrast_synonym', 'contrast_step', 'shared_prefix_sha256')) and
            a['truth'][-1] != b['truth'][-1] and a['truth'][-1] == b['opposite_truth'][-1] and
            b['truth'][-1] == a['opposite_truth'][-1], 'lexical twins are not one-word counterfactuals')
    return dict(pairs)


def trace_rows(trace, inputs, *, law, seed, arm, checkpoint, training, freeze):
    records = {r['id']: r for r in inputs['episodes']}
    expected = {(r['id'], t) for r in records.values() for t in
        ([len(r['utterances']) - 1] if arm in VIEWS else range(len(r['utterances'])))}
    base.require((trace['law'], trace['seed'], trace['arm']) == (law, seed, arm) and
        trace['input_sha256'] == base.digest(inputs) and trace['checkpoint_sha256'] == checkpoint and
        trace['training_sha256'] == training and trace['freeze_sha256'] == freeze, 'trace provenance differs')
    indexed = {}
    for row in trace['points']:
        base.fields(row, ('id', 'step', 'logp', 'order_logp'))
        key = row['id'], row['step']
        base.require(type(row['step']) is int and key in expected and key not in indexed, 'duplicate/unplanned forecast')
        indexed[key] = {**row, 'logp': previous._logs(row['logp'], 2 ** len(records[row['id']]['entities'])),
            'order_logp': previous._logs(row['order_logp'], 2)}
    base.require(indexed.keys() == expected, 'missing planned forecasts')
    return indexed


def points(rows, records, gold):
    return {key: previous._point(row, records[key[0]], gold[key[0]]) for key, row in rows.items()}


def probe_summary(measured, gold, pairs, synonym=None):
    selected = {identity: measured[identity, meta['contrast_step']] for identity, meta in gold.items()
        if synonym is None or meta['contrast_synonym'] == synonym}
    cell = lambda identity: gold[identity]['family'] + '/' + gold[identity]['language']
    groups = defaultdict(list)
    for identity, point in selected.items(): groups[cell(identity) + '/' + str(gold[identity]['effect_polarity'])].append(point)
    conjunctions = []
    for pair, members in sorted(pairs.items()):
        if members[0] not in selected: continue
        values = [selected[identity] for identity in members]
        base.require(all(value['critical'] for value in values), 'lexical pair lacks distinct consequences')
        conjunctions.append({'pair_id': pair, 'episodes': members, 'cell': cell(members[0]),
            'correct': all(value['correct'] for value in values),
            'minimum_gap': min(value['true_probability'] - value['wrong_order_probability'] for value in values)})
    return {'all': previous._stats(list(selected.values())),
        'by_family_language_polarity': {key: previous._stats(group) for key, group in sorted(groups.items())},
        'pairs': {'planned': len(conjunctions), 'correct': sum(p['correct'] for p in conjunctions),
            'minimum_gap': min(p['minimum_gap'] for p in conjunctions), 'records': conjunctions},
        'wrong_ids': [[p['id'], p['step']] for p in selected.values() if not p['correct']]}


def comparison(current, reference):
    base.require(current.keys() == reference.keys(), 'comparison inventory differs')
    worse = [{'id': key[0], 'step': key[1], 'increase': current[key]['nll'] - old['nll']}
        for key, old in reference.items() if current[key]['nll'] > old['nll']]
    better = [{'id': key[0], 'step': key[1], 'decrease': old['nll'] - current[key]['nll']}
        for key, old in reference.items() if current[key]['nll'] < old['nll']]
    deltas = [previous._difference(current[key]['nll'], old['nll']) for key, old in reference.items()]
    return {'planned': len(current),
        'regressions': [list(key) for key, old in reference.items() if old['correct'] and not current[key]['correct']],
        'repairs': [list(key) for key, old in reference.items() if not old['correct'] and current[key]['correct']],
        'nll_worse_count': len(worse), 'nll_worse': worse,
        'nll_better_count': len(better), 'nll_better': better,
        'nll_equal_count': sum(current[key]['nll'] == old['nll'] for key, old in reference.items()),
        'maximum_nll_increase': max((row['increase'] for row in worse), default=0.),
        'mean_nll_delta': math.fsum(deltas) / len(deltas) if all(value is not None and math.isfinite(value) for value in deltas) else None}


def _tv(a, b):
    return math.fsum(abs(math.exp(x) - math.exp(y)) for x, y in zip(a['logp'], b['logp'], strict=True)) / 2


def control_summary(rows, measured, gold, pairs):
    values = []
    for pair, (left, right) in sorted(pairs.items()):
        a, b = [(identity, gold[identity]['contrast_step']) for identity in (left, right)]
        swapped = [(rows['swapped'][a], gold[right]['truth'][-1]), (rows['swapped'][b], gold[left]['truth'][-1])]
        values.append({'pair_id': pair, 'masked_tv': _tv(rows['masked'][a], rows['masked'][b]),
            'masked_both_correct': measured['masked'][a]['correct'] and measured['masked'][b]['correct'],
            'swapped_counterpart_tv': max(_tv(rows['swapped'][a], rows['grounded'][b]),
                _tv(rows['swapped'][b], rows['grounded'][a])),
            'swapped_counterpart_probability': min(math.exp(row['logp'][previous._index(truth)]) for row, truth in swapped),
            'swapped_counterparts_correct': sum(max(range(len(row['logp'])), key=row['logp'].__getitem__) ==
                previous._index(truth) for row, truth in swapped)})
    return {'planned_pairs': len(values), 'masked_max_tv': max(v['masked_tv'] for v in values),
        'masked_both_correct': sum(v['masked_both_correct'] for v in values),
        'swapped_max_counterpart_tv': max(v['swapped_counterpart_tv'] for v in values),
        'swapped_min_counterpart_probability': min(v['swapped_counterpart_probability'] for v in values),
        'swapped_counterparts_correct': sum(v['swapped_counterparts_correct'] for v in values), 'records': values}


def probe_checks(summary, limits):
    cells, all_points = summary['by_family_language_polarity'].values(), summary['all']
    pairs = summary['pairs']['records']; paired = defaultdict(list)
    for pair in pairs: paired[pair['cell']].append(pair)
    return {'cells': all(v['accuracy'] >= limits['min_accuracy'] and v['mean_nll'] <= limits['max_mean_nll'] and
        v['order_correct'] >= limits['min_accuracy'] * v['order_planned'] for v in cells),
        'probabilities': all_points['min_critical_true_probability'] >= limits['min_true_probability'] and
            all_points['max_wrong_order_probability'] <= limits['max_wrong_order_probability'],
        'pairs': all(sum(v['correct'] for v in group) >= limits['min_accuracy'] * len(group) for group in paired.values()),
        'gap': summary['pairs']['minimum_gap'] >= limits['min_lexical_probability_gap']}


def evaluate(data, output, config, freeze, fitted):
    limits, seeds = config['analysis'], config['model_seeds']
    freeze_sha, training_sha = io._hash(data / 'freeze.json'), io._hash(fitted / 'training.json')
    base.require(io._read(data / 'freeze.json') == freeze and len(seeds) == len(set(seeds)) > 0, 'invalid freeze/seeds')
    for name, digest in {**freeze['sources'], **freeze['historical_artifacts']}.items():
        base.require(io._hash(io.ROOT / name) == digest, 'frozen source/history differs: ' + name)
    def bound_read(name):
        base.require(io._hash(data / name) == freeze['artifacts'][name]['sha256'], 'data artifact differs: ' + name)
        return io._read(data / name)
    training = io._read(fitted / 'training.json')
    expected_fits = {f'grounded/{seed}' for seed in seeds}
    base.require(training['version'] == config['version'] and training['complete'] is True and training['world_checkpoints_unchanged'] is True and
        training['freeze_sha256'] == freeze_sha and set(training['checkpoints']) == set(training['reports']) == expected_fits,
        'training inventory differs')
    base.require(training['training_input_sha256'] == base.digest(bound_read('train-inputs.json.xz')),
                 'training input binding differs')
    for seed in seeds:
        item, report = (training[key][f'grounded/{seed}'] for key in ('checkpoints', 'reports'))
        base.require(item['file'] == f'grounded-{seed}.json' and io._hash(fitted / item['file']) == item['sha256'] and
            report['parameters'] == 474 and report['updates'] == config['fit']['updates'] and
            report['training_forecasts_per_update'] == config['fit']['training_forecasts_per_update'] and
            report['parent_sha256'] == freeze['language_checkpoints'][str(seed)]['sha256'] and
            report['final_sha256'] == item['state_sha256'] and
            report['initial_sha256'] == freeze['language_checkpoints'][str(seed)]['state_sha256'], 'fitted checkpoint/exposure differs')
    laws = previous.LAWS
    inputs = {law: validate_inputs(bound_read(law + '-inputs.json.xz')) for law in laws}
    retained = {law: validate_inputs(io._read(io.ROOT / f'data/bilingual-v1/{law}-inputs.json.xz')) for law in laws}
    rows, resources, trace_hashes, archived = {}, {}, {}, {}
    for law in laws:
        for seed in seeds:
            parent = freeze['language_checkpoints'][str(seed)]['sha256']
            current = training['checkpoints'][f'grounded/{seed}']['sha256']
            for arm in ARMS:
                name = f'trace-{law}-{seed}-{arm}.json.xz'; trace_hashes[name] = io._hash(output / name)
                trace = io._read(output / name)
                rows[law, seed, arm] = trace_rows(trace, retained[law] if arm == 'retention' else inputs[law],
                    law=law, seed=seed, arm=arm, checkpoint=parent if arm == 'prior' else current,
                    training=training_sha, freeze=freeze_sha)
                resources[law, seed, arm] = trace['resources']
            historical = io._read(io.ROOT / f'results/bilingual-v1/trace-{law}-{seed}-grounded.json.xz')
            archived[law, seed] = trace_rows(historical, retained[law], law=law, seed=seed, arm='grounded',
                checkpoint=parent, training=config['parent_language_training_sha256'], freeze=config['old_data_freeze_sha256'])
    # Every complete and final-only trace is validated before any oracle is decoded.
    banks = {law: previous._inventory(inputs[law], bound_read(law + '-oracle.json.xz'), law) for law in laws}
    old_banks = {law: previous._inventory(retained[law], io._read(io.ROOT / f'data/bilingual-v1/{law}-oracle.json.xz'), law) for law in laws}
    summaries, probes, controls, transfers, comparisons, references, checks, structural = {}, {}, {}, {}, {}, {}, {}, {}
    for law in laws:
        records, gold, pairs = banks[law]; lexical = lexical_pairs(records, gold)
        old_records, old_gold, old_pairs = old_banks[law]
        for seed in seeds:
            key = f'{law}/{seed}'; current_rows = {arm: rows[law, seed, arm] for arm in ARMS}
            measured = {arm: points(current_rows[arm], records, gold) for arm in ARMS if arm != 'retention'}
            for arm in ('grounded', 'prior', 'retention'):
                r, g, p = (old_records, old_gold, old_pairs) if arm == 'retention' else (records, gold, pairs)
                summaries[key + '/' + arm] = {**previous._summary(current_rows[arm], r, g, p)[0],
                    'resources': resources[law, seed, arm]}
            for arm in ('grounded', 'prior', *VIEWS):
                probes[key + '/' + arm] = probe_summary(measured[arm], gold, lexical)
            control = control_summary(current_rows, measured, gold, lexical); controls[key] = control
            transfer = {label: probe_summary(measured['cross_order'], gold, lexical, synonym=index)
                for label, index in (('seen', 0), ('held_out', 1))}; transfers[key] = transfer
            structural[key] = {label: probe_checks(value, limits) for label, value in transfer.items()}
            native = previous._native(inputs[law], gold, freeze['checkpoints'], law, seed)
            native_points = points(native, records, gold)
            references[key] = {'points': list(native.values()), 'all': previous._stats(list(native_points.values()))}
            retention_points = points(current_rows['retention'], old_records, old_gold)
            comparisons[key] = {'native': comparison(measured['grounded'], native_points),
                'parent_fresh': comparison(measured['grounded'], measured['prior']),
                'parent_retention': comparison(retention_points, points(archived[law, seed], old_records, old_gold))}
            full, probe = summaries[key + '/grounded'], probes[key + '/grounded']
            cells = full['by_family_language'].values()
            checks[key] = {'canonical_cells': all(v['accuracy'] >= limits['min_accuracy'] and
                    v['mean_nll'] <= limits['max_mean_nll'] and v['order_correct'] >= limits['min_accuracy'] * v['order_planned']
                    for v in cells),
                'role_trajectories': all(v['role_pairs_correct'] >= limits['min_accuracy'] * v['role_pairs_planned'] for v in cells),
                'canonical_probabilities': full['all']['min_critical_true_probability'] >= limits['min_true_probability'] and
                    full['all']['max_wrong_order_probability'] <= limits['max_wrong_order_probability'],
                'canonical_twins': all(v['max_tv'] <= limits['max_twin_tv'] and v['map_consistent_pairs'] == v['planned_pairs'] for v in full['twins'].values()),
                **{'lexical_' + name: passed for name, passed in probe_checks(probe, limits).items()},
                'mask_information_removed': control['masked_max_tv'] <= limits['max_control_tv'] and
                    control['masked_both_correct'] == 0 and probes[key + '/masked']['all']['accuracy'] <= .5,
                'swapped_counterfactual': control['swapped_max_counterpart_tv'] <= limits['max_control_tv'] and
                    control['swapped_min_counterpart_probability'] >= limits['min_true_probability'],
                'gain_over_parent': probe['all']['accuracy'] - probes[key + '/prior']['all']['accuracy'] >= limits['min_prior_probe_accuracy_gain'],
                'native_retention': not comparisons[key]['native']['regressions'],
                'old_exact_retention': not comparisons[key]['parent_retention']['regressions']}
    passed = all(all(values.values()) for values in checks.values())
    transfer_pass = all(all(all(values.values()) for values in strata.values()) for strata in structural.values())
    return previous._safe({'version': config['version'], 'by_trace': summaries, 'probes': probes,
        'controls': controls, 'structural_transfer': transfers, 'comparisons': comparisons, 'native_reference': references,
        'bindings': {'freeze_sha256': freeze_sha, 'sources': freeze['sources'], 'checkpoints': freeze['checkpoints'],
            'language_checkpoints': freeze['language_checkpoints'], 'historical_artifacts': freeze['historical_artifacts'],
            'training_sha256': training_sha, 'trace_sha256': trace_hashes},
        'view_resources': {f'{law}/{seed}/{arm}': value for (law, seed, arm), value in resources.items() if arm in VIEWS},
        'decision': {'decision': 'KEEP_LEXICAL_GROUNDING' if passed else 'REVISE_LEXICAL_GROUNDING',
            'structural_transfer': 'STRUCTURAL_TRANSFER_ESTABLISHED' if transfer_pass else 'STRUCTURAL_TRANSFER_NOT_ESTABLISHED',
            'execution_complete': True, 'checks': checks, 'structural_checks': structural, 'scientific_admission': False,
            'scope': 'Outcome-learned lexical selection of supplied directed contact alternatives; word-by-layout recombination reported separately. No new action-kind, general-language or clarification result.'}})
