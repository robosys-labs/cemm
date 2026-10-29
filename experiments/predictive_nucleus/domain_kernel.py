"""Shared 3–6-entity successor; no simulator rules or newly trained parameters.

Self-contact conditions each learned pair factor on its two output slots naming
one physical variable. This supplied alias constraint is not evidence of learned
self-contact dynamics. Frozen three-entity sources/checkpoints stay unchanged.
"""
import torch
from torch import nn
from torch.nn import functional as F

from . import domain_contract as domain
from .joint_objective import JointKernel, DTYPE, fingerprint, require


class DomainKernel(JointKernel):
    supported_entities = (3, 4, 5, 6)
    supports_self_contact = True

    def __init__(self, *, persistence=False, role_tying=True, memory=True, hidden=16):
        super().__init__(persistence=persistence, role_tying=role_tying, memory=memory, hidden=hidden)
        del self.worlds  # Geometry is derived from each input, never a stale checkpoint buffer.

    def _pairs(self, pre, action):
        first, second = action[:, 1].clamp(min=0), action[:, 2].clamp(min=0)
        rows = torch.arange(len(pre))
        inputs = torch.stack((pre[rows, first], pre[rows, second]), -1)
        pair0 = self.pair(inputs).log_softmax(-1)
        pair1 = (self.pair(inputs.flip(-1)).log_softmax(-1)[:, [0, 2, 1, 3]] if self.role_tying
                 else self.pair_other(inputs).log_softmax(-1))
        return torch.stack((pair0, pair1), 1)

    @staticmethod
    def _alias_offsets(pair, action):
        alias = (action[:, 0] == 0) & (action[:, 1] == action[:, 2])
        offsets = torch.zeros_like(pair[:, :, 0])
        if bool(alias.any()):
            diagonal = pair[alias][:, :, [0, 3]]
            require(bool(torch.isfinite(diagonal).any(-1).all()) and
                    not bool((torch.isnan(diagonal) | torch.isposinf(diagonal)).any()),
                    'self-contact has empty or invalid diagonal support')
            # Normalize BEFORE mode mixing. Non-alias rows retain exact old arithmetic.
            offsets = offsets.index_copy(0, alias.nonzero().flatten(), diagonal.logsumexp(-1))
        return offsets

    def alias_log_mass(self, pre, action):
        """Pure per-mode retained diagonal log mass; zero for non-self actions."""
        entities = domain.validate_anchor(pre, 1)
        domain.validate_action(action, len(pre), entities)
        return self._alias_offsets(self._pairs(pre, action), action)

    def predict(self, pre, action, state):
        entities = domain.validate_anchor(pre, 1)
        domain.validate_action(action, len(pre), entities)
        n, count = len(pre), 2 ** entities
        require(isinstance(state, torch.Tensor) and state.device.type == 'cpu' and
                state.dtype == DTYPE and state.shape == (n, 2) and
                not bool((torch.isnan(state) | torch.isposinf(state)).any()) and
                bool((state.logsumexp(-1).abs() <= 1e-10).all()), 'invalid latent prior')
        worlds = torch.tensor(domain.binary_worlds(entities), dtype=torch.long)
        kind, first, second, value = action.unbind(-1)
        first_safe, second_safe = first.clamp(min=0), second.clamp(min=0)
        pair = self._pairs(pre, action)
        pair = pair - self._alias_offsets(pair, action)[:, :, None]
        candidates = worlds[None].expand(n, -1, -1)
        wa = candidates.gather(2, first_safe[:, None, None].expand(-1, count, 1)).squeeze(-1)
        wb = candidates.gather(2, second_safe[:, None, None].expand(-1, count, 1)).squeeze(-1)
        index = (wa * 2 + wb)[:, None, :].expand(-1, 2, -1)
        contact = pair.gather(2, index)
        a = pre[torch.arange(n), first_safe]
        set_probs = self.intervention(torch.stack((a, value.clamp(min=0).to(DTYPE)), -1)).log_softmax(-1)
        set_worlds = set_probs.gather(1, wa)[:, None, :].expand(-1, 2, -1)
        local = torch.where((kind == 0)[:, None, None], contact,
                            torch.where((kind == 1)[:, None, None], set_worlds, 0.0))
        slots = torch.arange(entities)[None, :]
        active = ((kind != 2)[:, None] & (slots == first[:, None])) | (
                  (kind == 0)[:, None] & (slots == second[:, None]))
        if self.persistence:
            possible = domain.persistence_support(pre, action, worlds)
            background = torch.zeros(n, count, dtype=DTYPE).masked_fill(~possible, -torch.inf)
        else:
            context = F.one_hot(kind, 3).to(DTYPE)[:, None, :].expand(-1, entities, -1)
            logits = self.background(torch.cat((pre[:, :, None], context), -1)).log_softmax(-1)
            per_bit = logits[:, None, :, :].expand(-1, count, -1, -1).gather(
                3, candidates[:, :, :, None]).squeeze(-1)
            background = torch.where(active[:, None, :], 0.0, per_bit).sum(-1)
        prior = state if self.memory else self.initial(n)
        weighted = local + background[:, None, :] + prior[:, :, None]
        impossible = torch.isneginf(weighted).all(1)
        safe = weighted.masked_fill(impossible[:, None, :], 0.0)
        return safe.logsumexp(1).masked_fill(impossible, -torch.inf), weighted

    def receive(self, pending, post):
        entities = domain.validate_anchor(post, 1)
        require(isinstance(pending, torch.Tensor) and pending.device.type == 'cpu' and
                pending.dtype == DTYPE and pending.shape == (len(post), 2, 2 ** entities) and
                not bool((torch.isnan(pending) | torch.isposinf(pending)).any()), 'invalid pending mode forecast')
        index = domain.world_index(post)
        evidence = pending.gather(2, index[:, None, None].expand(-1, 2, 1)).squeeze(-1)
        normalizer = evidence.logsumexp(-1, keepdim=True)
        require(bool(torch.isfinite(normalizer).all()), 'observation outside model support')
        return evidence - normalizer if self.memory else self.initial(len(post))


    @classmethod
    def from_legacy(cls, model):
        """Explicit tensor-only conversion of a verified local or exported JointKernel.

        Exported classes have another Python module identity. Recognize the original
        class name, exact child-module topology, boolean configuration and full tensor
        inventory instead of requiring a local isinstance match or permissive load.
        """
        require(isinstance(model, nn.Module) and type(model).__name__ == 'JointKernel',
                'only a legacy JointKernel can be adapted')
        config = {key: getattr(model, key, None) for key in ('persistence', 'role_tying', 'memory')}
        require(all(type(value) is bool for value in config.values()), 'invalid legacy kernel configuration')
        saved = model.state_dict()
        weight = saved.get('pair.0.weight')
        require(type(weight) is torch.Tensor and weight.ndim == 2 and weight.shape[1] == 2 and
                weight.shape[0] > 0, 'invalid legacy pair shape')
        config['hidden'] = weight.shape[0]
        with torch.random.fork_rng(devices=[]):
            result = cls(**config)
        topology = lambda value: {name: type(module) for name, module in value.named_modules() if name}
        require(topology(model) == topology(result), 'legacy module topology differs')
        expected = result.state_dict()
        require(set(saved) == set(expected) | {'worlds'}, 'legacy tensor inventory differs')
        geometry = saved['worlds']
        require(type(geometry) is torch.Tensor and geometry.device.type == 'cpu' and
                geometry.dtype == torch.long and geometry.layout == torch.strided and
                torch.equal(geometry, torch.tensor(domain.binary_worlds(3))), 'legacy world enumeration differs')
        for name, value in expected.items():
            old = saved[name]
            require(type(old) is torch.Tensor and old.device.type == 'cpu' and old.layout == torch.strided and
                    old.dtype == value.dtype and old.shape == value.shape and bool(torch.isfinite(old).all()),
                    f'invalid legacy learned tensor: {name}')
        origin = fingerprint(saved)
        learned = {name: saved[name].detach().clone() for name in expected}
        result.load_state_dict(learned, strict=True)
        learned_digest = fingerprint(learned)
        require(fingerprint(result.state_dict()) == learned_digest and fingerprint(model.state_dict()) == origin,
                'legacy adaptation changed learned tensors or source')
        result.train(model.training)
        result.domain_adaptation = {'version': 'shared-domain-adaptation-v1', 'original_entities': 3,
            'supported_entities': list(result.supported_entities), 'configuration': config,
            'source_full_state_sha256': origin, 'source_learned_parameters_sha256': learned_digest,
            'active_learned_parameters_sha256': fingerprint(result.state_dict()),
            'self_contact': 'supplied_per_mode_alias_conditioning; no performance claim',
            'extended_domain_training': False}
        return result
