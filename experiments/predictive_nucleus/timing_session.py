"""Full-feedback timing session; only observed group endpoints update belief.

This separate opt-in interface does not claim native masked-evidence support.
All full-world tails survive; forecasts are receipted before actual feedback.
"""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from time import perf_counter, process_time

import torch

from . import timing_contract as contract
from .acceptance_contract import receipt
from .active_checkpoint import predictor_spec
from .domain_contract import binary_worlds
from .joint_objective import DTYPE, fingerprint
from .timing_kernel import TimingKernel


def sources():
    root = Path(__file__).parent
    return {n: sha256((root / n).read_bytes()).hexdigest() for n in
            ('timing_contract.py', 'timing_kernel.py', 'timing_session.py')}


class Session:
    def __init__(self, model):
        self.model, self.kernel, self.phase, self.step = model, TimingKernel(model), 'NEW', 0

    @torch.no_grad()
    def handle(self, request):
        contract.require(type(request) is dict, 'request object required')
        op = request.get('op')
        if op == 'start':
            contract.fields(request, ('op', 'episode', 'ids', 'observation'))
            contract.require(self.phase == 'NEW' and contract.identifier(request['episode']), 'invalid start')
            ids = request['ids']
            contract.require(type(ids) is list and 3 <= len(ids) <= 6 and all(contract.identifier(x) for x in ids)
                             and len(set(ids)) == len(ids), 'three to six distinct IDs required')
            ids = sorted(ids)
            world = torch.tensor([contract.observation(request['observation'], ids)], dtype=DTYPE)
            identity = contract.implementation_identity(predictor_spec(model=self.model),
                fingerprint(self.model.state_dict()), sources())
            self.ids, self.episode, self.world = ids, request['episode'], world
            self.state, self.phase = self.model.initial(1), 'READY'
            self.implementation_sha256 = contract.digest(identity)
            return {'status': 'STARTED', 'episode': self.episode, 'ids': list(self.ids),
                'world_order': binary_worlds(len(ids)), 'implementation': identity,
                'implementation_sha256': self.implementation_sha256}
        if op == 'predict':
            contract.fields(request, ('op', 'episode', 'step', 'action', 'sensor_ids'))
            self._ordered(request, 'READY')
            contract.require(self.step < 128, 'event budget exceeded')
            selected = request['sensor_ids']
            contract.require(type(selected) is list and len(selected) == len(self.ids) and
                all(type(x) is str for x in selected) and set(selected) == set(self.ids), 'full coverage required')
            pairs, timing = contract.action_contacts(request['action'], self.ids)
            contacts = torch.tensor([[[0, self.ids.index(a), self.ids.index(b), -1] for a, b in pairs]])
            wall, cpu = perf_counter(), process_time()
            raw, pending = self.kernel.predict(self.world.clone(), contacts, timing, self.state.clone())
            total = raw.logsumexp(-1, keepdim=True)
            contract.require(bool(torch.isfinite(total).all()) and bool((total.abs() <= 1e-10).all()),
                             'compound forecast mass is not normalized')
            contract.require(torch.allclose(raw, pending.logsumexp(1), atol=1e-12, rtol=0),
                             'compound pending likelihood differs from forecast')
            logs = raw - total
            contract.require(not bool((torch.isnan(logs) | torch.isposinf(logs)).any()) and
                             bool(torch.isfinite(logs).any(-1).all()), 'invalid forecast')
            result = {'status': 'PREDICTED', 'episode': self.episode, 'step': self.step, 'ids': list(self.ids),
                'action': deepcopy(request['action']), 'sensor_ids': list(self.ids),
                'log': {'values': [[None if v == -torch.inf else v for v in logs[0].tolist()]],
                        'null_status': 'negative_infinity'},
                'normalization_log_total': total[0].tolist(),
                'implementation_sha256': self.implementation_sha256,
                'wall_seconds': perf_counter() - wall, 'cpu_seconds': process_time() - cpu}
            result['receipt'] = receipt(result)
            self.pending, self.receipt, self.phase = pending, result['receipt'], 'PENDING'
            return result
        if op == 'feedback':
            contract.fields(request, ('op', 'episode', 'step', 'receipt', 'observation'))
            self._ordered(request, 'PENDING')
            contract.require(request['receipt'] == self.receipt, 'feedback receipt differs')
            world = torch.tensor([contract.observation(request['observation'], self.ids)], dtype=DTYPE)
            state = self.model.receive(self.pending, world)
            self.world, self.state, self.phase, self.step = world, state, 'READY', self.step + 1
            del self.pending
            return {'status': 'RECEIVED', 'episode': self.episode, 'next_step': self.step}
        if op == 'end':
            contract.fields(request, ('op', 'episode'))
            contract.require(self.phase == 'READY' and request['episode'] == self.episode, 'invalid end')
            self.phase = 'CLOSED'
            return {'status': 'ENDED', 'episode': self.episode, 'feedback_steps': self.step,
                    'predictions': self.step, 'pending_forecast': False}
        raise ValueError('unsupported timing operation')

    def _ordered(self, request, phase):
        contract.require(self.phase == phase and request['episode'] == self.episode and
                         type(request['step']) is int and request['step'] == self.step,
                         'operation phase/episode/step differs')
