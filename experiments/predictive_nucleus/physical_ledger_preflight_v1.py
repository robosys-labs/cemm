"""Process-separated TRAIN qualification under PHYSICAL_LEDGER_PROTOCOL_V1.md."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from itertools import permutations
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile

import torch

from . import acceptance_contract as contract
from . import continuation_run as io
from .domain_contract import world_index
from .g3_train_coordinate_intervention import read_locked
from .physical_ledger_v1 import Ledger
from .physical_query_preflight_v1 import FEES, GOALS, observed_posterior
from .physical_query_v1 import choose


PROTOCOL_COMMIT = 'c6f48f6cdda4ad2092931ee88901fdfebe1a4732'
PROTOCOL_SHA256 = '30673cfbd9c22f955b2b0a607a8e122abe38f3c89873e6c8cfd472621187f1f8'
INPUTS = {
    'data/effect-role-v3/teach-inputs.json.xz':
        '74fecfda5a3287e5109d31990b9c62b34c39d7694bfeae7a6c1b0c50a029770d',
    'results/g3-g5-receipt-preflight.json':
        '90b8cc1d175efd11070c5549bceeba80154db30319faa30ba707852579df2363',
    'results/physical-query-preflight-v1.json':
        '769c7e83ce92c8e216a68c137e22624fa0d4e3ce4e34a62c13c25b5e84c94623',
}
SOURCES = ('physical_ledger_preflight_v1.py', 'physical_ledger_v1.py',
           'physical_query_v1.py', 'physical_query_preflight_v1.py',
           'acceptance_contract.py', 'continuation_run.py',
           'g3_train_coordinate_intervention.py', 'domain_contract.py', 'joint_objective.py')
ENCODING = 'domain_contract.world_index:ordered-roster-msb-first-binary-v1'
TOLERANCE = 1e-12
UNIFORM = (.25,) * 4
STAGES = ('producer', 'evaluator', 'recovery')


def _check(report, condition, message):
    if not condition:
        report['failed_checks'].append(message)


def _close(report, label, actual, expected):
    contract.require(len(actual) == len(expected), 'comparison dimensions differ')
    error = max(abs(a - b) for a, b in zip(actual, expected, strict=True))
    report['maximum_errors'][label] = max(report['maximum_errors'].get(label, 0.), error)
    _check(report, error <= TOLERANCE, f'{label} exceeds the registered tolerance')


def _decision_check(report, actual, expected, label):
    _check(report, actual['action'] == expected['action'] and actual['ask'] == expected['ask'],
           f'{label} action or query decision differs')
    keys = ('expected_before', 'expected_after', 'value')
    _close(report, label, [actual[key] for key in keys], [expected[key] for key in keys])


def _route_key(route):
    return route['seed'], route['warmup_id'], route['query_id']


def _native_routes():
    teaching, saved, published = [read_locked(io.ROOT / name, digest)
                                  for name, digest in INPUTS.items()]
    source = {record['id']: record for record in teaching['episodes']}
    contract.require(len(teaching['episodes']) == len(source) == 16, 'teaching inventory differs')
    contract.require(set(saved['seeds']) == {'7', '11', '23', '37', '53'}, 'world inventory differs')
    published_routes = {_route_key(route): route for route in published['routes']}
    contract.require(len(published['routes']) == len(published_routes) == 80,
                     'published route inventory differs')
    routes, warmups, queries = [], Counter(), Counter()
    for seed in (7, 11, 23, 37, 53):
        world = saved['seeds'][str(seed)]
        rows = world['rows']
        contract.require(len(rows) == len({row['evidence_id'] for row in rows}) == 16 and
                         {row['episode_id'] for row in rows} == set(source), 'native receipt inventory differs')
        groups = defaultdict(list)
        for row in rows:
            record = source[row['episode_id']]
            contract.require(row['evidence_id'] == record['id'] + '/utterance/0', 'receipt identity differs')
            prefix = {key: record[key] for key in ('entities', 'anchor', 'context')}
            prefix['utterance'] = record['utterances'][0]['text']
            contract.require(contract.digest(prefix) == row['prefix_digest'], 'public prefix binding differs')
            groups[(tuple(record['entities']), record['utterances'][0]['text'])].append(row)
        contract.require(len(groups) == 8 and all(len(pair) == 2 for pair in groups.values()),
                         'exact utterance pair inventory differs')
        for (entities, utterance), pair in sorted(groups.items()):
            for warmup, query in permutations(sorted(pair, key=lambda row: row['evidence_id'])):
                contract.require(warmup['actions'] == query['actions'] and
                                 warmup['evidence_id'] != query['evidence_id'] and
                                 warmup['prefix_digest'] != query['prefix_digest'], 'unaligned native pair')
                contract.require(len(warmup['actions']) == 4 and
                                 all(len(row) == 8 for row in query['endpoint_probabilities']),
                                 'native hypothesis or endpoint inventory differs')
                binding = {
                    'interpretation_sha256': contract.digest({'entities': entities, 'utterance': utterance}),
                    'world_sha256': world['world_sha256'],
                    'source_sha256': INPUTS['results/g3-g5-receipt-preflight.json'],
                    'actions': warmup['actions'], 'endpoint_encoding': ENCODING, 'endpoint_count': 8,
                }
                route = {'seed': seed, 'warmup_id': warmup['evidence_id'], 'query_id': query['evidence_id'],
                         'binding': binding, 'warmup': warmup, 'query': query}
                route['published'] = published_routes[_route_key(route)]
                routes.append(route)
                warmups[seed, warmup['evidence_id']] += 1
                queries[seed, query['evidence_id']] += 1
    expected = Counter((int(seed), row['evidence_id']) for seed, world in saved['seeds'].items()
                       for row in world['rows'])
    contract.require(len(routes) == len({_route_key(route) for route in routes}) == 80 and
                     warmups == queries == expected and set(map(_route_key, routes)) == set(published_routes),
                     'incomplete ordered-route coverage')
    contract.require(sum(len(route['policies']) for route in published_routes.values()) == 960,
                     'published policy inventory differs')
    return routes


def _receipt(binding, row):
    endpoint = int(world_index(torch.tensor(row['observed_endpoint'])))
    likelihood = row['endpoint_probabilities']
    contract.require([values[endpoint] for values in likelihood] == row['observed_likelihoods'],
                     'observed likelihood binding differs')
    return {'evidence_id': row['evidence_id'], 'prefix_digest': row['prefix_digest'],
            'binding_digest': contract.digest(binding), 'kind': 'physical_endpoint',
            'likelihood': deepcopy(likelihood), 'endpoint': endpoint}


def _forecast(binding, row):
    contract.require(row['actions'] == binding['actions'], 'forecast action binding differs')
    return {'binding_digest': contract.digest(binding), 'likelihood': deepcopy(row['endpoint_probabilities'])}


def _state(ledger):
    raw = json.dumps(ledger.snapshot(), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return raw, ledger.receipt_count, ledger.posterior, ledger.failure_evidence_id


def _conflicts(receipt, endpoint_count):
    prefix = deepcopy(receipt)
    prefix['prefix_digest'] = ('0' if prefix['prefix_digest'][0] != '0' else '1') + prefix['prefix_digest'][1:]
    endpoint = deepcopy(receipt)
    endpoint['endpoint'] = (endpoint['endpoint'] + 1) % endpoint_count
    likelihood = deepcopy(receipt)
    for row in likelihood['likelihood']:
        for index, value in enumerate(row):
            if value != row[0]:
                row[0], row[index] = row[index], row[0]
                return {'prefix': prefix, 'endpoint': endpoint, 'likelihood': likelihood}
    raise ValueError('native receipt has no unequal likelihood entries for the registered conflict')


def _exercise(ledger, path, report, label):
    original = _state(ledger)
    checkpoint = path.read_bytes()
    receipts = ledger.snapshot()['receipts']
    report['counts']['accepted_receipt_occurrences'] += len(receipts)
    for receipt in receipts:
        report['counts']['duplicate_attempts'] += 1
        identical = ledger.add(deepcopy(receipt)) is False and _state(ledger) == original
        report['counts']['idempotent_duplicates'] += int(identical)
        _check(report, identical, f'{label} duplicate changed state')
        for kind, changed in _conflicts(receipt, ledger.snapshot()['binding']['endpoint_count']).items():
            report['counts']['conflict_attempts'] += 1
            rejected = False
            try:
                ledger.add(changed)
            except ValueError:
                rejected = True
            atomic = rejected and _state(ledger) == original
            report['counts']['atomic_conflict_rejections'] += int(atomic)
            report['counts'][kind + '_conflict_rejections'] += int(atomic)
            _check(report, atomic, f'{label} {kind} conflict failed atomic rejection')
    ledger.save(path)
    _check(report, path.read_bytes() == checkpoint, f'{label} checkpoint changed during duplicate/conflict checks')


def _checkpoint(ledger, directory, name):
    path = directory / name
    digest = ledger.save(path)
    contract.require(digest == io._hash(path), 'saved snapshot hash differs')
    return {'path': name, 'sha256': digest,
            'receipt_ids': [receipt['evidence_id'] for receipt in ledger.snapshot()['receipts']]}


def _published_policies(route, prior_name):
    policies = {(policy['goal'], policy['fee_index']): policy for policy in route['published']['policies']
                if policy['prior'] == prior_name}
    contract.require(len(policies) == len(GOALS) * len(FEES) == 6, 'published context policies differ')
    return policies


def _produce(routes, directory, report):
    report['contexts'] = []
    for index, route in enumerate(routes):
        for prior_name in ('reset', 'retained'):
            ledger = Ledger(route['binding'], UNIFORM)
            uninterrupted = UNIFORM
            if prior_name == 'retained':
                ledger.add(_receipt(route['binding'], route['warmup']))
                uninterrupted = observed_posterior(UNIFORM, route['warmup'])
            _close(report, 'producer_prior', ledger.belief, uninterrupted)
            published = _published_policies(route, prior_name)
            policies = []
            for goal, rewards in GOALS.items():
                for fee_index, fee in enumerate(FEES):
                    decision = choose(uninterrupted, route['query']['endpoint_probabilities'], rewards, fee)
                    updated = observed_posterior(uninterrupted, route['query']) if decision['ask'] else None
                    _decision_check(report, decision, published[goal, fee_index], 'uninterrupted_published_policy')
                    policies.append({'goal': goal, 'fee_index': fee_index, **decision, 'observed_posterior': updated})
            checkpoint = _checkpoint(ledger, directory, f'initial-{index:03d}-{prior_name}.json')
            expected_ids = [route['warmup_id']] if prior_name == 'retained' else []
            _check(report, checkpoint['receipt_ids'] == expected_ids and
                   ledger.receipt_count == len(expected_ids), 'producer receipt inventory differs')
            _exercise(ledger, directory / checkpoint['path'], report, f'producer route {index} {prior_name}')
            report['contexts'].append({'route_key': _route_key(route), 'prior': prior_name,
                'binding': route['binding'], 'checkpoint': checkpoint,
                'uninterrupted_prior': uninterrupted, 'uninterrupted_policies': policies})
    report['counts']['initial_snapshots'] = len(report['contexts'])


def _evaluate(routes, directory, producer, report):
    indexed = {_route_key(route): route for route in routes}
    report['contexts'], report['purchases'] = [], []
    for context_index, context in enumerate(producer['contexts']):
        route = indexed[tuple(context['route_key'])]
        prior_name, checkpoint = context['prior'], context['checkpoint']
        contract.require(context['binding'] == route['binding'], 'producer frame differs from pinned input')
        ledger = Ledger.load(directory / checkpoint['path'], checkpoint['sha256'], route['binding'])
        report['counts']['initial_reloads'] += 1
        expected_ids = [route['warmup_id']] if prior_name == 'retained' else []
        actual_ids = [receipt['evidence_id'] for receipt in ledger.snapshot()['receipts']]
        _check(report, actual_ids == checkpoint['receipt_ids'] == expected_ids and
               ledger.receipt_count == len(expected_ids), 'initial reload receipt inventory differs')
        prior = ledger.belief
        _close(report, 'initial_prior_uninterrupted', prior, context['uninterrupted_prior'])
        _close(report, 'initial_prior_published', prior, route['published']['priors'][prior_name])
        _exercise(ledger, directory / checkpoint['path'], report, f'evaluator context {context_index}')
        initial = _state(ledger)
        forecast = _forecast(route['binding'], route['query'])
        complemented = deepcopy(route['query'])
        complemented['observed_endpoint'] = [1 - bit for bit in complemented['observed_endpoint']]
        control = _forecast(route['binding'], complemented)
        _check(report, forecast == control, 'unconsumed outcome changed forecast')
        published = _published_policies(route, prior_name)
        uninterrupted = {(policy['goal'], policy['fee_index']): policy
                         for policy in context['uninterrupted_policies']}
        policies = []
        for goal, rewards in GOALS.items():
            for fee_index, fee in enumerate(FEES):
                decision = choose(prior, forecast['likelihood'], rewards, fee)
                alternative = choose(prior, control['likelihood'], rewards, fee)
                report['counts']['policy_evaluations'] += 1
                report['counts']['endpoint_complement_checks'] += 1
                _check(report, decision == alternative, 'unconsumed endpoint changed a decision')
                _decision_check(report, decision, uninterrupted[goal, fee_index], 'policy_uninterrupted')
                _decision_check(report, decision, published[goal, fee_index], 'policy_published')
                updated = None
                if decision['ask']:
                    branch = Ledger.load(directory / checkpoint['path'], checkpoint['sha256'], route['binding'])
                    branch.add(_receipt(route['binding'], route['query']))
                    updated = branch.belief
                    purchased = _checkpoint(branch, directory,
                        f'purchased-{context_index:03d}-{goal}-{fee_index}.json')
                    report['purchases'].append({'route_key': context['route_key'], 'prior': prior_name,
                        'goal': goal, 'fee_index': fee_index, 'binding': route['binding'],
                        'checkpoint': purchased, 'posterior': updated})
                    report['counts'][prior_name + '_purchases'] += 1
                else:
                    report['counts']['hold_branches'] += 1
                    _check(report, _state(ledger) == initial and
                           io._hash(directory / checkpoint['path']) == checkpoint['sha256'],
                           'hold branch changed evidence or snapshot bytes')
                policies.append({'goal': goal, 'fee_index': fee_index, **decision, 'observed_posterior': updated})
        _check(report, _state(ledger) == initial, 'policy branching changed the shared pre-query state')
        report['contexts'].append({'route_key': context['route_key'], 'prior': prior_name,
            'checkpoint': checkpoint, 'belief': prior, 'policies': policies})


def _recover(routes, directory, producer, evaluator, report):
    indexed = {_route_key(route): route for route in routes}
    references = {(tuple(context['route_key']), context['prior']): context for context in producer['contexts']}
    completed = defaultdict(list)
    report['recovered'] = []
    for purchase in evaluator['purchases']:
        route_key, prior_name = tuple(purchase['route_key']), purchase['prior']
        route, checkpoint = indexed[route_key], purchase['checkpoint']
        contract.require(purchase['binding'] == route['binding'], 'purchase frame differs from pinned input')
        ledger = Ledger.load(directory / checkpoint['path'], checkpoint['sha256'], route['binding'])
        report['counts']['purchased_reloads'] += 1
        expected_ids = [route['query_id']]
        if prior_name == 'retained':
            expected_ids.insert(0, route['warmup_id'])
        actual_ids = [receipt['evidence_id'] for receipt in ledger.snapshot()['receipts']]
        _check(report, actual_ids == checkpoint['receipt_ids'] == expected_ids,
               'recovered purchase receipt inventory differs')
        _check(report, ledger.receipt_count == len(expected_ids), 'recovered receipt count differs')
        belief = ledger.belief
        reference = references[route_key, prior_name]
        policy_key = purchase['goal'], purchase['fee_index']
        uninterrupted = {(policy['goal'], policy['fee_index']): policy
                         for policy in reference['uninterrupted_policies']}
        published = _published_policies(route, prior_name)
        _close(report, 'purchased_posterior_uninterrupted', belief,
               uninterrupted[policy_key]['observed_posterior'])
        _close(report, 'purchased_posterior_published', belief, published[policy_key]['observed_posterior'])
        _close(report, 'purchased_posterior_pre_restart', belief, purchase['posterior'])
        _exercise(ledger, directory / checkpoint['path'], report,
                  f'recovery route {route_key} {prior_name}')
        report['recovered'].append({**purchase, 'posterior': belief, 'receipt_ids': actual_ids})
        if prior_name == 'retained':
            pair_key = route['seed'], *sorted((route['warmup_id'], route['query_id']))
            completed[pair_key].append(belief)
    for pair, beliefs in completed.items():
        _check(report, len(beliefs) == 2, f'completed delivery-order pair differs {pair}')
        if len(beliefs) == 2:
            _close(report, 'completed_delivery_order', *beliefs)
            report['counts']['completed_order_comparisons'] += 1


def _worker(stage, directory, producer_sha, evaluator_sha):
    report = {'stage': stage, 'counts': Counter(), 'maximum_errors': {}, 'failed_checks': []}
    try:
        routes = _native_routes()
        report['input_coverage'] = {'teaching_episodes': 16, 'worlds': 5, 'seed_qualified_receipts': 80,
                                  'ordered_routes': len(routes), 'warmup_occurrences': 80, 'query_occurrences': 80}
        if stage == 'producer':
            _produce(routes, directory, report)
            expected = {'initial_snapshots': 160, 'accepted_receipt_occurrences': 80,
                        'idempotent_duplicates': 80, 'atomic_conflict_rejections': 240}
        else:
            producer = contract.load_json(directory / 'producer.json', producer_sha)
            if stage == 'evaluator':
                _evaluate(routes, directory, producer, report)
                expected = {'initial_reloads': 160, 'accepted_receipt_occurrences': 80,
                            'idempotent_duplicates': 80, 'atomic_conflict_rejections': 240,
                            'policy_evaluations': 960, 'endpoint_complement_checks': 960,
                            'hold_branches': 840, 'reset_purchases': 80, 'retained_purchases': 40}
            else:
                evaluator = contract.load_json(directory / 'evaluator.json', evaluator_sha)
                _recover(routes, directory, producer, evaluator, report)
                expected = {'purchased_reloads': 120, 'accepted_receipt_occurrences': 160,
                            'idempotent_duplicates': 160, 'atomic_conflict_rejections': 480,
                            'completed_order_comparisons': 20}
        for name, count in expected.items():
            _check(report, report['counts'][name] == count, f'{stage} {name} inventory differs')
    except Exception as error:
        report['failed_checks'].append(f'{type(error).__name__} {error}')
    artifact = io._write(directory / (stage + '.json'), report)
    print(json.dumps({'stage': stage, 'pid': os.getpid(), 'parent_pid': os.getppid(),
                      'report_sha256': artifact['sha256']}, sort_keys=True))
    return int(bool(report['failed_checks']))


def run(output, custody, work_dir=None):
    contract.require(output != custody and not output.exists() and not custody.exists(),
                     'distinct unused result and custody paths required')
    contract.require(io._hash(io.ROOT / 'PHYSICAL_LEDGER_PROTOCOL_V1.md') == PROTOCOL_SHA256,
                     'prospective protocol changed')
    source_commit = io._git('rev-parse', 'HEAD')
    io._git('merge-base', '--is-ancestor', PROTOCOL_COMMIT, source_commit)
    source_hashes = {}
    for name in SOURCES:
        path = io.ROOT / name
        committed = subprocess.check_output(['git', '-C', str(io.REPO), 'show',
                                             source_commit + ':' + path.relative_to(io.REPO).as_posix()])
        contract.require(committed == path.read_bytes(), f'uncommitted measured source {name}')
        source_hashes[name] = io._hash(path)
    report = {'protocol_commit': PROTOCOL_COMMIT, 'protocol_sha256': PROTOCOL_SHA256,
              'source_commit': source_commit, 'source_sha256': source_hashes, 'input_sha256': INPUTS,
              'scope': 'Existing native TRAIN physical receipt persistence and custody',
              'python': platform.python_version(), 'torch': torch.__version__,
              'fees': FEES, 'goals': GOALS, 'tolerance': TOLERANCE,
              'stages': [], 'failed_checks': [], 'counts': Counter(), 'maximum_errors': {}}
    if work_dir is None:
        directory = Path(tempfile.mkdtemp(prefix='cemm-physical-ledger-'))
    else:
        directory = work_dir.resolve()
        directory.mkdir()
    execution = {'source_commit': source_commit, 'parent_pid': os.getpid(),
                 'workspace': str(directory), 'workers': []}
    environment = dict(os.environ, PYTHONHASHSEED='0', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1')
    environment.pop('PYTHONPATH', None)
    hashes = {}
    for stage in STAGES:
        command = [sys.executable, '-m', __package__ + '.physical_ledger_preflight_v1',
                   '--worker', stage, '--workspace', str(directory)]
        for previous in ('producer', 'evaluator'):
            if previous in hashes:
                command.extend(['--' + previous + '-sha', hashes[previous]])
        result = subprocess.run(command, cwd=io.REPO, env=environment, capture_output=True, text=True)
        receipt = {'stage': stage, 'command': command, 'exit_status': result.returncode,
                   'stdout': result.stdout, 'stderr': result.stderr}
        execution['workers'].append(receipt)
        (directory / (stage + '.stdout')).write_text(result.stdout)
        (directory / (stage + '.stderr')).write_text(result.stderr)
        try:
            process = json.loads(result.stdout)
            receipt.update(process)
            _check(report, process['parent_pid'] == os.getpid() and process['pid'] != os.getpid(),
                   f'{stage} did not report the expected fresh-process boundary')
            hashes[stage] = process['report_sha256']
            evidence = contract.load_json(directory / (stage + '.json'), hashes[stage])
            report['stages'].append(evidence)
            report['failed_checks'].extend(evidence['failed_checks'])
            report['counts'].update(evidence['counts'])
            for label, error in evidence['maximum_errors'].items():
                report['maximum_errors'][label] = max(report['maximum_errors'].get(label, 0.), error)
        except (ValueError, KeyError, OSError) as error:
            report['failed_checks'].append(f'{stage} worker receipt failed {error}')
        _check(report, result.returncode == 0, f'{stage} worker failed')
        if report['failed_checks']:
            break
    pids = [worker.get('pid') for worker in execution['workers']]
    _check(report, len(report['stages']) == 3 and len(set(pids)) == 3, 'three distinct completed workers required')
    for name, count in {'idempotent_duplicates': 320, 'atomic_conflict_rejections': 960,
                        'duplicate_attempts': 320, 'conflict_attempts': 960,
                        'prefix_conflict_rejections': 320, 'endpoint_conflict_rejections': 320,
                        'likelihood_conflict_rejections': 320}.items():
        _check(report, report['counts'][name] == count, f'total {name} inventory differs')
    for name, expected in {**source_hashes, 'PHYSICAL_LEDGER_PROTOCOL_V1.md': PROTOCOL_SHA256}.items():
        try:
            unchanged = io._hash(io.ROOT / name) == expected
        except OSError:
            unchanged = False
        _check(report, unchanged, f'measured source changed during execution {name}')
    report['decision'] = ('REVISE_LEDGER_RECOVERY' if report['failed_checks']
                          else 'RECOVERY_CHECKS_PASSED_PENDING_REPEAT')
    result_artifact = io._write(output, report)
    execution['result_sha256'] = result_artifact['sha256']
    io._write(custody, execution)
    if work_dir is None and not report['failed_checks']:
        shutil.rmtree(directory)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--custody', type=Path)
    parser.add_argument('--work-dir', type=Path, help='retain checkpoints and worker logs in this new directory')
    parser.add_argument('--worker', choices=STAGES, help=argparse.SUPPRESS)
    parser.add_argument('--workspace', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--producer-sha', help=argparse.SUPPRESS)
    parser.add_argument('--evaluator-sha', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        contract.require(args.workspace is not None, 'worker workspace required')
        return _worker(args.worker, args.workspace, args.producer_sha, args.evaluator_sha)
    contract.require(args.output is not None and args.custody is not None, 'output and custody paths required')
    report = run(args.output.resolve(), args.custody.resolve(), args.work_dir)
    print(json.dumps({'decision': report['decision'], 'failed_checks': report['failed_checks']}, sort_keys=True))
    return int(bool(report['failed_checks']))


if __name__ == '__main__':
    raise SystemExit(main())
