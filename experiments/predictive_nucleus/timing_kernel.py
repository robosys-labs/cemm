"""Exact two-contact composition around an unchanged learned DomainKernel.

Common snapshots use a SUPPLIED binary delta-union scheduler. Event outputs
are local proposals, conditional on one persistent mode; they are not two
constraints on a shared final variable. No source/target labels are accepted.
"""
import torch
from torch.nn import functional as F

from . import domain_contract as domain
from .domain_kernel import DomainKernel
from .joint_objective import DTYPE, require


class TimingKernel:
    def __init__(self, model):
        require(type(model) is DomainKernel and model.memory is True,
                'timing requires the registered persistent-mode DomainKernel')
        self.model = model

    @torch.no_grad()
    def predict(self, pre, contacts, timing, state):
        entities = domain.validate_anchor(pre, 1)
        batch, count = len(pre), 2 ** entities
        require(type(timing) is str and timing in ('ordered', 'common_snapshot'), 'invalid timing')
        require(isinstance(contacts, torch.Tensor) and contacts.device.type == 'cpu' and
                contacts.dtype == torch.long and contacts.ndim == 3 and contacts.shape[0] == batch and
                contacts.shape[1] in (1, 2) and contacts.shape[2] == 4, 'invalid contact group geometry')
        for action in contacts.unbind(1):
            domain.validate_action(action, batch, entities, allow_self=False)
            require(bool((action[:, 0] == 0).all()), 'contact-only timing group required')
        first, pending = self.model.predict(pre, contacts[:, 0], state)
        if contacts.shape[1] == 1: return first, pending
        worlds = torch.tensor(domain.binary_worlds(entities), dtype=torch.long)
        if timing == 'ordered':
            # Native transition 2 for every hypothetical world, with its mode
            # likelihood extracted before marginalization. No synthetic feedback.
            uniform = self.model.initial(batch * count)
            _, second = self.model.predict(worlds.repeat(batch, 1).to(DTYPE),
                contacts[:, 1].repeat_interleave(count, 0), uniform)
            likelihood = (second - uniform[:, :, None]).reshape(batch, count, 2, count).permute(0, 2, 1, 3)
            joint = (pending[:, :, :, None] + likelihood).logsumexp(2)
        else:
            outcomes = torch.tensor([(a, b) for a in range(4) for b in range(4)])
            pairs = [self.model._pairs(pre, contacts[:, event]) for event in range(2)]
            local = pairs[0][:, :, outcomes[:, 0]] + pairs[1][:, :, outcomes[:, 1]]
            changes = torch.zeros(batch, 16, entities, dtype=torch.bool)
            active = torch.zeros(batch, entities, dtype=torch.bool)
            rows = torch.arange(batch)[:, None]
            for event in range(2):
                for slot in range(2):
                    member = contacts[:, event, slot + 1]
                    values = (outcomes[:, event] >> (1 - slot)) & 1
                    delta = values[None, :] != pre[torch.arange(batch), member][:, None]
                    changes[rows, torch.arange(16)[None, :], member[:, None]] |= delta
                    active[torch.arange(batch), member] = True
            merged = pre.to(torch.long)[:, None, :] ^ changes.to(torch.long)
            agrees = ((merged[:, :, None, :] == worlds[None, None, :, :]) |
                      ~active[:, None, None, :]).all(-1)
            combined = local[:, :, :, None].masked_fill(~agrees[:, None, :, :], -torch.inf).logsumexp(2)
            if self.model.persistence:
                possible = ((worlds[None, :, :] == pre[:, None, :]) | active[:, None, :]).all(-1)
                background = torch.zeros(batch, count, dtype=DTYPE).masked_fill(~possible, -torch.inf)
            else:
                context = F.one_hot(torch.zeros(batch, dtype=torch.long), 3).to(DTYPE)
                logits = self.model.background(torch.cat((pre[:, :, None],
                    context[:, None, :].expand(-1, entities, -1)), -1)).log_softmax(-1)
                per_bit = logits[:, None, :, :].expand(-1, count, -1, -1).gather(3,
                    worlds[None, :, :, None].expand(batch, -1, -1, -1)).squeeze(-1)
                background = torch.where(active[:, None, :], 0., per_bit).sum(-1)
            joint = combined + background[:, None, :] + state[:, :, None]
        return joint.logsumexp(1), joint
