"""One frozen native/flat temporal-update study; preparation and scoring are separate.

Only prepare imports the physical simulator/oracle. Fit and collect consume
published observations and frozen native projections, never private meanings.
"""
import argparse
from collections import Counter
from hashlib import sha256
from itertools import product
import json
import lzma
from pathlib import Path
import random
import resource
import subprocess
import time

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
VERSION = 'temporal-native-transfer-v1'
SEEDS = (7, 11, 23, 37, 53)
PROTOCOL = 'TEMPORAL_NATIVE_TRANSFER_PROTOCOL_V1.md'
PROTOCOL_COMMIT = '0bdb45172f85b755c7916907cefbcd30f21766ed'
SOURCES = (PROTOCOL, 'temporal_native_transfer_v1.py', 'temporal_native_models_v1.py',
           'temporal_native_score_v1.py', 'coordinate_transport_v1.py',
           'temporal_observability_v1.py', 'effect_role_model.py',
           'effect_role_lexical.py', 'domain_kernel.py', 'bilingual_data.py',
           'effect_role_data.py', 'set_acquisition_data.py', 'multisource_law_oracle.py',
           'tests/test_temporal_native_models_v1.py', 'tests/test_temporal_native_score_v1.py',
           'tests/test_temporal_native_transfer_v1.py')


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False) + '\n').encode()


def digest(value):
    return sha256(encoded(value)).hexdigest()


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    data = encoded(value)
    if str(path).endswith('.xz'):
        data = lzma.compress(data)
    Path(path).write_bytes(data)


def read(path):
    data = Path(path).read_bytes()
    return json.loads(lzma.decompress(data) if str(path).endswith('.xz') else data)


def bits(value):
    return [(value >> shift) & 1 for shift in (2, 1, 0)]


def source():
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
    subprocess.run(['git', 'merge-base', '--is-ancestor', PROTOCOL_COMMIT, commit], cwd=REPO, check=True)
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=REPO):
        raise ValueError('commit tracked source before execution')
    hashes = {name: file_hash(ROOT / name) for name in SOURCES}
    for name in SOURCES:
        saved = subprocess.check_output(['git', 'show', commit + ':experiments/predictive_nucleus/' + name], cwd=REPO)
        if sha256(saved).hexdigest() != hashes[name]:
            raise ValueError('source is not committed: ' + name)
    return {'source_commit': commit, 'source_sha256': hashes, 'protocol_commit': PROTOCOL_COMMIT}


def receipt(start, extra):
    return {'wall_seconds': time.perf_counter() - start[0],
            'cpu_seconds': time.process_time() - start[1],
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, **extra}


def descriptor(law, mode, layout, state, word, scope, event_time, event_id):
    return {'native_key': f'{law}/{mode}/{layout}/{state}/{word}', 'before': bits(state),
            'word': word, 'scope': scope, 'time': event_time, 'evidence_id': event_id,
            'entities': ['E' + digest([event_id, slot])[:18] for slot in range(3)], 'layout': layout}


def prepare(output):
    """Generate actual observations and separate private evaluation records once."""
    from . import temporal_observability_v1 as physical
    from .coordinate_transport_v1 import restore, project
    start, stamp = (time.perf_counter(), time.process_time()), source()
    output.mkdir(parents=True, exist_ok=False)
    public = {'version': VERSION, 'train': [], 'test': []}
    answers, oracle_rows = {}, []
    # Public context and question schedule are fixed before new/cause assignment.
    for number, (law, mode, old, original, scope, target) in enumerate(product(
            physical.LAWS, range(2), range(4), range(8), ('local', 'sibling'), range(8))):
        a, b = original >> 1, target >> 1
        split = 'train' if (a + b) % 4 in (0, 1) else 'test'
        ticket = digest([VERSION, split, number])[:24]
        layouts = ('svo', 'osv') if split == 'train' else ('vos',)
        table = [[physical.checked_endpoint(law, mode, op, bits(s)) for s in range(8)] for op in range(4)]
        def desc(state, word, event_scope, when, stage):
            return descriptor(law, mode, layouts[stage % len(layouts)], state, word,
                              event_scope, when, ticket + '/' + str(stage))
        base = [{'query': desc(2*s, word, 'parent', -1, 4*word+s),
                 'endpoint': table[old][2*s], 'source': 'physical'} for word, s in product(range(2), range(4))]
        first_scope = 'local' if a % 2 == 0 else 'sibling'
        second_scope = 'sibling' if first_scope == 'local' else 'local'
        s1, s2 = 2*((b+1) % 4), 2*((b+2) % 4)+1
        q1, q2 = desc(s1, 0, first_scope, 1, 9), desc(s2, 0, second_scope, 1, 10)
        tq, pq = desc(target, 0, scope, 2, 11), desc(target, 1, scope, 2, 12)
        assert q1['before'][:2] != tq['before'][:2] != q2['before'][:2]
        worlds = [(new, cause) for new in range(4) if new != old for cause in physical.CAUSES]
        def outcome(world, state, where, protected=False):
            new, cause = world
            op = new if not protected and (cause == 'parent_correction' or
                                           (where == 'local' and cause == 'local_correction')) else old
            return table[op][state]
        for index, world in enumerate(worlds):
            new, cause = world
            claim = table[new][original]
            first_y, second_y, target_y = outcome(world, s1, first_scope), outcome(world, s2, second_scope), outcome(world, target, scope)
            row = {'id': ticket + '/case/' + str(index), 'law': law,
                   'base': base + [{'query': desc(original, 0, 'local', 0, 8), 'endpoint': claim, 'source': 'claim'}],
                   'first': {'query': q1, 'endpoint': first_y}, 'second': q2,
                   'target': tq, 'protected': pq}
            if split == 'train':
                row['answers'] = {'second_y': second_y, 'target_y': target_y, 'protected_y': table[old][target]}
            public[split].append(row)
            if split == 'test':
                answers[row['id']] = second_y
                distributions = {}
                for name, use_first, use_second in (('base', False, False), ('first', True, False),
                                                     ('second', False, True), ('both', True, True)):
                    support = [w for w in worlds if table[w[0]][original] == claim
                               and (not use_first or outcome(w, s1, first_scope) == first_y)
                               and (not use_second or outcome(w, s2, second_scope) == second_y)]
                    counts = Counter(outcome(w, target, scope) for w in support)
                    distributions[name] = [counts[y]/len(support) for y in range(8)]
                oracle_rows.append({'id': row['id'], 'law': law, 'mode': mode, 'old': old,
                    'new': new, 'cause': cause, 'target_scope': scope, 'target_state': target,
                    'first_y': first_y, 'second_y': second_y, 'target_y': target_y,
                    'protected_y': table[old][target], 'distributions': distributions})
    assert len(public['train']) == len(public['test']) == 12288
    public['train'] = random.Random(20261108101).sample(public['train'], 2048)
    write(output/'public.json.xz', public)
    write(output/'test-answers.json.xz', answers)
    write(output/'oracle.json.xz', {'version': VERSION, 'rows': oracle_rows})
    native_receipts = {}
    for seed in SEEDS:
        native, cell_receipts = {}, []
        for law in physical.LAWS:
            net, world, registry, metadata = restore(seed, law)
            words = [next(token for token, item in registry['tokens'].items() if item['id'] == identity)
                     for identity in net.new_ids]
            records, keys = [], []
            for mode, layout, state, word in product(range(2), ('svo', 'osv', 'vos'), range(8), range(2)):
                key = f'{law}/{mode}/{layout}/{state}/{word}'
                handles = ['P' + digest([VERSION, seed, key, slot])[:18] for slot in range(3)]
                current, context = [0, 0, 0], []
                actions = [(0, 0, 1, -1)] + [(1, slot, -1, bit) for slot, bit in enumerate(bits(state))]
                for action in actions:
                    after = physical.simulator._step(current, action, mode, law)
                    expected, probability = physical.oracle._distribution(current, action, (mode,), law)
                    assert expected == [sum(v << (2-i) for i, v in enumerate(after))] and probability == [1.]
                    context.append({'action': list(action), 'reading': list(after)})
                    current = after
                text = {'svo': [handles[0], words[word], handles[1]],
                        'osv': [handles[1], handles[0], words[word]],
                        'vos': [words[word], handles[1], handles[0]]}[layout]
                identity = digest([VERSION, seed, key])[:24]
                records.append({'id': identity, 'entities': handles, 'anchor': [0, 0, 0],
                                'context': context, 'text': ' '.join(text)})
                keys.append(key)
            rows, checks = project(net, world, registry, records, 'intact')
            renamed = []
            for record in records:
                names = {name: 'R' + digest([record['id'], i])[:18] for i, name in enumerate(record['entities'])}
                renamed.append({**record, 'id': digest(['renamed', record['id']])[:24],
                    'entities': list(names.values()), 'text': ' '.join(names.get(token, token) for token in record['text'].split())})
            repeated, _ = project(net, world, registry, renamed, 'intact')
            assert all(rows[a['id']]['likelihood'] == repeated[b['id']]['likelihood']
                       for a, b in zip(records, renamed, strict=True)), 'participant names changed native projections'
            checks['participant_rename_exact'] = len(records)
            for key, record in zip(keys, records, strict=True):
                native[key] = {'likelihood': rows[record['id']]['likelihood'],
                               'observed_prefix': record, 'frame': rows[record['id']]['frame']}
            cell_receipts.append({'metadata': metadata, 'checks': checks})
        write(output/f'native-{seed}.json.xz', native)
        native_receipts[str(seed)] = cell_receipts
        print(json.dumps({'stage': 'prepared_native', 'seed': seed}), flush=True)
    artifacts = {p.name: {'sha256': file_hash(p), 'bytes': p.stat().st_size} for p in sorted(output.iterdir())}
    manifest = {'version': VERSION, **stamp, 'artifacts': artifacts, 'train_cases': 2048,
                'train_pool': 12288, 'test_cases': 12288, 'native': native_receipts,
                'history_digest': digest(public['train']),
                'rule_contract': 'Four-way physical likelihoods; ignore claims; fresh exact-scope post-report prior; old parent fallback; separate protected word.'}
    write(output/'manifest.json', manifest)
    write(output/'execution.json', receipt(start, {'stage': 'prepare', 'manifest_sha256': file_hash(output/'manifest.json')}))
    return {'stage': 'prepare', 'train': 2048, 'test': 12288, 'data_sha256': file_hash(output/'manifest.json')}


def load(prepared, name):
    manifest = read(prepared/'manifest.json')
    if file_hash(prepared/name) != manifest['artifacts'][name]['sha256']:
        raise ValueError('prepared artifact changed: ' + name)
    return read(prepared/name)


def frozen_sources(prepared, stamp):
    if read(prepared/'manifest.json')['source_sha256'] != stamp['source_sha256']:
        raise ValueError('executable sources changed after data preparation')


def unique(records):
    """Delivery order is authoritative; exact replays do not update twice."""
    seen, result = {}, []
    for record in records:
        identity = record['query']['evidence_id']
        if identity in seen:
            if seen[identity] != record:
                raise ValueError('conflicting evidence identity')
        else:
            seen[identity] = record
            result.append(record)
    return result


def tensors(rows, native, answers=None):
    import torch
    from .temporal_native_models_v1 import receipt as observed
    def query(item):
        values = sum(native[item['native_key']]['likelihood'], [])
        return values + item['before'] + [int(item['scope'] == scope) for scope in ('parent', 'local', 'sibling')] + [item['time']] + [int(item['word'] == word) for word in range(2)]
    packed = {name: [] for name in ('base', 'first_q', 'first_y', 'second_q', 'second_y', 'target_q', 'protected_q')}
    training = 'answers' in rows[0]
    if training:
        packed.update(target_y=[], protected_y=[])
    for row in rows:
        base = unique(row['base'])
        if len(base) != 9:
            raise ValueError('registered unique teaching/report inventory differs')
        packed['base'].append([observed(query(r['query']), r['endpoint'], source=r['source']).tolist() for r in base])
        for key, value in (('first_q', query(row['first']['query'])), ('first_y', row['first']['endpoint']),
                           ('second_q', query(row['second'])), ('target_q', query(row['target'])),
                           ('protected_q', query(row['protected']))):
            packed[key].append(value)
        packed['second_y'].append(row['answers']['second_y'] if training else answers[row['id']])
        if training:
            for key in ('target_y', 'protected_y'):
                packed[key].append(row['answers'][key])
    return {key: torch.tensor(value, dtype=torch.long if key.endswith('_y') else torch.float64)
            for key, value in packed.items()}


def train(prepared, output):
    import torch
    from . import temporal_native_models_v1 as learned
    stamp, start = source(), (time.perf_counter(), time.process_time())
    frozen_sources(prepared, stamp)
    torch.set_num_threads(1)
    output.mkdir(parents=True, exist_ok=False)
    rows = load(prepared, 'public.json.xz')['train']
    data_sha = file_hash(prepared/'manifest.json')
    summaries = {}
    for seed in SEEDS:
        data = tensors(rows, load(prepared, f'native-{seed}.json.xz'))
        for arm in ('native', 'flat'):
            model = learned.Model(arm, seed)
            report = learned.fit(model, data, seed)
            state = {key: value.tolist() for key, value in model.state_dict().items()}
            item = {'version': VERSION, **stamp, 'arm': arm, 'seed': seed, 'data_sha256': data_sha,
                    'state': state, 'state_sha256': digest(state), 'fit': report}
            name = f'{arm}-{seed}.json'
            write(output/name, item)
            summaries[name] = {'sha256': file_hash(output/name), 'fit': report}
            print(json.dumps({'stage': 'fit', 'arm': arm, 'seed': seed, 'fit': report}), flush=True)
    write(output/'manifest.json', {'version': VERSION, **stamp, 'data_sha256': data_sha, 'checkpoints': summaries})
    write(output/'execution.json', receipt(start, {'stage': 'fit'}))
    return {'stage': 'fit', 'checkpoints': len(summaries)}


def rule(data):
    """Supplied scoped consistency control, never a learned cause inference."""
    import torch
    n = len(data['base'])
    parent = torch.full((n, 2, 4), .25, dtype=torch.float64)
    def update(prior, likelihood, hypothetical=False):
        weights = prior * likelihood
        mass = weights.sum(-1, keepdim=True)
        if not hypothetical and bool((mass == 0).any()):
            raise ValueError('actual physical evidence has zero rule support')
        # Impossible simulated answers have zero probability; keep their branch defined.
        return torch.where(mass > 0, weights / mass.clamp_min(1e-300), prior)
    for i in range(8):
        word = i//4
        parent[:, word] = update(parent[:, word], data['base'][:, i, :4])
    def likelihood(query):
        return query[:, :32].reshape(n, 4, 8)
    def mixture(p, query):
        return torch.einsum('nh,nhy->ny', p, likelihood(query))
    uniform = torch.full((n, 4), .25, dtype=torch.float64)
    first_l = likelihood(data['first_q']).gather(2, data['first_y'][:, None, None].expand(-1, 4, 1)).squeeze(2)
    first = update(uniform, first_l)
    same_first = (data['first_q'][:, 35:38] == data['target_q'][:, 35:38]).all(-1)[:, None]
    same_second = (data['second_q'][:, 35:38] == data['target_q'][:, 35:38]).all(-1)[:, None]
    views, decisions = {}, {}
    for name, prior in (('retained', torch.where(same_first, first, parent[:, 0])), ('cleared', parent[:, 0])):
        branches = torch.stack([mixture(torch.where(same_second, update(uniform, likelihood(data['second_q'])[:, :, y], True), prior),
                                       data['target_q']) for y in range(8)], 1)
        probe, before = mixture(parent[:, 0], data['second_q']), mixture(prior, data['target_q'])
        value = (probe * branches.max(-1).values).sum(-1) - before.max(-1).values
        decisions[name] = {'value': value, 'asks': torch.stack((value > .05+1e-12, value > 1+1e-12,
                                                               torch.zeros(n, dtype=torch.bool)), -1)}
        actual_l = likelihood(data['second_q']).gather(2, data['second_y'][:, None, None].expand(-1, 4, 1)).squeeze(2)
        update(uniform, actual_l)  # Actual support is checked only after the pre-answer decision.
        after = branches[torch.arange(n), data['second_y']]
        views[name] = {'probe': probe, 'before': before,
                       'branches': branches, 'after_second': after, 'protected': mixture(parent[:, 1], data['protected_q'])}
    return {'predictions': {'base_target': mixture(parent[:, 0], data['target_q']),
            'after_first': views['retained']['before'], 'after_second': views['retained']['after_second'],
            'protected': views['retained']['protected']}, 'views': views, 'decisions': decisions}


def collect(prepared, fitted, output):
    import torch
    from . import temporal_native_models_v1 as learned
    stamp, start = source(), (time.perf_counter(), time.process_time())
    frozen_sources(prepared, stamp)
    torch.set_num_threads(1)
    output.mkdir(parents=True, exist_ok=False)
    rows = load(prepared, 'public.json.xz')['test']
    answers = load(prepared, 'test-answers.json.xz')
    data_sha, weights = file_hash(prepared/'manifest.json'), read(fitted/'manifest.json')
    if weights['data_sha256'] != data_sha:
        raise ValueError('checkpoint data binding differs')
    for seed in SEEDS:
        data = tensors(rows, load(prepared, f'native-{seed}.json.xz'), answers)
        for arm in ('native', 'flat', 'rule'):
            checkpoint_sha = 'SUPPLIED_RULE'
            if arm == 'rule':
                forecasts = rule(data)
            else:
                name = f'{arm}-{seed}.json'
                checkpoint_sha = file_hash(fitted/name)
                if checkpoint_sha != weights['checkpoints'][name]['sha256']:
                    raise ValueError('fitted checkpoint changed')
                saved = read(fitted/name)
                if saved['data_sha256'] != data_sha or digest(saved['state']) != saved['state_sha256']:
                    raise ValueError('checkpoint data or tensor binding differs')
                model = learned.Model(arm, seed)
                model.load_state_dict({k: torch.tensor(v, dtype=torch.float64) for k, v in saved['state'].items()})
                result = learned.collect(model, data)
                forecasts = {'predictions': {k: result[k] for k in ('base_target', 'after_first', 'after_second', 'protected')},
                             'views': {}, 'decisions': {}}
                for name, view in (('retained', result), ('cleared', result['cleared'])):
                    forecasts['views'][name] = {'probe': view['q2distribution'], 'before': view['pretarget'],
                        'branches': view['branches'], 'after_second': view['after_second'], 'protected': view['protected']}
                    forecasts['decisions'][name] = {'value': view['question_value'], 'asks': view['question_asks']}
            converted = {key: {name: value.tolist() for name, value in values.items()} for key, values in forecasts.items() if key == 'predictions'}
            converted['views'] = {view: {name: value.tolist() for name, value in values.items()} for view, values in forecasts['views'].items()}
            converted['decisions'] = {view: {name: value.tolist() for name, value in values.items()} for view, values in forecasts['decisions'].items()}
            write(output/f'raw-{seed}-{arm}.json.xz', {'version': VERSION, **stamp, 'seed': seed, 'arm': arm,
                'checkpoint_sha256': checkpoint_sha, 'data_sha256': data_sha, 'ids': [r['id'] for r in rows], **converted})
            print(json.dumps({'stage': 'collect', 'seed': seed, 'arm': arm}), flush=True)
    provenance = [{'id': row['id'], 'base_ids': [r['query']['evidence_id'] for r in row['base']],
                   'first_id': row['first']['query']['evidence_id'], 'second_id': row['second']['evidence_id'],
                   'base_digest': digest(row['base']),
                   'first_digest': digest([*row['base'], {**row['first'], 'source': 'physical'}]),
                   'both_digest': digest([*row['base'], {**row['first'], 'source': 'physical'},
                                          {'query': row['second'], 'endpoint': answers[row['id']], 'source': 'physical'}]),
                   'second_only_digest': digest([*row['base'], {'query': row['second'], 'endpoint': answers[row['id']], 'source': 'physical'}])}
                  for row in rows]
    write(output/'provenance.json.xz', provenance)
    write(output/'manifest.json', {'version': VERSION, **stamp, 'data_sha256': data_sha,
        'artifacts': {p.name: {'sha256': file_hash(p), 'bytes': p.stat().st_size} for p in sorted(output.iterdir())}})
    write(output/'execution.json', receipt(start, {'stage': 'collect'}))
    return {'stage': 'collect', 'files': 15, 'cases_per_file': len(rows)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'fit', 'collect'))
    parser.add_argument('--prepared', type=Path)
    parser.add_argument('--fitted', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.stage == 'prepare':
        result = prepare(args.output)
    elif args.stage == 'fit':
        result = train(args.prepared, args.output)
    else:
        result = collect(args.prepared, args.fitted, args.output)
    print(json.dumps(result, sort_keys=True))
