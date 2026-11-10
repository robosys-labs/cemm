"""Frozen selective-memory hypothesis and outcome-only matched controls.

Inputs are observed receipt/query tensors. This module has no simulator,
private-label, evaluator, repository, or artifact-loading dependency.
"""
from hashlib import sha256
import json
import math
import random
import resource
import time

import torch
from torch import nn

from .temporal_native_models_v1 import DTYPE, _query, fingerprint, receipt

ARMS = ('selective', 'native', 'flat')
PARAMETERS = {'selective': 2188, 'native': 2244, 'flat': 2280}
FORECASTS = ('probe_0', 'probe_1', 'probe_2', 'probe_3', 'target_0', 'target_1')


class Model(nn.Module):
    """Shared soft slot addressing or a dense GRU; no prescribed word slots."""
    def __init__(self, arm, seed):
        super().__init__()
        if arm not in ARMS or type(seed) is not int:
            raise ValueError('expected a registered arm and integer seed')
        self.arm = arm
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            factory = {'dtype': DTYPE, 'device': 'cpu'}
            shape = (2, 8) if arm == 'selective' else (16,)
            self.initial_state = nn.Parameter(torch.randn(shape, **factory) * .05)
            self.gru = nn.GRUCell(18, 8 if arm == 'selective' else 16, **factory)
            if arm == 'selective':
                self.write_key = nn.Sequential(nn.Linear(18, 8, **factory), nn.Tanh(),
                                               nn.Linear(8, 8, **factory), nn.Tanh())
                self.read_key = nn.Sequential(nn.Linear(41, 8, **factory), nn.Tanh(),
                                              nn.Linear(8, 8, **factory), nn.Tanh())
            self.hidden = nn.Linear(49 if arm == 'selective' else 57,
                                    16 if arm == 'selective' else 8, **factory)
            self.output = nn.Linear(16 if arm == 'selective' else 8,
                                    8 if arm == 'flat' else 4, **factory)
        if sum(p.numel() for p in self.parameters()) != PARAMETERS[arm]:
            raise ValueError('registered parameter inventory differs')

    def initial(self, batch):
        return self.initial_state.unsqueeze(0).expand(batch, *self.initial_state.shape)

    @staticmethod
    def _attention(state, key):
        return ((state * key[:, None, :]).sum(-1) / math.sqrt(8)).softmax(-1)

    def receive(self, state, observation):
        observation = torch.as_tensor(observation, dtype=DTYPE, device='cpu')
        if observation.shape != (len(state), 18) or not torch.isfinite(observation).all():
            raise ValueError('expected a finite batch of 18-value receipts')
        if state.shape != (len(observation), *self.initial_state.shape):
            raise ValueError('state dimensions differ')
        if self.arm != 'selective':
            return self.gru(observation, state)
        attention = self._attention(state, self.write_key(observation))
        proposal = self.gru(observation.repeat_interleave(2, 0), state.reshape(-1, 8))
        # Both proposals and addresses depend on the same pre-receipt state.
        return state + attention[..., None] * (proposal.reshape_as(state) - state)

    def history(self, observations):
        observations = torch.as_tensor(observations, dtype=DTYPE, device='cpu')
        if observations.ndim != 3 or observations.shape[-1] != 18:
            raise ValueError('expected receipts with shape [batch,time,18]')
        state = self.initial(len(observations))
        for observation in observations.unbind(1):
            state = self.receive(state, observation)
        return state

    def predict(self, state, query):
        query = _query(query)
        if query.ndim != 2 or state.shape != (len(query), *self.initial_state.shape):
            raise ValueError('state and query dimensions differ')
        if self.arm == 'selective':
            attention = self._attention(state, self.read_key(query))
            state = (state * attention[..., None]).sum(1)
        weights = self.output(torch.tanh(self.hidden(torch.cat((state, query), -1)))).softmax(-1)
        if self.arm == 'flat':
            return weights
        return torch.einsum('bh,bhy->by', weights, query[:, :32].reshape(-1, 4, 8))


def _arrays(tensors, training=False):
    required = {'base', 'probe_q', 'probe_y', 'target_q'}
    if not required <= set(tensors) or set(tensors) - required - {'target_y'}:
        raise ValueError('observed tensor inventory differs')
    if training and 'target_y' not in tensors:
        raise ValueError('training requires observed target endpoints')
    data = {}
    for key in required | ({'target_y'} if training else set()):
        value = torch.as_tensor(tensors[key], device='cpu')
        if key.endswith('_y'):
            if value.dtype not in (torch.uint8, torch.int8, torch.int16, torch.int32, torch.int64):
                raise ValueError('endpoints must be non-boolean integers')
            if ((value < 0) | (value > 7)).any():
                raise ValueError('endpoints must be in [0,7]')
        data[key] = value.to(torch.long if key.endswith('_y') else DTYPE)
    size = len(data['base'])
    shapes = {'base': (size, 10, 18), 'probe_q': (size, 4, 41),
              'probe_y': (size, 4), 'target_q': (size, 2, 41), 'target_y': (size, 2)}
    if not size or any(value.shape != shapes[key] or not torch.isfinite(value).all()
                       for key, value in data.items()):
        raise ValueError('nonempty finite tensor dimensions differ')
    for key in ('probe_q', 'target_q'):
        _query(data[key])
    words = data['probe_q'][..., 39:41]
    if not (((words == 0) | (words == 1)).all() and (words.sum(-1) == 1).all()
            and (words[:, :2].sum(1) == 1).all() and (words[:, 2:].sum(1) == 1).all()):
        raise ValueError('each probe pair must contain each observed word exactly once')
    expected = data['target_q'].new_tensor(((1, 0), (0, 1)))
    if not (data['target_q'][..., 39:41] == expected).all():
        raise ValueError('target queries must be in observed word order')
    return data


def _targets(model, state, queries):
    return model.predict(state.repeat_interleave(2, 0), queries.reshape(-1, 41)).reshape(-1, 2, 8)


def fit(model, tensors, seed, steps=256, *, synthetic=False):
    """Exactly one fixed-budget fit; shorter runs are synthetic-test only."""
    if type(steps) is not int or not 0 < steps <= 256 or (steps != 256 and not synthetic):
        raise ValueError('real fits require exactly 256 updates')
    data = _arrays(tensors, training=True)
    size = len(data['base'])
    rng, digest = random.Random(20261110200 + seed), sha256()
    optimizer = torch.optim.Adam(model.parameters(), lr=.01)
    initial, losses = fingerprint(model), []
    wall, cpu = time.perf_counter(), time.process_time()
    model.train()
    for step in range(steps):
        indices = [rng.randrange(size) for _ in range(128)]
        digest.update((json.dumps(indices, separators=(',', ':')) + '\n').encode())
        batch = {key: value[indices] for key, value in data.items()}
        state, terms = model.history(batch['base']), []
        for index in range(4):
            query, answer = batch['probe_q'][:, index], batch['probe_y'][:, index]
            prediction = model.predict(state, query)
            terms.append(-prediction.gather(1, answer[:, None]).log().mean())
            state = model.receive(state, receipt(query, answer))
        predictions = _targets(model, state, batch['target_q'])
        final_losses = -predictions.gather(-1, batch['target_y'][..., None]).squeeze(-1).log()
        terms.extend(final_losses.mean(0).unbind())
        components = torch.stack(terms)
        loss = components.mean()
        if not torch.isfinite(loss):
            raise ValueError(f'nonfinite uncapped training NLL at update {step + 1}')
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        losses.append({'update': step + 1, 'mean_nll': loss.item(),
                       'forecast_nll': dict(zip(FORECASTS, components.detach().tolist()))})
    return {'arm': model.arm, 'seed': seed, 'synthetic': synthetic,
            'initial_sha256': initial, 'final_sha256': fingerprint(model),
            'parameters': PARAMETERS[model.arm], 'state_scalars': 16,
            'updates': steps, 'batch_size': 128, 'sampled_episodes': steps * 128,
            'forecast_terms': steps * 128 * 6, 'minibatch_seed': 20261110200 + seed,
            'minibatch_sha256': digest.hexdigest(), 'losses': losses,
            'wall_seconds': time.perf_counter() - wall, 'cpu_seconds': time.process_time() - cpu,
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def _optional(model, state, queries, targets, answers):
    """Two separate one-question decisions, both made at the same prefix."""
    size = len(state)
    # Flatten [episode,word]; each decision receives its own cloned prefix.
    state = state.repeat_interleave(2, 0)
    queries, targets = queries.reshape(-1, 41), targets.reshape(-1, 41)
    probe, before = model.predict(state, queries), model.predict(state, targets)
    hypothetical = receipt(queries.repeat_interleave(8, 0), torch.arange(8).repeat(2 * size))
    updated = model.receive(state.repeat_interleave(8, 0), hypothetical)
    branches = model.predict(updated, targets.repeat_interleave(8, 0)).reshape(2 * size, 8, 8)
    value = (probe * branches.amax(-1)).sum(-1) - before.amax(-1)
    asks = torch.stack((value > .05 + 1e-12, value > 1. + 1e-12,
                        torch.zeros_like(value, dtype=torch.bool)), -1)
    # Actual answers are consumed only after forecasts and decisions are fixed.
    actual_state = model.receive(state, receipt(queries, answers.reshape(-1)))
    after = model.predict(actual_state, targets)
    return {key: value.reshape(size, 2, *value.shape[1:]) for key, value in
            {'probe': probe, 'before': before, 'branches': branches,
             'after': after, 'value': value, 'asks': asks}.items()}


@torch.inference_mode()
def collect(model, tensors, chunk=512):
    """Frozen inference; target outcomes are never loaded or used here."""
    if type(chunk) is not int or chunk < 1:
        raise ValueError('chunk must be a positive integer')
    data = _arrays(tensors)
    model.eval()
    parts = []
    for offset in range(0, len(data['base']), chunk):
        batch = {key: value[offset:offset + chunk] for key, value in data.items()}
        state = model.history(batch['base'][:, :8])
        result = {'teaching': _targets(model, state, batch['target_q'])}
        for observation in batch['base'][:, 8:].unbind(1):
            state = model.receive(state, observation)
        claim_state = state
        result['claims'] = _targets(model, state, batch['target_q'])
        forecasts = []
        for index in range(4):
            query, answer = batch['probe_q'][:, index], batch['probe_y'][:, index]
            forecasts.append(model.predict(state, query))
            state = model.receive(state, receipt(query, answer))
            if index == 1:
                pair_state = state
                result['pair'] = _targets(model, state, batch['target_q'])
                # Metadata chooses an observed question, never a memory slot.
                indices = batch['probe_q'][:, 2:, 39:41].transpose(1, 2).argmax(-1) + 2
                queries = batch['probe_q'].gather(1, indices[..., None].expand(-1, -1, 41))
                answers = batch['probe_y'].gather(1, indices)
                result['optional_y'] = answers
                for prefix, name in ((pair_state, 'optional_'), (claim_state, 'cleared_optional_')):
                    result.update({name + key: value for key, value in
                                   _optional(model, prefix, queries, batch['target_q'], answers).items()})
            elif index == 2:
                result['third'] = _targets(model, state, batch['target_q'])
        result['final'] = _targets(model, state, batch['target_q'])
        result['next_probe'] = torch.stack(forecasts, 1)
        cleared = claim_state
        for index in (2, 3):
            cleared = model.receive(cleared, receipt(batch['probe_q'][:, index], batch['probe_y'][:, index]))
        result['cleared_final'] = _targets(model, cleared, batch['target_q'])
        parts.append(result)
    return {key: torch.cat([part[key] for part in parts]) for key in parts[0]}
