"""G5 v8: matched opposite post-epoch meanings and independent source modes.

Generator-only hidden meanings and source inversion rates are never read by
the collector/learner. Twins have identical observed pre-epoch prefixes.
"""
from dataclasses import dataclass
from hashlib import sha256
from .revision_study import select_triples
from .temporal_belief_v5 import TimedReceipt

SEEDS=(7,11,23,37,53)
LAWS=('nand','nor')
SPLITS=('train','challenge')
PAIRS_PER_TRIPLE=16
NAMESPACE='cemm-g5-v8-joint-trust-state-new-worlds-20261104'
REGIME={7:'stationary',11:'stationary',23:'B-degraded',
        37:'reversed',53:'within-epoch-source-switch'}
NORMAL={'A':.03,'B':.20}
REVERSED={'A':.20,'B':.03}
DEGRADED={'A':.03,'B':.30}

@dataclass(frozen=True)
class Episode:
    uid: str
    lineage: str
    records: tuple
    root: tuple
    region: tuple
    unit: tuple
    sibling: tuple
    outside: tuple
    truth: tuple  # evaluator-only (root,region,pre,post,sentinel)
    observed_sources: tuple
    source_modes: tuple  # evaluator-only (pre_orientation,post_orientation)
    flip: bool           # evaluator-only

def _uniform(parts):
    text='|'.join(str(x) for x in (NAMESPACE,*parts))
    return int(sha256(text.encode()).hexdigest()[:16],16)/2**64

def _token(*parts):
    return sha256('|'.join(str(x) for x in (NAMESPACE,'public',*parts))
                  .encode()).hexdigest()[:24]

def _modes(split,seed,key):
    if split == 'train':
        first=int(_uniform((*key,'hidden-source-first'))<.5)
        switch=int(_uniform((*key,'hidden-source-change'))<.2)
        return first,first^switch
    if seed in (7,11,23):return (0,0)
    if seed==37:return (1,1)
    if seed==53:return (0,1)
    raise ValueError('unknown hidden mode schedule')

def _error(split,seed,mode,source):
    if source not in ('A','B'):raise ValueError('unknown source')
    if split=='challenge' and seed==23:
        return DEGRADED[source]
    return (REVERSED if mode else NORMAL)[source]

def episodes(law,seed,split,bank):
    if law not in LAWS or seed not in SEEDS or split not in SPLITS:
        raise ValueError('unregistered source-trust study')
    for k,(rs,gs,ls) in enumerate(select_triples(bank,seed)):
        lineage=tuple(x[0]['lineage'] for x in (rs,gs,ls))
        for pair in range(PAIRS_PER_TRIPLE):
            key=(split,law,seed,lineage,k,pair)
            public_base=_token(*key,'pair-root')
            root=(f'world-{public_base}',)
            region=root+(f'region-{k}',)
            unit=region+(f'unit-{k}',)
            sibling=region+(f'sibling-{k}',)
            outside=root+(f'outside-{k}',)
            base=int(_uniform((*key,'truth','root'))<.5)
            regional=int(_uniform((*key,'truth','regional'))<.5)
            local=int(_uniform((*key,'truth','local'))<.5)
            sentinel=int(_uniform((*key,'truth','sentinel'))<.5)
            first,second=_modes(split,seed,key)
            placement=int(_uniform((*key,'hidden-twin-order'))<.5)
            for twin in (0,1):
                flip=bool(twin^placement)
                post=local ^ int(flip)
                uid=_token(*key,'private-episode',twin)
                records=[]
                sources=[]
                def add(site,term,scope,t,meaning,epoch=False):
                    source='A' if _uniform((*key,'source',term,t))<.5 else 'B'
                    action=int(_uniform((*key,'action',term,t))<.5)
                    real=site[0]['rewards'][action][meaning]
                    if type(real) is not int or real not in (0,1):
                        raise ValueError('invalid physical binary reward')
                    mode=first if t<9 else second
                    # Pre history, including IDs and noise, is twin-identical.
                    # After epoch only the observation-noise draw differs.
                    noise_key=key+('noise',term,t,source)+(() if t<9 else (twin,))
                    observed=real ^ int(_uniform(noise_key)<_error(split,seed,mode,source))
                    identity=(public_base if t<9 else uid)+f':{term}:{t}'
                    records.append(TimedReceipt(identity,term,scope,t,
                        f'sensor-{source}',tuple(site[1][action]),observed,
                        True,epoch))
                    sources.append(source)
                for t in range(3):
                    add(rs,'qor',root,t,base)
                    add(rs,'nav',root,t,sentinel)
                for t in range(3,6):
                    add(gs,'qor',region,t,regional)
                for t in range(6,9):
                    add(ls,'qor',unit,t,local)
                for t in range(9,12):
                    add(ls,'qor',unit,t,post,epoch=(t==9))
                assertion=int(_uniform((*key,'unverified-claim'))<.5)
                records.append(TimedReceipt(f'{uid}:unverified','qor',
                    unit,12,'unverified-witness',None,assertion,False,False))
                yield Episode(uid,'|'.join(lineage),tuple(records),
                    root,region,unit,sibling,outside,
                    (base,regional,local,post,sentinel),tuple(sources),
                    (first,second),flip)

def inventory(law,seed,split,bank):
    items=tuple(episodes(law,seed,split,bank))
    if len(items)!=6*PAIRS_PER_TRIPLE*2:
        raise ValueError('incomplete source-mode twin bank')
    if len(set(x.uid for x in items))!=len(items):
        raise ValueError('duplicate public world ID')
    for left,right in zip(items[::2],items[1::2],strict=True):
        for ep in (left,right):
            if (len(ep.records)!=16 or sum(r.physical for r in ep.records)!=15
                or len(set(r.evidence_id for r in ep.records))!=16
                or sum(bool(r.epoch) for r in ep.records)!=1
                or not ep.records[12].epoch or ep.records[-1].physical
                or len(ep.observed_sources)!=15):
                raise ValueError('invalid evidence schedule')
        if (left.records[:12]!=right.records[:12]
            or left.truth[:3]!=right.truth[:3]
            or left.truth[4]!=right.truth[4]
            or left.truth[3]==right.truth[3]
            or left.source_modes!=right.source_modes
            or left.observed_sources!=right.observed_sources
            or left.root!=right.root or left.unit!=right.unit):
            raise ValueError('opposite twins are not public-prefix matched')
    return items
