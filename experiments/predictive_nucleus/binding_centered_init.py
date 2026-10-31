"""Opt-in, untested research intervention: center only initial layout responses.

Three legal identity-marker layouts each contain two ones. Their mean is
(2/3, 2/3, 2/3); subtracting the corresponding initial response changes one
bias scalar. It assigns no word, ordering, role or polarity to a layout.
The bias remains trainable and inference is the unchanged unsaturated model.
This is a geometry-informed initialization hypothesis, not a learned result.
"""
import torch

from .binding_unsaturated import unsaturated_encoder


def centered_encoder(seed):
    """Keep 88/89 initial scalars exactly; center the single layout bias."""
    model = unsaturated_encoder(seed)
    with torch.no_grad():
        model.layout[0].bias.copy_(-(2.0 / 3.0) * model.layout[0].weight.sum(-1))
    return model
