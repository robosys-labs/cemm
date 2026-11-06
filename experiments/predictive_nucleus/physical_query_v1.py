"""Expected value of an observed physical answer over finite hypotheses."""
from math import fsum, isfinite


def _row(values, probability=False):
    row = tuple(values)
    if not row or any(type(value) not in (int, float) or not isfinite(value) for value in row):
        raise ValueError('expected nonempty finite numeric values')
    if probability:
        if min(row) < 0 or max(row) > 1. + 1e-10 or abs(fsum(row) - 1.) > 1e-10:
            raise ValueError('expected normalized nonnegative probabilities')
        total = fsum(row)
        return tuple(value / total for value in row)
    return row


def _belief(prior, likelihood):
    prior = _row(prior, probability=True)
    likelihood = tuple(_row(row, probability=True) for row in likelihood)
    if len(likelihood) != len(prior) or len({len(row) for row in likelihood}) != 1:
        raise ValueError('hypothesis or endpoint dimensions differ')
    return prior, likelihood


def choose(prior, likelihood, rewards, fee):
    """Choose before receiving an endpoint; the answer distribution may be ambiguous."""
    prior, likelihood = _belief(prior, likelihood)
    rewards = tuple(_row(row) for row in rewards)
    if len(rewards) != len(prior) or len({len(row) for row in rewards}) != 1:
        raise ValueError('hypothesis or action dimensions differ')
    if fee is not None and (type(fee) not in (int, float) or not isfinite(fee) or fee < 0):
        raise ValueError('invalid observation fee')
    actions = range(len(rewards[0]))
    try:
        expected = tuple(fsum(p * row[action] for p, row in zip(prior, rewards)) for action in actions)
        before = max(expected)
        endpoint_utilities = []
        # Multiplication by P(endpoint) cancels the posterior normalization.
        for endpoint in range(len(likelihood[0])):
            weighted_hypotheses = tuple(prior[h] * likelihood[h][endpoint] for h in range(len(prior)))
            per_action = tuple(fsum(weight * row[action] for weight, row in zip(weighted_hypotheses, rewards))
                               for action in actions)
            endpoint_utilities.append(max(per_action))
        after = fsum(endpoint_utilities)
    except OverflowError as error:
        raise ValueError('nonfinite expected utility') from error
    difference = after - before
    if not all(isfinite(value) for value in (*expected, after, difference)):
        raise ValueError('nonfinite expected utility or query value')
    value = max(0., difference)
    return {'action': expected.index(before), 'ask': fee is not None and value > fee + 1e-12,
            'expected_before': before, 'expected_after': after, 'value': value}


def posterior(prior, likelihood, endpoint):
    """Update only after a physical endpoint is observed, rejecting impossible evidence."""
    prior, likelihood = _belief(prior, likelihood)
    if type(endpoint) is not int or not 0 <= endpoint < len(likelihood[0]):
        raise ValueError('invalid observed endpoint')
    weights = tuple(p * row[endpoint] for p, row in zip(prior, likelihood))
    mass = fsum(weights)
    if mass == 0:
        raise ValueError('observed endpoint has zero predicted probability')
    return tuple(weight / mass for weight in weights)
