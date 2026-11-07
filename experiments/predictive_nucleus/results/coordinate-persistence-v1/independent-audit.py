"""Read-only, standard-library audit of the two frozen G5 recovery invocations.

No CEMM execution modules, evaluator files, model checkpoints, or scored results
are imported. The fixed sample is the first, middle, and last sorted context in
each law/seed/view cell. All checkpoint files, not just the sample, are hashed.
"""
import argparse
from collections import Counter
from hashlib import sha256
import json
import lzma
from math import fsum
from pathlib import Path
import platform
import time

HERE = None
ROOT = None
SOURCE = '9083c5c0f371c8d8a950abb4e8f748b95ff8d778'
MANIFEST_SHA = 'dd2ec95a1fa621907152887cb42ffb3a225bd50485beca5272bdd192ba22c760'
INPUTS_SHA = '4afb826fd3630b75b70791b21699a68af3720a2fae434ec8672f763909ea808a'
VIEWS = ('intact', 'zero_layout', 'cycled_layout')
EXPECTED = {f'{law}/{seed}/{view}' for law in ('nand', 'nor')
            for seed in (7, 11, 23, 37, 53) for view in VIEWS}


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def digest(value):
    return sha256(encoded(value)).hexdigest()


def read(path):
    raw = path.read_bytes()
    return json.loads(lzma.decompress(raw) if path.suffix == '.xz' else raw)


def require(value, description):
    if not value:
        raise ValueError(description)


def same(actual, expected, description):
    require(digest(actual) == digest(expected), description)


def normalize(row):
    total = fsum(row)
    return [value / total for value in row]


def update(prior, likelihood, endpoint):
    # Normalize both operands, matching the public numerical contract rather
    # than trusting any posterior serialized by the recovery runner.
    prior = normalize(prior)
    likelihood = [normalize(row) for row in likelihood]
    weights = [p * row[endpoint] for p, row in zip(prior, likelihood, strict=True)]
    return normalize(weights)


def forecast(prior, projection):
    prior = normalize(prior)
    outputs = {}
    for field, result in (('likelihood', 'endpoint'), ('action_probabilities', 'action')):
        rows = projection[field]
        values = [fsum(weight * row[index] for weight, row in zip(prior, rows, strict=True))
                  for index in range(len(rows[0]))]
        outputs[result + '_probabilities'] = values
        outputs['endpoint_action' if result == 'endpoint' else 'physical_action'] = values.index(max(values))
    return outputs


def policy(prior, observation, target, fee):
    prior = normalize(prior)
    likelihood = [normalize(row) for row in observation['likelihood']]
    rewards = target['likelihood']
    expected = [fsum(weight * row[action] for weight, row in zip(prior, rewards, strict=True))
                for action in range(len(rewards[0]))]
    utilities = []
    for endpoint in range(len(likelihood[0])):
        weights = [prior[h] * likelihood[h][endpoint] for h in range(len(prior))]
        utilities.append(max(fsum(weight * row[action]
                                  for weight, row in zip(weights, rewards, strict=True))
                             for action in range(len(rewards[0]))))
    before, after = max(expected), fsum(utilities)
    value = max(0., after - before)
    return {'action': expected.index(before), 'ask': fee is not None and value > fee + 1e-12,
            'expected_before': before, 'expected_after': after, 'value': value}


def main():
    global HERE, ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-dir', type=Path, required=True,
                        help='Directory containing both fresh runner outputs and run-1/run-2 banks')
    parser.add_argument('--source-root', type=Path, required=True,
                        help='Frozen experiments/predictive_nucleus directory')
    args = parser.parse_args()
    HERE, ROOT = args.evidence_dir.resolve(), args.source_root.resolve()
    started = time.perf_counter()
    reports = [read(HERE / f'recovery-{run}.json.xz') for run in (1, 2)]
    packed = [(HERE / f'recovery-{run}.json.xz').read_bytes() for run in (1, 2)]
    require(packed[0] == packed[1], 'complete deterministic reports differ')
    same(reports[0], reports[1], 'complete report contents differ')
    report = reports[0]
    require(report['source_commit'] == SOURCE and report['failed_checks'] == [] and
            report['decision'] == 'RECOVERY_CHECKS_PASSED_PENDING_REPEAT', 'unsuccessful report')
    require([stage['stage'] for stage in report['stages']] == ['produce', 'resume', 'recover'],
            'stage inventory differs')
    stage_rows = {stage['stage']: {row['key']: row for row in stage['records']}
                  for stage in report['stages']}
    for stage in report['stages']:
        require(not stage['failed_checks'] and len(stage['records']) == len(stage_rows[stage['stage']]) == 23040,
                'failed or incomplete stage')
        require(set(stage['conditions']) == EXPECTED and
                all(counts['seen'] == counts['completed'] == 768 for counts in stage['conditions'].values()),
                'condition coverage differs')
    require(set(stage_rows['produce']) == set(stage_rows['resume']) == set(stage_rows['recover']),
            'cross-stage contexts differ')

    expected_files = {}
    for stage in ('produce', 'resume'):
        for key, row in stage_rows[stage].items():
            phase = 'first' if stage == 'produce' else 'retained'
            name = phase + '/' + sha256(key.encode()).hexdigest() + '.json'
            same(row['checkpoint']['file'], name, 'checkpoint name differs')
            require(name not in expected_files, 'duplicate checkpoint path')
            expected_files[name] = row['checkpoint']['sha256']
            if stage == 'resume':
                same(row['checkpoint'], stage_rows['recover'][key]['checkpoint'], 'recovery checksum differs')
    require(len(expected_files) == 46080, 'checkpoint inventory incomplete')

    executions, inventory_reports, combined_pid, worker_invocations = [], [], [], []
    baseline_inventory = None
    for run, result in enumerate(reports, 1):
        directory = HERE / f'run-{run}'
        custody = read(HERE / f'custody-{run}.json')
        require(custody['source_commit'] == SOURCE and custody['result_sha256'] == sha256(packed[run-1]).hexdigest(),
                'custody source/result binding differs')
        require(len(custody['workers']) == 3 and len({w['pid'] for w in custody['workers']}) == 3,
                'cold-process boundaries missing')
        for worker, stage in zip(custody['workers'], result['stages'], strict=True):
            name = stage['stage']
            data = (directory / (name + '.json')).read_bytes()
            require(worker['stage'] == name and worker['exit_status'] == 0 and
                    worker['parent_pid'] == custody['parent_pid'] and worker['pid'] != custody['parent_pid'] and
                    sha256(data).hexdigest() == worker['report_sha256'], 'worker/stage binding differs')
            same(json.loads(data), stage, 'standalone and included stage reports differ')
            same(read(directory / (name + '-execution.json')),
                 {key: worker[key] for key in read(directory / (name + '-execution.json'))},
                 'worker execution receipt differs')
            require((directory / (name + '.stderr')).read_bytes() == b'', 'worker stderr is nonempty')
            combined_pid.append(worker['pid'])
            worker_invocations.append(worker['invocation_id'])
        actual_names = {str(path.relative_to(directory)) for phase in ('first', 'retained')
                        for path in (directory / phase).glob('*.json')}
        require(actual_names == set(expected_files), 'actual checkpoint inventory differs')
        inventory = []
        for name in sorted(actual_names):
            data = (directory / name).read_bytes()
            value = sha256(data).hexdigest()
            require(value == expected_files[name], 'actual checkpoint hash differs: ' + name)
            inventory.append({'file': name, 'sha256': value, 'bytes': len(data)})
        if baseline_inventory is None:
            baseline_inventory = inventory
        else:
            same(inventory, baseline_inventory, 'two actual checkpoint banks differ')
        inventory_reports.append({'run': run, 'checkpoint_files': len(inventory),
                                  'checkpoint_bytes': sum(row['bytes'] for row in inventory),
                                  'inventory_sha256': digest(inventory)})
        executions.append({'run': run, 'invocation_id': custody['invocation_id'],
                           'parent_pid': custody['parent_pid'],
                           'worker_pids': [worker['pid'] for worker in custody['workers']],
                           'custody_sha256': sha256((HERE / f'custody-{run}.json').read_bytes()).hexdigest()})
        print(f'Full checkpoint inventory verified for run {run}', flush=True)
    require(len(executions) == len({row['invocation_id'] for row in executions}) == 2,
            'complete invocation identities repeat')
    require(len(combined_pid) == 6 and len(worker_invocations) == len(set(worker_invocations)) == 6,
            'six independent worker invocation records required')

    source_files = report['source_sha256']
    for name, expected in source_files.items():
        require(sha256((ROOT / name).read_bytes()).hexdigest() == expected, 'source drift: ' + name)
    manifest_path = ROOT / 'results/coordinate-transport-v1/raw/manifest.json'
    require(sha256(manifest_path.read_bytes()).hexdigest() == MANIFEST_SHA, 'native manifest differs')
    public_path = ROOT / 'data/coordinate-transport-v1/inputs.json.xz'
    require(sha256(public_path.read_bytes()).hexdigest() == INPUTS_SHA, 'public inputs differ')
    manifest, public_data = read(manifest_path), read(public_path)
    public = {trial['id']: trial for trial in public_data['trials']}
    require(len(public) == 1536, 'public trial inventory differs')
    sampled = set()
    for condition in sorted(EXPECTED):
        keys = sorted(key for key in stage_rows['produce'] if key.startswith(condition + '/'))
        require(len(keys) == 768, 'sample condition size differs')
        sampled.update(keys[index] for index in (0, 384, 767))
    samples, policy_counts = [], Counter()
    for shard in manifest['shards']:
        path = manifest_path.parent / shard['file']
        require(sha256(path.read_bytes()).hexdigest() == shard['sha256'] and path.stat().st_size == shard['bytes'],
                'native shard changed')
        raw = read(path)
        for trial in raw['trials']:
            for view in VIEWS:
                key = f"{raw['law']}/{raw['seed']}/{view}/{trial['id']}"
                if key not in sampled:
                    continue
                reference = trial['views'][view]
                same(digest(reference), stage_rows['produce'][key]['reference_sha256'], 'reference digest differs')
                for stage in ('produce', 'resume', 'recover'):
                    same(stage_rows[stage][key]['reference_sha256'], digest(reference), 'cross-stage reference differs')
                checkpoints = [read(HERE / 'run-1' / stage_rows[stage][key]['checkpoint']['file'])
                               for stage in ('produce', 'resume')]
                receipts = reference['receipts']
                expected_deliveries = []
                public_records = [*public[trial['id']]['demonstrations'], public[trial['id']]['query']]
                for index, public_record in enumerate(public_records):
                    receipt = dict(receipts[index])
                    endpoint = None
                    if index < 2:
                        endpoint = receipt.pop('observed_endpoint')
                        bits = public_record['utterances'][0]['reading']
                        require(endpoint == bits[0] * 4 + bits[1] * 2 + bits[2], 'public endpoint differs')
                    else:
                        require('observed_endpoint' not in receipt, 'target outcome entered projection')
                    text = public_record['text'] if 'text' in public_record else public_record['utterances'][0]['text']
                    prefix = {name: public_record[name] for name in ('entities', 'anchor', 'context')}
                    prefix['text'] = text
                    same(receipt['prefix_digest'], digest(prefix), 'public prefix differs')
                    same(receipt['evidence_id'], public_record['id'] + '/utterance/0', 'public evidence identity differs')
                    same(receipt['entities'], public_record['entities'], 'public roster differs')
                    same(receipt['frame_digest'], digest(receipt['frame']), 'frame hash differs')
                    tokens, roster = text.split(), public_record['entities']
                    words = [token for token in tokens if token not in roster]
                    mentions = [roster.index(token) for token in tokens if token in roster]
                    require(len(words) == 1 and len(set(mentions)) == len(mentions) == 2,
                            'public lexical/participant inventory differs')
                    lexical_id = sha256(words[0].encode()).hexdigest()
                    require(lexical_id in raw['model']['new_ids'], 'public word is not acquired')
                    frame = {name: raw['model'][name] for name in ('language_sha256', 'registry_sha256', 'world_sha256')}
                    frame.update(version='coordinate-transport-v1', lexical_id=lexical_id,
                                 transforms=[[1, 1], [1, -1], [-1, 1], [-1, -1]], view=view)
                    same(receipt['frame'], frame, 'complete model/public frame differs')
                    a, b = mentions
                    same(receipt['actions'], [[0, a, b, -1], [0, b, a, -1], [1, a, -1, 1], [1, b, -1, 1]],
                         'public local physical menu differs')
                    if index < 2:
                        expected_deliveries.append({'projection': receipt, 'endpoint': endpoint})
                posteriors, forecasts = [], []
                for index, checkpoint in enumerate(checkpoints):
                    same(checkpoint['deliveries'], expected_deliveries[:index+1], 'saved ordered observations differ')
                    same(checkpoint['initial_prior'], [.25] * 4, 'saved initial prior differs')
                    same(checkpoint['frame'], expected_deliveries[0]['projection']['frame'], 'saved frame differs')
                    same(checkpoint['source_sha256'], shard['sha256'], 'saved native source differs')
                    prior = normalize(checkpoint['initial_prior'])
                    for delivery in checkpoint['deliveries']:
                        prior = update(prior, delivery['projection']['likelihood'], delivery['endpoint'])
                    name = 'first' if index == 0 else 'retained'
                    same(prior, reference['beliefs'][name], 'independent posterior differs')
                    same(prior, stage_rows['produce' if index == 0 else 'resume'][key]['posterior'], 'saved report posterior differs')
                    prediction = forecast(prior, receipts[2])
                    same(prediction, reference['predictions'][name], 'independent forecast differs')
                    posteriors.append(prior)
                    forecasts.append(prediction)
                policies = []
                for prior_name, prior in (('retained', posteriors[0]), ('reset', [.25] * 4)):
                    for fee_index, fee in enumerate((.05, .75, None)):
                        selected = policy(prior, receipts[1], receipts[2], fee)
                        consumed = [receipts[0]['evidence_id']] if prior_name == 'retained' else []
                        final = prior
                        if selected['ask']:
                            final = update(prior, receipts[1]['likelihood'], expected_deliveries[1]['endpoint'])
                            consumed.append(receipts[1]['evidence_id'])
                        prediction = forecast(final, receipts[2])
                        policies.append({'prior': prior_name, 'fee_index': fee_index, 'fee': fee, **selected,
                                         'posterior': final, 'consumed_ids': consumed,
                                         'endpoint_probabilities': prediction['endpoint_probabilities'],
                                         'target_selected_endpoint': prediction['endpoint_action']})
                        policy_counts['total'] += 1
                        policy_counts[prior_name + ('_purchases' if selected['ask'] else '_holds')] += 1
                same(policies, reference['policies'], 'independent query policy differs')
                same(digest(policies), stage_rows['resume'][key]['policies_sha256'], 'policy hash differs')
                same(digest(forecasts[0]), stage_rows['resume'][key]['first_forecast_sha256'], 'first forecast hash differs')
                same(digest(forecasts[1]), stage_rows['recover'][key]['forecast_sha256'], 'retained forecast hash differs')
                same(digest(checkpoints[1]), stage_rows['recover'][key]['ordered_provenance_sha256'], 'saved provenance hash differs')
                samples.append({'key': key, 'reference_sha256': digest(reference),
                                'first_checkpoint': stage_rows['produce'][key]['checkpoint'],
                                'retained_checkpoint': stage_rows['resume'][key]['checkpoint'],
                                'replayed_posterior_sha256': list(map(digest, posteriors)),
                                'replayed_forecast_sha256': list(map(digest, forecasts)),
                                'replayed_policies_sha256': digest(policies)})
    require({sample['key'] for sample in samples} == sampled and len(sampled) == 90, 'independent sample coverage differs')
    result = {'version': 'coordinate-persistence-independent-audit-v1', 'status': 'PASS',
              'source_commit': SOURCE, 'python': platform.python_version(),
              'audit_source_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
              'method': 'Standard-library-only file/hash/inventory audit plus independent normalized Bayesian replay and policy reconstruction; no runner/ledger imports or evaluator reads',
              'complete_reports_byte_identical': True, 'checkpoint_banks_byte_identical': True,
              'checkpoint_files_hashed': 92160, 'stage_reports_hashed': 6,
              'raw_shards_hashed': len(manifest['shards']),
              'report_sha256': sha256(packed[0]).hexdigest(),
              'report_uncompressed_sha256': sha256(lzma.decompress(packed[0])).hexdigest(),
              'inventories': inventory_reports, 'executions': executions,
              'worker_invocation_ids': worker_invocations,
              'process_identity_note': 'Two separately invoked execution environments may reuse numeric PIDs; each run has three distinct child PIDs, and all six worker invocation IDs and both parent invocation IDs are distinct',
              'sample_rule': 'Sorted context indices 0, 384, 767 in every law/seed/view cell, selected before outputs were inspected',
              'sample_conditions': len(EXPECTED), 'sample_contexts': len(samples),
              'actual_checkpoints_independently_replayed': 2 * len(samples),
              'policies_independently_reconstructed': dict(policy_counts),
              'sample_exact_numerical_matches': True, 'samples': sorted(samples, key=lambda row: row['key']),
              'failed_checks': [], 'wall_seconds': time.perf_counter() - started}
    destination = HERE / 'independent-audit.json'
    with destination.open('x') as stream:
        json.dump(result, stream, sort_keys=True, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({key: result[key] for key in ('status', 'checkpoint_files_hashed', 'sample_contexts', 'actual_checkpoints_independently_replayed', 'wall_seconds')}), flush=True)


if __name__ == '__main__':
    main()
