"""Source-neutral, goal-aware value-of-information policy for G5 v6.

Goal tables, costs and availability are externally supplied. No hidden
meaning, simulator truth or response can enter the query decision.
"""
from math import isfinite

GOALS=(
    ((1.,0.),(0.,1.)),       # direct
    ((0.,1.),(1.,0.)),       # reversed
    ((1.,1.),(1.,1.)),       # indifferent
    ((.55,.50),(.50,.55)),   # low information value
)
FEES=(.05,.75,None)

def public_task(uid):
    if not isinstance(uid,str) or len(uid)<20:
        raise ValueError('missing opaque public world ID')
    return (GOALS[int(uid[0:4],16)%4],
            GOALS[int(uid[4:8],16)%4],
            FEES[int(uid[16:20],16)%3])

def choose(p,goal,fee):
    """Return optimal action and paid-question choice *before* verification."""
    if not isinstance(p,(int,float)) or not isfinite(p) or not 0<=p<=1:
        raise ValueError('invalid belief')
    if (len(goal)!=2 or any(len(row)!=2 for row in goal) or
        any(not 0<=x<=1 for row in goal for x in row)):
        raise ValueError('invalid externally supplied goal reward matrix')
    if fee is not None and (not isfinite(fee) or fee<0):
        raise ValueError('invalid verification cost')
    expected=tuple((1-p)*goal[0][a]+p*goal[1][a] for a in range(2))
    action=int(expected[1]>expected[0])
    perfect=(1-p)*max(goal[0])+p*max(goal[1])
    voi=max(0.,perfect-expected[action])
    ask=fee is not None and voi>fee+1e-12
    return {'action':action,'ask':bool(ask),'voi':voi,
            'expected_unqueried':expected[action]}

def after_answer(goal,truth):
    """Evaluator-only: answer exists only after the policy actually pays."""
    if type(truth) is not int or truth not in (0,1):
        raise ValueError('invalid verified meaning')
    return int(goal[truth][1]>goal[truth][0])
