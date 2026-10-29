"""One delivered-history path for learning and inference; no simulator or oracle.

The loss is one joint log score per event with any delivered reading. All-null
events advance the filter but add no loss. This is not a scientific gate runner.
"""
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
import math
import resource
from pathlib import Path
from time import perf_counter, process_time

import torch

from . import active_paths as paths, domain_contract as domain
from .joint_objective import fingerprint

require = domain.require
VERSION = 'active-learning-v1'


@dataclass(frozen=True)
class ObservedBatch:
    observations: torch.Tensor  # time+1, episode, physical entity; -1 means absent
    actions: torch.Tensor       # time, episode, kind/first/second/value
    masks: torch.Tensor         # time+1, episode, physical entity
    coverage: torch.Tensor      # time, episode, selected before feedback
    episode_ids: tuple

    def validate(self):
        x, a, mask, cover = self.observations, self.actions, self.masks, self.coverage
        require(all(isinstance(v, torch.Tensor) for v in (x, a, mask, cover)) and
                x.ndim == a.ndim == 3 and 0 < len(a) <= 128 and a.shape[-1] == 4 and
                x.shape[:2] == (len(a) + 1, a.shape[1]), 'invalid delivered-history shape')
        n = domain.validate_anchor(x[0], 1)
        require(mask.device.type == cover.device.type == 'cpu' and
                mask.dtype == cover.dtype == torch.bool and mask.shape == x.shape and
                cover.shape == x[1:].shape and bool(mask[0].all()) and
                bool(cover.any(-1).all()) and not bool((mask[1:] & ~cover).any()),
                'invalid delivered mask or precommitted coverage')
        require(type(self.episode_ids) is tuple and len(self.episode_ids) == a.shape[1] and
                all(type(v) is str and 0 < len(v) <= 128 for v in self.episode_ids) and
                len(set(self.episode_ids)) == len(self.episode_ids), 'unique episode IDs required')
        for t, action in enumerate(a):
            domain.validate_action(action, a.shape[1], n)
            domain.validate_reading(x[t + 1], mask[t + 1], a.shape[1], n)
        return self

    def digest(self):
        self.validate()
        tensors = fingerprint({k: getattr(self, k) for k in ('observations', 'actions', 'masks', 'coverage')})
        return sha256(json.dumps([VERSION, self.episode_ids, tensors], separators=(',', ':')).encode()).hexdigest()

    def snapshot(self):
        self.validate()
        return ObservedBatch(*(getattr(self, k).detach().clone() for k in
            ('observations', 'actions', 'masks', 'coverage')), self.episode_ids)


def _dataset(batches):
    require(type(batches) in (list, tuple) and bool(batches) and
            all(type(b) is ObservedBatch for b in batches), 'nonempty observed batches required')
    copies = tuple(b.snapshot() for b in batches)
    ids = [name for b in copies for name in b.episode_ids]
    require(len(ids) == len(set(ids)), 'duplicate episode identity across batches')
    digest = sha256(json.dumps([b.digest() for b in copies], separators=(',', ':')).encode()).hexdigest()
    return copies, digest


class ReplayFailure(ValueError):
    def __init__(self, step, phase, cause, result):
        super().__init__(str(cause))
        self.step, self.phase, self.cause_type = step, phase, type(cause).__name__
        self.result = result


def _filter(anchor, model, memory, control, limit, expansion_limit, differentiable):
    require(not (model is not None and memory is not None), 'choose one predictor')
    require(type(limit) is int and limit > 0 and type(expansion_limit) is int and expansion_limit > 0,
            'positive integer path and expansion limits required')
    if model is not None:
        require(control is None, 'neural predictor cannot also select a control')
        return paths.NeuralPaths(model, anchor, limit, expansion_limit, differentiable=differentiable)
    require(not differentiable, 'differentiable replay requires a neural model')
    if memory is not None:
        control = paths.empirical_control(memory, control)
        return paths.EmpiricalPaths(memory, anchor, first_contact=control == 'first_contact',
                                    limit=limit, expansion_limit=expansion_limit)
    require(control == 'no_change', 'a predictor or no_change control is required')
    return paths.LastObserved(anchor)


def _replay_result(batch, predictions, answers, likelihoods, cost):
    steps, episodes, entities = len(predictions), batch.actions.shape[1], batch.observations.shape[-1]
    logs = torch.stack(predictions) if steps else torch.empty(0, episodes, 2 ** entities, dtype=torch.float64)
    answered = torch.stack(answers) if steps else torch.empty(0, episodes, dtype=torch.bool)
    ll = torch.stack(likelihoods) if steps else torch.empty(0, episodes, dtype=torch.float64)
    visible = batch.masks[1:steps + 1].any(-1)
    scored, count = visible & answered, int(visible.sum())
    loss = -ll[visible].mean() if count and bool(answered[visible].all()) else None
    return {'log_probabilities': logs, 'answered': answered, 'observed_log_likelihood': ll,
            'scored': scored, 'loss': loss, 'observed_events': count,
            'history_sha256': batch.digest(), 'costs': dict(cost)}


def replay(batch, *, model=None, memory=None, control=None, differentiable=False,
           limit=64, expansion_limit=512):
    """Forecast each event before its feedback, preserving all finite histories.

    Unsupported likelihood entries are NaN internally and have answered=False;
    evaluate serializes them as null. loss is absent if observed support is not
    complete. It never renormalizes over only the answered subset for training.
    """
    require(type(batch) is ObservedBatch and type(differentiable) is bool, 'invalid replay arguments')
    observed = batch.snapshot()
    history = observed.digest()
    before = fingerprint(model.state_dict()) if model is not None else memory.digest() if memory is not None else None
    f = _filter(observed.observations[0], model, memory, control, limit, expansion_limit, differentiable)
    worlds = torch.tensor(domain.binary_worlds(observed.observations.shape[-1]), dtype=torch.float64)
    predictions, answers, likelihoods = [], [], []
    cost = {'path_model_evaluations': 0, 'candidate_worlds': 0, 'max_live_paths_per_episode': 1}
    with torch.set_grad_enabled(differentiable):
        for t, action in enumerate(observed.actions):
            phase = 'predict'
            try:
                raw, answered = f.predict(action)
                logs, _ = domain.normalize_tensor(raw, answered)
                answered = torch.as_tensor(answered, dtype=torch.bool)
                reading, mask = observed.observations[t + 1], observed.masks[t + 1]
                compatible = ((worlds[None] == reading[:, None, :]) | ~mask[:, None, :]).all(-1)
                ll = domain.safe_logsumexp(logs.masked_fill(~compatible, -torch.inf), -1)
                ll = torch.where(mask.any(-1), ll, torch.zeros_like(ll))
                ll = ll.masked_fill(~answered, torch.nan)
                predictions.append(logs); answers.append(answered); likelihoods.append(ll)
                diagnostic = f.diagnostic
                live = diagnostic.get('live_paths', [len(p) for p in getattr(f, 'paths', [])])
                cost['path_model_evaluations'] += sum(live) if live else len(action)
                cost['candidate_worlds'] += sum(diagnostic.get('candidate_expansions', [len(action) * len(worlds)]))
                phase = 'feedback'
                f.receive(reading, mask)
                cost['max_live_paths_per_episode'] = max(cost['max_live_paths_per_episode'],
                    max(f.diagnostic.get('live_paths', [1])))
            except Exception as error:
                raise ReplayFailure(t, phase, error,
                    _replay_result(observed, predictions, answers, likelihoods, cost)) from error
        result = _replay_result(observed, predictions, answers, likelihoods, cost)
    require(batch.digest() == history, 'replay input changed during execution')
    after = fingerprint(model.state_dict()) if model is not None else memory.digest() if memory is not None else None
    require(before == after, 'replay mutated learned state')
    return result


def _training_state(model, provenance):
    model.training_provenance = deepcopy(provenance)
    if hasattr(model, 'checkpoint_metadata'):
        del model.checkpoint_metadata  # The old artifact no longer describes current weights.
    if hasattr(model, 'domain_adaptation'):
        origin = deepcopy(model.domain_adaptation)
        origin.update(active_learned_parameters_sha256=provenance['final_weights_sha256'],
                      training_performed_since_adaptation=True,
                      extended_domain_training=provenance['extended_domain_training'],
                      training_input_sha256=provenance['training_input_sha256'],
                      training_provenance=deepcopy(provenance))
        model.domain_adaptation = origin


def fit(model, batches, *, updates, cpu_seconds, learning_rate=.02, limit=64, expansion_limit=512):
    """Fixed history replay with explicit update/CPU ceilings and actual costs."""
    require(type(updates) is int and updates > 0 and type(cpu_seconds) in (int, float) and
            math.isfinite(cpu_seconds) and cpu_seconds > 0 and type(learning_rate) in (int, float) and
            math.isfinite(learning_rate) and learning_rate > 0, 'invalid fit budget')
    require(isinstance(model, torch.nn.Module), 'neural model required')
    parameters = list(model.parameters())
    require(bool(parameters) and all(p.device.type == 'cpu' and p.dtype == torch.float64 and
            p.requires_grad and bool(torch.isfinite(p).all()) for p in parameters), 'invalid trainable tensors')
    setup = perf_counter()
    data, digest = _dataset(batches)
    event_count = sum(int(b.masks[1:].any(-1).sum()) for b in data)
    require(event_count > 0, 'no observed events for training')
    initial = fingerprint(model.state_dict())
    from .active_checkpoint import predictor_spec
    settings = {'optimizer': 'Adam', 'learning_rate': float(learning_rate),
                'optimizer_defaults': {'betas': [.9, .999], 'eps': 1e-8, 'weight_decay': 0., 'amsgrad': False},
                'live_path_limit': limit, 'candidate_expansion_limit': expansion_limit,
                'training_source_sha256': sha256(Path(__file__).read_bytes()).hexdigest(),
                'predictor': predictor_spec(model=model),
                'parent_checkpoint_state_sha256': getattr(model, 'checkpoint_metadata', {}).get('state_sha256'),
                'extended_domain_training': any(b.observations.shape[-1] > 3 or bool(
                    ((b.actions[..., 0] == 0) & (b.actions[..., 1] == b.actions[..., 2])).any()) for b in data)}
    optimizer = torch.optim.Adam(parameters, lr=learning_rate)
    setup_seconds = perf_counter() - setup
    start, cpu_start, completed, last_cpu = perf_counter(), process_time(), 0, 0.
    cost = {'path_model_evaluations': 0, 'candidate_worlds': 0, 'max_live_paths_per_episode': 1}
    mutation_started = False
    try:
        while completed < updates and process_time() - cpu_start < cpu_seconds:
            step_start = process_time()
            optimizer.zero_grad(set_to_none=True)
            terms = []
            for batch in data:
                result = replay(batch, model=model, differentiable=True, limit=limit, expansion_limit=expansion_limit)
                if result['observed_events']:
                    require(result['loss'] is not None, 'incomplete neural observed support')
                    terms.append(result['loss'] * result['observed_events'])
                for name in ('path_model_evaluations', 'candidate_worlds'):
                    cost[name] += result['costs'][name]
                cost['max_live_paths_per_episode'] = max(cost['max_live_paths_per_episode'],
                                                       result['costs']['max_live_paths_per_episode'])
            loss = torch.stack(terms).sum() / event_count
            require(bool(torch.isfinite(loss)), 'nonfinite observed joint loss')
            loss.backward()
            require(all(p.grad is not None and bool(torch.isfinite(p.grad).all()) for p in parameters),
                    'nonfinite or missing gradient')
            mutation_started = True
            optimizer.step()
            require(all(bool(torch.isfinite(p).all()) for p in parameters), 'nonfinite learned tensor')
            completed += 1
            last_loss, last_cpu = float(loss.detach()), process_time() - step_start
        require(_dataset(batches)[1] == digest, 'fit input changed during execution')
    except BaseException:
        if mutation_started:
            _training_state(model, {**settings, 'version': VERSION, 'status': 'INTERRUPTED',
                'objective': 'observed_joint_nll', 'training_input_sha256': digest,
                'completed_updates': completed, 'final_weights_sha256': fingerprint(model.state_dict())})
        raise
    cpu, wall = process_time() - cpu_start, perf_counter() - start
    require(completed > 0, 'budget exhausted before any optimizer update')
    final = fingerprint(model.state_dict())
    report = {**settings, 'version': VERSION, 'status': 'COMPLETED',
              'objective': 'observed_joint_nll', 'training_input_sha256': digest,
              'completed_updates': completed, 'requested_updates': updates,
              'stop_reason': 'update_limit' if completed == updates else 'cpu_limit',
              'initial_weights_sha256': initial, 'final_weights_sha256': final,
              'parameters': sum(p.numel() for p in parameters), 'observed_events_per_update': event_count,
              'action_events_per_update': sum(b.actions.shape[0] * b.actions.shape[1] for b in data),
              'visible_bits_per_update': sum(int(b.masks[1:].sum()) for b in data),
              'history_sha256': [b.digest() for b in data], 'last_preupdate_observed_nll': last_loss,
              'setup_wall_seconds': setup_seconds, 'fit_wall_seconds': wall, 'fit_cpu_seconds': cpu,
              'cpu_ceiling_seconds': cpu_seconds, 'cpu_overshoot_seconds': max(0., cpu - cpu_seconds),
              'last_step_cpu_seconds': last_cpu, 'costs': cost,
              'process_peak_rss_kib': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'optimizer_resume_supported': False, 'capacity_or_consumed_compute_match_established': False}
    _training_state(model, report)
    return report


def fit_empirical(batches, *, mode, first_contact=False):
    """Count only fully delivered outcomes with sufficient delivered context."""
    require(type(first_contact) is bool and (not first_contact or mode == 'contact'), 'invalid empirical policy')
    data, digest = _dataset(batches)
    memory = domain.DomainMemory(mode)
    table, counted, incomplete_current, incomplete_history = defaultdict(Counter), 0, 0, 0
    for batch in data:
        states, actions = batch.observations.long().tolist(), batch.actions.tolist()
        for e in range(batch.actions.shape[1]):
            past = ()
            for t in range(len(actions)):
                before, action, after = tuple(states[t][e]), tuple(actions[t][e]), tuple(states[t + 1][e])
                context = tuple(row for row in past if row[1][0] == 0)[:1] if first_contact else past
                history_known = (mode == 'local' or all(
                    all(bit in (0, 1) for bit in pre + post) if mode == 'prefix' else
                    act[0] != 0 or all(pre[i] in (0, 1) and post[i] in (0, 1) for i in act[1:3])
                    for pre, act, post in context))
                if any(bit not in (0, 1) for bit in before + after):
                    incomplete_current += 1
                elif not history_known:
                    incomplete_history += 1
                else:
                    key, order = domain.domain_context(before, action, context, mode)
                    table[key][tuple(after[i] for i in order)] += 1
                    counted += 1
                past += ((before, action, after),)
    memory.table = dict(table)
    memory.control_name = 'first_contact' if first_contact else mode
    report = {'version': VERSION, 'objective': 'observed_counts', 'completed_updates': 0,
              'training_input_sha256': digest, 'history_sha256': [b.digest() for b in data],
              'action_events': sum(b.actions.shape[0] * b.actions.shape[1] for b in data),
              'counted_events': counted, 'skipped_incomplete_current': incomplete_current,
              'skipped_incomplete_history': incomplete_history, 'first_contact': first_contact,
              'table_sha256': memory.digest(), 'entries': len(memory.table), 'hidden_values_imputed': False,
              'training_source_sha256': sha256(Path(__file__).read_bytes()).hexdigest()}
    memory.training_provenance = deepcopy(report)
    return memory, report


def _number(value):
    if math.isnan(value): return None
    if math.isinf(value): return 'negative_infinity' if value < 0 else 'positive_infinity'
    return value


def evaluate(batches, *, model=None, memory=None, control=None, limit=64, expansion_limit=512):
    """Report delivered-event likelihood and coverage; no hidden gold or gate admission.

    A failed replay retains its planned denominator and explicit failure. Overall
    NLL is absent for incomplete support; answered-only NLL is labeled conditional.
    """
    data, digest = _dataset(batches)
    records, loss_sum, scored, answered_count, failures = [], 0., 0, 0, 0
    planned = sum(b.actions.shape[0] * b.actions.shape[1] for b in data)
    observed = sum(int(b.masks[1:].any(-1).sum()) for b in data)
    for batch in data:
        failure = {}
        try:
            result = replay(batch, model=model, memory=memory, control=control,
                            limit=limit, expansion_limit=expansion_limit)
        except ReplayFailure as error:
            failures += 1
            result = error.result
            failure = {'step': error.step, 'phase': error.phase, 'error_type': error.cause_type,
                       'message': str(error), 'feedback_committed': False if error.phase == 'feedback' else None}
        scored += int(result['scored'].sum())
        answered_count += int(result['answered'].sum())
        loss_sum -= float(result['observed_log_likelihood'][result['scored']].sum())
        likelihood = [[_number(value) for value in row] for row in result['observed_log_likelihood'].tolist()]
        forecast = domain.log_record(result['log_probabilities'].numpy())
        for t, row in enumerate(result['answered'].tolist()):
            for e, answered in enumerate(row):
                if not answered: forecast['values'][t][e] = None
        forecast['null_distribution_status'] = 'unsupported_prediction'
        records.append({'episode_ids': batch.episode_ids, 'status': 'REPLAY_ERROR' if failure else 'REPLAYED',
                        'history_sha256': result['history_sha256'], 'answered': result['answered'].tolist(),
                        'scored': result['scored'].tolist(), 'observed_log_likelihood': likelihood,
                        'log_probabilities': forecast, 'costs': result['costs'], **failure})
    predictor = model if model is not None else memory
    report = {'version': VERSION, 'gate_g1': 'NOT_ADMITTED', 'scope': 'delivered_observations_only',
              'evaluation_input_sha256': digest,
              'training_provenance': deepcopy(getattr(predictor, 'training_provenance', None)),
              'planned_action_events': planned, 'observed_events': observed,
              'scored_events': scored, 'answered_forecasts': answered_count, 'failed_batches': failures,
              'forecast_coverage': answered_count / planned,
              'observed_coverage': scored / observed if observed else None,
              'observed_nll': _number(loss_sum / observed) if observed and scored == observed else None,
              'conditional_observed_nll': _number(loss_sum / scored) if scored else None,
              'records': records}
    json.dumps(report, allow_nan=False)
    return report
