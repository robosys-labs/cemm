"""TRAIN-only physical receipt interface declared before execution at 1a4737f."""
from copy import deepcopy
from itertools import combinations
import json
import platform

import torch

from . import acceptance_contract as c, continuation_run as io
from .effect_role_model import action_candidates, pack
from .effect_role_run import world_for
from .g3_train_coordinate_intervention import read_locked
from .joint_objective import fingerprint, require

TRAIN_SHA = '766a8315d66e4a0bfca0079183d3966fbc7a0b4ed65c98177650d245a10671ed'
PAIRS = tuple(combinations(range(4), 2))


def prefix_digest(record):
    return c.digest({'entities': record['entities'], 'anchor': record['anchor'],
                     'context': record['context'], 'utterance': record['utterances'][0]['text']})


@torch.no_grad()
def measure(seed, freeze, teach, registry):
    world = world_for(freeze, 'nand', seed)
    initial = fingerprint(world.state_dict())
    revised = deepcopy(teach)
    for record in revised['episodes']:
        require(len(record['utterances']) == 1, 'preflight requires one endpoint per episode')
        event = record['utterances'][0]
        event['reading'] = [1 - bit for bit in event['reading']]
    original, changed = pack(teach, world, registry), pack(revised, world, registry)
    rows = []
    for group, other in zip(original, changed, strict=True):
        require(len(group['events']) == len(other['events']) == 1, 'event inventory changed')
        event, altered = group['events'][0], other['events'][0]
        require(torch.equal(group['state'], other['state']) and all(
            torch.equal(event[key], altered[key]) for key in ('features', 'mentions', 'likelihood')),
            'current endpoint leaked into a forecast input')
        actions = action_candidates(event['mentions'])
        require(torch.equal(actions, action_candidates(altered['mentions'])), 'endpoint changed candidate actions')
        probabilities = (event['likelihood'] + group['state'][:, None, :, None]).logsumexp(2).exp()
        require(bool(probabilities.isfinite().all()) and bool((probabilities >= 0).all()) and
                bool((probabilities.sum(-1) - 1).abs().le(1e-10).all()), 'invalid endpoint distribution')
        for index, (record, counterfactual) in enumerate(zip(group['records'], other['records'], strict=True)):
            require(record['id'] == counterfactual['id'] and
                    prefix_digest(record) == prefix_digest(counterfactual) and
                    record['utterances'][0]['reading'] != counterfactual['utterances'][0]['reading'],
                    'endpoint intervention changed the public prefix or was a no-op')
            predicted = probabilities[index]
            target = int(event['target'][index])
            likelihood = predicted[:, target]
            require(bool(likelihood.isfinite().all()) and likelihood.sum().item() > 0,
                    'invalid observed endpoint likelihood')
            distances = [(predicted[a] - predicted[b]).abs().sum().item() / 2 for a, b in PAIRS]
            rows.append({'episode_id': record['id'], 'evidence_id': record['id'] + '/utterance/0',
                         'prefix_digest': prefix_digest(record), 'actions': actions[index].tolist(),
                         'endpoint_probabilities': predicted.tolist(),
                         'observed_endpoint': record['utterances'][0]['reading'],
                         'observed_likelihoods': likelihood.tolist(),
                         'uniform_action_posterior': (likelihood / likelihood.sum()).tolist(),
                         'pairwise_tv': distances,
                         'numerically_equal_pairs': [list(pair) for pair, distance in zip(PAIRS, distances)
                                                     if distance <= 1e-10]})
    require(len(rows) == 16 and {row['episode_id'] for row in rows} ==
            {record['id'] for record in teach['episodes']}, 'missing or duplicate TRAIN evidence')
    require(fingerprint(world.state_dict()) == initial, 'frozen native world mutated')
    return {'world_sha256': initial, 'rows': rows,
            'rows_with_numerically_equal_candidates': sum(bool(row['numerically_equal_pairs']) for row in rows),
            'endpoint_complement_invariant': True}


def run():
    torch.set_num_threads(1)
    data = io.ROOT / 'data/effect-role-v3'
    training = read_locked(io.ROOT / 'data/effect-role-fit-v3/training.json', TRAIN_SHA)
    freeze = read_locked(data / 'freeze.json', training['freeze_sha256'])
    teach = read_locked(data / 'teach-inputs.json.xz', freeze['artifacts']['teach-inputs.json.xz']['sha256'])
    registry = read_locked(data / 'lexical-registry.json', freeze['artifacts']['lexical-registry.json']['sha256'])
    require(len(teach['episodes']) == len({row['id'] for row in teach['episodes']}) == 16,
            'invalid complete teaching tape')
    return {'protocol_commit': '1a4737f',
            'protocol_sha256': io._hash(io.ROOT / 'G3_G5_RECEIPT_PREFLIGHT.md'),
            'scope': 'G3 v3 observed TRAIN endpoints, event-local candidate indices',
            'python': platform.python_version(), 'torch': torch.__version__,
            'law': 'nand', 'teaching_rows': 16, 'pair_order': PAIRS, 'numerical_tv_tolerance': 1e-10,
            'seeds': {seed: measure(seed, freeze, teach, registry) for seed in (7, 11, 23, 37, 53)}}


if __name__ == '__main__':
    print(json.dumps(run(), sort_keys=True, separators=(',', ':'), allow_nan=False))
