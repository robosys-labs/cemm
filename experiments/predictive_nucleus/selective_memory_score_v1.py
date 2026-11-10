"""Vectorized saved-array scoring; no learner, simulator or oracle execution."""
import argparse
from hashlib import sha256
import json
import lzma
from pathlib import Path

import numpy as np

SEEDS = (7, 11, 23, 37, 53)
ARMS = ('selective', 'native', 'flat')
STAGES = ('teaching', 'claims', 'pair', 'third', 'final', 'cleared_final')
FEES = (('cheap', .05), ('prohibitive', 1.), ('unavailable', None))
RECORDS = 36864


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load(path):
    data = Path(path).read_bytes()
    return json.loads(lzma.decompress(data) if str(path).endswith('.xz') else data)


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def verify_manifest(directory, expected_data_sha=None):
    directory = Path(directory)
    manifest = load(directory / 'manifest.json')
    if expected_data_sha is not None:
        require(manifest['data_sha256'] == expected_data_sha, 'prepared-data binding differs')
    for name, item in manifest['artifacts'].items():
        require(Path(name).name == name and digest(directory / name) == item['sha256'],
                'artifact hash differs: ' + name)
        require((directory / name).stat().st_size == item['bytes'], 'artifact size differs: ' + name)
    return manifest


def probabilities(values, shape=None):
    p = np.asarray(values, dtype=np.float64)
    require((shape is None or p.shape == shape) and p.ndim >= 1 and p.shape[-1] == 8,
            'endpoint distribution shape differs')
    require(np.isfinite(p).all() and (p >= 0).all() and (p <= 1 + 1e-10).all()
            and (np.abs(p.sum(-1) - 1) <= 1e-10).all(), 'invalid endpoint distribution')
    return p


def endpoints(values, shape):
    y = np.asarray(values)
    require(y.shape == shape and np.issubdtype(y.dtype, np.integer)
            and ((y >= 0) & (y < 8)).all(), 'invalid observed endpoint')
    return y


def point_scores(p, y, q=None):
    """q is fixed by the observed prefix BEFORE any hidden-stratum selection."""
    p = probabilities(p)
    y = endpoints(y, p.shape[:-1])
    hit = np.take_along_axis(p, y[..., None], -1)[..., 0]
    chosen = p.argmax(-1)
    confidence = p.max(-1)
    with np.errstate(divide='ignore'):
        nll = -np.log(hit)
    points = {'correct': chosen == y, 'brier': ((p - np.eye(8)[y]) ** 2).sum(-1),
              'nll': nll, 'confident': confidence >= .95,
              'confident_errors': (confidence >= .95) & (chosen != y), 'zero': hit == 0}
    if q is not None:
        q = probabilities(q, p.shape)
        require((np.take_along_axis(q, y[..., None], -1)[..., 0] > 0).all(),
                'observed target outside conditional support')
        points.update(excess_brier=((p - q) ** 2).sum(-1), oracle_correct=q.argmax(-1) == y,
                      expected_attainable_accuracy=q.max(-1), oracle_expected_brier=1 - (q * q).sum(-1))
    return points


def selector(mask, shape):
    mask = np.asarray(mask, dtype=bool)
    return np.broadcast_to(mask[:, None] if mask.ndim == 1 else mask, shape)


def finite(value):
    return float(value) if np.isfinite(value) else 'Infinity'


def summarize(points, mask):
    selected = selector(mask, points['correct'].shape)
    n = int(selected.sum())
    if not n:
        return {'count': 0, 'accuracy': None, 'status': 'N/A'}
    mean = lambda key: float(points[key][selected].mean())
    total = lambda key: int(points[key][selected].sum())
    result = {'count': n, 'correct': total('correct'), 'accuracy': mean('correct'),
              'brier': mean('brier'), 'nll': finite(mean('nll')),
              'confident_count': total('confident'), 'confident_errors': total('confident_errors'),
              'confident_error_fraction': mean('confident_errors'), 'confident_coverage': mean('confident'),
              'zero_probability_count': total('zero')}
    result['confident_error_rate'] = (result['confident_errors'] / result['confident_count']
                                      if result['confident_count'] else None)
    if 'oracle_correct' in points:
        result.update(oracle_realized_accuracy=mean('oracle_correct'),
                      expected_attainable_accuracy=mean('expected_attainable_accuracy'),
                      oracle_expected_brier=mean('oracle_expected_brier'), excess_brier=mean('excess_brier'))
    if 'paid' in points:
        net = float(points['net'][selected].sum())
        result.update(paid_questions=total('paid'), gross_reward=total('correct'), net_reward=net,
                      mean_net_reward=mean('net'), no_query_correct=total('baseline'),
                      gross_gain_from_query=total('correct') - total('baseline'),
                      net_gain_from_query=net - total('baseline'), estimated_value_mean=mean('value'),
                      coherence_linf_mean=mean('coherence'),
                      coherence_linf_max=float(points['coherence'][selected].max()))
    return result


def validate_optional(raw, answer, prefix='optional_'):
    n = len(answer)
    probe, before, after = (probabilities(raw[prefix + key], (n, 2, 8))
                            for key in ('probe', 'before', 'after'))
    branches = probabilities(raw[prefix + 'branches'], (n, 2, 8, 8))
    answer = endpoints(answer, (n, 2))
    actual = branches[np.arange(n)[:, None], np.arange(2)[None, :], answer]
    require(np.max(np.abs(actual - after)) <= 1e-12, 'actual answer branch differs')
    expected = (probe * branches.max(-1)).sum(-1) - before.max(-1)
    value, asks = np.asarray(raw[prefix + 'value']), np.asarray(raw[prefix + 'asks'])
    require(value.shape == (n, 2) and np.isfinite(value).all()
            and np.max(np.abs(value - expected)) <= 1e-12, 'pre-answer value differs')
    expected_asks = np.stack([expected > fee + 1e-12 if fee is not None else np.zeros_like(expected, bool)
                              for _, fee in FEES], -1)
    require(asks.shape == (n, 2, 3) and asks.dtype == np.bool_ and np.array_equal(asks, expected_asks),
            'pre-answer decisions differ')


def policy_points(raw, y, q, fee_index, cleared=False):
    prefix = 'cleared_optional_' if cleared else 'optional_'
    before, after, probe, branches = (raw[prefix + k] for k in ('before', 'after', 'probe', 'branches'))
    ask = raw[prefix + 'asks'][..., fee_index]
    chosen = np.where(ask[..., None], after, before)
    conditional = np.where(ask[..., None], q['after'], q['before'])
    points = point_scores(chosen, y, conditional)
    fee = FEES[fee_index][1] or 0.
    points.update(paid=ask, net=points['correct'].astype(float) - fee * ask,
                  baseline=before.argmax(-1) == y, value=raw[prefix + 'value'],
                  coherence=np.abs(before - (probe[..., None] * branches).sum(-2)).max(-1))
    return points


def gates(selective, flat):
    final, cleared = selective['stages']['final'], selective['stages']['cleared_final']
    retained = selective['retention']
    cheap = lambda arm, view: arm['policies'][view]['cheap']['mean_net_reward']
    return {'attainable_accuracy': final['accuracy'] + .02 >= final['oracle_realized_accuracy'] - 1e-12,
            'excess_brier': final['excess_brier'] <= .02,
            'protected_retention': retained['accuracy'] >= .95 if retained['count'] else None,
            'confident_errors': final['confident_error_fraction'] <= .01,
            'flat_brier': final['brier'] <= flat['stages']['final']['brier'] + 1e-12,
            'retained_brier_gain': cleared['brier'] - final['brier'] > 1e-4,
            'flat_cheap_net': cheap(selective, 'retained') >= cheap(flat, 'retained') - 1e-12,
            'retained_cheap_net': cheap(selective, 'retained') >= cheap(selective, 'cleared') - 1e-12}


def adverse(points, ids):
    return {name: ids[mask].tolist() for name, mask in (
        ('incorrect', ~points['correct']), ('confident_errors', points['confident_errors']),
        ('zero_probability', points['zero']))}


def paired(candidate, reference, ids):
    result = {'exact_regressions': ids[reference['correct'] & ~candidate['correct']].tolist(),
              'exact_repairs': ids[candidate['correct'] & ~reference['correct']].tolist()}
    for metric in ('brier', 'nll', 'net'):
        if metric not in candidate:
            continue
        a, b = candidate[metric], reference[metric]
        bad = a < b if metric == 'net' else a > b
        result[metric + '_regressions'] = [
            {'id': str(identity), 'delta': finite(delta)}
            for identity, delta in zip(ids[bad], a[bad] - b[bad], strict=True)]
    return result


def pool(summaries):
    """Pool saved sufficient statistics; seeds remain repeated evaluations."""
    n = sum(s['count'] for s in summaries)
    totals = {'correct', 'confident_count', 'confident_errors', 'zero_probability_count', 'paid_questions',
              'gross_reward', 'net_reward', 'no_query_correct', 'gross_gain_from_query', 'net_gain_from_query'}
    result = {'count': n}
    for key in summaries[0]:
        if key in ('count', 'confident_error_rate'):
            continue
        values = [s[key] for s in summaries]
        if 'Infinity' in values:
            result[key] = 'Infinity'
        elif key in totals:
            result[key] = sum(values)
        elif key.endswith('_max'):
            result[key] = max(values)
        else:
            result[key] = sum(value * s['count'] for value, s in zip(values, summaries, strict=True)) / n
    result['confident_error_rate'] = (result['confident_errors'] / result['confident_count']
                                      if result['confident_count'] else None)
    return result


def score(prepared, raw, output):
    prepared, raw, output = map(Path, (prepared, raw, output))
    require(not output.exists(), 'output must be a fresh directory')
    data_manifest = verify_manifest(prepared)
    require('oracle.json.xz' in data_manifest['artifacts'], 'oracle is not bound by prepared manifest')
    data_sha = digest(prepared / 'manifest.json')
    raw_manifest = verify_manifest(raw, data_sha)
    require(raw_manifest['fit_sha256'] == digest(raw / 'fit-manifest.json'), 'fit manifest binding differs')
    require(raw_manifest['arms'] == list(ARMS) and raw_manifest['seeds'] == list(SEEDS)
            and raw_manifest['records'] == RECORDS, 'raw study inventory differs')
    fits = load(raw / 'fit-manifest.json')
    require(fits['data_sha256'] == data_sha and fits['fits'] == len(ARMS) * len(SEEDS)
            and fits['source_sha256'] == raw_manifest['source_sha256'], 'fit/source binding differs')
    names = {f'raw-{arm}-{seed}.npz' for arm in ARMS for seed in SEEDS}
    require(names <= raw_manifest['artifacts'].keys(), 'missing required raw bank')
    rows = load(prepared / 'oracle.json.xz')['rows']
    base_ids = [r['id'] for r in rows]
    n = len(rows)
    require(n == RECORDS and len(set(base_ids)) == n and raw_manifest['ids'] == base_ids
            and raw_manifest['id_order_sha256'] == sha256(canonical(base_ids)).hexdigest(), 'row order differs')
    ids = np.array([[identity + '/word:' + str(w) for w in range(2)] for identity in base_ids])
    probe_ids = np.array([[identity + '/probe:' + str(w) for w in range(4)] for identity in base_ids])
    y = endpoints([r['target_y'] for r in rows], (n, 2))
    probe_y = endpoints([r['probe_y'] for r in rows], (n, 4))
    q = {stage: probabilities([r['distributions'][stage] for r in rows], (n, 2, 8)) for stage in STAGES}
    probe_q = probabilities([r['next_probe'] for r in rows], (n, 4, 8))
    optional_q = {view: {key: probabilities([r[view][key] for r in rows], (n, 2, 8))
                         for key in ('before', 'after')} for view in ('optional', 'cleared_optional')}
    answer = endpoints([r['optional']['answer'] for r in rows], (n, 2))
    require(np.array_equal(answer, [r['cleared_optional']['answer'] for r in rows]), 'optional endpoints differ')
    require(np.array_equal(optional_q['optional']['before'], q['pair'])
            and np.array_equal(optional_q['cleared_optional']['before'], q['claims']), 'oracle prefixes differ')
    meta = {key: np.asarray([r[key] for r in rows]) for key in
            ('law', 'target_change_mask', 'persistent_change_mask', 'causes', 'target_scope')}
    laws, change = meta['law'], meta['target_change_mask']
    require(set(laws) == {'nand', 'nor'} and all(np.sum(laws == law) == n // 2 for law in set(laws)),
            'law inventory differs')
    require(set(change) == set(range(4)) and set(meta['persistent_change_mask']) == set(range(4)),
            'change mask inventory differs')
    unchanged = (change[:, None] & (1 << np.arange(2))) == 0
    del rows
    output.mkdir(parents=True)
    cells, diagnostics, pooled, adverse_counts = {}, {}, {arm: {} for arm in ARMS}, {}
    with lzma.open(output / 'adverse.json.xz', 'wt', encoding='utf-8') as sink:
        sink.write('{"id_schema":"original_id/word:w or original_id/probe:p","records":[')
        first = True

        def emit(label, records):
            nonlocal first
            sink.write('' if first else ',')
            first = False
            json.dump({'label': label, **records}, sink, sort_keys=True, separators=(',', ':'), allow_nan=False)
            adverse_counts[label] = {key: len(value) for key, value in records.items()}

        for seed in SEEDS:
            saved_points = {}
            for arm in ARMS:
                with np.load(raw / f'raw-{arm}-{seed}.npz', allow_pickle=False) as bank:
                    arrays = dict(bank)
                require(np.array_equal(arrays['optional_y'], answer), 'raw optional answers differ')
                for stage in STAGES:
                    probabilities(arrays[stage], (n, 2, 8))
                probabilities(arrays['next_probe'], (n, 4, 8))
                for prefix, canonical_stage in (('optional_', 'pair'), ('cleared_optional_', 'claims')):
                    validate_optional(arrays, answer, prefix)
                    require(np.max(np.abs(arrays[prefix + 'before'] - arrays[canonical_stage])) <= 1e-12,
                            'optional prefix differs from fixed-sequence prefix')
                points = {stage: point_scores(arrays[stage], y, q[stage]) for stage in STAGES}
                points['next_probe'] = point_scores(arrays['next_probe'], probe_y, probe_q)
                points['policies'] = {view: {label: policy_points(arrays, y, optional_q[
                    'cleared_optional' if view == 'cleared' else 'optional'], i, view == 'cleared')
                    for i, (label, _) in enumerate(FEES)} for view in ('retained', 'cleared')}
                saved_points[arm] = points
                all_rows = np.ones(n, bool)
                for stage in (*STAGES, 'next_probe'):
                    pooled[arm].setdefault(stage, []).append(summarize(points[stage], all_rows))
                    emit(f'{seed}/{arm}/{stage}', adverse(points[stage], probe_ids if stage == 'next_probe' else ids))
                pooled[arm].setdefault('retention', []).append(summarize(points['final'], unchanged))
                for view in ('retained', 'cleared'):
                    for label, _ in FEES:
                        item = points['policies'][view][label]
                        pooled[arm].setdefault(view + '/' + label, []).append(summarize(item, all_rows))
                        emit(f'{seed}/{arm}/{view}/{label}', {
                            **adverse(item, ids), 'query_net_regressions': [
                                {'id': str(identity), 'delta': float(delta)} for identity, delta in zip(
                                    ids[item['net'] < item['baseline']],
                                    (item['net'] - item['baseline'])[item['net'] < item['baseline']], strict=True)]})
                for law in ('nand', 'nor'):
                    for mask in range(4):
                        selected = (laws == law) & (change == mask)
                        key = f'{law}/{seed}/{mask}'
                        require(selected.any(), 'empty registered cell')
                        cell = {'stages': {stage: summarize(points[stage], selected) for stage in STAGES},
                                'retention': summarize(points['final'], selected[:, None] & unchanged),
                                'words': {str(w): summarize(points['final'], selected[:, None]
                                          & (np.arange(2) == w)) for w in range(2)},
                                'policies': {view: {label: summarize(item, selected) for label, item in items.items()}
                                             for view, items in points['policies'].items()}}
                        cells.setdefault(key, {'arms': {}})['arms'][arm] = cell
                diag = {}
                for field in ('persistent_change_mask', 'causes', 'target_scope'):
                    values = meta[field]
                    for value in sorted(set(values.ravel())):
                        mask = values == value
                        for law in ('nand', 'nor'):
                            selected = selector(mask, (n, 2)) & (laws == law)[:, None]
                            diag[f'{law}/{field}/{value}'] = summarize(points['final'], selected)
                diagnostics[f'{seed}/{arm}'] = diag
                del arrays
            candidate = saved_points['selective']
            for reference in ('native', 'flat', 'cleared'):
                other = saved_points['selective' if reference == 'cleared' else reference]
                for stage in ('final',) if reference == 'cleared' else STAGES[:-1]:
                    emit(f'{seed}/selective-v-{reference}/{stage}', paired(candidate[stage],
                        other['cleared_final' if reference == 'cleared' else stage], ids))
                for label, _ in FEES:
                    emit(f'{seed}/selective-v-{reference}/policy/{label}', paired(
                        candidate['policies']['retained'][label],
                        other['policies']['cleared' if reference == 'cleared' else 'retained'][label], ids))
        sink.write(']}\n')
    require(len(cells) == 8 * len(SEEDS), 'registered cell count differs')
    for cell in cells.values():
        cell['gates'] = gates(cell['arms']['selective'], cell['arms']['flat'])
        cell['passed'] = all(value for value in cell['gates'].values() if value is not None)
    checks = [value for cell in cells.values() for value in cell['gates'].values() if value is not None]
    worst = {}
    for metric, maximize in (('accuracy', False), ('brier', True), ('excess_brier', True),
                             ('confident_error_fraction', True)):
        key = (max if maximize else min)(cells, key=lambda k: cells[k]['arms']['selective']['stages']['final'][metric])
        worst[metric] = {'cell': key, 'value': cells[key]['arms']['selective']['stages']['final'][metric]}
    applicable = {key: cell['arms']['selective']['retention']['accuracy'] for key, cell in cells.items()
                  if cell['arms']['selective']['retention']['count']}
    key = min(applicable, key=applicable.get)
    worst['retention'] = {'cell': key, 'value': applicable[key]}
    key = min(cells, key=lambda k: cells[k]['arms']['selective']['policies']['retained']['cheap']['mean_net_reward'])
    worst['cheap_net_reward'] = {'cell': key,
        'value': cells[key]['arms']['selective']['policies']['retained']['cheap']['mean_net_reward']}
    summary = {'version': 'selective-memory-v1', 'decision': 'KEEP_SELECTIVE_MEMORY_V1' if all(checks)
               else 'REVISE_SELECTIVE_MEMORY_V1', 'passed_checks': sum(checks), 'total_checks': len(checks),
               'fully_passing_cells': sum(cell['passed'] for cell in cells.values()), 'cells': cells,
               'pooled': {arm: {key: pool(items) for key, items in values.items()} for arm, values in pooled.items()},
               'worst_selective_cells': worst, 'diagnostics': diagnostics, 'adverse_counts': adverse_counts,
               'denominator_note': '36,864 finite joint alternatives; five seeds repeat this bank. Each target is a word-specific forecast. Oracle MAP is fixed before hidden strata.',
               'id_schema': 'Append /word:w or /probe:p to original id; zero-based word and chronological probe indices.',
               'parameters': {'selective': 2188, 'native': 2244, 'flat': 2280}, 'state_scalars': 16,
               'data_sha256': data_sha, 'raw_sha256': digest(raw / 'manifest.json'),
               'fit_sha256': raw_manifest['fit_sha256'], 'scientific_admission': False}
    (output / 'summary.json').write_bytes(canonical(summary))
    manifest = {'version': 'selective-memory-v1', 'data_sha256': data_sha,
                'raw_sha256': summary['raw_sha256'], 'fit_sha256': summary['fit_sha256'],
                'scorer_sha256': digest(__file__), 'artifacts': {name: {'sha256': digest(output / name),
                'bytes': (output / name).stat().st_size} for name in ('summary.json', 'adverse.json.xz')}}
    (output / 'manifest.json').write_bytes(canonical(manifest))
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('prepared', 'raw', 'output'):
        parser.add_argument('--' + name, required=True, type=Path)
    args = parser.parse_args()
    result = score(args.prepared, args.raw, args.output)
    print(json.dumps({key: result[key] for key in ('decision', 'passed_checks', 'total_checks', 'fully_passing_cells')}))
