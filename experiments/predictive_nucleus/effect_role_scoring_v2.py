"""Unchanged fresh G3 scoring plus prospective retention of the opened v1 bank.

Only saved records are read. The runner binds the immutable v1 control/archive
bytes and verifies exact text-only reproduction. Masked comparisons describe a
control; only canonical forecasts define retained competence. Ambiguous actual
world changes remain visible without becoming identifiable-world regressions.
"""
import math

from . import acceptance_contract as c, effect_role_scoring as v1
from .acceptance_scoring import _safe
from .bilingual_scoring import _difference

# Exact reuse: no new fresh thresholds, denominators or historical retention law.
analyze, retention = v1.analyze, v1.retention


def _number(value):
    if value == 'positive_infinity': return math.inf
    if value == 'negative_infinity': return -math.inf
    c.require(type(value) in (int, float) and not math.isnan(value), 'invalid saved score')
    return value


def _compare(current, archived):
    now = {(p['episode'], p['step']): p for p in current}
    c.require(len(now) == len(current) and now.keys() == archived.keys(), 'opened comparison inventory differs')
    rows = []
    for key in sorted(now):
        point, old = now[key], archived[key]
        nll, old_nll, kl, old_kl = map(_number, (point['nll'], old['nll'], point['oracle_kl'], old['oracle_kl']))
        rows.append({'id': key[0], 'step': key[1],
            **{name: point[name] for name in ('family', 'layout', 'word', 'new_word', 'held_layout',
                                             'answerable', 'action_index', 'correct', 'map_world',
                                             'action_correct', 'map_action', 'map_outside_support')},
            'archived_correct': old['correct'], 'archived_map_world': old['map_world'],
            'archived_action_correct': old['action_correct'], 'archived_map_action': old['map_action'],
            'archived_map_outside_support': old['map_outside_support'],
            'world_map_changed': point['map_world'] != old['map_world'],
            'action_map_changed': point['map_action'] != old['map_action'],
            'world_repair': point['correct'] and not old['correct'],
            'world_regression': old['correct'] and not point['correct'],
            'action_repair': point['action_correct'] and not old['action_correct'],
            'action_regression': old['action_correct'] and not point['action_correct'],
            'nll': nll, 'archived_nll': old_nll, 'nll_change': _difference(nll, old_nll),
            'true_probability_change': math.exp(-nll) - math.exp(-old_nll),
            'oracle_kl': kl, 'archived_oracle_kl': old_kl, 'oracle_kl_change': _difference(kl, old_kl),
            'oracle_total_variation': point['oracle_total_variation'],
            'archived_oracle_total_variation': old['oracle_total_variation']})
    inventory = {name: [[r['id'], r['step']] for r in rows if r[field]] for name, field in (
        ('world_repairs', 'world_repair'), ('world_regressions', 'world_regression'),
        ('world_map_changes', 'world_map_changed'), ('action_repairs', 'action_repair'),
        ('action_regressions', 'action_regression'), ('action_map_changes', 'action_map_changed'))}
    for name, flag in (('identifiable', True), ('ambiguous', False)):
        for change in ('repair', 'regression'):
            inventory[name + '_world_' + change + 's'] = [[r['id'], r['step']] for r in rows
                if r['answerable'] == flag and r['world_' + change]]
    for name, flag in (('new_word', True), ('old_word', False)):
        for change in ('repair', 'regression'):
            inventory[name + '_action_' + change + 's'] = [[r['id'], r['step']] for r in rows
                if r['new_word'] == flag and r['action_' + change]]
    mean = lambda field: math.fsum(r[field] / len(rows) for r in rows)
    nll, old_nll, kl, old_kl = (mean(field) for field in ('nll', 'archived_nll', 'oracle_kl', 'archived_oracle_kl'))
    return {'planned': len(rows), 'identifiable_planned': sum(r['answerable'] for r in rows),
        'ambiguous_planned': sum(not r['answerable'] for r in rows),
        **{name: sum(r[name] for r in rows) for name in
           ('correct', 'archived_correct', 'action_correct', 'archived_action_correct')}, **inventory,
        'nll_worse': sum(r['nll_change'] is not None and r['nll_change'] > 0 for r in rows),
        'nll_better': sum(r['nll_change'] is not None and r['nll_change'] < 0 for r in rows),
        'nll_equal': sum(r['nll_change'] == 0 for r in rows),
        'nll_undefined': sum(r['nll_change'] is None for r in rows),
        'mean_nll': nll, 'archived_mean_nll': old_nll, 'mean_nll_change': _difference(nll, old_nll),
        'mean_oracle_kl': kl, 'archived_mean_oracle_kl': old_kl, 'mean_oracle_kl_change': _difference(kl, old_kl),
        'points': rows}


def analyze_opened(bundle, traces, archive, limits):
    """Keep every v1 gate, add canonical regression gates, retain all failures.

``traces`` contains current grounded canonical/masked records and archived v1
parser/text-only canonical records. ``archive`` is v1 grounded canonical/masked.
All globally taught action identities, both old and newly acquired words, are
retained separately from endpoint equivalence. No new fit or forecast occurs.
"""
    planned, _, _ = v1._inventory(bundle)
    before = v1._trace(archive, planned, 'grounded')
    analysis = v1.analyze(bundle, traces, limits)
    comparisons = {view: _compare(analysis['points'][arm], before[view])
                   for view, arm in (('canonical', 'grounded'), ('masked', 'masked'))}
    canonical = comparisons['canonical']
    checks = {**analysis['checks'],
        'opened_identifiable_world_retention': not canonical['identifiable_world_regressions'],
        'opened_taught_action_retention': not canonical['action_regressions']}
    return _safe({'version': 'effect-role-opened-regression-v2', 'analysis': analysis,
        'comparisons': comparisons, 'checks': checks, 'passed': all(checks.values()),
        'evidence_roles': {
            'grounded': {'origin': 'current_v2', 'view': 'canonical', 'role': 'candidate'},
            'masked': {'origin': 'current_v2', 'view': 'masked', 'role': 'causal_control'},
            'parser': {'origin': 'archived_v1', 'view': 'canonical', 'role': 'descriptive_parser_baseline'},
            'text_only': {'origin': 'archived_v1', 'view': 'canonical', 'role': 'text_only_control',
                'reproduction_required': 'Runner verifies current v2 state and curve exactly reproduce v1.'},
            'reference_grounded': {'origin': 'archived_v1', 'views': ['canonical', 'masked'],
                'role': 'opened_regression_reference', 'gated_view': 'canonical'}}})
