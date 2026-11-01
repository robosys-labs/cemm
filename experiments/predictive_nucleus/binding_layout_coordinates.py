"""Opt-in response-coordinate hypothesis; not scientifically evaluated.

On the three legal identity masks M=11^T-I, the affine layout map is
l=Mw+b1. Its parameter Jacobian has JJ^T=I+2*11^T: common-mode eigenvalue
7 versus contrast eigenvalue 1 under unpreconditioned gradient descent.
Three unconstrained learned responses remove that coupling and one redundant
parameter. This is not an exact Adam metric or a demonstrated optimization fix.

Every q in R^3 remains realizable (old w=-q, b=sum(q)). No sign, zero mean,
word meaning or role is prescribed. Equivalence is only for the existing legal
identity masks, not arbitrary feature vectors or a general language model.
"""
import torch
from torch import nn

from .binding_model import factor_inputs
from .binding_unsaturated import UnsaturatedFactorOrderEncoder
from .binding_centered_init import centered_encoder
from .joint_objective import DTYPE, require


class LayoutCoordinateEncoder(UnsaturatedFactorOrderEncoder):
    def __init__(self):
        super().__init__()
        self.layout = nn.Sequential(nn.Linear(3, 1, bias=False, dtype=DTYPE))

    def forward(self, features):
        lexical, layout = factor_inputs(features)
        content = self.lexical[2](self.lexical[1](self.lexical[0](lexical)))
        binding = self.layout[0](1. - layout)
        logits = self.order(content, binding)
        require(bool(torch.isfinite(logits).all()), 'nonfinite layout-coordinate logits')
        return logits.log_softmax(-1)


def coordinate_encoder(seed):
    """Match centered initial responses; preserve the other 85 scalars and RNG."""
    reference = centered_encoder(seed)
    with torch.random.fork_rng(devices=[]):
        model = LayoutCoordinateEncoder()
    masks = torch.ones(3, 3, dtype=DTYPE) - torch.eye(3, dtype=DTYPE)
    with torch.no_grad():
        model.lexical.load_state_dict(reference.lexical.state_dict())
        model.order.load_state_dict(reference.order.state_dict())
        model.layout[0].weight.copy_(reference.layout[0](masks).T)
    require(sum(p.numel() for p in model.parameters()) == 88, 'parameter inventory changed')
    return model
