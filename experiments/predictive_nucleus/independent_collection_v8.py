"""G5 v8 truth-blind collection. No oracle, evaluator, source-mode labels.

Reuses frozen v7 temporal controls and the same externally supplied
goal choice. Saves immutable case forecasts before any truth join.
"""
from time import process_time
from .revision_memory import Memory
from .source_temporal_v7 import probability as v7_probability
from .source_temporal_v7 import payoff_forecasts as v7_payoffs
from .joint_trust_v8 import views as joint_views,payoff_forecasts as joint_payoffs
from .independent_task_v8 import episodes
from .goal_policy_v6 import public_task
from .temporal_audit_v5 import record_digest

VIEWS=('mid_local','final_local','final_sibling','final_root','final_sentinel')
ARMS=('joint','frozen_v7','neutral','scoped_rule')

def collect(law,seed,bank):
    started=process_time()
    rows=[]
    seen=set()
    for ep in episodes(law,seed,'challenge',bank):
        if ep.uid in seen:
            raise ValueError('reused opaque world ID')
        seen.add(ep.uid)
        j=joint_views(ep)
        before=Memory(ep.records[:13])
        after=Memory(ep.records)
        context=(('qor',ep.unit,before),('qor',ep.unit,after),
                 ('qor',ep.sibling,after),('qor',ep.outside,after),
                 ('nav',ep.unit,after))
        cells=[]
        for view,(term,scope,m) in zip(VIEWS,context,strict=True):
            observed=m.snapshot()
            scoped=m.belief(term,scope)
            cells.append((j[view],
                v7_probability(observed,term,scope,.15,.03,.2),
                v7_probability(observed,term,scope,.15,.1,.1),
                .5 if scoped is None else float(scoped)))
        g0,g1,fee=public_task(ep.uid)
        rows.append(dict(id=ep.uid,
            record_hash=record_digest(ep.records),
            pre_record_hash=record_digest(ep.records[:12]),
            lineage=ep.lineage,
            beliefs=cells,
            payoff_p=joint_payoffs(ep.records),
            v7_payoff_p=v7_payoffs(ep.records,.15,.03,.2),
            neutral_payoff_p=v7_payoffs(ep.records,.15,.1,.1),
            source_ids=ep.observed_sources,
            pre_post_meaning_p=j['pre_after_epoch_local'],
            trust_pre_p=j['trust_pre'],trust_mid_p=j['trust_mid'],
            trust_final_p=j['trust_final'],
            goals=(g0,g1),fee=fee))
    if len(rows)!=192 or len(seen)!=192 or any(
        len(r['beliefs'])!=5 or any(len(c)!=4 for c in r['beliefs'])
        or len(r['payoff_p'])!=15 or len(r['v7_payoff_p'])!=15
        or len(r['neutral_payoff_p'])!=15 or len(r['source_ids'])!=15
        for r in rows):
        raise ValueError('incomplete 32-state forecast collection')
    return dict(version='g5-v8-raw',split='challenge',law=law,seed=seed,
        parameters=(.15,.03,.2,32),
        cpu_seconds=process_time()-started,rows=rows)
