"""Opt-in successor using repaired filters and unchanged v1 bundle weights.

The frozen exported participant and its manifest stay unchanged. This command
records a separate implementation identity; it is not the v1 research result.
"""
from hashlib import sha256
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import torch

from . import active_paths, external_participant as wire, comparison_scoring, joint_objective
from .active_evidence import ActiveEvidence


VERSION = 'active-inference-v3'


def implementation():
    names = ('active_paths.py', 'active_participant.py', 'active_evidence.py', 'context_support.py', 'external_participant.py',
             'masked_replay.py', 'comparison_scoring.py', 'joint_objective.py')
    root = Path(__file__).parent
    return {'version': VERSION, 'source_sha256': {n: sha256((root / n).read_bytes()).hexdigest() for n in names},
            'gate_g1': 'NOT_ADMITTED', 'domain': 'three binary entities; noiseless visible observations'}


class FeedbackFailure(ValueError):
    """Validated feedback was scored, but the existing filter rejected its update."""
    def __init__(self, cause, evidence):
        super().__init__(str(cause))
        self.cause_type, self.evidence = type(cause).__name__, evidence


class Session(wire.Session):
    def __init__(self, *, model=None, memory=None, control=None):
        super().__init__(active_paths, comparison_scoring, joint_objective,
                         model=model, memory=memory, control=control)

    def _handle(self, request):
        op = request.get('op') if type(request) is dict else None
        if op == 'predict' and self.phase == 'READY':
            # Optional active-only coverage; the frozen v1 transport stays unchanged.
            selected = request.get('sensor_ids', list(self.ids))
            wire.require(type(selected) is list, 'sensor_ids must be a list')
            coverage = self.evidence.sensor_ids(selected)
            original = {key: value for key, value in request.items() if key != 'sensor_ids'}
            result = super()._handle(original)
            logs = None if result['log'] is None else result['log']['values'][0]
            result['action'] = deepcopy(request['action'])
            result['evidence'] = self.evidence.begin(request['action'], logs, coverage)
            result['implementation_sha256'] = self.implementation_sha256
            canonical = {key: value for key, value in result.items()
                         if key not in ('wall_seconds', 'cpu_seconds', 'receipt')}
            self.receipt = sha256(json.dumps(canonical, sort_keys=True, allow_nan=False).encode()).hexdigest()
            self.evidence.bind(self.receipt)
            result['receipt'] = self.receipt
            return result
        if op == 'feedback':
            # Validate before even preparing evidence; no bad request can inflate it.
            wire.require(self.phase == 'PENDING' and set(request) ==
                         {'op', 'episode', 'step', 'receipt', 'observation'} and
                         request['episode'] == self.episode and type(request['step']) is int and
                         request['step'] == self.step and request['receipt'] == self.receipt,
                         'feedback ordering/episode/step/receipt/fields')
            self._observation(request['observation'])
            preview = self.evidence.preview(request['observation'], self.receipt)
            try:
                result = super()._handle(request)
            except Exception as error:
                # Path budgets and implementation failures retain their own error;
                # only the separately computed evidence can claim a contradiction.
                raise FeedbackFailure(error, preview) from error
            result['inference'] = dict(self.filter.diagnostic)
            result['evidence'] = self.evidence.receive(request['observation'], self.receipt)
            return result
        result = super()._handle(request)
        if result['status'] == 'STARTED':
            result['implementation'] = implementation()
            self.implementation_sha256 = sha256(json.dumps(result['implementation'], sort_keys=True).encode()).hexdigest()
            self.evidence = ActiveEvidence(self.ids, request['observation'])
            result['evidence_contract'] = self.evidence.contract
            result['implementation_sha256'] = self.implementation_sha256
        return result


def serve(session, incoming, outgoing):
    """Active wire preserves typed feedback evidence on terminal filter failure."""
    try:
        while session.phase != 'CLOSED':
            line = incoming.readline(wire.MAX_LINE + 1)
            wire.require(line and len(line) <= wire.MAX_LINE and line.endswith('\n'),
                         'truncated/oversized frame or missing end')
            reply = session.handle(wire.strict_json(line))
            outgoing.write(json.dumps(reply, sort_keys=True, allow_nan=False) + '\n')
            outgoing.flush()
        return 0
    except Exception as error:
        session.phase = 'ERROR'
        reply = {'status': 'ERROR', 'error_type': type(error).__name__, 'message': str(error),
                 'step': session.step, 'evaluated': False}
        if isinstance(error, FeedbackFailure):
            reply.update(error_type=error.cause_type, evidence=error.evidence, feedback_status='FILTER_REJECTED')
        outgoing.write(json.dumps(reply, sort_keys=True, allow_nan=False) + '\n')
        outgoing.flush()
        return 2


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', required=True, type=Path)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--participant', required=True)
    parser.add_argument('--seed', type=int)
    args = parser.parse_args()
    root = args.bundle.resolve()
    manifest = wire.verify_bundle(root, args.manifest_sha256)
    wire.require(sys.version_info[:2] == (3, 13) and torch.__version__ == '2.10.0+cpu' and
                 np.__version__ == '2.3.5', 'pinned Python/PyTorch/NumPy required')
    wire.require(torch.version.cuda is None and torch.version.hip is None, 'CPU-only build required')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    # Isolated import name avoids substituting an unrelated participant_core.
    name = '_active_frozen_' + args.manifest_sha256
    wire.require(name not in sys.modules, 'bundle namespace already loaded')
    spec = importlib.util.spec_from_file_location(name, root / 'participant_core' / '__init__.py',
                            submodule_search_locations=[str(root / 'participant_core')])
    sys.modules[name] = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sys.modules[name])
    model, memory = wire.restore(name, manifest, root, args.participant, args.seed)
    return serve(Session(model=model, memory=memory, control=args.participant), sys.stdin, sys.stdout)


if __name__ == '__main__':
    sys.exit(main())
