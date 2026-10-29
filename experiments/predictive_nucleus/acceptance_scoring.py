"""Pure prospective full-world scoring; no learner, fitter, or simulator imports.

Scores use the entire forecast, including mass outside declared information
support. Trajectory exactness is an AND of forecasts with delivered feedback,
never a rollout result or a joint trajectory likelihood. No score admits G1.
"""
from collections import defaultdict
from copy import deepcopy
from hashlib import sha256
import json
import math
from pathlib import Path


VERSION = 'active-acceptance-scoring-v1'
IDENTITY = ('participant', 'model_seed', 'episode', 'step')


def _require(ok, message):
    if not ok: raise ValueError(message)


def _mean(values):
    return math.fsum(v / len(values) for v in values) if values else None


def _percentile(values, fraction):
    return sorted(values)[math.ceil(len(values) * fraction) - 1] if values else None


def _safe(value):
    if isinstance(value, dict): return {k: _safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)): return [_safe(v) for v in value]
    if type(value) is float:
        _require(not math.isnan(value), 'NaN cannot be a reported score')
        if math.isinf(value): return 'positive_infinity' if value > 0 else 'negative_infinity'
    return value


def _index(bits):
    result = 0
    for bit in bits: result = 2 * result + bit
    return result


def _point(row):
    n, status = len(row['ids']), row['status']
    _require(3 <= n <= 6 and status in ('ANSWERED', 'ABSTAIN', 'UNPRODUCED'), 'invalid score domain/status')
    for key in ('truth', 'previous_truth'):
        _require(type(row[key]) is list and len(row[key]) == n and
                 all(type(b) is int and b in (0, 1) for b in row[key]), 'invalid complete-world target')
    possible = row['possible_worlds']
    gold = _index(row['truth'])
    _require(type(possible) is list and bool(possible) and possible == sorted(set(possible)) and
             all(type(w) is int and 0 <= w < 2 ** n for w in possible) and gold in possible,
             'invalid declared information support')
    keys = (*IDENTITY, 'family', 'partition', 'lineage', 'pair_id', 'direction', 'ids',
            'truth', 'previous_truth', 'possible_worlds', 'information_key', 'action_kind',
            'status', 'wall_seconds', 'cpu_seconds')
    result = {key: deepcopy(row[key]) for key in keys}
    unchanged = [i for i in range(n) if row['truth'][i] == row['previous_truth'][i]]
    result.update(answerable=len(possible) == 1, correct=False, map_world=None, maximizers=None,
                  nll=None, brier=None, confidence=None, underflow_world_count=0,
                  unchanged_bits_planned=len(unchanged), unchanged_bits_answered=0,
                  unchanged_bit_errors=0, log_probabilities=None)
    if status != 'ANSWERED':
        _require(row['log_probabilities'] is None, 'unsupported forecast must have no distribution')
        return result
    logs = row['log_probabilities']
    _require(type(logs) is list and len(logs) == 2 ** n and all(type(v) in (int, float) and
             not math.isnan(v) and v != math.inf for v in logs), 'invalid full-world log forecast')
    maximum = max(logs)
    _require(math.isfinite(maximum) and abs(maximum + math.log(math.fsum(
        math.exp(v - maximum) for v in logs))) <= 1e-12, 'forecast is not normalized')
    probabilities = [math.exp(v) for v in logs]
    maxima = [i for i, v in enumerate(logs) if v == maximum]
    best = maxima[0]  # Frozen lexicographic tie rule, independent of the target.
    result.update(correct=best == gold, map_world=best, maximizers=maxima,
        nll=-float(logs[gold]), brier=math.fsum((p - int(i == gold)) ** 2 for i, p in enumerate(probabilities)),
        confidence=probabilities[best], log_probabilities=list(logs),
        underflow_world_count=sum(math.isfinite(v) and p == 0 for v, p in zip(logs, probabilities)),
        unchanged_bits_answered=len(unchanged),
        unchanged_bit_errors=sum(((best >> (n - i - 1)) & 1) != row['truth'][i] for i in unchanged))
    return result


def _metrics(points):
    answered = [r for r in points if r['status'] == 'ANSWERED']
    n, a = len(points), len(answered)
    produced = sum(r['status'] != 'UNPRODUCED' for r in points)
    correct = sum(r['correct'] for r in answered)
    bins, ece = [], 0.
    for i in range(10):
        group = [r for r in answered if r['confidence'] >= i / 10 and
                 (r['confidence'] < (i + 1) / 10 if i < 9 else True)]
        accuracy, confidence = _mean([int(r['correct']) for r in group]), _mean([r['confidence'] for r in group])
        if group: ece += len(group) / a * abs(accuracy - confidence)
        bins.append({'bin': i, 'lower': i / 10, 'upper': (i + 1) / 10, 'count': len(group),
                     'accuracy': accuracy, 'confidence': confidence})
    nll, brier = _mean([r['nll'] for r in answered]), _mean([r['brier'] for r in answered])
    wall = [r['wall_seconds'] for r in points if r['wall_seconds'] is not None]
    cpu = [r['cpu_seconds'] for r in points if r['cpu_seconds'] is not None]
    return {'planned_points': n, 'produced_forecasts': produced, 'supported_forecasts': a,
        'explicit_abstentions': produced - a, 'unproduced_forecasts': n - produced,
        'correct': correct, 'wrong_supported': a - correct, 'accuracy': correct / n if n else None,
        'accuracy_among_supported': correct / a if a else None,
        'production_coverage': produced / n if n else None, 'support_coverage': a / n if n else None,
        'mean_nll': nll if n and a == n else None, 'mean_brier': brier if n and a == n else None,
        'conditional_mean_nll': nll, 'conditional_mean_brier': brier,
        'infinite_nll_count': sum(math.isinf(r['nll']) for r in answered),
        'ece_10_conditional_on_support': ece if a else None, 'ece_bins': bins,
        'tied_forecasts': sum(len(r['maximizers']) > 1 for r in answered),
        'underflow_world_count': sum(r['underflow_world_count'] for r in answered),
        'unchanged_bit_errors': sum(r['unchanged_bit_errors'] for r in answered),
        'unchanged_bits_planned': sum(r['unchanged_bits_planned'] for r in points),
        'unchanged_bits_answered': sum(r['unchanged_bits_answered'] for r in answered),
        'physical_lineages': len({r['lineage'] for r in points}),
        'timed_forecasts': len(wall), 'mean_reported_wall_seconds': _mean(wall),
        'mean_reported_cpu_seconds': _mean(cpu),
        'wall_seconds_p50': _percentile(wall, .5), 'wall_seconds_p95': _percentile(wall, .95),
        'cpu_seconds_p50': _percentile(cpu, .5), 'cpu_seconds_p95': _percentile(cpu, .95)}


def _trajectories(points):
    groups = defaultdict(list)
    for point in points: groups[tuple(point[k] for k in IDENTITY[:3])].append(point)
    result = []
    for key, rows in sorted(groups.items()):
        _require(sorted(r['step'] for r in rows) == list(range(len(rows))), 'trajectory prediction points are incomplete')
        metadata = ('family', 'partition', 'lineage', 'pair_id', 'direction', 'ids')
        _require(all(all(r[k] == rows[0][k] for k in metadata) for r in rows), 'trajectory metadata differs')
        result.append({**dict(zip(IDENTITY[:3], key)), **{k: rows[0][k] for k in metadata},
            'planned_points': len(rows), 'fully_produced': all(r['status'] != 'UNPRODUCED' for r in rows),
            'fully_supported': all(r['status'] == 'ANSWERED' for r in rows),
            'exact': all(r['correct'] for r in rows), 'all_points_answerable': all(r['answerable'] for r in rows)})
    return result


def _whole_metrics(points):
    trajectories = _trajectories(points)
    pairs = defaultdict(list)
    for row in trajectories:
        if row['pair_id'] is not None: pairs[row['participant'], row['model_seed'], row['pair_id']].append(row)
    pair_rows = []
    for (participant, seed, pair_id), members in sorted(pairs.items()):
        _require(len(members) == 2 and {m['direction'] for m in members} == {0, 1}, 'role pair needs both complete members')
        pair_rows.append({'participant': participant, 'model_seed': seed, 'pair_id': pair_id,
            'episodes': {str(m['direction']): m['episode'] for m in members},
            'both_fully_produced': all(m['fully_produced'] for m in members),
            'both_fully_supported': all(m['fully_supported'] for m in members),
            'both_exact': all(m['exact'] for m in members)})
    def counts(rows, exact, produced, supported):
        n = len(rows)
        return {'planned': n, 'fully_produced': sum(r[produced] for r in rows),
                'fully_supported': sum(r[supported] for r in rows), 'exact': sum(r[exact] for r in rows),
                'exact_rate': sum(r[exact] for r in rows) / n if n else None, 'records': rows}
    return {'trajectories': counts(trajectories, 'exact', 'fully_produced', 'fully_supported'),
            'role_pairs': counts(pair_rows, 'both_exact', 'both_fully_produced', 'both_fully_supported')}


def _summary(points, whole=False):
    result = {'all': _metrics(points), 'answerable': _metrics([r for r in points if r['answerable']]),
              'ambiguous': _metrics([r for r in points if not r['answerable']])}
    if whole: result.update(_whole_metrics(points))
    return result


def _by(points, key, whole=False):
    groups = defaultdict(list)
    for row in points: groups[key(row)].append(row)
    return {str(name): _summary(rows, whole) for name, rows in sorted(groups.items())}


def _seed_summary(by_seed):
    paths = {'accuracy': ('all', 'accuracy', min), 'support_coverage': ('all', 'support_coverage', min),
             'mean_nll': ('all', 'mean_nll', max), 'mean_brier': ('all', 'mean_brier', max),
             'trajectory_exact_rate': ('trajectories', 'exact_rate', min),
             'role_pair_exact_rate': ('role_pairs', 'exact_rate', min)}
    metrics = {}
    for name, (section, field, worst) in paths.items():
        values = [row[section][field] for row in by_seed.values()]
        missing = [seed for seed, row in by_seed.items() if row[section][field] is None]
        metrics[name] = {'mean': None if missing else _mean(values),
                         'worst': None if missing else worst(values), 'unavailable_seeds': missing}
    return {'seeds': [int(seed) for seed in by_seed], 'metrics': metrics, 'independent_physical_samples': False}


def _original_target(points, seeds):
    rows = {}
    for seed in seeds:
        selected = [r for r in points if r['model_seed'] == int(seed) and r['partition'] == 'in_family']
        accuracy = _metrics(selected)['accuracy']
        rows[seed] = {'planned_points': len(selected), 'accuracy': accuracy,
                      'at_least_target': accuracy >= .95 if accuracy is not None else None}
    return {'target': .95, 'by_seed': rows, 'numeric_comparison_only': True, 'admission_decision': False}


def score_rows(rows):
    """Score the complete normalized inventory returned by validate_bundle.

    All-planned accuracy is primary. Proper means are absent with any missing
    distribution; answered-only means are explicit. Information support labels
    subsets and never changes the submitted predictive distribution.
    """
    _require(type(rows) in (list, tuple) and bool(rows), 'nonempty planned score rows required')
    points = [_point(row) for row in rows]
    identities = [tuple(r[k] for k in IDENTITY) for r in points]
    _require(len(set(identities)) == len(identities), 'duplicate planned prediction point')
    points.sort(key=lambda r: tuple(r[k] for k in IDENTITY))
    participants = {}
    for name in sorted({r['participant'] for r in points}):
        group = [r for r in points if r['participant'] == name]
        by_seed = _by(group, lambda r: r['model_seed'], True)
        for seed, summary in by_seed.items():
            summary['by_family'] = _by([r for r in group if r['model_seed'] == int(seed)], lambda r: r['family'], True)
        participants[name] = {'aggregate': _summary(group, True), 'by_seed': by_seed,
            'by_family': _by(group, lambda r: r['family'], True), 'by_entity_count': _by(group, lambda r: len(r['ids'])),
            'by_action': _by(group, lambda r: r['action_kind']), 'by_partition': _by(group, lambda r: r['partition']),
            'seed_summary': _seed_summary(by_seed), 'original_in_family_target': _original_target(group, by_seed)}
    return _safe({'scoring_version': VERSION, 'gate_g1': 'NOT_ADMITTED', 'primary': 'all_planned_full_world_MAP_accuracy',
        'aggregate_scope': 'Inventory/descriptive across all arms and seeds; primary comparisons are per participant.',
        'interpretation': 'Descriptive only; correlated views and model seeds are not independent physical worlds.',
        'latency_scope': 'Reported per-forecast prediction region, nearest-rank quantiles; not end-to-end pipeline latency.',
        'trajectory_interpretation': 'All planned forecasts correct with delivered feedback; no trajectory likelihood or rollout claim.',
        'uncertainty_interpretation': 'Declared support defines answerability; no uniform prior, Bayes floor, or calibration claim.',
        'aggregate': _summary(points, True), 'participants': participants, 'points': points})


def _comparisons(points, reference):
    key = lambda r: (r['model_seed'], r['episode'], r['step'])
    baseline = {key(r): r for r in points if r['participant'] == reference}
    _require(bool(baseline), 'reference participant is missing')
    result = {}
    for name in sorted({r['participant'] for r in points} - {reference}):
        candidate = {key(r): r for r in points if r['participant'] == name}
        _require(candidate.keys() == baseline.keys(), 'reference/candidate planned inventories differ')
        transitions = {name: [] for name in ('correct_to_wrong', 'correct_to_abstain', 'correct_to_unproduced',
                                            'newly_correct', 'wrong_to_correct', 'abstain_to_correct', 'unproduced_to_correct')}
        common = 0
        for identity in sorted(baseline):
            a, b = baseline[identity], candidate[identity]
            common += a['status'] == b['status'] == 'ANSWERED'
            ident = {k: b[k] for k in ('model_seed', 'episode', 'step', 'lineage')}
            if a['correct'] and not b['correct']:
                suffix = {'ANSWERED': 'wrong', 'ABSTAIN': 'abstain', 'UNPRODUCED': 'unproduced'}[b['status']]
                transitions['correct_to_' + suffix].append(ident)
            if b['correct'] and not a['correct']:
                transitions['newly_correct'].append(ident)
                prefix = {'ANSWERED': 'wrong', 'ABSTAIN': 'abstain', 'UNPRODUCED': 'unproduced'}[a['status']]
                transitions[prefix + '_to_correct'].append(ident)
        n = len(baseline)
        result[name] = {'reference_participant': reference, 'planned_points': n,
            'common_supported': common, 'common_support_coverage': common / n,
            'reference_correct': sum(r['correct'] for r in baseline.values()),
            'candidate_correct': sum(r['correct'] for r in candidate.values()),
            'significance_claim': False, **transitions}
    return result


def evaluate(plan, inputs, oracle, traces):
    """Validate committed artifacts, then join evaluator-only targets and score."""
    from .acceptance_contract import validate_bundle
    bundle = validate_bundle(plan, inputs, oracle, traces)
    result = score_rows(bundle['rows'])
    result['metadata'] = deepcopy(bundle['metadata'])
    result['metadata']['source_sha256']['acceptance_scoring.py'] = sha256(Path(__file__).read_bytes()).hexdigest()
    result['comparisons'] = _comparisons(result['points'], bundle['metadata']['reference_participant'])
    json.dumps(result, allow_nan=False)
    return result


def main(argv=None):
    import argparse
    from .acceptance_contract import load_json, write_json
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('plan', 'inputs', 'oracle'):
        parser.add_argument('--' + name, required=True)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--trace', action='append', default=[])
    parser.add_argument('--trace-sha256', action='append', default=[])
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    _require(len(args.trace) == len(args.trace_sha256), 'every trace needs exactly one expected SHA')
    plan, inputs, oracle = [load_json(getattr(args, name), getattr(args, name + '_sha256'))
                           for name in ('plan', 'inputs', 'oracle')]
    traces = [load_json(path, digest) for path, digest in zip(args.trace, args.trace_sha256, strict=True)]
    report = evaluate(plan, inputs, oracle, traces)
    digest = write_json(args.output, report)
    print(json.dumps({'report_sha256': digest, 'gate_g1': 'NOT_ADMITTED'}, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
