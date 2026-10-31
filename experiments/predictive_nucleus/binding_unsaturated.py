"""Opt-in 89-parameter bottleneck ablation; not an evaluated replacement.

The closed factor-v1 fits saturate some incorrect lexical scalars. That suggests,
but does not establish, an optimization cause. Remove only the terminal lexical
and layout tanh operations; retain the hidden lexical tanh, all learned tensors,
features and bilinear readout. No word, role, language or inverse rule is supplied.
Historical encoders, trainer registry and checkpoint constructors remain untouched.
"""
import torch

from .binding_model import FactorOrderEncoder, factor_inputs
from .joint_objective import require


class UnsaturatedFactorOrderEncoder(FactorOrderEncoder):
    def __init__(self):
        super().__init__(interaction=True)

    def forward(self, features):
        lexical, layout = factor_inputs(features)
        content = self.lexical[2](self.lexical[1](self.lexical[0](lexical)))
        binding = self.layout[0](layout)
        logits = self.order(content, binding)
        require(bool(torch.isfinite(logits).all()), 'nonfinite unsaturated binding logits')
        return logits.log_softmax(-1)


def unsaturated_encoder(seed):
    """Same initial tensors as factor-v1 at the same seed; preserve caller RNG."""
    require(type(seed) is int and 0 <= seed < 2 ** 63, 'invalid binding seed')
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(seed)
        model = UnsaturatedFactorOrderEncoder()
    require(sum(p.numel() for p in model.parameters()) == 89, 'parameter inventory changed')
    return model
