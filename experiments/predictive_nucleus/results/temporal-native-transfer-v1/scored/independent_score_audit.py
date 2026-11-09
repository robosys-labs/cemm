"""Independent NumPy arithmetic on published records; never imports CEMM code."""
import argparse
from hashlib import sha256
import json
import lzma
from pathlib import Path
import random
import time
import numpy as np

TOL = 1e-12
CHECKS, DISCREPANCIES = 0, []
def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
def read(path):
    data = Path(path).read_bytes()
    return json.loads(lzma.decompress(data) if str(path).endswith('.xz') else data), sha256(data).hexdigest()
def check(path, actual, expected):
    global CHECKS
    CHECKS += 1
    equal = abs(float(actual) - float(expected)) <= TOL if type(actual) in (int, float) and type(expected) in (int, float) else actual == expected
    if not equal:
        DISCREPANCIES.append({'path': path, 'actual': actual, 'expected': expected})
def average(values):
    return float(np.mean(values, dtype=np.longdouble))
def distribution_check(path, values):
    check(path, bool(np.isfinite(values).all() and (values >= 0).all() and (values <= 1 + 1e-10).all()
                     and np.max(np.abs(values.sum(-1) - 1)) <= 1e-10), True)
def metrics(p, y, q):
    correct = p.argmax(1) == y
    brier = np.square(p - np.eye(8)[y]).sum(1)
    confident = p.max(1) >= .95
    actual = p[np.arange(len(y)), y]
    result = {'count': len(y), 'correct': int(correct.sum()), 'accuracy': average(correct), 'brier': average(brier),
              'excess_brier': average(np.square(p - q).sum(1)), 'conditional_accuracy_optimum': average(q.max(1)),
              'oracle_expected_brier': average(1 - np.square(q).sum(1)), 'confident_count': int(confident.sum()),
              'confident_error_fraction': average(confident & ~correct), 'confident_coverage': average(confident),
              'nll': 'Infinity' if (actual == 0).any() else average(-np.log(actual))}
    return result, correct
def policy(view, y, second_y, fee):
    before, probe, branches = (view[k] for k in ('before', 'probe', 'branches'))
    values = (probe * branches.max(2)).sum(1) - before.max(1)
    ask = values > fee + TOL if fee is not None else np.zeros(len(y), bool)
    chosen = np.where(ask[:, None], branches[np.arange(len(y)), second_y], before)
    correct, baseline = chosen.argmax(1) == y, before.argmax(1) == y
    net = correct.astype(float) - (fee or 0) * ask
    return {'count': len(y), 'correct': int(correct.sum()), 'accuracy': average(correct),
            'paid_questions': int(ask.sum()), 'mean_net_reward': average(net),
            'net_reward': float(np.sum(net, dtype=np.longdouble)), 'no_query_correct': int(baseline.sum())}, correct
def compare_metrics(path, actual, expected):
    for key, value in actual.items():
        check(path + '/' + key, value, expected[key])
def fit_audit(fitted, data_sha):
    manifest, _ = read(fitted / 'manifest.json')
    check('fit/data_sha256', manifest['data_sha256'], data_sha)
    order = ('gru.weight_ih', 'gru.weight_hh', 'gru.bias_ih', 'gru.bias_hh', 'hidden.weight', 'hidden.bias', 'output.weight', 'output.bias')
    hashes = {}
    for seed in (7, 11, 23, 37, 53):
        rng, batches = random.Random(20261108200 + seed), sha256()
        for _ in range(256):
            batches.update((json.dumps([rng.randrange(2048) for _ in range(128)], separators=(',', ':')) + '\n').encode())
        for arm in ('native', 'flat'):
            name = f'{arm}-{seed}.json'; item, digest = read(fitted / name); hashes[f'{seed}/{arm}'] = digest
            check('fit/file/' + name, digest, manifest['checkpoints'][name]['sha256'])
            check('fit/state/' + name, sha256(encoded(item['state'])).hexdigest(), item['state_sha256'])
            fingerprint = sha256()
            for key in order:
                value = np.asarray(item['state'][key], dtype='<f8')
                fingerprint.update(json.dumps([key, list(value.shape)], separators=(',', ':')).encode()); fingerprint.update(value.tobytes())
            check('fit/actual_weights/' + name, fingerprint.hexdigest(), item['fit']['final_sha256'])
            for key, expected in {'minibatch_sha256': batches.hexdigest(), 'updates': 256, 'batch_size': 128,
                                  'sampled_episodes': 32768, 'forecast_terms': 196608,
                                  'parameters': 1108 if arm == 'native' else 1144}.items():
                check('fit/' + name + '/' + key, item['fit'][key], expected)
    return hashes
def main(args):
    started = time.perf_counter()
    prepared, data_sha = read(args.prepared / 'manifest.json'); raw_manifest, raw_sha = read(args.raw / 'manifest.json')
    oracle, oracle_sha = read(args.prepared / 'oracle.json.xz'); scored, score_sha = read(args.score)
    check('raw/data_sha256', raw_manifest['data_sha256'], data_sha); check('score/data_sha256', scored['data_sha256'], data_sha)
    check('oracle/hash', oracle_sha, prepared['artifacts']['oracle.json.xz']['sha256']); check('score/raw_manifest', scored['raw_manifest_sha256'], raw_sha)
    rows = oracle['rows']; ids = np.array([r['id'] for r in rows]); y = np.array([r['target_y'] for r in rows]); second_y = np.array([r['second_y'] for r in rows])
    protected_y = np.array([r['protected_y'] for r in rows]); laws = np.array([r['law'] for r in rows])
    q = {view: np.array([r['distributions'][view] for r in rows]) for view in ('base', 'first', 'second', 'both')}
    check('oracle/inventory', (len(rows), len(set(ids))), (12288, 12288))
    fitted_hashes = fit_audit(args.fitted, data_sha); cells = {}; all_gates = []
    for seed in (7, 11, 23, 37, 53):
        current = {law: {} for law in ('nand', 'nor')}
        for arm in ('native', 'flat', 'rule'):
            name = f'raw-{seed}-{arm}.json.xz'; saved, digest = read(args.raw / name)
            check(name + '/hash', digest, raw_manifest['artifacts'][name]['sha256']); check(name + '/score_hash', digest, scored['raw_sha256'][name])
            check(name + '/identity', [saved['seed'], saved['arm'], saved['data_sha256'], saved['ids']], [seed, arm, data_sha, ids.tolist()])
            check(name + '/checkpoint', saved['checkpoint_sha256'], 'SUPPLIED_RULE' if arm == 'rule' else fitted_hashes[f'{seed}/{arm}'])
            predictions = {k: np.asarray(v) for k, v in saved['predictions'].items()}
            views = {label: {k: np.asarray(v) for k, v in view.items()} for label, view in saved['views'].items()}
            for label, view in views.items():
                for key, values in view.items(): distribution_check(name + '/' + label + '/' + key, values)
                value = (view['probe'] * view['branches'].max(2)).sum(1) - view['before'].max(1)
                check(name + '/' + label + '/decision_value_error', float(np.max(np.abs(value - saved['decisions'][label]['value']))), 0.)
                asks = np.stack((value > .05 + TOL, value > 1 + TOL, np.zeros(len(y), bool)), 1)
                check(name + '/' + label + '/asks', bool(np.array_equal(asks, saved['decisions'][label]['asks'])), True)
                check(name + '/' + label + '/actual_branch_error', float(np.max(np.abs(view['branches'][np.arange(len(y)), second_y] - view['after_second']))), 0.)
            for law in ('nand', 'nor'):
                indices = np.flatnonzero(laws == law); cellkey = f'{law}/{seed}'; reference = scored['cells'][cellkey]['arms'][arm]; summary, correct = {}, {}
                fields = (('both', predictions['after_second'], y, q['both']), ('protected', predictions['protected'], protected_y, np.eye(8)[protected_y]),
                          ('cleared_both', views['cleared']['after_second'], y, q['second']))
                for label, p, target, conditional in fields:
                    distribution_check(name + '/' + label, p)
                    summary[label], correct[label] = metrics(p[indices], target[indices], conditional[indices])
                    compare_metrics(cellkey + '/' + arm + '/' + label, summary[label], reference[label])
                summary['policies'], correct['policies'] = {}, {}
                for label, view in views.items():
                    result, correct['policies'][label] = policy({k: v[indices] for k, v in view.items()}, y[indices], second_y[indices], .05)
                    summary['policies'][label] = result; compare_metrics(cellkey + '/' + arm + '/cheap/' + label, result, reference['policies'][label]['cheap'])
                current[law][arm] = (summary, correct)
            del saved, predictions, views
        for law, arms in current.items():
            key = f'{law}/{seed}'; original = scored['cells'][key]; n, nc = arms['native']; f, fc = arms['flat']; b, c = n['both'], n['cleared_both']
            gates = {'attainable_accuracy': b['accuracy'] + .02 >= b['conditional_accuracy_optimum'] - TOL,
                     'excess_brier': b['excess_brier'] <= .02, 'protected_retention': n['protected']['accuracy'] >= .95,
                     'confident_errors': b['confident_error_fraction'] <= .01, 'flat_brier': b['brier'] <= f['both']['brier'] + TOL,
                     'retained_brier_gain': c['brier'] - b['brier'] > 1e-4,
                     'flat_cheap_net': n['policies']['retained']['mean_net_reward'] >= f['policies']['retained']['mean_net_reward'] - TOL,
                     'retained_cheap_net': n['policies']['retained']['mean_net_reward'] >= n['policies']['cleared']['mean_net_reward'] - TOL}
            check(key + '/gates', gates, original['gates']); all_gates.extend(gates.values()); selected_ids = ids[laws == law]
            for baseline in ('flat', 'rule', 'cleared'):
                rc = arms[baseline][1] if baseline != 'cleared' else nc
                for stage in ('both', 'cheap'):
                    candidate = nc['both'] if stage == 'both' else nc['policies']['retained']
                    other = rc['cleared_both' if baseline == 'cleared' else 'both'] if stage == 'both' else rc['policies']['cleared' if baseline == 'cleared' else 'retained']
                    target = original['paired'][baseline]['both'] if stage == 'both' else original['paired'][baseline]['policies']['cheap']
                    for label, mask in (('exact_regressions', other & ~candidate), ('exact_repairs', candidate & ~other)):
                        check(key + '/paired/' + baseline + '/' + stage + '/' + label, selected_ids[mask].tolist(), target[label])
            cells[key] = {'gates': gates, 'native': n, 'flat': f}
    decision = 'KEEP_NATIVE_TEMPORAL_UPDATER' if all(all_gates) else 'REVISE_NATIVE_TEMPORAL_UPDATER'
    check('decision', decision, scored['decision'])
    report = {'status': 'PASS' if not DISCREPANCIES else 'FAIL', 'decision': decision, 'checks': CHECKS,
              'discrepancies': DISCREPANCIES, 'cells': cells, 'raw_files': 15, 'gate_checks': len(all_gates),
              'score_sha256': score_sha, 'data_sha256': data_sha, 'raw_manifest_sha256': raw_sha,
              'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest(), 'wall_seconds': time.perf_counter() - started,
              'scope': 'Independent NumPy saved-record arithmetic and weight/exposure receipt audit; no model executed.'}
    args.output.write_bytes(encoded(report)); print(json.dumps({k: report[k] for k in ('status', 'decision', 'checks', 'raw_files', 'gate_checks', 'wall_seconds')}))
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('prepared', 'raw', 'fitted', 'score', 'output'): parser.add_argument('--' + name, type=Path, required=True)
    main(parser.parse_args())
