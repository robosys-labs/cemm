"""Unseen sender bindings over immutable G3 physical decisions from PR #83."""
from collections import Counter
from itertools import product

import numpy as np

from . import continuation_run as io
from .acceptance_contract import digest, require

PARENT = io.ROOT / 'data/sender-v1'
PARENT_FREEZE = '4227129ce5fc9c095d5294a739fcae395c3a955fa184dd10065a6ea2e5ce6f15'
STRATA = ('hidden', 'known', 'costly', 'indifferent')
PARTITIONS = {'train': ('train',), 'challenge': ('recombined', 'fresh')}
# Each XOR mask is a perfect matching on one parity class of eight badges.
MASKS = {'train': (3, 5, 6, 9, 3, 5), 'recombined': (10, 12, 10), 'fresh': (3, 12, 3)}
BITS = tuple(product((0, 1), repeat=2))


def badge(identity):
    require(type(identity) is int and 0 <= identity < 16, 'bad badge identity')
    return tuple(1 if identity & (1 << i) else -1 for i in range(4))


def goal_code(identity):
    a, b, c, d = badge(identity)
    return -b, a, -d, c


def catalogue(law, split):
    require(law in ('nand', 'nor') and split in PARTITIONS, 'unknown physical bank')
    freeze = io.ROOT / 'sender_freeze_v1.json'
    path = PARENT / f'{law}-{split}-pairs.json.xz'
    require(io._hash(freeze) == PARENT_FREEZE, 'parent freeze differs')
    require(io._hash(path) == io._read(freeze)['hashes'][path.relative_to(io.REPO).as_posix()],
            'physical pair catalogue differs')
    return io._read(path)


def _assignments(pair_ids, split):
    roster = sorted(pair_ids)
    require(len(roster) == 12, 'parent must supply twelve physical pairs')
    for partition in PARTITIONS[split]:
        ids = [i for i in range(16) if i.bit_count() % 2 == int(partition == 'fresh')]
        edges = [(i, i ^ m) for m in MASKS[partition] for i in ids if i < i ^ m]
        for index, edge in enumerate(edges):
            yield roster[index % len(roster)], partition, edge


def schedule(law, split):
    return tuple(_assignments(catalogue(law, split)['sites'], split))


def round_id(law, split, pair_id, partition, badge_ids, goal_id, bits, stratum, rep):
    return digest(['g4-transfer-round-v1', law, split, pair_id, partition,
                   badge_ids, goal_id, bits, stratum, rep])


def donor_id(r):
    site = r['badge_ids'].index(r['goal_id'])
    bits = [b ^ int(j != site or (r['rep'] >= 2 and r['stratum'] != 'known'))
            for j, b in enumerate(r['bits'])]
    return round_id(r['law'], r['split'], r['pair_id'], r['partition'], r['badge_ids'],
                    r['goal_id'], bits, r['stratum'], r['rep'])


def rounds(law, seed, split):
    bank = catalogue(law, split)
    forecasts = bank['forecasts'][str(seed)]
    for pair, partition, edge in _assignments(bank['sites'], split):
        native = bank['sites'][pair]
        for tags, focus, bits in product((edge, edge[::-1]), (0, 1), BITS):
            goal = tags[focus]
            witness = tuple(s['witness'][b]['id'] for s, b in zip(native, bits, strict=True))
            tape = native[focus]['episodes'][bits[focus]]
            payoff = native[focus]['rewards'][bits[focus]]
            for stratum, rep in product(STRATA, range(4)):
                identity = round_id(law, split, pair, partition, tags, goal, bits, stratum, rep)
                # Matched exploratory pairs in TRAIN must see the same physical action slots.
                reversed_menu = bool((rep // 2) ^ (int(pair[:8], 16) % 2)) if split == 'train' else bool(rep % 2)
                order = (1, 0) if reversed_menu else (0, 1)
                matrix = [[row[a] for a in order] for row in forecasts[pair][focus]]
                rewards = [payoff[a] for a in order]
                if stratum == 'indifferent':
                    matrix, rewards = [[1., 1.], [1., 1.]], [1, 1]
                local = bits[focus] if stratum == 'known' else None
                prior = matrix[local] if local is not None else [(x + y) / 2 for x, y in zip(*matrix)]
                r = dict(law=law, seed=seed, split=split, pair_id=pair, partition=partition,
                         id=identity, badge_ids=tags, goal_id=goal, sites=tuple(map(badge, tags)),
                         goal=goal_code(goal), bits=bits, source='W0', stratum=stratum, rep=rep,
                         menu_reversed=reversed_menu, cost=.75 if stratum == 'costly' else .05,
                         matrix=matrix, prior=prior, local=local, rewards=rewards, witness_ids=witness,
                         physical_ids=[tape[a] for a in order])
                r['donor'] = donor_id(r)
                r['random_bit'] = int(digest(['g4-transfer-random-v1', identity])[:16], 16) % 2
                yield r


def split_audit(law):
    """Structural evidence only. Never reads outcome values for selection or runs a model."""
    meta, supports, signatures, identities, edges = {}, {}, {}, {}, {}
    for split, partitions in PARTITIONS.items():
        bank = catalogue(law, split)
        sites = [s for p in bank['sites'].values() for s in p]
        supports[split] = {k: {v for s in sites for v in values(s)} for k, values in (
            ('entities', lambda s: s['entities']), ('sensor_receipts', lambda s: [w['id'] for w in s['witness']]),
            ('physical_tapes', lambda s: [i for h in s['episodes'] for i in h]),
            ('lineages', lambda s: [s['lineage']]))}
        assignments = tuple(_assignments(bank['sites'], split))
        require(len(set(assignments)) == len(assignments) == 24, 'repeated scheduled pair/edge')
        for partition in partitions:
            selected = [(p, e) for p, name, e in assignments if name == partition]
            edges[partition] = {e for _, e in selected}
            identities[partition] = {i for e in edges[partition] for i in e}
            counts = Counter(i for _, e in selected for i in e)
            require(len(set(counts.values())) == 1 and len(counts) == 8, 'badge incidence unbalanced')
            sig = set()
            design = []
            for edge in edges[partition]:
                for tags, goal, bits in product((edge, edge[::-1]), edge, BITS):
                    x, y = map(badge, tags)
                    g = goal_code(goal)
                    require(g not in (badge(goal), tuple(-v for v in badge(goal))) and
                            sum(a*b for a, b in zip(badge(goal), g)) == 0,
                            'aligned or antipodal goal leak')
                    sig.add((x, y, g, bits))
                    design.append([v * (a-b) for v in g for a, b in zip(x, y)])
            signatures[partition] = sig
            meta[partition] = dict(badges=sorted(counts), unordered_edges=sorted(edges[partition]),
                physical_pairs=len({p for p, _ in selected}), edge_assignments=len(selected),
                signatures=len(sig), signature_sha256=digest(sorted(sig)),
                bilinear_contrast_rank=int(np.linalg.matrix_rank(design)),
                rounds=len(selected)*2*2*len(BITS)*len(STRATA)*4)
    require(meta['train']['bilinear_contrast_rank'] == 16, 'training design is rank deficient')
    require(identities['recombined'] == identities['train'] and
            not identities['fresh'] & identities['train'], 'badge split invalid')
    for a, b in (('train', 'recombined'), ('train', 'fresh'), ('recombined', 'fresh')):
        require(signatures[a].isdisjoint(signatures[b]) and edges[a].isdisjoint(edges[b]),
                'sender-visible signature or unordered edge overlap')
    overlap = {k: len(supports['train'][k] & supports['challenge'][k]) for k in supports['train']}
    require(not any(overlap.values()), 'native physical split overlaps')
    return dict(law=law, parent_freeze=PARENT_FREEZE, partitions=meta, physical_overlap=overlap,
                sender_signature_overlap=0, unordered_edge_overlap=0)
