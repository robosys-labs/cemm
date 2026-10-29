"""Supplied finite-path inference for frozen models; no physics or evaluator import.

Missing values stay -1. Each branch is a hypothesis, not an observed reading.
No sampling/pruning or merging of distinct recurrent states; bound excess fails.
"""
from dataclasses import dataclass
from itertools import product
import math

import numpy as np
import torch

from . import comparison_scoring as scores
from .comparison_run import emit, _array_record

WORLDS = tuple(product((0, 1), repeat=3))


@dataclass(frozen=True)
class MaskedTrace:
    readings: torch.Tensor
    masks: torch.Tensor
    actions: torch.Tensor

    def validate(self):
        x, mask, a = self.readings, self.masks, self.actions
        scores.require(x.dtype == torch.float64 and mask.dtype == torch.bool and a.dtype == torch.long
                       and all(v.device.type == 'cpu' for v in (x, mask, a)), 'CPU trace dtypes')
        scores.require(a.ndim == x.ndim == 3 and a.shape[2] == 4 and x.shape[2] == 3 and
                       x.shape == mask.shape and x.shape[:2] == (len(a) + 1, a.shape[1]) and
                       a.shape[0] > 0 and a.shape[1] > 0, 'trace shape')
        scores.require(bool(mask[0].all()) and bool(((x[mask] == 0) | (x[mask] == 1)).all())
                       and bool((x[~mask] == -1).all()), 'hidden readings must be -1, full anchor required')
        k, p, q, v = a.unbind(-1)
        legal = ((k == 0) & (p >= 0) & (p < 3) & (q >= 0) & (q < 3) & (p != q) & (v == -1))
        legal |= (k == 1) & (p >= 0) & (p < 3) & (q == -1) & ((v == 0) | (v == 1))
        legal |= (k == 2) & (p == -1) & (q == -1) & (v == -1)
        scores.require(bool(legal.all()), 'invalid trace action')
        return self

    def digest(self):
        from .joint_objective import fingerprint
        return fingerprint({'readings': self.readings, 'masks': self.masks, 'actions': self.actions})


class NeuralPaths:
    """Exact mixture over hypothetical histories under an unchanged predictor."""
    def __init__(self, model, anchor, limit=64):
        self.model, self.limit = model, limit
        self.bits = anchor[:, None, :].clone()
        self.state = model.initial(len(anchor))[:, None, :]
        self.weight = torch.zeros(len(anchor), 1, dtype=torch.float64)
        self.worlds = torch.tensor(WORLDS, dtype=torch.float64)
        self.diagnostic = {}

    def predict(self, action):
        n, paths = self.weight.shape
        a = action[:, None, :].expand(-1, paths, -1).reshape(-1, 4)
        raw, pending = self.model.predict(self.bits.reshape(-1, 3), a, self.state.flatten(0, 1))
        normalized, correction = scores.normalize(raw, np.ones(len(raw), dtype=bool))
        conditional = torch.from_numpy(normalized).reshape(n, paths, 8)
        self.pending, self.conditional = pending, conditional
        result = (self.weight[:, :, None] + conditional).logsumexp(1)
        self.diagnostic = {'represented_paths': paths, 'max_abs_conditional_log_correction':
                           float(np.abs(correction).max())}
        return result, np.ones(n, dtype=bool)

    def receive(self, reading, mask):
        n, paths = self.weight.shape
        compatible = ((self.worlds[None] == reading[:, None, :]) | ~mask[:, None, :]).all(-1)
        counts = compatible.sum(-1)
        scores.require(bool((counts == counts[0]).all()), 'batch needs equal missing-bit counts')
        candidates = int(counts[0])
        scores.require(paths * candidates <= self.limit, 'path bound exceeded; no pruning allowed')
        indices = compatible.nonzero()[:, 1].reshape(n, candidates)
        selected = self.conditional.gather(2, indices[:, None, :].expand(-1, paths, -1))
        weight = (self.weight[:, :, None] + selected).reshape(n, -1)
        evidence = weight.logsumexp(-1, keepdim=True)
        scores.require(bool(torch.isfinite(evidence).all()), 'visible evidence outside model support')
        bits = self.worlds[indices][:, None].expand(-1, paths, -1, -1).reshape(n, -1, 3)
        # Never call receive on an exact-zero hypothetical branch.
        alive = torch.isfinite(weight).flatten()
        fathers = torch.arange(n * paths).reshape(n, paths, 1).expand(-1, -1, candidates).flatten()
        next_state = self.model.initial(n * paths * candidates)
        next_state[alive] = self.model.receive(self.pending[fathers[alive]], bits.reshape(-1, 3)[alive])
        self.bits, self.state = bits, next_state.reshape(n, paths * candidates, -1)
        self.weight = weight - evidence


class EmpiricalPaths:
    """Same marginalization for count tables; unsupported mass causes abstention."""
    def __init__(self, memory, anchor, *, first_contact=False, limit=64):
        self.memory, self.first_contact, self.limit = memory, first_contact, limit
        self.paths = [[(1., tuple(map(int, bits)), ())] for bits in anchor.tolist()]
        self.diagnostic = {}

    def predict(self, action):
        raw = torch.full((len(self.paths), 8), -torch.inf, dtype=torch.float64)
        answered, expansions, missing = [], [], 0
        for paths, a in zip(self.paths, action.tolist(), strict=True):
            a, expanded, total = tuple(a), [], [0.] * 8
            supported = bool(paths)
            for weight, pre, past in paths:
                context = past
                if self.first_contact:
                    contacts = tuple(row for row in past if row[1][0] == 0)
                    context = contacts[:1]
                probabilities = self.memory.predict(pre, a, context)
                if probabilities is None:
                    missing += 1
                    supported = False
                    break  # Cannot discard unknown mass and renormalize the rest.
                for world, probability in zip(WORLDS, probabilities, strict=True):
                    if probability > 0:
                        mass = weight * probability
                        scores.require(mass > 0, 'empirical path underflow')
                        expanded.append((mass, world, past + ((pre, a, world),)))
                        total[WORLDS.index(world)] += mass
            answered.append(supported)
            expansions.append(expanded if supported else [])
            if supported:
                raw[len(answered) - 1] = torch.tensor(total, dtype=torch.float64).log()
        self.expansions = expansions
        self.diagnostic = {'unsupported_positive_paths': missing,
                           'represented_paths_max': max(map(len, self.paths), default=0)}
        return raw, np.array(answered, dtype=bool)

    def receive(self, reading, mask):
        result = []
        for paths, x, visible in zip(self.expansions, reading.tolist(), mask.tolist(), strict=True):
            selected = [(w, bits, past) for w, bits, past in paths if
                        all(not show or bit == value for bit, value, show in zip(bits, x, visible))]
            scores.require(not paths or bool(selected), 'visible evidence outside empirical support')
            scores.require(len(selected) <= self.limit, 'empirical path bound exceeded')
            mass = math.fsum(w for w, _, _ in selected)
            result.append([(w / mass, bits, past) for w, bits, past in selected])
        self.paths = result


class LastObserved:
    """Explicitly supplied last-reading persistence baseline, not observed truth."""
    def __init__(self, anchor):
        self.bits, self.diagnostic = anchor.clone(), {}

    def predict(self, action):
        indices = (self.bits.long() * torch.tensor([4, 2, 1])).sum(-1)
        raw = torch.full((len(indices), 8), -torch.inf, dtype=torch.float64)
        raw[torch.arange(len(indices)), indices] = 0.
        return raw, np.ones(len(indices), dtype=bool)

    def receive(self, reading, mask):
        self.bits = torch.where(mask, reading, self.bits)


def replay(trace, stream, *, model=None, memory=None, first_contact=False, no_change=False):
    """No oracle argument. Flush forecasts before accessing their own feedback."""
    from .joint_objective import fingerprint
    trace.validate()
    scores.require(sum((model is not None, memory is not None, no_change)) == 1, 'one predictor required')
    before = trace.digest()
    weights = fingerprint(model.state_dict()) if model is not None else None
    table = memory.digest() if memory is not None else None
    if model is not None:
        model.eval()
    raw_all, norms, answers, offsets, diagnostics = [], [], [], [], []
    with torch.inference_mode():
        filter_ = (NeuralPaths(model, trace.readings[0]) if model is not None else
                   EmpiricalPaths(memory, trace.readings[0], first_contact=first_contact)
                   if memory is not None else LastObserved(trace.readings[0]))
        for t, action in enumerate(trace.actions):
            raw, answered = filter_.predict(action.clone())
            raw = raw.clone()
            emit(stream, {'kind': 'raw_forecast', 'step': t, 'raw_log': _array_record(raw),
                          'answered': answered.tolist(), 'filter': filter_.diagnostic})
            norm, offset = scores.normalize(raw, answered)
            emit(stream, {'kind': 'normalized_forecast', 'step': t, 'log': scores.log_record(norm),
                          'subtracted_log_mass': offset.tolist()})
            raw_all.append(raw.numpy().copy()); norms.append(norm); answers.append(answered)
            offsets.append(offset); diagnostics.append(dict(filter_.diagnostic))
            # ONLY delivered values, with -1 at every absent reading.
            filter_.receive(trace.readings[t + 1].clone(), trace.masks[t + 1].clone())
    scores.require(trace.digest() == before, 'replay mutated sensor history')
    scores.require(model is None or fingerprint(model.state_dict()) == weights, 'replay mutated weights')
    scores.require(memory is None or memory.digest() == table, 'replay mutated memory table')
    return np.stack(raw_all), np.stack(norms), np.stack(answers), np.stack(offsets), diagnostics
