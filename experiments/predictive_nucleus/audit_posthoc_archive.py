"""Read-only arithmetic audit of a completed, opened checkpoint replay.

No model, simulator, fitter, historical scorer or normalizer is imported.
This verifies recorded arithmetic and inventories, not independent science,
source authenticity, delivered sensor provenance or the G1 gate.
"""
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import permutations, product
import json
from math import fsum, isclose, isfinite, log
from pathlib import Path

ARMS = (('repeated', 'masked'), ('repeated', 'full'),
        ('augmented', 'masked'), ('augmented', 'full'))
SEEDS = (7, 11, 23, 37, 53)
MODELS = ('structured', 'flat', 'no_change', 'local_memory_with_persistence',
          'literal_history_memory', 'role_normalized_history_memory')
WORLDS = tuple(product((0, 1), repeat=3))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def equal(actual, expected, label):
    """Numeric comparison is explicit; bool and null cannot pass as numbers."""
    if type(expected) is float:
        require(type(actual) in (int, float) and isfinite(actual) and
                isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), label)
    else:
        require(type(actual) is type(expected) and actual == expected, label)


def distribution(rows, field):
    require(type(rows) is list and bool(rows), 'empty represented distribution')
    values = {}
    for row in rows:
        world, p = row['world'], row[field]
        require(type(world) is list and len(world) == 3 and
                all(type(b) is int and b in (0, 1) for b in world), 'invalid world')
        world = tuple(world)
        require(world not in values, 'duplicate represented world')
        require(type(p) in (int, float) and isfinite(p) and p >= 0, 'invalid mass')
        values[world] = p
    return values


def check_score(score, truth):
    """Recompute normalization and proper scores from retained raw masses."""
    if score['status'] == 'ABSTAIN':
        for key in ('map_world', 'map_correct', 'truth_probability', 'joint_log_score',
                    'joint_brier', 'world_probabilities', 'normalization'):
            require(score[key] is None, 'abstention contains numeric output')
        return None
    require(score['status'] == 'PREDICTED', 'unknown forecast status')
    audit = score['normalization']
    raw = distribution(audit['per_world'], 'before')
    after = distribution(audit['per_world'], 'after')
    total = fsum(raw.values())
    require(total > 0 and abs(total - 1) <= 1e-6, 'raw mass outside protocol tolerance')
    require(set(raw) == set(after), 'normalization changed support')
    normalized = {w: p / total for w, p in raw.items()}
    require(after == normalized, 'normalization is not uniform division')
    require(all(p <= 1 and (not raw[w] or p > 0) for w, p in after.items()), 'lost support')
    require(abs(fsum(after.values()) - 1) <= 1e-12, 'normalized mass not unit')
    raw_max = [list(w) for w in sorted(raw) if raw[w] == max(raw.values())]
    norm_max = [list(w) for w in sorted(after) if after[w] == max(after.values())]
    deltas = [after[w] - raw[w] for w in sorted(raw)]
    expected_audit = {
        'raw_total': total, 'normalized_total': fsum(after.values()),
        'mass_tolerance': 1e-6, 'normalized_tolerance': 1e-12,
        'raw_max_probability': max(raw.values()),
        'raw_max_overshoot': max(0.0, max(raw.values()) - 1),
        'raw_over_one_count': sum(p > 1 for p in raw.values()),
        'raw_maximizers': raw_max, 'normalized_maximizers': norm_max,
        'maximizer_set_changed': raw_max != norm_max,
        'raw_lexicographic_map': raw_max[0], 'normalized_lexicographic_map': norm_max[0],
        'lexicographic_map_changed': raw_max[0] != norm_max[0],
        'max_absolute_correction': max(map(abs, deltas)),
        'total_absolute_correction': fsum(map(abs, deltas)),
    }
    for key, value in expected_audit.items():
        equal(audit[key], value, 'normalization/' + key)
    for row in audit['per_world']:
        equal(row['delta'], row['after'] - row['before'], 'normalization delta')
    stored = distribution(score['world_probabilities'], 'probability')
    require(set(stored) == set(WORLDS), 'scored support inventory')
    require(stored == {w: after.get(w, 0.0) for w in WORLDS}, 'scored masses differ')
    best = norm_max[0]
    p = float(after.get(tuple(truth), 0.0))
    brier = fsum((after.get(w, 0.0) - (w == tuple(truth))) ** 2 for w in WORLDS)
    for key, value in {'map_world': best, 'map_correct': best == truth,
                       'truth_probability': p, 'joint_brier': brier}.items():
        equal(score[key], value, key)
    logs = {'clipped_log_loss': -log(max(p, 1e-12)),
            'uncapped_log_loss': -log(p) if p else None,
            'zero_probability': p == 0.0, 'floor_applied': p < 1e-12}
    for key, value in logs.items():
        equal(score['joint_log_score'][key], value, 'log_score/' + key)
    return stored


def check_summary(summary, values):
    answered = [r for r in values if r['status'] == 'PREDICTED']
    n, a = len(values), len(answered)
    c = sum(r['map_correct'] for r in answered)
    counts = {'queries': n, 'answered': a, 'abstained': n-a, 'correct': c, 'wrong': a-c,
              'coverage': a/n, 'accuracy_answered': c/a if a else None,
              'correct_per_query': c/n, 'wrong_per_query': (a-c)/n,
              'mean_joint_brier_answered': fsum(r['joint_brier'] for r in answered)/a if a else None}
    for key, value in counts.items():
        equal(summary[key], value, 'summary/' + key)
    if not a:
        require(summary['joint_log_loss'] is None, 'abstained summary has log loss')
        return
    logs = [r['joint_log_score'] for r in answered]
    zeros = sum(r['zero_probability'] for r in logs)
    expected = {'clipped_mean': fsum(r['clipped_log_loss'] for r in logs)/a,
                'floor_applied_count': sum(r['floor_applied'] for r in logs),
                'zero_probability_count': zeros, 'uncapped_mean_is_infinite': zeros > 0,
                'uncapped_mean': None if zeros else fsum(r['uncapped_log_loss'] for r in logs)/a}
    for key, value in expected.items():
        equal(summary['joint_log_loss'][key], value, 'summary log/' + key)


def run(directory):
    root = Path(directory)
    report_bytes = (root / 'report.json').read_bytes()
    require((root / 'COMPLETE').read_text().strip() == sha256(report_bytes).hexdigest(), 'report hash')
    report = json.loads(report_bytes)
    require(not (root / 'FAILED.json').exists(), 'failure marker present')
    require(report['status'] == 'POST_HOC_OPEN_PUBLIC_DEVELOPMENT_NOT_G1', 'not the frozen replay')
    require(report['verified_checkpoints'] == 40 and report['verified_control_tables'] == 6, 'fit inventory')
    rows, paired = defaultdict(list), defaultdict(Counter)
    diagnostics, case_count, total_rows = Counter(), 0, 0
    digest = sha256()
    with (root / 'cases.jsonl').open('rb') as stream:
        for line in stream:
            digest.update(line)
            case = json.loads(line)
            require(case['case'] == case_count, 'case order or duplicate')
            ids = tuple(case['original_ids'])
            require(len(set(ids)) == 3 and ids == tuple(sorted(ids)), 'identity inventory')
            expected = {(a, t, s, p) for a, t in ARMS for s in SEEDS for p in permutations(ids)}
            seen, histories, flat = set(), {}, defaultdict(dict)
            for row in case['case_rows']:
                a, t, seed, mapping = row['id_arm'], row['target'], row['seed'], row['mapping']
                require(set(mapping) == set(ids) and set(mapping.values()) == set(ids), 'invalid bijection')
                perm = tuple(mapping[x] for x in ids)
                key = (a, t, seed, perm)
                require(key in expected and key not in seen, 'view inventory')
                seen.add(key)
                history = json.dumps(row['public_history'], sort_keys=True)
                require(histories.setdefault(perm, history) == history, 'unpaired histories')
                require([step['step'] for step in row['steps']] == list(range(5)), 'step inventory')
                for step in row['steps']:
                    i = step['step']
                    require(step['ids'] == list(ids), 'score identity order')
                    require(type(step['truth']) is list and len(step['truth']) == 3 and
                            all(type(b) is int and b in (0, 1) for b in step['truth']), 'invalid truth')
                    require(set(step['models']) == set(MODELS), 'model inventory')
                    for name, score in step['models'].items():
                        check_score(score, step['truth'])
                        total_rows += 1
                        if score['status'] == 'PREDICTED':
                            audit = score['normalization']
                            diagnostics['raw_over_one_forecasts'] += audit['raw_over_one_count'] > 0
                            diagnostics['normalization_map_changes'] += audit['lexicographic_map_changed']
                            diagnostics['normalization_maximizer_changes'] += audit['maximizer_set_changed']
                        rows[(a, t, seed, i, name)].append({k: score[k] for k in (
                            'status', 'map_correct', 'joint_brier', 'joint_log_score')})
                    outcome = step['models']['flat']['map_correct']
                    require(type(outcome) is bool, 'flat abstention')
                    if i != 2:
                        flat[(seed, perm, i)][(a, t)] = outcome
            require(seen == expected, 'missing views')
            for (seed, _, _), outcomes in flat.items():
                require(set(outcomes) == set(ARMS), 'missing paired arm')
                for label, before, after in (
                    ('target/repeated', ARMS[0], ARMS[1]), ('target/augmented', ARMS[2], ARMS[3]),
                    ('id/masked', ARMS[0], ARMS[2]), ('id/full', ARMS[1], ARMS[3])):
                    b, a = outcomes[before], outcomes[after]
                    paired[(seed, label)].update({'queries': 1, 'before_correct': int(b),
                        'after_correct': int(a), 'fixed': int(a and not b), 'regressed': int(b and not a)})
            case_count += 1
    require(case_count == 64 and total_rows == 230400, 'complete case/forecast inventory')
    require(digest.hexdigest() == report['cases_sha256'], 'case bytes hash')
    seen = set()
    for summary in report['summaries']:
        key = tuple(summary[k] for k in ('id_arm', 'target', 'seed', 'step', 'model'))
        require(key in rows and key not in seen and len(rows[key]) == 384, 'summary inventory')
        seen.add(key)
        check_summary(summary, rows[key])
    require(seen == set(rows) and len(seen) == 600, 'missing summary')
    seen = set()
    for contrast in report['paired_contrasts']:
        key = (contrast['seed'], contrast['contrast'])
        require(key in paired and key not in seen, 'contrast inventory')
        seen.add(key)
        counts = paired[key]
        require(counts['queries'] == 1536, 'contrast denominator')
        for field, value in counts.items():
            equal(contrast[field], value, 'contrast/' + field)
        equal(contrast['difference'], (counts['after_correct']-counts['before_correct'])/1536, 'contrast difference')
    require(seen == set(paired) and len(seen) == 20, 'missing contrast')
    primary_seen = set()
    for item in report['primary']:
        key = (item['id_arm'], item['target'], item['seed'])
        require(key not in primary_seen and key[:2] in ARMS and key[2] in SEEDS, 'primary inventory')
        primary_seen.add(key)
        correct = sum(r['map_correct'] for i in (0, 1, 3, 4)
                      for r in rows[(*key, i, 'flat')])
        for name, value in {'queries': 1536, 'correct': correct, 'accuracy': correct/1536}.items():
            equal(item[name], value, 'primary/' + name)
    require(len(primary_seen) == 20, 'missing primary score')
    interaction_seen = set()
    for item in report['interactions']:
        seed = item['seed']
        require(seed in SEEDS and seed not in interaction_seen, 'interaction inventory')
        interaction_seen.add(seed)
        repeated, augmented = paired[(seed, 'target/repeated')], paired[(seed, 'target/augmented')]
        value = ((augmented['after_correct']-augmented['before_correct']) -
                 (repeated['after_correct']-repeated['before_correct']))/1536
        equal(item['difference_in_differences'], value, 'interaction')
    require(interaction_seen == set(SEEDS), 'missing interaction')
    return {'status': 'ARCHIVE_ARITHMETIC_VERIFIED_NOT_G1', 'cases': case_count,
            'forecast_records': total_rows, 'summary_cells': len(rows), 'paired_contrasts': len(paired),
            'primary_cells': len(primary_seen), 'interaction_cells': len(interaction_seen),
            'report_sha256': sha256(report_bytes).hexdigest(), 'cases_sha256': digest.hexdigest(),
            'normalization': dict(diagnostics),
            'limits': 'Arithmetic/inventory audit only. Not sensor provenance, independent challenge or G1 admission.'}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory')
    args = parser.parse_args()
    print(json.dumps(run(args.directory), sort_keys=True, allow_nan=False))
