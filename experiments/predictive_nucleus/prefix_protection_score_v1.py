"""Compare saved prefix-protection TRAIN forecasts; never execute a model."""
import argparse
from hashlib import sha256
import json
import lzma
import math
from pathlib import Path

import numpy as np


SEEDS = (7, 11, 23, 37, 53)
LAWS = ('nand', 'nor')
STAGES = ('teaching', 'claim', 'first', 'second')
FIELDS = ('target', 'protected')
INPUT_SHA256 = '660bb412f2d165295c30d2248daa2ae7a334c56d4fa95fe324f80aa356b7063f'
BASELINE_RAW_SHA256 = '027a9ecdc1676902cd64f5c8d355572a71f6f5ea31e76dd1636efd831984fe2c'
BASELINE_FIT_SHA256 = 'bd626b837f739a91971d296a448ee99cd1dcfcb841d7e78d275fc9945fa00ea3'
VERSION = 'prefix-protection-train-v1'
BASELINE_VERSION = 'temporal-native-train-trace-v1'
GATES = ('final_target_accuracy', 'final_target_brier', 'final_protected_accuracy',
         'final_protected_brier_gain', 'prefix_protected_brier_gain',
         'teaching_protected_accuracy', 'teaching_protected_brier')


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    data = Path(path).read_bytes()
    return json.loads(lzma.decompress(data) if str(path).endswith('.xz') else data)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_manifest(directory, version, input_hash):
    manifest = read(directory / 'manifest.json')
    require(manifest['version'] == version and manifest['input_sha256'] == input_hash,
            'raw version or TRAIN input binding differs')
    for name, length in (('source_commit', 40), ('fit_manifest_sha256', 64)):
        value = manifest[name]
        require(isinstance(value, str) and len(value) == length
                and all(c in '0123456789abcdef' for c in value), 'invalid ' + name)
    raw_names = {f'raw-{arm}-{seed}.json.xz' for arm in ('native', 'flat') for seed in SEEDS}
    require({name for name in manifest['artifacts'] if name.startswith('raw-')} == raw_names,
            'raw bank inventory differs')
    for name, record in manifest['artifacts'].items():
        require(Path(name).name == name, 'artifact must be a file in its bank directory')
        path = directory / name
        require(digest(path) == record['sha256'] and path.stat().st_size == record['bytes'],
                'artifact hash or size differs: ' + name)
    return manifest


def parameter_fingerprint(state, arm):
    """Reconstruct the frozen torch parameter-byte format without importing it."""
    shapes = [('gru.weight_ih', (24, 18)), ('gru.weight_hh', (24, 8)),
              ('gru.bias_ih', (24,)), ('gru.bias_hh', (24,)),
              ('hidden.weight', (8, 49)), ('hidden.bias', (8,)),
              ('output.weight', (4 if arm == 'native' else 8, 8)),
              ('output.bias', (4 if arm == 'native' else 8,))]
    require(set(state) == {name for name, _ in shapes}, 'parameter inventory differs')
    result = sha256()
    for name, shape in shapes:
        value = np.asarray(state[name], dtype='<f8')
        require(value.shape == shape and np.isfinite(value).all(), 'invalid saved parameter: ' + name)
        result.update(json.dumps([name, list(shape)], separators=(',', ':')).encode())
        result.update(value.tobytes())
    return result.hexdigest()


def candidate_bindings(fitted, raw_manifest, source):
    require(digest(fitted / 'manifest.json') == raw_manifest['fit_manifest_sha256'], 'candidate fit manifest hash differs')
    manifest = read(fitted / 'manifest.json')
    require(manifest['version'] == VERSION and manifest['input_sha256'] == INPUT_SHA256
            and manifest['baseline_fit_manifest_sha256'] == BASELINE_FIT_SHA256, 'candidate fit binding differs')
    names = set(source['source_sha256']) | {'PREFIX_PROTECTION_TRAIN_PROTOCOL_V1.md',
        'prefix_protection_train_v1.py', 'tests/test_prefix_protection_train_v1.py',
        Path(__file__).name, 'tests/test_prefix_protection_score_v1.py', 'temporal_train_trace_v1.py'}
    hashes = manifest['source_sha256']
    require(set(hashes) == names and hashes == raw_manifest['source_sha256'], 'candidate source inventories differ')
    for name in names:
        require(digest(Path(__file__).parent / name) == hashes[name], 'candidate source changed: ' + name)
        if name in source['source_sha256']:
            require(hashes[name] == source['source_sha256'][name], 'frozen model source changed')
    require(set(manifest['checkpoints']) == {f'{arm}-{seed}.json' for arm in ('native', 'flat') for seed in SEEDS},
            'candidate checkpoint inventory differs')
    bindings = {}
    for seed in SEEDS:
        for arm in ('native', 'flat'):
            name = f'{arm}-{seed}.json'
            path, expected = fitted / name, manifest['checkpoints'][name]
            require(digest(path) == expected['sha256'] and path.stat().st_size == expected['bytes'],
                    'candidate checkpoint artifact differs: ' + name)
            saved = read(path)
            require(saved['version'] == VERSION and saved['input_sha256'] == INPUT_SHA256
                    and saved['data_sha256'] == source['data_sha256'] and saved['arm'] == arm
                    and type(saved['seed']) is int and saved['seed'] == seed
                    and saved['source_sha256'] == hashes and saved['source_commit'] == manifest['source_commit'],
                    'candidate checkpoint identity differs: ' + name)
            require(sha256(encoded(saved['state'])).hexdigest() == saved['state_sha256'], 'candidate state JSON differs')
            fingerprint = parameter_fingerprint(saved['state'], arm)
            require(fingerprint == saved['fit']['final_sha256'], 'candidate parameter-byte fingerprint differs')
            bindings[f'raw-{arm}-{seed}.json.xz'] = {'checkpoint_sha256': expected['sha256'], 'weights_sha256': fingerprint}
    return bindings


def point_scores(probabilities, labels):
    require(len(probabilities) == len(labels), 'forecast count differs')
    correct, brier, nll = [], [], []
    for p, y in zip(probabilities, labels):
        require(len(p) == 8 and all(type(v) in (int, float) and math.isfinite(v)
                and 0 <= v <= 1 + 1e-10 for v in p)
                and abs(math.fsum(p) - 1) <= 1e-10, 'invalid eight-endpoint distribution')
        require(type(y) is int and 0 <= y < 8, 'invalid observed TRAIN endpoint')
        correct.append(max(range(8), key=p.__getitem__) == y)
        brier.append(math.fsum((v - int(j == y)) ** 2 for j, v in enumerate(p)))
        nll.append(-math.log(p[y]) if p[y] else math.inf)
    return {'correct': correct, 'brier': brier, 'nll': nll}


def load_raw(path, version, arm, seed, ids, labels, input_hash, expected_checkpoint=None):
    raw = read(path)
    require(raw['version'] == version and raw['arm'] == arm and type(raw['seed']) is int
            and raw['seed'] == seed and raw['ids'] == ids, 'raw identity or ordered case IDs differ')
    if version == VERSION:
        require(raw.get('input_sha256') == input_hash, 'candidate raw TRAIN input binding differs')
        require(expected_checkpoint is not None and all(raw.get(k) == v for k, v in expected_checkpoint.items()),
                'candidate raw checkpoint or weight identity differs')
    elif 'input_sha256' in raw:
        require(raw['input_sha256'] == input_hash, 'raw TRAIN input binding differs')
    require(set(raw['predictions']) == set(STAGES), 'raw stage inventory differs')
    result = {}
    for stage in STAGES:
        require(set(raw['predictions'][stage]) == set(FIELDS), 'raw field inventory differs')
        result[stage] = {field: point_scores(raw['predictions'][stage][field], labels[field]) for field in FIELDS}
    return result


def statistics(points, indices):
    losses = [points['nll'][i] for i in indices]
    correct = sum(points['correct'][i] for i in indices)
    return {'count': len(indices), 'correct': correct, 'accuracy': correct / len(indices),
            'brier': math.fsum(points['brier'][i] for i in indices) / len(indices),
            'nll': math.fsum(losses) / len(indices) if all(math.isfinite(v) for v in losses) else 'Infinity'}


def change(before, after):
    old_inf, new_inf = before['nll'] == 'Infinity', after['nll'] == 'Infinity'
    nll = (None if old_inf and new_inf else 'Infinity' if new_inf else '-Infinity' if old_inf
           else after['nll'] - before['nll'])
    return {'accuracy': after['accuracy'] - before['accuracy'], 'brier': after['brier'] - before['brier'],
            'nll': nll, 'nll_difference_defined': not (old_inf and new_inf)}


def compare_points(before, after, ids, indices):
    baseline, candidate = statistics(before, indices), statistics(after, indices)
    return {'baseline': baseline, 'candidate': candidate, 'change': change(baseline, candidate),
            'regressions': [ids[i] for i in indices if before['correct'][i] and not after['correct'][i]],
            'repairs': [ids[i] for i in indices if after['correct'][i] and not before['correct'][i]],
            'brier_worse': [ids[i] for i in indices if after['brier'][i] > before['brier'][i]],
            'nll_worse': [ids[i] for i in indices if after['nll'][i] > before['nll'][i]]}


def cell_gates(cell):
    target, protected, teaching = cell['target']['second'], cell['protected']['second'], cell['protected']['teaching']
    prefix = {arm: math.fsum(cell['protected'][stage][arm]['brier'] for stage in STAGES[1:]) / 3
              for arm in ('baseline', 'candidate')}
    gates = {
        'final_target_accuracy': target['candidate']['correct'] >= target['baseline']['correct'],
        'final_target_brier': target['candidate']['brier'] <= target['baseline']['brier'] + 1e-12,
        'final_protected_accuracy': protected['candidate']['correct'] >= protected['baseline']['correct'],
        'final_protected_brier_gain': protected['baseline']['brier'] - protected['candidate']['brier'] > 1e-4,
        'prefix_protected_brier_gain': prefix['baseline'] - prefix['candidate'] > 1e-4,
        'teaching_protected_accuracy': teaching['candidate']['correct'] >= teaching['baseline']['correct'],
        'teaching_protected_brier': teaching['candidate']['brier'] <= teaching['baseline']['brier'] + 1e-12}
    return {'gates': gates, 'prefix_protected_brier': prefix,
            'final_target': {arm: target[arm] for arm in ('baseline', 'candidate')},
            'final_protected': {arm: protected[arm] for arm in ('baseline', 'candidate')},
            'teaching_protected': {arm: teaching[arm] for arm in ('baseline', 'candidate')}}


def decide(cells):
    require(set(cells) == {f'{law}/{seed}' for law in LAWS for seed in SEEDS}, 'expected all ten native law/seed cells')
    require(all(set(cell['gates']) == set(GATES) and all(type(v) is bool for v in cell['gates'].values())
                for cell in cells.values()), 'expected seven boolean gates per cell')
    passed = sum(sum(cell['gates'].values()) for cell in cells.values())
    return {'decision': 'KEEP_PREFIX_OBJECTIVE_FOR_FRESH_STUDY' if passed == 70 else 'REVISE_PREFIX_OBJECTIVE',
            'passed_checks': passed, 'total_checks': 70, 'cells': cells}


def aggregate(comparisons):
    pooled = {}
    for arm in ('native', 'flat'):
        pooled[arm] = {}
        for field in FIELDS:
            pooled[arm][field] = {}
            for stage in STAGES:
                records = [comparisons[f'{arm}/{seed}']['all'][field][stage] for seed in SEEDS]
                values = {}
                for version in ('baseline', 'candidate'):
                    n = sum(r[version]['count'] for r in records)
                    correct = sum(r[version]['correct'] for r in records)
                    values[version] = {'count': n, 'correct': correct, 'accuracy': correct / n,
                        'brier': math.fsum(r[version]['brier'] * r[version]['count'] for r in records) / n,
                        'nll': 'Infinity' if any(r[version]['nll'] == 'Infinity' for r in records) else
                            math.fsum(r[version]['nll'] * r[version]['count'] for r in records) / n}
                values['change'] = change(values['baseline'], values['candidate'])
                values['adverse_counts'] = {name: sum(len(r[name]) for r in records)
                    for name in ('regressions', 'repairs', 'brier_worse', 'nll_worse')}
                pooled[arm][field][stage] = values
    return pooled


def score(selected, baseline_dir, candidate_dir, fitted, output):
    require(not output.exists(), 'output directory already exists')
    input_hash = digest(selected)
    require(input_hash == INPUT_SHA256, 'published TRAIN projection hash differs')
    source = read(selected)
    require(source['version'] == BASELINE_VERSION and 'test' not in source, 'expected TRAIN-only projection')
    rows = source['rows']
    ids = [row['id'] for row in rows]
    require(len(rows) == len(set(ids)) == 2048, 'expected all 2,048 unique TRAIN IDs')
    require(sha256(encoded(rows)).hexdigest() == source['history_digest'], 'TRAIN history digest differs')
    require({row['law'] for row in rows} == set(LAWS), 'TRAIN law inventory differs')
    labels = {field: [row['answers'][field + '_y'] for row in rows] for field in FIELDS}
    require(digest(baseline_dir / 'manifest.json') == BASELINE_RAW_SHA256, 'published original trace manifest differs')
    manifests = {name: load_manifest(directory, version, input_hash) for name, directory, version in
                 (('baseline', baseline_dir, BASELINE_VERSION), ('candidate', candidate_dir, VERSION))}
    require(manifests['baseline']['fit_manifest_sha256'] == BASELINE_FIT_SHA256, 'original fit manifest binding differs')
    bindings = candidate_bindings(fitted, manifests['candidate'], source)
    groups = {'all': list(range(len(rows))), **{law: [i for i, row in enumerate(rows) if row['law'] == law] for law in LAWS}}
    comparisons, cells = {}, {}
    for seed in SEEDS:
        for arm in ('native', 'flat'):
            name = f'raw-{arm}-{seed}.json.xz'
            old = load_raw(baseline_dir / name, BASELINE_VERSION, arm, seed, ids, labels, input_hash)
            new = load_raw(candidate_dir / name, VERSION, arm, seed, ids, labels, input_hash, bindings[name])
            comparisons[f'{arm}/{seed}'] = {}
            for group, indices in groups.items():
                cell = {field: {stage: compare_points(old[stage][field], new[stage][field], ids, indices)
                                for stage in STAGES} for field in FIELDS}
                comparisons[f'{arm}/{seed}'][group] = cell
                if arm == 'native' and group != 'all':
                    cells[f'{group}/{seed}'] = cell_gates(cell)
    provenance = {'version': VERSION, 'input_sha256': input_hash, 'scorer_sha256': digest(__file__),
        'protocol_sha256': digest(Path(__file__).with_name('PREFIX_PROTECTION_TRAIN_PROTOCOL_V1.md')),
        'baseline_manifest_sha256': digest(baseline_dir / 'manifest.json'),
        'candidate_manifest_sha256': digest(candidate_dir / 'manifest.json'),
        'source_commits': {name: manifest['source_commit'] for name, manifest in manifests.items()},
        'fit_manifest_sha256': {name: manifest['fit_manifest_sha256'] for name, manifest in manifests.items()},
        'scope': 'Observed TRAIN development comparison only; no held-out result or G5 admission.'}
    decision = {**provenance, **decide(cells), 'pooled': aggregate(comparisons)}
    report = {**decision, 'comparisons': comparisons}
    output.mkdir(parents=True)
    (output / 'score.json.xz').write_bytes(lzma.compress(encoded(report)))
    (output / 'decision.json').write_bytes(encoded(decision))
    (output / 'manifest.json').write_bytes(encoded({**provenance, 'decision': decision['decision'],
        'artifacts': {name: {'sha256': digest(output / name), 'bytes': (output / name).stat().st_size}
                      for name in ('score.json.xz', 'decision.json')}}))
    return {key: decision[key] for key in ('decision', 'passed_checks', 'total_checks', 'pooled')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('input', 'baseline', 'candidate', 'fitted', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(score(args.input, args.baseline, args.candidate, args.fitted, args.output), sort_keys=True))
