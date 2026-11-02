#!/usr/bin/env python3
"""Compare saved language forecasts after STOP; never import a model or scorer.

This is a same-team diagnostic, not a resumed scientific evaluation or a finding
of numerical root cause. It reads only source-freeze metadata, saved language
weights, raw/archived language forecasts and already-delivered language readings.
"""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
import lzma
import math
from pathlib import Path
import struct
import subprocess
import sys


BASE = '2ba2843b3a456957b9c4f0b789e42e90387354c8'
SEEDS = (7, 11, 23, 37, 53)
BANKS = ('bilingual', 'lexical', 'binding', 'saturation', 'centering', 'coordinate')


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def flatten(value):
    return [number for row in value for number in (flatten(row) if isinstance(row, list) else [row])]


def shape(value):
    return [len(value), *shape(value[0])] if isinstance(value, list) else []


def fingerprint(state):
    """Independently encode the archived float64 tensor fingerprint, no Torch."""
    result = sha256()
    for name, value in sorted(state.items()):
        numbers = flatten(value)
        metadata = json.dumps([name, 'torch.float64', shape(value)]).encode()
        raw = struct.pack('<' + str(len(numbers)) + 'd', *numbers)
        for part in (metadata, raw):
            result.update(len(part).to_bytes(8, 'big')); result.update(part)
    return result.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent,
                        help='experiments/predictive_nucleus directory; defaults to script directory')
    parser.add_argument('--output', type=Path, required=True, help='New exclusive diagnostic directory')
    args = parser.parse_args(); root = args.root.resolve()
    args.output.mkdir(parents=True, exist_ok=False)
    args.summary, args.records = args.output / 'summary.json', args.output / 'points.json.xz'
    artifacts = {}

    def read(path):
        raw = path.read_bytes(); artifacts[path.relative_to(root).as_posix()] = sha256(raw).hexdigest()
        return json.loads(lzma.decompress(raw) if path.suffix == '.xz' else raw)

    freeze = read(root / 'data/set-acquisition-v1/freeze.json')
    manifest = read(root / 'results/set-acquisition-v1/traces/manifest.json')
    failure = read(root / 'results/set-acquisition-v1/scored/failure.json')
    language_path = root / 'data/coordinate-fit-v1/checkpoints.json.xz'
    language = read(language_path)
    base_bytes = subprocess.check_output(['git', '-C', str(root.parents[1]), 'show',
        BASE + ':experiments/predictive_nucleus/data/coordinate-fit-v1/checkpoints.json.xz'])
    assert language_path.read_bytes() == base_bytes
    language_sha = artifacts[language_path.relative_to(root).as_posix()]
    assert language_sha == freeze['historical']['data/coordinate-fit-v1/checkpoints.json.xz']
    language_states = {}
    for seed in SEEDS:
        record = language['checkpoints'][f'coordinates/{seed}']
        language_states[str(seed)] = fingerprint(record['state'])
        assert language_states[str(seed)] == record['state_sha256']
    summaries, individual, nll_deltas = [], [], []
    by_bank, totals = defaultdict(Counter), Counter()
    maxima = {'order_logp': 0., 'world_logp': 0., 'world_probability': 0.}
    maximum_examples = {}

    for law in ('nand', 'nor'):
        for seed in SEEDS:
            for short in BANKS:
                bank = short + '_retention'; old_bank = 'fresh' if short == 'coordinate' else bank
                current_path = root / 'results/set-acquisition-v1/traces' / f'trace-{law}-{seed}-acquired-{bank}.json.xz'
                archive_path = root / 'results/coordinate-v1/traces' / f'trace-{law}-{seed}-coordinates-{old_bank}.json.xz'
                input_path = root / 'data' / f'{short}-v1' / f'{law}-inputs.json.xz'
                current, archive, inputs = (read(p) for p in (current_path, archive_path, input_path))
                assert artifacts[current_path.relative_to(root).as_posix()] == manifest['artifacts'][current_path.name]['sha256']
                for p in (archive_path, input_path):
                    assert artifacts[p.relative_to(root).as_posix()] == freeze['historical'][p.relative_to(root).as_posix()]
                assert current['language_sha256'] == language_states[str(seed)]
                assert current['input_sha256'] == archive['input_sha256'] == digest(inputs)
                cases = {r['id']: r for r in inputs['episodes']}
                expected = {(r['id'], t) for r in cases.values() for t in range(len(r['utterances']))}
                before = {(r['id'], r['step']): r for r in archive['points'] if r.get('view', 'canonical') == 'canonical'}
                now = {(r['id'], r['step']): r for r in current['points']}
                assert len(cases) == len(inputs['episodes']) and len(now) == len(current['points'])
                assert now.keys() == before.keys() == expected
                counts, cell_maxima = Counter(), {'order_logp': 0., 'world_logp': 0., 'world_probability': 0.}
                for key, point in now.items():
                    old = before[key]
                    assert all(type(v) in (float, int) and math.isfinite(v)
                               for row in (point, old) for field in ('order_logp', 'logp') for v in row[field])
                    order_changes = [[i, b, a] for i, (a, b) in enumerate(zip(point['order_logp'], old['order_logp'], strict=True)) if a != b]
                    differences = {'order_logp': max(abs(a-b) for a, b in zip(point['order_logp'], old['order_logp'], strict=True)),
                        'world_logp': max(abs(a-b) for a, b in zip(point['logp'], old['logp'], strict=True)),
                        'world_probability': max(abs(math.exp(a)-math.exp(b)) for a, b in zip(point['logp'], old['logp'], strict=True))}
                    identity = {'law': law, 'seed': seed, 'bank': bank, 'id': key[0], 'step': key[1]}
                    for metric, value in differences.items():
                        cell_maxima[metric] = max(cell_maxima[metric], value)
                        if value > maxima[metric]: maxima[metric] = value; maximum_examples[metric] = {**identity, 'difference': value}
                    reading = cases[key[0]]['utterances'][key[1]]['reading']
                    target = sum(bit << (len(reading)-i-1) for i, bit in enumerate(reading))
                    choose = lambda row: max(range(len(row['logp'])), key=row['logp'].__getitem__)
                    previous_map, current_map = choose(old), choose(point)
                    bc, ac = previous_map == target, current_map == target
                    delta = old['logp'][target] - point['logp'][target]; nll_deltas.append(delta)
                    world_unequal = point['logp'] != old['logp']
                    counts.update(planned=1, order_vectors_unequal=bool(order_changes), order_components_unequal=len(order_changes),
                        world_vectors_unequal=world_unequal, archived_correct=bc, current_correct=ac,
                        exact_regressions=bc and not ac, exact_repairs=ac and not bc,
                        nll_worse=delta > 0, nll_better=delta < 0, nll_equal=delta == 0)
                    if order_changes or world_unequal or bc != ac or delta != 0:
                        individual.append({**identity, 'order_component_changes_index_old_new': order_changes,
                            'maximum_abs_order_logp_difference': differences['order_logp'],
                            'maximum_abs_world_logp_difference': differences['world_logp'],
                            'maximum_abs_world_probability_difference': differences['world_probability'],
                            'archived_map': previous_map, 'current_map': current_map, 'observed_world': target,
                            'archived_correct': bc, 'current_correct': ac, 'exact_regression': bc and not ac,
                            'archived_nll': -old['logp'][target], 'current_nll': -point['logp'][target], 'nll_change': delta})
                totals.update(counts); by_bank[bank].update(counts)
                summaries.append({'law': law, 'seed': seed, 'bank': bank, **dict(counts), 'maximum_abs_difference': cell_maxima,
                    'current_trace': current_path.relative_to(root).as_posix(),
                    'archived_trace': archive_path.relative_to(root).as_posix(),
                    'observed_inputs': input_path.relative_to(root).as_posix()})

    metadata = {'status': 'POST_STOP_DIAGNOSTIC_ONLY', 'scientific_decision': None,
        'execution_status': 'SCORING_ABORTED', 'stopped_attempt_unchanged': True,
        'same_team_review': True, 'stdlib_only': True, 'model_executions': 0, 'original_scorer_executions': 0,
        'evaluator_files_opened': False, 'tolerance_changed': False, 'scientific_admission': False,
        'study_keep_claimed': False, 'script_sha256': sha256(Path(__file__).read_bytes()).hexdigest()}
    detail = {**metadata, 'version': 'set-retention-points-v1',
        'selection': 'Every record with any unequal order/world log vector, changed exact correctness, or nonzero NLL change.',
        'records': individual}
    raw = (json.dumps(detail, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()
    with args.records.open('xb') as stream: stream.write(lzma.compress(raw))
    report = {**metadata, 'version': 'set-retention-audit-v1', 'failure': failure,
        'artifact_sha256': artifacts, 'language_checkpoint': {'sha256': language_sha, 'byte_identical_to_commit': BASE,
            'state_sha256_reconstructed': language_states, 'all_current_trace_headers_match': True},
        'counts': dict(totals), 'maximum_abs_difference': maxima, 'maximum_examples': maximum_examples,
        'mean_nll_change': math.fsum(nll_deltas) / len(nll_deltas),
        'by_bank': {k: dict(v) for k, v in by_bank.items()}, 'by_law_seed_bank': summaries,
        'individual_records': {'file': args.records.name, 'records': len(individual),
            'sha256': sha256(args.records.read_bytes()).hexdigest(), 'bytes': args.records.stat().st_size},
        'interpretation': 'Frozen exact order equality was violated despite unchanged language weights. Differences are tiny. '
            'These file comparisons do not establish numerical root cause and do not resume scoring or grant KEEP. '
            'The frozen runner emitted failure.json only; no runner-produced scientific decision exists.',
        'limits': 'Language retention only. Exact-world diagnostics use already-delivered readings, not evaluator files. '
            'No new model forecasts, collection, original scorer execution, tolerance adjustment or scientific admission.'}
    assert 'torch' not in sys.modules
    with args.summary.open('x') as stream: json.dump(report, stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')
    print(json.dumps({'summary': str(args.summary), 'summary_sha256': sha256(args.summary.read_bytes()).hexdigest(),
        'individual_records': report['individual_records'], 'counts': dict(totals), 'maxima': maxima}))


if __name__ == '__main__': main()
