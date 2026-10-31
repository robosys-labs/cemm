"""Observed-only timing collection. No oracle, simulator, or fitting imports."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import platform
import resource
from time import perf_counter, process_time

import numpy as np
import torch

from . import timing_contract as contract
from .acceptance_runner import _copy, _identity, _unchanged
from .active_checkpoint import load_checkpoint
from .domain_contract import binary_worlds
from .timing_session import Session


def _episode(data, saved, before):
    name = data['episode']
    result = {'episode': name, 'started': None, 'events': [], 'failure': None, 'ended': None}
    phase, step = 'start', 0
    try:
        session = Session(saved['model'])
        start = _copy(session.handle({'op': 'start', 'episode': name, 'ids': deepcopy(data['ids']),
                                     'observation': deepcopy(data['observations'][0])}))
        contract.require(start['status'] == 'STARTED' and start['episode'] == name and
            start['ids'] == sorted(data['ids']) and start['world_order'] ==
            [list(w) for w in binary_worlds(len(data['ids']))] and
            start['implementation_sha256'] == contract.digest(start['implementation']), 'invalid timing start')
        result['started'] = start
        for step, action in enumerate(data['actions']):
            phase = 'predict'
            forecast = _copy(session.handle({'op': 'predict', 'episode': name, 'step': step,
                'action': deepcopy(action), 'sensor_ids': deepcopy(data['coverage'][step])}))
            contract.forecast_logs(forecast, data, step, start['implementation_sha256'])
            event = {'step': step, 'forecast': forecast, 'feedback': None}
            result['events'].append(event)  # Frozen before feedback, including failed updates.
            phase = 'feedback'
            feedback = _copy(session.handle({'op': 'feedback', 'episode': name, 'step': step,
                'receipt': forecast['receipt'], 'observation': deepcopy(data['observations'][step + 1])}))
            contract.require(feedback == {'status': 'RECEIVED', 'episode': name, 'next_step': step + 1},
                             'invalid feedback acknowledgment')
            event['feedback'] = feedback
        phase, step = 'end', len(data['actions'])
        ended = _copy(session.handle({'op': 'end', 'episode': name}))
        contract.require(ended == {'status': 'ENDED', 'episode': name,
            'feedback_steps': step, 'predictions': step, 'pending_forecast': False}, 'invalid end acknowledgment')
        result['ended'] = ended
    except Exception as error:
        result['failure'] = {'phase': phase, 'step': step, 'error_type': type(error).__name__, 'message': str(error)}
    finally:
        _unchanged(saved, before)
    return result


def collect(inputs, *, checkpoint, expected_sha256, model_seed):
    wall, cpu = perf_counter(), process_time()
    observed = contract.validate_inputs(inputs)
    contract.require(isinstance(checkpoint, Path) and type(model_seed) is int and model_seed >= 0,
                     'invalid checkpoint or seed')
    saved = load_checkpoint(checkpoint, expected_sha256)
    before = _identity(saved)
    contract.require(saved['memory'] is None and saved['control'] is None, 'neural timing checkpoint required')
    source = sha256(Path(__file__).read_bytes()).hexdigest()
    try:
        episodes = [_episode(case, saved, before) for case in observed['episodes']]
    finally:
        after = _unchanged(saved, before)
        contract.require(source == sha256(Path(__file__).read_bytes()).hexdigest(), 'collector source changed')
    return _copy({'version': 'timing-trace-v1', 'input_sha256': contract.digest(observed),
        'checkpoint_sha256': expected_sha256, 'participant': 'frozen', 'model_seed': model_seed,
        'episodes': episodes, 'source_sha256': {'timing_runner.py': source},
        'frozen_predictor_before': before, 'frozen_predictor_after': after,
        'resources': {'collection_wall_seconds': perf_counter() - wall,
            'collection_cpu_seconds': process_time() - cpu,
            'process_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'peak_rss_scope': 'whole_process_lifetime_high_water_mark',
            'trainable_parameters': sum(p.numel() for p in saved['model'].parameters()),
            'runtime': {'python': platform.python_version(), 'torch': str(torch.__version__),
                'numpy': np.__version__, 'num_threads': torch.get_num_threads(),
                'interop_threads': torch.get_num_interop_threads(),
                'deterministic': torch.are_deterministic_algorithms_enabled()}}})
