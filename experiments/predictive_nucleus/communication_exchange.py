"""One optional communication turn before a binary physical decision.

Physical observations, source observations and attributed wire content have
separate receipts. The task supplies a two-symbol measurement code; only the
value of asking and how to use attributed content are learned. Time here is the
communication trial clock; native_step identifies the archived physical probe.
"""
from itertools import product

from .acceptance_contract import digest, require
from .communication_policy import Witness
from .communication_score import STRATA

TOKENS = ('lo', 'hi')


def _receipt(tag, **body):
    return {**body, 'id': digest([tag, body])}


def ledger(*receipts):
    """Repeated receipt identities add no independent evidence, including conflicts."""
    unique = {}
    for receipt in receipts:
        key = receipt['id']
        require(key not in unique or unique[key] == receipt, 'receipt collision')
        unique[key] = receipt
    return tuple(unique.values())


def _view(matrix, support, token):
    if token not in TOKENS or TOKENS.index(token) not in support:
        return None
    return tuple(matrix[TOKENS.index(token)])


def rounds(case, law, split):
    """Yield all scheduled potential interventions. The runner exposes feedback after action.

    Public policy arguments are prior, witness metadata, opportunity, cost and
    the requested arm's view. Physical outcomes, true world, private source
    observation, report provenance and counterfactuals remain environment data.
    """
    focus = case['entities'][0]
    for stratum in STRATA:
        source = 'B' if stratum in ('misleading', 'conflict') else 'A'
        time = 0 if stratum == 'stale' else 1
        report_focus = case['entities'][1] if stratum == 'shifted' else focus
        witness = Witness(source, 1 - time, report_focus == focus)
        schedule = {}
        for h, rep in product(range(2), range(4)):
            identity = digest(['g4-round-v1', law, split, case['id'], stratum, h, rep])
            # Past and off-focus sources observe a separate balanced event. In
            # the shifted condition it is an independent probe on another roster
            # member, not an implicit second reading of the current probe.
            bit = rep % 2 if stratum in ('stale', 'shifted') else h
            if stratum in ('stale', 'shifted'):
                # An independently generated G4 probe has no G3 native receipt.
                observed = _receipt('independent-probe', episode=identity, source=source,
                    time=time, focus=report_focus, reading=bit, kind='synthetic_g4_probe')
            else:
                base = case['witness'][h]
                observed = _receipt('source-observation', episode=identity, source=source, time=time,
                    focus=focus, native_step=base['time'], native_evidence=base['id'],
                    reading=bit, kind='archived_calibration')
            content = bit ^ int(source == 'B')
            token = f'unregistered-{content}' if stratum == 'unknown' else TOKENS[content]
            report = _receipt('source-claim', episode=identity, source=source, time=time,
                focus=report_focus, evidence_id=observed['id'], token=token)
            schedule[h, rep] = identity, observed, report

        for (h, rep), (identity, observed, report) in schedule.items():
            matrix = ((1., 1.), (1., 1.)) if stratum == 'irrelevant' else case['predicted']
            known = stratum in ('known', 'conflict')
            support = (h,) if known else (0, 1)
            prior = tuple(sum(matrix[k][a] for k in support) / len(support) for a in (0, 1))
            opportunity = len({int(matrix[k][1] > matrix[k][0]) for k in support}) > 1
            anchor = _receipt('receiver-anchor', source='local', time=0, entities=case['entities'],
                              reading=case['anchor'])
            physical = [anchor]
            if known:
                physical.append(_receipt('receiver-observation', episode=identity, source='local', time=1,
                    focus=focus, reading=h, native_evidence=case['witness'][h]['id']))
            prior_claims, on_file_observations = (), ()
            if stratum == 'conflict':
                # A's earlier report is retained separately from both the local
                # instrument and B's possible reply during the single paid turn.
                prior_observed = _receipt('source-observation', episode=identity, source='A', time=1,
                    focus=focus, reading=h, native_step=case['witness'][h]['time'],
                    native_evidence=case['witness'][h]['id'], kind='archived_calibration')
                on_file_observations = (prior_observed,)
                prior_claims = ledger(_receipt('source-claim', episode=identity, source='A', time=1,
                    focus=focus, evidence_id=prior_observed['id'], token=TOKENS[h]))
            sensor = {'observations': ledger(*physical), 'support': support, 'prior': prior,
                      'claims_on_file': prior_claims}
            # A fixed-point-free permutation: low reps exchange replicates;
            # high reps exchange truths. Half the current witness bits change.
            donor = (h, rep ^ 1) if rep < 2 else (h ^ 1, rep)
            shuffled = schedule[donor][2]
            random_bit = int(digest(['independent-wire-v1', identity])[:16], 16) % 2
            random_token = f'unregistered-{random_bit}' if stratum == 'unknown' else TOKENS[random_bit]
            claims, views = {}, {}
            for arm, origin, token in (('delivered', report, report['token']),
                                       ('shuffled', shuffled, shuffled['token']),
                                       ('random', report, random_token)):
                claims[arm] = _receipt('wire-delivery', episode=identity, intervention=arm,
                    origin=origin['episode'], origin_claim_id=origin['id'], source=origin['source'],
                    evidence_id=origin['evidence_id'], time=origin['time'], focus=origin['focus'],
                    token=token, resolved=token in TOKENS)
                views[arm] = _view(matrix, support, token)
            yield dict(id=identity, case_id=case['id'], h=h, rep=rep, stratum=stratum,
                cost=.75 if stratum == 'costly' else .05, witness=witness, prior=prior,
                opportunity=opportunity, sensor=sensor, source_sensor=observed, source_claim=report, claims=claims,
                on_file_source_sensors=on_file_observations, views=views, rewards=[1, 1] if stratum == 'irrelevant' else list(case['rewards'][h]))
