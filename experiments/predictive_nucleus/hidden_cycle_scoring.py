"""Planned-denominator scoring of frozen full/hidden feedback twins.

Only evaluator assets define the propagation subset. Predictive distributions
remain unconditioned, including all soft mass outside the oracle support.
"""
from collections import defaultdict
import math

from .acceptance_contract import require
from .acceptance_scoring import _index, _safe
from .mixed_composition_run import information_scores
from .multisource_law_scoring import _indexed, _planned_metrics


def _logs(point):
    if point is None or point['status'] != 'ANSWERED': return None
    values = [-math.inf if x == 'negative_infinity' else x for x in point['log_probabilities']]
    require(len(values) == 2 ** len(point['ids']) and all(type(x) in (int, float) and
        not math.isnan(x) and x != math.inf for x in values), 'invalid twin distribution')
    maximum = max(values)
    require(math.isfinite(maximum) and abs(maximum + math.log(math.fsum(
        math.exp(x - maximum) for x in values))) <= 1e-12, 'twin distribution not normalized')
    return values


def _inventory(bundle):
    groups = {name: {c['episode']: c for c in values} for name, values in (
        ('cases', bundle['cases']), ('inputs', bundle['inputs']['episodes']),
        ('oracle', bundle['oracle']['episodes']), ('information', bundle['information']['episodes']))}
    cases = groups['cases']; require(bool(cases), 'empty planned cycle inventory')
    require(all(len(values) == len(cases) and values.keys() == cases.keys() for values in groups.values()) and
        all(len(values) == len(cases) for values in (bundle['cases'], bundle['inputs']['episodes'],
            bundle['oracle']['episodes'], bundle['information']['episodes'])), 'cycle inventory differs')
    twins, roles, planned = defaultdict(dict), defaultdict(list), {}
    for episode, meta in cases.items():
        case, gold, information = (groups[k][episode] for k in ('inputs', 'oracle', 'information'))
        require(meta['condition'] in ('full', 'hidden') and type(meta['critical']) is bool and
            meta['query_steps'] == [2] and len(case['actions']) == 3 and len(case['observations']) == 4 and
            len(gold['truth']) == 4 and len(information['forecasts']) == 3 and
            meta['entities'] == len(case['ids']), 'invalid cycle geometry/condition')
        require(meta['condition'] not in twins[meta['twin_id']], 'duplicate feedback twin')
        twins[meta['twin_id']][meta['condition']] = meta
        roles[meta['pair_id']].append(meta)
        ids = sorted(case['ids']); target = meta['final_target']
        require(target in ids and type(meta['stale_target_bit']) is int and meta['stale_target_bit'] in (0, 1) and
            meta['true_target_bit'] == gold['truth'][3][target] and
            meta['critical'] == (meta['stale_target_bit'] != meta['true_target_bit']), 'critical target alignment differs')
        require(type(meta['stale_final_world']) is int and 0 <= meta['stale_final_world'] < 2 ** len(ids) and
            ((meta['stale_final_world'] >> (len(ids) - ids.index(target) - 1)) & 1) == meta['stale_target_bit'],
            'stale world/target alignment differs')
        for step, info in enumerate(information['forecasts']):
            require(info['possible_worlds'] == gold['possible_worlds'][step] and
                info['information_key'] == gold['information_keys'][step] and
                (len(info['possible_worlds']) == 1) == (step > 0), 'cycle information stratum differs')
            planned[episode, step] = info
    for members in roles.values():
        require(len(members) == 2 and {m['direction'] for m in members} == {0, 1} and len({
            (m['family'], m['condition'], m['entities'], m['lineage']) for m in members}) == 1,
            'incomplete/cross-stratum planned role pair')
    for members in twins.values():
        require(set(members) == {'full', 'hidden'}, 'incomplete planned feedback twin')
        a, b = (members[c] for c in ('full', 'hidden'))
        require(all(a[k] == b[k] for k in ('family', 'entities', 'lineage', 'direction', 'critical',
            'hidden_handle', 'final_target', 'true_target_bit', 'stale_target_bit', 'stale_final_world')),
            'feedback twin metadata differs')
        left, right = (groups['inputs'][m['episode']] for m in (a, b))
        require(all(left[k] == right[k] for k in ('ids', 'actions', 'coverage')) and
            groups['oracle'][a['episode']]['truth'] == groups['oracle'][b['episode']]['truth'],
            'feedback twin physical design differs')
        differences = [(t, name) for t in range(4) for name in left['ids']
            if left['observations'][t][name] != right['observations'][t][name]]
        require(differences == [(2, b['hidden_handle'])] and
            right['observations'][2][b['hidden_handle']] is None and
            all(v is not None for reading in left['observations'] for v in reading.values()),
            'feedback twins must differ only at the hidden intermediate reading')
        require(planned[a['episode'], 2]['possible_worlds'] == planned[b['episode'], 2]['possible_worlds'],
            'feedback twins have different final information support')
    return groups, twins, roles, planned


def analyze(report, bundle, config):
    """Enrich the report's points, retaining absent records in every denominator."""
    groups, twins, roles, planned = _inventory(bundle)
    cases, limits, seeds = groups['cases'], config['analysis'], config['model_seeds']
    require(seeds and len(set(seeds)) == len(seeds), 'empty/repeated seed inventory')
    require(sum(t['hidden']['critical'] for t in twins.values()) == limits['critical_pairs'],
            'critical planned inventory differs')
    indexed = _indexed(report['points'])
    expected = {('frozen', seed, *key) for seed in seeds for key in planned}
    require(set(indexed) <= expected, 'unexpected cycle score identity')
    for key, point in indexed.items():
        _, _, episode, step = key
        case, meta, gold = (groups[k][episode] for k in ('inputs', 'cases', 'oracle'))
        ids = sorted(case['ids'])
        require(point['ids'] == ids and all(point[k] == meta[k] for k in
            ('family', 'partition', 'lineage', 'pair_id', 'direction')) and
            point['truth'] == [gold['truth'][step + 1][i] for i in ids] and
            point['previous_truth'] == [gold['truth'][step][i] for i in ids] and
            point['answerable'] == (step > 0), 'score/evaluator metadata alignment differs')
        previous = [_index([case['observations'][0][name] for name in ids])] if step == 0 else [
            world for world in planned[episode, step - 1]['possible_worlds'] if all(
                value is None or value == ((world >> (len(ids) - i - 1)) & 1)
                for i, name in enumerate(ids) for value in [case['observations'][step][name]])]
        if point['nll'] == 'positive_infinity': point['nll'] = math.inf
        _logs(point)
        point.update(information_scores(point, planned[episode, step], previous))
    by_seed, paired, checks = {}, {}, {}
    for seed in seeds:
        def strata(keys):
            return {name: _planned_metrics(indexed, 'frozen', seed, selected) for name, selected in (
                ('all', keys), ('identifiable', [k for k in keys if len(planned[k]['possible_worlds']) == 1]),
                ('ambiguous', [k for k in keys if len(planned[k]['possible_worlds']) > 1]))}
        def role_summary(members):
            records = []
            for identity, pair in members.items():
                keys = [(m['episode'], step) for m in pair for step in (1, 2)]
                points = [indexed.get(('frozen', seed, *key)) for key in keys]
                records.append({'pair_id': identity, 'episodes': [m['episode'] for m in pair],
                    'complete': all(p is not None and p['status'] == 'ANSWERED' for p in points),
                    'correct': all(p is not None and p['correct'] for p in points)})
            return {'planned': len(records), 'correct': sum(r['correct'] for r in records),
                'complete': sum(r['complete'] for r in records), 'records': records}
        row = strata(list(planned)); cells = {}
        for family, condition in sorted({(c['family'], c['condition']) for c in cases.values()}):
            keys = [k for k in planned if (cases[k[0]]['family'], cases[k[0]]['condition']) == (family, condition)]
            cell = strata(keys)
            cell['identifiable_role_pairs'] = role_summary({k: v for k, v in roles.items()
                if (v[0]['family'], v[0]['condition']) == (family, condition)})
            cells[family + '/' + condition] = cell
        row.update(by_family_condition=cells, identifiable_role_pairs=role_summary(roles),
            by_entity_count={str(n): strata([k for k in planned if cases[k[0]]['entities'] == n])
                             for n in sorted({c['entities'] for c in cases.values()})})
        by_seed[str(seed)] = row
        records, tolerance = [], limits['probability_tolerance']
        for identity, pair in sorted(twins.items()):
            full, hidden = (pair[c] for c in ('full', 'hidden'))
            points = [indexed.get(('frozen', seed, m['episode'], 2)) for m in (full, hidden)]
            logs = [_logs(p) for p in points]
            complete = all(v is not None for v in logs)
            prefix_equal = True
            for step in (0, 1):
                a, b = [_logs(indexed.get(('frozen', seed, m['episode'], step))) for m in (full, hidden)]
                prefix_equal &= a is not None and b is not None and all(
                    x == y or abs(x - y) <= tolerance for x, y in zip(a or [], b or [], strict=True))
            world = planned[hidden['episode'], 2]['possible_worlds'][0]
            probabilities = [None if v is None else math.exp(v[world]) for v in logs]
            target_index = sorted(groups['inputs'][hidden['episode']]['ids']).index(hidden['final_target'])
            stale_mass = None if logs[1] is None else math.fsum(math.exp(v) for w, v in enumerate(logs[1])
                if ((w >> (hidden['entities'] - target_index - 1)) & 1) == hidden['stale_target_bit'])
            critical_passed = complete and probabilities[1] + tolerance >= limits['min_critical_probability'] and \
                stale_mass <= limits['max_stale_target_probability'] + tolerance
            losses = [None if p is None else p['nll'] for p in points]
            delta = losses[1] - losses[0] if complete and not all(math.isinf(x) for x in losses) else None
            records.append({'twin_id': identity, 'family': hidden['family'], 'entities': hidden['entities'],
                'full_episode': full['episode'], 'hidden_episode': hidden['episode'], 'critical': hidden['critical'],
                'complete': complete, 'prefix_forecasts_equal': prefix_equal, 'full_correct': bool(points[0] and points[0]['correct']),
                'hidden_correct': bool(points[1] and points[1]['correct']), 'full_probability': probabilities[0],
                'hidden_probability': probabilities[1], 'stale_target_probability': stale_mass,
                'hidden_minus_full_probability': probabilities[1] - probabilities[0] if complete else None,
                'hidden_minus_full_nll': delta, 'both_infinite_nll': complete and all(math.isinf(x) for x in losses),
                'critical_passed': critical_passed if hidden['critical'] else None})
        paired[str(seed)] = {'planned': len(records), 'complete': sum(r['complete'] for r in records),
            'critical_planned': limits['critical_pairs'], 'critical_passed': sum(r['critical_passed'] is True for r in records),
            'repairs': [r['twin_id'] for r in records if r['complete'] and r['hidden_correct'] and not r['full_correct']],
            'regressions': [r['twin_id'] for r in records if r['full_correct'] and not r['hidden_correct']],
            'unpaired': [r['twin_id'] for r in records if not r['complete']], 'records': records}
        checks[str(seed)] = {
            'complete_support': row['all']['support_coverage'] == 1.,
            'identifiable_accuracy_each_cell': all(c['identifiable']['accuracy'] is not None and
                c['identifiable']['accuracy'] >= limits['identifiable_accuracy'] for c in cells.values()),
            'identifiable_role_pairs_each_cell': all(c['identifiable_role_pairs']['planned'] > 0 and
                c['identifiable_role_pairs']['correct'] >= limits['identifiable_accuracy'] *
                c['identifiable_role_pairs']['planned'] for c in cells.values()),
            'supported_MAP_worlds': row['all']['map_outside_support'] == 0,
            'known_unchanged_preserved': row['all']['known_unchanged_errors'] == 0,
            'joint_probability_quality_each_cell': all(c[s]['mean_oracle_kl'] is not None and
                c[s]['mean_oracle_kl'] <= limits['mean_oracle_kl'] for c in cells.values()
                for s in ('identifiable', 'ambiguous')),
            'ambiguous_no_collapse': row['ambiguous']['max_oracle_total_variation'] is not None and
                row['ambiguous']['max_oracle_total_variation'] <= limits['max_ambiguous_total_variation'],
            'prefix_forecasts_equal': all(r['prefix_forecasts_equal'] for r in records),
            'no_identifiable_twin_regressions': not paired[str(seed)]['regressions'],
            'every_critical_propagation': paired[str(seed)]['critical_passed'] == limits['critical_pairs']}
    missing = sorted(expected - set(indexed))
    complete = not missing and not report['metadata']['incomplete_inventory'] and not report['metadata']['failure_records'] and \
        all(p['status'] != 'UNPRODUCED' for p in indexed.values())
    passed = complete and all(all(c.values()) for c in checks.values())
    return _safe({'version': config['version'], 'by_seed': by_seed, 'paired': paired,
        'missing_records': missing, 'metadata': report['metadata'], 'decision': {
            'decision': 'STOP_INCOMPLETE_EXECUTION' if not complete else
                'KEEP_HIDDEN_CYCLE' if passed else 'REVISE_HIDDEN_CYCLE',
            'execution_complete': complete, 'checks': checks, 'gate_g1': 'NOT_ADMITTED',
            'g1_development_readiness': 'PROCEED_TO_G2', 'scientific_admission': False,
            'new_training_updates': 0, 'g2_scope': 'One hidden learned consequence in ordered cycles; full G2 remains open'}})
