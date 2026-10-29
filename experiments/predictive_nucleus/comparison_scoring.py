"""Frozen public comparison arithmetic; no model, fitter or simulator imports."""
from itertools import permutations, product
import math

import numpy as np
import torch

WORLDS = np.array(list(product((0, 1), repeat=3)), dtype=np.int64)
PERMUTATIONS = tuple(permutations(range(3)))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def log_record(values):
    """Strict JSON encoding. Null means -inf, never a finite underflowed log."""
    a = np.asarray(values, dtype=np.float64)
    require(not np.isnan(a).any() and not np.isposinf(a).any(), 'invalid log vector')
    return {'values': np.where(np.isneginf(a), None, a).tolist(),
            'null_status': 'negative_infinity'}


def normalize(raw, answered):
    """ONE uniform log normalization, including empirical and no-change controls."""
    require(isinstance(raw, torch.Tensor) and raw.dtype == torch.float64 and raw.device.type == 'cpu'
            and raw.ndim == 2 and raw.shape[1] == 8, 'expected CPU float64 eight-world matrix')
    mask = np.asarray(answered)
    require(mask.dtype == np.bool_ and mask.shape == (len(raw),), 'invalid answered mask')
    active = raw[torch.from_numpy(mask)]
    require(not bool((torch.isnan(active) | torch.isposinf(active)).any()), 'invalid log values')
    total = active.logsumexp(-1)
    require(bool(torch.isfinite(total).all()) and bool((total.abs() <= 1e-10).all()),
            'raw log mass outside frozen tolerance')
    normalized = active - total[:, None]
    probabilities = normalized.exp()
    require(bool(torch.isfinite(probabilities).all()) and bool(((probabilities >= 0) &
            (probabilities <= 1)).all()) and bool(((probabilities.sum(-1) - 1).abs() <= 1e-12).all()),
            'invalid normalized probabilities')
    result = torch.full_like(raw, -torch.inf)
    result[torch.from_numpy(mask)] = normalized
    correction = np.zeros(len(raw), dtype=np.float64)
    correction[mask] = total.numpy()
    return result.numpy(), correction


def score(logp, answered, truth, pre, raw=None):
    """Vectorized complete-world scores; retain infinite NLL and abstention."""
    logp, answered, truth, pre = map(np.asarray, (logp, answered, truth, pre))
    require(logp.shape == (*answered.shape, 8) and truth.shape == pre.shape == (*answered.shape, 3),
            'score shape mismatch')
    require(answered.dtype == np.bool_ and np.isin(truth, (0, 1)).all() and np.isin(pre, (0, 1)).all(),
            'invalid score inputs')
    require(not np.isnan(logp[answered]).any() and not np.isposinf(logp[answered]).any(), 'invalid score logs')
    p = np.exp(logp)
    require(np.all(np.abs(p[answered].sum(-1) - 1) <= 1e-12), 'score requires normalized probabilities')
    gold = truth @ np.array([4, 2, 1])
    best = logp.argmax(-1)  # first lexicographic maximum
    correct = answered & (best == gold)
    log_truth = np.take_along_axis(logp, gold[..., None], -1)[..., 0]
    nll = -log_truth
    brier = (p * p).sum(-1) - 2 * np.take_along_axis(p, gold[..., None], -1)[..., 0] + 1
    confidence = p.max(-1)
    maxima = (logp == logp.max(-1)[..., None]) & answered[..., None]
    unchanged = truth == pre
    wrong_bits = (WORLDS[best] != truth) & unchanged & answered[..., None]
    result = {'answered': answered, 'correct': correct, 'map': best, 'nll': nll, 'brier': brier,
              'confidence': confidence, 'maximizers': maxima, 'unchanged_bit_errors': wrong_bits.sum(-1),
              'unchanged_bits_answered': (unchanged & answered[..., None]).sum(-1),
              'underflow': (np.isfinite(logp) & (p == 0) & answered[..., None]).sum(-1)}
    if raw is not None:
        raw = np.asarray(raw)
        before = (raw == raw.max(-1)[..., None]) & answered[..., None]
        result['maximizers_changed'] = (before != maxima).any(-1) & answered
        result['map_changed'] = (raw.argmax(-1) != best) & answered
    return result


def summary(scores, selection=None):
    chosen = np.ones_like(scores['answered']) if selection is None else np.asarray(selection, dtype=bool)
    require(chosen.shape == scores['answered'].shape, 'summary selection mismatch')
    answered = scores['answered'] & chosen
    n, a = int(chosen.sum()), int(answered.sum())
    c = int((scores['correct'] & chosen).sum())
    infinite = int(np.isposinf(scores['nll'][answered]).sum())
    ece, bins = 0.0, []
    for i in range(10):
        group = answered & (scores['confidence'] >= i / 10) & (
            scores['confidence'] <= 1 if i == 9 else scores['confidence'] < (i + 1) / 10)
        size = int(group.sum())
        acc = float(scores['correct'][group].mean()) if size else None
        conf = float(scores['confidence'][group].mean()) if size else None
        if size:
            ece += size / a * abs(acc - conf)
        bins.append({'bin': i, 'count': size, 'accuracy': acc, 'confidence': conf})
    result = {'queries': n, 'answered': a, 'abstained': n - a, 'correct': c, 'wrong': a - c,
              'coverage': a / n if n else None, 'correct_per_query': c / n if n else None,
              'accuracy_among_answered': c / a if a else None,
              'nll_status': 'infinite' if infinite else ('finite' if a else 'no_answers'),
              'mean_nll': float(scores['nll'][answered].mean()) if a and not infinite else None,
              'infinite_nll_count': infinite,
              'mean_brier': float(scores['brier'][answered].mean()) if a else None,
              'ece_10': ece if a else None, 'ece_bins': bins,
              'unchanged_bit_errors': int(scores['unchanged_bit_errors'][answered].sum()),
              'unchanged_bits_answered': int(scores['unchanged_bits_answered'][answered].sum()),
              'underflow_world_count': int(scores['underflow'][answered].sum()),
              'tied_forecasts': int(((scores['maximizers'].sum(-1) > 1) & answered).sum())}
    for field in ('map_changed', 'maximizers_changed'):
        if field in scores:
            result['normalization_' + field] = int((scores[field] & chosen).sum())
    return result


def subset(scores, item):
    return {key: value[item] for key, value in scores.items()}


def renaming(logp, answered, n_cases):
    """Compare physical-coordinate distributions, separately from MAP tie breaks."""
    steps = len(logp)
    require(logp.shape == (steps, n_cases * 6, 8) and answered.shape == (steps, n_cases * 6),
            'renaming shape mismatch')
    p = np.exp(logp).reshape(steps, n_cases, 6, 8)
    answered = answered.reshape(steps, n_cases, 6)
    maps = logp.argmax(-1).reshape(steps, n_cases, 6)
    tv = np.full((steps, n_cases, 6), np.nan)
    changed = np.zeros_like(answered)
    for v, mapping in enumerate(PERMUTATIONS):
        inverse = np.argsort(mapping)
        lookup = WORLDS[:, inverse] @ np.array([4, 2, 1])
        physical = p[:, :, v, :][:, :, lookup]
        valid = answered[:, :, 0] & answered[:, :, v]
        tv[:, :, v][valid] = (np.abs(physical - p[:, :, 0]).sum(-1) / 2)[valid]
        physical_map = WORLDS[maps[:, :, v]][:, :, list(mapping)] @ np.array([4, 2, 1])
        changed[:, :, v] = valid & (physical_map != maps[:, :, 0])
    nonidentity = tv[:, :, 1:]
    comparable = np.isfinite(nonidentity)
    values = nonidentity[comparable]
    return {'comparisons': int(comparable.sum()), 'over_tolerance': int((values > 1e-10).sum()),
            'max_tv': float(values.max()) if len(values) else None,
            'median_tv': float(np.median(values)) if len(values) else None,
            'map_changed': int(changed[:, :, 1:].sum()),
            'status_changed': int((answered[:, :, 1:] != answered[:, :, :1]).sum())}, tv, changed


def paired(before, after):
    """Codes: 0 wrong, 1 correct, 2 abstained. IDs index the same case/view axis."""
    require(before.shape == after.shape and before.ndim == 1 and
            np.isin(before, (0, 1, 2)).all() and np.isin(after, (0, 1, 2)).all(), 'invalid paired codes')
    common = (before != 2) & (after != 2)
    result = {'queries': len(before), 'common_answered': int(common.sum()),
              'before_correct': int((before == 1).sum()), 'after_correct': int((after == 1).sum()),
              'before_wrong': int((before == 0).sum()), 'after_wrong': int((after == 0).sum()),
              'before_abstained': int((before == 2).sum()), 'after_abstained': int((after == 2).sum()),
              'common_before_correct': int(((before == 1) & common).sum()),
              'common_after_correct': int(((after == 1) & common).sum())}
    for name, a, b in [('correct_to_wrong', 1, 0), ('wrong_to_correct', 0, 1),
                        ('correct_to_abstained', 1, 2), ('abstained_to_correct', 2, 1)]:
        result[name] = np.flatnonzero((before == a) & (after == b)).tolist()
    return result


def role_pairs(codes, query, n_cases):
    require(n_cases > 0 and n_cases % 2 == 0 and codes.shape[1] == n_cases * 6, 'role-pair inventory')
    rows = codes[query].reshape(n_cases, 6)
    first, second = rows[::2], rows[1::2]
    return {'pairs': first.size, 'both_answered': int(((first != 2) & (second != 2)).sum()),
            'both_correct': int(((first == 1) & (second == 1)).sum()),
            'both_correct_ids': np.argwhere((first == 1) & (second == 1)).tolist(),
            'id_note': '[case_pair_index, view]; cases are 2*index and 2*index+1'}


def nearest_rank(values, percentile):
    require(bool(values) and 0 < percentile <= 1 and all(math.isfinite(x) and x >= 0 for x in values),
            'invalid latency sample')
    return sorted(values)[math.ceil(percentile * len(values)) - 1]
