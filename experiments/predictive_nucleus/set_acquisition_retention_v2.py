"""Prospective saved-record retention; numerical failures remain complete reports.

Tensor identity and publication are checked by the runner. This module neither
executes a model nor opens an evaluator. Numerical bounds never permit an exact
world/order MAP change; malformed or incomplete evidence remains an error.
"""
import math

from . import acceptance_contract as c
from .acceptance_scoring import _index, _safe
from .bilingual_contract import validate_inputs
from .bilingual_scoring import _difference, _logs


def _distance(left, right):
    # Equal zeros in probability space are equal, not abs(-inf - -inf) = NaN.
    return 0. if left == right else math.inf if math.isinf(left) or math.isinf(right) else abs(left - right)


def retention(inputs, current, archive, analysis):
    """Compare every canonical point, returning failed acceptance checks normally.

The two limits are absolute log-probability bounds, without a relative term.
MAP is the first maximizing index, matching the archived retention convention.
Archive-only masked/swapped views are validated but are not scored a second time.
"""
    c.require(type(analysis) is dict, 'retention limits required')
    names = ('max_retention_logp_change', 'max_retention_order_logp_change')
    c.require(all(type(analysis.get(k)) in (int, float) and math.isfinite(analysis[k]) and
                  analysis[k] >= 0 for k in names), 'invalid absolute retention limit')
    world_limit, order_limit = (analysis[k] for k in names)
    inputs = validate_inputs(inputs)
    records = {r['id']: r for r in inputs['episodes']}
    expected = {(r['id'], t) for r in records.values() for t in range(len(r['utterances']))}

    def indexed(rows, archived=False):
        c.require(type(rows) is list, 'retention rows must be a list')
        values, seen = {}, set()
        for row in rows:
            c.fields(row, ('id', 'step', 'view', 'logp', 'order_logp'))
            c.require(c.identifier(row['id']) and type(row['step']) is int and
                      type(row['view']) is str, 'invalid retention identity')
            key, view = (row['id'], row['step']), row['view']
            c.require(view == 'canonical' or archived and view in ('masked', 'swapped'),
                      'unexpected retention view')
            c.require(key in expected and (*key, view) not in seen, 'retention inventory differs')
            seen.add((*key, view))
            point = {'logp': _logs(row['logp'], 2 ** len(records[key[0]]['entities'])),
                     'order_logp': _logs(row['order_logp'], 2)}
            if view == 'canonical': values[key] = point
        c.require(values.keys() == expected, 'missing retention rows')
        return values

    now, before = indexed(current), indexed(archive, True)
    rows = []
    best = lambda values: max(range(len(values)), key=values.__getitem__)
    for key in sorted(expected):
        point, old = now[key], before[key]
        target = _index(records[key[0]]['utterances'][key[1]]['reading'])
        world, previous_world = best(point['logp']), best(old['logp'])
        order, previous_order = best(point['order_logp']), best(old['order_logp'])
        nll, previous_nll = -point['logp'][target], -old['logp'][target]
        distances = {name: max(_distance(a, b) for a, b in zip(point[name], old[name], strict=True))
                     for name in ('logp', 'order_logp')}
        tv = {name: math.fsum(abs(math.exp(a) - math.exp(b)) for a, b in
                             zip(point[name], old[name], strict=True)) / 2
              for name in ('logp', 'order_logp')}
        rows.append({'id': key[0], 'step': key[1], 'correct': world == target,
            'archived_correct': previous_world == target,
            'regression': previous_world == target and world != target,
            'map_world': world, 'archived_map_world': previous_world,
            'map_order': order, 'archived_map_order': previous_order,
            'world_map_changed': world != previous_world, 'order_map_changed': order != previous_order,
            'logp_equal': point['logp'] == old['logp'], 'order_logp_equal': point['order_logp'] == old['order_logp'],
            'nll': nll, 'archived_nll': previous_nll, 'nll_change': _difference(nll, previous_nll),
            'max_logp_change': distances['logp'], 'max_order_logp_change': distances['order_logp'],
            'total_variation': tv['logp'], 'order_total_variation': tv['order_logp']})
    maximum = max(r['max_logp_change'] for r in rows)
    order_maximum = max(r['max_order_logp_change'] for r in rows)
    identities = lambda field: [[r['id'], r['step']] for r in rows if r[field]]
    world_changes, order_changes, regressions = (identities(k) for k in
                                                ('world_map_changed', 'order_map_changed', 'regression'))
    checks = {'world_logp_retained': maximum <= world_limit,
              'order_logp_retained': order_maximum <= order_limit,
              'world_map_retained': not world_changes, 'order_map_retained': not order_changes,
              'no_exact_regressions': not regressions}
    # Separate nonnegative loss means avoid summing opposite infinite deltas.
    mean = lambda field: math.fsum(r[field] / len(rows) for r in rows)
    current_mean, archived_mean = mean('nll'), mean('archived_nll')
    return _safe({'planned': len(rows), 'correct': sum(r['correct'] for r in rows),
        'archived_correct': sum(r['archived_correct'] for r in rows),
        'regressions': regressions, 'world_map_changes': world_changes, 'order_map_changes': order_changes,
        'exact_world_vectors': sum(r['logp_equal'] for r in rows),
        'exact_order_vectors': sum(r['order_logp_equal'] for r in rows),
        'nll_worse': sum(r['nll_change'] is not None and r['nll_change'] > 0 for r in rows),
        'nll_better': sum(r['nll_change'] is not None and r['nll_change'] < 0 for r in rows),
        'nll_equal': sum(r['nll_change'] == 0 for r in rows),
        'nll_undefined': sum(r['nll_change'] is None for r in rows),
        'mean_nll': current_mean, 'archived_mean_nll': archived_mean,
        'mean_nll_change': _difference(current_mean, archived_mean),
        'max_logp_change': maximum, 'max_order_logp_change': order_maximum,
        'limits': dict(zip(names, (world_limit, order_limit))),
        'checks': checks, 'passed': all(checks.values()), 'points': rows})
