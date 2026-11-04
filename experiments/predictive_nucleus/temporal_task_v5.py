"""G5 v5 controlled temporal task: observed physical payoffs, no gold learner labels.

Physical menus come from frozen G3/G4 banks. The new noise/epoch task is
prospective but the physical families have been previously opened.
"""
from dataclasses import dataclass
from hashlib import sha256
from itertools import product

from .revision_study import select_triples
from .temporal_belief_v5 import TimedReceipt

SEEDS=(7,11,23,37,53)
LAWS=('nand','nor')
SALT={'train':'g5-temporal-v5-train-20261104',
      'challenge':'g5-temporal-v5-challenge-20261104'}


@dataclass(frozen=True)
class Episode:
    identity: str
    records: tuple
    root: tuple
    region: tuple
    unit: tuple
    sibling: tuple
    outside: tuple
    # Evaluator-only. Never supplied to fit(), posterior(), or an action policy.
    truth: tuple
    variant: int


def _noise(split,key,term,time):
    text=f'{SALT[split]}:{key}:{term}:{time}'.encode('utf-8')
    return (int(sha256(text).hexdigest()[:12],16) % 10000) < 800


def episodes(law,seed,split,bank):
    if split not in SALT or law not in LAWS or seed not in SEEDS:
        raise ValueError('unsupported frozen study condition')
    selected=select_triples(bank,seed)
    for k,(root_site,region_site,unit_site) in enumerate(selected):
        for idx,(base,regional,local,sentinel) in enumerate(product((0,1),repeat=4)):
            # Opaque ID doesn't contain bit values or variant; the learner
            # never derives meaning from the ID string.
            token=sha256(f'{SALT[split]}:site:{k}:case:{idx}'.encode()).hexdigest()[:20]
            root=(f'w-{token}',)
            region=root+(f'r-{k}',)
            unit=region+(f'u-{k}',)
            sibling=region+(f's-{k}',)
            outside=root+(f'x-{k}',)
            for variant in (0,1):
                records=[]
                def add(site,term,scope,t,meaning,epoch=False,force=False):
                    model,forecasts=site
                    action=t%2
                    native=model['rewards'][action][meaning]
                    # A verified physical reading may have 8% observational
                    # noise. The matched contradictory event itself is fixed.
                    received = native if force else native ^ int(_noise(split,token,term,t))
                    records.append(TimedReceipt(
                        f'{token}-{term}-{t}',term,scope,t,
                        f'physical-sensor-{t%2}',tuple(forecasts[action]),
                        received,True,epoch))
                for t in range(3):
                    add(root_site,'qor',root,t,base)
                    add(root_site,'nav',root,t,sentinel)
                for t in range(3,6):
                    add(region_site,'qor',region,t,regional)
                for t in range(6,9):
                    add(unit_site,'qor',unit,t,local)
                # Same public conflict and same observed selected payoff
                # for both latent realities; the later meaning differs.
                add(unit_site,'qor',unit,9,1-local,epoch=True,force=True)
                current=local if variant==0 else 1-local
                for t in (10,11):
                    add(unit_site,'qor',unit,t,current)
                records.append(TimedReceipt(
                    f'{token}-unverified','qor',unit,12,
                    'unverified-witness',None,1-current,False,False))
                yield Episode(token,tuple(records),root,region,unit,sibling,outside,
                              (base,regional,current,sentinel),variant)


def inventory(law,seed,split,bank):
    """Validate the exact new task and matched counterfactuals."""
    items=list(episodes(law,seed,split,bank))
    if len(items)!=192:
        raise ValueError('incomplete G5 temporal case inventory')
    for a,b in zip(items[::2],items[1::2],strict=True):
        if (a.identity!=b.identity or a.variant!=0 or b.variant!=1
                or a.records[:13]!=b.records[:13]
                or a.truth[2]==b.truth[2]
                or a.records[13:15]==b.records[13:15]
                or any(r.source=='unverified-witness' and r.physical for r in a.records)
                or len(a.records)!=len(b.records)!=16):
            raise ValueError('invalid matched exception/revision twins')
    return items
