"""Temperature calibration from a separate *sensor-only* calibration split.

No oracle orientation or hidden truth enters this procedure. Choose one scalar
using complete observed contact pairs, with episode-consistent latent mixture.
All later diagnostics report the selected temperature and its fit sample size.
"""
from __future__ import annotations
from dataclasses import dataclass
import math

import torch
from torch.nn import functional as F
from .latent_model import FrozenKernel, ContactKernel, Samples


@dataclass(frozen=True)
class TemperedKernel:
    uncalibrated: FrozenKernel
    temperature: float

    def _rescale(self, probs):
        weights = [max(float(p), 1e-12) ** (1.0 / self.temperature) for p in probs]
        total = sum(weights)
        return tuple(x / total for x in weights)

    def contact(self, a, b, hypothesis):
        return self._rescale(self.uncalibrated.contact(a, b, hypothesis))

    def intervention(self, previous, value):
        return self._rescale(self.uncalibrated.intervention(previous, value))


def contact_mixture_nll(model: ContactKernel, samples: Samples, temperature: float) -> float:
    if temperature <= 0:
        raise ValueError("positive temperature required")
    data = samples.contact
    x = data[:, :2].float()
    with torch.no_grad():
        p0 = F.log_softmax(model.pair_logits(x) / temperature, dim=-1)
        p1 = F.log_softmax(model.pair_logits(x[:, [1, 0]]) / temperature, dim=-1)
        i0 = data[:, 2] * 2 + data[:, 3]
        i1 = data[:, 3] * 2 + data[:, 2]
        lp0 = p0.gather(1, i0[:, None]).squeeze(1)
        lp1 = p1.gather(1, i1[:, None]).squeeze(1)
        total0 = torch.zeros(samples.episodes).index_add(0, samples.episode_id, lp0)
        total1 = torch.zeros(samples.episodes).index_add(0, samples.episode_id, lp1)
        nll = -(torch.logsumexp(torch.stack((total0, total1), -1), -1) - math.log(2)).mean()
        return float(nll)


def calibrate(model: ContactKernel, calibration: Samples, temperatures=(0.5, 0.75, 1., 1.5, 2., 3.)):
    """Never call with in-family or OOD sealed challenges."""
    candidates = {str(float(t)): contact_mixture_nll(model, calibration, float(t)) for t in temperatures}
    winning = min(candidates, key=lambda k: candidates[k])
    temp = float(winning)
    return TemperedKernel(model.freeze(), temp), {"temperature": temp,
        "calibration_contact_events": len(calibration.contact),
        "calibration_episodes": calibration.episodes, "nll_by_temperature": candidates}
