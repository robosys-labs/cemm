"""Fixed-mask set acquisition using the existing observed joint-likelihood replay.

Only 68 existing scalars may move. Forbidden updates are detected, never restored
or hidden. This module receives observed batches; it imports no study generator,
oracle, challenge data or language model.
"""
from hashlib import sha256
import math
from pathlib import Path
import resource
from time import perf_counter, process_time

import torch

from . import active_learning as learning
from .active_checkpoint import predictor_spec
from .domain_kernel import DomainKernel
from .joint_objective import fingerprint, require


VERSION = 'set-acquisition-fit-v1'


def parameter_masks(model):
    """Return the exact prospective 57 intervention + 11 set-column mask."""
    require(type(model) is DomainKernel and model.pair[0].out_features == 11 and
            model.persistence is False and model.role_tying is False and model.memory is True,
            'set acquisition requires the frozen 562-parameter world configuration')
    predictor_spec(model=model)  # Also checks the registered module topology.
    parameters = dict(model.named_parameters())
    require(sum(p.numel() for p in parameters.values()) == 562 and all(
        p.device.type == 'cpu' and p.dtype == torch.float64 and p.layout == torch.strided and
        bool(torch.isfinite(p).all()) for p in parameters.values()), 'invalid world tensors')
    masks = {name: torch.full_like(p, name.startswith('intervention.'), dtype=torch.bool)
             for name, p in parameters.items()}
    masks['background.0.weight'][:, 2] = True
    require(sum(int(mask.sum()) for mask in masks.values()) == 68 and
            sum(p.numel() for name, p in parameters.items() if name.startswith('intervention.')) == 57,
            'permitted parameter mask differs')
    return masks


def fit_masked(model, batches, settings):
    """Fit once; return provenance, or retain interrupted provenance and raise.

Settings supply updates, learning_rate, cpu_seconds and gradient_clip. Existing
path limits default to 64/512. Caller requires-grad flags are restored on exit;
no optimizer state or gradient hook survives. Curve indices count completed
updates, so the first and last measurements are the actual endpoint losses.
"""
    require(type(settings) is dict, 'fit settings required')
    updates, rate, ceiling, clip = (settings[k] for k in
                                  ('updates', 'learning_rate', 'cpu_seconds', 'gradient_clip'))
    limit, expansions = settings.get('live_path_limit', 64), settings.get('candidate_expansions', 512)
    require(type(updates) is int and updates > 0 and all(type(v) in (int, float) and
        math.isfinite(v) and v > 0 for v in (rate, ceiling, clip)) and
        type(limit) is int and limit > 0 and type(expansions) is int and expansions > 0,
        'invalid masked fit budget')
    setup = perf_counter()
    masks, parameters = parameter_masks(model), dict(model.named_parameters())
    original = {name: p.detach().clone() for name, p in parameters.items()}
    flags = {name: p.requires_grad for name, p in parameters.items()}
    data, data_hash = learning._dataset(batches)
    require(all(bool(b.masks.all()) and bool((b.actions[..., 0] == 1).all()) for b in data),
            'set acquisition requires complete observed set-only tapes')
    events = sum(b.actions.shape[0] * b.actions.shape[1] for b in data)
    require(events > 0, 'no observed set events')
    complement = lambda: {name: p.detach()[~masks[name]] for name, p in parameters.items()
                          if bool((~masks[name]).any())}
    immutable = fingerprint(complement())
    common = {'version': VERSION, 'objective': 'observed_joint_nll', 'training_input_sha256': data_hash,
        'history_sha256': [b.digest() for b in data], 'training_source_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
        'predictor': predictor_spec(model=model),
        'parent_checkpoint_state_sha256': getattr(model, 'checkpoint_metadata', {}).get('state_sha256'),
        'initial_weights_sha256': fingerprint(original), 'parameters': 562, 'permitted_scalars': 68,
        'immutable_scalars': 494, 'immutable_before_sha256': immutable,
        'parameter_mask': {name: 'all' if bool(mask.all()) else {'column': 2}
                           for name, mask in masks.items() if bool(mask.any())},
        'requested_updates': updates, 'optimizer': 'Adam', 'learning_rate': float(rate),
        'optimizer_defaults': {'betas': [.9, .999], 'eps': 1e-8, 'weight_decay': 0., 'amsgrad': False},
        'gradient_clip': float(clip), 'mask_before_clipping': True, 'fresh_optimizer': True,
        'live_path_limit': limit, 'candidate_expansion_limit': expansions,
        'extended_domain_training': any(b.observations.shape[-1] > 3 for b in data),
        'observed_events_per_update': events, 'action_events_per_update': events,
        'visible_bits_per_update': sum(int(b.masks[1:].sum()) for b in data),
        'cpu_ceiling_seconds': float(ceiling), 'optimizer_resume_supported': False,
        'capacity_or_consumed_compute_match_established': False}
    hook, completed, curve, last_cpu = None, 0, [], 0.
    cost = {'path_model_evaluations': 0, 'candidate_worlds': 0, 'max_live_paths_per_episode': 1,
            'observed_replay_passes': 0}
    start, cpu_start, setup_seconds = perf_counter(), process_time(), 0.

    def objective(differentiable):
        terms = []
        for batch in data:
            result = learning.replay(batch, model=model, differentiable=differentiable,
                                     limit=limit, expansion_limit=expansions)
            require(result['loss'] is not None and result['observed_events'] ==
                    batch.actions.shape[0] * batch.actions.shape[1], 'incomplete observed set support')
            terms.append(result['loss'] * result['observed_events'])
            for key in ('path_model_evaluations', 'candidate_worlds'): cost[key] += result['costs'][key]
            cost['max_live_paths_per_episode'] = max(cost['max_live_paths_per_episode'],
                                                    result['costs']['max_live_paths_per_episode'])
        cost['observed_replay_passes'] += 1
        loss = torch.stack(terms).sum() / events
        require(bool(torch.isfinite(loss)), 'nonfinite observed set loss')
        return loss

    def changes():
        changed = {name: p.detach().view(torch.int64) != original[name].view(torch.int64)
                   for name, p in parameters.items()}
        return {name: sum(int((value & (masks[key] if allowed else ~masks[key])).sum())
                         for key, value in changed.items())
                for name, allowed in (('changed_permitted_scalars', True), ('changed_forbidden_scalars', False))}

    def receipt(status, reason, final_loss=None):
        cpu = process_time() - cpu_start
        return {**common, 'status': status, 'stop_reason': reason, 'completed_updates': completed,
            'all_prescribed_updates_completed': completed == updates, 'curve': curve,
            'initial_observed_train_nll': curve[0][1] if curve else None,
            'final_observed_train_nll': final_loss, 'final_weights_sha256': fingerprint(model.state_dict()),
            'immutable_after_sha256': fingerprint(complement()), **changes(),
            'setup_wall_seconds': setup_seconds, 'fit_wall_seconds': perf_counter() - start,
            'fit_cpu_seconds': cpu, 'cpu_overshoot_seconds': max(0., cpu - ceiling),
            'last_step_cpu_seconds': last_cpu, 'costs': dict(cost),
            'cost_scope': 'Optimizer loop, per-step preservation checks and final observed-training measurement; setup separate.',
            'process_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}

    try:
        for name, p in parameters.items():
            p.grad = None
            p.requires_grad_(bool(masks[name].any()))
        active = [p for p in parameters.values() if p.requires_grad]
        hook = parameters['background.0.weight'].register_hook(lambda g: g * masks['background.0.weight'])
        optimizer = torch.optim.Adam(active, lr=rate, weight_decay=0.)
        setup_seconds = perf_counter() - setup
        start, cpu_start = perf_counter(), process_time()
        for _ in range(updates):
            if process_time() - cpu_start >= ceiling: raise TimeoutError('masked fit CPU ceiling exhausted')
            step = process_time()
            optimizer.zero_grad(set_to_none=True)
            loss = objective(True)
            curve.append([completed, float(loss.detach())])
            loss.backward()
            require(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in active),
                    'missing or nonfinite permitted gradient')
            torch.nn.utils.clip_grad_norm_(active, clip, error_if_nonfinite=True)
            optimizer.step()
            completed += 1
            require(all(bool(torch.isfinite(p).all()) for p in parameters.values()), 'nonfinite learned tensor')
            require(fingerprint(complement()) == immutable, 'forbidden parameter update')
            last_cpu = process_time() - step
            if process_time() - cpu_start > ceiling: raise TimeoutError('masked fit CPU ceiling exhausted')
        final_loss = float(objective(False))
        curve.append([completed, final_loss])
        require(learning._dataset(batches)[1] == data_hash, 'fit changed delivered observations/actions')
        require(fingerprint(complement()) == immutable, 'forbidden parameter update')
        if process_time() - cpu_start > ceiling: raise TimeoutError('masked fit CPU ceiling exhausted')
        report = receipt('COMPLETED', 'update_limit', final_loss)
        learning._training_state(model, report)
        return report
    except BaseException as error:
        interrupted = {**common, 'status': 'INTERRUPTED', 'stop_reason': 'cpu_limit' if
            isinstance(error, TimeoutError) else 'exception', 'completed_updates': completed,
            'final_weights_sha256': None, 'error_type': type(error).__name__, 'error': str(error)}
        learning._training_state(model, interrupted)  # Invalidate stale identity before fallible diagnostics.
        try:
            interrupted.update(receipt('INTERRUPTED', interrupted['stop_reason']))
            learning._training_state(model, interrupted)
        except BaseException:
            pass  # Keep the original error and explicit unavailable endpoint metadata.
        raise
    finally:
        if hook is not None: hook.remove()
        for name, p in parameters.items():
            p.grad = None
            p.requires_grad_(flags[name])
