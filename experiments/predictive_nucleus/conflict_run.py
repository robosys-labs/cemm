"""Single-use matched-convention experiment with a published fit and raw decision bank."""
import argparse
from contextlib import contextmanager
import os
import platform
import resource
import subprocess
import sys
import time

import numpy as np

from . import continuation_run as io
from .acceptance_contract import digest, require
from .communication_freeze import _outputs
from .conflict_live import live_catalogue
from .conflict_policy import Receiver, choose, fit, values
from .conflict_task import ARMS, CONVENTIONS, FEES, cases, split_inventory
from .sender_stage import ORIGIN
from .transfer_task import catalogue

BASE = 'dfb62319f7e650997529aeeada6635840455d283'
REF = 'refs/heads/research/g4-matched-conflict-v1'
ROOT = io.ROOT / 'results/matched-conflict-v1'
FREEZE = io.ROOT / 'matched_conflict_v1.json'
STAGES = ('fit', 'raw', 'scored')
LAWS = ('nand', 'nor')


def runtime():
    import torch
    threads = ('OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'OMP_NUM_THREADS')
    require(all(os.environ.get(k) == '1' for k in threads), 'use one numerical thread')
    return [sys.version, np.__version__, str(torch.__version__), platform.machine(), platform.libc_ver()[1]]


def sources():
    names = ['conflict_task.py', 'conflict_policy.py', 'conflict_live.py', 'conflict_score.py',
             'conflict_run.py', 'MATCHED_CONFLICT_STUDY_V1.md']
    paths = [*(io.ROOT / name for name in names), *(io.ROOT / 'tests').glob('test_conflict_*.py')]
    return {str(p.relative_to(io.ROOT)): io._hash(p) for p in sorted(paths)}


def prepare():
    require(io._git('rev-parse', 'HEAD') == BASE and not ROOT.exists(), 'unexpected parent or outputs')
    splits = {}
    for law in LAWS:
        train, held = (catalogue(law, s) for s in ('train', 'challenge'))
        splits[law] = dict(inventory=split_inventory(train, held),
                           roster={s: digest(sorted(b['sites'])) for s,b in [('train',train),('challenge',held)]})
    io._write(FREEZE, dict(base=BASE, runtime=runtime(), sources=sources(), splits=splits))


@contextmanager
def publication(stage):
    n = STAGES.index(stage)
    chain = io._git('rev-list', '--first-parent', '--reverse', BASE+'..HEAD').splitlines()
    require(not io._git('status', '--porcelain') and len(chain) == n+1
            and io._git('rev-parse', chain[0]+'^') == BASE, 'unexpected checkout or study sequence')
    remote = subprocess.check_output(['git','ls-remote','--exit-code',ORIGIN,REF], text=True, timeout=60)
    require(remote.split() == [chain[-1],REF], 'stage requires published tip')
    freeze = io._read(FREEZE)
    require(freeze['base'] == BASE and freeze['sources'] == sources() and freeze['runtime'] == runtime()
            and not io._git('diff','--name-only','--diff-filter=DMRT',BASE,chain[0]), 'freeze differs')
    for i, name in enumerate(STAGES[:n]):
        prev = ROOT/name
        prefix = str(prev.relative_to(io.REPO)) + '/'
        delta = io._git('diff','--name-only',chain[i],chain[i+1]).splitlines()
        r = io._read(prev/'receipt.json')
        require(delta and all(k.startswith(prefix) for k in delta) and r['status'] == 'complete'
                and r['outputs'] == _outputs(prev) and io._read(prev/'attempt.json')['parent'] == chain[i],
                'prerequisite changed')
    out = ROOT/stage
    out.mkdir(parents=True, exist_ok=False)
    io._write(out/'attempt.json', dict(stage=stage, parent=chain[-1]))
    cpu, wall = time.process_time(), time.monotonic()
    try:
        yield out
        receipt = dict(status='complete', outputs=_outputs(out))
    except BaseException as exc:
        receipt = dict(status='failed', error=repr(exc))
        raise
    finally:
        receipt.update(cpu_seconds=time.process_time()-cpu, wall_seconds=time.monotonic()-wall,
                       peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        io._write(out/'receipt.json', receipt)


def fit_condition(rows):
    fitted = []
    for convention in range(len(CONVENTIONS)):
        neural, empirical = fit((r['public'], r['explore'], r['rewards'][convention][r['explore']]) for r in rows)
        fitted.append(dict(neural=neural.weight, empirical=empirical.weight))
    feedback = [[r['id'], r['pubhash'], r['probe'], r['probe_reward'], r['explore'],
                 *[pay[r['explore']] for pay in r['rewards']]] for r in rows]
    return fitted, feedback


def fixed_probability(r, source, sign):
    bit = r['ca'][source]
    row = r['public'].probe_matrix[bit]
    predicted_success = int(row[1] > row[0]) == r['probe']
    # Under independent fair reports, even an accurate sole report may be a lucky distractor.
    trust = 2/3 if predicted_success == bool(r['probe_reward']) else 0.
    if sign < 0:
        trust = 1 - trust
    return trust * r['cb'][source] + (1 - trust) * .5


def collect(rows, checkpoints):
    networks = [Receiver(cp['neural']) for cp in checkpoints]
    empirical = [Receiver(cp['empirical'], 'empirical') for cp in checkpoints]
    for r in rows:
        view = r['public']
        entry = [r['id'], r['pubhash']]
        for c in range(2):
            learned = networks[c].probability(view)
            probabilities = (learned, empirical[c].probability(view), networks[1-c].probability(view),
                fixed_probability(r,0,empirical[c].weight), fixed_probability(r,1,empirical[c].weight),
                sum(r['cb'])/2, .5, learned, learned)
            arms = []
            for arm, p in zip(ARMS, probabilities, strict=True):
                pre = choose(view.target_matrix, p, None)[0]
                cell = [p, pre]
                for fee in FEES:
                    ask = arm != 'free_silent' and choose(view.target_matrix, p, fee)[1]
                    action = pre
                    if ask and arm != 'suppressed':
                        origin = rows[r['donor']] if arm == 'shuffled' else r
                        verified = values(view.target_matrix, origin['target_bits'][c])
                        action = int(verified[1] > verified[0])
                    cell.append(2 * int(ask) + action)
                arms.append(cell)
            entry.append(arms)
        yield entry


def run(stage):
    if stage == 'prepare':
        prepare()
        return
    from .conflict_score import score
    with publication(stage) as out:
        reports = {}
        split = 'train' if stage == 'fit' else 'challenge'
        for law in LAWS:
            if stage == 'scored':
                bank = catalogue(law, split)
            else:
                bank, parity = live_catalogue(law, split)
                io._write(out/f'{law}-live.json', parity)
                if stage == 'fit':
                    io._write(out/f'{law}-matrices.json', bank['forecasts'])
            for seed in io.SEEDS:
                key = f'{law}-{seed}'
                if stage == 'fit':
                    rows = list(cases(bank, law, seed, split))
                    cp, feedback = fit_condition(rows)
                    io._write(out/f'{key}.json', cp)
                    io._write(out/f'{key}-feedback.json.xz', feedback)
                else:
                    cp = io._read(ROOT/'fit'/f'{key}.json')
                    if stage == 'raw':
                        rows = list(cases(bank, law, seed, split))
                        io._write(out/f'{key}.json.xz', dict(live_matrices=bank['forecasts'][str(seed)],
                                  rows=list(collect(rows, cp))))
                    else:
                        raw = io._read(ROOT/'raw'/f'{key}.json.xz')
                        reports[key] = score(law,seed,bank,raw,cp)
        if stage == 'scored':
            require(len(reports) == len(LAWS)*len(io.SEEDS), 'condition missing')
            passed = all(r['passed'] for r in reports.values())
            io._write(out/'decision.json', dict(passed=passed, conditions=reports,
                      decision='KEEP_MATCHED_CONFLICT' if passed else 'REVISE_MATCHED_CONFLICT'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare',*STAGES))
    run(parser.parse_args().stage)
