"""Fresh flat 3–6-entity baseline; no legacy checkpoint conversion.

One global GRU consumes fixed address slots, and one global head predicts whole
worlds. No per-object network, interaction sharing, or identity equivariance is
supplied. The existence mask distinguishes absent slots from measured zero bits.
"""
import torch
from torch import nn
from torch.nn import functional as F

from . import domain_contract as domain
from .joint_objective import DTYPE, require


class DomainFlatGRU(nn.Module):
    """29 input features and 64 global logits, restricted to the current domain.

    Features are six bits, six existence flags, two six-slot operand indicators,
    three action-kind indicators and two intervention-value indicators. Existence
    already identifies entity count. The valid output coordinates have zero in
    unused trailing slots; normalize only those logits, not all 64 then truncate.

    Parameter count is 3*h*h + 157*h + 64 (1,512 at default h=8), unchanged by
    supplied persistence. This is an explicit baseline, not a capacity-match
    claim. Self-contact has one physical output coordinate without pair-factor
    projection; supporting it does not establish learned self-contact dynamics.
    """
    supported_entities, supports_self_contact = (3, 4, 5, 6), True

    def __init__(self, hidden=8, *, persistence=False):
        super().__init__()
        require(type(hidden) is int and hidden > 0 and type(persistence) is bool,
                'invalid flat configuration')
        self.hidden, self.persistence = hidden, persistence
        self.cell = nn.GRUCell(29, hidden, dtype=DTYPE)
        self.head = nn.Linear(hidden, 64, dtype=DTYPE)

    def initial(self, n):
        require(type(n) is int and n > 0, 'positive integer batch size required')
        return torch.zeros(n, self.hidden, dtype=DTYPE)

    def _validate_state(self, state, batch_size):
        require(isinstance(state, torch.Tensor) and state.device.type == 'cpu' and
                state.dtype == DTYPE and state.shape == (batch_size, self.hidden) and
                bool(torch.isfinite(state).all()), 'invalid flat recurrent state')

    def predict(self, pre, action, state):
        """Pure full-world conditional for one realized or hypothesized history."""
        entities = domain.validate_anchor(pre, 1)
        domain.validate_action(action, len(pre), entities)
        self._validate_state(state, len(pre))
        kind, first, second, value = action.unbind(-1)
        slots = torch.arange(6)[None, :]
        features = torch.cat((F.pad(pre, (0, 6 - entities)),
            (slots < entities).to(DTYPE).expand(len(pre), -1),
            (slots == first[:, None]).to(DTYPE),
            (slots == second[:, None]).to(DTYPE), F.one_hot(kind, 3).to(DTYPE),
            ((kind == 1)[:, None] & (value[:, None] == torch.arange(2)[None])).to(DTYPE)), -1)
        hidden = self.cell(features, state)
        logits = self.head(hidden)
        require(bool(torch.isfinite(hidden).all()) and bool(torch.isfinite(logits).all()),
                'nonfinite flat forecast')
        indices = torch.arange(2 ** entities) * (2 ** (6 - entities))
        logits = logits.index_select(1, indices)
        if self.persistence:
            worlds = torch.tensor(domain.binary_worlds(entities), dtype=torch.long)
            logits = logits.masked_fill(~domain.persistence_support(pre, action, worlds), -torch.inf)
        return logits.log_softmax(-1), hidden

    def receive(self, pending, post):
        """Next predict consumes each full post-state; filtering supplies its weight."""
        domain.validate_anchor(post, 1)
        self._validate_state(pending, len(post))
        return pending
