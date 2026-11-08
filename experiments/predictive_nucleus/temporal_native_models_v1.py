"""Outcome-only temporal learners; no simulator, labels or evaluator dependency."""
from hashlib import sha256
import json
import random
import resource
import time

import torch
from torch import nn


DTYPE = torch.float64
FORECASTS = ('first', 'second', 'target_before', 'target_first', 'target_both', 'protected')


def _query(value):
    value = torch.as_tensor(value, dtype=DTYPE, device='cpu')
    if value.ndim < 1 or value.shape[-1] != 41 or not torch.isfinite(value).all():
        raise ValueError('expected finite 41-value query features')
    rows = value[..., :32].reshape(*value.shape[:-1], 4, 8)
    if (rows < 0).any() or not torch.allclose(rows.sum(-1), torch.ones_like(rows[..., 0]), atol=1e-10, rtol=0):
        raise ValueError('native rows must be normalized probabilities')
    return value


def receipt(query, endpoint, source='physical'):
    """Encode only a delivered endpoint and its public query/source metadata.

    The four likelihood features are selected from the same frozen native rows
    available before the answer. A counterfactual receipt is encoded identically.
    """
    query = _query(query)
    endpoint = torch.as_tensor(endpoint, device='cpu')
    if endpoint.dtype not in (torch.uint8, torch.int8, torch.int16, torch.int32, torch.int64):
        raise ValueError('endpoint must be a non-boolean integer')
    endpoint = torch.broadcast_to(endpoint, query.shape[:-1]).long()
    if ((endpoint < 0) | (endpoint > 7)).any() or source not in ('physical', 'claim'):
        raise ValueError('invalid endpoint or source')
    rows = query[..., :32].reshape(*query.shape[:-1], 4, 8)
    likelihoods = rows.gather(-1, endpoint[..., None, None].expand(*endpoint.shape, 4, 1)).squeeze(-1)
    bits = torch.stack(tuple((endpoint >> shift) & 1 for shift in (2, 1, 0)), -1).to(DTYPE)
    source_bits = query.new_tensor((1, 0) if source == 'physical' else (0, 1)).expand(*endpoint.shape, 2)
    return torch.cat((likelihoods, bits, query[..., 32:39], source_bits, query[..., 39:41]), -1)


class Model(nn.Module):
    """Common receipt memory and query trunk, with native-mixture or flat output."""
    def __init__(self, arm, seed):
        super().__init__()
        if arm not in ('native', 'flat'):
            raise ValueError('arm must be native or flat')
        self.arm = arm
        # Isolate initialization from the caller's RNG; both arms share a trunk.
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            self.gru = nn.GRUCell(18, 8, dtype=DTYPE, device='cpu')
            self.hidden = nn.Linear(49, 8, dtype=DTYPE, device='cpu')
            self.output = nn.Linear(8, 4 if arm == 'native' else 8, dtype=DTYPE, device='cpu')
        expected = 1108 if arm == 'native' else 1144
        if sum(parameter.numel() for parameter in self.parameters()) != expected:
            raise ValueError('frozen parameter inventory differs')

    def initial(self, batch):
        return torch.zeros(batch, 8, dtype=DTYPE, device='cpu')

    def receive(self, state, observation):
        observation = torch.as_tensor(observation, dtype=DTYPE, device='cpu')
        if observation.ndim != 2 or observation.shape != (len(state), 18) or not torch.isfinite(observation).all():
            raise ValueError('expected a finite batch of 18-value receipts')
        return self.gru(observation, state)

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
        if query.ndim != 2 or state.shape != (len(query), 8):
            raise ValueError('state and query batch dimensions differ')
        weights = self.output(torch.tanh(self.hidden(torch.cat((state, query), -1)))).softmax(-1)
        if self.arm == 'flat':
            return weights
        return torch.einsum('bh,bhy->by', weights, query[:, :32].reshape(-1, 4, 8))


def fingerprint(model):
    """Bind parameter names, shapes and float64 bytes without pickle metadata."""
    digest = sha256()
    for name, value in model.state_dict().items():
        digest.update(json.dumps([name, list(value.shape)], separators=(',', ':')).encode())
        digest.update(value.detach().contiguous().numpy().astype('<f8', copy=False).tobytes())
    return digest.hexdigest()


def _arrays(tensors):
    data = {}
    for key, value in tensors.items():
        value = torch.as_tensor(value, device='cpu')
        if key.endswith('_y'):
            if value.ndim != 1 or value.dtype not in (torch.uint8, torch.int8, torch.int16, torch.int32, torch.int64):
                raise ValueError('endpoint arrays must contain non-boolean integers')
            if ((value < 0) | (value > 7)).any():
                raise ValueError('endpoint arrays must be in [0,7]')
        data[key] = value.to(torch.long if key.endswith('_y') else DTYPE)
    return data


def fit(model, tensors, seed, steps=256):
    """One fixed-budget Adam fit; identical sampled episodes for the two arms."""
    data = _arrays(tensors)
    size = len(data['base'])
    if not size or any(len(value) != size for value in data.values()):
        raise ValueError('training arrays must have one shared nonempty batch')
    if type(steps) is not int or not 0 < steps <= 256:
        raise ValueError('steps must be within the frozen 256-update budget')
    rng, digest = random.Random(20261108200 + seed), sha256()
    optimizer = torch.optim.Adam(model.parameters(), lr=.01)
    initial, losses = fingerprint(model), []
    wall, cpu = time.perf_counter(), time.process_time()
    model.train()
    for step in range(steps):
        indices = [rng.randrange(size) for _ in range(128)]
        digest.update((json.dumps(indices, separators=(',', ':')) + '\n').encode())
        batch = {key: value[indices] for key, value in data.items()}
        before = model.history(batch['base'])
        first = model.receive(before, receipt(batch['first_q'], batch['first_y']))
        both = model.receive(first, receipt(batch['second_q'], batch['second_y']))
        forecasts = ((before, 'first'), (first, 'second'), (before, 'target'),
                     (first, 'target'), (both, 'target'), (both, 'protected'))
        components = torch.stack(tuple(-model.predict(state, batch[name + '_q']).gather(
            1, batch[name + '_y'][:, None]).log().mean() for state, name in forecasts))
        loss = components.mean()
        if not torch.isfinite(loss):
            raise ValueError(f'nonfinite uncapped training NLL at update {step + 1}')
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        losses.append({'update': step + 1, 'mean_nll': loss.item(),
                       'forecast_nll': dict(zip(FORECASTS, components.detach().tolist()))})
    return {'arm': model.arm, 'seed': seed, 'initial_sha256': initial, 'final_sha256': fingerprint(model),
            'parameters': sum(parameter.numel() for parameter in model.parameters()),
            'updates': steps, 'batch_size': 128, 'sampled_episodes': steps * 128,
            'forecast_terms': steps * 128 * 6, 'target_endpoint_forecasts_per_episode': 3,
            'minibatch_seed': 20261108200 + seed, 'minibatch_sha256': digest.hexdigest(),
            'losses': losses, 'wall_seconds': time.perf_counter() - wall,
            'cpu_seconds': time.process_time() - cpu,
            'peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}


def _optional(model, state, second_query, target_query):
    """Counterfactual forecasts depend on the prefix, never the actual answer."""
    size = len(state)
    q2distribution = model.predict(state, second_query)
    pretarget = model.predict(state, target_query)
    hypothetical = receipt(second_query.repeat_interleave(8, 0), torch.arange(8).repeat(size))
    updated = model.receive(state.repeat_interleave(8, 0), hypothetical)
    branches = model.predict(updated, target_query.repeat_interleave(8, 0)).reshape(size, 8, 8)
    residual = (q2distribution[:, :, None] * branches).sum(1) - pretarget
    value = (q2distribution * branches.amax(-1)).sum(-1) - pretarget.amax(-1)
    asks = torch.stack((value > .05 + 1e-12, value > 1. + 1e-12,
                        torch.zeros_like(value, dtype=torch.bool)), -1)
    return {'q2distribution': q2distribution, 'pretarget': pretarget,
            'branches': branches, 'tower_residual': residual,
            'question_value': value, 'question_asks': asks}


@torch.inference_mode()
def collect(model, tensors, chunk=512):
    """Collect scheduled views plus the pre-answer optional-question branches.

    The after-second arrays are retrospective fixed-schedule views. Question
    decisions are fixed before the actual second receipt is consumed below.
    """
    if type(chunk) is not int or chunk < 1:
        raise ValueError('chunk must be a positive integer')
    data = _arrays(tensors)
    size = len(data['base'])
    if not size or any(len(value) != size for value in data.values()):
        raise ValueError('collection arrays must have one shared nonempty batch')
    parts, cleared_parts = [], []
    model.eval()
    for offset in range(0, size, chunk):
        batch = {key: value[offset:offset + chunk] for key, value in data.items()}
        before = model.history(batch['base'])
        first = model.receive(before, receipt(batch['first_q'], batch['first_y']))
        main = _optional(model, first, batch['second_q'], batch['target_q'])
        cleared = _optional(model, before, batch['second_q'], batch['target_q'])
        both = model.receive(first, receipt(batch['second_q'], batch['second_y']))
        clear_both = model.receive(before, receipt(batch['second_q'], batch['second_y']))
        main.update(base_target=cleared['pretarget'], after_first=main['pretarget'],
                    after_second=model.predict(both, batch['target_q']),
                    protected=model.predict(both, batch['protected_q']))
        cleared.update(after_second=model.predict(clear_both, batch['target_q']),
                       protected=model.predict(clear_both, batch['protected_q']))
        parts.append(main)
        cleared_parts.append(cleared)
    joined = {key: torch.cat([part[key] for part in parts]) for key in parts[0]}
    joined['cleared'] = {key: torch.cat([part[key] for part in cleared_parts]) for key in cleared_parts[0]}
    return joined
