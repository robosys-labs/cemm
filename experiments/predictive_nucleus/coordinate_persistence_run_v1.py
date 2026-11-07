"""Three-process recovery of published native projections; no fitting or truth scoring."""
import argparse
from collections import Counter
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import resource
import subprocess
import sys
import time
from uuid import uuid4

from . import acceptance_contract as c, continuation_run as io
from .coordinate_ledger_v1 import CoordinateLedger, _projection
from .coordinate_transport_run_v1 import FEES, LAWS, SEEDS, UNIFORM, VIEWS, prediction, prefix
from .coordinate_transport_v1 import ENDPOINT_ENCODING, TRANSFORMS
from .physical_query_v1 import choose

PROTOCOL = 'COORDINATE_PERSISTENCE_PROTOCOL_V1.md'
PROTOCOL_COMMIT = 'cd2a54e18463960e47d477b26fded26ae1b58a1f'
PROTOCOL_SHA256 = 'aeb9c5d7d72e63684abb467a511332c16ccaeace529661c241eff3b97cc05f67'
MANIFEST_SHA256 = 'dd2ec95a1fa621907152887cb42ffb3a225bd50485beca5272bdd192ba22c760'
INPUTS_SHA256 = '4afb826fd3630b75b70791b21699a68af3720a2fae434ec8672f763909ea808a'
RAW = io.ROOT / 'results/coordinate-transport-v1/raw'
INPUTS = io.ROOT / 'data/coordinate-transport-v1/inputs.json.xz'
STAGES = ('produce', 'resume', 'recover')
SOURCES = ('coordinate_persistence_run_v1.py', 'coordinate_ledger_v1.py', 'physical_ledger_v1.py',
           'physical_query_v1.py', 'coordinate_transport_run_v1.py', 'coordinate_transport_v1.py',
           'acceptance_contract.py', 'continuation_run.py')
EXPECTED = {f'{law}/{seed}/{view}': 768 for seed in SEEDS for law in LAWS for view in VIEWS}


def source_receipt():
    c.require(io._hash(io.ROOT / PROTOCOL) == PROTOCOL_SHA256, 'published protocol differs')
    c.require(io._git('status', '--porcelain', '--untracked-files=no') == '', 'clean tracked source required')
    commit = io._git('rev-parse', 'HEAD')
    io._git('merge-base', '--is-ancestor', PROTOCOL_COMMIT, commit)
    for name in (*SOURCES, PROTOCOL):
        path = io.ROOT / name
        published = subprocess.check_output(['git', '-C', str(io.REPO), 'show',
                                            commit + ':' + path.relative_to(io.REPO).as_posix()])
        c.require(published == path.read_bytes(), 'unpublished source ' + name)
    return {'protocol_commit': PROTOCOL_COMMIT, 'protocol_sha256': PROTOCOL_SHA256,
            'source_commit': commit, 'source_sha256': {name: io._hash(io.ROOT / name) for name in SOURCES},
            'raw_manifest_sha256': MANIFEST_SHA256, 'public_inputs_sha256': INPUTS_SHA256}


def _same(actual, expected, label):
    c.require(c.digest(actual) == c.digest(expected), label + ' differs')


def _public_projection(receipt, record, model, view, observed):
    public = prefix(record)
    tokens, entities = public['text'].split(), public['entities']
    mentions = [entities.index(token) for token in tokens if token in entities]
    words = [token for token in tokens if token not in entities]
    c.require(len(tokens) == 3 and len(mentions) == len(set(mentions)) == 2 and len(words) == 1,
              'public token inventory differs')
    lexical_id = sha256(words[0].encode()).hexdigest()
    c.require(lexical_id in model['new_ids'], 'public identity is not an acquired word')
    frame = {key: model[key] for key in ('language_sha256', 'registry_sha256', 'world_sha256')}
    frame.update(version='coordinate-transport-v1', lexical_id=lexical_id,
                 transforms=[list(pair) for pair in TRANSFORMS], view=view)
    supplied = deepcopy(receipt)
    if observed:
        bits = record['utterances'][0]['reading']
        c.require(len(bits) == 3 and all(type(bit) is int and bit in (0, 1) for bit in bits),
                  'invalid public observed endpoint')
        endpoint = 4 * bits[0] + 2 * bits[1] + bits[2]
        c.require(type(supplied.get('observed_endpoint')) is int and
                  supplied.pop('observed_endpoint') == endpoint, 'public observed endpoint differs')
    else:
        endpoint = None
        c.require('observed_endpoint' not in supplied, 'target truth entered the projection')
    _same(supplied['frame'], frame, 'public/model frame')
    a, b = mentions
    _same(supplied['actions'], [[0, a, b, -1], [0, b, a, -1],
                               [1, a, -1, 1], [1, b, -1, 1]], 'public local action menu')
    c.require(supplied['evidence_id'] == public['id'] and supplied['entities'] == entities and
              supplied['prefix_digest'] == c.digest({key: public[key] for key in
                                                     ('entities', 'anchor', 'context', 'text')}) and
              supplied['endpoint_encoding'] == ENDPOINT_ENCODING, 'public prefix binding differs')
    return _projection(supplied, c.digest(frame)), endpoint


def native_contexts():
    """Yield only checksum-bound public observations and archived pre-observation projections."""
    manifest = c.load_json(RAW / 'manifest.json', MANIFEST_SHA256)
    c.require(manifest['complete'] is True and manifest['failed_checks'] == [] and
              manifest['inputs_sha256'] == INPUTS_SHA256 and io._hash(INPUTS) == INPUTS_SHA256,
              'published native/public custody differs')
    public = io._read(INPUTS)['trials']
    indexed = {trial['id']: trial for trial in public}
    c.require(len(public) == len(indexed) == 1536, 'public trial inventory differs')
    expected_shards = [(seed, law) for seed in SEEDS for law in LAWS]
    c.require([(item['seed'], item['law']) for item in manifest['shards']] == expected_shards,
              'native shard inventory or order differs')
    for item in manifest['shards']:
        seed, law = item['seed'], item['law']
        c.require(item['file'] == f'raw-{law}-{seed}.json.xz', 'unexpected raw shard path')
        path = RAW / item['file']
        c.require(io._hash(path) == item['sha256'] and path.stat().st_size == item['bytes'],
                  'published raw shard differs')
        raw = io._read(path)
        c.require(raw['version'] == 'coordinate-transport-raw-v1' and
                  raw['seed'] == raw['model']['seed'] == seed and
                  raw['law'] == raw['model']['law'] == law, 'native model identity differs')
        for key in ('source_commit', 'source_sha256', 'protocol_commit', 'protocol_sha256', 'inputs_sha256'):
            _same(raw[key], manifest[key], 'native ' + key)
        trials = raw['trials']
        ids = [trial['id'] for trial in trials]
        c.require(len(ids) == len(set(ids)) == 768 and
                  set(ids) == {trial['id'] for trial in public if trial['law'] == law},
                  'raw/public trial inventory differs')
        for trial in trials:
            observations = indexed[trial['id']]
            c.require(set(trial['views']) == set(VIEWS), 'mapping view inventory differs')
            records = [*observations['demonstrations'], observations['query']]
            c.require(len(records) == 3, 'three public instances required')
            for view in VIEWS:
                reference = trial['views'][view]
                c.fields(reference, ('beliefs', 'policies', 'predictions', 'receipts'))
                c.require(len(reference['receipts']) == 3, 'three native projections required')
                validated = [_public_projection(receipt, record, raw['model'], view, position < 2)
                             for position, (receipt, record) in enumerate(
                                 zip(reference['receipts'], records, strict=True))]
                projections, endpoints = zip(*validated, strict=True)
                c.require(len({row['frame_digest'] for row in projections}) == 1 and
                          len({row['evidence_id'] for row in projections}) == 3,
                          'transport frame or evidence inventory differs')
                condition = f'{law}/{seed}/{view}'
                yield {'key': condition + '/' + trial['id'], 'condition': condition,
                       'source_sha256': item['sha256'], 'frame': projections[0]['frame'],
                       'projections': projections, 'endpoints': endpoints[:2], 'reference': reference}


def _filename(key, phase):
    return phase + '/' + sha256(key.encode()).hexdigest() + '.json'


def _checkpoint(ledger, directory, key, phase):
    name = _filename(key, phase)
    digest = ledger.save(directory / name)
    c.require(io._hash(directory / name) == digest, 'writer checkpoint digest differs')
    return {'file': name, 'sha256': digest}


def _load(context, previous, directory, phase):
    c.require(previous['key'] == context['key'] and
              previous['reference_sha256'] == c.digest(context['reference']), 'previous reference differs')
    checkpoint = previous['checkpoint']
    c.require(checkpoint['file'] == _filename(context['key'], phase), 'checkpoint path differs')
    return CoordinateLedger.load(directory / checkpoint['file'], checkpoint['sha256'],
                                 context['frame'], context['source_sha256'])


def _state(ledger):
    return c.digest(ledger.snapshot()), ledger.posterior, ledger.receipt_count, ledger.failure_evidence_id


def _provenance(ledger, context, count):
    snapshot = ledger.snapshot()
    _same(snapshot['initial_prior'], UNIFORM, 'original initial prior')
    expected = [{'projection': row, 'endpoint': endpoint} for row, endpoint in
                zip(context['projections'][:count], context['endpoints'][:count], strict=True)]
    _same(snapshot['deliveries'], expected, 'ordered complete delivery provenance')
    c.require(ledger.receipt_count == count, 'recovered receipt count differs')


def _produce(context, directory, counts):
    ledger = CoordinateLedger(context['frame'], context['source_sha256'], UNIFORM)
    c.require(ledger.add(context['projections'][0], context['endpoints'][0]), 'first observation not added')
    _same(ledger.belief, context['reference']['beliefs']['first'], 'produced first posterior')
    _provenance(ledger, context, 1)
    counts['first_snapshots'] += 1
    return {'checkpoint': _checkpoint(ledger, directory, context['key'], 'first'),
            'posterior': ledger.belief}


def _resume(context, directory, previous, counts):
    ledger = _load(context, previous, directory, 'first')
    _provenance(ledger, context, 1)
    reference, target = context['reference'], context['projections'][2]
    _same(ledger.belief, reference['beliefs']['first'], 'cold first posterior')
    _same(ledger.belief, previous['posterior'], 'pre-restart first posterior')
    forecast = prediction(ledger.belief, target)
    _same(forecast, reference['predictions']['first'], 'cold first forecast')
    original, policies = _state(ledger), []
    for name in ('retained', 'reset'):
        for fee_index, fee in enumerate(FEES):
            branch = deepcopy(ledger) if name == 'retained' else CoordinateLedger(
                context['frame'], context['source_sha256'], UNIFORM)
            decision = choose(branch.belief, context['projections'][1]['likelihood'], target['likelihood'], fee)
            if decision['ask']:
                c.require(branch.add(context['projections'][1], context['endpoints'][1]),
                          'purchased observation not added')
                counts[name + '_purchases'] += 1
            else:
                counts['hold_branches'] += 1
            final = prediction(branch.belief, target)
            policies.append({'prior': name, 'fee_index': fee_index, 'fee': fee, **decision,
                'posterior': branch.belief,
                'consumed_ids': [row['projection']['evidence_id'] for row in branch.snapshot()['deliveries']],
                'endpoint_probabilities': final['endpoint_probabilities'],
                'target_selected_endpoint': final['endpoint_action']})
            _same(policies[-1], reference['policies'][len(policies) - 1], 'cold policy branch')
            c.require(_state(ledger) == original, 'policy branch changed shared parent')
            counts['policy_checks'] += 1
    _same(policies, reference['policies'], 'complete policy inventory')
    c.require(io._hash(directory / previous['checkpoint']['file']) == previous['checkpoint']['sha256'],
              'policy branch changed initial checkpoint')
    c.require(ledger.add(context['projections'][1], context['endpoints'][1]), 'second observation not added')
    _provenance(ledger, context, 2)
    _same(ledger.belief, reference['beliefs']['retained'], 'continued retained posterior')
    counts['first_reloads'] += 1
    counts['retained_snapshots'] += 1
    return {'checkpoint': _checkpoint(ledger, directory, context['key'], 'retained'),
            'posterior': ledger.belief, 'first_forecast_sha256': c.digest(forecast),
            'policies_sha256': c.digest(policies)}


def _recover(context, directory, previous, counts):
    ledger = _load(context, previous, directory, 'retained')
    _provenance(ledger, context, 2)
    _same(ledger.belief, context['reference']['beliefs']['retained'], 'cold retained posterior')
    _same(ledger.belief, previous['posterior'], 'pre-restart retained posterior')
    forecast = prediction(ledger.belief, context['projections'][2])
    _same(forecast, context['reference']['predictions']['retained'], 'cold retained forecast')
    original = _state(ledger)
    checkpoint = directory / previous['checkpoint']['file']
    before = checkpoint.read_bytes()
    for projection, endpoint in zip(context['projections'][:2], context['endpoints'], strict=True):
        c.require(ledger.add(deepcopy(projection), endpoint) is False and _state(ledger) == original,
                  'duplicate observation changed state')
        counts['idempotent_duplicates'] += 1
        for field in ('prefix', 'endpoint', 'roster'):
            changed, outcome = deepcopy(projection), endpoint
            if field == 'prefix':
                changed['prefix_digest'] = ('0' if changed['prefix_digest'][0] != '0' else '1') + changed['prefix_digest'][1:]
            elif field == 'endpoint':
                outcome = (endpoint + 1) % 8
            else:
                changed['entities'] = list(reversed(changed['entities']))
            rejected = False
            try:
                ledger.add(changed, outcome)
            except ValueError:
                rejected = True
            c.require(rejected and _state(ledger) == original, field + ' conflict did not reject atomically')
            counts[field + '_conflict_rejections'] += 1
    c.require(checkpoint.read_bytes() == before, 'duplicate/conflict attempt changed checkpoint bytes')
    digest = ledger.save(checkpoint)
    c.require(checkpoint.read_bytes() == before and digest == previous['checkpoint']['sha256'],
              'recovered checkpoint round-trip bytes differ')
    counts['retained_reloads'] += 1
    counts['checkpoint_roundtrips'] += 1
    return {'checkpoint': previous['checkpoint'], 'posterior': ledger.belief,
            'forecast_sha256': c.digest(forecast), 'ordered_provenance_sha256': c.digest(ledger.snapshot())}


def stage_report(stage, directory, contexts, previous, expected):
    """Retain every reached case, including failures; native custody is checked by the caller."""
    report = {'stage': stage, 'counts': Counter(), 'conditions': {}, 'records': [], 'failed_checks': []}
    prior = {} if previous is None else {row['key']: row for row in previous['records']}
    c.require(previous is None or len(prior) == len(previous['records']), 'duplicate preceding context')
    seen = set()
    try:
        for context in contexts:
            key, condition = context['key'], context['condition']
            counts = report['conditions'].setdefault(condition, Counter())
            counts['seen'] += 1
            row = {'key': key, 'reference_sha256': c.digest(context['reference'])}
            try:
                c.require(key not in seen, 'duplicate context')
                seen.add(key)
                if stage == 'produce':
                    row.update(_produce(context, directory, counts))
                else:
                    row.update((_resume if stage == 'resume' else _recover)(context, directory, prior[key], counts))
                counts['completed'] += 1
            except Exception as error:
                row['failure'] = {'type': type(error).__name__, 'message': str(error)}
                report['failed_checks'].append({'key': key, **row['failure']})
            report['records'].append(row)
    except Exception as error:
        report['failed_checks'].append({'scope': 'input_inventory', 'type': type(error).__name__, 'message': str(error)})
    if set(report['conditions']) != set(expected):
        report['failed_checks'].append({'scope': 'condition_inventory', 'message': 'condition inventory differs'})
    for condition, count in expected.items():
        actual = report['conditions'].get(condition, {})
        if actual.get('seen') != count or actual.get('completed') != count:
            report['failed_checks'].append({'scope': condition, 'message': 'context coverage differs', 'expected': count})
    for counts in report['conditions'].values():
        report['counts'].update(counts)
    return report


def _worker(stage, directory, previous_sha):
    started, cpu = time.perf_counter(), time.process_time()
    report = {'stage': stage, 'records': [], 'counts': {}, 'conditions': {}, 'failed_checks': []}
    try:
        sources = source_receipt()
        prior_stage = STAGES[STAGES.index(stage) - 1]
        previous = None if stage == 'produce' else c.load_json(directory / (prior_stage + '.json'), previous_sha)
        if previous is not None:
            _same(previous['sources'], sources, 'preceding process source')
            c.require(previous['stage'] == prior_stage, 'preceding process stage differs')
        report = stage_report(stage, directory, native_contexts(), previous, EXPECTED)
        report['sources'] = sources
        _same(source_receipt(), sources, 'source after worker execution')
    except Exception as error:
        report['failed_checks'].append({'scope': 'worker', 'type': type(error).__name__, 'message': str(error)})
    artifact = io._write(directory / (stage + '.json'), report)
    execution = {'stage': stage, 'pid': os.getpid(), 'parent_pid': os.getppid(),
                 'invocation_id': uuid4().hex, 'report_sha256': artifact['sha256'],
                 'cpu_seconds': time.process_time() - cpu, 'wall_seconds': time.perf_counter() - started,
                 'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}
    io._write(directory / (stage + '-execution.json'), execution)
    print(json.dumps(execution, sort_keys=True), flush=True)
    return int(bool(report['failed_checks']))


def run(output, custody, work_dir):
    output, custody, directory = (Path(path).resolve() for path in (output, custody, work_dir))
    c.require(output != custody and not output.exists() and not custody.exists() and not directory.exists(),
              'new workspace and distinct unused output/custody paths required')
    sources = source_receipt()
    directory.mkdir(parents=True)
    for phase in ('first', 'retained'):
        (directory / phase).mkdir()
    report = {'version': 'coordinate-persistence-v1', **sources,
              'scope': 'Cold recovery/replay from published native projections; no new scientific admission',
              'python': platform.python_version(), 'parameter_delta': 0,
              'stages': [], 'counts': Counter(), 'failed_checks': []}
    execution = {'source_commit': sources['source_commit'], 'invocation_id': uuid4().hex,
                 'parent_pid': os.getpid(), 'workspace': str(directory), 'workers': []}
    environment = dict(os.environ, PYTHONHASHSEED='0', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    environment.pop('PYTHONPATH', None)
    previous_sha = None
    for stage in STAGES:
        command = [sys.executable, '-m', __package__ + '.coordinate_persistence_run_v1',
                   '--worker', stage, '--work-dir', str(directory)]
        if previous_sha is not None:
            command += ['--previous-sha', previous_sha]
        result = subprocess.run(command, cwd=io.REPO, env=environment, capture_output=True, text=True)
        (directory / (stage + '.stdout')).write_text(result.stdout)
        (directory / (stage + '.stderr')).write_text(result.stderr)
        receipt = {'stage': stage, 'exit_status': result.returncode, 'command': command}
        execution['workers'].append(receipt)
        try:
            receipt.update(json.loads(result.stdout))
            c.require(receipt['parent_pid'] == os.getpid() and receipt['pid'] != os.getpid(),
                      'expected cold-process boundary missing')
            previous_sha = receipt['report_sha256']
            evidence = c.load_json(directory / (stage + '.json'), previous_sha)
            _same(evidence['sources'], sources, 'worker source')
            report['stages'].append(evidence)
            report['counts'].update(evidence['counts'])
            report['failed_checks'].extend(evidence['failed_checks'])
            c.require(result.returncode == 0, 'worker returned a failure')
        except (ValueError, KeyError, OSError) as error:
            report['failed_checks'].append({'scope': stage, 'message': str(error)})
        if report['failed_checks']:
            break
        print(stage + ' complete', flush=True)
    pids = [worker.get('pid') for worker in execution['workers']]
    if len(report['stages']) != 3 or len(set(pids)) != 3:
        report['failed_checks'].append({'scope': 'processes', 'message': 'three distinct completed workers required'})
    try:
        _same(source_receipt(), sources, 'source after qualification')
    except Exception as error:
        report['failed_checks'].append({'scope': 'final_source', 'message': str(error)})
    report['decision'] = ('REVISE_TRANSFORMED_FRAME_RECOVERY' if report['failed_checks'] else
                          'RECOVERY_CHECKS_PASSED_PENDING_REPEAT')
    result_artifact = io._write(output, report)
    execution['result_sha256'] = result_artifact['sha256']
    io._write(custody, execution)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--custody', type=Path)
    parser.add_argument('--work-dir', type=Path, required=True)
    parser.add_argument('--worker', choices=STAGES, help=argparse.SUPPRESS)
    parser.add_argument('--previous-sha', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return _worker(args.worker, args.work_dir, args.previous_sha)
    c.require(args.output is not None and args.custody is not None, 'output and custody paths required')
    result = run(args.output, args.custody, args.work_dir)
    print(json.dumps({'decision': result['decision'], 'counts': result['counts'],
                      'failed_checks': result['failed_checks']}, sort_keys=True))
    return int(bool(result['failed_checks']))


if __name__ == '__main__':
    raise SystemExit(main())
