"""Versioned 3–6 entity coordinates, alias-aware evidence and empirical controls.

Identity aliasing is supplied structure, never a transition law. No simulator,
future target, smoothing, or learned-model fallback enters prediction here.
"""
from collections import Counter, defaultdict
from functools import lru_cache
from hashlib import sha256
from itertools import product
import json
import math

import torch

from .comparison_scoring import log_record, require
from .context_support import ObservedContextSupport


@lru_cache(maxsize=4, typed=True)
def binary_worlds(entities):
    require(type(entities) is int and 3 <= entities <= 6, 'entity count must be 3–6')
    return tuple(product((0, 1), repeat=entities))


def world_index(bits):
    require(isinstance(bits, torch.Tensor) and bits.ndim >= 1 and
            3 <= bits.shape[-1] <= 6 and bool(((bits == 0) | (bits == 1)).all()), 'invalid world bits')
    powers = 2 ** torch.arange(bits.shape[-1] - 1, -1, -1, device=bits.device, dtype=torch.long)
    return (bits.long() * powers).sum(-1)


def validate_anchor(anchor, limit):
    require(type(limit) is int and limit > 0, 'positive integer path limit required')
    require(isinstance(anchor, torch.Tensor) and anchor.device.type == 'cpu' and
            anchor.dtype == torch.float64 and anchor.ndim == 2 and
            3 <= anchor.shape[1] <= 6 and len(anchor) > 0 and
            bool(((anchor == 0) | (anchor == 1)).all()), 'invalid full anchor')
    return anchor.shape[1]


def validate_action(action, batch_size, entities, allow_self=True):
    binary_worlds(entities)
    require(type(batch_size) is int and batch_size > 0 and type(allow_self) is bool, 'invalid action scope')
    require(isinstance(action, torch.Tensor) and action.device.type == 'cpu' and
            action.dtype == torch.long and action.shape == (batch_size, 4), 'invalid action shape/dtype')
    kind, first, second, value = action.unbind(-1)
    valid = ((kind == 0) & (first >= 0) & (first < entities) & (second >= 0) &
             (second < entities) & (value == -1))
    if not allow_self:
        valid &= first != second
    valid |= (kind == 1) & (first >= 0) & (first < entities) & (second == -1) & ((value == 0) | (value == 1))
    valid |= (kind == 2) & (first == -1) & (second == -1) & (value == -1)
    require(bool(valid.all()), 'invalid action')


def validate_reading(reading, mask, batch_size, entities):
    binary_worlds(entities)
    require(type(batch_size) is int and batch_size > 0, 'invalid feedback batch size')
    require(isinstance(reading, torch.Tensor) and isinstance(mask, torch.Tensor) and
            reading.device.type == mask.device.type == 'cpu' and reading.dtype == torch.float64 and
            mask.dtype == torch.bool and reading.shape == mask.shape == (batch_size, entities),
            'invalid feedback shape/dtype')
    require(bool(((reading[mask] == 0) | (reading[mask] == 1)).all()) and
            bool((reading[~mask] == -1).all()), 'hidden values must be -1; visible values binary')


def safe_logsumexp(values, dim):
    """Exact zero support with zero derivative, avoiding logsumexp(all -inf)."""
    empty = torch.isneginf(values).all(dim, keepdim=True)
    safe = values.masked_fill(empty, 0.)
    return safe.logsumexp(dim).masked_fill(empty.squeeze(dim), -torch.inf)


def normalize_tensor(raw, answered):
    """Original tolerances and arithmetic, retaining the full autograd graph."""
    require(isinstance(raw, torch.Tensor) and raw.dtype == torch.float64 and raw.device.type == 'cpu'
            and raw.ndim == 2 and raw.shape[1] in (8, 16, 32, 64), 'expected CPU float64 world matrix')
    mask = torch.as_tensor(answered)
    require(mask.device.type == 'cpu' and mask.dtype == torch.bool and
            mask.shape == (len(raw),), 'invalid answered mask')
    active = raw[mask]
    require(not bool((torch.isnan(active) | torch.isposinf(active)).any()), 'invalid log values')
    total = active.logsumexp(-1)
    require(bool(torch.isfinite(total).all()) and bool((total.abs() <= 1e-10).all()),
            'raw log mass outside frozen tolerance')
    normalized = active - total[:, None]
    probabilities = normalized.exp()
    require(bool(torch.isfinite(probabilities).all()) and bool(((probabilities >= 0) &
            (probabilities <= 1)).all()) and bool(((probabilities.sum(-1) - 1).abs() <= 1e-12).all()),
            'invalid normalized probabilities')
    result = torch.full_like(raw, -torch.inf)
    result[mask] = normalized
    correction = torch.zeros(len(raw), dtype=torch.float64)
    correction[mask] = total
    return result, correction


def normalize(raw, answered):
    """Explicit detached NumPy boundary for the existing inference transport."""
    result, correction = normalize_tensor(raw, answered)
    return result.detach().numpy(), correction.detach().numpy()


def persistence_support(pre, action, worlds):
    """Supplied participant-locality mask; aliases address one physical entity."""
    entities = validate_anchor(pre, 1)
    validate_action(action, len(pre), entities)
    require(isinstance(worlds, torch.Tensor) and worlds.device.type == 'cpu' and
            worlds.shape == (2 ** entities, entities), 'world coordinate shape mismatch')
    kind, first, second, _ = action.unbind(-1)
    slots = torch.arange(entities)[None, :]
    active = ((kind != 2)[:, None] & (slots == first[:, None])) | (
              (kind == 0)[:, None] & (slots == second[:, None]))
    return ((worlds[None] == pre[:, None, :]) | active[:, None, :]).all(-1)


def _roles(participants):
    unique = tuple(dict.fromkeys(participants))
    return unique, tuple(unique.index(name) for name in participants)


def _bits(bits, entities, missing=False):
    bits = tuple(bits)
    require(len(bits) == entities and all(type(b) is int and b in ((-1, 0, 1) if missing else (0, 1))
                                        for b in bits), 'invalid empirical state')
    return bits


def _event(action, entities, allow_self=True):
    action = tuple(action)
    require(len(action) == 4 and all(type(v) is int for v in action), 'invalid empirical action')
    kind, first, second, value = action
    require((kind == 0 and 0 <= first < entities and 0 <= second < entities and value == -1 and
             (allow_self or first != second)) or
            (kind == 1 and 0 <= first < entities and second == -1 and value in (0, 1)) or
            (kind == 2 and first == second == value == -1), 'invalid empirical action')
    return action


def domain_context(pre, action, past, mode):
    """Canonical physical coordinates plus explicit current/historical role aliases."""
    entities = len(pre)
    binary_worlds(entities)
    pre, action = _bits(pre, entities), _event(action, entities)
    history = tuple((_bits(before, entities, True), _event(act, entities), _bits(after, entities, True))
                    for before, act, after in past)
    kind, first, second, value = action
    unique, aliases = _roles(tuple(i for i in (first, second) if i >= 0))
    if mode == 'prefix':
        return (entities, aliases, pre, action, history), tuple(range(entities))
    require(mode in ('local', 'contact'), 'unknown context mode')
    order = unique + tuple(i for i in range(entities) if i not in unique)
    signatures = []
    if mode == 'contact':
        for before, act, after in history:
            if act[0] == 0:
                members, roles = _roles(act[1:3])
                signatures.append((roles, tuple(before[i] for i in members), tuple(after[i] for i in members)))
    return (entities, kind, value, aliases, tuple(pre[i] for i in order), tuple(signatures)), order


class DomainMemory:
    """Measured full-world count tables; unsupported size/alias contexts abstain."""
    supported_entities = (3, 4, 5, 6)
    supports_self_contact = True

    def __init__(self, mode):
        require(mode in ('prefix', 'local', 'contact'), 'unknown memory mode')
        self.mode, self.table, self.origin_digest = mode, {}, None

    @property
    def domain_adaptation(self):
        return {'version': 'domain-memory-v1', 'origin_table_sha256': self.origin_digest,
                'supported_entities': list(self.supported_entities), 'supports_self_contact': True,
                'larger_or_alias_counts_synthesized': False,
                'prediction_policy': 'observed_counts_only; unsupported_contexts_abstain'}

    def fit(self, batch):
        x, actions = batch.observations, batch.actions
        require(isinstance(x, torch.Tensor) and isinstance(actions, torch.Tensor) and
                x.ndim == actions.ndim == 3 and len(actions) > 0 and
                x.shape[:2] == (len(actions) + 1, actions.shape[1]), 'invalid measured batch')
        entities = validate_anchor(x[0], 1)
        for t, act in enumerate(actions):
            validate_anchor(x[t + 1], 1)
            validate_action(act, actions.shape[1], entities)
        states, events, table = x.long().tolist(), actions.tolist(), defaultdict(Counter)
        for e in range(actions.shape[1]):
            past = ()
            for t in range(len(actions)):
                pre, act, post = tuple(states[t][e]), tuple(events[t][e]), tuple(states[t + 1][e])
                key, order = domain_context(pre, act, past, self.mode)
                table[key][tuple(post[i] for i in order)] += 1
                past += ((pre, act, post),)
        self.table, self.origin_digest = dict(table), None
        return self

    def predict(self, pre, action, past):
        key, order = domain_context(pre, action, past, self.mode)
        counts = self.table.get(key)
        if not counts:
            return None
        total, result = sum(counts.values()), [0.] * (2 ** len(pre))
        for canonical, count in counts.items():
            canonical = _bits(canonical, len(pre))
            require(type(count) is int and count > 0, 'invalid empirical count')
            world = [0] * len(pre)
            for index, slot in enumerate(order):
                world[slot] = canonical[index]
            result[sum(bit << (len(pre) - 1 - i) for i, bit in enumerate(world))] = count / total
        require(abs(math.fsum(result) - 1.) <= 1e-12, 'invalid empirical distribution')
        return tuple(result)

    @classmethod
    def from_legacy(cls, memory):
        """Copy three-ID counts; no new alias or larger-world evidence is created."""
        result = cls(memory.mode)
        result.origin_digest = memory.digest()
        for key, counts in memory.table.items():
            if memory.mode == 'prefix':
                pre, action, past = key
                _event(action, 3, False)
                for _, act, _ in past:
                    _event(act, 3, False)
                new_key, _ = domain_context(pre, action, past, 'prefix')
                require(len(pre) == 3, 'legacy table must have three entities')
            else:
                kind, value, pre, signatures = key
                _bits(pre, 3)
                act = (kind, 0 if kind != 2 else -1, 1 if kind == 0 else -1, value)
                _event(act, 3, False)
                aliases = (0, 1) if kind == 0 else (0,) if kind == 1 else ()
                require(memory.mode == 'contact' or not signatures, 'local table has contact history')
                converted = tuple(((0, 1), _bits(before, 2), _bits(after, 2)) for before, after in signatures)
                new_key = (3, kind, value, aliases, tuple(pre), converted)
            require(new_key not in result.table and bool(counts), 'duplicate/empty migrated table key')
            result.table[new_key] = Counter()
            for world, count in counts.items():
                require(type(count) is int and count > 0, 'invalid legacy count')
                result.table[new_key][_bits(world, 3)] = count
        require(memory.digest() == result.origin_digest, 'migration mutated original table')
        return result

    def digest(self):
        records = [[key, sorted(counts.items())] for key, counts in sorted(self.table.items())]
        return sha256(json.dumps(['domain-memory-v1', self.mode, self.origin_digest, records],
                                 separators=(',', ':'), allow_nan=False).encode()).hexdigest()


class DomainSupport:
    """Direct observed contact support; alias contexts never share distinct-role counts.

    Reuse validated sensor receipt/expiry bookkeeping only. No posterior interface
    is exposed. Unaffected old readings still rely on supplied action locality.
    """
    __init__ = ObservedContextSupport.__init__
    _validate_measurements = staticmethod(ObservedContextSupport._validate_measurements)
    receive = ObservedContextSupport.receive

    def _action(self, action):
        require(type(action) is dict and not set(action) - {'kind', 'participants', 'value'}, 'invalid action')
        kind, members, value = action.get('kind'), action.get('participants'), action.get('value')
        require(type(members) in (list, tuple) and all(type(p) is str and p in self.ids for p in members),
                'invalid action participants')
        require((kind == 'contact' and len(members) == 2 and value is None) or
                (kind == 'set' and len(members) == 1 and type(value) is int and value in (0, 1)) or
                (kind == 'observe' and not members and value is None), 'invalid action')
        return kind, tuple(members), value

    def _signature(self, kind, participants):
        unique, aliases = _roles(participants)
        return len(self.ids), kind, aliases, tuple(self._known[name] for name in unique)

    def assess(self, action):
        if self.pending is not None:
            raise RuntimeError('cannot assess before committed feedback')
        kind, participants, _ = self._action(action)
        if kind != 'contact':
            return {'supported': False, 'status': 'UNSUPPORTED_ACTION', 'observed_events': 0}
        if any(name not in self._known for name in participants):
            return {'supported': False, 'status': 'UNOBSERVED_INPUT', 'observed_events': 0}
        count = self._contexts[self._signature(kind, participants)]
        return {'supported': count > 0, 'status': 'OBSERVED_CONTEXT' if count else 'UNTESTED_CONTEXT',
                'observed_events': count}

    def commit_action(self, action, *, intended_sensor_ids, next_time):
        if self.pending is not None:
            raise RuntimeError('previous feedback is still pending')
        require(type(next_time) is int and next_time == self.time + 1, 'non-sequential action time')
        kind, participants, value = self._action(action)
        require(type(intended_sensor_ids) in (list, tuple), 'invalid precommitted sensor coverage')
        coverage = tuple(intended_sensor_ids)
        require(bool(coverage) and len(set(coverage)) == len(coverage) and
                all(name in self.ids for name in coverage), 'invalid precommitted sensor coverage')
        signature = (self._signature(kind, participants) if kind == 'contact' and
                     all(name in self._known for name in participants) else None)
        self.pending = (kind, participants, value, coverage, next_time, signature)
