#!/usr/bin/env python3
"""Audit saved lexical artifacts with stdlib arithmetic; never replay a model.

Reuse only the independent bilingual artifact auditor. Its metric calculations
do not import the study scorer, runner, generator, or learner.
"""
import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import sys
import time
import traceback

h = None
LAWS, VIEWS = ('nand', 'nor'), ('masked', 'swapped', 'cross_order')
ARMS = ('grounded', 'prior', *VIEWS, 'retention')
WORD_PAIRS = (('contacts', 'receives'), ('touches', 'accepts'), ('dax', 'vok'), ('mip', 'nuz'))
WORDS = {word: (i % 2, polarity) for i, pair in enumerate(WORD_PAIRS) for polarity, word in enumerate(pair)}
BORROW = dict(zip(sum(WORD_PAIRS, ()), sum(WORD_PAIRS[2:] + WORD_PAIRS[:2], ())))


def probe(points, gold, pairs, synonym=None):
    chosen = {i: points[i, g['contrast_step']] for i, g in gold.items() if synonym is None or g['contrast_synonym'] == synonym}
    cell = lambda i: gold[i]['family'] + '/' + gold[i]['language']
    groups, conjunctions = defaultdict(list), []
    for i, p in chosen.items(): groups[cell(i) + '/' + str(gold[i]['effect_polarity'])].append(p)
    for pair, members in sorted(pairs.items()):
        if members[0] in chosen:
            values = [chosen[i] for i in members]
            conjunctions.append({'pair_id': pair, 'episodes': members, 'cell': cell(members[0]),
                'correct': all(p['correct'] for p in values),
                'minimum_gap': min(p['true_probability'] - p['wrong_probability'] for p in values)})
    return {'all': h.metrics(list(chosen.values())),
        'by_family_language_polarity': {k: h.metrics(v) for k, v in sorted(groups.items())},
        'pairs': {'planned': len(conjunctions), 'correct': sum(p['correct'] for p in conjunctions),
            'minimum_gap': min(p['minimum_gap'] for p in conjunctions), 'records': conjunctions},
        'wrong_ids': [[p['id'], p['step']] for p in chosen.values() if not p['correct']]}


def compare(current, prior):
    worse, better, regressions, repairs, deltas = [], [], [], [], []
    if current.keys() != prior.keys(): raise ValueError('comparison denominator differs')
    for key, old in prior.items():
        new = current[key]; delta = h.difference(new['nll'], old['nll']); deltas.append(delta)
        if new['nll'] > old['nll']: worse.append({'id': key[0], 'step': key[1], 'increase': delta})
        if new['nll'] < old['nll']: better.append({'id': key[0], 'step': key[1], 'decrease': -delta})
        if old['correct'] and not new['correct']: regressions.append(list(key))
        if new['correct'] and not old['correct']: repairs.append(list(key))
    return {'planned': len(current), 'regressions': regressions, 'repairs': repairs,
        'nll_worse_count': len(worse), 'nll_worse': worse, 'nll_better_count': len(better), 'nll_better': better,
        'nll_equal_count': sum(current[k]['nll'] == v['nll'] for k, v in prior.items()),
        'maximum_nll_increase': max((v['increase'] for v in worse), default=0.),
        'mean_nll_delta': math.fsum(deltas) / len(deltas) if all(d is not None and math.isfinite(d) for d in deltas) else None}


def probability_ok(m, limits):
    return m['min_critical_true_probability'] >= limits['min_true_probability'] and m['max_wrong_order_probability'] <= limits['max_wrong_order_probability']


def cells_ok(cells, limits):
    return all(c['accuracy'] >= limits['min_accuracy'] and c['mean_nll'] <= limits['max_mean_nll'] and
        c['order_planned'] > 0 and c['order_correct'] / c['order_planned'] >= limits['min_accuracy'] for c in cells)


def probe_gate(p, limits):
    groups = defaultdict(list)
    for pair in p['pairs']['records']: groups[pair['cell']].append(pair['correct'])
    return {'cells': cells_ok(p['by_family_language_polarity'].values(), limits), 'probabilities': probability_ok(p['all'], limits),
        'pairs': all(sum(v) / len(v) >= limits['min_accuracy'] for v in groups.values()),
        'gap': p['pairs']['minimum_gap'] >= limits['min_lexical_probability_gap']}


def audit_saved(repo, audit):
    root = repo / 'experiments/predictive_nucleus'; data, fitted, results = (root / p for p in ('data/lexical-v1', 'data/lexical-fit-v1', 'results/lexical-v1'))
    config, freeze, trained, report, manifest, decision = [h.read(p) for p in (root / 'lexical_protocol_v1.json', data / 'freeze.json', fitted / 'training.json', results / 'summary.json.xz', results / 'manifest.json', results / 'decision.json')]
    seeds, limits = config['model_seeds'], config['analysis']; audit.equal(seeds, [7, 11, 23, 37, 53], 'seeds')
    audit.equal([v['version'] for v in (config, freeze, trained, report)], ['lexical-v1'] * 4, 'study_versions')
    audit.equal(h.sha(root / 'lexical_protocol_v1.json'), (root / 'snapshots/lexical_protocol_v1.sha256').read_text().split()[0], 'protocol_lock')
    audit.equal(freeze['protocol_sha256'], h.sha(root / 'lexical_protocol_v1.json'), 'protocol_binding')
    pinned = {'data/bilingual-fit-v1/training.json': config['parent_language_training_sha256'], 'data/bilingual-v1/freeze.json': config['old_data_freeze_sha256'], 'results/bilingual-v1/manifest.json': config['old_result_manifest_sha256']}
    audit.equal({k: freeze['historical_artifacts'][k] for k in pinned}, pinned, 'historical_anchors')
    old_freeze, old_fitted, old_manifest = [h.read(root / p) for p in ('data/bilingual-v1/freeze.json', 'data/bilingual-fit-v1/training.json', 'results/bilingual-v1/manifest.json')]
    audit.equal({k: freeze['sources'][k] for k in old_freeze['sources']}, old_freeze['sources'], 'unchanged_historical_sources')
    for name, item in old_freeze['artifacts'].items(): audit.equal(h.sha(root / 'data/bilingual-v1' / name), item['sha256'], 'old_data/' + name)
    audit.equal(set(freeze['artifacts']), {'train-inputs.json.xz', 'audit.json', *(f'{law}-{kind}.json.xz' for law in LAWS for kind in ('inputs', 'oracle'))}, 'data_inventory')
    for name, digest in {**freeze['sources'], **freeze['historical_artifacts']}.items(): audit.equal(h.sha(root / name), digest, 'frozen/' + name)
    for folder, inventory in ((data, freeze['artifacts']), (results, manifest['artifacts'])):
        for name, item in inventory.items():
            audit.equal([h.sha(folder / name), (folder / name).stat().st_size], [item['sha256'], item['bytes']], 'artifact/' + name)
    audit.equal(decision, report['decision'], 'decision_copy'); audit.check(not (results / 'failure.json').exists(), 'no_execution_failure')
    for item in (trained, manifest): audit.check(item.get('complete', item.get('execution_complete')) is True and item['world_checkpoints_unchanged'] is True, 'completed_unchanged')
    audit.equal(trained['freeze_sha256'], h.sha(data / 'freeze.json'), 'fit_freeze')
    for path, field, target in ((fitted / 'attempt.json', 'source_data_commit', data / 'freeze.json'), (results / 'attempt.json', 'weights_commit', fitted / 'training.json')):
        attempt = h.read(path)
        audit.check(h.subprocess.check_output(['git', '-C', str(repo), 'show', attempt[field] + ':' + target.relative_to(repo).as_posix()]) == target.read_bytes(), field)
        audit.equal({k: attempt['runtime'][k] for k in config['execution']['runtime']}, config['execution']['runtime'], field + '/runtime')
    expected_fits = {f'grounded/{s}' for s in seeds}; audit.check(set(trained['reports']) == set(trained['checkpoints']) == expected_fits, 'five_fits')
    audit.equal(set(freeze['language_checkpoints']), {str(s) for s in seeds}, 'parent_inventory'); audit.equal(set(freeze['checkpoints']), set(LAWS), 'native_laws')
    for seed in seeds:
        key = f'grounded/{seed}'; parent, item, fit = freeze['language_checkpoints'][str(seed)], trained['checkpoints'][key], trained['reports'][key]
        audit.equal(parent, {**old_fitted['checkpoints'][key], 'state_sha256': old_fitted['reports'][key]['final_sha256']}, 'published_parent/' + key)
        for folder, record in ((root / 'data/bilingual-fit-v1', parent), (fitted, item)):
            saved = h.read(folder / record['file']); digest, count = h.fingerprint(saved['state'])
            audit.equal([h.sha(folder / record['file']), digest, count, saved['arm'], saved['seed']], [record['sha256'], record['state_sha256'], 474, 'grounded', seed], 'language/' + str(folder) + '/' + key)
            audit.equal(saved['state_sha256'], digest, 'language_internal/' + key)
        audit.equal([saved['parent_sha256'], fit['parent_sha256'], fit['initial_sha256'], fit['final_sha256'], fit['parameters'], fit['updates'], fit['training_forecasts_per_update']],
            [parent['sha256'], parent['sha256'], parent['state_sha256'], item['state_sha256'], 474, 256, 768], 'warm_start/' + key)
        audit.check(fit['cpu_seconds'] <= config['fit']['cpu_seconds_per_fit'], 'cpu_limit/' + key)
    for law in LAWS:
        audit.equal(set(freeze['checkpoints'][law]), {str(s) for s in seeds}, 'native_seeds/' + law)
        for seed in seeds:
            item = freeze['checkpoints'][law][str(seed)]; path = root / 'data/multisource-law-fit-v1' / item['file']; saved = h.read(path)
            audit.equal([h.sha(path), *h.fingerprint(saved['state']), saved['state_sha256']], [item['sha256'], item['state_sha256'], 562, item['state_sha256']], 'native/' + path.name)
            for commit in (config['base_commit'], config['checkpoint_commit']):
                audit.check(h.subprocess.check_output(['git', '-C', str(repo), 'show', commit + ':' + path.relative_to(repo).as_posix()]) == path.read_bytes(), 'native_unchanged/' + commit + '/' + path.name)
    training = h.read(data / 'train-inputs.json.xz'); old_training = h.read(root / 'data/bilingual-v1/train-inputs.json.xz')
    audit.equal(trained['training_input_sha256'], h.canonical(training), 'fit_input'); audit.equal(training['episodes'][:256], old_training['episodes'], 'exact_rehearsal')
    audit.equal([len(training['episodes']), len({e['id'] for e in training['episodes']}), sum(len(e['utterances']) for e in training['episodes'])], [640, 640, 768], 'training_inventory')
    audit.check(all(len(e['utterances']) == 1 for e in training['episodes'][256:]) and all(set(e) == {'id', 'entities', 'anchor', 'context', 'utterances'} and all(set(v) == {'text', 'reading'} for v in e['utterances']) for e in training['episodes']), 'observed_only_single_fresh_training')
    positions, exposure = defaultdict(set), [0, 0]
    for e in training['episodes']:
        first = e['context'][0]; modes = [m for m in (0, 1) if h.transition(e['anchor'], first['action'], m, 'nand') == first['reading']]
        audit.equal(len(modes), 1, 'observed_training_mode'); before = e['anchor']
        for event in e['context']:
            before = h.transition(before, event['action'], modes[0], 'nand'); audit.equal(event['reading'], before, 'training_context')
        for event in e['utterances']:
            for i, word in enumerate(event['text'].split()):
                if word not in e['entities']: positions[word].add(i); exposure[WORDS[word][1]] += 1; order = int(i == 2) ^ WORDS[word][1]
            mentions = [e['entities'].index(w) for w in event['text'].split() if w in e['entities']]
            before = h.transition(before, [0, mentions[order], mentions[1 - order], -1], modes[0], 'nand'); audit.equal(event['reading'], before, 'training_word_consequence')
    audit.equal(exposure, [576, 192], 'semantic_exposure')
    for i, pair in enumerate(WORD_PAIRS):
        for word in pair: audit.equal(positions[word], {1, 2} if i % 2 == 0 else {1 if i < 2 else 2}, 'word_layout_support/' + word)
    expected = {f'trace-{law}-{seed}-{arm}.json.xz' for law in LAWS for seed in seeds for arm in ARMS}
    audit.equal(set(manifest['artifacts']), expected | {'attempt.json', 'summary.json.xz', 'decision.json'}, 'result_inventory')
    audit.equal({p.name for p in results.glob('trace-*.json.xz')}, expected, 'trace_directory')
    for section, arms in (('by_trace', ('grounded', 'prior', 'retention')), ('probes', ARMS[:-1]), ('view_resources', VIEWS)):
        audit.equal(set(report[section]), {f'{law}/{seed}/{arm}' for law in LAWS for seed in seeds for arm in arms}, section + '/inventory')
    for section in ('controls', 'structural_transfer', 'comparisons', 'native_reference'): audit.equal(set(report[section]), {f'{law}/{seed}' for law in LAWS for seed in seeds}, section + '/inventory')
    trace_hashes, checks, structural, details, totals, costs = {}, {}, {}, {}, defaultdict(int), defaultdict(float)
    for law in LAWS:
        inputs, oracle = h.read(data / f'{law}-inputs.json.xz'), h.read(data / f'{law}-oracle.json.xz')
        records, gold, groups = h.verify_gold(audit, inputs, oracle, law); pairs = defaultdict(list)
        old_inputs = h.read(root / f'data/bilingual-v1/{law}-inputs.json.xz')
        old_records, old_gold, old_groups = h.verify_gold(audit, old_inputs, h.read(root / f'data/bilingual-v1/{law}-oracle.json.xz'), law + '/retention')
        audit.equal([len(old_records), sum(len(r['utterances']) for r in old_records.values())], [576, 2080], law + '/retention_denominators')
        audit.equal([len(records), sum(len(r['utterances']) for r in records.values())], [1152, 4160], law + '/denominators')
        audit.check(not ({n for r in records.values() for n in r['entities']} & {n for r in training['episodes'] for n in r['entities']}), law + '/fresh_names')
        for identity, g in gold.items():
            r = records[identity]; words = r['utterances'][-1]['text'].split(); slot = next(i for i, w in enumerate(words) if w not in r['entities']); word = words[slot]
            for t, event in enumerate(r['utterances']):
                position, lexeme = next((i, w) for i, w in enumerate(event['text'].split()) if w not in r['entities'])
                audit.equal(g['action_orders'][t], int(position == 2) ^ WORDS[lexeme][1], 'declared_word_action/' + identity)
            audit.equal([g['contrast_step'], g['contrast_synonym'], g['effect_polarity']], [len(r['utterances']) - 1, *WORDS[word]], 'probe_metadata/' + identity)
            audit.equal(slot in positions[BORROW[word]], g['contrast_synonym'] == 0, 'transfer_support/' + identity)
            prefix = {k: r[k] for k in ('entities', 'anchor', 'context')}; prefix.update(utterances=r['utterances'][:-1], contrast_tokens=[w if w in r['entities'] else '<lexeme>' for w in words])
            audit.equal(h.canonical(prefix), g['shared_prefix_sha256'], 'prefix/' + identity); pairs[g['lexical_pair_id']].append(identity)
        audit.equal(len(pairs), 576, law + '/pair_count')
        for kind, buckets in groups.items():
            for members in buckets.values():
                a, b = [gold[i] for i in members]; dimension = {'role': 'direction', 'bilingual': 'language', 'synonym': 'synonym'}[kind]
                audit.equal({a[dimension], b[dimension]}, {'svo', 'osv'} if kind == 'bilingual' else {0, 1}, kind + '/paired_dimension')
                shared = [k for k in ('family', 'lineage', 'mode', 'direction', 'language', 'synonym', 'effect_polarity') if k != dimension]
                audit.equal([a[k] for k in shared], [b[k] for k in shared], kind + '/paired_stratum')
                audit.equal([records[members[0]][k] for k in ('entities', 'anchor', 'context')], [records[members[1]][k] for k in ('entities', 'anchor', 'context')], kind + '/paired_context')
                audit.equal(a['actions'], [[0, v[2], v[1], -1] for v in b['actions']] if kind == 'role' else b['actions'], kind + '/paired_actions')
                if kind != 'role': audit.equal([a[k] for k in ('truth', 'opposite_truth')], [b[k] for k in ('truth', 'opposite_truth')], kind + '/paired_truths')
        for members in pairs.values():
            audit.equal(len(members), 2, 'lexical_pair_size'); a, b = [gold[i] for i in members]; x, y = [records[i]['utterances'][-1]['text'].split() for i in members]
            changed = [(u, v) for u, v in zip(x, y, strict=True) if u != v]
            audit.check(len(changed) == 1 and all(w not in records[members[0]]['entities'] for w in changed[0]) and a['shared_prefix_sha256'] == b['shared_prefix_sha256'] and {a['effect_polarity'], b['effect_polarity']} == {0, 1}, 'one_word_shared_prefix')
            audit.equal([a[k] for k in ('family', 'language', 'mode', 'direction', 'synonym', 'contrast_synonym', 'contrast_step')], [b[k] for k in ('family', 'language', 'mode', 'direction', 'synonym', 'contrast_synonym', 'contrast_step')], 'lexical_paired_stratum')
            audit.equal([a['counterpart_id'], b['counterpart_id'], a['truth'][-1], b['truth'][-1], a['actions'][-1]], [b['id'], a['id'], b['opposite_truth'][-1], a['opposite_truth'][-1], [0, b['actions'][-1][2], b['actions'][-1][1], -1]], 'counterfactual_pair')
            audit.check(a['truth'][-1] != b['truth'][-1], 'distinct_pair_truths')
        def measured(raw, r, g, final, label, native=False):
            ids = [(v['id'], v['step']) for v in raw]; planned = {(i, t) for i, e in r.items() for t in ([len(e['utterances']) - 1] if final else range(len(e['utterances'])))}
            audit.check(len(ids) == len(set(ids)) and set(ids) == planned and all(type(v['step']) is int and set(v) == {'id', 'step', 'logp', 'order_logp'} for v in raw), label + '/inventory')
            audit.check(all(v['order_logp'] is None if native else type(v['order_logp']) is list for v in raw), label + '/order_inventory')
            return {(v['id'], v['step']): h.measure(audit, v, r[v['id']], g[v['id']], label) for v in raw}
        for seed in seeds:
            key = f'{law}/{seed}'; points, full, probes = {}, {}, {}; parent = freeze['language_checkpoints'][str(seed)]['sha256']
            for arm in ARMS:
                name = f'trace-{law}-{seed}-{arm}.json.xz'; trace = h.read(results / name); trace_hashes[name] = h.sha(results / name)
                r, g, group, envelope = (old_records, old_gold, old_groups, old_inputs) if arm == 'retention' else (records, gold, groups, inputs)
                bindings = {'law': law, 'seed': seed, 'arm': arm, 'input_sha256': h.canonical(envelope), 'freeze_sha256': h.sha(data / 'freeze.json'), 'training_sha256': h.sha(fitted / 'training.json'), 'checkpoint_sha256': parent if arm == 'prior' else trained['checkpoints'][f'grounded/{seed}']['sha256']}
                audit.equal({k: trace[k] for k in bindings}, bindings, key + '/' + arm + '/bindings')
                points[arm] = measured(trace['points'], r, g, arm in VIEWS, key + '/' + arm); totals[arm] += len(points[arm])
                if arm not in VIEWS:
                    full[arm] = h.summarize(points[arm], r, g, group); audit.equal(report['by_trace'][key + '/' + arm], {**full[arm], 'resources': trace['resources']}, key + '/' + arm + '/summary')
                if arm != 'retention': probes[arm] = probe(points[arm], gold, pairs); audit.equal(report['probes'][key + '/' + arm], probes[arm], key + '/' + arm + '/probes')
                if arm in VIEWS: audit.equal(report['view_resources'][key + '/' + arm], trace['resources'], key + '/' + arm + '/resources')
                resource = trace['resources']; prep = resource['native_cache_preparation_shared_once']; audit.check((prep is not None) == (arm == 'grounded'), key + '/' + arm + '/unique_cache_cost')
                for unit in ('cpu_seconds', 'wall_seconds'): costs['forecasts_' + unit] += resource[unit]; costs['preparation_' + unit] += prep[unit] if prep else 0.
                costs['peak_rss_kib'] = max(costs['peak_rss_kib'], resource['peak_rss_kib'], trained['resources']['peak_rss_kib'])
            reference = report['native_reference'][key]; native = measured(reference['points'], records, gold, False, key + '/native', True); totals['native'] += len(native)
            audit.equal(reference['all'], h.metrics(list(native.values())), key + '/native_summary')
            archived = h.read(root / f'results/bilingual-v1/trace-{law}-{seed}-grounded.json.xz')
            audit.equal(h.sha(root / f'results/bilingual-v1/trace-{law}-{seed}-grounded.json.xz'), old_manifest['artifacts'][f'trace-{law}-{seed}-grounded.json.xz']['sha256'], key + '/original_trace_hash')
            audit.equal([archived['checkpoint_sha256'], archived['input_sha256'], archived['freeze_sha256'], archived['training_sha256']], [parent, h.canonical(old_inputs), config['old_data_freeze_sha256'], config['parent_language_training_sha256']], key + '/archived_binding')
            comparisons = {'native': compare(points['grounded'], native), 'parent_fresh': compare(points['grounded'], points['prior']), 'parent_retention': compare(points['retention'], measured(archived['points'], old_records, old_gold, False, key + '/archived'))}
            audit.equal(report['comparisons'][key], comparisons, key + '/comparisons')
            tv = lambda a, b: math.fsum(abs(x - y) for x, y in zip(a['probabilities'], b['probabilities'])) / 2
            controls = []
            for pair, members in sorted(pairs.items()):
                a, b = [(i, gold[i]['contrast_step']) for i in members]; swap = [(points['swapped'][a], gold[b[0]]['truth'][-1]), (points['swapped'][b], gold[a[0]]['truth'][-1])]
                controls.append({'pair_id': pair, 'masked_tv': tv(points['masked'][a], points['masked'][b]), 'masked_both_correct': points['masked'][a]['correct'] and points['masked'][b]['correct'], 'swapped_counterpart_tv': max(tv(points['swapped'][a], points['grounded'][b]), tv(points['swapped'][b], points['grounded'][a])), 'swapped_counterpart_probability': min(p['probabilities'][h.index(truth)] for p, truth in swap), 'swapped_counterparts_correct': sum(p['map'] == h.index(truth) for p, truth in swap)})
            control = {'planned_pairs': len(controls), 'masked_max_tv': max(c['masked_tv'] for c in controls), 'masked_both_correct': sum(c['masked_both_correct'] for c in controls), 'swapped_max_counterpart_tv': max(c['swapped_counterpart_tv'] for c in controls), 'swapped_min_counterpart_probability': min(c['swapped_counterpart_probability'] for c in controls), 'swapped_counterparts_correct': sum(c['swapped_counterparts_correct'] for c in controls), 'records': controls}
            audit.equal(report['controls'][key], control, key + '/controls')
            transfer = {label: probe(points['cross_order'], gold, pairs, i) for i, label in enumerate(('seen', 'held_out'))}; audit.equal(report['structural_transfer'][key], transfer, key + '/structural')
            structural[key] = {label: probe_gate(p, limits) for label, p in transfer.items()}; candidate, query = full['grounded'], probes['grounded']
            checks[key] = {'canonical_cells': cells_ok(candidate['by_family_language'].values(), limits), 'role_trajectories': all(c['role_pairs_correct'] / c['role_pairs_planned'] >= limits['min_accuracy'] for c in candidate['by_family_language'].values()), 'canonical_probabilities': probability_ok(candidate['all'], limits), 'canonical_twins': all(t['max_tv'] <= limits['max_twin_tv'] and t['map_consistent_pairs'] == t['planned_pairs'] for t in candidate['twins'].values()), **{'lexical_' + k: v for k, v in probe_gate(query, limits).items()}, 'mask_information_removed': control['masked_max_tv'] <= limits['max_control_tv'] and control['masked_both_correct'] == 0 and probes['masked']['all']['accuracy'] <= .5, 'swapped_counterfactual': control['swapped_max_counterpart_tv'] <= limits['max_control_tv'] and control['swapped_min_counterpart_probability'] >= limits['min_true_probability'], 'gain_over_parent': query['all']['accuracy'] - probes['prior']['all']['accuracy'] >= limits['min_prior_probe_accuracy_gain'], 'native_retention': not comparisons['native']['regressions'], 'old_exact_retention': not comparisons['parent_retention']['regressions']}
            details[key] = {'full': {arm: {k: v for k, v in value.items() if k in ('all', 'by_entity_count', 'by_family_language', 'trajectories')} for arm, value in full.items()}, 'probe': {arm: p['all'] for arm, p in probes.items()}, 'structural': {label: {k: v for k, v in p.items() if k != 'pairs'} for label, p in transfer.items()}, 'controls': {k: v for k, v in control.items() if k != 'records'}, 'comparisons': {label: {k: v for k, v in c.items() if k not in ('nll_worse', 'nll_better')} for label, c in comparisons.items()}}
            details[key]['view_by_entity_count'] = {arm: {str(n): h.metrics([p for p in points[arm].values() if len(records[p['id']]['entities']) == n]) for n in (3, 4, 5, 6)} for arm in VIEWS}
    audit.equal(dict(totals), {'grounded': 41600, 'prior': 41600, 'masked': 11520, 'swapped': 11520, 'cross_order': 11520, 'retention': 20800, 'native': 41600}, 'all_denominators')
    audit.equal(report['bindings'], {'freeze_sha256': h.sha(data / 'freeze.json'), **{k: freeze[k] for k in ('sources', 'checkpoints', 'language_checkpoints', 'historical_artifacts')}, 'training_sha256': h.sha(fitted / 'training.json'), 'trace_sha256': trace_hashes}, 'summary_bindings')
    audit.equal(decision['checks'], checks, 'primary_checks'); audit.equal(decision['structural_checks'], structural, 'structural_checks')
    result = 'KEEP_LEXICAL_GROUNDING' if all(all(v.values()) for v in checks.values()) else 'REVISE_LEXICAL_GROUNDING'
    transfer_result = 'STRUCTURAL_TRANSFER_ESTABLISHED' if all(all(all(g.values()) for g in v.values()) for v in structural.values()) else 'STRUCTURAL_TRANSFER_NOT_ESTABLISHED'
    audit.equal([decision['decision'], decision['structural_transfer'], decision['scientific_admission'], decision['execution_complete']], [result, transfer_result, False, True], 'decisions')
    return {'decision': result, 'structural_transfer': transfer_result, 'totals': dict(totals), 'fit_updates': sum(r['updates'] for r in trained['reports'].values()), 'checks': checks, 'structural_checks': structural, 'details': details, 'resources': {**costs, 'fitting': trained['resources'], 'scoring': report['evaluator_resources']}}


def main():
    global h
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--repo', type=Path, required=True); parser.add_argument('--output', type=Path, required=True); args = parser.parse_args()
    repo = args.repo.resolve(); sys.dont_write_bytecode = True; sys.path.insert(0, str(repo / 'experiments/predictive_nucleus')); import audit_bilingual_saved as h
    audit, start = h.Audit(), time.perf_counter()
    try: result = audit_saved(repo, audit)
    except Exception: audit.check(False, 'audit_exception'); result = {'exception': traceback.format_exc()}
    result.update(check_count=audit.checks, discrepancies=audit.discrepancies, discrepancy_count=audit.discrepancy_count, audit_passed=audit.discrepancy_count == 0, audit_wall_seconds=time.perf_counter() - start, audit_sha256=h.sha(__file__), helper_sha256=h.sha(h.__file__))
    with args.output.open('x') as stream: json.dump(h.safe(result), stream, sort_keys=True, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({k: result.get(k) for k in ('audit_passed', 'decision', 'structural_transfer', 'check_count', 'discrepancy_count')})); return int(audit.discrepancy_count != 0)


if __name__ == '__main__': raise SystemExit(main())
