"""Prospective observations and evaluator-only conditional laws for selective v1.

Only ``prepare`` imports physical truth implementations. ``tensorize`` accepts
delivered observations and previously frozen native projections, never oracle
rows. Contexts and targets are newly generated; the native basis is reused.
"""
from collections import Counter
from hashlib import sha256
from itertools import product
import json
import lzma
from pathlib import Path
import random


ROOT = Path(__file__).resolve().parent
VERSION = 'selective-memory-v1'
SEEDS = (7, 11, 23, 37, 53)
LAWS = ('nand', 'nor')
SCOPES = ('local', 'sibling')
CAUSES = ('report_only', 'one_event_exception', 'local_correction', 'parent_correction')


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(value):
    return sha256(encoded(value)).hexdigest()


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    # Stream through a buffered text wrapper: repeated counterfactual rows may
    # serialize far larger than their shared in-memory observation structures.
    opener = lzma.open if str(path).endswith('.xz') else open
    with opener(path, 'wt', encoding='utf-8') as stream:
        json.dump(value, stream, sort_keys=True, separators=(',', ':'), allow_nan=False)
        stream.write('\n')


def read(path):
    opener = lzma.open if str(path).endswith('.xz') else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        return json.load(stream)


def bits(value):
    return [(value >> shift) & 1 for shift in (2, 1, 0)]


def contexts():
    """Canonical public sampling; hidden new operations/causes are not inputs."""
    rng = random.Random(20261110101)
    choices = {split: [p for p in product(range(4), repeat=4)
                      if sum(p) % 4 in allowed]
               for split, allowed in (('train', (0, 1)), ('test', (2, 3)))}
    for split in ('train', 'test'):
        for index, (law, mode, old0, old1, scope0, scope1) in enumerate(product(
                LAWS, range(2), range(4), range(4), SCOPES, SCOPES)):
            a0, a1, b0, b1 = rng.choice(choices[split])
            yield {'split': split, 'law': law, 'mode': mode, 'old': [old0, old1],
                   'target_scope': [scope0, scope1], 'a': [a0, a1], 'b': [b0, b1],
                   'start': (old0 + old1 + mode + 2 * SCOPES.index(scope0)
                             + SCOPES.index(scope1)) % 2,
                   'ticket': digest([VERSION, split, index])[:24]}


def current_operation(old, alternative, scope):
    new, cause = alternative
    return new if cause == 'parent_correction' or (
        cause == 'local_correction' and scope == 'local') else old


def context_rows(context, table, include_oracle=True):
    """Build one finite joint population, permitting synthetic tables in tests.

    ``table`` is evaluator-owned [operation][three-bit input] and has already
    been checked against both physical implementations by ``prepare``.
    """
    old, scopes = context['old'], context['target_scope']
    a, b, start = context['a'], context['b'], context['start']
    if len(table) != 4 or any(len(row) != 8 for row in table):
        raise ValueError('expected a four-operation eight-input physical table')
    signatures = [tuple(row[2 * state] for state in range(4)) for row in table]
    if len(set(signatures)) != 4:
        raise ValueError('teaching does not observationally identify old operations')
    for row in table:
        if any(type(value) is not int or value not in range(8) for value in row):
            raise ValueError('invalid physical endpoint table')
    order = [start, 1 - start]
    sequence = order * 2 if context['split'] == 'train' else order + order[::-1]
    layouts = ('svo', 'osv') if context['split'] == 'train' else ('vos',)

    def query(state, word, scope, when, stage):
        layout = layouts[stage % len(layouts)]
        evidence_id = context['ticket'] + '/' + str(stage)
        return {'native_key': f"{context['law']}/{context['mode']}/{layout}/{state}/{word}",
                'before': bits(state), 'word': word, 'scope': scope, 'time': when,
                'layout': layout, 'evidence_id': evidence_id,
                'entities': ['E' + digest([evidence_id, slot])[:18] for slot in range(3)]}

    teaching = []
    for state in range(4):
        for word in order:
            teaching.append({'query': query(2 * state, word, 'parent', -1, len(teaching)),
                             'endpoint': table[old[word]][2 * state], 'source': 'physical'})
    claim_queries = [query(2 * a[word], word, 'local', 0, 8 + pos)
                     for pos, word in enumerate(order)]
    probes, count = [], [0, 0]
    for pos, word in enumerate(sequence):
        n = count[word]
        first_scope = 'local' if a[word] % 2 == 0 else 'sibling'
        scope = first_scope if n == 0 else ('sibling' if first_scope == 'local' else 'local')
        state = 2 * ((b[word] + n + 1) % 4) + n
        probes.append(query(state, word, scope, 1, 10 + pos))
        count[word] += 1
    targets = [query(2 * b[word] + 1, word, scopes[word], 2, 14 + word) for word in range(2)]
    if any(probe['before'][:2] == targets[probe['word']]['before'][:2] for probe in probes):
        raise ValueError('probe has its word\'s target active input')
    options = [[(new, cause) for new in range(4) if new != old[word] for cause in CAUSES]
               for word in range(2)]
    alternatives = list(product(*options))
    observations, target_values, metadata, public = [], [], [], []
    for index, world in enumerate(alternatives):
        claims = [table[world[word][0]][2 * a[word]] for word in order]
        answers = [table[current_operation(old[q['word']], world[q['word']], q['scope'])]
                   [sum(bit << shift for bit, shift in zip(q['before'], (2, 1, 0)))] for q in probes]
        current = [current_operation(old[word], world[word], scopes[word]) for word in range(2)]
        target_y = [table[current[word]][2 * b[word] + 1] for word in range(2)]
        identity = context['ticket'] + '/case/' + str(index)
        row = {'id': identity, 'base': teaching + [
            {'query': q, 'endpoint': y, 'source': 'claim'}
            for q, y in zip(claim_queries, claims)],
            'probes': [{'query': q, 'endpoint': y, 'source': 'physical'}
                       for q, y in zip(probes, answers)], 'targets': targets}
        if context['split'] == 'train':
            row['target_y'] = target_y
        public.append(row)
        observations.append(claims + answers)
        target_values.append(target_y)
        metadata.append({'id': identity, 'law': context['law'], 'mode': context['mode'],
                         'old': list(old), 'new': [item[0] for item in world],
                         'causes': [item[1] for item in world], 'target_scope': list(scopes),
                         'target_y': target_y, 'probe_y': answers,
                         'target_change_mask': sum((current[word] != old[word]) << word for word in range(2)),
                         'persistent_change_mask': sum((world[word][1] in CAUSES[2:]) << word
                                                       for word in range(2))})
    if Counter(row['persistent_change_mask'] for row in metadata) != {i: 36 for i in range(4)}:
        raise ValueError('joint persistent-change population is not counterbalanced')
    if include_oracle:
        _conditionals(metadata, observations, target_values, sequence)
    return public, metadata


def _conditionals(rows, observations, targets, sequence):
    """Condition a full 144-world joint prior only on delivered observations."""
    def distribution(indices, column):
        counts = Counter(column[i] for i in indices)
        return [counts[y] / len(indices) for y in range(8)]

    columns = list(zip(*observations))
    target_columns = list(zip(*targets))
    stages = {'teaching': (), 'claims': (0, 1), 'pair': (0, 1, 2, 3),
              'third': (0, 1, 2, 3, 4), 'final': tuple(range(6)),
              'cleared_final': (0, 1, 4, 5)}
    caches = {}

    def posterior(i, used):
        used = tuple(used)
        if used not in caches:
            groups = {}
            for j, row in enumerate(observations):
                groups.setdefault(tuple(row[c] for c in used), []).append(j)
            caches[used] = {key: (group, [distribution(group, column) for column in target_columns])
                            for key, group in groups.items()}
        return caches[used][tuple(observations[i][c] for c in used)]

    option_cache = {}

    def optional(i, used):
        indices, before = posterior(i, used)
        key = (tuple(used), tuple(indices))
        if key not in option_cache:
            qprob, branches = [], []
            for word in range(2):
                column = columns[4 + sequence[2:].index(word)]
                qprob.append(distribution(indices, column))
                branches.append([distribution([j for j in indices if column[j] == answer],
                                              target_columns[word])
                                 if qprob[word][answer] else None for answer in range(8)])
            option_cache[key] = (qprob, branches)
        qprob, branches = option_cache[key]
        answer = [observations[i][4 + sequence[2:].index(word)] for word in range(2)]
        return {'probe': qprob, 'before': before, 'branches': branches, 'answer': answer,
                'after': [branches[word][answer[word]] for word in range(2)]}

    for i, row in enumerate(rows):
        row['distributions'] = {name: posterior(i, used)[1] for name, used in stages.items()}
        row['next_probe'] = [distribution(posterior(i, range(2 + pos))[0], columns[2 + pos])
                             for pos in range(4)]
        row['optional'] = optional(i, stages['pair'])
        row['cleared_optional'] = optional(i, stages['claims'])
        if any(row['distributions']['final'][word][row['target_y'][word]] <= 0 for word in range(2)):
            raise ValueError('actual endpoint is outside observational posterior support')


def prepare(output, native_source=None, stamp=None):
    """Prepare once after the caller has published the implementation source."""
    from .temporal_observability_v1 import checked_endpoint
    output = Path(output)
    native_source = Path(native_source or ROOT / 'data/temporal-native-transfer-v1')
    old_manifest = read(native_source / 'manifest.json')
    basis = {}
    for seed in SEEDS:
        name = f'native-{seed}.json.xz'
        data = (native_source / name).read_bytes()
        if sha256(data).hexdigest() != old_manifest['artifacts'][name]['sha256']:
            raise ValueError('frozen native basis changed: ' + name)
        basis[name] = data
    tables = {(law, mode): [[checked_endpoint(law, mode, op, bits(state)) for state in range(8)]
                           for op in range(4)] for law in LAWS for mode in range(2)}
    output.mkdir(parents=True, exist_ok=False)
    train, test, oracle = [], [], []
    sample = random.Random(20261110102)
    for context in contexts():
        public, private = context_rows(context, tables[context['law'], context['mode']],
                                       include_oracle=context['split'] == 'test')
        if context['split'] == 'train':
            for mask in range(4):
                eligible = [i for i, row in enumerate(private) if row['persistent_change_mask'] == mask]
                train.extend(public[i] for i in sample.sample(eligible, 2))
        else:
            test.extend(public)
            oracle.extend(private)
    if (len(train), len(test), len(oracle)) != (2048, 36864, 36864):
        raise ValueError('frozen population inventory differs')
    if len({r['id'] for r in train + test}) != len(train) + len(test):
        raise ValueError('duplicate or overlapping split identities')
    for name, rows in (('train', train), ('test', test), ('oracle', oracle)):
        write(output / f'{name}.json.xz', {'version': VERSION, 'rows': rows})
    for name, data in basis.items():
        (output / name).write_bytes(data)
    artifacts = {p.name: {'sha256': file_hash(p), 'bytes': p.stat().st_size}
                 for p in sorted(output.iterdir())}
    manifest = {'version': VERSION, **(stamp or {}), 'artifacts': artifacts,
                'contexts_per_split': 256, 'worlds_per_context': 144,
                'train_pool': 36864, 'train_cases': len(train), 'test_cases': len(test),
                'native_source_manifest_sha256': file_hash(native_source / 'manifest.json'),
                'train_order_sha256': digest([r['id'] for r in train]),
                'test_order_sha256': digest([r['id'] for r in test])}
    write(output / 'manifest.json', manifest)
    return manifest


def unique(records, seen=None):
    """Ignore an exact replay; fail if an evidence identity changes payload."""
    seen = {} if seen is None else seen
    result = []
    for row in records:
        identity = row['query']['evidence_id']
        if identity in seen:
            if seen[identity] != row:
                raise ValueError('conflicting evidence identity')
        else:
            seen[identity] = row
            result.append(row)
    return result


def tensorize(rows, native):
    """Pack only public observations; cache repeated query/receipt encodings.

    Equivalent vectorization to the frozen 41/18 feature contract avoids one
    PyTorch invocation per receipt in the full joint population.
    """
    import numpy as np
    import torch
    if not rows or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('nonempty unique episode inventory required')
    basis = {key: np.asarray(value['likelihood'], dtype=np.float64) for key, value in native.items()}
    if any(v.shape != (4, 8) or not np.isfinite(v).all() or (v < 0).any()
           or not np.allclose(v.sum(-1), 1, atol=1e-10, rtol=0) for v in basis.values()):
        raise ValueError('invalid frozen native probability rows')
    qcache, rcache = {}, {}

    def query(item):
        key = (item['native_key'], tuple(item['before']), item['scope'], item['time'], item['word'])
        if key not in qcache:
            if (len(item['before']) != 3 or any(type(x) is not int or x not in (0, 1) for x in item['before'])
                    or item['scope'] not in ('parent', 'local', 'sibling')
                    or type(item['word']) is not int or item['word'] not in (0, 1)
                    or type(item['time']) is not int or item['time'] not in (-1, 0, 1, 2)):
                raise ValueError('invalid public query metadata')
            qcache[key] = np.concatenate((basis[item['native_key']].reshape(32), item['before'],
                         [int(item['scope'] == s) for s in ('parent', 'local', 'sibling')],
                         [item['time']], [int(item['word'] == w) for w in range(2)]))
        return key, qcache[key]

    def endpoint(value):
        if type(value) is not int or value not in range(8):
            raise ValueError('endpoint must be a non-boolean integer in [0,7]')
        return value

    def receipt(item):
        key, q = query(item['query'])
        y, source = endpoint(item['endpoint']), item['source']
        if source not in ('claim', 'physical'):
            raise ValueError('invalid receipt source')
        key = (key, y, source)
        if key not in rcache:
            rcache[key] = np.concatenate((q[:32].reshape(4, 8)[:, y], bits(y), q[32:39],
                                         (1, 0) if source == 'physical' else (0, 1), q[39:41]))
        return rcache[key]

    n, training = len(rows), 'target_y' in rows[0]
    packed = {'base': np.empty((n, 10, 18)), 'probe_q': np.empty((n, 4, 41)),
              'probe_y': np.empty((n, 4), dtype=np.int64), 'target_q': np.empty((n, 2, 41))}
    if training:
        packed['target_y'] = np.empty((n, 2), dtype=np.int64)
    for i, row in enumerate(rows):
        if ('target_y' in row) != training:
            raise ValueError('TRAIN labels must be uniformly present or absent')
        seen = {}
        base, probes = unique(row['base'], seen), unique(row['probes'], seen)
        if (len(base), len(probes), len(row['targets'])) != (10, 4, 2):
            raise ValueError('observed history inventory differs')
        if ([r['source'] for r in base] != ['physical'] * 8 + ['claim'] * 2
                or any(r['source'] != 'physical' for r in probes)):
            raise ValueError('teaching/claim/probe source schedule differs')
        packed['base'][i] = [receipt(r) for r in base]
        packed['probe_q'][i] = [query(r['query'])[1] for r in probes]
        packed['probe_y'][i] = [endpoint(r['endpoint']) for r in probes]
        packed['target_q'][i] = [query(q)[1] for q in row['targets']]
        if [q['word'] for q in row['targets']] != [0, 1]:
            raise ValueError('targets must be ordered by public word identity')
        if training:
            if len(row['target_y']) != 2:
                raise ValueError('expected one observed training target per word')
            packed['target_y'][i] = [endpoint(y) for y in row['target_y']]
    return {key: torch.from_numpy(value) for key, value in packed.items()}
