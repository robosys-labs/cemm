"""Small learned binding alternatives; no lexicon, role labels or inverse rule.

Supplied inductive bias: lexical content is pooled independently of identity-token
layout, then two learned scalars interact. Their signs have no assigned meaning.
This is a rank-one interaction hypothesis for the existing two-order interface,
not a general parser or a claim of structural transfer. Historical models stay
unchanged. The additive arm removes the interaction without changing its inputs.
"""
import torch
from torch import nn

from .bilingual_model import OrderEncoder, _features
from .joint_objective import DTYPE, require

ARMS = ('gru', 'factor', 'additive')
PARAMETERS = {'gru': 474, 'factor': 89, 'additive': 91}


def factor_inputs(features):
    """Split existing generic features, without inspecting words or entity IDs."""
    _features(features)
    layout = features[:, :, 0]
    require(bool(((layout == 0) | (layout == 1)).all()) and
            bool((layout.sum(-1) == 2).all()), 'two identity markers required')
    lexical = features[:, :, 1:]
    require(bool((lexical * layout[:, :, None] == 0).all()),
            'identity tokens cannot contain lexical features')
    # Masked lexical features may be all zero; they are not missing identities.
    return lexical.sum(1), layout


class FactorOrderEncoder(nn.Module):
    """Learned content/layout bottlenecks with bilinear or additive readout."""
    def __init__(self, *, interaction=True):
        super().__init__()
        require(type(interaction) is bool, 'interaction must be boolean')
        self.interaction = interaction
        self.lexical = nn.Sequential(nn.Linear(8, 8, dtype=DTYPE), nn.Tanh(),
                                     nn.Linear(8, 1, dtype=DTYPE), nn.Tanh())
        self.layout = nn.Sequential(nn.Linear(3, 1, dtype=DTYPE), nn.Tanh())
        self.order = (nn.Bilinear(1, 1, 2, dtype=DTYPE) if interaction else
                      nn.Linear(2, 2, dtype=DTYPE))

    def forward(self, features):
        lexical, layout = factor_inputs(features)
        content, binding = self.lexical(lexical), self.layout(layout)
        logits = (self.order(content, binding) if self.interaction else
                  self.order(torch.cat((content, binding), -1)))
        return logits.log_softmax(-1)


def encoder(arm, seed):
    """Fresh, deterministic arms without changing the caller's CPU RNG state."""
    require(type(arm) is str and arm in ARMS, 'unknown binding arm')
    require(type(seed) is int and 0 <= seed < 2 ** 63, 'invalid binding seed')
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        model = OrderEncoder() if arm == 'gru' else FactorOrderEncoder(interaction=arm == 'factor')
    require(sum(p.numel() for p in model.parameters()) == PARAMETERS[arm] <= 474,
            'binding parameter inventory changed')
    return model
