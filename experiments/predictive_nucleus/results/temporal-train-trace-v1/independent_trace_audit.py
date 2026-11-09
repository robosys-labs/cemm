"""Audit saved TRAIN forecasts with NumPy; no learner or evaluator imports.

The first-regression attribution starts AFTER the eight teaching receipts.
Initially wrong predictions are reported separately; the trace cannot locate
their earlier cause. All identification uses the original ordered TRAIN IDs.
"""
import argparse
from hashlib import sha256
import json
import lzma
import math
from pathlib import Path

import numpy as np


SEEDS = (7, 11, 23, 37, 53)
STAGES = ('teaching', 'claim', 'first', 'second')
TRANSITIONS = tuple(a + '->' + b for a, b in zip(STAGES, STAGES[1:]))
VERSION = 'temporal-native-train-trace-v1'


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    data = Path(path).read_bytes()
    return json.loads(lzma.decompress(data) if str(path).endswith('.xz') else data)


def fingerprint(state, arm):
    """Reconstruct the published parameter-byte identity without torch."""
    shapes = [('gru.weight_ih', (24, 18)), ('gru.weight_hh', (24, 8)),
              ('gru.bias_ih', (24,)), ('gru.bias_hh', (24,)),
              ('hidden.weight', (8, 49)), ('hidden.bias', (8,)),
              ('output.weight', (4 if arm == 'native' else 8, 8)),
              ('output.bias', (4 if arm == 'native' else 8,))]
    if set(state) != {name for name, _ in shapes}:
        raise ValueError('parameter inventory differs')
    result = sha256()
    for name, shape in shapes:
        value = np.asarray(state[name], dtype='<f8')
        if value.shape != shape or not np.isfinite(value).all():
            raise ValueError('invalid saved parameter: ' + name)
        result.update(json.dumps([name, list(shape)], separators=(',', ':')).encode())
        result.update(value.tobytes())
    return result.hexdigest()


def audit(selected, trace_dir, fitted, output):
    checks = 0

    def check(condition, label):
        nonlocal checks
        checks += 1
        if not condition:
            raise ValueError(label)

    source, manifest = read(selected), read(trace_dir / 'manifest.json')
    fit_manifest = read(fitted / 'manifest.json')
    rows = source['rows']
    ids = np.asarray([row['id'] for row in rows], dtype=object)
    check(len(ids) == len(set(ids)) == 2048, 'TRAIN ID inventory differs')
    check(source['version'] == manifest['version'] == VERSION, 'trace version differs')
    check('test' not in source, 'projection contains held-out records')
    check(digest(selected) == manifest['input_sha256'], 'TRAIN projection hash differs')
    check(sha256(encoded(rows)).hexdigest() == source['history_digest'], 'TRAIN history hash differs')
    check(source['data_sha256'] == manifest['data_sha256'] == fit_manifest['data_sha256'],
          'prepared-data bindings differ')
    check(digest(fitted / 'manifest.json') == manifest['fit_manifest_sha256'], 'fit manifest differs')
    check(source['source_sha256'] == fit_manifest['source_sha256'], 'frozen source inventories differ')
    check(manifest['trained_updates'] == 0 and manifest['checkpoint_count'] == 10
          and manifest['histories_per_checkpoint'] == 2048
          and manifest['forecasts_per_checkpoint'] == 16384, 'trace execution inventory differs')
    expected_files = {f'raw-{arm}-{seed}.json.xz' for seed in SEEDS for arm in ('native', 'flat')}
    check(set(manifest['artifacts']) == expected_files | {'summary.json.xz'}, 'raw artifact inventory differs')
    for name, record in manifest['artifacts'].items():
        path = trace_dir / name
        check(digest(path) == record['sha256'] and path.stat().st_size == record['bytes'],
              'raw artifact binding differs: ' + name)
    repo = Path(__file__).resolve().parents[4]
    for name, expected in manifest['diagnostic_source_sha256'].items():
        check(digest(repo / name) == expected, 'diagnostic source differs: ' + name)
    for name, expected in source['source_sha256'].items():
        check(digest(repo / 'experiments/predictive_nucleus' / name) == expected,
              'frozen learner source differs: ' + name)
    summary = read(trace_dir / 'summary.json.xz')
    for key in ('version', 'source_commit', 'diagnostic_source_sha256', 'input_sha256',
                'data_sha256', 'fit_manifest_sha256'):
        check(summary[key] == manifest[key], 'summary binding differs: ' + key)
    check(summary['artifacts'] == {name: manifest['artifacts'][name] for name in expected_files},
          'summary raw inventory differs')
    check(set(summary['models']) == {f'{arm}/{seed}' for seed in SEEDS for arm in ('native', 'flat')},
          'model inventory differs')
    groups = {'all': np.arange(len(rows))}
    group_names = np.asarray(['/'.join((row['law'], 'target-' + row['target']['scope'],
                                      'first-' + row['first']['query']['scope'])) for row in rows])
    groups.update({name: np.flatnonzero(group_names == name) for name in sorted(set(group_names))})
    labels = {field: np.asarray([row['answers'][field + '_y'] for row in rows], dtype=int)
              for field in ('target', 'protected')}
    results, pooled = {}, {}
    for seed in SEEDS:
        for arm in ('native', 'flat'):
            model_key, checkpoint_name = f'{arm}/{seed}', f'{arm}-{seed}.json'
            checkpoint = read(fitted / checkpoint_name)
            raw = read(trace_dir / f'raw-{arm}-{seed}.json.xz')
            check(raw['ids'] == ids.tolist() and raw['version'] == VERSION
                  and raw['arm'] == arm and raw['seed'] == seed, 'raw identity differs: ' + model_key)
            check(digest(fitted / checkpoint_name) == raw['checkpoint_sha256']
                  == fit_manifest['checkpoints'][checkpoint_name]['sha256'], 'checkpoint hash differs')
            check(checkpoint['arm'] == arm and checkpoint['seed'] == seed
                  and checkpoint['data_sha256'] == source['data_sha256'], 'checkpoint binding differs')
            check(sha256(encoded(checkpoint['state'])).hexdigest() == checkpoint['state_sha256'],
                  'checkpoint state JSON differs')
            check(fingerprint(checkpoint['state'], arm) == raw['weights_sha256']
                  == checkpoint['fit']['final_sha256'], 'checkpoint parameter bytes differ')
            check(set(raw['predictions']) == set(STAGES), 'forecast stage inventory differs')
            arrays, correctness, nll = {}, {}, {}
            for field in labels:
                arrays[field] = np.asarray([raw['predictions'][stage][field] for stage in STAGES])
                p = arrays[field]
                check(p.shape == (4, 2048, 8) and np.isfinite(p).all()
                      and (p >= 0).all() and (p <= 1 + 1e-10).all()
                      and np.max(np.abs(p.sum(axis=2) - 1)) <= 1e-10, 'invalid forecast probabilities')
                correctness[field] = p.argmax(axis=2) == labels[field][None, :]
                true_p = np.take_along_axis(p, labels[field][None, :, None], axis=2).squeeze(2)
                # Use scalar log for exact published strict-comparison semantics.
                nll[field] = np.asarray([[(-math.log(v) if v else math.inf) for v in stage]
                                         for stage in true_p])
            results[model_key] = {}
            check(set(summary['models'][model_key]) == set(groups), 'summary groups differ')
            for group, indices in groups.items():
                group_ids, group_result = ids[indices], {}
                pool = pooled.setdefault(arm, {}).setdefault(group, {})
                for field, y in labels.items():
                    p, correct, loss = arrays[field][:, indices], correctness[field][:, indices], nll[field][:, indices]
                    saved = summary['models'][model_key][group][field]
                    stages, transitions, first_regression, first_loss, first_loss_final = {}, {}, {}, {}, {}
                    seen = np.zeros(len(indices), dtype=bool)
                    initial_wrong = ~correct[0]
                    field_pool = pool.setdefault(field, {'stages': {}, 'transitions': {}, 'initially_wrong': 0,
                        'first_regression': {}, 'initially_correct_first_loss': {},
                        'initially_correct_first_loss_final_state': {}, 'initially_correct_never_wrong': 0})
                    for stage_index, stage in enumerate(STAGES):
                        brier = ((p[stage_index] - np.eye(8)[y[indices]]) ** 2).sum(axis=1)
                        metrics = {'count': len(indices), 'correct': int(correct[stage_index].sum()),
                            'accuracy': float(correct[stage_index].mean()), 'brier': float(brier.mean()),
                            'nll': float(loss[stage_index].mean()) if np.isfinite(loss[stage_index]).all() else 'Infinity'}
                        expected = saved['stages'][stage]
                        check(metrics['count'] == expected['count'] and metrics['correct'] == expected['correct'],
                              f'{model_key}/{group}/{field}/{stage}: count differs')
                        for metric in ('accuracy', 'brier', 'nll'):
                            check(metrics[metric] == expected[metric] if isinstance(metrics[metric], str) else
                                  isinstance(expected[metric], (float, int)) and
                                  math.isclose(metrics[metric], expected[metric], rel_tol=1e-12, abs_tol=1e-12),
                                  f'{model_key}/{group}/{field}/{stage}: {metric} differs')
                        stages[stage] = metrics
                        total = field_pool['stages'].setdefault(stage, {'count': 0, 'correct': 0, 'brier_sum': 0., 'nll_sum': 0.})
                        total['count'] += len(indices)
                        total['correct'] += metrics['correct']
                        total['brier_sum'] += float(brier.sum())
                        total['nll_sum'] += float(loss[stage_index].sum())
                    for index, transition in enumerate(TRANSITIONS):
                        regression = correct[index] & ~correct[index + 1]
                        repair = ~correct[index] & correct[index + 1]
                        worse = loss[index + 1] > loss[index]
                        masks = {'regressions': regression, 'repairs': repair, 'nll_worse': worse}
                        for name, mask in masks.items():
                            check(group_ids[mask].tolist() == saved['transitions'][transition][name],
                                  f'{model_key}/{group}/{field}/{transition}/{name}: IDs differ')
                        transitions[transition] = {name: int(mask.sum()) for name, mask in masks.items()}
                        first_regression[transition] = group_ids[regression & ~seen].tolist()
                        first_loss_mask = regression & ~seen & ~initial_wrong
                        first_loss[transition] = group_ids[first_loss_mask].tolist()
                        first_loss_final[transition] = {
                            'still_wrong_at_second_ids': group_ids[first_loss_mask & ~correct[-1]].tolist(),
                            'repaired_by_second_ids': group_ids[first_loss_mask & correct[-1]].tolist()}
                        check(sum(map(len, first_loss_final[transition].values())) == len(first_loss[transition]),
                              'first-loss final-state partition is not complete')
                        final_counts = field_pool['initially_correct_first_loss_final_state'].setdefault(
                            transition, {'still_wrong_at_second': 0, 'repaired_by_second': 0})
                        for name in final_counts:
                            final_counts[name] += len(first_loss_final[transition][name + '_ids'])
                        seen |= regression
                        totals = field_pool['transitions'].setdefault(transition, dict.fromkeys(masks, 0))
                        for name, mask in masks.items():
                            totals[name] += int(mask.sum())
                        for name, values in (('first_regression', first_regression), ('initially_correct_first_loss', first_loss)):
                            field_pool[name][transition] = field_pool[name].get(transition, 0) + len(values[transition])
                    never_wrong = int((~initial_wrong & ~seen).sum())
                    check(sum(map(len, first_loss.values())) + never_wrong + int(initial_wrong.sum()) == len(indices),
                          'baseline partition is not complete')
                    field_pool['initially_wrong'] += int(initial_wrong.sum())
                    field_pool['initially_correct_never_wrong'] += never_wrong
                    group_result[field] = {'stages': stages, 'transitions': transitions,
                        'initially_wrong_ids': group_ids[initial_wrong].tolist(),
                        'first_post_teaching_regression_ids': first_regression,
                        'initially_correct_first_loss_ids': first_loss,
                        'initially_correct_first_loss_final_state': first_loss_final,
                        'initially_correct_never_wrong': never_wrong,
                        'initially_wrong_then_regressed_ids': group_ids[initial_wrong & seen].tolist()}
                coupled = {}
                for index, transition in enumerate(TRANSITIONS):
                    target, protected = correctness['target'][:, indices], correctness['protected'][:, indices]
                    mask = ~target[index] & target[index + 1] & protected[index] & ~protected[index + 1]
                    coupled[transition] = group_ids[mask].tolist()
                    counts = pool.setdefault('target_repair_protected_damage', {})
                    counts[transition] = counts.get(transition, 0) + int(mask.sum())
                group_result['target_repair_protected_damage_ids'] = coupled
                results[model_key][group] = group_result
    for arm_groups in pooled.values():
        for group in arm_groups.values():
            for field in labels:
                for metrics in group[field]['stages'].values():
                    metrics['accuracy'] = metrics['correct'] / metrics['count']
                    metrics['brier'] = metrics.pop('brier_sum') / metrics['count']
                    total_nll = metrics.pop('nll_sum')
                    metrics['nll'] = total_nll / metrics['count'] if math.isfinite(total_nll) else 'Infinity'
    report = {'version': 'temporal-native-train-trace-audit-v1', 'status': 'PASS', 'checks': checks,
        'scope': 'Saved TRAIN arrays only; no model execution. Earliest regression is among post-teaching updates only.',
        'script_sha256': digest(__file__), 'input_sha256': digest(selected),
        'trace_manifest_sha256': digest(trace_dir / 'manifest.json'), 'models': results, 'pooled': pooled}
    with output.open('xb') as stream:
        stream.write(encoded(report))
    return {'status': report['status'], 'checks': checks, 'report_sha256': digest(output),
            'pooled_all': {arm: values['all'] for arm, values in pooled.items()}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'trace', 'fitted', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.input, args.trace, args.fitted, args.output), sort_keys=True))
