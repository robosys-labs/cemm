"""Strict observed-input loading into the existing learner; no oracle or simulator."""
from collections import defaultdict

import torch

from .acceptance_contract import load_json, require, validate_inputs
from .active_learning import ObservedBatch


def as_batches(inputs, *, batch_size=32):
    """Group complete episodes by geometry, without padding or synthesizing targets.

    Groups sort by (entity count, action count); original order is preserved inside
    each group. Every arm must use this same frozen batching policy. A batch is
    an offline delivered tape, not permission to expose its future to inference.
    """
    data = validate_inputs(inputs)
    require(type(batch_size) is int and 1 <= batch_size <= 1024, 'invalid batch size')
    groups = defaultdict(list)
    for case in data['episodes']:
        groups[len(case['ids']), len(case['actions'])].append(case)
    result = []
    for (entities, steps), cases in sorted(groups.items()):
        for start in range(0, len(cases), batch_size):
            chunk = cases[start:start + batch_size]
            readings, actions, coverage = [], [], []
            for case in chunk:
                ids = sorted(case['ids'])
                readings.append([[(-1 if row[i] is None else row[i]) for i in ids]
                                 for row in case['observations']])
                encoded = []
                for action in case['actions']:
                    members = [ids.index(i) for i in action['participants']]
                    if action['kind'] == 'contact': encoded.append([0, *members, -1])
                    elif action['kind'] == 'set': encoded.append([1, members[0], -1, action['value']])
                    else: encoded.append([2, -1, -1, -1])
                actions.append(encoded)
                coverage.append([[i in row for i in ids] for row in case['coverage']])
            x = torch.tensor(readings, dtype=torch.float64).transpose(0, 1).contiguous()
            a = torch.tensor(actions, dtype=torch.long).transpose(0, 1).contiguous()
            c = torch.tensor(coverage, dtype=torch.bool).transpose(0, 1).contiguous()
            result.append(ObservedBatch(x, a, x != -1, c, tuple(case['episode'] for case in chunk)).validate())
    return tuple(result)


def load_batches(path, expected_sha256, *, batch_size=32):
    """Require exact file bytes and observed-only schema before tensor conversion."""
    return as_batches(load_json(path, expected_sha256), batch_size=batch_size)
