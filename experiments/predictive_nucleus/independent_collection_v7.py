"""G5 v7 truth-blind collection; uses only observed selected payoffs."""
from time import process_time
from .revision_memory import Memory
from .revision_study import scoped_latest
from .temporal_belief_v5 import probability as v6_probability
from .temporal_audit_v5 import record_digest, payoff_forecasts as v6_forecasts
from .source_temporal_v7 import probability as source_probability, payoff_forecasts
from .calibrated_rule_v7 import probability as rule_probability
from .independent_task_v7 import episodes
from .goal_policy_v6 import public_task

VIEWS=('mid_local','final_local','final_sibling','final_root','final_sentinel')
ARMS=('source_temporal','v6_frozen','rule_smoothed','scoped_rule','latest','no_memory')

def views(ep):
    before=Memory(ep.records[:13])
    after=Memory(ep.records[:15])
    after.add(ep.records[15])  # unverified statement cannot promote evidence
    return (('qor',ep.unit,before),('qor',ep.unit,after),
            ('qor',ep.sibling,after),('qor',ep.outside,after),
            ('nav',ep.unit,after))

def collect(law,seed,bank,fitted):
    m=fitted['fit']
    d=fitted['rule']['delta']
    h,ea,eb=m['h'],m['e_A'],m['e_B']
    start=process_time()
    rows=[]
    seen=set()
    for ep in episodes(law,seed,'challenge',bank):
        if ep.uid in seen:
            raise ValueError('duplicate public world ID')
        seen.add(ep.uid)
        cells=[]
        for term,scope,mem in views(ep):
            history=mem.snapshot()
            cells.append((
                source_probability(history,term,scope,h,ea,eb),
                v6_probability(history,term,scope,.15,.1),
                rule_probability(mem,term,scope,d),
                mem.belief(term,scope),
                scoped_latest(mem,term,scope)))
        g0,g1,fee=public_task(ep.uid)
        rows.append({
            'id':ep.uid,'record_hash':record_digest(ep.records),
            'lineage':ep.lineage,'beliefs':cells,
            'payoff_p':payoff_forecasts(ep.records,h,ea,eb),
            'v6_payoff_p':v6_forecasts(ep.records,.15,.1),
            'source_ids':ep.observed_sources,'goals':(g0,g1),'fee':fee})
    if len(rows)!=192 or len(seen)!=192 or any(
        len(r['beliefs'])!=5 or len(r['payoff_p'])!=15 or
        len(r['v6_payoff_p'])!=15 or len(r['source_ids'])!=15
        for r in rows):
        raise ValueError('incomplete v7 raw collection')
    return {'version':'g5-v7-raw','law':law,'seed':seed,
            'split':'challenge','parameters':(h,ea,eb,d),
            'cpu_seconds':process_time()-start,'rows':rows}
