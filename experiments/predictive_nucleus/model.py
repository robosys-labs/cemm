"""Small object-shared recurrent predictor; no oracle, grammar or semantic rules.

The learner only receives opaque IDs, observed bits, ordered action operands
and next-observation feedback AFTER prediction. Role orientation stays latent.
"""
from __future__ import annotations

import torch
from torch import nn
from torch.nn import functional as F


class SharedWorldModel(nn.Module):
    def __init__(self, hidden: int = 24):
        super().__init__()
        self.dynamics = nn.Sequential(nn.Linear(hidden + 10, 48), nn.Tanh(),
                                      nn.Linear(48, 48), nn.Tanh(), nn.Linear(48, 1))
        self.recurrence = nn.GRUCell(10, hidden)
        self.hidden = hidden
        self.reset_done = False

    def reset(self, initial_observation: dict) -> None:
        """A new independent episode, with only its public first observation."""
        measurements = initial_observation["measurements"]
        names = [m["id"] for m in measurements]
        if len(names) != len(set(names)):
            raise ValueError("duplicate initial ID")
        self.memory = {m["id"]: torch.tensor(float(m["bit"])) for m in measurements}
        self.h = torch.zeros(self.hidden)
        self.t = initial_observation["t"]
        self.pending = None
        self.losses: list[torch.Tensor] = []
        self.reset_done = True

    def predict(self, turn: dict) -> dict[str, torch.Tensor]:
        if not self.reset_done or self.pending is not None:
            raise RuntimeError("reset / feedback required before prediction")
        current = turn["observation"]
        if current["t"] != self.t:
            raise ValueError("stale observation")
        if not {m["id"] for m in current["measurements"]}.issubset(self.memory):
            raise ValueError("unrecognized observation identity")
        for item in current["measurements"]:
            self.memory[item["id"]] = torch.tensor(float(item["bit"]))
        action = turn["action"]
        kind, participants = action["kind"], action["participants"]
        if kind not in ("contact", "set", "observe") or any(e not in self.memory for e in participants):
            raise ValueError("unknown action or identity")
        first = self.memory[participants[0]] if participants else torch.tensor(0.)
        second = self.memory[participants[1]] if len(participants) == 2 else torch.tensor(0.)
        xs = []
        order = sorted(self.memory)
        for key in order:
            # The two possible participant positions are symmetric shared inputs;
            # network weights, not a transition table, learn each position's role.
            features = torch.stack((self.memory[key], first, second,
                                    torch.tensor(float(key == participants[0]) if participants else 0.),
                                    torch.tensor(float(len(participants) > 1 and key == participants[1])),
                                    torch.tensor(float(kind == "contact")),
                                    torch.tensor(float(kind == "set")),
                                    torch.tensor(float(kind == "observe")),
                                    torch.tensor(float(action.get("value", 0) or 0)),
                                    torch.tensor(1.)))
            xs.append(torch.cat((features, self.h)))
        output = torch.sigmoid(self.dynamics(torch.stack(xs)).squeeze(-1))
        prediction = {key: output[i] for i, key in enumerate(order)}
        self.pending = (action, self.memory.copy(), prediction)
        return prediction

    def receive(self, feedback: dict) -> None:
        if self.pending is None or feedback["t"] != self.t + 1:
            raise RuntimeError("future / duplicate / out-of-order feedback")
        action, prior, prediction = self.pending
        revealed = {m["id"]: m["bit"] for m in feedback["measurements"]}
        if not set(revealed).issubset(prediction):
            raise ValueError("future observation introduced unseen identity")
        for name, bit in revealed.items():
            if bit not in (0, 1) or type(bit) is not int:
                raise ValueError("invalid observed bit")
            self.losses.append(F.binary_cross_entropy(prediction[name], torch.tensor(float(bit))))
        participants = action["participants"]
        feature = []
        for position in range(2):
            if len(participants) > position:
                name = participants[position]
                feature += [prior[name], torch.tensor(float(revealed.get(name, 0))),
                            torch.tensor(float(name in revealed))]
            else:
                feature += [torch.tensor(0.), torch.tensor(0.), torch.tensor(0.)]
        feature += [torch.tensor(float(action["kind"] == kind)) for kind in ("contact", "set", "observe")]
        feature += [torch.tensor(float(action.get("value", 0) or 0))]
        self.h = self.recurrence(torch.stack(feature), self.h)
        self.memory = {name: torch.tensor(float(revealed[name])) if name in revealed else probability
                       for name, probability in prediction.items()}
        self.pending = None
        self.t += 1

    def episode_loss(self) -> torch.Tensor:
        if self.pending is not None or not self.losses:
            raise RuntimeError("episode has unfinished / empty feedback")
        return torch.stack(self.losses).mean()

    def parameter_count(self) -> int:
        return sum(p.numel() for p in self.parameters())
