"""Full-world empirical controls from measured histories, not simulator rules.

An unseen context abstains. Zeros remain zero; no smoothing, oracle lookup,
learned-model fallback or supplied persistence is hidden in these controls.
"""
from collections import Counter, defaultdict
from hashlib import sha256
import json
import math

import torch

from .joint_objective import WORLDS


def queries(batch):
    """Yield ONLY current inputs and prior feedback, never the current target.

    Materialized arrays remain evaluator-inspectable; this is causal ordering,
    not process isolation. The current post-action reading joins the NEXT past.
    """
    batch.validate()
    x, a = batch.observations.to(dtype=torch.long).tolist(), batch.actions.tolist()
    for episode in range(len(a[0])):
        past = ()
        for t in range(len(a)):
            pre, action = tuple(x[t][episode]), tuple(a[t][episode])
            yield t, episode, pre, action, past
            past += ((pre, action, tuple(x[t + 1][episode])),)


def context(pre, action, past, mode):
    """Context and output coordinate order for empirical controls.

    'contact' supplies a deliberately strong abstraction: prior ordered-pair
    contact observations transfer across identity/topology; intervening actions
    are omitted except through current measured state. No latent-mode labels,
    physics formulas or supplied persistence enter its full-world outcome table.
    """
    if mode == 'prefix':
        return (pre, action, past), (0, 1, 2)
    if mode not in ('local', 'contact'):
        raise ValueError('unknown context mode')
    kind, first, second, value = action
    participants = tuple(i for i in (first, second) if i >= 0)
    order = participants + tuple(i for i in range(3) if i not in participants)
    signatures = tuple((tuple(before[i] for i in act[1:3]), tuple(after[i] for i in act[1:3]))
                       for before, act, after in past if act[0] == 0) if mode == 'contact' else ()
    return (kind, value, tuple(pre[i] for i in order), signatures), order


class SensorMemory:
    def __init__(self, mode):
        if mode not in ('prefix', 'local', 'contact'):
            raise ValueError('unknown memory mode')
        self.mode, self.table = mode, {}

    def fit(self, batch):
        table = defaultdict(Counter)
        targets = batch.observations[1:].tolist()
        for t, e, pre, action, past in queries(batch):
            key, order = context(pre, action, past, self.mode)
            post = tuple(int(targets[t][e][i]) for i in order)
            table[key][post] += 1
        self.table = dict(table)
        return self

    def predict(self, pre, action, past):
        key, order = context(pre, action, past, self.mode)
        counts = self.table.get(key)
        if counts is None:
            return None
        total, result = sum(counts.values()), [0.0] * 8
        for canonical, count in counts.items():
            world = [0] * 3
            for index, slot in enumerate(order):
                world[slot] = canonical[index]
            result[WORLDS.index(tuple(world))] = count / total
        if abs(math.fsum(result) - 1.0) > 1e-12:
            raise ValueError('invalid empirical distribution')
        return tuple(result)

    def digest(self):
        records = [[key, sorted(counts.items())] for key, counts in sorted(self.table.items())]
        return sha256(json.dumps([self.mode, records], separators=(',', ':'), allow_nan=False).encode()).hexdigest()
