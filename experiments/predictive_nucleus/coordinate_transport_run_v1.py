"""Published-source collection and sealed-raw evaluation of learned coordinate transport."""
import argparse
from copy import deepcopy
from hashlib import sha256
from math import fsum
import os
from pathlib import Path
import platform
import resource
import subprocess
import time
from uuid import uuid4

import torch

from . import acceptance_contract as c, continuation_run as io
from .domain_contract import world_index
from .physical_query_v1 import _row, choose, posterior

PROTOCOL = 'COORDINATE_TRANSPORT_PROTOCOL_V1.md'
PROTOCOL_COMMIT = '97ff1f00ed8f3f3ca330ea14f566bdc87a4d9028'
PROTOCOL_SHA256 = '4ca02dfd87075d6d34bcf322cb9f542a418cc20b87f788fedb74e958368040e4'
SEEDS = (7, 11, 23, 37, 53)
LAWS = ('nand', 'nor')
VIEWS = ('intact', 'zero_layout', 'cycled_layout')
FEES = (.05, .75, None)
UNIFORM = (.25,) * 4
SOURCES = ('coordinate_transport_run_v1.py', 'coordinate_transport_v1.py',
           'coordinate_transport_data_v1.py', 'coordinate_transport_scoring_v1.py',
           'physical_query_v1.py', 'effect_role_lexical.py', 'effect_role_model.py',
           'effect_role_run.py', 'bilingual_model.py', 'binding_model.py',
           'binding_layout_coordinates.py', 'domain_kernel.py', 'domain_contract.py',
           'joint_objective.py', 'acceptance_contract.py', 'continuation_run.py')


def source_receipt():
    c.require(io._hash(io.ROOT / PROTOCOL) == PROTOCOL_SHA256, 'prospective protocol differs')
    c.require(io._git('status', '--porcelain', '--untracked-files=no') == '', 'tracked source must be clean')
    commit = io._git('rev-parse', 'HEAD')
    io._git('merge-base', '--is-ancestor', PROTOCOL_COMMIT, commit)
    for name in SOURCES:
        published(io.ROOT / name)
    return {'protocol_commit': PROTOCOL_COMMIT, 'protocol_sha256': PROTOCOL_SHA256,
            'source_commit': commit, 'source_sha256': {name: io._hash(io.ROOT / name) for name in SOURCES}}


def published(path):
    relative = path.resolve().relative_to(io.REPO).as_posix()
    raw = subprocess.check_output(['git', '-C', str(io.REPO), 'show', 'HEAD:' + relative])
    c.require(raw == path.read_bytes(), 'unpublished artifact ' + relative)


def prediction(prior, receipt):
    prior = _row(prior, probability=True)
    def mixture(rows):
        return [fsum(weight * row[column] for weight, row in zip(prior, rows, strict=True))
                for column in range(len(rows[0]))]
    endpoints = mixture(receipt['likelihood'])
    actions = mixture(receipt['action_probabilities'])
    _row(endpoints, probability=True)
    _row(actions, probability=True)
    return {'endpoint_probabilities': endpoints, 'action_probabilities': actions,
            'endpoint_action': endpoints.index(max(endpoints)),
            'physical_action': actions.index(max(actions))}


def trace(receipts, observed):
    """Keep common-history forecasts and terminal purchased branches distinct."""
    c.require(len(receipts) == 3 and len(observed) == 2, 'two demonstrations and a target required')
    c.require(len({row['evidence_id'] for row in receipts}) == 3, 'duplicate instance evidence')
    c.require(all(c.digest(row['frame']) == row['frame_digest'] for row in receipts), 'frame payload differs')
    c.require(len({row['frame_digest'] for row in receipts}) == 1, 'hypothesis frame changed')
    result = {'receipts': deepcopy(receipts)}
    first, second, target = result['receipts']
    first['observed_endpoint'], second['observed_endpoint'] = observed
    try:
        after_first = posterior(UNIFORM, first['likelihood'], observed[0])
    except ValueError as error:
        result['failure'] = {'message': str(error), 'evidence_id': first['evidence_id']}
        return result
    policies = []
    for name, prior in (('retained', after_first), ('reset', UNIFORM)):
        for fee_index, fee in enumerate(FEES):
            decision = choose(prior, second['likelihood'], target['likelihood'], fee)
            consumed = [first['evidence_id']] if name == 'retained' else []
            final = prior
            row = {'prior': name, 'fee_index': fee_index, 'fee': fee, **decision}
            if decision['ask']:
                consumed.append(second['evidence_id'])
                try:
                    final = posterior(prior, second['likelihood'], observed[1])
                except ValueError as error:
                    final = None
                    row['failure'] = {'message': str(error), 'evidence_id': second['evidence_id']}
                    result.setdefault('failure', row['failure'])
            forecast = prediction(final, target) if final is not None else None
            row.update(posterior=final, consumed_ids=consumed,
                       endpoint_probabilities=forecast['endpoint_probabilities'] if forecast else None,
                       target_selected_endpoint=forecast['endpoint_action'] if forecast else None)
            policies.append(row)
    result['policies'] = policies
    beliefs = {'reset': UNIFORM, 'first': after_first}
    for name, prior in (('latest', UNIFORM), ('retained', after_first)):
        try:
            beliefs[name] = posterior(prior, second['likelihood'], observed[1])
        except ValueError as error:
            beliefs[name] = None
            result.setdefault('failure', {'message': str(error), 'evidence_id': second['evidence_id']})
    result['beliefs'] = beliefs
    result['predictions'] = {name: prediction(belief, target) if belief is not None else None
                             for name, belief in beliefs.items()}
    return result


def prefix(record):
    """Only public history and text enter the native projection interface."""
    text = record['text'] if 'text' in record else record['utterances'][0]['text']
    return {key: deepcopy(record[key]) for key in ('entities', 'anchor', 'context')} | {
        'id': record['id'] + '/utterance/0', 'text': text}


def collect(data, output):
    from .coordinate_transport_v1 import project, restore
    sources = source_receipt()
    published(data / 'freeze.json')
    freeze = io._read(data / 'freeze.json')
    evaluator = (data / 'evaluator.json.xz').resolve().relative_to(io.REPO).as_posix()
    sealed = subprocess.check_output(['git', '-C', str(io.REPO), 'show', 'HEAD:' + evaluator])
    c.require(sha256(sealed).hexdigest() == freeze['artifacts']['evaluator.json.xz']['sha256'],
              'evaluator must be published before collection')
    del sealed
    inputs_path = data / 'inputs.json.xz'
    published(inputs_path)
    expected = freeze['artifacts']['inputs.json.xz']['sha256']
    c.require(io._hash(inputs_path) == expected, 'observed input hash differs')
    inputs = io._read(inputs_path)
    trials = inputs['trials']
    c.require(len(trials) == len({trial['id'] for trial in trials}) == 1536, 'trial inventory differs')
    output.mkdir(parents=True, exist_ok=False)
    torch.set_num_threads(1)
    manifest = {**sources, 'inputs_sha256': expected, 'complete': False, 'shards': [], 'failed_checks': []}
    execution = {**sources, 'python': platform.python_version(), 'torch': torch.__version__,
                 'pid': os.getpid(), 'invocation_id': uuid4().hex, 'shards': []}
    try:
        for seed in SEEDS:
            for law in LAWS:
                cpu, started = time.process_time(), time.perf_counter()
                name = f'raw-{law}-{seed}.json.xz'
                io._write(output / f'attempt-{law}-{seed}.json',
                          {'seed': seed, 'law': law, 'source_commit': sources['source_commit'], 'pid': os.getpid()})
                selected = [trial for trial in trials if trial['law'] == law]
                c.require(len(selected) == 768, 'law inventory differs')
                records = [prefix(record) for trial in selected
                           for record in (*trial['demonstrations'], trial['query'])]
                c.require(len(records) == len({row['id'] for row in records}) == 2304,
                          'instance inventory differs')
                net, world, registry, metadata = restore(seed, law)
                raw = {'version': 'coordinate-transport-raw-v1', **sources, 'inputs_sha256': expected,
                       'seed': seed, 'law': law, 'model': metadata, 'checks': {},
                       'trials': [{'id': trial['id'], 'views': {}} for trial in selected]}
                for view in VIEWS:
                    rows, checks = project(net, world, registry, records, view)
                    c.require(set(rows) == {record['id'] for record in records}, 'projected evidence IDs differ')
                    raw['checks'][view] = checks
                    for trial, destination in zip(selected, raw['trials'], strict=True):
                        c.require(trial['id'] == destination['id'], 'trial join differs')
                        keys = [record['id'] + '/utterance/0'
                                for record in (*trial['demonstrations'], trial['query'])]
                        observed = [int(world_index(torch.tensor(record['utterances'][0]['reading'])))
                                    for record in trial['demonstrations']]
                        row = trace([rows[key] for key in keys], observed)
                        destination['views'][view] = row
                        if 'failure' in row:
                            manifest['failed_checks'].append({'seed': seed, 'law': law,
                                'trial': trial['id'], 'view': view, **row['failure']})
                artifact = io._write(output / name, raw)
                manifest['shards'].append({'seed': seed, 'law': law, 'file': name, **artifact})
                execution['shards'].append({'seed': seed, 'law': law, 'cpu_seconds': time.process_time() - cpu,
                    'wall_seconds': time.perf_counter() - started,
                    'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss})
                print(f'Collected {law}/{seed}', flush=True)
        c.require(source_receipt() == sources, 'source changed during native collection')
        manifest['complete'] = not manifest['failed_checks'] and len(manifest['shards']) == 10
    except Exception as error:
        manifest['failed_checks'].append({'error': type(error).__name__, 'message': str(error)})
    io._write(output / 'manifest.json', manifest)
    io._write(output / 'execution.json', execution)
    return manifest


def replicate(raw_directory, repeat_directory, output):
    """Record two separate native invocations before evaluator access."""
    sources = source_receipt()
    c.require(raw_directory.resolve() != repeat_directory.resolve(), 'separate native directories required')
    runs = []
    for directory in (raw_directory, repeat_directory):
        manifest_path, execution_path = directory / 'manifest.json', directory / 'execution.json'
        manifest, execution = io._read(manifest_path), io._read(execution_path)
        for name in ('protocol_commit', 'protocol_sha256', 'source_commit', 'source_sha256'):
            c.require(manifest[name] == execution[name] == sources[name], 'native repetition source differs')
        for shard in manifest['shards']:
            path = directory / shard['file']
            c.require(io._hash(path) == shard['sha256'] and path.stat().st_size == shard['bytes'],
                      'native repetition shard differs from manifest')
        runs.append({'manifest': manifest, 'manifest_sha256': io._hash(manifest_path),
                     'execution': execution, 'execution_sha256': io._hash(execution_path)})
    c.require(all(c.identifier(run['execution']['invocation_id']) for run in runs) and
              runs[0]['execution']['invocation_id'] != runs[1]['execution']['invocation_id'],
              'separate native invocations required')
    identical = runs[0]['manifest'] == runs[1]['manifest']
    if identical:
        identical = all((raw_directory / shard['file']).read_bytes() ==
                        (repeat_directory / shard['file']).read_bytes()
                        for shard in runs[0]['manifest']['shards'])
    result = {'version': 'coordinate-transport-replication-v1', 'runs': runs, 'byte_identical': identical}
    c.require(source_receipt() == sources, 'source changed during replication check')
    io._write(output, result)
    return result


def score(data, raw_directory, output):
    from .coordinate_transport_scoring_v1 import score as evaluate
    sources = source_receipt()
    published(raw_directory / 'manifest.json')
    manifest = io._read(raw_directory / 'manifest.json')
    failures = list(manifest['failed_checks'])
    if not manifest['complete']:
        failures.append({'message': 'incomplete native collection'})
    c.require(manifest['source_sha256'] == sources['source_sha256'] and
              manifest['protocol_sha256'] == sources['protocol_sha256'], 'measured source differs')
    replication_path = raw_directory / 'replication.json'
    published(replication_path)
    replication = io._read(replication_path)
    c.require(replication['version'] == 'coordinate-transport-replication-v1' and
              len(replication['runs']) == 2 and replication['runs'][0]['manifest'] == manifest and
              replication['runs'][0]['manifest_sha256'] == io._hash(raw_directory / 'manifest.json') and
              replication['runs'][0]['execution']['invocation_id'] !=
              replication['runs'][1]['execution']['invocation_id'],
              'native repetition receipt differs')
    if replication['byte_identical'] is not True or replication['runs'][1]['manifest'] != manifest:
        failures.append({'message': 'native repetitions differ'})
    raw = []
    for shard in manifest['shards']:
        path = raw_directory / shard['file']
        published(path)
        c.require(io._hash(path) == shard['sha256'], 'raw shard hash differs')
        raw.append(io._read(path))
    published(data / 'freeze.json')
    freeze = io._read(data / 'freeze.json')
    path = data / 'evaluator.json.xz'
    published(path)
    c.require(io._hash(path) == freeze['artifacts'][path.name]['sha256'], 'evaluator hash differs')
    c.require(manifest['inputs_sha256'] == freeze['artifacts']['inputs.json.xz']['sha256'],
              'evaluator/observed bank binding differs')
    result = evaluate(raw, io._read(path), source_info={**sources,
        'raw_publication': io._git('rev-parse', 'HEAD'), 'raw_manifest_sha256': io._hash(raw_directory / 'manifest.json'),
        'evaluator_sha256': io._hash(path), 'replication_sha256': io._hash(replication_path)},
        collection_failures=failures)
    c.require(source_receipt() == sources, 'source changed during scoring')
    io._write(output, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'collect', 'replicate', 'score'))
    parser.add_argument('--data', type=Path)
    parser.add_argument('--raw', type=Path)
    parser.add_argument('--repeat', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.stage == 'prepare':
        from .coordinate_transport_data_v1 import prepare
        source_receipt()
        prepare(args.output)
        return 0
    if args.stage == 'replicate':
        c.require(args.raw is not None and args.repeat is not None, 'two native output directories required')
        return int(not replicate(args.raw, args.repeat, args.output)['byte_identical'])
    c.require(args.data is not None, 'published data directory required')
    if args.stage == 'collect':
        result = collect(args.data, args.output)
        return int(not result['complete'])
    c.require(args.raw is not None, 'published raw directory required')
    result = score(args.data, args.raw, args.output)
    print(result['decision'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
