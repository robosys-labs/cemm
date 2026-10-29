"""Observed-only acceptance traces from native checkpoints; no oracle or fit API.

Each episode uses the existing causal Session. A forecast is copied and its
receipt checked before actual feedback. Failures retain that forecast and do
not retry an episode. Predictor mutation invalidates the entire collection.
"""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import platform
import resource
from time import perf_counter, process_time

import numpy as np
import torch

from . import acceptance_contract as contract
from .active_checkpoint import load_checkpoint, predictor_spec
from .active_participant import FeedbackFailure, Session
from .domain_contract import binary_worlds, require
from .joint_objective import fingerprint

VERSION = 'active-acceptance-trace-v1'


def _copy(value):
    """Freeze before feedback and convert tuples into ordinary strict JSON lists."""
    return json.loads(json.dumps(deepcopy(value), allow_nan=False))


def _identity(saved):
    model, memory, control = (saved[key] for key in ('model', 'memory', 'control'))
    predictor = model if model is not None else memory
    spec = predictor_spec(model=model, memory=memory, control=control)
    state = fingerprint(model.state_dict()) if model is not None else memory.digest() if memory is not None else None
    metadata = {name: getattr(predictor, name) for name in
                ('domain_adaptation', 'training_provenance', 'checkpoint_metadata', 'control_name')
                if hasattr(predictor, name)}
    return _copy({'predictor': spec, 'state_sha256': state, 'effective_control': spec['control'],
                  'checkpoint_metadata': saved['metadata'], 'current_metadata': metadata,
                  'module_training': {name: module.training for name, module in model.named_modules()}
                  if model is not None else None})


def _unchanged(saved, before):
    try:
        after = _identity(saved)
    except Exception as error:
        raise ValueError('frozen predictor identity cannot be verified') from error
    require(contract.digest(after) == contract.digest(before), 'frozen predictor changed during collection')
    return after


def _episode(data, saved, before):
    name, ids = data['episode'], sorted(data['ids'])
    record = {'episode': name, 'started': None, 'events': [], 'failure': None, 'ended': None}
    phase, step, session = 'start', 0, None
    try:
        session = Session(**{key: saved[key] for key in ('model', 'memory', 'control')})
        session.checkpoint_metadata = deepcopy(saved['metadata'])
        started = _copy(session.handle({'op': 'start', 'episode': name, 'ids': deepcopy(data['ids']),
                                       'observation': deepcopy(data['observations'][0])}))
        require(started['status'] == 'STARTED' and started['episode'] == name and started['ids'] == ids and
                started['world_order'] == [list(world) for world in binary_worlds(len(ids))],
                'invalid session start identity or geometry')
        expected = sha256(json.dumps(started['implementation'], sort_keys=True).encode()).hexdigest()
        require(started['implementation_sha256'] == expected, 'invalid implementation identity hash')
        record['started'] = started
        for step, action in enumerate(data['actions']):
            phase = 'predict'
            forecast = _copy(session.handle({'op': 'predict', 'episode': name, 'step': step,
                'action': deepcopy(action), 'sensor_ids': deepcopy(data['coverage'][step])}))
            require(forecast['status'] in ('PREDICTED', 'ABSTAIN') and forecast['episode'] == name and
                    type(forecast['step']) is int and forecast['step'] == step and forecast['ids'] == ids and
                    forecast['implementation_sha256'] == expected and forecast['action'] == action and
                    forecast['evidence']['sensor_ids'] == sorted(data['coverage'][step]),
                    'forecast identity/action/coverage mismatch')
            require(forecast['receipt'] == contract.receipt(forecast), 'forecast receipt mismatch')
            event = {'step': step, 'forecast': forecast, 'feedback': None}
            record['events'].append(event)  # Retain this valid forecast even if feedback fails.
            phase = 'feedback'
            feedback = _copy(session.handle({'op': 'feedback', 'episode': name, 'step': step,
                'receipt': forecast['receipt'], 'observation': deepcopy(data['observations'][step + 1])}))
            require(feedback['status'] == 'RECEIVED' and feedback['episode'] == name and
                    type(feedback['next_step']) is int and feedback['next_step'] == step + 1,
                    'feedback acknowledgment mismatch')
            event['feedback'] = feedback
        phase, step = 'end', len(data['actions'])
        ended = _copy(session.handle({'op': 'end', 'episode': name}))
        require(ended['status'] == 'ENDED' and ended['feedback_steps'] == step and
                ended['predictions'] == step and ended['pending_forecast'] is False,
                'incomplete session end')
        record['ended'] = ended
    except Exception as error:
        record['failure'] = {'phase': phase, 'step': step,
            'error_type': error.cause_type if isinstance(error, FeedbackFailure) else type(error).__name__,
            'message': str(error)}
        if isinstance(error, FeedbackFailure):
            record['failure']['evidence'] = _copy(error.evidence)
    finally:
        if session is not None:
            _unchanged({'model': session.model, 'memory': session.memory, 'control': session.control,
                        'metadata': getattr(session, 'checkpoint_metadata', None)}, before)
        _unchanged(saved, before)
    return record


def collect(inputs, *, checkpoint: Path, expected_sha256: str, participant: str, model_seed: int):
    """Collect declared observed episodes only; labels do not prove scientific lineage."""
    wall, cpu = perf_counter(), process_time()
    observed = contract.validate_inputs(inputs)
    require(isinstance(checkpoint, Path) and type(participant) is str and 0 < len(participant) <= 128 and
            type(model_seed) is int and model_seed >= 0, 'invalid checkpoint path or run label')
    saved = load_checkpoint(checkpoint, expected_sha256)
    before = _identity(saved)
    source = sha256(Path(__file__).read_bytes()).hexdigest()
    episodes = []
    try:
        for data in observed['episodes']:
            episodes.append(_episode(data, saved, before))
    finally:
        after = _unchanged(saved, before)
        require(sha256(Path(__file__).read_bytes()).hexdigest() == source, 'collector source changed during collection')
    model, memory = saved['model'], saved['memory']
    resources = {'collection_wall_seconds': perf_counter() - wall,
                 'collection_cpu_seconds': process_time() - cpu,
                 'process_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                 'peak_rss_scope': 'whole_process_lifetime_high_water_mark',
                 'trainable_parameters': sum(p.numel() for p in model.parameters()) if model is not None else 0,
                 'runtime': {'python': platform.python_version(), 'torch': str(torch.__version__),
                     'numpy': np.__version__, 'platform': platform.platform(),
                     'cpu_architecture': platform.machine(), 'processor': platform.processor() or None,
                     'num_threads': torch.get_num_threads(), 'interop_threads': torch.get_num_interop_threads(),
                     'deterministic': torch.are_deterministic_algorithms_enabled(),
                     'deterministic_warn_only': torch.is_deterministic_algorithms_warn_only_enabled()}}
    if memory is not None:
        resources.update(empirical_entries=len(memory.table),
                         empirical_distinct_outcomes=sum(len(counts) for counts in memory.table.values()),
                         empirical_observed_events=sum(sum(counts.values()) for counts in memory.table.values()))
    return _copy({'version': VERSION, 'input_sha256': contract.digest(observed),
        'checkpoint_sha256': expected_sha256, 'participant': participant, 'model_seed': model_seed,
        'episodes': episodes, 'source_sha256': {'acceptance_runner.py': source},
        'frozen_predictor_before': before, 'frozen_predictor_after': after,
        'resources': resources})


def main():
    import argparse
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    command = commands.add_parser('collect')
    command.add_argument('--inputs', type=Path, required=True)
    command.add_argument('--inputs-sha256', required=True)
    command.add_argument('--checkpoint', type=Path, required=True)
    command.add_argument('--checkpoint-sha256', required=True)
    command.add_argument('--participant', required=True)
    command.add_argument('--seed', type=int, required=True)
    command.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(sys.version_info[:2] == (3, 13) and torch.__version__ == '2.10.0+cpu' and np.__version__ == '2.3.5' and
            torch.version.cuda is None and torch.version.hip is None, 'pinned CPU Python/PyTorch/NumPy required')
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    inputs = contract.load_json(args.inputs, args.inputs_sha256)
    result = collect(inputs, checkpoint=args.checkpoint, expected_sha256=args.checkpoint_sha256,
                     participant=args.participant, model_seed=args.seed)
    contract.write_json(args.output, result)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
