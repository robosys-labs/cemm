"""Active causal inference from a native checkpoint or unchanged v1 bundle.

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

from . import active_paths, external_participant as wire, domain_contract, joint_objective
from .active_evidence import ActiveEvidence


VERSION = 'active-inference-v5'


def implementation():
    names = ('active_paths.py', 'active_participant.py', 'active_evidence.py', 'domain_contract.py',
             'domain_kernel.py', 'domain_flat.py', 'active_checkpoint.py',
             'context_support.py', 'external_participant.py',
             'masked_replay.py', 'comparison_scoring.py', 'joint_objective.py')
    root = Path(__file__).parent
    return {'version': VERSION, 'source_sha256': {n: sha256((root / n).read_bytes()).hexdigest() for n in names},
            'gate_g1': 'NOT_ADMITTED', 'domain': '3-6 binary entities subject to predictor capabilities; noiseless readings'}


class FeedbackFailure(ValueError):
    """Validated feedback was scored, but the existing filter rejected its update."""
    def __init__(self, cause, evidence):
        super().__init__(str(cause))
        self.cause_type, self.evidence = type(cause).__name__, evidence


class Session(wire.Session):
    def __init__(self, *, model=None, memory=None, control=None):
        if memory is not None:
            control = active_paths.empirical_control(memory, control)
        super().__init__(active_paths, domain_contract, joint_objective,
                         model=model, memory=memory, control=control)
        predictor = model if model is not None else memory if memory is not None else active_paths.LastObserved
        self.supported_entities, self.allow_self = active_paths.capabilities(predictor)

    def _observation(self, data, anchor=False):
        wire.require(type(data) is dict and set(data) == set(self.ids), 'observation must name exactly the episode IDs')
        values = [data[name] for name in self.ids]
        wire.require(all(v is None or (type(v) is int and v in (0, 1)) for v in values), 'invalid reading')
        wire.require(not anchor or all(v is not None for v in values), 'full anchor required')
        return (torch.tensor([[v if v is not None else -1 for v in values]], dtype=torch.float64),
                torch.tensor([[v is not None for v in values]], dtype=torch.bool))

    def _action(self, data):
        wire.require(type(data) is dict and data.get('kind') in ('contact', 'set', 'observe'), 'invalid action')
        kind = data['kind']
        wire.require(set(data) == ({'kind', 'participants', 'value'} if kind == 'set' else {'kind', 'participants'}),
                     'extra/missing action field')
        members = data['participants']
        wire.require(type(members) is list and all(type(n) is str and n in self.ids for n in members) and
                     len(members) == {'contact': 2, 'set': 1, 'observe': 0}[kind], 'invalid action participants')
        value = data.get('value', -1)
        wire.require(type(value) is int and (kind != 'set' or value in (0, 1)), 'invalid set value')
        action = torch.tensor([[('contact', 'set', 'observe').index(kind),
            self.ids.index(members[0]) if members else -1,
            self.ids.index(members[1]) if len(members) == 2 else -1, value]], dtype=torch.long)
        domain_contract.validate_action(action, 1, len(self.ids), allow_self=self.allow_self)
        return action

    def _start(self, request):
        wire.require(self.phase == 'NEW' and set(request) == {'op', 'episode', 'ids', 'observation'}, 'invalid start')
        wire.require(type(request['episode']) is str and 0 < len(request['episode']) <= 128, 'invalid episode identifier')
        ids = request['ids']
        wire.require(type(ids) is list and 3 <= len(ids) <= 6 and
                     all(type(x) is str and 0 < len(x) <= 128 for x in ids) and len(set(ids)) == len(ids),
                     'three to six distinct IDs required')
        wire.require(len(ids) in self.supported_entities,
                     'entity count outside predictor domain; explicit adaptation required')
        self.episode, self.ids = request['episode'], tuple(sorted(ids))
        anchor, _ = self._observation(request['observation'], anchor=True)
        self.filter = (active_paths.NeuralPaths(self.model, anchor) if self.model is not None else
                       active_paths.EmpiricalPaths(self.memory, anchor, first_contact=self.control == 'first_contact')
                       if self.memory is not None else active_paths.LastObserved(anchor))
        self.evidence = ActiveEvidence(self.ids, request['observation'])
        identity = implementation()
        predictor = self.model if self.model is not None else self.memory
        identity.update(predictor_class=type(predictor).__name__ if predictor is not None else 'LastObserved',
                        control=self.control,
                        predictor_configuration={key: getattr(predictor, key) for key in
                            ('persistence', 'role_tying', 'memory', 'mode')
                            if type(getattr(predictor, key, None)) in (bool, str)},
                        predictor_domain={'entities': list(self.supported_entities), 'self_contact': self.allow_self,
                        'live_path_limit': 64, 'candidate_expansion_limit': 512, 'action_limit': 128},
                        checkpoint_state_sha256=self.weights, empirical_table_sha256=self.table,
                        adaptation=deepcopy(getattr(predictor, 'domain_adaptation', None)),
                        training=deepcopy(getattr(predictor, 'training_provenance', None)),
                        checkpoint=deepcopy(getattr(predictor, 'checkpoint_metadata',
                                                   getattr(self, 'checkpoint_metadata', None))))
        self.implementation_sha256 = sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
        self.phase = 'READY'
        return {'status': 'STARTED', 'episode': self.episode, 'ids': self.ids,
                'world_order': domain_contract.binary_worlds(len(self.ids)), 'gate_g1': 'NOT_ADMITTED',
                'implementation': identity, 'implementation_sha256': self.implementation_sha256,
                'evidence_contract': self.evidence.contract}

    def _handle(self, request):
        op = request.get('op') if type(request) is dict else None
        if op == 'start':
            return self._start(request)
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
        return super()._handle(request)


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
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--bundle', type=Path)
    source.add_argument('--checkpoint', type=Path)
    parser.add_argument('--checkpoint-sha256')
    parser.add_argument('--manifest-sha256')
    parser.add_argument('--participant')
    parser.add_argument('--seed', type=int)
    parser.add_argument('--expand-domain', action='store_true',
                        help='explicit structural kernel/table adaptation; not a learned transfer result')
    args = parser.parse_args()
    wire.require(sys.version_info[:2] == (3, 13) and torch.__version__ == '2.10.0+cpu' and
                 np.__version__ == '2.3.5', 'pinned Python/PyTorch/NumPy required')
    wire.require(torch.version.cuda is None and torch.version.hip is None, 'CPU-only build required')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    if args.checkpoint is not None:
        wire.require(args.checkpoint_sha256 is not None and args.manifest_sha256 is None and
                     args.participant is None and args.seed is None and not args.expand_domain,
                     'native checkpoint owns predictor/configuration; provide only checkpoint and its SHA')
        from .active_checkpoint import load_checkpoint
        saved = load_checkpoint(args.checkpoint, args.checkpoint_sha256)
        session = Session(model=saved['model'], memory=saved['memory'], control=saved['control'])
        session.checkpoint_metadata = deepcopy(saved['metadata'])
        return serve(session, sys.stdin, sys.stdout)
    wire.require(args.manifest_sha256 is not None and args.participant is not None and
                 args.checkpoint_sha256 is None, 'bundle manifest SHA and participant required')
    root = args.bundle.resolve()
    manifest = wire.verify_bundle(root, args.manifest_sha256)
    # Isolated import name avoids substituting an unrelated participant_core.
    name = '_active_frozen_' + args.manifest_sha256
    wire.require(name not in sys.modules, 'bundle namespace already loaded')
    spec = importlib.util.spec_from_file_location(name, root / 'participant_core' / '__init__.py',
                            submodule_search_locations=[str(root / 'participant_core')])
    sys.modules[name] = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sys.modules[name])
    model, memory = wire.restore(name, manifest, root, args.participant, args.seed)
    if args.expand_domain:
        if model is not None:
            wire.require(args.participant in ('kernel_supplied_persistence', 'kernel_learned_persistence',
                         'kernel_untied_roles', 'kernel_memory_reset'), 'flat checkpoint has a fixed three-entity domain')
            from .domain_kernel import DomainKernel
            model = DomainKernel.from_legacy(model).eval()
        elif memory is not None:
            memory = domain_contract.DomainMemory.from_legacy(memory)
    return serve(Session(model=model, memory=memory, control=args.participant), sys.stdin, sys.stdout)


if __name__ == '__main__':
    sys.exit(main())
