"""Same-author, separately implemented transfer evaluator. No old simulator import.

Truth is separate from the delivered MaskedTrace. This is not independent
challenge custody; oracle distributions are evaluator diagnostics only.
"""
from itertools import permutations, product
import numpy as np
import torch
from .masked_replay import MaskedTrace

WORLDS = tuple(product((0, 1), repeat=3))
MAPPINGS = tuple(permutations(range(3)))
HANDLES = ('handle-29', 'node-503', 'unit-907')
TABLES = (((0, 0), (0, 1), (1, 1), (1, 0)),
          ((0, 0), (1, 1), (1, 0), (0, 1)))


def advance(bits, action, mode):
    state = list(bits)
    kind, a, b, value = action
    if kind == 0:
        state[a], state[b] = TABLES[mode][2 * bits[a] + bits[b]]
    elif kind == 1:
        state[a] = value
    elif kind != 2:
        raise ValueError('unknown evaluator action')
    return tuple(state)


def oracle_step(bits, action, mode):
    """Separate scalar arithmetic check, not model-side transition knowledge."""
    kind, a, b, value = action
    state = list(bits)
    if kind == 0:
        source, target = (a, b) if mode == 0 else (b, a)
        state[target] = (bits[target] + bits[source]) % 2
    elif kind == 1:
        state[a] = value
    return tuple(state)


def episode(case, family, policy):
    if type(case) is not int or not 0 <= case < 256 or family not in ('reordered', 'reversed') or \
            policy not in ('full', 'hidden_resets', 'hidden_probe'):
        raise ValueError('invalid transfer selection')
    initial = tuple((case >> i) & 1 for i in (7, 6, 5))
    mode, x, y, z, reverse = ((case >> i) & 1 for i in (4, 3, 2, 1, 0))
    probe, order, pair = ((0, 1), (2, 0, 1), (1, 2)) if family == 'reordered' else (
                          (1, 0), (2, 1, 0), (2, 0))
    target = (x, y, z)
    pair = pair[::-1] if reverse else pair
    actions = [(1, 0, -1, 1), (1, 1, -1, 1), (0, *probe, -1)]
    actions += [(1, slot, -1, target[slot]) for slot in order]
    actions += [(0, *pair, -1), (2, -1, -1, -1)]
    truth, masks = [initial], [[True] * 3 for _ in range(9)]
    for action in actions:
        truth.append(advance(truth[-1], action, mode))
    if policy == 'hidden_resets':
        masks[5] = masks[6] = [False, False, True]
    elif policy == 'hidden_probe':
        masks[3], masks[4] = [False] * 3, [False, False, True]
        masks[5] = [i in (2, actions[4][1]) for i in range(3)]
    readings = [[bit if present else -1 for bit, present in zip(row, mask)]
                for row, mask in zip(truth, masks)]
    states, weights, oracle = [initial, initial], [0.5, 0.5], []
    for t, action in enumerate(actions):
        states = [oracle_step(state, action, m) for m, state in enumerate(states)]
        probabilities = [0.] * 8
        for weight, state in zip(weights, states):
            probabilities[WORLDS.index(state)] += weight
        oracle.append(probabilities)
        weights = [weight if all(not present or bit == value for bit, value, present in
                   zip(state, readings[t + 1], masks[t + 1])) else 0. for weight, state in zip(weights, states)]
        total = sum(weights)
        if total == 0:
            raise ValueError('evaluator sensor/oracle disagreement')
        weights = [weight / total for weight in weights]
    return np.array(readings), np.array(masks), np.array(actions), np.array(truth), np.array(oracle)


def build(family, policy, cases=range(256)):
    readings, masks, actions, truth, oracle = [], [], [], [], []
    for case in cases:
        x, m, a, y, p = episode(case, family, policy)
        for mapping in MAPPINGS:
            inverse = np.argsort(mapping)
            event = a.copy()
            for col in (1, 2):
                for old, new in enumerate(mapping):
                    event[a[:, col] == old, col] = new
            probabilities = np.zeros_like(p)
            for old, bits in enumerate(WORLDS):
                probabilities[:, WORLDS.index(tuple(bits[i] for i in inverse))] = p[:, old]
            readings.append(x[:, inverse]); masks.append(m[:, inverse]); actions.append(event)
            truth.append(y[:, inverse]); oracle.append(probabilities)
    trace = MaskedTrace(torch.tensor(np.stack(readings, 1), dtype=torch.float64),
                        torch.tensor(np.stack(masks, 1), dtype=torch.bool),
                        torch.tensor(np.stack(actions, 1), dtype=torch.long)).validate()
    return trace, np.stack(truth, 1), np.stack(oracle, 1)
