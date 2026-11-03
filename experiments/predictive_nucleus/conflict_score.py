"""Replay the sealed matched-convention choices against physical payoffs."""
from collections import Counter, defaultdict
from math import exp, isfinite

from .acceptance_contract import require
from .conflict_task import ARMS, FEES, cases


def _best(pair):
    return int(pair[1] > pair[0])


def _mixture(matrix, p):
    return tuple((1-p)*a + p*b for a, b in zip(*matrix, strict=True))


def _expected(case, fits, env):
    e = case['public']
    own, other = sorted(dict(e.probe_claims))
    old, new = dict(e.probe_claims), dict(e.target_claims)
    a, y = e.probe_action, e.probe_reward
    x = (2*y-1) * (e.probe_matrix[old[other]][a] - e.probe_matrix[old[own]][a])

    def reading(weight, discrete):
        z = x * weight
        q = (.5 if z == 0 else int(z > 0)) if discrete else 1 / (1 + exp(-z))
        return (1-q)*new[own] + q*new[other]

    fit = fits[env]
    main = reading(fit['neural'], False)
    result = dict(learned=main, suppressed=main, shuffled=main, free_silent=.5,
                  empirical=reading(fit['empirical'], True), crossed=reading(fits[1-env]['neural'], False),
                  blind=(new[own]+new[other])/2)
    for i, bit in enumerate(case['ca']):
        supports = int(_best(e.probe_matrix[bit]) == a) == y
        q = 2/3 if supports else 0.
        if fit['empirical'] < 0:
            q = 1-q
        result['fixed'+str(i)] = q*case['cb'][i] + (1-q)*.5
    return result


def _replay(cell, p, arm, matrix, truth, donor_bit):
    require(isinstance(cell, (list, tuple)) and len(cell) == 2+len(FEES) and
            type(cell[0]) in (int, float) and isfinite(cell[0]) and abs(cell[0]-p) <= 1e-10,
            'saved belief differs from checkpoint')
    utility = _mixture(matrix, p)
    pre = _best(utility)
    require(type(cell[1]) is int and cell[1] == pre, 'invalid unassisted action')
    value = (1-p)*max(matrix[0]) + p*max(matrix[1]) - max(utility)
    for fee, code in zip(FEES, cell[2:], strict=True):
        ask = fee is not None and arm != 'free_silent' and value > fee
        action = pre
        if ask and arm != 'suppressed':
            action = _best(matrix[donor_bit if arm == 'shuffled' else truth])
        require(type(code) is int and code == 2*ask + action, 'recorded request or action differs')
        yield int(ask), action


def _metrics():
    return {'pre_successes': 0, 'bit_brier_sum': 0.,
            'fees': [{'requests': 0, 'successes': 0, 'net_hundredths': 0} for _ in FEES]}


def score(law, seed, bank, raw, checkpoints):
    matrices = raw['live_matrices']
    archived = bank['forecasts'][str(seed)]
    require(matrices.keys() == archived.keys(), 'incomplete live matrix set')
    for pair in archived:
        for live, past in zip(matrices[pair], archived[pair], strict=True):
            for row, old in zip(live, past, strict=True):
                require(len(row) == 2 and _best(row) == _best(old) and
                        all(0 <= v <= 1 and abs(v-w) <= 1e-10 for v, w in zip(row, old, strict=True)),
                        'live G3 parity mismatch')
    bank = {**bank, 'forecasts': {str(seed): matrices}}
    targets = list(cases(bank, law, seed, 'challenge'))
    n = len(targets)
    require(n and n == len(raw['rows']) == len({t['id'] for t in targets}), 'raw bank coverage differs')
    require(len(checkpoints) == 2 and all(abs(c['neural']) <= 16 and
            c['empirical'] in (-1,1) for c in checkpoints), 'invalid trained conventions')
    reports = []
    checks = {}
    twin_count = twin_hits = training_blind_best = 0
    for env in (0,1):
        counts = {arm: _metrics() for arm in ARMS}
        strata = Counter()
        projections = {name: defaultdict(Counter) for name in ('no_attribution', 'no_probe_payoff')}
        uncertainty = 0.
        missed = []
        for i, (case, row) in enumerate(zip(targets, raw['rows'], strict=True)):
            require(case['index'] == i and len(row) == 4 and row[:2] == [case['id'], case['pubhash']],
                    'wrong paired input or order')
            matrix = case['public'].target_matrix
            truth = case['target_bits'][env]
            rewards = case['rewards'][env]
            require(sorted(rewards) == [0,1], 'expected unique physical optimum')
            strata['native_misses'] += _best(rewards) != _best(matrix[truth])
            donor = case['donor']
            require(0 <= donor < n and donor != i, 'invalid verification donor')
            calibration = case['ca'][0] != case['ca'][1]
            conflict = case['cb'][0] != case['cb'][1]
            critical, unresolved = calibration and conflict, not calibration and conflict
            group = 'critical' if critical else 'unresolved' if unresolved else 'agreement'
            strata[group] += 1
            expected = _expected(case, checkpoints, env)
            cells = dict(zip(ARMS, row[2+env], strict=True))
            for arm, cell in cells.items():
                p = expected[arm]
                x = counts[arm]
                x['bit_brier_sum'] += (p-truth)**2
                selections = _replay(cell, p, arm, matrix, truth, targets[donor]['target_bits'][env])
                for k, (ask, action) in enumerate(selections):
                    f = x['fees'][k]
                    gross = rewards[action]
                    f['successes'] += gross
                    f['requests'] += ask
                    f['net_hundredths'] += 100*gross - round(100*(FEES[k] or 0))*ask
                    if arm == 'learned' and k == 0 and unresolved:
                        strata['unresolved_cheap_asks'] += ask
                        strata['unresolved_cheap_successes'] += gross
                    if arm == 'learned' and not (k == 0 and unresolved):
                        strata['unneeded_requests'] += ask
                x['pre_successes'] += rewards[cell[1]]
            pre = rewards[cells['learned'][1]]
            strata[group+'_successes'] += pre
            if unresolved:
                uncertainty = max(uncertainty, abs(cells['learned'][0]-.5))
            if critical:
                # Pair and site give the full native menus/forecasts. Retaining them also grants
                # the hindsight optimum a potentially stronger physical-context identifier.
                context = (case['pair'], case['first'], case['probe'])
                earlier = case['public'].probe_claims
                later = case['public'].target_claims
                anonymous = (context, case['probe_reward'], tuple(b for _, b in earlier),
                             tuple(b for _, b in later))
                projections['no_attribution'][anonymous][_best(rewards)] += 1
                projections['no_probe_payoff'][context, earlier, later][_best(rewards)] += 1
                strata['crossed_successes'] += rewards[cells['crossed'][1]]
                strata['blind_successes'] += rewards[cells['blind'][1]]
                if env == 1:
                    require(case['target_bits'][0] != truth, 'convention twin has same target')
                    twin_count += 1
                    training_blind_best += max(sum(pay[a] for pay in case['rewards']) for a in (0,1))
                    twin_hits += bool(pre and case['rewards'][0][row[2][ARMS.index('learned')][1]])
            if not pre and len(missed) < 3:
                missed.append([case['id'], group])
            strata['policy_disagreements'] += cells['learned'][1:] != cells['empirical'][1:]
        require(strata['critical'] == strata['unresolved'] and 4*strata['critical'] == n and
                2*strata['agreement'] == n, 'incomplete information strata')
        for x in counts.values():
            x['bit_brier'] = x.pop('bit_brier_sum') / n
            x['mean_net'] = sum(f['net_hundredths'] for f in x['fees']) / (100*n*len(FEES))
        main = counts['learned']
        bounds = {
            'critical_correct': strata['critical_successes'] >= .95*strata['critical'],
            'crossed_fails': strata['crossed_successes'] <= .10*strata['critical'],
            'blind_chance': 2*strata['blind_successes'] == strata['critical'],
            'agreement': strata['agreement_successes'] >= .95*strata['agreement'],
            'unresolved_chance': 2*strata['unresolved_successes'] == strata['unresolved'],
            'uncertainty': uncertainty <= .1,
            'useful_verification': strata['unresolved_cheap_asks'] >= .95*strata['unresolved'],
            'verified_success': strata['unresolved_cheap_successes'] >= .95*strata['unresolved'],
            'avoid_waste': strata['unneeded_requests'] == 0,
        }
        ceilings = {}
        for name, groups in projections.items():
            correct = sum(max(c.values()) for c in groups.values())
            ceilings[name] = dict(groups=len(groups), max_correct=correct, n=strata['critical'])
            bounds[name + '_ceiling'] = 2 * correct == strata['critical']
        for arm in ('fixed0','fixed1'):
            bounds[arm+'_ceiling'] = 4*counts[arm]['pre_successes'] <= 3*n
            bounds[arm+'_gain'] = main['pre_successes'] - counts[arm]['pre_successes'] > .05*n
        for arm in ('free_silent','suppressed','shuffled'):
            bounds['net_vs_'+arm] = main['mean_net'] - counts[arm]['mean_net'] > .03
        for k, (own, empirical) in enumerate(zip(main['fees'], counts['empirical']['fees'], strict=True)):
            bounds['empirical_fee_'+str(k)] = own['net_hundredths'] - empirical['net_hundredths'] >= -.5*n
        bounds['empirical_net'] = main['mean_net'] - counts['empirical']['mean_net'] >= -.005
        reports.append(dict(n=n, arms=counts, strata=dict(strata), max_unresolved_bias=uncertainty,
                            missed_examples=missed, ceilings=ceilings, checks=bounds))
        checks.update({f'{env}/{key}': bool(v) for key, v in bounds.items()})
    checks['training_blind_ceiling'] = training_blind_best == twin_count
    checks['both_convention_choices'] = twin_hits >= .95*twin_count
    return dict(law=law, seed=seed, conventions=reports, twin_count=twin_count, twin_hits=twin_hits,
                training_blind_critical_ceiling=dict(max_correct=training_blind_best, n=2*twin_count),
                checks=checks, passed=all(checks.values()),
                empirical_tie=all(r['strata']['policy_disagreements'] == 0 for r in reports))
