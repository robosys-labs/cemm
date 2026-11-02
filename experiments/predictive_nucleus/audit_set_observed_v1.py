"""POST-STOP saved-record diagnostic of observed SET outcomes only.

No CEMM import, model execution, oracle file, original scorer, or gate decision.
Inputs are full observed before/action/after records and already saved forecasts.
Reexecution is an arithmetic audit of saved records, never a research retry.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import lzma
import math
from pathlib import Path

SEEDS = (7, 11, 23, 37, 53)
ARMS = ('parent', 'acquired', 'no_change')


def check(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def encode(value):
    if isinstance(value, dict): return {k: encode(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)): return [encode(v) for v in value]
    if type(value) is float and not math.isfinite(value):
        check(not math.isnan(value), 'undefined diagnostic arithmetic')
        return 'positive_infinity' if value > 0 else 'negative_infinity'
    return value


def stats(rows, arm):
    values = [r['arms'][arm]['nll'] for r in rows]
    return {'planned': len(rows), 'correct': sum(r['arms'][arm]['correct'] for r in rows),
            'mean_nll': math.fsum(values) / len(values), 'min_nll': min(values), 'max_nll': max(values),
            'finite_nll_count': sum(math.isfinite(v) for v in values)}


def compare(rows, arm):
    result = Counter()
    for row in rows:
        old, new = row['arms'][arm], row['arms']['acquired']
        result['repairs'] += not old['correct'] and new['correct']
        result['regressions'] += old['correct'] and not new['correct']
        result['nll_worse'] += new['nll'] > old['nll']
        result['nll_better'] += new['nll'] < old['nll']
        result['nll_equal'] += new['nll'] == old['nll']
    return dict(result)


def summarize(rows):
    return {'planned': len(rows), 'changed_sets': sum(r['changed'] for r in rows),
            'unchanged_sets': sum(not r['changed'] for r in rows),
            'arms': {arm: stats(rows, arm) for arm in ARMS},
            'changed': {arm: stats([r for r in rows if r['changed']], arm) for arm in ARMS},
            'unchanged': {arm: stats([r for r in rows if not r['changed']], arm) for arm in ARMS},
            'acquired_vs_parent': compare(rows, 'parent'),
            'acquired_vs_no_change': compare(rows, 'no_change')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent,
                        help='Predictive nucleus directory containing the frozen saved records.')
    parser.add_argument('--output', type=Path, required=True, help='New directory for this arithmetic audit.')
    args = parser.parse_args()
    ROOT = args.root.resolve()
    DATA = ROOT / 'data/set-acquisition-v1'
    TRACES = ROOT / 'results/set-acquisition-v1/traces'
    SOURCES = {}
    output_dir = args.output.resolve()
    output_dir.mkdir(parents=True, exist_ok=False)

    def read(path, expected=None):
        raw = path.read_bytes(); digest = sha256(raw).hexdigest()
        if expected is not None: check(digest == expected, 'file binding differs: ' + str(path))
        SOURCES[str(path.relative_to(ROOT))] = digest
        return json.loads(lzma.decompress(raw) if path.suffix == '.xz' else raw)


    freeze = read(DATA / 'freeze.json')
    manifest = read(TRACES / 'manifest.json')
    failure = read(ROOT / 'results/set-acquisition-v1/scored/failure.json')
    check(failure['stage'] == 'score' and failure['retry_permitted'] is False, 'stopped attempt not retained')
    check(manifest['complete'] is True and manifest['freeze_sha256'] == SOURCES['data/set-acquisition-v1/freeze.json'],
          'collection source binding differs')
    points = []; summaries = {}
    for law in ('nand', 'nor'):
        filename = law + '-inputs.json.xz'
        inputs = read(DATA / filename, freeze['artifacts'][filename]['sha256'])
        cases = {e['episode']: e for e in inputs['episodes']}
        check(len(cases) == len(inputs['episodes']), 'duplicate episode ID')
        expected = {(e['episode'], t) for e in cases.values() for t in range(len(e['actions']))}
        sets = {(e['episode'], t) for e in cases.values() for t, a in enumerate(e['actions']) if a['kind'] == 'set'}
        for seed in SEEDS:
            forecasts = {}
            for arm in ARMS:
                filename = f'trace-{law}-{seed}-{arm}-fresh.json.xz'
                trace = read(TRACES / filename, manifest['artifacts'][filename]['sha256'])
                check((trace['law'], trace['seed'], trace['arm'], trace['bank']) == (law, seed, arm, 'fresh') and
                      trace['input_sha256'] == digest(inputs) and all(trace[k] == manifest[k] for k in
                      ('weights_publication', 'freeze_sha256', 'training_sha256')), 'trace identity differs')
                lookup = {(p['id'], p['step']): p for p in trace['points']}
                check(len(lookup) == len(trace['points']) and set(lookup) == expected, 'trace point inventory differs')
                forecasts[arm] = lookup
            start = len(points)
            for episode, step in sorted(sets):
                e = cases[episode]; action = e['actions'][step]; ids = sorted(e['ids'])
                before, after = e['observations'][step:step + 2]; target = action['participants'][0]
                check(all(type(row[i]) is int and row[i] in (0, 1) for row in (before, after) for i in ids),
                      'incomplete observed target')
                truth = sum(after[i] << (len(ids) - j - 1) for j, i in enumerate(ids))
                record = {'law': law, 'seed': seed, 'id': episode, 'step': step, 'entities': len(ids),
                    'target': target, 'prior': before[target], 'requested': action['value'],
                    'observed_after': after[target], 'changed': before[target] != after[target],
                    'truth_world': truth, 'observed_spectator_changes': [i for i in ids if i != target and before[i] != after[i]],
                    'arms': {}}
                for arm in ARMS:
                    values = forecasts[arm][episode, step]['logp']
                    logs = [-math.inf if v == 'negative_infinity' else v for v in values]
                    check(len(logs) == 2 ** len(ids) and all(type(v) in (int, float) and
                          not math.isnan(v) and v != math.inf for v in logs), 'invalid saved forecast')
                    check(abs(math.fsum(math.exp(v) for v in logs) - 1.) <= 1e-10, 'unnormalized saved forecast')
                    best = max(range(len(logs)), key=logs.__getitem__)
                    record['arms'][arm] = {'map_world': best, 'correct': best == truth, 'nll': -logs[truth]}
                record['comparisons'] = {arm: {'repair': not record['arms'][arm]['correct'] and record['arms']['acquired']['correct'],
                    'regression': record['arms'][arm]['correct'] and not record['arms']['acquired']['correct'],
                    'nll_worse': record['arms']['acquired']['nll'] > record['arms'][arm]['nll'],
                    'nll_change': record['arms']['acquired']['nll'] - record['arms'][arm]['nll']}
                    for arm in ('parent', 'no_change')}
                points.append(record)
            summaries[f'{law}/{seed}'] = summarize(points[start:])
    archive = output_dir / 'points.json.xz'
    payload = {'status': 'POST_STOP_SAVED_RECORD_DIAGNOSTIC_ONLY', 'points': encode(points)}
    raw = lzma.compress((json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode())
    with archive.open('xb') as stream: stream.write(raw)
    report = {'status': 'POST_STOP_SAVED_RECORD_DIAGNOSTIC_ONLY', 'created_utc': datetime.now(timezone.utc).isoformat(),
        'execution': 'POST_STOP_SAVED_RECORD_ARITHMETIC_AUDIT',
        'scope': 'Observed native SET action endpoints only; all contacts, language retention, and other acceptance gates excluded.',
        'scientific_decision': None, 'stopped_attempt_unchanged': True, 'original_scorer_executed': False,
        'models_executed': False, 'oracle_or_evaluator_files_read': False,
        'limitations': 'Post-stop diagnostic of already collected dependent views. Complete observed feedback supplies targets; '
                       'this is not independent custody, a repaired scorer, a completed acceptance run, or a KEEP decision.',
        'failure': {'stage': failure['stage'], 'error': failure['error'], 'message': failure['message']},
        'summary': summarize(points), 'per_law_seed': summaries,
        'points': {'path': archive.name, 'sha256': sha256(raw).hexdigest(), 'bytes': len(raw), 'records': len(points),
                   'contents': 'Every SET point ID, observed target, all three MAP/NLL results, exact repairs/regressions and probability changes.'},
        'source_sha256': SOURCES, 'diagnostic_script_sha256': sha256(Path(__file__).read_bytes()).hexdigest()}
    output = output_dir / 'summary.json'
    with output.open('x') as stream: json.dump(encode(report), stream, indent=2, sort_keys=True, allow_nan=False); stream.write('\n')
    print(json.dumps({'status': report['status'], 'execution': report['execution'],
                      'summary': str(output), 'points': str(archive), 'records': len(points)}, sort_keys=True))


if __name__ == '__main__':
    main()
