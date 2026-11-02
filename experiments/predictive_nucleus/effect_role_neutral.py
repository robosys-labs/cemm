"""Probability-neutral expansion of the accepted contact selector.

The inherited contact distribution is conditional evidence within its family.
Its arbitrary common logit shift cannot determine the prior for the new family.
All 88 inherited scalars are copied unchanged and the four new scalars are zero.
At initialization each family has mass one half; subsequent SET scores are free.
"""
import math

import torch

from . import effect_role_model as prior
from .bilingual_model import SequenceControl
from .binding_model import factor_inputs
from .joint_objective import require


class ProbabilityNeutralEncoder(prior.EffectRoleEncoder):
    def forward(self, features):
        lexical, layout = factor_inputs(features)
        content = self.lexical[2](self.lexical[1](self.lexical[0](lexical)))
        binding = self.layout[0](1. - layout)
        logits = self.order(content, binding)
        require(bool(torch.isfinite(logits).all()), 'nonfinite probability-neutral logits')
        contact = logits[:, :2].log_softmax(-1) + math.log(2.)
        return torch.cat((contact, logits[:, 2:]), -1).log_softmax(-1)


def encoder(seed, parent_state):
    """Reuse the exact v1 tensor initialization without changing caller RNG."""
    reference = prior.encoder(seed, parent_state)
    with torch.random.fork_rng(devices=[]):
        result = ProbabilityNeutralEncoder()
    result.load_state_dict(reference.state_dict(), strict=True)
    require(sum(p.numel() for p in result.parameters()) == 92, 'parameter inventory changed')
    return result


def learner(arm, seed, parent_state):
    """Normalize grounded/parser scores; retain the exact text-only control."""
    require(arm in ('grounded', 'parser', 'text_only'), 'unknown learner')
    require(type(seed) is int and 0 <= seed < 2 ** 63, 'valid model seed required')
    if arm != 'text_only': return encoder(seed, parent_state)
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        return SequenceControl()
