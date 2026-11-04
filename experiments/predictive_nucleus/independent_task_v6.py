"""G5 v6 independent nuisance streams over unchanged frozen G3/G4 menus.

No observation or source selection depends on hidden meaning, realized payoff,
a contradiction, or later outcomes. Truth is evaluator-only.
"""
from dataclasses import dataclass
from hashlib import sha256
from .revision_study import select_triples
from .temporal_belief_v5 import TimedReceipt

SEEDS=(7,11,23,37,53)
LAWS=('nand','nor')
SPLITS=('train','challenge')
WORLDS_PER_TRIPLE=32
EPOCH_FLIP=.2
SOURCE_ERROR={'train':{'A':.03,'B':.18},
              'challenge':{'A':.03,'B':.24}}
NAMESPACE='cemm-g5-v6-independent-nuisance-20261104'

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
    truth: tuple  # evaluator-only (root,region,local-pre,local-post,sentinel)
    observed_sources: tuple

def _uniform(parts):
    key='|'.join(str(x) for x in (NAMESPACE,*parts))
    return int(sha256(key.encode('utf-8')).hexdigest()[:16],16)/2**64

def _token(*parts):
    return sha256(('|'.join(str(x) for x in (NAMESPACE,'public',*parts))).encode()).hexdigest()[:24]

def episodes(law,seed,split,bank):
    if law not in LAWS or seed not in SEEDS or split not in SPLITS:
        raise ValueError('unregistered law, seed or split')
    for k,(root_site,region_site,unit_site) in enumerate(select_triples(bank,seed)):
        lineage=tuple(x[0]['lineage'] for x in (root_site,region_site,unit_site))
        for j in range(WORLDS_PER_TRIPLE):
            # Independent domains make even matched numeric world indices
            # different physically sampled worlds across law/seed/split.
            key=(split,law,seed,lineage,k,j)
            uid=_token(*key)
            root=(f'world-{uid}',)
            region=root+(f'region-{k}',)
            unit=region+(f'unit-{k}',)
            sibling=region+(f'sibling-{k}',)
            outside=root+(f'outside-{k}',)
            base=int(_uniform((*key,'meaning','root'))<.5)
            regional=int(_uniform((*key,'meaning','regional'))<.5)
            local=int(_uniform((*key,'meaning','local'))<.5)
            sentinel=int(_uniform((*key,'meaning','sentinel'))<.5)
            changed=_uniform((*key,'epoch','persistent'))<EPOCH_FLIP
            post=local ^ int(changed)
            records=[]
            sources=[]
            def add(site,term,scope,t,truth,epoch=False):
                source='A' if _uniform((*key,'source',term,t))<.5 else 'B'
                action=int(_uniform((*key,'action',term,t))<.5)
                _,probabilities=site
                real=site[0]['rewards'][action][truth]
                if type(real) is not int or real not in (0,1):
                    raise ValueError('non-binary physical event outcome')
                # This is a scheduled noisy observation, not an
                # outcome-conditioned contradiction or cherry-picked case.
                noisy=_uniform((*key,'sensor-noise',term,t,source))
                observed=real ^ int(noisy<SOURCE_ERROR[split][source])
                records.append(TimedReceipt(
                    f'{uid}:{term}:{t}',term,scope,t,f'sensor-{source}',
                    tuple(probabilities[action]),observed,True,epoch))
                sources.append(source)
            for t in range(3):
                add(root_site,'qor',root,t,base)
                add(root_site,'nav',root,t,sentinel)
            for t in range(3,6):
                add(region_site,'qor',region,t,regional)
            for t in range(6,9):
                add(unit_site,'qor',unit,t,local)
            for t in range(9,12):
                add(unit_site,'qor',unit,t,post,epoch=(t==9))
            # Same public distribution whether this claim agrees with truth
            # or not. No latent-value branch or oracle-derived inversion.
            assertion=int(_uniform((*key,'unverified-claim'))<.5)
            records.append(TimedReceipt(f'{uid}:unverified','qor',unit,12,
                'unverified-witness',None,assertion,False,False))
            yield Episode(uid,'|'.join(lineage),tuple(records),root,region,
                          unit,sibling,outside,
                          (base,regional,local,post,sentinel),tuple(sources))

def inventory(law,seed,split,bank):
    items=tuple(episodes(law,seed,split,bank))
    if len(items)!=6*WORLDS_PER_TRIPLE:
        raise ValueError('missing independent physical worlds')
    if len(set(ep.uid for ep in items))!=len(items):
        raise ValueError('duplicate public world ID')
    for ep in items:
        records=ep.records
        if (len(records)!=16 or sum(r.physical for r in records)!=15
            or sum(bool(r.epoch) for r in records)!=1
            or not records[12].epoch
            or records[-1].physical
            or len(set(r.evidence_id for r in records))!=len(records)
            or len(ep.observed_sources)!=15):
            raise ValueError('invalid episode evidence/epoch')
    return items
