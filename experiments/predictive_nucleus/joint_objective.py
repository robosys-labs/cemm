"""One full-sensor, full-world objective for isolated three-entity comparisons.

No simulator or historical model imports. Two persistent latent modes, action
locality and optional role-swap tying/persistence are SUPPLIED model biases.
This is not a general partially observed nucleus or a G1 admission runner.
"""
from dataclasses import dataclass
from hashlib import sha256
from itertools import product
import json
import math
from time import perf_counter, process_time

import torch
from torch import nn
from torch.nn import functional as F

WORLDS = tuple(product((0, 1), repeat=3))
KINDS = ("contact", "set", "observe")
DTYPE = torch.float64


def require(condition, message):
    if not condition:
        raise ValueError(message)


def world_index(bits):
    return (bits.long() * bits.new_tensor([4, 2, 1], dtype=torch.long)).sum(-1)


def fingerprint(tensors):
    digest = sha256()
    for name, value in sorted(tensors.items()):
        value = value.detach().cpu().contiguous()
        meta = json.dumps([name, str(value.dtype), list(value.shape)]).encode()
        raw = bytes(value.view(torch.uint8).reshape(-1).tolist())
        for part in (meta, raw):
            digest.update(len(part).to_bytes(8, "big"))
            digest.update(part)
    return digest.hexdigest()


@dataclass(frozen=True)
class SensorBatch:
    observations: torch.Tensor  # (time+1, episode, 3), full measured bits
    actions: torch.Tensor       # (time, episode, 4): kind, first, second, value

    def validate(self):
        x, a = self.observations, self.actions
        require(x.device.type == a.device.type == "cpu", "CPU tensors required")
        require(x.dtype == DTYPE and a.dtype == torch.long, "unexpected batch dtype")
        require(x.ndim == a.ndim == 3 and x.shape[2] == 3 and a.shape[2] == 4 and
                x.shape[:2] == (a.shape[0] + 1, a.shape[1]) and
                a.shape[0] > 0 and a.shape[1] > 0, "invalid batch shape")
        require(bool(((x == 0) | (x == 1)).all()), "full binary observations required")
        k, first, second, value = a.unbind(-1)
        valid = ((k == 0) & (first >= 0) & (first < 3) & (second >= 0) &
                 (second < 3) & (first != second) & (value == -1))
        valid |= ((k == 1) & (first >= 0) & (first < 3) & (second == -1) &
                  ((value == 0) | (value == 1)))
        valid |= (k == 2) & (first == -1) & (second == -1) & (value == -1)
        require(bool(valid.all()), "invalid action encoding")
        return self

    def digest(self):
        return fingerprint({"observations": self.observations, "actions": self.actions})


def batch_histories(histories):
    """Copy only delivered sensor/action records; never inspect oracle fields.

    Equal-length, complete noiseless three-ID histories only. Missingness is
    rejected, not imputed. Offline arrays are inspectable, not secure custody.
    """
    observations, actions = [], []
    for history in histories:
        count = len(history.actions)
        require(count > 0, "empty history")
        ids, previous, states, events = None, None, [], []
        def read(record, time):
            require(type(record) is dict and set(record) == {"t", "measurements"} and
                    type(record["t"]) is int and record["t"] == time and
                    type(record["measurements"]) is list, "invalid sensor envelope")
            values = {}
            for item in record["measurements"]:
                require(type(item) is dict and set(item) == {"id", "bit"} and
                        type(item["id"]) is str and bool(item["id"]) and
                        item["id"] not in values and type(item["bit"]) is int and
                        item["bit"] in (0, 1), "invalid measurement")
                values[item["id"]] = item["bit"]
            require(len(values) == 3 and (ids is None or set(values) == set(ids)),
                    "exactly three unchanged identities must be measured")
            return values
        for t in range(count):
            turn = history.learner_turn(t)
            require(type(turn) is dict and set(turn) == {"observation", "action"}, "invalid turn")
            pre = read(turn["observation"], t)
            if ids is None:
                ids = tuple(sorted(pre))
                states.append(tuple(pre[name] for name in ids))
            require(previous is None or pre == previous, "discontinuous sensor history")
            action = turn["action"]
            require(type(action) is dict and type(action.get("kind")) is str and
                    action["kind"] in KINDS, "invalid action kind")
            kind = action["kind"]
            require(set(action) == ({"kind", "participants", "value"} if kind == "set" else
                                    {"kind", "participants"}), "invalid action envelope")
            members = action["participants"]
            require(type(members) in (list, tuple) and all(type(n) is str and n in ids for n in members),
                    "unknown action identity")
            expected = {"contact": 2, "set": 1, "observe": 0}[kind]
            require(len(members) == expected and len(set(members)) == len(members), "invalid operands")
            value = action.get("value", -1)
            require(type(value) is int and (kind != "set" or value in (0, 1)), "invalid intervention")
            events.append((KINDS.index(kind), ids.index(members[0]) if members else -1,
                           ids.index(members[1]) if len(members) == 2 else -1, value))
            # Capture the pre-action record before requesting any next reading.
            previous = read(history.reveal_after_prediction(t), t + 1)
            states.append(tuple(previous[name] for name in ids))
        observations.append(states)
        actions.append(events)
    require(bool(actions) and len({len(a) for a in actions}) == 1, "equal nonempty histories required")
    return SensorBatch(torch.tensor(observations, dtype=DTYPE).transpose(0, 1).contiguous(),
                       torch.tensor(actions, dtype=torch.long).transpose(0, 1).contiguous()).validate()


def _mlp(inputs, hidden, outputs, *, deep=False):
    layers = [nn.Linear(inputs, hidden, dtype=DTYPE), nn.Tanh()]
    if deep:
        layers.extend((nn.Linear(hidden, hidden, dtype=DTYPE), nn.Tanh()))
    return nn.Sequential(*layers, nn.Linear(hidden, outputs, dtype=DTYPE))


def persistence_support(pre, action, worlds):
    """Supplied unchanged-nonparticipant law, shared by BOTH model families."""
    kind, first, second, _ = action.unbind(-1)
    slots = torch.arange(3)[None, :]
    active = ((kind != 2)[:, None] & (slots == first[:, None])) | (
              (kind == 0)[:, None] & (slots == second[:, None]))
    return ((worlds[None] == pre[:, None, :]) | active[:, None, :]).all(-1)


class JointKernel(nn.Module):
    """Outcome-trained pair kernel, exact two-mode filtering, optional biases.

    No mode label or transition formula is supplied. Background outputs are
    either explicitly unchanged or learned from all full-state targets. The
    latter retains action locality/conditional factorization, not arbitrary
    dynamics. Removing swap tying does NOT remove entity-ID equivariance.
    """
    def __init__(self, *, persistence=False, role_tying=True, memory=True, hidden=16):
        super().__init__()
        require(all(type(v) is bool for v in (persistence, role_tying, memory)) and
                type(hidden) is int and hidden > 0, "invalid kernel configuration")
        self.persistence, self.role_tying, self.memory = persistence, role_tying, memory
        self.pair = _mlp(2, hidden, 4, deep=True)
        self.pair_other = None if role_tying else _mlp(2, hidden, 4, deep=True)
        self.intervention = _mlp(2, hidden, 2)
        self.background = None if persistence else _mlp(4, hidden, 2)
        self.register_buffer("worlds", torch.tensor(WORLDS, dtype=torch.long))

    def initial(self, n):
        return torch.full((n, 2), -math.log(2), dtype=DTYPE)

    def predict(self, pre, action, state):
        """Pure forecast; state and inputs are not mutated and no feedback is read."""
        n = pre.shape[0]
        kind, first, second, value = action.unbind(-1)
        first_safe, second_safe = first.clamp(min=0), second.clamp(min=0)
        rows = torch.arange(n)
        a, b = pre[rows, first_safe], pre[rows, second_safe]
        inputs = torch.stack((a, b), -1)
        pair0 = self.pair(inputs).log_softmax(-1)
        pair1 = (self.pair(inputs.flip(-1)).log_softmax(-1)[:, [0, 2, 1, 3]] if self.role_tying
                 else self.pair_other(inputs).log_softmax(-1))
        candidates = self.worlds[None].expand(n, -1, -1)
        wa = candidates.gather(2, first_safe[:, None, None].expand(-1, 8, 1)).squeeze(-1)
        wb = candidates.gather(2, second_safe[:, None, None].expand(-1, 8, 1)).squeeze(-1)
        pair_index = wa * 2 + wb
        contact = torch.stack((pair0.gather(1, pair_index), pair1.gather(1, pair_index)), 1)
        set_probs = self.intervention(torch.stack((a, value.clamp(min=0).to(DTYPE)), -1)).log_softmax(-1)
        set_worlds = set_probs.gather(1, wa)[:, None, :].expand(-1, 2, -1)
        local = torch.where((kind == 0)[:, None, None], contact,
                            torch.where((kind == 1)[:, None, None], set_worlds, 0.0))
        slots = torch.arange(3)[None, :]
        active = ((kind != 2)[:, None] & (slots == first[:, None])) | (
                  (kind == 0)[:, None] & (slots == second[:, None]))
        if self.persistence:
            possible = persistence_support(pre, action, self.worlds)
            background = torch.zeros(n, 8, dtype=DTYPE).masked_fill(~possible, -torch.inf)
        else:
            context = F.one_hot(kind, 3).to(DTYPE)[:, None, :].expand(-1, 3, -1)
            logits = self.background(torch.cat((pre[:, :, None], context), -1)).log_softmax(-1)
            per_bit = logits[:, None, :, :].expand(-1, 8, -1, -1).gather(
                3, candidates[:, :, :, None]).squeeze(-1)
            background = torch.where(active[:, None, :], 0.0, per_bit).sum(-1)
        conditional = local + background[:, None, :]
        prior = state if self.memory else self.initial(n)
        weighted = conditional + prior[:, :, None]
        impossible = torch.isneginf(weighted).all(1)
        # logsumexp(all -inf) has undefined derivatives; preserve exact zero
        # support without passing that undefined reduction to autograd.
        safe = weighted.masked_fill(impossible[:, None, :], 0.0)
        joint = safe.logsumexp(1).masked_fill(impossible, -torch.inf)
        return joint, weighted

    def receive(self, pending, post):
        index = world_index(post)
        evidence = pending.gather(2, index[:, None, None].expand(-1, 2, 1)).squeeze(-1)
        normalizer = evidence.logsumexp(-1, keepdim=True)
        require(bool(torch.isfinite(normalizer).all()), "observation outside model support")
        return evidence - normalizer if self.memory else self.initial(len(post))


class JointFlatGRU(nn.Module):
    """Unpadded three-ID GRU: 14 observed/action features, eight joint worlds.

    Sorted-ID slots are supplied addresses, not learned role labels. Unlike
    JointKernel this model has no exact ID-equivariance. Persistence can be supplied
    through the identical support mask used by JointKernel.
    """
    def __init__(self, hidden=8, *, persistence=False):
        super().__init__()
        require(type(hidden) is int and hidden > 0 and type(persistence) is bool, "invalid flat configuration")
        self.hidden, self.persistence = hidden, persistence
        self.register_buffer("worlds", torch.tensor(WORLDS, dtype=torch.long))
        self.cell = nn.GRUCell(14, hidden, dtype=DTYPE)
        self.head = nn.Linear(hidden, 8, dtype=DTYPE)

    def initial(self, n):
        return torch.zeros(n, self.hidden, dtype=DTYPE)

    def predict(self, pre, action, state):
        kind, first, second, value = action.unbind(-1)
        slots = torch.arange(3)[None, :]
        features = torch.cat((pre, (slots == first[:, None]).to(DTYPE),
            (slots == second[:, None]).to(DTYPE), F.one_hot(kind, 3).to(DTYPE),
            ((kind == 1)[:, None] & (value[:, None] == torch.arange(2)[None])).to(DTYPE)), -1)
        hidden = self.cell(features, state)
        logits = self.head(hidden)
        if self.persistence:
            logits = logits.masked_fill(~persistence_support(pre, action, self.worlds), -torch.inf)
        return logits.log_softmax(-1), hidden

    def receive(self, pending, post):
        # The next predict consumes the full post-action reading as its pre.
        return pending


def joint_log_probabilities(model, batch):
    """Shared causal loop; each forecast precedes receiving its own target."""
    batch.validate()
    state, predictions = model.initial(batch.actions.shape[1]), []
    for t, action in enumerate(batch.actions):
        logp, pending = model.predict(batch.observations[t], action, state)
        require(logp.shape == (batch.actions.shape[1], 8) and
                not bool((torch.isnan(logp) | torch.isposinf(logp)).any()) and
                bool(torch.allclose(logp.logsumexp(-1), torch.zeros(len(logp), dtype=DTYPE),
                                    atol=1e-10, rtol=0)), "invalid joint distribution")
        predictions.append(logp)
        state = model.receive(pending, batch.observations[t + 1])
    return torch.stack(predictions)


def full_world_nll(logp, post):
    """Exactly one equally weighted joint-state log loss per measured event."""
    require(logp.shape[:-1] == post.shape[:-1] and logp.shape[-1] == 8 and post.shape[-1] == 3,
            "loss shape mismatch")
    require(bool(((post == 0) | (post == 1)).all()), "complete binary targets required")
    require(not bool((torch.isnan(logp) | torch.isposinf(logp)).any()) and
            bool(torch.allclose(logp.logsumexp(-1), torch.zeros_like(logp[..., 0]), atol=1e-10, rtol=0)),
            "loss requires normalized log probabilities")
    loss = F.nll_loss(logp.reshape(-1, 8), world_index(post).reshape(-1), reduction="mean")
    require(bool(torch.isfinite(loss)), "nonfinite full-world loss")
    return loss


def fit(model, batch, *, updates, cpu_seconds, learning_rate=.02):
    """Common Adam loop, CPU ceiling and update ceiling; no evaluation/selection.

    Timed region includes forecasts, backward, optimizer and finite checks.
    Setup is separately measured. One step can overshoot; record it, never
    call equal ceilings equal consumed compute or equal update counts.
    """
    require(type(updates) is int and updates > 0 and type(cpu_seconds) in (int, float) and
            math.isfinite(cpu_seconds) and cpu_seconds > 0 and
            type(learning_rate) in (int, float) and math.isfinite(learning_rate) and learning_rate > 0,
            "invalid fit budget")
    batch.validate()
    require(all(p.device.type == "cpu" and p.dtype == DTYPE for p in model.parameters()),
            "CPU float64 model required")
    setup = perf_counter()
    initial = fingerprint(model.state_dict())
    data_before = batch.digest()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    setup_seconds = perf_counter() - setup
    start, cpu_start = perf_counter(), process_time()
    completed, loss_value, last_cpu = 0, None, 0.0
    while completed < updates and process_time() - cpu_start < cpu_seconds:
        step_start = process_time()
        optimizer.zero_grad(set_to_none=True)
        loss = full_world_nll(joint_log_probabilities(model, batch), batch.observations[1:])
        loss.backward()
        require(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in model.parameters()),
                "nonfinite or missing gradient")
        optimizer.step()
        require(all(bool(torch.isfinite(p).all()) for p in model.parameters()), "nonfinite parameter")
        completed += 1
        loss_value = float(loss.detach())
        last_cpu = process_time() - step_start
    cpu, wall = process_time() - cpu_start, perf_counter() - start
    require(completed > 0, "budget exhausted before any optimizer update")
    require(batch.digest() == data_before, "fit mutated delivered observations/actions")
    return {"parameters": sum(p.numel() for p in model.parameters()), "completed_updates": completed,
            "requested_updates": updates, "stop_reason": "update_limit" if completed == updates else "cpu_limit",
            "setup_wall_seconds": setup_seconds, "fit_wall_seconds": wall, "fit_cpu_seconds": cpu,
            "cpu_ceiling_seconds": cpu_seconds, "cpu_overshoot_seconds": max(0.0, cpu - cpu_seconds),
            "last_step_cpu_seconds": last_cpu, "last_preupdate_nll": loss_value,
            "events_per_update": batch.actions.shape[0] * batch.actions.shape[1],
            "training_input_sha256": data_before, "initial_weights_sha256": initial,
            "final_weights_sha256": fingerprint(model.state_dict())}
