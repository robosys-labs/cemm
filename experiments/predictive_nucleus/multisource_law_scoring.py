"""Pure primary-composition and common-history law-swap arithmetic."""
import math

from .acceptance_contract import require
from .acceptance_scoring import IDENTITY, _index, _safe
from .mixed_composition_run import _metrics


def _indexed(points):
    result = {tuple(p[k] for k in IDENTITY): p for p in points}
    require(len(result) == len(points), 'duplicate score identity')
    return result


def _planned_metrics(index, arm, seed, identities):
    rows = [index[arm, seed, *key] for key in identities if (arm, seed, *key) in index]
    result, n = _metrics(rows), len(identities)
    missing = [list(key) for key in identities if (arm, seed, *key) not in index]
    result.update(planned_points=n, missing_records=missing,
        unproduced_forecasts=result['unproduced_forecasts'] + len(missing),
        accuracy=result['correct'] / n if n else None,
        production_coverage=result['produced_forecasts'] / n if n else None,
        support_coverage=result['supported_forecasts'] / n if n else None)
    if missing:
        for key in result:
            if key.startswith(('mean_oracle_', 'max_oracle_')) or key in (
                    'mean_nll', 'mean_brier', 'mean_outside_support_mass',
                    'max_outside_support_mass', 'unchanged_bits_planned'): result[key] = None
    return result


def summarize_composition(points, cases, seeds, limits):
    """Keep all planned query points; acquisition contacts cannot improve gates."""
    index, inventory = _indexed(points), {}
    for case in cases:
        for step in case['query_steps']:
            key = (case['episode'], step)
            require(step >= 2 and key not in inventory and case['flow'] in ('fan_in', 'fan_out'),
                    'invalid primary composition inventory')
            inventory[key] = (case['family'], case['flow'])
    require(bool(inventory) and bool(seeds) and len(set(seeds)) == len(seeds), 'empty or repeated inventory')
    for p in points:
        key = (p['episode'], p['step'])
        if key in inventory:
            require(p['family'] == inventory[key][0] and p['answerable'], 'primary information alignment differs')
    families = sorted({family for family, _ in inventory.values()})
    arms, metrics, checks, changes = sorted({p['participant'] for p in points} | {'matched', 'crossed'}), {}, {}, {}
    for arm in arms:
        metrics[arm] = {}
        for seed in seeds:
            def metric(family=None, flow=None):
                return _planned_metrics(index, arm, seed, [k for k, (f, v) in inventory.items()
                    if (family is None or f == family) and (flow is None or v == flow)])
            metrics[arm][str(seed)] = {'all': metric(),
                'by_family': {f: metric(family=f) for f in families},
                'by_flow': {v: metric(flow=v) for v in ('fan_in', 'fan_out')},
                'by_family_flow': {f: {v: metric(f, v) for v in ('fan_in', 'fan_out')} for f in families}}
    for seed in seeds:
        cells = metrics['matched'][str(seed)]['by_family_flow']
        checks[str(seed)] = {f + '/' + flow: {
            'accuracy': m['accuracy'] is not None and m['accuracy'] >= limits['identifiable_accuracy'],
            'complete_support': m['support_coverage'] == 1.,
            'supported_MAP_worlds': m['map_outside_support'] == 0,
            'known_unchanged_preserved': m['known_unchanged_errors'] == 0}
            for f, flows in cells.items() for flow, m in flows.items()}
        changed = {key: [] for key in ('repairs', 'regressions', 'unpaired')}
        for episode, step in inventory:
            before, after = (index.get((arm, seed, episode, step)) for arm in ('crossed', 'matched'))
            if before is None or after is None: changed['unpaired'].append([episode, step])
            elif before['correct'] != after['correct']:
                changed['repairs' if after['correct'] else 'regressions'].append([episode, step])
        changes[str(seed)] = changed
    return _safe({'passed': all(all(c.values()) for s in checks.values() for c in s.values()),
        'planned_points_per_seed': len(inventory), 'by_arm': metrics, 'checks': checks, 'changes': changes})


def compare_laws(points_by_law, contexts, seeds, limits):
    """Check opposite laws on identical delivered prefixes, without conditioning forecasts."""
    require(set(points_by_law) == {'nand', 'nor'}, 'law inventory differs')
    identities = {(c['episode'], c['step']) for c in contexts}
    require(len(identities) == len(contexts) == limits['contexts'] and contexts and seeds and
        len(set(seeds)) == len(seeds) and all(c['step'] == 1 and c['nand_world'] != c['nor_world']
        for c in contexts), 'critical context inventory differs')
    indexes = {law: _indexed(points) for law, points in points_by_law.items()}
    allowed = {(arm, seed, *key) for arm in ('matched', 'crossed') for seed in seeds for key in identities}
    require(all(set(index) <= allowed for index in indexes.values()), 'unexpected critical score identity')
    rows, means, checks, tolerance = [], {}, {}, limits['probability_tolerance']
    for seed in seeds:
        losses = {law: {arm: [] for arm in ('matched', 'crossed')} for law in indexes}
        for context in contexts:
            vectors, coordinate_ids = {}, None
            for law, index in indexes.items():
                for arm in ('matched', 'crossed'):
                    p = index.get((arm, seed, context['episode'], context['step']))
                    if p is not None:
                        world = context[law + '_world']
                        require(p['information_key'] == context['information_key'] and
                            p['possible_worlds'] == [world] and _index(p['truth']) == world and
                            all(type(context[k]) is int and 0 <= context[k] < 2 ** len(p['ids'])
                                for k in ('nand_world', 'nor_world')),
                            'critical information/support alignment differs')
                        require(coordinate_ids is None or p['ids'] == coordinate_ids, 'critical coordinate alignment differs')
                        coordinate_ids = p['ids']
                    logs = None if p is None or p['status'] != 'ANSWERED' else [
                        -math.inf if v == 'negative_infinity' else v for v in p['log_probabilities']]
                    if logs is not None:
                        require(len(logs) == 2 ** len(p['ids']) and all(type(v) in (float, int) and
                            not math.isnan(v) and v != math.inf for v in logs), 'invalid critical log forecast')
                        maximum = max(logs)
                        require(math.isfinite(maximum) and abs(maximum + math.log(math.fsum(
                            math.exp(v - maximum) for v in logs))) <= 1e-12, 'critical forecast is not normalized')
                        losses[law][arm].append(-logs[context[law + '_world']])
                    vectors[law, arm] = logs
            for law, other in (('nand', 'nor'), ('nor', 'nand')):
                left, right = vectors[law, 'crossed'], vectors[other, 'matched']
                if left is not None and right is not None:
                    require(all(a == b or abs(a - b) <= tolerance for a, b in zip(left, right, strict=True)),
                            'crossed checkpoint forecast binding differs')
            complete = all(v is not None for v in vectors.values())
            nand = None if vectors['nand', 'matched'] is None else math.exp(vectors['nand', 'matched'][context['nand_world']])
            nor = None if vectors['nor', 'matched'] is None else math.exp(vectors['nor', 'matched'][context['nor_world']])
            wrong = None if vectors['nor', 'matched'] is None else math.exp(vectors['nor', 'matched'][context['nand_world']])
            gap = nand - wrong if nand is not None and wrong is not None else None
            passed = complete and min(nand, nor) + tolerance >= limits['min_matched_probability'] and \
                wrong <= limits['max_wrong_law_probability'] + tolerance and gap + tolerance >= limits['min_gap']
            rows.append({**context, 'model_seed': seed, 'complete': complete, 'nand_probability': nand,
                'nor_probability': nor, 'wrong_law_probability': wrong, 'gap': gap, 'passed': passed})
        means[str(seed)], checks[str(seed)] = {}, {}
        for law, arms in losses.items():
            scores = {arm: math.fsum(x / len(v) for x in v) if len(v) == len(contexts) else None for arm, v in arms.items()}
            valid = scores['matched'] is not None and math.isfinite(scores['matched']) and scores['crossed'] is not None
            gain = scores['crossed'] - scores['matched'] if valid else None
            means[str(seed)][law] = {**scores, 'gain': gain, 'answered': {a: len(v) for a, v in arms.items()}}
            checks[str(seed)][law + '_mean_nll_gain'] = valid and gain + tolerance >= limits['min_mean_nll_gain']
        checks[str(seed)]['every_context'] = all(r['passed'] for r in rows if r['model_seed'] == seed)
    return _safe({'passed': all(all(c.values()) for c in checks.values()), 'checks': checks,
        'planned_contexts_per_seed': len(contexts), 'rows': rows, 'means': means})
