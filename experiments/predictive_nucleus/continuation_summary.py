"""Fixed-index continuation summaries over already validated acceptance points.

The complete all-action report remains authoritative. Query subsets never enter
the acceptance trajectory scorer, and neither missing outputs nor zero-query
episodes are converted into successful predictions. No admission decision here.
"""
from collections import defaultdict
from copy import deepcopy
import json
import math

from .acceptance_scoring import _mean, _metrics, _require, _safe


def _metric(points):
    # The acceptance report serializes infinite proper losses as strict JSON.
    rows = [dict(row, nll=math.inf if row['nll'] == 'positive_infinity' else row['nll']) for row in points]
    return _metrics(rows)


def _pairs(cases, lookup):
    groups = defaultdict(list)
    for case in cases:
        if case['query_scope'] == 'continuation' and case['pair_id'] is not None:
            groups[case['pair_id']].append(case)
    records = []
    for pair, members in sorted(groups.items()):
        _require(len(members) == 2 and {m['direction'] for m in members} == {0, 1}, 'incomplete query role pair')
        a, b = sorted(members, key=lambda m: m['direction'])
        _require(a['query_steps'] == b['query_steps'] and bool(a['query_steps']), 'query role scope differs')
        points = [lookup[m['episode'], step] for m in (a, b) for step in m['query_steps']]
        records.append({'pair_id': pair, 'family': a['family'], 'query_steps': a['query_steps'],
            'episodes': [a['episode'], b['episode']], 'planned_points': len(points),
            'fully_produced': all(p['status'] != 'UNPRODUCED' for p in points),
            'fully_supported': all(p['status'] == 'ANSWERED' for p in points),
            'both_exact': all(p['correct'] for p in points)})
    return {'planned': len(records), 'exact': sum(r['both_exact'] for r in records),
            'exact_rate': _mean([int(r['both_exact']) for r in records]), 'records': records}


def summarize(points, cases, model_seeds=None, fit_status=None):
    """Summarize complete arm/seed inventories; cases carry evaluator query indices.

    OOD accuracy averages query points within physical lineage, then lineages
    within (family, N, total contacts), then cells within family, then families.
    Seed replication is separate; related views are never independent samples.
    """
    _require(bool(points) and bool(cases), 'nonempty acceptance points and cases required')
    metadata = {c['episode']: c for c in cases}
    _require(len(metadata) == len(cases), 'duplicate query case')
    seeds = sorted({p['model_seed'] for p in points}) if model_seeds is None else sorted(model_seeds)
    _require(bool(seeds) and len(set(seeds)) == len(seeds), 'invalid seed inventory')
    arms = {}
    for arm in sorted({p['participant'] for p in points}):
        arm_points = [p for p in points if p['participant'] == arm]
        _require({p['model_seed'] for p in arm_points} == set(seeds), 'arm seed inventory differs')
        by_seed = {}
        for seed in seeds:
            rows = [p for p in arm_points if p['model_seed'] == seed]
            lookup = {(p['episode'], p['step']): p for p in rows}
            _require(len(lookup) == len(rows) and {p['episode'] for p in rows} == set(metadata),
                     'duplicate point or missing query episode')
            selected, acquisition, draws, cells = [], [], defaultdict(list), defaultdict(list)
            for case in cases:
                steps = case['query_steps']
                _require(steps == sorted(set(steps)) and all(type(s) is int and s >= 0 for s in steps),
                         'invalid fixed query indices')
                _require(case['query_scope'] in ('continuation', 'self_contact', 'acquisition_only') and
                         (bool(steps) == (case['query_scope'] != 'acquisition_only')), 'query scope/count mismatch')
                for step in steps:
                    _require((case['episode'], step) in lookup, 'planned query point missing')
                    selected.append(lookup[case['episode'], step])
                if case['acquisition_step'] is not None:
                    _require((case['episode'], case['acquisition_step']) in lookup, 'acquisition point missing')
                    acquisition.append(lookup[case['episode'], case['acquisition_step']])
            for p in rows:
                c = metadata[p['episode']]
                _require(all(p[k] == c[k] for k in ('family', 'partition', 'lineage', 'pair_id', 'direction')) and
                         len(p['ids']) == c['entities'], 'point/query metadata differs')
            continuation = [p for p in selected if metadata[p['episode']]['query_scope'] == 'continuation']
            self_points = [p for p in selected if metadata[p['episode']]['query_scope'] == 'self_contact']
            for p in continuation: draws[p['lineage']].append(p)
            per_lineage = []
            for lineage, group in sorted(draws.items()):
                case = metadata[group[0]['episode']]
                cell = (case['family'], case['entities'], case['contact_count'])
                accuracy = _mean([int(p['correct']) for p in group])
                per_lineage.append({'lineage': lineage, 'family': cell[0], 'entities': cell[1],
                    'contact_count': cell[2], 'planned_points': len(group), 'correct': sum(p['correct'] for p in group),
                    'accuracy': accuracy, 'episodes': sorted({p['episode'] for p in group})})
                if case['partition'] == 'held_out': cells[cell].append(accuracy)
            family_cells = defaultdict(list)
            for (family, _, _), values in sorted(cells.items()): family_cells[family].append(_mean(values))
            family_accuracy = {family: _mean(values) for family, values in sorted(family_cells.items())}
            cell_groups = defaultdict(list)
            for c in cases: cell_groups[f"{c['family']}|N={c['entities']}|contacts={c['contact_count']}"]
            for p in selected:
                c = metadata[p['episode']]
                cell_groups[f"{c['family']}|N={c['entities']}|contacts={c['contact_count']}"].append(p)
            by_seed[str(seed)] = {'all_action': _metric(rows), 'continuation': _metric(continuation),
                'in_family_continuation': _metric([p for p in continuation if p['partition'] == 'in_family']),
                'ood_continuation': _metric([p for p in continuation if p['partition'] == 'held_out']),
                'self_contact': _metric(self_points), 'acquisition': _metric(acquisition),
                'acquisition_ambiguous': _metric([p for p in acquisition if not p['answerable']]),
                'zero_query_episodes': sorted(c['episode'] for c in cases if not c['query_steps']),
                'by_family': {f: _metric([p for p in selected if p['family'] == f]) for f in sorted({c['family'] for c in cases})},
                'by_cell': {key: _metric(group) for key, group in sorted(cell_groups.items())},
                'per_lineage': per_lineage, 'ood_family_accuracy': family_accuracy,
                'ood_macro_accuracy': _mean(list(family_accuracy.values())), 'query_role_pairs': _pairs(cases, lookup)}
        arms[arm] = {'by_seed': by_seed}
    result = _safe({'scope': 'FIXED_POST_ACQUISITION_QUERIES; SELF_CONTACT_SEPARATE',
        'gate_g1': 'NOT_ADMITTED', 'query_indices_are_original_steps': True,
        'ood_aggregation': 'mean family(mean cell(mean physical lineage(mean fixed query points across related views))))',
        'model_seeds': seeds, 'by_arm': arms, 'fit_status': deepcopy(fit_status)})
    json.dumps(result, allow_nan=False)
    return result
