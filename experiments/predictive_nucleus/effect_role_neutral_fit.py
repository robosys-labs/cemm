"""Prospective normalization-only fit; the frozen v1 recipe is unchanged.

The fit body retains v1's objective, optimizer, budget and integrity checks.
An explicit new learner avoids modifying or monkeypatching historical modules.
"""
import math
import time

import torch

from . import acceptance_contract as c, set_acquisition_run_v2 as native
from .effect_role_neutral import learner
from .effect_role_run import ARMS, OPTIMIZER, objective
from .joint_objective import fingerprint


def fit_one(arm, seed, parent, world, tapes, labels, settings):
    c.require(type(tapes) is dict and set(tapes) == {'teach', 'rehearsal'}, 'both observed training tapes required')
    c.require(arm in ARMS and (labels is not None) == (arm == 'parser') and
        (labels is None or type(labels) is dict and all(k in labels for k in tapes)), 'parser-only labels required')
    c.require(type(settings) is dict and type(settings.get('updates')) is int and settings['updates'] > 0 and
        all(type(settings.get(k)) in (int, float) and math.isfinite(settings[k]) and settings[k] > 0
            for k in ('learning_rate', 'gradient_clip', 'cpu_seconds_per_fit')) and
        type(settings.get('teach_weight')) in (int, float) and math.isfinite(settings['teach_weight']) and
        0 < settings['teach_weight'] < 1, 'invalid fixed fit budget/weight')
    c.require(not world.training and all(not p.requires_grad and p.grad is None for p in world.parameters()),
              'explicit frozen world required before fitting')
    net = learner(arm, seed, parent); initial = fingerprint(net.state_dict()); native_before = fingerprint(world.state_dict())
    optimizer = torch.optim.Adam(net.parameters(), lr=settings['learning_rate'], betas=tuple(OPTIMIZER['betas']),
                                 eps=OPTIMIZER['eps'], weight_decay=OPTIMIZER['weight_decay'], amsgrad=OPTIMIZER['amsgrad'])
    curves, cpu, started = [], time.process_time(), time.perf_counter()
    for step in range(settings['updates']):
        c.require(time.process_time() - cpu <= settings['cpu_seconds_per_fit'], 'fixed training CPU ceiling exceeded')
        optimizer.zero_grad(set_to_none=True)
        losses, counts = {}, {}
        for name in ('teach', 'rehearsal'):
            losses[name], counts[name] = objective(arm, net, world, tapes[name], labels[name] if labels is not None else None)
        loss = settings['teach_weight'] * losses['teach'] + (1. - settings['teach_weight']) * losses['rehearsal']
        c.require(bool(torch.isfinite(loss)), 'nonfinite weighted objective')
        loss.backward()
        torch.nn.utils.clip_grad_norm_(net.parameters(), settings['gradient_clip'], error_if_nonfinite=True)
        optimizer.step()
        c.require(all(bool(torch.isfinite(p).all()) for p in net.parameters()), 'nonfinite learned language tensor')
        c.require(fingerprint(world.state_dict()) == native_before and all(p.grad is None for p in world.parameters()),
                  'frozen native world mutated')
        if step == 0 or (step + 1) % 16 == 0:
            curves.append({'update': step + 1, **{k: float(v.detach()) for k, v in losses.items()}})
        c.require(time.process_time() - cpu <= settings['cpu_seconds_per_fit'], 'fixed training CPU ceiling exceeded')
    with torch.no_grad():
        measured = {name: objective(arm, net, world, groups, labels[name] if labels is not None else None)
                    for name, groups in tapes.items()}
        final = {name: float(value[0]) for name, value in measured.items()}
    c.require(all(math.isfinite(v) for v in final.values()) and
        {name: value[1] for name, value in measured.items()} == counts, 'final objective/count differs')
    c.require(fingerprint(world.state_dict()) == native_before and all(p.grad is None for p in world.parameters()),
              'frozen native world mutated during final measurement')
    c.require(time.process_time() - cpu <= settings['cpu_seconds_per_fit'], 'fixed training CPU ceiling exceeded')
    report = {'initial_sha256': initial, 'final_sha256': fingerprint(net.state_dict()),
        'world_sha256': native_before, 'world_unchanged': True, 'parameters': sum(p.numel() for p in net.parameters()),
        'updates': settings['updates'], 'observed_forecasts_per_update': counts, 'settings': dict(settings),
        'optimizer': {**OPTIMIZER, 'betas': list(OPTIMIZER['betas'])},
        'fresh_optimizer': True, 'curve': curves, 'final_objective': final,
        'resources': native.resources(cpu, started)}
    return net, report
