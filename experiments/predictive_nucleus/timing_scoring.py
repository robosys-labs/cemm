"""Planned-denominator timing comparisons; no learner or forecast execution.

Call once per law after ordinary full-world scoring and oracle enrichment. A
timing group is one forecast point, irrespective of its two atomic contacts.
The complete predictive distribution is retained, never projected onto truth.
"""
from collections import defaultdict
from copy import deepcopy
import math

from .acceptance_contract import require
from .acceptance_scoring import _index, _safe
from .hidden_cycle_scoring import _logs
from .multisource_law_scoring import _indexed, _planned_metrics


CONDITIONS = ('ordered', 'common_snapshot', 'common_snapshot_permuted')


def _number(value):
    return {'positive_infinity': math.inf, 'negative_infinity': -math.inf}.get(value, value)


def _inventory(cases):
    inventory, timings, permutations, roles, planned = {}, defaultdict(dict), defaultdict(dict), defaultdict(list), {}
    for case in cases:
        episode, condition = case['episode'], case['condition']
        require(episode not in inventory and condition in CONDITIONS and
            type(case['contact_count']) is int and 3 <= case['contact_count'] <= 5 and
            type(case['group_step']) is int and case['group_step'] == 1 and type(case['critical']) is bool and
            type(case['direction']) is int and case['direction'] in (0, 1) and
            type(case['hidden_source_slot']) is int and case['hidden_source_slot'] in (0, 1),
            'invalid or duplicate timing case')
        ids, count = case['ids'], case['contact_count'] - 1
        require(type(ids) is list and 3 <= len(ids) <= 6 and ids == sorted(set(ids)) and
            all(type(i) is str and i for i in ids) and case['entities'] == len(ids) and
            case['query_steps'] == list(range(1, count)) and
            len(case['forecast_information']) == count and
            all(type(case[k]) is str and case[k] for k in
                ('pre_group_key', 'timing_pair_id', 'permutation_pair_id', 'pair_id')),
            'invalid timing geometry or pairing identity')
        require('permutation_nontrivial' not in case or type(case['permutation_nontrivial']) is bool,
                'invalid event-permutation annotation')
        require(condition not in timings[case['timing_pair_id']], 'duplicate timing condition')
        timings[case['timing_pair_id']][condition] = case
        if condition != 'ordered':
            require(condition not in permutations[case['permutation_pair_id']], 'duplicate permutation condition')
            permutations[case['permutation_pair_id']][condition] = case
        roles[case['pair_id']].append(case); inventory[episode] = case
        for step, info in enumerate(case['forecast_information']):
            worlds, probabilities = info['possible_worlds'], info['probabilities']
            require(type(worlds) is list and worlds and worlds == sorted(set(worlds)) and
                all(type(w) is int and 0 <= w < 2 ** len(ids) for w in worlds) and
                type(probabilities) is list and len(worlds) == len(probabilities) and
                all(type(p) in (float, int) and math.isfinite(p) and p > 0 for p in probabilities) and
                abs(math.fsum(probabilities) - 1.) <= 1e-12 and
                (len(worlds) == 1) == (step > 0), 'invalid timing oracle information')
            require(all(type(info[k]) is list and len(info[k]) == len(ids) and
                all(type(b) is int and b in (0, 1) for b in info[k])
                for k in ('truth', 'previous_truth')) and _index(info['truth']) in worlds and
                type(info['information_key']) is str and bool(info['information_key']),
                'invalid complete-world timing target')
            if step:
                require(info['previous_truth'] == case['forecast_information'][step - 1]['truth'],
                        'timing trajectory truth is discontinuous')
            planned[episode, step] = info
    require(bool(inventory), 'empty timing case inventory')
    common = ('family', 'partition', 'lineage', 'entities', 'contact_count', 'direction',
              'hidden_source_slot', 'critical', 'ids', 'pre_group_key', 'permutation_pair_id')
    for members in timings.values():
        require(set(members) == set(CONDITIONS), 'incomplete planned timing triple')
        ordered, snapshot, permuted = (members[c] for c in CONDITIONS)
        require(all(all(m[k] == ordered[k] for k in common) and
            m.get('permutation_nontrivial') == ordered.get('permutation_nontrivial') for m in (snapshot, permuted)),
                'cross-context timing pair')
        a, b = (m['forecast_information'] for m in (ordered, snapshot))
        require(a[0] == b[0] and a[1]['previous_truth'] == b[1]['previous_truth'] and
            ordered['critical'] == (a[1]['possible_worlds'] != b[1]['possible_worlds']),
            'timing critical subset or pre-group history differs')
        require(ordered['family'] != 'disjoint' or not ordered['critical'],
                'disjoint oracle timing must agree')
    for members in permutations.values():
        require(set(members) == set(CONDITIONS[1:]), 'incomplete planned permutation pair')
        a, b = (members[c] for c in CONDITIONS[1:])
        require(a['timing_pair_id'] == b['timing_pair_id'] and all(a[k] == b[k] for k in common) and
            all(all(x[k] == y[k] for k in ('possible_worlds', 'probabilities', 'truth', 'previous_truth'))
                for x, y in zip(a['forecast_information'], b['forecast_information'], strict=True)),
            'permutation oracle alignment differs')
    for members in roles.values():
        require(len(members) == 2 and {m['direction'] for m in members} == {0, 1} and
            len({tuple(m[k] for k in ('family', 'condition', 'lineage', 'entities',
                                     'contact_count', 'hidden_source_slot')) for m in members}) == 1,
            'incomplete or cross-stratum role pair')
    return inventory, timings, permutations, roles, planned


def _equal(left, right, tolerance):
    return left is not None and right is not None and len(left) == len(right) and all(
        a == b or abs(a - b) <= tolerance for a, b in zip(left, right, strict=True))


def _difference(left, right):
    """Right minus left; two infinite losses have no numerical difference."""
    if left is None or right is None or (math.isinf(left) and math.isinf(right)): return None
    return right - left


def summarize(points, cases, seeds, limits):
    """Summarize one law; cases bind all points even when an output is absent.

    Cases add sorted ids, pre_group_key and forecast_information (oracle fields
    plus complete truth/previous_truth) to the data adapter's metadata. Points
    are acceptance_scoring points enriched with information_scores and aligned
    oracle_probabilities. Missing outputs never shrink a planned denominator.
    """
    require(type(seeds) is list and seeds and all(type(s) is int for s in seeds) and
        len(set(seeds)) == len(seeds), 'invalid seed inventory')
    for key in ('identifiable_accuracy', 'mean_oracle_kl', 'max_ambiguous_total_variation',
                'min_critical_probability', 'max_opposite_probability', 'min_timing_gap', 'probability_tolerance'):
        require(type(limits[key]) in (int, float) and math.isfinite(limits[key]) and 0 <= limits[key] <= 1,
                'invalid timing decision threshold')
    require(type(limits['critical_pairs']) is int and limits['critical_pairs'] > 0,
            'positive critical inventory required')
    inventory, timings, permutations, roles, planned = _inventory(cases)
    require(sum(m['ordered']['critical'] for m in timings.values()) == limits['critical_pairs'],
            'critical timing inventory differs from protocol')
    records = deepcopy(points)
    indexed = _indexed(records)
    expected = {('frozen', seed, *key) for seed in seeds for key in planned}
    require(set(indexed) <= expected, 'unexpected timing score identity')
    for (_, _, episode, step), point in indexed.items():
        case, info = inventory[episode], planned[episode, step]
        require(point['ids'] == case['ids'] and all(point[k] == case[k] for k in
            ('family', 'partition', 'lineage', 'pair_id', 'direction')) and
            all(point[k] == info[k] for k in ('truth', 'previous_truth', 'possible_worlds', 'information_key')) and
            point['oracle_probabilities'] == info['probabilities'] and point['answerable'] == (step > 0) and
            point['status'] in ('ANSWERED', 'ABSTAIN', 'UNPRODUCED'), 'score/evaluator timing metadata differs')
        for key in ('nll', 'oracle_kl'): point[key] = _number(point[key])
        _logs(point)
    by_seed, paired, permutation, checks = {}, {}, {}, {}
    tolerance = limits['probability_tolerance']
    cells = sorted({(c['family'], c['condition']) for c in cases})
    for seed in seeds:
        def point(case, step): return indexed.get(('frozen', seed, case['episode'], step))
        def strata(keys):
            return {name: _planned_metrics(indexed, 'frozen', seed, selected) for name, selected in (
                ('all', keys), ('identifiable', [k for k in keys if len(planned[k]['possible_worlds']) == 1]),
                ('ambiguous', [k for k in keys if len(planned[k]['possible_worlds']) > 1]))}
        def role_metrics(selected):
            rows = []
            for identity, members in selected.items():
                values = [point(m, step) for m in members for step in m['query_steps']]
                complete = all(p is not None and p['status'] == 'ANSWERED' for p in values)
                rows.append({'pair_id': identity, 'complete': complete,
                    'correct': complete and all(p['correct'] for p in values)})
            return {'planned': len(rows), 'complete': sum(r['complete'] for r in rows),
                    'correct': sum(r['correct'] for r in rows), 'records': rows}
        row = strata(list(planned))
        row['identifiable_role_pairs'] = role_metrics(roles)
        row['by_family_condition'] = {}
        for family, condition in cells:
            cell = strata([k for k in planned if (inventory[k[0]]['family'], inventory[k[0]]['condition']) == (family, condition)])
            cell['identifiable_role_pairs'] = role_metrics({k: v for k, v in roles.items()
                if (v[0]['family'], v[0]['condition']) == (family, condition)})
            row['by_family_condition'][family + '/' + condition] = cell
        by_seed[str(seed)] = row
        comparisons = []
        for identity, members in sorted(timings.items()):
            ordered, snapshot = (members[c] for c in CONDITIONS[:2])
            pair_points = [point(m, 1) for m in (ordered, snapshot)]
            logs = [_logs(p) for p in pair_points]
            worlds = [planned[m['episode'], 1]['possible_worlds'][0] for m in (ordered, snapshot)]
            complete = all(v is not None for v in logs)
            own = [None if v is None else math.exp(v[w]) for v, w in zip(logs, worlds, strict=True)]
            opposite = [None if v is None else math.exp(v[worlds[1 - i]]) for i, v in enumerate(logs)]
            gaps = [own[i] - opposite[1 - i] if complete else None for i in (0, 1)]
            critical_pass = complete and all(v + tolerance >= limits['min_critical_probability'] for v in own) and \
                all(v <= limits['max_opposite_probability'] + tolerance for v in opposite) and \
                all(v + tolerance >= limits['min_timing_gap'] for v in gaps)
            temporal = []
            for step in ordered['query_steps']:
                a, b = [point(m, step) for m in (ordered, snapshot)]
                x, y = _logs(a), _logs(b); ready = x is not None and y is not None
                temporal.append({'step': step, 'complete': ready,
                    'oracle_worlds_equal': planned[ordered['episode'], step]['possible_worlds'] ==
                                          planned[snapshot['episode'], step]['possible_worlds'],
                    'full_vector_tv': .5 * math.fsum(abs(math.exp(u) - math.exp(v))
                        for u, v in zip(x, y, strict=True)) if ready else None,
                    'common_minus_ordered_nll': _difference(a['nll'], b['nll']) if ready else None,
                    'both_infinite_nll': ready and math.isinf(a['nll']) and math.isinf(b['nll']),
                    'ordered_correct': bool(a and a['status'] == 'ANSWERED' and a['correct']),
                    'common_correct': bool(b and b['status'] == 'ANSWERED' and b['correct'])})
            comparisons.append({'timing_pair_id': identity, 'ordered_episode': ordered['episode'],
                'snapshot_episode': snapshot['episode'], 'family': ordered['family'],
                'entities': ordered['entities'], 'contact_count': ordered['contact_count'],
                'direction': ordered['direction'], 'hidden_source_slot': ordered['hidden_source_slot'],
                'critical': ordered['critical'], 'complete': complete,
                'pre_group_forecasts_equal': _equal(_logs(point(ordered, 0)), _logs(point(snapshot, 0)), tolerance),
                'own_world_probabilities': own, 'opposite_world_probabilities': opposite, 'timing_gaps': gaps,
                'critical_passed': critical_pass if ordered['critical'] else None,
                'disjoint_control': ordered['family'] == 'disjoint', 'temporal': temporal})
        paired[str(seed)] = {'planned': len(comparisons), 'complete': sum(r['complete'] for r in comparisons),
            'critical_planned': limits['critical_pairs'], 'critical_passed': sum(r['critical_passed'] is True for r in comparisons),
            'records': comparisons}
        permuted = []
        for identity, members in sorted(permutations.items()):
            a, b = (members[c] for c in CONDITIONS[1:])
            for step in range(a['contact_count'] - 1):
                x, y = _logs(point(a, step)), _logs(point(b, step))
                permuted.append({'permutation_pair_id': identity, 'step': step,
                    'nontrivial_event_permutation': a.get('permutation_nontrivial'),
                    'complete': x is not None and y is not None, 'equal': _equal(x, y, tolerance)})
        permutation[str(seed)] = {'planned': len(permuted), 'complete': sum(r['complete'] for r in permuted),
            'equal': sum(r['equal'] for r in permuted),
            'nontrivial_pairs_planned': sum(m['common_snapshot'].get('permutation_nontrivial') is True for m in permutations.values()),
            'nontrivial_points_planned': sum(r['nontrivial_event_permutation'] is True for r in permuted),
            'nontrivial_points_equal': sum(r['nontrivial_event_permutation'] is True and r['equal'] for r in permuted),
            'records': permuted}
        values = row['by_family_condition'].values()
        checks[str(seed)] = {
            'complete_support': row['all']['support_coverage'] == 1.,
            'identifiable_accuracy_each_cell': all(c['identifiable']['accuracy'] is not None and
                c['identifiable']['accuracy'] >= limits['identifiable_accuracy'] for c in values),
            'identifiable_role_pairs_each_cell': all(c['identifiable_role_pairs']['planned'] > 0 and
                c['identifiable_role_pairs']['correct'] >= limits['identifiable_accuracy'] *
                c['identifiable_role_pairs']['planned'] for c in values),
            'supported_MAP_worlds': row['all']['map_outside_support'] == 0,
            'known_unchanged_preserved': row['all']['known_unchanged_errors'] == 0,
            'joint_probability_quality_each_cell': all(c[s]['mean_oracle_kl'] is not None and
                c[s]['mean_oracle_kl'] <= limits['mean_oracle_kl'] for c in values for s in ('identifiable', 'ambiguous')),
            'ambiguous_no_collapse': row['ambiguous']['max_oracle_total_variation'] is not None and
                row['ambiguous']['max_oracle_total_variation'] <= limits['max_ambiguous_total_variation'],
            'identical_pre_group_predictions': all(r['pre_group_forecasts_equal'] for r in comparisons),
            'every_critical_timing': paired[str(seed)]['critical_passed'] == limits['critical_pairs'],
            'common_snapshot_permutation': all(r['equal'] for r in permuted)}
    missing = sorted(expected - set(indexed))
    complete = not missing and all(p['status'] == 'ANSWERED' for p in records)
    passed = complete and all(all(c.values()) for c in checks.values())
    return _safe({'by_seed': by_seed, 'timing': paired, 'permutation': permutation,
        'planned_points_per_seed': len(planned), 'missing_records': missing, 'execution_complete': complete,
        'decision': {'decision': 'STOP_INCOMPLETE_EXECUTION' if not complete else 'KEEP_TIMING' if passed else 'REVISE_TIMING',
            'execution_complete': complete, 'checks': checks, 'gate_g1': 'NOT_ADMITTED',
            'g1_development_readiness': 'PROCEED_TO_G2', 'scientific_admission': False,
            'new_training_updates': 0, 'new_parameters_each': 0,
            'scope': 'Frozen learned pair dynamics under supplied ordered/common-snapshot scheduling; no independent admission'}})
