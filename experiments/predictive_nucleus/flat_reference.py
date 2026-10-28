"""Small flat GRU reference trained solely on subsequent sensor observations.

There is no imported transition rule, orientation label or evaluator truth.
The model scores joint worlds and marginalizes padded or unobserved bits.
"""
from __future__ import annotations

from math import isfinite
from time import perf_counter

import torch
from torch import nn
from torch.nn import functional as F

from .flat_data import FEATURES, MAX_ENTITIES, event_features, initial_ids, readings, sensor_episode

STATE_BITS = torch.tensor([[int(bool(i & (1 << (MAX_ENTITIES - 1 - j))))
                            for j in range(MAX_ENTITIES)] for i in range(2 ** MAX_ENTITIES)],
                          dtype=torch.long)


class FlatWorldGRU(nn.Module):
    """Seven hidden units: 1,457 parameters for the declared 36 -> 64 ABI."""
    def __init__(self):
        super().__init__()
        self.cell = nn.GRUCell(FEATURES, 7)
        self.head = nn.Linear(7, 2 ** MAX_ENTITIES)

    def param_count(self):
        return sum(p.numel() for p in self.parameters())

    def reset(self, anchor: dict, *, sensor_error_rate: float = 0.0):
        self.ids = initial_ids(anchor)
        if type(sensor_error_rate) not in (float, int) or not isfinite(sensor_error_rate) or not 0 <= sensor_error_rate < .5:
            raise ValueError("invalid supplied sensor calibration")
        self.sensor_error_rate = float(sensor_error_rate)
        self.time = anchor["t"]
        self.observation = {"t": anchor["t"], "measurements": [dict(m) for m in anchor["measurements"]]}
        self.hidden = torch.zeros(1, 7)
        self.pending = None

    @torch.no_grad()
    def preview(self, action: dict, *, temperature: float = 1.0):
        if self.pending is not None:
            raise RuntimeError("feedback required before prediction")
        if not isfinite(temperature) or temperature <= 0:
            raise ValueError("invalid temperature")
        x = torch.tensor([event_features(self.ids, self.observation, action,
                                         sensor_error_rate=self.sensor_error_rate)], dtype=torch.float32)
        next_hidden = self.cell(x, self.hidden)
        probabilities = (self.head(next_hidden) / temperature).softmax(dim=-1).squeeze(0).tolist()
        world = {}
        for index, probability in enumerate(probabilities):
            bits = tuple(int(bool(index & (1 << (MAX_ENTITIES - 1 - i)))) for i in range(len(self.ids)))
            world[bits] = world.get(bits, 0.0) + probability
        return world, next_hidden

    @torch.no_grad()
    def commit(self, action: dict, *, temperature: float = 1.0):
        world, next_hidden = self.preview(action, temperature=temperature)
        self.pending = next_hidden
        return world

    def receive(self, observation: dict):
        if self.pending is None:
            raise RuntimeError("feedback without a committed prediction")
        if type(observation.get("t")) is not int or observation["t"] != self.time + 1:
            raise ValueError("non-sequential feedback")
        measured = readings(observation)
        if not set(measured).issubset(self.ids):
            raise ValueError("feedback introduces an unknown identity")
        self.hidden = self.pending
        self.pending = None
        self.time += 1
        self.observation = {"t": self.time, "measurements": [dict(m) for m in observation["measurements"]]}


def batch_episodes(episodes):
    rows = [sensor_episode(episode) for episode in episodes]
    if not rows:
        raise ValueError("no training episodes")
    steps, n = max(map(len, rows)), len(rows)
    x = torch.zeros((steps, n, FEATURES), dtype=torch.float32)
    y = torch.full((steps, n, MAX_ENTITIES), -1, dtype=torch.long)
    valid = torch.zeros((steps, n), dtype=torch.bool)
    for b, episode in enumerate(rows):
        for t, (features, target) in enumerate(episode):
            x[t, b] = torch.tensor(features, dtype=torch.float32)
            y[t, b] = torch.tensor(target, dtype=torch.long)
            valid[t, b] = True
    if not ((y >= 0).any(dim=-1) & valid).any():
        raise ValueError("no observed targets")
    return x, y, valid


def logits_for_batch(model: FlatWorldGRU, batch):
    x, _, valid = batch
    hidden = torch.zeros(x.shape[1], 7)
    outputs = []
    for t in range(x.shape[0]):
        proposal = model.cell(x[t], hidden)
        hidden = torch.where(valid[t, :, None], proposal, hidden)
        outputs.append(model.head(hidden))
    return torch.stack(outputs)


def sensor_nll(logits, targets, valid, temperature: float = 1.0):
    """Marginalize every unobserved and padded bit, never impute zero."""
    if not isfinite(temperature) or temperature <= 0:
        raise ValueError("invalid temperature")
    logp = F.log_softmax(logits / temperature, dim=-1)
    matches = ((targets[:, :, None, :] < 0) |
               (targets[:, :, None, :] == STATE_BITS[None, None, :, :])).all(dim=-1)
    measured = valid & (targets >= 0).any(dim=-1)
    log_observed = torch.logsumexp(logp.masked_fill(~matches, float("-inf")), dim=-1)
    if not measured.any():
        raise ValueError("no measured feedback")
    return -log_observed[measured].mean()


def fit_flat(batch, seed: int, *, max_steps: int, wall_budget_seconds: float,
             learning_rate: float = .02, fixed_steps: int | None = None):
    """No more optimizer steps and approximately no more fit time than reference.

    The last-step duration is a conservative predictor, not a hard real-time
    guarantee. Actual times and any overshoot must be reported.
    """
    if (type(seed) is not int or max_steps < 1 or not isfinite(wall_budget_seconds) or wall_budget_seconds <= 0 or
            (fixed_steps is not None and (type(fixed_steps) is not int or not 1 <= fixed_steps <= max_steps))):
        raise ValueError("invalid model seed or training budget")
    start = perf_counter()
    torch.manual_seed(seed)
    model = FlatWorldGRU()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    previous_step_seconds = 0.0
    steps = 0
    last = None
    while steps < (fixed_steps if fixed_steps is not None else max_steps):
        now = perf_counter()
        if fixed_steps is None and steps and now - start + previous_step_seconds >= wall_budget_seconds:
            break
        before = now
        logits = logits_for_batch(model, batch)
        loss = sensor_nll(logits, batch[1], batch[2])
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        previous_step_seconds = perf_counter() - before
        steps += 1
        last = float(loss.detach())
    elapsed = perf_counter() - start
    return model, {"parameters": model.param_count(), "gradient_steps": steps,
                   "fit_seconds": elapsed, "wall_budget_seconds": wall_budget_seconds,
                   "schedule": "fixed_replay" if fixed_steps is not None else "wall_capped",
                   "overshoot_seconds": max(0.0, elapsed - wall_budget_seconds),
                   "training_sensor_nll": last, "episodes": int(batch[0].shape[1]),
                   "measured_events": int((batch[2] & (batch[1] >= 0).any(dim=-1)).sum()),
                   "observed_bits": int(((batch[1] >= 0) & batch[2][:, :, None]).sum())}


def calibrate_flat(model, batch, temperatures=(.5, .75, 1., 1.5, 2., 3.)):
    """Select temperature only on a disjoint sensor-only calibration split."""
    with torch.no_grad():
        logits = logits_for_batch(model, batch)
        losses = {str(float(t)): float(sensor_nll(logits, batch[1], batch[2], float(t))) for t in temperatures}
    winner = min(losses, key=losses.get)
    return float(winner), {"temperature": float(winner), "nll_by_temperature": losses,
                           "episodes": int(batch[0].shape[1]),
                           "measured_events": int((batch[2] & (batch[1] >= 0).any(dim=-1)).sum())}
