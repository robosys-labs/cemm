"""Unchanged numerical gates with explicit opened-study provenance for v3.

This wrapper performs saved-record arithmetic only. All candidate and control
forecasts come from current v3 execution. The runner binds either the published
v1 reference forecasts or newly collected reference forecasts from the frozen
v2 checkpoint under the v3 runtime. Both banks remain opened regression evidence,
not independent fresh validation. No cross-runtime control reproduction is assumed.
"""
from . import acceptance_contract as c, effect_role_scoring as v1, effect_role_scoring_v2 as v2

analyze, retention = v1.analyze, v1.retention


def analyze_opened(bundle, traces, archive, limits, reference_study):
    """Reuse v2 arithmetic and canonical retention gates for a named archive."""
    c.require(type(reference_study) is str and reference_study in ('v1', 'v2'),
              'opened reference study must be v1 or v2')
    result = v2.analyze_opened(bundle, traces, archive, limits)
    result['version'] = 'effect-role-opened-regression-v3'
    result['reference_study'] = reference_study
    roles = result['evidence_roles']
    for arm in ('grounded', 'masked', 'parser', 'text_only'): roles[arm]['origin'] = 'current_v3'
    roles['parser']['role'] = 'parser_control'
    roles['text_only'].pop('reproduction_required')
    roles['reference_grounded']['origin'] = ('archived_v1' if reference_study == 'v1'
                                           else 'frozen_v2_checkpoint_reforecast')
    return result
