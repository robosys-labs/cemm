"""Pure evaluator for published coordinate-transport forecasts and separate truth."""
from collections import Counter
from hashlib import sha256
from itertools import permutations, product
from math import fsum, isfinite, log

from . import acceptance_contract as c
from .physical_query_v1 import _row, choose, posterior

VERSION = 'coordinate-transport-score-v1'
PROTOCOL_COMMIT = '97ff1f00ed8f3f3ca330ea14f566bdc87a4d9028'
PROTOCOL_SHA256 = '4ca02dfd87075d6d34bcf322cb9f542a418cc20b87f788fedb74e958368040e4'
TRAINING_SHA256 = '766a8315d66e4a0bfca0079183d3966fbc7a0b4ed65c98177650d245a10671ed'
SEEDS, LAWS = (7, 11, 23, 37, 53), ('nand', 'nor')
WORDS, LAYOUTS = ('lights', 'zef'), ('svo', 'osv', 'vos')
VIEWS = ('intact', 'zero_layout', 'cycled_layout')
BELIEFS = ('reset', 'first', 'latest', 'retained')
CONSUMED = {'reset': (), 'first': (0,), 'latest': (1,), 'retained': (0, 1)}
FEES, UNIFORM = (.05, .75, None), (.25,) * 4
TRANSFORMS = [[1, 1], [1, -1], [-1, 1], [-1, -1]]
MEANINGS = ((0, 0, 1, -1), (0, 1, 0, -1), (1, 0, -1, 1), (1, 1, -1, 1))
ENCODING = 'domain_contract.world_index:ordered-roster-msb-first-binary-v1'
TOLERANCE = 1e-12


def _probabilities(values, size):
    c.require(type(values) in (list, tuple) and len(values) == size, 'probability dimension differs')
    _row(values, probability=True)
    # Saved native rows are scored as published, without a second normalization.
    return tuple(values)


def _matrix(rows, height, width):
    c.require(type(rows) in (list, tuple) and len(rows) == height, 'matrix dimension differs')
    return tuple(_probabilities(row, width) for row in rows)


def _index(value, size):
    c.require(type(value) is int and 0 <= value < size, 'invalid discrete index')
    return value


def _number(value):
    c.require(type(value) in (int, float) and isfinite(value), 'expected finite numeric value')
    return value


def _equal(actual, expected, message):
    c.require(abs(_number(actual) - expected) <= TOLERANCE, message)


def _vector_equal(actual, expected, message):
    c.require(len(actual) == len(expected), message)
    c.require(all(abs(a - b) <= TOLERANCE for a, b in zip(actual, expected)), message)


def _mix(prior, rows):
    prior = _row(prior, probability=True)
    return [fsum(weight * row[column] for weight, row in zip(prior, rows, strict=True))
            for column in range(len(rows[0]))]


def _argmax(values):
    return values.index(max(values))


def _oracle_distribution(oracle, consumed):
    """Condition the uniform primitive-meaning prior on exactly the delivered tape."""
    survivors = [meaning for meaning in range(4) if all(
        oracle['outcomes_by_meaning'][stage][meaning] == oracle['endpoints'][stage]
        for stage in consumed)]
    c.require(survivors, 'oracle history has no compatible primitive meaning')
    result = [0.] * 8
    for meaning in survivors:
        result[oracle['outcomes_by_meaning'][2][meaning]] += 1. / len(survivors)
    return result


def _point(identity, probabilities, selected_endpoint, selected_action, oracle, consumed):
    probabilities = _probabilities(probabilities, 8)
    conditional = _oracle_distribution(oracle, consumed)
    truth = oracle['endpoints'][2]
    correct = selected_endpoint == truth
    confidence = max(probabilities)
    zero = probabilities[truth] == 0
    oracle_zero = any(q > 0 and p == 0 for q, p in zip(conditional, probabilities))
    return {'id': identity, 'endpoint_correct': correct,
            'action_correct': selected_action == oracle['action_indices'][2],
            'brier': fsum((p - int(index == truth)) ** 2 for index, p in enumerate(probabilities)),
            'nll': None if zero else -log(probabilities[truth]),
            'oracle_kl': None if oracle_zero else fsum(
                q * (log(q) - log(p)) for q, p in zip(conditional, probabilities) if q > 0),
            'zero_probability_outcome': zero, 'oracle_zero_probability': oracle_zero,
            'confidence': confidence, 'high_confidence_wrong': confidence >= .95 and not correct}


def _prediction_summary(records):
    count = len(records)
    c.require(count > 0, 'empty prediction group')
    bins = []
    for index in range(10):
        selected = [row for row in records if min(9, int(row['confidence'] * 10)) == index]
        size = len(selected)
        bins.append({'lower': index / 10, 'upper': (index + 1) / 10, 'count': size,
                     'accuracy': fsum(row['endpoint_correct'] for row in selected) / size if size else None,
                     'mean_confidence': fsum(row['confidence'] for row in selected) / size if size else None})
    infinite_nll = sum(row['zero_probability_outcome'] for row in records)
    infinite_kl = sum(row['oracle_zero_probability'] for row in records)
    high = sum(row['confidence'] >= .95 for row in records)
    return {'count': count,
            'endpoint_accuracy': fsum(row['endpoint_correct'] for row in records) / count,
            'action_accuracy': fsum(row['action_correct'] for row in records) / count,
            'mean_brier': fsum(row['brier'] for row in records) / count,
            'mean_nll': None if infinite_nll else fsum(row['nll'] for row in records) / count,
            'nll_status': 'infinite' if infinite_nll else 'finite', 'infinite_nll_count': infinite_nll,
            'mean_oracle_kl': None if infinite_kl else fsum(row['oracle_kl'] for row in records) / count,
            'oracle_kl_status': 'infinite' if infinite_kl else 'finite', 'infinite_oracle_kl_count': infinite_kl,
            'ece_10': fsum(row['count'] * abs(row['accuracy'] - row['mean_confidence'])
                           for row in bins if row['count']) / count,
            'calibration_bins': bins, 'high_confidence_count': high, 'high_confidence_coverage': high / count,
            'high_confidence_wrong': sum(row['high_confidence_wrong'] for row in records)}


def _policy_summary(records):
    count = len(records)
    c.require(count > 0, 'empty policy group')
    return {'count': count, 'purchased_count': sum(row['ask'] for row in records),
            'correct_count': sum(row['correct'] for row in records),
            'accuracy': fsum(row['correct'] for row in records) / count,
            'gross_total': fsum(row['gross'] for row in records),
            'fee_total': fsum(row['fee_paid'] for row in records),
            'net_total': fsum(row['net'] for row in records),
            'mean_gross': fsum(row['gross'] for row in records) / count,
            'mean_fee': fsum(row['fee_paid'] for row in records) / count,
            'mean_net': fsum(row['net'] for row in records) / count}


def _validate_oracle(evaluator):
    c.fields(evaluator, ('version', 'trials'))
    c.require(evaluator['version'] == 'coordinate-transport-v1' and
              type(evaluator['trials']) is list and len(evaluator['trials']) == 1536,
              'evaluator version or trial count differs')
    rows, cells, instances = {}, Counter(), set()
    for row in evaluator['trials']:
        c.fields(row, ('id', 'law', 'word', 'meaning', 'canonical_action', 'physical_actions',
                       'action_indices', 'endpoints', 'outcomes_by_meaning', 'instance_ids',
                       'evidence_ids', 'metadata'))
        c.require(c.identifier(row['id']) and row['id'] not in rows, 'invalid or duplicate oracle trial ID')
        c.require(row['law'] in LAWS and row['word'] in WORDS, 'unregistered law or lexical identity')
        meaning = _index(row['meaning'], 4)
        c.require(type(row['canonical_action']) is list and len(row['canonical_action']) == 4 and
                  all(type(value) is int for value in row['canonical_action']) and
                  tuple(row['canonical_action']) == MEANINGS[meaning], 'canonical primitive meaning differs')
        metadata = row['metadata']
        c.fields(metadata, ('layouts', 'pattern', 'modes'))
        c.require(type(metadata['layouts']) is list and
                  sorted(metadata['layouts']) == sorted(LAYOUTS), 'layout permutation differs')
        _index(metadata['pattern'], 2)
        c.require(type(metadata['modes']) is list and len(metadata['modes']) == 3, 'mode inventory differs')
        for mode in metadata['modes']:
            _index(mode, 2)
        for name in ('physical_actions', 'action_indices', 'endpoints', 'outcomes_by_meaning',
                     'instance_ids', 'evidence_ids'):
            c.require(type(row[name]) is list and len(row[name]) == 3, 'oracle stage inventory differs')
        for stage in range(3):
            action = row['physical_actions'][stage]
            c.require(type(action) is list and len(action) == 4 and all(type(v) is int for v in action),
                      'invalid oracle physical action')
            _index(row['action_indices'][stage], 4)
            _index(row['endpoints'][stage], 8)
            outcomes = row['outcomes_by_meaning'][stage]
            c.require(type(outcomes) is list and len(outcomes) == 4, 'oracle meaning inventory differs')
            for endpoint in outcomes:
                _index(endpoint, 8)
            c.require(outcomes[meaning] == row['endpoints'][stage], 'realized and counterfactual endpoints differ')
            instance = row['instance_ids'][stage]
            c.require(c.identifier(instance) and instance not in instances, 'duplicate or invalid instance ID')
            c.require(row['evidence_ids'][stage] == instance + '/utterance/0', 'evidence/instance join differs')
            instances.add(instance)
            index = meaning if metadata['layouts'][stage] == 'svo' else (1, 0, 3, 2)[meaning]
            c.require(row['action_indices'][stage] == index, 'meaning/local-action covariance differs')
        cells[(row['law'], row['word'], meaning, tuple(metadata['layouts']), metadata['pattern'],
               tuple(metadata['modes']))] += 1
        rows[row['id']] = row
    expected = set(product(LAWS, WORDS, range(4), permutations(LAYOUTS), range(2), product((0, 1), repeat=3)))
    c.require(set(cells) == expected and set(cells.values()) == {1}, 'registered factorial inventory differs')
    return rows


def _validate_receipt(receipt, oracle, stage, view, model):
    names = ('evidence_id', 'prefix_digest', 'entities', 'actions', 'endpoint_encoding',
             'action_probabilities', 'native_likelihood', 'likelihood', 'frame', 'frame_digest')
    c.fields(receipt, (*names, 'observed_endpoint') if stage < 2 else names)
    c.require(receipt['evidence_id'] == oracle['evidence_ids'][stage] and
              c.is_sha(receipt['prefix_digest']), 'receipt identity or prefix digest differs')
    entities = receipt['entities']
    c.require(type(entities) is list and len(entities) == 3 and all(map(c.identifier, entities)) and
              len(set(entities)) == 3, 'invalid public roster')
    actions = receipt['actions']
    c.require(type(actions) is list and len(actions) == 4 and all(
        type(row) is list and len(row) == 4 and all(type(value) is int for value in row)
        for row in actions), 'invalid local physical menu')
    a, b = actions[0][1:3]
    _index(a, 3)
    _index(b, 3)
    c.require(a != b and actions == [[0, a, b, -1], [0, b, a, -1], [1, a, -1, 1], [1, b, -1, 1]],
              'local physical menu geometry differs')
    c.require(actions[oracle['action_indices'][stage]] == oracle['physical_actions'][stage],
              'physical-action oracle join differs')
    c.require(receipt['endpoint_encoding'] == ENCODING, 'endpoint encoding differs')
    if stage < 2:
        _index(receipt['observed_endpoint'], 8)
        c.require(receipt['observed_endpoint'] == oracle['endpoints'][stage], 'delivered endpoint differs')
    frame = receipt['frame']
    c.fields(frame, ('version', 'language_sha256', 'registry_sha256', 'world_sha256',
                     'lexical_id', 'transforms', 'view'))
    c.require(frame['version'] == 'coordinate-transport-v1' and frame['view'] == view and
              frame['transforms'] == TRANSFORMS and
              frame['lexical_id'] == sha256(oracle['word'].encode()).hexdigest(), 'hypothesis frame differs')
    for key in ('language_sha256', 'registry_sha256', 'world_sha256'):
        c.require(c.is_sha(frame[key]) and frame[key] == model[key], 'model/frame binding differs')
    c.require(c.is_sha(receipt['frame_digest']) and receipt['frame_digest'] == c.digest(frame),
              'frame digest differs')
    actions_probability = _matrix(receipt['action_probabilities'], 4, 4)
    native = _matrix(receipt['native_likelihood'], 4, 8)
    likelihood = _matrix(receipt['likelihood'], 4, 8)
    _vector_equal(_mix(UNIFORM, actions_probability), UNIFORM, 'uniform hypothesis action invariant failed')
    for weights, projected in zip(actions_probability, likelihood):
        # Projection uses the saved native action weights without renormalizing them.
        expected = [fsum(weight * row[column] for weight, row in zip(weights, native)) for column in range(8)]
        _vector_equal(projected, expected, 'native action/endpoint projection differs')


def _evaluate_view(value, oracle, view, model):
    if 'failure' in value:
        failure = value['failure']
        c.fields(failure, ('message', 'evidence_id'))
        raise ValueError('recorded native failure at ' + str(failure['evidence_id']) + ': ' + str(failure['message']))
    c.fields(value, ('receipts', 'beliefs', 'predictions', 'policies'))
    receipts = value['receipts']
    c.require(type(receipts) is list and len(receipts) == 3, 'three projection receipts required')
    for stage, receipt in enumerate(receipts):
        _validate_receipt(receipt, oracle, stage, view, model)
    c.require(len({row['frame_digest'] for row in receipts}) == 1, 'frame changed within trial')
    c.require(len({row['prefix_digest'] for row in receipts}) == 3 and
              len({name for row in receipts for name in row['entities']}) == 9,
              'fresh-instance prefixes or participants repeated')
    first, second, target = receipts
    after_first = posterior(UNIFORM, first['likelihood'], first['observed_endpoint'])
    expected_beliefs = {'reset': UNIFORM, 'first': after_first,
                       'latest': posterior(UNIFORM, second['likelihood'], second['observed_endpoint']),
                       'retained': posterior(after_first, second['likelihood'], second['observed_endpoint'])}
    c.fields(value['beliefs'], BELIEFS)
    c.fields(value['predictions'], BELIEFS)
    predictions = {}
    for name in BELIEFS:
        belief = _probabilities(value['beliefs'][name], 4)
        _vector_equal(belief, expected_beliefs[name], 'delivered-evidence posterior differs')
        prediction = value['predictions'][name]
        c.fields(prediction, ('endpoint_probabilities', 'action_probabilities', 'endpoint_action', 'physical_action'))
        endpoints = _probabilities(prediction['endpoint_probabilities'], 8)
        actions = _probabilities(prediction['action_probabilities'], 4)
        _vector_equal(endpoints, _mix(belief, target['likelihood']), 'target endpoint mixture differs')
        _vector_equal(actions, _mix(belief, target['action_probabilities']), 'target action mixture differs')
        _index(prediction['endpoint_action'], 8)
        _index(prediction['physical_action'], 4)
        c.require(prediction['endpoint_action'] == _argmax(endpoints) and
                  prediction['physical_action'] == _argmax(actions), 'MAP action differs')
        predictions[name] = _point(oracle['id'], endpoints, prediction['endpoint_action'],
                                   prediction['physical_action'], oracle, CONSUMED[name])
    c.require(type(value['policies']) is list and len(value['policies']) == 6, 'policy inventory differs')
    policies = {}
    for policy in value['policies']:
        c.fields(policy, ('prior', 'fee_index', 'fee', 'action', 'ask', 'value', 'expected_before',
                          'expected_after', 'posterior', 'endpoint_probabilities',
                          'target_selected_endpoint', 'consumed_ids'))
        name, fee_index = policy['prior'], _index(policy['fee_index'], 3)
        key = (name, fee_index)
        c.require(name in ('retained', 'reset') and key not in policies, 'duplicate or unknown policy')
        fee = FEES[fee_index]
        c.require(policy['fee'] is None if fee is None else
                  type(policy['fee']) in (int, float) and policy['fee'] == fee, 'query fee differs')
        prior = after_first if name == 'retained' else UNIFORM
        decision = choose(prior, second['likelihood'], target['likelihood'], fee)
        _index(policy['action'], 8)
        c.require(type(policy['ask']) is bool and policy['ask'] == decision['ask'] and
                  policy['action'] == decision['action'], 'pre-observation query decision differs')
        for field in ('value', 'expected_before', 'expected_after'):
            _equal(policy[field], decision[field], 'pre-observation expected value differs')
        final = posterior(prior, second['likelihood'], second['observed_endpoint']) if policy['ask'] else prior
        _vector_equal(_probabilities(policy['posterior'], 4), final, 'query branch posterior differs')
        endpoint_probabilities = _probabilities(policy['endpoint_probabilities'], 8)
        _vector_equal(endpoint_probabilities, _mix(final, target['likelihood']), 'query target mixture differs')
        selected = _index(policy['target_selected_endpoint'], 8)
        c.require(selected == _argmax(endpoint_probabilities), 'query target MAP differs')
        consumed = [first['evidence_id']] if name == 'retained' else []
        if policy['ask']:
            consumed.append(second['evidence_id'])
        c.require(policy['consumed_ids'] == consumed, 'query branch evidence custody differs')
        correct = selected == oracle['endpoints'][2]
        paid = fee if policy['ask'] else 0.
        policies[key] = {'id': oracle['id'], 'ask': policy['ask'], 'correct': correct,
                         'gross': int(correct), 'fee_paid': paid, 'net': int(correct) - paid}
    return predictions, policies


def _validate_shard(shard, source_info):
    c.fields(shard, ('version', 'protocol_commit', 'protocol_sha256', 'source_commit', 'source_sha256',
                     'inputs_sha256', 'seed', 'law', 'model', 'checks', 'trials'))
    c.require(shard['version'] == 'coordinate-transport-raw-v1' and
              shard['protocol_commit'] == PROTOCOL_COMMIT and shard['protocol_sha256'] == PROTOCOL_SHA256,
              'raw version or prospective protocol differs')
    c.require(type(shard['seed']) is int and shard['seed'] in SEEDS and shard['law'] in LAWS,
              'unregistered law or model seed')
    commit = shard['source_commit']
    c.require(type(commit) is str and len(commit) == 40 and all(v in '0123456789abcdef' for v in commit),
              'invalid source commit')
    sources = shard['source_sha256']
    c.require(type(sources) is dict and 'coordinate_transport_scoring_v1.py' in sources and
              all(type(key) is str and c.is_sha(value) for key, value in sources.items()) and
              c.is_sha(shard['inputs_sha256']), 'invalid source or input fingerprints')
    if source_info is not None:
        c.require(type(source_info) is dict, 'source info must be a mapping')
        for name in ('protocol_commit', 'protocol_sha256', 'source_sha256'):
            c.require(source_info.get(name) == shard[name], 'scoring and collection sources differ')
    model = shard['model']
    c.fields(model, ('seed', 'law', 'training_sha256', 'freeze_sha256', 'checkpoint_sha256',
                     'language_sha256', 'registry_sha256', 'world_sha256', 'new_ids'))
    c.require(type(model['seed']) is int and model['seed'] == shard['seed'] and model['law'] == shard['law'] and
              model['training_sha256'] == TRAINING_SHA256, 'restored model identity differs')
    for name in ('freeze_sha256', 'checkpoint_sha256', 'language_sha256', 'registry_sha256', 'world_sha256'):
        c.require(c.is_sha(model[name]), 'invalid model fingerprint')
    c.require(type(model['new_ids']) is list and len(model['new_ids']) == 2 and
              set(model['new_ids']) == {sha256(word.encode()).hexdigest() for word in WORDS},
              'acquired lexical identity inventory differs')
    c.fields(shard['checks'], VIEWS)
    for check in shard['checks'].values():
        c.fields(check, ('records', 'endpoint_complement_checks', 'projection_checks',
                         'uniform_hypothesis_checks', 'maximum_projection_error', 'maximum_uniform_error',
                         'language_unchanged', 'world_unchanged'))
        for name in ('records', 'endpoint_complement_checks', 'projection_checks', 'uniform_hypothesis_checks'):
            expected = 9216 if name == 'projection_checks' else 2304
            c.require(type(check[name]) is int and check[name] == expected, 'native check inventory differs')
        for name in ('maximum_projection_error', 'maximum_uniform_error'):
            c.require(0 <= _number(check[name]) <= TOLERANCE, 'native projection invariant failed')
        c.require(check['language_unchanged'] is True and check['world_unchanged'] is True,
                  'frozen native model changed')
    c.require(type(shard['trials']) is list and len(shard['trials']) == 768, 'raw trial count differs')


def _key(*parts):
    return '/'.join(map(str, parts))


def _loss_change(left, right):
    if left is None or right is None:
        status = 'left_infinite' if left is None else 'right_infinite'
        if left is None and right is None:
            status = 'both_infinite'
        return {'change': None, 'status': status}
    return {'change': left - right, 'status': 'finite'}


def _paired_predictions(left, right):
    other = {row['id']: row for row in right}
    c.require(len(other) == len(right) == len(left) and set(other) == {row['id'] for row in left},
              'paired prediction inventory differs')
    records = []
    for row in left:
        baseline = other[row['id']]
        records.append({'id': row['id'], 'brier_change': row['brier'] - baseline['brier'],
                        'nll': _loss_change(row['nll'], baseline['nll']),
                        'oracle_kl': _loss_change(row['oracle_kl'], baseline['oracle_kl']),
                        'endpoint_correct_change': int(row['endpoint_correct']) - int(baseline['endpoint_correct']),
                        'action_correct_change': int(row['action_correct']) - int(baseline['action_correct']),
                        'left_high_confidence_wrong': row['high_confidence_wrong'],
                        'right_high_confidence_wrong': baseline['high_confidence_wrong']})
    return {'count': len(records), 'mean_brier_change': fsum(row['brier_change'] for row in records) / len(records),
            'endpoint_repairs': sum(row['endpoint_correct_change'] > 0 for row in records),
            'endpoint_regressions': sum(row['endpoint_correct_change'] < 0 for row in records),
            'action_repairs': sum(row['action_correct_change'] > 0 for row in records),
            'action_regressions': sum(row['action_correct_change'] < 0 for row in records),
            'brier_worse_count': sum(row['brier_change'] > TOLERANCE for row in records), 'records': records}


def _paired_policies(left, right):
    other = {row['id']: row for row in right}
    c.require(len(other) == len(right) == len(left) and set(other) == {row['id'] for row in left},
              'paired policy inventory differs')
    records = [{'id': row['id'], 'purchase_change': int(row['ask']) - int(other[row['id']]['ask']),
                'gross_change': row['gross'] - other[row['id']]['gross'],
                'fee_change': row['fee_paid'] - other[row['id']]['fee_paid'],
                'net_change': row['net'] - other[row['id']]['net']} for row in left]
    return {'count': len(records), 'mean_net_change': fsum(row['net_change'] for row in records) / len(records),
            'net_worse_count': sum(row['net_change'] < -TOLERANCE for row in records), 'records': records}


def _gates(metrics, policy_metrics):
    conditions = {}
    for law, seed in product(LAWS, SEEDS):
        retained = metrics.get(_key(law, seed, 'intact', 'retained'))
        complete = retained is not None and retained['count'] == 768
        gates = {'intact_retained_count': complete,
                 'endpoint_accuracy_at_least_095': complete and retained['endpoint_accuracy'] >= .95,
                 'action_accuracy_at_least_095': complete and retained['action_accuracy'] >= .95,
                 'zero_high_confidence_wrong': complete and retained['high_confidence_wrong'] == 0}
        for view, belief in (('intact', 'reset'), ('intact', 'latest'), ('zero_layout', 'retained')):
            baseline = metrics.get(_key(law, seed, view, belief))
            gates['brier_improves_over_' + view + '_' + belief] = bool(
                complete and baseline is not None and baseline['count'] == 768 and
                baseline['mean_brier'] - retained['mean_brier'] > TOLERANCE)
        first = policy_metrics.get(_key(law, seed, 'intact', 'retained', 0))
        reset = policy_metrics.get(_key(law, seed, 'intact', 'reset', 0))
        gates['cheap_retained_net_at_least_reset'] = bool(first is not None and reset is not None and
            first['count'] == reset['count'] == 768 and first['mean_net'] >= reset['mean_net'] - TOLERANCE)
        conditions[_key(law, seed)] = gates
    return conditions


def score(raw_shards, evaluator, *, source_info=None, collection_failures=()):
    """Evaluate sealed raw records. File publication and hashes are checked by the runner.

    A null loss with its explicit infinite status denotes a genuine zero-probability
    failure. The evaluator never clips probability tails or pools acceptance gates.
    Collection failures are retained alongside scored failures and require revision.
    """
    errors, predictions, policies = [], {}, {}
    if type(collection_failures) not in (list, tuple):
        errors.append({'location': 'collection', 'message': 'collection failures must be a sequence'})
    else:
        for index, failure in enumerate(collection_failures):
            location = _key('collection', index)
            try:
                c.require(type(failure) is dict and bool(failure), 'invalid collection failure record')
                c.digest(failure)
                errors.append({'location': location, 'message': str(failure.get('message', 'collection reported failure')),
                               'collection_failure': dict(failure)})
            except (ValueError, TypeError, OverflowError) as error:
                errors.append({'location': location, 'message': str(error)})
    public_receipts, fresh_entities, seen_shards, fresh_prefixes = {}, set(), set(), set()
    sources, models = None, {}
    try:
        oracle = _validate_oracle(evaluator)
    except (ValueError, TypeError, KeyError, IndexError, OverflowError) as error:
        oracle = {}
        errors.append({'location': 'evaluator', 'message': str(error)})
    if type(raw_shards) not in (list, tuple) or len(raw_shards) != 10:
        errors.append({'location': 'raw', 'message': 'exactly ten law/seed shards required'})
    for shard_index, shard in enumerate(raw_shards if type(raw_shards) in (list, tuple) else []):
        location = 'shard/' + str(shard_index)
        try:
            _validate_shard(shard, source_info)
            law, seed = shard['law'], shard['seed']
            location = _key(law, seed)
            c.require((law, seed) not in seen_shards, 'duplicate law/seed shard')
            seen_shards.add((law, seed))
            header = {name: shard[name] for name in ('protocol_commit', 'protocol_sha256', 'source_commit',
                                                    'source_sha256', 'inputs_sha256')}
            if sources is None:
                sources = header
            c.require(header == sources, 'raw source or observed-bank custody differs across shards')
            model = shard['model']
            language = {name: model[name] for name in ('training_sha256', 'freeze_sha256',
                                                       'checkpoint_sha256', 'language_sha256', 'registry_sha256', 'new_ids')}
            c.require(seed not in models or models[seed] == language, 'language changed between physical laws')
            if models:
                common_model = next(iter(models.values()))
                c.require(all(language[name] == common_model[name] for name in
                              ('training_sha256', 'freeze_sha256', 'registry_sha256', 'new_ids')),
                          'training or lexical registry changed between seeds')
            models[seed] = language
            identities = [row['id'] for row in shard['trials']]
            expected = {identity for identity, row in oracle.items() if row['law'] == law}
            c.require(len(set(identities)) == 768 and set(identities) == expected,
                      'raw/evaluator trial inventory differs')
        except (ValueError, TypeError, KeyError, IndexError, OverflowError) as error:
            errors.append({'location': location, 'message': str(error)})
            continue
        for trial in shard['trials']:
            identity = trial['id']
            try:
                c.fields(trial, ('id', 'views'))
                c.fields(trial['views'], VIEWS)
            except (ValueError, TypeError, KeyError, IndexError, OverflowError) as error:
                errors.append({'location': _key(law, seed, identity), 'message': str(error)})
                continue
            native = None
            for view in VIEWS:
                try:
                    value = trial['views'][view]
                    forecast_rows, policy_rows = _evaluate_view(value, oracle[identity], view, model)
                    common = [{name: row[name] for name in ('evidence_id', 'prefix_digest', 'entities',
                              'actions', 'endpoint_encoding')} | ({'observed_endpoint': row['observed_endpoint']}
                              if stage < 2 else {}) for stage, row in enumerate(value['receipts'])]
                    if identity in public_receipts:
                        c.require(common == public_receipts[identity], 'common observed instance tape differs')
                    else:
                        entities = {name for row in common for name in row['entities']}
                        prefixes = {row['prefix_digest'] for row in common}
                        c.require(not entities & fresh_entities and not prefixes & fresh_prefixes,
                                  'public participant or prefix repeated across trials')
                        fresh_entities.update(entities)
                        fresh_prefixes.update(prefixes)
                        public_receipts[identity] = common
                    current_native = [row['native_likelihood'] for row in value['receipts']]
                    if native is None:
                        native = current_native
                    c.require(current_native == native, 'physical forecast changed across mapping interventions')
                    for belief, row in forecast_rows.items():
                        predictions.setdefault(_key(law, seed, view, belief), []).append(row)
                    for (prior, fee_index), row in policy_rows.items():
                        policies.setdefault(_key(law, seed, view, prior, fee_index), []).append(row)
                except (ValueError, TypeError, KeyError, IndexError, OverflowError) as error:
                    errors.append({'location': _key(law, seed, identity, view), 'message': str(error)})
    if seen_shards != set(product(LAWS, SEEDS)):
        errors.append({'location': 'raw', 'message': 'complete unique law/seed inventory required'})
    if len(public_receipts) != 1536 or len(fresh_entities) != 13824 or len(fresh_prefixes) != 4608:
        errors.append({'location': 'raw', 'message': 'complete fresh trial/participant inventory required'})
    metrics = {key: _prediction_summary(rows) for key, rows in predictions.items()}
    policy_metrics = {key: _policy_summary(rows) for key, rows in policies.items()}
    paired_predictions, paired_policies = {}, {}
    for law, seed in product(LAWS, SEEDS):
        left = _key(law, seed, 'intact', 'retained')
        for view, belief in (('intact', 'reset'), ('intact', 'first'), ('intact', 'latest'),
                             ('zero_layout', 'retained'), ('cycled_layout', 'retained')):
            right = _key(law, seed, view, belief)
            if left in predictions and right in predictions:
                try:
                    paired_predictions[_key(law, seed, 'retained_minus', view, belief)] = _paired_predictions(
                        predictions[left], predictions[right])
                except ValueError as error:
                    errors.append({'location': right, 'message': str(error)})
        for view, fee_index in product(VIEWS, range(3)):
            retained_key, reset_key = _key(law, seed, view, 'retained', fee_index), _key(law, seed, view, 'reset', fee_index)
            if retained_key in policies and reset_key in policies:
                try:
                    paired_policies[_key(law, seed, view, fee_index)] = _paired_policies(
                        policies[retained_key], policies[reset_key])
                except ValueError as error:
                    errors.append({'location': retained_key, 'message': str(error)})
    counts = {'raw_shards': len(seen_shards), 'oracle_trials': len(oracle),
              'observed_trials': len(public_receipts), 'unique_entities': len(fresh_entities),
              'unique_prefixes': len(fresh_prefixes),
              'collection_failures': len(collection_failures) if type(collection_failures) in (list, tuple) else 1,
              'predictions': sum(map(len, predictions.values())), 'policies': sum(map(len, policies.values()))}
    counts['projection_receipts'] = counts['predictions'] // 4 * 3
    if counts['predictions'] != 92160 or counts['policies'] != 138240:
        errors.append({'location': 'scores', 'message': 'full prediction/policy inventory required'})
    conditions = _gates(metrics, policy_metrics)
    failed_gates = [{'condition': condition, 'gate': name} for condition, gates in conditions.items()
                    for name, passed in gates.items() if not passed]
    passed = not errors and not failed_gates
    return {'version': VERSION, 'decision': 'KEEP_TRANSPORT_PREFLIGHT' if passed else 'REVISE_TRANSPORT_PREFLIGHT',
            'sources': sources, 'source_info': source_info, 'counts': counts, 'validation_errors': errors,
            'condition_gates': conditions, 'failed_gates': failed_gates, 'metrics': metrics,
            'policy_metrics': policy_metrics, 'prediction_records': predictions, 'policy_records': policies,
            'paired_predictions': paired_predictions, 'paired_policies': paired_policies}
