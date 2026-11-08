"""Saved-record scoring only: no learner, simulator, fitting or oracle execution."""
import argparse
from collections import Counter
from hashlib import sha256
import json
import lzma
import math
from pathlib import Path

SEEDS = (7, 11, 23, 37, 53)
ARMS = ('native', 'flat', 'rule')
LAWS = ('nand', 'nor')
FEES = (('cheap', .05), ('prohibitive', 1.), ('unavailable', None))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    data = Path(path).read_bytes()
    return json.loads(lzma.decompress(data) if str(path).endswith('.xz') else data)


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def verify_manifest(directory, expected_data_sha=None):
    directory = Path(directory)
    manifest = load(directory / 'manifest.json')
    if expected_data_sha is not None:
        require(manifest['data_sha256'] == expected_data_sha, 'raw manifest data binding differs')
    for name, item in manifest['artifacts'].items():
        require(Path(name).name == name and digest(directory / name) == item['sha256'],
                'manifest file hash differs: ' + name)
    return manifest


def vector(values):
    require(isinstance(values, list) and len(values) == 8 and
            all(type(x) in (int, float) and math.isfinite(x) and 0 <= x <= 1 + 1e-10
                for x in values) and abs(math.fsum(values) - 1) <= 1e-10,
            'invalid endpoint distribution')
    return values


def metrics(predictions, rows, condition, target='target_y'):
    """Observed proper scores and expected regret against the public-history law."""
    points, excess, optimum, oracle_brier, confident_errors, zero = [], [], [], [], [], []
    confidence_count = 0
    for p, row in zip(predictions, rows, strict=True):
        vector(p)
        y = row[target]
        q = vector(row['distributions'][condition]) if condition else [int(i == y) for i in range(8)]
        require(q[y] > 0, 'observed target outside conditional support')
        choice = max(range(8), key=p.__getitem__)
        correct = int(choice == y)
        brier = math.fsum((v - int(i == y)) ** 2 for i, v in enumerate(p))
        nll = -math.log(p[y]) if p[y] else math.inf
        points.append((row['id'], correct, brier, nll))
        excess.append(math.fsum((a - b) ** 2 for a, b in zip(p, q)))
        optimum.append(max(q)); oracle_brier.append(1 - math.fsum(v * v for v in q))
        confidence_count += int(p[choice] >= .95)
        if p[choice] >= .95 and not correct:
            confident_errors.append(row['id'])
        if not p[y]:
            zero.append(row['id'])
    n = len(points)
    require(n > 0, 'empty scored stratum')
    mean = lambda values: math.fsum(values) / n
    return ({'count': n, 'correct': sum(p[1] for p in points),
             'accuracy': sum(p[1] for p in points) / n,
             'brier': mean(p[2] for p in points),
             'nll': 'Infinity' if zero else mean(p[3] for p in points),
             'excess_brier': mean(excess), 'conditional_accuracy_optimum': mean(optimum),
             'oracle_expected_brier': mean(oracle_brier),
             'confident_count': confidence_count, 'confident_errors': confident_errors,
             'confident_error_fraction': len(confident_errors) / n,
             'confident_coverage': confidence_count / n,
             'confident_error_rate': len(confident_errors) / confidence_count if confidence_count else None,
             'zero_probability_cases': zero}, points)


def validate_view(view, rows):
    require(set(view) == {'probe', 'before', 'branches', 'after_second', 'protected'}, 'view fields differ')
    require(all(len(values) == len(rows) for values in view.values()), 'view length differs')
    for i, row in enumerate(rows):
        for key in ('probe', 'before', 'after_second', 'protected'):
            vector(view[key][i])
        branches = view['branches'][i]
        require(isinstance(branches, list) and len(branches) == 8, 'branch inventory differs')
        for branch in branches:
            vector(branch)
        require(max(abs(a - b) for a, b in zip(branches[row['second_y']], view['after_second'][i])) <= 1e-12,
                'actual second answer disagrees with saved conditional forecast')


def validate_decisions(decisions, view):
    require(set(decisions) == {'value', 'asks'} and
            len(decisions['value']) == len(decisions['asks']) == len(view['before']),
            'saved decision inventory differs')
    for i, (value, asks) in enumerate(zip(decisions['value'], decisions['asks'], strict=True)):
        expected = math.fsum(w * max(branch) for w, branch in zip(view['probe'][i], view['branches'][i])) - max(view['before'][i])
        require(type(value) in (int, float) and math.isfinite(value) and abs(value - expected) <= 1e-12,
                'saved pre-answer value differs')
        require(isinstance(asks, list) and len(asks) == 3 and all(type(ask) is bool for ask in asks) and
                asks == [fee is not None and expected > fee + 1e-12 for _, fee in FEES],
                'saved pre-answer decisions differ')


def policy(view, rows, fee):
    """Decide from forecasts, then use the delivered answer solely to score the choice."""
    points, values, residuals, worse, improved = [], [], [], [], []
    no_query = 0
    for i, row in enumerate(rows):
        probe, before, branches = (view[k][i] for k in ('probe', 'before', 'branches'))
        value = math.fsum(w * max(branch) for w, branch in zip(probe, branches)) - max(before)
        ask = fee is not None and value > fee + 1e-12
        chosen = branches[row['second_y']] if ask else before
        correct = int(max(range(8), key=chosen.__getitem__) == row['target_y'])
        baseline = int(max(range(8), key=before.__getitem__) == row['target_y'])
        net = correct - fee if ask else float(correct)
        delta = net - baseline
        points.append((row['id'], correct, net, int(ask)))
        values.append(value); no_query += baseline
        residuals.append(max(abs(before[y] - math.fsum(probe[a] * branches[a][y] for a in range(8)))
                             for y in range(8)))
        if delta < 0:
            worse.append({'id': row['id'], 'net_delta': delta})
        elif delta > 0:
            improved.append({'id': row['id'], 'net_delta': delta})
    n = len(rows)
    gross, net, paid = sum(p[1] for p in points), math.fsum(p[2] for p in points), sum(p[3] for p in points)
    return ({'count': n, 'correct': gross, 'accuracy': gross / n, 'paid_questions': paid,
             'gross_reward': gross, 'net_reward': net, 'mean_net_reward': net / n,
             'no_query_correct': no_query, 'gross_gain_from_query': gross - no_query,
             'net_gain_from_query': net - no_query,
             'estimated_value_mean': math.fsum(values) / n,
             'coherence_linf_mean': math.fsum(residuals) / n, 'coherence_linf_max': max(residuals),
             'query_adverse_cases': worse, 'query_beneficial_cases': improved}, points)


def paired(candidate, reference, policy_points=False):
    regressions, repairs, adverse, nll_adverse = [], [], [], []
    for a, b in zip(candidate, reference, strict=True):
        require(a[0] == b[0], 'paired identities differ')
        if b[1] and not a[1]: regressions.append(a[0])
        if a[1] and not b[1]: repairs.append(a[0])
        delta = a[2] - b[2]
        if (delta < 0 if policy_points else delta > 0):
            adverse.append({'id': a[0], 'delta': delta})
        if not policy_points and a[3] > b[3]:
            nll_adverse.append({'id': a[0], 'delta': a[3] - b[3] if math.isfinite(a[3]) else 'Infinity'})
    return {'exact_regressions': regressions, 'exact_repairs': repairs,
            'net_regressions' if policy_points else 'brier_regressions': adverse,
            **({} if policy_points else {'nll_regressions': nll_adverse})}


def gates(arms):
    n, f = arms['native'], arms['flat']
    both, cleared = n['both'], n['cleared_both']
    cheap = lambda arm, view: arm['policies'][view]['cheap']['mean_net_reward']
    return {'attainable_accuracy': both['accuracy'] + .02 >= both['conditional_accuracy_optimum'] - 1e-12,
            'excess_brier': both['excess_brier'] <= .02,
            'protected_retention': n['protected']['accuracy'] >= .95,
            'confident_errors': both['confident_error_fraction'] <= .01,
            'flat_brier': both['brier'] <= f['both']['brier'] + 1e-12,
            'retained_brier_gain': cleared['brier'] - both['brier'] > 1e-4,
            'flat_cheap_net': cheap(n, 'retained') >= cheap(f, 'retained') - 1e-12,
            'retained_cheap_net': cheap(n, 'retained') >= cheap(n, 'cleared') - 1e-12}


def score(prepared, raw, output):
    prepared, raw, output = map(Path, (prepared, raw, output))
    require(not output.exists(), 'output must be a fresh directory')
    manifest = verify_manifest(prepared)
    data_sha = digest(prepared / 'manifest.json')
    require('oracle.json.xz' in manifest['artifacts'], 'oracle missing from data manifest')
    raw_manifest = verify_manifest(raw, data_sha) if (raw / 'manifest.json').exists() else None
    if raw_manifest:
        require({f'raw-{seed}-{arm}.json.xz' for seed in SEEDS for arm in ARMS} <= raw_manifest['artifacts'].keys(),
                'raw manifest omits required forecasts')
    oracle = load(prepared / 'oracle.json.xz')
    rows = oracle['rows']; ids = [r['id'] for r in rows]
    require(len(rows) == 12288 and len(set(ids)) == len(ids) and
            Counter(r['law'] for r in rows) == Counter(nand=6144, nor=6144), 'oracle inventory differs')
    for row in rows:
        require(all(type(row[k]) is int and 0 <= row[k] < 8 for k in
                    ('first_y', 'second_y', 'target_y', 'protected_y')), 'invalid observed endpoint')
        require(set(row['distributions']) == {'base', 'first', 'both', 'second'}, 'conditional inventory differs')
        for q in row['distributions'].values(): vector(q)
    cells, raw_hashes, raw_versions, checkpoints, source_commits = {}, {}, set(), {}, {}
    strata = {law: [i for i, row in enumerate(rows) if row['law'] == law] for law in LAWS}
    for seed in SEEDS:
        summaries = {law: {} for law in LAWS}; details = {law: {} for law in LAWS}
        for arm in ARMS:
            name = f'raw-{seed}-{arm}.json.xz'; saved = load(raw / name)
            require(saved['seed'] == seed and saved['arm'] == arm and saved['ids'] == ids and
                    saved['data_sha256'] == data_sha, 'raw identity or prepared hash differs')
            require(isinstance(saved['version'], str) and saved['version'], 'missing raw schema version')
            raw_versions.add(saved['version']); raw_hashes[name] = digest(raw / name)
            checkpoints[f'{seed}/{arm}'] = saved['checkpoint_sha256']
            source_commits[name] = saved['source_commit']
            if raw_manifest:
                require(saved['source_commit'] == raw_manifest['source_commit'], 'raw manifest source differs')
            require(isinstance(saved['source_commit'], str) and len(saved['source_commit']) == 40 and
                    all(c in '0123456789abcdef' for c in saved['source_commit']), 'invalid raw source commit')
            checkpoint = saved['checkpoint_sha256']
            require(checkpoint == 'SUPPLIED_RULE' if arm == 'rule' else
                    isinstance(checkpoint, str) and len(checkpoint) == 64 and
                    all(c in '0123456789abcdef' for c in checkpoint), 'invalid checkpoint identity')
            require(set(saved['predictions']) == {'base_target', 'after_first', 'after_second', 'protected'} and
                    set(saved['views']) == set(saved['decisions']) == {'retained', 'cleared'}, 'raw forecast inventory differs')
            for predictions in saved['predictions'].values():
                require(len(predictions) == len(rows), 'forecast length differs')
                for p in predictions: vector(p)
            for view_name, view in saved['views'].items():
                validate_view(view, rows)
                validate_decisions(saved['decisions'][view_name], view)
            for key, canonical in (('before', 'after_first'), ('after_second', 'after_second'), ('protected', 'protected')):
                require(saved['views']['retained'][key] == saved['predictions'][canonical], 'retained canonical forecasts differ')
            require(saved['views']['cleared']['before'] == saved['predictions']['base_target'], 'cleared prefix differs')
            for law, indices in strata.items():
                selected = [rows[i] for i in indices]; summary, points = {}, {}
                fields = (('base', saved['predictions']['base_target'], 'base', 'target_y'),
                          ('first', saved['predictions']['after_first'], 'first', 'target_y'),
                          ('both', saved['predictions']['after_second'], 'both', 'target_y'),
                          ('protected', saved['predictions']['protected'], None, 'protected_y'),
                          ('cleared_both', saved['views']['cleared']['after_second'], 'second', 'target_y'),
                          ('cleared_protected', saved['views']['cleared']['protected'], None, 'protected_y'))
                for label, forecasts, condition, target in fields:
                    summary[label], points[label] = metrics([forecasts[i] for i in indices], selected, condition, target)
                summary['strata'] = {}
                selectors = [('cause', lambda r: r['cause']), ('scope', lambda r: r['target_scope']),
                             ('identifiability', lambda r: 'identifiable' if max(r['distributions']['both']) == 1 else 'ambiguous')]
                for kind, select in selectors:
                    for value in sorted({select(row) for row in selected}):
                        positions = [i for i in indices if select(rows[i]) == value]
                        sub, _ = metrics([saved['predictions']['after_second'][i] for i in positions],
                                         [rows[i] for i in positions], 'both')
                        for key in ('confident_errors', 'zero_probability_cases'): sub[key + '_count'] = len(sub.pop(key))
                        summary['strata'][kind + '/' + str(value)] = sub
                summary['policies'], points['policies'] = {}, {}
                for view_name, full_view in saved['views'].items():
                    view = {k: [v[i] for i in indices] for k, v in full_view.items()}
                    summary['policies'][view_name], points['policies'][view_name] = {}, {}
                    for label, fee in FEES:
                        summary['policies'][view_name][label], points['policies'][view_name][label] = policy(view, selected, fee)
                summaries[law][arm], details[law][arm] = summary, points
        for law in LAWS:
            comparisons = {}
            n = details[law]['native']
            for reference in ('flat', 'rule', 'cleared'):
                r = details[law][reference] if reference != 'cleared' else n
                comparisons[reference] = {stage: paired(n[stage], r['cleared_' + stage] if reference == 'cleared' else r[stage])
                                          for stage in (('both', 'protected') if reference == 'cleared' else ('base', 'first', 'both', 'protected'))}
                comparisons[reference]['policies'] = {label: paired(n['policies']['retained'][label],
                    r['policies']['cleared' if reference == 'cleared' else 'retained'][label], True) for label, _ in FEES}
            cells[f'{law}/{seed}'] = {'arms': summaries[law], 'gates': gates(summaries[law]), 'paired': comparisons}
    require(len(raw_versions) == 1, 'raw schema versions differ')
    passed = all(all(cell['gates'].values()) for cell in cells.values())
    result = {'version': 'temporal-native-score-v1', 'data_sha256': data_sha,
              'oracle_sha256': digest(prepared / 'oracle.json.xz'), 'raw_sha256': raw_hashes,
              'raw_manifest_sha256': digest(raw / 'manifest.json') if raw_manifest else None,
              'checkpoint_sha256': checkpoints, 'raw_source_commits': source_commits,
              'raw_version': next(iter(raw_versions)),
              'scorer_sha256': digest(__file__), 'cells': cells,
              'decision': 'KEEP_NATIVE_TEMPORAL_UPDATER' if passed else 'REVISE_NATIVE_TEMPORAL_UPDATER',
              'g5_admission': 'NOT_ADMITTED', 'cases_per_seed': len(rows),
              'worst_native_cheap_net': min(c['arms']['native']['policies']['retained']['cheap']['mean_net_reward'] for c in cells.values())}
    data = (json.dumps(result, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    output.mkdir(parents=True, exist_ok=False); (output / 'score.json').write_bytes(data)
    return {'decision': result['decision'], 'score_sha256': sha256(data).hexdigest(), 'cells': len(cells)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ('prepared', 'raw', 'output'): parser.add_argument('--' + argument, required=True, type=Path)
    print(json.dumps(score(**vars(parser.parse_args())), sort_keys=True))
