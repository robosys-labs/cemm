"""Outcome-only binding comparison over one validated observed history.

Reuses the frozen bilingual pack/forecast path. This is an in-process preparation
API, not a prospective scientific runner: it neither freezes a challenge nor
establishes independent custody, checkpoint publication, or scientific admission.
No historical model or research fixture is loaded here. Callers own persistence.
"""
import math
import time

import torch

from . import acceptance_contract as contract
from .bilingual_contract import validate_inputs
from .domain_kernel import DomainKernel
from .bilingual_run import forecasts, pack
from .binding_model import ARMS, PARAMETERS, encoder
from .joint_objective import fingerprint, require


def fit_comparison(inputs, world, *, seed, updates, learning_rate=0.02,
                   gradient_clip=5.0, cpu_seconds_per_arm=120.0):
    """Fresh arms share every delivered outcome, batch, order and update budget.

    Equal exposure is not equal capacity or consumed compute. Inputs reject gold
    labels via the existing envelope validator. Only complete-world outcome NLL
    supervises language. An exception returns no completed-comparison result;
    this function does not offer retry, resume, rollback, or checkpoint selection.
    """
    require(type(updates) is int and 1 <= updates <= 4096, 'invalid update budget')
    require(type(seed) is int and 0 <= seed < 2 ** 63, 'invalid binding seed')
    for name, value in (('learning_rate', learning_rate), ('gradient_clip', gradient_clip),
                        ('cpu_seconds_per_arm', cpu_seconds_per_arm)):
        require(type(value) in (int, float) and math.isfinite(value) and value > 0,
                'invalid ' + name)
    observed = validate_inputs(inputs)
    # Validate, never mutate, caller-owned mode/trainability flags.
    require(type(world) is DomainKernel and world.memory is True, 'persistent DomainKernel required')
    require(all(not p.requires_grad for p in world.parameters()), 'world must already be frozen')
    require(all(not module.training for module in world.modules()), 'world must already be in evaluation mode')
    original = fingerprint(world.state_dict())
    started, cpu = time.perf_counter(), time.process_time()
    groups = pack(observed, world)
    preparation = {'wall_seconds': time.perf_counter() - started,
                   'cpu_seconds': time.process_time() - cpu}
    expected = sum(len(e['utterances']) for e in observed['episodes'])
    models, reports = {}, {}
    try:
        for arm in ARMS:
            model = encoder(arm, seed)
            initial = fingerprint(model.state_dict())
            optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
            wall0, cpu0 = time.perf_counter(), time.process_time()
            curve = []
            for update in range(updates):
                optimizer.zero_grad(set_to_none=True)
                total, count = 0., 0
                for group in groups:
                    predicted = forecasts('grounded', model, world, group)
                    for (raw, _), event in zip(predicted, group['events'], strict=True):
                        total = total - raw.gather(1, event['target'][:, None]).sum()
                        count += len(raw)
                require(count == expected, 'observed exposure changed')
                loss = total / count
                require(bool(torch.isfinite(loss)), 'nonfinite binding objective')
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), gradient_clip, error_if_nonfinite=True)
                optimizer.step()
                require(all(bool(torch.isfinite(p).all()) for p in model.parameters()),
                        'nonfinite binding update')
                if update == 0 or (update + 1) % 16 == 0 or update + 1 == updates:
                    curve.append([update + 1, float(loss.detach())])
                require(time.process_time() - cpu0 <= cpu_seconds_per_arm, 'binding CPU limit exceeded')
            models[arm] = model.eval()
            reports[arm] = {'initial_sha256': initial, 'final_sha256': fingerprint(model.state_dict()),
                'parameters': PARAMETERS[arm], 'updates': updates, 'observed_events_per_update': expected,
                'curve': curve, 'cpu_seconds': time.process_time() - cpu0,
                'wall_seconds': time.perf_counter() - wall0}
    finally:
        require(fingerprint(world.state_dict()) == original, 'frozen world changed')
    return {'models': models, 'reports': reports, 'training_input_sha256': contract.digest(observed),
            'world_state_sha256': original, 'seed': seed, 'shared_cache_preparation': preparation,
            'optimizer': {'name': 'Adam', 'learning_rate': learning_rate, 'gradient_clip': gradient_clip},
            'scientific_admission': False, 'scope': 'IN_PROCESS_COMPARISON_NOT_A_FROZEN_STUDY'}
