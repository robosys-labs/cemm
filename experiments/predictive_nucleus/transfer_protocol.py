"""Freeze exact input streams and enforce publication order for transfer v1."""
from contextlib import contextmanager
from hashlib import sha256
import json
import os
import platform
import resource
import subprocess
import sys
import time

import numpy as np

from . import continuation_run as io
from .acceptance_contract import require
from .communication_freeze import _outputs
from .sender_stage import ORIGIN

BASE = '78e1dcd22f31147dc5433420185d6f3e9ae17245'
REF = 'refs/heads/research/g4-shared-transfer-v1'
FREEZE = io.ROOT / 'transfer_binding_v1.json'
RESULT = io.ROOT / 'results/transfer-binding-v1'
STAGES = ('fit', 'raw', 'scored')


def signature(rows):
    h = sha256()
    count = 0
    for r in rows:
        h.update(json.dumps(r, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n')
        count += 1
    return {'rows': count, 'sha256': h.hexdigest()}


def implementation():
    names = ('transfer_task.py', 'transfer_sender.py', 'transfer_score.py', 'transfer_run.py',
             'transfer_protocol.py', 'TRANSFER_BINDING_STUDY_V1.md')
    paths = [*(io.ROOT / n for n in names), *io.ROOT.glob('tests/test_transfer_binding*.py'),
             *(io.ROOT / 'tests' / ('test_' + n) for n in ('transfer_score.py','transfer_task.py','transfer_sender.py'))]
    return {str(p.relative_to(io.ROOT)): io._hash(p) for p in sorted(set(paths)) if p.is_file()}


def runtime():
    require(os.environ.get('OPENBLAS_NUM_THREADS') == '1', 'use one BLAS thread')
    return {'python': sys.version, 'numpy': np.__version__, 'machine': platform.machine(),
            'libc': list(platform.libc_ver()), 'blas_threads': 1,
            'numpy_blas': np.__config__.CONFIG.get('Build Dependencies', {}).get('blas', {})}


@contextmanager
def stage(name):
    i = STAGES.index(name)
    require(not io._git('status', '--porcelain', '--untracked-files=all'), 'dirty study checkout')
    chain = io._git('rev-list', '--reverse', '--first-parent', BASE + '..HEAD').splitlines()
    require(len(chain) == i+1 and io._git('rev-parse', chain[0]+'^') == BASE, 'publication sequence differs')
    require(subprocess.check_output(['git','ls-remote','--exit-code',ORIGIN,REF], text=True, timeout=50).split()
            == [chain[-1],REF], 'commit must be published first')
    require(not io._git('diff','--name-only','--diff-filter=DMRT',BASE,chain[0]), 'parent changed at freeze')
    spec = io._read(FREEZE)
    require(spec['base'] == BASE and spec['implementation'] == implementation() and spec['runtime'] == runtime(),
            'source or runtime differs')
    for k in range(i):
        previous = RESULT / STAGES[k]
        prefix = str(previous.relative_to(io.REPO)) + '/'
        delta = io._git('diff','--name-only',chain[k],chain[k+1]).splitlines()
        receipt = io._read(previous/'receipt.json')
        require(delta and all(p.startswith(prefix) for p in delta) and receipt['status'] == 'complete'
                and receipt['outputs'] == _outputs(previous) and io._read(previous/'attempt.json')['input']==chain[k],
                'prerequisite evidence changed')
    out = RESULT / name
    out.mkdir(parents=True, exist_ok=False)
    io._write(out/'attempt.json', {'input':chain[-1], 'stage':name})
    cpu, wall = time.process_time(), time.monotonic()
    try:
        yield out
        receipt = {'status':'complete','outputs':_outputs(out)}
    except BaseException as exc:
        receipt = {'status':'failed','error':repr(exc)}
        raise
    finally:
        receipt.update(cpu_seconds=time.process_time()-cpu, wall_seconds=time.monotonic()-wall,
                       peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        io._write(out/'receipt.json',receipt)
