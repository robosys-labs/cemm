"""Outcome-trained two-role predictive kernel, with anonymous persistent mode.

No world/oracle imports: contact dynamics and set-intervention outcomes are
trained from *sensor-visible* before/after samples only. Two role hypotheses
share the SAME neural kernel with swapped ordered participant slots; the
predeclared symmetry is a supplied inductive bias, not a learned role label.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import random

import torch
from torch import nn
from torch.nn import functional as F


class ContactKernel(nn.Module):
    def __init__(self, hidden: int = 32):
        super().__init__()
        self.pair = nn.Sequential(nn.Linear(2, hidden), nn.Tanh(),
                                  nn.Linear(hidden, hidden), nn.Tanh(),
                                  nn.Linear(hidden, 4))
        self.set_net = nn.Sequential(nn.Linear(2, hidden), nn.Tanh(), nn.Linear(hidden, 2))

    def pair_logits(self, bits: torch.Tensor) -> torch.Tensor:
        return self.pair(bits.float())

    def param_count(self):
        return sum(p.numel() for p in self.parameters())

    @torch.no_grad()
    def freeze(self) -> "FrozenKernel":
        """Numerical cache of learned weights, NEVER simulator lookup-table import."""
        contact = {}
        intervention = {}
        for a in (0, 1):
            for b in (0, 1):
                for h in (0, 1):
                    inp = torch.tensor([[a, b] if h == 0 else [b, a]], dtype=torch.float32)
                    probs = self.pair_logits(inp).softmax(-1).squeeze(0)
                    if h == 1:
                        probs = probs[torch.tensor([0, 2, 1, 3])]
                    contact[a, b, h] = tuple(float(x) for x in probs)
                intervention[a, b] = tuple(float(x) for x in self.set_net(
                    torch.tensor([[a, b]], dtype=torch.float32)).softmax(-1).squeeze(0))
        return FrozenKernel(contact, intervention)


@dataclass(frozen=True)
class FrozenKernel:
    learned_contact: dict[tuple[int, int, int], tuple[float, ...]]
    learned_set: dict[tuple[int, int], tuple[float, ...]]

    def contact(self, a, b, hypothesis):
        return self.learned_contact[a, b, hypothesis]

    def intervention(self, previous, value):
        return self.learned_set[previous, value]


def sensor_only_samples(episode):
    """Read ONLY public pre/post observation pairs. Hidden bits never imputed.

    All contacts within an episode share one latent mode at training time.
    Incomplete pairs contribute no supervised observation; missing != zero.
    """
    contacts, interventions = [], []
    for i in range(len(episode.actions)):
        pre = {m["id"]: m["bit"] for m in episode.learner_turn(i)["observation"]["measurements"]}
        post = {m["id"]: m["bit"] for m in episode.reveal_after_prediction(i)["measurements"]}
        action = episode.learner_turn(i)["action"]
        kind = action["kind"]
        ids = action["participants"]
        if kind == "contact" and len(ids) == 2 and len(set(ids)) == 2 and all(key in pre and key in post for key in ids):
            contacts.append((pre[ids[0]], pre[ids[1]], post[ids[0]], post[ids[1]]))
        elif kind == "set" and ids[0] in pre and ids[0] in post:
            interventions.append((pre[ids[0]], action["value"], post[ids[0]]))
    return contacts, interventions


@dataclass(frozen=True)
class Samples:
    episodes: int
    contact: torch.Tensor
    episode_id: torch.Tensor
    intervention: torch.Tensor


def build_samples(episodes) -> Samples:
    contacts, indices, sets = [], [], []
    n = 0
    for episode in episodes:
        c, s = sensor_only_samples(episode)
        if c:
            indices.extend([n] * len(c))
            contacts.extend(c)
            n += 1
        sets.extend(s)
    if not contacts or not sets:
        raise ValueError("insufficient sensor-visible contrast samples")
    return Samples(n, torch.tensor(contacts, dtype=torch.long),
                   torch.tensor(indices, dtype=torch.long), torch.tensor(sets, dtype=torch.long))


def fit_kernel(samples: Samples, seed: int, steps: int = 300, learning_rate: float = 0.02) -> tuple[ContactKernel, dict]:
    """Unsupervised episode-level marginal likelihood, not gold latent labels.

    Loss = -sum_episodes log(.5 P(events|mode 0)+.5 P(events|mode 1)).
    Each mode explains a whole episode, never sampled independently per edge.
    """
    torch.manual_seed(seed)
    model = ContactKernel()
    opt = torch.optim.Adam(model.parameters(), lr=learning_rate)
    data = samples.contact
    inputs = data[:, :2].float()
    targets = data[:, 2] * 2 + data[:, 3]
    inverted_targets = data[:, 3] * 2 + data[:, 2]
    swapped_inputs = inputs[:, [1, 0]]
    set_samples = samples.intervention
    last = None
    for _ in range(steps):
        log0 = F.log_softmax(model.pair_logits(inputs), dim=-1).gather(1, targets[:, None]).squeeze(1)
        log1 = F.log_softmax(model.pair_logits(swapped_inputs), dim=-1).gather(1, inverted_targets[:, None]).squeeze(1)
        total0 = torch.zeros(samples.episodes).index_add(0, samples.episode_id, log0)
        total1 = torch.zeros(samples.episodes).index_add(0, samples.episode_id, log1)
        per_episode = torch.stack((total0, total1), dim=1)
        contact_loss = -(torch.logsumexp(per_episode, dim=1) - math.log(2)).mean()
        set_logits = model.set_net(set_samples[:, :2].float())
        set_loss = F.cross_entropy(set_logits, set_samples[:, 2])
        loss = contact_loss + 0.3 * set_loss
        opt.zero_grad()
        loss.backward()
        opt.step()
        last = (float(contact_loss.detach()), float(set_loss.detach()))
    return model, {"gradient_steps": steps, "episodes_with_complete_contact": samples.episodes,
                   "contact_samples": len(samples.contact), "interventions": len(samples.intervention),
                   "train_marginal_nll": last[0], "train_set_nll": last[1],
                   "parameters": model.param_count()}


def shuffle_contact_outcomes(samples: Samples, seed: int) -> Samples:
    """Training negative control: preserve inputs, break causal outcome pairing."""
    generator = torch.Generator().manual_seed(seed)
    disrupted = samples.contact.clone()
    permutation = torch.randperm(len(disrupted), generator=generator)
    disrupted[:, 2:] = samples.contact[permutation, 2:]
    return Samples(samples.episodes, disrupted, samples.episode_id.clone(),
                   samples.intervention.clone())
