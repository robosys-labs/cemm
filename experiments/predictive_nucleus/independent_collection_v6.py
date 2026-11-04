"""G5 v6 sealed forecast collection. Never reads Episode.truth.

The goal task, time, scope, source and physical selected-payoff forecasts
are frozen before evaluator/oracle scoring.
"""
from time import process_time
from .revision_memory import Memory
from .revision_study import scoped_latest
from .temporal_belief_v5 import probability
from .temporal_audit_v5 import record_digest, payoff_forecasts
from .goal_policy_v6 import public_task
from .independent_task_v6 import episodes

VIEWS=('mid_local','final_local','final_sibling','final_root','final_sentinel')
ARMS=('temporal','historical_temporal','scoped_rule','latest','no_memory')

def _views(ep):
    before=Memory(ep.records[:13])
    after=Memory(ep.records[:15])
    after.add(ep.records[15])  # unverified claim cannot promote physical truth
    return (
        ('qor',ep.unit,before),('qor',ep.unit,after),
        ('qor',ep.sibling,after),('qor',ep.outside,after),
        ('nav',ep.unit,after))

def collect(law,seed,bank,fitted):
    h,e=fitted['h'],fitted['e']
    started=process_time()
    seen=set()
    rows=[]
    for ep in episodes(law,seed,'challenge',bank):
        if ep.uid in seen:
            raise ValueError('duplicate world during raw collection')
        seen.add(ep.uid)
        beliefs=[]
        for term,scope,m in _views(ep):
            records=m.snapshot()  # episode memory reconstructed by typed evidence
            beliefs.append((
                probability(records,term,scope,h,e),
                probability(records,term,scope,.5,.1),
                m.belief(term,scope),
                scoped_latest(m,term,scope)
            ))
        midgoal,finalgoal,fee=public_task(ep.uid)
        rows.append({
            'id':ep.uid,'record_hash':record_digest(ep.records),
            'lineage':ep.lineage,
            'beliefs':beliefs,
            'payoff_p':payoff_forecasts(ep.records,h,e),
            'source_ids':ep.observed_sources,
            'goals':(midgoal,finalgoal),'fee':fee})
    if len(rows)!=192 or len(seen)!=192 or any(
            len(r['beliefs'])!=len(VIEWS) or len(r['payoff_p'])!=15
            for r in rows):
        raise ValueError('incomplete saved forecast bank')
    return {'version':'g5-v6-raw','law':law,'seed':seed,'split':'challenge',
            'parameters':(h,e),'cpu_seconds':process_time()-started,
            'rows':rows}
