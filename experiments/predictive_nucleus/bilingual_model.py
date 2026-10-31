"""Outcome-trained order binding over a frozen world; no language grammar.

Supplied: whitespace/event boundaries, exact roster identity lookup, two contact
operand permutations, and bounded character hashing. The GRU learns which
permutation the message denotes. No literal word selects an action or role.
"""
from functools import lru_cache
from hashlib import sha256

import torch
from torch import nn
from torch.nn import functional as F

from . import domain_contract as domain
from .domain_kernel import DomainKernel
from .joint_objective import DTYPE, require


@lru_cache(maxsize=256)
def _characters(token):
    pieces = list(token) + [token[i:i + 2] for i in range(len(token) - 1)]
    values = [0.] * 8
    for piece in pieces:
        code = sha256(piece.encode('utf-8')).digest()
        values[code[0] % 8] += 1. if code[1] & 1 else -1.
    return tuple(value / max(len(pieces), 1) for value in values)


def tokenize_batch(messages, rosters):
    """Return generic token features and identity occurrences, never gold roles."""
    require(type(messages) in (list, tuple) and type(rosters) in (list, tuple) and
            len(messages) == len(rosters) > 0, 'nonempty parallel messages/rosters required')
    features, mentions = [], []
    for message, roster in zip(messages, rosters, strict=True):
        require(type(roster) in (list, tuple) and 3 <= len(roster) <= 6 and
                all(type(name) is str and bool(name) and len(name.split()) == 1 for name in roster) and
                len(set(roster)) == len(roster), 'invalid opaque identity roster')
        require(type(message) is str and len(message) <= 512, 'bounded message required')
        tokens = message.split()
        require(len(tokens) == 3 and sum(token in roster for token in tokens) == 2,
                'one event requires two recognized identity occurrences and one lexical token')
        features.append([[1.] + [0.] * 8 if token in roster else [0.] + list(_characters(token))
                         for token in tokens])
        mentions.append([roster.index(token) for token in tokens if token in roster])
    return torch.tensor(features, dtype=DTYPE), torch.tensor(mentions, dtype=torch.long)


def _features(features):
    require(isinstance(features, torch.Tensor) and features.device.type == 'cpu' and
            features.dtype == DTYPE and features.ndim == 3 and features.shape[1:] == (3, 9) and
            len(features) > 0 and bool(torch.isfinite(features).all()), 'invalid token features')


def action_candidates(mentions):
    require(isinstance(mentions, torch.Tensor) and mentions.device.type == 'cpu' and
            mentions.dtype == torch.long and mentions.ndim == 2 and mentions.shape[1] == 2 and
            len(mentions) > 0 and bool(((mentions >= 0) & (mentions < 6)).all()),
            'invalid identity occurrences')
    actions = torch.full((len(mentions), 2, 4), -1, dtype=torch.long)
    actions[:, :, 0] = 0
    actions[:, 0, 1:3], actions[:, 1, 1:3] = mentions, mentions.flip(-1)
    return actions


class OrderEncoder(nn.Module):
    def __init__(self, hidden=8):
        super().__init__()
        require(type(hidden) is int and hidden > 0, 'positive hidden dimension required')
        self.sequence = nn.GRU(9, hidden, batch_first=True, dtype=DTYPE)
        self.order = nn.Linear(hidden, 2, dtype=DTYPE)

    def forward(self, features):
        _features(features)
        _, state = self.sequence(features)
        return self.order(state[-1]).log_softmax(-1)


def freeze_world(world):
    require(type(world) is DomainKernel and world.memory is True,
            'registered persistent-mode world required')
    world.eval().requires_grad_(False)
    return world


@torch.no_grad()
def frozen_options(world, pre, state, mentions):
    """Pure native forecasts for both orders, with no trainable world/history."""
    require(type(world) is DomainKernel and world.memory is True and
            all(not parameter.requires_grad for parameter in world.parameters()),
            'world weights must be explicitly frozen')
    entities = domain.validate_anchor(pre, 1)
    actions = action_candidates(mentions)
    require(len(actions) == len(pre) and bool((mentions < entities).all()), 'identity outside world')
    require(isinstance(state, torch.Tensor) and state.shape == (len(pre), 2), 'invalid mode state')
    _, pending = world.predict(pre.repeat_interleave(2, 0), actions.reshape(-1, 4),
                               state.repeat_interleave(2, 0))
    return pending.reshape(len(pre), 2, 2, 2 ** entities).detach()


def combine(order_logp, options):
    """Marginalize linguistic order, retaining shared mode/world dependence."""
    require(isinstance(order_logp, torch.Tensor) and order_logp.device.type == 'cpu' and
            order_logp.dtype == DTYPE and order_logp.ndim == 2 and order_logp.shape[1] == 2 and
            not bool((torch.isnan(order_logp) | torch.isposinf(order_logp)).any()) and
            bool((order_logp.logsumexp(-1).abs() <= 1e-10).all()), 'invalid order probabilities')
    require(isinstance(options, torch.Tensor) and options.device.type == 'cpu' and
            options.dtype == DTYPE and options.ndim == 4 and
            options.shape[:3] == (len(order_logp), 2, 2) and options.shape[3] in (8, 16, 32, 64) and
            not bool((torch.isnan(options) | torch.isposinf(options)).any()) and
            bool((options.flatten(2).logsumexp(-1).abs() <= 1e-10).all()),
            'invalid native order forecasts')
    pending = domain.safe_logsumexp(options + order_logp[:, :, None, None], 1)
    return domain.safe_logsumexp(pending, 1), pending


def make_context(pre, acquisition_pre, acquisition_action, acquisition_after, mentions, *, text_only=False):
    """The sequence control receives observed context, never a hidden mode label.

    48 features: current bits6, existence6, acquisition before6, ordered observed
    acquisition operands12, acquisition after6, current mention occurrences12.
    The text-only ablation retains only existence and mentioned identities.
    """
    entities = domain.validate_anchor(pre, 1)
    require(type(text_only) is bool, 'text-only flag must be boolean')
    for value in (acquisition_pre, acquisition_after):
        require(domain.validate_anchor(value, 1) == entities and value.shape == pre.shape,
                'acquisition geometry differs')
    domain.validate_action(acquisition_action, len(pre), entities)
    require(bool((acquisition_action[:, 0] == 0).all()), 'observed acquisition contact required')
    actions = action_candidates(mentions)
    require(len(actions) == len(pre) and bool((mentions < entities).all()), 'identity outside world')
    pad = lambda value: F.pad(value, (0, 6 - entities))
    onehot = lambda value: F.one_hot(value, 6).to(DTYPE).flatten(1)
    context = torch.cat((pad(pre), pad(torch.ones_like(pre)), pad(acquisition_pre),
        onehot(acquisition_action[:, 1:3]), pad(acquisition_after), onehot(mentions)), -1)
    if text_only:
        context[:, :6] = 0.
        context[:, 12:36] = 0.
    return context


class SequenceControl(nn.Module):
    """Direct neural outcome control; no acquired world or role supervision."""
    def __init__(self, hidden=6):
        super().__init__()
        require(type(hidden) is int and hidden > 0, 'positive hidden dimension required')
        self.sequence = nn.GRU(9, hidden, batch_first=True, dtype=DTYPE)
        self.context = nn.Linear(48, hidden, dtype=DTYPE)
        self.outcomes = nn.Linear(hidden, 64, dtype=DTYPE)

    def forward(self, features, context, entities):
        _features(features)
        domain.binary_worlds(entities)
        require(isinstance(context, torch.Tensor) and context.device.type == 'cpu' and
                context.dtype == DTYPE and context.shape == (len(features), 48) and
                bool(torch.isfinite(context).all()), 'invalid observed context')
        _, state = self.sequence(features)
        logits = self.outcomes(torch.tanh(state[-1] + self.context(context)))
        # Six-bit output geometry: absent trailing slots are zero, not unknown.
        indices = torch.arange(2 ** entities) * 2 ** (6 - entities)
        return logits[:, indices].log_softmax(-1)
