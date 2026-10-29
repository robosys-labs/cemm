"""Versioned inference repairs; frozen masked_replay and studies stay unchanged.

Exact-zero neural histories are removed, never small positive log mass. Empirical
re-entry uses only an observed sufficient context, never guessed hidden history.
The active domain is 3-6 binary entities; legacy predictors remain three-ID only.
"""
import math
from functools import wraps

import numpy as np
import torch

from . import domain_contract as scores
from . import masked_replay as frozen

WORLDS = frozen.WORLDS
require = scores.require


def _gradient_mode(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        require(not self.differentiable or not torch.is_inference_mode_enabled(),
                'differentiable filtering cannot run inside inference mode')
        with torch.set_grad_enabled(self.differentiable):
            return method(self, *args, **kwargs)
    return call


def capabilities(predictor):
    counts = getattr(predictor, 'supported_entities', (3,))
    aliases = getattr(predictor, 'supports_self_contact', False)
    require(type(counts) in (tuple, list) and bool(counts) and
            all(type(n) is int and 3 <= n <= 6 for n in counts) and
            len(set(counts)) == len(counts) and type(aliases) is bool, 'invalid predictor domain')
    return tuple(counts), aliases


def empirical_control(memory, control=None):
    """A fitted table's context abstraction is part of its predictor contract."""
    expected = getattr(memory, 'control_name', memory.mode)
    allowed = (memory.mode, 'first_contact') if memory.mode == 'contact' else (memory.mode,)
    require(expected in allowed and (control is None or control in allowed), 'invalid empirical control')
    require(not hasattr(memory, 'control_name') or control in (None, expected),
            'control differs from fitted empirical policy')
    return expected if control is None else control


def _domain(predictor, anchor, limit, expansion_limit):
    entities = scores.validate_anchor(anchor, limit)
    counts, aliases = capabilities(predictor)
    require(entities in counts, 'entity count outside predictor domain; explicit adaptation required')
    require(type(expansion_limit) is int and expansion_limit > 0, 'positive integer expansion limit required')
    return entities, aliases


class LastObserved:
    """Same supplied last-reading baseline, now with explicit dynamic geometry."""
    supported_entities, supports_self_contact = (3, 4, 5, 6), True

    def __init__(self, anchor):
        self.entities = scores.validate_anchor(anchor, 64)
        self.bits, self.diagnostic = anchor.clone(), {}

    def predict(self, action):
        scores.validate_action(action, len(self.bits), self.entities)
        indices = scores.world_index(self.bits)
        raw = torch.full((len(indices), 2 ** self.entities), -torch.inf, dtype=torch.float64)
        raw[torch.arange(len(indices)), indices] = 0.
        return raw, np.ones(len(indices), dtype=bool)

    def receive(self, reading, mask):
        scores.validate_reading(reading, mask, len(self.bits), self.entities)
        self.bits = torch.where(mask, reading, self.bits)


class NeuralPaths:
    """Packed live paths with per-episode budgets, including finite underflowed logs.

    Distinct recurrent histories are NEVER merged. Packed owners allow unequal
    path counts/masks across episodes without padding or artificial hypotheses.
    """
    def __init__(self, model, anchor, limit=64, expansion_limit=512, *, differentiable=False):
        require(type(differentiable) is bool, 'differentiable must be a boolean')
        self.differentiable = differentiable
        self.entities, self.aliases = _domain(model, anchor, limit, expansion_limit)
        self.expansion_limit = expansion_limit
        self.model, self.limit, self.n = model, limit, len(anchor)
        self.bits, self.state = anchor.clone(), model.initial(self.n)
        self.owner = torch.arange(self.n)
        self.weight = torch.zeros(self.n, dtype=torch.float64)
        self.worlds = torch.tensor(scores.binary_worlds(self.entities), dtype=torch.float64)
        self.ready, self.diagnostic = True, {}

    @_gradient_mode
    def predict(self, action):
        require(self.ready, 'feedback required before another prediction')
        scores.validate_action(action, self.n, self.entities, allow_self=self.aliases)
        counts = torch.bincount(self.owner, minlength=self.n)
        expansions = counts * len(self.worlds)
        require(bool((expansions <= self.expansion_limit).all()),
                'candidate expansion bound exceeded before prediction; no pruning')
        raw, pending = self.model.predict(self.bits.clone(), action[self.owner].clone(), self.state.clone())
        require(raw.shape == (len(self.owner), len(self.worlds)), 'predictor joint world shape mismatch')
        conditional, correction = scores.normalize_tensor(raw, np.ones(len(raw), dtype=bool))
        weighted = self.weight[:, None] + conditional
        result = torch.stack([scores.safe_logsumexp(block, 0) for block in weighted.split(counts.tolist())])
        diagnostic = {'live_paths': counts.tolist(),
                      'candidate_expansions': expansions.tolist(), 'expansion_limit': self.expansion_limit,
                      'stored_paths_total': len(self.owner),
                      'max_abs_conditional_log_correction': float(correction.detach().abs().max())}
        acts = action[self.owner]
        aliases = (acts[:, 0] == 0) & (acts[:, 1] == acts[:, 2])
        retained_mass = getattr(self.model, 'alias_log_mass', None)
        if bool(aliases.any()) and callable(retained_mass):
            mass = retained_mass(self.bits[aliases].clone(), acts[aliases].clone())
            require(isinstance(mass, torch.Tensor) and mass.dtype == torch.float64 and
                    mass.device.type == 'cpu' and mass.ndim == 2 and len(mass) == int(aliases.sum()) and
                    bool(torch.isfinite(mass).all()) and bool((mass <= 1e-10).all()),
                    'invalid retained alias log mass')
            diagnostic['alias_conditioning'] = {
                'interpretation': 'supplied_per_mode_diagonal_normalization',
                'path_owners': self.owner[aliases].tolist(),
                'retained_log_mass_by_path_and_mode': mass.tolist(),
                'learned_transfer_established': False}
        self.pending, self.conditional, self.ready = pending.clone(), conditional, False
        self.diagnostic = diagnostic
        return result, np.ones(self.n, dtype=bool)

    @_gradient_mode
    def receive(self, reading, mask):
        require(not self.ready, 'prediction required before feedback')
        scores.validate_reading(reading, mask, self.n, self.entities)
        compatible = ((self.worlds[None] == reading[:, None, :]) | ~mask[:, None, :]).all(-1)
        weighted = self.weight[:, None] + self.conditional
        alive = compatible[self.owner] & torch.isfinite(weighted)
        parents, outcomes = alive.nonzero(as_tuple=True)
        owners = self.owner[parents]
        counts = torch.bincount(owners, minlength=self.n)
        require(bool((counts > 0).all()), 'visible evidence outside model support')
        require(bool((counts <= self.limit).all()), 'live path bound exceeded; no positive-mass pruning')
        weights = weighted[parents, outcomes]
        evidence = torch.stack([block.logsumexp(0) for block in weights.split(counts.tolist())])
        bits = self.worlds[outcomes]
        state = self.model.receive(self.pending[parents], bits)
        require(state.shape == (len(parents), *self.state.shape[1:]) and
                not bool((torch.isnan(state) | torch.isposinf(state)).any()), 'invalid next recurrent state')
        # Commit only after every episode and budget has passed validation.
        self.owner, self.bits, self.state = owners, bits.clone(), state.clone()
        self.weight, self.ready = weights - evidence[owners], True
        self.diagnostic = {'live_paths': counts.tolist(), 'stored_paths_total': len(owners),
                           'visible_log_likelihood': evidence.tolist(),
                           'missing_bits': (~mask).sum(-1).tolist()}
        del self.pending, self.conditional
        return evidence


class EmpiricalPaths(frozen.EmpiricalPaths):
    """Retain direct observations separately from predictive table support.

    Recovery requires a full current observation and the sufficient *observed*
    context: none for local; complete prefix for prefix; complete ordered contact
    operand histories for contact; only the first contact for first_contact.
    Unknown historic bits stay -1 and are never turned into guessed evidence.
    """
    def __init__(self, memory, anchor, *, first_contact=False, limit=64, expansion_limit=512):
        self.entities, self.aliases = _domain(memory, anchor, limit, expansion_limit)
        self.worlds = scores.binary_worlds(self.entities)
        self.expansion_limit = expansion_limit
        require(memory.mode in ('prefix', 'local', 'contact') and type(first_contact) is bool and
                (not first_contact or memory.mode == 'contact'), 'invalid empirical recovery policy')
        super().__init__(memory, anchor, first_contact=first_contact, limit=limit)
        self.observed = [tuple(map(int, row)) for row in anchor.tolist()]
        self.history = [() for _ in self.observed]
        self.ready = True

    def predict(self, action):
        require(self.ready, 'feedback required before another prediction')
        scores.validate_action(action, len(self.paths), self.entities, allow_self=self.aliases)
        candidates = [len(paths) * len(self.worlds) for paths in self.paths]
        require(all(n <= self.expansion_limit for n in candidates),
                'candidate expansion bound exceeded before prediction; no pruning')
        raw = torch.full((len(self.paths), len(self.worlds)), -torch.inf, dtype=torch.float64)
        answered, expansions, missing = [], [], 0
        for paths, a in zip(self.paths, action.tolist(), strict=True):
            a, expanded, total = tuple(a), [], [0.] * len(self.worlds)
            supported = bool(paths)
            for weight, pre, past in paths:
                context = tuple(row for row in past if row[1][0] == 0)[:1] if self.first_contact else past
                probabilities = self.memory.predict(pre, a, context)
                if probabilities is None:
                    missing += 1
                    supported = False
                    break
                require(len(probabilities) == len(self.worlds) and
                        all(math.isfinite(p) and 0 <= p <= 1 for p in probabilities) and
                        abs(math.fsum(probabilities) - 1.) <= 1e-12, 'invalid empirical distribution')
                for index, (world, probability) in enumerate(zip(self.worlds, probabilities, strict=True)):
                    if probability > 0:
                        mass = weight * probability
                        require(mass > 0, 'empirical path underflow')
                        expanded.append((mass, world, past + ((pre, a, world),)))
                        total[index] += mass
            answered.append(supported)
            expansions.append(expanded if supported else [])
            if supported:
                raw[len(answered) - 1] = torch.tensor(total, dtype=torch.float64).log()
        self.expansions = expansions
        self.diagnostic = {'unsupported_positive_paths': missing,
                           'represented_paths_max': max(map(len, self.paths), default=0),
                           'candidate_expansions': candidates, 'expansion_limit': self.expansion_limit}
        self.actions = [tuple(row) for row in action.tolist()]
        self.ready = False
        return raw, np.array(answered, dtype=bool)

    def _context_complete(self, history):
        if self.memory.mode == 'local':
            return True
        if self.memory.mode == 'prefix':
            return all(all(bit in (0, 1) for bit in before + after) for before, _, after in history)
        contacts = [row for row in history if row[1][0] == 0]
        if self.first_contact:
            contacts = contacts[:1]
        return all(all(before[i] in (0, 1) and after[i] in (0, 1) for i in action[1:3])
                   for before, action, after in contacts)

    def receive(self, reading, mask):
        require(not self.ready, 'prediction required before feedback')
        scores.validate_reading(reading, mask, len(self.paths), self.entities)
        result, histories, observed, recovery = [], [], [], []
        for i, (paths, x, visible) in enumerate(zip(self.expansions, reading.tolist(), mask.tolist(), strict=True)):
            bits = tuple(map(int, x))
            history = self.history[i] + ((self.observed[i], self.actions[i], bits),)
            selected = [(w, state, past) for w, state, past in paths if
                        all(not show or bit == value for bit, value, show in zip(state, x, visible))]
            # Supported but impossible observations remain explicit conflicts.
            require(not paths or bool(selected), 'visible evidence outside empirical support')
            require(len(selected) <= self.limit, 'empirical live path bound exceeded')
            if selected:
                mass = math.fsum(w for w, _, _ in selected)
                result.append([(w / mass, state, past) for w, state, past in selected])
                recovery.append('conditioned_prediction')
            elif all(visible) and self._context_complete(history):
                # No probability assigned to unknown histories: the needed context
                # is now determined entirely by real measurements. Tables stay fixed.
                result.append([(1., bits, history)])
                recovery.append('recovered_observed_context')
            else:
                result.append([])
                recovery.append('missing_current_readings' if not all(visible) else 'missing_relevant_history')
            observed.append(bits)
            histories.append(history)
        self.paths, self.history, self.observed, self.ready = result, histories, observed, True
        self.diagnostic = {'recovery': recovery, 'live_paths': list(map(len, result))}
        del self.actions, self.expansions
