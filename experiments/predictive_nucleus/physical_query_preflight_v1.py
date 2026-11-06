"""Descriptive TRAIN qualification under PHYSICAL_QUERY_PREFLIGHT_V1.md."""
from collections import Counter, defaultdict
from itertools import permutations
import json
from math import fsum
import platform

import torch

from . import continuation_run as io
from .domain_contract import world_index
from .g3_train_coordinate_intervention import read_locked
from .joint_objective import require
from .physical_query_v1 import choose, posterior

FEES = (.05, .75, None)
GOALS = {'identify_menu': tuple(tuple(float(h == a) for a in range(4)) for h in range(4)),
         'indifferent': ((1.,) * 4,) * 4}


def observed_posterior(prior, row):
    endpoint = int(world_index(torch.tensor(row['observed_endpoint'])))
    likelihood = row['endpoint_probabilities']
    require([values[endpoint] for values in likelihood] == row['observed_likelihoods'],
            'observed endpoint differs from the sealed likelihood vector')
    return posterior(prior, likelihood, endpoint)


def exhaustive_value(prior, likelihood, rewards):
    prior = tuple(value / fsum(prior) for value in prior)
    likelihood = tuple(tuple(value / fsum(row) for value in row) for row in likelihood)
    expected = 0.
    for endpoint in range(len(likelihood[0])):
        joint = tuple(p * row[endpoint] for p, row in zip(prior, likelihood))
        mass = fsum(joint)
        if mass:
            updated = tuple(value / mass for value in joint)
            expected += mass * max(fsum(p * row[action] for p, row in zip(updated, rewards))
                                   for action in range(len(rewards[0])))
    return expected


def run():
    teaching = read_locked(io.ROOT / 'data/effect-role-v3/teach-inputs.json.xz',
                          '74fecfda5a3287e5109d31990b9c62b34c39d7694bfeae7a6c1b0c50a029770d')
    saved = read_locked(io.ROOT / 'results/g3-g5-receipt-preflight.json',
                       '90b8cc1d175efd11070c5549bceeba80154db30319faa30ba707852579df2363')
    source = {record['id']: record for record in teaching['episodes']}
    require(len(source) == 16 and set(saved['seeds']) == {'7', '11', '23', '37', '53'},
            'incomplete registered input')
    routes, counts = [], Counter()
    largest_enumeration_error = 0.
    for seed, report in saved['seeds'].items():
        require(len(report['rows']) == 16 and {row['episode_id'] for row in report['rows']} == set(source),
                'missing or duplicate native receipt')
        groups = defaultdict(list)
        for row in report['rows']:
            record = source[row['episode_id']]
            groups[(tuple(record['entities']), record['utterances'][0]['text'])].append(row)
        require(len(groups) == 8 and all(len(rows) == 2 for rows in groups.values()), 'unpaired exact utterance')
        for paired in groups.values():
            for warmup, query in permutations(paired):
                require(warmup['actions'] == query['actions'] and
                        warmup['evidence_id'] != query['evidence_id'] and
                        warmup['prefix_digest'] != query['prefix_digest'], 'unmatched or repeated physical evidence')
                priors = {'reset': (.25,) * 4, 'retained': observed_posterior((.25,) * 4, warmup)}
                policies, values = [], {}
                for prior_name, prior in priors.items():
                    for goal_name, rewards in GOALS.items():
                        likelihood = query['endpoint_probabilities']
                        explicit = exhaustive_value(prior, likelihood, rewards)
                        for fee_index, fee in enumerate(FEES):
                            decision = choose(prior, likelihood, rewards, fee)
                            error = abs(decision['expected_after'] - explicit)
                            largest_enumeration_error = max(largest_enumeration_error, error)
                            require(error <= 1e-12, 'query formula disagrees with exhaustive Bayesian enumeration')
                            # The actual query endpoint enters only after a paid decision.
                            updated = observed_posterior(prior, query) if decision['ask'] else None
                            policies.append({'prior': prior_name, 'goal': goal_name, 'fee_index': fee_index,
                                             **decision, 'observed_posterior': updated})
                            counts[f'{prior_name}/{goal_name}/{fee_index}'] += int(decision['ask'])
                            values[prior_name, goal_name] = decision['value']
                routes.append({'seed': int(seed), 'warmup_id': warmup['evidence_id'],
                               'query_id': query['evidence_id'],
                               'warmup_prefix_digest': warmup['prefix_digest'],
                               'query_prefix_digest': query['prefix_digest'],
                               'priors': priors, 'policies': policies,
                               'retained_minus_reset_value': {
                                   goal: values['retained', goal] - values['reset', goal] for goal in GOALS}})
    evaluations = sum(len(route['policies']) for route in routes)
    require(len(routes) == 80 and evaluations == 960, 'incomplete registered policy inventory')
    return {'protocol_commit': 'ae0924e',
            'protocol_sha256': io._hash(io.ROOT / 'PHYSICAL_QUERY_PREFLIGHT_V1.md'),
            'scope': 'Observed TRAIN, passive physical answer, expected event-local menu identification',
            'python': platform.python_version(), 'torch': torch.__version__,
            'warmup_fee': 0., 'fees': FEES, 'goals': GOALS, 'ordered_pairs': len(routes),
            'policy_evaluations': evaluations, 'largest_enumeration_error': largest_enumeration_error,
            'marginal_second_query_counts': dict(counts), 'routes': routes}


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True, separators=(',', ':'), allow_nan=False))
