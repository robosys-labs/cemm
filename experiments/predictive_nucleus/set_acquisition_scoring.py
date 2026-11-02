"""Pure saved-record SET scoring; no fitting, inference or oracle execution.

All native actions remain in the denominator. Ambiguous contact outcomes retain
their actual exact errors but are assessed against the full conditional law.
"""
from collections import defaultdict
import math

from . import acceptance_contract as c
from .acceptance_scoring import _index, _point, _safe
from .bilingual_scoring import _difference, _logs
from .mixed_composition_run import _metrics, information_scores

ARMS = ('parent', 'acquired', 'no_change')


def _inventory(bundle):
    c.fields(bundle, ('inputs', 'oracle', 'information', 'cases'))
    inputs = c.validate_inputs(bundle['inputs']); oracle = bundle['oracle']
    gold = c.validate_oracle(oracle, inputs, {'oracle_sha256': c.digest(oracle),
        'oracle_source_sha256': oracle['source_sha256'],
        'information_law_sha256': oracle['information_law_sha256']})
    records = {e['episode']: e for e in inputs['episodes']}
    cases = {e['episode']: e for e in bundle['cases']}
    information = bundle['information']
    c.fields(information, ('version', 'input_sha256', 'source_sha256', 'information_law_sha256', 'episodes'))
    c.require(information['version'] == 'set-acquisition-v1-information' and all(
        information[k] == oracle[k] for k in ('input_sha256', 'source_sha256', 'information_law_sha256')),
        'information binding differs')
    infos = {e['episode']: e for e in information['episodes']}
    c.require(len(cases) == len(bundle['cases']) == len(records) and cases.keys() == records.keys() and
        len(infos) == len(information['episodes']) == len(records) and infos.keys() == records.keys(),
        'case/information inventory differs')
    planned, pairs, shared = {}, defaultdict(list), {}
    for identity, record in records.items():
        meta, target, info = cases[identity], gold[identity], infos[identity]
        c.fields(meta, ('episode', 'family', 'partition', 'lineage', 'pair_id', 'direction',
                       'entities', 'hidden_source_slot', 'requested', 'set_points'))
        c.fields(info, ('episode', 'forecasts'))
        c.require(c.identifier(meta['family']) and c.identifier(meta['lineage']) and meta['partition'] == 'held_out'
            and type(meta['entities']) is int and meta['entities'] == len(record['ids']) and
            type(meta['requested']) is int and meta['requested'] in (0, 1) and
            len(info['forecasts']) == len(record['actions']) and all(
            all(value is not None for value in row.values()) for row in record['observations']),
            'invalid complete observed case')
        set_points = {p['step']: p for p in meta['set_points']}
        c.require(len(set_points) == len(meta['set_points']) and set(set_points) == {
            t for t, a in enumerate(record['actions']) if a['kind'] == 'set'}, 'SET stratum inventory differs')
        for t, (action, expected) in enumerate(zip(record['actions'], info['forecasts'], strict=True)):
            c.fields(expected, ('information_key', 'possible_worlds', 'probabilities', 'surviving_modes'))
            support, probabilities, modes = (expected[k] for k in ('possible_worlds', 'probabilities', 'surviving_modes'))
            c.require(expected['information_key'] == target['information_keys'][t] and
                support == target['possible_worlds'][t] and type(probabilities) is list and
                len(probabilities) == len(support) and all(type(p) in (int, float) and math.isfinite(p)
                and p > 0 for p in probabilities) and abs(sum(probabilities) - 1.) <= 1e-12 and
                type(modes) is list and modes and modes == sorted(set(modes)) and
                all(type(m) is int and m in (0, 1) for m in modes) and len(support) <= len(modes) and
                all(abs(p * len(modes) - round(p * len(modes))) <= 1e-12 for p in probabilities),
                'conditional distribution differs from oracle')
            key, distribution = expected['information_key'], (support, probabilities)
            c.require(key not in shared or shared[key] == distribution, 'same information has different probabilities')
            shared[key] = distribution
            if t in set_points:
                p = set_points[t]; c.fields(p, ('step', 'prior', 'requested', 'changed'))
                prior = record['observations'][t][action['participants'][0]]
                c.require(type(p['step']) is int and type(p['prior']) is int and p['prior'] == prior and
                    type(p['requested']) is int and p['requested'] == action['value'] and
                    type(p['changed']) is bool and p['changed'] == (prior != action['value']) and len(support) == 1,
                    'SET strata or identifiability differ')
            planned[identity, t] = (record, meta, target, expected, set_points.get(t))
        if meta['pair_id'] is None:
            c.require(meta['direction'] is None and meta['hidden_source_slot'] is None, 'unpaired case has role metadata')
        else:
            c.require(c.identifier(meta['pair_id']) and type(meta['direction']) is int and meta['direction'] in (0, 1)
                and type(meta['hidden_source_slot']) is int and meta['hidden_source_slot'] in (0, 1), 'invalid role pair')
            pairs[meta['pair_id']].append(identity)
    for members in pairs.values():
        c.require(len(members) == 2 and {cases[e]['direction'] for e in members} == {0, 1}, 'incomplete role pair')
        left, right = (records[e] for e in members); lm, rm = (cases[e] for e in members)
        c.require(all(lm[k] == rm[k] for k in ('family', 'lineage', 'hidden_source_slot', 'requested')) and
            set(left['ids']) == set(right['ids']) and left['observations'][0] == right['observations'][0] and
            left['coverage'] == right['coverage'] and len(left['actions']) == len(right['actions']) and
            any(a['kind'] == 'contact' for a in left['actions']) and all(
            a == ({**b, 'participants': b['participants'][::-1]} if b['kind'] == 'contact' else b)
            for a, b in zip(left['actions'], right['actions'], strict=True)), 'role reversal differs')
    return planned, pairs


def _points(rows, planned, arm):
    indexed = {}
    for row in rows:
        c.fields(row, ('id', 'step', 'logp'))
        key = row['id'], row['step']
        c.require(type(row['step']) is int and key in planned and key not in indexed, 'duplicate/unplanned forecast')
        record, meta, gold, expected, set_point = planned[key]
        ids, t = sorted(record['ids']), row['step']; logs = _logs(row['logp'], 2 ** len(ids))
        point = _point({**{k: meta[k] for k in ('episode', 'family', 'partition', 'lineage', 'pair_id', 'direction')},
            'participant': arm, 'model_seed': None, 'step': t, 'ids': ids,
            'truth': [gold['truth'][t + 1][i] for i in ids], 'previous_truth': [gold['truth'][t][i] for i in ids],
            'possible_worlds': expected['possible_worlds'], 'information_key': expected['information_key'],
            'action_kind': record['actions'][t]['kind'], 'status': 'ANSWERED', 'log_probabilities': logs,
            'wall_seconds': None, 'cpu_seconds': None})
        previous = [_index([record['observations'][t][i] for i in ids])]
        point.update(information_scores(point, expected, previous))
        point['set'] = set_point
        indexed[key] = point
    c.require(indexed.keys() == planned.keys(), 'missing planned forecasts')
    return indexed


def _strata(points):
    return {'all': _metrics(points), 'identifiable': _metrics([p for p in points if p['answerable']]),
            'ambiguous': _metrics([p for p in points if not p['answerable']])}


def _whole(points, pairs):
    groups = defaultdict(list)
    for p in points: groups[p['episode']].append(p)
    records = [{'episode': identity, 'correct': all(p['correct'] for p in rows),
        'identifiable_points': sum(p['answerable'] for p in rows),
        'identifiable_correct': all(p['correct'] for p in rows if p['answerable'])}
        for identity, rows in sorted(groups.items())]
    indexed = {p['episode']: p for p in records}
    paired = [{'pair_id': identity, 'episodes': members,
        'correct': all(indexed[e]['correct'] for e in members),
        'identifiable_correct': all(indexed[e]['identifiable_correct'] for e in members)}
        for identity, members in sorted(pairs.items())]
    return {name: {'planned': len(rows), 'correct': sum(r['correct'] for r in rows),
        'identifiable_correct': sum(r['identifiable_correct'] for r in rows), 'records': rows}
        for name, rows in (('trajectories', records), ('role_pairs', paired))}


def _summary(index, pairs):
    points = list(index.values()); cells = defaultdict(list)
    for p in points:
        if p['set'] is not None:
            s = p['set']; cells[f"{p['family']}/n{len(p['ids'])}/prior{s['prior']}/request{s['requested']}/changed{int(s['changed'])}"].append(p)
    return {**_strata(points), **_whole(points, pairs),
        'by_family': {f: _strata([p for p in points if p['family'] == f]) for f in sorted({p['family'] for p in points})},
        'by_entity_count': {str(n): _strata([p for p in points if len(p['ids']) == n]) for n in sorted({len(p['ids']) for p in points})},
        'by_set_cell': {key: _metrics(rows) for key, rows in sorted(cells.items())},
        'set_by_changed': {str(v).lower(): _metrics([p for p in points if p['set'] is not None and p['set']['changed'] == v])
                           for v in (False, True)},
        'wrong_records': [[p['episode'], p['step']] for p in points if not p['correct']]}


def _deltas(candidate, reference):
    changes = {'repairs': [], 'regressions': [], 'identifiable_regressions': [], 'nll_worse': [],
               'nll_better': [], 'nll_undefined': [], 'probability_changes': []}
    for key, now in candidate.items():
        old = reference[key]; delta = _difference(now['nll'], old['nll'])
        if now['correct'] and not old['correct']: changes['repairs'].append(list(key))
        if old['correct'] and not now['correct']:
            changes['regressions'].append(list(key))
            if now['answerable']: changes['identifiable_regressions'].append(list(key))
        if delta is None: changes['nll_undefined'].append(list(key))
        elif delta: changes['nll_worse' if delta > 0 else 'nll_better'].append([*key, delta])
        differences = [abs(math.exp(a) - math.exp(b)) for a, b in
                       zip(now['log_probabilities'], old['log_probabilities'], strict=True)]
        changes['probability_changes'].append({'id': key[0], 'step': key[1], 'nll_change': delta,
            'max_abs_probability_change': max(differences), 'total_variation': math.fsum(differences) / 2})
    keys = [k for k, p in candidate.items() if p['set'] is not None and p['set']['changed']]
    mean = lambda index, selected: math.fsum(index[k]['nll'] / len(selected) for k in selected) if selected else None
    a, b = mean(candidate, keys), mean(reference, keys)
    changes.update(planned=len(candidate), mean_nll_change=_difference(mean(candidate, candidate), mean(reference, reference)),
        changed_set_planned=len(keys), changed_set_nll_gain=None if a is None else _difference(b, a))
    return changes


def analyze_native(bundle, traces, limits):
    """Score one law/seed's three complete traces; outer receipts bind that identity."""
    c.require(type(traces) is dict and set(traces) == set(ARMS), 'arm inventory differs')
    for key in ('identifiable_accuracy', 'mean_oracle_kl', 'max_ambiguous_total_variation',
                'max_set_mean_nll', 'min_changed_set_nll_gain'):
        c.require(type(limits[key]) in (int, float) and math.isfinite(limits[key]) and limits[key] >= 0, 'invalid score limit')
    planned, pairs = _inventory(bundle)
    indexed = {arm: _points(traces[arm], planned, arm) for arm in ARMS}
    reports = {arm: _summary(points, pairs) for arm, points in indexed.items()}
    comparisons = {arm: _deltas(indexed['acquired'], indexed[arm]) for arm in ('parent', 'no_change')}
    candidate = reports['acquired']; strata = [s for f in candidate['by_family'].values()
        for name, s in f.items() if name != 'all' and s['planned_points']]
    identifiable = [candidate['identifiable'], *[r['identifiable'] for r in candidate['by_family'].values()],
                    *[r['identifiable'] for r in candidate['by_entity_count'].values()]]
    cells = list(candidate['by_set_cell'].values())
    checks = {'complete_support': candidate['all']['support_coverage'] == 1.,
        'identifiable_accuracy': all(s['accuracy'] is not None and s['accuracy'] >= limits['identifiable_accuracy'] for s in identifiable),
        'supported_MAP_worlds': candidate['all']['map_outside_support'] == 0,
        'known_unchanged_preserved': candidate['all']['known_unchanged_errors'] == 0,
        'conditional_probability_quality': all(s['mean_oracle_kl'] is not None and s['mean_oracle_kl'] <= limits['mean_oracle_kl'] for s in strata),
        'ambiguous_no_collapse': not candidate['ambiguous']['planned_points'] or
            candidate['ambiguous']['max_oracle_total_variation'] <= limits['max_ambiguous_total_variation'],
        'each_set_cell': bool(cells) and all(s['accuracy'] >= limits['identifiable_accuracy'] and
            s['mean_nll'] <= limits['max_set_mean_nll'] and s['known_unchanged_errors'] == 0 for s in cells),
        'identifiable_trajectories': candidate['trajectories']['identifiable_correct'] == candidate['trajectories']['planned'],
        'identifiable_role_pairs': candidate['role_pairs']['identifiable_correct'] == candidate['role_pairs']['planned'],
        'parent_identifiable_retention': not comparisons['parent']['identifiable_regressions'],
        **{arm + '_changed_set_gain': comparisons[arm]['changed_set_nll_gain'] is not None and
            comparisons[arm]['changed_set_nll_gain'] >= limits['min_changed_set_nll_gain'] for arm in ('parent', 'no_change')}}
    retained = ('episode', 'step', 'action_kind', 'answerable', 'correct', 'map_world', 'nll', 'brier',
                'oracle_kl', 'oracle_total_variation', 'map_outside_support', 'known_unchanged_errors', 'set')
    return _safe({'passed': all(checks.values()), 'checks': checks, 'reports': reports,
        'comparisons': comparisons, 'points': {arm: [{k: p[k] for k in retained} for p in rows.values()]
                                            for arm, rows in indexed.items()}})
