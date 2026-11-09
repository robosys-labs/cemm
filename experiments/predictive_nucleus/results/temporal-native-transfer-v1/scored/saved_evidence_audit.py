"""Read-only custody, exposure, and causal-prefix audit; imports no CEMM code."""
from collections import Counter
from hashlib import sha256
import argparse
import json
import lzma
from pathlib import Path
import random
import time

import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--root', type=Path, required=True, help='Predictive nucleus experiment root')
parser.add_argument('--output', type=Path, required=True, help='Audit report JSON path')
args = parser.parse_args()
ROOT = args.root.resolve()
OUT = args.output.resolve()
PREP = ROOT / 'data/temporal-native-transfer-v1'
FIT = ROOT / 'data/temporal-native-fit-v1'
RAW = ROOT / 'results/temporal-native-transfer-v1/raw'
START = time.perf_counter()
CHECKS = Counter()
ERRORS = []
MAX_PREFIX_ERROR = 0.0

def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()

def digest(value):
    return sha256(encoded(value)).hexdigest()

def read(path):
    data = path.read_bytes()
    return json.loads(lzma.decompress(data) if path.suffix == '.xz' else data)

def file_hash(path):
    return sha256(path.read_bytes()).hexdigest()

def check(name, condition, detail=None):
    CHECKS[name] += 1
    if not condition:
        ERRORS.append({'check': name, 'detail': detail})

prep, fitted, raw = [read(p / 'manifest.json') for p in (PREP, FIT, RAW)]
data_sha = file_hash(PREP / 'manifest.json')
for stage, folder, manifest in (('prepared', PREP, prep), ('fit', FIT, fitted), ('raw', RAW, raw)):
    check('source_inventory_equal', manifest['source_sha256'] == prep['source_sha256'], stage)
    check('protocol_binding', manifest['protocol_commit'] == '0bdb45172f85b755c7916907cefbcd30f21766ed', stage)
    for name, expected in manifest.get('artifacts', manifest.get('checkpoints', {})).items():
        check('artifact_hash', file_hash(folder / name) == expected['sha256'], stage + '/' + name)
        if 'bytes' in expected:
            check('artifact_size', (folder / name).stat().st_size == expected['bytes'], stage + '/' + name)
for name, expected in prep['source_sha256'].items():
    check('frozen_local_source_hash', file_hash(ROOT / name) == expected, name)
check('data_bindings', fitted['data_sha256'] == raw['data_sha256'] == data_sha)
public, answers = read(PREP / 'public.json.xz'), read(PREP / 'test-answers.json.xz')
rows = public['test']
ids = [row['id'] for row in rows]
check('inventory', len(public['train']) == 2048 and len(rows) == len(set(ids)) == len(answers) == 12288)
check('train_history_digest', digest(public['train']) == prep['history_digest'])

fit_hashes = {}
order = ('gru.weight_ih', 'gru.weight_hh', 'gru.bias_ih', 'gru.bias_hh',
         'hidden.weight', 'hidden.bias', 'output.weight', 'output.bias')
for seed in (7, 11, 23, 37, 53):
    rng, batches = random.Random(20261108200 + seed), sha256()
    for _ in range(256):
        batches.update((json.dumps([rng.randrange(2048) for _ in range(128)], separators=(',', ':')) + '\n').encode())
    for arm in ('native', 'flat'):
        name = f'{arm}-{seed}.json'
        saved = read(FIT / name)
        fit_hashes[(seed, arm)] = file_hash(FIT / name)
        check('checkpoint_manifest_report', saved['fit'] == fitted['checkpoints'][name]['fit'], name)
        check('checkpoint_state_json', digest(saved['state']) == saved['state_sha256'], name)
        h = sha256()
        parameters = 0
        for key in order:
            v = np.asarray(saved['state'][key], dtype='<f8')
            h.update(json.dumps([key, list(v.shape)], separators=(',', ':')).encode())
            h.update(v.tobytes())
            parameters += v.size
        check('actual_fitted_parameter_bytes', h.hexdigest() == saved['fit']['final_sha256'], name)
        expected = {'minibatch_sha256': batches.hexdigest(), 'updates': 256, 'batch_size': 128,
                    'sampled_episodes': 32768, 'forecast_terms': 196608,
                    'target_endpoint_forecasts_per_episode': 3,
                    'parameters': 1108 if arm == 'native' else 1144}
        for key, value in expected.items():
            check('matched_fixed_exposure', saved['fit'][key] == value, name + '/' + key)
        check('parameter_count', parameters == expected['parameters'], name)
        check('complete_finite_loss_trajectory', len(saved['fit']['losses']) == 256 and
              [v['update'] for v in saved['fit']['losses']] == list(range(1, 257)) and
              all(np.isfinite(v['mean_nll']) and len(v['forecast_nll']) == 6 and
                  all(np.isfinite(x) for x in v['forecast_nll'].values()) for v in saved['fit']['losses']), name)

def clean(query):
    return {key: value for key, value in query.items() if key not in ('entities', 'evidence_id')}

representatives = {view: {} for view in ('base', 'first', 'both')}
rep_indices = {view: [] for view in representatives}
answer_sets = {view: {} for view in ('base', 'first')}
provenance = read(RAW / 'provenance.json.xz')
check('provenance_inventory', [v['id'] for v in provenance] == ids)
for i, (row, p) in enumerate(zip(rows, provenance)):
    base, first, second_y = row['base'], {**row['first'], 'source': 'physical'}, answers[row['id']]
    second = {'query': row['second'], 'endpoint': second_y, 'source': 'physical'}
    expected = {'id': row['id'], 'base_ids': [r['query']['evidence_id'] for r in base],
                'first_id': first['query']['evidence_id'], 'second_id': row['second']['evidence_id'],
                'base_digest': digest(base), 'first_digest': digest([*base, first]),
                'both_digest': digest([*base, first, second]), 'second_only_digest': digest([*base, second])}
    check('exact_ordered_prefix_provenance', p == expected, row['id'])
    check('no_target_equivalent_question', row['first']['query']['before'][:2] != row['target']['before'][:2]
          and row['second']['before'][:2] != row['target']['before'][:2], row['id'])
    public_context = {'base': [{**r, 'query': clean(r['query'])} for r in base],
                      'first_query': clean(first['query']), 'second_query': clean(row['second']),
                      'target': clean(row['target']), 'protected': clean(row['protected'])}
    prefix = digest(public_context)
    for view, extra in (('base', ()), ('first', (first['endpoint'],)), ('both', (first['endpoint'], second_y))):
        key = (prefix, *extra)
        rep_indices[view].append(representatives[view].setdefault(key, i))
        if view != 'both':
            answer_sets[view].setdefault(key, set()).add(second_y)
rep_indices = {view: np.array(indices) for view, indices in rep_indices.items()}
second_y = np.array([answers[identity] for identity in ids])

def invariant(label, values, view):
    global MAX_PREFIX_ERROR
    values = np.asarray(values)
    if values.dtype == bool:
        check('same_prefix_same_preanswer', bool(np.array_equal(values, values[rep_indices[view]])), label)
    else:
        error = float(np.max(np.abs(values - values[rep_indices[view]])))
        MAX_PREFIX_ERROR = max(MAX_PREFIX_ERROR, error)
        check('same_prefix_same_preanswer', error <= 1e-12, {'label': label, 'max_error': error})

for seed in (7, 11, 23, 37, 53):
    for arm in ('native', 'flat', 'rule'):
        name = f'raw-{seed}-{arm}.json.xz'
        saved = read(RAW / name)
        check('complete_raw_bank', saved['ids'] == ids and saved['arm'] == arm and saved['seed'] == seed, name)
        check('raw_model_data_binding', saved['data_sha256'] == data_sha and saved['checkpoint_sha256'] ==
              ('SUPPLIED_RULE' if arm == 'rule' else fit_hashes[(seed, arm)]), name)
        for view, prefix in (('retained', 'first'), ('cleared', 'base')):
            v = {key: np.asarray(value) for key, value in saved['views'][view].items()}
            for key, values in v.items():
                check('complete_probability_array', values.shape == ((12288, 8, 8) if key == 'branches' else (12288, 8))
                      and bool(np.isfinite(values).all()) and bool((values >= 0).all()) and
                      float(np.max(np.abs(values.sum(-1) - 1))) <= 1e-10, name + '/' + view + '/' + key)
                if key in ('before', 'probe', 'branches'):
                    invariant(name + '/' + view + '/' + key, values, prefix)
            decisions = saved['decisions'][view]
            value = (v['probe'] * v['branches'].max(-1)).sum(-1) - v['before'].max(-1)
            check('preanswer_value_arithmetic', float(np.max(np.abs(value - decisions['value']))) <= 1e-12, name + '/' + view)
            asks = np.stack((value > .05 + 1e-12, value > 1 + 1e-12, np.zeros(len(ids), bool)), -1)
            check('preanswer_decision_arithmetic', bool(np.array_equal(asks, decisions['asks'])), name + '/' + view)
            for key in ('value', 'asks'):
                invariant(name + '/' + view + '/' + key, decisions[key], prefix)
            check('actual_answer_selects_saved_branch', float(np.max(np.abs(v['branches'][np.arange(len(ids)), second_y]
                                                                                - v['after_second']))) <= 1e-12, name + '/' + view)
        print(json.dumps({'audited_bank': name, 'failures': len(ERRORS)}), flush=True)

report = {'status': 'PASS' if not ERRORS else 'FAIL', 'failure_count': len(ERRORS), 'failures': ERRORS,
          'check_count': sum(CHECKS.values()), 'checks': dict(CHECKS),
          'audit_script_sha256': file_hash(Path(__file__)),
          'scope': 'Saved artifacts only: custody, exact matched exposure, native weight bytes, complete raw arrays, ordered evidence provenance, target-input exclusion, pre-answer causal-prefix invariance. No CEMM import, inference, fitting, collection, simulator, oracle or scorer execution.',
          'prepared_manifest_sha256': data_sha, 'fit_manifest_sha256': file_hash(FIT / 'manifest.json'),
          'raw_manifest_sha256': file_hash(RAW / 'manifest.json'), 'train_histories': 2048,
          'test_cases': 12288, 'checkpoints': 10, 'raw_banks': 15, 'raw_case_rows': 184320,
          'distinct_public_prefixes': {k: len(v) for k, v in representatives.items()},
          'prefixes_with_different_unseen_second_answers': {k: sum(len(v) > 1 for v in groups.values()) for k, groups in answer_sets.items()},
          'maximum_same_prefix_forecast_difference': MAX_PREFIX_ERROR,
          'publication_scope': 'Local source/artifact hashes verified. Remote stage order remains a separate publication-history check by the parent.',
          'wall_seconds': time.perf_counter() - START}
OUT.write_bytes(encoded(report))
print(json.dumps(report, sort_keys=True))
