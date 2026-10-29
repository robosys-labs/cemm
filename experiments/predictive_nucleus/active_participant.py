"""Opt-in successor using repaired filters and unchanged v1 bundle weights.

The frozen exported participant and its manifest stay unchanged. This command
records a separate implementation identity; it is not the v1 research result.
"""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import torch

from . import active_paths, external_participant as wire, comparison_scoring, joint_objective


VERSION = 'active-inference-v2'


def implementation():
    names = ('active_paths.py', 'active_participant.py', 'external_participant.py',
             'masked_replay.py', 'comparison_scoring.py', 'joint_objective.py')
    root = Path(__file__).parent
    return {'version': VERSION, 'source_sha256': {n: sha256((root / n).read_bytes()).hexdigest() for n in names},
            'gate_g1': 'NOT_ADMITTED', 'domain': 'three binary entities; noiseless visible observations'}


class Session(wire.Session):
    def __init__(self, *, model=None, memory=None, control=None):
        super().__init__(active_paths, comparison_scoring, joint_objective,
                         model=model, memory=memory, control=control)

    def _handle(self, request):
        result = super()._handle(request)
        if result['status'] == 'STARTED':
            result['implementation'] = implementation()
        elif result['status'] == 'RECEIVED':
            result['inference'] = dict(self.filter.diagnostic)
        return result


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
    return wire.serve(Session(model=model, memory=memory, control=args.participant), sys.stdin, sys.stdout)


if __name__ == '__main__':
    sys.exit(main())
