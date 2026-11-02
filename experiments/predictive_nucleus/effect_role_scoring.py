"""Saved-record effect/role and goal scoring; no fitting or oracle execution.

The evaluator joins native action labels only after validating every named
forecast. Endpoint equivalence and globally taught lexical action identity are
different measurements. Goals reuse four parallel, same-prefix final forecasts;
their rewards never alter a forecast or use the realized hidden mode.
"""
from collections import defaultdict
import math

from . import acceptance_contract as c
from .acceptance_scoring import _index, _point, _safe
from .bilingual_contract import validate_inputs
from .bilingual_scoring import _difference, _logs
from .mixed_composition_run import _metrics, information_scores

ARMS = ('grounded', 'parser', 'text_only')
LIMITS = ('identifiable_accuracy', 'mean_oracle_kl', 'max_ambiguous_total_variation',
          'identifiable_trajectory_accuracy', 'identifiable_role_pair_accuracy',
          'action_accuracy', 'max_bilingual_total_variation', 'goal_optimal_accuracy',
          'mean_goal_regret', 'max_goal_regret', 'min_effect_sensitive_goal_gain',
          'min_effect_sensitive_goals')


def _limits(limits, names):
    c.require(type(limits) is dict and all(type(limits.get(k)) in (int, float) and
        math.isfinite(limits[k]) and limits[k] >= 0 for k in names), 'invalid score limits')


def _prefix(record):
    return {k: record[k] for k in ('entities', 'anchor', 'context')} | {
        'utterances': record['utterances'][:-1]}


def _key(record, step):
    return c.digest({k: record[k] for k in ('entities', 'anchor', 'context')} | {
        'past': record['utterances'][:step], 'text': record['utterances'][step]['text']})


def _menu(record, step):
    mentions = [record['entities'].index(w) for w in record['utterances'][step]['text'].split()
                if w in record['entities']]
    a, b = mentions
    return [[0, a, b, -1], [0, b, a, -1], [1, a, -1, 1], [1, b, -1, 1]]


def _inventory(bundle):
    c.fields(bundle, ('inputs', 'oracle', 'goal_groups'))
    records = {e['id']: e for e in validate_inputs(bundle['inputs'])['episodes']}
    oracle = bundle['oracle']
    c.fields(oracle, ('version', 'input_sha256', 'source_sha256', 'information_law_sha256', 'episodes'))
    c.require(oracle['version'] == 'effect-role-oracle-v1' and
        oracle['input_sha256'] == c.digest(bundle['inputs']), 'oracle/input binding differs')
    c.require(all(type(oracle[k]) is str and len(oracle[k]) == 64 and
        set(oracle[k]) <= set('0123456789abcdef') for k in
        ('source_sha256', 'information_law_sha256')), 'invalid oracle source binding')
    c.require(type(oracle['episodes']) is list and all(type(m) is dict and c.identifier(m.get('id'))
        for m in oracle['episodes']), 'invalid oracle episodes')
    gold = {m['id']: m for m in oracle['episodes']}
    c.require(len(gold) == len(oracle['episodes']) and gold.keys() == records.keys(),
              'oracle episode inventory differs')
    planned, shared = {}, {}
    pairs = {name: defaultdict(list) for name in ('role', 'bilingual', 'translation', 'effect')}
    fields = ('id', 'law', 'mode', 'family', 'lineage', 'direction', 'layout', 'context_mode',
        'phase', 'actions', 'action_indices', 'truth', 'forecasts', 'cells', 'role_pair_id',
        'bilingual_pair_id', 'translation_group_id', 'effect_pair_id', 'goal_group_id',
        'final_choice', 'shared_prefix_sha256')
    for identity, record in records.items():
        meta = gold[identity]; c.fields(meta, fields)
        steps, n = len(record['utterances']), len(record['entities'])
        c.require(meta['law'] in ('nand', 'nor') and type(meta['mode']) is int and meta['mode'] in (0, 1)
            and type(meta['direction']) is int and meta['direction'] in (0, 1) and
            type(meta['phase']) is int and meta['phase'] in (0, 1) and
            meta['layout'] in ('svo', 'osv', 'vos') and meta['context_mode'] in ('established', 'unresolved')
            and c.identifier(meta['family']) and c.identifier(meta['lineage']) and
            type(meta['final_choice']) is int and meta['final_choice'] in range(4), 'invalid oracle stratum')
        c.require(all(type(meta[k]) is list and len(meta[k]) == steps for k in
            ('actions', 'action_indices', 'truth', 'forecasts', 'cells')), 'oracle geometry differs')
        c.require(meta['shared_prefix_sha256'] == c.digest(_prefix(record)), 'prefix binding differs')
        for name in pairs:
            value = meta[{'translation': 'translation_group_id'}.get(name, name + '_pair_id')]
            if name == 'bilingual' and meta['layout'] == 'vos':
                c.require(value is None, 'held layout has bilingual pair'); continue
            c.require(c.identifier(value), 'invalid pairing identity'); pairs[name][value].append(identity)
        for t, event in enumerate(record['utterances']):
            index, expected, cell = meta['action_indices'][t], meta['forecasts'][t], meta['cells'][t]
            c.require(type(index) is int and index in range(4) and meta['actions'][t] == _menu(record, t)[index],
                      'oracle lexical action differs')
            c.require(meta['truth'][t] == event['reading'], 'oracle truth differs')
            c.fields(cell, ('word', 'layout', 'new_word', 'held_layout'))
            word = next(w for w in event['text'].split() if w not in record['entities'])
            c.require(cell['word'] == word and cell['layout'] in ('svo', 'osv', 'vos') and
                type(cell['new_word']) is bool and type(cell['held_layout']) is bool and
                cell['held_layout'] == (cell['new_word'] and cell['layout'] == 'vos'), 'invalid lexical cell')
            c.fields(expected, ('possible_worlds', 'probabilities', 'surviving_modes',
                               'equivalent_action_indices', 'information_key'))
            worlds, probs, modes, equiv = (expected[k] for k in
                ('possible_worlds', 'probabilities', 'surviving_modes', 'equivalent_action_indices'))
            c.require(type(worlds) is list and worlds and worlds == sorted(set(worlds)) and
                all(type(w) is int and 0 <= w < 2 ** n for w in worlds) and _index(meta['truth'][t]) in worlds
                and type(probs) is list and len(probs) == len(worlds) and all(type(p) in (int, float)
                and math.isfinite(p) and p > 0 for p in probs) and abs(math.fsum(probs) - 1) <= 1e-12,
                'invalid conditional oracle distribution')
            c.require(type(modes) is list and modes and modes == sorted(set(modes)) and
                all(type(m) is int and m in (0, 1) for m in modes) and meta['mode'] in modes and
                type(equiv) is list and equiv == sorted(set(equiv)) and index in equiv and
                all(type(a) is int and a in range(4) for a in equiv), 'invalid information alternatives')
            c.require(expected['information_key'] == _key(record, t), 'information prefix differs')
            conditional = {k: expected[k] for k in expected if k != 'information_key'}
            c.require(shared.setdefault(expected['information_key'], conditional) == conditional,
                      'same visible information has different oracle law')
            planned[identity, t] = record, meta, expected, cell
    c.require(len({m['law'] for m in gold.values()}) == 1, 'mixed-law score bundle')
    for name, groups in pairs.items():
        for members in groups.values():
            c.require(len(members) == (3 if name == 'translation' else 2), 'incomplete ' + name + ' group')
            first, *others = [gold[e] for e in members]
            for other in others:
                a, b = records[first['id']], records[other['id']]
                c.require(all(a[k] == b[k] for k in ('entities', 'anchor', 'context')) and
                    all(first[k] == other[k] for k in ('family', 'mode', 'context_mode', 'phase')),
                    'cross-stratum or unaligned ' + name + ' group')
                if name == 'role':
                    c.require({first['direction'], other['direction']} == {0, 1} and
                        first['layout'] == other['layout'] and first['final_choice'] == other['final_choice'],
                        'role group not reversed')
                    for t, (x, y) in enumerate(zip(first['actions'], other['actions'], strict=True)):
                        operands = _menu(a, t)[0][1:3]
                        c.require(set(operands) == set(_menu(b, t)[0][1:3]) and
                            (x == [0, y[2], y[1], -1] if x[0] == 0 else
                             y[0] == 1 and x[1] != y[1] and {x[1], y[1]} == set(operands)),
                            'role actions not reversed')
                elif name == 'effect':
                    c.require(_prefix(a) == _prefix(b) and first['layout'] == other['layout'] and
                        first['direction'] == other['direction'] and
                        {first['actions'][-1][0], other['actions'][-1][0]} == {0, 1} and
                        _menu(a, len(a['utterances']) - 1) == _menu(b, len(b['utterances']) - 1),
                        'effect alternatives do not share mention order and prefix')
                else:
                    c.require(first['direction'] == other['direction'] and first['final_choice'] == other['final_choice']
                        and first['actions'] == other['actions'] and first['truth'] == other['truth'],
                        'translated messages differ physically')
                    for x, y in zip(first['forecasts'], other['forecasts'], strict=True):
                        c.require(all(x[k] == y[k] for k in ('possible_worlds', 'probabilities', 'surviving_modes')),
                                  'translated conditional laws differ')
            if name in ('bilingual', 'translation'):
                c.require({gold[e]['layout'] for e in members} ==
                    ({'svo', 'osv'} if name == 'bilingual' else {'svo', 'osv', 'vos'}), 'duplicate translated layout')
    groups = _goal_inventory(bundle['goal_groups'], records, gold)
    return planned, pairs, groups


def _goal_inventory(groups, records, gold):
    c.require(type(groups) is list and groups, 'missing goal inventory')
    seen, episodes, goals = set(), set(), set()
    for group in groups:
        c.fields(group, ('id', 'episodes', 'participants', 'before', 'shared_prefix_sha256', 'goals'))
        identity, members, participants = group['id'], group['episodes'], group['participants']
        c.require(c.identifier(identity) and identity not in seen and type(members) is list and len(members) == 4
            and len(set(members)) == 4 and all(e in records and e not in episodes for e in members),
            'invalid goal group inventory')
        seen.add(identity); episodes.update(members)
        record = records[members[0]]; n = len(record['entities'])
        c.require(type(participants) is list and len(participants) == 2 and len(set(participants)) == 2 and
            all(type(i) is int and 0 <= i < n for i in participants), 'invalid goal participants')
        before = record['utterances'][-2]['reading'] if len(record['utterances']) > 1 else record['context'][-1]['reading']
        c.require(group['before'] == before and group['shared_prefix_sha256'] == c.digest(_prefix(record)),
                  'goal prefix/previous reading differs')
        a, b = participants
        menu = [[0, a, b, -1], [0, b, a, -1], [1, a, -1, 1], [1, b, -1, 1]]
        for choice, episode in enumerate(members):
            meta = gold[episode]
            c.require(meta['goal_group_id'] == identity and meta['final_choice'] == choice and
                meta['actions'][-1] == menu[choice] and _prefix(records[episode]) == _prefix(record) and
                all(meta[k] == gold[members[0]][k] for k in
                    ('family', 'mode', 'direction', 'layout', 'context_mode', 'phase')),
                'goal alternatives differ before the hypothetical action')
        c.require(type(group['goals']) is list and len(group['goals']) == 4, 'four two-bit goals required')
        targets = set()
        for goal in group['goals']:
            c.fields(goal, ('id', 'target_bits', 'oracle_utilities', 'optimal_choices', 'max_utility',
                            'attainable', 'effect_sensitive', 'set_required', 'contact_required'))
            target = goal['target_bits']
            c.require(c.identifier(goal['id']) and goal['id'] not in goals and type(target) is list and
                len(target) == 2 and all(type(v) is int and v in (0, 1) for v in target), 'invalid goal identity/target')
            goals.add(goal['id']); targets.add(tuple(target))
            bits = list(before)
            for i, value in zip(participants, target, strict=True): bits[i] = value
            world = _index(bits)
            utilities = [dict(zip(gold[e]['forecasts'][-1]['possible_worlds'],
                                 gold[e]['forecasts'][-1]['probabilities'], strict=True)).get(world, 0.) for e in members]
            maximum = max(utilities); contact, setting = max(utilities[:2]), max(utilities[2:])
            c.require(type(goal['oracle_utilities']) is list and len(goal['oracle_utilities']) == 4 and
                all(type(u) in (int, float) and math.isfinite(u) and abs(u - v) <= 1e-12
                    for u, v in zip(goal['oracle_utilities'], utilities, strict=True)) and
                type(goal['max_utility']) in (int, float) and goal['max_utility'] == maximum and
                goal['optimal_choices'] == [i for i, u in enumerate(utilities) if u == maximum],
                'goal oracle utility differs from the conditional worlds')
            expected = {'attainable': maximum > 0, 'effect_sensitive': contact != setting,
                        'set_required': setting > contact, 'contact_required': contact > setting}
            c.require(all(type(goal[k]) is bool and goal[k] == v for k, v in expected.items()),
                      'goal sensitivity declaration differs')
        c.require(targets == {(0, 0), (0, 1), (1, 0), (1, 1)}, 'goal targets incomplete')
    c.require(episodes == records.keys(), 'missing goal alternatives')
    return groups


def _trace(rows, planned, arm):
    c.require(type(rows) is list, 'trace must be a list')
    views = ('canonical', 'masked') if arm == 'grounded' else ('canonical',)
    indexed = {view: {} for view in views}
    for row in rows:
        c.fields(row, ('id', 'step', 'view', 'logp', 'action_logp'))
        c.require(c.identifier(row['id']) and type(row['step']) is int and row['view'] in views,
                  'invalid forecast identity/view')
        key, view = (row['id'], row['step']), row['view']
        c.require(key in planned and key not in indexed[view], 'duplicate/unplanned forecast')
        record, meta, expected, cell = planned[key]; t = row['step']
        previous = record['context'][-1]['reading'] if t == 0 else record['utterances'][t - 1]['reading']
        c.require((row['action_logp'] is None) == (arm == 'text_only'), 'control action distribution nullness differs')
        actions = None if row['action_logp'] is None else _logs(row['action_logp'], 4)
        point = _point({'participant': arm + '/' + view, 'model_seed': None, 'episode': row['id'], 'step': t,
            'family': meta['family'], 'partition': 'held_out', 'lineage': meta['lineage'],
            'pair_id': meta['role_pair_id'], 'direction': meta['direction'], 'ids': record['entities'],
            'truth': meta['truth'][t], 'previous_truth': previous,
            'possible_worlds': expected['possible_worlds'], 'information_key': expected['information_key'],
            'action_kind': 'contact' if meta['actions'][t][0] == 0 else 'set', 'status': 'ANSWERED',
            'log_probabilities': _logs(row['logp'], 2 ** len(record['entities'])),
            'wall_seconds': None, 'cpu_seconds': None})
        point.update(information_scores(point, expected, [_index(previous)]))
        best = None if actions is None else max(range(4), key=actions.__getitem__)
        point.update(cell, context_mode=meta['context_mode'], action_index=meta['action_indices'][t],
            map_action=best, action_correct=None if best is None else best == meta['action_indices'][t],
            equivalent_action_indices=expected['equivalent_action_indices'],
            endpoint_action_compatible=None if best is None else best in expected['equivalent_action_indices'])
        indexed[view][key] = point
    c.require(all(rows.keys() == planned.keys() for rows in indexed.values()), 'missing named forecast points')
    return indexed


def _strata(points):
    return {'all': _metrics(points), 'identifiable': _metrics([p for p in points if p['answerable']]),
            'ambiguous': _metrics([p for p in points if not p['answerable']])}


def _actions(points):
    values = [p['action_correct'] for p in points if p['action_correct'] is not None]
    return {'planned': len(points), 'produced': len(values), 'correct': sum(values),
            'accuracy': sum(values) / len(points) if points and len(values) == len(points) else None,
            'endpoint_compatible': sum(p['endpoint_action_compatible'] is True for p in points)}


def _whole(index, pairs):
    episodes = defaultdict(list)
    for point in index.values(): episodes[point['episode']].append(point)
    trajectories = {e: {'episode': e, 'correct': all(p['correct'] for p in rows),
        'identifiable_points': sum(p['answerable'] for p in rows),
        'identifiable_correct': all(p['correct'] for p in rows if p['answerable'])}
        for e, rows in sorted(episodes.items())}
    paired = [{'pair_id': name, 'episodes': members,
        'correct': all(trajectories[e]['correct'] for e in members),
        'identifiable_points': sum(trajectories[e]['identifiable_points'] for e in members),
        'identifiable_correct': all(trajectories[e]['identifiable_correct'] for e in members)}
        for name, members in sorted(pairs.items())]
    def summarize(rows):
        identifiable = [r for r in rows if r['identifiable_points']]
        return {'planned': len(rows), 'correct': sum(r['correct'] for r in rows),
            'identifiable_planned': len(identifiable),
            'identifiable_correct': sum(r['identifiable_correct'] for r in identifiable),
            'identifiable_accuracy': sum(r['identifiable_correct'] for r in identifiable) / len(identifiable)
                if identifiable else None, 'records': rows}
    return {'trajectories': summarize(list(trajectories.values())), 'role_pairs': summarize(paired)}


def _twins(index, pairs):
    rows, steps_by_episode = [], defaultdict(list)
    for e, t in index: steps_by_episode[e].append(t)
    for name, members in sorted(pairs.items()):
        steps = sorted(steps_by_episode[members[0]])
        for t in steps:
            a, b = (index[e, t] for e in members)
            tv = .5 * math.fsum(abs(math.exp(x) - math.exp(y)) for x, y in
                               zip(a['log_probabilities'], b['log_probabilities'], strict=True))
            rows.append({'pair_id': name, 'step': t, 'episodes': members,
                         'total_variation': tv, 'map_equal': a['map_world'] == b['map_world']})
    return {'planned': len(rows), 'max_total_variation': max(r['total_variation'] for r in rows) if rows else None,
            'mean_total_variation': math.fsum(r['total_variation'] / len(rows) for r in rows) if rows else None,
            'map_equal': sum(r['map_equal'] for r in rows), 'records': rows}


def _summary(index, pairs):
    points = list(index.values()); grouped = {}
    for name, key in (('family', lambda p: p['family']), ('layout', lambda p: p['layout']),
                     ('effect', lambda p: p['action_kind']),
                     ('lexicon', lambda p: 'new' if p['new_word'] else 'old'),
                     ('cell', lambda p: '/'.join((p['family'], p['layout'], p['action_kind'],
                                                'new' if p['new_word'] else 'old')))):
        groups = defaultdict(list)
        for point in points: groups[key(point)].append(point)
        grouped['by_' + name] = {k: _strata(v) for k, v in sorted(groups.items())}
    words = defaultdict(list)
    for point in points: words[point['word'] + '/' + point['layout']].append(point)
    return {**_strata(points), **grouped, **_whole(index, pairs['role']),
        'bilingual': _twins(index, pairs['bilingual']), 'actions': _actions(points),
        'actions_by_lexicon': {name: _actions([p for p in points if p['new_word'] == new])
                               for name, new in (('new', True), ('old', False))},
        'by_taught_lexeme_layout': {k: _actions(v) for k, v in sorted(words.items())}}


def _goal_scores(index, groups):
    rows, finals = [], {}
    for (episode, t), point in index.items():
        if episode not in finals or t > finals[episode]['step']: finals[episode] = point
    for group in groups:
        final = [finals[episode] for episode in group['episodes']]
        for goal in group['goals']:
            target = list(group['before'])
            for i, bit in zip(group['participants'], goal['target_bits'], strict=True): target[i] = bit
            logs = [p['log_probabilities'][_index(target)] for p in final]
            utilities = [math.exp(value) for value in logs]
            choice = max(range(4), key=logs.__getitem__)  # First alternative wins exact log-space ties.
            actual = goal['oracle_utilities'][choice]
            rows.append({**goal, 'group_id': group['id'], 'family': final[0]['family'],
                'layout': final[0]['layout'], 'target_world': _index(target), 'predicted_utilities': utilities,
                'predicted_log_utilities': logs,
                'chosen': choice, 'optimal': choice in goal['optimal_choices'],
                'expected_utility': actual, 'regret': goal['max_utility'] - actual})
    def summarize(selected):
        return {'planned': len(selected), 'optimal': sum(r['optimal'] for r in selected),
            'optimal_accuracy': sum(r['optimal'] for r in selected) / len(selected) if selected else None,
            'mean_regret': math.fsum(r['regret'] / len(selected) for r in selected) if selected else None,
            'max_regret': max(r['regret'] for r in selected) if selected else None}
    report = {name: summarize(rows if name == 'all' else [r for r in rows if r[name]])
              for name in ('all', 'attainable', 'effect_sensitive', 'set_required', 'contact_required')}
    report['impossible'] = summarize([r for r in rows if not r['attainable']])
    for key in ('family', 'layout'):
        report['by_' + key] = {value: summarize([r for r in rows if r[key] == value])
                               for value in sorted({r[key] for r in rows})}
    return {**report, 'records': rows}


def analyze(bundle, traces, limits):
    """Score one law/seed. Invalid evidence raises; scientific failures are reports."""
    _limits(limits, LIMITS)
    c.require(type(limits['min_effect_sensitive_goals']) is int and limits['min_effect_sensitive_goals'] > 0,
              'positive integral effect-sensitive inventory bound required')
    c.require(type(traces) is dict and set(traces) == set(ARMS), 'arm inventory differs')
    planned, pairs, groups = _inventory(bundle)
    collected = {arm: _trace(traces[arm], planned, arm) for arm in ARMS}
    indexed = {arm: views['canonical'] for arm, views in collected.items()}
    indexed['masked'] = collected['grounded']['masked']
    reports = {arm: _summary(points, pairs) for arm, points in indexed.items()}
    goals = {arm: _goal_scores(points, groups) for arm, points in indexed.items()}
    candidate = reports['grounded']; target = goals['grounded']
    identifiable = [candidate['identifiable'], *[stratum['identifiable'] for key in
        ('by_family', 'by_layout', 'by_effect', 'by_lexicon', 'by_cell') for stratum in candidate[key].values()]]
    probability = [s for key in ('by_family', 'by_layout', 'by_effect', 'by_lexicon', 'by_cell')
                   for f in candidate[key].values() for name, s in f.items()
                   if name != 'all' and s['planned_points']]
    action_groups = [candidate['actions'], *candidate['actions_by_lexicon'].values(),
                     *candidate['by_taught_lexeme_layout'].values()]
    goal_names = ('attainable', 'effect_sensitive', 'set_required', 'contact_required')
    goal_groups = [target['all'], *[target[k] for k in goal_names if target[k]['planned']],
                   *target['by_family'].values(), *target['by_layout'].values()]
    improvements = {arm: {'planned': target['effect_sensitive']['planned'],
        'optimal_accuracy_gain': None if not target['effect_sensitive']['planned'] else
            target['effect_sensitive']['optimal_accuracy'] - goals[arm]['effect_sensitive']['optimal_accuracy']}
        for arm in ('masked', 'text_only')}
    checks = {'complete_support': candidate['all']['support_coverage'] == 1.,
        'identifiable_accuracy': all(s['accuracy'] >= limits['identifiable_accuracy']
                                    for s in identifiable if s['planned_points']),
        'supported_MAP_worlds': candidate['all']['map_outside_support'] == 0,
        'known_unchanged_preserved': candidate['all']['known_unchanged_errors'] == 0,
        'conditional_probability_quality': all(s['mean_oracle_kl'] <= limits['mean_oracle_kl'] for s in probability),
        'ambiguous_no_collapse': not candidate['ambiguous']['planned_points'] or
            candidate['ambiguous']['max_oracle_total_variation'] <= limits['max_ambiguous_total_variation'],
        'identifiable_trajectories': candidate['trajectories']['identifiable_accuracy'] is not None and
            candidate['trajectories']['identifiable_accuracy'] >= limits['identifiable_trajectory_accuracy'],
        'identifiable_role_pairs': candidate['role_pairs']['identifiable_accuracy'] is not None and
            candidate['role_pairs']['identifiable_accuracy'] >= limits['identifiable_role_pair_accuracy'],
        'globally_taught_action_identity': all(s['accuracy'] is not None and s['accuracy'] >= limits['action_accuracy']
                                              for s in action_groups),
        'bilingual_probability_agreement': candidate['bilingual']['max_total_variation'] is not None and
            candidate['bilingual']['max_total_variation'] <= limits['max_bilingual_total_variation'],
        'goal_stratum_inventory': all(target[k]['planned'] > 0 for k in goal_names),
        'goal_optimal_choices': all(s['optimal_accuracy'] >= limits['goal_optimal_accuracy'] for s in goal_groups),
        'goal_mean_regret': all(s['mean_regret'] <= limits['mean_goal_regret'] for s in goal_groups),
        'goal_max_regret': all(s['max_regret'] <= limits['max_goal_regret'] for s in goal_groups),
        'effect_sensitive_goal_inventory': target['effect_sensitive']['planned'] >= limits['min_effect_sensitive_goals'] and
            target['set_required']['planned'] > 0 and target['contact_required']['planned'] > 0,
        **{arm + '_goal_gain': r['optimal_accuracy_gain'] is not None and
            r['optimal_accuracy_gain'] >= limits['min_effect_sensitive_goal_gain'] for arm, r in improvements.items()}}
    retained = ('episode', 'step', 'family', 'layout', 'word', 'new_word', 'held_layout', 'action_kind',
        'answerable', 'correct', 'map_world', 'nll', 'brier', 'oracle_kl', 'oracle_total_variation',
        'outside_support_mass', 'map_outside_support', 'known_unchanged_errors', 'action_index',
        'map_action', 'action_correct', 'equivalent_action_indices', 'endpoint_action_compatible')
    return _safe({'passed': all(checks.values()), 'checks': checks, 'reports': reports,
        'goals': goals, 'comparisons': improvements, 'points': {arm: [{k: p[k] for k in retained}
            for p in points.values()] for arm, points in indexed.items()}})


def retention(inputs, current, archive, limits):
    """Retain contact competence while permitting learned-language probabilities to change."""
    _limits(limits, ('max_retention_mean_nll',))
    records = {e['id']: e for e in validate_inputs(inputs)['episodes']}
    expected = {(e['id'], t) for e in records.values() for t in range(len(e['utterances']))}
    def indexed(rows, archived=False):
        c.require(type(rows) is list, 'retention rows must be a list')
        values, seen = {}, set()
        for row in rows:
            action = 'order_logp' if archived else 'action_logp'
            c.fields(row, ('id', 'step', 'view', 'logp', action))
            c.require(c.identifier(row['id']) and type(row['step']) is int and type(row['view']) is str,
                      'invalid retention identity')
            key, view = (row['id'], row['step']), row['view']
            c.require(view == 'canonical' or archived and view in ('masked', 'swapped'), 'unexpected retention view')
            c.require(key in expected and (*key, view) not in seen, 'retention inventory differs')
            seen.add((*key, view)); actions = _logs(row[action], 2 if archived else 4)
            logs = _logs(row['logp'], 2 ** len(records[key[0]]['entities']))
            if view == 'canonical': values[key] = logs, actions
        c.require(values.keys() == expected, 'missing retention rows')
        return values
    now, before = indexed(current), indexed(archive, True)
    rows = []
    for key in sorted(expected):
        (point, action), (old, old_action) = now[key], before[key]
        target = _index(records[key[0]]['utterances'][key[1]]['reading'])
        world, previous = (max(range(len(values)), key=values.__getitem__) for values in (point, old))
        nll, previous_nll = -point[target], -old[target]
        action_map, previous_action = (max(range(len(values)), key=values.__getitem__)
                                       for values in (action, old_action))
        action_change = [math.exp(a) - math.exp(b) for a, b in
                         zip(action, [*old_action, -math.inf, -math.inf], strict=True)]
        differences = [abs(math.exp(a) - math.exp(b)) for a, b in zip(point, old, strict=True)]
        distances = [0. if a == b else math.inf if math.isinf(a) or math.isinf(b) else abs(a - b)
                     for a, b in zip(point, old, strict=True)]
        rows.append({'id': key[0], 'step': key[1], 'correct': world == target, 'archived_correct': previous == target,
            'regression': previous == target and world != target, 'repair': previous != target and world == target,
            'map_world': world, 'archived_map_world': previous, 'world_map_changed': world != previous,
            'map_action': action_map, 'archived_map_action': previous_action,
            'action_map_changed': action_map != previous_action, 'action_probability_changes': action_change,
            'candidate_set_mass': math.exp(action[2]) + math.exp(action[3]),
            'logp_equal': point == old, 'nll': nll, 'archived_nll': previous_nll,
            'nll_change': _difference(nll, previous_nll), 'max_logp_change': max(distances),
            'true_probability_change': math.exp(point[target]) - math.exp(old[target]),
            'max_abs_probability_change': max(differences), 'total_variation': math.fsum(differences) / 2})
    mean = lambda name: math.fsum(r[name] / len(rows) for r in rows)
    nll, archived_nll = mean('nll'), mean('archived_nll')
    checks = {'no_exact_regressions': not any(r['regression'] for r in rows),
              'retention_action_MAP': not any(r['action_map_changed'] for r in rows),
              'retention_mean_nll': nll <= limits['max_retention_mean_nll']}
    return _safe({'planned': len(rows), 'correct': sum(r['correct'] for r in rows),
        'archived_correct': sum(r['archived_correct'] for r in rows),
        **{name: [[r['id'], r['step']] for r in rows if r[field]] for name, field in
           (('regressions', 'regression'), ('repairs', 'repair'), ('world_map_changes', 'world_map_changed'),
            ('action_map_changes', 'action_map_changed'))},
        'exact_world_vectors': sum(r['logp_equal'] for r in rows), 'mean_nll': nll,
        'archived_mean_nll': archived_nll, 'mean_nll_change': _difference(nll, archived_nll),
        'max_logp_change': max(r['max_logp_change'] for r in rows),
        'mean_candidate_set_mass': mean('candidate_set_mass'),
        'max_candidate_set_mass': max(r['candidate_set_mass'] for r in rows),
        'checks': checks, 'passed': all(checks.values()), 'points': rows})
