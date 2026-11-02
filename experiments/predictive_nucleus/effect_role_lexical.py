"""Frozen grounded vocabulary plus independent probabilistic acquisition slots.

Identity membership supplies provenance, never an action label. Legacy support
is inherited from the accepted two-action parent. Each newly registered identity
learns an effect logit and a role coordinate from the observed objective only.
Unregistered raw tokens remain blocked by the existing registry tokenizer.
"""
import math

import torch
from torch import nn

from . import acceptance_contract as c, effect_role_model as prior
from .bilingual_model import SequenceControl
from .binding_layout_coordinates import LayoutCoordinateEncoder
from .binding_model import factor_inputs
from .joint_objective import DTYPE, require


def inherited_ids(registry):
    prior.validate_registry(registry)
    return sorted(registry['tokens'][token]['id'] for token in registry['legacy_tokens'])


class LexicalEffectRoleEncoder(nn.Module):
    def __init__(self, parent, registry, legacy_ids):
        super().__init__()
        prior.validate_registry(registry)
        require(type(parent) is LayoutCoordinateEncoder and type(legacy_ids) is list and
                legacy_ids == inherited_ids(registry), 'explicit inherited identity inventory differs')
        self.parent = parent.eval().requires_grad_(False)
        self.registry_sha256 = c.digest(registry)
        self.legacy_ids = tuple(legacy_ids)
        self.new_ids = tuple(sorted(record['id'] for record in registry['tokens'].values()
                                    if record['id'] not in self.legacy_ids))
        require(len(self.new_ids) == 2, 'two prospective acquisition identities required')
        # Rows are exact identities, not character-derived meanings. Both columns
        # start at zero independently; no shared unknown parameter is introduced.
        self.new_coordinates = nn.Parameter(torch.zeros(2, 2, dtype=DTYPE))
        self._identity_by_features = {tuple(record['features']): record['id']
                                     for record in registry['tokens'].values()}
        require((0.,) * 8 not in self._identity_by_features, 'masked feature sentinel collides with an identity')
        self._new_rows = {identity: row for row, identity in enumerate(self.new_ids)}

    def train(self, mode=True):
        super().train(mode)
        self.parent.eval()
        return self

    def forward(self, features):
        lexical, layout = factor_inputs(features)
        require(not self.parent.training and all(not p.requires_grad and p.grad is None
            for p in self.parent.parameters()), 'inherited role model must remain frozen')
        legacy, acquired, slots = [], [], []
        for row, values in enumerate(lexical.detach().tolist()):
            key = tuple(values)
            if key == (0.,) * 8: continue  # Explicit current-word masking, not a raw unknown token.
            require(key in self._identity_by_features, 'features have no registered lexical identity')
            identity = self._identity_by_features[key]
            if identity in self._new_rows:
                acquired.append(row); slots.append(self._new_rows[identity])
            else: legacy.append(row)
        result = torch.full((len(features), 4), -math.log(4.), dtype=DTYPE)
        if legacy:
            rows = torch.tensor(legacy, dtype=torch.long)
            old = self.parent(features.index_select(0, rows))
            preserved = torch.cat((old, torch.full_like(old, -torch.inf)), -1)
            result = result.index_copy(0, rows, preserved)
        if acquired:
            rows = torch.tensor(acquired, dtype=torch.long)
            coordinates = self.new_coordinates[torch.tensor(slots, dtype=torch.long)]
            effect, role = coordinates[:, :1], coordinates[:, 1:]
            binding = self.parent.layout[0](1. - layout.index_select(0, rows))
            logits = self.parent.order(role, binding) - self.parent.order.bias
            require(bool(torch.isfinite(logits).all()) and bool(torch.isfinite(effect).all()),
                    'nonfinite acquired lexical coordinate')
            roles = logits.log_softmax(-1)
            families = torch.cat((torch.zeros_like(effect), effect), -1).log_softmax(-1)
            joint = torch.cat((families[:, :1] + roles, families[:, 1:] + roles), -1)
            result = result.index_copy(0, rows, joint)
        return result


def encoder(seed, parent_state, registry, legacy_ids):
    """Keep all 88 original scalars live and frozen; add four trainable zeros."""
    require(type(seed) is int and 0 <= seed < 2 ** 63 and isinstance(parent_state, dict),
            'valid seed and explicit parent tensors required')
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        parent = LayoutCoordinateEncoder()
    expected = parent.state_dict(); require(set(expected) == set(parent_state), 'parent tensor inventory differs')
    restored = {}
    for name, target in expected.items():
        value = parent_state[name]
        if isinstance(value, torch.Tensor):
            require(value.dtype == DTYPE and value.device.type == 'cpu', 'parent tensor dtype/device differs')
        value = torch.as_tensor(value, dtype=DTYPE)
        require(value.shape == target.shape and bool(torch.isfinite(value).all()), 'parent tensor geometry differs')
        restored[name] = value
    parent.load_state_dict(restored, strict=True)
    result = LexicalEffectRoleEncoder(parent, registry, legacy_ids)
    require(sum(p.numel() for p in result.parameters()) == 92 and
        sum(p.numel() for p in result.parameters() if p.requires_grad) == 4 and
        not list(result.buffers()), 'protected/learned state inventory differs')
    return result


def learner(arm, seed, parent_state, registry, legacy_ids):
    require(arm in ('grounded', 'parser', 'text_only') and type(seed) is int and 0 <= seed < 2 ** 63,
            'valid learner and seed required')
    if arm != 'text_only': return encoder(seed, parent_state, registry, legacy_ids)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        return SequenceControl()
