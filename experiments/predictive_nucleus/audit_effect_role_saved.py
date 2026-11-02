"""Stdlib-only saved-evidence audit; no model, study scorer or oracle imports.

Pre-score checks every raw distribution using observed inputs only. Full mode
recomputes all decision gates and their world/action/goal/retention evidence.
It does not independently regenerate the physical oracle, ECE, or timing costs.
"""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

if __package__:
    from . import audit_bilingual_saved as h
else:
    import audit_bilingual_saved as h

LAWS, SEEDS, ARMS = ('nand', 'nor'), (7, 11, 23, 37, 53), ('grounded', 'parser', 'text_only')
BANKS = ('bilingual', 'lexical', 'binding', 'saturation', 'centering', 'coordinate')


def require(value, label):
    if not value: raise ValueError(label)


def average(values):
    return math.fsum(v / len(values) for v in values) if values else None


def accuracy(values):
    return sum(values) / len(values) if values else None


def logs(values, size, tolerance):
    require(type(values) is list and len(values) == size, 'forecast dimensions')
    values = [h.number(v) for v in values]
    require(all(type(v) in (int, float) and not math.isnan(v) and v != math.inf for v in values), 'log values')
    top = max(values)
    require(math.isfinite(top) and abs(top + math.log(math.fsum(math.exp(v - top) for v in values))) <= tolerance,
            'forecast normalization')
    return values


def index_rows(rows, records, arm='grounded', fresh=True, archived=False):
    """Input-only index: no target/oracle/report access or silent repairs."""
    expected = {(eid, t) for eid, record in records.items() for t in range(len(record['utterances']))}
    views = ('canonical', 'masked') if arm == 'grounded' and fresh and not archived else ('canonical',)
    result = {v: {} for v in views}; seen = set(); field = 'order_logp' if archived else 'action_logp'
    require(type(rows) is list, 'raw point list')
    for row in rows:
        require(set(row) == {'id', 'step', 'view', 'logp', field}, 'raw point fields')
        key, view = (row['id'], row['step']), row['view']
        require(type(row['id']) is str and type(row['step']) is int and key in expected and
            (*key, view) not in seen and (view in views or archived and view in ('masked', 'swapped')), 'point inventory')
        seen.add((*key, view))
        world = logs(row['logp'], 2 ** len(records[key[0]]['entities']), 1e-12 if fresh and not archived else 1e-10)
        require((row[field] is None) == (arm == 'text_only'), 'control action nullness')
        action = None if row[field] is None else logs(row[field], 2 if archived else 4, 1e-10)
        if view in result: result[view][key] = {'logp': world, 'action_logp': action}
    require(all(v.keys() == expected for v in result.values()), 'missing raw forecasts')
    return result


def prefix(record, t=None):
    value = {k: record[k] for k in ('entities', 'anchor', 'context')}
    return value | ({'utterances': record['utterances'][:-1]} if t is None else
                    {'past': record['utterances'][:t], 'text': record['utterances'][t]['text']})


def inventory(inputs, evaluator):
    records = {e['id']: e for e in inputs['episodes']}; oracle = evaluator['oracle']
    gold = {e['id']: e for e in oracle['episodes']}; pairs = {k: defaultdict(list) for k in ('role', 'bilingual')}
    require(len(gold) == len(oracle['episodes']) == len(records) and gold.keys() == records.keys() and
        oracle['input_sha256'] == h.canonical(inputs), 'evaluator inventory/binding')
    shared = {}
    for eid, meta in gold.items():
        record = records[eid]; n = len(record['entities']); steps = len(record['utterances'])
        require(all(len(meta[k]) == steps for k in ('actions', 'action_indices', 'truth', 'forecasts', 'cells')),
                'evaluator geometry')
        require(meta['shared_prefix_sha256'] == h.canonical(prefix(record)), 'evaluator shared prefix')
        for kind in pairs:
            if meta[kind + '_pair_id'] is not None: pairs[kind][meta[kind + '_pair_id']].append(eid)
        for t, f in enumerate(meta['forecasts']):
            support, probabilities = f['possible_worlds'], f['probabilities']
            require(support == sorted(set(support)) and support and all(type(w) is int and 0 <= w < 2 ** n for w in support)
                and len(support) == len(probabilities) and all(type(p) in (int, float) and math.isfinite(p) and p > 0
                for p in probabilities) and abs(math.fsum(probabilities) - 1) <= 1e-12, 'oracle probability geometry')
            require(meta['truth'][t] == record['utterances'][t]['reading'] and h.index(meta['truth'][t]) in support,
                    'evaluator delivered truth')
            a, b = [record['entities'].index(w) for w in record['utterances'][t]['text'].split() if w in record['entities']]
            menu = [[0, a, b, -1], [0, b, a, -1], [1, a, -1, 1], [1, b, -1, 1]]
            require(type(meta['action_indices'][t]) is int and meta['action_indices'][t] in range(4) and
                menu[meta['action_indices'][t]] == meta['actions'][t] and meta['action_indices'][t] in
                f['equivalent_action_indices'], 'evaluator menu identity')
            require(f['information_key'] == h.canonical(prefix(record, t)), 'oracle information key')
            conditional = {k: v for k, v in f.items() if k != 'information_key'}
            require(shared.setdefault(f['information_key'], conditional) == conditional, 'same-information target mismatch')
    require(all(len(v) == 2 for kind in pairs.values() for v in kind.values()), 'paired inventory')
    used = set()
    for group in evaluator['goal_groups']:
        ids = group['episodes']; require(len(ids) == 4 and len(set(ids)) == 4 and not set(ids) & used, 'goal branch inventory')
        used.update(ids); first = records[ids[0]]; before = first['utterances'][-2]['reading']
        require(all(prefix(records[e]) == prefix(first) for e in ids) and group['before'] == before and
                group['shared_prefix_sha256'] == h.canonical(prefix(first)), 'parallel goal prefix')
        a, b = group['participants']; menu = [[0, a, b, -1], [0, b, a, -1], [1, a, -1, 1], [1, b, -1, 1]]
        require(all(gold[e]['final_choice'] == i and gold[e]['actions'][-1] == menu[i] for i, e in enumerate(ids)),
                'parallel goal action menu')
        require({tuple(g['target_bits']) for g in group['goals']} == {(0, 0), (0, 1), (1, 0), (1, 1)} and
                len(group['goals']) == 4, 'complete goal targets including impossible')
        for goal in group['goals']:
            bits = before.copy(); bits[a], bits[b] = goal['target_bits']; world = h.index(bits)
            utilities = [dict(zip(gold[e]['forecasts'][-1]['possible_worlds'],
                gold[e]['forecasts'][-1]['probabilities'], strict=True)).get(world, 0.) for e in ids]
            contact, setting = max(utilities[:2]), max(utilities[2:]); best = max(utilities)
            expected = {'oracle_utilities': utilities, 'max_utility': best,
                'optimal_choices': [i for i, u in enumerate(utilities) if u == best], 'attainable': best > 0,
                'effect_sensitive': contact != setting, 'set_required': setting > contact, 'contact_required': contact > setting}
            require(all(goal[k] == v for k, v in expected.items()), 'conditional goal utility/spectator reward')
    require(used == records.keys(), 'unassigned final alternatives')
    return records, gold, pairs


def measured(indexed, records, gold):
    result = {}
    for (eid, t), row in indexed.items():
        record, meta = records[eid], gold[eid]; n = len(record['entities']); f = meta['forecasts'][t]
        q = dict(zip(f['possible_worlds'], f['probabilities'], strict=True)); values = row['logp']
        probabilities = [math.exp(v) for v in values]; best = values.index(max(values)); truth = h.index(meta['truth'][t])
        previous = h.index(record['context'][-1]['reading'] if t == 0 else record['utterances'][t - 1]['reading'])
        fixed = [i for i in range(n) if len({(w >> i) & 1 for w in [previous, *q]}) == 1]
        action = row['action_logp']; choice = None if action is None else action.index(max(action))
        result[eid, t] = {'episode': eid, 'step': t, 'family': meta['family'], **meta['cells'][t],
            'action_kind': 'contact' if meta['actions'][t][0] == 0 else 'set', 'answerable': len(q) == 1,
            'correct': best == truth, 'map_world': best, 'nll': -values[truth],
            'brier': math.fsum((p - (i == truth)) ** 2 for i, p in enumerate(probabilities)),
            'oracle_kl': sum(p * (math.log(p) - values[w]) for w, p in q.items()),
            'oracle_total_variation': sum(abs(p - q.get(w, 0.)) for w, p in enumerate(probabilities)) / 2,
            'outside_support_mass': sum(p for w, p in enumerate(probabilities) if w not in q),
            'map_outside_support': best not in q,
            'known_unchanged_errors': sum(((best >> i) & 1) != ((previous >> i) & 1) for i in fixed),
            'action_index': meta['action_indices'][t], 'map_action': choice,
            'action_correct': None if choice is None else choice == meta['action_indices'][t],
            'equivalent_action_indices': f['equivalent_action_indices'],
            'endpoint_action_compatible': None if choice is None else choice in f['equivalent_action_indices'],
            'probabilities': probabilities, 'logp': values}
    return result


def metric(points):
    n = len(points)
    return {'planned_points': n, 'supported_forecasts': n, 'support_coverage': 1. if n else None,
        'correct': sum(p['correct'] for p in points), 'accuracy': accuracy([p['correct'] for p in points]),
        'mean_nll': average([p['nll'] for p in points]), 'mean_brier': average([p['brier'] for p in points]),
        'map_outside_support': sum(p['map_outside_support'] for p in points),
        'known_unchanged_errors': sum(p['known_unchanged_errors'] for p in points),
        **{'mean_' + key: average([p[key] for p in points]) for key in ('oracle_kl', 'oracle_total_variation', 'outside_support_mass')},
        'max_oracle_total_variation': max((p['oracle_total_variation'] for p in points), default=None)}


def strata(points):
    return {'all': metric(points), 'identifiable': metric([p for p in points if p['answerable']]),
            'ambiguous': metric([p for p in points if not p['answerable']])}


def actions(points):
    values = [p['action_correct'] for p in points if p['action_correct'] is not None]
    return {'planned': len(points), 'produced': len(values), 'correct': sum(values),
        'accuracy': accuracy(values) if len(values) == len(points) else None,
        'endpoint_compatible': sum(p['endpoint_action_compatible'] is True for p in points)}


def summary(indexed, pairs):
    points = list(indexed.values()); result = strata(points)
    groupers = {'family': lambda p: p['family'], 'layout': lambda p: p['layout'], 'effect': lambda p: p['action_kind'],
        'lexicon': lambda p: 'new' if p['new_word'] else 'old',
        'cell': lambda p: '/'.join((p['family'], p['layout'], p['action_kind'], 'new' if p['new_word'] else 'old'))}
    for kind, key in groupers.items():
        groups = defaultdict(list)
        for p in points: groups[key(p)].append(p)
        result['by_' + kind] = {k: strata(v) for k, v in groups.items()}
    episodes = defaultdict(list)
    for p in points: episodes[p['episode']].append(p)
    for name, groups in (('trajectories', [[e] for e in sorted(episodes)]), ('role_pairs', list(pairs['role'].values()))):
        rows = [[p for e in ids for p in episodes[e] if p['answerable']] for ids in groups]
        rows = [r for r in rows if r]
        result[name] = {'identifiable_planned': len(rows), 'identifiable_correct': sum(all(p['correct'] for p in r) for r in rows),
            'identifiable_accuracy': accuracy([all(p['correct'] for p in r) for r in rows])}
    twins = [.5 * math.fsum(abs(x - y) for x, y in zip(indexed[a, t]['probabilities'], indexed[b, t]['probabilities'], strict=True))
             for a, b in pairs['bilingual'].values() for t in range(len(episodes[a]))]
    result.update(bilingual={'planned': len(twins), 'max_total_variation': max(twins) if twins else None},
        actions=actions(points), actions_by_lexicon={name: actions([p for p in points if p['new_word'] == value])
        for name, value in (('new', True), ('old', False))})
    words = defaultdict(list)
    for p in points: words[p['word'] + '/' + p['layout']].append(p)
    result['by_taught_lexeme_layout'] = {k: actions(v) for k, v in words.items()}
    return result


def goals(indexed, groups):
    finals = {}
    for (eid, t), p in indexed.items():
        if eid not in finals or t > finals[eid]['step']: finals[eid] = p
    rows = []
    for group in groups:
        last = [finals[e] for e in group['episodes']]
        for goal in group['goals']:
            bits = group['before'].copy()
            for i, bit in zip(group['participants'], goal['target_bits'], strict=True): bits[i] = bit
            world = h.index(bits); values = [p['logp'][world] for p in last]; choice = values.index(max(values))
            actual = goal['oracle_utilities'][choice]
            rows.append({**goal, 'group_id': group['id'], 'family': last[0]['family'], 'layout': last[0]['layout'],
                'target_world': world, 'predicted_utilities': [math.exp(v) for v in values], 'predicted_log_utilities': values,
                'chosen': choice, 'optimal': choice in goal['optimal_choices'], 'expected_utility': actual,
                'regret': goal['max_utility'] - actual})
    def stats(selected):
        return {'planned': len(selected), 'optimal': sum(r['optimal'] for r in selected),
            'optimal_accuracy': accuracy([r['optimal'] for r in selected]),
            'mean_regret': average([r['regret'] for r in selected]), 'max_regret': max((r['regret'] for r in selected), default=None)}
    result = {k: stats(rows if k == 'all' else [r for r in rows if r[k]])
              for k in ('all', 'attainable', 'effect_sensitive', 'set_required', 'contact_required')}
    result['impossible'] = stats([r for r in rows if not r['attainable']])
    for kind in ('family', 'layout'):
        result['by_' + kind] = {k: stats([r for r in rows if r[kind] == k]) for k in sorted({r[kind] for r in rows})}
    return {**result, 'records': rows}


def decision_checks(reports, goal_reports, limits):
    r, g = reports['grounded'], goal_reports['grounded']
    exact = [r['identifiable'], *[v['identifiable'] for k in ('family', 'layout', 'effect', 'lexicon', 'cell')
                                for v in r['by_' + k].values()]]
    quality = [v[k] for name in ('family', 'layout', 'effect', 'lexicon', 'cell') for v in r['by_' + name].values()
               for k in ('identifiable', 'ambiguous') if v[k]['planned_points']]
    binding = [r['actions'], *r['actions_by_lexicon'].values(), *r['by_taught_lexeme_layout'].values()]
    goal_names = ('attainable', 'effect_sensitive', 'set_required', 'contact_required')
    chosen = [g['all'], *[g[k] for k in goal_names if g[k]['planned']], *g['by_family'].values(), *g['by_layout'].values()]
    compare = {arm: {'planned': g['effect_sensitive']['planned'], 'optimal_accuracy_gain':
        g['effect_sensitive']['optimal_accuracy'] - goal_reports[arm]['effect_sensitive']['optimal_accuracy']
        if g['effect_sensitive']['planned'] else None} for arm in ('masked', 'text_only')}
    checks = {'complete_support': r['all']['support_coverage'] == 1.,
        'identifiable_accuracy': all(s['accuracy'] >= limits['identifiable_accuracy'] for s in exact if s['planned_points']),
        'supported_MAP_worlds': r['all']['map_outside_support'] == 0, 'known_unchanged_preserved': r['all']['known_unchanged_errors'] == 0,
        'conditional_probability_quality': all(s['mean_oracle_kl'] <= limits['mean_oracle_kl'] for s in quality),
        'ambiguous_no_collapse': not r['ambiguous']['planned_points'] or r['ambiguous']['max_oracle_total_variation'] <= limits['max_ambiguous_total_variation'],
        **{'identifiable_' + k: r[k]['identifiable_accuracy'] is not None and r[k]['identifiable_accuracy'] >= limits[limit]
            for k, limit in (('trajectories', 'identifiable_trajectory_accuracy'), ('role_pairs', 'identifiable_role_pair_accuracy'))},
        'globally_taught_action_identity': all(s['accuracy'] is not None and s['accuracy'] >= limits['action_accuracy'] for s in binding),
        'bilingual_probability_agreement': r['bilingual']['max_total_variation'] is not None and r['bilingual']['max_total_variation'] <= limits['max_bilingual_total_variation'],
        'goal_stratum_inventory': all(g[k]['planned'] > 0 for k in goal_names),
        'goal_optimal_choices': all(s['optimal_accuracy'] >= limits['goal_optimal_accuracy'] for s in chosen),
        'goal_mean_regret': all(s['mean_regret'] <= limits['mean_goal_regret'] for s in chosen),
        'goal_max_regret': all(s['max_regret'] <= limits['max_goal_regret'] for s in chosen),
        'effect_sensitive_goal_inventory': g['effect_sensitive']['planned'] >= max(1, limits.get('min_effect_sensitive_goals', 1)) and
            g['set_required']['planned'] > 0 and g['contact_required']['planned'] > 0,
        **{k + '_goal_gain': v['optimal_accuracy_gain'] is not None and v['optimal_accuracy_gain'] >= limits['min_effect_sensitive_goal_gain']
           for k, v in compare.items()}}
    return checks, compare


def retained(now, old, records, limits):
    rows = []
    for key in sorted(now):
        a, b = now[key], old[key]; target = h.index(records[key[0]]['utterances'][key[1]]['reading'])
        x, y = a['logp'], b['logp']; ax, ay = a['action_logp'], b['action_logp']
        mx, my, amx, amy = [v.index(max(v)) for v in (x, y, ax, ay)]; nll, old_nll = -x[target], -y[target]
        delta = [abs(math.exp(i) - math.exp(j)) for i, j in zip(x, y, strict=True)]
        rows.append({'id': key[0], 'step': key[1], 'correct': mx == target, 'archived_correct': my == target,
            'regression': my == target and mx != target, 'repair': my != target and mx == target,
            'map_world': mx, 'archived_map_world': my, 'world_map_changed': mx != my,
            'map_action': amx, 'archived_map_action': amy, 'action_map_changed': amx != amy,
            'action_probability_changes': [math.exp(i) - math.exp(j) for i, j in zip(ax, [*ay, -math.inf, -math.inf], strict=True)],
            'candidate_set_mass': math.exp(ax[2]) + math.exp(ax[3]), 'logp_equal': x == y,
            'nll': nll, 'archived_nll': old_nll, 'nll_change': h.difference(nll, old_nll),
            'max_logp_change': max(0. if i == j else math.inf if math.isinf(i) or math.isinf(j) else abs(i - j)
                                   for i, j in zip(x, y, strict=True)),
            'true_probability_change': math.exp(x[target]) - math.exp(y[target]),
            'max_abs_probability_change': max(delta), 'total_variation': math.fsum(delta) / 2})
    mean = lambda k: average([r[k] for r in rows]); nll, old_nll = mean('nll'), mean('archived_nll')
    checks = {'no_exact_regressions': not any(r['regression'] for r in rows),
        'retention_action_MAP': not any(r['action_map_changed'] for r in rows), 'retention_mean_nll': nll <= limits['max_retention_mean_nll']}
    return {'planned': len(rows), 'correct': sum(r['correct'] for r in rows), 'archived_correct': sum(r['archived_correct'] for r in rows),
        **{name: [[r['id'], r['step']] for r in rows if r[field]] for name, field in (('regressions', 'regression'),
            ('repairs', 'repair'), ('world_map_changes', 'world_map_changed'), ('action_map_changes', 'action_map_changed'))},
        'exact_world_vectors': sum(r['logp_equal'] for r in rows), 'mean_nll': nll, 'archived_mean_nll': old_nll,
        'mean_nll_change': h.difference(nll, old_nll), 'max_logp_change': max(r['max_logp_change'] for r in rows),
        'mean_candidate_set_mass': mean('candidate_set_mass'), 'max_candidate_set_mass': max(r['candidate_set_mass'] for r in rows),
        'checks': checks, 'passed': all(checks.values()), 'points': rows}


def compare_subset(audit, saved, computed, label):
    """Explicitly selected summaries; omitted rich fields are outside audit scope."""
    if isinstance(computed, dict):
        require(isinstance(saved, dict) and computed.keys() <= saved.keys(), 'missing saved summary: ' + label)
        for k, v in computed.items(): compare_subset(audit, saved[k], v, label + '/' + k)
    else: audit.equal(saved, computed, label)


def lexical_receipt(registry, observed, unknown_tokens, receipt=None):
    vocab = [{w for e in bank['episodes'] for event in e['utterances'] for w in event['text'].split()
              if w not in e['entities']} for bank in observed]
    tokens, legacy = registry['tokens'], registry['legacy_tokens']
    require(registry['version'] == 'effect-role-lexical-registry-v1' and set(tokens) == set.union(*vocab) and
        legacy == sorted(vocab[0]) and registry['training_sha256'] == [h.canonical(v) for v in observed], 'registry TRAIN provenance')
    used = set()
    for word in [*legacy, *sorted(tokens.keys() - set(legacy))]:
        pieces = list(word) + [word[i:i + 2] for i in range(len(word) - 1)]; values = [0.] * 8
        for piece in pieces:
            code = hashlib.sha256(piece.encode()).digest(); values[code[0] % 8] += 1. if code[1] & 1 else -1.
        values = [v / max(len(pieces), 1) for v in values]; source, nonce = 'characters', None
        if tuple(values) in used:
            require(word not in legacy, 'inherited feature collision')
            for nonce in range(256):
                raw = hashlib.sha256(b'effect-role-token-v1\0' + word.encode() + b'\0' + str(nonce).encode()).digest()
                values = [int.from_bytes(raw[i:i + 4], 'big') / 2 ** 31 - 1. for i in range(0, 32, 4)]
                if tuple(values) not in used: break
            source = 'identity_collision'
        expected = {'id': hashlib.sha256(word.encode()).hexdigest(), 'features': values, 'source': source, 'nonce': nonce}
        require(tokens[word] == expected and tuple(values) not in used, 'exact lexical identity assignment'); used.add(tuple(values))
    require(len(unknown_tokens) == len(set(unknown_tokens)) and not set(unknown_tokens) & tokens.keys(), 'unknown token inventory')
    expected = {'version': 'effect-role-lexical-controls-v1', 'registry_sha256': h.canonical(registry),
        'registry_after_sha256': h.canonical(registry), 'known_tokens': len(tokens), 'known_unique_ids': len(tokens),
        'known_unique_features': len(tokens), 'unknown': [{'token': w, 'id': hashlib.sha256(w.encode()).hexdigest(),
        'status': 'UNRESOLVED_LEXICAL_IDENTITY'} for w in sorted(unknown_tokens)], 'unresolved_exception': True,
        'semantic_model_calls': 0, 'checks': {}}
    r = expected if receipt is None else receipt
    require(set(r) == set(expected) and r['version'] == expected['version'] and type(r['unknown']) is list and
            all(type(r[k]) is int for k in ('known_tokens', 'known_unique_ids', 'known_unique_features', 'semantic_model_calls')),
            'lexical control fields')
    checks = {'registry_bound': r['registry_sha256'] == expected['registry_sha256'],
        'known_identities_distinct': r['known_tokens'] == r['known_unique_ids'] == len(tokens),
        'known_features_distinct': r['known_unique_features'] == len(tokens),
        'unknown_identities_unresolved': r['unresolved_exception'] is True and r['unknown'] == expected['unknown'],
        'registry_unchanged': r['registry_after_sha256'] == r['registry_sha256'],
        'no_semantic_forecast': r['semantic_model_calls'] == 0}
    return {**r, 'checks': checks}


def audit_saved(repo, audit, pre_score=False, publication=None):
    root = repo / 'experiments/predictive_nucleus'; data = root / 'data/effect-role-v1'
    fitted = root / 'data/effect-role-fit-v1'; traces = root / 'results/effect-role-v1/traces'; scored = traces.parent / 'scored'
    config, freeze, trained, manifest = [h.read(p) for p in (root / 'effect_role_protocol_v1.json', data / 'freeze.json',
        fitted / 'training.json', traces / 'manifest.json')]
    audit.equal(config['model_seeds'], list(SEEDS), 'seeds'); audit.equal(config['arms'], list(ARMS), 'arms')
    audit.equal([freeze['version'], trained['version']], ['effect-role-v1'] * 2, 'study identity')
    audit.equal(h.sha(root / 'effect_role_protocol_v1.json'),
                (root / 'snapshots/effect_role_protocol_v1.sha256').read_text().split()[0], 'protocol lock')
    audit.equal(freeze['protocol_sha256'], h.sha(root / 'effect_role_protocol_v1.json'), 'protocol binding')
    for name, digest in {**freeze['sources'], **freeze['historical']}.items(): audit.equal(h.sha(root / name), digest, name)
    commitment = h.read(root / 'effect_role_freeze_v1.json')
    audit.equal(set(commitment), set(freeze['artifacts']) | {'freeze.json'}, 'frozen inventory')
    for name, digest in commitment.items(): audit.equal(h.sha(data / name), digest, 'frozen/' + name)
    for name, item in freeze['artifacts'].items():
        audit.equal([h.sha(data / name), (data / name).stat().st_size], [item['sha256'], item['bytes']], 'artifact/' + name)
    audit.equal(h.canonical(freeze['runtime']), freeze['runtime_sha256'], 'runtime hash')
    audit.check({k: freeze['runtime'][k] for k in config['execution']['runtime']} == config['execution']['runtime'], 'runtime versions')
    for receipt in (trained, manifest):
        audit.check(receipt['complete'] is True and receipt['runtime'] == freeze['runtime'] and
            receipt['freeze_sha256'] == h.sha(data / 'freeze.json'), 'stage completion/runtime/binding')
    audit.check(manifest['oracle_opened'] is False and manifest['training_sha256'] == h.sha(fitted / 'training.json'), 'raw binding')
    for receipt, attempt, names in ((trained, h.read(fitted / 'attempt.json'), ('source_publication', 'runtime', 'freeze_sha256')),
            (manifest, h.read(traces / 'attempt.json'), ('weights_publication', 'runtime', 'freeze_sha256', 'training_sha256'))):
        audit.check(all(receipt[k] == attempt[k] for k in names), 'stage attempt identity')
    observed = {k: h.read(data / f'{k}-inputs.json.xz') for k in ('rehearsal', 'teach')}
    audit.equal(trained['training_input_sha256'], {k: h.canonical(v) for k, v in observed.items()}, 'observed TRAIN binding')
    audit.equal({k: sum(len(e['utterances']) for e in v['episodes']) for k, v in observed.items()}, config['training_forecasts'], 'TRAIN counts')
    audit.equal(h.sha(data / 'rehearsal-inputs.json.xz'), h.sha(root / 'data/saturation-v1/train-inputs.json.xz'), 'exact rehearsal bytes')
    expected_keys = {f'{arm}/{seed}' for arm in ARMS for seed in SEEDS}
    require(set(trained['reports']) == set(trained['checkpoints']) == expected_keys, '15 fit inventory')
    parents = h.read(root / 'data/coordinate-fit-v1/checkpoints.json.xz')['checkpoints']
    require(set(freeze['world_checkpoints']) == {f'{law}/{seed}' for law in LAWS for seed in SEEDS}, 'ten native checkpoints')
    for key, item in freeze['world_checkpoints'].items():
        path = root / 'data/set-acquisition-fit-v2' / item['file']; world = h.read(path)
        audit.equal([h.sha(path), *h.fingerprint(world['state'])], [item['sha256'], item['state_sha256'], 562], 'immutable world/' + key)
    for key in sorted(expected_keys):
        arm, seed = key.split('/'); item, report = trained['checkpoints'][key], trained['reports'][key]
        path = fitted / item['file']; record = h.read(path)
        audit.equal([h.sha(path), path.stat().st_size], [item['sha256'], item['bytes']], 'checkpoint/' + key)
        audit.equal([record['arm'], record['seed'], *h.fingerprint(record['state']), record['state_sha256']],
            [arm, int(seed), report['final_sha256'], config['parameters'][arm], report['final_sha256']], 'actual fitted state/' + key)
        audit.equal(report, h.read(fitted / f'fit-{arm}-{seed}.json'), 'fit report copy/' + key)
        audit.check(report['world_unchanged'] is True and report['world_sha256'] == freeze['world_checkpoints'][f'nand/{seed}']['state_sha256'], 'world receipt')
        audit.equal(report['settings'], config['fit'], 'fit recipe'); audit.equal(report['updates'], config['fit']['updates'], 'fit exposure')
        audit.equal(report['parameters'], config['parameters'][arm], 'parameter budget')
        audit.equal(report['observed_forecasts_per_update'], config['training_forecasts'], 'tape exposure')
        audit.check(report['fresh_optimizer'] is True, 'fresh optimizer')
        audit.equal(report['optimizer'], {'name': 'Adam', 'betas': [.9, .999], 'eps': 1e-8, 'weight_decay': 0., 'amsgrad': False}, 'optimizer recipe')
        if arm != 'text_only':
            initial = json.loads(json.dumps(parents[f'coordinates/{seed}']['state']))
            for name in initial:
                if name.startswith('order.'): initial[name] += [[[0.]], [[0.]]] if name.endswith('weight') else [0., 0.]
            audit.equal(h.fingerprint(initial), (report['initial_sha256'], 92), 'actual copied88+zero4/' + key)
    registry = h.read(data / 'lexical-registry.json')
    saved_lexical = h.read(traces / 'lexical-identities.json')
    lexical = lexical_receipt(registry, [observed[k] for k in ('rehearsal', 'teach')], config['unknown_tokens'], saved_lexical)
    audit.equal(saved_lexical, lexical, 'known/unknown identity control arithmetic')
    inputs = {(law, bank): h.read(data / f'{law}-inputs.json.xz') if bank == 'fresh' else
        h.read(root / f'data/{bank[:-10]}-v1/{law}-inputs.json.xz') for law in LAWS for bank in
        ('fresh', *(b + '_retention' for b in BANKS))}
    for law in LAWS:
        fresh = inputs[law, 'fresh']['episodes']
        audit.equal([len(fresh), sum(len(e['utterances']) for e in fresh)],
                    [config['fresh_episodes_per_law'], config['fresh_forecasts_per_law']], 'fresh input counts/' + law)
    schedules = [(law, seed, arm, bank) for law in LAWS for seed in SEEDS for arm in ARMS for bank in
                 (('fresh', *(b + '_retention' for b in BANKS)) if arm == 'grounded' else ('fresh',))]
    filenames = {f'trace-{law}-{seed}-{arm}-{bank}.json.xz' for law, seed, arm, bank in schedules}
    require(set(manifest['artifacts']) == filenames | {'lexical-identities.json'}, 'raw file inventory')
    require({p.name for p in traces.glob('trace-*.json.xz')} == filenames, 'unexpected unmanifested forecasts')
    for name, item in manifest['artifacts'].items():
        audit.equal([h.sha(traces / name), (traces / name).stat().st_size], [item['sha256'], item['bytes']], 'raw bytes/' + name)
    def published(commit, paths):
        require(type(commit) is str and len(commit) == 40 and set(commit) <= set('0123456789abcdef'), 'publication commit')
        for path in paths:
            raw = subprocess.check_output(['git', '-C', str(repo), 'show', commit + ':' + path.relative_to(repo).as_posix()])
            audit.equal(hashlib.sha256(raw).hexdigest(), h.sha(path), 'published/' + str(path.relative_to(root)))
    published(trained['source_publication'], [data / 'freeze.json'])
    published(manifest['weights_publication'], [fitted / 'training.json', *[fitted / v['file'] for v in trained['checkpoints'].values()]])
    raw_publication = publication or subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
    published(raw_publication, [traces / 'manifest.json', *[traces / name for name in manifest['artifacts']]])
    def trace(law, seed, arm, bank):
        value = h.read(traces / f'trace-{law}-{seed}-{arm}-{bank}.json.xz'); observed = inputs[law, bank]
        require((value['law'], value['seed'], value['arm'], value['bank']) == (law, seed, arm, bank) and
            value['input_sha256'] == h.canonical(observed) and value['state_sha256'] == trained['reports'][f'{arm}/{seed}']['final_sha256']
            and all(value[k] == manifest[k] for k in ('weights_publication', 'runtime', 'freeze_sha256', 'training_sha256')), 'trace provenance')
        records = {r['id']: r for r in observed['episodes']}; require(len(records) == len(observed['episodes']), 'observed duplicate identity')
        return index_rows(value['points'], records, arm, bank == 'fresh')
    totals = {'fresh': 0, 'retention': 0}
    for law, seed, arm, bank in schedules:
        totals['fresh' if bank == 'fresh' else 'retention'] += sum(map(len, trace(law, seed, arm, bank).values()))
    audit.equal(totals, {'fresh': config['fresh_saved_forecasts'], 'retention': config['retention_saved_forecasts']}, 'all raw counts')
    require(audit.discrepancy_count == 0, 'pre-score evidence verification failed before evaluator parsing')
    checks, details, expected = {}, {}, None
    if not pre_score:
        score_manifest, saved_decision = h.read(scored / 'manifest.json'), h.read(scored / 'decision.json')
        audit.check(score_manifest['runtime'] == freeze['runtime'] and score_manifest['trace_manifest_sha256'] == h.sha(traces / 'manifest.json'), 'score runtime/raw binding')
        audit.equal(score_manifest['traces_publication'], raw_publication, 'scored publication matches audited raw commit')
        expected_reports = {f'{law}/{seed}' for law in LAWS for seed in SEEDS}
        audit.equal(set(score_manifest['reports']), expected_reports, 'score report inventory')
        for law in LAWS:
            evaluator = h.read(data / f'{law}-evaluator.json.xz'); records, gold, pairs = inventory(inputs[law, 'fresh'], evaluator)
            forecasts = [f for g in gold.values() for f in g['forecasts']]
            audit.equal([sum(len(f['possible_worlds']) == 1 for f in forecasts), sum(len(f['possible_worlds']) > 1 for f in forecasts),
                sum(c['held_layout'] for g in gold.values() for c in g['cells']), len(evaluator['goal_groups']),
                sum(len(g['goals']) for g in evaluator['goal_groups'])], [config[k] for k in ('identifiable_forecasts_per_law',
                'ambiguous_forecasts_per_law', 'held_new_word_forecasts_per_law', 'goal_groups_per_law', 'goal_decisions_per_law')],
                'conditional/held/goal counts/' + law)
            for seed in SEEDS:
                key = f'{law}/{seed}'; print('Audit ' + key, flush=True)
                path = scored / f'report-{law}-{seed}.json.xz'; audit.equal(h.sha(path), score_manifest['reports'][key]['sha256'], 'score bytes/' + key)
                saved = h.read(path); points = {arm: measured(trace(law, seed, arm, 'fresh')['canonical'], records, gold) for arm in ARMS}
                points['masked'] = measured(trace(law, seed, 'grounded', 'fresh')['masked'], records, gold)
                reports = {arm: summary(rows, pairs) for arm, rows in points.items()}
                goal_reports = {arm: goals(rows, evaluator['goal_groups']) for arm, rows in points.items()}
                fresh_checks, comparisons = decision_checks(reports, goal_reports, config['analysis'])
                for arm, rows in points.items():
                    compare_subset(audit, saved['fresh']['reports'][arm], reports[arm], key + '/' + arm)
                    audit.equal(saved['fresh']['points'][arm], [{k: v for k, v in p.items() if k not in ('probabilities', 'logp')}
                        for p in rows.values()], 'all fresh point metrics/' + arm)
                    audit.equal(saved['fresh']['goals'][arm], goal_reports[arm], 'all goal records/' + arm)
                audit.equal(saved['fresh']['comparisons'], comparisons, 'goal control gains/' + key)
                audit.check(saved['fresh']['checks'] == fresh_checks and saved['fresh']['passed'] == all(fresh_checks.values()), 'fresh decision/' + key)
                checks[key] = fresh_checks
                for bank in BANKS:
                    full = bank + '_retention'; observed = inputs[law, full]; cases = {r['id']: r for r in observed['episodes']}
                    archive = h.read(root / f'results/set-acquisition-v2/traces/trace-{law}-{seed}-acquired-{full}.json.xz')
                    require(archive['input_sha256'] == h.canonical(observed), 'archive observed input')
                    result = retained(trace(law, seed, 'grounded', full)['canonical'],
                        index_rows(archive['points'], cases, fresh=False, archived=True)['canonical'], cases, config['analysis'])
                    audit.equal(saved['retention'][full], result, 'all retention records/' + key + '/' + bank)
                    checks[key].update({full + '/' + k: v for k, v in result['checks'].items()})
                details[key] = {'checks': checks[key], 'fresh': reports['grounded']['all'], 'goals': goal_reports['grounded']['all']}
        passed = all(all(v.values()) for v in checks.values()) and all(lexical['checks'].values())
        expected = 'DEVELOPMENT_G3_COMPLETE' if passed else 'REVISE_EFFECT_ROLE_GROUNDING'
        audit.check(saved_decision['checks'] == checks and saved_decision['lexical_identity_checks'] == lexical['checks'] and
            saved_decision['decision'] == expected and saved_decision['g3_complete'] == passed and saved_decision['execution_complete'] is True and
            saved_decision['scientific_admission'] is False and saved_decision['next_stage'] == ('G4' if passed else 'G3'), 'exact complete decision')
    audit.check(not any((p / 'failure.json').exists() for p in (fitted, traces, *([] if pre_score else [scored]))), 'no interrupted stages')
    require('torch' not in sys.modules and not any(k.endswith(('effect_role_scoring', 'effect_role_model')) for k in sys.modules), 'model/scorer imported')
    return {'version': 'effect-role-saved-audit-v1', 'mode': 'pre-score' if pre_score else 'full', 'decision': expected,
        'audit_passed': audit.discrepancy_count == 0, 'check_count': audit.checks, 'discrepancy_count': audit.discrepancy_count,
        'discrepancies': audit.discrepancies, 'forecast_counts': totals, 'trace_files': len(filenames),
        'lexical_identity_checks': lexical['checks'], 'evaluator_targets_parsed': not pre_score, 'evaluator_bytes_hashed': True,
        'score_files_read': not pre_score, 'model_execution': False, 'original_scorer_execution': False, 'original_oracle_execution': False,
        'new_fits': 0, 'new_collections': 0, 'scientific_admission': False, 'independent_custody': False,
        'scope': 'Complete source/data/weights/raw publication and runtime bindings; all raw rows, dimensions, normalization and views. '
            'Full mode also checks every decision gate, critical world/action summaries, every fresh point metric, all goal and retention records. '
            'Saved conditional targets are validated but not regenerated. ECE, omitted rich summaries, timing and memory costs are not independently recomputed. '
            'Lexical receipts and deterministic registry assignments are checked without invoking the tokenizer. Publication is verified in local git objects, not remote custody.',
        'raw_publication': raw_publication, 'auditor_sha256': h.sha(__file__), 'helper_sha256': h.sha(h.__file__), 'details': details}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--pre-score', action='store_true'); parser.add_argument('--publication')
    args = parser.parse_args(); report = audit_saved(args.repo.resolve(), h.Audit(), args.pre_score, args.publication)
    with args.output.open('x') as stream: json.dump(h.safe(report), stream, sort_keys=True, indent=2, allow_nan=False); stream.write('\n')
    print(json.dumps({k: report[k] for k in ('decision', 'audit_passed', 'check_count', 'discrepancy_count')}), flush=True)
    return int(not report['audit_passed'])


if __name__ == '__main__': raise SystemExit(main())
