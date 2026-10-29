"""Versioned inference repairs; frozen masked_replay and studies stay unchanged.

Exact-zero neural histories are removed, never small positive log mass. Empirical
re-entry uses only an observed sufficient context, never guessed hidden history.
Three binary entities and the original noiseless-visible-sensor contract remain.
"""
import math

import numpy as np
import torch

from . import comparison_scoring as scores
from . import masked_replay as frozen

WORLDS = frozen.WORLDS
LastObserved = frozen.LastObserved
require = scores.require


def _anchor(anchor, limit):
    require(type(limit) is int and limit > 0, 'positive integer path limit required')
    require(isinstance(anchor, torch.Tensor) and anchor.device.type == 'cpu' and
            anchor.dtype == torch.float64 and anchor.ndim == 2 and anchor.shape[1] == 3 and
            len(anchor) > 0 and bool(((anchor == 0) | (anchor == 1)).all()), 'invalid full anchor')


def _reading(reading, mask, n):
    require(isinstance(reading, torch.Tensor) and isinstance(mask, torch.Tensor) and
            reading.device.type == mask.device.type == 'cpu' and reading.dtype == torch.float64 and
            mask.dtype == torch.bool and reading.shape == mask.shape == (n, 3), 'invalid feedback shape/dtype')
    require(bool(((reading[mask] == 0) | (reading[mask] == 1)).all()) and
            bool((reading[~mask] == -1).all()), 'hidden values must be -1; visible values binary')


def _action(action, n):
    require(isinstance(action, torch.Tensor) and action.device.type == 'cpu' and
            action.dtype == torch.long and action.shape == (n, 4), 'invalid action shape/dtype')
    k, p, q, v = action.unbind(-1)
    valid = (k == 0) & (p >= 0) & (p < 3) & (q >= 0) & (q < 3) & (p != q) & (v == -1)
    valid |= (k == 1) & (p >= 0) & (p < 3) & (q == -1) & ((v == 0) | (v == 1))
    valid |= (k == 2) & (p == -1) & (q == -1) & (v == -1)
    require(bool(valid.all()), 'invalid action')


class NeuralPaths:
    """Packed live paths with per-episode budgets, including finite underflowed logs.

    Distinct recurrent histories are NEVER merged. Packed owners allow unequal
    path counts/masks across episodes without padding or artificial hypotheses.
    """
    def __init__(self, model, anchor, limit=64):
        _anchor(anchor, limit)
        self.model, self.limit, self.n = model, limit, len(anchor)
        self.bits, self.state = anchor.clone(), model.initial(self.n)
        self.owner = torch.arange(self.n)
        self.weight = torch.zeros(self.n, dtype=torch.float64)
        self.worlds = torch.tensor(WORLDS, dtype=torch.float64)
        self.ready, self.diagnostic = True, {}

    @torch.inference_mode()
    def predict(self, action):
        require(self.ready, 'feedback required before another prediction')
        _action(action, self.n)
        raw, pending = self.model.predict(self.bits.clone(), action[self.owner].clone(), self.state.clone())
        normalized, correction = scores.normalize(raw, np.ones(len(raw), dtype=bool))
        conditional = torch.from_numpy(normalized)
        weighted = self.weight[:, None] + conditional
        counts = torch.bincount(self.owner, minlength=self.n)
        result = torch.stack([block.logsumexp(0) for block in weighted.split(counts.tolist())])
        self.pending, self.conditional, self.ready = pending.clone(), conditional, False
        self.diagnostic = {'live_paths': counts.tolist(),
                           'stored_paths_total': len(self.owner),
                           'max_abs_conditional_log_correction': float(np.abs(correction).max())}
        return result, np.ones(self.n, dtype=bool)

    @torch.inference_mode()
    def receive(self, reading, mask):
        require(not self.ready, 'prediction required before feedback')
        _reading(reading, mask, self.n)
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


class EmpiricalPaths(frozen.EmpiricalPaths):
    """Retain direct observations separately from predictive table support.

    Recovery requires a full current observation and the sufficient *observed*
    context: none for local; complete prefix for prefix; complete ordered contact
    operand histories for contact; only the first contact for first_contact.
    Unknown historic bits stay -1 and are never turned into guessed evidence.
    """
    def __init__(self, memory, anchor, *, first_contact=False, limit=64):
        _anchor(anchor, limit)
        require(memory.mode in ('prefix', 'local', 'contact') and type(first_contact) is bool and
                (not first_contact or memory.mode == 'contact'), 'invalid empirical recovery policy')
        super().__init__(memory, anchor, first_contact=first_contact, limit=limit)
        self.observed = [tuple(map(int, row)) for row in anchor.tolist()]
        self.history = [() for _ in self.observed]
        self.ready = True

    def predict(self, action):
        require(self.ready, 'feedback required before another prediction')
        _action(action, len(self.paths))
        result = super().predict(action.clone())
        self.actions = [tuple(row) for row in action.tolist()]
        self.ready = False
        return result

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
        _reading(reading, mask, len(self.paths))
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
